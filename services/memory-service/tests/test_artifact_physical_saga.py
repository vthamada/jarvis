from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from sqlite3 import IntegrityError, connect
from threading import Barrier

import pytest
from memory_service.service import MemoryService

from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_rollback_plan,
    seal_local_text_physical_state_attestation,
)
from shared.contracts import (
    ArtifactLifecycleStateContract,
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalRollbackPlanContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
    LocalTextRollbackReceipt,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.local_text_rollback_permissions import (
    build_mutation_receipt_fingerprint,
    build_rollback_receipt_fingerprint,
)
from shared.types import MissionId, MissionStatus

NOW = "2026-08-30T12:00:00+00:00"
EMPTY_SHA256 = sha256(b"").hexdigest()
DESIRED_SHA256 = sha256(b"hello\n").hexdigest()


def _service(tmp_path) -> MemoryService:
    service = MemoryService(
        database_url=f"sqlite:///{tmp_path / 'memory.db'}",
        artifact_physical_mutation_verifier=lambda _receipt, _attestation: True,
        artifact_physical_rollback_verifier=lambda _receipt, _attestation: True,
    )
    service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId("mission:physical"),
            mission_goal="persist physical artifact",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=NOW,
            objective_ref="objective:physical",
            work_item_refs=["work-item:physical"],
            work_items=[
                WorkItemStateContract(
                    work_item_ref="work-item:physical",
                    work_item_status="active",
                    mission_id=MissionId("mission:physical"),
                    blocking_state="ready",
                )
            ],
        )
    )
    return service


def _apply_plan(*, saga_id: str = "saga:apply:1") -> ArtifactPhysicalApplyPlanContract:
    return seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id=saga_id,
            mission_id=MissionId("mission:physical"),
            artifact_ref="artifact:physical:1",
            artifact_version=1,
            owner_mission_id=MissionId("mission:physical"),
            objective_ref="objective:physical",
            work_item_ref="work-item:physical",
            lineage_root_ref="artifact:physical:1",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id="operation:physical:1",
            resource_ref="text:workspace/docs/result.md",
            root_alias="workspace",
            preflight_fingerprint=sha256(b"preflight").hexdigest(),
            root_config_fingerprint=sha256(b"root").hexdigest(),
            preflight_policy_version="1.0.0",
            transaction_policy_version="1.0.0",
            transaction_backend_version="posix-openat-v1",
            adapter_backend_version="local-text-v1",
            before_content_sha256=EMPTY_SHA256,
            desired_content_sha256=DESIRED_SHA256,
            rollback_plan_ref=sha256(b"rollback-plan").hexdigest(),
            expected_lineage_revision=0,
            created_at=NOW,
            plan_fingerprint="",
        )
    )


def _mutation_receipt(plan: ArtifactPhysicalApplyPlanContract) -> LocalTextMutationReceipt:
    operation = "create_text" if plan.before_content_sha256 == EMPTY_SHA256 else "replace_text"
    receipt = LocalTextMutationReceipt(
        operation_id=plan.physical_operation_id,
        execution_grant_id=f"grant:{plan.physical_operation_id}",
        execution_claim_id=f"claim:{plan.physical_operation_id}",
        operation=operation,
        resource_ref=plan.resource_ref,
        subject_ref="subject:physical:1",
        preflight_fingerprint=plan.preflight_fingerprint,
        before_content_sha256=plan.before_content_sha256,
        desired_content_sha256=plan.desired_content_sha256,
        root_config_fingerprint=plan.root_config_fingerprint,
        applied_event_fingerprint=sha256(plan.physical_operation_id.encode()).hexdigest(),
        committed_at=NOW,
        mutation_status="applied",
        receipt_fingerprint="",
    )
    return replace(receipt, receipt_fingerprint=build_mutation_receipt_fingerprint(receipt))


