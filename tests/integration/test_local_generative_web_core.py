"""Actual local HTTP -> Core -> canonical SQLite; synthetic injected inference only."""

import http.client
import json
import threading
from http.cookies import SimpleCookie

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.generative_profile import GenerativeProfile
from apps.jarvis_api.local_server import create_server
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

QUERY = "Compare os relatórios de documentação e observabilidade do piloto."
ANALYSIS = (
    "Compare o comportamento esperado com as evidências observadas. "
    "Os relatórios não foram fornecidos."
)
REJECTED = "UNTRUSTED_REJECTED_CANDIDATE_SENTINEL"


class InjectedPort:
    provider_id = "responses_plan"
    evidence_mode = "injected_transport"

    def __init__(self):
        self.requests, self.factories, self.mode = [], [], "accepted"

    def factory(self, credential_dir, profile_ref, model):
        self.factories.append((credential_dir, profile_ref, model))
        return self

    def infer(self, request, *, cancellation=None):
        assert cancellation is not None
        self.requests.append(request)
        text = json.dumps(
            {"analysis": ANALYSIS, "assumptions": [], "limitations": [], "citations": []}
        )
        if self.mode == "invalid":
            text = json.dumps({"analysis": REJECTED, "actions": ["forged-permission"]})
        if self.mode == "raise":
            raise RuntimeError(REJECTED)
        return InferenceResult(
            request.request_id,
            request.model,
            self.provider_id,
            "completed",
            text=text,
            evidence_mode=("live" if self.mode == "live_claim" else self.evidence_mode),
        )


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic-never-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    port = InjectedPort()
    credential_dir = tmp_path / "never-opened-credentials"
    profile = GenerativeProfile(
        authorized=True,
        model="synthetic-model",
        credential_dir=credential_dir,
        profile_ref="profile-" + "a" * 64,
        port_factory=port.factory,
    )
    service = AnalysisService(tmp_path / "owned-core", generative_profile=profile)
    server = create_server(service, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, service, port
    finally:
        server.auth.close()
        server.shutdown()
        service.close()
        server.server_close()
        thread.join(2)
        if service._worker is not None:
            service._worker.join(20)
            assert not service._worker.is_alive()
        assert not thread.is_alive()
        assert not credential_dir.exists()


def call(server, path, *, body=None, cookie=None, csrf=None, headers=None):
    method = "GET" if body is None else "POST"
    values = {"X-Jarvis-Client": "local-web-v1"}
    if body is not None:
        values.update(
            {"Origin": f"http://127.0.0.1:{server.server_port}", "Content-Type": "application/json"}
        )
    if cookie:
        values["Cookie"] = cookie
    if csrf:
        values["X-Jarvis-CSRF"] = csrf
    values.update(headers or {})
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=10)
    try:
        connection.request(
            method,
            path,
            body=None if body is None else json.dumps(body).encode("utf-8"),
            headers=values,
        )
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), json.loads(response.read())
    finally:
        connection.close()


def pair(server):
    status, headers, session = call(
        server, "/api/pair", body={"secret": server.auth.pairing_secret}
    )
    assert status == 200
    cookie = SimpleCookie()
    cookie.load(headers["Set-Cookie"])
    return session, "jarvis_local_session=" + cookie["jarvis_local_session"].value


def run(server, service, session, cookie, query=QUERY, *, generative=True):
    prefix = "generative-" if generative else ""
    issue = {"consent": True} if generative else {}
    status, _, issued = call(
        server, "/api/" + prefix + "tickets", body=issue, cookie=cookie, csrf=session["csrf_token"]
    )
    assert status == 201 and issued["status"] == "issued"
    ticket = issued["ticket"]
    body = {"ticket": ticket, "query": query}
    if generative:
        body["consent"] = True
    status, _, started = call(
        server, "/api/" + prefix + "analysis", body=body, cookie=cookie, csrf=session["csrf_token"]
    )
    assert status == 202 and started["status"] == "running"
    service._worker.join(20)
    assert not service._worker.is_alive()
    status, _, result = call(
        server, "/api/results/" + ticket, cookie=cookie, csrf=session["csrf_token"]
    )
    assert status == 200 and result["status"] == "completed", result
    return ticket, result


