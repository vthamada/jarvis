from pathlib import Path
from tempfile import gettempdir
from types import SimpleNamespace

import pytest

from tools import validate_baseline
from tools.validate_baseline import (
    check_profile_prerequisites,
    collect_preflight,
    resolve_database_url,
    resolve_ruff_command,
    run_governed_mission_smoke,
)


def test_resolve_database_url_uses_sqlite_for_development_profile() -> None:
    database_url = resolve_database_url("development", Path(gettempdir()) / "jarvis-tools-test")

    assert database_url is not None
    assert database_url.startswith("sqlite:///")


def test_resolve_ruff_command_prefers_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate_baseline, "which", lambda command: "C:/tools/ruff.exe")

    assert resolve_ruff_command() == ["ruff"]


def test_resolve_ruff_command_falls_back_to_python_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validate_baseline, "which", lambda command: None)
    monkeypatch.setattr(validate_baseline, "find_spec", lambda module: object())

    assert resolve_ruff_command()[1:] == ["-m", "ruff"]


def test_check_profile_prerequisites_requires_database_url_for_controlled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        check_profile_prerequisites("controlled", Path(gettempdir()) / "jarvis-tools-test")


def test_check_profile_prerequisites_validates_postgres_readiness(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/jarvis")
    monkeypatch.setattr(
        validate_baseline,
        "ensure_database_ready",
        lambda database_url: calls.append(database_url),
    )

    resolved = check_profile_prerequisites("controlled", Path(gettempdir()) / "jarvis-tools-test")

    assert resolved == "postgresql://postgres:postgres@localhost:5432/jarvis"
    assert calls == ["postgresql://postgres:postgres@localhost:5432/jarvis"]


def test_collect_preflight_aggregates_detected_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validate_baseline,
        "resolve_ruff_command",
        lambda: (_ for _ in ()).throw(RuntimeError("missing ruff")),
    )
    monkeypatch.setattr(
        validate_baseline,
        "check_profile_prerequisites",
        lambda profile, target_dir: (_ for _ in ()).throw(RuntimeError("database offline")),
    )

    issues, ruff_command, database_url = collect_preflight("controlled")

    assert issues == ["missing ruff", "database offline"]
    assert ruff_command is None
    assert database_url is None


def test_governed_mission_smoke_declares_bounded_autonomy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_contracts = []
    accepted_plan = SimpleNamespace(
        plan_summary="Controlled rollout plan",
        open_loops=["review rollout evidence"],
    )

    class FakeMemoryService:
        def get_mission_state(self, mission_id: str) -> SimpleNamespace:
            assert mission_id.startswith("mission-validate-")
            return SimpleNamespace(
                mission_goal="Plan the controlled rollout.",
                last_recommendation=accepted_plan.plan_summary,
                open_loops=accepted_plan.open_loops,
            )

    class FakeOrchestrator:
        def __init__(self) -> None:
            self.memory_service = FakeMemoryService()

        def handle_input(self, contract: object) -> SimpleNamespace:
            captured_contracts.append(contract)
            content = contract.content
            if content == "Plan the controlled rollout.":
                decision = validate_baseline.PermissionDecision.ALLOW_WITH_CONDITIONS
            elif content == "Start a new marketing campaign instead.":
                decision = validate_baseline.PermissionDecision.DEFER_FOR_VALIDATION
            else:
                decision = validate_baseline.PermissionDecision.BLOCK
            return SimpleNamespace(
                governance_decision=SimpleNamespace(decision=decision),
                deliberative_plan=accepted_plan,
            )

    monkeypatch.setattr(
        validate_baseline,
        "build_validation_orchestrator",
        lambda **kwargs: FakeOrchestrator(),
    )

    run_governed_mission_smoke("development", "sqlite:///ignored.db")

    assert len(captured_contracts) == 3
    assert {
        (contract.requested_autonomy_level, contract.max_autonomy_level)
        for contract in captured_contracts
    } == {("bounded_core_action", "bounded_core_action")}
