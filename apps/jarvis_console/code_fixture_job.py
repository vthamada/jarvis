# ruff: noqa: E402
"""Explicit one-shot fixed Docker fixture, composed with the existing job ledger.

No scheduler, arbitrary executor, model, Core grant or production memory access.
Ledger status and Docker are separate transactions. Reopening never retries an
unfinished claim; restart status is not persistence of the physical proof.
"""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from job_service import JobSpec, JobStoreError, SqliteJobStore
from job_service.store import _ref

from tools import run_code_fixture_linux as linux

_COUNTS = {"baseline": (3, 0, 3), "candidate": (3, 3, 0),
           "isolation": (5, 5, 0), "timeout": (0, 0, 0)}
_FIELDS = {"schema_version", "status", "reason", "evidence_mode", "scenario", "test_count",
           "passed_count", "failed_count", "fixture_sha256", "image_sha256",
           "cleanup_verified", "execution_started", "authority", "capability_promoted"}


@dataclass(frozen=True)
class CodeFixtureInput:
    """Caller scope labels and a literal fixture binding, never authorization."""

    actor_ref: str
    session_ref: str
    scenario: str

    def __post_init__(self):
        _ref(self.actor_ref)
        _ref(self.session_ref)
        if type(self.scenario) is not str or self.scenario not in linux.SCENARIOS:
            raise JobStoreError("unsupported_code_fixture")

    @property
    def task_ref(self):
        return "code-fixture:" + self.scenario

    @property
    def step_ref(self):
        return "fixture-" + self.scenario + "-" + linux.fixture_sha256(self.scenario)


def _cancelled(callback):
    if callback is None:
        return False
    try:
        value = callback()
    except (Exception, KeyboardInterrupt):
        raise JobStoreError("invalid_cancellation") from None
    if type(value) is not bool:
        raise JobStoreError("invalid_cancellation")
    return value


def _options(timeout_seconds, lease_seconds, cancelled):
    if (type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds) or not 0.1 <= timeout_seconds <= 30
            or type(lease_seconds) not in (int, float) or not math.isfinite(lease_seconds)
            or not timeout_seconds + 35 <= lease_seconds <= 120
            or cancelled is not None and not callable(cancelled)):
        raise JobStoreError("invalid_fixture_job_options")


def _verified(value, request):
    if type(value) is not dict or set(value) != _FIELDS:
        return False
    if any(type(value[key]) is not str for key in (
        "schema_version", "status", "reason", "evidence_mode", "scenario",
        "fixture_sha256", "image_sha256", "authority",
    )):
        return False
    return (
        value["schema_version"] == "jarvis-code-fixture-proof-v1"
        and value["status"] == "passed"
        and value["reason"] == ("expected_timeout" if request.scenario == "timeout"
                                else "expected_fixture_outcome")
        and value["evidence_mode"] == "controlled_linux_fixture"
        and value["scenario"] == request.scenario
        and value["fixture_sha256"] == linux.fixture_sha256(request.scenario)
        and value["image_sha256"] == linux.IMAGE
        and value["cleanup_verified"] is True and value["execution_started"] is True
        and value["authority"] == "none" and value["capability_promoted"] is False
        and all(type(value[key]) is int for key in ("test_count", "passed_count", "failed_count"))
        and tuple(value[key] for key in ("test_count", "passed_count", "failed_count"))
        == _COUNTS[request.scenario]
    )


def _bound(snapshot, request):
    return (snapshot.spec.task_ref == request.task_ref
            and snapshot.spec.approved_step_ref == request.step_ref
            and snapshot.spec.responsibility_ref == "code-fixture-pilot"
            and snapshot.spec.max_attempts == 1)


