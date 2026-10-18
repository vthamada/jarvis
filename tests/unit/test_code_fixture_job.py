"""Fixed Docker fixture jobs never become a generic or replayable executor."""

import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from job_service import JobSpec, JobStoreError, SqliteJobStore
from job_service.worker import FixtureJobWorker

from apps.jarvis_console import code_fixture_job as pilot
from tools import run_code_fixture_linux as linux

NOW = datetime(2026, 10, 14, tzinfo=UTC)


def setup_job(tmp_path, scenario="candidate"):
    clock = [NOW]
    store = SqliteJobStore(tmp_path / "jobs.db", clock=lambda: clock[0])
    request = pilot.CodeFixtureInput("actor", "session", scenario)
    spec = JobSpec("job", request.actor_ref, request.session_ref, "code-fixture-pilot",
                   request.step_ref, request.task_ref, NOW + timedelta(minutes=3), 1)
    store.register(spec)
    return store, request, clock


def proof(scenario):
    counts = {"baseline": (3, 0, 3), "candidate": (3, 3, 0),
              "isolation": (5, 5, 0), "timeout": (0, 0, 0)}[scenario]
    return {"schema_version": "jarvis-code-fixture-proof-v1", "status": "passed",
            "reason": "expected_timeout" if scenario == "timeout" else "expected_fixture_outcome",
            "evidence_mode": "controlled_linux_fixture", "scenario": scenario,
            "test_count": counts[0], "passed_count": counts[1], "failed_count": counts[2],
            "fixture_sha256": linux.fixture_sha256(scenario), "image_sha256": linux.IMAGE,
            "cleanup_verified": True, "execution_started": True, "authority": "none",
            "capability_promoted": False}


@pytest.mark.parametrize("scenario", linux.SCENARIOS)
def test_exact_fixed_proof_completes_one_job_without_promoting_capability(tmp_path, monkeypatch,
                                                                        scenario):
    store, request, _ = setup_job(tmp_path, scenario)
    calls = []

    def runner(**options):
        calls.append(options)
        assert options["cancelled"]() is False
        return proof(scenario)

    monkeypatch.setattr(linux, "run_code_fixture_linux", runner)
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert len(calls) == 1
    assert calls[0]["scenario"] == scenario and calls[0]["authorized"] is True
    assert report["job"]["status"] == "succeeded"
    assert report["job"]["attempts"] == 1
    assert report["job"]["evidence_mode"] == "fixture"
    assert report["result_accepted"] is True
    assert report["fixture"]["failed_count"] == (3 if scenario == "baseline" else 0)
    assert report["all_fixture_assertions_passed"] is (scenario in {"candidate", "isolation"})
    assert report["authority"] == "none"
    assert report["capability_promoted"] is False
    assert report["cross_ledger_atomic"] is False


@pytest.mark.parametrize("authorized", [False, None, 1, "yes"])
def test_authorization_precedes_any_store_or_runner_access(tmp_path, monkeypatch, authorized):
    store, request, _ = setup_job(tmp_path)
    monkeypatch.setattr(store, "get", lambda *a, **k: pytest.fail("unauthorized read"))
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: pytest.fail("runner invoked"))
    with pytest.raises(JobStoreError, match="fixture_job_opt_in_required"):
        pilot.CodeFixtureJobRunner(store, "worker").run_once(
            "job", request, authorized=authorized, expected_version=0)


def test_fixed_fixture_worker_refuses_new_task_before_claim(tmp_path, monkeypatch):
    store, _, _ = setup_job(tmp_path)
    monkeypatch.setattr(store, "claim", lambda *a, **k: pytest.fail("claimed fixture job"))
    with pytest.raises(JobStoreError, match="fixture_worker_code_refused"):
        FixtureJobWorker(store, "worker").run_once(
            "job", actor_ref="actor", session_ref="session", expected_version=0)


@pytest.mark.parametrize("field,value", [
    ("cleanup_verified", False), ("execution_started", False),
    ("scenario", "baseline"), ("fixture_sha256", "0" * 64),
    ("image_sha256", "sha256:" + "0" * 64), ("authority", "action"),
    ("capability_promoted", True), ("test_count", True), ("failed_count", 1),
    ("status", "failed"), ("reason", "unexpected"), ("evidence_mode", "fixture"),
    ("schema_version", "other"), ("private_output", "secret"),
])
def test_uncertain_or_tampered_proof_requires_decision(tmp_path, monkeypatch, field, value):
    store, request, _ = setup_job(tmp_path)
    result = proof("candidate")
    result[field] = value
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: result)
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert report["job"]["status"] == "needs_decision"
    assert report["result_accepted"] is False
    assert report["fixture"] is None
    assert "secret" not in str(report)


@pytest.mark.parametrize("error", [RuntimeError("secret/path"), KeyboardInterrupt()])
def test_runner_failure_is_sanitized_and_never_retried(tmp_path, monkeypatch, error):
    store, request, _ = setup_job(tmp_path)

    def broken(**options):
        raise error

    monkeypatch.setattr(linux, "run_code_fixture_linux", broken)
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert report["job"]["status"] == "needs_decision"
    assert "secret" not in str(report)
    with pytest.raises(JobStoreError, match="code_fixture_replay_refused"):
        store.retry("job", actor_ref="actor", session_ref="session",
                    expected_version=report["job"]["version"])


