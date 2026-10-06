# ruff: noqa: E402
"""Reviewed voice fixture -> sovereign Core -> synthetic speech, entirely local.

This opt-in pilot uses a temporary runtime. It does not open audio devices,
authenticate users, invoke model providers or promote a runtime capability.
"""

from __future__ import annotations

import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from apps.jarvis_voice import (
    AudioFixture,
    FinalSynthesis,
    FixtureSttPort,
    FixtureTtsPort,
    VoiceHarness,
    VoiceIdentity,
    VoiceRequest,
)
from apps.jarvis_voice.transcript_review import LocalTranscriptReview
from shared.contracts import InputContract, SurfaceIdentityContract
from shared.types import ChannelType, InputType, RequestId, SessionId


class _LocalOnlyObservability(ObservabilityService):
    @staticmethod
    def _build_agentic_adapter():
        return None


def _isolated_core(runtime: Path) -> OrchestratorService:
    governance = GovernanceService()
    return OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(runtime / 'memory.db').as_posix()}"
        ),
        observability_service=_LocalOnlyObservability(database_path=str(runtime / "events.db")),
        operational_service=OperationalService(
            artifact_dir=str(runtime / "artifacts"),
            action_confirmation_verifier=governance.verify_action_confirmation_claim,
        ),
    )


class ReviewedVoiceCorePort:
    """Trusted local composition, not an authentication or confirmation endpoint.

    Confirmation of transcription grants no action receipt. The normal Core path
    alone interprets, governs, records the turn and produces the final answer.
    """

    def __init__(
        self,
        core: OrchestratorService,
        identity: SurfaceIdentityContract,
        *,
        clock: Callable[[], float] = time.monotonic,
        transcript_review: LocalTranscriptReview | None = None,
    ):
        if (transcript_review is not None
                and not isinstance(transcript_review, LocalTranscriptReview)):
            raise ValueError("voice_core_review_invalid")
        self.core = core
        self.identity = VoiceIdentity.from_surface(identity)
        self.clock = clock
        self.response = None
        self.transcript_review = transcript_review

    def interact(self, request: VoiceRequest) -> FinalSynthesis:
        now = self.clock()
        if (
            not isinstance(request, VoiceRequest)
            or request.identity != self.identity
            or request.authority != "none"
            or request.input_mode not in {"reviewed_voice_fixture", "reviewed_local_transcript"}
            or not isinstance(request.request_id, str)
            or not re.fullmatch(r"voice-[A-Za-z0-9_-]{1,94}", request.request_id)
            or not isinstance(request.text, str)
            or not 1 <= len(request.text) <= 4000
            or not request.text.strip()
            or any(0xD800 <= ord(char) <= 0xDFFF for char in request.text)
            or any(ord(char) < 32 and char not in "\n\r\t" for char in request.text)
            or type(request.deadline) not in (float, int)
            or not math.isfinite(request.deadline)
            or type(now) not in (float, int)
            or not math.isfinite(now)
            or now >= request.deadline
        ):
            raise ValueError("voice_core_input_refused")
        # A local-review port cannot be downgraded into the legacy fixture path.
        # Consumption is atomic before dispatch; after this boundary revocation
        # cannot unsend a turn or undo canonical memory.
        if self.transcript_review is not None:
            if (request.input_mode != "reviewed_local_transcript"
                    or not self.transcript_review.take_request(request)):
                raise ValueError("voice_core_review_refused")
        elif request.input_mode == "reviewed_local_transcript":
            raise ValueError("voice_core_review_refused")
        identity = self.identity
        response = self.core.handle_input(
            InputContract(
                request_id=RequestId(request.request_id),
                session_id=SessionId(identity.surface_session_id),
                channel=ChannelType.VOICE,
                input_type=InputType.TEXT,
                content=request.text,
                timestamp=datetime.now(timezone.utc).isoformat(),
                surface_id=identity.surface_id,
                surface_kind=identity.surface_kind,
                surface_session_id=identity.surface_session_id,
                surface_capability_scope=[],
                operator_identity_ref=identity.operator_identity_ref,
                canonical_user_ref=identity.canonical_user_ref,
                requested_autonomy_level="assist_only",
                max_autonomy_level="assist_only",
            )
        )
        # Only a returned Core final turn can become the TTS input. This is not a
        # signed attestation; the reference identifies the Core's memory record.
        if (
            response.request_id != request.request_id
            or response.session_id != identity.surface_session_id
            or response.operation_dispatch is not None
            or response.operation_result is not None
            or not response.memory_record.memory_record_id
        ):
            raise ValueError("voice_core_final_refused")
        self.response = response
        return FinalSynthesis(
            request.request_id,
            identity,
            response.response_text,
            str(response.memory_record.memory_record_id),
            evidence_mode="core_local",
        )


def pilot_identity() -> SurfaceIdentityContract:
    return SurfaceIdentityContract(
        surface_id="surface://isolated-voice-pilot",
        surface_kind="voice",
        surface_session_id="session://isolated-voice-pilot",
        surface_capability_scope=[],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
    )


def run_voice_pilot() -> dict[str, object]:
    """Known synthetic input; output metadata omits audio and transcript content."""
    identity = pilot_identity()
    with TemporaryDirectory(prefix="jarvis-voice-pilot-") as runtime:
        port = ReviewedVoiceCorePort(_isolated_core(Path(runtime)), identity)
        tts = FixtureTtsPort()
        harness = VoiceHarness(identity=identity, stt=FixtureSttPort(), tts=tts, core=port)
        harness.consent(identity, granted=True)
        ticket = harness.start_capture(identity)
        if not harness.finish_capture(ticket, AudioFixture(b"\x01\x00" * 16)):
            raise ValueError("voice_pilot_capture_failed")
        revision = harness.snapshot()["transcript_revision"]
        if not harness.confirm_submission(ticket, identity=identity, transcript_revision=revision):
            raise ValueError("voice_pilot_submission_failed")
        if not harness.speak_final(ticket) or not harness.complete_playback(ticket):
            raise ValueError("voice_pilot_speech_failed")
        response = port.response
        return {
            "pilot_mode": "isolated_voice_fixture",
            "state": harness.snapshot()["state"],
            "core_evidence_mode": "core_local",
            "audio_evidence_mode": "synthetic_fixture",
            "hardware_audio": False,
            "runtime_capability_promoted": False,
            "operator_authenticated": False,
            "runtime_mode": "temporary_sqlite",
            "operation_dispatched": response.operation_dispatch is not None,
            "memory_record_id": str(response.memory_record.memory_record_id),
            "governance_decision": response.governance_decision.decision.value,
            "core_event_count": len(response.events),
            "voice_event_count": len(harness.events()),
            "synthetic_speech_count": tts.synthesis_count,
        }


def main() -> int:
    print(json.dumps(run_voice_pilot(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