class CodeFixtureJobRunner:
    """Trusted local composition only; no user-supplied runner or command port."""

    def __init__(self, store: SqliteJobStore, worker_id: str):
        if not isinstance(store, SqliteJobStore):
            raise JobStoreError("invalid_code_fixture_store")
        _ref(worker_id)
        self.store, self.worker_id = store, worker_id

    def run_once(self, job_id, request, *, authorized=False, expected_version,
                 lease_seconds=120, timeout_seconds=10, cancelled=None):
        if authorized is not True:
            raise JobStoreError("fixture_job_opt_in_required")
        if not isinstance(request, CodeFixtureInput):
            raise JobStoreError("invalid_code_fixture_input")
        _options(timeout_seconds, lease_seconds, cancelled)
        scope = {"actor_ref": request.actor_ref, "session_ref": request.session_ref}
        before = self.store.get(job_id, **scope)
        if not _bound(before, request):
            raise JobStoreError("code_fixture_binding_refused")
        result = {"schema_version": "jarvis-code-fixture-job-v1", "result_accepted": False,
                  "fixture": None, "fixture_invoked": False, "review_required": True,
                  "all_fixture_assertions_passed": False, "authority": "none",
                  "capability_promoted": False, "automatic_execution": False,
                  "cross_ledger_atomic": False, "exactly_once_claimed": False,
                  "physical_proof_persisted": False}
        if _cancelled(cancelled):
            final = self.store.cancel(job_id, expected_version=expected_version, **scope)
            result["job"] = final.telemetry()
            return result
        claim = self.store.claim(job_id, worker_id=self.worker_id,
                                 expected_version=expected_version, lease_seconds=lease_seconds,
                                 **scope)
        if claim is None:
            result["job"] = self.store.get(job_id, **scope).telemetry()
            return result

        interrupted = False

        def interruption_requested():
            nonlocal interrupted
            if interrupted:
                return True
            try:
                interrupted = (not _bound(self.store.validate_claim(claim), request)
                               or _cancelled(cancelled))
            except (Exception, KeyboardInterrupt):
                interrupted = True
            return interrupted

        try:
            if not _bound(self.store.validate_claim(claim), request):
                raise JobStoreError("code_fixture_binding_refused")
            # The store's trusted infrastructure clock is also used by CAS.
            # Reserve budget for the runner's preflight and mandatory cleanup;
            # its timeout is per subprocess, not a global wall-clock guarantee.
            remaining = claim.lease_until.timestamp() - self.store._now()
            bounded_timeout = min(timeout_seconds, remaining - 35)
            if bounded_timeout < 0.1 or interruption_requested():
                raise JobStoreError("fixture_claim_unavailable")
            result["fixture_invoked"] = True
            value = linux.run_code_fixture_linux(authorized=True, scenario=request.scenario,
                                                 timeout_seconds=bounded_timeout,
                                                 cancelled=interruption_requested)
            if not _bound(self.store.validate_claim(claim), request):
                raise JobStoreError("code_fixture_binding_refused")
            if interruption_requested() or not _verified(value, request):
                raise JobStoreError("fixture_proof_unconfirmed")
            final = self.store.finish(claim, "succeeded")
            result.update(result_accepted=True, review_required=False, fixture=dict(value),
                          all_fixture_assertions_passed=request.scenario in {
                              "candidate", "isolation"})
        except (Exception, KeyboardInterrupt):
            # Never overwrite a concurrent cancel/fence, and never repeat Docker.
            current = self.store.get(job_id, **scope)
            if current.status == "running" and current.version == claim.version:
                try:
                    self.store.pause(job_id, expected_version=current.version, **scope)
                except JobStoreError:
                    pass
            final = self.store.get(job_id, **scope)
        result["job"] = final.telemetry()
        return result


def run_code_fixture_job_pilot(scenario="candidate", *, authorized=False, timeout_seconds=10):
    if authorized is not True:
        raise JobStoreError("fixture_job_opt_in_required")
    request = CodeFixtureInput("local-pilot", "isolated-code-fixture-job", scenario)
    _options(timeout_seconds, 120, None)
    base = Path(tempfile.gettempdir()).resolve(strict=True)
    workspace = Path(__file__).resolve().parents[2]
    if not base.is_dir() or base.is_relative_to(workspace):
        raise JobStoreError("private_runtime_required")
    with tempfile.TemporaryDirectory(prefix="jarvis-code-fixture-job-", dir=base) as temporary:
        path = Path(temporary) / "jobs.db"
        store = SqliteJobStore(path)
        store.register(JobSpec("pilot-job", request.actor_ref, request.session_ref,
                               "code-fixture-pilot", request.step_ref, request.task_ref,
                               datetime.now(UTC) + timedelta(minutes=3), 1))
        result = CodeFixtureJobRunner(store, "pilot-worker").run_once(
            "pilot-job", request, authorized=True, expected_version=0,
            timeout_seconds=timeout_seconds)
        reopened = SqliteJobStore(path)
        result["restart_status"] = reopened.get(
            "pilot-job", actor_ref=request.actor_ref, session_ref=request.session_ref).status
        result.update(pilot_mode="isolated_code_fixture_job", runtime_mode="temporary_sqlite",
                      production_memory_opened=False)
        return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise JobStoreError("invalid_arguments")


def main(argv=None):
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--scenario", choices=linux.SCENARIOS, default="candidate")
    parser.add_argument("--timeout-seconds", type=float, default=10)
    try:
        options = parser.parse_args(argv)
        result = run_code_fixture_job_pilot(options.scenario, authorized=options.authorized,
                                           timeout_seconds=options.timeout_seconds)
        code = 0 if result["result_accepted"] else 2
    except (Exception, KeyboardInterrupt):
        result = {"status": "refused", "reason": "code_fixture_job_refused"}
        code = 2
    try:
        print(json.dumps(result, sort_keys=True))
    except (OSError, UnicodeError):
        return 2
    return code


if __name__ == "__main__":
    raise SystemExit(main())
