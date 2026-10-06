"""Actual IPv4 loopback evidence with synthetic callbacks; no OAuth account."""

from __future__ import annotations

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from inference_service.oauth_flow import SiwcAuthorizationFlow
from inference_service.oauth_listener import SiwcLoopbackListener
from inference_service.siwc_contracts import SiwcError

HOST = "urn:uuid:3ab59e96-7cd8-4eb1-9161-ebd1e10e5499"


@pytest.fixture(autouse=True)
def never_browser(monkeypatch):
    import webbrowser

    def refused(*args, **kwargs):
        raise AssertionError("browser must never open during loopback tests")

    monkeypatch.setattr(webbrowser, "open", refused)


def request(uri, target, *, headers=None, method="GET", extra=b""):
    parts = urlsplit(uri)
    headers = headers if headers is not None else [("Host", parts.netloc)]
    data = f"{method} {target} HTTP/1.1\r\n"
    data += "".join(f"{key}: {value}\r\n" for key, value in headers) + "\r\n"
    return send_raw(uri, data.encode("ascii") + extra)


def send_raw(uri, data):
    port = urlsplit(uri).port
    with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
        client.sendall(data)
        chunks = []
        while True:
            try:
                block = client.recv(4096)
            except ConnectionResetError:
                break
            if not block:
                break
            chunks.append(block)
        return b"".join(chunks)


def flow_and_attempt(listener):
    flow = SiwcAuthorizationFlow(host_id=HOST)
    attempt = flow.begin(redirect_uri=listener.redirect_uri, authorized=True,
                         timeout_seconds=5)
    query = parse_qs(urlsplit(attempt.authorization_url).query)
    target = "/auth/callback?" + urlencode({"state": query["state"][0],
                                           "code": "private-fixture-code",
                                           "client_id": "oaiapp_loopback"})
    return flow, attempt, target


def test_actual_loopback_callback_then_oauth_flow(capsys):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        assert uri.startswith("http://127.0.0.1:") and uri.endswith("/auth/callback")
        flow, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            response = request(uri, target)
            callback = future.result(timeout=3)
        assert callback == uri.removesuffix("/auth/callback") + target
        assert flow.finish(attempt, callback).client_id == "oaiapp_loopback"
        assert response.startswith(b"HTTP/1.1 200 OK")
        for header in (b"Cache-Control: no-store", b"Content-Security-Policy: default-src 'none'",
                       b"Referrer-Policy: no-referrer", b"Connection: close"):
            assert header in response
        assert b"validation pending" in response
        assert b"private-fixture-code" not in response
        assert b"state=" not in response and b"client_id=" not in response
        with pytest.raises(SiwcError, match="siwc_listener_state_invalid"):
            listener.receive(attempt)
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


@pytest.mark.parametrize("bad_headers", [
    [], [("Host", "localhost:1234")], [("Host", "evil.example")],
    [("Host", "{host}"), ("Host", "{host}")],
    [("Host", "{host}"), ("hOsT", "{host}")],
    [("Host", "{host}"), ("Origin", "https://auth.openai.com")],
    [("Host", "{host}"), ("Origin", "null")],
    [("Host", "{host}"), ("Origin", "{origin}"), ("Origin", "{origin}")],
    [("Host", "{host}"), ("Transfer-Encoding", "chunked")],
    [("Host", "{host}"), ("Content-Length", "1")],
    [("Host", "{host}"), ("X-Extra", "bad\tvalue")],
    [("Host", "{host}"), ("X-Extra", "bad\x7fvalue")],
])
def test_host_origin_header_checks_before_candidate(bad_headers):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        parts = urlsplit(uri)
        headers = [(key, value.replace("{host}", parts.netloc)
                    .replace("{origin}", "http://" + parts.netloc)) for key, value in bad_headers]
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            assert request(uri, target, headers=headers).startswith(b"HTTP/1.1 400")
            assert request(uri, target).startswith(b"HTTP/1.1 200")
            assert future.result(timeout=3).endswith(target)


