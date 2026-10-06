"""HTTP boundary and the complete static cockpit asset flow, on loopback only."""

from __future__ import annotations

import http.client
import threading

import pytest

from apps.jarvis_web.serve import ASSETS, create_server


@pytest.fixture
def server():
    instance = create_server(0)
    worker = threading.Thread(target=instance.serve_forever, daemon=True)
    worker.start()
    try:
        yield instance
    finally:
        instance.shutdown()
        instance.server_close()
        worker.join(timeout=2)


def request(server, path="/", method="GET", headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def test_asset_flow_is_fixture_only_and_disables_connections(server):
    assert server.server_address[0] == "127.0.0.1"
    for path in ASSETS:
        status, headers, content = request(server, path)
        assert status == 200
        assert content
        assert "connect-src 'none'" in headers["Content-Security-Policy"]
        assert "form-action 'none'" in headers["Content-Security-Policy"]
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Cache-Control"] == "no-store"
        assert "Access-Control-Allow-Origin" not in headers
    html = request(server)[2].decode()
    assert "Demonstração isolada" in html
    assert "Nenhuma ação real" in html
    assert 'src="/app.mjs"' in html


@pytest.mark.parametrize("path", [
    "/../AGENTS.md", "/%2e%2e/.git/config", "/.env", "/.git/config",
    "/serve.py", "/tests/test_serve.py", "/", "/api", "/fixtures.mjs?token=secret",
    "http://evil.invalid/styles.css", "//evil.invalid/styles.css", "/styles.css#fragment",
])
def test_non_allowlisted_paths_are_not_served(server, path):
    if path == "/":
        path = "/../"
    assert request(server, path)[0] in {403, 404}


def test_head_returns_only_headers(server):
    status, headers, body = request(server, "/index.html", "HEAD")
    assert status == 200
    assert int(headers["Content-Length"]) > 0
    assert body == b""


def test_localhost_host_is_accepted(server):
    assert request(server, headers={"Host": f"localhost:{server.server_port}"})[0] == 200


def test_unknown_method_not_reflected(server):
    status, headers, body = request(server, "/", "SECRET-METHOD")
    assert status == 501
    assert b"SECRET" not in body
    assert "connect-src 'none'" in headers["Content-Security-Policy"]


def test_missing_allowlisted_asset_fails_closed(server, monkeypatch):
    from apps.jarvis_web import serve

    monkeypatch.setattr(serve, "ASSET_ROOT", serve.ASSET_ROOT / "missing-assets-for-test")
    assert request(server, "/app.mjs")[0] == 404


@pytest.mark.parametrize(
    "method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"]
)
def test_no_mutating_or_proxy_methods(server, method):
    assert request(server, "/", method)[0] == 405


def test_host_rebinding_rejected_and_no_request_data_logged(server, capsys):
    status, _, body = request(server, "/?secret=neverlog", headers={"Host": "attacker.invalid"})
    assert status == 403
    assert b"secret" not in body
    assert "neverlog" not in capsys.readouterr().err


def test_duplicate_host_headers_fail_closed(server):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=2)
    try:
        connection.putrequest("GET", "/", skip_host=True)
        connection.putheader("Host", f"127.0.0.1:{server.server_port}")
        connection.putheader("Host", "attacker.invalid")
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 403
        response.read()
    finally:
        connection.close()


@pytest.mark.parametrize("port", [-1, 65536, "8765", True])
def test_invalid_port_rejected(port):
    with pytest.raises(ValueError):
        create_server(port)


def test_frontend_uses_safe_text_sinks_and_no_egress(server):
    script = request(server, "/app.mjs")[2].decode()
    assert "textContent" in script
    for forbidden in [
        "innerHTML", "fetch(", "XMLHttpRequest", "localStorage", "sessionStorage", "eval("
    ]:
        assert forbidden not in script
