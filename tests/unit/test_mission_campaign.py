"""Campaign controls prove accounting/binding, not an agent's intelligence."""

import json
from dataclasses import fields, replace

import pytest

from evals.operator_tasks import campaign as module
from evals.operator_tasks.campaign import CampaignArm, CampaignBudget, MissionCampaign
from evals.operator_tasks.fixture_port import FixtureTaskPort
from evals.operator_tasks.mission_corpus import MISSIONS
from evals.operator_tasks.mission_grader import MissionGrade
from evals.operator_tasks.runner import ExecutionResult


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class Port:
    evidence_mode = "fixture"

    def __init__(self, name, *, order=None, action=None):
        self.name, self.order, self.action = name, order, action
        self.requests = []

    def execute(self, request):
        self.requests.append(request)
        if self.order is not None:
            self.order.append(self.name)
        if self.action is not None:
            return self.action(request)
        return ExecutionResult(request.binding, "completed", b"invalid-public-test-payload")


def arm(name, port=None, **patch):
    capabilities = tuple(sorted({
        cap for mission in MISSIONS for cap in mission.required_capabilities
    }))
    values = dict(
        arm_id=name, harness_id="test-harness", revision="test-rev", evidence_mode="fixture",
        model_id=None, provider_id=None, environment_id="isolated-test",
        tool_policy_id="no-actions", capabilities=capabilities, port=port or Port(name),
    )
    values.update(patch)
    return CampaignArm(**values)


def selected(count=1):
    return tuple(mission.case_id for mission in MISSIONS[:count])


def passing_grader(monkeypatch):
    monkeypatch.setattr(module, "grade_mission", lambda *_args, **_kwargs:
                        MissionGrade("passed", True, ("bound_product",), ()))


def run(left, right, *, clock=None, case_ids=None, **options):
    return MissionCampaign(baseline=left, candidate=right, clock=clock or Clock()).run(
        selected() if case_ids is None else case_ids,
        run_id="public-test-run", authorized=True, **options,
    )


def test_no_dispatch_without_explicit_opt_in_or_valid_selection():
    left, right = arm("left"), arm("right")
    campaign = MissionCampaign(baseline=left, candidate=right, clock=Clock())
    for options in ({}, {"authorized": 1}):
        with pytest.raises(ValueError, match="mission_campaign_opt_in_required"):
            campaign.run(selected(), run_id="test", **options)
    for selection in ((), selected() * 2, ("unknown-public-case",), list(selected())):
        with pytest.raises(ValueError):
            campaign.run(selection, run_id="test", authorized=True)
    with pytest.raises(ValueError, match="invalid_campaign_reference"):
        campaign.run(selected(), run_id="not.v1.bound", authorized=True)
    assert not left.port.requests and not right.port.requests


@pytest.mark.parametrize("repeats", [1, 6, True, "2"])
def test_repeats_are_bounded_before_dispatch(repeats):
    with pytest.raises(ValueError, match="invalid_campaign"):
        MissionCampaign(baseline=arm("left"), candidate=arm("right"), repeats=repeats)


@pytest.mark.parametrize("patch", [
    {"arm_id": "../private/path"}, {"model_id": "Bearer secret"},
    {"revision": "sk-private-key"}, {"capabilities": ("text_reasoning", "text_reasoning")},
    {"evidence_mode": "model_real", "model_id": None},
    {"port": object()}, {"capabilities": ["text_reasoning"]},
])
def test_explicit_registration_is_closed_and_content_free(patch):
    with pytest.raises(ValueError) as caught:
        arm("left", **patch)
    assert "secret" not in str(caught.value) and "private" not in str(caught.value)


def test_known_fixture_cannot_be_relabelled_as_real_provider():
    port = FixtureTaskPort()
    port.evidence_mode = "model_real"
    with pytest.raises(ValueError, match="invalid_campaign_arm"):
        arm("pretend", port, evidence_mode="model_real",
            model_id="public-model", provider_id="test")


def test_counterbalance_across_cases_and_repeats_and_fresh_bindings(monkeypatch):
    passing_grader(monkeypatch)
    order = []
    left, right = arm("left", Port("left", order=order)), arm("right", Port("right", order=order))
    report = run(left, right, case_ids=selected(2))
    assert order == ["left", "right", "right", "left", "right", "left", "left", "right"]
    requests = left.port.requests + right.port.requests
    assert len({request.binding.request_id for request in requests}) == 8
    assert len({request.binding.session_ref for request in requests}) == 8
    assert all(request.binding.task_digest for request in requests)
    assert all({field.name for field in fields(request)} == {
        "binding", "brief", "sources", "deadline", "history",
    } for request in requests)
    assert all(request.history is None for request in requests)
    assert all(not hasattr(request, "expected") and not hasattr(request, "oracle")
               for request in requests)
    exported = report.export_metrics()
    assert exported["port_dispatches"] == exported["expected_measurements"] == 8
    assert exported["comparison_status"] == "control_only"
    assert exported["winner"] is None and not exported["sota_claim"]
    assert not exported["promotion_allowed"] and not exported["improvement_claim"]
    assert all(item["denominator_total"] == item["passed"] == 4 for item in exported["arms"])


