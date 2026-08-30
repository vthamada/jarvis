from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from sqlite3 import IntegrityError, connect

import pytest
from governance_service.service import GovernanceService
from test_adapter_execution_governance import (
    CLAIMED_AT,
    EFFECT_AT,
    _build_harness,
    _decision,
    _ExecutionHarness,
)
from test_adapter_execution_governance import (
    _claim as _claim_execution,
)

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.autonomy_ladder import AUTONOMY_ACTION_POLICY_VERSION
from shared.contracts import (
    ActionIntentContract,
    AutonomyActionPolicyDecisionContract,
    HumanConfirmationReceiptContract,
    LocalTextFileRollbackGrantClaimContract,
    LocalTextFileRollbackGrantContract,
    LocalTextFileRollbackRequestContract,
    LocalTextMutationReceipt,
    LocalTextRollbackReceipt,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR,
    SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY,
    build_local_text_file_rollback_registry_snapshot,
    build_mutation_receipt_fingerprint,
    build_rollback_receipt_fingerprint,
)
from shared.schemas import (
    LOCAL_TEXT_FILE_ROLLBACK_GRANT_CLAIM_SCHEMA,
    LOCAL_TEXT_FILE_ROLLBACK_GRANT_SCHEMA,
    LOCAL_TEXT_FILE_ROLLBACK_REQUEST_SCHEMA,
    LOCAL_TEXT_MUTATION_RECEIPT_SCHEMA,
    LOCAL_TEXT_ROLLBACK_RECEIPT_SCHEMA,
)
from shared.types import RiskLevel

ROLLBACK_REQUESTED_AT = "2026-08-30T12:04:00Z"
ROLLBACK_ISSUED_AT = "2026-08-30T12:04:10Z"
ROLLBACK_CONFIRMED_AT = "2026-08-30T12:04:20Z"
ROLLBACK_STAGING_AT = "2026-08-30T12:04:30Z"
ROLLBACK_CLAIMED_AT = "2026-08-30T12:04:40Z"
ROLLBACK_EFFECT_AT = "2026-08-30T12:04:50Z"
ROLLBACK_RECEIPT_AT = "2026-08-30T12:04:55Z"
ROLLBACK_RECORDED_AT = "2026-08-30T12:05:00Z"
ROLLBACK_EXPIRES_AT = "2026-08-30T12:05:30Z"
ROLLBACK_EXPIRED_AT = "2026-08-30T12:05:31Z"
ROLLBACK_OPERATION_ID = "operation://mb216/rollback-one"
ROLLBACK_RESERVATION = "8" * 64


@dataclass(frozen=True)
class _RollbackHarness:
    execution: _ExecutionHarness
    mutation_receipt: LocalTextMutationReceipt
    rollback_request: LocalTextFileRollbackRequestContract
    rollback_intent: ActionIntentContract
    rollback_decision: AutonomyActionPolicyDecisionContract
    rollback_grant: LocalTextFileRollbackGrantContract
    confirmation_receipt: HumanConfirmationReceiptContract

    @property
    def governance(self) -> GovernanceService:
        return self.execution.governance

    @property
    def database_path(self) -> Path:
        return self.execution.database_path


def _count(database_path: Path, table: str) -> int:
    with connect(database_path) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _mutation_receipt(
    execution: _ExecutionHarness,
    *,
    applied_event_fingerprint: str = "a" * 64,
    committed_at: str = EFFECT_AT,
) -> LocalTextMutationReceipt:
    claim = execution.governance.load_adapter_execution_claim_for_recovery_exact(
        "operation://mb216/execute-one"
    )
    request = execution.execution_request
    receipt = LocalTextMutationReceipt(
        operation_id=str(claim.operation_id),
        execution_grant_id=claim.grant_id,
        execution_claim_id=claim.claim_id,
        operation=request.operation,
        resource_ref=request.resource_ref,
        subject_ref=request.subject_ref,
        preflight_fingerprint=request.preflight_fingerprint,
        before_content_sha256=request.before_content_sha256,
        desired_content_sha256=request.desired_content_sha256,
        root_config_fingerprint=request.root_config_fingerprint,
        applied_event_fingerprint=applied_event_fingerprint,
        committed_at=committed_at,
        mutation_status="applied",
        receipt_fingerprint="0" * 64,
    )
    return replace(
        receipt,
        receipt_fingerprint=build_mutation_receipt_fingerprint(receipt),
    )


