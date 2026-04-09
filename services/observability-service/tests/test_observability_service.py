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


def test_observability_service_audits_metacognitive_guidance() -> None:
    temp_dir = runtime_dir("observability-metacognition")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-m1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan strategic options for the release."},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_missao_ativa"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_decisoria", "mente_estrategica"],
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "supporting_minds": ["mente_estrategica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "arbitration_summary": (
                        "mente_decisoria lidera com apoio estrategico e foco unico"
                    ),
                    "arbitration_source": "mind_registry",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "canonical_domains": ["estrategia_e_pensamento_sistemico"],
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "metacognitive_guidance_applied": True,
                    "metacognitive_guidance_summary": (
                        "mente decisoria ancora estrategia e pensamento sistemico via "
                        "strategy sob tensao equilibrar ambicao estrategica com a "
                        "menor proxima acao segura"
                    ),
                    "metacognitive_effects": [
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                    "metacognitive_containment_recommendation": None,
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "metacognitive_guidance_applied": True,
                    "metacognitive_guidance_summary": (
                        "mente decisoria ancora estrategia e pensamento sistemico via "
                        "strategy sob tensao equilibrar ambicao estrategica com a "
                        "menor proxima acao segura"
                    ),
                    "metacognitive_effects": [
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                    "metacognitive_containment_recommendation": None,
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-meta"))

    assert audit.metacognitive_guidance_status == "healthy"
    assert audit.metacognitive_guidance_summary is not None
    assert audit.metacognitive_effects == [
        "success_criteria",
        "smallest_safe_next_action",
    ]


def test_observability_service_distinguishes_contract_and_output_validation_failures() -> None:
    temp_dir = runtime_dir("observability-validation")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-v1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_executiva",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "dominant_tension": "equilibrar ambicao com a menor proxima acao segura",
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "contract_validation_status": "repaired",
                    "contract_validation_errors": ["missing_required_field:active_minds"],
                    "contract_validation_retry_applied": True,
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "contract_validation_status": "repaired",
                    "contract_validation_errors": ["missing_required_field:active_minds"],
                    "contract_validation_retry_applied": True,
                    "output_validation_status": "invalid",
                    "output_validation_errors": ["missing_clause:recommendation"],
                    "output_validation_retry_applied": True,
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-val"))
    evidence = service.build_incident_evidence(ObservabilityQuery(request_id="req-val"))

    assert audit.contract_validation_status == "repaired"
    assert audit.contract_validation_retry_applied is True
    assert audit.output_validation_status == "invalid"
    assert audit.output_validation_retry_applied is True
    assert "output_validation_failed" in audit.anomaly_flags
    assert audit.trace_complete is False
    assert (
        evidence.recommended_operator_action
        == "contain_response_and_recompose_with_last_valid_plan"
    )


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
                    "route_domains": ["software_development", "analysis"],
                    "primary_canonical_domain": "computacao_e_desenvolvimento",
                    "canonical_domain_refs_by_route": {
                        "software_development": ["computacao_e_desenvolvimento"],
                        "analysis": [
                            "dados_estatistica_e_inteligencia_analitica",
                            "tomada_de_decisao_complexa",
                        ],
                    },
                    "route_maturity": {
                        "software_development": "active_specialist",
                        "analysis": "active_specialist",
                    },
                    "route_modes": {
                        "software_development": "guided",
                        "analysis": "guided",
                    },
                    "linked_specialist_types": {
                        "software_development": "software_change_specialist",
                        "analysis": "structured_analysis_specialist",
                    },
                    "workflow_profiles": {
                        "software_development": "software_change_workflow",
                        "analysis": "structured_analysis_workflow",
                    },
                    "routing_sources": {
                        "software_development": "domain_registry",
                        "analysis": "domain_registry",
                    },
                    "shadow_domains": [],
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
                    "route_maturity": {"software_change_specialist": "active_specialist"},
                    "canonical_domain_refs": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "canonical_domain_refs_resolved": {
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
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoints": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                            "next_action_governed",
                        ],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending",
                            "step_sequence_validated": "pending",
                            "next_action_governed": "pending",
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
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
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                        "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
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
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_response_focus": (
                            "direcao recomendada, criterios e trade-offs dominantes"
                        ),
                        "workflow_state": "dispatched",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending",
                            "step_sequence_validated": "pending",
                            "next_action_governed": "pending",
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
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
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
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
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed",
                            "step_sequence_validated": "completed",
                            "next_action_governed": "completed",
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
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
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed",
                            "step_sequence_validated": "completed",
                            "next_action_governed": "completed",
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
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
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_planejadora",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "workflow_output_status": "coherent",
                    "workflow_output_errors": [],
                    "guided_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_focus": [
                        "estrategia_e_pensamento_sistemico",
                        "strategy",
                    ],
                    "procedural_memory_hint": "preservar o ultimo fio decisorio governado",
                },
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
    assert audit.workflow_profile_status == "healthy"
    assert audit.missing_required_events == []
    assert audit.anomaly_flags == []
    assert audit.trace_complete is True



