"""Contract tests for the opt-in loop; collaborators are explicit fixture ports."""

import json
from dataclasses import FrozenInstanceError, replace
from threading import Event

import pytest

from shared.model_inference import InferenceResult
from shared.model_tool_loop import (
    ToolAuthorization,
    ToolCall,
    ToolCitation,
    ToolLoopContext,
    ToolObservation,
    call_fingerprint,
    run_tool_loop,
)

CONTEXT = ToolLoopContext("request-one", "Compare the selected reports.", "binding-one",
                          ("documentation", "observability"))
REPORT = "Documentation: baseline is recorded.\nObservability: signals are logged."


def proposal(call_id="read-one", resource_id="documentation", tool="read_local_report"):
    return {"kind": "tool_call", "call_id": call_id, "tool": tool,
            "arguments": {"resource_id": resource_id}}


def final(call_id="read-one", quote="baseline is recorded."):
    return {"kind": "final", "analysis": "The report records the baseline.",
            "citations": [{"call_id": call_id, "quote": quote}]}


class FixturePort:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.hook = lambda: None

    def infer(self, request, *, cancellation=None):
        self.requests.append(request)
        self.hook()
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        if callable(value):
            return value(request)
        if isinstance(value, InferenceResult):
            return value
        return InferenceResult(
            request.request_id, request.model, "fixture", "completed",
            value if isinstance(value, str) else json.dumps(value),
        )


class Harness:
    def __init__(self, responses=None, context=CONTEXT):
        self.context = context
        self.port = FixturePort(responses if responses is not None else [proposal(), final()])
        self.authorizations = []
        self.executions = []
        self.events = []
        self.allowed = True
        self.now = 0.0
        self.cancel = Event()

    def authorize(self, call):
        self.authorizations.append(call)
        return ToolAuthorization("allow", call_fingerprint(self.context, call))

    def execute(self, call, authorization):
        self.executions.append((call, authorization))
        return ToolObservation(call.call_id, call.tool, call.resource_id,
                               authorization.fingerprint, REPORT)

    def run(self, **kwargs):
        options = {
            "model": "fixture-model", "context": self.context,
            "authorize": self.authorize, "execute": self.execute,
            "eligible": lambda: self.allowed, "emit": lambda n, p: self.events.append((n, p)),
            "clock": lambda: self.now, "cancellation": self.cancel,
        }
        options.update(kwargs)
        return run_tool_loop(self.port, **options)


def assert_discarded(outcome):
    assert outcome.status != "completed"
    assert outcome.observations == ()
    assert outcome.analysis == ""
    assert outcome.citations == ()


def test_complete_loop_returns_verified_quote_and_real_observation_to_model():
    harness = Harness()
    outcome = harness.run()
    assert outcome.status == "completed"
    assert outcome.error_code is None
    assert outcome.evidence_mode == "fixture"
    assert len(outcome.observations) == 1
    assert outcome.citations == (ToolCitation("read-one", "baseline is recorded."),)
    assert len(harness.authorizations) == 2
    assert len(harness.executions) == 1
    assert len(harness.port.requests) == 2
    first, second = [json.loads(r.messages[0].content) for r in harness.port.requests]
    assert first["available_resource_ids"] == ["documentation", "observability"]
    assert first["observations"] == []
    assert second["observations"][0]["text"] == REPORT
    assert "untrusted data" in harness.port.requests[0].instructions
    assert all(0 < request.timeout_seconds <= 30 for request in harness.port.requests)


def test_multiple_tool_results_are_retained_and_cited_by_exact_call_id():
    answer = final()
    answer["citations"].append({"call_id": "read-two", "quote": "signals are logged."})
    harness = Harness([proposal(), proposal("read-two", "observability"), answer])
    outcome = harness.run()
    assert outcome.status == "completed"
    assert len(outcome.observations) == len(outcome.citations) == 2
    assert len(harness.executions) == 2
    assert len(harness.authorizations) == 4


