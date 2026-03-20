from json import loads
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.agentic import JsonlAgenticMirrorAdapter, LangSmithObservabilityAdapter
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
            operation_id="op-1",
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
    assert filtered[0].operation_id == "op-1"


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


def test_observability_service_mirrors_events_to_agentic_adapter() -> None:
    temp_dir = runtime_dir("observability-agentic")
    mirror_path = temp_dir / "agentic.jsonl"
    service = ObservabilityService(
        database_path=str(temp_dir / "observability.db"),
        agentic_adapter=JsonlAgenticMirrorAdapter(mirror_path),
    )
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:03Z",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-4",
                session_id="sess-4",
                correlation_id="req-4",
                operation_id="op-4",
            )
        ]
    )

    mirrored_lines = mirror_path.read_text(encoding="utf-8").splitlines()
    assert len(mirrored_lines) == 2
    root_event = loads(mirrored_lines[0])
    mirrored_event = loads(mirrored_lines[1])
    assert root_event["name"] == "jarvis_trace"
    assert root_event["total_events"] == 1
    assert mirrored_event["name"] == "response_synthesized"
    assert mirrored_event["operation_id"] == "op-4"


def test_observability_service_summarizes_flow_metrics() -> None:
    temp_dir = runtime_dir("observability-metrics")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "hello"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"status": "completed"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
                operation_id="op-5",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"record": "ok"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
            ),
        ]
    )

    metrics = service.summarize_flow(ObservabilityQuery(request_id="req-5"))

    assert metrics.total_events == 3
    assert metrics.completed_operations == 1
    assert metrics.memory_writes == 1
    assert metrics.duration_seconds == 3.0


def test_observability_service_audits_flow_for_missing_events_and_anomalies() -> None:
    temp_dir = runtime_dir("observability-audit")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-a1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
            ),
            InternalEventEnvelope(
                event_id="evt-a2",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
            ),
            InternalEventEnvelope(
                event_id="evt-a3",
                event_name="operation_dispatched",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"operation_id": "op-audit"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
                operation_id="op-audit",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-audit"))

    assert audit.request_id == "req-audit"
    assert "memory_recovered" in audit.missing_required_events
    assert "operation_missing_completion" in audit.anomaly_flags
    assert audit.trace_complete is False


def test_langsmith_adapter_emits_trace_tree() -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def create_run(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            calls.append(kwargs)

    adapter = LangSmithObservabilityAdapter(client=FakeClient(), project_name="jarvis-test")
    adapter.emit(
        [
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "hello"},
                request_id="req-8",
                session_id="sess-8",
                correlation_id="req-8",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"status": "completed"},
                request_id="req-8",
                session_id="sess-8",
                correlation_id="req-8",
                operation_id="op-8",
            ),
        ]
    )

    assert len(calls) == 3
    root_run, first_child, second_child = calls
    assert root_run["name"] == "jarvis_trace"
    assert root_run["id"] == root_run["trace_id"]
    assert root_run["outputs"]["total_events"] == 2
    assert root_run["extra"]["metadata"]["request_id"] == "req-8"
    assert first_child["parent_run_id"] == root_run["id"]
    assert first_child["trace_id"] == root_run["trace_id"]
    assert first_child["extra"]["metadata"]["event_id"] == "evt-8"
    assert second_child["run_type"] == "tool"
    assert second_child["extra"]["metadata"]["operation_id"] == "op-8"


def test_langsmith_adapter_groups_events_by_request() -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def create_run(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            calls.append(kwargs)

    adapter = LangSmithObservabilityAdapter(client=FakeClient(), project_name="jarvis-test")
    adapter.emit(
        [
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "a"},
                request_id="req-a",
                session_id="sess-a",
                correlation_id="req-a",
            ),
            InternalEventEnvelope(
                event_id="evt-11",
                event_name="input_received",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"content": "b"},
                request_id="req-b",
                session_id="sess-b",
                correlation_id="req-b",
            ),
        ]
    )

    root_runs = [call for call in calls if call["name"] == "jarvis_trace"]
    child_runs = [call for call in calls if call["name"] != "jarvis_trace"]
    assert len(root_runs) == 2
    assert len(child_runs) == 2
    root_ids = {call["id"] for call in root_runs}
    assert all(call["parent_run_id"] in root_ids for call in child_runs)
