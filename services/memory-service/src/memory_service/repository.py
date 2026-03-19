"""Persistent repositories for the memory service."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, OperationalError, Row
from sqlite3 import connect as sqlite_connect
from urllib.parse import urlparse

from shared.contracts import MissionStateContract
from shared.types import MissionStatus

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when postgres backend is unavailable.
    psycopg = None
    dict_row = None


@dataclass(frozen=True)
class StoredTurn:
    session_id: str
    mission_id: str | None
    user_id: str | None
    request_content: str
    intent: str
    response_text: str
    timestamp: str
    plan_summary: str | None = None
    plan_steps: list[str] = field(default_factory=list)
    recommended_task_type: str | None = None


class MemoryRepository(ABC):
    """Persistence contract for episodic, contextual, and mission memory."""

    @abstractmethod
    def record_turn(self, turn: StoredTurn) -> None:
        """Persist a turn and refresh the derived session context."""

    @abstractmethod
    def fetch_recent_turns(self, session_id: str, limit: int) -> list[StoredTurn]:
        """Load the most recent turns for a session."""

    @abstractmethod
    def fetch_context_summary(self, session_id: str) -> str | None:
        """Load the latest derived context summary for a session."""

    @abstractmethod
    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        """Persist the latest known mission state."""

    @abstractmethod
    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Load a persisted mission state, if any."""


