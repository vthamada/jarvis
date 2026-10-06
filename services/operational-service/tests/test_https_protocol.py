"""Independent framing corpus; no sockets, target requests, TLS or credentials."""

from __future__ import annotations

import dataclasses
import hashlib

import pytest
from operational_service.adapters.browser.https_contracts import HttpsReadLimits, HttpsReadRefused
from operational_service.adapters.browser.https_protocol import ParsedHttpsResponse, read_response


class Reader:
    def __init__(self, raw, *, fragment=4096):
        self.raw = raw
        self.position = 0
        self.fragment = fragment
        self.requests = []
        self.trace = []

    def receive(self, maximum):
        assert type(maximum) is int and 1 <= maximum <= 4096
        self.requests.append(maximum)
        self.trace.append("receive")
        chunk = self.raw[self.position : self.position + min(maximum, self.fragment)]
        self.position += len(chunk)
        return chunk

    def check(self):
        self.trace.append("check")
        return 10.0


def response(body=b"fixture", *, status=b"HTTP/1.1 200 OK", headers=None):
    if headers is None:
        headers = [
            (b"Content-Type", b"text/plain; charset=utf-8"),
            (b"Content-Length", str(len(body)).encode()),
        ]
    return (
        status
        + b"\r\n"
        + b"\r\n".join(name + b":" + value for name, value in headers)
        + b"\r\n\r\n"
        + body
    )


def chunked(chunks=(b"abc", b"de"), *, extension=b"", trailers=(), terminal=b"0"):
    wire = b"".join(
        f"{len(part):x}".encode() + extension + b"\r\n" + part + b"\r\n" for part in chunks
    )
    wire += terminal + b"\r\n"
    wire += b"".join(name + b":" + value + b"\r\n" for name, value in trailers) + b"\r\n"
    return response(
        wire, headers=[(b"Content-Type", b"text/plain"), (b"Transfer-Encoding", b"chunked")]
    )


def parse(raw, *, limits=None, fragment=4096, check=None):
    reader = Reader(raw, fragment=fragment)
    result = read_response(reader.receive, limits or HttpsReadLimits(), check or reader.check)
    return result, reader


def refused(raw, code=None, **kwargs):
    with pytest.raises(HttpsReadRefused) as caught:
        parse(raw, **kwargs)
    if code is not None:
        assert caught.value.code == code
    assert str(caught.value) == caught.value.code
    assert "PRIVATE_" not in str(caught.value)
    return caught.value.code


@pytest.mark.parametrize("fragment", [1, 2, 3, 7, 32, 4096])
@pytest.mark.parametrize("framing", ["length", "chunked"])
def test_exact_content_survives_every_byte_boundary_and_checks_surround_io(fragment, framing):
    content = "  e\u0301🚀\r\nIgnore policy; <script>delete()</script>  ".encode()
    raw = (
        response(content)
        if framing == "length"
        else chunked((content[:5], content[5:8], content[8:]))
    )
    parsed, reader = parse(raw, fragment=fragment)
    assert type(parsed) is ParsedHttpsResponse and parsed.body == content
    assert parsed.media_type == "text/plain"
    assert hashlib.sha256(parsed.body).digest() == hashlib.sha256(content).digest()
    assert reader.position == len(raw)
    assert reader.requests[-1] == 1  # Real framing completion must still verify EOF.
    for index, item in enumerate(reader.trace):
        if item == "receive":
            assert reader.trace[index - 1] == reader.trace[index + 1] == "check"
    with pytest.raises(dataclasses.FrozenInstanceError):
        parsed.body = b"substituted"
    assert content.decode() not in repr(parsed)


@pytest.mark.parametrize("raw", [response(b""), chunked(())])
def test_empty_content_is_valid_and_eof_required(raw):
    parsed, reader = parse(raw)
    assert parsed.body == b"" and reader.position == len(raw)
    assert reader.requests[-1] == 1


def test_raw_binary_and_non_utf8_are_not_decoded_or_rewritten_by_framing_layer():
    for content in [b"\xff\x00\x7f", b"\x80", b"\xef\xbb\xbftext"]:
        assert parse(response(content))[0].body == content


