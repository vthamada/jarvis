from dataclasses import FrozenInstanceError

import pytest

from shared.autonomy_ladder import (
    AUTONOMY_ACTION_KINDS,
    AUTONOMY_LEVEL_POLICIES,
    CAPABILITY_MODE_ORDER,
    capability_mode_exceeds_autonomy_limit,
    derive_autonomy_ladder,
    evaluate_autonomy_action,
    normalize_autonomy_confirmation_mode,
)
from shared.contract_validation import validate_contract_instance
from shared.contracts import DeliberativePlanContract, InputContract
from shared.schemas import (
    AUTONOMY_ACTION_POLICY_DECISION_SCHEMA,
    AUTONOMY_LADDER_SCHEMA,
    DELIBERATIVE_PLAN_SCHEMA,
    OPERATION_DISPATCH_SCHEMA,
)
from shared.types import ChannelType, InputType, RequestId, SessionId

ACTION_KINDS_ORACLE = (
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
EXECUTION_KINDS_ORACLE = {
    "execute_reversible_core_action",
    "execute_external_action",
}
CAPABILITY_RANK_ORACLE = {
    "clarification_only": 0,
    "contained_guidance": 0,
    "core_guidance_only": 0,
    "core_with_specialist_handoff": 1,
    "core_with_local_operation": 2,
    "core_with_supervised_external_operation": 3,
}
ACTION_MIN_CAPABILITY_RANK_ORACLE = {
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
POLICY_ORACLE = {
    "assist_only": {
        "max_capability": "contained_guidance",
        "allowed": (
            "read_context",
            "draft_plan",
            "explain_limits",
        ),
        "requires_confirmation": (),
        "level_confirmation": False,
    },
    "confirm_before_action": {
        "max_capability": "core_with_local_operation",
        "allowed": (
            "read_context",
            "draft_plan",
            "explain_limits",
            "prepare_local_action",
            "execute_reversible_core_action",
        ),
        "requires_confirmation": ("execute_reversible_core_action",),
        "level_confirmation": True,
    },
    "bounded_core_action": {
        "max_capability": "core_with_local_operation",
        "allowed": (
            "read_context",
            "draft_plan",
            "explain_limits",
            "prepare_local_action",
            "execute_reversible_core_action",
        ),
        "requires_confirmation": (),
        "level_confirmation": False,
    },
    "supervised_external_action": {
        "max_capability": "core_with_supervised_external_operation",
        "allowed": (
            "read_context",
            "draft_plan",
            "explain_limits",
            "prepare_local_action",
            "execute_reversible_core_action",
            "prepare_external_action",
            "execute_external_action",
        ),
        "requires_confirmation": (
            "execute_reversible_core_action",
            "execute_external_action",
        ),
        "level_confirmation": True,
    },
}


def _plan(
    *,
    request_confirmation_mode: str | None = None,
    action_kind: str | None = None,
) -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="bounded plan",
        goal="preserve the policy boundary",
        steps=["inspect"],
        active_domains=[],
        active_minds=[],
        constraints=["fail closed"],
        risks=[],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="test fixture",
        request_confirmation_mode=request_confirmation_mode,
        autonomy_action_kind=action_kind,
    )


def _input(
    *,
    requested_level: str | None,
    max_level: str | None,
    confirmation_mode: str | None = None,
) -> InputContract:
    return InputContract(
        request_id=RequestId("req-autonomy-unit"),
        session_id=SessionId("sess-autonomy-unit"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="evaluate bounded autonomy",
        timestamp="2026-08-29T12:00:00Z",
        requested_autonomy_level=requested_level,
        max_autonomy_level=max_level,
        autonomy_confirmation_mode=confirmation_mode,
    )


def _blocked_for(level: str) -> tuple[str, ...]:
    allowed = set(POLICY_ORACLE[level]["allowed"])
    return tuple(action for action in ACTION_KINDS_ORACLE if action not in allowed)


def _selected_capability(action_kind: str) -> str:
    if action_kind in {"prepare_external_action", "execute_external_action"}:
        return "core_with_supervised_external_operation"
    if action_kind in {
        "prepare_local_action",
        "execute_reversible_core_action",
    }:
        return "core_with_local_operation"
    return "core_guidance_only"


def _evaluation_kwargs(
    level: str,
    action_kind: str,
    evidence_state: str,
) -> dict[str, object]:
    oracle = POLICY_ORACLE[level]
    confirmation_required = action_kind in oracle["requires_confirmation"]
    return {
        "requested_autonomy_level": level,
        "max_autonomy_level": level,
        "effective_autonomy_level": level,
        "autonomy_ladder_status": "within_limit",
        "action_kind": action_kind,
        "selected_capability_mode": _selected_capability(action_kind),
        "max_capability_mode": oracle["max_capability"],
        "allowed_runtime_actions": list(oracle["allowed"]),
        "blocked_runtime_actions": list(_blocked_for(level)),
        "human_confirmation_required": confirmation_required,
        "human_confirmation_mode": (
            "explicit_confirmation_required"
            if confirmation_required
            else "not_required"
        ),
        "confirmation_evidence_state": evidence_state,
        "autonomy_validation_errors": [],
    }


def test_policy_vocabulary_and_projections_match_independent_oracle() -> None:
    assert AUTONOMY_ACTION_KINDS == ACTION_KINDS_ORACLE
    for level, oracle in POLICY_ORACLE.items():
        policy = AUTONOMY_LEVEL_POLICIES[level]
        allowed = tuple(policy["allowed_runtime_actions"])
        blocked = tuple(policy["blocked_runtime_actions"])

        assert policy["max_capability_mode"] == oracle["max_capability"]
        assert allowed == oracle["allowed"]
        assert blocked == _blocked_for(level)
        assert set(allowed).isdisjoint(blocked)
        assert set(allowed) | set(blocked) == set(ACTION_KINDS_ORACLE)
        assert {
            "irreversible_action",
            "automatic_promotion",
            "core_mutation",
        }.issubset(blocked)


@pytest.mark.parametrize("level", tuple(POLICY_ORACLE))
def test_derive_autonomy_ladder_projects_each_level(level: str) -> None:
    oracle = POLICY_ORACLE[level]
    ladder = derive_autonomy_ladder(
        contract=_input(requested_level=level, max_level=level),
        plan=_plan(),
    )

    assert ladder.requested_autonomy_level == level
    assert ladder.max_autonomy_level == level
    assert ladder.effective_autonomy_level == level
    assert ladder.autonomy_ladder_status == "within_limit"
    assert ladder.max_capability_mode == oracle["max_capability"]
    assert ladder.allowed_runtime_actions == list(oracle["allowed"])
    assert ladder.blocked_runtime_actions == list(_blocked_for(level))
    assert ladder.human_confirmation_required is oracle["level_confirmation"]
    assert ladder.human_confirmation_mode == (
        "explicit_confirmation_required"
        if oracle["level_confirmation"]
        else "not_required"
    )
    assert ladder.autonomy_validation_errors == []


@pytest.mark.parametrize(
    ("requested_level", "max_level", "expected_error"),
    [
        (None, "bounded_core_action", "requested_autonomy_level_missing"),
        ("", "bounded_core_action", "requested_autonomy_level_missing"),
        (" ", "bounded_core_action", "requested_autonomy_level_unknown"),
        ("future_unbounded", "bounded_core_action", "requested_autonomy_level_unknown"),
        ("bounded_core_action", None, "max_autonomy_level_missing"),
        ("bounded_core_action", "", "max_autonomy_level_missing"),
        ("bounded_core_action", " ", "max_autonomy_level_unknown"),
        ("bounded_core_action", "future_unbounded", "max_autonomy_level_unknown"),
    ],
)
def test_derive_missing_or_unknown_level_is_invalid_assist_only(
    requested_level: str | None,
    max_level: str | None,
    expected_error: str,
) -> None:
    plan = _plan()
    plan.capability_decision_selected_mode = "core_with_local_operation"
    ladder = derive_autonomy_ladder(
        contract=_input(requested_level=requested_level, max_level=max_level),
        plan=plan,
    )

    assert ladder.requested_autonomy_level == "assist_only"
    assert ladder.max_autonomy_level == "assist_only"
    assert ladder.effective_autonomy_level == "assist_only"
    assert ladder.autonomy_ladder_status == "invalid_fail_closed"
    assert expected_error in ladder.autonomy_validation_errors
    assert "execute_reversible_core_action" in ladder.blocked_runtime_actions


def test_derive_accepts_explicit_alias_as_stricter_confirmation() -> None:
    ladder = derive_autonomy_ladder(
        contract=_input(
            requested_level="bounded_core_action",
            max_level="bounded_core_action",
            confirmation_mode="explicit",
        ),
        plan=_plan(),
        action_kind="execute_reversible_core_action",
    )

    assert ladder.autonomy_ladder_status == "within_limit"
    assert ladder.human_confirmation_required is True
    assert ladder.human_confirmation_mode == "explicit_confirmation_required"


@pytest.mark.parametrize(
    ("level", "action_kind"),
    [
        ("bounded_core_action", "prepare_local_action"),
        ("bounded_core_action", "execute_reversible_core_action"),
        ("supervised_external_action", "prepare_external_action"),
        ("supervised_external_action", "execute_external_action"),
    ],
)
def test_derive_missing_confirmation_mode_for_operational_action_fails_closed(
    level: str,
    action_kind: str,
) -> None:
    ladder = derive_autonomy_ladder(
        contract=_input(requested_level=level, max_level=level),
        plan=_plan(),
        action_kind=action_kind,
    )

    assert ladder.requested_autonomy_level == "assist_only"
    assert ladder.max_autonomy_level == "assist_only"
    assert ladder.effective_autonomy_level == "assist_only"
    assert ladder.autonomy_ladder_status == "invalid_fail_closed"
    assert "confirmation_mode_missing_for_effect" in (
        ladder.autonomy_validation_errors
    )


def test_derive_accepts_stricter_planned_confirmation_over_not_required_input() -> None:
    ladder = derive_autonomy_ladder(
        contract=_input(
            requested_level="bounded_core_action",
            max_level="bounded_core_action",
            confirmation_mode="not_required",
        ),
        plan=_plan(request_confirmation_mode="explicit_confirmation_required"),
        action_kind="execute_reversible_core_action",
    )

    assert ladder.autonomy_ladder_status == "within_limit"
    assert ladder.human_confirmation_required is True
    assert ladder.human_confirmation_mode == "explicit_confirmation_required"
    assert ladder.autonomy_validation_errors == []


def test_derive_unknown_planned_confirmation_mode_fails_closed() -> None:
    ladder = derive_autonomy_ladder(
        contract=_input(
            requested_level="bounded_core_action",
            max_level="bounded_core_action",
        ),
        plan=_plan(request_confirmation_mode="silent"),
        action_kind="execute_reversible_core_action",
    )

    assert ladder.autonomy_ladder_status == "invalid_fail_closed"
    assert "request_confirmation_mode_unknown" in ladder.autonomy_validation_errors


@pytest.mark.parametrize(
    ("confirmation_mode", "action_kind", "expected_error"),
    [
        ("silent", None, "autonomy_confirmation_mode_unknown"),
        (None, "future_action", "autonomy_action_kind_unknown"),
    ],
)
def test_derive_unknown_confirmation_or_action_is_invalid_fail_closed(
    confirmation_mode: str | None,
    action_kind: str | None,
    expected_error: str,
) -> None:
    ladder = derive_autonomy_ladder(
        contract=_input(
            requested_level="bounded_core_action",
            max_level="bounded_core_action",
            confirmation_mode=confirmation_mode,
        ),
        plan=_plan(),
        action_kind=action_kind,
    )

    assert ladder.effective_autonomy_level == "assist_only"
    assert ladder.autonomy_ladder_status == "invalid_fail_closed"
    assert expected_error in ladder.autonomy_validation_errors


MATRIX_CASES = [
    (level, action_kind, evidence_state)
    for level in POLICY_ORACLE
    for action_kind in ACTION_KINDS_ORACLE
    for evidence_state in ("absent", "verified", "invalid")
]


@pytest.mark.parametrize(
    ("level", "action_kind", "evidence_state"),
    MATRIX_CASES,
)
def test_evaluate_autonomy_action_total_matrix(
    level: str,
    action_kind: str,
    evidence_state: str,
) -> None:
    oracle = POLICY_ORACLE[level]
    allowed = action_kind in oracle["allowed"]
    confirmation_required = action_kind in oracle["requires_confirmation"]

    decision = evaluate_autonomy_action(
        **_evaluation_kwargs(level, action_kind, evidence_state)
    )

    if not allowed or evidence_state == "invalid":
        expected_decision = "block"
    elif confirmation_required and evidence_state == "absent":
        expected_decision = "require_confirmation"
    else:
        expected_decision = "allow"
    assert decision.decision == expected_decision
    assert decision.side_effect_allowed is (
        expected_decision == "allow" and action_kind in EXECUTION_KINDS_ORACLE
    )
    assert decision.execution_allowed is False
    assert decision.tool_dispatch_allowed is False
    assert decision.runtime_activation_allowed is False
    assert decision.automatic_promotion_allowed is False
    assert decision.core_mutation_allowed is False


ACTION_CAPABILITY_CASES = [
    (level, action_kind, selected_capability_mode)
    for level in POLICY_ORACLE
    for action_kind in ACTION_KINDS_ORACLE
    for selected_capability_mode in CAPABILITY_RANK_ORACLE
]


@pytest.mark.parametrize(
    ("level", "action_kind", "selected_capability_mode"),
    ACTION_CAPABILITY_CASES,
)
def test_evaluate_enforces_literal_action_capability_product(
    level: str,
    action_kind: str,
    selected_capability_mode: str,
) -> None:
    oracle = POLICY_ORACLE[level]
    minimum_rank = ACTION_MIN_CAPABILITY_RANK_ORACLE[action_kind]
    selected_rank = CAPABILITY_RANK_ORACLE[selected_capability_mode]
    max_rank = CAPABILITY_RANK_ORACLE[oracle["max_capability"]]
    action_allowed = action_kind in oracle["allowed"]
    capability_sufficient = (
        minimum_rank is not None
        and minimum_rank <= selected_rank <= max_rank
    )
    values = _evaluation_kwargs(level, action_kind, "verified")
    values["selected_capability_mode"] = selected_capability_mode

    decision = evaluate_autonomy_action(**values)

    expected_decision = (
        "allow" if action_allowed and capability_sufficient else "block"
    )
    assert decision.decision == expected_decision
    assert decision.side_effect_allowed is (
        expected_decision == "allow" and action_kind in EXECUTION_KINDS_ORACLE
    )
    if (
        action_allowed
        and minimum_rank is not None
        and selected_rank < minimum_rank
    ):
        assert "capability_below_action_requirement" in decision.reason_codes


@pytest.mark.parametrize(
    ("field_name", "invalid_value", "expected_reason"),
    [
        ("requested_autonomy_level", None, "requested_autonomy_level_missing"),
        ("max_autonomy_level", "", "max_autonomy_level_missing"),
        ("effective_autonomy_level", "future", "effective_autonomy_level_unknown"),
        ("autonomy_ladder_status", "future", "autonomy_ladder_status_unknown"),
        ("action_kind", None, "autonomy_action_kind_missing"),
        ("action_kind", " ", "autonomy_action_kind_unknown"),
        ("selected_capability_mode", None, "selected_capability_mode_missing"),
        ("selected_capability_mode", "future", "selected_capability_mode_unknown"),
        ("selected_capability_mode", " ", "selected_capability_mode_unknown"),
        ("max_capability_mode", "future", "max_capability_mode_unknown"),
        ("allowed_runtime_actions", None, "allowed_runtime_actions_invalid"),
        ("allowed_runtime_actions", 7, "allowed_runtime_actions_invalid"),
        (
            "blocked_runtime_actions",
            ["core_mutation"],
            "blocked_runtime_actions_projection_mismatch",
        ),
        ("human_confirmation_required", None, "human_confirmation_required_invalid"),
        ("human_confirmation_mode", None, "human_confirmation_mode_missing"),
        ("human_confirmation_mode", "silent", "human_confirmation_mode_unknown"),
        ("human_confirmation_mode", " ", "human_confirmation_mode_unknown"),
        (
            "confirmation_evidence_state",
            "future",
            "confirmation_evidence_state_unknown",
        ),
        (
            "autonomy_validation_errors",
            ["upstream_invalid"],
            "autonomy_validation_errors_present",
        ),
    ],
)
def test_evaluate_blocks_missing_unknown_or_tampered_projection(
    field_name: str,
    invalid_value: object,
    expected_reason: str,
) -> None:
    values = _evaluation_kwargs(
        "bounded_core_action",
        "execute_reversible_core_action",
        "absent",
    )
    values[field_name] = invalid_value

    decision = evaluate_autonomy_action(**values)

    assert decision.decision == "block"
    assert decision.side_effect_allowed is False
    assert expected_reason in decision.reason_codes


def test_evaluate_accepts_stricter_confirmation_for_bounded_action() -> None:
    values = _evaluation_kwargs(
        "bounded_core_action",
        "execute_reversible_core_action",
        "absent",
    )
    values["human_confirmation_required"] = True
    values["human_confirmation_mode"] = "explicit"

    pending = evaluate_autonomy_action(**values)
    values["confirmation_evidence_state"] = "verified"
    verified = evaluate_autonomy_action(**values)

    assert pending.decision == "require_confirmation"
    assert pending.side_effect_allowed is False
    assert verified.decision == "allow"
    assert verified.side_effect_allowed is True


@pytest.mark.parametrize(
    ("required", "mode"),
    [
        (True, "not_required"),
        (False, "explicit_confirmation_required"),
    ],
)
def test_evaluate_blocks_contradictory_confirmation_contract(
    required: bool,
    mode: str,
) -> None:
    values = _evaluation_kwargs(
        "bounded_core_action",
        "execute_reversible_core_action",
        "verified",
    )
    values["human_confirmation_required"] = required
    values["human_confirmation_mode"] = mode

    decision = evaluate_autonomy_action(**values)

    assert decision.decision == "block"
    assert "human_confirmation_contract_contradictory" in decision.reason_codes


def test_capability_comparison_is_total_and_fail_closed() -> None:
    assert CAPABILITY_MODE_ORDER["core_guidance_only"] == 0
    assert CAPABILITY_MODE_ORDER["core_with_local_operation"] == 2
    assert CAPABILITY_MODE_ORDER["core_with_supervised_external_operation"] == 3
    assert capability_mode_exceeds_autonomy_limit(
        selected_mode="core_with_local_operation",
        max_capability_mode="contained_guidance",
    )
    assert capability_mode_exceeds_autonomy_limit(
        selected_mode=None,
        max_capability_mode="contained_guidance",
    )
    assert capability_mode_exceeds_autonomy_limit(
        selected_mode="future",
        max_capability_mode="core_with_local_operation",
    )
    assert capability_mode_exceeds_autonomy_limit(
        selected_mode="core_guidance_only",
        max_capability_mode=None,
    )
    assert not capability_mode_exceeds_autonomy_limit(
        selected_mode="core_guidance_only",
        max_capability_mode="contained_guidance",
    )


def test_confirmation_aliases_are_bounded() -> None:
    assert normalize_autonomy_confirmation_mode("explicit") == (
        "explicit_confirmation_required"
    )
    assert normalize_autonomy_confirmation_mode("bounded_autonomy") == "not_required"
    assert normalize_autonomy_confirmation_mode("conditional_confirmation") is None
    assert normalize_autonomy_confirmation_mode(None) is None


def test_policy_decision_is_frozen_and_schemas_carry_new_contract() -> None:
    decision = evaluate_autonomy_action(
        **_evaluation_kwargs(
            "bounded_core_action",
            "execute_reversible_core_action",
            "absent",
        )
    )

    with pytest.raises(FrozenInstanceError):
        decision.decision = "allow"  # type: ignore[misc]
    assert AUTONOMY_ACTION_POLICY_DECISION_SCHEMA.contract_name == (
        "AutonomyActionPolicyDecisionContract"
    )
    assert "autonomy_action_kind" in AUTONOMY_LADDER_SCHEMA.optional_fields
    assert "autonomy_validation_errors" in AUTONOMY_LADDER_SCHEMA.optional_fields
    assert "autonomy_action_kind" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "autonomy_validation_errors" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "autonomy_action_kind" in OPERATION_DISPATCH_SCHEMA.optional_fields
    assert "autonomy_validation_errors" in OPERATION_DISPATCH_SCHEMA.optional_fields


def test_policy_decision_schema_accepts_allowed_and_fail_closed_results() -> None:
    allowed = evaluate_autonomy_action(
        **_evaluation_kwargs(
            "bounded_core_action",
            "execute_reversible_core_action",
            "absent",
        )
    )
    invalid_values = _evaluation_kwargs(
        "bounded_core_action",
        "execute_reversible_core_action",
        "absent",
    )
    invalid_values["action_kind"] = None
    blocked = evaluate_autonomy_action(**invalid_values)

    assert validate_contract_instance(
        allowed,
        schema=AUTONOMY_ACTION_POLICY_DECISION_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        blocked,
        schema=AUTONOMY_ACTION_POLICY_DECISION_SCHEMA,
    ).status == "coherent"
