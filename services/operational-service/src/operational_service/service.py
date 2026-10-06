"""Low-risk operational service with real text artifacts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from re import fullmatch
from typing import Protocol
from uuid import uuid4

from operational_service.adapters.local_text_file import LocalTextFilePreflightAdapter
from operational_service.adapters.local_text_transaction import (
    LocalTextClaimedAuthorizationLease,
    LocalTextExecutionAuthorizationContext,
    LocalTextExecutionAuthorizationRequest,
    LocalTextMutationReceipt,
    LocalTextMutationRequest,
    LocalTextRollbackReceipt,
    LocalTextRollbackRequest,
    LocalTextStagingAuthorizationRequest,
    LocalTextTransactionEngine,
)
from shared.action_confirmation import (
    build_action_fingerprint,
    canonical_action_confirmation_payload,
)
from shared.action_confirmation import (
    build_action_intent as build_shared_action_intent,
)
from shared.artifact_policy import (
    canonical_artifact_states_from_mission,
    order_artifact_states,
)
from shared.autonomy_ladder import evaluate_autonomy_action
from shared.contracts import (
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterExecutionRequestContract,
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalRollbackPlanContract,
    ArtifactRegistryContract,
    ArtifactResultContract,
    AutonomyActionPolicyDecisionContract,
    DailyOperatorWorkspaceContract,
    DailyWorkspaceMissionContract,
    LocalTextFilePreflightAttestationContract,
    LocalTextFilePreflightContract,
    LocalTextFilePreflightRequestContract,
    LocalTextPhysicalStateAttestationContract,
    MissionStateContract,
    OpenLoopRegistryContract,
    OperationDispatchContract,
    OperationResultContract,
    WorkItemQueueContract,
)
from shared.open_loop_policy import (
    canonical_open_loop_states_from_mission,
    mission_freshness,
    open_loop_resume_blockers,
)
from shared.types import (
    ArtifactId,
    ArtifactStatus,
    MissionStatus,
    OperationStatus,
    RequestId,
    RiskLevel,
)
from shared.work_item_policy import canonical_work_items_from_mission, order_work_items


class AdapterPreflightVerifierPort(Protocol):
    """Governance-owned exact verifier consumed without importing Governance."""

    def __call__(
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
    ) -> bool: ...


class LocalTextFilePreflightAttestorPort(Protocol):
    """Governance-owned recorder called directly with a materialized preflight."""

    def __call__(
        self,
        preflight: LocalTextFilePreflightContract,
    ) -> tuple[
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]: ...


class LocalTextStagingAuthorizationVerifierPort(Protocol):
    """Read-only authority check that must succeed before transaction state I/O."""

    def __call__(
        self,
        request: LocalTextStagingAuthorizationRequest,
        verified_at: datetime,
    ) -> bool: ...


class LocalTextHistoricalClaimVerifierPort(Protocol):
    """Verify an already-consumed claim for recovery without reopening authority."""

    def __call__(
        self,
        context: LocalTextExecutionAuthorizationContext,
        verified_at: datetime,
    ) -> bool: ...


class LocalTextEffectStartClaimVerifierPort(Protocol):
    """Recheck a freshly committed claim immediately before its first effect."""

    def __call__(
        self,
        context: LocalTextExecutionAuthorizationContext,
        verified_at: datetime,
    ) -> bool: ...


class LocalTextHistoricalClaimLookupPort(Protocol):
    """Load one exact persisted claim so recovery never reopens consumed authority."""

    def __call__(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        verified_at: datetime,
    ) -> LocalTextExecutionAuthorizationContext | None: ...


class LocalTextAuthorizationLeaseProviderPort(Protocol):
    """Atomically claim one exact execution and confirmation in Governance."""

    def __call__(
        self,
        request: LocalTextExecutionAuthorizationRequest,
        claimed_at: datetime,
    ) -> LocalTextClaimedAuthorizationLease: ...


class LocalTextTrustedTransactionClockPort(Protocol):
    """Trusted timezone-aware clock shared with the Governance boundary."""

    def __call__(self) -> datetime: ...


class LocalTextMutationReceiptRecorderPort(Protocol):
    """Persist the exact applied receipt in Governance, idempotently."""

    def __call__(self, receipt: LocalTextMutationReceipt) -> LocalTextMutationReceipt: ...


class LocalTextRollbackReceiptRecorderPort(Protocol):
    """Persist the exact rollback receipt in Governance, idempotently."""

    def __call__(self, receipt: LocalTextRollbackReceipt) -> LocalTextRollbackReceipt: ...


class LocalTextMutationReceiptVerifierPort(Protocol):
    """Verify one exact immutable mutation receipt in Governance."""

    def __call__(self, receipt: LocalTextMutationReceipt) -> bool: ...


class LocalTextRollbackReceiptVerifierPort(Protocol):
    """Verify one exact immutable rollback receipt in Governance."""

    def __call__(self, receipt: LocalTextRollbackReceipt) -> bool: ...


class ArtifactPhysicalEffectAuthorizerPort(Protocol):
    """Memory-owned exact reservation check for one sealed physical plan."""

    def __call__(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        *,
        resource_ref: str,
        mutation_receipt_fingerprint: str | None = None,
        effect_mode: str = "new_effect",
    ) -> bool: ...


class ArtifactPhysicalEffectScopeProviderPort(Protocol):
    """Memory-owned lock across a fresh claim and its first physical effect."""

    def __call__(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
    ) -> AbstractContextManager[None]: ...


class LocalTextResourcePhysicalBindingLookupPort(Protocol):
    """Report whether Memory has a pending or canonical binding for a resource."""

    def __call__(self, resource_ref: str) -> bool: ...


class ArtifactPhysicalCanonicalCommitReceiptVerifierPort(Protocol):
    """Verify that Memory persisted one exact canonical commit receipt."""

    def __call__(self, receipt: ArtifactPhysicalCanonicalCommitReceiptContract) -> bool: ...


class ArtifactPhysicalAttestationLeaseProviderPort(Protocol):
    """Open one ephemeral same-thread lease around the canonical Memory callback."""

    def __call__(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextMutationReceipt | LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> AbstractContextManager[None]: ...


@dataclass
class OperationalExecution:
    """Structured result of an operational execution."""

    operation_result: OperationResultContract
    artifact_results: list[ArtifactResultContract]


class OperationalService:
    """Execute low-risk tasks and persist text artifacts."""

    name = "operational-service"
    handler_version = "legacy-text-writer/v2"
    action_confirmation_policy_version = "action-confirmation/v2"
    action_kind = "execute_reversible_core_action"
    action_operation = action_kind
    action_intent_ttl = timedelta(minutes=10)

    @classmethod
    def build_artifact_registry(
        cls,
        mission_state: MissionStateContract,
    ) -> ArtifactRegistryContract:
        """Project canonical artifact lineage without mutating files or mission state."""

        artifact_states = order_artifact_states(
            canonical_artifact_states_from_mission(mission_state)
        )
        refs_by_status = {
            status: [
                item.artifact_ref for item in artifact_states if item.artifact_status == status
            ]
            for status in ("active", "archived", "superseded", "rolled_back")
        }
        registry_status = (
            "empty"
            if not artifact_states
            else "active"
            if refs_by_status["active"]
            else "historical"
        )
        return ArtifactRegistryContract(
            mission_id=mission_state.mission_id,
            registry_status=registry_status,
            artifact_states=artifact_states,
            active_artifact_refs=refs_by_status["active"],
            archived_artifact_refs=refs_by_status["archived"],
            superseded_artifact_refs=refs_by_status["superseded"],
            rolled_back_artifact_refs=refs_by_status["rolled_back"],
            evidence_refs=[
                f"mission-state://{mission_state.mission_id}@{mission_state.updated_at}",
                *mission_state.checkpoint_refs,
            ],
        )

    @classmethod
    def build_open_loop_registry(
        cls,
        mission_state: MissionStateContract,
        *,
        generated_at: str,
    ) -> OpenLoopRegistryContract:
        """Project resume eligibility without resuming or scheduling a loop."""

        states = canonical_open_loop_states_from_mission(mission_state)
        work_queue = cls.build_work_item_queue(mission_state)
        selected_work_item_ref = (
            work_queue.executable_work_item_refs[0]
            if work_queue.executable_work_item_refs
            else None
        )
        freshness_status, mission_age_hours = mission_freshness(
            mission_state.updated_at,
            generated_at,
        )
        blocking_reasons = {
            state.open_loop_ref: open_loop_resume_blockers(
                mission_state=mission_state,
                loop_state=state,
                freshness_status=freshness_status,
                has_structured_work_items=bool(mission_state.work_items),
                selected_work_item_ref=selected_work_item_ref,
            )
            for state in states
        }
        eligible_refs = [
            state.open_loop_ref for state in states if not blocking_reasons[state.open_loop_ref]
        ]
        blocked_refs = [
            state.open_loop_ref for state in states if blocking_reasons[state.open_loop_ref]
        ]
        registry_status = (
            "empty" if not states else "resume_available" if eligible_refs else "blocked"
        )
        return OpenLoopRegistryContract(
            mission_id=mission_state.mission_id,
            registry_status=registry_status,
            freshness_status=freshness_status,
            mission_age_hours=mission_age_hours,
            open_loop_states=states,
            eligible_open_loop_refs=eligible_refs,
            blocked_open_loop_refs=blocked_refs,
            blocking_reasons=blocking_reasons,
            selected_work_item_ref=selected_work_item_ref,
            evidence_refs=[
                f"mission-state://{mission_state.mission_id}@{mission_state.updated_at}",
                *mission_state.checkpoint_refs,
            ],
            generated_at=generated_at,
        )

    def __init__(
        self,
        artifact_dir: str | None = None,
        *,
        action_confirmation_verifier: Callable[..., bool] | None = None,
        adapter_preflight_verifier: AdapterPreflightVerifierPort | None = None,
        artifact_root_alias: str = "operational-artifacts",
        local_text_file_roots: Mapping[str, str | Path] | None = None,
        local_text_file_allowed_extensions: tuple[str, ...] = (".md", ".txt"),
        local_text_file_max_bytes: int = 1_048_576,
        local_text_file_preflight_attestor: LocalTextFilePreflightAttestorPort | None = None,
        local_text_file_transaction_roots: Mapping[str, str | Path] | None = None,
        local_text_file_staging_authorization_verifier: LocalTextStagingAuthorizationVerifierPort
        | None = None,
        local_text_file_effect_start_claim_verifier: LocalTextEffectStartClaimVerifierPort
        | None = None,
        local_text_file_historical_claim_lookup: LocalTextHistoricalClaimLookupPort | None = None,
        local_text_file_historical_claim_verifier: LocalTextHistoricalClaimVerifierPort
        | None = None,
        local_text_file_authorization_lease_provider: LocalTextAuthorizationLeaseProviderPort
        | None = None,
        local_text_file_trusted_transaction_clock: LocalTextTrustedTransactionClockPort
        | None = None,
        local_text_file_mutation_receipt_recorder: LocalTextMutationReceiptRecorderPort
        | None = None,
        local_text_file_rollback_receipt_recorder: LocalTextRollbackReceiptRecorderPort
        | None = None,
        local_text_file_mutation_receipt_verifier: LocalTextMutationReceiptVerifierPort
        | None = None,
        local_text_file_rollback_receipt_verifier: LocalTextRollbackReceiptVerifierPort
        | None = None,
        local_text_file_canonical_physical_effect_authorizer: ArtifactPhysicalEffectAuthorizerPort
        | None = None,
        local_text_file_canonical_physical_effect_scope_provider: (
            ArtifactPhysicalEffectScopeProviderPort | None
        ) = None,
        local_text_file_resource_physical_binding_lookup: LocalTextResourcePhysicalBindingLookupPort
        | None = None,
        local_text_file_canonical_commit_receipt_verifier: (
            ArtifactPhysicalCanonicalCommitReceiptVerifierPort | None
        ) = None,
        local_text_file_physical_attestation_lease_provider: (
            ArtifactPhysicalAttestationLeaseProviderPort | None
        ) = None,
        local_text_file_transaction_failure_injector: Callable[[str], None] | None = None,
    ) -> None:
        resolved_dir = (
            Path(artifact_dir) if artifact_dir else Path.cwd() / ".jarvis_runtime" / "artifacts"
        ).resolve()
        self.artifact_dir = resolved_dir
        self.artifact_root_alias = self._require_artifact_root_alias(artifact_root_alias)
        self.action_confirmation_verifier = action_confirmation_verifier
        self._adapter_preflight_verifier = adapter_preflight_verifier
        self._local_text_file_preflight_attestor = local_text_file_preflight_attestor
        self._local_text_file_mutation_receipt_recorder = local_text_file_mutation_receipt_recorder
        self._local_text_file_rollback_receipt_recorder = local_text_file_rollback_receipt_recorder
        self._local_text_file_canonical_physical_effect_authorizer = (
            local_text_file_canonical_physical_effect_authorizer
        )
        self._local_text_file_resource_physical_binding_lookup = (
            local_text_file_resource_physical_binding_lookup
        )
        self._local_text_file_preflight_adapter = (
            None
            if local_text_file_roots is None
            else LocalTextFilePreflightAdapter(
                roots=local_text_file_roots,
                verified_context_verifier=(self._verify_local_text_file_preflight_context),
                allowed_extensions=local_text_file_allowed_extensions,
                max_bytes=local_text_file_max_bytes,
            )
        )
        transaction_dependencies = (
            local_text_file_staging_authorization_verifier,
            local_text_file_effect_start_claim_verifier,
            local_text_file_historical_claim_lookup,
            local_text_file_historical_claim_verifier,
            local_text_file_authorization_lease_provider,
            local_text_file_trusted_transaction_clock,
            local_text_file_mutation_receipt_recorder,
            local_text_file_rollback_receipt_recorder,
        )
        receipt_proof_dependencies = (
            local_text_file_mutation_receipt_verifier,
            local_text_file_rollback_receipt_verifier,
            local_text_file_canonical_physical_effect_authorizer,
            local_text_file_canonical_physical_effect_scope_provider,
            local_text_file_resource_physical_binding_lookup,
            local_text_file_canonical_commit_receipt_verifier,
            local_text_file_physical_attestation_lease_provider,
        )
        if local_text_file_transaction_roots is None:
            if any(
                dependency is not None
                for dependency in (*transaction_dependencies, *receipt_proof_dependencies)
            ):
                raise ValueError("local_text_file_transaction_roots_required")
            if local_text_file_transaction_failure_injector is not None:
                raise ValueError("local_text_file_transaction_roots_required")
            self._local_text_file_transaction_engine = None
        else:
            if self._local_text_file_preflight_adapter is None:
                raise ValueError("local_text_file_preflight_not_configured")
            if any(dependency is None for dependency in transaction_dependencies):
                raise ValueError("local_text_file_transaction_governance_ports_required")
            self._local_text_file_transaction_engine = LocalTextTransactionEngine(
                preflight_adapter=self._local_text_file_preflight_adapter,
                transaction_roots={
                    alias: str(path) for alias, path in local_text_file_transaction_roots.items()
                },
                staging_authorization_verifier=(local_text_file_staging_authorization_verifier),
                effect_start_claim_verifier=local_text_file_effect_start_claim_verifier,
                historical_claim_lookup=local_text_file_historical_claim_lookup,
                historical_claim_verifier=local_text_file_historical_claim_verifier,
                authorization_lease_provider=local_text_file_authorization_lease_provider,
                trusted_transaction_clock=local_text_file_trusted_transaction_clock,
                mutation_receipt_verifier=local_text_file_mutation_receipt_verifier,
                rollback_receipt_verifier=local_text_file_rollback_receipt_verifier,
                canonical_physical_effect_authorizer=(
                    None
                    if local_text_file_canonical_physical_effect_authorizer is None
                    else self._authorize_local_text_file_canonical_physical_effect
                ),
                canonical_physical_effect_scope_provider=(
                    local_text_file_canonical_physical_effect_scope_provider
                ),
                resource_physical_binding_lookup=(local_text_file_resource_physical_binding_lookup),
                canonical_commit_receipt_verifier=(
                    local_text_file_canonical_commit_receipt_verifier
                ),
                physical_attestation_lease_provider=(
                    local_text_file_physical_attestation_lease_provider
                ),
                failure_injector=local_text_file_transaction_failure_injector,
            )

    def local_text_file_root_config_fingerprint(self) -> str:
        """Inspect the configured root identity without preparing or executing an action."""

        adapter = self._local_text_file_preflight_adapter
        if adapter is None:
            raise ValueError("local_text_file_preflight_not_configured")
        return adapter.root_config_fingerprint()

    def preflight_local_text_file(
        self,
        request: LocalTextFilePreflightRequestContract,
        *,
        now: datetime | None = None,
    ) -> LocalTextFilePreflightContract:
        """Prepare one exact local-text action without dispatching or writing it."""

        adapter = self._local_text_file_preflight_adapter
        if adapter is None:
            raise ValueError("local_text_file_preflight_not_configured")
        return adapter.preflight(request, now=now)

    def preflight_and_attest_local_text_file(
        self,
        request: LocalTextFilePreflightRequestContract,
        *,
        now: datetime | None = None,
    ) -> tuple[
        LocalTextFilePreflightContract,
        LocalTextFilePreflightAttestationContract,
        AdapterExecutionRequestContract,
    ]:
        """Materialize preflight and pass it directly to the trusted recorder."""

        attestor = self._local_text_file_preflight_attestor
        if attestor is None:
            raise ValueError("local_text_file_preflight_attestor_not_configured")
        preflight = self.preflight_local_text_file(request, now=now)
        attestation, execution_request = attestor(preflight)
        if (
            execution_request.preflight_attestation_id != attestation.attestation_id
            or execution_request.preflight_attestation_fingerprint
            != attestation.attestation_fingerprint
            or execution_request.preflight_fingerprint != preflight.preflight_fingerprint
        ):
            raise ValueError("local_text_file_preflight_attestation_binding_mismatch")
        return preflight, attestation, execution_request

    def execute_local_text_file(
        self,
        request: LocalTextMutationRequest,
    ) -> LocalTextMutationReceipt:
        """Execute one exact governed transaction; unavailable unless explicitly wired."""

        engine = self._require_local_text_file_transaction_engine()
        receipt = engine.execute(request)
        return self._record_local_text_mutation_receipt(receipt)

    def recover_local_text_file(
        self,
        *,
        root_alias: str,
        operation_id: str,
    ) -> LocalTextMutationReceipt:
        """Resume one durable mutation from its content-free journal."""

        engine = self._require_local_text_file_transaction_engine()
        receipt = engine.recover(root_alias=root_alias, operation_id=operation_id)
        return self._record_local_text_mutation_receipt(receipt)

    def rollback_local_text_file(
        self,
        request: LocalTextRollbackRequest,
    ) -> LocalTextRollbackReceipt:
        """Apply a separately authorized physical rollback."""

        engine = self._require_local_text_file_transaction_engine()
        receipt = engine.rollback(request)
        return self._record_local_text_rollback_receipt(receipt)

    def recover_local_text_file_rollback(
        self,
        *,
        root_alias: str,
        operation_id: str,
    ) -> LocalTextRollbackReceipt:
        """Resume an already-claimed rollback without minting new authority."""

        engine = self._require_local_text_file_transaction_engine()
        receipt = engine.recover_rollback(
            root_alias=root_alias,
            operation_id=operation_id,
        )
        return self._record_local_text_rollback_receipt(receipt)

    def execute_and_commit_local_text_file_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
        request: LocalTextMutationRequest,
        *,
        canonical_commit: Callable[
            [
                ArtifactPhysicalApplyPlanContract,
                LocalTextMutationReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Apply, record physical proof, and commit Memory under one resource lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.execute_and_commit_apply(
            plan,
            request,
            receipt_recorder=self._record_local_text_mutation_receipt,
            canonical_commit=canonical_commit,
        )

    def recover_and_commit_local_text_file_apply(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        root_alias: str,
        operation_id: str,
        canonical_commit: Callable[
            [
                ArtifactPhysicalApplyPlanContract,
                LocalTextMutationReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Recover an apply and finish its canonical commit under the same lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.recover_and_commit_apply(
            plan=plan,
            root_alias=root_alias,
            operation_id=operation_id,
            receipt_recorder=self._record_local_text_mutation_receipt,
            canonical_commit=canonical_commit,
        )

    def rollback_and_commit_local_text_file(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
        request: LocalTextRollbackRequest,
        *,
        canonical_commit: Callable[
            [
                ArtifactPhysicalRollbackPlanContract,
                LocalTextRollbackReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Roll back, record proof, and commit Memory under one resource lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.rollback_and_commit(
            plan,
            request,
            receipt_recorder=self._record_local_text_rollback_receipt,
            canonical_commit=canonical_commit,
        )

    def recover_and_commit_local_text_file_rollback(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        root_alias: str,
        operation_id: str,
        canonical_commit: Callable[
            [
                ArtifactPhysicalRollbackPlanContract,
                LocalTextRollbackReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Recover a rollback and finish its canonical commit under one lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.recover_rollback_and_commit(
            plan=plan,
            root_alias=root_alias,
            operation_id=operation_id,
            receipt_recorder=self._record_local_text_rollback_receipt,
            canonical_commit=canonical_commit,
        )

    def verify_local_text_file_mutation_receipt_current(
        self,
        *,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
    ) -> LocalTextMutationReceipt:
        """Verify persisted mutation proof plus its fresh physical state."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.verify_mutation_receipt_current(
            root_alias=root_alias,
            receipt=receipt,
        )

    def commit_local_text_file_mutation_if_current(
        self,
        *,
        plan: ArtifactPhysicalApplyPlanContract,
        root_alias: str,
        receipt: LocalTextMutationReceipt,
        canonical_commit: Callable[
            [
                ArtifactPhysicalApplyPlanContract,
                LocalTextMutationReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Commit canonical state only under exact fresh mutation proof and lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.commit_mutation_if_current(
            plan=plan,
            root_alias=root_alias,
            receipt=receipt,
            canonical_commit=canonical_commit,
        )

    def verify_local_text_file_rollback_receipt_current(
        self,
        *,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
    ) -> LocalTextRollbackReceipt:
        """Verify persisted rollback proof plus its fresh restored state."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.verify_rollback_receipt_current(
            root_alias=root_alias,
            receipt=receipt,
        )

    def commit_local_text_file_rollback_if_current(
        self,
        *,
        plan: ArtifactPhysicalRollbackPlanContract,
        root_alias: str,
        receipt: LocalTextRollbackReceipt,
        canonical_commit: Callable[
            [
                ArtifactPhysicalRollbackPlanContract,
                LocalTextRollbackReceipt,
                LocalTextPhysicalStateAttestationContract,
            ],
            ArtifactPhysicalCanonicalCommitReceiptContract,
        ],
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        """Commit canonical rollback state only under fresh proof and lock."""

        engine = self._require_local_text_file_transaction_engine()
        return engine.commit_rollback_if_current(
            plan=plan,
            root_alias=root_alias,
            receipt=receipt,
            canonical_commit=canonical_commit,
        )

    def _record_local_text_mutation_receipt(
        self,
        receipt: LocalTextMutationReceipt,
    ) -> LocalTextMutationReceipt:
        recorder = self._local_text_file_mutation_receipt_recorder
        if recorder is None:
            raise ValueError("local_text_file_mutation_receipt_recorder_not_configured")
        recorded = recorder(receipt)
        if recorded != receipt:
            raise ValueError("local_text_file_mutation_receipt_recording_mismatch")
        return recorded

    def _record_local_text_rollback_receipt(
        self,
        receipt: LocalTextRollbackReceipt,
    ) -> LocalTextRollbackReceipt:
        recorder = self._local_text_file_rollback_receipt_recorder
        if recorder is None:
            raise ValueError("local_text_file_rollback_receipt_recorder_not_configured")
        recorded = recorder(receipt)
        if recorded != receipt:
            raise ValueError("local_text_file_rollback_receipt_recording_mismatch")
        return recorded

    def _authorize_local_text_file_canonical_physical_effect(
        self,
        plan: ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract,
        *,
        effect_mode: str = "new_effect",
    ) -> bool:
        authorizer = self._local_text_file_canonical_physical_effect_authorizer
        if authorizer is None:
            return False
        mutation_receipt_fingerprint = (
            plan.mutation_receipt_fingerprint
            if isinstance(plan, ArtifactPhysicalRollbackPlanContract)
            else None
        )
        return authorizer(
            plan,
            resource_ref=plan.resource_ref,
            mutation_receipt_fingerprint=mutation_receipt_fingerprint,
            effect_mode=effect_mode,
        )

    def _require_local_text_file_transaction_engine(self) -> LocalTextTransactionEngine:
        engine = self._local_text_file_transaction_engine
        if engine is None:
            raise ValueError("local_text_file_transaction_not_configured")
        return engine

    def _verify_local_text_file_preflight_context(
        self,
        request: LocalTextFilePreflightRequestContract,
        verified_at: datetime,
    ) -> bool:
        verifier = self._adapter_preflight_verifier
        if verifier is None or verified_at.tzinfo is None:
            return False
        canonical_verified_at = verified_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        try:
            desired_content_digest = sha256(
                request.desired_text.encode("utf-8", errors="strict")
            ).hexdigest()
            verified = verifier(
                request.grant_id,
                subject_ref=request.subject_ref,
                action_request=request.adapter_request,
                expected_grant_fingerprint=request.grant_fingerprint,
                expected_action_fingerprint=request.action_fingerprint,
                expected_content_digest=desired_content_digest,
                expected_precondition_digest=(request.expected_root_config_fingerprint),
                intent_fingerprint=request.intent_fingerprint,
                expected_descriptor_fingerprint=request.descriptor_fingerprint,
                expected_registry_fingerprint=request.registry_fingerprint,
                expected_authorization_expires_at=request.authorization_expires_at,
                preflight_expires_at=request.expires_at,
                verified_at=canonical_verified_at,
            )
        except Exception:
            return False
        return verified is True

    def action_fingerprint_for_dispatch(
        self,
        dispatch: OperationDispatchContract,
        *,
        origin_request_id: str | None = None,
    ) -> str:
        """Derive the stable identity of the logical artifact action, read-only."""

        fields = self._action_identity_fields(
            dispatch,
            origin_request_id=origin_request_id,
        )
        return build_action_fingerprint(**fields)

    def build_action_intent(
        self,
        dispatch: OperationDispatchContract,
        *,
        issued_at: str | None = None,
        expires_at: str | None = None,
        nonce: str | None = None,
        origin_request_id: str | None = None,
    ) -> ActionIntentContract:
        """Build a validated, non-authorizing intent without touching the writer."""

        issued = self.now() if issued_at is None else issued_at
        expires = self._default_action_intent_expiry(issued) if expires_at is None else expires_at
        fields = self._action_identity_fields(
            dispatch,
            origin_request_id=origin_request_id,
        )
        return build_shared_action_intent(
            intent_id=f"action-intent://{uuid4().hex}",
            **fields,
            nonce=uuid4().hex if nonce is None else nonce,
            issued_at=issued,
            expires_at=expires,
            now=self.now(),
        )

    @classmethod
    def action_confirmation_required_for_dispatch(
        cls,
        dispatch: OperationDispatchContract,
    ) -> bool:
        """Return whether canonical autonomy policy requires exact confirmation."""

        decision = cls._autonomy_action_decision(
            dispatch,
            confirmation_evidence_state="absent",
        )
        return decision.decision == "require_confirmation"

    @staticmethod
    def _autonomy_action_decision(
        dispatch: OperationDispatchContract,
        *,
        confirmation_evidence_state: str,
    ) -> AutonomyActionPolicyDecisionContract:
        return evaluate_autonomy_action(
            requested_autonomy_level=dispatch.requested_autonomy_level,
            max_autonomy_level=dispatch.max_autonomy_level,
            effective_autonomy_level=dispatch.effective_autonomy_level,
            autonomy_ladder_status=dispatch.autonomy_ladder_status,
            action_kind=dispatch.autonomy_action_kind,
            selected_capability_mode=dispatch.capability_decision_selected_mode,
            max_capability_mode=dispatch.max_autonomy_capability_mode,
            allowed_runtime_actions=dispatch.autonomy_allowed_runtime_actions,
            blocked_runtime_actions=dispatch.autonomy_blocked_runtime_actions,
            human_confirmation_required=(dispatch.autonomy_human_confirmation_required),
            human_confirmation_mode=dispatch.autonomy_confirmation_mode,
            confirmation_evidence_state=confirmation_evidence_state,
            autonomy_validation_errors=dispatch.autonomy_validation_errors,
        )

    @classmethod
    def build_work_item_queue(
        cls,
        mission_state: MissionStateContract,
    ) -> WorkItemQueueContract:
        """Build a read-only governed queue without scheduling or execution."""

        ordered = order_work_items(canonical_work_items_from_mission(mission_state))
        mission_blocking_state = {
            MissionStatus.PAUSED: "mission_paused",
            MissionStatus.BLOCKED: "mission_blocked",
            MissionStatus.COMPLETED: "mission_completed",
            MissionStatus.CANCELED: "mission_canceled",
        }.get(mission_state.mission_status)
        if mission_blocking_state:
            ordered = [
                replace(item, blocking_state=mission_blocking_state)
                if item.work_item_status != "completed"
                else item
                for item in ordered
            ]
        executable_refs = [
            item.work_item_ref
            for item in ordered
            if item.work_item_status == "active" and item.blocking_state == "ready"
        ]
        blocked_refs = [
            item.work_item_ref
            for item in ordered
            if item.work_item_status != "completed" and item.work_item_ref not in executable_refs
        ]
        completed_refs = [
            item.work_item_ref for item in ordered if item.work_item_status == "completed"
        ]
        queue_status = (
            "empty"
            if not ordered
            else "ready_with_blocked"
            if executable_refs and blocked_refs
            else "ready"
            if executable_refs
            else "blocked"
            if blocked_refs
            else "completed"
        )
        return WorkItemQueueContract(
            mission_id=mission_state.mission_id,
            queue_status=queue_status,
            ordered_work_items=ordered,
            executable_work_item_refs=executable_refs,
            blocked_work_item_refs=blocked_refs,
            completed_work_item_refs=completed_refs,
            evidence_refs=[
                f"mission-state://{mission_state.mission_id}@{mission_state.updated_at}",
                *mission_state.checkpoint_refs,
            ],
        )

    @classmethod
    def build_daily_operator_workspace(
        cls,
        *,
        mission_states: list[MissionStateContract],
        pending_evolution_review_refs: list[str] | None = None,
        pending_memory_review_refs: list[str] | None = None,
        generated_at: str | None = None,
    ) -> DailyOperatorWorkspaceContract:
        """Build a read-only cross-session workspace from canonical state."""

        safe_generated_at = generated_at or cls.now()
        evolution_refs = cls._unique_values(pending_evolution_review_refs or [])
        memory_refs = cls._unique_values(pending_memory_review_refs or [])
        ordered_states = sorted(
            mission_states[:200],
            key=lambda state: str(state.mission_id),
        )
        ordered_states.sort(
            key=lambda state: cls._workspace_sort_timestamp(state.updated_at),
            reverse=True,
        )
        missions = [
            cls._daily_workspace_mission(state, generated_at=safe_generated_at)
            for state in ordered_states
        ]
        next_decision_refs = cls._unique_values(
            [f"review_evolution_proposal:{item}" for item in evolution_refs]
            + [f"review_memory_lifecycle:{item}" for item in memory_refs]
            + [decision for mission in missions for decision in mission.pending_decision_refs]
        )
        requires_operator_decision = bool(evolution_refs or memory_refs) or any(
            mission.operator_attention_status
            in {"blocked", "paused", "stale", "unknown", "decision_required"}
            for mission in missions
        )
        ready_for_next_action = any(
            mission.next_action_status in {"ready", "derive_from_work_item"} for mission in missions
        )
        workspace_status = (
            "operator_decision_required"
            if requires_operator_decision
            else "ready_for_next_action"
            if ready_for_next_action
            else "idle"
        )
        evidence_refs = cls._unique_values(
            [evidence for mission in missions for evidence in mission.evidence_refs]
            + [f"evolution-review://{item}" for item in evolution_refs]
            + [f"memory-review://{item}" for item in memory_refs]
        )
        fingerprint = "|".join(
            [
                safe_generated_at,
                *(f"{mission.mission_id}@{mission.updated_at}" for mission in missions),
                *evolution_refs,
                *memory_refs,
            ]
        )
        return DailyOperatorWorkspaceContract(
            workspace_id=(
                "daily-workspace://" + sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
            ),
            workspace_status=workspace_status,
            generated_at=safe_generated_at,
            missions=missions,
            mission_count=len(missions),
            active_objective_count=sum(
                mission.objective_status not in {"completed", "canceled"} for mission in missions
            ),
            active_work_item_count=sum(len(mission.active_work_items) for mission in missions),
            active_artifact_count=sum(len(mission.active_artifact_refs) for mission in missions),
            open_checkpoint_count=sum(len(mission.open_checkpoint_refs) for mission in missions),
            pending_review_count=len(evolution_refs) + len(memory_refs),
            stale_mission_count=sum(
                mission.freshness_status in {"stale", "unknown"} for mission in missions
            ),
            pending_evolution_review_refs=evolution_refs,
            pending_memory_review_refs=memory_refs,
            next_decision_refs=next_decision_refs,
            next_operator_decision=(next_decision_refs[0] if next_decision_refs else None),
            evidence_refs=evidence_refs,
        )

    @classmethod
    def _daily_workspace_mission(
        cls,
        state: MissionStateContract,
        *,
        generated_at: str,
    ) -> DailyWorkspaceMissionContract:
        mission_id = str(state.mission_id)
        work_item_queue = cls.build_work_item_queue(state)
        objective_status = state.objective_status or state.mission_status.value
        freshness_status, freshness_age_hours = cls._workspace_freshness(
            state.updated_at,
            generated_at,
        )
        blocked = state.mission_status == MissionStatus.BLOCKED or objective_status == "blocked"
        paused = state.mission_status == MissionStatus.PAUSED
        pending_decisions: list[str] = []
        if blocked:
            pending_decisions.append(f"resolve_blocked_mission:{mission_id}")
        elif paused:
            pending_decisions.append(f"review_paused_mission:{mission_id}")
        if freshness_status in {"stale", "unknown"}:
            pending_decisions.append(f"review_stale_mission:{mission_id}")
        if state.open_checkpoint_refs:
            pending_decisions.append(f"review_open_checkpoints:{mission_id}")
        if work_item_queue.blocked_work_item_refs:
            pending_decisions.append(f"review_blocked_work_items:{mission_id}")
        if not blocked and not paused:
            if state.next_action_ref:
                pending_decisions.append(f"continue_mission:{mission_id}:{state.next_action_ref}")
            elif work_item_queue.executable_work_item_refs:
                pending_decisions.append(
                    "select_work_item:" + work_item_queue.executable_work_item_refs[0]
                )
            else:
                pending_decisions.append(f"define_next_action:{mission_id}")
        next_action_status = (
            "blocked"
            if blocked
            else "paused"
            if paused
            else "ready"
            if state.next_action_ref
            else "derive_from_work_item"
            if work_item_queue.executable_work_item_refs
            else "blocked_by_work_item"
            if work_item_queue.blocked_work_item_refs
            else "missing"
        )
        operator_attention_status = (
            "blocked"
            if blocked
            else "paused"
            if paused
            else freshness_status
            if freshness_status in {"stale", "unknown"}
            else "decision_required"
            if state.open_checkpoint_refs
            else "ready"
            if next_action_status in {"ready", "derive_from_work_item"}
            else "decision_required"
        )
        return DailyWorkspaceMissionContract(
            mission_id=state.mission_id,
            mission_goal=state.mission_goal,
            mission_status=state.mission_status,
            objective_status=objective_status,
            updated_at=state.updated_at,
            freshness_status=freshness_status,
            freshness_age_hours=freshness_age_hours,
            operator_attention_status=operator_attention_status,
            next_action_status=next_action_status,
            project_ref=state.project_ref,
            objective_ref=state.objective_ref,
            next_action_ref=state.next_action_ref,
            work_item_refs=list(state.work_item_refs),
            active_work_items=list(state.active_work_items),
            ordered_work_item_refs=[
                item.work_item_ref for item in work_item_queue.ordered_work_items
            ],
            executable_work_item_refs=list(work_item_queue.executable_work_item_refs),
            blocked_work_item_refs=list(work_item_queue.blocked_work_item_refs),
            artifact_refs=list(state.artifact_refs),
            active_artifact_refs=list(state.active_artifact_refs),
            open_checkpoint_refs=list(state.open_checkpoint_refs),
            open_loops=list(state.open_loops),
            pending_decision_refs=cls._unique_values(pending_decisions),
            evidence_refs=[f"mission-state://{mission_id}@{state.updated_at}"],
        )

    @staticmethod
    def _workspace_freshness(
        updated_at: str,
        generated_at: str,
    ) -> tuple[str, float | None]:
        try:
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=UTC)
            age_hours = (generated - updated).total_seconds() / 3600
        except (TypeError, ValueError):
            return "unknown", None
        if age_hours < -0.084:
            return "unknown", None
        safe_age = round(max(0.0, age_hours), 2)
        if safe_age <= 24:
            return "fresh", safe_age
        if safe_age <= 72:
            return "aging", safe_age
        return "stale", safe_age

    @staticmethod
    def _workspace_sort_timestamp(value: str) -> float:
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return float("-inf")
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.timestamp()

    @staticmethod
    def _unique_values(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    def execute(self, dispatch: OperationDispatchContract) -> OperationalExecution:
        """Execute a low-risk operation using a deterministic local policy."""

        artifact_results: list[ArtifactResultContract] = []
        governance_flags: list[str] = []
        errors: list[str] = []
        confirmation_failed = False
        confirmation_evidence_state = "absent"
        autonomy_decision: AutonomyActionPolicyDecisionContract | None = None
        caller_destination_rejected = dispatch.artifact_destination is not None
        if caller_destination_rejected:
            content = (
                "Dispatch bloqueado: o destino fisico do artefato pertence "
                "exclusivamente a configuracao do servico."
            )
            status = OperationStatus.FAILED
            governance_flags.append("caller_artifact_destination_rejected")
            errors.append("artifact_destination_not_allowed")
        else:
            supported_content = self._content_for_dispatch(dispatch)
            if supported_content is None:
                content = f"Task type nao suportado: {dispatch.task_type}"
                status = OperationStatus.FAILED
            else:
                content = supported_content
                autonomy_decision = self._autonomy_action_decision(
                    dispatch,
                    confirmation_evidence_state=confirmation_evidence_state,
                )
                if autonomy_decision.decision == "block":
                    content = "Dispatch bloqueado: politica canonica de autonomia negou a acao."
                    status = OperationStatus.FAILED
                    governance_flags.append("autonomy_action_policy_blocked")
                    errors.extend(autonomy_decision.reason_codes)
                elif dispatch.autonomy_action_kind != self.action_kind:
                    content = "Dispatch bloqueado: action kind sem writer operacional registrado."
                    status = OperationStatus.FAILED
                    governance_flags.append("operational_action_kind_not_supported")
                    errors.append("operational_action_kind_not_supported")
                elif (
                    autonomy_decision.decision == "allow"
                    and not autonomy_decision.side_effect_allowed
                ):
                    content = (
                        "Dispatch bloqueado: a decisao de autonomia nao autoriza efeito colateral."
                    )
                    status = OperationStatus.FAILED
                    governance_flags.append("autonomy_action_policy_blocked")
                    errors.append("autonomy_action_side_effect_not_allowed")
                else:
                    status = OperationStatus.COMPLETED

        if (
            status == OperationStatus.COMPLETED
            and autonomy_decision is not None
            and autonomy_decision.decision == "require_confirmation"
        ):
            confirmation_error = self._action_confirmation_error(dispatch, content)
            if confirmation_error is not None:
                content = "Dispatch bloqueado: confirmacao humana exata nao verificada."
                status = OperationStatus.FAILED
                confirmation_failed = True
                governance_flags.append("action_confirmation_not_verified")
                errors.append(confirmation_error)
                confirmation_evidence_state = "invalid"
            else:
                confirmation_evidence_state = "verified"

        if status == OperationStatus.COMPLETED:
            final_autonomy_decision = self._autonomy_action_decision(
                dispatch,
                confirmation_evidence_state=confirmation_evidence_state,
            )
            if (
                final_autonomy_decision.decision != "allow"
                or not final_autonomy_decision.side_effect_allowed
                or dispatch.autonomy_action_kind != self.action_kind
            ):
                content = (
                    "Dispatch bloqueado: autoridade de autonomia nao valida "
                    "imediatamente antes do writer."
                )
                status = OperationStatus.FAILED
                governance_flags.append("autonomy_action_policy_blocked")
                errors.extend(
                    reason
                    for reason in final_autonomy_decision.reason_codes
                    if reason not in errors
                )
                if not errors:
                    errors.append("autonomy_action_side_effect_not_allowed")
            else:
                artifact_results.append(self._write_artifact(dispatch, content))

        outputs = [dispatch.plan_summary or content.splitlines()[0]]
        workflow_checkpoint_tokens = [
            f"workflow:{item}" for item in dispatch.workflow_checkpoints
        ] or [
            "workflow:composed",
            "workflow:executed",
        ]
        workflow_state = "completed" if status == OperationStatus.COMPLETED else "failed"
        workflow_completed_steps = (
            list(dispatch.workflow_steps) if status == OperationStatus.COMPLETED else []
        )
        workflow_checkpoint_state = self._workflow_checkpoint_state(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
        )
        workflow_pending_checkpoints = [
            checkpoint
            for checkpoint, checkpoint_status in workflow_checkpoint_state.items()
            if checkpoint_status != "completed"
        ]
        workflow_resume_status, workflow_resume_point = self._workflow_resume_outcome(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
            pending_checkpoints=workflow_pending_checkpoints,
        )
        workflow_decisions = self._workflow_decisions(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
        )
        active_artifact_refs = self._active_artifact_refs(dispatch, artifact_results)
        open_checkpoint_refs = [
            f"workflow_checkpoint:{checkpoint}:{checkpoint_status}"
            for checkpoint, checkpoint_status in workflow_checkpoint_state.items()
            if checkpoint_status != "completed"
        ]
        ecosystem_state_status = self._ecosystem_state_status(
            active_work_items=dispatch.active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=dispatch.surface_presence,
        )
        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            errors=errors,
            artifacts=[
                artifact.location_ref for artifact in artifact_results if artifact.location_ref
            ],
            checkpoints=[
                "operational_execution_started",
                f"workflow_route:{dispatch.workflow_domain_route or 'fallback'}",
                f"workflow_state:{dispatch.workflow_state or 'composed'}",
                f"workflow_resume_status:{dispatch.workflow_resume_status or 'fresh_start'}",
                "workflow_state:executing",
                *workflow_checkpoint_tokens,
                f"workflow_state:{workflow_state}",
                f"workflow_resume_outcome:{workflow_resume_status}",
                "operational_execution_finished",
            ],
            workflow_domain_route=dispatch.workflow_domain_route,
            workflow_state=workflow_state,
            workflow_completed_steps=workflow_completed_steps,
            workflow_decisions=workflow_decisions,
            workflow_checkpoint_state=workflow_checkpoint_state,
            workflow_pending_checkpoints=workflow_pending_checkpoints,
            workflow_resume_point=workflow_resume_point,
            workflow_resume_status=workflow_resume_status,
            ecosystem_state_status=ecosystem_state_status,
            active_work_items=list(dispatch.active_work_items),
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=list(dispatch.surface_presence),
            ecosystem_state_summary=self._ecosystem_state_summary(
                active_work_items=dispatch.active_work_items,
                active_artifact_refs=active_artifact_refs,
                open_checkpoint_refs=open_checkpoint_refs,
                surface_presence=dispatch.surface_presence,
            ),
            project_ref=dispatch.project_ref,
            objective_ref=dispatch.objective_ref,
            work_item_refs=list(dispatch.work_item_refs),
            checkpoint_refs=list(dispatch.checkpoint_refs),
            artifact_refs=self._project_artifact_refs(dispatch, artifact_results),
            objective_status=(
                "completed" if status == OperationStatus.COMPLETED else dispatch.objective_status
            ),
            next_action_ref=dispatch.next_action_ref,
            surface_id=dispatch.surface_id,
            surface_kind=dispatch.surface_kind,
            surface_session_id=dispatch.surface_session_id,
            surface_capability_scope=list(dispatch.surface_capability_scope),
            operator_identity_ref=dispatch.operator_identity_ref,
            canonical_user_ref=dispatch.canonical_user_ref,
            surface_continuity_status=dispatch.surface_continuity_status,
            next_recommendation=(
                "continue"
                if status == OperationStatus.COMPLETED
                else ("request_human_confirmation" if confirmation_failed else "review_dispatch")
            ),
            governance_flags=governance_flags,
            memory_record_hints=(
                ["artifact_generated", dispatch.plan_summary or "plan_executed"]
                if artifact_results
                else ["dispatch_review_required"]
            ),
        )
        return OperationalExecution(operation_result=result, artifact_results=artifact_results)

    def _write_artifact(
        self,
        dispatch: OperationDispatchContract,
        content: str,
    ) -> ArtifactResultContract:
        artifact_id = ArtifactId(f"artifact-{uuid4().hex[:8]}")
        target_dir = self.artifact_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = target_dir / f"{artifact_id}.md"
        # The action intent fingerprints the exact UTF-8 payload. Writing bytes
        # avoids platform newline translation after human confirmation.
        artifact_path.write_bytes(content.encode("utf-8"))
        return ArtifactResultContract(
            artifact_id=artifact_id,
            artifact_type="text_document",
            artifact_status=ArtifactStatus.GENERATED,
            produced_by=self.name,
            timestamp=self.now(),
            location_ref=str(artifact_path),
            summary=dispatch.plan_summary or content.splitlines()[0],
            format="text/markdown",
            request_id=dispatch.request_id,
        )

    def _action_identity_fields(
        self,
        dispatch: OperationDispatchContract,
        *,
        origin_request_id: str | None,
        content: str | None = None,
    ) -> dict[str, object]:
        if dispatch.artifact_destination is not None:
            raise ValueError("artifact_destination_not_allowed")
        if dispatch.autonomy_action_kind != self.action_kind:
            raise ValueError("action_intent_action_kind_not_supported")
        derived_content = content if content is not None else self._content_for_dispatch(dispatch)
        if derived_content is None:
            raise ValueError("unsupported_task_type_for_action_intent")
        if dispatch.session_id is None:
            raise ValueError("action_intent_session_id_required")
        operator_identity_ref = dispatch.operator_identity_ref or dispatch.canonical_user_ref
        if not operator_identity_ref:
            raise ValueError("action_intent_operator_identity_ref_required")
        resolved_origin_request_id = (
            str(dispatch.request_id) if origin_request_id is None else origin_request_id
        )
        return {
            "origin_request_id": RequestId(resolved_origin_request_id),
            "session_id": dispatch.session_id,
            "mission_id": dispatch.mission_id,
            "operator_identity_ref": operator_identity_ref,
            "handler_id": self.name,
            "handler_version": self.handler_version,
            "operation": self.action_kind,
            "target_ref": f"artifact-root://{self.artifact_root_alias}",
            "content_digest": sha256(derived_content.encode("utf-8")).hexdigest(),
            "precondition_digest": self._managed_create_precondition_digest(),
            "risk_level": self._risk_level_for_dispatch(dispatch),
            "policy_version": self.action_confirmation_policy_version,
        }

    @staticmethod
    def _risk_level_for_dispatch(
        dispatch: OperationDispatchContract,
    ) -> RiskLevel:
        if dispatch.risk_hint is not None:
            try:
                return RiskLevel(dispatch.risk_hint)
            except (TypeError, ValueError) as exc:
                raise ValueError("action_intent_risk_hint_unknown") from exc
        if dispatch.request_risk_profile is None:
            return RiskLevel.LOW
        planning_profiles = {
            "bounded_confidence": RiskLevel.LOW,
            "contained_review": RiskLevel.MODERATE,
            "governed_caution": RiskLevel.MODERATE,
        }
        try:
            return planning_profiles[dispatch.request_risk_profile]
        except (KeyError, TypeError) as exc:
            raise ValueError("action_intent_request_risk_profile_unknown") from exc

    def _action_confirmation_error(
        self,
        dispatch: OperationDispatchContract,
        content: str,
    ) -> str | None:
        operator_identity_ref = dispatch.operator_identity_ref or dispatch.canonical_user_ref
        required_values = (
            dispatch.receipt_id,
            dispatch.claim_id,
            dispatch.origin_request_id,
            dispatch.action_fingerprint,
            dispatch.intent_fingerprint,
            dispatch.claimed_at,
            operator_identity_ref,
        )
        if any(not isinstance(value, str) or not value for value in required_values):
            return "action_confirmation_claim_incomplete"
        try:
            fields = self._action_identity_fields(
                dispatch,
                origin_request_id=str(dispatch.origin_request_id),
                content=content,
            )
            expected_fingerprint = build_action_fingerprint(**fields)
        except (TypeError, ValueError):
            return "action_confirmation_context_invalid"
        if not compare_digest(
            str(dispatch.action_fingerprint),
            expected_fingerprint,
        ):
            return "action_confirmation_action_fingerprint_mismatch"
        if self.action_confirmation_verifier is None:
            return "action_confirmation_verifier_unavailable"
        try:
            verified = self.action_confirmation_verifier(
                receipt_id=str(dispatch.receipt_id),
                claim_id=str(dispatch.claim_id),
                operation_id=str(dispatch.operation_id),
                origin_request_id=str(dispatch.origin_request_id),
                expected_action_fingerprint=expected_fingerprint,
                intent_fingerprint=str(dispatch.intent_fingerprint),
                claimed_at=str(dispatch.claimed_at),
                verified_at=self.now(),
                operator_identity_ref=str(operator_identity_ref),
            )
        except Exception:
            return "action_confirmation_verifier_error"
        if verified is not True:
            return "action_confirmation_verification_failed"
        return None

    def _managed_create_precondition_digest(self) -> str:
        payload = canonical_action_confirmation_payload(
            {
                "operation": "managed_create",
                "action_kind": self.action_kind,
                "target_ref": f"artifact-root://{self.artifact_root_alias}",
                "version": "operational-managed-create/v2",
                "writer": self.name,
            }
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def _content_for_dispatch(
        cls,
        dispatch: OperationDispatchContract,
    ) -> str | None:
        if dispatch.task_type == "draft_plan":
            return cls._build_plan_content(dispatch)
        if dispatch.task_type == "produce_analysis_brief":
            return cls._build_analysis_content(dispatch)
        if dispatch.task_type == "general_response":
            return cls._build_general_content(dispatch)
        return None

    @classmethod
    def _default_action_intent_expiry(cls, issued_at: str) -> str:
        try:
            issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise ValueError("issued_at_must_be_iso8601") from exc
        if issued.tzinfo is None or issued.utcoffset() is None:
            raise ValueError("issued_at_must_include_timezone")
        return (issued + cls.action_intent_ttl).isoformat()

    @staticmethod
    def _require_artifact_root_alias(value: str) -> str:
        if fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", value) is None:
            raise ValueError("artifact_root_alias must be a canonical root alias")
        return value

    @staticmethod
    def _build_plan_content(dispatch: OperationDispatchContract) -> str:
        steps = (
            "\n".join(
                f"{index}. {step}" for index, step in enumerate(dispatch.planned_steps, start=1)
            )
            or "1. Revisar objetivo e confirmar proxima acao segura."
        )
        constraints = ", ".join(dispatch.constraints)
        risks = OperationalService._risk_line(
            dispatch.plan_risks,
            "sem risco material relevante",
        )
        success = "; ".join(dispatch.success_criteria[:3]) or (
            "manter resposta coerente e reversivel"
        )
        internal_alignment = dispatch.specialist_summary or "sem ajuste interno adicional"
        next_action = dispatch.smallest_safe_next_action or "preservar a menor proxima acao segura"
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
        return (
            f"Plano deliberativo para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Criterios de sucesso: {success}\n"
            f"Proxima acao segura: {next_action}\n"
            f"Restricoes: {constraints}\n"
            f"Riscos: {risks}\n"
            f"Ajuste interno: {internal_alignment}\n"
            f"{arbitration_lines}\n"
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
            f"Etapas:\n{steps}\n"
        )

    @staticmethod
    def _build_analysis_content(dispatch: OperationDispatchContract) -> str:
        domains = OperationalService._domain_line(dispatch.domain_hints)
        risks = OperationalService._risk_line(
            dispatch.plan_risks,
            "nenhum relevante no escopo local",
        )
        success = "; ".join(dispatch.success_criteria[:3]) or ("explicitar a melhor recomendacao")
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
        return (
            f"Analise deliberativa para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Dominios sugeridos: {domains}\n"
            f"Criterios de sucesso: {success}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"Riscos mapeados: {risks}\n"
            f"{arbitration_lines}\n"
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
        )

    @staticmethod
    def _build_general_content(dispatch: OperationDispatchContract) -> str:
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
        return (
            f"Resposta deliberativa segura para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Orientacao principal: {dispatch.plan_rationale or 'sem rationale adicional'}\n"
            f"Proxima acao segura: "
            f"{dispatch.smallest_safe_next_action or 'preservar direcao segura'}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"{arbitration_lines}\n"
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
            "A saida foi produzida dentro do escopo local e reversivel do v1.\n"
        )

    @staticmethod
    def _mind_domain_specialist_lines(dispatch: OperationDispatchContract) -> str:
        status = dispatch.mind_domain_specialist_contract_status or "not_applicable"
        summary = dispatch.mind_domain_specialist_contract_summary or "contrato nao explicitado"
        chain = dispatch.mind_domain_specialist_contract_chain or "none"
        consumer_mode = dispatch.mind_domain_specialist_consumer_mode or "not_defined"
        framing_mode = dispatch.mind_domain_specialist_framing_mode or "not_defined"
        continuity_mode = dispatch.mind_domain_specialist_continuity_mode or "not_defined"
        return (
            f"Mind-domain-specialist status: {status}\n"
            f"Mind-domain-specialist summary: {summary}\n"
            f"Mind-domain-specialist chain: {chain}\n"
            f"Mind-domain-specialist consumer mode: {consumer_mode}\n"
            f"Mind-domain-specialist framing mode: {framing_mode}\n"
            f"Mind-domain-specialist continuity mode: {continuity_mode}"
        )

    @staticmethod
    def _ecosystem_state_lines(dispatch: OperationDispatchContract) -> str:
        work_items = "; ".join(dispatch.active_work_items) or "none"
        artifact_refs = "; ".join(dispatch.active_artifact_refs) or "none"
        checkpoint_refs = "; ".join(dispatch.open_checkpoint_refs) or "none"
        surface_presence = "; ".join(dispatch.surface_presence) or "none"
        status = dispatch.ecosystem_state_status or "not_applicable"
        summary = dispatch.ecosystem_state_summary or "state not summarized"
        return (
            f"Ecosystem state status: {status}\n"
            f"Ecosystem state summary: {summary}\n"
            f"Active work items: {work_items}\n"
            f"Active artifact refs: {artifact_refs}\n"
            f"Open checkpoint refs: {checkpoint_refs}\n"
            f"Surface presence: {surface_presence}"
        )

    @staticmethod
    def _project_objective_lines(dispatch: OperationDispatchContract) -> str:
        work_items = "; ".join(dispatch.work_item_refs) or "none"
        checkpoints = "; ".join(dispatch.checkpoint_refs) or "none"
        artifacts = "; ".join(dispatch.artifact_refs) or "none"
        return (
            f"Project objective status: {dispatch.objective_status or 'not_applicable'}\n"
            f"Project ref: {dispatch.project_ref or 'none'}\n"
            f"Objective ref: {dispatch.objective_ref or 'none'}\n"
            f"Work item refs: {work_items}\n"
            f"Checkpoint refs: {checkpoints}\n"
            f"Artifact refs: {artifacts}\n"
            f"Next action ref: {dispatch.next_action_ref or 'none'}"
        )

    @staticmethod
    def _project_artifact_refs(
        dispatch: OperationDispatchContract,
        artifacts: list[ArtifactResultContract],
    ) -> list[str]:
        refs: list[str] = []
        for item in [
            *list(dispatch.artifact_refs),
            *(artifact.location_ref for artifact in artifacts if artifact.location_ref),
        ]:
            if item and item not in refs:
                refs.append(item)
        return refs

    @staticmethod
    def _workflow_lines(dispatch: OperationDispatchContract) -> str:
        if not dispatch.workflow_profile:
            return "Workflow: not_defined"
        objective = dispatch.workflow_objective or dispatch.task_goal
        deliverables = "; ".join(dispatch.workflow_expected_deliverables) or "none"
        telemetry_focus = "; ".join(dispatch.workflow_telemetry_focus) or "none"
        steps = "; ".join(dispatch.workflow_steps) or "none"
        governance_mode = dispatch.workflow_governance_mode or "not_defined"
        return (
            f"Workflow: {dispatch.workflow_profile}\n"
            f"Workflow domain route: {dispatch.workflow_domain_route or 'fallback'}\n"
            f"Objetivo do workflow: {objective}\n"
            f"Workflow deliverables: {deliverables}\n"
            f"Workflow telemetry focus: {telemetry_focus}\n"
            f"Workflow success focus: {dispatch.workflow_success_focus or 'not_defined'}\n"
            f"Workflow response focus: {dispatch.workflow_response_focus or 'not_defined'}\n"
            f"Workflow state inicial: {dispatch.workflow_state or 'composed'}\n"
            f"Workflow governance: {governance_mode}\n"
            f"Workflow steps: {steps}"
        )

    @staticmethod
    def _workflow_decision_line(dispatch: OperationDispatchContract) -> str:
        decision_points = "; ".join(dispatch.workflow_decision_points) or "none"
        return f"Workflow decision points: {decision_points}"

    @staticmethod
    def _workflow_decisions(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
    ) -> list[str]:
        decision_points = list(dispatch.workflow_decision_points)
        if not successful:
            return decision_points[:1]
        return decision_points

    @staticmethod
    def _workflow_checkpoint_state(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
    ) -> dict[str, str]:
        if not dispatch.workflow_checkpoints:
            return {}
        if successful:
            return {checkpoint: "completed" for checkpoint in dispatch.workflow_checkpoints}
        state = dict(dispatch.workflow_checkpoint_state)
        if not state:
            return {}
        first_checkpoint = dispatch.workflow_checkpoints[0]
        state[first_checkpoint] = "completed"
        for checkpoint in dispatch.workflow_checkpoints[1:]:
            state[checkpoint] = "pending"
        return state

    @staticmethod
    def _workflow_resume_outcome(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
        pending_checkpoints: list[str],
    ) -> tuple[str, str | None]:
        resume_point = dispatch.workflow_resume_point or dispatch.smallest_safe_next_action
        if not successful:
            return ("resume_blocked", resume_point)
        if dispatch.workflow_resume_status == "resume_available":
            return ("resumed_from_checkpoint", resume_point)
        if dispatch.requires_human_validation and resume_point:
            return ("checkpointed_for_manual_resume", resume_point)
        if resume_point or pending_checkpoints:
            return ("checkpointed_for_followup", resume_point)
        return ("completed_without_resume", None)

    @staticmethod
    def _active_artifact_refs(
        dispatch: OperationDispatchContract,
        artifact_results: list[ArtifactResultContract],
    ) -> list[str]:
        refs = list(dispatch.active_artifact_refs)
        for artifact in artifact_results:
            if artifact.location_ref and artifact.location_ref not in refs:
                refs.append(artifact.location_ref)
        return refs

    @staticmethod
    def _ecosystem_state_status(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        if not (
            active_work_items or active_artifact_refs or open_checkpoint_refs or surface_presence
        ):
            return "not_applicable"
        if (
            surface_presence
            and active_work_items
            and (active_artifact_refs or open_checkpoint_refs)
        ):
            return "operational_state_attached"
        return "partial_operational_state"

    @staticmethod
    def _ecosystem_state_summary(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        return (
            f"work_items={len(active_work_items)}; "
            f"artifacts={len(active_artifact_refs)}; "
            f"open_checkpoints={len(open_checkpoint_refs)}; "
            f"surfaces={len(surface_presence)}"
        )

    @staticmethod
    def _domain_line(domain_hints: list[str]) -> str:
        return ", ".join(domain_hints) if domain_hints else "assistencia_pessoal_e_operacional"

    @staticmethod
    def _risk_line(plan_risks: list[str], fallback: str) -> str:
        return ", ".join(plan_risks) if plan_risks else fallback

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
