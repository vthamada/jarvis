from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from governance_service.service import GovernanceService
from operational_service.service import OperationalExecution, OperationalService

from shared.action_confirmation import action_intent_fingerprint
from shared.contracts import (
    ArtifactLifecycleStateContract,
    MissionStateContract,
    OperationDispatchContract,
    WorkItemStateContract,
)
from shared.types import (
    MissionId,
    MissionStatus,
    OperationId,
    OperationStatus,
    RequestId,
    RiskLevel,
    SessionId,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


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


def autonomy_projection(
    level: str,
    *,
    stricter_confirmation: bool = False,
) -> dict[str, object]:
    policy = {
        "assist_only": {
            "max_capability_mode": "contained_guidance",
            "selected_capability_mode": "contained_guidance",
            "allowed_runtime_actions": AUTONOMY_ACTION_KINDS[:3],
            "confirmation_required": False,
        },
        "confirm_before_action": {
            "max_capability_mode": "core_with_local_operation",
            "selected_capability_mode": "core_with_local_operation",
            "allowed_runtime_actions": AUTONOMY_ACTION_KINDS[:5],
            "confirmation_required": True,
        },
        "bounded_core_action": {
            "max_capability_mode": "core_with_local_operation",
            "selected_capability_mode": "core_with_local_operation",
            "allowed_runtime_actions": AUTONOMY_ACTION_KINDS[:5],
            "confirmation_required": False,
        },
        "supervised_external_action": {
            "max_capability_mode": "core_with_supervised_external_operation",
            "selected_capability_mode": "core_with_local_operation",
            "allowed_runtime_actions": AUTONOMY_ACTION_KINDS[:7],
            "confirmation_required": True,
        },
    }[level]
    allowed_runtime_actions = list(policy["allowed_runtime_actions"])
    confirmation_required = bool(
        policy["confirmation_required"] or stricter_confirmation
    )
    return {
        "requested_autonomy_level": level,
        "max_autonomy_level": level,
        "effective_autonomy_level": level,
        "autonomy_ladder_status": "within_limit",
        "capability_decision_selected_mode": policy["selected_capability_mode"],
        "max_autonomy_capability_mode": policy["max_capability_mode"],
        "autonomy_human_confirmation_required": confirmation_required,
        "autonomy_confirmation_mode": (
            "explicit_confirmation_required"
            if confirmation_required
            else "not_required"
        ),
        "autonomy_action_kind": "execute_reversible_core_action",
        "autonomy_validation_errors": [],
        "autonomy_allowed_runtime_actions": allowed_runtime_actions,
        "autonomy_blocked_runtime_actions": [
            action
            for action in AUTONOMY_ACTION_KINDS
            if action not in allowed_runtime_actions
        ],
    }


def action_dispatch(**overrides: object) -> OperationDispatchContract:
    values: dict[str, object] = {
        "operation_id": OperationId("op-confirmed-action"),
        "request_id": RequestId("req-confirmed-action"),
        "session_id": SessionId("sess-confirmed-action"),
        "task_type": "draft_plan",
        "task_goal": "Create the exact confirmed plan",
        "task_plan": "write one governed text artifact",
        "constraints": ["configured-root-only"],
        "expected_output": "text_brief",
        "operator_identity_ref": "operator://local/tester",
        **autonomy_projection("confirm_before_action"),
    }
    values.update(overrides)
    return OperationDispatchContract(**values)


def claimed_dispatch(
    service: OperationalService,
    dispatch: OperationDispatchContract,
) -> OperationDispatchContract:
    origin_request_id = RequestId("req-confirmed-action-origin")
    intent = service.build_action_intent(
        dispatch,
        origin_request_id=str(origin_request_id),
        nonce="nonce_0123456789abcdef",
    )
    return replace(
        dispatch,
        receipt_id="confirmation-receipt://exact-action/1",
        claim_id="confirmation-claim://exact-action/1",
        origin_request_id=origin_request_id,
        action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        claimed_at="2026-08-29T12:02:00Z",
    )


def test_operational_service_name() -> None:
    assert OperationalService.name == "operational-service"


def test_operational_service_projects_read_only_artifact_registry() -> None:
    mission_id = MissionId("mission-artifact-registry")
    root_ref = "artifact://mission-artifact-registry/plan/v1"
    replacement_ref = "artifact://mission-artifact-registry/plan/v2"
    mission = MissionStateContract(
        mission_id=mission_id,
        mission_goal="Track plan lineage",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T09:00:00+00:00",
        artifact_states=[
            ArtifactLifecycleStateContract(
                artifact_ref=replacement_ref,
                artifact_status="active",
                mission_id=mission_id,
                artifact_version=2,
                owner_mission_id=mission_id,
                lineage_root_ref=root_ref,
                supersedes_artifact_ref=root_ref,
            ),
            ArtifactLifecycleStateContract(
                artifact_ref=root_ref,
                artifact_status="superseded",
                mission_id=mission_id,
                artifact_version=1,
                owner_mission_id=mission_id,
                lineage_root_ref=root_ref,
                replacement_artifact_ref=replacement_ref,
            ),
        ],
    )

    registry = OperationalService.build_artifact_registry(mission)

    assert [item.artifact_version for item in registry.artifact_states] == [1, 2]
    assert registry.active_artifact_refs == [replacement_ref]
    assert registry.superseded_artifact_refs == [root_ref]
    assert registry.read_only is True
    assert registry.external_file_mutation_allowed is False


def test_operational_service_builds_cross_session_daily_workspace() -> None:
    service = OperationalService(
        artifact_dir=str(runtime_dir("operational-daily-workspace"))
    )
    fresh = MissionStateContract(
        mission_id=MissionId("mission-fresh"),
        mission_goal="Continue the current release",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T09:00:00+00:00",
        project_ref="project://release",
        objective_ref="objective://release/controlled",
        objective_status="active",
        work_item_refs=["work-item://release/validate"],
        active_work_items=["work-item://release/validate"],
        artifact_refs=["artifact://release/plan/v1"],
        active_artifact_refs=["artifact://release/plan/v1"],
        next_action_ref="next-action://release/validate",
    )
    stale_blocked = MissionStateContract(
        mission_id=MissionId("mission-stale"),
        mission_goal="Resolve the blocked migration",
        mission_status=MissionStatus.BLOCKED,
        checkpoints=[],
        updated_at="2026-07-12T08:00:00+00:00",
        objective_status="blocked",
        open_checkpoint_refs=["checkpoint://migration/approval"],
    )

    workspace = service.build_daily_operator_workspace(
        mission_states=[stale_blocked, fresh],
        pending_evolution_review_refs=["proposal-001", "proposal-001"],
        pending_memory_review_refs=["memory-candidate-001"],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_id.startswith("daily-workspace://")
    assert workspace.workspace_status == "operator_decision_required"
    assert workspace.mission_count == 2
    assert workspace.active_objective_count == 2
    assert workspace.active_work_item_count == 1
    assert workspace.active_artifact_count == 1
    assert workspace.open_checkpoint_count == 1
    assert workspace.pending_review_count == 2
    assert workspace.stale_mission_count == 1
    assert [str(item.mission_id) for item in workspace.missions] == [
        "mission-fresh",
        "mission-stale",
    ]
    assert workspace.missions[0].freshness_status == "fresh"
    assert workspace.missions[0].next_action_status == "ready"
    assert workspace.missions[1].freshness_status == "stale"
    assert workspace.missions[1].operator_attention_status == "blocked"
    assert workspace.next_operator_decision == (
        "review_evolution_proposal:proposal-001"
    )
    assert "resolve_blocked_mission:mission-stale" in workspace.next_decision_refs
    assert "review_stale_mission:mission-stale" in workspace.next_decision_refs
    assert workspace.ordering_policy == "updated_at_desc_no_priority_inference"
    assert workspace.read_only is True
    assert workspace.autonomous_resume_allowed is False
    assert workspace.autonomous_scheduling_allowed is False
    assert fresh.active_work_items == ["work-item://release/validate"]


def test_operational_service_builds_idle_workspace_without_inventing_work() -> None:
    service = OperationalService(
        artifact_dir=str(runtime_dir("operational-empty-workspace"))
    )

    workspace = service.build_daily_operator_workspace(
        mission_states=[],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_status == "idle"
    assert workspace.mission_count == 0
    assert workspace.next_decision_refs == []
    assert workspace.next_operator_decision is None
    assert workspace.evidence_refs == []


def test_operational_service_requires_decision_for_open_mission_without_next_action() -> None:
    workspace = OperationalService.build_daily_operator_workspace(
        mission_states=[
            MissionStateContract(
                mission_id=MissionId("mission-needs-next-action"),
                mission_goal="Define the next governed action",
                mission_status=MissionStatus.ACTIVE,
                checkpoints=[],
                updated_at="2026-07-17T09:00:00+00:00",
                objective_status="active",
            )
        ],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_status == "operator_decision_required"
    assert workspace.missions[0].operator_attention_status == "decision_required"
    assert workspace.next_operator_decision == (
        "define_next_action:mission-needs-next-action"
    )


def test_operational_service_orders_governed_work_without_execution() -> None:
    mission_id = MissionId("mission-governed-work-order")
    foundation_ref = "work-item://mission-governed-work-order/foundation"
    release_ref = "work-item://mission-governed-work-order/release"
    mission = MissionStateContract(
        mission_id=mission_id,
        mission_goal="Order explicit work",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T09:00:00+00:00",
        objective_status="active",
        work_item_refs=[foundation_ref, release_ref],
        active_work_items=[foundation_ref, release_ref],
        work_items=[
            WorkItemStateContract(
                work_item_ref=release_ref,
                work_item_status="active",
                mission_id=mission_id,
                priority_level="p0",
                dependency_refs=[foundation_ref],
            ),
            WorkItemStateContract(
                work_item_ref=foundation_ref,
                work_item_status="active",
                mission_id=mission_id,
                priority_level="p2",
            ),
        ],
    )

    queue = OperationalService.build_work_item_queue(mission)
    workspace = OperationalService.build_daily_operator_workspace(
        mission_states=[mission],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert [item.work_item_ref for item in queue.ordered_work_items] == [
        foundation_ref,
        release_ref,
    ]
    assert queue.executable_work_item_refs == [foundation_ref]
    assert queue.blocked_work_item_refs == [release_ref]
    assert queue.autonomous_execution_allowed is False
    assert workspace.missions[0].ordered_work_item_refs == [
        foundation_ref,
        release_ref,
    ]
    assert workspace.missions[0].executable_work_item_refs == [foundation_ref]
    assert workspace.next_operator_decision == f"review_blocked_work_items:{mission_id}"


def test_operational_service_blocks_dispatch_above_autonomy_limit() -> None:
    temp_dir = runtime_dir("operational-autonomy-block")
    service = OperationalService(artifact_dir=str(temp_dir))
    projection = autonomy_projection("bounded_core_action")
    projection["max_autonomy_capability_mode"] = "contained_guidance"
    execution = service.execute(
        action_dispatch(
            **projection,
            operation_id=OperationId("op-autonomy-block"),
            request_id=RequestId("req-autonomy-block"),
            session_id=SessionId("sess-autonomy-block"),
            task_goal="Execute local operation",
            task_plan="attempt operation above autonomy limit",
        )
    )

    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
    assert "capability_above_autonomy_limit" in execution.operation_result.errors
    assert "autonomy_action_policy_blocked" in (
        execution.operation_result.governance_flags
    )
    assert execution.operation_result.next_recommendation == "review_dispatch"


def test_operational_service_rejects_caller_artifact_destination_without_writing() -> None:
    configured_root = runtime_dir("operational-configured-root")
    caller_root = configured_root.parent / f"caller-root-{uuid4().hex[:8]}"
    service = OperationalService(artifact_dir=str(configured_root))

    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-caller-destination"),
            request_id=RequestId("req-caller-destination"),
            session_id=SessionId("sess-caller-destination"),
            task_type="draft_plan",
            task_goal="Attempt a caller-selected artifact destination",
            task_plan="write outside the configured root",
            constraints=["bounded"],
            expected_output="text_brief",
            artifact_destination=str(caller_root),
        )
    )

    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
    assert "artifact_destination_not_allowed" in execution.operation_result.errors
    assert not caller_root.exists()
    assert list(configured_root.glob("*.md")) == []


def test_operational_service_builds_action_intent_without_touching_artifact_root() -> None:
    artifact_root = (
        Path(gettempdir())
        / "jarvis-tests"
        / f"read-only-intent-root-{uuid4().hex[:8]}"
    )
    service = OperationalService(
        artifact_dir=str(artifact_root),
        artifact_root_alias="governed-drafts",
    )
    dispatch = action_dispatch()

    intent = service.build_action_intent(
        dispatch,
        nonce="nonce_0123456789abcdef",
    )

    assert intent.target_ref == "artifact-root://governed-drafts"
    assert intent.operation == "execute_reversible_core_action"
    assert intent.handler_version == "legacy-text-writer/v2"
    assert intent.policy_version == "action-confirmation/v2"
    expected_content = service._content_for_dispatch(dispatch)
    assert expected_content is not None
    assert intent.content_digest == sha256(expected_content.encode("utf-8")).hexdigest()
    assert intent.content_digest != intent.precondition_digest
    assert intent.action_fingerprint == service.action_fingerprint_for_dispatch(
        dispatch
    )
    assert service.action_fingerprint_for_dispatch(
        replace(dispatch, request_id=RequestId("req-retry-envelope")),
        origin_request_id=str(dispatch.request_id),
    ) == service.action_fingerprint_for_dispatch(dispatch)
    assert service.action_fingerprint_for_dispatch(
        replace(dispatch, task_plan="write a different artifact")
    ) != intent.action_fingerprint
    assert service.action_fingerprint_for_dispatch(
        replace(dispatch, plan_rationale="materially different rationale")
    ) != intent.action_fingerprint
    assert service.action_fingerprint_for_dispatch(
        replace(dispatch, workflow_profile="different_workflow")
    ) != intent.action_fingerprint
    with pytest.raises(
        ValueError,
        match="action_intent_action_kind_not_supported",
    ):
        service.build_action_intent(
            replace(dispatch, autonomy_action_kind="execute_external_action")
        )
    assert not artifact_root.exists()


def test_operational_service_writes_exact_utf8_bytes_bound_to_intent() -> None:
    artifact_root = runtime_dir("operational-exact-confirmed-bytes")
    service = OperationalService(artifact_dir=str(artifact_root))
    dispatch = action_dispatch(
        **autonomy_projection("bounded_core_action"),
        request_confirmation_mode="not_required",
        task_plan="write line one\nwrite line two",
    )
    expected_content = service._content_for_dispatch(dispatch)
    assert expected_content is not None
    intent = service.build_action_intent(dispatch)

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.COMPLETED
    artifact_path = Path(execution.artifact_results[0].location_ref or "")
    physical_bytes = artifact_path.read_bytes()
    assert physical_bytes == expected_content.encode("utf-8")
    assert sha256(physical_bytes).hexdigest() == intent.content_digest


@pytest.mark.parametrize(
    ("projection_override", "expected_reason"),
    [
        pytest.param(
            {"requested_autonomy_level": None},
            "requested_autonomy_level_missing",
            id="level-missing",
        ),
        pytest.param(
            {"max_autonomy_level": "unknown_level"},
            "max_autonomy_level_unknown",
            id="level-unknown",
        ),
        pytest.param(
            {"effective_autonomy_level": "assist_only"},
            "effective_autonomy_level_mismatch",
            id="level-contradictory",
        ),
        pytest.param(
            {"autonomy_ladder_status": "unknown_status"},
            "autonomy_ladder_status_unknown",
            id="status-unknown",
        ),
        pytest.param(
            {"autonomy_action_kind": None},
            "autonomy_action_kind_missing",
            id="action-missing",
        ),
        pytest.param(
            {"autonomy_action_kind": "unknown_action"},
            "autonomy_action_kind_unknown",
            id="action-unknown",
        ),
        pytest.param(
            {"capability_decision_selected_mode": None},
            "selected_capability_mode_missing",
            id="capability-missing",
        ),
        pytest.param(
            {"capability_decision_selected_mode": "unknown_capability"},
            "selected_capability_mode_unknown",
            id="capability-unknown",
        ),
        pytest.param(
            {"capability_decision_selected_mode": "core_guidance_only"},
            "capability_below_action_requirement",
            id="capability-below-action-requirement",
        ),
        pytest.param(
            {"max_autonomy_capability_mode": "contained_guidance"},
            "capability_above_autonomy_limit",
            id="capability-contradictory",
        ),
        pytest.param(
            {"autonomy_confirmation_mode": None},
            "human_confirmation_mode_missing",
            id="mode-missing",
        ),
        pytest.param(
            {"autonomy_confirmation_mode": "unknown_mode"},
            "human_confirmation_mode_unknown",
            id="mode-unknown",
        ),
        pytest.param(
            {"autonomy_human_confirmation_required": True},
            "human_confirmation_contract_contradictory",
            id="mode-contradictory",
        ),
        pytest.param(
            {"autonomy_allowed_runtime_actions": None},
            "allowed_runtime_actions_invalid",
            id="allowed-list-missing",
        ),
        pytest.param(
            {"autonomy_allowed_runtime_actions": ["unknown_action"]},
            "allowed_runtime_actions_projection_mismatch",
            id="allowed-list-unknown",
        ),
        pytest.param(
            {
                "autonomy_blocked_runtime_actions": [
                    "execute_reversible_core_action"
                ]
            },
            "blocked_runtime_actions_projection_mismatch",
            id="lists-contradictory",
        ),
        pytest.param(
            {"autonomy_validation_errors": ["upstream_projection_invalid"]},
            "autonomy_validation_errors_present",
            id="upstream-validation-error",
        ),
    ],
)
def test_operational_service_blocks_invalid_autonomy_projection_without_artifact(
    projection_override: dict[str, object],
    expected_reason: str,
) -> None:
    artifact_root = runtime_dir("operational-autonomy-negative-matrix")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )
    projection = autonomy_projection("bounded_core_action")
    projection.update(projection_override)

    execution = service.execute(action_dispatch(**projection))

    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
    assert expected_reason in execution.operation_result.errors
    assert "autonomy_action_policy_blocked" in (
        execution.operation_result.governance_flags
    )
    assert verifier_calls == []
    assert list(artifact_root.glob("*.md")) == []


@pytest.mark.parametrize(
    ("level", "stricter_confirmation", "confirmation_required"),
    [
        pytest.param(
            "confirm_before_action",
            False,
            True,
            id="confirm-before-action",
        ),
        pytest.param(
            "bounded_core_action",
            False,
            False,
            id="bounded-without-confirmation",
        ),
        pytest.param(
            "bounded_core_action",
            True,
            True,
            id="bounded-with-stricter-confirmation",
        ),
        pytest.param(
            "supervised_external_action",
            False,
            True,
            id="supervised-local-writer",
        ),
    ],
)
def test_operational_service_executes_supported_action_by_autonomy_level(
    level: str,
    stricter_confirmation: bool,
    confirmation_required: bool,
) -> None:
    artifact_root = runtime_dir(f"operational-autonomy-{level}")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )
    dispatch = action_dispatch(
        **autonomy_projection(
            level,
            stricter_confirmation=stricter_confirmation,
        )
    )
    if confirmation_required:
        dispatch = claimed_dispatch(service, dispatch)

    assert (
        service.action_confirmation_required_for_dispatch(dispatch)
        is confirmation_required
    )
    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.COMPLETED
    assert len(execution.artifact_results) == 1
    assert len(list(artifact_root.glob("*.md"))) == 1
    assert len(verifier_calls) == int(confirmation_required)


def test_operational_service_revalidates_autonomy_immediately_before_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact_root = runtime_dir("operational-final-autonomy-gate")
    service = OperationalService(artifact_dir=str(artifact_root))
    original_decision = service._autonomy_action_decision
    decision_calls = 0

    def changing_decision(
        dispatch: OperationDispatchContract,
        *,
        confirmation_evidence_state: str,
    ) -> object:
        nonlocal decision_calls
        decision_calls += 1
        decision = original_decision(
            dispatch,
            confirmation_evidence_state=confirmation_evidence_state,
        )
        if decision_calls == 2:
            return replace(
                decision,
                decision="block",
                side_effect_allowed=False,
                reason_codes=("autonomy_changed_before_writer",),
            )
        return decision

    monkeypatch.setattr(service, "_autonomy_action_decision", changing_decision)

    execution = service.execute(
        action_dispatch(**autonomy_projection("bounded_core_action"))
    )

    assert decision_calls == 2
    assert execution.operation_result.status == OperationStatus.FAILED
    assert "autonomy_changed_before_writer" in execution.operation_result.errors
    assert execution.artifact_results == []
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_blocks_assist_only_even_with_exact_receipt() -> None:
    artifact_root = runtime_dir("operational-assist-receipt-block")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )
    dispatch = claimed_dispatch(
        service,
        action_dispatch(**autonomy_projection("assist_only")),
    )

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "action_kind_blocked_by_autonomy_level" in (
        execution.operation_result.errors
    )
    assert verifier_calls == []
    assert execution.artifact_results == []
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_rejects_external_action_before_verifier() -> None:
    artifact_root = runtime_dir("operational-external-action-block")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )
    dispatch = replace(
        action_dispatch(**autonomy_projection("supervised_external_action")),
        autonomy_action_kind="execute_external_action",
        capability_decision_selected_mode=(
            "core_with_supervised_external_operation"
        ),
        receipt_id="confirmation-receipt://external/1",
        claim_id="confirmation-claim://external/1",
        origin_request_id=RequestId("req-confirmed-action-origin"),
        action_fingerprint="1" * 64,
        intent_fingerprint="2" * 64,
        claimed_at="2026-08-29T12:02:00Z",
    )

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "operational_action_kind_not_supported" in (
        execution.operation_result.errors
    )
    assert verifier_calls == []
    assert execution.artifact_results == []
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_maps_planning_risk_profiles_fail_closed() -> None:
    service = OperationalService(
        artifact_dir=str(runtime_dir("operational-risk-profile"))
    )
    for profile, expected in (
        ("bounded_confidence", RiskLevel.LOW),
        ("contained_review", RiskLevel.MODERATE),
        ("governed_caution", RiskLevel.MODERATE),
    ):
        intent = service.build_action_intent(
            action_dispatch(request_risk_profile=profile)
        )
        assert intent.risk_level == expected

    explicit = service.build_action_intent(
        action_dispatch(
            risk_hint=RiskLevel.HIGH,
            request_risk_profile="unknown_but_shadowed_by_exact_hint",
        )
    )
    assert explicit.risk_level == RiskLevel.HIGH

    with pytest.raises(
        ValueError,
        match="action_intent_request_risk_profile_unknown",
    ):
        service.build_action_intent(
            action_dispatch(request_risk_profile="unknown_profile")
        )
    with pytest.raises(ValueError, match="action_intent_risk_hint_unknown"):
        service.build_action_intent(
            action_dispatch(risk_hint="unknown_risk")
        )


