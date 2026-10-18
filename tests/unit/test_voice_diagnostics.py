"""Private phase metadata proof with synthetic SDKs; no process/model/GPU runs."""

from __future__ import annotations

import io
import json
import math
import os
import subprocess
import sys
import types
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import lab_batch, worker

IDENTITY = {"run_id": "ac" * 16, "engine": "qwen3_tts", "device": "cpu"}


def _read(directory, **changes):
    return worker.read_voice_diagnostics(directory, **{**IDENTITY, **changes})


def _event(sequence=0, phase="imports", event="started", part_index=None, **changes):
    return {"schema_version": worker.DIAGNOSTICS_VERSION, "sequence": sequence,
            **IDENTITY, "phase": phase, "event": event, "elapsed_seconds": float(sequence),
            "part_index": part_index, "resources": {}, **changes}


def _write(directory, events):
    path = directory / worker.DIAGNOSTICS_NAME
    path.write_bytes(b"".join(json.dumps(event).encode() + b"\n" for event in events))
    return path


def test_writer_leaves_started_phase_readable_without_close_or_completion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    times = iter([10.0, 10.25, 11.0, 12.0])
    recorder = worker.VoiceDiagnostics(tmp_path, **IDENTITY, clock=lambda: next(times))
    try:
        recorder.emit("imports", "started")
        recorder.emit("imports", "completed")
        recorder.emit("model_load", "started")
        events = _read(tmp_path, part_count=1)
        assert [event["elapsed_seconds"] for event in events] == [0.25, 1.0, 2.0]
        assert (events[-1]["phase"], events[-1]["event"]) == ("model_load", "started")
        assert recorder.path.stat().st_size <= 32768
    finally:
        recorder.close()
    assert _read(tmp_path) == events


def test_writer_uses_binary_lf_bytes_without_windows_text_translation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    recorder = worker.VoiceDiagnostics(tmp_path, **IDENTITY)
    try:
        recorder.emit("imports", "started")
        raw = recorder.path.read_bytes()
        assert raw.endswith(b"\n") and b"\r" not in raw
        assert recorder.size == len(raw) == recorder.path.stat().st_size
        recorder.emit("imports", "completed")
        assert len(_read(tmp_path)) == 2
        assert recorder.size == len(recorder.path.read_bytes())
    finally:
        recorder.close()


def test_writer_exclusive_creation_preserves_existing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / worker.DIAGNOSTICS_NAME
    path.write_bytes(b"foreign unchanged")
    with pytest.raises(FileExistsError):
        worker.VoiceDiagnostics(tmp_path, **IDENTITY)
    assert path.read_bytes() == b"foreign unchanged"


def test_writer_rejects_different_directory_before_creation(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="diagnostic_cwd_mismatch"):
        worker.VoiceDiagnostics(elsewhere, **IDENTITY)
    assert not (elsewhere / worker.DIAGNOSTICS_NAME).exists()


def test_writer_rejects_foreign_growth_without_overwriting_it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    recorder = worker.VoiceDiagnostics(tmp_path, **IDENTITY)
    try:
        recorder.emit("imports", "started")
        with recorder.path.open("ab") as handle:
            handle.write(b"foreign unchanged")
        before = recorder.path.read_bytes()
        with pytest.raises(ValueError, match="diagnostic_file_changed"):
            recorder.emit("imports", "completed")
        assert recorder.path.read_bytes() == before
    finally:
        recorder.close()


@pytest.mark.parametrize("boundary", ["events", "bytes"])
def test_writer_enforces_hard_limits_before_writing(tmp_path, monkeypatch, boundary):
    monkeypatch.chdir(tmp_path)
    recorder = worker.VoiceDiagnostics(tmp_path, **IDENTITY)
    try:
        if boundary == "events":
            monkeypatch.setattr(worker, "MAX_DIAGNOSTICS_EVENTS", 1)
        recorder.emit("imports", "started")
        before = recorder.path.read_bytes()
        if boundary == "bytes":
            monkeypatch.setattr(worker, "MAX_DIAGNOSTICS_BYTES", len(before))
        with pytest.raises(ValueError, match="diagnostic_(event|byte)_limit"):
            recorder.emit("imports", "completed")
        assert recorder.path.read_bytes() == before
    finally:
        recorder.close()


@pytest.mark.parametrize("clock", [lambda: True, lambda: float("nan"),
                                   lambda: float("inf"), lambda: 10**400])
