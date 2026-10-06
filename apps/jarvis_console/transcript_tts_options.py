"""Explicit local TTS options, independent of transcript/Core authorization.

Defaults are deliberately absent: a TTS argument cannot silently activate or
configure audio without its own opt-in. Parsing and configuration do no file
inspection, source-audio reading, model loading or Core bootstrap.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.persistent_tts import (
    LocalFinalTtsConfig,
    validate_local_tts_config,
)

_FIELDS = (
    "tts_authorized", "tts_engine", "tts_reference", "tts_model_dir",
    "tts_python", "tts_workspace", "tts_device", "tts_sdk_source_dir",
    "tts_timeout", "tts_voice_profile", "tts_reference_start",
    "tts_reference_duration", "tts_reference_transcript",
    "tts_transcript_confirmed", "tts_seed", "tts_show_output_path", "tts_batch",
)


def add_transcript_tts_arguments(parser: ArgumentParser) -> None:
    """Register optional local audio flags with no implicit authorization."""
    group = parser.add_argument_group("Explicit local final-response TTS")
    group.add_argument("--tts-authorized", action="store_true", default=None,
                       help="Authorize local synthesis separately from the Core turn.")
    group.add_argument("--tts-batch", action="store_true", default=None,
                       help="Render the exact complete final in one bounded local SDK campaign.")
    group.add_argument("--tts-engine", default=None)
    group.add_argument("--tts-reference", default=None)
    group.add_argument("--tts-model-dir", default=None)
    group.add_argument("--tts-python", default=None)
    group.add_argument("--tts-workspace", default=None)
    group.add_argument("--tts-device", default=None)
    group.add_argument("--tts-sdk-source-dir", default=None)
    group.add_argument("--tts-timeout", type=float, default=None)
    group.add_argument("--tts-voice-profile", default=None)
    group.add_argument("--tts-reference-start", type=float, default=None)
    group.add_argument("--tts-reference-duration", type=float, default=None)
    group.add_argument("--tts-reference-transcript", default=None)
    group.add_argument("--tts-transcript-confirmed", action="store_true", default=None)
    group.add_argument("--tts-seed", type=int, default=None)
    group.add_argument("--tts-show-output-path", action="store_true", default=None,
                       help="Display a safe temporary artifact locator when available "
                            "(private paths stay redacted).")


def _path(value: object) -> Path:
    # Do not stringify arbitrary objects: their representation can execute code
    # or carry sensitive details. Path construction itself does no filesystem IO.
    if type(value) is not str or not value or not value.strip():
        raise ValueError("transcript_tts_config_refused")
    return Path(value)


def _default(value: object, fallback: object) -> object:
    return fallback if value is None else value


def transcript_tts_config(args: Namespace) -> LocalFinalTtsConfig | None:
    """Pure pre-stdin validation; return None only when audio was not requested.

    Path existence and runtime preflight belong to the explicit handoff after
    envelope validation. This function never exposes caller strings in errors.
    Older console Namespaces lacking TTS fields retain their text-only behavior.
    """
    try:
        supplied = {name: getattr(args, name, None) for name in _FIELDS}
        if all(value is None for value in supplied.values()):
            return None
        if supplied["tts_authorized"] is not True:
            raise ValueError("transcript_tts_config_refused")
        for name in ("tts_transcript_confirmed", "tts_show_output_path", "tts_batch"):
            if supplied[name] is not None and type(supplied[name]) is not bool:
                raise ValueError("transcript_tts_config_refused")
        sdk = supplied["tts_sdk_source_dir"]
        workspace = supplied["tts_workspace"]
        config = LocalFinalTtsConfig(
            authorized=True,
            engine=supplied["tts_engine"],
            reference_path=_path(supplied["tts_reference"]),
            model_dir=_path(supplied["tts_model_dir"]),
            python_executable=_path(supplied["tts_python"]),
            workspace_root=ROOT if workspace is None else _path(workspace),
            device=_default(supplied["tts_device"], "cpu"),
            sdk_source_dir=None if sdk is None else _path(sdk),
            timeout_seconds=_default(supplied["tts_timeout"], 300),
            voice_profile=_default(supplied["tts_voice_profile"], "baseline"),
            reference_start_seconds=_default(supplied["tts_reference_start"], 0),
            reference_duration_seconds=_default(supplied["tts_reference_duration"], 10),
            reference_transcript=supplied["tts_reference_transcript"],
            transcript_confirmed=_default(supplied["tts_transcript_confirmed"], False),
            seed=supplied["tts_seed"],
            batch_mode=_default(supplied["tts_batch"], False),
        )
        validate_local_tts_config(config)
        return config
    except Exception:
        raise ValueError("transcript_tts_config_refused") from None
