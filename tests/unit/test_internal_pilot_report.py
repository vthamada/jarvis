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
    assert summaries[0].expectation_status == "operation_completed"
    assert "plan_built" in summaries[0].missing_required_events
    assert "continuity_decided" in summaries[0].missing_required_events
    assert "response_continuity_action" in summaries[0].missing_continuity_signals
    assert summaries[0].workflow_domain_route is None
    assert summaries[0].workflow_trace_status == "attention_required"
    assert summaries[0].workflow_profile_status == "not_applicable"
    assert summaries[0].workflow_profile_assessment == "not_applicable"
    assert summaries[0].memory_causality_status == "not_applicable"
    assert summaries[0].mind_domain_specialist_status == "incomplete"
    assert summaries[0].cognitive_recomposition_applied is False
    assert summaries[0].cognitive_recomposition_assessment == "not_applicable"
    assert summaries[0].continuity_trace_status == "incomplete"
    assert summaries[0].axis_gate_status == "attention_required"
    assert summaries[0].trace_status == "attention_required"
    assert summaries[0].anomaly_flags == [
        "operation_completed_without_dispatch",
        "workflow_missing_composition",
        "workflow_missing_governance",
        "workflow_missing_completion",
        "allowed_flow_missing_response",
        "allowed_flow_missing_memory_record",
    ]
    assert summaries[0].source_services == ["orchestrator-service"]


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
                    "anomaly_flags": ["operation_missing_completion"],
                    "continuity_action": "retomar",
                    "continuity_source": "related_mission",
                    "continuity_runtime_mode": "langgraph_subflow",
                    "workflow_domain_route": "strategy",
                    "domain_alignment_status": "healthy",
                    "mind_alignment_status": "partial",
                    "identity_alignment_status": "healthy",
                    "memory_alignment_status": "healthy",
                    "specialist_sovereignty_status": "healthy",
                    "axis_gate_status": "partial",
                    "expectation_status": "continuity_progressing",
                    "workflow_trace_status": "healthy",
                    "workflow_profile_status": "maturation_recommended",
                    "workflow_profile_assessment": "maturation_recommended",
                    "memory_causality_status": "causal_guidance",
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_source": "mind_registry",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "mind_domain_specialist_status": "aligned",
                    "cognitive_recomposition_applied": False,
                    "cognitive_recomposition_assessment": "not_applicable",
                    "cognitive_recomposition_reason": None,
                    "cognitive_recomposition_trigger": None,
                    "semantic_memory_focus": [
                        "dados_estatistica_e_inteligencia_analitica"
                    ],
                    "procedural_memory_hint": "preservar criterio de comparacao",
                    "semantic_memory_specialists": [
                        "structured_analysis_specialist"
                    ],
                    "procedural_memory_specialists": [
                        "structured_analysis_specialist"
                    ],
                    "continuity_trace_status": "attention_required",
                    "missing_continuity_signals": ["memory_continuity_mode"],
                    "continuity_anomaly_flags": ["retomar_missing_target_mission"],
                    "trace_status": "attention_required",
                    "governance_decision": "allow",
                    "operation_status": "completed",
                    "duration_seconds": 2.0,
                    "source_services": ["orchestrator-service"],
                },
            )()
        ]
    )

    assert "request_id=req-x" in rendered
    assert "missing_required_events=plan_built" in rendered
    assert "anomaly_flags=operation_missing_completion" in rendered
    assert "continuity_action=retomar" in rendered
    assert "continuity_runtime_mode=langgraph_subflow" in rendered
    assert "workflow_domain_route=strategy" in rendered
    assert "mind_alignment_status=partial" in rendered
    assert "axis_gate_status=partial" in rendered
    assert "expectation_status=continuity_progressing" in rendered
    assert "workflow_trace_status=healthy" in rendered
    assert "workflow_profile_status=maturation_recommended" in rendered
    assert "workflow_profile_assessment=maturation_recommended" in rendered
    assert "memory_causality_status=causal_guidance" in rendered
    assert "dominant_tension=equilibrar profundidade analitica com conclusao util" in rendered
    assert "primary_domain_driver=dados_estatistica_e_inteligencia_analitica" in rendered
    assert "mind_domain_specialist_status=aligned" in rendered
    assert "cognitive_recomposition_assessment=not_applicable" in rendered
    assert "semantic_memory_focus=dados_estatistica_e_inteligencia_analitica" in rendered
    assert "procedural_memory_hint=preservar criterio de comparacao" in rendered
    assert "continuity_anomaly_flags=retomar_missing_target_mission" in rendered
    assert "trace_status=attention_required" in rendered
