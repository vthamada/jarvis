from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from json import loads

import pytest

from shared.contracts import (
    DECISION_ATTRIBUTION_CAUSALITY_SCOPE,
    DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS,
    DecisionOutcomeAttributionRecordContract,
)
from shared.decision_attribution import (
    canonical_decision_attribution_payload,
    canonicalize_decision_attribution_record,
    classify_decision_attribution,
    classify_decision_attribution_record,
    decision_attribution_fingerprint,
    validate_decision_attribution_record,
)
from shared.types import MissionId, RequestId, SessionId


def _record(**overrides: object) -> DecisionOutcomeAttributionRecordContract:
    values: dict[str, object] = {
        "attribution_record_id": "decision-attribution://req-1",
        "request_id": RequestId("req-1"),
        "session_id": SessionId("sess-1"),
        "mission_id": MissionId("mission-1"),
        "observed_at": "2026-08-11T12:00:00+00:00",
        "governance_decision_ref": "governance-decision://req-1",
        "governance_decision_status": "allow_with_conditions",
        "workflow_profile": "software_change_workflow",
        "route": "software_engineering",
        "outcome_ref": "experience://mission-1/req-1",
        "outcome_status": "completed",
        "experience_id": "experience://mission-1/req-1",
        "workflow_policy_ref": "workflow-policy://software-change/v1",
        "workflow_policy_version": "1.0.0",
        "workflow_policy_source_registry_ref": "registry://domains/v1",
        "workflow_policy_source_registry_fingerprint": "sha256:registry-v1",
        "workflow_policy_application_status": "applied",
        "workflow_policy_effects": ["success_criteria", "response_focus"],
        "memory_policy_decision_ref": "memory-influence-decision://req-1",
        "memory_policy_status": "applied",
        "memory_policy_refs": ["policy://memory-influence/priority-v1"],
        "memory_selected_refs": ["memory://semantic/anchor-1"],
        "memory_use_reasons": {
            "memory://semantic/anchor-1": "selected:semantic:priority=2"
        },
        "memory_signal_kinds": {"memory://semantic/anchor-1": "semantic"},
        "memory_causal_use_allowed": True,
        "declared_effects_by_ref": {
            "memory://semantic/anchor-1": ["framing", "success_criteria"]
        },
        "evidence_refs": [
            "event://plan-built/req-1",
            "event://response-synthesized/req-1",
        ],
    }
    values.update(overrides)
    return DecisionOutcomeAttributionRecordContract(**values)


def test_classification_distinguishes_declared_causality_per_participant() -> None:
    classification = classify_decision_attribution(
        workflow_policy_ref="workflow-policy://software-change/v1",
        workflow_policy_application_status="applied",
        workflow_policy_effects=["success_criteria"],
        memory_policy_decision_ref="memory-influence-decision://req-1",
        memory_policy_status="applied",
        memory_selected_refs=["memory://semantic/anchor-1"],
        memory_use_reasons={
            "memory://semantic/anchor-1": "selected:semantic:priority=2"
        },
        memory_signal_kinds={"memory://semantic/anchor-1": "semantic"},
        memory_causal_use_allowed=True,
        declared_effects_by_ref={
            "memory://semantic/anchor-1": ["framing"]
        },
        outcome_ref="experience://mission-1/req-1",
        outcome_status="completed",
        evidence_refs=["event://plan-built/req-1"],
    )

    assert classification.attribution_status == "declared_causality"
    assert classification.participating_refs == [
        "workflow-policy://software-change/v1",
        "memory://semantic/anchor-1",
    ]
    assert classification.declared_causal_refs == classification.participating_refs
    assert classification.correlated_refs == []
    assert classification.causality_scope == DECISION_ATTRIBUTION_CAUSALITY_SCOPE
    assert classification.causal_effect_proven is False
    assert classification.gain_claim_status == DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS
    assert classification.promotion_authorized is False
    assert classification.automatic_promotion_allowed is False
    assert classification.core_mutation_allowed is False


def test_classification_keeps_observed_participation_as_correlation_without_effect() -> None:
    classification = classify_decision_attribution(
        memory_policy_decision_ref="memory-influence-decision://req-1",
        memory_policy_status="applied",
        memory_selected_refs=["memory://semantic/anchor-1"],
        memory_use_reasons={"memory://semantic/anchor-1": "selected:semantic"},
        memory_signal_kinds={"memory://semantic/anchor-1": "semantic"},
        memory_causal_use_allowed=False,
        outcome_ref="trace://request/req-1",
        outcome_status="governed",
        evidence_refs=["event://memory-influence/req-1"],
    )

    assert classification.attribution_status == "correlation_only"
    assert classification.declared_causal_refs == []
    assert classification.correlated_refs == ["memory://semantic/anchor-1"]
    assert classification.causal_effect_proven is False
    assert classification.gain_claim_status == "not_established_without_comparator"


