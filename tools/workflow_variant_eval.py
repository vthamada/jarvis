"""Controlled paired evaluation for versioned workflow candidates."""

from __future__ import annotations

from evolution_lab.service import EvolutionLabService
from observability_service.service import ObservabilityService

from shared.contracts import (
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalCaseResultContract,
    WorkflowVariantEvalRunContract,
)
from shared.domain_registry import (
    active_workflow_registry_fingerprint,
    workflow_definition_hash,
)
from shared.workflow_variant_eval import (
    derive_workflow_variant_eval_case_checks,
    derive_workflow_variant_eval_metric_deltas,
    derive_workflow_variant_eval_metrics,
    validate_workflow_variant_eval_case_pack,
    workflow_variant_eval_case_pack_fingerprint,
    workflow_variant_eval_control_fingerprint,
)


def run_workflow_variant_eval(
    *,
    service: EvolutionLabService,
    registry: WorkflowProfileVersionRegistryContract,
    case_pack: WorkflowVariantEvalCasePackContract,
    run_id: str,
    generated_at: str,
    minimum_pass_rate: float = 1.0,
) -> WorkflowVariantEvalRunContract:
    """Validate, compare and persist paired sandbox observations without execution."""

    blockers = [
        *_registry_blockers(registry),
        *validate_workflow_variant_eval_case_pack(case_pack),
    ]
    baseline = _version_by_ref(registry, case_pack.baseline_version_ref)
    candidate = _version_by_ref(registry, case_pack.candidate_version_ref)
    if baseline is None:
        blockers.append("workflow_eval_baseline_not_registered")
    if candidate is None:
        blockers.append("workflow_eval_candidate_not_registered")
    if baseline is not None and candidate is not None:
        blockers.extend(
            _version_pair_blockers(
                registry=registry,
                baseline=baseline,
                candidate=candidate,
            )
        )
        blockers.extend(
            _case_pack_pair_blockers(
                registry=registry,
                case_pack=case_pack,
                baseline=baseline,
                candidate=candidate,
            )
        )

    pack_fingerprint = workflow_variant_eval_case_pack_fingerprint(case_pack)
    service.register_workflow_variant_case_pack(case_pack, registry=registry)
    definition_hashes = [
        baseline.definition_hash if baseline is not None else "missing",
        candidate.definition_hash if candidate is not None else "missing",
    ]
    claim_created = service.claim_workflow_variant_eval_run(
        run_id=run_id,
        input_fingerprint=service.workflow_variant_eval_input_fingerprint(case_pack),
        baseline_version_ref=case_pack.baseline_version_ref,
        baseline_definition_hash=definition_hashes[0],
        candidate_version_ref=case_pack.candidate_version_ref,
        candidate_definition_hash=definition_hashes[1],
        case_pack_id=case_pack.case_pack_id,
        case_pack_version=case_pack.case_pack_version,
        case_pack_fingerprint=pack_fingerprint,
        control_fingerprint=service.workflow_variant_eval_control_fingerprint(case_pack),
        claimed_at=generated_at,
    )
    if not claim_created:
        existing = service.get_workflow_variant_eval_run(run_id)
        if existing is not None:
            return existing

    results = (
        [
            _evaluate_case(
                case=case,
                case_pack=case_pack,
                baseline=baseline,
                candidate=candidate,
            )
            for case in case_pack.cases
        ]
        if baseline is not None and candidate is not None
        else []
    )
    evidence_refs = list(
        dict.fromkeys(
            [
                registry.registry_id,
                case_pack.case_pack_id,
                case_pack.baseline_version_ref,
                case_pack.candidate_version_ref,
                *registry.evidence_refs,
                *case_pack.evidence_refs,
                *(reference for result in results for reference in result.evidence_refs),
            ]
        )
    )[:100]
    run = ObservabilityService.build_workflow_variant_eval_run(
        run_id=run_id,
        case_pack=case_pack,
        case_results=results,
        minimum_pass_rate=minimum_pass_rate,
        evidence_refs=evidence_refs,
        generated_at=generated_at,
        blockers=sorted(set(blockers)),
    )
    return service.record_workflow_variant_eval_run(run)


