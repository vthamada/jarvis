"""OAuth/catalog HTTPS wiring evidence only; never requests real credentials."""

from __future__ import annotations

import json
import ssl
from threading import Event
from urllib.parse import parse_qs

import pytest
from inference_service.oauth_http import ModelCatalog, ModelChoice, SiwcHttpsClient
from inference_service.siwc_contracts import DIRECT_SCOPE, ISSUER, RESOURCE, SiwcError


class Response:
    def __init__(self, body=None, *, raw=None, status=200, content_type="application/json",
                 encoding="identity", chunks=None, on_read=None):
        self.body = raw if raw is not None else json.dumps(body).encode()
        self.status = status
        self.headers = {"Content-Type": content_type, "Content-Encoding": encoding}
        self.closed = False
        self.reads = []
        self.chunks = iter(chunks) if chunks is not None else None
        self.on_read = on_read

    def getheader(self, key, default=None):
        return self.headers.get(key, default)

    def read1(self, amount):
        self.reads.append(amount)
        if self.on_read:
            self.on_read()
        if self.chunks is not None:
            return next(self.chunks, b"")
        result, self.body = self.body[:amount], self.body[amount:]
        return result

    def close(self):
        self.closed = True


class Socket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, value):
        self.timeouts.append(value)


class Connection:
    def __init__(self, response, *, on_connect=None, on_request=None, on_response=None,
                 detach=False):
        self.response = response
        self.closed = False
        self.sock = Socket()
        self.original_socket = self.sock
        self.requests = []
        self.on_connect = on_connect
        self.on_request = on_request
        self.on_response = on_response
        self.detach = detach

    def connect(self):
        if self.on_connect:
            self.on_connect()

    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, body, headers))
        if self.on_request:
            self.on_request()

    def getresponse(self):
        if self.on_response:
            self.on_response()
        if self.detach:
            self.sock = None
        return self.response

    def close(self):
        self.closed = True


class Factory:
    def __init__(self, response, **kwargs):
        self.connection = Connection(response, **kwargs)
        self.calls = []

    def __call__(self, host, **kwargs):
        self.calls.append((host, kwargs))
        return self.connection


def discovery():
    return {"issuer": ISSUER, "authorization_endpoint": ISSUER + "/api/accounts/authorize",
            "token_endpoint": ISSUER + "/api/accounts/oauth/token",
            "jwks_uri": ISSUER + "/.well-known/jwks.json"}


def fixture(body=None, **kwargs):
    response = Response(discovery() if body is None else body, **kwargs)
    factory = Factory(response)
    return SiwcHttpsClient(authorized=True, connection_factory=factory), factory, response


def models(client, **kwargs):
    params = {"access_token": "access.private", "expires_at": 1000,
              "scopes": (DIRECT_SCOPE,), "wall_clock": lambda: 100}
    params.update(kwargs)
    return client.models(**params)


def exchange(client, **kwargs):
    params = {"client_id": "oaiapp_fixture", "code": "code.private",
              "code_verifier": "v" * 43,
              "redirect_uri": "http://127.0.0.1:12345/auth/callback"}
    params.update(kwargs)
    return client.auth_code(**params)


def test_discovery_fixed_tls_route_and_no_credentials():
    client, factory, response = fixture({**discovery(), "revocation_endpoint": "https://evil.test"})
    assert client.discovery() == discovery()
    host, options = factory.calls[0]
    assert host == "auth.openai.com" and options["port"] == 443
    assert options["context"].verify_mode == ssl.CERT_REQUIRED
    assert options["context"].check_hostname
    method, path, body, headers = factory.connection.requests[0]
    assert (method, path, body) == ("GET", "/.well-known/openid-configuration", None)
    assert "Authorization" not in headers
    assert response.closed and factory.connection.closed


@pytest.mark.parametrize("key", list(discovery()))
@pytest.mark.parametrize("replacement", [None, "https://evil.test", "https://auth.openai.com/"])
def test_discovery_endpoint_exact_match(key, replacement):
    doc = discovery()
    doc[key] = replacement
    client, _, response = fixture(doc)
    with pytest.raises(SiwcError, match="^siwc_discovery_invalid$"):
        client.discovery()
    assert response.closed


def test_jwks_route_without_authorization_and_no_claim_of_validation():
    client, factory, response = fixture({"keys": [{"kty": "RSA", "kid": "fixture"}]})
    assert client.jwks()["keys"][0]["kid"] == "fixture"
    assert factory.connection.requests[0][1] == "/.well-known/jwks.json"
    assert "Authorization" not in factory.connection.requests[0][3]
    assert response.closed