def _rollback_intent(
    request: LocalTextFileRollbackRequestContract,
    *,
    suffix: str = "one",
) -> ActionIntentContract:
    return build_action_intent(
        intent_id=f"local-text-rollback-intent://mb216/{suffix}",
        origin_request_id=f"request://mb216/rollback-{suffix}",
        session_id="session://mb216/operator",
        mission_id=f"mission://mb216/rollback-{suffix}",
        operator_identity_ref=request.subject_ref,
        handler_id=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.executor_ref,
        handler_version=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_version,
        operation=request.operation,
        target_ref=request.resource_ref,
        content_digest=request.restored_content_sha256,
        precondition_digest=request.rollback_request_fingerprint,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=f"localTextRollbackIntentNonceMb216{suffix}123456",
        issued_at=ROLLBACK_REQUESTED_AT,
        expires_at=ROLLBACK_EXPIRES_AT,
        now=ROLLBACK_REQUESTED_AT,
    )


def _build_rollback_harness(tmp_path: Path) -> _RollbackHarness:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    mutation_receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT
    execution.governance.activate_local_text_file_rollback_registry(
        SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY
    )
    assert (
        execution.governance.record_local_text_mutation_receipt(mutation_receipt)
        == mutation_receipt
    )
    rollback_request = execution.governance.prepare_local_text_file_rollback(
        mutation_receipt,
        rollback_operation_id=ROLLBACK_OPERATION_ID,
    )
    rollback_intent = _rollback_intent(rollback_request)
    rollback_decision = _decision("execute_external_action")
    registry, descriptor = execution.governance.resolve_active_local_text_file_rollback_descriptor(
        rollback_request
    )
    execution.clock.current = ROLLBACK_ISSUED_AT
    rollback_grant = execution.governance.issue_local_text_file_rollback_grant(
        rollback_intent,
        rollback_request,
        rollback_decision,
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
    )
    challenge = execution.governance.issue_action_confirmation_challenge(rollback_intent)
    confirmation_receipt = execution.governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=rollback_intent.operator_identity_ref,
        expected_action_fingerprint=rollback_intent.action_fingerprint,
        confirmed_at=ROLLBACK_CONFIRMED_AT,
    )
    return _RollbackHarness(
        execution=execution,
        mutation_receipt=mutation_receipt,
        rollback_request=rollback_request,
        rollback_intent=rollback_intent,
        rollback_decision=rollback_decision,
        rollback_grant=rollback_grant,
        confirmation_receipt=confirmation_receipt,
    )


def _stage(harness: _RollbackHarness, **changes: str) -> bool:
    values = {
        "subject_ref": harness.rollback_intent.operator_identity_ref,
        "expected_grant_fingerprint": harness.rollback_grant.grant_fingerprint,
        "expected_action_fingerprint": harness.rollback_intent.action_fingerprint,
        "expected_rollback_request_fingerprint": (
            harness.rollback_request.rollback_request_fingerprint
        ),
        "intent_fingerprint": action_intent_fingerprint(harness.rollback_intent),
        "confirmation_receipt_id": harness.confirmation_receipt.receipt_id,
    }
    values.update(changes)
    return harness.governance.verify_local_text_file_rollback_grant_for_staging_exact(
        harness.rollback_grant.grant_id,
        **values,
    )


def _claim(
    harness: _RollbackHarness,
    *,
    rollback_operation_id: str = ROLLBACK_OPERATION_ID,
    rollback_journal_reservation_fingerprint: str = ROLLBACK_RESERVATION,
) -> LocalTextFileRollbackGrantClaimContract:
    return harness.governance.claim_local_text_file_rollback_grant_exact(
        harness.rollback_grant.grant_id,
        rollback_operation_id=rollback_operation_id,
        rollback_journal_reservation_fingerprint=(rollback_journal_reservation_fingerprint),
        subject_ref=harness.rollback_intent.operator_identity_ref,
        expected_grant_fingerprint=harness.rollback_grant.grant_fingerprint,
        expected_action_fingerprint=harness.rollback_intent.action_fingerprint,
        expected_rollback_request_fingerprint=(
            harness.rollback_request.rollback_request_fingerprint
        ),
        intent_fingerprint=action_intent_fingerprint(harness.rollback_intent),
        confirmation_receipt_id=harness.confirmation_receipt.receipt_id,
    )


