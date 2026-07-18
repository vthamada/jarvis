from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService
from planning_engine.engine import PlanningEngine
from synthesis_engine.engine import SynthesisEngine

from shared.contracts import (
    InputContract,
    MissionStateContract,
    OpenLoopResumePlanContract,
    WorkItemStateContract,
)
from shared.open_loop_policy import (
    canonical_open_loop_states_from_mission,
    mission_freshness,
    open_loop_ref,
    open_loop_resume_blockers,
)
from shared.schemas import (
    OPEN_LOOP_REGISTRY_SCHEMA,
    OPEN_LOOP_RESUME_PLAN_SCHEMA,
    OPEN_LOOP_STATE_SCHEMA,
)
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    MissionStatus,
    PermissionDecision,
    RequestId,
    SessionId,
)


def active_mission(*, updated_at: str | None = None) -> MissionStateContract:
    mission_id = MissionId("mission-open-loop-resume")
    work_item_ref = "work-item://mission-open-loop-resume/validate"
    return MissionStateContract(
        mission_id=mission_id,
        mission_goal="Resume governed daily work",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at=updated_at or datetime.now(UTC).isoformat(),
        objective_ref="objective://mission-open-loop-resume/daily-work",
        objective_status="active",
        open_loops=["Validate the next bounded implementation step"],
        work_item_refs=[work_item_ref],
        active_work_items=[work_item_ref],
        work_items=[
            WorkItemStateContract(
                work_item_ref=work_item_ref,
                work_item_status="active",
                mission_id=mission_id,
                priority_level="p1",
            )
        ],
        checkpoint_refs=["checkpoint://mission-open-loop-resume/context"],
    )


def resume_contract(mission_id: str) -> InputContract:
    return InputContract(
        request_id=RequestId("req-open-loop-test"),
        session_id=SessionId("sess-open-loop-test"),
        mission_id=MissionId(mission_id),
        channel=ChannelType.CONSOLE,
        input_type=InputType.STRUCTURED_PAYLOAD,
        content="open_loop_resume:resume",
        timestamp=datetime.now(UTC).isoformat(),
    )


def test_open_loop_policy_lifts_legacy_state_with_stable_reference() -> None:
    mission = active_mission()

    first = canonical_open_loop_states_from_mission(mission)
    second = canonical_open_loop_states_from_mission(mission)

    assert first == second
    assert first[0].open_loop_ref == open_loop_ref(
        str(mission.mission_id), mission.open_loops[0]
    )
    assert first[0].loop_status == "open"
    assert OPEN_LOOP_STATE_SCHEMA.contract_name == type(first[0]).__name__
    assert OPEN_LOOP_REGISTRY_SCHEMA.contract_name == "OpenLoopRegistryContract"
    assert OPEN_LOOP_RESUME_PLAN_SCHEMA.contract_name == "OpenLoopResumePlanContract"


def test_open_loop_freshness_and_blockers_fail_closed() -> None:
    generated_at = "2026-07-17T12:00:00+00:00"
    assert mission_freshness("2026-07-17T11:00:00+00:00", generated_at)[0] == "fresh"
    assert mission_freshness("2026-07-15T12:00:00+00:00", generated_at)[0] == "aging"
    assert mission_freshness("2026-07-13T11:59:00+00:00", generated_at)[0] == "stale"
    assert mission_freshness("invalid", generated_at) == ("unknown", None)

    mission = replace(
        active_mission(updated_at="2026-07-13T11:59:00+00:00"),
        surface_identity_conflict_flags=["canonical_user_mismatch"],
    )
    loop = canonical_open_loop_states_from_mission(mission)[0]
    blockers = open_loop_resume_blockers(
        mission_state=mission,
        loop_state=loop,
        freshness_status="stale",
        has_structured_work_items=True,
        selected_work_item_ref=None,
    )

    assert blockers == [
        "freshness_status:stale",
        "surface_identity_conflict",
        "no_executable_work_item",
    ]


def test_operational_registry_projects_eligible_and_stale_loops_without_mutation() -> None:
    mission = active_mission(updated_at="2026-07-17T10:00:00+00:00")
    before = replace(mission)

    registry = OperationalService.build_open_loop_registry(
        mission,
        generated_at="2026-07-17T12:00:00+00:00",
    )
    stale_registry = OperationalService.build_open_loop_registry(
        replace(mission, updated_at="2026-07-10T12:00:00+00:00"),
        generated_at="2026-07-17T12:00:00+00:00",
    )

    assert registry.registry_status == "resume_available"
    assert registry.mission_age_hours == 2.0
    assert registry.eligible_open_loop_refs == [registry.open_loop_states[0].open_loop_ref]
    assert registry.selected_work_item_ref == mission.work_items[0].work_item_ref
    assert registry.read_only is True
    assert registry.autonomous_resume_allowed is False
    assert stale_registry.registry_status == "blocked"
    assert stale_registry.blocking_reasons[stale_registry.blocked_open_loop_refs[0]] == [
        "freshness_status:stale"
    ]
    assert mission == before


