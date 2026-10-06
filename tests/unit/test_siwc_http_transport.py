"""SIWC framing/HTTPS composition with injected sockets; no external requests."""

from __future__ import annotations

import json
import ssl
from collections import deque
from threading import Event

import pytest
from inference_service.http_transport import PlanResponsesHttpsTransport, PlanTransportError
from inference_service.providers import ResponsesPlanInferenceProvider

from shared.model_inference import InferenceMessage, InferenceRequest

TOKEN = "explicit-private-test-credential"
PAYLOAD = {
    "model": "account-model",
    "input": [{"role": "user", "content": "Synthetic request"}],
    "store": False,
    "stream": True,
}
COMPLETE = {
    "type": "response.completed",
    "response": {
        "id": "response-synthetic",
        "model": "account-model",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Olá"}],
            }
        ],
    },
}


def sse(event=COMPLETE):
    return ("data: " + json.dumps(event, ensure_ascii=False) + "\n\n").encode("utf-8")


class Socket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)


class Response:
    def __init__(
        self, chunks=(), *, status=200, content_type="text/event-stream", encoding="identity"
    ):
        self.chunks = deque(chunks)
        self.status = status
        self.content_type = content_type
        self.encoding = encoding
        self.closed = False
        self.reads = 0
        self.on_read = None

    def getheader(self, key, default):
        return {"Content-Type": self.content_type, "Content-Encoding": self.encoding}.get(
            key, default
        )

    def read1(self, size):
        assert size == 4096
        self.reads += 1
        if self.on_read:
            self.on_read()
        value = self.chunks.popleft() if self.chunks else b""
        if isinstance(value, Exception):
            raise value
        return value

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, response):
        self.response = response
        self.sock = Socket()
        self.timeout = None
        self.calls = []
        self.closed = False
        self.on_connect = None
        self.on_request = None
        self.on_response = None

    def connect(self):
        self.calls.append("connect")
        if self.on_connect:
            self.on_connect()

    def request(self, method, path, *, body, headers):
        self.calls.append((method, path, body, headers))
        if self.on_request:
            self.on_request()

    def getresponse(self):
        self.calls.append("getresponse")
        if self.on_response:
            self.on_response()
        return self.response

    def close(self):
        self.closed = True


def fixture(*, chunks=None, response=None, **kwargs):
    response = response or Response([sse()] if chunks is None else chunks)
    connection = Connection(response)
    factory_calls = []

    def factory(*args, **options):
        factory_calls.append((args, options))
        return connection

    defaults = {
        "bearer_token": TOKEN,
        "expires_at": 2000.0,
        "authorized": True,
        "granted_scopes": ("chatgpt.tokens.use.direct",),
        "connection_factory": factory,
        "clock": lambda: 1.0,
        "wall_clock": lambda: 1000.0,
    }
    defaults.update(kwargs)
    transport = PlanResponsesHttpsTransport(**defaults)
    return transport, connection, response, factory_calls


def collect(transport, payload=None, *, cancellation=None, timeout=10):
    return list(
        transport(
            PAYLOAD if payload is None else payload,
            timeout_seconds=timeout,
            cancellation=cancellation or Event(),
        )
    )


def assert_error(transport, code, **kwargs):
    with pytest.raises(PlanTransportError) as failure:
        collect(transport, **kwargs)
    assert str(failure.value) == code
    assert TOKEN not in repr(failure.value)
    return failure.value


def test_construction_and_generator_creation_have_no_network():
    transport, connection, response, calls = fixture()
    stream = transport(PAYLOAD, timeout_seconds=10, cancellation=Event())
    assert calls == connection.calls == []
    assert TOKEN not in repr(transport)
    assert "Synthetic request" not in repr(stream)
    stream.close()
    assert not connection.closed and not response.closed