def test_invalid_initial_clock_never_creates_artifact(tmp_path, monkeypatch, clock):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="invalid_diagnostic_clock"):
        worker.VoiceDiagnostics(tmp_path, **IDENTITY, clock=clock)
    assert not (tmp_path / worker.DIAGNOSTICS_NAME).exists()


def test_decreasing_clock_is_refused_before_second_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    times = iter([10.0, 12.0, 11.0])
    recorder = worker.VoiceDiagnostics(tmp_path, **IDENTITY, clock=lambda: next(times))
    try:
        recorder.emit("imports", "started")
        with pytest.raises(ValueError, match="invalid_diagnostic_clock"):
            recorder.emit("imports", "completed")
        assert len(_read(tmp_path)) == 1
    finally:
        recorder.close()


@pytest.mark.parametrize("changes", [
    {"schema_version": "other"}, {"sequence": True}, {"sequence": 2},
    {"run_id": "bd" * 16}, {"engine": "chatterbox_pt_br"}, {"device": "cuda:0"},
    {"phase": "PRIVATE_TEXT"}, {"event": "PRIVATE_TEXT"}, {"part_index": 0},
    {"elapsed_seconds": -1}, {"elapsed_seconds": True}, {"elapsed_seconds": float("nan")},
    {"elapsed_seconds": float("inf")}, {"elapsed_seconds": 86401},
    {"resources": {"path": "PRIVATE_PATH"}}, {"resources": {"cuda_allocated_bytes": 0}},
    {"extra": "PRIVATE_SECRET"}, {"phase": "generate", "part_index": True},
    {"phase": "generate", "part_index": -1}, {"phase": "generate", "part_index": 16},
    {"event": "failed"}, {"phase": "completion"},
])
def test_reader_rejects_schema_binding_clock_and_resource_forgery(tmp_path, changes):
    _write(tmp_path, [_event(**changes)])
    with pytest.raises(ValueError):
        _read(tmp_path)


@pytest.mark.parametrize("raw", [
    b"", b"{}", b"{}\n", b"[]\n", b"\xef\xbb\xbf{}\n", b"\xff\n",
    b"{\"schema_version\":1,\"schema_version\":2}\n", b"{\"x\":NaN}\n",
    b"x" * 32769 + b"\n", b"{}\n" * 81,
], ids=["empty", "missing-newline", "empty-object", "array", "bom", "non-ascii",
        "duplicate-field", "non-finite", "oversize", "too-many-events"])
def test_reader_refuses_malformed_or_unbounded_stream(tmp_path, raw):
    (tmp_path / worker.DIAGNOSTICS_NAME).write_bytes(raw)
    with pytest.raises(ValueError):
        _read(tmp_path)


def _complete_events(parts=1):
    values = [("imports", "started", None), ("imports", "completed", None),
              ("model_load", "started", None), ("model_load", "completed", None)]
    for index in range(parts):
        values += [("generate", "started", index), ("generate", "completed", index),
                   ("save", "started", index), ("save", "completed", index)]
    values += [("completion", "completed", None)]
    return [_event(sequence, phase, event, index)
            for sequence, (phase, event, index) in enumerate(values)]


def test_reader_binds_pairs_part_order_and_terminal_completion(tmp_path):
    _write(tmp_path, _complete_events(2))
    assert len(_read(tmp_path, part_count=2)) == 13
    with pytest.raises(ValueError, match="invalid_diagnostic_completion"):
        _read(tmp_path, part_count=3)
    with pytest.raises(ValueError, match="invalid_diagnostic_part_binding"):
        _read(tmp_path, part_count=1)


@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
def test_maximum_sixteen_part_plan_fits_private_diagnostic_limits(tmp_path, monkeypatch, device):
    monkeypatch.chdir(tmp_path)
    cuda = types.SimpleNamespace(
        is_initialized=lambda: True, memory_allocated=lambda _: 2**63 - 1,
        memory_reserved=lambda _: 2**63 - 1, max_memory_allocated=lambda _: 2**63 - 1)
    recorder = worker.VoiceDiagnostics(tmp_path, **{**IDENTITY, "device": device})
    try:
        for event in _complete_events(16):
            recorder.emit(event["phase"], event["event"], part_index=event["part_index"],
                          torch_module=types.SimpleNamespace(cuda=cuda))
    finally:
        recorder.close()
    events = _read(tmp_path, device=device, part_count=16)
    assert len(events) == 69 <= worker.MAX_DIAGNOSTICS_EVENTS
    assert recorder.path.stat().st_size <= worker.MAX_DIAGNOSTICS_BYTES
    assert events[-1]["event"] == "completed"


