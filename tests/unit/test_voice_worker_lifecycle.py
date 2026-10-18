"""Identity, fail-closed cleanup, and pre-SDK handshake without launching a worker."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jarvis_voice_lab import asr_worker, transcribe
from apps.jarvis_voice_lab import worker_lifecycle as lifecycle


class Process:
    pid = 100
    _handle = 11


class Api:
    def __init__(self, image):
        self.expected_image = lifecycle._normalized(image)
        self.worker_pid, self.worker_parent = 200, 100
        self.creation, self.stopped = 200, False
        self.opened, self.closed, self.terminated, self.waited = [], [], [], []

    def created(self, handle):
        return 100 if handle == 11 else self.creation

    def open(self, pid):
        self.opened.append(pid)
        return 22

    def pid(self, handle):
        return self.worker_pid

    def parent(self, handle):
        return self.worker_parent

    def image(self, handle):
        return self.expected_image

    def exited(self, handle, seconds=0):
        self.waited.append((handle, seconds))
        return self.stopped

    def terminate(self, handle):
        self.terminated.append(handle)
        self.stopped = True

    def close(self, handle):
        self.closed.append(handle)


@pytest.fixture
def supervisor(tmp_path):
    binding = lifecycle.new_binding("a" * 32)
    ready = dict(binding, pid=200, ppid=100, creation_time=200)
    api = Api(tmp_path / "python.exe")
    owner = lifecycle.OwnedWorkerSupervisor(
        process=Process(), directory=tmp_path, binding=binding,
        expected_image=api.expected_image, api=api,
    )
    return owner, ready, api


def test_ack_is_only_written_after_handle_identity_is_retained(supervisor):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    assert owner.poll_handshake()
    acknowledgment, _ = lifecycle._read(owner.directory / lifecycle.ACK)
    assert acknowledgment == ready
    assert api.opened == [200] and owner.handle == 22
    owner.confirm_exit(terminate=True)
    assert owner.exit_confirmed and api.terminated == [22]
    assert api.waited[-1] == (22, lifecycle.EXIT_SECONDS)
    owner.confirm_exit(terminate=True)
    assert api.terminated == [22]  # Confirmed exit is idempotent, not a second kill.
    owner.close()
    assert api.closed == [22]


def test_cancel_before_ack_never_starts_sdk(supervisor):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    owner.confirm_exit(terminate=True)
    assert owner.exit_confirmed and api.terminated == [22]
    assert not (owner.directory / lifecycle.ACK).exists()


def test_direct_python_worker_binds_parent_to_supervisor(supervisor):
    owner, ready, api = supervisor
    ready.update(pid=owner.process.pid, ppid=os.getpid())
    api.worker_pid, api.worker_parent = owner.process.pid, os.getpid()
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    assert owner.poll_handshake()
    owner.confirm_exit(terminate=True)
    assert api.terminated == [22] and owner.exit_confirmed


def test_worker_predating_this_launcher_is_never_acknowledged(supervisor):
    owner, ready, api = supervisor
    ready["creation_time"], api.creation = 90, 90
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    with pytest.raises(ValueError, match="worker_handle_identity_refused"):
        owner.poll_handshake()
    assert api.closed == [22] and not api.terminated
    assert not (owner.directory / lifecycle.ACK).exists()


@pytest.mark.parametrize("field,value", [
    ("schema_version", "other"), ("run_id", "b" * 32), ("nonce", "b" * 64),
    ("pid", True), ("pid", 0), ("ppid", 999), ("creation_time", 201),
])
def test_unbound_identity_is_not_acknowledged_or_terminated(supervisor, field, value):
    owner, ready, api = supervisor
    ready[field] = value
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    with pytest.raises(ValueError):
        owner.poll_handshake()
    assert not (owner.directory / lifecycle.ACK).exists()
    assert not api.terminated


@pytest.mark.parametrize("attribute,value", [
    ("worker_pid", 201), ("worker_parent", 999), ("creation", 201),
    ("expected_image", "other-python.exe"), ("stopped", True),
])
def test_handle_attestation_failure_closes_without_killing(supervisor, attribute, value):
    owner, ready, api = supervisor
    setattr(api, attribute, value)
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    with pytest.raises(ValueError, match="worker_handle_identity_refused"):
        owner.poll_handshake()
    assert api.closed == [22] and not api.terminated
    assert not (owner.directory / lifecycle.ACK).exists()


def test_unknown_worker_and_unconfirmed_exit_are_sanitized_quarantine(supervisor):
    owner, _, api = supervisor
    with pytest.raises(lifecycle.WorkerExitUnconfirmed) as captured:
        owner.confirm_exit(terminate=True)
    assert str(captured.value) == "local_asr_worker_exit_unconfirmed"
    assert captured.value.artifacts_retained is True
    assert not api.opened and not api.terminated


def test_failed_termination_or_wait_retains_artifacts(supervisor, monkeypatch):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    owner.poll_handshake()
    monkeypatch.setattr(api, "terminate", lambda handle: None)
    with pytest.raises(lifecycle.WorkerExitUnconfirmed):
        owner.confirm_exit(terminate=True, timeout_seconds=0.1)
    assert not owner.exit_confirmed
    assert (owner.directory / lifecycle.READY).exists()


@pytest.mark.parametrize("exits_during_termination", [True, False])
def test_termination_error_requires_new_kernel_exit_confirmation(
    supervisor, monkeypatch, exits_during_termination,
):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    owner.poll_handshake()

    def failed_termination(handle):
        api.terminated.append(handle)
        api.stopped = exits_during_termination
        raise OSError("fixture termination refused")

    monkeypatch.setattr(api, "terminate", failed_termination)
    if exits_during_termination:
        owner.confirm_exit(terminate=True, timeout_seconds=0.1)
        assert owner.exit_confirmed
    else:
        with pytest.raises(lifecycle.WorkerExitUnconfirmed) as captured:
            owner.confirm_exit(terminate=True, timeout_seconds=0.1)
        assert str(captured.value) == "local_asr_worker_exit_unconfirmed"
        assert captured.value.artifacts_retained and not owner.exit_confirmed
    assert api.terminated == [22]  # No retry or replacement PID/handle.
    assert api.waited[-2:] == [(22, 0), (22, 0.1)]


def test_failed_kernel_wait_after_termination_error_is_quarantined(supervisor, monkeypatch):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    owner.poll_handshake()

    def failed_termination(handle):
        api.terminated.append(handle)
        raise OSError("fixture termination refused")

    def failed_wait(handle, seconds=0):
        if seconds:
            raise OSError("fixture kernel wait failed")
        return False

    monkeypatch.setattr(api, "terminate", failed_termination)
    monkeypatch.setattr(api, "exited", failed_wait)
    with pytest.raises(lifecycle.WorkerExitUnconfirmed):
        owner.confirm_exit(terminate=True, timeout_seconds=0.1)
    assert not owner.exit_confirmed and api.terminated == [22]


def test_ack_creation_failure_keeps_verified_handle_for_safe_stop(supervisor):
    owner, ready, api = supervisor
    lifecycle._write(owner.directory / lifecycle.READY, ready)
    (owner.directory / lifecycle.ACK).write_bytes(b"pre-existing")
    with pytest.raises(FileExistsError):
        owner.poll_handshake()
    assert owner.handle == 22
    owner.confirm_exit(terminate=True)
    assert api.terminated == [22]


def test_private_records_are_bounded_binary_and_replacement_refused(tmp_path):
    path = tmp_path / lifecycle.READY
    lifecycle._write(path, {"a": 1})
    assert path.read_bytes() == b'{"a":1}\n'
    _, identity = lifecycle._read(path)
    other = tmp_path / "replacement"
    other.write_bytes(b'{"a":2}\n')
    os.replace(other, path)
    with pytest.raises(ValueError, match="worker_private_metadata_refused"):
        lifecycle._read(path, identity)
    path.write_bytes(b"x" * (lifecycle.MAX_BYTES + 1))
    with pytest.raises(ValueError, match="worker_private_metadata_refused"):
        lifecycle._read(path)


def test_partial_record_waits_but_duplicate_fields_are_refused(tmp_path):
    path = tmp_path / lifecycle.READY
    path.write_bytes(b'{"a":')
    document, identity = lifecycle._read(path)
    assert document is None and identity is not None
    path.write_bytes(b'{"a":1,"a":2}\n')
    with pytest.raises(ValueError, match="worker_duplicate_field"):
        lifecycle._read(path, identity)


def test_hard_linked_private_record_is_refused(tmp_path):
    path = tmp_path / lifecycle.READY
    path.write_bytes(b'{"a":1}\n')
    os.link(path, tmp_path / "unowned-alias")
    with pytest.raises(ValueError, match="worker_private_file_required"):
        lifecycle._read(path)


@pytest.mark.parametrize("run_id", [None, "", "A" * 32, "a" * 31, True])
def test_invalid_binding_rejected(run_id):
    with pytest.raises(ValueError, match="worker_identity_binding_refused"):
        lifecycle.new_binding(run_id)


def test_venv_image_comes_from_validated_local_configuration(tmp_path):
    scripts, base = tmp_path / "env" / "Scripts", tmp_path / "base"
    scripts.mkdir(parents=True)
    base.mkdir()
    executable, real = scripts / "python.exe", base / "python.exe"
    executable.write_bytes(b"fixture launcher")
    real.write_bytes(b"fixture real image")
    (scripts.parent / "pyvenv.cfg").write_text(f"home = {base}\n", encoding="utf-8")
    assert lifecycle.expected_worker_image(executable) == lifecycle._normalized(real)
    (scripts.parent / "pyvenv.cfg").write_text("home = relative\n", encoding="utf-8")
    with pytest.raises(ValueError, match="worker_venv_configuration_refused"):
        lifecycle.expected_worker_image(executable)


@pytest.mark.parametrize("selected", [
    r"\\server\share\python.exe", "//server/share/python.exe",
    r"\\?\C:\runtime\python.exe", r"\\.\pipe\python.exe",
    r"\??\C:\runtime\python.exe", r"\Device\HarddiskVolume1\python.exe",
    r"\runtime\python.exe", r"C:runtime\python.exe", "relative/python.exe",
])
def test_untrusted_selected_executable_is_refused_before_metadata_io(selected, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("metadata IO attempted for rejected executable")

    monkeypatch.setattr(Path, "lstat", forbidden)
    monkeypatch.setattr(Path, "stat", forbidden)
    with pytest.raises(ValueError, match="worker_private_path_refused"):
        lifecycle.expected_worker_image(selected)


@pytest.mark.parametrize("home", [
    r"\\server\share\runtime", "//server/share/runtime",
    r"\\?\C:\runtime", r"\\.\pipe\runtime", r"\??\C:\runtime",
    r"\Device\HarddiskVolume1\runtime", r"\runtime", r"C:runtime", "relative/runtime",
])
def test_venv_home_is_refused_before_any_home_metadata_io(tmp_path, home, monkeypatch):
    scripts = tmp_path / "env" / "Scripts"
    scripts.mkdir(parents=True)
    executable, configuration = scripts / "python.exe", scripts.parent / "pyvenv.cfg"
    executable.write_bytes(b"fixture launcher")
    configuration.write_text(f"home = {home}\n", encoding="utf-8")
    original_lstat, original_stat = Path.lstat, Path.stat
    # Reading the explicit local launcher/configuration is legitimate. No other
    # leaf, including the cfg's nominated python.exe, may be inspected.
    allowed = {executable, configuration, *executable.parents, *configuration.parents}

    def guarded_lstat(path, *args, **kwargs):
        if path not in allowed:
            pytest.fail("lstat attempted on rejected venv home")
        return original_lstat(path, *args, **kwargs)

    def guarded_stat(path, *args, **kwargs):
        if path not in allowed:
            pytest.fail("stat attempted on rejected venv home")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    with pytest.raises(ValueError, match="worker_venv_configuration_refused"):
        lifecycle.expected_worker_image(executable)


def test_worker_sdk_is_forbidden_without_acknowledgment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    api = SimpleNamespace(current=lambda: 22, created=lambda handle: 200)
    binding = lifecycle.new_binding("a" * 32)
    request = dict(run_id="a" * 32, output_directory=str(tmp_path), worker_lifecycle=binding)
    current, pauses = [0.0], []

    def pause(seconds):
        pauses.append(seconds)
        current[0] += seconds

    with pytest.raises(ValueError, match="worker_acknowledgment_expired"):
        lifecycle.acknowledge_worker(request, api=api, clock=lambda: current[0], pause=pause)
    assert current[0] >= lifecycle.HANDSHAKE_SECONDS
    assert pauses and max(pauses) <= 0.01
    ready, _ = lifecycle._read(tmp_path / lifecycle.READY)
    assert ready["nonce"] == binding["nonce"] and not (tmp_path / lifecycle.ACK).exists()


def test_asr_handshake_happens_before_guard_and_sdk_and_is_not_stdout(monkeypatch, capsys):
    events = []
    request = dict(authorized=True, run_id="a" * 32, device="cpu", worker_lifecycle={})
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(
        buffer=io.BytesIO(json.dumps(request).encode()),
    ))

    def spec(name, path):
        def execute(module):
            if name == "offline_worker_lifecycle":
                module.acknowledge_worker = lambda value: events.append("ack")
            else:
                module._deny_network = lambda: events.append("guard")
        return SimpleNamespace(loader=SimpleNamespace(exec_module=execute))

    monkeypatch.setattr(asr_worker.importlib.util, "spec_from_file_location", spec)
    monkeypatch.setattr(asr_worker.importlib.util, "module_from_spec",
                        lambda value: SimpleNamespace())
    monkeypatch.setattr(asr_worker, "generate", lambda value: events.append("sdk"))
    assert asr_worker.main() == 0
    assert events == ["ack", "guard", "sdk"]
    assert json.loads(capsys.readouterr().out) == {"run_id": "a" * 32, "status": "completed"}


def test_asr_failed_handshake_cannot_import_guard_or_sdk(monkeypatch, capsys):
    request = dict(authorized=True, run_id="a" * 32, device="cpu", worker_lifecycle={})
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(
        buffer=io.BytesIO(json.dumps(request).encode()),
    ))
    imports = []

    def refuse(value):
        raise ValueError("private failure details must not appear in stdout")

    def spec(name, path):
        imports.append(name)
        return SimpleNamespace(loader=SimpleNamespace(
            exec_module=lambda module: setattr(module, "acknowledge_worker", refuse),
        ))

    monkeypatch.setattr(asr_worker.importlib.util, "spec_from_file_location", spec)
    monkeypatch.setattr(asr_worker.importlib.util, "module_from_spec",
                        lambda value: SimpleNamespace())
    monkeypatch.setattr(asr_worker, "generate", lambda value: pytest.fail("SDK invoked"))
    assert asr_worker.main() == 0
    assert imports == ["offline_worker_lifecycle"]
    assert json.loads(capsys.readouterr().out) == {
        "run_id": "a" * 32, "status": "failed", "error_type": "ValueError",
    }


@pytest.fixture
def transcription_arguments(tmp_path):
    source, models = tmp_path / "capture.wav", tmp_path / "models"
    models.mkdir()
    with wave.open(str(source), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x01\x00" * 8000)
    return dict(authorized=True, source=source, model_dir=models,
                python_executable=Path(sys.executable).resolve(strict=True))


def test_lifecycle_flag_is_strict_before_source_io(transcription_arguments):
    with pytest.raises(ValueError, match="invalid_local_asr_lifecycle_option"):
        transcribe.transcribe_local_wav(**dict(transcription_arguments, source=Path("missing")),
                                       confirm_worker_exit="yes")


@pytest.mark.parametrize("platform,enabled", [("win32", True), ("linux", True), ("win32", False)])
def test_guarded_transcription_reaps_before_artifact_read(
    transcription_arguments, monkeypatch, platform, enabled,
):
    events, seen = [], {}

    class Child:
        returncode = 0

        def __init__(self, *args, **kwargs):
            seen.update(kwargs)

        def communicate(self, input=None, timeout=None):
            request = json.loads(input)
            seen["request"] = request
            output = Path(request["output_directory"])
            (output / "transcript.txt").write_text("RASCUNHO fixture", encoding="utf-8")
            (output / "transcript.json").write_text('{"review_required":true}', encoding="utf-8")
            seen["stdout"].write(json.dumps(dict(run_id=request["run_id"], status="completed"))
                                 .encode())
            seen["stdout"].flush()
            events.append("launcher_returned")

    class Supervisor:
        def __init__(self, **kwargs):
            events.append("supervised")

        def poll_handshake(self):
            events.append("handshake")

        def confirm_exit(self, **kwargs):
            events.append("real_exit")

        def close(self):
            events.append("handle_closed")

    monkeypatch.setattr(transcribe.sys, "platform", platform)
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0, raising=False)
    monkeypatch.setattr(transcribe, "expected_worker_image", lambda executable: str(executable))
    monkeypatch.setattr(transcribe, "OwnedWorkerSupervisor", Supervisor)
    monkeypatch.setattr(transcribe.subprocess, "Popen", Child)
    result = transcribe.transcribe_local_wav(**transcription_arguments, confirm_worker_exit=enabled)
    assert result["review_required"] is True
    guarded = platform == "win32" and enabled
    assert ("worker_lifecycle" in seen["request"]) is guarded
    assert ("real_exit" in events) is guarded
    if guarded:
        assert events == [
            "supervised", "handshake", "launcher_returned", "real_exit", "handle_closed",
        ]
    assert not Path(result["transcript_path"]).with_name("worker-status.tmp").exists()


def test_unconfirmed_worker_preserves_runtime_and_capture(transcription_arguments, monkeypatch):
    seen = {}

    class Child:
        def __init__(self, *args, **kwargs):
            seen.update(kwargs)

        def communicate(self, input=None, timeout=None):
            seen["request"] = json.loads(input)
            raise RuntimeError("fixture control failure")

    class Supervisor:
        def __init__(self, **kwargs):
            pass

        def poll_handshake(self):
            pass

        def confirm_exit(self, **kwargs):
            raise lifecycle.WorkerExitUnconfirmed()

        def close(self):
            pass

    original = transcription_arguments["source"].read_bytes()
    monkeypatch.setattr(transcribe.sys, "platform", "win32")
    monkeypatch.setattr(subprocess, "CREATE_NO_WINDOW", 0, raising=False)
    monkeypatch.setattr(transcribe, "expected_worker_image", lambda executable: str(executable))
    monkeypatch.setattr(transcribe, "OwnedWorkerSupervisor", Supervisor)
    monkeypatch.setattr(transcribe.subprocess, "Popen", Child)
    monkeypatch.setattr(transcribe, "_stop", lambda process: None)
    with pytest.raises(lifecycle.WorkerExitUnconfirmed):
        transcribe.transcribe_local_wav(**transcription_arguments, confirm_worker_exit=True)
    runtime = Path(seen["request"]["output_directory"])
    assert runtime.is_dir() and (runtime / "worker-status.tmp").exists()
    assert transcription_arguments["source"].read_bytes() == original