def test_fixed_https_request_tls_and_in_memory_header():
    transport, connection, response, calls = fixture()
    assert collect(transport) == [COMPLETE]
    assert len(calls) == 1
    args, options = calls[0]
    assert args == ("api.openai.com",)
    assert options["port"] == 443
    assert options["context"].verify_mode == ssl.CERT_REQUIRED
    assert options["context"].check_hostname
    method, path, body, headers = connection.calls[1]
    assert (method, path) == ("POST", "/v1/responses")
    assert json.loads(body) == PAYLOAD
    assert headers == {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Accept-Encoding": "identity",
    }
    assert connection.closed and response.closed
    assert transport.evidence_mode == "injected_transport"


def test_default_factory_does_not_read_proxy_environment(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "https://foreign.invalid:9000")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://foreign.invalid")
    monkeypatch.setenv("OPENAI_API_KEY", "should-not-be-read")
    response = Response([sse()])
    connection = Connection(response)
    calls = []
    monkeypatch.setattr(
        "inference_service.http_transport.http.client.HTTPSConnection",
        lambda *args, **kw: calls.append((args, kw)) or connection,
    )
    transport = PlanResponsesHttpsTransport(
        bearer_token=TOKEN,
        expires_at=2000,
        authorized=True,
        granted_scopes=("chatgpt.tokens.use.direct",),
        wall_clock=lambda: 1000,
    )
    assert transport.evidence_mode == "fixed_https_transport"  # Not live-call evidence.
    assert collect(transport) == [COMPLETE]
    assert calls[0][0] == ("api.openai.com",)
    assert connection.calls[1][3]["Authorization"] == f"Bearer {TOKEN}"


@pytest.mark.parametrize(
    "kwargs,code",
    [
        ({"authorized": False}, "plan_usage_not_authorized"),
        ({"granted_scopes": ()}, "plan_usage_scope_missing"),
        (
            {
                "granted_scopes": (
                    "openid",
                    "chatgpt.tokens.use",
                )
            },
            "plan_usage_scope_missing",
        ),
        ({"expires_at": 1000}, "credential_expired"),
        ({"wall_clock": lambda: float("nan")}, "invalid_clock"),
        ({"clock": lambda: True}, "invalid_clock"),
    ],
)
def test_scope_consent_expiry_and_clock_refuse_before_factory(kwargs, code):
    transport, connection, response, calls = fixture(**kwargs)
    assert_error(transport, code)
    assert calls == connection.calls == []
    assert not response.closed  # No response was opened.


@pytest.mark.parametrize(
    "token", ["", "x\r\nX: private", "token with space", "token💥", "x" * 8193, None, "x=y"]
)
def test_invalid_credentials_sanitized_without_network(token):
    with pytest.raises(ValueError, match="^invalid_bearer_credential$"):
        fixture(bearer_token=token)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"expires_at": True},
        {"expires_at": float("inf")},
        {"authorized": "yes"},
        {"granted_scopes": ["chatgpt.tokens.use.direct"]},
        {"granted_scopes": (None,)},
        {"clock": None},
        {"wall_clock": None},
        {"connection_factory": 7},
        {"max_events": True},
        {"max_line_bytes": 0},
        {"max_stream_bytes": 8_388_609},
        {"max_event_bytes": 1_048_577},
    ],
)
def test_invalid_constructor_declarations(kwargs):
    with pytest.raises(ValueError):
        fixture(**kwargs)


@pytest.mark.parametrize(
    "change",
    [
        {"store": True},
        {"stream": False},
        {"input": "private"},
        {"input": []},
        {"input": [{"role": "system", "content": "private"}]},
        {"input": [{"role": "developer", "content": "private"}]},
        {"input": [{"role": "user", "content": "private", "type": "message"}]},
        {"input": [{"role": "user", "content": " "}]},
        {"input": [{"role": "user", "content": "x" * 32001}]},
        {"input": [{"role": "user", "content": "x"}] * 33},
        {"input": [{"role": "user", "content": "x" * 32000}] * 3},
        {"instructions": "x" * 16001},
        {"instructions": None},
        {"model": "bad\nmodel"},
        {"model": "x" * 161},
        {"input": [{"role": "user", "content": "\ud800"}]},
    ],
)
def test_payload_refusals_before_network(change):
    transport, connection, response, calls = fixture()
    assert_error(transport, "invalid_request_payload", payload=PAYLOAD | change)
    assert calls == connection.calls == []


