"""Public CLI/HTTP memory use and a no-history control from the same snapshot.

The HTTP peer is a payload-driven scripted model, not real model weights. It
receives no expected preference. Core, governance, selected report reads,
canonical synthesis, SQLite, separate CLI processes and restart are real.
"""

import json
import re
import shutil

import pytest
from test_local_model_tool_loop_cli_flow import MODEL, QUERY, SESSION, _invoke, _server

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

_PREFERENCE = re.compile(r"Preferred response label: ([a-z0-9-]+)\.")


class _PayloadOnlyResponses:
    """Serve three bounded turns by inspecting only the current HTTP payload.

    The existing server indexes this sequence after recording the request. Its
    nine-entry ceiling rejects any unexpected extra inference. The answer is
    derived anew every time; earlier requests, Python globals and constructor
    arguments never supply the preference.
    """

    def __init__(self):
        self.requests = None

    def __len__(self):
        return 9

    def __getitem__(self, index):
        assert self.requests is not None and index == len(self.requests) - 1
        # This is the latest body actually received over TCP, not test intent or
        # a precomputed answer indexed by the expected arm/preference.
        request = self.requests[-1][2]
        payload = json.loads(request["messages"][-1]["content"])
        observations = payload["observations"]
        unread = payload["continuation"]["unread_resource_ids"]
        if unread:
            return {
                "kind": "tool_call", "call_id": f"current-read-{len(observations) + 1}",
                "tool": "read_local_report", "arguments": {"resource_id": unread[0]},
            }
        queries = [item["query"] for item in payload.get("history", [])] + [payload["query"]]
        labels = [match.group(1) for query in queries for match in _PREFERENCE.finditer(query)]
        label = labels[-1] if labels else "not-available"
        assert len(observations) == 2
        return {
            "kind": "final",
            "analysis": (
                f"Response label: {label}. "
                "Documentation and observability evidence were compared."
            ),
            "citations": [{"call_id": item["call_id"], "quote": item["text"]}
                          for item in observations],
        }


def _annex_values(result, prefix):
    annex = result["response_text"].split(GENERATIVE_ANALYSIS_MARKER, 1)[1]
    return [json.loads(line[len(prefix):]) for line in annex.splitlines()
            if line.startswith(prefix)]


def _run_arm(directory, endpoint, documentation, observability, *, query=QUERY, history=False,
             structured=False):
    extra = ["--include-content", "--include-phase-diagnostics",
             "--report", "observability=" + str(observability)]
    if history:
        extra.append("--include-canonical-history")
    if structured:
        extra.append("--structured-tool-output")
    process = _invoke(directory, endpoint, documentation, query=query, extra=tuple(extra))
    assert process.returncode == 0 and process.stderr == b""
    result = json.loads(process.stdout)
    assert result["canonical_turn_recorded"] is True
    assert result["model_tool_loop_status"] == "completed"
    assert result["model_tool_loop_observation_count"] == 2
    assert result["model_tool_loop_evidence_mode"] == "live"  # Physical HTTP only.
    assert result["real_model_verified"] is result["local_weights_verified"] is False
    assert result["account_used"] is False and result["operation_dispatched"] is False
    assert result["authority"] == "none" and result["content_included"] is True
    assert len(result["phase_diagnostics"]) == 21
    if structured:
        assert result["structured_output_requested"] is True
        assert result["structured_output_schema"] == "jarvis_tool_loop_v1"
    else:
        assert "structured_output_requested" not in result
        assert "structured_output_schema" not in result
    return result


def _readback(directory, result, *, first_result=None):
    restarted = _isolated_core(directory / "runtime")
    rows = restarted.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(rows) == (1 if first_result is None else 2)
    assert all(row.user_id == "user://local_operator" and row.session_id == SESSION for row in rows)
    assert rows[-1].response_text == result["response_text"]
    assert len(rows[-1].response_text) == result["response_character_count"]
    if first_result is not None:
        assert rows[0].response_text == first_result["response_text"]
        assert rows[-1].request_content == QUERY
    events = restarted.observability_service.repository.list_events(session_id=SESSION, limit=200)
    assert sum(event.event_name == "model_tool_loop_model_requested" for event in events) == (
        3 * len(rows)
    )
    assert sum(event.event_name == "model_tool_loop_tool_observed" for event in events) == (
        2 * len(rows)
    )
    assert "local_inference_phase" not in json.dumps([event.payload for event in events],
                                                    default=str)


