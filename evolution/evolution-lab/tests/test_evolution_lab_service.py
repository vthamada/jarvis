from dataclasses import replace
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
from memory_service.service import MemoryService

from shared.contracts import (
    ExperienceRecordContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    RecurringPatternEvidenceContract,
    SandboxToReleaseChecklistContract,
    SkillCandidateContract,
    SkillMiningRequestContract,
    WorkflowEvolutionRequestContract,
    WorkflowProfileVersionContract,
)
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    route_metadata_payload,
    workflow_definition_hash,
)
from shared.types import MissionId, RiskLevel


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


def test_evolution_lab_exposes_inactive_workflow_version_registry() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-version-registry")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:00:00Z",
        evidence_refs=["evidence://evolution-lab/workflow-baseline"],
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "operational_readiness_workflow"
    )
    candidate_steps = [*baseline.workflow_steps, "record candidate evidence"]
    candidate: WorkflowProfileVersionContract = replace(
        baseline,
        workflow_version_id=(
            "workflow-version://operational_readiness_workflow/1.1.0"
        ),
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=candidate_steps,
            workflow_checkpoints=baseline.workflow_checkpoints,
            workflow_decision_points=baseline.workflow_decision_points,
            success_criteria=baseline.success_criteria,
        ),
        workflow_steps=candidate_steps,
        evidence_refs=[*baseline.evidence_refs, "pattern://readiness/evidence"],
        proposed_tests=["test://workflow/readiness-candidate"],
        rollback_plan_ref="rollback://workflow/readiness/1.0.0",
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="record evidence before readiness recommendation",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )

    updated = service.register_workflow_candidate_version(registry, candidate)

    assert "evolution-lab://workflow-version-registry" in registry.evidence_refs
    assert updated.candidate_count == 1
    assert updated.versions[-1].lifecycle_status == "candidate_inactive"
    assert updated.versions[-1].runtime_activation_allowed is False
    assert updated.active_registry_mutation_allowed is False
    assert updated.automatic_promotion_allowed is False


def test_reviewed_memory_pattern_builds_only_inactive_workflow_candidate_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-candidate")
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    for index in (1, 2):
        experience_id = f"experience://workflow-candidate/{index}"
        memory.record_experience_reflection(
            experience=ExperienceRecordContract(
                experience_id=experience_id,
                mission_id=MissionId(f"mission-workflow-candidate-{index}"),
                workflow_profile="software_change_workflow",
                route="software_development",
                primary_domain_driver="software_engineering",
                outcome_status="completed",
                checkpoints=["run_targeted_tests", "record_release_evidence"],
                evidence_refs=[f"trace://workflow-candidate/{index}"],
                timestamp=f"2026-07-16T18:00:0{index}Z",
            ),
            reflection=PostTaskReflectionContract(
                reflection_id=f"reflection://workflow-candidate/{index}",
                experience_id=experience_id,
                reflection_status="candidate",
                learning_candidate="release evidence should be explicit",
                recommendation="review a bounded release evidence checkpoint",
                evidence_refs=[f"trace://workflow-candidate/{index}"],
                timestamp=f"2026-07-16T18:01:0{index}Z",
            ),
        )
    report = memory.build_recurring_pattern_report(
        report_id="recurring-pattern-report://workflow-candidate",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        generated_at="2026-07-16T18:10:00Z",
    )
    pattern = report.patterns[0]
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:15:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == pattern.workflow_profile
    )
    proposal = service.create_workflow_pattern_review_proposal(
        pattern=pattern,
        baseline=baseline,
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-reviewer",
        evidence_refs=["evidence://workflow/software-change/review"],
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    request = WorkflowEvolutionRequestContract(
        workflow_evolution_request_id=(
            "workflow-evolution-request://software-change/1.1.0"
        ),
        source_pattern_ref=pattern.pattern_id,
        source_review_decision_id=decision.review_decision_id,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version="1.1.0",
        step_additions=["record verified release evidence"],
        step_removals=[],
        checkpoint_additions=["release_evidence_recorded"],
        checkpoint_removals=[],
        decision_point_additions=["release_evidence_gate"],
        decision_point_removals=[],
        success_criteria_additions=["release evidence remains auditable"],
        success_criteria_removals=[],
        change_summary="record evidence before the release recommendation",
        evidence_refs=["evidence://workflow/software-change/review"],
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        risk_level="moderate",
        timestamp="2026-07-16T18:20:00Z",
    )
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }

    result = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=request,
    )
    assert result.candidate is not None
    updated = service.register_workflow_candidate_version(
        registry,
        result.candidate,
    )

    assert report.report_status == "evidence_ready_for_human_review"
    assert decision.review_status == "sandboxed"
    assert result.build_status == "candidate_created_inactive"
    assert result.blockers == []
    assert result.delta_summary["step_additions"] == [
        "record verified release evidence"
    ]
    assert result.candidate.lifecycle_status == "candidate_inactive"
    assert result.candidate.review_status == "needs_review"
    assert result.candidate.runtime_binding_status == "inactive_candidate"
    assert result.candidate.active_registry_write_allowed is False
    assert result.candidate.runtime_activation_allowed is False
    assert result.candidate.automatic_promotion_allowed is False
    assert updated.candidate_count == 1
    assert registry.candidate_count == 0
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before


