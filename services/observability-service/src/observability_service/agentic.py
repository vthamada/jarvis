"""Optional agentic observability adapters for v1 controlled operation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from json import dumps
from pathlib import Path

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
            for event in events:
                stream.write(
                    dumps(
                        {
                            "event_id": event.event_id,
                            "event_name": event.event_name,
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

    def __init__(self, *, client: object | None = None, project_name: str = "jarvis-v1") -> None:
        if client is None and Client is None:  # pragma: no cover - depends on optional packages.
            raise RuntimeError("langsmith package is required for LangSmith observability.")
        self.client = client or Client()
        self.project_name = project_name

    def emit(self, events: list[InternalEventEnvelope]) -> None:
        for event in events:
            self.client.create_run(
                name=event.event_name,
                run_type="chain",
                inputs={
                    "payload": event.payload,
                    "request_id": event.request_id,
                    "session_id": event.session_id,
                    "mission_id": event.mission_id,
                    "operation_id": event.operation_id,
                },
                project_name=self.project_name,
                extra={
                    "metadata": {
                        "event_id": event.event_id,
                        "source_service": event.source_service,
                        "correlation_id": event.correlation_id,
                        "tags": event.tags,
                    }
                },
            )