@pytest.mark.parametrize("keys", [None, {}, [], [1], [None], [{}] * 65], ids=[
    "null", "object", "empty", "integer", "null_key", "too_many"])
def test_jwks_shape_bounded(keys):
    client, _, _ = fixture({"keys": keys})
    with pytest.raises(SiwcError, match="^siwc_jwks_invalid$"):
        client.jwks()


def test_authorization_exchange_public_form_no_secret():
    token_response = {"access_token": "secret.access", "scope": DIRECT_SCOPE}
    client, factory, response = fixture(token_response)
    assert exchange(client) == token_response
    method, path, body, headers = factory.connection.requests[0]
    assert (method, path) == ("POST", "/api/accounts/oauth/token")
    assert parse_qs(body.decode()) == {
        "grant_type": ["authorization_code"], "client_id": ["oaiapp_fixture"],
        "code": ["code.private"], "code_verifier": ["v" * 43],
        "redirect_uri": ["http://127.0.0.1:12345/auth/callback"], "resource": [RESOURCE]}
    assert "Authorization" not in headers
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert "secret.access" not in repr(client)
    assert response.closed


def test_refresh_issued_registration_no_scope_or_secret():
    client, factory, _ = fixture({"access_token": "new.token"})
    client.refresh(client_id="oaiapp_fixture", refresh_token="refresh.private")
    assert parse_qs(factory.connection.requests[0][2].decode()) == {
        "grant_type": ["refresh_token"], "client_id": ["oaiapp_fixture"],
        "refresh_token": ["refresh.private"], "resource": [RESOURCE]}


@pytest.mark.parametrize("method", ["discovery", "jwks", "exchange", "refresh", "models"])
def test_disabled_no_network_even_discovery(method):
    factory = Factory(Response(discovery()))
    client = SiwcHttpsClient(connection_factory=factory)
    assert not factory.calls
    with pytest.raises(SiwcError, match="^siwc_network_not_authorized$"):
        if method == "exchange":
            exchange(client)
        elif method == "refresh":
            client.refresh(client_id="oaiapp_fixture", refresh_token="refresh.private")
        elif method == "models":
            models(client)
        else:
            getattr(client, method)()
    assert not factory.calls


@pytest.mark.parametrize("argument,bad", [
    ("client_id", "dynamic_agent_client"), ("client_id", "oaiapp_"),
    ("client_id", "oaiapp_a\r\nHeader:private"), ("code", "bad token"),
    ("code", ""), ("code_verifier", "v" * 42), ("code_verifier", "v" * 129),
    ("code_verifier", "v" * 42 + "="), ("code_verifier", None),
    ("redirect_uri", "http://localhost:12345/auth/callback"),
    ("redirect_uri", "http://127.0.0.1:12345/callback"),
    ("redirect_uri", "https://127.0.0.1:12345/auth/callback"),
    ("redirect_uri", "http://127.0.0.1:12345/auth/callback?token=private"),
    ("redirect_uri", "http://127.0.0.1:0/auth/callback"),
    ("redirect_uri", "http://user@127.0.0.1:12345/auth/callback"),
    ("redirect_uri", "http://127.0.0.1:012345/auth/callback"),
    ("redirect_uri", "http://127.0.0.1:65536/auth/callback"),
    ("redirect_uri", "http://127.0.0.1:12345/auth/callback#private"),
], ids=["dynamic", "empty_client", "client_injection", "code_space", "empty_code",
        "short_pkce", "long_pkce", "pkce_padding", "pkce_null", "localhost", "path",
        "https", "query", "zero_port", "userinfo", "noncanonical_port", "large_port", "fragment"])
def test_code_request_refused_before_socket(argument, bad):
    client, factory, _ = fixture()
    with pytest.raises(SiwcError, match="^siwc_token_request_invalid$"):
        exchange(client, **{argument: bad})
    assert not factory.calls


@pytest.mark.parametrize("params", [{"client_id": "dynamic_agent_client", "refresh_token": "t"},
                                    {"client_id": "oaiapp_fixture", "refresh_token": "a\nb"}])
def test_refresh_invalid_zero_io(params):
    client, factory, _ = fixture()
    with pytest.raises(SiwcError, match="^siwc_token_request_invalid$"):
        client.refresh(**params)
    assert not factory.calls


