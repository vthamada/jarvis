"""MB229 synthetic prose -> sovereign Core -> disposable persistent SQLite.

The graph is an owned scheduler fixture, not installed LangGraph evidence.
The TLS server is owned loopback with a synthetic CA, not an external model.
No autonomy, routing, specialist selection or governance is loosened for success.
"""

from __future__ import annotations

import hashlib
import http.client
import importlib.util
import json
import socket
import ssl
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

import pytest
from inference_service.http_transport import PlanResponsesHttpsTransport
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.providers import ResponsesPlanInferenceProvider
from inference_service.session_inference_port import SessionInferencePort
from inference_service.siwc_contracts import REQUESTED_SCOPES, SiwcCredentials
from inference_service.siwc_session import SiwcSession
from knowledge_service.source_review import LocalKnowledgeReview
from orchestrator_service import langgraph_flow
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import KnowledgeReviewBinding, ReviewedTextSource
from shared.types import PermissionDecision

QUERY = "Compare documentation and observability pilot reports."
ANALYSIS = (
    "Documentation describes intended behavior, whereas observability reports show "
    "what happened. Compare their coverage and discrepancies before deciding whether "
    "the pilot met its stated criteria. No actual report contents were supplied."
)
PRIOR = "PRIVATE_PRIOR_CONTEXT_SENTINEL"
RAW_BODY = "PRIVATE_UNSELECTED_BODY_SENTINEL"
QUOTE = "The pilot records coverage and discrepancies."
CREDENTIAL = "synthetic-explicit-private-credential"
MARKER = "Model-generated analysis (unverified; not facts, grants or action confirmations):"

_SPEC = importlib.util.spec_from_file_location(
    "jarvis_generative_tls_fixture",
    Path(__file__).resolve().parents[2] / "tests/support/https_fixture.py",
)
tls = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tls)


class _InferenceTlsFixture(tls.TlsFixture):
    """Consume the bounded POST body before replying/closing, unlike a GET fixture."""

    def __init__(self, context, payload, **kwargs):
        super().__init__(context, payload, **kwargs)
        self.server_errors = []

    def _serve(self):
        while not self.stop.is_set():
            try:
                connection, _ = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self.connections.append(connection)
            self.accepted.set()
            try:
                connection.settimeout(2)
                connection = self.context.wrap_socket(connection, server_side=True)
                self.connections.append(connection)
                request = bytearray()
                total = None
                while len(request) <= 32768:
                    block = connection.recv(4096)
                    if not block:
                        break
                    request.extend(block)
                    if total is None and b"\r\n\r\n" in request:
                        headers, body = request.split(b"\r\n\r\n", 1)
                        length = next(
                            (
                                int(line.split(b":", 1)[1])
                                for line in headers.split(b"\r\n")
                                if line.lower().startswith(b"content-length:")
                            ),
                            0,
                        )
                        total = len(headers) + 4 + length
                    if total is not None and len(request) >= total:
                        self.requests.append(bytes(request))
                        self.request_received.set()
                        connection.sendall(self.payload)
                        self.response_sent.set()
                        break
            except (OSError, ValueError, StopIteration) as error:
                self.server_errors.append(type(error).__name__)
            finally:
                connection.close()


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
        raise AssertionError("owned scheduler did not terminate")


def _contract(request="generative-core-request", text=QUERY):
    contract = PilotContext("generative-synthetic-subject", "generative-session").input(
        request, text
    )
    return replace(contract, user_id=contract.canonical_user_ref)


def _run(core, contract, flow, monkeypatch, **kwargs):
    if flow == "graph_fixture":
        monkeypatch.setattr(
            langgraph_flow, "_load_langgraph", lambda: (_GraphFixture, "start", "end")
        )
        return core.handle_input_langgraph_flow(contract, **kwargs)
    return core.handle_input(contract, **kwargs)


