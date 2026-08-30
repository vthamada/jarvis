"""Deterministic, content-free contracts for physical artifact consistency sagas."""

from __future__ import annotations

import re
from dataclasses import asdict, is_dataclass, replace
from datetime import datetime
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from typing import TypeVar
from unicodedata import category, is_normalized

from shared.contracts import (
    ARTIFACT_PHYSICAL_APPLY_PHASES,
    ARTIFACT_PHYSICAL_ROLLBACK_PHASES,
    ArtifactPhysicalApplyPlanContract,
    ArtifactPhysicalCanonicalCommitReceiptContract,
    ArtifactPhysicalLineageContract,
    ArtifactPhysicalOutboxDeliveryContract,
    ArtifactPhysicalOutboxItemContract,
    ArtifactPhysicalRollbackPlanContract,
    ArtifactPhysicalSagaEventContract,
    ArtifactPhysicalSagaStateContract,
    LocalTextPhysicalStateAttestationContract,
    PhysicalArtifactVersionContract,
)
from shared.local_text_resource_ref import require_valid_local_text_relative_path

_SELF_FINGERPRINT_FIELD = {
    ArtifactPhysicalApplyPlanContract: "plan_fingerprint",
    ArtifactPhysicalRollbackPlanContract: "plan_fingerprint",
    ArtifactPhysicalSagaEventContract: "event_fingerprint",
    ArtifactPhysicalSagaStateContract: "state_fingerprint",
    PhysicalArtifactVersionContract: "version_fingerprint",
    ArtifactPhysicalLineageContract: "lineage_fingerprint",
    ArtifactPhysicalOutboxItemContract: "outbox_fingerprint",
    ArtifactPhysicalOutboxDeliveryContract: "delivery_fingerprint",
    LocalTextPhysicalStateAttestationContract: "attestation_fingerprint",
    ArtifactPhysicalCanonicalCommitReceiptContract: "commit_fingerprint",
}
_APPLY_TRANSITIONS = {
    None: {"reserved"},
    "reserved": {"effect_dispatched", "failed"},
    "effect_dispatched": {
        "physical_applied",
        "reconciliation_required",
        "compensated",
    },
    "physical_applied": {
        "canonical_committed",
        "reconciliation_required",
        "compensation_required",
        "compensated",
    },
    "canonical_committed": {"completed"},
    "reconciliation_required": set(),
    "compensation_required": {"compensated"},
    "compensated": set(),
    "completed": set(),
    "failed": set(),
}
_ROLLBACK_TRANSITIONS = {
    None: {"rollback_reserved"},
    "rollback_reserved": {"rollback_effect_dispatched", "failed"},
    "rollback_effect_dispatched": {
        "physically_rolled_back",
        "reconciliation_required",
    },
    "physically_rolled_back": {
        "canonical_rolled_back",
        "compensation_committed",
        "reconciliation_required",
    },
    "canonical_rolled_back": {"completed"},
    "compensation_committed": {"completed"},
    "reconciliation_required": set(),
    "completed": set(),
    "failed": set(),
}
_T = TypeVar("_T")
ArtifactPhysicalPlanContract = (
    ArtifactPhysicalApplyPlanContract | ArtifactPhysicalRollbackPlanContract
)
_ROOT_ALIAS = re.compile(r"[a-z][a-z0-9_-]{0,63}")


def canonical_artifact_physical_payload(value: object) -> str:
    """Return the canonical JSON used by every MB-217 fingerprint."""

    if not is_dataclass(value):
        raise TypeError("artifact physical payload must be a dataclass")
    payload = asdict(value)
    field_name = _SELF_FINGERPRINT_FIELD.get(type(value))
    if field_name is None:
        raise TypeError("unsupported artifact physical contract")
    payload.pop(field_name, None)
    return dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def artifact_physical_fingerprint(value: object) -> str:
    return sha256(canonical_artifact_physical_payload(value).encode("utf-8")).hexdigest()


def _seal(value: _T, field_name: str) -> _T:
    return replace(value, **{field_name: artifact_physical_fingerprint(value)})


def seal_artifact_physical_apply_plan(
    plan: ArtifactPhysicalApplyPlanContract,
) -> ArtifactPhysicalApplyPlanContract:
    return _seal(plan, "plan_fingerprint")