def test_observability_service_flags_workflow_contract_drift() -> None:
    temp_dir = runtime_dir("observability-workflow-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-d1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoints": ["goal_scope_confirmed"],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending"
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                        "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d3",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_completed_steps": [
                        "frame the strategic scenario and the decision horizon",
                    ],
                    "workflow_decisions": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d4",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_decision_points": ["goal_scope_confirmed"],
                    "workflow_decisions": ["goal_scope_confirmed"],
                    "status": "completed",
                    "checkpoints": [
                        "workflow_state:composed",
                        "workflow_state:completed",
                    ],
                },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow-drift"))

    assert audit.workflow_trace_status == "attention_required"


def test_observability_service_marks_workflow_profile_maturation_recommended() -> None:
    temp_dir = runtime_dir("observability-workflow-maturation")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mw1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoints": ["goal_scope_confirmed"],
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "pending"
                    },
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_resume_eligible": False,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw3",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                        "workflow_response_focus": (
                            "direcao recomendada, criterios e trade-offs dominantes"
                        ),
                        "workflow_state": "completed",
                        "workflow_decisions": ["goal_scope_confirmed"],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed"
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                    },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw4",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "completed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed"
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                        "workflow_decisions": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw5",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "workflow_output_status": "partial",
                    "workflow_output_errors": ["missing_clause:workflow_checkpoint"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow-maturation"))

    assert audit.workflow_trace_status == "healthy"
    assert audit.workflow_profile_status == "maturation_recommended"
    assert audit.trace_complete is False


def test_observability_service_flags_workflow_output_misalignment() -> None:
    temp_dir = runtime_dir("observability-workflow-output-misaligned")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-wom1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoints": ["goal_scope_confirmed"],
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "pending"
                    },
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_resume_eligible": False,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom3",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "completed"
                    },
                    "workflow_pending_checkpoints": [],
                    "workflow_resume_status": "completed_without_resume",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                    "workflow_decisions": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom4",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_planejadora",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "workflow_output_status": "misaligned",
                    "workflow_output_errors": [
                        "mismatched_clause:workflow_response_focus"
                    ],
                    "guided_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_focus": [
                        "estrategia_e_pensamento_sistemico",
                        "strategy",
                    ],
                    "procedural_memory_hint": "preservar o ultimo fio decisorio governado",
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom5",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
            ),
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-workflow-output-misaligned")
    )

    assert audit.workflow_output_status == "misaligned"
    assert "mismatched_clause:workflow_response_focus" in audit.workflow_output_errors
    assert audit.workflow_profile_status == "attention_required"
    assert "workflow_output_misaligned" in audit.anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_tracks_organization_scope_no_go() -> None:
    temp_dir = runtime_dir("observability-organization-scope")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-og1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Keep organization scope outside baseline."},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"organization_scope_status": "no_go_without_canonical_consumer"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "preservar guardrails do baseline",
                    "arbitration_summary": "mente analitica lidera o fluxo",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og8",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og9",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_mode": "continuar",
                    "organization_scope_status": "no_go_without_canonical_consumer",
                },
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-organization-scope"))

    assert audit.organization_scope_status == "no_go_without_canonical_consumer"


