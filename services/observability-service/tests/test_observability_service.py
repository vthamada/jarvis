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
