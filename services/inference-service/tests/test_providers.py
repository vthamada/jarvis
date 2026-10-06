"""Unit and injected-transport E2E tests; no auth, HTTP or entitlement claims."""

from threading import Event

import pytest
from inference_service import FakeInferenceProvider, ResponsesPlanInferenceProvider

from shared.model_inference import InferenceMessage, InferenceRequest


def request(**kwargs):
    return InferenceRequest(
        request_id="request-1",
        model="account-model-slug",
        messages=(InferenceMessage("user", "Private request content"),),
        **kwargs,
    )


def response(**kwargs):
    return {"id": "resp_1", "model": "account-model-slug", **kwargs}


def complete(text="Hello", **kwargs):
    return {
        "type": "response.completed",
        "response": response(
            status="completed",
            output=[
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": text},
                    ],
                }
            ],
            **kwargs,
        ),
    }


def provider(events, **kwargs):
    return ResponsesPlanInferenceProvider(lambda *a, **k: iter(events), **kwargs)


def test_payload_to_stream_to_completed_offline_e2e():
    seen = []
    traces = []

    def transport(payload, *, timeout_seconds, cancellation):
        seen.append((payload, timeout_seconds, cancellation))
        yield {"type": "response.created", "response": response(status="in_progress")}
        yield {
            "type": "response.output_item.added",
            "item": {
                "type": "message",
                "role": "assistant",
            },
        }
        yield {"type": "response.output_text.delta", "delta": "Hel"}
        yield {"type": "response.output_text.delta", "delta": "lo"}
        yield {"type": "response.output_text.done", "text": "Hello"}
        yield complete(usage={"input_tokens": 4, "output_tokens": 2})

    token = Event()
    result = ResponsesPlanInferenceProvider(transport, telemetry=traces.append).infer(
        request(instructions="Core-selected instructions"),
        cancellation=token,
    )
    assert result.status == "completed"
    assert result.text == "Hello"
    assert result.evidence_mode == "injected_transport"
    assert (result.input_tokens, result.output_tokens) == (4, 2)
    assert seen == [
        (
            {
                "model": "account-model-slug",
                "input": [
                    {
                        "role": "user",
                        "content": "Private request content",
                    }
                ],
                "store": False,
                "stream": True,
                "instructions": "Core-selected instructions",
            },
            30.0,
            token,
        )
    ]
    assert traces[0]["event_count"] == 6
    assert "Private" not in repr(traces) and "Hello" not in repr(traces)
    assert "account-model-slug" not in repr(traces)


def test_conversation_history_is_explicit_and_no_unsupported_fields():
    seen = []
    req = InferenceRequest(
        "id",
        "account-model-slug",
        (
            InferenceMessage("user", "Question"),
            InferenceMessage("assistant", "Prior answer"),
            InferenceMessage("user", "Follow-up"),
        ),
    )

    def transport(payload, **kwargs):
        seen.append(payload)
        return [complete()]

    assert ResponsesPlanInferenceProvider(transport).infer(req).status == "completed"
    assert set(seen[0]) == {"model", "input", "store", "stream"}
    assert [x["role"] for x in seen[0]["input"]] == ["user", "assistant", "user"]


@pytest.mark.parametrize(
    "events,code",
    [
        ([], "stream_interrupted"),
        (
            [{"type": "response.output_text.delta", "delta": "private partial"}],
            "stream_interrupted",
        ),
        ([None], "malformed_event"),
        ([{"type": 5}], "malformed_event"),
        ([{"type": "response.output_text.delta", "delta": None}], "malformed_delta"),
        ([{"type": "response.created", "response": []}], "malformed_response"),
        ([{"type": "response.created"}], "malformed_response"),
        ([{"type": "response.completed"}], "malformed_completion"),
        ([{"type": "response.incomplete"}], "response_incomplete"),
        ([{"type": "future.unknown"}], "unsupported_event"),
        (
            [{"type": "response.output_item.added", "item": {"type": "function_call"}}],
            "unsupported_output",
        ),
        (
            [{"type": "response.content_part.added", "part": {"type": "refusal"}}],
            "unsupported_output",
        ),
        ([{"type": "response.output_text.done", "text": 5}], "malformed_event"),
        ([{"type": "error", "code": "sk-secret-token", "message": "private"}], "provider_error"),
        ([complete(), complete()], "event_after_terminal"),
        ([{"type": "response.output_text.delta", "delta": "wrong"}, complete()], "output_mismatch"),
        ([complete(" ")], "empty_output"),
    ],
)
def test_failure_is_content_free(events, code):
    traces = []
    result = provider(events, telemetry=traces.append).infer(request())
    assert result.status == "failed"
    assert result.error_code == code
    assert result.text == ""
    assert "private" not in repr(result)
    assert "sk-secret-token" not in repr(traces)


