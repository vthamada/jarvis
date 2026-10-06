"""Bounded inspection of a quiescent, existing local Job ledger.

This reader never constructs the writable store, migrates, reconciles a clock,
or starts a worker. Caller-supplied scope is a binding, not authentication.
Path/stat checks are preflight under the trusted host, not an adversarial FD
sandbox or a promise of a consistent snapshot of a concurrently changing file.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import stat
from dataclasses import asdict
from math import isfinite
from pathlib import Path

from job_service.store import JobStoreError, SqliteJobStore

MAX_DATABASE_BYTES = 128 * 1024 * 1024
MAX_JOBS = 32
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_COLUMNS = (
    ("job_id", "TEXT", 0, 1),
    ("actor_ref", "TEXT", 1, 0),
    ("session_ref", "TEXT", 1, 0),
    ("responsibility_ref", "TEXT", 1, 0),
    ("approved_step_ref", "TEXT", 1, 0),
    ("task_ref", "TEXT", 1, 0),
    ("deadline", "REAL", 1, 0),
    ("max_attempts", "INTEGER", 1, 0),
    ("fingerprint", "TEXT", 1, 0),
    ("status", "TEXT", 1, 0),
    ("version", "INTEGER", 1, 0),
    ("fencing", "INTEGER", 1, 0),
    ("attempts", "INTEGER", 1, 0),
    ("worker_id", "TEXT", 0, 0),
    ("lease_until", "REAL", 0, 0),
    ("last_outcome", "TEXT", 0, 0),
    ("updated_at", "REAL", 1, 0),
)
_TEXT_COLUMNS = tuple(name for name, kind, _, _ in _COLUMNS if kind == "TEXT")


class JobInspectionError(ValueError):
    """Fixed codes only; no source paths, identifiers, SQL or exception detail."""


def _fail(code: str) -> None:
    raise JobInspectionError("job_inspection_" + code)


def _valid_ref(value: object) -> bool:
    return type(value) is str and _REF.fullmatch(value) is not None


def _identity(info) -> tuple:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_nlink,
        info.st_mode,
    )


def _preflight(path: Path) -> tuple:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or ".." in path.parts
        or str(path).startswith(("\\\\", "//"))
        or any(":" in part for part in path.parts[1:])
    ):
        _fail("source_unsafe")
    try:
        # lstat every component: resolve() would hide symlinks/reparse points.
        for component in (*reversed(path.parents), path):
            info = component.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                _fail("source_unsafe")
            if component != path and not stat.S_ISDIR(info.st_mode):
                _fail("source_unsafe")
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            _fail("source_unsafe")
        if not 100 <= info.st_size <= MAX_DATABASE_BYTES:
            _fail("source_unsafe")
        for suffix in ("-wal", "-shm", "-journal"):
            try:
                path.with_name(path.name + suffix).lstat()
            except FileNotFoundError:
                continue
            _fail("source_not_quiescent")
        with path.open("rb") as source:
            header = source.read(100)
        if header[:16] != b"SQLite format 3\x00":
            _fail("schema_unsupported")
        # Both SQLite write/read versions must use rollback-journal format.
        if header[18:20] != b"\x01\x01":
            _fail("source_not_quiescent")
        return _identity(info)
    except OSError:
        _fail("source_unavailable")


def _schema(db: sqlite3.Connection) -> None:
    if db.execute("PRAGMA user_version").fetchone()[0] != 1:
        _fail("schema_unsupported")
    if db.execute("PRAGMA journal_mode").fetchone()[0] != "delete":
        _fail("source_not_quiescent")
    tables = db.execute("SELECT type FROM sqlite_schema WHERE name='fixture_jobs'").fetchall()
    if len(tables) != 1 or tables[0][0] != "table":
        _fail("schema_unsupported")
    columns = db.execute("PRAGMA table_xinfo(fixture_jobs)").fetchall()
    if tuple((r[1], r[2], r[3], r[5]) for r in columns) != _COLUMNS or any(
        r[6] != 0 for r in columns
    ):
        _fail("schema_unsupported")


def _project(
    db: sqlite3.Connection, job_id: str, actor_ref: str, session_ref: str, include_refs: bool
) -> dict:
    # Length/type checks happen in SQLite before any untrusted large text is
    # allocated by the Python sqlite adapter. Inspect only explicit bound jobs.
    guard = " OR ".join(
        f"({name} IS NOT NULL AND (typeof({name})!='text' OR length({name})>128))"
        for name in _TEXT_COLUMNS
    )
    guard += " OR " + " OR ".join(
        f"({name} IS NOT NULL AND typeof({name}) NOT IN ('integer','real'))"
        for name, kind, _, _ in _COLUMNS
        if kind != "TEXT"
    )
    bounded = db.execute(
        f"SELECT actor_ref=?, session_ref=?, ({guard}) FROM fixture_jobs WHERE job_id=?",
        (actor_ref, session_ref, job_id),
    ).fetchall()
    if len(bounded) != 1 or bounded[0][0] != 1 or bounded[0][1] != 1:
        _fail("job_unavailable")
    if bounded[0][2]:
        _fail("record_invalid")
    row = db.execute("SELECT * FROM fixture_jobs WHERE job_id=?", (job_id,)).fetchone()
    try:
        snapshot = SqliteJobStore._snapshot(row)
        if type(row["updated_at"]) not in (int, float) or not isfinite(row["updated_at"]):
            _fail("record_invalid")
        values = asdict(snapshot.spec)
        values["deadline"] = snapshot.spec.deadline.timestamp()
        expected = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
        if row["fingerprint"] != expected:
            _fail("record_invalid")
    except (JobStoreError, ValueError, TypeError, OverflowError, OSError):
        _fail("record_invalid")
    result = snapshot.telemetry()
    if include_refs:
        result["references"] = {
            "job_id": snapshot.spec.job_id,
            "actor_ref": snapshot.spec.actor_ref,
            "session_ref": snapshot.spec.session_ref,
            "responsibility_ref": snapshot.spec.responsibility_ref,
            "approved_step_ref": snapshot.spec.approved_step_ref,
            "task_ref": snapshot.spec.task_ref,
            "worker_id": snapshot.worker_id,
        }
    return result


def build_job_inspection(
    database_path: Path,
    *,
    actor_ref: str,
    session_ref: str,
    job_ids: tuple[str, ...],
    include_refs: bool = False,
) -> dict:
    """All-or-nothing projection from an existing, closed DELETE-mode ledger.

    No identifiers are disclosed by default, no foreign jobs are enumerated,
    and even an expired running claim remains running (no clock reconciliation).
    include_refs is explicit disclosure of bounded references, not a grant.
    """
    if (
        not _valid_ref(actor_ref)
        or not _valid_ref(session_ref)
        or type(job_ids) is not tuple
        or not 1 <= len(job_ids) <= MAX_JOBS
        or any(not _valid_ref(job_id) for job_id in job_ids)
        or len(set(job_ids)) != len(job_ids)
        or type(include_refs) is not bool
    ):
        _fail("input_invalid")
    before = _preflight(database_path)
    db = None
    try:
        # URI escaping via as_uri prevents path text from injecting SQLite URI
        # options. No immutable=1: it would conceal live WAL/change behavior.
        db = sqlite3.connect(
            database_path.as_uri() + "?mode=ro", uri=True, timeout=0, isolation_level=None
        )
        db.row_factory = sqlite3.Row
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16384)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192)
        db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 64)
        budget = 2000

        def progress() -> int:
            nonlocal budget
            budget -= 1
            return int(budget <= 0)

        db.set_progress_handler(progress, 1000)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("BEGIN")
        _schema(db)
        jobs = [_project(db, job_id, actor_ref, session_ref, include_refs) for job_id in job_ids]
        db.rollback()
    except sqlite3.DataError:
        _fail("record_invalid")
    except sqlite3.Error:
        _fail("storage_unavailable")
    finally:
        if db is not None:
            db.close()
        if _preflight(database_path) != before:
            _fail("source_not_quiescent")
    return {
        "schema_version": "jarvis-job-inspection-v1",
        "read_only": True,
        "authority": "none",
        "scope_binding": "caller_supplied_not_authentication",
        "source_mode": "quiescent_existing_local_sqlite",
        "job_count": len(jobs),
        "jobs": jobs,
    }
