from pathlib import Path

from tools.compare_orchestrator_paths import (
    cognitive_recomposition_assessment,
    compare_results,
    render_text,
    resolve_output_dir,
    serialize_comparisons,
    summarize_comparisons,
    workflow_profile_assessment,
)
from tools.internal_pilot_support import PilotExecutionResult


def make_result(  # type: ignore[no-untyped-def]
    *,
    scenario_id: str,
    path_name: str,
    intent: str = "planning",
    governance_decision: str = "allow_with_conditions",
    expected_decision: str = "allow_with_conditions",
    decision_matches_expectation: bool = True,
    operation_status: str | None = "completed",
    expected_operation: bool = True,
    operation_matches_expectation: bool = True,
    continuity_action: str | None = "continuar",
    continuity_source: str | None = "active_mission",
    continuity_runtime_mode: str | None = "baseline_linear",
    specialist_subflow_status: str = "healthy",
    specialist_subflow_runtime_mode: str | None = "native_pipeline",
    mission_runtime_state_status: str = "healthy",
    workflow_domain_route: str | None = "strategy",
    registry_domains: list[str] | None = None,
    shadow_specialists: list[str] | None = None,
    domain_alignment_status: str = "healthy",
    mind_alignment_status: str = "healthy",
    identity_alignment_status: str = "healthy",
    memory_alignment_status: str = "healthy",
    specialist_sovereignty_status: str = "healthy",
    axis_gate_status: str = "healthy",
    workflow_trace_status: str = "healthy",
    workflow_checkpoint_status: str = "healthy",
    workflow_resume_status: str = "fresh_start",
    workflow_pending_checkpoint_count: int = 0,
    workflow_profile_status: str = "healthy",
    metacognitive_guidance_status: str = "healthy",
    mind_disagreement_status: str = "not_applicable",
    mind_validation_checkpoint_status: str = "not_applicable",
    memory_causality_status: str = "causal_guidance",
    memory_lifecycle_status: str = "retained",
    memory_review_status: str = "stable",
    memory_corpus_status: str = "stable",
    memory_retention_pressure: str | None = "low",
    procedural_artifact_status: str = "reusable",
    procedural_artifact_refs: list[str] | None = None,
    procedural_artifact_version: int | None = 1,
    primary_mind: str | None = "planejamento_estruturado",
    primary_route: str | None = "strategy",
    dominant_tension: str | None = "equilibrar profundidade analitica com conclusao util",
    arbitration_source: str | None = "mind_registry",
    primary_domain_driver: str | None = "dados_estatistica_e_inteligencia_analitica",
    mind_domain_specialist_status: str = "aligned",
    mind_domain_specialist_chain_status: str = "aligned",
    cognitive_recomposition_applied: bool = False,
    cognitive_recomposition_reason: str | None = None,
    cognitive_recomposition_trigger: str | None = None,
    semantic_memory_source: str | None = "active_mission",
    procedural_memory_source: str | None = "active_mission",
    semantic_memory_focus: list[str] | None = None,
    procedural_memory_hint: str | None = "preservar criterio de comparacao mais recente",
    semantic_memory_effects: list[str] | None = None,
    procedural_memory_effects: list[str] | None = None,
    semantic_memory_lifecycle: str | None = "retained",
    procedural_memory_lifecycle: str | None = "retained",
    semantic_memory_specialists: list[str] | None = None,
    procedural_memory_specialists: list[str] | None = None,
    expected_continuity_action: str | None = "continuar",
    continuity_matches_expectation: bool | None = True,
    continuity_trace_status: str = "healthy",
    continuity_anomaly_flags: list[str] | None = None,
    missing_continuity_signals: list[str] | None = None,
    trace_status: str = "healthy",
    anomaly_flags: list[str] | None = None,
    missing_required_events: list[str] | None = None,
) -> PilotExecutionResult:
    return PilotExecutionResult(
        scenario_id=scenario_id,
        path_name=path_name,
        request_id=f"req-{path_name}-{scenario_id}",
        session_id=f"sess-{scenario_id}",
        mission_id=None,
        intent=intent,
        governance_decision=governance_decision,
        expected_decision=expected_decision,
        decision_matches_expectation=decision_matches_expectation,
        operation_status=operation_status,
        expected_operation=expected_operation,
        operation_matches_expectation=operation_matches_expectation,
        continuity_action=continuity_action,
        continuity_source=continuity_source,
        continuity_runtime_mode=continuity_runtime_mode,
        specialist_subflow_status=specialist_subflow_status,
        specialist_subflow_runtime_mode=specialist_subflow_runtime_mode,
        mission_runtime_state_status=mission_runtime_state_status,
        workflow_domain_route=workflow_domain_route,
        registry_domains=registry_domains or ["strategy"],
        shadow_specialists=shadow_specialists or [],
        domain_alignment_status=domain_alignment_status,
        mind_alignment_status=mind_alignment_status,
        identity_alignment_status=identity_alignment_status,
        memory_alignment_status=memory_alignment_status,
        specialist_sovereignty_status=specialist_sovereignty_status,
        axis_gate_status=axis_gate_status,
        workflow_trace_status=workflow_trace_status,
        workflow_checkpoint_status=workflow_checkpoint_status,
        workflow_resume_status=workflow_resume_status,
        workflow_pending_checkpoint_count=workflow_pending_checkpoint_count,
        workflow_profile_status=workflow_profile_status,
        metacognitive_guidance_status=metacognitive_guidance_status,
        mind_disagreement_status=mind_disagreement_status,
        mind_validation_checkpoint_status=mind_validation_checkpoint_status,
        memory_causality_status=memory_causality_status,
        primary_mind=primary_mind,
        primary_route=primary_route,
        dominant_tension=dominant_tension,
        arbitration_source=arbitration_source,
        primary_domain_driver=primary_domain_driver,
        mind_domain_specialist_status=mind_domain_specialist_status,
        mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
        mind_domain_specialist_chain=(
            f"{primary_mind or 'none'} -> {primary_domain_driver or 'none'} -> "
            f"{primary_route or 'none'} -> specialists[operational_planning_specialist]"
        ),
        cognitive_recomposition_applied=cognitive_recomposition_applied,
        cognitive_recomposition_reason=cognitive_recomposition_reason,
        cognitive_recomposition_trigger=cognitive_recomposition_trigger,
        semantic_memory_source=semantic_memory_source,
        procedural_memory_source=procedural_memory_source,
        semantic_memory_focus=semantic_memory_focus
        or ["dados_estatistica_e_inteligencia_analitica"],
        procedural_memory_hint=procedural_memory_hint,
        semantic_memory_effects=semantic_memory_effects or ["framing", "continuity"],
        procedural_memory_effects=procedural_memory_effects or ["next_action", "continuity"],
        semantic_memory_lifecycle=semantic_memory_lifecycle,
        procedural_memory_lifecycle=procedural_memory_lifecycle,
        memory_lifecycle_status=memory_lifecycle_status,
        memory_review_status=memory_review_status,
        procedural_artifact_status=procedural_artifact_status,
        procedural_artifact_refs=procedural_artifact_refs
        or ["artifact://procedural/strategy/strategy_workflow/v1"],
        procedural_artifact_version=procedural_artifact_version,
        memory_corpus_status=memory_corpus_status,
        memory_retention_pressure=memory_retention_pressure,
        semantic_memory_specialists=semantic_memory_specialists
        or ["structured_analysis_specialist"],
        procedural_memory_specialists=procedural_memory_specialists
        or ["structured_analysis_specialist"],
        expected_continuity_action=expected_continuity_action,
        continuity_matches_expectation=continuity_matches_expectation,
        continuity_trace_status=continuity_trace_status,
        missing_continuity_signals=missing_continuity_signals or [],
        continuity_anomaly_flags=continuity_anomaly_flags or [],
        trace_status=trace_status,
        anomaly_flags=anomaly_flags or [],
        missing_required_events=missing_required_events or [],
        total_events=8,
        duration_seconds=2.0,
        active_domains=["strategy"],
        specialist_hints=["operational_planning_specialist"],
        response_preview="preview",
    )