def test_governance_allows_only_evidenced_eligible_explicit_resume() -> None:
    mission = active_mission()
    registry = OperationalService.build_open_loop_registry(
        mission,
        generated_at=datetime.now(UTC).isoformat(),
    )
    loop = registry.open_loop_states[0]
    service = GovernanceService()

    allowed = service.assess_open_loop_resume(
        contract=resume_contract(str(mission.mission_id)),
        current_state=mission,
        requested_open_loop_ref=loop.open_loop_ref,
        loop_state=loop,
        freshness_status=registry.freshness_status,
        selected_work_item_ref=registry.selected_work_item_ref,
        blocking_reasons=[],
        evidence_refs=registry.evidence_refs,
        requested_by_service="test",
    )
    blocked = service.assess_open_loop_resume(
        contract=resume_contract(str(mission.mission_id)),
        current_state=mission,
        requested_open_loop_ref="open-loop://unsafe\nspoof",
        loop_state=loop,
        freshness_status="fresh",
        selected_work_item_ref=registry.selected_work_item_ref,
        blocking_reasons=[],
        evidence_refs=registry.evidence_refs,
        requested_by_service="test",
    )

    assert allowed.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert allowed.governance_decision.requires_audit is True
    assert blocked.governance_decision.decision == PermissionDecision.BLOCK
    assert blocked.governance_decision.containment_hint == "block_unbounded_open_loop_ref"


def test_planning_and_synthesis_bound_resume_without_execution() -> None:
    plan = PlanningEngine().plan_open_loop_resume(
        mission_id="mission-open-loop-resume",
        open_loop_ref="open-loop://mission-open-loop-resume/abc",
        loop_summary="  Validate   the next bounded step  ",
        selected_work_item_ref="work-item://mission-open-loop-resume/validate",
        evidence_refs=["evidence://one", "evidence://one", "evidence://two"],
        generated_at="2026-07-17T12:00:00+00:00",
    )
    response = SynthesisEngine.compose_open_loop_resume(plan)

    assert plan.loop_summary == "Validate the next bounded step"
    assert plan.next_action_ref.startswith(
        "next-action://mission-open-loop-resume/open-loop/"
    )
    assert plan.evidence_refs == ["evidence://one", "evidence://two"]
    assert plan.autonomous_execution_allowed is False
    assert "nao executou ferramentas nem agendou trabalho" in response


def test_memory_persists_resume_and_rejects_state_race(tmp_path) -> None:
    service = MemoryService(database_url=f"sqlite:///{(tmp_path / 'memory.db').as_posix()}")
    mission = active_mission()
    service.repository.upsert_mission_state(mission)
    loop = canonical_open_loop_states_from_mission(mission)[0]
    plan = OpenLoopResumePlanContract(
        mission_id=mission.mission_id,
        open_loop_ref=loop.open_loop_ref,
        loop_summary=loop.loop_summary,
        next_action_ref="next-action://mission-open-loop-resume/open-loop/test",
        next_action_summary="Validate the next bounded step",
        selected_work_item_ref=mission.work_items[0].work_item_ref,
        evidence_refs=["evidence://resume/test"],
    )

    updated = service.resume_open_loop_state(
        mission_id=str(mission.mission_id),
        open_loop_ref=loop.open_loop_ref,
        plan=plan,
        expected_updated_at=mission.updated_at,
        checkpoint_ref="checkpoint://open-loop/resumed",
    )
    reloaded = service.get_mission_state(str(mission.mission_id))

    assert updated is not None and reloaded is not None
    assert reloaded.open_loops == []
    assert reloaded.open_loop_states[0].loop_status == "resumed"
    assert reloaded.next_action_ref == plan.next_action_ref
    assert reloaded.open_loop_states[0].evidence_refs == ["evidence://resume/test"]

    service.repository.upsert_mission_state(
        replace(reloaded, updated_at=(datetime.now(UTC) + timedelta(seconds=1)).isoformat())
    )
    with pytest.raises(ValueError, match="changed after resume revalidation"):
        service.resume_open_loop_state(
            mission_id=str(mission.mission_id),
            open_loop_ref=loop.open_loop_ref,
            plan=plan,
            expected_updated_at=reloaded.updated_at,
            checkpoint_ref="checkpoint://open-loop/race",
        )


def test_orchestrator_resumes_once_through_core_and_emits_auditable_events(
    tmp_path,
) -> None:
    memory = MemoryService(database_url=f"sqlite:///{(tmp_path / 'memory.db').as_posix()}")
    observability = ObservabilityService(database_path=str(tmp_path / "events.db"))
    mission = active_mission()
    memory.repository.upsert_mission_state(mission)
    loop_ref = open_loop_ref(str(mission.mission_id), mission.open_loops[0])
    service = OrchestratorService(
        memory_service=memory,
        operational_service=OperationalService(artifact_dir=str(tmp_path / "artifacts")),
        observability_service=observability,
    )

    result = service.resume_open_loop(
        mission_id=str(mission.mission_id),
        open_loop_ref=loop_ref,
        session_id="sess-open-loop-cross-session",
        operator_identity_ref="operator://test",
        canonical_user_ref="user://test",
    )
    repeated = service.resume_open_loop(
        mission_id=str(mission.mission_id),
        open_loop_ref=loop_ref,
        session_id="sess-open-loop-repeat",
    )
    events = observability.list_recent_events(
        ObservabilityQuery(mission_id=str(mission.mission_id), limit=20)
    )

    assert result.status == "resumed"
    assert result.open_loop_state is not None
    assert result.open_loop_state.loop_status == "resumed"
    assert result.response_text is not None
    assert result.resume_plan is not None
    assert result.resume_plan.autonomous_execution_allowed is False
    assert repeated.status == "blocked"
    assert [event.event_name for event in result.events] == [
        "governance_checked",
        "open_loop_resumed",
        "mission_updated",
        "response_synthesized",
    ]
    assert "operation_dispatched" not in {event.event_name for event in events}
    resumed_event = next(event for event in events if event.event_name == "open_loop_resumed")
    assert resumed_event.payload["autonomous_resume_allowed"] is False
    assert resumed_event.payload["autonomous_execution_allowed"] is False