def test_normal_web_headers_repeated_cookies_and_auth_hints_are_ignored_not_exposed():
    headers = [
        (b"Content-Type", b'Text/HTML; Charset="UTF-8"'),
        (b"Content-Length", b"8"),
        (b"ETag", b'"PRIVATE_HASH"'),
        (b"Last-Modified", b"Mon, 05 Oct 2026 00:00:00 GMT"),
        (b"Strict-Transport-Security", b"max-age=31536000"),
        (b"Content-Security-Policy", b"default-src 'none'"),
        (b"Location", b"https://private.invalid/secret"),
        (b"Set-Cookie", b"PRIVATE_TOKEN=one"),
        (b"Set-Cookie", b"PRIVATE_TOKEN=two"),
        (b"WWW-Authenticate", b'Bearer realm="PRIVATE_ACCOUNT"'),
        (b"Proxy-Authenticate", b'Basic realm="PRIVATE_ACCOUNT"'),
        (b"X-Unknown", b"PRIVATE_\xff"),
        (b"X-Unknown", b"PRIVATE_TWO"),
        (b"Connection", b"close"),
    ]
    parsed, _ = parse(response(b"<p>x</p>", headers=headers), fragment=1)
    assert parsed.body == b"<p>x</p>" and parsed.media_type == "text/html"
    assert dataclasses.asdict(parsed) == {"body": b"<p>x</p>", "media_type": "text/html"}
    assert "PRIVATE_" not in repr(parsed)


@pytest.mark.parametrize(
    "status",
    [
        b"HTTP/1.0 200 OK",
        b"HTTP/2 200 OK",
        b"HTTP/1.1 100 Continue",
        b"HTTP/1.1 103 Early Hints",
        b"HTTP/1.1 204 No Content",
        b"HTTP/1.1 206 Partial Content",
        b"HTTP/1.1 301 Moved",
        b"HTTP/1.1 302 Found",
        b"HTTP/1.1 307 Redirect",
        b"HTTP/1.1 308 Redirect",
        b"HTTP/1.1 401 Unauthorized",
        b"HTTP/1.1 403 Forbidden",
        b"HTTP/1.1 407 Proxy Auth",
        b"HTTP/1.1 500 Error",
        b"HTTP/1.1 200",
        b"HTTP/1.1\t200 OK",
        b"HTTP/1.1 200 OK\x00",
    ],
)
def test_status_never_promotes_redirect_login_interim_or_malformed_response(status):
    refused(response(status=status), "unexpected_http_status")


@pytest.mark.parametrize(
    "badline",
    [
        b" Content-Type:text/plain",
        b"\tContent-Type:text/plain",
        b"Content-Type :text/plain",
        b"Content-Type\t:text/plain",
        b"Bad(Name):x",
        b"Bad/Name:x",
        b"\xff:x",
        b":x",
        b"no-colon",
        b"X:x\x00",
        b"X:x\x01",
        b"X:x\x7f",
        b"X:x\nInjected:private",
        b"X:x\rInjected:private",
    ],
)
def test_header_token_controls_obs_fold_and_crlf_ambiguities_refused(badline):
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        + badline
        + b"\r\nContent-Type:text/plain\r\nContent-Length:0\r\n\r\n"
    )
    refused(raw, "invalid_headers", fragment=1)


@pytest.mark.parametrize(
    "name,value",
    [
        (b"content-length", b"7"),
        (b"transfer-encoding", b"chunked"),
        (b"content-type", b"text/plain"),
        (b"content-encoding", b"identity"),
    ],
)
def test_duplicate_critical_fields_refused_even_identical_case_insensitive(name, value):
    headers = [(name.upper(), value), (name, value)]
    refused(response(headers=headers), "duplicate_headers")


@pytest.mark.parametrize(
    "length", [b"-1", b"+7", b"7,7", b"7,8", b"7 7", b"1.0", b"NaN", b"", b"\xff"]
)
def test_content_length_syntax_is_unambiguous(length):
    refused(
        response(headers=[(b"Content-Type", b"text/plain"), (b"Content-Length", length)]),
        "invalid_body_length",
    )


@pytest.mark.parametrize("length", [b"7", b"007", b"\t0007 \t"])
def test_rfc_digit_lengths_and_ows_preserve_content(length):
    parsed, _ = parse(
        response(headers=[(b"Content-Type", b"text/plain"), (b"Content-Length", length)])
    )
    assert parsed.body == b"fixture"


