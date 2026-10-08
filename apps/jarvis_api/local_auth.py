"""One-launch loopback pairing. Session possession is not human identity or a grant."""

from __future__ import annotations

import math
import re
import secrets
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .contracts import (
    PAIRING_SECONDS,
    SESSION_SCHEMA,
    SESSION_SECONDS,
    LocalWebRejected,
    SessionIdentity,
)

_TOKEN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
MAX_PAIRING_ATTEMPTS = 8


@dataclass(frozen=True)
class _Session:
    token: str = field(repr=False)
    csrf: str = field(repr=False)
    identity: SessionIdentity
    expires_at: float


class LocalAuth:
    """Single active session, bounded one-use pairing and content-free failures."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._lock = threading.RLock()
        self._last_now: float | None = None
        self._secret = secrets.token_hex(32)
        self._pairing_deadline = self._now() + PAIRING_SECONDS
        self._attempts = 0
        self._consumed = False
        self._session: _Session | None = None

    def _now(self) -> float:
        with self._lock:
            try:
                value = self._clock()
                if isinstance(value, bool) or not isinstance(value, (float, int)):
                    raise ValueError()
                value = float(value)
                if not math.isfinite(value) or (
                    self._last_now is not None and value < self._last_now
                ):
                    raise ValueError()
            except Exception:
                raise LocalWebRejected("auth_unavailable") from None
            self._last_now = value
            return value

    @property
    def pairing_secret(self) -> str:
        """Explicit terminal-only launch secret; never included in HTTP responses."""
        return self._secret

    def pair(self, secret: str) -> tuple[str, str, SessionIdentity]:
        with self._lock:
            if self._consumed or self._now() >= self._pairing_deadline:
                raise LocalWebRejected("pairing_unavailable")
            if self._attempts >= MAX_PAIRING_ATTEMPTS:
                raise LocalWebRejected("pairing_rate_limited")
            self._attempts += 1
            if (
                type(secret) is not str
                or not _TOKEN.fullmatch(secret)
                or not secrets.compare_digest(secret, self._secret)
            ):
                raise LocalWebRejected("pairing_refused")
            suffix = secrets.token_hex(16)
            identity = SessionIdentity(
                session_ref=f"session://web-live/{suffix}",
                principal_ref=f"operator://web-live/{suffix}",
                canonical_user_ref=f"user://web-live/{suffix}",
            )
            token, csrf = secrets.token_hex(32), secrets.token_hex(32)
            self._session = _Session(token, csrf, identity, self._now() + SESSION_SECONDS)
            self._consumed = True
            return token, csrf, identity

    def _active(self, token: str) -> _Session:
        session = self._session
        if session is not None and self._now() >= session.expires_at:
            self._session = None
            session = None
        if (
            session is None
            or type(token) is not str
            or not _TOKEN.fullmatch(token)
            or not secrets.compare_digest(token, session.token)
        ):
            raise LocalWebRejected("session_refused")
        return session

    def authenticate(self, token: str) -> SessionIdentity:
        with self._lock:
            return self._active(token).identity

    def csrf(self, token: str, supplied: str) -> SessionIdentity:
        with self._lock:
            session = self._active(token)
            if (
                type(supplied) is not str
                or not _TOKEN.fullmatch(supplied)
                or not secrets.compare_digest(supplied, session.csrf)
            ):
                raise LocalWebRejected("csrf_refused")
            return session.identity

    def session_payload(self, token: str, last_ticket: str | None) -> dict[str, object]:
        with self._lock:
            if last_ticket is not None:
                from .contracts import TICKET_PATTERN

                if type(last_ticket) is not str or not TICKET_PATTERN.fullmatch(last_ticket):
                    raise LocalWebRejected("auth_unavailable")
            session = self._active(token)
            remaining = min(SESSION_SECONDS, math.ceil(session.expires_at - self._now()))
            if remaining < 1:
                self._session = None
                raise LocalWebRejected("session_refused")
            return {
                "schema_version": SESSION_SCHEMA,
                "authenticated": True,
                "session_ref": session.identity.session_ref,
                "csrf_token": session.csrf,
                "expires_in_seconds": remaining,
                "last_ticket": last_ticket,
            }

    def revoke(self, token: str) -> SessionIdentity | None:
        with self._lock:
            try:
                session = self._active(token)
            except LocalWebRejected:
                return None
            self._session = None
            return session.identity

    def close(self) -> None:
        with self._lock:
            self._consumed = True
            self._session = None