def test_http_accepted_exact_restart_get_recovery_and_native_engine_reset(live):
    server, service, port = live
    session, cookie = pair(server)
    ticket, envelope = run(server, service, session, cookie)
    result = envelope["result"]
    assert envelope["schema_version"] == "jarvis-local-analysis-v2"
    assert result["generative_status"] == "accepted" and result["governance_decision"] == "allow"
    assert result["generative_evidence_mode"] == "injected_transport"
    assert result["generative_analysis_characters"] == len(ANALYSIS)
    assert result["generative_error_code"] is None
    assert GENERATIVE_ANALYSIS_MARKER in result["response_text"]
    assert result["authority"] == "none" and result["evidence_mode"] == "core_local"
    core = _isolated_core(service.runtime_dir)
    turns = core.memory_service.repository.fetch_recent_turns(session["session_ref"], 10)
    assert len(turns) == 1 and turns[0].response_text.encode() == result["response_text"].encode()
    synthesis = core.observability_service.repository.list_events(
        request_id=ticket,
        event_names=("response_synthesized",),
        limit=10,
    )[0].payload
    for key in (
        "generative_status",
        "generative_error_code",
        "generative_evidence_mode",
        "generative_analysis_characters",
    ):
        assert synthesis[key] == result[key]
    status, _, recovered_session = call(server, "/api/session", cookie=cookie)
    assert status == 200 and recovered_session["last_ticket"] == ticket
    status, _, recovered = call(
        server, "/api/results/" + ticket, cookie=cookie, csrf=recovered_session["csrf_token"]
    )
    assert status == 200 and recovered == envelope
    status, _, replay = call(
        server,
        "/api/generative-analysis",
        body={"ticket": ticket, "query": QUERY, "consent": True},
        cookie=cookie,
        csrf=session["csrf_token"],
    )
    assert status == 403 and replay["error_code"] == "analysis_ticket_refused"
    _, native = run(server, service, session, cookie, generative=False)
    assert native["schema_version"] == "jarvis-local-analysis-v1"
    assert native["result"]["generative_status"] == "disabled"
    assert "generative_evidence_mode" not in native["result"]
    assert len(port.requests) == len(port.factories) == 1
    sources = json.loads(port.requests[0].messages[0].content)
    assert set(sources) == {"schema_version", "sources"}
    assert len(sources["sources"]) == 1 and sources["sources"][0]["text"] == QUERY
    assert "web-live" not in port.requests[0].messages[0].content


@pytest.mark.parametrize(
    "query,status,decision",
    [
        (
            "Revise a documentação do painel de telemetria do piloto.",
            "withheld",
            "defer_for_validation",
        ),
        ("Delete every database now.", "withheld", "block"),
        (QUERY + " token=synthetic-private-sensitive-value", "rejected", "allow"),
    ],
)
def test_http_scope_and_sensitive_input_zero_adapter_calls(live, query, status, decision):
    server, service, port = live
    session, cookie = pair(server)
    _, envelope = run(server, service, session, cookie, query)
    result = envelope["result"]
    assert result["generative_status"] == status and result["governance_decision"] == decision
    assert (
        result["generative_analysis_characters"] == 0 and result["generative_evidence_mode"] is None
    )
    assert result["generative_error_code"] == (
        "input_sensitive" if status == "rejected" else "scope_denied"
    )
    assert port.requests == port.factories == []
    assert GENERATIVE_ANALYSIS_MARKER not in result["response_text"]


