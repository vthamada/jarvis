"""Real Core recall flow and fail-closed trusted-composition boundaries."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jarvis_console import memory_recall_pilot as pilot


def test_real_pilot_records_four_finals_but_does_not_claim_useful_recall(tmp_path, monkeypatch):
    builds = []
    build = pilot._isolated_core

    def tracked_build(runtime):
        assert runtime.parent == Path(pilot.tempfile.gettempdir()).resolve()
        core = build(runtime)
        builds.append((core, runtime))
        return core

    monkeypatch.setattr(pilot, "_isolated_core", tracked_build)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.chdir(tmp_path)
    report = pilot.run_memory_recall_pilot(authorized=True)
    cases = report["cases"]
    assert report["core_turn_count"] == 4
    assert report["evidence_mode"] == "core_local"
    assert report["runtime_mode"] == "temporary_sqlite"
    assert not report["operator_authenticated"]
    assert not report["runtime_capability_promoted"]
    assert not report["retention_mutation_performed"]
    assert cases["same_session"]["selection_before_turn"]["prior_session_turn_count"] == 1
    second = cases["new_session_same_subject"]["selection_before_turn"]
    assert second["prior_session_turn_count"] == 0
    assert second["prior_user_interaction_count"] == 2
    assert second["user_scope_status"] == "seeded"
    assert second["semantic_candidates"] == []
    other = cases["new_subject"]["selection_before_turn"]
    assert other["prior_user_interaction_count"] == 0
    assert other["user_memory_refs"] == ["memory://user/recall-pilot-beta"]
    for case in cases.values():
        assert case["memory_record_id"] and case["core_event_count"] >= 20
        assert case["final_matches_canonical_record"]
        assert not case["operation_dispatched"]
        assert not case["useful_continuity_demonstrated"]
        assert case["governance_decision"] == "defer_for_validation"
        assert case["recall_outcome"] == "persisted_tracking_only"
    assert all(not runtime.exists() for _, runtime in builds)
    assert not list(tmp_path.iterdir())
    encoded = json.dumps(report)
    for content in ("Plan an internal pilot", "response_text", "request_content", "summary="):
        assert content not in encoded


def test_opt_in_precedes_any_runtime_creation(monkeypatch):
    monkeypatch.setattr(pilot, "_isolated_core", lambda _: pytest.fail("opt-in bypass"))
    with pytest.raises(ValueError, match="opt_in_required"):
        pilot.run_memory_recall_pilot()


@pytest.mark.parametrize("relative", ["", "private-temp"])
def test_temp_base_in_workspace_is_refused_before_directory_or_core(relative, monkeypatch):
    workspace = Path(pilot.__file__).resolve().parents[2]
    monkeypatch.setattr(pilot.tempfile, "gettempdir", lambda: str(workspace / relative))
    monkeypatch.setattr(pilot, "TemporaryDirectory", lambda **_: pytest.fail("created unsafe TEMP"))
    monkeypatch.setattr(pilot, "_isolated_core", lambda _: pytest.fail("opened Core in workspace"))
    with pytest.raises(ValueError, match="temp_base_refused"):
        pilot.run_memory_recall_pilot(authorized=True)


@pytest.mark.parametrize(
    "changes",
    [
        {"user_id": "other"},
        {"canonical_user_ref": "user://other"},
        {"operator_identity_ref": "operator://other"},
        {"session_id": "other-session"},
        {"surface_session_id": "other-session"},
        {"mission_id": "unknown-mission"},
        {"surface_capability_scope": ["effect"]},
        {"max_autonomy_level": "bounded_core_action"},
    ],
)
def test_binding_drift_refused_before_core_or_memory(changes):
    context = pilot.PilotContext(pilot.SUBJECT, "safe-session", pilot.MISSION)
    core = SimpleNamespace(handle_input=lambda _: pytest.fail("drift reached Core"))
    with pytest.raises(ValueError, match="binding_drift"):
        pilot.RecallPilotPort(core, context).interact(
            replace(context.input("req", "safe"), **changes)
        )


def test_mission_owner_mismatch_is_not_retrieved():
    context = pilot.PilotContext("other-subject", "safe-session", pilot.MISSION)
    memory = SimpleNamespace(
        get_mission_state=lambda _: SimpleNamespace(
            mission_id=pilot.MISSION, owner_context=pilot.SUBJECT
        )
    )
    with pytest.raises(ValueError, match="mission_subject_mismatch"):
        pilot.RecallPilotPort(SimpleNamespace(memory_service=memory), context).inspect(
            context.input("req", "safe")
        )


def test_canonical_reference_drift_refused_before_core(tmp_path):
    core = pilot._isolated_core(tmp_path / "runtime")
    context = pilot.PilotContext(pilot.SUBJECT, "safe-session")
    contract = context.input("req", "safe")
    recovered = core.memory_service.recover_for_input(contract)
    recovered.user_scope_context.memory_refs.append("memory://user/other-subject")
    core.memory_service.recover_for_input = lambda _: recovered
    core.handle_input = lambda _: pytest.fail("ref drift reached Core")
    with pytest.raises(ValueError, match="user_ref_drift"):
        pilot.RecallPilotPort(core, context).interact(contract)


def test_candidate_reference_drift_is_not_explained_as_selection(tmp_path):
    core = pilot._isolated_core(tmp_path / "runtime")
    context = pilot.PilotContext(pilot.SUBJECT, "safe-session")
    contract = context.input("req", "safe")
    recovered = core.memory_service.recover_for_input(contract)
    recovered.semantic_memory_candidates.append(
        SimpleNamespace(
            anchor_ref="memory://mission/unowned/semantic",
            read_only=True,
            memory_write_allowed=False,
        )
    )
    core.memory_service.recover_for_input = lambda _: recovered
    with pytest.raises(ValueError, match="candidate_ref_drift"):
        pilot.RecallPilotPort(core, context).inspect(contract)


def test_wrong_core_final_is_not_delivery(tmp_path):
    core = pilot._isolated_core(tmp_path / "runtime")
    context = pilot.PilotContext(pilot.SUBJECT, "safe-session")
    handle = core.handle_input

    def wrong_final(contract):
        response = handle(contract)
        response.response_text += " altered outside synthesis"
        return response

    core.handle_input = wrong_final
    with pytest.raises(ValueError, match="canonical_final_refused"):
        pilot.RecallPilotPort(core, context).interact(context.input("req", "Explain the pilot."))


def test_cli_requires_opt_in_without_private_argv(monkeypatch):
    monkeypatch.setattr(
        pilot, "run_memory_recall_pilot", lambda **_: pytest.fail("ran without opt-in")
    )
    with pytest.raises(SystemExit) as result:
        pilot.main([])
    assert result.value.code == 2
