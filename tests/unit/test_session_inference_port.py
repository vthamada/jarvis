"""MB229 account leaf: synthetic credentials, no login/profile/live model."""

from __future__ import annotations

import json
import ssl
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import pytest
from inference_service.oauth_http import ModelCatalog, ModelChoice, SiwcHttpsClient
from inference_service.session_inference_port import SessionInferencePort
from inference_service.siwc_contracts import DIRECT_SCOPE, SiwcCredentials, SiwcError
from inference_service.siwc_session import SiwcSession

from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult

HOST = "urn:uuid:3ab59e96-7cd8-4eb1-9161-ebd1e10e5499"
MODEL = "selected-model"


class Clock:
    now = 100.0

    def __call__(self):
        return self.now


def credentials():
    return SiwcCredentials("oaiapp_fixture", HOST, "synthetic-account", "synthetic-access",
                           "synthetic-refresh", "synthetic.id.token",
                           ("openid", "resource.invoke", DIRECT_SCOPE), 500.0, 100.0)


def request(**changes):
    return replace(InferenceRequest("request-id", MODEL, (InferenceMessage("user", "private"),),
                                    timeout_seconds=10.0), **changes)


def complete(req):
    return InferenceResult(req.request_id, req.model, "responses_plan", "completed",
                           text="unverified draft", evidence_mode="injected_transport")


@pytest.fixture
def rig(monkeypatch):
    clock = Clock()
    client = SiwcHttpsClient(authorized=True, connection_factory=lambda *a, **k: None,
                            clock=clock)
    session = SiwcSession(host_id=HOST, client=client, wall_clock=lambda: 100.0, clock=clock)
    session._replace(credentials())
    state = SimpleNamespace(session=session, clock=clock, calls=[], on_catalog=lambda: None,
                            on_provider=lambda: None, on_infer=lambda: None, outcome=complete,
                            catalog=ModelCatalog((ModelChoice(MODEL, "Fixture"),)))

    def catalog(**kwargs):
        state.calls.append(("catalog", kwargs))
        state.on_catalog()
        session._catalog = state.catalog
        return state.catalog

    def provider(model, **kwargs):
        state.calls.append(("provider", model, kwargs))
        state.on_provider()

        def infer(req, *, cancellation):
            state.calls.append(("infer", req, cancellation))
            state.on_infer()
            return state.outcome(req)

        return SimpleNamespace(infer=infer)

    monkeypatch.setattr(session, "catalog", catalog)
    monkeypatch.setattr(session, "provider", provider)
    state.port = SessionInferencePort(session, model=MODEL, authorized=True, clock=clock)
    return state


def test_constructor_inert_and_repr_private(rig):
    assert rig.calls == []
    assert "selected-model" not in repr(rig.port)
    assert "synthetic" not in repr(rig.port)


@pytest.mark.parametrize("kwargs", [{"authorized": 1}, {"clock": None},
                                     {"connection_factory": "x"}, {"model": "bad model"}])
def test_invalid_composition(rig, kwargs):
    options = {"model": MODEL, **kwargs}
    with pytest.raises(ValueError):
        SessionInferencePort(rig.session, **options)
    assert rig.calls == []


def test_inert_default_off(rig):
    port = SessionInferencePort(rig.session, model=MODEL)
    result = port.infer(request())
    assert result.status == "failed" and result.text == ""
    assert rig.calls == []


@pytest.mark.parametrize("reason", ["cancelled", "model", "invalid_cancellation", "account",
                                    "host", "generation"])
def test_refusals_never_load_catalog(rig, reason):
    token, req = Event(), request()
    if reason == "cancelled":
        token.set()
    elif reason == "model":
        req = request(model="different-model")
    elif reason == "invalid_cancellation":
        token = object()
    elif reason == "account":
        rig.session.disconnect_local()
    elif reason == "host":
        rig.session._host = "different-host"
    else:
        rig.session._generation = True
    result = rig.port.infer(req, cancellation=token)
    assert result.status != "completed" and result.text == ""
    assert rig.calls == []


def test_catalog_and_infer_share_budget_and_exact_model(rig):
    rig.on_catalog = lambda: setattr(rig.clock, "now", 106.0)
    rig.on_provider = lambda: setattr(rig.clock, "now", 107.0)
    result = rig.port.infer(request())
    assert result.status == "completed"
    assert result.evidence_mode == "injected_transport"
    assert [call[0] for call in rig.calls] == ["catalog", "provider", "infer"]
    assert rig.calls[0][1]["timeout_seconds"] == 10.0
    assert rig.calls[1][1] == MODEL
    assert rig.calls[2][1].timeout_seconds == 3.0
    assert rig.calls[0][1]["cancellation"] is rig.calls[2][2]


