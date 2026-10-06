"""Synthetic MB218 campaign across containers sharing one exclusive Linux volume.

The public entry point fixes /validation. Process death is not a power-loss proof.
The fixture contains only bounded synthetic authorization metadata, never input.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

STAGES = ("prepare", "confirm", "crash", "recover", "rollback", "verify")
VALIDATION_ROOT = Path("/validation")
CRASH_EXIT_CODE = 86
FIXTURE_LIMIT = 32_768
MISSION = "mission://persistent-validation/synthetic"
WORK = "work-item://persistent-validation/synthetic"
OPERATOR = "operator://persistent-validation/synthetic"
USER = "user://persistent-validation/synthetic"
SESSION = "session://persistent-validation/synthetic"
V1 = "Synthetic persistent validation version one.\n"
V2 = "Synthetic persistent validation version two.\n"
ARTIFACTS = ("artifact://persistent-validation/v1", "artifact://persistent-validation/v2")


def _fixture_bytes(fixture: dict) -> bytes:
    data = json.dumps(fixture, sort_keys=True, allow_nan=False).encode("utf-8")
    if len(data) > FIXTURE_LIMIT:
        raise ValueError("persistent_fixture_limit")
    return data


def _save_fixture(root: Path, fixture: dict) -> None:
    data = _fixture_bytes(fixture)
    temporary = root / "fixture.pending"
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, root / "fixture.json")
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _load_fixture(root: Path, stage: str) -> dict:
    fd = os.open(root / "fixture.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_nlink != 1
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > FIXTURE_LIMIT
        ):
            raise ValueError("persistent_fixture_invalid")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(FIXTURE_LIMIT + 1)
        if len(data) > FIXTURE_LIMIT:
            raise ValueError("persistent_fixture_limit")
        fixture = json.loads(data)
    finally:
        os.close(fd)
    expected = STAGES[STAGES.index(stage) - 1]
    if (
        not isinstance(fixture, dict)
        or fixture.get("schema_version") != "persistent-physical-scenario/v1"
        or fixture.get("stage") != expected
    ):
        raise ValueError("persistent_stage_order")
    return fixture


def _command(root: Path, action: str, **fields) -> list[str]:
    command = [
        "physical",
        "--runtime-dir",
        str(root / "runtime"),
        "--root",
        f"notes={root / 'notes'}",
        "--action",
        action,
        "--operator-identity-ref",
        OPERATOR,
        "--canonical-user-ref",
        USER,
        "--session-id",
        SESSION,
        "--format",
        "json",
        "--enable-execution",
    ]
    for name, value in fields.items():
        if value is None or value is False:
            continue
        command.append("--" + name.replace("_", "-"))
        if value is not True:
            command.append(str(value))
    return command


def _invoke(root: Path, action: str, *, refused: bool = False, **fields) -> dict:
    from apps.jarvis_console.cli import main

    output, error = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
        code = main(_command(root, action, **fields))
    if refused:
        assert code == 3 and not output.getvalue()
        envelope = json.loads(error.getvalue())
        assert envelope["error_code"] == "physical_operation_refused"
        assert str(root) not in error.getvalue() and V1.strip() not in error.getvalue()
        assert V2.strip() not in error.getvalue()
        return envelope
    assert code == 0 and not error.getvalue(), "synthetic CLI stage failed"
    envelope = json.loads(output.getvalue())
    assert envelope["status"] == "success"
    result = json.loads(envelope["outputs"][0])
    if not fields.get("show_diff"):
        assert "preview" not in result
        assert V1.strip() not in output.getvalue() and V2.strip() not in output.getvalue()
    assert str(root) not in output.getvalue()
    return result


def _exact(record: dict) -> dict:
    return {name: record[name] for name in ("challenge_id", "action_fingerprint")}


def _authorized(record: dict) -> dict:
    return {**_exact(record), "confirmation_receipt_id": record["confirmation_receipt_id"]}


def _console(root: Path):
    from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
    from apps.jarvis_console.physical_operations import PhysicalOperationsConsole

    core = build_physical_orchestrator(
        runtime_dir=root / "runtime",
        roots={"notes": root / "notes"},
        enable_execution=True,
    )
    return PhysicalOperationsConsole(
        core, OPERATOR, USER, runtime_dir=root / "runtime" / "physical-requests"
    )


def _prepare(root: Path) -> dict:
    from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
    from shared.contracts import MissionStateContract, WorkItemStateContract
    from shared.types import MissionId, MissionStatus

    for name in ("notes", "inputs"):
        (root / name).mkdir(mode=0o700)
    (root / "notes" / ".jarvis-transactions").mkdir(mode=0o700)
    core = build_physical_orchestrator(
        runtime_dir=root / "runtime",
        roots={"notes": root / "notes"},
        enable_execution=True,
    )
    core.memory_service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId(MISSION),
            mission_goal="Synthetic persistent CLI validation",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=datetime.now(UTC).isoformat(),
            objective_ref="objective://persistent-validation/synthetic",
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
    for version, text in ((1, V1), (2, V2)):
        path = root / "inputs" / f"v{version}.txt"
        with path.open("xb") as stream:
            stream.write(text.encode("utf-8"))
        path.chmod(0o600)
    result = _invoke(
        root,
        "prepare",
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref=ARTIFACTS[0],
        resource_ref="text:notes/note.txt",
        desired_file=root / "inputs" / "v1.txt",
    )
    assert result["root_alias"] == "notes" and result["relative_path"] == "note.txt"
    assert result["operation"] == "create_text" and result["risk_level"] == "moderate"
    assert result["expires_at"] and result["desired_sha256"] == sha256(V1.encode()).hexdigest()
    assert result["durable"] and result["confirmation_receipt_id"] is None
    inspection = _invoke(root, "inspect", request_id=result["request_id"], show_diff=True)
    assert inspection["preview_sensitive"] and "+" + V1.strip() in inspection["preview"]
    assert inspection["phase"] == "prepared"
    _invoke(
        root,
        "confirm",
        refused=True,
        request_id=result["request_id"],
        challenge_id="confirmation-challenge://synthetic/foreign",
        action_fingerprint=result["action_fingerprint"],
    )
    assert not (root / "notes" / "note.txt").exists()
    assert core.memory_service.get_artifact_physical_version(ARTIFACTS[0]) is None
    return {"schema_version": "persistent-physical-scenario/v1", "apply": result}


def _confirm(root: Path, fixture: dict) -> None:
    record = fixture["apply"]
    result = _invoke(root, "confirm", request_id=record["request_id"], **_exact(record))
    record["confirmation_receipt_id"] = result["confirmation_receipt_id"]
    _invoke(root, "confirm", refused=True, request_id=record["request_id"], **_exact(record))
    status = _invoke(root, "status", request_id=record["request_id"])
    assert (
        status["phase"] == "confirmed"
        and status["confirmation_receipt_id"] == record["confirmation_receipt_id"]
    )
    assert not (root / "notes" / "note.txt").exists()


def _crash(root: Path, fixture: dict) -> None:
    console = _console(root)
    record = fixture["apply"]

    def crash(boundary: str) -> None:
        if boundary == "before_apply_canonical_commit":
            assert (root / "notes" / "note.txt").read_bytes() == V1.encode()
            memory = console.orchestrator.memory_service
            assert memory.get_artifact_physical_version(ARTIFACTS[0]) is None
            assert memory.get_artifact_physical_saga(record["saga_id"]).phase == "effect_dispatched"
            fixture["stage"] = "crash"
            _save_fixture(root, fixture)
            print(
                json.dumps(
                    {
                        "stage": "crash",
                        "process_exit_code": CRASH_EXIT_CODE,
                        "boundary": boundary,
                        "power_loss_proof": False,
                    }
                ),
                flush=True,
            )
            os._exit(CRASH_EXIT_CODE)

    console.orchestrator.artifact_physical_sagas._failure_injector = crash
    try:
        console.execute(record["request_id"], **_authorized(record))
        raise AssertionError("physical crash boundary not reached")
    finally:
        console.close()


def _recover(root: Path, fixture: dict) -> None:
    record = fixture["apply"]
    assert _invoke(root, "status", request_id=record["request_id"])["phase"] == "effect_dispatched"
    console = _console(root)
    before = console.orchestrator.governance_service.load_action_confirmation_context(
        record["confirmation_receipt_id"]
    )
    assert before.claim is not None
    console.close()
    outcome = _invoke(root, "recover", request_id=record["request_id"], **_authorized(record))
    assert outcome["phase"] == "completed"
    _invoke(root, "execute", refused=True, request_id=record["request_id"], **_authorized(record))
    assert (
        _invoke(root, "recover", request_id=record["request_id"], **_authorized(record))["phase"]
        == "completed"
    )
    console = _console(root)
    try:
        after = console.orchestrator.governance_service.load_action_confirmation_context(
            record["confirmation_receipt_id"]
        )
        assert after == before, "recovery must not mint or reclaim authorization"
        assert (
            console.orchestrator.memory_service.get_artifact_physical_version(ARTIFACTS[0])
            is not None
        )
    finally:
        console.close()
    assert (root / "notes" / "note.txt").read_bytes() == V1.encode()


def _rollback(root: Path, fixture: dict) -> None:
    replacement = _invoke(
        root,
        "prepare",
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref=ARTIFACTS[1],
        resource_ref="text:notes/note.txt",
        desired_file=root / "inputs" / "v2.txt",
        operation="replace_text",
        expected_current_sha256=sha256(V1.encode()).hexdigest(),
        supersedes_artifact_ref=ARTIFACTS[0],
    )
    confirmation = _invoke(
        root, "confirm", request_id=replacement["request_id"], **_exact(replacement)
    )
    replacement["confirmation_receipt_id"] = confirmation["confirmation_receipt_id"]
    assert (
        _invoke(root, "execute", request_id=replacement["request_id"], **_authorized(replacement))[
            "phase"
        ]
        == "completed"
    )
    assert (root / "notes" / "note.txt").read_bytes() == V2.encode()
    rollback = _invoke(root, "prepare-rollback", request_id=replacement["request_id"])
    assert rollback["operation"] == "rollback" and rollback["confirmation_receipt_id"] is None
    assert rollback["before_sha256"] == sha256(V2.encode()).hexdigest()
    assert rollback["desired_sha256"] == sha256(V1.encode()).hexdigest()
    _invoke(root, "confirm", refused=True, request_id=rollback["request_id"], **_exact(rollback))
    confirmation = _invoke(
        root, "confirm-rollback", request_id=rollback["request_id"], **_exact(rollback)
    )
    rollback["confirmation_receipt_id"] = confirmation["confirmation_receipt_id"]
    assert rollback["confirmation_receipt_id"] != replacement["confirmation_receipt_id"]
    _invoke(
        root,
        "rollback",
        refused=True,
        request_id=rollback["request_id"],
        **_exact(rollback),
        confirmation_receipt_id=replacement["confirmation_receipt_id"],
    )
    assert (root / "notes" / "note.txt").read_bytes() == V2.encode()
    assert (
        _invoke(root, "rollback", request_id=rollback["request_id"], **_authorized(rollback))[
            "phase"
        ]
        == "completed"
    )
    fixture.update(replacement=replacement, rollback=rollback)


def _verify(root: Path, fixture: dict) -> None:
    console = _console(root)
    from observability_service.service import ObservabilityQuery

    try:
        memory, governance = (
            console.orchestrator.memory_service,
            console.orchestrator.governance_service,
        )
        lineage = memory.get_artifact_physical_lineage(MISSION, ARTIFACTS[0])
        assert lineage.active_artifact_ref == ARTIFACTS[0] and lineage.revision == 3
        for key in ("apply", "replacement", "rollback"):
            record = fixture[key]
            assert console.status(record["request_id"])["phase"] == "completed"
            commit = memory.get_artifact_physical_canonical_commit_receipt(record["saga_id"])
            assert commit is not None and not commit.contains_content
            assert memory.verify_artifact_physical_canonical_commit_receipt(commit)
            outbox = memory.get_artifact_physical_outbox_for_saga(record["saga_id"])
            assert outbox is not None and not outbox.contains_content
            assert outbox.canonical_event_fingerprint == commit.canonical_event_fingerprint
            assert (
                memory.repository.fetch_artifact_physical_outbox_delivery(outbox.outbox_id)
                is not None
            )
            context = governance.load_action_confirmation_context(record["confirmation_receipt_id"])
            assert (
                context.claim is not None
                and context.receipt.action_fingerprint == record["action_fingerprint"]
            )
            source_operation = (
                commit.physical_operation_id
                if key != "rollback"
                else (
                    memory.get_artifact_physical_rollback_plan(
                        record["saga_id"]
                    ).mutation_operation_id
                )
            )
            mutation = governance.load_local_text_mutation_receipt_exact(
                source_operation,
                expected_receipt_fingerprint=commit.mutation_receipt_fingerprint,
            )
            assert governance.verify_local_text_mutation_receipt_exact(mutation)
            if key == "rollback":
                receipt = governance.load_local_text_rollback_receipt_exact(
                    commit.physical_operation_id,
                    expected_rollback_receipt_fingerprint=commit.rollback_receipt_fingerprint,
                )
                assert governance.verify_local_text_rollback_receipt_exact(receipt)
        assert not memory.list_pending_artifact_physical_outbox(limit=20)
        events = console.orchestrator.observability_service.list_recent_events(
            ObservabilityQuery(limit=200)
        )
        rendered = json.dumps([asdict(event) for event in events], default=str)
        assert events and V1.strip() not in rendered and V2.strip() not in rendered
        assert str(root) not in rendered and "desired_text" not in rendered
        challenge_events = [event for event in events if event.source_service == "jarvis-console"]
        assert challenge_events and all(
            event.payload.get("contains_content") is False for event in challenge_events
        )
    finally:
        console.close()
    assert (root / "notes" / "note.txt").read_bytes() == V1.encode()


def run_stage(stage: str, root: Path) -> dict:
    """Internal test seam; production main never accepts an alternate root."""
    if sys.platform != "linux" or stage not in STAGES:
        raise ValueError("persistent_scenario_linux_stage_required")
    root = Path(root)
    info = root.lstat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o700
    ):
        raise ValueError("persistent_scenario_private_root_required")
    if stage == "prepare":
        if any(root.iterdir()):
            raise ValueError("persistent_scenario_empty_volume_required")
        fixture = _prepare(root)
    else:
        fixture = _load_fixture(root, stage)
        {
            "confirm": _confirm,
            "crash": _crash,
            "recover": _recover,
            "rollback": _rollback,
            "verify": _verify,
        }[stage](root, fixture)
    fixture["stage"] = stage
    _save_fixture(root, fixture)
    return {
        "stage": stage,
        "status": "passed",
        "storage": "exclusive_linux_volume",
        "contains_content": False,
        "power_loss_proof": False,
    }


def main(stage: str | None = None) -> int:
    if stage is None:
        if len(sys.argv) != 2:
            return 2
        stage = sys.argv[1]
    if sys.platform != "linux" or stage not in STAGES:
        return 2
    print(json.dumps(run_stage(stage, VALIDATION_ROOT), sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