def _rollback_receipt(
    harness: _RollbackHarness,
    claim: LocalTextFileRollbackGrantClaimContract,
    *,
    event_fingerprint: str = "c" * 64,
) -> LocalTextRollbackReceipt:
    receipt = LocalTextRollbackReceipt(
        operation_id=str(claim.rollback_operation_id),
        mutation_operation_id=harness.mutation_receipt.operation_id,
        rollback_grant_id=claim.grant_id,
        rollback_claim_id=claim.claim_id,
        mutation_receipt_fingerprint=harness.mutation_receipt.receipt_fingerprint,
        resource_ref=harness.mutation_receipt.resource_ref,
        restored_content_sha256=harness.rollback_request.restored_content_sha256,
        rolled_back_at=ROLLBACK_RECEIPT_AT,
        rolled_back_event_fingerprint=event_fingerprint,
        rollback_receipt_fingerprint="0" * 64,
    )
    return replace(
        receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(receipt),
    )


def test_mutation_receipt_is_recorded_independently_and_survives_restart(
    tmp_path: Path,
) -> None:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT

    with pytest.raises(KeyError, match="unknown local text mutation receipt"):
        execution.governance.prepare_local_text_file_rollback(
            receipt,
            rollback_operation_id=ROLLBACK_OPERATION_ID,
        )
    assert execution.governance.record_local_text_mutation_receipt(receipt) == receipt
    assert execution.governance.record_local_text_mutation_receipt(receipt) == receipt
    assert _count(execution.database_path, "local_text_mutation_receipts") == 1
    assert _count(execution.database_path, "local_text_file_rollback_requests") == 0

    restarted = GovernanceService(
        execution.database_path,
        trusted_execution_clock=execution.clock,
    )
    restarted.activate_local_text_file_rollback_registry(SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY)
    request = restarted.prepare_local_text_file_rollback(
        receipt,
        rollback_operation_id=ROLLBACK_OPERATION_ID,
    )
    assert request.mutation_receipt_fingerprint == receipt.receipt_fingerprint
    assert request.source_execution_request_fingerprint == (
        execution.execution_request.execution_request_fingerprint
    )
    execution.clock.current = ROLLBACK_EXPIRED_AT
    assert (
        restarted.prepare_local_text_file_rollback(
            receipt,
            rollback_operation_id=ROLLBACK_OPERATION_ID,
        )
        == request
    )
    assert _count(execution.database_path, "local_text_mutation_receipts") == 1
    assert _count(execution.database_path, "local_text_file_rollback_requests") == 1


def test_mutation_receipt_exact_proof_fails_closed_and_survives_restart(
    tmp_path: Path,
) -> None:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT
    execution.governance.record_local_text_mutation_receipt(receipt)

    assert (
        execution.governance.load_local_text_mutation_receipt_exact(
            receipt.operation_id,
            expected_receipt_fingerprint=receipt.receipt_fingerprint,
        )
        == receipt
    )
    assert execution.governance.verify_local_text_mutation_receipt_exact(receipt)
    restarted = GovernanceService(
        execution.database_path,
        trusted_execution_clock=execution.clock,
    )
    assert restarted.verify_local_text_mutation_receipt_exact(receipt)

    with pytest.raises(KeyError, match="unknown local text mutation receipt"):
        restarted.load_local_text_mutation_receipt_exact(
            "operation://mb217/wrong",
            expected_receipt_fingerprint=receipt.receipt_fingerprint,
        )
    with pytest.raises(KeyError, match="unknown local text mutation receipt"):
        restarted.load_local_text_mutation_receipt_exact(
            receipt.operation_id,
            expected_receipt_fingerprint="f" * 64,
        )
    divergent = replace(receipt, resource_ref="text:artifacts/divergent.txt")
    assert not restarted.verify_local_text_mutation_receipt_exact(divergent)

    with connect(execution.database_path) as connection:
        connection.execute("DROP TRIGGER local_text_mutation_receipts_no_update")
        connection.execute(
            """
            UPDATE local_text_mutation_receipts
            SET resource_ref = 'text:artifacts/tampered.txt'
            WHERE mutation_operation_id = ?
            """,
            (receipt.operation_id,),
        )
    assert not restarted.verify_local_text_mutation_receipt_exact(receipt)
    with pytest.raises(ValueError, match="adapter stored resource_ref mismatch"):
        restarted.load_local_text_mutation_receipt_exact(
            receipt.operation_id,
            expected_receipt_fingerprint=receipt.receipt_fingerprint,
        )


