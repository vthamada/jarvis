"""Real loopback HTTP, synthetic service only: no accounts, models or human stores."""

import http.client
import json
import socket
import threading

import pytest

from apps.jarvis_api.contracts import LocalWebRejected
from apps.jarvis_api.local_auth import LocalAuth
from apps.jarvis_api.local_server import COOKIE_NAME, CSP, MAX_REQUEST_THREADS, create_server

TICKET = "web-request-" + "a" * 32


class Clock:
    value = 100.0

    def __call__(self):
        return self.value


class FakeService:
    def __init__(self):
        self.calls = []
        self.ticket = None
        self.error = None
        self.after = None

    def _call(self, name, *args):
        self.calls.append((name, args))
        if self.error:
            raise self.error
        if self.after:
            self.after()

    def current_ticket(self, identity):
        self._call("current", identity)
        return self.ticket

    def issue_ticket(self, identity):
        self._call("issue", identity)
        self.ticket = TICKET
        return self.envelope("issued")

    def submit(self, identity, ticket, query):
        self._call("submit", identity, ticket, query)
        return self.envelope("running")

    def get_result(self, identity, ticket):
        self._call("get", identity, ticket)
        return self.envelope("completed", {"final_text": "Resposta sintética\r\n👋"})

    def revoke(self, identity):
        self._call("revoke", identity)

    @staticmethod
    def envelope(status, result=None):
        return {
            "schema_version": "jarvis-local-analysis-v1",
            "status": status,
            "ticket": TICKET,
            "error_code": None,
            "result": result,
        }


@pytest.fixture
def running():
    clock, service = Clock(), FakeService()
    auth = LocalAuth(clock=clock)
    server = create_server(service, auth=auth)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    context = {
        "server": server,
        "clock": clock,
        "service": service,
        "auth": auth,
        "origin": f"http://127.0.0.1:{server.server_port}",
    }
    yield context
    server.shutdown()
    auth.close()
    server.server_close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def request(
    ctx, method="GET", path="/api/session", body=None, *, headers=None, client=True, origin=True
):
    merged = {}
    if client:
        merged["X-Jarvis-Client"] = "local-web-v1"
    if origin and method == "POST":
        merged["Origin"] = ctx["origin"]
    if "cookie" in ctx:
        merged["Cookie"] = ctx["cookie"]
        merged["X-Jarvis-CSRF"] = ctx["csrf"]
    if type(body) is dict:
        body = json.dumps(body, ensure_ascii=True).encode("ascii")
        merged["Content-Type"] = "application/json"
    if headers:
        merged.update(headers)
    connection = http.client.HTTPConnection("127.0.0.1", ctx["server"].server_port, timeout=2)
    try:
        connection.request(method, path, body, merged)
        response = connection.getresponse()
        data = response.read()
        return response.status, dict(response.getheaders()), data
    finally:
        connection.close()


def pair(ctx):
    status, headers, data = request(
        ctx, "POST", "/api/pair", {"secret": ctx["auth"].pairing_secret}
    )
    assert status == 200
    payload = json.loads(data)
    ctx["cookie"] = headers["Set-Cookie"].split(";", 1)[0]
    ctx["csrf"] = payload["csrf_token"]
    return headers, payload


def raw(ctx, message):
    with socket.create_connection(
        ("127.0.0.1", ctx["server"].server_port), timeout=2
    ) as connection:
        connection.sendall(message)
        connection.shutdown(socket.SHUT_WR)
        data = bytearray()
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            data.extend(chunk)
        header, _, body = bytes(data).partition(b"\r\n\r\n")
        return int(header.split(b" ", 2)[1]), body