def seal_artifact_physical_rollback_plan(
    plan: ArtifactPhysicalRollbackPlanContract,
) -> ArtifactPhysicalRollbackPlanContract:
    return _seal(plan, "plan_fingerprint")


def seal_artifact_physical_saga_event(
    event: ArtifactPhysicalSagaEventContract,
) -> ArtifactPhysicalSagaEventContract:
    return _seal(event, "event_fingerprint")


def seal_artifact_physical_saga_state(
    state: ArtifactPhysicalSagaStateContract,
) -> ArtifactPhysicalSagaStateContract:
    return _seal(state, "state_fingerprint")


def seal_physical_artifact_version(
    version: PhysicalArtifactVersionContract,
) -> PhysicalArtifactVersionContract:
    return _seal(version, "version_fingerprint")


def seal_artifact_physical_lineage(
    lineage: ArtifactPhysicalLineageContract,
) -> ArtifactPhysicalLineageContract:
    return _seal(lineage, "lineage_fingerprint")


def seal_artifact_physical_outbox_item(
    item: ArtifactPhysicalOutboxItemContract,
) -> ArtifactPhysicalOutboxItemContract:
    return _seal(item, "outbox_fingerprint")


def seal_artifact_physical_outbox_delivery(
    delivery: ArtifactPhysicalOutboxDeliveryContract,
) -> ArtifactPhysicalOutboxDeliveryContract:
    return _seal(delivery, "delivery_fingerprint")


def seal_local_text_physical_state_attestation(
    attestation: LocalTextPhysicalStateAttestationContract,
) -> LocalTextPhysicalStateAttestationContract:
    return _seal(attestation, "attestation_fingerprint")


def seal_artifact_physical_canonical_commit_receipt(
    receipt: ArtifactPhysicalCanonicalCommitReceiptContract,
) -> ArtifactPhysicalCanonicalCommitReceiptContract:
    return _seal(receipt, "commit_fingerprint")


def _require_nonempty(value: object, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 512
        or value != value.strip()
        or not is_normalized("NFC", value)
        or any(category(char) in {"Cc", "Cf"} for char in value)
    ):
        raise ValueError(f"artifact_physical_{field_name}_invalid")


def require_valid_local_text_resource_ref(value: object, root_alias: str) -> None:
    """Validate the canonical MB-215 local-text resource grammar."""

    if not isinstance(value, str) or _ROOT_ALIAS.fullmatch(root_alias) is None:
        raise ValueError("artifact_physical_resource_ref_invalid")
    resource_ref = value
    prefix = f"text:{root_alias}/"
    if not resource_ref.startswith(prefix):
        raise ValueError("artifact_physical_resource_ref_invalid")
    relative = resource_ref.removeprefix(prefix)
    try:
        require_valid_local_text_relative_path(
            relative,
            allowed_extensions=(".md", ".txt"),
        )
    except (TypeError, ValueError):
        raise ValueError("artifact_physical_resource_ref_invalid") from None


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"artifact_physical_{field_name}_invalid")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"artifact_physical_{field_name}_invalid") from exc


def _require_timestamp(value: object, field_name: str) -> None:
    _require_nonempty(value, field_name)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"artifact_physical_{field_name}_timezone_required")


def _require_common_plan(plan: object) -> None:
    for field_name in (
        "saga_id",
        "mission_id",
        "owner_mission_id",
        "work_item_ref",
        "lineage_root_ref",
        "physical_operation_id",
        "root_alias",
    ):
        _require_nonempty(getattr(plan, field_name), field_name)
    if str(getattr(plan, "mission_id")) != str(getattr(plan, "owner_mission_id")):
        raise ValueError("artifact_physical_owner_mission_mismatch")
    if int(getattr(plan, "expected_lineage_revision")) < 0:
        raise ValueError("artifact_physical_expected_lineage_revision_invalid")
    if _ROOT_ALIAS.fullmatch(str(getattr(plan, "root_alias"))) is None:
        raise ValueError("artifact_physical_root_alias_invalid")
    require_valid_local_text_resource_ref(
        getattr(plan, "resource_ref"), str(getattr(plan, "root_alias"))
    )
    _require_timestamp(getattr(plan, "created_at"), "created_at")
    if (
        getattr(plan, "contains_content") is not False
        or getattr(plan, "read_only") is not True
        or getattr(plan, "immutable") is not True
    ):
        raise ValueError("artifact_physical_plan_authority_flags_invalid")


