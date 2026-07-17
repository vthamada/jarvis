from observability_service.service import ObservabilityService

from shared.contracts import (
    DomainEvalCaseResultContract,
    WorkflowVariantEvalCaseResultContract,
)


def _result(case_id: str, *, passed: bool) -> DomainEvalCaseResultContract:
    return DomainEvalCaseResultContract(
        eval_pack_id="eval-pack://domain/analysis/1.0.0",
        case_id=case_id,
        passed=passed,
        checks={"route": passed},
        failures=[] if passed else ["route_mismatch"],
        observed_governance_decision="allow_with_conditions",
        observed_route="analysis" if passed else "strategy",
        observed_canonical_domain_refs=[],
        observed_workflow_profile="structured_analysis_workflow",
        observed_specialist_types=["structured_analysis_specialist"],
        observed_memory_causality_status="causal_guidance",
        response_evidence=[],
        response_length=500,
        observed_events=[],
    )


def test_observability_builds_manual_review_only_domain_eval_run() -> None:
    run = ObservabilityService.build_domain_eval_run(
        run_id="domain-eval-1",
        eval_pack_id="eval-pack://domain/analysis/1.0.0",
        pack_version="1.0.0",
        route_name="analysis",
        case_results=[_result("case-1", passed=True)],
        minimum_pass_rate=1.0,
        evidence_refs=["evidence://domain-eval"],
        generated_at="2026-07-16T00:00:00Z",
    )

    assert run.status == "passed"
    assert run.readiness_status == "candidate_ready_for_human_review"
    assert run.promotion_readiness == "manual_review_only"
    assert run.promotion_authorized is False


def test_observability_exposes_case_failure_as_readiness_blocker() -> None:
    run = ObservabilityService.build_domain_eval_run(
        run_id="domain-eval-2",
        eval_pack_id="eval-pack://domain/analysis/1.0.0",
        pack_version="1.0.0",
        route_name="analysis",
        case_results=[_result("case-1", passed=False)],
        minimum_pass_rate=1.0,
        evidence_refs=["evidence://domain-eval"],
        generated_at="2026-07-16T00:00:00Z",
    )

    assert run.status == "failed"
    assert run.pass_rate == 0.0
    assert run.promotion_readiness == "blocked"
    assert "case:case-1:route_mismatch" in run.blockers


def test_observability_aggregates_workflow_variant_as_manual_gate_evidence() -> None:
    metrics = {
        "success_score": 0.8,
        "contract_adherence": 0.8,
        "rework_rate": 0.2,
        "checkpoint_coverage": 0.8,
        "memory_causality": 0.7,
    }
    candidate_metrics = {
        **metrics,
        "success_score": 0.9,
        "rework_rate": 0.1,
    }
    result = WorkflowVariantEvalCaseResultContract(
        case_id="workflow-case-1",
        scenario_ref="scenario://workflow/1",
        workflow_profile="software_change_workflow",
        route="software_development",
        baseline_version_ref="workflow-version://software_change_workflow/1.0.0",
        candidate_version_ref="workflow-version://software_change_workflow/1.1.0",
        passed=True,
        checks={"no_metric_regression": True},
        baseline_metrics=metrics,
        candidate_metrics=candidate_metrics,
        metric_deltas={
            key: round(candidate_metrics[key] - metrics[key], 4) for key in metrics
        },
        improvement_signals=["success_score_improved", "rework_rate_improved"],
        regression_flags=[],
        failures=[],
        evidence_refs=["eval://workflow/1"],
    )

    run = ObservabilityService.build_workflow_variant_eval_run(
        run_id="workflow-eval-1",
        workflow_profile=result.workflow_profile,
        route=result.route,
        baseline_version_ref=result.baseline_version_ref,
        candidate_version_ref=result.candidate_version_ref,
        case_results=[result],
        minimum_pass_rate=1.0,
        evidence_refs=result.evidence_refs,
        generated_at="2026-07-16T20:00:00Z",
    )

    assert run.status == "passed"
    assert run.comparison_conclusion == "candidate_improved_without_regression"
    assert run.promotion_readiness == "manual_gate_only"
    assert run.promotion_authorized is False
