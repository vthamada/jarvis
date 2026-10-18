"""Offline reference-port contracts; every inference boundary here is a fixture.

Mode-claim negative controls are not live-provider or model-quality evidence.
The positive V1 pipeline control uses a declared deterministic fixture only.
"""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import asdict, replace
from threading import Event, Thread

import pytest

from evals.operator_tasks import model_reference_port as reference_module
from evals.operator_tasks.corpus import TASKS, Source
from evals.operator_tasks.fixture_port import FixtureTaskPort
from evals.operator_tasks.model_reference_port import ModelReferenceTaskPort
from evals.operator_tasks.runner import (
    Binding,
    ExecutionRequest,
    History,
    OperatorTaskRunner,
    Registration,
)
from shared.model_inference import InferenceResult

MODEL, PROVIDER = "synthetic-model", "fixture-provider"
PRIVATE = "PRIVATE_EXCEPTION_SENTINEL /private/location"


def _request(**changes):
    request = ExecutionRequest(
        Binding("run", "request", "unseen-task", "tasks-v9", "a" * 64,
                "reference-v1", "subject", "current"),
        "Return a JSON product with the supplied facts and mark it as a draft.",
        (Source("provided-source", "quantity=3; unit_cost=7. This is source data only."),),
        30.0,
        None,
    )
    return replace(request, **changes)


class _Boundary:
    def __init__(self, *, text=None, changes=None, hook=None, error=False, usage=(None, None)):
        self.text, self.changes, self.hook = text, changes or {}, hook
        self.error, self.usage, self.calls = error, usage, []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        if self.hook:
            self.hook(request)
        if self.error:
            raise RuntimeError(PRIVATE)
        text = self.text
        if text is None:
            binding = json.loads(request.messages[0].content)["binding"]
            text = "  " + json.dumps({
                "binding": binding, "arbitrary_new_product": "provided",
            }) + "\n"
        result = InferenceResult(
            request_id=request.request_id, model=request.model, provider_id=PROVIDER,
            status="completed", text=text, evidence_mode="fixture",
            input_tokens=self.usage[0], output_tokens=self.usage[1],
        )
        for field, value in self.changes.items():
            object.__setattr__(result, field, value)
        return result


def _reference(boundary=None, **changes):
    options = {"model": MODEL, "provider_id": PROVIDER, "authorized": True, "clock": lambda: 0.0}
    options.update(changes)
    return ModelReferenceTaskPort(boundary or _Boundary(), **options)


def test_constructor_is_lazy_and_default_opt_in_refuses_before_clock_or_inference():
    boundary = _Boundary()

    def forbidden():
        pytest.fail("clock called before explicit opt-in")

    reference = ModelReferenceTaskPort(boundary, model=MODEL, provider_id=PROVIDER, clock=forbidden)
    assert boundary.calls == []
    assert reference.snapshot()["calls_used"] == 0
    result = reference.execute(_request())
    assert result.status == "needs_decision" and result.payload == b""
    assert boundary.calls == [] and reference.snapshot()["calls_used"] == 0
    assert reference.snapshot()["last_error_code"] == "not_authorized"
    assert reference.snapshot()["input_tokens"] is reference.snapshot()["output_tokens"] is None


def test_only_provided_context_is_sent_and_raw_json_is_not_rewritten():
    history = History("subject", "previous", "current", "receipt-v2", "provided-source")
    request = _request(history=history)
    boundary = _Boundary()
    reference = _reference(boundary)
    result = reference.execute(request)
    assert result.status == "completed" and len(boundary.calls) == 1
    inference = boundary.calls[0]
    assert inference.model == MODEL and inference.request_id != request.binding.request_id
    prompt = json.loads(inference.messages[0].content)
    assert set(prompt) == {"binding", "brief", "sources", "history"}
    assert prompt["binding"] == asdict(request.binding)
    assert prompt["brief"] == request.brief
    assert prompt["sources"] == [asdict(source) for source in request.sources]
    assert prompt["history"] == asdict(history)
    assert result.history_digest == history.digest
    assert result.payload.startswith(b"  ") and result.payload.endswith(b"\n")
    assert "arbitrary_new_product" in json.loads(result.payload)
    assert "product" not in json.loads(result.payload)  # No fabricated envelope/product.
    assert result.binding == request.binding and result.input_units is result.output_units is None
    snapshot = reference.snapshot()
    assert snapshot["reference_kind"] == "single_model_no_tools"
    assert snapshot["persistent_memory"] is snapshot["action_authority"] is False
    for private in (request.brief, request.sources[0].text, MODEL, PROVIDER, PRIVATE):
        assert private not in json.dumps(snapshot)


