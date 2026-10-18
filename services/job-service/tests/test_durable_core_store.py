"""Opt-in dispatch journal: no model, account, scheduler or Core execution."""

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta

import pytest
from job_service import FixtureJobWorker, JobStoreError, SqliteJobStore
from job_service.durable import (
    DurableCoreJobStore,
    durable_request_id,
    durable_session_id,
)
from job_service.store import DURABLE_CORE_TASK

SCOPE = {"actor_ref": "actor", "session_ref": "session"}
INPUT = "Compare the documentation and observability reports."
RECEIPT = "c" * 64


@pytest.fixture
def state(tmp_path):
    now = [datetime(2026, 10, 16, 12, tzinfo=UTC)]
    path = tmp_path / "jobs.db"
    store = DurableCoreJobStore(path, clock=lambda: now[0])
    return store, now, path


def register(state, **patch):
    store, now, _ = state
    values = {"input_text": INPUT, "deadline": now[0] + timedelta(minutes=10), **SCOPE}
    values.update(patch)
    return store.register_task("job", **values)


def claim(store, version=0, **patch):
    values = {"worker_id": "worker", "expected_version": version, **SCOPE}
    values.update(patch)
    return store.claim_task("job", **values)


def task(store):
    return store.load_task("job", **SCOPE)


def snapshot(store):
    return store.get("job", **SCOPE)


def sql(path, statement, values=()):
    with sqlite3.connect(path) as db:
        db.execute(statement, values)


def test_final_claim_validation_rechecks_checkpoint_binding_after_start(state):
    store, _, path = state
    register(state)
    active = claim(store)
    store.start_dispatch(active)
    sql(path, "UPDATE durable_core_tasks SET input_text=? WHERE job_id='job'", ("drift",))
    with pytest.raises(JobStoreError, match="durable_binding_mismatch"):
        store.validate_claim(active)


def test_fractional_lease_roundtrips_without_false_claim_conflict(state):
    store, now, _ = state
    now[0] = now[0].replace(microsecond=2)
    register(state)
    active = claim(store, lease_seconds=0.001)
    store.start_dispatch(active)
    assert store.validate_claim(active).status == "running"


