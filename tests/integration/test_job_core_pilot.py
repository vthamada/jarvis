"""Actual Core + SQLite ledger; interruption tests keep already persisted memory."""

import io
import json
import socket
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from job_service import FixtureJobWorker, JobSpec, JobStoreError, SqliteJobStore
from job_service.store import CORE_TASK

from apps.jarvis_console import job_pilot
from apps.jarvis_console.job_pilot import (
    CoreJobInput,
    CoreJobRunner,
    _isolated_core,
    run_job_core_pilot,
)
from shared.types import PermissionDecision


@pytest.fixture
def setup(tmp_path):
    now = [datetime.now(UTC)]
    store = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: now[0])
    request = CoreJobInput("local-pilot", "isolated-job-pilot", "acknowledgement")
    store.register(
        JobSpec(
            "job-1",
            request.actor_ref,
            request.session_ref,
            "core-assist-pilot",
            request.step_ref,
            CORE_TASK,
            now[0] + timedelta(minutes=10),
            1,
        )
    )
    core = _isolated_core(tmp_path)
    runner = CoreJobRunner(store, core, "worker-1")
    return store, core, runner, request, now


def scope(request):
    return {"actor_ref": request.actor_ref, "session_ref": request.session_ref}


def test_actual_pipeline_retains_core_decision_and_private_canonical_final(setup, monkeypatch):
    store, core, runner, request, _ = setup
    contracts = []
    original = core.handle_input

    def handle(contract):
        contracts.append(contract)
        return original(contract)

    monkeypatch.setattr(core, "handle_input", handle)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-never-open")
    monkeypatch.setattr(socket.socket, "connect", lambda *args: pytest.fail("network refused"))
    result = runner.run_once("job-1", request, expected_version=0)
    assert result["core_invoked"] and result["canonical_final_verified"]
    assert result["result_recorded"] and result["core_event_count"] > 0
    assert result["request_id"] and result["memory_record_id"]
    assert not result["operation_dispatched"]
    assert not result["cross_ledger_atomic"] and not result["exactly_once_claimed"]
    assert not result["operator_authenticated"] and not result["action_authority"]
    contract = contracts[0]
    assert contract.content == request.text
    assert contract.canonical_user_ref == f"user://{request.actor_ref}"
    assert contract.surface_session_id == request.core_session_id
    assert contract.user_id == contract.canonical_user_ref == f"user://{request.actor_ref}"
    assert not contract.surface_capability_scope
    assert contract.max_autonomy_level == contract.requested_autonomy_level == "assist_only"
    assert contract.action_confirmation_receipt_id is None
    turns = core.memory_service.repository.fetch_recent_turns(contract.session_id, 5)
    assert len(turns) == 1 and turns[0].request_content == request.text
    assert turns[0].response_text not in json.dumps(result)
    assert request.text not in json.dumps(result)
    # Completion of the Core pipeline is not approval of its deferred decision.
    assert result["job"]["status"] == (
        "succeeded" if result["governance_decision"] == "allow" else "needs_decision"
    )
    second = runner.run_once("job-1", request, expected_version=result["job"]["version"])
    assert not second["core_invoked"] and len(contracts) == 1
    assert store.get("job-1", **scope(request)).attempts == 1


@pytest.mark.parametrize("mutation", ["cancel", "pause", "expire"])
def test_interruption_after_real_core_persistence_discards_ledger_success(
    setup, monkeypatch, mutation
):
    store, core, runner, request, now = setup
    original = core.handle_input

    def handle(contract):
        response = original(contract)
        # Real canonical memory is already committed before the ledger mutation.
        assert len(core.memory_service.repository.fetch_recent_turns(contract.session_id, 5)) == 1
        if mutation == "expire":
            now[0] += timedelta(seconds=120)
        else:
            getattr(store, mutation)("job-1", expected_version=1, **scope(request))
        return response

    monkeypatch.setattr(core, "handle_input", handle)
    result = runner.run_once("job-1", request, expected_version=0)
    assert result["canonical_final_verified"] and result["memory_record_id"]
    assert not result["result_recorded"] and not result["result_accepted"]
    assert result["review_required"]
    assert result["job"]["status"] == ("cancelled" if mutation == "cancel" else "needs_decision")
    second = runner.run_once("job-1", request, expected_version=result["job"]["version"])
    assert not second["core_invoked"]
    assert len(core.memory_service.repository.fetch_recent_turns(request.core_session_id, 5)) == 1


