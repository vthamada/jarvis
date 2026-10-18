"""Real SQLite recovery plus explicitly opt-in physical Docker composition."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from job_service import JobSpec, SqliteJobStore

from apps.jarvis_console import code_fixture_job as pilot
from tools import run_code_fixture_linux as linux

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def setup_job(tmp_path):
    clock = [NOW]
    store = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])
    request = pilot.CodeFixtureInput("actor", "session", "candidate")
    store.register(JobSpec("job", "actor", "session", "code-fixture-pilot", request.step_ref,
                           request.task_ref, NOW + timedelta(minutes=3), 1))
    return store, request, clock


def proof():
    return {"schema_version": "jarvis-code-fixture-proof-v1", "status": "passed",
            "reason": "expected_fixture_outcome", "evidence_mode": "controlled_linux_fixture",
            "scenario": "candidate", "test_count": 3, "passed_count": 3, "failed_count": 0,
            "fixture_sha256": linux.fixture_sha256("candidate"), "image_sha256": linux.IMAGE,
            "cleanup_verified": True, "execution_started": True, "authority": "none",
            "capability_promoted": False}


def test_completed_job_survives_restart_without_another_execution(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    calls = []
    monkeypatch.setattr(linux, "run_code_fixture_linux",
                        lambda **k: calls.append(k) or proof())
    report = pilot.CodeFixtureJobRunner(store, "first").run_once(
        "job", request, authorized=True, expected_version=0)
    reopened = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: NOW)
    again = pilot.CodeFixtureJobRunner(reopened, "second").run_once(
        "job", request, authorized=True, expected_version=report["job"]["version"])
    assert again["job"]["status"] == "succeeded"
    assert again["job"]["attempts"] == 1
    assert again["result_accepted"] is False  # Historical status is not a fresh physical proof.
    assert len(calls) == 1


def test_abandoned_running_claim_after_restart_requires_decision_not_replay(tmp_path,
                                                                           monkeypatch):
    store, request, clock = setup_job(tmp_path)
    claim = store.claim("job", worker_id="lost", actor_ref="actor", session_ref="session",
                        expected_version=0, lease_seconds=1)
    clock[0] += timedelta(seconds=2)
    reopened = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: pytest.fail("replayed"))
    report = pilot.CodeFixtureJobRunner(reopened, "restart").run_once(
        "job", request, authorized=True, expected_version=claim.version)
    assert report["job"]["status"] == "needs_decision"
    assert report["job"]["attempts"] == 1
    assert report["result_accepted"] is False


@pytest.mark.skipif(os.environ.get("JARVIS_CODE_FIXTURE_TEST_AUTHORIZED") != "yes",
                    reason="Physical fixed Docker job proof requires explicit local opt-in")
@pytest.mark.parametrize("scenario", linux.SCENARIOS)
def test_physical_job_fixture_reports_cleanup_and_restart(scenario):
    result = pilot.run_code_fixture_job_pilot(scenario, authorized=True)
    assert result["result_accepted"] is True
    assert result["fixture"]["cleanup_verified"] is True
    assert result["fixture"]["execution_started"] is True
    assert result["restart_status"] == "succeeded"
    assert result["job"]["attempts"] == 1
    assert result["production_memory_opened"] is False