def test_real_http_pair_ticket_submit_poll_disconnect_exact_binding(running):
    ctx = running
    headers, payload = pair(ctx)
    assert set(payload) == {
        "schema_version",
        "authenticated",
        "session_ref",
        "csrf_token",
        "expires_in_seconds",
        "last_ticket",
    }
    assert payload["schema_version"] == "jarvis-local-session-v1"
    assert payload["expires_in_seconds"] == 900 and payload["last_ticket"] is None
    assert "HttpOnly; SameSite=Strict; Path=/; Max-Age=900" in headers["Set-Cookie"]
    assert "Secure" not in headers["Set-Cookie"]
    assert ctx["auth"].pairing_secret not in json.dumps(payload)
    status, _, data = request(ctx, "POST", "/api/tickets", {})
    assert status == 201 and json.loads(data) == FakeService.envelope("issued")
    query = "Compare documentação e observabilidade.\r\n👋"
    status, _, data = request(ctx, "POST", "/api/analysis", {"ticket": TICKET, "query": query})
    assert status == 202 and json.loads(data) == FakeService.envelope("running")
    status, _, data = request(ctx, path="/api/results/" + TICKET)
    assert status == 200 and json.loads(data)["result"]["final_text"] == "Resposta sintética\r\n👋"
    identities = [args[0] for name, args in ctx["service"].calls]
    assert all(item is identities[0] for item in identities)
    assert [args[-1] for name, args in ctx["service"].calls if name == "submit"] == [query]
    status, _, data = request(ctx)
    assert status == 200 and json.loads(data)["last_ticket"] == TICKET
    status, headers, data = request(ctx, "POST", "/api/disconnect", {})
    assert status == 200 and json.loads(data) == {"status": "disconnected"}
    assert "Max-Age=0" in headers["Set-Cookie"]
    assert ctx["service"].calls[-1][0] == "revoke"
    assert request(ctx)[0] == 401
    assert request(ctx, "POST", "/api/pair", {"secret": ctx["auth"].pairing_secret})[0] == 403


@pytest.mark.parametrize(
    "headers,code",
    [
        ({"Host": "localhost:1"}, "origin_refused"),
        ({"Host": "evil.example"}, "origin_refused"),
        ({"Origin": "https://evil.example"}, "origin_refused"),
        ({"Origin": "null"}, "origin_refused"),
        ({"Sec-Fetch-Site": "cross-site"}, "origin_refused"),
        ({"Sec-Fetch-Site": "same-site"}, "origin_refused"),
        ({"X-Jarvis-Client": "different"}, "client_refused"),
    ],
)
def test_pair_boundary_rejects_before_service(running, headers, code):
    status, _, data = request(
        running, "POST", "/api/pair", {"secret": running["auth"].pairing_secret}, headers=headers
    )
    assert status == 403 and json.loads(data) == {"error_code": code}
    assert running["service"].calls == []


@pytest.mark.parametrize("client,origin", [(False, True), (True, False)])
def test_pair_missing_required_headers(running, client, origin):
    assert (
        request(
            running,
            "POST",
            "/api/pair",
            {"secret": running["auth"].pairing_secret},
            client=client,
            origin=origin,
        )[0]
        == 403
    )
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/session"),
        ("GET", "/api/results/" + TICKET),
        ("POST", "/api/tickets"),
        ("POST", "/api/analysis"),
        ("POST", "/api/disconnect"),
    ],
)
def test_unpaired_api_never_reaches_service(running, method, path):
    status, _, data = request(running, method, path, {} if method == "POST" else None)
    assert status == 401 and json.loads(data) == {"error_code": "session_refused"}
    assert running["service"].calls == []


@pytest.mark.parametrize("csrf", ["", "0" * 64, "wrong", "A" * 64])
@pytest.mark.parametrize(
    "method,path",
    [("GET", "/api/results/" + TICKET), ("POST", "/api/tickets"), ("POST", "/api/disconnect")],
)
def test_csrf_exact_required_before_service(running, csrf, method, path):
    pair(running)
    running["service"].calls.clear()
    status, _, data = request(
        running, method, path, {} if method == "POST" else None, headers={"X-Jarvis-CSRF": csrf}
    )
    assert status == 403 and json.loads(data) == {"error_code": "csrf_refused"}
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "cookie",
    [
        "",
        "other=value",
        COOKIE_NAME + "=bad",
        COOKIE_NAME + "=" + "0" * 64,
        COOKIE_NAME + "=" + "0" * 64 + "; " + COOKIE_NAME + "=" + "0" * 64,
        "broken; foo=bar",
    ],
)
def test_cookie_missing_unknown_or_ambiguous(running, cookie):
    pair(running)
    running["service"].calls.clear()
    assert request(running, headers={"Cookie": cookie})[0] == 401
    assert running["service"].calls == []


