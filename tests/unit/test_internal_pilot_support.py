from pathlib import Path

from tools.internal_pilot_support import default_pilot_scenarios, run_pilot_scenarios, runtime_dir


def test_default_pilot_scenarios_cover_allowed_and_blocked_paths() -> None:
    scenarios = default_pilot_scenarios()

    assert any(item.expected_operation for item in scenarios)
    assert any(item.expected_decision == "block" for item in scenarios)
    assert any(item.mission_key for item in scenarios)
    assert any(item.expected_decision == "defer_for_validation" for item in scenarios)
    assert any("continuity_resume" in item.metadata for item in scenarios)


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
