from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.archive.close_alignment_cycle import build_payload, render_markdown


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_close_alignment_cycle_builds_next_v2_cut() -> None:
    temp_dir = runtime_dir("v2-alignment-cycle-closure")
    observability_db = temp_dir / "observability.db"
    evolution_db = temp_dir / "evolution.db"
    comparison_json = temp_dir / "path_comparison.json"
    comparison_json.write_text(
        dumps(
            {
                "overall_verdict": "equivalent",
                "comparison_summary": {
                    "matched_scenarios": 4,
                    "divergent_scenarios": 0,
                "baseline_axis_adherence_score": 0.94,
                "candidate_axis_adherence_score": 0.96,
                "baseline_axis_gate_pass_rate": 1.0,
                "candidate_axis_gate_pass_rate": 1.0,
                "candidate_runtime_coverage": 1.0,
                "baseline_workflow_profile_decision": "baseline_saudavel",
                "candidate_workflow_profile_decision": "maturation_recommended",
                "baseline_workflow_baseline_rate": 1.0,
                "candidate_workflow_baseline_rate": 0.5,
                "baseline_workflow_maturation_rate": 0.0,
                "candidate_workflow_maturation_rate": 0.5,
                "baseline_memory_causality_decision": "causal_guidance",
                "candidate_memory_causality_decision": "causal_guidance",
                "baseline_memory_causal_rate": 1.0,
                "candidate_memory_causal_rate": 1.0,
                "baseline_memory_attached_only_rate": 0.0,
                "candidate_memory_attached_only_rate": 0.0,
                "baseline_mind_domain_specialist_decision": "aligned",
                "candidate_mind_domain_specialist_decision": "aligned",
                "baseline_mind_domain_specialist_alignment_rate": 1.0,
                "candidate_mind_domain_specialist_alignment_rate": 1.0,
                "baseline_cognitive_recomposition_decision": "not_applicable",
                "candidate_cognitive_recomposition_decision": "coherent",
                "baseline_cognitive_recomposition_coherent_rate": 0.0,
                "candidate_cognitive_recomposition_coherent_rate": 0.5,
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
                timestamp="2026-03-27T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "review the aligned runtime"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="memory_recovered",
                timestamp="2026-03-27T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar_missao_ativa"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="intent_classified",
                timestamp="2026-03-27T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="directive_composed",
                timestamp="2026-03-27T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="context_composed",
                timestamp="2026-03-27T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "active_minds": ["mente_analitica", "mente_estrategica"],
                    "supporting_minds": ["mente_estrategica"],
                    "suppressed_minds": ["mente_expressiva"],
                    "dominant_tension": "profundidade_vs_ritmo",
                    "arbitration_summary": "a mente analitica lidera com apoio estrategico",
                    "arbitration_source": "mind_registry",
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="plan_built",
                timestamp="2026-03-27T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="continuity_decided",
                timestamp="2026-03-27T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="domain_registry_resolved",
                timestamp="2026-03-27T00:00:07+00:00",
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
                event_id="evt-9",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-27T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_hints": ["software_change_specialist"],
                    "sharing_modes": {
                        "software_change_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "software_change_specialist": {
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            }
                        }
                    },
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-27T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "response_channel": "through_core",
                    "tool_access_mode": "none",
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-11",
                event_name="plan_governed",
                timestamp="2026-03-27T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                    "identity_guardrail": "preserve_unified_core",
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-12",
                event_name="governance_checked",
                timestamp="2026-03-27T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-13",
                event_name="response_synthesized",
                timestamp="2026-03-27T00:00:12+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                    "response_style": "analytical_unified",
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-14",
                event_name="memory_recorded",
                timestamp="2026-03-27T00:00:13+00:00",
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

    assert payload["decision"] == "close_v2_alignment_cycle_and_open_next_v2_cut"
    assert payload["evidence_summary"]["requests_audited"] == 1
    assert payload["evidence_summary"]["domain_alignment_healthy"] == 1
    assert payload["evidence_summary"]["mind_alignment_healthy"] == 1
    assert payload["evidence_summary"]["identity_alignment_healthy"] == 1
    assert payload["evidence_summary"]["memory_alignment_healthy"] == 1
    assert payload["evidence_summary"]["sovereignty_healthy"] == 1
    assert payload["evidence_summary"]["axis_gate_healthy"] == 1
    assert (
        payload["evidence_summary"]["candidate_workflow_profile_decision"]
        == "maturation_recommended"
    )
    assert payload["evidence_summary"]["candidate_memory_causality_decision"] == "causal_guidance"
    assert payload["evidence_summary"]["candidate_mind_domain_specialist_decision"] == "aligned"
    assert payload["evidence_summary"]["candidate_cognitive_recomposition_decision"] == "coherent"
    assert payload["next_cut_scope"][0]["item_id"] == "v2-domain-specialists-beyond-shadow"
    assert payload["deferred_scope"][0]["item_id"] == "defer-wide-computer-use"
    assert payload["vision_scope"][0]["item_id"] == "vision-robust-ecosystem"


def test_close_alignment_cycle_renders_markdown() -> None:
    payload = {
        "cycle_id": "v2-alignment-cycle-1",
        "decision": "close_v2_alignment_cycle_and_open_next_v2_cut",
        "evidence_summary": {
            "requests_audited": 1,
            "healthy_requests": 1,
            "incomplete_requests": 0,
            "attention_required_requests": 0,
            "domain_alignment_healthy": 1,
            "domain_alignment_partial": 0,
            "domain_alignment_incomplete": 0,
            "domain_alignment_attention_required": 0,
            "mind_alignment_healthy": 1,
            "mind_alignment_partial": 0,
            "mind_alignment_incomplete": 0,
            "mind_alignment_attention_required": 0,
            "identity_alignment_healthy": 1,
            "identity_alignment_partial": 0,
            "identity_alignment_incomplete": 0,
            "identity_alignment_attention_required": 0,
            "memory_alignment_healthy": 1,
            "memory_alignment_partial": 0,
            "memory_alignment_incomplete": 0,
            "memory_alignment_attention_required": 0,
            "sovereignty_healthy": 1,
            "sovereignty_incomplete": 0,
            "sovereignty_attention_required": 0,
            "axis_gate_healthy": 1,
            "axis_gate_partial": 0,
            "axis_gate_attention_required": 0,
            "recent_evolution_proposals": 0,
            "recent_evolution_decisions": 0,
            "comparison_overall_verdict": "equivalent",
            "comparison_decision": "candidate_ready_for_eval_gate",
            "matched_scenarios": 4,
            "divergent_scenarios": 0,
            "baseline_axis_adherence_score": 0.94,
            "candidate_axis_adherence_score": 0.96,
            "baseline_axis_gate_pass_rate": 1.0,
            "candidate_axis_gate_pass_rate": 1.0,
            "candidate_runtime_coverage": 1.0,
            "baseline_workflow_profile_decision": "baseline_saudavel",
            "candidate_workflow_profile_decision": "maturation_recommended",
            "baseline_workflow_baseline_rate": 1.0,
            "candidate_workflow_baseline_rate": 0.5,
            "baseline_workflow_maturation_rate": 0.0,
            "candidate_workflow_maturation_rate": 0.5,
            "baseline_memory_causality_decision": "causal_guidance",
            "candidate_memory_causality_decision": "causal_guidance",
            "baseline_memory_causal_rate": 1.0,
            "candidate_memory_causal_rate": 1.0,
            "baseline_memory_attached_only_rate": 0.0,
            "candidate_memory_attached_only_rate": 0.0,
            "baseline_mind_domain_specialist_decision": "aligned",
            "candidate_mind_domain_specialist_decision": "aligned",
            "baseline_mind_domain_specialist_alignment_rate": 1.0,
            "candidate_mind_domain_specialist_alignment_rate": 1.0,
            "baseline_cognitive_recomposition_decision": "not_applicable",
            "candidate_cognitive_recomposition_decision": "coherent",
            "baseline_cognitive_recomposition_coherent_rate": 0.0,
            "candidate_cognitive_recomposition_coherent_rate": 0.5,
        },
        "next_cut_scope": [
            {
                "item_id": "v2-domain-specialists-beyond-shadow",
                "title": "especialistas de dominio acima do shadow mode",
                "target_class": "proximo_corte_v2",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "deferred_scope": [
            {
                "item_id": "defer-wide-computer-use",
                "title": "computer use amplo e operacao extensa do computador",
                "target_class": "manter_deferido",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "vision_scope": [
            {
                "item_id": "vision-robust-ecosystem",
                "title": "ecossistema robusto que absorve o melhor do estado da arte",
                "target_class": "preservar_como_visao",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "decision_rationale": "decisao racional",
    }

    rendered = render_markdown(payload)

    assert "# Fechamento do V2 Alignment Cycle" in rendered
    assert "`v2-domain-specialists-beyond-shadow`" in rendered
    assert "`defer-wide-computer-use`" in rendered
    assert "`vision-robust-ecosystem`" in rendered
    assert "candidate_ready_for_eval_gate" in rendered
    assert "candidate workflow profile decision" in rendered
    assert "candidate memory causality decision" in rendered
    assert "candidate mind-domain-specialist decision" in rendered
    assert "candidate cognitive recomposition decision" in rendered
