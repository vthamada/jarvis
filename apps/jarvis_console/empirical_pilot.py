"""Empirical evaluator -> two isolated, sovereign Core instances.

Both arms intentionally run the same revision. This demonstrates the real pipeline,
not a JARVIS improvement, intelligence benchmark or capability promotion.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

from apps.jarvis_console.voice_pilot import _isolated_core
from evolution.empirical_runner import (
    CORPUS_DIGEST,
    CORPUS_VERSION,
    Arm,
    EmpiricalRunner,
    EvaluationRequest,
    EvaluationResponse,
)
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId

CONTROL_REVISION = "same_revision_control"
RUN_ID = "empirical-core-control"


class IsolatedEmpiricalCorePort:
    """Trusted experimental composition, not an authenticated public adapter."""

    def __init__(self, core, arm_id: str, *, clock: Callable[[], float] = time.monotonic):
        if arm_id not in ("baseline", "candidate"):
            raise ValueError("unsupported_control_arm")
        self.core = core
        self.arm_id = arm_id
        self.clock = clock
        self.session_ref = f"session://empirical-core-control-{arm_id}"
        self.turn_count = 0
        self.event_count = 0
        self.memory_record_count = 0
        self.operation_dispatch_observed = False
        self.governance_decisions: dict[str, int] = {}

    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        now = self.clock()
        if (
            not isinstance(request, EvaluationRequest)
            or request.run_id != RUN_ID
            or request.arm_id != self.arm_id
            or request.arm_revision != CONTROL_REVISION
            or request.evidence_mode != "core_local"
            or request.corpus_version != CORPUS_VERSION
            or request.corpus_digest != CORPUS_DIGEST
            or not isinstance(request.request_id, str)
            or not re.fullmatch(r"[a-f0-9]{64}", request.request_id)
            or not isinstance(request.prompt, str)
            or not 1 <= len(request.prompt) <= 2000
            or not request.prompt.strip()
            or any(ord(c) < 32 and c not in "\r\n\t" for c in request.prompt)
            or any(0xD800 <= ord(c) <= 0xDFFF for c in request.prompt)
            or type(request.deadline) not in (int, float)
            or not math.isfinite(request.deadline)
            or type(now) not in (int, float)
            or not math.isfinite(now)
            or now >= request.deadline
        ):
            raise ValueError("empirical_core_input_refused")
        digest = hashlib.sha256(
            json.dumps(request.prompt, ensure_ascii=True, separators=(",", ":")).encode()
        ).hexdigest()
        if digest != request.input_digest:
            raise ValueError("empirical_input_digest_mismatch")
        response = self.core.handle_input(
            InputContract(
                request_id=RequestId(request.request_id),
                session_id=SessionId(self.session_ref),
                channel=ChannelType.CHAT,
                input_type=InputType.TEXT,
                content=request.prompt,
                timestamp=datetime.now(timezone.utc).isoformat(),
                surface_id=f"surface://empirical-core-control-{self.arm_id}",
                surface_kind="console",
                surface_session_id=self.session_ref,
                surface_capability_scope=[],
                operator_identity_ref="operator://local-evaluator",
                canonical_user_ref="user://isolated-evaluator",
                requested_autonomy_level="assist_only",
                max_autonomy_level="assist_only",
            )
        )
        self.operation_dispatch_observed |= response.operation_dispatch is not None
        turns = self.core.memory_service.repository.fetch_recent_turns(self.session_ref, 20)
        self.memory_record_count = len(turns)
        if (
            not turns
            or turns[-1].request_content != request.prompt
            or turns[-1].response_text != response.response_text
        ):
            raise ValueError("empirical_canonical_final_refused")
        if (
            response.request_id != request.request_id
            or response.session_id != self.session_ref
            or response.operation_dispatch is not None
            or response.operation_result is not None
            or not response.memory_record.memory_record_id
        ):
            raise ValueError("empirical_core_final_refused")
        self.turn_count += 1
        self.event_count += len(response.events)
        decision = response.governance_decision.decision.value
        self.governance_decisions[decision] = self.governance_decisions.get(decision, 0) + 1
        # Never extract an integer, patch the answer, or change the evaluator's scorer.
        return EvaluationResponse.from_request(request, response.response_text)

    def metadata(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "revision": CONTROL_REVISION,
            "core_turn_count": self.turn_count,
            "core_event_count": self.event_count,
            "governance_decisions": dict(self.governance_decisions),
            "canonical_memory_record_count": self.memory_record_count,
            "evidence_mode": "core_local",
            "operation_dispatched": self.operation_dispatch_observed,
        }


def run_empirical_core_pilot() -> dict[str, object]:
    with TemporaryDirectory(prefix="jarvis-empirical-core-") as temporary:
        runtime = Path(temporary)
        ports = {
            arm: IsolatedEmpiricalCorePort(_isolated_core(runtime / arm), arm)
            for arm in ("baseline", "candidate")
        }
        runner = EmpiricalRunner(
            baseline=Arm("baseline", CONTROL_REVISION, "core_local", ports["baseline"]),
            candidate=Arm("candidate", CONTROL_REVISION, "core_local", ports["candidate"]),
        )
        report = runner.run(run_id=RUN_ID)
        return {
            "pilot_mode": "isolated_empirical_core_control",
            "comparison_kind": CONTROL_REVISION,
            "claim": "pipeline_only_no_improvement_claim",
            "runtime_mode": "temporary_sqlite",
            "production_memory_opened": False,
            "external_model_used": False,
            "runtime_capability_promoted": False,
            "arms": [ports[arm].metadata() for arm in ("baseline", "candidate")],
            "report": report.export_metrics(),
        }


def main() -> int:
    result = run_empirical_core_pilot()
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["report"]["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