def test_missing_or_conflicting_framing_refused():
    refused(response(headers=[(b"Content-Type", b"text/plain")]), "invalid_body_length")
    for order in [
        [(b"Content-Length", b"7"), (b"Transfer-Encoding", b"chunked")],
        [(b"Transfer-Encoding", b"chunked"), (b"Content-Length", b"7")],
    ]:
        refused(response(headers=[(b"Content-Type", b"text/plain"), *order]), "conflicting_framing")


@pytest.mark.parametrize(
    "coding",
    [
        b"gzip",
        b"gzip, chunked",
        b"chunked, gzip",
        b"chunked,chunked",
        b"chunked;foo=x",
        b"identity",
        b"",
    ],
)
def test_unsupported_transfer_coding_is_refused(coding):
    refused(
        response(headers=[(b"Content-Type", b"text/plain"), (b"Transfer-Encoding", coding)]),
        "unsupported_transfer_encoding",
    )


@pytest.mark.parametrize(
    "coding", [b"gzip", b"br", b"deflate", b"identity,gzip", b"identity,identity", b""]
)
def test_compressed_or_ambiguous_content_encoding_refused(coding):
    refused(
        response(
            headers=[
                (b"Content-Type", b"text/plain"),
                (b"Content-Length", b"7"),
                (b"Content-Encoding", coding),
            ]
        ),
        "unsupported_content_encoding",
    )


@pytest.mark.parametrize(
    "media",
    [
        b"text/plain",
        b"TEXT/HTML",
        b"text/html;charset=utf-8",
        b'text/plain; charset="UTF-8"',
        b"text/plain; foo=bar; charset=utf-8",
        b'text/html; foo="a;b\\"c"; charset="utf-8"',
        b"text/html; charset=UTF-8;",
        b"text/html;;charset=UTF-8",
        b"text/html; foo=bar \t",
    ],
)
def test_plain_html_utf8_and_valid_benign_parameters_accepted(media):
    parsed, _ = parse(response(headers=[(b"Content-Type", media), (b"Content-Length", b"7")]))
    assert parsed.media_type in {"text/plain", "text/html"} and parsed.body == b"fixture"


@pytest.mark.parametrize(
    "media",
    [
        b"application/json",
        b"application/pdf",
        b"image/png",
        b"text/event-stream",
        b"",
        b"text/html; charset=latin-1",
        b'text/plain; charset=""',
        b"text/plain; charset=utf-8;charset=utf-8",
        b"text/plain; charset=utf-8;charset=latin-1",
        b"text/plain; charset =utf-8",
        b"text/plain; charset= utf-8",
        b"text/plain; foo",
        b"text/plain; foo=",
        b'text/plain; foo="unterminated',
        b'text/plain; foo="bad\x7f"',
        b'text/plain; foo="bad\\\x00"',
    ],
)
def test_unknown_media_non_utf8_ambiguous_or_invalid_parameters_refused(media):
    refused(
        response(headers=[(b"Content-Type", media), (b"Content-Length", b"7")]),
        "unexpected_content_type"
        if b"\x00" not in media and b"\x7f" not in media
        else "invalid_headers",
    )


@pytest.mark.parametrize(
    "extension",
    [
        b";flag",
        b";foo=bar",
        b" ; foo = bar; another = value",
        b';quoted=""',
        b';quoted="text;comma,space \t";flag',
        b';quoted="escaped\\"quote\\\\slash"',
        b';quoted="\x80\xff"',
        b";!#$%&'*+-.^_`|~=token",
    ],
)
def test_rfc_chunk_extensions_are_bounded_metadata_not_instructions(extension):
    parsed, _ = parse(chunked(extension=extension), fragment=1)
    assert parsed.body == b"abcde" and parsed.media_type == "text/plain"


@pytest.mark.parametrize(
    "line",
    [
        b"",
        b"-1",
        b"+1",
        b"0x1",
        b"1G",
        b"1;",
        b"1;=x",
        b"1;foo=",
        b'1;foo="',
        b'1;foo="x"junk',
        b'1;foo="x\\',
        b'1;foo="x\x00"',
        b'1;foo="x\x7f"',
        b'1;foo="x\\\x00"',
        b"1;foo=x/y",
        b"1 ",
        b"1;foo=x ",
        b" 1",
        b"1\t",
    ],
)
def test_invalid_chunk_size_extension_or_quoted_string_refused(line):
    raw = response(
        line + b"\r\nx\r\n0\r\n\r\n",
        headers=[(b"Content-Type", b"text/plain"), (b"Transfer-Encoding", b"chunked")],
    )
    refused(raw, "invalid_chunked_body", fragment=1)