def test_exception_after_canonical_commit_is_not_retried(setup, monkeypatch):
    store, core, runner, request, _ = setup
    original = core.handle_input

    def handle(contract):
        original(contract)
        raise RuntimeError("must not leak private payload")

    monkeypatch.setattr(core, "handle_input", handle)
    result = runner.run_once("job-1", request, expected_version=0)
    assert result["job"]["status"] == "needs_decision" and result["review_required"]
    assert "private payload" not in json.dumps(result)
    assert len(core.memory_service.repository.fetch_recent_turns(request.core_session_id, 5)) == 1
    with pytest.raises(JobStoreError, match="core_replay_refused"):
        store.retry("job-1", expected_version=2, **scope(request))


@pytest.mark.parametrize("mutation", ["text", "governance", "memory_id"])
def test_tampered_final_does_not_become_job_success(setup, monkeypatch, mutation):
    _, core, runner, request, _ = setup
    original = core.handle_input

    def handle(contract):
        response = original(contract)
        if mutation == "text":
            return replace(response, response_text="substituted noncanonical final")
        if mutation == "governance":
            return replace(
                response,
                governance_decision=replace(
                    response.governance_decision,
                    decision=PermissionDecision.ALLOW,
                ),
            )
        return replace(
            response,
            memory_record=replace(
                response.memory_record,
                memory_record_id="forged-record",
            ),
        )

    monkeypatch.setattr(core, "handle_input", handle)
    result = runner.run_once("job-1", request, expected_version=0)
    assert not result["canonical_final_verified"]
    assert not result["result_recorded"]
    assert result["job"]["status"] == "needs_decision"


@pytest.mark.parametrize("field", ["actor_ref", "session_ref", "case"])
def test_exact_binding_refuses_before_claim_and_core(setup, monkeypatch, field):
    store, core, runner, request, _ = setup
    monkeypatch.setattr(core, "handle_input", lambda _: pytest.fail("must not enter Core"))
    changed = replace(request, **{field: "arithmetic" if field == "case" else "other"})
    with pytest.raises(JobStoreError, match="job_unavailable|core_input_binding_refused"):
        runner.run_once("job-1", changed, expected_version=0)
    assert store.get("job-1", **scope(request)).attempts == 0


@pytest.mark.parametrize("operation", ["cancel", "pause"])
def test_stop_before_claim_never_calls_core(setup, monkeypatch, operation):
    store, core, runner, request, _ = setup
    monkeypatch.setattr(core, "handle_input", lambda _: pytest.fail("must not enter Core"))
    stopped = getattr(store, operation)("job-1", expected_version=0, **scope(request))
    result = runner.run_once("job-1", request, expected_version=stopped.version)
    assert not result["core_invoked"] and result["job"]["attempts"] == 0


def test_fixture_worker_cannot_claim_core_job(setup):
    store, _, _, request, _ = setup
    with pytest.raises(JobStoreError, match="fixture_worker_core_refused"):
        FixtureJobWorker(store, "fixture-worker").run_once(
            "job-1", expected_version=0, **scope(request)
        )
    assert store.get("job-1", **scope(request)).attempts == 0


def test_cli_composition_real_core_temp_reopen_does_not_promote():
    result = run_job_core_pilot("arithmetic", authorized=True)
    assert result["canonical_final_verified"] and result["result_recorded"]
    assert result["restart_status"] == result["job"]["status"]
    assert result["runtime_mode"] == "temporary_sqlite"
    assert not result["production_memory_opened"] and not result["automatic_execution"]
    assert not result["runtime_capability_promoted"]


