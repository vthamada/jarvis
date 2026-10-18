"""Explicit numeric-loopback Chat Completions HTTP; no discovery or credentials.

Complete JSON responses use Content-Length or an unambiguous HTTP/1.1 chunked
body; this is not SSE or model streaming. Peer close remains mandatory. Chunk
extensions and trailers are deliberately unsupported. It never resolves DNS,
reads proxy settings, redirects, retries or starts a server/model. Loopback proves
destination only: a server may itself forward prompts to cloud providers.
"""

from __future__ import annotations

import errno
import ipaddress
import json
import re
import select
import socket
from collections.abc import Callable
from math import isfinite
from threading import Event
from time import monotonic
from urllib.parse import urlsplit

LOCAL_CHAT_ERROR_CODES = frozenset({
    "invalid_timeout", "invalid_cancellation", "invalid_clock", "invalid_request_payload",
    "request_limit_exceeded", "response_limit_exceeded", "cancelled", "timeout",
    "http_request_refused", "invalid_http_response", "unsupported_response_encoding",
    "response_interrupted", "transport_error",
    "configuration_changed",
})
_PATH = "/v1/chat/completions"
_HEADER_TOKEN = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_MAX_CHUNKS = 4096
_MAX_CHUNK_SIZE_LINE_BYTES = 8
_MAX_CHUNK_OVERHEAD_BYTES = 65_536


class LocalChatTransportError(Exception):
    """Fixed codes only: bodies, URLs and exception strings never escape."""

    def __init__(self, code: str) -> None:
        self.code = (code if type(code) is str and code in LOCAL_CHAT_ERROR_CODES
                     else "transport_error")
        self.status = {"cancelled": "cancelled", "timeout": "timed_out"}.get(self.code, "failed")
        super().__init__(self.code)


def _number(value: object) -> bool:
    try:
        return type(value) in {int, float} and isfinite(value)
    except OverflowError:
        return False


def _endpoint(value: str) -> tuple[str, int, int, str]:
    try:
        if (type(value) is not str or not 1 <= len(value) <= 256
                or any(not 33 <= ord(c) <= 126 for c in value) or "%" in value):
            raise ValueError
        parsed = urlsplit(value)
        if (parsed.scheme != "http" or parsed.path != _PATH or parsed.query or parsed.fragment
                or "?" in value or "#" in value or parsed.username is not None
                or parsed.password is not None or parsed.port is None):
            raise ValueError
        address = ipaddress.ip_address(parsed.hostname or "")
        # Mapped IPv6 remains outside policy even when a stdlib release treats
        # it as loopback or renders it in dotted IPv4 notation.
        if ((address.version == 6 and address.ipv4_mapped is not None)
                or not address.is_loopback or not 1 <= parsed.port <= 65535):
            raise ValueError
        host = str(address)
        authority = f"[{host}]:{parsed.port}" if address.version == 6 else f"{host}:{parsed.port}"
        # Reject alternate spellings, userinfo, escaped paths and parser normalization.
        if value != f"http://{authority}{_PATH}":
            raise ValueError
        family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
        return host, parsed.port, family, authority
    except (ValueError, TypeError):
        raise ValueError("invalid_local_chat_endpoint") from None