def test_operational_service_requires_complete_confirmation_before_writing() -> None:
    artifact_root = runtime_dir("operational-missing-confirmation")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )

    execution = service.execute(action_dispatch())

    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
    assert "action_confirmation_claim_incomplete" in execution.operation_result.errors
    assert verifier_calls == []
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_rejects_confirmation_fingerprint_mismatch() -> None:
    artifact_root = runtime_dir("operational-confirmation-mismatch")
    verifier_calls: list[dict[str, object]] = []
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **values: (
            verifier_calls.append(values) or True
        ),
    )
    dispatch = replace(
        claimed_dispatch(service, action_dispatch()),
        action_fingerprint="0" * 64,
    )

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "action_confirmation_action_fingerprint_mismatch" in (
        execution.operation_result.errors
    )
    assert verifier_calls == []
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_fails_closed_when_confirmation_verifier_is_absent() -> None:
    artifact_root = runtime_dir("operational-confirmation-no-verifier")
    service = OperationalService(artifact_dir=str(artifact_root))
    dispatch = claimed_dispatch(service, action_dispatch())

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "action_confirmation_verifier_unavailable" in (
        execution.operation_result.errors
    )
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_fails_closed_when_confirmation_verifier_raises() -> None:
    artifact_root = runtime_dir("operational-confirmation-error")

    def raising_verifier(**_: object) -> bool:
        raise RuntimeError("ledger unavailable")

    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=raising_verifier,
    )
    dispatch = claimed_dispatch(service, action_dispatch())

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "action_confirmation_verifier_error" in execution.operation_result.errors
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_fails_closed_when_confirmation_verifier_returns_false() -> None:
    artifact_root = runtime_dir("operational-confirmation-false")
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=lambda **_: False,
    )
    dispatch = claimed_dispatch(service, action_dispatch())

    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.FAILED
    assert "action_confirmation_verification_failed" in (
        execution.operation_result.errors
    )
    assert list(artifact_root.glob("*.md")) == []


