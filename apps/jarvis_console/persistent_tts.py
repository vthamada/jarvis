"""Explicit local speech of an already persisted sovereign final, never a new turn.

This complement generates an artifact, not playback or an action receipt. Model
inference and perceptual quality remain distinct from fixture evidence.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import struct
import tempfile
import time
import unicodedata
import wave
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Callable
from uuid import uuid4

from apps.jarvis_console.voice_pilot import ReviewedVoiceCorePort
from apps.jarvis_voice import FinalSynthesis, VoiceRequest
from apps.jarvis_voice_lab import LabResult, run_voice_lab
from apps.jarvis_voice_lab.batch_audio import inspect_wav, segment_text
from apps.jarvis_voice_lab.lab import ENGINES, _local_tree, _plain_path, _wav_metadata
from apps.jarvis_voice_lab.lab_batch import BatchLabResult, run_voice_lab_batch
from apps.jarvis_voice_lab.quality import validate_quality_options
from shared.events import InternalEventEnvelope


@dataclass(frozen=True)
class LocalFinalTtsConfig:
    authorized: bool
    engine: str
    reference_path: Path = field(repr=False)
    model_dir: Path = field(repr=False)
    python_executable: Path = field(repr=False)
    workspace_root: Path = field(repr=False)
    device: str = "cpu"
    sdk_source_dir: Path | None = field(default=None, repr=False)
    timeout_seconds: float = 300
    voice_profile: str = "baseline"
    reference_start_seconds: float = 0
    reference_duration_seconds: float = 10
    reference_transcript: str | None = field(default=None, repr=False)
    transcript_confirmed: bool = False
    seed: int | None = None
    batch_mode: bool = False


@dataclass(frozen=True)
class LocalFinalTtsResult:
    status: str
    reason: str
    engine: str
    audio_evidence_mode: str = "not_run"
    final_character_count: int = 0
    text_fallback_available: bool = True
    audit_event_recorded: bool = False
    output_path: str | None = field(default=None, repr=False)
    batch_mode: bool = False
    part_count: int = 0
    completed_parts: int = 0

    def metadata(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": self.reason,
            "engine": self.engine,
            "audio_evidence_mode": self.audio_evidence_mode,
            "artifact_available": self.status == "completed" and self.output_path is not None,
            "final_character_count": self.final_character_count,
            "text_fallback_available": self.text_fallback_available,
            "audit_event_recorded": self.audit_event_recorded,
            "authority": "none",
            "hardware_audio": False,
            "runtime_capability_promoted": False,
            "voice_quality_approved": False,
            "batch_mode": self.batch_mode,
            "part_count": self.part_count,
            "completed_parts": self.completed_parts,
        }


def _local_path_syntax(path: object) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("local_tts_path_refused")
    raw = str(path)
    if (
        raw.startswith(("\\\\", "//"))
        or "~" in raw
        or any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in raw)
        or ".." in path.parts
        or any(":" in part for part in path.parts[1:])
        or any(part.endswith((".", " ")) for part in path.parts[1:])
        or any(re.fullmatch(r"(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
               for part in path.parts[1:])
    ):
        raise ValueError("local_tts_path_refused")


def validate_local_tts_config(config: LocalFinalTtsConfig) -> None:
    """Pure validation: authorization and local syntax precede stdin/filesystem IO."""
    if not isinstance(config, LocalFinalTtsConfig) or config.authorized is not True:
        raise ValueError("local_tts_authorization_required")
    try:
        if config.engine not in ENGINES or config.device not in {"cpu", "cuda:0"}:
            raise ValueError("invalid_engine_or_device")
        if type(config.batch_mode) is not bool:
            raise ValueError("invalid_batch_mode")
        for path in (config.reference_path, config.model_dir, config.python_executable,
                     config.workspace_root):
            _local_path_syntax(path)
        if config.sdk_source_dir is not None:
            _local_path_syntax(config.sdk_source_dir)
            if config.engine != "chatterbox_pt_br":
                raise ValueError("sdk_source_engine_mismatch")
        if (type(config.timeout_seconds) not in (int, float)
                or not math.isfinite(config.timeout_seconds)
                or not 0 < config.timeout_seconds <= 1800):
            raise ValueError("invalid_timeout")
        validate_quality_options(
            engine=config.engine, profile=config.voice_profile,
            reference_start_seconds=config.reference_start_seconds,
            reference_duration_seconds=config.reference_duration_seconds,
            reference_transcript=config.reference_transcript,
            transcript_confirmed=config.transcript_confirmed, seed=config.seed,
        )
    except (TypeError, ValueError):
        raise ValueError("local_tts_config_refused") from None


def _local_volume(path: Path) -> None:
    """Read-only locality check, including Windows mapped network drives."""
    if os.name == "nt":
        import ctypes

        kind = ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor))
        if kind not in {2, 3, 6}:  # removable, fixed, RAM disk; never remote/unknown.
            raise ValueError("local_tts_volume_refused")


def _readonly_temp_base() -> Path:
    # A cold gettempdir() writes and deletes a probe. Preflight must not initialize
    # that cache or create any file; the lab independently chooses/revalidates its
    # actual temp directory after the explicit Core turn.
    if tempfile.tempdir is not None:
        candidate = Path(tempfile.gettempdir())
        _local_path_syntax(candidate)
        _local_volume(candidate)
        return _plain_path(candidate, directory=True)
    for name in tempfile._candidate_tempdir_list():
        try:
            candidate = Path(name)
            _local_path_syntax(candidate)
            _local_volume(candidate)
            base = _plain_path(candidate, directory=True)
            if os.access(base, os.W_OK | os.X_OK):
                return base
        except (OSError, ValueError):
            continue
    raise ValueError("local_tts_temp_unavailable")


def preflight_local_tts_config(config: LocalFinalTtsConfig) -> None:
    """Read-only preflight. No Core bootstrap, subprocess, or output is created."""
    validate_local_tts_config(config)
    try:
        for path in (config.workspace_root, config.reference_path, config.model_dir,
                     config.python_executable, config.sdk_source_dir):
            if path is not None:
                _local_volume(path)
        workspace = _plain_path(config.workspace_root, directory=True)
        source = _plain_path(config.reference_path)
        model = _plain_path(config.model_dir, directory=True)
        _local_tree(model)
        _plain_path(config.python_executable)
        if config.sdk_source_dir is not None:
            sdk = _plain_path(config.sdk_source_dir, directory=True)
            _plain_path(sdk / "chatterbox" / "src" / "chatterbox" / "tts.py")
            _local_tree(sdk)
        rate, frames, channels = _wav_metadata(source, source=True)
        start = int(config.reference_start_seconds * rate)
        count = int(config.reference_duration_seconds * rate)
        if start + count > frames:
            raise ValueError("reference_window_out_of_bounds")
        with wave.open(str(source), "rb") as audio:
            audio.setpos(start)
            raw = audio.readframes(count)
        if len(raw) != count * channels * 2:
            raise ValueError("truncated_reference_window")
        signal = any(raw) if channels == 1 else any(
            (left + right) // 2 for left, right in struct.iter_unpack("<hh", raw)
        )
        if not signal:
            raise ValueError("silent_reference_window")
        base = _readonly_temp_base()
        if base == workspace or workspace in base.parents:
            raise ValueError("temporary_directory_inside_workspace_denied")
    except Exception:
        raise ValueError("local_tts_preflight_refused") from None


def _bound_final(port, request, final) -> bool:
    if not isinstance(port, ReviewedVoiceCorePort):
        return False
    response = port.response
    if (
        not isinstance(request, VoiceRequest) or not isinstance(final, FinalSynthesis)
        or request.identity != port.identity or request.authority != "none"
        or request.input_mode not in {"reviewed_local_transcript", "reviewed_voice_fixture"}
        or final.request_id != request.request_id or final.identity != port.identity
        or final.status != "completed" or final.confirmed is not True
        or final.evidence_mode != "core_local" or response is None
        or response.request_id != request.request_id
        or response.session_id != port.identity.surface_session_id
        or response.response_text != final.text
        or any(getattr(response, field) is not None for field in (
            "operation_dispatch", "operation_result", "adapter_grant", "adapter_grant_claim",
            "action_confirmation_claim"))
        or final.synthesis_ref != str(response.memory_record.memory_record_id)
        or not response.memory_record.memory_record_id
        or response.memory_record.session_id != port.identity.surface_session_id
        or response.memory_record.record_type != "interaction_turn"
        or response.memory_record.payload.get("request_content") != request.text
        or response.memory_record.payload.get("response_text") != final.text
        or response.memory_record.payload.get("governance_decision")
        != response.governance_decision.decision.value
        or not response.governance_decision.decision_id
        or port.core.observability_service.agentic_adapter is not None
    ):
        return False
    memory = port.core.memory_service.repository
    observability = port.core.observability_service.repository
    # The promoted product slice is local persistent SQLite, not :memory: or
    # a future unverified remote backend.
    for repository in (memory, observability):
        database = getattr(repository, "database_path", None)
        if not isinstance(database, Path) or not database.is_file():
            return False
    turns = memory.fetch_recent_turns(port.identity.surface_session_id, 1)
    events = observability.list_events(
        limit=100, request_id=request.request_id, session_id=port.identity.surface_session_id
    )
    return (
        len(turns) == 1 and turns[0].request_content == request.text
        and turns[0].response_text == final.text
        and {"governance_checked", "response_synthesized", "memory_recorded"}
        <= {event.event_name for event in events}
        and any(event.event_name == "memory_recorded"
                and event.payload.get("memory_record_id") == final.synthesis_ref
                and event.payload.get("record_type") == "interaction_turn" for event in events)
        and any(event.event_name == "governance_checked"
                and event.payload.get("decision") == response.governance_decision.decision.value
                for event in events)
    )


def _audit(port, request, name: str, result: LocalFinalTtsResult) -> bool:
    try:
        if port.core.observability_service.agentic_adapter is not None:
            return False
        event = InternalEventEnvelope(
            event_id=f"local-final-tts-{uuid4().hex}", event_name=name,
            timestamp=datetime.now(UTC).isoformat(), source_service="jarvis-console",
            payload=result.metadata(), request_id=request.request_id,
            session_id=port.identity.surface_session_id,
            tags=["local_final_tts", "authority_none"],
        )
        # This complement is strictly local: do not traverse adapter emission,
        # including a tracing adapter changed concurrently after the check.
        repository = port.core.observability_service.repository
        repository.record_event(event)
        return event in repository.list_events(
            limit=100, event_names=(name,), request_id=request.request_id,
            session_id=port.identity.surface_session_id,
        )
    except Exception:
        return False


def _validated_output(config: LocalFinalTtsConfig, lab: LabResult, mode: str) -> str:
    if (
        not isinstance(lab, LabResult) or lab.engine != config.engine
        or lab.evidence_mode != mode or lab.status != "completed"
        or lab.reason != ("fixture_only" if mode == "fixture" else "local_sample_generated")
        or lab.voice_profile != config.voice_profile
        or lab.reference_transcript_reviewed is not (
            config.transcript_confirmed if config.voice_profile in {"qwen_icl", "qwen_icl_draft"}
            else None)
        or not isinstance(lab.run_id, str)
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", lab.run_id)
        or not isinstance(lab.output_path, str)
    ):
        raise ValueError("local_tts_output_refused")
    output = Path(lab.output_path)
    _local_path_syntax(output)
    _local_volume(output)
    output = _plain_path(output)
    base = _plain_path(Path(tempfile.gettempdir()), directory=True)
    workspace = _plain_path(config.workspace_root, directory=True)
    if (
        output.name != "sample.wav" or output.parent.parent != base
        or not output.parent.name.startswith(f"jarvis-voice-lab-{lab.run_id}-")
        or output == config.reference_path or workspace in output.parents
    ):
        raise ValueError("local_tts_output_refused")
    rate, frames, channels = (inspect_wav(output) if config.batch_mode
                              else _wav_metadata(output, source=False))
    if (
        channels != 1 or type(lab.sample_rate) is not int or lab.sample_rate != rate
        or type(lab.duration_seconds) not in (int, float)
        or not math.isfinite(lab.duration_seconds) or lab.duration_seconds != frames / rate
        or not isinstance(lab.output_digest, str)
        or not re.fullmatch(r"[0-9a-f]{64}", lab.output_digest)
        or hashlib.sha256(output.read_bytes()).hexdigest() != lab.output_digest
    ):
        raise ValueError("local_tts_output_refused")
    return str(output)


def speak_persisted_final(
    *, config: LocalFinalTtsConfig, port: ReviewedVoiceCorePort, request: VoiceRequest,
    final: FinalSynthesis, lab_runner: Callable[..., LabResult] | None = None,
) -> LocalFinalTtsResult:
    """Bind, audit and render the exact existing final once; all failures keep text.

    Callers must preflight before submitting the Core turn. This function repeats
    preflight against changed files, but never calls handle_input or retries.
    A supplied runner is fixture evidence regardless of its reported claims.
    """
    started = time.monotonic()
    result = LocalFinalTtsResult(
        "refused", "local_tts_config_refused",
        config.engine if isinstance(config, LocalFinalTtsConfig)
        and isinstance(config.engine, str) and config.engine in ENGINES
        else "unavailable",
        final_character_count=len(final.text) if isinstance(final, FinalSynthesis)
        and isinstance(final.text, str) else 0,
        batch_mode=config.batch_mode is True if isinstance(config, LocalFinalTtsConfig) else False,
    )
    try:
        validate_local_tts_config(config)
    except Exception:
        return result
    try:
        bound = _bound_final(port, request, final)
    except Exception:
        bound = False
    if not bound:
        return replace(result, reason="core_final_binding_refused")
    deadline = started + config.timeout_seconds

    def finish(status: str, reason: str, **fields) -> LocalFinalTtsResult:
        if config.batch_mode and time.monotonic() >= deadline:
            status, reason = "timed_out", "deadline_exceeded"
            fields["output_path"] = None
        record = replace(result, status=status, reason=reason, **fields)
        audited = _audit(port, request, "local_final_tts_finished", record)
        if config.batch_mode and time.monotonic() >= deadline and status == "completed":
            # Audit persistence/readback is also inside the one campaign deadline.
            # Its earlier completion candidate is superseded by this refusal.
            record = replace(record, status="timed_out", reason="deadline_exceeded",
                             output_path=None)
            audited = _audit(port, request, "local_final_tts_finished", record)
            return replace(record, audit_event_recorded=audited)
        if status == "completed" and not audited:
            return replace(record, status="failed", reason="local_tts_audit_unavailable",
                           output_path=None, audit_event_recorded=False)
        return replace(record, audit_event_recorded=audited)

    if getattr(port, "_local_final_tts_attempted_request_id", None) == request.request_id:
        return finish("refused", "final_tts_already_attempted")
    if not isinstance(final.text, str) or not final.text.strip() or any(
        unicodedata.category(c) in {"Cf", "Cs"}
        or (unicodedata.category(c) == "Cc" and c not in "\r\n\t") for c in final.text
    ):
        return finish("refused", "invalid_core_final_text")
    if not config.batch_mode and len(final.text) > 600:
        return finish("refused", "final_text_too_long")
    chunks = ()
    if config.batch_mode:
        try:
            chunks = segment_text(final.text)
            result = replace(result, part_count=len(chunks))
        except Exception:
            return finish("refused", "batch_text_refused")
    try:
        preflight_local_tts_config(config)
    except Exception:
        return finish("refused", "local_tts_preflight_refused")
    mode = "model_real" if lab_runner is None else "fixture"
    lock = port.__dict__.setdefault("_local_final_tts_lock", RLock())
    with lock:
        if getattr(port, "_local_final_tts_attempted_request_id", None) == request.request_id:
            return finish("refused", "final_tts_already_attempted")
        # Consume before audit/runner callbacks. Concurrent and reentrant calls
        # cannot produce a second artifact; audit failure does not permit retry.
        port._local_final_tts_attempted_request_id = request.request_id
    if not _audit(port, request, "local_final_tts_requested", replace(
        result, status="requested", reason="explicit_local_tts_requested", audio_evidence_mode=mode
    )):
        return replace(result, reason="local_tts_audit_unavailable")
    default_runner = run_voice_lab_batch if config.batch_mode else run_voice_lab
    runner = default_runner if lab_runner is None else lab_runner
    try:
        timeout = deadline - time.monotonic() if config.batch_mode else config.timeout_seconds
        if timeout <= 0:
            return finish("timed_out", "deadline_exceeded")
        lab = runner(
            engine=config.engine, authorized=True, reference_path=config.reference_path,
            text=final.text, model_dir=config.model_dir, python_executable=config.python_executable,
            workspace_root=config.workspace_root, device=config.device,
            timeout_seconds=timeout, sdk_source_dir=config.sdk_source_dir,
            voice_profile=config.voice_profile,
            reference_start_seconds=config.reference_start_seconds,
            reference_duration_seconds=config.reference_duration_seconds,
            reference_transcript=config.reference_transcript,
            transcript_confirmed=config.transcript_confirmed, seed=config.seed, evidence_mode=mode,
        )
        if (not isinstance(lab, LabResult) or lab.engine != config.engine
                or lab.evidence_mode != mode):
            return finish("failed", "local_tts_output_refused", audio_evidence_mode=mode)
        if config.batch_mode:
            if (not isinstance(lab, BatchLabResult) or type(lab.part_count) is not int
                    or type(lab.completed_parts) is not int or lab.part_count != len(chunks)
                    or not 0 <= lab.completed_parts <= len(chunks)):
                return finish("failed", "local_tts_output_refused", audio_evidence_mode=mode)
            result = replace(result, completed_parts=lab.completed_parts)
        if lab.status != "completed":
            status = lab.status if lab.status in {"failed", "cancelled", "timed_out"} else "failed"
            reason = lab.reason if lab.reason in {
                "sdk_unavailable", "sdk_incompatible", "local_inference_failed",
                "deadline_exceeded", "cancelled", "invalid_audio_output",
            } else "local_tts_generation_failed"
            return finish(status, reason, audio_evidence_mode=mode)
        if config.batch_mode and (
            lab.completed_parts != len(chunks)
            or lab.text_sha256 != hashlib.sha256(final.text.encode("utf-8")).hexdigest()
            or type(lab.part_text_sha256) is not tuple
            or lab.part_text_sha256 != tuple(hashlib.sha256(part.encode("utf-8")).hexdigest()
                                            for part in chunks)
        ):
            return finish("failed", "local_tts_output_refused", audio_evidence_mode=mode)
        output = _validated_output(config, lab, mode)
    except Exception:
        return finish("failed", "local_tts_generation_failed", audio_evidence_mode=mode)
    return finish("completed", "fixture_only" if mode == "fixture" else "local_sample_generated",
                  audio_evidence_mode=mode, output_path=output)
