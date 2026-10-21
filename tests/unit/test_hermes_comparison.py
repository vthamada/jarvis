"""Independent deterministic checks, never a judge of general agent quality."""

import json
from dataclasses import replace

import pytest

from evals.operator_tasks.hermes_comparison import (
    FOLLOWUP_QUERY,
    PREFERENCE,
    PUBLIC_CASE_DIGEST,
    REVISED_REPORTS,
    SEED_QUERY,
    SEED_REPORTS,
    CanonicalReadback,
    ComparisonConfig,
    Trial,
    TurnExecution,
    compare_conversations,
    grade_forbidden_turn,
    grade_turn,
    run_conversation_arm,
)
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER


def _execution(trial, *, analysis=None):
    count, latency = (12, 180) if trial.phase == "seed" else (13, 170)
    label = "not-available" if trial.phase == "control" else PREFERENCE
    if analysis is None:
        analysis = f"Response label: {label}. Reviewed items: {count}; p95: {latency}ms."
    text = "Canonical native response.\n" + GENERATIVE_ANALYSIS_MARKER + "\n"
    text += "Analysis: " + json.dumps(analysis) + "\n"
    for _, report in trial.reports:
        text += "Observed quote: " + json.dumps(report) + "\n"
    return TurnExecution({
        "model_tool_loop_status": "completed", "model_tool_loop_error_code": None,
        "model_tool_loop_observation_count": 2, "canonical_turn_recorded": True,
        "operation_dispatched": False, "authority": "none", "content_included": True,
        "response_text": text, "response_character_count": len(text),
    }, 3)


def _readback(execution):
    text = execution.result["response_text"]
    return CanonicalReadback(text, text, 3, 2)


def _trial(tmp_path, phase="memory"):
    return Trial(phase, tmp_path / phase, FOLLOWUP_QUERY, REVISED_REPORTS, phase == "memory")


def test_public_memory_fixture_does_not_leak_the_preference_to_followup_or_sources():
    assert PREFERENCE in SEED_QUERY
    assert PREFERENCE not in FOLLOWUP_QUERY
    assert all(PREFERENCE not in text for _, text in SEED_REPORTS + REVISED_REPORTS)
    assert len(PUBLIC_CASE_DIGEST) == 64
    assert dict(SEED_REPORTS)["documentation"] != dict(REVISED_REPORTS)["documentation"]


@pytest.mark.parametrize("phase", ["seed", "memory", "control"])
def test_all_phases_check_actual_analysis_quotes_and_independent_readback(tmp_path, phase):
    trial = _trial(tmp_path, phase)
    if phase == "seed":
        trial = replace(trial, query=SEED_QUERY, reports=SEED_REPORTS)
    execution = _execution(trial)
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert grade["success"] is True
    assert grade["failed_checks"] == []
    assert grade["deterministic_checks_only"] is True
    assert grade["human_review_required"] is True
    assert PREFERENCE not in json.dumps(grade)


@pytest.mark.parametrize("analysis,expected_failure", [
    ("13 reviewed items and p95 170ms; label unknown.", "remembered_preference"),
    (f"Response label: {PREFERENCE}. Reviewed items: 12; p95: 180ms.", "fresh_numeric_facts"),
])
def test_history_transport_or_stale_facts_are_not_memory_acceptance(
    tmp_path, analysis, expected_failure,
):
    trial = _trial(tmp_path)
    execution = _execution(trial, analysis=analysis)
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert grade["success"] is False
    assert expected_failure in grade["failed_checks"]


def test_control_must_not_invent_or_receive_the_seed_preference(tmp_path):
    trial = _trial(tmp_path, "control")
    execution = _execution(trial, analysis=f"{PREFERENCE}; 13 reviewed items, 170ms.")
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert "control_without_preference" in grade["failed_checks"]


@pytest.mark.parametrize("analysis", [
    f"I cannot recall it, maybe {PREFERENCE}. 13 reviewed items; 170ms.",
    f'"Response label: {PREFERENCE}." 13 reviewed items; 170ms.',
    f"Response label: different-label. 13 reviewed items; 170ms; {PREFERENCE}.",
    f"13 reviewed items; 170ms. Response label: {PREFERENCE}.",
    f"Response label: {PREFERENCE}-wrong. 13 reviewed items; 170ms.",
])
def test_preference_must_be_the_anchored_requested_field_not_merely_a_token(tmp_path, analysis):
    trial = _trial(tmp_path)
    execution = _execution(trial, analysis=analysis)
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert grade["success"] is False
    assert "remembered_preference" in grade["failed_checks"]


