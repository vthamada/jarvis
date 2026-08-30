"""One-shot provenance for fresh MB-217 physical-state attestations.

SHA-256 seals protect integrity, not provenance.  This authority supplies the
missing in-process capability: Operational opens a lease while it still owns
the resource lock, and Memory consumes the exact receipt/attestation pair once
inside the canonical callback.  The lease is deliberately ephemeral; restart
recovery must perform a new physical observation and issue a new lease.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock, get_ident, local
from typing import Iterator

from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_rollback_plan,
    require_valid_local_text_physical_state_attestation,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalRollbackPlanContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
)
from shared.local_text_rollback_permissions import (
    require_valid_local_text_mutation_receipt,
    require_valid_local_text_rollback_receipt,
)

ArtifactPhysicalPlanContract = (
    ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract
)
ArtifactPhysicalReceiptContract = LocalTextMutationReceipt | LocalTextRollbackReceipt


@dataclass(frozen=True)
class _LeaseBinding:
    thread_id: int
    purpose: str
    saga_id: str
    plan_fingerprint: str
    receipt: ArtifactPhysicalReceiptContract
    attestation: LocalTextPhysicalStateAttestationContract


class ArtifactPhysicalAttestationLeaseAuthority:
    """Issue and consume exact same-thread attestation capabilities."""

    def __init__(self) -> None:
        self._thread_state = local()
        self._state_lock = RLock()

    @contextmanager
    def issue(
        self,
        plan: ArtifactPhysicalPlanContract,
        receipt: ArtifactPhysicalReceiptContract,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> Iterator[None]:
        """Open one capability for the duration of a canonical callback."""

        binding = self._validated_binding(plan, receipt, attestation)
        with self._state_lock:
            if getattr(self._thread_state, "binding", None) is not None:
                raise ValueError("artifact_physical_attestation_lease_nested")
            self._thread_state.binding = binding
            self._thread_state.consumed = False
        try:
            yield
        finally:
            with self._state_lock:
                self._thread_state.binding = None
                self._thread_state.consumed = False

    def verify_and_consume(
        self,
        receipt: ArtifactPhysicalReceiptContract,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> bool:
        """Consume the exact active capability once on its issuing thread."""

        try:
            self._validate_receipt_attestation(receipt, attestation)
        except (TypeError, ValueError):
            return False
        with self._state_lock:
            binding = getattr(self._thread_state, "binding", None)
            consumed = bool(getattr(self._thread_state, "consumed", False))
            if (
                not isinstance(binding, _LeaseBinding)
                or consumed
                or binding.thread_id != get_ident()
                or binding.receipt != receipt
                or binding.attestation != attestation
            ):
                return False
            self._thread_state.consumed = True
            return True

    @classmethod
    def _validated_binding(
        cls,
        plan: ArtifactPhysicalPlanContract,
        receipt: ArtifactPhysicalReceiptContract,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> _LeaseBinding:
        cls._validate_receipt_attestation(receipt, attestation)
        if isinstance(plan, ArtifactPhysicalApplyPlanContract):
            require_valid_artifact_physical_apply_plan(plan)
            if not isinstance(receipt, LocalTextMutationReceipt):
                raise ValueError("artifact_physical_apply_attestation_receipt_invalid")
            receipt_fingerprint = receipt.receipt_fingerprint
            if (
                plan.physical_operation_id != receipt.operation_id
                or plan.resource_ref != receipt.resource_ref
                or attestation.purpose != "mutation_current"
            ):
                raise ValueError("artifact_physical_apply_attestation_lease_mismatch")
        elif isinstance(plan, ArtifactPhysicalRollbackPlanContract):
            require_valid_artifact_physical_rollback_plan(plan)
            if not isinstance(receipt, LocalTextRollbackReceipt):
                raise ValueError("artifact_physical_rollback_attestation_receipt_invalid")
            receipt_fingerprint = receipt.rollback_receipt_fingerprint
            if (
                plan.physical_operation_id != receipt.operation_id
                or plan.mutation_operation_id != receipt.mutation_operation_id
                or plan.resource_ref != receipt.resource_ref
                or attestation.purpose != "rollback_current"
            ):
                raise ValueError("artifact_physical_rollback_attestation_lease_mismatch")
        else:
            raise TypeError("artifact physical attestation plan type is invalid")
        if (
            attestation.receipt_fingerprint != receipt_fingerprint
            or attestation.resource_ref != plan.resource_ref
            or attestation.root_alias != plan.root_alias
        ):
            raise ValueError("artifact_physical_attestation_lease_binding_mismatch")
        return _LeaseBinding(
            thread_id=get_ident(),
            purpose=plan.purpose,
            saga_id=plan.saga_id,
            plan_fingerprint=plan.plan_fingerprint,
            receipt=receipt,
            attestation=attestation,
        )

    @staticmethod
    def _validate_receipt_attestation(
        receipt: ArtifactPhysicalReceiptContract,
        attestation: LocalTextPhysicalStateAttestationContract,
    ) -> None:
        if isinstance(receipt, LocalTextMutationReceipt):
            require_valid_local_text_mutation_receipt(receipt)
        elif isinstance(receipt, LocalTextRollbackReceipt):
            require_valid_local_text_rollback_receipt(receipt)
        else:
            raise TypeError("artifact physical attestation receipt type is invalid")
        require_valid_local_text_physical_state_attestation(attestation)
