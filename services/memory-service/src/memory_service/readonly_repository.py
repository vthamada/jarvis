"""Existing SQLite memory accessed without schema initialization or writes."""

import math
import time
from pathlib import Path
from sqlite3 import Connection, Cursor, Row, connect
from typing import Callable

from memory_service.repository import SqliteMemoryRepository
from shared.sqlite_connection import ClosingSqliteConnection


class _ControlledCursor(Cursor):
    """Check short operations as well as the VM's cooperative progress callback."""

    def _run(self, operation, *args, sql=False):
        control = self.connection._read_control
        try:
            if sql:
                control._before_sql(self.connection)
            else:
                control._check_control()
            result = operation(*args)
            control._check_control()
            return result
        except Exception:
            control._refuse_control()

    def execute(self, sql, parameters=()):
        return self._run(super().execute, sql, parameters, sql=True)

    def executemany(self, sql, parameters):
        return self._run(super().executemany, sql, parameters, sql=True)

    def executescript(self, sql_script):
        return self._run(super().executescript, sql_script, sql=True)

    def fetchone(self):
        return self._run(super().fetchone)

    def fetchmany(self, size=None):
        return self._run(super().fetchmany, *(() if size is None else (size,)))

    def fetchall(self):
        return self._run(super().fetchall)

    def __next__(self):
        # Exhaustion is not a failed control and must retain iterator semantics.
        control = self.connection._read_control
        control._check_control()
        try:
            row = super().__next__()
        except StopIteration:
            control._check_control()
            raise
        except Exception:
            control._refuse_control()
        control._check_control()
        return row


class _ControlledConnection(ClosingSqliteConnection):
    def cursor(self, factory=None):
        if factory is not None and factory is not _ControlledCursor:
            self._read_control._refuse_control()
        return super().cursor(factory=_ControlledCursor)

    def execute(self, sql, parameters=()):
        return self.cursor().execute(sql, parameters)

    def executemany(self, sql, parameters):
        return self.cursor().executemany(sql, parameters)

    def executescript(self, sql_script):
        return self.cursor().executescript(sql_script)

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self._read_control._check_control()
        finally:
            result = super().__exit__(exc_type, exc_value, traceback)
        return result


class ReadOnlySqliteMemoryRepository(SqliteMemoryRepository):
    def __init__(self, database_path: Path, *, deadline_monotonic: float | None = None,
                 monotonic_clock: Callable[[], float] = time.monotonic,
                 cancelled: Callable[[], bool] | None = None):
        """Optional single deadline across all connections, never reset per query.

        SQLite VM work is interrupted cooperatively; lock waits receive at most
        the remaining budget. This cannot bound stalled OS file access or a
        blocking user-defined SQLite function, and is not a thread watchdog.
        Existing exporters without controls retain their original behavior.
        """
        self._deadline_monotonic = deadline_monotonic
        self._monotonic_clock = monotonic_clock
        self._cancelled = cancelled
        self._control_failed = False
        self._last_monotonic = None
        self._controlled = deadline_monotonic is not None or cancelled is not None
        try:
            if (deadline_monotonic is not None and (
                    type(deadline_monotonic) not in (int, float)
                    or not math.isfinite(deadline_monotonic))
                    or not callable(monotonic_clock)
                    or cancelled is not None and not callable(cancelled)):
                self._refuse_control()
        except (TypeError, OverflowError):
            self._refuse_control()
        self._check_control()
        path = Path(database_path)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError("existing_memory_database_required")
        self.database_path = path.resolve(strict=True)
        self._require_quiescent_database()
        self._check_control()
        # No mkdir, CREATE TABLE, schema patch, migration or default DB fallback.

    def _refuse_control(self):
        self._control_failed = True
        raise ValueError("readonly_memory_control_refused") from None

    def _check_control(self):
        if self._control_failed:
            self._refuse_control()
        if not self._controlled:
            return 5.0
        try:
            if self._cancelled is not None:
                stopped = self._cancelled()
                if type(stopped) is not bool or stopped:
                    self._refuse_control()
            if self._deadline_monotonic is None:
                return 5.0
            now = self._monotonic_clock()
            if (type(now) not in (int, float) or not math.isfinite(now)
                    or self._last_monotonic is not None and now < self._last_monotonic
                    or now >= self._deadline_monotonic):
                self._refuse_control()
            self._last_monotonic = now
            return min(5.0, self._deadline_monotonic - now)
        except BaseException:
            # SQLite suppresses callback exceptions. Sticky state prevents any
            # caller that catches an interrupted query from recovering success.
            self._refuse_control()

    def _progress(self):
        try:
            self._check_control()
            return 0
        except ValueError:
            return 1

    def _before_sql(self, connection):
        remaining = self._check_control()
        # Use the base method to avoid recursion through guarded execute; floor
        # milliseconds so SQLite's lock timeout never rounds past the budget.
        cursor = Connection.execute(connection, f"PRAGMA busy_timeout={int(remaining * 1000)}")
        cursor.close()
        self._check_control()

    def _require_quiescent_database(self):
        # WAL readers can create -wal/-shm despite mode=ro. This first exporter
        # only accepts a quiescent DELETE-mode database; never use immutable=1
        # against a mutable live store to bypass SQLite locking/change detection.
        with self.database_path.open("rb") as handle:
            header = handle.read(100)
        if (
            len(header) < 100 or header[:16] != b"SQLite format 3\x00"
            or header[18:20] != b"\x01\x01"
            or any(Path(str(self.database_path) + suffix).exists()
                   for suffix in ("-wal", "-shm", "-journal"))
        ):
            raise ValueError("quiescent_delete_mode_database_required")

    def _connect(self):
        remaining = self._check_control()
        self._require_quiescent_database()
        remaining = self._check_control()
        try:
            connection = connect(
                self.database_path.as_uri() + "?mode=ro", uri=True,
                timeout=remaining,
                factory=_ControlledConnection if self._controlled else ClosingSqliteConnection,
            )
        except Exception:
            if self._controlled:
                self._refuse_control()
            raise
        try:
            if self._controlled:
                connection._read_control = self
                self._check_control()
                connection.set_progress_handler(self._progress, 1000)
            connection.row_factory = Row
            connection.execute("PRAGMA query_only=ON")
            self._check_control()
            return connection
        except BaseException:
            connection.close()
            if self._controlled:
                self._refuse_control()
            raise
