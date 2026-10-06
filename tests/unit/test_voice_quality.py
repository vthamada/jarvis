"""Quality controls are bounded experiments, not a perceptual quality certificate."""

import json
import struct
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab.lab import prepare_reference, run_voice_lab
from apps.jarvis_voice_lab.quality import validate_quality_options


def options(**overrides):
    value = dict(
        engine="qwen3_tts",
        profile="baseline",
        reference_start_seconds=0,
        reference_duration_seconds=10,
        reference_transcript=None,
        transcript_confirmed=False,
        seed=None,
    )
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    "overrides",
    [
        {"reference_start_seconds": -1},
        {"reference_start_seconds": float("nan")},
        {"reference_duration_seconds": 16},
        {"reference_duration_seconds": True},
        {"seed": True},
        {"seed": -1},
        {"seed": 2**32},
        {"profile": "best_voice"},
        {"profile": "chatterbox_conversational"},
        {"reference_transcript": "not_used"},
        {"transcript_confirmed": True},
        {"transcript_confirmed": "true"},
        {"profile": "qwen_icl"},
        {"profile": "qwen_icl", "reference_transcript": "text"},
        {"profile": "qwen_icl", "reference_transcript": "\x00", "transcript_confirmed": True},
        {"profile": "qwen_icl", "reference_transcript": "x" * 2001, "transcript_confirmed": True},
        {"profile": "qwen_icl", "engine": "chatterbox_pt_br"},
        {"profile": "qwen_icl_draft"},
        {
            "profile": "qwen_icl_draft",
            "reference_transcript": "draft",
            "transcript_confirmed": True,
        },
        {
            "profile": "qwen_icl_draft",
            "reference_transcript": "draft",
            "engine": "chatterbox_pt_br",
        },
    ],
)
def test_options_fail_closed(overrides):
    with pytest.raises(ValueError):
        validate_quality_options(**options(**overrides))


def test_confirmed_icl_and_conversational_profiles():
    validate_quality_options(**options(profile="qwen_icl_draft", reference_transcript="Rascunho."))
    validate_quality_options(
        **options(
            profile="qwen_icl",
            reference_transcript="Fala exata.",
            transcript_confirmed=True,
            seed=42,
        )
    )
    validate_quality_options(
        **options(engine="chatterbox_pt_br", profile="chatterbox_conversational", seed=42)
    )


def write_source(path, seconds=12):
    with wave.open(str(path), "wb") as source:
        source.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        source.writeframes(
            b"".join(struct.pack("<h", 100 + i // 8000) for i in range(seconds * 8000))
        )


def test_offset_exact_window_and_original_readonly(tmp_path):
    source, output = tmp_path / "source.wav", tmp_path / "reference.wav"
    write_source(source)
    original = source.read_bytes()
    assert prepare_reference(
        source, output, start_seconds=5, duration_seconds=3, exact_window=True
    ) == (8000, 3)
    with wave.open(str(output), "rb") as audio:
        assert struct.unpack("<h", audio.readframes(1))[0] == 105
        assert audio.getnframes() == 24000
    assert source.read_bytes() == original
    with pytest.raises(ValueError, match="reference_window_out_of_bounds"):
        prepare_reference(
            source,
            tmp_path / "overflow.wav",
            start_seconds=10,
            duration_seconds=3,
            exact_window=True,
        )
    assert not (tmp_path / "overflow.wav").exists()
    with pytest.raises(FileExistsError):
        prepare_reference(source, output)


@pytest.mark.parametrize("profile", ["qwen_icl", "qwen_icl_draft"])
def test_icl_private_stdin_binding_and_metadata_without_transcript(tmp_path, profile):
    import sys

    source = tmp_path / "source.wav"
    write_source(source)
    model = tmp_path / "models"
    model.mkdir()
    seen = {}
    transcript = "Texto privado exatamente associado ao trecho de referência."

    def fixture_worker(request):
        seen.update(request)
        write_source(Path(request["output_path"]), seconds=1)
        return {"status": "completed", "run_id": request["run_id"], "engine": request["engine"]}

    result = run_voice_lab(
        engine="qwen3_tts",
        authorized=True,
        reference_path=source,
        text="Outra frase.",
        model_dir=model,
        python_executable=Path(sys.executable),
        workspace_root=tmp_path,
        voice_profile=profile,
        reference_start_seconds=5,
        reference_duration_seconds=3,
        reference_transcript=transcript,
        transcript_confirmed=profile == "qwen_icl",
        seed=42,
        evidence_mode="fixture",
        fixture_worker=fixture_worker,
    )
    assert result.status == "completed" and result.evidence_mode == "fixture"
    assert seen["reference_transcript"] == transcript
    assert seen["transcript_confirmed"] is (profile == "qwen_icl")
    assert seen["voice_profile"] == profile and seen["seed"] == 42
    assert transcript not in json.dumps(result.metadata())
    assert "Outra frase." not in json.dumps(result.metadata())
    assert result.metadata()["voice_profile"] == profile
    assert result.metadata()["reference_transcript_reviewed"] is (profile == "qwen_icl")
    if profile == "qwen_icl_draft":
        assert result.metadata()["review_required"] is True
