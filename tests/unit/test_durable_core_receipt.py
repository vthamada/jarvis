"""Real Core/SQLite finals and deliberately inconsistent private test stores."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import ExitStack
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from job_service.store import JobStoreError

from apps.jarvis_console import durable_core_receipt as module
from apps.jarvis_console.durable_core_receipt import find_core_receipt
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, PermissionDecision, RequestId, SessionId


@dataclass(frozen=True)
class Task:
    job_id: str = "receipt-job"
    actor_ref: str = "receipt-actor"
    session_ref: str = "receipt-session"
    input_text: str = "Compare documentation and observability pilot reports."
    input_sha256: str = ""
    request_id: str = "durable-receipt-request"
    core_session_id: str = "session://durable-receipt-test"
    phase: str = "started"
    started_at: datetime | None = None
    deadline: datetime | None = None
    binding_sha256: str = "b" * 64
    receipt_sha256: str | None = None


def task_at_now():
    now = datetime.now(UTC)
    task = Task(started_at=now - timedelta(seconds=2), deadline=now + timedelta(seconds=120))
    return replace(task, input_sha256=hashlib.sha256(task.input_text.encode("utf-8")).hexdigest())


def contract_for(task):
    return InputContract(
        request_id=RequestId(task.request_id), session_id=SessionId(task.core_session_id),
        channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=task.input_text,
        timestamp=datetime.now(UTC).isoformat(), user_id=f"user://{task.actor_ref}",
        canonical_user_ref=f"user://{task.actor_ref}",
        operator_identity_ref=f"operator://{task.actor_ref}",
        surface_id="surface://durable-core-task", surface_kind="console",
        surface_session_id=task.core_session_id, surface_capability_scope=[],
        requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
    )


@pytest.fixture
def completed(tmp_path):
    core = _isolated_core(tmp_path / "runtime")
    task = task_at_now()
    response = core.handle_input(contract_for(task))
    assert response.operation_dispatch is None and response.adapter_grant is None
    subflow = next(event.payload for event in response.events
                   if event.event_name == "specialist_subflow_completed")
    assert subflow["selection_count"] == 0
    assert subflow["invocation_count"] == 0
    assert subflow["contribution_count"] == 0
    return core, task, response


def events_path(core):
    return core.observability_service.repository.database_path


def update_event(core, name, *, envelope=None, payload=None):
    with sqlite3.connect(events_path(core)) as db:
        row = db.execute("SELECT event_id, payload FROM internal_events WHERE event_name=?",
                         (name,)).fetchone()
        assert row is not None
        if payload is not None:
            data = json.loads(row[1])
            payload(data)
            db.execute("UPDATE internal_events SET payload=? WHERE event_id=?",
                       (json.dumps(data), row[0]))
        for key, value in (envelope or {}).items():
            assert key in {"source_service", "request_id", "correlation_id", "session_id",
                           "mission_id", "timestamp", "operation_id"}
            db.execute(f"UPDATE internal_events SET {key}=? WHERE event_id=?", (value, row[0]))


def assert_refused(core, task):
    with pytest.raises(JobStoreError, match="^durable_receipt_refused$") as caught:
        find_core_receipt(core, task)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None


def test_recovers_exact_native_final_and_receipt_after_restart(completed, tmp_path):
    core, task, response = completed
    receipt = find_core_receipt(core, task)
    assert receipt is not None
    assert receipt.response_text == response.response_text
    assert receipt.request_id == task.request_id
    assert receipt.memory_record_id == str(response.memory_record.memory_record_id)
    assert receipt.query_sha256 == task.input_sha256
    assert receipt.response_sha256 == hashlib.sha256(response.response_text.encode()).hexdigest()
    assert receipt.outcome == ("succeeded" if response.governance_decision.decision.value == "allow"
                               else "needs_decision")
    assert receipt.event_count == len(response.events)
    restarted = _isolated_core(tmp_path / "runtime")
    assert find_core_receipt(restarted, task) == receipt
    assert find_core_receipt(restarted, replace(
        task, phase="completed", receipt_sha256=receipt.receipt_sha256,
    )) == receipt
    assert_refused(restarted, replace(task, phase="completed", receipt_sha256="0" * 64))
    assert response.response_text not in repr(receipt)


def test_absent_claim_and_events_is_unknown_not_a_fabricated_final(tmp_path):
    core = _isolated_core(tmp_path / "runtime")
    assert find_core_receipt(core, task_at_now()) is None


def test_canonical_receipt_works_without_optional_sqlite_extension_api(completed, monkeypatch):
    core, task, response = completed
    connect = sqlite3.connect
    opened = []

    class NoExtensionApi(sqlite3.Connection):
        def __getattribute__(self, name):
            if name == "enable_load_extension":
                raise AttributeError(name)
            return super().__getattribute__(name)

    def without_extensions(*args, **kwargs):
        connection = connect(*args, **kwargs, factory=NoExtensionApi)
        opened.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", without_extensions)
    receipt = find_core_receipt(core, task)
    assert receipt is not None and receipt.response_text == response.response_text
    assert receipt.request_id == task.request_id and receipt.query_sha256 == task.input_sha256
    assert len(opened) == 3
    for connection in opened:
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


def test_claim_without_flushed_final_is_unknown(tmp_path):
    core = _isolated_core(tmp_path / "runtime")
    task = task_at_now()
    assert core.memory_service.claim_runtime_request(
        request_id=task.request_id, session_id=task.core_session_id,
        claimed_at=datetime.now(UTC).isoformat(),
    )
    assert find_core_receipt(core, task) is None


def test_turn_commit_without_flushed_events_is_unknown_never_last_turn(completed):
    core, task, _ = completed
    with sqlite3.connect(events_path(core)) as db:
        db.execute("DELETE FROM internal_events")
    assert find_core_receipt(core, task) is None


@pytest.mark.parametrize("name", ["input_received", "governance_checked", "response_synthesized",
                                 "memory_recorded"])
def test_missing_one_required_event_is_unknown(completed, name):
    core, task, _ = completed
    with sqlite3.connect(events_path(core)) as db:
        db.execute("DELETE FROM internal_events WHERE event_name=?", (name,))
    assert find_core_receipt(core, task) is None
    assert_refused(core, replace(task, phase="completed", receipt_sha256="1" * 64))


@pytest.mark.parametrize("key,value", [
    ("request_id", "wrong-request"), ("correlation_id", "wrong-correlation"),
    ("session_id", "session://other"), ("mission_id", "mission://unexpected"),
    ("source_service", "external-provider"), ("operation_id", "operation-unexpected"),
])
def test_wrong_event_scope_is_refused_not_hidden_by_query(completed, key, value):
    core, task, _ = completed
    update_event(core, "memory_recorded", envelope={key: value})
    assert_refused(core, task)


@pytest.mark.parametrize("key,value", [
    ("canonical_user_ref", "user://other"), ("operator_identity_ref", "operator://other"),
    ("surface_id", "surface://other"), ("surface_session_id", "session://other"),
    ("surface_capability_scope", ["execute"]), ("max_autonomy_level", "full_auto"),
    ("requested_autonomy_level", "full_auto"), ("content", "another input"),
])
def test_received_actor_input_and_surface_are_exact(completed, key, value):
    core, task, _ = completed
    update_event(core, "input_received", payload=lambda data: data.__setitem__(key, value))
    assert_refused(core, task)


@pytest.mark.parametrize("key,value", [
    ("canonical_user_ref", "user://other"), ("operator_identity_ref", "operator://other"),
    ("content", "another input"), ("surface_capability_scope", ["execute"]),
])
def test_incomplete_bundle_does_not_hide_inconsistent_input(completed, key, value):
    core, task, _ = completed
    update_event(core, "input_received", payload=lambda data: data.__setitem__(key, value))
    with sqlite3.connect(events_path(core)) as db:
        db.execute("DELETE FROM internal_events WHERE event_name='memory_recorded'")
    assert_refused(core, task)


def test_conditional_native_final_needs_decision_and_helper_default_is_unchanged(
    tmp_path, monkeypatch,
):
    core = _isolated_core(tmp_path / "runtime")
    task = task_at_now()
    assess = core.governance_service.assess_request

    def conditional(*args, **kwargs):
        assessment = assess(*args, **kwargs)
        return replace(assessment, governance_decision=replace(
            assessment.governance_decision, decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
            conditions=["Human review is still required."],
        ))

    monkeypatch.setattr(core.governance_service, "assess_request", conditional)
    response = core.handle_input(contract_for(task))
    assert response.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert response.operation_dispatch is None and response.adapter_grant is None
    receipt = find_core_receipt(core, task)
    assert receipt is not None and receipt.outcome == "needs_decision"
    assert receipt.response_text == response.response_text
    with ExitStack() as stack:
        def check():
            return None

        memory = module._open(core.memory_service.repository.database_path, stack, check,
                              "interaction_turns")
        events = module._open(events_path(core), stack, check, "internal_events")
        kwargs = {"session_id": task.core_session_id, "request_id": task.request_id,
                  "principal_ref": f"user://{task.actor_ref}", "check": check}
        with pytest.raises(ValueError, match="^conversation_export_refused$"):
            module._read(memory, events, **kwargs)
        with pytest.raises(ValueError, match="^conversation_export_refused$"):
            module._read(memory, events, **kwargs, allow_conditional=1)
        assert module._read(memory, events, **kwargs, allow_conditional=True)[4] == (
            "allow_with_conditions"
        )


def test_duplicate_required_event_is_refused(completed):
    core, task, _ = completed
    with sqlite3.connect(events_path(core)) as db:
        db.execute(
            "INSERT INTO internal_events SELECT ?,event_name,timestamp,source_service,payload,"
            "correlation_id,request_id,session_id,mission_id,operation_id,tags "
            "FROM internal_events WHERE event_name='input_received'", ("duplicate-" + uuid4().hex,),
        )
    assert_refused(core, task)


def test_wrong_readback_hash_is_refused(completed):
    core, task, _ = completed
    update_event(core, "memory_recorded", payload=lambda data: data["conversation_readback"].update(
        response_text_sha256="0" * 64,
    ))
    assert_refused(core, task)


def test_record_id_cannot_be_reused_by_another_request(completed):
    core, task, _ = completed
    with sqlite3.connect(events_path(core)) as db:
        db.execute(
            "INSERT INTO internal_events SELECT ?,event_name,timestamp,source_service,payload,"
            "'other-request','other-request',session_id,mission_id,operation_id,tags "
            "FROM internal_events WHERE event_name='memory_recorded'",
            ("reuse-" + uuid4().hex,),
        )
    assert_refused(core, task)


def test_event_bundle_without_native_claim_is_inconsistent(completed):
    core, task, _ = completed
    with sqlite3.connect(core.memory_service.repository.database_path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM runtime_request_claims WHERE request_id=?", (task.request_id,))
        # Deliberate offline corruption of this disposable test database only.
        db.execute("DROP TRIGGER runtime_request_claims_no_delete")
        db.execute("DELETE FROM runtime_request_claims WHERE request_id=?", (task.request_id,))
    assert_refused(core, task)


@pytest.mark.parametrize("field", ["session_id", "claimed_at"])
def test_claim_scope_and_original_execution_window_are_exact(completed, field):
    core, task, _ = completed
    value = "session://other" if field == "session_id" else (
        task.deadline + timedelta(seconds=1)
    ).isoformat()
    with sqlite3.connect(core.memory_service.repository.database_path) as db:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute(f"UPDATE runtime_request_claims SET {field}=? WHERE request_id=?",
                       (value, task.request_id))
        # The production append-only trigger is never relaxed by the verifier.
        db.execute("DROP TRIGGER runtime_request_claims_no_update")
        db.execute(f"UPDATE runtime_request_claims SET {field}=? WHERE request_id=?",
                   (value, task.request_id))
    assert_refused(core, task)


def test_late_final_event_is_not_made_valid_by_later_recovery(completed):
    core, task, _ = completed
    update_event(core, "memory_recorded", envelope={
        "timestamp": (task.deadline + timedelta(seconds=1)).isoformat(),
    })
    assert_refused(core, task)


@pytest.mark.parametrize("marker", ["operation_dispatched", "adapter_grant_issued",
                                   "specialists_dispatched", "model_tool_loop_started"])
def test_active_effect_grant_specialist_or_model_event_is_refused(completed, marker):
    core, task, _ = completed
    with sqlite3.connect(events_path(core)) as db:
        db.execute(
            "INSERT INTO internal_events SELECT ?,?,timestamp,source_service,'{}',correlation_id,"
            "request_id,session_id,mission_id,operation_id,tags FROM internal_events "
            "WHERE event_name='input_received'", ("active-" + uuid4().hex, marker),
        )
    assert_refused(core, task)


@pytest.mark.parametrize("key,value", [("model_tool_loop_status", "completed"),
                                      ("generative_status", "accepted"),
                                      ("extractive_status", "accepted")])
def test_non_native_synthesis_is_refused(completed, key, value):
    core, task, _ = completed
    update_event(core, "response_synthesized", payload=lambda data: data.__setitem__(key, value))
    assert_refused(core, task)


def test_lookup_never_calls_core_or_writes_stores(completed, monkeypatch):
    core, task, _ = completed
    paths = (core.memory_service.repository.database_path, events_path(core))
    before = [
        (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).digest()) for path in paths
    ]
    monkeypatch.setattr(core, "handle_input", lambda *_args: pytest.fail("Core replayed"))
    assert find_core_receipt(core, task) is not None
    after = [
        (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).digest()) for path in paths
    ]
    assert after == before


def test_private_os_exception_is_not_chained_or_displayed(completed, monkeypatch):
    core, task, _ = completed

    def fail(*_args):
        raise PermissionError("PRIVATE_PATH/private-secret")

    monkeypatch.setattr(module, "_file_state", fail)
    assert_refused(core, task)
