from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from evolution_lab.service import (
    ComparisonInput,
    EvolutionLabService,
    FlowEvaluationInput,
    PostTaskReflectionInput,
    TechnologyAbsorptionInput,
)

from shared.contracts import ProceduralPlaybookCandidateContract


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


def test_evolution_lab_registers_governed_technology_absorption_candidate() -> None:
    temp_dir = runtime_dir("evolution-lab-technology-absorption")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://openai-agents-sdk/handoff-adapters",
            technology_name="OpenAI Agents SDK",
            absorption_class="promotable_translation",
            target_gap_refs=["TA-005"],
            hypothesis="Handoff adapter semantics can improve bounded edge tracing.",
            expected_gain="Clearer handoff evidence without replacing the core.",
            source_refs=["source://technology-absorption-order/openai-agents-sdk"],
            evidence_refs=["evidence://comparison/handoff-adapter"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            risk_hint="moderate",
            status="validated",
            requested_core_role="adapter",
            rollback_plan_ref="rollback://sovereign-core/current",
        ),
        target_scope="orchestrator-service",
    )

    state = proposal.strategy_context["technology_absorption_state"]
    matrix = proposal.evaluation_matrix["technology_absorption"]

    assert proposal.proposal_type == "technology_absorption_candidate"
    assert proposal.requires_sandbox is True
    assert proposal.candidate_refs == [
        "tech-candidate://openai-agents-sdk/handoff-adapters"
    ]
    assert state["absorption_decision"] == "manual_promotion_review"
    assert state["promotion_readiness"] == "manual_review_only"
    assert matrix["absorption_class"] == "promotable_translation"
    assert matrix["blockers"] == []
    assert "technology://readiness/ready_for_manual_review" in proposal.source_signals
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert service.list_recent_proposals(limit=1)[0].target_scope == "orchestrator-service"


def test_evolution_lab_blocks_technology_candidate_that_requests_core_role() -> None:
    temp_dir = runtime_dir("evolution-lab-technology-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://external-core",
            technology_name="External Core Runtime",
            absorption_class="sandbox_experiment",
            target_gap_refs=["RH-001"],
            hypothesis="External runtime could replace central reasoning.",
            expected_gain="Not accepted because it violates core sovereignty.",
            evidence_refs=["evidence://claim"],
            proposed_tests=["pytest tests/unit"],
            requested_core_role="core_brain",
            rollback_plan_ref="rollback://baseline",
        )
    )

    state = proposal.strategy_context["technology_absorption_state"]
    assert state["absorption_decision"] == "block_absorption"
    assert state["promotion_readiness"] == "blocked"
    assert "technology://blocker/core_sovereignty_violation" in proposal.source_signals
    assert proposal.strategy_context["promotion_policy"]["core_replacement_allowed"] is False


def test_evolution_lab_creates_sandbox_proposal_from_post_task_reflection() -> None:
    temp_dir = runtime_dir("evolution-lab-reflection")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reflection/001",
            mission_id="mission-reflection",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Contract-first slices reduced implementation drift.",
            recommendation="Promote a bounded checklist only after tests.",
            evidence_refs=["trace://req-reflection"],
            signal_refs=["workflow_output_status:coherent"],
            proposed_change_type="workflow",
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )

    assert proposal.proposal_type == "post_task_reflection_improvement"
    assert proposal.requires_sandbox is True
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert proposal.strategy_context["promotion_policy"]["core_mutation_allowed"] is False
    assert proposal.strategy_context["evolution_review"]["review_status"] == "needs_review"
    assert (
        proposal.strategy_context["evolution_review"]["promotion_blocked_without_gate"]
        is True
    )
    assert proposal.evaluation_matrix["post_task_reflection"]["reflection_status"] == (
        "candidate"
    )
    review_items = service.list_human_review_queue(limit=5)
    assert review_items[0].review_status == "needs_review"
    assert review_items[0].requires_human_review is True
    assert review_items[0].requires_sandbox is True
    assert review_items[0].rollback_plan_ref == "rollback://workflow/current"
    assert "experience://mission-reflection/001" in review_items[0].candidate_refs


