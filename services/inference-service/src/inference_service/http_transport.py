"""Explicit, fixed-origin SIWC HTTPS/SSE transport, disabled without consent.

Credential, scope and expiry are supplied by trusted composition. They are
declarations, not JWT verification or proof of an OAuth grant. This component
never discovers credentials, refreshes tokens, follows redirects, retries, uses
proxies or switches billing paths. Construction does not contact the network.

Deadlines/cancellation are cooperative around blocking I/O. Remaining socket
timeouts bound socket operations, not DNS resolution or a hard process kill.
"""

from __future__ import annotations

import http.client
import json
import re
import ssl
from collections.abc import Callable, Iterator
from email.errors import MissingHeaderBodySeparatorDefect
from math import isfinite
from threading import Event
from time import monotonic, time

from inference_service.diagnostics import emit_diagnostic

_HOST = "api.openai.com"
_PATH = "/v1/responses"
_SCOPE = "chatgpt.tokens.use.direct"
PLAN_TRANSPORT_ERROR_CODES = frozenset(
    {
        "invalid_timeout",
        "invalid_cancellation",
        "invalid_request_payload",
        "unsupported_request_field",
        "request_limit_exceeded",
        "invalid_clock",
        "cancelled",
        "timeout",
        "plan_usage_not_authorized",
        "plan_usage_scope_missing",
        "credential_expired",
        "tls_verification_required",
        "plan_authentication_refused",
        "plan_permission_refused",
        "plan_usage_limited",
        "http_request_refused",
        "unsupported_response_encoding",
        "transport_error",
        "event_limit_exceeded",
        "ambiguous_stream_terminal",
        "malformed_sse_event",
        "malformed_stream_chunk",
        "stream_limit_exceeded",
        "line_limit_exceeded",
        "ambiguous_sse_event",
        "stream_interrupted",
    }
)


class PlanTransportError(Exception):
    """Content-free errors suitable for the provider's failure contract."""

    def __init__(self, code: str, status: str = "failed") -> None:
        self.code = (
            code if type(code) is str and code in PLAN_TRANSPORT_ERROR_CODES else "transport_error"
        )
        expected_status = {"cancelled": "cancelled", "timeout": "timed_out"}.get(
            self.code, "failed"
        )
        # A caller cannot turn a transport refusal into success or inject diagnostic text.
        self.status = expected_status
        super().__init__(self.code)


def _finite_number(value: object) -> bool:
    try:
        return type(value) in {int, float} and isfinite(value)
    except OverflowError:
        return False


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("non_finite_json")


def _response_metadata_code(response: object, phase: str) -> str:
    """Observe parsed metadata only; never raw wire, body, values or defect text.

    Exact stdlib message objects are required. Unavailable synthetic seams or
    exceptional metadata cannot change transport acceptance. The caller fences
    every observation before computing the next one.
    """
    unavailable = {
        "responses_http_version": "response_http_unavailable",
        "responses_header_count": "response_headers_unavailable",
        "responses_header_parse": "response_header_parse_unavailable",
        "responses_media_presence": "response_media_presence_unavailable",
        "responses_content_length": "response_length_unavailable",
        "responses_transfer_encoding": "response_transfer_unavailable",
    }[phase]
    try:
        if phase == "responses_http_version":
            version = response.version
            if type(version) is not int:
                return unavailable
            return {10: "response_http_1_0", 11: "response_http_1_1"}.get(
                version, "response_http_other"
            )
        message = response.headers
        if type(message) is not http.client.HTTPMessage:
            return unavailable
        if phase == "responses_header_count":
            return "response_headers_present" if len(message) else "response_headers_empty"
        if phase == "responses_header_parse":
            defects = message.defects
            if type(defects) is not list:
                return unavailable
            if not defects:
                return "response_header_parse_clean"
            if any(type(defect) is MissingHeaderBodySeparatorDefect for defect in defects):
                return "response_header_parse_missing_separator"
            return "response_header_parse_other_defect"
        if phase == "responses_media_presence":
            return ("response_media_present" if "Content-Type" in message
                    else "response_media_absent")
        length = phase == "responses_content_length"
        prefix = "response_length" if length else "response_transfer"
        values = message.get_all("Content-Length" if length else "Transfer-Encoding")
        if values is None:
            return prefix + "_absent"
        if type(values) is not list or not values:
            return prefix + "_invalid"
        if len(values) != 1:
            return prefix + "_multiple"
        value = values[0]
        if type(value) is not str or len(value) > 65_536:
            return prefix + "_invalid"
        value = value.strip()
        if length:
            # No integer conversion, arbitrary precision allocation or echo.
            if not value or not value.isascii() or not value.isdecimal():
                return "response_length_invalid"
            return "response_length_nonzero" if value.strip("0") else "response_length_zero"
        return ("response_transfer_chunked" if value.lower() == "chunked"
                else "response_transfer_other")
    except Exception:
        return unavailable


