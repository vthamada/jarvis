"""Persistent repositories for the memory service."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, OperationalError, Row
from sqlite3 import connect as sqlite_connect
from urllib.parse import urlparse

from shared.contracts import (
    ContinuityCheckpointContract,
    MissionStateContract,
    SpecialistSharedMemoryContextContract,
)
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


@dataclass(frozen=True)
class SessionContinuitySnapshot:
    session_id: str
    continuity_brief: str
    continuity_mode: str
    anchor_mission_id: str | None
    anchor_goal: str | None
    related_mission_id: str | None
    related_goal: str | None
    updated_at: str


@dataclass(frozen=True)
class StoredContinuityCheckpoint:
    checkpoint_id: str
    session_id: str
    continuity_action: str
    checkpoint_status: str
    checkpoint_summary: str
    updated_at: str
    mission_id: str | None = None
    continuity_source: str | None = None
    target_mission_id: str | None = None
    target_goal: str | None = None
    origin_request_id: str | None = None
    replay_summary: str | None = None


@dataclass(frozen=True)
class StoredContinuityPauseResolution:
    session_id: str
    checkpoint_id: str
    resolution_status: str
    resolved_at: str
    resolved_by: str | None = None
    resolution_note: str | None = None


@dataclass(frozen=True)
class StoredSpecialistSharedMemory:
    session_id: str
    specialist_type: str
    sharing_mode: str
    continuity_mode: str
    shared_memory_brief: str
    write_policy: str
    updated_at: str
    consumer_mode: str = "baseline_shared_context"
    source_mission_id: str | None = None
    source_mission_goal: str | None = None
    mission_context_brief: str | None = None
    domain_context_brief: str | None = None
    continuity_context_brief: str | None = None
    related_mission_ids: list[str] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    memory_class_policies: dict[str, dict[str, object]] = field(default_factory=dict)
    semantic_focus: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    last_recommendation: str | None = None


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
    def upsert_session_continuity(
        self,
        snapshot: SessionContinuitySnapshot,
    ) -> None:
        """Persist the latest continuity snapshot for a session."""

    @abstractmethod
    def fetch_session_continuity(
        self,
        session_id: str,
    ) -> SessionContinuitySnapshot | None:
        """Load the latest continuity snapshot for a session."""

    @abstractmethod
    def upsert_continuity_checkpoint(
        self,
        checkpoint: StoredContinuityCheckpoint,
    ) -> None:
        """Persist the latest recoverable checkpoint for a session."""

    @abstractmethod
    def fetch_continuity_checkpoint(
        self,
        session_id: str,
    ) -> StoredContinuityCheckpoint | None:
        """Load the latest recoverable checkpoint for a session."""

    @abstractmethod
    def upsert_continuity_pause_resolution(
        self,
        resolution: StoredContinuityPauseResolution,
    ) -> None:
        """Persist the latest manual resolution attached to a continuity pause."""

    @abstractmethod
    def fetch_continuity_pause_resolution(
        self,
        session_id: str,
    ) -> StoredContinuityPauseResolution | None:
        """Load the latest manual resolution attached to a continuity pause."""

    @abstractmethod
    def upsert_specialist_shared_memory(
        self,
        snapshot: StoredSpecialistSharedMemory,
    ) -> None:
        """Persist the latest specialist-facing shared memory snapshot for a session."""

    @abstractmethod
    def fetch_specialist_shared_memory(
        self,
        *,
        session_id: str,
        specialist_type: str,
    ) -> SpecialistSharedMemoryContextContract | None:
        """Load the latest specialist-facing shared memory snapshot for a session."""

    @abstractmethod
    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        """Persist the latest known mission state."""

    @abstractmethod
    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Load a persisted mission state, if any."""

    @abstractmethod
    def list_related_mission_states(
        self,
        *,
        session_id: str,
        exclude_mission_id: str,
        limit: int,
    ) -> list[MissionStateContract]:
        """Load other mission states observed in the same session."""


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
                    last_recommendation, semantic_brief, semantic_focus,
                    identity_continuity_brief, open_loops, last_decision_frame, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(mission_id) DO UPDATE SET
                    mission_goal = excluded.mission_goal,
                    mission_status = excluded.mission_status,
                    checkpoints = excluded.checkpoints,
                    active_tasks = excluded.active_tasks,
                    related_memories = excluded.related_memories,
                    related_artifacts = excluded.related_artifacts,
                    recent_plan_steps = excluded.recent_plan_steps,
                    last_recommendation = excluded.last_recommendation,
                    semantic_brief = excluded.semantic_brief,
                    semantic_focus = excluded.semantic_focus,
                    identity_continuity_brief = excluded.identity_continuity_brief,
                    open_loops = excluded.open_loops,
                    last_decision_frame = excluded.last_decision_frame,
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
                    mission_state.semantic_brief,
                    dumps(mission_state.semantic_focus),
                    mission_state.identity_continuity_brief,
                    dumps(mission_state.open_loops),
                    mission_state.last_decision_frame,
                    mission_state.updated_at,
                ),
            )
            connection.commit()

    def upsert_session_continuity(self, snapshot: SessionContinuitySnapshot) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO session_continuity (
                    session_id, continuity_brief, continuity_mode, anchor_mission_id,
                    anchor_goal, related_mission_id, related_goal, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    continuity_brief = excluded.continuity_brief,
                    continuity_mode = excluded.continuity_mode,
                    anchor_mission_id = excluded.anchor_mission_id,
                    anchor_goal = excluded.anchor_goal,
                    related_mission_id = excluded.related_mission_id,
                    related_goal = excluded.related_goal,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.continuity_brief,
                    snapshot.continuity_mode,
                    snapshot.anchor_mission_id,
                    snapshot.anchor_goal,
                    snapshot.related_mission_id,
                    snapshot.related_goal,
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_session_continuity(self, session_id: str) -> SessionContinuitySnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, continuity_brief, continuity_mode, anchor_mission_id,
                       anchor_goal, related_mission_id, related_goal, updated_at
                FROM session_continuity
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return SessionContinuitySnapshot(
            session_id=str(row["session_id"]),
            continuity_brief=str(row["continuity_brief"]),
            continuity_mode=str(row["continuity_mode"]),
            anchor_mission_id=row["anchor_mission_id"],
            anchor_goal=row["anchor_goal"],
            related_mission_id=row["related_mission_id"],
            related_goal=row["related_goal"],
            updated_at=str(row["updated_at"]),
        )

    def upsert_continuity_checkpoint(
        self,
        checkpoint: StoredContinuityCheckpoint,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO continuity_checkpoints (
                    session_id, checkpoint_id, continuity_action, checkpoint_status,
                    checkpoint_summary, mission_id, continuity_source, target_mission_id,
                    target_goal, origin_request_id, replay_summary, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    checkpoint_id = excluded.checkpoint_id,
                    continuity_action = excluded.continuity_action,
                    checkpoint_status = excluded.checkpoint_status,
                    checkpoint_summary = excluded.checkpoint_summary,
                    mission_id = excluded.mission_id,
                    continuity_source = excluded.continuity_source,
                    target_mission_id = excluded.target_mission_id,
                    target_goal = excluded.target_goal,
                    origin_request_id = excluded.origin_request_id,
                    replay_summary = excluded.replay_summary,
                    updated_at = excluded.updated_at
                """,
                (
                    checkpoint.session_id,
                    checkpoint.checkpoint_id,
                    checkpoint.continuity_action,
                    checkpoint.checkpoint_status,
                    checkpoint.checkpoint_summary,
                    checkpoint.mission_id,
                    checkpoint.continuity_source,
                    checkpoint.target_mission_id,
                    checkpoint.target_goal,
                    checkpoint.origin_request_id,
                    checkpoint.replay_summary,
                    checkpoint.updated_at,
                ),
            )
            connection.commit()

    def fetch_continuity_checkpoint(
        self,
        session_id: str,
    ) -> StoredContinuityCheckpoint | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, checkpoint_id, continuity_action, checkpoint_status,
                       checkpoint_summary, mission_id, continuity_source, target_mission_id,
                       target_goal, origin_request_id, replay_summary, updated_at
                FROM continuity_checkpoints
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredContinuityCheckpoint(
            checkpoint_id=str(row["checkpoint_id"]),
            session_id=str(row["session_id"]),
            continuity_action=str(row["continuity_action"]),
            checkpoint_status=str(row["checkpoint_status"]),
            checkpoint_summary=str(row["checkpoint_summary"]),
            mission_id=row["mission_id"],
            continuity_source=row["continuity_source"],
            target_mission_id=row["target_mission_id"],
            target_goal=row["target_goal"],
            origin_request_id=row["origin_request_id"],
            replay_summary=row["replay_summary"],
            updated_at=str(row["updated_at"]),
        )

    def upsert_continuity_pause_resolution(
        self,
        resolution: StoredContinuityPauseResolution,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO continuity_pause_resolutions (
                    session_id, checkpoint_id, resolution_status, resolved_by,
                    resolution_note, resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    checkpoint_id = excluded.checkpoint_id,
                    resolution_status = excluded.resolution_status,
                    resolved_by = excluded.resolved_by,
                    resolution_note = excluded.resolution_note,
                    resolved_at = excluded.resolved_at
                """,
                (
                    resolution.session_id,
                    resolution.checkpoint_id,
                    resolution.resolution_status,
                    resolution.resolved_by,
                    resolution.resolution_note,
                    resolution.resolved_at,
                ),
            )
            connection.commit()

    def fetch_continuity_pause_resolution(
        self,
        session_id: str,
    ) -> StoredContinuityPauseResolution | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, checkpoint_id, resolution_status, resolved_by,
                       resolution_note, resolved_at
                FROM continuity_pause_resolutions
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return StoredContinuityPauseResolution(
            session_id=str(row["session_id"]),
            checkpoint_id=str(row["checkpoint_id"]),
            resolution_status=str(row["resolution_status"]),
            resolved_by=row["resolved_by"],
            resolution_note=row["resolution_note"],
            resolved_at=str(row["resolved_at"]),
        )

    def upsert_specialist_shared_memory(
        self,
        snapshot: StoredSpecialistSharedMemory,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO specialist_shared_memory (
                    session_id, specialist_type, sharing_mode, continuity_mode,
                    shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                    source_mission_goal, mission_context_brief, domain_context_brief,
                    continuity_context_brief, related_mission_ids, memory_refs,
                    memory_class_policies, semantic_focus, open_loops,
                    last_recommendation, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id, specialist_type) DO UPDATE SET
                    sharing_mode = excluded.sharing_mode,
                    continuity_mode = excluded.continuity_mode,
                    shared_memory_brief = excluded.shared_memory_brief,
                    write_policy = excluded.write_policy,
                    consumer_mode = excluded.consumer_mode,
                    source_mission_id = excluded.source_mission_id,
                    source_mission_goal = excluded.source_mission_goal,
                    mission_context_brief = excluded.mission_context_brief,
                    domain_context_brief = excluded.domain_context_brief,
                    continuity_context_brief = excluded.continuity_context_brief,
                    related_mission_ids = excluded.related_mission_ids,
                    memory_refs = excluded.memory_refs,
                    memory_class_policies = excluded.memory_class_policies,
                    semantic_focus = excluded.semantic_focus,
                    open_loops = excluded.open_loops,
                    last_recommendation = excluded.last_recommendation,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.specialist_type,
                    snapshot.sharing_mode,
                    snapshot.continuity_mode,
                    snapshot.shared_memory_brief,
                    snapshot.write_policy,
                    snapshot.consumer_mode,
                    snapshot.source_mission_id,
                    snapshot.source_mission_goal,
                    snapshot.mission_context_brief,
                    snapshot.domain_context_brief,
                    snapshot.continuity_context_brief,
                    dumps(snapshot.related_mission_ids),
                    dumps(snapshot.memory_refs),
                    dumps(snapshot.memory_class_policies),
                    dumps(snapshot.semantic_focus),
                    dumps(snapshot.open_loops),
                    snapshot.last_recommendation,
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_specialist_shared_memory(
        self,
        *,
        session_id: str,
        specialist_type: str,
    ) -> SpecialistSharedMemoryContextContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, specialist_type, sharing_mode, continuity_mode,
                       shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                       source_mission_goal, mission_context_brief, domain_context_brief,
                       continuity_context_brief, related_mission_ids, memory_refs,
                       memory_class_policies, semantic_focus, open_loops,
                       last_recommendation
                FROM specialist_shared_memory
                WHERE session_id = ?
                  AND specialist_type = ?
                """,
                (session_id, specialist_type),
            ).fetchone()
        return None if row is None else self._row_to_specialist_shared_memory(row)

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, semantic_brief, semantic_focus,
                       identity_continuity_brief, open_loops, last_decision_frame, updated_at
                FROM mission_states
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        return None if row is None else self._row_to_mission_state(row)

    def list_related_mission_states(
        self,
        *,
        session_id: str,
        exclude_mission_id: str,
        limit: int,
    ) -> list[MissionStateContract]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT mission_id
                FROM (
                    SELECT mission_id, MAX(timestamp) AS last_seen
                    FROM interaction_turns
                    WHERE session_id = ?
                      AND mission_id IS NOT NULL
                      AND mission_id <> ?
                    GROUP BY mission_id
                )
                ORDER BY last_seen DESC, mission_id ASC
                LIMIT ?
                """,
                (session_id, exclude_mission_id, limit),
            ).fetchall()
        states: list[MissionStateContract] = []
        for row in rows:
            mission_state = self.fetch_mission_state(str(row["mission_id"]))
            if mission_state is not None:
                states.append(mission_state)
        return states

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

                CREATE TABLE IF NOT EXISTS session_continuity (
                    session_id TEXT PRIMARY KEY,
                    continuity_brief TEXT NOT NULL,
                    continuity_mode TEXT NOT NULL,
                    anchor_mission_id TEXT,
                    anchor_goal TEXT,
                    related_mission_id TEXT,
                    related_goal TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS continuity_checkpoints (
                    session_id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    continuity_action TEXT NOT NULL,
                    checkpoint_status TEXT NOT NULL,
                    checkpoint_summary TEXT NOT NULL,
                    mission_id TEXT,
                    continuity_source TEXT,
                    target_mission_id TEXT,
                    target_goal TEXT,
                    origin_request_id TEXT,
                    replay_summary TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS continuity_pause_resolutions (
                    session_id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    resolution_status TEXT NOT NULL,
                    resolved_by TEXT,
                    resolution_note TEXT,
                    resolved_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS continuity_pause_resolutions (
                    session_id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    resolution_status TEXT NOT NULL,
                    resolved_by TEXT,
                    resolution_note TEXT,
                    resolved_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS specialist_shared_memory (
                    session_id TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    sharing_mode TEXT NOT NULL,
                    continuity_mode TEXT NOT NULL,
                    shared_memory_brief TEXT NOT NULL,
                    write_policy TEXT NOT NULL,
                    consumer_mode TEXT NOT NULL DEFAULT 'baseline_shared_context',
                    source_mission_id TEXT,
                    source_mission_goal TEXT,
                    mission_context_brief TEXT,
                    domain_context_brief TEXT,
                    continuity_context_brief TEXT,
                    related_mission_ids TEXT NOT NULL DEFAULT '[]',
                    memory_refs TEXT NOT NULL DEFAULT '[]',
                    memory_class_policies TEXT NOT NULL DEFAULT '{}',
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, specialist_type)
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
                    semantic_brief TEXT,
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    identity_continuity_brief TEXT,
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_decision_frame TEXT,
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
            self._ensure_column(connection, "mission_states", "semantic_brief", "TEXT")
            self._ensure_column(
                connection, "mission_states", "semantic_focus", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(connection, "mission_states", "identity_continuity_brief", "TEXT")
            self._ensure_column(
                connection, "mission_states", "open_loops", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(connection, "mission_states", "last_decision_frame", "TEXT")
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "memory_class_policies",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "consumer_mode",
                "TEXT NOT NULL DEFAULT 'baseline_shared_context'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "mission_context_brief",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "domain_context_brief",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "continuity_context_brief",
                "TEXT",
            )
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
            semantic_brief=row["semantic_brief"],
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            identity_continuity_brief=row["identity_continuity_brief"],
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_decision_frame=row["last_decision_frame"],
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_specialist_shared_memory(row: Row) -> SpecialistSharedMemoryContextContract:
        return SpecialistSharedMemoryContextContract(
            specialist_type=str(row["specialist_type"]),
            sharing_mode=str(row["sharing_mode"]),
            continuity_mode=str(row["continuity_mode"]),
            shared_memory_brief=str(row["shared_memory_brief"]),
            write_policy=str(row["write_policy"]),
            consumer_mode=str(row["consumer_mode"] or "baseline_shared_context"),
            source_mission_id=row["source_mission_id"],
            source_mission_goal=row["source_mission_goal"],
            mission_context_brief=row["mission_context_brief"],
            domain_context_brief=row["domain_context_brief"],
            continuity_context_brief=row["continuity_context_brief"],
            related_mission_ids=list(loads(row["related_mission_ids"] or "[]")),
            memory_refs=list(loads(row["memory_refs"] or "[]")),
            memory_class_policies=dict(loads(row["memory_class_policies"] or "{}")),
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_recommendation=row["last_recommendation"],
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
                    last_recommendation, semantic_brief, semantic_focus,
                    identity_continuity_brief, open_loops, last_decision_frame, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (mission_id) DO UPDATE SET
                    mission_goal = EXCLUDED.mission_goal,
                    mission_status = EXCLUDED.mission_status,
                    checkpoints = EXCLUDED.checkpoints,
                    active_tasks = EXCLUDED.active_tasks,
                    related_memories = EXCLUDED.related_memories,
                    related_artifacts = EXCLUDED.related_artifacts,
                    recent_plan_steps = EXCLUDED.recent_plan_steps,
                    last_recommendation = EXCLUDED.last_recommendation,
                    semantic_brief = EXCLUDED.semantic_brief,
                    semantic_focus = EXCLUDED.semantic_focus,
                    identity_continuity_brief = EXCLUDED.identity_continuity_brief,
                    open_loops = EXCLUDED.open_loops,
                    last_decision_frame = EXCLUDED.last_decision_frame,
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
                    mission_state.semantic_brief,
                    dumps(mission_state.semantic_focus),
                    mission_state.identity_continuity_brief,
                    dumps(mission_state.open_loops),
                    mission_state.last_decision_frame,
                    mission_state.updated_at,
                ),
            )
            connection.commit()

    def upsert_session_continuity(self, snapshot: SessionContinuitySnapshot) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO session_continuity (
                    session_id, continuity_brief, continuity_mode, anchor_mission_id,
                    anchor_goal, related_mission_id, related_goal, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    continuity_brief = EXCLUDED.continuity_brief,
                    continuity_mode = EXCLUDED.continuity_mode,
                    anchor_mission_id = EXCLUDED.anchor_mission_id,
                    anchor_goal = EXCLUDED.anchor_goal,
                    related_mission_id = EXCLUDED.related_mission_id,
                    related_goal = EXCLUDED.related_goal,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.continuity_brief,
                    snapshot.continuity_mode,
                    snapshot.anchor_mission_id,
                    snapshot.anchor_goal,
                    snapshot.related_mission_id,
                    snapshot.related_goal,
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def upsert_continuity_checkpoint(
        self,
        checkpoint: StoredContinuityCheckpoint,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO continuity_checkpoints (
                    session_id, checkpoint_id, continuity_action, checkpoint_status,
                    checkpoint_summary, mission_id, continuity_source, target_mission_id,
                    target_goal, origin_request_id, replay_summary, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    checkpoint_id = EXCLUDED.checkpoint_id,
                    continuity_action = EXCLUDED.continuity_action,
                    checkpoint_status = EXCLUDED.checkpoint_status,
                    checkpoint_summary = EXCLUDED.checkpoint_summary,
                    mission_id = EXCLUDED.mission_id,
                    continuity_source = EXCLUDED.continuity_source,
                    target_mission_id = EXCLUDED.target_mission_id,
                    target_goal = EXCLUDED.target_goal,
                    origin_request_id = EXCLUDED.origin_request_id,
                    replay_summary = EXCLUDED.replay_summary,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    checkpoint.session_id,
                    checkpoint.checkpoint_id,
                    checkpoint.continuity_action,
                    checkpoint.checkpoint_status,
                    checkpoint.checkpoint_summary,
                    checkpoint.mission_id,
                    checkpoint.continuity_source,
                    checkpoint.target_mission_id,
                    checkpoint.target_goal,
                    checkpoint.origin_request_id,
                    checkpoint.replay_summary,
                    checkpoint.updated_at,
                ),
            )
            connection.commit()

    def fetch_session_continuity(self, session_id: str) -> SessionContinuitySnapshot | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, continuity_brief, continuity_mode, anchor_mission_id,
                       anchor_goal, related_mission_id, related_goal, updated_at
                FROM session_continuity
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return SessionContinuitySnapshot(
            session_id=row["session_id"],
            continuity_brief=row["continuity_brief"],
            continuity_mode=row["continuity_mode"],
            anchor_mission_id=row["anchor_mission_id"],
            anchor_goal=row["anchor_goal"],
            related_mission_id=row["related_mission_id"],
            related_goal=row["related_goal"],
            updated_at=row["updated_at"],
        )

    def fetch_continuity_checkpoint(
        self,
        session_id: str,
    ) -> StoredContinuityCheckpoint | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, checkpoint_id, continuity_action, checkpoint_status,
                       checkpoint_summary, mission_id, continuity_source, target_mission_id,
                       target_goal, origin_request_id, replay_summary, updated_at
                FROM continuity_checkpoints
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return StoredContinuityCheckpoint(
            checkpoint_id=row["checkpoint_id"],
            session_id=row["session_id"],
            continuity_action=row["continuity_action"],
            checkpoint_status=row["checkpoint_status"],
            checkpoint_summary=row["checkpoint_summary"],
            mission_id=row["mission_id"],
            continuity_source=row["continuity_source"],
            target_mission_id=row["target_mission_id"],
            target_goal=row["target_goal"],
            origin_request_id=row["origin_request_id"],
            replay_summary=row["replay_summary"],
            updated_at=row["updated_at"],
        )

    def upsert_continuity_pause_resolution(
        self,
        resolution: StoredContinuityPauseResolution,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO continuity_pause_resolutions (
                    session_id, checkpoint_id, resolution_status, resolved_by,
                    resolution_note, resolved_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    checkpoint_id = EXCLUDED.checkpoint_id,
                    resolution_status = EXCLUDED.resolution_status,
                    resolved_by = EXCLUDED.resolved_by,
                    resolution_note = EXCLUDED.resolution_note,
                    resolved_at = EXCLUDED.resolved_at
                """,
                (
                    resolution.session_id,
                    resolution.checkpoint_id,
                    resolution.resolution_status,
                    resolution.resolved_by,
                    resolution.resolution_note,
                    resolution.resolved_at,
                ),
            )
            connection.commit()

    def fetch_continuity_pause_resolution(
        self,
        session_id: str,
    ) -> StoredContinuityPauseResolution | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, checkpoint_id, resolution_status, resolved_by,
                       resolution_note, resolved_at
                FROM continuity_pause_resolutions
                WHERE session_id = %s
                """,
                (session_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return StoredContinuityPauseResolution(
            session_id=row["session_id"],
            checkpoint_id=row["checkpoint_id"],
            resolution_status=row["resolution_status"],
            resolved_by=row["resolved_by"],
            resolution_note=row["resolution_note"],
            resolved_at=row["resolved_at"],
        )

    def upsert_specialist_shared_memory(
        self,
        snapshot: StoredSpecialistSharedMemory,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO specialist_shared_memory (
                    session_id, specialist_type, sharing_mode, continuity_mode,
                    shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                    source_mission_goal, mission_context_brief, domain_context_brief,
                    continuity_context_brief, related_mission_ids, memory_refs,
                    memory_class_policies, semantic_focus, open_loops,
                    last_recommendation, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, specialist_type) DO UPDATE SET
                    sharing_mode = EXCLUDED.sharing_mode,
                    continuity_mode = EXCLUDED.continuity_mode,
                    shared_memory_brief = EXCLUDED.shared_memory_brief,
                    write_policy = EXCLUDED.write_policy,
                    consumer_mode = EXCLUDED.consumer_mode,
                    source_mission_id = EXCLUDED.source_mission_id,
                    source_mission_goal = EXCLUDED.source_mission_goal,
                    mission_context_brief = EXCLUDED.mission_context_brief,
                    domain_context_brief = EXCLUDED.domain_context_brief,
                    continuity_context_brief = EXCLUDED.continuity_context_brief,
                    related_mission_ids = EXCLUDED.related_mission_ids,
                    memory_refs = EXCLUDED.memory_refs,
                    memory_class_policies = EXCLUDED.memory_class_policies,
                    semantic_focus = EXCLUDED.semantic_focus,
                    open_loops = EXCLUDED.open_loops,
                    last_recommendation = EXCLUDED.last_recommendation,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.specialist_type,
                    snapshot.sharing_mode,
                    snapshot.continuity_mode,
                    snapshot.shared_memory_brief,
                    snapshot.write_policy,
                    snapshot.consumer_mode,
                    snapshot.source_mission_id,
                    snapshot.source_mission_goal,
                    snapshot.mission_context_brief,
                    snapshot.domain_context_brief,
                    snapshot.continuity_context_brief,
                    dumps(snapshot.related_mission_ids),
                    dumps(snapshot.memory_refs),
                    dumps(snapshot.memory_class_policies),
                    dumps(snapshot.semantic_focus),
                    dumps(snapshot.open_loops),
                    snapshot.last_recommendation,
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_specialist_shared_memory(
        self,
        *,
        session_id: str,
        specialist_type: str,
    ) -> SpecialistSharedMemoryContextContract | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, specialist_type, sharing_mode, continuity_mode,
                       shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                       source_mission_goal, mission_context_brief, domain_context_brief,
                       continuity_context_brief, related_mission_ids, memory_refs,
                       memory_class_policies, semantic_focus, open_loops,
                       last_recommendation
                FROM specialist_shared_memory
                WHERE session_id = %s
                  AND specialist_type = %s
                """,
                (session_id, specialist_type),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return SpecialistSharedMemoryContextContract(
            specialist_type=row["specialist_type"],
            sharing_mode=row["sharing_mode"],
            continuity_mode=row["continuity_mode"],
            shared_memory_brief=row["shared_memory_brief"],
            write_policy=row["write_policy"],
            consumer_mode=row["consumer_mode"] or "baseline_shared_context",
            source_mission_id=row["source_mission_id"],
            source_mission_goal=row["source_mission_goal"],
            mission_context_brief=row["mission_context_brief"],
            domain_context_brief=row["domain_context_brief"],
            continuity_context_brief=row["continuity_context_brief"],
            related_mission_ids=list(loads(row["related_mission_ids"] or "[]")),
            memory_refs=list(loads(row["memory_refs"] or "[]")),
            memory_class_policies=dict(loads(row["memory_class_policies"] or "{}")),
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_recommendation=row["last_recommendation"],
        )

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, semantic_brief, semantic_focus,
                       identity_continuity_brief, open_loops, last_decision_frame, updated_at
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
            semantic_brief=row["semantic_brief"],
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            identity_continuity_brief=row["identity_continuity_brief"],
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_decision_frame=row["last_decision_frame"],
            updated_at=row["updated_at"],
        )

    def list_related_mission_states(
        self,
        *,
        session_id: str,
        exclude_mission_id: str,
        limit: int,
    ) -> list[MissionStateContract]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT mission_id
                FROM (
                    SELECT mission_id, MAX(timestamp) AS last_seen
                    FROM interaction_turns
                    WHERE session_id = %s
                      AND mission_id IS NOT NULL
                      AND mission_id <> %s
                    GROUP BY mission_id
                ) ranked
                ORDER BY last_seen DESC, mission_id ASC
                LIMIT %s
                """,
                (session_id, exclude_mission_id, limit),
            )
            rows = cursor.fetchall()
        states: list[MissionStateContract] = []
        for row in rows:
            mission_state = self.fetch_mission_state(str(row["mission_id"]))
            if mission_state is not None:
                states.append(mission_state)
        return states

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
                CREATE TABLE IF NOT EXISTS session_continuity (
                    session_id TEXT PRIMARY KEY,
                    continuity_brief TEXT NOT NULL,
                    continuity_mode TEXT NOT NULL,
                    anchor_mission_id TEXT,
                    anchor_goal TEXT,
                    related_mission_id TEXT,
                    related_goal TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS continuity_checkpoints (
                    session_id TEXT PRIMARY KEY,
                    checkpoint_id TEXT NOT NULL,
                    continuity_action TEXT NOT NULL,
                    checkpoint_status TEXT NOT NULL,
                    checkpoint_summary TEXT NOT NULL,
                    mission_id TEXT,
                    continuity_source TEXT,
                    target_mission_id TEXT,
                    target_goal TEXT,
                    origin_request_id TEXT,
                    replay_summary TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS specialist_shared_memory (
                    session_id TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    sharing_mode TEXT NOT NULL,
                    continuity_mode TEXT NOT NULL,
                    shared_memory_brief TEXT NOT NULL,
                    write_policy TEXT NOT NULL,
                    consumer_mode TEXT NOT NULL DEFAULT 'baseline_shared_context',
                    source_mission_id TEXT,
                    source_mission_goal TEXT,
                    mission_context_brief TEXT,
                    domain_context_brief TEXT,
                    continuity_context_brief TEXT,
                    related_mission_ids TEXT NOT NULL DEFAULT '[]',
                    memory_refs TEXT NOT NULL DEFAULT '[]',
                    memory_class_policies TEXT NOT NULL DEFAULT '{}',
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, specialist_type)
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
                    semantic_brief TEXT,
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    identity_continuity_brief TEXT,
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_decision_frame TEXT,
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
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "related_artifacts TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "recent_plan_steps TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS last_recommendation TEXT"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS semantic_brief TEXT"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "semantic_focus TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS identity_continuity_brief TEXT"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "open_loops TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS last_decision_frame TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "memory_class_policies TEXT NOT NULL DEFAULT '{}'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "consumer_mode TEXT NOT NULL DEFAULT 'baseline_shared_context'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "mission_context_brief TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "domain_context_brief TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "continuity_context_brief TEXT"
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


def continuity_checkpoint_to_contract(
    checkpoint: StoredContinuityCheckpoint,
) -> ContinuityCheckpointContract:
    return ContinuityCheckpointContract(
        checkpoint_id=checkpoint.checkpoint_id,
        session_id=checkpoint.session_id,
        mission_id=checkpoint.mission_id,
        continuity_action=checkpoint.continuity_action,
        continuity_source=checkpoint.continuity_source,
        target_mission_id=checkpoint.target_mission_id,
        target_goal=checkpoint.target_goal,
        checkpoint_status=checkpoint.checkpoint_status,
        checkpoint_summary=checkpoint.checkpoint_summary,
        origin_request_id=checkpoint.origin_request_id,
        replay_summary=checkpoint.replay_summary,
        updated_at=checkpoint.updated_at,
    )
