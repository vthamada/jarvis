"""Public batch campaign controls; all audio and SDK process behavior are synthetic.

Popen doubles below exercise the parent's real-process supervision branch, not
real inference. No human reference, executable, credentials or Core store runs.
"""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import lab_batch

TEXT = "  Synthetic final, exact whitespace.\r\n" * 30


def _wav(path, *, frames=16, rate=8000, value=300, channels=1):
    raw = struct.pack("<h", value) * frames * channels
    with wave.open(str(path), "wb") as audio:
        audio.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(raw)
    return raw


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    model = tmp_path / "private-marker-model"
    model.mkdir()
    python = tmp_path / "private-marker-python.exe"
    python.write_bytes(b"synthetic executable never launched")
    reference = tmp_path / "private-marker-reference.wav"
    _wav(reference, frames=8000 * 15)
    values = {
        "engine": "qwen3_tts", "authorized": True, "reference_path": reference,
        "text": TEXT, "model_dir": model, "python_executable": python,
        "workspace_root": workspace, "timeout_seconds": 30,
        "evidence_mode": "fixture", "clock": lambda: 0.0,
    }
    return tmp_path, values


def _runs(root):
    return tuple(root.glob("jarvis-voice-lab-*"))


def _complete(request, *, rate=8000):
    directory = Path(request["output_dir"])
    for index, _part in enumerate(request["chunks"]):
        _wav(directory / f"part-{index:04d}.wav", rate=rate, frames=13 + index,
             value=300 + index)
    return {
        "batch_version": lab_batch.BATCH_VERSION, "run_id": request["run_id"],
        "engine": request["engine"], "status": "completed",
        "part_count": len(request["chunks"]), "completed_parts": len(request["chunks"]),
        "text_sha256": hashlib.sha256(request["text"].encode()).hexdigest(),
        "part_text_sha256": [hashlib.sha256(part.encode()).hexdigest()
                             for part in request["chunks"]],
    }


def _run(campaign, *, worker=_complete, **changes):
    _, supplied = campaign
    return lab_batch.run_voice_lab_batch(**{**supplied, "fixture_worker": worker, **changes})


def _forbid_side_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid or unconsented campaign touched files or launched a child")

    monkeypatch.setattr(lab_batch, "_plain_path", forbidden)
    monkeypatch.setattr(lab_batch.tempfile, "mkdtemp", forbidden)
    monkeypatch.setattr(lab_batch.subprocess, "Popen", forbidden)


@pytest.mark.parametrize("consent", [None, False, 0, 1, "true", [], {}])
def test_missing_consent_precedes_any_io_or_child(campaign, monkeypatch, consent):
    _forbid_side_effects(monkeypatch)
    with pytest.raises(ValueError, match="^authorization_required$"):
        _run(campaign, authorized=consent)


@pytest.mark.parametrize("changes", [
    {"engine": "private-marker"}, {"engine": []}, {"device": "private-marker"},
    {"text": ""}, {"text": "x" * 6001}, {"text": "private-marker\x00"},
    {"text": "private-marker\u202e"}, {"text": "private-marker\ud800"},
    {"timeout_seconds": 0}, {"timeout_seconds": 1801}, {"timeout_seconds": True},
    {"timeout_seconds": float("nan")}, {"timeout_seconds": float("inf")},
    {"cancelled": False}, {"clock": 1}, {"clock": lambda: float("nan")},
    {"voice_profile": "private-marker"}, {"reference_start_seconds": -1},
    {"reference_duration_seconds": 2}, {"reference_transcript": "private-marker"},
    {"transcript_confirmed": 1}, {"seed": -1}, {"seed": 2**32},
    {"evidence_mode": "private-marker"}, {"evidence_mode": "model_real"},
    {"fixture_worker": False}, {"fixture_worker": None},
])
def test_invalid_pure_configuration_precedes_any_io_or_child(campaign, monkeypatch, changes):
    _forbid_side_effects(monkeypatch)
    with pytest.raises(ValueError) as error:
        _run(campaign, **changes)
    assert "private-marker" not in str(error.value)