def test_observability_service_tracks_specialist_recurrence_status() -> None:
    temp_dir = runtime_dir("observability-specialist-recurrence")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-sr1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review software rollout again."},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "aprofundar contexto recorrente",
                    "arbitration_summary": "mente analitica lidera o fluxo",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "guided_specialists": ["software_change_specialist"],
                    "recurrent_context_statuses": {"software_change_specialist": "recoverable"},
                    "recurrent_interaction_counts": {"software_change_specialist": 2},
                },
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr9",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr10",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-specialist-recurrence"))

    assert audit.specialist_recurrence_status == "recoverable"


def test_observability_service_tracks_user_scope_status() -> None:
    temp_dir = runtime_dir("observability-user-scope")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-us1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze rollout context."},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"user_scope_status": "seeded"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "consolidar contexto do usuario sem perder rigor",
                    "arbitration_summary": "mente_analitica lidera a leitura do contexto",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us8",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us9",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar", "user_scope_status": "recoverable"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-user-scope"))

    assert audit.user_scope_status == "recoverable"




def test_observability_service_marks_mind_alignment_attention_when_plan_drifts() -> None:
    temp_dir = runtime_dir("observability-mind-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-md1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review rollout trade-offs."},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md4",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_logica"],
                    "canonical_domains": ["dados_estatistica_e_inteligencia_analitica"],
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "supporting_minds": ["mente_logica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": "mente_analitica lidera a resposta com apoio logico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md5",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "tomada_de_decisao_complexa",
                    "arbitration_source": "mind_registry",
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md6",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md7",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md8",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md9",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-mind-drift"))

    assert audit.mind_alignment_status == "attention_required"

def test_observability_service_marks_domain_alignment_attention_when_selection_drifts() -> None:
    temp_dir = runtime_dir("observability-selection-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-d1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review software rollout."},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d4",
                event_name="domain_registry_resolved",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "registry_domains": ["computacao_e_desenvolvimento"],
                    "route_domains": ["software_development"],
                    "canonical_domain_refs_by_route": {
                        "software_development": ["computacao_e_desenvolvimento"]
                    },
                    "route_maturity": {"software_development": "active_specialist"},
                    "route_modes": {"software_development": "guided"},
                    "linked_specialist_types": {
                        "software_development": "software_change_specialist"
                    },
                    "workflow_profiles": {
                        "software_development": "software_change_workflow"
                    },
                    "routing_sources": {"software_development": "domain_registry"},
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d5",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": "mente_analitica lidera a resposta",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d6",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d7",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d8",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d9",
                event_name="specialist_selection_decided",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "selected_specialists": ["software_change_specialist"],
                    "domain_links": {"software_change_specialist": "software_development"},
                    "selection_modes": {"software_change_specialist": "shadow"},
                    "route_maturity": {"software_change_specialist": "active_specialist"},
                    "canonical_domain_refs_resolved": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "registry_link_matches": {"software_change_specialist": True},
                    "registry_mode_matches": {"software_change_specialist": False},
                    "registry_specialist_eligibility": {"software_change_specialist": False},
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d10",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d11",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-selection-drift"))

    assert audit.domain_alignment_status == "attention_required"


def test_observability_service_flags_primary_driver_specialist_drift() -> None:
    temp_dir = runtime_dir("observability-primary-driver-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-pd1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Compare strategic options for the release."},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd4",
                event_name="domain_registry_resolved",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "registry_domains": [
                        "estrategia_e_pensamento_sistemico",
                        "dados_estatistica_e_inteligencia_analitica",
                    ],
                    "route_domains": ["strategy", "analysis"],
                    "canonical_domain_refs_by_route": {
                        "strategy": ["estrategia_e_pensamento_sistemico"],
                        "analysis": ["dados_estatistica_e_inteligencia_analitica"],
                    },
                    "route_maturity": {
                        "strategy": "active_specialist",
                        "analysis": "active_specialist",
                    },
                    "route_modes": {"strategy": "guided", "analysis": "guided"},
                    "linked_specialist_types": {
                        "strategy": "structured_analysis_specialist",
                        "analysis": "structured_analysis_specialist",
                    },
                    "workflow_profiles": {
                        "strategy": "strategic_direction_workflow",
                        "analysis": "structured_analysis_workflow",
                    },
                    "routing_sources": {
                        "strategy": "domain_registry",
                        "analysis": "domain_registry",
                    },
                    "promoted_route_registry": {
                        "strategy": {
                            "canonical_domain_refs": ["estrategia_e_pensamento_sistemico"],
                            "linked_specialist_type": "structured_analysis_specialist",
                            "specialist_mode": "guided",
                            "maturity": "active_specialist",
                            "mode_is_governed": True,
                            "eligible": True,
                        },
                        "analysis": {
                            "canonical_domain_refs": [
                                "dados_estatistica_e_inteligencia_analitica"
                            ],
                            "linked_specialist_type": "structured_analysis_specialist",
                            "specialist_mode": "guided",
                            "maturity": "active_specialist",
                            "mode_is_governed": True,
                            "eligible": True,
                        },
                    },
                    "consumer_profiles": {
                        "strategy": "strategy_tradeoff_review",
                        "analysis": "analysis_evidence_review",
                    },
                    "consumer_objectives": {
                        "strategy": "clarificar trade-offs estrategicos",
                        "analysis": "estruturar leitura de evidencia",
                    },
                    "expected_deliverables": {
                        "strategy": ["tradeoff_map"],
                        "analysis": ["analysis_findings"],
                    },
                    "telemetry_focus": {
                        "strategy": ["tradeoff_clarity"],
                        "analysis": ["evidence_clarity"],
                    },
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd5",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_decisoria"],
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "arbitration_summary": "mente_decisoria lidera a resposta",
                    "arbitration_source": "mind_registry",
                    "canonical_domains": [
                        "estrategia_e_pensamento_sistemico",
                        "dados_estatistica_e_inteligencia_analitica",
                    ],
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd6",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd7",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd8",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd9",
                event_name="specialist_selection_decided",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "selected_specialists": ["structured_analysis_specialist"],
                    "domain_links": {"structured_analysis_specialist": "analysis"},
                    "selection_modes": {"structured_analysis_specialist": "guided"},
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "primary_route": "strategy",
                    "primary_canonical_domain": "estrategia_e_pensamento_sistemico",
                    "route_maturity": {"structured_analysis_specialist": "active_specialist"},
                    "canonical_domain_refs_resolved": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                    "registry_route_payloads": {
                        "structured_analysis_specialist": {
                            "route_name": "analysis",
                            "linked_specialist_type": "structured_analysis_specialist",
                            "canonical_domain_refs": [
                                "dados_estatistica_e_inteligencia_analitica"
                            ],
                        }
                    },
                    "registry_link_matches": {"structured_analysis_specialist": True},
                    "registry_mode_matches": {"structured_analysis_specialist": True},
                    "registry_specialist_eligibility": {"structured_analysis_specialist": True},
                    "primary_route_matches": {"structured_analysis_specialist": False},
                    "primary_canonical_matches": {"structured_analysis_specialist": False},
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": False
                    },
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd10",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd11",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-primary-driver-drift"))

    assert audit.domain_alignment_status == "attention_required"


