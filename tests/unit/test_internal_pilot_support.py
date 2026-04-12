from pathlib import Path

from tools.internal_pilot_support import default_pilot_scenarios, run_pilot_scenarios, runtime_dir


def test_default_pilot_scenarios_cover_allowed_and_blocked_paths() -> None:
    scenarios = default_pilot_scenarios()

    assert any(item.expected_operation for item in scenarios)
    assert any(item.expected_decision == "block" for item in scenarios)
    assert any(item.mission_key for item in scenarios)
    assert any(item.expected_decision == "defer_for_validation" for item in scenarios)
    assert any("continuity_resume" in item.metadata for item in scenarios)
    assert any(item.scenario_id == "guided_memory_followup" for item in scenarios)
    assert any(item.scenario_id == "recomposition_impasse" for item in scenarios)
    assert any(item.scenario_id == "analysis_guided_review" for item in scenarios)
    assert any(item.scenario_id == "decision_risk_review" for item in scenarios)
    assert any(item.scenario_id == "governance_boundary_review" for item in scenarios)
    assert any(item.expected_route == "software_development" for item in scenarios)
    assert any("memory_causality" in item.coverage_tags for item in scenarios)
    assert any("cognitive_recomposition" in item.coverage_tags for item in scenarios)
    assert any("mind_domain_specialist" in item.coverage_tags for item in scenarios)
    assert any("dominant_tension" in item.coverage_tags for item in scenarios)
    assert any("specialist_subflow" in item.coverage_tags for item in scenarios)
    assert any("mission_runtime_state" in item.coverage_tags for item in scenarios)


def test_run_pilot_scenarios_returns_structured_results() -> None:
    temp_dir = runtime_dir("pilot-support")

    results = run_pilot_scenarios(
        profile="development",
        workdir=Path(temp_dir),
        scenarios=default_pilot_scenarios()[:1],
    )

    assert len(results) == 1
    assert results[0].scenario_id == "controlled_plan"
    assert results[0].governance_decision == "allow_with_conditions"
    assert results[0].decision_matches_expectation is True
    assert results[0].operation_status == "completed"
    assert results[0].operation_matches_expectation is True
    assert results[0].expected_route == "operational_readiness"
    assert results[0].route_matches_expectation is True
    assert results[0].expected_workflow_profile == "operational_readiness_workflow"
    assert results[0].workflow_profile_matches_expectation is True
    assert results[0].specialist_subflow_status == "healthy"
    assert results[0].mission_runtime_state_status == "healthy"
    assert results[0].capability_decision_status == "healthy"
    assert results[0].capability_effectiveness == "effective"