@pytest.mark.parametrize("mutation", ["unpaired", "wrong_part", "reordered", "after_terminal"])
def test_reader_refuses_plausible_but_inconsistent_phase_stream(tmp_path, mutation):
    events = _complete_events()
    if mutation == "unpaired":
        events[5]["event"] = "started"
    elif mutation == "wrong_part":
        events[5]["part_index"] = 1
    elif mutation == "reordered":
        events[4]["phase"] = "save"
    else:
        events.append(_event(9))
    _write(tmp_path, events)
    with pytest.raises(ValueError):
        _read(tmp_path)


@pytest.mark.parametrize("invalid", [True, 0, 17, "1"])
def test_reader_rejects_invalid_expected_part_count(tmp_path, invalid):
    with pytest.raises(ValueError, match="invalid_diagnostic_part_count"):
        _read(tmp_path, part_count=invalid)


def test_cuda_metrics_are_numeric_only_and_do_not_initialize_device(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cuda = types.SimpleNamespace(is_initialized=lambda: True, memory_allocated=lambda _: 10,
                                 memory_reserved=lambda _: 20, max_memory_allocated=lambda _: 30)
    recorder = worker.VoiceDiagnostics(tmp_path, **{**IDENTITY, "device": "cuda:0"})
    try:
        recorder.emit("imports", "started", torch_module=types.SimpleNamespace(cuda=cuda))
    finally:
        recorder.close()
    event = _read(tmp_path, device="cuda:0")[0]
    assert event["resources"] == {"cuda_allocated_bytes": 10, "cuda_reserved_bytes": 20,
                                  "cuda_peak_allocated_bytes": 30}


@pytest.mark.parametrize("case", ["not_initialized", "missing_cuda"])
def test_cuda_telemetry_absence_is_empty_not_a_new_device_operation(tmp_path, monkeypatch, case):
    monkeypatch.chdir(tmp_path)
    cuda = types.SimpleNamespace(is_initialized=lambda: False)
    torch = types.SimpleNamespace(cuda=cuda) if case == "not_initialized" else object()
    recorder = worker.VoiceDiagnostics(tmp_path, **{**IDENTITY, "device": "cuda:0"})
    try:
        recorder.emit("imports", "started", torch_module=torch)
    finally:
        recorder.close()
    assert _read(tmp_path, device="cuda:0")[0]["resources"] == {}


@pytest.fixture
def synthetic_worker(tmp_path, monkeypatch):
    """SDK doubles execute exact production sequencing, never heavyweight imports."""
    model = tmp_path / "model"
    model.mkdir()
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"private fixture only")
    output = tmp_path / "run"
    output.mkdir()
    monkeypatch.chdir(output)
    request = {"batch_version": worker.BATCH_VERSION, "authorized": True, **IDENTITY,
               "text": "  First.\nSecond exact.  ", "chunks": ["  First.\n", "Second exact.  "],
               "reference_path": str(reference), "model_dir": str(model), "output_dir": str(output)}
    seen = {"loads": 0, "texts": []}

    class Audio(list):
        ndim = 1

        def __ne__(self, value):
            return [item != value for item in self]

    class Model:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            seen["loads"] += 1
            if seen.get("load_error"):
                raise RuntimeError("PRIVATE_MODEL_PATH")
            return cls()

        def generate_voice_clone(self, **kwargs):
            seen["texts"].append(kwargs["text"])
            if seen.get("fail_part") == len(seen["texts"]):
                raise RuntimeError("PRIVATE_TEXT_SECRET")
            return [Audio([0.1, -0.2])], 8000

    def write(handle, audio, rate, **kwargs):
        with wave.open(handle, "wb") as wav:
            wav.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x01\x00" * len(audio))

    monkeypatch.setitem(sys.modules, "numpy", types.SimpleNamespace(
        asarray=lambda audio: audio, any=any, clip=lambda audio, *args: audio,
        isfinite=lambda audio: types.SimpleNamespace(all=lambda: all(map(math.isfinite, audio)))))
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(
        float32="float32", bfloat16="bfloat16"))
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=write))
    monkeypatch.setitem(sys.modules, "qwen_tts", types.SimpleNamespace(Qwen3TTSModel=Model))
    monkeypatch.setattr(worker, "_deny_network", lambda: None)
    return request, seen, output


