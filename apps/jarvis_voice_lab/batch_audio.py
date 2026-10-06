"""Lossless bounded text segmentation and local PCM batch publication.

This module deliberately imports no SDK or package-relative module: the isolated
voice worker can load the same contracts by file path. Audio here is an artifact,
never a new response, and concatenation never rewrites the final synthesis text.
"""

from __future__ import annotations

import hashlib
import math
import os
import stat
import struct
import time
import unicodedata
import uuid
import wave
from pathlib import Path
from typing import Callable, Sequence

MAX_TEXT_CODEPOINTS = 6000
MAX_PART_CODEPOINTS = 600
MAX_PARTS = 16
MAX_OUTPUT_BYTES = 32 * 1024 * 1024
MAX_TOTAL_SECONDS = 600
MAX_PART_SECONDS = 120
_READ_FRAMES = 16384


def segment_text(text: str) -> tuple[str, ...]:
    """Partition exact code points, preferring sentence/space/grapheme boundaries.

    A suffix feasibility pass avoids producing a whitespace-only final segment
    or refusing a valid partition just because an earlier natural cut was chosen.
    Combining clusters longer than the per-part limit require a code-point cut;
    CRLF is never split. No normalization or trimming is performed.
    """
    if (
        not isinstance(text, str)
        or not 1 <= len(text) <= MAX_TEXT_CODEPOINTS
        or not text.strip()
        or any(
            unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in "\n\r\t"
            for char in text
        )
    ):
        raise ValueError("invalid_batch_text")
    size = len(text)
    if size <= MAX_PART_CODEPOINTS:
        return (text,)
    speech = [0]
    for char in text:
        speech.append(speech[-1] + (not char.isspace()))

    def allowed(end: int) -> bool:
        return end == size or not (text[end - 1] == "\r" and text[end] == "\n")

    # Minimal number of nonblank parts in each suffix. Values above MAX_PARTS
    # are equivalent to impossible within this contract, and remain bounded.
    cost = [MAX_PARTS + 1] * (size + 1)
    cost[size] = 0
    for start in range(size - 1, -1, -1):
        for end in range(start + 1, min(size, start + MAX_PART_CODEPOINTS) + 1):
            if speech[end] > speech[start] and allowed(end):
                cost[start] = min(cost[start], 1 + cost[end])
    if cost[0] > MAX_PARTS:
        raise ValueError("batch_text_partition_impossible")

    parts = []
    start = 0
    while start < size:
        remaining = MAX_PARTS - len(parts) - 1
        candidates = [
            end
            for end in range(start + 1, min(size, start + MAX_PART_CODEPOINTS) + 1)
            if speech[end] > speech[start] and allowed(end) and cost[end] <= remaining
        ]
        if not candidates:
            raise ValueError("batch_text_partition_impossible")
        if size in candidates:
            end = size
        else:
            safe = [
                end for end in candidates if not unicodedata.category(text[end]).startswith("M")
            ]
            sentence = [
                end
                for end in safe
                if text[end - 1] in ".!?;:" and text[end].isspace()
            ]
            spaces = [end for end in safe if text[end - 1].isspace()]
            end = max(sentence or spaces or safe or candidates)
        parts.append(text[start:end])
        start = end
    return tuple(parts)