@pytest.mark.parametrize(
    "field",
    [
        "background",
        "conversation",
        "max_output_tokens",
        "max_tool_calls",
        "metadata",
        "moderation",
        "multi_agent",
        "prompt",
        "prompt_cache_retention",
        "safety_identifier",
        "temperature",
        "top_logprobs",
        "top_p",
        "truncation",
        "user",
        "previous_response_id",
        "tools",
        "base_url",
    ],
)
def test_unsupported_preview_fields_never_sent(field):
    transport, connection, _, calls = fixture()
    assert_error(transport, "unsupported_request_field", payload=PAYLOAD | {field: "private"})
    assert calls == connection.calls == []


@pytest.mark.parametrize("timeout", [True, 0, -1, 121, float("nan"), "10"])
def test_invalid_timeout_is_eager(timeout):
    transport, _, _, calls = fixture()
    with pytest.raises(PlanTransportError, match="^invalid_timeout$"):
        transport(PAYLOAD, timeout_seconds=timeout, cancellation=Event())
    assert calls == []


def test_payload_is_snapshotted_before_network():
    transport, connection, _, _ = fixture()
    payload = PAYLOAD | {"input": [{"role": "user", "content": "before"}]}
    stream = transport(payload, timeout_seconds=10, cancellation=Event())
    payload["input"][0]["content"] = "after"
    assert list(stream) == [COMPLETE]
    assert json.loads(connection.calls[1][2])["input"][0]["content"] == "before"


@pytest.mark.parametrize(
    "status,code",
    [
        (301, "http_request_refused"),
        (307, "http_request_refused"),
        (400, "http_request_refused"),
        (401, "plan_authentication_refused"),
        (403, "plan_permission_refused"),
        (429, "plan_usage_limited"),
        (500, "http_request_refused"),
    ],
)
def test_http_errors_and_redirects_no_body_retry_or_echo(status, code):
    transport, connection, response, calls = fixture(
        response=Response([b"private body"], status=status)
    )
    assert_error(transport, code)
    assert response.reads == 0
    assert len(calls) == 1
    assert connection.closed and response.closed


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content_type": "application/json"},
        {"content_type": None},
        {"encoding": "gzip"},
        {"encoding": None},
    ],
)
def test_wrong_content_type_or_encoding_refused(kwargs):
    transport, connection, response, _ = fixture(response=Response([sse()], **kwargs))
    assert_error(transport, "unsupported_response_encoding")
    assert response.reads == 0
    assert connection.closed and response.closed


@pytest.mark.parametrize("separator", [b"\n", b"\r\n", b"\r"])
def test_sse_utf8_splits_comments_bom_and_multiline_data(separator):
    data = (
        b"\xef\xbb\xbf: heartbeat"
        + separator
        + b"event: response.completed"
        + separator
        + b"id: untrusted"
        + separator
        + b"retry: 123"
        + separator
        + b"unknown: ignored"
        + separator
        + b'data: {"type": "response.completed",'
        + separator
        + b'data: "response":'
        + json.dumps(COMPLETE["response"], ensure_ascii=False).encode("utf-8")
        + b"}"
        + separator
        + separator
    )
    transport, connection, response, _ = fixture(chunks=[bytes([byte]) for byte in data])
    assert collect(transport) == [COMPLETE]
    assert connection.closed and response.closed


