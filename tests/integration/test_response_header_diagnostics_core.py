"""Fixed header categories over owned TLS, sovereign Core and persisted SQLite.

Only synthetic credentials and local TLS peers are used. Header diagnostics
cannot authorize a parser, read a refused body or promote injected evidence.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from threading import Event

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "jarvis_header_diagnostic_core_fixture",
    Path(__file__).with_name("test_inference_diagnostics_core.py"),
)
diagnostic = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(diagnostic)
PRIVATE_PARAMETER = b"PRIVATE_HEADER_PARAMETER_NEVER_PUBLISHED"
PRIVATE_ENCODING = b"PRIVATE_ENCODING_VALUE_NEVER_PUBLISHED"
PRIVATE_BODY = b"PRIVATE_REFUSED_BODY_NEVER_PUBLISHED"
HEADER_PHASES = ("responses_media_type", "responses_content_encoding")


def _exercise_headers(
    tmp_path, monkeypatch, *, media=b"text/event-stream", encoding=b"identity",
    accepted=False, cancel_phase=None, http_refusal=False, telemetry=True,
    malformed_prefix=False,
):
    """Reuse real collaborators while changing only owned server header bytes."""
    body = diagnostic.large._model_wire().split(b"\r\n\r\n", 1)[1]
    if not accepted or http_refusal:
        body = PRIVATE_BODY
    headers = [(b"Content-Length", str(len(body)).encode()), (b"Connection", b"close")]
    if media is not None:
        headers.append((b"Content-Type", media))
    if encoding is not None:
        headers.append((b"Content-Encoding", encoding))
    wire = diagnostic.tls.response(
        body, status=b"403 Owned refusal" if http_refusal else b"200 OK", headers=headers,
    )
    if malformed_prefix:
        status_line, rest = wire.split(b"\r\n", 1)
        wire = status_line + b"\r\n" + PRIVATE_PARAMETER + b"\r\n" + rest
    monkeypatch.setattr(diagnostic, "_model_payload", lambda _mode: wire)
    observed = []
    original_response = diagnostic.large._ObservedResponse

    class ObservedHeaders(original_response):
        def __init__(self, response, broken):
            super().__init__(response, broken)
            self.header_reads = []
            observed.append(self)

        def getheader(self, name, default=None):
            self.header_reads.append(name.lower())
            return self.response.getheader(name, default)

        def read(self, *args, **kwargs):
            chunk = self.response.read(*args, **kwargs)
            self.bytes_read += len(chunk)
            return chunk

    monkeypatch.setattr(diagnostic.large, "_ObservedResponse", ObservedHeaders)
    cancellation = Event()
    monkeypatch.setattr(diagnostic, "Event", lambda: cancellation)
    original_port = diagnostic.SessionInferencePort

    def port_factory(*args, **kwargs):
        sink = kwargs["telemetry"]
        if sink is not None and cancel_phase is not None:
            def cancel_observer(record):
                sink(record)
                if record["phase"] == cancel_phase:
                    cancellation.set()
            kwargs["telemetry"] = cancel_observer
        return original_port(*args, **kwargs)

    monkeypatch.setattr(diagnostic, "SessionInferencePort", port_factory)
    composed_results = []
    original_configure = diagnostic.fixture._configure

    def capture_configuration(*args, **kwargs):
        inputs, results = original_configure(*args, **kwargs)
        composed_results.append(results)
        return inputs, results

    monkeypatch.setattr(diagnostic.fixture, "_configure", capture_configuration)
    records, final = diagnostic._run_case(
        tmp_path, monkeypatch, mode="http_403" if http_refusal else "header_corpus",
        expected="accepted" if accepted and cancel_phase is None else "rejected",
        telemetry=telemetry,
    )
    assert len(composed_results) == 1 and len(composed_results[0]) == 1
    synthesis_result = composed_results[0][0]
    if accepted and cancel_phase is None and not http_refusal:
        assert synthesis_result.generative_error_code is None
        assert synthesis_result.generative_evidence_mode == "injected_transport"
    else:
        assert synthesis_result.generative_error_code == (
            "cancelled" if cancel_phase is not None else "inference_failed"
        )
        assert synthesis_result.generative_evidence_mode is None
    assert len(observed) == 2
    model_response = observed[1]
    assert model_response.closed
    if not accepted or cancel_phase is not None or http_refusal:
        assert model_response.bytes_read == 0
    else:
        assert model_response.bytes_read == len(body)
    encoded = json.dumps(records, ensure_ascii=False)
    for private in (PRIVATE_PARAMETER, PRIVATE_ENCODING, PRIVATE_BODY):
        assert private.decode() not in encoded and private.decode() not in final
    categories = [record for record in records if record["phase"] in HEADER_PHASES]
    for record in categories:
        assert record == {
            "schema_version": "jarvis-inference-diagnostic-v1",
            "phase": record["phase"], "status": "observed",
            "code": record["code"], "http_status": None,
        }
    if http_refusal:
        assert model_response.header_reads == [] and categories == []
        assert any(record["code"] == "plan_permission_refused" for record in records)
    elif telemetry:
        assert any(record["phase"] == "responses_http" and record["http_status"] == 200
                   for record in records)
        if not accepted and cancel_phase is None:
            assert any(record["code"] == "unsupported_response_encoding" for record in records)
    else:
        assert records == [] and categories == []
    return categories, records, model_response


@pytest.mark.parametrize("media,code", [
    (b"application/json; private=" + PRIVATE_PARAMETER, "response_media_type_json"),
    (b"text/html; private=" + PRIVATE_PARAMETER, "response_media_type_html"),
    (None, "response_media_type_missing"),
    (b"application/x-" + PRIVATE_PARAMETER, "response_media_type_other"),
])
def test_non_sse_media_categories_refuse_before_body_and_preserve_native_restart(
    tmp_path, monkeypatch, media, code,
):
    categories, _, response = _exercise_headers(tmp_path, monkeypatch, media=media)
    assert [(record["phase"], record["code"]) for record in categories] == [
        ("responses_media_type", code),
        ("responses_content_encoding", "response_encoding_identity"),
    ]
    assert response.header_reads == ["content-type", "content-encoding"]


@pytest.mark.parametrize("encoding,code", [
    (b"gzip", "response_encoding_gzip"),
    (b"deflate", "response_encoding_deflate"),
    (b"br", "response_encoding_br"),
    (PRIVATE_ENCODING, "response_encoding_other"),
])
def test_compressed_or_unknown_encoding_refuses_without_decompression_or_body_read(
    tmp_path, monkeypatch, encoding, code,
):
    categories, _, response = _exercise_headers(tmp_path, monkeypatch, encoding=encoding)
    assert [(record["phase"], record["code"]) for record in categories] == [
        ("responses_media_type", "response_media_type_sse"),
        ("responses_content_encoding", code),
    ]
    assert response.header_reads == ["content-type", "content-encoding"]


@pytest.mark.parametrize("encoding", [b"identity", None, b""])
def test_identity_or_missing_encoding_preserves_accepted_injected_final_and_restart(
    tmp_path, monkeypatch, encoding,
):
    categories, _, response = _exercise_headers(
        tmp_path, monkeypatch, encoding=encoding,
        media=b" Text/Event-Stream ; private=" + PRIVATE_PARAMETER, accepted=True,
    )
    assert [(record["phase"], record["code"]) for record in categories] == [
        ("responses_media_type", "response_media_type_sse"),
        ("responses_content_encoding", "response_encoding_identity"),
    ]
    assert response.header_reads == ["content-type", "content-encoding"]


def test_http_refusal_never_reads_headers_or_body_and_preserves_native_restart(
    tmp_path, monkeypatch,
):
    _exercise_headers(tmp_path, monkeypatch, http_refusal=True)


@pytest.mark.parametrize("phase", HEADER_PHASES)
def test_header_observer_cancellation_prevents_body_and_preserves_native_restart(
    tmp_path, monkeypatch, phase,
):
    categories, records, _ = _exercise_headers(
        tmp_path, monkeypatch, accepted=True, cancel_phase=phase,
    )
    assert [record["phase"] for record in categories] == (
        ["responses_media_type"] if phase == "responses_media_type" else list(HEADER_PHASES)
    )
    assert any(record["code"] == "cancelled" for record in records)
    assert not any(record["phase"] == "responses_stream" and record["status"] == "completed"
                   for record in records)


@pytest.mark.parametrize("accepted", [True, False])
def test_header_diagnostics_default_off_preserves_existing_tls_core_behavior(
    tmp_path, monkeypatch, accepted,
):
    _exercise_headers(tmp_path, monkeypatch, accepted=accepted, telemetry=False,
                      media=b"text/event-stream" if accepted else b"application/json")


@pytest.mark.parametrize("media,malformed,parse,presence,count,length", [
    (None, False, "clean", "absent", "present", "nonzero"),
    (b"", False, "clean", "present", "present", "nonzero"),
    (b"text/event-stream", True, "missing_separator", "absent", "empty", "absent"),
])
def test_parsed_header_diagnosis_through_tls_core_memory_and_restart(
    tmp_path, monkeypatch, media, malformed, parse, presence, count, length,
):
    _, records, response = _exercise_headers(
        tmp_path, monkeypatch, media=media, malformed_prefix=malformed,
    )
    observed = {record["phase"]: record["code"] for record in records}
    assert observed["responses_http_version"] == "response_http_1_1"
    assert observed["responses_header_parse"] == "response_header_parse_" + parse
    assert observed["responses_media_presence"] == "response_media_" + presence
    assert observed["responses_header_count"] == "response_headers_" + count
    assert observed["responses_content_length"] == "response_length_" + length
    assert observed["responses_transfer_encoding"] == "response_transfer_absent"
    assert response.bytes_read == 0


@pytest.mark.parametrize("phase", [
    "responses_http_version", "responses_header_count", "responses_header_parse",
    "responses_media_presence", "responses_content_length", "responses_transfer_encoding",
])
def test_parsed_metadata_cancellation_preserves_native_final_and_restart(
    tmp_path, monkeypatch, phase,
):
    _, records, response = _exercise_headers(
        tmp_path, monkeypatch, accepted=True, cancel_phase=phase,
    )
    assert any(record["phase"] == phase for record in records)
    assert any(record["code"] == "cancelled" for record in records)
    assert response.bytes_read == 0
    assert not any(record["phase"] == "responses_stream" and record["status"] == "completed"
                   for record in records)
