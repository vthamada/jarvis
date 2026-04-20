"""Verify release-grade signal grammar for the active v2 baseline."""

from __future__ import annotations

from pathlib import Path
from sys import path as sys_path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _make_result(  # type: ignore[no-untyped-def]
    *,
    scenario_id: str,
    path_name: str,
    workflow_profile_status: str = "healthy",
    metacognitive_guidance_status: str = "healthy",
    mind_disagreement_status: str = "not_applicable",
    mind_validation_checkpoint_status: str = "not_applicable",
    memory_causality_status: str = "causal_guidance",
    memory_maintenance_status: str = "compaction_active",
    memory_maintenance_effectiveness: str = "effective",
    context_compaction_status: str | None = "compressed_live_context",
    cross_session_recall_status: str | None = "active",
    memory_lifecycle_status: str = "retained",
    memory_review_status: str = "stable",
    memory_corpus_status: str = "stable",
    memory_retention_pressure: str | None = "low",
    workflow_checkpoint_status: str = "healthy",
    workflow_resume_status: str = "fresh_start",
    workflow_pending_checkpoint_count: int = 0,
    workflow_output_status: str = "coherent",
    adaptive_intervention_status: str = "not_applicable",
    adaptive_intervention_reason: str | None = None,
    adaptive_intervention_trigger: str | None = None,
    adaptive_intervention_selected_action: str | None = None,
    adaptive_intervention_effectiveness: str = "not_applicable",
    procedural_artifact_status: str = "reusable",
    procedural_artifact_version: int | None = 1,
    mind_domain_specialist_status: str = "aligned",
    mind_domain_specialist_chain_status: str = "aligned",
    mind_domain_specialist_effectiveness: str = "effective",
    mind_domain_specialist_mismatch_flags: list[str] | None = None,
    cognitive_recomposition_applied: bool = False,
    cognitive_recomposition_reason: str | None = None,
    cognitive_recomposition_trigger: str | None = None,
    dominant_tension: str | None = "equilibrar profundidade analitica com conclusao util",
    primary_mind: str | None = "analise_estruturada",
    primary_route: str | None = "analysis",
    primary_domain_driver: str | None = "dados_estatistica_e_inteligencia_analitica",
    semantic_memory_source: str | None = "active_mission",
    procedural_memory_source: str | None = "active_mission",
    semantic_memory_focus: list[str] | None = None,
    procedural_memory_hint: str | None = "preservar criterio de comparacao mais recente",
    adaptive_intervention_policy_status: str = "not_applicable",
    request_identity_status: str = "healthy",
    mission_policy_status: str = "policy_aligned",
    request_identity_mismatch_flags: list[str] | None = None,
) -> Any:
    from tools.internal_pilot_support import PilotExecutionResult

    return PilotExecutionResult(
        scenario_id=scenario_id,
        path_name=path_name,
        request_id=f"req-{path_name}-{scenario_id}",
        session_id=f"sess-{scenario_id}",
        mission_id=None,
        intent="analysis",
        governance_decision="allow_with_conditions",
        expected_decision="allow_with_conditions",
        decision_matches_expectation=True,
        operation_status=None,
        expected_operation=False,
        operation_matches_expectation=True,
        continuity_action="continuar",
        continuity_source="active_mission",
        continuity_runtime_mode="baseline_linear",
        specialist_subflow_status="healthy",
        specialist_subflow_runtime_mode="native_pipeline",
        mission_runtime_state_status="healthy",
        workflow_domain_route="analysis",
        registry_domains=["analysis"],
        shadow_specialists=[],
        domain_alignment_status="healthy",
        mind_alignment_status="healthy",
        identity_alignment_status="healthy",
        memory_alignment_status="healthy",
        specialist_sovereignty_status="healthy",
        axis_gate_status="healthy",
        workflow_trace_status="healthy",
        workflow_checkpoint_status=workflow_checkpoint_status,
        workflow_resume_status=workflow_resume_status,
        workflow_pending_checkpoint_count=workflow_pending_checkpoint_count,
        workflow_profile_status=workflow_profile_status,
        workflow_output_status=workflow_output_status,
        metacognitive_guidance_status=metacognitive_guidance_status,
        mind_disagreement_status=mind_disagreement_status,
        mind_validation_checkpoint_status=mind_validation_checkpoint_status,
        request_identity_status=request_identity_status,
        mission_policy_status=mission_policy_status,
        request_identity_mismatch_flags=request_identity_mismatch_flags or [],
        adaptive_intervention_status=adaptive_intervention_status,
        adaptive_intervention_reason=adaptive_intervention_reason,
        adaptive_intervention_trigger=adaptive_intervention_trigger,
        adaptive_intervention_selected_action=adaptive_intervention_selected_action,
        adaptive_intervention_effectiveness=adaptive_intervention_effectiveness,
        adaptive_intervention_policy_status=adaptive_intervention_policy_status,
        memory_causality_status=memory_causality_status,
        memory_maintenance_status=memory_maintenance_status,
        memory_maintenance_reason=(
            "memory pressure requires review before expanding reuse"
            if memory_maintenance_status == "review_required"
            else "live context was compacted to preserve bounded continuity"
            if memory_maintenance_status == "compaction_active"
            else "cross-session recall is active and remains bounded to sovereign summaries"
            if memory_maintenance_status == "cross_session_recall_active"
            else "live memory is stable under the current bounded context"
        ),
        memory_maintenance_fallback_mode=(
            "review_before_reuse"
            if memory_maintenance_status == "review_required"
            else "minimal_context_only"
            if memory_maintenance_status == "compaction_active"
            else "summary_only_recall"
            if memory_maintenance_status == "cross_session_recall_active"
            else "none"
        ),
        memory_maintenance_effectiveness=memory_maintenance_effectiveness,
        context_compaction_status=context_compaction_status,
        cross_session_recall_status=cross_session_recall_status,
        primary_mind=primary_mind,
        primary_route=primary_route,
        dominant_tension=dominant_tension,
        arbitration_source="mind_registry",
        primary_domain_driver=primary_domain_driver,
        mind_domain_specialist_status=mind_domain_specialist_status,
        mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
        mind_domain_specialist_chain=(
            f"{primary_mind or 'none'} -> {primary_domain_driver or 'none'} -> "
            f"{primary_route or 'none'} -> specialists[structured_analysis_specialist]"
        ),
        mind_domain_specialist_effectiveness=mind_domain_specialist_effectiveness,
        mind_domain_specialist_mismatch_flags=(
            mind_domain_specialist_mismatch_flags or []
        ),
        cognitive_recomposition_applied=cognitive_recomposition_applied,
        cognitive_recomposition_reason=cognitive_recomposition_reason,
        cognitive_recomposition_trigger=cognitive_recomposition_trigger,
        semantic_memory_source=semantic_memory_source,
        procedural_memory_source=procedural_memory_source,
        semantic_memory_focus=semantic_memory_focus
        or ["dados_estatistica_e_inteligencia_analitica"],
        procedural_memory_hint=procedural_memory_hint,
        semantic_memory_effects=["framing", "continuity"],
        procedural_memory_effects=["next_action", "continuity"],
        semantic_memory_lifecycle="retained",
        procedural_memory_lifecycle="retained",
        memory_lifecycle_status=memory_lifecycle_status,
        memory_review_status=memory_review_status,
        procedural_artifact_status=procedural_artifact_status,
        procedural_artifact_refs=["artifact://procedural/analysis/structured_analysis_workflow/v1"],
        procedural_artifact_version=procedural_artifact_version,
        memory_corpus_status=memory_corpus_status,
        memory_retention_pressure=memory_retention_pressure,
        semantic_memory_specialists=["structured_analysis_specialist"],
        procedural_memory_specialists=["structured_analysis_specialist"],
        expected_continuity_action="continuar",
        continuity_matches_expectation=True,
        continuity_trace_status="healthy",
        missing_continuity_signals=[],
        continuity_anomaly_flags=[],
        trace_status="healthy",
        anomaly_flags=[],
        missing_required_events=[],
        total_events=12,
        duration_seconds=2.0,
        active_domains=["analysis"],
        specialist_hints=["structured_analysis_specialist"],
        response_preview="preview",
    )


