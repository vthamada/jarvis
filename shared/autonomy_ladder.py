"""Canonical, fail-closed autonomy policy for runtime actions."""

from __future__ import annotations

from collections.abc import Sequence

from shared.contracts import (
    AutonomyActionPolicyDecisionContract,
    AutonomyLadderContract,
    DeliberativePlanContract,
    InputContract,
)

AUTONOMY_ACTION_POLICY_VERSION = "autonomy-action-policy/v1"

AUTONOMY_LEVEL_ORDER = (
    "assist_only",
    "confirm_before_action",
    "bounded_core_action",
    "supervised_external_action",
)

AUTONOMY_ACTION_KINDS = (
    "read_context",
    "draft_plan",
    "explain_limits",
    "prepare_local_action",
    "execute_reversible_core_action",
    "prepare_external_action",
    "execute_external_action",
    "irreversible_action",
    "automatic_promotion",
    "core_mutation",
)

GUIDANCE_ACTION_KINDS = frozenset(
    {"read_context", "draft_plan", "explain_limits"}
)
EXECUTION_ACTION_KINDS = frozenset(
    {"execute_reversible_core_action", "execute_external_action"}
)
_OPERATIONAL_ACTION_KINDS = frozenset(
    {
        "prepare_local_action",
        "execute_reversible_core_action",
        "prepare_external_action",
        "execute_external_action",
    }
)
GLOBALLY_BLOCKED_ACTION_KINDS = frozenset(
    {"irreversible_action", "automatic_promotion", "core_mutation"}
)

CONFIRMATION_MODE_NOT_REQUIRED = "not_required"
CONFIRMATION_MODE_EXPLICIT_REQUIRED = "explicit_confirmation_required"
AUTONOMY_CONFIRMATION_MODES = (
    CONFIRMATION_MODE_NOT_REQUIRED,
    CONFIRMATION_MODE_EXPLICIT_REQUIRED,
)
AUTONOMY_CONFIRMATION_EVIDENCE_STATES = ("absent", "verified", "invalid")

_CONFIRMATION_MODE_ALIASES = {
    "explicit": CONFIRMATION_MODE_EXPLICIT_REQUIRED,
    "bounded_autonomy": CONFIRMATION_MODE_NOT_REQUIRED,
    CONFIRMATION_MODE_NOT_REQUIRED: CONFIRMATION_MODE_NOT_REQUIRED,
    CONFIRMATION_MODE_EXPLICIT_REQUIRED: CONFIRMATION_MODE_EXPLICIT_REQUIRED,
}

CAPABILITY_MODE_ORDER = {
    "clarification_only": 0,
    "contained_guidance": 0,
    "core_guidance_only": 0,
    "core_with_specialist_handoff": 1,
    "core_with_local_operation": 2,
    "core_with_supervised_external_operation": 3,
}

_ACTION_KIND_MIN_CAPABILITY_RANK: dict[str, int | None] = {
    "read_context": 0,
    "draft_plan": 0,
    "explain_limits": 0,
    "prepare_local_action": 2,
    "execute_reversible_core_action": 2,
    "prepare_external_action": 3,
    "execute_external_action": 3,
    "irreversible_action": None,
    "automatic_promotion": None,
    "core_mutation": None,
}

_ASSIST_ALLOWED = (
    "read_context",
    "draft_plan",
    "explain_limits",
)
_LOCAL_ALLOWED = (
    *_ASSIST_ALLOWED,
    "prepare_local_action",
    "execute_reversible_core_action",
)
_SUPERVISED_ALLOWED = (
    *_LOCAL_ALLOWED,
    "prepare_external_action",
    "execute_external_action",
)


def _blocked_actions(allowed_actions: tuple[str, ...]) -> tuple[str, ...]:
    allowed = frozenset(allowed_actions)
    return tuple(action for action in AUTONOMY_ACTION_KINDS if action not in allowed)


