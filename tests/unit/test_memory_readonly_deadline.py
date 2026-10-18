"""One opt-in monotonic budget governs readonly SQLite, including setup failures."""

import math
import sqlite3

import pytest
from memory_service import readonly_repository as readonly


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "memory.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE fixture(value INTEGER)")
        connection.execute("INSERT INTO fixture VALUES (7)")
    return path


@pytest.mark.parametrize("deadline", [True, "1", math.nan, math.inf, -math.inf])
def test_invalid_deadline_refused_before_file_access(tmp_path, deadline):
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        readonly.ReadOnlySqliteMemoryRepository(tmp_path / "missing.db",
                                               deadline_monotonic=deadline)


def test_expired_budget_prevents_connect(database, monkeypatch):
    clock = [1.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=2.0, monotonic_clock=lambda: clock[0],
    )
    clock[0] = 2.0

    def forbidden(*_args, **_kwargs):
        pytest.fail("expired read opened SQLite")

    monkeypatch.setattr(readonly, "connect", forbidden)
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        reader._connect()


def test_legacy_default_does_not_consult_clock(database):
    def forbidden():
        pytest.fail("legacy default unexpectedly needs a clock")

    reader = readonly.ReadOnlySqliteMemoryRepository(database, monotonic_clock=forbidden)
    with reader._connect() as connection:
        assert connection.execute("SELECT value FROM fixture").fetchone()[0] == 7
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("INSERT INTO fixture VALUES (9)")


@pytest.mark.parametrize("value", [True, 1, None, "false"])
def test_cancelled_or_invalid_callback_refused(database, value):
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        readonly.ReadOnlySqliteMemoryRepository(database, cancelled=lambda: value)


def test_callback_exception_is_fixed_refusal(database):
    def broken():
        raise RuntimeError("private-clock-detail")

    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        readonly.ReadOnlySqliteMemoryRepository(database, cancelled=broken)


@pytest.mark.parametrize("failure", ["expired", "clock_exception", "pragma_exception"])
def test_connection_setup_failure_closes_owned_handle(database, monkeypatch, failure):
    clock = [0.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=10.0, monotonic_clock=lambda: clock[0],
    )
    opened = []
    real_connect = readonly.connect

    class BrokenSetup(sqlite3.Connection):
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("private-setup-detail")

    def tracked(*args, **kwargs):
        if failure == "pragma_exception":
            kwargs["factory"] = BrokenSetup
        connection = real_connect(*args, **kwargs)
        opened.append(connection)
        if failure == "expired":
            clock[0] = 10.0
        if failure == "clock_exception":
            reader._monotonic_clock = lambda: (_ for _ in ()).throw(RuntimeError("private"))
        return connection

    monkeypatch.setattr(readonly, "connect", tracked)
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        reader._connect()
    assert len(opened) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        sqlite3.Connection.execute(opened[0], "SELECT 1")


@pytest.mark.parametrize("value", [math.nan, math.inf, True, "0", -1.0])
def test_invalid_or_backward_clock_becomes_sticky_refusal(database, value):
    clock = [0.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=10.0, monotonic_clock=lambda: clock[0],
    )
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            clock[0] = value
            connection.execute("SELECT 1")
    clock[0] = 0.0
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        reader._connect()


def test_remaining_budget_decreases_across_queries_and_connections(database):
    clock = [0.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=4.0, monotonic_clock=lambda: clock[0],
    )
    with reader._connect() as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 4000
        clock[0] = 3.0
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 1000
    clock[0] = 3.5
    with reader._connect() as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 500


def test_expiry_after_short_fetch_prevents_success_and_closes(database):
    clock = [0.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=1.0, monotonic_clock=lambda: clock[0],
    )
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            assert connection.execute("SELECT 1").fetchone()[0] == 1
            clock[0] = 1.0
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        connection.execute("SELECT 1")


@pytest.mark.parametrize("operation", ["execute", "fetchone", "fetchmany", "fetchall", "next"])
def test_direct_cursor_short_operations_refuse_after_expiry(database, operation):
    clock = [0.0]
    reader = readonly.ReadOnlySqliteMemoryRepository(
        database, deadline_monotonic=1.0, monotonic_clock=lambda: clock[0],
    )
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            cursor = connection.cursor().execute("SELECT value FROM fixture")
            clock[0] = 1.0
            if operation == "execute":
                cursor.execute("SELECT 1")
            elif operation == "next":
                next(iter(cursor))
            else:
                getattr(cursor, operation)()


def test_direct_cursor_iteration_preserves_exhaustion(database):
    reader = readonly.ReadOnlySqliteMemoryRepository(database, cancelled=lambda: False)
    with reader._connect() as connection:
        rows = list(connection.execute("SELECT value FROM fixture"))
        assert [row[0] for row in rows] == [7]


def test_callback_failure_during_vm_cannot_be_recovered_to_success(database):
    state = {"calls": 0, "broken": False}

    def cancelled():
        state["calls"] += 1
        if state["broken"]:
            raise RuntimeError("private-callback-detail")
        return False

    reader = readonly.ReadOnlySqliteMemoryRepository(database, cancelled=cancelled)
    with pytest.raises(ValueError, match="^readonly_memory_control_refused$"):
        with reader._connect() as connection:
            def break_callback():
                state["broken"] = True
                return 0

            connection.create_function("fixture_break", 0, break_callback)
            try:
                connection.execute(
                    "WITH RECURSIVE n(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM n "
                    "WHERE x<10000000) SELECT sum(x+fixture_break()) FROM n"
                ).fetchone()
            except (sqlite3.OperationalError, ValueError):
                state["broken"] = False
            connection.execute("SELECT 1")