def test_catalog_filters_preserves_order_and_exact_selection():
    doc = {"models": [{"visibility": "hidden", "slug": "ignored"},
                       {"visibility": "list", "slug": "model-z", "display_name": "Modelo Z"},
                       {"visibility": "list", "slug": "model-a", "display_name": "Á Modelo A"}]}
    client, factory, response = fixture(doc)
    catalog = models(client)
    assert [choice.slug for choice in catalog.choices] == ["model-z", "model-a"]
    assert catalog.select("model-a").display_name == "Á Modelo A"
    assert catalog.metadata() == {"mode": "siwc_model_catalog", "authority": "none",
                                  "choice_count": 2, "evidence_mode": "injected_transport"}
    with pytest.raises(SiwcError, match="^siwc_model_unavailable$"):
        catalog.select("MODEL-A")
    assert "model-a" not in repr(catalog)
    assert factory.calls[0][0] == "api.openai.com"
    assert factory.connection.requests[0][:3] == ("GET", "/v1/models", None)
    assert factory.connection.requests[0][3]["Authorization"] == "Bearer access.private"
    assert response.closed


@pytest.mark.parametrize("doc", [
    {"data": []}, {"models": None}, {"models": {}}, {"models": [None]},
    {"models": [{}]}, {"models": [{"visibility": 1}]},
    {"models": [{"visibility": "list", "slug": "m"}]},
    {"models": [{"visibility": "list", "slug": "m", "display_name": ""}]},
    {"models": [{"visibility": "list", "slug": "m", "display_name": "a\u202eb"}]},
    {"models": [{"visibility": "list", "slug": "m\r", "display_name": "M"}]},
    {"models": [{"visibility": "list", "slug": "m", "display_name": "M"}] * 2},
    {"models": [{"visibility": "hidden"}] * 1025},
], ids=["wrong_schema", "null", "object", "null_model", "missing_visibility", "bad_visibility",
        "missing_name", "empty_name", "bidi_name", "slug_control", "duplicate", "too_many"])
def test_catalog_malformed_no_fallback(doc):
    client, _, response = fixture(doc)
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        models(client)
    assert response.closed


@pytest.mark.parametrize("kwargs,code", [
    ({"expires_at": 100}, "siwc_credential_expired"),
    ({"scopes": ()}, "siwc_plan_scope_missing"),
    ({"access_token": "token\r\nprivate"}, "siwc_credential_invalid"),
    ({"scopes": [DIRECT_SCOPE]}, "siwc_credential_invalid"),
    ({"scopes": (DIRECT_SCOPE, DIRECT_SCOPE)}, "siwc_credential_invalid"),
    ({"scopes": ("a b",)}, "siwc_credential_invalid"),
    ({"expires_at": float("nan")}, "siwc_credential_invalid"),
    ({"expires_at": True}, "siwc_credential_invalid"),
    ({"wall_clock": lambda: float("nan")}, "siwc_clock_invalid"),
], ids=["expired", "scope_missing", "token_injection", "scope_list", "duplicate_scope",
        "scope_space", "expiry_nan", "expiry_bool", "wall_nan"])
def test_catalog_credential_checks_zero_factory(kwargs, code):
    client, factory, _ = fixture({"models": []})
    with pytest.raises(SiwcError, match="^" + code + "$"):
        models(client, **kwargs)
    assert not factory.calls


@pytest.mark.parametrize("raw", [b'{"issuer":1,"issuer":2}', b'{"x":{"a":1,"a":2}}',
                                  b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
                                  b'{"x":"\\ud800"}', b'\xff', b'[]', b'{}x', b'',
                                  b'{"x":' + b'[' * 18 + b'0' + b']' * 18 + b'}'],
                         ids=["duplicate", "nested_duplicate", "nan", "infinity", "overflow",
                              "surrogate", "utf8", "array", "suffix", "empty", "depth"])
def test_strict_json_refuses_ambiguous_or_invalid_documents(raw):
    client, factory, response = fixture(raw=raw)
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        client.discovery()
    assert response.closed and factory.connection.closed


@pytest.mark.parametrize("status,body,code", [
    (400, {"error": "invalid_grant", "error_description": "secret.private"}, "siwc_invalid_grant"),
    (400, {"error": "invalid_client"}, "siwc_invalid_client"),
    (400, {"error": "secret.private"}, "siwc_http_refused"),
    (401, {"error": {}}, "siwc_authentication_refused"),
    (403, {"error": {}}, "siwc_permission_refused"),
    (429, {"error": {}}, "siwc_usage_limited"),
    (302, {}, "siwc_http_refused"), (500, {}, "siwc_http_refused"),
], ids=["invalid_grant", "invalid_client", "private_error", "401", "403", "429",
        "redirect", "server"])
