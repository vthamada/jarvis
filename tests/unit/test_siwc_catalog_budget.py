"""Synthetic endpoint-local byte budgets; no account, network or model acceptance."""

from __future__ import annotations

import json
import ssl
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.siwc_contracts import DIRECT_SCOPE, SiwcError

LEGACY = 262144
CATALOG = 2097152
LARGE = LEGACY + 8192
TOKEN = "synthetic.access"


def rows(count=2):
    return [{"visibility": "list", "slug": f"model-{index:04d}",
             "display_name": f"Synthetic model {index}"} for index in range(count)]


def padded(document=None, *, size=LARGE):
    value = {"models": rows()} if document is None else document
    bare = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    prefix = bare[:-1] + b',"synthetic_metadata_padding":"'
    suffix = b'"}'
    assert len(prefix) + len(suffix) <= size
    return prefix + b"x" * (size - len(prefix) - len(suffix)) + suffix


class Response:
    """Offset-based reader, not repeated whole-body slicing for large fixtures."""

    def __init__(self, raw, *, status=200, content_type="application/json",
                 encoding="identity", on_read=None, cleanup_error=False):
        self.raw, self.offset, self.status = raw, 0, status
        self.headers = {"Content-Type": content_type, "Content-Encoding": encoding}
        self.reads, self.closed, self.close_calls = [], False, 0
        self.on_read, self.cleanup_error = on_read, cleanup_error

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read1(self, amount):
        self.reads.append(amount)
        chunk = self.raw[self.offset:self.offset + amount]
        self.offset += len(chunk)
        if self.on_read:
            self.on_read(self)
        return chunk

    def close(self):
        self.close_calls += 1
        self.closed = True
        if self.cleanup_error:
            raise OSError("synthetic.private.response")


class Socket:
    def __init__(self):
        self.timeouts = []

    def settimeout(self, timeout):
        self.timeouts.append(timeout)


class Connection:
    def __init__(self, response, *, cleanup_error=False):
        self.response, self.sock = response, Socket()
        self.requests, self.connected, self.closed, self.close_calls = [], False, False, 0
        self.cleanup_error = cleanup_error

    def connect(self):
        self.connected = True

    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, body, headers))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True
        self.close_calls += 1
        if self.cleanup_error:
            raise OSError("synthetic.private.connection")


def fixture(raw=None, *, clock=lambda: 0, authorized=True, connection_cleanup=False, **kwargs):
    response = Response(padded() if raw is None else raw, **kwargs)
    connection = Connection(response, cleanup_error=connection_cleanup)
    calls = []

    def factory(host, **options):
        calls.append((host, options))
        return connection

    client = SiwcHttpsClient(authorized=authorized, connection_factory=factory, clock=clock)
    return client, response, connection, calls


def models(client, **overrides):
    options = {"access_token": TOKEN, "expires_at": 1000, "scopes": (DIRECT_SCOPE,),
               "wall_clock": lambda: 100, "timeout_seconds": 20}
    options.update(overrides)
    return client.models(**options)


def call_endpoint(client, endpoint, **options):
    if endpoint == "models":
        return models(client, **options)
    if endpoint == "exchange":
        return client.auth_code(client_id="oaiapp_synthetic", code="synthetic.code",
                                code_verifier="v" * 43,
                                redirect_uri="http://127.0.0.1:12345/auth/callback", **options)
    if endpoint == "refresh":
        return client.refresh(client_id="oaiapp_synthetic", refresh_token="synthetic.refresh",
                              **options)
    return getattr(client, endpoint)(**options)


def assert_closed(response, connection, calls):
    assert response.closed and connection.closed
    assert response.close_calls == connection.close_calls == 1
    assert len(calls) == len(connection.requests) == 1


@pytest.mark.parametrize("size", [LEGACY + 1, LARGE, CATALOG - 1, CATALOG])
def test_valid_large_catalog_inclusive_byte_cap(size):
    client, response, connection, calls = fixture(padded(size=size))
    catalog = models(client)
    assert [choice.slug for choice in catalog.choices] == ["model-0000", "model-0001"]
    assert catalog.metadata() == {"mode": "siwc_model_catalog", "authority": "none",
                                  "choice_count": 2, "evidence_mode": "injected_transport"}
    assert response.offset == size and max(response.reads) <= 4096
    assert_closed(response, connection, calls)
    if size == CATALOG:
        assert response.reads[-1] == 1  # Mandatory EOF probe; never reads beyond cap+1.
        assert len(response.reads) == CATALOG // 4096 + 1


