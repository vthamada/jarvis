"""Real Core, disposable canonical stores, explicit synthetic autonomy only."""

import json
from dataclasses import replace

import pytest
from orchestrator_service import langgraph_flow
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.types import PermissionDecision

TEXT = "Analise os fatos: A revisao acontece na quinta-feira. O responsavel e Ana."
QUOTE = "A revisao acontece na quinta-feira."


class _GraphFixture:
    """Node scheduler fixture, not evidence of installed LangGraph execution."""

    def __init__(self, _state_type):
        self.nodes, self.edges = {}, {}

    def add_node(self, name, handler):
        self.nodes[name] = handler

    def add_edge(self, start, end):
        self.edges[start] = end

    def compile(self):
        return self

    def invoke(self, initial):
        state, node = dict(initial), "start"
        for _ in range(32):
            node = self.edges[node]
            if node == "end":
                return state
            state.update(self.nodes[node](state))
        raise AssertionError("fixture graph did not terminate")


def _run(core, contract, mode, monkeypatch):
    if mode == "graph_fixture":
        monkeypatch.setattr(
            langgraph_flow, "_load_langgraph", lambda: (_GraphFixture, "start", "end")
        )
        return core.handle_input_langgraph_flow(contract)
    return core.handle_input(contract)


class ExtractiveFixture:
    def __init__(self, mode="valid"):
        self.mode = mode
        self.calls = []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        source = json.loads(request.messages[0].content)
        offset = source["text"].index(QUOTE)
        candidate = {
            "citations": [
                {
                    "source_ref": source["source_ref"],
                    "start": offset,
                    "end": offset + len(QUOTE),
                    "quote": QUOTE,
                }
            ]
        }
        if self.mode == "authority":
            candidate["executed"] = True
        if self.mode == "bad_quote":
            candidate["citations"][0]["quote"] = "FORBIDDEN MODEL SENTINEL"
        return InferenceResult(
            request_id=request.request_id,
            model=request.model,
            provider_id="fixture",
            status="completed",
            text=json.dumps(candidate),
            evidence_mode="fixture",
        )


def _contract(autonomy="bounded_core_action"):
    return replace(
        PilotContext("extractive-synthetic-subject", "extractive-synthetic-session").input(
            "extractive-public-request",
            TEXT,
        ),
        requested_autonomy_level=autonomy,
        max_autonomy_level=autonomy,
    )


@pytest.mark.parametrize(
    "mode,expected_status",
    [
        ("valid", "accepted"),
        ("authority", "rejected"),
        ("bad_quote", "rejected"),
    ],
)
@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_real_core_canonical_synthesis_contains_only_validated_excerpts(
    tmp_path,
    monkeypatch,
    mode,
    expected_status,
    flow,
):
    core = _isolated_core(tmp_path)
    fixture = ExtractiveFixture(mode)
    core.synthesis_engine = SynthesisEngine(inference_port=fixture, inference_model="fixture-model")
    outputs, inputs = [], []
    compose = core.synthesis_engine.compose_result

    def capture(value):
        inputs.append(value)
        result = compose(value)
        outputs.append(result)
        return result

    monkeypatch.setattr(core.synthesis_engine, "compose_result", capture)
    monkeypatch.setattr(
        core.operational_service,
        "execute",
        lambda *_a, **_kw: pytest.fail(
            "extractive synthesis attempted an operation",
        ),
    )
    response = _run(core, _contract(), flow, monkeypatch)
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert response.operation_dispatch is None and response.operation_result is None
    assert len(fixture.calls) == 1
    result = outputs[0]
    assert result.extractive_status == expected_status
    canonical = core.memory_service.repository.fetch_recent_turns(response.session_id, 10)[-1]
    assert canonical.response_text == response.response_text == result.response_text
    assert "FORBIDDEN MODEL SENTINEL" not in response.response_text
    assert ("Evidence excerpts (untrusted input" in response.response_text) == (mode == "valid")
    synthesis_event = next(
        event for event in response.events if event.event_name == "response_synthesized"
    )
    assert synthesis_event.payload["extractive_status"] == expected_status
    assert synthesis_event.payload["extractive_excerpt_count"] == (1 if mode == "valid" else 0)
    assert synthesis_event.payload["extractive_evidence_mode"] == (
        "fixture" if mode == "valid" else None
    )
    assert "quote" not in synthesis_event.payload and "candidate" not in synthesis_event.payload
    if mode != "valid":
        assert (
            result.response_text
            == core.synthesis_engine._compose_native_result(
                inputs[0],
            ).response_text
        )


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_real_core_defer_and_default_disabled_never_call_model(tmp_path, monkeypatch, flow):
    core = _isolated_core(tmp_path)
    fixture = ExtractiveFixture()
    core.synthesis_engine = SynthesisEngine(inference_port=fixture, inference_model="fixture-model")
    response = _run(core, _contract("assist_only"), flow, monkeypatch)
    assert response.governance_decision.decision != PermissionDecision.ALLOW
    assert fixture.calls == []
    event = next(event for event in response.events if event.event_name == "response_synthesized")
    assert event.payload["extractive_status"] == "withheld"
    core.synthesis_engine = SynthesisEngine()
    response = _run(
        core, replace(_contract(), request_id="extractive-default-off"), flow, monkeypatch
    )
    event = next(event for event in response.events if event.event_name == "response_synthesized")
    assert event.payload["extractive_status"] == "disabled"
    assert fixture.calls == []
