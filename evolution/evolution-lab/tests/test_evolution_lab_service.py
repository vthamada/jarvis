from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from evolution_lab.service import ComparisonInput, EvolutionLabService, FlowEvaluationInput


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_evolution_lab_service_name() -> None:
    assert EvolutionLabService.name == "evolution-lab"


def test_evolution_lab_defaults_to_manual_variants_strategy() -> None:
    temp_dir = runtime_dir("evolution-lab-default-strategy")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    assert service.preferred_strategy() == "manual_variants"
    assert service.resolve_strategy_name(None) == "manual_variants"
    assert service.resolve_strategy_name("unknown") == "manual_variants"
    assert "manual_variants" in service.list_supported_strategies()


def test_evolution_lab_persists_proposals_and_sandbox_candidate_decision() -> None:
    temp_dir = runtime_dir("evolution-lab")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="workflow_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate sequencing should improve stability without increasing risk.",
        expected_gain="Higher stability for the same low-risk profile.",
        baseline_refs=["baseline://orchestrator/current"],
        source_signals=["observability://flows/req-1"],
        proposed_tests=["pytest -q"],
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-a",
            baseline_metrics={"stability": 0.72, "risk": 0.2, "throughput": 0.5},
            candidate_metrics={"stability": 0.81, "risk": 0.18, "throughput": 0.56},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate kept sandbox-only"],
        ),
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.decision.promoted_to is None
    assert comparison.metric_deltas["stability"] > 0
    assert "strategy://manual_variants" in proposal.source_signals
    assert "preferred_strategy=manual_variants" in proposal.promotion_constraints
    assert proposal.selection_criteria == {}
    assert proposal.evaluation_matrix == {}
    assert "strategy=manual_variants" in comparison.decision.notes
    assert comparison.decision.selection_criteria["strategy"] == "manual_variants"
    assert comparison.decision.metric_deltas["stability"] > 0
    assert service.list_recent_proposals(limit=1)[0].target_scope == "orchestrator-service"
    assert service.list_recent_decisions(limit=1)[0].decision == "sandbox_candidate"


def test_evolution_lab_holds_baseline_when_risk_increases() -> None:
    temp_dir = runtime_dir("evolution-lab-hold")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="prompt_refinement",
        target_scope="synthesis-engine",
        hypothesis="A more aggressive style could improve throughput.",
        expected_gain="Faster synthesis.",
        baseline_refs=["baseline://synthesis/current"],
        strategy_name="textgrad_like_refinement",
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-risky",
            baseline_metrics={"stability": 0.8, "risk": 0.1},
            candidate_metrics={"stability": 0.78, "risk": 0.3},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate rejected for higher risk"],
            strategy_name="textgrad_like_refinement",
        ),
    )

    assert comparison.decision.decision == "hold_baseline"
    assert comparison.decision.rollback_plan_ref == "sandbox://rollback/current"
    assert "strategy://textgrad_like_refinement" in proposal.source_signals
    assert "strategy=textgrad_like_refinement" in comparison.decision.notes


