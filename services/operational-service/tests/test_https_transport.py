"""Pinned HTTPS transport controls; fake sockets here never reach the network."""

from __future__ import annotations

import errno
import socket
import ssl
import tempfile
from pathlib import Path

import pytest
from operational_service.adapters.browser import https_transport as transport
from operational_service.adapters.browser.https_contracts import HttpsReadRefused

HOST = "fixture.example"
PIN = "8.8.8.8"


class Control:
    def __init__(self):
        self.remaining = 10.0
        self.code = None
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.code:
            raise HttpsReadRefused(self.code)
        return self.remaining


class FakeRaw:
    def __init__(self):
        self.peer = (PIN, 443)
        self.connected = []
        self.blocking = []
        self.closed = 0
        self.connection_error = 0
        self.socket_errors = [0]
        self.after_connect = lambda: None
        self.after_close = lambda: None

    def setblocking(self, value):
        self.blocking.append(value)

    def connect_ex(self, address):
        self.connected.append(address)
        self.after_connect()
        return self.connection_error

    def getsockopt(self, level, option):
        assert (level, option) == (socket.SOL_SOCKET, socket.SO_ERROR)
        return self.socket_errors.pop(0)

    def getpeername(self):
        return self.peer

    def close(self):
        self.closed += 1
        self.after_close()


class FakeTls(FakeRaw):
    def __init__(self):
        super().__init__()
        self.handshakes = []
        self.handshake_calls = 0
        self.sends = []
        self.receives = [b"body"]
        self.sent = []
        self.read_sizes = []
        self.after_handshake = lambda: None
        self.after_send = lambda: None
        self.after_receive = lambda: None

    def do_handshake(self):
        self.handshake_calls += 1
        step = self.handshakes.pop(0) if self.handshakes else None
        if isinstance(step, BaseException):
            raise step
        self.after_handshake()

    def send(self, data):
        self.sent.append(bytes(data))
        step = self.sends.pop(0) if self.sends else len(data)
        if isinstance(step, BaseException):
            raise step
        self.after_send()
        return step

    def recv(self, maximum):
        self.read_sizes.append(maximum)
        step = self.receives.pop(0)
        if isinstance(step, BaseException):
            raise step
        self.after_receive()
        return step


class FakeContext:
    verify_mode = ssl.CERT_REQUIRED
    check_hostname = True
    minimum_version = ssl.TLSVersion.TLSv1_2
    keylog_filename = None

    def __init__(self, stream):
        self.stream = stream
        self.wraps = []
        self.after_wrap = lambda: None

    def wrap_socket(self, raw, **kwargs):
        self.wraps.append((raw, kwargs))
        self.after_wrap()
        return self.stream


@pytest.fixture
def sockets(monkeypatch):
    control, raw, stream = Control(), FakeRaw(), FakeTls()
    context = FakeContext(stream)
    creations, polls = [], []

    def create(family, kind):
        creations.append((family, kind))
        return raw

    def poll(readable, writable, exceptional, interval):
        polls.append((readable, writable, exceptional, interval))
        assert 0 < interval <= 0.1
        return readable, writable, []

    monkeypatch.setattr(transport.socket, "socket", create)
    monkeypatch.setattr(transport, "_client_context", lambda: context)
    monkeypatch.setattr(transport.select, "select", poll)
    return control, raw, stream, context, creations, polls


def _connection(sockets):
    return transport.PinnedTlsConnection(HOST, PIN, sockets[0])


def _error(action, code):
    with pytest.raises(HttpsReadRefused, match=f"^{code}$") as error:
        action()
    assert error.value.code == code
    assert "private-marker" not in str(error.value)
    assert HOST not in str(error.value) and PIN not in str(error.value)
    return error.value


@pytest.mark.parametrize("host", [None, "", "localhost", "127.0.0.1", "Fixture.example",
                                   "private-marker@fixture.example", "fixture.example\r\n"])
def test_invalid_hostname_refuses_before_socket_creation(sockets, host):
    _error(lambda: transport.PinnedTlsConnection(host, PIN, sockets[0]),
           "invalid_https_transport")
    assert not sockets[4]


