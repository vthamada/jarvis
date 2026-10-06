"""One-shot, in-memory SIWC authorization transactions.

This module performs no I/O and does not authenticate an account. The caller
starts its exact loopback listener before opening the explicitly exposed URL.
Only the token exchange and ID-token verifier may turn CodeExchange into a
validated account. Callback scope is deliberately not returned as a grant.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import unquote_to_bytes, urlencode

from inference_service.siwc_contracts import (
    ISSUER,
    REQUESTED_SCOPES,
    RESOURCE,
    SiwcError,
    VerifiedIdentity,
    finite_number,
    valid_client_id,
    valid_host_id,
    valid_token,
)

_REDIRECT = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})/auth/callback\Z")
_BAD_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_CALLBACK_KEYS = frozenset({"state", "code", "client_id", "scope", "error",
                            "error_description", "error_uri"})


def _visible(value: object, limit: int, *, spaces: bool = False) -> bool:
    return (type(value) is str and 1 <= len(value) <= limit
            and all((32 if spaces else 33) <= ord(char) <= 126 for char in value))


def _redirect(value: object) -> str:
    if type(value) is not str:
        raise SiwcError("siwc_redirect_invalid")
    match = _REDIRECT.fullmatch(value)
    if match is None or int(match[1]) > 65535:
        raise SiwcError("siwc_redirect_invalid")
    return value


@dataclass(frozen=True, eq=False)
class AuthorizationAttempt:
    """An opaque local handle, not a serializable authorization credential."""

    authorization_url: str = field(repr=False)
    deadline: float


@dataclass(frozen=True)
class CodeExchange:
    """Private exchange input; no identity or plan grant has been proved yet."""

    client_id: str = field(repr=False)
    code: str = field(repr=False)
    code_verifier: str = field(repr=False)
    nonce: str = field(repr=False)
    redirect_uri: str = field(repr=False)
    selected_identity: VerifiedIdentity | None = field(repr=False)
    resource: str = RESOURCE


@dataclass(frozen=True, repr=False)
class _Pending:
    attempt: AuthorizationAttempt
    authorization_url: str
    deadline: float
    state: str
    nonce: str
    verifier: str
    redirect_uri: str
    requested_client_id: str
    selected_identity: VerifiedIdentity | None


def _callback_parameters(callback_url: object, redirect_uri: str) -> dict[str, str]:
    if (not _visible(callback_url, 32768)
            or not callback_url.startswith(redirect_uri + "?")
            or "#" in callback_url):
        raise SiwcError("siwc_callback_invalid")
    query = callback_url[len(redirect_uri) + 1:]
    pieces = query.split("&")
    if not 1 <= len(pieces) <= len(_CALLBACK_KEYS):
        raise SiwcError("siwc_callback_invalid")
    parameters: dict[str, str] = {}
    for piece in pieces:
        if "=" not in piece or _BAD_ESCAPE.search(piece):
            raise SiwcError("siwc_callback_invalid")
        raw_key, raw_value = piece.split("=", 1)
        try:
            key, value = (unquote_to_bytes(part.replace("+", " ")).decode("utf-8", "strict")
                          for part in (raw_key, raw_value))
        except (UnicodeError, ValueError):
            raise SiwcError("siwc_callback_invalid") from None
        if (key not in _CALLBACK_KEYS or key in parameters
                or not value or len(value) > 16384
                or any(ord(char) < 32 or ord(char) == 127
                       or 0xD800 <= ord(char) <= 0xDFFF for char in value)):
            raise SiwcError("siwc_callback_invalid")
        parameters[key] = value
    return parameters


class SiwcAuthorizationFlow:
    """At most one pending attempt, locked and consumed even on failed finish.

    A new successful begin replaces the preceding attempt. Hints are provided
    by trusted composition: the ID token hint must belong to the selected
    previously verified account; this class does not verify hint signatures.
    Cancellation drops secret references, not a promise of Python memory erase.
    """

    def __init__(self, *, host_id: str, clock: Callable[[], float] = time.monotonic):
        if not valid_host_id(host_id) or not callable(clock):
            raise SiwcError("siwc_flow_invalid")
        self._host_id = host_id
        self._clock = clock
        self._lock = threading.Lock()
        self._pending: _Pending | None = None

    def __repr__(self) -> str:
        return "SiwcAuthorizationFlow()"

    def _now(self) -> float:
        try:
            now = self._clock()
        except Exception:
            raise SiwcError("siwc_clock_invalid") from None
        if not finite_number(now):
            raise SiwcError("siwc_clock_invalid")
        return float(now)

    def begin(self, *, redirect_uri: str, authorized: bool = False,
              selected_identity: VerifiedIdentity | None = None,
              registration_client_id: str | None = None,
              id_token_hint: str | None = None, login_hint: str | None = None,
              timeout_seconds: float = 300.0) -> AuthorizationAttempt:
        if authorized is not True:
            raise SiwcError("siwc_authorization_required")
        redirect_uri = _redirect(redirect_uri)
        if not finite_number(timeout_seconds) or not 0 < timeout_seconds <= 600:
            raise SiwcError("siwc_timeout_invalid")
        if selected_identity is None:
            if id_token_hint is not None or login_hint is not None:
                raise SiwcError("siwc_hint_invalid")
            identity = None
            if registration_client_id is not None and not valid_client_id(registration_client_id):
                raise SiwcError("siwc_client_invalid")
            # A failed exchange can retain this issued registration identifier,
            # but it still has no validated identity or credentials.
            client_id = registration_client_id or "dynamic_agent_client"
        else:
            if registration_client_id is not None:
                raise SiwcError("siwc_client_invalid")
            if type(selected_identity) is not VerifiedIdentity:
                raise SiwcError("siwc_identity_invalid")
            identity = VerifiedIdentity(selected_identity.client_id, selected_identity.subject,
                                        selected_identity.email, selected_identity.issuer)
            client_id = identity.client_id
            if ((id_token_hint is not None and not valid_token(id_token_hint))
                    or (login_hint is not None and
                        (not _visible(login_hint, 320) or login_hint != identity.email))):
                raise SiwcError("siwc_hint_invalid")
        with self._lock:
            now = self._now()
            deadline = now + timeout_seconds
            if not finite_number(deadline) or deadline <= now:
                raise SiwcError("siwc_timeout_invalid")
            state, nonce, verifier = (secrets.token_urlsafe(32) for _ in range(3))
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            parameters = {"client_id": client_id, "ext_agent_host_id": self._host_id,
                          "response_type": "code", "redirect_uri": redirect_uri,
                          "scope": " ".join(REQUESTED_SCOPES), "resource": RESOURCE,
                          "state": state, "nonce": nonce, "code_challenge_method": "S256",
                          "code_challenge": challenge.decode("ascii").rstrip("=")}
            if client_id == "dynamic_agent_client":
                parameters["agent_name_hint"] = "Jarvis"
            if id_token_hint is not None:
                parameters["id_token_hint"] = id_token_hint
            if login_hint is not None:
                parameters["login_hint"] = login_hint
            url = ISSUER + "/api/accounts/authorize?" + urlencode(parameters)
            attempt = AuthorizationAttempt(url, deadline)
            self._pending = _Pending(attempt, url, deadline, state, nonce, verifier,
                                     redirect_uri, client_id, identity)
            return attempt

    def finish(self, attempt: AuthorizationAttempt, callback_url: str) -> CodeExchange:
        with self._lock:
            pending, self._pending = self._pending, None
            if (pending is None or type(attempt) is not AuthorizationAttempt
                    or attempt is not pending.attempt
                    or attempt.authorization_url != pending.authorization_url
                    or attempt.deadline != pending.deadline):
                raise SiwcError("siwc_attempt_invalid")
            if self._now() >= pending.deadline:
                raise SiwcError("siwc_attempt_expired")
            parameters = _callback_parameters(callback_url, pending.redirect_uri)
            supplied_state = parameters.get("state", "")
            if not hmac.compare_digest(supplied_state.encode("utf-8"),
                                       pending.state.encode("ascii")):
                raise SiwcError("siwc_state_invalid")
            if "error" in parameters:
                # Never interpolate OAuth error strings or descriptions.
                if "code" in parameters:
                    raise SiwcError("siwc_callback_invalid")
                raise SiwcError("siwc_authorization_denied")
            if "error_description" in parameters or "error_uri" in parameters:
                raise SiwcError("siwc_callback_invalid")
            code = parameters.get("code")
            if not _visible(code, 4096):
                raise SiwcError("siwc_code_invalid")
            supplied_client = parameters.get("client_id")
            if pending.requested_client_id == "dynamic_agent_client":
                if not valid_client_id(supplied_client):
                    raise SiwcError("siwc_registration_incomplete")
                client_id = supplied_client
            else:
                client_id = pending.requested_client_id
                if supplied_client is not None and supplied_client != client_id:
                    raise SiwcError("siwc_client_mismatch")
            return CodeExchange(client_id, code, pending.verifier, pending.nonce,
                                pending.redirect_uri, pending.selected_identity)

    def cancel(self) -> None:
        with self._lock:
            self._pending = None

    def metadata(self) -> dict[str, object]:
        with self._lock:
            return {"mode": "siwc_authorization_flow", "pending": self._pending is not None,
                    "authority": "none", "automatic_browser": False,
                    "automatic_network": False}
