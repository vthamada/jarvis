"""Bounded experimental voice profiles; no claim of perceptual improvement."""

from __future__ import annotations

import math

PROFILES = frozenset({"baseline", "chatterbox_conversational", "qwen_icl", "qwen_icl_draft"})


def validate_quality_options(
    *,
    engine,
    profile,
    reference_start_seconds,
    reference_duration_seconds,
    reference_transcript,
    transcript_confirmed,
    seed,
):
    if profile not in PROFILES:
        raise ValueError("invalid_voice_profile")
    for value in (reference_start_seconds, reference_duration_seconds):
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError("invalid_reference_window")
    if not 0 <= reference_start_seconds <= 900 or not 3 <= reference_duration_seconds <= 15:
        raise ValueError("invalid_reference_window")
    if seed is not None and (type(seed) is not int or not 0 <= seed <= 2**32 - 1):
        raise ValueError("invalid_seed")
    if type(transcript_confirmed) is not bool:
        raise ValueError("invalid_transcript_confirmation")
    if profile == "chatterbox_conversational" and engine != "chatterbox_pt_br":
        raise ValueError("profile_engine_mismatch")
    if profile in {"qwen_icl", "qwen_icl_draft"}:
        if engine != "qwen3_tts":
            raise ValueError("profile_engine_mismatch")
        if (
            transcript_confirmed is not (profile == "qwen_icl")
            or not isinstance(reference_transcript, str)
            or not 1 <= len(reference_transcript) <= 2000
            or not reference_transcript.strip()
            or any(ord(c) < 32 and c not in "\n\r\t" for c in reference_transcript)
            or any(0xD800 <= ord(c) <= 0xDFFF for c in reference_transcript)
        ):
            raise ValueError(
                "confirmed_reference_transcript_required"
                if profile == "qwen_icl"
                else "unconfirmed_draft_transcript_required"
            )
    elif reference_transcript is not None or transcript_confirmed:
        raise ValueError("unused_reference_transcript")