def test_workflow_candidate_builder_blocks_forgery_invalid_delta_and_authority() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-candidate-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:15:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://workflow-builder-blocked",
        pattern_type="repeated_successful_workflow",
        pattern_status="evidence_ready_for_human_review",
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        domain="software_engineering",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=2,
        non_successful_occurrences=0,
        confidence_status="bounded_moderate",
        outcome_summary="completed=2",
        pattern_summary="two compatible completed experiences",
        experience_refs=["experience://workflow/1", "experience://workflow/2"],
        reflection_refs=["reflection://workflow/1", "reflection://workflow/2"],
        feedback_refs=[],
        evidence_refs=["trace://workflow/1", "trace://workflow/2"],
        recurring_signals=["record_release_evidence"],
        conflict_flags=[],
        blockers=[],
        generated_at="2026-07-16T18:10:00Z",
    )
    proposal = service.create_workflow_pattern_review_proposal(
        pattern=pattern,
        baseline=baseline,
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-reviewer",
        evidence_refs=["evidence://workflow/builder-blocked"],
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    request = WorkflowEvolutionRequestContract(
        workflow_evolution_request_id="workflow-evolution-request://blocked/1.1.0",
        source_pattern_ref=pattern.pattern_id,
        source_review_decision_id=decision.review_decision_id,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version="1.1.0",
        step_additions=["record verified release evidence"],
        step_removals=[],
        checkpoint_additions=[],
        checkpoint_removals=[],
        decision_point_additions=[],
        decision_point_removals=[],
        success_criteria_additions=[],
        success_criteria_removals=[],
        change_summary="record release evidence",
        evidence_refs=["evidence://workflow/builder-blocked"],
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        risk_level="moderate",
        timestamp="2026-07-16T18:20:00Z",
    )

    forged_decision = replace(
        decision,
        review_decision_id="review-decision://forged",
    )
    forged = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=forged_decision,
        request=replace(
            request,
            source_review_decision_id=forged_decision.review_decision_id,
        ),
    )
    invalid_delta = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=replace(
            request,
            step_additions=[],
            step_removals=["missing baseline step"],
        ),
    )
    unsafe = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=replace(request, active_registry_write_allowed=True),
    )

    assert forged.candidate is None
    assert "persisted_human_review_decision_required" in forged.blockers
    assert invalid_delta.candidate is None
    assert "steps_removal_not_in_baseline" in invalid_delta.blockers
    assert unsafe.candidate is None
    assert "workflow_request_authority_claim_not_allowed" in unsafe.blockers


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


