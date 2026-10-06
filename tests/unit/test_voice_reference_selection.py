"""Energy suggestions are read-only, bounded and never confer transcript approval."""

import struct
import wave

import pytest

from apps.jarvis_voice_lab.lab import prepare_reference
from apps.jarvis_voice_lab.reference_selection import suggest_reference_windows


def source_wav(path, *, stereo=False, quiet_only=False):
    values = [0 if quiet_only or i % 16000 < 800 else 3000 for i in range(16000 * 12)]
    raw = b"".join(struct.pack("<hh", v, v) if stereo else struct.pack("<h", v) for v in values)
    with wave.open(str(path), "wb") as stream:
        stream.setparams((2 if stereo else 1, 2, 16000, 0, "NONE", "not compressed"))
        stream.writeframes(raw)


@pytest.mark.parametrize("stereo", [False, True])
def test_readonly_suggestions_extract_exact_frames_and_never_approve(tmp_path, stereo):
    source = tmp_path / "original.wav"
    source_wav(source, stereo=stereo)
    original = source.read_bytes()
    results = suggest_reference_windows(source, anchor_seconds=4, target_duration_seconds=4)
    assert results and len(results) <= 3
    assert source.read_bytes() == original
    for i, result in enumerate(results):
        assert 3 <= result.duration_seconds <= 5.5
        assert 0 <= result.start_seconds <= 12 - result.duration_seconds
        assert result.low_energy_edges
        assert result.energetic_fraction >= 0.5
        metadata = result.metadata()
        assert metadata["human_review_required"] is True
        assert metadata["selection_mode"] == "energy_edges_only"
        assert str(source) not in str(metadata)
        target = tmp_path / f"reference-{i}.wav"
        prepare_reference(
            source,
            target,
            start_seconds=result.start_seconds,
            duration_seconds=result.duration_seconds,
            exact_window=True,
        )
        with wave.open(str(target), "rb") as audio:
            assert audio.getnchannels() == 1
            assert audio.getnframes() == int(result.duration_seconds * 16000)


@pytest.mark.parametrize(
    "overrides",
    [
        {"anchor_seconds": True},
        {"anchor_seconds": float("nan")},
        {"anchor_seconds": -1},
        {"anchor_seconds": 15},
        {"search_radius_seconds": 20},
        {"search_radius_seconds": False},
        {"target_duration_seconds": 16},
        {"count": True},
        {"count": 0},
    ],
)
def test_invalid_search_fails_before_any_output(tmp_path, overrides):
    source = tmp_path / "original.wav"
    source_wav(source)
    arguments = dict(anchor_seconds=4)
    arguments.update(overrides)
    with pytest.raises(ValueError):
        suggest_reference_windows(source, **arguments)
    assert list(tmp_path.iterdir()) == [source]


def test_low_energy_only_is_not_selected_as_speech(tmp_path):
    source = tmp_path / "original.wav"
    # Nonzero but below -35dBFS: not recognized as energetic reference material.
    with wave.open(str(source), "wb") as stream:
        stream.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        stream.writeframes(struct.pack("<h", 2) * 16000 * 10)
    assert not suggest_reference_windows(source, anchor_seconds=2, target_duration_seconds=4)