def _no_effects(core, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("generative analysis attempted an operational effect")

    for name in ("execute", "execute_local_text_file", "execute_and_commit_local_text_file_apply"):
        monkeypatch.setattr(core.operational_service, name, forbidden)


def _candidate():
    return {
        "analysis": ANALYSIS,
        "assumptions": ["Both reports refer to the same pilot."],
        "limitations": ["Their actual contents have not been independently verified."],
        "citations": [],
    }


class _Port:
    def __init__(self, mode="valid"):
        self.mode, self.calls = mode, []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        candidate = _candidate()
        if self.mode == "authority":
            candidate["actions"] = [{"delete": "database"}]
        elif self.mode == "bad_citation":
            candidate["citations"] = [
                {"source_ref": "foreign:source", "start": 0, "end": 1, "quote": "x"}
            ]
        elif self.mode == "oversized":
            candidate["analysis"] = "x" * 4001
        elif self.mode == "invalid_assumptions":
            candidate["assumptions"] = "not a list"
        elif self.mode == "empty_analysis":
            candidate["analysis"] = " "
        elif self.mode == "quote":
            sources = json.loads(request.messages[0].content)["sources"]
            source = next(value for value in sources if value["text"] == QUOTE)
            candidate["citations"] = [
                {"source_ref": source["source_ref"], "start": 0, "end": len(QUOTE), "quote": QUOTE}
            ]
        if self.mode == "raise":
            raise RuntimeError(CREDENTIAL)
        if self.mode in {"failed", "cancelled", "timed_out"}:
            return InferenceResult(
                request_id=request.request_id,
                model=request.model,
                provider_id="fixture",
                status=self.mode,
                error_code="synthetic_failure",
            )
        text = json.dumps(candidate)
        if self.mode == "duplicate":
            text = text[:-1] + ',"analysis":"FORGED_DUPLICATE_SENTINEL"}'
        return InferenceResult(
            request_id="foreign-request" if self.mode == "request" else request.request_id,
            model="foreign-model" if self.mode == "model" else request.model,
            provider_id="foreign-provider" if self.mode == "provider" else "fixture",
            status="completed",
            text=text,
            evidence_mode="live" if self.mode == "live_claim" else "fixture",
        )


def _configure(core, port, monkeypatch, **kwargs):
    core.synthesis_engine = SynthesisEngine(
        generative_port=port, generative_model="synthetic-model", **kwargs
    )
    inputs, results = [], []
    compose = core.synthesis_engine.compose_result

    def capture(value):
        inputs.append(value)
        result = compose(value)
        results.append(result)
        return result

    monkeypatch.setattr(core.synthesis_engine, "compose_result", capture)
    _no_effects(core, monkeypatch)
    return inputs, results


def _synthesis_event(response):
    return next(event for event in response.events if event.event_name == "response_synthesized")


def _assert_persisted(runtime, response):
    restarted = _isolated_core(runtime)
    turns = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 10)
    assert turns[-1].response_text == response.response_text
    events = restarted.observability_service.repository.list_events(
        request_id=response.request_id, event_names=("response_synthesized",), limit=10
    )
    assert len(events) == 1 and events[0].payload == _synthesis_event(response).payload
    return restarted