def test_record_can_mix_declared_and_correlated_participant_refs() -> None:
    record = _record(
        memory_causal_use_allowed=False,
        declared_effects_by_ref={},
    )

    classification = classify_decision_attribution_record(record)

    assert classification.attribution_status == "declared_causality"
    assert classification.declared_causal_refs == [
        "workflow-policy://software-change/v1"
    ]
    assert classification.correlated_refs == ["memory://semantic/anchor-1"]


def test_applied_policy_without_declared_effect_is_valid_correlation() -> None:
    canonical = canonicalize_decision_attribution_record(
        _record(
            workflow_policy_effects=[],
            memory_causal_use_allowed=False,
            declared_effects_by_ref={},
        )
    )

    validate_decision_attribution_record(canonical)
    assert canonical.attribution_status == "correlation_only"
    assert canonical.declared_causal_refs == []
    assert canonical.correlated_refs == canonical.participating_refs


@pytest.mark.parametrize(
    ("overrides", "expected_limitation"),
    [
        ({"outcome_ref": None}, "outcome_evidence_required"),
        ({"outcome_status": None}, "outcome_evidence_required"),
        ({"outcome_status": "invented"}, "outcome_status_not_canonical"),
        ({"evidence_refs": []}, "attribution_evidence_refs_required"),
        ({"execution_allowed": True}, "authority_claim_not_allowed"),
        (
            {"memory_selected_refs": {"memory://semantic/anchor-1": "selected"}},
            "memory_selected_refs_must_be_a_list",
        ),
        (
            {"memory_use_reasons": {}},
            "memory_use_reason_required:memory://semantic/anchor-1",
        ),
        (
            {"memory_signal_kinds": {}},
            "memory_signal_kind_required:memory://semantic/anchor-1",
        ),
        (
            {"memory_policy_status": "blocked_no_eligible_signal"},
            "memory_policy_status_mismatch_for_selected_memory",
        ),
        (
            {"memory_policy_status": "governance_blocked"},
            "memory_policy_governance_blocked",
        ),
        (
            {"workflow_policy_application_status": "invented"},
            "workflow_policy_application_status_not_canonical",
        ),
        (
            {
                "declared_effects_by_ref": {
                    "memory://semantic/not-selected": ["framing"]
                }
            },
            "declared_effect_for_non_participant:memory://semantic/not-selected",
        ),
    ],
)
def test_classification_fails_closed_for_incomplete_or_unsafe_evidence(
    overrides: dict[str, object],
    expected_limitation: str,
) -> None:
    classification = classify_decision_attribution_record(_record(**overrides))

    assert classification.attribution_status == "insufficient_evidence"
    assert expected_limitation in classification.limitations
    assert classification.declared_causal_refs == []
    assert classification.correlated_refs == classification.participating_refs
    assert classification.causal_effect_proven is False
    assert classification.gain_claim_status == "not_established_without_comparator"


def test_duplicate_participant_refs_fail_closed_instead_of_being_silently_deduped() -> None:
    record = _record(
        memory_selected_refs=[
            "memory://semantic/anchor-1",
            "memory://semantic/anchor-1",
        ]
    )

    classification = classify_decision_attribution_record(record)

    assert classification.attribution_status == "insufficient_evidence"
    assert (
        "memory_selected_ref_duplicate:memory://semantic/anchor-1"
        in classification.limitations
    )


def test_blocked_memory_governance_fails_closed_even_without_selected_memory() -> None:
    classification = classify_decision_attribution(
        workflow_policy_ref="workflow-policy://software-change/v1",
        workflow_policy_application_status="applied",
        workflow_policy_effects=["bounded_plan"],
        memory_policy_decision_ref="memory-influence-decision://req-1",
        memory_policy_status="governance_blocked",
        memory_selected_refs=[],
        outcome_ref="experience://mission-1/req-1",
        outcome_status="governed",
        evidence_refs=["event://memory-influence/req-1"],
    )

    assert classification.attribution_status == "insufficient_evidence"
    assert classification.declared_causal_refs == []
    assert "memory_policy_governance_blocked" in classification.limitations



