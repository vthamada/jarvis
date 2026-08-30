"""Canonical fingerprints and fail-closed workflow lifecycle validation."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from hashlib import sha256
from json import dumps
from typing import Any, Callable

from shared.contracts import (
    WorkflowLifecycleGovernanceAssessmentContract,
    WorkflowLifecycleTransitionContract,
)
from shared.domain_registry import (
    ACTIVE_WORKFLOW_MATURITIES,
    ACTIVE_WORKFLOW_REGISTRY_REF,
    RUNTIME_ROUTE_REGISTRY,
    active_workflow_registry_fingerprint,
    workflow_definition_hash,
    workflow_runtime_guidance,
)
from shared.versioning import parse_canonical_semver

WORKFLOW_LIFECYCLE_ACTIONS = frozenset(
    {"activate_candidate", "rollback_to_baseline"}
)
WORKFLOW_LIFECYCLE_STATUSES = frozenset(
    {"active_promoted", "baseline_restored"}
)
WORKFLOW_LIFECYCLE_MEMORY_WRITE_MODE = "through_core_only"

_ACTION_STATUS = {
    "activate_candidate": "active_promoted",
    "rollback_to_baseline": "baseline_restored",
}
_AUTHORITY_FALSE_FIELDS = (
    "active_registry_write_allowed",
    "runtime_execution_allowed",
    "automatic_promotion_allowed",
    "automatic_rollback_allowed",
    "core_mutation_allowed",
)
_ARTIFACT_FINGERPRINT_FIELDS = (
    "proposal_fingerprint",
    "review_decision_fingerprint",
    "release_checklist_fingerprint",
    "promotion_gate_fingerprint",
    "workflow_eval_run_fingerprint",
    "rollback_plan_fingerprint",
)


def canonical_workflow_lifecycle_payload(value: object) -> str:
    """Serialize a lifecycle or release artifact deterministically."""

    payload: Any = asdict(value) if is_dataclass(value) else value
    return dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def workflow_lifecycle_artifact_fingerprint(value: object) -> str:
    """Return the stable SHA-256 fingerprint of a complete canonical artifact."""

    payload = canonical_workflow_lifecycle_payload(value)
    return sha256(payload.encode("utf-8")).hexdigest()


workflow_lifecycle_transition_fingerprint = workflow_lifecycle_artifact_fingerprint


def validate_workflow_lifecycle_transition_shape(
    transition: WorkflowLifecycleTransitionContract,
) -> list[str]:
    """Validate a persisted runtime binding without re-evaluating its CAS history."""

    return _validation_failures(
        lambda: _validate_transition_shape_or_raise(transition)
    )


def validate_workflow_lifecycle_transition(
    transition: WorkflowLifecycleTransitionContract,
    *,
    current_transition: WorkflowLifecycleTransitionContract | None = None,
) -> list[str]:
    """Validate one append-only transition and its exact predecessor, if any."""

    failures = validate_workflow_lifecycle_transition_shape(transition)
    if failures:
        return failures
    if current_transition is None:
        if transition.revision != 1:
            return ["workflow_lifecycle_previous_transition_required"]
        if (
            transition.previous_transition_id is not None
            or transition.previous_transition_fingerprint is not None
        ):
            return ["workflow_lifecycle_genesis_cannot_claim_predecessor"]
        if transition.transition_action != "activate_candidate":
            return ["workflow_lifecycle_genesis_must_activate_candidate"]
        return []

    failures = validate_workflow_lifecycle_transition_shape(current_transition)
    if failures:
        return [f"current_transition:{failure}" for failure in failures]
    return _validation_failures(
        lambda: _validate_transition_lineage_or_raise(
            transition,
            current_transition=current_transition,
        )
    )


def validate_workflow_lifecycle_governance_assessment(
    assessment: WorkflowLifecycleGovernanceAssessmentContract,
    *,
    transition: WorkflowLifecycleTransitionContract | None = None,
    current_transition: WorkflowLifecycleTransitionContract | None = None,
) -> list[str]:
    """Validate an assessment against the transition it governs."""

    if transition is None:
        return ["workflow_lifecycle_transition_required_for_assessment"]
    transition_failures = validate_workflow_lifecycle_transition(
        transition,
        current_transition=current_transition,
    )
    if transition_failures:
        return [f"transition:{failure}" for failure in transition_failures]
    return _validation_failures(
        lambda: _validate_assessment_or_raise(assessment, transition=transition)
    )


def _validate_transition_shape_or_raise(
    transition: WorkflowLifecycleTransitionContract,
) -> None:
    for field_name in (
        "transition_id",
        "workflow_profile",
        "route",
        "transition_action",
        "transition_status",
        "source_registry_ref",
        "source_registry_fingerprint",
        "baseline_version_ref",
        "baseline_definition_hash",
        "candidate_version_ref",
        "candidate_definition_hash",
        "active_version_ref",
        "active_definition_hash",
        "evolution_proposal_id",
        "review_decision_id",
        "release_checklist_id",
        "promotion_gate_id",
        "workflow_eval_run_id",
        "rollback_plan_id",
        "human_authorization_ref",
        "operator_ref",
        "timestamp",
    ):
        _require_text(getattr(transition, field_name), field_name=field_name)
    if transition.transition_action not in WORKFLOW_LIFECYCLE_ACTIONS:
        raise ValueError("workflow lifecycle transition_action is not canonical")
    if transition.transition_status not in WORKFLOW_LIFECYCLE_STATUSES:
        raise ValueError("workflow lifecycle transition_status is not canonical")
    if _ACTION_STATUS[transition.transition_action] != transition.transition_status:
        raise ValueError("workflow lifecycle action and status do not match")
    if not transition.transition_id.startswith("workflow-lifecycle-transition://"):
        raise ValueError("workflow lifecycle transition_id must be typed")
    if not transition.human_authorization_ref.startswith("human-authorization://"):
        raise ValueError("workflow lifecycle human_authorization_ref must be typed")
    if not transition.operator_ref.startswith("operator://"):
        raise ValueError("workflow lifecycle operator_ref must be typed")
    if transition.human_authorization_ref == transition.operator_ref:
        raise ValueError("workflow lifecycle human authorization and operator must differ")
    artifact_ids = {
        transition.evolution_proposal_id,
        transition.review_decision_id,
        transition.release_checklist_id,
        transition.promotion_gate_id,
        transition.workflow_eval_run_id,
        transition.rollback_plan_id,
    }
    if transition.human_authorization_ref in artifact_ids:
        raise ValueError("workflow lifecycle human authorization must be independent")
    if (
        isinstance(transition.revision, bool)
        or not isinstance(transition.revision, int)
        or not 1 <= transition.revision <= 2**31 - 1
    ):
        raise ValueError("workflow lifecycle revision must be a positive integer")
    _require_optional_text(
        transition.previous_transition_id,
        field_name="previous_transition_id",
    )
    if transition.previous_transition_fingerprint is not None:
        _require_sha256(
            transition.previous_transition_fingerprint,
            field_name="previous_transition_fingerprint",
        )
    if (transition.previous_transition_id is None) != (
        transition.previous_transition_fingerprint is None
    ):
        raise ValueError("workflow lifecycle predecessor id and fingerprint must pair")

    for field_name in (
        "source_registry_fingerprint",
        "baseline_definition_hash",
        "candidate_definition_hash",
        "active_definition_hash",
        *_ARTIFACT_FINGERPRINT_FIELDS,
    ):
        _require_sha256(getattr(transition, field_name), field_name=field_name)
    if transition.source_registry_ref != ACTIVE_WORKFLOW_REGISTRY_REF:
        raise ValueError("workflow lifecycle source registry is not sovereign")
    if (
        transition.source_registry_fingerprint
        != active_workflow_registry_fingerprint()
    ):
        raise ValueError("workflow lifecycle source registry fingerprint drifted")
    route_entry = RUNTIME_ROUTE_REGISTRY.get(transition.route)
    if (
        route_entry is None
        or route_entry.maturity not in ACTIVE_WORKFLOW_MATURITIES
        or route_entry.workflow_profile != transition.workflow_profile
    ):
        raise ValueError("workflow lifecycle route/profile is not active and canonical")
    baseline_success_criteria = list(
        dict.fromkeys(
            [
                *route_entry.expected_deliverables,
                workflow_runtime_guidance(transition.workflow_profile).success_focus,
            ]
        )
    )
    expected_baseline_hash = workflow_definition_hash(
        workflow_steps=route_entry.workflow_steps,
        workflow_checkpoints=route_entry.workflow_checkpoints,
        workflow_decision_points=route_entry.workflow_decision_points,
        success_criteria=baseline_success_criteria,
    )
    if transition.baseline_definition_hash != expected_baseline_hash:
        raise ValueError("workflow lifecycle baseline is not the sovereign definition")
    baseline_version = _workflow_version_from_ref(
        transition.baseline_version_ref,
        workflow_profile=transition.workflow_profile,
        field_name="baseline_version_ref",
    )
    candidate_version = _workflow_version_from_ref(
        transition.candidate_version_ref,
        workflow_profile=transition.workflow_profile,
        field_name="candidate_version_ref",
    )
    if candidate_version <= baseline_version:
        raise ValueError("workflow lifecycle candidate version must advance baseline")
    if transition.candidate_definition_hash == transition.baseline_definition_hash:
        raise ValueError("workflow lifecycle candidate must differ from baseline")

    active_steps = _canonical_text_list(
        transition.active_workflow_steps,
        field_name="active_workflow_steps",
        minimum=1,
        maximum=100,
    )
    active_checkpoints = _canonical_text_list(
        transition.active_workflow_checkpoints,
        field_name="active_workflow_checkpoints",
        minimum=1,
        maximum=100,
    )
    active_decision_points = _canonical_text_list(
        transition.active_workflow_decision_points,
        field_name="active_workflow_decision_points",
        minimum=0,
        maximum=100,
    )
    active_success_criteria = _canonical_text_list(
        transition.active_success_criteria,
        field_name="active_success_criteria",
        minimum=1,
        maximum=100,
    )
    expected_active_hash = workflow_definition_hash(
        workflow_steps=active_steps,
        workflow_checkpoints=active_checkpoints,
        workflow_decision_points=active_decision_points,
        success_criteria=active_success_criteria,
    )
    if transition.active_definition_hash != expected_active_hash:
        raise ValueError("workflow lifecycle active definition fingerprint mismatch")
    if transition.transition_action == "activate_candidate":
        if (
            transition.active_version_ref != transition.candidate_version_ref
            or transition.active_definition_hash
            != transition.candidate_definition_hash
        ):
            raise ValueError("workflow lifecycle activation must bind the candidate")
        if transition.failure_refs:
            raise ValueError("workflow lifecycle activation cannot claim failure refs")
    else:
        if (
            transition.active_version_ref != transition.baseline_version_ref
            or transition.active_definition_hash
            != transition.baseline_definition_hash
        ):
            raise ValueError("workflow lifecycle rollback must restore the baseline")
        _canonical_text_list(
            transition.failure_refs,
            field_name="failure_refs",
            minimum=1,
            maximum=50,
        )
    evidence_refs = _canonical_text_list(
        transition.evidence_refs,
        field_name="evidence_refs",
        minimum=7,
        maximum=100,
    )
    required_evidence_refs = {
        transition.evolution_proposal_id,
        transition.review_decision_id,
        transition.release_checklist_id,
        transition.promotion_gate_id,
        transition.workflow_eval_run_id,
        transition.rollback_plan_id,
        transition.human_authorization_ref,
    }
    if not required_evidence_refs.issubset(evidence_refs):
        raise ValueError(
            "workflow lifecycle evidence must bind every release and human ref"
        )
    _canonical_text_list(
        transition.completed_test_refs,
        field_name="completed_test_refs",
        minimum=1,
        maximum=100,
    )
    if transition.transition_action == "activate_candidate":
        _canonical_text_list(
            transition.failure_refs,
            field_name="failure_refs",
            minimum=0,
            maximum=0,
        )
    _require_timestamp(transition.timestamp, field_name="timestamp")
    if (
        transition.read_only is not True
        or transition.immutable is not True
        or transition.human_authorized is not True
        or transition.memory_write_mode != WORKFLOW_LIFECYCLE_MEMORY_WRITE_MODE
    ):
        raise ValueError("workflow lifecycle transition authority posture is unsafe")
    _validate_false_authorities(transition)


def _validate_transition_lineage_or_raise(
    transition: WorkflowLifecycleTransitionContract,
    *,
    current_transition: WorkflowLifecycleTransitionContract,
) -> None:
    if transition.revision != current_transition.revision + 1:
        raise ValueError("workflow lifecycle revision is not compare-and-swap safe")
    if transition.previous_transition_id != current_transition.transition_id:
        raise ValueError("workflow lifecycle previous transition id mismatch")
    if transition.previous_transition_fingerprint != (
        workflow_lifecycle_transition_fingerprint(current_transition)
    ):
        raise ValueError("workflow lifecycle previous transition fingerprint mismatch")
    for field_name in (
        "workflow_profile",
        "route",
        "source_registry_ref",
        "source_registry_fingerprint",
        "baseline_version_ref",
        "baseline_definition_hash",
    ):
        if getattr(transition, field_name) != getattr(current_transition, field_name):
            raise ValueError(f"workflow lifecycle lineage changed {field_name}")
    if transition.transition_action == "activate_candidate":
        if current_transition.transition_status != "baseline_restored":
            raise ValueError("workflow lifecycle activation requires restored baseline")
        if (
            current_transition.active_version_ref
            != current_transition.baseline_version_ref
            or current_transition.active_definition_hash
            != current_transition.baseline_definition_hash
        ):
            raise ValueError("workflow lifecycle predecessor did not restore baseline")
    else:
        if current_transition.transition_status != "active_promoted":
            raise ValueError("workflow lifecycle rollback requires active candidate")
        for field_name in (
            "candidate_version_ref",
            "candidate_definition_hash",
        ):
            if getattr(transition, field_name) != getattr(
                current_transition,
                field_name,
            ):
                raise ValueError(f"workflow lifecycle rollback changed {field_name}")
    if _parsed_timestamp(transition.timestamp) < _parsed_timestamp(
        current_transition.timestamp
    ):
        raise ValueError("workflow lifecycle timestamp precedes its predecessor")


def _validate_assessment_or_raise(
    assessment: WorkflowLifecycleGovernanceAssessmentContract,
    *,
    transition: WorkflowLifecycleTransitionContract,
) -> None:
    for field_name in (
        "assessment_id",
        "transition_id",
        "transition_action",
        "transition_fingerprint",
        "status",
        "timestamp",
    ):
        _require_text(getattr(assessment, field_name), field_name=field_name)
    _require_sha256(
        assessment.transition_fingerprint,
        field_name="transition_fingerprint",
    )
    if (
        assessment.transition_id != transition.transition_id
        or assessment.transition_action != transition.transition_action
        or assessment.transition_fingerprint
        != workflow_lifecycle_transition_fingerprint(transition)
    ):
        raise ValueError("workflow lifecycle assessment transition binding mismatch")
    if assessment.status not in {"approved", "blocked"}:
        raise ValueError("workflow lifecycle assessment status is not canonical")
    blockers = _canonical_text_list(
        assessment.blockers,
        field_name="assessment blockers",
        minimum=0,
        maximum=100,
    )
    _canonical_text_list(
        assessment.conditions,
        field_name="assessment conditions",
        minimum=1,
        maximum=50,
    )
    _canonical_text_list(
        assessment.policy_refs,
        field_name="assessment policy_refs",
        minimum=1,
        maximum=50,
    )
    approved = assessment.status == "approved"
    if approved != (not blockers):
        raise ValueError("workflow lifecycle assessment blockers/status mismatch")
    if assessment.human_authorization_verified is not approved:
        raise ValueError("workflow lifecycle human authorization projection mismatch")
    if assessment.transition_recording_authorized is not approved:
        raise ValueError("workflow lifecycle recording authority projection mismatch")
    if (
        assessment.human_review_required is not True
        or assessment.memory_write_mode != WORKFLOW_LIFECYCLE_MEMORY_WRITE_MODE
        or assessment.read_only is not True
    ):
        raise ValueError("workflow lifecycle assessment authority posture is unsafe")
    _validate_false_authorities(assessment)
    _require_timestamp(assessment.timestamp, field_name="assessment timestamp")
    if _parsed_timestamp(assessment.timestamp) < _parsed_timestamp(
        transition.timestamp
    ):
        raise ValueError("workflow lifecycle assessment predates transition")


def _validate_false_authorities(value: object) -> None:
    for field_name in _AUTHORITY_FALSE_FIELDS:
        if getattr(value, field_name, None) is not False:
            raise ValueError(f"workflow lifecycle {field_name} must be false")


def _workflow_version_from_ref(
    value: str,
    *,
    workflow_profile: str,
    field_name: str,
) -> tuple[int, int, int]:
    prefix = f"workflow-version://{workflow_profile}/"
    if not value.startswith(prefix):
        raise ValueError(f"{field_name} does not belong to workflow profile")
    version = parse_canonical_semver(value.removeprefix(prefix))
    if version is None:
        raise ValueError(f"{field_name} must end in canonical semver")
    return version


def _canonical_text_list(
    values: object,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> list[str]:
    if not isinstance(values, list) or not minimum <= len(values) <= maximum:
        raise ValueError(f"{field_name} must be a bounded list")
    canonical: list[str] = []
    for value in values:
        _require_text(value, field_name=field_name)
        canonical.append(value)
    if len(canonical) != len(set(canonical)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return canonical


def _require_optional_text(value: object, *, field_name: str) -> None:
    if value is not None:
        _require_text(value, field_name=field_name)


def _require_text(value: object, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 500
    ):
        raise ValueError(f"{field_name} must be canonical bounded text")


def _require_sha256(value: object, *, field_name: str) -> None:
    _require_text(value, field_name=field_name)
    assert isinstance(value, str)
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 fingerprint")


def _parsed_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("workflow lifecycle timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("workflow lifecycle timestamp must include a timezone")
    return parsed


def _require_timestamp(value: object, *, field_name: str) -> None:
    _require_text(value, field_name=field_name)
    assert isinstance(value, str)
    try:
        _parsed_timestamp(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc


def _validation_failures(validation: Callable[[], None]) -> list[str]:
    try:
        validation()
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    return []
