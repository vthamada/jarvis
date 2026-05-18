from shared.technology_absorption import derive_technology_absorption_state


def test_reference_candidate_stays_reference_only() -> None:
    state = derive_technology_absorption_state(
        absorption_class="reference",
        candidate_status="observed",
        requested_core_role="reference",
    )

    assert state["absorption_decision"] == "hold_as_reference"
    assert state["promotion_readiness"] == "not_applicable"
    assert state["requires_sandbox"] is False


def test_candidate_cannot_request_core_brain_role() -> None:
    state = derive_technology_absorption_state(
        absorption_class="sandbox_experiment",
        candidate_status="candidate",
        requested_core_role="core_brain",
        evidence_refs=["evidence://trace"],
        proposed_tests=["pytest tests/unit"],
        rollback_plan_ref="rollback://baseline",
    )

    assert state["absorption_decision"] == "block_absorption"
    assert state["promotion_readiness"] == "blocked"
    assert "core_sovereignty_violation" in state["blockers"]


def test_validated_candidate_only_reaches_manual_review_with_evidence_and_rollback() -> None:
    state = derive_technology_absorption_state(
        absorption_class="promotable_translation",
        candidate_status="validated",
        requested_core_role="adapter",
        evidence_refs=["evidence://comparison"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://current-baseline",
    )

    assert state["absorption_readiness"] == "ready_for_manual_review"
    assert state["absorption_decision"] == "manual_promotion_review"
    assert state["promotion_readiness"] == "manual_review_only"


def test_unvalidated_candidate_remains_in_controlled_lane() -> None:
    state = derive_technology_absorption_state(
        absorption_class="controlled_complement",
        candidate_status="sandboxed",
        requested_core_role="tool",
        evidence_refs=["evidence://sandbox"],
        proposed_tests=["pytest tests/unit"],
    )

    assert state["absorption_decision"] == "hold_in_lane"
    assert state["experiment_lane_status"] == "controlled_candidate"
    assert "missing_rollback_plan" in state["blockers"]