def test_evolution_lab_blocks_reflection_that_requests_autopromotion() -> None:
    temp_dir = runtime_dir("evolution-lab-reflection-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reflection-blocked/001",
            mission_id="mission-reflection-blocked",
            workflow_profile="strategic_direction_workflow",
            outcome_status="partial",
            learning_candidate="Mutate the core automatically.",
            recommendation="Apply without human review.",
            automatic_promotion_allowed=True,
            core_mutation_allowed=True,
        )
    )

    assert proposal.optimization_candidate_status == "blocked"
    assert proposal.optimization_safety_status == "blocked_by_safety"
    assert "automatic_promotion_not_allowed" in proposal.optimization_blockers
    assert "core_mutation_not_allowed" in proposal.optimization_blockers
    assert "evidence_required" in proposal.optimization_blockers


def test_evolution_lab_records_human_review_decision_for_proposal() -> None:
    temp_dir = runtime_dir("evolution-lab-human-review")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-human-review/001",
            mission_id="mission-human-review",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Reviewable learning should be approved by a human.",
            recommendation="Sandbox the change before any promotion.",
            evidence_refs=["trace://req-human-review"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )

    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-human-review"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/current",
        risk_acceptance="bounded_sandbox_only",
    )
    review_items = service.list_human_review_queue(limit=5)
    recent_decisions = service.list_recent_decisions(limit=5)

    assert decision.review_status == "approved"
    assert decision.automatic_promotion_allowed is False
    assert decision.core_mutation_allowed is False
    assert review_items[0].review_status == "approved"
    assert review_items[0].rollback_plan_ref == "rollback://workflow/current"
    assert recent_decisions[0].decision == "human_approve"
    assert recent_decisions[0].promoted_to is None


def test_evolution_lab_derives_reviewed_learning_guidance_from_human_review() -> None:
    temp_dir = runtime_dir("evolution-lab-reviewed-guidance")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reviewed-guidance/001",
            mission_id="mission-reviewed-guidance",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Prefer small reviewed code changes.",
            recommendation="Use reviewed learning as planning guidance only.",
            evidence_refs=["trace://req-reviewed-guidance"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/reviewed-guidance",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-reviewed-guidance"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/reviewed-guidance",
    )

    guidance = service.derive_reviewed_learning_guidance(decision)

    assert guidance.source_review_decision_id == decision.review_decision_id
    assert guidance.evolution_proposal_id == proposal.evolution_proposal_id
    assert guidance.review_status == "sandboxed"
    assert guidance.workflow_profile == "software_change_workflow"
    assert guidance.route == "software_change_workflow"
    assert guidance.domain == "software_change_workflow"
    assert guidance.guidance_summary == "Use reviewed learning as planning guidance only."
    assert guidance.allowed_usage == [
        "sandbox_planning_context",
        "sandbox_synthesis_context",
        "evaluation_context",
    ]
    assert "trace://req-reviewed-guidance" in guidance.evidence_refs
    assert "baseline://sovereign-core/current" in guidance.evidence_refs
    assert guidance.rollback_plan_ref == "rollback://workflow/reviewed-guidance"
    assert guidance.automatic_promotion_allowed is False
    assert guidance.core_mutation_allowed is False


def test_evolution_lab_builds_sandbox_to_release_checklist() -> None:
    temp_dir = runtime_dir("evolution-lab-release-checklist")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-release-checklist/001",
            mission_id="mission-release-checklist",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Use reviewed release checklist.",
            recommendation="Promote only after release gate.",
            evidence_refs=["trace://req-release-checklist"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/release-checklist",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-release-checklist"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/release-checklist",
    )

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=decision,
    )

    assert checklist.checklist_status == "ready_for_release_review"
    assert checklist.human_review_status == "sandboxed"
    assert "human_review" in checklist.required_gates
    assert "standard_engineering_gate" in checklist.required_gates
    assert checklist.evidence_refs == ["trace://req-release-checklist"]
    assert checklist.proposed_tests == [
        "python tools/engineering_gate.py --mode standard"
    ]
    assert checklist.rollback_plan_ref == "rollback://workflow/release-checklist"
    assert checklist.blockers == []
    assert checklist.automatic_promotion_allowed is False
    assert checklist.core_mutation_allowed is False