def test_shared_rollback_schemas_expose_distinct_stable_contracts() -> None:
    assert LOCAL_TEXT_MUTATION_RECEIPT_SCHEMA.contract_name == "LocalTextMutationReceipt"
    assert LOCAL_TEXT_ROLLBACK_RECEIPT_SCHEMA.contract_name == "LocalTextRollbackReceipt"
    assert "mutation_operation_id" in LOCAL_TEXT_ROLLBACK_RECEIPT_SCHEMA.required_fields
    assert LOCAL_TEXT_FILE_ROLLBACK_REQUEST_SCHEMA.contract_name == (
        "LocalTextFileRollbackRequestContract"
    )
    assert LOCAL_TEXT_FILE_ROLLBACK_GRANT_SCHEMA.contract_name == (
        "LocalTextFileRollbackGrantContract"
    )
    assert LOCAL_TEXT_FILE_ROLLBACK_GRANT_CLAIM_SCHEMA.contract_name == (
        "LocalTextFileRollbackGrantClaimContract"
    )


def test_mutation_receipt_rejects_tamper_conflict_and_untrusted_time(
    tmp_path: Path,
) -> None:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT

    forged = replace(
        receipt,
        desired_content_sha256="d" * 64,
        receipt_fingerprint="0" * 64,
    )
    forged = replace(
        forged,
        receipt_fingerprint=build_mutation_receipt_fingerprint(forged),
    )
    with pytest.raises(ValueError, match="persisted execution evidence"):
        execution.governance.record_local_text_mutation_receipt(forged)

    future = replace(receipt, committed_at=ROLLBACK_EXPIRED_AT, receipt_fingerprint="0" * 64)
    future = replace(
        future,
        receipt_fingerprint=build_mutation_receipt_fingerprint(future),
    )
    with pytest.raises(ValueError, match="future-dated"):
        execution.governance.record_local_text_mutation_receipt(future)

    backdated = replace(
        receipt,
        committed_at="2026-08-30T12:01:49Z",
        receipt_fingerprint="0" * 64,
    )
    backdated = replace(
        backdated,
        receipt_fingerprint=build_mutation_receipt_fingerprint(backdated),
    )
    with pytest.raises(ValueError, match="predates execution claim"):
        execution.governance.record_local_text_mutation_receipt(backdated)

    assert execution.governance.record_local_text_mutation_receipt(receipt) == receipt
    conflicting = replace(
        receipt,
        applied_event_fingerprint="b" * 64,
        receipt_fingerprint="0" * 64,
    )
    conflicting = replace(
        conflicting,
        receipt_fingerprint=build_mutation_receipt_fingerprint(conflicting),
    )
    with pytest.raises(ValueError, match="different receipt evidence"):
        execution.governance.record_local_text_mutation_receipt(conflicting)


def test_trusted_clock_blocks_backdated_rollback_issuance(tmp_path: Path) -> None:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT
    execution.governance.activate_local_text_file_rollback_registry(
        SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY
    )
    execution.governance.record_local_text_mutation_receipt(receipt)
    request = execution.governance.prepare_local_text_file_rollback(
        receipt,
        rollback_operation_id=ROLLBACK_OPERATION_ID,
    )
    intent = _rollback_intent(request)
    registry, descriptor = execution.governance.resolve_active_local_text_file_rollback_descriptor(
        request
    )
    execution.clock.current = ROLLBACK_EXPIRED_AT

    with pytest.raises(ValueError, match="rollback_(intent|grant_window)_invalid"):
        execution.governance.issue_local_text_file_rollback_grant(
            intent,
            request,
            _decision("execute_external_action"),
            expected_registry_fingerprint=registry.registry_fingerprint,
            expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        )


