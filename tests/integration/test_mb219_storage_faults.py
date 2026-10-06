"""Linux storage fault campaign with real transactions, bytes and durable reload.

ENOSPC/EIO are injected once at a concrete fsync/SQLite commit call. This is
not a genuinely full filesystem, SQLite VFS fault injection or power-loss proof.
SQLite fsync runs in C: journal durability is tested at its commit boundary.
"""

import errno
import os
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_operations import PhysicalOperationsConsole
from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="MB219 storage campaign requires real Linux physical backend"
)
MISSION = "mission://mb219/storage-fault"
WORK = "work-item://mb219/storage-fault"
SESSION = "session://mb219/storage-fault"
LINEAGE = "artifact://mb219/storage-fault/v1"


class _CommitFailureConnection:
    """Delegate actual SQL, fail one selected commit before it becomes durable."""

    def __init__(self, connection, predicate, failures):
        self.connection = connection
        self.predicate = predicate
        self.failures = failures
        self.selected = False

    def __getattr__(self, name):
        return getattr(self.connection, name)

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, *arguments):
        return self.connection.__exit__(*arguments)

    def execute(self, sql, parameters=()):
        cursor = self.connection.execute(sql, parameters)
        self.selected |= self.predicate(" ".join(sql.split()), parameters)
        return cursor

    def commit(self):
        if self.selected and not self.failures:
            self.failures.append("commit")
            raise OSError(errno.EIO, "synthetic SQLite durability failure")
        return self.connection.commit()


