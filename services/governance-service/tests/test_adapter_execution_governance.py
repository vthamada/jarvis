from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from sqlite3 import IntegrityError, connect

import pytest
from governance_service.service import GovernanceService
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.service import OperationalService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_execution_permissions import (
    LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR,
    SEEDED_ADAPTER_EXECUTION_REGISTRY,
    build_adapter_execution_registry_snapshot,
)
from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AdapterExecutionRequestContract,
    AdapterGrantContract,
    AutonomyActionPolicyDecisionContract,
    HumanConfirmationReceiptContract,
    LocalTextFilePreflightContract,
    LocalTextFilePreflightRequestContract,
)
from shared.types import RiskLevel

PREPARE_ISSUED_AT = "2026-08-30T12:00:00Z"
PREFLIGHT_AT = "2026-08-30T12:01:00Z"
ATTESTED_AT = "2026-08-30T12:01:10Z"
EXECUTION_ISSUED_AT = "2026-08-30T12:01:20Z"
CONFIRMED_AT = "2026-08-30T12:01:30Z"
STAGING_AT = "2026-08-30T12:01:40Z"
CLAIMED_AT = "2026-08-30T12:01:50Z"
EFFECT_AT = "2026-08-30T12:01:55Z"
EXECUTION_EXPIRES_AT = "2026-08-30T12:02:30Z"
PREFLIGHT_EXPIRES_AT = "2026-08-30T12:03:00Z"
PREPARE_GRANT_EXPIRES_AT = "2026-08-30T12:05:00Z"
PREPARE_INTENT_EXPIRES_AT = "2026-08-30T12:10:00Z"
EXPIRED_AT = "2026-08-30T12:02:31Z"
PREFLIGHT_EXPIRED_AT = "2026-08-30T12:03:01Z"


@dataclass
class _Clock:
    current: str = PREPARE_ISSUED_AT

    def __call__(self) -> str:
        return self.current


@dataclass(frozen=True)
class _ExecutionHarness:
    database_path: Path
    governance: GovernanceService
    clock: _Clock
    prepare_intent: ActionIntentContract
    prepare_grant: AdapterGrantContract
    preflight: LocalTextFilePreflightContract
    execution_request: AdapterExecutionRequestContract
    execution_intent: ActionIntentContract
    execution_decision: AutonomyActionPolicyDecisionContract
    execution_grant: AdapterExecutionGrantContract
    confirmation_receipt: HumanConfirmationReceiptContract


def _decision(action_kind: str) -> AutonomyActionPolicyDecisionContract:
    policy = AUTONOMY_LEVEL_POLICIES["supervised_external_action"]
    confirmation_required = action_kind == "execute_external_action"
    return evaluate_autonomy_action(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="supervised_external_action",
        effective_autonomy_level="supervised_external_action",
        autonomy_ladder_status="within_limit",
        action_kind=action_kind,
        selected_capability_mode="core_with_supervised_external_operation",
        max_capability_mode="core_with_supervised_external_operation",
        allowed_runtime_actions=policy["allowed_runtime_actions"],
        blocked_runtime_actions=policy["blocked_runtime_actions"],
        human_confirmation_required=confirmation_required,
        human_confirmation_mode=(
            "explicit_confirmation_required" if confirmation_required else "not_required"
        ),
        confirmation_evidence_state="absent",
    )


def _prepare_action_request() -> AdapterActionRequestContract:
    return AdapterActionRequestContract(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        operation="create_text",
        resource_scope="configured_text_root",
        resource_ref="text:notes/mb216.txt",
    )


def _execution_intent(
    request: AdapterExecutionRequestContract,
    *,
    suffix: str = "one",
) -> ActionIntentContract:
    return build_action_intent(
        intent_id=f"adapter-execution-intent://mb216/{suffix}",
        origin_request_id=f"request://mb216/{suffix}",
        session_id="session://mb216/operator",
        mission_id=f"mission://mb216/{suffix}",
        operator_identity_ref=request.subject_ref,
        handler_id=LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.executor_ref,
        handler_version=LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.adapter_version,
        operation=request.operation,
        target_ref=request.resource_ref,
        content_digest=request.desired_content_sha256,
        precondition_digest=request.execution_request_fingerprint,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=f"adapterExecutionIntentNonce{suffix}123456",
        issued_at=ATTESTED_AT,
        expires_at=EXECUTION_EXPIRES_AT,
        now=ATTESTED_AT,
    )