def test_observability_service_tracks_memory_causality_status() -> None:
    temp_dir = runtime_dir("observability-memory-causality")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mc1",
                event_name="input_received",
                timestamp="2026-04-02T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Compare release options with prior context."},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc2",
                event_name="memory_recovered",
                timestamp="2026-04-02T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc3",
                event_name="intent_classified",
                timestamp="2026-04-02T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc4",
                event_name="context_composed",
                timestamp="2026-04-02T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "conectar contexto previo com decisao atual",
                    "arbitration_summary": "mente analitica lidera a resposta",
                    "arbitration_source": "mind_registry",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "canonical_domains": ["dados_estatistica_e_inteligencia_analitica"],
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc5",
                event_name="plan_built",
                timestamp="2026-04-02T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc6",
                event_name="continuity_decided",
                timestamp="2026-04-02T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc7",
                event_name="governance_checked",
                timestamp="2026-04-02T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-04-02T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "structured_analysis_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "structured_analysis_specialist": {
                            "semantic": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "procedural": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                    "consumed_memory_classes": {
                        "structured_analysis_specialist": ["semantic", "procedural"]
                    },
                    "memory_write_policies": {
                        "structured_analysis_specialist": {
                            "semantic": "through_core_only",
                            "procedural": "through_core_only",
                        }
                    },
                    "memory_refs_by_specialist": {
                        "structured_analysis_specialist": [
                            "memory://semantic/release-context",
                            "memory://procedural/release-checklist",
                        ]
                    },
                    "semantic_focus_by_specialist": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                    "consumer_modes": {
                        "structured_analysis_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "structured_analysis_specialist": "structured_analysis"
                    },
                    "consumer_objectives": {
                        "structured_analysis_specialist": "compare_safe_options"
                    },
                    "expected_deliverables": {
                        "structured_analysis_specialist": ["comparison_frame"]
                    },
                    "telemetry_focus": {
                        "structured_analysis_specialist": ["analysis_trace"]
                    },
                    "domain_mission_link_reasons": {
                        "structured_analysis_specialist": (
                            "analysis linked to active mission and canonical domain"
                        )
                    },
                    "semantic_memory_specialists": ["structured_analysis_specialist"],
                    "procedural_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_states": {
                        "structured_analysis_specialist": "operational"
                    },
                    "procedural_memory_states": {
                        "structured_analysis_specialist": "operational"
                    },
                    "memory_consolidation_statuses": {
                        "structured_analysis_specialist": "in_progress"
                    },
                    "memory_fixation_statuses": {
                        "structured_analysis_specialist": "not_fixed"
                    },
                    "memory_archive_statuses": {
                        "structured_analysis_specialist": "active_memory"
                    },
                    "memory_review_statuses": {
                        "structured_analysis_specialist": "monitor"
                    },
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc9",
                event_name="response_synthesized",
                timestamp="2026-04-02T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                    "semantic_memory_available": True,
                    "procedural_memory_available": True,
                    "semantic_memory_focus": [
                        "dados_estatistica_e_inteligencia_analitica"
                    ],
                    "procedural_memory_hint": "preservar a moldura de comparacao mais recente",
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc10",
                event_name="memory_recorded",
                timestamp="2026-04-02T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-memory-causality"))

    assert audit.memory_causality_status == "causal_guidance"
    assert audit.semantic_memory_focus == ["dados_estatistica_e_inteligencia_analitica"]
    assert (
        audit.procedural_memory_hint
        == "preservar a moldura de comparacao mais recente"
    )
    assert audit.semantic_memory_specialists == ["structured_analysis_specialist"]
    assert audit.procedural_memory_specialists == ["structured_analysis_specialist"]
    assert audit.memory_consolidation_status == "in_progress"
    assert audit.memory_fixation_status == "not_fixed"
    assert audit.memory_archive_status == "active_memory"