@pytest.mark.parametrize("changed", [
    {"request_id": "request-two"}, {"binding_id": "binding-two"},
    {"query": "Different request"}, {"resource_ids": ("documentation",)},
])
def test_fingerprint_binds_every_context_field(changed):
    call = ToolCall("read-one", "read_local_report", "documentation")
    before = call_fingerprint(CONTEXT, call)
    assert len(before) == 64
    assert before != call_fingerprint(replace(CONTEXT, **changed), call)
    assert before == call_fingerprint(CONTEXT, replace(call))


@pytest.mark.parametrize("changed", [
    {"call_id": "read-two"}, {"tool": "other_tool"}, {"resource_id": "observability"},
])
def test_fingerprint_binds_every_call_field(changed):
    call = ToolCall("read-one", "read_local_report", "documentation")
    assert call_fingerprint(CONTEXT, call) != call_fingerprint(CONTEXT, replace(call, **changed))


def test_public_data_is_frozen_and_repr_hides_prose():
    harness = Harness()
    outcome = harness.run()
    assert REPORT not in repr(outcome)
    assert outcome.analysis not in repr(outcome)
    assert outcome.citations[0].quote not in repr(outcome.citations[0])
    assert CONTEXT.query not in repr(CONTEXT)
    with pytest.raises(FrozenInstanceError):
        outcome.analysis = "changed"
    with pytest.raises(FrozenInstanceError):
        outcome.observations[0].text = "changed"


@pytest.mark.parametrize("message", [
    "not JSON", "```json\n{}\n```", "{} {}", "[]", "null", "true",
    '{"kind":"final","kind":"tool_call"}',
    '{"kind":"tool_call","call_id":"r","tool":"read_local_report",'
    '"arguments":{"resource_id":"documentation","resource_id":"observability"}}',
    '{"kind":"final","analysis":NaN,"citations":[]}',
    '{"kind":"final","analysis":Infinity,"citations":[]}',
    {"kind": []}, {"kind": "other"},
])
def test_malformed_json_or_discriminator_never_reaches_authority(message):
    harness = Harness([message])
    outcome = harness.run()
    assert_discarded(outcome)
    assert outcome.error_code == "invalid_model_message"
    assert harness.authorizations == harness.executions == []


@pytest.mark.parametrize("message", [
    {**proposal(), "extra": "ignored?"},
    {**proposal(), "arguments": {"resource_id": "documentation", "path": "secret"}},
    {**proposal(), "arguments": []},
    proposal(call_id="../escape"), proposal(call_id="ação"),
    proposal(call_id=""), proposal(call_id="a" * 81),
    proposal(resource_id="C:/private/report"), proposal(resource_id=True),
])
def test_invalid_tool_schema_and_ids_fail_before_authorize(message):
    harness = Harness([message])
    outcome = harness.run()
    assert_discarded(outcome)
    assert outcome.error_code == "invalid_tool_message"
    assert harness.authorizations == harness.executions == []


def test_unknown_tool_and_unselected_resource_are_refused_before_authorize():
    for message, reason in [(proposal(tool="exec_command"), "tool_not_allowed"),
                            (proposal(resource_id="private"), "resource_not_selected")]:
        harness = Harness([message])
        outcome = harness.run()
        assert outcome.error_code == reason
        assert harness.authorizations == harness.executions == []
        assert_discarded(outcome)


@pytest.mark.parametrize("decision,reason", [
    ("block", "authorization_blocked"),
    ("defer_for_validation", "authorization_deferred"),
    ("approve", "invalid_authorization"),
])
def test_governance_decisions_are_not_model_errors_or_execution_permission(decision, reason):
    harness = Harness()
    outcome = harness.run(authorize=lambda call: ToolAuthorization(decision, ""))
    assert outcome.status == "refused"
    assert outcome.error_code == reason
    assert harness.executions == []
    assert len(harness.port.requests) == 1
    assert_discarded(outcome)


def test_authorization_is_rechecked_before_execution_and_second_denial_wins():
    harness = Harness()
    decisions = iter(["allow", "block"])
    outcome = harness.run(authorize=lambda call: ToolAuthorization(
        next(decisions), call_fingerprint(CONTEXT, call),
    ))
    assert outcome.error_code == "authorization_blocked"
    assert harness.executions == []


