from __future__ import annotations

from json import loads
from pathlib import Path
from sqlite3 import connect

import pytest

from apps.jarvis_console import cli
from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.commands.doctor import (
    build_doctor_report,
    render_doctor_report,
)


def _initialize_sqlite(path: Path) -> None:
    with connect(path) as connection:
        connection.execute("CREATE TABLE doctor_fixture (id INTEGER PRIMARY KEY)")


def test_doctor_reads_initialized_stores_without_mutating_them(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    stores = [
        runtime_dir / "memory.db",
        runtime_dir / "evolution.db",
        runtime_dir / "observability.db",
    ]
    for store in stores:
        _initialize_sqlite(store)
    before = {store: (store.read_bytes(), store.stat().st_mtime_ns) for store in stores}

    report = build_doctor_report(
        root=ROOT,
        runtime_dir=runtime_dir,
        memory_db=stores[0],
        evolution_db=stores[1],
        observability_db=stores[2],
    )

    assert report.status == "healthy"
    assert report.recommended_exit_code == 0
    assert report.warning_count == 0
    assert report.failed_count == 0
    assert report.read_only is True
    assert report.repair_allowed is False
    assert report.write_attempted is False
    assert {
        check.check_id: check.status for check in report.checks
    }["governance_boundary"] == "passed"
    assert {
        store: (store.read_bytes(), store.stat().st_mtime_ns) for store in stores
    } == before
    rendered = render_doctor_report(report)
    assert str(tmp_path) not in rendered
    assert "doctor=read_only" in rendered


def test_doctor_reports_missing_runtime_and_stores_without_creating_them(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "missing-runtime"
    stores = [
        runtime_dir / "memory.db",
        runtime_dir / "evolution.db",
        runtime_dir / "observability.db",
    ]

    report = build_doctor_report(
        root=ROOT,
        runtime_dir=runtime_dir,
        memory_db=stores[0],
        evolution_db=stores[1],
        observability_db=stores[2],
    )

    assert report.status == "degraded"
    assert report.recommended_exit_code == 0
    assert report.warning_count == 4
    assert not runtime_dir.exists()
    assert all(not store.exists() for store in stores)


def test_doctor_fails_closed_for_invalid_store_without_mutating_it(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    invalid_store = runtime_dir / "memory.db"
    invalid_store.write_bytes(b"not-a-sqlite-database")
    before = invalid_store.read_bytes()

    report = build_doctor_report(
        root=ROOT,
        runtime_dir=runtime_dir,
        memory_db=invalid_store,
        evolution_db=runtime_dir / "missing-evolution.db",
        observability_db=runtime_dir / "missing-observability.db",
    )

    memory_check = next(
        check for check in report.checks if check.check_id == "memory_store"
    )
    assert report.status == "failed"
    assert report.recommended_exit_code == 1
    assert memory_check.status == "failed"
    assert memory_check.summary.startswith("store_unreachable:")
    assert invalid_store.read_bytes() == before


def test_doctor_fails_when_backlog_and_master_map_are_not_synchronized(
    tmp_path: Path,
) -> None:
    implementation_dir = tmp_path / "docs" / "implementation"
    implementation_dir.mkdir(parents=True)
    (implementation_dir / "execution-backlog.md").write_text(
        "### MB-999\n\n- `status`: `ready`\n",
        encoding="utf-8",
    )
    (implementation_dir / "implementation-master-map.md").write_text(
        "### MB-999 -- Drifted\n\nStatus: blocked.\n",
        encoding="utf-8",
    )
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()

    report = build_doctor_report(
        root=tmp_path,
        runtime_dir=runtime_dir,
        memory_db=runtime_dir / "memory.db",
        evolution_db=runtime_dir / "evolution.db",
        observability_db=runtime_dir / "observability.db",
    )

    backlog_check = next(
        check for check in report.checks if check.check_id == "backlog_state"
    )
    assert report.status == "failed"
    assert backlog_check.status == "failed"
    assert backlog_check.summary.startswith("status_drift:")


def test_cli_doctor_supports_json_and_does_not_construct_core_or_create_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_dir = tmp_path / "missing-runtime"

    def fail_build(*args: object, **kwargs: object) -> None:
        pytest.fail("standalone doctor command constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", fail_build)

    exit_code = cli.main(
        [
            "doctor",
            "--runtime-dir",
            str(runtime_dir),
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["schema_version"] == "jarvis-console/v1"
    assert payload["command_id"] == "doctor"
    assert payload["status"] == "degraded"
    assert set(payload["warnings"]) == {
        "runtime_directory",
        "memory_store",
        "evolution_store",
        "observability_store",
    }
    assert "doctor=read_only" in payload["outputs"][0]
    assert not runtime_dir.exists()


def test_cli_doctor_returns_runtime_error_for_invalid_store(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_dir = tmp_path / "runtime"
    runtime_dir.mkdir()
    invalid_store = runtime_dir / "invalid.db"
    invalid_store.write_text("invalid", encoding="utf-8")

    exit_code = cli.main(
        [
            "doctor",
            "--runtime-dir",
            str(runtime_dir),
            "--memory-db",
            str(invalid_store),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err == ""
    assert "status=failed" in captured.out
    assert "check_id=memory_store" in captured.out
