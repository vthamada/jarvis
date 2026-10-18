"""Independent text-port contract and local endpoint policy; no network/model."""

from __future__ import annotations

import json
from dataclasses import replace
from threading import Event

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider
from inference_service.local_chat_transport import LocalChatHttpTransport, LocalChatTransportError

from shared.model_inference import InferenceMessage, InferenceRequest

MODEL = "selected-local-model:quantized"


def request(**kwargs):
    return InferenceRequest(request_id="local-request", model=MODEL,
                            messages=(InferenceMessage("user", "Compare public reports."),),
                            **kwargs)


def completion(**kwargs):
    value = {"id": "chatcmpl-fixture", "object": "chat.completion", "model": MODEL,
             "choices": [{"index": 0, "finish_reason": "stop",
                          "message": {"role": "assistant", "content": "Text is data only."}}],
             "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
    value.update(kwargs)
    return value


class FixtureTransport:
    def __init__(self, response=None, *, raw=None, after=None):
        self.response = completion() if response is None else response
        self.raw = raw
        self.after = after
        self.calls = []

    def __call__(self, payload, **kwargs):
        self.calls.append((payload, kwargs))
        if self.after:
            self.after()
        return self.raw if self.raw is not None else json.dumps(self.response).encode("utf-8")


def provider(transport=None, **kwargs):
    return ChatCompletionsInferenceProvider(model=MODEL, transport=transport or FixtureTransport(),
                                           **kwargs)


def test_text_contract_serializes_system_and_history_without_grants_or_tools():
    fixture = FixtureTransport()
    selected = replace(request(instructions="Keep sources separate."), messages=(
        InferenceMessage("user", "A"), InferenceMessage("assistant", "B"),
        InferenceMessage("user", "C"),
    ))
    result = provider(fixture, evidence_mode="fixture").infer(selected)
    assert result.status == "completed"
    assert result.text == "Text is data only."
    assert result.provider_id == "chat_completions_local"
    assert result.evidence_mode == "fixture"
    assert (result.request_id, result.model) == (selected.request_id, MODEL)
    assert (result.input_tokens, result.output_tokens) == (10, 5)
    payload, options = fixture.calls[0]
    assert payload == {"model": MODEL, "n": 1, "stream": False, "messages": [
        {"role": "system", "content": "Keep sources separate."},
        {"role": "user", "content": "A"}, {"role": "assistant", "content": "B"},
        {"role": "user", "content": "C"},
    ]}
    assert 0 < options["timeout_seconds"] <= selected.timeout_seconds
    assert isinstance(options["cancellation"], Event)
    assert len(fixture.calls) == 1


@pytest.mark.parametrize("endpoint", [
    "http://localhost:11434/v1/chat/completions", "https://127.0.0.1:11434/v1/chat/completions",
    "http://192.168.1.1:80/v1/chat/completions", "http://169.254.169.254:80/v1/chat/completions",
    "http://0.0.0.0:80/v1/chat/completions", "http://[::]:80/v1/chat/completions",
    "http://[::ffff:127.0.0.1]:80/v1/chat/completions",
    "http://127.1:80/v1/chat/completions", "http://2130706433:80/v1/chat/completions",
    "http://127.0.0.1/v1/chat/completions", "http://127.0.0.1:0/v1/chat/completions",
    "http://127.0.0.1:65536/v1/chat/completions", "http://u:p@127.0.0.1:80/v1/chat/completions",
    "http://127.0.0.1:80/v1/chat/completions?", "http://127.0.0.1:80/v1/chat/completions#",
    "http://127.0.0.1:80/v1/chat/completions?next=x", "http://127.0.0.1:80/v1/%63hat/completions",
    "http://127.0.0.1:80//v1/chat/completions", "http://127.0.0.1:80/v1/chat/completions/",
    "http://127.0.0.1:80/v1/../v1/chat/completions", " http://127.0.0.1:80/v1/chat/completions",
    "http://127.0.0.1:80/v1/chat/completions\r\nX: y", "http://127.0.0.1:80/v1/responses",
])
def test_endpoint_refuses_dns_network_redirect_surfaces_credentials_and_ambiguity(endpoint):
    with pytest.raises(ValueError, match="^invalid_local_chat_endpoint$"):
        LocalChatHttpTransport(endpoint=endpoint)


@pytest.mark.parametrize("endpoint", ["http://127.0.0.1:11434/v1/chat/completions",
                                     "http://[::1]:1234/v1/chat/completions"])
def test_construction_is_inert_and_has_no_credential_repr(endpoint):
    selected = LocalChatHttpTransport(endpoint=endpoint)
    assert endpoint not in repr(selected)
    configured = provider(selected, evidence_mode="live")
    assert configured.provider_id == "chat_completions_local"


@pytest.mark.parametrize("mode", ["live", "model_real", "", None])
def test_injected_transport_cannot_claim_live(mode):
    with pytest.raises(ValueError, match="^invalid_chat_evidence_mode$"):
        provider(evidence_mode=mode)


@pytest.mark.parametrize("mode", ["fixture", "injected_transport"])
def test_real_transport_cannot_masquerade_as_fixture(mode):
    transport = LocalChatHttpTransport(endpoint="http://127.0.0.1:11434/v1/chat/completions")
    with pytest.raises(ValueError, match="^invalid_chat_evidence_mode$"):
        provider(transport, evidence_mode=mode)


@pytest.mark.parametrize("change,error", [
    ({"model": "different-model"}, "model_mismatch"),
    ({"object": "chat.completion.chunk"}, "malformed_completion"),
    ({"id": ""}, "malformed_completion"), ({"status": "in_progress"}, "malformed_completion"),
    ({"error": {"message": "PRIVATE_ERROR"}}, "malformed_completion"),
    ({"choices": []}, "malformed_completion"),
    ({"choices": [{"index": True}]}, "malformed_completion"),
])
def test_invalid_completion_never_publishes_text(change, error):
    fixture = FixtureTransport(completion(**change))
    result = provider(fixture).infer(request())
    assert (result.status, result.error_code, result.text) == ("failed", error, "")
    assert len(fixture.calls) == 1
    assert "PRIVATE_ERROR" not in repr(result)


@pytest.mark.parametrize("reason", [None, "length", "tool_calls", "function_call",
                                    "content_filter"])
def test_nonterminal_or_truncated_output_is_never_published(reason):
    value = completion()
    value["choices"][0]["finish_reason"] = reason
    result = provider(FixtureTransport(value)).infer(request())
    assert (result.error_code, result.text) == ("response_incomplete", "")


@pytest.mark.parametrize("message,error", [
    ({"role": "user", "content": "x"}, "unsupported_output"),
    ({"role": "assistant", "content": None}, "empty_output"),
    ({"role": "assistant", "content": " "}, "empty_output"),
    ({"role": "assistant", "content": [{"text": "x"}]}, "empty_output"),
    ({"role": "assistant", "content": "x", "tool_calls": []}, "unsupported_output"),
    ({"role": "assistant", "content": "x", "function_call": None}, "unsupported_output"),
    ({"role": "assistant", "content": "x", "refusal": "no"}, "unsupported_output"),
    ({"role": "assistant", "content": "x", "audio": {}}, "unsupported_output"),
    ({"role": "assistant", "content": "x\x00y"}, "unsupported_output"),
    ({"role": "assistant", "content": "\ud800"}, "unsupported_output"),
])
def test_only_complete_utf8_assistant_text_is_accepted(message, error):
    value = completion()
    value["choices"][0]["message"] = message
    result = provider(FixtureTransport(value)).infer(request())
    assert (result.error_code, result.text) == (error, "")


@pytest.mark.parametrize("usage", [[], {}, {"prompt_tokens": 1},
    {"prompt_tokens": True, "completion_tokens": 1, "total_tokens": 2},
    {"prompt_tokens": -1, "completion_tokens": 1, "total_tokens": 0},
    {"prompt_tokens": 1.0, "completion_tokens": 1, "total_tokens": 2},
    {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 3},
    {"prompt_tokens": 2**40, "completion_tokens": 1, "total_tokens": 2**40 + 1},
])
def test_usage_is_optional_but_if_present_must_be_consistent_bounded_integers(usage):
    result = provider(FixtureTransport(completion(usage=usage))).infer(request())
    assert (result.error_code, result.text) == ("malformed_usage", "")


def test_absent_usage_is_not_fabricated():
    value = completion()
    del value["usage"]
    result = provider(FixtureTransport(value)).infer(request())
    assert result.status == "completed"
    assert result.input_tokens is result.output_tokens is None


@pytest.mark.parametrize("raw", [b"{}{}", b"\xff", b'{"a":1,"a":2}',
    b'{"unused":NaN}', b'{"unused":Infinity}', b'{"unused":1e999}',
    b"{" * 1100, b"[]", b"null"])
def test_malformed_duplicate_nonfinite_recursive_or_wrong_root_json_is_withheld(raw):
    result = provider(FixtureTransport(raw=raw)).infer(request())
    assert result.status == "failed" and result.text == ""


def test_model_mismatch_and_precancel_do_no_io():
    fixture = FixtureTransport()
    selected = provider(fixture)
    result = selected.infer(replace(request(), model="another"))
    assert result.error_code == "model_mismatch"
    token = Event()
    token.set()
    result = selected.infer(request(), cancellation=token)
    assert result.status == "cancelled"
    assert fixture.calls == []


def test_cancel_after_transport_and_after_telemetry_withholds_text():
    token = Event()
    result = provider(FixtureTransport(after=token.set)).infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""
    token.clear()
    result = provider(telemetry=lambda _value: token.set()).infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""


@pytest.mark.parametrize("clock_values,error", [([float("nan")], "invalid_clock"),
    ([0, -1], "invalid_clock"), ([0, float("inf")], "invalid_clock"),
    ([0, 0, 0, 31], "timeout"), ([True], "invalid_clock")])
def test_invalid_regressing_or_expired_clock_is_fail_closed(clock_values, error):
    values = iter(clock_values)
    last = clock_values[-1]
    result = provider(clock=lambda: next(values, last)).infer(request())
    assert result.error_code == error and result.text == ""


def test_limits_and_failure_exception_text_do_not_escape():
    result = provider(max_response_bytes=10).infer(request())
    assert result.error_code == "response_limit_exceeded"
    result = provider().infer(request(max_output_chars=1))
    assert result.error_code == "output_limit_exceeded"
    def fail(*_args, **_kwargs):
        raise RuntimeError("PRIVATE_SECRET_AND_PROMPT")
    result = provider(fail).infer(request())
    assert result.error_code == "transport_error"
    assert "PRIVATE_SECRET" not in repr(result)


def test_transport_errors_are_normalized_and_no_retries_occur():
    calls = []
    def fail(*_args, **_kwargs):
        calls.append(1)
        raise LocalChatTransportError("PRIVATE_SECRET")
    result = provider(fail).infer(request())
    assert result.error_code == "transport_error" and result.text == ""
    assert calls == [1]


@pytest.mark.parametrize("values", [[0, 0, 0, 0, 31], [0, 0, 0, 0, 0, 31],
                                   [0, 0, 0, 0, 0, 0, 31]])
def test_deadline_covers_parsing_validation_and_publication(values):
    ticks = iter(values)
    result = provider(clock=lambda: next(ticks, values[-1])).infer(request())
    assert result.status == "timed_out" and result.text == ""


def test_telemetry_is_content_free_and_its_failure_does_not_publish_new_authority():
    captured = []
    def record(value):
        captured.append(value)
        raise RuntimeError("observability unavailable")
    result = provider(telemetry=record).infer(request())
    assert result.status == "completed"
    assert captured == [{"event": "inference_finished", "provider_id": "chat_completions_local",
                         "status": "completed", "error_code": None,
                         "evidence_mode": "injected_transport", "input_tokens": 10,
                         "output_tokens": 5}]
    assert "Text is data only." not in repr(captured)


@pytest.mark.parametrize("limit", [True, 0, -1, 2_097_153, 1.5])
def test_provider_and_transport_limits_are_validated_before_io(limit):
    with pytest.raises(ValueError, match="invalid_chat_response_limit"):
        provider(max_response_bytes=limit)
    with pytest.raises(ValueError, match="invalid_local_chat_limit"):
        LocalChatHttpTransport(endpoint="http://127.0.0.1:11434/v1/chat/completions",
                               max_response_bytes=limit)


@pytest.mark.parametrize("field,value", [
    ("request_id", "invalid request"), ("model", ""), ("messages", []),
    ("messages", (object(),)), ("instructions", None), ("instructions", "\ud800"),
    ("instructions", "private\x00instruction"), ("timeout_seconds", float("nan")),
    ("timeout_seconds", True), ("max_output_chars", 0),
])
def test_forged_frozen_requests_are_revalidated_before_any_transport(field, value):
    fixture = FixtureTransport()
    selected = request()
    object.__setattr__(selected, field, value)
    with pytest.raises(ValueError, match="^invalid_inference_request$"):
        provider(fixture).infer(selected)
    assert fixture.calls == []


@pytest.mark.parametrize("field,value", [
    ("role", "system"), ("role", None), ("content", ""), ("content", "x" * 32_001),
    ("content", "\ud800"), ("content", "private\x00text"),
])
def test_forged_frozen_messages_are_copied_and_revalidated_before_io(field, value):
    fixture = FixtureTransport()
    selected = request()
    object.__setattr__(selected.messages[0], field, value)
    with pytest.raises(ValueError, match="^invalid_inference_request$"):
        provider(fixture).infer(selected)
    assert fixture.calls == []


@pytest.mark.parametrize("phase", ["transport", "telemetry"])
@pytest.mark.parametrize("field,value", [
    ("request_id", "changed-id"), ("model", "changed-model"),
    ("instructions", "Changed instructions"), ("timeout_seconds", 120),
    ("max_output_chars", 1), ("messages", (InferenceMessage("user", "Changed query"),)),
])
def test_request_drift_is_withheld_and_result_retains_original_binding(phase, field, value):
    selected = request()
    original = (selected.request_id, selected.model)
    def mutate():
        object.__setattr__(selected, field, value)
    fixture = FixtureTransport(after=mutate if phase == "transport" else None)
    port = provider(fixture, telemetry=(lambda _value: mutate()) if phase == "telemetry" else None)
    result = port.infer(selected)
    assert (result.status, result.error_code, result.text) == ("failed", "request_changed", "")
    assert (result.request_id, result.model) == original
    assert result.provider_id == "chat_completions_local"
    assert result.evidence_mode == "injected_transport"
    assert len(fixture.calls) == 1


@pytest.mark.parametrize("phase", ["transport", "telemetry"])
def test_nested_message_drift_is_detected_without_aliasing_frozen_original(phase):
    selected = request()
    def mutate():
        object.__setattr__(selected.messages[0], "content", "Changed nested message")
    fixture = FixtureTransport(after=mutate if phase == "transport" else None)
    result = provider(fixture, telemetry=(lambda _value: mutate())
                      if phase == "telemetry" else None).infer(selected)
    assert result.error_code == "request_changed" and result.text == ""
    assert len(fixture.calls) == 1


@pytest.mark.parametrize("phase", ["transport", "telemetry"])
@pytest.mark.parametrize("field", ["_model", "provider_id", "_evidence_mode", "_transport",
                                   "_clock", "_telemetry", "_max_response"])
def test_provider_configuration_cannot_drift_or_forge_binding_during_callbacks(phase, field):
    replacement_calls = []
    def replacement_transport(*_args, **_kwargs):
        replacement_calls.append(1)
        return json.dumps(completion()).encode("utf-8")
    changes = {"_model": "changed-model", "provider_id": "changed-provider",
               "_evidence_mode": "live", "_transport": replacement_transport,
               "_clock": lambda: 0, "_telemetry": lambda _event: None,
               "_max_response": 2_097_152}
    def mutate():
        setattr(port, field, changes[field])
    fixture = FixtureTransport(after=mutate if phase == "transport" else None)
    port = provider(fixture, telemetry=(lambda _value: mutate()) if phase == "telemetry" else None)
    result = port.infer(request())
    assert (result.status, result.error_code, result.text) == (
        "failed", "configuration_changed", "",
    )
    assert (result.model, result.provider_id, result.evidence_mode) == (
        MODEL, "chat_completions_local", "injected_transport",
    )
    assert len(fixture.calls) == 1 and replacement_calls == []


def test_response_and_provider_model_cannot_be_changed_together_to_publish_wrong_model():
    """Regression: old code accepted changed _model while Result.model stayed original."""
    response = completion()
    def mutate():
        port._model = "different-real-model"
        response["model"] = "different-real-model"
        response["choices"][0]["message"]["content"] = "WRONG_MODEL_TEXT"
    fixture = FixtureTransport(response, after=mutate)
    port = provider(fixture)
    result = port.infer(request())
    assert (result.status, result.error_code, result.text) == (
        "failed", "configuration_changed", "",
    )
    assert result.model == MODEL and "WRONG_MODEL_TEXT" not in repr(result)
    assert len(fixture.calls) == 1


@pytest.mark.parametrize("field,value", [("_model", "changed-model"),
    ("provider_id", "changed-provider"), ("_evidence_mode", "live"),
    ("_transport", lambda *_args, **_kwargs: b"private")])
def test_configuration_changed_before_inference_is_refused_before_transport(field, value):
    fixture = FixtureTransport()
    port = provider(fixture)
    setattr(port, field, value)
    result = port.infer(request())
    assert result.error_code == "configuration_changed" and result.text == ""
    assert fixture.calls == []


def test_transport_cannot_mutate_model_or_query_in_payload_without_refusal():
    def mutate_payload(payload, **_kwargs):
        payload["messages"][0]["content"] = "DIFFERENT_QUERY"
        return json.dumps(completion()).encode("utf-8")
    result = provider(mutate_payload).infer(request())
    assert result.error_code == "request_changed" and result.text == ""


@pytest.mark.parametrize("clock_value", [1e308, -1e308, 10**400])
def test_clock_deadline_overflow_or_nonadvancing_float_is_refused_before_io(clock_value):
    fixture = FixtureTransport()
    result = provider(fixture, clock=lambda: clock_value).infer(request())
    assert result.error_code == "invalid_clock" and result.text == ""
    assert fixture.calls == []


def test_clock_callback_mutation_is_fenced_before_transport():
    def clock():
        port._evidence_mode = "live"
        return 0
    fixture = FixtureTransport()
    port = provider(fixture, clock=clock)
    result = port.infer(request())
    assert result.error_code == "configuration_changed" and result.text == ""
    assert result.evidence_mode == "injected_transport" and fixture.calls == []


def test_clock_callback_cancellation_is_rechecked_before_transport():
    token = Event()
    ticks = []
    def clock():
        ticks.append(1)
        if len(ticks) == 3:  # Invocation immediately before the injected transport.
            token.set()
        return 0
    fixture = FixtureTransport()
    result = provider(fixture, clock=clock).infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""
    assert fixture.calls == []


@pytest.mark.parametrize("field,value", [("_host", "192.0.2.1"), ("_port", 1),
    ("_authority", "192.0.2.1:1"), ("_max_response", 2_097_152), ("_clock", lambda: 0)])
def test_transport_configuration_is_not_a_mutable_endpoint_policy_bypass(field, value):
    transport = LocalChatHttpTransport(endpoint="http://127.0.0.1:11434/v1/chat/completions")
    setattr(transport, field, value)
    with pytest.raises(LocalChatTransportError, match="^configuration_changed$"):
        transport({}, timeout_seconds=1, cancellation=Event())


@pytest.mark.parametrize("clock_value", [1e308, -1e308, 10**400])
def test_transport_rejects_unrepresentable_deadlines_before_io(clock_value):
    transport = LocalChatHttpTransport(endpoint="http://127.0.0.1:11434/v1/chat/completions",
                                       clock=lambda: clock_value)
    with pytest.raises(LocalChatTransportError, match="^invalid_clock$"):
        transport({}, timeout_seconds=1, cancellation=Event())
