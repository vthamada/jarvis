from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import pytest
from orchestrator_service.artifact_physical_saga import ArtifactPhysicalSagaCoordinator

from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_canonical_commit_receipt,
    seal_artifact_physical_outbox_delivery,
    seal_artifact_physical_outbox_item,
    seal_artifact_physical_saga_state,
    seal_local_text_physical_state_attestation,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalOutboxDeliveryContract,
    ArtifactPhysicalOutboxItemContract,
    ArtifactPhysicalSagaStateContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
)
from shared.events import InternalEventEnvelope
from shared.types import MissionId


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _apply_plan() -> ArtifactPhysicalApplyPlanContract:
    return seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id="artifact-physical-saga:apply:unit-1",
            mission_id=MissionId("mission://artifact-physical/unit"),
            artifact_ref="artifact://artifact-physical/unit/v1",
            artifact_version=1,
            owner_mission_id=MissionId("mission://artifact-physical/unit"),
            objective_ref="objective://artifact-physical/unit",
            work_item_ref="work-item://artifact-physical/unit",
            lineage_root_ref="artifact://artifact-physical/unit/v1",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id="operation://artifact-physical/unit/apply",
            resource_ref="text:notes/unit.txt",
            root_alias="notes",
            preflight_fingerprint=_digest("preflight"),
            root_config_fingerprint=_digest("root"),
            preflight_policy_version="local-text-preflight/1.0.0",
            transaction_policy_version="local-text-transaction/1.0.0",
            transaction_backend_version="posix-openat-1.0.0",
            adapter_backend_version="local-text-openat/1.0.0",
            before_content_sha256=_digest("before"),
            desired_content_sha256=_digest("desired"),
            rollback_plan_ref=_digest("rollback-plan"),
            expected_lineage_revision=0,
            created_at="2026-08-30T12:00:00+00:00",
            plan_fingerprint="0" * 64,
        )
    )


def _request(plan: ArtifactPhysicalApplyPlanContract) -> SimpleNamespace:
    preflight = SimpleNamespace(
        resource_ref=plan.resource_ref,
        root_alias=plan.root_alias,
        preflight_fingerprint=plan.preflight_fingerprint,
        root_config_fingerprint=plan.root_config_fingerprint,
        preflight_policy_version=plan.preflight_policy_version,
        adapter_backend_version=plan.adapter_backend_version,
        before_content_sha256=plan.before_content_sha256,
        desired_content_sha256=plan.desired_content_sha256,
        rollback_plan=SimpleNamespace(rollback_fingerprint=plan.rollback_plan_ref),
    )
    return SimpleNamespace(operation_id=plan.physical_operation_id, preflight=preflight)


def _state(
    plan: ArtifactPhysicalApplyPlanContract,
    phase: str,
    *,
    sequence: int,
    mutation_receipt_fingerprint: str | None = None,
    attestation_fingerprint: str | None = None,
) -> ArtifactPhysicalSagaStateContract:
    return seal_artifact_physical_saga_state(
        ArtifactPhysicalSagaStateContract(
            saga_id=plan.saga_id,
            purpose=plan.purpose,
            mission_id=plan.mission_id,
            physical_operation_id=plan.physical_operation_id,
            plan_fingerprint=plan.plan_fingerprint,
            phase=phase,
            latest_sequence=sequence,
            latest_event_fingerprint=_digest(f"event:{phase}:{sequence}"),
            mutation_receipt_fingerprint=mutation_receipt_fingerprint,
            rollback_receipt_fingerprint=None,
            physical_state_attestation_fingerprint=attestation_fingerprint,
            updated_at=f"2026-08-30T12:00:0{sequence}+00:00",
            state_fingerprint="0" * 64,
        )
    )


def _mutation_receipt(plan: ArtifactPhysicalApplyPlanContract) -> LocalTextMutationReceipt:
    receipt = LocalTextMutationReceipt(
        operation_id=plan.physical_operation_id,
        execution_grant_id="grant://artifact-physical/unit",
        execution_claim_id="claim://artifact-physical/unit",
        operation="create_text",
        resource_ref=plan.resource_ref,
        subject_ref="operator://artifact-physical/unit",
        preflight_fingerprint=plan.preflight_fingerprint,
        before_content_sha256=plan.before_content_sha256,
        desired_content_sha256=plan.desired_content_sha256,
        root_config_fingerprint=plan.root_config_fingerprint,
        applied_event_fingerprint=_digest("applied-event"),
        committed_at="2026-08-30T12:00:02+00:00",
        mutation_status="applied",
        receipt_fingerprint=_digest("mutation-receipt"),
    )
    return receipt


def _attestation(
    plan: ArtifactPhysicalApplyPlanContract,
    receipt: LocalTextMutationReceipt,
) -> LocalTextPhysicalStateAttestationContract:
    return seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id="attestation://artifact-physical/unit",
            purpose="mutation_current",
            receipt_fingerprint=receipt.receipt_fingerprint,
            mutation_operation_id=receipt.operation_id,
            rollback_operation_id=None,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            root_config_fingerprint=plan.root_config_fingerprint,
            physical_state="applied",
            observed_content_sha256=plan.desired_content_sha256,
            observed_identity_fingerprint=_digest("identity"),
            journal_event_fingerprint=receipt.applied_event_fingerprint,
            transaction_policy_version=plan.transaction_policy_version,
            transaction_backend_version=plan.transaction_backend_version,
            verified_at="2026-08-30T12:00:03+00:00",
            attestation_fingerprint="0" * 64,
        )
    )


