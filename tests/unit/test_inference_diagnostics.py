"""Content-free observations through injected HTTPS/session seams; no real I/O."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from threading import Event

import pytest
from inference_service import providers, siwc_session
from inference_service.diagnostics import (
    DIAGNOSTIC_CODES,
    DIAGNOSTIC_PHASES,
    DIAGNOSTIC_STATUSES,
    emit_diagnostic,
)
from inference_service.http_transport import PLAN_TRANSPORT_ERROR_CODES, PlanTransportError
from inference_service.oauth_http import ModelCatalog, ModelChoice, SiwcHttpsClient
from inference_service.siwc_contracts import DIRECT_SCOPE, SiwcCredentials, SiwcError
from inference_service.siwc_session import SiwcSession

from shared.model_inference import InferenceMessage, InferenceRequest

_SPEC = importlib.util.spec_from_file_location(
    "_inference_diagnostics_transport_fixtures",
    Path(__file__).with_name("test_siwc_http_transport.py"),
)
_FIXTURE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_FIXTURE)
_HOST = "urn:uuid:12345678-1234-4234-8234-123456789abc"
_SECRET = "PRIVATE-CONTENT-CREDENTIAL-URL-IDENTITY"
_KEYS = {"schema_version", "phase", "status", "code", "http_status"}


def assert_records(records):
    assert records
    for record in records:
        assert type(record) is dict and set(record) == _KEYS
        assert record["schema_version"] == "jarvis-inference-diagnostic-v1"
        assert record["phase"] in DIAGNOSTIC_PHASES
        assert record["status"] in DIAGNOSTIC_STATUSES
        assert record["code"] is None or record["code"] in DIAGNOSTIC_CODES
        status = record["http_status"]
        assert status is None or type(status) is int and 100 <= status <= 599
    encoded = repr(records)
    for withheld in (_SECRET, _FIXTURE.TOKEN, "account-model", "response-synthetic", "Olá"):
        assert withheld not in encoded


def session_fixture():
    session = SiwcSession(host_id=_HOST, client=SiwcHttpsClient(), wall_clock=lambda: 1000)
    session._credentials = SiwcCredentials(
        "oaiapp_synthetic", _HOST, "synthetic.subject", "synthetic.access",
        "synthetic.refresh", "synthetic.id", (DIRECT_SCOPE,), 2000, 1000,
    )
    session._catalog = ModelCatalog((ModelChoice("account-model", "Synthetic"),))
    return session


def infer_fixture(response=None, *, telemetry=None, cancellation=None):
    response = response or _FIXTURE.Response([_FIXTURE.sse()])
    connection = _FIXTURE.Connection(response)
    calls = []

    def factory(*args, **kwargs):
        calls.append((args, kwargs))
        return connection

    session = session_fixture()
    provider = session.provider("account-model", authorized=True, connection_factory=factory,
                                telemetry=telemetry)
    assert not calls and not connection.calls and response.reads == 0
    request = InferenceRequest("synthetic-request", "account-model",
                               (InferenceMessage("user", _SECRET),), timeout_seconds=10)
    result = provider.infer(request, cancellation=cancellation)
    return result, session, connection, response, calls


@pytest.mark.parametrize("phase", sorted(DIAGNOSTIC_PHASES))
@pytest.mark.parametrize("status", sorted(DIAGNOSTIC_STATUSES))
def test_schema_accepts_only_fixed_metadata(phase, status):
    records = []
    emit_diagnostic(records.append, phase=phase, status=status)
    assert records == [{"schema_version": "jarvis-inference-diagnostic-v1", "phase": phase,
                        "status": status, "code": None, "http_status": None}]


@pytest.mark.parametrize("code", sorted(DIAGNOSTIC_CODES))
def test_literal_codes_round_trip(code):
    records = []
    emit_diagnostic(records.append, phase="provider_result", status="failed", code=code)
    assert records[0]["code"] == code
    assert_records(records)


@pytest.mark.parametrize("code", [_SECRET, "arbitrary_valid_identifier", "", 3, True,
                                  [], {}, object(), RuntimeError(_SECRET)])
def test_unknown_codes_are_withheld_without_inspecting_objects(code):
    records = []
    emit_diagnostic(records.append, phase="provider_result", status="failed", code=code)
    assert records[0]["code"] == "diagnostic_code_withheld"
    assert_records(records)


@pytest.mark.parametrize("value", [None, _SECRET, "", [], {}, True, 5])
@pytest.mark.parametrize("field", ["phase", "status"])
def test_invalid_phase_or_status_drops_record(value, field):
    records = []
    options = {"phase": "provider_result", "status": "failed"}
    options[field] = value
    emit_diagnostic(records.append, **options, code=_SECRET, http_status=401)
    assert records == []


@pytest.mark.parametrize("status", [None, 99, 600, -1, True, False, "401", 401.0, [], {}])
def test_http_status_rejects_non_exact_integer_and_range(status):
    records = []
    emit_diagnostic(records.append, phase="responses_http", status="observed", http_status=status)
    assert records[0]["http_status"] is None


@pytest.mark.parametrize("status", [100, 200, 401, 403, 429, 503, 599])
def test_http_status_exact_integer(status):
    records = []
    emit_diagnostic(records.append, phase="responses_http", status="observed", http_status=status)
    assert records[0]["http_status"] == status


def test_str_and_integer_subclasses_cannot_smuggle_labels():
    class Label(str):
        pass

    class Number(int):
        pass

    records = []
    emit_diagnostic(records.append, phase=Label("catalog"), status="completed")
    emit_diagnostic(records.append, phase="catalog", status=Label("completed"))
    assert not records
    emit_diagnostic(records.append, phase="catalog", status="failed",
                    code=Label("timeout"), http_status=Number(401))
    assert records[0]["code"] == "diagnostic_code_withheld"
    assert records[0]["http_status"] is None


def test_observer_exception_is_swallowed_and_no_repr_str_is_read(capsys):
    class Opaque:
        def __str__(self):
            raise AssertionError("must not stringify")

        def __repr__(self):
            raise AssertionError("must not render")

    def sink(record):
        assert record["code"] == "diagnostic_code_withheld"
        raise RuntimeError(_SECRET)

    emit_diagnostic(sink, phase="catalog", status="failed", code=Opaque(), http_status=Opaque())
    for sink in (None, False, {}, Opaque()):
        emit_diagnostic(sink, phase="catalog", status="failed")
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


def test_records_are_fresh_and_sink_mutation_does_not_contaminate_next_record():
    originals, snapshots = [], []

    def sink(record):
        originals.append(record)
        snapshots.append(dict(record))
        record.update(schema_version=_SECRET, content=_SECRET)

    for _ in range(2):
        emit_diagnostic(sink, phase="catalog", status="completed")
    assert originals[0] is not originals[1]
    assert_records(snapshots)


def test_literal_allowlist_covers_existing_transport_and_parser_errors():
    assert PLAN_TRANSPORT_ERROR_CODES <= DIAGNOSTIC_CODES
    assert providers._KNOWN_ERRORS <= DIAGNOSTIC_CODES
    tree = ast.parse(Path(providers.__file__).read_text(encoding="utf-8"))
    codes = {node.args[0].value for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == "_Failure" and node.args
             and isinstance(node.args[0], ast.Constant) and type(node.args[0].value) is str}
    assert codes <= DIAGNOSTIC_CODES


def test_transport_constructor_and_lazy_iterator_do_not_emit_or_connect():
    records = []
    transport, connection, response, calls = _FIXTURE.fixture(telemetry=records.append)
    stream = transport(_FIXTURE.PAYLOAD, timeout_seconds=10, cancellation=Event())
    assert not records and not calls and not connection.calls and not response.reads
    stream.close()
    assert not records and not calls


@pytest.mark.parametrize("sink", [False, True, 3, "callback", {}, []])
def test_transport_invalid_sink_refuses_inertly(sink):
    with pytest.raises(ValueError, match="^invalid_telemetry$"):
        _FIXTURE.fixture(telemetry=sink)


@pytest.mark.parametrize("sink", [False, True, 3, "callback", {}, []])
def test_session_invalid_sink_refuses_before_inference(sink):
    session = session_fixture()
    with pytest.raises(SiwcError, match="^siwc_session_input_invalid$"):
        session.provider("account-model", authorized=True, telemetry=sink)


@pytest.mark.parametrize("status,code", [(401, "plan_authentication_refused"),
    (403, "plan_permission_refused"), (429, "plan_usage_limited"),
    (503, "http_request_refused"), (302, "http_request_refused")])
def test_http_refusals_observe_status_without_reading_error_body(status, code):
    records = []
    response = _FIXTURE.Response([_SECRET.encode()], status=status)
    result, session, connection, response, calls = infer_fixture(response, telemetry=records.append)
    assert result.status == "failed" and result.error_code == code and result.text == ""
    assert result.evidence_mode == "injected_transport"
    assert response.reads == 0 and response.closed and connection.closed and len(calls) == 1
    assert [(r["phase"], r["status"]) for r in records] == [
        ("responses_request", "completed"), ("responses_http", "observed"),
        ("responses_stream", "failed"), ("provider_result", "failed")]
    assert records[1]["http_status"] == status
    assert records[-1]["code"] == code
    assert session.metadata()["authority"] == "none"
    assert_records(records)


def test_success_observes_clean_eof_without_promoting_authority_or_live_evidence():
    records = []
    result, session, connection, response, calls = infer_fixture(telemetry=records.append)
    assert result.status == "completed" and result.text == "Olá"
    assert result.evidence_mode == "injected_transport" and result.provider_id == "responses_plan"
    assert len(calls) == 1 and response.reads == 2 and response.closed and connection.closed
    assert [(r["phase"], r["status"]) for r in records] == [
        ("responses_request", "completed"), ("responses_http", "observed"),
        ("responses_stream", "completed"), ("provider_result", "completed")]
    assert session.metadata()["operator_authenticated"] is False
    assert_records(records)


@pytest.mark.parametrize("broken,code", [
    ({"type": "response.unknown", "content": _SECRET}, "unsupported_event"),
    ({"type": "response.output_text.delta", "delta": 4}, "malformed_delta"),
    ({"type": "error", "error": {"code": _SECRET}}, "provider_error"),
])
def test_parser_errors_withhold_partial_text_and_only_relay_fixed_code(broken, code):
    records = []
    partial = {"type": "response.output_text.delta", "delta": _SECRET}
    response = _FIXTURE.Response([_FIXTURE.sse(partial), _FIXTURE.sse(broken)])
    result, _, connection, response, calls = infer_fixture(response, telemetry=records.append)
    assert result.status == "failed" and result.error_code == code and result.text == ""
    assert records[-1]["phase"] == "provider_result" and records[-1]["code"] == code
    assert len(calls) == 1 and response.closed and connection.closed
    assert_records(records)


@pytest.mark.parametrize("chunk,code", [(b"data: {bad json}\n\n", "malformed_sse_event"),
    (b"data: [DONE]\n\n", "ambiguous_stream_terminal"),
    (RuntimeError(_SECRET), "transport_error"), (TimeoutError(_SECRET), "timeout")])
def test_framing_and_io_failures_do_not_echo_bodies_or_exception_text(chunk, code):
    records = []
    result, _, connection, response, calls = infer_fixture(
        _FIXTURE.Response([chunk]), telemetry=records.append)
    assert result.error_code == code and result.text == ""
    assert records[-2]["phase"] == "responses_stream" and records[-2]["code"] == code
    assert records[-1]["code"] == code
    assert len(calls) == 1 and response.closed and connection.closed
    assert_records(records)


def test_eager_payload_refusal_observes_no_content_and_has_zero_io():
    records = []
    transport, connection, response, calls = _FIXTURE.fixture(telemetry=records.append)
    with pytest.raises(PlanTransportError, match="^unsupported_request_field$"):
        _FIXTURE.collect(transport, payload={**_FIXTURE.PAYLOAD, _SECRET: _SECRET})
    assert not calls and not connection.calls and not response.reads
    assert records[0]["phase"] == "responses_request"
    assert records[0]["code"] == "unsupported_request_field"
    assert_records(records)


@pytest.mark.parametrize("phase", ["responses_request", "responses_http", "responses_stream"])
@pytest.mark.parametrize("mutation,code", [("cancel", "cancelled"), ("deadline", "timeout"),
                                        ("expiry", "credential_expired")])
def test_observer_mutations_are_fenced_before_next_io_or_completion(phase, mutation, code):
    records, cancellation, clock, wall = [], Event(), [1.0], [1000.0]

    def sink(record):
        records.append(record)
        if record["phase"] == phase and record["status"] in {"completed", "observed"}:
            if mutation == "cancel":
                cancellation.set()
            elif mutation == "deadline":
                clock[0] = 11.0
            else:
                wall[0] = 2000.0

    transport, connection, response, calls = _FIXTURE.fixture(
        telemetry=sink, clock=lambda: clock[0], wall_clock=lambda: wall[0])
    with pytest.raises(PlanTransportError, match="^" + code + "$"):
        _FIXTURE.collect(transport, cancellation=cancellation)
    assert len(calls) == 1 and connection.closed
    assert response.reads == (2 if phase == "responses_stream" else 0)
    assert response.closed is (phase != "responses_request")
    if phase == "responses_request":
        assert "getresponse" not in connection.calls
    assert records[-1]["code"] == code
    assert_records(records)


def test_provider_relay_exception_does_not_change_result_or_write_logs(capsys):
    baseline = infer_fixture()[0]

    def sink(record):
        raise RuntimeError(_SECRET)

    observed = infer_fixture(telemetry=sink)[0]
    assert observed == baseline
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


@pytest.mark.parametrize("enabled", [False, True])
def test_none_compatibility_and_relay_ignore_all_extra_provider_fields(monkeypatch, enabled):
    captured, records = {}, []

    def transport(**kwargs):
        captured["transport"] = kwargs
        return object()

    def provider(fenced_transport, **kwargs):
        captured["provider"] = kwargs
        return "inert-provider"

    monkeypatch.setattr(siwc_session, "PlanResponsesHttpsTransport", transport)
    monkeypatch.setattr(siwc_session, "ResponsesPlanInferenceProvider", provider)
    sink = records.append if enabled else None
    result = session_fixture().provider("account-model", authorized=True, telemetry=sink)
    assert result == "inert-provider" and not records
    if not enabled:
        assert "telemetry" not in captured["transport"] and not captured["provider"]
        return
    assert captured["transport"]["telemetry"] == sink
    relay = captured["provider"]["telemetry"]
    relay({"status": "failed", "error_code": _SECRET, "event_count": 9,
           "input_tokens": 99, "request_id": _SECRET, "evidence_mode": "live", "body": _SECRET})
    assert records[0]["phase"] == "provider_result"
    assert records[0]["code"] == "diagnostic_code_withheld"
    relay({"status": _SECRET, "error_code": "timeout"})
    relay([_SECRET])
    assert len(records) == 1
    assert_records(records)
