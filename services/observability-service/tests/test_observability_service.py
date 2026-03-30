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
    assert audit.workflow_trace_status == "not_applicable"
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
                payload={
                    "active_minds": ["mente_analitica", "mente_logica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_logica", "mente_critica"],
                    "suppressed_minds": ["mente_probabilistica"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente_analitica lidera a resposta com apoio de "
                        "mente_logica, mente_critica"
                    ),
                    "arbitration_source": "mind_registry",
                },
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
    assert audit.workflow_trace_status == "not_applicable"
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
                event_id="evt-s3b",
                event_name="directive_composed",
                timestamp="2026-03-18T00:00:02.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style_preview": "analitico, sintetico e rigoroso",
                },
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
                payload={
                    "active_minds": ["mente_analitica", "mente_logica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_logica", "mente_critica"],
                    "suppressed_minds": ["mente_probabilistica"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente_analitica lidera a resposta com apoio de "
                        "mente_logica, mente_critica"
                    ),
                    "arbitration_source": "mind_registry",
                },
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
                        "software_change_specialist": "core_mediated_read_only"
                    },
                    "consumer_modes": {
                        "software_change_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "consumer_objectives": {
                        "software_change_specialist": (
                            "avaliar segurança da mudança, impacto de implementação e "
                            "direção de patch recomendada"
                        )
                    },
                    "expected_deliverables": {
                        "software_change_specialist": [
                            "implementation_findings",
                            "change_risk_summary",
                            "recommended_patch_direction",
                        ]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": [
                            "contract_impact",
                            "change_safety",
                            "implementation_trace",
                        ]
                    },
                    "consumed_memory_classes": {
                        "software_change_specialist": ["mission", "domain"]
                    },
                    "memory_write_policies": {
                        "software_change_specialist": {
                            "mission": "through_core_only",
                            "domain": "through_core_only",
                        }
                    },
                    "domain_mission_link_reasons": {
                        "software_change_specialist": (
                            "route=software_development "
                            "canonicos=computacao_e_desenvolvimento "
                            "missao=Review Python service rollout"
                        )
                    },
                    "memory_class_policies": {
                        "software_change_specialist": {
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "domain": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
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
                event_name="domain_specialist_completed",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["software_change_specialist"],
                    "linked_domains": {"software_change_specialist": "software_development"},
                    "selection_modes": {"software_change_specialist": "guided"},
                    "canonical_domain_refs": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "expected_deliverables": {
                        "software_change_specialist": [
                            "implementation_findings",
                            "change_risk_summary",
                            "recommended_patch_direction",
                        ]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": [
                            "contract_impact",
                            "change_safety",
                            "implementation_trace",
                        ]
                    },
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s10b",
                event_name="plan_governed",
                timestamp="2026-03-18T00:00:09.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "decision_frame": "analysis",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style": "analitico, sintetico e rigoroso",
                    "identity_guardrail": "preservar rigor analitico antes de concluir",
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
                payload={
                    "continuity_action": "continuar",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style": "analitico, sintetico e rigoroso",
                },
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
    assert audit.domain_specialists == ["software_change_specialist"]
    assert audit.shadow_specialists == []
    assert audit.domain_alignment_status == "healthy"
    assert audit.workflow_trace_status == "not_applicable"
    assert audit.mind_alignment_status == "healthy"
    assert audit.identity_alignment_status == "healthy"
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



def test_observability_service_audits_healthy_workflow_trace() -> None:
    temp_dir = runtime_dir("observability-workflow")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-w1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan rollout checkpoints."},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_planejadora", "mente_logica"],
                    "primary_mind": "mente_planejadora",
                    "supporting_minds": ["mente_logica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "transformar meta em checkpoints seguros",
                    "arbitration_summary": "mente_planejadora lidera com apoio logico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w8",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_decision_points": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w9",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_decision_points": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w10",
                event_name="operation_dispatched",
                timestamp="2026-03-18T00:00:07.800000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "task_type": "draft_plan",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_state": "dispatched",
                    "workflow_decision_points": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w11",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_state": "completed",
                    "workflow_completed_steps": [
                        "structure the goal and success criteria",
                        "sequence the smallest safe steps",
                        "emit checkpoints and the next safe action",
                    ],
                    "workflow_decisions": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w12",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_state": "completed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_decision_points": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                    "workflow_decisions": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                    "status": "completed",
                    "checkpoints": [
                        "workflow_state:composed",
                        "workflow:goal_structured",
                        "workflow_state:completed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w13",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w14",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow"))

    assert audit.workflow_domain_route == "strategy"
    assert audit.workflow_profile == "strategic_direction_workflow"
    assert audit.workflow_governance_mode == "core_mediated"
    assert audit.workflow_trace_status == "healthy"
    assert audit.missing_required_events == []
    assert audit.anomaly_flags == []
    assert audit.trace_complete is True