@pytest.mark.parametrize("stage", ["catalog", "provider", "infer"])
@pytest.mark.parametrize("transition", ["replace", "disconnect", "host", "client", "token"])
def test_identity_binding_rechecked_at_each_boundary(rig, stage, transition):
    def change():
        if transition == "replace":
            rig.session._replace(credentials())
        elif transition == "disconnect":
            rig.session.disconnect_local()
        elif transition == "host":
            rig.session._host = "changed-host"
        elif transition == "client":
            rig.session._client = SiwcHttpsClient()
        else:
            object.__setattr__(rig.session._credentials, "access_token", "changed-synthetic")

    setattr(rig, "on_" + stage, change)
    result = rig.port.infer(request())
    assert result.status == "failed" and result.text == ""
    assert len(rig.calls) == {"catalog": 1, "provider": 2, "infer": 3}[stage]


@pytest.mark.parametrize("stage", ["catalog", "provider", "infer"])
@pytest.mark.parametrize("now,status", [(110.0, "timed_out"), (111.0, "timed_out"),
                                        (99.0, "failed"), (float("nan"), "failed"),
                                        (float("inf"), "failed"), (True, "failed")])
def test_global_deadline_and_clock_revalidated(rig, stage, now, status):
    setattr(rig, "on_" + stage, lambda: setattr(rig.clock, "now", now))
    result = rig.port.infer(request())
    assert result.status == status and result.text == ""
    assert len(rig.calls) == {"catalog": 1, "provider": 2, "infer": 3}[stage]


@pytest.mark.parametrize("stage", ["catalog", "provider", "infer"])
def test_cancellation_mid_operation_discards_text(rig, stage):
    token = Event()
    setattr(rig, "on_" + stage, token.set)
    result = rig.port.infer(request(), cancellation=token)
    assert result.status == "cancelled" and result.text == ""


@pytest.mark.parametrize("changes", [
    {"request_id": "wrong"}, {"model": "wrong"}, {"provider_id": "wrong"},
    {"evidence_mode": "live"}, {"evidence_mode": "fixture"}, {"text": "x" * 100},
    {"input_tokens": 1_000_000_001}, {"output_tokens": 1_000_000_001},
])
def test_candidate_boundary_mismatches_fail_closed(rig, changes):
    rig.outcome = lambda req: replace(complete(req), **changes)
    result = rig.port.infer(request(max_output_chars=80))
    assert result.status == "failed" and result.text == ""
    assert result.error_code == "session_result_invalid"


@pytest.mark.parametrize("mutations", [{"status": "partial"}, {"text": None},
                                      {"input_tokens": True}, {"error_code": "secret error"}])
def test_forged_frozen_results_revalidated(rig, mutations):
    def forged(req):
        result = complete(req)
        for key, value in mutations.items():
            object.__setattr__(result, key, value)
        return result

    rig.outcome = forged
    result = rig.port.infer(request())
    assert result.status == "failed" and result.text == ""
    assert "secret" not in repr(result)


@pytest.mark.parametrize("status,code", [("failed", "arbitrary_secret_code"),
                                        ("cancelled", "cancelled"), ("timed_out", "timeout")])
def test_failure_is_content_free_and_fixed(rig, status, code):
    rig.outcome = lambda req: InferenceResult(req.request_id, req.model, "responses_plan", status,
                                              error_code=code, evidence_mode="injected_transport")
    result = rig.port.infer(request())
    assert result.status == status and result.text == ""
    assert "secret" not in result.error_code


@pytest.mark.parametrize("stage", ["catalog", "provider", "infer"])
@pytest.mark.parametrize("error,status", [(RuntimeError("private exception"), "failed"),
                                         (SiwcError("siwc_cancelled"), "cancelled"),
                                         (SiwcError("siwc_timeout"), "timed_out"),
                                         (TimeoutError("private exception"), "timed_out")])
def test_exception_no_retry_no_private_message(rig, stage, error, status):
    def fail():
        raise error

    setattr(rig, "on_" + stage, fail)
    result = rig.port.infer(request())
    assert result.status == status and result.text == ""
    assert "private" not in repr(result)
    assert len(rig.calls) == {"catalog": 1, "provider": 2, "infer": 3}[stage]


