"""OAuth transactions, not live account or network evidence."""

from __future__ import annotations

import base64
import copy
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from inference_service.oauth_flow import AuthorizationAttempt, SiwcAuthorizationFlow
from inference_service.siwc_contracts import (
    DIRECT_SCOPE,
    ISSUER,
    REQUESTED_SCOPES,
    RESOURCE,
    SiwcError,
    VerifiedIdentity,
)

HOST = "urn:uuid:3ab59e96-7cd8-4eb1-9161-ebd1e10e5499"
REDIRECT = "http://127.0.0.1:1455/auth/callback"
IDENTITY = VerifiedIdentity("oaiapp_test_account", "account-subject", "local@example.test")


class Clock:
    now = 10.0

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def flow(clock):
    return SiwcAuthorizationFlow(host_id=HOST, clock=clock)


def begin(flow, **kwargs):
    return flow.begin(redirect_uri=REDIRECT, authorized=True, **kwargs)


def parameters(attempt):
    query = parse_qs(urlsplit(attempt.authorization_url).query)
    return {key: value[0] for key, value in query.items()}


def callback(attempt, **kwargs):
    data = {"state": parameters(attempt)["state"], "code": "fixture-code",
            "client_id": "oaiapp_new"}
    data.update(kwargs)
    return REDIRECT + "?" + urlencode(data)


def refused(flow, attempt, url, code=None):
    with pytest.raises(SiwcError) as error:
        flow.finish(attempt, url)
    if code is not None:
        assert error.value.code == code
    assert flow.metadata()["pending"] is False
    with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
        flow.finish(attempt, callback(attempt))


def test_initial_url_and_exchange(flow):
    attempt = begin(flow)
    query = parameters(attempt)
    assert urlsplit(attempt.authorization_url).scheme == "https"
    assert attempt.authorization_url.startswith(ISSUER + "/api/accounts/authorize?")
    assert query["client_id"] == "dynamic_agent_client"
    assert query["agent_name_hint"] == "Jarvis"
    assert query["ext_agent_host_id"] == HOST
    assert query["redirect_uri"] == REDIRECT
    assert query["scope"].split() == list(REQUESTED_SCOPES)
    assert query["resource"] == RESOURCE
    assert query["response_type"] == "code"
    assert query["code_challenge_method"] == "S256"
    assert len(query["state"]) >= 43 and len(query["nonce"]) >= 43
    exchange = flow.finish(attempt, callback(attempt, scope=DIRECT_SCOPE))
    assert exchange.client_id == "oaiapp_new"
    assert exchange.code == "fixture-code"
    assert exchange.nonce == query["nonce"]
    assert exchange.redirect_uri == REDIRECT and exchange.resource == RESOURCE
    assert exchange.selected_identity is None
    expected = base64.urlsafe_b64encode(hashlib.sha256(exchange.code_verifier.encode()).digest())
    assert query["code_challenge"] == expected.decode().rstrip("=")
    assert not hasattr(exchange, "scopes")
    with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
        flow.finish(attempt, callback(attempt))


@pytest.mark.parametrize("with_client", [False, True])
def test_returning_identity_and_hints(flow, with_client):
    attempt = begin(flow, selected_identity=IDENTITY, id_token_hint="old.id.token",
                    login_hint=IDENTITY.email)
    query = parameters(attempt)
    assert query["client_id"] == IDENTITY.client_id
    assert "agent_name_hint" not in query
    assert query["id_token_hint"] == "old.id.token" and query["login_hint"] == IDENTITY.email
    data = {"state": query["state"], "code": "returned-code"}
    if with_client:
        data["client_id"] = IDENTITY.client_id
    exchange = flow.finish(attempt, REDIRECT + "?" + urlencode(data))
    assert exchange.client_id == IDENTITY.client_id
    assert exchange.selected_identity == IDENTITY
    assert exchange.selected_identity is not IDENTITY


def test_returning_mismatch_not_account_switch(flow):
    attempt = begin(flow, selected_identity=IDENTITY)
    refused(flow, attempt, callback(attempt), "siwc_client_mismatch")


@pytest.mark.parametrize("with_client", [False, True])
def test_invalid_grant_retry_fresh_pkce_without_claimed_identity(flow, with_client):
    original = begin(flow)
    original_query = parameters(original)
    issued_client = flow.finish(original, callback(original)).client_id
    attempt = begin(flow, registration_client_id=issued_client)
    query = parameters(attempt)
    assert query["client_id"] == issued_client
    assert "agent_name_hint" not in query
    assert "id_token_hint" not in query and "login_hint" not in query
    for key in ("state", "nonce", "code_challenge"):
        assert query[key] != original_query[key]
    data = {"state": query["state"], "code": "fresh-code"}
    if with_client:
        data["client_id"] = issued_client
    exchange = flow.finish(attempt, REDIRECT + "?" + urlencode(data))
    assert exchange.client_id == issued_client and exchange.selected_identity is None