def test_each_run_has_new_request_ids_even_with_reused_run_label(monkeypatch):
    passing_grader(monkeypatch)
    left, right = arm("left"), arm("right")
    run(left, right)
    initial = {request.binding.request_id for request in left.port.requests + right.port.requests}
    run(left, right)
    later = {request.binding.request_id
             for request in left.port.requests[2:] + right.port.requests[2:]}
    assert initial.isdisjoint(later)


def test_unsupported_keeps_total_denominator_and_never_calls_port_or_grader(monkeypatch):
    left, right = arm("left", capabilities=()), arm("right", capabilities=())
    monkeypatch.setattr(module, "grade_mission",
                        lambda *_a, **_kw: pytest.fail("unsupported graded"))
    exported = run(left, right).export_metrics()
    assert exported["port_dispatches"] == 0 and exported["reported_measurements"] == 4
    assert len(exported["capability_gaps"]) == 2
    assert all(item["missing_capabilities"] for item in exported["capability_gaps"])
    for summary in exported["arms"]:
        assert summary["denominator_total"] == summary["not_run"] == summary["unsupported"] == 2
        assert summary["passed"] == 0 and summary["success_rate_total"] == 0
        assert summary["input_units"] is None and summary["cost"] is None
    assert all(item["elapsed_ms"] is None for item in exported["measurements"])
    assert not left.port.requests and not right.port.requests


def test_actual_independent_grader_does_not_pass_invalid_payload():
    exported = run(arm("left"), arm("right")).export_metrics()
    assert all(not item["success"] for item in exported["measurements"])
    assert all(item["outcome"] in {"invalid_output", "blocked"}
               for item in exported["measurements"])


@pytest.mark.parametrize("patch", [
    {"model_id": "other-model"}, {"provider_id": "other-provider"},
    {"environment_id": "other-environment"}, {"tool_policy_id": "other-policy"},
    {"budget": CampaignBudget(timeout_seconds=1)},
])
def test_different_declared_conditions_are_not_head_to_head(monkeypatch, patch):
    passing_grader(monkeypatch)
    left_port, right_port = Port("left"), Port("right")
    left_port.evidence_mode = right_port.evidence_mode = "model_real"
    base = dict(evidence_mode="model_real", model_id="same-model", provider_id="same-provider")
    exported = run(arm("left", left_port, **base),
                   arm("right", right_port, **(base | patch))).export_metrics()
    assert not exported["declared_conditions_match"]
    assert exported["comparison_status"] == "not_comparable" and exported["winner"] is None


def test_matching_real_registration_is_configuration_only_not_budget_proof(monkeypatch):
    passing_grader(monkeypatch)
    left, right = Port("left"), Port("right")
    left.evidence_mode = right.evidence_mode = "model_real"
    metadata = dict(evidence_mode="model_real", model_id="same-model", provider_id="same-provider")
    exported = run(arm("left", left, **metadata), arm("right", right, **metadata)).export_metrics()
    assert exported["declared_conditions_match"]
    assert exported["comparison_status"] == "matched_configuration_only"
    assert not exported["paired_budget_execution_verified"]
    assert all(item["model_calls"] is None for item in exported["arms"])


def test_mixed_fixture_and_native_never_become_model_comparison(monkeypatch):
    passing_grader(monkeypatch)
    native = Port("native")
    native.evidence_mode = "core_local"
    exported = run(arm("fixture"), arm("native", native,
                   evidence_mode="core_local")).export_metrics()
    assert exported["comparison_status"] == "not_comparable"
    assert not exported["declared_conditions_match"] and exported["winner"] is None


def test_dispatch_cap_stops_before_next_port_but_accounts_all_selected_cells(monkeypatch):
    passing_grader(monkeypatch)
    left, right = arm("left"), arm("right")
    report = run(left, right, max_executions=1)
    exported = report.export_metrics()
    assert exported["port_dispatches"] == 1
    assert len(left.port.requests) + len(right.port.requests) == 1
    assert len(exported["measurements"]) == 4
    assert sum(item["outcome"] == "execution_limit" for item in exported["measurements"]) == 3
    assert exported["status"] == "inconclusive"


@pytest.mark.parametrize("state,reason", [(True, "cancelled"), ("yes", "control_error")])
def test_control_before_dispatch_never_calls_port(state, reason):
    left, right = arm("left"), arm("right")
    exported = run(left, right, cancelled=lambda: state).export_metrics()
    assert exported["reason"] == reason and exported["port_dispatches"] == 0
    assert all(item["status"] == "not_run" for item in exported["measurements"])


def test_cancellation_after_dispatch_discards_grade_and_accounts_failure(monkeypatch):
    state = [False]

    def execute(request):
        state[0] = True
        return ExecutionResult(request.binding, "completed", b"private generated output")

    monkeypatch.setattr(module, "grade_mission", lambda *_a, **_kw: pytest.fail("cancelled graded"))
    exported = run(arm("left", Port("left", action=execute)), arm("right"),
                   cancelled=lambda: state[0]).export_metrics()
    assert exported["port_dispatches"] == 1
    assert exported["measurements"][0]["status"] == "executed"
    assert exported["measurements"][0]["outcome"] == "cancelled"
    assert "private generated output" not in json.dumps(exported)