@pytest.mark.parametrize("pin", [None, "", "127.0.0.1", "10.0.0.1", "169.254.169.254",
                                  "192.0.2.1", "8.8.8.08", "fixture.example", "::1"])
def test_invalid_pin_refuses_before_socket_creation(sockets, pin):
    _error(lambda: transport.PinnedTlsConnection(HOST, pin, sockets[0]),
           "invalid_https_transport")
    assert not sockets[4]


def test_enter_revalidates_pin_before_network_after_mutation(sockets):
    connection = _connection(sockets)
    connection._pin = "127.0.0.1"
    _error(connection.__enter__, "invalid_https_transport")
    assert not sockets[4]


@pytest.mark.parametrize("remaining", [None, True, False, "private-marker", float("nan"),
                                        float("inf"), 10**400])
def test_invalid_deadline_callback_refuses_before_socket(sockets, remaining):
    sockets[0].remaining = remaining
    _error(_connection(sockets).__enter__, "invalid_https_transport")
    assert not sockets[4]


@pytest.mark.parametrize("code", ["cancelled", "deadline_exceeded", "invalid_clock"])
def test_control_refusals_before_dial_are_preserved_without_io(sockets, code):
    sockets[0].code = code
    _error(_connection(sockets).__enter__, code)
    assert not sockets[4]


@pytest.mark.parametrize("remaining", [0, -1])
def test_nonpositive_remaining_time_never_dials(sockets, remaining):
    sockets[0].remaining = remaining
    _error(_connection(sockets).__enter__, "deadline_exceeded")
    assert not sockets[4]


def test_throwing_deadline_callback_is_sanitized(sockets):
    def private_error():
        raise RuntimeError("private-marker callback failed")

    _error(lambda: transport.PinnedTlsConnection(HOST, PIN, private_error).__enter__(),
           "invalid_https_transport")
    assert not sockets[4]


def test_unknown_control_error_is_sanitized(sockets):
    sockets[0].code = "private-marker"
    _error(_connection(sockets).__enter__, "invalid_https_transport")


