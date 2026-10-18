"""Fixed header categories through an injected socket; no account or network I/O."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from threading import Event

import pytest
from inference_service.http_transport import PlanTransportError

_SPEC = importlib.util.spec_from_file_location(
    "_response_header_transport_fixtures",
    Path(__file__).with_name("test_siwc_http_transport.py"),
)
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)
_SECRET = "PRIVATE-HEADER-ACCOUNT-URL-CREDENTIAL-CONTENT"
_MEDIA_PHASE = "responses_media_type"
_ENCODING_PHASE = "responses_content_encoding"
_KEYS = {"schema_version", "phase", "status", "code", "http_status"}


class Opaque:
    def __str__(self):
        raise AssertionError("must not stringify header")

    def __repr__(self):
        raise AssertionError("must not render header")

    def __eq__(self, other):
        raise AssertionError("must not compare header")


class StringSubclass(str):
    def split(self, *args, **kwargs):
        raise AssertionError("must not normalize a string subclass")

    def strip(self, *args, **kwargs):
        raise AssertionError("must not normalize a string subclass")


class HeaderResponse(_FIXTURE.Response):
    def __init__(self, headers, *, status=200, chunks=None):
        super().__init__([_FIXTURE.sse()] if chunks is None else chunks, status=status)
        self.headers = headers
        self.header_calls = []

    def getheader(self, key, default):
        self.header_calls.append((key, default))
        return self.headers.get(key, default)


def header_records(records):
    return [record for record in records if record["phase"] in {_MEDIA_PHASE, _ENCODING_PHASE}]


def expected_record(phase, code):
    return {
        "schema_version": "jarvis-inference-diagnostic-v1",
        "phase": phase,
        "status": "observed",
        "code": code,
        "http_status": None,
    }


def assert_content_free(records):
    assert records
    for record in records:
        assert type(record) is dict and set(record) == _KEYS
        assert record["schema_version"] == "jarvis-inference-diagnostic-v1"
    rendered = repr(records)
    for value in (_SECRET, _FIXTURE.TOKEN, "account-model", "response-synthetic", "Olá"):
        assert value not in rendered


def run_transport(response, *, telemetry=None, **options):
    transport, connection, response, calls = _FIXTURE.fixture(
        response=response, telemetry=telemetry, **options
    )
    try:
        result = _FIXTURE.collect(transport)
        error = None
    except PlanTransportError as failure:
        result = None
        error = (failure.code, failure.status, str(failure))
    return result, error, connection, response, calls


@pytest.mark.parametrize(
    "value,code,accepted",
    [
        ("text/event-stream", "response_media_type_sse", True),
        (" TEXT/EVENT-STREAM ; charset=utf-8", "response_media_type_sse", True),
        ("text/event-stream; account=" + _SECRET, "response_media_type_sse", True),
        ("application/json", "response_media_type_json", False),
        (" APPLICATION/JSON ; detail=" + _SECRET, "response_media_type_json", False),
        ("text/html", "response_media_type_html", False),
        (" TEXT/HTML; url=" + _SECRET, "response_media_type_html", False),
        ("", "response_media_type_missing", False),
        (" \t ; detail=" + _SECRET, "response_media_type_missing", False),
        ("application/problem+json", "response_media_type_other", False),
        (_SECRET, "response_media_type_other", False),
        ("text/event-stream, application/json", "response_media_type_other", False),
        (None, "response_media_type_invalid", False),
        (b"text/event-stream", "response_media_type_invalid", False),
        (True, "response_media_type_invalid", False),
        (3, "response_media_type_invalid", False),
        ([], "response_media_type_invalid", False),
        ({}, "response_media_type_invalid", False),
        (Opaque(), "response_media_type_invalid", False),
        (StringSubclass("text/event-stream"), "response_media_type_invalid", False),
    ],
    ids=[f"media-{number}" for number in range(20)],
)
def test_media_categories_preserve_strict_framing_acceptance(value, code, accepted):
    records = []
    response = HeaderResponse({"Content-Type": value, "Content-Encoding": "identity"})
    result, error, connection, response, calls = run_transport(response, telemetry=records.append)
    assert header_records(records) == [
        expected_record(_MEDIA_PHASE, code),
        expected_record(_ENCODING_PHASE, "response_encoding_identity"),
    ]
    assert result == ([_FIXTURE.COMPLETE] if accepted else None)
    assert error == (None if accepted else (
        "unsupported_response_encoding", "failed", "unsupported_response_encoding"
    ))
    assert response.reads == (2 if accepted else 0)
    assert len(calls) == 1 and response.closed and connection.closed
    assert_content_free(records)


@pytest.mark.parametrize(
    "value,code,accepted",
    [
        ("identity", "response_encoding_identity", True),
        (" IDENTITY \t", "response_encoding_identity", True),
        ("", "response_encoding_identity", True),
        (" \t", "response_encoding_identity", True),
        ("gzip", "response_encoding_gzip", False),
        (" GZIP \t", "response_encoding_gzip", False),
        ("deflate", "response_encoding_deflate", False),
        (" DEFLATE ", "response_encoding_deflate", False),
        ("br", "response_encoding_br", False),
        (" BR ", "response_encoding_br", False),
        ("gzip, br", "response_encoding_other", False),
        ("gzip; credential=" + _SECRET, "response_encoding_other", False),
        (_SECRET, "response_encoding_other", False),
        (None, "response_encoding_invalid", False),
        (b"identity", "response_encoding_invalid", False),
        (False, "response_encoding_invalid", False),
        (3.0, "response_encoding_invalid", False),
        ([], "response_encoding_invalid", False),
        ({}, "response_encoding_invalid", False),
        (Opaque(), "response_encoding_invalid", False),
        (StringSubclass("identity"), "response_encoding_invalid", False),
    ],
    ids=[f"encoding-{number}" for number in range(21)],
)
def test_encoding_categories_never_enable_decompression(value, code, accepted):
    records = []
    response = HeaderResponse({"Content-Type": "text/event-stream", "Content-Encoding": value})
    result, error, connection, response, calls = run_transport(response, telemetry=records.append)
    assert header_records(records) == [
        expected_record(_MEDIA_PHASE, "response_media_type_sse"),
        expected_record(_ENCODING_PHASE, code),
    ]
    assert result == ([_FIXTURE.COMPLETE] if accepted else None)
    assert error == (None if accepted else (
        "unsupported_response_encoding", "failed", "unsupported_response_encoding"
    ))
    assert response.reads == (2 if accepted else 0)
    assert len(calls) == 1 and response.closed and connection.closed
    assert_content_free(records)


@pytest.mark.parametrize(
    "headers,media,encoding,accepted",
    [
        ({}, "response_media_type_missing", "response_encoding_identity", False),
        ({"Content-Type": "text/event-stream"},
         "response_media_type_sse", "response_encoding_identity", True),
        ({"Content-Type": "text/html", "Content-Encoding": "gzip"},
         "response_media_type_html", "response_encoding_gzip", False),
        ({"Content-Type": None, "Content-Encoding": None},
         "response_media_type_invalid", "response_encoding_invalid", False),
    ],
)
def test_absent_defaults_and_both_refusal_causes_are_observed(headers, media, encoding, accepted):
    records = []
    result, error, connection, response, calls = run_transport(
        HeaderResponse(headers), telemetry=records.append
    )
    assert header_records(records) == [
        expected_record(_MEDIA_PHASE, media), expected_record(_ENCODING_PHASE, encoding)
    ]
    assert response.header_calls == [("Content-Type", ""), ("Content-Encoding", "identity")]
    assert (error is None) is accepted
    assert result == ([_FIXTURE.COMPLETE] if accepted else None)
    assert response.reads == (2 if accepted else 0)
    assert len(calls) == 1 and response.closed and connection.closed
    assert_content_free(records)


@pytest.mark.parametrize("status", [302, 401, 403, 429, 503])
def test_non_200_refusals_do_not_inspect_headers_or_body(status):
    records = []
    result, error, connection, response, calls = run_transport(
        HeaderResponse({"Content-Type": Opaque(), "Content-Encoding": Opaque()},
                       status=status, chunks=[_SECRET.encode()]),
        telemetry=records.append,
    )
    assert result is None and error is not None
    assert not header_records(records) and not response.header_calls and response.reads == 0
    assert len(calls) == 1 and response.closed and connection.closed
    assert_content_free(records)


@pytest.mark.parametrize("phase", [_MEDIA_PHASE, _ENCODING_PHASE])
@pytest.mark.parametrize("mutation,code", [
    ("cancel", "cancelled"), ("deadline", "timeout"), ("expiry", "credential_expired")
])
def test_new_observer_boundaries_fence_reads_and_next_observation(phase, mutation, code):
    records, cancellation, clock, wall = [], Event(), [1.0], [1000.0]

    def sink(record):
        records.append(dict(record))
        if record["phase"] == phase:
            if mutation == "cancel":
                cancellation.set()
            elif mutation == "deadline":
                clock[0] = 11.0
            else:
                wall[0] = 2000.0

    transport, connection, response, calls = _FIXTURE.fixture(
        response=HeaderResponse({"Content-Type": "text/event-stream"}),
        telemetry=sink, clock=lambda: clock[0], wall_clock=lambda: wall[0],
    )
    with pytest.raises(PlanTransportError, match="^" + code + "$"):
        _FIXTURE.collect(transport, cancellation=cancellation)
    assert response.reads == 0 and response.closed and connection.closed and len(calls) == 1
    assert records[-1]["phase"] == "responses_stream" and records[-1]["code"] == code
    assert [record["phase"] for record in header_records(records)] == (
        [_MEDIA_PHASE] if phase == _MEDIA_PHASE else [_MEDIA_PHASE, _ENCODING_PHASE]
    )
    assert_content_free(records)


@pytest.mark.parametrize("mode", ["raise", "mutate"])
@pytest.mark.parametrize("accepted", [False, True])
def test_callback_errors_and_record_mutations_do_not_change_result(mode, accepted, capsys):
    headers = {"Content-Type": "text/event-stream" if accepted else "application/json"}
    baseline = run_transport(HeaderResponse(headers))
    records = []

    def sink(record):
        records.append(dict(record))
        if record["phase"] in {_MEDIA_PHASE, _ENCODING_PHASE}:
            if mode == "raise":
                raise RuntimeError(_SECRET)
            record.clear()
            record.update(content=_SECRET, phase=_SECRET, status="completed")

    observed = run_transport(HeaderResponse(headers), telemetry=sink)
    assert observed[:2] == baseline[:2]
    assert observed[3].reads == baseline[3].reads
    assert len(header_records(records)) == 2
    assert_content_free(records)
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


@pytest.mark.parametrize("headers", [
    {"Content-Type": "text/event-stream"},
    {"Content-Type": "application/json"},
    {"Content-Type": "text/event-stream", "Content-Encoding": "gzip"},
    {"Content-Type": None, "Content-Encoding": None},
])
def test_none_default_preserves_header_io_and_clock_budget(headers):
    clocks, wall_clocks = [], []

    def run(sink):
        clock_calls, wall_calls = [], []
        response = HeaderResponse(headers)
        result = run_transport(
            response, telemetry=sink,
            clock=lambda: clock_calls.append(1.0) or 1.0,
            wall_clock=lambda: wall_calls.append(1000.0) or 1000.0,
        )
        clocks.append(len(clock_calls))
        wall_clocks.append(len(wall_calls))
        return result

    legacy = run(None)
    records = []
    observed = run(records.append)
    assert legacy[:2] == observed[:2]
    assert legacy[3].header_calls == observed[3].header_calls
    assert legacy[3].reads == observed[3].reads
    accepted = legacy[1] is None
    # Existing opt-in EOF observation adds one check on successful framing.
    # Header and parsed framing categories add eight fenced observations.
    # The None path keeps its exact old budget.
    assert clocks[0] == (14 if accepted else 8)
    assert wall_clocks[0] == (13 if accepted else 7)
    extra_checks = 9 if accepted else 8
    assert clocks[1] == clocks[0] + extra_checks
    assert wall_clocks[1] == wall_clocks[0] + extra_checks
    assert legacy[2].calls[1] == observed[2].calls[1]
    assert len(legacy[4]) == len(observed[4]) == 1


@pytest.mark.parametrize("options,chunks,code", [
    ({"max_line_bytes": 4}, [b"data: long\n"], "line_limit_exceeded"),
    ({"max_event_bytes": 4}, [b": long\n"], "event_limit_exceeded"),
    ({"max_stream_bytes": 4}, [b": ok\n"], "stream_limit_exceeded"),
    ({"max_events": 1}, [_FIXTURE.sse(), _FIXTURE.sse()], "event_limit_exceeded"),
    ({}, [b"data: [DONE]\n\n"], "ambiguous_stream_terminal"),
])
def test_observations_do_not_relax_existing_stream_caps_or_terminal_rules(options, chunks, code):
    records = []
    result, error, connection, response, calls = run_transport(
        HeaderResponse({"Content-Type": "text/event-stream"}, chunks=chunks),
        telemetry=records.append, **options,
    )
    assert result is None and error == (code, "failed", code)
    assert len(header_records(records)) == 2
    assert len(calls) == 1 and response.closed and connection.closed
    assert_content_free(records)