def test_http_errors_fixed_no_response_echo_or_retry(status, body, code):
    client, factory, response = fixture(body, status=status)
    with pytest.raises(SiwcError, match="^" + code + "$") as caught:
        client.discovery()
    assert "private" not in str(caught.value)
    assert len(factory.calls) == 1 and response.closed and factory.connection.closed
    if status in {302, 500}:
        assert not response.reads


@pytest.mark.parametrize("kwargs", [{"content_type": "text/html"}, {"encoding": "gzip"},
                                    {"content_type": None}, {"encoding": None}])
def test_invalid_media_refused_without_read(kwargs):
    client, factory, response = fixture(**kwargs)
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        client.discovery()
    assert not response.reads and factory.connection.closed and response.closed


def test_body_bounded_reads_and_closes():
    client, factory, response = fixture(raw=b"x" * 262_145)
    with pytest.raises(SiwcError, match="^siwc_response_limit_exceeded$"):
        client.discovery()
    assert max(response.reads) <= 4096
    assert response.closed and factory.connection.closed


@pytest.mark.parametrize("chunk", ["text", None, bytearray(b"a"), b"a" * 4097],
                         ids=["str", "null", "bytearray", "oversize"])
def test_invalid_chunk_fixed_error(chunk):
    client, _, response = fixture(chunks=[chunk])
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        client.discovery()
    assert response.closed


@pytest.mark.parametrize("timeout", [0, -1, 121, True, float("inf"), float("nan"), "30"])
def test_timeout_invalid_zero_network(timeout):
    client, factory, _ = fixture()
    with pytest.raises(SiwcError, match="^siwc_timeout_invalid$"):
        client.discovery(timeout_seconds=timeout)
    assert not factory.calls


def test_cancelled_before_network_and_invalid_signal():
    client, factory, _ = fixture()
    cancel = Event()
    cancel.set()
    with pytest.raises(SiwcError, match="^siwc_cancelled$"):
        client.discovery(cancellation=cancel)
    with pytest.raises(SiwcError, match="^siwc_cancellation_invalid$"):
        client.discovery(cancellation=True)
    assert not factory.calls


@pytest.mark.parametrize("phase", ["connect", "request", "response", "read"])
def test_cancel_during_io_closes_and_no_extra_operation(phase):
    cancel = Event()
    response = Response(discovery(), on_read=cancel.set if phase == "read" else None)
    factory = Factory(response, **{"on_" + phase: cancel.set} if phase != "read" else {})
    client = SiwcHttpsClient(authorized=True, connection_factory=factory)
    with pytest.raises(SiwcError, match="^siwc_cancelled$"):
        client.discovery(cancellation=cancel)
    assert factory.connection.closed
    if phase == "read":
        assert response.closed


def test_expiry_during_response_no_catalog():
    wall = [100]
    response = Response({"models": []})
    factory = Factory(response, on_response=lambda: wall.__setitem__(0, 1000))
    client = SiwcHttpsClient(authorized=True, connection_factory=factory)
    with pytest.raises(SiwcError, match="^siwc_credential_expired$"):
        models(client, wall_clock=lambda: wall[0])
    assert response.closed and factory.connection.closed and not response.reads


def test_monotonic_deadline_closes_detached_socket_and_remaining_time():
    now = [0]
    response = Response(discovery(), on_read=lambda: now.__setitem__(0, now[0] + 2))
    factory = Factory(response, on_connect=lambda: now.__setitem__(0, 1), detach=True)
    client = SiwcHttpsClient(authorized=True, connection_factory=factory, clock=lambda: now[0])
    with pytest.raises(SiwcError, match="^siwc_timeout$"):
        client.discovery(timeout_seconds=3)
    assert factory.connection.original_socket.timeouts[-1] == 2
    assert factory.connection.closed and response.closed


@pytest.mark.parametrize("clock", [lambda: float("nan"), lambda: True])
def test_invalid_clock_before_factory(clock):
    factory = Factory(Response(discovery()))
    client = SiwcHttpsClient(authorized=True, connection_factory=factory, clock=clock)
    with pytest.raises(SiwcError, match="^siwc_clock_invalid$"):
        client.discovery()
    assert not factory.calls


def test_clock_backwards_after_connect_refused():
    now = [100]
    factory = Factory(Response(discovery()), on_connect=lambda: now.__setitem__(0, 99))
    client = SiwcHttpsClient(authorized=True, connection_factory=factory, clock=lambda: now[0])
    with pytest.raises(SiwcError, match="^siwc_clock_invalid$"):
        client.discovery()
    assert factory.connection.closed and not factory.connection.requests


