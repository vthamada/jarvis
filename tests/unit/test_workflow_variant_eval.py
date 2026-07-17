from dataclasses import replace

from evolution_lab.service import EvolutionLabService

from shared.contract_validation import validate_contract_instance
from shared.contracts import WorkflowVariantEvalCaseContract
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    build_active_workflow_version_registry,
    register_workflow_candidate_version,
    route_metadata_payload,
    workflow_definition_hash,
)
from shared.schemas import (
    WORKFLOW_ROLLBACK_PLAN_SCHEMA,
    WORKFLOW_VARIANT_EVAL_CASE_RESULT_SCHEMA,
    WORKFLOW_VARIANT_EVAL_CASE_SCHEMA,
    WORKFLOW_VARIANT_EVAL_RUN_SCHEMA,
)
from tools.workflow_release_gate import evaluate_workflow_release_gate
from tools.workflow_variant_eval import run_workflow_variant_eval


def _registry_with_candidate():  # type: ignore[no-untyped-def]
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T20:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    steps = [*baseline.workflow_steps, "record verified release evidence"]
    checkpoints = [*baseline.workflow_checkpoints, "release_evidence_recorded"]
    decision_points = [*baseline.workflow_decision_points, "release_evidence_gate"]
    success_criteria = [
        *baseline.success_criteria,
        "release evidence remains auditable",
    ]
    candidate = replace(
        baseline,
        workflow_version_id=(
            "workflow-version://software_change_workflow/1.1.0"
        ),
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=steps,
            workflow_checkpoints=checkpoints,
            workflow_decision_points=decision_points,
            success_criteria=success_criteria,
        ),
        workflow_steps=steps,
        workflow_checkpoints=checkpoints,
        workflow_decision_points=decision_points,
        success_criteria=success_criteria,
        evidence_refs=[
            *baseline.evidence_refs,
            "recurring-pattern://software-release",
            "review-decision://software-release/001",
            "evidence://workflow/software-release",
        ],
        proposed_tests=["test://workflow/software-release-variant"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="record release evidence before recommendation",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )
    return baseline, candidate, register_workflow_candidate_version(
        registry,
        candidate,
    )


def _case(candidate, *, candidate_success: float = 0.9):  # type: ignore[no-untyped-def]
    return WorkflowVariantEvalCaseContract(
        case_id="software_release_evidence",
        scenario_ref="scenario://workflow/software-release/equivalent-1",
        workflow_profile=candidate.workflow_profile,
        route=candidate.route,
        baseline_version_ref=candidate.baseline_version_ref,
        candidate_version_ref=candidate.workflow_version_id,
        required_candidate_steps=["record verified release evidence"],
        required_candidate_checkpoints=["release_evidence_recorded"],
        required_candidate_decision_points=["release_evidence_gate"],
        required_candidate_success_criteria=[
            "release evidence remains auditable"
        ],
        baseline_metrics={
            "success_score": 0.8,
            "contract_adherence": 0.8,
            "rework_rate": 0.2,
            "checkpoint_coverage": 0.75,
            "memory_causality": 0.7,
        },
        candidate_metrics={
            "success_score": candidate_success,
            "contract_adherence": 0.9,
            "rework_rate": 0.1,
            "checkpoint_coverage": 0.9,
            "memory_causality": 0.8,
        },
        evidence_refs=[
            "eval://workflow/software-release/baseline",
            "eval://workflow/software-release/candidate",
        ],
    )


def test_workflow_variant_eval_compares_equivalent_case_without_activation() -> None:
    baseline, candidate, registry = _registry_with_candidate()
    case = _case(candidate)
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }

    result = run_workflow_variant_eval(
        registry=registry,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        cases=[case],
        run_id="workflow-variant-eval://software-release/001",
        generated_at="2026-07-16T20:10:00Z",
    )

    assert result.status == "passed"
    assert result.readiness_status == "candidate_ready_for_human_gate_review"
    assert result.promotion_readiness == "manual_gate_only"
    assert result.comparison_conclusion == "candidate_improved_without_regression"
    assert result.pass_rate == 1.0
    assert result.aggregate_metric_deltas["success_score"] == 0.1
    assert result.aggregate_metric_deltas["rework_rate"] == -0.1
    assert result.regression_flags == []
    assert result.promotion_authorized is False
    assert result.automatic_promotion_allowed is False
    assert result.core_mutation_allowed is False
    assert registry.versions[-1].runtime_activation_allowed is False
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before
    assert validate_contract_instance(
        case,
        schema=WORKFLOW_VARIANT_EVAL_CASE_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        result.case_results[0],
        schema=WORKFLOW_VARIANT_EVAL_CASE_RESULT_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        result,
        schema=WORKFLOW_VARIANT_EVAL_RUN_SCHEMA,
    ).status == "coherent"


