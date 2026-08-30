from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from operational_service.adapters.local_text_governance import (
    LocalTextGovernanceAuthorityAdapter,
)
from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    LocalTextExecutionAuthorizationRequest,
    LocalTextExecutionGrantBinding,
    LocalTextStagingAuthorizationRequest,
)

from shared.contracts import (
    AdapterExecutionGrantClaimContract,
    LocalTextFileRollbackGrantClaimContract,
)

NOW = datetime(2026, 8, 30, 12, tzinfo=UTC)


def _hash(character: str) -> str:
    return character * 64


def _apply_evidence() -> tuple[SimpleNamespace, AdapterExecutionGrantClaimContract]:
    execution = SimpleNamespace(
        action_kind="execute_external_action",
        execution_policy_version="local-text-file-execution-policy/v1",
        execution_backend_version="local-text-transactional-writer/v1",
        operation="replace_text",
        resource_ref="text:alpha/note.txt",
        subject_ref="operator://one",
        preflight_fingerprint=_hash("a"),
        before_content_sha256=_hash("b"),
        desired_content_sha256=_hash("c"),
        root_config_fingerprint=_hash("d"),
        execution_request_fingerprint=_hash("e"),
    )
    grant = SimpleNamespace(
        grant_id="grant://apply",
        grant_fingerprint=_hash("f"),
        action_fingerprint=_hash("1"),
        intent_fingerprint=_hash("2"),
    )
    context = SimpleNamespace(execution_request=execution, grant=grant)
    claim = AdapterExecutionGrantClaimContract(
        claim_id="claim://apply",
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        operation_id="operation://apply",
        journal_reservation_fingerprint=_hash("3"),
        subject_ref=execution.subject_ref,
        execution_request=execution,
        intent_id="intent://apply",
        intent_fingerprint=grant.intent_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        claimed_at="2026-08-30T12:00:00Z",
        expires_at="2026-08-30T12:02:00Z",
        claim_fingerprint=_hash("4"),
        confirmation_receipt_id="confirmation://apply",
        confirmation_claim_id="confirmation-claim://apply",
        confirmation_claim_fingerprint=_hash("5"),
    )
    return context, claim


def _rollback_evidence() -> tuple[SimpleNamespace, LocalTextFileRollbackGrantClaimContract]:
    rollback = SimpleNamespace(
        action_kind="execute_external_action",
        source_execution_policy_version="local-text-file-execution-policy/v1",
        source_execution_backend_version="local-text-transactional-writer/v1",
        transaction_backend_version="posix-openat-1.0.0",
        rollback_policy_version="local-text-file-rollback-policy/v1",
        rollback_backend_version="local-text-transactional-writer/v1",
        operation="rollback_text",
        rollback_operation_id="operation://rollback",
        resource_ref="text:alpha/note.txt",
        subject_ref="operator://one",
        source_preflight_fingerprint=_hash("a"),
        expected_current_sha256=_hash("c"),
        restored_content_sha256=_hash("b"),
        root_config_fingerprint=_hash("d"),
        mutation_receipt_fingerprint=_hash("6"),
        rollback_request_fingerprint=_hash("7"),
        transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    )
    grant = SimpleNamespace(
        grant_id="grant://rollback",
        grant_fingerprint=_hash("8"),
        action_fingerprint=_hash("9"),
        intent_fingerprint=_hash("0"),
    )
    mutation_receipt = SimpleNamespace(receipt_fingerprint=rollback.mutation_receipt_fingerprint)
    context = SimpleNamespace(
        rollback_request=rollback,
        mutation_receipt=mutation_receipt,
        grant=grant,
    )
    claim = LocalTextFileRollbackGrantClaimContract(
        claim_id="claim://rollback",
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        rollback_operation_id=rollback.rollback_operation_id,
        rollback_journal_reservation_fingerprint=_hash("a"),
        subject_ref=rollback.subject_ref,
        rollback_request=rollback,
        intent_id="intent://rollback",
        intent_fingerprint=grant.intent_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        claimed_at="2026-08-30T12:03:00Z",
        expires_at="2026-08-30T12:05:00Z",
        claim_fingerprint=_hash("b"),
        confirmation_receipt_id="confirmation://rollback",
        confirmation_claim_id="confirmation-claim://rollback",
        confirmation_claim_fingerprint=_hash("c"),
    )
    return context, claim