def test_observability_service_flags_archivable_guided_memory_reuse() -> None:
    temp_dir = runtime_dir("observability-archivable-guided-memory")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-archivable-memory",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-04-09T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "software_change_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "software_change_specialist": {
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "semantic": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                    "consumed_memory_classes": {
                        "software_change_specialist": ["mission", "semantic"]
                    },
                    "memory_write_policies": {
                        "software_change_specialist": {
                            "mission": "through_core_only",
                            "semantic": "through_core_only",
                        }
                    },
                    "memory_refs_by_specialist": {
                        "software_change_specialist": [
                            "memory://mission",
                            "memory://semantic/mission/old",
                        ]
                    },
                    "semantic_focus_by_specialist": {
                        "software_change_specialist": ["software_development"]
                    },
                    "consumer_modes": {
                        "software_change_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "consumer_objectives": {
                        "software_change_specialist": "review rollout change"
                    },
                    "expected_deliverables": {
                        "software_change_specialist": ["change_assessment"]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": ["change_trace"]
                    },
                    "domain_mission_link_reasons": {
                        "software_change_specialist": "software route linked to active mission"
                    },
                    "semantic_memory_states": {
                        "software_change_specialist": "archivable"
                    },
                    "procedural_memory_states": {
                        "software_change_specialist": "archivable"
                    },
                    "memory_consolidation_statuses": {
                        "software_change_specialist": "revisit_before_reuse"
                    },
                    "memory_fixation_statuses": {
                        "software_change_specialist": "not_fixed"
                    },
                    "memory_archive_statuses": {
                        "software_change_specialist": "archive_candidate"
                    },
                    "memory_review_statuses": {
                        "software_change_specialist": "review_recommended"
                    },
                },
                request_id="req-archivable-memory",
                session_id="sess-archivable-memory",
                correlation_id="req-archivable-memory",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-archivable-memory"))

    assert audit.memory_alignment_status == "attention_required"


