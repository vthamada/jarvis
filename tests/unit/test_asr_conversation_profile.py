"""Explicit faster decoding stays a reviewable draft, never an automatic Core turn."""

import json
import sys
import wave
from io import BytesIO
from pathlib import Path

import pytest

from apps.jarvis_api import voice_profile
from apps.jarvis_voice_lab import asr_worker, transcribe


@pytest.mark.parametrize("profile,expected", [("quality", 5), ("conversation", 1)])
def test_decoding_policy_is_explicit_and_does_not_remove_draft(profile, expected):
    calls = []

    def recognize(value, **options):
        calls.append(options)
        return {"text": "Frase sintetica para revisao."}

    result = asr_worker.transcribe_windows(
        recognize, [1] * 10, 1, 10, decoding_profile=profile,
    )
    assert len(calls) == 1
    assert calls[0]["generate_kwargs"]["num_beams"] == expected
    assert calls[0]["generate_kwargs"]["no_repeat_ngram_size"] == 4
    assert calls[0]["generate_kwargs"]["max_new_tokens"] == 256
    _, document = asr_worker.transcript_document(result, 10)
    assert document["review_required"] is True
    assert document["segments"][0]["text"] == "Frase sintetica para revisao."


@pytest.mark.parametrize("profile", [None, True, 1, [], {}, "", "fast", "CONVERSATION"])
def test_invalid_profile_is_rejected_before_read_or_inference(profile, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid policy must not inspect files or perform inference")

    monkeypatch.setattr(transcribe, "_plain_path", forbidden)
    with pytest.raises(ValueError):
        transcribe.transcribe_local_wav(
            authorized=True, source="not-opened", model_dir="not-opened",
            python_executable="not-run", decoding_profile=profile,
        )
    with pytest.raises(ValueError):
        asr_worker.transcribe_windows(forbidden, [1], 1, 1, decoding_profile=profile)


@pytest.fixture
def local_profile(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "config.json").write_text("{}", encoding="utf-8")
    executable = tmp_path / "synthetic-python.exe"
    executable.write_bytes(b"never execute")
    path = tmp_path / "voice.json"
    data = {
        "schema_version": "jarvis-local-voice-profile-v1", "tts": None,
        "asr": {"model_dir": str(model), "python_executable": str(executable),
                "device": "cpu", "timeout_seconds": 20},
    }
    return path, data


@pytest.mark.parametrize("selected", ["quality", "conversation", "omitted"])
def test_private_host_profile_is_backward_compatible(local_profile, selected, tmp_path):
    path, document = local_profile
    if selected != "omitted":
        document["asr"]["decoding_profile"] = selected
    path.write_text(json.dumps(document), encoding="utf-8")
    config = voice_profile.load_voice_profile(path, tmp_path).asr
    assert config.decoding_profile == ("quality" if selected == "omitted" else selected)


@pytest.mark.parametrize("selected", [None, True, 1, [], {}, "", "fast", "CONVERSATION"])
def test_host_profile_never_selects_unrecognised_decoding(local_profile, selected, tmp_path):
    path, document = local_profile
    document["asr"]["decoding_profile"] = selected
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(ValueError, match="^invalid_voice_profile$"):
        voice_profile.load_voice_profile(path, tmp_path)


def test_web_wrapper_forwards_policy_through_owned_worker_and_cleans_draft(tmp_path, monkeypatch):
    config = voice_profile.LocalAsrConfig(
        tmp_path, Path(sys.executable).resolve(strict=True), "cpu", 20, "conversation",
    )
    output = BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * 8000)
    seen = []

    class Process:
        returncode = 0

        def __init__(self, command, **options):
            self.options = options
            assert command[1] == "-I"

        def communicate(self, input=None, timeout=None):
            from pathlib import Path

            request = json.loads(input)
            assert request["decoding_profile"] == "conversation"
            directory = Path(request["output_directory"])
            seen.append(directory)

            def recognize(_audio, **options):
                assert options["generate_kwargs"]["num_beams"] == 1
                return {"text": "Frase sintetica para revisao."}

            result = asr_worker.transcribe_windows(
                recognize, [1], 1, 1, decoding_profile=request["decoding_profile"],
            )
            text, document = asr_worker.transcript_document(result, 1)
            (directory / "transcript.txt").write_text(text, encoding="utf-8")
            (directory / "transcript.json").write_text(json.dumps(document), encoding="utf-8")
            self.options["stdout"].write(json.dumps({
                "run_id": request["run_id"], "status": "completed",
            }).encode("utf-8"))
            self.options["stdout"].flush()

    class ConfirmedSupervisor:
        def __init__(self, **kwargs):
            pass

        def poll_handshake(self):
            return True

        def confirm_exit(self, **kwargs):
            pass

        def close(self):
            pass

    monkeypatch.setattr(transcribe.subprocess, "Popen", Process)
    # Kernel identity/exit is exercised separately; this is the decoding unit seam.
    monkeypatch.setattr(transcribe, "OwnedWorkerSupervisor", ConfirmedSupervisor)
    monkeypatch.setattr(transcribe, "expected_worker_image", lambda path: str(path))
    assert voice_profile.transcribe_bytes(config, output.getvalue(), lambda: False) == (
        "Frase sintetica para revisao."
    )
    assert len(seen) == 1 and not seen[0].exists()
