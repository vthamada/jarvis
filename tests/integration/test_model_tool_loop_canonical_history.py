"""Opt-in canonical history through real Core/SQLite, with a fixture model only."""

import json
from dataclasses import replace
from threading import Event

import pytest
from memory_service.repository import StoredTurn
from orchestrator_service.model_tool_loop import ModelToolLoopConfig, run_core_tool_loop
from test_model_tool_loop_core import (
    ANALYSIS,
    MODEL,
    QUERY,
    _annex_values,
    _configured_core,
    _contract,
    _final,
    _payload,
    _reports,
    _ScriptedPort,
    _tool,
)

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER, response_for_planning


def test_canonical_history_survives_restart_and_never_replays_model_annex(tmp_path, monkeypatch):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    first_port = _ScriptedPort([_tool(), _final()])
    first_core, _ = _configured_core(
        runtime, ModelToolLoopConfig(port=first_port, model=MODEL, reader=reader), monkeypatch
    )
    previous_query = QUERY
    first = first_core.handle_input(_contract("history-first", previous_query))
    assert _payload(first)["model_tool_loop_status"] == "completed"
    assert _annex_values(first, "Analysis: ") == [ANALYSIS]

    port = _ScriptedPort([_tool(), _final()])
    core, inputs = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    current_query = QUERY
    response = core.handle_input(_contract("history-second", current_query))
    assert _payload(response)["model_tool_loop_status"] == "completed"
    for request in port.calls:
        payload = json.loads(request.messages[0].content)
        assert payload["history"] == [{
            "query": previous_query,
            "response": response_for_planning(first.response_text),
        }]
        assert payload["query"] == current_query
        assert ANALYSIS not in request.messages[0].content
        assert GENERATIVE_ANALYSIS_MARKER not in request.messages[0].content
        assert "history" in request.instructions.lower()
        assert "authority" in request.instructions.lower()
    # Native Planning must still see the pre-existing safe read-side projection,
    # never the prior generated prose. No history is written as a new turn.
    assert ANALYSIS not in repr(inputs[-1].deliberative_plan)
    restarted = _isolated_core(runtime)
    turns = restarted.memory_service.repository.fetch_recent_turns(first.session_id, 6)
    assert len(turns) == 2
    assert turns[0].response_text == first.response_text
    assert turns[1].response_text == response.response_text
    assert reads == ["documentation", "documentation"]


def test_canonical_history_default_off_preserves_old_payload_and_does_not_fetch(
    tmp_path, monkeypatch,
):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    port = _ScriptedPort([_tool(), _final()])
    config = ModelToolLoopConfig(port=port, model=MODEL, reader=reader)
    core, inputs = _configured_core(
        tmp_path / "runtime", config,
        monkeypatch,
    )
    response = core.handle_input(_contract("history-default-off"))
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert all("history" not in json.loads(r.messages[0].content) for r in port.calls)
    # The complete Core also reads memory for native Planning; isolate only the
    # already-admitted model/tool composition when checking its optional fetch.
    direct_port = _ScriptedPort([_tool(), _final()])
    config = replace(config, port=direct_port)
    core.model_tool_loop = config

    def forbidden_fetch(*_args, **_kwargs):
        pytest.fail("default-off model history attempted a repository read")

    monkeypatch.setattr(core.memory_service.repository, "fetch_recent_turns", forbidden_fetch)
    value = replace(inputs[-1], model_tool_loop_outcome=None, model_tool_loop_guard=None)
    outcome, _ = run_core_tool_loop(
        core, config, _contract("history-default-off"), value, emit=lambda *_args: None,
    )
    assert outcome.status == "completed"
    assert all("history" not in json.loads(r.messages[0].content) for r in direct_port.calls)


def test_canonical_history_other_session_is_not_sent(tmp_path, monkeypatch):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    seed = _isolated_core(runtime)
    seed.handle_input(_contract("other-session-seed"))
    port = _ScriptedPort([_tool(), _final()])
    core, _ = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    contract = _contract("history-other-session")
    contract = replace(contract, session_id="another-session", surface_session_id="another-session")
    response = core.handle_input(contract)
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert all("history" not in json.loads(r.messages[0].content) for r in port.calls)


