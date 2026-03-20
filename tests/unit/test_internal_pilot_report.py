from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.internal_pilot_report import render_text, summarize_traces


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_internal_pilot_report_summarizes_recent_request() -> None:
    database_path = runtime_dir("pilot-report") / "observability.db"
    service = ObservabilityService(database_path=str(database_path))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-1",
                event_name="input_received",
                timestamp="2026-03-19T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-pilot",
                session_id="sess-pilot",
                correlation_id="req-pilot",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="governance_checked",
                timestamp="2026-03-19T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-pilot",
                session_id="sess-pilot",
                correlation_id="req-pilot",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="operation_completed",
                timestamp="2026-03-19T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"status": "completed"},
                request_id="req-pilot",
                session_id="sess-pilot",
                correlation_id="req-pilot",
                operation_id="op-pilot",
            ),
        ]
    )

    summaries = summarize_traces(str(database_path), limit=5)

    assert len(summaries) == 1
    assert summaries[0].request_id == "req-pilot"
    assert summaries[0].governance_decision == "allow_with_conditions"
    assert summaries[0].operation_status == "completed"
    assert "plan_built" in summaries[0].missing_required_events


def test_internal_pilot_report_renders_text() -> None:
    rendered = render_text(
        [
            type(
                "PilotTraceSummaryStub",
                (),
                {
                    "request_id": "req-x",
                    "session_id": "sess-x",
                    "mission_id": None,
                    "total_events": 3,
                    "event_names": ["input_received"],
                    "missing_required_events": ["plan_built"],
                    "governance_decision": "allow",
                    "operation_status": "completed",
                    "duration_seconds": 2.0,
                },
            )()
        ]
    )

    assert "request_id=req-x" in rendered
    assert "missing_required_events=plan_built" in rendered
