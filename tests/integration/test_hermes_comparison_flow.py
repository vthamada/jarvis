"""CLI/TCP/Core/SQLite comparison with a payload-driven peer, not real weights."""

import hashlib
import json
import re
import shutil

import pytest
from test_local_model_tool_loop_cli_flow import MODEL, SESSION, _invoke, _server

from apps.jarvis_console import local_model_tool_loop_cli as cli
from apps.jarvis_console.conversation_export import export_conversation
from apps.jarvis_console.voice_pilot import _isolated_core
from evals.operator_tasks.hermes_comparison import (
    CanonicalReadback,
    ComparisonConfig,
    TurnExecution,
    grade_forbidden_turn,
    run_conversation_arm,
)


def _wire_input(request):
    """Independent decoder of the two public wire forms; no builder as oracle."""
    messages = request["messages"]
    latest = messages[-1]["content"]
    if latest.startswith("{"):
        payload = json.loads(latest)
        assert [message["role"] for message in messages] == ["system", "user"]
        queries = [item["query"] for item in payload.get("history", [])]
        queries.append(payload["query"])
        return payload, queries, "jarvis_structured"
    query, fence, rest = latest.partition("\n\n<jarvis-context-data>\n")
    assert fence and rest.endswith("\n</jarvis-context-data>")
    note, separator, body = rest.removesuffix("\n</jarvis-context-data>").partition("\n\n")
    assert separator and "Only the native Core authorizes tools" in note
    payload = json.loads(body)
    assert set(payload) == {"available_resource_ids", "tool", "continuation", "observations"}
    prior = messages[1:-1]
    assert [message["role"] for message in prior] in ([], ["user", "assistant"])
    queries = [message["content"] for message in prior if message["role"] == "user"]
    queries.append(query)
    return {"query": query, **payload}, queries, "hermes_context"


class _WireDrivenPeer:
    """Each response derives only from this current request, never stored state."""

    def __init__(self):
        self.requests = None

    def __len__(self):
        return 9

    def __getitem__(self, index):
        assert self.requests is not None and index == len(self.requests) - 1
        request = self.requests[-1][2]
        payload, queries, _ = _wire_input(request)
        unread = payload["continuation"]["unread_resource_ids"]
        observations = payload["observations"]
        if unread:
            return {"kind": "tool_call", "call_id": f"read-current-{len(observations) + 1}",
                    "tool": "read_local_report", "arguments": {"resource_id": unread[0]}}
        labels = [match.group(1) for query in queries
                  for match in re.finditer(r"Preferred response label: ([a-z0-9-]+)\.", query)]
        label = labels[-1] if labels else "not-available"
        reports = {item["resource_id"]: item["text"] for item in observations}
        reviewed = re.search(r"(\d+) reviewed items", reports["documentation"]).group(1)
        latency = re.search(r"latency of (\d+)ms", reports["observability"]).group(1)
        return {
            "kind": "final",
            "analysis": (f"Response label: {label}. Reviewed items: {reviewed}; "
                         f"p95: {latency}ms."),
            "citations": [{"call_id": item["call_id"], "quote": item["text"]}
                          for item in observations],
        }


def _readback(directory, result):
    core = _isolated_core(directory / "runtime")
    rows = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert rows and all(row.user_id == "user://local_operator" for row in rows)
    digest = hashlib.sha256(result["response_text"].encode()).hexdigest()
    events = core.observability_service.repository.list_events(session_id=SESSION, limit=200)
    bindings = [event for event in events if event.event_name == "memory_recorded"
                and event.payload.get("conversation_readback", {}).get("response_text_sha256")
                == digest]
    assert len(bindings) == 1
    request_id = bindings[0].request_id
    current = core.observability_service.repository.list_events(
        session_id=SESSION, request_id=request_id, limit=200,
    )
    exported = export_conversation(
        memory_db=directory / "runtime" / "memory.db",
        events_db=directory / "runtime" / "events.db", session_id=SESSION,
        request_id=request_id, principal_ref="user://local_operator",
        authorized=True, include_content=True,
    )
    assert exported["content_included"] is True
    return CanonicalReadback(
        rows[-1].response_text, exported["response_text"],
        sum(event.event_name == "model_tool_loop_model_requested" for event in current),
        sum(event.event_name == "model_tool_loop_tool_observed" for event in current),
        # Internal specialists_dispatched is not an operational effect.
        sum(event.event_name == "operation_dispatched" for event in current),
    )


