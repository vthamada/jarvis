"""Opt-in content-free phase export through the public local report composition.

The real HTTP peer is scripted; socket observations never certify model weights
or reasoning quality. Transport and provider timings have separate origins.
"""

import json

import pytest
from test_local_model_tool_loop_cli_flow import (
    ANALYSIS,
    MODEL,
    QUERY,
    REPORT,
    _final,
    _invoke,
    _server,
    _tool,
)

from apps.jarvis_console import local_model_tool_loop_cli as cli
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

_PHASES = (
    "connect_complete", "request_sent", "first_byte", "headers_validated",
    "body_complete", "peer_closed", "provider_parse_complete",
)


class _InjectedPort:
    provider_id = "chat_completions_local"
    evidence_mode = "injected_transport"

    def __init__(self):
        self.calls = 0

    def infer(self, request, *, cancellation=None):
        self.calls += 1
        assert self.calls <= 2
        return InferenceResult(
            request.request_id, request.model, self.provider_id, "completed",
            text=json.dumps(_tool() if self.calls == 1 else _final()),
            evidence_mode=self.evidence_mode,
        )


def _options(tmp_path):
    path = tmp_path / "report.txt"
    path.write_text(REPORT, encoding="utf-8")
    return dict(
        authorized=True, confirmed=True, reports_confirmed=True,
        upstream_egress_acknowledged=True, session_id="phase-diagnostic-session",
        endpoint="http://127.0.0.1:11434/v1/chat/completions", model=MODEL,
        reports={"documentation": path},
    )


def test_opt_in_api_does_not_turn_injected_results_into_phase_evidence(tmp_path):
    port = _InjectedPort()
    result = cli.analyze_local_reports(
        {"schema_version": cli.INPUT_SCHEMA, "query": QUERY}, **_options(tmp_path),
        core_factory=lambda: _isolated_core(tmp_path / "runtime"),
        port_factory=lambda *_: port, include_phase_diagnostics=True,
    )
    assert result["model_tool_loop_status"] == "completed"
    assert result["model_tool_loop_evidence_mode"] == "injected_transport"
    assert result["phase_diagnostics"] == []
    assert result["phase_diagnostics_clock_scope"] == "per_component_operation"
    assert result["real_model_verified"] is result["local_weights_verified"] is False
    assert port.calls == 2


@pytest.mark.parametrize("value", [None, 1, "true", [], {}],
                         ids=["none", "int", "string", "list", "dict"])
def test_diagnostic_opt_in_must_be_literal_bool_before_core_or_model(tmp_path, value):
    def forbidden(*_args, **_kwargs):
        pytest.fail("invalid diagnostic option reached a factory")

    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        cli.analyze_local_reports(
            {"schema_version": cli.INPUT_SCHEMA, "query": QUERY}, **_options(tmp_path),
            core_factory=forbidden, port_factory=forbidden, include_phase_diagnostics=value,
        )
    assert not (tmp_path / "runtime").exists()


def _sample(**changes):
    return {"event": "local_inference_phase", "phase": "first_byte",
            "elapsed_ms": 17, "timing_mode": "live", **changes}


@pytest.mark.parametrize("value", [
    None, [], _sample(details="PRIVATE_DIAGNOSTIC_SENTINEL"),
    _sample(event="PRIVATE_DIAGNOSTIC_SENTINEL"), _sample(phase="unknown"),
    _sample(phase="provider_parse_complete"), _sample(elapsed_ms=True),
    _sample(elapsed_ms=-1), _sample(elapsed_ms=120_001), _sample(elapsed_ms=1.0),
    _sample(elapsed_ms=float("nan")), _sample(timing_mode=False),
    _sample(timing_mode="PRIVATE_DIAGNOSTIC_SENTINEL"),
], ids=["none", "list", "extra", "event", "phase", "other-component", "bool-ms",
        "negative-ms", "large-ms", "float-ms", "nan-ms", "bool-mode", "unknown-mode"])
def test_diagnostic_collector_rejects_non_allowlisted_shapes_and_types(value):
    collector = cli._PhaseDiagnostics()
    collector.observer("transport")(value)
    assert collector.snapshot() == []


def test_diagnostic_collector_is_bounded_copied_and_component_specific():
    collector = cli._PhaseDiagnostics()
    transport = collector.observer("transport")
    provider = collector.observer("provider")
    value = _sample()
    transport(value)
    value["phase"] = "PRIVATE_DIAGNOSTIC_SENTINEL"
    value["details"] = "PRIVATE_DIAGNOSTIC_SENTINEL"
    provider(_sample(phase="first_byte"))
    provider(_sample(phase="provider_parse_complete", timing_mode="injected_clock"))
    for _ in range(50):
        transport(_sample(elapsed_ms=120_000))
    events = collector.snapshot()
    assert len(events) == 28
    assert events[0] == {"component": "transport", **_sample()}
    assert events[1] == {
        "component": "provider",
        **_sample(phase="provider_parse_complete", timing_mode="injected_clock"),
    }
    events[0]["phase"] = "PRIVATE_DIAGNOSTIC_SENTINEL"
    assert "PRIVATE_DIAGNOSTIC_SENTINEL" not in json.dumps(collector.snapshot())