class _Governance:
    def __init__(self) -> None:
        self.apply_context, self.apply_claim = _apply_evidence()
        self.rollback_context, self.rollback_claim = _rollback_evidence()
        self.apply_stage_calls = 0
        self.rollback_stage_calls = 0
        self.receipts: list[object] = []

    def load_adapter_execution_grant_context(self, _grant_id: str) -> SimpleNamespace:
        return self.apply_context

    def verify_adapter_execution_grant_for_staging_exact(
        self, _grant_id: str, **_kwargs: object
    ) -> bool:
        self.apply_stage_calls += 1
        return True

    def claim_adapter_execution_grant_exact(
        self, _grant_id: str, **_kwargs: object
    ) -> AdapterExecutionGrantClaimContract:
        return self.apply_claim

    def load_adapter_execution_claim_for_recovery_exact(
        self, operation_id: str, **_kwargs: object
    ) -> AdapterExecutionGrantClaimContract:
        if operation_id != str(self.apply_claim.operation_id):
            raise KeyError(operation_id)
        return self.apply_claim

    def verify_adapter_execution_claim_for_effect_start_exact(
        self, _claim: object, **_kwargs: object
    ) -> bool:
        return True

    def verify_adapter_execution_claim_for_recovery_exact(self, _claim: object) -> bool:
        return True

    def load_local_text_file_rollback_grant_context(self, _grant_id: str) -> SimpleNamespace:
        return self.rollback_context

    def verify_local_text_file_rollback_grant_for_staging_exact(
        self, _grant_id: str, **_kwargs: object
    ) -> bool:
        self.rollback_stage_calls += 1
        return True

    def claim_local_text_file_rollback_grant_exact(
        self, _grant_id: str, **_kwargs: object
    ) -> LocalTextFileRollbackGrantClaimContract:
        return self.rollback_claim

    def load_local_text_file_rollback_claim_for_recovery_exact(
        self, operation_id: str, **_kwargs: object
    ) -> LocalTextFileRollbackGrantClaimContract:
        if operation_id != str(self.rollback_claim.rollback_operation_id):
            raise KeyError(operation_id)
        return self.rollback_claim

    def verify_local_text_file_rollback_claim_for_effect_start_exact(
        self, _claim: object, **_kwargs: object
    ) -> bool:
        return True

    def verify_local_text_file_rollback_claim_for_recovery_exact(self, _claim: object) -> bool:
        return True

    def record_local_text_mutation_receipt(self, receipt: object) -> object:
        self.receipts.append(receipt)
        return receipt

    def record_local_text_rollback_receipt(self, receipt: object) -> object:
        self.receipts.append(receipt)
        return receipt


def _apply_binding(governance: _Governance) -> LocalTextExecutionGrantBinding:
    grant = governance.apply_context.grant
    request = governance.apply_context.execution_request
    return LocalTextExecutionGrantBinding(
        execution_grant_id=grant.grant_id,
        execution_grant_fingerprint=grant.grant_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        execution_request_fingerprint=request.execution_request_fingerprint,
        intent_fingerprint=grant.intent_fingerprint,
        confirmation_receipt_id="confirmation://apply",
    )


def _apply_staging(governance: _Governance) -> LocalTextStagingAuthorizationRequest:
    request = governance.apply_context.execution_request
    return LocalTextStagingAuthorizationRequest(
        purpose="execute",
        operation_id="operation://apply",
        operation=request.operation,
        resource_ref=request.resource_ref,
        subject_ref=request.subject_ref,
        preflight_fingerprint=request.preflight_fingerprint,
        before_content_sha256=request.before_content_sha256,
        desired_content_sha256=request.desired_content_sha256,
        root_config_fingerprint=request.root_config_fingerprint,
        execution_binding=_apply_binding(governance),
    )


def _authority_from_staging(
    staging: LocalTextStagingAuthorizationRequest,
    *,
    reservation: str,
) -> LocalTextExecutionAuthorizationRequest:
    binding = staging.execution_binding
    return LocalTextExecutionAuthorizationRequest(
        purpose=staging.purpose,
        operation_id=staging.operation_id,
        action_kind="execute_external_action",
        operation=staging.operation,
        resource_ref=staging.resource_ref,
        subject_ref=staging.subject_ref,
        preflight_fingerprint=staging.preflight_fingerprint,
        before_content_sha256=staging.before_content_sha256,
        desired_content_sha256=staging.desired_content_sha256,
        root_config_fingerprint=staging.root_config_fingerprint,
        transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
        execution_grant_id=binding.execution_grant_id,
        execution_grant_fingerprint=binding.execution_grant_fingerprint,
        action_fingerprint=binding.action_fingerprint,
        execution_request_fingerprint=binding.execution_request_fingerprint,
        intent_fingerprint=binding.intent_fingerprint,
        confirmation_receipt_id=binding.confirmation_receipt_id,
        journal_reservation_fingerprint=reservation,
        mutation_receipt_fingerprint=staging.mutation_receipt_fingerprint,
    )


