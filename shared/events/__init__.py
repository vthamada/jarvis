"""Canonical event metadata and envelopes."""

from dataclasses import dataclass, field

from shared.types import Timestamp


INTERNAL_EVENT_NAMES = (
    "input_received",
    "intent_classified",
    "context_composed",
    "memory_recovered",
    "memory_recorded",
    "operation_dispatched",
    "operation_completed",
    "governance_checked",
    "governance_blocked",
    "mission_updated",
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
    tags: list[str] = field(default_factory=list)
