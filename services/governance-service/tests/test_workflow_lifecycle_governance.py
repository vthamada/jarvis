from dataclasses import replace

from governance_service.service import GovernanceService

from shared.workflow_lifecycle import (
    validate_workflow_lifecycle_governance_assessment,
)
from tests.unit.test_workflow_lifecycle import _activation, _rollback


def test_governance_approves_human_activation_for_append_only_recording_only() -> None:
    transition = _activation()

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at="2026-08-12T10:31:00Z",
    )

    assert assessment.status == "approved"
    assert assessment.human_authorization_verified is True
    assert assessment.transition_recording_authorized is True
    assert assessment.memory_write_mode == "through_core_only"
    assert assessment.active_registry_write_allowed is False
    assert assessment.runtime_execution_allowed is False
    assert assessment.automatic_promotion_allowed is False
    assert assessment.automatic_rollback_allowed is False
    assert assessment.core_mutation_allowed is False
    assert validate_workflow_lifecycle_governance_assessment(
        assessment,
        transition=transition,
    ) == []


def test_governance_approves_explicit_rollback_with_exact_current_lineage() -> None:
    activation = _activation()
    rollback = _rollback(activation)

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        rollback,
        current_transition=activation,
        release_bundle_verifier=lambda candidate: candidate == rollback,
        assessed_at="2026-08-12T11:01:00Z",
    )

    assert assessment.status == "approved"
    assert assessment.transition_recording_authorized is True
    assert validate_workflow_lifecycle_governance_assessment(
        assessment,
        transition=rollback,
        current_transition=activation,
    ) == []


def test_governance_blocks_rollback_without_current_or_failure_evidence() -> None:
    activation = _activation()
    rollback = replace(_rollback(activation), failure_refs=[])

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        rollback,
        release_bundle_verifier=lambda candidate: candidate == rollback,
        assessed_at="2026-08-12T11:01:00Z",
    )

    assert assessment.status == "blocked"
    assert assessment.human_authorization_verified is False
    assert assessment.transition_recording_authorized is False
    assert assessment.blockers


def test_governance_blocks_static_registry_write_or_automatic_rollback_claim() -> None:
    transition = replace(
        _activation(),
        active_registry_write_allowed=True,
        automatic_rollback_allowed=True,
    )

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at="2026-08-12T10:31:00Z",
    )

    assert assessment.status == "blocked"
    assert assessment.transition_recording_authorized is False
    assert any("active_registry_write_allowed" in item for item in assessment.blockers)


def test_governance_blocks_assessment_that_claims_to_predate_transition() -> None:
    transition = _activation()

    assessment = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        release_bundle_verifier=lambda candidate: candidate == transition,
        assessed_at="2026-08-12T10:29:59Z",
    )

    assert assessment.status == "blocked"
    assert assessment.timestamp == transition.timestamp
    assert "workflow_lifecycle_assessment_time_invalid" in assessment.blockers
    assert assessment.transition_recording_authorized is False


def test_governance_blocks_structural_transition_without_persisted_release_bundle() -> None:
    transition = _activation()

    missing_verifier = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        assessed_at="2026-08-12T10:31:00Z",
    )
    rejected_bundle = GovernanceService().assess_workflow_lifecycle_transition(
        transition,
        release_bundle_verifier=lambda _candidate: False,
        assessed_at="2026-08-12T10:31:00Z",
    )

    for assessment in (missing_verifier, rejected_bundle):
        assert assessment.status == "blocked"
        assert assessment.human_authorization_verified is False
        assert assessment.transition_recording_authorized is False
        assert "workflow_lifecycle_release_bundle_not_verified" in assessment.blockers