def _attestation(
    plan: ArtifactPhysicalApplyPlanContract,
    receipt: LocalTextMutationReceipt,
) -> LocalTextPhysicalStateAttestationContract:
    return seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id=f"attestation:{plan.physical_operation_id}",
            purpose="mutation_current",
            receipt_fingerprint=receipt.receipt_fingerprint,
            mutation_operation_id=receipt.operation_id,
            rollback_operation_id=None,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            root_config_fingerprint=plan.root_config_fingerprint,
            physical_state="applied",
            observed_content_sha256=plan.desired_content_sha256,
            observed_identity_fingerprint=sha256(
                f"identity:{plan.physical_operation_id}".encode()
            ).hexdigest(),
            journal_event_fingerprint=receipt.applied_event_fingerprint,
            transaction_policy_version=plan.transaction_policy_version,
            transaction_backend_version=plan.transaction_backend_version,
            verified_at=NOW,
            attestation_fingerprint="",
        )
    )


def _rollback_receipt(
    plan: ArtifactPhysicalRollbackPlanContract,
    *,
    suffix: str,
) -> LocalTextRollbackReceipt:
    receipt = LocalTextRollbackReceipt(
        operation_id=plan.physical_operation_id,
        mutation_operation_id=plan.mutation_operation_id,
        rollback_grant_id=f"grant:rollback:{suffix}",
        rollback_claim_id=f"claim:rollback:{suffix}",
        mutation_receipt_fingerprint=plan.mutation_receipt_fingerprint,
        resource_ref=plan.resource_ref,
        restored_content_sha256=plan.restored_content_sha256,
        rolled_back_at=NOW,
        rolled_back_event_fingerprint=sha256(f"rolled-back:{suffix}".encode()).hexdigest(),
        rollback_receipt_fingerprint="",
    )
    return replace(
        receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(receipt),
    )


def _rollback_attestation(
    plan: ArtifactPhysicalRollbackPlanContract,
    source: ArtifactPhysicalApplyPlanContract,
    receipt: LocalTextRollbackReceipt,
    *,
    suffix: str,
) -> LocalTextPhysicalStateAttestationContract:
    return seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id=f"attestation:rollback:{suffix}",
            purpose="rollback_current",
            receipt_fingerprint=receipt.rollback_receipt_fingerprint,
            mutation_operation_id=plan.mutation_operation_id,
            rollback_operation_id=plan.physical_operation_id,
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            root_config_fingerprint=source.root_config_fingerprint,
            physical_state="restored" if plan.restored_artifact_ref is not None else "absent",
            observed_content_sha256=plan.restored_content_sha256,
            observed_identity_fingerprint=sha256(
                f"rollback-identity:{suffix}".encode()
            ).hexdigest(),
            journal_event_fingerprint=receipt.rolled_back_event_fingerprint,
            transaction_policy_version=source.transaction_policy_version,
            transaction_backend_version=source.transaction_backend_version,
            verified_at=NOW,
            attestation_fingerprint="",
        )
    )


