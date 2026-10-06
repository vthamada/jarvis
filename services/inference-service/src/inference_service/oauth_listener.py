"""Explicit, single-use IPv4 loopback receiver; not an OAuth validator.

No browser, background thread, credential storage or I/O at construction. The
bounded receiver returns a callback only to trusted composition, which must
consume it through SiwcAuthorizationFlow and validate the exchanged ID token.
"""

from __future__ import annotations

import re
import socket
import threading
import time
from http.server import HTTPServer
from socketserver import BaseRequestHandler, TCPServer
from typing import Callable
from urllib.parse import parse_qs, unquote_to_bytes, urlsplit

from inference_service.oauth_flow import AuthorizationAttempt
from inference_service.siwc_contracts import ISSUER, SiwcError, finite_number

_MAX_REQUEST = 40960
_MAX_TARGET = 32768
_MAX_HEADERS = 8192
_BAD_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")
_RECEIVED = b"<!doctype html><html><body>Response received; validation pending.</body></html>"
_REFUSED = b"<!doctype html><html><body>Request refused.</body></html>"


def _response(connection, *, status: int, body: bytes) -> None:
    reasons = {200: "OK", 400: "Bad Request", 405: "Method Not Allowed", 408: "Request Timeout"}
    headers = (f"HTTP/1.1 {status} {reasons[status]}\r\n"
               "Content-Type: text/html; charset=utf-8\r\n"
               f"Content-Length: {len(body)}\r\n"
               "Cache-Control: no-store\r\n"
               "Content-Security-Policy: default-src 'none'\r\n"
               "Referrer-Policy: no-referrer\r\n"
               "X-Content-Type-Options: nosniff\r\n"
               "Connection: close\r\n\r\n").encode("ascii")
    try:
        connection.sendall(headers + body)
    except OSError:
        pass


class _Handler(BaseRequestHandler):
    def handle(self):
        self.server.request_count += 1
        try:
            data = bytearray()
            while b"\r\n\r\n" not in data:
                self.server.check_active()
                block = self.request.recv(min(4096, _MAX_REQUEST + 1 - len(data)))
                if not block:
                    raise SiwcError("siwc_callback_invalid")
                data.extend(block)
                if len(data) > _MAX_REQUEST:
                    raise SiwcError("siwc_callback_invalid")
            self.server.check_active()
            header, extra = bytes(data).split(b"\r\n\r\n", 1)
            if extra:
                raise SiwcError("siwc_callback_invalid")
            lines = header.split(b"\r\n")
            if len(lines) > 33 or sum(len(line) + 2 for line in lines[1:]) > _MAX_HEADERS:
                raise SiwcError("siwc_callback_invalid")
            request_line = lines[0].decode("ascii", "strict").split(" ")
            if len(request_line) != 3:
                raise SiwcError("siwc_callback_invalid")
            method, target, protocol = request_line
            if method != "GET":
                _response(self.request, status=405, body=_REFUSED)
                return
            if (protocol not in {"HTTP/1.0", "HTTP/1.1"} or not 1 <= len(target) <= _MAX_TARGET
                    or any(not 33 <= ord(char) <= 126 for char in target)
                    or not target.startswith("/auth/callback?") or "#" in target):
                raise SiwcError("siwc_callback_invalid")
            if _BAD_ESCAPE.search(target):
                raise SiwcError("siwc_callback_invalid")
            decoded_query = unquote_to_bytes(target.split("?", 1)[1]).decode("utf-8", "strict")
            if any(ord(char) < 32 or ord(char) == 127 for char in decoded_query):
                raise SiwcError("siwc_callback_invalid")
            headers: dict[str, str] = {}
            for line in lines[1:]:
                text = line.decode("ascii", "strict")
                if ":" not in text or text.startswith((" ", "\t")):
                    raise SiwcError("siwc_callback_invalid")
                key, value = text.split(":", 1)
                if (not key or any(char not in "abcdefghijklmnopqrstuvwxyz"
                                 "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for char in key)
                        or any(ord(char) < 32 or ord(char) == 127 for char in value)):
                    raise SiwcError("siwc_callback_invalid")
                key = key.lower()
                if key in headers:
                    raise SiwcError("siwc_callback_invalid")
                headers[key] = value.strip(" ")
            if (headers.get("host") != self.server.expected_host
                    or ("origin" in headers and headers["origin"] != self.server.expected_origin)
                    or "transfer-encoding" in headers
                    or headers.get("content-length", "0") != "0"):
                raise SiwcError("siwc_callback_invalid")
            self.server.check_active()
            self.server.candidate = self.server.expected_origin + target
            _response(self.request, status=200, body=_RECEIVED)
        except (SiwcError, UnicodeError, OSError, ValueError):
            _response(self.request, status=400, body=_REFUSED)


class _Server(HTTPServer):
    address_family = socket.AF_INET
    allow_reuse_address = False

    def server_bind(self):
        # HTTPServer normally performs getfqdn(host) here. A numerical loopback
        # receiver neither needs nor permits that implicit DNS/reverse lookup.
        TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]

    def get_request(self):
        connection, address = super().get_request()
        try:
            connection.settimeout(min(1.0, max(0.001, self.deadline - self.now())))
        except Exception:
            connection.close()
            raise
        return connection, address

    def handle_error(self, request, client_address):
        # socketserver's default prints exception traces and request metadata.
        pass

    def now(self):
        try:
            value = self.clock()
        except Exception:
            raise SiwcError("siwc_clock_invalid") from None
        if not finite_number(value):
            raise SiwcError("siwc_clock_invalid")
        return float(value)

    def check_active(self):
        if self.cancellation is not None and self.cancellation.is_set():
            raise SiwcError("siwc_listener_cancelled")
        if self.now() >= self.deadline:
            raise SiwcError("siwc_listener_timeout")


