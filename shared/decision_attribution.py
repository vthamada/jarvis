"""Pure, fail-closed decision/outcome attribution semantics."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import asdict, replace
from hashlib import sha256
from json import dumps

from shared.contracts import (
    DECISION_ATTRIBUTION_CAUSALITY_SCOPE,
    DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS,
    DECISION_ATTRIBUTION_STATUSES,
    DecisionAttributionClassificationContract,
    DecisionOutcomeAttributionRecordContract,
)
from shared.versioning import parse_canonical_semver

_APPLIED_MEMORY_POLICY_STATUSES = {
    "applied",
    "applied_with_conflict_resolution",
}
_MEMORY_POLICY_STATUSES = {
    *_APPLIED_MEMORY_POLICY_STATUSES,
    "blocked_no_eligible_signal",
    "governance_blocked",
    "not_applicable",
    "not_evaluated",
}
_WORKFLOW_POLICY_APPLICATION_STATUSES = {
    "applied",
    "not_applied",
    "not_evaluated",
}
_OUTCOME_STATUSES = {
    "allow",
    "allow_with_conditions",
    "block",
    "completed",
    "defer_for_validation",
    "failed",
    "governed",
}
_GOVERNANCE_DECISION_STATUSES = {
    "allow",
    "allow_with_conditions",
    "block",
    "defer_for_validation",
}
_MISSING_OUTCOME_STATUSES = {"", "missing", "not_observed", "unknown"}


def classify_decision_attribution(
    *,
    workflow_policy_ref: str | None = None,
    workflow_policy_application_status: str = "not_evaluated",
    workflow_policy_effects: Iterable[str] = (),
    memory_policy_decision_ref: str | None = None,
    memory_policy_status: str = "not_evaluated",
    memory_selected_refs: Iterable[str] = (),
    memory_use_reasons: Mapping[str, str] | None = None,
    memory_signal_kinds: Mapping[str, str] | None = None,
    memory_causal_use_allowed: bool = False,
    declared_effects_by_ref: Mapping[str, Iterable[str]] | None = None,
    outcome_ref: str | None = None,
    outcome_status: str | None = None,
    evidence_refs: Iterable[str] = (),
    memory_write_allowed: bool = False,
    execution_allowed: bool = False,
    tool_dispatch_allowed: bool = False,
    promotion_authorized: bool = False,
    automatic_promotion_allowed: bool = False,
    core_mutation_allowed: bool = False,
) -> DecisionAttributionClassificationContract:
    """Classify trace participation without inferring a causal effect or gain."""

    limitations: list[str] = []
    safe_workflow_ref = _optional_text(
        workflow_policy_ref,
        field_name="workflow_policy_ref",
        limitations=limitations,
    )
    safe_memory_decision_ref = _optional_text(
        memory_policy_decision_ref,
        field_name="memory_policy_decision_ref",
        limitations=limitations,
    )
    safe_outcome_ref = _optional_text(
        outcome_ref,
        field_name="outcome_ref",
        limitations=limitations,
    )
    safe_outcome_status = _optional_text(
        outcome_status,
        field_name="outcome_status",
        limitations=limitations,
    )
    selected_refs = _string_list(
        memory_selected_refs,
        field_name="memory_selected_refs",
        limitations=limitations,
        duplicate_prefix="memory_selected_ref_duplicate",
    )
    workflow_effects = _string_list(
        workflow_policy_effects,
        field_name="workflow_policy_effects",
        limitations=limitations,
        duplicate_prefix="workflow_policy_effect_duplicate",
    )
    safe_evidence_refs = _string_list(
        evidence_refs,
        field_name="evidence_refs",
        limitations=limitations,
        duplicate_prefix="attribution_evidence_ref_duplicate",
    )
    safe_use_reasons = _string_map(
        memory_use_reasons,
        field_name="memory_use_reasons",
        limitations=limitations,
    )
    safe_signal_kinds = _string_map(
        memory_signal_kinds,
        field_name="memory_signal_kinds",
        limitations=limitations,
    )
    safe_effects_by_ref = _effects_map(
        declared_effects_by_ref,
        limitations=limitations,
    )

    if any(
        value is not False
        for value in (
            memory_write_allowed,
            execution_allowed,
            tool_dispatch_allowed,
            promotion_authorized,
            automatic_promotion_allowed,
            core_mutation_allowed,
        )
    ):
        limitations.append("authority_claim_not_allowed")
    if not isinstance(memory_causal_use_allowed, bool):
        limitations.append("memory_causal_use_allowed_must_be_boolean")
        memory_causal_use_allowed = False
    if safe_outcome_ref is None or (
        safe_outcome_status is None
        or safe_outcome_status.lower() in _MISSING_OUTCOME_STATUSES
    ):
        limitations.append("outcome_evidence_required")
    elif safe_outcome_status not in _OUTCOME_STATUSES:
        limitations.append("outcome_status_not_canonical")
    if not safe_evidence_refs:
        limitations.append("attribution_evidence_refs_required")

    if (
        workflow_policy_application_status
        not in _WORKFLOW_POLICY_APPLICATION_STATUSES
    ):
        limitations.append("workflow_policy_application_status_not_canonical")
    if (
        workflow_policy_application_status != "applied"
        and workflow_effects
    ):
        limitations.append("workflow_policy_effects_without_application")
    if memory_policy_status not in _MEMORY_POLICY_STATUSES:
        limitations.append("memory_policy_status_not_canonical")
    if memory_policy_status == "governance_blocked":
        limitations.append("memory_policy_governance_blocked")
    if memory_policy_status in _APPLIED_MEMORY_POLICY_STATUSES:
        if safe_memory_decision_ref is None:
            limitations.append(
                "memory_policy_decision_ref_required_for_applied_status"
            )
        if not selected_refs:
            limitations.append(
                "memory_selected_refs_required_for_applied_status"
            )
    elif selected_refs:
        limitations.append(
            "memory_policy_status_mismatch_for_selected_memory"
        )
    if memory_causal_use_allowed is True and not selected_refs:
        limitations.append("memory_causal_use_without_selected_memory")

    participating_refs: list[str] = []
    if workflow_policy_application_status == "applied":
        if safe_workflow_ref is None:
            limitations.append("workflow_policy_ref_required_for_applied_status")
        else:
            participating_refs.append(safe_workflow_ref)

    if selected_refs:
        for selected_ref in selected_refs:
            if not safe_use_reasons.get(selected_ref):
                limitations.append(
                    f"memory_use_reason_required:{selected_ref}"
                )
            if not safe_signal_kinds.get(selected_ref):
                limitations.append(
                    f"memory_signal_kind_required:{selected_ref}"
                )
            if selected_ref not in participating_refs:
                participating_refs.append(selected_ref)
            else:
                limitations.append(
                    f"participating_ref_source_collision:{selected_ref}"
                )

    if not participating_refs:
        limitations.append("guidance_participation_evidence_required")
    for effect_ref in safe_effects_by_ref:
        if effect_ref not in participating_refs:
            limitations.append(
                f"declared_effect_for_non_participant:{effect_ref}"
            )

    declared_causal_refs: list[str] = []
    if (
        safe_workflow_ref is not None
        and safe_workflow_ref in participating_refs
        and workflow_effects
    ):
        declared_causal_refs.append(safe_workflow_ref)
    if memory_causal_use_allowed is True:
        declared_causal_refs.extend(
            selected_ref
            for selected_ref in selected_refs
            if safe_effects_by_ref.get(selected_ref)
            and selected_ref not in declared_causal_refs
        )
    correlated_refs = [
        ref for ref in participating_refs if ref not in declared_causal_refs
    ]

    limitations = _dedupe(limitations)
    attribution_reasons: list[str] = []
    if limitations:
        attribution_status = "insufficient_evidence"
        declared_causal_refs = []
        correlated_refs = list(participating_refs)
        attribution_reasons.append("classification_blocked_by_limitations")
    elif declared_causal_refs:
        attribution_status = "declared_causality"
        attribution_reasons.extend(
            f"declared_runtime_participation:{ref}"
            for ref in declared_causal_refs
        )
        attribution_reasons.extend(
            f"correlated_runtime_participation:{ref}" for ref in correlated_refs
        )
    else:
        attribution_status = "correlation_only"
        attribution_reasons.extend(
            f"correlated_runtime_participation:{ref}" for ref in correlated_refs
        )
    attribution_reasons.extend(
        [
            "declared_participation_is_not_causal_effect_proof",
            "gain_requires_valid_comparator",
        ]
    )
    if attribution_status not in DECISION_ATTRIBUTION_STATUSES:
        attribution_status = "insufficient_evidence"
        limitations.append("invalid_attribution_status")

    return DecisionAttributionClassificationContract(
        attribution_status=attribution_status,
        participating_refs=participating_refs,
        declared_causal_refs=declared_causal_refs,
        correlated_refs=correlated_refs,
        attribution_reasons=_dedupe(attribution_reasons),
        limitations=_dedupe(limitations),
        causality_scope=DECISION_ATTRIBUTION_CAUSALITY_SCOPE,
        causal_effect_proven=False,
        gain_claim_status=DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS,
        read_only=True,
        human_review_required=True,
        memory_write_allowed=False,
        execution_allowed=False,
        tool_dispatch_allowed=False,
        promotion_authorized=False,
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
    )


def classify_decision_attribution_record(
    record: DecisionOutcomeAttributionRecordContract,
) -> DecisionAttributionClassificationContract:
    """Recompute the classification carried by an immutable record."""

    return classify_decision_attribution(
        workflow_policy_ref=record.workflow_policy_ref,
        workflow_policy_application_status=(
            record.workflow_policy_application_status
        ),
        workflow_policy_effects=record.workflow_policy_effects,
        memory_policy_decision_ref=record.memory_policy_decision_ref,
        memory_policy_status=record.memory_policy_status,
        memory_selected_refs=record.memory_selected_refs,
        memory_use_reasons=record.memory_use_reasons,
        memory_signal_kinds=record.memory_signal_kinds,
        memory_causal_use_allowed=record.memory_causal_use_allowed,
        declared_effects_by_ref=record.declared_effects_by_ref,
        outcome_ref=record.outcome_ref,
        outcome_status=record.outcome_status,
        evidence_refs=record.evidence_refs,
        memory_write_allowed=record.memory_write_allowed,
        execution_allowed=record.execution_allowed,
        tool_dispatch_allowed=record.tool_dispatch_allowed,
        promotion_authorized=record.promotion_authorized,
        automatic_promotion_allowed=record.automatic_promotion_allowed,
        core_mutation_allowed=record.core_mutation_allowed,
    )


def canonicalize_decision_attribution_record(
    record: DecisionOutcomeAttributionRecordContract,
) -> DecisionOutcomeAttributionRecordContract:
    """Attach the one canonical classification without changing source evidence."""

    classification = classify_decision_attribution_record(record)
    return replace(
        record,
        participating_refs=list(classification.participating_refs),
        declared_causal_refs=list(classification.declared_causal_refs),
        correlated_refs=list(classification.correlated_refs),
        attribution_status=classification.attribution_status,
        attribution_reasons=list(classification.attribution_reasons),
        limitations=list(classification.limitations),
        causality_scope=DECISION_ATTRIBUTION_CAUSALITY_SCOPE,
        causal_effect_proven=False,
        gain_claim_status=DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS,
    )


def validate_decision_attribution_record(
    record: DecisionOutcomeAttributionRecordContract,
) -> None:
    """Reject non-canonical, mutable or authority-bearing attribution records."""

    _require_text(record.attribution_record_id, "attribution_record_id")
    _require_text(str(record.request_id), "request_id")
    _require_text(str(record.session_id), "session_id")
    _require_text(record.observed_at, "observed_at")
    _require_text(record.governance_decision_ref, "governance_decision_ref")
    _require_text(record.governance_decision_status, "governance_decision_status")
    if record.governance_decision_status not in _GOVERNANCE_DECISION_STATUSES:
        raise ValueError("governance_decision_status is not canonical")
    if record.workflow_policy_application_status == "applied":
        for field_name, value in (
            ("workflow_policy_ref", record.workflow_policy_ref),
            ("workflow_policy_version", record.workflow_policy_version),
            (
                "workflow_policy_source_registry_ref",
                record.workflow_policy_source_registry_ref,
            ),
            (
                "workflow_policy_source_registry_fingerprint",
                record.workflow_policy_source_registry_fingerprint,
            ),
        ):
            _require_text(value, field_name)
    for selected_ref in record.memory_selected_refs:
        if not selected_ref.startswith("reviewed-playbook://"):
            continue
        version = record.memory_version_refs.get(selected_ref)
        review_decision_ref = record.memory_review_decision_refs.get(selected_ref)
        if parse_canonical_semver(version) is None:
            raise ValueError(
                "reviewed procedural attribution requires canonical version"
            )
        _require_text(
            review_decision_ref,
            "reviewed_procedural_review_decision_ref",
        )
    _require_text(record.experience_id, "experience_id")
    if record.mission_id is None:
        raise ValueError("experience_id requires mission_id")
    expected_experience_id = (
        f"experience://{record.mission_id}/{record.request_id}"
    )
    if record.experience_id != expected_experience_id:
        raise ValueError(
            "experience_id does not match request and mission identity"
        )
    if record.outcome_ref != record.experience_id:
        raise ValueError("outcome_ref must match experience_id")

    canonical = canonicalize_decision_attribution_record(record)
    classification_fields = (
        "participating_refs",
        "declared_causal_refs",
        "correlated_refs",
        "attribution_status",
        "attribution_reasons",
        "limitations",
        "causality_scope",
        "causal_effect_proven",
        "gain_claim_status",
    )
    if any(
        getattr(record, field_name) != getattr(canonical, field_name)
        for field_name in classification_fields
    ):
        raise ValueError("decision attribution classification does not match evidence")
    if record.attribution_status not in DECISION_ATTRIBUTION_STATUSES:
        raise ValueError("decision attribution status is not canonical")
    if (
        record.read_only is not True
        or record.immutable is not True
        or record.human_review_required is not True
        or record.memory_write_allowed is not False
        or record.execution_allowed is not False
        or record.tool_dispatch_allowed is not False
        or record.promotion_authorized is not False
        or record.automatic_promotion_allowed is not False
        or record.core_mutation_allowed is not False
    ):
        raise ValueError("decision attribution authority flags are not allowed")
    if record.causal_effect_proven is not False:
        raise ValueError("decision attribution cannot prove a causal effect")
    if record.gain_claim_status != DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS:
        raise ValueError("decision attribution cannot establish gain without comparator")


def canonical_decision_attribution_payload(
    record: DecisionOutcomeAttributionRecordContract,
) -> str:
    """Serialize one record deterministically for immutable persistence."""

    return dumps(
        asdict(record),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decision_attribution_fingerprint(
    record: DecisionOutcomeAttributionRecordContract,
) -> str:
    """Return the stable SHA-256 identity of the complete canonical payload."""

    payload = canonical_decision_attribution_payload(record)
    return sha256(payload.encode("utf-8")).hexdigest()


def _optional_text(
    value: object,
    *,
    field_name: str,
    limitations: list[str],
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        limitations.append(f"{field_name}_must_be_text")
        return None
    normalized = value.strip()
    if not normalized:
        limitations.append(f"{field_name}_must_not_be_empty")
        return None
    if normalized != value:
        limitations.append(f"{field_name}_must_be_canonical")
    return normalized


def _string_list(
    values: Iterable[str],
    *,
    field_name: str,
    limitations: list[str],
    duplicate_prefix: str,
) -> list[str]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        limitations.append(f"{field_name}_must_be_a_list")
        return []
    try:
        raw_values = list(values)
    except TypeError:
        limitations.append(f"{field_name}_must_be_a_list")
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in raw_values:
        safe_value = _optional_text(
            value,
            field_name=f"{field_name}_item",
            limitations=limitations,
        )
        if safe_value is None:
            continue
        if safe_value in seen:
            limitations.append(f"{duplicate_prefix}:{safe_value}")
            continue
        seen.add(safe_value)
        normalized.append(safe_value)
    return normalized


def _string_map(
    values: Mapping[str, str] | None,
    *,
    field_name: str,
    limitations: list[str],
) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        limitations.append(f"{field_name}_must_be_a_map")
        return {}
    normalized: dict[str, str] = {}
    for key, value in values.items():
        safe_key = _optional_text(
            key,
            field_name=f"{field_name}_key",
            limitations=limitations,
        )
        safe_value = _optional_text(
            value,
            field_name=f"{field_name}_value",
            limitations=limitations,
        )
        if safe_key is not None and safe_value is not None:
            normalized[safe_key] = safe_value
    return normalized


def _effects_map(
    values: Mapping[str, Iterable[str]] | None,
    *,
    limitations: list[str],
) -> dict[str, list[str]]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        limitations.append("declared_effects_by_ref_must_be_a_map")
        return {}
    normalized: dict[str, list[str]] = {}
    for key, effects in values.items():
        safe_key = _optional_text(
            key,
            field_name="declared_effects_by_ref_key",
            limitations=limitations,
        )
        safe_effects = _string_list(
            effects,
            field_name="declared_effects_by_ref_effects",
            limitations=limitations,
            duplicate_prefix="declared_effect_duplicate",
        )
        if safe_key is not None:
            normalized[safe_key] = safe_effects
    return normalized


def _require_text(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"decision attribution {field_name} is required and canonical")


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
