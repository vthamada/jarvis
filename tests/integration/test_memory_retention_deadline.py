"""Real SQLite VM/lock interruption, canonical CLI completion, and no mutations."""

import hashlib
import sqlite3
import time
from datetime import UTC, datetime, timedelta

import pytest
from memory_service import readonly_repository as readonly

from apps.jarvis_console import memory_retention_cli as retention
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId

SUBJECT, SESSION = "user://deadline-fixture", "deadline-session"


def fingerprint(directory):
    return {item.name: (hashlib.sha256(item.read_bytes()).hexdigest(), item.stat().st_mtime_ns,
                        item.stat().st_size) for item in directory.iterdir() if item.is_file()}


def canonical_source(directory):
    core = _isolated_core(directory)
    core.handle_input(InputContract(
        request_id=RequestId("deadline-source-1"), session_id=SessionId(SESSION),
        user_id=SUBJECT, canonical_user_ref=SUBJECT, surface_session_id=SESSION,
        channel=ChannelType.CONSOLE, input_type=InputType.TEXT,
        content="Compare the pilot documentation and observability reports.",
        timestamp=datetime.now(UTC).isoformat(), requested_autonomy_level="assist_only",
        max_autonomy_level="assist_only",
    ))
    turns = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == 1
    return directory / "memory.db", (
        datetime.fromisoformat(turns[0].timestamp) + timedelta(days=31)
    ).isoformat()


def fixture_database(tmp_path):
    path = tmp_path / "memory.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE fixture(value INTEGER)")
        connection.execute("INSERT INTO fixture VALUES (7)")
    return path


def test_real_recursive_sql_exhausts_one_deadline_without_mutation(tmp_path):
    path = fixture_database(tmp_path)
    before = fingerprint(tmp_path)
    reader = readonly.ReadOnlySqliteMemoryRepository(
        path, deadline_monotonic=time.monotonic() + 0.1,
    )
    started = time.monotonic()
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            connection.execute(
                "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n "
                "WHERE x<1000000000) SELECT sum(x) FROM n"
            ).fetchone()
    assert time.monotonic() - started < 2.0  # Scheduling margin, not a hard OS promise.
    assert fingerprint(tmp_path) == before
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


def test_real_sql_vm_observes_cancellation_without_partial_rows(tmp_path):
    path = fixture_database(tmp_path)
    before = fingerprint(tmp_path)
    state = {"cancelled": False, "steps": 0}
    reader = readonly.ReadOnlySqliteMemoryRepository(path, cancelled=lambda: state["cancelled"])
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            def cancel_after_first_step():
                state["steps"] += 1
                state["cancelled"] = True
                return 1

            connection.create_function("fixture_step", 0, cancel_after_first_step)
            connection.execute(
                "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n "
                "WHERE x<1000000) SELECT sum(x+fixture_step()) FROM n"
            ).fetchone()
    assert 0 < state["steps"] < 1000000
    assert fingerprint(tmp_path) == before


def test_real_exclusive_lock_wait_is_bounded_by_remaining_budget(tmp_path):
    path = fixture_database(tmp_path)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with sqlite3.connect(path) as locker:
        # BEGIN EXCLUSIVE without writes leaves the DELETE-mode file quiescent;
        # nevertheless, a different reader must wait for the real SQLite lock.
        locker.execute("BEGIN EXCLUSIVE")
        reader = readonly.ReadOnlySqliteMemoryRepository(
            path, deadline_monotonic=time.monotonic() + 0.15,
        )
        started = time.monotonic()
        with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
            with reader._connect() as connection:
                connection.execute("SELECT value FROM fixture").fetchall()
        assert time.monotonic() - started < 2.0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert {item.name for item in tmp_path.iterdir()} == {"memory.db"}


def test_retention_cli_preserves_positive_canonical_review_without_writes(tmp_path):
    path, as_of = canonical_source(tmp_path)
    before = fingerprint(tmp_path)
    result = retention.build_memory_retention_report(
        authorized=True, database_path=path, subject_id=SUBJECT,
        session_ids=(SESSION,), as_of=as_of,
    )
    assert result["status"] == "review_ready"
    assert result["candidate_count"] == 1
    assert result["mutation_performed"] is False and result["authority"] == "none"
    assert fingerprint(tmp_path) == before


def test_retention_cli_budget_applies_inside_first_real_sql(tmp_path, monkeypatch, capsys):
    path, as_of = canonical_source(tmp_path)
    before = fingerprint(tmp_path)
    clock = {"value": 0.0, "steps": 0}
    monkeypatch.setattr(retention, "time", type("Clock", (), {
        "monotonic": staticmethod(lambda: clock["value"]),
    }))

    def long_snapshot(self, _subject):
        with self._connect() as connection:
            def step():
                clock["steps"] += 1
                clock["value"] = 6.0
                return 1

            connection.create_function("fixture_step", 0, step)
            connection.execute(
                "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n "
                "WHERE x<1000000) SELECT sum(x+fixture_step()) FROM n"
            ).fetchone()
        return None

    monkeypatch.setattr(readonly.ReadOnlySqliteMemoryRepository,
                        "fetch_user_scope_snapshot", long_snapshot)
    assert retention.main([
        "--authorized", "--memory-db", str(path), "--subject-id", SUBJECT,
        "--session-id", SESSION, "--as-of", as_of,
    ]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err.strip() == '{"error_code": "memory_retention_refused"}'
    assert 0 < clock["steps"] < 1000000
    assert fingerprint(tmp_path) == before
