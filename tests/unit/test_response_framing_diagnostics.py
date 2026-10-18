"""Parsed HTTP metadata, using real stdlib parsing and synthetic wire bytes only."""

from __future__ import annotations

import http.client
import importlib.util
from io import BytesIO
from pathlib import Path
from threading import Event

import pytest
from inference_service.http_transport import PlanTransportError

_SPEC = importlib.util.spec_from_file_location(
    "_framing_header_fixture", Path(__file__).with_name("test_response_header_diagnostics.py")
)
header = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(header)
PHASES = (
    "responses_http_version", "responses_header_count", "responses_header_parse",
    "responses_media_presence", "responses_content_length", "responses_transfer_encoding",
)
PRIVATE = b"PRIVATE_FRAMING_NEVER_PUBLISHED"


class Socket:
    def __init__(self, wire):
        self.wire = BytesIO(wire)

    def makefile(self, mode):
        return self.wire


class ParsedResponse:
    def __init__(self, wire):
        self.response = http.client.HTTPResponse(Socket(wire))
        self.response.begin()
        self.reads = 0
        self.closed = False

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read1(self, count):
        self.reads += 1
        return self.response.read1(count)

    def close(self):
        self.closed = True
        self.response.close()


def parsed(headers=b"", *, version=b"HTTP/1.1", status=b"200 OK", body=None):
    body = header._FIXTURE.sse() if body is None else body
    return ParsedResponse(version + b" " + status + b"\r\n" + headers + b"\r\n" + body)


def codes(records):
    return {record["phase"]: record["code"] for record in records if record["phase"] in PHASES}


@pytest.mark.parametrize("wire,expected", [
    (b"Content-Length: 0\r\n", ("response_headers_present", "response_header_parse_clean",
                               "response_media_absent", "response_length_zero")),
    (b"Content-Type: \r\nContent-Length: 1\r\n",
     ("response_headers_present", "response_header_parse_clean",
      "response_media_present", "response_length_nonzero")),
    (PRIVATE + b"\r\nContent-Type: text/event-stream\r\nContent-Length: 1\r\n",
     ("response_headers_empty", "response_header_parse_missing_separator",
      "response_media_absent", "response_length_absent")),
])
def test_distinguishes_absent_blank_and_discarded_headers_without_body(wire, expected):
    records = []
    result, error, connection, response, calls = header.run_transport(
        parsed(wire, body=PRIVATE), telemetry=records.append
    )
    assert result is None and error[0] == "unsupported_response_encoding"
    assert codes(records) == dict(zip(PHASES, (
        "response_http_1_1", *expected, "response_transfer_absent"
    ), strict=True))
    assert response.reads == 0 and response.closed and connection.closed and len(calls) == 1
    assert PRIVATE.decode() not in repr(records)
    header.assert_content_free(records)


@pytest.mark.parametrize("field,value,expected", [
    ("Content-Length", b"000", "response_length_zero"),
    ("Content-Length", b"0001", "response_length_nonzero"),
    ("Content-Length", b"-1", "response_length_invalid"),
    ("Content-Length", PRIVATE, "response_length_invalid"),
    ("Content-Length", b"1\r\nContent-Length: 1", "response_length_multiple"),
    ("Transfer-Encoding", b"chunked", "response_transfer_chunked"),
    ("Transfer-Encoding", b"CHUNKED", "response_transfer_chunked"),
    ("Transfer-Encoding", b"", "response_transfer_other"),
    ("Transfer-Encoding", PRIVATE, "response_transfer_other"),
    ("Transfer-Encoding", b"chunked\r\nTransfer-Encoding: chunked",
     "response_transfer_multiple"),
])
def test_framing_values_are_classified_without_relaxing_media_guard(field, value, expected):
    records = []
    result, error, _, response, _ = header.run_transport(
        parsed(field.encode() + b": " + value + b"\r\n", body=PRIVATE),
        telemetry=records.append,
    )
    phase = ("responses_content_length" if field == "Content-Length"
             else "responses_transfer_encoding")
    assert codes(records)[phase] == expected
    assert result is None and error[0] == "unsupported_response_encoding" and response.reads == 0
    header.assert_content_free(records)
    assert PRIVATE.decode() not in repr(records)


@pytest.mark.parametrize("version,expected", [
    (b"HTTP/1.0", "response_http_1_0"), (b"HTTP/1.1", "response_http_1_1")
])
def test_valid_stream_preserves_result_with_fixed_version_metadata(version, expected):
    body = header._FIXTURE.sse()
    records = []
    result, error, connection, response, calls = header.run_transport(
        parsed(b"Content-Type: text/event-stream\r\nContent-Length: "
               + str(len(body)).encode() + b"\r\n", version=version), telemetry=records.append,
    )
    assert result == [header._FIXTURE.COMPLETE] and error is None
    assert codes(records)["responses_http_version"] == expected
    assert len(codes(records)) == len(PHASES)
    assert response.closed and connection.closed and len(calls) == 1
    header.assert_content_free(records)


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("mutation,code", [
    ("cancel", "cancelled"), ("expiry", "credential_expired"), ("deadline", "timeout")
])
def test_each_metadata_observer_is_fenced_before_next_observation_or_read(phase, mutation, code):
    records, cancellation, wall, clock = [], Event(), [1000.0], [1.0]

    def sink(record):
        records.append(dict(record))
        if record["phase"] == phase:
            if mutation == "cancel":
                cancellation.set()
            elif mutation == "expiry":
                wall[0] = 2000.0
            else:
                clock[0] = 11.0

    response = parsed(b"Content-Type: text/event-stream\r\n")
    transport, connection, response, calls = header._FIXTURE.fixture(
        response=response, telemetry=sink, clock=lambda: clock[0], wall_clock=lambda: wall[0]
    )
    with pytest.raises(PlanTransportError, match="^" + code + "$"):
        header._FIXTURE.collect(transport, cancellation=cancellation)
    assert tuple(codes(records)) == PHASES[:PHASES.index(phase) + 1]
    assert response.reads == 0 and response.closed and connection.closed and len(calls) == 1


