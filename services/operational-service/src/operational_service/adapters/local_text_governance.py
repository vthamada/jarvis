"""Exact bridge between Governance evidence and the local-text transaction engine.

The adapter deliberately depends on a structural port instead of importing the
Governance implementation.  It projects persisted shared contracts into the
engine's local authorization context only after checking every physical binding
that the engine can observe.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hmac import compare_digest
from re import fullmatch
from typing import Protocol

from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    LocalTextExecutionAuthorizationContext,
    LocalTextExecutionAuthorizationRequest,
    LocalTextStagingAuthorizationRequest,
    build_execution_authority_fingerprint,
)
from shared.adapter_execution_permissions import (
    LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION,
    LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION,
)
from shared.contracts import (
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AdapterExecutionRequestContract,
    LocalTextFileRollbackGrantClaimContract,
    LocalTextFileRollbackGrantContract,
    LocalTextFileRollbackRequestContract,
    LocalTextMutationReceipt,
    LocalTextRollbackReceipt,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION,
    LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION as SHARED_TRANSACTION_BACKEND_VERSION,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION as SHARED_TRANSACTION_POLICY_VERSION,
)

_SHA256 = r"[0-9a-f]{64}"


class AdapterExecutionGrantContextPort(Protocol):
    execution_request: AdapterExecutionRequestContract
    grant: AdapterExecutionGrantContract


class LocalTextRollbackGrantContextPort(Protocol):
    rollback_request: LocalTextFileRollbackRequestContract
    mutation_receipt: LocalTextMutationReceipt
    grant: LocalTextFileRollbackGrantContract


class LocalTextExecutionGovernancePort(Protocol):
    """Governance surface required by the physical transaction boundary."""

    def load_adapter_execution_grant_context(
        self, grant_id: str
    ) -> AdapterExecutionGrantContextPort: ...

    def verify_adapter_execution_grant_for_staging_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> bool: ...

    def claim_adapter_execution_grant_exact(
        self,
        grant_id: str,
        *,
        operation_id: str,
        journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_execution_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> AdapterExecutionGrantClaimContract: ...

    def verify_adapter_execution_claim_for_effect_start_exact(
        self,
        claim: AdapterExecutionGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_precondition_content_sha256: str,
        observed_desired_content_sha256: str,
    ) -> bool: ...

    def verify_adapter_execution_claim_for_recovery_exact(
        self, claim: AdapterExecutionGrantClaimContract
    ) -> bool: ...

    def load_adapter_execution_claim_for_recovery_exact(
        self,
        operation_id: str,
        *,
        journal_reservation_fingerprint: str | None = None,
    ) -> AdapterExecutionGrantClaimContract: ...

    def load_local_text_file_rollback_grant_context(
        self, grant_id: str
    ) -> LocalTextRollbackGrantContextPort: ...

    def verify_local_text_file_rollback_grant_for_staging_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> bool: ...

    def claim_local_text_file_rollback_grant_exact(
        self,
        grant_id: str,
        *,
        rollback_operation_id: str,
        rollback_journal_reservation_fingerprint: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_rollback_request_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str,
    ) -> LocalTextFileRollbackGrantClaimContract: ...

    def verify_local_text_file_rollback_claim_for_effect_start_exact(
        self,
        claim: LocalTextFileRollbackGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_expected_current_sha256: str,
        observed_restored_content_sha256: str,
    ) -> bool: ...

    def verify_local_text_file_rollback_claim_for_recovery_exact(
        self, claim: LocalTextFileRollbackGrantClaimContract
    ) -> bool: ...

    def load_local_text_file_rollback_claim_for_recovery_exact(
        self,
        rollback_operation_id: str,
        *,
        rollback_journal_reservation_fingerprint: str | None = None,
    ) -> LocalTextFileRollbackGrantClaimContract: ...

    def record_local_text_mutation_receipt(
        self, receipt: LocalTextMutationReceipt
    ) -> LocalTextMutationReceipt: ...

    def record_local_text_rollback_receipt(
        self, receipt: LocalTextRollbackReceipt
    ) -> LocalTextRollbackReceipt: ...


@dataclass
class _PersistedClaimLease:
    """Local lifecycle marker for a claim already persisted by Governance."""

    _context: LocalTextExecutionAuthorizationContext
    _completed_fingerprint: str | None = None
    _interruption_reason: str | None = None

    @property
    def context(self) -> LocalTextExecutionAuthorizationContext:
        return self._context

    def complete(self, receipt_fingerprint: str) -> None:
        if fullmatch(_SHA256, receipt_fingerprint) is None:
            raise ValueError("local_text_governance_receipt_fingerprint_invalid")
        if self._completed_fingerprint is not None and not compare_digest(
            self._completed_fingerprint, receipt_fingerprint
        ):
            raise ValueError("local_text_governance_lease_completion_mismatch")
        self._completed_fingerprint = receipt_fingerprint

    def interrupt(self, reason: str) -> None:
        if not reason:
            raise ValueError("local_text_governance_interruption_reason_required")
        self._interruption_reason = reason


def _require_aware_time(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("local_text_governance_verified_at_invalid")


def _require_exact(observed: tuple[object, ...], expected: tuple[object, ...], error: str) -> None:
    if observed != expected:
        raise ValueError(error)


class LocalTextGovernanceAuthorityAdapter:
    """Bind one engine request to one exact persisted Governance authority."""

    def __init__(self, governance: LocalTextExecutionGovernancePort) -> None:
        self._governance = governance

    @staticmethod
    def _require_apply_staging(
        request: LocalTextStagingAuthorizationRequest,
        context: AdapterExecutionGrantContextPort,
    ) -> None:
        execution = context.execution_request
        grant = context.grant
        binding = request.execution_binding
        _require_exact(
            (
                request.purpose,
                execution.action_kind,
                execution.execution_policy_version,
                execution.execution_backend_version,
                request.operation,
                request.resource_ref,
                request.subject_ref,
                request.preflight_fingerprint,
                request.before_content_sha256,
                request.desired_content_sha256,
                request.root_config_fingerprint,
                request.mutation_receipt_fingerprint,
                binding.execution_grant_id,
                binding.execution_grant_fingerprint,
                binding.action_fingerprint,
                binding.execution_request_fingerprint,
                binding.intent_fingerprint,
            ),
            (
                "execute",
                "execute_external_action",
                LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION,
                LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION,
                execution.operation,
                execution.resource_ref,
                execution.subject_ref,
                execution.preflight_fingerprint,
                execution.before_content_sha256,
                execution.desired_content_sha256,
                execution.root_config_fingerprint,
                None,
                grant.grant_id,
                grant.grant_fingerprint,
                grant.action_fingerprint,
                execution.execution_request_fingerprint,
                grant.intent_fingerprint,
            ),
            "local_text_governance_apply_staging_binding_mismatch",
        )

    @staticmethod
    def _require_rollback_staging(
        request: LocalTextStagingAuthorizationRequest,
        context: LocalTextRollbackGrantContextPort,
    ) -> None:
        rollback = context.rollback_request
        grant = context.grant
        binding = request.execution_binding
        _require_exact(
            (
                request.purpose,
                request.operation_id,
                rollback.action_kind,
                rollback.source_execution_policy_version,
                rollback.source_execution_backend_version,
                rollback.transaction_policy_version,
                rollback.transaction_backend_version,
                rollback.rollback_policy_version,
                rollback.rollback_backend_version,
                request.operation,
                request.resource_ref,
                request.subject_ref,
                request.preflight_fingerprint,
                request.before_content_sha256,
                request.desired_content_sha256,
                request.root_config_fingerprint,
                request.mutation_receipt_fingerprint,
                context.mutation_receipt.receipt_fingerprint,
                binding.execution_grant_id,
                binding.execution_grant_fingerprint,
                binding.action_fingerprint,
                binding.execution_request_fingerprint,
                binding.intent_fingerprint,
            ),
            (
                "rollback",
                str(rollback.rollback_operation_id),
                "execute_external_action",
                LOCAL_TEXT_FILE_EXECUTION_POLICY_VERSION,
                LOCAL_TEXT_FILE_EXECUTION_BACKEND_VERSION,
                SHARED_TRANSACTION_POLICY_VERSION,
                SHARED_TRANSACTION_BACKEND_VERSION,
                LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION,
                LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION,
                rollback.operation,
                rollback.resource_ref,
                rollback.subject_ref,
                rollback.source_preflight_fingerprint,
                rollback.expected_current_sha256,
                rollback.restored_content_sha256,
                rollback.root_config_fingerprint,
                rollback.mutation_receipt_fingerprint,
                rollback.mutation_receipt_fingerprint,
                grant.grant_id,
                grant.grant_fingerprint,
                grant.action_fingerprint,
                rollback.rollback_request_fingerprint,
                grant.intent_fingerprint,
            ),
            "local_text_governance_rollback_staging_binding_mismatch",
        )

    def verify_staging(
        self,
        request: LocalTextStagingAuthorizationRequest,
        verified_at: datetime,
    ) -> bool:
        _require_aware_time(verified_at)
        binding = request.execution_binding
        if request.purpose == "execute":
            context = self._governance.load_adapter_execution_grant_context(
                binding.execution_grant_id
            )
            self._require_apply_staging(request, context)
            return self._governance.verify_adapter_execution_grant_for_staging_exact(
                binding.execution_grant_id,
                subject_ref=request.subject_ref,
                expected_grant_fingerprint=binding.execution_grant_fingerprint,
                expected_action_fingerprint=binding.action_fingerprint,
                expected_execution_request_fingerprint=(binding.execution_request_fingerprint),
                intent_fingerprint=binding.intent_fingerprint,
                confirmation_receipt_id=binding.confirmation_receipt_id,
            )
        if request.purpose == "rollback":
            context = self._governance.load_local_text_file_rollback_grant_context(
                binding.execution_grant_id
            )
            self._require_rollback_staging(request, context)
            return self._governance.verify_local_text_file_rollback_grant_for_staging_exact(
                binding.execution_grant_id,
                subject_ref=request.subject_ref,
                expected_grant_fingerprint=binding.execution_grant_fingerprint,
                expected_action_fingerprint=binding.action_fingerprint,
                expected_rollback_request_fingerprint=(binding.execution_request_fingerprint),
                intent_fingerprint=binding.intent_fingerprint,
                confirmation_receipt_id=binding.confirmation_receipt_id,
            )
        raise ValueError("local_text_governance_purpose_invalid")

    @staticmethod
    def _require_apply_authority(
        request: LocalTextExecutionAuthorizationRequest,
        context: AdapterExecutionGrantContextPort,
    ) -> None:
        staging = LocalTextStagingAuthorizationRequest(
            purpose=request.purpose,
            operation_id=request.operation_id,
            operation=request.operation,
            resource_ref=request.resource_ref,
            subject_ref=request.subject_ref,
            preflight_fingerprint=request.preflight_fingerprint,
            before_content_sha256=request.before_content_sha256,
            desired_content_sha256=request.desired_content_sha256,
            root_config_fingerprint=request.root_config_fingerprint,
            execution_binding=_binding_from_authority(request),
            mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
        )
        LocalTextGovernanceAuthorityAdapter._require_apply_staging(staging, context)
        if (
            request.transaction_policy_version != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
            or LOCAL_TEXT_TRANSACTION_BACKEND_VERSION != SHARED_TRANSACTION_BACKEND_VERSION
        ):
            raise ValueError("local_text_governance_transaction_policy_mismatch")

    @staticmethod
    def _require_rollback_authority(
        request: LocalTextExecutionAuthorizationRequest,
        context: LocalTextRollbackGrantContextPort,
    ) -> None:
        staging = LocalTextStagingAuthorizationRequest(
            purpose=request.purpose,
            operation_id=request.operation_id,
            operation=request.operation,
            resource_ref=request.resource_ref,
            subject_ref=request.subject_ref,
            preflight_fingerprint=request.preflight_fingerprint,
            before_content_sha256=request.before_content_sha256,
            desired_content_sha256=request.desired_content_sha256,
            root_config_fingerprint=request.root_config_fingerprint,
            execution_binding=_binding_from_authority(request),
            mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
        )
        LocalTextGovernanceAuthorityAdapter._require_rollback_staging(staging, context)
        if (
            request.transaction_policy_version != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
            or context.rollback_request.transaction_policy_version
            != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
            or context.rollback_request.transaction_backend_version
            != LOCAL_TEXT_TRANSACTION_BACKEND_VERSION
        ):
            raise ValueError("local_text_governance_transaction_policy_mismatch")

    def claim(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        claimed_at: datetime,
    ) -> _PersistedClaimLease:
        _require_aware_time(claimed_at)
        if request.purpose == "execute":
            context = self._governance.load_adapter_execution_grant_context(
                request.execution_grant_id
            )
            self._require_apply_authority(request, context)
            claim = self._governance.claim_adapter_execution_grant_exact(
                request.execution_grant_id,
                operation_id=request.operation_id,
                journal_reservation_fingerprint=request.journal_reservation_fingerprint,
                subject_ref=request.subject_ref,
                expected_grant_fingerprint=request.execution_grant_fingerprint,
                expected_action_fingerprint=request.action_fingerprint,
                expected_execution_request_fingerprint=(request.execution_request_fingerprint),
                intent_fingerprint=request.intent_fingerprint,
                confirmation_receipt_id=request.confirmation_receipt_id,
            )
            translated = _apply_context(claim)
        elif request.purpose == "rollback":
            context = self._governance.load_local_text_file_rollback_grant_context(
                request.execution_grant_id
            )
            self._require_rollback_authority(request, context)
            claim = self._governance.claim_local_text_file_rollback_grant_exact(
                request.execution_grant_id,
                rollback_operation_id=request.operation_id,
                rollback_journal_reservation_fingerprint=(request.journal_reservation_fingerprint),
                subject_ref=request.subject_ref,
                expected_grant_fingerprint=request.execution_grant_fingerprint,
                expected_action_fingerprint=request.action_fingerprint,
                expected_rollback_request_fingerprint=(request.execution_request_fingerprint),
                intent_fingerprint=request.intent_fingerprint,
                confirmation_receipt_id=request.confirmation_receipt_id,
            )
            translated = _rollback_context(claim)
        else:
            raise ValueError("local_text_governance_purpose_invalid")
        _require_context_matches_request(translated, request)
        return _PersistedClaimLease(translated)

    def verify_effect_start(
        self,
        context: LocalTextExecutionAuthorizationContext,
        verified_at: datetime,
    ) -> bool:
        _require_aware_time(verified_at)
        try:
            claim = self._load_claim(context)
        except KeyError:
            return False
        translated = _context_from_claim(claim)
        if translated != context:
            return False
        if context.purpose == "execute":
            return self._governance.verify_adapter_execution_claim_for_effect_start_exact(
                claim,
                observed_root_config_fingerprint=context.root_config_fingerprint,
                observed_precondition_content_sha256=context.before_content_sha256,
                observed_desired_content_sha256=context.desired_content_sha256,
            )
        return self._governance.verify_local_text_file_rollback_claim_for_effect_start_exact(
            claim,
            observed_root_config_fingerprint=context.root_config_fingerprint,
            observed_expected_current_sha256=context.before_content_sha256,
            observed_restored_content_sha256=context.desired_content_sha256,
        )

    def lookup_historical(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        verified_at: datetime,
    ) -> LocalTextExecutionAuthorizationContext | None:
        _require_aware_time(verified_at)
        try:
            claim = self._load_claim_for_request(request)
        except KeyError:
            return None
        context = _context_from_claim(claim)
        _require_context_matches_request(context, request)
        if not self._verify_recovery_claim(claim, request.purpose):
            raise ValueError("local_text_governance_historical_claim_not_verified")
        return context

    def verify_historical(
        self,
        context: LocalTextExecutionAuthorizationContext,
        verified_at: datetime,
    ) -> bool:
        _require_aware_time(verified_at)
        try:
            claim = self._load_claim(context)
        except KeyError:
            return False
        translated = _context_from_claim(claim)
        return translated == context and self._verify_recovery_claim(claim, context.purpose)

    def _load_claim(
        self, context: LocalTextExecutionAuthorizationContext
    ) -> AdapterExecutionGrantClaimContract | LocalTextFileRollbackGrantClaimContract:
        if context.purpose == "execute":
            return self._governance.load_adapter_execution_claim_for_recovery_exact(
                context.operation_id,
                journal_reservation_fingerprint=context.journal_reservation_fingerprint,
            )
        if context.purpose == "rollback":
            return self._governance.load_local_text_file_rollback_claim_for_recovery_exact(
                context.operation_id,
                rollback_journal_reservation_fingerprint=(context.journal_reservation_fingerprint),
            )
        raise ValueError("local_text_governance_purpose_invalid")

    def _load_claim_for_request(
        self, request: LocalTextExecutionAuthorizationRequest
    ) -> AdapterExecutionGrantClaimContract | LocalTextFileRollbackGrantClaimContract:
        if request.purpose == "execute":
            return self._governance.load_adapter_execution_claim_for_recovery_exact(
                request.operation_id,
                journal_reservation_fingerprint=request.journal_reservation_fingerprint,
            )
        if request.purpose == "rollback":
            return self._governance.load_local_text_file_rollback_claim_for_recovery_exact(
                request.operation_id,
                rollback_journal_reservation_fingerprint=(request.journal_reservation_fingerprint),
            )
        raise ValueError("local_text_governance_purpose_invalid")

    def _verify_recovery_claim(
        self,
        claim: AdapterExecutionGrantClaimContract | LocalTextFileRollbackGrantClaimContract,
        purpose: str,
    ) -> bool:
        if purpose == "execute":
            return self._governance.verify_adapter_execution_claim_for_recovery_exact(claim)
        if purpose == "rollback":
            return self._governance.verify_local_text_file_rollback_claim_for_recovery_exact(claim)
        raise ValueError("local_text_governance_purpose_invalid")

    def record_mutation_receipt(
        self, receipt: LocalTextMutationReceipt
    ) -> LocalTextMutationReceipt:
        return self._governance.record_local_text_mutation_receipt(receipt)

    def record_rollback_receipt(
        self, receipt: LocalTextRollbackReceipt
    ) -> LocalTextRollbackReceipt:
        return self._governance.record_local_text_rollback_receipt(receipt)


def _binding_from_authority(request: LocalTextExecutionAuthorizationRequest):
    from operational_service.adapters.local_text_transaction import (
        LocalTextExecutionGrantBinding,
    )

    return LocalTextExecutionGrantBinding(
        execution_grant_id=request.execution_grant_id,
        execution_grant_fingerprint=request.execution_grant_fingerprint,
        action_fingerprint=request.action_fingerprint,
        execution_request_fingerprint=request.execution_request_fingerprint,
        intent_fingerprint=request.intent_fingerprint,
        confirmation_receipt_id=request.confirmation_receipt_id,
    )


def _apply_context(
    claim: AdapterExecutionGrantClaimContract,
) -> LocalTextExecutionAuthorizationContext:
    request = claim.execution_request
    context = LocalTextExecutionAuthorizationContext(
        purpose="execute",
        operation_id=str(claim.operation_id),
        execution_grant_id=claim.grant_id,
        execution_claim_id=claim.claim_id,
        action_kind=request.action_kind,
        operation=request.operation,
        resource_ref=request.resource_ref,
        subject_ref=request.subject_ref,
        preflight_fingerprint=request.preflight_fingerprint,
        before_content_sha256=request.before_content_sha256,
        desired_content_sha256=request.desired_content_sha256,
        root_config_fingerprint=request.root_config_fingerprint,
        claimed_at=str(claim.claimed_at),
        expires_at=str(claim.expires_at),
        authority_fingerprint="0" * 64,
        execution_grant_fingerprint=claim.grant_fingerprint,
        action_fingerprint=claim.action_fingerprint,
        execution_request_fingerprint=request.execution_request_fingerprint,
        intent_fingerprint=claim.intent_fingerprint,
        confirmation_receipt_id=claim.confirmation_receipt_id,
        journal_reservation_fingerprint=claim.journal_reservation_fingerprint,
    )
    return _with_authority_fingerprint(context)


def _rollback_context(
    claim: LocalTextFileRollbackGrantClaimContract,
) -> LocalTextExecutionAuthorizationContext:
    request = claim.rollback_request
    context = LocalTextExecutionAuthorizationContext(
        purpose="rollback",
        operation_id=str(claim.rollback_operation_id),
        execution_grant_id=claim.grant_id,
        execution_claim_id=claim.claim_id,
        action_kind=request.action_kind,
        operation=request.operation,
        resource_ref=request.resource_ref,
        subject_ref=request.subject_ref,
        preflight_fingerprint=request.source_preflight_fingerprint,
        before_content_sha256=request.expected_current_sha256,
        desired_content_sha256=request.restored_content_sha256,
        root_config_fingerprint=request.root_config_fingerprint,
        claimed_at=str(claim.claimed_at),
        expires_at=str(claim.expires_at),
        authority_fingerprint="0" * 64,
        execution_grant_fingerprint=claim.grant_fingerprint,
        action_fingerprint=claim.action_fingerprint,
        execution_request_fingerprint=request.rollback_request_fingerprint,
        intent_fingerprint=claim.intent_fingerprint,
        confirmation_receipt_id=claim.confirmation_receipt_id,
        journal_reservation_fingerprint=(claim.rollback_journal_reservation_fingerprint),
        mutation_receipt_fingerprint=request.mutation_receipt_fingerprint,
    )
    return _with_authority_fingerprint(context)


def _with_authority_fingerprint(
    context: LocalTextExecutionAuthorizationContext,
) -> LocalTextExecutionAuthorizationContext:
    from dataclasses import replace

    return replace(
        context,
        authority_fingerprint=build_execution_authority_fingerprint(context),
    )


def _context_from_claim(
    claim: AdapterExecutionGrantClaimContract | LocalTextFileRollbackGrantClaimContract,
) -> LocalTextExecutionAuthorizationContext:
    if isinstance(claim, AdapterExecutionGrantClaimContract):
        return _apply_context(claim)
    if isinstance(claim, LocalTextFileRollbackGrantClaimContract):
        return _rollback_context(claim)
    raise TypeError("local_text_governance_claim_type_invalid")


def _require_context_matches_request(
    context: LocalTextExecutionAuthorizationContext,
    request: LocalTextExecutionAuthorizationRequest,
) -> None:
    _require_exact(
        (
            context.purpose,
            context.operation_id,
            context.action_kind,
            context.operation,
            context.resource_ref,
            context.subject_ref,
            context.preflight_fingerprint,
            context.before_content_sha256,
            context.desired_content_sha256,
            context.root_config_fingerprint,
            context.execution_grant_id,
            context.execution_grant_fingerprint,
            context.action_fingerprint,
            context.execution_request_fingerprint,
            context.intent_fingerprint,
            context.confirmation_receipt_id,
            context.journal_reservation_fingerprint,
            context.mutation_receipt_fingerprint,
        ),
        (
            request.purpose,
            request.operation_id,
            request.action_kind,
            request.operation,
            request.resource_ref,
            request.subject_ref,
            request.preflight_fingerprint,
            request.before_content_sha256,
            request.desired_content_sha256,
            request.root_config_fingerprint,
            request.execution_grant_id,
            request.execution_grant_fingerprint,
            request.action_fingerprint,
            request.execution_request_fingerprint,
            request.intent_fingerprint,
            request.confirmation_receipt_id,
            request.journal_reservation_fingerprint,
            request.mutation_receipt_fingerprint,
        ),
        "local_text_governance_claim_binding_mismatch",
    )