@pytest.mark.parametrize("elapsed,expected", [(899, 200), (900, 401), (901, 401)])
def test_expired_session_http(running, elapsed, expected):
    pair(running)
    running["clock"].value += elapsed
    assert request(running)[0] == expected


def test_session_get_origin_optional_but_cross_origin_refused(running):
    pair(running)
    assert request(running)[0] == 200
    assert (
        request(running, headers={"Origin": running["origin"], "Sec-Fetch-Site": "same-origin"})[0]
        == 200
    )
    assert request(running, headers={"Origin": "http://evil.example"})[0] == 403
    assert request(running, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    assert request(running, client=False)[0] == 403


@pytest.mark.parametrize(
    "body",
    [
        b"",
        b"null",
        b"[]",
        b"{",
        b'{"secret":"a","secret":"b"}',
        b'{"secret":"\xff"}',
        b'{"secret":"x","extra":1}',
        b'{"secret":NaN}',
        b'{"secret":Infinity}',
    ],
)
def test_json_invalid_content_free(running, body):
    status, _, data = request(
        running, "POST", "/api/pair", body, headers={"Content-Type": "application/json"}
    )
    assert status == 400 and json.loads(data) == {"error_code": "request_invalid"}
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "content_type", ["text/plain", "application/json; charset=latin1", "", "multipart/form-data"]
)
def test_content_type_rejected(running, content_type):
    assert (
        request(running, "POST", "/api/pair", b"{}", headers={"Content-Type": content_type})[0]
        == 400
    )


def test_oversized_body_rejected_without_service(running):
    status, _, data = request(
        running, "POST", "/api/pair", b"x" * 32769, headers={"Content-Type": "application/json"}
    )
    assert status == 413 and json.loads(data) == {"error_code": "request_too_large"}
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "extra",
    [
        b"Host: duplicate\r\n",
        b"Origin: http://evil\r\n",
        b"Content-Length: 2\r\n",
        b"X-Jarvis-Client: other\r\n",
        b"Cookie: other=value\r\nCookie: again=value\r\n",
        b"X-Jarvis-CSRF: a\r\nX-Jarvis-CSRF: b\r\n",
        b"Transfer-Encoding: chunked\r\n",
        b"Expect: 100-continue\r\n",
        b"Origin: same\r\n folded\r\n",
    ],
)
def test_duplicate_or_ambiguous_headers(running, extra):
    port = running["server"].server_port
    message = (
        (
            f"POST /api/pair HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
            f"Origin: {running['origin']}\r\nX-Jarvis-Client: local-web-v1\r\n"
            "Content-Type: application/json\r\nContent-Length: 2\r\n"
        ).encode("ascii")
        + extra
        + b"\r\n{}"
    )
    status, body = raw(running, message)
    assert status == 400 and json.loads(body) == {"error_code": "request_invalid"}
    assert running["service"].calls == []


@pytest.mark.parametrize("length", [None, "-1", "+2", "02", "abc", "999999999", "2,2"])
def test_content_length_strict(running, length):
    port = running["server"].server_port
    length_header = "" if length is None else f"Content-Length: {length}\r\n"
    message = (
        f"POST /api/pair HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Origin: {running['origin']}\r\nX-Jarvis-Client: local-web-v1\r\n"
        f"Content-Type: application/json\r\n{length_header}\r\n{{}}"
    ).encode("ascii")
    status, _ = raw(running, message)
    assert status == (413 if length == "999999999" else 400)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"ticket": TICKET, "query": "x", "extra": True},
        {"ticket": "bad", "query": "x"},
        {"ticket": TICKET, "query": None},
        {"ticket": TICKET, "query": []},
        {"ticket": TICKET, "query": ""},
        {"ticket": TICKET, "query": " "},
        {"ticket": TICKET, "query": "x" * 4001},
        {"ticket": TICKET, "query": "\ud800"},
    ],
)
def test_analysis_body_contract_before_service(running, body):
    pair(running)
    running["service"].calls.clear()
    assert request(running, "POST", "/api/analysis", body)[0] == 400
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/session?secret=private"),
        ("GET", "/api/results/bad"),
        ("HEAD", "/api/session"),
        ("GET", "/../HANDOFF.md"),
        ("GET", "http://evil.example/api/session"),
        ("GET", "/fixtures.mjs"),
        ("GET", "/index.html"),
        ("PUT", "/api/tickets"),
        ("OPTIONS", "/api/session"),
        ("TRACE", "/"),
    ],
)
def test_no_other_routes_methods_or_sensitive_reflection(running, method, path):
    pair(running)
    running["service"].calls.clear()
    status, _, data = request(running, method, path)
    assert status in {400, 403}
    assert b"private" not in data and b"evil" not in data and b"HANDOFF" not in data
    assert running["service"].calls == []


