"""Synthetic RSA OAuth -> private local store -> restart -> real Core evidence.

HTTPS responses and models are injected; real DPAPI on Windows protects only
temporary synthetic records. Nothing signs into OpenAI or uses a real model.
"""

from __future__ import annotations

import json
import os
import ssl
from dataclasses import replace
from threading import Event
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from inference_service.credential_store import SiwcCredentialStore
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.siwc_contracts import DIRECT_SCOPE, ISSUER, REQUESTED_SCOPES, SiwcError
from inference_service.siwc_session import SiwcSession
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceMessage, InferenceRequest
from shared.types import PermissionDecision

NOW = 1_800_000_000
CLIENT = "oaiapp_session_fixture"
SUBJECT = "synthetic-private-subject"
MODEL = "account-selected-model"
ACCESS = "synthetic-private-access"
REFRESH = "synthetic-private-refresh"
TEXT = "Analise os fatos: A revisao acontece na quinta-feira. O responsavel e Ana."
QUOTE = "A revisao acontece na quinta-feira."


@pytest.fixture(scope="module")
def signing():
    jwt = pytest.importorskip("jwt")
    rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    key.update(kid="synthetic-key", alg="RS256", use="sig", key_ops=["verify"])
    return jwt, private, {"keys": [key]}


class _Response:
    status = 200

    def __init__(self, body, *, stream=False, on_read=None):
        self.body = body if type(body) is bytes else json.dumps(body).encode()
        self.stream, self.closed, self.on_read = stream, False, on_read

    def getheader(self, name, default=None):
        return {"Content-Type": "text/event-stream" if self.stream else "application/json",
                "Content-Encoding": "identity"}.get(name, default)

    def read1(self, size):
        if self.on_read:
            callback, self.on_read = self.on_read, None
            callback()
        chunk, self.body = self.body[:min(size, 31)], self.body[min(size, 31):]
        return chunk

    def close(self):
        self.closed = True


class _Socket:
    def settimeout(self, _value):
        pass


class _Connection:
    def __init__(self, wire, host):
        self.wire, self.host = wire, host
        self.sock, self.closed, self.response = _Socket(), False, None

    def connect(self):
        pass

    def request(self, method, path, *, body, headers):
        self.wire.requests.append((self.host, method, path, body, headers))
        if path == "/.well-known/openid-configuration":
            value = {"issuer": ISSUER,
                     "authorization_endpoint": ISSUER + "/api/accounts/authorize",
                     "token_endpoint": ISSUER + "/api/accounts/oauth/token",
                     "jwks_uri": ISSUER + "/.well-known/jwks.json"}
        elif path == "/api/accounts/oauth/token":
            assert "Authorization" not in headers
            value = self.wire.tokens
        elif path == "/.well-known/jwks.json":
            assert "Authorization" not in headers
            value = self.wire.signing[2]
        elif path == "/v1/models":
            value = {"models": [{"visibility": "hidden", "slug": "unlisted-model"},
                                {"visibility": "list", "slug": MODEL,
                                 "display_name": "Account-selected fixture model"}]}
        else:
            assert path == "/v1/responses" and method == "POST"
            request = json.loads(body)
            assert request["model"] == MODEL and request["store"] is False
            assert request["stream"] is True
            if request.get("instructions"):
                source = json.loads(request["input"][0]["content"])
                offset = source["text"].index(QUOTE)
                candidate = json.dumps({"citations": [{"source_ref": source["source_ref"],
                                        "start": offset, "end": offset + len(QUOTE),
                                        "quote": QUOTE}]})
            else:
                candidate = "Synthetic final"
            completion = {"type": "response.completed", "response": {
                "id": "synthetic-response", "model": MODEL, "status": "completed",
                "output": [{"type": "message", "role": "assistant", "status": "completed",
                            "content": [{"type": "output_text", "text": candidate}]}],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}}
            value = ("data: " + json.dumps(completion) + "\r\n\r\n").encode()
            self.response = _Response(value, stream=True, on_read=self.wire.on_model_read)
            return
        self.response = _Response(value)

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class _Wire:
    def __init__(self, signing):
        self.signing, self.tokens, self.requests = signing, {}, []
        self.connections, self.on_model_read = [], None

    def factory(self, host, *, port, timeout, context):
        assert host in {"auth.openai.com", "api.openai.com"} and port == 443
        assert timeout > 0 and context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        connection = _Connection(self, host)
        self.connections.append(connection)
        return connection


