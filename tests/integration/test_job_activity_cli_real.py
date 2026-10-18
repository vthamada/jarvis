"""Standalone CLI reads actual SQLite without creating, reconciling or replaying jobs."""

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

from apps.jarvis_console import job_activity_cli as activity

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 1, tzinfo=UTC)
ACTOR, SESSION = "private-actor", "private-session"


def seed(path, *, actor=ACTOR, session=SESSION, job="private-job", task="fixture:success"):
    store = SqliteJobStore(path, clock=lambda: NOW)
    store.register(JobSpec(
        job, actor, session, "core-assist-pilot" if task == CORE_TASK else "private-responsibility",
        "input-" + "a" * 64 if task == CORE_TASK else "private-approval", task,
        NOW + timedelta(hours=1), 1 if task == CORE_TASK else 3,
    ))
    return store


def fingerprint(directory):
    return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns,
                     p.stat().st_size) for p in directory.iterdir() if p.is_file()}


def invoke(directory, path, *extra, actor=ACTOR, session=SESSION, job="private-job",
           authorized=True):
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL="postgresql://not-used.invalid/private-marker")
    argv = [sys.executable, "-m", "apps.jarvis_console.job_activity_cli", "--job-db", str(path),
            "--actor-ref", actor, "--session-ref", session, "--job-id", job]
    if authorized:
        argv.append("--authorized")
    return subprocess.run([*argv, *extra], cwd=directory, env=env, capture_output=True, timeout=60)


@pytest.mark.parametrize("task", ["fixture:success", CORE_TASK])
def test_crashed_running_claim_remains_running_after_two_process_restarts(tmp_path, task):
    path = tmp_path / "private-ledger.db"
    # A separate writer commits the claim then abruptly exits without finishing.
    # The reader never runs recovery; an expired claim is still ledger-running.
    script = """
import os, sys
from datetime import UTC, datetime, timedelta
from apps.jarvis_console.bootstrap import ensure_src_paths
ensure_src_paths()
from job_service.store import CORE_TASK, JobSpec, SqliteJobStore
now = datetime(2026, 10, 1, tzinfo=UTC)
task = sys.argv[2]
store = SqliteJobStore(sys.argv[1], clock=lambda: now)
store.register(JobSpec('private-job', 'private-actor', 'private-session',
    'core-assist-pilot' if task == CORE_TASK else 'private-responsibility',
    'input-' + 'a' * 64 if task == CORE_TASK else 'private-approval', task,
    now + timedelta(hours=1), 1 if task == CORE_TASK else 3))
claim = store.claim('private-job', actor_ref='private-actor', session_ref='private-session',
    worker_id='private-worker', expected_version=0, lease_seconds=1)
assert claim is not None
os._exit(73)
"""
    crashed = subprocess.run(
        [sys.executable, "-c", script, str(path), task], cwd=tmp_path,
        env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1"),
        capture_output=True, timeout=60,
    )
    assert crashed.returncode == 73 and not crashed.stdout and not crashed.stderr
    before = fingerprint(tmp_path)
    first, second = invoke(tmp_path, path), invoke(tmp_path, path)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout and not first.stderr and not second.stderr
    result = json.loads(first.stdout)
    assert result["status_counts"]["running"] == 1
    assert result["progress"]["active_count"] == 1
    assert result["progress"]["terminal_count"] == 0
    assert result["attempts_recorded"] == 1
    assert b"private" not in first.stdout and b"input-" not in first.stdout
    assert fingerprint(tmp_path) == before
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT status,attempts,version,fencing FROM fixture_jobs").fetchone()
    assert row == ("running", 1, 1, 1)


def test_selected_states_and_foreign_rows_not_enumerated(tmp_path):
    path = tmp_path / "private-ledger.db"
    store = seed(path)
    seed(path, job="private-done")
    claim = store.claim("private-done", actor_ref=ACTOR, session_ref=SESSION,
                        worker_id="private-worker", expected_version=0)
    store.finish(claim, "succeeded")
    seed(path, job="foreign-job", actor="foreign-actor")
    with sqlite3.connect(path) as db:
        db.execute("UPDATE fixture_jobs SET fingerprint='corrupt' WHERE job_id='foreign-job'")
    before = fingerprint(tmp_path)
    result = invoke(tmp_path, path, "--job-id", "private-done")
    assert result.returncode == 0, result.stderr
    product = json.loads(result.stdout)
    assert product["selected_job_count"] == 2
    assert product["status_counts"]["registered"] == 1
    assert product["status_counts"]["succeeded"] == 1
    assert product["progress"]["terminal_count"] == 1
    assert b"foreign" not in result.stdout and b"private" not in result.stdout
    assert fingerprint(tmp_path) == before


