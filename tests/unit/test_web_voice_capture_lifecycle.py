"""Captured audio is removable only after the owned worker boundary is safe."""

import json
from pathlib import Path

import pytest

from apps.jarvis_api import voice_profile as module
from apps.jarvis_voice_lab import transcribe
from apps.jarvis_voice_lab.worker_lifecycle import WorkerExitUnconfirmed


@pytest.fixture
def capture(tmp_path, monkeypatch):
    original, created = module.tempfile.mkdtemp, []

    def create(**kwargs):
        directory = Path(original(dir=tmp_path, **kwargs))
        created.append(directory)
        return str(directory)

    monkeypatch.setattr(module.tempfile, "mkdtemp", create)
    return created


def draft(kwargs):
    root = kwargs["private_output_root"]
    output = root / "transcript.json"
    output.write_text(json.dumps({"segments": [{"text": "Rascunho revisavel."}]}),
                      encoding="utf-8")
    return {"segments_path": str(output)}


def config(tmp_path):
    # The stub owns transcription; these selections are never opened/executed.
    return module.LocalAsrConfig(tmp_path / "model", tmp_path / "python.exe")


@pytest.mark.parametrize("platform,guarded", [("win32", True), ("linux", False)])
def test_safe_capture_cleanup_and_windows_only_guard(tmp_path, capture, monkeypatch,
                                                    platform, guarded):
    seen = []

    def worker(**kwargs):
        seen.append(kwargs)
        assert kwargs["source"].read_bytes() == b"synthetic capture"
        return draft(kwargs)

    monkeypatch.setattr(module.sys, "platform", platform)
    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    assert module.transcribe_bytes(config(tmp_path), b"synthetic capture", lambda: False) == (
        "Rascunho revisavel."
    )
    assert len(capture) == len(seen) == 1 and not capture[0].exists()
    assert (seen[0].get("confirm_worker_exit") is True) is guarded
    assert "decoding_profile" not in seen[0]  # quality remains the default.


def test_uncertain_worker_retains_capture_and_never_attempts_cleanup(
        tmp_path, capture, monkeypatch):
    failure = WorkerExitUnconfirmed()

    def worker(**kwargs):
        draft(kwargs)
        raise failure

    def forbidden(*args, **kwargs):
        pytest.fail("an unconfirmed worker may still hold captured audio")

    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    monkeypatch.setattr(module.shutil, "rmtree", forbidden)
    with pytest.raises(WorkerExitUnconfirmed) as error:
        module.transcribe_bytes(config(tmp_path), b"retained capture", lambda: False)
    assert error.value is failure and error.value.artifacts_retained is True
    assert capture[0].is_dir() and (capture[0] / "capture.wav").read_bytes() == b"retained capture"
    assert (capture[0] / "transcript.json").exists()
    assert str(error.value) == "local_asr_worker_exit_unconfirmed"


@pytest.mark.parametrize("failure", [InterruptedError("local_asr_cancelled"),
                                    ValueError("local_asr_deadline_or_metadata_limit")])
def test_confirmed_worker_failure_cleans_capture_and_preserves_primary_error(
        tmp_path, capture, monkeypatch, failure):
    def worker(**kwargs):
        draft(kwargs)
        raise failure

    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    with pytest.raises(type(failure)) as error:
        module.transcribe_bytes(config(tmp_path), b"private capture", lambda: False)
    assert error.value is failure and not capture[0].exists()


@pytest.mark.parametrize("primary_failure", [False, True])
def test_cleanup_failure_is_sanitized_and_retains_capture(
        tmp_path, capture, monkeypatch, primary_failure):
    def worker(**kwargs):
        result = draft(kwargs)
        if primary_failure:
            raise InterruptedError("local_asr_cancelled")
        return result

    def locked(*args, **kwargs):
        raise PermissionError("sensitive-path capture.wav secret-context")

    monkeypatch.setattr(transcribe, "transcribe_local_wav", worker)
    monkeypatch.setattr(module.shutil, "rmtree", locked)
    with pytest.raises(WorkerExitUnconfirmed) as error:
        module.transcribe_bytes(config(tmp_path), b"private capture", lambda: False)
    assert str(error.value) == "local_asr_worker_exit_unconfirmed"
    assert error.value.artifacts_retained and capture[0].is_dir()


def test_partial_cleanup_failure_never_returns_draft_or_claims_complete_erasure(
        tmp_path, capture, monkeypatch):
    def partial_cleanup(directory):
        (directory / "capture.wav").unlink()
        raise PermissionError("synthetic partial cleanup")

    monkeypatch.setattr(transcribe, "transcribe_local_wav", lambda **kwargs: draft(kwargs))
    monkeypatch.setattr(module.shutil, "rmtree", partial_cleanup)
    with pytest.raises(WorkerExitUnconfirmed, match="^local_asr_worker_exit_unconfirmed$"):
        module.transcribe_bytes(config(tmp_path), b"private capture", lambda: False)
    assert capture[0].exists() and (capture[0] / "transcript.json").exists()
    assert not (capture[0] / "capture.wav").exists()


@pytest.mark.parametrize("change", ["identity", "redirected"])
def test_capture_boundary_drift_never_deletes_replacement(tmp_path, capture, monkeypatch, change):
    original, reads = module._capture_identity, []

    def identity(path):
        reads.append(path)
        value = original(path)
        if len(reads) == 1:
            return value
        if change == "redirected":
            raise ValueError("redirected_path_denied")
        return value[0], value[1] + 1

    def forbidden(*args, **kwargs):
        pytest.fail("a replaced capture cannot be recursively removed")

    monkeypatch.setattr(module, "_capture_identity", identity)
    monkeypatch.setattr(transcribe, "transcribe_local_wav", lambda **kwargs: draft(kwargs))
    monkeypatch.setattr(module.shutil, "rmtree", forbidden)
    with pytest.raises(WorkerExitUnconfirmed, match="^local_asr_worker_exit_unconfirmed$"):
        module.transcribe_bytes(config(tmp_path), b"private capture", lambda: False)
    assert capture[0].is_dir() and len(reads) == 2


def test_initial_capture_boundary_failure_never_starts_worker(tmp_path, capture, monkeypatch):
    def refused(*args, **kwargs):
        raise ValueError("private path refused")

    def forbidden(*args, **kwargs):
        pytest.fail("unvalidated private capture must not start a worker or be removed")

    monkeypatch.setattr(module, "_capture_identity", refused)
    monkeypatch.setattr(transcribe, "transcribe_local_wav", forbidden)
    monkeypatch.setattr(module.shutil, "rmtree", forbidden)
    with pytest.raises(WorkerExitUnconfirmed, match="^local_asr_worker_exit_unconfirmed$"):
        module.transcribe_bytes(config(tmp_path), b"private capture", lambda: False)
    assert capture[0].is_dir() and not list(capture[0].iterdir())
