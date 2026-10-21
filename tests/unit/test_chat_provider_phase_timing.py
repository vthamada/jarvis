"""Provider parse diagnostics remain content-free and cannot publish late text."""

from __future__ import annotations

import json
from threading import Event

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider

from shared.model_inference import InferenceMessage, InferenceRequest

MODEL = "private-model"


def _request():
    return InferenceRequest(request_id="PRIVATE_REQUEST", model=MODEL,
                            messages=(InferenceMessage("user", "PRIVATE_PROMPT"),))


def _completion():
    return json.dumps({
        "id": "private-completion-id", "object": "chat.completion", "model": MODEL,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": "PRIVATE_RESPONSE"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }).encode("utf-8")


def test_parse_phase_is_opt_in_content_free_and_separate_from_existing_terminal_telemetry():
    ticks = [0.0]
    events, telemetry = [], []

    def fixture(_payload, **_options):
        ticks[0] = 2.0
        return _completion()

    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=fixture, clock=lambda: ticks[0],
        phase_observer=events.append, telemetry=telemetry.append,
    )
    result = provider.infer(_request())
    assert result.status == "completed" and result.text == "PRIVATE_RESPONSE"
    assert events == [{"event": "local_inference_phase", "phase": "provider_parse_complete",
                       "elapsed_ms": 2000, "timing_mode": "injected_clock"}]
    assert len(telemetry) == 1 and telemetry[0]["event"] == "inference_finished"
    assert "PRIVATE" not in repr(events)


@pytest.mark.parametrize("action,code,status", [
    ("cancel", "cancelled", "cancelled"), ("deadline", "timeout", "timed_out"),
    ("configuration", "configuration_changed", "failed"),
    ("observer", "configuration_changed", "failed"),
    ("request", "request_changed", "failed"),
    ("payload", "request_changed", "failed"),
])
def test_parse_observer_mutations_and_late_revocations_withhold_text(action, code, status):
    selected, token = _request(), Event()
    ticks, payloads, events, telemetry = [0.0], [], [], []

    def fixture(payload, **_options):
        payloads.append(payload)
        ticks[0] = 2.0
        return _completion()

    def observe(event):
        events.append(event)
        if action == "cancel":
            token.set()
        elif action == "deadline":
            ticks[0] = selected.timeout_seconds
        elif action == "configuration":
            provider._model = "different-model"
        elif action == "observer":
            provider._phase_observer = None
        elif action == "request":
            object.__setattr__(selected.messages[0], "content", "different-prompt")
        else:
            payloads[0]["messages"][0]["content"] = "different-prompt"
        raise RuntimeError("PRIVATE_OBSERVER_EXCEPTION")

    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=fixture, clock=lambda: ticks[0],
        phase_observer=observe, telemetry=telemetry.append,
    )
    result = provider.infer(selected, cancellation=token)
    assert (result.status, result.error_code, result.text) == (status, code, "")
    assert len(events) == 1
    assert len(telemetry) == 1 and telemetry[0]["status"] == status


def test_provider_ordinary_phase_observer_exception_is_isolated():
    def observe(_event):
        raise RuntimeError("PRIVATE_OBSERVER_EXCEPTION")

    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=lambda _payload, **_options: _completion(), phase_observer=observe,
    )
    result = provider.infer(_request())
    assert result.status == "completed" and result.text == "PRIVATE_RESPONSE"


def test_live_timing_clock_does_not_promote_injected_transport_to_live_model_evidence():
    events = []
    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=lambda _payload, **_options: _completion(),
        phase_observer=events.append,
    )
    result = provider.infer(_request())
    assert result.status == "completed" and result.evidence_mode == "injected_transport"
    assert len(events) == 1 and events[0]["timing_mode"] == "live"
    assert type(events[0]["elapsed_ms"]) is int and 0 <= events[0]["elapsed_ms"] <= 120_000


def test_phase_timing_origin_resets_on_each_provider_operation():
    ticks, events = [0.0], []

    def fixture(_payload, **_options):
        ticks[0] += 2.0
        return _completion()

    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=fixture, clock=lambda: ticks[0], phase_observer=events.append,
    )
    for start in (0.0, 10.0):
        ticks[0] = start
        assert provider.infer(_request()).status == "completed"
    assert [event["elapsed_ms"] for event in events] == [2000, 2000]


@pytest.mark.parametrize("raw", [b"PRIVATE_INVALID_JSON", b'{}'])
def test_malformed_response_never_emits_parse_complete(raw):
    events = []
    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=lambda _payload, **_options: raw, phase_observer=events.append,
    )
    result = provider.infer(_request())
    assert result.status == "failed" and result.text == ""
    assert events == []


@pytest.mark.parametrize("observer", [False, 1, "callback", object()])
def test_invalid_provider_phase_observer_is_refused_at_inert_construction(observer):
    with pytest.raises(ValueError, match="^invalid_chat_phase_observer$"):
        ChatCompletionsInferenceProvider(
            model=MODEL, transport=lambda _payload, **_options: _completion(),
            phase_observer=observer,
        )


def test_provider_phase_observer_rebinding_before_infer_is_refused_before_transport():
    def forbidden_transport(*_args, **_options):
        pytest.fail("configuration change reached transport")

    provider = ChatCompletionsInferenceProvider(
        model=MODEL, transport=forbidden_transport, phase_observer=lambda _event: None,
    )
    provider._phase_observer = None
    result = provider.infer(_request())
    assert (result.status, result.error_code, result.text) == (
        "failed", "configuration_changed", "",
    )