@pytest.mark.parametrize("authorization", [None, True, {"decision": "allow"},
    ToolAuthorization("allow", "0" * 64), ToolAuthorization("allow", True)])
def test_missing_or_foreign_authority_binding_is_refused(authorization):
    harness = Harness()
    outcome = harness.run(authorize=lambda call: authorization)
    assert_discarded(outcome)
    assert harness.executions == []


def test_call_mutation_during_authorization_cannot_reuse_old_grant():
    harness = Harness()

    def authorize(call):
        fingerprint = call_fingerprint(CONTEXT, call)
        object.__setattr__(call, "resource_id", "observability")
        return ToolAuthorization("allow", fingerprint)

    outcome = harness.run(authorize=authorize)
    assert outcome.error_code == "call_binding_changed"
    assert harness.executions == []


def test_context_mutation_during_authorization_is_refused_before_io():
    context = replace(CONTEXT)
    harness = Harness(context=context)

    def authorize(call):
        answer = ToolAuthorization("allow", call_fingerprint(context, call))
        object.__setattr__(context, "binding_id", "replaced-binding")
        return answer

    outcome = harness.run(authorize=authorize)
    assert outcome.error_code == "context_binding_changed"
    assert harness.executions == []


@pytest.mark.parametrize("field,value", [
    ("call_id", "other"), ("tool", "other"), ("resource_id", "observability"),
    ("fingerprint", "0" * 64), ("text", ""), ("text", "x" * 8_193),
    ("text", "\ud800"),
])
def test_observation_is_bound_to_exact_authorized_call(field, value):
    harness = Harness()

    def execute(call, authorization):
        return replace(harness.execute(call, authorization), **{field: value})

    outcome = harness.run(execute=execute)
    assert outcome.error_code == "invalid_observation"
    assert_discarded(outcome)
    assert len(harness.port.requests) == 1


@pytest.mark.parametrize("field,value", [
    ("request_id", "other-request"), ("model", "other-model"),
    ("provider_id", "other-provider"), ("evidence_mode", "live"),
])
def test_result_identity_and_evidence_mode_must_match_request(field, value):
    def response(request):
        result = InferenceResult(request.request_id, request.model, "fixture", "completed",
                                 json.dumps(proposal()))
        return replace(result, **{field: value})

    harness = Harness([response])
    outcome = harness.run()
    assert outcome.error_code == "inference_binding_mismatch"
    assert harness.authorizations == harness.executions == []


@pytest.mark.parametrize("status", ["failed", "cancelled", "timed_out"])
def test_noncompleted_inference_never_creates_observation(status):
    harness = Harness([lambda request: InferenceResult(
        request.request_id, request.model, "fixture", status,
        error_code="private_provider_failure",
    )])
    outcome = harness.run()
    assert outcome.status == status
    assert "private_provider_failure" not in repr(outcome)
    assert harness.authorizations == harness.executions == []


@pytest.mark.parametrize("answer,reason", [
    ({**final(), "extra": "bad"}, "invalid_final_message"),
    ({**final(), "analysis": "x" * 4_001}, "invalid_final_message"),
    ({**final(), "analysis": ""}, "invalid_final_message"),
    ({**final(), "citations": []}, "citation_required"),
    ({**final(), "citations": {}}, "citation_required"),
    (final(call_id="invented"), "citation_not_observed"),
    (final(quote="a fact not present"), "citation_not_exact"),
    (final(quote="Baseline is recorded."), "citation_not_exact"),
    (final(quote="x" * 513), "invalid_citation"),
    (final(quote=""), "invalid_citation"),
    ({**final(), "citations": [{**final()["citations"][0], "path": "bad"}]},
     "invalid_citation"),
    ({**final(), "citations": final()["citations"] * 2}, "duplicate_citation"),
])
def test_final_analysis_requires_bounded_exact_provenance(answer, reason):
    harness = Harness([proposal(), answer])
    outcome = harness.run()
    assert outcome.error_code == reason
    assert_discarded(outcome)
    assert len(harness.executions) == 1


def test_final_without_observation_is_never_a_completed_task():
    harness = Harness([final()])
    outcome = harness.run()
    assert outcome.error_code == "observation_required"
    assert harness.executions == []


