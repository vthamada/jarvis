"""MB218 preparation and negative boundary evidence; no physical effects here."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from apps.jarvis_console.physical_bootstrap import build_physical_orchestrator
from apps.jarvis_console.physical_operations import PhysicalOperationsConsole
from shared.artifact_physical_saga import seal_artifact_physical_apply_plan
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.types import MissionId, MissionStatus

MISSION = "mission://physical-console/test"
WORK = "work-item://physical-console/test"
OPERATOR = "operator://physical-console/test"
USER = "user://physical-console/test"
SESSION = "session://physical-console/test"


@pytest.fixture
def prepared_console(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    orchestrator = build_physical_orchestrator(
        runtime_dir=tmp_path / "runtime",
        roots={"notes": root},
        enable_execution=False,
    )
    orchestrator.memory_service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId(MISSION),
            mission_goal="Prepare an inspectable artifact",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=datetime.now(UTC).isoformat(),
            owner_context=USER,
            objective_ref="objective://physical-console/test",
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
    console = PhysicalOperationsConsole(orchestrator, OPERATOR, USER)
    yield console, root
    console.close()


def prepare(console, **changes):
    inputs = dict(
        mission_id=MISSION,
        work_item_ref=WORK,
        artifact_ref="artifact://physical-console/v1",
        resource_ref="text:notes/note.txt",
        desired_text="private test content\n",
        session_id=SESSION,
    )
    inputs.update(changes)
    return console.prepare(**inputs)


def exact(prepared):
    return {
        "challenge_id": prepared["challenge_id"],
        "action_fingerprint": prepared["action_fingerprint"],
    }


def test_prepare_inspect_confirm_are_separate_without_target_or_canonical_effect(prepared_console):
    console, root = prepared_console
    result = prepare(console)
    assert result["purpose"] == "apply" and result["operation"] == "create_text"
    assert result["relative_path"] == "note.txt" and result["root_alias"] == "notes"
    assert result["preview_sensitive"] and "+private test content" in result["preview"]
    assert result["risk_level"] == "moderate" and not result["durable"]
    assert result["confirmation_receipt_id"] is None
    assert console.status(result["request_id"])["phase"] == "prepared"
    assert console.inspect(result["request_id"])["preview"] == result["preview"]
    confirmation = console.confirm(result["request_id"], **exact(result))
    assert confirmation["confirmation_receipt_id"]
    assert console.status(result["request_id"])["phase"] == "confirmed"
    assert not (root / "note.txt").exists()
    assert console._saga(result["saga_id"]) is None
    assert (
        console.orchestrator.memory_service.get_artifact_physical_version(result["artifact_ref"])
        is None
    )
    record = console._store.load(result["request_id"])
    assert "unified_diff" not in str(record) and "preview" not in record
    assert "preparation" not in record and "persistence_allowed" not in str(record)


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"mission_id": "mission://missing"}, "mission_unknown"),
        ({"work_item_ref": "work-item://missing"}, "work_item_mismatch"),
        ({"resource_ref": "text:notes/../escape.txt"}, "resource_invalid"),
        ({"resource_ref": "text:notes/C:/escape.txt"}, "resource_invalid"),
        ({"operation": "delete"}, "operation_invalid"),
        ({"operation": "replace_text"}, "replace_requires_canonical_predecessor"),
        ({"desired_text": "x" * 262145}, "content_limit"),
    ],
)
def test_invalid_inputs_never_prepare_or_write(prepared_console, changes, code):
    console, root = prepared_console
    with pytest.raises(ValueError, match=code):
        prepare(console, **changes)
    assert list(root.iterdir()) == []


def test_mission_owner_active_and_work_item_ready_required(prepared_console, monkeypatch):
    console, root = prepared_console
    memory = console.orchestrator.memory_service
    mission = memory.get_mission_state(MISSION)
    mission.owner_context = "user://other"
    # owner_context is not persisted by the current Memory repository. This
    # branch is an explicit in-process double, not durable human-owner evidence.
    with monkeypatch.context() as context:
        context.setattr(memory, "get_mission_state", lambda mission_id: mission)
        with pytest.raises(ValueError, match="owner_mismatch"):
            prepare(console)
    mission.owner_context = USER
    mission.mission_status = MissionStatus.PAUSED
    memory.repository.upsert_mission_state(mission)
    with pytest.raises(ValueError, match="mission_not_active"):
        prepare(console)
    mission.mission_status = MissionStatus.ACTIVE
    mission.work_items[0].blocking_state = "blocked"
    memory.repository.upsert_mission_state(mission)
    with pytest.raises(ValueError, match="work_item_mismatch"):
        prepare(console)
    assert list(root.iterdir()) == []


def test_confirmation_requires_exact_challenge_and_fingerprint(prepared_console):
    console, root = prepared_console
    result = prepare(console)
    with pytest.raises(ValueError, match="challenge_mismatch"):
        console.confirm(
            result["request_id"],
            challenge_id="wrong",
            action_fingerprint=result["action_fingerprint"],
        )
    with pytest.raises(ValueError, match="challenge_mismatch"):
        console.confirm(
            result["request_id"], challenge_id=result["challenge_id"], action_fingerprint="0" * 64
        )
    with pytest.raises(ValueError, match="wrong_confirmation_command"):
        console.confirm_rollback(result["request_id"], **exact(result))
    console.confirm(result["request_id"], **exact(result))
    with pytest.raises(ValueError, match="already_confirmed"):
        console.confirm(result["request_id"], **exact(result))
    assert list(root.iterdir()) == []


def test_execute_does_not_confirm_and_receipts_are_not_interchangeable(prepared_console):
    console, root = prepared_console
    result = prepare(console)
    with pytest.raises(ValueError, match="receipt_mismatch"):
        console.execute(result["request_id"], **exact(result), confirmation_receipt_id="missing")
    assert console.status(result["request_id"])["phase"] == "prepared"
    confirmation = console.confirm(result["request_id"], **exact(result))
    other = prepare(console, artifact_ref="artifact://other")
    with pytest.raises(ValueError, match="receipt_mismatch"):
        console.execute(
            other["request_id"],
            **exact(other),
            confirmation_receipt_id=confirmation["confirmation_receipt_id"],
        )
    assert list(root.iterdir()) == []


def test_backend_refusal_before_journal_or_saga_when_execution_not_enabled(prepared_console):
    console, root = prepared_console
    result = prepare(console)
    confirmation = console.confirm(result["request_id"], **exact(result))
    with pytest.raises(ValueError, match="execution_(backend_unavailable|not_enabled)"):
        console.execute(
            result["request_id"],
            **exact(result),
            confirmation_receipt_id=confirmation["confirmation_receipt_id"],
        )
    assert list(root.iterdir()) == []
    assert console._saga(result["saga_id"]) is None


def test_expired_challenge_is_not_confirmed(prepared_console):
    console, _root = prepared_console
    result = prepare(console)
    console._clock = lambda: datetime.now(UTC) + timedelta(minutes=5)
    with pytest.raises(ValueError):
        console.confirm(result["request_id"], **exact(result))
    assert console.status(result["request_id"])["phase"] == "prepared"


def test_foreign_identity_and_resealed_canonical_plan_cache_tamper_fail_closed(prepared_console):
    console, _root = prepared_console
    result = prepare(console)
    console.operator_identity_ref = "operator://other"
    with pytest.raises(ValueError, match="identity_mismatch"):
        console.status(result["request_id"])
    console.operator_identity_ref = OPERATOR
    record = console._store.load(result["request_id"])
    plan = ArtifactPhysicalApplyPlanContract(**record["plan"])
    tampered = seal_artifact_physical_apply_plan(
        replace(
            plan,
            artifact_ref="artifact://tampered",
            lineage_root_ref="artifact://tampered",
        )
    )
    record["plan"] = asdict(tampered)
    console._store.save(result["request_id"], record, replace=True)
    with pytest.raises(ValueError, match="exact_binding_mismatch"):
        console.status(result["request_id"])


def test_fresh_inspection_rejects_human_edits(prepared_console):
    console, root = prepared_console
    result = prepare(console)
    (root / "note.txt").write_text("human change", encoding="utf-8")
    with pytest.raises(ValueError, match="create_target_exists"):
        console.inspect(result["request_id"])
    assert (root / "note.txt").read_text() == "human change"


def test_telemetry_is_content_free_and_preview_is_not_in_status(prepared_console):
    from observability_service.service import ObservabilityQuery

    console, root = prepared_console
    result = prepare(console)
    console.confirm(result["request_id"], **exact(result))
    events = console.orchestrator.observability_service.list_recent_events(
        ObservabilityQuery(limit=10)
    )
    rendered = str([event.payload for event in events])
    assert "private test content" not in rendered and str(root) not in rendered
    assert "preview" not in rendered and "desired_text" not in rendered
    assert "preview" not in console.status(result["request_id"])


def test_operator_input_cache_tamper_and_swapped_challenge_detected(prepared_console):
    console, root = prepared_console
    first = prepare(console)
    second = prepare(console, artifact_ref="artifact://other")
    record = console._store.load(first["request_id"])
    original_text = record["operator_input"]["desired_text"]
    record["operator_input"]["desired_text"] = "tampered"
    console._store.save(first["request_id"], record, replace=True)
    with pytest.raises(ValueError, match="input_changed"):
        console.status(first["request_id"])
    record["operator_input"]["desired_text"] = original_text
    record["challenge_id"] = second["challenge_id"]
    console._store.save(first["request_id"], record, replace=True)
    with pytest.raises(ValueError, match="challenge_mismatch"):
        console.status(first["request_id"])
    assert list(root.iterdir()) == []


def test_invalid_identifiers_and_windows_sensitive_store_refusal(tmp_path, monkeypatch):
    from apps.jarvis_console import physical_operations

    with pytest.raises(ValueError, match="identity_required"):
        PhysicalOperationsConsole(None, "", USER)
    monkeypatch.setattr(physical_operations.sys, "platform", "win32")
    with pytest.raises(ValueError, match="private_store_unavailable"):
        PhysicalOperationsConsole(None, OPERATOR, USER, runtime_dir=tmp_path / "sensitive")
    assert not (tmp_path / "sensitive").exists()


def test_corrupt_plan_and_clock_errors_do_not_echo_private_cache_content(prepared_console):
    console, _root = prepared_console
    result = prepare(console)
    record = console._store.load(result["request_id"])
    record["plan"]["unexpected_private_secret"] = "private"
    console._store.save(result["request_id"], record, replace=True)
    with pytest.raises(ValueError, match="physical_console_request_corrupt") as failure:
        console.status(result["request_id"])
    assert "private" not in str(failure.value)

    def broken_clock():
        raise RuntimeError("private token")

    console._clock = broken_clock
    with pytest.raises(ValueError, match="physical_console_clock_invalid"):
        prepare(console)


@pytest.mark.parametrize("field", ["transaction_policy_version", "transaction_backend_version"])
def test_resealed_transaction_version_drift_is_rejected_before_status_confirm(
    prepared_console, field
):
    console, root = prepared_console
    result = prepare(console)
    record = console._store.load(result["request_id"])
    plan = ArtifactPhysicalApplyPlanContract(**record["plan"])
    altered = seal_artifact_physical_apply_plan(replace(plan, **{field: "tampered-version"}))
    record["plan"] = asdict(altered)
    console._store.save(result["request_id"], record, replace=True)
    with pytest.raises(ValueError, match="preflight_binding_mismatch"):
        console.status(result["request_id"])
    with pytest.raises(ValueError, match="preflight_binding_mismatch"):
        console.confirm(result["request_id"], **exact(result))
    assert list(root.iterdir()) == []


@pytest.mark.parametrize(
    "purpose,journal_error",
    [
        ("apply", "local_text_transaction_journal_missing"),
        ("rollback", "local_text_transaction_journal_missing"),
        ("rollback", "local_text_rollback_request_required_before_journal"),
    ],
)
@pytest.mark.parametrize(
    "changed_scope,code",
    [
        ("paused", "mission_not_active"),
        ("blocked", "work_item_mismatch"),
        ("objective", "objective_changed"),
    ],
)
def test_missing_journal_recovery_revalidates_scope_before_constructing_request(
    prepared_console, monkeypatch, purpose, journal_error, changed_scope, code
):
    """Declared recovery seam doubles; not evidence of physical execution."""
    console, root = prepared_console
    prepared = prepare(console)
    confirmation = console.confirm(prepared["request_id"], **exact(prepared))
    authorization = {
        **exact(prepared),
        "confirmation_receipt_id": confirmation["confirmation_receipt_id"],
    }
    record, plan, context = console._authorized(
        prepared["request_id"],
        authorization["challenge_id"],
        authorization["action_fingerprint"],
        authorization["confirmation_receipt_id"],
    )
    # A rollback-shaped seam exercises the same scope fields. Real rollback
    # contracts/physical effects remain the Linux integration test's concern.
    record["purpose"] = purpose
    monkeypatch.setattr(console, "_authorized", lambda *args: (record, plan, context))
    monkeypatch.setattr(console, "_require_execution_platform", lambda: None)
    monkeypatch.setattr(
        console,
        "_saga",
        lambda saga_id: SimpleNamespace(
            phase="effect_dispatched" if purpose == "apply" else "rollback_effect_dispatched"
        ),
    )
    calls = []

    def journal_missing(saga_id, *, request):
        calls.append(request)
        raise ValueError(journal_error)

    def must_not_construct(*args):
        pytest.fail("new physical request constructed after canonical scope changed")

    monkeypatch.setattr(
        console.orchestrator, f"recover_artifact_physical_{purpose}", journal_missing
    )
    monkeypatch.setattr(console, "_fresh_preflight", must_not_construct)
    monkeypatch.setattr(console, "_rollback_request", must_not_construct)
    memory = console.orchestrator.memory_service
    mission = memory.get_mission_state(MISSION)
    if changed_scope == "paused":
        mission.mission_status = MissionStatus.PAUSED
    elif changed_scope == "blocked":
        mission.work_items[0].blocking_state = "blocked"
    else:
        mission.objective_ref = "objective://changed"
    memory.repository.upsert_mission_state(mission)
    with pytest.raises(ValueError, match=code):
        console.recover(prepared["request_id"], **authorization)
    assert calls == [None]
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_historical_journal_recovery_does_not_require_active_mission(
    prepared_console, monkeypatch, purpose
):
    """Declared recovery seam doubles; no effect or journal is fabricated."""
    console, root = prepared_console
    prepared = prepare(console)
    confirmation = console.confirm(prepared["request_id"], **exact(prepared))
    authorization = {
        **exact(prepared),
        "confirmation_receipt_id": confirmation["confirmation_receipt_id"],
    }
    record, plan, context = console._authorized(
        prepared["request_id"],
        authorization["challenge_id"],
        authorization["action_fingerprint"],
        authorization["confirmation_receipt_id"],
    )
    record["purpose"] = purpose
    monkeypatch.setattr(console, "_authorized", lambda *args: (record, plan, context))
    monkeypatch.setattr(console, "_require_execution_platform", lambda: None)
    monkeypatch.setattr(
        console,
        "_saga",
        lambda saga_id: SimpleNamespace(
            phase="effect_dispatched" if purpose == "apply" else "rollback_effect_dispatched"
        ),
    )
    calls = []
    monkeypatch.setattr(
        console.orchestrator,
        f"recover_artifact_physical_{purpose}",
        lambda saga_id, *, request: calls.append(request),
    )
    monkeypatch.setattr(console, "status", lambda request_id: {"historical_recovery": True})
    mission = console.orchestrator.memory_service.get_mission_state(MISSION)
    mission.mission_status = MissionStatus.PAUSED
    console.orchestrator.memory_service.repository.upsert_mission_state(mission)
    assert console.recover(prepared["request_id"], **authorization) == {"historical_recovery": True}
    assert calls == [None]
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("reader", ["status", "inspect"])
def test_committed_confirmation_reconciles_after_cache_save_failure_and_restart(
    prepared_console, monkeypatch, reader
):
    console, root = prepared_console
    prepared = prepare(console)
    cache_before = dict(console._store._memory)

    def disk_full(*args, **kwargs):
        raise OSError("injected cache disk full")

    with monkeypatch.context() as context:
        context.setattr(console._store, "save", disk_full)
        with pytest.raises(OSError, match="cache disk full"):
            console.confirm(prepared["request_id"], **exact(prepared))
    governance = console.orchestrator.governance_service
    persisted = governance.load_action_confirmation_context_for_challenge(prepared["challenge_id"])
    assert persisted is not None and persisted.claim is None
    assert console._store.load(prepared["request_id"])["confirmation_receipt_id"] is None

    # Rebuild real services and restore only the stale ephemeral cache. This
    # proves the ledger seam on Windows without claiming durable Linux storage.
    restarted_core = build_physical_orchestrator(
        runtime_dir=root.parent / "runtime", roots={"notes": root}
    )
    restarted = PhysicalOperationsConsole(restarted_core, OPERATOR, USER)
    restarted._store._memory = cache_before

    def never_issue(*args, **kwargs):
        pytest.fail("reconciliation must not issue a new confirmation")

    monkeypatch.setattr(restarted_core.governance_service, "confirm_action_challenge", never_issue)
    try:
        result = getattr(restarted, reader)(prepared["request_id"])
        assert result["phase"] == "confirmed"
        assert result["confirmation_receipt_id"] == persisted.receipt.receipt_id
        assert result["expires_at"] == prepared["expires_at"]
        assert restarted.status(prepared["request_id"])["confirmation_receipt_id"] == (
            persisted.receipt.receipt_id
        )
        with pytest.raises(ValueError, match="already_confirmed"):
            restarted.confirm(prepared["request_id"], **exact(prepared))
        restarted._clock = lambda: datetime.now(UTC) + timedelta(minutes=5)
        expired = restarted.status(prepared["request_id"])
        assert expired["phase"] == "confirmed" and expired["challenge_state"] == "expired"
        assert (
            restarted_core.governance_service.load_action_confirmation_context_for_challenge(
                prepared["challenge_id"]
            )
            == persisted
        )
        assert list(root.iterdir()) == []
        assert restarted._saga(prepared["saga_id"]) is None
    finally:
        restarted.close()


def test_status_with_no_persisted_receipt_does_not_confirm_or_change_cache(prepared_console):
    console, root = prepared_console
    prepared = prepare(console)
    before = dict(console._store._memory)
    assert console.status(prepared["request_id"])["phase"] == "prepared"
    assert console._store._memory == before
    assert (
        console.orchestrator.governance_service.load_action_confirmation_context_for_challenge(
            prepared["challenge_id"]
        )
        is None
    )
    assert list(root.iterdir()) == []


def test_confirmation_reconciliation_save_failure_is_retryable_without_new_receipt(
    prepared_console, monkeypatch
):
    console, root = prepared_console
    prepared = prepare(console)
    governance = console.orchestrator.governance_service
    receipt = governance.confirm_action_challenge(
        prepared["challenge_id"],
        operator_identity_ref=OPERATOR,
        expected_action_fingerprint=prepared["action_fingerprint"],
    )
    before = dict(console._store._memory)

    def disk_full(*args, **kwargs):
        raise OSError("injected reconciliation save failure")

    with monkeypatch.context() as context:
        context.setattr(console._store, "save", disk_full)
        with pytest.raises(OSError, match="reconciliation save failure"):
            console.status(prepared["request_id"])
    assert console._store._memory == before
    assert console.status(prepared["request_id"])["confirmation_receipt_id"] == receipt.receipt_id
    persisted = governance.load_action_confirmation_context_for_challenge(prepared["challenge_id"])
    assert persisted.receipt == receipt and persisted.claim is None
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("drift", ["intent", "challenge", "operator", "fingerprint"])
def test_confirmation_reconciliation_rejects_foreign_context_without_cache_write(
    prepared_console, monkeypatch, drift
):
    console, root = prepared_console
    prepared = prepare(console)
    other = prepare(console, artifact_ref="artifact://other")
    governance = console.orchestrator.governance_service
    other_receipt = console.confirm(other["request_id"], **exact(other))
    foreign = governance.load_action_confirmation_context(other_receipt["confirmation_receipt_id"])
    # Obtain a valid own context without allowing the cache to observe it yet.
    receipt = governance.confirm_action_challenge(
        prepared["challenge_id"],
        operator_identity_ref=OPERATOR,
        expected_action_fingerprint=prepared["action_fingerprint"],
    )
    own = governance.load_action_confirmation_context(receipt.receipt_id)
    if drift == "intent":
        altered = replace(own, intent=foreign.intent)
    elif drift == "challenge":
        altered = replace(own, challenge=foreign.challenge)
    elif drift == "operator":
        altered = replace(
            own, receipt=replace(own.receipt, operator_identity_ref="operator://other")
        )
    else:
        altered = replace(own, receipt=replace(own.receipt, action_fingerprint="0" * 64))
    before = dict(console._store._memory)
    monkeypatch.setattr(
        governance, "load_action_confirmation_context_for_challenge", lambda challenge_id: altered
    )
    with pytest.raises(ValueError, match="receipt_mismatch"):
        console.status(prepared["request_id"])
    assert console._store._memory == before
    assert list(root.iterdir()) == []


@pytest.mark.parametrize("field", [
    "receipt_id", "challenge_id", "operator_identity_ref", "action_fingerprint",
])
@pytest.mark.parametrize("reader", ["status", "authorized"])
def test_cached_receipt_rechecks_all_exact_fields(prepared_console, monkeypatch, field, reader):
    """A declared ledger seam double; no physical or corrupted-ledger proof."""
    console, root = prepared_console
    prepared = prepare(console)
    confirmed = console.confirm(prepared["request_id"], **exact(prepared))
    governance = console.orchestrator.governance_service
    receipt_id = confirmed["confirmation_receipt_id"]
    context = governance.load_action_confirmation_context(receipt_id)
    altered = replace(context, receipt=replace(context.receipt, **{field: "foreign-value"}))
    calls = []

    def load(value):
        calls.append(value)
        # The authorized path performs a second ledger read after _load.
        return context if reader == "authorized" and len(calls) == 1 else altered

    monkeypatch.setattr(governance, "load_action_confirmation_context", load)
    with pytest.raises(ValueError, match="receipt_mismatch"):
        if reader == "status":
            console.status(prepared["request_id"])
        else:
            console._authorized(prepared["request_id"], **exact(prepared),
                                confirmation_receipt_id=receipt_id)
    assert list(root.iterdir()) == []
    assert console._saga(prepared["saga_id"]) is None