def test_cancelled_before_claim_has_zero_attempts(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: pytest.fail("cancel ignored"))
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0, cancelled=lambda: True)
    assert report["job"]["status"] == "cancelled"
    assert report["job"]["attempts"] == 0


def test_cancellation_during_fixture_preserves_external_fence(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)

    def cancelled_runner(**options):
        store.cancel("job", actor_ref="actor", session_ref="session", expected_version=1)
        assert options["cancelled"]() is True
        return proof("candidate")

    monkeypatch.setattr(linux, "run_code_fixture_linux", cancelled_runner)
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert report["job"]["status"] == "cancelled"
    assert report["result_accepted"] is False
    assert report["fixture"] is None


def test_expired_claim_never_accepts_proof_or_replays(tmp_path, monkeypatch):
    store, request, clock = setup_job(tmp_path)

    def expired_runner(**options):
        clock[0] += timedelta(seconds=121)
        assert options["cancelled"]() is True
        return proof("candidate")

    monkeypatch.setattr(linux, "run_code_fixture_linux", expired_runner)
    runner = pilot.CodeFixtureJobRunner(store, "worker")
    report = runner.run_once("job", request, authorized=True, expected_version=0)
    assert report["job"]["status"] == "needs_decision"
    assert report["result_accepted"] is False
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: pytest.fail("replayed"))
    again = runner.run_once("job", request, authorized=True,
                            expected_version=report["job"]["version"])
    assert again["job"]["attempts"] == 1


@pytest.mark.parametrize("change", [{"max_attempts": 2}, {"responsibility_ref": "other"},
                                    {"approved_step_ref": "step"}])
def test_job_spec_requires_nonreplayable_fixed_binding(tmp_path, change):
    store, request, _ = setup_job(tmp_path)
    spec = store.get("job", actor_ref="actor", session_ref="session").spec
    with pytest.raises(JobStoreError, match="invalid_code_fixture_binding"):
        replace(spec, **change)


def test_request_binding_mismatch_is_rejected_before_claim(tmp_path, monkeypatch):
    store, _, _ = setup_job(tmp_path)
    request = pilot.CodeFixtureInput("actor", "session", "baseline")
    monkeypatch.setattr(store, "claim", lambda *a, **k: pytest.fail("mismatched claim"))
    with pytest.raises(JobStoreError, match="code_fixture_binding_refused"):
        pilot.CodeFixtureJobRunner(store, "worker").run_once(
            "job", request, authorized=True, expected_version=0)


@pytest.mark.parametrize("scenario", ["arbitrary", True, None, ["candidate"]])
def test_request_is_literal_allowlist_only(scenario):
    with pytest.raises(JobStoreError, match="unsupported_code_fixture"):
        pilot.CodeFixtureInput("actor", "session", scenario)


def test_pilot_authorization_precedes_temp_filesystem(monkeypatch):
    monkeypatch.setattr(pilot.tempfile, "gettempdir", lambda: pytest.fail("filesystem reached"))
    with pytest.raises(JobStoreError, match="fixture_job_opt_in_required"):
        pilot.run_code_fixture_job_pilot(authorized=False)


@pytest.mark.parametrize("options", [{"timeout_seconds": True}, {"timeout_seconds": 31},
                                     {"timeout_seconds": float("nan")}, {"lease_seconds": 30},
                                     {"lease_seconds": 121}, {"cancelled": True}])
def test_invalid_budget_rejected_before_store_read(tmp_path, monkeypatch, options):
    store, request, _ = setup_job(tmp_path)
    monkeypatch.setattr(store, "get", lambda *a, **k: pytest.fail("invalid options reached store"))
    with pytest.raises(JobStoreError, match="invalid_fixture_job_options"):
        pilot.CodeFixtureJobRunner(store, "worker").run_once(
            "job", request, authorized=True, expected_version=0, **options)


def test_short_job_deadline_does_not_start_docker(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    spec = store.get("job", actor_ref="actor", session_ref="session").spec
    store.register(replace(spec, job_id="short", deadline=NOW + timedelta(seconds=10)))
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: pytest.fail("budget ignored"))
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "short", request, authorized=True, expected_version=0)
    assert report["fixture_invoked"] is False
    assert report["job"]["status"] == "needs_decision"


