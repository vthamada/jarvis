"""Linux-only physical MB218 proof through real composed services, never mocks."""

import json
import os
import stat
import sys
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_operations import PhysicalOperationsConsole, _RequestStore
from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="real Linux physical backend required"
)
MISSION = "mission://physical-console/integration"
WORK = "work-item://physical-console/integration"
OPERATOR = "operator://physical-console/integration"
USER = "user://physical-console/integration"
SESSION = "session://physical-console/integration"


def build(tmp_path, *, seed=False):
    root = tmp_path / "root"
    root.mkdir(exist_ok=True)
    (root / ".jarvis-transactions").mkdir(mode=0o700, exist_ok=True)
    orchestrator = build_physical_orchestrator(
        runtime_dir=tmp_path / "runtime",
        roots={"notes": root},
        enable_execution=True,
    )
    if seed:
        orchestrator.memory_service.repository.upsert_mission_state(
            MissionStateContract(
                mission_id=MissionId(MISSION),
                mission_goal="Physical console restart integration",
                mission_status=MissionStatus.ACTIVE,
                checkpoints=[],
                updated_at=datetime.now(UTC).isoformat(),
                objective_ref="objective://physical-console/integration",
                objective_status="active",
                active_work_items=[WORK],
                work_item_refs=[WORK],
                work_items=[
                    WorkItemStateContract(
                        work_item_ref=WORK,
                        work_item_status="active",
                        mission_id=MissionId(MISSION),
                        priority_level="p1",
                        blocking_state="ready",
                    )
                ],
            )
        )
    return PhysicalOperationsConsole(
        orchestrator,
        OPERATOR,
        USER,
        runtime_dir=tmp_path / "requests",
    ), root


def prepare(console, *, version=1):
    return console.prepare(
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref=f"artifact://console/v{version}",
        resource_ref="text:notes/note.txt",
        desired_text=f"private v{version}\n",
        session_id=SESSION,
        operation="create_text" if version == 1 else "replace_text",
        expected_current_sha256=None
        if version == 1
        else sha256(f"private v{version - 1}\n".encode()).hexdigest(),
        supersedes_artifact_ref=None if version == 1 else f"artifact://console/v{version - 1}",
    )


def exact(record):
    return {
        "challenge_id": record["challenge_id"],
        "action_fingerprint": record["action_fingerprint"],
    }


def authorize(console, prepared):
    confirmation = console.confirm(prepared["request_id"], **exact(prepared))
    return {**exact(prepared), "confirmation_receipt_id": confirmation["confirmation_receipt_id"]}


