"""Content-free phase diagnostics over deterministic socket seams; no network/model."""

from __future__ import annotations

from threading import Event

import pytest
from inference_service import local_chat_transport as transport

PHASES = (
    "connect_complete", "request_sent", "first_byte", "headers_validated",
    "body_complete", "peer_closed",
)
PAYLOAD = {"model": "private-model", "n": 1, "stream": False,
           "messages": [{"role": "user", "content": "PRIVATE_PROMPT"}]}


class Clock:
    def __init__(self):
        self.now = 0.0
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.now


def _socket_seam(monkeypatch, *, chunked=False, tail=b"", incomplete=False):
    clock = Clock()
    body = b'"PRIVATE_RESPONSE"'
    if chunked:
        head = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        head += b"Transfer-Encoding: chunked\r\n\r\n"
        first = head + f"{len(body):x}\r\n".encode("ascii") + body + b"\r\n"
        last = b"0\r\n\r\n"
    else:
        head = b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
        head += f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        first, last = head + body[:3], body[3:]
    pieces = [(3.0, first)]
    if not incomplete:
        pieces.append((4.0, last))
    if tail:
        pieces.append((5.0, tail))
    pieces.append((6.0, b""))

    class Connection:
        closed = False
        receives = 0

        def setblocking(self, value):
            assert value is False

        def connect_ex(self, address):
            assert address == ("127.0.0.1", 11434)
            clock.now = 1.0
            return 0

        def getsockopt(self, *_args):
            return 0

        def send(self, data):
            clock.now = 2.0
            return len(data)

        def recv(self, size):
            assert size == 8192
            self.receives += 1
            clock.now, value = pieces.pop(0)
            return value

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(transport.socket, "socket", lambda *_args: connection)
    monkeypatch.setattr(transport.select, "select",
                        lambda readable, writable, _errors, _timeout: (readable, writable, []))
    return clock, connection, body


def test_phase_observer_is_explicit_and_default_off_without_extra_clock_calls(monkeypatch):
    counts = []
    for options in ({}, {"phase_observer": None}):
        clock, connection, expected = _socket_seam(monkeypatch)
        client = transport.LocalChatHttpTransport(
            endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock, **options,
        )
        assert client(PAYLOAD, timeout_seconds=30, cancellation=Event()) == expected
        assert connection.closed
        counts.append(clock.calls)
    assert counts[0] == counts[1]


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_success_phases_are_ordered_bounded_content_free_and_wait_for_peer_close(
    monkeypatch, chunked,
):
    clock, connection, expected = _socket_seam(monkeypatch, chunked=chunked)
    events = []
    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock,
        phase_observer=events.append,
    )
    assert client(PAYLOAD, timeout_seconds=30, cancellation=Event()) == expected
    assert connection.closed and connection.receives == 3
    assert [event["phase"] for event in events] == list(PHASES)
    assert [event["elapsed_ms"] for event in events] == [1000, 2000, 3000, 3000, 4000, 6000]
    for event in events:
        assert set(event) == {"event", "phase", "elapsed_ms", "timing_mode"}
        assert event["event"] == "local_inference_phase"
        assert event["timing_mode"] == "injected_clock"
        assert type(event["elapsed_ms"]) is int and 0 <= event["elapsed_ms"] <= 120_000
        assert "PRIVATE" not in repr(event) and "11434" not in repr(event)


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("action,code", [
    ("cancel", "cancelled"), ("deadline", "timeout"),
    ("configuration", "configuration_changed"), ("observer", "configuration_changed"),
])
def test_every_observer_is_followed_by_cancellation_deadline_and_binding_fences(
    monkeypatch, phase, action, code,
):
    clock, connection, _expected = _socket_seam(monkeypatch)
    token = Event()
    events = []

    def observe(event):
        events.append(event)
        if event["phase"] != phase:
            return
        if action == "cancel":
            token.set()
        elif action == "deadline":
            clock.now = 30.0
        elif action == "configuration":
            client._port = 80
        else:
            client._phase_observer = None
        raise RuntimeError("PRIVATE_OBSERVER_EXCEPTION")

    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock,
        phase_observer=observe,
    )
    with pytest.raises(transport.LocalChatTransportError) as caught:
        client(PAYLOAD, timeout_seconds=30, cancellation=token)
    assert caught.value.code == code and str(caught.value) == code
    assert connection.closed
    assert [event["phase"] for event in events] == list(PHASES[:PHASES.index(phase) + 1])


def test_ordinary_observer_exception_does_not_change_transport_result(monkeypatch):
    clock, connection, expected = _socket_seam(monkeypatch)

    def observe(_event):
        raise RuntimeError("PRIVATE_OBSERVER_EXCEPTION")

    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock,
        phase_observer=observe,
    )
    assert client(PAYLOAD, timeout_seconds=30, cancellation=Event()) == expected
    assert connection.closed


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_body_complete_never_accepts_late_extra_bytes(monkeypatch, chunked):
    clock, connection, _expected = _socket_seam(monkeypatch, chunked=chunked, tail=b"PRIVATE_TAIL")
    events = []
    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock,
        phase_observer=events.append,
    )
    with pytest.raises(transport.LocalChatTransportError, match="^invalid_http_response$"):
        client(PAYLOAD, timeout_seconds=30, cancellation=Event())
    assert connection.closed
    assert [event["phase"] for event in events] == list(PHASES[:-1])


@pytest.mark.parametrize("chunked", [False, True], ids=["content-length", "chunked"])
def test_incomplete_body_reports_peer_close_without_body_complete(monkeypatch, chunked):
    clock, connection, _expected = _socket_seam(monkeypatch, chunked=chunked, incomplete=True)
    events = []
    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", clock=clock,
        phase_observer=events.append,
    )
    with pytest.raises(transport.LocalChatTransportError, match="^response_interrupted$"):
        client(PAYLOAD, timeout_seconds=30, cancellation=Event())
    assert connection.closed
    assert [event["phase"] for event in events] == [*PHASES[:4], "peer_closed"]


@pytest.mark.parametrize("observer", [False, 1, "callback", object()])
def test_invalid_phase_observer_is_refused_at_inert_construction(observer):
    with pytest.raises(ValueError, match="^invalid_local_chat_phase_observer$"):
        transport.LocalChatHttpTransport(
            endpoint="http://127.0.0.1:11434/v1/chat/completions", phase_observer=observer,
        )


def test_phase_observer_rebinding_before_call_is_refused_before_socket(monkeypatch):
    def forbidden_socket(*_args):
        pytest.fail("configuration change reached socket construction")

    monkeypatch.setattr(transport.socket, "socket", forbidden_socket)
    client = transport.LocalChatHttpTransport(
        endpoint="http://127.0.0.1:11434/v1/chat/completions", phase_observer=lambda _event: None,
    )
    client._phase_observer = None
    with pytest.raises(transport.LocalChatTransportError, match="^configuration_changed$"):
        client(PAYLOAD, timeout_seconds=30, cancellation=Event())
