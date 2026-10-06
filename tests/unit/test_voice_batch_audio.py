"""Lossless batch text and complete, atomic local PCM artifact contracts."""

import importlib.util
import math
import os
import stat
import struct
import time
import types
import unicodedata
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import batch_audio
from apps.jarvis_voice_lab.batch_audio import assemble_wavs, inspect_wav, segment_text


def write_wav(path, *, rate=8000, channels=1, width=2, frames=8000, value=300):
    sample = struct.pack("<h", value) if width == 2 else b"\x01" * width
    if value == 0:
        sample = b"\x00" * width
    pcm = sample * frames * channels
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(pcm)
    return pcm


@pytest.fixture
def parts(tmp_path):
    first, second = tmp_path / "part-1.wav", tmp_path / "part-2.wav"
    write_wav(first, frames=17, value=123)
    write_wav(second, frames=19, value=-456)
    return first, second


def assemble(parts, output, **kwargs):
    return assemble_wavs(parts, output, deadline=time.monotonic() + 30, **kwargs)


@pytest.mark.parametrize(
    "text",
    [
        "Fala.", "  Fala.  ", "\tFala\r\n", "x" * 600, "x" * 601, "x" * 6000,
        "A\U0001f680e\u0301\r\n" * 700,
        "Olá, senhor. " * 120,
        " a " * 1000,
        "x" + " " * 598 + "y" + " " * 599 + "z",
        " " * 599 + "a" + "b" + " " * 599,
        "e" + "\u0301" * 1800,
        "a\r\n" * 1999,
        "x" * 598 + "\r\n" + "y" * 601,
        "x" * 599 + "\r\n" + "y" * 601,
        "A\u2003B\u2028C\u2029D" * 600,
    ],
)
def test_text_is_exact_codepoints_nonblank_and_bounded(text):
    result = segment_text(text)
    assert isinstance(result, tuple)
    assert 1 <= len(result) <= 16
    assert "".join(result) == text
    assert "".join(result).encode("utf-8") == text.encode("utf-8")
    assert all(1 <= len(part) <= 600 and part.strip() for part in result)
    assert all(not (left.endswith("\r") and right.startswith("\n"))
               for left, right in zip(result, result[1:]))


@pytest.mark.parametrize(
    "text",
    [None, False, 42, b"hello", "", " \n\t\r ", "x" * 6001,
     "secret\x00", "secret\x01", "secret\x7f", "secret\x85",
     "secret\u200b", "secret\u200d", "secret\u202e", "secret\ufeff",
     "secret\ud800", "secret\udfff"],
)
def test_invalid_text_is_refused_without_echo(text):
    with pytest.raises(ValueError, match="^invalid_batch_text$"):
        segment_text(text)


@pytest.mark.parametrize("text", ["x" + " " * 600, " " * 600 + "x", " " * 900 + "x",
                                  "x" + " " * 1300 + "y"])
def test_impossible_nonblank_partition_is_explicit_not_trimmed(text):
    with pytest.raises(ValueError, match="^batch_text_partition_impossible$"):
        segment_text(text)


def test_sentence_preferred_over_later_space_and_decomposed_text_is_not_normalized():
    sentence = "e\u0301" * 200 + "."
    text = sentence + " " + "more words " * 90
    result = segment_text(text)
    assert result[0] == sentence
    assert "".join(result) != unicodedata.normalize("NFC", text)
    assert not any(unicodedata.category(part[0]).startswith("M") for part in result[1:])


def test_combining_boundary_moves_earlier_when_a_safe_cut_exists():
    result = segment_text("a" * 599 + "e\u0301" + "b" * 599)
    assert len(result[0]) == 599
    assert result[1].startswith("e\u0301")


def test_suffix_feasibility_does_not_leave_blank_tail():
    text = "x" * 599 + "y" + " " * 599
    result = segment_text(text)
    assert result == ("x" * 599, "y" + " " * 599)


@pytest.mark.parametrize("rate", [8000, 11025, 22050, 44100, 48000, 96000])
def test_inspect_pcm16_mono_supported_rates(tmp_path, rate):
    source = tmp_path / "source.wav"
    write_wav(source, rate=rate, frames=rate)
    assert inspect_wav(source) == (rate, rate, 1)
    assert inspect_wav(source, max_duration_seconds=1) == (rate, rate, 1)


