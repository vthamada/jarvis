"""Large owned TLS catalogs -> lazy session -> real Core and canonical SQLite.

Synthetic credentials and injected CA/transports only; no human account, OAuth,
external model, LangGraph, authority promotion or production-store access.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
import socket
import ssl
from pathlib import Path

import pytest
from inference_service.oauth_http import SiwcHttpsClient
from inference_service.session_inference_port import SessionInferencePort
from inference_service.siwc_contracts import REQUESTED_SCOPES, SiwcCredentials
from inference_service.siwc_session import SiwcSession

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.types import PermissionDecision

_SPEC = importlib.util.spec_from_file_location(
    "jarvis_large_catalog_core_fixture",
    Path(__file__).with_name("test_generative_analysis_core.py"),
)
fixture = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(fixture)
tls = fixture.tls
MODEL = "synthetic-model"
OLD_LIMIT = 262_144
CATALOG_LIMIT = 2_097_152
PADDING_SENTINEL = "UNTRUSTED_CATALOG_METADATA_NOT_MODEL_INPUT"


def _catalog(size, mode):
    entries = [
        {"visibility": "list", "slug": "first-z", "display_name": "First synthetic"},
        {"visibility": "hidden", "slug": "hidden-model"},
        {"visibility": "list", "slug": MODEL, "display_name": "Selected synthetic"},
        {"visibility": "list", "slug": "last-a", "display_name": "Last synthetic"},
    ]
    if mode == "unlisted":
        entries[2]["slug"] = "different-model"
    elif mode == "count":
        entries = [{"visibility": "hidden"}] * 1025
    document = {"models": entries, "metadata": PADDING_SENTINEL}
    if mode == "schema":
        document["data"] = document.pop("models")
    if mode == "error":
        document = {"error": "temporarily_unavailable", "metadata": PADDING_SENTINEL}
    raw = json.dumps(document, separators=(",", ":")).encode()
    # JSON whitespace exercises the byte budget without changing model limits.
    assert len(raw) < size
    raw += b" " * (size - len(raw))
    if mode == "json":
        raw = b"[" + raw[1:]
    return raw


def _wire(body, content_type, status=b"200 OK"):
    return tls.response(body, status=status, headers=[
        (b"Content-Type", content_type),
        (b"Content-Length", str(len(body)).encode()),
        (b"Connection", b"close"),
    ])


def _model_wire():
    completion = {"type": "response.completed", "response": {
        "id": "owned-large-catalog-response", "model": MODEL, "status": "completed",
        "output": [{"type": "message", "role": "assistant", "status": "completed",
                    "content": [{"type": "output_text",
                                 "text": json.dumps(fixture._candidate())}]}],
    }}
    return _wire(("data: " + json.dumps(completion) + "\r\n\r\n").encode(),
                 b"text/event-stream")


class _ObservedResponse:
    def __init__(self, response, broken):
        self.response, self.broken = response, broken
        self.closed, self.bytes_read = False, 0

    def __getattr__(self, name):
        return getattr(self.response, name)

    def read1(self, maximum):
        chunk = self.response.read1(maximum)
        self.bytes_read += len(chunk)
        return chunk

    def close(self):
        self.response.close()
        self.closed = True
        if self.broken:
            raise OSError("synthetic private response cleanup failure")


def _exercise(tmp_path, monkeypatch, *, mode="valid", size=OLD_LIMIT + 1,
              query=fixture.QUERY, expected="accepted", decision=PermissionDecision.ALLOW):
    catalog_body = _catalog(size, mode)
    assert len(catalog_body) == size and size > OLD_LIMIT
    catalog_payload = _wire(catalog_body, b"application/json",
                            b"429 Too Many Requests" if mode == "error" else b"200 OK")
    catalog_dir, model_dir = tmp_path / "catalog-tls", tmp_path / "model-tls"
    catalog_dir.mkdir()
    model_dir.mkdir()
    original_connection = http.client.HTTPSConnection
    monkeypatch.setattr(tls, "TlsFixture", fixture._InferenceTlsFixture)
    with (tls.tls_fixture(catalog_dir, catalog_payload) as (catalog_server, catalog_client),
          tls.tls_fixture(model_dir, _model_wire()) as (model_server, model_client)):

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
                self.observed_response = _ObservedResponse(
                    super().getresponse(), self.label == "catalog" and mode == "cleanup_response",
                )
                return self.observed_response

            def close(self):
                super().close()
                self.was_closed = True
                # http.client also closes the connection inside getresponse()
                # for Connection: close. Fail only the final cleanup stage.
                if (self.label == "catalog" and mode == "cleanup_connection"
                        and self.observed_response is not None):
                    raise OSError("synthetic private connection cleanup failure")

        calls, port_results = [], []
        connections = {label: OwnedConnection(server, client, label) for label, server, client in (
            ("catalog", catalog_server, catalog_client), ("inference", model_server, model_client),
        )}

        def factory(label):
            def connect(host, *, port, timeout, context):
                assert host == "api.openai.com" and port == 443
                assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
                assert 0 < timeout <= 30
                calls.append(label)
                connection = connections[label]
                connection.timeout = timeout
                return connection
            return connect

        def forbidden(*_args, **_kwargs):
            pytest.fail("large catalog test attempted unowned network/account operation")

        monkeypatch.setattr(http.client, "HTTPSConnection", forbidden)
        monkeypatch.setattr(socket, "getaddrinfo", forbidden)
        host = "urn:uuid:12345678-1234-4234-8234-123456789abc"
        session = SiwcSession(host_id=host, wall_clock=lambda: 1000,
                              client=SiwcHttpsClient(authorized=True,
                                                    connection_factory=factory("catalog")))
        session._credentials = SiwcCredentials(
            "oaiapp_large_catalog_fixture", host, "synthetic-account-subject",
            fixture.CREDENTIAL, "synthetic-refresh", "synthetic-id-token",
            REQUESTED_SCOPES, 2000, 1000,
        )
        for name in ("begin", "load", "refresh"):
            monkeypatch.setattr(session, name, forbidden)
        port = SessionInferencePort(session, model=MODEL, authorized=True,
                                    connection_factory=factory("inference"))
        infer = port.infer

        def capture(request, **kwargs):
            result = infer(request, **kwargs)
            port_results.append(result)
            return result

        monkeypatch.setattr(port, "infer", capture)
        assert port.evidence_mode == "injected_transport" and not calls
        runtime = tmp_path / "runtime"
        core = _isolated_core(runtime)
        inputs, results = fixture._configure(
            core, port, monkeypatch, generative_provider_id="responses_plan",
            generative_evidence_mode="injected_transport",
        )
        contract = fixture._contract(text=query)
        response = core.handle_input(contract)
        assert response.governance_decision.decision == decision
        assert len(results) == 1 and results[0].generative_status == expected, (
            results[0].generative_error_code, calls,
            [(value.status, value.error_code) for value in port_results],
        )
        if expected == "accepted":
            assert calls == ["catalog", "inference"] and len(port_results) == 1
            assert port_results[0].model == MODEL
            assert port_results[0].evidence_mode == "injected_transport"
            assert [choice.slug for choice in session._catalog.choices] == [
                "first-z", MODEL, "last-a",
            ]
            assert connections["catalog"].observed_response.bytes_read == size
            assert len(model_server.requests) == 1
            payload = json.loads(model_server.requests[0].split(b"\r\n\r\n", 1)[1])
            assert payload["model"] == MODEL and payload["store"] is False
            assert payload["stream"] is True
            prompt = json.loads(payload["input"][0]["content"])
            assert {source["text"] for source in prompt["sources"]} == {query}
            assert PADDING_SENTINEL not in json.dumps(payload)
            assert fixture.MARKER in response.response_text
            assert results[0].generative_evidence_mode == "injected_transport"
            assert results[0].generative_error_code is None
            assert not response.specialist_invocations
        else:
            assert calls == ([] if expected == "withheld" else ["catalog"])
            assert not model_server.requests and not model_server.accepted.is_set()
            assert fixture.MARKER not in response.response_text
            native = core.synthesis_engine._compose_native_result(inputs[0]).response_text
            assert response.response_text == native
            assert results[0].generative_analysis_characters == 0
            assert results[0].generative_evidence_mode is None
            assert results[0].generative_error_code is not None
            if mode != "unlisted":
                assert session._catalog is None
        assert len(catalog_server.requests) == (0 if expected == "withheld" else 1)
        for label in calls:
            assert connections[label].was_closed
            assert connections[label].observed_response.closed
        assert fixture.CREDENTIAL not in response.response_text
        assert PADDING_SENTINEL not in response.response_text
        fixture._assert_no_authority(response)
        assert response.response_text == results[0].response_text
        assert response.request_id == contract.request_id
        assert response.session_id == response.memory_record.session_id == contract.session_id
        restarted = fixture._assert_persisted(runtime, response)
        turn = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 1)[0]
        assert turn.request_content == query
        assert turn.user_id == response.memory_record.user_id == contract.user_id
        assert turn.timestamp == response.memory_record.timestamp
        assert turn.response_text == response.memory_record.payload["response_text"]
        assert turn.response_text == response.response_text
        events = restarted.observability_service.repository.list_events(
            request_id=response.request_id, session_id=response.session_id, limit=100,
            event_names=("input_received", "governance_checked",
                         "response_synthesized", "memory_recorded"),
        )
        assert len(events) == 4 and {event.event_name for event in events} == {
            "input_received", "governance_checked", "response_synthesized", "memory_recorded",
        }
        by_name = {event.event_name: event.payload for event in events}
        assert (by_name["memory_recorded"]["memory_record_id"]
                == response.memory_record.memory_record_id)
        assert by_name["governance_checked"]["decision"] == decision.value
        assert by_name["response_synthesized"]["generative_status"] == expected
        assert fixture.CREDENTIAL not in json.dumps(by_name, default=str)


@pytest.mark.parametrize("size", [OLD_LIMIT + 1, CATALOG_LIMIT])
def test_large_catalog_real_tls_exact_model_and_canonical_restart(tmp_path, monkeypatch, size):
    _exercise(tmp_path, monkeypatch, size=size)


@pytest.mark.parametrize("mode,size", [
    ("oversize", CATALOG_LIMIT + 1), ("schema", OLD_LIMIT + 1),
    ("count", OLD_LIMIT + 1), ("json", OLD_LIMIT + 1),
    ("cleanup_response", OLD_LIMIT + 1), ("cleanup_connection", OLD_LIMIT + 1),
    ("error", OLD_LIMIT + 1), ("unlisted", OLD_LIMIT + 1),
])
def test_large_catalog_refusal_never_contacts_model_preserves_native_final(
    tmp_path, monkeypatch, mode, size,
):
    _exercise(tmp_path, monkeypatch, mode=mode, size=size, expected="rejected")


@pytest.mark.parametrize("query,decision", [
    ("Analyze policy evidence in read-only mode.", PermissionDecision.DEFER_FOR_VALIDATION),
    ("Delete every database now.", PermissionDecision.BLOCK),
])
def test_native_governance_never_collects_even_a_large_catalog(
    tmp_path, monkeypatch, query, decision,
):
    _exercise(tmp_path, monkeypatch, size=CATALOG_LIMIT, query=query,
              expected="withheld", decision=decision)