def test_compare_results_flags_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            operation_status=None,
            trace_status="attention_required",
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == ["operation_status", "trace_status"]
    assert comparisons[0].core_match is False


def test_compare_results_flags_continuity_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline", continuity_action="retomar")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            continuity_action="continuar",
            workflow_domain_route="analysis",
            workflow_trace_status="attention_required",
            continuity_trace_status="attention_required",
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == [
        "continuity_action",
        "workflow_domain_route",
        "workflow_trace_status",
        "continuity_trace_status",
    ]


def test_compare_results_flags_axis_alignment_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            domain_alignment_status="partial",
            axis_gate_status="partial",
            shadow_specialists=["software_change_specialist"],
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == ["domain_alignment_status", "axis_gate_status"]


def test_compare_results_flags_release_signal_mismatch_fields() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [
        make_result(
            scenario_id="x",
            path_name="langgraph",
            workflow_profile_status="maturation_recommended",
            mind_disagreement_status="validation_required",
            mind_validation_checkpoint_status="attention_required",
            memory_causality_status="attached_only",
            memory_corpus_status="review_recommended",
            memory_retention_pressure="high",
            dominant_tension="equilibrar clareza executiva com a menor proxima acao segura",
            arbitration_source="mind_registry_recomposition",
            primary_domain_driver="assistencia_pessoal_e_operacional",
            mind_domain_specialist_status="mismatch",
            specialist_subflow_status="contained",
            mission_runtime_state_status="attention_required",
            cognitive_recomposition_applied=True,
            cognitive_recomposition_reason=(
                "primary domain driver has no matching guided specialist route"
            ),
            cognitive_recomposition_trigger="specialist_route_impasse",
            semantic_memory_focus=["produtividade_execucao_e_coordenacao"],
            procedural_memory_hint="preservar o fio decisorio anterior",
            semantic_memory_specialists=["operational_planning_specialist"],
            procedural_memory_specialists=["operational_planning_specialist"],
        )
    ]

    comparisons = compare_results(baseline, candidate)

    assert comparisons[0].mismatch_fields == [
        "workflow_profile_status",
        "mind_disagreement_status",
        "mind_validation_checkpoint_status",
        "memory_causality_status",
        "memory_corpus_status",
        "memory_retention_pressure",
        "dominant_tension",
        "arbitration_source",
        "primary_domain_driver",
        "mind_domain_specialist_status",
        "mind_domain_specialist_chain",
        "specialist_subflow_status",
        "mission_runtime_state_status",
        "cognitive_recomposition_applied",
        "cognitive_recomposition_reason",
        "cognitive_recomposition_trigger",
        "semantic_memory_focus",
        "procedural_memory_hint",
        "semantic_memory_specialists",
        "procedural_memory_specialists",
    ]


