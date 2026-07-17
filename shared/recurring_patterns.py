"""Bounded recurring-pattern evidence derived from canonical learning records."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256

from shared.contracts import (
    ExperienceRecordContract,
    PostTaskReflectionContract,
    RecurringPatternEvidenceContract,
    RecurringPatternReportContract,
)

SUCCESS_OUTCOMES = frozenset({"completed", "success", "succeeded"})
UNSCOPED = "unscoped"


def build_recurring_pattern_report(
    *,
    report_id: str,
    experiences: list[ExperienceRecordContract],
    reflections: list[PostTaskReflectionContract] | None,
    minimum_occurrences: int,
    generated_at: str,
    workflow_profile: str | None = None,
    route: str | None = None,
    domain: str | None = None,
    max_records: int = 100,
    max_patterns: int = 20,
) -> RecurringPatternReportContract:
    """Aggregate compatible recurrence without granting evolution authority."""

    if minimum_occurrences < 2:
        raise ValueError("recurring patterns require at least two occurrences")
    if not 1 <= max_records <= 500:
        raise ValueError("max_records must be between 1 and 500")
    if not 1 <= max_patterns <= 100:
        raise ValueError("max_patterns must be between 1 and 100")

    unique_experiences = _deduplicate_experiences(experiences)
    filtered = [
        experience
        for experience in unique_experiences
        if _matches_scope(
            experience,
            workflow_profile=workflow_profile,
            route=route,
            domain=domain,
        )
    ]
    sample_truncated = len(filtered) > max_records
    sampled = filtered[:max_records]
    reflection_by_experience = {
        reflection.experience_id: reflection
        for reflection in reflections or []
        if reflection.experience_id
    }

    groups: dict[tuple[str, str, str], list[ExperienceRecordContract]] = defaultdict(list)
    for experience in sampled:
        groups[_scope_key(experience)].append(experience)

    compatible_groups = [
        (scope, records)
        for scope, records in groups.items()
        if len(records) >= minimum_occurrences
    ]
    compatible_groups.sort(key=lambda item: (-len(item[1]), item[0]))
    patterns = [
        _build_pattern(
            scope=scope,
            records=records,
            reflection_by_experience=reflection_by_experience,
            minimum_occurrences=minimum_occurrences,
            generated_at=generated_at,
        )
        for scope, records in compatible_groups[:max_patterns]
    ]
    eligible_count = sum(
        pattern.pattern_status == "evidence_ready_for_human_review"
        for pattern in patterns
    )
    if eligible_count:
        report_status = "evidence_ready_for_human_review"
        blockers: list[str] = []
    elif patterns:
        report_status = "attention_required"
        blockers = ["no_eligible_recurring_pattern"]
    else:
        report_status = "insufficient_evidence"
        blockers = [
            "no_experience_records" if not sampled else "no_compatible_recurring_pattern"
        ]

    evidence_refs = _unique(
        reference
        for pattern in patterns
        for reference in pattern.evidence_refs
    )[:200]
    return RecurringPatternReportContract(
        report_id=report_id,
        report_status=report_status,
        records_analyzed=len(sampled),
        compatible_group_count=len(compatible_groups),
        eligible_pattern_count=eligible_count,
        minimum_occurrences=minimum_occurrences,
        scope_filters={
            key: value
            for key, value in (
                ("workflow_profile", workflow_profile),
                ("route", route),
                ("domain", domain),
            )
            if value
        },
        patterns=patterns,
        evidence_refs=evidence_refs,
        blockers=blockers,
        generated_at=generated_at,
        sample_truncated=sample_truncated,
    )


def _build_pattern(
    *,
    scope: tuple[str, str, str],
    records: list[ExperienceRecordContract],
    reflection_by_experience: dict[str, PostTaskReflectionContract],
    minimum_occurrences: int,
    generated_at: str,
) -> RecurringPatternEvidenceContract:
    workflow_profile, route, domain = scope
    outcomes = Counter(_normalized(experience.outcome_status) for experience in records)
    successful = sum(outcomes[outcome] for outcome in SUCCESS_OUTCOMES)
    non_successful = len(records) - successful
    feedback_refs = _unique(
        reference
        for experience in records
        for reference in (*experience.evidence_refs, *experience.signal_refs)
        if reference.startswith("operator-feedback://")
        and "/assessment/" not in reference
    )
    correction_count = sum(
        _has_operator_correction(experience) for experience in records
    )
    recurring_signals = _recurring_signals(records)
    reflection_refs = _unique(
        reflection.reflection_id
        for experience in records
        if (reflection := reflection_by_experience.get(experience.experience_id))
    )
    evidence_refs = _unique(
        reference
        for experience in records
        for reference in (
            experience.experience_id,
            *experience.evidence_refs,
            *experience.signal_refs,
        )
    )
    evidence_refs = _unique(
        [
            *evidence_refs,
            *reflection_refs,
            *(
                reference
                for experience in records
                if (reflection := reflection_by_experience.get(experience.experience_id))
                for reference in reflection.evidence_refs
            ),
        ]
    )[:100]

    conflict_flags: list[str] = []
    blockers: list[str] = []
    scope_complete = UNSCOPED not in scope
    if not scope_complete:
        blockers.append("compatible_scope_incomplete")
    if successful and non_successful:
        conflict_flags.append("mixed_outcomes")
        blockers.append("outcome_conflict_requires_review")
    if not successful:
        blockers.append("successful_outcome_required")

    if correction_count >= minimum_occurrences:
        pattern_type = "recurring_operator_correction"
    elif successful == len(records):
        pattern_type = "repeated_successful_workflow"
    elif successful:
        pattern_type = "mixed_workflow_outcomes"
    else:
        pattern_type = "repeated_non_successful_workflow"

    if not blockers:
        pattern_status = "evidence_ready_for_human_review"
        confidence_status = (
            "bounded_high" if len(records) >= 3 else "bounded_moderate"
        )
    elif conflict_flags:
        pattern_status = "conflict_detected"
        confidence_status = "insufficient_due_to_conflict"
    else:
        pattern_status = "attention_required"
        confidence_status = "insufficient"

    outcome_summary = "; ".join(
        f"{outcome}={count}" for outcome, count in sorted(outcomes.items())
    )
    scope_text = f"workflow={workflow_profile}; route={route}; domain={domain}"
    pattern_seed = f"{scope_text}; type={pattern_type}"
    pattern_id = f"recurring-pattern://{sha256(pattern_seed.encode()).hexdigest()[:16]}"
    pattern_summary = (
        f"{scope_text}; occurrences={len(records)}; outcomes={outcome_summary}; "
        f"corrections={correction_count}; status={pattern_status}"
    )
    return RecurringPatternEvidenceContract(
        pattern_id=pattern_id,
        pattern_type=pattern_type,
        pattern_status=pattern_status,
        workflow_profile=workflow_profile,
        route=route,
        domain=domain,
        occurrence_count=len(records),
        minimum_occurrences=minimum_occurrences,
        successful_occurrences=successful,
        non_successful_occurrences=non_successful,
        confidence_status=confidence_status,
        outcome_summary=outcome_summary,
        pattern_summary=pattern_summary,
        experience_refs=[experience.experience_id for experience in records],
        reflection_refs=reflection_refs,
        feedback_refs=feedback_refs,
        evidence_refs=evidence_refs,
        recurring_signals=recurring_signals,
        conflict_flags=conflict_flags,
        blockers=blockers,
        generated_at=generated_at,
    )


def _deduplicate_experiences(
    experiences: list[ExperienceRecordContract],
) -> list[ExperienceRecordContract]:
    deduplicated: list[ExperienceRecordContract] = []
    seen: set[str] = set()
    for experience in experiences:
        if experience.experience_id in seen:
            continue
        seen.add(experience.experience_id)
        deduplicated.append(experience)
    return deduplicated


def _matches_scope(
    experience: ExperienceRecordContract,
    *,
    workflow_profile: str | None,
    route: str | None,
    domain: str | None,
) -> bool:
    return (
        (not workflow_profile or experience.workflow_profile == workflow_profile)
        and (not route or experience.route == route)
        and (not domain or experience.primary_domain_driver == domain)
    )


def _scope_key(experience: ExperienceRecordContract) -> tuple[str, str, str]:
    return (
        _normalized(experience.workflow_profile) or UNSCOPED,
        _normalized(experience.route) or UNSCOPED,
        _normalized(experience.primary_domain_driver) or UNSCOPED,
    )


def _recurring_signals(records: list[ExperienceRecordContract]) -> list[str]:
    signal_sets = [
        set(_unique([*record.learned_patterns, *record.checkpoints]))
        for record in records
    ]
    if not signal_sets:
        return []
    return sorted(set.intersection(*signal_sets))[:20]


def _has_operator_correction(experience: ExperienceRecordContract) -> bool:
    return (
        "operator-feedback://assessment/correction" in experience.signal_refs
        or "assessment=correction" in (experience.user_feedback or "")
    )


def _normalized(value: object | None) -> str:
    return str(value or "").strip().lower()


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value).strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result
