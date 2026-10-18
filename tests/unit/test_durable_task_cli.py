"""Explicit persistent task input, privacy, native dispatch and restart controls."""

import io
import json
from pathlib import Path

import pytest

from apps.jarvis_console import durable_task_cli as cli
from apps.jarvis_console import durable_task_runner as runner_module

QUERY = "Compare documentation and observability pilot reports."
SCOPE = {"job_id": "task-one", "actor_ref": "operator", "session_ref": "daily"}


def _submit(tmp_path, **changes):
    options = dict(
        runtime_dir=tmp_path / "private-tasks", authorized=True, confirmed=True,
        document={"schema_version": cli.INPUT_SCHEMA, "query": QUERY}, **SCOPE,
    )
    options.update(changes)
    return cli.operate_task("submit", **options)


@pytest.mark.parametrize("change", [
    {"authorized": False}, {"confirmed": False}, {"confirmed": "yes"},
    {"job_id": "../../job"}, {"actor_ref": "a b"}, {"session_ref": "a/b"},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": QUERY, "action": "run"}},
    {"document": {"schema_version": "unknown", "query": QUERY}},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": " "}},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": "x" * 2049}},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": "Bearer secret-token"}},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": "Hello\u200b"}},
    {"document": {"schema_version": cli.INPUT_SCHEMA, "query": "Hello\u007f"}},
    {"deadline_seconds": True}, {"deadline_seconds": 0}, {"include_content": True},
])
def test_invalid_submission_does_not_create_runtime(tmp_path, change):
    with pytest.raises(ValueError):
        _submit(tmp_path, **change)
    assert not (tmp_path / "private-tasks").exists()