def test_serialize_comparisons_reports_equivalent_verdict() -> None:
    baseline = [make_result(scenario_id="x", path_name="baseline")]
    candidate = [make_result(scenario_id="x", path_name="langgraph")]

    payload = serialize_comparisons(
        compare_results(baseline, candidate),
        profile="development",
        langgraph_status="available",
    )

    assert payload["overall_verdict"] == "equivalent"
    assert payload["comparison_summary"]["decision"] == "candidate_requires_iteration"
    assert payload["comparison_summary"]["candidate_axis_gate_pass_rate"] == 1.0
    assert payload["scenario_results"][0]["baseline"]["workflow_profile_status"] == "healthy"
    assert payload["scenario_results"][0]["candidate"]["workflow_profile_status"] == "healthy"
    assert (
        payload["comparison_summary"]["baseline_workflow_profile_decision"]
        == "baseline_saudavel"
    )
    assert (
        payload["comparison_summary"]["candidate_workflow_profile_decision"]
        == "baseline_saudavel"
    )
    assert (
        payload["scenario_results"][0]["baseline_workflow_profile_assessment"]
        == "baseline_saudavel"
    )
    assert (
        payload["scenario_results"][0]["candidate_workflow_profile_assessment"]
        == "baseline_saudavel"
    )
    assert (
        payload["scenario_results"][0]["baseline_memory_causality_assessment"]
        == "causal_guidance"
    )
    assert (
        payload["scenario_results"][0]["baseline_mind_disagreement_assessment"]
        == "not_applicable"
    )
    assert (
        payload["scenario_results"][0]["baseline_mind_validation_checkpoint_assessment"]
        == "not_applicable"
    )
    assert (
        payload["scenario_results"][0]["baseline_memory_corpus_assessment"] == "stable"
    )
    assert (
        payload["scenario_results"][0]["baseline_mind_domain_specialist_assessment"]
        == "aligned"
    )
    assert (
        payload["scenario_results"][0]["baseline_specialist_subflow_assessment"]
        == "healthy"
    )
    assert (
        payload["scenario_results"][0]["baseline_mission_runtime_state_assessment"]
        == "healthy"
    )
    assert (
        payload["scenario_results"][0]["baseline_cognitive_recomposition_assessment"]
        == "not_applicable"
    )
    assert payload["comparison_summary"]["candidate_cognitive_recomposition_decision"] == (
        "not_applicable"
    )
    assert payload["comparison_summary"]["baseline_refinement_vectors"] == []
    assert "strategy" in payload["comparison_summary"]["baseline_evaluation_matrix"]


