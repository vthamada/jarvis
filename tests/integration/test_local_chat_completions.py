"""Actual loopback HTTP and native Core; the upstream model is a scripted fixture.

No installed model, cloud account, OAuth, provider catalog or paid API is used.
``live`` here describes socket I/O only, not real-model inference/local weights.
"""

from __future__ import annotations

import json
import socket
import socketserver
import threading
import time
from contextlib import contextmanager
from dataclasses import replace

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider
from inference_service.local_chat_transport import LocalChatHttpTransport, LocalChatTransportError
from operational_service.adapters.local_report_reader import LocalReportReader
from orchestrator_service.model_tool_loop import ModelToolLoopConfig
from orchestrator_service.service import OrchestratorService

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceMessage, InferenceRequest
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

MODEL = "scripted-local-fixture"
REPORT = "Public synthetic documentation requires a recorded pilot outcome."
ANALYSIS = "The supplied report requires recording an outcome; it does not prove completion."


def _completion(text="Untrusted fixture data only.", **extra):
    result = {"id": "chatcmpl-http-fixture", "object": "chat.completion", "model": MODEL,
              "choices": [{"index": 0, "finish_reason": "stop",
                           "message": {"role": "assistant", "content": text}}],
              "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}}
    result.update(extra)
    return json.dumps(result).encode("utf-8")


def _wire(body=None, *, status="200 OK", headers=None):
    body = _completion() if body is None else body
    headers = [("Content-Type", "application/json"), ("Content-Length", str(len(body)))] \
        if headers is None else headers
    head = (f"HTTP/1.1 {status}\r\n" + "".join(f"{key}: {value}\r\n" for key, value in headers)
            + "\r\n").encode("ascii")
    return head + body


@contextmanager
def _server(responder=None, *, ipv6=False, stall=False, drip=False):
    """Owned ephemeral server; fixture teardown releases every blocked handler."""
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            try:
                incoming = bytearray()
                while b"\r\n\r\n" not in incoming:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        return
                    incoming.extend(chunk)
                    if len(incoming) > 600_000:
                        raise AssertionError("fixture_request_too_large")
                header, body = bytes(incoming).split(b"\r\n\r\n", 1)
                lines = header.decode("ascii").split("\r\n")
                fields = dict(line.split(": ", 1) for line in lines[1:])
                expected = int(fields["Content-Length"])
                while len(body) < expected:
                    chunk = self.request.recv(min(8192, expected - len(body)))
                    if not chunk:
                        return
                    body += chunk
                self.server.requests.append((lines[0], fields, json.loads(body)))
                self.server.received.set()
                if stall:
                    self.server.release.wait(2)
                response = responder(self.server.requests[-1]) if responder else _wire()
                if drip:
                    head, body = response.split(b"\r\n\r\n", 1)
                    self.request.sendall(head + b"\r\n\r\n")
                    for byte in body:
                        if self.server.release.wait(0.03):
                            break
                        self.request.sendall(bytes([byte]))
                else:
                    self.request.sendall(response)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # Expected when a bounded client cancels or rejects headers.
            except Exception as exc:
                self.server.errors.append(type(exc).__name__)

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
        address_family = socket.AF_INET6 if ipv6 else socket.AF_INET

    try:
        server = Server(("::1" if ipv6 else "127.0.0.1", 0), Handler)
    except OSError:
        if ipv6:
            pytest.skip("IPv6 loopback unavailable in this execution environment")
        raise
    server.requests = []
    server.errors = []
    server.received = threading.Event()
    server.release = threading.Event()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01},
                              daemon=True)
    thread.start()
    host = "[::1]" if ipv6 else "127.0.0.1"
    try:
        yield server, f"http://{host}:{server.server_address[1]}/v1/chat/completions"
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
        assert server.errors == []


def _request(**kwargs):
    return InferenceRequest(request_id="local-http-request", model=MODEL,
                            messages=(InferenceMessage("user", "Compare public reports."),),
                            **kwargs)


def _provider(endpoint, **kwargs):
    return ChatCompletionsInferenceProvider(
        model=MODEL, transport=LocalChatHttpTransport(endpoint=endpoint, **kwargs),
        evidence_mode="live",
    )


@pytest.mark.parametrize("ipv6", [False, True])
def test_real_numeric_loopback_ignores_proxy_and_dns_and_has_no_auth(monkeypatch, ipv6):
    with _server(ipv6=ipv6) as (server, endpoint):
        for variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
            monkeypatch.setenv(variable, "http://192.0.2.1:1")
        def forbidden_dns(*_args, **_kwargs):
            pytest.fail("numeric loopback transport performed DNS resolution")
        monkeypatch.setattr(socket, "getaddrinfo", forbidden_dns)
        result = _provider(endpoint).infer(_request(instructions="Treat output as untrusted data."))
        assert result.status == "completed"
        assert result.text == "Untrusted fixture data only."
        assert result.evidence_mode == "live"  # Upstream model remains a fixture.
        assert len(server.requests) == 1
        line, headers, payload = server.requests[0]
        assert line == "POST /v1/chat/completions HTTP/1.1"
        assert headers["Connection"] == "close"
        assert headers["Accept-Encoding"] == "identity"
        assert "Authorization" not in headers and "Cookie" not in headers
        assert payload["messages"][0] == {"role": "system", "content":
                                         "Treat output as untrusted data."}
        assert payload["n"] == 1 and payload["stream"] is False