def test_preflight_missing_input_creates_no_run_or_child(campaign, monkeypatch):
    root, _ = campaign
    monkeypatch.setattr(lab_batch.subprocess, "Popen",
                        lambda *a, **kw: pytest.fail("bad preflight launched a child"))
    with pytest.raises(ValueError, match="^local_batch_preflight_refused$"):
        _run(campaign, reference_path=root / "private-marker-missing.wav")
    assert not _runs(root)
    assert not tuple(root.rglob("*.db"))


def test_initial_cancel_does_not_touch_inputs_or_create_run(campaign, monkeypatch):
    _forbid_side_effects(monkeypatch)
    result = _run(campaign, cancelled=lambda: True)
    assert result.status == result.reason == "cancelled"
    assert result.output_path is None and result.completed_parts == 0


def test_success_preserves_exact_hashes_counts_pcm_and_private_metadata(campaign):
    root, supplied = campaign
    result = _run(campaign)
    assert result.status == "completed" and result.evidence_mode == "fixture"
    assert result.reason == "fixture_only"
    assert result.part_count == result.completed_parts > 1
    assert result.text_sha256 == hashlib.sha256(TEXT.encode()).hexdigest()
    parts = lab_batch.segment_text(TEXT)
    assert result.part_text_sha256 == tuple(hashlib.sha256(part.encode()).hexdigest()
                                           for part in parts)
    output = Path(result.output_path)
    assert output.parent.parent == root and output.name == "sample.wav"
    with wave.open(str(output), "rb") as audio:
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2
        assert audio.getframerate() == 8000
        raw = audio.readframes(audio.getnframes())
    expected = b"".join(struct.pack("<h", 300 + index) * (13 + index)
                        for index in range(len(parts)))
    assert raw == expected
    assert result.output_digest == hashlib.sha256(output.read_bytes()).hexdigest()
    assert not (output.parent / "worker-status.tmp").exists()
    metadata = json.dumps(result.metadata())
    assert result.run_id in metadata
    assert result.text_sha256 not in metadata and result.output_digest not in metadata
    assert not any(part_hash in metadata for part_hash in result.part_text_sha256)
    assert "private-marker" not in metadata and str(supplied["workspace_root"]) not in metadata
    assert TEXT not in metadata and "output_path" not in metadata
    assert result.metadata()["batch_mode"] is True
    assert result.metadata()["voice_quality_approved"] is False
    assert not tuple(root.rglob("*.db"))


def test_full_public_text_bound_is_supported_without_shortening(campaign):
    observed = []

    def worker(request):
        observed.append(request)
        return _complete(request)

    result = _run(campaign, worker=worker, text="x" * 6000)
    assert result.status == "completed"
    assert len(observed) == 1 and observed[0]["text"] == "x" * 6000
    assert "".join(observed[0]["chunks"]) == "x" * 6000
    assert result.part_count == result.completed_parts == 10


@pytest.mark.parametrize("mutate", [
    lambda value: value.update(run_id="private-marker"),
    lambda value: value.update(engine="chatterbox_pt_br"),
    lambda value: value.update(batch_version="private-marker"),
    lambda value: value.update(part_count=True),
    lambda value: value.update(completed_parts=True),
    lambda value: value.update(part_count=value["part_count"] + 1),
    lambda value: value.update(completed_parts=value["completed_parts"] - 1),
    lambda value: value.update(text_sha256="0" * 64),
    lambda value: value.update(part_text_sha256=list(reversed(value["part_text_sha256"]))),
    lambda value: value.update(part_text_sha256=[value["part_text_sha256"][0]]),
    lambda value: value.update(private_marker="private-marker"),
])
def test_untrusted_success_manifest_must_bind_exact_campaign(campaign, mutate):
    root, _ = campaign

    def worker(request):
        response = _complete(request)
        mutate(response)
        return response

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.output_path is None
    assert result.reason in {"worker_binding_mismatch", "batch_manifest_refused"}
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))


