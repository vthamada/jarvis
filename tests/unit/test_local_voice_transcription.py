"""Local ASR bounds/privacy and actual subprocess orchestration via explicit doubles."""

import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import transcribe
from apps.jarvis_voice_lab.asr_worker import transcribe_windows, transcript_document


def test_independent_windows_have_coarse_times_and_no_carried_context():
    calls = []

    def asr(value, **kwargs):
        calls.append((value, kwargs))
        return {"text": "Janela fixture."}

    result = transcribe_windows(asr, list(range(45)), 1, 45)
    assert [c["timestamp"] for c in result["chunks"]] == [(0, 20), (20, 40), (40, 45)]
    assert [len(c[0]["array"]) for c in calls] == [20, 20, 5]
    assert all(c[1]["return_timestamps"] is False for c in calls)
    assert all(c[1]["generate_kwargs"]["no_repeat_ngram_size"] == 4 for c in calls)
    _, data = transcript_document(result, 45)
    assert all(s["timestamps_estimated"] for s in data["segments"])


def test_empty_window_is_explicit_not_invented_speech():
    result = transcribe_windows(lambda *a, **k: {"text": " "}, [0], 1, 1)
    assert result["chunks"][0]["text"] == "[Sem fala reconhecida nesta janela.]"


def test_draft_timestamps_and_no_speaker_identity():
    text, data = transcript_document(
        {
            "chunks": [
                {"text": " Fala reconhecida. ", "timestamp": (0.1, 3.4)},
                {"text": " Outra frase.", "timestamp": (4.0, None)},
            ]
        },
        10.0,
    )
    assert "RASCUNHO NÃO REVISADO" in text and "[00:00.10–00:03.40]" in text
    assert data["review_required"] is True and data["segments"][-1]["timestamps_estimated"]
    assert data["segments"][-1]["end_seconds"] == 10


@pytest.mark.parametrize(
    "result,duration",
    [
        ({"chunks": []}, 10),
        ({"chunks": [{"text": " ", "timestamp": (0, 1)}]}, 10),
        ({"chunks": [{"text": "x", "timestamp": (float("nan"), 1)}]}, 10),
        ({"chunks": [{"text": "x", "timestamp": (2, 1)}]}, 10),
        ({"chunks": [{"text": "x", "timestamp": (0, 13)}]}, 10),
        ({"chunks": [{"text": "\x00", "timestamp": (0, 1)}]}, 10),
        ({"chunks": [{"text": "x", "timestamp": (0, 1)}]}, True),
    ],
)
def test_malformed_result_is_not_a_transcript(result, duration):
    with pytest.raises(ValueError):
        transcript_document(result, duration)


@pytest.fixture
def arguments(tmp_path):
    source = tmp_path / "original.wav"
    with wave.open(str(source), "wb") as wav:
        wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        wav.writeframes(b"\x01\x00" * 8000)
    models = tmp_path / "models"
    models.mkdir()
    return dict(
        authorized=True, source=source, model_dir=models, python_executable=Path(sys.executable)
    )


def test_authorization_is_required_before_audio_read(arguments):
    arguments.update(authorized=False, source=Path("does-not-exist.wav"))
    with pytest.raises(ValueError, match="authorization_required"):
        transcribe.transcribe_local_wav(**arguments)


def test_private_worker_stdin_and_unconfirmed_output(arguments, monkeypatch):
    seen = {}
    original = arguments["source"].read_bytes()

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            seen.update(command=command, kwargs=kwargs)

        def communicate(self, input=None, timeout=None):
            request = json.loads(input)
            output = Path(request["output_directory"])
            (output / "transcript.txt").write_text("Transcricao privada fixture.", encoding="utf-8")
            (output / "transcript.json").write_text('{"review_required":true}', encoding="utf-8")
            seen["kwargs"]["stdout"].write(
                json.dumps({"run_id": request["run_id"], "status": "completed"}).encode()
            )
            seen["kwargs"]["stdout"].flush()

    monkeypatch.setattr(transcribe.subprocess, "Popen", Process)
    monkeypatch.setenv("OPENAI_API_KEY", "private-secret")
    result = transcribe.transcribe_local_wav(**arguments)
    assert result["review_required"] and not result["speaker_identity_verified"]
    assert "Transcricao privada" not in json.dumps(result)
    assert "private-secret" not in json.dumps(seen["kwargs"]["env"])
    assert seen["kwargs"]["stderr"] == subprocess.DEVNULL
    assert str(arguments["source"]) not in " ".join(seen["command"])
    assert arguments["source"].read_bytes() == original
    assert not Path(result["transcript_path"]).with_name("worker-status.tmp").exists()


def test_deadline_kills_and_reaps_only_own_worker(arguments, monkeypatch):
    processes = []

    class Process:
        returncode = None
        killed = False

        def __init__(self, *args, **kwargs):
            processes.append(self)

        def communicate(self, *args, **kwargs):
            if not self.killed:
                raise subprocess.TimeoutExpired("fixture", 1)
            self.returncode = -1

        def poll(self):
            return self.returncode

        def kill(self):
            self.killed = True

    monkeypatch.setattr(transcribe.subprocess, "Popen", Process)
    clock = iter([0, 0, 2])
    monkeypatch.setattr(transcribe.time, "monotonic", lambda: next(clock))
    with pytest.raises(ValueError, match="local_asr_deadline_or_metadata_limit"):
        transcribe.transcribe_local_wav(**arguments, timeout_seconds=1)
    assert len(processes) == 1 and processes[0].killed and processes[0].returncode == -1
