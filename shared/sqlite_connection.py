"""Owned SQLite connections close after their transaction context finishes."""

from sqlite3 import Connection


class ClosingSqliteConnection(Connection):
    """Keep SQLite commit/rollback semantics and release the owned file handle.

    sqlite3.Connection's default context manager does not close the connection.
    Use only for repositories that open a fresh connection per transaction.
    """

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()