@pytest.mark.parametrize(
    "code",
    [
        "subscription_sharing_usage_limit_exceeded",
        "subscription_sharing_usage_unavailable",
        "subscription_sharing_unsupported_capability",
        "rate_limit_exceeded",
    ],
)
def test_known_error_after_partial_is_normalized_without_partial_or_error_message(code):
    events = [
        {"type": "response.output_text.delta", "delta": "Private partial"},
        {
            "type": "response.failed",
            "response": response(
                status="failed",
                error={
                    "code": code,
                    "message": "Credentials and private context",
                },
            ),
        },
    ]
    traces = []
    result = provider(events, telemetry=traces.append).infer(request())
    assert result.error_code == code
    assert result.text == ""
    assert "Private" not in repr(traces) and "Credentials" not in repr(traces)


@pytest.mark.parametrize(
    "change,code",
    [
        ({"model": "different"}, "model_mismatch"),
        ({"id": "resp_other"}, "response_identity_mismatch"),
        ({"id": None}, "malformed_response"),
        ({"status": "in_progress"}, "malformed_completion"),
        ({"output": None}, "malformed_completion"),
        ({"output": [{"type": "function_call"}]}, "unsupported_output"),
        ({"output": [{"type": "message", "role": "user", "content": []}]}, "unsupported_output"),
        ({"usage": {"input_tokens": True, "output_tokens": 2}}, "malformed_usage"),
        ({"usage": {"input_tokens": -1, "output_tokens": 2}}, "malformed_usage"),
        ({"usage": {"input_tokens": 2}}, "malformed_usage"),
        ({"usage": []}, "malformed_usage"),
        ({"usage": {"input_tokens": 10**40, "output_tokens": 2}}, "malformed_usage"),
    ],
)
def test_terminal_shape_identity_and_usage_checked(change, code):
    terminal = complete()
    terminal["response"].update(change)
    result = provider(
        [
            {"type": "response.created", "response": response(status="in_progress")},
            terminal,
        ]
    ).infer(request())
    assert result.error_code == code
    assert result.text == ""


def test_explicit_stream_identity_cannot_change_at_terminal():
    result = provider(
        [
            {
                "type": "response.output_text.delta",
                "delta": "Hello",
                "response_id": "resp_other",
            },
            complete(),
        ]
    ).infer(request())
    assert result.error_code == "response_identity_mismatch"


@pytest.mark.parametrize(
    "events,kwargs",
    [
        ([{"type": "response.output_text.delta", "delta": "x" * 10}], {}),
        ([complete("x" * 10)], {}),
        ([{"type": "response.output_text.done", "text": "x" * 10}], {}),
    ],
)
def test_output_limit_is_local_not_sent_as_unsupported_field(events, kwargs):
    result = provider(events, **kwargs).infer(request(max_output_chars=5))
    assert result.error_code == "output_limit_exceeded" and result.text == ""


def test_event_and_byte_limits_stop_unbounded_streams():
    event = {"type": "response.reasoning_summary_text.delta", "delta": "x"}
    assert provider([event] * 4, max_events=3).infer(request()).error_code == "event_limit_exceeded"
    assert (
        provider([event], max_event_bytes=2).infer(request()).error_code == "stream_limit_exceeded"
    )
    assert provider([event] * 4, max_stream_bytes=100).infer(request()).error_code == (
        "stream_limit_exceeded"
    )


def test_non_json_events_are_rejected_without_exception_contents():
    result = provider([{"type": "response.created", "extra": object()}]).infer(request())
    assert result.error_code == "malformed_event"


def test_cancellation_before_transport_never_calls_it():
    token = Event()
    token.set()

    def transport(*args, **kwargs):
        pytest.fail("Cancelled requests must not reach transport")

    result = ResponsesPlanInferenceProvider(transport).infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""


