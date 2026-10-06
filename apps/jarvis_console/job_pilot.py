# ruff: noqa: E402
"""Explicit durable job -> assist-only sovereign Core, in an isolated pilot.

No scheduler, arbitrary executor, credentials, production memory or tool grant.
The ledger and canonical memory are separate transactions, never exactly-once.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from job_service import JobSpec, JobStoreError, SqliteJobStore
from job_service.store import CORE_TASK, _ref
from orchestrator_service.service import OrchestratorService

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId

_CORPUS = {
    "acknowledgement": "Reply with a brief greeting only. Do not execute any actions.",
    "arithmetic": "What is two plus two? Do not execute tools or actions.",
}


@dataclass(frozen=True)
class CoreJobInput:
    """Closed benign corpus only; refs are bindings, not authenticated identities."""

    actor_ref: str
    session_ref: str
    case: str

    def __post_init__(self):
        _ref(self.actor_ref)
        _ref(self.session_ref)
        if not isinstance(self.case, str) or self.case not in _CORPUS:
            raise JobStoreError("unsupported_core_case")

    @property
    def text(self) -> str:
        return _CORPUS[self.case]

    @property
    def step_ref(self) -> str:
        return "input-" + hashlib.sha256(self.text.encode("utf-8")).hexdigest()

    @property
    def core_session_id(self) -> str:
        digest = hashlib.sha256(json.dumps([self.actor_ref, self.session_ref]).encode()).hexdigest()
        return f"session://job-pilot-{digest}"


class CoreJobRunner:
    """Trusted local composition of an actual Core; not a public auth endpoint."""

    def __init__(self, store: SqliteJobStore, core: OrchestratorService, worker_id: str):
        if not isinstance(store, SqliteJobStore) or not isinstance(core, OrchestratorService):
            raise JobStoreError("invalid_core_composition")
        _ref(worker_id)
        self.store, self.core, self.worker_id = store, core, worker_id

    def run_once(
        self, job_id: str, request: CoreJobInput, *, expected_version: int, lease_seconds=120
    ) -> dict[str, object]:
        if not isinstance(request, CoreJobInput):
            raise JobStoreError("invalid_core_input")
        scope = {"actor_ref": request.actor_ref, "session_ref": request.session_ref}
        before = self.store.get(job_id, **scope)
        if (
            before.spec.task_ref != CORE_TASK
            or before.spec.approved_step_ref != request.step_ref
            or before.spec.responsibility_ref != "core-assist-pilot"
        ):
            raise JobStoreError("core_input_binding_refused")
        claim = self.store.claim(
            job_id,
            worker_id=self.worker_id,
            expected_version=expected_version,
            lease_seconds=lease_seconds,
            **scope,
        )
        result = {
            "evidence_mode": "not_run",
            "core_invoked": False,
            "canonical_final_verified": False,
            "result_accepted": False,
            "result_recorded": False,
            "review_required": True,
            "operation_dispatched": False,
            "core_event_count": 0,
            "request_id": None,
            "memory_record_id": None,
            "operator_authenticated": False,
            "action_authority": False,
            "cross_ledger_atomic": False,
            "exactly_once_claimed": False,
            "runtime_capability_promoted": False,
        }
        if claim is None:
            result["job"] = self.store.get(job_id, **scope).telemetry()
            return result
        # Deterministic within the bound job only; no automatic resubmission.
        request_id = (
            "job-"
            + hashlib.sha256(
                json.dumps(
                    [job_id, request.actor_ref, request.session_ref, request.step_ref]
                ).encode()
            ).hexdigest()
        )
        session_id = request.core_session_id
        try:
            self.store.validate_claim(claim)
            result.update(core_invoked=True, request_id=request_id, evidence_mode="core_local")
            response = self.core.handle_input(
                InputContract(
                    request_id=RequestId(request_id),
                    session_id=SessionId(session_id),
                    channel=ChannelType.CHAT,
                    input_type=InputType.TEXT,
                    content=request.text,
                    timestamp=datetime.now(UTC).isoformat(),
                    surface_id="surface://isolated-job-pilot",
                    surface_kind="console",
                    surface_session_id=session_id,
                    surface_capability_scope=[],
                    operator_identity_ref=f"operator://{request.actor_ref}",
                    canonical_user_ref=f"user://{request.actor_ref}",
                    user_id=f"user://{request.actor_ref}",
                    requested_autonomy_level="assist_only",
                    max_autonomy_level="assist_only",
                )
            )
            result["operation_dispatched"] = response.operation_dispatch is not None
            result["core_event_count"] = len(response.events)
            turns = self.core.memory_service.repository.fetch_recent_turns(session_id, 1)
            events = self.core.observability_service.repository.list_events(
                limit=100,
                request_id=request_id,
                session_id=session_id,
            )
            names = {event.event_name for event in events}
            governance_matches = any(
                event.event_name == "governance_checked"
                and event.payload.get("decision") == response.governance_decision.decision.value
                for event in events
            )
            memory_matches = any(
                event.event_name == "memory_recorded"
                and event.payload.get("memory_record_id")
                == str(response.memory_record.memory_record_id)
                for event in events
            )
            if (
                response.request_id != request_id
                or response.session_id != session_id
                or response.operation_dispatch is not None
                or response.operation_result is not None
                or response.adapter_grant is not None
                or response.adapter_grant_claim is not None
                or response.action_confirmation_claim is not None
                or not response.memory_record.memory_record_id
                or response.memory_record.session_id != session_id
                or not response.governance_decision.decision_id
                or not governance_matches
                or not memory_matches
                or not {"governance_checked", "response_synthesized", "memory_recorded"} <= names
                or not turns
                or turns[0].request_content != request.text
                or turns[0].response_text != response.response_text
                or not response.response_text
            ):
                raise JobStoreError("core_final_evidence_refused")
            result.update(
                canonical_final_verified=True,
                memory_record_id=str(response.memory_record.memory_record_id),
                governance_decision=response.governance_decision.decision.value,
            )
            outcome = (
                "succeeded"
                if response.governance_decision.decision.value == "allow"
                else "needs_decision"
            )
            final = self.store.finish(claim, outcome)
            result.update(result_recorded=True, result_accepted=outcome == "succeeded")
        except Exception:
            # Even a failure before final return may have recorded a turn. Do not replay.
            current = self.store.get(job_id, **scope)
            if current.status == "running" and current.version == claim.version:
                try:
                    self.store.pause(job_id, expected_version=current.version, **scope)
                except JobStoreError:
                    pass  # Concurrent cancellation/pause wins; never overwrite it.
            final = self.store.get(job_id, **scope)
        result["job"] = final.telemetry()
        result["review_required"] = not result["result_accepted"]
        return result


def run_job_core_pilot(
    case: str = "acknowledgement", *, authorized: bool = False
) -> dict[str, object]:
    if authorized is not True:
        raise JobStoreError("pilot_opt_in_required")
    request = CoreJobInput("local-pilot", "isolated-job-pilot", case)
    base = Path(tempfile.gettempdir()).resolve(strict=True)
    workspace = Path(__file__).resolve().parents[2]
    if not base.is_dir() or base.is_relative_to(workspace):
        raise JobStoreError("private_runtime_required")
    with TemporaryDirectory(prefix="jarvis-job-core-pilot-", dir=base) as temporary:
        runtime = Path(temporary)
        store = SqliteJobStore(runtime / "jobs.db")
        store.register(
            JobSpec(
                "pilot-job",
                request.actor_ref,
                request.session_ref,
                "core-assist-pilot",
                request.step_ref,
                CORE_TASK,
                datetime.now(UTC) + timedelta(minutes=3),
                1,
            )
        )
        result = CoreJobRunner(store, _isolated_core(runtime), "pilot-worker").run_once(
            "pilot-job",
            request,
            expected_version=0,
        )
        # Reopening is read-only with respect to execution; no fresh Core turn.
        reopened = SqliteJobStore(runtime / "jobs.db")
        result["restart_status"] = reopened.get(
            "pilot-job",
            actor_ref=request.actor_ref,
            session_ref=request.session_ref,
        ).status
        result.update(
            pilot_mode="isolated_job_core",
            runtime_mode="temporary_sqlite",
            production_memory_opened=False,
            automatic_execution=False,
        )
        return result


def main(argv=None) -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.authorized is not True:
            raise JobStoreError("pilot_opt_in_required")
        # Only the selected benign case crosses stdin, never input text in argv.
        raw = sys.stdin.read(1025)
        if len(raw) > 1024:
            raise ValueError("invalid_request")
        request = json.loads(raw) if raw.strip() else {"case": "acknowledgement"}
        if not isinstance(request, dict) or set(request) != {"case"}:
            raise ValueError("invalid_request")
        result = run_job_core_pilot(request["case"], authorized=True)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0 if result["result_recorded"] else 1
    except Exception:
        print(json.dumps({"status": "refused", "reason": "job_pilot_unavailable"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
