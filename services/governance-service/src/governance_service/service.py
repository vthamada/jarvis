"""Governance service with explicit low, moderate, and high-risk policies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from shared.action_confirmation import (
    action_confirmation_challenge_fingerprint,
    action_intent_fingerprint,
    human_confirmation_receipt_fingerprint,
)
from shared.adapter_execution_permissions import (
    LOCAL_TEXT_FILE_EXECUTION_MAX_TTL_SECONDS,
    build_adapter_execution_grant,
)
from shared.adapter_permissions import build_adapter_grant
from shared.artifact_policy import (
    canonical_artifact_states_from_mission,
    validate_artifact_lineage,
    validate_artifact_transition,
    validate_artifact_version,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    evaluate_autonomy_action,
)
from shared.contracts import (
    WORK_ITEM_PRIORITY_LEVELS,
    ActionConfirmationChallengeContract,
    ActionConfirmationClaimContract,
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterDescriptorContract,
    AdapterExecutionDescriptorContract,
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AdapterExecutionRegistrySnapshotContract,
    AdapterExecutionRequestContract,
    AdapterGrantClaimContract,
    AdapterGrantContract,
    AdapterRegistrySnapshotContract,
    AutonomyActionPolicyDecisionContract,
    DeliberativePlanContract,
    GovernanceCheckContract,
    GovernanceDecisionContract,
    HumanConfirmationReceiptContract,
    InputContract,
    KnowledgeEvidenceGovernanceContract,
    LocalTextFilePreflightAttestationContract,
    LocalTextFilePreflightContract,
    LocalTextFileRollbackDescriptorContract,
    LocalTextFileRollbackGrantClaimContract,
    LocalTextFileRollbackGrantContract,
    LocalTextFileRollbackRegistrySnapshotContract,
    LocalTextFileRollbackRequestContract,
    LocalTextMutationReceipt,
    LocalTextRollbackReceipt,
    MemoryInfluenceGovernanceAssessmentContract,
    MemoryInfluencePolicyDecisionContract,
    MemoryLifecycleCandidateContract,
    MemoryLifecycleGovernanceAssessmentContract,
    MissionStateContract,
    OpenLoopStateContract,
    OperationDispatchContract,
    OperatorFeedbackContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
    WorkflowLifecycleGovernanceAssessmentContract,
    WorkflowLifecycleTransitionContract,
)
from shared.local_text_rollback_permissions import (
    LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS,
    build_local_text_file_rollback_grant,
)
from shared.types import (
    GovernanceCheckId,
    GovernanceDecisionId,
    MemoryClass,
    MissionStatus,
    PermissionDecision,
    RiskLevel,
)
from shared.work_item_policy import (
    canonical_work_items_from_mission,
    refresh_work_item_blocking_states,
    unresolved_dependency_refs,
    validate_work_item_graph,
    validate_work_item_transition,
)
from shared.workflow_lifecycle import (
    validate_workflow_lifecycle_transition,
    workflow_lifecycle_transition_fingerprint,
)

from .repository import (
    ActionConfirmationContext,
    ActionConfirmationRepository,
    AdapterExecutionGrantContext,
    AdapterGrantContext,
    LocalTextFileRollbackGrantContext,
)

HIGH_RISK_KEYWORDS = (
    "delete",
    "drop",
    "destroy",
    "excluir",
    "apagar",
    "deletar",
    "remover",
)

MODERATE_RISK_KEYWORDS = (
    "deploy",
    "publish",
    "release",
    "migrate",
    "update",
    "rewrite",
    "alter",
    "change",
)


@dataclass
class GovernanceAssessment:
    """Structured governance output for a request or memory assessment."""

    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract


class GovernanceService:
    """Apply explicit request and memory policies for the v1 flow."""

    name = "governance-service"

    def __init__(
        self,
        action_confirmation_database_path: str | Path = ":memory:",
        *,
        action_confirmation_repository: ActionConfirmationRepository | None = None,
        trusted_execution_clock: Callable[[], str] | None = None,
    ) -> None:
        execution_clock = trusted_execution_clock or self.now
        if not callable(execution_clock):
            raise TypeError("trusted execution clock must be callable")
        self.action_confirmation_repository = (
            action_confirmation_repository
            if action_confirmation_repository is not None
            else ActionConfirmationRepository(
                action_confirmation_database_path,
                trusted_execution_clock=execution_clock,
            )
        )
        self._trusted_execution_clock = execution_clock

    def activate_adapter_registry(
        self,
        snapshot: AdapterRegistrySnapshotContract,
        *,
        activated_at: str | None = None,
    ) -> AdapterRegistrySnapshotContract:
        """Activate one exact immutable allowlist snapshot explicitly."""

        return self.action_confirmation_repository.activate_adapter_registry(
            snapshot,
            activated_at=activated_at or self.now(),
        )

    def load_active_adapter_registry(self) -> AdapterRegistrySnapshotContract:
        """Load the current exact allowlist snapshot."""

        return self.action_confirmation_repository.load_active_adapter_registry()

    def resolve_active_adapter_descriptor(
        self,
        action_request: AdapterActionRequestContract,
    ) -> tuple[AdapterRegistrySnapshotContract, AdapterDescriptorContract]:
        """Resolve one request against the current allowlist without granting it."""

        return self.action_confirmation_repository.resolve_active_adapter_descriptor(action_request)

    def issue_adapter_grant(
        self,
        intent: ActionIntentContract,
        action_request: AdapterActionRequestContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        *,
        expected_registry_fingerprint: str,
        expected_descriptor_fingerprint: str,
        issued_at: str | None = None,
        expires_at: str | None = None,
    ) -> AdapterGrantContract:
        """Persist one exact metadata-only grant under the active allowlist."""

        issuance_time = issued_at or str(intent.issued_at)
        registry, descriptor = self.resolve_active_adapter_descriptor(action_request)
        if registry.registry_fingerprint != expected_registry_fingerprint:
            raise ValueError("adapter registry fingerprint changed before grant issuance")
        if descriptor.descriptor_fingerprint != expected_descriptor_fingerprint:
            raise ValueError("adapter descriptor fingerprint changed before grant issuance")
        intent_fingerprint = action_intent_fingerprint(intent)
        grant_identity = sha256(
            f"{intent_fingerprint}:{intent.nonce}:adapter-grant".encode("utf-8")
        ).hexdigest()
        grant_nonce = sha256(
            f"{intent.nonce}:{intent_fingerprint}:grant-nonce".encode("utf-8")
        ).hexdigest()
        grant = build_adapter_grant(
            grant_id=f"adapter-grant://{grant_identity}",
            subject_ref=intent.operator_identity_ref,
            request=action_request,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            policy_version=AUTONOMY_ACTION_POLICY_VERSION,
            nonce=grant_nonce,
            issued_at=issuance_time,
            expires_at=expires_at or intent.expires_at,
            now=issuance_time,
        )
        return self.action_confirmation_repository.record_adapter_grant(
            intent,
            grant,
            autonomy_decision,
            verified_at=issuance_time,
        )

    def load_adapter_grant_context(self, grant_id: str) -> AdapterGrantContext:
        """Load and reverify a persisted historical grant context."""

        return self.action_confirmation_repository.load_adapter_grant_context(grant_id)

    def verify_adapter_grant_for_preflight_exact(
        self,
        grant_id: str,
        *,
        subject_ref: str,
        action_request: AdapterActionRequestContract,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        expected_content_digest: str,
        expected_precondition_digest: str,
        expected_descriptor_fingerprint: str,
        expected_registry_fingerprint: str,
        expected_authorization_expires_at: str,
        preflight_expires_at: str,
        intent_fingerprint: str,
        verified_at: str,
    ) -> bool:
        """Verify exact prepare-only preflight authority without consuming evidence."""

        return self.action_confirmation_repository.verify_adapter_grant_for_preflight_exact(
            grant_id,
            subject_ref=subject_ref,
            action_request=action_request,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_content_digest=expected_content_digest,
            expected_precondition_digest=expected_precondition_digest,
            expected_descriptor_fingerprint=expected_descriptor_fingerprint,
            expected_registry_fingerprint=expected_registry_fingerprint,
            expected_authorization_expires_at=expected_authorization_expires_at,
            preflight_expires_at=preflight_expires_at,
            intent_fingerprint=intent_fingerprint,
            verified_at=verified_at,
        )

    def activate_adapter_execution_registry(
        self,
        snapshot: AdapterExecutionRegistrySnapshotContract,
        *,
        activated_at: str | None = None,
    ) -> AdapterExecutionRegistrySnapshotContract:
        """Activate a separate execution-only adapter allowlist snapshot."""

        return self.action_confirmation_repository.activate_adapter_execution_registry(
            snapshot,
            activated_at=activated_at or self.now(),
        )

    def load_active_adapter_execution_registry(
        self,
    ) -> AdapterExecutionRegistrySnapshotContract:
        """Load the current execution-only registry snapshot."""

        return self.action_confirmation_repository.load_active_adapter_execution_registry()

    def resolve_active_adapter_execution_descriptor(
        self,
        execution_request: AdapterExecutionRequestContract,
    ) -> tuple[
        AdapterExecutionRegistrySnapshotContract,
        AdapterExecutionDescriptorContract,
    ]:
        """Resolve an attested execution request without issuing authority."""

        return self.action_confirmation_repository.resolve_active_adapter_execution_descriptor(
            execution_request
        )

    def attest_local_text_file_preflight(
        self,
        preflight: LocalTextFilePreflightContract,
    ) -> tuple[
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]:
        """Persist trusted, content-free evidence for a materialized preflight."""

        return self.action_confirmation_repository.record_local_text_file_preflight_attestation(
            preflight,
            attested_at=self._execution_now(),
        )

    def issue_adapter_execution_grant(
        self,
        intent: ActionIntentContract,
        execution_request: AdapterExecutionRequestContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        *,
        expected_registry_fingerprint: str,
        expected_descriptor_fingerprint: str,
        expires_at: str | None = None,
    ) -> AdapterExecutionGrantContract:
        """Issue one confirmation-required execution grant from trusted evidence."""

        issuance_time = self._execution_now()
        registry, descriptor = self.resolve_active_adapter_execution_descriptor(execution_request)
        if registry.registry_fingerprint != expected_registry_fingerprint:
            raise ValueError("adapter execution registry changed before grant issuance")
        if descriptor.descriptor_fingerprint != expected_descriptor_fingerprint:
            raise ValueError("adapter execution descriptor changed before grant issuance")
        intent_fingerprint = action_intent_fingerprint(intent)
        grant_identity = sha256(
            (
                f"{execution_request.execution_request_fingerprint}:"
                f"{intent_fingerprint}:adapter-execution-grant"
            ).encode("utf-8")
        ).hexdigest()
        grant_nonce = sha256(
            (
                f"{execution_request.preflight_attestation_fingerprint}:"
                f"{intent.nonce}:execution-grant-nonce"
            ).encode("utf-8")
        ).hexdigest()
        grant_id = f"adapter-execution-grant://{grant_identity}"
        try:
            existing = self.load_adapter_execution_grant_context(grant_id)
        except KeyError:
            existing = None
        if existing is not None:
            if (
                existing.intent == intent
                and existing.execution_request == execution_request
                and existing.autonomy_decision == autonomy_decision
                and existing.registry.registry_fingerprint == expected_registry_fingerprint
                and existing.descriptor.descriptor_fingerprint == expected_descriptor_fingerprint
            ):
                return existing.grant
            raise ValueError("adapter execution grant identity has different evidence")
        grant = build_adapter_execution_grant(
            grant_id=grant_id,
            subject_ref=intent.operator_identity_ref,
            request=execution_request,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            policy_version=AUTONOMY_ACTION_POLICY_VERSION,
            nonce=grant_nonce,
            issued_at=issuance_time,
            expires_at=(
                expires_at
                or min(
                    datetime.fromisoformat(issuance_time.replace("Z", "+00:00"))
                    + timedelta(seconds=LOCAL_TEXT_FILE_EXECUTION_MAX_TTL_SECONDS),
                    datetime.fromisoformat(str(intent.expires_at).replace("Z", "+00:00")),
                    datetime.fromisoformat(
                        str(execution_request.preflight_expires_at).replace("Z", "+00:00")
                    ),
                    datetime.fromisoformat(
                        str(execution_request.preflight_authorization_expires_at).replace(
                            "Z", "+00:00"
                        )
                    ),
                ).isoformat()
            ),
            now=issuance_time,
        )
        return self.action_confirmation_repository.record_adapter_execution_grant(
            intent,
            grant,
            autonomy_decision,
            verified_at=issuance_time,
        )

    def load_adapter_execution_grant_context(
        self,
        grant_id: str,
    ) -> AdapterExecutionGrantContext:
        """Load historical execution evidence without reopening active authority."""

        return self.action_confirmation_repository.load_adapter_execution_grant_context(grant_id)

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
    ) -> bool:
        """Verify exact active authority before journal, stage, or backup I/O."""

        return self.action_confirmation_repository.verify_adapter_execution_grant_for_staging_exact(
            grant_id,
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_execution_request_fingerprint=(expected_execution_request_fingerprint),
            intent_fingerprint=intent_fingerprint,
            confirmation_receipt_id=confirmation_receipt_id,
            verified_at=self._execution_now(),
        )

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
    ) -> AdapterExecutionGrantClaimContract:
        """Atomically claim execution and its confirmation at trusted current time."""

        return self.action_confirmation_repository.claim_adapter_execution_grant_exact(
            grant_id,
            operation_id=operation_id,
            journal_reservation_fingerprint=journal_reservation_fingerprint,
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_execution_request_fingerprint=(expected_execution_request_fingerprint),
            intent_fingerprint=intent_fingerprint,
            confirmation_receipt_id=confirmation_receipt_id,
            claimed_at=self._execution_now(),
        )

    def verify_adapter_execution_claim_for_effect_start_exact(
        self,
        claim: AdapterExecutionGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_precondition_content_sha256: str,
        observed_desired_content_sha256: str,
    ) -> bool:
        """Recheck persisted claim plus physical bindings immediately before effect."""

        repository = self.action_confirmation_repository
        return repository.verify_adapter_execution_claim_for_effect_start_exact(
            claim,
            observed_root_config_fingerprint=observed_root_config_fingerprint,
            observed_precondition_content_sha256=(observed_precondition_content_sha256),
            observed_desired_content_sha256=observed_desired_content_sha256,
            verified_at=self._execution_now(),
        )

    def verify_adapter_execution_claim_for_recovery_exact(
        self,
        claim: AdapterExecutionGrantClaimContract,
    ) -> bool:
        """Verify historical evidence only; never authorize a new effect."""

        return (
            self.action_confirmation_repository.verify_adapter_execution_claim_for_recovery_exact(
                claim
            )
        )

    def load_adapter_execution_claim_for_recovery_exact(
        self,
        operation_id: str,
        *,
        journal_reservation_fingerprint: str | None = None,
    ) -> AdapterExecutionGrantClaimContract:
        """Find historical claim evidence by operation, with optional journal binding."""

        return self.action_confirmation_repository.load_adapter_execution_claim_for_recovery_exact(
            operation_id,
            journal_reservation_fingerprint=journal_reservation_fingerprint,
        )

    def activate_local_text_file_rollback_registry(
        self,
        snapshot: LocalTextFileRollbackRegistrySnapshotContract,
    ) -> LocalTextFileRollbackRegistrySnapshotContract:
        """Activate a rollback-only allowlist without changing apply authority."""

        return self.action_confirmation_repository.activate_local_text_file_rollback_registry(
            snapshot,
        )

    def record_local_text_mutation_receipt(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> LocalTextMutationReceipt:
        """Persist exact post-apply evidence independently of rollback intent."""

        return self.action_confirmation_repository.record_local_text_mutation_receipt(receipt)

    def load_local_text_mutation_receipt_exact(
        self,
        operation_id: str,
        *,
        expected_receipt_fingerprint: str,
    ) -> LocalTextMutationReceipt:
        """Load one exact persisted mutation proof without reopening authority."""

        return self.action_confirmation_repository.load_local_text_mutation_receipt_exact(
            operation_id,
            expected_receipt_fingerprint=expected_receipt_fingerprint,
        )

    def verify_local_text_mutation_receipt_exact(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> bool:
        """Fail closed unless a mutation receipt exactly matches the ledger."""

        return self.action_confirmation_repository.verify_local_text_mutation_receipt_exact(receipt)

    def load_active_local_text_file_rollback_registry(
        self,
    ) -> LocalTextFileRollbackRegistrySnapshotContract:
        return self.action_confirmation_repository.load_active_local_text_file_rollback_registry()

    def resolve_active_local_text_file_rollback_descriptor(
        self,
        request: LocalTextFileRollbackRequestContract,
    ) -> tuple[
        LocalTextFileRollbackRegistrySnapshotContract,
        LocalTextFileRollbackDescriptorContract,
    ]:
        return (
            self.action_confirmation_repository.resolve_active_local_text_file_rollback_descriptor(
                request
            )
        )

    def prepare_local_text_file_rollback(
        self,
        mutation_receipt: LocalTextMutationReceipt,
        *,
        rollback_operation_id: str,
    ) -> LocalTextFileRollbackRequestContract:
        """Load trusted mutation evidence and derive one dedicated rollback request."""

        return self.action_confirmation_repository.prepare_local_text_file_rollback(
            mutation_receipt,
            rollback_operation_id=rollback_operation_id,
        )

    def issue_local_text_file_rollback_grant(
        self,
        intent: ActionIntentContract,
        rollback_request: LocalTextFileRollbackRequestContract,
        autonomy_decision: AutonomyActionPolicyDecisionContract,
        *,
        expected_registry_fingerprint: str,
        expected_descriptor_fingerprint: str,
        expires_at: str | None = None,
    ) -> LocalTextFileRollbackGrantContract:
        """Issue a fresh confirmation-required rollback grant from persisted evidence."""

        issuance_time = self._execution_now()
        registry, descriptor = self.resolve_active_local_text_file_rollback_descriptor(
            rollback_request
        )
        if registry.registry_fingerprint != expected_registry_fingerprint:
            raise ValueError("local text rollback registry changed before issuance")
        if descriptor.descriptor_fingerprint != expected_descriptor_fingerprint:
            raise ValueError("local text rollback descriptor changed before issuance")
        intent_fingerprint = action_intent_fingerprint(intent)
        identity = sha256(
            (
                f"{rollback_request.rollback_request_fingerprint}:"
                f"{intent_fingerprint}:local-text-rollback-grant"
            ).encode("utf-8")
        ).hexdigest()
        nonce = sha256(
            (
                f"{rollback_request.mutation_receipt_fingerprint}:"
                f"{intent.nonce}:rollback-grant-nonce"
            ).encode("utf-8")
        ).hexdigest()
        grant_id = f"local-text-rollback-grant://{identity}"
        try:
            existing = self.load_local_text_file_rollback_grant_context(grant_id)
        except KeyError:
            existing = None
        if existing is not None:
            if (
                existing.intent == intent
                and existing.rollback_request == rollback_request
                and existing.autonomy_decision == autonomy_decision
                and existing.registry.registry_fingerprint == expected_registry_fingerprint
                and existing.descriptor.descriptor_fingerprint == expected_descriptor_fingerprint
            ):
                return existing.grant
            raise ValueError("local text rollback grant identity has different evidence")
        effective_expiry = (
            expires_at
            or min(
                datetime.fromisoformat(issuance_time.replace("Z", "+00:00"))
                + timedelta(seconds=LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS),
                datetime.fromisoformat(str(intent.expires_at).replace("Z", "+00:00")),
                datetime.fromisoformat(str(rollback_request.expires_at).replace("Z", "+00:00")),
            ).isoformat()
        )
        grant = build_local_text_file_rollback_grant(
            grant_id=grant_id,
            request=rollback_request,
            descriptor=descriptor,
            registry=registry,
            intent=intent,
            intent_fingerprint=intent_fingerprint,
            autonomy_decision=autonomy_decision,
            nonce=nonce,
            issued_at=issuance_time,
            expires_at=effective_expiry,
            now=issuance_time,
        )
        return self.action_confirmation_repository.record_local_text_file_rollback_grant(
            intent,
            grant,
            autonomy_decision,
        )

    def load_local_text_file_rollback_grant_context(
        self,
        grant_id: str,
    ) -> LocalTextFileRollbackGrantContext:
        return self.action_confirmation_repository.load_local_text_file_rollback_grant_context(
            grant_id
        )

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
    ) -> bool:
        repository = self.action_confirmation_repository
        return repository.verify_local_text_file_rollback_grant_for_staging_exact(
            grant_id,
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_rollback_request_fingerprint=(expected_rollback_request_fingerprint),
            intent_fingerprint=intent_fingerprint,
            confirmation_receipt_id=confirmation_receipt_id,
        )

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
    ) -> LocalTextFileRollbackGrantClaimContract:
        return self.action_confirmation_repository.claim_local_text_file_rollback_grant_exact(
            grant_id,
            rollback_operation_id=rollback_operation_id,
            rollback_journal_reservation_fingerprint=(rollback_journal_reservation_fingerprint),
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_rollback_request_fingerprint=(expected_rollback_request_fingerprint),
            intent_fingerprint=intent_fingerprint,
            confirmation_receipt_id=confirmation_receipt_id,
        )

    def verify_local_text_file_rollback_claim_for_effect_start_exact(
        self,
        claim: LocalTextFileRollbackGrantClaimContract,
        *,
        observed_root_config_fingerprint: str,
        observed_expected_current_sha256: str,
        observed_restored_content_sha256: str,
    ) -> bool:
        repository = self.action_confirmation_repository
        return repository.verify_local_text_file_rollback_claim_for_effect_start_exact(
            claim,
            observed_root_config_fingerprint=observed_root_config_fingerprint,
            observed_expected_current_sha256=observed_expected_current_sha256,
            observed_restored_content_sha256=observed_restored_content_sha256,
        )

    def verify_local_text_file_rollback_claim_for_recovery_exact(
        self,
        claim: LocalTextFileRollbackGrantClaimContract,
    ) -> bool:
        repository = self.action_confirmation_repository
        return repository.verify_local_text_file_rollback_claim_for_recovery_exact(claim)

    def load_local_text_file_rollback_claim_for_recovery_exact(
        self,
        rollback_operation_id: str,
        *,
        rollback_journal_reservation_fingerprint: str | None = None,
    ) -> LocalTextFileRollbackGrantClaimContract:
        repository = self.action_confirmation_repository
        return repository.load_local_text_file_rollback_claim_for_recovery_exact(
            rollback_operation_id,
            rollback_journal_reservation_fingerprint=(rollback_journal_reservation_fingerprint),
        )

    def record_local_text_rollback_receipt(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> LocalTextRollbackReceipt:
        return self.action_confirmation_repository.record_local_text_rollback_receipt(receipt)

    def load_local_text_rollback_receipt_exact(
        self,
        rollback_operation_id: str,
        *,
        expected_rollback_receipt_fingerprint: str,
    ) -> LocalTextRollbackReceipt:
        """Load one exact persisted rollback proof without reopening authority."""

        repository = self.action_confirmation_repository
        return repository.load_local_text_rollback_receipt_exact(
            rollback_operation_id,
            expected_rollback_receipt_fingerprint=(expected_rollback_receipt_fingerprint),
        )

    def verify_local_text_rollback_receipt_exact(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> bool:
        """Fail closed unless a rollback receipt exactly matches the ledger."""

        return self.action_confirmation_repository.verify_local_text_rollback_receipt_exact(receipt)

    def claim_adapter_grant_exact(
        self,
        grant_id: str,
        *,
        operation_id: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        confirmation_receipt_id: str | None = None,
        claimed_at: str | None = None,
    ) -> AdapterGrantClaimContract:
        """Atomically claim a grant and its exact confirmation when required."""

        return self.action_confirmation_repository.claim_adapter_grant_exact(
            grant_id,
            operation_id=operation_id,
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            intent_fingerprint=intent_fingerprint,
            confirmation_receipt_id=confirmation_receipt_id,
            claimed_at=claimed_at or self.now(),
        )

    def verify_adapter_grant_claim_exact(
        self,
        *,
        grant_id: str,
        claim_id: str,
        operation_id: str,
        subject_ref: str,
        expected_grant_fingerprint: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        claimed_at: str,
        verified_at: str,
        confirmation_receipt_id: str | None = None,
        confirmation_claim_id: str | None = None,
        confirmation_claim_fingerprint: str | None = None,
    ) -> bool:
        """Reverify one exact claim against the current allowlist and policy."""

        return self.action_confirmation_repository.verify_adapter_grant_claim_exact(
            grant_id=grant_id,
            claim_id=claim_id,
            operation_id=operation_id,
            subject_ref=subject_ref,
            expected_grant_fingerprint=expected_grant_fingerprint,
            expected_action_fingerprint=expected_action_fingerprint,
            intent_fingerprint=intent_fingerprint,
            claimed_at=claimed_at,
            verified_at=verified_at,
            confirmation_receipt_id=confirmation_receipt_id,
            confirmation_claim_id=confirmation_claim_id,
            confirmation_claim_fingerprint=confirmation_claim_fingerprint,
        )

    def issue_action_confirmation_challenge(
        self,
        intent: ActionIntentContract,
        *,
        prepared_dispatch: OperationDispatchContract | None = None,
        challenged_at: str | None = None,
    ) -> ActionConfirmationChallengeContract:
        """Persist one intent and emit a non-authorizing exact human challenge."""

        challenge_time = challenged_at or intent.issued_at
        if challenge_time != intent.issued_at:
            raise ValueError("action confirmation challenge must preserve intent issuance")
        challenge = ActionConfirmationChallengeContract(
            challenge_id=f"confirmation-challenge://{uuid4().hex}",
            intent_id=intent.intent_id,
            intent_fingerprint=action_intent_fingerprint(intent),
            action_fingerprint=intent.action_fingerprint,
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            operation=intent.operation,
            nonce=intent.nonce,
            issued_at=challenge_time,
            expires_at=intent.expires_at,
        )
        return self.action_confirmation_repository.record_intent_and_challenge(
            intent,
            challenge,
            prepared_dispatch=prepared_dispatch,
        )

    def confirm_action_challenge(
        self,
        challenge_id: str,
        *,
        operator_identity_ref: str,
        expected_action_fingerprint: str,
        confirmed_at: str | None = None,
    ) -> HumanConfirmationReceiptContract:
        """Record an exact human confirmation without granting execution authority."""

        confirmation_time = confirmed_at or self.now()
        intent, challenge = self.action_confirmation_repository.load_intent_and_challenge(
            challenge_id,
            verified_at=confirmation_time,
        )
        if operator_identity_ref != intent.operator_identity_ref:
            raise ValueError("action confirmation operator mismatch")
        if expected_action_fingerprint != intent.action_fingerprint:
            raise ValueError("action confirmation action fingerprint mismatch")
        receipt = HumanConfirmationReceiptContract(
            receipt_id=f"confirmation-receipt://{uuid4().hex}",
            challenge_id=challenge.challenge_id,
            challenge_fingerprint=action_confirmation_challenge_fingerprint(challenge),
            intent_id=intent.intent_id,
            intent_fingerprint=action_intent_fingerprint(intent),
            action_fingerprint=intent.action_fingerprint,
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            operation=intent.operation,
            confirmed_at=confirmation_time,
            expires_at=challenge.expires_at,
        )
        return self.action_confirmation_repository.record_receipt(
            receipt,
            verified_at=confirmation_time,
        )

    def load_action_confirmation_context(
        self,
        receipt_id: str,
    ) -> ActionConfirmationContext:
        """Load verified origin context for an exact confirmation retry envelope."""

        return self.action_confirmation_repository.load_confirmation_context(receipt_id)

    def load_action_confirmation_context_for_challenge(
        self,
        challenge_id: str,
    ) -> ActionConfirmationContext | None:
        """Read a persisted confirmation for reconciliation, without issuing one."""
        return self.action_confirmation_repository.load_confirmation_context_for_challenge(
            challenge_id
        )

    def claim_action_confirmation(
        self,
        receipt_id: str,
        *,
        operation_id: str,
        origin_request_id: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        operator_identity_ref: str,
        claimed_at: str | None = None,
    ) -> ActionConfirmationClaimContract:
        """Atomically consume a receipt for one exact operation before side effects."""

        claim_time = claimed_at or self.now()
        context = self.action_confirmation_repository.load_confirmation_context(receipt_id)
        intent = context.intent
        receipt = context.receipt
        expected_values = {
            "origin_request_id": (origin_request_id, intent.origin_request_id),
            "action_fingerprint": (
                expected_action_fingerprint,
                intent.action_fingerprint,
            ),
            "intent_fingerprint": (
                intent_fingerprint,
                action_intent_fingerprint(intent),
            ),
            "operator_identity_ref": (
                operator_identity_ref,
                intent.operator_identity_ref,
            ),
        }
        for field_name, (provided, expected) in expected_values.items():
            if provided != expected:
                raise ValueError(f"action confirmation {field_name} mismatch")
        claim = ActionConfirmationClaimContract(
            claim_id=f"confirmation-claim://{uuid4().hex}",
            receipt_id=receipt.receipt_id,
            receipt_fingerprint=human_confirmation_receipt_fingerprint(receipt),
            intent_id=intent.intent_id,
            intent_fingerprint=action_intent_fingerprint(intent),
            action_fingerprint=intent.action_fingerprint,
            operation_id=operation_id,
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            operation=intent.operation,
            claimed_at=claim_time,
            expires_at=receipt.expires_at,
        )
        return self.action_confirmation_repository.record_claim(
            claim,
            expected_action_fingerprint=expected_action_fingerprint,
            expected_operation_id=operation_id,
            expected_operator_identity_ref=operator_identity_ref,
            verified_at=claim_time,
        )

    def verify_action_confirmation_claim(
        self,
        *,
        receipt_id: str,
        claim_id: str,
        operation_id: str,
        origin_request_id: str,
        expected_action_fingerprint: str,
        intent_fingerprint: str,
        claimed_at: str,
        verified_at: str,
        operator_identity_ref: str,
    ) -> bool:
        """Reopen and reverify the claimed receipt as defense in depth."""

        return self.action_confirmation_repository.verify_claim_exact(
            receipt_id=receipt_id,
            claim_id=claim_id,
            operation_id=operation_id,
            origin_request_id=origin_request_id,
            expected_action_fingerprint=expected_action_fingerprint,
            intent_fingerprint=intent_fingerprint,
            claimed_at=claimed_at,
            verified_at=verified_at,
            operator_identity_ref=operator_identity_ref,
        )

    def assess_workflow_lifecycle_transition(
        self,
        transition: WorkflowLifecycleTransitionContract,
        *,
        current_transition: WorkflowLifecycleTransitionContract | None = None,
        release_bundle_verifier: (
            Callable[[WorkflowLifecycleTransitionContract], bool] | None
        ) = None,
        assessed_at: str | None = None,
    ) -> WorkflowLifecycleGovernanceAssessmentContract:
        """Authorize only an append-only, explicitly human-reviewed binding record."""

        blockers = validate_workflow_lifecycle_transition(
            transition,
            current_transition=current_transition,
        )
        release_bundle_verified = False
        if release_bundle_verifier is not None and not blockers:
            try:
                release_bundle_verified = bool(release_bundle_verifier(transition))
            except (TypeError, ValueError, RuntimeError):
                release_bundle_verified = False
        if not release_bundle_verified:
            blockers.append("workflow_lifecycle_release_bundle_not_verified")
        assessment_timestamp = assessed_at or self.now()
        try:
            transition_time = datetime.fromisoformat(transition.timestamp.replace("Z", "+00:00"))
            assessment_time = datetime.fromisoformat(assessment_timestamp.replace("Z", "+00:00"))
            if (
                transition_time.tzinfo is None
                or assessment_time.tzinfo is None
                or assessment_time < transition_time
            ):
                blockers.append("workflow_lifecycle_assessment_time_invalid")
                assessment_timestamp = transition.timestamp
        except (AttributeError, ValueError):
            blockers.append("workflow_lifecycle_assessment_time_invalid")
            assessment_timestamp = transition.timestamp
        blockers = list(dict.fromkeys(blockers))
        approved = not blockers
        return WorkflowLifecycleGovernanceAssessmentContract(
            assessment_id=f"workflow-lifecycle-assessment://{uuid4().hex[:12]}",
            transition_id=transition.transition_id,
            transition_action=transition.transition_action,
            transition_fingerprint=workflow_lifecycle_transition_fingerprint(transition),
            status="approved" if approved else "blocked",
            blockers=blockers,
            conditions=[
                "Record the transition append-only through canonical memory and Core.",
                "Keep the sovereign static workflow registry unchanged.",
                "Grant no execution authority from the lifecycle record itself.",
                "Require a new human-authorized transition for activation or rollback.",
            ],
            policy_refs=[
                "policy://workflow-lifecycle/human-authorization-required",
                "policy://workflow-lifecycle/append-only-cas",
                "policy://workflow-lifecycle/sovereign-registry-immutable",
                "policy://workflow-lifecycle/manual-rollback-only",
                "policy://memory/write-through-core-only",
            ],
            timestamp=assessment_timestamp,
            human_review_required=True,
            human_authorization_verified=approved,
            transition_recording_authorized=approved,
            memory_write_mode="through_core_only",
            read_only=True,
            active_registry_write_allowed=False,
            runtime_execution_allowed=False,
            automatic_promotion_allowed=False,
            automatic_rollback_allowed=False,
            core_mutation_allowed=False,
        )

    def assess_memory_lifecycle_review(
        self,
        candidate: MemoryLifecycleCandidateContract,
        *,
        decision_action: str,
        operator_ref: str,
        evidence_refs: list[str],
        rollback_plan_ref: str | None,
        previous_review_status: str | None = None,
        assessed_at: str | None = None,
    ) -> MemoryLifecycleGovernanceAssessmentContract:
        """Govern a human queue decision without authorizing maintenance execution."""

        normalized_action = decision_action.replace("-", "_")
        blockers: list[str] = []
        if candidate.maintenance_action not in {"consolidate", "archive", "expire"}:
            blockers.append("unsupported_memory_maintenance_action")
        if normalized_action not in {"approve", "reject", "needs_review", "rollback"}:
            blockers.append("unsupported_memory_review_action")
        if not self._is_bounded_reference(operator_ref):
            blockers.append("bounded_operator_ref_required")
        if not candidate.target_refs or not candidate.evidence_refs:
            blockers.append("memory_lifecycle_candidate_evidence_required")
        if not candidate.rollback_plan_ref:
            blockers.append("memory_lifecycle_candidate_rollback_required")
        if (
            not candidate.human_review_required
            or candidate.automatic_execution_allowed
            or candidate.core_mutation_allowed
            or candidate.execution_status != "not_executed"
        ):
            blockers.append("memory_lifecycle_candidate_authority_not_allowed")
        if normalized_action in {"approve", "rollback"} and not evidence_refs:
            blockers.append("explicit_review_evidence_required")
        if normalized_action in {"approve", "rollback"} and not rollback_plan_ref:
            blockers.append("explicit_rollback_plan_required")
        if rollback_plan_ref and not self._is_bounded_reference(rollback_plan_ref):
            blockers.append("bounded_rollback_plan_ref_required")
        if normalized_action == "rollback" and previous_review_status != "approved":
            blockers.append("approved_review_required_before_rollback")

        return MemoryLifecycleGovernanceAssessmentContract(
            assessment_id=f"memory-lifecycle-assessment://{uuid4().hex[:12]}",
            candidate_id=candidate.candidate_id,
            maintenance_action=candidate.maintenance_action,
            decision_action=normalized_action,
            status="blocked" if blockers else "governed",
            timestamp=assessed_at or self.now(),
            blockers=blockers,
            conditions=[
                "Persist only the human review decision through canonical memory.",
                "Do not consolidate, archive, expire or delete memory in this review step.",
                "Require a separate governed and reversible maintenance workflow.",
            ],
            policy_refs=[
                "policy://memory-lifecycle/human-review-required",
                "policy://memory-lifecycle/no-autonomous-maintenance",
                "policy://memory-lifecycle/separate-execution-step",
            ],
            human_review_required=True,
            execution_authorized=False,
            automatic_execution_allowed=False,
            core_mutation_allowed=False,
        )

    def assess_memory_influence_policy(
        self,
        decision: MemoryInfluencePolicyDecisionContract,
        *,
        assessed_at: str | None = None,
    ) -> MemoryInfluenceGovernanceAssessmentContract:
        """Fail closed when causal memory use lacks a complete policy trail."""

        blockers: list[str] = []
        if (
            not decision.read_only
            or decision.memory_write_allowed
            or decision.execution_allowed
            or decision.tool_dispatch_allowed
            or decision.automatic_promotion_allowed
            or decision.core_mutation_allowed
        ):
            blockers.append("memory_influence_authority_claim_not_allowed")
        reviewed_playbook_refs = [
            ref for ref in decision.selected_refs if ref.startswith("reviewed-playbook://")
        ]
        if reviewed_playbook_refs and not all(
            ref in decision.version_refs for ref in reviewed_playbook_refs
        ):
            blockers.append("reviewed_procedural_version_trace_required")
        if reviewed_playbook_refs and not all(
            ref in decision.review_decision_refs for ref in reviewed_playbook_refs
        ):
            blockers.append("reviewed_procedural_human_review_trace_required")
        if decision.selected_refs and not all(
            ref in decision.use_reasons for ref in decision.selected_refs
        ):
            blockers.append("memory_influence_selected_reason_required")
        if decision.ignored_refs and not all(
            ref in decision.non_use_reasons for ref in decision.ignored_refs
        ):
            blockers.append("memory_influence_non_use_reason_required")
        if decision.conflict_refs and (
            decision.decision_status != "applied_with_conflict_resolution"
        ):
            blockers.append("memory_influence_conflict_status_mismatch")
        if decision.priority_order != [
            "reviewed_learning",
            "procedural",
            "semantic",
            "reflection",
        ]:
            blockers.append("memory_influence_priority_policy_mismatch")
        if not decision.policy_refs:
            blockers.append("memory_influence_policy_refs_required")
        blockers = list(dict.fromkeys(blockers))
        causal_use_allowed = bool(
            not blockers
            and decision.selected_refs
            and decision.decision_status in {"applied", "applied_with_conflict_resolution"}
        )
        return MemoryInfluenceGovernanceAssessmentContract(
            assessment_id=f"memory-influence-assessment://{uuid4().hex[:12]}",
            assessment_status="governed" if not blockers else "blocked",
            decision_id=decision.decision_id,
            blockers=blockers,
            policy_refs=[
                "policy://governance/memory-influence-trace-required",
                *decision.policy_refs,
            ],
            timestamp=assessed_at or self.now(),
            causal_use_allowed=causal_use_allowed,
            human_review_required=bool(blockers),
            execution_allowed=False,
            tool_dispatch_allowed=False,
        )

    def assess_knowledge_evidence(
        self,
        *,
        provenance_status: str,
        freshness_status: str,
        conflict_status: str,
        source_refs: list[str],
        uncertainty_notes: list[str],
        assessed_at: str | None = None,
    ) -> KnowledgeEvidenceGovernanceContract:
        """Qualify evidence use without changing the request permission decision."""

        status = "evidence_ready"
        use_mode = "bounded_grounding"
        conditions = ["Expose source refs in the observable response trail."]
        blockers: list[str] = []
        human_review_required = False

        if conflict_status == "conflict_detected":
            status = "review_required"
            use_mode = "do_not_assert_as_verified"
            blockers.append("Declared source conflicts require explicit resolution.")
            human_review_required = True
        elif provenance_status == "missing":
            status = "review_required"
            use_mode = "do_not_assert_as_verified"
            blockers.append("Source provenance is missing.")
            human_review_required = True
        elif freshness_status == "stale":
            status = "review_required"
            use_mode = "historical_context_only"
            blockers.append("Source freshness window has expired.")
            human_review_required = True
        elif (
            provenance_status != "complete"
            or freshness_status != "current"
            or conflict_status != "none_declared"
        ):
            status = "conditional_use"
            use_mode = "qualified_grounding"
            conditions.append("Surface uncertainty and avoid unqualified factual claims.")
            human_review_required = True

        if uncertainty_notes:
            conditions.append("Preserve retrieval uncertainty in final synthesis.")

        return KnowledgeEvidenceGovernanceContract(
            assessment_id=f"knowledge-evidence-assessment://{uuid4().hex[:12]}",
            status=status,
            use_mode=use_mode,
            provenance_status=provenance_status,
            freshness_status=freshness_status,
            conflict_status=conflict_status,
            source_refs=list(dict.fromkeys(source_refs)),
            conditions=conditions,
            blockers=blockers,
            uncertainty_notes=list(dict.fromkeys(uncertainty_notes)),
            timestamp=assessed_at or self.now(),
            human_review_required=human_review_required,
            request_decision_mutation_allowed=False,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

    def assess_request(
        self,
        contract: InputContract,
        intent: str,
        requested_by_service: str,
        *,
        plan: DeliberativePlanContract | None = None,
        identity_mode: str | None = None,
        identity_signature: str | None = None,
        response_style: str | None = None,
    ) -> GovernanceAssessment:
        """Build and evaluate a governance check for an incoming request."""

        risk_hint = self.classify_risk(contract, intent)
        proposed_effect = self.proposed_effect(intent=intent, plan=plan)
        continuity_hint = self._continuity_hint(plan)
        request_confirmation_mode = plan.request_confirmation_mode if plan else None
        request_reversibility_mode = plan.request_reversibility_mode if plan else None
        autonomy_action_policy = (
            self.evaluate_plan_autonomy_action(plan) if plan is not None else None
        )
        identity_guardrail = self._identity_guardrail(
            intent=intent,
            proposed_effect=proposed_effect,
            identity_mode=identity_mode,
        )
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="request",
            subject_action=intent,
            scope="session",
            context={
                "content": contract.content,
                "channel": contract.channel.value,
                "input_type": contract.input_type.value,
                "recommended_task_type": plan.recommended_task_type if plan else None,
                "plan_summary": plan.plan_summary if plan else None,
                "capability_decision_status": (plan.capability_decision_status if plan else None),
                "capability_decision_selected_mode": (
                    plan.capability_decision_selected_mode if plan else None
                ),
                "capability_decision_authorization_status": (
                    plan.capability_decision_authorization_status if plan else None
                ),
                "capability_decision_tool_class": (
                    plan.capability_decision_tool_class if plan else None
                ),
                "capability_decision_handoff_mode": (
                    plan.capability_decision_handoff_mode if plan else None
                ),
                "request_identity_status": (plan.request_identity_status if plan else None),
                "request_active_mission": (plan.request_active_mission if plan else None),
                "request_executive_posture": (plan.request_executive_posture if plan else None),
                "request_authority_level": (plan.request_authority_level if plan else None),
                "request_risk_profile": (plan.request_risk_profile if plan else None),
                "request_reversibility_mode": request_reversibility_mode,
                "request_confirmation_mode": request_confirmation_mode,
                "request_identity_summary": (plan.request_identity_summary if plan else None),
                "request_identity_policy_refs": (
                    list(plan.request_identity_policy_refs) if plan else []
                ),
                "requested_autonomy_level": (plan.requested_autonomy_level if plan else None),
                "max_autonomy_level": plan.max_autonomy_level if plan else None,
                "effective_autonomy_level": (plan.effective_autonomy_level if plan else None),
                "autonomy_ladder_status": (plan.autonomy_ladder_status if plan else None),
                "max_autonomy_capability_mode": (
                    plan.max_autonomy_capability_mode if plan else None
                ),
                "autonomy_human_confirmation_required": (
                    plan.autonomy_human_confirmation_required if plan else None
                ),
                "autonomy_confirmation_mode": (plan.autonomy_confirmation_mode if plan else None),
                "autonomy_action_kind": (plan.autonomy_action_kind if plan else None),
                "autonomy_validation_errors": (
                    list(plan.autonomy_validation_errors) if plan else []
                ),
                "autonomy_allowed_runtime_actions": (
                    list(plan.autonomy_allowed_runtime_actions) if plan else []
                ),
                "autonomy_blocked_runtime_actions": (
                    list(plan.autonomy_blocked_runtime_actions) if plan else []
                ),
                "autonomy_policy_refs": (list(plan.autonomy_policy_refs) if plan else []),
                "autonomy_summary": plan.autonomy_summary if plan else None,
                "autonomy_automatic_promotion_allowed": (
                    plan.autonomy_automatic_promotion_allowed if plan else False
                ),
                "autonomy_core_mutation_allowed": (
                    plan.autonomy_core_mutation_allowed if plan else False
                ),
                "autonomy_action_policy_applicable": plan is not None,
                "autonomy_action_policy_decision": (
                    autonomy_action_policy.decision if autonomy_action_policy is not None else None
                ),
                "autonomy_action_policy_reason_codes": (
                    list(autonomy_action_policy.reason_codes)
                    if autonomy_action_policy is not None
                    else []
                ),
                "autonomy_action_side_effect_allowed": (
                    autonomy_action_policy.side_effect_allowed
                    if autonomy_action_policy is not None
                    else False
                ),
                "continuity_replay_status": (plan.continuity_replay_status if plan else None),
                "continuity_recovery_mode": (plan.continuity_recovery_mode if plan else None),
                "continuity_resume_point": (plan.continuity_resume_point if plan else None),
                "identity_mode": identity_mode,
                "identity_signature": identity_signature,
                "response_style": response_style,
                "identity_guardrail": identity_guardrail,
            },
            sensitivity="high" if risk_hint in {RiskLevel.HIGH, RiskLevel.CRITICAL} else "normal",
            reversibility=self._reversibility_level(
                proposed_effect=proposed_effect,
                request_reversibility_mode=request_reversibility_mode,
            ),
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect=proposed_effect,
            risk_hint=risk_hint,
            policy_hint=request_confirmation_mode,
            requested_by_service=requested_by_service,
            declared_risks=list(plan.risks) if plan else [],
            requires_human_validation=bool(plan.requires_human_validation) if plan else False,
            decision_frame=self._decision_frame(plan),
            mission_continuity_hint=continuity_hint,
            open_loops=self._extract_open_loops(plan),
        )
        governance_decision = self.make_decision(governance_check)
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_objective_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_next_action_ref: str | None,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven objective state changes."""

        current_status = current_state.mission_status.value if current_state is not None else None
        current_objective_status = (
            current_state.objective_status if current_state is not None else None
        )
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="objective_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "current_mission_status": current_status,
                "current_objective_status": current_objective_status,
                "requested_next_action_ref": requested_next_action_ref,
                "memory_write_mode": "through_core_only",
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="objective_state_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="objective_transition",
            mission_continuity_hint="operator_bounded_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Transicao operacional bounded permitida pelo nucleo com memoria canonica."
        conditions = [
            "Persistir somente via memoria canonica.",
            "Registrar evento auditavel com estado anterior e novo.",
            "Manter especialistas e automacoes fora da escrita direta.",
        ]
        requires_audit = True
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://objective-transition/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber transicao operacional."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://objective-transition/missing-state"]
        elif requested_transition == "resume" and current_state.mission_status in {
            MissionStatus.COMPLETED,
            MissionStatus.CANCELED,
        }:
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode ser retomada por comando bounded."
            conditions = ["Abrir nova missao ou revisao explicita em vez de reativar estado final."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_resume"
            policy_refs = ["policy://objective-transition/terminal-state"]
        elif requested_transition == "redefine-next-action" and not requested_next_action_ref:
            decision = PermissionDecision.BLOCK
            justification = "Redefinir proxima acao exige referencia explicita."
            conditions = ["Informar --next-action-ref com uma referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_next_action_ref"
            policy_refs = ["policy://objective-transition/missing-next-action"]
        elif requested_next_action_ref and not self._is_bounded_reference(
            requested_next_action_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de proxima acao fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_next_action_ref"
            policy_refs = ["policy://objective-transition/unbounded-reference"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_open_loop_resume(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_open_loop_ref: str,
        loop_state: OpenLoopStateContract | None,
        freshness_status: str,
        selected_work_item_ref: str | None,
        blocking_reasons: list[str],
        evidence_refs: list[str],
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern an explicit cross-session loop selection and resume."""

        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="open_loop_resume",
            subject_action="resume",
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "requested_open_loop_ref": requested_open_loop_ref,
                "freshness_status": freshness_status,
                "selected_work_item_ref": selected_work_item_ref,
                "blocking_reasons": list(blocking_reasons),
                "evidence_refs": list(evidence_refs),
                "memory_write_mode": "through_core_only",
                "autonomous_resume_allowed": False,
                "autonomous_scheduling_allowed": False,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="open_loop_resume",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="explicit_operator_resume",
            mission_continuity_hint="selected_open_loop_resume",
            open_loops=[loop_state.loop_summary] if loop_state else [],
        )
        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Retomada explicita elegivel via Core e memoria canonica."
        conditions = [
            "Registrar selecao, evidencia, checkpoint e proxima acao.",
            "Nao executar ferramenta, work item ou scheduler durante o resume.",
        ]
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://open-loop-resume/explicit-selection"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode retomar open loop."
            conditions = ["Recuperar a missao canonica antes da retomada."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://open-loop-resume/missing-state"]
        elif not self._is_bounded_reference(requested_open_loop_ref):
            decision = PermissionDecision.BLOCK
            justification = "Open loop ref fora do formato bounded permitido."
            conditions = ["Selecionar uma ref retornada por open-loops."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_open_loop_ref"
            policy_refs = ["policy://open-loop-resume/unbounded-reference"]
        elif loop_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Open loop selecionado nao existe na missao canonica."
            conditions = ["Listar open-loops e selecionar uma ref existente."]
            requires_rollback_plan = True
            containment_hint = "block_missing_open_loop"
            policy_refs = ["policy://open-loop-resume/missing-loop"]
        elif not evidence_refs:
            decision = PermissionDecision.BLOCK
            justification = "Retomada sem evidencia de estado canonico."
            conditions = ["Recalcular elegibilidade a partir do estado da missao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_resume_evidence"
            policy_refs = ["policy://open-loop-resume/missing-evidence"]
        elif blocking_reasons:
            decision = PermissionDecision.BLOCK
            justification = "Open loop nao esta elegivel para retomada."
            conditions = [*blocking_reasons]
            requires_rollback_plan = True
            containment_hint = "block_open_loop_resume_conflict"
            policy_refs = ["policy://open-loop-resume/revalidation"]
        elif selected_work_item_ref and selected_work_item_ref not in {
            item.work_item_ref
            for item in refresh_work_item_blocking_states(
                canonical_work_items_from_mission(current_state)
            )
            if item.work_item_status == "active" and item.blocking_state == "ready"
        }:
            decision = PermissionDecision.BLOCK
            justification = "Work item selecionado deixou de estar executavel."
            conditions = ["Recalcular a fila governada antes de retomar."]
            requires_rollback_plan = True
            containment_hint = "block_stale_resume_work_item"
            policy_refs = ["policy://open-loop-resume/work-item-readiness"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_work_item_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_work_item_ref: str | None,
        requested_next_action_ref: str | None,
        requested_by_service: str,
        requested_dependency_refs: list[str] | None = None,
        requested_priority_level: str | None = None,
        requested_blocker_refs: list[str] | None = None,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven work item state changes."""

        current_status = current_state.mission_status.value if current_state is not None else None
        existing_refs = set(current_state.work_item_refs if current_state else [])
        active_refs = set(current_state.active_work_items if current_state else [])
        current_items = canonical_work_items_from_mission(current_state)
        current_item = next(
            (item for item in current_items if item.work_item_ref == requested_work_item_ref),
            None,
        )
        effective_dependency_refs = (
            list(requested_dependency_refs)
            if requested_dependency_refs is not None
            else list(current_item.dependency_refs)
            if current_item
            else []
        )
        effective_priority_level = requested_priority_level or (
            current_item.priority_level if current_item else "p2"
        )
        blocker_refs = list(requested_blocker_refs or [])
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="work_item_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "current_mission_status": current_status,
                "requested_work_item_ref": requested_work_item_ref,
                "requested_next_action_ref": requested_next_action_ref,
                "requested_dependency_refs": effective_dependency_refs,
                "requested_priority_level": effective_priority_level,
                "requested_blocker_refs": blocker_refs,
                "existing_work_item_count": len(existing_refs),
                "active_work_item_count": len(active_refs),
                "memory_write_mode": "through_core_only",
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="work_item_state_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="work_item_transition",
            mission_continuity_hint="operator_bounded_work_item_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Transicao bounded de work item permitida via nucleo e memoria canonica."
        conditions = [
            "Persistir somente via MissionStateContract canonico.",
            "Registrar evento auditavel com work item, transicao e checkpoint.",
            "Nao executar ou agendar o work item automaticamente.",
        ]
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://work-item-transition/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber work item."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://work-item-transition/missing-state"]
        elif current_state.mission_status in {MissionStatus.COMPLETED, MissionStatus.CANCELED}:
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode receber mutacao de work item."
            conditions = ["Abrir nova missao ou revisao explicita antes de alterar tarefas."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_mission"
            policy_refs = ["policy://work-item-transition/terminal-state"]
        elif not requested_work_item_ref:
            decision = PermissionDecision.BLOCK
            justification = "Transicao de work item exige referencia explicita."
            conditions = ["Informar --work-item-ref com referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_work_item_ref"
            policy_refs = ["policy://work-item-transition/missing-work-item-ref"]
        elif not self._is_bounded_reference(requested_work_item_ref):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de work item fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_work_item_ref"
            policy_refs = ["policy://work-item-transition/unbounded-reference"]
        elif requested_next_action_ref and not self._is_bounded_reference(
            requested_next_action_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de proxima acao fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_next_action_ref"
            policy_refs = ["policy://work-item-transition/unbounded-next-action"]
        elif any(
            not self._is_bounded_reference(item)
            for item in [*effective_dependency_refs, *blocker_refs]
        ):
            decision = PermissionDecision.BLOCK
            justification = "Dependencia ou blocker fora do formato bounded permitido."
            conditions = ["Usar somente referencias bounded sem caracteres de controle."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_work_item_relation"
            policy_refs = ["policy://work-item-transition/unbounded-relation"]
        elif effective_priority_level not in WORK_ITEM_PRIORITY_LEVELS:
            decision = PermissionDecision.BLOCK
            justification = "Prioridade de work item fora da escala governada."
            conditions = ["Usar uma prioridade entre p0, p1, p2 ou p3."]
            requires_rollback_plan = True
            containment_hint = "block_invalid_work_item_priority"
            policy_refs = ["policy://work-item-transition/invalid-priority"]
        elif requested_transition not in {"create", "update"} and (
            requested_dependency_refs is not None or requested_priority_level is not None
        ):
            decision = PermissionDecision.BLOCK
            justification = "Dependencias e prioridade so mudam por create ou update."
            conditions = ["Separar a alteracao estrutural da transicao de lifecycle."]
            requires_rollback_plan = True
            containment_hint = "block_metadata_outside_create_update"
            policy_refs = ["policy://work-item-transition/metadata-scope"]
        elif requested_transition == "block" and not blocker_refs:
            decision = PermissionDecision.BLOCK
            justification = "Bloqueio de work item exige causa explicita."
            conditions = ["Informar ao menos um --blocker-ref bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_blocker_ref"
            policy_refs = ["policy://work-item-transition/missing-blocker"]
        elif requested_transition != "block" and blocker_refs:
            decision = PermissionDecision.BLOCK
            justification = "Blocker explicito so pode ser declarado pela transicao block."
            conditions = ["Usar block para registrar causa ou resume para limpa-la."]
            requires_rollback_plan = True
            containment_hint = "block_blocker_outside_block_transition"
            policy_refs = ["policy://work-item-transition/blocker-scope"]
        elif (
            transition_error := validate_work_item_transition(
                current_status=(current_item.work_item_status if current_item else None),
                requested_transition=requested_transition,
            )
        ) is not None:
            decision = PermissionDecision.BLOCK
            justification = f"Transicao de work item invalida: {transition_error}."
            conditions = ["Aplicar uma transicao valida para o estado canonico atual."]
            requires_rollback_plan = True
            containment_hint = f"block_{transition_error.replace(':', '_')}"
            policy_refs = ["policy://work-item-transition/state-machine"]
        elif requested_transition in {"create", "update"} and (
            graph_errors := validate_work_item_graph(
                current_items,
                work_item_ref=str(requested_work_item_ref),
                dependency_refs=effective_dependency_refs,
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Grafo de dependencias de work item invalido."
            conditions = [*graph_errors]
            requires_rollback_plan = True
            containment_hint = "block_invalid_work_item_graph"
            policy_refs = ["policy://work-item-transition/dependency-graph"]
        elif (
            requested_transition in {"resume", "complete"}
            and current_item
            and (unresolved := unresolved_dependency_refs(current_item, current_items))
        ):
            decision = PermissionDecision.BLOCK
            justification = "Work item possui dependencias ainda nao concluidas."
            conditions = [f"complete_dependency:{item}" for item in unresolved]
            requires_rollback_plan = True
            containment_hint = "block_unresolved_work_item_dependencies"
            policy_refs = ["policy://work-item-transition/dependency-readiness"]
        elif requested_transition == "redefine-next-action" and not requested_next_action_ref:
            decision = PermissionDecision.BLOCK
            justification = "Redefinir proxima acao exige referencia explicita."
            conditions = ["Informar --next-action-ref com uma referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_next_action_ref"
            policy_refs = ["policy://work-item-transition/missing-next-action"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_artifact_lifecycle_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_artifact_ref: str | None,
        requested_artifact_version: int | None,
        requested_work_item_ref: str | None,
        requested_replacement_artifact_ref: str | None,
        requested_rollback_plan_ref: str | None,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven artifact lifecycle changes."""

        artifact_states = canonical_artifact_states_from_mission(current_state)
        current_artifact = next(
            (item for item in artifact_states if item.artifact_ref == requested_artifact_ref),
            None,
        )
        existing_refs = {item.artifact_ref for item in artifact_states}
        active_refs = set(current_state.active_artifact_refs if current_state else [])
        effective_work_item_ref = requested_work_item_ref or (
            current_artifact.work_item_ref if current_artifact else None
        )
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="artifact_lifecycle_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "requested_artifact_ref": requested_artifact_ref,
                "requested_artifact_version": requested_artifact_version,
                "requested_work_item_ref": requested_work_item_ref,
                "requested_replacement_artifact_ref": requested_replacement_artifact_ref,
                "requested_rollback_plan_ref": requested_rollback_plan_ref,
                "existing_artifact_count": len(existing_refs),
                "active_artifact_count": len(active_refs),
                "memory_write_mode": "through_core_only",
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="artifact_lifecycle_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="artifact_lifecycle_transition",
            mission_continuity_hint="operator_bounded_artifact_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Transicao bounded de artefato permitida via memoria canonica."
        conditions = [
            "Persistir somente via MissionStateContract canonico.",
            "Registrar evento auditavel com artefato, transicao e checkpoint.",
            "Nao ler, mover, deletar ou editar arquivos reais nesta transicao.",
        ]
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://artifact-lifecycle/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber artefato."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://artifact-lifecycle/missing-state"]
        elif current_state.mission_status in {MissionStatus.COMPLETED, MissionStatus.CANCELED}:
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode receber mutacao de artefato."
            conditions = ["Abrir nova missao ou revisao explicita antes de alterar artefatos."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_mission"
            policy_refs = ["policy://artifact-lifecycle/terminal-state"]
        elif not requested_artifact_ref:
            decision = PermissionDecision.BLOCK
            justification = "Transicao de artefato exige referencia explicita."
            conditions = ["Informar --artifact-ref com referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_artifact_ref"
            policy_refs = ["policy://artifact-lifecycle/missing-artifact-ref"]
        elif not self._is_bounded_reference(requested_artifact_ref):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de artefato fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como artifact://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_artifact_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-reference"]
        elif requested_replacement_artifact_ref and not self._is_bounded_reference(
            requested_replacement_artifact_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de substituicao fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como artifact://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_replacement_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-replacement"]
        elif requested_rollback_plan_ref and not self._is_bounded_reference(
            requested_rollback_plan_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de rollback fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como rollback://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_rollback_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-rollback"]
        elif requested_work_item_ref and not self._is_bounded_reference(requested_work_item_ref):
            decision = PermissionDecision.BLOCK
            justification = "Source work item fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded de work item."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_artifact_work_item"
            policy_refs = ["policy://artifact-lifecycle/unbounded-work-item"]
        elif (
            transition_error := validate_artifact_transition(
                current_status=(current_artifact.artifact_status if current_artifact else None),
                requested_transition=requested_transition,
            )
        ) is not None:
            decision = PermissionDecision.BLOCK
            justification = f"Transicao de artefato invalida: {transition_error}."
            conditions = ["Aplicar uma transicao valida ao estado canonico atual."]
            requires_rollback_plan = True
            containment_hint = f"block_{transition_error.replace(':', '_')}"
            policy_refs = ["policy://artifact-lifecycle/state-machine"]
        elif (
            version_error := validate_artifact_version(
                requested_transition=requested_transition,
                requested_version=requested_artifact_version,
                current_version=(current_artifact.artifact_version if current_artifact else None),
            )
        ) is not None:
            decision = PermissionDecision.BLOCK
            justification = f"Versao de artefato invalida: {version_error}."
            conditions = ["Preservar versoes positivas, sequenciais e imutaveis."]
            requires_rollback_plan = True
            containment_hint = f"block_{version_error}"
            policy_refs = ["policy://artifact-lifecycle/immutable-version"]
        elif requested_transition in {"register", "replace"} and not effective_work_item_ref:
            decision = PermissionDecision.BLOCK
            justification = "Nova versao de artefato exige source work item explicito."
            conditions = ["Informar --work-item-ref pertencente a missao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_artifact_work_item"
            policy_refs = ["policy://artifact-lifecycle/source-work-item"]
        elif effective_work_item_ref and effective_work_item_ref not in {
            item.work_item_ref for item in canonical_work_items_from_mission(current_state)
        }:
            decision = PermissionDecision.BLOCK
            justification = "Source work item nao pertence ao estado canonico da missao."
            conditions = ["Criar ou selecionar um work item canonico da mesma missao."]
            requires_rollback_plan = True
            containment_hint = "block_unknown_artifact_work_item"
            policy_refs = ["policy://artifact-lifecycle/source-work-item"]
        elif requested_transition not in {"register", "replace"} and requested_work_item_ref:
            decision = PermissionDecision.BLOCK
            justification = "Source work item de uma versao existente e imutavel."
            conditions = ["Definir source work item somente em register ou replace."]
            requires_rollback_plan = True
            containment_hint = "block_immutable_artifact_work_item"
            policy_refs = ["policy://artifact-lifecycle/immutable-ownership"]
        elif requested_transition in {"activate", "archive"} and requested_rollback_plan_ref:
            decision = PermissionDecision.BLOCK
            justification = "Rollback ref nao altera metadata de versao existente."
            conditions = ["Remover rollback ref desta transicao de lifecycle."]
            requires_rollback_plan = True
            containment_hint = "block_immutable_artifact_rollback_metadata"
            policy_refs = ["policy://artifact-lifecycle/immutable-version"]
        elif requested_transition == "replace" and not requested_replacement_artifact_ref:
            decision = PermissionDecision.BLOCK
            justification = "Substituir artefato exige referencia de substituicao."
            conditions = ["Informar --replacement-artifact-ref."]
            requires_rollback_plan = True
            containment_hint = "block_missing_replacement_ref"
            policy_refs = ["policy://artifact-lifecycle/missing-replacement"]
        elif requested_transition == "replace" and not requested_rollback_plan_ref:
            decision = PermissionDecision.BLOCK
            justification = "Substituir artefato exige rollback ref explicita."
            conditions = ["Informar --rollback-plan-ref bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_replacement_rollback"
            policy_refs = ["policy://artifact-lifecycle/missing-rollback"]
        elif requested_transition != "replace" and requested_replacement_artifact_ref:
            decision = PermissionDecision.BLOCK
            justification = "Replacement ref so pode ser usada pela transicao replace."
            conditions = ["Remover replacement ref ou usar replace."]
            requires_rollback_plan = True
            containment_hint = "block_replacement_outside_replace"
            policy_refs = ["policy://artifact-lifecycle/replacement-scope"]
        elif requested_transition == "replace" and (
            lineage_errors := validate_artifact_lineage(
                artifact_states,
                artifact_ref=str(requested_artifact_ref),
                replacement_artifact_ref=requested_replacement_artifact_ref,
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Linhagem de substituicao de artefato invalida."
            conditions = [*lineage_errors]
            requires_rollback_plan = True
            containment_hint = "block_invalid_artifact_lineage"
            policy_refs = ["policy://artifact-lifecycle/lineage"]
        elif requested_transition == "rollback" and not requested_rollback_plan_ref:
            decision = PermissionDecision.BLOCK
            justification = "Rollback exige referencia de plano explicita."
            conditions = ["Informar --rollback-plan-ref bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_rollback_ref"
            policy_refs = ["policy://artifact-lifecycle/missing-rollback"]
        elif (
            requested_transition == "rollback"
            and current_artifact
            and not (current_artifact.replacement_artifact_ref)
        ):
            decision = PermissionDecision.BLOCK
            justification = "Artefato sem sucessor canonico nao pode receber rollback."
            conditions = ["Selecionar uma versao superseded com sucessor registrado."]
            requires_rollback_plan = True
            containment_hint = "block_missing_rollback_successor"
            policy_refs = ["policy://artifact-lifecycle/rollback-lineage"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    @staticmethod
    def _is_bounded_reference(value: str) -> bool:
        if not value or len(value) > 160:
            return False
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:/._-")
        return all(character in allowed for character in value)

    def assess_operator_feedback(
        self,
        *,
        contract: InputContract,
        feedback: OperatorFeedbackContract,
        experience_mission_id: str | None,
        reflection_available: bool,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern an explicit bounded post-mission operator feedback write."""

        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="operator_feedback",
            subject_action="record",
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "experience_id": feedback.experience_id,
                "experience_mission_id": experience_mission_id,
                "reflection_available": reflection_available,
                "assessment": feedback.assessment,
                "rating": feedback.rating,
                "comment_length": len(feedback.comment or ""),
                "correction_length": len(feedback.correction or ""),
                "next_expectation_length": len(feedback.next_expectation or ""),
                "evidence_ref_count": len(feedback.evidence_refs),
                "memory_write_mode": feedback.memory_write_mode,
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
                "automatic_promotion_allowed": feedback.automatic_promotion_allowed,
                "core_mutation_allowed": feedback.core_mutation_allowed,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="append_bounded_operator_feedback",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="operator_feedback_write",
            mission_continuity_hint="post_mission_operator_learning",
        )
        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Feedback explicito bounded permitido via nucleo e memoria canonica."
        conditions = [
            "Persistir o feedback somente via experiencia/reflexao canonica.",
            "Enviar qualquer proposta evolutiva para revisao humana.",
            "Nao autorizar promocao automatica ou mutacao do nucleo.",
        ]
        containment_hint = None
        policy_refs = ["policy://operator-feedback/bounded-core-write"]

        if experience_mission_id is None:
            decision = PermissionDecision.BLOCK
            justification = "Feedback exige experiencia canonica existente."
            containment_hint = "block_missing_experience"
            policy_refs = ["policy://operator-feedback/missing-experience"]
        elif str(contract.mission_id) != experience_mission_id:
            decision = PermissionDecision.BLOCK
            justification = "Experiencia nao pertence a missao informada."
            containment_hint = "block_experience_mission_mismatch"
            policy_refs = ["policy://operator-feedback/mission-mismatch"]
        elif not reflection_available:
            decision = PermissionDecision.BLOCK
            justification = "Feedback pos-missao exige reflexao canonica existente."
            containment_hint = "block_missing_reflection"
            policy_refs = ["policy://operator-feedback/missing-reflection"]
        elif feedback.assessment not in {
            "helpful",
            "partially_helpful",
            "not_helpful",
            "correction",
        }:
            decision = PermissionDecision.BLOCK
            justification = "Assessment de feedback nao suportado."
            containment_hint = "block_unsupported_assessment"
            policy_refs = ["policy://operator-feedback/unsupported-assessment"]
        elif feedback.rating is not None and (
            isinstance(feedback.rating, bool) or feedback.rating < 1 or feedback.rating > 5
        ):
            decision = PermissionDecision.BLOCK
            justification = "Rating deve estar entre 1 e 5."
            containment_hint = "block_invalid_rating"
            policy_refs = ["policy://operator-feedback/invalid-rating"]
        elif feedback.assessment == "correction" and not feedback.correction:
            decision = PermissionDecision.BLOCK
            justification = "Feedback corretivo exige texto de correcao."
            containment_hint = "block_missing_correction"
            policy_refs = ["policy://operator-feedback/missing-correction"]
        elif any(
            len(value or "") > limit
            for value, limit in (
                (feedback.comment, 1000),
                (feedback.correction, 1000),
                (feedback.next_expectation, 500),
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Conteudo de feedback excede os limites bounded."
            containment_hint = "block_unbounded_feedback_content"
            policy_refs = ["policy://operator-feedback/unbounded-content"]
        elif not all(
            self._is_bounded_reference(value)
            for value in (
                feedback.feedback_id,
                feedback.experience_id,
                feedback.operator_ref,
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencias de feedback fora do formato bounded."
            containment_hint = "block_unbounded_feedback_reference"
            policy_refs = ["policy://operator-feedback/unbounded-reference"]
        elif len(feedback.evidence_refs) > 20 or any(
            not self._is_bounded_reference(value) for value in feedback.evidence_refs
        ):
            decision = PermissionDecision.BLOCK
            justification = "Evidence refs de feedback fora do formato bounded."
            containment_hint = "block_unbounded_feedback_evidence"
            policy_refs = ["policy://operator-feedback/unbounded-evidence"]
        elif feedback.memory_write_mode != "through_core_only":
            decision = PermissionDecision.BLOCK
            justification = "Feedback deve ser persistido somente pelo nucleo."
            containment_hint = "block_feedback_memory_bypass"
            policy_refs = ["policy://operator-feedback/core-write-required"]
        elif feedback.automatic_promotion_allowed or feedback.core_mutation_allowed:
            decision = PermissionDecision.BLOCK
            justification = "Feedback nao pode autorizar promocao ou mutacao autonoma."
            containment_hint = "block_autonomous_feedback_mutation"
            policy_refs = ["policy://operator-feedback/no-autonomous-mutation"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=False,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_specialist_handoff(
        self,
        *,
        contract: InputContract,
        plan: DeliberativePlanContract,
        selections: list[SpecialistSelectionContract],
        invocations: list[SpecialistInvocationContract],
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Evaluate internal specialist handoffs before executing them."""

        selected = [item for item in selections if item.selection_status == "selected"]
        invalid_boundary = any(
            invocation.boundary.response_channel != "through_core"
            or invocation.boundary.tool_access_mode != "none"
            or invocation.boundary.memory_write_mode != "through_core_only"
            for invocation in invocations
        )
        requires_review = any(item.requires_governance_review for item in selected)
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="specialist_handoff",
            subject_action="dispatch",
            scope="session",
            context={
                "selected_specialists": [item.specialist_type for item in selected],
                "selection_statuses": {
                    item.specialist_type: item.selection_status for item in selections
                },
                "selected_invocation_ids": [item.invocation_id for item in selected],
                "response_channels": [
                    invocation.boundary.response_channel for invocation in invocations
                ],
                "tool_access_modes": [
                    invocation.boundary.tool_access_mode for invocation in invocations
                ],
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="internal_specialist_handoff",
            risk_hint=RiskLevel.MODERATE if selected else RiskLevel.LOW,
            requested_by_service=requested_by_service,
            declared_risks=list(plan.risks),
            requires_human_validation=False,
            decision_frame="specialist_handoff",
            mission_continuity_hint=self._continuity_hint(plan),
            open_loops=self._extract_open_loops(plan),
        )

        decision = PermissionDecision.ALLOW
        justification = "Convocacao interna de especialista permanece subordinada e rastreavel."
        conditions: list[str] = []
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://specialist-handoff/default"]

        if invalid_boundary:
            decision = PermissionDecision.BLOCK
            justification = (
                "A convocacao proposta viola a fronteira interna permitida para especialistas."
            )
            conditions = [
                "Especialista deve responder apenas pelo nucleo.",
                "Especialista nao pode acessar tools ou memoria fora das fronteiras internas.",
            ]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_invalid_specialist_boundary"
            policy_refs = ["policy://specialist-handoff/boundary-block"]
        elif selected and (
            requires_review
            or plan.continuity_recovery_mode in {"governed_review", "contained_recovery"}
            or plan.requires_human_validation
        ):
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = (
                "Convocacao interna permitida com trilha reforcada e limites explicitos "
                "de handoff subordinado."
            )
            conditions = [
                "Especialista nao responde diretamente ao usuario.",
                "Toda saida deve retornar ao nucleo por canal interno estruturado.",
                "Nao executar tools nem escrita direta de memoria no especialista.",
            ]
            requires_audit = True
            policy_refs = ["policy://specialist-handoff/allow-with-conditions"]
        elif not selected:
            justification = "Nenhum especialista ficou elegivel para convocacao nesta rodada."
            policy_refs = ["policy://specialist-handoff/no-selection"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def classify_risk(self, contract: InputContract, intent: str) -> RiskLevel:
        """Classify the current request using a deterministic policy matrix."""

        content = contract.content.lower()
        if intent == "sensitive_action":
            return RiskLevel.HIGH
        if any(keyword in content for keyword in HIGH_RISK_KEYWORDS):
            return RiskLevel.HIGH
        if any(keyword in content for keyword in MODERATE_RISK_KEYWORDS):
            return RiskLevel.MODERATE
        return RiskLevel.LOW

    def make_decision(
        self,
        governance_check: GovernanceCheckContract,
    ) -> GovernanceDecisionContract:
        """Produce the v1 governance decision for request handling."""

        risk_level = governance_check.risk_hint or RiskLevel.LOW
        decision = PermissionDecision.ALLOW
        justification = "Solicitacao reversivel e coerente com a missao ativa do v1."
        conditions: list[str] = []
        policy_refs = ["policy://request/default-low-risk"]
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None
        proposed_effect = governance_check.proposed_effect or "analysis_or_guidance_only"
        open_loops = list(governance_check.open_loops)
        continuity_hint = governance_check.mission_continuity_hint or "sem_continuidade"
        decision_frame = governance_check.decision_frame or "analysis"
        request_confirmation_mode = governance_check.context.get("request_confirmation_mode")
        autonomy_action_policy = self._autonomy_action_policy_decision(governance_check)
        autonomy_violation = self._autonomy_ladder_violation(governance_check)

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            decision = PermissionDecision.BLOCK
            justification = "Potencial destrutivo detectado; a execucao direta foi bloqueada."
            conditions = ["Exigir validacao forte fora do fluxo normal antes de qualquer acao."]
            policy_refs = ["policy://request/high-risk"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_direct_execution"
        elif autonomy_violation == "forbidden_autonomy_claim":
            decision = PermissionDecision.BLOCK
            justification = (
                "O contrato de autonomia tentou permitir autopromocao ou mutacao "
                "do nucleo, o que e proibido."
            )
            conditions = [
                "Manter automatic_promotion_allowed=false.",
                "Manter core_mutation_allowed=false.",
            ]
            policy_refs = ["policy://autonomy-ladder/forbidden-claim"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_forbidden_autonomy_claim"
        elif autonomy_violation == "capability_above_autonomy_limit":
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            justification = (
                "A capability selecionada excede o nivel maximo de autonomia "
                "permitido para a request/missao."
            )
            conditions = [
                "Rebaixar a capability ao max_autonomy_capability_mode.",
                "Solicitar confirmacao humana antes de qualquer execucao acima do limite.",
                "Registrar o limite aplicado em eventos e console.",
            ]
            policy_refs = ["policy://autonomy-ladder/enforce-max-capability"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "defer_capability_above_autonomy_limit"
        elif autonomy_action_policy is not None and autonomy_action_policy.decision == "block":
            decision = PermissionDecision.BLOCK
            justification = (
                "A projecao de autonomia da acao e ausente, desconhecida ou "
                "incompativel; nenhum efeito pode ser preparado."
            )
            conditions = [
                "Corrigir o contrato de autonomia antes de preparar a acao.",
                *[
                    f"Resolver bloqueio de autonomia: {reason}."
                    for reason in autonomy_action_policy.reason_codes
                ],
            ]
            policy_refs = ["policy://autonomy-action/fail-closed"]
            requires_audit = True
            containment_hint = "block_autonomy_action"
        elif self._should_defer(governance_check, proposed_effect, open_loops, continuity_hint):
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            if continuity_hint == "checkpoint_contido":
                justification = (
                    "A retomada parte de checkpoint contido e exige revisao explicita "
                    "antes de qualquer continuidade."
                )
            elif continuity_hint == "checkpoint_aguarda_validacao":
                justification = (
                    "O checkpoint recuperado ainda aguarda validacao e nao pode ser "
                    "retomado automaticamente."
                )
            elif continuity_hint == "retomada_relacionada":
                justification = (
                    "A retomada relacionada disputa direcao com loop ainda aberto e exige "
                    "validacao explicita."
                )
            else:
                justification = (
                    "O plano atual tenta ampliar ou reformular o escopo com "
                    "loop critico ainda aberto."
                )
            conditions = [
                "Manter apenas analise e rastreabilidade ate revisao explicita.",
                "Nao ampliar objetivo enquanto houver loop aberto relevante.",
            ]
            policy_refs = ["policy://request/defer-mission-reframe"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "defer_open_loop_reframe"
        elif (
            autonomy_action_policy is not None
            and autonomy_action_policy.decision == "require_confirmation"
        ):
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = (
                "A acao pode somente ser preparada para confirmacao humana exata; "
                "a evidencia ainda nao autoriza efeito."
            )
            conditions = [
                "Preparar challenge vinculado a acao exata.",
                "Exigir claim valido antes de emitir qualquer efeito operacional.",
            ]
            policy_refs = ["policy://autonomy-action/exact-confirmation"]
            requires_audit = True
            containment_hint = "prepare_exact_action_confirmation"
        elif self._should_allow_with_conditions(
            proposed_effect=proposed_effect,
            risk_level=risk_level,
            decision_frame=decision_frame,
            open_loops=open_loops,
        ):
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = "Operacao local segura permitida com rastreabilidade reforcada."
            conditions = [
                "Manter trilha de eventos completa.",
                "Restringir a artefatos locais e reversiveis.",
            ]
            if request_confirmation_mode == "explicit_confirmation_required":
                conditions.append("Nao ampliar a autonomia sem confirmacao explicita do operador.")
            if open_loops:
                conditions.append(
                    "Fechar explicitamente o loop principal da missao nesta resposta."
                )
            policy_refs = ["policy://request/local-safe-operation"]
            requires_audit = True
        elif decision_frame == "analysis":
            decision = PermissionDecision.ALLOW
            justification = "Analise reversivel permitida com continuidade coerente."
            policy_refs = ["policy://request/reversible-analysis"]

        return GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=risk_level,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            conditions=conditions,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )

    @staticmethod
    def _autonomy_ladder_violation(
        governance_check: GovernanceCheckContract,
    ) -> str | None:
        context = governance_check.context
        if context.get("autonomy_automatic_promotion_allowed") is True:
            return "forbidden_autonomy_claim"
        if context.get("autonomy_core_mutation_allowed") is True:
            return "forbidden_autonomy_claim"
        policy_decision = GovernanceService._autonomy_action_policy_decision(governance_check)
        if policy_decision is not None and (
            "capability_above_autonomy_limit" in policy_decision.reason_codes
        ):
            return "capability_above_autonomy_limit"
        return None

    @staticmethod
    def evaluate_plan_autonomy_action(
        plan: DeliberativePlanContract,
        *,
        confirmation_evidence_state: str = "absent",
    ) -> AutonomyActionPolicyDecisionContract:
        """Evaluate the exact action projected by one materialized plan."""

        return evaluate_autonomy_action(
            requested_autonomy_level=plan.requested_autonomy_level,
            max_autonomy_level=plan.max_autonomy_level,
            effective_autonomy_level=plan.effective_autonomy_level,
            autonomy_ladder_status=plan.autonomy_ladder_status,
            action_kind=plan.autonomy_action_kind,
            selected_capability_mode=plan.capability_decision_selected_mode,
            max_capability_mode=plan.max_autonomy_capability_mode,
            allowed_runtime_actions=plan.autonomy_allowed_runtime_actions,
            blocked_runtime_actions=plan.autonomy_blocked_runtime_actions,
            human_confirmation_required=(plan.autonomy_human_confirmation_required),
            human_confirmation_mode=plan.autonomy_confirmation_mode,
            confirmation_evidence_state=confirmation_evidence_state,
            autonomy_validation_errors=plan.autonomy_validation_errors,
        )

    @staticmethod
    def _autonomy_action_policy_decision(
        governance_check: GovernanceCheckContract,
    ) -> AutonomyActionPolicyDecisionContract | None:
        context = governance_check.context
        if context.get("autonomy_action_policy_applicable") is not True:
            return None

        def text_value(name: str) -> str | None:
            value = context.get(name)
            return value if isinstance(value, str) else None

        def string_sequence(name: str) -> list[str] | tuple[str, ...] | None:
            value = context.get(name)
            if isinstance(value, (list, tuple)):
                return value
            return None

        confirmation_required = context.get("autonomy_human_confirmation_required")
        return evaluate_autonomy_action(
            requested_autonomy_level=text_value("requested_autonomy_level"),
            max_autonomy_level=text_value("max_autonomy_level"),
            effective_autonomy_level=text_value("effective_autonomy_level"),
            autonomy_ladder_status=text_value("autonomy_ladder_status"),
            action_kind=text_value("autonomy_action_kind"),
            selected_capability_mode=text_value("capability_decision_selected_mode"),
            max_capability_mode=text_value("max_autonomy_capability_mode"),
            allowed_runtime_actions=string_sequence("autonomy_allowed_runtime_actions"),
            blocked_runtime_actions=string_sequence("autonomy_blocked_runtime_actions"),
            human_confirmation_required=(
                confirmation_required if isinstance(confirmation_required, bool) else None
            ),
            human_confirmation_mode=text_value("autonomy_confirmation_mode"),
            confirmation_evidence_state="absent",
            autonomy_validation_errors=string_sequence("autonomy_validation_errors"),
        )

    @staticmethod
    def proposed_effect(intent: str, plan: DeliberativePlanContract | None) -> str:
        if intent == "sensitive_action":
            return "external_or_sensitive_change"
        if plan is None:
            return "analysis_or_guidance_only"
        if plan.capability_decision_selected_mode == "core_with_local_operation":
            return "local_safe_operation"
        if plan.capability_decision_selected_mode in {
            "clarification_only",
            "contained_guidance",
        }:
            return "analysis_or_guidance_only"
        if plan.requires_human_validation:
            return "external_or_sensitive_change"
        if plan.recommended_task_type in {"draft_plan", "general_response"}:
            return "local_safe_operation"
        return "analysis_or_guidance_only"

    @staticmethod
    def _decision_frame(plan: DeliberativePlanContract | None) -> str | None:
        if not plan:
            return None
        if plan.recommended_task_type == "produce_analysis_brief":
            return "analysis"
        if plan.recommended_task_type == "draft_plan":
            return "planning"
        if plan.recommended_task_type == "general_response" and plan.requires_human_validation:
            return "clarification"
        return "execution" if plan.smallest_safe_next_action else "planning"

    @staticmethod
    def _extract_open_loops(plan: DeliberativePlanContract | None) -> list[str]:
        if not plan:
            return []
        return list(plan.open_loops[:3])

    @staticmethod
    def _continuity_hint(plan: DeliberativePlanContract | None) -> str | None:
        if not plan:
            return None
        if plan.continuity_recovery_mode == "governed_review":
            return "checkpoint_aguarda_validacao"
        if plan.continuity_recovery_mode == "contained_recovery":
            return "checkpoint_contido"
        if plan.continuity_action == "reformular":
            return "reformulacao_de_objetivo"
        if plan.continuity_action == "retomar":
            return "retomada_relacionada"
        if plan.continuity_action == "continuar":
            return "continuidade_coerente"
        if plan.continuity_action == "encerrar":
            return "fechamento_de_loop"
        return None

    @staticmethod
    def _identity_guardrail(
        *,
        intent: str,
        proposed_effect: str,
        identity_mode: str | None,
    ) -> str:
        mode = identity_mode or "executive_guidance"
        if mode == "governed_refusal" or proposed_effect == "external_or_sensitive_change":
            return "preservar limites do nucleo antes de ampliar acao"
        if intent == "analysis":
            return "preservar rigor analitico antes de concluir"
        if intent == "planning":
            return "preservar unidade executiva e rastreabilidade do plano"
        return "preservar coerencia do nucleo e utilidade controlada"

    @staticmethod
    def _should_defer(
        governance_check: GovernanceCheckContract,
        proposed_effect: str,
        open_loops: list[str],
        continuity_hint: str,
    ) -> bool:
        if governance_check.requires_human_validation:
            return True
        if proposed_effect == "external_or_sensitive_change":
            return True
        if continuity_hint in {"checkpoint_aguarda_validacao", "checkpoint_contido"}:
            return True
        if continuity_hint == "retomada_relacionada" and bool(open_loops):
            return True
        if continuity_hint == "reformulacao_de_objetivo" and bool(open_loops):
            return True
        return False

    @staticmethod
    def _should_allow_with_conditions(
        *,
        proposed_effect: str,
        risk_level: RiskLevel,
        decision_frame: str,
        open_loops: list[str],
    ) -> bool:
        if proposed_effect == "local_safe_operation" and decision_frame in {
            "planning",
            "execution",
        }:
            return True
        if risk_level == RiskLevel.MODERATE:
            return True
        return decision_frame == "execution" and bool(open_loops)

    @staticmethod
    def _reversibility_level(
        *,
        proposed_effect: str,
        request_reversibility_mode: str | None,
    ) -> str:
        if request_reversibility_mode == "prefer_reversible_change":
            return "high"
        if proposed_effect == "external_or_sensitive_change":
            return "low"
        return "high"

    def assess_memory_operation(
        self,
        *,
        memory_class: MemoryClass,
        action: str,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Evaluate access to critical memory classes with explicit policy."""

        is_critical = memory_class in {MemoryClass.IDENTITY, MemoryClass.NORMATIVE}
        check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="memory",
            subject_action=action,
            scope=memory_class.value,
            context={"memory_class": memory_class.value},
            sensitivity="critical" if is_critical else "normal",
            reversibility="low" if action in {"write", "promote", "delete"} else "high",
            risk_hint=RiskLevel.CRITICAL if is_critical else RiskLevel.LOW,
            requested_by_service=requested_by_service,
        )
        decision = PermissionDecision.ALLOW
        justification = "Memory action is compatible with the current policy."
        policy_refs = [f"policy://memory/{memory_class.value}/default"]
        conditions: list[str] = []
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None

        if is_critical and action in {"write", "promote", "delete"}:
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            justification = "Critical memory mutation requires explicit validation."
            policy_refs = [f"policy://memory/{memory_class.value}/critical-mutation"]
            conditions = ["Validate actor and intent before changing critical memory."]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "protect_critical_memory"

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=check.governance_check_id,
            risk_level=check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(governance_check=check, governance_decision=governance_decision)

    def _execution_now(self) -> str:
        value = self._trusted_execution_clock()
        if not isinstance(value, str):
            raise TypeError("trusted execution clock must return an ISO-8601 string")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("trusted execution clock returned an invalid timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("trusted execution clock must be timezone-aware")
        return parsed.astimezone(UTC).isoformat()

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
