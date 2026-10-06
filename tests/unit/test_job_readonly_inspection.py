"""Actual SQLite file proofs, not a worker or authentication claim."""

import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from job_service import readonly
from job_service.readonly import JobInspectionError
from job_service.store import CORE_TASK, JobSpec, SqliteJobStore

from apps.jarvis_console.job_inspect_cli import build_job_inspection

NOW = datetime(2026, 10, 5, 12, tzinfo=UTC)
ACTOR = "private-actor"
SESSION = "private-session"


def seed(tmp_path, *, task="fixture:success", job_id="private-job", actor=ACTOR):
    path = tmp_path / "jobs.sqlite3"
    store = SqliteJobStore(path, clock=lambda: NOW)
    spec = JobSpec(
        job_id,
        actor,
        SESSION,
        "core-assist-pilot" if task == CORE_TASK else "private-responsibility",
        "input-" + "a" * 64 if task == CORE_TASK else "private-approved-step",
        task,
        NOW + timedelta(minutes=30),
        1 if task == CORE_TASK else 3,
    )
    store.register(spec)
    return path, store


def inspect(path, **kwargs):
    return build_job_inspection(
        path, actor_ref=ACTOR, session_ref=SESSION, job_ids=("private-job",), **kwargs
    )


def inventory(directory):
    return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


def update(path, assignments):
    with sqlite3.connect(path) as db:
        db.execute("UPDATE fixture_jobs SET " + assignments)


def test_actual_existing_projection_is_readonly_and_redacted(tmp_path, monkeypatch):
    path, _ = seed(tmp_path)
    before = inventory(tmp_path)
    # Inspection must not construct/create/migrate the writable store.
    monkeypatch.setattr(SqliteJobStore, "__init__", lambda *_a, **_k: pytest.fail("writer"))
    result = inspect(path)
    assert result["schema_version"] == "jarvis-job-inspection-v1"
    assert result["read_only"] is True
    assert result["authority"] == "none"
    assert result["scope_binding"] == "caller_supplied_not_authentication"
    assert result["job_count"] == 1
    assert result["jobs"][0]["status"] == "registered"
    assert result["jobs"][0]["evidence_mode"] == "fixture"
    assert result["jobs"][0]["lease_present"] is False
    output = json.dumps(result)
    for private in ("private", str(path), "input-", "worker_id", "deadline", "fingerprint"):
        assert private not in output
    assert inventory(tmp_path) == before


def test_explicit_refs_only_validated_bounded_metadata(tmp_path):
    path, _ = seed(tmp_path)
    refs = inspect(path, include_refs=True)["jobs"][0]["references"]
    assert refs["job_id"] == "private-job"
    assert refs["actor_ref"] == ACTOR
    assert refs["session_ref"] == SESSION
    assert refs["worker_id"] is None
    assert "source" not in refs


def test_uri_metacharacters_in_existing_filename_are_escaped(tmp_path):
    path, _ = seed(tmp_path)
    escaped = tmp_path / "jobs#archive%name&mode=rw.sqlite3"
    path.rename(escaped)
    before = inventory(tmp_path)
    assert inspect(escaped)["job_count"] == 1
    assert inventory(tmp_path) == before


def test_non_path_and_unc_and_stream_input_are_sanitized(tmp_path):
    for path in (
        "private-source",
        Path("//server/private/jobs.sqlite3"),
        tmp_path / "jobs.sqlite3:private-stream",
    ):
        with pytest.raises(JobInspectionError, match="^job_inspection_source_unsafe$"):
            inspect(path)


