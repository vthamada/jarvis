"""Opt-in dispatch checkpoint in the jobs ledger, never canonical memory.

The marker is committed before Core is called. A started dispatch is never
replayed; only a trusted Core receipt may reconcile its eventual outcome.
Actor/session references bind scope, not authentication or action authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from math import isfinite

from .store import (
    CODE_FIXTURE_TASKS,
    CORE_TASK,
    DURABLE_CORE_TASK,
    FixtureOutcome,
    JobClaim,
    JobSnapshot,
    JobSpec,
    JobStoreError,
    SqliteJobStore,
    _ref,
    _utc,
)

_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_PHASES = {"prepared", "started", "uncertain", "completed"}
_OUTCOMES = {"succeeded", "failed", "needs_decision"}
_SPEC_FIELDS = (
    "job_id", "actor_ref", "session_ref", "responsibility_ref",
    "approved_step_ref", "task_ref", "deadline", "max_attempts",
)


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _sha(value: object) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise JobStoreError("invalid_receipt_digest")


def _input_digest(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise JobStoreError("invalid_durable_input")
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        raise JobStoreError("invalid_durable_input") from None
    if len(encoded) > 2048:
        raise JobStoreError("invalid_durable_input")
    return hashlib.sha256(encoded).hexdigest()


def durable_request_id(
    job_id: str, actor_ref: str, session_ref: str, input_sha256: str
) -> str:
    """Stable correlation only; not a grant or an executable capability."""
    for value in (job_id, actor_ref, session_ref):
        _ref(value)
    _sha(input_sha256)
    return "durable-job-" + _digest({
        "job_id": job_id, "actor_ref": actor_ref,
        "session_ref": session_ref, "input_sha256": input_sha256,
    })


def durable_session_id(actor_ref: str, session_ref: str) -> str:
    for value in (actor_ref, session_ref):
        _ref(value)
    return "session://durable-job-" + _digest({
        "actor_ref": actor_ref, "session_ref": session_ref,
    })


@dataclass(frozen=True)
class DurableCoreTask:
    job_id: str
    actor_ref: str
    session_ref: str
    input_text: str = field(repr=False)
    input_sha256: str
    request_id: str
    core_session_id: str
    phase: str
    deadline: datetime
    binding_sha256: str
    receipt_sha256: str | None = None
    started_at: datetime | None = None


class DurableCoreJobStore(SqliteJobStore):
    """Explicit dispatch/reconciliation API; construction never resumes work.

    The private input is an operational checkpoint in the same jobs.db. It is
    not indexed, recalled as a fact, returned in telemetry or executable itself.
    Schema v1 and the default SqliteJobStore remain unchanged.
    """

    def __init__(self, path, *, clock=None):
        super().__init__(path, clock=clock)
        with self._connection(write=True) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS durable_core_tasks (
                job_id TEXT PRIMARY KEY REFERENCES fixture_jobs(job_id),
                actor_ref TEXT NOT NULL, session_ref TEXT NOT NULL,
                input_text TEXT NOT NULL, input_sha256 TEXT NOT NULL,
                request_id TEXT NOT NULL, core_session_id TEXT NOT NULL,
                deadline REAL NOT NULL, binding_sha256 TEXT NOT NULL,
                created_at REAL NOT NULL, payload_sha256 TEXT NOT NULL,
                phase TEXT NOT NULL, started_at REAL, receipt_sha256 TEXT,
                result_outcome TEXT
            )""")

    @staticmethod
    def _spec_binding(row) -> str:
        # Match the existing v1 registration fingerprint, using raw row values
        # rather than a round-tripped projection that can conceal field drift.
        values = {name: row[name] for name in _SPEC_FIELDS}
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def _payload_binding(row) -> str:
        return _digest({name: row[name] for name in (
            "job_id", "actor_ref", "session_ref", "input_sha256", "request_id",
            "core_session_id", "deadline", "binding_sha256", "created_at",
        )})

    def _record(self, db, job_id, actor_ref, session_ref):
        row = self._row(db, job_id, actor_ref, session_ref)
        data = db.execute(
            "SELECT * FROM durable_core_tasks WHERE job_id=?", (job_id,)
        ).fetchone()
        try:
            if data is None or row["task_ref"] != DURABLE_CORE_TASK:
                raise JobStoreError("durable_task_unavailable")
            if (
                row["fingerprint"] != self._spec_binding(row)
                or row["fingerprint"] != data["binding_sha256"]
                or data["actor_ref"] != actor_ref
                or data["session_ref"] != session_ref
                or data["deadline"] != row["deadline"]
                or _input_digest(data["input_text"]) != data["input_sha256"]
                or row["approved_step_ref"] != "input-" + data["input_sha256"]
                or data["request_id"] != durable_request_id(
                    job_id, actor_ref, session_ref, data["input_sha256"]
                )
                or data["core_session_id"] != durable_session_id(actor_ref, session_ref)
                or data["payload_sha256"] != self._payload_binding(data)
            ):
                raise JobStoreError("durable_binding_mismatch")
            created = data["created_at"]
            if (
                not isinstance(created, (int, float)) or not isfinite(created)
                or created >= row["deadline"] or row["updated_at"] < created
                or data["phase"] not in _PHASES
            ):
                raise JobStoreError("invalid_durable_record")
            started = data["started_at"]
            receipt = data["receipt_sha256"]
            outcome = data["result_outcome"]
            if data["phase"] == "prepared":
                if started is not None or receipt is not None or outcome is not None:
                    raise JobStoreError("invalid_durable_record")
                if row["status"] in {"succeeded", "failed"}:
                    raise JobStoreError("invalid_durable_record")
            else:
                if (
                    not isinstance(started, (int, float)) or not isfinite(started)
                    or not created <= started < row["deadline"]
                    or started > row["updated_at"] or row["attempts"] != 1
                ):
                    raise JobStoreError("invalid_durable_record")
                if data["phase"] == "completed":
                    _sha(receipt)
                    if outcome not in _OUTCOMES or row["status"] not in {outcome, "cancelled"}:
                        raise JobStoreError("invalid_durable_record")
                elif receipt is not None or outcome is not None:
                    raise JobStoreError("invalid_durable_record")
                elif data["phase"] == "uncertain":
                    if row["status"] not in {"needs_decision", "cancelled"}:
                        raise JobStoreError("invalid_durable_record")
                elif row["status"] not in {"running", "needs_decision", "cancelled", "expired"}:
                    raise JobStoreError("invalid_durable_record")
            task = DurableCoreTask(
                job_id=job_id, actor_ref=actor_ref, session_ref=session_ref,
                input_text=data["input_text"], input_sha256=data["input_sha256"],
                request_id=data["request_id"], core_session_id=data["core_session_id"],
                phase=data["phase"], deadline=datetime.fromtimestamp(data["deadline"], UTC),
                binding_sha256=data["binding_sha256"], receipt_sha256=receipt,
                started_at=datetime.fromtimestamp(started, UTC) if started is not None else None,
            )
            return row, task
        except JobStoreError:
            raise
        except (ValueError, TypeError, OverflowError, OSError, KeyError):
            raise JobStoreError("invalid_durable_record") from None

    def register_task(
        self, job_id: str, *, actor_ref: str, session_ref: str,
        input_text: str, deadline: datetime,
    ) -> JobSnapshot:
        input_sha = _input_digest(input_text)
        spec = JobSpec(
            job_id, actor_ref, session_ref, "core-durable-task", "input-" + input_sha,
            DURABLE_CORE_TASK, deadline, 1,
        )
        values = {name: getattr(spec, name) for name in _SPEC_FIELDS}
        values["deadline"] = _utc(deadline)
        binding = self._spec_binding(values)
        with self._connection(write=True) as db:
            now = self._now()
            existing = db.execute(
                "SELECT * FROM fixture_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            if existing is not None:
                if (existing["actor_ref"] != actor_ref or existing["session_ref"] != session_ref
                        or existing["fingerprint"] != binding):
                    raise JobStoreError("registration_conflict")
                row, task = self._record(db, job_id, actor_ref, session_ref)
                if task.input_text != input_text:
                    raise JobStoreError("registration_conflict")
                return self._snapshot(row)
            if values["deadline"] <= now:
                raise JobStoreError("deadline_expired")
            payload = {
                "job_id": job_id, "actor_ref": actor_ref, "session_ref": session_ref,
                "input_text": input_text, "input_sha256": input_sha,
                "request_id": durable_request_id(job_id, actor_ref, session_ref, input_sha),
                "core_session_id": durable_session_id(actor_ref, session_ref),
                "deadline": values["deadline"], "binding_sha256": binding, "created_at": now,
            }
            payload["payload_sha256"] = self._payload_binding(payload)
            db.execute("""INSERT INTO fixture_jobs (
                job_id,actor_ref,session_ref,responsibility_ref,approved_step_ref,task_ref,
                deadline,max_attempts,fingerprint,status,version,fencing,attempts,
                worker_id,lease_until,last_outcome,updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,'registered',0,0,0,NULL,NULL,NULL,?)""", (
                job_id, actor_ref, session_ref, spec.responsibility_ref, spec.approved_step_ref,
                DURABLE_CORE_TASK, values["deadline"], 1, binding, now,
            ))
            db.execute("""INSERT INTO durable_core_tasks (
                job_id,actor_ref,session_ref,input_text,input_sha256,request_id,core_session_id,
                deadline,binding_sha256,created_at,payload_sha256,phase
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,'prepared')""", tuple(payload[name] for name in (
                "job_id", "actor_ref", "session_ref", "input_text", "input_sha256",
                "request_id", "core_session_id", "deadline", "binding_sha256", "created_at",
                "payload_sha256",
            )))
            row, _ = self._record(db, job_id, actor_ref, session_ref)
            return self._snapshot(row)

    def load_task(self, job_id: str, *, actor_ref: str, session_ref: str) -> DurableCoreTask:
        with self._connection() as db:
            return self._record(db, job_id, actor_ref, session_ref)[1]

    def get(self, job_id: str, *, actor_ref: str, session_ref: str) -> JobSnapshot:
        with self._connection() as db:
            row = self._row(db, job_id, actor_ref, session_ref)
            journaled = db.execute(
                "SELECT 1 FROM durable_core_tasks WHERE job_id=?", (job_id,)
            ).fetchone() is not None
            if row["task_ref"] == DURABLE_CORE_TASK or journaled:
                row, _ = self._record(db, job_id, actor_ref, session_ref)
            return self._snapshot(row)

    def claim_task(
        self, job_id: str, *, worker_id: str, actor_ref: str, session_ref: str,
        expected_version: int, lease_seconds: float = 120,
    ) -> JobClaim | None:
        _ref(worker_id)
        if (isinstance(lease_seconds, bool) or not isinstance(lease_seconds, (int, float))
                or not isfinite(lease_seconds) or not 0 < lease_seconds <= 120):
            raise JobStoreError("invalid_lease")
        with self._connection(write=True) as db:
            now = self._now()
            row, task = self._record(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            if row["status"] not in {"registered", "running"} or task.phase != "prepared":
                return None
            if now >= row["deadline"]:
                self._stop(db, job_id, "expired", "deadline_expired", now)
                return None
            if row["status"] == "running" and now < row["lease_until"]:
                return None
            # Reclaim transfers the same *unstarted* dispatch, not a new attempt.
            attempts = 1
            # Persist the same microsecond precision carried by JobClaim. A
            # fractional float addition can otherwise fail its own strict CAS.
            lease = _utc(datetime.fromtimestamp(min(now + lease_seconds, row["deadline"]), UTC))
            changed = db.execute("""UPDATE fixture_jobs SET status='running',
                version=version+1,fencing=fencing+1,attempts=?,worker_id=?,lease_until=?,
                last_outcome=NULL,updated_at=? WHERE job_id=? AND version=?""", (
                    attempts, worker_id, lease, now, job_id, expected_version,
                )).rowcount
            if changed != 1:
                raise JobStoreError("version_conflict")
            return JobClaim(job_id, actor_ref, session_ref, worker_id,
                            row["version"] + 1, row["fencing"] + 1,
                            datetime.fromtimestamp(lease, UTC))

    def _claim_record(self, db, claim, now, *, allow_expired=False):
        if not isinstance(claim, JobClaim):
            raise JobStoreError("invalid_claim")
        # Revalidate even a trusted callback that mutated a frozen dataclass.
        JobClaim(claim.job_id, claim.actor_ref, claim.session_ref, claim.worker_id,
                 claim.version, claim.fencing, claim.lease_until)
        row, task = self._record(db, claim.job_id, claim.actor_ref, claim.session_ref)
        self._cas(row, claim.version, now)
        if (row["status"] != "running" or row["fencing"] != claim.fencing
                or row["worker_id"] != claim.worker_id
                or row["lease_until"] != _utc(claim.lease_until)):
            raise JobStoreError("claim_conflict")
        if not allow_expired and (now >= row["lease_until"] or now >= row["deadline"]):
            raise JobStoreError("claim_expired")
        return row, task

    def start_dispatch(self, claim: JobClaim) -> DurableCoreTask:
        with self._connection(write=True) as db:
            now = self._now()
            _, task = self._claim_record(db, claim, now)
            if task.phase != "prepared":
                raise JobStoreError("dispatch_already_started")
            db.execute("""UPDATE durable_core_tasks SET phase='started',started_at=?
                WHERE job_id=? AND phase='prepared'""", (now, claim.job_id))
            # Keep claim version stable, but anchor the committed marker's time.
            db.execute("UPDATE fixture_jobs SET updated_at=? WHERE job_id=?", (now, claim.job_id))
            return self._record(db, claim.job_id, claim.actor_ref, claim.session_ref)[1]

    def validate_claim(self, claim: JobClaim) -> JobSnapshot:
        """Last pre-Core check includes the immutable checkpoint, not just lease."""
        if not isinstance(claim, JobClaim):
            raise JobStoreError("invalid_claim")
        with self._connection() as db:
            row = self._row(db, claim.job_id, claim.actor_ref, claim.session_ref)
            journaled = db.execute(
                "SELECT 1 FROM durable_core_tasks WHERE job_id=?", (claim.job_id,)
            ).fetchone() is not None
            if row["task_ref"] == DURABLE_CORE_TASK or journaled:
                row, task = self._claim_record(db, claim, self._now())
                if task.phase != "started":
                    raise JobStoreError("dispatch_not_started")
                return self._snapshot(row)
        return super().validate_claim(claim)

    @staticmethod
    def _receipt(receipt_sha256, outcome):
        _sha(receipt_sha256)
        if not isinstance(outcome, str) or outcome not in _OUTCOMES:
            raise JobStoreError("invalid_outcome")

    def _complete(self, db, row, now, receipt_sha256, outcome, *, revoke):
        db.execute("""UPDATE durable_core_tasks SET phase='completed',receipt_sha256=?,
            result_outcome=? WHERE job_id=?""", (receipt_sha256, outcome, row["job_id"]))
        db.execute("""UPDATE fixture_jobs SET status=?,last_outcome=?,version=version+1,
            fencing=fencing+?,worker_id=NULL,lease_until=NULL,updated_at=?
            WHERE job_id=? AND version=?""", (
                outcome, outcome, int(revoke), now, row["job_id"], row["version"],
            ))
        record, _ = self._record(db, row["job_id"], row["actor_ref"], row["session_ref"])
        return self._snapshot(record)

    def finish_task(
        self, claim: JobClaim, *, receipt_sha256: str, outcome: FixtureOutcome,
    ) -> JobSnapshot:
        self._receipt(receipt_sha256, outcome)
        with self._connection(write=True) as db:
            now = self._now()
            row, task = self._claim_record(db, claim, now)
            if task.phase != "started":
                raise JobStoreError("dispatch_not_started")
            return self._complete(db, row, now, receipt_sha256, outcome, revoke=False)

    def mark_uncertain(self, claim: JobClaim) -> JobSnapshot:
        with self._connection(write=True) as db:
            now = self._now()
            row, task = self._claim_record(db, claim, now, allow_expired=True)
            if task.phase != "started":
                raise JobStoreError("dispatch_not_started")
            db.execute("UPDATE durable_core_tasks SET phase='uncertain' WHERE job_id=?",
                       (claim.job_id,))
            self._stop(db, claim.job_id, "needs_decision", "needs_decision", now)
            record, _ = self._record(db, row["job_id"], row["actor_ref"], row["session_ref"])
            return self._snapshot(record)

    def reconcile_task(
        self, job_id: str, *, actor_ref: str, session_ref: str, expected_version: int,
        receipt_sha256: str, outcome: FixtureOutcome,
    ) -> JobSnapshot:
        """Record an already-verified Core receipt; never redispatch anything."""
        self._receipt(receipt_sha256, outcome)
        with self._connection(write=True) as db:
            now = self._now()
            row, task = self._record(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            eligible = (
                task.phase == "started" and row["status"] == "running"
                and now >= row["lease_until"]
            ) or (task.phase == "uncertain" and row["status"] == "needs_decision")
            if not eligible:
                raise JobStoreError("invalid_reconcile_state")
            return self._complete(db, row, now, receipt_sha256, outcome, revoke=True)

    def _control(self, operation, job_id, actor_ref, session_ref, expected_version):
        with self._connection(write=True) as db:
            now = self._now()
            row = self._row(db, job_id, actor_ref, session_ref)
            journaled = db.execute(
                "SELECT 1 FROM durable_core_tasks WHERE job_id=?", (job_id,)
            ).fetchone() is not None
            if row["task_ref"] == DURABLE_CORE_TASK or journaled:
                row, _ = self._record(db, job_id, actor_ref, session_ref)
            self._cas(row, expected_version, now)
            allowed = {"registered", "running"}
            if operation == "cancel":
                allowed |= {"failed", "needs_decision"}
            elif row["task_ref"] != DURABLE_CORE_TASK:
                # Preserve the base policy for legacy task kinds.
                if row["task_ref"] != CORE_TASK and row["task_ref"] not in CODE_FIXTURE_TASKS:
                    raise JobStoreError("invalid_pause_state")
            if row["status"] not in allowed:
                raise JobStoreError("invalid_" + operation + "_state")
            status = "cancelled" if operation == "cancel" else "needs_decision"
            self._stop(db, job_id, status, status, now)
            record = self._row(db, job_id, actor_ref, session_ref)
            return self._snapshot(record)

    def pause(self, job_id, *, actor_ref, session_ref, expected_version) -> JobSnapshot:
        return self._control("pause", job_id, actor_ref, session_ref, expected_version)

    def cancel(self, job_id, *, actor_ref, session_ref, expected_version) -> JobSnapshot:
        return self._control("cancel", job_id, actor_ref, session_ref, expected_version)