def test_observability_service_tracks_cognitive_recomposition_alignment() -> None:
    temp_dir = runtime_dir("observability-cognitive-recomposition")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-cr1",
                event_name="input_received",
                timestamp="2026-04-02T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Resolve the domain impasse before answering."},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr2",
                event_name="memory_recovered",
                timestamp="2026-04-02T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr3",
                event_name="intent_classified",
                timestamp="2026-04-02T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr4",
                event_name="context_composed",
                timestamp="2026-04-02T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "supporting_minds": ["mente_critica"],
                    "suppressed_minds": ["mente_expressiva"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente analitica lidera com recomposicao critica"
                    ),
                    "arbitration_source": "mind_registry_recomposition",
                    "canonical_domains": [
                        "dados_estatistica_e_inteligencia_analitica"
                    ],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr5",
                event_name="cognitive_recomposition_applied",
                timestamp="2026-04-02T00:00:03.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_critica"],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr6",
                event_name="plan_built",
                timestamp="2026-04-02T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr7",
                event_name="continuity_decided",
                timestamp="2026-04-02T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr8",
                event_name="governance_checked",
                timestamp="2026-04-02T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr9",
                event_name="domain_specialist_completed",
                timestamp="2026-04-02T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["structured_analysis_specialist"],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": True
                    },
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr10",
                event_name="response_synthesized",
                timestamp="2026-04-02T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr11",
                event_name="memory_recorded",
                timestamp="2026-04-02T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-cognitive-recomposition")
    )

    assert audit.mind_alignment_status == "healthy"
    assert audit.mind_domain_specialist_status == "aligned"
    assert audit.cognitive_recomposition_applied is True
    assert (
        audit.cognitive_recomposition_trigger == "specialist_route_impasse"
    )