def _main(request, monkeypatch, *, diagnostics):
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(
        buffer=io.BytesIO(json.dumps(request).encode())))
    return worker.main(diagnostics=diagnostics)


@pytest.mark.parametrize("diagnostics", [False, True])
def test_main_preserves_audio_and_stdout_contract_with_opt_in(
    synthetic_worker, monkeypatch, capsys, diagnostics,
):
    request, seen, directory = synthetic_worker
    assert _main(request, monkeypatch, diagnostics=diagnostics) == 0
    raw = capsys.readouterr().out
    result = json.loads(raw)
    assert result["status"] == "completed" and result["completed_parts"] == 2
    assert set(result) == {"run_id", "engine", "status", "batch_version", "part_count",
                           "completed_parts", "text_sha256", "part_text_sha256"}
    assert seen["loads"] == 1 and seen["texts"] == request["chunks"]
    assert len(tuple(directory.glob("part-*.wav"))) == 2
    assert not (directory / "sample.wav").exists()
    assert request["text"] not in raw and str(directory) not in raw
    assert (directory / worker.DIAGNOSTICS_NAME).exists() is diagnostics
    if diagnostics:
        events = _read(directory, part_count=2)
        assert [(item["phase"], item["event"], item["part_index"]) for item in events] == [
            (item["phase"], item["event"], item["part_index"])
            for item in _complete_events(2)]
        assert all(first["elapsed_seconds"] <= second["elapsed_seconds"]
                   for first, second in zip(events, events[1:]))
        assert "PRIVATE" not in (directory / worker.DIAGNOSTICS_NAME).read_text()


@pytest.mark.parametrize("failure", ["imports", "load", "generate"])
def test_failure_sidecar_retains_last_started_phase_without_audio_success(
    synthetic_worker, monkeypatch, capsys, failure,
):
    request, seen, directory = synthetic_worker
    if failure == "imports":
        monkeypatch.setitem(sys.modules, "qwen_tts", None)
    elif failure == "load":
        seen["load_error"] = True
    else:
        seen["fail_part"] = 2
    assert _main(request, monkeypatch, diagnostics=True) == 0
    raw = capsys.readouterr().out
    result = json.loads(raw)
    assert result["status"] == "failed"
    events = _read(directory, part_count=2)
    assert (events[-1]["phase"], events[-1]["event"]) == ("completion", "failed")
    assert events[-2]["phase"] == {"imports": "imports", "load": "model_load",
                                   "generate": "generate"}[failure]
    assert events[-2]["event"] == "started"
    assert "PRIVATE" not in raw and "PRIVATE" not in json.dumps(events)
    assert not (directory / "sample.wav").exists()


def test_diagnostic_write_failure_does_not_retry_or_promote_audio(
    synthetic_worker, monkeypatch, capsys,
):
    request, seen, directory = synthetic_worker

    def broken(*args, **kwargs):
        raise OSError("PRIVATE_DISK_PATH")

    monkeypatch.setattr(worker.VoiceDiagnostics, "emit", broken)
    assert _main(request, monkeypatch, diagnostics=True) == 0
    raw = capsys.readouterr().out
    assert json.loads(raw)["status"] == "completed"
    assert seen["loads"] == 1 and seen["texts"] == request["chunks"]
    assert "PRIVATE" not in raw and not (directory / "sample.wav").exists()
    with pytest.raises(ValueError):
        _read(directory)


@pytest.mark.parametrize("flag", [None, 1, "true", [], {}])
def test_supervisor_refuses_non_boolean_flag_before_io(monkeypatch, flag):
    monkeypatch.setattr(lab_batch, "_plain_path", lambda *args, **kwargs: pytest.fail("I/O"))
    with pytest.raises(ValueError, match="invalid_diagnostics_flag"):
        lab_batch.run_voice_lab_batch(engine="qwen3_tts", authorized=True,
                                     reference_path=Path("unused"), text="Exact.",
                                     model_dir=Path("unused"), python_executable=Path("unused"),
                                     workspace_root=Path("unused"), diagnostics=flag)


