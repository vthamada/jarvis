"""Offline inference-to-code slice includes real Core memory and final synthesis."""

import json
from dataclasses import replace
from threading import Event

import pytest
from inference_service import FakeInferenceProvider, ResponsesPlanInferenceProvider
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console import code_pilot
from shared.model_inference import InferenceResult


def test_success_preserves_core_and_leaves_no_runtime(tmp_path, monkeypatch):
    composed = []
    compose = SynthesisEngine.compose_result

    def tracked_compose(self, synthesis_input):
        result = compose(self, synthesis_input)
        composed.append(result)
        return result

    monkeypatch.setattr(SynthesisEngine, "compose_result", tracked_compose)
    monkeypatch.chdir(tmp_path)
    # A local pilot cannot inherit database/tracing settings from production.
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    result = code_pilot.IsolatedCodePilot(
        FakeInferenceProvider(code_pilot.fixture_proposal())
    ).run()
    assert result.fixture_result.status == "passed"
    assert result.fixture_result.passed == 3
    response = result.core_response
    assert response.operation_dispatch is None
    assert response.operation_result is None
    assert response.intent == "analysis"
    assert response.memory_record.memory_record_id
    assert response.governance_decision
    assert response.response_text
    names = [event.event_name for event in response.events]
    assert composed[-1].response_text == response.response_text
    assert any("memory" in name for name in names)
    assert not list(tmp_path.iterdir())
    projection = result.projection()
    assert projection["core"]["runtime_mode"] == "temporary_sqlite"
    assert projection["runtime_capability_promoted"] is False
    assert "after_text" not in json.dumps(projection)
    assert "a + b" not in repr(result)


@pytest.mark.parametrize("text", [
    "not-json", "[]", '{"path":"calculator.py","path":"evil.py"}',
    code_pilot.fixture_proposal().replace("calculator.py", "../secret.py"),
    code_pilot.fixture_proposal().replace("expected_sha256", "authority"),
    json.dumps({**json.loads(code_pilot.fixture_proposal()), "grant": "allow"}),
])
def test_malformed_proposal_cannot_reach_core_as_instructions(text):
    result = code_pilot.IsolatedCodePilot(FakeInferenceProvider(text)).run()
    assert result.proposal_status == "rejected"
    assert result.fixture_result is None
    assert "evil.py" not in result.core_response.response_text
    assert result.core_response.operation_dispatch is None


@pytest.mark.parametrize("source,status", [
    (code_pilot.FIXTURE_BEFORE, "test_failed"),
    ("import os\ndef add(a, b):\n    return a + b\n", "rejected"),
])
def test_failing_and_unsafe_code_are_not_success(source, status):
    result = code_pilot.IsolatedCodePilot(
        FakeInferenceProvider(code_pilot.fixture_proposal(source))
    ).run()
    assert result.fixture_result.status == status
    assert result.fixture_result.host_effects is False
    assert result.core_response.operation_dispatch is None


def test_cancellation_never_tests_a_candidate():
    cancellation = Event()
    cancellation.set()
    result = code_pilot.IsolatedCodePilot(
        FakeInferenceProvider(code_pilot.fixture_proposal())
    ).run(cancellation=cancellation)
    assert result.inference_status == "cancelled"
    assert result.fixture_result is None


@pytest.mark.parametrize("change", ["identity", "live", "exception", "not-contract"])
def test_bad_provider_is_unavailable_and_sanitized(change):
    class Provider:
        def infer(self, request, *, cancellation=None):
            if change == "exception":
                raise RuntimeError("secret-provider-diagnostic")
            if change == "not-contract":
                return object()
            result = InferenceResult(
                request.request_id, request.model, "fixture", "completed",
                text=code_pilot.fixture_proposal(),
            )
            return replace(result, **(
                {"request_id": "different"} if change == "identity" else {"evidence_mode": "live"}
            ))
    result = code_pilot.IsolatedCodePilot(Provider()).run()
    assert result.inference_status == "failed"
    assert result.fixture_result is None
    assert "secret-provider-diagnostic" not in json.dumps(result.projection())


def test_injected_response_stream_is_only_fixture_evidence():
    def transport(payload, **kwargs):
        yield {"type": "response.completed", "response": {
            "id": "resp-fixture", "model": payload["model"], "status": "completed",
            "output": [{"type": "message", "role": "assistant", "status": "completed",
                        "content": [{"type": "output_text",
                                     "text": code_pilot.fixture_proposal()}]}],
        }}
    result = code_pilot.IsolatedCodePilot(ResponsesPlanInferenceProvider(transport)).run()
    assert result.inference_evidence_mode == "injected_transport"
    assert result.fixture_result.status == "passed"
    assert result.projection()["runtime_capability_promoted"] is False
