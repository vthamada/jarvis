"""Executable go-live checklist for the JARVIS baseline internal rollout."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from json import loads
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
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    PermissionDecision,
    RequestId,
    SessionId,
)
from tools.operational_artifacts import (
    create_baseline_snapshot,
    create_containment_drill,
    read_baseline_snapshot,
    resolve_backend_label,
    write_baseline_snapshot,
    write_containment_drill,
    write_incident_evidence,
)
from tools.validate_baseline import check_profile_prerequisites, resolve_database_url


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run the JARVIS baseline executable go-live checklist.")
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
    database_url = check_profile_prerequisites(profile, workdir)
    observability = ObservabilityService(
        database_path=str(workdir / "observability.db"),
        agentic_adapter=JsonlAgenticMirrorAdapter(workdir / "agentic.jsonl"),
    )
    memory = MemoryService(database_url=database_url)
    operational = OperationalService(artifact_dir=str(workdir / "artifacts"))
    return OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=memory,
        operational_service=operational,
        observability_service=observability,
    )


def unique_id(label: str) -> str:
    return f"{label}-{uuid4().hex[:6]}"


def check_allowed_flow(profile: str) -> None:
    workdir = runtime_dir("allowed-flow")
    orchestrator = build_orchestrator(profile, workdir)
    mission_id = unique_id("mission-allowed")
    result = orchestrator.handle_input(
        InputContract(
            request_id=RequestId(unique_id("req-allowed")),
            session_id=SessionId(unique_id("sess-allowed")),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the internal pilot rollout.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    mission_state = orchestrator.memory_service.get_mission_state(mission_id)
    if result.governance_decision.decision not in {
        PermissionDecision.ALLOW,
        PermissionDecision.ALLOW_WITH_CONDITIONS,
    }:
        raise RuntimeError("Go-live check failed: allowed flow was not permitted.")
    if result.operation_result is None or not result.artifact_results:
        raise RuntimeError("Go-live check failed: allowed flow did not produce operation output.")
    if mission_state is None or mission_state.open_loops != result.deliberative_plan.open_loops:
        raise RuntimeError(
            "Go-live check failed: allow_with_conditions loop state is inconsistent."
        )


def check_blocked_flow(profile: str) -> None:
    workdir = runtime_dir("blocked-flow")
    orchestrator = build_orchestrator(profile, workdir)
    request_id = unique_id("req-blocked")
    result = orchestrator.handle_input(
        InputContract(
            request_id=RequestId(request_id),
            session_id=SessionId(unique_id("sess-blocked")),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all release records now.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    if result.governance_decision.decision != PermissionDecision.BLOCK:
        raise RuntimeError("Go-live check failed: destructive flow was not blocked.")
    evidence = orchestrator.observability_service.build_incident_evidence(
        ObservabilityQuery(request_id=request_id, limit=100)
    )
    write_incident_evidence(profile, evidence)
    if evidence.recommended_operator_action != "keep_contained_and_require_manual_review":
        raise RuntimeError("Go-live check failed: blocked flow did not produce operator evidence.")


def check_deferred_mission_conflict(profile: str) -> None:
    workdir = runtime_dir("deferred-flow")
    first = build_orchestrator(profile, workdir)
    second = build_orchestrator(profile, workdir)
    mission_id = unique_id("mission-defer")
    session_id = unique_id("sess-defer")
    accepted = first.handle_input(
        InputContract(
            request_id=RequestId(unique_id("req-defer-a")),
            session_id=SessionId(session_id),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone closure.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    deferred = second.handle_input(
        InputContract(
            request_id=RequestId(unique_id("req-defer-b")),
            session_id=SessionId(session_id),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-19T00:01:00+00:00",
        )
    )
    mission_state = second.memory_service.get_mission_state(mission_id)
    if deferred.governance_decision.decision != PermissionDecision.DEFER_FOR_VALIDATION:
        raise RuntimeError("Go-live check failed: conflicting mission request was not deferred.")
    if (
        mission_state is None
        or mission_state.last_recommendation != accepted.deliberative_plan.plan_summary
    ):
        raise RuntimeError(
            "Go-live check failed: deferred flow rewrote the accepted mission state."
        )


def check_mission_recovery(profile: str) -> None:
    workdir = runtime_dir("mission-recovery")
    orchestrator_one = build_orchestrator(profile, workdir)
    orchestrator_two = build_orchestrator(profile, workdir)
    mission_id = unique_id("mission-v1")
    session_id = unique_id("sess-mission")
    contract_one = InputContract(
        request_id=RequestId(unique_id("req-mission-1")),
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan milestone closure.",
        timestamp="2026-03-19T00:00:00+00:00",
    )
    contract_two = InputContract(
        request_id=RequestId(unique_id("req-mission-2")),
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
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
            request_id=RequestId(unique_id("req-agentic")),
            session_id=SessionId(unique_id("sess-agentic")),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Provide a safe rollout summary.",
            timestamp="2026-03-19T00:00:00+00:00",
        )
    )
    mirrored = (workdir / "agentic.jsonl").read_text(encoding="utf-8").splitlines()
    if not mirrored:
        raise RuntimeError("Go-live check failed: agentic mirror did not capture events.")
    mirrored_events = [loads(line) for line in mirrored]
    root_traces = [event for event in mirrored_events if event["name"] == "jarvis_trace"]
    child_runs = [event for event in mirrored_events if event["name"] != "jarvis_trace"]
    if not root_traces or not child_runs:
        raise RuntimeError("Go-live check failed: agentic mirror did not produce trace tree.")


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


def check_baseline_snapshot(profile: str) -> None:
    snapshot = read_baseline_snapshot(profile)
    if snapshot is None:
        database_url = resolve_database_url(profile, runtime_dir(f"snapshot-{profile}"))
        if database_url is None:
            raise RuntimeError("Go-live check failed: could not resolve snapshot database URL.")
        snapshot = create_baseline_snapshot(
            profile=profile,
            backend=resolve_backend_label(database_url),
            checks_passed=["go_live_internal_checklist"],
            operational_decision="go_conditional_for_controlled_production",
        )
        write_baseline_snapshot(snapshot)
    drill = create_containment_drill(
        snapshot=snapshot,
        trigger_reason="go_live_internal_containment_drill",
    )
    write_containment_drill(drill)
    if drill.rollback_target != snapshot.git_sha:
        raise RuntimeError("Go-live check failed: containment drill has no rollback target.")


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
    check_deferred_mission_conflict(args.profile)
    check_mission_recovery(args.profile)
    check_agentic_mirror(args.profile)
    check_evolution_lab()
    check_baseline_snapshot(args.profile)
    print(f"Go-live checklist passed for profile={args.profile}.")


if __name__ == "__main__":
    main()