@pytest.fixture
def setup(tmp_path, monkeypatch, signing):
    def no_real_https(*_args, **_kwargs):
        pytest.fail("synthetic integration attempted real external HTTPS")

    monkeypatch.setattr("inference_service.oauth_http.http.client.HTTPSConnection", no_real_https)
    store = SiwcCredentialStore(tmp_path / "provider-private", authorized=True)
    host = store.initialize()
    wire = _Wire(signing)
    wall = [NOW]
    session = SiwcSession(host_id=host,
                          client=SiwcHttpsClient(authorized=True, connection_factory=wire.factory),
                          store=store, wall_clock=lambda: wall[0])
    return session, store, wire, wall


def _token(wire, *, nonce, client=CLIENT, subject=SUBJECT, updates=None):
    jwt, private, _ = wire.signing
    claims = {"iss": ISSUER, "aud": client, "sub": subject,
              "iat": NOW - 30, "exp": NOW + 3600, "nonce": nonce,
              "email": "synthetic@example.invalid", **(updates or {})}
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "synthetic-key"})


def _prepare(session, wire, *, returning=False, claim_updates=None, token_updates=None,
             client=CLIENT, subject=SUBJECT):
    attempt = session.begin(redirect_uri="http://127.0.0.1:23456/auth/callback",
                            authorized=True, returning=returning)
    query = parse_qs(urlsplit(attempt.authorization_url).query)
    wire.tokens = {"access_token": ACCESS, "refresh_token": REFRESH, "token_type": "Bearer",
                   "id_token": _token(wire, nonce=query["nonce"][0], client=client,
                                      subject=subject, updates=claim_updates),
                   "scope": " ".join(REQUESTED_SCOPES), "expires_in": 3600,
                   **(token_updates or {})}
    callback = "http://127.0.0.1:23456/auth/callback?" + urlencode({
        "state": query["state"][0], "code": "synthetic-private-code", "client_id": client})
    return attempt, callback


def _activate(setup):
    session, store, wire, wall = setup
    attempt, callback = _prepare(session, wire)
    session.complete(attempt, callback)
    return session, store, wire, wall


def _inventory(store):
    return {path.name: path.read_bytes() for path in store.directory.iterdir()}


def _request(model=MODEL):
    return InferenceRequest("session-synthetic-infer", model,
                            (InferenceMessage("user", "Synthetic input"),), timeout_seconds=3)


def test_oauth_rsa_private_restart_catalog_to_real_core_canonical_final(
    setup, tmp_path, monkeypatch
):
    session, store, wire, wall = _activate(setup)
    assert session.metadata()["operator_authenticated"] is False
    assert store.load(client_id=CLIENT, subject=SUBJECT).access_token == ACCESS
    if os.name == "nt":
        for name, data in _inventory(store).items():
            if name.endswith(".sealed"):
                assert data.startswith(b"jarvis-siwc-dpapi-v1\n")
                assert ACCESS.encode() not in data and REFRESH.encode() not in data
                assert SUBJECT.encode() not in data
    restarted = SiwcSession(
        host_id=store.host_id(), store=store,
        client=SiwcHttpsClient(authorized=True, connection_factory=wire.factory),
        wall_clock=lambda: wall[0],
    )
    restarted.load(client_id=CLIENT, subject=SUBJECT)
    catalog = restarted.catalog(authorized=True)
    assert [choice.slug for choice in catalog.choices] == [MODEL]
    provider = restarted.provider(catalog.select(MODEL).slug, authorized=True,
                                  connection_factory=wire.factory)
    core = _isolated_core(tmp_path / "core")
    core.synthesis_engine = SynthesisEngine(inference_port=provider, inference_model=MODEL,
        inference_provider_id="responses_plan", inference_evidence_mode="injected_transport")
    monkeypatch.setattr(core.operational_service, "execute",
                        lambda *_a, **_kw: pytest.fail("provider identity dispatched operation"))
    contract = replace(PilotContext("local-core-actor", "local-core-session").input(
        "validated-provider-core", TEXT), requested_autonomy_level="bounded_core_action",
        max_autonomy_level="bounded_core_action")
    result = core.handle_input(contract)
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.operation_dispatch is None and result.operation_result is None
    assert QUOTE in result.response_text
    assert "Evidence excerpts (untrusted input" in result.response_text
    canonical = core.memory_service.repository.fetch_recent_turns(result.session_id, 10)[-1]
    assert canonical.response_text == result.response_text
    persisted = core.observability_service.repository.list_events(
        request_id=result.request_id, event_names=("response_synthesized",), limit=10)
    assert len(persisted) == 1 and persisted[0].payload["extractive_status"] == "accepted"
    assert persisted[0].payload["extractive_evidence_mode"] == "injected_transport"
    metadata = json.dumps([restarted.metadata(), restarted.events(), catalog.metadata(),
                           persisted[0].payload], default=str)
    for private in (CLIENT, SUBJECT, ACCESS, REFRESH, "synthetic-private-code"):
        assert private not in metadata and private not in result.response_text
    assert all(conn.closed and conn.response.closed for conn in wire.connections)


