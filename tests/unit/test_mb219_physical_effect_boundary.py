"""MB219 live-scope evidence; SQLite authority tests are not physical Linux proof."""

from dataclasses import replace
from hashlib import sha256

import pytest
from memory_service.service import MemoryService

from shared.artifact_physical_saga import (
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_rollback_plan,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalRollbackPlanContract,
    MissionStateContract,
    WorkItemStateContract,
)
from shared.types import MissionId, MissionStatus

NOW = "2026-10-04T12:00:00+00:00"
MISSION = MissionId("mission://mb219/boundary")
WORK = "work-item://mb219/boundary"


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _dispatched(tmp_path, purpose):
    service = MemoryService(database_url=f"sqlite:///{tmp_path / 'boundary.db'}")
    service.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MISSION,
            mission_goal="Disposable physical authority boundary test",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at=NOW,
            objective_ref="objective://mb219/boundary",
            work_item_refs=[WORK],
            work_items=[
                WorkItemStateContract(
                    work_item_ref=WORK,
                    work_item_status="active",
                    mission_id=MISSION,
                    blocking_state="ready",
                )
            ],
        )
    )
    apply = seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id="saga://mb219/apply",
            mission_id=MISSION,
            artifact_ref="artifact://mb219/v1",
            artifact_version=1,
            owner_mission_id=MISSION,
            objective_ref="objective://mb219/boundary",
            work_item_ref=WORK,
            lineage_root_ref="artifact://mb219/v1",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id="operation://mb219/apply",
            resource_ref="text:workspace/mb219.txt",
            root_alias="workspace",
            preflight_fingerprint=_digest("preflight"),
            root_config_fingerprint=_digest("root"),
            preflight_policy_version="1.0.0",
            transaction_policy_version="1.0.0",
            transaction_backend_version="posix-openat-v1",
            adapter_backend_version="local-text-v1",
            before_content_sha256=_digest(""),
            desired_content_sha256=_digest("disposable\n"),
            rollback_plan_ref=_digest("rollback-plan"),
            expected_lineage_revision=0,
            created_at=NOW,
            plan_fingerprint="",
        )
    )
    service.reserve_artifact_physical_apply(apply)
    service.advance_artifact_physical_apply(
        apply.saga_id, phase="effect_dispatched", occurred_at=NOW
    )
    if purpose == "apply":
        return service, apply, {}
    rollback = seal_artifact_physical_rollback_plan(
        ArtifactPhysicalRollbackPlanContract(
            saga_id="saga://mb219/rollback",
            mission_id=MISSION,
            active_artifact_ref=apply.artifact_ref,
            active_artifact_version=1,
            restored_artifact_ref=None,
            restored_artifact_version=None,
            owner_mission_id=MISSION,
            objective_ref=apply.objective_ref,
            work_item_ref=WORK,
            lineage_root_ref=apply.lineage_root_ref,
            physical_operation_id="operation://mb219/rollback",
            mutation_operation_id=apply.physical_operation_id,
            source_apply_saga_id=apply.saga_id,
            rollback_mode="precanonical_compensation",
            canonical_effect_expected=False,
            mutation_receipt_fingerprint=_digest("mutation-receipt"),
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
        rollback.saga_id, phase="rollback_effect_dispatched", occurred_at=NOW
    )
    return (
        service,
        rollback,
        {"mutation_receipt_fingerprint": rollback.mutation_receipt_fingerprint},
    )


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_exact_dispatched_plan_in_live_scope_is_authorizable_without_side_effect(tmp_path, purpose):
    service, plan, kwargs = _dispatched(tmp_path, purpose)
    before = service.get_artifact_physical_saga(plan.saga_id)
    assert (
        service.authorize_artifact_physical_effect(plan, resource_ref=plan.resource_ref, **kwargs)
        is True
    )
    assert service.get_artifact_physical_saga(plan.saga_id) == before
    assert service.get_artifact_physical_lineage(str(MISSION), plan.lineage_root_ref) is None
    assert not (tmp_path / "mb219.txt").exists()


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
@pytest.mark.parametrize(
    "drift", ["paused", "objective", "blocked", "inactive_work_item", "foreign_work_owner"]
)
def test_dispatch_marker_is_not_fresh_authority_after_live_scope_drift(tmp_path, purpose, drift):
    service, plan, kwargs = _dispatched(tmp_path, purpose)
    mission = service.get_mission_state(str(MISSION))
    if drift == "paused":
        mission.mission_status = MissionStatus.PAUSED
    elif drift == "objective":
        mission.objective_ref = "objective://mb219/changed"
    elif drift == "blocked":
        mission.work_items[0].blocking_state = "blocked"
    elif drift == "inactive_work_item":
        mission.work_items[0].work_item_status = "completed"
    else:
        mission.work_items[0].mission_id = MissionId("mission://mb219/foreign")
    service.repository.upsert_mission_state(mission)
    before = service.get_artifact_physical_saga(plan.saga_id)
    assert (
        service.authorize_artifact_physical_effect(plan, resource_ref=plan.resource_ref, **kwargs)
        is False
    )
    assert service.get_artifact_physical_saga(plan.saga_id) == before


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
@pytest.mark.parametrize("substitution", ["plan", "resource", "receipt"])
def test_self_resealed_or_wrong_resource_or_receipt_cannot_authorize_effect(
    tmp_path, purpose, substitution
):
    service, plan, kwargs = _dispatched(tmp_path, purpose)
    resource = plan.resource_ref
    if substitution == "resource":
        resource = "text:workspace/other.txt"
    elif substitution == "receipt":
        kwargs["mutation_receipt_fingerprint"] = _digest("foreign-receipt")
    elif purpose == "apply":
        plan = seal_artifact_physical_apply_plan(
            replace(plan, desired_content_sha256=_digest("substituted"))
        )
    else:
        plan = seal_artifact_physical_rollback_plan(
            replace(plan, restored_content_sha256=_digest("substituted"))
        )
    assert (
        service.authorize_artifact_physical_effect(plan, resource_ref=resource, **kwargs) is False
    )


@pytest.mark.parametrize("purpose", ["apply", "rollback"])
def test_authorizer_repository_failure_denies_instead_of_granting(tmp_path, monkeypatch, purpose):
    service, plan, kwargs = _dispatched(tmp_path, purpose)

    def unavailable(_saga_id):
        raise RuntimeError("disposable repository failure")

    monkeypatch.setattr(service.repository, "fetch_artifact_physical_saga_plan", unavailable)
    assert (
        service.authorize_artifact_physical_effect(plan, resource_ref=plan.resource_ref, **kwargs)
        is False
    )