def test_registration_retry_client_must_match(flow):
    attempt = begin(flow, registration_client_id="oaiapp_previous")
    refused(flow, attempt, callback(attempt), "siwc_client_mismatch")


@pytest.mark.parametrize("client", ["", "dynamic_agent_client", "unissued", True, 1])
def test_registration_retry_requires_issued_client(flow, client):
    with pytest.raises(SiwcError, match="siwc_client_invalid"):
        begin(flow, registration_client_id=client)


def test_registration_retry_cannot_mix_identity_or_hints(flow):
    with pytest.raises(SiwcError, match="siwc_client_invalid"):
        begin(flow, registration_client_id="oaiapp_previous", selected_identity=IDENTITY)
    with pytest.raises(SiwcError, match="siwc_hint_invalid"):
        begin(flow, registration_client_id="oaiapp_previous", id_token_hint="opaque.id.token")


@pytest.mark.parametrize("client_id",
                         [None, "", "dynamic_agent_client", "oaiapp_", "other", "oaiapp_é"])
def test_initial_issued_client_required(flow, client_id):
    attempt = begin(flow)
    data = {"state": parameters(attempt)["state"], "code": "code"}
    if client_id is not None:
        data["client_id"] = client_id
    refused(flow, attempt, REDIRECT + "?" + urlencode(data))


@pytest.mark.parametrize("authorized", [False, None, 1, "yes", [], {}])
def test_opt_in_exact_boolean(flow, authorized):
    with pytest.raises(SiwcError, match="siwc_authorization_required"):
        flow.begin(redirect_uri=REDIRECT, authorized=authorized)
    assert not flow.metadata()["pending"]


@pytest.mark.parametrize("redirect", [
    "http://localhost:1455/auth/callback", "https://127.0.0.1:1455/auth/callback",
    "http://127.0.0.2:1455/auth/callback", "http://[::1]:1455/auth/callback",
    "http://127.0.0.1:0/auth/callback", "http://127.0.0.1:65536/auth/callback",
    "http://127.0.0.1:01455/auth/callback", "http://127.0.0.1:1455/callback",
    REDIRECT + "?", REDIRECT + "#", REDIRECT + "/", REDIRECT + "\n",
    REDIRECT.replace("127.0.0.1", "user@127.0.0.1"),
    REDIRECT.replace("/auth", "/x/../auth"), REDIRECT.replace("auth", "%61uth"),
    " " + REDIRECT, None, 123,
])
def test_redirect_exact(flow, redirect):
    with pytest.raises(SiwcError, match="siwc_redirect_invalid"):
        flow.begin(redirect_uri=redirect, authorized=True)


@pytest.mark.parametrize("port", [1, 65535, 54321])
def test_supported_ports(flow, port):
    uri = f"http://127.0.0.1:{port}/auth/callback"
    attempt = flow.begin(redirect_uri=uri, authorized=True)
    data = {"state": parameters(attempt)["state"], "code": "code", "client_id": "oaiapp_new"}
    assert flow.finish(attempt, uri + "?" + urlencode(data)).redirect_uri == uri


@pytest.mark.parametrize("timeout",
                         [0, -1, 600.1, float("inf"), float("nan"), True, None, "300", 10 ** 400])
def test_timeout_guard(flow, timeout):
    with pytest.raises(SiwcError, match="siwc_timeout_invalid"):
        begin(flow, timeout_seconds=timeout)


@pytest.mark.parametrize("hint", ["", "wrong@example.test", "local@example.test\n", 12])
def test_login_hint_must_selected_email(flow, hint):
    with pytest.raises(SiwcError, match="siwc_hint_invalid"):
        begin(flow, selected_identity=IDENTITY, login_hint=hint)


@pytest.mark.parametrize("hint", ["", "x\ny", "x y", "é", "x" * 16385, 4],
                         ids=["empty", "newline", "space", "unicode", "oversize", "integer"])
def test_id_hint_guard(flow, hint):
    with pytest.raises(SiwcError, match="siwc_hint_invalid"):
        begin(flow, selected_identity=IDENTITY, id_token_hint=hint)


@pytest.mark.parametrize("hint_key", ["login_hint", "id_token_hint"])
def test_new_registration_cannot_have_hints(flow, hint_key):
    with pytest.raises(SiwcError, match="siwc_hint_invalid"):
        begin(flow, **{hint_key: "associated-only-with-selected-account"})