def require_valid_artifact_physical_apply_plan(
    plan: ArtifactPhysicalApplyPlanContract,
) -> None:
    _require_common_plan(plan)
    _require_nonempty(plan.artifact_ref, "artifact_ref")
    if plan.purpose != "apply" or plan.transition not in {"register", "replace"}:
        raise ValueError("artifact_physical_apply_purpose_or_transition_invalid")
    if plan.artifact_version < 1:
        raise ValueError("artifact_physical_artifact_version_invalid")
    if plan.transition == "register":
        if plan.supersedes_artifact_ref is not None or plan.expected_lineage_revision != 0:
            raise ValueError("artifact_physical_register_lineage_invalid")
        if plan.artifact_ref != plan.lineage_root_ref or plan.artifact_version != 1:
            raise ValueError("artifact_physical_register_identity_invalid")
    else:
        _require_nonempty(plan.supersedes_artifact_ref, "supersedes_artifact_ref")
        if plan.supersedes_artifact_ref == plan.artifact_ref:
            raise ValueError("artifact_physical_replacement_must_be_distinct")
        if plan.expected_lineage_revision < 1:
            raise ValueError("artifact_physical_replace_revision_invalid")
    for field_name in (
        "preflight_policy_version",
        "transaction_policy_version",
        "transaction_backend_version",
        "adapter_backend_version",
    ):
        _require_nonempty(getattr(plan, field_name), field_name)
    for field_name in (
        "rollback_plan_ref",
        "preflight_fingerprint",
        "root_config_fingerprint",
        "before_content_sha256",
        "desired_content_sha256",
        "plan_fingerprint",
    ):
        _require_sha256(getattr(plan, field_name), field_name)
    if not compare_digest(plan.plan_fingerprint, artifact_physical_fingerprint(plan)):
        raise ValueError("artifact_physical_apply_plan_fingerprint_mismatch")


def require_valid_artifact_physical_rollback_plan(
    plan: ArtifactPhysicalRollbackPlanContract,
) -> None:
    _require_common_plan(plan)
    if plan.purpose != "rollback":
        raise ValueError("artifact_physical_rollback_purpose_invalid")
    _require_nonempty(plan.active_artifact_ref, "active_artifact_ref")
    if plan.restored_artifact_ref is not None:
        _require_nonempty(plan.restored_artifact_ref, "restored_artifact_ref")
    if plan.active_artifact_ref == plan.restored_artifact_ref:
        raise ValueError("artifact_physical_rollback_refs_must_be_distinct")
    if plan.rollback_mode not in {"canonical_rollback", "precanonical_compensation"}:
        raise ValueError("artifact_physical_rollback_mode_invalid")
    if plan.rollback_mode == "canonical_rollback":
        if not plan.canonical_effect_expected:
            raise ValueError("artifact_physical_canonical_rollback_binding_invalid")
        if (
            plan.expected_lineage_revision < 1
            or plan.restored_artifact_ref is None
            or plan.active_artifact_version < 2
            or plan.restored_artifact_version is None
            or plan.restored_artifact_version != plan.active_artifact_version - 1
        ):
            raise ValueError("artifact_physical_rollback_version_binding_invalid")
    elif plan.canonical_effect_expected:
        raise ValueError("artifact_physical_compensation_canonical_effect_invalid")
    elif (
        plan.active_artifact_version < 1
        or (plan.restored_artifact_ref is None) != (plan.restored_artifact_version is None)
        or plan.restored_artifact_version is not None
        and plan.restored_artifact_version != plan.active_artifact_version - 1
        or plan.restored_artifact_ref is None
        and (plan.active_artifact_version != 1 or plan.expected_lineage_revision != 0)
        or plan.restored_artifact_ref is not None
        and (plan.active_artifact_version < 2 or plan.expected_lineage_revision < 1)
    ):
        raise ValueError("artifact_physical_compensation_version_invalid")
    for field_name in ("mutation_operation_id", "source_apply_saga_id"):
        _require_nonempty(getattr(plan, field_name), field_name)
    for field_name in (
        "mutation_receipt_fingerprint",
        "expected_current_sha256",
        "restored_content_sha256",
        "plan_fingerprint",
    ):
        _require_sha256(getattr(plan, field_name), field_name)
    if not compare_digest(plan.plan_fingerprint, artifact_physical_fingerprint(plan)):
        raise ValueError("artifact_physical_rollback_plan_fingerprint_mismatch")


