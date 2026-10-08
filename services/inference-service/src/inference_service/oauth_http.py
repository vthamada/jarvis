"""Opt-in fixed-origin SIWC HTTP operations; no credential discovery or login.

Injected HTTPS factories are trusted test seams, not endpoint overrides or live
evidence. Cancellation and socket deadlines are cooperative; DNS resolution is
not a hard-deadline sandbox. Identity and account binding remain with the caller.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import Event
from time import monotonic, time
from urllib.parse import urlencode, urlsplit

from .siwc_contracts import (
    DIRECT_SCOPE,
    ISSUER,
    RESOURCE,
    SiwcError,
    finite_number,
    valid_client_id,
    valid_token,
)

_DISCOVERY = "/.well-known/openid-configuration"
_JWKS = "/.well-known/jwks.json"
_TOKEN = "/api/accounts/oauth/token"
_AUTHORIZE = "/api/accounts/authorize"
_MAX_BYTES = 262_144
# Account catalogs carry metadata not projected into the model picker. Only
# this fixed successful route gets a larger budget; grants and errors do not.
_MAX_CATALOG_BYTES = 2_097_152
_KNOWN_ERRORS = frozenset({"invalid_grant", "invalid_client", "invalid_request",
                           "unauthorized_client", "unsupported_grant_type",
                           "invalid_scope", "access_denied", "temporarily_unavailable"})


def _display(value: object, maximum: int) -> bool:
    return (type(value) is str and 1 <= len(value) <= maximum and bool(value.strip())
            and all(unicodedata.category(char) not in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                    for char in value))


@dataclass(frozen=True)
class ModelChoice:
    slug: str = field(repr=False)
    display_name: str = field(repr=False)

    def __post_init__(self) -> None:
        if (type(self.slug) is not str or not 1 <= len(self.slug) <= 160
                or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", self.slug) is None
                or not _display(self.display_name, 256)):
            raise SiwcError("siwc_catalog_invalid")


@dataclass(frozen=True)
class ModelCatalog:
    choices: tuple[ModelChoice, ...] = field(repr=False)
    evidence_mode: str = "injected_transport"

    def __post_init__(self) -> None:
        if (type(self.choices) is not tuple or len(self.choices) > 1024
                or any(type(choice) is not ModelChoice for choice in self.choices)
                or len({choice.slug for choice in self.choices}) != len(self.choices)
                or self.evidence_mode not in {"injected_transport", "fixed_https_transport"}):
            raise SiwcError("siwc_catalog_invalid")

    def select(self, slug: str) -> ModelChoice:
        for choice in self.choices:
            if type(slug) is str and choice.slug == slug:
                return choice
        raise SiwcError("siwc_model_unavailable")

    def metadata(self) -> dict[str, object]:
        return {"mode": "siwc_model_catalog", "authority": "none",
                "choice_count": len(self.choices), "evidence_mode": self.evidence_mode}


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("duplicate")
        output[key] = value
    return output


def _constant(_: str) -> None:
    raise ValueError("nonfinite")


def _json_object(body: bytes) -> dict[str, object]:
    try:
        value = json.loads(body.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
        if type(value) is not dict:
            raise ValueError("object")
        # Also refuse escaped surrogates and exponent overflow anywhere in JSON.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 16:
                raise ValueError("depth")
            if type(item) is dict:
                pending.extend((child, depth + 1) for child in item.values())
            elif type(item) is list:
                pending.extend((child, depth + 1) for child in item)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise SiwcError("siwc_response_invalid") from None


def _redirect_uri(value: object) -> bool:
    if type(value) is not str or len(value) > 128:
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
        return (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                and port is not None and 1 <= port <= 65535
                and parsed.netloc == f"127.0.0.1:{port}"
                and parsed.path == "/auth/callback" and not parsed.query and not parsed.fragment
                and value == f"http://127.0.0.1:{port}/auth/callback")
    except ValueError:
        return False


class SiwcHttpsClient:
    """Public-client OAuth operations and account-specific model listing.

    No constructor I/O, client secret, paid API-key fallback, proxy, redirect,
    retries or URL options. No tokens are retained by this transport.
    """

    def __init__(self, *, authorized: bool = False,
                 connection_factory: Callable[..., object] | None = None,
                 clock: Callable[[], float] = monotonic) -> None:
        if (type(authorized) is not bool or not callable(clock)
                or (connection_factory is not None and not callable(connection_factory))):
            raise SiwcError("siwc_transport_configuration_invalid")
        self._authorized = authorized
        self._factory = connection_factory
        self._clock = clock

    @property
    def evidence_mode(self) -> str:
        return "injected_transport" if self._factory is not None else "fixed_https_transport"

    def discovery(self, *, timeout_seconds: float = 30,
                  cancellation: Event | None = None) -> dict[str, object]:
        value = self._request("auth.openai.com", _DISCOVERY, "GET",
                              timeout_seconds=timeout_seconds, cancellation=cancellation)
        expected = {"issuer": ISSUER, "authorization_endpoint": ISSUER + _AUTHORIZE,
                    "token_endpoint": ISSUER + _TOKEN, "jwks_uri": ISSUER + _JWKS}
        if any(value.get(key) != match for key, match in expected.items()):
            raise SiwcError("siwc_discovery_invalid")
        # Do not return unspecified endpoint URLs as trusted transport targets.
        return expected

    def jwks(self, *, timeout_seconds: float = 30,
             cancellation: Event | None = None) -> dict[str, object]:
        value = self._request("auth.openai.com", _JWKS, "GET",
                              timeout_seconds=timeout_seconds, cancellation=cancellation)
        keys = value.get("keys")
        if (type(keys) is not list or not 1 <= len(keys) <= 64
                or any(type(key) is not dict for key in keys)):
            raise SiwcError("siwc_jwks_invalid")
        # Cryptographic key validation belongs to the ID-token verifier.
        return value

    def auth_code(self, *, client_id: str, code: str, code_verifier: str,
                  redirect_uri: str, timeout_seconds: float = 30,
                  cancellation: Event | None = None) -> dict[str, object]:
        if (not valid_client_id(client_id) or not valid_token(code)
                or type(code_verifier) is not str
                or re.fullmatch(r"[A-Za-z0-9._~-]{43,128}", code_verifier) is None
                or not _redirect_uri(redirect_uri)):
            raise SiwcError("siwc_token_request_invalid")
        return self._grant({"grant_type": "authorization_code", "client_id": client_id,
                            "code": code, "code_verifier": code_verifier,
                            "redirect_uri": redirect_uri, "resource": RESOURCE},
                           timeout_seconds=timeout_seconds, cancellation=cancellation)

    def refresh(self, *, client_id: str, refresh_token: str, timeout_seconds: float = 30,
                cancellation: Event | None = None) -> dict[str, object]:
        if not valid_client_id(client_id) or not valid_token(refresh_token):
            raise SiwcError("siwc_token_request_invalid")
        return self._grant({"grant_type": "refresh_token", "client_id": client_id,
                            "refresh_token": refresh_token, "resource": RESOURCE},
                           timeout_seconds=timeout_seconds, cancellation=cancellation)

    def _grant(self, form: dict[str, str], *, timeout_seconds: float,
               cancellation: Event | None) -> dict[str, object]:
        return self._request("auth.openai.com", _TOKEN, "POST",
                             body=urlencode(form).encode("ascii"),
                             timeout_seconds=timeout_seconds, cancellation=cancellation)

    def models(self, *, access_token: str, expires_at: float, scopes: tuple[str, ...],
               timeout_seconds: float = 30, cancellation: Event | None = None,
               wall_clock: Callable[[], float] = time) -> ModelCatalog:
        if (not valid_token(access_token) or not finite_number(expires_at)
                or type(scopes) is not tuple or len(scopes) > 32
                or any(type(scope) is not str or not 1 <= len(scope) <= 128
                       or not all(33 <= ord(char) <= 126 for char in scope) for scope in scopes)
                or len(set(scopes)) != len(scopes) or not callable(wall_clock)):
            raise SiwcError("siwc_credential_invalid")

        def check_credential() -> None:
            try:
                wall = wall_clock()
            except Exception:
                raise SiwcError("siwc_clock_invalid") from None
            if not finite_number(wall):
                raise SiwcError("siwc_clock_invalid")
            if wall >= expires_at:
                raise SiwcError("siwc_credential_expired")
            if DIRECT_SCOPE not in scopes:
                raise SiwcError("siwc_plan_scope_missing")

        value = self._request("api.openai.com", "/v1/models", "GET",
                              bearer=access_token, check_credential=check_credential,
                              timeout_seconds=timeout_seconds, cancellation=cancellation)
        models = value.get("models")
        if type(models) is not list or len(models) > 1024:
            raise SiwcError("siwc_catalog_invalid")
        choices = []
        slugs = set()
        for model in models:
            if type(model) is not dict or not _display(model.get("visibility"), 32):
                raise SiwcError("siwc_catalog_invalid")
            if model["visibility"] != "list":
                continue
            choice = ModelChoice(model.get("slug"), model.get("display_name"))
            if choice.slug in slugs:
                raise SiwcError("siwc_catalog_invalid")
            choices.append(choice)
            slugs.add(choice.slug)
        return ModelCatalog(tuple(choices), self.evidence_mode)

    def _request(self, host: str, path: str, method: str, *,
                 timeout_seconds: float, cancellation: Event | None,
                 body: bytes | None = None, bearer: str | None = None,
                 check_credential: Callable[[], None] | None = None) -> dict[str, object]:
        if not finite_number(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise SiwcError("siwc_timeout_invalid")
        if cancellation is not None and not isinstance(cancellation, Event):
            raise SiwcError("siwc_cancellation_invalid")
        if not self._authorized:
            raise SiwcError("siwc_network_not_authorized")
        connection = response = io_socket = None
        try:
            start = self._clock()
            if not finite_number(start):
                raise SiwcError("siwc_clock_invalid")
            deadline, last_clock = start + timeout_seconds, start

            def check() -> float:
                nonlocal last_clock
                if cancellation is not None and cancellation.is_set():
                    raise SiwcError("siwc_cancelled")
                now = self._clock()
                if not finite_number(now) or now < last_clock:
                    raise SiwcError("siwc_clock_invalid")
                last_clock = now
                if now >= deadline:
                    raise SiwcError("siwc_timeout")
                if check_credential is not None:
                    check_credential()
                return deadline - now

            def before_io() -> float:
                nonlocal io_socket
                remaining = check()
                if response is not None and callable(getattr(response, "isclosed", None)):
                    if response.isclosed():
                        return remaining
                if connection is not None:
                    connection.timeout = remaining
                    if getattr(connection, "sock", None) is not None:
                        io_socket = connection.sock
                    if io_socket is not None:
                        io_socket.settimeout(remaining)
                return remaining

            remaining = check()
            context = ssl.create_default_context()
            if not context.check_hostname or context.verify_mode != ssl.CERT_REQUIRED:
                raise SiwcError("siwc_tls_verification_required")
            factory = self._factory or http.client.HTTPSConnection
            connection = factory(host, port=443, timeout=remaining, context=context)
            before_io()
            connection.connect()
            check()
            headers = {"Accept": "application/json", "Accept-Encoding": "identity"}
            if body is not None:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            if bearer is not None:
                headers["Authorization"] = "Bearer " + bearer
            before_io()
            connection.request(method, path, body=body, headers=headers)
            check()
            before_io()
            response = connection.getresponse()
            check()
            status = response.status
            if type(status) is not int or (status != 200 and status not in {400, 401, 403, 429}):
                raise SiwcError("siwc_http_refused")
            content_type = response.getheader("Content-Type", "")
            encoding = response.getheader("Content-Encoding", "identity")
            if (type(content_type) is not str
                    or content_type.split(";", 1)[0].strip().lower() != "application/json"
                    or type(encoding) is not str
                    or encoding.strip().lower() not in {"", "identity"}):
                raise SiwcError("siwc_response_invalid")
            maximum = (_MAX_CATALOG_BYTES
                       if (host, path, method, status) == (
                           "api.openai.com", "/v1/models", "GET", 200,
                       ) else _MAX_BYTES)
            raw = bytearray()
            while True:
                before_io()
                chunk = response.read1(min(4096, maximum + 1 - len(raw)))
                check()
                if type(chunk) is not bytes or len(chunk) > 4096:
                    raise SiwcError("siwc_response_invalid")
                raw.extend(chunk)
                if len(raw) > maximum:
                    raise SiwcError("siwc_response_limit_exceeded")
                if not chunk:
                    break
            value = _json_object(bytes(raw))
            if status != 200:
                error = value.get("error")
                if type(error) is str and error in _KNOWN_ERRORS:
                    raise SiwcError("siwc_" + error)
                raise SiwcError({401: "siwc_authentication_refused",
                                 403: "siwc_permission_refused",
                                 429: "siwc_usage_limited"}.get(status, "siwc_http_refused"))
            return value
        except SiwcError:
            raise
        except TimeoutError:
            raise SiwcError("siwc_timeout") from None
        except Exception:
            raise SiwcError("siwc_transport_failed") from None
        finally:
            cleanup_failed = False
            for resource in (response, connection):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        cleanup_failed = True
            if cleanup_failed:
                raise SiwcError("siwc_cleanup_failed") from None