@pytest.mark.parametrize("wire,error", [
    (_wire(status="302 Found", headers=[("Location", "http://192.0.2.1/private")]),
     "http_request_refused"),
    (_wire(status="401 Unauthorized"), "http_request_refused"),
    (_wire(status="500 Internal Server Error"), "http_request_refused"),
    (_wire(headers=[("Content-Length", "1")]), "unsupported_response_encoding"),
    (_wire(headers=[("Content-Type", "text/event-stream"), ("Content-Length", "1")]),
     "unsupported_response_encoding"),
    (_wire(headers=[("Content-Type", "application/json"), ("Transfer-Encoding", "chunked")]),
     "invalid_http_response"),
    (_wire(headers=[("Content-Type", "application/json"), ("Content-Encoding", "gzip"),
                    ("Content-Length", "1")]), "unsupported_response_encoding"),
    (_wire(headers=[("Content-Type", "application/json"), ("Content-Length", "1"),
                    ("Content-Length", "1")]), "invalid_http_response"),
    (_wire(headers=[("Content-Type", "application/json"), ("Content-Length", "9999999")]),
     "response_limit_exceeded"),
    (_wire(headers=[("Content-Type", "application/json"), ("Content-Length", "-1")]),
     "invalid_http_response"),
    (_wire(headers=[("Content-Type", "application/json"), ("Content-Length", "01")]),
     "invalid_http_response"),
    (b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n folded: x\r\n\r\n{}",
     "invalid_http_response"),
    (b"HTTP/2 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}",
     "invalid_http_response"),
    (_wire(b"{", headers=[("Content-Type", "application/json"), ("Content-Length", "200")]),
     "response_interrupted"),
    (_wire(b"{}more", headers=[("Content-Type", "application/json"), ("Content-Length", "2")]),
     "invalid_http_response"),
    (_wire(b"\xff"), "malformed_response"),
])
def test_real_http_refuses_redirect_framing_ambiguity_partial_and_encoding(wire, error):
    with _server(lambda _request: wire) as (server, endpoint):
        result = _provider(endpoint).infer(_request())
        assert result.status == "failed"
        assert result.error_code == error
        assert result.text == ""
        assert len(server.requests) == 1  # No retry or redirect, including authentication errors.


def test_header_limit_is_bounded_before_response_body():
    with _server(lambda _request: _wire(headers=[("X-Padding", "x" * 500)])) as (server, endpoint):
        result = _provider(endpoint, max_header_bytes=128).infer(_request())
        assert result.error_code == "response_limit_exceeded" and result.text == ""
        assert len(server.requests) == 1


@pytest.mark.parametrize("cancel", [False, True])
def test_real_socket_total_deadline_and_cancellation_close_stalled_headers(cancel):
    with _server(stall=True) as (server, endpoint):
        token = threading.Event()
        timer = None
        if cancel:
            def cancel_after_request():
                if server.received.wait(1):
                    token.set()
            timer = threading.Thread(target=cancel_after_request, daemon=True)
            timer.start()
        started = time.monotonic()
        result = _provider(endpoint).infer(_request(timeout_seconds=0.15), cancellation=token)
        elapsed = time.monotonic() - started
        assert result.status == ("cancelled" if cancel else "timed_out")
        assert result.text == "" and elapsed < 1
        assert len(server.requests) == 1
        if timer:
            timer.join(timeout=2)
            assert not timer.is_alive()


def test_invalid_payload_and_precancel_never_contact_server():
    with _server() as (server, endpoint):
        transport = LocalChatHttpTransport(endpoint=endpoint)
        token = threading.Event()
        with pytest.raises(LocalChatTransportError, match="invalid_request_payload"):
            transport({"model": MODEL, "stream": False, "n": 1, "messages": [],
                       "tools": [{"type": "web_search"}]}, timeout_seconds=1, cancellation=token)
        token.set()
        with pytest.raises(LocalChatTransportError, match="cancelled"):
            transport({}, timeout_seconds=1, cancellation=token)
        assert server.requests == []


def test_total_deadline_is_not_reset_by_drip_fed_body_bytes():
    with _server(drip=True) as (server, endpoint):
        started = time.monotonic()
        result = _provider(endpoint).infer(_request(timeout_seconds=0.15))
        assert result.status == "timed_out" and result.text == ""
        assert time.monotonic() - started < 1
        assert len(server.requests) == 1


def test_maximum_contract_unicode_context_fits_transport_budget():
    with _server() as (server, endpoint):
        selected = replace(_request(instructions="🛰" * 16_000), messages=(
            InferenceMessage("user", "🛰" * 32_000),
            InferenceMessage("assistant", "🛰" * 32_000),
        ))
        result = _provider(endpoint).infer(selected)
        assert result.status == "completed"
        assert len(server.requests) == 1