@pytest.mark.parametrize("catalog", [None, {"choices": [MODEL]},
                                    ModelCatalog((ModelChoice("not-selected", "Other"),))])
def test_invalid_or_unselected_catalog_stops_before_provider(rig, catalog):
    rig.catalog = catalog
    result = rig.port.infer(request())
    assert result.status == "failed" and result.text == ""
    assert len(rig.calls) == 1


def test_forged_request_fails_before_side_effect(rig):
    req = request()
    object.__setattr__(req, "timeout_seconds", 121)
    with pytest.raises(ValueError):
        rig.port.infer(req)
    assert rig.calls == []


class Response:
    status = 200

    def __init__(self, body, *, stream=False, close_failure=False):
        self.body, self.stream = body, stream
        self.close_failure, self.closed = close_failure, False

    def getheader(self, name, default=None):
        return {"Content-Type": "text/event-stream" if self.stream else "application/json",
                "Content-Encoding": "identity"}.get(name, default)

    def read1(self, size):
        result, self.body = self.body[:size], self.body[size:]
        return result

    def close(self):
        self.closed = True
        if self.close_failure:
            raise RuntimeError("private close error")


class Connection:
    def __init__(self, wire, host):
        self.wire, self.host, self.sock = wire, host, None
        self.closed, self.response, self.timeout = False, None, None

    def connect(self):
        pass

    def request(self, method, path, *, body, headers):
        self.wire.calls.append((self.host, method, path))
        if path == "/v1/models":
            value = {"models": [{"slug": MODEL, "display_name": "Fixture", "visibility": "list"}]}
            self.response = Response(json.dumps(value).encode())
        else:
            assert path == "/v1/responses" and method == "POST"
            payload = json.loads(body)
            assert payload["model"] == MODEL
            assert payload["store"] is False and payload["stream"] is True
            response = {"id": "fixture-response", "model": MODEL, "status": "completed",
                        "output": [{"type": "message", "role": "assistant", "status": "completed",
                                    "content": [{"type": "output_text",
                                                 "text": "Synthetic draft"}]}]}
            event = {"type": "response.completed", "response": response}
            self.response = Response(("data: " + json.dumps(event) + "\n\n").encode(), stream=True,
                                     close_failure=self.wire.close_failure == "response")

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True
        if self.wire.close_failure == "connection" and self.response.stream:
            raise RuntimeError("private close error")


class Wire:
    def __init__(self, close_failure=None):
        self.calls, self.connections, self.close_failure = [], [], close_failure

    def factory(self, host, *, port, timeout, context):
        assert host == "api.openai.com" and port == 443
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        connection = Connection(self, host)
        self.connections.append(connection)
        return connection


def wire_port(wire):
    session = SiwcSession(host_id=HOST, client=SiwcHttpsClient(authorized=True,
                          connection_factory=wire.factory), wall_clock=lambda: 100.0)
    session._replace(credentials())
    return SessionInferencePort(session, model=MODEL, authorized=True,
                                connection_factory=wire.factory)


def test_real_session_provider_and_transports_via_injected_wire():
    wire = Wire()
    result = wire_port(wire).infer(request())
    assert result.status == "completed" and result.text == "Synthetic draft"
    assert result.evidence_mode == "injected_transport"
    assert [call[2] for call in wire.calls] == ["/v1/models", "/v1/responses"]
    assert all(c.closed and c.response.closed for c in wire.connections)


@pytest.mark.parametrize("resource", ["response", "connection"])
def test_cleanup_failure_discards_completed_draft(resource):
    wire = Wire(close_failure=resource)
    result = wire_port(wire).infer(request())
    assert result.status == "failed" and result.text == ""
    assert result.error_code == "session_cleanup_failed"
    assert all(c.closed and c.response.closed for c in wire.connections)


def test_default_transport_evidence_does_not_contact_network():
    session = SiwcSession(host_id=HOST, client=SiwcHttpsClient())
    port = SessionInferencePort(session, model=MODEL)
    assert port.evidence_mode == "live"
    # Live identifies composition, not completed model acceptance or account login.
    assert port.infer(request()).status == "failed"


def test_injected_client_never_upgraded_without_response_factory():
    wire = Wire()
    session = SiwcSession(host_id=HOST, client=SiwcHttpsClient(connection_factory=wire.factory))
    assert SessionInferencePort(session, model=MODEL).evidence_mode == "injected_transport"
    assert wire.calls == []
