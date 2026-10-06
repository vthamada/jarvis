"""Explicit validated provider session; no automatic login, refresh or inference.

OAuth identity is an external account binding, never a JARVIS principal/action
receipt. Caller authentication, Core governance and final synthesis are separate.
"""

from __future__ import annotations

import time
from threading import Event, RLock

from inference_service.credential_store import SiwcCredentialStore
from inference_service.http_transport import PlanResponsesHttpsTransport
from inference_service.identity_tokens import verify_id_token
from inference_service.oauth_flow import CodeExchange, SiwcAuthorizationFlow
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.providers import ResponsesPlanInferenceProvider
from inference_service.siwc_contracts import (
    DIRECT_SCOPE,
    SiwcCredentials,
    SiwcError,
    finite_number,
    valid_token,
)


class _CombinedCancellation(Event):
    def __init__(self, caller: Event, session: Event):
        super().__init__()
        self._caller, self._session = caller, session

    def is_set(self):
        return self._caller.is_set() or self._session.is_set()


def _scopes(value: object) -> tuple[str, ...]:
    if type(value) is not str or not 1 <= len(value) <= 4096:
        raise SiwcError("siwc_token_response_invalid")
    scopes = tuple(value.split(" "))
    if (not 1 <= len(scopes) <= 32 or len(set(scopes)) != len(scopes)
            or any(not scope or not all(33 <= ord(c) <= 126 for c in scope) for scope in scopes)):
        raise SiwcError("siwc_token_response_invalid")
    return scopes


def _credentials(tokens, *, exchange=None, previous=None, jwks, host_id, now):
    if (type(tokens) is not dict or len(tokens) > 32 or not finite_number(now)
            or tokens.get("token_type") != "Bearer"
            or not valid_token(tokens.get("access_token"))
            or len(tokens["access_token"]) > 8192
            or type(tokens.get("expires_in")) is not int
            or not 1 <= tokens["expires_in"] <= 604_800):
        raise SiwcError("siwc_token_response_invalid")
    if previous is None:
        if type(exchange) is not CodeExchange or not valid_token(tokens.get("id_token")):
            raise SiwcError("siwc_token_response_invalid")
        identity = verify_id_token(tokens["id_token"], jwks=jwks, client_id=exchange.client_id,
                                   nonce=exchange.nonce,
                                   expected_identity=exchange.selected_identity,
                                   now=now)
        scopes = _scopes(tokens.get("scope"))
        refresh = tokens.get("refresh_token")
        id_token = tokens["id_token"]
    else:
        identity = previous.identity
        id_token = tokens.get("id_token", previous.id_token)
        if "id_token" in tokens:
            identity = verify_id_token(id_token, jwks=jwks, client_id=previous.client_id,
                                       nonce=None, expected_identity=identity, now=now)
        # OAuth refresh may omit scope/refresh_token: the original grant and
        # renewable token persist. If provided, replacements are used together.
        scopes = _scopes(tokens["scope"]) if "scope" in tokens else previous.scopes
        refresh = tokens.get("refresh_token", previous.refresh_token)
    if (not valid_token(refresh) or len(refresh) > 8192
            or "openid" not in scopes or "resource.invoke" not in scopes
            or DIRECT_SCOPE not in scopes):
        raise SiwcError("siwc_plan_scope_missing")
    return SiwcCredentials(identity.client_id, host_id, identity.subject, tokens["access_token"],
                           refresh, id_token, scopes, now + tokens["expires_in"], now,
                           identity.email)


