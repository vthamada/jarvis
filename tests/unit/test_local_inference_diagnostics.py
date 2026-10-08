"""Host-only diagnostic composition, synthetic ports and no account/network IO."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Event
from types import SimpleNamespace

import pytest

from apps.jarvis_api import __main__ as startup
from apps.jarvis_api.generative_profile import GenerativeProfile
from apps.jarvis_console import generative_analysis_cli as cli
from shared.model_inference import InferenceMessage, InferenceRequest, InferenceResult

MODEL = "synthetic-model"
PROFILE = "profile-" + "a" * 64


def _profile(tmp_path, **changes):
    return GenerativeProfile(authorized=True, model=MODEL, credential_dir=tmp_path,
                             profile_ref=PROFILE, **changes)


def _request():
    return InferenceRequest("synthetic-request", MODEL,
                            (InferenceMessage("user", "Private synthetic input"),),
                            timeout_seconds=20, max_output_chars=256)


class _Port:
    provider_id = "responses_plan"

    def __init__(self, evidence="injected_transport", fail=False):
        self.evidence_mode, self.calls, self.fail = evidence, 0, fail

    def infer(self, request, *, cancellation):
        self.calls += 1
        return InferenceResult(request.request_id, request.model, self.provider_id,
                               "failed" if self.fail else "completed",
                               text="" if self.fail else "Private synthetic output",
                               error_code="plan_permission_refused" if self.fail else None,
                               evidence_mode=self.evidence_mode)


@pytest.mark.parametrize("sink", [False, 1, "private", [], {}])
def test_sink_invalid_before_factory(tmp_path, sink):
    with pytest.raises(ValueError, match="^invalid_local_generative_profile$"):
        _profile(tmp_path, diagnostic_sink=sink)


def test_profile_default_factory_receives_only_explicit_sink(tmp_path, monkeypatch):
    records, calls = [], []
    # Synthetic replacement of the default factory does not prove live inference.
    backend = _Port("live")

    def factory(*args, **kwargs):
        calls.append((args, kwargs))
        return backend

    monkeypatch.setattr(cli, "_session_factory", factory)
    profile = _profile(tmp_path, diagnostic_sink=records.append)
    assert not calls and not records
    result = profile.port_for(Event()).infer(_request())
    assert result.status == "completed" and backend.calls == 1
    assert calls[0][0] == (tmp_path, PROFILE, MODEL)
    assert calls[0][1]["telemetry"] == records.append
    assert [r["phase"] for r in records] == ["profile_setup", "profile_setup", "profile_result"]
    serialized = json.dumps(records)
    for private in (str(tmp_path), PROFILE, MODEL, "Private", "synthetic-request"):
        assert private not in serialized


def test_injected_three_argument_factory_still_injected_with_sink(tmp_path):
    records, calls, backend = [], [], _Port()

    def factory(directory, profile, model):
        calls.append((directory, profile, model))
        return backend

    profile = _profile(tmp_path, port_factory=factory, diagnostic_sink=records.append)
    result = profile.port_for(Event()).infer(_request())
    assert result.status == "completed" and result.evidence_mode == "injected_transport"
    assert calls == [(tmp_path, PROFILE, MODEL)]


def test_none_sink_preserves_factory_kwargs(tmp_path, monkeypatch):
    calls, backend = [], _Port("live")

    def factory(*args, **kwargs):
        calls.append(kwargs)
        return backend

    monkeypatch.setattr(cli, "_session_factory", factory)
    result = _profile(tmp_path).port_for(Event()).infer(_request())
    assert result.status == "completed" and calls == [{}]


@pytest.mark.parametrize("mode", ["raise", "mutate"])
@pytest.mark.parametrize("fail", [False, True])
def test_observer_exception_or_record_mutation_does_not_change_result(tmp_path, mode, fail):
    backend = _Port(fail=fail)

    def sink(record):
        if mode == "raise":
            raise RuntimeError("Private observer failure")
        record.clear()
        record["secret"] = "Private observer data"

    profile = _profile(tmp_path, port_factory=lambda *args: backend, diagnostic_sink=sink)
    result = profile.port_for(Event()).infer(_request())
    assert result.status == ("failed" if fail else "completed")
    assert result.error_code == ("inference_failed" if fail else None)
    assert result.text == ("" if fail else "Private synthetic output")
    assert backend.calls == 1


@pytest.mark.parametrize("mutation", ["cancel", "sink", "deadline"])
def test_observer_fenced_before_factory(tmp_path, mutation):
    token, calls, clock = Event(), [], [1.0]
    profile = None

    def sink(record):
        if record["phase"] == "profile_setup":
            if mutation == "cancel":
                token.set()
            elif mutation == "sink":
                profile._options = replace(profile._options, diagnostic_sink=lambda r: None)
            else:
                clock[0] = 21.0

    profile = _profile(tmp_path, diagnostic_sink=sink,
                       port_factory=lambda *args: calls.append(args), clock=lambda: clock[0])
    result = profile.port_for(token).infer(_request())
    assert not calls and not result.text
    assert result.error_code == {"cancel": "cancelled", "sink": "profile_changed",
                                  "deadline": "timeout"}[mutation]


@pytest.mark.parametrize("mutation", ["request", "provider", "evidence"])
def test_profile_terminal_observer_cannot_skip_final_binding(tmp_path, mutation):
    backend, req = _Port(), _request()

    def sink(record):
        if record["phase"] == "profile_result" and record["status"] == "completed":
            if mutation == "request":
                object.__setattr__(req, "messages", (InferenceMessage("user", "changed"),))
            elif mutation == "provider":
                backend.provider_id = "changed-provider"
            else:
                backend.evidence_mode = "live"

    profile = _profile(tmp_path, port_factory=lambda *args: backend, diagnostic_sink=sink)
    result = profile.port_for(Event()).infer(req)
    assert result.status == "failed" and not result.text
    assert result.error_code == ("request_changed" if mutation == "request" else "binding_mismatch")


@pytest.mark.parametrize("mutation", ["model", "provider", "factory", "session_method"])
def test_session_terminal_observer_cannot_skip_final_binding(monkeypatch, mutation):
    from inference_service.session_inference_port import SessionInferencePort

    from tests.unit import test_session_inference_port as fixture

    # Existing pure synthetic rig; no network or credential store.
    rig = fixture.rig.__wrapped__(monkeypatch)
    port = None

    def sink(record):
        if record["phase"] == "session_result" and record["status"] == "completed":
            if mutation == "model":
                port._model = "different-model"
            elif mutation == "provider":
                port.provider_id = "changed-provider"
            elif mutation == "factory":
                port._factory = lambda *a, **k: None
            else:
                monkeypatch.setattr(rig.session, "provider", lambda *a, **k: None)

    port = SessionInferencePort(rig.session, model=fixture.MODEL, authorized=True,
                                clock=rig.clock, telemetry=sink)
    result = port.infer(fixture.request())
    assert result.status == "failed" and not result.text
    assert result.error_code == "session_binding_changed"


def test_cli_printer_is_fixed_stderr_and_bounded_under_threads(capsys):
    sink = startup._diagnostic_printer()
    raw = {"phase": "responses_http", "status": "observed", "code": "private_code",
           "http_status": 403, "token": "Private secret", "url": "https://private.invalid"}
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(sink, [raw] * 400))
    captured = capsys.readouterr()
    assert not captured.out
    lines = captured.err.splitlines()
    assert len(lines) == 256
    for line in lines:
        record = json.loads(line)
        assert set(record) == {"schema_version", "phase", "status", "code", "http_status"}
        assert record["code"] == "diagnostic_code_withheld" and record["http_status"] == 403
        assert len(line.encode()) < 512 and "Private" not in line and "private.invalid" not in line


@pytest.mark.parametrize("raw", [None, [], "private", {"phase": "private", "status": "observed"},
                                  {"phase": "responses_http", "status": "private"}])
def test_cli_printer_drops_bad_records(raw, capsys):
    startup._diagnostic_printer()(raw)
    captured = capsys.readouterr()
    assert not captured.out and not captured.err


def test_cli_printer_write_failure_does_not_escape(monkeypatch):
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: (_ for _ in ()).throw(
        OSError("Private stderr unavailable")))
    startup._diagnostic_printer()({"phase": "responses_http", "status": "observed"})


@pytest.mark.parametrize("args", [
    ["--inference-diagnostics"], ["--authorized", "--inference-diagnostics"],
    ["--authorized", "--inference-diagnostics", "--model", MODEL],
])
def test_cli_flag_invalid_without_optins_before_runtime(args, monkeypatch, capsys):
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("runtime opened"))
    assert startup.main(args) == 2
    assert "Private" not in capsys.readouterr().err


@pytest.mark.parametrize("diagnostics", [False, True])
def test_cli_composition_inert_and_optional(tmp_path, monkeypatch, diagnostics, capsys):
    from apps.jarvis_api import analysis_service, local_server

    profiles, closed = [], []

    class Service:
        def __init__(self, runtime, *, generative_profile):
            assert runtime == tmp_path
            profiles.append(generative_profile)

        def close(self):
            closed.append("service")

    def stop():
        raise KeyboardInterrupt

    server = SimpleNamespace(server_port=42001, serve_forever=stop,
                             auth=SimpleNamespace(pairing_secret="a" * 64,
                                                  close=lambda: closed.append("auth")),
                             server_close=lambda: closed.append("server"))
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: tmp_path)
    monkeypatch.setattr(analysis_service, "AnalysisService", Service)
    monkeypatch.setattr(local_server, "create_server", lambda *args: server)
    args = ["--authorized", "--enable-generative", "--model", MODEL,
            "--credential-dir", str(tmp_path), "--profile-ref", PROFILE]
    if diagnostics:
        args.append("--inference-diagnostics")
    assert startup.main(args) == 0
    assert closed == ["auth", "service", "server"]
    assert bool(profiles[0]._options.diagnostic_sink) == diagnostics
    assert not capsys.readouterr().err
