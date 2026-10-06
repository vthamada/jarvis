"""Bounded read-only energy-edge suggestions, not speech/identity/quality detection."""

from __future__ import annotations

import math
import struct
import wave
from dataclasses import asdict, dataclass
from pathlib import Path

from .lab import _wav_metadata


@dataclass(frozen=True)
class ReferenceWindow:
    start_seconds: float
    duration_seconds: float
    start_edge_dbfs: float
    end_edge_dbfs: float
    rms_dbfs: float
    energetic_fraction: float
    low_energy_edges: bool
    selection_mode: str = "energy_edges_only"
    human_review_required: bool = True

    def metadata(self):
        return asdict(self)


def _dbfs(rms):
    return round(20 * math.log10(max(rms, 1e-8)), 2)


def suggest_reference_windows(
    source: Path,
    *,
    anchor_seconds: float,
    search_radius_seconds: float = 8,
    target_duration_seconds: float = 10,
    count: int = 3,
) -> tuple[ReferenceWindow, ...]:
    """Suggest nearby cuts at relatively quiet 20ms blocks. Never alters the WAV.

    Energy cannot distinguish speech from music/noise or ensure complete words.
    Returned references always require human review. No automatic ICL approval.
    """
    for value in (anchor_seconds, search_radius_seconds, target_duration_seconds):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("invalid_reference_search")
    if (
        not 0 <= anchor_seconds <= 900
        or not 2 <= search_radius_seconds <= 15
        or not 3 <= target_duration_seconds <= 15
        or type(count) is not int
        or not 1 <= count <= 5
    ):
        raise ValueError("invalid_reference_search")
    rate, frames, channels = _wav_metadata(source, source=True)
    if anchor_seconds >= frames / rate:
        raise ValueError("reference_anchor_out_of_bounds")
    block_frames = max(1, int(rate * 0.02))
    begin = int(max(0, anchor_seconds - search_radius_seconds) * rate)
    stop = min(frames, int((anchor_seconds + search_radius_seconds + 15) * rate))
    with wave.open(str(source), "rb") as audio:
        audio.setpos(begin)
        raw = audio.readframes(stop - begin)
    if len(raw) != (stop - begin) * channels * 2:
        raise ValueError("truncated_reference_search")
    values = [
        sum(pair) / channels / 32768
        for pair in struct.iter_unpack("<h" if channels == 1 else "<hh", raw)
    ]
    energy = [
        sum(v * v for v in values[i : i + block_frames]) / block_frames
        for i in range(0, len(values) - block_frames + 1, block_frames)
    ]
    prefix, active = [0.0], [0]
    quiet_power = 10 ** (-35 / 10)
    for power in energy:
        prefix.append(prefix[-1] + power)
        active.append(active[-1] + (power > quiet_power))
    block_seconds = block_frames / rate
    minimum = math.ceil(max(3, target_duration_seconds - 1.5) / block_seconds)
    maximum = math.floor(min(15, target_duration_seconds + 1.5) / block_seconds)
    candidates = []
    for start in range(len(energy)):
        absolute_start = (begin + start * block_frames) / rate
        if absolute_start > anchor_seconds + search_radius_seconds:
            break
        for end in range(start + minimum, min(len(energy), start + maximum) + 1):
            size = end - start
            fraction = (active[end] - active[start]) / size
            if fraction < 0.5:
                continue
            duration = size * block_seconds
            score = math.sqrt(energy[start]) + math.sqrt(energy[end - 1])
            score += 0.005 * abs(duration - target_duration_seconds)
            candidates.append((score, absolute_start, duration, start, end, fraction))
    chosen = []
    for _, start_seconds, duration, start, end, fraction in sorted(candidates):
        if any(abs(start_seconds - item.start_seconds) < 1.5 for item in chosen):
            continue
        chosen.append(
            ReferenceWindow(
                start_seconds=start_seconds,
                duration_seconds=duration,
                start_edge_dbfs=_dbfs(math.sqrt(energy[start])),
                end_edge_dbfs=_dbfs(math.sqrt(energy[end - 1])),
                rms_dbfs=_dbfs(math.sqrt((prefix[end] - prefix[start]) / (end - start))),
                energetic_fraction=round(fraction, 3),
                low_energy_edges=energy[start] <= quiet_power and energy[end - 1] <= quiet_power,
            )
        )
        if len(chosen) == count:
            break
    return tuple(chosen)
