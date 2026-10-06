"""Real standalone CLI observes existing ledger without bootstrapping/replay."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from job_service.store import JobSpec, SqliteJobStore

from apps.jarvis_console import cli

ROOT = Path(__file__).resolve().parents[2]


def seed(path, job_id="job-one"):
    store = SqliteJobStore(path)
    store.register(JobSpec(job_id, "actor-one", "session-one", "responsibility-one", "step-one",
                           "fixture:success", datetime.now(timezone.utc) + timedelta(minutes=5)))
    return store


def invoke(tmp_path, path, *extra, job_id="job-one", actor="actor-one"):
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL="postgresql://not-used.invalid/blocked")
    return subprocess.run(
        [sys.executable, "-m", "apps.jarvis_console", "--format", "json", "job-inspect",
         "--job-db", str(path), "--actor-ref", actor, "--session-ref", "session-one",
         "--job-id", job_id, *extra], capture_output=True, cwd=tmp_path, env=env, timeout=60,
    )


@pytest.mark.parametrize("refs", [False, True])
def test_existing_running_job_no_execution_or_mutation(tmp_path, refs):
    path = tmp_path / "ledger.db"
    store = seed(path)
    claim = store.claim("job-one", actor_ref="actor-one", session_ref="session-one",
                        worker_id="worker-one", expected_version=0)
    assert claim is not None
    before, inventory = path.read_bytes(), sorted(p.name for p in tmp_path.iterdir())
    result = invoke(tmp_path, path, *( ["--include-refs"] if refs else [] ))
    assert result.returncode == 0, result.stderr.decode()
    assert not result.stderr
    envelope = json.loads(result.stdout)
    assert envelope["command_id"] == "job-inspect" and envelope["redacted"] is False
    product = json.loads(envelope["outputs"][0])
    assert product["read_only"] is True and product["authority"] == "none"
    job = product["jobs"][0]
    assert job["status"] == "running" and job["automatic_execution"] is False
    assert ("references" in job) is refs
    if not refs:
        assert b"actor-one" not in result.stdout and b"job-one" not in result.stdout
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == inventory


@pytest.mark.parametrize("failure", ["missing", "foreign", "invalid", "wal"])
def test_refusal_private_no_partial_output_or_store_creation(tmp_path, failure):
    path = tmp_path / "ledger.db"
    if failure != "missing":
        seed(path)
    if failure == "wal":
        path.with_name(path.name + "-wal").write_bytes(b"private-sentinel")
    inventory = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = invoke(tmp_path, path, actor="foreign" if failure == "foreign" else "actor-one",
                    job_id="password=private-marker" if failure == "invalid" else "job-one")
    assert result.returncode == 2 and not result.stdout
    assert b"private-marker" not in result.stderr and b"ledger.db" not in result.stderr
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == inventory


def test_secret_reference_withheld_whole_not_rewritten(tmp_path):
    path = tmp_path / "ledger.db"
    job_id = "sk-" + "a" * 40
    seed(path, job_id)
    result = invoke(tmp_path, path, "--include-refs", job_id=job_id)
    assert result.returncode == 0, result.stderr.decode()
    envelope = json.loads(result.stdout)
    assert envelope["redacted"] is False
    product = json.loads(envelope["outputs"][0])
    assert product["references_withheld"] is True
    assert "references" not in product["jobs"][0]
    assert job_id.encode() not in result.stdout and b"<redacted>" not in result.stdout


def test_standalone_handler_never_builds_core(tmp_path, monkeypatch, capsys):
    path = tmp_path / "ledger.db"
    seed(path)
    monkeypatch.setattr(cli.JarvisConsole, "build",
                        lambda **kwargs: pytest.fail("Core bootstrapped"))
    assert cli.main(["job-inspect", "--job-db", str(path), "--actor-ref", "actor-one",
                     "--session-ref", "session-one", "--job-id", "job-one",
                     "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["command_id"] == "job-inspect"


def test_parser_error_does_not_echo_scope(monkeypatch, capsys):
    assert cli.main(["job-inspect", "--private-option=password=private-marker"]) == 2
    captured = capsys.readouterr()
    assert not captured.out and "private-marker" not in captured.err


@pytest.mark.parametrize("second", ["absent", "foreign"])
def test_multiple_ids_all_or_nothing(tmp_path, second):
    path = tmp_path / "ledger.db"
    store = seed(path)
    if second == "foreign":
        store.register(JobSpec("foreign", "other-actor", "session-one", "responsibility-one",
                               "step-one", "fixture:success",
                               datetime.now(timezone.utc) + timedelta(minutes=5)))
    before = path.read_bytes()
    result = invoke(tmp_path, path, "--job-id", second, "--include-refs")
    assert result.returncode == 2 and not result.stdout
    assert b"job-one" not in result.stderr and b"other-actor" not in result.stderr
    assert path.read_bytes() == before