AUTONOMY_LEVEL_POLICIES = {
    "assist_only": {
        "max_capability_mode": "contained_guidance",
        "human_confirmation_required": False,
        "allowed_runtime_actions": _ASSIST_ALLOWED,
        "blocked_runtime_actions": _blocked_actions(_ASSIST_ALLOWED),
        "confirmation_required_actions": (),
    },
    "confirm_before_action": {
        "max_capability_mode": "core_with_local_operation",
        "human_confirmation_required": True,
        "allowed_runtime_actions": _LOCAL_ALLOWED,
        "blocked_runtime_actions": _blocked_actions(_LOCAL_ALLOWED),
        "confirmation_required_actions": ("execute_reversible_core_action",),
    },
    "bounded_core_action": {
        "max_capability_mode": "core_with_local_operation",
        "human_confirmation_required": False,
        "allowed_runtime_actions": _LOCAL_ALLOWED,
        "blocked_runtime_actions": _blocked_actions(_LOCAL_ALLOWED),
        "confirmation_required_actions": (),
    },
    "supervised_external_action": {
        "max_capability_mode": "core_with_supervised_external_operation",
        "human_confirmation_required": True,
        "allowed_runtime_actions": _SUPERVISED_ALLOWED,
        "blocked_runtime_actions": _blocked_actions(_SUPERVISED_ALLOWED),
        "confirmation_required_actions": (
            "execute_reversible_core_action",
            "execute_external_action",
        ),
    },
}


