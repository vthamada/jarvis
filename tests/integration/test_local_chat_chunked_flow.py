"""Real chunked loopback HTTP to the adapter and sovereign Core, scripted model only."""

from __future__ import annotations

import json
import socketserver
import threading
import time
from contextlib import contextmanager
from dataclasses import replace

import pytest
from inference_service.chat_completions_provider import ChatCompletionsInferenceProvider
from inference_service.local_chat_transport import LocalChatHttpTransport
from operational_service.adapters.local_report_reader import LocalReportReader
from orchestrator_service.model_tool_loop import ModelToolLoopConfig
from orchestrator_service.service import OrchestratorService

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceMessage, InferenceRequest
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

MODEL = "chunked-scripted-fixture"
REPORT = "Public synthetic documentation records a pending pilot result."
ANALYSIS = "The supplied report records a pending result, not completed acceptance."


def _completion(text="Untrusted fixture data only.", *, model=MODEL, padding=""):
    return json.dumps({
        "id": "chatcmpl-chunked-fixture", "object": "chat.completion", "model": model,
        "choices": [{"index": 0, "finish_reason": "stop", "message": {
            "role": "assistant", "content": text,
        }}], "fixture_padding": padding,
    }, ensure_ascii=False).encode("utf-8")


def _wire(body, *, chunk_size=97):
    chunks = [body[i:i + chunk_size] for i in range(0, len(body), chunk_size)]
    return (b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
            b"Transfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
            + b"".join(f"{len(chunk):X}\r\n".encode("ascii") + chunk + b"\r\n"
                       for chunk in chunks) + b"0\r\n\r\n")


@contextmanager
def _server(responses, *, width=None, hold_open=False, drip=False, late_extra=b""):
    """Owned ephemeral fixture; no daemon/model or account is contacted."""
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            self.request.settimeout(2)
            try:
                incoming = bytearray()
                while b"\r\n\r\n" not in incoming:
                    data = self.request.recv(4096)
                    if not data:
                        return
                    incoming.extend(data)
                    if len(incoming) > 600_000:
                        raise AssertionError("fixture_request_limit")
                header, body = bytes(incoming).split(b"\r\n\r\n", 1)
                lines = header.decode("ascii").split("\r\n")
                fields = dict(line.split(": ", 1) for line in lines[1:])
                expected = int(fields["Content-Length"])
                if expected > 524_288:
                    raise AssertionError("fixture_request_limit")
                while len(body) < expected:
                    data = self.request.recv(min(8192, expected - len(body)))
                    if not data:
                        return
                    body += data
                self.server.requests.append((fields, json.loads(body)))
                wire = self.server.responses.pop(0)
                if drip:
                    head, wire = wire.split(b"\r\n\r\n", 1)
                    self.request.sendall(head + b"\r\n\r\n")
                step = width or len(wire)
                for offset in range(0, len(wire), step):
                    if drip and self.server.release.wait(0.03):
                        return
                    self.request.sendall(wire[offset:offset + step])
                self.server.sent.set()
                if late_extra and not self.server.release.wait(0.03):
                    self.request.sendall(late_extra)
                if hold_open:
                    self.server.release.wait(2)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as exc:
                self.server.errors.append(type(exc).__name__)

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    server = Server(("127.0.0.1", 0), Handler)
    server.responses = list(responses)
    server.requests = []
    server.errors = []
    server.sent = threading.Event()
    server.release = threading.Event()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01},
                              daemon=True)
    thread.start()
    try:
        yield server, f"http://127.0.0.1:{server.server_address[1]}/v1/chat/completions"
    finally:
        server.release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
        assert server.errors == []


def _provider(endpoint, *, telemetry=None, max_response_bytes=1_048_576):
    return ChatCompletionsInferenceProvider(
        model=MODEL, transport=LocalChatHttpTransport(
            endpoint=endpoint, max_response_bytes=max_response_bytes,
        ), evidence_mode="live", telemetry=telemetry,
    )


def _request(*, timeout_seconds=2):
    return InferenceRequest(
        request_id="chunked-request", model=MODEL,
        messages=(InferenceMessage("user", "Compare public synthetic reports."),),
        timeout_seconds=timeout_seconds,
    )


@pytest.mark.parametrize("width", [1, 23, 8192])
def test_real_http_complete_large_json_survives_arbitrary_write_boundaries(width):
    text = "Untrusted synthetic data: " + "á" * 3000
    body = _completion(text)
    assert len(body) > 2048
    with _server([_wire(body)], width=width) as (server, endpoint):
        result = _provider(endpoint).infer(_request())
        assert result.status == "completed" and result.text == text
        assert result.evidence_mode == "live"  # Socket I/O only; model is a fixture.
        assert len(server.requests) == 1 and server.responses == []
        headers, payload = server.requests[0]
        assert headers["Connection"] == "close" and "Authorization" not in headers
        assert payload["stream"] is False and payload["n"] == 1


@pytest.mark.parametrize("tail", [b"", b"0", b"0\r", b"0\r\n", b"0\r\n\r"])
def test_real_chunked_eof_cannot_publish_json_without_complete_terminal_frame(tail):
    wire = _wire(_completion())[:-5] + tail
    with _server([wire]) as (server, endpoint):
        result = _provider(endpoint).infer(_request())
        assert result.status == "failed" and result.error_code == "response_interrupted"
        assert result.text == "" and len(server.requests) == 1