def _plain_path(path: Path, *, directory: bool = False) -> Path:
    """Local equivalent of lab._plain_path, without a worker import cycle."""
    path = path.absolute()
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("redirected_path_denied")
    info = path.stat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("directory_required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("regular_single_link_file_required")
    return Path(os.path.abspath(path))


def _fingerprint(info: os.stat_result) -> tuple[int, ...]:
    # Windows stat and fstat can report creation/change time differently. Device,
    # inode, size and mtime agree; a second PCM digest independently binds bytes.
    common = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    return common if os.name == "nt" else (*common, info.st_ctime_ns)


def _open_source(path: Path):
    path = _plain_path(path)
    before = path.stat()
    handle = path.open("rb")
    try:
        info = os.fstat(handle.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or _fingerprint(info) != _fingerprint(before)
            or _fingerprint(path.stat()) != _fingerprint(info)
        ):
            raise ValueError("audio_source_changed")
        _plain_path(path)
    except Exception:
        handle.close()
        raise
    return handle, _fingerprint(info)


def _check(deadline: float, cancelled: Callable[[], bool], clock: Callable[[], float]) -> None:
    try:
        stopped = cancelled()
        now = clock()
    except Exception:
        raise ValueError("audio_control_failed") from None
    if stopped:
        raise InterruptedError("cancelled")
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError("invalid_audio_clock")
    if now >= deadline:
        raise TimeoutError("deadline_exceeded")


def _riff_layout(handle, size: int, check: Callable[[], None]) -> None:
    """Reject truncated/ambiguous chunks that wave.open otherwise tolerates."""
    check()
    header = handle.read(12)
    if (
        len(header) != 12
        or header[:4] != b"RIFF"
        or header[8:] != b"WAVE"
        or struct.unpack("<I", header[4:8])[0] + 8 != size
    ):
        raise ValueError("invalid_wav_container")
    position = 12
    found_format = False
    found_data = False
    while position < size:
        check()
        chunk = handle.read(8)
        if len(chunk) != 8:
            raise ValueError("truncated_wav")
        kind, length = struct.unpack("<4sI", chunk)
        position += 8
        padded = length + (length % 2)
        if position + padded > size:
            raise ValueError("truncated_wav")
        if kind == b"fmt ":
            if found_format or found_data or length not in (16, 18):
                raise ValueError("unsupported_wav_format")
            fmt = handle.read(length)
            code, channels, rate, byte_rate, alignment, width = struct.unpack("<HHIIHH", fmt[:16])
            if (
                code != 1
                or channels != 1
                or not 8000 <= rate <= 96000
                or width != 16
                or alignment != 2
                or byte_rate != rate * 2
                or (length == 18 and fmt[16:] != b"\x00\x00")
            ):
                raise ValueError("unsupported_wav_format")
            found_format = True
            handle.seek(padded - length, 1)
        else:
            if kind == b"data":
                if not found_format or found_data or length == 0 or length % 2:
                    raise ValueError("invalid_wav_data")
                found_data = True
            handle.seek(padded, 1)
        position += padded
    if position != size or not found_format or not found_data:
        raise ValueError("invalid_wav_container")
    handle.seek(0)


def _inspect(path: Path, duration: float, check: Callable[[], None]):
    check()
    with_handle, fingerprint = _open_source(path)
    with with_handle as handle:
        if not 44 <= fingerprint[2] <= MAX_OUTPUT_BYTES:
            raise ValueError("wav_size_out_of_bounds")
        _riff_layout(handle, fingerprint[2], check)
        with wave.open(handle, "rb") as audio:
            rate, frames, channels = audio.getframerate(), audio.getnframes(), audio.getnchannels()
            if (
                audio.getsampwidth() != 2
                or audio.getcomptype() != "NONE"
                or channels != 1
                or not 8000 <= rate <= 96000
            ):
                raise ValueError("unsupported_wav_format")
            if not 0 < frames / rate <= duration:
                raise ValueError("wav_duration_out_of_bounds")
            digest = hashlib.sha256()
            has_signal = False
            remaining = frames
            while remaining:
                check()
                count = min(_READ_FRAMES, remaining)
                raw = audio.readframes(count)
                if len(raw) != count * 2:
                    raise ValueError("truncated_wav")
                has_signal = has_signal or any(raw)
                digest.update(raw)
                remaining -= count
            check()
            if not has_signal:
                raise ValueError("silent_output")
            if _fingerprint(os.fstat(handle.fileno())) != fingerprint:
                raise ValueError("audio_source_changed")
        return (rate, frames, channels), fingerprint, digest.digest()


def inspect_wav(path: Path, *, max_duration_seconds: float = 600) -> tuple[int, int, int]:
    """Validate plain local, complete, nonsilent mono PCM16 without loading an SDK."""
    if (
        type(max_duration_seconds) not in (int, float)
        or not math.isfinite(max_duration_seconds)
        or not 0 < max_duration_seconds <= MAX_TOTAL_SECONDS
    ):
        raise ValueError("invalid_wav_duration_limit")
    try:
        metadata, _, _ = _inspect(Path(path), max_duration_seconds, lambda: None)
        return metadata
    except (OSError, EOFError, wave.Error, struct.error, TypeError):
        raise ValueError("invalid_audio_source") from None


def assemble_wavs(
    parts: Sequence[Path],
    output_path: Path,
    *,
    deadline: float,
    cancelled: Callable[[], bool] = lambda: False,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[int, int, int]:
    """Publish exact PCM only after every part validates, with no-overwrite linking.

    A private, uniquely owned pending file is removed on failure; inputs and any
    preexisting/racing output are never deleted. A hard link atomically reserves
    the final name without POSIX rename's overwrite semantics. Filesystems that
    cannot provide that primitive fail closed instead of publishing partially.
    """
    if (
        type(deadline) not in (int, float)
        or not math.isfinite(deadline)
        or not callable(cancelled)
        or not callable(clock)
        or not isinstance(parts, (tuple, list))
        or not 1 <= len(parts) <= MAX_PARTS
    ):
        raise ValueError("invalid_audio_batch")
    pending = None
    pending_identity = None
    def check():
        _check(deadline, cancelled, clock)

    try:
        check()
        sources = tuple(_plain_path(Path(part)) for part in parts)
        output = Path(os.path.abspath(output_path))
        parent = _plain_path(output.parent, directory=True)
        if output in sources:
            raise ValueError("output_is_input")
        if os.path.lexists(output):
            raise ValueError("output_exists")
        inspected = [_inspect(source, MAX_PART_SECONDS, check) for source in sources]
        rate = inspected[0][0][0]
        frames = sum(item[0][1] for item in inspected)
        if any(item[0][0] != rate for item in inspected):
            raise ValueError("batch_format_mismatch")
        if frames / rate > MAX_TOTAL_SECONDS or 44 + frames * 2 > MAX_OUTPUT_BYTES:
            raise ValueError("batch_audio_out_of_bounds")
        check()
        candidate = parent / (".jarvis-audio-" + uuid.uuid4().hex + ".pending")
        with candidate.open("xb") as handle:
            pending = candidate
            created = os.fstat(handle.fileno())
            pending_identity = (created.st_dev, created.st_ino)
            os.chmod(pending, 0o600)
            with wave.open(handle, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(rate)
                audio.setnframes(frames)
                for source, (metadata, fingerprint, original_digest) in zip(sources, inspected):
                    check()
                    input_handle, current = _open_source(source)
                    with input_handle:
                        if current != fingerprint:
                            raise ValueError("audio_source_changed")
                        with wave.open(input_handle, "rb") as part:
                            if (
                                part.getframerate(), part.getnframes(), part.getnchannels()
                            ) != metadata:
                                raise ValueError("audio_source_changed")
                            remaining = metadata[1]
                            digest = hashlib.sha256()
                            while remaining:
                                check()
                                count = min(_READ_FRAMES, remaining)
                                raw = part.readframes(count)
                                if len(raw) != count * 2:
                                    raise ValueError("truncated_wav")
                                digest.update(raw)
                                audio.writeframesraw(raw)
                                check()
                                remaining -= count
                            if (
                                digest.digest() != original_digest
                                or _fingerprint(os.fstat(input_handle.fileno())) != fingerprint
                            ):
                                raise ValueError("audio_source_changed")
            handle.flush()
            os.fsync(handle.fileno())
        check()
        _plain_path(parent, directory=True)
        _plain_path(pending)
        pending_info = pending.stat()
        if (pending_info.st_dev, pending_info.st_ino) != pending_identity:
            raise ValueError("audio_pending_changed")
        if pending.stat().st_size != 44 + frames * 2:
            raise ValueError("invalid_assembled_audio")
        os.link(pending, output)
        pending.unlink()
        pending = None
        return rate, frames, 1
    except (TimeoutError, InterruptedError):
        raise
    except (OSError, EOFError, wave.Error, struct.error, TypeError):
        raise ValueError("audio_assembly_failed") from None
    finally:
        if pending is not None:
            try:
                pending_info = pending.lstat()
                if (pending_info.st_dev, pending_info.st_ino) == pending_identity:
                    pending.unlink()
            except OSError:
                # No broad cleanup or deletion of a possibly unrelated final.
                pass