@pytest.mark.parametrize("limit", [0, -1, 601, True, None, "600", math.nan, math.inf])
def test_inspection_invalid_duration_bound_is_pre_io(tmp_path, limit):
    with pytest.raises(ValueError, match="^invalid_wav_duration_limit$"):
        inspect_wav(tmp_path / "does-not-exist.wav", max_duration_seconds=limit)


@pytest.mark.parametrize(
    "settings,reason",
    [({"channels": 2}, "unsupported_wav_format"),
     ({"width": 1}, "unsupported_wav_format"),
     ({"width": 3}, "unsupported_wav_format"),
     ({"rate": 7999}, "unsupported_wav_format"),
     ({"rate": 96001}, "unsupported_wav_format"),
     ({"value": 0}, "silent_output"),
     ({"frames": 0}, "invalid_wav_data"),
     ({"frames": 8001}, "wav_duration_out_of_bounds")],
)
def test_inspection_refuses_invalid_format_or_content(tmp_path, settings, reason):
    source = tmp_path / "source.wav"
    write_wav(source, **settings)
    with pytest.raises(ValueError, match=f"^{reason}$"):
        inspect_wav(source, max_duration_seconds=1)


@pytest.mark.parametrize("change", ["truncated", "riff-short", "riff-long", "bad-riff",
                                   "bad-wave", "odd-data", "byte-rate", "alignment",
                                   "compressed", "duplicate-data", "duplicate-format"])
def test_complete_container_and_pcm_header_are_checked(tmp_path, change):
    source = tmp_path / "source.wav"
    write_wav(source, frames=32)
    raw = bytearray(source.read_bytes())
    if change == "truncated":
        del raw[-2:]
    elif change == "riff-short":
        raw[4:8] = struct.pack("<I", len(raw) - 10)
    elif change == "riff-long":
        raw[4:8] = struct.pack("<I", len(raw))
    elif change == "bad-riff":
        raw[:4] = b"RIFX"
    elif change == "bad-wave":
        raw[8:12] = b"NOPE"
    elif change == "odd-data":
        raw[40:44] = struct.pack("<I", 63)
    elif change == "byte-rate":
        raw[28:32] = struct.pack("<I", 1)
    elif change == "alignment":
        raw[32:34] = struct.pack("<H", 4)
    elif change == "compressed":
        raw[20:22] = struct.pack("<H", 3)
    elif change == "duplicate-data":
        raw.extend(b"data" + struct.pack("<I", 2) + b"\x01\x00")
        raw[4:8] = struct.pack("<I", len(raw) - 8)
    elif change == "duplicate-format":
        raw.extend(raw[12:36])
        raw[4:8] = struct.pack("<I", len(raw) - 8)
    source.write_bytes(raw)
    with pytest.raises(ValueError) as error:
        inspect_wav(source)
    assert "source.wav" not in str(error.value)


def test_riff_ancillary_chunks_and_pcm_fmt_extension_are_supported(tmp_path):
    source = tmp_path / "source.wav"
    pcm = write_wav(source, frames=32)
    raw = source.read_bytes()
    fmt = raw[12:36]
    expanded_fmt = fmt[:4] + struct.pack("<I", 18) + fmt[8:] + b"\x00\x00"
    body = b"WAVE" + b"JUNK" + struct.pack("<I", 3) + b"abc\x00" + expanded_fmt + raw[36:]
    source.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    assert inspect_wav(source) == (8000, 32, 1)
    output = tmp_path / "complete.wav"
    assert assemble((source,), output) == (8000, 32, 1)
    with wave.open(str(output), "rb") as audio:
        assert audio.readframes(100) == pcm


def test_inspection_rejects_missing_directory_hardlink_and_redirected_paths(tmp_path, parts):
    with pytest.raises(ValueError, match="^invalid_audio_source$"):
        inspect_wav(tmp_path / "PRIVATE-missing.wav")
    with pytest.raises(ValueError, match="^regular_single_link_file_required$"):
        inspect_wav(tmp_path)
    linked = tmp_path / "linked.wav"
    os.link(parts[0], linked)
    with pytest.raises(ValueError, match="^regular_single_link_file_required$"):
        inspect_wav(linked)