@pytest.mark.parametrize("size", [CATALOG + 1, CATALOG + 4096, CATALOG * 2])
def test_large_catalog_cap_plus_one_refused_without_retry(size):
    client, response, connection, calls = fixture(padded(size=size))
    with pytest.raises(SiwcError, match="^siwc_response_limit_exceeded$"):
        models(client)
    assert response.offset == CATALOG + 1 and response.reads[-1] == 1
    assert max(response.reads) == 4096
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("endpoint", ["discovery", "jwks", "exchange", "refresh"])
def test_other_public_successes_keep_legacy_cap(endpoint):
    client, response, connection, calls = fixture(padded(size=LEGACY + 1))
    with pytest.raises(SiwcError, match="^siwc_response_limit_exceeded$"):
        call_endpoint(client, endpoint)
    assert response.offset == LEGACY + 1 and response.reads[-1] == 1
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("endpoint", ["discovery", "jwks", "exchange", "refresh", "models"])
@pytest.mark.parametrize("status", [400, 401, 403, 429])
def test_all_error_responses_keep_legacy_cap(endpoint, status):
    client, response, connection, calls = fixture(
        padded({"error": "invalid_grant", "detail": "synthetic.private.error"}, size=LEGACY + 1),
        status=status)
    with pytest.raises(SiwcError, match="^siwc_response_limit_exceeded$"):
        call_endpoint(client, endpoint)
    assert response.offset == LEGACY + 1 and response.reads[-1] == 1
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("host,path,method", [
    ("api.openai.com", "/v1/models", "POST"),
    ("api.openai.com", "/v1/models", "get"),
    ("auth.openai.com", "/v1/models", "GET"),
    ("API.OPENAI.COM", "/v1/models", "GET"),
    ("api.openai.com", "/v1/models/", "GET"),
    ("api.openai.com", "/v1/models?selection=all", "GET"),
    ("api.openai.com", "/v1/Models", "GET"),
    ("api.openai.com", "/v1/responses", "POST"),
])
def test_private_budget_selector_requires_exact_tuple(host, path, method):
    client, response, connection, calls = fixture(padded(size=LEGACY + 1))
    with pytest.raises(SiwcError, match="^siwc_response_limit_exceeded$"):
        client._request(host, path, method, timeout_seconds=20, cancellation=None)
    assert response.offset == LEGACY + 1
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("status", [201, 204, 301, 302, 307, 308, 500, 503, True, "200"])
def test_nonaccepted_statuses_and_redirects_refused_before_body(status):
    client, response, connection, calls = fixture(padded(size=CATALOG), status=status)
    with pytest.raises(SiwcError, match="^siwc_http_refused$"):
        models(client)
    assert response.offset == 0 and not response.reads
    assert_closed(response, connection, calls)


def test_large_catalog_filters_order_exact_slug_selection_and_no_fallback():
    candidates = [{"visibility": "hidden", "slug": "not-a-choice"},
                  {"visibility": "list", "slug": "model-z", "display_name": "Synthetic Z"},
                  {"visibility": "list", "slug": "Model-A", "display_name": "Á synthetic A"}]
    client, response, connection, calls = fixture(padded({"models": candidates}))
    catalog = models(client)
    assert [choice.slug for choice in catalog.choices] == ["model-z", "Model-A"]
    assert catalog.select("Model-A").display_name == "Á synthetic A"
    for invalid in ["model-a", "model-z ", "Model", ["Model-A"], "not-a-choice", "gpt-default"]:
        with pytest.raises(SiwcError, match="^siwc_model_unavailable$"):
            catalog.select(invalid)
    assert_closed(response, connection, calls)


def test_large_catalog_1024_entries_remain_allowed():
    client, response, connection, calls = fixture(padded({"models": rows(1024)}))
    assert len(models(client).choices) == 1024
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("candidates", [rows(1025),
    [{"visibility": "hidden"}] * 1025, [rows()[0], rows()[0]],
    [{"visibility": "list", "slug": "bad slug", "display_name": "Synthetic"}],
    [{"visibility": "list", "slug": "valid", "display_name": "x\u200by"}],
    [{"visibility": "list", "slug": "valid", "display_name": "x" * 257}],
    [{"visibility": "list", "slug": "x" * 161, "display_name": "Synthetic"}],
    None, {}, [None], [3]], ids=["1025", "1025_hidden", "duplicate_slugs", "slug_space",
    "control_display", "display_limit", "slug_limit", "null", "object", "null_entry", "integer"])
