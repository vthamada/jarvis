"""Recoverable orchestration for MB-217 physical/canonical artifact sagas.

The coordinator deliberately owns ordering, not authority.  Governance owns
the physical receipts, Operational owns the handle-safe filesystem boundary,
and Memory owns the immutable saga/canonical state.  A successful return is
therefore possible only after all three services agree on the exact evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Callable, Protocol

from operational_service.adapters.local_text_transaction import (
    LocalTextMutationRequest,
    LocalTextRollbackRequest,
)

from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_rollback_plan,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalOutboxDeliveryContract,
    ArtifactPhysicalOutboxItemContract,
    ArtifactPhysicalRollbackPlanContract,
    ArtifactPhysicalSagaStateContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
)
from shared.events import INTERNAL_EVENT_NAMES, InternalEventEnvelope

ArtifactPhysicalPlanContract = (
    ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract
)
FailureInjector = Callable[[str], None]
Clock = Callable[[], str]


class ArtifactPhysicalMemoryPort(Protocol):
    def reserve_artifact_physical_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
    ) -> ArtifactPhysicalSagaStateContract: ...

    def reserve_artifact_physical_rollback(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
    ) -> ArtifactPhysicalSagaStateContract: ...

    def advance_artifact_physical_apply(
        self,
        saga_id: str,
        *,
        phase: str,
        occurred_at: str,
    ) -> ArtifactPhysicalSagaStateContract: ...

    def advance_artifact_physical_rollback(
        self,
        saga_id: str,
        *,
        phase: str,
        occurred_at: str,
    ) -> ArtifactPhysicalSagaStateContract: ...

    def get_artifact_physical_apply_plan(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalApplyPlanContract | None: ...

    def get_artifact_physical_rollback_plan(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalRollbackPlanContract | None: ...

    def get_artifact_physical_saga(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalSagaStateContract | None: ...

    def commit_artifact_physical_apply(
        self,
        saga_id: str,
        *,
        receipt: LocalTextMutationReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

    def commit_artifact_physical_rollback(
        self,
        saga_id: str,
        *,
        receipt: LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

    def list_pending_artifact_physical_outbox(
        self,
        *,
        limit: int = 20,
    ) -> list[ArtifactPhysicalOutboxItemContract]: ...

    def get_artifact_physical_outbox_for_saga(
        self,
        saga_id: str,
    ) -> ArtifactPhysicalOutboxItemContract | None: ...

    def mark_artifact_physical_outbox_published(
        self,
        outbox_id: str,
        *,
        publisher_ref: str,
        published_at: str,
    ) -> ArtifactPhysicalOutboxDeliveryContract: ...


class ArtifactPhysicalGovernancePort(Protocol):
    def load_local_text_mutation_receipt_exact(
        self,
        operation_id: str,
        *,
        expected_receipt_fingerprint: str,
    ) -> LocalTextMutationReceipt: ...

    def load_local_text_rollback_receipt_exact(
        self,
        rollback_operation_id: str,
        *,
        expected_rollback_receipt_fingerprint: str,
    ) -> LocalTextRollbackReceipt: ...


class ArtifactPhysicalOperationalPort(Protocol):
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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...

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
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract: ...


class ArtifactPhysicalObservabilityPort(Protocol):
    def ingest_events(self, events: list[InternalEventEnvelope]) -> None: ...


@dataclass(frozen=True)
class ArtifactPhysicalSagaRunResult:
    """Exact durable result of one apply/rollback execution or recovery."""

    plan: ArtifactPhysicalPlanContract
    state: ArtifactPhysicalSagaStateContract
    commit_receipt: ArtifactPhysicalCanonicalCommitReceiptContract | None
    outbox_delivery: ArtifactPhysicalOutboxDeliveryContract | None
    published_event: InternalEventEnvelope | None


class ArtifactPhysicalSagaCoordinator:
    """Sequence physical effects, canonical commits and outbox delivery safely."""

    publisher_ref = "orchestrator-service/artifact-physical-saga"

    def __init__(
        self,
        *,
        memory: ArtifactPhysicalMemoryPort,
        governance: ArtifactPhysicalGovernancePort,
        operational: ArtifactPhysicalOperationalPort,
        observability: ArtifactPhysicalObservabilityPort,
        now: Clock | None = None,
        failure_injector: FailureInjector | None = None,
    ) -> None:
        self._memory = memory
        self._governance = governance
        self._operational = operational
        self._observability = observability
        self._now = now or (lambda: datetime.now(UTC).isoformat())
        self._failure_injector = failure_injector

    def execute_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
        request: LocalTextMutationRequest,
    ) -> ArtifactPhysicalSagaRunResult:
        """Reserve, execute and canonically activate exactly one physical version."""

        self._require_apply_request_binding(plan, request)
        state = self._memory.reserve_artifact_physical_apply(plan)
        self._fail("after_apply_reservation")
        if state.phase == "reserved":
            state = self._memory.advance_artifact_physical_apply(
                plan.saga_id,
                phase="effect_dispatched",
                occurred_at=self._now(),
            )
        self._fail("after_apply_effect_dispatched")
        if state.phase == "effect_dispatched":
            commit_receipt = self._operational.execute_and_commit_local_text_file_apply(
                plan,
                request,
                canonical_commit=self._commit_apply,
            )
            self._fail("after_apply_canonical_commit")
        else:
            commit_receipt = self._existing_commit_or_raise(plan, state)
        return self._finalize(plan, commit_receipt)

    def recover_apply(
        self,
        saga_id: str,
        *,
        request: LocalTextMutationRequest | None = None,
    ) -> ArtifactPhysicalSagaRunResult:
        """Recover one apply from durable checkpoints without minting new authority."""

        plan = self._memory.get_artifact_physical_apply_plan(saga_id)
        if plan is None:
            raise KeyError("unknown artifact physical apply saga")
        require_valid_artifact_physical_apply_plan(plan)
        state = self._require_state(saga_id)
        if state.phase == "reserved":
            if request is None:
                raise ValueError("artifact_physical_apply_request_required_before_dispatch")
            self._require_apply_request_binding(plan, request)
            state = self._memory.advance_artifact_physical_apply(
                saga_id,
                phase="effect_dispatched",
                occurred_at=self._now(),
            )
        if state.phase == "effect_dispatched":
            if request is not None:
                self._require_apply_request_binding(plan, request)
                commit_receipt = self._operational.execute_and_commit_local_text_file_apply(
                    plan,
                    request,
                    canonical_commit=self._commit_apply,
                )
            else:
                commit_receipt = self._operational.recover_and_commit_local_text_file_apply(
                    plan=plan,
                    root_alias=plan.root_alias,
                    operation_id=plan.physical_operation_id,
                    canonical_commit=self._commit_apply,
                )
            self._fail("after_apply_canonical_commit")
        elif state.phase == "physical_applied":
            commit_receipt = self._commit_apply_from_persisted_receipt(plan, state)
        else:
            commit_receipt = self._existing_commit_or_raise(plan, state)
        return self._finalize(plan, commit_receipt)

    def execute_rollback(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
        request: LocalTextRollbackRequest,
    ) -> ArtifactPhysicalSagaRunResult:
        """Reserve and execute one independently authorized rollback saga."""

        self._require_rollback_request_binding(plan, request)
        state = self._memory.reserve_artifact_physical_rollback(plan)
        self._fail("after_rollback_reservation")
        if state.phase == "rollback_reserved":
            state = self._memory.advance_artifact_physical_rollback(
                plan.saga_id,
                phase="rollback_effect_dispatched",
                occurred_at=self._now(),
            )
        self._fail("after_rollback_effect_dispatched")
        if state.phase == "rollback_effect_dispatched":
            commit_receipt = self._operational.rollback_and_commit_local_text_file(
                plan,
                request,
                canonical_commit=self._commit_rollback,
            )
            self._fail("after_rollback_canonical_commit")
        else:
            commit_receipt = self._existing_commit_or_raise(plan, state)
        return self._finalize(plan, commit_receipt)

    def recover_rollback(
        self,
        saga_id: str,
        *,
        request: LocalTextRollbackRequest | None = None,
    ) -> ArtifactPhysicalSagaRunResult:
        """Recover one rollback from its immutable plan and historical claim."""

        plan = self._memory.get_artifact_physical_rollback_plan(saga_id)
        if plan is None:
            raise KeyError("unknown artifact physical rollback saga")
        require_valid_artifact_physical_rollback_plan(plan)
        state = self._require_state(saga_id)
        if state.phase == "rollback_reserved":
            if request is None:
                raise ValueError("artifact_physical_rollback_request_required_before_dispatch")
            self._require_rollback_request_binding(plan, request)
            state = self._memory.advance_artifact_physical_rollback(
                saga_id,
                phase="rollback_effect_dispatched",
                occurred_at=self._now(),
            )
        if state.phase == "rollback_effect_dispatched":
            if request is not None:
                self._require_rollback_request_binding(plan, request)
                commit_receipt = self._operational.rollback_and_commit_local_text_file(
                    plan,
                    request,
                    canonical_commit=self._commit_rollback,
                )
            else:
                commit_receipt = self._operational.recover_and_commit_local_text_file_rollback(
                    plan=plan,
                    root_alias=plan.root_alias,
                    operation_id=plan.physical_operation_id,
                    canonical_commit=self._commit_rollback,
                )
            self._fail("after_rollback_canonical_commit")
        elif state.phase == "physically_rolled_back":
            commit_receipt = self._commit_rollback_from_persisted_receipt(plan, state)
        else:
            commit_receipt = self._existing_commit_or_raise(plan, state)
        return self._finalize(plan, commit_receipt)

    def deliver_pending_outbox(
        self,
        *,
        saga_id: str,
    ) -> tuple[
        ArtifactPhysicalOutboxDeliveryContract | None,
        InternalEventEnvelope | None,
    ]:
        """Publish the canonical item with a stable event identity, then mark delivery."""

        state = self._require_state(saga_id)
        if state.phase == "completed":
            return None, None
        outbox = self._memory.get_artifact_physical_outbox_for_saga(saga_id)
        if outbox is None:
            raise ValueError("artifact_physical_outbox_missing_for_committed_saga")
        if outbox.event_name not in INTERNAL_EVENT_NAMES:
            raise ValueError("artifact_physical_outbox_event_name_unregistered")
        event = InternalEventEnvelope(
            event_id=outbox.outbox_id,
            event_name=outbox.event_name,
            timestamp=outbox.created_at,
            source_service=self.publisher_ref,
            payload=asdict(outbox),
            correlation_id=outbox.saga_id,
            mission_id=str(outbox.mission_id),
            tags=["artifact_physical_saga", "canonical_outbox"],
        )
        self._observability.ingest_events([event])
        self._fail("after_artifact_physical_outbox_publish")
        # The timestamp is deliberately stable across response-loss retries.  The
        # immutable delivery identity is stronger than wall-clock attempt time.
        delivery = self._memory.mark_artifact_physical_outbox_published(
            outbox.outbox_id,
            publisher_ref=self.publisher_ref,
            published_at=outbox.created_at,
        )
        self._fail("after_artifact_physical_outbox_delivery")
        return delivery, event

    def _commit_apply(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
        receipt: LocalTextMutationReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        self._fail("before_apply_canonical_commit")
        result = self._memory.commit_artifact_physical_apply(
            plan.saga_id,
            receipt=receipt,
            attestation=attestation,
        )
        self._fail("after_apply_memory_commit_before_ack")
        return result

    def _commit_rollback(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
        receipt: LocalTextRollbackReceipt,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        self._fail("before_rollback_canonical_commit")
        result = self._memory.commit_artifact_physical_rollback(
            plan.saga_id,
            receipt=receipt,
            attestation=attestation,
        )
        self._fail("after_rollback_memory_commit_before_ack")
        return result

    def _commit_apply_from_persisted_receipt(
        self,
        plan: ArtifactPhysicalApplyPlanContract,
        state: ArtifactPhysicalSagaStateContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        if state.mutation_receipt_fingerprint is None:
            raise ValueError("artifact_physical_apply_receipt_checkpoint_missing")
        receipt = self._governance.load_local_text_mutation_receipt_exact(
            plan.physical_operation_id,
            expected_receipt_fingerprint=state.mutation_receipt_fingerprint,
        )
        return self._operational.commit_local_text_file_mutation_if_current(
            plan=plan,
            root_alias=plan.root_alias,
            receipt=receipt,
            canonical_commit=self._commit_apply,
        )

    def _commit_rollback_from_persisted_receipt(
        self,
        plan: ArtifactPhysicalRollbackPlanContract,
        state: ArtifactPhysicalSagaStateContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract:
        if state.rollback_receipt_fingerprint is None:
            raise ValueError("artifact_physical_rollback_receipt_checkpoint_missing")
        receipt = self._governance.load_local_text_rollback_receipt_exact(
            plan.physical_operation_id,
            expected_rollback_receipt_fingerprint=state.rollback_receipt_fingerprint,
        )
        return self._operational.commit_local_text_file_rollback_if_current(
            plan=plan,
            root_alias=plan.root_alias,
            receipt=receipt,
            canonical_commit=self._commit_rollback,
        )

    def _existing_commit_or_raise(
        self,
        plan: ArtifactPhysicalPlanContract,
        state: ArtifactPhysicalSagaStateContract,
    ) -> ArtifactPhysicalCanonicalCommitReceiptContract | None:
        allowed = (
            {"canonical_committed", "completed"}
            if plan.purpose == "apply"
            else {"canonical_rolled_back", "compensation_committed", "completed"}
        )
        if state.phase not in allowed:
            raise ValueError(f"artifact_physical_saga_requires_reconciliation:{state.phase}")
        verifier = getattr(
            self._memory,
            "get_artifact_physical_canonical_commit_receipt",
            None,
        )
        if verifier is None:
            verifier = getattr(
                self._memory,
                "get_artifact_physical_commit_receipt",
                None,
            )
        if verifier is None:
            if state.phase == "completed":
                return None
            raise ValueError("artifact_physical_commit_receipt_lookup_unavailable")
        receipt = verifier(plan.saga_id)
        if receipt is None and state.phase != "completed":
            raise ValueError("artifact_physical_commit_receipt_missing")
        return receipt

    def _finalize(
        self,
        plan: ArtifactPhysicalPlanContract,
        commit_receipt: ArtifactPhysicalCanonicalCommitReceiptContract | None,
    ) -> ArtifactPhysicalSagaRunResult:
        state = self._require_state(plan.saga_id)
        if state.phase == "completed":
            return ArtifactPhysicalSagaRunResult(plan, state, commit_receipt, None, None)
        delivery, event = self.deliver_pending_outbox(saga_id=plan.saga_id)
        final_state = self._require_state(plan.saga_id)
        if final_state.phase != "completed":
            raise ValueError("artifact_physical_saga_not_completed_after_outbox_delivery")
        return ArtifactPhysicalSagaRunResult(
            plan=plan,
            state=final_state,
            commit_receipt=commit_receipt,
            outbox_delivery=delivery,
            published_event=event,
        )

    def _require_state(self, saga_id: str) -> ArtifactPhysicalSagaStateContract:
        state = self._memory.get_artifact_physical_saga(saga_id)
        if state is None:
            raise KeyError("unknown artifact physical saga")
        return state

    @staticmethod
    def _require_apply_request_binding(
        plan: ArtifactPhysicalApplyPlanContract,
        request: LocalTextMutationRequest,
    ) -> None:
        require_valid_artifact_physical_apply_plan(plan)
        preflight = request.preflight
        if (
            request.operation_id != plan.physical_operation_id
            or preflight.resource_ref != plan.resource_ref
            or preflight.root_alias != plan.root_alias
            or preflight.preflight_fingerprint != plan.preflight_fingerprint
            or preflight.root_config_fingerprint != plan.root_config_fingerprint
            or preflight.preflight_policy_version != plan.preflight_policy_version
            or preflight.adapter_backend_version != plan.adapter_backend_version
            or preflight.before_content_sha256 != plan.before_content_sha256
            or preflight.desired_content_sha256 != plan.desired_content_sha256
            or preflight.rollback_plan.rollback_fingerprint != plan.rollback_plan_ref
        ):
            raise ValueError("artifact_physical_apply_request_plan_mismatch")

    @staticmethod
    def _require_rollback_request_binding(
        plan: ArtifactPhysicalRollbackPlanContract,
        request: LocalTextRollbackRequest,
    ) -> None:
        require_valid_artifact_physical_rollback_plan(plan)
        receipt = request.receipt
        if (
            request.rollback_operation_id != plan.physical_operation_id
            or receipt.operation_id != plan.mutation_operation_id
            or receipt.receipt_fingerprint != plan.mutation_receipt_fingerprint
            or receipt.resource_ref != plan.resource_ref
            or receipt.desired_content_sha256 != plan.expected_current_sha256
            or receipt.before_content_sha256 != plan.restored_content_sha256
        ):
            raise ValueError("artifact_physical_rollback_request_plan_mismatch")

    def _fail(self, boundary: str) -> None:
        if self._failure_injector is not None:
            self._failure_injector(boundary)