def _assert_no_authority(response):
    assert response.directive.should_execute_operation is False
    assert response.operation_dispatch is None and response.operation_result is None
    assert response.adapter_grant is None and response.action_confirmation_claim is None


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_meaningful_new_prose_is_subordinate_and_exact_final_survives_restart(
    tmp_path, monkeypatch, flow
):
    contract = _contract()
    baseline_core = _isolated_core(tmp_path / "baseline")
    baseline = _run(baseline_core, contract, flow, monkeypatch)
    runtime = tmp_path / "generative"
    core, port = _isolated_core(runtime), _Port()
    inputs, results = _configure(core, port, monkeypatch)
    response = _run(core, contract, flow, monkeypatch)
    assert baseline.governance_decision.decision == PermissionDecision.ALLOW
    assert response.governance_decision.decision == baseline.governance_decision.decision
    assert contract.requested_autonomy_level == contract.max_autonomy_level == "assist_only"
    assert response.deliberative_plan.capability_decision_selected_mode == "core_guidance_only"
    assert not response.specialist_invocations
    assert len(port.calls) == 1 and len(results) == 1
    assert results[0].generative_status == "accepted"
    assert results[0].generative_analysis_characters == len(ANALYSIS)
    assert MARKER in response.response_text
    assert ANALYSIS in response.response_text and ANALYSIS not in contract.content
    native = core.synthesis_engine._compose_native_result(inputs[0]).response_text
    assert response.response_text.startswith(native + "\n\n")
    assert response.response_text == results[0].response_text
    _assert_no_authority(response)
    event = _synthesis_event(response)
    assert event.payload["generative_status"] == "accepted"
    assert event.payload["generative_evidence_mode"] == "fixture"
    assert event.payload["generative_analysis_characters"] == len(ANALYSIS)
    event_text = json.dumps(event.payload, default=str)
    for secret in (ANALYSIS, "synthetic-model", CREDENTIAL):
        assert secret not in event_text
    # Canonical audit identity predates MB229. New model fields contain only
    # fixed status/code/mode/count, not identity or model/provider content.
    assert (
        event.payload["canonical_user_ref"]
        == _synthesis_event(baseline).payload["canonical_user_ref"]
    )
    generative_payload = {
        key: value for key, value in event.payload.items() if key.startswith("generative_")
    }
    assert contract.canonical_user_ref not in json.dumps(generative_payload)
    assert not {"analysis", "candidate", "prompt", "model", "account", "url"} & event.payload.keys()
    _assert_persisted(runtime, response)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize(
    "mode",
    [
        "authority",
        "bad_citation",
        "oversized",
        "invalid_assumptions",
        "empty_analysis",
        "duplicate",
        "request",
        "model",
        "provider",
        "live_claim",
        "failed",
        "cancelled",
        "timed_out",
        "raise",
    ],
)
def test_invalid_or_failed_proposal_retains_native_final_exactly(tmp_path, monkeypatch, flow, mode):
    core, port = _isolated_core(tmp_path), _Port(mode)
    inputs, results = _configure(core, port, monkeypatch)
    response = _run(core, _contract(), flow, monkeypatch)
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert len(port.calls) == 1
    assert results[0].generative_status == "rejected"
    assert results[0].generative_evidence_mode is None
    assert results[0].generative_analysis_characters == 0
    assert (
        response.response_text
        == core.synthesis_engine._compose_native_result(inputs[0]).response_text
    )
    assert MARKER not in response.response_text and CREDENTIAL not in response.response_text
    assert "FORGED_DUPLICATE_SENTINEL" not in response.response_text
    _assert_no_authority(response)
    _assert_persisted(tmp_path, response)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize(
    "query,decision",
    [
        ("Analyze policy evidence in read-only mode.", PermissionDecision.DEFER_FOR_VALIDATION),
        ("Delete every database now.", PermissionDecision.BLOCK),
    ],
)
def test_native_defer_or_block_never_calls_port(tmp_path, monkeypatch, flow, query, decision):
    core, port = _isolated_core(tmp_path), _Port()
    _, results = _configure(core, port, monkeypatch)
    response = _run(core, _contract(text=query), flow, monkeypatch)
    assert response.governance_decision.decision == decision
    assert port.calls == []
    assert results[0].generative_status == "withheld"
    assert MARKER not in response.response_text
    _assert_no_authority(response)
    _assert_persisted(tmp_path, response)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_default_disabled_and_precancelled_analysis_do_not_call_port(tmp_path, monkeypatch, flow):
    core = _isolated_core(tmp_path / "default")
    _no_effects(core, monkeypatch)
    default = _run(core, _contract(), flow, monkeypatch)
    assert default.governance_decision.decision == PermissionDecision.ALLOW
    assert MARKER not in default.response_text
    assert _synthesis_event(default).payload["generative_status"] == "disabled"
    cancellation = Event()
    cancellation.set()
    core, port = _isolated_core(tmp_path / "cancelled"), _Port()
    inputs, results = _configure(core, port, monkeypatch, generative_cancellation=cancellation)
    response = _run(core, _contract(), flow, monkeypatch)
    assert port.calls == [] and results[0].generative_status == "rejected"
    assert (
        response.response_text
        == core.synthesis_engine._compose_native_result(inputs[0]).response_text
    )


