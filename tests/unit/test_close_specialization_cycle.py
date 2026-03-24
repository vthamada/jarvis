from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.close_specialization_cycle import build_payload, render_markdown


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_close_specialization_cycle_builds_alignment_cut() -> None:
    temp_dir = runtime_dir("v2-cycle-closure")
    observability_db = temp_dir / "observability.db"
    evolution_db = temp_dir / "evolution.db"
    comparison_json = temp_dir / "path_comparison.json"
    comparison_json.write_text(
        dumps(
            {
                "overall_verdict": "equivalent",
                "comparison_summary": {
                    "matched_scenarios": 3,
                    "divergent_scenarios": 0,
                    "baseline_axis_adherence_score": 0.91,
                    "candidate_axis_adherence_score": 0.93,
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
                timestamp="2026-03-23T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "review software domain"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="memory_recovered",
                timestamp="2026-03-23T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar_missao_ativa"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="intent_classified",
                timestamp="2026-03-23T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="context_composed",
                timestamp="2026-03-23T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"active_minds": ["mente_analitica"]},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="plan_built",
                timestamp="2026-03-23T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="continuity_decided",
                timestamp="2026-03-23T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="domain_registry_resolved",
                timestamp="2026-03-23T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_domains": ["software_development"],
                    "registry_domains": ["computacao_e_desenvolvimento"],
                    "route_domains": ["software_development"],
                    "shadow_domains": ["software_development"],
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-23T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_hints": ["especialista_software_subordinado"],
                    "sharing_modes": {
                        "especialista_software_subordinado": "core_mediated_read_only"
                    },
                    "linked_domains": {
                        "especialista_software_subordinado": "software_development"
                    },
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-23T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "response_channel": "through_core",
                    "tool_access_mode": "none",
                    "shadow_specialists": ["especialista_software_subordinado"],
                    "shared_memory_attached": True,
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="specialist_shadow_mode_completed",
                timestamp="2026-03-23T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["especialista_software_subordinado"],
                    "linked_domains": {
                        "especialista_software_subordinado": "software_development"
                    },
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-11",
                event_name="governance_checked",
                timestamp="2026-03-23T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-12",
                event_name="response_synthesized",
                timestamp="2026-03-23T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-13",
                event_name="memory_recorded",
                timestamp="2026-03-23T00:00:12+00:00",
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

    assert payload["decision"] == "open_v2_alignment_cycle"
    assert payload["evidence_summary"]["requests_audited"] == 1
    assert payload["evidence_summary"]["domain_alignment_healthy"] == 1
    assert payload["evidence_summary"]["memory_alignment_healthy"] == 1
    assert payload["evidence_summary"]["sovereignty_healthy"] == 1
    assert payload["correct_now_scope"][0]["item_id"] == "alignment-domain-sovereignty"
    assert payload["deferred_scope"][0]["item_id"] == "defer-wide-tool-layer"
    assert payload["vision_scope"][0]["item_id"] == "vision-full-domain-maturity"


def test_close_specialization_cycle_renders_markdown() -> None:
    payload = {
        "cycle_id": "v2-cycle-1",
        "decision": "open_v2_alignment_cycle",
        "evidence_summary": {
            "requests_audited": 1,
            "healthy_requests": 1,
            "incomplete_requests": 0,
            "attention_required_requests": 0,
            "domain_alignment_healthy": 1,
            "domain_alignment_partial": 0,
            "domain_alignment_incomplete": 0,
            "domain_alignment_attention_required": 0,
            "memory_alignment_healthy": 1,
            "memory_alignment_partial": 0,
            "memory_alignment_incomplete": 0,
            "memory_alignment_attention_required": 0,
            "sovereignty_healthy": 1,
            "sovereignty_incomplete": 0,
            "sovereignty_attention_required": 0,
            "recent_evolution_proposals": 0,
            "recent_evolution_decisions": 0,
            "comparison_overall_verdict": "equivalent",
            "comparison_decision": "candidate_ready_for_eval_gate",
            "matched_scenarios": 3,
            "divergent_scenarios": 0,
            "baseline_axis_adherence_score": 0.91,
            "candidate_axis_adherence_score": 0.93,
            "candidate_runtime_coverage": 1.0,
        },
        "correct_now_scope": [
            {
                "item_id": "alignment-domain-sovereignty",
                "title": "dominios como fonte soberana de roteamento e ativacao",
                "target_class": "corrigir_agora",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "deferred_scope": [
            {
                "item_id": "defer-wide-tool-layer",
                "title": "tool layer ampla e operacao computacional extensa",
                "target_class": "manter_deferido",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "vision_scope": [
            {
                "item_id": "vision-full-domain-maturity",
                "title": "todos os dominios do mestre operando com maturidade plena ao mesmo tempo",
                "target_class": "preservar_como_visao",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "decision_rationale": "decisao racional",
    }

    rendered = render_markdown(payload)

    assert "# Fechamento do Primeiro Corte do V2" in rendered
    assert "`alignment-domain-sovereignty`" in rendered
    assert "`defer-wide-tool-layer`" in rendered
    assert "`vision-full-domain-maturity`" in rendered
    assert "candidate_ready_for_eval_gate" in rendered