def test_sqlite_apply_commit_is_atomic_reopenable_and_overlays_mission(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    receipt = _mutation_receipt(plan)
    attestation = _attestation(plan, receipt)

    assert service.reserve_artifact_physical_apply(plan).phase == "reserved"
    assert (
        service.advance_artifact_physical_apply(
            plan.saga_id,
            phase="effect_dispatched",
            occurred_at=NOW,
        ).phase
        == "effect_dispatched"
    )
    commit = service.commit_artifact_physical_apply(
        plan.saga_id,
        receipt=receipt,
        attestation=attestation,
    )

    assert service.verify_artifact_physical_canonical_commit_receipt(commit)
    assert service.get_artifact_physical_canonical_commit_receipt(plan.saga_id) == commit
    outbox = service.get_artifact_physical_outbox_for_saga(plan.saga_id)
    assert outbox is not None
    assert outbox.event_name == "artifact_lifecycle_state_changed"
    mission = service.repository.fetch_mission_state("mission:physical")
    assert mission is not None
    projected = next(
        item for item in mission.artifact_states if item.artifact_ref == plan.artifact_ref
    )
    assert projected.physical_consistency_status == "verified"
    assert projected.physical_version_fingerprint

    reopened = MemoryService(
        database_url=f"sqlite:///{tmp_path / 'memory.db'}",
        artifact_physical_mutation_verifier=lambda _receipt, _attestation: True,
    )
    assert reopened.get_artifact_physical_apply_plan(plan.saga_id) == plan
    assert reopened.get_artifact_physical_canonical_commit_receipt(plan.saga_id) == commit
    assert reopened.get_artifact_physical_outbox_for_saga(plan.saga_id) == outbox


def test_rejected_or_forged_apply_cannot_create_canonical_state(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    service.reserve_artifact_physical_apply(plan)
    service.advance_artifact_physical_apply(
        plan.saga_id,
        phase="effect_dispatched",
        occurred_at=NOW,
    )
    receipt = _mutation_receipt(plan)
    attestation = _attestation(plan, receipt)

    with pytest.raises(ValueError, match="receipt"):
        service.commit_artifact_physical_apply(
            plan.saga_id,
            receipt=replace(receipt, operation_id="operation:forged"),
            attestation=attestation,
        )
    assert service.get_artifact_physical_version(plan.artifact_ref) is None
    assert service.get_artifact_physical_outbox_for_saga(plan.saga_id) is None


def test_self_sealed_attestation_is_not_authority_without_trusted_verifier(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    service.reserve_artifact_physical_apply(plan)
    service.advance_artifact_physical_apply(
        plan.saga_id,
        phase="effect_dispatched",
        occurred_at=NOW,
    )
    receipt = _mutation_receipt(plan)
    attestation = _attestation(plan, receipt)
    service._artifact_physical_mutation_verifier = lambda _receipt, _attestation: False

    with pytest.raises(ValueError, match="not_verified"):
        service.commit_artifact_physical_apply(
            plan.saga_id,
            receipt=receipt,
            attestation=attestation,
        )
    assert service.get_artifact_physical_canonical_commit_receipt(plan.saga_id) is None


def test_register_reservation_rejects_objective_and_pending_resource_collisions(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    with pytest.raises(ValueError, match="objective"):
        service.reserve_artifact_physical_apply(
            seal_artifact_physical_apply_plan(replace(plan, objective_ref="objective:other"))
        )
    service.reserve_artifact_physical_apply(plan)
    competing = seal_artifact_physical_apply_plan(
        replace(
            plan,
            saga_id="saga:apply:2",
            artifact_ref="artifact:physical:2",
            lineage_root_ref="artifact:physical:2",
            physical_operation_id="operation:physical:2",
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="resource|pending"):
        service.reserve_artifact_physical_apply(competing)


def test_saga_chain_accepts_monotonic_later_checkpoint_time(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    service.reserve_artifact_physical_apply(plan)
    state = service.advance_artifact_physical_apply(
        plan.saga_id,
        phase="effect_dispatched",
        occurred_at="2026-08-30T12:00:01+00:00",
    )
    assert state.updated_at == "2026-08-30T12:00:01+00:00"


def test_plan_fingerprint_and_rollback_shape_are_fail_closed() -> None:
    plan = _apply_plan()
    with pytest.raises(ValueError, match="fingerprint"):
        from shared.artifact_physical_saga import require_valid_artifact_physical_apply_plan

        require_valid_artifact_physical_apply_plan(
            replace(plan, desired_content_sha256=sha256(b"tampered").hexdigest())
        )
    compensation = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga:rollback:1",
            mission_id=plan.mission_id,
            active_artifact_ref=plan.artifact_ref,
            active_artifact_version=plan.artifact_version,
            restored_artifact_ref=None,
            restored_artifact_version=None,
            owner_mission_id=plan.owner_mission_id,
            objective_ref=plan.objective_ref,
            work_item_ref=plan.work_item_ref,
            lineage_root_ref=plan.lineage_root_ref,
            physical_operation_id="operation:rollback:1",
            mutation_operation_id=plan.physical_operation_id,
            source_apply_saga_id=plan.saga_id,
            rollback_mode="precanonical_compensation",
            canonical_effect_expected=False,
            mutation_receipt_fingerprint=sha256(b"receipt").hexdigest(),
            resource_ref=plan.resource_ref,
            root_alias=plan.root_alias,
            expected_current_sha256=plan.desired_content_sha256,
            restored_content_sha256=plan.before_content_sha256,
            expected_lineage_revision=0,
            created_at=NOW,
            plan_fingerprint="",
        )
    )
    assert compensation.restored_artifact_ref is None
    assert compensation.canonical_effect_expected is False


def test_precanonical_compensation_closes_source_and_emits_non_lifecycle_outbox(
    tmp_path,
) -> None:
    service = _service(tmp_path)
    apply = _apply_plan()
    mutation = _mutation_receipt(apply)
    service.reserve_artifact_physical_apply(apply)
    service.advance_artifact_physical_apply(
        apply.saga_id,
        phase="effect_dispatched",
        occurred_at=NOW,
    )
    rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga:rollback:compensation",
            mission_id=apply.mission_id,
            active_artifact_ref=apply.artifact_ref,
            active_artifact_version=apply.artifact_version,
            restored_artifact_ref=None,
            restored_artifact_version=None,
            owner_mission_id=apply.owner_mission_id,
            objective_ref=apply.objective_ref,
            work_item_ref=apply.work_item_ref,
            lineage_root_ref=apply.lineage_root_ref,
            physical_operation_id="operation:rollback:compensation",
            mutation_operation_id=apply.physical_operation_id,
            source_apply_saga_id=apply.saga_id,
            rollback_mode="precanonical_compensation",
            canonical_effect_expected=False,
            mutation_receipt_fingerprint=mutation.receipt_fingerprint,
            resource_ref=apply.resource_ref,
            root_alias=apply.root_alias,
            expected_current_sha256=apply.desired_content_sha256,
            restored_content_sha256=apply.before_content_sha256,
            expected_lineage_revision=0,
            created_at=NOW,
            plan_fingerprint="",
        )
    )
    service.reserve_artifact_physical_rollback(rollback)
    service.advance_artifact_physical_rollback(
        rollback.saga_id,
        phase="rollback_effect_dispatched",
        occurred_at=NOW,
    )
    rollback_receipt = LocalTextRollbackReceipt(
        operation_id=rollback.physical_operation_id,
        mutation_operation_id=rollback.mutation_operation_id,
        rollback_grant_id="grant:rollback:compensation",
        rollback_claim_id="claim:rollback:compensation",
        mutation_receipt_fingerprint=mutation.receipt_fingerprint,
        resource_ref=rollback.resource_ref,
        restored_content_sha256=rollback.restored_content_sha256,
        rolled_back_at=NOW,
        rolled_back_event_fingerprint=sha256(b"rolled-back").hexdigest(),
        rollback_receipt_fingerprint="",
    )
    rollback_receipt = replace(
        rollback_receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(rollback_receipt),
    )
    rollback_attestation = seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id="attestation:rollback:compensation",
            purpose="rollback_current",
            receipt_fingerprint=rollback_receipt.rollback_receipt_fingerprint,
            mutation_operation_id=rollback.mutation_operation_id,
            rollback_operation_id=rollback.physical_operation_id,
            resource_ref=rollback.resource_ref,
            root_alias=rollback.root_alias,
            root_config_fingerprint=apply.root_config_fingerprint,
            physical_state="absent",
            observed_content_sha256=rollback.restored_content_sha256,
            observed_identity_fingerprint=sha256(b"absent").hexdigest(),
            journal_event_fingerprint=rollback_receipt.rolled_back_event_fingerprint,
            transaction_policy_version=apply.transaction_policy_version,
            transaction_backend_version=apply.transaction_backend_version,
            verified_at=NOW,
            attestation_fingerprint="",
        )
    )

    commit = service.commit_artifact_physical_rollback(
        rollback.saga_id,
        receipt=rollback_receipt,
        attestation=rollback_attestation,
    )

    assert commit.artifact_ref is None
    assert service.get_artifact_physical_saga(apply.saga_id).phase == "compensated"
    outbox = service.get_artifact_physical_outbox_for_saga(rollback.saga_id)
    assert outbox is not None
    assert outbox.event_name == "artifact_physical_apply_compensated"
    service.mark_artifact_physical_outbox_published(
        outbox.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )
    assert not service.is_local_text_resource_physically_bound(apply.resource_ref)
    replacement_attempt = seal_artifact_physical_apply_plan(
        replace(
            apply,
            saga_id="saga:apply:after-compensation",
            artifact_ref="artifact:physical:after-compensation",
            lineage_root_ref="artifact:physical:after-compensation",
            physical_operation_id="operation:physical:after-compensation",
            plan_fingerprint="",
        )
    )
    assert service.reserve_artifact_physical_apply(replacement_attempt).phase == "reserved"