def test_default_off_never_constructs_the_diagnostic_collector(tmp_path, monkeypatch):
    def forbidden():
        pytest.fail("default-off constructed the diagnostic collector")

    monkeypatch.setattr(cli, "_PhaseDiagnostics", forbidden)
    port = _InjectedPort()
    result = cli.analyze_local_reports(
        {"schema_version": cli.INPUT_SCHEMA, "query": QUERY}, **_options(tmp_path),
        core_factory=lambda: _isolated_core(tmp_path / "runtime"),
        port_factory=lambda *_: port,
    )
    assert result["model_tool_loop_status"] == "completed" and port.calls == 2
    assert "phase_diagnostics" not in result and "phase_diagnostics_clock_scope" not in result


@pytest.mark.parametrize("enabled", [False, True], ids=["default-off", "enabled"])
def test_public_cli_exports_only_opted_in_safe_phase_metadata_over_real_http(tmp_path, enabled):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    with _server([_tool(), _final()]) as (server, endpoint):
        process = _invoke(
            tmp_path, endpoint, report,
            extra=("--include-phase-diagnostics",) if enabled else (),
        )
        assert process.returncode == 0 and process.stderr == b""
        result = json.loads(process.stdout)
        assert result["model_tool_loop_status"] == "completed"
        assert len(server.requests) == 2
        assert result["real_model_verified"] is result["local_weights_verified"] is False
        assert result["account_used"] is False
        if not enabled:
            assert "phase_diagnostics" not in result
            return
        events = result["phase_diagnostics"]
        assert result["phase_diagnostics_clock_scope"] == "per_component_operation"
        assert len(events) == 14
        assert [item["phase"] for item in events] == list(_PHASES) * 2
        assert [item["component"] for item in events] == (
            ["transport"] * 6 + ["provider"]
        ) * 2
        for event in events:
            assert set(event) == {
                "component", "event", "phase", "elapsed_ms", "timing_mode",
            }
            assert event["event"] == "local_inference_phase"
            assert type(event["elapsed_ms"]) is int and 0 <= event["elapsed_ms"] <= 120_000
            assert event["timing_mode"] == "live"  # Real clock, not model evidence.
        for start in (0, 7):
            # Compare cumulative samples only within the same transport operation.
            values = [item["elapsed_ms"] for item in events[start:start + 6]]
            assert values == sorted(values)
        for private in (QUERY, REPORT, ANALYSIS, endpoint, str(tmp_path), MODEL):
            assert private.encode() not in process.stdout
        assert result["content_included"] is False and "response_text" not in result
    restarted = _isolated_core(tmp_path / "runtime")
    metadata = json.dumps([
        event.payload for event in restarted.observability_service.repository.list_events(
            session_id="local-http-cli-session", limit=100,
        )
    ], default=str)
    assert "local_inference_phase" not in metadata and "phase_diagnostics" not in metadata
    turns = restarted.memory_service.repository.fetch_recent_turns("local-http-cli-session", 10)
    assert len(turns) == 1 and "phase_diagnostics" not in turns[0].response_text


def test_public_cli_model_mismatch_retains_partial_diagnostics_without_retry_or_model_text(
    tmp_path,
):
    report = tmp_path / "selected-report.txt"
    report.write_text(REPORT, encoding="utf-8")
    with _server([_tool()], model="unselected-model") as (server, endpoint):
        process = _invoke(tmp_path, endpoint, report, extra=("--include-phase-diagnostics",))
        assert process.returncode == 0 and process.stderr == b""
        result = json.loads(process.stdout)
        assert result["canonical_turn_recorded"] is True
        assert result["model_tool_loop_status"] == "failed"
        assert result["model_tool_loop_observation_count"] == 0
        assert result["model_tool_loop_analysis_characters"] == 0
        assert result["operation_dispatched"] is False and len(server.requests) == 1
        assert result["content_included"] is False and "response_text" not in result
        events = result["phase_diagnostics"]
        assert [event["phase"] for event in events] == list(_PHASES[:-1])
        assert all(event["component"] == "transport" for event in events)
        for private in (
            QUERY, REPORT, ANALYSIS, endpoint, MODEL, "unselected-model", str(tmp_path),
        ):
            assert private.encode() not in process.stdout
    restarted = _isolated_core(tmp_path / "runtime")
    turns = restarted.memory_service.repository.fetch_recent_turns("local-http-cli-session", 10)
    assert len(turns) == 1 and GENERATIVE_ANALYSIS_MARKER not in turns[0].response_text
    recorded = restarted.observability_service.repository.list_events(
        session_id="local-http-cli-session", limit=100,
    )
    assert sum(event.event_name == "model_tool_loop_model_requested" for event in recorded) == 1
    assert not any(event.event_name == "model_tool_loop_tool_observed" for event in recorded)