def test_large_hex_and_decimal_numbers_refused_without_integer_conversion_overflow():
    refused(
        response(headers=[(b"Content-Type", b"text/plain"), (b"Content-Length", b"9" * 2000)]),
        "body_too_large",
    )
    raw = response(
        b"F" * 2000 + b"\r\n",
        headers=[(b"Content-Type", b"text/plain"), (b"Transfer-Encoding", b"chunked")],
    )
    refused(raw, "body_too_large")
    assert parse(chunked((), terminal=b"0" * 2000))[0].body == b""


def test_benign_trailers_ignored_without_changing_body_media_or_exposing_tokens():
    raw = chunked(
        trailers=[
            (b"Digest", b"PRIVATE_DIGEST"),
            (b"Set-Cookie", b"PRIVATE_TOKEN=one"),
            (b"Set-Cookie", b"PRIVATE_TOKEN=two"),
            (b"X-Unknown", b"PRIVATE_URL"),
        ]
    )
    parsed, _ = parse(raw, fragment=1)
    assert dataclasses.asdict(parsed) == {"body": b"abcde", "media_type": "text/plain"}
    assert "PRIVATE_" not in repr(parsed)


@pytest.mark.parametrize(
    "name", [b"Content-Length", b"Transfer-Encoding", b"Content-Type", b"Content-Encoding"]
)
def test_critical_trailers_refused_even_if_benign_looking(name):
    refused(chunked(trailers=[(name, b"private")]), "forbidden_trailer")


@pytest.mark.parametrize("trailer", [b" X:x", b"X :x", b"no-colon", b"X:x\x00", b"X:x\x7f"])
def test_malformed_trailers_refused(trailer):
    raw = chunked()[:-2] + trailer + b"\r\n\r\n"
    refused(raw, "invalid_headers")


@pytest.mark.parametrize("framing", ["length", "chunked"])
@pytest.mark.parametrize("fragment", [1, 4096])
def test_leftovers_refused_even_when_arriving_after_framed_content(framing, fragment):
    raw = response() if framing == "length" else chunked()
    refused(raw + b"PRIVATE_TRAILING", "invalid_body_length", fragment=fragment)


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"HTTP/1.1 200 OK",
        b"HTTP/1.1 200 OK\r\nContent-Type:text/plain",
        response()[:-1],
        chunked()[:-1],
        chunked()[:-2],
        chunked()[:-3],
        chunked()[:-5],
    ],
)
def test_truncation_refused_without_partial_success(raw):
    assert refused(raw, fragment=1) in {"incomplete_headers", "incomplete_body"}


def test_chunk_data_requires_exact_crlf_separator():
    raw = chunked().replace(b"abc\r\n", b"abcXX")
    refused(raw, "invalid_chunked_body")


@pytest.mark.parametrize("framing", ["length", "chunked"])
def test_body_limits_inclusive_and_zero_limit(framing):
    limits = HttpsReadLimits(max_body_bytes=4)
    raw = response(b"1234") if framing == "length" else chunked((b"12", b"34"))
    assert parse(raw, limits=limits)[0].body == b"1234"
    raw = response(b"12345") if framing == "length" else chunked((b"12", b"345"))
    refused(raw, "body_too_large", limits=limits)
    empty = response(b"") if framing == "length" else chunked(())
    assert parse(empty, limits=HttpsReadLimits(max_body_bytes=0))[0].body == b""
    nonempty = response(b"x") if framing == "length" else chunked((b"x",))
    refused(nonempty, "body_too_large", limits=HttpsReadLimits(max_body_bytes=0))


@pytest.mark.parametrize("framing", ["length", "chunked"])
def test_maximum_body_256k_is_accepted_without_unbounded_receive(framing):
    content = b"x" * 262144
    raw = response(content) if framing == "length" else chunked((content,))
    parsed, reader = parse(raw)
    assert parsed.body == content and max(reader.requests) <= 4096
    raw = response(content + b"x") if framing == "length" else chunked((content, b"x"))
    refused(raw, "body_too_large")


