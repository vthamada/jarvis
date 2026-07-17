"""Canonical event metadata and envelopes."""

from dataclasses import dataclass, field

from shared.types import Timestamp

INTERNAL_EVENT_NAMES = (
    "input_received",
    "intent_classified",
    "context_composed",
    "knowledge_retrieved",
    "memory_recovered",
    "memory_influence_governed",
    "memory_recorded",
    "surface_identity_declared",
    "ecosystem_state_declared",
    "objective_state_declared",
    "objective_state_inspected",
    "long_horizon_goal_strategy_declared",
    "mission_progress_report_generated",
    "work_item_state_changed",
    "artifact_lifecycle_state_changed",
    "technology_absorption_candidate_declared",
    "experience_record_declared",
    "post_task_reflection_declared",
    "operator_feedback_recorded",
    "evolution_review_decision_declared",
    "reviewed_learning_guidance_declared",
    "promotion_gate_evaluated",
    "autonomy_ladder_declared",
    "operation_dispatched",
    "operation_completed",
    "governance_checked",
    "governance_blocked",
    "mission_updated",
    "response_synthesized",
    "error_raised",
)


@dataclass
class InternalEventEnvelope:
    event_id: str
    event_name: str
    timestamp: Timestamp
    source_service: str
    payload: dict[str, object]
    correlation_id: str | None = None
    request_id: str | None = None
    session_id: str | None = None
    mission_id: str | None = None
    operation_id: str | None = None
    tags: list[str] = field(default_factory=list)