@pytest.mark.parametrize("mutation", [
    lambda url: url.replace("127.0.0.1", "localhost"),
    lambda url: url.replace(":1455/", ":1456/"),
    lambda url: url.replace("http:", "https:"),
    lambda url: url.replace("/auth/callback", "/callback"),
    lambda url: url.replace("/auth/callback", "/auth/../auth/callback"),
    lambda url: url.replace("/auth/callback", "/%61uth/callback"),
    lambda url: url.replace("127.0.0.1", "user@127.0.0.1"),
    lambda url: url + "#anything", lambda url: " " + url, lambda url: url + "\n",
    lambda url: url + "&state=duplicate", lambda url: url + "&%73tate=duplicate",
    lambda url: url + "&unknown=value", lambda url: url + "&code=duplicate",
    lambda url: url + "&scope=bad%", lambda url: url + "&scope=bad%GG",
    lambda url: url + "&scope=%FF", lambda url: url + "&scope=%C0%AF",
    lambda url: url + "&scope=%00", lambda url: url + "&scope=%0A",
    lambda url: url + "&scope=%7F", lambda url: url + "&scope=",
    lambda url: url + "&", lambda url: url + "&scope", lambda url: url.replace("?", "??"),
])
def test_malformed_callbacks_are_consumed(flow, mutation):
    attempt = begin(flow)
    refused(flow, attempt, mutation(callback(attempt)))


@pytest.mark.parametrize("code", ["", "a b", "a\nb", "a\x00b", "é", "a" * 4097],
                         ids=["empty", "space", "newline", "nul", "unicode", "oversize"])
def test_code_guard(flow, code):
    attempt = begin(flow)
    refused(flow, attempt, callback(attempt, code=code))


@pytest.mark.parametrize("url", [None, 13, "", "x" * 32769],
                         ids=["none", "integer", "empty", "oversize"])
def test_callback_type_and_size_guard(flow, url):
    attempt = begin(flow)
    refused(flow, attempt, url)


def test_state_precedes_error_handling(flow):
    attempt = begin(flow)
    url = REDIRECT + "?" + urlencode({"state": "wrong", "error": "access_denied"})
    refused(flow, attempt, url, "siwc_state_invalid")


def test_denial_sanitized_and_consumed(flow):
    attempt = begin(flow)
    url = REDIRECT + "?" + urlencode({"state": parameters(attempt)["state"],
                                     "error": "private-error",
                                     "error_description": "private-message"})
    refused(flow, attempt, url, "siwc_authorization_denied")


def test_error_with_code_is_ambiguous(flow):
    attempt = begin(flow)
    refused(flow, attempt, callback(attempt, error="access_denied"), "siwc_callback_invalid")


def test_error_description_without_error(flow):
    attempt = begin(flow)
    refused(flow, attempt, callback(attempt, error_description="private-message"),
            "siwc_callback_invalid")


@pytest.mark.parametrize("state", ["", "wrong", "é", "a" * 1000])
def test_state_guard(flow, state):
    attempt = begin(flow)
    refused(flow, attempt, callback(attempt, state=state))


def test_nonce_state_challenge_change_and_old_attempt_invalidated(flow):
    old = begin(flow)
    current = begin(flow)
    old_query, query = parameters(old), parameters(current)
    for key in ("state", "nonce", "code_challenge"):
        assert query[key] != old_query[key]
    refused(flow, old, callback(old), "siwc_attempt_invalid")
    # A finish call is one-shot even if its handle is obsolete.
    with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
        flow.finish(current, callback(current))


@pytest.mark.parametrize("operation", [copy.copy, copy.deepcopy, lambda x: replace(x),
                                      lambda x: AuthorizationAttempt(x.authorization_url,
                                                                     x.deadline)])
def test_copied_handle_refused(flow, operation):
    attempt = begin(flow)
    refused(flow, operation(attempt), callback(attempt), "siwc_attempt_invalid")


@pytest.mark.parametrize("field,value", [("authorization_url", "changed"), ("deadline", 99999.0)])
def test_tamper_refused(flow, field, value):
    attempt = begin(flow)
    original_callback = callback(attempt)
    object.__setattr__(attempt, field, value)
    with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
        flow.finish(attempt, original_callback)
    assert not flow.metadata()["pending"]


def test_expiry_exact_boundary(flow, clock):
    attempt = begin(flow, timeout_seconds=2)
    clock.now = 12.0
    refused(flow, attempt, callback(attempt), "siwc_attempt_expired")


def test_cancel_and_restart(flow):
    attempt = begin(flow)
    query = parameters(attempt)
    flow.cancel()
    refused(flow, attempt, callback(attempt), "siwc_attempt_invalid")
    new = begin(flow)
    assert parameters(new)["state"] != query["state"]
    assert flow.finish(new, callback(new)).code == "fixture-code"


