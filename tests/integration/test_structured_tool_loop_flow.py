"""Structured generation is a host hint, never permission or answer repair."""

import json

import pytest
from test_local_model_tool_loop_cli_flow import (
    MODEL,
    QUERY,
    REPORT,
    SESSION,
    _invoke,
    _server,
)

from apps.jarvis_console import local_model_tool_loop_cli as cli
from apps.jarvis_console.voice_pilot import _isolated_core


def _forbidden(*args, **kwargs):
    pytest.fail("invalid structured selection attempted I/O or provider construction")


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_structured_selection_requires_literal_host_boolean_before_io(tmp_path, value):
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        cli.analyze_local_reports(
            {"schema_version": cli.INPUT_SCHEMA, "query": QUERY},
            reports={"documentation": tmp_path / "not-opened.txt"},
            endpoint="http://127.0.0.1:11434/v1/chat/completions", model=MODEL,
            session_id=SESSION, authorized=True, confirmed=True, reports_confirmed=True,
            upstream_egress_acknowledged=True, core_factory=_forbidden,
            port_factory=_forbidden, structured_tool_output=value,
        )
    assert list(tmp_path.iterdir()) == []


def test_structured_selection_cannot_claim_support_from_injected_port(tmp_path):
    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        cli.analyze_local_reports(
            {"schema_version": cli.INPUT_SCHEMA, "query": QUERY},
            reports={"documentation": tmp_path / "not-opened.txt"},
            endpoint="http://127.0.0.1:11434/v1/chat/completions", model=MODEL,
            session_id=SESSION, authorized=True, confirmed=True, reports_confirmed=True,
            upstream_egress_acknowledged=True, core_factory=_forbidden,
            port_factory=_forbidden, structured_tool_output=True,
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("proposal,code", [
    ("REJECTED_PROPOSAL_SENTINEL", "invalid_model_message"),
    ({"kind": "function", "analysis": "REJECTED_PROPOSAL_SENTINEL"},
     "invalid_model_message"),
    ({"kind": "final", "analysis": "REJECTED_PROPOSAL_SENTINEL", "citations": []},
     "observation_required"),
    ({"kind": "tool_call", "call_id": "read-1", "tool": "delete_file",
      "arguments": {"resource_id": "documentation"}}, "tool_not_allowed"),
    ({"kind": "tool_call", "call_id": "read-1", "tool": "read_local_report",
      "arguments": {"resource_id": "not-selected"}}, "resource_not_selected"),
])
def test_server_ignoring_schema_cannot_bypass_core_or_trigger_repair(tmp_path, proposal, code):
    report = tmp_path / "selected.txt"
    report.write_text(REPORT, encoding="utf-8")
    with _server([proposal]) as (server, endpoint):
        process = _invoke(tmp_path, endpoint, report,
                          extra=("--structured-tool-output", "--include-content"))
        assert process.returncode == 0 and process.stderr == b""
        result = json.loads(process.stdout)
        assert len(server.requests) == 1
        assert server.requests[0][2]["response_format"]["type"] == "json_schema"
        initial_schema = server.requests[0][2]["response_format"]["json_schema"]["schema"]
        initial_branches = initial_schema["anyOf"]
        assert [branch["properties"]["kind"]["enum"] for branch in initial_branches] == [
            ["tool_call"],
        ]
        assert result["structured_output_requested"] is True
        assert result["structured_output_schema"] == "jarvis_tool_loop_v1"
        assert result["model_tool_loop_status"] == "refused"
        assert result["model_tool_loop_error_code"] == code
        assert result["model_tool_loop_observation_count"] == 0
        assert result["operation_dispatched"] is False
        assert result["canonical_turn_recorded"] is True
        assert result["authority"] == "none"
        assert result["real_model_verified"] is result["local_weights_verified"] is False
        assert "REJECTED_PROPOSAL_SENTINEL" not in json.dumps(result)

    core = _isolated_core(tmp_path / "runtime")
    rows = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(rows) == 1 and rows[0].response_text == result["response_text"]
    events = core.observability_service.repository.list_events(session_id=SESSION, limit=200)
    assert sum(event.event_name == "model_tool_loop_model_requested" for event in events) == 1
    assert not any(event.event_name == "model_tool_loop_tool_observed" for event in events)


def test_structured_schema_follows_core_phase_until_final_only_after_three_reads(tmp_path):
    report = tmp_path / "phase-selected.txt"
    report.write_text(REPORT, encoding="utf-8")
    proposals = [
        {"kind": "tool_call", "call_id": f"phase-read-{index}", "tool": "read_local_report",
         "arguments": {"resource_id": "documentation"}} for index in (1, 2, 3)
    ] + [{"kind": "final", "analysis": "The selected report records the documentation outcome.",
          "citations": [{"call_id": "phase-read-3", "quote": REPORT}]}]
    expected_kinds = [["tool_call"], ["tool_call", "final"], ["tool_call", "final"], ["final"]]
    with _server(proposals) as (server, endpoint):
        process = _invoke(tmp_path, endpoint, report,
                          extra=("--structured-tool-output", "--include-content"))
        assert process.returncode == 0 and process.stderr == b""
        result = json.loads(process.stdout)
        assert result["model_tool_loop_status"] == "completed"
        assert result["model_tool_loop_observation_count"] == 3
        assert result["canonical_turn_recorded"] is True
        assert result["operation_dispatched"] is False
        assert len(server.requests) == 4
        for (_, _, request), expected in zip(server.requests, expected_kinds, strict=True):
            progress = json.loads(request["messages"][-1]["content"])["continuation"]
            assert progress["allowed_response_kinds"] == expected
            branches = request["response_format"]["json_schema"]["schema"]["anyOf"]
            assert [branch["properties"]["kind"]["enum"][0] for branch in branches] == expected

    core = _isolated_core(tmp_path / "runtime")
    rows = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(rows) == 1 and rows[0].response_text == result["response_text"]


def test_ignored_read_priority_does_not_introduce_a_new_core_coverage_policy(tmp_path):
    report = tmp_path / "documentation.txt"
    report.write_text(REPORT, encoding="utf-8")
    other = tmp_path / "observability.txt"
    other.write_text("UNREAD_REPORT_SENTINEL: Observability remains selected.", encoding="utf-8")
    proposals = [
        {"kind": "tool_call", "call_id": "only-read", "tool": "read_local_report",
         "arguments": {"resource_id": "documentation"}},
        {"kind": "final", "analysis": "Only documentation was consulted; comparison is incomplete.",
         "citations": [{"call_id": "only-read", "quote": REPORT}]},
    ]
    with _server(proposals) as (server, endpoint):
        process = _invoke(
            tmp_path, endpoint, report,
            extra=("--report", "observability=" + str(other),
                   "--structured-tool-output", "--include-content"),
        )
        assert process.returncode == 0 and process.stderr == b""
        result = json.loads(process.stdout)
        assert len(server.requests) == 2
        second = server.requests[1][2]
        progress = json.loads(second["messages"][-1]["content"])["continuation"]
        assert progress["allowed_response_kinds"] == ["tool_call", "final"]
        assert progress["suggested_next_action"] == "read_unread_report"
        branches = second["response_format"]["json_schema"]["schema"]["anyOf"]
        assert [branch["properties"]["kind"]["enum"] for branch in branches] == [["tool_call"]]
        # A hint is not a new Core refusal or hidden retry. Native acceptance
        # and the task's incomplete coverage must remain distinguishable.
        assert result["model_tool_loop_status"] == "completed"
        assert result["model_tool_loop_error_code"] is None
        assert result["model_tool_loop_observation_count"] == 1
        assert result["canonical_turn_recorded"] is True
        assert result["operation_dispatched"] is False
        assert "UNREAD_REPORT_SENTINEL" not in json.dumps(result)
    core = _isolated_core(tmp_path / "runtime")
    rows = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(rows) == 1 and rows[0].response_text == result["response_text"]