def _review(contract):
    text = RAW_BODY + "\n" + QUOTE + "\n" + RAW_BODY
    raw = text.encode("utf-8")
    source = ReviewedTextSource(
        text=text,
        source_url="https://fixture.example/private?token=private-url-sentinel",
        observed_at=datetime.now(UTC).isoformat(),
        content_sha256=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
        media_type="text/plain",
    )
    binding = KnowledgeReviewBinding(
        contract.canonical_user_ref, str(contract.session_id), str(contract.request_id)
    )
    review = LocalKnowledgeReview(binding)
    review.consent(binding, granted=True)
    ticket = review.propose(source, contract.content, binding=binding)
    review.review(ticket, binding=binding)
    start = text.index(QUOTE)
    selected = review.select(ticket, binding=binding, start=start, end=start + len(QUOTE))
    context = review.confirm(
        ticket, binding=binding, fingerprint=selected.fingerprint, revision=selected.revision
    )
    return review, context


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_only_current_input_and_reviewed_quote_are_sent_not_history_body_or_identity(
    tmp_path, monkeypatch, flow
):
    core = _isolated_core(tmp_path)
    _run(core, _contract("private-earlier", QUERY + " " + PRIOR), flow, monkeypatch)
    contract = _contract()
    review, context = _review(contract)
    port = _Port("quote")
    inputs, results = _configure(core, port, monkeypatch)
    response = _run(
        core, contract, flow, monkeypatch, reviewed_knowledge=context, knowledge_review=review
    )
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert results[0].generative_status == "accepted"
    assert PRIOR in "\n".join(inputs[0].recovered_context)
    assert len(port.calls) == 1
    request = port.calls[0]
    prompt = json.loads(request.messages[0].content)
    assert set(prompt) == {"schema_version", "sources"}
    assert prompt["schema_version"] == 1
    assert {source["text"] for source in prompt["sources"]} == {QUERY, QUOTE}
    assert all(set(source) == {"source_ref", "text"} for source in prompt["sources"])
    entire_request = request.instructions + request.messages[0].content
    for private in (
        PRIOR,
        RAW_BODY,
        context.source.source_url,
        contract.canonical_user_ref,
        contract.operator_identity_ref,
        contract.user_id,
        str(contract.session_id),
    ):
        assert private not in entire_request
    assert MARKER in response.response_text and QUOTE in response.response_text
    _assert_no_authority(response)
    _assert_persisted(tmp_path, response)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_synthesis_rechecks_effect_modes_and_pending_confirmations_without_inference(
    tmp_path, monkeypatch, flow
):
    core, port = _isolated_core(tmp_path), _Port()
    inputs, results = _configure(core, port, monkeypatch)
    _run(core, _contract(), flow, monkeypatch)
    assert results[0].generative_status == "accepted"
    value = inputs[0]
    plan = value.deliberative_plan
    mutations = [
        {"capability_decision_selected_mode": "operational_execution"},
        {
            "capability_decision_selected_capabilities": [
                "core_reasoning",
                "execute_external_action",
            ]
        },
        {"requires_human_validation": True},
        {"autonomy_human_confirmation_required": True},
        {"autonomy_confirmation_mode": "explicit_confirmation_required"},
        {"request_confirmation_mode": "explicit_confirmation_required"},
        {"capability_decision_authorization_status": "clarification_required"},
        {"objective_status": "blocked"},
    ]
    for change in mutations:
        port.calls.clear()
        altered = replace(value, deliberative_plan=replace(plan, **change))
        result = core.synthesis_engine.compose_result(altered)
        assert result.generative_status == "withheld", change
        assert port.calls == [], change
        assert MARKER not in result.response_text, change
    for change in ({"intent": "sensitive_action"}, {"extractive_context": None}):
        port.calls.clear()
        result = core.synthesis_engine.compose_result(replace(value, **change))
        assert result.generative_status == "withheld", change
        assert port.calls == [], change


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_port_cannot_change_eligible_plan_during_analysis(tmp_path, monkeypatch, flow):
    core, port = _isolated_core(tmp_path), _Port()
    inputs, results = _configure(core, port, monkeypatch)
    infer = port.infer

    def tamper(request, **kwargs):
        result = infer(request, **kwargs)
        inputs[-1].deliberative_plan.capability_decision_selected_capabilities.append(
            "execute_external_action"
        )
        return result

    monkeypatch.setattr(port, "infer", tamper)
    response = _run(core, _contract(), flow, monkeypatch)
    assert len(port.calls) == 1 and results[0].generative_status == "rejected"
    assert results[0].generative_error_code == "context_changed"
    assert MARKER not in response.response_text and ANALYSIS not in response.response_text
    _assert_no_authority(response)
    _assert_persisted(tmp_path, response)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