class SqliteMemoryRepository(MemoryRepository):
    """SQLite-backed implementation used for local persistence and tests."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def record_turn(self, turn: StoredTurn) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO interaction_turns (
                    session_id, mission_id, user_id, request_content, intent, response_text,
                    timestamp, plan_summary, plan_steps, recommended_task_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.session_id,
                    turn.mission_id,
                    turn.user_id,
                    turn.request_content,
                    turn.intent,
                    turn.response_text,
                    turn.timestamp,
                    turn.plan_summary,
                    dumps(turn.plan_steps),
                    turn.recommended_task_type,
                ),
            )
            summary = self._build_summary(connection, turn.session_id)
            connection.execute(
                """
                INSERT INTO session_context (session_id, recent_summary, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    recent_summary = excluded.recent_summary,
                    updated_at = excluded.updated_at
                """,
                (turn.session_id, summary, turn.timestamp),
            )
            connection.commit()

    def fetch_recent_turns(self, session_id: str, limit: int) -> list[StoredTurn]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT session_id, mission_id, user_id, request_content, intent, response_text,
                       timestamp, plan_summary, plan_steps, recommended_task_type
                FROM interaction_turns
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._row_to_turn(row) for row in reversed(rows)]

    def fetch_context_summary(self, session_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT recent_summary
                FROM session_context
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        return None if row is None else str(row["recent_summary"])

    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mission_states (
                    mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                    related_memories, related_artifacts, recent_plan_steps,
                    last_recommendation, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    mission_goal = excluded.mission_goal,
                    mission_status = excluded.mission_status,
                    checkpoints = excluded.checkpoints,
                    active_tasks = excluded.active_tasks,
                    related_memories = excluded.related_memories,
                    related_artifacts = excluded.related_artifacts,
                    recent_plan_steps = excluded.recent_plan_steps,
                    last_recommendation = excluded.last_recommendation,
                    updated_at = excluded.updated_at
                """,
                (
                    str(mission_state.mission_id),
                    mission_state.mission_goal,
                    mission_state.mission_status.value,
                    dumps(mission_state.checkpoints),
                    dumps(mission_state.active_tasks),
                    dumps(mission_state.related_memories),
                    dumps(mission_state.related_artifacts),
                    dumps(mission_state.recent_plan_steps),
                    mission_state.last_recommendation,
                    mission_state.updated_at,
                ),
            )
            connection.commit()

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, updated_at
                FROM mission_states
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        return None if row is None else self._row_to_mission_state(row)

    def _connect(self) -> Connection:
        connection = sqlite_connect(self.database_path)
        connection.row_factory = Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS interaction_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    user_id TEXT,
                    request_content TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    plan_summary TEXT,
                    plan_steps TEXT,
                    recommended_task_type TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_interaction_turns_session_timestamp
                ON interaction_turns (session_id, timestamp);

                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    recent_summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS mission_states (
                    mission_id TEXT PRIMARY KEY,
                    mission_goal TEXT NOT NULL,
                    mission_status TEXT NOT NULL,
                    checkpoints TEXT NOT NULL,
                    active_tasks TEXT NOT NULL,
                    related_memories TEXT NOT NULL,
                    related_artifacts TEXT NOT NULL DEFAULT '[]',
                    recent_plan_steps TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(connection, "interaction_turns", "plan_summary", "TEXT")
            self._ensure_column(connection, "interaction_turns", "plan_steps", "TEXT")
            self._ensure_column(connection, "interaction_turns", "recommended_task_type", "TEXT")
            self._ensure_column(
                connection, "mission_states", "related_artifacts", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(
                connection, "mission_states", "recent_plan_steps", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(connection, "mission_states", "last_recommendation", "TEXT")
            connection.commit()

    def _ensure_column(
        self, connection: Connection, table: str, column: str, definition: str
    ) -> None:
        try:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except OperationalError:
            pass

    def _build_summary(self, connection: Connection, session_id: str) -> str:
        rows = connection.execute(
            """
            SELECT request_content, intent, response_text, plan_summary
            FROM interaction_turns
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 3
            """,
            (session_id,),
        ).fetchall()
        fragments = []
        for row in reversed(rows):
            fragment = (
                f"intent={row['intent']} user={row['request_content']} "
                f"response={row['response_text']}"
            )
            if row["plan_summary"]:
                fragment = f"{fragment} plan={row['plan_summary']}"
            fragments.append(fragment)
        return " || ".join(fragments)

    @staticmethod
    def _row_to_turn(row: Row) -> StoredTurn:
        return StoredTurn(
            session_id=str(row["session_id"]),
            mission_id=row["mission_id"],
            user_id=row["user_id"],
            request_content=str(row["request_content"]),
            intent=str(row["intent"]),
            response_text=str(row["response_text"]),
            timestamp=str(row["timestamp"]),
            plan_summary=row["plan_summary"],
            plan_steps=list(loads(row["plan_steps"] or "[]")),
            recommended_task_type=row["recommended_task_type"],
        )

    @staticmethod
    def _row_to_mission_state(row: Row) -> MissionStateContract:
        return MissionStateContract(
            mission_id=row["mission_id"],
            mission_goal=str(row["mission_goal"]),
            mission_status=MissionStatus(str(row["mission_status"])),
            checkpoints=list(loads(row["checkpoints"])),
            active_tasks=list(loads(row["active_tasks"])),
            related_memories=list(loads(row["related_memories"])),
            related_artifacts=list(loads(row["related_artifacts"] or "[]")),
            recent_plan_steps=list(loads(row["recent_plan_steps"] or "[]")),
            last_recommendation=row["last_recommendation"],
            updated_at=str(row["updated_at"]),
        )


class PostgresMemoryRepository(MemoryRepository):
    """PostgreSQL-backed implementation aligned with the v1 persistence target."""

    def __init__(self, database_url: str) -> None:
        if psycopg is None:  # pragma: no cover - depends on environment packages.
            raise RuntimeError("psycopg is required for PostgreSQL memory persistence.")
        self.database_url = database_url
        self._init_schema()

    def record_turn(self, turn: StoredTurn) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO interaction_turns (
                    session_id, mission_id, user_id, request_content, intent, response_text,
                    timestamp, plan_summary, plan_steps, recommended_task_type
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    turn.session_id,
                    turn.mission_id,
                    turn.user_id,
                    turn.request_content,
                    turn.intent,
                    turn.response_text,
                    turn.timestamp,
                    turn.plan_summary,
                    dumps(turn.plan_steps),
                    turn.recommended_task_type,
                ),
            )
            cursor.execute(
                """
                SELECT request_content, intent, response_text, plan_summary
                FROM interaction_turns
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT 3
                """,
                (turn.session_id,),
            )
            rows = cursor.fetchall()
            summary = " || ".join(
                [
                    (
                        (
                            f"intent={row['intent']} user={row['request_content']} "
                            f"response={row['response_text']}"
                        )
                        + (f" plan={row['plan_summary']}" if row["plan_summary"] else "")
                    )
                    for row in reversed(rows)
                ]
            )
            cursor.execute(
                """
                INSERT INTO session_context (session_id, recent_summary, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    recent_summary = EXCLUDED.recent_summary,
                    updated_at = EXCLUDED.updated_at
                """,
                (turn.session_id, summary, turn.timestamp),
            )
            connection.commit()

    def fetch_recent_turns(self, session_id: str, limit: int) -> list[StoredTurn]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, mission_id, user_id, request_content, intent, response_text,
                       timestamp, plan_summary, plan_steps, recommended_task_type
                FROM interaction_turns
                WHERE session_id = %s
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                (session_id, limit),
            )
            rows = cursor.fetchall()
        return [
            StoredTurn(
                session_id=row["session_id"],
                mission_id=row["mission_id"],
                user_id=row["user_id"],
                request_content=row["request_content"],
                intent=row["intent"],
                response_text=row["response_text"],
                timestamp=row["timestamp"],
                plan_summary=row["plan_summary"],
                plan_steps=list(loads(row["plan_steps"] or "[]")),
                recommended_task_type=row["recommended_task_type"],
            )
            for row in reversed(rows)
        ]

    def fetch_context_summary(self, session_id: str) -> str | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT recent_summary FROM session_context WHERE session_id = %s",
                (session_id,),
            )
            row = cursor.fetchone()
        return None if row is None else str(row["recent_summary"])

    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mission_states (
                    mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                    related_memories, related_artifacts, recent_plan_steps,
                    last_recommendation, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (mission_id) DO UPDATE SET
                    mission_goal = EXCLUDED.mission_goal,
                    mission_status = EXCLUDED.mission_status,
                    checkpoints = EXCLUDED.checkpoints,
                    active_tasks = EXCLUDED.active_tasks,
                    related_memories = EXCLUDED.related_memories,
                    related_artifacts = EXCLUDED.related_artifacts,
                    recent_plan_steps = EXCLUDED.recent_plan_steps,
                    last_recommendation = EXCLUDED.last_recommendation,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    str(mission_state.mission_id),
                    mission_state.mission_goal,
                    mission_state.mission_status.value,
                    dumps(mission_state.checkpoints),
                    dumps(mission_state.active_tasks),
                    dumps(mission_state.related_memories),
                    dumps(mission_state.related_artifacts),
                    dumps(mission_state.recent_plan_steps),
                    mission_state.last_recommendation,
                    mission_state.updated_at,
                ),
            )
            connection.commit()

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, updated_at
                FROM mission_states
                WHERE mission_id = %s
                """,
                (mission_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return MissionStateContract(
            mission_id=row["mission_id"],
            mission_goal=row["mission_goal"],
            mission_status=MissionStatus(row["mission_status"]),
            checkpoints=list(loads(row["checkpoints"])),
            active_tasks=list(loads(row["active_tasks"])),
            related_memories=list(loads(row["related_memories"])),
            related_artifacts=list(loads(row["related_artifacts"] or "[]")),
            recent_plan_steps=list(loads(row["recent_plan_steps"] or "[]")),
            last_recommendation=row["last_recommendation"],
            updated_at=row["updated_at"],
        )

    def _connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_schema(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS interaction_turns (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    mission_id TEXT,
                    user_id TEXT,
                    request_content TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    plan_summary TEXT,
                    plan_steps TEXT,
                    recommended_task_type TEXT
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_interaction_turns_session_timestamp
                ON interaction_turns (session_id, timestamp)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_context (
                    session_id TEXT PRIMARY KEY,
                    recent_summary TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mission_states (
                    mission_id TEXT PRIMARY KEY,
                    mission_goal TEXT NOT NULL,
                    mission_status TEXT NOT NULL,
                    checkpoints TEXT NOT NULL,
                    active_tasks TEXT NOT NULL,
                    related_memories TEXT NOT NULL,
                    related_artifacts TEXT NOT NULL DEFAULT '[]',
                    recent_plan_steps TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                "ALTER TABLE interaction_turns ADD COLUMN IF NOT EXISTS plan_summary TEXT"
            )
            cursor.execute("ALTER TABLE interaction_turns ADD COLUMN IF NOT EXISTS plan_steps TEXT")
            cursor.execute(
                "ALTER TABLE interaction_turns ADD COLUMN IF NOT EXISTS recommended_task_type TEXT"
            )
            cursor.execute(
                (
                    "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                    "related_artifacts TEXT NOT NULL DEFAULT '[]'"
                )
            )
            cursor.execute(
                (
                    "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                    "recent_plan_steps TEXT NOT NULL DEFAULT '[]'"
                )
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS last_recommendation TEXT"
            )
            connection.commit()


def build_memory_repository(database_url: str | None) -> MemoryRepository:
    """Create the best available repository for the configured database URL."""

    normalized_url = normalize_database_url(database_url)
    if normalized_url and is_postgres_url(normalized_url):
        return PostgresMemoryRepository(normalized_url)
    if normalized_url and normalized_url.startswith("sqlite:///"):
        return SqliteMemoryRepository(parse_sqlite_database_path(normalized_url))
    runtime_db = Path.cwd() / ".jarvis_runtime" / "memory.db"
    return SqliteMemoryRepository(runtime_db)


def normalize_database_url(database_url: str | None) -> str | None:
    """Normalize supported database URLs to the forms expected by the repositories."""

    if not database_url:
        return None
    if database_url.startswith("postgres://"):
        return f"postgresql://{database_url.removeprefix('postgres://')}"
    if database_url.startswith("postgresql+psycopg://"):
        return f"postgresql://{database_url.removeprefix('postgresql+psycopg://')}"
    return database_url


def is_postgres_url(database_url: str) -> bool:
    """Return whether the given normalized URL targets PostgreSQL."""

    return database_url.startswith("postgresql://")


def parse_sqlite_database_path(database_url: str) -> Path:
    """Resolve a sqlite URL into a usable filesystem path."""

    parsed = urlparse(database_url)
    database_path = Path(parsed.path)
    if parsed.path.startswith("/") and len(parsed.path) > 2 and parsed.path[2] == ":":
        return Path(parsed.path.lstrip("/"))
    return database_path
