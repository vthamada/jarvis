"""Real composed physical boundaries; skip, never emulate POSIX, on Windows."""

import sys
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_operations import PhysicalOperationsConsole
from shared.contracts import MissionStateContract, WorkItemStateContract
from shared.types import MissionId, MissionStatus

pytestmark = pytest.mark.skipif(
    sys.platform != "linux", reason="MB219 requires real Linux physical backend"
)
MISSION = "mission://mb219/physical-boundary"
WORK = "work-item://mb219/physical-boundary"


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
                mission_goal="Disposable MB219 physical scope boundary",
                mission_status=MissionStatus.ACTIVE,
                checkpoints=[],
                updated_at=datetime.now(UTC).isoformat(),
                objective_ref="objective://mb219/physical-boundary",
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
        "operator://mb219/physical-boundary",
        "user://mb219/physical-boundary",
        runtime_dir=tmp_path / "requests",
    ), root


def _prepare_confirm(console):
    prepared = console.prepare(
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref="artifact://mb219/physical-v1",
        resource_ref="text:notes/boundary.txt",
        desired_text="disposable MB219 content\n",
        session_id="session://mb219/physical-boundary",
        operation="create_text",
    )
    exact = {
        "challenge_id": prepared["challenge_id"],
        "action_fingerprint": prepared["action_fingerprint"],
    }
    receipt = console.confirm(prepared["request_id"], **exact)
    return prepared, {**exact, "confirmation_receipt_id": receipt["confirmation_receipt_id"]}


def _pause(console):
    memory = console.orchestrator.memory_service
    mission = memory.get_mission_state(MISSION)
    mission.mission_status = MissionStatus.PAUSED
    memory.repository.upsert_mission_state(mission)


def _assert_unclaimed(console, prepared):
    governance = console.orchestrator.governance_service
    context = governance.load_action_confirmation_context_for_challenge(prepared["challenge_id"])
    assert context is not None and context.claim is None
    assert (
        console.orchestrator.memory_service.get_artifact_physical_version(
            "artifact://mb219/physical-v1"
        )
        is None
    )


def test_pause_after_staging_precedes_first_claim_and_target_mutation(tmp_path):
    console, root = _build(tmp_path, seed=True)
    try:
        prepared, authorization = _prepare_confirm(console)

        def pause_at_stage(boundary):
            if boundary == "after_stage_durable":
                _pause(console)

        engine = console.orchestrator.operational_service._local_text_file_transaction_engine
        engine._failure_injector = pause_at_stage
        with pytest.raises(
            ValueError, match="physical_(?:first_)?effect_not_authorized|mission_not_active"
        ):
            console.execute(prepared["request_id"], **authorization)
        assert not (root / "boundary.txt").exists()
        _assert_unclaimed(console, prepared)
    finally:
        console.close()


def test_staged_journal_without_claim_is_not_historical_authority_after_restart(tmp_path):
    console, root = _build(tmp_path, seed=True)
    prepared, authorization = _prepare_confirm(console)

    def crash_at_stage(boundary):
        if boundary == "after_stage_durable":
            raise RuntimeError("disposable crash before first claim")

    engine = console.orchestrator.operational_service._local_text_file_transaction_engine
    engine._failure_injector = crash_at_stage
    try:
        with pytest.raises(RuntimeError, match="before first claim"):
            console.execute(prepared["request_id"], **authorization)
        assert not (root / "boundary.txt").exists()
        _assert_unclaimed(console, prepared)
        _pause(console)
    finally:
        console.close()
    console, _ = _build(tmp_path)
    try:
        with pytest.raises(
            ValueError, match="physical_(?:first_)?effect_not_authorized|mission_not_active"
        ):
            console.recover(prepared["request_id"], **authorization)
        assert not (root / "boundary.txt").exists()
        _assert_unclaimed(console, prepared)
    finally:
        console.close()


def test_durable_exact_claim_reconciles_after_pause_without_a_second_claim(tmp_path):
    console, root = _build(tmp_path, seed=True)
    prepared, authorization = _prepare_confirm(console)

    def crash_after_claim(boundary):
        if boundary == "after_claim":
            raise RuntimeError("disposable crash after exact claim")

    engine = console.orchestrator.operational_service._local_text_file_transaction_engine
    engine._failure_injector = crash_after_claim
    try:
        with pytest.raises(RuntimeError, match="after exact claim"):
            console.execute(prepared["request_id"], **authorization)
        context = (
            console.orchestrator.governance_service.load_action_confirmation_context_for_challenge(
                prepared["challenge_id"]
            )
        )
        assert context is not None and context.claim is not None
        original_claim = context.claim
        assert not (root / "boundary.txt").exists()
        _pause(console)
    finally:
        console.close()
    console, _ = _build(tmp_path)
    try:
        assert console.recover(prepared["request_id"], **authorization)["phase"] == "completed"
        recovered = (
            console.orchestrator.governance_service.load_action_confirmation_context_for_challenge(
                prepared["challenge_id"]
            )
        )
        assert recovered.claim == original_claim
        assert (root / "boundary.txt").read_text() == "disposable MB219 content\n"
        assert (
            console.orchestrator.memory_service.get_artifact_physical_version(
                "artifact://mb219/physical-v1"
            )
            is not None
        )
    finally:
        console.close()


def test_confirmed_rollback_does_not_overwrite_a_later_human_edit(tmp_path):
    console, root = _build(tmp_path, seed=True)
    try:
        prepared, authorization = _prepare_confirm(console)
        console.execute(prepared["request_id"], **authorization)
        replacement = console.prepare(
            mission_id=MISSION,
            work_item_ref=WORK,
            artifact_ref="artifact://mb219/physical-v2",
            resource_ref="text:notes/boundary.txt",
            desired_text="disposable replacement\n",
            session_id="session://mb219/physical-boundary",
            operation="replace_text",
            expected_current_sha256=sha256(b"disposable MB219 content\n").hexdigest(),
            supersedes_artifact_ref="artifact://mb219/physical-v1",
        )
        exact = {
            "challenge_id": replacement["challenge_id"],
            "action_fingerprint": replacement["action_fingerprint"],
        }
        confirmation = console.confirm(replacement["request_id"], **exact)
        console.execute(
            replacement["request_id"],
            **exact,
            confirmation_receipt_id=confirmation["confirmation_receipt_id"],
        )
        rollback = console.prepare_rollback(
            replacement["request_id"], session_id="session://mb219/physical-boundary"
        )
        rollback_exact = {
            "challenge_id": rollback["challenge_id"],
            "action_fingerprint": rollback["action_fingerprint"],
        }
        rollback_confirmation = console.confirm_rollback(rollback["request_id"], **rollback_exact)
        (root / "boundary.txt").write_text("later human content\n", encoding="utf-8")
        with pytest.raises(ValueError, match="later_edit_detected|physical_state|hash_mismatch"):
            console.rollback(
                rollback["request_id"],
                **rollback_exact,
                confirmation_receipt_id=rollback_confirmation["confirmation_receipt_id"],
            )
        assert (root / "boundary.txt").read_text() == "later human content\n"
        governance = console.orchestrator.governance_service
        context = governance.load_action_confirmation_context_for_challenge(
            rollback["challenge_id"]
        )
        assert context is not None and context.claim is None
        lineage = console.orchestrator.memory_service.get_artifact_physical_lineage(
            MISSION, "artifact://mb219/physical-v1"
        )
        assert lineage.revision == 2
        assert lineage.active_artifact_ref == "artifact://mb219/physical-v2"
    finally:
        console.close()
