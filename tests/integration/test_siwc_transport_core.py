"""Injected HTTPS/SSE -> provider -> extractive synthesis -> real SQLite Core.

No endpoint is contacted. Synthetic transport data and scheduler fixtures prove
local composition/fallback, not live inference, OAuth, LangGraph or promotion.
"""

from __future__ import annotations

import json
import ssl
from collections import deque
from dataclasses import replace

import pytest
from inference_service.http_transport import PlanResponsesHttpsTransport
from inference_service.providers import ResponsesPlanInferenceProvider
from orchestrator_service import langgraph_flow
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.types import PermissionDecision

TEXT = "Analise os fatos: A revisao acontece na quinta-feira. O responsavel e Ana."
QUOTE = "A revisao acontece na quinta-feira."
CREDENTIAL = "synthetic-explicit-private-credential"
PARTIAL = "UNPUBLISHED_PARTIAL_MODEL_SENTINEL"
OLDER = "PRIVATE_OLDER_CONTEXT_SENTINEL"


class _GraphFixture:
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
        raise AssertionError("synthetic scheduler did not terminate")


def _run(core, contract, mode, monkeypatch):
    if mode == "graph_fixture":
        monkeypatch.setattr(
            langgraph_flow, "_load_langgraph", lambda: (_GraphFixture, "start", "end")
        )
        return core.handle_input_langgraph_flow(contract)
    return core.handle_input(contract)


def _contract(
    *, request_id="siwc-extractive-request", content=TEXT, autonomy="bounded_core_action"
):
    return replace(
        PilotContext("siwc-synthetic-subject", "siwc-synthetic-session").input(request_id, content),
        requested_autonomy_level=autonomy,
        max_autonomy_level=autonomy,
    )


def _sse(event):
    return ("data: " + json.dumps(event, ensure_ascii=False) + "\r\n\r\n").encode("utf-8")


class _Socket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)


class _Response:
    status = 200

    def __init__(self):
        self.chunks = deque()
        self.closed = False

    def getheader(self, name, default):
        return {"Content-Type": "text/event-stream", "Content-Encoding": "identity"}.get(
            name, default
        )

    def read1(self, size):
        assert size == 4096
        return self.chunks.popleft() if self.chunks else b""

    def close(self):
        self.closed = True


class _Connection:
    def __init__(self, mode):
        self.mode = mode
        self.sock = _Socket()
        self.response = _Response()
        self.requests = []
        self.closed = False
        self.connected = False

    def connect(self):
        self.connected = True

    def request(self, method, path, *, body, headers):
        assert (method, path) == ("POST", "/v1/responses")
        assert headers["Authorization"] == f"Bearer {CREDENTIAL}"
        request = json.loads(body)
        self.requests.append(request)
        assert set(request) == {"model", "input", "instructions", "store", "stream"}
        assert request["store"] is False and request["stream"] is True
        assert len(request["input"]) == 1 and request["input"][0]["role"] == "user"
        source = json.loads(request["input"][0]["content"])
        assert set(source) == {"source_ref", "text"}
        assert source["text"] == TEXT
        assert OLDER not in body.decode("utf-8")
        offset = source["text"].index(QUOTE)
        candidate = json.dumps(
            {
                "citations": [
                    {
                        "source_ref": source["source_ref"],
                        "start": offset,
                        "end": offset + len(QUOTE),
                        "quote": QUOTE,
                    }
                ]
            }
        )
        completion = {
            "type": "response.completed",
            "response": {
                "id": "synthetic-response",
                "model": request["model"],
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": candidate}],
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 15, "total_tokens": 35},
            },
        }
        if self.mode == "partial":
            wire = _sse({"type": "response.output_text.delta", "delta": PARTIAL})
        elif self.mode == "failed":
            wire = _sse({"type": "response.output_text.delta", "delta": PARTIAL}) + _sse(
                {
                    "type": "response.failed",
                    "response": {
                        "id": "synthetic-response",
                        "model": request["model"],
                        "status": "failed",
                        "error": {"code": "subscription_sharing_usage_unavailable"},
                    },
                }
            )
        elif self.mode == "late_failed":
            wire = _sse(completion) + _sse({"type": "error", "code": CREDENTIAL})
        elif self.mode == "truncated":
            wire = _sse(completion).removesuffix(b"\r\n\r\n")
        else:
            assert self.mode == "valid"
            wire = (
                b": synthetic keepalive\r\n\r\n"
                + _sse({"type": "response.output_text.delta", "delta": candidate})
                + _sse(completion)
            )
        # Arbitrary byte boundaries exercise framing, not a direct Mapping seam.
        self.response.chunks.extend(wire[index : index + 17] for index in range(0, len(wire), 17))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


