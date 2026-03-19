"""Persistent repository for local observability data."""

from __future__ import annotations

from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, Row
from sqlite3 import connect as sqlite_connect

from shared.events import InternalEventEnvelope


class ObservabilityRepository:
    """Store and query structured events for local tracing."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def record_event(self, event: InternalEventEnvelope) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO internal_events (
                    event_id, event_name, timestamp, source_service, payload,
                    correlation_id, request_id, session_id, mission_id, operation_id, tags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.event_name,
                    event.timestamp,
                    event.source_service,
                    dumps(event.payload),
                    event.correlation_id,
                    event.request_id,
                    event.session_id,
                    event.mission_id,
                    event.operation_id,
                    dumps(event.tags),
                ),
            )
            connection.commit()

    def list_events(
        self,
        *,
        limit: int = 20,
        request_id: str | None = None,
        session_id: str | None = None,
        mission_id: str | None = None,
        correlation_id: str | None = None,
        operation_id: str | None = None,
    ) -> list[InternalEventEnvelope]:
        clauses = []
        params: list[object] = []
        if request_id:
            clauses.append("request_id = ?")
            params.append(request_id)
        if session_id:
            clauses.append("session_id = ?")
            params.append(session_id)
        if mission_id:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if correlation_id:
            clauses.append("correlation_id = ?")
            params.append(correlation_id)
        if operation_id:
            clauses.append("operation_id = ?")
            params.append(operation_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = (
            "SELECT event_id, event_name, timestamp, source_service, payload, "
            "correlation_id, request_id, session_id, mission_id, operation_id, tags "
            "FROM internal_events "
            f"{where} "
            "ORDER BY timestamp DESC, rowid DESC "
            "LIMIT ?"
        )
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_event(row) for row in reversed(rows)]

    def _connect(self) -> Connection:
        connection = sqlite_connect(self.database_path)
        connection.row_factory = Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS internal_events (
                    event_id TEXT PRIMARY KEY,
                    event_name TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_service TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    correlation_id TEXT,
                    request_id TEXT,
                    session_id TEXT,
                    mission_id TEXT,
                    operation_id TEXT,
                    tags TEXT NOT NULL
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(internal_events)").fetchall()
            }
            if "operation_id" not in columns:
                connection.execute("ALTER TABLE internal_events ADD COLUMN operation_id TEXT")
            connection.commit()

    @staticmethod
    def _row_to_event(row: Row) -> InternalEventEnvelope:
        payload = loads(str(row["payload"]))
        tags = list(loads(str(row["tags"])))
        return InternalEventEnvelope(
            event_id=str(row["event_id"]),
            event_name=str(row["event_name"]),
            timestamp=str(row["timestamp"]),
            source_service=str(row["source_service"]),
            payload=payload,
            correlation_id=row["correlation_id"],
            request_id=row["request_id"],
            session_id=row["session_id"],
            mission_id=row["mission_id"],
            operation_id=row["operation_id"],
            tags=tags,
        )