def test_operational_service_allows_one_execution_for_one_verified_claim() -> None:
    artifact_root = runtime_dir("operational-confirmation-single-use")
    ledger_root = runtime_dir("operational-confirmation-ledger")
    governance = GovernanceService(
        action_confirmation_database_path=ledger_root / "confirmation.sqlite3"
    )
    service = OperationalService(
        artifact_dir=str(artifact_root),
        action_confirmation_verifier=governance.verify_action_confirmation_claim,
    )
    dispatch = action_dispatch()
    intent = service.build_action_intent(dispatch)
    challenge = governance.issue_action_confirmation_challenge(
        intent,
        challenged_at=intent.issued_at,
    )
    receipt = governance.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
    )
    claim = governance.claim_action_confirmation(
        receipt.receipt_id,
        operation_id=str(dispatch.operation_id),
        origin_request_id=str(intent.origin_request_id),
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        operator_identity_ref=intent.operator_identity_ref,
    )
    dispatch = replace(
        dispatch,
        receipt_id=receipt.receipt_id,
        claim_id=claim.claim_id,
        origin_request_id=claim.origin_request_id,
        action_fingerprint=claim.action_fingerprint,
        intent_fingerprint=claim.intent_fingerprint,
        claimed_at=claim.claimed_at,
    )

    first = service.execute(dispatch)
    replay = service.execute(dispatch)

    assert first.operation_result.status == OperationStatus.COMPLETED
    assert replay.operation_result.status == OperationStatus.FAILED
    assert "action_confirmation_verification_failed" in replay.operation_result.errors
    assert len(list(artifact_root.glob("*.md"))) == 1