@pytest.mark.parametrize(
    "code,status",
    [
        ("analysis_invalid", 400),
        ("analysis_busy", 409),
        ("analysis_ticket_refused", 403),
        ("analysis_closed", 503),
        ("private exception", 503),
    ],
)
def test_fixed_service_exception_mapping(running, code, status):
    pair(running)
    running["service"].error = LocalWebRejected(code)
    response_status, _, data = request(running, "POST", "/api/tickets", {})
    assert response_status == status
    assert json.loads(data) == {
        "error_code": code if code.startswith("analysis_") else "service_unavailable"
    }


def test_arbitrary_internal_exception_never_echoed_or_logged(running, capsys):
    pair(running)
    running["service"].error = Exception("secret account private credential")
    status, _, data = request(running, "POST", "/api/tickets", {})
    assert status == 503 and json.loads(data) == {"error_code": "service_unavailable"}
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_result_expiry_rechecked_after_service(running):
    pair(running)
    running["service"].after = lambda: setattr(running["clock"], "value", 1000)
    status, _, data = request(running, path="/api/results/" + TICKET)
    assert status == 401 and b"final_text" not in data and b"sint" not in data


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", "/api/session", None),
        ("GET", "/api/results/" + TICKET, None),
        ("POST", "/api/tickets", {}),
        ("POST", "/api/analysis", {"ticket": TICKET, "query": "Compare docs."}),
    ],
)
@pytest.mark.parametrize("change", ["expire", "revoke"])
def test_auth_fence_after_each_service_response(running, method, path, body, change):
    pair(running)
    token = running["cookie"].split("=", 1)[1]
    if change == "expire":
        running["service"].after = lambda: setattr(running["clock"], "value", 1000)
    else:
        running["service"].after = lambda: running["auth"].revoke(token)
    status, _, data = request(running, method, path, body)
    assert status == 401 and json.loads(data) == {"error_code": "session_refused"}
    assert b"final_text" not in data and b"csrf_token" not in data and b"ticket" not in data


@pytest.mark.parametrize(
    "method,path", [("GET", "/api/session"), ("GET", "/api/results/" + TICKET)]
)
def test_get_duplicate_cookie_and_csrf_rejected(running, method, path):
    pair(running)
    port = running["server"].server_port
    message = (
        f"{method} {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "X-Jarvis-Client: local-web-v1\r\n"
        f"Cookie: {running['cookie']}\r\nCookie: {running['cookie']}\r\n"
        f"X-Jarvis-CSRF: {running['csrf']}\r\n\r\n"
    ).encode("ascii")
    status, body = raw(running, message)
    assert status == 400 and json.loads(body) == {"error_code": "request_invalid"}


def test_service_result_auth_revalidated_after_serialization(running):
    pair(running)
    token = running["cookie"].split("=", 1)[1]

    class RevokingDict(dict):
        def items(self):
            running["auth"].revoke(token)
            return super().items()

    running["service"].get_result = lambda *_: RevokingDict(
        FakeService.envelope("completed", {"final_text": "never deliver"})
    )
    status, _, data = request(running, path="/api/results/" + TICKET)
    assert status == 401 and b"never deliver" not in data