def test_workflow_variant_eval_blocks_regression_and_registry_authority() -> None:
    baseline, candidate, registry = _registry_with_candidate()
    regressed = run_workflow_variant_eval(
        registry=registry,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        cases=[_case(candidate, candidate_success=0.7)],
        run_id="workflow-variant-eval://software-release/regression",
        generated_at="2026-07-16T20:10:00Z",
    )
    unsafe_registry = replace(registry, runtime_activation_allowed=True)
    unsafe = run_workflow_variant_eval(
        registry=unsafe_registry,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        cases=[_case(candidate)],
        run_id="workflow-variant-eval://software-release/unsafe",
        generated_at="2026-07-16T20:11:00Z",
    )

    assert regressed.status == "failed"
    assert regressed.comparison_conclusion == "candidate_regression_detected"
    assert (
        "case:software_release_evidence:success_score_regressed"
        in regressed.regression_flags
    )
    assert regressed.promotion_readiness == "blocked"
    assert unsafe.status == "failed"
    assert "workflow_eval_registry_authority_claim_not_allowed" in unsafe.blockers
    assert unsafe.promotion_authorized is False


def test_workflow_release_gate_requires_new_review_eval_and_manual_rollback(
    tmp_path,
) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    workflow_eval = run_workflow_variant_eval(
        registry=registry,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        cases=[_case(candidate)],
        run_id="workflow-variant-eval://software-release/gate",
        generated_at="2026-07-16T20:20:00Z",
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    proposal = service.create_proposal_from_workflow_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-release-reviewer",
        evidence_refs=["evidence://workflow/software-release/release-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    rollback_plan = service.build_workflow_rollback_plan(
        baseline=baseline,
        candidate=candidate,
        trigger_conditions=[
            "success score regresses below the approved baseline",
            "contract or checkpoint regression is observed",
        ],
        verification_tests=["test://workflow/software-release-rollback"],
        evidence_refs=["evidence://workflow/software-release/rollback"],
        operator_ref="operator://workflow-release-reviewer",
        generated_at="2026-07-16T20:21:00Z",
    )
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }

    release = evaluate_workflow_release_gate(
        service=service,
        proposal=proposal,
        review_decision=review,
        candidate=candidate,
        workflow_eval=workflow_eval,
        rollback_plan=rollback_plan,
        completed_external_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    forged_release = evaluate_workflow_release_gate(
        service=service,
        proposal=proposal,
        review_decision=replace(
            review,
            review_decision_id="review-decision://workflow-release/forged",
        ),
        candidate=candidate,
        workflow_eval=workflow_eval,
        rollback_plan=rollback_plan,
        completed_external_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )

    assert proposal.proposal_type == "workflow_candidate"
    assert review.candidate_identity_ref == candidate.workflow_profile
    assert review.candidate_version == candidate.version
    assert rollback_plan.plan_status == "verified_for_manual_execution"
    assert rollback_plan.execution_mode == "manual_only"
    assert rollback_plan.execution_authorized is False
    assert release.checklist.checklist_status == "ready_for_release_review"
    assert release.checklist.candidate_type == "workflow_candidate"
    assert release.checklist.baseline_version_ref == baseline.workflow_version_id
    assert "workflow_variant_eval" in release.checklist.required_gates
    assert "workflow_rollback_plan" in release.checklist.required_gates
    assert release.gate_decision.gate_status == "passed"
    assert "workflow_variant_eval" in release.gate_decision.completed_gates
    assert "workflow_rollback_plan" in release.gate_decision.completed_gates
    assert release.gate_decision.release_conclusion == (
        "release_gate_passed_pending_human_decision"
    )
    assert release.gate_decision.promotion_eligible is True
    assert release.gate_decision.promotion_authorized is False
    assert forged_release.gate_decision.gate_status == "blocked"
    assert (
        "persisted_candidate_review_last_review_decision_id_mismatch"
        in forged_release.checklist.blockers
    )
    assert candidate.runtime_activation_allowed is False
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before
    assert validate_contract_instance(
        rollback_plan,
        schema=WORKFLOW_ROLLBACK_PLAN_SCHEMA,
    ).status == "coherent"


def test_workflow_release_gate_blocks_failed_eval_and_missing_rollback(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    failed_eval = run_workflow_variant_eval(
        registry=registry,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        cases=[_case(candidate, candidate_success=0.7)],
        run_id="workflow-variant-eval://software-release/gate-failed",
        generated_at="2026-07-16T20:20:00Z",
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    proposal = service.create_proposal_from_workflow_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-release-reviewer",
        evidence_refs=["evidence://workflow/software-release/release-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )

    release = evaluate_workflow_release_gate(
        service=service,
        proposal=proposal,
        review_decision=review,
        candidate=candidate,
        workflow_eval=failed_eval,
        rollback_plan=None,
        completed_external_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )

    assert release.checklist.checklist_status == "blocked"
    assert "workflow_variant_eval_not_passed" in release.checklist.blockers
    assert "workflow_rollback_plan_required" in release.checklist.blockers
    assert "workflow_variant_eval" in release.gate_decision.missing_gates
    assert "workflow_rollback_plan" in release.gate_decision.missing_gates
    assert release.gate_decision.gate_status == "blocked"
    assert release.gate_decision.promotion_eligible is False
    assert release.gate_decision.promotion_authorized is False