def test_operational_service_preserves_actions_that_do_not_require_confirmation() -> None:
    artifact_root = runtime_dir("operational-no-confirmation-required")
    service = OperationalService(artifact_dir=str(artifact_root))
    dispatch = action_dispatch(
        **autonomy_projection("bounded_core_action"),
        request_confirmation_mode="not_required",
    )

    assert service.action_confirmation_required_for_dispatch(dispatch) is False
    execution = service.execute(dispatch)

    assert execution.operation_result.status == OperationStatus.COMPLETED
    assert len(execution.artifact_results) == 1
    assert len(list(artifact_root.glob("*.md"))) == 1


def test_operational_service_generates_text_artifact_for_supported_task() -> None:
    temp_dir = runtime_dir("operational-artifact")
    service = OperationalService(artifact_dir=str(temp_dir))
    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-1"),
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            task_type="draft_plan",
            task_goal="Plan milestone M3",
            task_plan="priorizar memoria persistente",
            constraints=["low-risk"],
            expected_output="text_brief",
            **autonomy_projection("bounded_core_action"),
            plan_summary="decompor milestone em etapas reversiveis",
            planned_steps=["definir objetivo", "listar etapas"],
            plan_risks=["sem risco material relevante"],
            plan_rationale="contexto=nenhum; apoio=baseline local",
            specialist_summary="encadear o plano em etapas pequenas",
            specialist_findings=["open_loop: fechar checkpoint principal"],
            mind_domain_specialist_contract_status="authoritative_chain",
            mind_domain_specialist_contract_summary=(
                "cadeia soberana autoritativa preserva mente_executiva -> "
                "estrategia_e_pensamento_sistemico -> strategy -> "
                "operational_planning_specialist"
            ),
            mind_domain_specialist_contract_chain=(
                "mente_executiva -> estrategia_e_pensamento_sistemico -> strategy -> "
                "operational_planning_specialist"
            ),
            mind_domain_specialist_active_specialist="operational_planning_specialist",
            mind_domain_specialist_consumer_mode="authoritative_specialist",
            mind_domain_specialist_framing_mode="route_and_specialist_locked",
            mind_domain_specialist_continuity_mode="preserve_authoritative_chain",
            specialist_hints=["operational_planning_specialist"],
            workflow_profile="strategic_direction_workflow",
            workflow_domain_route="strategy",
            workflow_objective="Plan milestone M3",
            workflow_expected_deliverables=[
                "tradeoff_map",
                "decision_criteria",
                "recommended_direction",
            ],
            workflow_telemetry_focus=[
                "tradeoff_clarity",
                "decision_trace",
                "domain_alignment",
            ],
            workflow_success_focus="direcao recomendada com criterios explicitos",
            workflow_response_focus="direcao recomendada, criterios e trade-offs dominantes",
            workflow_state="composed",
            workflow_governance_mode="core_mediated",
            workflow_steps=[
                "structure the goal and success criteria",
                "sequence the smallest safe steps",
                "emit checkpoints and the next safe action",
            ],
            workflow_checkpoints=["goal_structured", "steps_sequenced", "next_action_defined"],
            workflow_decision_points=[
                "goal_scope_confirmed",
                "step_sequence_validated",
                "next_action_governed",
            ],
            ecosystem_state_status="operational_state_attached",
            active_work_items=["mission_task:Plan milestone M3"],
            active_artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
            open_checkpoint_refs=[
                "workflow_checkpoint:goal_structured:pending",
                "workflow_checkpoint:steps_sequenced:pending",
            ],
            surface_presence=["surface:chat", "session:sess-1"],
            ecosystem_state_summary=(
                "work_items=1; artifacts=1; open_checkpoints=2; surfaces=2"
            ),
            project_ref="project://jarvis/persistent-objectives",
            objective_ref="objective://jarvis/persistent-objectives/mb-110",
            work_item_refs=["work-item://mb-110/contracts"],
            checkpoint_refs=["checkpoint://mb-110/contract-ready"],
            artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
            objective_status="active",
            next_action_ref="next-action://mb-110/define-contract",
            success_criteria=["plano deve indicar a menor proxima acao segura"],
            smallest_safe_next_action="definir objetivo",
        )
    )
    assert isinstance(execution, OperationalExecution)
    assert execution.operation_result.status == OperationStatus.COMPLETED
    assert execution.artifact_results
    artifact_path = Path(execution.artifact_results[0].location_ref or "")
    assert artifact_path.exists()
    content = artifact_path.read_text(encoding="utf-8")
    assert "Plano deliberativo para" in content
    assert "Criterios de sucesso" in content
    assert "Workflow: strategic_direction_workflow" in content
    assert "Workflow domain route: strategy" in content
    assert (
        "Workflow deliverables: tradeoff_map; decision_criteria; recommended_direction"
        in content
    )
    assert (
        "Workflow telemetry focus: tradeoff_clarity; decision_trace; domain_alignment"
        in content
    )
    assert "Workflow success focus: direcao recomendada com criterios explicitos" in content
    assert (
        "Workflow response focus: direcao recomendada, criterios e trade-offs dominantes"
        in content
    )
    assert "Workflow steps:" in content
    assert "Workflow governance: core_mediated" in content
    assert "Workflow decision points:" in content
    assert "Mind-domain-specialist status: authoritative_chain" in content
    assert "Mind-domain-specialist consumer mode: authoritative_specialist" in content
    assert "Mind-domain-specialist framing mode: route_and_specialist_locked" in content
    assert "Ecosystem state status: operational_state_attached" in content
    assert "Active work items: mission_task:Plan milestone M3" in content
    assert "Open checkpoint refs:" in content
    assert "Surface presence: surface:chat; session:sess-1" in content
    assert "Project objective status: active" in content
    assert "Project ref: project://jarvis/persistent-objectives" in content
    assert "Objective ref: objective://jarvis/persistent-objectives/mb-110" in content
    assert "Next action ref: next-action://mb-110/define-contract" in content
    assert "Ajuste interno" in content
    assert execution.operation_result.workflow_domain_route == "strategy"
    assert execution.operation_result.workflow_state == "completed"
    assert execution.operation_result.workflow_completed_steps == [
        "structure the goal and success criteria",
        "sequence the smallest safe steps",
        "emit checkpoints and the next safe action",
    ]
    assert execution.operation_result.workflow_decisions == [
        "goal_scope_confirmed",
        "step_sequence_validated",
        "next_action_governed",
    ]
    assert "workflow_route:strategy" in execution.operation_result.checkpoints
    assert "workflow:goal_structured" in execution.operation_result.checkpoints
    assert "workflow_state:completed" in execution.operation_result.checkpoints
    assert execution.operation_result.ecosystem_state_status == (
        "operational_state_attached"
    )
    assert execution.operation_result.active_work_items == [
        "mission_task:Plan milestone M3"
    ]
    assert "artifact://procedural/strategy/milestone-plan/v1" in (
        execution.operation_result.active_artifact_refs
    )
    assert execution.operation_result.surface_presence == ["surface:chat", "session:sess-1"]
    assert execution.operation_result.project_ref == "project://jarvis/persistent-objectives"
    assert execution.operation_result.objective_ref == (
        "objective://jarvis/persistent-objectives/mb-110"
    )
    assert execution.operation_result.objective_status == "completed"
    assert execution.operation_result.next_action_ref == (
        "next-action://mb-110/define-contract"
    )


def test_operational_service_fails_for_unsupported_task() -> None:
    temp_dir = runtime_dir("operational-fail")
    service = OperationalService(artifact_dir=str(temp_dir))
    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-2"),
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            task_type="unknown_task",
            task_goal="Do something unsupported",
            task_plan="n/a",
            constraints=["low-risk"],
            expected_output="text_brief",
        )
    )
    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
