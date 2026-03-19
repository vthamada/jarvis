from pathlib import Path
from tempfile import gettempdir

import pytest

from tools import validate_v1
from tools.validate_v1 import (
    check_profile_prerequisites,
    collect_preflight,
    resolve_database_url,
    resolve_ruff_command,
)


def test_resolve_database_url_uses_sqlite_for_development_profile() -> None:
    database_url = resolve_database_url("development", Path(gettempdir()) / "jarvis-tools-test")

    assert database_url is not None
    assert database_url.startswith("sqlite:///")


def test_resolve_ruff_command_prefers_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(validate_v1, "which", lambda command: "C:/tools/ruff.exe")

    assert resolve_ruff_command() == ["ruff"]


def test_resolve_ruff_command_falls_back_to_python_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validate_v1, "which", lambda command: None)
    monkeypatch.setattr(validate_v1, "find_spec", lambda module: object())

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
        validate_v1,
        "ensure_database_ready",
        lambda database_url: calls.append(database_url),
    )

    resolved = check_profile_prerequisites("controlled", Path(gettempdir()) / "jarvis-tools-test")

    assert resolved == "postgresql://postgres:postgres@localhost:5432/jarvis"
    assert calls == ["postgresql://postgres:postgres@localhost:5432/jarvis"]


def test_collect_preflight_aggregates_detected_issues(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        validate_v1,
        "resolve_ruff_command",
        lambda: (_ for _ in ()).throw(RuntimeError("missing ruff")),
    )
    monkeypatch.setattr(
        validate_v1,
        "check_profile_prerequisites",
        lambda profile, target_dir: (_ for _ in ()).throw(RuntimeError("database offline")),
    )

    issues, ruff_command, database_url = collect_preflight("controlled")

    assert issues == ["missing ruff", "database offline"]
    assert ruff_command is None
    assert database_url is None