def require_valid_artifact_physical_saga_event(
    event: ArtifactPhysicalSagaEventContract,
    *,
    previous_event: ArtifactPhysicalSagaEventContract | None = None,
) -> None:
    for field_name in (
        "event_id",
        "saga_id",
        "purpose",
        "phase",
        "physical_operation_id",
    ):
        _require_nonempty(getattr(event, field_name), field_name)
    for field_name in ("plan_fingerprint", "event_fingerprint"):
        _require_sha256(getattr(event, field_name), field_name)
    for field_name in ("mutation_receipt_fingerprint", "rollback_receipt_fingerprint"):
        value = getattr(event, field_name)
        if value is not None:
            _require_sha256(value, field_name)
    if event.physical_state_attestation_fingerprint is not None:
        _require_sha256(
            event.physical_state_attestation_fingerprint,
            "physical_state_attestation_fingerprint",
        )
    _require_timestamp(event.occurred_at, "occurred_at")
    if event.contains_content or not event.read_only or not event.immutable:
        raise ValueError("artifact_physical_event_authority_flags_invalid")
    if not compare_digest(event.event_fingerprint, artifact_physical_fingerprint(event)):
        raise ValueError("artifact_physical_event_fingerprint_mismatch")
    allowed_phases = (
        ARTIFACT_PHYSICAL_APPLY_PHASES
        if event.purpose == "apply"
        else ARTIFACT_PHYSICAL_ROLLBACK_PHASES
        if event.purpose == "rollback"
        else ()
    )
    if event.phase not in allowed_phases:
        raise ValueError("artifact_physical_event_phase_invalid")
    apply_post_effect = {
        "physical_applied",
        "canonical_committed",
        "completed",
        "compensation_required",
    }
    apply_compensated = event.purpose == "apply" and event.phase == "compensated"
    rollback_post_effect = {
        "physically_rolled_back",
        "canonical_rolled_back",
        "compensation_committed",
        "completed",
    }
    if (
        event.purpose == "apply"
        and event.phase in apply_post_effect
        and (
            event.mutation_receipt_fingerprint is None
            or event.rollback_receipt_fingerprint is not None
            or event.physical_state_attestation_fingerprint is None
        )
    ):
        raise ValueError("artifact_physical_apply_receipt_binding_invalid")
    if apply_compensated and (
        event.mutation_receipt_fingerprint is None
        or event.rollback_receipt_fingerprint is None
        or event.physical_state_attestation_fingerprint is None
    ):
        raise ValueError("artifact_physical_apply_compensation_binding_invalid")
    if (
        event.purpose == "apply"
        and event.phase in {"reserved", "effect_dispatched"}
        and any(
            value is not None
            for value in (
                event.mutation_receipt_fingerprint,
                event.rollback_receipt_fingerprint,
                event.physical_state_attestation_fingerprint,
            )
        )
    ):
        raise ValueError("artifact_physical_apply_early_receipt_forbidden")
    if (
        event.purpose == "rollback"
        and event.phase in rollback_post_effect
        and (
            event.mutation_receipt_fingerprint is None
            or event.rollback_receipt_fingerprint is None
            or event.physical_state_attestation_fingerprint is None
        )
    ):
        raise ValueError("artifact_physical_rollback_receipt_binding_invalid")
    if (
        event.purpose == "rollback"
        and event.phase
        in {
            "rollback_reserved",
            "rollback_effect_dispatched",
        }
        and (
            event.mutation_receipt_fingerprint is None
            or event.rollback_receipt_fingerprint is not None
            or event.physical_state_attestation_fingerprint is not None
        )
    ):
        raise ValueError("artifact_physical_rollback_early_receipt_binding_invalid")
    prior_phase = previous_event.phase if previous_event is not None else None
    allowed = (_APPLY_TRANSITIONS if event.purpose == "apply" else _ROLLBACK_TRANSITIONS).get(
        prior_phase, set()
    )
    if event.phase not in allowed:
        raise ValueError("artifact_physical_event_transition_invalid")
    expected_sequence = 1 if previous_event is None else previous_event.sequence + 1
    expected_previous = None if previous_event is None else previous_event.event_fingerprint
    if event.sequence != expected_sequence or event.previous_event_fingerprint != expected_previous:
        raise ValueError("artifact_physical_event_chain_invalid")
    if previous_event is not None and (
        event.saga_id != previous_event.saga_id
        or event.purpose != previous_event.purpose
        or event.plan_fingerprint != previous_event.plan_fingerprint
        or event.physical_operation_id != previous_event.physical_operation_id
    ):
        raise ValueError("artifact_physical_event_binding_changed")
    if previous_event is not None and datetime.fromisoformat(
        str(event.occurred_at).replace("Z", "+00:00")
    ) < datetime.fromisoformat(str(previous_event.occurred_at).replace("Z", "+00:00")):
        raise ValueError("artifact_physical_event_time_regressed")
    if previous_event is not None:
        for field_name in (
            "mutation_receipt_fingerprint",
            "rollback_receipt_fingerprint",
            "physical_state_attestation_fingerprint",
        ):
            previous_value = getattr(previous_event, field_name)
            current_value = getattr(event, field_name)
            if previous_value is not None and current_value != previous_value:
                raise ValueError("artifact_physical_event_receipt_binding_changed")


