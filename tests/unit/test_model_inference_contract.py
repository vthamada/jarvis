"""Stable inference contract rejects ambiguous statuses and unbounded data."""

from dataclasses import FrozenInstanceError, replace

import pytest

from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult


def request():
    return InferenceRequest("req-1", "fixture-model", (InferenceMessage("user", "secret"),))


@pytest.mark.parametrize("changes", [
    {"request_id": "contains space"}, {"model": "model\n"}, {"messages": []},
    {"messages": ()}, {"messages": ("text",)}, {"timeout_seconds": True},
    {"timeout_seconds": float("nan")}, {"timeout_seconds": float("inf")},
    {"timeout_seconds": 0}, {"timeout_seconds": 121}, {"max_output_chars": True},
    {"max_output_chars": 0}, {"max_output_chars": 64_001},
    {"instructions": "x" * 16_001},
    {"messages": (InferenceMessage("user", "x" * 32_000),) * 3},
])
def test_invalid_request(changes):
    with pytest.raises(ValueError):
        replace(request(), **changes)


@pytest.mark.parametrize("role,content", [
    ("system", "x"), ("user", " "), ("assistant", "x" * 32_001), ("user", None),
])
def test_invalid_message(role, content):
    with pytest.raises(ValueError):
        InferenceMessage(role, content)


@pytest.mark.parametrize("changes", [
    {"request_id": "bad\n"}, {"model": None}, {"provider_id": "x" * 161},
    {"status": "partial"}, {"evidence_mode": "verified"}, {"text": " "},
    {"text": "x" * 64_001}, {"input_tokens": True}, {"output_tokens": -1},
    {"error_code": "remote secret message"},
    {"status": "failed", "error_code": "timeout"}, {"status": "failed", "text": ""},
])
def test_invalid_result(changes):
    result = InferenceResult("req-1", "model", "fixture", "completed", text="secret")
    with pytest.raises(ValueError):
        replace(result, **changes)


def test_frozen_contract_and_sensitive_content_not_in_repr():
    value = request()
    assert "secret" not in repr(value)
    with pytest.raises(FrozenInstanceError):
        value.model = "different"
    failed = InferenceResult("req-1", "model", "fixture", "failed", error_code="timeout")
    assert failed.text == ""
