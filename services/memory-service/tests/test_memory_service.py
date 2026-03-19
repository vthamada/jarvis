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

from shared.contracts import DeliberativePlanContract, InputContract
from shared.types import ChannelType, InputType, MemoryClass, MissionId, RequestId, SessionId


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
        steps=["definir objetivo", "listar etapas", "recomendar proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=nenhum; apoio=baseline local",
    )


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
    )

    reader = MemoryService(database_url=database_url)
    recovered = reader.recover_for_input(contract)

    assert isinstance(record, MemoryRecordResult)
    assert record.record_contract.record_type == "interaction_turn"
    assert any("planning" in item for item in recovered.recovered_items)
    assert any("context_summary=" in item for item in recovered.session_context)
    assert any("prior_plan=" in item for item in recovered.plan_hints)


def test_memory_service_persists_mission_state_with_deliberative_hints() -> None:
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
    )
    mission_state = service.get_mission_state("mission-1")

    assert mission_state is not None
    assert mission_state.mission_goal == "Coordinate milestone M3."
    assert mission_state.checkpoints
    assert "planning" in mission_state.active_tasks
    assert mission_state.last_recommendation == "decompor objetivo em etapas reversiveis"
    assert mission_state.recent_plan_steps


def test_build_memory_repository_defaults_to_runtime_sqlite() -> None:
    repository = build_memory_repository(None)

    assert isinstance(repository, SqliteMemoryRepository)


def test_parse_sqlite_database_path_handles_windows_style_urls() -> None:
    database_path = parse_sqlite_database_path("sqlite:///C:/jarvis/runtime/memory.db")

    assert database_path == Path("C:/jarvis/runtime/memory.db")


def test_normalize_database_url_accepts_postgres_aliases() -> None:
    assert normalize_database_url("postgres://user:pass@localhost:5432/jarvis") == (
        "postgresql://user:pass@localhost:5432/jarvis"
    )
    assert normalize_database_url("postgresql+psycopg://user:pass@localhost:5432/jarvis") == (
        "postgresql://user:pass@localhost:5432/jarvis"
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