def _build_harness(tmp_path: Path) -> _ExecutionHarness:
    database_path = tmp_path / "governance.db"
    text_root = tmp_path / "configured-text-root"
    text_root.mkdir(parents=True)
    clock = _Clock()
    governance = GovernanceService(
        database_path,
        trusted_execution_clock=clock,
    )
    governance.activate_adapter_registry(
        SEEDED_ADAPTER_REGISTRY,
        activated_at=PREPARE_ISSUED_AT,
    )
    governance.activate_adapter_execution_registry(
        SEEDED_ADAPTER_EXECUTION_REGISTRY,
        activated_at=PREPARE_ISSUED_AT,
    )
    operational = OperationalService(
        artifact_dir=str(tmp_path / "artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_roots={"notes": text_root},
    )
    action_request = _prepare_action_request()
    desired_text = "MB-216 execution authority is exact.\n"
    root_config_fingerprint = operational.local_text_file_root_config_fingerprint()
    prepare_intent = build_action_intent(
        intent_id="adapter-intent://mb216/prepare",
        origin_request_id="request://mb216/prepare",
        session_id="session://mb216/operator",
        mission_id="mission://mb216/prepare",
        operator_identity_ref="operator://local/vtham",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation=action_request.operation,
        target_ref=action_request.resource_ref,
        content_digest=sha256(desired_text.encode("utf-8")).hexdigest(),
        precondition_digest=root_config_fingerprint,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce="adapterPrepareIntentNonceMb216123456",
        issued_at=PREPARE_ISSUED_AT,
        expires_at=PREPARE_INTENT_EXPIRES_AT,
        now=PREPARE_ISSUED_AT,
    )
    registry, descriptor = governance.resolve_active_adapter_descriptor(action_request)
    prepare_grant = governance.issue_adapter_grant(
        prepare_intent,
        action_request,
        _decision("prepare_external_action"),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=PREPARE_ISSUED_AT,
        expires_at=PREPARE_GRANT_EXPIRES_AT,
    )
    preflight_request = LocalTextFilePreflightRequestContract(
        grant_id=prepare_grant.grant_id,
        grant_fingerprint=prepare_grant.grant_fingerprint,
        action_fingerprint=prepare_intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(prepare_intent),
        descriptor_fingerprint=prepare_grant.descriptor_fingerprint,
        registry_fingerprint=prepare_grant.registry_fingerprint,
        subject_ref=prepare_intent.operator_identity_ref,
        adapter_request=action_request,
        desired_text=desired_text,
        expected_root_config_fingerprint=root_config_fingerprint,
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at=PREFLIGHT_AT,
        expires_at=PREFLIGHT_EXPIRES_AT,
        authorization_expires_at=prepare_grant.expires_at,
    )
    preflight = operational.preflight_local_text_file(
        preflight_request,
        now=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
    )
    clock.current = ATTESTED_AT
    _attestation, execution_request = governance.attest_local_text_file_preflight(preflight)
    execution_intent = _execution_intent(execution_request)
    execution_decision = _decision("execute_external_action")
    clock.current = EXECUTION_ISSUED_AT
    execution_registry, execution_descriptor = (
        governance.resolve_active_adapter_execution_descriptor(execution_request)
    )
    execution_grant = governance.issue_adapter_execution_grant(
        execution_intent,
        execution_request,
        execution_decision,
        expected_registry_fingerprint=execution_registry.registry_fingerprint,
        expected_descriptor_fingerprint=execution_descriptor.descriptor_fingerprint,
    )
    challenge = governance.issue_action_confirmation_challenge(execution_intent)
    confirmation_receipt = governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=execution_intent.operator_identity_ref,
        expected_action_fingerprint=execution_intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    return _ExecutionHarness(
        database_path=database_path,
        governance=governance,
        clock=clock,
        prepare_intent=prepare_intent,
        prepare_grant=prepare_grant,
        preflight=preflight,
        execution_request=execution_request,
        execution_intent=execution_intent,
        execution_decision=execution_decision,
        execution_grant=execution_grant,
        confirmation_receipt=confirmation_receipt,
    )


def _stage(harness: _ExecutionHarness, **changes: str) -> bool:
    values = {
        "subject_ref": harness.execution_intent.operator_identity_ref,
        "expected_grant_fingerprint": harness.execution_grant.grant_fingerprint,
        "expected_action_fingerprint": harness.execution_intent.action_fingerprint,
        "expected_execution_request_fingerprint": (
            harness.execution_request.execution_request_fingerprint
        ),
        "intent_fingerprint": action_intent_fingerprint(harness.execution_intent),
        "confirmation_receipt_id": harness.confirmation_receipt.receipt_id,
    }
    values.update(changes)
    return harness.governance.verify_adapter_execution_grant_for_staging_exact(
        harness.execution_grant.grant_id,
        **values,
    )


def _claim(
    harness: _ExecutionHarness,
    *,
    operation_id: str = "operation://mb216/execute-one",
    journal_reservation_fingerprint: str = "7" * 64,
) -> AdapterExecutionGrantClaimContract:
    return harness.governance.claim_adapter_execution_grant_exact(
        harness.execution_grant.grant_id,
        operation_id=operation_id,
        journal_reservation_fingerprint=journal_reservation_fingerprint,
        subject_ref=harness.execution_intent.operator_identity_ref,
        expected_grant_fingerprint=harness.execution_grant.grant_fingerprint,
        expected_action_fingerprint=harness.execution_intent.action_fingerprint,
        expected_execution_request_fingerprint=(
            harness.execution_request.execution_request_fingerprint
        ),
        intent_fingerprint=action_intent_fingerprint(harness.execution_intent),
        confirmation_receipt_id=harness.confirmation_receipt.receipt_id,
    )


def _count(database_path: Path, table: str) -> int:
    with connect(database_path) as connection:
        return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def test_attestation_and_grant_are_exact_content_free_and_unique(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    context = harness.governance.load_adapter_execution_grant_context(
        harness.execution_grant.grant_id
    )

    assert context.execution_request == harness.execution_request
    assert context.preflight_attestation.preflight_fingerprint == (
        harness.preflight.preflight_fingerprint
    )
    assert context.source_prepare_grant == harness.prepare_grant
    assert context.intent.content_digest == harness.execution_request.desired_content_sha256
    assert context.intent.precondition_digest == (
        harness.execution_request.execution_request_fingerprint
    )
    assert context.grant.confirmation_required is True
    assert context.grant.execution_allowed is False
    assert context.execution_request.preflight_attestation_id == (
        context.preflight_attestation.attestation_id
    )
    with connect(harness.database_path) as connection:
        attestation_payload = connection.execute(
            "SELECT payload FROM local_text_file_preflight_attestations"
        ).fetchone()[0]
        assert harness.preflight.unified_diff not in attestation_payload
        assert "desired_text" not in attestation_payload
        assert connection.execute(
            "SELECT COUNT(*) FROM local_text_file_preflight_attestations"
        ).fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM adapter_execution_grants").fetchone() == (
            1,
        )

    harness.clock.current = STAGING_AT
    assert (
        harness.governance.issue_adapter_execution_grant(
            harness.execution_intent,
            harness.execution_request,
            harness.execution_decision,
            expected_registry_fingerprint=context.registry.registry_fingerprint,
            expected_descriptor_fingerprint=context.descriptor.descriptor_fingerprint,
        )
        == harness.execution_grant
    )
    attestation, request = harness.governance.attest_local_text_file_preflight(harness.preflight)
    assert attestation == context.preflight_attestation
    assert request == harness.execution_request

    other_intent = _execution_intent(harness.execution_request, suffix="duplicate")
    with pytest.raises(ValueError, match="already has different authority"):
        harness.governance.issue_adapter_execution_grant(
            other_intent,
            harness.execution_request,
            harness.execution_decision,
            expected_registry_fingerprint=context.registry.registry_fingerprint,
            expected_descriptor_fingerprint=context.descriptor.descriptor_fingerprint,
            expires_at=EXECUTION_EXPIRES_AT,
        )


def test_staging_requires_exact_execution_confirmation_without_writes(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    challenge = harness.governance.issue_action_confirmation_challenge(harness.prepare_intent)
    prepare_receipt = harness.governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=harness.prepare_intent.operator_identity_ref,
        expected_action_fingerprint=harness.prepare_intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    counts_before = {
        table: _count(harness.database_path, table)
        for table in (
            "action_confirmation_claims",
            "adapter_execution_grant_claims",
            "adapter_execution_grants",
            "local_text_file_preflight_attestations",
        )
    }
    harness.clock.current = STAGING_AT

    assert _stage(harness) is True
    assert _stage(harness, confirmation_receipt_id=prepare_receipt.receipt_id) is False
    assert _stage(harness, expected_grant_fingerprint="1" * 64) is False
    assert _stage(harness, expected_action_fingerprint="2" * 64) is False
    assert _stage(harness, expected_execution_request_fingerprint="3" * 64) is False
    assert {table: _count(harness.database_path, table) for table in counts_before} == counts_before

    with pytest.raises(KeyError, match="unknown adapter execution grant"):
        harness.governance.claim_adapter_execution_grant_exact(
            harness.prepare_grant.grant_id,
            operation_id="operation://mb216/forged-prepare",
            journal_reservation_fingerprint="4" * 64,
            subject_ref=harness.prepare_intent.operator_identity_ref,
            expected_grant_fingerprint=harness.prepare_grant.grant_fingerprint,
            expected_action_fingerprint=harness.prepare_intent.action_fingerprint,
            expected_execution_request_fingerprint="5" * 64,
            intent_fingerprint=action_intent_fingerprint(harness.prepare_intent),
            confirmation_receipt_id=prepare_receipt.receipt_id,
        )


def test_joint_claim_is_atomic_idempotent_and_replay_safe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    harness = _build_harness(tmp_path)
    harness.clock.current = CLAIMED_AT
    repository = harness.governance.action_confirmation_repository

    def fail_after_confirmation(*args: object, **kwargs: object) -> None:
        raise RuntimeError("injected crash after confirmation claim")

    with monkeypatch.context() as scoped:
        scoped.setattr(repository, "_insert_adapter_execution_claim", fail_after_confirmation)
        with pytest.raises(RuntimeError, match="injected crash"):
            _claim(harness)
    assert _count(harness.database_path, "action_confirmation_claims") == 0
    assert _count(harness.database_path, "adapter_execution_grant_claims") == 0

    claim = _claim(harness)
    assert _claim(harness) == claim
    assert _count(harness.database_path, "action_confirmation_claims") == 1
    assert _count(harness.database_path, "adapter_execution_grant_claims") == 1
    with pytest.raises(ValueError, match="already claimed"):
        _claim(harness, operation_id="operation://mb216/replay")
    with pytest.raises(ValueError, match="already claimed"):
        _claim(harness, journal_reservation_fingerprint="8" * 64)


def test_concurrent_exact_claim_has_one_persisted_joint_claim(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    harness.clock.current = CLAIMED_AT
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: _claim(harness), range(8)))

    assert len({item.claim_id for item in results}) == 1
    assert _count(harness.database_path, "adapter_execution_grant_claims") == 1
    assert _count(harness.database_path, "action_confirmation_claims") == 1


def test_effect_start_rechecks_physical_bindings_and_active_descriptor(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    harness.clock.current = CLAIMED_AT
    claim = _claim(harness)
    harness.clock.current = EFFECT_AT
    verify = harness.governance.verify_adapter_execution_claim_for_effect_start_exact

    assert verify(
        claim,
        observed_root_config_fingerprint=harness.execution_request.root_config_fingerprint,
        observed_precondition_content_sha256=(
            harness.execution_request.precondition_content_sha256
        ),
        observed_desired_content_sha256=harness.execution_request.desired_content_sha256,
    )
    assert not verify(
        claim,
        observed_root_config_fingerprint="1" * 64,
        observed_precondition_content_sha256=(
            harness.execution_request.precondition_content_sha256
        ),
        observed_desired_content_sha256=harness.execution_request.desired_content_sha256,
    )
    empty_registry = build_adapter_execution_registry_snapshot(
        registry_id=SEEDED_ADAPTER_EXECUTION_REGISTRY.registry_id,
        registry_version="1.1.0",
        descriptors=(),
    )
    harness.governance.activate_adapter_execution_registry(
        empty_registry,
        activated_at=EFFECT_AT,
    )
    assert not verify(
        claim,
        observed_root_config_fingerprint=harness.execution_request.root_config_fingerprint,
        observed_precondition_content_sha256=(
            harness.execution_request.precondition_content_sha256
        ),
        observed_desired_content_sha256=harness.execution_request.desired_content_sha256,
    )
    assert harness.governance.verify_adapter_execution_claim_for_recovery_exact(claim)


def test_expiry_blocks_new_effect_but_historical_recovery_remains_exact(
    tmp_path: Path,
) -> None:
    harness = _build_harness(tmp_path)
    harness.clock.current = CLAIMED_AT
    claim = _claim(harness)
    harness.clock.current = EXPIRED_AT

    assert _stage(harness) is False
    assert not harness.governance.verify_adapter_execution_claim_for_effect_start_exact(
        claim,
        observed_root_config_fingerprint=harness.execution_request.root_config_fingerprint,
        observed_precondition_content_sha256=(
            harness.execution_request.precondition_content_sha256
        ),
        observed_desired_content_sha256=harness.execution_request.desired_content_sha256,
    )
    assert harness.governance.verify_adapter_execution_claim_for_recovery_exact(claim)
    assert (
        harness.governance.load_adapter_execution_claim_for_recovery_exact(str(claim.operation_id))
        == claim
    )
    assert (
        harness.governance.load_adapter_execution_claim_for_recovery_exact(
            str(claim.operation_id),
            journal_reservation_fingerprint=claim.journal_reservation_fingerprint,
        )
        == claim
    )
    with pytest.raises(KeyError):
        harness.governance.load_adapter_execution_claim_for_recovery_exact(
            str(claim.operation_id),
            journal_reservation_fingerprint="9" * 64,
        )

    unclaimed = _build_harness(tmp_path / "unclaimed")
    unclaimed.clock.current = EXPIRED_AT
    repository = unclaimed.governance.action_confirmation_repository
    assert not repository.verify_adapter_execution_grant_for_staging_exact(
        unclaimed.execution_grant.grant_id,
        subject_ref=unclaimed.execution_intent.operator_identity_ref,
        expected_grant_fingerprint=unclaimed.execution_grant.grant_fingerprint,
        expected_action_fingerprint=unclaimed.execution_intent.action_fingerprint,
        expected_execution_request_fingerprint=(
            unclaimed.execution_request.execution_request_fingerprint
        ),
        intent_fingerprint=action_intent_fingerprint(unclaimed.execution_intent),
        confirmation_receipt_id=unclaimed.confirmation_receipt.receipt_id,
        verified_at=STAGING_AT,
    )
    with pytest.raises(ValueError, match="expired"):
        repository.claim_adapter_execution_grant_exact(
            unclaimed.execution_grant.grant_id,
            operation_id="operation://mb216/backdated",
            journal_reservation_fingerprint="6" * 64,
            subject_ref=unclaimed.execution_intent.operator_identity_ref,
            expected_grant_fingerprint=unclaimed.execution_grant.grant_fingerprint,
            expected_action_fingerprint=unclaimed.execution_intent.action_fingerprint,
            expected_execution_request_fingerprint=(
                unclaimed.execution_request.execution_request_fingerprint
            ),
            intent_fingerprint=action_intent_fingerprint(unclaimed.execution_intent),
            confirmation_receipt_id=unclaimed.confirmation_receipt.receipt_id,
            claimed_at=CLAIMED_AT,
        )


def test_tamper_and_backdated_paths_fail_closed(tmp_path: Path) -> None:
    harness = _build_harness(tmp_path)
    context = harness.governance.load_adapter_execution_grant_context(
        harness.execution_grant.grant_id
    )
    forged_request = replace(
        harness.execution_request,
        rollback_fingerprint="a" * 64,
    )
    forged_intent = _execution_intent(forged_request, suffix="forged")
    harness.clock.current = EXECUTION_ISSUED_AT
    with pytest.raises(ValueError):
        harness.governance.issue_adapter_execution_grant(
            forged_intent,
            forged_request,
            harness.execution_decision,
            expected_registry_fingerprint=context.registry.registry_fingerprint,
            expected_descriptor_fingerprint=context.descriptor.descriptor_fingerprint,
            expires_at=EXECUTION_EXPIRES_AT,
        )

    with connect(harness.database_path) as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE adapter_execution_grants SET subject_ref = 'operator://forged'"
            )
        connection.execute("DROP TRIGGER adapter_execution_grants_no_update")
        connection.execute(
            "UPDATE adapter_execution_grants SET payload = '{}' WHERE grant_id = ?",
            (harness.execution_grant.grant_id,),
        )
        connection.commit()
    harness.clock.current = STAGING_AT
    assert _stage(harness) is False

    late_clock = _Clock(PREFLIGHT_EXPIRED_AT)
    late_service = GovernanceService(
        harness.database_path,
        trusted_execution_clock=late_clock,
    )
    with pytest.raises(ValueError, match="inactive"):
        late_service.attest_local_text_file_preflight(harness.preflight)
    with pytest.raises(ValueError, match="inactive"):
        late_service.action_confirmation_repository.record_local_text_file_preflight_attestation(
            harness.preflight,
            attested_at=ATTESTED_AT,
        )


def test_rollback_operation_is_not_authorized_by_execution_descriptor() -> None:
    assert "rollback_text" not in LOCAL_TEXT_FILE_EXECUTION_DESCRIPTOR.allowed_operations