def test_cancellation_during_stream_closes_generator_without_partial():
    token = Event()
    closed = []

    def transport(*args, **kwargs):
        try:
            yield {"type": "response.output_text.delta", "delta": "Private partial"}
            token.set()
            yield complete()
        finally:
            closed.append(True)

    result = ResponsesPlanInferenceProvider(transport).infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""
    assert closed == [True]


def test_cooperative_timeout_after_yield_discards_text():
    instant = [0.0]

    def transport(*args, **kwargs):
        yield {"type": "response.output_text.delta", "delta": "Partial"}
        instant[0] = 2
        yield complete()

    result = ResponsesPlanInferenceProvider(transport, clock=lambda: instant[0]).infer(
        request(timeout_seconds=1),
    )
    assert result.status == "timed_out" and result.text == ""


@pytest.mark.parametrize(
    "exception,code,status",
    [
        (RuntimeError("sk-secret Private prompt"), "transport_error", "failed"),
        (TimeoutError("sk-secret"), "timeout", "timed_out"),
    ],
)
def test_transport_exceptions_are_redacted(exception, code, status):
    traces = []

    def transport(*args, **kwargs):
        yield {"type": "response.output_text.delta", "delta": "Partial"}
        raise exception

    result = ResponsesPlanInferenceProvider(transport, telemetry=traces.append).infer(request())
    assert result.status == status and result.error_code == code
    assert result.text == ""
    assert "sk-secret" not in repr(traces)


def test_exception_after_completed_is_not_published_as_success():
    def transport(*args, **kwargs):
        yield complete()
        raise RuntimeError("Interrupted stream")

    assert ResponsesPlanInferenceProvider(transport).infer(request()).status == "failed"


def test_transport_setup_timeout_and_invalid_clock():
    def transport(*args, **kwargs):
        raise TimeoutError()

    assert ResponsesPlanInferenceProvider(transport).infer(request()).status == "timed_out"
    assert provider([], clock=lambda: float("nan")).infer(request()).error_code == "invalid_clock"


def test_telemetry_failure_cannot_change_completed_inference():
    def telemetry(event):
        raise RuntimeError("private telemetry contents")

    assert provider([complete()], telemetry=telemetry).infer(request()).status == "completed"


@pytest.mark.parametrize(
    "change,code",
    [
        ({"error": {"code": "private", "message": "secret"}}, "malformed_completion"),
        ({"incomplete_details": {"reason": "max_output_tokens"}}, "malformed_completion"),
        ({"usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 99}}, "malformed_usage"),
        (
            {"usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": True}},
            "malformed_usage",
        ),
    ],
)
def test_completion_cannot_conflict_with_errors_or_usage(change, code):
    event = complete()
    event["response"].update(change)
    assert provider([event]).infer(request()).error_code == code


def test_completed_response_requires_completed_message_when_status_present():
    event = complete()
    event["response"]["output"][0]["status"] = "in_progress"
    assert provider([event]).infer(request()).error_code == "malformed_completion"


def test_valid_total_usage_and_reasoning_are_supported():
    event = complete(usage={"input_tokens": 1, "output_tokens": 2, "total_tokens": 3})
    event["response"]["output"].insert(0, {"type": "reasoning", "summary": []})
    assert provider([event]).infer(request()).status == "completed"


def test_backward_clock_is_not_allowed_to_extend_deadline():
    times = iter([2.0, 1.0])
    result = provider([], clock=lambda: next(times)).infer(request())
    assert result.error_code == "invalid_clock"


def test_transport_creation_exception_is_content_free():
    def transport(*args, **kwargs):
        raise RuntimeError("private access token")

    result = ResponsesPlanInferenceProvider(transport).infer(request())
    assert result.error_code == "transport_error"
    assert result.text == ""


def test_close_failure_is_redacted_and_preserves_existing_result():
    class CloseFailure:
        def __init__(self):
            self.events = iter([complete()])

        def __iter__(self):
            return self

        def __next__(self):
            return next(self.events)

        @property
        def close(self):
            raise RuntimeError("private cleanup failure")

    result = ResponsesPlanInferenceProvider(lambda *a, **k: CloseFailure()).infer(request())
    assert result.status == "completed"


@pytest.mark.parametrize(
    "event,code",
    [
        ({"type": "response.output_text.done", "text": "Different"}, "output_mismatch"),
        (
            {"type": "response.output_item.added", "item": {"type": "message", "role": "user"}},
            "unsupported_output",
        ),
        (
            {"type": "response.content_part.done", "part": {"type": "output_text", "text": None}},
            "unsupported_output",
        ),
        ({"type": "response.reasoning_summary_text.delta", "delta": {}}, "malformed_event"),
        ({"type": "response.reasoning_summary_text.done", "text": None}, "malformed_event"),
        (
            {"type": "response.reasoning_summary_part.added", "part": {"type": "summary_text"}},
            "malformed_event",
        ),
        (
            {
                "type": "response.content_part.done",
                "part": {"type": "output_text", "text": "Wrong"},
            },
            "output_mismatch",
        ),
        (
            {
                "type": "response.output_item.done",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "status": "in_progress",
                },
            },
            "malformed_event",
        ),
        (
            {"type": "response.output_text.delta", "delta": "Hello", "output_index": True},
            "malformed_event",
        ),
        (
            {
                "type": "response.output_item.done",
                "item": {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Different",
                        }
                    ],
                },
            },
            "output_mismatch",
        ),
    ],
)
def test_cross_review_malformed_intermediate_events_cannot_be_false_success(event, code):
    result = provider([event, complete()]).infer(request())
    assert result.status == "failed" and result.text == ""
    assert result.error_code == code