@pytest.mark.parametrize("progress", [True, -1, 999, "private-marker", None, [], {}])
def test_failed_worker_cannot_forge_completed_part_progress(campaign, progress):
    def worker(request):
        return {"batch_version": lab_batch.BATCH_VERSION, "run_id": request["run_id"],
                "engine": request["engine"], "status": "failed", "reason": "private-marker",
                "completed_parts": progress}

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.reason == "worker_failed"
    assert result.completed_parts == 0 and result.output_path is None
    assert "private-marker" not in json.dumps(result.metadata())


def test_failed_worker_bounded_progress_is_preserved(campaign):
    def worker(request):
        return {"batch_version": lab_batch.BATCH_VERSION, "run_id": request["run_id"],
                "engine": request["engine"], "status": "failed",
                "reason": "sdk_unavailable", "completed_parts": 1}

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.completed_parts == 1
    assert result.reason == "sdk_unavailable" and result.output_path is None


@pytest.mark.parametrize("callback_result", [None, [], "private-marker", {"x": "x" * 4096},
                                             {"x": float("nan")}])
def test_fixture_metadata_is_bounded_and_never_echoed(campaign, callback_result):
    result = _run(campaign, worker=lambda request: callback_result)
    assert result.status == "failed" and result.output_path is None
    assert "private-marker" not in json.dumps(result.metadata())


@pytest.mark.parametrize("mode", ["cancel", "late"])
def test_fixture_return_after_cancel_or_single_deadline_never_publishes_final(campaign, mode):
    root, _ = campaign
    control = {"time": 0.0, "cancelled": False}

    def worker(request):
        response = _complete(request)
        if mode == "cancel":
            control["cancelled"] = True
        else:
            control["time"] = 30.0
        return response

    result = _run(campaign, worker=worker, clock=lambda: control["time"],
                  cancelled=lambda: control["cancelled"])
    assert result.status == ("cancelled" if mode == "cancel" else "timed_out")
    assert result.output_path is None
    assert not tuple(root.rglob("sample.wav"))


def test_fixture_request_mutation_cannot_change_parent_plan(campaign):
    root, _ = campaign

    def worker(request):
        response = _complete(request)
        request["chunks"][0] = "private-marker"
        response["part_text_sha256"][0] = hashlib.sha256(b"private-marker").hexdigest()
        return response

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.reason == "batch_manifest_refused"
    assert not tuple(root.rglob("sample.wav"))


def test_heterogeneous_part_rates_refuse_aggregate(campaign):
    root, _ = campaign

    def worker(request):
        response = _complete(request)
        _wav(Path(request["output_dir"]) / "part-0001.wav", rate=16000)
        return response

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.output_path is None
    assert not tuple(root.rglob("sample.wav"))


class FakeProcess:
    """No executable runs; emulate parent Popen communication and kill semantics."""

    def __init__(self, command, *, stdout, response=None, returncode=0, timeout_once=False,
                 on_communicate=None, **kwargs):
        self.command = command
        self.kwargs = kwargs
        self.stdout = stdout
        self.response = response
        self.exit_code = returncode
        self.returncode = None
        self.timeout_once = timeout_once
        self.on_communicate = on_communicate
        self.calls = []
        self.kill_count = 0
        self.payload = None

    def communicate(self, input=None, timeout=None):
        self.calls.append((input, timeout))
        if self.kill_count:
            self.returncode = -9
            return None, None
        if input is not None:
            assert self.payload is None
            self.payload = json.loads(input)
        if self.on_communicate is not None:
            self.on_communicate(self)
        if self.timeout_once:
            self.timeout_once = False
            raise subprocess.TimeoutExpired(self.command, timeout)
        raw = self.response(self.payload) if callable(self.response) else self.response
        if raw is None:
            raw = json.dumps(_complete(self.payload)).encode()
        self.stdout.write(raw)
        self.stdout.flush()
        self.returncode = self.exit_code
        return None, None

    def poll(self):
        return self.returncode

    def kill(self):
        self.kill_count += 1

    def wait(self, timeout=None):
        self.returncode = -9
        return self.returncode


