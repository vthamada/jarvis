"""Reviewed text -> isolated sovereign Core final -> opt-in local TTS laboratory.

No microphone, runtime capability promotion, provider credentials or default
production databases. The normal Core final is never shortened to fit TTS.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable
from uuid import uuid4

from apps.jarvis_console.voice_pilot import ReviewedVoiceCorePort, _isolated_core, pilot_identity
from apps.jarvis_voice import FinalSynthesis, VoiceRequest
from apps.jarvis_voice_lab import LabResult, run_voice_lab
from apps.jarvis_voice_lab.lab import ENGINES


@dataclass(frozen=True)
class LocalTtsPilotResult:
    status: str
    reason: str
    request_id: str
    memory_record_id: str
    governance_decision: str
    core_event_count: int
    final_character_count: int
    lab_result: LabResult | None = None

    @property
    def output_path(self) -> str | None:
        return self.lab_result.output_path if self.lab_result is not None else None

    def metadata(self) -> dict[str, object]:
        return {
            "pilot_mode": "isolated_core_to_local_tts_lab",
            "status": self.status,
            "reason": self.reason,
            "core_evidence_mode": "core_local",
            "audio_evidence_mode": self.lab_result.evidence_mode
            if self.lab_result is not None
            else "not_run",
            "runtime_mode": "temporary_sqlite",
            "runtime_capability_promoted": False,
            "operator_authenticated": False,
            "hardware_audio": False,
            "operation_dispatched": False,
            "authority": "none",
            "request_id": self.request_id,
            "memory_record_id": self.memory_record_id,
            "governance_decision": self.governance_decision,
            "core_event_count": self.core_event_count,
            "final_character_count": self.final_character_count,
            "lab": self.lab_result.metadata() if self.lab_result is not None else None,
        }


def _valid_text(text: object) -> bool:
    return (
        isinstance(text, str)
        and 1 <= len(text) <= 600
        and bool(text.strip())
        and not any(ord(character) < 32 and character not in "\n\r\t" for character in text)
        and not any(0xD800 <= ord(character) <= 0xDFFF for character in text)
    )


def run_local_tts_pilot(
    *,
    authorized: bool,
    reviewed_text: str,
    reference_path: Path,
    model_dir: Path,
    python_executable: Path,
    engine: str,
    workspace_root: Path,
    device: str = "cpu",
    sdk_source_dir: Path | None = None,
    timeout_seconds: float = 300,
    lab_runner: Callable[..., LabResult] | None = None,
) -> LocalTtsPilotResult:
    """Only bound, persisted Core final text may enter the explicitly enabled lab.

    A custom lab_runner is a fixture injection, not proof of model inference.
    The production voice path does not import or activate this research pilot.
    """
    if authorized is not True:
        raise ValueError("authorization_required")
    if not _valid_text(reviewed_text):
        raise ValueError("invalid_reviewed_text")
    if engine not in ENGINES or device not in {"cpu", "cuda:0"}:
        raise ValueError("invalid_engine_or_device")
    workspace = Path(workspace_root).absolute()
    base = Path(tempfile.gettempdir()).absolute()
    if base == workspace or workspace in base.parents:
        raise ValueError("temporary_directory_inside_workspace_denied")
    identifier = uuid4().hex
    identity = replace(
        pilot_identity(),
        surface_id="surface://isolated-local-tts-pilot",
        surface_session_id=f"session://isolated-local-tts-pilot-{identifier}",
    )
    with tempfile.TemporaryDirectory(prefix="jarvis-core-local-tts-", dir=base) as runtime:
        core = _isolated_core(Path(runtime))
        port = ReviewedVoiceCorePort(core, identity)
        request = VoiceRequest(
            f"voice-{identifier}", port.identity, reviewed_text, time.monotonic() + 30
        )
        final = port.interact(request)
        response = port.response
        if (
            not isinstance(final, FinalSynthesis)
            or final.request_id != request.request_id
            or final.identity != port.identity
            or final.status != "completed"
            or final.confirmed is not True
            or final.evidence_mode != "core_local"
            or response is None
            or response.response_text != final.text
            or response.request_id != request.request_id
            or response.session_id != identity.surface_session_id
            or response.operation_dispatch is not None
            or response.operation_result is not None
            or response.adapter_grant is not None
            or response.adapter_grant_claim is not None
            or response.action_confirmation_claim is not None
            or final.synthesis_ref != str(response.memory_record.memory_record_id)
            or response.memory_record.session_id != identity.surface_session_id
        ):
            raise ValueError("core_final_binding_refused")
        turns = core.memory_service.repository.fetch_recent_turns(identity.surface_session_id, 1)
        events = core.observability_service.repository.list_events(
            limit=100, request_id=request.request_id, session_id=identity.surface_session_id
        )
        names = {event.event_name for event in events}
        if (
            len(turns) != 1
            or turns[0].request_content != reviewed_text
            or turns[0].response_text != final.text
            or not {"governance_checked", "response_synthesized", "memory_recorded"} <= names
            or not response.governance_decision.decision_id
        ):
            raise ValueError("core_final_evidence_refused")
        result_fields = {
            "request_id": request.request_id,
            "memory_record_id": str(response.memory_record.memory_record_id),
            "governance_decision": response.governance_decision.decision.value,
            "core_event_count": len(events),
            "final_character_count": len(final.text),
        }
        if len(final.text) > 600:
            return LocalTtsPilotResult("refused", "final_text_too_long", **result_fields)
        if not _valid_text(final.text):
            return LocalTtsPilotResult("refused", "invalid_core_final_text", **result_fields)
        runner = run_voice_lab if lab_runner is None else lab_runner
        lab = runner(
            engine=engine,
            authorized=True,
            reference_path=reference_path,
            text=final.text,
            model_dir=model_dir,
            python_executable=python_executable,
            workspace_root=workspace,
            device=device,
            timeout_seconds=timeout_seconds,
            sdk_source_dir=sdk_source_dir,
            evidence_mode="model_real" if lab_runner is None else "fixture",
        )
        if (
            not isinstance(lab, LabResult)
            or lab.engine != engine
            or lab.evidence_mode != ("model_real" if lab_runner is None else "fixture")
        ):
            raise ValueError("lab_result_binding_refused")
        return LocalTtsPilotResult(lab.status, lab.reason, **result_fields, lab_result=lab)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--engine", choices=sorted(ENGINES), required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--device", choices=["cpu", "cuda:0"], default="cpu")
    parser.add_argument("--sdk-source-dir", type=Path)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--text-stdin", action="store_true", required=True)
    parser.add_argument("--show-output-path", action="store_true")
    args = parser.parse_args(argv)
    reviewed_text = sys.stdin.read(601)
    try:
        result = run_local_tts_pilot(
            authorized=args.authorized,
            reviewed_text=reviewed_text,
            reference_path=args.reference,
            model_dir=args.model_dir,
            python_executable=args.python,
            engine=args.engine,
            workspace_root=args.workspace,
            device=args.device,
            sdk_source_dir=args.sdk_source_dir,
            timeout_seconds=args.timeout,
        )
    except Exception:
        print(json.dumps({"status": "failed", "reason": "invalid_or_unavailable_local_pilot"}))
        return 2
    metadata = result.metadata()
    if args.show_output_path and result.output_path is not None:
        metadata["output_path"] = result.output_path
    print(json.dumps(metadata, ensure_ascii=True))
    return 0 if result.status == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
