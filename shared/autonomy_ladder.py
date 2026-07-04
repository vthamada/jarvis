"""Runtime autonomy ladder policy helpers.

This module declares the bounded language of autonomy for the runtime. It does
not enforce execution; governance and dispatch enforcement are handled by later
runtime layers.
"""

from __future__ import annotations

from shared.contracts import AutonomyLadderContract, DeliberativePlanContract, InputContract

AUTONOMY_LEVEL_ORDER = (
    "assist_only",
    "confirm_before_action",
    "bounded_core_action",
    "supervised_external_action",
)

AUTONOMY_LEVEL_POLICIES = {
    "assist_only": {
        "max_capability_mode": "contained_guidance",
        "human_confirmation_required": True,
        "allowed_runtime_actions": ["read_context", "draft_plan", "explain_limits"],
        "blocked_runtime_actions": [
            "execute_operation",
            "external_tool_action",
            "automatic_promotion",
            "core_mutation",
        ],
    },
    "confirm_before_action": {
        "max_capability_mode": "core_with_specialist_handoff",
        "human_confirmation_required": True,
        "allowed_runtime_actions": [
            "read_context",
            "draft_plan",
            "prepare_bounded_action",
        ],
        "blocked_runtime_actions": [
            "execute_without_confirmation",
            "automatic_promotion",
            "core_mutation",
        ],
    },
    "bounded_core_action": {
        "max_capability_mode": "core_with_local_operation",
        "human_confirmation_required": False,
        "allowed_runtime_actions": [
            "read_context",
            "draft_plan",
            "execute_reversible_core_action",
        ],
        "blocked_runtime_actions": [
            "irreversible_action",
            "external_tool_action_without_gate",
            "automatic_promotion",
            "core_mutation",
        ],
    },
    "supervised_external_action": {
        "max_capability_mode": "core_with_local_operation",
        "human_confirmation_required": True,
        "allowed_runtime_actions": [
            "read_context",
            "draft_plan",
            "prepare_external_action",
        ],
        "blocked_runtime_actions": [
            "external_tool_action_without_confirmation",
            "automatic_promotion",
            "core_mutation",
        ],
    },
}


def derive_autonomy_ladder(
    *,
    contract: InputContract,
    plan: DeliberativePlanContract,
) -> AutonomyLadderContract:
    """Derive the effective autonomy contract from request and plan signals."""

    requested_level = _normalize_level(
        contract.requested_autonomy_level,
        default=_default_requested_level(plan),
    )
    max_level = _normalize_level(
        contract.max_autonomy_level,
        default=_default_max_level(plan),
    )
    effective_level = _min_level(requested_level, max_level)
    status = "within_limit" if effective_level == requested_level else "downgraded_to_max"
    policy = AUTONOMY_LEVEL_POLICIES[effective_level]
    human_confirmation_required = bool(
        policy["human_confirmation_required"]
        or plan.requires_human_validation
        or plan.capability_decision_authorization_status
        in {"human_validation_required", "blocked"}
    )
    confirmation_mode = (
        contract.autonomy_confirmation_mode
        or plan.request_confirmation_mode
        or ("explicit" if human_confirmation_required else "not_required")
    )
    policy_refs = list(dict.fromkeys([
        "policy://autonomy-ladder/runtime-contract",
        *contract.autonomy_policy_refs,
        *plan.request_identity_policy_refs,
    ]))
    return AutonomyLadderContract(
        requested_autonomy_level=requested_level,
        max_autonomy_level=max_level,
        effective_autonomy_level=effective_level,
        autonomy_ladder_status=status,
        max_capability_mode=str(policy["max_capability_mode"]),
        human_confirmation_required=human_confirmation_required,
        human_confirmation_mode=confirmation_mode,
        allowed_runtime_actions=list(policy["allowed_runtime_actions"]),
        blocked_runtime_actions=list(policy["blocked_runtime_actions"]),
        policy_refs=policy_refs,
        summary=(
            f"requested={requested_level}; max={max_level}; "
            f"effective={effective_level}; status={status}"
        ),
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
    )


def _default_requested_level(plan: DeliberativePlanContract) -> str:
    if plan.capability_decision_selected_mode == "core_with_local_operation":
        return "bounded_core_action"
    if plan.capability_decision_selected_mode == "core_with_specialist_handoff":
        return "confirm_before_action"
    return "assist_only"


def _default_max_level(plan: DeliberativePlanContract) -> str:
    if plan.requires_human_validation:
        return "confirm_before_action"
    if plan.capability_decision_selected_mode == "core_with_local_operation":
        return "bounded_core_action"
    if plan.capability_decision_selected_mode == "core_with_specialist_handoff":
        return "confirm_before_action"
    return "assist_only"


def _normalize_level(value: str | None, *, default: str) -> str:
    if value in AUTONOMY_LEVEL_ORDER:
        return value
    return default


def _min_level(requested_level: str, max_level: str) -> str:
    requested_index = AUTONOMY_LEVEL_ORDER.index(requested_level)
    max_index = AUTONOMY_LEVEL_ORDER.index(max_level)
    return AUTONOMY_LEVEL_ORDER[min(requested_index, max_index)]