def test_evolution_lab_blocks_release_checklist_with_foreign_review() -> None:
    temp_dir = runtime_dir("evolution-lab-foreign-release-review")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    first = service.create_proposal(
        proposal_type="review_integrity",
        target_scope="workflow:first",
        hypothesis="First bounded release candidate.",
        expected_gain="Validated release path.",
        baseline_refs=["baseline://release/first"],
        proposed_tests=["test:first"],
    )
    second = service.create_proposal(
        proposal_type="review_integrity",
        target_scope="workflow:second",
        hypothesis="Second bounded release candidate.",
        expected_gain="Validated release path.",
        baseline_refs=["baseline://release/second"],
        proposed_tests=["test:second"],
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(first.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://release/first"],
        proposed_tests=["test:first"],
        rollback_plan_ref="rollback://release/first",
    )

    with pytest.raises(
        ValueError,
        match="review decision does not belong to the evolution proposal",
    ):
        service.build_sandbox_to_release_checklist(
            second,
            review_decision=decision,
        )


def test_evolution_lab_creates_sandbox_proposal_from_procedural_playbook_candidate() -> None:
    temp_dir = runtime_dir("evolution-lab-procedural-playbook")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/001",
            procedure_name="bounded patch review",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            domain="engenharia_de_software",
            bounded_steps=[
                "collect evidence",
                "run targeted tests",
                "prepare rollback",
            ],
            evidence_refs=["trace://req-playbook"],
            source_artifact_refs=["artifact://procedural/software/v1"],
            source_reflection_refs=["reflection://mission/001"],
            proposed_tests=["pytest services/memory-service/tests"],
            rollback_plan_ref="rollback://playbook/001",
            timestamp="2026-07-04T00:00:00Z",
        )
    )

    assert proposal.proposal_type == "procedural_playbook_candidate"
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.optimization_safety_status == "sandbox_only"
    assert proposal.evaluation_matrix["procedural_playbook_candidate"][
        "manual_review_required"
    ] is True
    assert (
        proposal.strategy_context["promotion_policy"]["manual_review_required"]
        is True
    )
    assert (
        proposal.strategy_context["promotion_policy"]["automatic_promotion"]
        is False
    )
    assert (
        proposal.strategy_context["promotion_policy"]["release_gate_required"]
        is True
    )
    assert "playbook://promotion/manual_review_required" in proposal.source_signals


def test_evolution_lab_blocks_human_approval_without_required_evidence() -> None:
    temp_dir = runtime_dir("evolution-lab-human-review-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-human-review-blocked/001",
            mission_id="mission-human-review-blocked",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Unsafe approval without evidence.",
            recommendation="Should remain in review.",
        )
    )

    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
    )
    review_items = service.list_human_review_queue(limit=5)

    assert decision.review_status == "needs_review"
    assert "evidence_required_for_human_approval" in decision.review_notes
    assert "tests_required_for_human_approval" in decision.review_notes
    assert "rollback_required_for_human_approval" in decision.review_notes
    assert review_items[0].review_status == "needs_review"
    assert set(review_items[0].blockers) == {
        "evidence_required_for_human_approval",
        "tests_required_for_human_approval",
        "rollback_required_for_human_approval",
    }


def test_evolution_lab_blocks_guidance_from_unapproved_review() -> None:
    temp_dir = runtime_dir("evolution-lab-reviewed-guidance-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reviewed-guidance-blocked/001",
            mission_id="mission-reviewed-guidance-blocked",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Insufficient review should not influence runtime.",
            recommendation="Keep this learning out of planning.",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="needs-review",
        operator_ref="operator://local_console",
    )

    try:
        service.derive_reviewed_learning_guidance(decision)
    except ValueError as exc:
        assert "approved or sandboxed" in str(exc)
    else:
        raise AssertionError("unapproved review must not produce guidance")


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
