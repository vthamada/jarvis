"""Existing SQLite memory accessed without schema initialization or writes."""

from pathlib import Path
from sqlite3 import Row, connect

from memory_service.repository import SqliteMemoryRepository
from shared.sqlite_connection import ClosingSqliteConnection


class ReadOnlySqliteMemoryRepository(SqliteMemoryRepository):
    def __init__(self, database_path: Path):
        path = Path(database_path)
        if not path.is_absolute() or path.is_symlink() or not path.is_file():
            raise ValueError("existing_memory_database_required")
        self.database_path = path.resolve(strict=True)
        self._require_quiescent_database()
        # No mkdir, CREATE TABLE, schema patch, migration or default DB fallback.

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
        self._require_quiescent_database()
        connection = connect(
            self.database_path.as_uri() + "?mode=ro", uri=True,
            factory=ClosingSqliteConnection,
        )
        connection.row_factory = Row
        connection.execute("PRAGMA query_only=ON")
        return connection