def test_render_text_reports_workflow_profile_status() -> None:
    payload = serialize_comparisons(
        compare_results(
            [make_result(scenario_id="x", path_name="baseline", workflow_profile_status="healthy")],
            [
                make_result(
                    scenario_id="x",
                    path_name="langgraph",
                    workflow_profile_status="maturation_recommended",
                    mind_disagreement_status="validation_required",
                    mind_validation_checkpoint_status="attention_required",
                    memory_corpus_status="monitor",
                    memory_retention_pressure="moderate",
                    workflow_checkpoint_status="attention_required",
                    workflow_resume_status="manual_resume_required",
                    workflow_pending_checkpoint_count=1,
                    procedural_artifact_status="candidate",
                    procedural_artifact_version=2,
                    cognitive_recomposition_applied=True,
                    cognitive_recomposition_reason=(
                        "primary domain driver has no matching guided specialist route"
                    ),
                    cognitive_recomposition_trigger="specialist_route_impasse",
                )
            ],
        ),
        profile="development",
        langgraph_status="available",
    )

    rendered = render_text(payload)

    assert "baseline_workflow_profile_status=healthy" in rendered
    assert "baseline_workflow_profile_assessment=baseline_saudavel" in rendered
    assert "candidate_workflow_profile_status=maturation_recommended" in rendered
    assert "candidate_workflow_profile_assessment=maturation_recommended" in rendered
    assert "candidate_workflow_profile_decision=maturation_recommended" in rendered
    assert "candidate_mind_disagreement_status=validation_required" in rendered
    assert "candidate_mind_disagreement_assessment=validation_required" in rendered
    assert (
        "candidate_mind_validation_checkpoint_status=attention_required" in rendered
    )
    assert (
        "candidate_mind_validation_checkpoint_assessment=attention_required" in rendered
    )
    assert "baseline_memory_causality_status=causal_guidance" in rendered
    assert "candidate_memory_causality_status=causal_guidance" in rendered
    assert "candidate_memory_corpus_status=monitor" in rendered
    assert "candidate_memory_corpus_assessment=monitor" in rendered
    assert "candidate_memory_retention_pressure=moderate" in rendered
    assert "candidate_workflow_checkpoint_status=attention_required" in rendered
    assert "candidate_workflow_checkpoint_assessment=attention_required" in rendered
    assert "candidate_workflow_resume_status=manual_resume_required" in rendered
    assert "candidate_workflow_resume_assessment=manual_resume_required" in rendered
    assert "candidate_procedural_artifact_status=candidate" in rendered
    assert "candidate_procedural_artifact_assessment=candidate" in rendered
    assert "baseline_mind_domain_specialist_status=aligned" in rendered
    assert "candidate_mind_domain_specialist_status=aligned" in rendered
    assert "baseline_specialist_subflow_status=healthy" in rendered
    assert "candidate_specialist_subflow_status=healthy" in rendered
    assert "baseline_mission_runtime_state_status=healthy" in rendered
    assert "candidate_mission_runtime_state_status=healthy" in rendered
    assert "candidate_cognitive_recomposition_assessment=coherent" in rendered
    assert "candidate_cognitive_recomposition_decision=coherent" in rendered
    assert (
        "candidate_refinement_axes="
        "mind_composition,memory_corpus,procedural_artifacts,workflow_checkpointing,"
        "workflow_profile,workflow_resume"
    ) in rendered
    assert "candidate_evaluation_matrix_workflows=strategy" in rendered