@pytest.mark.parametrize("sensitive", [
    "password=PRIVATE_SENTINEL", "Bearer PRIVATE_SENTINEL", "C:\\private\\document.txt",
    "contact@example.test", "user://private-principal",
])
def test_canonical_history_sensitive_rows_are_not_sent(tmp_path, monkeypatch, sensitive):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    contract = _contract("history-sensitive")
    seed = _isolated_core(runtime)
    seed.memory_service.repository.record_turn(StoredTurn(
        session_id=str(contract.session_id), mission_id=None, user_id=contract.user_id,
        request_content="Compare documentation reports.", intent="analysis",
        response_text="Previous native response. " + sensitive,
        timestamp="2026-10-18T10:00:00+00:00",
    ))
    port = _ScriptedPort([_tool(), _final()])
    core, _ = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    response = core.handle_input(contract)
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert all("history" not in json.loads(r.messages[0].content) for r in port.calls)
    assert all(sensitive not in r.messages[0].content for r in port.calls)


def test_same_session_foreign_subject_cannot_supply_history(tmp_path, monkeypatch):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    contract = _contract("history-foreign-subject")
    seed = _isolated_core(runtime)
    seed.memory_service.repository.record_turn(StoredTurn(
        session_id=str(contract.session_id), mission_id=None, user_id="user://other-subject",
        request_content="FOREIGN_QUERY_SENTINEL", intent="analysis",
        response_text="FOREIGN_RESPONSE_SENTINEL", timestamp="2026-10-18T10:00:00+00:00",
    ))
    port = _ScriptedPort([_tool(), _final()])
    core, _ = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        core.handle_input(contract)
    assert port.calls == []


@pytest.mark.parametrize("boundary", [
    "before_cancel", "after_cancel", "after_deadline", "config_changed",
    "repository_changed", "history_event_changed", "unavailable",
])
def test_history_fetch_and_selection_respect_original_fences(tmp_path, monkeypatch, boundary):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    setup_port = _ScriptedPort([_tool(), _final()])
    config = ModelToolLoopConfig(port=setup_port, model=MODEL, reader=reader)
    core, inputs = _configured_core(tmp_path / "runtime", config, monkeypatch)
    contract = _contract("history-fence")
    first = core.handle_input(contract)
    assert _payload(first)["model_tool_loop_status"] == "completed"
    value = replace(inputs[-1], model_tool_loop_outcome=None, model_tool_loop_guard=None)
    port = _ScriptedPort([])
    cancellation = Event()
    config = replace(config, port=port, include_canonical_history=True, cancellation=cancellation)
    core.model_tool_loop = config
    ticks = [0.0]
    monkeypatch.setattr("orchestrator_service.model_tool_loop.time.monotonic", lambda: ticks[0])
    fetches = []
    repository = core.memory_service.repository
    original_fetch = repository.fetch_recent_turns

    def fetch(session_id, limit):
        fetches.append((session_id, limit))
        rows = original_fetch(session_id, limit)
        if boundary == "after_cancel":
            cancellation.set()
        elif boundary == "after_deadline":
            ticks[0] = 31.0
        elif boundary == "config_changed":
            object.__setattr__(config, "include_canonical_history", False)
        elif boundary == "repository_changed":
            core.memory_service.repository = object()
        elif boundary == "unavailable":
            raise RuntimeError("PRIVATE_EXCEPTION_SENTINEL")
        return rows

    monkeypatch.setattr(repository, "fetch_recent_turns", fetch)
    events = []

    def emit(name, payload):
        events.append((name, payload))
        if boundary == "history_event_changed" and name == "model_tool_loop_history_selected":
            cancellation.set()

    if boundary == "before_cancel":
        cancellation.set()
    outcome, _ = run_core_tool_loop(core, config, contract, value, emit=emit)
    assert outcome.status != "completed"
    assert outcome.analysis == "" and outcome.observations == ()
    assert port.calls == []
    assert len(fetches) == (0 if boundary == "before_cancel" else 1)
    assert all(limit == 6 for _, limit in fetches)
    wire = json.dumps(events)
    assert contract.content not in wire
    assert str(contract.session_id) not in wire
    assert "PRIVATE_EXCEPTION_SENTINEL" not in repr(outcome) + wire


def test_canonical_history_selection_event_is_content_free_and_persisted(tmp_path, monkeypatch):
    reader, _, _ = _reports(tmp_path, monkeypatch)
    port = _ScriptedPort([_tool(), _final()])
    runtime = tmp_path / "runtime"
    core, _ = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    response = core.handle_input(_contract("history-event"))
    assert _payload(response)["model_tool_loop_status"] == "completed"
    selected = [e for e in response.events if e.event_name == "model_tool_loop_history_selected"]
    assert len(selected) == 1
    assert selected[0].payload == {
        "inspected_count": 0, "selected_count": 0, "excluded_count": 0,
        "character_count": 0, "authority": "none",
    }
    restarted = _isolated_core(runtime)
    retained = restarted.observability_service.repository.list_events(
        request_id=response.request_id, event_names=("model_tool_loop_history_selected",), limit=10,
    )
    assert len(retained) == 1
    assert retained[0].payload == selected[0].payload
