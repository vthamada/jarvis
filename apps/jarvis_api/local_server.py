"""Bounded same-origin loopback HTTP adapter; never constructs or bypasses Core."""

from __future__ import annotations

import json
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .contracts import (
    CLIENT_HEADER,
    MAX_BODY_BYTES,
    MAX_QUERY_CHARACTERS,
    TICKET_PATTERN,
    LocalWebRejected,
)
from .local_auth import LocalAuth

ASSET_ROOT = Path(__file__).resolve().parent.parent / "jarvis_web"
ASSETS = {
    "/": ("live-index.html", "text/html; charset=utf-8"),
    "/live-app.mjs": ("live-app.mjs", "text/javascript; charset=utf-8"),
    "/live-controller.mjs": ("live-controller.mjs", "text/javascript; charset=utf-8"),
    "/live-job-activity.mjs": ("live-job-activity.mjs", "text/javascript; charset=utf-8"),
    "/live-generative-projection.mjs": (
        "live-generative-projection.mjs", "text/javascript; charset=utf-8"
    ),
    "/live-style.css": ("live-style.css", "text/css; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/particle-sphere.mjs": ("particle-sphere.mjs", "text/javascript; charset=utf-8"),
    "/cinematic.css": ("cinematic.css", "text/css; charset=utf-8"),
    "/live-presence.mjs": ("live-presence.mjs", "text/javascript; charset=utf-8"),
    "/local-voice-playback.mjs": ("local-voice-playback.mjs", "text/javascript; charset=utf-8"),
    "/microphone-capture.mjs": ("microphone-capture.mjs", "text/javascript; charset=utf-8"),
    "/live-conversation-voice.mjs": (
        "live-conversation-voice.mjs", "text/javascript; charset=utf-8"
    ),
    "/live-voice-controls.mjs": ("live-voice-controls.mjs", "text/javascript; charset=utf-8"),
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
    "img-src 'none'; font-src 'none'; media-src 'none'; worker-src 'none'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)
COOKIE_NAME = "jarvis_local_session"
MAX_REQUEST_THREADS = 8
REQUEST_READ_SECONDS = 5.0
_TOKEN = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_ERROR_STATUS = {
    "auth_unavailable": 503,
    "pairing_unavailable": 403,
    "pairing_rate_limited": 429,
    "pairing_refused": 403,
    "session_refused": 401,
    "csrf_refused": 403,
    "analysis_invalid": 400,
    "analysis_busy": 409,
    "analysis_ticket_refused": 403,
    "analysis_closed": 503,
    "generative_unavailable": 409,
    "job_activity_disabled": 409,
    "job_activity_unavailable": 503,
    "voice_disabled": 409,
    "voice_busy": 409,
    "voice_invalid": 400,
    "voice_unavailable": 503,
    "voice_cancelled": 409,
    "voice_expired": 409,
    "voice_ticket_refused": 403,
}


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise LocalWebRejected("request_invalid")
        result[key] = value
    return result


class LocalWebServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = MAX_REQUEST_THREADS

    def __init__(self, service: object, port: int, auth: LocalAuth, job_activity_profile=None,
                 voice_profile=None, voice_service=None):
        if job_activity_profile is not None:
            from .job_activity_profile import JobActivityProfile

            if type(job_activity_profile) is not JobActivityProfile:
                raise ValueError("invalid_job_activity_profile")
        self.job_activity_profile = job_activity_profile
        self.auth = auth
        self.analysis_service = service
        from .voice_service import LocalVoiceService

        if voice_service is not None and type(voice_service) is not LocalVoiceService:
            raise ValueError("invalid_voice_service")
        self.voice_service = voice_service or LocalVoiceService(service, voice_profile)
        self._slots = threading.BoundedSemaphore(MAX_REQUEST_THREADS)
        self._requests: set[socket.socket] = set()
        self._requests_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), LocalWebHandler)

    def process_request(self, request: socket.socket, client_address: tuple[str, int]) -> None:
        if not self._slots.acquire(blocking=False):
            try:
                # Consume a small bounded header prefix before closing: on Windows
                # unread incoming bytes can reset the connection before the 503.
                deadline = time.monotonic() + 0.05
                incoming = bytearray()
                while len(incoming) < 8192 and b"\r\n\r\n" not in incoming:
                    request.settimeout(max(0.001, deadline - time.monotonic()))
                    chunk = request.recv(min(4096, 8192 - len(incoming)))
                    if not chunk:
                        break
                    incoming.extend(chunk)
                    if time.monotonic() >= deadline:
                        break
                request.settimeout(0.2)
                payload = b'{"error_code":"server_busy"}'
                request.sendall(
                    b"HTTP/1.0 503 Service Unavailable\r\nContent-Type: application/json\r\n"
                    b"Connection: close\r\nCache-Control: no-store\r\n"
                    b"X-Content-Type-Options: nosniff\r\nContent-Security-Policy: "
                    + CSP.encode("ascii")
                    + b"\r\nContent-Length: "
                    + str(len(payload)).encode("ascii")
                    + b"\r\n\r\n"
                    + payload
                )
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(
        self, request: socket.socket, client_address: tuple[str, int]
    ) -> None:
        try:
            with self._requests_lock:
                self._requests.add(request)
            super().process_request_thread(request, client_address)
        finally:
            with self._requests_lock:
                self._requests.discard(request)
            self._slots.release()

    def handle_error(self, request: object, client_address: object) -> None:
        pass  # Never print request, body, identity or exception payloads.

    def server_close(self) -> None:
        self.voice_service.close()
        self.auth.close()
        with self._requests_lock:
            for request in self._requests:
                try:
                    request.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
        super().server_close()


