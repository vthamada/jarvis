from tools.run_domain_eval import render_text


def test_domain_eval_text_report_exposes_readiness_and_case_signals() -> None:
    payload = {
        "run_id": "domain-eval-1",
        "eval_pack_id": "eval-pack://domain/analysis/1.0.0",
        "route_name": "analysis",
        "status": "passed",
        "readiness_status": "candidate_ready_for_human_review",
        "pass_rate": 1.0,
        "promotion_readiness": "manual_review_only",
        "case_results": [
            {
                "case_id": "analysis_seed",
                "passed": True,
                "observed_governance_decision": "allow_with_conditions",
                "observed_route": "analysis",
                "observed_workflow_profile": "structured_analysis_workflow",
                "observed_memory_causality_status": "not_applicable",
                "failures": [],
            }
        ],
    }

    rendered = render_text(payload)

    assert "readiness=candidate_ready_for_human_review" in rendered
    assert "promotion_readiness=manual_review_only" in rendered
    assert "case_id=analysis_seed passed=true" in rendered
