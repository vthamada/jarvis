"""One-shot Core job fencing differs deliberately from replayable fixtures."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from job_service import JobSpec, JobStoreError, SqliteJobStore
from job_service.store import CORE_TASK

SCOPE = {"actor_ref": "actor", "session_ref": "session"}


@pytest.fixture
def setup(tmp_path):
    now = [datetime(2026, 10, 3, tzinfo=UTC)]
    path = tmp_path / "jobs.db"
    store = SqliteJobStore(path, clock=lambda: now[0])
    spec = JobSpec(
        "job",
        "actor",
        "session",
        "core-assist-pilot",
        "input-" + "a" * 64,
        CORE_TASK,
        now[0] + timedelta(minutes=10),
        1,
    )
    store.register(spec)
    return store, spec, now, path


@pytest.mark.parametrize(
    "patch",
    [
        {"max_attempts": 2},
        {"responsibility_ref": "other"},
        {"approved_step_ref": "fixture:success"},
        {"approved_step_ref": "input-" + "g" * 64},
    ],
)
def test_closed_core_registration_binding(setup, patch):
    _, spec, _, _ = setup
    with pytest.raises(JobStoreError, match="invalid_core_binding"):
        replace(spec, **patch)


def test_restart_never_replays_running_core_and_expiry_requires_review(setup):
    store, _, now, path = setup
    active = store.claim("job", worker_id="worker", expected_version=0, lease_seconds=1, **SCOPE)
    reopened = SqliteJobStore(path, clock=lambda: now[0])
    assert reopened.get("job", **SCOPE).status == "running"
    assert reopened.get("job", **SCOPE).attempts == 1
    now[0] += timedelta(seconds=1)
    assert reopened.claim("job", worker_id="other", expected_version=1, **SCOPE) is None
    waiting = reopened.get("job", **SCOPE)
    assert waiting.status == "needs_decision" and waiting.attempts == 1
    assert waiting.fencing == 2
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.finish(active, "succeeded")
    with pytest.raises(JobStoreError, match="core_replay_refused"):
        reopened.retry("job", expected_version=waiting.version, **SCOPE)


def test_pause_running_revokes_claim_and_never_resumes(setup):
    store, _, _, _ = setup
    active = store.claim("job", worker_id="worker", expected_version=0, **SCOPE)
    store.validate_claim(active)
    stopped = store.pause("job", expected_version=1, **SCOPE)
    assert stopped.status == "needs_decision" and stopped.fencing == 2
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.validate_claim(active)
    with pytest.raises(JobStoreError, match="version_conflict"):
        store.finish(active, "succeeded")
    assert store.claim("job", worker_id="other", expected_version=2, **SCOPE) is None


def test_expired_preflight_and_deadline_before_claim(setup):
    store, _, now, _ = setup
    active = store.claim("job", worker_id="worker", expected_version=0, lease_seconds=1, **SCOPE)
    now[0] += timedelta(seconds=1)
    with pytest.raises(JobStoreError, match="claim_expired"):
        store.validate_claim(active)
    now[0] += timedelta(minutes=20)
    assert store.claim("job", worker_id="other", expected_version=1, **SCOPE) is None
    assert store.get("job", **SCOPE).status == "needs_decision"


def test_core_telemetry_never_asserts_fixture_execution(setup):
    store, _, _, _ = setup
    metadata = store.get("job", **SCOPE).telemetry()
    assert metadata["evidence_mode"] == "metadata_ledger"
    assert not metadata["action_authority"] and not metadata["automatic_execution"]
    assert "actor" not in repr(metadata) and "input-" not in repr(metadata)