def test_control_does_not_accept_not_available_only_as_a_later_quoted_guess(tmp_path):
    trial = _trial(tmp_path, "control")
    execution = _execution(trial, analysis='13 reviewed items, 170ms. Guess "not-available".')
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert grade["success"] is False
    assert "control_without_preference" in grade["failed_checks"]


@pytest.mark.parametrize("count,latency", [
    ("13.5", "170"), ("13,5", "170"), ("-13", "170"), ("−13", "170"),
    ("13", "170.75"), ("13", "-170"), ("13", "170e2"),
    ("170", "13"),
])
def test_fractional_negative_and_scientific_values_do_not_match_expected_integers(
    tmp_path, count, latency,
):
    trial = _trial(tmp_path)
    execution = _execution(
        trial, analysis=f"Response label: {PREFERENCE}. Reviewed items: {count}; p95: {latency}ms.",
    )
    grade = grade_turn(trial, execution, _readback(execution), max_inferences=4)
    assert grade["success"] is False
    assert "fresh_numeric_facts" in grade["failed_checks"]
    assert "fresh_report_quotes" not in grade["failed_checks"]


@pytest.mark.parametrize("latency", ["170ms", "170 ms", "170 milliseconds"])
def test_positive_integer_latency_can_have_direct_or_spaced_units(tmp_path, latency):
    trial = _trial(tmp_path)
    execution = _execution(
        trial, analysis=f"Response label: {PREFERENCE}. Reviewed items: 13; p95: {latency}.",
    )
    assert grade_turn(trial, execution, _readback(execution))["success"] is True


@pytest.mark.parametrize("field,value,expected_failure", [
    ("response_text", "different restart final", "canonical_restart_exact"),
    ("exported_response_text", "different export final", "canonical_export_exact"),
    ("model_requests", 2, "inference_event_count"),
    ("tool_observations", 1, "tool_event_count"),
    ("effect_count", 1, "no_external_effects"),
])
def test_host_readback_mismatches_are_not_hidden(tmp_path, field, value, expected_failure):
    trial = _trial(tmp_path)
    execution = _execution(trial)
    readback = replace(_readback(execution), **{field: value})
    grade = grade_turn(trial, execution, readback, max_inferences=4)
    assert grade["success"] is False
    assert expected_failure in grade["failed_checks"]


def test_runner_clones_same_seed_before_either_followup_and_never_retries(tmp_path):
    calls, clones, results = [], [], {}

    def execute(trial):
        if trial.phase != "seed":
            assert len(clones) == 2
        calls.append(trial)
        execution = _execution(trial)
        results[trial.phase] = execution
        return execution

    def readback(trial, result):
        assert result is results[trial.phase].result
        return _readback(results[trial.phase])

    config = ComparisonConfig("synthetic-scripted-model")
    run = run_conversation_arm(
        directory=tmp_path, name="baseline", configuration=config,
        execute_turn=execute, readback_turn=readback,
        clone_seed=lambda source, target: clones.append((source, target)),
    )
    assert [trial.phase for trial in calls] == ["seed", "memory", "control"]
    assert calls[0].include_canonical_history is False
    assert calls[1].include_canonical_history is True
    assert calls[2].include_canonical_history is False
    assert clones == [(tmp_path / "seed", tmp_path / "memory"),
                      (tmp_path / "seed", tmp_path / "control")]
    assert run["all_checks_passed"] is True
    assert run["inference_attempts"] == 9
    assert run["improvement_claim"] is run["runtime_capability_promoted"] is False
    assert run["real_model_verified"] is False
    encoded = json.dumps(run)
    assert PREFERENCE not in encoded and SEED_QUERY not in encoded
    paired = compare_conversations(run, {**run, "name": "adapted_candidate"})
    assert paired["comparison_status"] == "complete"
    assert paired["improvement_claim"] is False
    assert paired["human_review_required"] is True


def test_runner_stops_at_failed_first_turn_with_unknown_calls_on_exception(tmp_path):
    calls = []

    def execute(trial):
        calls.append(trial.phase)
        raise RuntimeError("PRIVATE_SENTINEL")

    run = run_conversation_arm(
        directory=tmp_path, name="baseline", configuration=ComparisonConfig("test-model"),
        execute_turn=execute, readback_turn=lambda *args: pytest.fail("no result"),
        clone_seed=lambda *args: pytest.fail("cannot clone failed seed"),
    )
    assert calls == ["seed"]
    assert run["stopped_after"] == "seed" and run["all_checks_passed"] is False
    assert run["inference_attempts"] is None
    assert "PRIVATE_SENTINEL" not in json.dumps(run)


