"""Optional agentic observability adapters for v1 controlled operation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from json import dumps
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from shared.events import InternalEventEnvelope

try:
    from langsmith import Client
except ImportError:  # pragma: no cover - depends on optional environment packages.
    Client = None


class AgenticObservabilityAdapter(ABC):
    """Mirror selected observability events to an agentic sink."""

    @abstractmethod
    def emit(self, events: list[InternalEventEnvelope]) -> None:
        """Mirror the provided events without affecting the local observability path."""


class JsonlAgenticMirrorAdapter(AgenticObservabilityAdapter):
    """Persist a JSONL mirror of the event trail for controlled validation."""

    def __init__(self, mirror_path: Path) -> None:
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        self.mirror_path = mirror_path

    def emit(self, events: list[InternalEventEnvelope]) -> None:
        with self.mirror_path.open("a", encoding="utf-8") as stream:
            grouped = LangSmithObservabilityAdapter._group_events(events)
            for trace_key, grouped_events in grouped.items():
                ordered_events = sorted(
                    grouped_events,
                    key=lambda item: (item.timestamp, item.event_id),
                )
                root_event = ordered_events[0]
                stream.write(
                    dumps(
                        {
                            "name": "jarvis_trace",
                            "trace_key": trace_key,
                            "request_id": root_event.request_id,
                            "session_id": root_event.session_id,
                            "mission_id": root_event.mission_id,
                            "correlation_id": root_event.correlation_id,
                            "operation_id": root_event.operation_id,
                            "source_service": "jarvis",
                            "event_names": [event.event_name for event in ordered_events],
                            "total_events": len(ordered_events),
                        },
                        ensure_ascii=True,
                    )
                    + "\n"
                )
                for event in ordered_events:
                    stream.write(
                        dumps(
                            {
                                "name": event.event_name,
                                "event_id": event.event_id,
                                "timestamp": event.timestamp,
                                "source_service": event.source_service,
                                "payload": event.payload,
                                "correlation_id": event.correlation_id,
                                "request_id": event.request_id,
                                "session_id": event.session_id,
                                "mission_id": event.mission_id,
                                "operation_id": event.operation_id,
                                "tags": event.tags,
                            },
                            ensure_ascii=True,
                        )
                        + "\n"
                    )


class LangSmithObservabilityAdapter(AgenticObservabilityAdapter):
    """Mirror event envelopes to LangSmith when the SDK is available."""

    def __init__(
        self,
        *,
        client: object | None = None,
        project_name: str = "jarvis-v1",
        endpoint: str | None = None,
        workspace_id: str | None = None,
    ) -> None:
        if client is None and Client is None:  # pragma: no cover - depends on optional packages.
            raise RuntimeError("langsmith package is required for LangSmith observability.")
        self.client = client or Client(api_url=endpoint, workspace_id=workspace_id)
        self.project_name = project_name

    def emit(self, events: list[InternalEventEnvelope]) -> None:
        if not events:
            return
        for trace_key, grouped_events in self._group_events(events).items():
            ordered_events = sorted(
                grouped_events,
                key=lambda item: (item.timestamp, item.event_id),
            )
            trace_id = str(uuid5(NAMESPACE_URL, f"jarvis-trace:{trace_key}"))
            root_event = ordered_events[0]
            root_order = f"{self._timestamp_token(root_event.timestamp)}{trace_id.replace('-', '')}"
            self.client.create_run(
                id=trace_id,
                trace_id=trace_id,
                dotted_order=root_order,
                name="jarvis_trace",
                run_type="chain",
                inputs={
                    "trace_key": trace_key,
                    "request_id": root_event.request_id,
                    "session_id": root_event.session_id,
                    "mission_id": root_event.mission_id,
                    "correlation_id": root_event.correlation_id,
                },
                outputs={
                    "total_events": len(ordered_events),
                    "event_names": [event.event_name for event in ordered_events],
                    "final_event": ordered_events[-1].event_name,
                },
                start_time=self._parse_timestamp(root_event.timestamp),
                end_time=self._parse_timestamp(ordered_events[-1].timestamp),
                project_name=self.project_name,
                tags=["jarvis", "trace_root"],
                extra={
                    "metadata": {
                        "request_id": root_event.request_id,
                        "session_id": root_event.session_id,
                        "mission_id": root_event.mission_id,
                        "operation_id": root_event.operation_id,
                        "correlation_id": root_event.correlation_id,
                        "source_services": sorted(
                            {event.source_service for event in ordered_events}
                        ),
                    }
                },
            )
            for event in ordered_events:
                event_id = str(uuid5(NAMESPACE_URL, f"jarvis-event:{event.event_id}"))
                self.client.create_run(
                    id=event_id,
                    trace_id=trace_id,
                    parent_run_id=trace_id,
                    dotted_order=(
                        f"{root_order}."
                        f"{self._timestamp_token(event.timestamp)}{event_id.replace('-', '')}"
                    ),
                    name=event.event_name,
                    run_type=self._run_type_for_event(event),
                    inputs={
                        "payload": event.payload,
                        "request_id": event.request_id,
                        "session_id": event.session_id,
                        "mission_id": event.mission_id,
                        "operation_id": event.operation_id,
                    },
                    outputs={
                        "event_name": event.event_name,
                        "payload_keys": sorted(event.payload.keys()),
                    },
                    start_time=self._parse_timestamp(event.timestamp),
                    end_time=self._parse_timestamp(event.timestamp),
                    project_name=self.project_name,
                    tags=self._tags_for_event(event),
                    extra={
                        "metadata": {
                            "event_id": event.event_id,
                            "request_id": event.request_id,
                            "session_id": event.session_id,
                            "mission_id": event.mission_id,
                            "operation_id": event.operation_id,
                            "correlation_id": event.correlation_id,
                            "source_service": event.source_service,
                            "payload_keys": sorted(event.payload.keys()),
                            "tags": event.tags,
                        }
                    },
                )

    @staticmethod
    def _group_events(
        events: list[InternalEventEnvelope],
    ) -> dict[str, list[InternalEventEnvelope]]:
        grouped: dict[str, list[InternalEventEnvelope]] = {}
        for event in events:
            trace_key = (
                event.request_id
                or event.correlation_id
                or event.session_id
                or event.mission_id
                or event.event_id
            )
            grouped.setdefault(trace_key, []).append(event)
        return grouped

    @staticmethod
    def _run_type_for_event(event: InternalEventEnvelope) -> str:
        if event.event_name == "knowledge_retrieved":
            return "retriever"
        if event.event_name in {"operation_dispatched", "operation_completed"}:
            return "tool"
        return "chain"

    @staticmethod
    def _tags_for_event(event: InternalEventEnvelope) -> list[str]:
        tags = [
            "jarvis",
            f"event:{event.event_name}",
            f"service:{event.source_service}",
        ]
        tags.extend(event.tags)
        return list(dict.fromkeys(tags))

    @staticmethod
    def _parse_timestamp(timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)

    @classmethod
    def _timestamp_token(cls, timestamp: str) -> str:
        return cls._parse_timestamp(timestamp).strftime("%Y%m%dT%H%M%S%fZ")