@pytest.mark.parametrize("failure", ["unauthorized", "missing", "foreign_actor",
                                    "foreign_session", "missing_job", "partial", "duplicate",
                                    "invalid_ref", "limit", "fingerprint", "schema", "wal"])
def test_negative_cases_no_partial_output_or_file_writes(tmp_path, failure):
    path = tmp_path / "private-ledger.db"
    if failure != "missing":
        seed(path)
    if failure == "fingerprint":
        with sqlite3.connect(path) as db:
            db.execute("UPDATE fixture_jobs SET fingerprint='private-corrupt'")
    if failure == "schema":
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA user_version=2")
    if failure == "wal":
        path.with_name(path.name + "-wal").write_bytes(b"private-marker")
    extra = []
    if failure in {"partial", "duplicate"}:
        extra = ["--job-id", "missing" if failure == "partial" else "private-job"]
    if failure == "limit":
        extra = [value for i in range(32) for value in ("--job-id", f"private-{i}")]
    before = fingerprint(tmp_path)
    result = invoke(
        tmp_path, path, *extra, actor="foreign" if failure == "foreign_actor" else ACTOR,
        session="foreign" if failure == "foreign_session" else SESSION,
        job=("missing" if failure == "missing_job" else
             "password=private-marker" if failure == "invalid_ref" else "private-job"),
        authorized=failure != "unauthorized",
    )
    assert result.returncode == 2 and not result.stdout
    assert json.loads(result.stderr) == {"error_code": "job_activity_refused"}
    assert fingerprint(tmp_path) == before


def test_no_writer_or_core_bootstrap_in_process(tmp_path, monkeypatch, capsys):
    path = tmp_path / "private-ledger.db"
    seed(path)
    before = fingerprint(tmp_path)
    monkeypatch.setattr(SqliteJobStore, "__init__", lambda *_a, **_k: pytest.fail("writer"))
    assert activity.main(["--authorized", "--job-db", str(path), "--actor-ref", ACTOR,
                          "--session-ref", SESSION, "--job-id", "private-job"]) == 0
    assert json.loads(capsys.readouterr().out)["read_only"] is True
    assert fingerprint(tmp_path) == before


def test_missing_parent_not_created(tmp_path):
    path = tmp_path / "private-missing" / "ledger.db"
    result = invoke(tmp_path, path)
    assert result.returncode == 2 and not result.stdout
    assert not path.parent.exists()


@pytest.mark.parametrize("stderr_closed", [False, True])
def test_real_closed_standard_pipes_exit_two_without_shutdown_reflection(tmp_path, stderr_closed):
    path = tmp_path / "private-ledger.db"
    seed(path)
    before = fingerprint(tmp_path)
    # A stdin barrier guarantees that the parent closes the real output pipes
    # before main writes. This exercises CPython shutdown, not a fake stream.
    script = (
        "import sys; from apps.jarvis_console import job_activity_cli as app; "
        "sys.stdin.read(1); raise SystemExit(app.main(sys.argv[1:]))"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", script, "--authorized", "--job-db", str(path),
         "--actor-ref", ACTOR, "--session-ref", SESSION, "--job-id", "private-job"],
        cwd=tmp_path, env=dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1"),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        child.stdout.close()
        child.stdout = None
        if stderr_closed:
            child.stderr.close()
            child.stderr = None
        child.stdin.write(b"x")
        child.stdin.close()
        child.stdin = None
        _, diagnostic = child.communicate(timeout=30)
        assert child.returncode == 2
        if not stderr_closed:
            assert json.loads(diagnostic) == {"error_code": "job_activity_refused"}
            assert b"Exception ignored" not in diagnostic
            assert b"Traceback" not in diagnostic and b"private" not in diagnostic
        assert fingerprint(tmp_path) == before
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=30)
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None and not stream.closed:
                stream.close()