class _Memory:
    def __init__(self, plan: ArtifactPhysicalApplyPlanContract) -> None:
        self.plan = plan
        self.state = _state(plan, "reserved", sequence=1)
        self.commit_receipt: ArtifactPhysicalCanonicalCommitReceiptContract | None = None
        self.outbox: ArtifactPhysicalOutboxItemContract | None = None
        self.delivery: ArtifactPhysicalOutboxDeliveryContract | None = None
        self.commit_calls = 0

    def reserve_artifact_physical_apply(self, plan):
        assert plan == self.plan
        return self.state

    def advance_artifact_physical_apply(self, saga_id, *, phase, occurred_at):
        assert saga_id == self.plan.saga_id
        assert phase == "effect_dispatched"
        self.state = _state(self.plan, phase, sequence=2)
        return self.state

    def get_artifact_physical_apply_plan(self, saga_id):
        if saga_id != self.plan.saga_id:
            raise KeyError(saga_id)
        return self.plan

    def get_artifact_physical_saga(self, saga_id):
        if saga_id != self.plan.saga_id:
            raise KeyError(saga_id)
        return self.state

    def commit_artifact_physical_apply(self, saga_id, *, receipt, attestation):
        assert saga_id == self.plan.saga_id
        self.commit_calls += 1
        if self.commit_receipt is not None:
            return self.commit_receipt
        canonical_event = _digest("canonical-event")
        self.commit_receipt = seal_artifact_physical_canonical_commit_receipt(
            ArtifactPhysicalCanonicalCommitReceiptContract(
                commit_id=f"{saga_id}:commit",
                purpose="apply",
                saga_id=saga_id,
                plan_fingerprint=self.plan.plan_fingerprint,
                mission_id=self.plan.mission_id,
                artifact_ref=self.plan.artifact_ref,
                artifact_version=1,
                lineage_root_ref=self.plan.lineage_root_ref,
                lineage_revision=1,
                physical_operation_id=self.plan.physical_operation_id,
                resource_ref=self.plan.resource_ref,
                root_alias=self.plan.root_alias,
                mutation_receipt_fingerprint=receipt.receipt_fingerprint,
                rollback_receipt_fingerprint=None,
                physical_state_attestation_fingerprint=attestation.attestation_fingerprint,
                canonical_event_fingerprint=canonical_event,
                committed_at=attestation.verified_at,
                commit_fingerprint="0" * 64,
            )
        )
        self.outbox = seal_artifact_physical_outbox_item(
            ArtifactPhysicalOutboxItemContract(
                outbox_id=f"{saga_id}:outbox",
                saga_id=saga_id,
                purpose="apply",
                event_name="artifact_lifecycle_state_changed",
                mission_id=self.plan.mission_id,
                artifact_ref=self.plan.artifact_ref,
                lineage_root_ref=self.plan.lineage_root_ref,
                canonical_event_fingerprint=canonical_event,
                created_at=attestation.verified_at,
                outbox_fingerprint="0" * 64,
            )
        )
        self.state = _state(
            self.plan,
            "canonical_committed",
            sequence=4,
            mutation_receipt_fingerprint=receipt.receipt_fingerprint,
            attestation_fingerprint=attestation.attestation_fingerprint,
        )
        return self.commit_receipt

    def get_artifact_physical_canonical_commit_receipt(self, saga_id):
        assert saga_id == self.plan.saga_id
        return self.commit_receipt

    def get_artifact_physical_outbox_for_saga(self, saga_id):
        assert saga_id == self.plan.saga_id
        return self.outbox

    def list_pending_artifact_physical_outbox(self, *, limit=20):
        return [self.outbox] if self.outbox is not None and self.delivery is None else []

    def mark_artifact_physical_outbox_published(
        self,
        outbox_id,
        *,
        publisher_ref,
        published_at,
    ):
        assert self.outbox is not None and outbox_id == self.outbox.outbox_id
        if self.delivery is None:
            self.delivery = seal_artifact_physical_outbox_delivery(
                ArtifactPhysicalOutboxDeliveryContract(
                    delivery_id=f"{outbox_id}:delivery",
                    outbox_id=outbox_id,
                    publisher_ref=publisher_ref,
                    published_at=published_at,
                    delivery_fingerprint="0" * 64,
                )
            )
            self.state = _state(
                self.plan,
                "completed",
                sequence=5,
                mutation_receipt_fingerprint=(
                    self.commit_receipt.mutation_receipt_fingerprint
                    if self.commit_receipt
                    else None
                ),
                attestation_fingerprint=(
                    self.commit_receipt.physical_state_attestation_fingerprint
                    if self.commit_receipt
                    else None
                ),
            )
        return self.delivery