def _request_bytes(payload: object, limit: int) -> bytes:
    if (type(payload) is not dict or set(payload) != {"model", "messages", "n", "stream"}
            or type(payload["model"]) is not str or not 1 <= len(payload["model"]) <= 160
            or any(not 33 <= ord(c) <= 126 for c in payload["model"])
            or "://" in payload["model"] or type(payload["n"]) is not int or payload["n"] != 1
            or payload["stream"] is not False):
        raise LocalChatTransportError("invalid_request_payload")
    messages = payload["messages"]
    if type(messages) is not list or not 1 <= len(messages) <= 33:
        raise LocalChatTransportError("invalid_request_payload")
    for index, message in enumerate(messages):
        if (type(message) is not dict or set(message) != {"role", "content"}
                or message["role"] not in {"user", "assistant", "system"}
                or (message["role"] == "system" and index != 0)
                or type(message["content"]) is not str or not message["content"].strip()
                or len(message["content"]) > 32_000 or "\x00" in message["content"]):
            raise LocalChatTransportError("invalid_request_payload")
    try:
        raw = json.dumps(payload, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8", errors="strict")
    except (ValueError, TypeError, UnicodeError, RecursionError, OverflowError):
        raise LocalChatTransportError("invalid_request_payload") from None
    if len(raw) > limit:
        raise LocalChatTransportError("request_limit_exceeded")
    return raw


class _ChunkedDecoder:
    """Incremental, bounded RFC 9112 framing for one complete JSON response.

    No optional chunk extensions or trailer fields are accepted; the zero chunk
    must be followed by exactly CRLF and then peer EOF. Eight hexadecimal digits
    bound integer parsing, 4,096 data chunks bound framing work, and 64KiB bounds
    total wire overhead in addition to the independently enforced decoded limit.
    Scratch state never grows with arbitrary line/trailer input. ``check`` keeps
    the enclosing total deadline/cancellation active even within buffered bytes.
    """

    def __init__(self, limit: int, *, check: Callable[[], object]) -> None:
        self._limit = limit
        self._check = check
        self._body = bytearray()
        self._line = bytearray()
        self._state = "size"
        self._remaining = 0
        self._chunks = 0
        self._wire_bytes = 0

    def feed(self, data: bytes) -> None:
        self._check()
        if self._wire_bytes + len(data) > self._limit + _MAX_CHUNK_OVERHEAD_BYTES:
            raise LocalChatTransportError("response_limit_exceeded")
        self._wire_bytes += len(data)
        view = memoryview(data)
        position = 0
        while position < len(view):
            self._check()
            if self._state == "complete":
                raise LocalChatTransportError("invalid_http_response")
            if self._state == "data":
                count = min(self._remaining, len(view) - position)
                self._body.extend(view[position:position + count])
                position += count
                self._remaining -= count
                if self._remaining == 0:
                    self._state = "data_cr"
                continue
            byte = view[position]
            position += 1
            if self._state == "size":
                if byte == 59:  # ';': even valid extensions are out of this slice.
                    raise LocalChatTransportError("unsupported_response_encoding")
                if byte == 13:
                    if not self._line:
                        raise LocalChatTransportError("invalid_http_response")
                    self._state = "size_lf"
                elif len(self._line) >= _MAX_CHUNK_SIZE_LINE_BYTES:
                    raise LocalChatTransportError("response_limit_exceeded")
                elif not (48 <= byte <= 57 or 65 <= byte <= 70 or 97 <= byte <= 102):
                    raise LocalChatTransportError("invalid_http_response")
                else:
                    self._line.append(byte)
            elif self._state == "size_lf":
                if byte != 10:
                    raise LocalChatTransportError("invalid_http_response")
                size = int(self._line, 16)
                self._line.clear()
                if size == 0:
                    self._state = "final_cr"
                else:
                    self._chunks += 1
                    if (self._chunks > _MAX_CHUNKS
                            or size > self._limit - len(self._body)):
                        raise LocalChatTransportError("response_limit_exceeded")
                    self._remaining = size
                    self._state = "data"
            elif self._state == "data_cr":
                if byte != 13:
                    raise LocalChatTransportError("invalid_http_response")
                self._state = "data_lf"
            elif self._state == "data_lf":
                if byte != 10:
                    raise LocalChatTransportError("invalid_http_response")
                self._state = "size"
            elif self._state == "final_cr":
                if byte != 13:
                    # Any trailer field is unsupported, not silently ignored.
                    raise LocalChatTransportError("unsupported_response_encoding")
                self._state = "final_lf"
            elif self._state == "final_lf":
                if byte != 10:
                    raise LocalChatTransportError("invalid_http_response")
                self._state = "complete"

    def finish(self) -> bytes:
        self._check()
        if self._state != "complete":
            raise LocalChatTransportError("response_interrupted")
        if not self._body:
            raise LocalChatTransportError("response_limit_exceeded")
        result = bytes(self._body)
        self._check()
        return result


class LocalChatHttpTransport:
    """Bounded synchronous socket I/O with cooperative cancellation every <=50ms.

    Construction is inert. The configured endpoint is never taken from model
    output or request data. No authentication is supported by this first slice.
    A custom clock is a trusted deterministic seam, not evidence of live timing.
    """

    def __init__(
        self, *, endpoint: str, max_request_bytes: int = 524_288,
        max_response_bytes: int = 1_048_576, max_header_bytes: int = 16_384,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._host, self._port, self._family, self._authority = _endpoint(endpoint)
        for value, bound in ((max_request_bytes, 524_288), (max_response_bytes, 2_097_152),
                             (max_header_bytes, 65_536)):
            if type(value) is not int or not 1 <= value <= bound:
                raise ValueError("invalid_local_chat_limit")
        if not callable(clock):
            raise ValueError("invalid_local_chat_clock")
        self._max_request = max_request_bytes
        self._max_response = max_response_bytes
        self._max_headers = max_header_bytes
        self._clock = clock
        self._initial = (self._host, self._port, self._family, self._authority,
                         max_request_bytes, max_response_bytes, max_header_bytes, clock)

    def _fence(self, snapshot):
        current = (self._host, self._port, self._family, self._authority,
                   self._max_request, self._max_response, self._max_headers)
        if (self._initial is not snapshot
                or any(type(value) is not type(expected) or value != expected
                       for value, expected in zip(current, snapshot[:7], strict=True))
                or self._clock is not snapshot[7]):
            raise LocalChatTransportError("configuration_changed")

    def __call__(self, payload: dict[str, object], *, timeout_seconds: float,
                 cancellation: Event) -> bytes:
        if not _number(timeout_seconds) or not 0 < timeout_seconds <= 120:
            raise LocalChatTransportError("invalid_timeout")
        if not isinstance(cancellation, Event):
            raise LocalChatTransportError("invalid_cancellation")
        connection = None
        try:
            snapshot = self._initial
            self._fence(snapshot)
            (host, port, family, authority, request_limit, response_limit,
             header_limit, clock) = snapshot
            start = clock()
            if not _number(start):
                raise LocalChatTransportError("invalid_clock")
            last = start
            deadline = start + timeout_seconds
            if not _number(deadline) or deadline <= start:
                raise LocalChatTransportError("invalid_clock")

            def check() -> float:
                nonlocal last
                self._fence(snapshot)
                if cancellation.is_set():
                    raise LocalChatTransportError("cancelled")
                now = clock()
                self._fence(snapshot)
                if cancellation.is_set():
                    raise LocalChatTransportError("cancelled")
                if not _number(now) or now < last:
                    raise LocalChatTransportError("invalid_clock")
                last = now
                if now >= deadline:
                    raise LocalChatTransportError("timeout")
                return deadline - now

            check()
            body = _request_bytes(payload, request_limit)
            check()
            headers = (f"POST {_PATH} HTTP/1.1\r\nHost: {authority}\r\n"
                       "Content-Type: application/json\r\nAccept: application/json\r\n"
                       "Accept-Encoding: identity\r\nConnection: close\r\n"
                       f"Content-Length: {len(body)}\r\n\r\n").encode("ascii")
            connection = socket.socket(family, socket.SOCK_STREAM)
            connection.setblocking(False)

            def wait(*, write=False) -> None:
                while True:
                    remaining = check()
                    readable, writable, exceptional = select.select(
                        [] if write else [connection], [connection] if write else [],
                        [connection], min(remaining, 0.05),
                    )
                    check()
                    if exceptional:
                        raise LocalChatTransportError("transport_error")
                    if readable or writable:
                        return

            target = ((host, port, 0, 0) if family == socket.AF_INET6 else (host, port))
            code = connection.connect_ex(target)
            pending = {0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY,
                       10035, 10036, 10037}
            if code not in pending:
                raise LocalChatTransportError("transport_error")
            wait(write=True)
            if connection.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                raise LocalChatTransportError("transport_error")
            outgoing = memoryview(headers + body)
            while outgoing:
                wait(write=True)
                try:
                    sent = connection.send(outgoing)
                except BlockingIOError:
                    continue
                if sent <= 0:
                    raise LocalChatTransportError("transport_error")
                outgoing = outgoing[sent:]
            buffered = bytearray()
            length = None
            framing_ready = False
            decoder = None
            while True:
                wait()
                try:
                    chunk = connection.recv(8192)
                except BlockingIOError:
                    continue
                check()
                if not chunk:
                    if decoder is not None:
                        result = decoder.finish()
                        check()
                        return result
                    if framing_ready and len(buffered) == length:
                        result = bytes(buffered)
                        check()
                        return result
                    raise LocalChatTransportError("response_interrupted")
                if not framing_ready:
                    buffered.extend(chunk)
                    boundary = buffered.find(b"\r\n\r\n")
                    if boundary < 0:
                        if len(buffered) > header_limit:
                            raise LocalChatTransportError("response_limit_exceeded")
                        continue
                    if boundary + 4 > header_limit:
                        raise LocalChatTransportError("response_limit_exceeded")
                    length = self._parse_headers(bytes(buffered[:boundary]), response_limit)
                    chunk = bytes(buffered[boundary + 4:])
                    buffered.clear()
                    framing_ready = True
                    if length is None:
                        decoder = _ChunkedDecoder(response_limit, check=check)
                if decoder is not None:
                    decoder.feed(chunk)
                    continue
                buffered.extend(chunk)
                if len(buffered) > length:
                    raise LocalChatTransportError("invalid_http_response")
                # Require peer close after the exact declared body; late extra
                # bytes cannot become a second ambiguous response or JSON tail.
        except LocalChatTransportError:
            raise
        except Exception:
            raise LocalChatTransportError("transport_error") from None
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _parse_headers(raw: bytes, response_limit: int) -> int | None:
        """Return a fixed length or None for the one supported chunked coding."""
        lines = raw.split(b"\r\n")
        if not re.fullmatch(rb"HTTP/1\.[01] [0-9]{3}(?: [\x20-\x7e]*)?", lines[0]):
            raise LocalChatTransportError("invalid_http_response")
        if lines[0][9:12] != b"200":
            raise LocalChatTransportError("http_request_refused")
        values = {}
        if len(lines) > 65:
            raise LocalChatTransportError("response_limit_exceeded")
        for line in lines[1:]:
            name, separator, value = line.partition(b":")
            key = name.lower()
            if (not separator or not _HEADER_TOKEN.fullmatch(name) or key in values
                    or any(c < 32 or c > 126 for c in value)):
                raise LocalChatTransportError("invalid_http_response")
            values[key] = value.strip().lower()
        if b"transfer-encoding" in values and b"content-length" in values:
            raise LocalChatTransportError("invalid_http_response")
        if (values.get(b"content-encoding", b"identity") != b"identity"
                or b"trailer" in values):
            raise LocalChatTransportError("unsupported_response_encoding")
        if values.get(b"content-type") not in {
            b"application/json", b"application/json; charset=utf-8",
            b"application/json;charset=utf-8",
        }:
            raise LocalChatTransportError("unsupported_response_encoding")
        if b"transfer-encoding" in values:
            if values[b"transfer-encoding"] != b"chunked":
                raise LocalChatTransportError("unsupported_response_encoding")
            if not lines[0].startswith(b"HTTP/1.1 "):
                raise LocalChatTransportError("invalid_http_response")
            return None
        length = values.get(b"content-length", b"")
        if (not 1 <= len(length) <= 8 or not length.isdigit()
                or str(int(length)).encode("ascii") != length):
            raise LocalChatTransportError("invalid_http_response")
        count = int(length)
        if not 1 <= count <= response_limit:
            raise LocalChatTransportError("response_limit_exceeded")
        return count