def _evaluate_case(
    *,
    case: WorkflowVariantEvalCaseContract,
    case_pack: WorkflowVariantEvalCasePackContract,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
) -> WorkflowVariantEvalCaseResultContract:
    control_fingerprint = workflow_variant_eval_control_fingerprint(case.control_snapshot)
    baseline_metrics = derive_workflow_variant_eval_metrics(
        case.baseline_observation,
        checkpoint_refs=baseline.workflow_checkpoints,
    )
    candidate_metrics = derive_workflow_variant_eval_metrics(
        case.candidate_observation,
        checkpoint_refs=candidate.workflow_checkpoints,
    )
    deltas = derive_workflow_variant_eval_metric_deltas(
        baseline_metrics,
        candidate_metrics,
    )
    regressions = [
        f"{metric}_regressed"
        for metric, delta in deltas.items()
        if (metric == "rework_rate" and delta > 0.0) or (metric != "rework_rate" and delta < 0.0)
    ]
    improvements = [
        f"{metric}_improved"
        for metric, delta in deltas.items()
        if (metric == "rework_rate" and delta < 0.0) or (metric != "rework_rate" and delta > 0.0)
    ]
    checks = derive_workflow_variant_eval_case_checks(
        case,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
    )
    failures = [name for name, passed in checks.items() if not passed]
    limitations = sorted(
        set(
            [
                *case.limitations,
                *case.baseline_observation.limitations,
                *case.candidate_observation.limitations,
            ]
        )
    )
    evidence_refs = list(
        dict.fromkeys(
            [
                case.scenario_ref,
                case.baseline_observation.outcome_ref,
                case.candidate_observation.outcome_ref,
                *case.evidence_refs,
                *case.baseline_observation.evidence_refs,
                *case.candidate_observation.evidence_refs,
            ]
        )
    )[:50]
    return WorkflowVariantEvalCaseResultContract(
        case_pack_id=case.case_pack_id,
        case_pack_version=case.case_pack_version,
        case_pack_fingerprint=workflow_variant_eval_case_pack_fingerprint(case_pack),
        case_id=case.case_id,
        case_version=case.case_version,
        scenario_ref=case.scenario_ref,
        input_snapshot_fingerprint=case.input_snapshot_fingerprint,
        workflow_profile=case.workflow_profile,
        route=case.route,
        baseline_version_ref=case.baseline_version_ref,
        candidate_version_ref=case.candidate_version_ref,
        baseline_definition_hash=baseline.definition_hash,
        candidate_definition_hash=candidate.definition_hash,
        control_snapshot_id=case.control_snapshot.control_snapshot_id,
        control_snapshot_fingerprint=control_fingerprint,
        baseline_outcome_ref=case.baseline_observation.outcome_ref,
        candidate_outcome_ref=case.candidate_observation.outcome_ref,
        baseline_outcome_status=case.baseline_observation.outcome_status,
        candidate_outcome_status=case.candidate_observation.outcome_status,
        passed=bool(improvements) and not (failures or regressions or limitations),
        checks=checks,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        metric_deltas=deltas,
        improvement_signals=improvements,
        regression_flags=regressions,
        failures=failures,
        limitations=limitations,
        evidence_refs=evidence_refs,
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
        version for version in registry.versions if version.workflow_version_id == version_ref
    ]
    return matches[0] if len(matches) == 1 else None


