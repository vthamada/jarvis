"""Real SQLite -> inert host profile, including restart and zero writes."""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from job_service.store import CORE_TASK, JobSpec, SqliteJobStore

from apps.jarvis_api.job_activity_profile import JobActivityProfile, JobActivityUnavailable

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 1, tzinfo=UTC)
ACTOR, SESSION = "private-actor", "private-session"


def seed(path, *, job="private-job", actor=ACTOR, session=SESSION,
         task="fixture:success"):
    store = SqliteJobStore(path, clock=lambda: NOW)
    store.register(JobSpec(
        job, actor, session, "core-assist-pilot" if task == CORE_TASK else "private-responsibility",
        "input-" + "a" * 64 if task == CORE_TASK else "private-approval", task,
        NOW + timedelta(hours=1), 1 if task == CORE_TASK else 3,
    ))
    return store


def profile(path, *, actor=ACTOR, session=SESSION, jobs=("private-job",)):
    return JobActivityProfile(authorized=True, database_path=path, actor_ref=actor,
                              session_ref=session, job_ids=jobs)


def fingerprint(directory):
    return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns,
                     p.stat().st_size) for p in directory.iterdir() if p.is_file()}


@pytest.mark.parametrize("task", ["fixture:success", CORE_TASK])
def test_real_running_state_survives_reader_restarts_without_recovery(tmp_path, task):
    path = tmp_path / "private-ledger.db"
    store = seed(path, task=task)
    claim = store.claim("private-job", actor_ref=ACTOR, session_ref=SESSION,
                        worker_id="private-worker", expected_version=0, lease_seconds=1)
    assert claim is not None
    before = fingerprint(tmp_path)
    script = """
import json, sys
from pathlib import Path
from apps.jarvis_api.job_activity_profile import JobActivityProfile
profile = JobActivityProfile(authorized=True, database_path=Path(sys.argv[1]),
    actor_ref='private-actor', session_ref='private-session', job_ids=('private-job',))
print(json.dumps(profile.read(), sort_keys=True))
"""
    children = [subprocess.run(
        [sys.executable, "-c", script, str(path)], cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
                 DATABASE_URL="postgresql://unused.invalid/private-secret"),
        capture_output=True, timeout=30,
    ) for _ in range(2)]
    assert all(child.returncode == 0 and not child.stderr for child in children)
    assert children[0].stdout == children[1].stdout
    result = json.loads(children[0].stdout)
    assert result["status_counts"]["running"] == 1
    assert result["progress"]["active_count"] == 1
    assert result["attempts_recorded"] == 1
    assert result["evidence_counts"] == {
        "fixture": int(task != CORE_TASK), "metadata_ledger": int(task == CORE_TASK)}
    assert b"private" not in children[0].stdout
    assert fingerprint(tmp_path) == before
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT status,attempts,version,fencing FROM fixture_jobs").fetchone()
    assert row == ("running", 1, 1, 1)


def test_real_selected_scope_never_enumerates_foreign_rows(tmp_path, monkeypatch):
    path = tmp_path / "private-ledger.db"
    store = seed(path)
    seed(path, job="private-done")
    claim = store.claim("private-done", actor_ref=ACTOR, session_ref=SESSION,
                        worker_id="private-worker", expected_version=0)
    store.finish(claim, "succeeded")
    seed(path, job="foreign-job", actor="foreign-actor")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE fixture_jobs SET fingerprint='private-corrupt' "
                   "WHERE job_id='foreign-job'")
    before = fingerprint(tmp_path)
    monkeypatch.setattr(SqliteJobStore, "__init__", lambda *_a, **_k: pytest.fail("writer"))
    bound = profile(path, jobs=("private-job", "private-done"))
    result = bound.read()
    assert result["selected_job_count"] == 2
    assert result["status_counts"]["registered"] == 1
    assert result["status_counts"]["succeeded"] == 1
    assert result["progress"]["terminal_count"] == 1
    assert len(json.dumps(result).encode()) <= 4096
    assert "private" not in json.dumps(result) and "foreign" not in json.dumps(result)
    assert fingerprint(tmp_path) == before


@pytest.mark.parametrize("failure", ["missing", "foreign_actor", "foreign_session",
                                    "foreign_job", "partial", "fingerprint", "schema",
                                    "wal", "shm", "journal", "non_sqlite"])
def test_real_source_and_scope_denials_have_no_writes(tmp_path, failure):
    path = tmp_path / "private-ledger.db"
    if failure != "missing":
        seed(path)
    if failure == "fingerprint":
        with sqlite3.connect(path) as db:
            db.execute("UPDATE fixture_jobs SET fingerprint='private-corrupt'")
    if failure == "schema":
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA user_version=2")
    if failure in {"wal", "shm", "journal"}:
        path.with_name(path.name + "-" + failure).write_bytes(b"private-marker")
    if failure == "non_sqlite":
        path.write_bytes(b"private-marker" * 100)
    args = dict(actor=ACTOR, session=SESSION, jobs=("private-job",))
    if failure == "foreign_actor":
        args["actor"] = "foreign-actor"
    if failure == "foreign_session":
        args["session"] = "foreign-session"
    if failure == "foreign_job":
        args["jobs"] = ("foreign-job",)
    if failure == "partial":
        args["jobs"] = ("private-job", "foreign-job")
    bound = profile(path, **args)
    before = fingerprint(tmp_path)
    with pytest.raises(JobActivityUnavailable, match="^job_activity_unavailable$"):
        bound.read()
    assert fingerprint(tmp_path) == before


def test_no_parent_or_source_created_when_missing(tmp_path):
    path = tmp_path / "private-absent" / "ledger.db"
    bound = profile(path)
    assert not path.parent.exists()
    with pytest.raises(JobActivityUnavailable):
        bound.read()
    assert not path.parent.exists()


def test_all_32_selected_jobs_read_with_bounded_response(tmp_path):
    path = tmp_path / "private-ledger.db"
    jobs = tuple(f"private-job-{index}" for index in range(32))
    for job in jobs:
        seed(path, job=job)
    before = fingerprint(tmp_path)
    result = profile(path, jobs=jobs).read()
    assert result["selected_job_count"] == result["status_counts"]["registered"] == 32
    assert result["attempts_recorded"] == 0
    assert len(json.dumps(result).encode()) <= 4096
    assert fingerprint(tmp_path) == before
