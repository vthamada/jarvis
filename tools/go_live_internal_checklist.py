"""Executable go-live checklist for the JARVIS v1 internal rollout."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
from sys import path as sys_path
from tempfile import gettempdir
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "orchestrator-service" / "src",
    ROOT / "services" / "memory-service" / "src",
    ROOT / "services" / "governance-service" / "src",
    ROOT / "services" / "operational-service" / "src",
    ROOT / "services" / "knowledge-service" / "src",
    ROOT / "services" / "observability-service" / "src",
    ROOT / "engines" / "identity-engine" / "src",
    ROOT / "engines" / "executive-engine" / "src",
    ROOT / "engines" / "cognitive-engine" / "src",
    ROOT / "engines" / "planning-engine" / "src",
    ROOT / "engines" / "synthesis-engine" / "src",
    ROOT / "engines" / "specialist-engine" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from evolution_lab.service import ComparisonInput, EvolutionLabService
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.agentic import JsonlAgenticMirrorAdapter
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.contracts import InputContract
from shared.events import InternalEventEnvelope
from shared.types import ChannelType, InputType, MissionId, PermissionDecision, RequestId, SessionId
from tools.validate_v1 import check_profile_prerequisites, resolve_database_url


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run the JARVIS v1 executable go-live checklist.")
    parser.add_argument(
        "--profile",
        choices=["development", "controlled"],
        default="development",
        help="Operational profile used for the checklist.",
    )
    return parser.parse_args()


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-go-live"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def build_orchestrator(profile: str, workdir: Path) -> OrchestratorService:
    observability = ObservabilityService(
        database_path=str(workdir / "observability.db"),
        agentic_adapter=JsonlAgenticMirrorAdapter(workdir / "agentic.jsonl"),
    )
    memory = MemoryService(database_url=resolve_database_url(profile, workdir))
    operational = OperationalService(artifact_dir=str(workdir / "artifacts"))
    return OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=memory,
        operational_service=operational,
        observability_service=observability,
    )


def check_allowed_flow(profile: str) -> None:
    workdir = runtime_dir("allowed-flow")
    orchestrator = build_orchestrator(profile, workdir)
    result = orchestrator.handle_input(
        InputContract(
            request_id=RequestId("req-allowed"),
            session_id=SessionId("sess-allowed"),
            mission_id=MissionId("mission-allowed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the internal pilot rollout.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    if result.governance_decision.decision not in {
        PermissionDecision.ALLOW,
        PermissionDecision.ALLOW_WITH_CONDITIONS,
    }:
        raise RuntimeError("Go-live check failed: allowed flow was not permitted.")
    if result.operation_result is None or not result.artifact_results:
        raise RuntimeError("Go-live check failed: allowed flow did not produce operation output.")


def check_blocked_flow(profile: str) -> None:
    workdir = runtime_dir("blocked-flow")
    orchestrator = build_orchestrator(profile, workdir)
    result = orchestrator.handle_input(
        InputContract(
            request_id=RequestId("req-blocked"),
            session_id=SessionId("sess-blocked"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all release records now.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    if result.governance_decision.decision != PermissionDecision.BLOCK:
        raise RuntimeError("Go-live check failed: destructive flow was not blocked.")


def check_mission_recovery(profile: str) -> None:
    workdir = runtime_dir("mission-recovery")
    orchestrator_one = build_orchestrator(profile, workdir)
    orchestrator_two = build_orchestrator(profile, workdir)
    contract_one = InputContract(
        request_id=RequestId("req-mission-1"),
        session_id=SessionId("sess-mission"),
        mission_id=MissionId("mission-v1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan milestone closure.",
        timestamp="2026-03-19T00:00:00+00:00",
    )
    contract_two = InputContract(
        request_id=RequestId("req-mission-2"),
        session_id=SessionId("sess-mission"),
        mission_id=MissionId("mission-v1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Analyze the milestone closure plan.",
        timestamp="2026-03-19T00:01:00+00:00",
    )
    orchestrator_one.handle_input(contract_one)
    result_two = orchestrator_two.handle_input(contract_two)
    required_hints = (
        "mission_recommendation=",
        "mission_semantic_brief=",
        "mission_focus=",
    )
    if not all(
        any(hint in item for item in result_two.recovered_context) for hint in required_hints
    ):
        raise RuntimeError("Go-live check failed: mission recovery is not stable across instances.")


def check_agentic_mirror(profile: str) -> None:
    workdir = runtime_dir("agentic-mirror")
    orchestrator = build_orchestrator(profile, workdir)
    orchestrator.handle_input(
        InputContract(
            request_id=RequestId("req-agentic"),
            session_id=SessionId("sess-agentic"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Provide a safe rollout summary.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    mirrored = (workdir / "agentic.jsonl").read_text(encoding="utf-8").splitlines()
    if not mirrored:
        raise RuntimeError("Go-live check failed: agentic mirror did not capture events.")


def check_evolution_lab() -> None:
    workdir = runtime_dir("evolution-lab")
    observability = ObservabilityService(database_path=str(workdir / "observability.db"))
    observability.ingest_events(
        [
            orchestrator_event(
                "evt-1",
                "req-base",
                "sess-base",
                "input_received",
                "2026-03-19T00:00:00+00:00",
            ),
            orchestrator_event(
                "evt-2",
                "req-base",
                "sess-base",
                "operation_completed",
                "2026-03-19T00:00:02+00:00",
                operation_id="op-base",
            ),
            orchestrator_event(
                "evt-3",
                "req-cand",
                "sess-cand",
                "input_received",
                "2026-03-19T00:00:03+00:00",
            ),
            orchestrator_event(
                "evt-4",
                "req-cand",
                "sess-cand",
                "operation_completed",
                "2026-03-19T00:00:04+00:00",
                operation_id="op-cand",
            ),
        ]
    )
    service = EvolutionLabService(database_path=str(workdir / "evolution.db"))
    baseline_metrics = observability.summarize_flow(ObservabilityQuery(request_id="req-base"))
    candidate_metrics = observability.summarize_flow(ObservabilityQuery(request_id="req-cand"))
    proposal = service.create_proposal(
        proposal_type="observability-driven-comparison",
        target_scope="go-live-internal",
        hypothesis="Candidate should stay sandbox-only pending review.",
        expected_gain="Higher throughput under the same governance envelope.",
        baseline_refs=["trace://req-base"],
        source_signals=["trace://req-base", "trace://req-cand"],
        proposed_tests=["python tools/go_live_internal_checklist.py --profile development"],
    )
    result = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="baseline",
            candidate_label="candidate",
            baseline_metrics={
                "success": 1.0 if baseline_metrics.completed_operations else 0.0,
                "stability": 1.0 if baseline_metrics.error_events == 0 else 0.0,
                "throughput": float(baseline_metrics.total_events),
                "risk": float(baseline_metrics.blocked_events + baseline_metrics.error_events),
            },
            candidate_metrics={
                "success": 1.0 if candidate_metrics.completed_operations else 0.0,
                "stability": 1.0 if candidate_metrics.error_events == 0 else 0.0,
                "throughput": float(candidate_metrics.total_events),
                "risk": float(candidate_metrics.blocked_events + candidate_metrics.error_events),
            },
            governance_refs=["policy://sandbox/manual-review"],
            notes=["go-live checklist"],
        ),
    )
    if result.decision.promoted_to is not None:
        raise RuntimeError("Go-live check failed: evolution candidate was promoted automatically.")


def orchestrator_event(
    event_id: str,
    request_id: str,
    session_id: str,
    event_name: str,
    timestamp: str,
    *,
    operation_id: str | None = None,
) -> InternalEventEnvelope:
    return InternalEventEnvelope(
        event_id=event_id,
        event_name=event_name,
        timestamp=timestamp,
        source_service="orchestrator-service",
        payload={"status": "completed" if event_name == "operation_completed" else "ok"},
        request_id=request_id,
        session_id=session_id,
        correlation_id=request_id,
        operation_id=operation_id,
    )


def main() -> None:
    args = parse_args()
    check_profile_prerequisites(args.profile, runtime_dir(f"preflight-{args.profile}"))
    check_allowed_flow(args.profile)
    check_blocked_flow(args.profile)
    check_mission_recovery(args.profile)
    check_agentic_mirror(args.profile)
    check_evolution_lab()
    print(f"Go-live checklist passed for profile={args.profile}.")


if __name__ == "__main__":
    main()