def test_observability_service_tracks_mid_flow_cognitive_strategy_shift() -> None:
    temp_dir = runtime_dir("observability-cognitive-strategy-shift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-css1",
                event_name="input_received",
                timestamp="2026-04-09T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Resolve the strategic impasse before concluding."},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css2",
                event_name="memory_recovered",
                timestamp="2026-04-09T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css3",
                event_name="intent_classified",
                timestamp="2026-04-09T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css4",
                event_name="context_composed",
                timestamp="2026-04-09T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_executiva", "mente_critica"],
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "supporting_minds": ["mente_critica"],
                    "suppressed_minds": ["mente_expressiva"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar direcao estrategica com checkpoint governado",
                    "arbitration_summary": "mente executiva lidera com apoio critico",
                    "arbitration_source": "mind_registry",
                    "canonical_domains": ["estrategia_e_pensamento_sistemico"],
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css5",
                event_name="plan_built",
                timestamp="2026-04-09T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "mind_disagreement_status": "validation_required",
                    "mind_validation_checkpoints": ["validar o checkpoint estrategico"],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css6",
                event_name="continuity_decided",
                timestamp="2026-04-09T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css7",
                event_name="plan_refined",
                timestamp="2026-04-09T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={
                    "cognitive_strategy_shift_applied": True,
                    "cognitive_strategy_shift_summary": (
                        "revisao especializada manteve tensao aberta sob workflow governado; "
                        "checkpoint ativo scenario framed; loop alinhar checkpoint principal"
                    ),
                    "cognitive_strategy_shift_trigger": "guided_validation_impasse",
                    "cognitive_strategy_shift_effects": [
                        "steps",
                        "constraints",
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css8",
                event_name="governance_checked",
                timestamp="2026-04-09T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css9",
                event_name="response_synthesized",
                timestamp="2026-04-09T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "workflow_output_status": "coherent",
                    "cognitive_strategy_shift_applied": True,
                    "cognitive_strategy_shift_summary": (
                        "revisao especializada manteve tensao aberta sob workflow governado; "
                        "checkpoint ativo scenario framed; loop alinhar checkpoint principal"
                    ),
                    "cognitive_strategy_shift_trigger": "guided_validation_impasse",
                    "cognitive_strategy_shift_effects": [
                        "steps",
                        "constraints",
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css10",
                event_name="memory_recorded",
                timestamp="2026-04-09T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-cognitive-shift"))

    assert audit.cognitive_strategy_shift_status == "healthy"
    assert audit.cognitive_strategy_shift_applied is True
    assert audit.cognitive_strategy_shift_trigger == "guided_validation_impasse"
    assert "steps" in audit.cognitive_strategy_shift_effects


def test_observability_service_tracks_specialist_subflow_and_mission_runtime_state() -> None:
    temp_dir = runtime_dir("observability-pre-v3-hardening")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-p1",
                event_name="input_received",
                timestamp="2026-04-03T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan the pilot checkpoint."},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p2",
                event_name="memory_recovered",
                timestamp="2026-04-03T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p3",
                event_name="intent_classified",
                timestamp="2026-04-03T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p4",
                event_name="context_composed",
                timestamp="2026-04-03T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p5",
                event_name="plan_built",
                timestamp="2026-04-03T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p6",
                event_name="continuity_decided",
                timestamp="2026-04-03T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p7",
                event_name="specialist_selection_decided",
                timestamp="2026-04-03T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"domain_specialists": ["structured_analysis_specialist"]},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p8",
                event_name="specialist_subflow_completed",
                timestamp="2026-04-03T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "native_pipeline",
                    "subflow_name": "specialist_handoffs",
                    "selection_status": "selected",
                    "governance_status": "approved",
                    "dispatch_status": "dispatched",
                    "completion_status": "completed",
                    "selection_count": 1,
                    "invocation_count": 1,
                    "contribution_count": 1,
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p9",
                event_name="mission_runtime_state_declared",
                timestamp="2026-04-03T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "native_pipeline",
                    "mission_id": "mission-pre-v3",
                    "mission_goal": "Plan the pilot checkpoint.",
                    "mission_status": "active",
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_route": "strategy",
                    "workflow_profile": "strategic_direction_workflow",
                    "active_task_count": 2,
                    "open_loop_count": 1,
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p10",
                event_name="governance_checked",
                timestamp="2026-04-03T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p11",
                event_name="response_synthesized",
                timestamp="2026-04-03T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p12",
                event_name="memory_recorded",
                timestamp="2026-04-03T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-pre-v3"))

    assert audit.specialist_subflow_status == "healthy"
    assert audit.specialist_subflow_runtime_mode == "native_pipeline"
    assert audit.mission_runtime_state_status == "healthy"
    assert audit.trace_complete is True