def test_model_draft_is_retained_exact_but_not_reintroduced_as_planning_context(
    tmp_path, monkeypatch, flow
):
    core, port = _isolated_core(tmp_path), _Port()
    _, results = _configure(core, port, monkeypatch)
    first = _run(core, _contract(), flow, monkeypatch)
    assert results[0].generative_status == "accepted"
    restarted = _assert_persisted(tmp_path, first)
    next_port = _Port()
    inputs, results = _configure(restarted, next_port, monkeypatch)
    second = _run(restarted, _contract("generative-after-restart"), flow, monkeypatch)
    assert results[0].generative_status == "accepted"
    assert ANALYSIS not in "\n".join(inputs[0].recovered_context)
    assert ANALYSIS not in second.deliberative_plan.rationale
    assert ANALYSIS not in next_port.calls[0].messages[0].content
    retained = restarted.memory_service.repository.fetch_recent_turns(first.session_id, 10)
    assert len(retained) == 2
    assert retained[0].response_text == first.response_text
    assert retained[1].response_text == second.response_text
    _assert_no_authority(second)


@pytest.mark.parametrize("flow", ["native", "graph_fixture"])
@pytest.mark.parametrize("terminal", ["completed", "partial", "failed"])
def test_owned_verified_tls_sse_provider_composes_or_falls_back_through_core(
    tmp_path, monkeypatch, flow, terminal
):
    candidate = json.dumps(_candidate())
    partial = {"type": "response.output_text.delta", "delta": "PRIVATE_PARTIAL_SENTINEL"}
    completed = {
        "type": "response.completed",
        "response": {
            "id": "owned-response",
            "model": "synthetic-model",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": candidate}],
                }
            ],
        },
    }
    events = [completed] if terminal == "completed" else [partial]
    if terminal == "failed":
        events.append(
            {
                "type": "response.failed",
                "response": {
                    "id": "owned-response",
                    "model": "synthetic-model",
                    "status": "failed",
                    "error": {"code": "subscription_sharing_usage_unavailable"},
                },
            }
        )
    wire = b"".join(("data: " + json.dumps(value) + "\r\n\r\n").encode() for value in events)
    payload = tls.response(
        wire,
        headers=[
            (b"Content-Type", b"text/event-stream"),
            (b"Content-Length", str(len(wire)).encode()),
            (b"Connection", b"close"),
        ],
    )
    calls, requests, inferences, socket_errors = [], [], [], []
    original_connection = http.client.HTTPSConnection
    original_timeout = ssl.SSLSocket.settimeout

    def audit_timeout(sock, value):
        try:
            return original_timeout(sock, value)
        except Exception as error:
            socket_errors.append((type(error).__name__, sock.fileno()))
            raise

    monkeypatch.setattr(ssl.SSLSocket, "settimeout", audit_timeout)
    monkeypatch.setattr(tls, "TlsFixture", _InferenceTlsFixture)
    with tls.tls_fixture(tmp_path, payload) as (server, client):

        class OwnedConnection(original_connection):
            def connect(self):
                raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw.settimeout(self.timeout)
                raw.connect(server.address)
                self.sock = client.wrap_socket(raw, server_hostname=tls.HOSTNAME)

        connection = OwnedConnection(tls.HOSTNAME, timeout=30, context=client)

        def factory(host, *, port, timeout, context):
            assert host == "api.openai.com" and port == 443
            assert context.check_hostname and timeout <= 30
            calls.append(host)
            connection.timeout = timeout
            return connection

        monkeypatch.setattr(
            "inference_service.http_transport.http.client.HTTPSConnection",
            lambda *_a, **_kw: pytest.fail("attempted unowned external HTTPS"),
        )
        transport = PlanResponsesHttpsTransport(
            bearer_token=CREDENTIAL,
            expires_at=2000,
            wall_clock=lambda: 1000,
            authorized=True,
            granted_scopes=("chatgpt.tokens.use.direct",),
            connection_factory=factory,
        )
        provider = ResponsesPlanInferenceProvider(transport)
        infer = provider.infer

        def capture(request, **kwargs):
            requests.append(request)
            result = infer(request, **kwargs)
            inferences.append(result)
            return result

        monkeypatch.setattr(provider, "infer", capture)
        runtime = tmp_path / "runtime"
        core = _isolated_core(runtime)
        inputs, results = _configure(
            core,
            provider,
            monkeypatch,
            generative_provider_id="responses_plan",
            generative_evidence_mode="injected_transport",
        )
        response = _run(core, _contract(), flow, monkeypatch)
        assert calls == ["api.openai.com"] and len(requests) == 1, (
            results[0].generative_status,
            results[0].generative_error_code,
            response.governance_decision.decision,
            len(requests),
            calls,
        )
        assert server.requests and server.server_names == [tls.HOSTNAME], (
            [(value.status, value.error_code) for value in inferences],
            server.server_errors,
            socket_errors,
        )
    expected = "accepted" if terminal == "completed" else "rejected"
    assert results[0].generative_status == expected, (
        results[0].generative_error_code,
        [(value.status, value.error_code) for value in inferences],
        socket_errors,
    )
    assert socket_errors == []
    if terminal == "completed":
        assert MARKER in response.response_text and ANALYSIS in response.response_text
        assert results[0].generative_evidence_mode == "injected_transport"
    else:
        assert (
            response.response_text
            == core.synthesis_engine._compose_native_result(inputs[0]).response_text
        )
    assert (
        CREDENTIAL not in response.response_text
        and "PRIVATE_PARTIAL_SENTINEL" not in response.response_text
    )
    _assert_no_authority(response)
    _assert_persisted(runtime, response)


