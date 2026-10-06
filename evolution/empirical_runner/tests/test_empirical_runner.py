"""Local and actual port-to-report integration tests (no external model claims)."""

import json
from dataclasses import FrozenInstanceError, replace

import pytest

from evolution.empirical_runner import (
    CORPUS_DIGEST,
    Arm,
    EmpiricalRunner,
    EvaluationResponse,
)


class ExecutingPort:
    def __init__(self, transform=None):
        self.calls = []
        self.transform = transform

    def evaluate(self, request):
        self.calls.append(request)
        # Implements the requested operations, not the evaluator's expected-answer lookup.
        if "integer" in request.prompt:
            words = request.prompt.rstrip(".").split()
            text = str(int(words[-3]) + int(words[-1]))
        else:
            text = request.prompt.split(": ")[-1].lower()
        result = EvaluationResponse.from_request(request, text)
        return self.transform(result) if self.transform else result


def runner(baseline=None, candidate=None, mode="fixture", **kwargs):
    return EmpiricalRunner(
        baseline=Arm("baseline", "rev-1", mode, baseline or ExecutingPort()),
        candidate=Arm("candidate", "rev-2", mode, candidate or ExecutingPort()),
        **kwargs,
    )


def test_actual_ports_execute_repeats_and_separate_holdout_with_bound_requests():
    baseline = ExecutingPort(lambda result: replace(result, text="wrong"))
    candidate = ExecutingPort()
    report = runner(baseline, candidate).run(run_id="run-01")
    assert report.status == "completed"
    assert report.conclusion == "demonstration_only"
    assert len(baseline.calls) == len(candidate.calls) == 6
    assert len(report.measurements) == report.expected_measurements == 12
    assert len({call.request_id for call in baseline.calls + candidate.calls}) == 12
    for port in (baseline, candidate):
        assert [r.repeat for r in port.calls if r.case_id == "train-add"] == [0, 1]
        assert [r.repeat for r in port.calls if r.case_id == "held-add"] == [0]
        assert {r.split for r in port.calls} == {"repeat", "holdout"}
        assert all(r.corpus_digest == CORPUS_DIGEST for r in port.calls)
        assert all(not hasattr(r, "expected") for r in port.calls)
    metrics = report.export_metrics()
    assert metrics["arms"]["baseline"]["splits"]["repeat"]["pass_rate"] == 0
    assert metrics["arms"]["candidate"]["splits"]["holdout"]["pass_rate"] == 1
    assert metrics["promotion_allowed"] is False
    serialized = json.dumps(metrics)
    assert "Return only" not in serialized
    assert "wrong" not in serialized
    assert "jarvis" not in serialized
    assert "47" not in [e["ref"] for e in metrics["evidence"]]


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", "foreign"),
        ("run_id", "foreign"),
        ("arm_id", "foreign"),
        ("arm_revision", "foreign"),
        ("case_id", "foreign"),
        ("split", "holdout"),
        ("repeat", 9),
        ("corpus_version", "foreign"),
        ("corpus_digest", "foreign"),
        ("input_digest", "foreign"),
        ("evidence_mode", "model_real"),
    ],
)
def test_tampered_output_binding_invalidates_comparison_and_scores(field, value):
    candidate = ExecutingPort(lambda result: replace(result, **{field: value}))
    report = runner(candidate=candidate).run(run_id="run-tampered")
    assert report.status == "invalid"
    assert report.reason == "response_binding_mismatch"
    assert report.conclusion == "comparison_unavailable"
    assert report.export_metrics()["arms"]["baseline"]["splits"]["repeat"]["pass_rate"] is None
    assert len(candidate.calls) == 1


@pytest.mark.parametrize("output", ["", "x" * 2001, "bad\x00", "bad\ud800", 4, None])
def test_invalid_output_never_scored(output):
    report = runner(candidate=ExecutingPort(lambda r: replace(r, text=output))).run(
        run_id="run-bad"
    )
    assert report.reason == "invalid_output"
    assert report.status == "invalid"


@pytest.mark.parametrize("status", ["incomplete", "failed", "cancelled"])
def test_incomplete_response_invalid(status):
    report = runner(candidate=ExecutingPort(lambda r: replace(r, status=status))).run(run_id="run")
    assert report.reason == "incomplete_response"


def test_injected_exception_and_arbitrary_object_are_not_success():
    class Exploding:
        def evaluate(self, request):
            raise RuntimeError("secret response or credentials")

    report = runner(candidate=Exploding()).run(run_id="run")
    assert report.reason == "port_or_control_error"
    assert "secret" not in json.dumps(report.export_metrics())
    report = runner(candidate=ExecutingPort(lambda r: object())).run(run_id="run")
    assert report.reason == "invalid_response"