@pytest.mark.parametrize("error,code", [(OSError("secret.private"), "siwc_transport_failed"),
                                      (TimeoutError("secret.private"), "siwc_timeout")])
def test_transport_failure_content_free_and_resources_closed(error, code):
    def fail():
        raise error

    factory = Factory(Response(discovery()), on_request=fail)
    client = SiwcHttpsClient(authorized=True, connection_factory=factory)
    with pytest.raises(SiwcError, match="^" + code + "$") as caught:
        client.discovery()
    assert factory.connection.closed and caught.value.__cause__ is None


def test_insecure_tls_context_zero_factory(monkeypatch):
    class Insecure:
        check_hostname = False
        verify_mode = ssl.CERT_NONE

    monkeypatch.setattr("inference_service.oauth_http.ssl.create_default_context", Insecure)
    client, factory, _ = fixture()
    with pytest.raises(SiwcError, match="^siwc_tls_verification_required$"):
        client.discovery()
    assert not factory.calls


@pytest.mark.parametrize("args", [{"authorized": 1}, {"connection_factory": 1}, {"clock": 1}])
def test_invalid_configuration(args):
    with pytest.raises(SiwcError, match="^siwc_transport_configuration_invalid$"):
        SiwcHttpsClient(**args)


def test_model_records_frozen_validated_and_metadata_only():
    choice = ModelChoice("fixture-model", "Fixture Model")
    catalog = ModelCatalog((choice,))
    assert "fixture-model" not in repr(choice)
    with pytest.raises(AttributeError):
        choice.slug = "changed"
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        ModelCatalog([choice])
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        ModelCatalog((choice, choice))
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        ModelCatalog((choice,), "live")
    assert catalog.metadata()["authority"] == "none"


@pytest.mark.parametrize("display_name", ["M\nprivate", "M\u2028private", "M\u2029private",
                                          "M\ufeffprivate", "M\ud800private", " "],
                         ids=["newline", "line_separator", "paragraph_separator", "bom",
                              "surrogate", "whitespace"])
def test_display_name_controls_refused(display_name):
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        ModelChoice("fixture", display_name)


def test_split_multibyte_utf8_is_decoded_after_complete_bounded_read():
    raw = json.dumps({"models": [{"visibility": "list", "slug": "fixture",
                                  "display_name": "Á voz"}]}, ensure_ascii=False).encode()
    client, _, _ = fixture(chunks=[bytes([value]) for value in raw])
    assert models(client).choices[0].display_name == "Á voz"


def test_escaped_duplicate_json_keys_refused():
    client, _, _ = fixture(raw=b'{"keys":[], "\\u006beys":[{}]}')
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        client.jwks()


def test_no_factory_branch_stays_fixed_tls_without_real_network(monkeypatch):
    factory = Factory(Response(discovery()))
    monkeypatch.setattr("inference_service.oauth_http.http.client.HTTPSConnection", factory)
    client = SiwcHttpsClient(authorized=True)
    assert client.evidence_mode == "fixed_https_transport"
    assert client.discovery() == discovery()
    assert factory.calls[0][0] == "auth.openai.com"
    assert factory.connection.closed


def test_factory_error_never_echoes_credentials_and_no_retry():
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise OSError("access.private refresh.private")

    client = SiwcHttpsClient(authorized=True, connection_factory=fail)
    with pytest.raises(SiwcError, match="^siwc_transport_failed$"):
        models(client)
    assert len(calls) == 1


def test_credential_clock_exception_before_factory():
    def broken_clock():
        raise RuntimeError("private.local.details")

    client, factory, _ = fixture({"models": []})
    with pytest.raises(SiwcError, match="^siwc_clock_invalid$"):
        models(client, wall_clock=broken_clock)
    assert not factory.calls


def test_scope_unicode_and_oversized_token_refused_before_factory():
    client, factory, _ = fixture({"models": []})
    for overrides in ({"scopes": ("private\u202e",)}, {"access_token": "t" * 16_385}):
        with pytest.raises(SiwcError, match="^siwc_credential_invalid$"):
            models(client, **overrides)
    assert not factory.calls


def test_successful_empty_catalog_never_invents_a_fallback_model():
    client, _, _ = fixture({"models": []})
    catalog = models(client)
    assert catalog.choices == ()
    with pytest.raises(SiwcError, match="^siwc_model_unavailable$"):
        catalog.select("gpt-default")