def _fake_popen(monkeypatch, **options):
    processes = []

    def launch(command, **kwargs):
        process = FakeProcess(command, **kwargs, **options)
        processes.append(process)
        return process

    monkeypatch.setattr(lab_batch.subprocess, "Popen", launch)
    return processes


def _supervised(campaign, **changes):
    _, values = campaign
    return lab_batch.run_voice_lab_batch(**{**values, "evidence_mode": "model_real", **changes})


def test_supervision_simulation_single_child_isolated_env_and_resumed_stdin(campaign, monkeypatch):
    root, supplied = campaign
    monkeypatch.setenv("OPENAI_API_KEY", "private-marker")
    monkeypatch.setenv("HTTPS_PROXY", "private-marker")
    processes = _fake_popen(monkeypatch, timeout_once=True)
    result = _supervised(campaign)
    assert result.status == "completed" and result.reason == "local_sample_generated"
    # This label describes the exercised branch, not actual model execution.
    assert result.evidence_mode == "model_real"
    assert len(processes) == 1
    process = processes[0]
    assert process.command[0] == str(supplied["python_executable"])
    assert process.command[1] == "-I" and process.command[2].endswith("worker.py")
    assert len(process.calls) == 2 and process.calls[0][0] is not None
    assert process.calls[1][0] is None and process.kill_count == 0
    assert process.kwargs["stdin"] == subprocess.PIPE
    assert process.kwargs["stderr"] == subprocess.DEVNULL
    assert process.kwargs["cwd"].parent == root
    assert "OPENAI_API_KEY" not in process.kwargs["env"]
    assert "HTTPS_PROXY" not in process.kwargs["env"]
    assert process.kwargs["env"]["HF_HUB_OFFLINE"] == "1"
    assert not tuple(root.rglob("worker-status.tmp"))


@pytest.mark.parametrize("mode", ["cancel", "timeout"])
def test_supervision_kills_single_live_child_on_cancel_or_shared_deadline(
    campaign, monkeypatch, mode,
):
    root, _ = campaign
    control = {"time": 0.0, "cancelled": False}

    def boundary(process):
        if mode == "timeout":
            control["time"] = 30.0
        else:
            control["cancelled"] = True

    processes = _fake_popen(monkeypatch, timeout_once=True, on_communicate=boundary)
    result = _supervised(campaign, clock=lambda: control["time"],
                         cancelled=lambda: control["cancelled"])
    assert result.status == ("cancelled" if mode == "cancel" else "timed_out")
    assert len(processes) == 1 and processes[0].kill_count == 1
    assert processes[0].returncode == -9 and result.output_path is None
    assert not tuple(root.rglob("worker-status.tmp"))
    assert not tuple(root.rglob("sample.wav"))


def test_child_start_failure_is_sanitized_and_spool_is_removed(campaign, monkeypatch):
    root, _ = campaign
    launched = []

    def launch(*args, **kwargs):
        launched.append(args)
        raise OSError("private-marker executable launch failed")

    monkeypatch.setattr(lab_batch.subprocess, "Popen", launch)
    result = _supervised(campaign)
    assert len(launched) == 1 and result.status == "failed"
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("worker-status.tmp"))


def test_nonzero_child_exit_never_returns_output(campaign, monkeypatch):
    root, _ = campaign
    processes = _fake_popen(monkeypatch, returncode=17, response=b"private-marker stderr")
    result = _supervised(campaign)
    assert len(processes) == 1 and result.status == "failed"
    assert result.reason == "worker_failed" and result.output_path is None
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))
    assert not tuple(root.rglob("worker-status.tmp"))


@pytest.mark.parametrize("raw", [
    b"", b"private-marker", b"[]", b"null", b"\xff", b"\xef\xbb\xbf{}",
    b'{"status":"completed","status":"failed"}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":"' + b"x" * 4096 + b'"}',
])
def test_real_branch_spool_metadata_is_strict_bounded_and_private(campaign, monkeypatch, raw):
    root, _ = campaign
    processes = _fake_popen(monkeypatch, response=raw)
    result = _supervised(campaign)
    assert len(processes) == 1 and result.status == "failed"
    assert result.output_path is None and "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))
    assert not tuple(root.rglob("worker-status.tmp"))


