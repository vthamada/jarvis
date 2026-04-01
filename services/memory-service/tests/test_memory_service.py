from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import memory_service.repository as memory_repository
from memory_service.repository import (
    SqliteMemoryRepository,
    build_memory_repository,
    normalize_database_url,
    parse_sqlite_database_path,
)
from memory_service.service import MemoryRecordResult, MemoryRecoveryResult, MemoryService

from shared.contracts import DeliberativePlanContract, InputContract, SpecialistContributionContract
from shared.memory_registry import DEFAULT_MEMORY_SCOPES
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    PermissionDecision,
    RequestId,
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
    assert persisted.consumer_profile == guided.consumer_profile
    assert persisted.consumer_objective == guided.consumer_objective
    assert persisted.expected_deliverables == guided.expected_deliverables
    assert persisted.telemetry_focus == guided.telemetry_focus
    assert persisted.mission_context_brief == guided.mission_context_brief
    assert persisted.domain_context_brief == guided.domain_context_brief
    assert persisted.continuity_context_brief == guided.continuity_context_brief


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
    assert any(str(scope.value) == "user" for scope in recovered.recovery_contract.requested_scopes)