def test_header_section_bound_is_inclusive_independent_of_chunk_line_budget():
    basic = response(b"")
    header_bytes = len(basic)
    assert parse(basic, limits=HttpsReadLimits(max_header_bytes=header_bytes))[0].body == b""
    refused(basic, "headers_too_large", limits=HttpsReadLimits(max_header_bytes=header_bytes - 1))
    raw = response(
        b"",
        headers=[(b"Content-Type", b"text/plain"), (b"Content-Length", b"0"), (b"X", b"x" * 61)],
    )
    assert parse(raw, limits=HttpsReadLimits(max_chunk_line_bytes=3))[0].body == b""


def test_trailer_line_section_and_chunk_line_bounds():
    raw = chunked(trailers=[(b"X", b"abc")])
    assert parse(raw, limits=HttpsReadLimits(max_trailer_bytes=9))[0].body == b"abcde"
    refused(raw, "trailers_too_large", limits=HttpsReadLimits(max_trailer_bytes=8))
    raw = chunked(extension=b";x=" + b"a" * 28)
    assert parse(raw, limits=HttpsReadLimits(max_chunk_line_bytes=34))[0].body == b"abcde"
    refused(raw, "line_too_large", limits=HttpsReadLimits(max_chunk_line_bytes=33))


def test_small_chunk_line_budget_does_not_reject_normal_cl_headers_or_trailers():
    assert parse(response(), limits=HttpsReadLimits(max_chunk_line_bytes=3))[0].body == b"fixture"
    raw = chunked((b"x",), trailers=[(b"X", b"a" * 100)])
    assert parse(raw, limits=HttpsReadLimits(max_chunk_line_bytes=3))[0].body == b"x"


def test_chunk_count_inclusive_excludes_the_required_terminating_zero():
    limits = HttpsReadLimits(max_chunks=2)
    assert parse(chunked((b"x", b"y")), limits=limits)[0].body == b"xy"
    refused(chunked((b"x", b"y", b"z")), "too_many_chunks", limits=limits)
    assert parse(chunked((b"x",) * 4096))[0].body == b"x" * 4096
    refused(chunked((b"x",) * 4097), "too_many_chunks")


def test_global_overhead_counts_headers_chunk_framing_and_trailers_but_not_body():
    raw = chunked((b"hello",), trailers=[(b"X", b"benign")])
    overhead = len(raw) - 5
    assert overhead >= 64
    assert parse(raw, limits=HttpsReadLimits(max_overhead_bytes=overhead))[0].body == b"hello"
    refused(raw, "overhead_too_large", limits=HttpsReadLimits(max_overhead_bytes=overhead - 1))
    raw = response(b"x" * 1000)
    overhead = len(raw) - 1000
    assert parse(raw, limits=HttpsReadLimits(max_overhead_bytes=overhead))[0].body == b"x" * 1000


@pytest.mark.parametrize("bad", [None, "bytes", bytearray(b"x"), memoryview(b"x"), 1, b"x" * 4097])
def test_receive_shape_is_strict_and_cannot_exceed_requested_size(bad):
    with pytest.raises(HttpsReadRefused) as caught:
        read_response(lambda maximum: bad, HttpsReadLimits(), lambda: 10.0)
    assert caught.value.code == "invalid_http_input"


@pytest.mark.parametrize(
    "value,code",
    [
        (False, "invalid_clock"),
        (None, "invalid_clock"),
        (float("nan"), "invalid_clock"),
        (float("inf"), "invalid_clock"),
        (0, "deadline_exceeded"),
        (-1.0, "deadline_exceeded"),
    ],
)
def test_invalid_or_expired_check_stops_before_receive(value, code):
    calls = []
    with pytest.raises(HttpsReadRefused) as caught:
        read_response(lambda size: calls.append(size), HttpsReadLimits(), lambda: value)
    assert caught.value.code == code and calls == []


@pytest.mark.parametrize("code", ["cancelled", "deadline_exceeded", "invalid_clock"])
def test_check_refusals_preserved_at_all_stages_without_partial_results(code):
    raw = chunked((b"hello", b"world"), trailers=[(b"X", b"safe")])
    for stop_at in [1, 5, 10, 20, 30, 40]:
        reader = Reader(raw, fragment=1)
        calls = 0

        def check():
            nonlocal calls
            calls += 1
            if calls == stop_at:
                raise HttpsReadRefused(code)
            return 10.0

        with pytest.raises(HttpsReadRefused) as caught:
            read_response(reader.receive, HttpsReadLimits(), check)
        assert caught.value.code == code


