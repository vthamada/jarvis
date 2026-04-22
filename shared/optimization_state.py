"""Shared grammar for governed compile/optimize loop readiness."""

from __future__ import annotations

from collections import Counter

_PROMPT_AXES = {
    "workflow_output",
    "metacognitive_guidance",
}
_PLAN_AXES = {
    "mind_composition",
    "capability_decision",
    "capability_effectiveness",
    "handoff_adapter",
    "request_identity",
    "mission_policy",
    "adaptive_intervention",
    "adaptive_intervention_policy",
    "memory_causality",
    "memory_maintenance",
    "memory_lifecycle",
    "memory_corpus",
    "mind_domain_specialist_chain",
    "mind_domain_specialist_effectiveness",
    "expanded_eval_scope",
    "controlled_wave2_experiment",
}
_WORKFLOW_AXES = {
    "workflow_profile",
    "workflow_checkpointing",
    "workflow_resume",
    "procedural_artifacts",
}
_BAD_STATUSES = {"attention_required", "incomplete", "insufficient", "mismatch"}


def _priority_rank(priority: str | None) -> int:
    return {"p0": 0, "p1": 1, "p2": 2}.get(priority or "", 9)


def optimization_target_kind(
    refinement_vectors: list[dict[str, object]] | None,
) -> str:
    vectors = list(refinement_vectors or [])
    if not vectors:
        return "not_applicable"

    by_kind: Counter[str] = Counter()
    best_priority: dict[str, int] = {}
    for vector in vectors:
        axis = str(vector.get("axis", ""))
        priority = _priority_rank(str(vector.get("priority", "")))
        if axis in _PROMPT_AXES:
            kind = "prompt"
        elif axis in _WORKFLOW_AXES:
            kind = "workflow"
        else:
            kind = "plan"
        by_kind[kind] += 1
        current_best = best_priority.get(kind, 99)
        if priority < current_best:
            best_priority[kind] = priority

    if len(by_kind) == 1:
        return next(iter(by_kind))

    ranked = sorted(
        by_kind,
        key=lambda kind: (best_priority.get(kind, 99), -by_kind[kind], kind),
    )
    if len(ranked) > 1 and best_priority.get(ranked[0], 99) == best_priority.get(
        ranked[1], 99
    ):
        return "multi_target"
    return ranked[0]


def derive_optimization_state(
    *,
    refinement_vectors: list[dict[str, object]] | None,
    trace_status: str | None,
    request_identity_status: str | None,
    mission_policy_status: str | None,
    capability_decision_status: str | None,
    handoff_adapter_status: str | None,
    expanded_eval_status: str | None,
    experiment_lane_status: str | None,
    promotion_readiness: str | None,
    adaptive_intervention_effectiveness: str | None,
    memory_maintenance_effectiveness: str | None,
    mind_domain_specialist_effectiveness: str | None,
    workflow_profile_status: str | None,
    workflow_output_status: str | None,
) -> dict[str, object]:
    vectors = list(refinement_vectors or [])
    target_kind = optimization_target_kind(vectors)
    if not vectors and all(
        value in {None, "not_applicable"}
        for value in (
            trace_status,
            request_identity_status,
            mission_policy_status,
            capability_decision_status,
            handoff_adapter_status,
            expanded_eval_status,
            experiment_lane_status,
            promotion_readiness,
            adaptive_intervention_effectiveness,
            memory_maintenance_effectiveness,
            mind_domain_specialist_effectiveness,
            workflow_profile_status,
            workflow_output_status,
        )
    ):
        return {
            "optimization_scope": "not_applicable",
            "optimization_target_kind": "not_applicable",
            "optimization_candidate_status": "not_applicable",
            "optimization_safety_status": "not_applicable",
            "optimization_blockers": [],
            "optimization_readiness": "not_applicable",
            "optimization_release_status": "not_applicable",
        }

    blockers: list[str] = []
    if trace_status in {"attention_required", "incomplete"}:
        blockers.append("trace_not_healthy")
    if request_identity_status in _BAD_STATUSES:
        blockers.append("request_identity_not_ready")
    if mission_policy_status in _BAD_STATUSES:
        blockers.append("mission_policy_not_ready")
    if capability_decision_status in _BAD_STATUSES:
        blockers.append("capability_decision_not_ready")
    if handoff_adapter_status in _BAD_STATUSES:
        blockers.append("handoff_adapter_not_ready")
    if expanded_eval_status == "attention_required":
        blockers.append("expanded_eval_not_ready")
    if experiment_lane_status == "attention_required":
        blockers.append("experiment_lane_not_ready")
    if promotion_readiness == "blocked":
        blockers.append("promotion_blocked")
    if target_kind in {"plan", "multi_target"} and adaptive_intervention_effectiveness in {
        "insufficient",
        "incomplete",
    }:
        blockers.append("adaptive_intervention_not_effective")
    if target_kind in {"plan", "multi_target"} and memory_maintenance_effectiveness in {
        "insufficient",
        "incomplete",
    }:
        blockers.append("memory_maintenance_not_effective")
    if target_kind in {"plan", "multi_target"} and mind_domain_specialist_effectiveness in {
        "insufficient",
        "incomplete",
    }:
        blockers.append("mind_domain_specialist_not_effective")
    if target_kind in {"workflow", "multi_target"} and workflow_profile_status in {
        "attention_required",
        "incomplete",
    }:
        blockers.append("workflow_profile_not_ready")
    if target_kind in {"prompt", "multi_target"} and workflow_output_status in {
        "misaligned",
        "attention_required",
        "incomplete",
    }:
        blockers.append("workflow_output_not_ready")

    if not vectors:
        candidate_status = "no_candidate"
        safety_status = "baseline_only"
        readiness = "hold_baseline"
        release_status = "hold_baseline"
    elif blockers:
        candidate_status = "blocked"
        safety_status = "blocked_by_safety"
        readiness = "blocked"
        release_status = "freeze_and_review"
    else:
        highest_priority = min(_priority_rank(str(item.get("priority", ""))) for item in vectors)
        if highest_priority <= 0:
            candidate_status = "candidate_ready"
            safety_status = "manual_review_only"
            readiness = "candidate_ready"
            release_status = "manual_review_only"
        else:
            candidate_status = "observe_only"
            safety_status = "governed_observation"
            readiness = "observe_only"
            release_status = "observe_in_sandbox"

    return {
        "optimization_scope": "sandbox_only_governed_compile_optimize_loop",
        "optimization_target_kind": target_kind,
        "optimization_candidate_status": candidate_status,
        "optimization_safety_status": safety_status,
        "optimization_blockers": blockers,
        "optimization_readiness": readiness,
        "optimization_release_status": release_status,
    }