def test_durable_prepare_restart_confirm_execute_replace_and_independent_rollback(tmp_path):
    console, root = build(tmp_path, seed=True)
    prepared = prepare(console)
    assert not (root / "note.txt").exists()
    request_file = tmp_path / "requests" / f"{prepared['request_id']}.json"
    persisted = json.loads(request_file.read_text())
    assert stat.S_IMODE(request_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(request_file.parent.stat().st_mode) == 0o700
    assert persisted["operator_input"]["desired_text"] == "private v1\n"
    assert "unified_diff" not in str(persisted) and "preview" not in str(persisted)
    console.close()
    console, _ = build(tmp_path)
    assert console.inspect(prepared["request_id"])["phase"] == "prepared"
    authorization = authorize(console, prepared)
    console.close()
    console, _ = build(tmp_path)
    assert console.status(prepared["request_id"])["phase"] == "confirmed"
    assert console.execute(prepared["request_id"], **authorization)["phase"] == "completed"
    assert (root / "note.txt").read_text() == "private v1\n"
    replacement = prepare(console, version=2)
    assert (
        console.execute(replacement["request_id"], **authorize(console, replacement))["phase"]
        == "completed"
    )
    rollback = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
    assert (root / "note.txt").read_text() == "private v2\n"
    with pytest.raises(ValueError, match="wrong_confirmation_command"):
        console.confirm(rollback["request_id"], **exact(rollback))
    rollback_confirmation = console.confirm_rollback(rollback["request_id"], **exact(rollback))
    with pytest.raises(ValueError, match="receipt_mismatch"):
        console.rollback(
            rollback["request_id"],
            **exact(rollback),
            confirmation_receipt_id=authorization["confirmation_receipt_id"],
        )
    console.close()
    console, _ = build(tmp_path)
    result = console.rollback(
        rollback["request_id"],
        **exact(rollback),
        confirmation_receipt_id=rollback_confirmation["confirmation_receipt_id"],
    )
    assert result["phase"] == "completed"
    assert (root / "note.txt").read_text() == "private v1\n"
    lineage = console.orchestrator.memory_service.get_artifact_physical_lineage(
        MISSION, "artifact://console/v1"
    )
    assert lineage.active_artifact_ref == "artifact://console/v1" and lineage.revision == 3
    console.close()


def test_recovery_after_effect_and_before_canonical_commit_survives_restart(tmp_path):
    console, root = build(tmp_path, seed=True)
    prepared = prepare(console)
    authorization = authorize(console, prepared)

    def crash(boundary):
        if boundary == "before_apply_canonical_commit":
            raise RuntimeError("injected crash")

    console.orchestrator.artifact_physical_sagas._failure_injector = crash
    with pytest.raises(RuntimeError, match="injected crash"):
        console.execute(prepared["request_id"], **authorization)
    assert (root / "note.txt").read_text() == "private v1\n"
    assert console.status(prepared["request_id"])["phase"] == "effect_dispatched"
    console.close()
    console, _ = build(tmp_path)
    assert console.recover(prepared["request_id"], **authorization)["phase"] == "completed"
    assert (
        console.orchestrator.memory_service.get_artifact_physical_version("artifact://console/v1")
        is not None
    )
    console.close()


def test_persisted_input_tamper_permissions_and_hardlinks_fail_closed(tmp_path):
    console, root = build(tmp_path, seed=True)
    prepared = prepare(console)
    request_file = tmp_path / "requests" / f"{prepared['request_id']}.json"
    original = request_file.read_text()
    record = json.loads(original)
    record["operator_input"]["desired_text"] = "tampered"
    request_file.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="input_changed"):
        console.status(prepared["request_id"])
    request_file.write_text(original)
    request_file.chmod(0o644)
    with pytest.raises(ValueError, match="store_permissions"):
        console.status(prepared["request_id"])
    request_file.chmod(0o600)
    os.link(request_file, tmp_path / "hardlink.json")
    with pytest.raises(ValueError, match="store_permissions"):
        console.status(prepared["request_id"])
    assert not (root / "note.txt").exists()
    console.close()


def test_fresh_human_edit_after_confirmation_prevents_execute(tmp_path):
    console, root = build(tmp_path, seed=True)
    first = prepare(console)
    console.execute(first["request_id"], **authorize(console, first))
    second = prepare(console, version=2)
    authorization = authorize(console, second)
    (root / "note.txt").write_text("human content\n")
    with pytest.raises(ValueError):
        console.execute(second["request_id"], **authorization)
    assert (root / "note.txt").read_text() == "human content\n"
    assert console.status(second["request_id"])["phase"] == "confirmed"
    console.close()


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_crash_before_journal_then_paused_mission_cannot_start_effect(tmp_path, purpose):
    console, root = build(tmp_path, seed=True)
    prepared = prepare(console)
    if purpose == "rollback":
        console.execute(prepared["request_id"], **authorize(console, prepared))
        replacement = prepare(console, version=2)
        console.execute(replacement["request_id"], **authorize(console, replacement))
        prepared = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
        confirmation = console.confirm_rollback(prepared["request_id"], **exact(prepared))
        authorization = {
            **exact(prepared),
            "confirmation_receipt_id": confirmation["confirmation_receipt_id"],
        }
        dispatch = console.rollback
    else:
        authorization = authorize(console, prepared)
        dispatch = console.execute

    def crash(boundary):
        if boundary == f"after_{purpose}_effect_dispatched":
            raise RuntimeError("injected before journal")

    console.orchestrator.artifact_physical_sagas._failure_injector = crash
    with pytest.raises(RuntimeError, match="injected before journal"):
        dispatch(prepared["request_id"], **authorization)
    mission = console.orchestrator.memory_service.get_mission_state(MISSION)
    mission.mission_status = MissionStatus.PAUSED
    console.orchestrator.memory_service.repository.upsert_mission_state(mission)
    console.close()
    console, _ = build(tmp_path)
    with pytest.raises(ValueError, match="mission_not_active"):
        console.recover(prepared["request_id"], **authorization)
    if purpose == "rollback":
        assert (root / "note.txt").read_text() == "private v2\n"
    else:
        assert not (root / "note.txt").exists()
    console.close()