def test_spool_growth_while_child_alive_is_bounded_and_killed(campaign, monkeypatch):
    root, _ = campaign

    def fill(process):
        process.stdout.write(b"private-marker" + b"x" * 4096)
        process.stdout.flush()

    processes = _fake_popen(monkeypatch, timeout_once=True, on_communicate=fill)
    result = _supervised(campaign)
    assert result.status == "failed" and result.output_path is None
    assert len(processes) == 1 and processes[0].kill_count == 1
    assert not tuple(root.rglob("worker-status.tmp"))


@pytest.mark.parametrize("mode", ["late", "cancel", "inspect_fail"])
def test_post_assembly_refusal_leaves_no_published_final(campaign, monkeypatch, mode):
    root, _ = campaign
    original = lab_batch.assemble_wavs
    control = {"time": 0.0, "cancelled": False}

    def assembly(*args, **kwargs):
        result = original(*args, **kwargs)
        if mode == "late":
            control["time"] = 30.0
        elif mode == "cancel":
            control["cancelled"] = True
        return result

    monkeypatch.setattr(lab_batch, "assemble_wavs", assembly)
    if mode == "inspect_fail":
        monkeypatch.setattr(lab_batch, "inspect_wav", lambda path: (1, 2, 3))
    result = _run(campaign, clock=lambda: control["time"],
                  cancelled=lambda: control["cancelled"])
    assert result.status == {"late": "timed_out", "cancel": "cancelled",
                             "inspect_fail": "failed"}[mode]
    assert result.output_path is None
    assert not tuple(root.rglob("sample.wav"))


def test_deadline_includes_text_planning_without_reset_or_file_inspection(campaign, monkeypatch):
    root, _ = campaign
    original = lab_batch.segment_text
    control = {"time": 0.0}

    def plan(text):
        chunks = original(text)
        control["time"] = 30.0
        return chunks

    monkeypatch.setattr(lab_batch, "segment_text", plan)
    monkeypatch.setattr(lab_batch, "_plain_path",
                        lambda *a, **kw: pytest.fail("expired planning inspected input files"))
    result = _run(campaign, clock=lambda: control["time"])
    assert result.status == "timed_out" and result.reason == "deadline_exceeded"
    assert result.output_path is None and not _runs(root)


@pytest.mark.parametrize("mode", ["late", "cancel"])
def test_post_publication_boundary_removes_only_owned_final(campaign, monkeypatch, mode):
    root, _ = campaign
    original = lab_batch.os.link
    control = {"time": 0.0, "cancelled": False}

    def publish(source, target, *args, **kwargs):
        result = original(source, target, *args, **kwargs)
        if Path(target).name == "sample.wav":
            if mode == "late":
                control["time"] = 30.0
            else:
                control["cancelled"] = True
        return result

    monkeypatch.setattr(lab_batch.os, "link", publish)
    result = _run(campaign, clock=lambda: control["time"],
                  cancelled=lambda: control["cancelled"])
    assert result.status == ("timed_out" if mode == "late" else "cancelled")
    assert result.output_path is None
    assert not tuple(root.rglob("sample.wav"))


def test_staging_cleanup_failure_cannot_publish_success_or_leak_private_error(
    campaign, monkeypatch,
):
    root, _ = campaign
    original = Path.unlink

    def refuse_staging(path, *args, **kwargs):
        if path.name == ".batch-aggregate.wav":
            raise PermissionError("private-marker staging cleanup failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refuse_staging)
    result = _run(campaign)
    assert result.status == "failed" and result.output_path is None
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))