def _make_pilot_trace_summary() -> Any:
    from tools.internal_pilot_report import PilotTraceSummary

    return PilotTraceSummary(
        request_id="req-release-signals",
        session_id="sess-release-signals",
        mission_id=None,
        total_events=12,
        event_names=["context_composed", "response_synthesized"],
        missing_required_events=[],
        anomaly_flags=[],
        continuity_action="continuar",
        continuity_source="active_mission",
        continuity_runtime_mode="baseline_linear",
        specialist_subflow_status="healthy",
        specialist_subflow_runtime_mode="native_pipeline",
        mission_runtime_state_status="healthy",
        workflow_domain_route="analysis",
        registry_domains=["dados_estatistica_e_inteligencia_analitica"],
        shadow_specialists=[],
        domain_alignment_status="healthy",
        mind_alignment_status="healthy",
        identity_alignment_status="healthy",
        memory_alignment_status="healthy",
        specialist_sovereignty_status="healthy",
        axis_gate_status="healthy",
        expectation_status="continuity_progressing",
        workflow_trace_status="healthy",
        workflow_checkpoint_status="attention_required",
        workflow_resume_status="manual_resume_required",
        workflow_pending_checkpoint_count=1,
        workflow_profile_status="maturation_recommended",
        workflow_profile_assessment="maturation_recommended",
        workflow_output_status="partial",
        workflow_output_assessment="maturation_recommended",
        metacognitive_guidance_status="healthy",
        mind_disagreement_status="validation_required",
        mind_validation_checkpoint_status="attention_required",
        request_identity_status="healthy",
        mission_policy_status="attention_required",
        request_identity_mismatch_flags=["confirmation_mode_mismatch"],
        adaptive_intervention_status="healthy",
        adaptive_intervention_reason="discordancia entre mentes exigiu checkpoint governado",
        adaptive_intervention_trigger="mind_validation_required",
        adaptive_intervention_selected_action="specialist_reevaluation",
        adaptive_intervention_effectiveness="effective",
        adaptive_intervention_policy_status="policy_aligned",
        memory_causality_status="attached_only",
        memory_maintenance_status="review_required",
        memory_maintenance_reason="memory pressure requires review before expanding reuse",
        memory_maintenance_fallback_mode="review_before_reuse",
        memory_maintenance_effectiveness="effective",
        context_compaction_status="compressed_live_context",
        cross_session_recall_status="active",
        primary_mind="analise_estruturada",
        primary_route="analysis",
        dominant_tension="equilibrar profundidade analitica com conclusao util",
        arbitration_source="mind_registry_recomposition",
        primary_domain_driver="assistencia_pessoal_e_operacional",
        mind_domain_specialist_status="mismatch",
        mind_domain_specialist_chain_status="attention_required",
        mind_domain_specialist_chain=(
            "analise_estruturada -> assistencia_pessoal_e_operacional -> analysis -> "
            "specialists[structured_analysis_specialist]"
        ),
        mind_domain_specialist_effectiveness="insufficient",
        mind_domain_specialist_mismatch_flags=["completed_specialist_mismatch"],
        cognitive_recomposition_applied=True,
        cognitive_recomposition_assessment="coherent",
        cognitive_recomposition_reason=(
            "primary domain driver has no matching guided specialist route"
        ),
        cognitive_recomposition_trigger="specialist_route_impasse",
        semantic_memory_source="related_mission",
        procedural_memory_source="active_mission",
        semantic_memory_focus=["produtividade_execucao_e_coordenacao"],
        procedural_memory_hint="preservar o fio decisorio anterior",
        semantic_memory_effects=["framing", "continuity"],
        procedural_memory_effects=["next_action", "continuity"],
        semantic_memory_lifecycle="promoted",
        procedural_memory_lifecycle="retained",
        memory_lifecycle_status="review_recommended",
        memory_review_status="review_recommended",
        procedural_artifact_status="candidate",
        procedural_artifact_refs=[
            "artifact://procedural/analysis/structured_analysis_workflow/v2"
        ],
        procedural_artifact_version=2,
        memory_corpus_status="review_recommended",
        memory_retention_pressure="high",
        semantic_memory_specialists=["structured_analysis_specialist"],
        procedural_memory_specialists=["structured_analysis_specialist"],
        continuity_trace_status="healthy",
        missing_continuity_signals=[],
        continuity_anomaly_flags=[],
        trace_status="healthy",
        governance_decision="defer_for_validation",
        operation_status=None,
        duration_seconds=2.4,
        source_services=["orchestrator-service"],
    )