def test_workflow_profile_assessment_classifies_statuses() -> None:
    assert (
        workflow_profile_assessment(make_result(scenario_id="x", path_name="baseline"))
        == "baseline_saudavel"
    )
    assert (
        workflow_profile_assessment(
            make_result(
                scenario_id="x",
                path_name="baseline",
                workflow_profile_status="maturation_recommended",
            )
        )
        == "maturation_recommended"
    )
    assert (
        workflow_profile_assessment(
            make_result(
                scenario_id="x",
                path_name="baseline",
                workflow_profile_status="attention_required",
            )
        )
        == "attention_required"
    )


def test_cognitive_recomposition_assessment_classifies_statuses() -> None:
    assert (
        cognitive_recomposition_assessment(
            make_result(scenario_id="x", path_name="baseline")
        )
        == "not_applicable"
    )
    assert (
        cognitive_recomposition_assessment(
            make_result(
                scenario_id="x",
                path_name="baseline",
                cognitive_recomposition_applied=True,
                cognitive_recomposition_reason=(
                    "primary domain driver has no matching guided specialist route"
                ),
                cognitive_recomposition_trigger="specialist_route_impasse",
            )
        )
        == "coherent"
    )
    assert (
        cognitive_recomposition_assessment(
            make_result(
                scenario_id="x",
                path_name="baseline",
                cognitive_recomposition_applied=True,
                cognitive_recomposition_reason=None,
                cognitive_recomposition_trigger="specialist_route_impasse",
            )
        )
        == "attention_required"
    )


def test_summarize_comparisons_promotes_candidate_ready_gate() -> None:
    comparisons = compare_results(
        [make_result(scenario_id="x", path_name="baseline")],
        [
            make_result(
                scenario_id="x",
                path_name="langgraph",
                continuity_runtime_mode="langgraph_subflow",
            )
        ],
    )

    summary = summarize_comparisons(comparisons, langgraph_status="available")

    assert summary["decision"] == "candidate_ready_for_eval_gate"
    assert summary["candidate_runtime_coverage"] == 1.0
    assert summary["candidate_axis_gate_pass_rate"] == 1.0


def test_resolve_output_dir_defaults_to_stable_alignment_artifact_path() -> None:
    resolved = resolve_output_dir(None)

    assert str(resolved).endswith(str(Path(".jarvis_runtime") / "path_comparison_v2"))