def test_large_catalog_cardinality_and_shape_not_relaxed(candidates):
    client, response, connection, calls = fixture(padded({"models": candidates}))
    with pytest.raises(SiwcError, match="^siwc_catalog_invalid$"):
        models(client)
    assert response.offset > LEGACY
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("raw", [
    b'{"models":[],"models":[]}', b'{"models":[],"\\u006dodels":[]}',
    b'{"models":[],"nested":{"x":1,"x":2}}', b'{"models":[],"bad":NaN}',
    b'{"models":[],"bad":Infinity}', b'{"models":[],"bad":1e999}',
    b'{"models":[],"bad":"\\ud800"}', b'{"models":[],"bad":"\xff"}',
    b'{"models":[],"bad":"\xc3"}', b'{"models":[],}', b'[]', b'null',
    b'{"models":[]} {"models":[]}', b'\xef\xbb\xbf{"models":[]}',
], ids=["duplicate", "escaped_duplicate", "nested_duplicate", "nan", "infinity",
    "overflow", "surrogate", "utf8_invalid", "utf8_incomplete", "trailing_comma",
    "array_root", "null_root", "second_object", "bom"])
def test_large_payload_json_strictness_not_relaxed(raw):
    raw += b" " * (LARGE - len(raw))
    client, response, connection, calls = fixture(raw)
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        models(client)
    assert response.offset == LARGE
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("depth,accepted", [(15, True), (16, False), (17, False)])
def test_large_catalog_json_depth_limit_stays_16(depth, accepted):
    nested = 0
    for _ in range(depth):
        nested = [nested]
    client, response, connection, calls = fixture(padded({"models": rows(), "nested": nested}))
    if accepted:
        assert len(models(client).choices) == 2
    else:
        with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
            models(client)
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("action,error", [("cancel", "siwc_cancelled"),
                                         ("expiry", "siwc_credential_expired"),
                                         ("deadline", "siwc_timeout")])
def test_control_boundaries_after_legacy_budget_are_still_enforced(action, error):
    token, clock, wall = Event(), [0], [100]

    def on_read(response):
        if response.offset > LEGACY:
            if action == "cancel":
                token.set()
            elif action == "expiry":
                wall[0] = 1000
            else:
                clock[0] = 20

    client, response, connection, calls = fixture(padded(size=CATALOG),
                                                clock=lambda: clock[0], on_read=on_read)
    with pytest.raises(SiwcError, match=f"^{error}$"):
        models(client, cancellation=token, wall_clock=lambda: wall[0])
    assert LEGACY < response.offset <= LEGACY + 4096
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("content_type,encoding", [
    ("text/html", "identity"), ("application/octet-stream", "identity"),
    (None, "identity"), ("application/json", "gzip"), ("application/json", "br"),
    ("application/json", 1),
])
def test_large_catalog_media_and_identity_before_body(content_type, encoding):
    client, response, connection, calls = fixture(padded(size=CATALOG),
        content_type=content_type, encoding=encoding)
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        models(client)
    assert not response.reads
    assert_closed(response, connection, calls)


def test_large_catalog_tls_origin_identity_and_reader_socket_limits():
    client, response, connection, calls = fixture(padded())
    assert len(models(client).choices) == 2
    host, options = calls[0]
    assert host == "api.openai.com" and options["port"] == 443
    assert options["context"].check_hostname
    assert options["context"].verify_mode == ssl.CERT_REQUIRED
    assert options["timeout"] == 20
    assert connection.requests == [("GET", "/v1/models", None, {
        "Accept": "application/json", "Accept-Encoding": "identity",
        "Authorization": "Bearer " + TOKEN})]
    assert connection.connected and connection.sock.timeouts
    assert all(0 < timeout <= 20 for timeout in connection.sock.timeouts)
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("check_hostname,verify_mode", [(False, ssl.CERT_REQUIRED),
                                                      (True, ssl.CERT_NONE)])
def test_unverified_tls_context_refused_before_factory(monkeypatch, check_hostname, verify_mode):
    monkeypatch.setattr("inference_service.oauth_http.ssl.create_default_context",
                        lambda: SimpleNamespace(check_hostname=check_hostname,
                                                verify_mode=verify_mode))
    client, response, connection, calls = fixture()
    with pytest.raises(SiwcError, match="^siwc_tls_verification_required$"):
        models(client)
    assert not calls and not connection.requests and not response.reads


@pytest.mark.parametrize("stage", ["success", "oversize", "cancel"])
@pytest.mark.parametrize("resource", ["response", "connection", "both"])
def test_cleanup_failure_remains_fail_closed_on_all_large_outcomes(stage, resource):
    token = Event()
    raw = padded(size=CATALOG + 1 if stage == "oversize" else LARGE)

    def on_read(response):
        if stage == "cancel" and response.offset > LEGACY:
            token.set()

    client, response, connection, calls = fixture(raw, on_read=on_read,
        cleanup_error=resource in {"response", "both"},
        connection_cleanup=resource in {"connection", "both"})
    with pytest.raises(SiwcError, match="^siwc_cleanup_failed$"):
        models(client, cancellation=token)
    assert_closed(response, connection, calls)