def _build(tmp_path, *, seed=False):
    root = tmp_path / "root"
    root.mkdir(mode=0o700, exist_ok=True)
    (root / ".jarvis-transactions").mkdir(mode=0o700, exist_ok=True)
    orchestrator = build_physical_orchestrator(
        runtime_dir=tmp_path / "runtime", roots={"notes": root}, enable_execution=True
    )
    if seed:
        orchestrator.memory_service.repository.upsert_mission_state(
            MissionStateContract(
                mission_id=MissionId(MISSION),
                mission_goal="Disposable storage fault campaign",
                mission_status=MissionStatus.ACTIVE,
                checkpoints=[],
                updated_at=datetime.now(UTC).isoformat(),
                objective_ref="objective://mb219/storage-fault",
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
        "operator://mb219/storage-fault",
        "user://mb219/storage-fault",
        runtime_dir=tmp_path / "requests",
    ), root


def _prepare(console, version):
    return console.prepare(
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref=f"artifact://mb219/storage-fault/v{version}",
        resource_ref="text:notes/fault.txt",
        desired_text=f"synthetic v{version}\n",
        session_id=SESSION,
        operation="create_text" if version == 1 else "replace_text",
        expected_current_sha256=None
        if version == 1
        else sha256(b"synthetic v1\n").hexdigest(),
        supersedes_artifact_ref=None if version == 1 else LINEAGE,
    )


def _confirm(console, prepared, *, rollback=False):
    exact = {
        "challenge_id": prepared["challenge_id"],
        "action_fingerprint": prepared["action_fingerprint"],
    }
    method = console.confirm_rollback if rollback else console.confirm
    receipt = method(prepared["request_id"], **exact)
    return {**exact, "confirmation_receipt_id": receipt["confirmation_receipt_id"]}


def _operation(console, purpose):
    first = _prepare(console, 1)
    if purpose == "apply":
        return first, _confirm(console, first), console.execute
    console.execute(first["request_id"], **_confirm(console, first))
    replacement = _prepare(console, 2)
    console.execute(replacement["request_id"], **_confirm(console, replacement))
    rollback = console.prepare_rollback(replacement["request_id"], session_id=SESSION)
    return rollback, _confirm(console, rollback, rollback=True), console.rollback


def _inject_failure(patch, console, root, purpose, boundary, failures):
    engine = console.orchestrator.operational_service._local_text_file_transaction_engine
    if boundary == "preclaim" and purpose == "apply":
        fsync = os.fsync

        def fail_desired_fsync(descriptor):
            location = os.readlink(f"/proc/self/fd/{descriptor}")
            if location.startswith(str(root / ".jarvis-transactions")) and location.endswith(
                ".desired"
            ) and not failures:
                failures.append("fsync")
                raise OSError(errno.ENOSPC, "synthetic desired staging fsync failure")
            return fsync(descriptor)

        patch.setattr(os, "fsync", fail_desired_fsync)
    elif boundary == "preclaim":
        journal_connection = engine._journal_connection

        @contextmanager
        def failed_journal(alias):
            with journal_connection(alias) as connection:
                yield _CommitFailureConnection(
                    connection,
                    lambda sql, parameters: sql.startswith(
                        "INSERT INTO local_text_transaction_events"
                    ) and parameters[2] == "rollback_reserved",
                    failures,
                )

        patch.setattr(engine, "_journal_connection", failed_journal)
    else:
        if boundary == "receipt":
            repository = console.orchestrator.governance_service.action_confirmation_repository
            method = "_new_connection"
            table = (
                "local_text_mutation_receipts"
                if purpose == "apply"
                else "local_text_rollback_receipts"
            )
        else:
            repository = console.orchestrator.memory_service.repository
            method = "_connect"
            table = "artifact_physical_canonical_commits"
        connect = getattr(repository, method)
        patch.setattr(
            repository,
            method,
            lambda: _CommitFailureConnection(
                connect(), lambda sql, _parameters: sql.startswith(f"INSERT INTO {table} "),
                failures,
            ),
        )


def _forbid_new_authority(*_arguments, **_keywords):
    pytest.fail("historical recovery must not issue a new confirmation or claim")


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
@pytest.mark.parametrize("boundary", ["preclaim", "receipt", "canonical"])
def test_storage_fault_then_durable_reload_preserves_authority_and_recovery(
    tmp_path, monkeypatch, purpose, boundary
):
    console, root = _build(tmp_path, seed=True)
    try:
        prepared, authorization, dispatch = _operation(console, purpose)
        _, plan, _ = console._load(prepared["request_id"])
        memory = console.orchestrator.memory_service
        lineage_before = memory.get_artifact_physical_lineage(MISSION, LINEAGE)
        failures = []
        expected = (
            (ValueError, f"local_text_{'mutation' if purpose == 'apply' else 'rollback'}"
             "_receipt_recording_failed")
            if boundary == "receipt"
            else (OSError, "synthetic")
        )
        with monkeypatch.context() as patch:
            _inject_failure(patch, console, root, purpose, boundary, failures)
            with pytest.raises(expected[0], match=expected[1]):
                dispatch(prepared["request_id"], **authorization)
        assert len(failures) == 1, "the selected concrete storage call was not exercised"
        governance = console.orchestrator.governance_service
        before = governance.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert (before.claim is None) is (boundary == "preclaim")
        assert memory.get_artifact_physical_lineage(MISSION, LINEAGE) == lineage_before
        assert memory.get_artifact_physical_canonical_commit_receipt(plan.saga_id) is None
        assert memory.get_artifact_physical_outbox_for_saga(plan.saga_id) is None
        if boundary == "preclaim":
            if purpose == "apply":
                assert not (root / "fault.txt").exists()
                assert not list((root / ".jarvis-transactions").glob("*.desired"))
            else:
                assert (root / "fault.txt").read_bytes() == b"synthetic v2\n"
        else:
            assert (root / "fault.txt").read_bytes() == b"synthetic v1\n"
    finally:
        console.close()

    # Rebuild actual services from the same on-disk stores; no in-memory snapshot.
    console, root = _build(tmp_path)
    try:
        governance = console.orchestrator.governance_service
        memory = console.orchestrator.memory_service
        reloaded = governance.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert reloaded.receipt == before.receipt and reloaded.claim == before.claim
        assert memory.get_artifact_physical_lineage(MISSION, LINEAGE) == lineage_before
        assert memory.get_artifact_physical_canonical_commit_receipt(plan.saga_id) is None
        engine = console.orchestrator.operational_service._local_text_file_transaction_engine
        events = engine._load_events(
            plan.root_alias,
            plan.physical_operation_id if purpose == "apply" else plan.mutation_operation_id,
        )
        if boundary == "preclaim":
            assert events[-1].phase == ("reserved" if purpose == "apply" else "cleaned")
        else:
            physical_receipt = (
                engine._receipt_from_applied(engine._find_event(events, "applied"))
                if purpose == "apply"
                else engine._rollback_receipt_from_event(events[-1])
            )
            verify = (
                governance.verify_local_text_mutation_receipt_exact
                if purpose == "apply"
                else governance.verify_local_text_rollback_receipt_exact
            )
            assert verify(physical_receipt) is (boundary == "canonical")
        mission = memory.get_mission_state(MISSION)
        mission.mission_status = MissionStatus.PAUSED
        memory.repository.upsert_mission_state(mission)
        for method in (
            "confirm_action_challenge",
            "claim_adapter_execution_grant_exact",
            "claim_local_text_file_rollback_grant_exact",
        ):
            monkeypatch.setattr(governance, method, _forbid_new_authority)
        if boundary == "preclaim":
            with pytest.raises(
                ValueError, match="mission_not_active|physical_(?:first_)?effect_not_authorized"
            ):
                console.recover(prepared["request_id"], **authorization)
            if purpose == "apply":
                assert not (root / "fault.txt").exists()
            else:
                assert (root / "fault.txt").read_bytes() == b"synthetic v2\n"
            assert memory.get_artifact_physical_lineage(MISSION, LINEAGE) == lineage_before
        else:
            assert console.recover(prepared["request_id"], **authorization)["phase"] == "completed"
            commit = memory.get_artifact_physical_canonical_commit_receipt(plan.saga_id)
            assert commit is not None
            assert console.recover(prepared["request_id"], **authorization)["phase"] == "completed"
            assert memory.get_artifact_physical_canonical_commit_receipt(plan.saga_id) == commit
            assert (root / "fault.txt").read_bytes() == b"synthetic v1\n"
            lineage = memory.get_artifact_physical_lineage(MISSION, LINEAGE)
            assert lineage.revision == (1 if purpose == "apply" else 3)
            assert lineage.active_artifact_ref == LINEAGE
        after = governance.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert after.receipt == before.receipt and after.claim == before.claim
    finally:
        console.close()