def test_child_termination_failure_preserves_sanitized_timeout_result(campaign, monkeypatch):
    root, _ = campaign
    control = {"time": 0.0}
    processes = _fake_popen(
        monkeypatch, timeout_once=True,
        on_communicate=lambda process: control.update(time=30.0),
    )

    def kill_error(process):
        raise OSError("private-marker child termination failed")

    monkeypatch.setattr(lab_batch, "_stop", kill_error)
    result = _supervised(campaign, clock=lambda: control["time"])
    assert result.status != "completed" and result.output_path is None
    assert len(processes) == 1
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))


def test_spool_cleanup_error_never_escapes_as_a_private_exception(campaign, monkeypatch):
    root, _ = campaign
    original = Path.unlink
    processes = _fake_popen(monkeypatch)

    def refuse_spool(path, *args, **kwargs):
        if path.name == "worker-status.tmp":
            raise PermissionError("private-marker spool cleanup failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", refuse_spool)
    result = _supervised(campaign)
    assert len(processes) == 1
    assert "private-marker" not in json.dumps(result.metadata())
    if result.status == "completed":
        assert result.output_path is not None
        assert lab_batch.inspect_wav(Path(result.output_path))[2] == 1
    else:
        assert result.output_path is None
    # A private diagnostic spool can remain; deletion/retention is not promised.
    assert tuple(root.rglob("worker-status.tmp"))


def test_foreign_preexisting_final_is_never_overwritten_or_deleted(campaign):
    root, _ = campaign
    outputs = []

    def worker(request):
        response = _complete(request)
        output = Path(request["output_dir"]) / "sample.wav"
        output.write_bytes(b"unrelated preexisting artifact")
        outputs.append(output)
        return response

    result = _run(campaign, worker=worker)
    assert result.status == "failed" and result.output_path is None
    assert len(outputs) == 1 and outputs[0].read_bytes() == b"unrelated preexisting artifact"
    assert not tuple(root.rglob(".batch-aggregate.wav"))


@pytest.mark.parametrize("clock_case", ["private_exception", "overflowing_integer"])
def test_initial_clock_failures_are_sanitized_before_io(campaign, monkeypatch, clock_case):
    _forbid_side_effects(monkeypatch)

    def clock():
        if clock_case == "private_exception":
            raise RuntimeError("private-marker initial clock callback failed")
        return 10**400

    with pytest.raises(ValueError, match="^invalid_clock$") as error:
        _run(campaign, clock=clock)
    assert "private-marker" not in str(error.value)
    assert error.value.__cause__ is None


@pytest.mark.parametrize("poll_case", ["still_live", "private_exception"])
def test_unconfirmed_child_termination_cannot_publish_final(campaign, monkeypatch, poll_case):
    root, _ = campaign
    processes = []

    def poll():
        if poll_case == "private_exception":
            raise RuntimeError("private-marker process poll failed")
        return None

    def launch(command, **kwargs):
        process = FakeProcess(command, **kwargs)
        process.poll = poll
        processes.append(process)
        return process

    monkeypatch.setattr(lab_batch.subprocess, "Popen", launch)
    result = _supervised(campaign)
    assert result.status == "failed" and result.output_path is None
    assert len(processes) == 1
    assert "private-marker" not in json.dumps(result.metadata())
    assert not tuple(root.rglob("sample.wav"))


@pytest.mark.parametrize("cleanup_case", ["late", "cancel"])
def test_post_spool_cleanup_boundary_refuses_late_or_cancelled_success(
    campaign, monkeypatch, cleanup_case,
):
    root, _ = campaign
    control = {"time": 0.0, "cancelled": False}
    original = Path.unlink
    observed = []

    def cleanup(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.name == "worker-status.tmp":
            observed.append(path)
            if cleanup_case == "late":
                control["time"] = 31.0
            else:
                control["cancelled"] = True
        return result

    monkeypatch.setattr(Path, "unlink", cleanup)
    result = _run(campaign, clock=lambda: control["time"],
                  cancelled=lambda: control["cancelled"])
    assert len(observed) == 1
    assert result.status == ("timed_out" if cleanup_case == "late" else "cancelled")
    assert result.reason == ("deadline_exceeded" if cleanup_case == "late" else "cancelled")
    assert result.output_path is None
    assert not tuple(root.rglob("sample.wav"))