def test_default_schema_remains_v1_without_opt_in_journal(tmp_path):
    path = tmp_path / "jobs.db"
    SqliteJobStore(path)
    with sqlite3.connect(path) as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert names == {"fixture_jobs"}
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
    DurableCoreJobStore(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM durable_core_tasks").fetchone()[0] == 0


def test_registration_immutable_ids_and_metadata_only_projection(state):
    store, now, path = state
    first = register(state)
    loaded = task(store)
    digest = hashlib.sha256(INPUT.encode()).hexdigest()
    expected_request_digest = hashlib.sha256(json.dumps({
        "job_id": "job", "actor_ref": "actor", "session_ref": "session", "input_sha256": digest,
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert loaded.request_id == "durable-job-" + expected_request_digest
    assert loaded.request_id == durable_request_id("job", "actor", "session", digest)
    assert loaded.core_session_id == durable_session_id("actor", "session")
    assert loaded.input_text == INPUT and loaded.input_sha256 == digest
    assert loaded.deadline == now[0] + timedelta(minutes=10)
    assert loaded.phase == "prepared" and loaded.started_at is None
    assert loaded.receipt_sha256 is None and len(loaded.binding_sha256) == 64
    assert first.spec.task_ref == DURABLE_CORE_TASK and first.spec.max_attempts == 1
    assert first.spec.responsibility_ref == "core-durable-task"
    assert first.spec.approved_step_ref == "input-" + digest
    assert INPUT not in repr(loaded)
    assert register(state) == first
    assert task(DurableCoreJobStore(path, clock=lambda: now[0])) == loaded
    assert snapshot(store).version == 0
    telemetry = first.telemetry()
    assert telemetry["event"] == "job_state" and telemetry["evidence_mode"] == "metadata_ledger"
    assert not telemetry["action_authority"] and not telemetry["automatic_execution"]
    assert INPUT not in repr(telemetry) and digest not in repr(telemetry)
    with pytest.raises(FrozenInstanceError):
        loaded.input_text = "changed"
    with pytest.raises(JobStoreError, match="registration_conflict"):
        register(state, input_text=INPUT + " altered")
    assert task(store) == loaded


@pytest.mark.parametrize("text", [None, "", "  ", "x" * 2049, "é" * 1025, "\ud800"])
def test_input_is_bounded_utf8_before_any_registration(state, text):
    store, _, path = state
    with pytest.raises(JobStoreError, match="invalid_durable_input"):
        register(state, input_text=text)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM fixture_jobs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM durable_core_tasks").fetchone()[0] == 0
    with pytest.raises(JobStoreError, match="job_unavailable"):
        task(store)


@pytest.mark.parametrize("patch", [
    {"actor_ref": "private identity"}, {"session_ref": "../escape"},
    {"deadline": datetime(2026, 10, 16)},
])
def test_closed_registration_contract(state, patch):
    with pytest.raises(JobStoreError):
        register(state, **patch)


def test_2048_utf8_bytes_are_allowed(state):
    store, _, _ = state
    register(state, input_text="é" * 1024)
    assert len(task(store).input_text.encode("utf-8")) == 2048


def test_registration_rolls_back_job_when_journal_write_fails(state):
    _, _, path = state
    sql(path, """CREATE TRIGGER refuse_payload BEFORE INSERT ON durable_core_tasks
        BEGIN SELECT RAISE(ABORT, 'private database failure'); END""")
    with pytest.raises(JobStoreError, match="^storage_unavailable$"):
        register(state)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM fixture_jobs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM durable_core_tasks").fetchone()[0] == 0


def test_base_apis_and_fixture_worker_cannot_dispatch_new_task(state, monkeypatch):
    store, now, path = state
    register(state)
    base = SqliteJobStore(path, clock=lambda: now[0])
    with pytest.raises(JobStoreError, match="durable_core_api_required"):
        base.claim("job", worker_id="worker", expected_version=0, **SCOPE)
    with pytest.raises(JobStoreError, match="durable_core_replay_refused"):
        base.retry("job", expected_version=0, **SCOPE)

    def forbidden(*args, **kwargs):
        raise AssertionError("fixture must refuse before claim")

    monkeypatch.setattr(base, "claim", forbidden)
    with pytest.raises(JobStoreError, match="fixture_worker_core_refused"):
        FixtureJobWorker(base, "fixture").run_once("job", expected_version=0, **SCOPE)
    active = claim(store)
    with pytest.raises(JobStoreError, match="durable_core_api_required"):
        base.finish(active, "succeeded")
    assert snapshot(store).status == "running"


def test_reopen_prepared_transfer_is_same_attempt_and_fences_old_claim(state):
    store, now, path = state
    register(state)
    old = claim(store, lease_seconds=1)
    now[0] += timedelta(seconds=1)
    reopened = DurableCoreJobStore(path, clock=lambda: now[0])
    assert snapshot(reopened).version == 1 and task(reopened).phase == "prepared"
    active = claim(reopened, 1, worker_id="other")
    assert (active.version, active.fencing) == (2, 2)
    assert snapshot(reopened).attempts == 1
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.start_dispatch(old)
    started = reopened.start_dispatch(active)
    assert started.phase == "started" and started.started_at == now[0]
    assert snapshot(reopened).version == active.version
    with pytest.raises(JobStoreError, match="dispatch_already_started"):
        reopened.start_dispatch(active)
    completed = reopened.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")
    assert completed.status == "succeeded" and completed.attempts == 1
    assert task(reopened).receipt_sha256 == RECEIPT
    assert task(reopened).phase == "completed"
    with pytest.raises(JobStoreError):
        reopened.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")


def test_two_stores_atomic_claim_have_one_winner(state):
    store, now, path = state
    register(state)
    other = DurableCoreJobStore(path, clock=lambda: now[0])

    def attempt(pair):
        item, worker = pair
        try:
            return claim(item, worker_id=worker)
        except JobStoreError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [(store, "one"), (other, "two")]))
    assert sum(not isinstance(result, str) for result in results) == 1
    assert "version_conflict" in results
    assert snapshot(store).attempts == 1


def test_started_dispatch_is_never_replayed_after_lease_or_host_restart(state):
    store, now, path = state
    register(state)
    active = claim(store, lease_seconds=1)
    store.start_dispatch(active)
    now[0] += timedelta(seconds=2)
    reopened = DurableCoreJobStore(path, clock=lambda: now[0])
    assert claim(reopened, 1, worker_id="other") is None
    assert snapshot(reopened).version == 1 and task(reopened).phase == "started"
    with pytest.raises(JobStoreError, match="claim_expired"):
        reopened.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")
    reconciled = reopened.reconcile_task(
        "job", expected_version=1, receipt_sha256=RECEIPT, outcome="succeeded", **SCOPE,
    )
    assert reconciled.status == "succeeded" and reconciled.fencing == 2
    assert task(reopened).receipt_sha256 == RECEIPT


def test_uncertain_revokes_claim_and_reconciles_without_dispatch(state):
    store, now, _ = state
    register(state)
    active = claim(store, lease_seconds=1)
    store.start_dispatch(active)
    now[0] += timedelta(seconds=2)
    uncertain = store.mark_uncertain(active)
    assert (uncertain.status, uncertain.fencing, uncertain.version) == ("needs_decision", 2, 2)
    assert task(store).phase == "uncertain"
    assert claim(store, 2, worker_id="other") is None
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.mark_uncertain(active)
    final = store.reconcile_task(
        "job", expected_version=2, receipt_sha256=RECEIPT, outcome="failed", **SCOPE,
    )
    assert final.status == "failed" and task(store).phase == "completed"


@pytest.mark.parametrize("phase", ["prepared", "started", "uncertain"])
def test_cancelled_scope_never_dispatches_finishes_or_reconciles(state, phase):
    store, _, _ = state
    register(state)
    active = claim(store)
    if phase != "prepared":
        store.start_dispatch(active)
    if phase == "uncertain":
        store.mark_uncertain(active)
    cancelled = store.cancel("job", expected_version=snapshot(store).version, **SCOPE)
    assert claim(store, cancelled.version) is None
    with pytest.raises(JobStoreError):
        store.start_dispatch(active)
    with pytest.raises(JobStoreError):
        store.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")
    with pytest.raises(JobStoreError, match="invalid_reconcile_state"):
        store.reconcile_task("job", expected_version=cancelled.version,
                             receipt_sha256=RECEIPT, outcome="succeeded", **SCOPE)
    assert snapshot(store) == cancelled


def test_manual_pause_started_is_not_uncertain_and_cannot_reconcile(state):
    store, now, _ = state
    register(state)
    active = claim(store, lease_seconds=1)
    store.start_dispatch(active)
    paused = store.pause("job", expected_version=1, **SCOPE)
    assert task(store).phase == "started"
    now[0] += timedelta(minutes=20)
    with pytest.raises(JobStoreError, match="invalid_reconcile_state"):
        store.reconcile_task("job", expected_version=paused.version,
                             receipt_sha256=RECEIPT, outcome="succeeded", **SCOPE)
    assert claim(store, paused.version) is None and snapshot(store) == paused


def test_deadline_expires_only_unstarted_task_and_reconciliation_can_be_later(state):
    store, now, _ = state
    register(state, deadline=now[0] + timedelta(seconds=1))
    now[0] += timedelta(seconds=1)
    assert claim(store) is None
    assert snapshot(store).status == "expired" and snapshot(store).attempts == 0
    with pytest.raises(JobStoreError, match="invalid_reconcile_state"):
        store.reconcile_task("job", expected_version=1,
                             receipt_sha256=RECEIPT, outcome="succeeded", **SCOPE)


def test_reconciliation_after_deadline_records_receipt_without_reclaim(state):
    store, now, _ = state
    register(state, deadline=now[0] + timedelta(seconds=2))
    active = claim(store)
    store.start_dispatch(active)
    now[0] += timedelta(minutes=20)
    assert claim(store, 1) is None
    final = store.reconcile_task("job", expected_version=1, receipt_sha256=RECEIPT,
                                outcome="succeeded", **SCOPE)
    assert final.status == "succeeded" and final.attempts == 1


def test_finish_requires_start_and_reconciliation_requires_expired_lease(state):
    store, _, _ = state
    register(state)
    active = claim(store)
    with pytest.raises(JobStoreError, match="dispatch_not_started"):
        store.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")
    with pytest.raises(JobStoreError, match="dispatch_not_started"):
        store.mark_uncertain(active)
    store.start_dispatch(active)
    with pytest.raises(JobStoreError, match="invalid_reconcile_state"):
        store.reconcile_task("job", expected_version=1, receipt_sha256=RECEIPT,
                             outcome="succeeded", **SCOPE)
    assert snapshot(store).status == "running"


@pytest.mark.parametrize("operation", ["start", "finish", "uncertain", "reconcile"])
def test_marker_receipt_and_job_transition_are_atomic_under_write_fault(state, operation):
    store, now, path = state
    register(state)
    active = claim(store, lease_seconds=1)
    if operation != "start":
        store.start_dispatch(active)
    if operation == "reconcile":
        now[0] += timedelta(seconds=2)
    before_task, before_job = task(store), snapshot(store)
    sql(path, """CREATE TRIGGER refuse_transition BEFORE UPDATE ON fixture_jobs
        BEGIN SELECT RAISE(ABORT, 'private failed write'); END""")
    operations = {
        "start": lambda: store.start_dispatch(active),
        "finish": lambda: store.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded"),
        "uncertain": lambda: store.mark_uncertain(active),
        "reconcile": lambda: store.reconcile_task("job", expected_version=1,
            receipt_sha256=RECEIPT, outcome="succeeded", **SCOPE),
    }
    with pytest.raises(JobStoreError, match="^storage_unavailable$"):
        operations[operation]()
    assert task(store) == before_task and snapshot(store) == before_job


@pytest.mark.parametrize("table,column,value", [
    ("fixture_jobs", "approved_step_ref", "input-" + "b" * 64),
    ("fixture_jobs", "fingerprint", "b" * 64),
    ("fixture_jobs", "task_ref", "fixture:success"),
    ("fixture_jobs", "deadline", 2000000000.0),
    ("fixture_jobs", "updated_at", 1.0),
    ("durable_core_tasks", "input_text", "private changed input"),
    ("durable_core_tasks", "input_sha256", "b" * 64),
    ("durable_core_tasks", "request_id", "durable-job-" + "b" * 64),
    ("durable_core_tasks", "core_session_id", "session://durable-job-" + "b" * 64),
    ("durable_core_tasks", "binding_sha256", "b" * 64),
    ("durable_core_tasks", "created_at", 1.0),
    ("durable_core_tasks", "phase", "started"),
    ("durable_core_tasks", "receipt_sha256", "b" * 64),
])
def test_raw_spec_input_and_time_drift_refuse_before_claim(state, table, column, value):
    store, _, path = state
    register(state)
    sql(path, f"UPDATE {table} SET {column}=? WHERE job_id='job'", (value,))
    with pytest.raises(JobStoreError):
        task(store)
    with pytest.raises(JobStoreError):
        snapshot(store)
    with pytest.raises(JobStoreError):
        claim(store)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT attempts FROM fixture_jobs").fetchone()[0] == 0


@pytest.mark.parametrize("patch", [
    {"worker_id": "other"}, {"actor_ref": "other"}, {"session_ref": "other"},
    {"fencing": 9}, {"lease_until": datetime(2030, 1, 1, tzinfo=UTC)},
])
def test_exact_claim_binding_guards_start_and_completion(state, patch):
    store, _, _ = state
    register(state)
    active = claim(store)
    forged = replace(active, **patch)
    with pytest.raises(JobStoreError):
        store.start_dispatch(forged)
    assert task(store).phase == "prepared"
    store.start_dispatch(active)
    with pytest.raises(JobStoreError):
        store.finish_task(forged, receipt_sha256=RECEIPT, outcome="succeeded")
    final = store.finish_task(active, receipt_sha256=RECEIPT, outcome="succeeded")
    assert final.status == "succeeded"


@pytest.mark.parametrize("receipt,outcome", [
    (None, "succeeded"), ("private output", "succeeded"),
    ("g" * 64, "succeeded"), (RECEIPT, "private output"), (RECEIPT, []),
])
def test_only_fixed_outcomes_and_receipt_digest_are_persisted(state, receipt, outcome):
    store, _, _ = state
    register(state)
    active = claim(store)
    store.start_dispatch(active)
    with pytest.raises(JobStoreError) as caught:
        store.finish_task(active, receipt_sha256=receipt, outcome=outcome)
    assert "private" not in str(caught.value)
    assert task(store).receipt_sha256 is None and snapshot(store).status == "running"


def test_clock_regression_and_expired_start_fail_closed(state):
    store, now, _ = state
    register(state)
    active = claim(store, lease_seconds=1)
    now[0] -= timedelta(seconds=1)
    with pytest.raises(JobStoreError, match="clock_regressed"):
        store.start_dispatch(active)
    now[0] += timedelta(seconds=2)
    with pytest.raises(JobStoreError, match="claim_expired"):
        store.start_dispatch(active)
    assert task(store).phase == "prepared"


def test_scope_bindings_do_not_leak_or_mutate_other_task(state):
    store, _, _ = state
    register(state)
    wrong = {"actor_ref": "other", "session_ref": "session"}
    with pytest.raises(JobStoreError, match="job_unavailable"):
        store.load_task("job", **wrong)
    with pytest.raises(JobStoreError, match="job_unavailable"):
        store.claim_task("job", worker_id="worker", expected_version=0, **wrong)
    assert snapshot(store).attempts == 0