def test_applied_memory_status_requires_decision_and_selected_refs() -> None:
    classification = classify_decision_attribution(
        workflow_policy_ref="workflow-policy://software-change/v1",
        workflow_policy_application_status="applied",
        workflow_policy_effects=["bounded_plan"],
        memory_policy_status="applied",
        outcome_ref="experience://mission-1/req-1",
        outcome_status="governed",
        evidence_refs=["event://memory-influence/req-1"],
    )

    assert classification.attribution_status == "insufficient_evidence"
    assert classification.declared_causal_refs == []
    assert (
        "memory_policy_decision_ref_required_for_applied_status"
        in classification.limitations
    )
    assert (
        "memory_selected_refs_required_for_applied_status"
        in classification.limitations
    )


def test_canonicalize_and_validate_record_share_one_classification_semantics() -> None:
    canonical = canonicalize_decision_attribution_record(_record())

    validate_decision_attribution_record(canonical)
    assert canonical.attribution_status == "declared_causality"
    assert canonical.declared_causal_refs == [
        "workflow-policy://software-change/v1",
        "memory://semantic/anchor-1",
    ]
    assert canonical.correlated_refs == []

    with pytest.raises(ValueError, match="classification does not match"):
        validate_decision_attribution_record(
            replace(canonical, attribution_status="correlation_only")
        )


def test_validate_record_rejects_authority_even_when_classification_is_fail_closed() -> None:
    unsafe = canonicalize_decision_attribution_record(
        _record(automatic_promotion_allowed=True)
    )

    assert unsafe.attribution_status == "insufficient_evidence"
    with pytest.raises(ValueError, match="authority flags"):
        validate_decision_attribution_record(unsafe)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        (
            {"experience_id": "experience://mission-other/req-1"},
            "does not match request and mission",
        ),
        (
            {"outcome_ref": "experience://mission-1/req-other"},
            "outcome_ref must match experience_id",
        ),
        (
            {"governance_decision_status": "invented"},
            "governance_decision_status is not canonical",
        ),
        (
            {"workflow_policy_version": None},
            "workflow_policy_version is required and canonical",
        ),
        (
            {"workflow_policy_source_registry_fingerprint": None},
            "workflow_policy_source_registry_fingerprint is required and canonical",
        ),
    ],
)
def test_validate_record_binds_identity_and_policy_provenance(
    overrides: dict[str, object],
    message: str,
) -> None:
    record = canonicalize_decision_attribution_record(_record(**overrides))

    with pytest.raises(ValueError, match=message):
        validate_decision_attribution_record(record)


def test_validate_record_requires_runtime_experience_identity() -> None:
    record = canonicalize_decision_attribution_record(
        _record(
            experience_id=None,
            outcome_ref="outcome://unbound",
        )
    )

    with pytest.raises(ValueError, match="experience_id is required"):
        validate_decision_attribution_record(record)


def test_validate_record_requires_reviewed_playbook_version_and_review_ref() -> None:
    ref = "reviewed-playbook://software/safe-change@1.0.0"
    record = canonicalize_decision_attribution_record(
        _record(
            memory_selected_refs=[ref],
            memory_use_reasons={ref: "selected:procedural"},
            memory_signal_kinds={ref: "procedural"},
            declared_effects_by_ref={ref: ["bounded guidance"]},
            memory_version_refs={},
            memory_review_decision_refs={},
        )
    )

    with pytest.raises(ValueError, match="requires canonical version"):
        validate_decision_attribution_record(record)


def test_canonical_payload_and_fingerprint_are_stable_and_round_trippable() -> None:
    canonical = canonicalize_decision_attribution_record(_record())
    payload = canonical_decision_attribution_payload(canonical)
    decoded = loads(payload)
    round_tripped = DecisionOutcomeAttributionRecordContract(**decoded)

    assert round_tripped == canonical
    assert canonical_decision_attribution_payload(round_tripped) == payload
    assert decision_attribution_fingerprint(round_tripped) == (
        decision_attribution_fingerprint(canonical)
    )
    assert decision_attribution_fingerprint(
        replace(canonical, outcome_status="governed")
    ) != decision_attribution_fingerprint(canonical)


def test_decision_attribution_record_is_frozen_and_defaults_to_no_authority() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.outcome_status = "mutated"  # type: ignore[misc]
    assert record.read_only is True
    assert record.immutable is True
    assert record.memory_write_allowed is False
    assert record.execution_allowed is False
    assert record.tool_dispatch_allowed is False
    assert record.promotion_authorized is False
    assert record.automatic_promotion_allowed is False
    assert record.core_mutation_allowed is False
