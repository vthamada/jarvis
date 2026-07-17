"""Governed offline comparison for versioned workflow candidates."""

from __future__ import annotations

from evolution_lab.service import EvolutionLabService
from observability_service.service import ObservabilityService

from shared.contracts import (
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalRunContract,
)
from shared.domain_registry import active_workflow_registry_fingerprint


def run_workflow_variant_eval(
    *,
    registry: WorkflowProfileVersionRegistryContract,
    baseline_version_ref: str,
    candidate_version_ref: str,
    cases: list[WorkflowVariantEvalCaseContract],
    run_id: str,
    generated_at: str,
    minimum_pass_rate: float = 1.0,
) -> WorkflowVariantEvalRunContract:
    """Compare equivalent case evidence without activating the candidate."""

    blockers = _registry_blockers(registry)
    baseline = _version_by_ref(registry, baseline_version_ref)
    candidate = _version_by_ref(registry, candidate_version_ref)
    if baseline is None:
        blockers.append("workflow_eval_baseline_not_registered")
    if candidate is None:
        blockers.append("workflow_eval_candidate_not_registered")
    if baseline is not None and candidate is not None:
        blockers.extend(_version_pair_blockers(baseline, candidate))
    if len(cases) > 32:
        blockers.append("workflow_eval_case_limit_exceeded")
    case_ids = [case.case_id for case in cases]
    if len(case_ids) != len(set(case_ids)):
        blockers.append("duplicate_workflow_eval_case_id")
    scenario_refs = [case.scenario_ref for case in cases]
    if len(scenario_refs) != len(set(scenario_refs)):
        blockers.append("duplicate_workflow_eval_scenario_ref")

    case_results = (
        [
            EvolutionLabService.evaluate_workflow_variant_case(
                baseline=baseline,
                candidate=candidate,
                case=case,
            )
            for case in cases
        ]
        if baseline is not None and candidate is not None
        else []
    )
    workflow_profile = (
        candidate.workflow_profile
        if candidate is not None
        else baseline.workflow_profile if baseline is not None else "unknown"
    )
    route = (
        candidate.route
        if candidate is not None
        else baseline.route if baseline is not None else "unknown"
    )
    evidence_refs = list(
        dict.fromkeys(
            [
                registry.registry_id,
                baseline_version_ref,
                candidate_version_ref,
                *registry.evidence_refs,
                *(reference for case in cases for reference in case.evidence_refs),
                *(reference for result in case_results for reference in result.evidence_refs),
            ]
        )
    )[:100]
    return ObservabilityService.build_workflow_variant_eval_run(
        run_id=run_id,
        workflow_profile=workflow_profile,
        route=route,
        baseline_version_ref=baseline_version_ref,
        candidate_version_ref=candidate_version_ref,
        case_results=case_results,
        minimum_pass_rate=minimum_pass_rate,
        evidence_refs=evidence_refs,
        generated_at=generated_at,
        blockers=sorted(set(blockers)),
    )


def _registry_blockers(
    registry: WorkflowProfileVersionRegistryContract,
) -> list[str]:
    blockers = list(registry.blockers)
    if registry.active_registry_fingerprint != active_workflow_registry_fingerprint():
        blockers.append("active_workflow_registry_drift")
    if registry.registry_status != "candidate_registered_inactive":
        blockers.append("inactive_workflow_candidate_registry_required")
    if registry.candidate_count < 1:
        blockers.append("registered_workflow_candidate_required")
    if (
        registry.active_registry_mutation_allowed
        or registry.runtime_activation_allowed
        or registry.automatic_promotion_allowed
        or registry.core_mutation_allowed
    ):
        blockers.append("workflow_eval_registry_authority_claim_not_allowed")
    return blockers


def _version_by_ref(
    registry: WorkflowProfileVersionRegistryContract,
    version_ref: str,
) -> WorkflowProfileVersionContract | None:
    matches = [
        version
        for version in registry.versions
        if version.workflow_version_id == version_ref
    ]
    return matches[0] if len(matches) == 1 else None


def _version_pair_blockers(
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
) -> list[str]:
    blockers: list[str] = []
    if baseline.lifecycle_status != "baseline_snapshot":
        blockers.append("workflow_eval_baseline_snapshot_required")
    if candidate.lifecycle_status != "candidate_inactive":
        blockers.append("workflow_eval_inactive_candidate_required")
    if candidate.baseline_version_ref != baseline.workflow_version_id:
        blockers.append("workflow_eval_candidate_baseline_mismatch")
    if (
        baseline.workflow_profile != candidate.workflow_profile
        or baseline.route != candidate.route
    ):
        blockers.append("workflow_eval_version_scope_mismatch")
    if candidate.definition_hash == baseline.definition_hash:
        blockers.append("workflow_eval_distinct_definition_required")
    if not any(
        reference.startswith("recurring-pattern://")
        for reference in candidate.evidence_refs
    ):
        blockers.append("workflow_eval_pattern_evidence_required")
    if not any(
        reference.startswith("review-decision://")
        for reference in candidate.evidence_refs
    ):
        blockers.append("workflow_eval_review_evidence_required")
    if (
        candidate.active_registry_write_allowed
        or candidate.runtime_activation_allowed
        or candidate.automatic_promotion_allowed
        or candidate.core_mutation_allowed
    ):
        blockers.append("workflow_eval_candidate_authority_claim_not_allowed")
    return blockers
