from observability_service.service import ObservabilityService

from shared.contracts import DomainEvalCaseResultContract


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