def test_snapshot_failure_summary_remains_comparable_as_partial_not_forged_complete(tmp_path):
    def failed_snapshot(*args):
        raise RuntimeError("PRIVATE_SNAPSHOT_FAILURE")

    common = {
        "configuration": ComparisonConfig("test-model"), "execute_turn": _execution,
        "readback_turn": lambda trial, result: _readback(_execution(trial)),
    }
    failed = run_conversation_arm(directory=tmp_path / "failed", name="baseline",
                                  clone_seed=failed_snapshot, **common)
    valid = run_conversation_arm(directory=tmp_path / "valid", name="candidate",
                                 clone_seed=lambda *args: None, **common)
    assert failed["stopped_after"] == "snapshot" and failed["inference_attempts"] == 3
    assert failed["turns"][-1]["deterministic_checks_only"] is True
    assert failed["turns"][-1]["human_review_required"] is True
    comparison = compare_conversations(failed, valid)
    assert comparison["comparison_status"] == "partial"
    assert comparison["baseline_passed_phases"] == 1
    assert comparison["candidate_passed_phases"] == 3
    assert "PRIVATE_SNAPSHOT_FAILURE" not in json.dumps(failed)


def test_comparison_refuses_unequal_budgets(tmp_path):
    def execute(trial):
        return _execution(trial)

    run = run_conversation_arm(
        directory=tmp_path, name="baseline", configuration=ComparisonConfig("test-model"),
        execute_turn=execute, readback_turn=lambda trial, value: _readback(_execution(trial)),
        clone_seed=lambda *args: None,
    )
    candidate = {**run, "name": "candidate",
                 "configuration": {**run["configuration"], "timeout_seconds": 119.0}}
    with pytest.raises(ValueError, match="incomparable_configuration"):
        compare_conversations(run, candidate)


def test_empty_turns_and_absent_configuration_cannot_claim_a_complete_comparison():
    forged = {
        "schema_version": "jarvis-hermes-conversation-comparison-v1",
        "corpus_digest": PUBLIC_CASE_DIGEST, "name": "forged",
        "all_checks_passed": True, "turns": [],
    }
    with pytest.raises(ValueError, match="invalid_comparison_summary"):
        compare_conversations(forged, {**forged, "name": "other"})


@pytest.mark.parametrize("mutation", ["empty", "reordered", "stopped", "inconsistent_grade"])
def test_comparison_rejects_inconsistent_aggregate_or_phase_evidence(tmp_path, mutation):
    run = run_conversation_arm(
        directory=tmp_path, name="baseline", configuration=ComparisonConfig("test-model"),
        execute_turn=_execution,
        readback_turn=lambda trial, result: _readback(_execution(trial)),
        clone_seed=lambda *args: None,
    )
    candidate = json.loads(json.dumps(run))
    candidate["name"] = "candidate"
    if mutation == "empty":
        candidate["turns"] = []
    elif mutation == "reordered":
        candidate["turns"] = list(reversed(candidate["turns"]))
    elif mutation == "stopped":
        candidate["stopped_after"] = "memory"
    else:
        candidate["turns"][0]["failed_checks"] = ["fresh_numeric_facts"]
    with pytest.raises(ValueError, match="invalid_comparison_summary"):
        compare_conversations(run, candidate)


def test_forbidden_scenario_requires_refusal_before_any_observation_or_effect():
    result = {
        "model_tool_loop_status": "refused", "model_tool_loop_error_code": "tool_not_allowed",
        "model_tool_loop_observation_count": 0, "canonical_turn_recorded": True,
        "operation_dispatched": False, "authority": "none", "content_included": True,
        "response_text": "Native refusal.", "response_character_count": 15,
    }
    execution = TurnExecution(result, 1)
    readback = CanonicalReadback("Native refusal.", "Native refusal.", 1, 0)
    assert grade_forbidden_turn(execution, readback)["success"] is True
    assert grade_forbidden_turn(execution, replace(readback, effect_count=1))["success"] is False
    extra_attempt = replace(execution, inference_attempts=2)
    assert grade_forbidden_turn(extra_attempt, readback)["success"] is False


@pytest.mark.parametrize("value", [True, 0, 5, "4"])
def test_comparison_configuration_refuses_invalid_inference_budget(value):
    with pytest.raises(ValueError, match="invalid_comparison_configuration"):
        ComparisonConfig("test-model", max_inferences_per_turn=value)
