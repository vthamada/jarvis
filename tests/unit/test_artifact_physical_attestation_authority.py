from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from threading import Thread

from shared.artifact_physical_attestation_authority import (
    ArtifactPhysicalAttestationLeaseAuthority,
)
from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_local_text_physical_state_attestation,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    LocalTextMutationReceipt,
    LocalTextPhysicalStateAttestationContract,
)
from shared.local_text_rollback_permissions import build_mutation_receipt_fingerprint
from shared.types import MissionId


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _evidence():
    plan = seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id="saga://attestation/unit",
            mission_id=MissionId("mission://attestation/unit"),
            artifact_ref="artifact://attestation/unit/v1",
            artifact_version=1,
            owner_mission_id=MissionId("mission://attestation/unit"),
            objective_ref="objective://attestation/unit",
            work_item_ref="work-item://attestation/unit",
            lineage_root_ref="artifact://attestation/unit/v1",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id="operation://attestation/unit",
            resource_ref="text:notes/attestation.txt",
            root_alias="notes",
            preflight_fingerprint=_digest("preflight"),
            root_config_fingerprint=_digest("root"),
            preflight_policy_version="local-text-preflight/1.0.0",
            transaction_policy_version="local-text-transaction/1.0.0",
            transaction_backend_version="posix-openat-1.0.0",
            adapter_backend_version="local-text-openat/1.0.0",
            before_content_sha256=sha256(b"").hexdigest(),
            desired_content_sha256=_digest("after"),
            rollback_plan_ref=_digest("rollback"),
            expected_lineage_revision=0,
            created_at="2026-08-30T12:00:00+00:00",
            plan_fingerprint="0" * 64,
        )
    )
    receipt = LocalTextMutationReceipt(
        operation_id=plan.physical_operation_id,
        execution_grant_id="grant://attestation/unit",
        execution_claim_id="claim://attestation/unit",
        operation="create_text",
        resource_ref=plan.resource_ref,
        subject_ref="operator://attestation/unit",
        preflight_fingerprint=plan.preflight_fingerprint,
        before_content_sha256=plan.before_content_sha256,
        desired_content_sha256=plan.desired_content_sha256,
        root_config_fingerprint=plan.root_config_fingerprint,
        applied_event_fingerprint=_digest("applied"),
        committed_at="2026-08-30T12:00:01+00:00",
        mutation_status="applied",
        receipt_fingerprint="0" * 64,
    )
    receipt = replace(
        receipt,
        receipt_fingerprint=build_mutation_receipt_fingerprint(receipt),
    )
    attestation = seal_local_text_physical_state_attestation(
        LocalTextPhysicalStateAttestationContract(
            attestation_id="attestation://unit/1",
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
            verified_at="2026-08-30T12:00:02+00:00",
            attestation_fingerprint="0" * 64,
        )
    )
    return plan, receipt, attestation


def test_attestation_requires_an_active_exact_one_shot_lease() -> None:
    plan, receipt, attestation = _evidence()
    authority = ArtifactPhysicalAttestationLeaseAuthority()

    assert authority.verify_and_consume(receipt, attestation) is False
    with authority.issue(plan, receipt, attestation):
        assert authority.verify_and_consume(receipt, attestation) is True
        assert authority.verify_and_consume(receipt, attestation) is False
    assert authority.verify_and_consume(receipt, attestation) is False


def test_attestation_lease_rejects_substitution_and_another_thread() -> None:
    plan, receipt, attestation = _evidence()
    authority = ArtifactPhysicalAttestationLeaseAuthority()
    substituted = replace(
        attestation,
        attestation_id="attestation://unit/forged",
        attestation_fingerprint="0" * 64,
    )
    substituted = seal_local_text_physical_state_attestation(substituted)
    results: list[bool] = []

    with authority.issue(plan, receipt, attestation):
        assert authority.verify_and_consume(receipt, substituted) is False
        thread = Thread(
            target=lambda: results.append(authority.verify_and_consume(receipt, attestation))
        )
        thread.start()
        thread.join()
        assert results == [False]
        assert authority.verify_and_consume(receipt, attestation) is True


def test_attestation_lease_is_private_to_the_issuing_authority() -> None:
    plan, receipt, attestation = _evidence()
    issuing_authority = ArtifactPhysicalAttestationLeaseAuthority()
    unrelated_authority = ArtifactPhysicalAttestationLeaseAuthority()

    with issuing_authority.issue(plan, receipt, attestation):
        assert unrelated_authority.verify_and_consume(receipt, attestation) is False
        assert issuing_authority.verify_and_consume(receipt, attestation) is True
