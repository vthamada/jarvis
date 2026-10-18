"""Host-owned offline voice configuration. Browser input never selects paths."""

from __future__ import annotations

import json
import math
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from apps.jarvis_console.persistent_tts import (
    LocalFinalTtsConfig,
    _local_path_syntax,
    _local_volume,
    _validated_output,
    preflight_local_tts_config,
)
from apps.jarvis_voice_lab.asr_worker import validate_decoding_profile
from apps.jarvis_voice_lab.lab import _local_tree, _plain_path
from apps.jarvis_voice_lab.worker_lifecycle import WorkerExitUnconfirmed


@dataclass(frozen=True)
class LocalAsrConfig:
    model_dir: Path = field(repr=False)
    python_executable: Path = field(repr=False)
    device: str = "cpu"
    timeout_seconds: float = 300
    decoding_profile: str = "quality"

    def __post_init__(self):
        validate_decoding_profile(self.decoding_profile)


@dataclass(frozen=True)
class LocalVoiceProfile:
    asr: LocalAsrConfig | None = None
    tts: LocalFinalTtsConfig | None = None


def load_voice_profile(path: Path, workspace_root: Path) -> LocalVoiceProfile:
    """Read an explicitly selected private local file, never discover one."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("invalid_voice_profile")
            result[key] = value
        return result

    try:
        _local_path_syntax(path)
        _local_volume(path)
        path = _plain_path(path)
        if not 1 <= path.stat().st_size <= 16384:
            raise ValueError("invalid_voice_profile")
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
        if type(data) is not dict or set(data) != {"schema_version", "asr", "tts"}:
            raise ValueError("invalid_voice_profile")
        if data["schema_version"] != "jarvis-local-voice-profile-v1":
            raise ValueError("invalid_voice_profile")
        asr = tts = None
        if data["asr"] is not None:
            value = data["asr"]
            required = {"model_dir", "python_executable", "device", "timeout_seconds"}
            if (type(value) is not dict or not required <= set(value)
                    or set(value) - required - {"decoding_profile"}):
                raise ValueError("invalid_voice_profile")
            decoding = validate_decoding_profile(value.get("decoding_profile", "quality"))
            model, python = Path(value["model_dir"]), Path(value["python_executable"])
            timeout = value["timeout_seconds"]
            if (value["device"] not in {"cpu", "cuda:0"}
                    or type(timeout) not in {int, float} or not math.isfinite(timeout)
                    or not 0 < timeout <= 300):
                raise ValueError("invalid_voice_profile")
            for selected in (model, python):
                _local_path_syntax(selected)
                _local_volume(selected)
            _plain_path(model, directory=True)
            _local_tree(model)
            _plain_path(python)
            asr = LocalAsrConfig(model, python, value["device"], timeout, decoding)
        if data["tts"] is not None:
            if type(data["tts"]) is not dict:
                raise ValueError("invalid_voice_profile")
            value = dict(data["tts"])
            required = {"engine", "reference_path", "model_dir", "python_executable"}
            optional = {"device", "sdk_source_dir", "timeout_seconds", "voice_profile",
                        "reference_start_seconds", "reference_duration_seconds",
                        "reference_transcript", "transcript_confirmed", "seed"}
            if not required <= set(value) or set(value) - required - optional:
                raise ValueError("invalid_voice_profile")
            for key in required - {"engine"}:
                value[key] = Path(value[key])
            if value.get("sdk_source_dir") is not None:
                value["sdk_source_dir"] = Path(value["sdk_source_dir"])
            value.setdefault("timeout_seconds", 300)
            if value["timeout_seconds"] > 300:
                raise ValueError("invalid_voice_profile")
            tts = LocalFinalTtsConfig(authorized=True, workspace_root=workspace_root,
                                      batch_mode=True, **value)
            preflight_local_tts_config(tts)
        if asr is None and tts is None:
            raise ValueError("invalid_voice_profile")
        return LocalVoiceProfile(asr, tts)
    except Exception:
        raise ValueError("invalid_voice_profile") from None


def _capture_identity(capture: Path) -> tuple[int, int]:
    info = _plain_path(capture, directory=True).stat()
    return info.st_dev, info.st_ino


def _remove_capture(capture: Path, identity: tuple[int, int]) -> None:
    """Delete only our unchanged private capture after the worker boundary is safe."""
    try:
        if _capture_identity(capture) != identity:
            raise ValueError("capture_identity_changed")
        shutil.rmtree(capture)
    except Exception:
        # Preserve a replaced/locked capture, quarantine voice, and expose no path.
        raise WorkerExitUnconfirmed() from None


def transcribe_bytes(config: LocalAsrConfig, raw: bytes, cancelled) -> str:
    """Keep capture private; uncertainty retains it instead of racing worker exit."""

    from apps.jarvis_voice_lab.transcribe import transcribe_local_wav

    options = ({"decoding_profile": config.decoding_profile}
               if config.decoding_profile != "quality" else {})
    if sys.platform == "win32":
        options["confirm_worker_exit"] = True
    capture = Path(tempfile.mkdtemp(prefix="jarvis-web-capture-"))
    try:
        identity = _capture_identity(capture)
    except Exception:
        raise WorkerExitUnconfirmed() from None
    try:
        source = capture / "capture.wav"
        source.write_bytes(raw)
        result = transcribe_local_wav(
            authorized=True, source=source, model_dir=config.model_dir,
            python_executable=config.python_executable, device=config.device,
            timeout_seconds=config.timeout_seconds, cancelled=cancelled,
            private_output_root=capture,
            **options,
        )
        # The worker creates a reviewed-document draft, not a human-confirmed turn.
        document = json.loads(Path(result["segments_path"]).read_text(encoding="utf-8"))
        text = "\n".join(segment["text"] for segment in document["segments"])
    except WorkerExitUnconfirmed:
        # A launcher exit alone is not proof that the actual Windows worker exited.
        raise
    except BaseException:
        _remove_capture(capture, identity)
        raise
    _remove_capture(capture, identity)
    return text


def synthesize_bytes(config: LocalFinalTtsConfig, text: str, cancelled) -> bytes:
    """Render the exact, already bound canonical final, with no Core dispatch."""
    import hashlib

    from apps.jarvis_voice_lab.batch_audio import segment_text
    from apps.jarvis_voice_lab.lab_batch import run_voice_lab_batch

    preflight_local_tts_config(config)
    chunks = segment_text(text)
    result = run_voice_lab_batch(
        engine=config.engine, authorized=True, reference_path=config.reference_path,
        text=text, model_dir=config.model_dir, python_executable=config.python_executable,
        workspace_root=config.workspace_root, device=config.device,
        timeout_seconds=config.timeout_seconds, cancelled=cancelled,
        sdk_source_dir=config.sdk_source_dir, voice_profile=config.voice_profile,
        reference_start_seconds=config.reference_start_seconds,
        reference_duration_seconds=config.reference_duration_seconds,
        reference_transcript=config.reference_transcript,
        transcript_confirmed=config.transcript_confirmed, seed=config.seed,
    )
    if (result.status != "completed" or result.part_count != len(chunks)
            or result.completed_parts != len(chunks)
            or result.text_sha256 != hashlib.sha256(text.encode("utf-8")).hexdigest()
            or result.part_text_sha256 != tuple(hashlib.sha256(part.encode("utf-8")).hexdigest()
                                               for part in chunks)):
        raise ValueError("voice_unavailable")
    return Path(_validated_output(config, result, "model_real")).read_bytes()