@pytest.mark.parametrize("action", ["unauthorized", "cancelled", "expired", "scope"])
def test_refused_before_factory_has_no_dispatch_or_body_reads(action):
    client, response, connection, calls = fixture(authorized=action != "unauthorized")
    parameters, code = {}, "siwc_network_not_authorized"
    if action == "cancelled":
        token = Event()
        token.set()
        parameters, code = {"cancellation": token}, "siwc_cancelled"
    elif action == "expired":
        parameters, code = {"expires_at": 100}, "siwc_credential_expired"
    elif action == "scope":
        parameters, code = {"scopes": ()}, "siwc_plan_scope_missing"
    with pytest.raises(SiwcError, match=f"^{code}$"):
        models(client, **parameters)
    assert not calls and not connection.requests and not response.reads


@pytest.mark.parametrize("status,error", [(400, "siwc_http_refused"),
                                        (401, "siwc_authentication_refused"),
                                        (403, "siwc_permission_refused"),
                                        (429, "siwc_usage_limited")])
def test_error_response_body_never_echoed_and_no_retry(status, error, capsys):
    secret = "synthetic.private.provider.detail"
    raw = json.dumps({"error": secret, "detail": secret}).encode()
    client, response, connection, calls = fixture(raw, status=status)
    with pytest.raises(SiwcError, match=f"^{error}$") as caught:
        models(client)
    assert secret not in str(caught.value) + repr(client)
    assert capsys.readouterr() == ("", "")
    assert_closed(response, connection, calls)


def test_factory_failure_sanitized_no_retry(capsys):
    calls = []

    def fail(*args, **kwargs):
        calls.append((args, kwargs))
        raise OSError("synthetic.private.provider.detail")

    client = SiwcHttpsClient(authorized=True, connection_factory=fail)
    with pytest.raises(SiwcError, match="^siwc_transport_failed$"):
        models(client)
    assert len(calls) == 1 and capsys.readouterr() == ("", "")


@pytest.mark.parametrize("offset", [LEGACY - 1, LEGACY, LEGACY + 4096, LARGE - 3])
def test_invalid_utf8_across_and_beyond_old_byte_boundary(offset):
    raw = bytearray(padded())
    raw[offset] = 0xff
    client, response, connection, calls = fixture(bytes(raw))
    with pytest.raises(SiwcError, match="^siwc_response_invalid$"):
        models(client)
    assert response.offset == LARGE
    assert_closed(response, connection, calls)


def test_account_cli_display_cap_stays_256k_with_large_valid_catalog(monkeypatch):
    from inference_service import credential_store, oauth_http, siwc_session
    from inference_service.oauth_http import ModelCatalog, ModelChoice

    from apps.jarvis_console.chatgpt_account_cli import run_chatgpt_account
    from apps.jarvis_console.runtime import ConsoleCommandError

    catalog = ModelCatalog(tuple(ModelChoice(f"{index:04d}" + "a" * 156, "b" * 256)
                                 for index in range(1024)))
    assert len(json.dumps({"models": [{"slug": item.slug, "display_name": item.display_name}
                                     for item in catalog.choices]}).encode()) > LEGACY
    calls = []

    class Store:
        def __init__(self, *_args, **_kwargs):
            calls.append("synthetic_store")

        def load_profile(self, _reference):
            return SimpleNamespace(client_id="oaiapp_synthetic", subject="synthetic.subject")

        def host_id(self):
            return "synthetic.host"

    class Session:
        def __init__(self, **_kwargs):
            pass

        def load(self, **_kwargs):
            pass

        def catalog(self, *, authorized):
            assert authorized is True
            calls.append("synthetic_catalog")
            return catalog

    monkeypatch.setattr(credential_store, "SiwcCredentialStore", Store)
    monkeypatch.setattr(oauth_http, "SiwcHttpsClient", lambda **_kwargs: object())
    monkeypatch.setattr(siwc_session, "SiwcSession", Session)
    args = SimpleNamespace(authorized=True, action="catalog", timeout_seconds=30,
                           credential_dir=Path("unused-synthetic-directory"),
                           profile_ref="profile-" + "a" * 64)
    with pytest.raises(ConsoleCommandError) as caught:
        run_chatgpt_account(args)
    assert caught.value.error_code == "siwc_operation_refused"
    assert calls == ["synthetic_store", "synthetic_catalog"]
