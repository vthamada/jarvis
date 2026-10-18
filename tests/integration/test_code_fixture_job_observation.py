"""Persisted fixed-task states remain readable without replay or authority.

This is a real SQLite/CLI/host-profile compatibility test, not physical Docker
evidence: only the fixed runner boundary is substituted with synthetic proof.
"""

import hashlib
import json
from datetime import UTC, datetime, timedelta

import pytest
from job_service import JobSpec, SqliteJobStore

from apps.jarvis_api.job_activity_profile import JobActivityProfile
from apps.jarvis_console import code_fixture_job as pilot
from apps.jarvis_console.job_activity_cli import main as activity_main
from tools import run_code_fixture_linux as linux

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def synthetic_proof(scenario):
    counts = {"baseline": (3, 0, 3), "candidate": (3, 3, 0),
              "isolation": (5, 5, 0), "timeout": (0, 0, 0)}[scenario]
    return {
        "schema_version": "jarvis-code-fixture-proof-v1", "status": "passed",
        "reason": "expected_timeout" if scenario == "timeout" else "expected_fixture_outcome",
        "evidence_mode": "controlled_linux_fixture", "scenario": scenario,
        "test_count": counts[0], "passed_count": counts[1], "failed_count": counts[2],
        "fixture_sha256": linux.fixture_sha256(scenario), "image_sha256": linux.IMAGE,
        "cleanup_verified": True, "execution_started": True,
        "authority": "none", "capability_promoted": False,
    }


@pytest.mark.parametrize("scenario", linux.SCENARIOS)
def test_fixture_job_restart_to_readonly_activity_has_no_replay(tmp_path, monkeypatch,
                                                               capsys, scenario):
    path = tmp_path / "jobs.db"
    store = SqliteJobStore(path, clock=lambda: NOW)
    request = pilot.CodeFixtureInput("private-actor", "private-session", scenario)
    spec = JobSpec("private-job", request.actor_ref, request.session_ref,
                   "code-fixture-pilot", request.step_ref, request.task_ref,
                   NOW + timedelta(minutes=3), 1)
    store.register(spec)
    calls = []
    monkeypatch.setattr(linux, "run_code_fixture_linux",
                        lambda **options: calls.append(options) or synthetic_proof(scenario))
    result = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        spec.job_id, request, authorized=True, expected_version=0)
    assert result["result_accepted"] is True
    assert result["job"]["status"] == "succeeded"
    assert len(calls) == 1

    reopened = SqliteJobStore(path, clock=lambda: NOW)
    historical = pilot.CodeFixtureJobRunner(reopened, "restarted").run_once(
        spec.job_id, request, authorized=True, expected_version=result["job"]["version"])
    assert historical["result_accepted"] is False
    assert historical["fixture"] is None
    before = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    monkeypatch.setattr(linux, "run_code_fixture_linux",
                        lambda **_options: pytest.fail("readonly_activity_replayed_fixture"))
    profile = JobActivityProfile(authorized=True, database_path=path,
                                actor_ref=spec.actor_ref, session_ref=spec.session_ref,
                                job_ids=(spec.job_id,))
    first, second = profile.read(), profile.read()
    assert first == second
    assert first["status_counts"]["succeeded"] == 1
    assert first["evidence_counts"] == {"fixture": 1, "metadata_ledger": 0}
    assert first["attempts_recorded"] == 1
    assert first["progress"]["terminal_count"] == 1
    assert first["read_only"] is True and first["authority"] == "none"
    assert activity_main(["--authorized", "--job-db", str(path),
                          "--actor-ref", spec.actor_ref, "--session-ref", spec.session_ref,
                          "--job-id", spec.job_id]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert json.loads(output.out) == first
    assert "private" not in output.out
    assert "cleanup_verified" not in output.out  # Ledger state != current physical proof.
    assert (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) == before