def _bounded_string(schema, maximum):
    assert schema["type"] == "string"
    assert type(schema["minLength"]) is int and schema["minLength"] == 1
    assert type(schema["maxLength"]) is int and schema["maxLength"] == maximum


def _fixed_response_format(request, *, structured, allowed_kinds, schema_kinds):
    payload = json.loads(request["messages"][-1]["content"])
    assert payload["continuation"]["allowed_response_kinds"] == allowed_kinds
    expected_fields = {"model", "messages", "n", "stream"}
    if not structured:
        assert set(request) == expected_fields
        return
    assert set(request) == expected_fields | {"response_format"}
    value = request["response_format"]
    assert set(value) == {"type", "json_schema"} and value["type"] == "json_schema"
    specification = value["json_schema"]
    assert set(specification) == {"name", "strict", "schema"}
    assert specification["name"] == "jarvis_tool_loop_v1" and specification["strict"] is True
    schema = specification["schema"]
    assert set(schema) == {"type", "anyOf"} and schema["type"] == "object"
    assert type(schema["anyOf"]) is list and len(schema["anyOf"]) == len(schema_kinds)
    branches = {}
    for branch in schema["anyOf"]:
        assert branch["type"] == "object" and branch["additionalProperties"] is False
        kind = branch["properties"]["kind"]
        assert set(kind) == {"enum"} and len(kind["enum"]) == 1
        assert type(kind["enum"][0]) is str
        assert kind["enum"][0] not in branches
        branches[kind["enum"][0]] = branch
    assert set(branches) == set(schema_kinds)
    if "tool_call" in branches:
        tool = branches["tool_call"]
        assert set(tool["properties"]) == set(tool["required"]) == {
            "kind", "call_id", "tool", "arguments",
        }
        _bounded_string(tool["properties"]["call_id"], 80)
        assert tool["properties"]["tool"] == {"enum": ["read_local_report"]}
        arguments = tool["properties"]["arguments"]
        assert arguments["type"] == "object" and arguments["additionalProperties"] is False
        assert set(arguments["properties"]) == set(arguments["required"]) == {"resource_id"}
        _bounded_string(arguments["properties"]["resource_id"], 80)
    if "final" in branches:
        final = branches["final"]
        assert set(final["properties"]) == set(final["required"]) == {
            "kind", "analysis", "citations",
        }
        _bounded_string(final["properties"]["analysis"], 4000)
        citations = final["properties"]["citations"]
        assert citations["type"] == "array"
        assert citations["minItems"] == 1 and citations["maxItems"] == 3
        item = citations["items"]
        assert item["type"] == "object" and item["additionalProperties"] is False
        assert set(item["properties"]) == set(item["required"]) == {"call_id", "quote"}
        _bounded_string(item["properties"]["call_id"], 80)
        _bounded_string(item["properties"]["quote"], 512)