def test_rollback_crash_before_reservation_retries_original_request_after_restart(
    tmp_path, monkeypatch
):
    console, root = build(tmp_path, seed=True)
    first = prepare(console)
    console.execute(first["request_id"], **authorize(console, first))
    replacement = prepare(console, version=2)
    console.execute(replacement["request_id"], **authorize(console, replacement))
    rollback = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
    confirmation = console.confirm_rollback(rollback["request_id"], **exact(rollback))
    authorization = {
        **exact(rollback),
        "confirmation_receipt_id": confirmation["confirmation_receipt_id"],
    }

    def crash(boundary):
        if boundary == "after_rollback_effect_dispatched":
            raise RuntimeError("injected before rollback reservation")

    console.orchestrator.artifact_physical_sagas._failure_injector = crash
    with pytest.raises(RuntimeError, match="before rollback reservation"):
        console.rollback(rollback["request_id"], **authorization)
    assert (root / "note.txt").read_text() == "private v2\n"
    before = console.orchestrator.governance_service.load_action_confirmation_context(
        authorization["confirmation_receipt_id"]
    )
    assert before.claim is None
    console.close()
    console, _ = build(tmp_path)

    def never_confirm(*args, **kwargs):
        pytest.fail("recovery must reuse the original confirmation")

    monkeypatch.setattr(
        console.orchestrator.governance_service, "confirm_action_challenge", never_confirm
    )
    try:
        assert console.recover(rollback["request_id"], **authorization)["phase"] == "completed"
        assert (root / "note.txt").read_text() == "private v1\n"
        after = console.orchestrator.governance_service.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert after.receipt == before.receipt and after.claim is not None
        assert console.recover(rollback["request_id"], **authorization)["phase"] == "completed"
        assert console.orchestrator.governance_service.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        ) == after
    finally:
        console.close()


