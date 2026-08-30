from dataclasses import FrozenInstanceError, replace

import pytest

from shared.contracts import (
    WorkflowLifecycleGovernanceAssessmentContract,
    WorkflowLifecycleTransitionContract,
)
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    build_active_workflow_version_registry,
    route_metadata_payload,
    workflow_definition_hash,
)
from shared.schemas import (
    DELIBERATIVE_PLAN_SCHEMA,
    OPERATION_DISPATCH_SCHEMA,
    WORKFLOW_LIFECYCLE_GOVERNANCE_ASSESSMENT_SCHEMA,
    WORKFLOW_LIFECYCLE_TRANSITION_SCHEMA,
)
from shared.workflow_lifecycle import (
    canonical_workflow_lifecycle_payload,
    validate_workflow_lifecycle_governance_assessment,
    validate_workflow_lifecycle_transition,
    validate_workflow_lifecycle_transition_shape,
    workflow_lifecycle_artifact_fingerprint,
    workflow_lifecycle_transition_fingerprint,
)


def _activation() -> WorkflowLifecycleTransitionContract:
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-08-12T10:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    candidate_steps = [*baseline.workflow_steps, "record bounded release evidence"]
    candidate_checkpoints = [
        *baseline.workflow_checkpoints,
        "bounded_release_evidence_recorded",
    ]
    candidate_decisions = [
        *baseline.workflow_decision_points,
        "bounded_release_evidence_gate",
    ]
    candidate_success = [
        *baseline.success_criteria,
        "bounded release evidence remains auditable",
    ]
    candidate_hash = workflow_definition_hash(
        workflow_steps=candidate_steps,
        workflow_checkpoints=candidate_checkpoints,
        workflow_decision_points=candidate_decisions,
        success_criteria=candidate_success,
    )
    return WorkflowLifecycleTransitionContract(
        transition_id="workflow-lifecycle-transition://software-change/1",
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        transition_action="activate_candidate",
        transition_status="active_promoted",
        revision=1,
        previous_transition_id=None,
        previous_transition_fingerprint=None,
        source_registry_ref=baseline.source_registry_ref,
        source_registry_fingerprint=baseline.source_registry_fingerprint,
        baseline_version_ref=baseline.workflow_version_id,
        baseline_definition_hash=baseline.definition_hash,
        candidate_version_ref=(
            f"workflow-version://{baseline.workflow_profile}/1.1.0"
        ),
        candidate_definition_hash=candidate_hash,
        active_version_ref=(
            f"workflow-version://{baseline.workflow_profile}/1.1.0"
        ),
        active_definition_hash=candidate_hash,
        active_workflow_steps=candidate_steps,
        active_workflow_checkpoints=candidate_checkpoints,
        active_workflow_decision_points=candidate_decisions,
        active_success_criteria=candidate_success,
        evolution_proposal_id="evolution-proposal://workflow/software-change/1",
        proposal_fingerprint="1" * 64,
        review_decision_id="evolution-review://workflow/software-change/1",
        review_decision_fingerprint="2" * 64,
        release_checklist_id="release-checklist://workflow/software-change/1",
        release_checklist_fingerprint="3" * 64,
        promotion_gate_id="promotion-gate://workflow/software-change/1",
        promotion_gate_fingerprint="4" * 64,
        workflow_eval_run_id="workflow-eval-run://software-change/1",
        workflow_eval_run_fingerprint="5" * 64,
        rollback_plan_id="workflow-rollback://software-change/1",
        rollback_plan_fingerprint="6" * 64,
        human_authorization_ref="human-authorization://workflow/software-change/1",
        operator_ref="operator://primary",
        evidence_refs=[
            "evolution-proposal://workflow/software-change/1",
            "evolution-review://workflow/software-change/1",
            "release-checklist://workflow/software-change/1",
            "promotion-gate://workflow/software-change/1",
            "workflow-eval-run://software-change/1",
            "workflow-rollback://software-change/1",
            "human-authorization://workflow/software-change/1",
        ],
        completed_test_refs=["test://workflow/software-change/release"],
        failure_refs=[],
        timestamp="2026-08-12T10:30:00Z",
    )