@pytest.mark.parametrize("cancel", [False, True])
def test_terminal_chunk_does_not_bypass_peer_eof_deadline_or_cancellation(cancel):
    with _server([_wire(_completion())], hold_open=True) as (server, endpoint):
        token = threading.Event()
        waiter = None
        if cancel:
            def cancel_when_sent():
                if server.sent.wait(1):
                    token.set()
            waiter = threading.Thread(target=cancel_when_sent, daemon=True)
            waiter.start()
        started = time.monotonic()
        result = _provider(endpoint).infer(_request(timeout_seconds=0.15), cancellation=token)
        assert result.status == ("cancelled" if cancel else "timed_out")
        assert result.text == "" and time.monotonic() - started < 1
        assert len(server.requests) == 1
        if waiter is not None:
            waiter.join(timeout=2)
            assert not waiter.is_alive()


def test_chunk_framing_drip_cannot_reset_total_deadline():
    with _server([_wire(_completion())], width=1, drip=True) as (server, endpoint):
        started = time.monotonic()
        result = _provider(endpoint).infer(_request(timeout_seconds=0.15))
        assert result.status == "timed_out" and result.text == ""
        assert time.monotonic() - started < 1 and len(server.requests) == 1


@pytest.mark.parametrize("extra", [b"secret-garbage", b"HTTP/1.1 401 Unauthorized\r\n\r\n"])
def test_late_extra_bytes_after_terminal_chunk_are_not_silent_success(extra):
    events = []
    with _server([_wire(_completion())], late_extra=extra) as (server, endpoint):
        result = _provider(endpoint, telemetry=events.append).infer(_request())
        assert result.status == "failed" and result.error_code == "invalid_http_response"
        assert result.text == "" and len(server.requests) == 1
        assert len(events) == 1 and events[0]["error_code"] == "invalid_http_response"
        serialized = json.dumps(events)
        assert "secret" not in serialized and "Untrusted fixture" not in serialized
        assert endpoint not in serialized


def test_decoded_json_limit_applies_across_many_legitimate_chunks():
    with _server([_wire(_completion("x" * 3000), chunk_size=100)]) as (server, endpoint):
        result = _provider(endpoint, max_response_bytes=2048).infer(_request())
        assert result.status == "failed" and result.error_code == "response_limit_exceeded"
        assert result.text == "" and len(server.requests) == 1


def test_chunked_response_keeps_exact_model_binding():
    with _server([_wire(_completion(model="different-model"))]) as (server, endpoint):
        result = _provider(endpoint).infer(_request())
        assert result.status == "failed" and result.error_code == "model_mismatch"
        assert result.text == "" and result.model == MODEL and len(server.requests) == 1


def test_chunked_fixture_to_core_tool_native_final_and_durable_memory(tmp_path):
    report = tmp_path / "public-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    proposals = [
        {"kind": "tool_call", "call_id": "read-1", "tool": "read_local_report",
         "arguments": {"resource_id": "documentation"}},
        {"kind": "final", "analysis": ANALYSIS,
         "citations": [{"call_id": "read-1", "quote": REPORT}]},
    ]
    # >2KiB JSON per response, but only the bound proposal text is model output.
    responses = [_wire(_completion(json.dumps(value), padding="x" * 3000))
                 for value in proposals]
    runtime = tmp_path / "core-runtime"
    with _server(responses) as (server, endpoint):
        base = _isolated_core(runtime)
        core = OrchestratorService(
            governance_service=base.governance_service, memory_service=base.memory_service,
            operational_service=base.operational_service, knowledge_service=base.knowledge_service,
            observability_service=base.observability_service,
            model_tool_loop=ModelToolLoopConfig(
                port=_provider(endpoint), model=MODEL,
                reader=LocalReportReader({"documentation": report}),
                expected_provider_id="chat_completions_local", expected_evidence_mode="live",
            ),
        )
        value = PilotContext("chunked-fixture-subject", "chunked-fixture-session").input(
            "chunked-core-request", "Compare documentation and observability pilot reports.",
        )
        response = core.handle_input(replace(value, user_id=value.canonical_user_ref))
        assert server.responses == [] and len(server.requests) == 2
        assert GENERATIVE_ANALYSIS_MARKER in response.response_text
        assert ANALYSIS in response.response_text
        assert response.directive.should_execute_operation is False
        assert response.operation_dispatch is response.operation_result is None
        assert response.adapter_grant is response.adapter_grant_claim is None
        payload = next(event.payload for event in response.events
                       if event.event_name == "response_synthesized")
        assert payload["model_tool_loop_status"] == "completed"
        assert payload["model_tool_loop_observation_count"] == 1
        prompts = [json.loads(request["messages"][-1]["content"])
                   for _, request in server.requests]
        assert prompts[0]["observations"] == []
        assert prompts[1]["observations"][0]["text"] == REPORT
        assert str(report) not in json.dumps(server.requests)
        restarted = _isolated_core(runtime)
        turns = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 10)
        assert len(turns) == 1 and turns[0].response_text == response.response_text
        events = restarted.observability_service.repository.list_events(
            request_id=response.request_id, event_names=("response_synthesized",), limit=10,
        )
        assert len(events) == 1 and events[0].payload == payload
