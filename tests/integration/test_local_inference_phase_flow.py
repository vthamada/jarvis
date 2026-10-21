"""Real loopback TCP proves phase/EOF fences; completions are scripted fixtures."""

from __future__ import annotations

import json
import socketserver
import threading
from contextlib import contextmanager

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider
from inference_service.local_chat_transport import LocalChatHttpTransport

from shared.model_inference import InferenceMessage, InferenceRequest

MODEL = "scripted-phase-fixture"
PRIVATE_TEXT = "PRIVATE_SYNTHETIC_COMPLETION"
PHASES = ["connect_complete", "request_sent", "first_byte", "headers_validated",
          "body_complete", "peer_closed", "provider_parse_complete"]


@contextmanager
def _phase_server(*, chunked, tail=b""):
    body = json.dumps({
        "id": "private-completion-id", "object": "chat.completion", "model": MODEL,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": PRIVATE_TEXT}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }).encode("utf-8")
    fields = "Content-Type: application/json\r\n"
    if chunked:
        fields += "Transfer-Encoding: chunked\r\n"
        wire_body = f"{len(body):X}\r\n".encode("ascii") + body + b"\r\n0\r\n\r\n"
    else:
        fields += f"Content-Length: {len(body)}\r\n"
        wire_body = body
    wire = f"HTTP/1.1 200 OK\r\n{fields}\r\n".encode("ascii") + wire_body

    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            try:
                incoming = bytearray()
                while b"\r\n\r\n" not in incoming:
                    part = self.request.recv(4096)
                    if not part:
                        return
                    incoming.extend(part)
                    if len(incoming) > 524_288:
                        raise AssertionError("fixture_request_limit")
                head, request_body = bytes(incoming).split(b"\r\n\r\n", 1)
                lines = head.decode("ascii").split("\r\n")
                headers = dict(line.split(": ", 1) for line in lines[1:])
                length = int(headers["Content-Length"])
                if not 0 < length <= 524_288:
                    raise AssertionError("fixture_request_limit")
                while len(request_body) < length:
                    part = self.request.recv(min(8192, length - len(request_body)))
                    if not part:
                        return
                    request_body += part
                self.server.requests.append((lines[0], headers, json.loads(request_body)))
                self.server.response_started.set()
                self.request.sendall(wire)
                if not self.server.release.wait(2):
                    raise AssertionError("fixture_release_timeout")
                if tail:
                    self.request.sendall(tail)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass  # A cancelled/refusing transport is allowed to close first.
            except Exception as exc:
                self.server.errors.append(type(exc).__name__)
            finally:
                self.server.handler_finished.set()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    server.requests, server.errors = [], []
    server.response_started = threading.Event()
    server.release = threading.Event()
    server.handler_finished = threading.Event()
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01},
                              daemon=True)
    worker.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
        assert not worker.is_alive()
        assert server.handler_finished.wait(2)
        assert server.errors == []


def _start_inference(endpoint, observer, cancellation):
    provider = ChatCompletionsInferenceProvider(
        model=MODEL,
        transport=LocalChatHttpTransport(endpoint=endpoint, phase_observer=observer),
        evidence_mode="live", phase_observer=observer,
    )
    request = InferenceRequest(
        request_id="private-inference-id", model=MODEL, timeout_seconds=5,
        messages=(InferenceMessage("user", "PRIVATE_SYNTHETIC_PROMPT"),),
    )
    results = []
    worker = threading.Thread(
        target=lambda: results.append(provider.infer(request, cancellation=cancellation)),
        daemon=True,
    )
    worker.start()
    return worker, results


def _assert_private_metadata(events):
    for event in events:
        assert set(event) == {"event", "phase", "elapsed_ms", "timing_mode"}
        assert event["event"] == "local_inference_phase"
        assert event["phase"] in PHASES
        assert event["timing_mode"] == "live"  # Clock/socket evidence, not a real model.
        assert type(event["elapsed_ms"]) is int and 0 <= event["elapsed_ms"] <= 120_000
    text = repr(events).lower()
    for private in ("private", MODEL, "127.0.0.1", "content-type", "tokens", "authorization"):
        assert private.lower() not in text


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_body_phase_is_observed_before_eof_but_publication_waits_for_peer_close(chunked):
    events, observed = [], threading.Event()

    def observe(event):
        events.append(event)
        if event["phase"] == "body_complete":
            observed.set()

    with _phase_server(chunked=chunked) as (server, endpoint):
        worker, results = _start_inference(endpoint, observe, threading.Event())
        try:
            assert observed.wait(2)
            assert server.response_started.is_set() and not server.handler_finished.is_set()
            assert worker.is_alive() and results == []
            assert [event["phase"] for event in events] == PHASES[:5]
            server.release.set()
            worker.join(timeout=2)
            assert not worker.is_alive() and len(results) == 1
            assert results[0].status == "completed" and results[0].text == PRIVATE_TEXT
            assert [event["phase"] for event in events] == PHASES
            assert len(server.requests) == 1
            path, headers, payload = server.requests[0]
            assert path == "POST /v1/chat/completions HTTP/1.1"
            assert "Authorization" not in headers and "Cookie" not in headers
            assert headers["Connection"] == "close" and payload["stream"] is False
            _assert_private_metadata(events)
        finally:
            server.release.set()
            worker.join(timeout=2)
            assert not worker.is_alive()


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_body_phase_callback_can_cancel_before_eof_and_withhold_text(chunked):
    events, observed, cancellation = [], threading.Event(), threading.Event()

    def observe(event):
        events.append(event)
        if event["phase"] == "body_complete":
            cancellation.set()
            observed.set()

    with _phase_server(chunked=chunked) as (server, endpoint):
        worker, results = _start_inference(endpoint, observe, cancellation)
        try:
            assert observed.wait(2)
            worker.join(timeout=2)
            assert not worker.is_alive() and len(results) == 1
            assert (results[0].status, results[0].error_code, results[0].text) == (
                "cancelled", "cancelled", "",
            )
            assert [event["phase"] for event in events] == PHASES[:5]
            _assert_private_metadata(events)
        finally:
            server.release.set()
            worker.join(timeout=2)
            assert not worker.is_alive()


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_late_bytes_after_body_phase_remain_refused_without_provider_parse(chunked):
    events, observed = [], threading.Event()

    def observe(event):
        events.append(event)
        if event["phase"] == "body_complete":
            observed.set()

    with _phase_server(chunked=chunked, tail=b"PRIVATE_LATE_TAIL") as (server, endpoint):
        worker, results = _start_inference(endpoint, observe, threading.Event())
        try:
            assert observed.wait(2)
            assert worker.is_alive() and results == []
            server.release.set()
            worker.join(timeout=2)
            assert not worker.is_alive() and len(results) == 1
            assert (results[0].status, results[0].error_code, results[0].text) == (
                "failed", "invalid_http_response", "",
            )
            assert [event["phase"] for event in events] == PHASES[:5]
            _assert_private_metadata(events)
        finally:
            server.release.set()
            worker.join(timeout=2)
            assert not worker.is_alive()