def test_exact_maximum_jobs_without_foreign_enumeration(tmp_path):
    path, store = seed(tmp_path)
    jobs = ("private-job",) + tuple(f"private-job-{i}" for i in range(31))
    for job_id in jobs[1:]:
        store.register(
            JobSpec(
                job_id,
                ACTOR,
                SESSION,
                "responsibility",
                "approval",
                "fixture:success",
                NOW + timedelta(days=1),
            )
        )
    before = inventory(tmp_path)
    result = build_job_inspection(path, actor_ref=ACTOR, session_ref=SESSION, job_ids=jobs)
    assert result["job_count"] == 32
    assert len(result["jobs"]) == 32
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("task", ["fixture:success", CORE_TASK])
def test_claim_not_finished_reconciled_or_replayed_on_inspection(tmp_path, task):
    path, store = seed(tmp_path, task=task)
    claim = store.claim(
        "private-job",
        worker_id="private-worker",
        actor_ref=ACTOR,
        session_ref=SESSION,
        expected_version=0,
        lease_seconds=1,
    )
    assert claim is not None
    before = inventory(tmp_path)
    result = inspect(path)
    assert result["jobs"][0]["status"] == "running"
    assert result["jobs"][0]["fencing"] == 1
    assert result["jobs"][0]["attempts"] == 1
    assert result["jobs"][0]["lease_present"] is True
    # Actual wall clock is later than fixture lease. Reopen the inspection and
    # prove it does not call mutating claim/reconcile behavior on stale leases.
    assert inspect(path) == result
    assert inventory(tmp_path) == before
    restored = SqliteJobStore(path, clock=lambda: NOW + timedelta(days=5)).get(
        "private-job", actor_ref=ACTOR, session_ref=SESSION
    )
    assert restored.status == "running" and restored.worker_id == "private-worker"


@pytest.mark.parametrize(
    "actor,session,ids",
    [
        ("foreign", SESSION, ("private-job",)),
        (ACTOR, "foreign", ("private-job",)),
        (ACTOR, SESSION, ("missing",)),
        (ACTOR, SESSION, ("private-job", "missing")),
    ],
)
def test_unavailable_scope_all_or_nothing_no_partial_or_counts(tmp_path, actor, session, ids):
    path, _ = seed(tmp_path)
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_job_unavailable$") as error:
        build_job_inspection(path, actor_ref=actor, session_ref=session, job_ids=ids)
    assert "private" not in str(error.value)
    assert inventory(tmp_path) == before


def test_only_requested_bound_jobs_are_read_not_foreign_invalid_rows(tmp_path):
    path, store = seed(tmp_path)
    spec = JobSpec(
        "foreign-job",
        "other-actor",
        SESSION,
        "responsibility",
        "approved",
        "fixture:success",
        NOW + timedelta(days=1),
    )
    store.register(spec)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE fixture_jobs SET fingerprint='bad' WHERE job_id='foreign-job'")
    assert inspect(path)["job_count"] == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"actor_ref": "../actor"},
        {"session_ref": 7},
        {"job_ids": []},
        {"job_ids": ()},
        {"job_ids": ("private-job",) * 2},
        {"job_ids": tuple(f"job-{i}" for i in range(33))},
        {"job_ids": ("x" * 129,)},
        {"job_ids": ("injected\n",)},
        {"include_refs": 1},
    ],
)
def test_invalid_inputs_never_touch_source(tmp_path, monkeypatch, kwargs):
    monkeypatch.setattr(readonly, "_preflight", lambda _p: pytest.fail("source opened"))
    args = {"actor_ref": ACTOR, "session_ref": SESSION, "job_ids": ("private-job",)}
    args.update(kwargs)
    with pytest.raises(JobInspectionError, match="^job_inspection_input_invalid$"):
        build_job_inspection(tmp_path / "absent.sqlite3", **args)


def test_missing_file_not_created_and_no_parent_created(tmp_path):
    path = tmp_path / "absent" / "jobs.sqlite3"
    with pytest.raises(JobInspectionError, match="^job_inspection_source_unavailable$"):
        inspect(path)
    assert not path.parent.exists()


@pytest.mark.parametrize("kind", ["relative", "traversal", "directory", "empty", "oversized"])
def test_unsafe_paths_and_sizes_refused(tmp_path, kind):
    path, _ = seed(tmp_path)
    if kind == "relative":
        path = Path("jobs.sqlite3")
    elif kind == "traversal":
        path = tmp_path / "other" / ".." / "jobs.sqlite3"
    elif kind == "directory":
        path = tmp_path
    elif kind == "empty":
        path = tmp_path / "empty.sqlite3"
        path.touch()
    else:
        path = tmp_path / "large.sqlite3"
        with path.open("wb") as stream:
            stream.truncate(readonly.MAX_DATABASE_BYTES + 1)
    with pytest.raises(JobInspectionError, match="^job_inspection_source_unsafe$"):
        inspect(path)