def _make_closure_payload() -> dict[str, object]:
    evidence_summary = {
        "requests_audited": 2,
        "healthy_requests": 2,
        "incomplete_requests": 0,
        "attention_required_requests": 0,
        "domain_alignment_healthy": 2,
        "domain_alignment_partial": 0,
        "domain_alignment_incomplete": 0,
        "domain_alignment_attention_required": 0,
        "mind_alignment_healthy": 2,
        "mind_alignment_partial": 0,
        "mind_alignment_incomplete": 0,
        "mind_alignment_attention_required": 0,
        "identity_alignment_healthy": 2,
        "identity_alignment_partial": 0,
        "identity_alignment_incomplete": 0,
        "identity_alignment_attention_required": 0,
        "memory_alignment_healthy": 2,
        "memory_alignment_partial": 0,
        "memory_alignment_incomplete": 0,
        "memory_alignment_attention_required": 0,
        "sovereignty_healthy": 2,
        "sovereignty_incomplete": 0,
        "sovereignty_attention_required": 0,
        "axis_gate_healthy": 2,
        "axis_gate_partial": 0,
        "axis_gate_attention_required": 0,
        "recent_evolution_proposals": 1,
        "recent_evolution_decisions": 1,
        "comparison_overall_verdict": "equivalent",
        "comparison_decision": "candidate_ready_for_eval_gate",
        "matched_scenarios": 2,
        "divergent_scenarios": 0,
        "baseline_axis_adherence_score": 0.95,
        "candidate_axis_adherence_score": 0.97,
        "baseline_axis_gate_pass_rate": 1.0,
        "candidate_axis_gate_pass_rate": 1.0,
        "candidate_runtime_coverage": 1.0,
        "baseline_workflow_profile_decision": "baseline_saudavel",
        "candidate_workflow_profile_decision": "maturation_recommended",
        "baseline_workflow_baseline_rate": 1.0,
        "candidate_workflow_baseline_rate": 0.5,
        "baseline_workflow_maturation_rate": 0.0,
        "candidate_workflow_maturation_rate": 0.5,
        "baseline_workflow_output_decision": "baseline_saudavel",
        "candidate_workflow_output_decision": "maturation_recommended",
        "baseline_workflow_output_baseline_rate": 1.0,
        "candidate_workflow_output_baseline_rate": 0.5,
        "baseline_workflow_output_maturation_rate": 0.0,
        "candidate_workflow_output_maturation_rate": 0.5,
        "baseline_metacognitive_guidance_decision": "healthy",
        "candidate_metacognitive_guidance_decision": "healthy",
        "baseline_metacognitive_guidance_healthy_rate": 1.0,
        "candidate_metacognitive_guidance_healthy_rate": 1.0,
        "baseline_memory_causality_decision": "causal_guidance",
        "candidate_memory_causality_decision": "attached_only",
        "baseline_memory_causal_rate": 1.0,
        "candidate_memory_causal_rate": 0.5,
        "baseline_memory_attached_only_rate": 0.0,
        "candidate_memory_attached_only_rate": 0.5,
        "baseline_memory_lifecycle_decision": "retained",
        "candidate_memory_lifecycle_decision": "review_recommended",
        "baseline_memory_lifecycle_retained_rate": 1.0,
        "candidate_memory_lifecycle_retained_rate": 0.5,
        "baseline_memory_lifecycle_review_rate": 0.0,
        "candidate_memory_lifecycle_review_rate": 0.5,
        "baseline_workflow_checkpoint_decision": "healthy",
        "candidate_workflow_checkpoint_decision": "attention_required",
        "baseline_workflow_checkpoint_healthy_rate": 1.0,
        "candidate_workflow_checkpoint_healthy_rate": 0.5,
        "baseline_workflow_resume_decision": "fresh_start",
        "candidate_workflow_resume_decision": "manual_resume_required",
        "baseline_workflow_resume_available_rate": 0.0,
        "candidate_workflow_resume_available_rate": 0.0,
        "baseline_procedural_artifact_decision": "reusable",
        "candidate_procedural_artifact_decision": "candidate",
        "baseline_procedural_artifact_reusable_rate": 1.0,
        "candidate_procedural_artifact_reusable_rate": 0.5,
        "baseline_procedural_artifact_candidate_rate": 0.0,
        "candidate_procedural_artifact_candidate_rate": 0.5,
        "baseline_mind_domain_specialist_decision": "aligned",
        "candidate_mind_domain_specialist_decision": "mismatch",
        "baseline_mind_domain_specialist_alignment_rate": 1.0,
        "candidate_mind_domain_specialist_alignment_rate": 0.5,
        "baseline_mind_domain_specialist_chain_decision": "aligned",
        "candidate_mind_domain_specialist_chain_decision": "attention_required",
        "baseline_mind_domain_specialist_chain_alignment_rate": 1.0,
        "candidate_mind_domain_specialist_chain_alignment_rate": 0.5,
        "baseline_cognitive_recomposition_decision": "not_applicable",
        "candidate_cognitive_recomposition_decision": "coherent",
        "baseline_cognitive_recomposition_coherent_rate": 0.0,
        "candidate_cognitive_recomposition_coherent_rate": 0.5,
    }
    return {
        "cut_id": "v2-release-signals",
        "cycle_id": "v2-release-signals",
        "decision": "candidate_ready_for_eval_gate",
        "evidence_summary": evidence_summary,
        "next_cut_scope": [
            {
                "item_id": "next-cut",
                "title": "next cut",
                "target_class": "proximo_corte_v2",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "deferred_scope": [
            {
                "item_id": "deferred-cut",
                "title": "deferred cut",
                "target_class": "manter_deferido",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "vision_scope": [
            {
                "item_id": "vision-cut",
                "title": "vision cut",
                "target_class": "preservar_como_visao",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "goals_met": ["goal one"],
        "decision_rationale": "decisao racional",
    }


def main() -> None:
    from tools.archive.close_alignment_cycle import (
        render_markdown as render_alignment_markdown,
    )
    from tools.archive.close_sovereign_alignment_cut import (
        render_markdown as render_sovereign_markdown,
    )
    from tools.compare_orchestrator_paths import (
        compare_results,
        serialize_comparisons,
    )
    from tools.compare_orchestrator_paths import (
        render_text as render_comparison_text,
    )
    from tools.internal_pilot_report import render_text as render_pilot_text

    comparison_payload = serialize_comparisons(
        compare_results(
            [_make_result(scenario_id="baseline", path_name="baseline")],
            [
                _make_result(
                    scenario_id="baseline",
                    path_name="candidate",
                    workflow_profile_status="maturation_recommended",
                    workflow_output_status="partial",
                    metacognitive_guidance_status="healthy",
                    mind_disagreement_status="validation_required",
                    mind_validation_checkpoint_status="attention_required",
                    adaptive_intervention_status="healthy",
                    adaptive_intervention_reason=(
                        "discordancia entre mentes exigiu checkpoint governado"
                    ),
                    adaptive_intervention_trigger="mind_validation_required",
                    adaptive_intervention_selected_action="specialist_reevaluation",
                    adaptive_intervention_effectiveness="effective",
                    adaptive_intervention_policy_status="policy_aligned",
                    memory_causality_status="attached_only",
                    memory_maintenance_status="review_required",
                    memory_maintenance_effectiveness="effective",
                    context_compaction_status="compressed_live_context",
                    cross_session_recall_status="active",
                    memory_lifecycle_status="review_recommended",
                    memory_review_status="review_recommended",
                    memory_corpus_status="review_recommended",
                    memory_retention_pressure="high",
                    workflow_checkpoint_status="attention_required",
                    workflow_resume_status="manual_resume_required",
                    workflow_pending_checkpoint_count=1,
                    procedural_artifact_status="candidate",
                    procedural_artifact_version=2,
                    mind_domain_specialist_status="mismatch",
                    mind_domain_specialist_chain_status="attention_required",
                    mind_domain_specialist_effectiveness="insufficient",
                    mind_domain_specialist_mismatch_flags=[
                        "completed_specialist_mismatch"
                    ],
                    cognitive_recomposition_applied=True,
                    cognitive_recomposition_reason=(
                        "primary domain driver has no matching guided specialist route"
                    ),
                    cognitive_recomposition_trigger="specialist_route_impasse",
                    dominant_tension=(
                        "equilibrar clareza executiva com a menor proxima acao segura"
                    ),
                    primary_mind="analise_estruturada",
                    primary_route="analysis",
                    primary_domain_driver="assistencia_pessoal_e_operacional",
                    semantic_memory_source="related_mission",
                    procedural_memory_source="active_mission",
                    semantic_memory_focus=["produtividade_execucao_e_coordenacao"],
                    procedural_memory_hint="preservar o fio decisorio anterior",
                )
            ],
        ),
        profile="development",
        langgraph_status="available",
    )
    comparison_text = render_comparison_text(comparison_payload)
    pilot_text = render_pilot_text([_make_pilot_trace_summary()])
    closure_payload = _make_closure_payload()
    alignment_markdown = render_alignment_markdown(closure_payload)
    sovereign_markdown = render_sovereign_markdown(closure_payload)

    summary = comparison_payload["comparison_summary"]
    scenario = comparison_payload["scenario_results"][0]
    _ensure(
        summary["candidate_workflow_output_decision"] == "maturation_recommended",
        "Comparison summary lost the workflow output release decision.",
    )
    _ensure(
        summary["candidate_cognitive_recomposition_decision"] == "coherent",
        "Comparison summary lost the cognitive recomposition release decision.",
    )
    _ensure(
        summary["candidate_metacognitive_guidance_decision"] == "healthy",
        "Comparison summary lost the metacognitive guidance release decision.",
    )
    _ensure(
        summary["candidate_memory_causality_decision"] == "attached_only",
        "Comparison summary lost the memory causality release decision.",
    )
    _ensure(
        summary["candidate_memory_lifecycle_decision"] == "review_recommended",
        "Comparison summary lost the memory lifecycle release decision.",
    )
    _ensure(
        summary["candidate_mind_disagreement_decision"] == "validation_required",
        "Comparison summary lost the mind disagreement release decision.",
    )
    _ensure(
        summary["candidate_mind_validation_checkpoint_decision"] == "attention_required",
        "Comparison summary lost the mind validation checkpoint release decision.",
    )
    _ensure(
        summary["candidate_adaptive_intervention_policy_decision"] == "policy_aligned",
        "Comparison summary lost the adaptive intervention policy release decision.",
    )
    _ensure(
        summary["candidate_memory_corpus_decision"] == "review_recommended",
        "Comparison summary lost the memory corpus release decision.",
    )
    _ensure(
        summary["candidate_workflow_checkpoint_decision"] == "attention_required",
        "Comparison summary lost the workflow checkpoint release decision.",
    )
    _ensure(
        summary["candidate_workflow_resume_decision"] == "manual_resume_required",
        "Comparison summary lost the workflow resume release decision.",
    )
    _ensure(
        summary["candidate_procedural_artifact_decision"] == "candidate",
        "Comparison summary lost the procedural artifact release decision.",
    )
    _ensure(
        summary["candidate_mind_domain_specialist_decision"] == "mismatch",
        "Comparison summary lost the mind-domain-specialist release decision.",
    )
    _ensure(
        summary["candidate_mind_domain_specialist_chain_decision"]
        == "attention_required",
        "Comparison summary lost the mind-domain-specialist chain release decision.",
    )
    _ensure(
        summary["candidate_mind_domain_specialist_effectiveness_decision"]
        == "insufficient",
        "Comparison summary lost the mind-domain-specialist effectiveness release decision.",
    )
    _ensure(
        summary["candidate_mind_domain_specialist_mismatch_decision"] == "mismatch",
        "Comparison summary lost the mind-domain-specialist mismatch release decision.",
    )
    _ensure(
        scenario["candidate_workflow_output_assessment"] == "maturation_recommended",
        "Scenario comparison lost the workflow output assessment.",
    )
    _ensure(
        scenario["candidate_mind_disagreement_assessment"] == "validation_required",
        "Scenario comparison lost the mind disagreement assessment.",
    )
    _ensure(
        scenario["candidate_mind_validation_checkpoint_assessment"]
        == "attention_required",
        "Scenario comparison lost the mind validation checkpoint assessment.",
    )
    _ensure(
        scenario["candidate_adaptive_intervention_policy_assessment"]
        == "policy_aligned",
        "Scenario comparison lost the adaptive intervention policy assessment.",
    )
    _ensure(
        scenario["candidate_memory_corpus_assessment"] == "review_recommended",
        "Scenario comparison lost the memory corpus assessment.",
    )
    _ensure(
        scenario["candidate_workflow_checkpoint_assessment"] == "attention_required",
        "Scenario comparison lost the workflow checkpoint assessment.",
    )
    _ensure(
        scenario["candidate_workflow_resume_assessment"] == "manual_resume_required",
        "Scenario comparison lost the workflow resume assessment.",
    )
    _ensure(
        scenario["candidate_procedural_artifact_assessment"] == "candidate",
        "Scenario comparison lost the procedural artifact assessment.",
    )
    _ensure(
        scenario["candidate_cognitive_recomposition_assessment"] == "coherent",
        "Scenario comparison lost the recomposition assessment.",
    )
    _ensure(
        "candidate_workflow_output_decision=maturation_recommended" in comparison_text,
        "Comparison text lost the workflow output release line.",
    )
    _ensure(
        "candidate_metacognitive_guidance_decision=healthy" in comparison_text,
        "Comparison text lost the metacognitive guidance release line.",
    )
    _ensure(
        "candidate_mind_disagreement_decision=validation_required" in comparison_text,
        "Comparison text lost the mind disagreement release line.",
    )
    _ensure(
        "candidate_mind_validation_checkpoint_decision=attention_required"
        in comparison_text,
        "Comparison text lost the mind validation checkpoint release line.",
    )
    _ensure(
        "candidate_adaptive_intervention_policy_decision=policy_aligned"
        in comparison_text,
        "Comparison text lost the adaptive intervention policy release line.",
    )
    _ensure(
        "candidate_memory_corpus_decision=review_recommended" in comparison_text,
        "Comparison text lost the memory corpus release line.",
    )
    _ensure(
        "candidate_workflow_checkpoint_decision=attention_required" in comparison_text,
        "Comparison text lost the workflow checkpoint release line.",
    )
    _ensure(
        "candidate_workflow_resume_decision=manual_resume_required" in comparison_text,
        "Comparison text lost the workflow resume release line.",
    )
    _ensure(
        "candidate_procedural_artifact_decision=candidate" in comparison_text,
        "Comparison text lost the procedural artifact release line.",
    )
    _ensure(
        "candidate_refinement_axes=" in comparison_text
        and "mind_composition" in comparison_text
        and "mind_domain_specialist_effectiveness" in comparison_text
        and "memory_corpus" in comparison_text
        and "workflow_profile" in comparison_text,
        "Comparison text lost the refinement vector summary.",
    )
    _ensure(
        "candidate_evaluation_matrix_workflows=analysis" in comparison_text,
        "Comparison text lost the evaluation matrix workflow summary.",
    )
    _ensure(
        "candidate_cognitive_recomposition_decision=coherent" in comparison_text,
        "Comparison text lost the recomposition release line.",
    )
    _ensure(
        "candidate_memory_lifecycle_decision=review_recommended" in comparison_text,
        "Comparison text lost the memory lifecycle release line.",
    )
    _ensure(
        "candidate_mind_domain_specialist_effectiveness_decision=insufficient"
        in comparison_text,
        "Comparison text lost the mind-domain-specialist effectiveness release line.",
    )
    _ensure(
        "candidate_mind_domain_specialist_mismatch_decision=mismatch"
        in comparison_text,
        "Comparison text lost the mind-domain-specialist mismatch release line.",
    )
    _ensure(
        "cognitive_recomposition_assessment=coherent" in pilot_text,
        "Pilot report text lost the recomposition assessment.",
    )
    _ensure(
        "workflow_output_status=partial" in pilot_text,
        "Pilot report text lost the workflow output assessment.",
    )
    _ensure(
        "mind_disagreement_status=validation_required" in pilot_text,
        "Pilot report text lost the mind disagreement assessment.",
    )
    _ensure(
        "memory_corpus_status=review_recommended" in pilot_text,
        "Pilot report text lost the memory corpus assessment.",
    )
    _ensure(
        "workflow_checkpoint_status=attention_required" in pilot_text,
        "Pilot report text lost the workflow checkpoint assessment.",
    )
    _ensure(
        "workflow_resume_status=manual_resume_required" in pilot_text,
        "Pilot report text lost the workflow resume assessment.",
    )
    _ensure(
        "adaptive_intervention_policy_status=policy_aligned" in pilot_text,
        "Pilot report text lost the adaptive intervention policy assessment.",
    )
    _ensure(
        "memory_maintenance_status=review_required" in pilot_text,
        "Pilot report text lost the live-memory maintenance status.",
    )
    _ensure(
        "context_compaction_status=compressed_live_context" in pilot_text,
        "Pilot report text lost the context compaction signal.",
    )
    _ensure(
        "cross_session_recall_status=active" in pilot_text,
        "Pilot report text lost the cross-session recall signal.",
    )
    _ensure(
        "mind_domain_specialist_effectiveness=insufficient" in pilot_text,
        "Pilot report text lost the mind-domain-specialist effectiveness assessment.",
    )
    _ensure(
        "mind_domain_specialist_mismatch_flags=completed_specialist_mismatch"
        in pilot_text,
        "Pilot report text lost the mind-domain-specialist mismatch assessment.",
    )
    _ensure(
        "procedural_artifact_status=candidate" in pilot_text,
        "Pilot report text lost the procedural artifact assessment.",
    )
    _ensure(
        "memory_lifecycle_status=review_recommended" in pilot_text,
        "Pilot report text lost the memory lifecycle assessment.",
    )
    _ensure(
        "candidate cognitive recomposition decision" in alignment_markdown,
        "Alignment closure markdown lost the recomposition section.",
    )
    _ensure(
        "candidate cognitive recomposition decision" in sovereign_markdown,
        "Sovereign closure markdown lost the recomposition section.",
    )

    print("[verify-release-signal-baseline] release signal grammar is coherent")


if __name__ == "__main__":
    main()
