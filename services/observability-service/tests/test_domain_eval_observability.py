from dataclasses import replace

from observability_service.service import ObservabilityService

from shared.contracts import (
    DomainEvalCaseResultContract,
)
from tests.unit.test_workflow_variant_eval import (
    _pack,
    _registry_with_candidate,
    _with_second_case_version,
)
from tools.workflow_variant_eval import _evaluate_case


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
    baseline, candidate, _registry = _registry_with_candidate()
    case_pack = _pack(baseline, candidate)
    result = _evaluate_case(
        case=case_pack.cases[0],
        case_pack=case_pack,
        baseline=baseline,
        candidate=candidate,
    )

    run = ObservabilityService.build_workflow_variant_eval_run(
        run_id="workflow-eval-1",
        case_pack=case_pack,
        case_results=[result],
        minimum_pass_rate=1.0,
        evidence_refs=result.evidence_refs,
        generated_at="2026-07-16T20:00:00Z",
    )

    assert run.status == "passed"
    assert run.comparison_conclusion == "candidate_improved_without_regression"
    assert run.promotion_readiness == "manual_gate_only"
    assert run.promotion_authorized is False


def test_observability_recomputes_forged_result_and_authority_fail_closed() -> None:
    baseline, candidate, _registry = _registry_with_candidate()
    case_pack = _pack(baseline, candidate)
    valid = _evaluate_case(
        case=case_pack.cases[0],
        case_pack=case_pack,
        baseline=baseline,
        candidate=candidate,
    )
    forged = replace(
        valid,
        passed=True,
        baseline_metrics={key: 1.0 for key in valid.baseline_metrics},
        candidate_metrics={key: 0.0 for key in valid.candidate_metrics},
        metric_deltas={key: 1.0 for key in valid.metric_deltas},
        improvement_signals=["forged_improvement"],
        regression_flags=[],
        failures=[],
        offline_only=False,
        sandbox_only=False,
        execution_allowed=True,
        tool_dispatch_allowed=True,
        runtime_activation_allowed=True,
        release_authorized=True,
        promotion_authorized=True,
        automatic_promotion_allowed=True,
        core_mutation_allowed=True,
    )

    run = ObservabilityService.build_workflow_variant_eval_run(
        run_id="workflow-eval-forged",
        case_pack=case_pack,
        case_results=[forged],
        minimum_pass_rate=1.0,
        evidence_refs=forged.evidence_refs,
        generated_at="2026-07-16T20:00:00Z",
    )

    assert run.status == "failed"
    assert run.comparison_conclusion == "insufficient_or_invalid_evidence"
    assert run.case_results[0].baseline_metrics == valid.baseline_metrics
    assert run.case_results[0].candidate_metrics == valid.candidate_metrics
    assert run.execution_allowed is False
    assert run.tool_dispatch_allowed is False
    assert run.runtime_activation_allowed is False
    assert run.release_authorized is False
    assert run.promotion_authorized is False
    assert run.automatic_promotion_allowed is False
    assert run.core_mutation_allowed is False
    assert "case:software_release_evidence:source_authority_safe" in run.blockers


def test_observability_keys_versioned_cases_by_complete_identity() -> None:
    baseline, candidate, _registry = _registry_with_candidate()
    versioned_pack = _with_second_case_version(_pack(baseline, candidate))
    results = [
        _evaluate_case(
            case=case,
            case_pack=versioned_pack,
            baseline=baseline,
            candidate=candidate,
        )
        for case in versioned_pack.cases
    ]

    run = ObservabilityService.build_workflow_variant_eval_run(
        run_id="workflow-eval-versioned-cases",
        case_pack=versioned_pack,
        case_results=results,
        minimum_pass_rate=1.0,
        evidence_refs=[
            reference for result in results for reference in result.evidence_refs
        ],
        generated_at="2026-07-16T20:00:00Z",
    )

    assert run.status == "passed"
    assert run.total_cases == 2
    assert [(result.case_id, result.case_version) for result in run.case_results] == [
        (case.case_id, case.case_version) for case in versioned_pack.cases
    ]