def _configure(core, mode, monkeypatch, *, authorized=True):
    calls, results, telemetry, inputs, synthesis = [], [], [], [], []
    connection = _Connection(mode)

    def factory(host, *, port, timeout, context):
        calls.append(host)
        assert host == "api.openai.com" and port == 443
        assert 0 < timeout <= 2
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        return connection

    monkeypatch.setattr(
        "inference_service.http_transport.http.client.HTTPSConnection",
        lambda *_a, **_kw: pytest.fail("test attempted a real external HTTPS connection"),
    )
    authorization = {"authorized": True} if authorized else {}
    transport = PlanResponsesHttpsTransport(
        bearer_token=CREDENTIAL,
        expires_at=2000,
        granted_scopes=("chatgpt.tokens.use.direct",),
        wall_clock=lambda: 1000,
        connection_factory=factory,
        **authorization,
    )
    provider = ResponsesPlanInferenceProvider(transport, telemetry=telemetry.append)
    infer = provider.infer

    def capture_inference(request, **kwargs):
        result = infer(request, **kwargs)
        results.append(result)
        return result

    monkeypatch.setattr(provider, "infer", capture_inference)
    core.synthesis_engine = SynthesisEngine(
        inference_port=provider,
        inference_model="account-selected-model",
        inference_provider_id="responses_plan",
        inference_evidence_mode="injected_transport",
    )
    compose = core.synthesis_engine.compose_result

    def capture_synthesis(value):
        inputs.append(value)
        result = compose(value)
        synthesis.append(result)
        return result

    monkeypatch.setattr(core.synthesis_engine, "compose_result", capture_synthesis)
    monkeypatch.setattr(
        core.operational_service,
        "execute",
        lambda *_a, **_kw: pytest.fail("inference attempted to dispatch an operation"),
    )
    return calls, results, telemetry, inputs, synthesis, connection


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize(
    "mode", ["valid", "partial", "failed", "late_failed", "truncated", "auth_off"]
)
def test_https_framing_provider_and_real_core_canonical_final(tmp_path, monkeypatch, flow, mode):
    core = _isolated_core(tmp_path)
    # Persist earlier private source to prove it is not sent as model context.
    _run(core, _contract(request_id="siwc-earlier", content="Analise " + OLDER), flow, monkeypatch)
    calls, results, telemetry, inputs, synthesis, connection = _configure(
        core,
        "valid" if mode == "auth_off" else mode,
        monkeypatch,
        authorized=mode != "auth_off",
    )
    response = _run(core, _contract(), flow, monkeypatch)
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert response.operation_dispatch is None and response.operation_result is None
    assert len(results) == len(synthesis) == len(telemetry) == 1
    expected = "accepted" if mode == "valid" else "rejected"
    assert synthesis[0].extractive_status == expected
    canonical = core.memory_service.repository.fetch_recent_turns(response.session_id, 10)[-1]
    assert canonical.response_text == response.response_text == synthesis[0].response_text
    assert CREDENTIAL not in response.response_text and PARTIAL not in response.response_text
    assert ("Evidence excerpts (untrusted input" in response.response_text) == (mode == "valid")
    if mode == "valid":
        assert QUOTE in response.response_text
        assert results[0].status == "completed"
        assert results[0].evidence_mode == "injected_transport"
        assert telemetry[0]["input_tokens"] == 20 and telemetry[0]["output_tokens"] == 15
    else:
        assert results[0].status == "failed" and results[0].text == ""
        assert (
            response.response_text
            == core.synthesis_engine._compose_native_result(inputs[0]).response_text
        )
        assert synthesis[0].extractive_evidence_mode is None
        assert synthesis[0].extractive_excerpt_count == 0
    if mode == "auth_off":
        assert calls == [] and connection.requests == []
        assert results[0].error_code == "plan_usage_not_authorized"
        assert not connection.connected
    else:
        assert calls == ["api.openai.com"] and len(connection.requests) == 1
        assert connection.closed and connection.response.closed
    persisted = core.observability_service.repository.list_events(
        request_id=response.request_id, event_names=("response_synthesized",), limit=10
    )
    assert len(persisted) == 1
    event = next(event for event in response.events if event.event_name == "response_synthesized")
    assert persisted[0].payload == event.payload
    assert event.payload["extractive_status"] == expected
    assert event.payload["extractive_excerpt_count"] == (1 if mode == "valid" else 0)
    assert event.payload["extractive_evidence_mode"] == (
        "injected_transport" if mode == "valid" else None
    )
    assert "quote" not in event.payload and "candidate" not in event.payload
    serialized = json.dumps([event.payload, telemetry], default=str)
    assert CREDENTIAL not in serialized and PARTIAL not in serialized


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_governance_defer_prevents_https_factory_even_when_opted_in(tmp_path, monkeypatch, flow):
    core = _isolated_core(tmp_path)
    calls, results, telemetry, _, synthesis, connection = _configure(core, "valid", monkeypatch)
    response = _run(core, _contract(autonomy="assist_only"), flow, monkeypatch)
    assert response.governance_decision.decision != PermissionDecision.ALLOW
    assert synthesis[0].extractive_status == "withheld"
    assert calls == results == telemetry == connection.requests == []
    assert not connection.connected
