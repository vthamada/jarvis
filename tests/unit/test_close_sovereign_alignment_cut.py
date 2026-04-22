from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.archive.close_sovereign_alignment_cut import build_payload, render_markdown


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_close_sovereign_alignment_cut_builds_payload() -> None:
    temp_dir = runtime_dir("v2-sovereign-alignment-cut")
    observability_db = temp_dir / "observability.db"
    evolution_db = temp_dir / "evolution.db"
    comparison_json = temp_dir / "path_comparison.json"
    comparison_json.write_text(
        dumps(
            {
                "overall_verdict": "equivalent",
                "comparison_summary": {
                    "matched_scenarios": 5,
                    "divergent_scenarios": 0,
                "baseline_axis_adherence_score": 0.95,
                "candidate_axis_adherence_score": 0.97,
                "baseline_axis_gate_pass_rate": 1.0,
                "candidate_axis_gate_pass_rate": 1.0,
                "candidate_runtime_coverage": 1.0,
                "baseline_workflow_profile_decision": "baseline_saudavel",
                "candidate_workflow_profile_decision": "maturation_recommended",
                "baseline_workflow_baseline_rate": 1.0,
                "candidate_workflow_baseline_rate": 0.6,
                "baseline_workflow_maturation_rate": 0.0,
                "candidate_workflow_maturation_rate": 0.4,
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
                "baseline_expanded_eval_readiness": "baseline_only",
                "candidate_expanded_eval_readiness": "candidate_ready",
                "baseline_wave2_lane_health": "baseline_only",
                "candidate_wave2_lane_health": "controlled_candidate",
                "baseline_experiment_release_status": "hold_baseline",
                "candidate_experiment_release_status": "hold_in_lane",
                "baseline_promotion_blocker_rate": 0.0,
                "candidate_promotion_blocker_rate": 0.0,
                "baseline_optimization_target_kind_decision": "not_applicable",
                "candidate_optimization_target_kind_decision": "workflow",
                "baseline_optimization_readiness_decision": "hold_baseline",
                "candidate_optimization_readiness_decision": "candidate_ready",
                "baseline_optimization_release_decision": "hold_baseline",
                "candidate_optimization_release_decision": "hold_in_lane",
                "baseline_optimization_candidate_ready_rate": 0.0,
                "candidate_optimization_candidate_ready_rate": 0.5,
                "baseline_optimization_blocked_rate": 0.0,
                "candidate_optimization_blocked_rate": 0.0,
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
                timestamp="2026-03-30T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "review sovereign cut"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="memory_recovered",
                timestamp="2026-03-30T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar_missao_ativa"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="intent_classified",
                timestamp="2026-03-30T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="directive_composed",
                timestamp="2026-03-30T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="context_composed",
                timestamp="2026-03-30T00:00:04+00:00",
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
                    "canonical_domains": ["dados_estatistica_e_inteligencia_analitica"],
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="plan_built",
                timestamp="2026-03-30T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="continuity_decided",
                timestamp="2026-03-30T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="domain_registry_resolved",
                timestamp="2026-03-30T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_domains": ["analysis", "decision_risk"],
                    "registry_domains": ["dados_estatistica_e_inteligencia_analitica"],
                    "route_domains": ["analysis", "decision_risk"],
                    "primary_canonical_domain": "dados_estatistica_e_inteligencia_analitica",
                    "canonical_domain_refs_by_route": {
                        "analysis": ["dados_estatistica_e_inteligencia_analitica"],
                        "decision_risk": ["governanca_do_sistema"],
                    },
                    "route_modes": {"analysis": "guided", "decision_risk": "guided"},
                    "route_maturity": {
                        "analysis": "active_specialist",
                        "decision_risk": "active_specialist",
                    },
                    "linked_specialist_types": {
                        "analysis": "structured_analysis_specialist",
                        "decision_risk": "governance_review_specialist",
                    },
                    "workflow_profiles": {
                        "analysis": "structured_analysis_workflow",
                        "decision_risk": "decision_risk_workflow",
                    },
                    "routing_sources": {
                        "analysis": "domain_registry",
                        "decision_risk": "domain_registry",
                    },
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-30T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "structured_analysis_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "structured_analysis_specialist": {
                            "domain": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "contextual": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                    "consumed_memory_classes": {
                        "structured_analysis_specialist": ["domain", "mission", "contextual"]
                    },
                    "memory_write_policies": {
                        "structured_analysis_specialist": {
                            "domain": "through_core_only",
                            "mission": "through_core_only",
                            "contextual": "through_core_only",
                        }
                    },
                    "domain_mission_link_reasons": {
                        "structured_analysis_specialist": (
                            "analysis linked to active mission and canonical domain"
                        )
                    },
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-30T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"response_channel": "through_core", "tool_access_mode": "none"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-11",
                event_name="domain_specialist_completed",
                timestamp="2026-03-30T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["structured_analysis_specialist"],
                    "linked_domains": {"structured_analysis_specialist": "analysis"},
                    "selection_modes": {"structured_analysis_specialist": "guided"},
                    "route_maturity": {"structured_analysis_specialist": "active_specialist"},
                    "canonical_domain_refs": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                    "canonical_domain_refs_resolved": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-12",
                event_name="plan_governed",
                timestamp="2026-03-30T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                    "identity_guardrail": "preserve_unified_core",
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-13",
                event_name="governance_checked",
                timestamp="2026-03-30T00:00:12+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-14",
                event_name="response_synthesized",
                timestamp="2026-03-30T00:00:13+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "jarvis-core-v2",
                    "response_style": "analytical_unified",
                },
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
            InternalEventEnvelope(
                event_id="evt-15",
                event_name="memory_recorded",
                timestamp="2026-03-30T00:00:14+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cut",
                session_id="sess-cut",
                correlation_id="req-cut",
            ),
        ]
    )

    payload = build_payload(
        observability_db=str(observability_db),
        evolution_db=str(evolution_db),
        comparison_json=str(comparison_json),
        limit=10,
    )

    assert payload["decision"] == "complete_v2_sovereign_alignment_cut"
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
    assert payload["evidence_summary"]["candidate_expanded_eval_readiness"] == "candidate_ready"
    assert payload["evidence_summary"]["candidate_wave2_lane_health"] == "controlled_candidate"
    assert payload["evidence_summary"]["candidate_experiment_release_status"] == "hold_in_lane"
    assert payload["evidence_summary"]["candidate_optimization_target_kind"] == "workflow"
    assert payload["evidence_summary"]["candidate_optimization_readiness"] == "candidate_ready"
    assert payload["evidence_summary"]["candidate_optimization_release_status"] == "hold_in_lane"
    assert payload["next_cut_scope"][0]["item_id"] == "v2-domain-consumers-and-specialists"


def test_close_sovereign_alignment_cut_renders_markdown() -> None:
    payload = {
        "cut_id": "v2-sovereign-alignment-cut-1",
        "decision": "complete_v2_sovereign_alignment_cut",
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
            "matched_scenarios": 5,
            "divergent_scenarios": 0,
            "baseline_axis_adherence_score": 0.95,
            "candidate_axis_adherence_score": 0.97,
            "baseline_axis_gate_pass_rate": 1.0,
            "candidate_axis_gate_pass_rate": 1.0,
            "candidate_runtime_coverage": 1.0,
            "baseline_workflow_profile_decision": "baseline_saudavel",
            "candidate_workflow_profile_decision": "maturation_recommended",
            "baseline_workflow_baseline_rate": 1.0,
            "candidate_workflow_baseline_rate": 0.6,
            "baseline_workflow_maturation_rate": 0.0,
            "candidate_workflow_maturation_rate": 0.4,
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
            "baseline_expanded_eval_readiness": "baseline_only",
            "candidate_expanded_eval_readiness": "candidate_ready",
            "baseline_wave2_lane_health": "baseline_only",
            "candidate_wave2_lane_health": "controlled_candidate",
            "baseline_experiment_release_status": "hold_baseline",
            "candidate_experiment_release_status": "hold_in_lane",
            "baseline_promotion_blocker_rate": 0.0,
            "candidate_promotion_blocker_rate": 0.0,
            "baseline_optimization_target_kind": "not_applicable",
            "candidate_optimization_target_kind": "workflow",
            "baseline_optimization_readiness": "hold_baseline",
            "candidate_optimization_readiness": "candidate_ready",
            "baseline_optimization_release_status": "hold_baseline",
            "candidate_optimization_release_status": "hold_in_lane",
            "baseline_optimization_candidate_ready_rate": 0.0,
            "candidate_optimization_candidate_ready_rate": 0.5,
            "baseline_optimization_blocked_rate": 0.0,
            "candidate_optimization_blocked_rate": 0.0,
        },
        "next_cut_scope": [
            {
                "item_id": "v2-domain-consumers-and-specialists",
                "title": "consumidores canonicos de dominio acima do guided atual",
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
                "item_id": "vision-robust-absorbing-ecosystem",
                "title": "ecossistema robusto capaz de absorver o melhor do estado da arte",
                "target_class": "preservar_como_visao",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "goals_met": ["goal one"],
        "decision_rationale": "decisao racional",
    }

    rendered = render_markdown(payload)

    assert "Fechamento do V2 Sovereign Alignment Cut" in rendered
    assert "complete_v2_sovereign_alignment_cut" in rendered
    assert "consumidores canonicos de dominio acima do guided atual" in rendered
    assert "ecossistema robusto capaz de absorver o melhor do estado da arte" in rendered
    assert "candidate workflow profile decision" in rendered
    assert "candidate memory causality decision" in rendered
    assert "candidate mind-domain-specialist decision" in rendered
    assert "candidate cognitive recomposition decision" in rendered
    assert "candidate expanded eval readiness" in rendered
    assert "candidate wave2 lane health" in rendered
    assert "candidate experiment release status" in rendered
    assert "candidate optimization release status" in rendered