def test_cancellation_before_calls_and_after_port_return():
    baseline = ExecutingPort()
    candidate = ExecutingPort()
    report = runner(baseline, candidate).run(run_id="run", cancelled=lambda: True)
    assert report.status == "inconclusive"
    assert report.reason == "cancelled"
    assert not baseline.calls and not candidate.calls
    report = runner(baseline, candidate).run(run_id="run", cancelled=lambda: bool(baseline.calls))
    assert report.reason == "cancelled"
    assert len(baseline.calls) == 1 and not candidate.calls
    assert not report.measurements


def test_late_synchronous_port_result_discarded():
    ticks = iter([0, 0, 2])
    baseline = ExecutingPort()
    report = runner(baseline=baseline, clock=lambda: next(ticks)).run(
        run_id="run", timeout_seconds=1
    )
    assert report.status == "inconclusive"
    assert report.reason == "deadline_exceeded"
    assert len(baseline.calls) == 1
    assert not report.measurements


def test_deadline_before_call_and_clock_regression():
    ticks = iter([0, 2])
    report = runner(clock=lambda: next(ticks)).run(run_id="run", timeout_seconds=1)
    assert report.reason == "deadline_exceeded"
    ticks = iter([1, 0])
    report = runner(clock=lambda: next(ticks)).run(run_id="run")
    assert report.status == "invalid" and report.reason == "invalid_clock"


@pytest.mark.parametrize("mode", ["core_local", "model_real"])
def test_declared_nonfixture_mode_is_measurement_only_not_proof_or_promotion(mode):
    report = runner(mode=mode).run(run_id="run")
    assert report.status == "completed"
    assert report.conclusion == "measurement_only_no_promotion"
    assert report.export_metrics()["promotion_allowed"] is False


def test_mixed_evidence_modes_cannot_produce_comparable_rates():
    report = EmpiricalRunner(
        baseline=Arm("baseline", "v1", "fixture", ExecutingPort()),
        candidate=Arm("candidate", "v1", "core_local", ExecutingPort()),
    ).run(run_id="run")
    assert report.reason == "mixed_evidence_modes"
    assert report.status == "inconclusive"
    assert report.export_metrics()["arms"]["candidate"]["splits"]["holdout"]["pass_rate"] is None


def test_request_contract_frozen_and_has_no_expected_answers():
    port = ExecutingPort()
    runner(baseline=port).run(run_id="run")
    with pytest.raises(FrozenInstanceError):
        port.calls[0].case_id = "new"


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 301, "2"])
def test_timeout_bounds(timeout):
    with pytest.raises(ValueError, match="invalid_timeout"):
        runner().run(run_id="run", timeout_seconds=timeout)


@pytest.mark.parametrize("repeats", [0, 1, 11, True, 2.0])
def test_repeat_bounds(repeats):
    with pytest.raises(ValueError, match="repeats_out_of_bounds"):
        runner(repeats=repeats)


def test_arm_and_run_ids_reject_content_in_metrics_and_unknown_modes():
    with pytest.raises(ValueError):
        runner().run(run_id="contains secrets and spaces")
    with pytest.raises(ValueError):
        Arm("arm", "rev", "network", ExecutingPort())
    with pytest.raises(ValueError):
        EmpiricalRunner(
            baseline=Arm("same", "1", "fixture", ExecutingPort()),
            candidate=Arm("same", "2", "fixture", ExecutingPort()),
        )


def test_frozen_request_bypass_cannot_rebind_response_after_call():
    class TamperingPort:
        def evaluate(self, request):
            object.__setattr__(request, "case_id", "foreign")
            return EvaluationResponse.from_request(request, "42")

    report = runner(candidate=TamperingPort()).run(run_id="run")
    assert report.reason == "response_binding_mismatch"


def test_boolean_repeat_is_not_equal_to_integer_repeat():
    report = runner(candidate=ExecutingPort(lambda r: replace(r, repeat=False))).run(run_id="run")
    assert report.reason == "response_binding_mismatch"


def test_nonnumeric_clock_after_port_return_is_invalid():
    ticks = iter([0, 0, "not-a-time"])
    report = runner(clock=lambda: next(ticks)).run(run_id="run")
    assert report.reason == "invalid_clock"


@pytest.mark.parametrize("field,value", [("prompt", "foreign"), ("deadline", 999999999)])
def test_request_content_or_deadline_mutation_rejected(field, value):
    class TamperingPort:
        def evaluate(self, request):
            object.__setattr__(request, field, value)
            return EvaluationResponse.from_request(request, "42")

    report = runner(candidate=TamperingPort()).run(run_id="run")
    assert report.reason == "request_tampered"