def test_matching_scenario_with_wrong_hash_is_refused_before_claim(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    spec = store.get("job", actor_ref="actor", session_ref="session").spec
    store.register(replace(spec, job_id="wrong",
                           approved_step_ref="fixture-candidate-" + "0" * 64))
    monkeypatch.setattr(store, "claim", lambda *a, **k: pytest.fail("wrong hash claimed"))
    with pytest.raises(JobStoreError, match="code_fixture_binding_refused"):
        pilot.CodeFixtureJobRunner(store, "worker").run_once(
            "wrong", request, authorized=True, expected_version=0)


def test_callback_exception_after_claim_aborts_without_private_reflection(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    calls = [0]

    def callback():
        calls[0] += 1
        if calls[0] == 1:
            return False
        raise RuntimeError("private-session")

    monkeypatch.setattr(linux, "run_code_fixture_linux",
                        lambda **k: pytest.fail("invalid callback"))
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0, cancelled=callback)
    assert report["fixture_invoked"] is False
    assert report["job"]["status"] == "needs_decision"
    assert "private-session" not in str(report)


@pytest.mark.parametrize("mode", ["true", "raises", "nonbool"])
def test_cancellation_during_runner_is_sticky_even_after_valid_proof(tmp_path, monkeypatch, mode):
    store, request, _ = setup_job(tmp_path)
    phase = ["before"]

    def callback():
        if phase[0] != "during":
            return False
        if mode == "raises":
            raise RuntimeError("private-cancellation")
        return True if mode == "true" else "not-a-bool"

    def runner(**options):
        phase[0] = "during"
        assert options["cancelled"]() is True
        phase[0] = "after"
        assert options["cancelled"]() is True
        return proof("candidate")

    monkeypatch.setattr(linux, "run_code_fixture_linux", runner)
    report = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0, cancelled=callback)
    assert report["job"]["status"] == "needs_decision"
    assert report["result_accepted"] is False
    assert report["fixture"] is None
    assert "private-cancellation" not in str(report)


@pytest.mark.parametrize("mode", ["raises", "nonbool"])
def test_invalid_cancellation_before_claim_is_sanitized(tmp_path, monkeypatch, mode):
    store, request, _ = setup_job(tmp_path)

    def callback():
        if mode == "raises":
            raise RuntimeError("private-error")
        return 1

    monkeypatch.setattr(store, "claim", lambda *a, **k: pytest.fail("invalid callback claimed"))
    with pytest.raises(JobStoreError, match="^invalid_cancellation$"):
        pilot.CodeFixtureJobRunner(store, "worker").run_once(
            "job", request, authorized=True, expected_version=0, cancelled=callback)
    assert store.get("job", actor_ref="actor", session_ref="session").attempts == 0


def test_late_proof_is_rejected_even_when_runner_never_polls_callback(tmp_path, monkeypatch):
    store, request, clock = setup_job(tmp_path)

    def runner(**options):
        clock[0] += timedelta(seconds=121)
        return proof("candidate")

    monkeypatch.setattr(linux, "run_code_fixture_linux", runner)
    result = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert result["result_accepted"] is False
    assert result["job"]["status"] == "needs_decision"


def test_finish_storage_failure_never_accepts_proof_or_replays(tmp_path, monkeypatch):
    store, request, _ = setup_job(tmp_path)
    monkeypatch.setattr(linux, "run_code_fixture_linux", lambda **k: proof("candidate"))

    def failed_finish(*args, **options):
        raise JobStoreError("storage_unavailable")

    monkeypatch.setattr(store, "finish", failed_finish)
    result = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert result["job"]["status"] == "needs_decision"
    assert result["result_accepted"] is False
    assert result["fixture"] is None


def test_cli_output_failure_is_not_retried_or_reflected(monkeypatch):
    calls = []
    monkeypatch.setattr(pilot, "run_code_fixture_job_pilot",
                        lambda *a, **k: {"result_accepted": True})

    def broken_output(*args, **options):
        calls.append(args)
        raise BrokenPipeError("private-path")

    monkeypatch.setattr("builtins.print", broken_output)
    assert pilot.main(["--authorized"]) == 2
    assert len(calls) == 1


@pytest.mark.parametrize("timing", ["claim", "after_fixture"])
def test_changed_binding_after_initial_read_never_accepts_or_runs_wrong_task(tmp_path,
                                                                          monkeypatch, timing):
    store, request, _ = setup_job(tmp_path)
    alternate = pilot.CodeFixtureInput("actor", "session", "baseline")

    def mutate_binding():
        with sqlite3.connect(tmp_path / "jobs.db") as db:
            db.execute("UPDATE fixture_jobs SET task_ref=?, approved_step_ref=? WHERE job_id='job'",
                       (alternate.task_ref, alternate.step_ref))

    if timing == "claim":
        original = store.claim

        def claim(*args, **options):
            mutate_binding()
            return original(*args, **options)

        monkeypatch.setattr(store, "claim", claim)
        monkeypatch.setattr(linux, "run_code_fixture_linux",
                            lambda **k: pytest.fail("different bound task executed"))
    else:
        def runner(**options):
            mutate_binding()
            return proof("candidate")

        monkeypatch.setattr(linux, "run_code_fixture_linux", runner)
    result = pilot.CodeFixtureJobRunner(store, "worker").run_once(
        "job", request, authorized=True, expected_version=0)
    assert result["result_accepted"] is False
    assert result["fixture"] is None
    assert result["job"]["status"] == "needs_decision"
    assert result["fixture_invoked"] is (timing == "after_fixture")