class LocalWebHandler(BaseHTTPRequestHandler):
    server_version = "JarvisLocal/1"
    sys_version = ""
    server: LocalWebServer

    def setup(self) -> None:
        self.request.settimeout(2.0)
        super().setup()
        self._body_read = False
        self._deadline = threading.Timer(REQUEST_READ_SECONDS, self._abort_read)
        self._deadline.daemon = True
        self._deadline.start()

    def _abort_read(self) -> None:
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def finish(self) -> None:
        self._deadline.cancel()
        super().finish()

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _reply(
        self,
        status: int,
        payload: bytes,
        content_type: str = "application/json; charset=utf-8",
        *,
        cookie: str | None = None,
        head: bool = False,
    ) -> None:
        self.close_connection = True
        self.send_response(status)
        for key, value in (
            ("Content-Type", content_type),
            ("Content-Length", str(len(payload))),
            ("Content-Security-Policy", CSP),
            ("X-Content-Type-Options", "nosniff"),
            ("Referrer-Policy", "no-referrer"),
            ("Cache-Control", "no-store"),
            ("Permissions-Policy", "camera=(), microphone=" + (
                "(self)" if self.server.voice_service.config()["asr_enabled"] else "()"
            ) + ", geolocation=()"),
            ("Connection", "close"),
        ):
            self.send_header(key, value)
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        if not head:
            self.wfile.write(payload)

    def _json(
        self,
        status: int,
        payload: object,
        *,
        cookie: str | None = None,
        fence: tuple[str, object, bool] | None = None,
    ) -> None:
        rendered = json.dumps(
            payload, ensure_ascii=True, allow_nan=False, separators=(",", ":")
        ).encode("ascii")
        if fence is not None:
            self._fence(*fence)
        self._reply(status, rendered, cookie=cookie)

    def _fence(self, token: str, identity: object, csrf: bool = True) -> None:
        current = (
            self.server.auth.csrf(token, self.headers.get("X-Jarvis-CSRF", ""))
            if csrf
            else self.server.auth.authenticate(token)
        )
        if current is not identity:
            raise LocalWebRejected("session_refused")

    def _error(self, status: int, code: str) -> None:
        self._discard_rejected_body()
        self._json(status, {"error_code": code})

    def _discard_rejected_body(self) -> None:
        """Bounded discard, never validation: preserve deny response on Windows."""
        if self._body_read or not hasattr(self, "headers"):
            return
        if (
            self.command != "POST"
            and self.headers.get("Content-Length") is None
            and self.headers.get("Transfer-Encoding") is None
        ):
            return
        maximum = MAX_BODY_BYTES + 8192
        lengths = self.headers.get_all("Content-Length", [])
        if len(lengths) == 1 and re.fullmatch(r"[0-9]{1,9}", lengths[0], re.ASCII):
            maximum = min(maximum, int(lengths[0]))
        deadline = time.monotonic() + 0.05
        try:
            while maximum > 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self.connection.settimeout(remaining)
                chunk = self.rfile.read1(min(4096, maximum))
                if not chunk:
                    break
                maximum -= len(chunk)
        except OSError:
            pass
        finally:
            self.connection.settimeout(2.0)
            self._body_read = True

    def send_error(self, code: int, message=None, explain=None) -> None:
        self._error(code if code in {400, 401, 403, 409, 413, 429, 503} else 400, "request_invalid")

    def _boundary(self, *, post: bool, api: bool) -> None:
        names = [name.lower() for name in self.headers.keys()]
        if len(names) != len(set(names)) or any(
            "\r" in value or "\n" in value for value in self.headers.values()
        ):
            raise LocalWebRejected("request_invalid")
        origin = f"http://127.0.0.1:{self.server.server_port}"
        if self.headers.get("Host") != origin[7:]:
            raise LocalWebRejected("origin_refused")
        if post and self.headers.get("Origin") != origin:
            raise LocalWebRejected("origin_refused")
        if not post and self.headers.get("Origin") not in {None, origin}:
            raise LocalWebRejected("origin_refused")
        if self.headers.get("Sec-Fetch-Site") not in {None, "same-origin", "none"}:
            raise LocalWebRejected("origin_refused")
        if api and self.headers.get("X-Jarvis-Client") != CLIENT_HEADER:
            raise LocalWebRejected("client_refused")
        if (
            "?" in self.path
            or "#" in self.path
            or not self.path.startswith("/")
            or self.path.startswith("//")
        ):
            raise LocalWebRejected("request_invalid")
        if (
            self.headers.get("Transfer-Encoding") is not None
            or self.headers.get("Expect") is not None
        ):
            raise LocalWebRejected("request_invalid")
        if not post and self.headers.get("Content-Length") not in {None, "0"}:
            raise LocalWebRejected("request_invalid")

    def _body(self, keys: set[str]) -> dict[str, object]:
        if self.headers.get("Content-Type") not in {
            "application/json",
            "application/json; charset=utf-8",
        }:
            raise LocalWebRejected("request_invalid")
        length = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"0|[1-9][0-9]{0,8}", length, re.ASCII):
            raise LocalWebRejected("request_invalid")
        if int(length) > MAX_BODY_BYTES:
            raise LocalWebRejected("request_too_large")
        raw = self.rfile.read(int(length))
        if len(raw) != int(length):
            raise LocalWebRejected("request_invalid")
        self._body_read = True
        try:
            value = json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=_object,
                parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            )
        except (ValueError, UnicodeError, RecursionError):
            raise LocalWebRejected("request_invalid") from None
        if type(value) is not dict or set(value) != keys:
            raise LocalWebRejected("request_invalid")
        self._deadline.cancel()
        return value

    def _token(self) -> str:
        cookie = self.headers.get("Cookie", "")
        parts = [part.strip().split("=", 1) for part in cookie.split(";")]
        names = [part[0] for part in parts]
        if any(len(part) != 2 for part in parts) or len(names) != len(set(names)):
            raise LocalWebRejected("session_refused")
        tokens = [part[1] for part in parts if part[0] == COOKIE_NAME]
        if len(tokens) != 1 or not _TOKEN.fullmatch(tokens[0]):
            raise LocalWebRejected("session_refused")
        return tokens[0]

    def _voice_body(self) -> bytes:
        from .voice_service import MAX_CAPTURE_BYTES

        if (self.headers.get("Content-Type") != "audio/wav"
                or self.headers.get("X-Jarvis-Voice-Consent") != "local-audio-v1"):
            raise LocalWebRejected("voice_invalid")
        length = self.headers.get("Content-Length", "")
        if not re.fullmatch(r"[1-9][0-9]{0,8}", length, re.ASCII):
            raise LocalWebRejected("voice_invalid")
        if int(length) > MAX_CAPTURE_BYTES:
            raise LocalWebRejected("request_too_large")
        raw = self.rfile.read(int(length))
        self._body_read = True
        self._deadline.cancel()
        if len(raw) != int(length):
            raise LocalWebRejected("voice_invalid")
        return raw

    def _identity(self, *, csrf: bool):
        token = self._token()
        if csrf:
            return token, self.server.auth.csrf(token, self.headers.get("X-Jarvis-CSRF", ""))
        return token, self.server.auth.authenticate(token)

    def _handle(self, *, post: bool = False, head: bool = False) -> None:
        try:
            api = self.path.startswith("/api/")
            self._boundary(post=post, api=api)
            service, auth = self.server.analysis_service, self.server.auth
            if head and api:
                self._error(400, "request_invalid")
                return
            if post:
                if self.path == "/api/pair":
                    body = self._body({"secret"})
                    token, _, identity = auth.pair(body["secret"])
                    payload = auth.session_payload(token, service.current_ticket(identity))
                    self._json(
                        200,
                        payload,
                        cookie=(
                            f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; "
                            f"Max-Age={payload['expires_in_seconds']}"
                        ),
                        fence=(token, identity, False),
                    )
                    return
                token, identity = self._identity(csrf=True)
                if self.path == "/api/voice/transcriptions":
                    if not self.server.voice_service.config()["asr_enabled"]:
                        raise LocalWebRejected("voice_disabled")
                    raw = self._voice_body()
                    self._fence(token, identity)
                    result = self.server.voice_service.start_transcription(
                        identity, raw, consent=True,
                    )
                    self._json(202, result, fence=(token, identity, True))
                elif self.path == "/api/voice/speech":
                    body = self._body({"ticket", "consent"})
                    self._fence(token, identity)
                    result = self.server.voice_service.start_speech(
                        identity, body["ticket"], consent=body["consent"],
                    )
                    self._json(202, result, fence=(token, identity, True))
                elif self.path == "/api/voice/cancel":
                    body = self._body({"job_id"})
                    self._fence(token, identity)
                    result = self.server.voice_service.cancel(identity, body["job_id"])
                    self._json(200, result, fence=(token, identity, True))
                elif self.path == "/api/tickets":
                    self._body(set())
                    self._fence(token, identity)
                    result = service.issue_ticket(identity)
                    self._json(201, result, fence=(token, identity, True))
                elif self.path == "/api/generative-tickets":
                    body = self._body({"consent"})
                    if body["consent"] is not True:
                        raise LocalWebRejected("analysis_invalid")
                    self._fence(token, identity)
                    result = service.issue_generative_ticket(identity, consent=True)
                    self._json(201, result, fence=(token, identity, True))
                elif self.path in {"/api/analysis", "/api/generative-analysis"}:
                    generative = self.path == "/api/generative-analysis"
                    body = self._body(
                        {"ticket", "query", "consent"} if generative else {"ticket", "query"},
                    )
                    if generative and body["consent"] is not True:
                        raise LocalWebRejected("analysis_invalid")
                    if type(body["ticket"]) is not str or not TICKET_PATTERN.fullmatch(
                        body["ticket"]
                    ):
                        raise LocalWebRejected("analysis_invalid")
                    query = body["query"]
                    if (
                        type(query) is not str
                        or not 1 <= len(query) <= MAX_QUERY_CHARACTERS
                        or not query.strip()
                    ):
                        raise LocalWebRejected("analysis_invalid")
                    try:
                        query.encode("utf-8", errors="strict")
                    except UnicodeError:
                        raise LocalWebRejected("analysis_invalid") from None
                    self._fence(token, identity)
                    if generative:
                        result = service.submit_generative(
                            identity, body["ticket"], body["query"], consent=True,
                        )
                    else:
                        result = service.submit(identity, body["ticket"], body["query"])
                    self._json(202, result, fence=(token, identity, True))
                elif self.path == "/api/disconnect":
                    self._body(set())
                    self._fence(token, identity)
                    self.server.voice_service.revoke(identity)
                    auth.revoke(token)
                    service.revoke(identity)
                    self._json(
                        200,
                        {"status": "disconnected"},
                        cookie=f"{COOKIE_NAME}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0",
                    )
                else:
                    self._error(400, "request_invalid")
                return
            self._deadline.cancel()
            if self.path == "/api/session":
                token, identity = self._identity(csrf=False)
                self._json(
                    200,
                    auth.session_payload(token, service.current_ticket(identity)),
                    fence=(token, identity, False),
                )
            elif self.path == "/api/voice/config":
                token, identity = self._identity(csrf=True)
                self._json(200, self.server.voice_service.config(), fence=(token, identity, True))
            elif self.path.startswith(("/api/voice/jobs/", "/api/voice/audio/")):
                from .voice_service import JOB_PATTERN

                token, identity = self._identity(csrf=True)
                self._fence(token, identity)
                job_id = self.path.split("/", 4)[-1]
                if not JOB_PATTERN.fullmatch(job_id):
                    raise LocalWebRejected("voice_ticket_refused")
                if self.path.startswith("/api/voice/audio/"):
                    audio = self.server.voice_service.audio(identity, job_id)
                    self._fence(token, identity)
                    self._reply(200, audio, "audio/wav")
                else:
                    result = self.server.voice_service.get(identity, job_id)
                    self._json(200, result, fence=(token, identity, True))
            elif self.path.startswith("/api/results/"):
                ticket = self.path.removeprefix("/api/results/")
                if not TICKET_PATTERN.fullmatch(ticket):
                    raise LocalWebRejected("analysis_ticket_refused")
                token, identity = self._identity(csrf=True)
                result = service.get_result(identity, ticket)
                self._json(200, result, fence=(token, identity, True))
            elif self.path == "/api/job-activity":
                token, identity = self._identity(csrf=True)
                profile = self.server.job_activity_profile
                if profile is None:
                    raise LocalWebRejected("job_activity_disabled")
                from .job_activity_profile import JobActivityUnavailable

                self._fence(token, identity)
                try:
                    activity = profile.read()
                except JobActivityUnavailable:
                    raise LocalWebRejected("job_activity_unavailable") from None
                # A paired browser can view only the host-selected summary.
                # Ledger scope is not the browser principal or a Core grant.
                self._json(200, {
                    "schema_version": "jarvis-local-job-activity-v1",
                    "session_ref": identity.session_ref,
                    "activity": activity,
                }, fence=(token, identity, True))
            elif self.path in ASSETS:
                filename, content_type = ASSETS[self.path]
                asset = ASSET_ROOT / filename
                if (
                    asset.is_symlink()
                    or asset.resolve().parent != ASSET_ROOT
                    or not asset.is_file()
                ):
                    self._error(503, "asset_unavailable")
                else:
                    self._reply(200, asset.read_bytes(), content_type, head=head)
            else:
                self._error(400, "request_invalid")
        except LocalWebRejected as error:
            code = (
                error.code
                if error.code in _ERROR_STATUS
                or error.code
                in {"request_invalid", "request_too_large", "origin_refused", "client_refused"}
                else "service_unavailable"
            )
            status = _ERROR_STATUS.get(
                code,
                {
                    "request_too_large": 413,
                    "origin_refused": 403,
                    "client_refused": 403,
                    "request_invalid": 400,
                }.get(code, 503),
            )
            self._error(status, code)
        except Exception:
            self._error(503, "service_unavailable")

    def do_GET(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle(head=True)

    def do_POST(self) -> None:
        self._handle(post=True)

    def _reject(self) -> None:
        self._error(400, "request_invalid")

    do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = do_CONNECT = _reject


def create_server(
    service: object, port: int = 0, *, auth: LocalAuth | None = None,
    job_activity_profile=None,
    voice_profile=None, voice_service=None,
) -> LocalWebServer:
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_port")
    return LocalWebServer(service, port, auth if auth is not None else LocalAuth(),
                          job_activity_profile, voice_profile, voice_service)