@pytest.mark.parametrize("structured", [False, True], ids=["default-off", "structured"])
def test_contextual_http_answer_uses_only_opted_in_history_and_fresh_tools_after_restart(
    tmp_path, structured,
):
    label = "marigold-mica-731"
    initial_query = QUERY + f" Preferred response label: {label}."
    documentation = tmp_path / "documentation.txt"
    observability = tmp_path / "observability.txt"
    old_reports = (
        "Documentation records the initial pilot outcome.",
        "Observability records initial request latency.",
    )
    new_reports = (
        "Documentation now requires reviewing the pilot outcome.",
        "Observability now requires recording the revised latency measure.",
    )
    documentation.write_text(old_reports[0], encoding="utf-8")
    observability.write_text(old_reports[1], encoding="utf-8")
    seed, assisted, control = (tmp_path / name for name in ("seed", "assisted", "control"))
    for directory in (seed, assisted, control):
        directory.mkdir()
    proposals = _PayloadOnlyResponses()
    with _server(proposals) as (server, endpoint):
        proposals.requests = server.requests
        first = _run_arm(seed, endpoint, documentation, observability, query=initial_query,
                         structured=structured)
        assert len(server.requests) == 3
        _readback(seed, first)
        assert _annex_values(first, "Observed quote: ") == list(old_reports)
        assert label in _annex_values(first, "Analysis: ")[0]

        # The seed process has exited and all readback operations returned. Both
        # arms receive an identical quiescent SQLite runtime, not one another's
        # second turn. There is no shared process/provider history.
        shutil.copytree(seed / "runtime", assisted / "runtime")
        shutil.copytree(seed / "runtime", control / "runtime")
        documentation.write_text(new_reports[0], encoding="utf-8")
        observability.write_text(new_reports[1], encoding="utf-8")
        assert label not in QUERY and all(label not in text for text in old_reports + new_reports)

        second = _run_arm(assisted, endpoint, documentation, observability, history=True,
                          structured=structured)
        without_history = _run_arm(control, endpoint, documentation, observability,
                                  structured=structured)
        assert len(server.requests) == 9
        assert all(request[2]["model"] == MODEL for request in server.requests)
        # Independent scenario oracle: each arm reads the two selected reports,
        # then answers. Do not derive schema expectations from query text,
        # production factories or the continuation returned in the payload.
        expected_phases = (
            (["tool_call"], ["tool_call"]),
            (["tool_call", "final"], ["tool_call"]),
            (["tool_call", "final"], ["tool_call", "final"]),
        )
        for index, request in enumerate(server.requests):
            allowed_kinds, schema_kinds = expected_phases[index % 3]
            _fixed_response_format(request[2], structured=structured, allowed_kinds=allowed_kinds,
                                   schema_kinds=schema_kinds)
        payloads = [json.loads(request[2]["messages"][-1]["content"])
                    for request in server.requests]
        for payload in payloads[:3]:
            assert payload["query"] == initial_query and "history" not in payload
        for payload in payloads[3:6]:
            assert payload["query"] == QUERY
            assert len(payload["history"]) == 1
            assert payload["history"][0]["query"] == initial_query
            assert label not in json.dumps({key: value for key, value in payload.items()
                                           if key != "history"})
        for request, payload in zip(server.requests[6:], payloads[6:], strict=True):
            assert payload["query"] == QUERY and "history" not in payload
            assert label not in json.dumps(request[2])
        for start in (0, 3, 6):
            assert payloads[start]["observations"] == []
            assert payloads[start]["continuation"]["allowed_response_kinds"] == ["tool_call"]
            assert len(payloads[start + 1]["observations"]) == 1
            assert payloads[start + 1]["continuation"]["allowed_response_kinds"] == [
                "tool_call", "final",
            ]
            assert payloads[start + 1]["continuation"]["suggested_next_action"] == (
                "read_unread_report"
            )
            assert [len(payloads[start + offset]["continuation"]["unread_resource_ids"])
                    for offset in range(3)] == [2, 1, 0]
            assert len(payloads[start + 2]["observations"]) == 2
            assert payloads[start + 2]["continuation"]["remaining_tool_calls"] == 1
            assert payloads[start + 2]["continuation"]["suggested_next_action"] == "finalize"
        for payload in (payloads[5], payloads[8]):
            assert [item["text"] for item in payload["observations"]] == list(new_reports)

    expected = "Documentation and observability evidence were compared."
    assert _annex_values(second, "Analysis: ") == [f"Response label: {label}. {expected}"]
    assert _annex_values(without_history, "Analysis: ") == [
        f"Response label: not-available. {expected}",
    ]
    assert _annex_values(second, "Observed quote: ") == list(new_reports)
    assert _annex_values(without_history, "Observed quote: ") == list(new_reports)
    assert label not in _annex_values(without_history, "Analysis: ")[0]
    _readback(assisted, second, first_result=first)
    _readback(control, without_history, first_result=first)
