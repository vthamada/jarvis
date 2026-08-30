from dataclasses import replace
from hashlib import sha256

import pytest
from operational_service.adapters.local_text_file import (
    _validate_local_text_relative_path,
)

from shared.artifact_physical_saga import (
    require_valid_artifact_physical_apply_plan,
    require_valid_artifact_physical_saga_event,
    require_valid_local_text_resource_ref,
    seal_artifact_physical_apply_plan,
    seal_artifact_physical_saga_event,
)
from shared.contracts import (
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalSagaEventContract,
)
from shared.types import MissionId

NOW = "2026-08-30T12:00:00+00:00"
DEFAULT_LOCAL_TEXT_EXTENSIONS = (".md", ".txt")


def _plan(resource_ref: str = "text:workspace/docs/result.md") -> ArtifactPhysicalApplyPlanContract:
    return seal_artifact_physical_apply_plan(
        ArtifactPhysicalApplyPlanContract(
            saga_id="saga:shared:1",
            mission_id=MissionId("mission:shared"),
            artifact_ref="artifact:shared:1",
            artifact_version=1,
            owner_mission_id=MissionId("mission:shared"),
            objective_ref=None,
            work_item_ref="work-item:shared",
            lineage_root_ref="artifact:shared:1",
            supersedes_artifact_ref=None,
            transition="register",
            physical_operation_id="operation:shared:1",
            resource_ref=resource_ref,
            root_alias="workspace",
            preflight_fingerprint=sha256(b"preflight").hexdigest(),
            root_config_fingerprint=sha256(b"root").hexdigest(),
            preflight_policy_version="1.0.0",
            transaction_policy_version="1.0.0",
            transaction_backend_version="posix-openat-v1",
            adapter_backend_version="local-text-v1",
            before_content_sha256=sha256(b"").hexdigest(),
            desired_content_sha256=sha256(b"desired").hexdigest(),
            rollback_plan_ref=sha256(b"rollback").hexdigest(),
            expected_lineage_revision=0,
            created_at=NOW,
            plan_fingerprint="",
        )
    )


@pytest.mark.parametrize(
    "resource_ref",
    (
        "C:/Windows/system.ini",
        "text:workspace//server/share/result.md",
        "text:workspace//docs/result.md",
        "text:workspace/docs//result.md",
        "text:workspace/../escape.md",
        "text:workspace/docs/./result.md",
        "text:workspace/C:/escape.md",
        "text:workspace/.jarvis-transactions/state.md",
        "text:workspace/docs/result.exe",
        "text:workspace/docs\\result.md",
        "text:workspace/docs/CON.md",
        "text:workspace/docs/AUX.txt",
        "text:workspace/docs/NUL.txt",
        "text:workspace/docs/CLOCK$.md",
        "text:workspace/docs/COM¹.txt",
        "text:workspace/docs/LPT³.md",
        "text:workspace/docs/file*.md",
        "text:workspace/docs/file?.md",
        "text:workspace/docs/file.md:stream",
        "text:workspace/docs./result.md",
        "text:workspace/docs /result.md",
        "text:workspace/docs/‮result.md",
        "text:workspace/docs/résult.md",
        f"text:workspace/{'é' * 256}.md",
    ),
)
def test_apply_plan_rejects_unsafe_or_noncanonical_resource_refs(resource_ref: str) -> None:
    with pytest.raises(ValueError, match="resource_ref"):
        require_valid_artifact_physical_apply_plan(_plan(resource_ref))


@pytest.mark.parametrize(
    "relative_path",
    (
        "docs/note.txt",
        "docs/résumé.md",
        "docs/result .md",
        f"{'a' * 250}/{'b' * 250}/xresult.md",
    ),
)
def test_mb215_and_mb217_accept_the_same_canonical_resource_paths(
    relative_path: str,
) -> None:
    _validate_local_text_relative_path(
        relative_path,
        allowed_extensions=DEFAULT_LOCAL_TEXT_EXTENSIONS,
    )
    require_valid_artifact_physical_apply_plan(
        _plan(f"text:workspace/{relative_path}"),
    )


@pytest.mark.parametrize(
    "relative_path",
    (
        "../escape.md",
        "docs//result.md",
        "docs\\result.md",
        "C:/escape.md",
        "docs/file.md:stream",
        "docs/CON.txt",
        "docs/COM¹.md",
        "docs/file?.md",
        "docs/result.md ",
        "docs/\u202eresult.md",
        "docs/résult.md",
        ".JARVIS-TRANSACTIONS/state.md",
        f"{'a' * 250}/{'b' * 250}/xxresult.md",
        f"docs/{'a' * 253}.md",
    ),
)
def test_mb215_and_mb217_reject_the_same_noncanonical_resource_paths(
    relative_path: str,
) -> None:
    with pytest.raises(ValueError):
        _validate_local_text_relative_path(
            relative_path,
            allowed_extensions=DEFAULT_LOCAL_TEXT_EXTENSIONS,
        )
    with pytest.raises(ValueError, match="resource_ref"):
        require_valid_local_text_resource_ref(
            f"text:workspace/{relative_path}",
            "workspace",
        )


def test_apply_plan_fingerprint_is_deterministic_and_binds_transaction_policy() -> None:
    plan = _plan()
    assert _plan() == plan
    with pytest.raises(ValueError, match="fingerprint"):
        require_valid_artifact_physical_apply_plan(
            replace(plan, transaction_policy_version="2.0.0")
        )


def test_reconciliation_checkpoint_is_terminal_and_chain_bound() -> None:
    plan = _plan()
    reserved = seal_artifact_physical_saga_event(
        ArtifactPhysicalSagaEventContract(
            event_id="event:shared:1",
            saga_id=plan.saga_id,
            purpose="apply",
            phase="reserved",
            sequence=1,
            plan_fingerprint=plan.plan_fingerprint,
            physical_operation_id=plan.physical_operation_id,
            occurred_at=NOW,
            previous_event_fingerprint=None,
            mutation_receipt_fingerprint=None,
            rollback_receipt_fingerprint=None,
            physical_state_attestation_fingerprint=None,
            event_fingerprint="",
        )
    )
    dispatched = seal_artifact_physical_saga_event(
        replace(
            reserved,
            event_id="event:shared:2",
            phase="effect_dispatched",
            sequence=2,
            previous_event_fingerprint=reserved.event_fingerprint,
            event_fingerprint="",
        )
    )
    reconciliation = seal_artifact_physical_saga_event(
        replace(
            dispatched,
            event_id="event:shared:3",
            phase="reconciliation_required",
            sequence=3,
            previous_event_fingerprint=dispatched.event_fingerprint,
            event_fingerprint="",
        )
    )
    require_valid_artifact_physical_saga_event(
        reconciliation,
        previous_event=dispatched,
    )
    impossible_resume = seal_artifact_physical_saga_event(
        replace(
            reconciliation,
            event_id="event:shared:4",
            phase="physical_applied",
            sequence=4,
            previous_event_fingerprint=reconciliation.event_fingerprint,
            mutation_receipt_fingerprint=sha256(b"receipt").hexdigest(),
            physical_state_attestation_fingerprint=sha256(b"attestation").hexdigest(),
            event_fingerprint="",
        )
    )
    with pytest.raises(ValueError, match="transition"):
        require_valid_artifact_physical_saga_event(
            impossible_resume,
            previous_event=reconciliation,
        )
