"""Governed causal policy for semantic, procedural and reviewed memory inputs."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime

from shared.contracts import (
    MemoryInfluencePolicyDecisionContract,
    MemoryInfluenceSignalContract,
)
from shared.versioning import parse_canonical_semver

MEMORY_INFLUENCE_PRIORITY = (
    "reviewed_learning",
    "procedural",
    "semantic",
    "reflection",
)
MEMORY_INFLUENCE_POLICY_REFS = (
    "policy://memory-influence/priority-v1",
    "policy://memory-influence/evidence-required",
    "policy://memory-influence/semantic-freshness-v1",
    "policy://memory-influence/semantic-relevance-v1",
    "policy://memory-influence/reviewed-procedural-version-v1",
    "policy://memory-influence/conflict-fail-closed",
    "policy://governance/core-mediated-memory-only",
)
_PRIORITY = {
    source_kind: len(MEMORY_INFLUENCE_PRIORITY) - index
    for index, source_kind in enumerate(MEMORY_INFLUENCE_PRIORITY)
}
_BLOCKED_LIFECYCLES = {"aging", "archived", "expired", "archive_candidate"}
_BLOCKED_REVIEWS = {
    "rejected",
    "revoked",
    "rolled_back",
    "review_recommended",
}
_ELIGIBLE_SEMANTIC_FRESHNESS = {"current", "aging"}
_MIN_SEMANTIC_RELEVANCE = 0.5


def semantic_memory_freshness_status(
    observed_at: str | None,
    generated_at: str | None,
) -> str:
    """Classify bounded semantic freshness from canonical timestamps."""

    observed = _parse_timestamp(observed_at)
    generated = _parse_timestamp(generated_at)
    if observed is None or generated is None:
        return "unknown"
    age_seconds = (generated - observed).total_seconds()
    if age_seconds < -300:
        return "unknown"
    age_days = max(age_seconds, 0.0) / 86_400
    if age_days <= 7:
        return "current"
    if age_days <= 30:
        return "aging"
    return "stale"


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def evaluate_memory_influence_policy(
    *,
    decision_id: str,
    signals: Iterable[MemoryInfluenceSignalContract],
    route: str | None,
    workflow_profile: str | None,
    domain: str | None,
    generated_at: str,
    max_signals: int = 16,
    max_reviewed_procedural: int | None = None,
) -> MemoryInfluencePolicyDecisionContract:
    """Select bounded causal inputs and explain every non-use decision."""

    bounded = list(signals)
    selected_refs: list[str] = []
    ignored_refs: list[str] = []
    conflict_refs: list[str] = []
    use_reasons: dict[str, str] = {}
    non_use_reasons: dict[str, str] = {}
    evidence_refs: list[str] = []
    signal_kinds: dict[str, str] = {}
    freshness_statuses: dict[str, str] = {}
    relevance_scores: dict[str, float] = {}
    version_refs: dict[str, str] = {}
    review_decision_refs: dict[str, str] = {}
    if max_signals < 1 or max_signals > 16:
        max_signals = 16
        non_use_reasons["policy://input"] = "invalid_signal_limit"
    if max_reviewed_procedural is not None and (
        max_reviewed_procedural < 1 or max_reviewed_procedural > max_signals
    ):
        max_reviewed_procedural = 1
        non_use_reasons["policy://reviewed-procedural-input"] = (
            "invalid_reviewed_procedural_limit"
        )
    duplicate_refs = {
        signal_ref
        for signal_ref, count in Counter(
            signal.signal_ref for signal in bounded
        ).items()
        if count > 1
    }
    eligible: list[MemoryInfluenceSignalContract] = []
    for signal in bounded:
        if signal.signal_ref in duplicate_refs:
            ignored_refs.append(signal.signal_ref)
            non_use_reasons[signal.signal_ref] = "duplicate_signal_ref"
            continue
        signal_kinds[signal.signal_ref] = signal.source_kind
        effective_freshness = signal.freshness_status
        freshness_claim_mismatch = False
        if signal.source_kind == "semantic":
            effective_freshness = semantic_memory_freshness_status(
                signal.observed_at,
                generated_at,
            )
            freshness_statuses[signal.signal_ref] = effective_freshness
            freshness_claim_mismatch = (
                signal.freshness_status is not None
                and signal.freshness_status != effective_freshness
            )
        elif signal.freshness_status:
            freshness_statuses[signal.signal_ref] = signal.freshness_status
        if signal.relevance_score is not None:
            relevance_scores[signal.signal_ref] = signal.relevance_score
        if signal.version_ref:
            version_refs[signal.signal_ref] = signal.version_ref
        if signal.review_decision_ref:
            review_decision_refs[signal.signal_ref] = signal.review_decision_ref
        reason = _ineligibility_reason(
            signal,
            route=route,
            workflow_profile=workflow_profile,
            domain=domain,
            effective_freshness=effective_freshness,
        )
        if freshness_claim_mismatch:
            reason = (
                "semantic_freshness_claim_mismatch:"
                f"{signal.freshness_status}:{effective_freshness}"
            )
        if reason:
            ignored_refs.append(signal.signal_ref)
            non_use_reasons[signal.signal_ref] = reason
            continue
        eligible.append(signal)

    selected_by_group: dict[str, MemoryInfluenceSignalContract] = {}
    selected_reviewed_procedural_refs: list[str] = []
    ordered = sorted(
        eligible,
        key=lambda signal: (
            -_PRIORITY[signal.source_kind],
            -(signal.relevance_score if signal.relevance_score is not None else -1.0),
            *_descending_version_key(signal.version_ref),
            signal.signal_ref,
        ),
    )
    for signal in ordered:
        selected = selected_by_group.get(signal.conflict_group)
        if (
            selected is not None
            and signal.source_kind == "procedural"
            and signal.version_ref is not None
        ):
            ignored_refs.append(signal.signal_ref)
            non_use_reasons[signal.signal_ref] = (
                f"superseded_by_newer_version:{selected.signal_ref}"
            )
            if selected.directive != signal.directive:
                conflict_refs.extend([selected.signal_ref, signal.signal_ref])
            continue
        if selected is not None and selected.directive != signal.directive:
            ignored_refs.append(signal.signal_ref)
            conflict_refs.extend([selected.signal_ref, signal.signal_ref])
            non_use_reasons[signal.signal_ref] = (
                f"conflict_with_higher_priority:{selected.signal_ref}"
            )
            continue
        if (
            selected is None
            and max_reviewed_procedural is not None
            and _is_reviewed_procedural(signal)
            and len(selected_reviewed_procedural_refs)
            >= max_reviewed_procedural
        ):
            ignored_refs.append(signal.signal_ref)
            non_use_reasons[signal.signal_ref] = (
                "reviewed_procedural_application_limit_exceeded:"
                f"{selected_reviewed_procedural_refs[0]}"
            )
            continue
        if len(selected_refs) >= max_signals:
            ignored_refs.append(signal.signal_ref)
            non_use_reasons[signal.signal_ref] = "signal_limit_exceeded"
            continue
        selected_by_group.setdefault(signal.conflict_group, signal)
        selected_refs.append(signal.signal_ref)
        if _is_reviewed_procedural(signal):
            selected_reviewed_procedural_refs.append(signal.signal_ref)
        evidence_refs.extend(signal.evidence_refs)
        use_reasons[signal.signal_ref] = (
            f"selected:{signal.source_kind}:priority={_PRIORITY[signal.source_kind]}:"
            f"scope={_scope_reason(signal, route, workflow_profile, domain)}"
            + (
                f":freshness={freshness_statuses[signal.signal_ref]}:"
                f"relevance={signal.relevance_score:.2f}:"
                f"reason={signal.relevance_reason}"
                if signal.source_kind == "semantic"
                and signal.relevance_score is not None
                else ""
            )
            + (
                f":version={signal.version_ref}:"
                f"review={signal.review_decision_ref}"
                if signal.source_kind == "procedural" and signal.version_ref
                else ""
            )
        )

    selected_refs = list(dict.fromkeys(selected_refs))
    ignored_refs = list(dict.fromkeys(ignored_refs))
    conflict_refs = list(dict.fromkeys(conflict_refs))
    evidence_refs = list(dict.fromkeys(evidence_refs))[:100]
    decision_status = (
        "not_applicable"
        if not bounded and not ignored_refs
        else (
            "blocked_no_eligible_signal"
            if not selected_refs
            else (
                "applied_with_conflict_resolution"
                if conflict_refs
                else "applied"
            )
        )
    )
    return MemoryInfluencePolicyDecisionContract(
        decision_id=decision_id,
        decision_status=decision_status,
        route=route,
        workflow_profile=workflow_profile,
        domain=domain,
        selected_refs=selected_refs,
        ignored_refs=ignored_refs,
        priority_order=list(MEMORY_INFLUENCE_PRIORITY),
        conflict_refs=conflict_refs,
        use_reasons=use_reasons,
        non_use_reasons=non_use_reasons,
        evidence_refs=evidence_refs,
        policy_refs=list(MEMORY_INFLUENCE_POLICY_REFS),
        generated_at=generated_at,
        signal_kinds=signal_kinds,
        freshness_statuses=freshness_statuses,
        relevance_scores=relevance_scores,
        version_refs=version_refs,
        review_decision_refs=review_decision_refs,
        execution_allowed=False,
        tool_dispatch_allowed=False,
    )


def _ineligibility_reason(
    signal: MemoryInfluenceSignalContract,
    *,
    route: str | None,
    workflow_profile: str | None,
    domain: str | None,
    effective_freshness: str | None,
) -> str | None:
    if signal.source_kind not in _PRIORITY:
        return "unsupported_source_kind"
    if not signal.signal_ref or len(signal.signal_ref) > 240:
        return "signal_ref_missing_or_unbounded"
    if not signal.summary or len(signal.summary) > 1000:
        return "summary_missing_or_unbounded"
    if not signal.evidence_refs:
        return "evidence_required"
    if len(signal.evidence_refs) > 20 or any(
        not ref or len(ref) > 240 for ref in signal.evidence_refs
    ):
        return "evidence_refs_invalid_or_unbounded"
    if signal.source_kind == "semantic":
        if signal.observed_at is None:
            return "semantic_observed_at_required"
        if effective_freshness not in _ELIGIBLE_SEMANTIC_FRESHNESS:
            return f"freshness_not_eligible:{effective_freshness or 'missing'}"
        if (
            signal.relevance_score is None
            or isinstance(signal.relevance_score, bool)
            or not isinstance(signal.relevance_score, (int, float))
            or not 0 <= signal.relevance_score <= 1
        ):
            return "semantic_relevance_required"
        if signal.relevance_score < _MIN_SEMANTIC_RELEVANCE:
            return "semantic_relevance_below_threshold"
        if not signal.relevance_reason or len(signal.relevance_reason) > 500:
            return "semantic_relevance_reason_missing_or_unbounded"
    if (
        signal.source_kind == "procedural"
        and signal.signal_ref.startswith("playbook-candidate://")
    ):
        return "procedural_human_approval_required"
    reviewed_procedural = _is_reviewed_procedural(signal)
    if reviewed_procedural:
        if signal.review_status in _BLOCKED_REVIEWS:
            return f"review_status_not_eligible:{signal.review_status}"
        if parse_canonical_semver(signal.version_ref) is None:
            return "procedural_version_invalid"
        if signal.review_status != "approved":
            return "procedural_human_approval_required"
        if not signal.review_decision_ref:
            return "procedural_review_decision_required"
    if not signal.conflict_group or not signal.directive:
        return "conflict_contract_required"
    if (
        not signal.read_only
        or signal.memory_write_allowed
        or signal.execution_allowed
        or signal.tool_dispatch_allowed
        or signal.automatic_promotion_allowed
        or signal.core_mutation_allowed
    ):
        return "authority_claim_not_allowed"
    if not {
        "planning_context",
        "sandbox_planning_context",
    }.intersection(signal.allowed_usage):
        return "planning_usage_not_allowed"
    aging_semantic = (
        signal.source_kind == "semantic"
        and signal.lifecycle_status == "aging"
        and effective_freshness == "aging"
    )
    if signal.lifecycle_status in _BLOCKED_LIFECYCLES and not aging_semantic:
        return f"lifecycle_not_eligible:{signal.lifecycle_status}"
    if signal.review_status in _BLOCKED_REVIEWS:
        return f"review_status_not_eligible:{signal.review_status}"
    if signal.source_kind == "reviewed_learning" and signal.review_status not in {
        "approved",
        "sandboxed",
    }:
        return "reviewed_learning_human_review_required"
    if signal.source_kind == "reflection" and signal.review_status not in {
        "candidate",
        "reviewed",
    }:
        return "reflection_status_not_eligible"
    scope_mismatch = _scope_mismatch(signal, route, workflow_profile, domain)
    if scope_mismatch:
        return scope_mismatch
    return None


def _is_reviewed_procedural(signal: MemoryInfluenceSignalContract) -> bool:
    return signal.source_kind == "procedural" and (
        signal.signal_ref.startswith("reviewed-playbook://")
        or signal.version_ref is not None
        or signal.review_decision_ref is not None
    )


def _descending_version_key(version_ref: str | None) -> tuple[int, int, int]:
    parsed = parse_canonical_semver(version_ref)
    if parsed is None:
        return (0, 0, 0)
    major, minor, patch = parsed
    return (-major, -minor, -patch)


def _scope_mismatch(
    signal: MemoryInfluenceSignalContract,
    route: str | None,
    workflow_profile: str | None,
    domain: str | None,
) -> str | None:
    comparisons = (
        ("route", signal.route, route),
        ("workflow", signal.workflow_profile, workflow_profile),
        ("domain", signal.domain, domain),
    )
    for label, signal_value, active_value in comparisons:
        if signal_value and signal_value != active_value:
            return f"scope_mismatch:{label}"
    if not any((signal.route, signal.workflow_profile, signal.domain)):
        return "scope_required"
    return None


def _scope_reason(
    signal: MemoryInfluenceSignalContract,
    route: str | None,
    workflow_profile: str | None,
    domain: str | None,
) -> str:
    matches: list[str] = []
    if signal.route and signal.route == route:
        matches.append("route")
    if signal.workflow_profile and signal.workflow_profile == workflow_profile:
        matches.append("workflow")
    if signal.domain and signal.domain == domain:
        matches.append("domain")
    return "+".join(matches) or "none"
