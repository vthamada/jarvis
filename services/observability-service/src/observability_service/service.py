# ruff: noqa: E501
"""Structured local observability service."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from observability_service.agentic import (
    AgenticObservabilityAdapter,
    JsonlAgenticMirrorAdapter,
    LangSmithObservabilityAdapter,
)
from observability_service.repository import ObservabilityRepository
from shared.events import InternalEventEnvelope


@dataclass(frozen=True)
class FlowMetrics:
    """Minimal correlated metrics for a traced flow."""

    total_events: int
    blocked_events: int
    completed_operations: int
    memory_writes: int
    error_events: int
    duration_seconds: float


@dataclass(frozen=True)
class ObservabilityQuery:
    """Query filters for recent event inspection."""

    limit: int = 20
    request_id: str | None = None
    session_id: str | None = None
    mission_id: str | None = None
    correlation_id: str | None = None
    operation_id: str | None = None


class ObservabilityService:
    """Collect and query structured telemetry from orchestrated flows."""

    name = "observability-service"

    def __init__(
        self,
        database_path: str | None = None,
        agentic_adapter: AgenticObservabilityAdapter | None = None,
    ) -> None:
        runtime_path = database_path or getenv("JARVIS_OBSERVABILITY_DB")
        resolved = (
            Path(runtime_path)
            if runtime_path
            else Path.cwd() / ".jarvis_runtime" / "observability.db"
        )
        self.repository = ObservabilityRepository(resolved)
        self.agentic_adapter = agentic_adapter or self._build_agentic_adapter()

    def ingest_events(self, events: list[InternalEventEnvelope]) -> None:
        """Persist the event trail for later inspection."""

        for event in events:
            self.repository.record_event(event)
        if self.agentic_adapter is not None:
            self.agentic_adapter.emit(events)

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
            operation_id=filters.operation_id,
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

    def summarize_flow(self, query: ObservabilityQuery) -> FlowMetrics:
        """Summarize a correlated request/session/mission flow for governance and evolution."""

        events = self.list_recent_events(query)
        if not events:
            return FlowMetrics(
                total_events=0,
                blocked_events=0,
                completed_operations=0,
                memory_writes=0,
                error_events=0,
                duration_seconds=0.0,
            )
        timestamps = [event.timestamp for event in events]
        duration = 0.0
        if len(timestamps) > 1:
            from datetime import datetime

            started = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration = round((ended - started).total_seconds(), 4)
        return FlowMetrics(
            total_events=len(events),
            blocked_events=sum(1 for event in events if event.event_name == "governance_blocked"),
            completed_operations=sum(
                1 for event in events if event.event_name == "operation_completed"
            ),
            memory_writes=sum(1 for event in events if event.event_name == "memory_recorded"),
            error_events=sum(1 for event in events if event.event_name == "error_raised"),
            duration_seconds=duration,
        )

    @staticmethod
    def _build_agentic_adapter() -> AgenticObservabilityAdapter | None:
        tracing_enabled = getenv("LANGSMITH_TRACING", "false").lower() == "true"
        if not tracing_enabled:
            return None
        project_name = getenv("LANGSMITH_PROJECT", "jarvis-v1")
        if getenv("LANGSMITH_API_KEY"):
            try:
                return LangSmithObservabilityAdapter(project_name=project_name)
            except Exception:
                pass
        mirror_path = getenv("JARVIS_AGENTIC_MIRROR_PATH")
        resolved = (
            Path(mirror_path)
            if mirror_path
            else Path.cwd() / ".jarvis_runtime" / "agentic_observability.jsonl"
        )
        return JsonlAgenticMirrorAdapter(resolved)