@pytest.mark.parametrize(
    "field,value",
    [
        ("mutation_operation_id", "operation://foreign"),
        ("mutation_receipt_fingerprint", "0" * 64),
        ("resource_ref", "text:notes/foreign.txt"),
    ],
)
def test_source_mutation_journal_is_not_missing_rollback_proof_for_foreign_plan(
    tmp_path, field, value
):
    """Real source journal/ledger; deliberately malformed private kernel input."""
    console, root = build(tmp_path, seed=True)
    try:
        first = prepare(console)
        console.execute(first["request_id"], **authorize(console, first))
        replacement = prepare(console, version=2)
        console.execute(replacement["request_id"], **authorize(console, replacement))
        rollback = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
        confirmation = console.confirm_rollback(rollback["request_id"], **exact(rollback))
        _, plan, _ = console._load(rollback["request_id"])
        engine = console.orchestrator.operational_service._local_text_file_transaction_engine
        with pytest.raises(ValueError, match="canonical_physical_plan_binding_mismatch"):
            engine._recover_rollback(
                root_alias=plan.root_alias,
                operation_id=plan.mutation_operation_id,
                plan=replace(plan, **{field: value}),
                receipt_recorder=None,
                canonical_commit=None,
            )
        assert (root / "note.txt").read_text() == "private v2\n"
        assert console.orchestrator.governance_service.load_action_confirmation_context(
            confirmation["confirmation_receipt_id"]
        ).claim is None
        assert console._saga(plan.saga_id) is None
    finally:
        console.close()


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_confirmation_cache_failure_recovers_exact_receipt_after_durable_restart(
    tmp_path, monkeypatch, purpose
):
    console, root = build(tmp_path, seed=True)
    prepared = prepare(console)
    if purpose == "rollback":
        console.execute(prepared["request_id"], **authorize(console, prepared))
        replacement = prepare(console, version=2)
        console.execute(replacement["request_id"], **authorize(console, replacement))
        prepared = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
        confirmation_method = console.confirm_rollback
    else:
        confirmation_method = console.confirm

    def disk_full(*args, **kwargs):
        raise OSError("injected confirmation cache failure")

    with monkeypatch.context() as context:
        context.setattr(console._store, "save", disk_full)
        with pytest.raises(OSError, match="cache failure"):
            confirmation_method(prepared["request_id"], **exact(prepared))
    original = (
        console.orchestrator.governance_service.load_action_confirmation_context_for_challenge(
            prepared["challenge_id"]
        )
    )
    assert original is not None and original.claim is None
    console.close()
    console, _ = build(tmp_path)
    assert console._store.load(prepared["request_id"])["confirmation_receipt_id"] is None

    def never_issue(*args, **kwargs):
        pytest.fail("restart reconciliation must not confirm again")

    monkeypatch.setattr(
        console.orchestrator.governance_service, "confirm_action_challenge", never_issue
    )
    healed = console.status(prepared["request_id"])
    assert healed["phase"] == "confirmed"
    assert healed["confirmation_receipt_id"] == original.receipt.receipt_id
    console.close()
    console, _ = build(tmp_path)
    assert console.status(prepared["request_id"])["confirmation_receipt_id"] == (
        original.receipt.receipt_id
    )
    authorization = {**exact(prepared), "confirmation_receipt_id": original.receipt.receipt_id}
    if purpose == "rollback":
        assert (root / "note.txt").read_text() == "private v2\n"
        dispatch = console.rollback
    else:
        assert not (root / "note.txt").exists()
        dispatch = console.execute
    assert dispatch(prepared["request_id"], **authorization)["phase"] == "completed"
    assert (root / "note.txt").read_text() == "private v1\n"
    console.close()


@pytest.mark.parametrize("replace_record", [False, True])
@pytest.mark.parametrize("boundary", ["file_fsync", "publication"])
def test_request_store_staging_failure_leaves_no_partial_record_or_sensitive_temporary(
    tmp_path, monkeypatch, replace_record, boundary
):
    """Real Linux store I/O with an explicit failure boundary, no target mutation."""
    request_id = "a" * 32
    path = tmp_path / "private-requests"
    store = _RequestStore(path)
    before = {"request_id": request_id, "operator_input": {"desired_text": "old private"}}
    after = {"request_id": request_id, "operator_input": {"desired_text": "new private"}}
    if replace_record:
        store.save(request_id, before)

    def fail(*args, **kwargs):
        raise OSError("injected staged storage failure")

    try:
        with monkeypatch.context() as context:
            if boundary == "file_fsync":
                context.setattr(os, "fsync", fail)
            else:
                context.setattr(os, "replace" if replace_record else "link", fail)
            with pytest.raises(OSError, match="staged storage failure"):
                store.save(request_id, after, replace=replace_record)
        assert not list(path.glob(".*.tmp"))
        if replace_record:
            assert store.load(request_id) == before
        else:
            assert list(path.iterdir()) == []
    finally:
        store.close()


def test_request_store_create_never_overwrites_existing_request_and_cleans_stage(tmp_path):
    path = tmp_path / "private-requests"
    store = _RequestStore(path)
    request_id = "b" * 32
    first = {"request_id": request_id, "operator_input": {"desired_text": "original"}}
    second = {"request_id": request_id, "operator_input": {"desired_text": "replacement"}}
    try:
        store.save(request_id, first)
        with pytest.raises(FileExistsError):
            store.save(request_id, second)
        assert store.load(request_id) == first
        assert [file.name for file in path.iterdir()] == [f"{request_id}.json"]
        assert (path / f"{request_id}.json").stat().st_nlink == 1
    finally:
        store.close()
