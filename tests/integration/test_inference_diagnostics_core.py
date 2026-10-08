"""Redacted opt-in inference diagnostics with owned TLS and actual Core/SQLite.

No human token/store, external account/model, refresh, LangGraph or live evidence.
Callbacks observe only; they cannot change canonical output or bypass fences.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import socket
import ssl
from pathlib import Path
from threading import Event

import pytest
from inference_service.diagnostics import (
    DIAGNOSTIC_CODES,
    DIAGNOSTIC_PHASES,
    DIAGNOSTIC_STATUSES,
)
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.session_inference_port import SessionInferencePort
from inference_service.siwc_contracts import REQUESTED_SCOPES, SiwcCredentials
from inference_service.siwc_session import SiwcSession

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.types import PermissionDecision

_SPEC = importlib.util.spec_from_file_location(
    "jarvis_diagnostic_core_tls_fixture",
    Path(__file__).with_name("test_large_catalog_core.py"),
)
large = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(large)
fixture, tls = large.fixture, large.tls
MODEL = large.MODEL
PRIVATE_ERROR_BODY = "PRIVATE_DIAGNOSTIC_HTTP_ERROR_BODY_NEVER_PUBLISHED"
PRIVATE_HEADER = "PRIVATE_DIAGNOSTIC_HTTP_HEADER_NEVER_PUBLISHED"
PRIVATE_SSE = "PRIVATE_DIAGNOSTIC_SSE_TEXT_NEVER_PUBLISHED"
CLIENT = "oaiapp_diagnostic_synthetic_client"
SUBJECT = "diagnostic-external-synthetic-subject"


def _model_payload(mode):
    if mode.startswith("http_"):
        status = int(mode.split("_", 1)[1])
        body = json.dumps({"error": {"message": PRIVATE_ERROR_BODY}}).encode()
        return tls.response(body, status=f"{status} Owned refusal".encode(), headers=[
            (b"Content-Type", b"application/json"),
            (b"Content-Length", str(len(body)).encode()),
            (b"X-Private-Sentinel", PRIVATE_HEADER.encode()),
            (b"Location", b"https://private.invalid/account"),
            (b"Connection", b"close"),
        ])
    if mode == "unsupported":
        event = {"type": "response.unsupported.private", "text": PRIVATE_SSE}
    elif mode == "incomplete":
        event = {"type": "response.incomplete", "response": {
            "id": "owned-incomplete", "model": MODEL, "status": "incomplete",
            "incomplete_details": {"reason": PRIVATE_SSE},
        }}
    elif mode == "sse_error":
        event = {"type": "error", "code": "subscription_sharing_usage_limit_exceeded",
                 "message": PRIVATE_SSE}
    elif mode == "sse_unknown_error":
        event = {"type": "error", "code": PRIVATE_SSE, "message": PRIVATE_SSE}
    else:
        return large._model_wire()
    return large._wire(("data: " + json.dumps(event) + "\r\n\r\n").encode(),
                       b"text/event-stream")


def _assert_redacted(records, root):
    assert 0 < len(records) <= 256
    for record in records:
        assert type(record) is dict
        assert set(record) == {"schema_version", "phase", "status", "code", "http_status"}
        assert record["schema_version"] == "jarvis-inference-diagnostic-v1"
        assert type(record["phase"]) is str and record["phase"] in DIAGNOSTIC_PHASES
        assert type(record["status"]) is str and record["status"] in DIAGNOSTIC_STATUSES
        assert (record["code"] is None or type(record["code"]) is str
                and record["code"] in DIAGNOSTIC_CODES)
        assert (record["http_status"] is None or type(record["http_status"]) is int
                and 100 <= record["http_status"] <= 599)
    encoded = json.dumps(records, ensure_ascii=False)
    for secret in (
        fixture.CREDENTIAL, "synthetic-refresh", "synthetic-id-token", CLIENT, SUBJECT,
        MODEL, fixture.QUERY, fixture.ANALYSIS, PRIVATE_ERROR_BODY, PRIVATE_HEADER, PRIVATE_SSE,
        str(root), "https://", "api.openai.com", "auth.openai.com", "Authorization",
        "Bearer", "profile-", "user://", "operator://", "generative-session",
    ):
        assert secret not in encoded


def _run_case(tmp_path, monkeypatch, *, mode="valid", callback="collect", telemetry=True,
              query=fixture.QUERY, decision=PermissionDecision.ALLOW, expected="accepted"):
    catalog_body = large._catalog(large.OLD_LIMIT + 1,
                                  "schema" if mode == "catalog_invalid" else "valid")
    catalog_dir, model_dir = tmp_path / "catalog-tls", tmp_path / "model-tls"
    catalog_dir.mkdir()
    model_dir.mkdir()
    original_connection = http.client.HTTPSConnection
    monkeypatch.setattr(tls, "TlsFixture", fixture._InferenceTlsFixture)
    records, calls, port_results = [], [], []
    token = Event()
    with (tls.tls_fixture(catalog_dir, large._wire(catalog_body, b"application/json"))
          as (catalog_server, catalog_client),
          tls.tls_fixture(model_dir, _model_payload(mode)) as (model_server, model_client)):

        class OwnedConnection(original_connection):
            def __init__(self, server, client, label):
                super().__init__(tls.HOSTNAME, timeout=30, context=client)
                self.server, self.client, self.label = server, client, label
                self.was_closed, self.observed_response = False, None

            def connect(self):
                raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                raw.settimeout(self.timeout)
                raw.connect(self.server.address)
                self.sock = self.client.wrap_socket(raw, server_hostname=tls.HOSTNAME)

            def getresponse(self):
                self.observed_response = large._ObservedResponse(super().getresponse(), False)
                return self.observed_response

            def close(self):
                super().close()
                self.was_closed = True
                if (mode == "cleanup" and self.label == "inference"
                        and self.observed_response is not None):
                    raise OSError(PRIVATE_HEADER)

        connections = {label: OwnedConnection(server, client, label) for label, server, client in (
            ("catalog", catalog_server, catalog_client), ("inference", model_server, model_client),
        )}

        def factory(label):
            def connect(host, *, port, timeout, context):
                assert host == "api.openai.com" and port == 443 and 0 < timeout <= 30
                assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
                calls.append(label)
                connection = connections[label]
                connection.timeout = timeout
                return connection
            return connect

        def forbidden(*_args, **_kwargs):
            pytest.fail("diagnostic test attempted external network/account operation")

        monkeypatch.setattr(http.client, "HTTPSConnection", forbidden)
        monkeypatch.setattr(socket, "getaddrinfo", forbidden)
        host = "urn:uuid:12345678-1234-4234-8234-123456789abc"
        session = SiwcSession(host_id=host, wall_clock=lambda: 1000,
                              client=SiwcHttpsClient(authorized=True,
                                                    connection_factory=factory("catalog")))
        session._credentials = SiwcCredentials(
            CLIENT, host, SUBJECT, fixture.CREDENTIAL, "synthetic-refresh", "synthetic-id-token",
            REQUESTED_SCOPES, 999 if mode == "expired" else 2000, 100,
        )
        for name in ("begin", "load", "refresh"):
            monkeypatch.setattr(session, name, forbidden)

        def sink(record):
            records.append(dict(record))
            if callback == "raise":
                raise RuntimeError(PRIVATE_SSE)
            if callback == "mutate_record":
                record.clear()
                record.update(status="completed", code=PRIVATE_ERROR_BODY)
            if (callback == "mutate_session" and record.get("phase") == "catalog"
                    and record.get("status") == "completed"):
                session._generation += 1
            if (callback == "cancel" and record.get("phase") == "catalog"
                    and record.get("status") == "completed"):
                token.set()

        port = SessionInferencePort(session, model=MODEL, authorized=True,
                                    connection_factory=factory("inference"),
                                    telemetry=sink if telemetry else None)
        infer = port.infer

        def capture(request, **kwargs):
            result = infer(request, **kwargs)
            port_results.append(result)
            return result

        monkeypatch.setattr(port, "infer", capture)
        assert port.evidence_mode == "injected_transport" and calls == [] and records == []
        runtime = tmp_path / "runtime"
        core = _isolated_core(runtime)
        inputs, results = fixture._configure(
            core, port, monkeypatch, generative_provider_id="responses_plan",
            generative_evidence_mode="injected_transport", generative_cancellation=token,
        )
        contract = fixture._contract(text=query)
        response = core.handle_input(contract)
        assert response.governance_decision.decision == decision
        assert len(results) == 1 and results[0].generative_status == expected, (
            results[0].generative_error_code, calls, records,
        )
        if expected == "withheld":
            assert calls == [] and records == [] and port_results == []
        elif mode == "expired":
            assert calls == [] and not catalog_server.accepted.is_set()
        elif mode == "catalog_invalid" or callback in {"mutate_session", "cancel"}:
            assert calls == ["catalog"]
        else:
            assert calls == ["catalog", "inference"]
        assert len(catalog_server.requests) == calls.count("catalog")
        assert len(model_server.requests) == calls.count("inference")
        if "inference" not in calls:
            assert not model_server.accepted.is_set()
        else:
            payload = json.loads(model_server.requests[0].split(b"\r\n\r\n", 1)[1])
            assert payload["model"] == MODEL and payload["store"] is False
            assert payload["stream"] is True
            prompt = json.loads(payload["input"][0]["content"])
            assert {source["text"] for source in prompt["sources"]} == {query}
            if mode.startswith("http_"):
                assert connections["inference"].observed_response.bytes_read == 0
        for label in calls:
            assert connections[label].was_closed and connections[label].observed_response.closed
        if expected == "accepted":
            assert results[0].generative_evidence_mode == "injected_transport"
            assert results[0].generative_error_code is None
            assert port_results[0].status == "completed"
            assert port_results[0].evidence_mode == "injected_transport"
            assert fixture.MARKER in response.response_text
            assert fixture.ANALYSIS in response.response_text
        else:
            assert results[0].generative_analysis_characters == 0
            assert results[0].generative_evidence_mode is None
            native = core.synthesis_engine._compose_native_result(inputs[0]).response_text
            assert response.response_text == native
            assert fixture.MARKER not in response.response_text
        for text in (fixture.CREDENTIAL, PRIVATE_ERROR_BODY, PRIVATE_HEADER, PRIVATE_SSE):
            assert text not in response.response_text
        fixture._assert_no_authority(response)
        assert response.response_text == results[0].response_text
        restarted = fixture._assert_persisted(runtime, response)
        turn = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 1)[0]
        assert turn.request_content == query and turn.response_text == response.response_text
        assert turn.user_id == response.memory_record.user_id == contract.user_id
        assert turn.timestamp == response.memory_record.timestamp
        events = restarted.observability_service.repository.list_events(
            request_id=response.request_id, session_id=response.session_id, limit=100,
            event_names=("input_received", "governance_checked",
                         "response_synthesized", "memory_recorded"),
        )
        assert len(events) == 4
        synthesis = next(event for event in events if event.event_name == "response_synthesized")
        assert synthesis.payload["generative_status"] == expected
        assert not {"diagnostics", "http_status", "provider_error_code"} & synthesis.payload.keys()
        if telemetry and expected != "withheld":
            _assert_redacted(records, tmp_path)
        else:
            assert records == []
    return records, response.response_text


@pytest.mark.parametrize("callback", ["collect", "raise", "mutate_record"])
def test_opt_in_diagnostics_and_callback_failures_preserve_real_core_final(
    tmp_path, monkeypatch, callback,
):
    _run_case(tmp_path, monkeypatch, callback=callback)


@pytest.mark.parametrize("mode,code,http_status", [
    ("http_401", "plan_authentication_refused", 401),
    ("http_403", "plan_permission_refused", 403),
    ("http_429", "plan_usage_limited", 429),
    ("http_503", "http_request_refused", 503),
    ("unsupported", "unsupported_event", None),
    ("incomplete", "response_incomplete", None),
    ("sse_error", "subscription_sharing_usage_limit_exceeded", None),
    ("sse_unknown_error", "provider_error", None),
    ("cleanup", "session_cleanup_failed", None),
])
def test_specific_redacted_diagnostic_does_not_replace_canonical_native_fallback(
    tmp_path, monkeypatch, mode, code, http_status,
):
    records, _ = _run_case(tmp_path, monkeypatch, mode=mode, expected="rejected")
    assert any(record.get("code") == code for record in records), records
    if http_status is not None:
        assert any(record.get("http_status") == http_status for record in records), records


@pytest.mark.parametrize("mode,code", [
    ("catalog_invalid", "siwc_catalog_invalid"), ("expired", "siwc_credential_expired"),
])
def test_catalog_diagnostics_never_dispatch_model_or_echo_account(
    tmp_path, monkeypatch, mode, code,
):
    records, _ = _run_case(tmp_path, monkeypatch, mode=mode, expected="rejected")
    assert any(record.get("code") == code for record in records), records


@pytest.mark.parametrize("callback,code", [
    ("mutate_session", "session_binding_changed"), ("cancel", "cancelled"),
])
def test_diagnostic_callback_cannot_bypass_account_fence_or_cancellation(
    tmp_path, monkeypatch, callback, code,
):
    records, _ = _run_case(tmp_path, monkeypatch, callback=callback, expected="rejected")
    assert any(record.get("code") == code for record in records), records


@pytest.mark.parametrize("query,decision", [
    ("Analyze policy evidence in read-only mode.", PermissionDecision.DEFER_FOR_VALIDATION),
    ("Delete every database now.", PermissionDecision.BLOCK),
])
def test_native_governance_emits_no_inference_diagnostics_or_requests(
    tmp_path, monkeypatch, query, decision,
):
    _run_case(tmp_path, monkeypatch, query=query, decision=decision, expected="withheld")


def test_diagnostics_default_off_with_real_tls_core_and_canonical_restart(tmp_path, monkeypatch):
    _run_case(tmp_path, monkeypatch, telemetry=False)