def _rollback(
    activation: WorkflowLifecycleTransitionContract,
) -> WorkflowLifecycleTransitionContract:
    route = RUNTIME_ROUTE_REGISTRY[activation.route]
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-08-12T10:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == activation.workflow_profile
    )
    assert list(route.workflow_steps) == baseline.workflow_steps
    return replace(
        activation,
        transition_id="workflow-lifecycle-transition://software-change/2",
        transition_action="rollback_to_baseline",
        transition_status="baseline_restored",
        revision=2,
        previous_transition_id=activation.transition_id,
        previous_transition_fingerprint=(
            workflow_lifecycle_transition_fingerprint(activation)
        ),
        active_version_ref=activation.baseline_version_ref,
        active_definition_hash=activation.baseline_definition_hash,
        active_workflow_steps=list(baseline.workflow_steps),
        active_workflow_checkpoints=list(baseline.workflow_checkpoints),
        active_workflow_decision_points=list(baseline.workflow_decision_points),
        active_success_criteria=list(baseline.success_criteria),
        human_authorization_ref=(
            "human-authorization://workflow/software-change/rollback/1"
        ),
        evidence_refs=[
            ref
            for ref in activation.evidence_refs
            if ref != activation.human_authorization_ref
        ]
        + ["human-authorization://workflow/software-change/rollback/1"],
        failure_refs=["failure://workflow/software-change/regression/1"],
        timestamp="2026-08-12T11:00:00Z",
    )


def _approved_assessment(
    transition: WorkflowLifecycleTransitionContract,
) -> WorkflowLifecycleGovernanceAssessmentContract:
    return WorkflowLifecycleGovernanceAssessmentContract(
        assessment_id="workflow-lifecycle-assessment://software-change/1",
        transition_id=transition.transition_id,
        transition_action=transition.transition_action,
        transition_fingerprint=workflow_lifecycle_transition_fingerprint(transition),
        status="approved",
        blockers=[],
        conditions=["record through canonical memory only"],
        policy_refs=["policy://workflow-lifecycle/manual-only"],
        timestamp="2026-08-12T10:31:00Z",
        human_authorization_verified=True,
        transition_recording_authorized=True,
    )


def test_workflow_lifecycle_activation_is_frozen_canonical_and_registry_safe() -> None:
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }
    transition = _activation()

    assert validate_workflow_lifecycle_transition(transition) == []
    assert validate_workflow_lifecycle_transition_shape(transition) == []
    assert workflow_lifecycle_transition_fingerprint(transition) == (
        workflow_lifecycle_artifact_fingerprint(transition)
    )
    assert canonical_workflow_lifecycle_payload(transition).startswith("{")
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before
    with pytest.raises(FrozenInstanceError):
        transition.revision = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        (
            {"active_workflow_steps": ["forged step"]},
            "active definition fingerprint mismatch",
        ),
        (
            {"source_registry_fingerprint": "a" * 64},
            "source registry fingerprint drifted",
        ),
        (
            {"runtime_execution_allowed": True},
            "runtime_execution_allowed must be false",
        ),
        (
            {"human_authorized": False},
            "transition authority posture is unsafe",
        ),
        (
            {"human_authorization_ref": "evidence://caller-claimed-human"},
            "human_authorization_ref must be typed",
        ),
        (
            {"operator_ref": "human-authorization://not-an-operator"},
            "operator_ref must be typed",
        ),
        (
            {"failure_refs": ["failure://not-valid-during-activation"]},
            "activation cannot claim failure refs",
        ),
    ],
)
def test_workflow_lifecycle_activation_fails_closed(
    changes: dict[str, object],
    expected: str,
) -> None:
    failures = validate_workflow_lifecycle_transition(
        replace(_activation(), **changes)
    )

    assert any(expected in failure for failure in failures)


