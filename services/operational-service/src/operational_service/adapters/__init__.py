"""Side-effect-free operational adapter preflights."""

from operational_service.adapters.local_text_file import (
    LocalTextFilePreflightAdapter,
    build_local_text_file_preflight_fingerprint,
    build_local_text_file_rollback_fingerprint,
    require_valid_local_text_file_preflight,
    validate_local_text_file_preflight,
    validate_local_text_file_preflight_fingerprint,
    validate_local_text_file_rollback_fingerprint,
)
from operational_service.adapters.local_text_governance import (
    LocalTextExecutionGovernancePort,
    LocalTextGovernanceAuthorityAdapter,
)
from operational_service.adapters.local_text_transaction import (
    LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
    LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
    InjectedTransactionFailure,
    LocalTextClaimedAuthorizationLease,
    LocalTextExecutionAuthorizationContext,
    LocalTextExecutionAuthorizationRequest,
    LocalTextExecutionGrantBinding,
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
    LocalTextStagingAuthorizationRequest,
    LocalTextTransactionEngine,
    build_execution_authority_fingerprint,
)
from shared.contracts import LocalTextMutationReceipt, LocalTextRollbackReceipt
from shared.local_text_rollback_permissions import (
    build_mutation_receipt_fingerprint,
    build_rollback_receipt_fingerprint,
)

__all__ = (
    "LocalTextFilePreflightAdapter",
    "LocalTextExecutionGovernancePort",
    "LocalTextGovernanceAuthorityAdapter",
    "build_local_text_file_preflight_fingerprint",
    "build_local_text_file_rollback_fingerprint",
    "require_valid_local_text_file_preflight",
    "validate_local_text_file_preflight",
    "validate_local_text_file_preflight_fingerprint",
    "validate_local_text_file_rollback_fingerprint",
    "InjectedTransactionFailure",
    "LOCAL_TEXT_TRANSACTION_BACKEND_VERSION",
    "LOCAL_TEXT_TRANSACTION_POLICY_VERSION",
    "LocalTextClaimedAuthorizationLease",
    "LocalTextExecutionAuthorizationContext",
    "LocalTextExecutionAuthorizationRequest",
    "LocalTextExecutionGrantBinding",
    "LocalTextMutationReceipt",
    "LocalTextMutationRequest",
    "LocalTextRollbackReceipt",
    "LocalTextRollbackRequest",
    "LocalTextStagingAuthorizationRequest",
    "LocalTextTransactionEngine",
    "build_execution_authority_fingerprint",
    "build_mutation_receipt_fingerprint",
    "build_rollback_receipt_fingerprint",
)
