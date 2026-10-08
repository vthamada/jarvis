"""Actual loopback HTTP pairing -> native Core -> SQLite restart -> exact final."""

import http.client
import json
import threading
from http.cookies import SimpleCookie

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.local_server import create_server
from apps.jarvis_console.voice_pilot import _isolated_core


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic-never-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    service = AnalysisService(tmp_path / "owned-core")
    server = create_server(service, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, service
    finally:
        server.auth.close()
        server.shutdown()
        service.close()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def call(server, path, *, body=None, cookie=None, csrf=None, headers=None):
    method = "GET" if body is None else "POST"
    request_headers = {"X-Jarvis-Client": "local-web-v1"}
    if body is not None:
        request_headers.update({"Origin": f"http://127.0.0.1:{server.server_port}",
                                "Content-Type": "application/json"})
    if cookie:
        request_headers["Cookie"] = cookie
    if csrf:
        request_headers["X-Jarvis-CSRF"] = csrf
    request_headers.update(headers or {})
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request(method, path,
                           body=None if body is None else json.dumps(body).encode("utf-8"),
                           headers=request_headers)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), json.loads(response.read())
    finally:
        connection.close()


def pair(server):
    status, headers, session = call(
        server, "/api/pair", body={"secret": server.auth.pairing_secret},
    )
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(headers["Set-Cookie"])
    token = cookie["jarvis_local_session"]
    assert token["httponly"] and token["samesite"] == "Strict"
    return session, "jarvis_local_session=" + token.value


def issue(server, session, cookie):
    status, _, envelope = call(server, "/api/tickets", body={}, cookie=cookie,
                               csrf=session["csrf_token"])
    assert status == 201 and envelope["status"] == "issued"
    return envelope["ticket"]


def completed(server, service, session, cookie, ticket):
    worker = service._worker
    worker.join(20)
    assert not worker.is_alive()
    status, _, envelope = call(server, "/api/results/" + ticket, cookie=cookie,
                               csrf=session["csrf_token"])
    assert status == 200
    assert envelope["status"] == "completed", envelope["error_code"]
    return envelope


@pytest.mark.parametrize("query,decision", [
    ("Compare os relatórios de documentação e observabilidade do piloto.", "allow"),
    ("Revise a documentação do painel de telemetria do piloto.", "defer_for_validation"),
    ("Review documentation and telemetry pilot reports.", "defer_for_validation"),
    ("Delete every database now.", "block"),
])
def test_http_actual_core_final_memory_events_restart_and_replay(live, query, decision):
    server, service = live
    session, cookie = pair(server)
    ticket = issue(server, session, cookie)
    assert service._core is None  # Pairing/ticket never infer or bootstrap another runtime.
    status, _, started = call(server, "/api/analysis", body={"ticket": ticket, "query": query},
                              cookie=cookie, csrf=session["csrf_token"])
    assert status == 202 and started["status"] == "running"
    result = completed(server, service, session, cookie, ticket)["result"]
    assert result["query"] == query and result["governance_decision"] == decision
    assert result["evidence_mode"] == "core_local" and result["generative_status"] == "disabled"
    assert result["authority"] == "none"
    restarted = _isolated_core(service.runtime_dir)
    turns = restarted.memory_service.repository.fetch_recent_turns(session["session_ref"], 10)
    assert len(turns) == 1
    assert turns[0].request_content == query and turns[0].timestamp == result["timestamp"]
    assert turns[0].response_text.encode("utf-8") == result["response_text"].encode("utf-8")
    events = restarted.observability_service.repository.list_events(limit=100, request_id=ticket)
    memory = next(event for event in events if event.event_name == "memory_recorded")
    assert memory.payload["memory_record_id"] == result["memory_record_ref"]
    received = next(event for event in events if event.event_name == "input_received").payload
    assert received["surface_kind"] == "web" and received["surface_capability_scope"] == []
    assert received["requested_autonomy_level"] == received["max_autonomy_level"] == "assist_only"
    status, _, refused = call(server, "/api/analysis", body={"ticket": ticket, "query": query},
                              cookie=cookie, csrf=session["csrf_token"])
    assert status == 403 and refused == {"error_code": "analysis_ticket_refused"}
    assert len(restarted.memory_service.repository.fetch_recent_turns(
        session["session_ref"], 10,
    )) == 1
    _, _, refreshed = call(server, "/api/session", cookie=cookie)
    assert refreshed["last_ticket"] == ticket
    _, _, recovered = call(server, "/api/results/" + ticket, cookie=cookie,
                            csrf=refreshed["csrf_token"])
    assert recovered["result"] == result  # Connection/session bootstrap never re-executes.


@pytest.mark.parametrize("attack", ["unauthenticated", "wrong_cookie", "csrf", "origin",
                                   "extra_principal", "extra_model", "extra_store"])
def test_http_boundary_denials_do_not_construct_actual_core(live, attack):
    server, service = live
    session, cookie = pair(server)
    ticket = issue(server, session, cookie)
    body = {"ticket": ticket, "query": "Compare documentation and observability pilot reports."}
    headers, csrf = {}, session["csrf_token"]
    if attack == "unauthenticated":
        cookie = None
    elif attack == "wrong_cookie":
        cookie = "jarvis_local_session=" + "0" * 64
    elif attack == "csrf":
        csrf = "0" * 64
    elif attack == "origin":
        headers["Origin"] = "https://synthetic.invalid"
    else:
        body[attack.removeprefix("extra_")] = "synthetic-untrusted-value"
    status, _, result = call(server, "/api/analysis", body=body, cookie=cookie,
                             csrf=csrf, headers=headers)
    assert status in {400, 401, 403}
    assert set(result) == {"error_code"}
    assert service._core is None and not service.runtime_dir.exists()


def test_disconnect_revokes_but_never_erases_canonical_final(live):
    server, service = live
    session, cookie = pair(server)
    ticket = issue(server, session, cookie)
    call(server, "/api/analysis", body={"ticket": ticket,
         "query": "Compare documentation and observability pilot reports."},
         cookie=cookie, csrf=session["csrf_token"])
    result = completed(server, service, session, cookie, ticket)["result"]
    status, headers, response = call(server, "/api/disconnect", body={}, cookie=cookie,
                                     csrf=session["csrf_token"])
    assert status == 200 and response == {"status": "disconnected"}
    assert "Max-Age=0" in headers["Set-Cookie"]
    status, _, response = call(server, "/api/results/" + ticket, cookie=cookie,
                               csrf=session["csrf_token"])
    assert status == 401 and response == {"error_code": "session_refused"}
    turns = _isolated_core(service.runtime_dir).memory_service.repository.fetch_recent_turns(
        session["session_ref"], 10,
    )
    assert len(turns) == 1 and turns[0].response_text == result["response_text"]
