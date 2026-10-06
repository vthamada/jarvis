"""Owned repository connections must not leak handles after a transaction."""

import sqlite3

import pytest

from shared.sqlite_connection import ClosingSqliteConnection


def test_commit_closes_connection(tmp_path):
    path = tmp_path / "owned.db"
    connection = sqlite3.connect(path, factory=ClosingSqliteConnection)
    with connection:
        connection.execute("CREATE TABLE records(value TEXT)")
        connection.execute("INSERT INTO records VALUES ('persisted')")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")
    with sqlite3.connect(path, factory=ClosingSqliteConnection) as check:
        assert check.execute("SELECT value FROM records").fetchone() == ("persisted",)
    # On Windows unlink fails if a database handle remains open.
    path.unlink()


def test_rollback_and_exception_still_close(tmp_path):
    path = tmp_path / "rollback.db"
    with sqlite3.connect(path, factory=ClosingSqliteConnection) as connection:
        connection.execute("CREATE TABLE records(value TEXT)")
    failed = sqlite3.connect(path, factory=ClosingSqliteConnection)
    with pytest.raises(RuntimeError, match="stop"):
        with failed:
            failed.execute("INSERT INTO records VALUES ('not_committed')")
            raise RuntimeError("stop")
    with pytest.raises(sqlite3.ProgrammingError):
        failed.execute("SELECT 1")
    with sqlite3.connect(path, factory=ClosingSqliteConnection) as check:
        assert check.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0