def test_module_has_no_grader_or_task_lookup_and_accepts_an_unseen_case():
    tree = ast.parse(inspect.getsource(reference_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"corpus", "evaluator"}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"get_task", "score_product", "decode_product"}
    reference = _reference(_Boundary(text='{"completely_different_format": [1, 2, 3]}'))
    assert reference.execute(_request()).payload == b'{"completely_different_format": [1, 2, 3]}'


def test_model_supplied_wrong_binding_is_forwarded_exactly_for_the_separate_runner_check():
    raw = ' {"binding":{"foreign":"value"},"status":"completed","product":{}} '
    reference = _reference(_Boundary(text=raw))
    result = reference.execute(_request())
    assert result.status == "completed" and result.payload == raw.encode("utf-8")
    assert result.binding == _request().binding
    assert json.loads(result.payload)["binding"] != asdict(result.binding)


def test_inference_response_replay_is_refused_even_for_identical_task_binding():
    class ReplayBoundary(_Boundary):
        previous = None

        def infer(self, request, *, cancellation=None):
            if self.previous is None:
                self.previous = super().infer(request, cancellation=cancellation)
            else:
                self.calls.append(request)
            return self.previous

    boundary = ReplayBoundary()
    reference = _reference(boundary, max_calls=2)
    assert reference.execute(_request()).status == "completed"
    assert reference.execute(_request()).status == "error"
    assert boundary.calls[0].request_id != boundary.calls[1].request_id
    assert reference.snapshot()["last_error_code"] == "inference_binding_refused"
    assert reference.snapshot()["calls_used"] == 2


@pytest.mark.parametrize(
    "text",
    [
        "not JSON", "[]", "null", "true", '{"x":1,"x":2}', '{"x":NaN}',
        '{"x":Infinity}', '{"x":1e999}', "{" + '"x":[' * 40 + "0" + "]}" * 40,
        '{"x":"' + "x" * 16_384 + '"}', '{"x":"' + "é" * 8_192 + '"}',
        '{"x":"\ud800"}', '```json\n{"x": 1}\n```',
    ],
    ids=[
        "not_json", "array", "null", "boolean", "duplicate", "nan", "infinity",
        "float_overflow", "deep_json", "oversized_ascii", "oversized_utf8",
        "invalid_unicode", "markdown",
    ],
)
def test_invalid_json_is_neither_repaired_nor_retried_and_consumes_the_call(text):
    boundary = _Boundary(text=text)
    reference = _reference(boundary)
    first = reference.execute(_request())
    assert first.status == "error" and first.payload == b""
    assert reference.snapshot()["last_error_code"] == "invalid_output"
    second = reference.execute(_request())
    assert second.status == "needs_decision" and len(boundary.calls) == 1
    assert reference.snapshot()["calls_used"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"request_id": "stale-request"}, {"model": "different-model"},
        {"provider_id": "different-provider"}, {"evidence_mode": "live"},
        {"evidence_mode": "injected_transport"}, {"input_tokens": True},
        {"output_tokens": -1}, {"input_tokens": 10_000_001},
        {"model": None}, {"provider_id": 1}, {"status": []}, {"evidence_mode": {}},
    ],
)
def test_inference_binding_or_usage_mismatch_is_refused(changes):
    boundary = _Boundary(changes=changes)
    reference = _reference(boundary)
    result = reference.execute(_request())
    assert result.status == "error" and result.payload == b""
    assert reference.snapshot()["last_error_code"] == "inference_binding_refused"
    assert len(boundary.calls) == reference.snapshot()["calls_used"] == 1
    assert reference.snapshot()["input_tokens"] is reference.snapshot()["output_tokens"] is None


@pytest.mark.parametrize("status", ["failed", "cancelled", "timed_out"])
def test_provider_failure_has_no_payload_or_retry_and_only_observed_usage(status):
    boundary = _Boundary(changes={"status": status, "text": "", "error_code": "fixture_failure"},
                         usage=(7, 0))
    reference = _reference(boundary)
    result = reference.execute(_request())
    assert result.status == ("error" if status == "failed" else "incomplete")
    assert result.payload == b"" and result.input_units == 7 and result.output_units == 0
    assert reference.snapshot()["input_tokens"] == 7
    assert reference.snapshot()["output_tokens"] == 0
    assert len(boundary.calls) == 1