@pytest.mark.parametrize(
    "mode,query,status,catalog_count,infer_count",
    [
        ("selected", QUERY, "accepted", 1, 1),
        ("unlisted", QUERY, "rejected", 1, 0),
        ("defer", "Analyze policy evidence in read-only mode.", "withheld", 0, 0),
        ("block", "Delete every database now.", "withheld", 0, 0),
    ],
)
def test_real_lazy_session_catalog_and_model_tls_remain_subordinate_to_native_governance(
    tmp_path, monkeypatch, mode, query, status, catalog_count, infer_count
):
    """Synthetic in-memory account fixture, not OAuth signature/login acceptance."""
    model = "synthetic-model"
    catalog_body = json.dumps(
        {
            "models": [
                {
                    "visibility": "list",
                    "slug": model if mode != "unlisted" else "different-model",
                    "display_name": "Owned synthetic model",
                }
            ]
        }
    ).encode()
    catalog_payload = tls.response(
        catalog_body,
        headers=[
            (b"Content-Type", b"application/json"),
            (b"Content-Length", str(len(catalog_body)).encode()),
            (b"Connection", b"close"),
        ],
    )
    completion = {
        "type": "response.completed",
        "response": {
            "id": "owned-response",
            "model": model,
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": json.dumps(_candidate())}],
                }
            ],
        },
    }
    wire = ("data: " + json.dumps(completion) + "\r\n\r\n").encode()
    inference_payload = tls.response(
        wire,
        headers=[
            (b"Content-Type", b"text/event-stream"),
            (b"Content-Length", str(len(wire)).encode()),
            (b"Connection", b"close"),
        ],
    )
    catalog_dir, model_dir = tmp_path / "catalog-tls", tmp_path / "model-tls"
    catalog_dir.mkdir()
    model_dir.mkdir()
    original_connection = http.client.HTTPSConnection
    monkeypatch.setattr(tls, "TlsFixture", _InferenceTlsFixture)
    with (
        tls.tls_fixture(catalog_dir, catalog_payload) as (catalog_server, catalog_client),
        tls.tls_fixture(model_dir, inference_payload) as (model_server, model_client),
    ):

        class OwnedConnection(original_connection):
            def __init__(self, server, client):
                super().__init__(tls.HOSTNAME, timeout=30, context=client)
                self.server, self.client = server, client

            def connect(self):
                raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw.settimeout(self.timeout)
                raw.connect(self.server.address)
                self.sock = self.client.wrap_socket(raw, server_hostname=tls.HOSTNAME)

        catalog_connection = OwnedConnection(catalog_server, catalog_client)
        model_connection = OwnedConnection(model_server, model_client)
        calls = []

        def catalog_factory(host, *, port, timeout, context):
            assert host == "api.openai.com" and port == 443 and context.check_hostname
            calls.append("catalog")
            catalog_connection.timeout = timeout
            return catalog_connection

        def model_factory(host, *, port, timeout, context):
            assert host == "api.openai.com" and port == 443 and context.check_hostname
            calls.append("inference")
            model_connection.timeout = timeout
            return model_connection

        monkeypatch.setattr(
            "inference_service.http_transport.http.client.HTTPSConnection",
            lambda *_a, **_kw: pytest.fail("attempted unowned account network request"),
        )
        host = "urn:uuid:12345678-1234-4234-8234-123456789abc"
        session = SiwcSession(
            host_id=host,
            wall_clock=lambda: 1000,
            client=SiwcHttpsClient(authorized=True, connection_factory=catalog_factory),
        )
        # Construct only this synthetic account. No credential store or human
        # token discovery/sign-in is used or claimed by this composition test.
        session._credentials = SiwcCredentials(
            "oaiapp_owned_fixture",
            host,
            "external-fixture-subject",
            CREDENTIAL,
            "synthetic-refresh",
            "synthetic-id-token",
            REQUESTED_SCOPES,
            2000,
            1000,
        )
        for name in ("begin", "load", "refresh"):
            if hasattr(session, name):
                monkeypatch.setattr(
                    session,
                    name,
                    lambda *_a, **_kw: pytest.fail(
                        "lazy inference attempted login/profile-load/refresh"
                    ),
                )
        port = SessionInferencePort(
            session, model=model, authorized=True, connection_factory=model_factory
        )
        inferences = []
        infer = port.infer

        def capture(request, **kwargs):
            result = infer(request, **kwargs)
            inferences.append(result)
            return result

        monkeypatch.setattr(port, "infer", capture)
        assert port.evidence_mode == "injected_transport"
        assert calls == [] and session._catalog is None
        core = _isolated_core(tmp_path / "runtime")
        inputs, results = _configure(
            core,
            port,
            monkeypatch,
            generative_provider_id="responses_plan",
            generative_evidence_mode=port.evidence_mode,
        )
        response = core.handle_input(_contract(text=query))
        assert results[0].generative_status == status, (
            results[0].generative_error_code,
            calls,
            [(value.status, value.error_code) for value in inferences],
        )
        assert calls.count("catalog") == catalog_count
        assert calls.count("inference") == infer_count
        assert len(catalog_server.requests) == catalog_count
        assert len(model_server.requests) == infer_count
        if infer_count:
            assert calls == ["catalog", "inference"]
            request = model_server.requests[0]
            body = json.loads(request.split(b"\r\n\r\n", 1)[1])
            prompt = json.loads(body["input"][0]["content"])
            assert {source["text"] for source in prompt["sources"]} == {query}
            assert body["model"] == model and body["store"] is False
            assert MARKER in response.response_text
        else:
            assert MARKER not in response.response_text
            assert (
                response.response_text
                == core.synthesis_engine._compose_native_result(inputs[0]).response_text
            )
        _assert_no_authority(response)
        _assert_persisted(tmp_path / "runtime", response)
