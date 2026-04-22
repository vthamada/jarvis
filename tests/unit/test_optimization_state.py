from shared.optimization_state import (
    derive_optimization_state,
    optimization_target_kind,
)


def test_optimization_target_kind_prefers_primary_prompt_axis() -> None:
    target_kind = optimization_target_kind(
        [
            {
                "workflow_profile": "analysis",
                "axis": "workflow_output",
                "priority": "p0",
                "recommendation": "tighten final synthesis framing",
            },
            {
                "workflow_profile": "analysis",
                "axis": "mission_policy",
                "priority": "p1",
                "recommendation": "review executive policy framing",
            },
        ]
    )

    assert target_kind == "prompt"


def test_derive_optimization_state_blocks_workflow_candidate_when_release_guardrails_drift(
) -> None:
    state = derive_optimization_state(
        refinement_vectors=[
            {
                "workflow_profile": "operational_readiness",
                "axis": "workflow_checkpointing",
                "priority": "p0",
                "recommendation": "stabilize checkpoint coverage",
            }
        ],
        trace_status="healthy",
        request_identity_status="healthy",
        mission_policy_status="policy_aligned",
        capability_decision_status="healthy",
        handoff_adapter_status="healthy",
        expanded_eval_status="candidate_ready",
        experiment_lane_status="controlled_candidate",
        promotion_readiness="blocked",
        adaptive_intervention_effectiveness="effective",
        memory_maintenance_effectiveness="effective",
        mind_domain_specialist_effectiveness="effective",
        workflow_profile_status="attention_required",
        workflow_output_status="coherent",
    )

    assert state["optimization_scope"] == "sandbox_only_governed_compile_optimize_loop"
    assert state["optimization_target_kind"] == "workflow"
    assert state["optimization_candidate_status"] == "blocked"
    assert state["optimization_safety_status"] == "blocked_by_safety"
    assert state["optimization_readiness"] == "blocked"
    assert state["optimization_release_status"] == "freeze_and_review"
    assert state["optimization_blockers"] == [
        "promotion_blocked",
        "workflow_profile_not_ready",
    ]
