import importlib.util
from os import getenv
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from memory_service.service import MemoryService

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId
from tools.benchmarks.harness import ADOPT_IN_V1, BenchmarkHarness


def postgres_url() -> str:
    database_url = getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL nao configurada para a integracao PostgreSQL.")
    if importlib.util.find_spec("psycopg") is None:
        pytest.skip("psycopg nao instalado na .venv local.")
    return database_url


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_memory_service_persists_session_history_in_postgres() -> None:
    service = MemoryService(database_url=postgres_url())
    contract = InputContract(
        request_id=RequestId("postgres-req-1"),
        session_id=SessionId("postgres-sess-1"),
        mission_id=MissionId("postgres-mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the PostgreSQL validation flow.",
        timestamp="2026-03-19T00:00:00Z",
    )

    service.record_turn(contract, intent="planning", response_text="PostgreSQL validated.")
    recovered = MemoryService(database_url=postgres_url()).recover_for_input(contract)
    mission_state = MemoryService(database_url=postgres_url()).get_mission_state(
        "postgres-mission-1"
    )

    assert any("PostgreSQL validated." in item for item in recovered.recovered_items)
    assert any(
        ("intent=planning" in item) or ("PostgreSQL validated." in item)
        for item in recovered.recovered_items
    )
    assert mission_state is not None
    assert "planning" in mission_state.active_tasks
    assert mission_state.semantic_brief is not None
    assert "Plan the PostgreSQL validation flow." in mission_state.semantic_brief


def test_memory_benchmark_track_adopts_postgres_when_environment_is_ready() -> None:
    harness = BenchmarkHarness(
        output_dir=str(runtime_dir("memory-benchmark") / "benchmarks"),
        postgres_url=postgres_url(),
    )

    report = harness.run_memory_track()

    assert report.decision == ADOPT_IN_V1
    candidate = report.metrics["candidate"]
    assert candidate["backend"] == "postgresql"
    assert candidate["executed"] is True
    assert candidate["functional_parity"] is True
    assert candidate["persistence_across_instances"] is True
    assert candidate["mission_state_persisted"] is True
    assert candidate["failure_rate"] == 0.0