def require_valid_artifact_physical_saga_state(
    state: ArtifactPhysicalSagaStateContract,
) -> None:
    for field_name in (
        "saga_id",
        "purpose",
        "mission_id",
        "physical_operation_id",
        "phase",
    ):
        _require_nonempty(getattr(state, field_name), field_name)
    for field_name in (
        "plan_fingerprint",
        "latest_event_fingerprint",
        "state_fingerprint",
    ):
        _require_sha256(getattr(state, field_name), field_name)
    if state.physical_state_attestation_fingerprint is not None:
        _require_sha256(
            state.physical_state_attestation_fingerprint,
            "physical_state_attestation_fingerprint",
        )
    if state.latest_sequence < 1:
        raise ValueError("artifact_physical_state_sequence_invalid")
    _require_timestamp(state.updated_at, "updated_at")
    if state.contains_content or not state.read_only or not state.immutable:
        raise ValueError("artifact_physical_state_authority_flags_invalid")
    if not compare_digest(state.state_fingerprint, artifact_physical_fingerprint(state)):
        raise ValueError("artifact_physical_state_fingerprint_mismatch")


def require_valid_physical_artifact_version(version: PhysicalArtifactVersionContract) -> None:
    for field_name in (
        "mission_id",
        "artifact_ref",
        "owner_mission_id",
        "work_item_ref",
        "lineage_root_ref",
        "physical_operation_id",
        "resource_ref",
        "root_alias",
        "canonical_saga_id",
    ):
        _require_nonempty(getattr(version, field_name), field_name)
    if str(version.mission_id) != str(version.owner_mission_id) or version.artifact_version < 1:
        raise ValueError("artifact_physical_version_identity_invalid")
    if _ROOT_ALIAS.fullmatch(version.root_alias) is None:
        raise ValueError("artifact_physical_version_root_alias_invalid")
    require_valid_local_text_resource_ref(version.resource_ref, version.root_alias)
    for field_name in (
        "preflight_policy_version",
        "transaction_policy_version",
        "transaction_backend_version",
        "adapter_backend_version",
    ):
        _require_nonempty(getattr(version, field_name), field_name)
    for field_name in (
        "rollback_plan_ref",
        "mutation_receipt_fingerprint",
        "preflight_fingerprint",
        "root_config_fingerprint",
        "before_content_sha256",
        "desired_content_sha256",
        "version_fingerprint",
        "physical_state_attestation_fingerprint",
    ):
        _require_sha256(getattr(version, field_name), field_name)
    _require_timestamp(version.canonicalized_at, "canonicalized_at")
    if version.contains_content or not version.read_only or not version.immutable:
        raise ValueError("artifact_physical_version_flags_invalid")
    if not compare_digest(version.version_fingerprint, artifact_physical_fingerprint(version)):
        raise ValueError("artifact_physical_version_fingerprint_mismatch")