def test_rollback_requires_fresh_exact_confirmation_and_is_read_only_before_claim(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    counts = {
        table: _count(harness.database_path, table)
        for table in (
            "local_text_file_rollback_grants",
            "local_text_file_rollback_grant_claims",
            "action_confirmation_claims",
            "local_text_rollback_receipts",
        )
    }
    harness.execution.clock.current = ROLLBACK_STAGING_AT

    assert _stage(harness)
    assert not _stage(
        harness,
        confirmation_receipt_id=harness.execution.confirmation_receipt.receipt_id,
    )
    assert not _stage(harness, expected_grant_fingerprint="1" * 64)
    assert not _stage(harness, expected_action_fingerprint="2" * 64)
    assert not _stage(harness, expected_rollback_request_fingerprint="3" * 64)
    assert {table: _count(harness.database_path, table) for table in counts} == counts
    assert harness.rollback_intent.precondition_digest == (
        harness.rollback_request.rollback_request_fingerprint
    )
    assert harness.rollback_intent.content_digest == (
        harness.rollback_request.restored_content_sha256
    )
    assert harness.rollback_request.source_execution_request_fingerprint == (
        harness.execution.execution_request.execution_request_fingerprint
    )


def test_rollback_grant_is_idempotent_and_unique_per_mutation_receipt(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    context = harness.governance.load_local_text_file_rollback_grant_context(
        harness.rollback_grant.grant_id
    )
    harness.execution.clock.current = ROLLBACK_STAGING_AT
    assert (
        harness.governance.issue_local_text_file_rollback_grant(
            harness.rollback_intent,
            harness.rollback_request,
            harness.rollback_decision,
            expected_registry_fingerprint=context.registry.registry_fingerprint,
            expected_descriptor_fingerprint=context.descriptor.descriptor_fingerprint,
        )
        == harness.rollback_grant
    )

    duplicate_intent = _rollback_intent(harness.rollback_request, suffix="duplicate")
    with pytest.raises(ValueError, match="different rollback authority"):
        harness.governance.issue_local_text_file_rollback_grant(
            duplicate_intent,
            harness.rollback_request,
            harness.rollback_decision,
            expected_registry_fingerprint=context.registry.registry_fingerprint,
            expected_descriptor_fingerprint=context.descriptor.descriptor_fingerprint,
        )
    assert _count(harness.database_path, "local_text_file_rollback_grants") == 1


def test_joint_rollback_claim_is_atomic_concurrent_idempotent_and_distinct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    repository = harness.governance.action_confirmation_repository
    harness.execution.clock.current = ROLLBACK_CLAIMED_AT

    def fail_after_confirmation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected crash after rollback confirmation claim")

    with monkeypatch.context() as scoped:
        scoped.setattr(
            repository,
            "_insert_local_text_file_rollback_claim",
            fail_after_confirmation,
        )
        with pytest.raises(RuntimeError, match="injected crash"):
            _claim(harness)
    assert _count(harness.database_path, "action_confirmation_claims") == 1
    assert _count(harness.database_path, "local_text_file_rollback_grant_claims") == 0

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _claim(harness), range(8)))
    assert len({item.claim_id for item in results}) == 1
    claim = results[0]
    assert _claim(harness) == claim
    assert _count(harness.database_path, "action_confirmation_claims") == 2
    assert _count(harness.database_path, "local_text_file_rollback_grant_claims") == 1
    with pytest.raises(ValueError, match="already claimed"):
        _claim(harness, rollback_operation_id="operation://mb216/rollback-replay")
    with pytest.raises(ValueError, match="already claimed"):
        _claim(harness, rollback_journal_reservation_fingerprint="9" * 64)

    separate = _build_rollback_harness(tmp_path / "same-apply-reservation")
    separate.execution.clock.current = ROLLBACK_CLAIMED_AT
    with pytest.raises(ValueError, match="must differ from apply"):
        _claim(
            separate,
            rollback_journal_reservation_fingerprint="7" * 64,
        )