class PlanResponsesHttpsTransport:
    """A callable Responses transport with explicit in-memory OAuth credentials.

    ``connection_factory`` and clocks are trusted composition/test seams, not
    operator endpoint/TLS overrides. Injected connections are not live evidence.
    Credentials and payloads are intentionally absent from repr and errors.
    The provider, not this framing layer, owns semantic completion validation.
    """

    def __init__(
        self,
        *,
        bearer_token: str,
        expires_at: float,
        authorized: bool = False,
        granted_scopes: tuple[str, ...] = (),
        connection_factory: Callable[..., object] | None = None,
        clock: Callable[[], float] = monotonic,
        wall_clock: Callable[[], float] = time,
        max_stream_bytes: int = 2_097_152,
        max_event_bytes: int = 262_144,
        max_line_bytes: int = 262_144,
        max_events: int = 4096,
        telemetry: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        if (
            type(bearer_token) is not str
            or not 1 <= len(bearer_token) <= 8192
            or re.fullmatch(r"[A-Za-z0-9._~+/\-]+=*", bearer_token) is None
        ):
            raise ValueError("invalid_bearer_credential")
        if not _finite_number(expires_at):
            raise ValueError("invalid_credential_expiry")
        if type(authorized) is not bool:
            raise ValueError("invalid_authorization_declaration")
        if (
            type(granted_scopes) is not tuple
            or len(granted_scopes) > 32
            or any(type(scope) is not str or not 1 <= len(scope) <= 128 for scope in granted_scopes)
        ):
            raise ValueError("invalid_scope_declaration")
        if not callable(clock) or not callable(wall_clock):
            raise ValueError("invalid_clock")
        if connection_factory is not None and not callable(connection_factory):
            raise ValueError("invalid_connection_factory")
        if telemetry is not None and not callable(telemetry):
            raise ValueError("invalid_telemetry")
        for value, maximum in (
            (max_stream_bytes, 8_388_608),
            (max_event_bytes, 1_048_576),
            (max_line_bytes, 1_048_576),
            (max_events, 10_000),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("invalid_stream_limit")
        self._token = bearer_token
        self._expires_at = expires_at
        self._authorized = authorized
        self._scopes = granted_scopes
        self._factory = connection_factory
        self._clock = clock
        self._wall_clock = wall_clock
        self._max_stream_bytes = max_stream_bytes
        self._max_event_bytes = max_event_bytes
        self._max_line_bytes = max_line_bytes
        self._max_events = max_events
        self._telemetry = telemetry

    @property
    def evidence_mode(self) -> str:
        """Transport wiring metadata only, never proof of a live model call."""
        return "injected_transport" if self._factory is not None else "fixed_https_transport"

    def __call__(
        self, payload: dict[str, object], *, timeout_seconds: float, cancellation: Event
    ) -> Iterator[dict[str, object]]:
        # Validate eagerly and snapshot before opening any socket or lazy stream.
        try:
            body = self._request_body(payload)
            if not _finite_number(timeout_seconds) or not 0 < timeout_seconds <= 120:
                raise PlanTransportError("invalid_timeout")
            if not isinstance(cancellation, Event):
                raise PlanTransportError("invalid_cancellation")
        except PlanTransportError as error:
            emit_diagnostic(self._telemetry, phase="responses_request", status=error.status,
                            code=error.code)
            raise
        return self._stream(body, float(timeout_seconds), cancellation)

    @staticmethod
    def _request_body(payload: object) -> bytes:
        if type(payload) is not dict or not {"model", "input", "store", "stream"} <= payload.keys():
            raise PlanTransportError("invalid_request_payload")
        if payload.keys() - {"model", "input", "instructions", "store", "stream"}:
            raise PlanTransportError("unsupported_request_field")
        model = payload["model"]
        if (
            type(model) is not str
            or not 1 <= len(model) <= 160
            or any(ord(char) < 33 or ord(char) > 126 for char in model)
            or payload["store"] is not False
            or payload["stream"] is not True
        ):
            raise PlanTransportError("invalid_request_payload")
        messages = payload["input"]
        if type(messages) is not list or not 1 <= len(messages) <= 32:
            raise PlanTransportError("invalid_request_payload")
        total = 0
        for message in messages:
            if (
                type(message) is not dict
                or set(message) != {"role", "content"}
                or message["role"] not in ("user", "assistant")
                or type(message["content"]) is not str
                or not message["content"].strip()
                or len(message["content"]) > 32_000
            ):
                raise PlanTransportError("invalid_request_payload")
            total += len(message["content"])
        instructions = payload.get("instructions", "")
        if total > 64_000 or type(instructions) is not str or len(instructions) > 16_000:
            raise PlanTransportError("invalid_request_payload")
        try:
            body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (ValueError, TypeError, UnicodeError):
            raise PlanTransportError("invalid_request_payload") from None
        if len(body) > 524_288:
            raise PlanTransportError("request_limit_exceeded")
        return body

    def _stream(
        self, body: bytes, timeout_seconds: float, cancellation: Event
    ) -> Iterator[dict[str, object]]:
        connection = None
        response = None
        io_socket = None
        try:
            start = self._clock()
            if not _finite_number(start):
                raise PlanTransportError("invalid_clock")
            deadline = start + timeout_seconds
            last_clock = start

            def check() -> float:
                nonlocal last_clock
                if cancellation.is_set():
                    raise PlanTransportError("cancelled", "cancelled")
                if not self._authorized:
                    raise PlanTransportError("plan_usage_not_authorized")
                if _SCOPE not in self._scopes:
                    raise PlanTransportError("plan_usage_scope_missing")
                wall = self._wall_clock()
                now = self._clock()
                if not _finite_number(wall) or not _finite_number(now) or now < last_clock:
                    raise PlanTransportError("invalid_clock")
                last_clock = now
                if wall >= self._expires_at:
                    raise PlanTransportError("credential_expired")
                if now >= deadline:
                    raise PlanTransportError("timeout", "timed_out")
                return deadline - now

            def before_io() -> None:
                nonlocal io_socket
                remaining = check()
                # A length-delimited final read closes HTTPResponse.fp. With
                # Connection: close its last socket owner may now be gone; the
                # next read is a local EOF, not I/O on that closed descriptor.
                # Keep deadline/cancellation checks but do not retime a dead fd.
                if response is not None and callable(getattr(response, "isclosed", None)):
                    if response.isclosed():
                        return
                if connection is not None:
                    connection.timeout = remaining
                    sock = getattr(connection, "sock", None)
                    if sock is not None:
                        io_socket = sock
                    # HTTPConnection can detach its socket on Connection: close;
                    # the response file still owns that socket until EOF/close.
                    if io_socket is not None:
                        io_socket.settimeout(remaining)

            remaining = check()
            context = ssl.create_default_context()
            # No SSL options, CA path, proxy, endpoint or port are operator configurable.
            if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
                raise PlanTransportError("tls_verification_required")
            factory = self._factory or http.client.HTTPSConnection
            connection = factory(_HOST, port=443, timeout=remaining, context=context)
            before_io()
            connection.connect()
            check()
            before_io()
            connection.request(
                "POST",
                _PATH,
                body=body,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                    "Accept-Encoding": "identity",
                },
            )
            emit_diagnostic(self._telemetry, phase="responses_request", status="completed")
            check()
            before_io()
            response = connection.getresponse()
            emit_diagnostic(self._telemetry, phase="responses_http", status="observed",
                            http_status=response.status)
            check()
            if response.status != 200:
                # Do not read/echo untrusted error bodies, redirect targets or headers.
                code = {
                    401: "plan_authentication_refused",
                    403: "plan_permission_refused",
                    429: "plan_usage_limited",
                }.get(response.status, "http_request_refused")
                raise PlanTransportError(code)
            content_type = response.getheader("Content-Type", "")
            encoding = response.getheader("Content-Encoding", "identity")
            if self._telemetry is not None:
                # Classify only values already read for the legacy SSE guard.
                # Never emit raw headers or change that guard's public refusal.
                media_code = "response_media_type_invalid"
                encoding_code = "response_encoding_invalid"
                if type(content_type) is str:
                    media_code = {
                        "text/event-stream": "response_media_type_sse",
                        "application/json": "response_media_type_json",
                        "text/html": "response_media_type_html",
                        "": "response_media_type_missing",
                    }.get(content_type.split(";", 1)[0].strip().lower(),
                          "response_media_type_other")
                if type(encoding) is str:
                    encoding_code = {
                        "": "response_encoding_identity", "identity": "response_encoding_identity",
                        "gzip": "response_encoding_gzip", "deflate": "response_encoding_deflate",
                        "br": "response_encoding_br",
                    }.get(encoding.strip().lower(), "response_encoding_other")
                emit_diagnostic(self._telemetry, phase="responses_media_type", status="observed",
                                code=media_code)
                check()
                emit_diagnostic(self._telemetry, phase="responses_content_encoding",
                                status="observed", code=encoding_code)
                check()
                for phase in (
                    "responses_http_version", "responses_header_count", "responses_header_parse",
                    "responses_media_presence", "responses_content_length",
                    "responses_transfer_encoding",
                ):
                    emit_diagnostic(self._telemetry, phase=phase, status="observed",
                                    code=_response_metadata_code(response, phase))
                    check()
            if (
                type(content_type) is not str
                or content_type.split(";", 1)[0].strip().lower() != "text/event-stream"
                or type(encoding) is not str
                or encoding.strip().lower() not in {"", "identity"}
            ):
                raise PlanTransportError("unsupported_response_encoding")
            yield from self._events(response, check, before_io)
            if self._telemetry is not None:
                emit_diagnostic(self._telemetry, phase="responses_stream", status="completed")
                check()
        except PlanTransportError as error:
            emit_diagnostic(self._telemetry, phase="responses_stream", status=error.status,
                            code=error.code)
            raise
        except TimeoutError:
            emit_diagnostic(self._telemetry, phase="responses_stream", status="timed_out",
                            code="timeout")
            raise PlanTransportError("timeout", "timed_out") from None
        except Exception:
            emit_diagnostic(self._telemetry, phase="responses_stream", status="failed",
                            code="transport_error")
            # No private credential, request, server body, URL or OS diagnostics escape.
            raise PlanTransportError("transport_error") from None
        finally:
            for resource in (response, connection):
                if resource is not None:
                    try:
                        resource.close()
                    except Exception:
                        pass

    def _events(
        self, response: object, check: Callable[[], float], before_io: Callable[[], None]
    ) -> Iterator[dict[str, object]]:
        buffer = bytearray()
        data: list[str] = []
        event_type: str | None = None
        event_bytes = 0
        stream_bytes = 0
        event_count = 0
        first_line = True

        def decode_event() -> dict[str, object]:
            nonlocal event_count
            event_count += 1
            if event_count > self._max_events:
                raise PlanTransportError("event_limit_exceeded")
            value = "\n".join(data)
            if value == "[DONE]":
                raise PlanTransportError("ambiguous_stream_terminal")
            try:
                event = json.loads(
                    value, object_pairs_hook=_strict_object, parse_constant=_reject_constant
                )
                if (
                    type(event) is not dict
                    or type(event.get("type")) is not str
                    or (event_type is not None and event_type != event["type"])
                ):
                    raise ValueError("invalid_event")
                # Exponent overflow and escaped surrogate strings must also fail closed.
                json.dumps(event, ensure_ascii=False, allow_nan=False).encode("utf-8")
            except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
                raise PlanTransportError("malformed_sse_event") from None
            return event

        eof = False
        while not eof:
            before_io()
            chunk = response.read1(4096)
            check()
            if type(chunk) is not bytes or len(chunk) > 4096:
                raise PlanTransportError("malformed_stream_chunk")
            eof = not chunk
            stream_bytes += len(chunk)
            if stream_bytes > self._max_stream_bytes:
                raise PlanTransportError("stream_limit_exceeded")
            buffer.extend(chunk)
            while buffer:
                # SSE accepts LF, CRLF and CR, including separators split between reads.
                endings = [
                    position
                    for position in (buffer.find(b"\n"), buffer.find(b"\r"))
                    if position >= 0
                ]
                if not endings:
                    if len(buffer) > self._max_line_bytes:
                        raise PlanTransportError("line_limit_exceeded")
                    break
                position = min(endings)
                if position > self._max_line_bytes:
                    raise PlanTransportError("line_limit_exceeded")
                if buffer[position] == 13 and position == len(buffer) - 1 and not eof:
                    break
                line_bytes = bytes(buffer[:position])
                separator = 2 if buffer[position : position + 2] == b"\r\n" else 1
                del buffer[: position + separator]
                try:
                    line = line_bytes.decode("utf-8", errors="strict")
                except UnicodeError:
                    raise PlanTransportError("malformed_sse_event") from None
                if first_line:
                    line = line.removeprefix("\ufeff")
                    first_line = False
                if not line:
                    if data:
                        check()
                        yield decode_event()
                        check()
                    data = []
                    event_type = None
                    event_bytes = 0
                    continue
                event_bytes += len(line_bytes) + separator
                if event_bytes > self._max_event_bytes:
                    raise PlanTransportError("event_limit_exceeded")
                if line.startswith(":"):
                    continue
                field, colon, value = line.partition(":")
                value = value.removeprefix(" ") if colon else ""
                if field == "data":
                    data.append(value)
                elif field == "event":
                    if event_type is not None:
                        raise PlanTransportError("ambiguous_sse_event")
                    event_type = value
                # id/retry and unknown SSE fields are ignored, never used for replay.
            if eof and (buffer or data or event_type is not None):
                raise PlanTransportError("stream_interrupted")
