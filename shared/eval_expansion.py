"""Shared grammar for expanded eval scope and controlled wave-two experiments."""

from __future__ import annotations

_GOOD_REQUEST_IDENTITY = {"healthy", "not_applicable"}
_GOOD_MISSION_POLICY = {"policy_aligned", "mandatory_override", "not_applicable"}
_GOOD_CAPABILITY_DECISION = {"healthy", "not_applicable"}
_GOOD_CAPABILITY_EFFECTIVENESS = {"effective", "not_applicable"}
_GOOD_HANDOFF = {"healthy", "contained", "not_applicable"}

_GOOD_CONTINUITY = {"healthy", "not_applicable"}
_GOOD_CHECKPOINT = {"healthy", "not_applicable"}
_GOOD_RESUME = {
    "healthy",
    "not_applicable",
    "fresh_start",
    "resume_available",
    "resumed_from_checkpoint",
    "checkpointed_for_followup",
    "checkpointed_for_manual_resume",
    "completed_without_resume",
}
_GOOD_SUBFLOW = {"healthy", "contained", "not_applicable"}
_GOOD_RUNTIME_STATE = {"healthy", "not_applicable"}

_BAD_SURFACE = {"attention_required", "incomplete", "insufficient"}
_BAD_ECOSYSTEM = {
    "attention_required",
    "incomplete",
    "resume_blocked",
    "manual_resume_required",
}


def _all_not_applicable(*values: str | None) -> bool:
    return all(value in {None, "not_applicable"} for value in values)


def surface_axis_status(
    *,
    capability_decision_status: str | None,
    capability_effectiveness: str | None,
    handoff_adapter_status: str | None,
    request_identity_status: str | None,
    mission_policy_status: str | None,
) -> str:
    values = (
        capability_decision_status,
        capability_effectiveness,
        handoff_adapter_status,
        request_identity_status,
        mission_policy_status,
    )
    if _all_not_applicable(*values):
        return "not_in_phase"
    if (
        capability_decision_status in _BAD_SURFACE
        or capability_effectiveness in _BAD_SURFACE
        or handoff_adapter_status in _BAD_SURFACE
        or request_identity_status in _BAD_SURFACE
        or mission_policy_status in _BAD_SURFACE
    ):
        return "attention_required"
    if (
        capability_decision_status in _GOOD_CAPABILITY_DECISION
        and capability_effectiveness in _GOOD_CAPABILITY_EFFECTIVENESS
        and handoff_adapter_status in _GOOD_HANDOFF
        and request_identity_status in _GOOD_REQUEST_IDENTITY
        and mission_policy_status in _GOOD_MISSION_POLICY
    ):
        return "candidate_ready"
    return "coverage_partial"


def ecosystem_state_status(
    *,
    continuity_trace_status: str | None,
    workflow_checkpoint_status: str | None,
    workflow_resume_status: str | None,
    specialist_subflow_status: str | None,
    mission_runtime_state_status: str | None,
) -> str:
    values = (
        continuity_trace_status,
        workflow_checkpoint_status,
        workflow_resume_status,
        specialist_subflow_status,
        mission_runtime_state_status,
    )
    if _all_not_applicable(*values):
        return "not_in_phase"
    if (
        continuity_trace_status in _BAD_ECOSYSTEM
        or workflow_checkpoint_status in _BAD_ECOSYSTEM
        or workflow_resume_status in _BAD_ECOSYSTEM
        or specialist_subflow_status in _BAD_ECOSYSTEM
        or mission_runtime_state_status in _BAD_ECOSYSTEM
    ):
        return "attention_required"
    if (
        continuity_trace_status in _GOOD_CONTINUITY
        and workflow_checkpoint_status in _GOOD_CHECKPOINT
        and workflow_resume_status in _GOOD_RESUME
        and specialist_subflow_status in _GOOD_SUBFLOW
        and mission_runtime_state_status in _GOOD_RUNTIME_STATE
    ):
        return "candidate_ready"
    return "coverage_partial"