def test_rollback_operation_is_distinct_and_does_not_relax_apply_uniqueness(
    tmp_path: Path,
) -> None:
    execution = _build_harness(tmp_path)
    execution.clock.current = CLAIMED_AT
    _claim_execution(execution)
    receipt = _mutation_receipt(execution)
    execution.clock.current = ROLLBACK_REQUESTED_AT
    execution.governance.activate_local_text_file_rollback_registry(
        SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY
    )
    execution.governance.record_local_text_mutation_receipt(receipt)

    with pytest.raises(ValueError, match="operation_id_not_distinct"):
        execution.governance.prepare_local_text_file_rollback(
            receipt,
            rollback_operation_id=receipt.operation_id,
        )
    request = execution.governance.prepare_local_text_file_rollback(
        receipt,
        rollback_operation_id=ROLLBACK_OPERATION_ID,
    )
    with pytest.raises(ValueError, match="another rollback request"):
        execution.governance.prepare_local_text_file_rollback(
            receipt,
            rollback_operation_id="operation://mb216/rollback-two",
        )
    assert request.purpose == "rollback"
    assert _count(execution.database_path, "adapter_execution_grants") == 1
    assert _count(execution.database_path, "adapter_execution_grant_claims") == 1
    assert _count(execution.database_path, "local_text_file_rollback_grants") == 0