def test_apply_binding_is_checked_before_governance_and_survives_recovery() -> None:
    governance = _Governance()
    adapter = LocalTextGovernanceAuthorityAdapter(governance)
    staging = _apply_staging(governance)

    assert adapter.verify_staging(staging, NOW)
    assert governance.apply_stage_calls == 1

    with pytest.raises(ValueError, match="apply_staging_binding_mismatch"):
        adapter.verify_staging(replace(staging, resource_ref="text:beta/other.txt"), NOW)
    assert governance.apply_stage_calls == 1

    governance.apply_context.execution_request.execution_backend_version = "unsupported/v2"
    with pytest.raises(ValueError, match="apply_staging_binding_mismatch"):
        adapter.verify_staging(staging, NOW)
    governance.apply_context.execution_request.execution_backend_version = (
        "local-text-transactional-writer/v1"
    )
    assert governance.apply_stage_calls == 1

    authority = _authority_from_staging(
        staging,
        reservation=governance.apply_claim.journal_reservation_fingerprint,
    )
    lease = adapter.claim(authority, NOW)
    assert lease.context.operation_id == authority.operation_id
    assert adapter.verify_effect_start(lease.context, NOW)
    assert adapter.lookup_historical(authority, NOW) == lease.context
    assert adapter.verify_historical(lease.context, NOW)


def test_rollback_uses_dedicated_request_and_mutation_receipt_bindings() -> None:
    governance = _Governance()
    adapter = LocalTextGovernanceAuthorityAdapter(governance)
    rollback = governance.rollback_context.rollback_request
    grant = governance.rollback_context.grant
    staging = LocalTextStagingAuthorizationRequest(
        purpose="rollback",
        operation_id=rollback.rollback_operation_id,
        operation=rollback.operation,
        resource_ref=rollback.resource_ref,
        subject_ref=rollback.subject_ref,
        preflight_fingerprint=rollback.source_preflight_fingerprint,
        before_content_sha256=rollback.expected_current_sha256,
        desired_content_sha256=rollback.restored_content_sha256,
        root_config_fingerprint=rollback.root_config_fingerprint,
        execution_binding=LocalTextExecutionGrantBinding(
            execution_grant_id=grant.grant_id,
            execution_grant_fingerprint=grant.grant_fingerprint,
            action_fingerprint=grant.action_fingerprint,
            execution_request_fingerprint=rollback.rollback_request_fingerprint,
            intent_fingerprint=grant.intent_fingerprint,
            confirmation_receipt_id="confirmation://rollback",
        ),
        mutation_receipt_fingerprint=rollback.mutation_receipt_fingerprint,
    )

    assert adapter.verify_staging(staging, NOW)
    assert governance.rollback_stage_calls == 1
    with pytest.raises(ValueError, match="rollback_staging_binding_mismatch"):
        adapter.verify_staging(replace(staging, mutation_receipt_fingerprint=_hash("f")), NOW)
    assert governance.rollback_stage_calls == 1

    authority = _authority_from_staging(
        staging,
        reservation=(governance.rollback_claim.rollback_journal_reservation_fingerprint),
    )
    lease = adapter.claim(authority, NOW)
    assert lease.context.mutation_receipt_fingerprint == rollback.mutation_receipt_fingerprint
    assert adapter.verify_effect_start(lease.context, NOW)
    assert adapter.lookup_historical(authority, NOW) == lease.context
    assert adapter.verify_historical(lease.context, NOW)


def test_bridge_rejects_naive_engine_time_and_unknown_history() -> None:
    governance = _Governance()
    adapter = LocalTextGovernanceAuthorityAdapter(governance)
    staging = _apply_staging(governance)

    with pytest.raises(ValueError, match="verified_at_invalid"):
        adapter.verify_staging(staging, datetime(2026, 8, 30, 12))

    authority = replace(
        _authority_from_staging(staging, reservation=_hash("3")),
        operation_id="operation://missing",
    )
    assert adapter.lookup_historical(authority, NOW) is None