def expanded_eval_status(*, surface_axis: str, ecosystem_state: str) -> str:
    if "attention_required" in {surface_axis, ecosystem_state}:
        return "attention_required"
    if surface_axis == "candidate_ready" and ecosystem_state == "candidate_ready":
        return "candidate_ready"
    if surface_axis == "not_in_phase" and ecosystem_state == "not_in_phase":
        return "not_in_phase"
    if "candidate_ready" in {surface_axis, ecosystem_state} or "coverage_partial" in {
        surface_axis,
        ecosystem_state,
    }:
        return "baseline_expanding"
    return "baseline_only"


def wave2_candidate_class(*, surface_axis: str, ecosystem_state: str) -> str:
    if surface_axis == "candidate_ready" and ecosystem_state == "candidate_ready":
        return "surface_and_ecosystem"
    if surface_axis == "candidate_ready":
        return "surface_contract"
    if ecosystem_state == "candidate_ready":
        return "ecosystem_state"
    return "baseline_hardening"


def experiment_entry_status(*, expanded_eval: str, candidate_class: str) -> str:
    if expanded_eval == "attention_required":
        return "blocked_by_drift"
    if candidate_class != "baseline_hardening":
        return "candidate_ready"
    if expanded_eval == "not_in_phase":
        return "blocked_by_phase"
    return "baseline_only"


def promotion_readiness(*, experiment_entry: str) -> str:
    if experiment_entry == "candidate_ready":
        return "manual_review_only"
    if experiment_entry == "baseline_only":
        return "not_applicable"
    return "blocked"


def experiment_lane_status(
    *,
    experiment_entry: str,
    promotion_readiness_status: str,
) -> str:
    if experiment_entry == "blocked_by_drift":
        return "attention_required"
    if experiment_entry == "blocked_by_phase":
        return "out_of_lane"
    if promotion_readiness_status == "manual_review_only":
        return "controlled_candidate"
    return "baseline_only"


def experiment_exit_status(*, experiment_lane: str) -> str:
    if experiment_lane == "attention_required":
        return "freeze_and_review"
    if experiment_lane == "controlled_candidate":
        return "hold_in_lane"
    return "hold_baseline"


def derive_expanded_eval_state(
    *,
    capability_decision_status: str | None,
    capability_effectiveness: str | None,
    handoff_adapter_status: str | None,
    request_identity_status: str | None,
    mission_policy_status: str | None,
    continuity_trace_status: str | None,
    workflow_checkpoint_status: str | None,
    workflow_resume_status: str | None,
    specialist_subflow_status: str | None,
    mission_runtime_state_status: str | None,
) -> dict[str, str]:
    surface = surface_axis_status(
        capability_decision_status=capability_decision_status,
        capability_effectiveness=capability_effectiveness,
        handoff_adapter_status=handoff_adapter_status,
        request_identity_status=request_identity_status,
        mission_policy_status=mission_policy_status,
    )
    ecosystem = ecosystem_state_status(
        continuity_trace_status=continuity_trace_status,
        workflow_checkpoint_status=workflow_checkpoint_status,
        workflow_resume_status=workflow_resume_status,
        specialist_subflow_status=specialist_subflow_status,
        mission_runtime_state_status=mission_runtime_state_status,
    )
    expanded = expanded_eval_status(
        surface_axis=surface,
        ecosystem_state=ecosystem,
    )
    candidate_class = wave2_candidate_class(
        surface_axis=surface,
        ecosystem_state=ecosystem,
    )
    entry = experiment_entry_status(
        expanded_eval=expanded,
        candidate_class=candidate_class,
    )
    readiness = promotion_readiness(experiment_entry=entry)
    lane = experiment_lane_status(
        experiment_entry=entry,
        promotion_readiness_status=readiness,
    )
    return {
        "expanded_eval_status": expanded,
        "surface_axis_status": surface,
        "ecosystem_state_status": ecosystem,
        "experiment_lane_status": lane,
        "wave2_candidate_class": candidate_class,
        "experiment_entry_status": entry,
        "experiment_exit_status": experiment_exit_status(experiment_lane=lane),
        "promotion_readiness": readiness,
    }