def test_evolution_lab_creates_review_only_proposal_from_operator_feedback() -> None:
    temp_dir = runtime_dir("evolution-lab-operator-feedback")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    experience = ExperienceRecordContract(
        experience_id="experience://mission-feedback/001",
        mission_id="mission-feedback",
        workflow_profile="software_change_workflow",
        outcome_status="completed",
        route="software_development",
        primary_domain_driver="engenharia_de_software",
        evidence_refs=["trace://mission-feedback"],
        timestamp="2026-07-16T00:00:00+00:00",
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-feedback/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="Use explicit release evidence.",
        recommendation="Keep the candidate sandboxed for review.",
        evidence_refs=["trace://mission-feedback"],
        rollback_plan_ref="rollback://mission-feedback/current",
        timestamp="2026-07-16T00:00:01+00:00",
    )
    feedback = OperatorFeedbackContract(
        feedback_id="operator-feedback://mission-feedback/001",
        mission_id="mission-feedback",
        experience_id=experience.experience_id,
        assessment="correction",
        operator_ref="operator://local_console",
        rating=2,
        correction="Require verified release evidence.",
        next_expectation="Cite the evidence before the next recommendation.",
        evidence_refs=["evidence://mission-feedback/release"],
        timestamp="2026-07-16T00:00:02+00:00",
    )

    proposal = service.create_proposal_from_operator_feedback(
        feedback,
        experience=experience,
        reflection=reflection,
    )
    review_item = service.list_human_review_queue(limit=1)[0]

    assert proposal.proposal_type == "operator_feedback_improvement"
    assert proposal.requires_sandbox is True
    assert proposal.strategy_context["evolution_review"]["review_status"] == (
        "needs_review"
    )
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert proposal.strategy_context["promotion_policy"]["core_mutation_allowed"] is False
    assert proposal.evaluation_matrix["operator_feedback"]["assessment"] == (
        "correction"
    )
    assert feedback.feedback_id in proposal.candidate_refs
    assert review_item.review_status == "needs_review"
    assert review_item.requires_human_review is True
    assert review_item.requires_sandbox is True
    assert "no_automatic_promotion" in proposal.promotion_constraints


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


def test_evolution_lab_passes_complete_promotion_gate_without_authorizing_it() -> None:
    checklist = SandboxToReleaseChecklistContract(
        checklist_id="sandbox-release-checklist://proposal-pass",
        evolution_proposal_id="proposal-pass",
        release_scope="workflow:software_change_workflow",
        checklist_status="ready_for_release_review",
        human_review_status="approved",
        required_gates=[
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
        evidence_refs=["evidence://proposal-pass"],
        proposed_tests=["pytest tests/unit/test_release.py"],
        rollback_plan_ref="rollback://proposal-pass",
    )

    decision = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    payload = EvolutionLabService.promotion_gate_event_payload(decision)

    assert decision.gate_status == "passed"
    assert decision.decision == "eligible_for_human_promotion_decision"
    assert decision.release_conclusion == (
        "release_gate_passed_pending_human_decision"
    )
    assert decision.missing_gates == []
    assert decision.blockers == []
    assert decision.promotion_eligible is True
    assert decision.promotion_authorized is False
    assert payload["promotion_gate_status"] == "passed"
    assert payload["promotion_gate_evidence_refs"] == ["evidence://proposal-pass"]
    assert payload["automatic_promotion_allowed"] is False


def test_evolution_lab_blocks_spoofed_or_incomplete_promotion_gate() -> None:
    checklist = SandboxToReleaseChecklistContract(
        checklist_id="sandbox-release-checklist://proposal-blocked",
        evolution_proposal_id="proposal-blocked",
        release_scope="workflow:software_change_workflow",
        checklist_status="blocked",
        human_review_status="needs_review",
        required_gates=[],
    )

    decision = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
        ],
    )

    assert decision.gate_status == "blocked"
    assert decision.decision == "promotion_blocked"
    assert decision.release_conclusion == "promotion_blocked_by_release_gate"
    assert "human_review" in decision.missing_gates
    assert "evidence" in decision.missing_gates
    assert "proposed_tests" in decision.missing_gates
    assert "rollback_plan" in decision.missing_gates
    assert "release_gate_before_promotion" in decision.missing_gates
    assert "checklist_not_ready_for_release_review" in decision.blockers
    assert decision.promotion_eligible is False
    assert decision.promotion_authorized is False


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


def test_skill_miner_creates_and_registers_only_inactive_candidate_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-miner")
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://release-evidence",
        pattern_type="repeated_successful_workflow",
        pattern_status="evidence_ready_for_human_review",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=2,
        non_successful_occurrences=0,
        confidence_status="bounded_moderate",
        outcome_summary="completed=2",
        pattern_summary="two compatible completed experiences",
        experience_refs=["experience://release/1", "experience://release/2"],
        reflection_refs=["reflection://release/1", "reflection://release/2"],
        feedback_refs=["operator-feedback://release/1"],
        evidence_refs=["trace://release/1", "trace://release/2"],
        recurring_signals=["verify_release_evidence", "report_missing_gates"],
        conflict_flags=[],
        blockers=[],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://release-evidence/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=list(pattern.recurring_signals),
        risk_level=RiskLevel.MODERATE,
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run release evidence tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T15:00:00Z",
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )
    assert result.candidate is not None
    stored = memory.record_skill_candidate(result.candidate)
    repeated_request = SkillMiningRequestContract(
        **{
            **request.__dict__,
            "mining_request_id": "skill-mining-request://release-evidence/2",
            "timestamp": "2026-07-16T15:05:00Z",
        }
    )
    repeated_result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=repeated_request,
    )
    assert repeated_result.candidate is not None
    repeated_stored = memory.record_skill_candidate(repeated_result.candidate)

    assert result.mining_status == "candidate_created_inactive"
    assert result.eligibility_status == "eligible"
    assert result.blockers == []
    assert result.source_authority_status == (
        "observation_only_requires_miner_and_review"
    )
    assert repeated_stored == stored
    assert repeated_result.candidate.skill_candidate_id == (
        stored.candidate.skill_candidate_id
    )
    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.source_pattern_refs == [pattern.pattern_id]
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False