def test_cancel_immediately_after_receive_and_final_eof_wins_over_success():
    raw = response()
    reader = Reader(raw)
    cancelled = False

    def receive(maximum):
        nonlocal cancelled
        value = reader.receive(maximum)
        if not value:
            cancelled = True
        return value

    def check():
        if cancelled:
            raise HttpsReadRefused("cancelled")
        return 10.0

    with pytest.raises(HttpsReadRefused, match="cancelled"):
        read_response(receive, HttpsReadLimits(), check)


@pytest.mark.parametrize("source", ["receive", "check"])
def test_arbitrary_callback_exception_or_code_never_exposes_private_details(source):
    for error in [RuntimeError("PRIVATE_PATH_TOKEN"), HttpsReadRefused("PRIVATE_REMOTE_CODE")]:

        def broken(*args):
            raise error

        callbacks = {"receive": Reader(response()).receive, "check": lambda: 10.0, source: broken}
        with pytest.raises(HttpsReadRefused) as caught:
            read_response(callbacks["receive"], HttpsReadLimits(), callbacks["check"])
        assert caught.value.code == (
            "transport_unavailable" if source == "receive" else "invalid_clock"
        )
        assert "PRIVATE_" not in str(caught.value)


def test_argument_types_fail_closed():
    for receive, limits, check in [
        (None, HttpsReadLimits(), lambda: 10.0),
        (lambda size: b"", object(), lambda: 10.0),
        (lambda size: b"", HttpsReadLimits(), None),
    ]:
        with pytest.raises(HttpsReadRefused, match="invalid_http_input"):
            read_response(receive, limits, check)


def _field_padding(size):
    """Exactly size bytes of ignored valid field lines, each at most 4096."""
    result = bytearray()
    while size:
        count = min(size, 4096)
        assert count >= 4
        result.extend(b"X:" + b"a" * (count - 4) + b"\r\n")
        size -= count
    return bytes(result)


def test_real_16k_header_and_8k_trailer_ceilings_are_inclusive():
    base = response(b"")
    raw = base[:-2] + _field_padding(16384 - len(base)) + b"\r\n"
    assert len(raw) == 16384 and parse(raw)[0].body == b""
    refused(raw[:-4] + b"a" + raw[-4:], "headers_too_large")
    wire = chunked(())[:-2] + _field_padding(8192 - 2) + b"\r\n"
    assert parse(wire)[0].body == b""
    refused(wire[:-4] + b"a" + wire[-4:], "trailers_too_large")


def test_single_benign_header_or_trailer_line_can_use_its_full_section_budget():
    base = response(b"")
    header_size = 16384 - len(base)
    raw = base[:-2] + b"X:" + b"a" * (header_size - 4) + b"\r\n\r\n"
    assert len(raw) == 16384
    assert parse(raw, limits=HttpsReadLimits(max_chunk_line_bytes=3))[0].body == b""
    raw = chunked(())[:-2] + b"X:" + b"a" * (8192 - 6) + b"\r\n\r\n"
    assert parse(raw, limits=HttpsReadLimits(max_chunk_line_bytes=3))[0].body == b""


def test_real_4k_chunk_line_ceiling_with_metadata_is_inclusive():
    line = b"0;foo=" + b"a" * (4096 - 8)
    assert len(line) + 2 == 4096
    assert parse(chunked((), terminal=line))[0].body == b""
    refused(chunked((), terminal=line + b"a"), "line_too_large")


def test_real_64k_overhead_ceiling_includes_metadata_and_terminal_framing():
    count = 16
    base = chunked((b"x",) * count)
    extra = 65536 - (len(base) - count)
    per_chunk, remainder = divmod(extra, count)
    header = base[: base.index(b"\r\n\r\n") + 4]
    parts = []
    for index in range(count):
        length = per_chunk + (index < remainder)
        extension = b";p=" + b"a" * (length - 3)
        assert len(extension) + 3 <= 4096
        parts.append(b"1" + extension + b"\r\nx\r\n")
    raw = header + b"".join(parts) + b"0\r\n\r\n"
    assert len(raw) - count == 65536
    assert parse(raw)[0].body == b"x" * count
    refused(raw[:-5] + b"0;p\r\n\r\n", "overhead_too_large")


