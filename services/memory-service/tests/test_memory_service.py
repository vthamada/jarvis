from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import memory_service.repository as memory_repository
import pytest
from governance_service.service import GovernanceService
from memory_service.repository import (
    PostgresMemoryRepository,
    SqliteMemoryRepository,
    StoredSpecialistSharedMemory,
    build_memory_repository,
    normalize_database_url,
    parse_sqlite_database_path,
)
from memory_service.service import MemoryRecordResult, MemoryRecoveryResult, MemoryService

from shared.contracts import (
    DeliberativePlanContract,
    InputContract,
    MemoryLifecycleGovernanceAssessmentContract,
    MissionStateContract,
    OperationDispatchContract,
    OperationResultContract,
    ProceduralPlaybookCandidateContract,
    ReviewedLearningGuidanceContract,
    SkillCandidateContract,
    SpecialistContributionContract,
    SpecialistSharedMemoryContextContract,
)
from shared.memory_registry import DEFAULT_MEMORY_SCOPES, memory_lifecycle_decision
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    MissionStatus,
    OperationId,
    OperationStatus,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def sample_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="decompor objetivo em etapas reversiveis",
        goal="Please plan the sprint.",
        steps=["continuar a missao", "listar etapas", "recomendar proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=nenhum; apoio=baseline local",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["operational_planning_specialist"],
        success_criteria=["plano deve indicar a menor proxima acao segura"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="continuar a missao",
        continuity_action="continuar",
        open_loops=["fechar checkpoint principal"],
    )


def sample_specialist_contributions() -> list[SpecialistContributionContract]:
    return [
        SpecialistContributionContract(
            specialist_type="operational_planning_specialist",
            role="planejamento_operacional_subordinado",
            focus="sequenciamento reversivel e checkpoints claros",
            findings=["open_loop: fechar checkpoint principal"],
            recommendation="encadear o plano em etapas pequenas e verificaveis",
            confidence=0.78,
        )
    ]


def test_memory_service_name() -> None:
    assert MemoryService.name == "memory-service"


def test_memory_service_transitions_work_item_in_canonical_mission_state() -> None:
    temp_dir = runtime_dir("memory-work-item-transition")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    contract = InputContract(
        request_id=RequestId("req-work-item-memory"),
        session_id=SessionId("sess-work-item-memory"),
        mission_id=MissionId("mission-work-item-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the controlled rollout.",
        timestamp="2026-05-18T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan ready.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    created = service.transition_work_item_state(
        mission_id="mission-work-item-memory",
        work_item_ref="work-item://mission-work-item-memory/validate-plan",
        work_item_status="active",
        transition_ref=(
            "work_item_transition:create:"
            "work-item://mission-work-item-memory/validate-plan:abc12345"
        ),
        next_action_ref="next_action:validate-plan",
    )
    paused = service.transition_work_item_state(
        mission_id="mission-work-item-memory",
        work_item_ref="work-item://mission-work-item-memory/validate-plan",
        work_item_status="paused",
        transition_ref=(
            "work_item_transition:pause:"
            "work-item://mission-work-item-memory/validate-plan:def67890"
        ),
    )

    assert created is not None
    assert created.next_action_ref == "next_action:validate-plan"
    assert "work-item://mission-work-item-memory/validate-plan" in created.work_item_refs
    assert (
        "work-item://mission-work-item-memory/validate-plan"
        in created.active_work_items
    )
    assert paused is not None
    assert "work-item://mission-work-item-memory/validate-plan" in paused.work_item_refs
    assert (
        "work-item://mission-work-item-memory/validate-plan"
        not in paused.active_work_items
    )
    assert any(
        ref.startswith("work_item_transition:pause:")
        for ref in paused.checkpoint_refs
    )


def test_memory_service_persists_work_item_graph_and_refreshes_readiness() -> None:
    temp_dir = runtime_dir("memory-work-item-graph")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    mission_id = "mission-memory-work-item-graph"
    foundation_ref = f"work-item://{mission_id}/foundation"
    release_ref = f"work-item://{mission_id}/release"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-memory-work-item-graph"),
            session_id=SessionId("sess-memory-work-item-graph"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content="Plan the governed graph.",
            timestamp="2026-07-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Graph planned.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=foundation_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{foundation_ref}:one",
        priority_level="p2",
    )
    created = service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=release_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{release_ref}:two",
        dependency_refs=[foundation_ref],
        priority_level="p0",
    )

    reloaded = MemoryService(database_url=database_url).get_mission_state(mission_id)

    assert created is not None
    assert reloaded is not None
    assert len(reloaded.work_items) == 2
    release = next(item for item in reloaded.work_items if item.work_item_ref == release_ref)
    assert release.dependency_refs == [foundation_ref]
    assert release.priority_level == "p0"
    assert release.blocking_state == "dependency_blocked"

    completed = service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref=foundation_ref,
        work_item_status="completed",
        transition="complete",
        transition_ref=f"work_item_transition:complete:{foundation_ref}:three",
    )

    assert completed is not None
    release = next(item for item in completed.work_items if item.work_item_ref == release_ref)
    assert release.blocking_state == "ready"
    assert release_ref in completed.active_work_items


def test_memory_service_transitions_artifact_lifecycle_in_mission_state() -> None:
    temp_dir = runtime_dir("memory-artifact-lifecycle")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    contract = InputContract(
        request_id=RequestId("req-artifact-memory"),
        session_id=SessionId("sess-artifact-memory"),
        mission_id=MissionId("mission-artifact-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the controlled rollout.",
        timestamp="2026-05-18T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan ready.",
        deliberative_plan=sample_plan(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    work_item_ref = "work-item://mission-artifact-memory/plan"
    service.transition_work_item_state(
        mission_id="mission-artifact-memory",
        work_item_ref=work_item_ref,
        work_item_status="active",
        transition="create",
        transition_ref=f"work_item_transition:create:{work_item_ref}:source",
    )

    registered = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition_ref=(
            "artifact_lifecycle_transition:register:"
            "artifact://mission-artifact-memory/plan/v1:abc12345"
        ),
        artifact_version=1,
        work_item_ref=work_item_ref,
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    replaced = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition_ref=(
            "artifact_lifecycle_transition:replace:"
            "artifact://mission-artifact-memory/plan/v1:def67890"
        ),
        replacement_artifact_ref="artifact://mission-artifact-memory/plan/v2",
        artifact_version=2,
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    rolled_back = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="active",
        transition="rollback",
        transition_ref=(
            "artifact_lifecycle_transition:rollback:"
            "artifact://mission-artifact-memory/plan/v1:rollback1"
        ),
        rollback_plan_ref="rollback://mission-artifact-memory/plan/v1",
    )
    reloaded = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    ).get_mission_state("mission-artifact-memory")
    archived = service.transition_artifact_lifecycle_state(
        mission_id="mission-artifact-memory",
        artifact_ref="artifact://mission-artifact-memory/plan/v1",
        artifact_status="archived",
        transition_ref=(
            "artifact_lifecycle_transition:archive:"
            "artifact://mission-artifact-memory/plan/v1:fedcba98"
        ),
    )

    assert registered is not None
    assert "artifact://mission-artifact-memory/plan/v1" in registered.artifact_refs
    assert (
        "artifact://mission-artifact-memory/plan/v1"
        in registered.active_artifact_refs
    )
    assert replaced is not None
    assert "artifact://mission-artifact-memory/plan/v2" in replaced.artifact_refs
    assert (
        "artifact://mission-artifact-memory/plan/v2"
        in replaced.active_artifact_refs
    )
    assert (
        "artifact://mission-artifact-memory/plan/v1"
        not in replaced.active_artifact_refs
    )
    assert len(replaced.artifact_states) == 2
    version_one = next(
        item
        for item in replaced.artifact_states
        if item.artifact_ref == "artifact://mission-artifact-memory/plan/v1"
    )
    version_two = next(
        item
        for item in replaced.artifact_states
        if item.artifact_ref == "artifact://mission-artifact-memory/plan/v2"
    )
    assert version_one.artifact_status == "superseded"
    assert version_one.replacement_artifact_ref == version_two.artifact_ref
    assert version_two.supersedes_artifact_ref == version_one.artifact_ref
    assert version_two.artifact_version == 2
    assert version_two.work_item_ref == work_item_ref
    assert rolled_back is not None
    assert reloaded is not None
    reloaded_v1 = next(
        item for item in reloaded.artifact_states if item.artifact_ref == version_one.artifact_ref
    )
    reloaded_v2 = next(
        item for item in reloaded.artifact_states if item.artifact_ref == version_two.artifact_ref
    )
    assert reloaded_v1.artifact_status == "active"
    assert reloaded_v2.artifact_status == "rolled_back"
    assert reloaded_v1.artifact_version == 1
    assert reloaded_v1.created_at == version_one.created_at
    assert archived is not None
    assert (
        "artifact://mission-artifact-memory/plan/v1"
        not in archived.active_artifact_refs
    )
    assert any(
        ref.startswith("artifact_lifecycle_transition:archive:")
        for ref in archived.checkpoint_refs
    )


def test_postgres_mission_upsert_keeps_columns_and_placeholders_in_sync() -> None:
    captured: dict[str, object] = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query: str, params: tuple[object, ...]) -> None:
            captured["query"] = query
            captured["params"] = params

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            captured["committed"] = True

    repository = PostgresMemoryRepository.__new__(PostgresMemoryRepository)
    repository._connect = lambda: FakeConnection()
    mission = MissionStateContract(
        mission_id=MissionId("mission-postgres-artifact-state"),
        mission_goal="Persist artifact lineage",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T00:00:00Z",
    )

    repository.upsert_mission_state(mission)

    query = str(captured["query"])
    params = captured["params"]
    assert isinstance(params, tuple)
    assert query.count("%s") == len(params) == 36
    assert "artifact_states" in query
    assert "open_loop_states" in query
    assert captured["committed"] is True