def test_reparse_attribute_is_denied_without_needing_symlink_privileges(parts, monkeypatch):
    original = Path.lstat

    def redirected(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path == parts[0]:
            return types.SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
        return info

    monkeypatch.setattr(Path, "lstat", redirected)
    with pytest.raises(ValueError, match="^redirected_path_denied$"):
        inspect_wav(parts[0])


def test_size_limit_is_checked_before_wave_parser(parts, monkeypatch):
    monkeypatch.setattr(batch_audio, "MAX_OUTPUT_BYTES", 45)
    with pytest.raises(ValueError, match="^wav_size_out_of_bounds$"):
        inspect_wav(parts[0])


def test_pcm_concatenation_is_exact_and_inputs_are_unchanged(tmp_path, parts):
    before = [part.read_bytes() for part in parts]
    output = tmp_path / "complete.wav"
    assert assemble(parts, output) == (8000, 36, 1)
    assert inspect_wav(output) == (8000, 36, 1)
    with wave.open(str(output), "rb") as audio:
        assert audio.readframes(100) == struct.pack("<h", 123) * 17 + struct.pack("<h", -456) * 19
    assert [part.read_bytes() for part in parts] == before
    assert output.stat().st_nlink == 1
    assert not list(tmp_path.glob("*.pending"))


def test_pcm_extremes_are_not_crossfaded_resampled_or_clipped(tmp_path):
    sources = (tmp_path / "low.wav", tmp_path / "high.wav")
    low = write_wav(sources[0], rate=96000, frames=123, value=-32768)
    high = write_wav(sources[1], rate=96000, frames=321, value=32767)
    output = tmp_path / "full.wav"
    assert assemble(sources, output) == (96000, 444, 1)
    with wave.open(str(output), "rb") as audio:
        assert audio.readframes(444) == low + high


@pytest.mark.parametrize("count", [0, 17])
def test_part_count_limit_precedes_io(tmp_path, count):
    with pytest.raises(ValueError, match="^invalid_audio_batch$"):
        assemble((tmp_path / "missing.wav",) * count, tmp_path / "final.wav")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("deadline", [True, None, "tomorrow", math.inf, math.nan])
def test_invalid_deadline_precedes_io(tmp_path, deadline):
    with pytest.raises(ValueError, match="^invalid_audio_batch$"):
        assemble_wavs([tmp_path / "missing.wav"], tmp_path / "final.wav", deadline=deadline)


@pytest.mark.parametrize("kwargs", [{"cancelled": None}, {"clock": None}])
def test_invalid_callback_precedes_io(tmp_path, kwargs):
    with pytest.raises(ValueError, match="^invalid_audio_batch$"):
        assemble((tmp_path / "missing.wav",), tmp_path / "final.wav", **kwargs)


@pytest.mark.parametrize("second", ["silent", "truncated", "stereo", "different-rate", "long"])
def test_any_bad_part_prevents_final_and_pending_creation(tmp_path, parts, second):
    if second == "silent":
        write_wav(parts[1], value=0)
    elif second == "truncated":
        parts[1].write_bytes(parts[1].read_bytes()[:-2])
    elif second == "stereo":
        write_wav(parts[1], channels=2)
    elif second == "different-rate":
        write_wav(parts[1], rate=16000)
    elif second == "long":
        write_wav(parts[1], frames=8000 * 120 + 1)
    before = [part.read_bytes() for part in parts]
    with pytest.raises(ValueError):
        assemble(parts, tmp_path / "final.wav")
    assert [part.read_bytes() for part in parts] == before
    assert {path.name for path in tmp_path.iterdir()} == {part.name for part in parts}


def test_total_duration_bound_all_parts_instead_of_each_part_only(tmp_path):
    sources = tuple(tmp_path / f"part-{index}.wav" for index in range(6))
    for source in sources:
        write_wav(source, frames=8000 * 101)
    with pytest.raises(ValueError, match="^batch_audio_out_of_bounds$"):
        assemble(sources, tmp_path / "final.wav")
    assert len(list(tmp_path.iterdir())) == 6


def test_exact_total_duration_and_sixteen_parts_are_accepted(tmp_path):
    sources = tuple(tmp_path / f"part-{index}.wav" for index in range(16))
    for source in sources:
        write_wav(source, frames=8000 * 600 // 16)
    output = tmp_path / "final.wav"
    assert assemble(sources, output) == (8000, 8000 * 600, 1)
    assert inspect_wav(output) == (8000, 8000 * 600, 1)


def test_total_byte_limit_counts_header_and_pcm_not_just_part_sizes(tmp_path, parts, monkeypatch):
    monkeypatch.setattr(batch_audio, "MAX_OUTPUT_BYTES", 44 + 35 * 2)
    with pytest.raises(ValueError, match="^batch_audio_out_of_bounds$"):
        assemble(parts, tmp_path / "final.wav")
    assert len(list(tmp_path.iterdir())) == 2


@pytest.mark.parametrize("kind", ["file", "directory", "input"])
def test_existing_final_and_input_are_never_overwritten(tmp_path, parts, kind):
    output = tmp_path / "final.wav"
    if kind == "file":
        output.write_bytes(b"PRIVATE-previous-output")
    elif kind == "directory":
        output.mkdir()
    else:
        output = parts[0]
    previous = output.read_bytes() if output.is_file() else None
    with pytest.raises(ValueError, match="^(output_exists|output_is_input)$"):
        assemble(parts, output)
    if previous is not None:
        assert output.read_bytes() == previous


def test_publication_is_atomic_only_after_full_validation(tmp_path, parts, monkeypatch):
    original_link = os.link
    observed = []
    output = tmp_path / "final.wav"

    def publish(source, destination):
        observed.append(source)
        assert not output.exists()
        assert source.name.endswith(".pending")
        assert inspect_wav(source) == (8000, 36, 1)
        if os.name != "nt":
            assert stat.S_IMODE(source.stat().st_mode) == 0o600
        original_link(source, destination)

    monkeypatch.setattr(os, "link", publish)
    assemble(parts, output)
    assert len(observed) == 1
    assert not observed[0].exists()


def test_output_created_by_another_process_during_publication_is_preserved(tmp_path, parts,
                                                                         monkeypatch):
    original_link = os.link
    output = tmp_path / "final.wav"

    def racing_link(source, destination):
        output.write_bytes(b"another-owner")
        original_link(source, destination)

    monkeypatch.setattr(os, "link", racing_link)
    with pytest.raises(ValueError, match="^audio_assembly_failed$"):
        assemble(parts, output)
    assert output.read_bytes() == b"another-owner"
    assert len(list(tmp_path.iterdir())) == 3


def test_pending_collision_is_not_deleted(tmp_path, parts, monkeypatch):
    monkeypatch.setattr(batch_audio.uuid, "uuid4", lambda: types.SimpleNamespace(hex="same"))
    previous = tmp_path / ".jarvis-audio-same.pending"
    previous.write_bytes(b"another-pending-owner")
    with pytest.raises(ValueError, match="^audio_assembly_failed$"):
        assemble(parts, tmp_path / "final.wav")
    assert previous.read_bytes() == b"another-pending-owner"


def test_failure_cleanup_removes_only_own_pending(tmp_path, parts, monkeypatch):
    foreign = tmp_path / ".unrelated.pending"
    foreign.write_bytes(b"other-owner")

    def denied(*args):
        raise OSError("PRIVATE-path-or-token")

    monkeypatch.setattr(os, "link", denied)
    with pytest.raises(ValueError, match="^audio_assembly_failed$") as error:
        assemble(parts, tmp_path / "final.wav")
    assert "PRIVATE" not in str(error.value)
    assert foreign.read_bytes() == b"other-owner"
    assert len(list(tmp_path.iterdir())) == 3


@pytest.mark.parametrize("action", ["deadline", "cancel"])
def test_expired_or_cancelled_before_io(tmp_path, action):
    kwargs = {"deadline": 10, "clock": lambda: 10}
    error = TimeoutError
    reason = "deadline_exceeded"
    if action == "cancel":
        kwargs["cancelled"] = lambda: True
        error, reason = InterruptedError, "cancelled"
    with pytest.raises(error, match=f"^{reason}$"):
        assemble_wavs((tmp_path / "missing.wav",), tmp_path / "final.wav", **kwargs)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("phase", ["read", "write", "publish"])
@pytest.mark.parametrize("action", ["deadline", "cancel"])
def test_deadline_and_cancellation_observed_during_each_bounded_phase(tmp_path, parts,
                                                                    monkeypatch, phase, action):
    control = {"stop": False}
    if phase == "read":
        original = wave.Wave_read.readframes

        def reading(handle, count):
            result = original(handle, count)
            control["stop"] = True
            return result

        monkeypatch.setattr(wave.Wave_read, "readframes", reading)
    elif phase == "write":
        original = wave.Wave_write.writeframesraw

        def writing(handle, raw):
            result = original(handle, raw)
            control["stop"] = True
            return result

        monkeypatch.setattr(wave.Wave_write, "writeframesraw", writing)
    else:
        original = os.fsync

        def syncing(descriptor):
            original(descriptor)
            control["stop"] = True

        monkeypatch.setattr(os, "fsync", syncing)
    kwargs = {"deadline": 10, "clock": lambda: 11 if control["stop"] else 0}
    error, reason = TimeoutError, "deadline_exceeded"
    if action == "cancel":
        kwargs.update(clock=lambda: 0, cancelled=lambda: control["stop"])
        error, reason = InterruptedError, "cancelled"
    before = [part.read_bytes() for part in parts]
    with pytest.raises(error, match=f"^{reason}$"):
        assemble_wavs(parts, tmp_path / "final.wav", **kwargs)
    assert [part.read_bytes() for part in parts] == before
    assert len(list(tmp_path.iterdir())) == 2


def test_source_replaced_after_validation_is_refused(tmp_path, parts, monkeypatch):
    original = batch_audio._inspect
    calls = []

    def inspect(source, duration, check):
        result = original(source, duration, check)
        calls.append(source)
        if len(calls) == len(parts):
            write_wav(parts[0], frames=17, value=999)
        return result

    monkeypatch.setattr(batch_audio, "_inspect", inspect)
    with pytest.raises(ValueError, match="^audio_source_changed$"):
        assemble(parts, tmp_path / "final.wav")
    assert len(list(tmp_path.iterdir())) == 2


def test_pcm_digest_catches_same_identity_size_and_timestamp_mutation(tmp_path, parts,
                                                                  monkeypatch):
    original = batch_audio._inspect
    calls = []

    def inspect(source, duration, check):
        result = original(source, duration, check)
        calls.append(source)
        if len(calls) == len(parts):
            before = parts[0].stat()
            raw = bytearray(parts[0].read_bytes())
            raw[-2:] = struct.pack("<h", 789)
            parts[0].write_bytes(raw)
            os.utime(parts[0], ns=(before.st_atime_ns, before.st_mtime_ns))
        return result

    # Force only the stable identity/size/mtime fingerprint even on POSIX, so
    # this specifically proves independent byte binding rather than stat checks.
    monkeypatch.setattr(batch_audio, "_fingerprint", lambda info: (
        info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns))
    monkeypatch.setattr(batch_audio, "_inspect", inspect)
    with pytest.raises(ValueError, match="^audio_source_changed$"):
        assemble(parts, tmp_path / "final.wav")
    assert len(list(tmp_path.iterdir())) == 2


def test_foreign_pending_replacement_is_not_removed_during_cleanup(tmp_path, parts, monkeypatch):
    foreign = []

    def swap_before_link(path, destination):
        path.unlink()
        path.write_bytes(b"foreign-private-pending")
        foreign.append(path)
        raise OSError("PRIVATE error")

    monkeypatch.setattr(os, "link", swap_before_link)
    with pytest.raises(ValueError, match="^audio_assembly_failed$"):
        assemble(parts, tmp_path / "final.wav")
    assert len(foreign) == 1
    assert foreign[0].read_bytes() == b"foreign-private-pending"
    assert not (tmp_path / "final.wav").exists()


@pytest.mark.parametrize("value", [None, math.nan, math.inf, True, "PRIVATE"])
def test_bad_clock_values_are_fixed_errors_without_io(tmp_path, value):
    with pytest.raises(ValueError, match="^invalid_audio_clock$"):
        assemble_wavs([tmp_path / "missing.wav"], tmp_path / "final.wav",
                      deadline=10, clock=lambda: value)


@pytest.mark.parametrize("callback", ["clock", "cancelled"])
def test_callback_exceptions_do_not_echo_private_content(tmp_path, callback):
    def fail():
        raise RuntimeError("PRIVATE-token-and-path")

    with pytest.raises(ValueError, match="^audio_control_failed$"):
        assemble([tmp_path / "missing.wav"], tmp_path / "final.wav", **{callback: fail})


def test_module_can_be_loaded_by_isolated_worker_file_path():
    spec = importlib.util.spec_from_file_location("standalone_audio_contract", batch_audio.__file__)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.segment_text("x" * 601) == ("x" * 600, "x")
    assert module.MAX_PARTS == 16
