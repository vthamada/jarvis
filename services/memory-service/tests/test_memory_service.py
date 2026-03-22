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
from shared.types import (
    ChannelType,
    InputType,
    MemoryClass,
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
        specialist_hints=["especialista_planejamento_operacional"],
        success_criteria=["plano deve indicar a menor proxima acao segura"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="continuar a missao",
        continuity_action="continuar",
        open_loops=["fechar checkpoint principal"],
    )


def sample_specialist_contributions() -> list[SpecialistContributionContract]:
    return [
        SpecialistContributionContract(
            specialist_type="especialista_planejamento_operacional",
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
    assert result.recovery_contract.requested_scopes == [
        MemoryClass.CONTEXTUAL,
        MemoryClass.EPISODIC,
        MemoryClass.MISSION,
    ]


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
    assert recovered.mission_hints == []
    assert any("prior_plan=" in item for item in recovered.plan_hints)


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
    assert any(item == "related_mission_id=mission-a" for item in recovered.mission_hints)
    assert any(
        item == "continuity_recommendation=priorizar_loop_ativo"
        for item in recovered.mission_hints
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