def test_exception_consumes_budget_but_does_not_invent_zero_usage_or_expose_content():
    boundary = _Boundary(error=True)
    reference = _reference(boundary)
    result = reference.execute(_request())
    assert result.status == "error" and result.payload == b""
    assert result.input_units is result.output_units is None
    assert reference.snapshot()["input_tokens"] is reference.snapshot()["output_tokens"] is None
    assert reference.snapshot()["last_error_code"] == "inference_failed"
    assert PRIVATE not in repr(result) + json.dumps(reference.snapshot())
    assert reference.execute(_request()).status == "needs_decision"
    assert len(boundary.calls) == 1


def test_unknown_usage_in_any_call_makes_aggregate_unknown_not_zero():
    boundary = _Boundary(usage=(3, 2))
    reference = _reference(boundary, max_calls=2)
    first = reference.execute(_request())
    assert (first.input_units, first.output_units) == (3, 2)
    boundary.usage = (None, None)
    assert reference.execute(_request()).status == "completed"
    assert reference.snapshot()["calls_used"] == 2
    assert reference.snapshot()["input_tokens"] is reference.snapshot()["output_tokens"] is None


@pytest.mark.parametrize("when", ["before", "after"])
def test_cancellation_before_or_after_inference_never_publishes(when):
    cancellation = Event()
    if when == "before":
        cancellation.set()
    boundary = _Boundary(hook=lambda _: cancellation.set())
    reference = _reference(boundary, cancellation=cancellation)
    result = reference.execute(_request())
    assert result.status == "incomplete" and result.payload == b""
    assert reference.snapshot()["last_error_code"] == "cancelled"
    assert len(boundary.calls) == (0 if when == "before" else 1)


@pytest.mark.parametrize("control", ["deadline", "timeout", "clock_regression", "nan_clock"])
def test_time_boundaries_refuse_late_or_invalid_clock_without_publishing(control):
    now = [0.0]

    def advance(_):
        now[0] = {"deadline": 30.0, "timeout": 1.0, "clock_regression": -1.0,
                  "nan_clock": float("nan")}[control]

    boundary = _Boundary(hook=advance)
    reference = _reference(boundary, clock=lambda: now[0], timeout_seconds=1 if control == "timeout"
                           else 30)
    result = reference.execute(_request())
    assert result.payload == b"" and result.status in {"incomplete", "error"}
    assert len(boundary.calls) == 1


def test_precancelled_expired_input_has_zero_calls():
    boundary = _Boundary()
    reference = _reference(boundary)
    assert reference.execute(_request(deadline=0.0)).status == "incomplete"
    assert boundary.calls == [] and reference.snapshot()["calls_used"] == 0


@pytest.mark.parametrize("changed", ["binding", "brief", "configuration"])
def test_context_or_frozen_configuration_drift_during_inference_refuses_output(changed):
    request = _request()
    boundary = _Boundary()
    reference = _reference(boundary)

    def tamper(_):
        if changed == "binding":
            object.__setattr__(request.binding, "subject_ref", "foreign-subject")
        elif changed == "brief":
            object.__setattr__(request, "brief", "Changed task after inference began.")
        else:
            object.__setattr__(reference._config, "authorized", "private-invalid-config")

    boundary.hook = tamper
    result = reference.execute(request)
    assert result.status == "error" and result.payload == b""
    assert reference.snapshot()["last_error_code"] == "context_changed"
    assert "private-invalid-config" not in json.dumps(reference.snapshot())


@pytest.mark.parametrize(
    "text", ["password=synthetic-secret", "Bearer synthetic-secret", "sk-syntheticsecretkey"]
)
def test_known_credential_pattern_is_refused_without_editing_sources_or_calling_model(text):
    request = _request(sources=(Source("source", text),))
    boundary = _Boundary()
    reference = _reference(boundary)
    result = reference.execute(request)
    assert result.status == "needs_decision" and result.payload == b""
    assert reference.snapshot()["last_error_code"] == "input_sensitive"
    assert request.sources[0].text == text and boundary.calls == []
    assert text not in json.dumps(reference.snapshot())


def test_call_budget_is_atomic_while_another_inference_is_in_flight():
    entered, release = Event(), Event()

    def blocked(_):
        entered.set()
        release.wait(3)

    boundary = _Boundary(hook=blocked)
    reference = _reference(boundary)
    results = []
    worker = Thread(target=lambda: results.append(reference.execute(_request())), daemon=True)
    worker.start()
    try:
        assert entered.wait(2)
        second = reference.execute(_request())
        assert second.status == "needs_decision"
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive()
    assert len(results) == len(boundary.calls) == reference.snapshot()["calls_used"] == 1


