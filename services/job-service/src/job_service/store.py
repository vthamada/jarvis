"""SQLite CAS/fencing ledger for explicit, metadata-only fixture work."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Callable, Literal

JobStatus = Literal[
    "registered",
    "running",
    "succeeded",
    "failed",
    "needs_decision",
    "cancelled",
    "expired",
]
FixtureOutcome = Literal["succeeded", "failed", "needs_decision"]
CORE_TASK = "core:assist_only"
_TASKS = {"fixture:success", "fixture:failure", "fixture:needs_decision", CORE_TASK}
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class JobStoreError(ValueError):
    """Sanitized, stable reason only; never source, SQL, paths or exceptions."""


def _ref(value: object) -> None:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise JobStoreError("invalid_reference")


def _utc(value: object) -> float:
    if (
        not isinstance(value, datetime)
        or value.utcoffset() is None
        or value.utcoffset().total_seconds()
    ):
        raise JobStoreError("invalid_utc_time")
    stamp = value.timestamp()
    if not isfinite(stamp):
        raise JobStoreError("invalid_utc_time")
    return stamp


def _version(value: int) -> None:
    if type(value) is not int or not 0 <= value < 2**60:
        raise JobStoreError("invalid_version")


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    actor_ref: str
    session_ref: str
    responsibility_ref: str
    approved_step_ref: str
    task_ref: str
    deadline: datetime
    max_attempts: int = 3

    def __post_init__(self) -> None:
        for value in (
            self.job_id,
            self.actor_ref,
            self.session_ref,
            self.responsibility_ref,
            self.approved_step_ref,
        ):
            _ref(value)
        if not isinstance(self.task_ref, str) or self.task_ref not in _TASKS:
            raise JobStoreError("unsupported_fixture_task")
        _utc(self.deadline)
        if type(self.max_attempts) is not int or not 1 <= self.max_attempts <= 10:
            raise JobStoreError("invalid_attempt_limit")
        if self.task_ref == CORE_TASK and (
            self.max_attempts != 1
            or self.responsibility_ref != "core-assist-pilot"
            or not re.fullmatch(r"input-[a-f0-9]{64}", self.approved_step_ref)
        ):
            raise JobStoreError("invalid_core_binding")


@dataclass(frozen=True)
class JobSnapshot:
    spec: JobSpec
    status: JobStatus
    version: int
    fencing: int
    attempts: int
    worker_id: str | None
    lease_until: datetime | None
    last_outcome: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.spec, JobSpec):
            raise JobStoreError("invalid_record")
        if self.status not in {
            "registered",
            "running",
            "succeeded",
            "failed",
            "needs_decision",
            "cancelled",
            "expired",
        }:
            raise JobStoreError("invalid_record")
        _version(self.version)
        _version(self.fencing)
        if (
            type(self.attempts) is not int
            or not 0 <= self.attempts <= self.spec.max_attempts
            or not self.attempts <= self.fencing <= self.version
        ):
            raise JobStoreError("invalid_record")
        if self.last_outcome not in {
            None,
            "succeeded",
            "failed",
            "needs_decision",
            "cancelled",
            "deadline_expired",
            "attempts_exhausted",
            "retry_requested",
        }:
            raise JobStoreError("invalid_record")
        if self.status == "running":
            _ref(self.worker_id)
            if self.lease_until is None or not self.attempts:
                raise JobStoreError("invalid_record")
            if _utc(self.lease_until) > _utc(self.spec.deadline):
                raise JobStoreError("invalid_record")
        elif self.worker_id is not None or self.lease_until is not None:
            raise JobStoreError("invalid_record")

    def telemetry(self) -> dict[str, object]:
        return {
            "event": "job_state" if self.spec.task_ref == CORE_TASK else "fixture_job_state",
            "status": self.status,
            "version": self.version,
            "fencing": self.fencing,
            "attempts": self.attempts,
            "max_attempts": self.spec.max_attempts,
            "lease_present": self.lease_until is not None,
            "last_outcome": self.last_outcome,
            "evidence_mode": "metadata_ledger" if self.spec.task_ref == CORE_TASK else "fixture",
            "action_authority": False,
            "automatic_execution": False,
        }


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    actor_ref: str
    session_ref: str
    worker_id: str
    version: int
    fencing: int
    lease_until: datetime

    def __post_init__(self) -> None:
        for value in (self.job_id, self.actor_ref, self.session_ref, self.worker_id):
            _ref(value)
        _version(self.version)
        _version(self.fencing)
        _utc(self.lease_until)


class SqliteJobStore:
    """No worker/scheduler startup on construction or reopen.

    Actor/session are scope bindings, not authentication. Core must authenticate
    their caller; responsibility/approval references do not constitute grants.
    Clock is trusted infrastructure. Reclaim does not provide exactly-once effects.
    """

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] | None = None):
        if str(path) == ":memory:":
            raise JobStoreError("durable_path_required")
        if not callable(clock) and clock is not None:
            raise JobStoreError("invalid_clock")
        self._path = Path(path)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection(write=True) as db:
            schema = db.execute("PRAGMA user_version").fetchone()[0]
            if schema not in {0, 1}:
                raise JobStoreError("unsupported_schema")
            db.execute("""CREATE TABLE IF NOT EXISTS fixture_jobs (
                job_id TEXT PRIMARY KEY, actor_ref TEXT NOT NULL, session_ref TEXT NOT NULL,
                responsibility_ref TEXT NOT NULL, approved_step_ref TEXT NOT NULL,
                task_ref TEXT NOT NULL, deadline REAL NOT NULL, max_attempts INTEGER NOT NULL,
                fingerprint TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL,
                fencing INTEGER NOT NULL, attempts INTEGER NOT NULL, worker_id TEXT,
                lease_until REAL, last_outcome TEXT, updated_at REAL NOT NULL
            )""")
            db.execute("PRAGMA user_version=1")

    @contextmanager
    def _connection(self, *, write: bool = False):
        db = None
        try:
            db = sqlite3.connect(str(self._path), timeout=5, isolation_level=None)
            db.row_factory = sqlite3.Row
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except sqlite3.Error:
            if db is not None:
                db.rollback()
            raise JobStoreError("storage_unavailable") from None
        except Exception:
            if db is not None:
                db.rollback()
            raise
        finally:
            if db is not None:
                db.close()

    def _now(self) -> float:
        try:
            return _utc(self._clock())
        except Exception:
            raise JobStoreError("invalid_clock") from None

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> JobSnapshot:
        try:
            spec = JobSpec(
                row["job_id"],
                row["actor_ref"],
                row["session_ref"],
                row["responsibility_ref"],
                row["approved_step_ref"],
                row["task_ref"],
                datetime.fromtimestamp(row["deadline"], UTC),
                row["max_attempts"],
            )
            return JobSnapshot(
                spec,
                row["status"],
                row["version"],
                row["fencing"],
                row["attempts"],
                row["worker_id"],
                datetime.fromtimestamp(row["lease_until"], UTC)
                if row["lease_until"] is not None
                else None,
                row["last_outcome"],
            )
        except (ValueError, TypeError, OverflowError, OSError):
            raise JobStoreError("invalid_record") from None

    @staticmethod
    def _row(db, job_id: str, actor_ref: str, session_ref: str):
        for value in (job_id, actor_ref, session_ref):
            _ref(value)
        row = db.execute("SELECT * FROM fixture_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None or row["actor_ref"] != actor_ref or row["session_ref"] != session_ref:
            raise JobStoreError("job_unavailable")
        SqliteJobStore._snapshot(row)
        if not isinstance(row["updated_at"], (int, float)) or not isfinite(row["updated_at"]):
            raise JobStoreError("invalid_record")
        return row

    @staticmethod
    def _cas(row, expected_version: int, now: float) -> None:
        _version(expected_version)
        if row["version"] != expected_version:
            raise JobStoreError("version_conflict")
        if now < row["updated_at"]:
            raise JobStoreError("clock_regressed")

    def register(self, spec: JobSpec) -> JobSnapshot:
        if not isinstance(spec, JobSpec):
            raise JobStoreError("invalid_job_spec")
        values = asdict(spec)
        values["deadline"] = _utc(spec.deadline)
        fingerprint = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        with self._connection(write=True) as db:
            now = self._now()
            row = db.execute("SELECT * FROM fixture_jobs WHERE job_id=?", (spec.job_id,)).fetchone()
            if row is not None:
                if (
                    row["actor_ref"] != spec.actor_ref
                    or row["session_ref"] != spec.session_ref
                    or row["fingerprint"] != fingerprint
                ):
                    raise JobStoreError("registration_conflict")
                return self._snapshot(row)
            if values["deadline"] <= now:
                raise JobStoreError("deadline_expired")
            db.execute(
                """INSERT INTO fixture_jobs VALUES (
                ?,?,?,?,?,?,?,?,?, 'registered',0,0,0,NULL,NULL,NULL,?
            )""",
                (
                    spec.job_id,
                    spec.actor_ref,
                    spec.session_ref,
                    spec.responsibility_ref,
                    spec.approved_step_ref,
                    spec.task_ref,
                    values["deadline"],
                    spec.max_attempts,
                    fingerprint,
                    now,
                ),
            )
            return self._snapshot(self._row(db, spec.job_id, spec.actor_ref, spec.session_ref))

    def get(self, job_id: str, *, actor_ref: str, session_ref: str) -> JobSnapshot:
        with self._connection() as db:
            return self._snapshot(self._row(db, job_id, actor_ref, session_ref))

    def claim(
        self,
        job_id: str,
        *,
        worker_id: str,
        actor_ref: str,
        session_ref: str,
        expected_version: int,
        lease_seconds: float = 30,
    ) -> JobClaim | None:
        _ref(worker_id)
        if (
            isinstance(lease_seconds, bool)
            or not isinstance(lease_seconds, (float, int))
            or not isfinite(lease_seconds)
            or not 0 < lease_seconds <= 120
        ):
            raise JobStoreError("invalid_lease")
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            if row["status"] not in {"registered", "running"}:
                return None
            # A started Core turn may already have canonical memory. Never replay it.
            if row["task_ref"] == CORE_TASK and row["status"] == "running":
                if now >= row["lease_until"]:
                    self._stop(db, job_id, "needs_decision", "needs_decision", now)
                return None
            if now >= row["deadline"]:
                self._stop(db, job_id, "expired", "deadline_expired", now)
                return None
            if row["status"] == "running" and now < row["lease_until"]:
                return None
            if row["attempts"] >= row["max_attempts"]:
                self._stop(db, job_id, "failed", "attempts_exhausted", now)
                return None
            lease_until = min(now + lease_seconds, row["deadline"])
            db.execute(
                """UPDATE fixture_jobs SET status='running', version=version+1,
                fencing=fencing+1, attempts=attempts+1, worker_id=?, lease_until=?,
                last_outcome=NULL, updated_at=? WHERE job_id=? AND version=?""",
                (worker_id, lease_until, now, job_id, expected_version),
            )
            return JobClaim(
                job_id,
                actor_ref,
                session_ref,
                worker_id,
                row["version"] + 1,
                row["fencing"] + 1,
                datetime.fromtimestamp(lease_until, UTC),
            )

    @staticmethod
    def _stop(db, job_id: str, status: str, outcome: str, now: float) -> None:
        db.execute(
            """UPDATE fixture_jobs SET status=?, last_outcome=?, version=version+1,
            fencing=fencing+1, worker_id=NULL, lease_until=NULL, updated_at=? WHERE job_id=?""",
            (status, outcome, now, job_id),
        )

    def finish(self, claim: JobClaim, outcome: FixtureOutcome) -> JobSnapshot:
        if (
            not isinstance(claim, JobClaim)
            or not isinstance(outcome, str)
            or outcome
            not in {
                "succeeded",
                "failed",
                "needs_decision",
            }
        ):
            raise JobStoreError("invalid_outcome")
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, claim.job_id, claim.actor_ref, claim.session_ref)
            self._cas(row, claim.version, now)
            if (
                row["status"] != "running"
                or row["fencing"] != claim.fencing
                or row["worker_id"] != claim.worker_id
                or row["lease_until"] != _utc(claim.lease_until)
            ):
                raise JobStoreError("claim_conflict")
            if now >= row["lease_until"] or now >= row["deadline"]:
                raise JobStoreError("claim_expired")
            db.execute(
                """UPDATE fixture_jobs SET status=?, last_outcome=?, version=version+1,
                worker_id=NULL, lease_until=NULL, updated_at=? WHERE job_id=? AND version=?""",
                (outcome, outcome, now, claim.job_id, claim.version),
            )
            return self._snapshot(self._row(db, claim.job_id, claim.actor_ref, claim.session_ref))

    def validate_claim(self, claim: JobClaim) -> JobSnapshot:
        """Preflight only; cannot make a separate Core ledger transaction atomic."""
        if not isinstance(claim, JobClaim):
            raise JobStoreError("invalid_claim")
        with self._connection() as db:
            now = self._now()
            row = self._row(db, claim.job_id, claim.actor_ref, claim.session_ref)
            self._cas(row, claim.version, now)
            if (
                row["status"] != "running"
                or row["fencing"] != claim.fencing
                or row["worker_id"] != claim.worker_id
                or row["lease_until"] != _utc(claim.lease_until)
            ):
                raise JobStoreError("claim_conflict")
            if now >= row["lease_until"] or now >= row["deadline"]:
                raise JobStoreError("claim_expired")
            return self._snapshot(row)

    def pause(
        self, job_id: str, *, actor_ref: str, session_ref: str, expected_version: int
    ) -> JobSnapshot:
        """Revoke a pilot claim; no resume grant or interruption of an active Core."""
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            if row["task_ref"] != CORE_TASK or row["status"] not in {"registered", "running"}:
                raise JobStoreError("invalid_pause_state")
            self._stop(db, job_id, "needs_decision", "needs_decision", now)
            return self._snapshot(self._row(db, job_id, actor_ref, session_ref))

    def cancel(
        self, job_id: str, *, actor_ref: str, session_ref: str, expected_version: int
    ) -> JobSnapshot:
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            if row["status"] not in {"registered", "running", "failed", "needs_decision"}:
                raise JobStoreError("invalid_cancel_state")
            self._stop(db, job_id, "cancelled", "cancelled", now)
            return self._snapshot(self._row(db, job_id, actor_ref, session_ref))

    def retry(
        self, job_id: str, *, actor_ref: str, session_ref: str, expected_version: int
    ) -> JobSnapshot:
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            if row["task_ref"] == CORE_TASK:
                raise JobStoreError("core_replay_refused")
            if row["status"] != "failed":
                raise JobStoreError("invalid_retry_state")
            if row["attempts"] >= row["max_attempts"]:
                raise JobStoreError("attempts_exhausted")
            if now >= row["deadline"]:
                raise JobStoreError("deadline_expired")
            self._stop(db, job_id, "registered", "retry_requested", now)
            return self._snapshot(self._row(db, job_id, actor_ref, session_ref))