@pytest.mark.parametrize("mutation", ["aud", "sub", "nonce", "issuer", "expired", "signature",
                                      "scope", "bearer", "missing_refresh", "callback_state",
                                      "callback_client", "callback_scope"],
                         ids=["aud", "sub", "nonce", "issuer", "expired", "signature",
                              "scope", "bearer", "refresh", "state", "client", "callback_scope"])
def test_unvalidated_login_never_activates_persists_or_grants_inference(setup, mutation):
    session, store, wire, _ = setup
    inventory = _inventory(store)
    claims = {"aud": "oaiapp_wrong"} if mutation == "aud" else (
        {"sub": ""} if mutation == "sub" else {"nonce": "wrong"} if mutation == "nonce" else
        {"iss": "https://invalid.example"} if mutation == "issuer" else
        {"exp": NOW - 6} if mutation == "expired" else None)
    attempt, callback = _prepare(session, wire, claim_updates=claims)
    if mutation == "signature":
        parts = wire.tokens["id_token"].split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        wire.tokens["id_token"] = ".".join(parts)
    if mutation in {"scope", "callback_scope"}:
        wire.tokens["scope"] = "openid profile email resource.invoke"
        callback += "&scope=" + DIRECT_SCOPE
    if mutation == "bearer":
        wire.tokens["token_type"] = "Basic"
    if mutation == "missing_refresh":
        del wire.tokens["refresh_token"]
    if mutation == "callback_state":
        callback = callback.replace("state=", "state=wrong")
    if mutation == "callback_client":
        callback = callback.replace(CLIENT, "dynamic_agent_client")
    with pytest.raises(SiwcError):
        session.complete(attempt, callback)
    assert session.metadata()["authenticated_provider_account"] is False
    assert _inventory(store) == inventory
    assert not any(request[2] == "/v1/responses" for request in wire.requests)
    with pytest.raises(SiwcError):
        session.catalog(authorized=True)
    with pytest.raises(SiwcError):
        session.provider(MODEL, authorized=True, connection_factory=wire.factory)
    if mutation.startswith("callback_") and mutation != "callback_scope":
        assert wire.requests == []


def test_failed_returning_identity_keeps_old_account_and_storage(setup):
    session, store, wire, _ = _activate(setup)
    session.catalog(authorized=True)
    provider = session.provider(MODEL, authorized=True, connection_factory=wire.factory)
    before = session.metadata(), _inventory(store)
    attempt, callback = _prepare(session, wire, returning=True, subject="different-subject")
    with pytest.raises(SiwcError, match="^siwc_id_token_invalid$"):
        session.complete(attempt, callback)
    assert session.metadata() == before[0] and _inventory(store) == before[1]
    assert provider.infer(_request()).status == "completed"


def test_callback_one_shot_even_after_success_no_token_replay(setup):
    session, _, wire, _ = setup
    attempt, callback = _prepare(session, wire)
    session.complete(attempt, callback)
    count = len(wire.requests)
    with pytest.raises(SiwcError, match="^siwc_attempt_invalid$"):
        session.complete(attempt, callback)
    assert len(wire.requests) == count