def test_numeric_pin_sni_and_single_owned_connection_ignore_dns_and_proxies(sockets, monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://private-marker.invalid:9999")
    monkeypatch.setenv("ALL_PROXY", "http://private-marker.invalid:9999")
    monkeypatch.setattr(transport.socket, "getaddrinfo",
                        lambda *a, **kw: pytest.fail("transport resolved DNS"))
    monkeypatch.setattr(transport.socket, "create_connection",
                        lambda *a, **kw: pytest.fail("transport used hostname connection helper"))
    control, raw, stream, context, creations, polls = sockets
    with _connection(sockets) as connection:
        connection.send(b"GET / HTTP/1.1\r\nHost: fixture.example\r\n\r\n")
        assert connection.receive(8) == b"body"
    assert creations == [(socket.AF_INET, socket.SOCK_STREAM)]
    assert raw.connected == [(PIN, 443)] and raw.blocking == [False]
    assert stream.blocking == [False] and not polls
    assert context.wraps == [(raw, {"server_hostname": HOST, "do_handshake_on_connect": False,
                                   "suppress_ragged_eofs": True})]
    assert raw.closed == stream.closed == 1 and control.calls > 10


def test_native_client_context_does_not_activate_environment_keylog(monkeypatch):
    with tempfile.TemporaryDirectory(prefix="jarvis-https-context-test-") as runtime:
        keylog = Path(runtime) / "private-marker-keylog.txt"
        monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
        monkeypatch.setattr(ssl, "create_default_context",
                            lambda *a, **kw: pytest.fail("inherited keylog helper used"))
        context = transport._client_context()
        assert context.protocol == ssl.PROTOCOL_TLS_CLIENT
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True
        assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
        assert context.keylog_filename is None and not keylog.exists()


@pytest.mark.parametrize("field,value", [
    ("verify_mode", ssl.CERT_NONE), ("check_hostname", False),
    ("minimum_version", ssl.TLSVersion.TLSv1_1),
    ("keylog_filename", "private-marker"),
])
def test_weakened_internal_context_is_refused_and_raw_socket_closed(sockets, field, value):
    setattr(sockets[3], field, value)
    _error(_connection(sockets).__enter__, "https_tls_refused")
    assert sockets[1].closed == 1 and sockets[2].closed == 0
    assert not sockets[3].wraps


def test_nonblocking_connect_polls_one_address_without_retry(sockets):
    sockets[1].connection_error = errno.EINPROGRESS
    sockets[1].socket_errors = [errno.EWOULDBLOCK, 0]
    with _connection(sockets):
        pass
    assert sockets[1].connected == [(PIN, 443)]
    assert len(sockets[4]) == 1 and len(sockets[5]) == 2
    assert all(not poll[0] and poll[1] == [sockets[1]] for poll in sockets[5])


def test_empty_connect_poll_cannot_be_mistaken_for_connected(sockets, monkeypatch):
    raw = sockets[1]
    raw.connection_error = errno.EINPROGRESS
    calls = []

    def poll(readable, writable, exceptional, timeout):
        calls.append(timeout)
        return ([], [], []) if len(calls) == 1 else ([], writable, [])

    monkeypatch.setattr(transport.select, "select", poll)
    with _connection(sockets):
        pass
    assert len(calls) == 2 and raw.socket_errors == []


@pytest.mark.parametrize("failure", [errno.ECONNREFUSED, errno.EHOSTUNREACH, True, None])
def test_connect_failure_closes_only_attempt_without_retry(sockets, failure):
    sockets[1].connection_error = failure
    _error(_connection(sockets).__enter__, "https_connect_refused")
    assert sockets[1].closed == 1 and len(sockets[4]) == 1
    assert not sockets[3].wraps


@pytest.mark.parametrize("where", ["raw", "tls"])
def test_peer_must_equal_actual_dial_address_before_using_connection(sockets, where):
    sockets[1 if where == "raw" else 2].peer = ("1.1.1.1", 443)
    _error(_connection(sockets).__enter__,
           "https_connect_refused" if where == "raw" else "https_tls_refused")
    assert sockets[1].closed == 1
    assert sockets[2].closed == (0 if where == "raw" else 1)


def test_private_loopback_dial_is_only_a_test_seam_and_peer_still_bound(sockets, monkeypatch):
    address = ("127.0.0.1", 32123)
    monkeypatch.setattr(transport, "_dial_address", lambda pin: address)
    sockets[1].peer = sockets[2].peer = address
    with _connection(sockets):
        pass
    assert sockets[1].connected == [address]


def test_hostname_in_dial_seam_is_refused_before_socket(sockets, monkeypatch):
    monkeypatch.setattr(transport, "_dial_address", lambda pin: ("private-marker.invalid", 443))
    _error(_connection(sockets).__enter__, "https_connect_refused")
    assert not sockets[4]


def test_handshake_want_read_write_both_poll_then_complete(sockets):
    stream = sockets[2]
    stream.handshakes = [ssl.SSLWantReadError(), ssl.SSLWantWriteError(), None]
    with _connection(sockets):
        pass
    assert stream.handshake_calls == 3
    assert sockets[5][0][0] == [stream] and not sockets[5][0][1]
    assert sockets[5][1][1] == [stream] and not sockets[5][1][0]


@pytest.mark.parametrize("error", [ssl.SSLCertVerificationError("private-marker"),
                                  ssl.SSLError("private-marker"), OSError("private-marker")])
def test_tls_failure_never_leaks_hostname_certificate_or_socket_details(sockets, error):
    sockets[2].handshakes = [error]
    _error(_connection(sockets).__enter__, "https_tls_refused")
    assert sockets[1].closed == sockets[2].closed == 1


@pytest.mark.parametrize("boundary", ["connect", "wrap", "handshake", "send", "receive"])
@pytest.mark.parametrize("code", ["cancelled", "deadline_exceeded"])
def test_late_control_after_successful_io_is_refused_and_closes_socket(sockets, boundary, code):
    control, raw, stream, context, *_ = sockets
    setattr({"connect": raw, "wrap": context, "handshake": stream,
             "send": stream, "receive": stream}[boundary], f"after_{boundary}",
            lambda: setattr(control, "code", code))
    if boundary in {"connect", "wrap", "handshake"}:
        _error(_connection(sockets).__enter__, code)
    else:
        connection = _connection(sockets).__enter__()
        _error(lambda: connection.send(b"GET /\r\n") if boundary == "send"
               else connection.receive(8), code)
    assert raw.closed == 1
    if boundary != "connect":
        assert stream.closed == 1


def test_cancel_during_select_does_not_complete_handshake(sockets, monkeypatch):
    sockets[2].handshakes = [ssl.SSLWantReadError()]

    def poll(readable, writable, exceptional, timeout):
        sockets[0].code = "cancelled"
        return readable, writable, []

    monkeypatch.setattr(transport.select, "select", poll)
    _error(_connection(sockets).__enter__, "cancelled")
    assert sockets[2].handshake_calls == 1
    assert sockets[1].closed == sockets[2].closed == 1


def test_send_partial_want_read_write_does_not_repeat_already_sent_bytes(sockets):
    stream = sockets[2]
    stream.sends = [2, ssl.SSLWantWriteError(), ssl.SSLWantReadError(), 2, 2]
    with _connection(sockets) as connection:
        connection.send(b"abcdef")
    assert stream.sent == [b"abcdef", b"cdef", b"cdef", b"cdef", b"ef"]
    assert len(sockets[5]) == 2


@pytest.mark.parametrize("written", [0, -1, True, None, 99999])
def test_invalid_partial_send_refuses_and_closes_socket(sockets, written):
    connection = _connection(sockets).__enter__()
    sockets[2].sends = [written]
    _error(lambda: connection.send(b"GET /\r\n"), "https_io_refused")
    assert sockets[1].closed == sockets[2].closed == 1


def test_receive_want_read_write_eof_and_read_cap(sockets):
    stream = sockets[2]
    stream.receives = [ssl.SSLWantReadError(), ssl.SSLWantWriteError(), b"body", b""]
    with _connection(sockets) as connection:
        assert connection.receive(10**100) == b"body"
        assert connection.receive(4) == b""
    assert stream.read_sizes == [65536, 65536, 65536, 4]
    assert len(sockets[5]) == 2


@pytest.mark.parametrize("maximum", [0, -1, True, False, None, "private-marker", 4.0])
def test_receive_invalid_maximum_does_not_read_and_closes(sockets, maximum):
    connection = _connection(sockets).__enter__()
    _error(lambda: connection.receive(maximum), "invalid_https_transport")
    assert not sockets[2].read_sizes
    assert sockets[1].closed == sockets[2].closed == 1


@pytest.mark.parametrize("data", [None, "private-marker", bytearray(b"GET"), memoryview(b"GET")])
def test_send_invalid_data_does_not_write_and_closes(sockets, data):
    connection = _connection(sockets).__enter__()
    _error(lambda: connection.send(data), "invalid_https_transport")
    assert not sockets[2].sent
    assert sockets[1].closed == sockets[2].closed == 1


@pytest.mark.parametrize("received", [None, bytearray(b"body"), "private-marker", b"too-long"])
def test_received_bytes_must_match_bounded_binary_contract(sockets, received):
    connection = _connection(sockets).__enter__()
    sockets[2].receives = [received]
    _error(lambda: connection.receive(4), "https_io_refused")


def test_exit_checks_deadline_after_socket_cleanup(sockets):
    connection = _connection(sockets).__enter__()
    sockets[1].after_close = lambda: setattr(sockets[0], "remaining", 0)
    _error(lambda: connection.__exit__(None, None, None), "deadline_exceeded")
    assert sockets[1].closed == sockets[2].closed == 1


def test_closed_context_cannot_redial_or_read_and_repr_contains_no_target(sockets):
    connection = _connection(sockets)
    with connection:
        pass
    _error(connection.__enter__, "invalid_https_transport")
    _error(lambda: connection.receive(8), "invalid_https_transport")
    _error(lambda: connection.send(b"GET /"), "invalid_https_transport")
    assert len(sockets[4]) == 1
    assert HOST not in repr(connection) and PIN not in repr(connection)


@pytest.mark.parametrize("boundary", ["context", "wrap", "raw_nonblocking", "tls_nonblocking"])
def test_initialization_failure_closes_every_acquired_socket(sockets, monkeypatch, boundary):
    def private_error(*args, **kwargs):
        raise OSError("private-marker initialization failed")

    if boundary == "context":
        monkeypatch.setattr(transport, "_client_context", private_error)
    elif boundary == "wrap":
        sockets[3].wrap_socket = private_error
    elif boundary == "raw_nonblocking":
        sockets[1].setblocking = private_error
    else:
        sockets[2].setblocking = private_error
    _error(_connection(sockets).__enter__,
           "https_connect_refused" if boundary == "raw_nonblocking" else "https_tls_refused")
    assert sockets[1].closed == 1
    assert sockets[2].closed == (1 if boundary == "tls_nonblocking" else 0)


@pytest.mark.parametrize("operation", ["send", "receive"])
def test_private_io_failures_are_sanitized_and_close_both_sockets(sockets, operation):
    connection = _connection(sockets).__enter__()
    if operation == "send":
        sockets[2].sends = [OSError("private-marker send failed")]
        _error(lambda: connection.send(b"GET /"), "https_io_refused")
    else:
        sockets[2].receives = [OSError("private-marker read failed")]
        _error(lambda: connection.receive(8), "https_io_refused")
    assert sockets[1].closed == sockets[2].closed == 1


def test_select_exception_is_sanitized_and_never_retries_a_connection(sockets, monkeypatch):
    sockets[1].connection_error = errno.EINPROGRESS

    def private_error(*args, **kwargs):
        raise OSError("private-marker select failed")

    monkeypatch.setattr(transport.select, "select", private_error)
    _error(_connection(sockets).__enter__, "https_connect_refused")
    assert sockets[1].closed == 1 and len(sockets[4]) == 1


def test_exceptional_select_is_refused_without_attempting_tls(sockets, monkeypatch):
    sockets[1].connection_error = errno.EINPROGRESS
    monkeypatch.setattr(transport.select, "select",
                        lambda readable, writable, exceptional, timeout: ([], [], exceptional))
    _error(_connection(sockets).__enter__, "https_connect_refused")
    assert not sockets[3].wraps and sockets[1].closed == 1


def test_cleanup_failure_is_sanitized_and_does_not_skip_other_owned_socket(sockets):
    connection = _connection(sockets).__enter__()

    def private_error():
        raise OSError("private-marker close failed")

    sockets[2].after_close = private_error
    _error(lambda: connection.__exit__(None, None, None), "https_io_refused")
    assert sockets[1].closed == sockets[2].closed == 1


def test_parser_failure_is_not_masked_by_cleanup_or_a_later_control_error(sockets):
    connection = _connection(sockets).__enter__()
    sockets[0].code = "cancelled"
    assert connection.__exit__(HttpsReadRefused, HttpsReadRefused("invalid_http"), None) is False
    assert sockets[1].closed == sockets[2].closed == 1


@pytest.mark.parametrize("field,value", [
    ("_hostname", "private-marker.example"), ("_pin", "1.1.1.1"),
    ("_check_callback", lambda: 60.0),
])
def test_first_control_callback_cannot_rebind_destination_or_deadline(sockets, field, value):
    calls = []
    connection = None

    def callback():
        calls.append("original")
        setattr(connection, field, value)
        return 10.0

    connection = transport.PinnedTlsConnection(HOST, PIN, callback)
    _error(connection.__enter__, "invalid_https_transport")
    assert calls == ["original"] and not sockets[4]


@pytest.mark.parametrize("field,value", [
    ("_hostname", "private-marker.example"), ("_pin", "1.1.1.1"),
    ("_check_callback", lambda: 60.0),
])
def test_io_callback_rebinding_cannot_continue_handshake_or_change_sni(sockets, field, value):
    connection = _connection(sockets)
    sockets[1].after_connect = lambda: setattr(connection, field, value)
    _error(connection.__enter__, "invalid_https_transport")
    assert sockets[1].connected == [(PIN, 443)]
    assert not sockets[3].wraps
    assert sockets[1].closed == 1