class _Operational:
    def __init__(self, receipt, attestation) -> None:
        self.receipt = receipt
        self.attestation = attestation
        self.physical_calls = 0

    def execute_and_commit_local_text_file_apply(
        self,
        plan,
        request,
        *,
        canonical_commit,
    ):
        self.physical_calls += 1
        return canonical_commit(plan, self.receipt, self.attestation)

    def recover_and_commit_local_text_file_apply(self, **kwargs):
        self.physical_calls += 1
        return kwargs["canonical_commit"](kwargs["plan"], self.receipt, self.attestation)


class _Governance:
    pass


class _Observability:
    def __init__(self) -> None:
        self.attempts = 0
        self.events: dict[str, InternalEventEnvelope] = {}

    def ingest_events(self, events):
        for event in events:
            self.attempts += 1
            existing = self.events.get(event.event_id)
            if existing is not None and existing != event:
                raise ValueError("observability event identity is immutable")
            self.events[event.event_id] = event


def _coordinator(memory, operational, observability, failure_injector=None):
    return ArtifactPhysicalSagaCoordinator(
        memory=memory,
        governance=_Governance(),
        operational=operational,
        observability=observability,
        now=lambda: "2026-08-30T12:00:01+00:00",
        failure_injector=failure_injector,
    )


def test_apply_returns_only_after_canonical_commit_and_outbox_delivery() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)
    operational = _Operational(receipt, _attestation(plan, receipt))
    observability = _Observability()

    result = _coordinator(memory, operational, observability).execute_apply(
        plan,
        _request(plan),
    )

    assert result.state.phase == "completed"
    assert result.commit_receipt == memory.commit_receipt
    assert result.outbox_delivery == memory.delivery
    assert result.published_event is not None
    assert result.published_event.payload["contains_content"] is False
    assert operational.physical_calls == 1
    assert memory.commit_calls == 1
    assert len(observability.events) == 1


def test_response_loss_after_memory_commit_recovers_without_repeating_physical_effect() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)
    operational = _Operational(receipt, _attestation(plan, receipt))
    observability = _Observability()

    def fail(boundary: str) -> None:
        if boundary == "after_apply_memory_commit_before_ack":
            raise RuntimeError("simulated response loss")

    with pytest.raises(RuntimeError, match="response loss"):
        _coordinator(memory, operational, observability, fail).execute_apply(
            plan,
            _request(plan),
        )

    assert memory.state.phase == "canonical_committed"
    recovered = _coordinator(memory, operational, observability).recover_apply(plan.saga_id)
    assert recovered.state.phase == "completed"
    assert operational.physical_calls == 1
    assert memory.commit_calls == 1


def test_outbox_response_loss_republishes_the_same_event_identity_exactly() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)
    operational = _Operational(receipt, _attestation(plan, receipt))
    observability = _Observability()

    def fail(boundary: str) -> None:
        if boundary == "after_artifact_physical_outbox_publish":
            raise RuntimeError("simulated outbox response loss")

    with pytest.raises(RuntimeError, match="outbox response loss"):
        _coordinator(memory, operational, observability, fail).execute_apply(
            plan,
            _request(plan),
        )

    assert memory.state.phase == "canonical_committed"
    recovered = _coordinator(memory, operational, observability).recover_apply(plan.saga_id)
    assert recovered.state.phase == "completed"
    assert observability.attempts == 2
    assert len(observability.events) == 1
    assert operational.physical_calls == 1


def test_request_cannot_substitute_resource_after_plan_reservation() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)
    operational = _Operational(receipt, _attestation(plan, receipt))
    request = _request(plan)
    request.preflight.resource_ref = "text:notes/other.txt"

    with pytest.raises(ValueError, match="request_plan_mismatch"):
        _coordinator(memory, operational, _Observability()).execute_apply(plan, request)

    assert memory.state.phase == "reserved"
    assert operational.physical_calls == 0


def test_request_cannot_substitute_rollback_plan_after_reservation() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)
    operational = _Operational(receipt, _attestation(plan, receipt))
    request = _request(plan)
    request.preflight.rollback_plan.rollback_fingerprint = _digest("other-rollback")

    with pytest.raises(ValueError, match="request_plan_mismatch"):
        _coordinator(memory, operational, _Observability()).execute_apply(plan, request)

    assert memory.state.phase == "reserved"
    assert operational.physical_calls == 0


def test_failed_physical_write_never_creates_canonical_state_or_outbox() -> None:
    plan = _apply_plan()
    memory = _Memory(plan)
    receipt = _mutation_receipt(plan)

    class FailedOperational(_Operational):
        def execute_and_commit_local_text_file_apply(self, *_args, **_kwargs):
            self.physical_calls += 1
            raise OSError("simulated write failure")

    operational = FailedOperational(receipt, _attestation(plan, receipt))
    with pytest.raises(OSError, match="write failure"):
        _coordinator(memory, operational, _Observability()).execute_apply(
            plan,
            _request(plan),
        )

    assert memory.state.phase == "effect_dispatched"
    assert memory.commit_receipt is None
    assert memory.outbox is None
    assert operational.physical_calls == 1