def test_text_cannot_continue_after_done():
    events = [
        {"type": "response.output_text.done", "text": "Hello"},
        {"type": "response.output_text.delta", "delta": "Hello"},
        complete(),
    ]
    assert provider(events).infer(request()).error_code == "text_after_done"


def test_done_text_must_match_observed_deltas():
    events = [
        {"type": "response.output_text.delta", "delta": "Hello"},
        {"type": "response.output_text.done", "text": "Wrong"},
        complete(),
    ]
    assert provider(events).infer(request()).error_code == "output_mismatch"


def test_realistic_reasoning_and_text_event_sequence_is_validated():
    part = {"type": "output_text", "text": "Hello"}
    events = [
        {"type": "response.created", "response": response(status="in_progress")},
        {
            "type": "response.reasoning_summary_part.added",
            "part": {
                "type": "summary_text",
                "text": "",
            },
        },
        {"type": "response.reasoning_summary_text.delta", "delta": "Thinking"},
        {"type": "response.reasoning_summary_text.done", "text": "Thinking"},
        {
            "type": "response.reasoning_summary_part.done",
            "part": {
                "type": "summary_text",
                "text": "Thinking",
            },
        },
        {"type": "response.output_item.done", "item": {"type": "reasoning", "summary": []}},
        {
            "type": "response.output_item.added",
            "item": {
                "type": "message",
                "role": "assistant",
                "status": "in_progress",
                "content": [],
            },
        },
        {"type": "response.content_part.added", "part": {"type": "output_text", "text": ""}},
        {"type": "response.output_text.delta", "delta": "Hello", "output_index": 1},
        {"type": "response.output_text.done", "text": "Hello"},
        {"type": "response.content_part.done", "part": part},
        {
            "type": "response.output_item.done",
            "item": {
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [part],
            },
        },
        complete(),
    ]
    result = provider(events).infer(request())
    assert result.status == "completed" and result.text == "Hello"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_events": True},
        {"max_events": 0},
        {"max_events": 10001},
        {"max_event_bytes": 0},
        {"max_stream_bytes": -1},
        {"telemetry": "not callable"},
    ],
)
def test_configuration_limits(kwargs):
    with pytest.raises(ValueError):
        provider([], **kwargs)


def test_fake_is_deterministic_fixture_and_does_not_echo_private_context():
    fake = FakeInferenceProvider()
    result = fake.infer(request())
    assert result == fake.infer(request())
    assert result.evidence_mode == "fixture"
    assert "Private" not in result.text
    assert fake.infer(request(max_output_chars=1)).error_code == "output_limit_exceeded"
    token = Event()
    token.set()
    assert fake.infer(request(), cancellation=token).status == "cancelled"


@pytest.mark.parametrize(
    "text", ["", " ", None, "x" * 64001], ids=["empty", "blank", "wrong_type", "oversized"]
)
def test_fixture_config_validation(text):
    with pytest.raises(ValueError):
        FakeInferenceProvider(text)