def test_replace_and_canonical_rollback_use_exact_predecessor_and_cas(tmp_path) -> None:
    service = _service(tmp_path)
    first = _apply_plan()
    first_receipt = _mutation_receipt(first)
    service.reserve_artifact_physical_apply(first)
    service.advance_artifact_physical_apply(
        first.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    service.commit_artifact_physical_apply(
        first.saga_id,
        receipt=first_receipt,
        attestation=_attestation(first, first_receipt),
    )
    pending_first = service.get_artifact_physical_outbox_for_saga(first.saga_id)
    assert pending_first is not None

    second_hash = sha256(b"hello again\n").hexdigest()
    second = seal_artifact_physical_apply_plan(
        replace(
            first,
            saga_id="saga:apply:2",
            artifact_ref="artifact:physical:2",
            artifact_version=2,
            lineage_root_ref=first.lineage_root_ref,
            supersedes_artifact_ref=first.artifact_ref,
            transition="replace",
            physical_operation_id="operation:physical:2",
            preflight_fingerprint=sha256(b"preflight-2").hexdigest(),
            before_content_sha256=first.desired_content_sha256,
            desired_content_sha256=second_hash,
            rollback_plan_ref=sha256(b"rollback-plan-2").hexdigest(),
            expected_lineage_revision=1,
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="pending"):
        service.reserve_artifact_physical_apply(second)
    service.mark_artifact_physical_outbox_published(
        pending_first.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )
    second_receipt = _mutation_receipt(second)
    service.reserve_artifact_physical_apply(second)
    service.advance_artifact_physical_apply(
        second.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    service.commit_artifact_physical_apply(
        second.saga_id,
        receipt=second_receipt,
        attestation=_attestation(second, second_receipt),
    )
    pending_second = service.get_artifact_physical_outbox_for_saga(second.saga_id)
    assert pending_second is not None
    service.mark_artifact_physical_outbox_published(
        pending_second.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )

    rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga:rollback:canonical",
            mission_id=second.mission_id,
            active_artifact_ref=second.artifact_ref,
            active_artifact_version=2,
            restored_artifact_ref=first.artifact_ref,
            restored_artifact_version=1,
            owner_mission_id=second.owner_mission_id,
            objective_ref=second.objective_ref,
            work_item_ref=second.work_item_ref,
            lineage_root_ref=second.lineage_root_ref,
            physical_operation_id="operation:rollback:canonical",
            mutation_operation_id=second.physical_operation_id,
            source_apply_saga_id=second.saga_id,
            rollback_mode="canonical_rollback",
            canonical_effect_expected=True,
            mutation_receipt_fingerprint=second_receipt.receipt_fingerprint,
            resource_ref=second.resource_ref,
            root_alias=second.root_alias,
            expected_current_sha256=second.desired_content_sha256,
            restored_content_sha256=first.desired_content_sha256,
            expected_lineage_revision=2,
            created_at=NOW,
            plan_fingerprint="",
        )
    )
    service.reserve_artifact_physical_rollback(rollback)
    service.advance_artifact_physical_rollback(
        rollback.saga_id,
        phase="rollback_effect_dispatched",
        occurred_at=NOW,
    )
    rollback_receipt = LocalTextRollbackReceipt(
        operation_id=rollback.physical_operation_id,
        mutation_operation_id=rollback.mutation_operation_id,
        rollback_grant_id="grant:rollback:canonical",
        rollback_claim_id="claim:rollback:canonical",
        mutation_receipt_fingerprint=rollback.mutation_receipt_fingerprint,
        resource_ref=rollback.resource_ref,
        restored_content_sha256=rollback.restored_content_sha256,
        rolled_back_at=NOW,
        rolled_back_event_fingerprint=sha256(b"rolled-back-canonical").hexdigest(),
        rollback_receipt_fingerprint="",
    )
    rollback_receipt = replace(
        rollback_receipt,
        rollback_receipt_fingerprint=build_rollback_receipt_fingerprint(rollback_receipt),
    )
    rollback_attestation = seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id="attestation:rollback:canonical",
            purpose="rollback_current",
            receipt_fingerprint=rollback_receipt.rollback_receipt_fingerprint,
            mutation_operation_id=rollback.mutation_operation_id,
            rollback_operation_id=rollback.physical_operation_id,
            resource_ref=rollback.resource_ref,
            root_alias=rollback.root_alias,
            root_config_fingerprint=second.root_config_fingerprint,
            physical_state="restored",
            observed_content_sha256=rollback.restored_content_sha256,
            observed_identity_fingerprint=sha256(b"restored-identity").hexdigest(),
            journal_event_fingerprint=rollback_receipt.rolled_back_event_fingerprint,
            transaction_policy_version=second.transaction_policy_version,
            transaction_backend_version=second.transaction_backend_version,
            verified_at=NOW,
            attestation_fingerprint="",
        )
    )
    commit = service.commit_artifact_physical_rollback(
        rollback.saga_id,
        receipt=rollback_receipt,
        attestation=rollback_attestation,
    )

    assert commit.artifact_ref == first.artifact_ref
    lineage = service.get_artifact_physical_lineage(str(first.mission_id), first.lineage_root_ref)
    assert lineage is not None
    assert lineage.revision == 3
    assert lineage.active_artifact_ref == first.artifact_ref
    rollback_outbox = service.get_artifact_physical_outbox_for_saga(rollback.saga_id)
    assert rollback_outbox is not None
    third = seal_artifact_physical_apply_plan(
        replace(
            second,
            saga_id="saga:apply:3",
            artifact_ref="artifact:physical:3",
            artifact_version=3,
            supersedes_artifact_ref=first.artifact_ref,
            physical_operation_id="operation:physical:3",
            preflight_fingerprint=sha256(b"preflight-3").hexdigest(),
            before_content_sha256=first.desired_content_sha256,
            desired_content_sha256=sha256(b"hello third\n").hexdigest(),
            rollback_plan_ref=sha256(b"rollback-plan-3").hexdigest(),
            expected_lineage_revision=3,
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="pending"):
        service.reserve_artifact_physical_apply(third)
    service.mark_artifact_physical_outbox_published(
        rollback_outbox.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )
    assert service.reserve_artifact_physical_apply(third).phase == "reserved"


def test_precanonical_replace_compensation_restores_exact_canonical_head(tmp_path) -> None:
    service = _service(tmp_path)
    first = _apply_plan(saga_id="saga:replace-compensation:v1")
    first_receipt = _mutation_receipt(first)
    service.reserve_artifact_physical_apply(first)
    service.advance_artifact_physical_apply(
        first.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    service.commit_artifact_physical_apply(
        first.saga_id,
        receipt=first_receipt,
        attestation=_attestation(first, first_receipt),
    )
    first_outbox = service.get_artifact_physical_outbox_for_saga(first.saga_id)
    assert first_outbox is not None
    service.mark_artifact_physical_outbox_published(
        first_outbox.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )
    second = seal_artifact_physical_apply_plan(
        replace(
            first,
            saga_id="saga:replace-compensation:v2",
            artifact_ref="artifact:replace-compensation:v2",
            artifact_version=2,
            supersedes_artifact_ref=first.artifact_ref,
            transition="replace",
            physical_operation_id="operation:replace-compensation:v2",
            preflight_fingerprint=sha256(b"replace-compensation-preflight").hexdigest(),
            before_content_sha256=first.desired_content_sha256,
            desired_content_sha256=sha256(b"replacement\n").hexdigest(),
            rollback_plan_ref=sha256(b"replace-compensation-rollback").hexdigest(),
            expected_lineage_revision=1,
            plan_fingerprint="",
        )
    )
    second_receipt = _mutation_receipt(second)
    service.reserve_artifact_physical_apply(second)
    service.advance_artifact_physical_apply(
        second.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga:replace-compensation:rollback",
            mission_id=second.mission_id,
            active_artifact_ref=second.artifact_ref,
            active_artifact_version=second.artifact_version,
            restored_artifact_ref=first.artifact_ref,
            restored_artifact_version=first.artifact_version,
            owner_mission_id=second.owner_mission_id,
            objective_ref=second.objective_ref,
            work_item_ref=second.work_item_ref,
            lineage_root_ref=second.lineage_root_ref,
            physical_operation_id="operation:replace-compensation:rollback",
            mutation_operation_id=second.physical_operation_id,
            source_apply_saga_id=second.saga_id,
            rollback_mode="precanonical_compensation",
            canonical_effect_expected=False,
            mutation_receipt_fingerprint=second_receipt.receipt_fingerprint,
            resource_ref=second.resource_ref,
            root_alias=second.root_alias,
            expected_current_sha256=second.desired_content_sha256,
            restored_content_sha256=first.desired_content_sha256,
            expected_lineage_revision=1,
            created_at=NOW,
            plan_fingerprint="",
        )
    )
    forged = seal_artifact_physical_rollback_plan(
        replace(
            rollback,
            saga_id="saga:replace-compensation:forged",
            restored_content_sha256=sha256(b"not-the-predecessor").hexdigest(),
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="compensation_restore|source"):
        service.reserve_artifact_physical_rollback(forged)
    assert service.repository.fetch_artifact_physical_saga_plan(forged.saga_id) is None

    service.reserve_artifact_physical_rollback(rollback)
    service.advance_artifact_physical_rollback(
        rollback.saga_id,
        phase="rollback_effect_dispatched",
        occurred_at=NOW,
    )
    rollback_receipt = _rollback_receipt(rollback, suffix="replace-compensation")
    service.commit_artifact_physical_rollback(
        rollback.saga_id,
        receipt=rollback_receipt,
        attestation=_rollback_attestation(
            rollback,
            second,
            rollback_receipt,
            suffix="replace-compensation",
        ),
    )

    assert service.get_artifact_physical_saga(second.saga_id).phase == "compensated"
    assert service.get_artifact_physical_version(second.artifact_ref) is None
    lineage = service.get_artifact_physical_lineage(str(first.mission_id), first.lineage_root_ref)
    assert lineage is not None
    assert lineage.revision == 1
    assert lineage.active_artifact_ref == first.artifact_ref
    compensation_outbox = service.get_artifact_physical_outbox_for_saga(rollback.saga_id)
    assert compensation_outbox is not None
    pending_third = seal_artifact_physical_apply_plan(
        replace(
            second,
            saga_id="saga:replace-compensation:v2-retry",
            artifact_ref="artifact:replace-compensation:v2-retry",
            physical_operation_id="operation:replace-compensation:v2-retry",
            plan_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="pending"):
        service.reserve_artifact_physical_apply(pending_third)
    service.mark_artifact_physical_outbox_published(
        compensation_outbox.outbox_id,
        publisher_ref="publisher:test",
        published_at=NOW,
    )
    assert service.reserve_artifact_physical_apply(pending_third).phase == "reserved"


def test_register_reservation_is_exactly_once_under_concurrency(tmp_path) -> None:
    first_service = _service(tmp_path)
    second_service = MemoryService(
        database_url=f"sqlite:///{tmp_path / 'memory.db'}",
        artifact_physical_mutation_verifier=lambda _receipt, _attestation: True,
    )
    first = _apply_plan(saga_id="saga:race:1")
    second = seal_artifact_physical_apply_plan(
        replace(
            first,
            saga_id="saga:race:2",
            artifact_ref="artifact:race:2",
            lineage_root_ref="artifact:race:2",
            physical_operation_id="operation:race:2",
            plan_fingerprint="",
        )
    )
    barrier = Barrier(2)

    def reserve(service: MemoryService, plan: ArtifactPhysicalApplyPlanContract) -> bool:
        barrier.wait()
        try:
            service.reserve_artifact_physical_apply(plan)
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda pair: reserve(*pair),
                ((first_service, first), (second_service, second)),
            )
        )
    assert sorted(results) == [False, True]


def test_sqlite_saga_rows_are_append_only_and_physical_projection_wins(tmp_path) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    receipt = _mutation_receipt(plan)
    service.reserve_artifact_physical_apply(plan)
    service.advance_artifact_physical_apply(
        plan.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    service.commit_artifact_physical_apply(
        plan.saga_id,
        receipt=receipt,
        attestation=_attestation(plan, receipt),
    )

    with connect(tmp_path / "memory.db") as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE artifact_physical_saga_plans SET purpose = 'rollback' WHERE saga_id = ?",
                (plan.saga_id,),
            )

    mission = service.repository.fetch_mission_state("mission:physical")
    assert mission is not None
    forged = replace(
        mission,
        artifact_states=[
            replace(
                mission.artifact_states[0],
                artifact_status="archived",
                physical_consistency_status=None,
            )
        ],
    )
    service.repository.upsert_mission_state(forged)
    fetched = service.repository.fetch_mission_state("mission:physical")
    assert fetched is not None
    assert fetched.artifact_states[0].artifact_status == "active"
    assert fetched.artifact_states[0].physical_consistency_status == "verified"


def test_physical_projection_shadows_forged_lineage_and_sanitizes_unmatched_legacy(
    tmp_path,
) -> None:
    service = _service(tmp_path)
    plan = _apply_plan()
    receipt = _mutation_receipt(plan)
    service.reserve_artifact_physical_apply(plan)
    service.advance_artifact_physical_apply(
        plan.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    service.commit_artifact_physical_apply(
        plan.saga_id,
        receipt=receipt,
        attestation=_attestation(plan, receipt),
    )
    mission = service.repository.fetch_mission_state("mission:physical")
    assert mission is not None
    forged_sibling = ArtifactLifecycleStateContract(
        artifact_ref="artifact:forged:sibling",
        artifact_status="active",
        mission_id=plan.mission_id,
        artifact_version=999,
        owner_mission_id=plan.owner_mission_id,
        lineage_root_ref=plan.lineage_root_ref,
        physical_version_fingerprint=sha256(b"forged-version").hexdigest(),
        mutation_receipt_fingerprint=sha256(b"forged-receipt").hexdigest(),
        canonical_saga_id="saga:forged",
        physical_resource_ref=plan.resource_ref,
        physical_state_attestation_fingerprint=sha256(b"forged-attestation").hexdigest(),
        physical_consistency_status="verified",
    )
    forged_unmatched = replace(
        forged_sibling,
        artifact_ref="artifact:legacy:unmatched",
        lineage_root_ref="artifact:legacy:unmatched",
    )
    service.repository.upsert_mission_state(
        replace(
            mission,
            artifact_refs=[
                *mission.artifact_refs,
                forged_sibling.artifact_ref,
                forged_unmatched.artifact_ref,
            ],
            active_artifact_refs=[
                *mission.active_artifact_refs,
                forged_sibling.artifact_ref,
                forged_unmatched.artifact_ref,
            ],
            artifact_states=[*mission.artifact_states, forged_sibling, forged_unmatched],
        )
    )

    fetched = service.repository.fetch_mission_state("mission:physical")
    assert fetched is not None
    assert forged_sibling.artifact_ref not in fetched.artifact_refs
    assert forged_sibling.artifact_ref not in fetched.active_artifact_refs
    assert (
        len(
            [
                item
                for item in fetched.artifact_states
                if item.lineage_root_ref == plan.lineage_root_ref
            ]
        )
        == 1
    )
    legacy = next(
        item
        for item in fetched.artifact_states
        if item.artifact_ref == forged_unmatched.artifact_ref
    )
    assert legacy.physical_consistency_status == "unverified_legacy"
    assert legacy.physical_version_fingerprint is None
    assert legacy.mutation_receipt_fingerprint is None
    assert legacy.canonical_saga_id is None
    assert legacy.physical_resource_ref is None
    assert legacy.physical_state_attestation_fingerprint is None


@pytest.mark.parametrize(
    "resource_ref",
    (
        "text:workspace/docs/CON.txt",
        "text:workspace/docs/NUL.md",
        "text:workspace/docs/CLOCK$.txt",
        "text:workspace/docs/COM¹.md",
        "text:workspace/docs/file*.md",
        "text:workspace/docs/file?.txt",
        "text:workspace/docs/file<name>.md",
        "text:workspace/docs/file.md:stream",
        "text:workspace/docs/../escape.md",
        "text:workspace/docs\\escape.md",
        "text:workspace//server/share.md",
        "text:workspace/C:/escape.md",
        "text:workspace/.jarvis-transactions/state.md",
        "text:workspace/docs/‮result.md",
        "text:workspace/docs/résult.md",
        f"text:workspace/{'é' * 256}.md",
    ),
)
def test_reserve_rejects_noncanonical_resource_before_database_delta(
    tmp_path,
    resource_ref: str,
) -> None:
    service = _service(tmp_path)
    database_path = tmp_path / "memory.db"
    before = database_path.read_bytes()
    invalid = replace(_apply_plan(), resource_ref=resource_ref)

    with pytest.raises(ValueError, match="resource_ref"):
        service.reserve_artifact_physical_apply(invalid)

    assert database_path.read_bytes() == before
    assert service.repository.fetch_artifact_physical_saga_plan(invalid.saga_id) is None
