"""Real durable task/Core/SQLite recovery, including three abrupt process deaths.

No live model, network, Docker or arbitrary executor is involved. Fault injection
is limited to fixed dispatch/commit boundaries; authoritative behavior is real.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from job_service import JobStoreError
from job_service.durable import DurableCoreJobStore
from job_service.store import DURABLE_CORE_TASK

from apps.jarvis_console.durable_task_runner import DurableCoreJobRunner
from apps.jarvis_console.voice_pilot import _isolated_core

QUERY = "Compare documentation and observability pilot reports."
JOB = "private-durable-job"
SCOPE = {"actor_ref": "private-durable-actor", "session_ref": "private-durable-session"}
ROOT = Path(__file__).resolve().parents[2]
CRASH_HELPER = ROOT / "tests/support/durable_task_crash_fixture.py"
CRASH_EXIT = {"before_dispatch": 71, "after_dispatch": 72, "after_core_commit": 73}


def _register(tmp_path):
    runtime = tmp_path / "private-runtime"
    clock = [datetime.now(UTC)]
    store = DurableCoreJobStore(runtime / "jobs.db", clock=lambda: clock[0])
    snapshot = store.register_task(
        JOB, **SCOPE, input_text=QUERY, deadline=clock[0] + timedelta(minutes=10)
    )
    assert snapshot.spec.task_ref == DURABLE_CORE_TASK
    assert snapshot.spec.max_attempts == 1 and snapshot.attempts == 0
    return runtime, clock, store


def _reopen(runtime, clock, *, worker="restarted-worker"):
    store = DurableCoreJobStore(runtime / "jobs.db", clock=lambda: clock[0])
    core = _isolated_core(runtime)
    return store, core, DurableCoreJobRunner(store, core, worker)


def _run_crash(runtime, clock, stage):
    # A closed environment excludes account/provider configuration. Bootstrap is
    # from a verified repository helper, not PYTHONPATH or a shell-built command.
    environment = {
        key: value for key, value in os.environ.items()
        if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
    }
    environment.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONNOUSERSITE="1")
    completed = subprocess.run(
        [
            sys.executable, str(CRASH_HELPER), "--runtime", str(runtime),
            "--clock", clock[0].isoformat(), "--stage", stage, "--job-id", JOB,
            "--actor-ref", SCOPE["actor_ref"], "--session-ref", SCOPE["session_ref"],
        ],
        cwd=str(ROOT), env=environment, capture_output=True, timeout=30, check=False,
    )
    assert completed.returncode == CRASH_EXIT[stage], (
        "owned_crash_boundary_not_reached", stage, completed.returncode
    )
    assert completed.stdout == b"" and completed.stderr == b""


def _no_core(core, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("durable recovery replayed the sovereign Core")

    monkeypatch.setattr(core, "handle_input", forbidden)


def _expire_lease(store, clock):
    current = store.get(JOB, **SCOPE)
    assert current.lease_until is not None
    clock[0] = max(datetime.now(UTC), current.lease_until + timedelta(microseconds=1))


def _metadata(report, runtime, *, final_text=None):
    assert report["schema_version"] == "jarvis-durable-core-task-v1"
    for key in (
        "action_authority", "operator_authenticated", "automatic_execution",
        "exactly_once_claimed", "cross_ledger_atomic", "runtime_capability_promoted",
    ):
        assert report[key] is False
    serialized = json.dumps(report, default=str)
    for private in (QUERY, str(runtime), SCOPE["actor_ref"], SCOPE["session_ref"]):
        assert private not in serialized
    if final_text:
        assert final_text not in serialized


def _canonical(core, task):
    turns = core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10)
    assert len(turns) == 1
    assert turns[0].request_content == QUERY
    events = core.observability_service.repository.list_events(
        request_id=task.request_id, session_id=task.core_session_id, limit=100
    )
    final = [event for event in events if event.event_name == "response_synthesized"]
    memory = [event for event in events if event.event_name == "memory_recorded"]
    governance = [event for event in events if event.event_name == "governance_checked"]
    assert len(final) == len(memory) == len(governance) == 1
    return turns[0], memory[0].payload["memory_record_id"], governance[0].payload["decision"]


def _accepted(report, decision):
    assert report["canonical_final_verified"] is True
    assert report["result_recorded"] is True
    assert report["result_accepted"] is (decision == "allow")
    assert report["review_required"] is (decision != "allow")
    assert report["job"]["status"] == ("succeeded" if decision == "allow" else "needs_decision")
    assert report["checkpoint_phase"] == "completed"


def test_private_query_normal_flow_and_two_restarts_preserve_exact_canonical_final(
    tmp_path, monkeypatch
):
    runtime, clock, store = _register(tmp_path)
    core = _isolated_core(runtime)
    report = DurableCoreJobRunner(store, core, "first-worker").run_once(
        JOB, **SCOPE, expected_version=0, authorized=True
    )
    task = store.load_task(JOB, **SCOPE)
    turn, memory_id, decision = _canonical(core, task)
    assert report["core_invoked"] is True and report["recovered_result"] is False
    assert report["request_id"] == task.request_id
    assert report["memory_record_id"] == str(memory_id)
    _accepted(report, decision)
    _metadata(report, runtime, final_text=turn.response_text)
    assert QUERY.encode("utf-8") in (runtime / "jobs.db").read_bytes()
    original_claim = core.memory_service.repository.fetch_runtime_request_claim(task.request_id)
    assert original_claim is not None
    for index in range(2):
        reopened, fresh_core, runner = _reopen(runtime, clock, worker=f"reopen-{index}")
        _no_core(fresh_core, monkeypatch)
        current = reopened.get(JOB, **SCOPE)
        again = runner.resume(JOB, **SCOPE, expected_version=current.version, authorized=True)
        assert again["core_invoked"] is False and again["recovered_result"] is True
        assert again["evidence_mode"] == "canonical_recovery"
        _accepted(again, decision)
        _metadata(again, runtime, final_text=turn.response_text)
        retained, retained_memory_id, retained_decision = _canonical(fresh_core, task)
        assert asdict(retained) == asdict(turn)
        assert str(retained_memory_id) == str(memory_id) and retained_decision == decision
        assert asdict(fresh_core.memory_service.repository.fetch_runtime_request_claim(
            task.request_id
        )) == asdict(original_claim)


def test_real_crash_before_dispatch_allows_only_explicit_fenced_resume(tmp_path, monkeypatch):
    runtime, clock, _ = _register(tmp_path)
    _run_crash(runtime, clock, "before_dispatch")
    reopened, core, runner = _reopen(runtime, clock)
    task = reopened.load_task(JOB, **SCOPE)
    before = reopened.get(JOB, **SCOPE)
    assert task.phase == "prepared" and task.started_at is None
    assert before.status == "running" and before.attempts == 1
    assert core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10) == []
    assert core.memory_service.repository.fetch_runtime_request_claim(task.request_id) is None
    _expire_lease(reopened, clock)
    calls = []
    handle = core.handle_input

    def observed(contract):
        calls.append(contract)
        return handle(contract)

    monkeypatch.setattr(core, "handle_input", observed)
    report = runner.resume(JOB, **SCOPE, expected_version=before.version, authorized=True)
    assert len(calls) == 1 and report["core_invoked"] is True
    turn, _, decision = _canonical(core, task)
    _accepted(report, decision)
    assert report["job"]["attempts"] == 1
    assert report["job"]["fencing"] > before.fencing
    _metadata(report, runtime, final_text=turn.response_text)


def test_real_crash_after_dispatch_is_uncertain_and_never_replays_across_restarts(
    tmp_path, monkeypatch
):
    runtime, clock, initial_store = _register(tmp_path)
    _run_crash(runtime, clock, "after_dispatch")
    _expire_lease(initial_store, clock)
    for index in range(2):
        store, core, runner = _reopen(runtime, clock, worker=f"uncertain-{index}")
        _no_core(core, monkeypatch)
        task = store.load_task(JOB, **SCOPE)
        assert task.phase == ("started" if index == 0 else "uncertain")
        assert task.started_at is not None
        current = store.get(JOB, **SCOPE)
        report = runner.resume(JOB, **SCOPE, expected_version=current.version, authorized=True)
        assert report["core_invoked"] is False
        assert report["canonical_final_verified"] is False
        assert report["result_recorded"] is report["result_accepted"] is False
        assert report["review_required"] is True
        assert report["checkpoint_phase"] == "uncertain"
        assert report["job"]["status"] == "needs_decision"
        assert report["job"]["attempts"] == 1
        assert core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10) == []
        _metadata(report, runtime)


@pytest.mark.parametrize("after_deadline", [False, True])
def test_real_crash_after_core_commit_reconciles_receipt_without_another_core_call(
    tmp_path, monkeypatch, after_deadline
):
    runtime, clock, _ = _register(tmp_path)
    _run_crash(runtime, clock, "after_core_commit")
    reopened, core, runner = _reopen(runtime, clock)
    task = reopened.load_task(JOB, **SCOPE)
    assert task.phase == "started"
    turn, memory_id, decision = _canonical(core, task)
    original_claim = core.memory_service.repository.fetch_runtime_request_claim(task.request_id)
    assert original_claim is not None
    _no_core(core, monkeypatch)
    before = reopened.get(JOB, **SCOPE)
    busy = runner.resume(
        JOB, **SCOPE, expected_version=before.version, authorized=True
    )
    assert busy["core_invoked"] is busy["result_recorded"] is False
    assert busy["evidence_mode"] == "active_claim"
    assert reopened.get(JOB, **SCOPE) == before
    _metadata(busy, runtime, final_text=turn.response_text)
    if after_deadline:
        clock[0] = task.deadline + timedelta(seconds=1)
    else:
        _expire_lease(reopened, clock)
    current = reopened.get(JOB, **SCOPE)
    report = runner.resume(JOB, **SCOPE, expected_version=current.version, authorized=True)
    assert report["core_invoked"] is False and report["recovered_result"] is True
    assert report["memory_record_id"] == str(memory_id)
    assert report["evidence_mode"] == "canonical_recovery"
    _accepted(report, decision)
    _metadata(report, runtime, final_text=turn.response_text)
    second_store, second_core, second_runner = _reopen(runtime, clock, worker="second-recovery")
    _no_core(second_core, monkeypatch)
    again = second_runner.resume(
        JOB, **SCOPE, expected_version=second_store.get(JOB, **SCOPE).version, authorized=True
    )
    _accepted(again, decision)
    retained, _, _ = _canonical(second_core, task)
    assert asdict(retained) == asdict(turn)
    assert asdict(second_core.memory_service.repository.fetch_runtime_request_claim(
        task.request_id
    )) == asdict(original_claim)


def test_explicit_safe_resume_revokes_the_stale_predispatch_owner(tmp_path):
    runtime, clock, store = _register(tmp_path)
    old = store.claim_task(
        JOB, **SCOPE, worker_id="stale-owner", expected_version=0, lease_seconds=0.001
    )
    assert old is not None
    _expire_lease(store, clock)
    fresh_store, _, runner = _reopen(runtime, clock)
    report = runner.resume(JOB, **SCOPE, expected_version=old.version, authorized=True)
    assert report["core_invoked"] is True and report["job"]["attempts"] == 1
    assert report["job"]["fencing"] > old.fencing
    stable = fresh_store.get(JOB, **SCOPE)
    with pytest.raises(JobStoreError):
        store.start_dispatch(old)
    with pytest.raises(JobStoreError):
        store.finish_task(old, receipt_sha256="a" * 64, outcome="succeeded")
    assert fresh_store.get(JOB, **SCOPE) == stable


@pytest.mark.parametrize("operation", ["cancel", "pause"])
@pytest.mark.parametrize("has_receipt", [False, True])
def test_manual_stop_is_sticky_even_if_a_canonical_result_exists(
    tmp_path, monkeypatch, operation, has_receipt
):
    runtime, clock, _ = _register(tmp_path)
    _run_crash(runtime, clock, "after_core_commit" if has_receipt else "before_dispatch")
    store, core, runner = _reopen(runtime, clock)
    task = store.load_task(JOB, **SCOPE)
    current = store.get(JOB, **SCOPE)
    stopped = getattr(store, operation)(JOB, **SCOPE, expected_version=current.version)
    clock[0] += timedelta(seconds=3)
    _no_core(core, monkeypatch)
    report = runner.resume(JOB, **SCOPE, expected_version=stopped.version, authorized=True)
    assert report["core_invoked"] is False
    assert report["result_recorded"] is report["result_accepted"] is False
    assert report["review_required"] is True
    assert report["job"]["status"] == ("cancelled" if operation == "cancel" else "needs_decision")
    assert store.get(JOB, **SCOPE).version == stopped.version
    turns = core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10)
    assert len(turns) == int(has_receipt)
    _metadata(report, runtime, final_text=turns[0].response_text if turns else None)


def test_expired_prepared_task_does_not_dispatch(tmp_path, monkeypatch):
    runtime, clock, store = _register(tmp_path)
    task = store.load_task(JOB, **SCOPE)
    clock[0] = task.deadline + timedelta(seconds=1)
    _, core, runner = _reopen(runtime, clock)
    _no_core(core, monkeypatch)
    report = runner.resume(JOB, **SCOPE, expected_version=0, authorized=True)
    assert report["core_invoked"] is False
    assert report["result_recorded"] is report["result_accepted"] is False
    assert report["review_required"] is True
    assert report["job"]["status"] == "expired"
    assert report["job"]["attempts"] == 0
    assert core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10) == []


@pytest.mark.parametrize("method", ["run_once", "resume"])
@pytest.mark.parametrize("authorized", [False, None, 1, "true"])
def test_opt_in_is_required_before_loading_or_dispatching_any_task(
    tmp_path, monkeypatch, method, authorized
):
    runtime, _, store = _register(tmp_path)
    core = _isolated_core(runtime)
    runner = DurableCoreJobRunner(store, core, "unauthorized-worker")
    _no_core(core, monkeypatch)

    def forbidden(*_args, **_kwargs):
        pytest.fail("durable task was accessed before explicit opt-in")

    for name in ("get", "load_task", "claim_task", "start_dispatch"):
        monkeypatch.setattr(store, name, forbidden)
    with pytest.raises(JobStoreError):
        getattr(runner, method)(JOB, **SCOPE, expected_version=0, authorized=authorized)


@pytest.mark.parametrize("changed", ["actor_ref", "session_ref"])
def test_different_scope_cannot_load_or_resume_the_private_input(tmp_path, monkeypatch, changed):
    runtime, clock, store = _register(tmp_path)
    _, core, runner = _reopen(runtime, clock)
    _no_core(core, monkeypatch)
    different = {**SCOPE, changed: "foreign-scope"}
    with pytest.raises(JobStoreError):
        runner.resume(JOB, **different, expected_version=0, authorized=True)
    assert store.get(JOB, **SCOPE).attempts == 0
    assert store.load_task(JOB, **SCOPE).phase == "prepared"


@pytest.mark.parametrize("configured", ["model_tool_loop", "generative_port", "extractive_port"])
def test_non_native_configuration_is_refused_before_claim_or_core(
    tmp_path, monkeypatch, configured
):
    runtime, clock, store = _register(tmp_path)
    _, core, runner = _reopen(runtime, clock)
    _no_core(core, monkeypatch)
    if configured == "model_tool_loop":
        core.model_tool_loop = object()
    else:
        field = "_generative_port" if configured == "generative_port" else "_inference_port"
        monkeypatch.setattr(core.synthesis_engine, field, object())
    with pytest.raises(JobStoreError, match="durable_native_only"):
        runner.run_once(JOB, **SCOPE, expected_version=0, authorized=True)
    assert store.get(JOB, **SCOPE).attempts == 0
    assert store.load_task(JOB, **SCOPE).phase == "prepared"


@pytest.mark.parametrize("boundary", ["registered", "claimed", "canonical_commit"])
def test_actual_checkpoint_input_drift_is_refused_without_redispatch_or_receipt_rebinding(
    tmp_path, monkeypatch, boundary
):
    runtime, clock, store = _register(tmp_path)
    expected_attempts = 0
    expected_phase = "prepared"
    if boundary == "claimed":
        store.claim_task(JOB, **SCOPE, worker_id="first-owner", expected_version=0)
        expected_attempts = 1
    elif boundary == "canonical_commit":
        _run_crash(runtime, clock, "after_core_commit")
        expected_attempts = 1
        expected_phase = "started"
    before = store.get(JOB, **SCOPE)
    substituted = "PRIVATE_SUBSTITUTED_QUERY_SENTINEL: Compare unrelated reports."
    with closing(sqlite3.connect(runtime / "jobs.db")) as connection:
        with connection:
            connection.execute(
                "UPDATE durable_core_tasks SET input_text=? WHERE job_id=?", (substituted, JOB)
            )
    _, core, runner = _reopen(runtime, clock)
    _no_core(core, monkeypatch)
    with pytest.raises(JobStoreError) as rejected:
        runner.resume(JOB, **SCOPE, expected_version=before.version, authorized=True)
    assert substituted not in str(rejected.value)
    assert str(runtime) not in str(rejected.value)
    with closing(sqlite3.connect(runtime / "jobs.db")) as connection:
        row = connection.execute(
            "SELECT attempts FROM fixture_jobs WHERE job_id=?", (JOB,)
        ).fetchone()
        phase = connection.execute(
            "SELECT phase FROM durable_core_tasks WHERE job_id=?", (JOB,)
        ).fetchone()
    assert row == (expected_attempts,) and phase == (expected_phase,)


def test_input_drift_after_dispatch_marker_is_refused_at_last_check_before_core(
    tmp_path, monkeypatch
):
    runtime, _, store = _register(tmp_path)
    task = store.load_task(JOB, **SCOPE)
    core = _isolated_core(runtime)
    runner = DurableCoreJobRunner(store, core, "last-check-worker")
    _no_core(core, monkeypatch)
    start_dispatch = store.start_dispatch
    markers = []
    substituted = "PRIVATE_LAST_BOUNDARY_DRIFT_SENTINEL: Compare other reports."

    def mark_then_change_input(claim):
        started = start_dispatch(claim)
        markers.append(started)
        with closing(sqlite3.connect(runtime / "jobs.db")) as connection:
            with connection:
                connection.execute(
                    "UPDATE durable_core_tasks SET input_text=? WHERE job_id=?",
                    (substituted, JOB),
                )
        return started

    monkeypatch.setattr(store, "start_dispatch", mark_then_change_input)
    with pytest.raises(JobStoreError) as rejected:
        runner.run_once(JOB, **SCOPE, expected_version=0, authorized=True)
    assert len(markers) == 1 and markers[0].phase == "started"
    assert substituted not in str(rejected.value) and str(runtime) not in str(rejected.value)
    assert core.memory_service.repository.fetch_runtime_request_claim(task.request_id) is None
    assert core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10) == []
    with closing(sqlite3.connect(runtime / "jobs.db")) as connection:
        row = connection.execute(
            "SELECT attempts FROM fixture_jobs WHERE job_id=?", (JOB,)
        ).fetchone()
        phase = connection.execute(
            "SELECT phase,started_at FROM durable_core_tasks WHERE job_id=?", (JOB,)
        ).fetchone()
    assert row == (1,)
    assert phase[0] == "started" and phase[1] is not None