def require_valid_artifact_physical_lineage(lineage: ArtifactPhysicalLineageContract) -> None:
    for field_name in (
        "mission_id",
        "lineage_root_ref",
        "last_saga_id",
    ):
        _require_nonempty(getattr(lineage, field_name), field_name)
    if lineage.revision < 1:
        raise ValueError("artifact_physical_lineage_revision_invalid")
    _require_nonempty(lineage.active_artifact_ref, "active_artifact_ref")
    for field_name in ("last_event_fingerprint", "lineage_fingerprint"):
        _require_sha256(getattr(lineage, field_name), field_name)
    _require_timestamp(lineage.updated_at, "updated_at")
    if not lineage.read_only:
        raise ValueError("artifact_physical_lineage_flags_invalid")
    if not compare_digest(lineage.lineage_fingerprint, artifact_physical_fingerprint(lineage)):
        raise ValueError("artifact_physical_lineage_fingerprint_mismatch")


def require_valid_artifact_physical_outbox_item(
    item: ArtifactPhysicalOutboxItemContract,
) -> None:
    for field_name in (
        "outbox_id",
        "saga_id",
        "purpose",
        "event_name",
        "mission_id",
        "artifact_ref",
        "lineage_root_ref",
    ):
        _require_nonempty(getattr(item, field_name), field_name)
    for field_name in ("canonical_event_fingerprint", "outbox_fingerprint"):
        _require_sha256(getattr(item, field_name), field_name)
    _require_timestamp(item.created_at, "created_at")
    valid_names = (
        {"artifact_lifecycle_state_changed"}
        if item.purpose == "apply"
        else {
            "artifact_lifecycle_state_changed",
            "artifact_physical_apply_compensated",
        }
        if item.purpose == "rollback"
        else set()
    )
    if item.event_name not in valid_names:
        raise ValueError("artifact_physical_outbox_event_name_invalid")
    if item.contains_content or not item.read_only or not item.immutable:
        raise ValueError("artifact_physical_outbox_flags_invalid")
    if not compare_digest(item.outbox_fingerprint, artifact_physical_fingerprint(item)):
        raise ValueError("artifact_physical_outbox_fingerprint_mismatch")


def require_valid_artifact_physical_outbox_delivery(
    delivery: ArtifactPhysicalOutboxDeliveryContract,
) -> None:
    for field_name in ("delivery_id", "outbox_id", "publisher_ref"):
        _require_nonempty(getattr(delivery, field_name), field_name)
    _require_sha256(delivery.delivery_fingerprint, "delivery_fingerprint")
    _require_timestamp(delivery.published_at, "published_at")
    if not delivery.read_only or not delivery.immutable:
        raise ValueError("artifact_physical_delivery_flags_invalid")
    if not compare_digest(
        delivery.delivery_fingerprint,
        artifact_physical_fingerprint(delivery),
    ):
        raise ValueError("artifact_physical_delivery_fingerprint_mismatch")


def require_valid_local_text_physical_state_attestation(
    attestation: LocalTextPhysicalStateAttestationContract,
) -> None:
    for field_name in (
        "attestation_id",
        "purpose",
        "receipt_fingerprint",
        "mutation_operation_id",
        "resource_ref",
        "root_alias",
        "physical_state",
        "transaction_policy_version",
        "transaction_backend_version",
    ):
        _require_nonempty(getattr(attestation, field_name), field_name)
    if _ROOT_ALIAS.fullmatch(attestation.root_alias) is None:
        raise ValueError("local_text_physical_attestation_root_alias_invalid")
    require_valid_local_text_resource_ref(attestation.resource_ref, attestation.root_alias)
    if attestation.purpose not in {"mutation_current", "rollback_current"}:
        raise ValueError("local_text_physical_attestation_purpose_invalid")
    if attestation.physical_state not in {"applied", "restored", "absent"}:
        raise ValueError("local_text_physical_attestation_state_invalid")
    if attestation.purpose == "mutation_current":
        if attestation.rollback_operation_id is not None or attestation.physical_state != "applied":
            raise ValueError("local_text_mutation_attestation_binding_invalid")
    elif not attestation.rollback_operation_id or attestation.physical_state not in {
        "restored",
        "absent",
    }:
        raise ValueError("local_text_rollback_attestation_binding_invalid")
    for field_name in (
        "receipt_fingerprint",
        "root_config_fingerprint",
        "observed_content_sha256",
        "observed_identity_fingerprint",
        "journal_event_fingerprint",
        "attestation_fingerprint",
    ):
        _require_sha256(getattr(attestation, field_name), field_name)
    _require_timestamp(attestation.verified_at, "verified_at")
    if attestation.contains_content or not attestation.read_only or not attestation.immutable:
        raise ValueError("local_text_physical_attestation_flags_invalid")
    if not compare_digest(
        attestation.attestation_fingerprint,
        artifact_physical_fingerprint(attestation),
    ):
        raise ValueError("local_text_physical_attestation_fingerprint_mismatch")


