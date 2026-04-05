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
    memory_causality_status: str = "causal_guidance",
    mind_domain_specialist_status: str = "aligned",
    cognitive_recomposition_applied: bool = False,
    cognitive_recomposition_reason: str | None = None,
    cognitive_recomposition_trigger: str | None = None,
    dominant_tension: str | None = "equilibrar profundidade analitica com conclusao util",
    primary_domain_driver: str | None = "dados_estatistica_e_inteligencia_analitica",
    semantic_memory_focus: list[str] | None = None,
    procedural_memory_hint: str | None = "preservar criterio de comparacao mais recente",
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
        workflow_profile_status=workflow_profile_status,
        memory_causality_status=memory_causality_status,
        dominant_tension=dominant_tension,
        arbitration_source="mind_registry",
        primary_domain_driver=primary_domain_driver,
        mind_domain_specialist_status=mind_domain_specialist_status,
        cognitive_recomposition_applied=cognitive_recomposition_applied,
        cognitive_recomposition_reason=cognitive_recomposition_reason,
        cognitive_recomposition_trigger=cognitive_recomposition_trigger,
        semantic_memory_focus=semantic_memory_focus
        or ["dados_estatistica_e_inteligencia_analitica"],
        procedural_memory_hint=procedural_memory_hint,
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
        workflow_profile_status="maturation_recommended",
        workflow_profile_assessment="maturation_recommended",
        memory_causality_status="attached_only",
        dominant_tension="equilibrar profundidade analitica com conclusao util",
        arbitration_source="mind_registry_recomposition",
        primary_domain_driver="assistencia_pessoal_e_operacional",
        mind_domain_specialist_status="mismatch",
        cognitive_recomposition_applied=True,
        cognitive_recomposition_assessment="coherent",
        cognitive_recomposition_reason=(
            "primary domain driver has no matching guided specialist route"
        ),
        cognitive_recomposition_trigger="specialist_route_impasse",
        semantic_memory_focus=["produtividade_execucao_e_coordenacao"],
        procedural_memory_hint="preservar o fio decisorio anterior",
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
        "baseline_memory_causality_decision": "causal_guidance",
        "candidate_memory_causality_decision": "attached_only",
        "baseline_memory_causal_rate": 1.0,
        "candidate_memory_causal_rate": 0.5,
        "baseline_memory_attached_only_rate": 0.0,
        "candidate_memory_attached_only_rate": 0.5,
        "baseline_mind_domain_specialist_decision": "aligned",
        "candidate_mind_domain_specialist_decision": "mismatch",
        "baseline_mind_domain_specialist_alignment_rate": 1.0,
        "candidate_mind_domain_specialist_alignment_rate": 0.5,
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
                    memory_causality_status="attached_only",
                    mind_domain_specialist_status="mismatch",
                    cognitive_recomposition_applied=True,
                    cognitive_recomposition_reason=(
                        "primary domain driver has no matching guided specialist route"
                    ),
                    cognitive_recomposition_trigger="specialist_route_impasse",
                    dominant_tension=(
                        "equilibrar clareza executiva com a menor proxima acao segura"
                    ),
                    primary_domain_driver="assistencia_pessoal_e_operacional",
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
        summary["candidate_cognitive_recomposition_decision"] == "coherent",
        "Comparison summary lost the cognitive recomposition release decision.",
    )
    _ensure(
        summary["candidate_memory_causality_decision"] == "attached_only",
        "Comparison summary lost the memory causality release decision.",
    )
    _ensure(
        summary["candidate_mind_domain_specialist_decision"] == "mismatch",
        "Comparison summary lost the mind-domain-specialist release decision.",
    )
    _ensure(
        scenario["candidate_cognitive_recomposition_assessment"] == "coherent",
        "Scenario comparison lost the recomposition assessment.",
    )
    _ensure(
        "candidate_cognitive_recomposition_decision=coherent" in comparison_text,
        "Comparison text lost the recomposition release line.",
    )
    _ensure(
        "cognitive_recomposition_assessment=coherent" in pilot_text,
        "Pilot report text lost the recomposition assessment.",
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
