from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.close_stateful_runtime_cycle import build_payload, render_markdown


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_close_stateful_runtime_cycle_builds_v2_cut() -> None:
    temp_dir = runtime_dir("v1-5-cycle-closure")
    observability_db = temp_dir / "observability.db"
    evolution_db = temp_dir / "evolution.db"
    comparison_json = temp_dir / "path_comparison.json"
    comparison_json.write_text(
        dumps(
            {
                "langgraph_status": "available",
                "overall_verdict": "equivalent",
                "comparison_summary": {
                    "scenario_count": 2,
                    "matched_scenarios": 2,
                    "divergent_scenarios": 0,
                    "baseline_expectation_score": 1.0,
                    "candidate_expectation_score": 1.0,
                    "candidate_runtime_coverage": 1.0,
                    "decision": "candidate_ready_for_eval_gate",
                },
            },
            ensure_ascii=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    service = ObservabilityService(database_path=str(observability_db))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-1",
                event_name="input_received",
                timestamp="2026-03-22T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "continue"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="memory_recovered",
                timestamp="2026-03-22T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar_missao_ativa"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="intent_classified",
                timestamp="2026-03-22T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="context_composed",
                timestamp="2026-03-22T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"active_minds": ["mente_estrategica"]},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="plan_built",
                timestamp="2026-03-22T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="continuity_decided",
                timestamp="2026-03-22T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="governance_checked",
                timestamp="2026-03-22T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="continuity_subflow_completed",
                timestamp="2026-03-22T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"runtime_mode": "langgraph_subflow"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="response_synthesized",
                timestamp="2026-03-22T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="memory_recorded",
                timestamp="2026-03-22T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
        ]
    )

    payload = build_payload(
        observability_db=str(observability_db),
        evolution_db=str(evolution_db),
        comparison_json=str(comparison_json),
        limit=10,
    )

    assert payload["decision"] == "promote_to_v2"
    assert payload["evidence_summary"]["requests_audited"] == 1
    assert payload["evidence_summary"]["langgraph_status"] == "available"
    assert payload["evidence_summary"]["comparison_decision"] == "candidate_ready_for_eval_gate"
    assert payload["v2_scope"][0]["item_id"] == "v2-specialist-runtime-contracts"
    assert payload["deferred_scope"][0]["item_id"] == "later-computer-use-wide"


def test_close_stateful_runtime_cycle_renders_markdown() -> None:
    payload = {
        "cycle_id": "v1-5-cycle-1",
        "decision": "promote_to_v2",
        "evidence_summary": {
            "requests_audited": 2,
            "healthy_requests": 1,
            "incomplete_requests": 1,
            "attention_required_requests": 0,
            "continuity_traces_healthy": 1,
            "continuity_traces_incomplete": 1,
            "continuity_traces_attention_required": 0,
            "recent_evolution_proposals": 1,
            "recent_evolution_decisions": 1,
            "langgraph_status": "available",
            "comparison_overall_verdict": "equivalent",
            "comparison_decision": "candidate_ready_for_eval_gate",
            "matched_scenarios": 6,
            "divergent_scenarios": 0,
            "baseline_expectation_score": 0.9,
            "candidate_expectation_score": 0.9,
            "candidate_runtime_coverage": 1.0,
        },
        "v2_scope": [
            {
                "item_id": "v2-specialist-runtime-contracts",
                "title": "contratos e runtime inicial de especialistas subordinados",
                "target_phase": "v2",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "deferred_scope": [
            {
                "item_id": "later-computer-use-wide",
                "title": "computer use amplo e operacao extensa do computador",
                "target_phase": "deferir_apos_primeiro_ciclo_v2",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "decision_rationale": "decisao racional",
    }

    rendered = render_markdown(payload)

    assert "# Fechamento do Ciclo V1.5" in rendered
    assert "`v2-specialist-runtime-contracts`" in rendered
    assert "`later-computer-use-wide`" in rendered
    assert "candidate_ready_for_eval_gate" in rendered