def test_hard_link_refused_without_changing_alias(tmp_path):
    path, _ = seed(tmp_path)
    alias = tmp_path / "alias.sqlite3"
    os.link(path, alias)
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_source_unsafe$"):
        inspect(path)
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("parent", [False, True])
def test_symlink_file_or_parent_refused(tmp_path, parent):
    root = tmp_path / "actual"
    root.mkdir()
    path, _ = seed(root)
    link = tmp_path / "alias"
    try:
        link.symlink_to(root if parent else path, target_is_directory=parent)
    except OSError:
        pytest.skip("Host does not permit test symlink creation")
    with pytest.raises(JobInspectionError, match="^job_inspection_source_unsafe$"):
        inspect(link / path.name if parent else link)


@pytest.mark.parametrize("suffix", ["-wal", "-shm", "-journal"])
def test_sidecars_refused_even_if_empty(tmp_path, suffix):
    path, _ = seed(tmp_path)
    (tmp_path / (path.name + suffix)).touch()
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_source_not_quiescent$"):
        inspect(path)
    assert inventory(tmp_path) == before


def test_closed_wal_database_header_refused_without_creating_sidecars(tmp_path):
    path, _ = seed(tmp_path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_source_not_quiescent$"):
        inspect(path)
    assert inventory(tmp_path) == before


@pytest.mark.parametrize(
    "assignment",
    [
        "status='unsupported'",
        "fingerprint='bad'",
        "version=-1",
        "attempts=99",
        "fencing=99",
        "worker_id='worker'",
        "last_outcome='private-content'",
        "deadline='secret-text'",
        "updated_at='secret-text'",
        "approved_step_ref=zeroblob(131072)",
        "lease_until=zeroblob(131072)",
        "approved_step_ref='../../secret'",
    ],
)
def test_invalid_rows_fail_closed_fixed_errors_no_source_leaks(tmp_path, assignment):
    path, _ = seed(tmp_path)
    update(path, assignment)
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_record_invalid$"):
        inspect(path, include_refs=True)
    assert inventory(tmp_path) == before


@pytest.mark.parametrize("change", ["version", "column", "view"])
def test_schema_not_migrated_or_accepted(tmp_path, change):
    path, _ = seed(tmp_path)
    with sqlite3.connect(path) as db:
        if change == "version":
            db.execute("PRAGMA user_version=2")
        elif change == "column":
            db.execute("ALTER TABLE fixture_jobs ADD COLUMN unknown TEXT")
        else:
            db.execute("DROP TABLE fixture_jobs")
            db.execute("CREATE VIEW fixture_jobs AS SELECT 'private-source' AS job_id")
    before = inventory(tmp_path)
    with pytest.raises(JobInspectionError, match="^job_inspection_schema_unsupported$"):
        inspect(path)
    assert inventory(tmp_path) == before


def test_mutation_during_read_refused_not_concurrent_snapshot_claim(tmp_path, monkeypatch):
    path, _ = seed(tmp_path)
    original = readonly._project

    def project(*args):
        result = original(*args)
        # Metadata-only drift injected at the source preflight boundary. No
        # claim that this check detects an adversarial same-UID restoration.
        info = path.stat()
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1000000000))
        return result

    monkeypatch.setattr(readonly, "_project", project)
    with pytest.raises(JobInspectionError, match="^job_inspection_source_not_quiescent$"):
        inspect(path)


def test_connection_uri_readonly_query_only_and_no_immutable(tmp_path, monkeypatch):
    path, _ = seed(tmp_path)
    connect = sqlite3.connect
    observed = []

    def checked(source_uri, **kwargs):
        assert source_uri == path.as_uri() + "?mode=ro"
        assert "immutable" not in source_uri
        assert kwargs["uri"] is True
        db = connect(source_uri, **kwargs)
        db.set_trace_callback(observed.append)
        return db

    monkeypatch.setattr(readonly.sqlite3, "connect", checked)
    inspect(path)
    assert "PRAGMA query_only=ON" in observed
    assert "BEGIN" in observed
    assert "ROLLBACK" in observed
    assert not any(statement.startswith(("UPDATE", "INSERT", "CREATE")) for statement in observed)
