"""A single bounded GET of an explicitly configured loopback text fixture.

This transport never resolves DNS, follows redirects, interprets HTML/JS,
authenticates a user, or grants tool authority. Received text is untrusted data.
"""

from __future__ import annotations

import hashlib
import math
import re
import socket
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_PATH = re.compile(
    r"/(?:[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)?/)*"
    r"[A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)?\Z"
)
_HEADER_NAMES = {
    "server",
    "date",
    "content-type",
    "content-length",
    "connection",
    "cache-control",
}


def _ref(value: str) -> None:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise ValueError("invalid_reference")


def _target(url: str) -> tuple[int, str]:
    if not isinstance(url, str) or len(url) > 1024 or not url.isascii():
        raise ValueError("invalid_fixture_url")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError:
        raise ValueError("invalid_fixture_url") from None
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or port is None
        or not 1 <= port <= 65535
        or parsed.netloc != f"127.0.0.1:{port}"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or "?" in url
        or "#" in url
        or not _PATH.fullmatch(parsed.path)
        or url != f"http://127.0.0.1:{port}{parsed.path}"
    ):
        raise ValueError("invalid_fixture_url")
    return port, parsed.path


@dataclass(frozen=True)
class ReadLimits:
    max_body_bytes: int = 65536
    max_header_bytes: int = 8192
    timeout_seconds: float = 1.0
    deadline_seconds: float = 3.0

    def __post_init__(self) -> None:
        for value, lower, upper in (
            (self.max_body_bytes, 1, 262144),
            (self.max_header_bytes, 128, 16384),
        ):
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError("invalid_read_limits")
        for value in (self.timeout_seconds, self.deadline_seconds):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0.01 <= value <= 10
            ):
                raise ValueError("invalid_read_limits")


@dataclass(frozen=True)
class FixtureReadScope:
    principal_ref: str
    session_ref: str
    scope_ref: str
    purpose_ref: str
    url: str

    def __post_init__(self) -> None:
        for value in (self.principal_ref, self.session_ref, self.scope_ref, self.purpose_ref):
            _ref(value)
        _target(self.url)


@dataclass(frozen=True)
class FixtureReadRequest:
    principal_ref: str
    session_ref: str
    scope_ref: str
    purpose_ref: str
    url: str


@dataclass(frozen=True)
class FixtureObservation:
    status: str
    error_code: str | None
    text: str | None = None
    source_url: str | None = None
    observed_at: str | None = None
    content_sha256: str | None = None
    byte_count: int = 0
    media_type: str | None = None
    mode: str = "http_fixture_observation"
    authority: str = "none"
    untrusted_data: bool = True

    def telemetry(self) -> dict[str, str | int | bool | None]:
        """Deliberately excludes content, source URL, and all subject references."""
        return {
            "event_name": "isolated_fixture_http_observation",
            "status": self.status,
            "error_code": self.error_code,
            "byte_count": self.byte_count,
            "mode": self.mode,
            "authority": self.authority,
            "untrusted_data": self.untrusted_data,
        }


class _Refused(Exception):
    def __init__(self, code: str) -> None:
        self.code = code