def require_valid_artifact_physical_canonical_commit_receipt(
    receipt: ArtifactPhysicalCanonicalCommitReceiptContract,
) -> None:
    for field_name in (
        "commit_id",
        "purpose",
        "saga_id",
        "plan_fingerprint",
        "mission_id",
        "lineage_root_ref",
        "physical_operation_id",
        "resource_ref",
        "root_alias",
        "mutation_receipt_fingerprint",
        "physical_state_attestation_fingerprint",
        "canonical_event_fingerprint",
        "commit_fingerprint",
    ):
        _require_nonempty(getattr(receipt, field_name), field_name)
    if receipt.purpose not in {"apply", "rollback"}:
        raise ValueError("artifact_physical_commit_purpose_invalid")
    if _ROOT_ALIAS.fullmatch(receipt.root_alias) is None or receipt.lineage_revision < 0:
        raise ValueError("artifact_physical_commit_scope_invalid")
    require_valid_local_text_resource_ref(receipt.resource_ref, receipt.root_alias)
    for field_name in (
        "plan_fingerprint",
        "mutation_receipt_fingerprint",
        "physical_state_attestation_fingerprint",
        "canonical_event_fingerprint",
        "commit_fingerprint",
    ):
        _require_sha256(getattr(receipt, field_name), field_name)
    if receipt.rollback_receipt_fingerprint is not None:
        _require_sha256(
            receipt.rollback_receipt_fingerprint,
            "rollback_receipt_fingerprint",
        )
    if receipt.purpose == "apply":
        if (
            receipt.artifact_ref is None
            or receipt.artifact_version is None
            or receipt.artifact_version < 1
            or receipt.rollback_receipt_fingerprint is not None
        ):
            raise ValueError("artifact_physical_apply_commit_receipt_invalid")
    elif (receipt.artifact_ref is None) != (receipt.artifact_version is None):
        raise ValueError("artifact_physical_rollback_commit_artifact_binding_invalid")
    _require_timestamp(receipt.committed_at, "committed_at")
    if receipt.contains_content or not receipt.read_only or not receipt.immutable:
        raise ValueError("artifact_physical_commit_receipt_flags_invalid")
    if not compare_digest(
        receipt.commit_fingerprint,
        artifact_physical_fingerprint(receipt),
    ):
        raise ValueError("artifact_physical_commit_receipt_fingerprint_mismatch")


def saga_state_from_event(
    event: ArtifactPhysicalSagaEventContract,
    *,
    plan: ArtifactPhysicalPlanContract,
    previous_event: ArtifactPhysicalSagaEventContract | None = None,
) -> ArtifactPhysicalSagaStateContract:
    require_valid_artifact_physical_saga_event(
        event,
        previous_event=previous_event,
    )
    if (
        event.saga_id != plan.saga_id
        or event.purpose != plan.purpose
        or event.plan_fingerprint != plan.plan_fingerprint
        or event.physical_operation_id != plan.physical_operation_id
    ):
        raise ValueError("artifact_physical_state_plan_event_binding_mismatch")
    state = ArtifactPhysicalSagaStateContract(
        saga_id=event.saga_id,
        purpose=event.purpose,
        mission_id=plan.mission_id,
        physical_operation_id=event.physical_operation_id,
        plan_fingerprint=event.plan_fingerprint,
        phase=event.phase,
        latest_sequence=event.sequence,
        latest_event_fingerprint=event.event_fingerprint,
        mutation_receipt_fingerprint=event.mutation_receipt_fingerprint,
        rollback_receipt_fingerprint=event.rollback_receipt_fingerprint,
        physical_state_attestation_fingerprint=(event.physical_state_attestation_fingerprint),
        updated_at=event.occurred_at,
        state_fingerprint="",
    )
    return seal_artifact_physical_saga_state(state)