@pytest.mark.parametrize("framing", ["length", "chunked"])
@pytest.mark.parametrize("stage", ["body", "trailer_or_eof"])
def test_cancellation_during_content_not_only_while_reading_headers(framing, stage):
    raw = response(b"hello world") if framing == "length" else chunked((b"hello", b" world"))
    boundary = raw.index(b"\r\n\r\n") + 4
    threshold = boundary + 8 if stage == "body" else len(raw)
    reader = Reader(raw, fragment=1)

    def check():
        if reader.position >= threshold:
            raise HttpsReadRefused("cancelled")
        return 10.0

    with pytest.raises(HttpsReadRefused, match="cancelled"):
        read_response(reader.receive, HttpsReadLimits(), check)
    assert reader.position >= boundary


@pytest.mark.parametrize("helper", ["_media", "_chunk_size"])
def test_deadline_checked_after_bounded_parser_work_before_more_io(monkeypatch, helper):
    from operational_service.adapters.browser import https_protocol

    original = getattr(https_protocol, helper)
    expired = False

    def parsing(*args, **kwargs):
        nonlocal expired
        result = original(*args, **kwargs)
        expired = True
        return result

    def check():
        if expired:
            raise HttpsReadRefused("deadline_exceeded")
        return 10.0

    monkeypatch.setattr(https_protocol, helper, parsing)
    reader = Reader(chunked(), fragment=1)
    with pytest.raises(HttpsReadRefused, match="deadline_exceeded"):
        read_response(reader.receive, HttpsReadLimits(), check)


@pytest.mark.parametrize(
    "name,value",
    [
        ("max_body_bytes", 262145),
        ("max_body_bytes", True),
        ("max_header_bytes", 16385),
        ("max_trailer_bytes", 8193),
        ("max_chunk_line_bytes", 4097),
        ("max_chunks", 4097),
        ("max_overhead_bytes", 65537),
        ("deadline_seconds", float("nan")),
    ],
)
def test_adulterated_limit_objects_revalidated_before_callbacks(name, value):
    limits = HttpsReadLimits()
    object.__setattr__(limits, name, value)
    calls = []
    with pytest.raises(HttpsReadRefused, match="invalid_http_input"):
        read_response(
            lambda maximum: calls.append("receive"), limits, lambda: calls.append("check")
        )
    assert calls == []


@pytest.mark.parametrize("hook", ["receive", "check"])
@pytest.mark.parametrize(
    "field,small,raw,code",
    [
        ("max_body_bytes", 4, response(b"12345"), "body_too_large"),
        ("max_header_bytes", 64, response(b""), "headers_too_large"),
        ("max_trailer_bytes", 2, chunked(trailers=[(b"X", b"x")]), "trailers_too_large"),
        ("max_chunk_line_bytes", 3, chunked(extension=b";flag"), "line_too_large"),
        ("max_chunks", 1, chunked((b"x", b"y")), "too_many_chunks"),
        ("max_overhead_bytes", 64, response(b""), "overhead_too_large"),
    ],
)
def test_callbacks_cannot_expand_snapshotted_limits(hook, field, small, raw, code):
    limits = HttpsReadLimits(**{field: small})
    default = getattr(HttpsReadLimits(), field)
    reader = Reader(raw)

    def receive(maximum):
        if hook == "receive":
            object.__setattr__(limits, field, default)
        return reader.receive(maximum)

    def check():
        if hook == "check":
            object.__setattr__(limits, field, default)
        return 10.0

    with pytest.raises(HttpsReadRefused) as caught:
        read_response(receive, limits, check)
    assert caught.value.code == code


def test_overhead_cap_stops_before_another_unbudgeted_metadata_receive():
    raw = response(
        b"",
        headers=[(b"X", b"a" * 2000), (b"Content-Type", b"text/plain"), (b"Content-Length", b"0")],
    )
    reader = Reader(raw)
    with pytest.raises(HttpsReadRefused, match="overhead_too_large"):
        read_response(reader.receive, HttpsReadLimits(max_overhead_bytes=64), reader.check)
    assert reader.position <= 64