@pytest.mark.parametrize("operation", ["catalog", "provider", "refresh"])
def test_operations_require_distinct_explicit_authorization_after_login(setup, operation):
    session, _, wire, _ = _activate(setup)
    count = len(wire.requests)
    with pytest.raises(SiwcError):
        session.provider(MODEL) if operation == "provider" else getattr(session, operation)()
    assert len(wire.requests) == count


def test_expired_access_never_lists_models_and_no_automatic_refresh(setup):
    session, _, wire, wall = _activate(setup)
    wall[0] += 3600
    count = len(wire.requests)
    with pytest.raises(SiwcError, match="^siwc_credential_expired$"):
        session.catalog(authorized=True)
    assert len(wire.requests) == count


def test_unlisted_model_and_wrong_request_model_never_reach_https(setup):
    session, _, wire, _ = _activate(setup)
    session.catalog(authorized=True)
    count = len(wire.requests)
    with pytest.raises(SiwcError, match="^siwc_model_unavailable$"):
        session.provider("unlisted-model", authorized=True, connection_factory=wire.factory)
    provider = session.provider(MODEL, authorized=True, connection_factory=wire.factory)
    result = provider.infer(_request("unlisted-model"))
    assert result.status == "failed" and result.text == ""
    assert len(wire.requests) == count


@pytest.mark.parametrize("action", ["disconnect", "switch", "refresh", "cancel_stream"])
def test_issued_provider_fenced_before_or_during_lazy_stream(setup, action):
    session, store, wire, _ = _activate(setup)
    session.catalog(authorized=True)
    provider = session.provider(MODEL, authorized=True, connection_factory=wire.factory)
    count = len(wire.requests)
    if action == "disconnect":
        session.disconnect_local()
    elif action == "switch":
        session.load(client_id=CLIENT, subject=SUBJECT)
    elif action == "refresh":
        wire.tokens = {"access_token": "rotated-access", "token_type": "Bearer",
                       "expires_in": 3600, "refresh_token": "rotated-refresh"}
        session.refresh(authorized=True)
        count = len(wire.requests)
        assert store.load(client_id=CLIENT, subject=SUBJECT).refresh_token == "rotated-refresh"
    else:
        wire.on_model_read = session.disconnect_local
    result = provider.infer(_request())
    assert result.status == ("cancelled" if action == "cancel_stream" else "failed")
    assert result.text == ""
    assert sum(request[2] == "/v1/responses" for request in wire.requests[count:]) == (
        1 if action == "cancel_stream" else 0)
    assert all(connection.closed for connection in wire.connections)


def test_refresh_loads_latest_locked_tokens_and_replaces_rotating_pair(setup):
    session, store, wire, _ = _activate(setup)
    previous = store.load(client_id=CLIENT, subject=SUBJECT)
    store.save(replace(previous, access_token="other-process-access",
                       refresh_token="other-process-refresh"))
    wire.tokens = {"access_token": "new-access", "refresh_token": "new-refresh",
                   "token_type": "Bearer", "expires_in": 3600}
    session.refresh(authorized=True)
    refresh_request = next(request for request in reversed(wire.requests)
                           if request[2] == "/api/accounts/oauth/token")
    assert parse_qs(refresh_request[3].decode())["refresh_token"] == ["other-process-refresh"]
    assert "scope" not in parse_qs(refresh_request[3].decode())
    stored = store.load(client_id=CLIENT, subject=SUBJECT)
    assert stored.access_token == "new-access" and stored.refresh_token == "new-refresh"
    assert stored.scopes == previous.scopes and stored.id_token == previous.id_token


@pytest.mark.parametrize(
    "replacement", ["id_missing", "id_valid", "id_other_subject", "scope_removed"]
)
def test_refresh_optional_fields_keep_or_validate_prior_account(setup, replacement):
    session, store, wire, _ = _activate(setup)
    original = store.load(client_id=CLIENT, subject=SUBJECT)
    before = _inventory(store)
    wire.tokens = {"access_token": "new-access", "token_type": "Bearer", "expires_in": 3600}
    if replacement.startswith("id_") and replacement != "id_missing":
        subject = "other-subject" if replacement == "id_other_subject" else SUBJECT
        wire.tokens["id_token"] = _token(wire, nonce="unused-on-refresh", subject=subject)
    if replacement == "scope_removed":
        wire.tokens["scope"] = "openid resource.invoke"
    if replacement in {"id_other_subject", "scope_removed"}:
        with pytest.raises(SiwcError):
            session.refresh(authorized=True)
        assert _inventory(store) == before
    else:
        session.refresh(authorized=True)
        stored = store.load(client_id=CLIENT, subject=SUBJECT)
        assert stored.access_token == "new-access"
        assert stored.refresh_token == original.refresh_token
        assert stored.scopes == original.scopes


