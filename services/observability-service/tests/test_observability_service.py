from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.events import InternalEventEnvelope


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_observability_service_name() -> None:
    assert ObservabilityService.name == "observability-service"


def test_observability_service_persists_and_filters_events() -> None:
    temp_dir = runtime_dir("observability")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    events = [
        InternalEventEnvelope(
            event_id="evt-1",
            event_name="input_received",
            timestamp="2026-03-18T00:00:00Z",
            source_service="orchestrator-service",
            payload={"content": "hello"},
            request_id="req-1",
            session_id="sess-1",
            correlation_id="req-1",
        ),
        InternalEventEnvelope(
            event_id="evt-2",
            event_name="memory_recorded",
            timestamp="2026-03-18T00:00:01Z",
            source_service="orchestrator-service",
            payload={"record": "ok"},
            request_id="req-2",
            session_id="sess-2",
            correlation_id="req-2",
        ),
    ]

    service.ingest_events(events)
    filtered = service.list_recent_events(ObservabilityQuery(request_id="req-1"))

    assert len(filtered) == 1
    assert filtered[0].event_name == "input_received"


def test_observability_service_exports_trace_view() -> None:
    temp_dir = runtime_dir("observability-export")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:02Z",
                source_service="orchestrator-service",
                payload={"intent": "planning", "status": "ok"},
                request_id="req-3",
                session_id="sess-3",
                correlation_id="req-3",
            )
        ]
    )

    trace_view = service.export_trace_view(ObservabilityQuery(request_id="req-3"))

    assert len(trace_view) == 1
    assert trace_view[0]["name"] == "response_synthesized"
    assert trace_view[0]["payload_keys"] == ["intent", "status"]