def test_closed_composition_rejects_callable_and_arbitrary_input(setup):
    store, _, _, _, _ = setup
    with pytest.raises(JobStoreError, match="invalid_core_composition"):
        CoreJobRunner(store, lambda _: "success", "worker")
    with pytest.raises(JobStoreError, match="unsupported_core_case"):
        CoreJobInput("actor", "session", "arbitrary user prompt")


@pytest.mark.parametrize(
    "stdin",
    [
        "{",
        "[]",
        '{"case":"arbitrary prompt"}',
        '{"case":"arithmetic","secret":"value"}',
        "x" * 1025,
    ],
)
def test_cli_invalid_stdin_refuses_without_private_echo(monkeypatch, capsys, stdin):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    assert job_pilot.main(["--authorized"]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "refused",
        "reason": "job_pilot_unavailable",
    }


def test_core_port_never_turns_fixture_task_into_core_success(setup, monkeypatch):
    store, core, runner, request, now = setup
    store.register(
        JobSpec(
            "fixture-job",
            request.actor_ref,
            request.session_ref,
            "resp",
            "step",
            "fixture:success",
            now[0] + timedelta(minutes=1),
        )
    )
    monkeypatch.setattr(core, "handle_input", lambda _: pytest.fail("no Core for fixture"))
    with pytest.raises(JobStoreError, match="core_input_binding_refused"):
        runner.run_once("fixture-job", request, expected_version=0)
    assert store.get("fixture-job", **scope(request)).attempts == 0


def test_missing_opt_in_never_reads_stdin_or_constructs_core(monkeypatch, capsys):
    class Unreadable:
        def read(self, *_):
            pytest.fail("no stdin read before opt in")

    monkeypatch.setattr(sys, "stdin", Unreadable())
    monkeypatch.setattr(job_pilot, "_isolated_core", lambda _: pytest.fail("no Core before opt in"))
    assert job_pilot.main([]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "refused"
    for value in (False, None, 1, "true"):
        with pytest.raises(JobStoreError, match="pilot_opt_in_required"):
            run_job_core_pilot(authorized=value)


def test_two_actors_same_surface_session_get_distinct_canonical_memory(setup):
    store, core, runner, first, now = setup
    second = CoreJobInput("second-pilot", first.session_ref, "arithmetic")
    store.register(
        JobSpec(
            "second-job",
            second.actor_ref,
            second.session_ref,
            "core-assist-pilot",
            second.step_ref,
            CORE_TASK,
            now[0] + timedelta(minutes=10),
            1,
        )
    )
    result1 = runner.run_once("job-1", first, expected_version=0)
    result2 = runner.run_once("second-job", second, expected_version=0)
    assert result1["canonical_final_verified"] and result2["canonical_final_verified"]
    assert first.core_session_id != second.core_session_id
    for request in (first, second):
        turns = core.memory_service.repository.fetch_recent_turns(request.core_session_id, 10)
        assert len(turns) == 1 and turns[0].request_content == request.text
        assert turns[0].user_id == f"user://{request.actor_ref}"


def test_runtime_redirected_into_workspace_is_refused_before_creation(monkeypatch):
    workspace = job_pilot.Path(job_pilot.__file__).resolve().parents[2]
    monkeypatch.setattr(job_pilot.tempfile, "gettempdir", lambda: str(workspace))
    monkeypatch.setattr(
        job_pilot, "TemporaryDirectory", lambda **_: pytest.fail("no runtime creation in workspace")
    )
    monkeypatch.setattr(job_pilot, "_isolated_core", lambda _: pytest.fail("no Core in workspace"))
    with pytest.raises(JobStoreError, match="private_runtime_required"):
        run_job_core_pilot(authorized=True)