def test_cancelled_refresh_retains_persisted_pair(setup):
    session, store, wire, _ = _activate(setup)
    before, count = _inventory(store), len(wire.requests)
    cancelled = Event()
    cancelled.set()
    with pytest.raises(SiwcError, match="^siwc_cancelled$"):
        session.refresh(authorized=True, cancellation=cancelled)
    assert _inventory(store) == before and len(wire.requests) == count


def test_os_locked_store_refuses_competing_rotation_before_network(setup):
    session, store, wire, _ = _activate(setup)
    competing_store = SiwcCredentialStore(store.directory, authorized=True)
    before, count = _inventory(store), len(wire.requests)
    with competing_store.locked():
        with pytest.raises(SiwcError, match="^siwc_storage_busy$"):
            session.refresh(authorized=True)
    assert _inventory(store) == before and len(wire.requests) == count


@pytest.mark.parametrize("operation", ["complete", "refresh"])
def test_cancel_after_atomic_local_commit_keeps_active_and_persisted_credentials_consistent(
    setup, monkeypatch, operation
):
    session, store, wire, _ = setup
    if operation == "refresh":
        _activate(setup)
        wire.tokens = {"access_token": "committed-access", "refresh_token": "committed-refresh",
                       "token_type": "Bearer", "expires_in": 3600}
        original_save = store.save_locked
    else:
        original_save = store.save
        attempt, callback = _prepare(session, wire)
    cancel = Event()

    def committed_save(credentials):
        original_save(credentials)
        # Cancellation cannot undo a successful atomic replacement. The manager
        # must activate that same committed pair, not report a rollback it lacks.
        cancel.set()

    monkeypatch.setattr(store, "save_locked" if operation == "refresh" else "save", committed_save)
    if operation == "refresh":
        session.refresh(authorized=True, cancellation=cancel)
    else:
        session.complete(attempt, callback, cancellation=cancel)
    assert session.metadata()["authenticated_provider_account"] is True
    stored = store.load(client_id=CLIENT, subject=SUBJECT)
    session.catalog(authorized=True)
    assert wire.requests[-1][4]["Authorization"] == "Bearer " + stored.access_token


def test_wall_clock_failure_during_valid_login_is_sanitized_without_persistence(setup, monkeypatch):
    session, store, wire, _ = setup
    before = _inventory(store)
    attempt, callback = _prepare(session, wire)

    def private_failure():
        raise RuntimeError("private-clock-diagnostic-sentinel")

    monkeypatch.setattr(session, "_wall_clock", private_failure)
    with pytest.raises(SiwcError, match="^siwc_clock_invalid$") as caught:
        session.complete(attempt, callback)
    assert caught.value.__cause__ is None
    assert "private-clock" not in str(caught.value)
    assert _inventory(store) == before
    assert session.metadata()["authenticated_provider_account"] is False


def test_budget_clock_failure_before_refresh_io_is_sanitized_keeps_saved_tokens(setup, monkeypatch):
    session, store, wire, _ = _activate(setup)
    before, count = _inventory(store), len(wire.requests)
    clock, calls = session._clock, []

    def broken_remaining_clock():
        calls.append(None)
        if len(calls) == 2:
            raise RuntimeError("private-clock-diagnostic-sentinel")
        return clock()

    monkeypatch.setattr(session, "_clock", broken_remaining_clock)
    with pytest.raises(SiwcError, match="^siwc_clock_invalid$") as caught:
        session.refresh(authorized=True)
    assert caught.value.__cause__ is None
    assert "private-clock" not in str(caught.value)
    assert _inventory(store) == before and len(wire.requests) == count
