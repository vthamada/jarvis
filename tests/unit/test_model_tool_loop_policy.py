"""Exact read-only tool policy, using a plan and identity from the real local Core.

No model, report adapter, filesystem executor or external policy provider is used.
An assessment is not an executable grant; Core still binds and consumes the exact
authorization immediately before its bounded reader.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from apps.jarvis_console.memory_recall_pilot import PilotContext
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_tool_loop import ToolCall, ToolLoopContext, call_fingerprint
from shared.types import PermissionDecision

QUERY = "Compare documentation and observability pilot reports."
RESOURCES = ("documentation", "observability")


@pytest.fixture
def policy_case(tmp_path, monkeypatch):
    core = _isolated_core(tmp_path)
    contract = PilotContext("tool-policy-subject", "tool-policy-session").input(
        "tool-policy-request", QUERY
    )
    contract = replace(contract, user_id=contract.canonical_user_ref)
    inputs = []
    compose = core.synthesis_engine.compose_result

    def capture(value):
        inputs.append(value)
        return compose(value)

    monkeypatch.setattr(core.synthesis_engine, "compose_result", capture)
    response = core.handle_input(contract)
    assert response.governance_decision.decision == PermissionDecision.ALLOW
    assert response.deliberative_plan.capability_decision_selected_mode == "core_guidance_only"
    assert core.model_tool_loop is None
    value = inputs[-1]
    return SimpleNamespace(
        core=core,
        contract=contract,
        context=ToolLoopContext(
            request_id=str(contract.request_id), query=QUERY,
            binding_id="a" * 64, resource_ids=RESOURCES,
        ),
        call=ToolCall("call-1", "read_local_report", "documentation"),
        plan=response.deliberative_plan,
        identity_mode=value.identity_mode,
        identity_signature=value.identity_profile.identity_signature,
        response_style=value.response_style,
    )


def _assess(case, **changes):
    arguments = {
        "context": case.context,
        "call": case.call,
        "plan": case.plan,
        "approved_resource_ids": RESOURCES,
        "requested_by_service": case.core.name,
        "identity_mode": case.identity_mode,
        "identity_signature": case.identity_signature,
        "response_style": case.response_style,
    }
    arguments.update(changes)
    return case.core.governance_service.assess_model_tool_call(case.contract, **arguments)


def test_exact_tool_policy_has_its_own_subject_and_binds_the_actual_call(policy_case):
    assessment = _assess(policy_case)
    check = assessment.governance_check
    decision = assessment.governance_decision
    assert decision.decision == PermissionDecision.ALLOW
    assert check.subject_type == "model_tool_call"
    assert check.subject_action == "read_local_report"
    assert check.proposed_effect == "read_host_selected_local_report"
    assert check.context["request_id"] == str(policy_case.contract.request_id)
    assert check.context["request_decision_id"]
    assert check.context["host_selected"] is check.context["read_only"] is True
    assert check.context["tool"] == policy_case.call.tool
    assert check.context["call_id"] == policy_case.call.call_id
    assert check.context["resource_id"] == policy_case.call.resource_id
    assert check.context["call_fingerprint"] == call_fingerprint(
        policy_case.context, policy_case.call
    )
    assert decision.governance_check_id == check.governance_check_id
    assert decision.requires_audit is True
    second_call = replace(policy_case.call, call_id="call-2", resource_id="observability")
    second = _assess(policy_case, call=second_call)
    assert second.governance_decision.decision == PermissionDecision.ALLOW
    assert second.governance_check.context["call_fingerprint"] == call_fingerprint(
        policy_case.context, second_call
    )
    assert second.governance_check.context["call_fingerprint"] != check.context["call_fingerprint"]


@pytest.mark.parametrize(
    "scope_change",
    [
        "unselected_resource", "write_tool", "foreign_request", "foreign_query",
        "invalid_binding", "short_binding", "different_catalog", "unapproved_catalog",
        "duplicate_catalog", "list_catalog", "empty_catalog",
    ],
)
def test_tool_scope_and_context_mismatch_are_blocked(policy_case, scope_change):
    context = policy_case.context
    call = policy_case.call
    approved = RESOURCES
    if scope_change == "unselected_resource":
        call = replace(call, resource_id="not_selected")
    elif scope_change == "write_tool":
        call = replace(call, tool="execute_local_text_file")
    elif scope_change == "foreign_request":
        context = replace(context, request_id="foreign-request")
    elif scope_change == "foreign_query":
        context = replace(context, query="Compare unrelated reports.")
    elif scope_change == "invalid_binding":
        context = replace(context, binding_id="z" * 64)
    elif scope_change == "short_binding":
        context = replace(context, binding_id="a" * 63)
    elif scope_change == "different_catalog":
        context = replace(context, resource_ids=("documentation",))
    elif scope_change == "unapproved_catalog":
        approved = ("not_selected",)
    elif scope_change == "duplicate_catalog":
        approved = ("documentation", "documentation")
        context = replace(context, resource_ids=approved)
    elif scope_change == "list_catalog":
        approved = list(RESOURCES)
    elif scope_change == "empty_catalog":
        approved = ()
        context = replace(context, resource_ids=())
    assessment = _assess(
        policy_case, context=context, call=call, approved_resource_ids=approved
    )
    assert assessment.governance_decision.decision == PermissionDecision.BLOCK
    assert assessment.governance_check.context["host_selected"] is False
    assert assessment.governance_check.context["tool"] is None
    assert assessment.governance_check.context["call_id"] is None
    assert assessment.governance_check.context["resource_id"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"capability_decision_selected_mode": "operational_execution"},
        {"capability_decision_selected_capabilities": [
            "core_reasoning", "execute_external_action",
        ]},
        {"requires_human_validation": True},
        {"autonomy_human_confirmation_required": True},
        {"autonomy_confirmation_mode": "explicit_confirmation_required"},
        {"objective_status": "blocked"},
        {"objective_status": "completed"},
    ],
)
def test_effectful_confirmation_or_inactive_plan_cannot_authorize_a_tool(policy_case, change):
    assessment = _assess(policy_case, plan=replace(policy_case.plan, **change))
    assert assessment.governance_decision.decision == PermissionDecision.BLOCK
    assert assessment.governance_check.context["host_selected"] is False


@pytest.mark.parametrize(
    "parent_decision,expected",
    [
        (PermissionDecision.BLOCK, PermissionDecision.BLOCK),
        (PermissionDecision.DEFER_FOR_VALIDATION, PermissionDecision.DEFER_FOR_VALIDATION),
        (PermissionDecision.ALLOW_WITH_CONDITIONS, PermissionDecision.BLOCK),
    ],
)
def test_parent_policy_veto_or_conditional_allow_is_never_promoted_to_tool_allow(
    policy_case, monkeypatch, parent_decision, expected
):
    assess = policy_case.core.governance_service.assess_request
    parent_checks = []

    def changed_parent_policy(*args, **kwargs):
        parent = assess(*args, **kwargs)
        assert parent.governance_decision.decision == PermissionDecision.ALLOW
        parent_checks.append(parent.governance_check)
        return replace(
            parent,
            governance_decision=replace(parent.governance_decision, decision=parent_decision),
        )

    monkeypatch.setattr(
        policy_case.core.governance_service, "assess_request", changed_parent_policy
    )
    assessment = _assess(policy_case)
    assert len(parent_checks) == 1
    assert parent_checks[0].subject_type == "request"
    assert assessment.governance_check.subject_type == "model_tool_call"
    assert assessment.governance_decision.decision == expected


@pytest.mark.parametrize("private", ["password=synthetic-policy-secret", r"C:\private\report.txt"])
@pytest.mark.parametrize(
    "field",
    ["tool", "call_id", "resource_id", "query", "binding_id", "request_id", "catalog"],
)
def test_invalid_call_and_context_are_blocked_without_echoing_private_values(
    policy_case, private, field
):
    call = policy_case.call
    context = policy_case.context
    if field in {"tool", "call_id", "resource_id"}:
        call = replace(call, **{field: private})
    elif field == "catalog":
        context = replace(context, resource_ids=(private,))
    else:
        context = replace(context, **{field: private})
    assessment = _assess(policy_case, context=context, call=call)
    assert assessment.governance_decision.decision == PermissionDecision.BLOCK
    assert assessment.governance_check.context["host_selected"] is False
    serialized = json.dumps(asdict(assessment), default=str)
    assert private not in serialized
    assert json.dumps(private)[1:-1] not in serialized
    for field_name in ("tool", "call_id", "resource_id"):
        assert assessment.governance_check.context[field_name] is None