def derive_autonomy_ladder(
    *,
    contract: InputContract,
    plan: DeliberativePlanContract,
    action_kind: str | None = None,
) -> AutonomyLadderContract:
    """Derive a canonical ladder without inheriting executable plan authority."""

    validation_errors: list[str] = []
    requested_level = _validate_declared_level(
        contract.requested_autonomy_level,
        field_name="requested_autonomy_level",
        errors=validation_errors,
    )
    max_level = _validate_declared_level(
        contract.max_autonomy_level,
        field_name="max_autonomy_level",
        errors=validation_errors,
    )

    declared_action_kind = action_kind or plan.autonomy_action_kind
    if declared_action_kind is not None and declared_action_kind not in AUTONOMY_ACTION_KINDS:
        _append_reason(validation_errors, "autonomy_action_kind_unknown")

    confirmation_mode = _resolve_declared_confirmation_mode(
        requested_mode=contract.autonomy_confirmation_mode,
        planned_mode=plan.request_confirmation_mode,
        errors=validation_errors,
    )
    if (
        confirmation_mode is None
        and declared_action_kind in _OPERATIONAL_ACTION_KINDS
    ):
        _append_reason(validation_errors, "confirmation_mode_missing_for_effect")

    if requested_level is None or max_level is None or validation_errors:
        requested_level = "assist_only"
        max_level = "assist_only"
        effective_level = "assist_only"
        status = "invalid_fail_closed"
    else:
        effective_level = _min_level(requested_level, max_level)
        status = (
            "within_limit"
            if effective_level == requested_level
            else "downgraded_to_max"
        )

    policy = AUTONOMY_LEVEL_POLICIES[effective_level]
    minimum_confirmation_required = _minimum_confirmation_required(
        policy=policy,
        action_kind=(
            declared_action_kind
            if declared_action_kind in AUTONOMY_ACTION_KINDS
            else None
        ),
    )
    if confirmation_mode is None:
        confirmation_mode = (
            CONFIRMATION_MODE_EXPLICIT_REQUIRED
            if minimum_confirmation_required
            else CONFIRMATION_MODE_NOT_REQUIRED
        )
    elif (
        minimum_confirmation_required
        and confirmation_mode != CONFIRMATION_MODE_EXPLICIT_REQUIRED
    ):
        _append_reason(validation_errors, "confirmation_below_policy_minimum")

    if validation_errors and status != "invalid_fail_closed":
        requested_level = "assist_only"
        max_level = "assist_only"
        effective_level = "assist_only"
        status = "invalid_fail_closed"
        policy = AUTONOMY_LEVEL_POLICIES[effective_level]
        confirmation_mode = CONFIRMATION_MODE_NOT_REQUIRED

    human_confirmation_required = (
        confirmation_mode == CONFIRMATION_MODE_EXPLICIT_REQUIRED
    )
    policy_refs = list(
        dict.fromkeys(
            [
                "policy://autonomy-ladder/runtime-contract",
                f"policy://autonomy-action/{AUTONOMY_ACTION_POLICY_VERSION}",
                *contract.autonomy_policy_refs,
                *plan.request_identity_policy_refs,
            ]
        )
    )
    return AutonomyLadderContract(
        requested_autonomy_level=requested_level,
        max_autonomy_level=max_level,
        effective_autonomy_level=effective_level,
        autonomy_ladder_status=status,
        max_capability_mode=str(policy["max_capability_mode"]),
        human_confirmation_required=human_confirmation_required,
        human_confirmation_mode=confirmation_mode,
        autonomy_action_kind=(
            declared_action_kind
            if declared_action_kind in AUTONOMY_ACTION_KINDS
            else None
        ),
        autonomy_validation_errors=list(validation_errors),
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


def evaluate_autonomy_action(
    *,
    requested_autonomy_level: str | None,
    max_autonomy_level: str | None,
    effective_autonomy_level: str | None,
    autonomy_ladder_status: str | None,
    action_kind: str | None,
    selected_capability_mode: str | None,
    max_capability_mode: str | None,
    allowed_runtime_actions: Sequence[str] | None,
    blocked_runtime_actions: Sequence[str] | None,
    human_confirmation_required: bool | None,
    human_confirmation_mode: str | None,
    confirmation_evidence_state: str = "absent",
    autonomy_validation_errors: Sequence[str] | None = (),
) -> AutonomyActionPolicyDecisionContract:
    """Evaluate one complete autonomy projection and deny every unknown state."""

    reasons: list[str] = []
    requested_valid = _require_known_value(
        requested_autonomy_level,
        allowed=AUTONOMY_LEVEL_ORDER,
        field_name="requested_autonomy_level",
        reasons=reasons,
    )
    max_valid = _require_known_value(
        max_autonomy_level,
        allowed=AUTONOMY_LEVEL_ORDER,
        field_name="max_autonomy_level",
        reasons=reasons,
    )
    effective_valid = _require_known_value(
        effective_autonomy_level,
        allowed=AUTONOMY_LEVEL_ORDER,
        field_name="effective_autonomy_level",
        reasons=reasons,
    )

    expected_status: str | None = None
    if requested_valid and max_valid:
        expected_effective = _min_level(
            str(requested_autonomy_level),
            str(max_autonomy_level),
        )
        expected_status = (
            "within_limit"
            if expected_effective == requested_autonomy_level
            else "downgraded_to_max"
        )
        if effective_autonomy_level != expected_effective:
            _append_reason(reasons, "effective_autonomy_level_mismatch")

    if autonomy_ladder_status == "invalid_fail_closed":
        _append_reason(reasons, "autonomy_ladder_invalid_fail_closed")
    elif autonomy_ladder_status not in {"within_limit", "downgraded_to_max"}:
        _append_reason(reasons, "autonomy_ladder_status_unknown")
    elif expected_status is not None and autonomy_ladder_status != expected_status:
        _append_reason(reasons, "autonomy_ladder_status_mismatch")

    declared_validation_errors = _canonical_string_sequence(
        autonomy_validation_errors
    )
    if declared_validation_errors is None:
        _append_reason(reasons, "autonomy_validation_errors_invalid")
    elif declared_validation_errors:
        _append_reason(reasons, "autonomy_validation_errors_present")

    action_valid = _require_known_value(
        action_kind,
        allowed=AUTONOMY_ACTION_KINDS,
        field_name="autonomy_action_kind",
        reasons=reasons,
    )
    selected_capability_valid = _require_known_value(
        selected_capability_mode,
        allowed=tuple(CAPABILITY_MODE_ORDER),
        field_name="selected_capability_mode",
        reasons=reasons,
    )
    max_capability_valid = _require_known_value(
        max_capability_mode,
        allowed=tuple(CAPABILITY_MODE_ORDER),
        field_name="max_capability_mode",
        reasons=reasons,
    )

    policy = (
        AUTONOMY_LEVEL_POLICIES[str(effective_autonomy_level)]
        if effective_valid
        else None
    )
    if policy is not None and max_capability_valid:
        if max_capability_mode != policy["max_capability_mode"]:
            _append_reason(reasons, "max_capability_mode_projection_mismatch")
    if selected_capability_valid and max_capability_valid:
        if CAPABILITY_MODE_ORDER[str(selected_capability_mode)] > CAPABILITY_MODE_ORDER[
            str(max_capability_mode)
        ]:
            _append_reason(reasons, "capability_above_autonomy_limit")
    if action_valid and selected_capability_valid:
        minimum_capability_rank = _ACTION_KIND_MIN_CAPABILITY_RANK[str(action_kind)]
        if minimum_capability_rank is None:
            _append_reason(reasons, "action_kind_globally_blocked")
        elif (
            CAPABILITY_MODE_ORDER[str(selected_capability_mode)]
            < minimum_capability_rank
        ):
            _append_reason(reasons, "capability_below_action_requirement")

    declared_allowed = _canonical_string_sequence(allowed_runtime_actions)
    declared_blocked = _canonical_string_sequence(blocked_runtime_actions)
    if declared_allowed is None:
        _append_reason(reasons, "allowed_runtime_actions_invalid")
    if declared_blocked is None:
        _append_reason(reasons, "blocked_runtime_actions_invalid")
    if policy is not None:
        if declared_allowed != tuple(policy["allowed_runtime_actions"]):
            _append_reason(reasons, "allowed_runtime_actions_projection_mismatch")
        if declared_blocked != tuple(policy["blocked_runtime_actions"]):
            _append_reason(reasons, "blocked_runtime_actions_projection_mismatch")

    normalized_confirmation_mode = normalize_autonomy_confirmation_mode(
        human_confirmation_mode
    )
    if human_confirmation_mode is None or human_confirmation_mode == "":
        _append_reason(reasons, "human_confirmation_mode_missing")
    elif normalized_confirmation_mode is None:
        _append_reason(reasons, "human_confirmation_mode_unknown")
    if type(human_confirmation_required) is not bool:
        _append_reason(reasons, "human_confirmation_required_invalid")
    elif normalized_confirmation_mode is not None and human_confirmation_required != (
        normalized_confirmation_mode == CONFIRMATION_MODE_EXPLICIT_REQUIRED
    ):
        _append_reason(reasons, "human_confirmation_contract_contradictory")

    minimum_confirmation_required = False
    action_allowed = False
    if policy is not None and action_valid:
        action_allowed = str(action_kind) in policy["allowed_runtime_actions"]
        minimum_confirmation_required = str(action_kind) in policy[
            "confirmation_required_actions"
        ]
        if not action_allowed:
            _append_reason(reasons, "action_kind_blocked_by_autonomy_level")
    if (
        minimum_confirmation_required
        and normalized_confirmation_mode != CONFIRMATION_MODE_EXPLICIT_REQUIRED
    ):
        _append_reason(reasons, "confirmation_below_policy_minimum")

    if confirmation_evidence_state not in AUTONOMY_CONFIRMATION_EVIDENCE_STATES:
        _append_reason(reasons, "confirmation_evidence_state_unknown")
    elif confirmation_evidence_state == "invalid":
        _append_reason(reasons, "confirmation_evidence_invalid")

    confirmation_required = (
        normalized_confirmation_mode == CONFIRMATION_MODE_EXPLICIT_REQUIRED
    )
    if reasons:
        decision = "block"
        side_effect_allowed = False
    elif confirmation_required and confirmation_evidence_state == "absent":
        decision = "require_confirmation"
        side_effect_allowed = False
        reasons = ["exact_confirmation_required"]
    else:
        decision = "allow"
        side_effect_allowed = bool(
            action_allowed and action_kind in EXECUTION_ACTION_KINDS
        )
        reasons = ["autonomy_action_policy_satisfied"]

    return AutonomyActionPolicyDecisionContract(
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        decision=decision,
        requested_autonomy_level=requested_autonomy_level,
        max_autonomy_level=max_autonomy_level,
        effective_autonomy_level=effective_autonomy_level,
        autonomy_ladder_status=autonomy_ladder_status,
        action_kind=action_kind,
        selected_capability_mode=selected_capability_mode,
        max_capability_mode=max_capability_mode,
        confirmation_required=confirmation_required,
        confirmation_requirement=(
            normalized_confirmation_mode or CONFIRMATION_MODE_NOT_REQUIRED
        ),
        confirmation_evidence_state=confirmation_evidence_state,
        side_effect_allowed=side_effect_allowed,
        reason_codes=tuple(reasons),
    )


def normalize_autonomy_confirmation_mode(value: str | None) -> str | None:
    """Normalize supported boundary aliases to the two internal modes."""

    if not isinstance(value, str) or not value:
        return None
    return _CONFIRMATION_MODE_ALIASES.get(value)


def capability_mode_exceeds_autonomy_limit(
    *,
    selected_mode: str | None,
    max_capability_mode: str | None,
) -> bool:
    """Return true for an exceeded, absent, or unknown capability projection."""

    if not isinstance(selected_mode, str) or selected_mode not in CAPABILITY_MODE_ORDER:
        return True
    if (
        not isinstance(max_capability_mode, str)
        or max_capability_mode not in CAPABILITY_MODE_ORDER
    ):
        return True
    return (
        CAPABILITY_MODE_ORDER[selected_mode]
        > CAPABILITY_MODE_ORDER[max_capability_mode]
    )


def _validate_declared_level(
    value: str | None,
    *,
    field_name: str,
    errors: list[str],
) -> str | None:
    if value is None or value == "":
        _append_reason(errors, f"{field_name}_missing")
        return None
    if value not in AUTONOMY_LEVEL_ORDER:
        _append_reason(errors, f"{field_name}_unknown")
        return None
    return value


def _resolve_declared_confirmation_mode(
    *,
    requested_mode: str | None,
    planned_mode: str | None,
    errors: list[str],
) -> str | None:
    normalized_requested = normalize_autonomy_confirmation_mode(requested_mode)
    normalized_planned = normalize_autonomy_confirmation_mode(planned_mode)
    if requested_mode is not None and normalized_requested is None:
        _append_reason(errors, "autonomy_confirmation_mode_unknown")
    if planned_mode is not None and normalized_planned is None:
        _append_reason(errors, "request_confirmation_mode_unknown")
    if CONFIRMATION_MODE_EXPLICIT_REQUIRED in {
        normalized_requested,
        normalized_planned,
    }:
        return CONFIRMATION_MODE_EXPLICIT_REQUIRED
    if CONFIRMATION_MODE_NOT_REQUIRED in {
        normalized_requested,
        normalized_planned,
    }:
        return CONFIRMATION_MODE_NOT_REQUIRED
    return None


def _minimum_confirmation_required(
    *,
    policy: dict[str, object],
    action_kind: str | None,
) -> bool:
    if action_kind is not None:
        return action_kind in policy["confirmation_required_actions"]
    return bool(policy["human_confirmation_required"])


def _min_level(requested_level: str, max_level: str) -> str:
    requested_index = AUTONOMY_LEVEL_ORDER.index(requested_level)
    max_index = AUTONOMY_LEVEL_ORDER.index(max_level)
    return AUTONOMY_LEVEL_ORDER[min(requested_index, max_index)]


def _require_known_value(
    value: str | None,
    *,
    allowed: tuple[str, ...],
    field_name: str,
    reasons: list[str],
) -> bool:
    if value is None or value == "":
        _append_reason(reasons, f"{field_name}_missing")
        return False
    if value not in allowed:
        _append_reason(reasons, f"{field_name}_unknown")
        return False
    return True


def _canonical_string_sequence(
    values: Sequence[str] | None,
) -> tuple[str, ...] | None:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return None
    normalized = tuple(values)
    if any(not isinstance(value, str) or not value for value in normalized):
        return None
    return normalized


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)