def test_bad_principal_or_ticket_never_revealed_in_session_payload(running):
    pair(running)
    running["service"].ticket = "private-user-specific-ticket"
    status, _, data = request(running)
    assert status == 503 and b"private-user" not in data


def test_unknown_method_safe_error(running):
    status, _, data = request(running, "PRIVATE_METHOD", "/private-uri")
    assert status == 400 and json.loads(data) == {"error_code": "request_invalid"}


def test_partial_declared_body_is_rejected(running):
    port = running["server"].server_port
    message = (
        f"POST /api/pair HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        f"Origin: {running['origin']}\r\nX-Jarvis-Client: local-web-v1\r\n"
        "Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{}"
    ).encode("ascii")
    status, body = raw(running, message)
    assert status == 400 and json.loads(body) == {"error_code": "request_invalid"}


@pytest.mark.parametrize("delay", [0, 0.02])
def test_early_origin_rejection_discards_delayed_body_without_echo(running, delay):
    port = running["server"].server_port
    body = b'{"secret":"synthetic-private-marker"}'
    headers = (
        f"POST /api/pair HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "X-Jarvis-Client: local-web-v1\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode("ascii")
    with socket.create_connection(("127.0.0.1", port), timeout=2) as connection:
        connection.sendall(headers)
        threading.Event().wait(delay)
        connection.sendall(body)
        response = http.client.HTTPResponse(connection)
        response.begin()
        data = response.read()
        assert response.status == 403
        assert json.loads(data) == {"error_code": "origin_refused"}
        assert b"synthetic-private-marker" not in data
    assert running["service"].calls == []


def test_pairing_budget_and_expiry_real_http(running):
    for _ in range(8):
        assert request(running, "POST", "/api/pair", {"secret": "0" * 64})[0] == 403
    assert (
        request(running, "POST", "/api/pair", {"secret": running["auth"].pairing_secret})[0] == 429
    )
    running["clock"].value = 220
    assert (
        request(running, "POST", "/api/pair", {"secret": running["auth"].pairing_secret})[0] == 403
    )


def test_response_security_headers_and_no_cors(running):
    headers, _ = pair(running)
    assert headers["Content-Security-Policy"] == CSP
    assert "connect-src 'self'" in CSP
    assert headers["Cache-Control"] == "no-store"
    assert headers["Connection"] == "close"
    assert headers["Referrer-Policy"] == "no-referrer"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert not any(key.lower().startswith("access-control") for key in headers)


def test_thread_admission_bounded_and_recovers(running):
    server = running["server"]
    for _ in range(MAX_REQUEST_THREADS):
        assert server._slots.acquire(blocking=False)
    try:
        status, headers, data = request(running)
        assert status == 503 and json.loads(data) == {"error_code": "server_busy"}
        assert headers["Cache-Control"] == "no-store"
        assert headers["Content-Security-Policy"] == CSP
    finally:
        for _ in range(MAX_REQUEST_THREADS):
            server._slots.release()
    assert request(running)[0] == 401


def test_static_allowlist_real_asset_and_fixture_server_unchanged(running):
    status, headers, data = request(running, path="/particle-sphere.mjs", client=False)
    assert status == 200 and b"export" in data
    assert headers["Content-Type"] == "text/javascript; charset=utf-8"
    from apps.jarvis_web.serve import ASSETS as fixture_assets
    from apps.jarvis_web.serve import CSP as fixture_csp

    assert fixture_assets["/"][0] == "index.html"
    assert "connect-src 'none'" in fixture_csp


def test_header_read_deadline_is_total_and_bounded(running, monkeypatch):
    import apps.jarvis_api.local_server as module

    monkeypatch.setattr(module, "REQUEST_READ_SECONDS", 0.1)
    with socket.create_connection(
        ("127.0.0.1", running["server"].server_port), timeout=2
    ) as connection:
        connection.sendall(b"GET / HTTP/1.1\r\n")
        assert connection.recv(1) == b""


@pytest.mark.parametrize("port", [True, -1, 65536, 1.0, "0", None])
def test_invalid_port_never_binds(port):
    with pytest.raises(ValueError, match="^invalid_port$"):
        create_server(FakeService(), port)
