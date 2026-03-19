# ruff: noqa: E501
"""Structured local observability service."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from observability_service.repository import ObservabilityRepository
from shared.events import InternalEventEnvelope


@dataclass(frozen=True)
class ObservabilityQuery:
    """Query filters for recent event inspection."""

    limit: int = 20
    request_id: str | None = None
    session_id: str | None = None
    mission_id: str | None = None
    correlation_id: str | None = None


class ObservabilityService:
    """Collect and query structured telemetry from orchestrated flows."""

    name = "observability-service"

    def __init__(self, database_path: str | None = None) -> None:
        runtime_path = database_path or getenv("JARVIS_OBSERVABILITY_DB")
        resolved = (
            Path(runtime_path)
            if runtime_path
            else Path.cwd() / ".jarvis_runtime" / "observability.db"
        )
        self.repository = ObservabilityRepository(resolved)

    def ingest_events(self, events: list[InternalEventEnvelope]) -> None:
        """Persist the event trail for later inspection."""

        for event in events:
            self.repository.record_event(event)

    def list_recent_events(
        self, query: ObservabilityQuery | None = None
    ) -> list[InternalEventEnvelope]:
        """Return recent events filtered by the most relevant correlation fields."""

        filters = query or ObservabilityQuery()
        return self.repository.list_events(
            limit=filters.limit,
            request_id=filters.request_id,
            session_id=filters.session_id,
            mission_id=filters.mission_id,
            correlation_id=filters.correlation_id,
        )

    def export_trace_view(self, query: ObservabilityQuery | None = None) -> list[dict[str, object]]:
        """Return a trace-friendly projection of the stored internal events."""

        events = self.list_recent_events(query)
        return [
            {
                "span_id": event.event_id,
                "name": event.event_name,
                "timestamp": event.timestamp,
                "service": event.source_service,
                "request_id": event.request_id,
                "session_id": event.session_id,
                "mission_id": event.mission_id,
                "correlation_id": event.correlation_id,
                "tags": list(event.tags),
                "payload_keys": sorted(event.payload.keys()),
            }
            for event in events
        ]

