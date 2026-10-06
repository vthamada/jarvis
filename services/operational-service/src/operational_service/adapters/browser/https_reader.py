"""One opt-in, scope-bound HTTPS GET; never a browser engine or Core authority."""

from __future__ import annotations

import hashlib
import math
import threading
import time
from dataclasses import fields
from datetime import UTC, datetime

from .https_contracts import (
    HttpsObservation,
    HttpsReadLimits,
    HttpsReadRefused,
    HttpsReadRequest,
    HttpsReadScope,
    validate_target,
)
from .https_protocol import read_response
from .https_transport import PinnedTlsConnection

_ERROR_CODES = frozenset({
    "invalid_http_input", "invalid_headers", "headers_too_large", "line_too_large",
    "unexpected_http_status", "duplicate_headers", "invalid_body_length",
    "conflicting_framing", "unsupported_transfer_encoding", "unexpected_content_type",
    "unsupported_content_encoding", "body_too_large", "incomplete_headers", "incomplete_body",
    "invalid_chunked_body", "too_many_chunks", "trailers_too_large", "forbidden_trailer",
    "overhead_too_large", "transport_unavailable", "deadline_exceeded", "cancelled",
    "invalid_clock", "invalid_https_transport", "https_connect_refused", "https_tls_refused",
    "https_io_refused", "invalid_utf8", "binary_content",
})


def _copy(value, kind):
    if type(value) is not kind:
        raise ValueError("invalid_https_configuration")
    return kind(**{item.name: getattr(value, item.name) for item in fields(kind)})


def _request_tuple(value: HttpsReadRequest | HttpsReadScope) -> tuple:
    return tuple(getattr(value, item.name) for item in fields(HttpsReadRequest))


class CredentiallessHttpsReader:
    """A configured external observation adapter, disabled until each explicit opt-in.

    Exact reference equality is a boundary, not authentication of the principal.
    Network data has no instruction, memory, tool-grant or governance authority.
    """

    def __init__(self, scope: HttpsReadScope, limits: HttpsReadLimits | None = None) -> None:
        self._scope = _copy(scope, HttpsReadScope)
        self._limits = _copy(HttpsReadLimits() if limits is None else limits, HttpsReadLimits)
        self._lock = threading.Lock()

    def observe(
        self, request: HttpsReadRequest, *, authorized: bool = False,
        cancel: threading.Event | None = None,
    ) -> HttpsObservation:
        if authorized is not True:
            return HttpsObservation("refused", "authorization_required")
        if cancel is not None and not isinstance(cancel, threading.Event):
            return HttpsObservation("refused", "invalid_cancellation")
        if not self._lock.acquire(blocking=False):
            return HttpsObservation("refused", "reader_busy")
        try:
            # Snapshot and revalidate before any external callbacks or socket I/O.
            scope = _copy(self._scope, HttpsReadScope)
            limits = _copy(self._limits, HttpsReadLimits)
            if type(request) is not HttpsReadRequest:
                return HttpsObservation("refused", "scope_mismatch")
            supplied = _request_tuple(request)
            if (any(type(value) is not str for value in supplied)
                    or supplied != _request_tuple(scope)):
                return HttpsObservation("refused", "scope_mismatch")
            return self._read(scope, limits, cancel)
        except HttpsReadRefused as error:
            code = error.code if (type(error.code) is str and error.code in _ERROR_CODES) \
                else "transport_unavailable"
            return HttpsObservation("cancelled" if code == "cancelled" else "refused", code)
        except Exception:
            return HttpsObservation("refused", "transport_unavailable")
        finally:
            self._lock.release()

    @staticmethod
    def _read(scope, limits, cancel) -> HttpsObservation:
        hostname, target = validate_target(scope.url)
        started = time.monotonic()
        if type(started) not in (int, float) or not math.isfinite(started):
            raise HttpsReadRefused("invalid_clock")
        deadline = started + limits.deadline_seconds

        def check() -> float:
            if cancel is not None and cancel.is_set():
                raise HttpsReadRefused("cancelled")
            now = time.monotonic()
            if type(now) not in (int, float) or not math.isfinite(now) or now < started:
                raise HttpsReadRefused("invalid_clock")
            remaining = deadline - now
            if remaining <= 0:
                raise HttpsReadRefused("deadline_exceeded")
            return remaining

        check()
        request_bytes = (
            f"GET {target} HTTP/1.1\r\nHost: {hostname}\r\n"
            "Accept: text/plain, text/html\r\nAccept-Encoding: identity\r\n"
            "Connection: close\r\n\r\n"
        ).encode("ascii")
        with PinnedTlsConnection(hostname, scope.ipv4_pin, check) as connection:
            connection.send(request_bytes)
            parsed = read_response(connection.receive, limits, check)
            check()
            try:
                text = parsed.body.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise HttpsReadRefused("invalid_utf8") from None
            if any((ord(char) < 32 and char not in "\r\n\t") or ord(char) == 127 for char in text):
                raise HttpsReadRefused("binary_content")
            digest = hashlib.sha256(parsed.body).hexdigest()
            observed_at = datetime.now(UTC).isoformat()
            check()
        # Cleanup may consume time or observe cancellation; never publish stale success.
        check()
        return HttpsObservation(
            "observed", None, text, scope.url, observed_at,
            digest, len(parsed.body), parsed.media_type,
        )
