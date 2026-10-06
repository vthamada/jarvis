"""Real Linux first-effect fences against an independent SQLite writer process.

The failure-injector seam synchronizes the claim/rename window; it does not
replace filesystem I/O, Governance claims, Memory transactions or process locks.
This is process/SQLite evidence, not power-loss or storage-controller evidence.
"""

import multiprocessing
import sqlite3
import sys
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_operations import PhysicalOperationsConsole
from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="MB219 process fence requires real Linux physical backend"
)
MISSION = "mission://mb219/process-fence"
WORK = "work-item://mb219/process-fence"
SESSION = "session://mb219/process-fence"
DEADLINE = 10


def _pause_writer(database_path, connection):
    """Synthetic independent canonical writer; no inherited database connection."""
    database = sqlite3.connect(database_path, timeout=0)
    sql = "UPDATE mission_states SET mission_status = ? WHERE mission_id = ?"
    arguments = (MissionStatus.PAUSED.value, MISSION)
    try:
        connection.send("ready")
        if not connection.poll(DEADLINE):
            raise RuntimeError("writer command deadline")
        command = connection.recv()
        if command == "probe_fence":
            try:
                database.execute(sql, arguments)
                database.commit()
            except sqlite3.OperationalError as error:
                if error.sqlite_errorcode not in {sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED}:
                    raise
                database.rollback()
                connection.send("fenced")
            else:
                connection.send("unexpected_unfenced_write")
                return
            if not connection.poll(DEADLINE) or connection.recv() != "retry":
                raise RuntimeError("writer retry deadline")
            database.execute(f"PRAGMA busy_timeout = {DEADLINE * 1000}")
            database.set_trace_callback(
                lambda statement: connection.send("retry_attempted")
                if statement.startswith("UPDATE")
                else None
            )
        elif command != "pause_now":
            raise RuntimeError("unexpected writer command")
        database.execute(sql, arguments)
        database.commit()
        connection.send("paused")
    except Exception as error:
        connection.send(("writer_failed", type(error).__name__))
    finally:
        database.close()
        connection.close()


def _receive(connection, expected):
    assert connection.poll(DEADLINE), f"writer did not report {expected} before deadline"
    assert connection.recv() == expected


def _start_writer(console):
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    writer = context.Process(
        target=_pause_writer,
        args=(str(console.orchestrator.memory_service.repository.database_path), child),
        daemon=True,
    )
    writer.start()
    child.close()
    try:
        _receive(parent, "ready")
    except BaseException:
        _stop_writer(writer, parent)
        raise
    return writer, parent


def _stop_writer(writer, connection):
    connection.close()
    writer.join(timeout=DEADLINE)
    if writer.is_alive():
        writer.terminate()
        writer.join(timeout=2)
    if writer.is_alive():
        writer.kill()
        writer.join(timeout=2)
    assert not writer.is_alive(), "synthetic writer process survived bounded cleanup"


def _build(tmp_path):
    root = tmp_path / "root"
    root.mkdir(mode=0o700)
    (root / ".jarvis-transactions").mkdir(mode=0o700)
    orchestrator = build_physical_orchestrator(
        runtime_dir=tmp_path / "runtime", roots={"notes": root}, enable_execution=True
    )
    orchestrator.memory_service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId(MISSION),
            mission_goal="Disposable process-fence proof",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=datetime.now(UTC).isoformat(),
            objective_ref="objective://mb219/process-fence",
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
        "operator://mb219/process-fence",
        "user://mb219/process-fence",
        runtime_dir=tmp_path / "requests",
    ), root


def _prepare(console, version):
    return console.prepare(
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref=f"artifact://mb219/process-fence/v{version}",
        resource_ref="text:notes/fence.txt",
        desired_text=f"synthetic v{version}\n",
        session_id=SESSION,
        operation="create_text" if version == 1 else "replace_text",
        expected_current_sha256=None
        if version == 1
        else sha256(b"synthetic v1\n").hexdigest(),
        supersedes_artifact_ref=None
        if version == 1
        else "artifact://mb219/process-fence/v1",
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


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_first_claim_fences_other_process_pause_until_physical_effect_finishes(tmp_path, purpose):
    console, root = _build(tmp_path)
    writer = connection = None
    try:
        prepared, authorization, dispatch = _operation(console, purpose)
        writer, connection = _start_writer(console)
        boundary = "after_claim" if purpose == "apply" else "after_rollback_claim"
        observations = []

        def inspect_claim_window(observed):
            if observed != boundary:
                return
            context = console.orchestrator.governance_service.load_action_confirmation_context(
                authorization["confirmation_receipt_id"]
            )
            assert context.claim is not None
            if purpose == "apply":
                assert not (root / "fence.txt").exists()
            else:
                assert (root / "fence.txt").read_bytes() == b"synthetic v2\n"
            connection.send("probe_fence")
            _receive(connection, "fenced")
            assert console.orchestrator.memory_service.get_mission_state(
                MISSION
            ).mission_status is MissionStatus.ACTIVE
            connection.send("retry")
            _receive(connection, "retry_attempted")
            observations.append(context.claim)

        engine = console.orchestrator.operational_service._local_text_file_transaction_engine
        engine._failure_injector = inspect_claim_window
        assert dispatch(prepared["request_id"], **authorization)["phase"] == "completed"
        _receive(connection, "paused")
        writer.join(timeout=DEADLINE)
        assert writer.exitcode == 0
        assert len(observations) == 1
        assert console.orchestrator.memory_service.get_mission_state(
            MISSION
        ).mission_status is MissionStatus.PAUSED
        assert (root / "fence.txt").read_bytes() == b"synthetic v1\n"
        context = console.orchestrator.governance_service.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert context.claim == observations[0]
        lineage = console.orchestrator.memory_service.get_artifact_physical_lineage(
            MISSION, "artifact://mb219/process-fence/v1"
        )
        assert lineage.revision == (1 if purpose == "apply" else 3)
        assert lineage.active_artifact_ref == "artifact://mb219/process-fence/v1"
    finally:
        if writer is not None:
            _stop_writer(writer, connection)
        console.close()


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_other_process_pause_wins_before_dispatch_without_new_claim_or_effect(tmp_path, purpose):
    console, root = _build(tmp_path)
    writer = connection = None
    try:
        prepared, authorization, dispatch = _operation(console, purpose)
        lineage_before = console.orchestrator.memory_service.get_artifact_physical_lineage(
            MISSION, "artifact://mb219/process-fence/v1"
        )
        writer, connection = _start_writer(console)
        connection.send("pause_now")
        _receive(connection, "paused")
        writer.join(timeout=DEADLINE)
        assert writer.exitcode == 0
        with pytest.raises(ValueError, match="mission_not_active"):
            dispatch(prepared["request_id"], **authorization)
        context = console.orchestrator.governance_service.load_action_confirmation_context(
            authorization["confirmation_receipt_id"]
        )
        assert context.claim is None
        assert console.orchestrator.memory_service.get_artifact_physical_lineage(
            MISSION, "artifact://mb219/process-fence/v1"
        ) == lineage_before
        if purpose == "apply":
            assert not (root / "fence.txt").exists()
        else:
            assert (root / "fence.txt").read_bytes() == b"synthetic v2\n"
    finally:
        if writer is not None:
            _stop_writer(writer, connection)
        console.close()