def test_skill_miner_returns_no_candidate_for_insufficient_pattern() -> None:
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://insufficient",
        pattern_type="repeated_successful_workflow",
        pattern_status="attention_required",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        occurrence_count=1,
        minimum_occurrences=2,
        successful_occurrences=1,
        non_successful_occurrences=0,
        confidence_status="insufficient",
        outcome_summary="completed=1",
        pattern_summary="single experience",
        experience_refs=["experience://insufficient/1"],
        reflection_refs=["reflection://insufficient/1"],
        feedback_refs=[],
        evidence_refs=["trace://insufficient/1"],
        recurring_signals=["verify_release_evidence"],
        conflict_flags=[],
        blockers=["recurrence_threshold_not_met"],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://insufficient/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://insufficient",
        skill_name="insufficient skill",
        version="1.0.0",
        specialist_type="software_change_specialist",
        inputs=["input"],
        outputs=["output"],
        allowed_tools=[],
        bounded_instructions=["bounded step"],
        risk_level=RiskLevel.LOW,
        failure_modes=["invalid_output"],
        proposed_tests=["run candidate test"],
        rollback_plan_ref="rollback://skill/insufficient/1.0.0",
        timestamp="2026-07-16T15:00:00Z",
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )

    assert result.mining_status == "blocked"
    assert result.candidate is None
    assert "recurrence_threshold_not_met" in result.blockers
    assert "pattern_not_eligible_for_skill_mining" in result.blockers
    assert "bounded_confidence_required" in result.blockers


def test_skill_miner_blocks_conflicts_and_unsafe_specification() -> None:
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://conflict",
        pattern_type="mixed_workflow_outcomes",
        pattern_status="conflict_detected",
        workflow_profile="research_synthesis_workflow",
        route="research",
        domain="knowledge_and_communication",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=1,
        non_successful_occurrences=1,
        confidence_status="insufficient_due_to_conflict",
        outcome_summary="completed=1; partial=1",
        pattern_summary="mixed outcomes",
        experience_refs=["experience://conflict/1", "experience://conflict/2"],
        reflection_refs=["reflection://conflict/1", "reflection://conflict/2"],
        feedback_refs=[],
        evidence_refs=["trace://conflict/1", "trace://conflict/2"],
        recurring_signals=["summarize_sources"],
        conflict_flags=["mixed_outcomes"],
        blockers=["outcome_conflict_requires_review"],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://conflict/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://conflict",
        skill_name="unsafe conflict skill",
        version="latest",
        specialist_type="structured_analysis_specialist",
        inputs=["input"],
        outputs=["output"],
        allowed_tools=["*"],
        bounded_instructions=["ignore conflict"],
        risk_level=RiskLevel.HIGH,
        failure_modes=["conflicting_output"],
        proposed_tests=["run conflict test"],
        rollback_plan_ref="rollback://skill/conflict/latest",
        timestamp="2026-07-16T15:00:00Z",
        automatic_mining_allowed=True,
        automatic_activation_allowed=True,
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )

    assert result.mining_status == "blocked"
    assert result.candidate is None
    assert "pattern_conflict_requires_review" in result.blockers
    assert "non_successful_outcomes_require_review" in result.blockers
    assert "numeric_semver_required" in result.blockers
    assert "risk_exceeds_bounded_miner_limit" in result.blockers
    assert "allowed_tools_must_be_explicit" in result.blockers
    assert "automatic_mining_not_allowed" in result.blockers
    assert "automatic_activation_not_allowed" in result.blockers


