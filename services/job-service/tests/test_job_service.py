"""Durable jobs local and E2E fixtures; no background scheduling/effects."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from job_service import FixtureJobWorker, JobSpec, JobStoreError, SqliteJobStore

SCOPE = {"actor_ref": "actor-1", "session_ref": "session-1"}


@pytest.fixture
def clock():
    return [datetime(2026, 10, 2, 12, tzinfo=UTC)]


@pytest.fixture
def store(tmp_path, clock):
    return SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])


def spec(clock, **kwargs):
    return JobSpec(
        "job-1",
        "actor-1",
        "session-1",
        "responsibility-1",
        "approved-step-1",
        kwargs.pop("task_ref", "fixture:success"),
        clock[0] + timedelta(minutes=10),
        **kwargs,
    )


def claim(store, **kwargs):
    return store.claim("job-1", worker_id="worker-1", expected_version=0, **SCOPE, **kwargs)


def snapshot(store):
    return store.get("job-1", **SCOPE)


def test_register_then_explicit_worker_e2e(store, clock):
    registered = store.register(spec(clock))
    assert registered.status == "registered"
    assert (registered.version, registered.fencing, registered.attempts) == (0, 0, 0)
    assert registered.lease_until is None
    completed = FixtureJobWorker(store, "worker-1").run_once(
        "job-1",
        expected_version=0,
        **SCOPE,
    )
    assert completed.status == "succeeded"
    assert (completed.version, completed.fencing, completed.attempts) == (2, 1, 1)
    assert completed.worker_id is None and completed.lease_until is None
    telemetry = completed.telemetry()
    assert telemetry["evidence_mode"] == "fixture"
    assert telemetry["action_authority"] is False
    assert "responsibility-1" not in repr(telemetry)
    assert "actor-1" not in repr(telemetry)


def test_registration_idempotency_and_fingerprint_conflict(store, clock):
    first = store.register(spec(clock))
    assert store.register(spec(clock)) == first
    with pytest.raises(JobStoreError, match="registration_conflict"):
        store.register(replace(spec(clock), approved_step_ref="other-step"))
    with pytest.raises(JobStoreError, match="registration_conflict"):
        store.register(replace(spec(clock), actor_ref="other-actor"))
    assert snapshot(store) == first


@pytest.mark.parametrize(
    "other_scope",
    [
        {"actor_ref": "other", "session_ref": "session-1"},
        {"actor_ref": "actor-1", "session_ref": "other"},
    ],
)
def test_scope_is_required_for_all_operations(store, clock, other_scope):
    store.register(spec(clock))
    operations = [
        lambda: store.get("job-1", **other_scope),
        lambda: store.claim("job-1", worker_id="worker-1", expected_version=0, **other_scope),
        lambda: store.cancel("job-1", expected_version=0, **other_scope),
        lambda: store.retry("job-1", expected_version=0, **other_scope),
    ]
    for operation in operations:
        with pytest.raises(JobStoreError, match="job_unavailable"):
            operation()
    assert snapshot(store).status == "registered"


def test_two_workers_atomic_claim_cas(store, tmp_path, clock):
    store.register(spec(clock))
    other = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])

    def attempt(pair):
        worker, job_store = pair
        try:
            return job_store.claim("job-1", worker_id=worker, expected_version=0, **SCOPE)
        except JobStoreError as error:
            return str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [("worker-1", store), ("worker-2", other)]))
    assert sum(not isinstance(item, str) for item in outcomes) == 1
    assert "version_conflict" in outcomes
    assert snapshot(store).attempts == 1
    assert store.claim("job-1", worker_id="worker-2", expected_version=1, **SCOPE) is None


def test_lease_expiry_reclaim_fences_previous_worker(store, clock):
    store.register(spec(clock))
    old = claim(store, lease_seconds=1)
    clock[0] += timedelta(seconds=1)
    with pytest.raises(JobStoreError, match="claim_expired"):
        store.finish(old, "succeeded")
    new = store.claim("job-1", worker_id="worker-2", expected_version=1, lease_seconds=2, **SCOPE)
    assert new.fencing == 2
    assert snapshot(store).attempts == 2
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.finish(old, "succeeded")
    assert store.finish(new, "succeeded").status == "succeeded"


def test_cancel_running_revokes_claim_and_fencing(store, clock):
    store.register(spec(clock))
    active = claim(store)
    cancelled = store.cancel("job-1", expected_version=1, **SCOPE)
    assert cancelled.status == "cancelled"
    assert cancelled.fencing == 2
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.finish(active, "succeeded")
    assert store.claim("job-1", worker_id="worker-2", expected_version=2, **SCOPE) is None


def test_cancel_before_claim_and_conflict_are_no_effect(store, clock):
    store.register(spec(clock))
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.cancel("job-1", expected_version=99, **SCOPE)
    assert snapshot(store).version == 0
    cancelled = store.cancel("job-1", expected_version=0, **SCOPE)
    assert cancelled.status == "cancelled"
    with pytest.raises(JobStoreError, match="invalid_cancel_state"):
        store.cancel("job-1", expected_version=1, **SCOPE)


@pytest.mark.parametrize(
    "task,outcome",
    [
        ("fixture:failure", "failed"),
        ("fixture:needs_decision", "needs_decision"),
    ],
)
def test_failure_and_needs_decision_do_not_execute_next_steps(store, clock, task, outcome):
    store.register(spec(clock, task_ref=task))
    worker = FixtureJobWorker(store, "worker-1")
    result = worker.run_once("job-1", expected_version=0, **SCOPE)
    assert result.status == outcome
    assert worker.run_once("job-1", expected_version=2, **SCOPE) == result
    if outcome == "needs_decision":
        with pytest.raises(JobStoreError, match="invalid_retry_state"):
            store.retry("job-1", expected_version=2, **SCOPE)


def test_explicit_retry_is_bounded_and_never_resets_attempts(store, clock):
    store.register(spec(clock, task_ref="fixture:failure", max_attempts=2))
    worker = FixtureJobWorker(store, "worker-1")
    failed = worker.run_once("job-1", expected_version=0, **SCOPE)
    registered = store.retry("job-1", expected_version=failed.version, **SCOPE)
    assert registered.status == "registered" and registered.attempts == 1
    assert registered.fencing == 2
    final = worker.run_once("job-1", expected_version=registered.version, **SCOPE)
    assert final.attempts == 2 and final.status == "failed"
    with pytest.raises(JobStoreError, match="attempts_exhausted"):
        store.retry("job-1", expected_version=final.version, **SCOPE)


def test_exhausted_expired_claim_is_reconciled_not_run(store, clock):
    store.register(spec(clock, max_attempts=1))
    old = claim(store, lease_seconds=1)
    clock[0] += timedelta(seconds=1)
    assert store.claim("job-1", worker_id="worker-2", expected_version=1, **SCOPE) is None
    stopped = snapshot(store)
    assert stopped.status == "failed"
    assert stopped.last_outcome == "attempts_exhausted"
    assert stopped.fencing == 2
    with pytest.raises(JobStoreError):
        store.finish(old, "succeeded")


def test_reopen_and_host_offline_require_explicit_resume(store, tmp_path, clock):
    spec_value = spec(clock)
    store.register(spec_value)
    claim(store, lease_seconds=1)
    clock[0] += timedelta(seconds=5)
    restarted = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])
    pending = snapshot(restarted)
    assert pending.status == "running" and pending.attempts == 1
    assert pending.spec.deadline == spec_value.deadline
    # Construction/read has not reclaimed or executed anything.
    assert pending.version == 1
    result = FixtureJobWorker(restarted, "worker-2").run_once(
        "job-1",
        expected_version=1,
        **SCOPE,
    )
    assert result.status == "succeeded" and result.attempts == 2


def test_deadline_caps_lease_and_blocks_completion_or_restart(store, tmp_path, clock):
    store.register(replace(spec(clock), deadline=clock[0] + timedelta(seconds=2)))
    active = claim(store, lease_seconds=120)
    assert active.lease_until == clock[0] + timedelta(seconds=2)
    clock[0] += timedelta(seconds=2)
    with pytest.raises(JobStoreError, match="claim_expired"):
        store.finish(active, "succeeded")
    restarted = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])
    assert restarted.claim("job-1", worker_id="worker-2", expected_version=1, **SCOPE) is None
    assert snapshot(restarted).status == "expired"


def test_clock_regression_and_naive_clock_fail_closed(store, clock):
    store.register(spec(clock))
    clock[0] -= timedelta(seconds=1)
    with pytest.raises(JobStoreError, match="clock_regressed"):
        claim(store)
    assert snapshot(store).attempts == 0
    clock[0] = datetime(2026, 10, 2)
    with pytest.raises(JobStoreError, match="invalid_clock"):
        claim(store)


@pytest.mark.parametrize(
    "mutation",
    [
        {"worker_id": "other"},
        {"actor_ref": "other"},
        {"session_ref": "other"},
        {"fencing": 99},
        {"lease_until": datetime(2030, 1, 1, tzinfo=UTC)},
    ],
)
def test_exact_claim_cannot_be_forged(store, clock, mutation):
    store.register(spec(clock))
    active = claim(store)
    with pytest.raises(JobStoreError):
        store.finish(replace(active, **mutation), "succeeded")
    assert snapshot(store).status == "running"
    assert store.finish(active, "succeeded").status == "succeeded"
    with pytest.raises(JobStoreError):
        store.finish(active, "succeeded")


@pytest.mark.parametrize("bad", [None, "private freeform outcome", "completed", 1])
def test_only_normalized_outcomes_are_persisted(store, clock, bad):
    store.register(spec(clock))
    active = claim(store)
    with pytest.raises(JobStoreError, match="invalid_outcome"):
        store.finish(active, bad)
    assert snapshot(store).last_outcome is None


@pytest.mark.parametrize(
    "mutation",
    [
        {"deadline": datetime(2026, 10, 2)},
        {"deadline": datetime(2026, 10, 2, tzinfo=timezone(timedelta(hours=1)))},
        {"job_id": "../escape"},
        {"actor_ref": "private text"},
        {"session_ref": ""},
        {"max_attempts": True},
        {"max_attempts": 0},
        {"max_attempts": 11},
        {"task_ref": "run:subprocess"},
        {"task_ref": None},
    ],
)
def test_metadata_input_validation(clock, mutation):
    with pytest.raises(JobStoreError):
        replace(spec(clock), **mutation)


@pytest.mark.parametrize("lease", [0, -1, True, 121, float("inf"), float("nan"), "30"])
def test_lease_validation(store, clock, lease):
    store.register(spec(clock))
    with pytest.raises(JobStoreError, match="invalid_lease"):
        claim(store, lease_seconds=lease)
    assert snapshot(store).version == 0


def test_expired_registration_and_unknown_job(store, clock):
    with pytest.raises(JobStoreError, match="deadline_expired"):
        store.register(replace(spec(clock), deadline=clock[0]))
    with pytest.raises(JobStoreError, match="job_unavailable"):
        snapshot(store)


def test_connections_close_and_database_can_be_moved_on_windows(store, tmp_path, clock):
    store.register(spec(clock))
    claim(store)
    snapshot(store)
    path = tmp_path / "jobs.db"
    path.rename(tmp_path / "moved.db")
    reopened = SqliteJobStore(tmp_path / "moved.db", clock=lambda: clock[0])
    assert snapshot(reopened).status == "running"


@pytest.mark.parametrize(
    "column,value",
    [
        ("status", "private corrupted status"),
        ("attempts", -1),
        ("version", -1),
        ("last_outcome", "private credentials"),
        ("worker_id", "bad worker"),
        ("deadline", "not a timestamp"),
        ("updated_at", "private text"),
    ],
)
def test_corrupt_record_is_not_projected_or_claimed(store, tmp_path, clock, column, value):
    store.register(spec(clock))
    db = sqlite3.connect(tmp_path / "jobs.db")
    try:
        db.execute(f"UPDATE fixture_jobs SET {column}=? WHERE job_id='job-1'", (value,))
        db.commit()
    finally:
        db.close()
    with pytest.raises(JobStoreError, match="invalid_record"):
        snapshot(store)
    with pytest.raises(JobStoreError, match="invalid_record"):
        claim(store)


def test_epoch_microseconds_preserve_exact_claim_round_trip(store, clock):
    clock[0] += timedelta(microseconds=123456)
    store.register(spec(clock))
    active = claim(store, lease_seconds=1.234567)
    assert store.finish(active, "succeeded").status == "succeeded"


def test_unknown_schema_version_is_not_migrated(tmp_path, clock):
    path = tmp_path / "jobs.db"
    db = sqlite3.connect(path)
    try:
        db.execute("PRAGMA user_version=999")
    finally:
        db.close()
    with pytest.raises(JobStoreError, match="unsupported_schema"):
        SqliteJobStore(path, clock=lambda: clock[0])


def test_retry_expired_deadline_does_not_create_new_attempt(store, clock):
    store.register(spec(clock, task_ref="fixture:failure"))
    FixtureJobWorker(store, "worker-1").run_once("job-1", expected_version=0, **SCOPE)
    clock[0] += timedelta(hours=1)
    with pytest.raises(JobStoreError, match="deadline_expired"):
        store.retry("job-1", expected_version=2, **SCOPE)
    assert snapshot(store).attempts == 1


@pytest.mark.parametrize("version", [True, -1, "0", 2**60])
def test_expected_version_validation(store, clock, version):
    store.register(spec(clock))
    with pytest.raises(JobStoreError, match="invalid_version"):
        store.cancel("job-1", expected_version=version, **SCOPE)
    assert snapshot(store).version == 0


def test_telemetry_does_not_claim_expired_lease_is_active(store, clock):
    store.register(spec(clock))
    claim(store, lease_seconds=1)
    clock[0] += timedelta(seconds=2)
    telemetry = snapshot(store).telemetry()
    assert telemetry["lease_present"] is True
    assert "lease_active" not in telemetry


def test_completion_uses_time_after_lock_acquisition(store, clock, monkeypatch):
    store.register(spec(clock))
    active = claim(store, lease_seconds=1)
    original = store._connection

    @contextmanager
    def waited_for_lock(*, write=False):
        with original(write=write) as db:
            if write:
                clock[0] += timedelta(seconds=2)
            yield db

    monkeypatch.setattr(store, "_connection", waited_for_lock)
    with pytest.raises(JobStoreError, match="claim_expired"):
        store.finish(active, "succeeded")
    assert snapshot(store).status == "running"