def test_expiry_blocks_new_rollback_effect_but_historical_recovery_survives_restart(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    harness.execution.clock.current = ROLLBACK_CLAIMED_AT
    claim = _claim(harness)
    harness.execution.clock.current = ROLLBACK_EFFECT_AT
    verify_effect = harness.governance.verify_local_text_file_rollback_claim_for_effect_start_exact
    assert verify_effect(
        claim,
        observed_root_config_fingerprint=harness.rollback_request.root_config_fingerprint,
        observed_expected_current_sha256=(harness.rollback_request.expected_current_sha256),
        observed_restored_content_sha256=(harness.rollback_request.restored_content_sha256),
    )

    harness.execution.clock.current = ROLLBACK_EXPIRED_AT
    assert not _stage(harness)
    assert not verify_effect(
        claim,
        observed_root_config_fingerprint=harness.rollback_request.root_config_fingerprint,
        observed_expected_current_sha256=(harness.rollback_request.expected_current_sha256),
        observed_restored_content_sha256=(harness.rollback_request.restored_content_sha256),
    )
    assert harness.governance.verify_local_text_file_rollback_claim_for_recovery_exact(claim)
    restarted = GovernanceService(
        harness.database_path,
        trusted_execution_clock=harness.execution.clock,
    )
    assert (
        restarted.load_local_text_file_rollback_claim_for_recovery_exact(
            ROLLBACK_OPERATION_ID,
            rollback_journal_reservation_fingerprint=ROLLBACK_RESERVATION,
        )
        == claim
    )
    with pytest.raises(KeyError):
        restarted.load_local_text_file_rollback_claim_for_recovery_exact(
            ROLLBACK_OPERATION_ID,
            rollback_journal_reservation_fingerprint="f" * 64,
        )

    unclaimed = _build_rollback_harness(tmp_path / "unclaimed")
    unclaimed.execution.clock.current = ROLLBACK_EXPIRED_AT
    with pytest.raises(ValueError, match="grant_window_invalid"):
        _claim(unclaimed)


def test_descriptor_removal_blocks_effect_but_not_historical_recovery(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    harness.execution.clock.current = ROLLBACK_CLAIMED_AT
    claim = _claim(harness)
    empty_registry = build_local_text_file_rollback_registry_snapshot(
        registry_id=SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY.registry_id,
        registry_version="1.1.0",
        descriptors=(),
    )
    harness.execution.clock.current = ROLLBACK_EFFECT_AT
    harness.governance.activate_local_text_file_rollback_registry(empty_registry)

    assert not harness.governance.verify_local_text_file_rollback_claim_for_effect_start_exact(
        claim,
        observed_root_config_fingerprint=harness.rollback_request.root_config_fingerprint,
        observed_expected_current_sha256=(harness.rollback_request.expected_current_sha256),
        observed_restored_content_sha256=(harness.rollback_request.restored_content_sha256),
    )
    assert harness.governance.verify_local_text_file_rollback_claim_for_recovery_exact(claim)


def test_rollback_receipt_binds_both_operations_and_is_append_only(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    harness.execution.clock.current = ROLLBACK_CLAIMED_AT
    claim = _claim(harness)
    receipt = _rollback_receipt(harness, claim)
    harness.execution.clock.current = ROLLBACK_RECORDED_AT

    assert harness.governance.record_local_text_rollback_receipt(receipt) == receipt
    assert harness.governance.record_local_text_rollback_receipt(receipt) == receipt
    context = harness.governance.load_local_text_file_rollback_grant_context(
        harness.rollback_grant.grant_id
    )
    assert context.rollback_receipt == receipt
    assert receipt.operation_id == ROLLBACK_OPERATION_ID
    assert receipt.mutation_operation_id == harness.mutation_receipt.operation_id
    with connect(harness.database_path) as connection:
        row = connection.execute(
            """
            SELECT rollback_operation_id, mutation_operation_id
            FROM local_text_rollback_receipts
            """
        ).fetchone()
        assert row == (ROLLBACK_OPERATION_ID, harness.mutation_receipt.operation_id)
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE local_text_rollback_receipts SET resource_ref = 'text:forged.txt'"
            )
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE local_text_file_rollback_requests SET expires_at = ?",
                (ROLLBACK_EXPIRED_AT,),
            )

    forged = replace(
        receipt,
        mutation_operation_id="operation://mb216/forged-mutation",
        rollback_receipt_fingerprint="0" * 64,
    )
    forged = replace(
        forged,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(forged),
    )
    with pytest.raises(ValueError, match="binding_mismatch"):
        harness.governance.record_local_text_rollback_receipt(forged)

    future = replace(
        receipt,
        rolled_back_at=ROLLBACK_EXPIRED_AT,
        rollback_receipt_fingerprint="0" * 64,
    )
    future = replace(
        future,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(future),
    )
    with pytest.raises(ValueError, match="future-dated"):
        harness.governance.record_local_text_rollback_receipt(future)

    backdated = replace(
        receipt,
        rolled_back_at=ROLLBACK_STAGING_AT,
        rollback_receipt_fingerprint="0" * 64,
    )
    backdated = replace(
        backdated,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(backdated),
    )
    with pytest.raises(ValueError, match="predates_claim"):
        harness.governance.record_local_text_rollback_receipt(backdated)


def test_rollback_receipt_exact_proof_fails_closed_and_survives_restart(
    tmp_path: Path,
) -> None:
    harness = _build_rollback_harness(tmp_path)
    harness.execution.clock.current = ROLLBACK_CLAIMED_AT
    claim = _claim(harness)
    receipt = _rollback_receipt(harness, claim)
    harness.execution.clock.current = ROLLBACK_RECORDED_AT
    harness.governance.record_local_text_rollback_receipt(receipt)

    assert (
        harness.governance.load_local_text_rollback_receipt_exact(
            receipt.operation_id,
            expected_rollback_receipt_fingerprint=(receipt.rollback_receipt_fingerprint),
        )
        == receipt
    )
    assert harness.governance.verify_local_text_rollback_receipt_exact(receipt)
    restarted = GovernanceService(
        harness.database_path,
        trusted_execution_clock=harness.execution.clock,
    )
    assert restarted.verify_local_text_rollback_receipt_exact(receipt)

    with pytest.raises(KeyError, match="unknown local text rollback receipt"):
        restarted.load_local_text_rollback_receipt_exact(
            "operation://mb217/wrong-rollback",
            expected_rollback_receipt_fingerprint=(receipt.rollback_receipt_fingerprint),
        )
    with pytest.raises(KeyError, match="unknown local text rollback receipt"):
        restarted.load_local_text_rollback_receipt_exact(
            receipt.operation_id,
            expected_rollback_receipt_fingerprint="f" * 64,
        )
    divergent = replace(receipt, resource_ref="text:artifacts/divergent.txt")
    assert not restarted.verify_local_text_rollback_receipt_exact(divergent)

    with connect(harness.database_path) as connection:
        connection.execute("DROP TRIGGER local_text_rollback_receipts_no_update")
        connection.execute(
            """
            UPDATE local_text_rollback_receipts
            SET resource_ref = 'text:artifacts/tampered.txt'
            WHERE rollback_operation_id = ?
            """,
            (receipt.operation_id,),
        )
    assert not restarted.verify_local_text_rollback_receipt_exact(receipt)
    with pytest.raises(ValueError, match="adapter stored resource_ref mismatch"):
        restarted.load_local_text_rollback_receipt_exact(
            receipt.operation_id,
            expected_rollback_receipt_fingerprint=(receipt.rollback_receipt_fingerprint),
        )