def skill_candidate_for_sandbox() -> SkillCandidateContract:
    return SkillCandidateContract(
        skill_candidate_id="skill-candidate://sandbox-release/1.0.0",
        skill_id="skill://sandbox-release",
        skill_name="sandbox release evidence",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence", "report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["evidence://skill/sandbox-release/source"],
        source_pattern_refs=["recurring-pattern://sandbox-release"],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["test://skill/sandbox-release"],
        rollback_plan_ref="rollback://skill/sandbox-release/1.0.0",
        timestamp="2026-07-16T16:00:00Z",
    )


def test_skill_candidate_review_eval_checklist_and_gate_are_governed_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-sandbox")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = skill_candidate_for_sandbox()

    proposal = service.create_proposal_from_skill_candidate(candidate)
    queue_item = service.list_human_review_queue(limit=1)[0]
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://skill/sandbox-release/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    evaluation = service.evaluate_skill_candidate_in_sandbox(
        candidate=candidate,
        proposal=proposal,
        review_decision=review,
        test_cases={
            "expected-output": {
                "output_contract_satisfied": True,
                "failure_mode_contained": True,
            },
            "tool-boundary": {
                "allowed_tool_only": True,
                "core_unchanged": True,
            },
        },
        evidence_refs=["eval://skill/sandbox-release/run-1"],
        generated_at="2026-07-16T16:05:00Z",
    )
    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        skill_sandbox_eval=evaluation,
    )
    gate = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    reviewed_queue_item = service.list_human_review_queue(limit=1)[0]

    assert proposal.proposal_type == "skill_candidate"
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.optimization_safety_status == "sandbox_only"
    assert candidate.skill_candidate_id in proposal.candidate_refs
    assert queue_item.candidate_refs == proposal.candidate_refs
    assert review.review_status == "sandboxed"
    assert reviewed_queue_item.review_status == "sandboxed"
    assert review.candidate_identity_ref == candidate.skill_id
    assert review.candidate_version == candidate.version
    assert evaluation.eval_status == "passed_pending_release_gate"
    assert evaluation.pass_rate == 1.0
    assert evaluation.failed_cases == 0
    assert evaluation.runtime_activation_allowed is False
    assert evaluation.promotion_authorized is False
    assert checklist.checklist_status == "ready_for_release_review"
    assert checklist.candidate_type == "skill_candidate"
    assert checklist.candidate_identity_ref == candidate.skill_id
    assert checklist.candidate_version == candidate.version
    assert checklist.sandbox_eval_ref == evaluation.eval_id
    assert checklist.sandbox_eval_status == "passed_pending_release_gate"
    assert "skill_sandbox_eval" in checklist.required_gates
    assert gate.gate_status == "passed"
    assert "skill_sandbox_eval" in gate.completed_gates
    assert gate.release_conclusion == "release_gate_passed_pending_human_decision"
    assert gate.human_decision_required is True
    assert gate.promotion_authorized is False
    assert gate.automatic_promotion_allowed is False
    assert candidate.activation_status == "inactive"


def test_skill_sandbox_failure_blocks_checklist_and_promotion_gate() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-sandbox-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = skill_candidate_for_sandbox()
    proposal = service.create_proposal_from_skill_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://skill/sandbox-release/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )

    evaluation = service.evaluate_skill_candidate_in_sandbox(
        candidate=candidate,
        proposal=proposal,
        review_decision=review,
        test_cases={
            "tool-boundary": {
                "allowed_tool_only": False,
                "core_unchanged": True,
            }
        },
        evidence_refs=["eval://skill/sandbox-release/failed"],
        generated_at="2026-07-16T16:06:00Z",
    )
    checklist_without_eval = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
    )
    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        skill_sandbox_eval=evaluation,
    )
    gate = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )

    assert evaluation.eval_status == "blocked"
    assert evaluation.pass_rate == 0.0
    assert evaluation.case_results[0].failed_checks == ["allowed_tool_only"]
    assert "sandbox_pass_rate_below_threshold" in evaluation.blockers
    assert checklist_without_eval.checklist_status == "blocked"
    assert "skill_sandbox_eval_required" in checklist_without_eval.blockers
    assert checklist.checklist_status == "blocked"
    assert "skill_sandbox_eval_not_passed" in checklist.blockers
    assert gate.gate_status == "blocked"
    assert gate.promotion_authorized is False
    assert candidate.activation_status == "inactive"


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