def test_duplicate_call_id_never_reexecutes_and_call_budget_has_one_final_step():
    duplicate = Harness([proposal(), proposal()])
    assert duplicate.run().error_code == "reused_call_id"
    assert len(duplicate.executions) == 1
    budget = Harness([proposal("one"), proposal("two"), proposal("three"), proposal("four")])
    outcome = budget.run()
    assert outcome.error_code == "tool_call_limit"
    assert len(budget.port.requests) == 4
    assert len(budget.executions) == 3
    assert_discarded(outcome)


@pytest.mark.parametrize("boundary", ["infer", "authorize", "execute", "final"])
def test_revoked_context_stops_at_each_boundary_and_discards_partial_data(boundary):
    harness = Harness()

    def infer_hook():
        if boundary == "infer" or (boundary == "final" and len(harness.port.requests) == 2):
            harness.allowed = False

    def authorize(call):
        result = harness.authorize(call)
        if boundary == "authorize":
            harness.allowed = False
        return result

    def execute(call, authorization):
        result = harness.execute(call, authorization)
        if boundary == "execute":
            harness.allowed = False
        return result

    harness.port.hook = infer_hook
    outcome = harness.run(authorize=authorize, execute=execute)
    assert outcome.error_code == "context_ineligible"
    assert_discarded(outcome)
    if boundary in {"infer", "authorize"}:
        assert harness.executions == []


@pytest.mark.parametrize("boundary", ["infer", "authorize", "execute", "final"])
def test_cancellation_and_deadline_are_rechecked_after_callbacks(boundary):
    for cancelled in (False, True):
        harness = Harness()

        def stop():
            if cancelled:
                harness.cancel.set()
            else:
                harness.now = 30

        def infer_hook():
            if boundary == "infer" or (boundary == "final" and len(harness.port.requests) == 2):
                stop()

        def authorize(call):
            result = harness.authorize(call)
            if boundary == "authorize":
                stop()
            return result

        def execute(call, authorization):
            result = harness.execute(call, authorization)
            if boundary == "execute":
                stop()
            return result

        harness.port.hook = infer_hook
        outcome = harness.run(authorize=authorize, execute=execute)
        assert outcome.status == ("cancelled" if cancelled else "timed_out")
        assert_discarded(outcome)
        if boundary in {"infer", "authorize"}:
            assert harness.executions == []


def test_global_deadline_is_not_reset_for_each_model_step():
    harness = Harness()
    harness.port.hook = lambda: setattr(harness, "now", harness.now + 4)
    outcome = harness.run(timeout_seconds=7)
    assert outcome.status == "timed_out"
    assert len(harness.port.requests) == 2
    assert harness.port.requests[1].timeout_seconds <= 3
    assert_discarded(outcome)


def test_late_result_from_previous_step_is_refused_before_another_execution():
    harness = Harness()

    class LateResultPort:
        first = None

        def infer(self, request, *, cancellation=None):
            harness.port.requests.append(request)
            if self.first is None:
                self.first = InferenceResult(
                    request.request_id, request.model, "fixture", "completed",
                    json.dumps(proposal()),
                )
            return self.first

    outcome = run_tool_loop(
        LateResultPort(), model="fixture-model", context=CONTEXT,
        authorize=harness.authorize, execute=harness.execute,
        eligible=lambda: True, emit=lambda *_: None, clock=lambda: 0,
    )
    assert outcome.error_code == "inference_binding_mismatch"
    assert len(harness.executions) == 1
    first, second = harness.port.requests
    assert first.request_id != second.request_id
    assert all(len(request.request_id) <= 160 for request in (first, second))
    assert CONTEXT.query not in first.request_id + second.request_id
    assert_discarded(outcome)


def test_step_identity_changes_with_observed_payload_not_just_step_counter():
    first = Harness()
    second = Harness([proposal(), final(quote="different observed evidence")])

    def execute(call, authorization):
        return replace(second.execute(call, authorization), text="different observed evidence")

    assert first.run().status == "completed"
    assert second.run(execute=execute).status == "completed"
    assert first.port.requests[0].request_id == second.port.requests[0].request_id
    assert first.port.requests[1].request_id != second.port.requests[1].request_id