def test_matching_optional_origin_accepted():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        host = urlsplit(uri).netloc
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            response = request(uri, target, headers=[("Host", host), ("Origin", "http://" + host)])
            assert response.startswith(b"HTTP/1.1 200")
            assert future.result(timeout=3).endswith(target)


@pytest.mark.parametrize("bad_target", [
    "/", "/callback?code=private", "/auth/callback", "/auth/callback/?code=private",
    "/x/../auth/callback?code=private", "/%61uth/callback?code=private",
    "/auth/callback?code=private#fragment", "http://evil.example/auth/callback?code=private",
    "/auth/callback?code=bad\x7f", "/auth/callback?code=" + "a" * 32768,
], ids=["root", "wrong-path", "no-query", "slash", "traversal", "encoded-path",
        "fragment", "absolute-target", "control", "oversize"])
def test_path_query_guards_before_candidate(bad_target):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            assert request(uri, bad_target).startswith(b"HTTP/1.1 400")
            request(uri, target)
            assert future.result(timeout=3).endswith(target)


@pytest.mark.parametrize("method", ["POST", "HEAD", "PUT", "DELETE", "OPTIONS"])
def test_other_methods_never_callback(method):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            assert request(uri, target, method=method).startswith(b"HTTP/1.1 405")
            request(uri, target)
            assert future.result(timeout=3).endswith(target)


@pytest.mark.parametrize("raw", [
    b"GET / HTTP/1.1\r\n malformed\r\n\r\n",
    b"GET / HTTP/1.1\r\nHost: bad\r\n\r\nBODY",
    b"GET / HTTP/1.1\r\nHost: bad\r\nX: \xff\r\n\r\n",
    b"GET / HTTP/1.1\r\nHost: bad\r\nX: " + b"a" * 8192 + b"\r\n\r\n",
    b"GET / HTTP/1.1\r\n" + b"X: a\r\n" * 34 + b"\r\n",
], ids=["folded", "body", "non-ascii", "big-header", "many-headers"])
def test_raw_request_budgets(raw):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            assert send_raw(uri, raw).startswith(b"HTTP/1.1 400")
            request(uri, target)
            assert future.result(timeout=3).endswith(target)


def test_slow_request_bounded_then_can_receive_valid_request():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            with socket.create_connection(("127.0.0.1", urlsplit(uri).port), timeout=3) as client:
                client.sendall(b"GET /auth/callback?")
                assert client.recv(4096).startswith(b"HTTP/1.1 400")
            request(uri, target)
            assert future.result(timeout=3).endswith(target)


def test_request_limit_and_port_closed():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, _ = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            for _ in range(16):
                assert request(uri, "/").startswith(b"HTTP/1.1 400")
            with pytest.raises(SiwcError, match="siwc_listener_request_limit"):
                future.result(timeout=3)
        with pytest.raises(OSError):
            socket.create_connection(("127.0.0.1", urlsplit(uri).port), timeout=0.1)


def test_idle_timeout():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=0.02) as listener:
        _, attempt, _ = flow_and_attempt(listener)
        started = time.monotonic()
        with pytest.raises(SiwcError, match="siwc_listener_timeout"):
            listener.receive(attempt)
        assert time.monotonic() - started < 2


def test_cancellation():
    cancellation = threading.Event()
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5,
                              cancellation=cancellation) as listener:
        _, attempt, _ = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            cancellation.set()
            with pytest.raises(SiwcError, match="siwc_listener_cancelled"):
                future.result(timeout=3)


def test_expired_attempt_not_received():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        _, attempt, _ = flow_and_attempt(listener)
        with pytest.raises(SiwcError, match="siwc_listener_timeout"):
            listener.receive(replace(attempt, deadline=time.monotonic() - 1))


def test_mismatched_redirect_refused():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        flow = SiwcAuthorizationFlow(host_id=HOST)
        attempt = flow.begin(redirect_uri="http://127.0.0.1:1/auth/callback", authorized=True)
        with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
            listener.receive(attempt)


