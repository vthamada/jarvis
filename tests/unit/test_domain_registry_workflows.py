from dataclasses import replace

import pytest

from shared.contracts import WorkflowProfileVersionContract
from shared.domain_registry import (
    ACTIVE_WORKFLOW_MATURITIES,
    RUNTIME_ROUTE_REGISTRY,
    WORKFLOW_VERSION_LIFECYCLE_STATUSES,
    active_workflow_registry_fingerprint,
    build_active_workflow_version_registry,
    register_workflow_candidate_version,
    route_metadata_payload,
    specialist_route_payload,
    workflow_definition_hash,
)


def test_active_runtime_routes_define_workflow_contracts() -> None:
    active_routes = {
        name: entry
        for name, entry in RUNTIME_ROUTE_REGISTRY.items()
        if entry.maturity in {"active_registry", "active_specialist"}
    }

    assert active_routes
    for route_name, entry in active_routes.items():
        assert entry.workflow_profile, route_name
        assert list(entry.workflow_steps), route_name
        assert list(entry.workflow_checkpoints), route_name
        assert list(entry.workflow_decision_points), route_name


def test_specialist_route_payload_preserves_workflow_contracts() -> None:
    payload = specialist_route_payload("strategy")

    assert payload["workflow_profile"] == "strategic_direction_workflow"
    assert payload["workflow_steps"]
    assert payload["workflow_checkpoints"]
    assert payload["workflow_decision_points"]


def workflow_candidate(
    baseline: WorkflowProfileVersionContract,
) -> WorkflowProfileVersionContract:
    steps = [*baseline.workflow_steps, "record bounded candidate evidence"]
    return replace(
        baseline,
        workflow_version_id=(
            f"workflow-version://{baseline.workflow_profile}/1.1.0"
        ),
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=steps,
            workflow_checkpoints=baseline.workflow_checkpoints,
            workflow_decision_points=baseline.workflow_decision_points,
            success_criteria=baseline.success_criteria,
        ),
        workflow_steps=steps,
        evidence_refs=[*baseline.evidence_refs, "pattern://workflow/change-evidence"],
        proposed_tests=["tests/unit/test_domain_registry_workflows.py"],
        rollback_plan_ref=(
            f"rollback://workflow/{baseline.workflow_profile}/{baseline.version}"
        ),
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="add explicit bounded evidence recording",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )


def test_active_workflows_build_deterministic_versioned_baselines() -> None:
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:00:00Z",
        evidence_refs=["evidence://workflow-registry/baseline"],
    )
    expected_profiles = {
        entry.workflow_profile
        for entry in RUNTIME_ROUTE_REGISTRY.values()
        if entry.maturity in ACTIVE_WORKFLOW_MATURITIES and entry.workflow_profile
    }

    assert registry.registry_status == "baseline_snapshot_ready"
    assert registry.workflow_count == len(expected_profiles)
    assert registry.baseline_count == len(expected_profiles)
    assert registry.candidate_count == 0
    assert {version.workflow_profile for version in registry.versions} == (
        expected_profiles
    )
    assert registry.active_registry_fingerprint == (
        active_workflow_registry_fingerprint()
    )
    assert all(version.workflow_steps for version in registry.versions)
    assert all(version.workflow_checkpoints for version in registry.versions)
    assert all(version.workflow_decision_points for version in registry.versions)
    assert all(version.success_criteria for version in registry.versions)
    assert all(version.evidence_refs for version in registry.versions)
    assert all(version.proposed_tests for version in registry.versions)
    assert all(version.rollback_plan_ref for version in registry.versions)
    assert all(
        version.lifecycle_status == "baseline_snapshot"
        for version in registry.versions
    )
    assert registry.active_registry_mutation_allowed is False
    assert "candidate_inactive" in WORKFLOW_VERSION_LIFECYCLE_STATUSES
    assert "promoted_snapshot" in WORKFLOW_VERSION_LIFECYCLE_STATUSES


def test_register_workflow_candidate_is_immutable_idempotent_and_inactive() -> None:
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    candidate = workflow_candidate(baseline)
    active_before = {
        route_name: route_metadata_payload(route_name)
        for route_name in RUNTIME_ROUTE_REGISTRY
    }

    updated = register_workflow_candidate_version(registry, candidate)
    retried = register_workflow_candidate_version(updated, candidate)

    assert registry.candidate_count == 0
    assert len(registry.versions) == registry.baseline_count
    assert updated.workflow_count == registry.workflow_count
    assert updated.candidate_count == 1
    assert updated.registry_status == "candidate_registered_inactive"
    assert updated.versions[-1] == candidate
    assert updated.versions[-1].runtime_binding_status == "inactive_candidate"
    assert updated.versions[-1].runtime_activation_allowed is False
    assert updated.versions[-1].active_registry_write_allowed is False
    assert retried == updated
    assert {
        route_name: route_metadata_payload(route_name)
        for route_name in RUNTIME_ROUTE_REGISTRY
    } == active_before


def test_workflow_candidate_registry_rejects_collision_drift_and_authority() -> None:
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    candidate = workflow_candidate(baseline)
    updated = register_workflow_candidate_version(registry, candidate)

    with pytest.raises(ValueError, match="runtime or mutation authority"):
        register_workflow_candidate_version(
            registry,
            replace(candidate, runtime_activation_allowed=True),
        )
    with pytest.raises(ValueError, match="identity must match"):
        register_workflow_candidate_version(
            registry,
            replace(candidate, workflow_version_id="workflow-version://spoofed"),
        )
    with pytest.raises(ValueError, match="source fingerprint mismatch"):
        register_workflow_candidate_version(
            registry,
            replace(candidate, source_registry_fingerprint="stale"),
        )
    collision_steps = [*candidate.workflow_steps, "mutated collision step"]
    with pytest.raises(ValueError, match="identifiers are immutable"):
        register_workflow_candidate_version(
            updated,
            replace(
                candidate,
                workflow_steps=collision_steps,
                definition_hash=workflow_definition_hash(
                    workflow_steps=collision_steps,
                    workflow_checkpoints=candidate.workflow_checkpoints,
                    workflow_decision_points=candidate.workflow_decision_points,
                    success_criteria=candidate.success_criteria,
                ),
            ),
        )
    with pytest.raises(ValueError, match="must change the baseline"):
        register_workflow_candidate_version(
            registry,
            replace(
                candidate,
                definition_hash=baseline.definition_hash,
                workflow_steps=list(baseline.workflow_steps),
            ),
        )