def test_submit_persists_input_but_never_constructs_core(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_isolated_core", lambda _: pytest.fail("submit invoked Core"))
    result = _submit(tmp_path)
    runtime = tmp_path / "private-tasks"
    assert result["job"]["status"] == "registered"
    assert result["checkpoint_phase"] == "prepared"
    assert result["input_persisted"] is True and result["core_invoked"] is False
    assert QUERY not in json.dumps(result)
    assert not (runtime / "memory.db").exists() and not (runtime / "events.db").exists()
    task = cli.DurableCoreJobStore(runtime / "jobs.db").load_task(
        SCOPE["job_id"], actor_ref=SCOPE["actor_ref"], session_ref=SCOPE["session_ref"],
    )
    assert task.input_text == QUERY
    assert QUERY not in repr(task)


@pytest.mark.parametrize("location", ["relative", "onedrive", "populated", "root"])
def test_private_location_preflight_does_not_create_job_db(tmp_path, location):
    if location == "relative":
        path = Path("not-absolute")
    elif location == "onedrive":
        path = tmp_path / "OneDrive" / "tasks"
    elif location == "populated":
        path = tmp_path / "existing"
        path.mkdir()
        (path / "unrelated.txt").write_text("preserve", encoding="utf-8")
    else:
        path = Path(tmp_path.anchor)
    with pytest.raises(ValueError):
        _submit(tmp_path, runtime_dir=path)
    assert not (path / "jobs.db").exists()
    if location == "populated":
        assert (path / "unrelated.txt").read_text(encoding="utf-8") == "preserve"


@pytest.mark.parametrize("change", [{"expected_version": 3}, {"actor_ref": "other"}])
def test_bad_scope_and_stale_version_do_not_open_core(tmp_path, monkeypatch, change):
    _submit(tmp_path)
    monkeypatch.setattr(cli, "_isolated_core", lambda _: pytest.fail("bad scope opened Core"))
    options = dict(runtime_dir=tmp_path / "private-tasks", authorized=True,
                   expected_version=0, **SCOPE)
    options.update(change)
    with pytest.raises(ValueError):
        cli.operate_task("resume", **options)


@pytest.mark.parametrize("phase", ["prepared", "started"])
def test_active_claim_does_not_read_unsettled_canonical_databases(tmp_path, monkeypatch, phase):
    _submit(tmp_path)
    runtime = tmp_path / "private-tasks"
    store = cli.DurableCoreJobStore(runtime / "jobs.db")
    scope = {"actor_ref": SCOPE["actor_ref"], "session_ref": SCOPE["session_ref"]}
    claim = store.claim_task(SCOPE["job_id"], worker_id="active", expected_version=0, **scope)
    if phase == "started":
        store.start_dispatch(claim)
    core = cli._isolated_core(runtime)
    monkeypatch.setattr(
        runner_module, "find_core_receipt",
        lambda *_args: pytest.fail("busy recovery inspected a potentially changing database"),
    )
    monkeypatch.setattr(core, "handle_input", lambda _: pytest.fail("busy recovery entered Core"))
    monkeypatch.setattr(
        core.memory_service.repository, "fetch_runtime_request_claim",
        lambda _: pytest.fail("busy recovery inspected a potentially changing claim database"),
    )
    result = runner_module.DurableCoreJobRunner(store, core, "waiting").resume(
        SCOPE["job_id"], expected_version=claim.version, authorized=True, **scope,
    )
    assert result["evidence_mode"] == "active_claim"
    assert not result["core_invoked"] and not result["result_recorded"]
    assert store.get(SCOPE["job_id"], **scope).version == claim.version


def test_cli_active_claim_does_not_construct_core(tmp_path, monkeypatch):
    _submit(tmp_path)
    runtime = tmp_path / "private-tasks"
    store = cli.DurableCoreJobStore(runtime / "jobs.db")
    scope = {"actor_ref": SCOPE["actor_ref"], "session_ref": SCOPE["session_ref"]}
    claim = store.claim_task(SCOPE["job_id"], worker_id="active", expected_version=0, **scope)
    store.start_dispatch(claim)
    monkeypatch.setattr(cli, "_isolated_core", lambda _: pytest.fail("busy CLI initialized Core"))
    result = cli.operate_task(
        "resume", runtime_dir=runtime, expected_version=claim.version, authorized=True, **SCOPE,
    )
    assert result["evidence_mode"] == "active_claim" and not result["core_invoked"]
    assert not (runtime / "memory.db").exists() and not (runtime / "events.db").exists()


@pytest.mark.parametrize("query", ["Hello\u200b", "Hello\u007f"])
def test_runner_refuses_unreceiptable_text_before_claim_or_core(tmp_path, monkeypatch, query):
    from datetime import UTC, datetime, timedelta

    runtime = tmp_path / "private-tasks"
    store = cli.DurableCoreJobStore(runtime / "jobs.db")
    scope = {"actor_ref": SCOPE["actor_ref"], "session_ref": SCOPE["session_ref"]}
    store.register_task(SCOPE["job_id"], input_text=query,
                        deadline=datetime.now(UTC) + timedelta(minutes=10), **scope)
    core = cli._isolated_core(runtime)
    monkeypatch.setattr(core, "handle_input", lambda _: pytest.fail("invalid text entered Core"))
    with pytest.raises(ValueError):
        runner_module.DurableCoreJobRunner(store, core, "worker").resume(
            SCOPE["job_id"], expected_version=0, authorized=True, **scope,
        )
    snapshot = store.get(SCOPE["job_id"], **scope)
    task = store.load_task(SCOPE["job_id"], **scope)
    assert snapshot.status == "registered" and snapshot.attempts == 0
    assert core.memory_service.repository.fetch_runtime_request_claim(task.request_id) is None


def test_real_submit_resume_reopen_keeps_one_canonical_answer(tmp_path):
    submitted = _submit(tmp_path)
    options = dict(runtime_dir=tmp_path / "private-tasks", authorized=True, **SCOPE)
    first = cli.operate_task("resume", expected_version=submitted["job"]["version"], **options)
    assert first["result_recorded"] and first["canonical_final_verified"]
    assert first["core_invoked"] and not first["recovered_result"]
    assert QUERY not in json.dumps(first) and "response_text" not in first
    again = cli.operate_task(
        "resume", expected_version=first["job"]["version"], include_content=True, **options,
    )
    assert again["recovered_result"] and again["result_recorded"]
    assert not again["core_invoked"] and again["job"] == first["job"]
    core = cli._isolated_core(tmp_path / "private-tasks")
    task = cli.DurableCoreJobStore(tmp_path / "private-tasks" / "jobs.db").load_task(
        SCOPE["job_id"], actor_ref=SCOPE["actor_ref"], session_ref=SCOPE["session_ref"],
    )
    turns = core.memory_service.repository.fetch_recent_turns(task.core_session_id, 10)
    assert len(turns) == 1 and turns[0].request_content == QUERY
    assert again["content_included"] and again["response_text"] == turns[0].response_text
    assert not again["operator_authenticated"] and not again["action_authority"]
    assert not again["runtime_capability_promoted"] and not again["automatic_execution"]


@pytest.mark.parametrize("operation", ["cancel", "pause"])
def test_stop_before_dispatch_preserved_after_resume(tmp_path, operation):
    _submit(tmp_path)
    options = dict(runtime_dir=tmp_path / "private-tasks", authorized=True, **SCOPE)
    stopped = cli.operate_task(operation, expected_version=0, **options)
    resumed = cli.operate_task("resume", expected_version=stopped["job"]["version"], **options)
    assert not resumed["core_invoked"] and not resumed["result_recorded"]
    assert resumed["job"]["status"] == ("cancelled" if operation == "cancel" else "needs_decision")


def test_cli_parse_refuses_without_echo_or_storage(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "operate_task", lambda *a, **k: pytest.fail("invalid args dispatched"))
    monkeypatch.setattr("sys.stdin", io.StringIO("private data"))
    code = cli.main(["resume", "--runtime-dir", str(tmp_path), "--job-id", "private-job"])
    assert code == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "refused", "error_code": "durable_task_cli_refused",
    }