@pytest.mark.parametrize("diagnostics", [False, True])
@pytest.mark.parametrize("terminal", ["timeout", "cancel"])
def test_supervisor_keeps_diagnostic_phase_after_kill_without_relaxing_final(
    tmp_path, monkeypatch, diagnostics, terminal,
):
    """Popen boundary simulation, not a child executable or inference test."""
    monkeypatch.setattr(lab_batch.tempfile, "gettempdir", lambda: str(tmp_path))
    workspace, model = tmp_path / "workspace", tmp_path / "model"
    workspace.mkdir()
    model.mkdir()
    executable = tmp_path / "never-executed"
    executable.write_bytes(b"fixture only")
    reference = tmp_path / "reference.wav"
    with wave.open(str(reference), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x01\x00" * 24000)
    control = {"time": 0.0, "cancelled": False}
    processes = []

    class Process:
        def __init__(self, command, *, cwd, **kwargs):
            self.command, self.cwd = command, cwd
            self.returncode, self.kill_count = None, 0
            self.request = None

        def communicate(self, input=None, timeout=None):
            if self.kill_count:
                self.returncode = -9
                return None, None
            self.request = json.loads(input)
            assert "diagnostics" not in self.request
            if diagnostics:
                previous = Path.cwd()
                try:
                    os.chdir(self.cwd)
                    recorder = worker.VoiceDiagnostics(
                        self.cwd, run_id=self.request["run_id"], engine=self.request["engine"],
                        device=self.request["device"], clock=lambda: control["time"])
                    try:
                        recorder.emit("imports", "started")
                        recorder.emit("imports", "completed")
                        recorder.emit("model_load", "started")
                    finally:
                        recorder.close()
                finally:
                    os.chdir(previous)
            if terminal == "timeout":
                control["time"] = 30.0
            else:
                control["cancelled"] = True
            raise subprocess.TimeoutExpired(self.command, timeout)

        def poll(self):
            return self.returncode

        def kill(self):
            self.kill_count += 1

    def launch(command, **kwargs):
        process = Process(command, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(lab_batch.subprocess, "Popen", launch)
    result = lab_batch.run_voice_lab_batch(
        engine="qwen3_tts", authorized=True, reference_path=reference, text="Exact whole final.",
        model_dir=model, python_executable=executable, workspace_root=workspace,
        reference_duration_seconds=3, timeout_seconds=30, diagnostics=diagnostics,
        clock=lambda: control["time"], cancelled=lambda: control["cancelled"])
    assert result.status == ("timed_out" if terminal == "timeout" else "cancelled")
    assert result.output_path is None and result.completed_parts == 0
    assert len(processes) == 1 and processes[0].kill_count == 1
    process = processes[0]
    assert (process.command[-1] == "--diagnostics") is diagnostics
    assert not tuple(tmp_path.rglob("sample.wav"))
    assert not tuple(tmp_path.rglob("worker-status.tmp"))
    assert (process.cwd / worker.DIAGNOSTICS_NAME).exists() is diagnostics
    if diagnostics:
        events = _read(process.cwd, run_id=result.run_id, part_count=1)
        assert (events[-1]["phase"], events[-1]["event"]) == ("model_load", "started")
    assert "diagnostic" not in json.dumps(result.metadata())
    assert str(tmp_path) not in json.dumps(result.metadata())


@pytest.mark.parametrize("redirection", ["symlink", "reparse", "hardlink"])
def test_reader_refuses_redirected_path_without_platform_privilege(
    tmp_path, monkeypatch, redirection,
):
    path = _write(tmp_path, [_event()])
    original_lstat, original_stat = Path.lstat, Path.stat

    def lstat(candidate, *args, **kwargs):
        info = original_lstat(candidate, *args, **kwargs)
        if candidate != path or redirection == "hardlink":
            return info
        return types.SimpleNamespace(st_mode=0o120777 if redirection == "symlink" else info.st_mode,
                                     st_file_attributes=0x400 if redirection == "reparse" else 0)

    def stat(candidate, *args, **kwargs):
        info = original_stat(candidate, *args, **kwargs)
        if candidate != path or redirection != "hardlink":
            return info
        return types.SimpleNamespace(st_mode=info.st_mode, st_nlink=2)

    monkeypatch.setattr(Path, "lstat", lstat)
    monkeypatch.setattr(Path, "stat", stat)
    with pytest.raises(ValueError):
        _read(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="Windows symlink creation needs external privilege")
def test_reader_and_writer_reject_symlink_without_changing_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "foreign"
    target.write_bytes(b"foreign unchanged")
    (tmp_path / worker.DIAGNOSTICS_NAME).symlink_to(target)
    with pytest.raises((OSError, ValueError)):
        worker.VoiceDiagnostics(tmp_path, **IDENTITY)
    with pytest.raises(ValueError, match="redirected_path_denied"):
        _read(tmp_path)
    assert target.read_bytes() == b"foreign unchanged"