class SiwcSession:
    def __init__(self, *, host_id: str, client: SiwcHttpsClient,
                 store: SiwcCredentialStore | None = None, wall_clock=time.time,
                 clock=time.monotonic):
        if not isinstance(client, SiwcHttpsClient) or not callable(wall_clock):
            raise SiwcError("siwc_session_input_invalid")
        if store is not None and not isinstance(store, SiwcCredentialStore):
            raise SiwcError("siwc_session_input_invalid")
        self.flow = SiwcAuthorizationFlow(host_id=host_id, clock=clock)
        self._host = host_id
        self._client = client
        self._store = store
        self._wall_clock = wall_clock
        self._clock = clock
        self._lock = RLock()
        self._credentials = None
        self._catalog = None
        self._generation = 0
        self._events = []
        self.registration_client_id = None
        self._stop = Event()

    def __repr__(self):
        return "SiwcSession(provider_account_only=True, authority='none')"

    def _now(self):
        try:
            now = self._wall_clock()
        except Exception:
            raise SiwcError("siwc_clock_invalid") from None
        if not finite_number(now):
            raise SiwcError("siwc_clock_invalid")
        return now

    def _event(self, name):
        self._events.append({"name": name, "generation": self._generation, "authority": "none"})
        del self._events[:-256]

    def _replace(self, credentials):
        self._stop.set()
        self._stop = Event()
        self._credentials, self._catalog = credentials, None
        self._generation += 1

    def _budget(self, timeout_seconds, cancellation, *, attempt_deadline=None):
        if (not finite_number(timeout_seconds) or not 0 < timeout_seconds <= 120
                or (cancellation is not None and not isinstance(cancellation, Event))):
            raise SiwcError("siwc_timeout_invalid")
        try:
            last = self._clock()
        except Exception:
            raise SiwcError("siwc_clock_invalid") from None
        if not finite_number(last):
            raise SiwcError("siwc_clock_invalid")
        deadline = last + timeout_seconds
        if attempt_deadline is not None:
            deadline = min(deadline, attempt_deadline)

        def remaining():
            nonlocal last
            try:
                now = self._clock()
            except Exception:
                raise SiwcError("siwc_clock_invalid") from None
            if not finite_number(now) or now < last:
                raise SiwcError("siwc_clock_invalid")
            last = now
            if cancellation is not None and cancellation.is_set():
                raise SiwcError("siwc_cancelled")
            if now >= deadline:
                raise SiwcError("siwc_timeout")
            return deadline - now

        return remaining

    def begin(self, *, redirect_uri: str, authorized: bool = False,
              returning: bool = False, retry_registration: bool = False, timeout_seconds=300):
        with self._lock:
            if type(returning) is not bool or type(retry_registration) is not bool:
                raise SiwcError("siwc_session_input_invalid")
            if returning and self._credentials is None:
                raise SiwcError("siwc_account_missing")
            selected = self._credentials if returning else None
            if retry_registration and (selected is not None or self.registration_client_id is None):
                raise SiwcError("siwc_registration_missing")
            attempt = self.flow.begin(
                redirect_uri=redirect_uri, authorized=authorized, timeout_seconds=timeout_seconds,
                selected_identity=selected.identity if selected else None,
                id_token_hint=selected.id_token if selected else None,
                login_hint=selected.email if selected else None,
                registration_client_id=self.registration_client_id if retry_registration else None,
            )
            self._event("siwc_authorization_started")
            return attempt

    def complete(self, attempt, callback_url: str, *, timeout_seconds=30,
                 cancellation: Event | None = None):
        """Validate and persist before making a new account active.

        Failed/replaced attempts never alter the previously active credentials.
        Serial local operations and one-shot flow consumption prevent replay.
        """
        with self._lock:
            exchange = self.flow.finish(attempt, callback_url)
            self.registration_client_id = exchange.client_id
            remaining = self._budget(timeout_seconds, cancellation,
                                     attempt_deadline=attempt.deadline)
            self._client.discovery(timeout_seconds=remaining(), cancellation=cancellation)
            tokens = self._client.auth_code(
                client_id=exchange.client_id, code=exchange.code,
                code_verifier=exchange.code_verifier, redirect_uri=exchange.redirect_uri,
                timeout_seconds=remaining(), cancellation=cancellation,
            )
            jwks = self._client.jwks(timeout_seconds=remaining(), cancellation=cancellation)
            credentials = _credentials(tokens, exchange=exchange, jwks=jwks,
                                       host_id=self._host, now=self._now())
            remaining()
            if self._store is not None:
                self._store.save(credentials)
            self._replace(credentials)
            self.registration_client_id = None
            self._event("siwc_account_activated")
            return credentials.identity  # no tokens in default result

    def load(self, *, client_id: str, subject: str):
        with self._lock:
            if self._store is None:
                raise SiwcError("siwc_storage_unavailable")
            credentials = self._store.load(client_id=client_id, subject=subject)
            if credentials.host_id != self._host:
                raise SiwcError("siwc_storage_binding_mismatch")
            self.flow.cancel()
            self._replace(credentials)
            self._event("siwc_saved_account_selected")

    def refresh(self, *, authorized: bool = False, timeout_seconds=30,
                cancellation: Event | None = None):
        with self._lock:
            if authorized is not True or self._credentials is None:
                raise SiwcError("siwc_refresh_not_authorized")
            remaining = self._budget(timeout_seconds, cancellation)

            def rotate(previous):
                tokens = self._client.refresh(
                    client_id=previous.client_id, refresh_token=previous.refresh_token,
                    timeout_seconds=remaining(), cancellation=cancellation,
                )
                jwks = (self._client.jwks(timeout_seconds=remaining(), cancellation=cancellation)
                        if "id_token" in tokens else {})
                return _credentials(tokens, previous=previous, jwks=jwks,
                                    host_id=self._host, now=self._now())

            if self._store is not None:
                with self._store.locked():
                    # Another process may have refreshed while this session was idle.
                    previous = self._store.load_locked(client_id=self._credentials.client_id,
                                                       subject=self._credentials.subject)
                    replacement = rotate(previous)
                    remaining()
                    self._store.save_locked(replacement)
            else:
                replacement = rotate(self._credentials)
                remaining()
            # Successful durable replacement is the local commit point. A
            # cancellation arriving during commit must not leave active memory
            # on the old rotating token pair after storage contains the new one.
            self._replace(replacement)
            self._event("siwc_credentials_rotated")
            return self.metadata()

    def catalog(self, *, authorized: bool = False, timeout_seconds=30,
                cancellation: Event | None = None):
        with self._lock:
            if authorized is not True or self._credentials is None:
                raise SiwcError("siwc_catalog_not_authorized")
            creds = self._credentials
            catalog = self._client.models(
                access_token=creds.access_token, expires_at=creds.expires_at, scopes=creds.scopes,
                wall_clock=self._wall_clock, timeout_seconds=timeout_seconds,
                cancellation=cancellation,
            )
            self._catalog = catalog
            self._event("siwc_catalog_loaded")
            return catalog

    def provider(self, model: str, *, authorized: bool = False,
                 connection_factory=None) -> ResponsesPlanInferenceProvider:
        """No network here; every request rechecks the session generation.

        Injected connection factories are trusted test seams. Plan scope/model
        selection never supplies JARVIS authority. Default synthesis stays native.
        """
        with self._lock:
            if authorized is not True or self._credentials is None or self._catalog is None:
                raise SiwcError("siwc_inference_not_authorized")
            self._catalog.select(model)
            generation = self._generation
            creds = self._credentials
            stop = self._stop
            transport = PlanResponsesHttpsTransport(
                bearer_token=creds.access_token, expires_at=creds.expires_at,
                granted_scopes=creds.scopes, authorized=True, connection_factory=connection_factory,
                wall_clock=self._wall_clock,
            )

            def fenced_transport(payload, *, timeout_seconds, cancellation):
                with self._lock:
                    if generation != self._generation or self._credentials is not creds:
                        raise SiwcError("siwc_session_replaced")
                    if payload.get("model") != model:
                        raise SiwcError("siwc_model_selection_mismatch")
                # The fence runs on first iteration, not merely iterator creation.
                # Session cancellation is checked by the actual HTTP transport at
                # every cooperative I/O boundary, including after a partial yield.
                yield from transport(payload, timeout_seconds=timeout_seconds,
                                     cancellation=_CombinedCancellation(cancellation, stop))

            return ResponsesPlanInferenceProvider(fenced_transport)

    def disconnect_local(self):
        """Stop this in-memory session; remote revocation/storage erasure separate."""
        with self._lock:
            self.flow.cancel()
            self._replace(None)
            self.registration_client_id = None
            self._event("siwc_session_disconnected_locally")

    def metadata(self):
        with self._lock:
            return {"mode": "siwc_provider_session", "authority": "none",
                    "authenticated_provider_account": self._credentials is not None,
                    "operator_authenticated": False,
                    "generation": self._generation, "catalog_loaded": self._catalog is not None,
                    "remote_revocation_confirmed": False,
                    "plan_scope_granted": self._credentials is not None
                    and DIRECT_SCOPE in self._credentials.scopes}

    def events(self):
        with self._lock:
            return tuple(dict(event) for event in self._events)