def test_memory_service_recovers_empty_context_for_new_session() -> None:
    temp_dir = runtime_dir("memory-empty")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    result = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Hello",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    assert isinstance(result, MemoryRecoveryResult)
    assert result.recovered_items == []
    assert result.recovery_contract.requested_scopes == DEFAULT_MEMORY_SCOPES
    assert result.recovery_contract.priority_rules[0].startswith("default_recovery_order=")


def test_memory_service_records_and_recovers_session_history_across_instances() -> None:
    temp_dir = runtime_dir("memory-history")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-2"),
        session_id=SessionId("sess-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    writer = MemoryService(database_url=database_url)
    record = writer.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    reader = MemoryService(database_url=database_url)
    recovered = reader.recover_for_input(contract)
    assert isinstance(record, MemoryRecordResult)
    assert record.record_contract.record_type == "interaction_turn"
    assert record.record_contract.payload["decision_frame"] == "planning"
    assert record.record_contract.payload["dominant_goal"] == "Please plan the sprint."
    assert record.record_contract.payload["open_loops"] == ["fechar checkpoint principal"]
    assert any("planning" in item for item in recovered.recovered_items)
    assert any("context_summary=" in item for item in recovered.session_context)
    assert any("session_continuity_brief=" in item for item in recovered.session_context)
    assert any("session_continuity_mode=continuar" in item for item in recovered.session_context)
    assert any("continuity_checkpoint_id=" in item for item in recovered.session_context)
    assert any("continuity_checkpoint_status=ready" in item for item in recovered.session_context)
    assert any("continuity_replay_status=resumable" in item for item in recovered.session_context)
    assert any("continuity_resume_point=continuar:" in item for item in recovered.session_context)
    assert recovered.mission_hints == []
    assert any("prior_plan=" in item for item in recovered.plan_hints)


def test_memory_service_exposes_recoverable_continuity_checkpoint() -> None:
    temp_dir = runtime_dir("memory-checkpoint")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-checkpoint"),
        session_id=SessionId("sess-checkpoint"),
        mission_id=MissionId("mission-checkpoint"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    checkpoint = MemoryService(database_url=database_url).get_session_continuity_checkpoint(
        "sess-checkpoint"
    )

    assert checkpoint is not None
    assert checkpoint.session_id == SessionId("sess-checkpoint")
    assert checkpoint.continuity_action == "continuar"
    assert checkpoint.checkpoint_status == "ready"
    assert "sessao segue ancorada" in checkpoint.checkpoint_summary
    assert checkpoint.replay_summary is not None


def test_memory_service_builds_resumable_continuity_replay_state() -> None:
    temp_dir = runtime_dir("memory-replay")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-replay"),
        session_id=SessionId("sess-replay"),
        mission_id=MissionId("mission-replay"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    replay = MemoryService(database_url=database_url).get_session_continuity_replay("sess-replay")

    assert replay is not None
    assert replay.session_id == SessionId("sess-replay")
    assert replay.replay_status == "resumable"
    assert replay.recovery_mode == "resume_active_mission"
    assert replay.resume_point.startswith("continuar:")
    assert replay.requires_manual_resume is False


def test_memory_service_recovers_bounded_ecosystem_state_for_continuity() -> None:
    temp_dir = runtime_dir("memory-ecosystem-state")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    contract = InputContract(
        request_id=RequestId("req-eco-1"),
        session_id=SessionId("sess-eco"),
        mission_id=MissionId("mission-eco"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-04-23T00:00:00Z",
    )
    service = MemoryService(database_url=database_url)
    dispatch = sample_operation_dispatch(
        request_id="req-eco-1",
        session_id="sess-eco",
        mission_id="mission-eco",
    )
    result = sample_operation_result(
        operation_id="op-sample",
        artifact_ref="runtime://artifact/milestone-plan.md",
    )

    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
        operation_dispatch=dispatch,
        operation_result=result,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-eco-2"),
            session_id=SessionId("sess-eco"),
            mission_id=MissionId("mission-eco"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue milestone coordination.",
            timestamp="2026-04-23T00:01:00Z",
        )
    )
    replay = service.get_session_continuity_replay("sess-eco")
    checkpoint = service.get_session_continuity_checkpoint("sess-eco")
    mission_state = service.get_mission_state("mission-eco")

    assert replay is not None
    assert replay.ecosystem_state_status == "operational_state_attached"
    assert replay.recovery_mode == "resume_operational_checkpoint"
    assert replay.resume_point.startswith("ecosystem_checkpoint:")
    assert replay.linked_surface_ids == ["surface://jarvis_console"]
    assert replay.active_surface_id == "surface://jarvis_console"
    assert replay.surface_continuity_status == "single_surface"
    assert replay.surface_identity_conflict_flags == []
    assert checkpoint is not None
    assert checkpoint.ecosystem_state_status == "operational_state_attached"
    assert checkpoint.open_checkpoint_refs == [
        "workflow_checkpoint:close_readiness_checkpoint:pending"
    ]
    assert checkpoint.active_surface_id == "surface://jarvis_console"
    assert mission_state is not None
    assert mission_state.ecosystem_state_status == "operational_state_attached"
    assert mission_state.active_work_items == ["mission_task:Plan milestone M3"]
    assert "runtime://artifact/milestone-plan.md" in mission_state.active_artifact_refs
    assert mission_state.project_ref == "project://mission-eco"
    assert mission_state.objective_ref == "objective://mission-eco"
    assert mission_state.objective_status == "completed"
    assert mission_state.next_action_ref == "next_action:close_readiness_checkpoint"
    assert mission_state.linked_surface_ids == ["surface://jarvis_console"]
    assert mission_state.active_surface_id == "surface://jarvis_console"
    assert any(
        item == "mission_ecosystem_state_status=operational_state_attached"
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_active_work_items=mission_task:Plan milestone M3")
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_active_artifact_refs=")
        and "runtime://artifact/milestone-plan.md" in item
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_open_checkpoint_refs=")
        for item in recovered.recovered_items
    )
    assert any(
        item == "mission_objective_status=completed"
        for item in recovered.recovered_items
    )
    assert any(
        item == "mission_project_ref=project://mission-eco"
        for item in recovered.recovered_items
    )
    assert any(
        item.startswith("mission_work_item_refs=")
        for item in recovered.recovered_items
    )
    assert any(
        item == "mission_active_surface_id=surface://jarvis_console"
        for item in recovered.recovered_items
    )


def test_memory_service_resolves_governed_continuity_pause() -> None:
    temp_dir = runtime_dir("memory-pause")
    database_url = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    service = MemoryService(database_url=database_url)
    contract = InputContract(
        request_id=RequestId("req-pause-1"),
        session_id=SessionId("sess-pause"),
        mission_id=MissionId("mission-pause"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Please plan the sprint.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            continuity_reason="pedido atual desloca o foco da missao ativa",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )

    pause = service.get_session_continuity_pause("sess-pause")

    assert pause is not None
    assert pause.pause_status == "awaiting_validation"
    assert pause.requires_human_input is True

    resolved_pause = service.resolve_session_continuity_pause(
        "sess-pause",
        approved=True,
        resolved_by="operator",
        resolution_note="validado manualmente para retomar",
    )
    replay = service.get_session_continuity_replay("sess-pause")

    assert resolved_pause is not None
    assert resolved_pause.pause_status == "approved"
    assert resolved_pause.resolution_status == "approved"
    assert replay is not None
    assert replay.replay_status == "resumable"
    assert replay.requires_manual_resume is False


def test_memory_service_persists_mission_state_with_identity_continuity_and_open_loops() -> None:
    temp_dir = runtime_dir("memory-mission")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-3"),
        session_id=SessionId("sess-3"),
        mission_id=MissionId("mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    mission_state = service.get_mission_state("mission-1")
    assert mission_state is not None
    assert mission_state.mission_goal == "Coordinate milestone M3."
    assert mission_state.checkpoints
    assert "planning" in mission_state.active_tasks
    assert mission_state.last_recommendation == "decompor objetivo em etapas reversiveis"
    assert mission_state.semantic_brief is not None
    assert mission_state.identity_continuity_brief is not None
    assert "prioridade=fechar checkpoint principal" in mission_state.identity_continuity_brief
    assert mission_state.open_loops == ["fechar checkpoint principal"]
    assert mission_state.last_decision_frame == "planning"


def test_memory_service_lists_open_missions_by_latest_canonical_update() -> None:
    temp_dir = runtime_dir("memory-daily-workspace-list")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    for mission_id, status, updated_at in (
        ("mission-older", MissionStatus.PAUSED, "2026-07-16T09:00:00+00:00"),
        ("mission-closed", MissionStatus.COMPLETED, "2026-07-17T10:00:00+00:00"),
        ("mission-newer", MissionStatus.ACTIVE, "2026-07-17T09:00:00+00:00"),
    ):
        service.repository.upsert_mission_state(
            MissionStateContract(
                mission_id=MissionId(mission_id),
                mission_goal=f"Goal for {mission_id}",
                mission_status=status,
                checkpoints=[],
                updated_at=updated_at,
            )
        )

    open_states = service.list_mission_states(limit=20)
    all_states = service.list_mission_states(limit=20, include_closed=True)

    assert [str(state.mission_id) for state in open_states] == [
        "mission-newer",
        "mission-older",
    ]
    assert [str(state.mission_id) for state in all_states] == [
        "mission-closed",
        "mission-newer",
        "mission-older",
    ]


def test_memory_service_recovers_mission_hints_in_continuity_priority_order() -> None:
    temp_dir = runtime_dir("memory-order")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-4"),
        session_id=SessionId("sess-4"),
        mission_id=MissionId("mission-2"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    recovered = service.recover_for_input(contract)
    assert recovered.mission_hints[0].startswith("identity_continuity_brief=")
    assert recovered.mission_hints[1].startswith("open_loops=")
    assert any(item.startswith("mission_goal=") for item in recovered.mission_hints)
    assert any(item.startswith("mission_recommendation=") for item in recovered.mission_hints)


def test_memory_service_derives_long_horizon_goal_strategy_read_only() -> None:
    temp_dir = runtime_dir("memory-long-horizon")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    mission_id = "mission-long-horizon"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-long-horizon"),
            session_id=SessionId("sess-long-horizon"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the long horizon rollout.",
            timestamp="2026-05-20T00:00:00Z",
        ),
        intent="planning",
        response_text="Long horizon rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    service.transition_work_item_state(
        mission_id=mission_id,
        work_item_ref="work-item://mission-long-horizon/validate-plan",
        work_item_status="active",
        transition_ref="work_item_transition:create:long-horizon",
        next_action_ref="next_action:operator-review",
    )
    service.transition_artifact_lifecycle_state(
        mission_id=mission_id,
        artifact_ref="artifact://mission-long-horizon/plan/v1",
        artifact_status="active",
        transition_ref="artifact_lifecycle_transition:register:long-horizon",
        artifact_version=1,
        work_item_ref="work-item://mission-long-horizon/validate-plan",
    )

    strategy = service.build_long_horizon_goal_strategy(mission_id)

    assert strategy is not None
    assert strategy.strategy_status == "ready"
    assert "mode=read_only_no_scheduler" in strategy.strategy_summary
    assert "work-item://mission-long-horizon/validate-plan" in strategy.milestone_refs
    assert "artifact://mission-long-horizon/plan/v1" in strategy.evidence_refs
    assert strategy.next_action_ref == "next_action:operator-review"
    assert strategy.memory_write_mode == "read_only"
    assert strategy.autonomous_scheduling_allowed is False


def test_memory_service_detects_related_mission_continuity_within_same_session() -> None:
    temp_dir = runtime_dir("memory-related")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-1"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-2"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="analysis",
        response_text="Risk analysis drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-related-3"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the risk analysis.",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert recovered.continuity_context is not None
    assert recovered.continuity_context.related_candidates
    candidate = recovered.continuity_context.related_candidates[0]
    assert candidate.mission_id == MissionId("mission-a")
    assert candidate.relation_type == "same_session_related_mission"
    assert candidate.priority_score >= 0.6
    assert recovered.continuity_context.recommended_action == "priorizar_loop_ativo"


def test_memory_service_prepares_core_mediated_shared_memory_for_specialists() -> None:
    temp_dir = runtime_dir("memory-specialist-shared")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-specialist-a"),
            session_id=SessionId("sess-specialist"),
            mission_id=MissionId("mission-specialist-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )
    continuity = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-specialist-b"),
            session_id=SessionId("sess-specialist"),
            mission_id=MissionId("mission-specialist-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:01:00Z",
        )
    ).continuity_context

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-specialist",
        specialist_hints=["operational_planning_specialist"],
        active_domains=["strategy", "productivity"],
        mission_id="mission-specialist-b",
        continuity_context=continuity,
    )

    shared_memory = contexts["operational_planning_specialist"]
    persisted = service.get_specialist_shared_memory(
        session_id="sess-specialist",
        specialist_type="operational_planning_specialist",
    )

    assert shared_memory.sharing_mode == "core_mediated_read_only"
    assert shared_memory.write_policy == "through_core_only"
    assert shared_memory.related_mission_ids
    assert shared_memory.shared_memory_brief.startswith(
        "specialist=operational_planning_specialist"
    )
    assert persisted is not None
    assert persisted.shared_memory_brief == shared_memory.shared_memory_brief
    assert persisted.write_policy == "through_core_only"
    assert "memory://relational" in persisted.memory_refs
    assert "memory://domain/strategy" in persisted.memory_refs
    assert persisted.memory_class_policies["mission"]["sharing_mode"] == "core_mediated_read_only"
    assert persisted.memory_class_policies["domain"]["domain_linked"] is True
    assert "semantic" not in persisted.consumed_memory_classes
    assert "procedural" not in persisted.consumed_memory_classes
    assert persisted.consumer_mode == "baseline_shared_context"
    assert persisted.mission_context_brief is not None
    assert persisted.domain_context_brief is not None
    assert persisted.continuity_context_brief is not None


def test_memory_service_builds_guided_domain_memory_packet_for_promoted_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-domain")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-memory-1"),
        session_id=SessionId("sess-guided-memory"),
        mission_id=MissionId("mission-guided-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Analyze Python service rollout.",
        timestamp="2026-03-27T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial software analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar rollout do servico Python com contratos estaveis",
            goal="Review Python service rollout",
            steps=["mapear contratos", "comparar mudanca", "recomendar"],
            active_domains=["software_development", "analysis"],
            active_minds=["mente_analitica"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=False,
            rationale="contexto=software",
            specialist_hints=["software_change_specialist"],
            continuity_action="continuar",
            open_loops=["comparar mudanca no servico"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-memory",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development", "analysis"],
        mission_id="mission-guided-memory",
        continuity_context=None,
    )

    guided = contexts["software_change_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert guided.mission_context_brief is not None
    assert "goal=Analyze Python service rollout." in guided.mission_context_brief
    assert guided.domain_context_brief is not None
    assert "active_domains=software_development,analysis" in guided.domain_context_brief
    assert "workflow_profile=software_change_workflow" in guided.domain_context_brief
    assert guided.continuity_context_brief is not None
    assert "continuity_mode=continuar" in guided.continuity_context_brief
    assert guided.consumer_profile == "software_change_review"
    assert guided.consumer_objective is not None
    assert "direção de patch recomendada" in guided.consumer_objective
    assert guided.expected_deliverables == [
        "implementation_findings",
        "change_risk_summary",
        "recommended_patch_direction",
    ]
    assert guided.telemetry_focus == [
        "contract_impact",
        "change_safety",
        "implementation_trace",
    ]

    persisted = service.get_specialist_shared_memory(
        session_id="sess-guided-memory",
        specialist_type="software_change_specialist",
    )
    assert persisted is not None
    assert persisted.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in persisted.consumed_memory_classes
    assert "procedural" in persisted.consumed_memory_classes
    assert guided.semantic_memory_state == "operational"
    assert guided.procedural_memory_state == "operational"
    assert guided.memory_consolidation_status == "in_progress"
    assert guided.memory_fixation_status == "not_fixed"
    assert guided.memory_archive_status == "active_memory"
    assert guided.procedural_artifact_status == "candidate"
    assert guided.procedural_artifact_refs
    assert guided.procedural_artifact_version == 1
    assert guided.procedural_artifact_summary is not None
    assert persisted.consumer_profile == guided.consumer_profile
    assert persisted.consumer_objective == guided.consumer_objective
    assert persisted.expected_deliverables == guided.expected_deliverables
    assert persisted.telemetry_focus == guided.telemetry_focus
    assert persisted.mission_context_brief == guided.mission_context_brief
    assert persisted.domain_context_brief == guided.domain_context_brief
    assert persisted.continuity_context_brief == guided.continuity_context_brief
    assert persisted.semantic_memory_state == "operational"
    assert persisted.procedural_memory_state == "operational"
    assert persisted.memory_consolidation_status == "in_progress"
    assert persisted.memory_fixation_status == "not_fixed"
    assert persisted.memory_archive_status == "active_memory"
    assert persisted.procedural_artifact_status == "candidate"
    assert persisted.procedural_artifact_refs == guided.procedural_artifact_refs
    assert persisted.procedural_artifact_version == guided.procedural_artifact_version
    assert persisted.procedural_artifact_summary == guided.procedural_artifact_summary


def test_memory_service_records_bounded_procedural_playbook_candidate() -> None:
    temp_dir = runtime_dir("memory-procedural-playbook")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    record = service.record_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/001",
            procedure_name="bounded patch review",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            domain="engenharia_de_software",
            bounded_steps=[
                "collect evidence",
                "run targeted tests",
                "prepare rollback",
            ],
            evidence_refs=["trace://req-playbook"],
            source_artifact_refs=["artifact://procedural/software/v1"],
            source_reflection_refs=["reflection://mission/001"],
            proposed_tests=["pytest services/memory-service/tests"],
            rollback_plan_ref="rollback://playbook/001",
            timestamp="2026-07-04T00:00:00Z",
        )
    )
    blocked = service.record_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/blocked",
            procedure_name="unsafe patch review",
            workflow_profile="software_change_workflow",
            bounded_steps=["skip evidence"],
            evidence_refs=[],
            timestamp="2026-07-04T00:01:00Z",
            automatic_promotion_allowed=True,
        )
    )

    assert record.candidate.review_status == "candidate"
    assert record.candidate.automatic_promotion_allowed is False
    assert record.candidate.core_mutation_allowed is False
    assert blocked.candidate.review_status == "needs_review"
    assert "evidence_required" in blocked.candidate.blockers
    assert "rollback_plan_required" in blocked.candidate.blockers
    assert "automatic_promotion_not_allowed" in blocked.candidate.blockers

    records = service.list_procedural_playbook_candidates(
        workflow_profile="software_change_workflow",
        limit=5,
    )
    assert [item.candidate.playbook_candidate_id for item in records] == [
        "playbook-candidate://software-change/blocked",
        "playbook-candidate://software-change/001",
    ]
    assert records[1].candidate.memory_write_mode == "through_core_only"


def test_memory_service_registers_versioned_inactive_skill_candidate() -> None:
    temp_dir = runtime_dir("memory-skill-candidate")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    candidate = SkillCandidateContract(
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence", "report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["trace://release-evidence/1"],
        source_pattern_refs=["recurring-pattern://release-evidence"],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run targeted release tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T14:00:00Z",
    )

    stored = service.record_skill_candidate(candidate)
    idempotent = service.record_skill_candidate(candidate)
    reloaded = service.get_skill_candidate(candidate.skill_candidate_id)
    filtered = service.list_skill_candidates(
        skill_id=candidate.skill_id,
        version="1.0.0",
        domain="software_engineering",
        review_status="needs_review",
    )

    assert stored == idempotent
    assert reloaded == stored
    assert filtered == [stored]
    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.risk_level == RiskLevel.MODERATE
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False


def test_memory_service_contains_unsafe_skill_candidate_claims() -> None:
    temp_dir = runtime_dir("memory-skill-candidate-contained")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )

    stored = service.record_skill_candidate(
        SkillCandidateContract(
            skill_candidate_id="skill-candidate://unsafe-release/1.0.0",
            skill_id="skill://unsafe-release",
            skill_name="unsafe release automation",
            version="1.0.0",
            workflow_profile="software_change_workflow",
            domain="software_engineering",
            specialist_type="software_change_specialist",
            inputs=["release_scope"],
            outputs=["release_decision"],
            allowed_tools=["*"],
            bounded_instructions=["release without review"],
            risk_level=RiskLevel.HIGH,
            evidence_refs=["trace://unsafe-release/1"],
            source_pattern_refs=["recurring-pattern://unsafe-release"],
            failure_modes=["unauthorized_release"],
            proposed_tests=["run release gate"],
            rollback_plan_ref="rollback://skill/unsafe-release/1.0.0",
            registry_status="active",
            review_status="approved",
            activation_status="active",
            sandbox_required=False,
            automatic_activation_allowed=True,
            automatic_promotion_allowed=True,
            core_mutation_allowed=True,
            memory_write_mode="direct",
            timestamp="2026-07-16T14:01:00Z",
        )
    )

    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.sandbox_required is True
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False
    assert stored.candidate.memory_write_mode == "through_core_only"
    assert "high_risk_candidate_requires_explicit_sandbox_review" in (
        stored.candidate.blockers
    )
    assert "activation_status_forced_inactive" in stored.candidate.blockers
    assert "automatic_activation_not_allowed" in stored.candidate.blockers
    assert "allowed_tools_must_be_explicit" in stored.candidate.blockers


