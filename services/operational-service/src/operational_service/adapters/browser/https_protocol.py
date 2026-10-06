"""Bounded HTTP/1.1 response framing for one credentialless HTTPS GET.

No header, trailer or chunk extension can supply identity, actions or authority.
Bodies are returned as exact bytes; the reader owns UTF-8/content validation.
RFC 9112 sections 5-8 and RFC 9110 section 5.6 define the framing/token grammar.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, fields

from .https_contracts import HttpsReadLimits, HttpsReadRefused

_TOKEN = re.compile(rb"[!#$%&'*+\-.^_`|~0-9A-Za-z]+\Z")
_TOKEN_BYTES = frozenset(
    b"!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)
_CRITICAL = frozenset(
    {b"content-length", b"transfer-encoding", b"content-type", b"content-encoding"}
)
_CALLBACK_CODES = frozenset({"cancelled", "deadline_exceeded", "invalid_clock"})
_PARSER_CODES = frozenset(
    {
        "invalid_http_input",
        "invalid_headers",
        "headers_too_large",
        "line_too_large",
        "unexpected_http_status",
        "duplicate_headers",
        "invalid_body_length",
        "conflicting_framing",
        "unsupported_transfer_encoding",
        "unexpected_content_type",
        "unsupported_content_encoding",
        "body_too_large",
        "incomplete_headers",
        "incomplete_body",
        "invalid_chunked_body",
        "too_many_chunks",
        "trailers_too_large",
        "forbidden_trailer",
        "overhead_too_large",
        "transport_unavailable",
        *_CALLBACK_CODES,
    }
)


@dataclass(frozen=True, slots=True)
class ParsedHttpsResponse:
    body: bytes = field(repr=False)
    media_type: str


class _Input:
    def __init__(self, receive, limits, check):
        self.receive = receive
        self.limits = limits
        self.check_callback = check
        self.pending = bytearray()
        self.eof = False
        self.overhead = 0

    def check(self):
        try:
            value = self.check_callback()
        except HttpsReadRefused as error:
            if error.code in _CALLBACK_CODES:
                raise
            raise HttpsReadRefused("invalid_clock") from None
        except Exception:
            raise HttpsReadRefused("invalid_clock") from None
        if type(value) not in (int, float) or not math.isfinite(value):
            raise HttpsReadRefused("invalid_clock")
        if value <= 0:
            raise HttpsReadRefused("deadline_exceeded")

    def fill(self, maximum):
        self.check()
        if self.eof:
            return
        maximum = min(maximum, 4096)
        if maximum < 1:
            raise HttpsReadRefused("invalid_http_input")
        try:
            chunk = self.receive(maximum)
        except HttpsReadRefused as error:
            if error.code in _CALLBACK_CODES | {"transport_unavailable"}:
                raise
            raise HttpsReadRefused("transport_unavailable") from None
        except Exception:
            raise HttpsReadRefused("transport_unavailable") from None
        self.check()
        if type(chunk) is not bytes or len(chunk) > maximum:
            raise HttpsReadRefused("invalid_http_input")
        if not chunk:
            self.eof = True
        else:
            self.pending.extend(chunk)

    def add_overhead(self, count):
        self.check()
        self.overhead += count
        if self.overhead > self.limits.max_overhead_bytes:
            raise HttpsReadRefused("overhead_too_large")

    def line(self, maximum, too_large, incomplete):
        self.check()
        remaining = self.limits.max_overhead_bytes - self.overhead
        if remaining < maximum:
            maximum, too_large = remaining, "overhead_too_large"
        while True:
            boundary = self.pending.find(b"\r\n")
            if boundary >= 0:
                count = boundary + 2
                if count > maximum:
                    raise HttpsReadRefused(too_large)
                result = bytes(self.pending[:boundary])
                del self.pending[:count]
                self.add_overhead(count)
                self.check()
                return result
            if len(self.pending) >= maximum:
                raise HttpsReadRefused(too_large)
            if self.eof:
                raise HttpsReadRefused(incomplete)
            self.fill(maximum - len(self.pending))

    def exact(self, count):
        self.check()
        result = bytearray()
        while len(result) < count:
            self.check()
            if not self.pending:
                if self.eof:
                    raise HttpsReadRefused("incomplete_body")
                self.fill(count - len(result))
                continue
            size = min(count - len(result), len(self.pending))
            result.extend(self.pending[:size])
            del self.pending[:size]
        self.check()
        return bytes(result)

    def require_eof(self):
        self.check()
        if self.pending:
            raise HttpsReadRefused("invalid_body_length")
        self.fill(1)
        if self.pending or not self.eof:
            raise HttpsReadRefused("invalid_body_length")
        self.check()


def _field(line: bytes) -> tuple[bytes, bytes]:
    if b":" not in line:
        raise HttpsReadRefused("invalid_headers")
    name, value = line.split(b":", 1)
    if not _TOKEN.fullmatch(name) or any(byte < 32 and byte != 9 or byte == 127 for byte in value):
        raise HttpsReadRefused("invalid_headers")
    return name.lower(), value.strip(b" \t")


def _parameters(raw: bytes, *, extension: bool) -> Iterator[tuple[bytes, bytes | None]]:
    """Parse RFC token/quoted-string metadata without acting on its contents."""
    index = 0
    code = "invalid_chunked_body" if extension else "unexpected_content_type"

    def whitespace(position):
        while position < len(raw) and raw[position] in (32, 9):
            position += 1
        return position

    while index < len(raw):
        index = whitespace(index)
        if index >= len(raw) or raw[index] != 59:
            raise HttpsReadRefused(code)
        index = whitespace(index + 1)
        start = index
        while index < len(raw) and raw[index] in _TOKEN_BYTES:
            index += 1
        if start == index:
            # Media parameters permit empty semicolon entries (RFC 9110 5.6.6).
            if not extension and (index == len(raw) or raw[index] == 59):
                continue
            raise HttpsReadRefused(code)
        name = raw[start:index].lower()
        equals = whitespace(index) if extension else index
        if equals < len(raw) and raw[equals] == 61:
            index = whitespace(equals + 1) if extension else equals + 1
            if index < len(raw) and raw[index] == 34:
                index += 1
                value = bytearray()
                while index < len(raw) and raw[index] != 34:
                    byte = raw[index]
                    if byte == 92:
                        index += 1
                        if index >= len(raw):
                            raise HttpsReadRefused(code)
                        byte = raw[index]
                    if byte != 9 and not 32 <= byte <= 126 and byte < 128:
                        raise HttpsReadRefused(code)
                    value.append(byte)
                    index += 1
                if index >= len(raw):
                    raise HttpsReadRefused(code)
                index += 1
                parsed = bytes(value)
            else:
                start = index
                while index < len(raw) and raw[index] in _TOKEN_BYTES:
                    index += 1
                if start == index:
                    raise HttpsReadRefused(code)
                parsed = raw[start:index]
        elif extension:
            parsed = None
        else:
            raise HttpsReadRefused(code)
        yield name, parsed
        # Any trailing BWS in chunk-ext must precede the next semicolon.
        if index < len(raw) and whitespace(index) == len(raw):
            if extension:
                raise HttpsReadRefused(code)
            return


def _media(raw: bytes) -> str:
    separator = raw.find(b";")
    base = (raw if separator < 0 else raw[:separator]).strip(b" \t").lower()
    if base not in {b"text/plain", b"text/html"}:
        raise HttpsReadRefused("unexpected_content_type")
    if separator >= 0:
        charset = False
        for name, value in _parameters(raw[separator:], extension=False):
            if name == b"charset":
                if charset or value.lower() != b"utf-8":
                    raise HttpsReadRefused("unexpected_content_type")
                charset = True
    return base.decode("ascii")


def _decimal(raw: bytes, maximum: int) -> int:
    if not re.fullmatch(rb"[0-9]+", raw):
        raise HttpsReadRefused("invalid_body_length")
    digits = raw.lstrip(b"0") or b"0"
    if len(digits) > len(str(maximum)) or int(digits) > maximum:
        raise HttpsReadRefused("body_too_large")
    return int(digits)


def _chunk_size(raw: bytes, maximum: int) -> int:
    match = re.match(rb"[0-9A-Fa-f]+", raw)
    if match is None:
        raise HttpsReadRefused("invalid_chunked_body")
    digits = match.group().lstrip(b"0") or b"0"
    if len(digits) > len(f"{maximum:x}") or int(digits, 16) > maximum:
        raise HttpsReadRefused("body_too_large")
    for _ in _parameters(raw[match.end() :], extension=True):
        pass
    return int(digits, 16)


def read_response(
    receive: Callable[[int], bytes],
    limits: HttpsReadLimits,
    check: Callable[[], float],
) -> ParsedHttpsResponse:
    """Read one complete response and its EOF; never return partial success."""
    if type(limits) is not HttpsReadLimits or not callable(receive) or not callable(check):
        raise HttpsReadRefused("invalid_http_input")
    # Frozen dataclasses can still be altered with object.__setattr__. Revalidate
    # and snapshot policy before calling any supplied hook; hooks cannot expand it.
    try:
        limits = HttpsReadLimits(
            **{item.name: getattr(limits, item.name) for item in fields(HttpsReadLimits)}
        )
    except Exception:
        raise HttpsReadRefused("invalid_http_input") from None
    stream = _Input(receive, limits, check)
    try:
        used = 0

        def header_line():
            nonlocal used
            remaining = limits.max_header_bytes - used
            line = stream.line(remaining, "headers_too_large", "incomplete_headers")
            used += len(line) + 2
            return line

        status = header_line()
        if not re.fullmatch(rb"HTTP/1\.1 200 [\t\x20-\x7e\x80-\xff]*", status):
            raise HttpsReadRefused("unexpected_http_status")
        stream.check()
        critical = {}
        while True:
            line = header_line()
            if not line:
                break
            name, value = _field(line)
            if name in _CRITICAL:
                if name in critical:
                    raise HttpsReadRefused("duplicate_headers")
                critical[name] = value
            stream.check()
        if b"content-length" in critical and b"transfer-encoding" in critical:
            raise HttpsReadRefused("conflicting_framing")
        media_type = _media(critical.get(b"content-type", b""))
        if critical.get(b"content-encoding", b"identity").lower() != b"identity":
            raise HttpsReadRefused("unsupported_content_encoding")
        stream.check()
        if b"transfer-encoding" in critical:
            if critical[b"transfer-encoding"].lower() != b"chunked":
                raise HttpsReadRefused("unsupported_transfer_encoding")
            body = bytearray()
            chunks = 0
            while True:
                line = stream.line(limits.max_chunk_line_bytes, "line_too_large", "incomplete_body")
                size = _chunk_size(line, limits.max_body_bytes - len(body))
                stream.check()
                if size == 0:
                    break
                chunks += 1
                if chunks > limits.max_chunks:
                    raise HttpsReadRefused("too_many_chunks")
                body.extend(stream.exact(size))
                if stream.exact(2) != b"\r\n":
                    raise HttpsReadRefused("invalid_chunked_body")
                stream.add_overhead(2)
            trailers = 0
            while True:
                remaining = limits.max_trailer_bytes - trailers
                line = stream.line(remaining, "trailers_too_large", "incomplete_body")
                trailers += len(line) + 2
                if not line:
                    break
                name, _ = _field(line)
                if name in _CRITICAL:
                    raise HttpsReadRefused("forbidden_trailer")
                stream.check()
            body = bytes(body)
        elif b"content-length" in critical:
            body = stream.exact(_decimal(critical[b"content-length"], limits.max_body_bytes))
        else:
            raise HttpsReadRefused("invalid_body_length")
        stream.require_eof()
        stream.check()
        return ParsedHttpsResponse(body, media_type)
    except HttpsReadRefused as error:
        if error.code in _PARSER_CODES:
            raise
        raise HttpsReadRefused("invalid_http_input") from None
    except Exception:
        raise HttpsReadRefused("invalid_http_input") from None