def _version_pair_blockers(
    *,
    registry: WorkflowProfileVersionRegistryContract,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
) -> list[str]:
    blockers: list[str] = []
    expected_baseline_hash = workflow_definition_hash(
        workflow_steps=baseline.workflow_steps,
        workflow_checkpoints=baseline.workflow_checkpoints,
        workflow_decision_points=baseline.workflow_decision_points,
        success_criteria=baseline.success_criteria,
    )
    expected_candidate_hash = workflow_definition_hash(
        workflow_steps=candidate.workflow_steps,
        workflow_checkpoints=candidate.workflow_checkpoints,
        workflow_decision_points=candidate.workflow_decision_points,
        success_criteria=candidate.success_criteria,
    )
    if baseline.definition_hash != expected_baseline_hash:
        blockers.append("workflow_eval_baseline_definition_hash_mismatch")
    if candidate.definition_hash != expected_candidate_hash:
        blockers.append("workflow_eval_candidate_definition_hash_mismatch")
    if baseline.lifecycle_status != "baseline_snapshot":
        blockers.append("workflow_eval_baseline_snapshot_required")
    if candidate.lifecycle_status != "candidate_inactive":
        blockers.append("workflow_eval_inactive_candidate_required")
    if candidate.runtime_binding_status != "inactive_candidate":
        blockers.append("workflow_eval_inactive_candidate_binding_required")
    if candidate.review_status != "needs_review":
        blockers.append("workflow_eval_candidate_review_status_mismatch")
    if not candidate.human_review_required:
        blockers.append("workflow_eval_candidate_human_review_required")
    if not candidate.sandbox_required:
        blockers.append("workflow_eval_candidate_sandbox_required")
    if candidate.blockers:
        blockers.append("workflow_eval_candidate_blocked")
    if candidate.baseline_version_ref != baseline.workflow_version_id:
        blockers.append("workflow_eval_candidate_baseline_mismatch")
    if (
        baseline.workflow_profile != candidate.workflow_profile
        or baseline.route != candidate.route
    ):
        blockers.append("workflow_eval_version_scope_mismatch")
    if candidate.definition_hash == baseline.definition_hash:
        blockers.append("workflow_eval_distinct_definition_required")
    if (
        baseline.source_registry_ref != registry.active_registry_ref
        or baseline.source_registry_fingerprint != registry.active_registry_fingerprint
    ):
        blockers.append("workflow_eval_baseline_registry_provenance_mismatch")
    if (
        candidate.source_registry_ref != registry.active_registry_ref
        or candidate.source_registry_fingerprint != registry.active_registry_fingerprint
        or candidate.source_registry_ref != baseline.source_registry_ref
        or candidate.source_registry_fingerprint != baseline.source_registry_fingerprint
    ):
        blockers.append("workflow_eval_candidate_registry_provenance_mismatch")
    if not set(candidate.evidence_refs).issubset(registry.evidence_refs):
        blockers.append("workflow_eval_candidate_registry_evidence_mismatch")
    if (
        not candidate.evidence_refs
        or len(candidate.evidence_refs) > 50
        or any(
            not isinstance(reference, str)
            or not reference.strip()
            or len(reference) > 500
            for reference in candidate.evidence_refs
        )
    ):
        blockers.append("workflow_eval_candidate_evidence_required")
    if not any(
        reference.startswith("recurring-pattern://")
        for reference in candidate.evidence_refs
    ):
        blockers.append("workflow_eval_candidate_pattern_evidence_required")
    if not any(
        reference.startswith("review-decision://")
        for reference in candidate.evidence_refs
    ):
        blockers.append("workflow_eval_candidate_review_evidence_required")
    if (
        not candidate.proposed_tests
        or len(candidate.proposed_tests) > 50
        or any(
            not isinstance(test_ref, str)
            or not test_ref.strip()
            or len(test_ref) > 500
            for test_ref in candidate.proposed_tests
        )
    ):
        blockers.append("workflow_eval_candidate_tests_required")
    if (
        not isinstance(candidate.rollback_plan_ref, str)
        or not candidate.rollback_plan_ref.strip()
        or len(candidate.rollback_plan_ref) > 500
    ):
        blockers.append("workflow_eval_candidate_rollback_required")
    if (
        candidate.active_registry_write_allowed
        or candidate.runtime_activation_allowed
        or candidate.automatic_promotion_allowed
        or candidate.core_mutation_allowed
    ):
        blockers.append("workflow_eval_candidate_authority_claim_not_allowed")
    return blockers


def _case_pack_pair_blockers(
    *,
    registry: WorkflowProfileVersionRegistryContract,
    case_pack: WorkflowVariantEvalCasePackContract,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
) -> list[str]:
    """Bind every case source snapshot to the exact registered version pair."""

    blockers: list[str] = []
    if (
        case_pack.baseline_version_ref != baseline.workflow_version_id
        or case_pack.candidate_version_ref != candidate.workflow_version_id
    ):
        blockers.append("workflow_eval_case_pack_version_refs_mismatch")
    if (
        case_pack.workflow_profile != baseline.workflow_profile
        or case_pack.workflow_profile != candidate.workflow_profile
        or case_pack.route != baseline.route
        or case_pack.route != candidate.route
    ):
        blockers.append("workflow_eval_case_pack_scope_mismatch")

    expected_versions = (
        ("baseline", baseline),
        ("candidate", candidate),
    )
    for case in case_pack.cases:
        if (
            case.control_snapshot.workflow_policy_source_registry_ref
            != registry.active_registry_ref
            or case.control_snapshot.workflow_policy_source_registry_fingerprint
            != registry.active_registry_fingerprint
        ):
            blockers.append(
                f"case:{case.case_id}:{case.case_version}:"
                "workflow_policy_registry_mismatch"
            )
        for arm, version in expected_versions:
            observation = getattr(case, f"{arm}_observation")
            if observation.workflow_version_ref != version.workflow_version_id:
                blockers.append(
                    f"case:{case.case_id}:{case.case_version}:{arm}_version_ref_mismatch"
                )
            if (
                observation.definition_hash != version.definition_hash
                or observation.expected_workflow_steps != version.workflow_steps
                or observation.expected_checkpoint_refs != version.workflow_checkpoints
                or observation.expected_decision_points
                != version.workflow_decision_points
                or observation.expected_success_criteria != version.success_criteria
            ):
                blockers.append(
                    f"case:{case.case_id}:{case.case_version}:"
                    f"{arm}_definition_snapshot_mismatch"
                )
    return blockers