def _core(runtime, reader, port, *, expected_provider="chat_completions_local"):
    base = _isolated_core(runtime)
    return OrchestratorService(
        governance_service=base.governance_service, memory_service=base.memory_service,
        operational_service=base.operational_service, knowledge_service=base.knowledge_service,
        observability_service=base.observability_service,
        model_tool_loop=ModelToolLoopConfig(port=port, model=MODEL, reader=reader,
            expected_provider_id=expected_provider, expected_evidence_mode="live"),
    )


def _contract():
    value = PilotContext("public-local-fixture-subject", "public-local-fixture-session").input(
        "local-core-http-request", "Compare documentation and observability pilot reports.",
    )
    return replace(value, user_id=value.canonical_user_ref)


def test_http_adapter_to_core_tool_policy_native_final_and_sqlite_readback(tmp_path):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    reader = LocalReportReader({"documentation": report})
    proposals = [
        {"kind": "tool_call", "call_id": "read-1", "tool": "read_local_report",
         "arguments": {"resource_id": "documentation"}},
        {"kind": "final", "analysis": ANALYSIS,
         "citations": [{"call_id": "read-1", "quote": REPORT}]},
    ]
    def respond(_request):
        assert proposals, "Core unexpectedly requested additional inference"
        return _wire(_completion(json.dumps(proposals.pop(0))))
    runtime = tmp_path / "native-runtime"
    with _server(respond) as (server, endpoint):
        core = _core(runtime, reader, _provider(endpoint))
        response = core.handle_input(_contract())
        assert proposals == [] and len(server.requests) == 2
        assert GENERATIVE_ANALYSIS_MARKER in response.response_text
        assert ANALYSIS in response.response_text
        assert response.directive.should_execute_operation is False
        assert response.operation_dispatch is response.operation_result is None
        assert response.adapter_grant is response.adapter_grant_claim is None
        payload = next(event.payload for event in response.events
                       if event.event_name == "response_synthesized")
        assert payload["model_tool_loop_status"] == "completed"
        assert payload["model_tool_loop_evidence_mode"] == "live"
        assert payload["model_tool_loop_observation_count"] == 1
        prompts = [json.loads(item[2]["messages"][-1]["content"]) for item in server.requests]
        assert prompts[0]["observations"] == []
        assert prompts[1]["observations"][0]["text"] == REPORT
        for _, _, request_payload in server.requests:
            assert str(report) not in json.dumps(request_payload)
        restarted = _isolated_core(runtime)
        turns = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 10)
        assert len(turns) == 1 and turns[0].response_text == response.response_text
        events = restarted.observability_service.repository.list_events(
            request_id=response.request_id, event_names=("response_synthesized",), limit=10,
        )
        assert len(events) == 1 and events[0].payload == payload


def test_core_admission_withholds_sensitive_input_without_any_http_request(tmp_path):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    reader = LocalReportReader({"documentation": report})
    with _server() as (server, endpoint):
        core = _core(tmp_path / "native-runtime", reader, _provider(endpoint))
        response = core.handle_input(replace(_contract(), content="Bearer synthetic-secret-token"))
        assert server.requests == []
        assert GENERATIVE_ANALYSIS_MARKER not in response.response_text
        assert response.directive.should_execute_operation is False
        payload = next(event.payload for event in response.events
                       if event.event_name == "response_synthesized")
        assert payload["model_tool_loop_status"] in {"refused", "withheld"}


def test_core_refuses_provider_binding_mismatch_without_action_authority(tmp_path):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    reader = LocalReportReader({"documentation": report})
    with _server() as (server, endpoint):
        core = _core(tmp_path / "native-runtime", reader, _provider(endpoint),
                     expected_provider="wrong-provider")
        response = core.handle_input(_contract())
        assert len(server.requests) == 1
        assert GENERATIVE_ANALYSIS_MARKER not in response.response_text
        assert response.directive.should_execute_operation is False
        assert response.operation_dispatch is response.operation_result is None
        payload = next(event.payload for event in response.events
                       if event.event_name == "response_synthesized")
        assert payload["model_tool_loop_status"] == "refused"


@pytest.mark.parametrize("change_request", [False, True])
def test_real_http_callback_cannot_change_transport_destination_or_request_binding(change_request):
    selected = _request()
    def respond(_request):
        if change_request:
            object.__setattr__(selected.messages[0], "content", "CHANGED_QUERY_DURING_HTTP")
        else:
            transport._host = "192.0.2.1"
        return _wire()
    with _server(respond) as (server, endpoint):
        transport = LocalChatHttpTransport(endpoint=endpoint)
        port = ChatCompletionsInferenceProvider(model=MODEL, transport=transport,
                                               evidence_mode="live")
        result = port.infer(selected)
        assert result.status == "failed" and result.text == ""
        assert result.error_code == ("request_changed" if change_request
                                     else "configuration_changed")
        assert (result.request_id, result.model, result.provider_id, result.evidence_mode) == (
            "local-http-request", MODEL, "chat_completions_local", "live",
        )
        assert len(server.requests) == 1