@pytest.mark.parametrize(
    "stream,code",
    [
        (b"data: [DONE]\n\n", "ambiguous_stream_terminal"),
        (b'data: {"type":"one","type":"two"}\n\n', "malformed_sse_event"),
        (b'data: {"type":"one","nested":{"x":1,"x":2}}\n\n', "malformed_sse_event"),
        (b'data: {"type":"one","x":NaN}\n\n', "malformed_sse_event"),
        (b'data: {"type":"one","x":1e999}\n\n', "malformed_sse_event"),
        (b'data: {"type":"one","x":"\\ud800"}\n\n', "malformed_sse_event"),
        (b'data: {"type":"one","x":"\xff"}\n\n', "malformed_sse_event"),
        (b"data: []\n\n", "malformed_sse_event"),
        (b"data: {}\n\n", "malformed_sse_event"),
        (b'data: {"type":"one"} private\n\n', "malformed_sse_event"),
        (b'event: two\ndata: {"type":"one"}\n\n', "malformed_sse_event"),
        (b'event: one\nevent: one\ndata: {"type":"one"}\n\n', "ambiguous_sse_event"),
        (b'data: {"type":"one"}\n', "stream_interrupted"),
        (b'data: {"type":"one"}', "stream_interrupted"),
        (b'data: {"type":', "stream_interrupted"),
    ],
)
def test_malformed_sse_never_echoes_content(stream, code):
    transport, connection, response, _ = fixture(chunks=[stream])
    assert_error(transport, code)
    assert connection.closed and response.closed


@pytest.mark.parametrize(
    "kwargs,chunks,code",
    [
        ({"max_line_bytes": 4}, [b"data: long"], "line_limit_exceeded"),
        ({"max_line_bytes": 4}, [b"data: long\n"], "line_limit_exceeded"),
        ({"max_event_bytes": 4}, [b": long\n"], "event_limit_exceeded"),
        ({"max_stream_bytes": 4}, [b": ok\n"], "stream_limit_exceeded"),
        ({"max_events": 1}, [sse(), sse()], "event_limit_exceeded"),
        ({}, [b"x" * 4097], "malformed_stream_chunk"),
        ({}, ["private"], "malformed_stream_chunk"),
    ],
)
def test_stream_limits_and_invalid_chunks(kwargs, chunks, code):
    transport, connection, response, _ = fixture(chunks=chunks, **kwargs)
    assert_error(transport, code)
    assert connection.closed and response.closed


def test_cancellation_before_connect_never_opens_network():
    token = Event()
    token.set()
    transport, _, _, calls = fixture()
    error = assert_error(transport, "cancelled", cancellation=token)
    assert error.status == "cancelled"
    assert calls == []


@pytest.mark.parametrize("phase", ["connect", "request", "response", "read"])
def test_cancellation_checked_after_every_io_and_closes(phase):
    token = Event()
    transport, connection, response, _ = fixture()
    target = response if phase == "read" else connection
    setattr(target, "on_" + phase, token.set)
    assert_error(transport, "cancelled", cancellation=token)
    assert connection.closed
    assert response.closed == (phase in {"response", "read"})


def test_deadline_timeout_between_io_updates_remaining_socket_timeout():
    now = [1.0]
    transport, connection, response, _ = fixture(clock=lambda: now[0])
    connection.on_connect = lambda: now.__setitem__(0, 3.0)
    response.on_read = lambda: now.__setitem__(0, 11.0)
    error = assert_error(transport, "timeout")
    assert error.status == "timed_out"
    assert 8.0 in connection.sock.timeouts
    assert connection.closed and response.closed


def test_expiry_rechecked_after_connect():
    wall = [1000.0]
    transport, connection, _, _ = fixture(wall_clock=lambda: wall[0])
    connection.on_connect = lambda: wall.__setitem__(0, 2000.0)
    assert_error(transport, "credential_expired")
    assert connection.calls == ["connect"]
    assert connection.closed