def test_constructor_no_io(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("construction must not bind")

    monkeypatch.setattr(socket, "socket", refused)
    listener = SiwcLoopbackListener()
    assert repr(listener) == "SiwcLoopbackListener()"
    with pytest.raises(SiwcError, match="siwc_listener_state_invalid"):
        _ = listener.redirect_uri
    with pytest.raises(SiwcError, match="siwc_authorization_required"):
        listener.__enter__()


def test_context_lifecycle():
    listener = SiwcLoopbackListener(authorized=True)
    with listener:
        with pytest.raises(SiwcError, match="siwc_listener_state_invalid"):
            listener.__enter__()
    with pytest.raises(SiwcError, match="siwc_listener_state_invalid"):
        listener.__enter__()
    listener.close()


@pytest.mark.parametrize("kwargs", [{"authorized": 1}, {"timeout_seconds": 0},
                                   {"timeout_seconds": 601}, {"timeout_seconds": True},
                                   {"timeout_seconds": float("nan")}, {"port": -1},
                                   {"port": 65536}, {"port": True}, {"cancellation": "bad"},
                                   {"clock": None}])
def test_config_guards(kwargs):
    with pytest.raises(SiwcError, match="siwc_listener_invalid"):
        SiwcLoopbackListener(**kwargs)


def test_pre_cancelled_no_bind(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("cancelled listener must not bind")

    cancellation = threading.Event()
    cancellation.set()
    monkeypatch.setattr(socket, "socket", refused)
    with pytest.raises(SiwcError, match="siwc_listener_cancelled"):
        with SiwcLoopbackListener(authorized=True, cancellation=cancellation):
            pass


def test_bind_error_private_message_not_exposed(monkeypatch):
    def refused(*args, **kwargs):
        raise OSError("private path and OS detail")

    monkeypatch.setattr(socket, "socket", refused)
    with pytest.raises(SiwcError) as error:
        with SiwcLoopbackListener(authorized=True):
            pass
    assert str(error.value) == "siwc_listener_unavailable"
    assert "private" not in repr(error.value)


def test_numerical_bind_never_reverse_dns(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("no reverse DNS required for numerical loopback")

    monkeypatch.setattr(socket, "getfqdn", refused)
    monkeypatch.setattr(socket, "gethostbyaddr", refused)
    with SiwcLoopbackListener(authorized=True) as listener:
        assert listener.redirect_uri.startswith("http://127.0.0.1:")


@pytest.mark.parametrize("query", ["%00", "%0A", "%7f", "%", "%zz", "%ff", "%C0%AF"])
def test_encoded_control_and_bad_utf8_before_candidate(query):
    with SiwcLoopbackListener(authorized=True, timeout_seconds=5) as listener:
        uri = listener.redirect_uri
        _, attempt, target = flow_and_attempt(listener)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(listener.receive, attempt)
            assert request(uri, "/auth/callback?state=" + query).startswith(b"HTTP/1.1 400")
            request(uri, target)
            assert future.result(timeout=3).endswith(target)


def test_close_failure_sanitized(monkeypatch):
    listener = SiwcLoopbackListener(authorized=True)
    listener.__enter__()
    real_close = listener._server.server_close

    def fail():
        real_close()
        raise OSError("private local endpoint detail")

    monkeypatch.setattr(listener._server, "server_close", fail)
    with pytest.raises(SiwcError) as error:
        listener.close()
    assert str(error.value) == "siwc_listener_close_failed"
    listener.close()


def test_replayed_receive_after_timeout_refused():
    with SiwcLoopbackListener(authorized=True, timeout_seconds=0.01) as listener:
        _, attempt, _ = flow_and_attempt(listener)
        with pytest.raises(SiwcError, match="siwc_listener_timeout"):
            listener.receive(attempt)
        with pytest.raises(SiwcError, match="siwc_listener_state_invalid"):
            listener.receive(attempt)