class SiwcLoopbackListener:
    """Explicit context bind, then one bounded synchronous receive and close."""

    def __init__(self, *, authorized: bool = False, timeout_seconds: float = 300.0,
                 cancellation: threading.Event | None = None,
                 clock: Callable[[], float] = time.monotonic, port: int = 0):
        if (type(authorized) is not bool or not finite_number(timeout_seconds)
                or not 0 < timeout_seconds <= 600 or not callable(clock)
                or type(port) is not int or not 0 <= port <= 65535
                or (cancellation is not None and not isinstance(cancellation, threading.Event))):
            raise SiwcError("siwc_listener_invalid")
        self._authorized = authorized
        self._timeout = timeout_seconds
        self._cancellation = cancellation
        self._clock = clock
        self._port = port
        self._server: _Server | None = None
        self._state = "new"
        self._lock = threading.Lock()

    def __repr__(self):
        return "SiwcLoopbackListener()"

    def __enter__(self):
        with self._lock:
            if self._state != "new":
                raise SiwcError("siwc_listener_state_invalid")
            self._state = "binding"
        server = None
        try:
            if not self._authorized:
                raise SiwcError("siwc_authorization_required")
            if self._cancellation is not None and self._cancellation.is_set():
                raise SiwcError("siwc_listener_cancelled")
            server = _Server(("127.0.0.1", self._port), _Handler, bind_and_activate=False)
            server.clock = self._clock
            server.cancellation = self._cancellation
            now = server.now()
            server.deadline = now + self._timeout
            if not finite_number(server.deadline) or server.deadline <= now:
                raise SiwcError("siwc_listener_invalid")
            server.candidate = None
            server.request_count = 0
            server.server_bind()
            server.server_activate()
            server.expected_host = f"127.0.0.1:{server.server_address[1]}"
            server.expected_origin = "http://" + server.expected_host
            with self._lock:
                self._server = server
                self._state = "ready"
            return self
        except Exception as error:
            if server is not None:
                try:
                    server.server_close()
                except Exception:
                    pass
            with self._lock:
                self._state = "closed"
            if isinstance(error, SiwcError):
                raise error
            raise SiwcError("siwc_listener_unavailable") from None

    @property
    def redirect_uri(self) -> str:
        with self._lock:
            if self._state not in {"ready", "receiving"} or self._server is None:
                raise SiwcError("siwc_listener_state_invalid")
            return self._server.expected_origin + "/auth/callback"

    def receive(self, attempt: AuthorizationAttempt) -> str:
        with self._lock:
            if self._state != "ready" or self._server is None:
                raise SiwcError("siwc_listener_state_invalid")
            self._state = "receiving"
            server = self._server
        try:
            if type(attempt) is not AuthorizationAttempt or not finite_number(attempt.deadline):
                raise SiwcError("siwc_attempt_invalid")
            url = urlsplit(attempt.authorization_url)
            parameters = parse_qs(url.query, strict_parsing=True, max_num_fields=16)
            if (url.scheme != "https" or url.netloc != "auth.openai.com"
                    or url.path != "/api/accounts/authorize" or url.fragment
                    or parameters.get("redirect_uri") != [self.redirect_uri]
                    or not attempt.authorization_url.startswith(
                        ISSUER + "/api/accounts/authorize?")):
                raise SiwcError("siwc_attempt_invalid")
            server.deadline = min(server.deadline, attempt.deadline)
            while True:
                server.check_active()
                if server.request_count >= 16:
                    raise SiwcError("siwc_listener_request_limit")
                server.timeout = min(1.0, max(0.001, server.deadline - server.now()))
                server.handle_request()
                server.check_active()
                if server.candidate is not None:
                    return server.candidate
        except SiwcError:
            raise
        except Exception:
            raise SiwcError("siwc_listener_refused") from None
        finally:
            self.close()

    def close(self) -> None:
        with self._lock:
            server, self._server = self._server, None
            self._state = "closed"
        if server is not None:
            try:
                server.server_close()
            except Exception:
                raise SiwcError("siwc_listener_close_failed") from None

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