def test_memory_service_rejects_skill_candidate_version_collisions_and_mutation() -> None:
    temp_dir = runtime_dir("memory-skill-candidate-immutable")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )

    def candidate(candidate_id: str, *, name: str) -> SkillCandidateContract:
        return SkillCandidateContract(
            skill_candidate_id=candidate_id,
            skill_id="skill://immutable",
            skill_name=name,
            version="1.0.0",
            workflow_profile="software_change_workflow",
            domain="software_engineering",
            specialist_type="software_change_specialist",
            inputs=["input"],
            outputs=["output"],
            allowed_tools=[],
            bounded_instructions=["bounded step"],
            risk_level=RiskLevel.LOW,
            evidence_refs=["trace://immutable/1"],
            source_pattern_refs=["recurring-pattern://immutable"],
            failure_modes=["invalid_output"],
            proposed_tests=["run immutable skill test"],
            rollback_plan_ref="rollback://skill/immutable/1.0.0",
            timestamp="2026-07-16T14:02:00Z",
        )

    service.record_skill_candidate(
        candidate("skill-candidate://immutable/1.0.0", name="immutable skill")
    )

    with pytest.raises(ValueError, match="versions are immutable"):
        service.record_skill_candidate(
            candidate("skill-candidate://immutable/1.0.0", name="mutated skill")
        )
    with pytest.raises(ValueError, match="already belong"):
        service.record_skill_candidate(
            candidate("skill-candidate://immutable-alias/1.0.0", name="alias skill")
        )
    with pytest.raises(ValueError, match="numeric semver"):
        invalid_version = candidate(
            "skill-candidate://immutable/latest",
            name="invalid version",
        )
        invalid_version.version = "latest"
        service.record_skill_candidate(invalid_version)