def test_detached_response_socket_retains_remaining_deadline_timeout():
    now = [1.0]
    transport, connection, response, _ = fixture(clock=lambda: now[0])
    sock = connection.sock

    def detach_socket():
        connection.sock = None
        now[0] = 5.0

    connection.on_response = detach_socket
    assert collect(transport) == [COMPLETE]
    assert sock.timeouts[-1] == 6.0
    assert connection.closed and response.closed


def test_backward_clock_refused_after_connect():
    now = [1.0]
    transport, connection, _, _ = fixture(clock=lambda: now[0])
    connection.on_connect = lambda: now.__setitem__(0, 0.0)
    assert_error(transport, "invalid_clock")
    assert connection.closed


@pytest.mark.parametrize(
    "error,code", [(TimeoutError(TOKEN), "timeout"), (OSError(TOKEN), "transport_error")]
)
def test_socket_error_details_not_published(error, code):
    transport, connection, response, _ = fixture(chunks=[error])
    assert_error(transport, code)
    assert connection.closed and response.closed


def test_explicit_stream_close_releases_connection_and_response():
    transport, connection, response, _ = fixture(chunks=[sse(), sse()])
    stream = transport(PAYLOAD, timeout_seconds=10, cancellation=Event())
    assert next(stream) == COMPLETE
    assert not connection.closed and not response.closed
    stream.close()
    assert connection.closed and response.closed


def test_semantic_completion_is_delegated_to_provider():
    transport, connection, response, _ = fixture(chunks=[b": comment\n\n"])
    result = ResponsesPlanInferenceProvider(transport).infer(
        InferenceRequest(
            "synthetic", "account-model", (InferenceMessage("user", "Synthetic request"),)
        )
    )
    assert result.status == "failed" and result.error_code == "stream_interrupted"
    assert result.text == ""
    assert result.evidence_mode == "injected_transport"
    assert connection.closed and response.closed


def test_injected_connection_provider_end_to_end():
    transport, connection, response, _ = fixture(
        chunks=[sse({"type": "response.output_text.delta", "delta": "Olá"}), sse()]
    )
    result = ResponsesPlanInferenceProvider(transport).infer(
        InferenceRequest(
            "synthetic", "account-model", (InferenceMessage("user", "Synthetic request"),)
        )
    )
    assert result.status == "completed" and result.text == "Olá"
    assert result.evidence_mode == "injected_transport"
    assert connection.closed and response.closed


@pytest.mark.parametrize(
    "tail",
    [
        sse({"type": "error", "code": "private-details"}),
        b"private incomplete tail",
        b"data: [DONE]\n\n",
    ],
)
def test_late_error_or_tail_discards_completed_text(tail):
    transport, connection, response, _ = fixture(chunks=[sse(), tail])
    result = ResponsesPlanInferenceProvider(transport).infer(
        InferenceRequest(
            "synthetic", "account-model", (InferenceMessage("user", "Synthetic request"),)
        )
    )
    assert result.status == "failed" and result.text == ""
    assert connection.closed and response.closed


def test_unverified_tls_context_never_opens_connection(monkeypatch):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    monkeypatch.setattr(
        "inference_service.http_transport.ssl.create_default_context", lambda: context
    )
    transport, _, _, calls = fixture()
    assert_error(transport, "tls_verification_required")
    assert calls == []


@pytest.mark.parametrize(
    "code,status,expected_code,expected_status",
    [
        (TOKEN, "completed", "transport_error", "failed"),
        (None, "cancelled", "transport_error", "failed"),
        ("cancelled", "completed", "cancelled", "cancelled"),
        ("timeout", "failed", "timeout", "timed_out"),
        ("credential_expired", "timed_out", "credential_expired", "failed"),
    ],
)
def test_transport_error_class_clamps_unknown_codes_and_statuses(
    code, status, expected_code, expected_status
):
    error = PlanTransportError(code, status)
    assert error.code == expected_code
    assert error.status == expected_status
    assert str(error) == expected_code
    assert TOKEN not in repr(error)