@pytest.mark.parametrize("clock", [lambda: float("nan"), lambda: float("inf"), lambda: True,
    lambda: "time"])
def test_invalid_clock_never_starts_inference(clock):
    harness = Harness()
    assert harness.run(clock=clock).error_code == "invalid_clock"
    assert harness.port.requests == []


def test_backwards_clock_and_nonboolean_eligibility_fail_closed():
    harness = Harness()
    readings = iter([2, 1])
    assert harness.run(clock=lambda: next(readings)).error_code == "invalid_clock"
    assert harness.run(eligible=lambda: "yes").error_code == "context_ineligible"
    assert harness.port.requests == []


@pytest.mark.parametrize("options", [
    {"timeout_seconds": 0}, {"timeout_seconds": 121}, {"timeout_seconds": True},
    {"timeout_seconds": float("nan")}, {"max_tool_calls": 0}, {"max_tool_calls": 4},
    {"max_tool_calls": True}, {"expected_evidence_mode": "unverified"},
    {"model": ""}, {"cancellation": object()},
])
def test_invalid_configuration_does_not_invoke_model(options):
    harness = Harness()
    outcome = harness.run(**options)
    assert outcome.error_code == "invalid_configuration"
    assert harness.port.requests == []
    assert_discarded(outcome)


@pytest.mark.parametrize("boundary", ["infer", "authorize", "execute", "eligible", "emit"])
def test_callback_exceptions_do_not_leak_content(boundary):
    harness = Harness()

    def fail(*args, **kwargs):
        raise RuntimeError("SECRET-CREDENTIAL-AND-PROSE")

    kwargs = {}
    if boundary == "infer":
        harness.port.hook = fail
    else:
        kwargs[boundary] = fail
    outcome = harness.run(**kwargs)
    assert outcome.status == "failed"
    assert "SECRET" not in repr(outcome)
    assert "SECRET" not in json.dumps(harness.events)
    assert_discarded(outcome)


def test_emitted_events_contain_only_metadata_and_no_untrusted_text():
    harness = Harness()
    outcome = harness.run()
    assert outcome.status == "completed"
    wire = json.dumps(harness.events)
    for text in (CONTEXT.query, REPORT, outcome.analysis, outcome.citations[0].quote):
        assert text not in wire
    assert all(name.startswith("model_tool_loop_") for name, _ in harness.events)
    allowed_keys = {"step", "tool_calls", "observation_count", "evidence_mode", "fingerprint",
                    "text_sha256", "status", "citation_count", "error_code"}
    assert all(set(payload) <= allowed_keys for _, payload in harness.events)


def test_failure_after_observation_does_not_return_partial_prose_or_quotes():
    harness = Harness([proposal(), RuntimeError("sensitive")])
    outcome = harness.run()
    assert outcome.error_code == "inference_failed"
    assert_discarded(outcome)
    assert len(harness.executions) == 1


def test_oversized_model_message_and_context_are_bounded():
    harness = Harness(["x" * 8_001])
    assert harness.run().error_code == "invalid_model_message"
    harness = Harness([proposal("one"), proposal("two"), final("two")])

    def execute(call, authorization):
        return replace(harness.execute(call, authorization), text='"' * 8_000)

    outcome = harness.run(execute=execute)
    assert outcome.error_code == "model_context_too_large"
    assert len(harness.port.requests) == 2
    assert_discarded(outcome)


def test_model_and_provider_identifiers_retain_inference_port_compatibility():
    harness = Harness([proposal(), final()])

    class CompatiblePort:
        def infer(self, request, *, cancellation=None):
            return replace(harness.port.infer(request, cancellation=cancellation),
                           provider_id="fixture/provider")

    outcome = run_tool_loop(
        CompatiblePort(), model="fixture/model", context=CONTEXT,
        authorize=harness.authorize, execute=harness.execute,
        eligible=lambda: True, emit=lambda *_: None,
        expected_provider_id="fixture/provider", clock=lambda: 0,
    )
    assert outcome.status == "completed"