def test_race_only_one_exchange(flow):
    attempt = begin(flow)
    url = callback(attempt)

    def finish():
        try:
            return flow.finish(attempt, url)
        except SiwcError:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: finish(), range(16)))
    assert sum(result is not None for result in results) == 1


def test_repr_and_metadata_have_no_sensitive_fields(flow):
    attempt = begin(flow, selected_identity=IDENTITY, id_token_hint="secret.id.token",
                    login_hint=IDENTITY.email)
    assert repr(flow) == "SiwcAuthorizationFlow()"
    before = repr(attempt) + repr(flow.metadata())
    exchange = flow.finish(attempt, callback(attempt, client_id=IDENTITY.client_id))
    after = repr(exchange) + repr(flow.metadata())
    for secret in ("secret.id.token", IDENTITY.email, IDENTITY.subject, IDENTITY.client_id,
                   parameters(attempt)["state"], exchange.nonce, exchange.code_verifier,
                   "fixture-code", REDIRECT):
        assert secret not in before + after
    assert flow.metadata()["authority"] == "none"
    assert flow.metadata()["automatic_network"] is False


@pytest.mark.parametrize("now", [float("inf"), float("nan"), True, None, "10"])
def test_invalid_clock_refused(flow, clock, now):
    clock.now = now
    with pytest.raises(SiwcError, match="siwc_clock_invalid"):
        begin(flow)


def test_clock_error_sanitized_and_consumed():
    clock = Clock()
    flow = SiwcAuthorizationFlow(host_id=HOST, clock=clock)
    attempt = begin(flow)

    def fail():
        raise ValueError("private clock message")

    flow._clock = fail
    refused(flow, attempt, callback(attempt), "siwc_clock_invalid")


def test_no_network_browser_files_or_environment(monkeypatch):
    import builtins
    import os
    import socket
    import webbrowser

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(webbrowser, "open", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(os, "getenv", forbidden)
    flow = SiwcAuthorizationFlow(host_id=HOST, clock=Clock())
    attempt = begin(flow)
    assert flow.finish(attempt, callback(attempt)).client_id == "oaiapp_new"


@pytest.mark.parametrize("host", [None, "", "hostname", "user@example.test",
                                 "urn:uuid:3ab59e96-7cd8-1eb1-9161-ebd1e10e5499",
                                 "urn:uuid:3AB59E96-7CD8-4EB1-9161-EBD1E10E5499"])
def test_invalid_host_id_rejected(host):
    with pytest.raises(SiwcError, match="siwc_flow_invalid"):
        SiwcAuthorizationFlow(host_id=host)


def test_selected_identity_cannot_be_unverified_mapping(flow):
    with pytest.raises(SiwcError, match="siwc_identity_invalid"):
        begin(flow, selected_identity={"client_id": "oaiapp_new", "subject": "unverified"})


def test_identity_is_snapshotted_before_callback(flow):
    identity = VerifiedIdentity("oaiapp_original", "original", "original@example.test")
    attempt = begin(flow, selected_identity=identity)
    object.__setattr__(identity, "client_id", "oaiapp_switched")
    url = callback(attempt, client_id="oaiapp_original")
    assert flow.finish(attempt, url).selected_identity.client_id == "oaiapp_original"


def test_callback_scope_not_permission(flow):
    attempt = begin(flow)
    exchange = flow.finish(attempt, callback(attempt, scope="not-granted-to-provider"))
    assert exchange.client_id == "oaiapp_new"
    assert not hasattr(exchange, "scopes")


def test_unknown_handle_consumes_pending(flow):
    attempt = begin(flow)
    with pytest.raises(SiwcError, match="siwc_attempt_invalid"):
        flow.finish(None, callback(attempt))
    assert not flow.metadata()["pending"]


def test_percent_utf8_scope_can_be_ignored_without_lossy_decode(flow):
    attempt = begin(flow)
    assert flow.finish(attempt, callback(attempt, scope="perfil-válido")).client_id == "oaiapp_new"


def test_callback_plus_is_form_semantics(flow):
    attempt = begin(flow)
    assert flow.finish(attempt, callback(attempt, scope="openid profile")).client_id == "oaiapp_new"


def test_escaped_duplicate_keys_rejected(flow):
    attempt = begin(flow)
    refused(flow, attempt, callback(attempt) + "&%63lient_id=oaiapp_attacker")


def test_timeout_deadline_overflow_rejected(clock):
    clock.now = 1e308
    flow = SiwcAuthorizationFlow(host_id=HOST, clock=clock)
    with pytest.raises(SiwcError, match="siwc_timeout_invalid"):
        begin(flow)
