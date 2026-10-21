"""Entire reusable two-arm driver, real Core/SQLite and scripted local HTTP."""

import hashlib
import json

import pytest
from test_hermes_comparison_flow import _wire_input, _WireDrivenPeer
from test_local_model_tool_loop_cli_flow import MODEL, _server

from apps.jarvis_console.conversation_export import export_conversation
from apps.jarvis_console.voice_pilot import _isolated_core
from evals.operator_tasks import hermes_local_experiment as lab
from evals.operator_tasks.hermes_comparison import (
    FOLLOWUP_QUERY,
    PREFERENCE,
    PUBLIC_CASE_DIGEST,
    REVISED_REPORTS,
    SEED_QUERY,
    SEED_REPORTS,
)
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

SESSION = "hermes-synthetic-comparison"


class _DriverPeer(_WireDrivenPeer):
    def __len__(self):
        return 24


class _FirstArmFaultPeer(_DriverPeer):
    def __getitem__(self, index):
        if index == 0:
            # Deliberate single faulty model response. The next independent
            # arm remains payload-driven, not a retry of the failed seed.
            return {"kind": "final", "analysis": "Premature completion.", "citations": []}
        return super().__getitem__(index)


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_independent_canonical_readback(directory, phase):
    native = _load(directory / "canonical-result.json")
    core = _isolated_core(directory / "runtime")
    turns = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == (1 if phase == "seed" else 2)
    assert turns[-1].request_content == (SEED_QUERY if phase == "seed" else FOLLOWUP_QUERY)
    assert turns[-1].response_text == native["response_text"]
    assert all(turn.user_id == "user://local_operator" for turn in turns)
    events = core.observability_service.repository.list_events(
        session_id=SESSION, event_names=("response_synthesized",), limit=10,
    )
    request = max(events, key=lambda event: event.timestamp)
    exported = export_conversation(
        memory_db=directory / "runtime" / "memory.db",
        events_db=directory / "runtime" / "events.db", session_id=SESSION,
        request_id=request.request_id, principal_ref="user://local_operator",
        authorized=True, include_content=True,
    )
    assert exported["response_text"] == turns[-1].response_text
    assert exported["query"] == turns[-1].request_content
    annex = native["response_text"].partition(GENERATIVE_ANALYSIS_MARKER)[2]
    analyses = [json.loads(line.removeprefix("Analysis: "))
                for line in annex.splitlines() if line.startswith("Analysis: ")]
    expected_label = "not-available" if phase == "control" else PREFERENCE
    expected_count, expected_latency = (12, 180) if phase == "seed" else (13, 170)
    assert analyses == [f"Response label: {expected_label}. Reviewed items: {expected_count}; "
                        f"p95: {expected_latency}ms."]
    for resource_id, text in SEED_REPORTS if phase == "seed" else REVISED_REPORTS:
        assert (directory / (resource_id + ".txt")).read_text(encoding="utf-8") == text
        assert PREFERENCE not in text
    budget = _load(directory / "budget.json")
    assert budget["attempted_model_calls"] == budget["completed_model_calls"] == 3
    assert native["operation_dispatched"] is False
    assert native["real_model_verified"] is native["local_weights_verified"] is False
    assert native["account_used"] is False