class FixtureHttpReader:
    def __init__(self, scope: FixtureReadScope, limits: ReadLimits | None = None) -> None:
        if type(scope) is not FixtureReadScope:
            raise ValueError("invalid_fixture_scope")
        if limits is not None and type(limits) is not ReadLimits:
            raise ValueError("invalid_read_limits")
        self.scope = scope
        self.limits = limits or ReadLimits()

    def observe(
        self,
        request: FixtureReadRequest,
        *,
        cancel: threading.Event | None = None,
    ) -> FixtureObservation:
        """No retry, redirect, cookie jar, proxy, credentials, or side-effect action."""
        if type(request) is not FixtureReadRequest:
            return FixtureObservation("refused", "scope_mismatch")
        expected = FixtureReadRequest(
            self.scope.principal_ref,
            self.scope.session_ref,
            self.scope.scope_ref,
            self.scope.purpose_ref,
            self.scope.url,
        )
        if request != expected:
            return FixtureObservation("refused", "scope_mismatch")
        if cancel is not None and not isinstance(cancel, threading.Event):
            return FixtureObservation("refused", "invalid_cancellation")
        try:
            return self._read(cancel)
        except _Refused as exc:
            status = "cancelled" if exc.code == "cancelled" else "refused"
            return FixtureObservation(status, exc.code)
        except (OSError, ValueError, UnicodeError):
            return FixtureObservation("refused", "transport_unavailable")

    def _read(self, cancel: threading.Event | None) -> FixtureObservation:
        port, path = _target(self.scope.url)
        limits = self.limits
        deadline = time.monotonic() + limits.deadline_seconds

        def check() -> float:
            if cancel is not None and cancel.is_set():
                raise _Refused("cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise _Refused("deadline_exceeded")
            return remaining

        check()
        # A numeric AF_INET destination avoids URL opener proxy/DNS behavior entirely.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            connection.settimeout(min(check(), limits.timeout_seconds, 0.1))
            try:
                connection.connect(("127.0.0.1", port))
            except TimeoutError:
                check()
                raise _Refused("timeout") from None
            connection.settimeout(min(check(), limits.timeout_seconds, 0.1))
            request = (
                f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
                "Accept: text/plain, text/html\r\nConnection: close\r\n\r\n"
            ).encode("ascii")
            try:
                connection.sendall(request)
            except TimeoutError:
                check()
                raise _Refused("timeout") from None
            idle_deadline = time.monotonic() + limits.timeout_seconds

            def receive(maximum: int) -> bytes:
                nonlocal idle_deadline
                while True:
                    remaining = check()
                    idle_remaining = idle_deadline - time.monotonic()
                    if idle_remaining <= 0:
                        raise _Refused("timeout")
                    connection.settimeout(min(remaining, idle_remaining, 0.05))
                    try:
                        chunk = connection.recv(maximum)
                    except TimeoutError:
                        continue
                    check()
                    if chunk:
                        idle_deadline = time.monotonic() + limits.timeout_seconds
                    return chunk

            header = bytearray()
            while b"\r\n\r\n" not in header:
                # Never buffer unbounded headers; the last chunk may contain body bytes.
                chunk = receive(min(4096, limits.max_header_bytes + 4 - len(header)))
                if not chunk:
                    raise _Refused("incomplete_headers")
                header.extend(chunk)
                boundary = header.find(b"\r\n\r\n")
                if boundary < 0 and len(header) >= limits.max_header_bytes + 4:
                    raise _Refused("headers_too_large")
            boundary = header.index(b"\r\n\r\n")
            if boundary + 4 > limits.max_header_bytes:
                raise _Refused("headers_too_large")
            media_type, content_length = self._headers(bytes(header[:boundary]))
            if content_length > limits.max_body_bytes:
                raise _Refused("body_too_large")
            body = bytearray(header[boundary + 4 :])
            if len(body) > content_length:
                raise _Refused("invalid_body_length")
            while len(body) < content_length:
                chunk = receive(min(4096, content_length - len(body)))
                if not chunk:
                    raise _Refused("incomplete_body")
                body.extend(chunk)
            check()
            try:
                text = body.decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                raise _Refused("invalid_utf8") from None
            if any(
                (ord(character) < 32 and character not in "\r\n\t") or ord(character) == 127
                for character in text
            ):
                raise _Refused("binary_content")
            check()
            return FixtureObservation(
                "observed",
                None,
                text,
                self.scope.url,
                datetime.now(UTC).isoformat(),
                hashlib.sha256(body).hexdigest(),
                len(body),
                media_type,
            )

    @staticmethod
    def _headers(raw: bytes) -> tuple[str, int]:
        try:
            lines = raw.decode("ascii").split("\r\n")
        except UnicodeDecodeError:
            raise _Refused("invalid_headers") from None
        if not re.fullmatch(r"HTTP/1\.[01] 200(?: [\x20-\x7e]*)?", lines[0]):
            raise _Refused("unexpected_http_status")
        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line or any(ord(char) < 32 or ord(char) == 127 for char in line):
                raise _Refused("invalid_headers")
            name, value = line.split(":", 1)
            name = name.lower()
            if name not in _HEADER_NAMES or name in headers:
                raise _Refused("unexpected_headers")
            headers[name] = value.strip()
        length = headers.get("content-length", "")
        if not re.fullmatch(r"0|[1-9][0-9]{0,8}", length):
            raise _Refused("invalid_body_length")
        media = headers.get("content-type", "")
        match = re.fullmatch(r"(text/plain|text/html)(?:; charset=utf-8)?", media.lower())
        if match is None:
            raise _Refused("unexpected_content_type")
        if headers.get("connection", "close").lower() != "close":
            raise _Refused("unexpected_headers")
        return match.group(1), int(length)
