"""Bounded chunk framing, independently specified wire examples (not SSE)."""

from __future__ import annotations

import pytest
from inference_service import local_chat_transport as transport


def _decode(parts, *, limit=1_048_576, check=lambda: None):
    decoder = transport._ChunkedDecoder(limit, check=check)
    for part in parts:
        decoder.feed(part)
    return decoder.finish()


@pytest.mark.parametrize("width", [1, 2, 3, 7, 16, 8192])
def test_chunk_boundaries_are_independent_of_receive_boundaries(width):
    # UTF-8 and HTTP framing may both be split at every individual byte.
    wire = b'1\r\n{\r\n8\r\n"x":"\xc3\xa1"\r\n1\r\n}\r\n0\r\n\r\n'
    assert _decode([wire[i:i + width] for i in range(0, len(wire), width)]) == b'{"x":"\xc3\xa1"}'


@pytest.mark.parametrize("size", [2049, 4097, 65536, 1_048_576])
def test_large_valid_chunk_is_bounded_by_decoded_size_not_old_small_response_assumption(size):
    body = b"x" * size
    wire = f"{size:X}\r\n".encode("ascii") + body + b"\r\n0\r\n\r\n"
    assert _decode([wire[i:i + 8192] for i in range(0, len(wire), 8192)], limit=size) == body


@pytest.mark.parametrize("wire,code", [
    (b"g\r\n", "invalid_http_response"),
    (b"+1\r\nx\r\n0\r\n\r\n", "invalid_http_response"),
    (b" 1\r\nx\r\n0\r\n\r\n", "invalid_http_response"),
    (b"1 \r\nx\r\n0\r\n\r\n", "invalid_http_response"),
    (b"0x1\r\nx\r\n0\r\n\r\n", "invalid_http_response"),
    (b"1\nx\r\n0\r\n\r\n", "invalid_http_response"),
    (b"1\rx\r\n0\r\n\r\n", "invalid_http_response"),
    (b"1\r\nx\n0\r\n\r\n", "invalid_http_response"),
    (b"1\r\nx\ry0\r\n\r\n", "invalid_http_response"),
    (b"1;foo=secret\r\nx\r\n0\r\n\r\n", "unsupported_response_encoding"),
    (b"0;foo=secret\r\n\r\n", "unsupported_response_encoding"),
    (b"1\r\nx\r\n0\r\nX-Private: secret\r\n\r\n", "unsupported_response_encoding"),
    (b"1\r\nx\r\n0\r\n\r\nextra", "invalid_http_response"),
    (b"1\r\nx\r\n0\r\n\r\nHTTP/1.1 200 OK\r\n\r\n", "invalid_http_response"),
    (b"FFFFFFFF\r\n", "response_limit_exceeded"),
    (b"100000000\r\n", "response_limit_exceeded"),
    (b"000000000\r\n", "response_limit_exceeded"),
    (b"0\r\n\r\n", "response_limit_exceeded"),
])
def test_invalid_or_unsupported_chunk_framing_has_fixed_private_error(wire, code):
    with pytest.raises(transport.LocalChatTransportError) as caught:
        _decode([bytes([byte]) for byte in wire], limit=64)
    assert caught.value.code == code
    assert str(caught.value) == code
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("wire", [
    b"", b"1", b"1\r", b"1\r\n", b"2\r\nx", b"1\r\nx", b"1\r\nx\r",
    b"1\r\nx\r\n", b"1\r\nx\r\n0", b"1\r\nx\r\n0\r", b"1\r\nx\r\n0\r\n",
    b"1\r\nx\r\n0\r\n\r",
])
def test_eof_at_any_incomplete_framing_stage_never_returns_partial_body(wire):
    with pytest.raises(transport.LocalChatTransportError, match="response_interrupted"):
        _decode([wire])


def test_decoded_limit_accounts_for_all_chunks_before_accepting_data():
    decoder = transport._ChunkedDecoder(3, check=lambda: None)
    decoder.feed(b"2\r\nab\r\n")
    with pytest.raises(transport.LocalChatTransportError, match="response_limit_exceeded"):
        decoder.feed(b"2\r\n")


def test_small_chunks_cannot_turn_metadata_into_unbounded_work():
    decoder = transport._ChunkedDecoder(8192, check=lambda: None)
    with pytest.raises(transport.LocalChatTransportError, match="response_limit_exceeded"):
        decoder.feed(b"1\r\nx\r\n" * 4097 + b"0\r\n\r\n")


def test_wire_limit_is_enforced_without_buffering_attacker_input():
    decoder = transport._ChunkedDecoder(1, check=lambda: None)
    with pytest.raises(transport.LocalChatTransportError, match="response_limit_exceeded"):
        decoder.feed(b"x" * (65_536 + 2))


def test_cancellation_or_deadline_is_checked_during_buffered_chunk_processing():
    count = 0

    def check():
        nonlocal count
        count += 1
        if count == 10:
            raise transport.LocalChatTransportError("cancelled")

    with pytest.raises(transport.LocalChatTransportError, match="cancelled"):
        _decode([b"1\r\nx\r\n" * 100 + b"0\r\n\r\n"], check=check)
    assert count == 10


@pytest.mark.parametrize("zero", [b"0", b"00", b"00000000"])
def test_rfc_hexadecimal_zero_and_case_are_accepted_without_extensions(zero):
    assert _decode([b"a\r\n0123456789\r\n" + zero + b"\r\n\r\n"]) == b"0123456789"


def _headers(*fields, version=b"1.1"):
    return (b"HTTP/" + version + b" 200 OK\r\nContent-Type: application/json\r\n"
            + b"\r\n".join(fields))


@pytest.mark.parametrize("fields,code", [
    ((b"Transfer-Encoding: chunked", b"Content-Length: 2"), "invalid_http_response"),
    ((b"Transfer-Encoding: chunked", b"Transfer-Encoding: chunked"), "invalid_http_response"),
    ((b"Transfer-Encoding: gzip, chunked",), "unsupported_response_encoding"),
    ((b"Transfer-Encoding: chunked, chunked",), "unsupported_response_encoding"),
    ((b"Transfer-Encoding: chunked; foo=bar",), "unsupported_response_encoding"),
    ((b"Transfer-Encoding: identity",), "unsupported_response_encoding"),
    ((b"Transfer-Encoding: chunked", b"Trailer: X-Digest"), "unsupported_response_encoding"),
    ((b"Transfer-Encoding: chunked", b"Content-Encoding: gzip"),
     "unsupported_response_encoding"),
    ((b"Transfer-Encoding : chunked",), "invalid_http_response"),
    ((b"Transfer-Encoding: chunked\nX-Secret: secret",), "invalid_http_response"),
])
def test_ambiguous_headers_never_select_a_framing_mode(fields, code):
    with pytest.raises(transport.LocalChatTransportError, match=code):
        transport.LocalChatHttpTransport._parse_headers(_headers(*fields), 64)


def test_http10_chunked_is_not_an_accepted_wire_protocol():
    with pytest.raises(transport.LocalChatTransportError, match="invalid_http_response"):
        transport.LocalChatHttpTransport._parse_headers(
            _headers(b"Transfer-Encoding: chunked", version=b"1.0"), 64,
        )


def test_headers_select_only_whole_json_chunked_or_existing_content_length():
    assert transport.LocalChatHttpTransport._parse_headers(
        _headers(b"Transfer-Encoding: ChUnKeD"), 64,
    ) is None
    assert transport.LocalChatHttpTransport._parse_headers(
        _headers(b"Content-Length: 2"), 64,
    ) == 2