def test_memory_service_persists_session_continuity_for_governed_reformulation() -> None:
    temp_dir = runtime_dir("memory-session-continuity")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-session-1"),
        session_id=SessionId("sess-session"),
        mission_id=MissionId("mission-session"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Plan created.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-session-2"),
            session_id=SessionId("sess-session"),
            mission_id=MissionId("mission-session"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Please plan the sprint.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            continuity_reason="pedido atual desloca o foco da missao ativa",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-session-3"),
            session_id=SessionId("sess-session"),
            mission_id=MissionId("mission-session"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="How should we proceed?",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert any("session_continuity_mode=reformular" in item for item in recovered.session_context)
    assert any(
        "session_continuity_brief=sessao entrou em reformulacao governada" in item
        for item in recovered.session_context
    )


def test_memory_service_recommends_related_mission_for_new_request_when_score_is_strong() -> None:
    temp_dir = runtime_dir("memory-related-new")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    service.record_turn(
        InputContract(
            request_id=RequestId("req-related-4"),
            session_id=SessionId("sess-related-new"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Rollout plan drafted.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-related-5"),
            session_id=SessionId("sess-related-new"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:03:00Z",
        )
    )

    assert recovered.continuity_context is not None
    assert recovered.continuity_context.recommended_action == "retomar_missao_relacionada"
    assert recovered.continuity_context.related_priority_score is not None
    assert recovered.continuity_context.related_priority_score >= 0.7
    assert any(
        item == "continuity_recommendation=retomar_missao_relacionada"
        for item in recovered.mission_hints
    )


def test_memory_service_ranks_related_candidates_deterministically() -> None:
    temp_dir = runtime_dir("memory-ranked")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    first_plan = sample_plan()
    second_plan = sample_plan()
    second_plan.open_loops = []
    service.record_turn(
        InputContract(
            request_id=RequestId("req-rank-a"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        response_text="Plan A.",
        deliberative_plan=first_plan,
        specialist_contributions=sample_specialist_contributions(),
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-rank-b"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout risk controls.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Plan B.",
        deliberative_plan=second_plan,
        specialist_contributions=[],
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-rank-c"),
            session_id=SessionId("sess-ranked"),
            mission_id=MissionId("mission-c"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout.",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert recovered.continuity_context is not None
    candidates = recovered.continuity_context.related_candidates
    assert [candidate.mission_id for candidate in candidates] == [
        MissionId("mission-b"),
        MissionId("mission-a"),
    ]


def test_build_memory_repository_defaults_to_runtime_sqlite() -> None:
    repository = build_memory_repository(None)
    assert isinstance(repository, SqliteMemoryRepository)


def test_parse_sqlite_database_path_handles_windows_style_urls() -> None:
    database_path = parse_sqlite_database_path("sqlite:///C:/jarvis/runtime/memory.db")
    assert database_path == Path("C:/jarvis/runtime/memory.db")


def test_normalize_database_url_accepts_postgres_aliases() -> None:
    assert (
        normalize_database_url("postgres://user:pass@localhost:5432/jarvis")
        == "postgresql://user:pass@localhost:5432/jarvis"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@localhost:5432/jarvis")
        == "postgresql://user:pass@localhost:5432/jarvis"
    )


def test_build_memory_repository_uses_postgres_for_operational_urls(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakePostgresRepository:
        def __init__(self, database_url: str) -> None:
            captured["database_url"] = database_url

    monkeypatch.setattr(memory_repository, "PostgresMemoryRepository", FakePostgresRepository)
    repository = build_memory_repository("postgres://postgres:postgres@localhost:5432/jarvis")
    assert isinstance(repository, FakePostgresRepository)
    assert captured["database_url"] == "postgresql://postgres:postgres@localhost:5432/jarvis"


def test_memory_service_preserves_accepted_mission_state_on_defer_and_block() -> None:
    temp_dir = runtime_dir("memory-governed")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    mission_contract = InputContract(
        request_id=RequestId("req-accepted"),
        session_id=SessionId("sess-governed"),
        mission_id=MissionId("mission-governed"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Coordinate milestone M3.",
        timestamp="2026-03-17T00:00:00Z",
    )
    accepted_plan = sample_plan()
    service.record_turn(
        mission_contract,
        intent="planning",
        response_text="Milestone plan drafted.",
        deliberative_plan=accepted_plan,
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-defer"),
            session_id=SessionId("sess-governed"),
            mission_id=MissionId("mission-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        ),
        intent="planning",
        response_text="Need explicit validation before changing mission.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="reformular objetivo com impacto operacional",
            goal="Start a new marketing campaign instead.",
            steps=["explicitar conflito", "pedir validacao"],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            constraints=["revisao humana"],
            risks=["pedido contem sinais de risco operacional"],
            recommended_task_type="general_response",
            requires_human_validation=True,
            rationale="contexto=missao ativa; apoio=baseline local",
            continuity_action="reformular",
            open_loops=["fechar checkpoint principal"],
        ),
        governance_decision=PermissionDecision.DEFER_FOR_VALIDATION,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-block"),
            session_id=SessionId("sess-governed"),
            mission_id=MissionId("mission-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all mission records now.",
            timestamp="2026-03-17T00:02:00Z",
        ),
        intent="sensitive_action",
        response_text="Blocked by governance.",
        deliberative_plan=accepted_plan,
        governance_decision=PermissionDecision.BLOCK,
    )

    mission_state = service.get_mission_state("mission-governed")

    assert mission_state is not None
    assert mission_state.mission_goal == "Coordinate milestone M3."
    assert mission_state.last_recommendation == accepted_plan.plan_summary
    assert mission_state.open_loops == ["fechar checkpoint principal"]
    assert mission_state.last_decision_frame == "planning"



def test_memory_service_builds_guided_domain_memory_packet_for_analysis_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-analysis")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-analysis-1"),
        session_id=SessionId("sess-guided-analysis"),
        mission_id=MissionId("mission-guided-analysis"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Compare evidence for the rollout decision.",
        timestamp="2026-03-27T00:10:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial structured analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar evidencias e trade-offs do rollout",
            goal="Compare rollout evidence",
            steps=["coletar evidencias", "comparar trade-offs", "recomendar criterio"],
            active_domains=["analysis", "decision_risk"],
            active_minds=["mente_analitica"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=False,
            rationale="contexto=analysis",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["consolidar criterio dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-analysis",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["analysis", "decision_risk"],
        mission_id="mission-guided-analysis",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert any(ref.startswith("memory://semantic/") for ref in guided.memory_refs)
    assert not any(ref.startswith("memory://procedural/") for ref in guided.memory_refs)
    assert guided.domain_context_brief is not None
    assert "active_domains=analysis,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=structured_analysis_workflow" in guided.domain_context_brief
    persisted = service.get_specialist_shared_memory(
        session_id="sess-guided-analysis",
        specialist_type="structured_analysis_specialist",
    )
    assert persisted is not None
    assert persisted.consumer_mode == "domain_guided_memory_packet"



def test_memory_service_prefers_first_eligible_route_when_specialist_is_shared() -> None:
    temp_dir = runtime_dir("memory-guided-shared-analysis-route")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-shared-analysis-1"),
        session_id=SessionId("sess-guided-shared-analysis"),
        mission_id=MissionId("mission-guided-shared-analysis"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Compare strategic options and clarify the dominant trade-off.",
        timestamp="2026-03-27T00:20:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial strategic analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar trade-offs estrategicos e recomendar direcao",
            goal="Plan strategic options",
            steps=["mapear opcoes", "comparar trade-offs", "recomendar direcao"],
            active_domains=["strategy", "analysis"],
            active_minds=["mente_decisoria"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=strategy",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["fechar criterio estrategico dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-shared-analysis",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["strategy", "analysis"],
        mission_id="mission-guided-shared-analysis",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert guided.consumer_profile == "strategy_tradeoff_review"
    assert guided.consumer_objective is not None
    assert "trade-offs" in guided.consumer_objective
    assert guided.expected_deliverables == [
        "tradeoff_map",
        "decision_criteria",
        "recommended_direction",
    ]
    assert guided.telemetry_focus == [
        "tradeoff_clarity",
        "decision_trace",
        "domain_alignment",
    ]


def sample_operation_dispatch(
    *,
    request_id: str,
    session_id: str,
    mission_id: str,
) -> OperationDispatchContract:
    return OperationDispatchContract(
        operation_id=OperationId("op-sample"),
        request_id=RequestId(request_id),
        task_type="draft_plan",
        task_goal="Coordinate milestone M3.",
        task_plan="Draft milestone plan.",
        constraints=["low-risk"],
        expected_output="markdown plan",
        plan_summary="decompor objetivo em etapas reversiveis",
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        workflow_profile="operational_readiness_workflow",
        workflow_domain_route="operational_readiness",
        workflow_steps=["map readiness", "close checkpoint"],
        workflow_checkpoints=["capture_scope", "close_readiness_checkpoint"],
        workflow_checkpoint_state={
            "capture_scope": "completed",
            "close_readiness_checkpoint": "pending",
        },
        workflow_resume_point="close_readiness_checkpoint",
        workflow_resume_status="resume_available",
        ecosystem_state_status="operational_state_attached",
        active_work_items=["mission_task:Plan milestone M3"],
        active_artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
        open_checkpoint_refs=[
            "workflow_checkpoint:close_readiness_checkpoint:pending"
        ],
        surface_presence=["surface:chat", f"session:{session_id}", f"mission:{mission_id}"],
        ecosystem_state_summary="work_items=1; artifacts=1; open_checkpoints=1; surfaces=3",
        surface_id="surface://jarvis_console",
        surface_kind="console",
        surface_session_id=session_id,
        surface_capability_scope=["text_input"],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
        surface_continuity_status="single_surface",
    )


def sample_operation_result(*, operation_id: str, artifact_ref: str) -> OperationResultContract:
    return OperationResultContract(
        operation_id=OperationId(operation_id),
        status=OperationStatus.COMPLETED,
        outputs=["Milestone plan created."],
        timestamp="2026-04-23T00:00:00Z",
        artifacts=[artifact_ref],
        checkpoints=["workflow_state:completed"],
        ecosystem_state_status="operational_state_attached",
        active_work_items=["mission_task:Plan milestone M3"],
        active_artifact_refs=[
            "artifact://procedural/strategy/milestone-plan/v1",
            artifact_ref,
        ],
        open_checkpoint_refs=[
            "workflow_checkpoint:close_readiness_checkpoint:pending"
        ],
        surface_presence=["surface:chat", "session:sess-eco", "mission:mission-eco"],
        ecosystem_state_summary="work_items=1; artifacts=2; open_checkpoints=1; surfaces=3",
        surface_id="surface://jarvis_console",
        surface_kind="console",
        surface_session_id="sess-eco",
        surface_capability_scope=["text_input"],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
        surface_continuity_status="single_surface",
    )


def test_memory_service_exposes_archivable_lifecycle_policy_for_stale_guided_memory() -> None:
    decision = memory_lifecycle_decision(
        semantic_sources=["related_mission"],
        procedural_sources=["user_scope"],
        continuity_source="fresh_request",
    )

    assert decision.semantic_lifecycle == "aging"
    assert decision.procedural_lifecycle == "aging"
    assert decision.semantic_memory_state == "archivable"
    assert decision.procedural_memory_state == "archivable"
    assert decision.lifecycle_status == "review_recommended"
    assert decision.review_status == "review_recommended"
    assert decision.consolidation_status == "revisit_before_reuse"
    assert decision.fixation_status == "not_fixed"
    assert decision.archive_status == "archive_candidate"


def test_memory_service_recovery_marks_archivable_procedural_artifact_for_review() -> None:
    temp_dir = runtime_dir("memory-archivable-artifact-recovery")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-archivable-artifact-1"),
        session_id=SessionId("sess-archivable-artifact"),
        mission_id=MissionId("mission-archivable-artifact"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Prepare the rollout procedure update.",
        timestamp="2026-04-09T00:00:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Governed rollout procedure stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="estruturar procedimento de rollout com revisao governada",
            goal="Prepare rollout procedure update",
            steps=["preparar patch", "revisar rollback", "publicar checkpoint"],
            active_domains=["software_development"],
            active_minds=["mente_executiva"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=software",
            specialist_hints=["software_change_specialist"],
            continuity_action="continuar",
            open_loops=["revisar checkpoint de rollback"],
            procedural_memory_lifecycle="aging",
            procedural_memory_state="archivable",
            memory_review_status="review_recommended",
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-archivable-artifact-2"),
            session_id=SessionId("sess-archivable-artifact"),
            mission_id=MissionId("mission-archivable-artifact"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the rollout procedure review.",
            timestamp="2026-04-09T00:01:00Z",
        )
    )

    assert "procedural_artifact_status=archivable" in recovered.plan_hints
    assert "memory_recovery_mode=review_before_reuse" in recovered.plan_hints
    assert not any(item.startswith("procedural_artifact_ref=") for item in recovered.plan_hints)
    assert not any(
        item.startswith("procedural_artifact_summary=") for item in recovered.plan_hints
    )


def test_memory_service_blocks_auto_reuse_of_archivable_recurrent_specialist_memory(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("memory-archivable-recurrent-specialist")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    stale_context = SpecialistSharedMemoryContextContract(
        specialist_type="software_change_specialist",
        sharing_mode="core_mediated_read_only",
        continuity_mode="continuar",
        shared_memory_brief="specialist=software_change_specialist continuidade=continuar",
        write_policy="through_core_only",
        consumer_mode="domain_guided_memory_packet",
        semantic_focus=["software_development"],
        semantic_memory_lifecycle="aging",
        procedural_memory_lifecycle="aging",
        semantic_memory_state="archivable",
        procedural_memory_state="archivable",
        memory_lifecycle_status="review_recommended",
        memory_review_status="review_recommended",
        memory_consolidation_status="revisit_before_reuse",
        memory_fixation_status="not_fixed",
        memory_archive_status="archive_candidate",
        recurrent_context_status="recoverable",
        recurrent_interaction_count=2,
        recurrent_context_brief="specialist=software_change_specialist | reuse=enabled",
        recurrent_domain_focus=["software_development"],
        recurrent_memory_refs=["memory://semantic/mission/old"],
        recurrent_continuity_modes=["continuar"],
    )

    monkeypatch.setattr(
        service.repository,
        "fetch_latest_specialist_shared_memory_for_user",
        lambda **_: stale_context,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-archivable-recurrent-specialist",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development"],
        mission_id=None,
        continuity_context=None,
        user_id="user-archivable-recurrent",
    )

    guided = contexts["software_change_specialist"]

    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" not in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.recurrent_context_status == "review_required"
    assert guided.continuity_context_brief is not None
    assert "recurrent_memory_status=review_required" in guided.continuity_context_brief
    assert guided.domain_context_brief is not None
    assert "memory_runtime_mode=review_only" in guided.domain_context_brief


def test_memory_service_builds_guided_domain_memory_packet_for_governance_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-governance")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-governance-1"),
        session_id=SessionId("sess-guided-governance"),
        mission_id=MissionId("mission-guided-governance"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Review governance limits for the rollout.",
        timestamp="2026-03-27T00:30:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial governance analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar limites de governanca do rollout",
            goal="Review governance limits",
            steps=["mapear riscos", "comparar limites", "recomendar contenção"],
            active_domains=["governance", "decision_risk"],
            active_minds=["mente_etica"],
            constraints=["through_core_only"],
            risks=["governance_risk"],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=True,
            rationale="contexto=governance",
            specialist_hints=["governance_review_specialist"],
            continuity_action="continuar",
            open_loops=["validar limite dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-governance",
        specialist_hints=["governance_review_specialist"],
        active_domains=["governance", "decision_risk"],
        mission_id="mission-guided-governance",
        continuity_context=None,
    )

    guided = contexts["governance_review_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=governance,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=governance_boundary_workflow" in guided.domain_context_brief



def test_memory_service_builds_guided_packet_for_readiness_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-readiness")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-readiness-1"),
        session_id=SessionId("sess-guided-readiness"),
        mission_id=MissionId("mission-guided-readiness"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan readiness checks for the release.",
        timestamp="2026-03-27T00:50:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial readiness planning stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="estruturar readiness checks do release",
            goal="Plan readiness checks",
            steps=["mapear readiness", "definir checkpoints", "sugerir rollback"],
            active_domains=["operational_readiness", "observability"],
            active_minds=["mente_executiva"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=readiness",
            specialist_hints=["operational_planning_specialist"],
            continuity_action="continuar",
            open_loops=["fechar checkpoint de readiness"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-readiness",
        specialist_hints=["operational_planning_specialist"],
        active_domains=["operational_readiness", "observability"],
        mission_id="mission-guided-readiness",
        continuity_context=None,
    )

    guided = contexts["operational_planning_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=operational_readiness,observability" in guided.domain_context_brief
    assert "workflow_profile=operational_readiness_workflow" in guided.domain_context_brief



def test_memory_service_builds_guided_packet_for_strategy_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-strategy")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-strategy-1"),
        session_id=SessionId("sess-guided-strategy"),
        mission_id=MissionId("mission-guided-strategy"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan strategic options for the next release.",
        timestamp="2026-03-27T01:10:00Z",
    )
    service.record_turn(
        contract,
        intent="planning",
        response_text="Initial strategy planning stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="comparar direcoes estrategicas do release",
            goal="Plan strategic options",
            steps=["mapear opcoes", "comparar trade-offs", "recomendar criterio"],
            active_domains=["strategy", "decision_risk"],
            active_minds=["mente_decisoria"],
            constraints=["through_core_only"],
            risks=[],
            recommended_task_type="draft_plan",
            requires_human_validation=False,
            rationale="contexto=strategy",
            specialist_hints=["structured_analysis_specialist"],
            continuity_action="continuar",
            open_loops=["fechar criterio estrategico dominante"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-strategy",
        specialist_hints=["structured_analysis_specialist"],
        active_domains=["strategy", "decision_risk"],
        mission_id="mission-guided-strategy",
        continuity_context=None,
    )

    guided = contexts["structured_analysis_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=strategy,decision_risk" in guided.domain_context_brief
    assert "workflow_profile=strategic_direction_workflow" in guided.domain_context_brief


def test_memory_service_builds_guided_packet_for_decision_risk_specialist() -> None:
    temp_dir = runtime_dir("memory-guided-decision-risk")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    contract = InputContract(
        request_id=RequestId("req-guided-decision-risk-1"),
        session_id=SessionId("sess-guided-decision-risk"),
        mission_id=MissionId("mission-guided-decision-risk"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Review decision risk and containment gates for the release.",
        timestamp="2026-03-27T01:30:00Z",
    )
    service.record_turn(
        contract,
        intent="analysis",
        response_text="Initial decision risk analysis stored.",
        deliberative_plan=DeliberativePlanContract(
            plan_summary="avaliar reversibilidade e gate dominante da decisao",
            goal="Review decision risk",
            steps=["mapear risco", "comparar reversibilidade", "recomendar gate dominante"],
            active_domains=["decision_risk", "governance"],
            active_minds=["mente_etica"],
            constraints=["through_core_only"],
            risks=["decision_risk"],
            recommended_task_type="produce_analysis_brief",
            requires_human_validation=True,
            rationale="contexto=decision_risk",
            specialist_hints=["governance_review_specialist"],
            continuity_action="continuar",
            open_loops=["fechar gate dominante de decisao"],
        ),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    contexts = service.prepare_specialist_shared_memory(
        session_id="sess-guided-decision-risk",
        specialist_hints=["governance_review_specialist"],
        active_domains=["decision_risk", "governance"],
        mission_id="mission-guided-decision-risk",
        continuity_context=None,
    )

    guided = contexts["governance_review_specialist"]
    assert guided.consumer_mode == "domain_guided_memory_packet"
    assert "semantic" in guided.consumed_memory_classes
    assert "procedural" not in guided.consumed_memory_classes
    assert guided.domain_context_brief is not None
    assert "active_domains=decision_risk,governance" in guided.domain_context_brief
    assert "workflow_profile=decision_risk_workflow" in guided.domain_context_brief




def test_memory_service_builds_recoverable_recurrent_specialist_context() -> None:
    temp_dir = runtime_dir("memory-specialist-recurrence")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")

    first = service.prepare_specialist_shared_memory(
        session_id="sess-recurrent-1",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development"],
        mission_id=None,
        continuity_context=None,
        user_id="user-recurrent-1",
    )["software_change_specialist"]
    second = service.prepare_specialist_shared_memory(
        session_id="sess-recurrent-2",
        specialist_hints=["software_change_specialist"],
        active_domains=["software_development", "analysis"],
        mission_id=None,
        continuity_context=None,
        user_id="user-recurrent-1",
    )["software_change_specialist"]

    assert first.recurrent_context_status == "seeded"
    assert first.recurrent_interaction_count == 1
    assert second.recurrent_context_status == "recoverable"
    assert second.recurrent_interaction_count == 2
    assert second.recurrent_context_brief is not None
    assert "software_development" in second.recurrent_domain_focus
    assert second.recurrent_continuity_modes == ["continuar"]
    persisted = service.get_specialist_shared_memory(
        session_id="sess-recurrent-2",
        specialist_type="software_change_specialist",
    )
    assert persisted is not None
    assert persisted.recurrent_context_status == "recoverable"
    assert persisted.recurrent_interaction_count == 2


def test_memory_service_recovers_recoverable_user_scope_context() -> None:
    temp_dir = runtime_dir("memory-user-scope")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    user_id = "user-1"
    service.record_turn(
        InputContract(
            request_id=RequestId("req-user-1"),
            session_id=SessionId("sess-user-1"),
            mission_id=MissionId("mission-user-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the first milestone.",
            timestamp="2026-03-31T00:00:00Z",
            user_id=user_id,
        ),
        intent="planning",
        response_text="Initial milestone plan stored.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )
    service.record_turn(
        InputContract(
            request_id=RequestId("req-user-2"),
            session_id=SessionId("sess-user-2"),
            mission_id=MissionId("mission-user-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the milestone trade-offs.",
            timestamp="2026-03-31T00:01:00Z",
            user_id=user_id,
        ),
        intent="analysis",
        response_text="Trade-off analysis stored.",
        deliberative_plan=sample_plan(),
        specialist_contributions=sample_specialist_contributions(),
        governance_decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
    )

    recovered = service.recover_for_input(
        InputContract(
            request_id=RequestId("req-user-3"),
            session_id=SessionId("sess-user-3"),
            mission_id=MissionId("mission-user-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue from the user context.",
            timestamp="2026-03-31T00:02:00Z",
            user_id=user_id,
        )
    )

    assert recovered.organization_scope_status == "no_go_without_canonical_consumer"
    assert recovered.organization_scope_reopen_signal == "canonical_consumer_required_for_reopen"
    assert recovered.user_scope_context is not None
    assert recovered.user_scope_context.context_status == "recoverable"
    assert recovered.user_scope_context.interaction_count == 2
    assert "planning" in recovered.user_scope_context.recent_intents
    assert "analysis" in recovered.user_scope_context.recent_intents
    assert recovered.user_scope_context.recent_domain_focus
    assert any(item == "user_scope_status=recoverable" for item in recovered.user_hints)
    assert any(item.startswith("user_context_brief=") for item in recovered.user_hints)
    assert any(
        item == "context_compaction_status=compressed_live_context"
        for item in recovered.session_context
    )
    assert any(item.startswith("context_live_summary=") for item in recovered.session_context)
    assert any(
        item == "cross_session_recall_status=active" for item in recovered.recovered_items
    )
    assert any(
        item.startswith("cross_session_recall_summary=")
        for item in recovered.recovered_items
    )
    assert any(str(scope.value) == "user" for scope in recovered.recovery_contract.requested_scopes)


def test_memory_lifecycle_queue_requires_human_review_and_never_mutates_sources() -> None:
    temp_dir = runtime_dir("memory-lifecycle-review")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    service.repository.upsert_specialist_shared_memory(
        StoredSpecialistSharedMemory(
            session_id="sess-memory-consolidating",
            specialist_type="software_change_specialist",
            sharing_mode="shared_read_only",
            continuity_mode="continuar",
            shared_memory_brief="consolidating memory",
            write_policy="through_core_only",
            semantic_memory_lifecycle="consolidating",
            procedural_memory_lifecycle="consolidating",
            memory_lifecycle_status="emerging",
            memory_review_status="monitor",
            updated_at="2026-07-16T00:00:00Z",
        )
    )
    service.repository.upsert_specialist_shared_memory(
        StoredSpecialistSharedMemory(
            session_id="sess-memory-aging",
            specialist_type="structured_analysis_specialist",
            sharing_mode="shared_read_only",
            continuity_mode="continuar",
            shared_memory_brief="aging memory",
            write_policy="through_core_only",
            semantic_memory_lifecycle="aging",
            procedural_memory_lifecycle="aging",
            memory_lifecycle_status="review_recommended",
            memory_review_status="review_recommended",
            updated_at="2026-07-16T00:00:00Z",
        )
    )
    service.record_reviewed_learning_guidance(
        ReviewedLearningGuidanceContract(
            guidance_id="reviewed-learning-guidance://expired/001",
            source_review_decision_id="review-decision://expired/001",
            evolution_proposal_id="proposal-expired-001",
            review_status="approved",
            route="software_change",
            workflow_profile="software_change_workflow",
            domain="software_development",
            guidance_summary="use the bounded rollback checklist",
            allowed_usage=["planning_context"],
            evidence_refs=["trace://expired-guidance/001"],
            rollback_plan_ref="rollback://reviewed-learning/expired/001",
            timestamp="2026-07-14T00:00:00Z",
            expires_at="2026-07-15T00:00:00Z",
        )
    )

    generated_at = "2026-07-16T00:00:00Z"
    queue = service.list_memory_lifecycle_review_queue(
        generated_at=generated_at,
        limit=10,
    )
    assert {candidate.maintenance_action for candidate in queue} == {
        "archive",
        "consolidate",
        "expire",
    }
    assert all(candidate.review_status == "needs_review" for candidate in queue)
    assert all(candidate.execution_status == "not_executed" for candidate in queue)
    assert all(not candidate.automatic_execution_allowed for candidate in queue)

    archive_candidate = next(
        candidate for candidate in queue if candidate.maintenance_action == "archive"
    )
    source_summary_before = service.repository.summarize_memory_corpus()
    guidance_before = service.list_reviewed_learning_guidance(limit=10)
    governance = GovernanceService()
    assessment = governance.assess_memory_lifecycle_review(
        archive_candidate,
        decision_action="approve",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/archive/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        assessed_at="2026-07-16T00:00:01Z",
    )
    approved = service.record_memory_lifecycle_review_decision(
        candidate_id=archive_candidate.candidate_id,
        decision_action="approve",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/archive/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        review_notes=["evidence checked; manual execution remains separate"],
        governance_assessment=assessment,
    )

    assert approved.review_status == "approved"
    assert approved.execution_authorized is False
    approved_queue = service.list_memory_lifecycle_review_queue(
        generated_at=generated_at,
        limit=10,
    )
    approved_candidate = next(
        candidate
        for candidate in approved_queue
        if candidate.candidate_id == archive_candidate.candidate_id
    )
    assert approved_candidate.review_status == "approved"
    assert approved_candidate.execution_status == "not_executed"

    rollback_assessment = governance.assess_memory_lifecycle_review(
        approved_candidate,
        decision_action="rollback",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/rollback/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        previous_review_status=approved.review_status,
        assessed_at="2026-07-16T00:00:02Z",
    )
    rolled_back = service.record_memory_lifecycle_review_decision(
        candidate_id=archive_candidate.candidate_id,
        decision_action="rollback",
        operator_ref="operator://memory-reviewer",
        evidence_refs=["trace://memory-review/rollback/001"],
        rollback_plan_ref=archive_candidate.rollback_plan_ref,
        review_notes=["reverted review disposition only"],
        governance_assessment=rollback_assessment,
    )

    assert rolled_back.review_status == "rolled_back"
    assert rolled_back.execution_authorized is False
    assert service.repository.summarize_memory_corpus() == source_summary_before
    assert service.list_reviewed_learning_guidance(limit=10) == guidance_before

    expire_candidate = next(
        candidate for candidate in queue if candidate.maintenance_action == "expire"
    )
    forged_assessment = MemoryLifecycleGovernanceAssessmentContract(
        assessment_id="memory-lifecycle-assessment://forged",
        candidate_id=expire_candidate.candidate_id,
        maintenance_action="expire",
        decision_action="reject",
        status="governed",
        timestamp="2026-07-16T00:00:03Z",
    )
    with pytest.raises(ValueError, match="policy trace required"):
        service.record_memory_lifecycle_review_decision(
            candidate_id=expire_candidate.candidate_id,
            decision_action="reject",
            operator_ref="operator://memory-reviewer",
            evidence_refs=[],
            rollback_plan_ref=None,
            review_notes=[],
            governance_assessment=forged_assessment,
        )