def test_evolution_lab_creates_proposal_from_flow_evaluation() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-proposal")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_flow_evaluation(
        FlowEvaluationInput(
            request_id="req-flow",
            session_id="sess-flow",
            mission_id="mission-flow",
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.4,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            mind_alignment_status="partial",
            identity_alignment_status="healthy",
            axis_gate_status="attention_required",
            workflow_profile_status="maturation_recommended",
            workflow_output_status="partial",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="insufficient",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="attention_required",
            request_identity_mismatch_flags=["confirmation_mode_mismatch"],
            memory_causality_status="attached_only",
            workflow_checkpoint_status="attention_required",
            workflow_resume_status="manual_resume_required",
            procedural_artifact_status="candidate",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=2,
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_source="mind_registry",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="incomplete",
            mind_domain_specialist_effectiveness="incomplete",
            mind_domain_specialist_mismatch_flags=["dispatch_specialist_mismatch"],
            cognitive_recomposition_applied=True,
            cognitive_recomposition_reason=(
                "primary domain driver has no matching guided specialist route"
            ),
            cognitive_recomposition_trigger="specialist_route_impasse",
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        target_scope="orchestrator-service",
    )

    assert proposal.proposal_type == "flow_evaluation_refinement"
    assert "observability://request/req-flow" in proposal.source_signals
    assert "continuity://action/retomar" in proposal.source_signals
    assert "continuity://runtime/langgraph_subflow" in proposal.source_signals
    assert "alignment://mind/partial" in proposal.source_signals
    assert "alignment://axis-gate/attention_required" in proposal.source_signals
    assert "workflow://profile-status/maturation_recommended" in proposal.source_signals
    assert "workflow://output-status/partial" in proposal.source_signals
    assert "runtime://adaptive-intervention-policy/policy_aligned" in proposal.source_signals
    assert "runtime://request-identity/healthy" in proposal.source_signals
    assert "runtime://mission-policy/attention_required" in proposal.source_signals
    assert (
        "runtime://request-identity-mismatch/confirmation_mode_mismatch"
        in proposal.source_signals
    )
    assert "memory://causality/attached_only" in proposal.source_signals
    assert "workflow://checkpoint-status/attention_required" in proposal.source_signals
    assert "artifact://procedural-status/candidate" in proposal.source_signals
    assert (
        "domain://primary-driver/dados_estatistica_e_inteligencia_analitica"
        in proposal.source_signals
    )
    assert "alignment://mind-domain-specialist/incomplete" in proposal.source_signals
    assert (
        "alignment://mind-domain-specialist-effectiveness/incomplete"
        in proposal.source_signals
    )
    assert (
        "alignment://mind-domain-specialist-mismatch/dispatch_specialist_mismatch"
        in proposal.source_signals
    )
    assert "mind://recomposition/applied" in proposal.source_signals
    assert proposal.risk_hint == "moderate"
    assert proposal.refinement_vectors[0]["axis"] in {
        "workflow_output",
        "metacognitive_guidance",
        "adaptive_intervention_policy",
        "memory_causality",
        "mind_composition",
        "mind_domain_specialist_chain",
        "mind_domain_specialist_effectiveness",
        "workflow_checkpointing",
    }
    assert "baseline_runtime" in proposal.evaluation_matrix
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mind_composition"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["adaptive_intervention_policy"]
        == "review_recommended"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["request_identity"] == "healthy"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mission_policy"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"][
            "mind_domain_specialist_effectiveness"
        ]
        == "incomplete"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mind_domain_specialist_mismatch"]
        == "mismatch"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["expanded_eval"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["surface_axis"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["ecosystem_state"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["experiment_lane"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["promotion_readiness"]
        == "blocked"
    )
    assert "wave_two_readiness_matrix" in proposal.strategy_context
    assert "controlled_wave2_experiment" in proposal.strategy_context
    assert (
        proposal.strategy_context["controlled_wave2_experiment"]["experiment_lane_status"]
        == "attention_required"
    )
    assert (
        proposal.strategy_context["wave_two_readiness_matrix"]["graphiti_zep"]["status"]
        == "stabilize_nucleus_first"
    )


def test_evolution_lab_compares_flow_evaluations() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-comparison")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="flow_evaluation_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate path should improve trace health.",
        expected_gain="Fewer anomalies.",
        baseline_refs=["trace://req-a"],
    )

    comparison = service.compare_flow_evaluations(
        proposal,
        baseline_label="baseline",
        candidate_label="candidate",
        baseline=FlowEvaluationInput(
            request_id="req-a",
            session_id="sess-a",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=7,
            duration_seconds=3.2,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="baseline_linear",
            mind_alignment_status="partial",
            identity_alignment_status="healthy",
            axis_gate_status="attention_required",
            workflow_profile_status="maturation_recommended",
            workflow_output_status="partial",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="insufficient",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="attention_required",
            request_identity_mismatch_flags=["confirmation_mode_mismatch"],
            memory_causality_status="attached_only",
            workflow_checkpoint_status="attention_required",
            workflow_resume_status="manual_resume_required",
            procedural_artifact_status="candidate",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=2,
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="incomplete",
            mind_domain_specialist_effectiveness="insufficient",
            mind_domain_specialist_mismatch_flags=["completed_specialist_mismatch"],
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        candidate=FlowEvaluationInput(
            request_id="req-b",
            session_id="sess-b",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.1,
            missing_required_events=[],
            anomaly_flags=[],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            mind_alignment_status="healthy",
            identity_alignment_status="healthy",
            axis_gate_status="healthy",
            workflow_profile_status="healthy",
            workflow_output_status="coherent",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="effective",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="policy_aligned",
            request_identity_mismatch_flags=[],
            memory_causality_status="causal_guidance",
            workflow_checkpoint_status="healthy",
            workflow_resume_status="resume_available",
            procedural_artifact_status="reusable",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=3,
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="aligned",
            mind_domain_specialist_effectiveness="effective",
            cognitive_recomposition_applied=True,
            cognitive_recomposition_reason=(
                "primary domain driver has no matching guided specialist route"
            ),
            cognitive_recomposition_trigger="specialist_route_impasse",
            continuity_trace_status="healthy",
        ),
        governance_refs=["policy://sandbox/manual-review"],
        notes=["pilot comparison"],
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.metric_deltas["risk"] < 0
    assert comparison.metric_deltas["continuity_health"] > 0
    assert comparison.metric_deltas["runtime_statefulness"] > 0
    assert comparison.metric_deltas["axis_gate"] > 0
    assert comparison.metric_deltas["workflow_profile"] > 0
    assert comparison.metric_deltas["workflow_output"] > 0
    assert comparison.metric_deltas["adaptive_intervention_policy"] > 0
    assert comparison.metric_deltas["mission_policy"] > 0
    assert comparison.metric_deltas["memory_causality"] > 0
    assert comparison.metric_deltas["workflow_checkpoint"] > 0
    assert comparison.metric_deltas["workflow_resume"] > 0
    assert comparison.metric_deltas["procedural_artifact"] > 0
    assert comparison.metric_deltas["mind_domain_specialist"] > 0
    assert comparison.metric_deltas["mind_domain_specialist_effectiveness"] > 0
    assert comparison.metric_deltas["mind_domain_specialist_mismatch"] > 0