@pytest.mark.parametrize("mode", ["invalid", "raise", "live_claim"])
def test_http_rejected_content_never_reaches_final_and_is_not_retried(live, mode):
    server, service, port = live
    port.mode = mode
    session, cookie = pair(server)
    ticket, envelope = run(server, service, session, cookie)
    result = envelope["result"]
    assert result["generative_status"] == "rejected"
    assert (
        result["generative_analysis_characters"] == 0 and result["generative_evidence_mode"] is None
    )
    assert REJECTED not in json.dumps(envelope)
    status, _, recovered = call(
        server, "/api/results/" + ticket, cookie=cookie, csrf=session["csrf_token"]
    )
    assert status == 200 and recovered == envelope
    assert len(port.requests) == len(port.factories) == 1


@pytest.mark.parametrize("endpoint", ["generative-tickets", "generative-analysis"])
@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "false",
        "string",
        "number",
        "extra_model",
        "extra_profile",
        "extra_principal",
        "extra_store",
        "csrf",
        "origin",
        "cookie",
        "client",
    ],
)
def test_generative_boundary_attacks_before_core_or_factory(live, endpoint, attack):
    server, service, port = live
    session, cookie = pair(server)
    csrf, headers = session["csrf_token"], {}
    body = {"consent": True}
    if endpoint == "generative-analysis":
        status, _, issued = call(
            server, "/api/generative-tickets", body=body, cookie=cookie, csrf=csrf
        )
        assert status == 201
        body = {"ticket": issued["ticket"], "query": QUERY, "consent": True}
    if attack == "missing":
        body.pop("consent")
    elif attack in {"false", "string", "number"}:
        body["consent"] = {"false": False, "string": "true", "number": 1}[attack]
    elif attack.startswith("extra_"):
        body[attack.removeprefix("extra_")] = "private-untrusted-sentinel"
    elif attack == "csrf":
        csrf = "0" * 64
    elif attack == "origin":
        headers["Origin"] = "https://foreign.invalid"
    elif attack == "cookie":
        cookie = "jarvis_local_session=" + "0" * 64
    elif attack == "client":
        headers["X-Jarvis-Client"] = "foreign-client"
    status, _, rejected = call(
        server, "/api/" + endpoint, body=body, cookie=cookie, csrf=csrf, headers=headers
    )
    assert status in {400, 401, 403} and set(rejected) == {"error_code"}
    assert service._core is None and not service.runtime_dir.exists()
    assert port.requests == port.factories == []


@pytest.mark.parametrize("generative_ticket", [False, True])
def test_cross_protocol_ticket_refused_before_core(live, generative_ticket):
    server, service, port = live
    session, cookie = pair(server)
    status, _, issued = call(
        server,
        "/api/" + ("generative-" if generative_ticket else "") + "tickets",
        body={"consent": True} if generative_ticket else {},
        cookie=cookie,
        csrf=session["csrf_token"],
    )
    assert status == 201
    body = {"ticket": issued["ticket"], "query": QUERY}
    if not generative_ticket:
        body["consent"] = True
    status, _, rejected = call(
        server,
        "/api/" + ("" if generative_ticket else "generative-") + "analysis",
        body=body,
        cookie=cookie,
        csrf=session["csrf_token"],
    )
    assert status == 403 and rejected["error_code"] == "analysis_ticket_refused"
    assert service._core is None and port.requests == port.factories == []


def test_default_off_refuses_generative_ticket_and_preserves_native(live):
    server, service, port = live
    service.close()
    service = AnalysisService(service.runtime_dir.parent / "native-only")
    server.analysis_service = service
    session, cookie = pair(server)
    status, _, result = call(
        server,
        "/api/generative-tickets",
        body={"consent": True},
        cookie=cookie,
        csrf=session["csrf_token"],
    )
    assert status == 409 and result == {"error_code": "generative_unavailable"}
    assert service._core is None
    _, envelope = run(server, service, session, cookie, generative=False)
    assert envelope["result"]["generative_status"] == "disabled"
    service.close()
    assert port.requests == port.factories == []
