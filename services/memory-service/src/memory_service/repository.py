"""Persistent repositories for the memory service."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, OperationalError, Row
from sqlite3 import connect as sqlite_connect
from urllib.parse import urlparse

from shared.contracts import (
    ARTIFACT_LIFECYCLE_STATUSES,
    WORK_ITEM_PRIORITY_LEVELS,
    ArtifactLifecycleStateContract,
    ContinuityCheckpointContract,
    ExperienceRecordContract,
    MemoryLifecycleReviewDecisionContract,
    MissionStateContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    ReviewedLearningGuidanceContract,
    SkillCandidateContract,
    SpecialistSharedMemoryContextContract,
    UserScopeContextContract,
    WorkItemStateContract,
)
from shared.memory_registry import memory_lifecycle_support_signals
from shared.types import MissionId, MissionStatus, RiskLevel

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when postgres backend is unavailable.
    psycopg = None
    dict_row = None


def _serialize_work_items(work_items: list[WorkItemStateContract]) -> str:
    return dumps([asdict(item) for item in work_items])


def _deserialize_work_items(
    raw: str | None,
    *,
    mission_id: str,
) -> list[WorkItemStateContract]:
    values = loads(raw or "[]")
    if not isinstance(values, list):
        raise ValueError("mission work_items must be a JSON list")
    items: list[WorkItemStateContract] = []
    seen_refs: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("mission work_items entries must be JSON objects")
        item_ref = str(value["work_item_ref"])
        if item_ref in seen_refs:
            raise ValueError("mission work_items must not contain duplicate refs")
        seen_refs.add(item_ref)
        stored_mission_id = str(value.get("mission_id") or mission_id)
        if stored_mission_id != mission_id:
            raise ValueError("mission work item identity does not match its mission")
        priority_level = str(value.get("priority_level") or "p2")
        if priority_level not in WORK_ITEM_PRIORITY_LEVELS:
            raise ValueError("mission work item has invalid priority")
        items.append(
            WorkItemStateContract(
                work_item_ref=item_ref,
                work_item_status=str(value["work_item_status"]),
                mission_id=MissionId(stored_mission_id),
                transition=(
                    str(value["transition"])
                    if value.get("transition") is not None
                    else None
                ),
                next_action_ref=(
                    str(value["next_action_ref"])
                    if value.get("next_action_ref") is not None
                    else None
                ),
                dependency_refs=_work_item_string_list(
                    value.get("dependency_refs", []), "dependency_refs"
                ),
                priority_level=priority_level,
                blocking_state=str(value.get("blocking_state") or "ready"),
                blocker_refs=_work_item_string_list(
                    value.get("blocker_refs", []), "blocker_refs"
                ),
                checkpoint_refs=_work_item_string_list(
                    value.get("checkpoint_refs", []), "checkpoint_refs"
                ),
                memory_write_mode=str(
                    value.get("memory_write_mode") or "through_core_only"
                ),
            )
        )
    return items


def _work_item_string_list(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"mission work item {field_name} must be a JSON list")
    return [str(item) for item in value]


def _serialize_artifact_states(
    artifact_states: list[ArtifactLifecycleStateContract],
) -> str:
    return dumps([asdict(item) for item in artifact_states])


def _deserialize_artifact_states(
    raw: str | None,
    *,
    mission_id: str,
) -> list[ArtifactLifecycleStateContract]:
    values = loads(raw or "[]")
    if not isinstance(values, list):
        raise ValueError("mission artifact_states must be a JSON list")
    states: list[ArtifactLifecycleStateContract] = []
    seen_refs: set[str] = set()
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("mission artifact_states entries must be JSON objects")
        artifact_ref = str(value["artifact_ref"])
        if artifact_ref in seen_refs:
            raise ValueError("mission artifact_states must not contain duplicate refs")
        seen_refs.add(artifact_ref)
        stored_mission_id = str(value.get("mission_id") or mission_id)
        owner_mission_id = str(value.get("owner_mission_id") or mission_id)
        if stored_mission_id != mission_id or owner_mission_id != mission_id:
            raise ValueError("mission artifact identity does not match its mission")
        artifact_status = str(value["artifact_status"])
        if artifact_status not in ARTIFACT_LIFECYCLE_STATUSES:
            raise ValueError("mission artifact has invalid lifecycle status")
        raw_version = value.get("artifact_version")
        artifact_version = int(raw_version) if raw_version is not None else None
        if artifact_version is not None and artifact_version < 1:
            raise ValueError("mission artifact has invalid version")
        states.append(
            ArtifactLifecycleStateContract(
                artifact_ref=artifact_ref,
                artifact_status=artifact_status,
                mission_id=MissionId(stored_mission_id),
                transition=(
                    str(value["transition"])
                    if value.get("transition") is not None
                    else None
                ),
                artifact_version=artifact_version,
                owner_mission_id=MissionId(owner_mission_id),
                objective_ref=_optional_string(value.get("objective_ref")),
                work_item_ref=_optional_string(value.get("work_item_ref")),
                lineage_root_ref=_optional_string(value.get("lineage_root_ref")),
                supersedes_artifact_ref=_optional_string(
                    value.get("supersedes_artifact_ref")
                ),
                replacement_artifact_ref=_optional_string(
                    value.get("replacement_artifact_ref")
                ),
                rollback_plan_ref=_optional_string(value.get("rollback_plan_ref")),
                created_at=_optional_string(value.get("created_at")),
                updated_at=_optional_string(value.get("updated_at")),
                checkpoint_refs=_work_item_string_list(
                    value.get("checkpoint_refs", []), "artifact checkpoint_refs"
                ),
                memory_write_mode=str(
                    value.get("memory_write_mode") or "through_core_only"
                ),
            )
        )
    return states


def _optional_string(value: object) -> str | None:
    return str(value) if value is not None else None


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
class StoredUserScopeSnapshot:
    user_id: str
    context_status: str
    interaction_count: int
    updated_at: str
    user_context_brief: str | None = None
    recent_intents: list[str] = field(default_factory=list)
    recent_domain_focus: list[str] = field(default_factory=list)
    active_mission_ids: list[str] = field(default_factory=list)
    recent_session_ids: list[str] = field(default_factory=list)
    last_recommended_task_type: str | None = None
    continuity_preference: str | None = None
    memory_refs: list[str] = field(default_factory=list)


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
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None


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
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None


@dataclass(frozen=True)
class StoredContinuityPauseResolution:
    session_id: str
    checkpoint_id: str
    resolution_status: str
    resolved_at: str
    resolved_by: str | None = None
    resolution_note: str | None = None


@dataclass(frozen=True)
class StoredExperienceReflection:
    experience: ExperienceRecordContract
    reflection: PostTaskReflectionContract | None = None


@dataclass(frozen=True)
class StoredReviewedLearningGuidance:
    guidance: ReviewedLearningGuidanceContract


@dataclass(frozen=True)
class StoredMemoryLifecycleReviewDecision:
    decision: MemoryLifecycleReviewDecisionContract


@dataclass(frozen=True)
class StoredProceduralPlaybookCandidate:
    candidate: ProceduralPlaybookCandidateContract


@dataclass(frozen=True)
class StoredSkillCandidate:
    candidate: SkillCandidateContract


def _stored_skill_candidate_from_row(row: Row | dict[str, object]) -> StoredSkillCandidate:
    return StoredSkillCandidate(
        candidate=SkillCandidateContract(
            skill_candidate_id=str(row["skill_candidate_id"]),
            skill_id=str(row["skill_id"]),
            skill_name=str(row["skill_name"]),
            version=str(row["version"]),
            workflow_profile=str(row["workflow_profile"]),
            domain=str(row["domain"]),
            specialist_type=str(row["specialist_type"]),
            inputs=list(loads(str(row["inputs"] or "[]"))),
            outputs=list(loads(str(row["outputs"] or "[]"))),
            allowed_tools=list(loads(str(row["allowed_tools"] or "[]"))),
            bounded_instructions=list(
                loads(str(row["bounded_instructions"] or "[]"))
            ),
            risk_level=RiskLevel(str(row["risk_level"])),
            evidence_refs=list(loads(str(row["evidence_refs"] or "[]"))),
            source_pattern_refs=list(
                loads(str(row["source_pattern_refs"] or "[]"))
            ),
            failure_modes=list(loads(str(row["failure_modes"] or "[]"))),
            proposed_tests=list(loads(str(row["proposed_tests"] or "[]"))),
            rollback_plan_ref=str(row["rollback_plan_ref"]),
            registry_status=str(row["registry_status"]),
            review_status=str(row["review_status"]),
            activation_status=str(row["activation_status"]),
            blockers=list(loads(str(row["blockers"] or "[]"))),
            sandbox_required=bool(row["sandbox_required"]),
            human_review_required=bool(row["human_review_required"]),
            automatic_activation_allowed=bool(
                row["automatic_activation_allowed"]
            ),
            automatic_promotion_allowed=bool(
                row["automatic_promotion_allowed"]
            ),
            core_mutation_allowed=bool(row["core_mutation_allowed"]),
            memory_write_mode=str(row["memory_write_mode"]),
            timestamp=str(row["timestamp"]),
        )
    )


def _stored_memory_lifecycle_review_from_row(
    row: Row | dict[str, object],
) -> StoredMemoryLifecycleReviewDecision:
    return StoredMemoryLifecycleReviewDecision(
        decision=MemoryLifecycleReviewDecisionContract(
            review_decision_id=str(row["review_decision_id"]),
            candidate_id=str(row["candidate_id"]),
            maintenance_action=str(row["maintenance_action"]),
            decision_action=str(row["decision_action"]),
            review_status=str(row["review_status"]),
            operator_ref=str(row["operator_ref"]),
            evidence_refs=list(loads(str(row["evidence_refs"] or "[]"))),
            rollback_plan_ref=str(row["rollback_plan_ref"]),
            governance_assessment_id=str(row["governance_assessment_id"]),
            timestamp=str(row["timestamp"]),
            review_notes=list(loads(str(row["review_notes"] or "[]"))),
            execution_authorized=bool(row["execution_authorized"]),
            automatic_execution_allowed=bool(row["automatic_execution_allowed"]),
            core_mutation_allowed=bool(row["core_mutation_allowed"]),
        )
    )


@dataclass(frozen=True)
class StoredSpecialistSharedMemory:
    session_id: str
    specialist_type: str
    sharing_mode: str
    continuity_mode: str
    shared_memory_brief: str
    write_policy: str
    updated_at: str
    user_id: str | None = None
    consumer_mode: str = "baseline_shared_context"
    source_mission_id: str | None = None
    source_mission_goal: str | None = None
    mission_context_brief: str | None = None
    domain_context_brief: str | None = None
    continuity_context_brief: str | None = None
    consumer_profile: str | None = None
    consumer_objective: str | None = None
    expected_deliverables: list[str] = field(default_factory=list)
    telemetry_focus: list[str] = field(default_factory=list)
    related_mission_ids: list[str] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    memory_class_policies: dict[str, dict[str, object]] = field(default_factory=dict)
    consumed_memory_classes: list[str] = field(default_factory=list)
    memory_write_policies: dict[str, str] = field(default_factory=dict)
    semantic_focus: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    last_recommendation: str | None = None
    semantic_memory_lifecycle: str | None = None
    procedural_memory_lifecycle: str | None = None
    memory_lifecycle_status: str | None = None
    memory_review_status: str | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_refs: list[str] = field(default_factory=list)
    procedural_artifact_version: int | None = None
    procedural_artifact_summary: str | None = None
    domain_mission_link_reason: str | None = None
    recurrent_context_status: str = "not_applicable"
    recurrent_interaction_count: int = 0
    recurrent_context_brief: str | None = None
    recurrent_domain_focus: list[str] = field(default_factory=list)
    recurrent_memory_refs: list[str] = field(default_factory=list)
    recurrent_continuity_modes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryCorpusSummary:
    user_scope_records: int
    mission_state_records: int
    specialist_context_records: int
    semantic_records: int
    procedural_records: int
    retained_records: int
    promoted_records: int
    aging_records: int
    review_recommended_records: int
    fixed_records: int
    operational_records: int
    archivable_records: int
    consolidating_records: int


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
    def upsert_user_scope_snapshot(self, snapshot: StoredUserScopeSnapshot) -> None:
        """Persist the latest recoverable user-scope snapshot."""

    @abstractmethod
    def fetch_user_scope_snapshot(self, user_id: str) -> UserScopeContextContract | None:
        """Load the latest recoverable user-scope snapshot."""

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

    def record_experience_reflection(
        self,
        record: StoredExperienceReflection,
    ) -> None:
        """Persist a bounded experience/reflection pair."""
        raise NotImplementedError

    def record_experience(self, experience: ExperienceRecordContract) -> None:
        """Persist a bounded experience before reflection exists."""
        self.record_experience_reflection(StoredExperienceReflection(experience=experience))

    def list_experience_reflections(
        self,
        *,
        mission_id: str | None = None,
        workflow_profile: str | None = None,
        limit: int = 20,
    ) -> list[StoredExperienceReflection]:
        """Load recent bounded experience/reflection pairs."""
        raise NotImplementedError

    def fetch_experience_reflection(
        self,
        experience_id: str,
    ) -> StoredExperienceReflection | None:
        """Load one bounded experience/reflection pair by canonical id."""
        raise NotImplementedError

    def record_reviewed_learning_guidance(
        self,
        record: StoredReviewedLearningGuidance,
    ) -> None:
        """Persist human-reviewed learning guidance."""
        raise NotImplementedError

    def list_reviewed_learning_guidance(
        self,
        *,
        route: str | None = None,
        workflow_profile: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[StoredReviewedLearningGuidance]:
        """Load recent human-reviewed learning guidance."""
        raise NotImplementedError

    def record_memory_lifecycle_review_decision(
        self,
        record: StoredMemoryLifecycleReviewDecision,
    ) -> None:
        """Persist one human memory-maintenance review decision."""
        raise NotImplementedError

    def list_memory_lifecycle_review_decisions(
        self,
        *,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> list[StoredMemoryLifecycleReviewDecision]:
        """Load bounded human memory-maintenance review history."""
        raise NotImplementedError

    def record_procedural_playbook_candidate(
        self,
        record: StoredProceduralPlaybookCandidate,
    ) -> None:
        """Persist a bounded procedural playbook candidate."""
        raise NotImplementedError

    def list_procedural_playbook_candidates(
        self,
        *,
        workflow_profile: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredProceduralPlaybookCandidate]:
        """Load recent bounded procedural playbook candidates."""
        raise NotImplementedError

    def record_skill_candidate(self, record: StoredSkillCandidate) -> None:
        """Persist one inactive versioned skill candidate."""
        raise NotImplementedError

    def fetch_skill_candidate(
        self,
        skill_candidate_id: str,
    ) -> StoredSkillCandidate | None:
        """Load one skill candidate by registry identity."""
        raise NotImplementedError

    def list_skill_candidates(
        self,
        *,
        skill_id: str | None = None,
        version: str | None = None,
        domain: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredSkillCandidate]:
        """Load inactive skill candidates through bounded registry filters."""
        raise NotImplementedError

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
    def fetch_latest_specialist_shared_memory_for_user(
        self,
        *,
        user_id: str,
        specialist_type: str,
        exclude_session_id: str | None = None,
    ) -> SpecialistSharedMemoryContextContract | None:
        """Load the latest specialist-facing shared memory snapshot for a user."""

    @abstractmethod
    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        """Persist the latest known mission state."""

    @abstractmethod
    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Load a persisted mission state, if any."""

    @abstractmethod
    def list_mission_states(
        self,
        *,
        limit: int,
        include_closed: bool = False,
    ) -> list[MissionStateContract]:
        """Load canonical mission states ordered by most recent update."""

    @abstractmethod
    def list_related_mission_states(
        self,
        *,
        session_id: str,
        exclude_mission_id: str,
        limit: int,
    ) -> list[MissionStateContract]:
        """Load other mission states observed in the same session."""

    @abstractmethod
    def summarize_memory_corpus(self) -> MemoryCorpusSummary:
        """Return a compact system-level summary of the persisted memory corpus."""


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

    def upsert_user_scope_snapshot(self, snapshot: StoredUserScopeSnapshot) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_scope_snapshots (
                    user_id, context_status, interaction_count, user_context_brief,
                    recent_intents, recent_domain_focus, active_mission_ids, recent_session_ids,
                    last_recommended_task_type, continuity_preference, memory_refs, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    context_status = excluded.context_status,
                    interaction_count = excluded.interaction_count,
                    user_context_brief = excluded.user_context_brief,
                    recent_intents = excluded.recent_intents,
                    recent_domain_focus = excluded.recent_domain_focus,
                    active_mission_ids = excluded.active_mission_ids,
                    recent_session_ids = excluded.recent_session_ids,
                    last_recommended_task_type = excluded.last_recommended_task_type,
                    continuity_preference = excluded.continuity_preference,
                    memory_refs = excluded.memory_refs,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.user_id,
                    snapshot.context_status,
                    snapshot.interaction_count,
                    snapshot.user_context_brief,
                    dumps(snapshot.recent_intents),
                    dumps(snapshot.recent_domain_focus),
                    dumps(snapshot.active_mission_ids),
                    dumps(snapshot.recent_session_ids),
                    snapshot.last_recommended_task_type,
                    snapshot.continuity_preference,
                    dumps(snapshot.memory_refs),
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_user_scope_snapshot(self, user_id: str) -> UserScopeContextContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT user_id, context_status, interaction_count, user_context_brief,
                       recent_intents, recent_domain_focus, active_mission_ids, recent_session_ids,
                       last_recommended_task_type, continuity_preference, memory_refs
                FROM user_scope_snapshots
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_user_scope_snapshot(row)

    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO mission_states (
                    mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                    related_memories, related_artifacts, recent_plan_steps,
                    last_recommendation, semantic_brief, semantic_focus,
                    identity_continuity_brief, open_loops, last_decision_frame,
                    ecosystem_state_status, active_work_items, active_artifact_refs,
                    open_checkpoint_refs, surface_presence, ecosystem_state_summary,
                    project_ref, objective_ref, work_item_refs, work_items, checkpoint_refs,
                    artifact_refs, artifact_states, objective_status, next_action_ref,
                    linked_surface_ids, active_surface_id, last_surface_id,
                    surface_continuity_status, surface_identity_conflict_flags, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
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
                    ecosystem_state_status = excluded.ecosystem_state_status,
                    active_work_items = excluded.active_work_items,
                    active_artifact_refs = excluded.active_artifact_refs,
                    open_checkpoint_refs = excluded.open_checkpoint_refs,
                    surface_presence = excluded.surface_presence,
                    ecosystem_state_summary = excluded.ecosystem_state_summary,
                    project_ref = excluded.project_ref,
                    objective_ref = excluded.objective_ref,
                    work_item_refs = excluded.work_item_refs,
                    work_items = excluded.work_items,
                    checkpoint_refs = excluded.checkpoint_refs,
                    artifact_refs = excluded.artifact_refs,
                    artifact_states = excluded.artifact_states,
                    objective_status = excluded.objective_status,
                    next_action_ref = excluded.next_action_ref,
                    linked_surface_ids = excluded.linked_surface_ids,
                    active_surface_id = excluded.active_surface_id,
                    last_surface_id = excluded.last_surface_id,
                    surface_continuity_status = excluded.surface_continuity_status,
                    surface_identity_conflict_flags = excluded.surface_identity_conflict_flags,
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
                    mission_state.ecosystem_state_status,
                    dumps(mission_state.active_work_items),
                    dumps(mission_state.active_artifact_refs),
                    dumps(mission_state.open_checkpoint_refs),
                    dumps(mission_state.surface_presence),
                    mission_state.ecosystem_state_summary,
                    mission_state.project_ref,
                    mission_state.objective_ref,
                    dumps(mission_state.work_item_refs),
                    _serialize_work_items(mission_state.work_items),
                    dumps(mission_state.checkpoint_refs),
                    dumps(mission_state.artifact_refs),
                    _serialize_artifact_states(mission_state.artifact_states),
                    mission_state.objective_status,
                    mission_state.next_action_ref,
                    dumps(mission_state.linked_surface_ids),
                    mission_state.active_surface_id,
                    mission_state.last_surface_id,
                    mission_state.surface_continuity_status,
                    dumps(mission_state.surface_identity_conflict_flags),
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
                    anchor_goal, related_mission_id, related_goal, ecosystem_state_status,
                    active_work_items, active_artifact_refs, open_checkpoint_refs,
                    surface_presence, ecosystem_state_summary, linked_surface_ids,
                    project_ref, objective_ref, work_item_refs, checkpoint_refs,
                    artifact_refs, objective_status, next_action_ref,
                    active_surface_id, last_surface_id, surface_continuity_status,
                    surface_identity_conflict_flags, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?
                )
                ON CONFLICT(session_id) DO UPDATE SET
                    continuity_brief = excluded.continuity_brief,
                    continuity_mode = excluded.continuity_mode,
                    anchor_mission_id = excluded.anchor_mission_id,
                    anchor_goal = excluded.anchor_goal,
                    related_mission_id = excluded.related_mission_id,
                    related_goal = excluded.related_goal,
                    ecosystem_state_status = excluded.ecosystem_state_status,
                    active_work_items = excluded.active_work_items,
                    active_artifact_refs = excluded.active_artifact_refs,
                    open_checkpoint_refs = excluded.open_checkpoint_refs,
                    surface_presence = excluded.surface_presence,
                    ecosystem_state_summary = excluded.ecosystem_state_summary,
                    linked_surface_ids = excluded.linked_surface_ids,
                    project_ref = excluded.project_ref,
                    objective_ref = excluded.objective_ref,
                    work_item_refs = excluded.work_item_refs,
                    checkpoint_refs = excluded.checkpoint_refs,
                    artifact_refs = excluded.artifact_refs,
                    objective_status = excluded.objective_status,
                    next_action_ref = excluded.next_action_ref,
                    active_surface_id = excluded.active_surface_id,
                    last_surface_id = excluded.last_surface_id,
                    surface_continuity_status = excluded.surface_continuity_status,
                    surface_identity_conflict_flags = excluded.surface_identity_conflict_flags,
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
                    snapshot.ecosystem_state_status,
                    dumps(snapshot.active_work_items),
                    dumps(snapshot.active_artifact_refs),
                    dumps(snapshot.open_checkpoint_refs),
                    dumps(snapshot.surface_presence),
                    snapshot.ecosystem_state_summary,
                    dumps(snapshot.linked_surface_ids),
                    snapshot.project_ref,
                    snapshot.objective_ref,
                    dumps(snapshot.work_item_refs),
                    dumps(snapshot.checkpoint_refs),
                    dumps(snapshot.artifact_refs),
                    snapshot.objective_status,
                    snapshot.next_action_ref,
                    snapshot.active_surface_id,
                    snapshot.last_surface_id,
                    snapshot.surface_continuity_status,
                    dumps(snapshot.surface_identity_conflict_flags),
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_session_continuity(self, session_id: str) -> SessionContinuitySnapshot | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT session_id, continuity_brief, continuity_mode, anchor_mission_id,
                       anchor_goal, related_mission_id, related_goal, ecosystem_state_status,
                       active_work_items, active_artifact_refs, open_checkpoint_refs,
                       surface_presence, ecosystem_state_summary, linked_surface_ids,
                       project_ref, objective_ref, work_item_refs, checkpoint_refs,
                       artifact_refs, objective_status, next_action_ref,
                       active_surface_id, last_surface_id, surface_continuity_status,
                       surface_identity_conflict_flags, updated_at
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            project_ref=row["project_ref"],
            objective_ref=row["objective_ref"],
            work_item_refs=list(loads(row["work_item_refs"] or "[]")),
            checkpoint_refs=list(loads(row["checkpoint_refs"] or "[]")),
            artifact_refs=list(loads(row["artifact_refs"] or "[]")),
            objective_status=row["objective_status"],
            next_action_ref=row["next_action_ref"],
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
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
                    target_goal, origin_request_id, replay_summary, ecosystem_state_status,
                    active_work_items, active_artifact_refs, open_checkpoint_refs,
                    surface_presence, ecosystem_state_summary, linked_surface_ids,
                    project_ref, objective_ref, work_item_refs, checkpoint_refs,
                    artifact_refs, objective_status, next_action_ref,
                    active_surface_id, last_surface_id, surface_continuity_status,
                    surface_identity_conflict_flags, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
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
                    ecosystem_state_status = excluded.ecosystem_state_status,
                    active_work_items = excluded.active_work_items,
                    active_artifact_refs = excluded.active_artifact_refs,
                    open_checkpoint_refs = excluded.open_checkpoint_refs,
                    surface_presence = excluded.surface_presence,
                    ecosystem_state_summary = excluded.ecosystem_state_summary,
                    linked_surface_ids = excluded.linked_surface_ids,
                    project_ref = excluded.project_ref,
                    objective_ref = excluded.objective_ref,
                    work_item_refs = excluded.work_item_refs,
                    checkpoint_refs = excluded.checkpoint_refs,
                    artifact_refs = excluded.artifact_refs,
                    objective_status = excluded.objective_status,
                    next_action_ref = excluded.next_action_ref,
                    active_surface_id = excluded.active_surface_id,
                    last_surface_id = excluded.last_surface_id,
                    surface_continuity_status = excluded.surface_continuity_status,
                    surface_identity_conflict_flags = excluded.surface_identity_conflict_flags,
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
                    checkpoint.ecosystem_state_status,
                    dumps(checkpoint.active_work_items),
                    dumps(checkpoint.active_artifact_refs),
                    dumps(checkpoint.open_checkpoint_refs),
                    dumps(checkpoint.surface_presence),
                    checkpoint.ecosystem_state_summary,
                    dumps(checkpoint.linked_surface_ids),
                    checkpoint.project_ref,
                    checkpoint.objective_ref,
                    dumps(checkpoint.work_item_refs),
                    dumps(checkpoint.checkpoint_refs),
                    dumps(checkpoint.artifact_refs),
                    checkpoint.objective_status,
                    checkpoint.next_action_ref,
                    checkpoint.active_surface_id,
                    checkpoint.last_surface_id,
                    checkpoint.surface_continuity_status,
                    dumps(checkpoint.surface_identity_conflict_flags),
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
                       target_goal, origin_request_id, replay_summary, ecosystem_state_status,
                       active_work_items, active_artifact_refs, open_checkpoint_refs,
                       surface_presence, ecosystem_state_summary, linked_surface_ids,
                       project_ref, objective_ref, work_item_refs, checkpoint_refs,
                       artifact_refs, objective_status, next_action_ref,
                       active_surface_id, last_surface_id, surface_continuity_status,
                       surface_identity_conflict_flags, updated_at
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            project_ref=row["project_ref"],
            objective_ref=row["objective_ref"],
            work_item_refs=list(loads(row["work_item_refs"] or "[]")),
            checkpoint_refs=list(loads(row["checkpoint_refs"] or "[]")),
            artifact_refs=list(loads(row["artifact_refs"] or "[]")),
            objective_status=row["objective_status"],
            next_action_ref=row["next_action_ref"],
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
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

    def record_experience_reflection(
        self,
        record: StoredExperienceReflection,
    ) -> None:
        experience = record.experience
        reflection = record.reflection
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO experience_reflections (
                    experience_id, reflection_id, mission_id, objective_ref, surface_id,
                    workflow_profile, outcome_status, user_intent, route, primary_mind,
                    primary_domain_driver, specialist_used, plan_summary, execution_summary,
                    outcome, errors, tools_used, checkpoints, user_feedback,
                    evidence_refs, signal_refs, failure_modes, decision_refs,
                    learned_patterns, next_action_ref,
                    source_kind, reusable_memory_status, experience_human_review_required,
                    experience_automatic_promotion_allowed, experience_core_mutation_allowed,
                    reflection_status, learning_candidate, recommendation,
                    proposed_change_type, proposed_tests, blockers, rollback_plan_ref,
                    risk_hint, reflection_human_review_required,
                    reflection_automatic_promotion_allowed, reflection_core_mutation_allowed,
                    timestamp
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    experience.experience_id,
                    reflection.reflection_id if reflection else None,
                    str(experience.mission_id),
                    experience.objective_ref,
                    experience.surface_id,
                    experience.workflow_profile,
                    experience.outcome_status,
                    experience.user_intent,
                    experience.route,
                    experience.primary_mind,
                    experience.primary_domain_driver,
                    dumps(experience.specialist_used),
                    experience.plan_summary,
                    experience.execution_summary,
                    experience.outcome,
                    dumps(experience.errors),
                    dumps(experience.tools_used),
                    dumps(experience.checkpoints),
                    experience.user_feedback,
                    dumps(experience.evidence_refs),
                    dumps(experience.signal_refs),
                    dumps(experience.failure_modes),
                    dumps(experience.decision_refs),
                    dumps(experience.learned_patterns),
                    experience.next_action_ref,
                    experience.source_kind,
                    experience.reusable_memory_status,
                    int(experience.human_review_required),
                    int(experience.automatic_promotion_allowed),
                    int(experience.core_mutation_allowed),
                    reflection.reflection_status if reflection else None,
                    reflection.learning_candidate if reflection else None,
                    reflection.recommendation if reflection else None,
                    reflection.proposed_change_type if reflection else None,
                    dumps(reflection.proposed_tests if reflection else []),
                    dumps(reflection.blockers if reflection else []),
                    reflection.rollback_plan_ref if reflection else None,
                    reflection.risk_hint if reflection else None,
                    int(reflection.human_review_required) if reflection else None,
                    int(reflection.automatic_promotion_allowed) if reflection else None,
                    int(reflection.core_mutation_allowed) if reflection else None,
                    experience.timestamp,
                ),
            )
            connection.commit()

    def list_experience_reflections(
        self,
        *,
        mission_id: str | None = None,
        workflow_profile: str | None = None,
        limit: int = 20,
    ) -> list[StoredExperienceReflection]:
        clauses: list[str] = []
        params: list[object] = []
        if mission_id:
            clauses.append("mission_id = ?")
            params.append(mission_id)
        if workflow_profile:
            clauses.append("workflow_profile = ?")
            params.append(workflow_profile)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM experience_reflections
                {where}
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_experience_reflection(row) for row in rows]

    def fetch_experience_reflection(
        self,
        experience_id: str,
    ) -> StoredExperienceReflection | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM experience_reflections
                WHERE experience_id = ?
                """,
                (experience_id,),
            ).fetchone()
        return self._row_to_experience_reflection(row) if row is not None else None

    def record_reviewed_learning_guidance(
        self,
        record: StoredReviewedLearningGuidance,
    ) -> None:
        guidance = record.guidance
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO reviewed_learning_guidance (
                    guidance_id, source_review_decision_id, evolution_proposal_id,
                    review_status, route, workflow_profile, domain, guidance_summary,
                    allowed_usage, evidence_refs, rollback_plan_ref, timestamp,
                    expires_at, automatic_promotion_allowed, core_mutation_allowed
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    guidance.guidance_id,
                    guidance.source_review_decision_id,
                    str(guidance.evolution_proposal_id),
                    guidance.review_status,
                    guidance.route,
                    guidance.workflow_profile,
                    guidance.domain,
                    guidance.guidance_summary,
                    dumps(guidance.allowed_usage),
                    dumps(guidance.evidence_refs),
                    guidance.rollback_plan_ref,
                    guidance.timestamp,
                    guidance.expires_at,
                    int(guidance.automatic_promotion_allowed),
                    int(guidance.core_mutation_allowed),
                ),
            )
            connection.commit()

    def list_reviewed_learning_guidance(
        self,
        *,
        route: str | None = None,
        workflow_profile: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[StoredReviewedLearningGuidance]:
        clauses: list[str] = []
        params: list[object] = []
        if route:
            clauses.append("route = ?")
            params.append(route)
        if workflow_profile:
            clauses.append("workflow_profile = ?")
            params.append(workflow_profile)
        if domain:
            clauses.append("domain = ?")
            params.append(domain)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM reviewed_learning_guidance
                {where}
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_reviewed_learning_guidance(row) for row in rows]

    def record_memory_lifecycle_review_decision(
        self,
        record: StoredMemoryLifecycleReviewDecision,
    ) -> None:
        decision = record.decision
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_lifecycle_review_decisions (
                    review_decision_id, candidate_id, maintenance_action,
                    decision_action, review_status, operator_ref, evidence_refs,
                    rollback_plan_ref, governance_assessment_id, review_notes,
                    execution_authorized, automatic_execution_allowed,
                    core_mutation_allowed, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.review_decision_id,
                    decision.candidate_id,
                    decision.maintenance_action,
                    decision.decision_action,
                    decision.review_status,
                    decision.operator_ref,
                    dumps(decision.evidence_refs),
                    decision.rollback_plan_ref,
                    decision.governance_assessment_id,
                    dumps(decision.review_notes),
                    int(decision.execution_authorized),
                    int(decision.automatic_execution_allowed),
                    int(decision.core_mutation_allowed),
                    decision.timestamp,
                ),
            )
            connection.commit()

    def list_memory_lifecycle_review_decisions(
        self,
        *,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> list[StoredMemoryLifecycleReviewDecision]:
        where = "WHERE candidate_id = ?" if candidate_id else ""
        params: tuple[object, ...] = (
            (candidate_id, limit) if candidate_id else (limit,)
        )
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM memory_lifecycle_review_decisions
                {where}
                ORDER BY timestamp DESC, review_decision_id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [_stored_memory_lifecycle_review_from_row(row) for row in rows]

    def record_procedural_playbook_candidate(
        self,
        record: StoredProceduralPlaybookCandidate,
    ) -> None:
        candidate = record.candidate
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO procedural_playbook_candidates (
                    playbook_candidate_id, procedure_name, workflow_profile, route,
                    domain, bounded_steps, evidence_refs, source_artifact_refs,
                    source_reflection_refs, proposed_tests, rollback_plan_ref,
                    risk_hint, review_status, blockers, human_review_required,
                    automatic_promotion_allowed, core_mutation_allowed,
                    memory_write_mode, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.playbook_candidate_id,
                    candidate.procedure_name,
                    candidate.workflow_profile,
                    candidate.route,
                    candidate.domain,
                    dumps(candidate.bounded_steps),
                    dumps(candidate.evidence_refs),
                    dumps(candidate.source_artifact_refs),
                    dumps(candidate.source_reflection_refs),
                    dumps(candidate.proposed_tests),
                    candidate.rollback_plan_ref,
                    candidate.risk_hint,
                    candidate.review_status,
                    dumps(candidate.blockers),
                    int(candidate.human_review_required),
                    int(candidate.automatic_promotion_allowed),
                    int(candidate.core_mutation_allowed),
                    candidate.memory_write_mode,
                    candidate.timestamp,
                ),
            )
            connection.commit()

    def list_procedural_playbook_candidates(
        self,
        *,
        workflow_profile: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredProceduralPlaybookCandidate]:
        clauses: list[str] = []
        params: list[object] = []
        if workflow_profile:
            clauses.append("workflow_profile = ?")
            params.append(workflow_profile)
        if review_status:
            clauses.append("review_status = ?")
            params.append(review_status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM procedural_playbook_candidates
                {where}
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_procedural_playbook_candidate(row) for row in rows]

    def record_skill_candidate(self, record: StoredSkillCandidate) -> None:
        candidate = record.candidate
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO skill_candidates (
                    skill_candidate_id, skill_id, skill_name, version,
                    workflow_profile, domain, specialist_type, inputs, outputs,
                    allowed_tools, bounded_instructions, risk_level, evidence_refs,
                    source_pattern_refs, failure_modes, proposed_tests,
                    rollback_plan_ref, registry_status, review_status,
                    activation_status, blockers, sandbox_required,
                    human_review_required, automatic_activation_allowed,
                    automatic_promotion_allowed, core_mutation_allowed,
                    memory_write_mode, timestamp
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    candidate.skill_candidate_id,
                    candidate.skill_id,
                    candidate.skill_name,
                    candidate.version,
                    candidate.workflow_profile,
                    candidate.domain,
                    candidate.specialist_type,
                    dumps(candidate.inputs),
                    dumps(candidate.outputs),
                    dumps(candidate.allowed_tools),
                    dumps(candidate.bounded_instructions),
                    str(candidate.risk_level),
                    dumps(candidate.evidence_refs),
                    dumps(candidate.source_pattern_refs),
                    dumps(candidate.failure_modes),
                    dumps(candidate.proposed_tests),
                    candidate.rollback_plan_ref,
                    candidate.registry_status,
                    candidate.review_status,
                    candidate.activation_status,
                    dumps(candidate.blockers),
                    int(candidate.sandbox_required),
                    int(candidate.human_review_required),
                    int(candidate.automatic_activation_allowed),
                    int(candidate.automatic_promotion_allowed),
                    int(candidate.core_mutation_allowed),
                    candidate.memory_write_mode,
                    candidate.timestamp,
                ),
            )
            connection.commit()

    def fetch_skill_candidate(
        self,
        skill_candidate_id: str,
    ) -> StoredSkillCandidate | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM skill_candidates
                WHERE skill_candidate_id = ?
                """,
                (skill_candidate_id,),
            ).fetchone()
        return _stored_skill_candidate_from_row(row) if row is not None else None

    def list_skill_candidates(
        self,
        *,
        skill_id: str | None = None,
        version: str | None = None,
        domain: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredSkillCandidate]:
        clauses: list[str] = []
        params: list[object] = []
        for column, value in (
            ("skill_id", skill_id),
            ("version", version),
            ("domain", domain),
            ("review_status", review_status),
        ):
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM skill_candidates
                {where}
                ORDER BY timestamp DESC, skill_candidate_id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [_stored_skill_candidate_from_row(row) for row in rows]

    def upsert_specialist_shared_memory(
        self,
        snapshot: StoredSpecialistSharedMemory,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO specialist_shared_memory (
                    session_id, specialist_type, sharing_mode, continuity_mode,
                    shared_memory_brief, write_policy, user_id, consumer_mode,
                    source_mission_id, source_mission_goal, mission_context_brief,
                    domain_context_brief, continuity_context_brief, consumer_profile,
                    consumer_objective, expected_deliverables, telemetry_focus,
                    related_mission_ids, memory_refs, memory_class_policies,
                    consumed_memory_classes, memory_write_policies, semantic_focus,
                    open_loops, last_recommendation, semantic_memory_lifecycle,
                    procedural_memory_lifecycle, memory_lifecycle_status,
                    memory_review_status, procedural_artifact_status,
                    procedural_artifact_refs, procedural_artifact_version,
                    procedural_artifact_summary, domain_mission_link_reason,
                    recurrent_context_status, recurrent_interaction_count,
                    recurrent_context_brief, recurrent_domain_focus,
                    recurrent_memory_refs, recurrent_continuity_modes, updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(session_id, specialist_type) DO UPDATE SET
                    sharing_mode = excluded.sharing_mode,
                    continuity_mode = excluded.continuity_mode,
                    shared_memory_brief = excluded.shared_memory_brief,
                    write_policy = excluded.write_policy,
                    user_id = excluded.user_id,
                    consumer_mode = excluded.consumer_mode,
                    source_mission_id = excluded.source_mission_id,
                    source_mission_goal = excluded.source_mission_goal,
                    mission_context_brief = excluded.mission_context_brief,
                    domain_context_brief = excluded.domain_context_brief,
                    continuity_context_brief = excluded.continuity_context_brief,
                    consumer_profile = excluded.consumer_profile,
                    consumer_objective = excluded.consumer_objective,
                    expected_deliverables = excluded.expected_deliverables,
                    telemetry_focus = excluded.telemetry_focus,
                    related_mission_ids = excluded.related_mission_ids,
                    memory_refs = excluded.memory_refs,
                    memory_class_policies = excluded.memory_class_policies,
                    consumed_memory_classes = excluded.consumed_memory_classes,
                    memory_write_policies = excluded.memory_write_policies,
                    semantic_focus = excluded.semantic_focus,
                    open_loops = excluded.open_loops,
                    last_recommendation = excluded.last_recommendation,
                    semantic_memory_lifecycle = excluded.semantic_memory_lifecycle,
                    procedural_memory_lifecycle = excluded.procedural_memory_lifecycle,
                    memory_lifecycle_status = excluded.memory_lifecycle_status,
                    memory_review_status = excluded.memory_review_status,
                    procedural_artifact_status = excluded.procedural_artifact_status,
                    procedural_artifact_refs = excluded.procedural_artifact_refs,
                    procedural_artifact_version = excluded.procedural_artifact_version,
                    procedural_artifact_summary = excluded.procedural_artifact_summary,
                    domain_mission_link_reason = excluded.domain_mission_link_reason,
                    recurrent_context_status = excluded.recurrent_context_status,
                    recurrent_interaction_count = excluded.recurrent_interaction_count,
                    recurrent_context_brief = excluded.recurrent_context_brief,
                    recurrent_domain_focus = excluded.recurrent_domain_focus,
                    recurrent_memory_refs = excluded.recurrent_memory_refs,
                    recurrent_continuity_modes = excluded.recurrent_continuity_modes,
                    updated_at = excluded.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.specialist_type,
                    snapshot.sharing_mode,
                    snapshot.continuity_mode,
                    snapshot.shared_memory_brief,
                    snapshot.write_policy,
                    snapshot.user_id,
                    snapshot.consumer_mode,
                    snapshot.source_mission_id,
                    snapshot.source_mission_goal,
                    snapshot.mission_context_brief,
                    snapshot.domain_context_brief,
                    snapshot.continuity_context_brief,
                    snapshot.consumer_profile,
                    snapshot.consumer_objective,
                    dumps(snapshot.expected_deliverables),
                    dumps(snapshot.telemetry_focus),
                    dumps(snapshot.related_mission_ids),
                    dumps(snapshot.memory_refs),
                    dumps(snapshot.memory_class_policies),
                    dumps(snapshot.consumed_memory_classes),
                    dumps(snapshot.memory_write_policies),
                    dumps(snapshot.semantic_focus),
                    dumps(snapshot.open_loops),
                    snapshot.last_recommendation,
                    snapshot.semantic_memory_lifecycle,
                    snapshot.procedural_memory_lifecycle,
                    snapshot.memory_lifecycle_status,
                    snapshot.memory_review_status,
                    snapshot.procedural_artifact_status,
                    dumps(snapshot.procedural_artifact_refs),
                    snapshot.procedural_artifact_version,
                    snapshot.procedural_artifact_summary,
                    snapshot.domain_mission_link_reason,
                    snapshot.recurrent_context_status,
                    snapshot.recurrent_interaction_count,
                    snapshot.recurrent_context_brief,
                    dumps(snapshot.recurrent_domain_focus),
                    dumps(snapshot.recurrent_memory_refs),
                    dumps(snapshot.recurrent_continuity_modes),
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
                       continuity_context_brief, consumer_profile, consumer_objective,
                       expected_deliverables, telemetry_focus, related_mission_ids, memory_refs,
                       memory_class_policies, consumed_memory_classes, memory_write_policies,
                       semantic_focus, open_loops, last_recommendation,
                       semantic_memory_lifecycle, procedural_memory_lifecycle,
                       memory_lifecycle_status, memory_review_status,
                       procedural_artifact_status, procedural_artifact_refs,
                       procedural_artifact_version, procedural_artifact_summary,
                       domain_mission_link_reason, recurrent_context_status,
                       recurrent_interaction_count, recurrent_context_brief,
                       recurrent_domain_focus, recurrent_memory_refs,
                       recurrent_continuity_modes
                FROM specialist_shared_memory
                WHERE session_id = ?
                  AND specialist_type = ?
                """,
                (session_id, specialist_type),
            ).fetchone()
        return None if row is None else self._row_to_specialist_shared_memory(row)

    def fetch_latest_specialist_shared_memory_for_user(
        self,
        *,
        user_id: str,
        specialist_type: str,
        exclude_session_id: str | None = None,
    ) -> SpecialistSharedMemoryContextContract | None:
        query = """
                SELECT session_id, specialist_type, sharing_mode, continuity_mode,
                       shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                       source_mission_goal, mission_context_brief, domain_context_brief,
                       continuity_context_brief, consumer_profile, consumer_objective,
                       expected_deliverables, telemetry_focus, related_mission_ids, memory_refs,
                       memory_class_policies, consumed_memory_classes, memory_write_policies,
                       semantic_focus, open_loops, last_recommendation,
                       semantic_memory_lifecycle, procedural_memory_lifecycle,
                       memory_lifecycle_status, memory_review_status,
                       procedural_artifact_status, procedural_artifact_refs,
                       procedural_artifact_version, procedural_artifact_summary,
                       domain_mission_link_reason, recurrent_context_status,
                       recurrent_interaction_count, recurrent_context_brief,
                       recurrent_domain_focus, recurrent_memory_refs,
                       recurrent_continuity_modes
                FROM specialist_shared_memory
                WHERE user_id = ?
                  AND specialist_type = ?
        """
        params: list[str] = [user_id, specialist_type]
        if exclude_session_id is not None:
            query += "\n                  AND session_id <> ?"
            params.append(exclude_session_id)
        query += "\n                ORDER BY updated_at DESC\n                LIMIT 1"
        with self._connect() as connection:
            row = connection.execute(query, tuple(params)).fetchone()
        return None if row is None else self._row_to_specialist_shared_memory(row)

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, semantic_brief, semantic_focus,
                       identity_continuity_brief, open_loops, last_decision_frame,
                       ecosystem_state_status, active_work_items, active_artifact_refs,
                       open_checkpoint_refs, surface_presence, ecosystem_state_summary,
                       project_ref, objective_ref, work_item_refs, work_items, checkpoint_refs,
                       artifact_refs, artifact_states, objective_status, next_action_ref,
                       linked_surface_ids, active_surface_id, last_surface_id,
                       surface_continuity_status, surface_identity_conflict_flags, updated_at
                FROM mission_states
                WHERE mission_id = ?
                """,
                (mission_id,),
            ).fetchone()
        return None if row is None else self._row_to_mission_state(row)

    def list_mission_states(
        self,
        *,
        limit: int,
        include_closed: bool = False,
    ) -> list[MissionStateContract]:
        clauses = ""
        params: list[object] = []
        if not include_closed:
            clauses = "WHERE mission_status NOT IN (?, ?)"
            params.extend(
                [MissionStatus.COMPLETED.value, MissionStatus.CANCELED.value]
            )
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT mission_id
                FROM mission_states
                {clauses}
                ORDER BY updated_at DESC, mission_id ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        states = [
            self.fetch_mission_state(str(row["mission_id"])) for row in rows
        ]
        return [state for state in states if state is not None]

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

    def summarize_memory_corpus(self) -> MemoryCorpusSummary:
        with self._connect() as connection:
            user_scope_records = int(
                connection.execute(
                    "SELECT COUNT(*) AS total FROM user_scope_snapshots"
                ).fetchone()["total"]
            )
            mission_state_records = int(
                connection.execute(
                    "SELECT COUNT(*) AS total FROM mission_states"
                ).fetchone()["total"]
            )
            specialist_context_records = int(
                connection.execute(
                    "SELECT COUNT(*) AS total FROM specialist_shared_memory"
                ).fetchone()["total"]
            )
            semantic_records = int(
                connection.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM mission_states WHERE semantic_brief IS NOT NULL)
                        + (
                            SELECT COUNT(*)
                            FROM specialist_shared_memory
                            WHERE consumed_memory_classes LIKE '%"semantic"%'
                        ) AS total
                    """
                ).fetchone()["total"]
            )
            procedural_records = int(
                connection.execute(
                    """
                    SELECT
                        (
                            SELECT COUNT(*)
                            FROM mission_states
                            WHERE last_recommendation IS NOT NULL
                               OR recent_plan_steps <> '[]'
                        )
                        + (
                            SELECT COUNT(*)
                            FROM specialist_shared_memory
                            WHERE consumed_memory_classes LIKE '%"procedural"%'
                        ) AS total
                    """
                ).fetchone()["total"]
            )
            retained_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE memory_lifecycle_status = 'retained'
                    """
                ).fetchone()["total"]
            )
            promoted_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE memory_lifecycle_status = 'promoted'
                    """
                ).fetchone()["total"]
            )
            aging_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE semantic_memory_lifecycle = 'aging'
                       OR procedural_memory_lifecycle = 'aging'
                    """
                ).fetchone()["total"]
            )
            review_recommended_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE memory_review_status = 'review_recommended'
                    """
                ).fetchone()["total"]
            )
            fixed_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE semantic_memory_lifecycle = 'retained'
                       OR procedural_memory_lifecycle = 'retained'
                    """
                ).fetchone()["total"]
            )
            operational_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE semantic_memory_lifecycle IN ('promoted', 'consolidating')
                       OR procedural_memory_lifecycle IN ('promoted', 'consolidating')
                    """
                ).fetchone()["total"]
            )
            archivable_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE semantic_memory_lifecycle = 'aging'
                       OR procedural_memory_lifecycle = 'aging'
                    """
                ).fetchone()["total"]
            )
            consolidating_records = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS total
                    FROM specialist_shared_memory
                    WHERE semantic_memory_lifecycle = 'consolidating'
                       OR procedural_memory_lifecycle = 'consolidating'
                    """
                ).fetchone()["total"]
            )
        return MemoryCorpusSummary(
            user_scope_records=user_scope_records,
            mission_state_records=mission_state_records,
            specialist_context_records=specialist_context_records,
            semantic_records=semantic_records,
            procedural_records=procedural_records,
            retained_records=retained_records,
            promoted_records=promoted_records,
            aging_records=aging_records,
            review_recommended_records=review_recommended_records,
            fixed_records=fixed_records,
            operational_records=operational_records,
            archivable_records=archivable_records,
            consolidating_records=consolidating_records,
        )

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

                CREATE TABLE IF NOT EXISTS user_scope_snapshots (
                    user_id TEXT PRIMARY KEY,
                    context_status TEXT NOT NULL,
                    interaction_count INTEGER NOT NULL,
                    user_context_brief TEXT,
                    recent_intents TEXT NOT NULL DEFAULT '[]',
                    recent_domain_focus TEXT NOT NULL DEFAULT '[]',
                    active_mission_ids TEXT NOT NULL DEFAULT '[]',
                    recent_session_ids TEXT NOT NULL DEFAULT '[]',
                    last_recommended_task_type TEXT,
                    continuity_preference TEXT,
                    memory_refs TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    project_ref TEXT,
                    objective_ref TEXT,
                    work_item_refs TEXT NOT NULL DEFAULT '[]',
                    checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_states TEXT NOT NULL DEFAULT '[]',
                    objective_status TEXT,
                    next_action_ref TEXT,
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    project_ref TEXT,
                    objective_ref TEXT,
                    work_item_refs TEXT NOT NULL DEFAULT '[]',
                    checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_refs TEXT NOT NULL DEFAULT '[]',
                    objective_status TEXT,
                    next_action_ref TEXT,
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
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

                CREATE TABLE IF NOT EXISTS experience_reflections (
                    experience_id TEXT PRIMARY KEY,
                    reflection_id TEXT,
                    mission_id TEXT NOT NULL,
                    objective_ref TEXT,
                    surface_id TEXT,
                    workflow_profile TEXT NOT NULL,
                    outcome_status TEXT NOT NULL,
                    user_intent TEXT,
                    route TEXT,
                    primary_mind TEXT,
                    primary_domain_driver TEXT,
                    specialist_used TEXT NOT NULL DEFAULT '[]',
                    plan_summary TEXT,
                    execution_summary TEXT,
                    outcome TEXT,
                    errors TEXT NOT NULL DEFAULT '[]',
                    tools_used TEXT NOT NULL DEFAULT '[]',
                    checkpoints TEXT NOT NULL DEFAULT '[]',
                    user_feedback TEXT,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    signal_refs TEXT NOT NULL DEFAULT '[]',
                    failure_modes TEXT NOT NULL DEFAULT '[]',
                    decision_refs TEXT NOT NULL DEFAULT '[]',
                    learned_patterns TEXT NOT NULL DEFAULT '[]',
                    next_action_ref TEXT,
                    source_kind TEXT NOT NULL,
                    reusable_memory_status TEXT NOT NULL,
                    experience_human_review_required INTEGER NOT NULL,
                    experience_automatic_promotion_allowed INTEGER NOT NULL,
                    experience_core_mutation_allowed INTEGER NOT NULL,
                    reflection_status TEXT,
                    learning_candidate TEXT,
                    recommendation TEXT,
                    proposed_change_type TEXT,
                    proposed_tests TEXT NOT NULL DEFAULT '[]',
                    blockers TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT,
                    risk_hint TEXT,
                    reflection_human_review_required INTEGER,
                    reflection_automatic_promotion_allowed INTEGER,
                    reflection_core_mutation_allowed INTEGER,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_experience_reflections_mission_timestamp
                ON experience_reflections (mission_id, timestamp);

                CREATE TABLE IF NOT EXISTS reviewed_learning_guidance (
                    guidance_id TEXT PRIMARY KEY,
                    source_review_decision_id TEXT NOT NULL,
                    evolution_proposal_id TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    route TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    guidance_summary TEXT NOT NULL,
                    allowed_usage TEXT NOT NULL DEFAULT '[]',
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT,
                    automatic_promotion_allowed INTEGER NOT NULL,
                    core_mutation_allowed INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_reviewed_learning_guidance_scope_timestamp
                ON reviewed_learning_guidance (workflow_profile, route, domain, timestamp);

                CREATE TABLE IF NOT EXISTS memory_lifecycle_review_decisions (
                    review_decision_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    maintenance_action TEXT NOT NULL,
                    decision_action TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    operator_ref TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT NOT NULL,
                    governance_assessment_id TEXT NOT NULL,
                    review_notes TEXT NOT NULL DEFAULT '[]',
                    execution_authorized INTEGER NOT NULL,
                    automatic_execution_allowed INTEGER NOT NULL,
                    core_mutation_allowed INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_review_candidate_timestamp
                ON memory_lifecycle_review_decisions (candidate_id, timestamp);

                CREATE TABLE IF NOT EXISTS procedural_playbook_candidates (
                    playbook_candidate_id TEXT PRIMARY KEY,
                    procedure_name TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    route TEXT,
                    domain TEXT,
                    bounded_steps TEXT NOT NULL DEFAULT '[]',
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    source_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    source_reflection_refs TEXT NOT NULL DEFAULT '[]',
                    proposed_tests TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT,
                    risk_hint TEXT,
                    review_status TEXT NOT NULL,
                    blockers TEXT NOT NULL DEFAULT '[]',
                    human_review_required INTEGER NOT NULL,
                    automatic_promotion_allowed INTEGER NOT NULL,
                    core_mutation_allowed INTEGER NOT NULL,
                    memory_write_mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_procedural_playbook_candidates_scope_timestamp
                ON procedural_playbook_candidates (workflow_profile, review_status, timestamp);

                CREATE TABLE IF NOT EXISTS skill_candidates (
                    skill_candidate_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    inputs TEXT NOT NULL DEFAULT '[]',
                    outputs TEXT NOT NULL DEFAULT '[]',
                    allowed_tools TEXT NOT NULL DEFAULT '[]',
                    bounded_instructions TEXT NOT NULL DEFAULT '[]',
                    risk_level TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    source_pattern_refs TEXT NOT NULL DEFAULT '[]',
                    failure_modes TEXT NOT NULL DEFAULT '[]',
                    proposed_tests TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT NOT NULL,
                    registry_status TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    activation_status TEXT NOT NULL,
                    blockers TEXT NOT NULL DEFAULT '[]',
                    sandbox_required INTEGER NOT NULL,
                    human_review_required INTEGER NOT NULL,
                    automatic_activation_allowed INTEGER NOT NULL,
                    automatic_promotion_allowed INTEGER NOT NULL,
                    core_mutation_allowed INTEGER NOT NULL,
                    memory_write_mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE (skill_id, version)
                );

                CREATE INDEX IF NOT EXISTS idx_skill_candidates_scope_timestamp
                ON skill_candidates (
                    workflow_profile, domain, review_status, timestamp
                );

                CREATE TABLE IF NOT EXISTS specialist_shared_memory (
                    session_id TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    sharing_mode TEXT NOT NULL,
                    continuity_mode TEXT NOT NULL,
                    shared_memory_brief TEXT NOT NULL,
                    write_policy TEXT NOT NULL,
                    user_id TEXT,
                    consumer_mode TEXT NOT NULL DEFAULT 'baseline_shared_context',
                    source_mission_id TEXT,
                    source_mission_goal TEXT,
                    mission_context_brief TEXT,
                    domain_context_brief TEXT,
                    continuity_context_brief TEXT,
                    consumer_profile TEXT,
                    consumer_objective TEXT,
                    expected_deliverables TEXT NOT NULL DEFAULT '[]',
                    telemetry_focus TEXT NOT NULL DEFAULT '[]',
                    related_mission_ids TEXT NOT NULL DEFAULT '[]',
                    memory_refs TEXT NOT NULL DEFAULT '[]',
                    memory_class_policies TEXT NOT NULL DEFAULT '{}',
                    consumed_memory_classes TEXT NOT NULL DEFAULT '[]',
                    memory_write_policies TEXT NOT NULL DEFAULT '{}',
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    semantic_memory_lifecycle TEXT,
                    procedural_memory_lifecycle TEXT,
                    memory_lifecycle_status TEXT,
                    memory_review_status TEXT,
                    procedural_artifact_status TEXT,
                    procedural_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    procedural_artifact_version INTEGER,
                    procedural_artifact_summary TEXT,
                    domain_mission_link_reason TEXT,
                    recurrent_context_status TEXT NOT NULL DEFAULT 'not_applicable',
                    recurrent_interaction_count INTEGER NOT NULL DEFAULT 0,
                    recurrent_context_brief TEXT,
                    recurrent_domain_focus TEXT NOT NULL DEFAULT '[]',
                    recurrent_memory_refs TEXT NOT NULL DEFAULT '[]',
                    recurrent_continuity_modes TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    project_ref TEXT,
                    objective_ref TEXT,
                    work_item_refs TEXT NOT NULL DEFAULT '[]',
                    work_items TEXT NOT NULL DEFAULT '[]',
                    checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_refs TEXT NOT NULL DEFAULT '[]',
                    objective_status TEXT,
                    next_action_ref TEXT,
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
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
            self._ensure_column(connection, "mission_states", "ecosystem_state_status", "TEXT")
            self._ensure_column(
                connection, "mission_states", "active_work_items", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(
                connection,
                "mission_states",
                "active_artifact_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "mission_states",
                "open_checkpoint_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection, "mission_states", "surface_presence", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(connection, "mission_states", "ecosystem_state_summary", "TEXT")
            self._ensure_project_objective_columns(connection, "mission_states")
            self._ensure_column(
                connection, "mission_states", "work_items", "TEXT NOT NULL DEFAULT '[]'"
            )
            self._ensure_column(
                connection,
                "mission_states",
                "artifact_states",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_surface_continuity_columns(connection, "mission_states")
            self._ensure_column(connection, "session_continuity", "ecosystem_state_status", "TEXT")
            self._ensure_column(
                connection,
                "session_continuity",
                "active_work_items",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "session_continuity",
                "active_artifact_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "session_continuity",
                "open_checkpoint_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "session_continuity",
                "surface_presence",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection, "session_continuity", "ecosystem_state_summary", "TEXT"
            )
            self._ensure_project_objective_columns(connection, "session_continuity")
            self._ensure_surface_continuity_columns(connection, "session_continuity")
            self._ensure_column(
                connection, "continuity_checkpoints", "ecosystem_state_status", "TEXT"
            )
            self._ensure_column(
                connection,
                "continuity_checkpoints",
                "active_work_items",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "continuity_checkpoints",
                "active_artifact_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "continuity_checkpoints",
                "open_checkpoint_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "continuity_checkpoints",
                "surface_presence",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection, "continuity_checkpoints", "ecosystem_state_summary", "TEXT"
            )
            self._ensure_project_objective_columns(connection, "continuity_checkpoints")
            self._ensure_surface_continuity_columns(connection, "continuity_checkpoints")
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
                "consumed_memory_classes",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "memory_write_policies",
                "TEXT NOT NULL DEFAULT '{}'",
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
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "domain_mission_link_reason",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "semantic_memory_lifecycle",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "procedural_memory_lifecycle",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "memory_lifecycle_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "memory_review_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "procedural_artifact_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "procedural_artifact_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "procedural_artifact_version",
                "INTEGER",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "procedural_artifact_summary",
                "TEXT",
            )
            self._ensure_column(connection, "specialist_shared_memory", "user_id", "TEXT")
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_context_status",
                "TEXT NOT NULL DEFAULT 'not_applicable'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_interaction_count",
                "INTEGER NOT NULL DEFAULT 0",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_context_brief",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_domain_focus",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_memory_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "specialist_shared_memory",
                "recurrent_continuity_modes",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            connection.commit()

    def _ensure_column(
        self, connection: Connection, table: str, column: str, definition: str
    ) -> None:
        try:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        except OperationalError:
            pass

    def _ensure_surface_continuity_columns(
        self,
        connection: Connection,
        table: str,
    ) -> None:
        self._ensure_column(
            connection, table, "linked_surface_ids", "TEXT NOT NULL DEFAULT '[]'"
        )
        self._ensure_column(connection, table, "active_surface_id", "TEXT")
        self._ensure_column(connection, table, "last_surface_id", "TEXT")
        self._ensure_column(connection, table, "surface_continuity_status", "TEXT")
        self._ensure_column(
            connection,
            table,
            "surface_identity_conflict_flags",
            "TEXT NOT NULL DEFAULT '[]'",
        )

    def _ensure_project_objective_columns(
        self,
        connection: Connection,
        table: str,
    ) -> None:
        self._ensure_column(connection, table, "project_ref", "TEXT")
        self._ensure_column(connection, table, "objective_ref", "TEXT")
        self._ensure_column(
            connection, table, "work_item_refs", "TEXT NOT NULL DEFAULT '[]'"
        )
        self._ensure_column(
            connection, table, "checkpoint_refs", "TEXT NOT NULL DEFAULT '[]'"
        )
        self._ensure_column(
            connection, table, "artifact_refs", "TEXT NOT NULL DEFAULT '[]'"
        )
        self._ensure_column(connection, table, "objective_status", "TEXT")
        self._ensure_column(connection, table, "next_action_ref", "TEXT")

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
    def _row_to_user_scope_snapshot(row: Row) -> UserScopeContextContract:
        return UserScopeContextContract(
            user_id=str(row["user_id"]),
            context_status=str(row["context_status"]),
            interaction_count=int(row["interaction_count"] or 0),
            user_context_brief=row["user_context_brief"],
            recent_intents=list(loads(row["recent_intents"] or "[]")),
            recent_domain_focus=list(loads(row["recent_domain_focus"] or "[]")),
            active_mission_ids=list(loads(row["active_mission_ids"] or "[]")),
            recent_session_ids=list(loads(row["recent_session_ids"] or "[]")),
            last_recommended_task_type=row["last_recommended_task_type"],
            continuity_preference=row["continuity_preference"],
            memory_refs=list(loads(row["memory_refs"] or "[]")),
        )

    @staticmethod
    def _row_to_experience_reflection(row: Row) -> StoredExperienceReflection:
        evidence_refs = list(loads(row["evidence_refs"] or "[]"))
        experience = ExperienceRecordContract(
            experience_id=str(row["experience_id"]),
            mission_id=MissionId(str(row["mission_id"])),
            objective_ref=row["objective_ref"],
            surface_id=row["surface_id"],
            workflow_profile=str(row["workflow_profile"]),
            outcome_status=str(row["outcome_status"]),
            user_intent=row["user_intent"],
            route=row["route"],
            primary_mind=row["primary_mind"],
            primary_domain_driver=row["primary_domain_driver"],
            specialist_used=list(loads(row["specialist_used"] or "[]")),
            plan_summary=row["plan_summary"],
            execution_summary=row["execution_summary"],
            outcome=row["outcome"],
            errors=list(loads(row["errors"] or "[]")),
            tools_used=list(loads(row["tools_used"] or "[]")),
            checkpoints=list(loads(row["checkpoints"] or "[]")),
            user_feedback=row["user_feedback"],
            evidence_refs=evidence_refs,
            signal_refs=list(loads(row["signal_refs"] or "[]")),
            failure_modes=list(loads(row["failure_modes"] or "[]")),
            decision_refs=list(loads(row["decision_refs"] or "[]")),
            learned_patterns=list(loads(row["learned_patterns"] or "[]")),
            next_action_ref=row["next_action_ref"],
            source_kind=str(row["source_kind"]),
            reusable_memory_status=str(row["reusable_memory_status"]),
            human_review_required=bool(row["experience_human_review_required"]),
            automatic_promotion_allowed=bool(
                row["experience_automatic_promotion_allowed"]
            ),
            core_mutation_allowed=bool(row["experience_core_mutation_allowed"]),
            timestamp=str(row["timestamp"]),
        )
        if row["reflection_id"] is None:
            return StoredExperienceReflection(experience=experience, reflection=None)
        reflection = PostTaskReflectionContract(
            reflection_id=str(row["reflection_id"]),
            experience_id=str(row["experience_id"]),
            reflection_status=str(row["reflection_status"]),
            learning_candidate=str(row["learning_candidate"]),
            recommendation=str(row["recommendation"]),
            proposed_change_type=str(row["proposed_change_type"]),
            evidence_refs=evidence_refs,
            proposed_tests=list(loads(row["proposed_tests"] or "[]")),
            blockers=list(loads(row["blockers"] or "[]")),
            rollback_plan_ref=row["rollback_plan_ref"],
            risk_hint=row["risk_hint"],
            human_review_required=bool(row["reflection_human_review_required"]),
            automatic_promotion_allowed=bool(
                row["reflection_automatic_promotion_allowed"]
            ),
            core_mutation_allowed=bool(row["reflection_core_mutation_allowed"]),
            timestamp=str(row["timestamp"]),
        )
        return StoredExperienceReflection(experience=experience, reflection=reflection)

    @staticmethod
    def _row_to_reviewed_learning_guidance(
        row: Row,
    ) -> StoredReviewedLearningGuidance:
        return StoredReviewedLearningGuidance(
            guidance=ReviewedLearningGuidanceContract(
                guidance_id=str(row["guidance_id"]),
                source_review_decision_id=str(row["source_review_decision_id"]),
                evolution_proposal_id=str(row["evolution_proposal_id"]),
                review_status=str(row["review_status"]),
                route=str(row["route"]),
                workflow_profile=str(row["workflow_profile"]),
                domain=str(row["domain"]),
                guidance_summary=str(row["guidance_summary"]),
                allowed_usage=list(loads(row["allowed_usage"] or "[]")),
                evidence_refs=list(loads(row["evidence_refs"] or "[]")),
                rollback_plan_ref=row["rollback_plan_ref"],
                timestamp=str(row["timestamp"]),
                expires_at=row["expires_at"],
                automatic_promotion_allowed=bool(
                    row["automatic_promotion_allowed"]
                ),
                core_mutation_allowed=bool(row["core_mutation_allowed"]),
            )
        )

    @staticmethod
    def _row_to_procedural_playbook_candidate(
        row: Row,
    ) -> StoredProceduralPlaybookCandidate:
        return StoredProceduralPlaybookCandidate(
            candidate=ProceduralPlaybookCandidateContract(
                playbook_candidate_id=str(row["playbook_candidate_id"]),
                procedure_name=str(row["procedure_name"]),
                workflow_profile=str(row["workflow_profile"]),
                route=row["route"],
                domain=row["domain"],
                bounded_steps=list(loads(row["bounded_steps"] or "[]")),
                evidence_refs=list(loads(row["evidence_refs"] or "[]")),
                source_artifact_refs=list(
                    loads(row["source_artifact_refs"] or "[]")
                ),
                source_reflection_refs=list(
                    loads(row["source_reflection_refs"] or "[]")
                ),
                proposed_tests=list(loads(row["proposed_tests"] or "[]")),
                rollback_plan_ref=row["rollback_plan_ref"],
                risk_hint=row["risk_hint"],
                review_status=str(row["review_status"]),
                blockers=list(loads(row["blockers"] or "[]")),
                human_review_required=bool(row["human_review_required"]),
                automatic_promotion_allowed=bool(
                    row["automatic_promotion_allowed"]
                ),
                core_mutation_allowed=bool(row["core_mutation_allowed"]),
                memory_write_mode=str(row["memory_write_mode"]),
                timestamp=str(row["timestamp"]),
            )
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            project_ref=row["project_ref"],
            objective_ref=row["objective_ref"],
            work_item_refs=list(loads(row["work_item_refs"] or "[]")),
            work_items=_deserialize_work_items(
                row["work_items"], mission_id=str(row["mission_id"])
            ),
            checkpoint_refs=list(loads(row["checkpoint_refs"] or "[]")),
            artifact_refs=list(loads(row["artifact_refs"] or "[]")),
            artifact_states=_deserialize_artifact_states(
                row["artifact_states"], mission_id=str(row["mission_id"])
            ),
            objective_status=row["objective_status"],
            next_action_ref=row["next_action_ref"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _row_to_specialist_shared_memory(row: Row) -> SpecialistSharedMemoryContextContract:
        lifecycle_support = memory_lifecycle_support_signals(
            semantic_lifecycle=row["semantic_memory_lifecycle"],
            procedural_lifecycle=row["procedural_memory_lifecycle"],
        )
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
            consumer_profile=row["consumer_profile"],
            consumer_objective=row["consumer_objective"],
            expected_deliverables=list(loads(row["expected_deliverables"] or "[]")),
            telemetry_focus=list(loads(row["telemetry_focus"] or "[]")),
            related_mission_ids=list(loads(row["related_mission_ids"] or "[]")),
            memory_refs=list(loads(row["memory_refs"] or "[]")),
            memory_class_policies=dict(loads(row["memory_class_policies"] or "{}")),
            consumed_memory_classes=list(loads(row["consumed_memory_classes"] or "[]")),
            memory_write_policies=dict(loads(row["memory_write_policies"] or "{}")),
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_recommendation=row["last_recommendation"],
            semantic_memory_lifecycle=row["semantic_memory_lifecycle"],
            procedural_memory_lifecycle=row["procedural_memory_lifecycle"],
            semantic_memory_state=str(lifecycle_support["semantic_memory_state"])
            if lifecycle_support["semantic_memory_state"] is not None
            else None,
            procedural_memory_state=str(lifecycle_support["procedural_memory_state"])
            if lifecycle_support["procedural_memory_state"] is not None
            else None,
            memory_lifecycle_status=row["memory_lifecycle_status"],
            memory_review_status=row["memory_review_status"],
            memory_consolidation_status=str(lifecycle_support["consolidation_status"]),
            memory_fixation_status=str(lifecycle_support["fixation_status"]),
            memory_archive_status=str(lifecycle_support["archive_status"]),
            procedural_artifact_status=row["procedural_artifact_status"],
            procedural_artifact_refs=list(loads(row["procedural_artifact_refs"] or "[]")),
            procedural_artifact_version=row["procedural_artifact_version"],
            procedural_artifact_summary=row["procedural_artifact_summary"],
            domain_mission_link_reason=row["domain_mission_link_reason"],
            recurrent_context_status=str(row["recurrent_context_status"] or "not_applicable"),
            recurrent_interaction_count=int(row["recurrent_interaction_count"] or 0),
            recurrent_context_brief=row["recurrent_context_brief"],
            recurrent_domain_focus=list(loads(row["recurrent_domain_focus"] or "[]")),
            recurrent_memory_refs=list(loads(row["recurrent_memory_refs"] or "[]")),
            recurrent_continuity_modes=list(loads(row["recurrent_continuity_modes"] or "[]")),
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

    def upsert_user_scope_snapshot(self, snapshot: StoredUserScopeSnapshot) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_scope_snapshots (
                    user_id, context_status, interaction_count, user_context_brief,
                    recent_intents, recent_domain_focus, active_mission_ids, recent_session_ids,
                    last_recommended_task_type, continuity_preference, memory_refs, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    context_status = EXCLUDED.context_status,
                    interaction_count = EXCLUDED.interaction_count,
                    user_context_brief = EXCLUDED.user_context_brief,
                    recent_intents = EXCLUDED.recent_intents,
                    recent_domain_focus = EXCLUDED.recent_domain_focus,
                    active_mission_ids = EXCLUDED.active_mission_ids,
                    recent_session_ids = EXCLUDED.recent_session_ids,
                    last_recommended_task_type = EXCLUDED.last_recommended_task_type,
                    continuity_preference = EXCLUDED.continuity_preference,
                    memory_refs = EXCLUDED.memory_refs,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot.user_id,
                    snapshot.context_status,
                    snapshot.interaction_count,
                    snapshot.user_context_brief,
                    dumps(snapshot.recent_intents),
                    dumps(snapshot.recent_domain_focus),
                    dumps(snapshot.active_mission_ids),
                    dumps(snapshot.recent_session_ids),
                    snapshot.last_recommended_task_type,
                    snapshot.continuity_preference,
                    dumps(snapshot.memory_refs),
                    snapshot.updated_at,
                ),
            )
            connection.commit()

    def fetch_user_scope_snapshot(self, user_id: str) -> UserScopeContextContract | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, context_status, interaction_count, user_context_brief,
                       recent_intents, recent_domain_focus, active_mission_ids, recent_session_ids,
                       last_recommended_task_type, continuity_preference, memory_refs
                FROM user_scope_snapshots
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return UserScopeContextContract(
            user_id=row["user_id"],
            context_status=row["context_status"],
            interaction_count=int(row["interaction_count"] or 0),
            user_context_brief=row["user_context_brief"],
            recent_intents=list(loads(row["recent_intents"] or "[]")),
            recent_domain_focus=list(loads(row["recent_domain_focus"] or "[]")),
            active_mission_ids=list(loads(row["active_mission_ids"] or "[]")),
            recent_session_ids=list(loads(row["recent_session_ids"] or "[]")),
            last_recommended_task_type=row["last_recommended_task_type"],
            continuity_preference=row["continuity_preference"],
            memory_refs=list(loads(row["memory_refs"] or "[]")),
        )

    def upsert_mission_state(self, mission_state: MissionStateContract) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mission_states (
                    mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                    related_memories, related_artifacts, recent_plan_steps,
                    last_recommendation, semantic_brief, semantic_focus,
                    identity_continuity_brief, open_loops, last_decision_frame,
                    ecosystem_state_status, active_work_items, active_artifact_refs,
                    open_checkpoint_refs, surface_presence, ecosystem_state_summary,
                    project_ref, objective_ref, work_item_refs, work_items, checkpoint_refs,
                    artifact_refs, artifact_states, objective_status, next_action_ref,
                    linked_surface_ids, active_surface_id, last_surface_id,
                    surface_continuity_status, surface_identity_conflict_flags, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
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
                    ecosystem_state_status = EXCLUDED.ecosystem_state_status,
                    active_work_items = EXCLUDED.active_work_items,
                    active_artifact_refs = EXCLUDED.active_artifact_refs,
                    open_checkpoint_refs = EXCLUDED.open_checkpoint_refs,
                    surface_presence = EXCLUDED.surface_presence,
                    ecosystem_state_summary = EXCLUDED.ecosystem_state_summary,
                    project_ref = EXCLUDED.project_ref,
                    objective_ref = EXCLUDED.objective_ref,
                    work_item_refs = EXCLUDED.work_item_refs,
                    work_items = EXCLUDED.work_items,
                    checkpoint_refs = EXCLUDED.checkpoint_refs,
                    artifact_refs = EXCLUDED.artifact_refs,
                    artifact_states = EXCLUDED.artifact_states,
                    objective_status = EXCLUDED.objective_status,
                    next_action_ref = EXCLUDED.next_action_ref,
                    linked_surface_ids = EXCLUDED.linked_surface_ids,
                    active_surface_id = EXCLUDED.active_surface_id,
                    last_surface_id = EXCLUDED.last_surface_id,
                    surface_continuity_status = EXCLUDED.surface_continuity_status,
                    surface_identity_conflict_flags = EXCLUDED.surface_identity_conflict_flags,
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
                    mission_state.ecosystem_state_status,
                    dumps(mission_state.active_work_items),
                    dumps(mission_state.active_artifact_refs),
                    dumps(mission_state.open_checkpoint_refs),
                    dumps(mission_state.surface_presence),
                    mission_state.ecosystem_state_summary,
                    mission_state.project_ref,
                    mission_state.objective_ref,
                    dumps(mission_state.work_item_refs),
                    _serialize_work_items(mission_state.work_items),
                    dumps(mission_state.checkpoint_refs),
                    dumps(mission_state.artifact_refs),
                    _serialize_artifact_states(mission_state.artifact_states),
                    mission_state.objective_status,
                    mission_state.next_action_ref,
                    dumps(mission_state.linked_surface_ids),
                    mission_state.active_surface_id,
                    mission_state.last_surface_id,
                    mission_state.surface_continuity_status,
                    dumps(mission_state.surface_identity_conflict_flags),
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
                    anchor_goal, related_mission_id, related_goal, ecosystem_state_status,
                    active_work_items, active_artifact_refs, open_checkpoint_refs,
                    surface_presence, ecosystem_state_summary, linked_surface_ids,
                    active_surface_id, last_surface_id, surface_continuity_status,
                    surface_identity_conflict_flags, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id) DO UPDATE SET
                    continuity_brief = EXCLUDED.continuity_brief,
                    continuity_mode = EXCLUDED.continuity_mode,
                    anchor_mission_id = EXCLUDED.anchor_mission_id,
                    anchor_goal = EXCLUDED.anchor_goal,
                    related_mission_id = EXCLUDED.related_mission_id,
                    related_goal = EXCLUDED.related_goal,
                    ecosystem_state_status = EXCLUDED.ecosystem_state_status,
                    active_work_items = EXCLUDED.active_work_items,
                    active_artifact_refs = EXCLUDED.active_artifact_refs,
                    open_checkpoint_refs = EXCLUDED.open_checkpoint_refs,
                    surface_presence = EXCLUDED.surface_presence,
                    ecosystem_state_summary = EXCLUDED.ecosystem_state_summary,
                    linked_surface_ids = EXCLUDED.linked_surface_ids,
                    active_surface_id = EXCLUDED.active_surface_id,
                    last_surface_id = EXCLUDED.last_surface_id,
                    surface_continuity_status = EXCLUDED.surface_continuity_status,
                    surface_identity_conflict_flags = EXCLUDED.surface_identity_conflict_flags,
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
                    snapshot.ecosystem_state_status,
                    dumps(snapshot.active_work_items),
                    dumps(snapshot.active_artifact_refs),
                    dumps(snapshot.open_checkpoint_refs),
                    dumps(snapshot.surface_presence),
                    snapshot.ecosystem_state_summary,
                    dumps(snapshot.linked_surface_ids),
                    snapshot.active_surface_id,
                    snapshot.last_surface_id,
                    snapshot.surface_continuity_status,
                    dumps(snapshot.surface_identity_conflict_flags),
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
                    target_goal, origin_request_id, replay_summary, ecosystem_state_status,
                    active_work_items, active_artifact_refs, open_checkpoint_refs,
                    surface_presence, ecosystem_state_summary, linked_surface_ids,
                    active_surface_id, last_surface_id, surface_continuity_status,
                    surface_identity_conflict_flags, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
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
                    ecosystem_state_status = EXCLUDED.ecosystem_state_status,
                    active_work_items = EXCLUDED.active_work_items,
                    active_artifact_refs = EXCLUDED.active_artifact_refs,
                    open_checkpoint_refs = EXCLUDED.open_checkpoint_refs,
                    surface_presence = EXCLUDED.surface_presence,
                    ecosystem_state_summary = EXCLUDED.ecosystem_state_summary,
                    linked_surface_ids = EXCLUDED.linked_surface_ids,
                    active_surface_id = EXCLUDED.active_surface_id,
                    last_surface_id = EXCLUDED.last_surface_id,
                    surface_continuity_status = EXCLUDED.surface_continuity_status,
                    surface_identity_conflict_flags = EXCLUDED.surface_identity_conflict_flags,
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
                    checkpoint.ecosystem_state_status,
                    dumps(checkpoint.active_work_items),
                    dumps(checkpoint.active_artifact_refs),
                    dumps(checkpoint.open_checkpoint_refs),
                    dumps(checkpoint.surface_presence),
                    checkpoint.ecosystem_state_summary,
                    dumps(checkpoint.linked_surface_ids),
                    checkpoint.active_surface_id,
                    checkpoint.last_surface_id,
                    checkpoint.surface_continuity_status,
                    dumps(checkpoint.surface_identity_conflict_flags),
                    checkpoint.updated_at,
                ),
            )
            connection.commit()

    def fetch_session_continuity(self, session_id: str) -> SessionContinuitySnapshot | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT session_id, continuity_brief, continuity_mode, anchor_mission_id,
                       anchor_goal, related_mission_id, related_goal, ecosystem_state_status,
                       active_work_items, active_artifact_refs, open_checkpoint_refs,
                       surface_presence, ecosystem_state_summary, linked_surface_ids,
                       active_surface_id, last_surface_id, surface_continuity_status,
                       surface_identity_conflict_flags, updated_at
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
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
                       target_goal, origin_request_id, replay_summary, ecosystem_state_status,
                       active_work_items, active_artifact_refs, open_checkpoint_refs,
                       surface_presence, ecosystem_state_summary, linked_surface_ids,
                       active_surface_id, last_surface_id, surface_continuity_status,
                       surface_identity_conflict_flags, updated_at
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
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

    def record_experience_reflection(
        self,
        record: StoredExperienceReflection,
    ) -> None:
        experience = record.experience
        reflection = record.reflection
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO experience_reflections (
                    experience_id, reflection_id, mission_id, objective_ref, surface_id,
                    workflow_profile, outcome_status, user_intent, route, primary_mind,
                    primary_domain_driver, specialist_used, plan_summary, execution_summary,
                    outcome, errors, tools_used, checkpoints, user_feedback,
                    evidence_refs, signal_refs, failure_modes, decision_refs, learned_patterns,
                    next_action_ref,
                    source_kind, reusable_memory_status, experience_human_review_required,
                    experience_automatic_promotion_allowed, experience_core_mutation_allowed,
                    reflection_status, learning_candidate, recommendation,
                    proposed_change_type, proposed_tests, blockers, rollback_plan_ref,
                    risk_hint, reflection_human_review_required,
                    reflection_automatic_promotion_allowed, reflection_core_mutation_allowed,
                    timestamp
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (experience_id) DO UPDATE SET
                    reflection_id = EXCLUDED.reflection_id,
                    workflow_profile = EXCLUDED.workflow_profile,
                    outcome_status = EXCLUDED.outcome_status,
                    user_intent = EXCLUDED.user_intent,
                    route = EXCLUDED.route,
                    primary_mind = EXCLUDED.primary_mind,
                    primary_domain_driver = EXCLUDED.primary_domain_driver,
                    specialist_used = EXCLUDED.specialist_used,
                    plan_summary = EXCLUDED.plan_summary,
                    execution_summary = EXCLUDED.execution_summary,
                    outcome = EXCLUDED.outcome,
                    errors = EXCLUDED.errors,
                    tools_used = EXCLUDED.tools_used,
                    checkpoints = EXCLUDED.checkpoints,
                    user_feedback = EXCLUDED.user_feedback,
                    evidence_refs = EXCLUDED.evidence_refs,
                    signal_refs = EXCLUDED.signal_refs,
                    failure_modes = EXCLUDED.failure_modes,
                    decision_refs = EXCLUDED.decision_refs,
                    learned_patterns = EXCLUDED.learned_patterns,
                    next_action_ref = EXCLUDED.next_action_ref,
                    reusable_memory_status = EXCLUDED.reusable_memory_status,
                    reflection_status = EXCLUDED.reflection_status,
                    learning_candidate = EXCLUDED.learning_candidate,
                    recommendation = EXCLUDED.recommendation,
                    proposed_change_type = EXCLUDED.proposed_change_type,
                    proposed_tests = EXCLUDED.proposed_tests,
                    blockers = EXCLUDED.blockers,
                    rollback_plan_ref = EXCLUDED.rollback_plan_ref,
                    risk_hint = EXCLUDED.risk_hint,
                    timestamp = EXCLUDED.timestamp
                """,
                (
                    experience.experience_id,
                    reflection.reflection_id if reflection else None,
                    str(experience.mission_id),
                    experience.objective_ref,
                    experience.surface_id,
                    experience.workflow_profile,
                    experience.outcome_status,
                    experience.user_intent,
                    experience.route,
                    experience.primary_mind,
                    experience.primary_domain_driver,
                    dumps(experience.specialist_used),
                    experience.plan_summary,
                    experience.execution_summary,
                    experience.outcome,
                    dumps(experience.errors),
                    dumps(experience.tools_used),
                    dumps(experience.checkpoints),
                    experience.user_feedback,
                    dumps(experience.evidence_refs),
                    dumps(experience.signal_refs),
                    dumps(experience.failure_modes),
                    dumps(experience.decision_refs),
                    dumps(experience.learned_patterns),
                    experience.next_action_ref,
                    experience.source_kind,
                    experience.reusable_memory_status,
                    experience.human_review_required,
                    experience.automatic_promotion_allowed,
                    experience.core_mutation_allowed,
                    reflection.reflection_status if reflection else None,
                    reflection.learning_candidate if reflection else None,
                    reflection.recommendation if reflection else None,
                    reflection.proposed_change_type if reflection else None,
                    dumps(reflection.proposed_tests if reflection else []),
                    dumps(reflection.blockers if reflection else []),
                    reflection.rollback_plan_ref if reflection else None,
                    reflection.risk_hint if reflection else None,
                    reflection.human_review_required if reflection else None,
                    reflection.automatic_promotion_allowed if reflection else None,
                    reflection.core_mutation_allowed if reflection else None,
                    experience.timestamp,
                ),
            )
            connection.commit()

    def list_experience_reflections(
        self,
        *,
        mission_id: str | None = None,
        workflow_profile: str | None = None,
        limit: int = 20,
    ) -> list[StoredExperienceReflection]:
        clauses: list[str] = []
        params: list[object] = []
        if mission_id:
            clauses.append("mission_id = %s")
            params.append(mission_id)
        if workflow_profile:
            clauses.append("workflow_profile = %s")
            params.append(workflow_profile)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM experience_reflections
                {where}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return [self._row_to_experience_reflection(row) for row in rows]

    def fetch_experience_reflection(
        self,
        experience_id: str,
    ) -> StoredExperienceReflection | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM experience_reflections
                WHERE experience_id = %s
                """,
                (experience_id,),
            )
            row = cursor.fetchone()
        return self._row_to_experience_reflection(row) if row is not None else None

    def record_reviewed_learning_guidance(
        self,
        record: StoredReviewedLearningGuidance,
    ) -> None:
        guidance = record.guidance
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO reviewed_learning_guidance (
                    guidance_id, source_review_decision_id, evolution_proposal_id,
                    review_status, route, workflow_profile, domain, guidance_summary,
                    allowed_usage, evidence_refs, rollback_plan_ref, timestamp,
                    expires_at, automatic_promotion_allowed, core_mutation_allowed
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (guidance_id) DO UPDATE SET
                    source_review_decision_id = EXCLUDED.source_review_decision_id,
                    evolution_proposal_id = EXCLUDED.evolution_proposal_id,
                    review_status = EXCLUDED.review_status,
                    route = EXCLUDED.route,
                    workflow_profile = EXCLUDED.workflow_profile,
                    domain = EXCLUDED.domain,
                    guidance_summary = EXCLUDED.guidance_summary,
                    allowed_usage = EXCLUDED.allowed_usage,
                    evidence_refs = EXCLUDED.evidence_refs,
                    rollback_plan_ref = EXCLUDED.rollback_plan_ref,
                    timestamp = EXCLUDED.timestamp,
                    expires_at = EXCLUDED.expires_at,
                    automatic_promotion_allowed = EXCLUDED.automatic_promotion_allowed,
                    core_mutation_allowed = EXCLUDED.core_mutation_allowed
                """,
                (
                    guidance.guidance_id,
                    guidance.source_review_decision_id,
                    str(guidance.evolution_proposal_id),
                    guidance.review_status,
                    guidance.route,
                    guidance.workflow_profile,
                    guidance.domain,
                    guidance.guidance_summary,
                    dumps(guidance.allowed_usage),
                    dumps(guidance.evidence_refs),
                    guidance.rollback_plan_ref,
                    guidance.timestamp,
                    guidance.expires_at,
                    guidance.automatic_promotion_allowed,
                    guidance.core_mutation_allowed,
                ),
            )
            connection.commit()

    def list_reviewed_learning_guidance(
        self,
        *,
        route: str | None = None,
        workflow_profile: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[StoredReviewedLearningGuidance]:
        clauses: list[str] = []
        params: list[object] = []
        if route:
            clauses.append("route = %s")
            params.append(route)
        if workflow_profile:
            clauses.append("workflow_profile = %s")
            params.append(workflow_profile)
        if domain:
            clauses.append("domain = %s")
            params.append(domain)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM reviewed_learning_guidance
                {where}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return [self._row_to_reviewed_learning_guidance(row) for row in rows]

    def record_memory_lifecycle_review_decision(
        self,
        record: StoredMemoryLifecycleReviewDecision,
    ) -> None:
        decision = record.decision
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO memory_lifecycle_review_decisions (
                    review_decision_id, candidate_id, maintenance_action,
                    decision_action, review_status, operator_ref, evidence_refs,
                    rollback_plan_ref, governance_assessment_id, review_notes,
                    execution_authorized, automatic_execution_allowed,
                    core_mutation_allowed, timestamp
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    decision.review_decision_id,
                    decision.candidate_id,
                    decision.maintenance_action,
                    decision.decision_action,
                    decision.review_status,
                    decision.operator_ref,
                    dumps(decision.evidence_refs),
                    decision.rollback_plan_ref,
                    decision.governance_assessment_id,
                    dumps(decision.review_notes),
                    decision.execution_authorized,
                    decision.automatic_execution_allowed,
                    decision.core_mutation_allowed,
                    decision.timestamp,
                ),
            )
            connection.commit()

    def list_memory_lifecycle_review_decisions(
        self,
        *,
        candidate_id: str | None = None,
        limit: int = 20,
    ) -> list[StoredMemoryLifecycleReviewDecision]:
        where = "WHERE candidate_id = %s" if candidate_id else ""
        params: tuple[object, ...] = (
            (candidate_id, limit) if candidate_id else (limit,)
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM memory_lifecycle_review_decisions
                {where}
                ORDER BY timestamp DESC, review_decision_id DESC
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()
        return [_stored_memory_lifecycle_review_from_row(row) for row in rows]

    def record_procedural_playbook_candidate(
        self,
        record: StoredProceduralPlaybookCandidate,
    ) -> None:
        candidate = record.candidate
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO procedural_playbook_candidates (
                    playbook_candidate_id, procedure_name, workflow_profile, route,
                    domain, bounded_steps, evidence_refs, source_artifact_refs,
                    source_reflection_refs, proposed_tests, rollback_plan_ref,
                    risk_hint, review_status, blockers, human_review_required,
                    automatic_promotion_allowed, core_mutation_allowed,
                    memory_write_mode, timestamp
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                ON CONFLICT (playbook_candidate_id) DO UPDATE SET
                    procedure_name = EXCLUDED.procedure_name,
                    workflow_profile = EXCLUDED.workflow_profile,
                    route = EXCLUDED.route,
                    domain = EXCLUDED.domain,
                    bounded_steps = EXCLUDED.bounded_steps,
                    evidence_refs = EXCLUDED.evidence_refs,
                    source_artifact_refs = EXCLUDED.source_artifact_refs,
                    source_reflection_refs = EXCLUDED.source_reflection_refs,
                    proposed_tests = EXCLUDED.proposed_tests,
                    rollback_plan_ref = EXCLUDED.rollback_plan_ref,
                    risk_hint = EXCLUDED.risk_hint,
                    review_status = EXCLUDED.review_status,
                    blockers = EXCLUDED.blockers,
                    human_review_required = EXCLUDED.human_review_required,
                    automatic_promotion_allowed = EXCLUDED.automatic_promotion_allowed,
                    core_mutation_allowed = EXCLUDED.core_mutation_allowed,
                    memory_write_mode = EXCLUDED.memory_write_mode,
                    timestamp = EXCLUDED.timestamp
                """,
                (
                    candidate.playbook_candidate_id,
                    candidate.procedure_name,
                    candidate.workflow_profile,
                    candidate.route,
                    candidate.domain,
                    dumps(candidate.bounded_steps),
                    dumps(candidate.evidence_refs),
                    dumps(candidate.source_artifact_refs),
                    dumps(candidate.source_reflection_refs),
                    dumps(candidate.proposed_tests),
                    candidate.rollback_plan_ref,
                    candidate.risk_hint,
                    candidate.review_status,
                    dumps(candidate.blockers),
                    candidate.human_review_required,
                    candidate.automatic_promotion_allowed,
                    candidate.core_mutation_allowed,
                    candidate.memory_write_mode,
                    candidate.timestamp,
                ),
            )
            connection.commit()

    def list_procedural_playbook_candidates(
        self,
        *,
        workflow_profile: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredProceduralPlaybookCandidate]:
        clauses: list[str] = []
        params: list[object] = []
        if workflow_profile:
            clauses.append("workflow_profile = %s")
            params.append(workflow_profile)
        if review_status:
            clauses.append("review_status = %s")
            params.append(review_status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM procedural_playbook_candidates
                {where}
                ORDER BY timestamp DESC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return [self._row_to_procedural_playbook_candidate(row) for row in rows]

    def record_skill_candidate(self, record: StoredSkillCandidate) -> None:
        candidate = record.candidate
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO skill_candidates (
                    skill_candidate_id, skill_id, skill_name, version,
                    workflow_profile, domain, specialist_type, inputs, outputs,
                    allowed_tools, bounded_instructions, risk_level, evidence_refs,
                    source_pattern_refs, failure_modes, proposed_tests,
                    rollback_plan_ref, registry_status, review_status,
                    activation_status, blockers, sandbox_required,
                    human_review_required, automatic_activation_allowed,
                    automatic_promotion_allowed, core_mutation_allowed,
                    memory_write_mode, timestamp
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    candidate.skill_candidate_id,
                    candidate.skill_id,
                    candidate.skill_name,
                    candidate.version,
                    candidate.workflow_profile,
                    candidate.domain,
                    candidate.specialist_type,
                    dumps(candidate.inputs),
                    dumps(candidate.outputs),
                    dumps(candidate.allowed_tools),
                    dumps(candidate.bounded_instructions),
                    str(candidate.risk_level),
                    dumps(candidate.evidence_refs),
                    dumps(candidate.source_pattern_refs),
                    dumps(candidate.failure_modes),
                    dumps(candidate.proposed_tests),
                    candidate.rollback_plan_ref,
                    candidate.registry_status,
                    candidate.review_status,
                    candidate.activation_status,
                    dumps(candidate.blockers),
                    candidate.sandbox_required,
                    candidate.human_review_required,
                    candidate.automatic_activation_allowed,
                    candidate.automatic_promotion_allowed,
                    candidate.core_mutation_allowed,
                    candidate.memory_write_mode,
                    candidate.timestamp,
                ),
            )
            connection.commit()

    def fetch_skill_candidate(
        self,
        skill_candidate_id: str,
    ) -> StoredSkillCandidate | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM skill_candidates
                WHERE skill_candidate_id = %s
                """,
                (skill_candidate_id,),
            )
            row = cursor.fetchone()
        return _stored_skill_candidate_from_row(row) if row is not None else None

    def list_skill_candidates(
        self,
        *,
        skill_id: str | None = None,
        version: str | None = None,
        domain: str | None = None,
        review_status: str | None = None,
        limit: int = 20,
    ) -> list[StoredSkillCandidate]:
        clauses: list[str] = []
        params: list[object] = []
        for column, value in (
            ("skill_id", skill_id),
            ("version", version),
            ("domain", domain),
            ("review_status", review_status),
        ):
            if value:
                clauses.append(f"{column} = %s")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT *
                FROM skill_candidates
                {where}
                ORDER BY timestamp DESC, skill_candidate_id ASC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        return [_stored_skill_candidate_from_row(row) for row in rows]

    def upsert_specialist_shared_memory(
        self,
        snapshot: StoredSpecialistSharedMemory,
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO specialist_shared_memory (
                    session_id, specialist_type, sharing_mode, continuity_mode,
                    shared_memory_brief, write_policy, user_id, consumer_mode,
                    source_mission_id, source_mission_goal, mission_context_brief,
                    domain_context_brief, continuity_context_brief, consumer_profile,
                    consumer_objective, expected_deliverables, telemetry_focus,
                    related_mission_ids, memory_refs, memory_class_policies,
                    consumed_memory_classes, memory_write_policies, semantic_focus,
                    open_loops, last_recommendation, semantic_memory_lifecycle,
                    procedural_memory_lifecycle, memory_lifecycle_status,
                    memory_review_status, procedural_artifact_status,
                    procedural_artifact_refs, procedural_artifact_version,
                    procedural_artifact_summary, domain_mission_link_reason,
                    recurrent_context_status, recurrent_interaction_count,
                    recurrent_context_brief, recurrent_domain_focus,
                    recurrent_memory_refs, recurrent_continuity_modes, updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (session_id, specialist_type) DO UPDATE SET
                    sharing_mode = EXCLUDED.sharing_mode,
                    continuity_mode = EXCLUDED.continuity_mode,
                    shared_memory_brief = EXCLUDED.shared_memory_brief,
                    write_policy = EXCLUDED.write_policy,
                    user_id = EXCLUDED.user_id,
                    consumer_mode = EXCLUDED.consumer_mode,
                    source_mission_id = EXCLUDED.source_mission_id,
                    source_mission_goal = EXCLUDED.source_mission_goal,
                    mission_context_brief = EXCLUDED.mission_context_brief,
                    domain_context_brief = EXCLUDED.domain_context_brief,
                    continuity_context_brief = EXCLUDED.continuity_context_brief,
                    consumer_profile = EXCLUDED.consumer_profile,
                    consumer_objective = EXCLUDED.consumer_objective,
                    expected_deliverables = EXCLUDED.expected_deliverables,
                    telemetry_focus = EXCLUDED.telemetry_focus,
                    related_mission_ids = EXCLUDED.related_mission_ids,
                    memory_refs = EXCLUDED.memory_refs,
                    memory_class_policies = EXCLUDED.memory_class_policies,
                    consumed_memory_classes = EXCLUDED.consumed_memory_classes,
                    memory_write_policies = EXCLUDED.memory_write_policies,
                    semantic_focus = EXCLUDED.semantic_focus,
                    open_loops = EXCLUDED.open_loops,
                    last_recommendation = EXCLUDED.last_recommendation,
                    semantic_memory_lifecycle = EXCLUDED.semantic_memory_lifecycle,
                    procedural_memory_lifecycle = EXCLUDED.procedural_memory_lifecycle,
                    memory_lifecycle_status = EXCLUDED.memory_lifecycle_status,
                    memory_review_status = EXCLUDED.memory_review_status,
                    procedural_artifact_status = EXCLUDED.procedural_artifact_status,
                    procedural_artifact_refs = EXCLUDED.procedural_artifact_refs,
                    procedural_artifact_version = EXCLUDED.procedural_artifact_version,
                    procedural_artifact_summary = EXCLUDED.procedural_artifact_summary,
                    domain_mission_link_reason = EXCLUDED.domain_mission_link_reason,
                    recurrent_context_status = EXCLUDED.recurrent_context_status,
                    recurrent_interaction_count = EXCLUDED.recurrent_interaction_count,
                    recurrent_context_brief = EXCLUDED.recurrent_context_brief,
                    recurrent_domain_focus = EXCLUDED.recurrent_domain_focus,
                    recurrent_memory_refs = EXCLUDED.recurrent_memory_refs,
                    recurrent_continuity_modes = EXCLUDED.recurrent_continuity_modes,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    snapshot.session_id,
                    snapshot.specialist_type,
                    snapshot.sharing_mode,
                    snapshot.continuity_mode,
                    snapshot.shared_memory_brief,
                    snapshot.write_policy,
                    snapshot.user_id,
                    snapshot.consumer_mode,
                    snapshot.source_mission_id,
                    snapshot.source_mission_goal,
                    snapshot.mission_context_brief,
                    snapshot.domain_context_brief,
                    snapshot.continuity_context_brief,
                    snapshot.consumer_profile,
                    snapshot.consumer_objective,
                    dumps(snapshot.expected_deliverables),
                    dumps(snapshot.telemetry_focus),
                    dumps(snapshot.related_mission_ids),
                    dumps(snapshot.memory_refs),
                    dumps(snapshot.memory_class_policies),
                    dumps(snapshot.consumed_memory_classes),
                    dumps(snapshot.memory_write_policies),
                    dumps(snapshot.semantic_focus),
                    dumps(snapshot.open_loops),
                    snapshot.last_recommendation,
                    snapshot.semantic_memory_lifecycle,
                    snapshot.procedural_memory_lifecycle,
                    snapshot.memory_lifecycle_status,
                    snapshot.memory_review_status,
                    snapshot.procedural_artifact_status,
                    dumps(snapshot.procedural_artifact_refs),
                    snapshot.procedural_artifact_version,
                    snapshot.procedural_artifact_summary,
                    snapshot.domain_mission_link_reason,
                    snapshot.recurrent_context_status,
                    snapshot.recurrent_interaction_count,
                    snapshot.recurrent_context_brief,
                    dumps(snapshot.recurrent_domain_focus),
                    dumps(snapshot.recurrent_memory_refs),
                    dumps(snapshot.recurrent_continuity_modes),
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
                       continuity_context_brief, consumer_profile, consumer_objective,
                       expected_deliverables, telemetry_focus, related_mission_ids, memory_refs,
                       memory_class_policies, consumed_memory_classes, memory_write_policies,
                       semantic_focus, open_loops, last_recommendation,
                       semantic_memory_lifecycle, procedural_memory_lifecycle,
                       memory_lifecycle_status, memory_review_status,
                       procedural_artifact_status, procedural_artifact_refs,
                       procedural_artifact_version, procedural_artifact_summary,
                       domain_mission_link_reason, recurrent_context_status,
                       recurrent_interaction_count, recurrent_context_brief,
                       recurrent_domain_focus, recurrent_memory_refs,
                       recurrent_continuity_modes
                FROM specialist_shared_memory
                WHERE session_id = %s
                  AND specialist_type = %s
                """,
                (session_id, specialist_type),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        lifecycle_support = memory_lifecycle_support_signals(
            semantic_lifecycle=row["semantic_memory_lifecycle"],
            procedural_lifecycle=row["procedural_memory_lifecycle"],
        )
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
            consumer_profile=row["consumer_profile"],
            consumer_objective=row["consumer_objective"],
            expected_deliverables=list(loads(row["expected_deliverables"] or "[]")),
            telemetry_focus=list(loads(row["telemetry_focus"] or "[]")),
            related_mission_ids=list(loads(row["related_mission_ids"] or "[]")),
            memory_refs=list(loads(row["memory_refs"] or "[]")),
            memory_class_policies=dict(loads(row["memory_class_policies"] or "{}")),
            consumed_memory_classes=list(loads(row["consumed_memory_classes"] or "[]")),
            memory_write_policies=dict(loads(row["memory_write_policies"] or "{}")),
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_recommendation=row["last_recommendation"],
            semantic_memory_lifecycle=row["semantic_memory_lifecycle"],
            procedural_memory_lifecycle=row["procedural_memory_lifecycle"],
            semantic_memory_state=str(lifecycle_support["semantic_memory_state"])
            if lifecycle_support["semantic_memory_state"] is not None
            else None,
            procedural_memory_state=str(lifecycle_support["procedural_memory_state"])
            if lifecycle_support["procedural_memory_state"] is not None
            else None,
            memory_lifecycle_status=row["memory_lifecycle_status"],
            memory_review_status=row["memory_review_status"],
            memory_consolidation_status=str(lifecycle_support["consolidation_status"]),
            memory_fixation_status=str(lifecycle_support["fixation_status"]),
            memory_archive_status=str(lifecycle_support["archive_status"]),
            procedural_artifact_status=row["procedural_artifact_status"],
            procedural_artifact_refs=list(loads(row["procedural_artifact_refs"] or "[]")),
            procedural_artifact_version=row["procedural_artifact_version"],
            procedural_artifact_summary=row["procedural_artifact_summary"],
            domain_mission_link_reason=row["domain_mission_link_reason"],
            recurrent_context_status=row["recurrent_context_status"] or "not_applicable",
            recurrent_interaction_count=int(row["recurrent_interaction_count"] or 0),
            recurrent_context_brief=row["recurrent_context_brief"],
            recurrent_domain_focus=list(loads(row["recurrent_domain_focus"] or "[]")),
            recurrent_memory_refs=list(loads(row["recurrent_memory_refs"] or "[]")),
            recurrent_continuity_modes=list(loads(row["recurrent_continuity_modes"] or "[]")),
        )

    def fetch_latest_specialist_shared_memory_for_user(
        self,
        *,
        user_id: str,
        specialist_type: str,
        exclude_session_id: str | None = None,
    ) -> SpecialistSharedMemoryContextContract | None:
        query = """
                SELECT session_id, specialist_type, sharing_mode, continuity_mode,
                       shared_memory_brief, write_policy, consumer_mode, source_mission_id,
                       source_mission_goal, mission_context_brief, domain_context_brief,
                       continuity_context_brief, consumer_profile, consumer_objective,
                       expected_deliverables, telemetry_focus, related_mission_ids, memory_refs,
                       memory_class_policies, consumed_memory_classes, memory_write_policies,
                       semantic_focus, open_loops, last_recommendation,
                       semantic_memory_lifecycle, procedural_memory_lifecycle,
                       memory_lifecycle_status, memory_review_status,
                       procedural_artifact_status, procedural_artifact_refs,
                       procedural_artifact_version, procedural_artifact_summary,
                       domain_mission_link_reason, recurrent_context_status,
                       recurrent_interaction_count, recurrent_context_brief,
                       recurrent_domain_focus, recurrent_memory_refs,
                       recurrent_continuity_modes
                FROM specialist_shared_memory
                WHERE user_id = %s
                  AND specialist_type = %s
        """
        params: list[str] = [user_id, specialist_type]
        if exclude_session_id is not None:
            query += "\n                  AND session_id <> %s"
            params.append(exclude_session_id)
        query += "\n                ORDER BY updated_at DESC\n                LIMIT 1"
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            row = cursor.fetchone()
        if row is None:
            return None
        lifecycle_support = memory_lifecycle_support_signals(
            semantic_lifecycle=row["semantic_memory_lifecycle"],
            procedural_lifecycle=row["procedural_memory_lifecycle"],
        )
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
            consumer_profile=row["consumer_profile"],
            consumer_objective=row["consumer_objective"],
            expected_deliverables=list(loads(row["expected_deliverables"] or "[]")),
            telemetry_focus=list(loads(row["telemetry_focus"] or "[]")),
            related_mission_ids=list(loads(row["related_mission_ids"] or "[]")),
            memory_refs=list(loads(row["memory_refs"] or "[]")),
            memory_class_policies=dict(loads(row["memory_class_policies"] or "{}")),
            consumed_memory_classes=list(loads(row["consumed_memory_classes"] or "[]")),
            memory_write_policies=dict(loads(row["memory_write_policies"] or "{}")),
            semantic_focus=list(loads(row["semantic_focus"] or "[]")),
            open_loops=list(loads(row["open_loops"] or "[]")),
            last_recommendation=row["last_recommendation"],
            semantic_memory_lifecycle=row["semantic_memory_lifecycle"],
            procedural_memory_lifecycle=row["procedural_memory_lifecycle"],
            semantic_memory_state=str(lifecycle_support["semantic_memory_state"])
            if lifecycle_support["semantic_memory_state"] is not None
            else None,
            procedural_memory_state=str(lifecycle_support["procedural_memory_state"])
            if lifecycle_support["procedural_memory_state"] is not None
            else None,
            memory_lifecycle_status=row["memory_lifecycle_status"],
            memory_review_status=row["memory_review_status"],
            memory_consolidation_status=str(lifecycle_support["consolidation_status"]),
            memory_fixation_status=str(lifecycle_support["fixation_status"]),
            memory_archive_status=str(lifecycle_support["archive_status"]),
            procedural_artifact_status=row["procedural_artifact_status"],
            procedural_artifact_refs=list(loads(row["procedural_artifact_refs"] or "[]")),
            procedural_artifact_version=row["procedural_artifact_version"],
            procedural_artifact_summary=row["procedural_artifact_summary"],
            domain_mission_link_reason=row["domain_mission_link_reason"],
            recurrent_context_status=row["recurrent_context_status"] or "not_applicable",
            recurrent_interaction_count=int(row["recurrent_interaction_count"] or 0),
            recurrent_context_brief=row["recurrent_context_brief"],
            recurrent_domain_focus=list(loads(row["recurrent_domain_focus"] or "[]")),
            recurrent_memory_refs=list(loads(row["recurrent_memory_refs"] or "[]")),
            recurrent_continuity_modes=list(loads(row["recurrent_continuity_modes"] or "[]")),
        )

    def fetch_mission_state(self, mission_id: str) -> MissionStateContract | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT mission_id, mission_goal, mission_status, checkpoints, active_tasks,
                       related_memories, related_artifacts, recent_plan_steps,
                       last_recommendation, semantic_brief, semantic_focus,
                       identity_continuity_brief, open_loops, last_decision_frame,
                       ecosystem_state_status, active_work_items, active_artifact_refs,
                       open_checkpoint_refs, surface_presence, ecosystem_state_summary,
                       project_ref, objective_ref, work_item_refs, work_items, checkpoint_refs,
                       artifact_refs, artifact_states, objective_status, next_action_ref,
                       linked_surface_ids, active_surface_id, last_surface_id,
                       surface_continuity_status, surface_identity_conflict_flags, updated_at
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
            ecosystem_state_status=row["ecosystem_state_status"],
            active_work_items=list(loads(row["active_work_items"] or "[]")),
            active_artifact_refs=list(loads(row["active_artifact_refs"] or "[]")),
            open_checkpoint_refs=list(loads(row["open_checkpoint_refs"] or "[]")),
            surface_presence=list(loads(row["surface_presence"] or "[]")),
            ecosystem_state_summary=row["ecosystem_state_summary"],
            project_ref=row["project_ref"],
            objective_ref=row["objective_ref"],
            work_item_refs=list(loads(row["work_item_refs"] or "[]")),
            work_items=_deserialize_work_items(
                row["work_items"], mission_id=str(row["mission_id"])
            ),
            checkpoint_refs=list(loads(row["checkpoint_refs"] or "[]")),
            artifact_refs=list(loads(row["artifact_refs"] or "[]")),
            artifact_states=_deserialize_artifact_states(
                row["artifact_states"], mission_id=str(row["mission_id"])
            ),
            objective_status=row["objective_status"],
            next_action_ref=row["next_action_ref"],
            linked_surface_ids=list(loads(row["linked_surface_ids"] or "[]")),
            active_surface_id=row["active_surface_id"],
            last_surface_id=row["last_surface_id"],
            surface_continuity_status=row["surface_continuity_status"],
            surface_identity_conflict_flags=list(
                loads(row["surface_identity_conflict_flags"] or "[]")
            ),
            updated_at=row["updated_at"],
        )

    def list_mission_states(
        self,
        *,
        limit: int,
        include_closed: bool = False,
    ) -> list[MissionStateContract]:
        clauses = ""
        params: list[object] = []
        if not include_closed:
            clauses = "WHERE mission_status NOT IN (%s, %s)"
            params.extend(
                [MissionStatus.COMPLETED.value, MissionStatus.CANCELED.value]
            )
        params.append(limit)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT mission_id
                FROM mission_states
                {clauses}
                ORDER BY updated_at DESC, mission_id ASC
                LIMIT %s
                """,
                tuple(params),
            )
            rows = cursor.fetchall()
        states = [
            self.fetch_mission_state(str(row["mission_id"])) for row in rows
        ]
        return [state for state in states if state is not None]

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

    def summarize_memory_corpus(self) -> MemoryCorpusSummary:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM user_scope_snapshots")
            user_scope_records = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(*) AS total FROM mission_states")
            mission_state_records = int(cursor.fetchone()["total"])
            cursor.execute("SELECT COUNT(*) AS total FROM specialist_shared_memory")
            specialist_context_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM mission_states WHERE semantic_brief IS NOT NULL)
                    + (
                        SELECT COUNT(*)
                        FROM specialist_shared_memory
                        WHERE consumed_memory_classes LIKE '%%"semantic"%%'
                    ) AS total
                """
            )
            semantic_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM mission_states
                        WHERE last_recommendation IS NOT NULL
                           OR recent_plan_steps <> '[]'
                    )
                    + (
                        SELECT COUNT(*)
                        FROM specialist_shared_memory
                        WHERE consumed_memory_classes LIKE '%%"procedural"%%'
                    ) AS total
                """
            )
            procedural_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE memory_lifecycle_status = 'retained'
                """
            )
            retained_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE memory_lifecycle_status = 'promoted'
                """
            )
            promoted_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE semantic_memory_lifecycle = 'aging'
                   OR procedural_memory_lifecycle = 'aging'
                """
            )
            aging_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE memory_review_status = 'review_recommended'
                """
            )
            review_recommended_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE semantic_memory_lifecycle = 'retained'
                   OR procedural_memory_lifecycle = 'retained'
                """
            )
            fixed_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE semantic_memory_lifecycle IN ('promoted', 'consolidating')
                   OR procedural_memory_lifecycle IN ('promoted', 'consolidating')
                """
            )
            operational_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE semantic_memory_lifecycle = 'aging'
                   OR procedural_memory_lifecycle = 'aging'
                """
            )
            archivable_records = int(cursor.fetchone()["total"])
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM specialist_shared_memory
                WHERE semantic_memory_lifecycle = 'consolidating'
                   OR procedural_memory_lifecycle = 'consolidating'
                """
            )
            consolidating_records = int(cursor.fetchone()["total"])
        return MemoryCorpusSummary(
            user_scope_records=user_scope_records,
            mission_state_records=mission_state_records,
            specialist_context_records=specialist_context_records,
            semantic_records=semantic_records,
            procedural_records=procedural_records,
            retained_records=retained_records,
            promoted_records=promoted_records,
            aging_records=aging_records,
            review_recommended_records=review_recommended_records,
            fixed_records=fixed_records,
            operational_records=operational_records,
            archivable_records=archivable_records,
            consolidating_records=consolidating_records,
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
                CREATE TABLE IF NOT EXISTS user_scope_snapshots (
                    user_id TEXT PRIMARY KEY,
                    context_status TEXT NOT NULL,
                    interaction_count INTEGER NOT NULL,
                    user_context_brief TEXT,
                    recent_intents TEXT NOT NULL DEFAULT '[]',
                    recent_domain_focus TEXT NOT NULL DEFAULT '[]',
                    active_mission_ids TEXT NOT NULL DEFAULT '[]',
                    recent_session_ids TEXT NOT NULL DEFAULT '[]',
                    last_recommended_task_type TEXT,
                    continuity_preference TEXT,
                    memory_refs TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reviewed_learning_guidance (
                    guidance_id TEXT PRIMARY KEY,
                    source_review_decision_id TEXT NOT NULL,
                    evolution_proposal_id TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    route TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    guidance_summary TEXT NOT NULL,
                    allowed_usage TEXT NOT NULL DEFAULT '[]',
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT,
                    timestamp TEXT NOT NULL,
                    expires_at TEXT,
                    automatic_promotion_allowed BOOLEAN NOT NULL,
                    core_mutation_allowed BOOLEAN NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_reviewed_learning_guidance_scope_timestamp
                ON reviewed_learning_guidance (workflow_profile, route, domain, timestamp)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_lifecycle_review_decisions (
                    review_decision_id TEXT PRIMARY KEY,
                    candidate_id TEXT NOT NULL,
                    maintenance_action TEXT NOT NULL,
                    decision_action TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    operator_ref TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT NOT NULL,
                    governance_assessment_id TEXT NOT NULL,
                    review_notes TEXT NOT NULL DEFAULT '[]',
                    execution_authorized BOOLEAN NOT NULL,
                    automatic_execution_allowed BOOLEAN NOT NULL,
                    core_mutation_allowed BOOLEAN NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_lifecycle_review_candidate_timestamp
                ON memory_lifecycle_review_decisions (candidate_id, timestamp)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS procedural_playbook_candidates (
                    playbook_candidate_id TEXT PRIMARY KEY,
                    procedure_name TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    route TEXT,
                    domain TEXT,
                    bounded_steps TEXT NOT NULL DEFAULT '[]',
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    source_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    source_reflection_refs TEXT NOT NULL DEFAULT '[]',
                    proposed_tests TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT,
                    risk_hint TEXT,
                    review_status TEXT NOT NULL,
                    blockers TEXT NOT NULL DEFAULT '[]',
                    human_review_required BOOLEAN NOT NULL,
                    automatic_promotion_allowed BOOLEAN NOT NULL,
                    core_mutation_allowed BOOLEAN NOT NULL,
                    memory_write_mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_procedural_playbook_candidates_scope_timestamp
                ON procedural_playbook_candidates (workflow_profile, review_status, timestamp)
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_candidates (
                    skill_candidate_id TEXT PRIMARY KEY,
                    skill_id TEXT NOT NULL,
                    skill_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    domain TEXT NOT NULL,
                    specialist_type TEXT NOT NULL,
                    inputs TEXT NOT NULL DEFAULT '[]',
                    outputs TEXT NOT NULL DEFAULT '[]',
                    allowed_tools TEXT NOT NULL DEFAULT '[]',
                    bounded_instructions TEXT NOT NULL DEFAULT '[]',
                    risk_level TEXT NOT NULL,
                    evidence_refs TEXT NOT NULL DEFAULT '[]',
                    source_pattern_refs TEXT NOT NULL DEFAULT '[]',
                    failure_modes TEXT NOT NULL DEFAULT '[]',
                    proposed_tests TEXT NOT NULL DEFAULT '[]',
                    rollback_plan_ref TEXT NOT NULL,
                    registry_status TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    activation_status TEXT NOT NULL,
                    blockers TEXT NOT NULL DEFAULT '[]',
                    sandbox_required BOOLEAN NOT NULL,
                    human_review_required BOOLEAN NOT NULL,
                    automatic_activation_allowed BOOLEAN NOT NULL,
                    automatic_promotion_allowed BOOLEAN NOT NULL,
                    core_mutation_allowed BOOLEAN NOT NULL,
                    memory_write_mode TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    UNIQUE (skill_id, version)
                )
                """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_skill_candidates_scope_timestamp
                ON skill_candidates (
                    workflow_profile, domain, review_status, timestamp
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
                    user_id TEXT,
                    consumer_mode TEXT NOT NULL DEFAULT 'baseline_shared_context',
                    source_mission_id TEXT,
                    source_mission_goal TEXT,
                    mission_context_brief TEXT,
                    domain_context_brief TEXT,
                    continuity_context_brief TEXT,
                    consumer_profile TEXT,
                    consumer_objective TEXT,
                    expected_deliverables TEXT NOT NULL DEFAULT '[]',
                    telemetry_focus TEXT NOT NULL DEFAULT '[]',
                    related_mission_ids TEXT NOT NULL DEFAULT '[]',
                    memory_refs TEXT NOT NULL DEFAULT '[]',
                    memory_class_policies TEXT NOT NULL DEFAULT '{}',
                    consumed_memory_classes TEXT NOT NULL DEFAULT '[]',
                    memory_write_policies TEXT NOT NULL DEFAULT '{}',
                    semantic_focus TEXT NOT NULL DEFAULT '[]',
                    open_loops TEXT NOT NULL DEFAULT '[]',
                    last_recommendation TEXT,
                    semantic_memory_lifecycle TEXT,
                    procedural_memory_lifecycle TEXT,
                    memory_lifecycle_status TEXT,
                    memory_review_status TEXT,
                    procedural_artifact_status TEXT,
                    procedural_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    procedural_artifact_version INTEGER,
                    procedural_artifact_summary TEXT,
                    domain_mission_link_reason TEXT,
                    recurrent_context_status TEXT NOT NULL DEFAULT 'not_applicable',
                    recurrent_interaction_count INTEGER NOT NULL DEFAULT 0,
                    recurrent_context_brief TEXT,
                    recurrent_domain_focus TEXT NOT NULL DEFAULT '[]',
                    recurrent_memory_refs TEXT NOT NULL DEFAULT '[]',
                    recurrent_continuity_modes TEXT NOT NULL DEFAULT '[]',
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
                    ecosystem_state_status TEXT,
                    active_work_items TEXT NOT NULL DEFAULT '[]',
                    active_artifact_refs TEXT NOT NULL DEFAULT '[]',
                    open_checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    surface_presence TEXT NOT NULL DEFAULT '[]',
                    ecosystem_state_summary TEXT,
                    project_ref TEXT,
                    objective_ref TEXT,
                    work_item_refs TEXT NOT NULL DEFAULT '[]',
                    checkpoint_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_refs TEXT NOT NULL DEFAULT '[]',
                    artifact_states TEXT NOT NULL DEFAULT '[]',
                    objective_status TEXT,
                    next_action_ref TEXT,
                    linked_surface_ids TEXT NOT NULL DEFAULT '[]',
                    active_surface_id TEXT,
                    last_surface_id TEXT,
                    surface_continuity_status TEXT,
                    surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]',
                    work_items TEXT NOT NULL DEFAULT '[]',
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
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS ecosystem_state_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "active_work_items TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "work_items TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "artifact_states TEXT NOT NULL DEFAULT '[]'"
            )
            for column_definition in (
                "project_ref TEXT",
                "objective_ref TEXT",
                "work_item_refs TEXT NOT NULL DEFAULT '[]'",
                "checkpoint_refs TEXT NOT NULL DEFAULT '[]'",
                "artifact_refs TEXT NOT NULL DEFAULT '[]'",
                "objective_status TEXT",
                "next_action_ref TEXT",
            ):
                cursor.execute(
                    "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                    + column_definition
                )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "active_artifact_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "open_checkpoint_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS "
                "surface_presence TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE mission_states ADD COLUMN IF NOT EXISTS ecosystem_state_summary TEXT"
            )
            for table_name in (
                "mission_states",
                "session_continuity",
                "continuity_checkpoints",
            ):
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "
                    "linked_surface_ids TEXT NOT NULL DEFAULT '[]'"
                )
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS active_surface_id TEXT"
                )
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS last_surface_id TEXT"
                )
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "
                    "surface_continuity_status TEXT"
                )
                cursor.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "
                    "surface_identity_conflict_flags TEXT NOT NULL DEFAULT '[]'"
                )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "ecosystem_state_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "active_work_items TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "active_artifact_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "open_checkpoint_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "surface_presence TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE session_continuity ADD COLUMN IF NOT EXISTS "
                "ecosystem_state_summary TEXT"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "ecosystem_state_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "active_work_items TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "active_artifact_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "open_checkpoint_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "surface_presence TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE continuity_checkpoints ADD COLUMN IF NOT EXISTS "
                "ecosystem_state_summary TEXT"
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
                "consumed_memory_classes TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "memory_write_policies TEXT NOT NULL DEFAULT '{}'"
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
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "consumer_profile TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "consumer_objective TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "expected_deliverables TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "telemetry_focus TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "domain_mission_link_reason TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "semantic_memory_lifecycle TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "procedural_memory_lifecycle TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "memory_lifecycle_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "memory_review_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "procedural_artifact_status TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "procedural_artifact_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "procedural_artifact_version INTEGER"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "procedural_artifact_summary TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS user_id TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_context_status TEXT NOT NULL DEFAULT 'not_applicable'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_interaction_count INTEGER NOT NULL DEFAULT 0"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_context_brief TEXT"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_domain_focus TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_memory_refs TEXT NOT NULL DEFAULT '[]'"
            )
            cursor.execute(
                "ALTER TABLE specialist_shared_memory ADD COLUMN IF NOT EXISTS "
                "recurrent_continuity_modes TEXT NOT NULL DEFAULT '[]'"
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
        ecosystem_state_status=checkpoint.ecosystem_state_status,
        active_work_items=list(checkpoint.active_work_items),
        active_artifact_refs=list(checkpoint.active_artifact_refs),
        open_checkpoint_refs=list(checkpoint.open_checkpoint_refs),
        surface_presence=list(checkpoint.surface_presence),
        ecosystem_state_summary=checkpoint.ecosystem_state_summary,
        project_ref=checkpoint.project_ref,
        objective_ref=checkpoint.objective_ref,
        work_item_refs=list(checkpoint.work_item_refs),
        checkpoint_refs=list(checkpoint.checkpoint_refs),
        artifact_refs=list(checkpoint.artifact_refs),
        objective_status=checkpoint.objective_status,
        next_action_ref=checkpoint.next_action_ref,
        linked_surface_ids=list(checkpoint.linked_surface_ids),
        active_surface_id=checkpoint.active_surface_id,
        last_surface_id=checkpoint.last_surface_id,
        surface_continuity_status=checkpoint.surface_continuity_status,
        surface_identity_conflict_flags=list(checkpoint.surface_identity_conflict_flags),
        updated_at=checkpoint.updated_at,
    )