@pytest.mark.parametrize("advance,reason", [(-1, "invalid_clock"), (6, "deadline_exceeded")])
def test_bad_clock_or_global_deadline_after_port_stops_further_calls(advance, reason):
    clock = Clock()

    def execute(request):
        clock.now += advance
        return ExecutionResult(request.binding, "completed", b"private generated output")

    exported = run(arm("left", Port("left", action=execute)), arm("right"),
                   clock=clock, timeout_seconds=5).export_metrics()
    assert exported["reason"] == reason and exported["port_dispatches"] == 1
    assert all(not item["success"] for item in exported["measurements"])
    if reason == "invalid_clock":
        assert exported["elapsed_ms"] is None


def test_per_execution_deadline_rejects_late_payload_without_stopping_other_arm(monkeypatch):
    clock = Clock()

    def execute(request):
        clock.now += 2
        return ExecutionResult(request.binding, "completed", b"late private output")

    passing_grader(monkeypatch)
    exported = run(arm("left", Port("left", action=execute), budget=CampaignBudget(1)),
                   arm("right"), clock=clock).export_metrics()
    left = [item for item in exported["measurements"] if item["arm_id"] == "left"]
    assert all(item["outcome"] == "execution_deadline_exceeded" for item in left)
    assert exported["port_dispatches"] == 4


@pytest.mark.parametrize("fault", [
    "binding", "usage", "status", "payload", "request_deadline", "request_source",
])
def test_candidate_cannot_change_binding_metadata_or_public_sources(monkeypatch, fault):
    passing_grader(monkeypatch)
    original_digest = MISSIONS[0].digest

    def execute(request):
        if fault == "request_deadline":
            object.__setattr__(request, "deadline", "private tampered deadline")
        if fault == "request_source":
            object.__setattr__(request.sources[0], "text", "private tampered source")
        return ExecutionResult(
            replace(request.binding, revision="stale") if fault == "binding" else request.binding,
            [] if fault == "status" else "completed",
            "private raw output" if fault == "payload" else b"test output",
            input_units=True if fault == "usage" else None,
        )

    exported = run(arm("left", Port("left", action=execute)), arm("right")).export_metrics()
    left = [item for item in exported["measurements"] if item["arm_id"] == "left"]
    assert all(not item["success"] for item in left)
    assert all(item["outcome"] in {"binding_or_metadata_refused", "request_tampered"}
               for item in left)
    assert MISSIONS[0].digest == original_digest
    assert "private" not in json.dumps(exported)


def test_unknown_usage_is_not_zero_and_all_exports_omit_input_identity_and_payload(monkeypatch):
    passing_grader(monkeypatch)
    left, right = arm("left"), arm("right")
    exported = run(left, right).export_metrics()
    encoded = json.dumps(exported)
    for item in exported["arms"]:
        assert item["input_units"] is item["output_units"] is item["cost"] is None
    for request in left.port.requests + right.port.requests:
        assert request.brief not in encoded
        assert request.binding.subject_ref not in encoded
        assert request.binding.session_ref not in encoded
        assert request.binding.request_id not in encoded
        assert request.binding.run_id not in encoded
    assert "invalid-public-test-payload" not in encoded


def test_port_failures_are_filtered_without_retry(monkeypatch):
    def broken(_request):
        raise RuntimeError("private credential and absolute path")

    passing_grader(monkeypatch)
    left, right = arm("left", Port("left", action=broken)), arm("right")
    exported = run(left, right).export_metrics()
    assert len(left.port.requests) == 2
    assert all(item["outcome"] == "port_error" for item in exported["measurements"]
               if item["arm_id"] == "left")
    assert "private credential" not in json.dumps(exported)


def test_grader_failure_is_content_free_and_trusted_effect_callback_is_forwarded(monkeypatch):
    def verifier(*_args):
        return False

    def grade(_mission, _binding, _result, *, available_capabilities, verify_effect):
        assert available_capabilities
        assert verify_effect is verifier
        raise RuntimeError("private effect verification failure")

    monkeypatch.setattr(module, "grade_mission", grade)
    exported = run(arm("left", verify_effect=verifier),
                   arm("right", verify_effect=verifier)).export_metrics()
    assert all(item["outcome"] == "grading_error" for item in exported["measurements"])
    assert "private effect" not in json.dumps(exported)


def test_cancellation_during_grading_does_not_accept_partial_success(monkeypatch):
    state = [False]

    def grade(*_args, **_kwargs):
        state[0] = True
        return MissionGrade("passed", True, ("bound_product",), ())

    monkeypatch.setattr(module, "grade_mission", grade)
    exported = run(arm("left"), arm("right"), cancelled=lambda: state[0]).export_metrics()
    assert exported["reason"] == "cancelled" and exported["port_dispatches"] == 1
    assert all(not item["success"] for item in exported["measurements"])