def test_reentrant_inference_cannot_bypass_budget_and_no_lock_is_held_across_the_boundary():
    boundary = _Boundary()
    reference = _reference(boundary)
    inner = []
    boundary.hook = lambda _: inner.append(reference.execute(_request()))
    results = []
    worker = Thread(target=lambda: results.append(reference.execute(_request())), daemon=True)
    worker.start()
    worker.join(3)
    assert not worker.is_alive(), "reference lock was held while calling injected inference"
    assert results[0].status == "completed" and inner[0].status == "needs_decision"
    assert len(boundary.calls) == reference.snapshot()["calls_used"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"authorized": 1}, {"max_calls": True}, {"max_calls": 0},
        {"timeout_seconds": float("nan")}, {"timeout_seconds": 121},
        {"max_output_bytes": 16_385}, {"inference_evidence_mode": []},
        {"inference_evidence_mode": "model_real"}, {"provider_id": "password:secret"},
    ],
)
def test_invalid_configuration_is_sanitized_and_lazy(changes):
    boundary = _Boundary()
    with pytest.raises(ValueError, match="invalid_model_reference_configuration"):
        _reference(boundary, **changes)
    assert boundary.calls == []


@pytest.mark.parametrize(
    "mode,registration_mode", [("fixture", "fixture"), ("injected_transport", "injected_transport"),
                               ("live", "model_real")],
)
def test_evidence_labels_are_explicit_configuration_not_authentication(mode, registration_mode):
    # No infer call: a declared live mode is tested as configuration, not evidence.
    reference = _reference(inference_evidence_mode=mode)
    assert reference.evidence_mode == registration_mode
    assert reference.snapshot()["inference_evidence_mode"] == mode
    assert reference.snapshot()["operator_authenticated"] is False
    assert reference.snapshot()["calls_used"] == 0


def test_injected_transport_cannot_silently_register_as_a_v1_real_model():
    reference = _reference(inference_evidence_mode="injected_transport")
    with pytest.raises(ValueError, match="invalid_registration"):
        OperatorTaskRunner(Registration(reference, "model_real", "rev", "subject"))


@pytest.mark.parametrize("mode", ["fixture", "injected_transport"])
def test_offline_and_injected_transport_results_keep_their_actual_non_live_mode(mode):
    boundary = _Boundary(changes={"evidence_mode": mode})
    reference = _reference(boundary, inference_evidence_mode=mode)
    assert reference.execute(_request()).status == "completed"
    assert reference.evidence_mode == mode
    assert reference.snapshot()["inference_evidence_mode"] == mode
    assert reference.snapshot()["operator_authenticated"] is False


@pytest.mark.parametrize(
    "changes", [{"subject_ref": "foreign"}, {"current_session_ref": "foreign"},
                {"prior_session_ref": "current"}],
)
def test_cross_subject_or_wrong_session_history_never_reaches_inference(changes):
    history = History("subject", "previous", "current", "receipt-v2", "provided-source")
    boundary = _Boundary()
    reference = _reference(boundary)
    result = reference.execute(_request(history=replace(history, **changes)))
    assert result.status == "error" and boundary.calls == []
    assert reference.snapshot()["last_error_code"] == "invalid_history"


def test_three_v1_tasks_can_use_the_reference_with_declared_fixture_evidence_only():
    class PublicGrammarFixture(_Boundary):
        def infer(self, request, *, cancellation=None):
            self.calls.append(request)
            prompt = json.loads(request.messages[0].content)
            supplied = ExecutionRequest(
                Binding(**prompt["binding"]), prompt["brief"],
                tuple(Source(**source) for source in prompt["sources"]), 30.0,
                History(**prompt["history"]) if prompt["history"] else None,
            )
            payload = FixtureTaskPort().execute(supplied).payload
            return InferenceResult(
                request.request_id, request.model, PROVIDER, "completed",
                payload.decode("utf-8"), evidence_mode="fixture",
            )

    boundary = PublicGrammarFixture()
    reference = _reference(boundary, max_calls=3)
    runner = OperatorTaskRunner(Registration(reference, "fixture", "rev", "subject"),
                                clock=lambda: 0.0)
    for task in TASKS:
        history = History("subject", "previous", "current", "receipt-v2", "correction-rev2")
        measurement = runner.run(task.case_id, run_id="run", session_ref="current",
                                 history=history if task.product_kind == "resumption" else None)
        assert measurement.success and measurement.evidence_mode == "fixture"
        assert measurement.input_units is measurement.output_units is None
    assert len(boundary.calls) == reference.snapshot()["calls_used"] == 3