def test_reusable_driver_records_two_complete_arms_and_all_eighteen_scripted_requests(tmp_path):
    directory = tmp_path / "experiment"
    peer = _DriverPeer()
    with _server(peer, model=MODEL) as (server, endpoint):
        peer.requests = server.requests
        result = lab.run_local_experiment(directory=directory, endpoint=endpoint, model=MODEL,
                                          authorized=True, upstream_egress_acknowledged=True)
        assert len(server.requests) == result["attempted_inferences"] == 18
        assert result["status"] == "recorded"
        assert result["comparison"]["comparison_status"] == "complete"
        assert result["sequential_order"] == ["jarvis_structured", "hermes_context"]
        assert all(arm["all_checks_passed"] is True for arm in result["arms"])
        assert all(arm["inference_attempts"] == 9 for arm in result["arms"])
        assert result["automatic_retry"] is result["paid_fallback"] is False
        assert result["warmup_calls"] == 0 and result["max_inference_attempts"] == 24
        assert result["improvement_claim"] is result["real_model_verified"] is False
        assert result["residency_controlled"] is result["runtime_capability_promoted"] is False
        assert result["corpus_digest"] == PUBLIC_CASE_DIGEST
        assert _load(directory / "comparison.json") == result
        manifest = _load(directory / "manifest.json")
        assert manifest["status"] == "preflight" and manifest["attempted_inferences"] == 0

        calls = _load(directory / "inferences.json")
        assert [call["attempt"] for call in calls] == list(range(1, 19))
        assert all(call["status"] == "completed" and call["error_code"] is None for call in calls)
        assert all(0 < call["timeout_ms"] <= 120000 for call in calls)
        assert [call["observations"] for call in calls] == [0, 1, 2] * 6
        assert [call["history_pairs"] for call in calls] == ([0] * 3 + [1] * 3 + [0] * 3) * 2
        assert all(call["phase_diagnostics"] for call in calls)
        for index, request in enumerate(server.requests):
            payload, queries, form = _wire_input(request[2])
            phase = ("seed", "memory", "control")[(index % 9) // 3]
            assert request[2]["model"] == MODEL
            assert request[2]["response_format"]["type"] == "json_schema"
            assert form == ("jarvis_structured" if index < 9 else "hermes_context")
            assert payload["query"] == (SEED_QUERY if phase == "seed" else FOLLOWUP_QUERY)
            if phase == "control":
                assert len(queries) == 1 and PREFERENCE not in json.dumps(request[2])
            if phase == "memory":
                assert len(queries) == 2 and PREFERENCE in queries[0]
                assert PREFERENCE not in queries[-1]

    snapshots = _load(directory / "snapshots.json")
    assert len(snapshots) == 4
    for name in ("jarvis_structured", "hermes_context"):
        arm_snapshots = [item for item in snapshots if item["arm"] == name]
        assert [item["phase"] for item in arm_snapshots] == ["memory", "control"]
        assert arm_snapshots[0]["database_sha256"] == arm_snapshots[1]["database_sha256"]
        assert all(len(digest) == 64 for digest in arm_snapshots[0]["database_sha256"])
        for phase in ("seed", "memory", "control"):
            _assert_independent_canonical_readback(directory / name / phase, phase)
    before = {path.relative_to(directory): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in directory.rglob("*") if path.is_file()}
    with pytest.raises(FileExistsError):
        lab.run_local_experiment(directory=directory, endpoint=endpoint, model=MODEL,
                                 authorized=True, upstream_egress_acknowledged=True)
    after = {path.relative_to(directory): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in directory.rglob("*") if path.is_file()}
    assert before == after


def test_first_arm_failure_stops_that_arm_without_retry_and_records_partial_comparison(tmp_path):
    directory = tmp_path / "experiment"
    peer = _FirstArmFaultPeer()
    with _server(peer, model=MODEL) as (server, endpoint):
        peer.requests = server.requests
        result = lab.run_local_experiment(directory=directory, endpoint=endpoint, model=MODEL,
                                          authorized=True, upstream_egress_acknowledged=True)
        assert len(server.requests) == result["attempted_inferences"] == 10
    baseline, candidate = result["arms"]
    assert baseline["stopped_after"] == "seed" and baseline["all_checks_passed"] is False
    assert baseline["inference_attempts"] == 1
    assert candidate["all_checks_passed"] is True and candidate["inference_attempts"] == 9
    assert result["comparison"]["comparison_status"] == "partial"
    assert result["improvement_claim"] is False
    assert not (directory / "jarvis_structured" / "memory").exists()
    assert not (directory / "jarvis_structured" / "control").exists()
    calls = _load(directory / "inferences.json")
    assert [(call["arm"], call["phase"]) for call in calls[:2]] == [
        ("jarvis_structured", "seed"), ("hermes_context", "seed"),
    ]
