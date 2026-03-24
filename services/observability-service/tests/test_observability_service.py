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
    assert "continuity_decided" in audit.missing_required_events
    assert "operation_missing_completion" in audit.anomaly_flags
    assert "continuity_decided" in audit.missing_continuity_signals
    assert audit.trace_complete is False


def test_observability_service_audits_continuity_signals() -> None:
    temp_dir = runtime_dir("observability-continuity")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-c1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "retomar_missao_relacionada"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"active_minds": ["mente_analitica"]},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar", "continuity_source": "related_mission"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c6",
                event_name="continuity_subflow_completed",
                timestamp="2026-03-18T00:00:04.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "langgraph_subflow",
                    "subflow_name": "continuity_stateful",
                },
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c6b",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "retomar",
                    "continuity_source": "related_mission",
                },
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-cont"))

    assert audit.continuity_action == "retomar"
    assert audit.continuity_source == "related_mission"
    assert audit.continuity_runtime_mode == "langgraph_subflow"
    assert audit.continuity_trace_status == "attention_required"
    assert "retomar_missing_target_mission" in audit.continuity_anomaly_flags
    assert "memory_continuity_mismatch" in audit.continuity_anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_audits_domain_memory_and_sovereignty_alignment() -> None:
    temp_dir = runtime_dir("observability-specialist-alignment")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-s1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze the Python service rollout."},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s4",
                event_name="domain_registry_resolved",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_domains": ["software_development", "analysis"],
                    "registry_domains": [
                        "computacao_e_desenvolvimento",
                        "dados_estatistica_e_inteligencia_analitica",
                        "tomada_de_decisao_complexa",
                    ],
                    "shadow_domains": ["software_development"],
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s5",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"active_minds": ["mente_analitica"]},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s6",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s7",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "especialista_software_subordinado": "core_mediated_read_only"
                    }
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s9",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "response_channel": "through_core",
                    "tool_access_mode": "none",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s10",
                event_name="specialist_shadow_mode_completed",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["especialista_software_subordinado"],
                    "linked_domains": {
                        "especialista_software_subordinado": "software_development"
                    },
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s11",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s12",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s13",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:12+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-specialist-align"))

    assert audit.registry_domains == [
        "computacao_e_desenvolvimento",
        "dados_estatistica_e_inteligencia_analitica",
        "tomada_de_decisao_complexa",
    ]
    assert audit.shadow_specialists == ["especialista_software_subordinado"]
    assert audit.domain_alignment_status == "healthy"
    assert audit.memory_alignment_status == "healthy"
    assert audit.specialist_sovereignty_status == "healthy"


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

def test_observability_service_builds_incident_evidence_for_governed_flow() -> None:
    temp_dir = runtime_dir("observability-incident")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-i1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "delete records"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
            InternalEventEnvelope(
                event_id="evt-i2",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"decision": "block"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
            InternalEventEnvelope(
                event_id="evt-i3",
                event_name="governance_blocked",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"justification": "blocked"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
        ]
    )

    evidence = service.build_incident_evidence(ObservabilityQuery(request_id="req-incident"))

    assert evidence.request_id == "req-incident"
    assert evidence.governance_decision == "block"
    assert evidence.recommended_operator_action == "keep_contained_and_require_manual_review"
    assert "memory_recovered" in evidence.missing_required_events