def test_workflow_lifecycle_rollback_requires_failure_and_exact_cas_lineage() -> None:
    activation = _activation()
    rollback = _rollback(activation)

    assert validate_workflow_lifecycle_transition(
        rollback,
        current_transition=activation,
    ) == []
    assert validate_workflow_lifecycle_transition_shape(rollback) == []
    assert "previous_transition_required" in validate_workflow_lifecycle_transition(
        rollback
    )[0]
    assert "fingerprint mismatch" in validate_workflow_lifecycle_transition(
        replace(rollback, previous_transition_fingerprint="f" * 64),
        current_transition=activation,
    )[0]
    assert "failure_refs must be a bounded list" in (
        validate_workflow_lifecycle_transition(
            replace(rollback, failure_refs=[]),
            current_transition=activation,
        )[0]
    )


def test_workflow_lifecycle_blocks_direct_replacement_and_double_rollback() -> None:
    activation = _activation()
    direct_replacement = replace(
        activation,
        transition_id="workflow-lifecycle-transition://software-change/2",
        revision=2,
        previous_transition_id=activation.transition_id,
        previous_transition_fingerprint=(
            workflow_lifecycle_transition_fingerprint(activation)
        ),
        timestamp="2026-08-12T11:00:00Z",
    )
    rollback = _rollback(activation)
    second_rollback = replace(
        rollback,
        transition_id="workflow-lifecycle-transition://software-change/3",
        revision=3,
        previous_transition_id=rollback.transition_id,
        previous_transition_fingerprint=(
            workflow_lifecycle_transition_fingerprint(rollback)
        ),
        timestamp="2026-08-12T11:30:00Z",
    )

    assert "activation requires restored baseline" in (
        validate_workflow_lifecycle_transition(
            direct_replacement,
            current_transition=activation,
        )[0]
    )
    assert "rollback requires active candidate" in (
        validate_workflow_lifecycle_transition(
            second_rollback,
            current_transition=rollback,
        )[0]
    )


def test_workflow_lifecycle_assessment_is_bound_and_authority_safe() -> None:
    transition = _activation()
    assessment = _approved_assessment(transition)

    assert validate_workflow_lifecycle_governance_assessment(
        assessment,
        transition=transition,
    ) == []
    forged = replace(assessment, transition_fingerprint="f" * 64)
    assert "binding mismatch" in validate_workflow_lifecycle_governance_assessment(
        forged,
        transition=transition,
    )[0]
    unsafe = replace(assessment, automatic_rollback_allowed=True)
    assert "automatic_rollback_allowed must be false" in (
        validate_workflow_lifecycle_governance_assessment(
            unsafe,
            transition=transition,
        )[0]
    )


def test_workflow_lifecycle_schemas_expose_lineage_and_runtime_provenance() -> None:
    transition_fields = {
        *WORKFLOW_LIFECYCLE_TRANSITION_SCHEMA.required_fields,
        *WORKFLOW_LIFECYCLE_TRANSITION_SCHEMA.optional_fields,
    }
    assessment_fields = {
        *WORKFLOW_LIFECYCLE_GOVERNANCE_ASSESSMENT_SCHEMA.required_fields,
        *WORKFLOW_LIFECYCLE_GOVERNANCE_ASSESSMENT_SCHEMA.optional_fields,
    }

    assert {
        "previous_transition_id",
        "previous_transition_fingerprint",
        "promotion_gate_fingerprint",
        "workflow_eval_run_fingerprint",
        "human_authorized",
        "automatic_rollback_allowed",
    }.issubset(transition_fields)
    assert {
        "transition_fingerprint",
        "human_authorization_verified",
        "transition_recording_authorized",
    }.issubset(assessment_fields)
    assert "workflow_lifecycle_transition" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "workflow_lifecycle_transition" in OPERATION_DISPATCH_SCHEMA.optional_fields