@pytest.mark.parametrize("mode", ["raise", "mutate"])
def test_observer_exceptions_and_mutation_do_not_affect_result(mode):
    records = []

    def sink(record):
        records.append(dict(record))
        if record["phase"] in PHASES:
            if mode == "raise":
                raise RuntimeError(PRIVATE.decode())
            record.clear()

    result, error, _, response, _ = header.run_transport(
        parsed(b"Content-Type: text/event-stream\r\n"), telemetry=sink
    )
    assert result == [header._FIXTURE.COMPLETE] and error is None and response.closed
    assert len(codes(records)) == len(PHASES)
    header.assert_content_free(records)


def test_default_off_does_not_touch_additional_response_attributes():
    class NoMetadata(header.HeaderResponse):
        def __getattribute__(self, name):
            if name in {"version", "headers"}:
                raise AssertionError("unexpected metadata read")
            return super().__getattribute__(name)

        def getheader(self, key, default):
            return "text/event-stream" if key == "Content-Type" else default

    result, error, _, _, _ = header.run_transport(NoMetadata({}))
    assert result == [header._FIXTURE.COMPLETE] and error is None


def test_unavailable_attributes_are_content_free_and_do_not_change_guard():
    class Unavailable(header.HeaderResponse):
        @property
        def version(self):
            raise RuntimeError(PRIVATE.decode())

    records = []
    result, error, _, _, _ = header.run_transport(
        Unavailable({"Content-Type": "text/event-stream"}), telemetry=records.append
    )
    assert result == [header._FIXTURE.COMPLETE] and error is None
    assert all(code.endswith("unavailable") for code in codes(records).values())
    assert PRIVATE.decode() not in repr(records)


def test_non_200_preserves_no_header_or_body_inspection():
    records = []
    _, error, _, response, _ = header.run_transport(
        parsed(PRIVATE + b"\r\n", status=b"403 Refused", body=PRIVATE), telemetry=records.append
    )
    assert error[0] == "plan_permission_refused" and not codes(records) and response.reads == 0


@pytest.mark.parametrize("version,expected", [
    (20, "response_http_other"), (True, "response_http_unavailable"),
    (header.Opaque(), "response_http_unavailable"),
])
def test_version_values_are_never_coerced_or_echoed(version, expected):
    response = parsed(b"Content-Type: text/event-stream\r\n")
    response.response.version = version
    records = []
    result, error, _, _, _ = header.run_transport(response, telemetry=records.append)
    assert result == [header._FIXTURE.COMPLETE] and error is None
    assert codes(records)["responses_http_version"] == expected
    header.assert_content_free(records)


@pytest.mark.parametrize("defects,expected", [
    ([RuntimeError(PRIVATE.decode())], "response_header_parse_other_defect"),
    (header.Opaque(), "response_header_parse_unavailable"),
])
def test_defect_values_are_never_rendered_or_used_as_authority(defects, expected):
    response = parsed(b"Content-Type: text/event-stream\r\n")
    response.response.headers.defects = defects
    records = []
    result, error, _, _, _ = header.run_transport(response, telemetry=records.append)
    assert result == [header._FIXTURE.COMPLETE] and error is None
    assert codes(records)["responses_header_parse"] == expected
    assert PRIVATE.decode() not in repr(records)


@pytest.mark.parametrize("field,phase,value,expected", [
    ("Content-Length", "responses_content_length", header.Opaque(), "response_length_invalid"),
    ("Content-Length", "responses_content_length", header.StringSubclass("1"),
     "response_length_invalid"),
    ("Content-Length", "responses_content_length", "\u0661", "response_length_invalid"),
    ("Transfer-Encoding", "responses_transfer_encoding", header.Opaque(),
     "response_transfer_invalid"),
    ("Transfer-Encoding", "responses_transfer_encoding", header.StringSubclass("chunked"),
     "response_transfer_invalid"),
])
def test_non_plain_header_values_are_not_stringified(field, phase, value, expected):
    response = parsed(b"Content-Type: text/event-stream\r\n")
    response.response.headers[field] = value
    records = []
    result, error, _, _, _ = header.run_transport(response, telemetry=records.append)
    assert result == [header._FIXTURE.COMPLETE] and error is None
    assert codes(records)[phase] == expected
    header.assert_content_free(records)