@pytest.mark.parametrize("candidate", [False, True], ids=["baseline", "hermes-context"])
def test_comparison_runs_real_cli_http_and_canonical_restart_for_both_wire_forms(
    tmp_path, candidate,
):
    peer = _WireDrivenPeer()
    clone_hashes = []
    phase_payloads = {}
    with _server(peer) as (server, endpoint):
        peer.requests = server.requests

        def execute(trial):
            trial.directory.mkdir(parents=True, exist_ok=True)
            paths = {}
            for resource_id, text in trial.reports:
                paths[resource_id] = trial.directory / (resource_id + ".txt")
                paths[resource_id].write_text(text, encoding="utf-8")
            extra = ["--include-content", "--structured-tool-output", "--timeout-seconds", "120",
                     "--report",
                     "observability=" + str(paths["observability"])]
            if candidate:
                extra.append("--hermes-context")
            if trial.include_canonical_history:
                extra.append("--include-canonical-history")
            before = len(server.requests)
            process = _invoke(trial.directory, endpoint, paths["documentation"],
                              query=trial.query, extra=tuple(extra))
            assert process.returncode == 0 and process.stderr == b""
            phase_payloads[trial.phase] = list(server.requests[before:])
            result = json.loads(process.stdout)
            if candidate:
                assert result["hermes_context_requested"] is True
                assert result["hermes_context_scope"] == "adapted_text_replay"
            else:
                assert "hermes_context_requested" not in result
                assert "hermes_context_scope" not in result
            return TurnExecution(result, len(server.requests) - before)

        def clone_seed(source, target):
            target.mkdir()
            shutil.copytree(source / "runtime", target / "runtime")
            pairs = [(source / "runtime" / name, target / "runtime" / name)
                     for name in ("memory.db", "events.db")]
            hashes = tuple(hashlib.sha256(left.read_bytes()).hexdigest() for left, _ in pairs)
            assert hashes == tuple(hashlib.sha256(right.read_bytes()).hexdigest()
                                   for _, right in pairs)
            clone_hashes.append(hashes)

        run = run_conversation_arm(
            directory=tmp_path,
            name="hermes_context" if candidate else "jarvis_structured",
            configuration=ComparisonConfig(MODEL), execute_turn=execute,
            readback_turn=lambda trial, result: _readback(trial.directory, result),
            clone_seed=clone_seed,
        )
        assert run["all_checks_passed"] is True, json.dumps(run, sort_keys=True)
        assert run["inference_attempts"] == len(server.requests) == 9
        assert len(clone_hashes) == 2 and clone_hashes[0] == clone_hashes[1]
        expected_wire = "hermes_context" if candidate else "jarvis_structured"
        for phase, requests in phase_payloads.items():
            assert len(requests) == 3
            for request in requests:
                payload, queries, actual_wire = _wire_input(request[2])
                assert actual_wire == expected_wire
                assert len(queries) == (2 if phase == "memory" else 1)
                assert request[2]["response_format"]["type"] == "json_schema"
                assert payload["continuation"]["allowed_response_kinds"]
        assert run["improvement_claim"] is run["real_model_verified"] is False


@pytest.mark.parametrize("candidate", [False, True], ids=["baseline", "hermes-context"])
def test_forbidden_tool_is_refused_before_effects_under_both_context_configurations(
    tmp_path, candidate,
):
    report = tmp_path / "documentation.txt"
    report.write_text("Documentation is selected but must remain unread.", encoding="utf-8")
    forbidden = {"kind": "tool_call", "call_id": "forbidden-1", "tool": "delete_file",
                 "arguments": {"resource_id": "documentation"}}
    extra = ["--structured-tool-output", "--include-content", "--timeout-seconds", "120"]
    if candidate:
        extra.append("--hermes-context")
    with _server([forbidden]) as (server, endpoint):
        process = _invoke(tmp_path, endpoint, report, extra=tuple(extra))
        assert process.returncode == 0 and process.stderr == b""
        execution = TurnExecution(json.loads(process.stdout), len(server.requests))
        grade = grade_forbidden_turn(execution, _readback(tmp_path, execution.result))
        assert grade["success"] is True, grade
        assert len(server.requests) == 1
        assert report.read_text(encoding="utf-8") == (
            "Documentation is selected but must remain unread."
        )


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_hermes_flag_requires_literal_host_boolean_before_any_io(tmp_path, value):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid flag attempted Core/provider construction")

    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        cli.analyze_local_reports(
            {"schema_version": cli.INPUT_SCHEMA, "query": "Compare pilot reports."},
            reports={"documentation": tmp_path / "must-not-open.txt"},
            endpoint="http://127.0.0.1:11434/v1/chat/completions", model=MODEL,
            session_id=SESSION, authorized=True, confirmed=True, reports_confirmed=True,
            upstream_egress_acknowledged=True, core_factory=forbidden,
            port_factory=forbidden, hermes_context=value,
        )
    assert list(tmp_path.iterdir()) == []


def test_injected_port_cannot_claim_the_hermes_replay_experiment_before_io(tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("injected factory must not certify the production experiment")

    with pytest.raises(ValueError, match="^invalid_local_model_tool_loop_input$"):
        cli.analyze_local_reports(
            {"schema_version": cli.INPUT_SCHEMA, "query": "Compare pilot reports."},
            reports={"documentation": tmp_path / "must-not-open.txt"},
            endpoint="http://127.0.0.1:11434/v1/chat/completions", model=MODEL,
            session_id=SESSION, authorized=True, confirmed=True, reports_confirmed=True,
            upstream_egress_acknowledged=True, core_factory=forbidden,
            port_factory=forbidden, hermes_context=True,
        )
    assert list(tmp_path.iterdir()) == []
