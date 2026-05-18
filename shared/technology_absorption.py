"""Governed grammar for technology absorption candidates."""

from __future__ import annotations

from collections.abc import Iterable

VALID_ABSORPTION_CLASSES = {
    "reference",
    "sandbox_experiment",
    "controlled_complement",
    "promotable_translation",
}

VALID_CANDIDATE_STATUSES = {
    "observed",
    "candidate",
    "sandboxed",
    "validated",
    "rejected",
    "promoted",
    "deprecated",
    "rolled_back",
}

SUBORDINATE_CORE_ROLES = {
    "reference",
    "experiment",
    "complement",
    "adapter",
    "tool",
    "subordinate",
}


def _as_list(values: Iterable[str] | None) -> list[str]:
    return [str(value) for value in values or [] if str(value).strip()]


def derive_technology_absorption_state(
    *,
    absorption_class: str,
    candidate_status: str,
    requested_core_role: str,
    evidence_refs: Iterable[str] | None = None,
    proposed_tests: Iterable[str] | None = None,
    blockers: Iterable[str] | None = None,
    human_review_required: bool = True,
    rollback_plan_ref: str | None = None,
) -> dict[str, object]:
    """Classify a technology candidate without allowing automatic promotion."""

    normalized_class = str(absorption_class or "").strip()
    normalized_status = str(candidate_status or "").strip()
    normalized_role = str(requested_core_role or "").strip()
    evidence = _as_list(evidence_refs)
    tests = _as_list(proposed_tests)
    resolved_blockers = _as_list(blockers)

    if normalized_class not in VALID_ABSORPTION_CLASSES:
        resolved_blockers.append("unknown_absorption_class")
    if normalized_status not in VALID_CANDIDATE_STATUSES:
        resolved_blockers.append("unknown_candidate_status")
    if normalized_role not in SUBORDINATE_CORE_ROLES:
        resolved_blockers.append("core_sovereignty_violation")

    if resolved_blockers:
        return {
            "absorption_readiness": "blocked",
            "absorption_decision": "block_absorption",
            "experiment_lane_status": "attention_required",
            "promotion_readiness": "blocked",
            "requires_sandbox": True,
            "requires_human_review": True,
            "blockers": sorted(set(resolved_blockers)),
        }

    if normalized_class == "reference":
        return {
            "absorption_readiness": "reference_only",
            "absorption_decision": "hold_as_reference",
            "experiment_lane_status": "baseline_only",
            "promotion_readiness": "not_applicable",
            "requires_sandbox": False,
            "requires_human_review": False,
            "blockers": [],
        }

    missing_controls: list[str] = []
    if not evidence:
        missing_controls.append("missing_evidence_refs")
    if not tests:
        missing_controls.append("missing_proposed_tests")
    if not rollback_plan_ref:
        missing_controls.append("missing_rollback_plan")
    if not human_review_required:
        missing_controls.append("manual_review_not_required")

    if normalized_status == "validated" and not missing_controls:
        return {
            "absorption_readiness": "ready_for_manual_review",
            "absorption_decision": "manual_promotion_review",
            "experiment_lane_status": "controlled_candidate",
            "promotion_readiness": "manual_review_only",
            "requires_sandbox": True,
            "requires_human_review": True,
            "blockers": [],
        }

    if normalized_status == "rejected":
        return {
            "absorption_readiness": "rejected",
            "absorption_decision": "hold_baseline",
            "experiment_lane_status": "baseline_only",
            "promotion_readiness": "blocked",
            "requires_sandbox": True,
            "requires_human_review": True,
            "blockers": missing_controls,
        }

    return {
        "absorption_readiness": "sandbox_required",
        "absorption_decision": "hold_in_lane",
        "experiment_lane_status": "controlled_candidate",
        "promotion_readiness": "blocked" if missing_controls else "manual_review_only",
        "requires_sandbox": True,
        "requires_human_review": True,
        "blockers": missing_controls,
    }
