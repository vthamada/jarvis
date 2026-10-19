"""Two-turn usefulness of canonical history with a contextual fixture model.

The model fixture derives its answer from received data, not constructor state.
Core admission, report reads, native synthesis, SQLite storage and restart are
real. This proves context wiring and fences, not live-model reasoning quality.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace

import pytest
from orchestrator_service.model_tool_loop import ModelToolLoopConfig
from test_model_tool_loop_core import (
    DOCUMENTATION,
    MODEL,
    QUERY,
    _annex_values,
    _assert_no_authority,
    _configured_core,
    _contract,
    _payload,
    _reports,
)

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

_PREFERENCE = re.compile(r"Preferred response label: ([a-z0-9-]+)\.")


class _ContextualPreferencePort:
    """Generic extraction from history only, followed by a fresh report read.

    No expected preference is supplied to this port. A new instance is created
    after the first Core is discarded, so process-local fixture state cannot
    stand in for the persisted conversation. The alternative modes intentionally
    propose invalid finals to exercise the real coordinator's evidence checks.
    """

    def __init__(self, *, mode="read_then_finish"):
        self.mode = mode
        self.calls = []

    def infer(self, request, *, cancellation=None):
        self.calls.append(request)
        payload = json.loads(request.messages[0].content)
        matches = [
            match.group(1)
            for turn in payload.get("history", [])
            for match in _PREFERENCE.finditer(turn["query"])
        ]
        label = matches[-1] if matches else "not-available"
        analysis = f"Presentation label: {label}. Documentation evidence was considered."
        observations = payload["observations"]
        if not observations and self.mode != "finish_without_read":
            proposal = {
                "kind": "tool_call", "call_id": "fresh-read",
                "tool": "read_local_report", "arguments": {"resource_id": "documentation"},
            }
        else:
            if self.mode == "finish_without_read":
                citation = {"call_id": "historical-read", "quote": label}
            elif self.mode == "cite_historical_call":
                citation = {"call_id": "historical-read", "quote": observations[0]["text"]}
            elif self.mode == "cite_history_only":
                citation = {"call_id": "fresh-read", "quote": label}
            else:
                citation = {"call_id": "fresh-read", "quote": observations[0]["text"]}
            proposal = {"kind": "final", "analysis": analysis, "citations": [citation]}
        return InferenceResult(
            request_id=request.request_id, model=request.model, provider_id="fixture",
            status="completed", text=json.dumps(proposal), evidence_mode="fixture",
        )


def _seed_preference(runtime, label):
    """Admit and persist a normal user turn; no direct database seeding."""
    first_core = _isolated_core(runtime)
    first_contract = _contract(
        "preference-first", QUERY + f" Preferred response label: {label}."
    )
    first = first_core.handle_input(first_contract)
    _assert_no_authority(first)
    turns = first_core.memory_service.repository.fetch_recent_turns(first.session_id, 6)
    assert len(turns) == 1
    assert turns[0].request_content == first_contract.content
    assert turns[0].response_text == first.response_text
    return first


def _second_turn(runtime, reader, monkeypatch, *, history=True, mode="read_then_finish",
                 contract=None):
    port = _ContextualPreferencePort(mode=mode)
    core, inputs = _configured_core(
        runtime,
        ModelToolLoopConfig(
            port=port, model=MODEL, reader=reader, include_canonical_history=history,
        ),
        monkeypatch,
    )
    selected_contract = contract or _contract("preference-second")
    assert selected_contract.content == QUERY
    response = core.handle_input(selected_contract)
    return core, inputs, response, port


@pytest.mark.parametrize("label", ["saffron-nacre-731", "cobalt-juniper-482"],
                         ids=["saffron", "cobalt"])
def test_second_turn_uses_unrepeated_arbitrary_preference_after_sqlite_restart(
    tmp_path, monkeypatch, label,
):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    first = _seed_preference(runtime, label)
    core, inputs, response, port = _second_turn(runtime, reader, monkeypatch)
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert len(port.calls) == 2
    assert reads == ["documentation"]
    assert label not in QUERY and label not in DOCUMENTATION
    for call in port.calls:
        payload = json.loads(call.messages[0].content)
        assert payload["query"] == QUERY
        assert label not in payload["query"]
        assert len(payload["history"]) == 1
        assert label in payload["history"][0]["query"]
    assert _annex_values(response, "Analysis: ") == [
        f"Presentation label: {label}. Documentation evidence was considered."
    ]
    assert _annex_values(response, "Observed quote: ") == [DOCUMENTATION]
    assert json.loads(port.calls[0].messages[0].content)["observations"] == []
    assert json.loads(port.calls[1].messages[0].content)["observations"] == [{
        "call_id": "fresh-read", "tool": "read_local_report",
        "resource_id": "documentation", "text": DOCUMENTATION,
    }]
    _assert_no_authority(response)
    native = core.synthesis_engine._compose_native_result(inputs[-1]).response_text
    assert response.response_text.startswith(native + "\n\n" + GENERATIVE_ANALYSIS_MARKER)
    restarted = _isolated_core(runtime)
    retained = restarted.memory_service.repository.fetch_recent_turns(first.session_id, 6)
    assert len(retained) == 2
    assert retained[0].response_text == first.response_text
    assert retained[1].request_content == QUERY
    assert retained[1].response_text == response.response_text


@pytest.mark.parametrize("scope", ["default-off", "other-session", "other-subject"],
                         ids=["default-off", "other-session", "other-subject"])
def test_preference_is_not_sent_without_opt_in_or_across_subject_session_scope(
    tmp_path, monkeypatch, scope,
):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    label = "violet-spruce-926"
    _seed_preference(runtime, label)
    contract = _contract("preference-second")
    if scope in {"other-session", "other-subject"}:
        contract = replace(contract, session_id="preference-new-session",
                           surface_session_id="preference-new-session")
    if scope == "other-subject":
        contract = replace(contract, user_id="user://another-synthetic-subject",
                           canonical_user_ref="user://another-synthetic-subject",
                           operator_identity_ref="operator://another-synthetic-subject")
    _, _, response, port = _second_turn(
        runtime, reader, monkeypatch, history=scope != "default-off", contract=contract,
    )
    assert _payload(response)["model_tool_loop_status"] == "completed"
    assert len(port.calls) == 2 and reads == ["documentation"]
    for call in port.calls:
        assert label not in call.messages[0].content + call.instructions
        assert "history" not in json.loads(call.messages[0].content)
    assert _annex_values(response, "Analysis: ") == [
        "Presentation label: not-available. Documentation evidence was considered."
    ]
    _assert_no_authority(response)


def test_same_session_different_subject_is_rejected_before_contextual_model(tmp_path, monkeypatch):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    _seed_preference(runtime, "amber-fern-613")
    port = _ContextualPreferencePort()
    core, _ = _configured_core(
        runtime,
        ModelToolLoopConfig(port=port, model=MODEL, reader=reader, include_canonical_history=True),
        monkeypatch,
    )
    contract = replace(
        _contract("preference-foreign-subject"), user_id="user://another-synthetic-subject",
        canonical_user_ref="user://another-synthetic-subject",
        operator_identity_ref="operator://another-synthetic-subject",
    )
    with pytest.raises(ValueError, match="session_subject_scope_mismatch"):
        core.handle_input(contract)
    assert port.calls == [] and reads == []


@pytest.mark.parametrize("mode,error,expected_reads,expected_calls", [
    ("finish_without_read", "observation_required", [], 1),
    ("cite_historical_call", "citation_not_observed", ["documentation"], 2),
    ("cite_history_only", "citation_not_exact", ["documentation"], 2),
], ids=["no-new-read", "old-call-id", "history-only-quote"])
def test_second_turn_memory_never_replaces_fresh_report_read_and_exact_citation(
    tmp_path, monkeypatch, mode, error, expected_reads, expected_calls,
):
    reader, reads, _ = _reports(tmp_path, monkeypatch)
    runtime = tmp_path / "runtime"
    label = "silver-heather-854"
    _seed_preference(runtime, label)
    core, inputs, response, port = _second_turn(runtime, reader, monkeypatch, mode=mode)
    payload = _payload(response)
    assert payload["model_tool_loop_status"] == "refused"
    assert payload["model_tool_loop_error_code"] == error
    assert payload["model_tool_loop_observation_count"] == 0
    assert payload["model_tool_loop_analysis_characters"] == 0
    assert len(port.calls) == expected_calls and reads == expected_reads
    first_prompt = json.loads(port.calls[0].messages[0].content)
    assert label in first_prompt["history"][0]["query"]
    assert first_prompt["observations"] == []
    assert response.response_text == core.synthesis_engine._compose_native_result(
        inputs[-1]
    ).response_text
    assert GENERATIVE_ANALYSIS_MARKER not in response.response_text
    _assert_no_authority(response)
    restarted = _isolated_core(runtime)
    retained = restarted.memory_service.repository.fetch_recent_turns(response.session_id, 6)
    assert len(retained) == 2
    assert retained[-1].request_content == QUERY
    assert retained[-1].response_text == response.response_text
    assert "Presentation label:" not in retained[-1].response_text
