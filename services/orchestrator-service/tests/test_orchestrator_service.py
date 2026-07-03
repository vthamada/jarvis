from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorResponse, OrchestratorService
from specialist_engine.engine import SpecialistReview
from synthesis_engine.engine import SynthesisResult

from shared.contracts import (
    DeliberativePlanContract,
    ExperienceRecordContract,
    InputContract,
    PostTaskReflectionContract,
    ReviewedLearningGuidanceContract,
)
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    OperationStatus,
    PermissionDecision,
    RequestId,
    SessionId,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_orchestrator_service_name() -> None:
    assert OrchestratorService.name == "orchestrator-service"


def test_orchestrator_transitions_work_item_through_governed_core() -> None:
    temp_dir = runtime_dir("orchestrator-work-item")
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    mission_id = "mission-orchestrator-work-item"
    service.handle_input(
        InputContract(
            request_id=RequestId("req-orchestrator-work-item"),
            session_id=SessionId("sess-orchestrator-work-item"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content="Plan the controlled rollout.",
            timestamp="2026-05-18T00:00:00Z",
        )
    )

    created = service.transition_work_item(
        mission_id=mission_id,
        work_item_ref="work-item://mission-orchestrator-work-item/validate-plan",
        transition="create",
        session_id="sess-orchestrator-work-item",
        next_action_ref="next_action:validate-plan",
    )
    completed = service.transition_work_item(
        mission_id=mission_id,
        work_item_ref="work-item://mission-orchestrator-work-item/validate-plan",
        transition="complete",
        session_id="sess-orchestrator-work-item",
    )
    mission_state = service.memory_service.get_mission_state(mission_id)
    event_names = [
        event.event_name for event in service.observability_service.list_recent_events()
    ]

    assert created.status == "updated"
    assert created.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert created.work_item_state is not None
    assert created.work_item_state.work_item_status == "active"
    assert completed.status == "updated"
    assert completed.work_item_state is not None
    assert completed.work_item_state.work_item_status == "completed"
    assert mission_state is not None
    assert (
        "work-item://mission-orchestrator-work-item/validate-plan"
        in mission_state.work_item_refs
    )
    assert (
        "work-item://mission-orchestrator-work-item/validate-plan"
        not in mission_state.active_work_items
    )
    assert "work_item_state_changed" in event_names
    assert "mission_updated" in event_names


def test_orchestrator_transitions_artifact_lifecycle_through_governed_core() -> None:
    temp_dir = runtime_dir("orchestrator-artifact-lifecycle")
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    mission_id = "mission-orchestrator-artifact"
    service.handle_input(
        InputContract(
            request_id=RequestId("req-orchestrator-artifact"),
            session_id=SessionId("sess-orchestrator-artifact"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content="Plan the controlled rollout.",
            timestamp="2026-05-18T00:00:00Z",
        )
    )

    registered = service.transition_artifact_lifecycle(
        mission_id=mission_id,
        artifact_ref="artifact://mission-orchestrator-artifact/plan/v1",
        transition="register",
        session_id="sess-orchestrator-artifact",
        artifact_version=1,
        rollback_plan_ref="rollback://mission-orchestrator-artifact/plan/v1",
    )
    replaced = service.transition_artifact_lifecycle(
        mission_id=mission_id,
        artifact_ref="artifact://mission-orchestrator-artifact/plan/v1",
        transition="replace",
        session_id="sess-orchestrator-artifact",
        artifact_version=2,
        replacement_artifact_ref="artifact://mission-orchestrator-artifact/plan/v2",
        rollback_plan_ref="rollback://mission-orchestrator-artifact/plan/v1",
    )
    mission_state = service.memory_service.get_mission_state(mission_id)
    event_names = [
        event.event_name for event in service.observability_service.list_recent_events()
    ]

    assert registered.status == "updated"
    assert registered.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert registered.artifact_state is not None
    assert registered.artifact_state.artifact_status == "active"
    assert replaced.status == "updated"
    assert replaced.artifact_state is not None
    assert replaced.artifact_state.replacement_artifact_ref == (
        "artifact://mission-orchestrator-artifact/plan/v2"
    )
    assert mission_state is not None
    assert "artifact://mission-orchestrator-artifact/plan/v2" in mission_state.artifact_refs
    assert (
        "artifact://mission-orchestrator-artifact/plan/v2"
        in mission_state.active_artifact_refs
    )
    assert (
        "artifact://mission-orchestrator-artifact/plan/v1"
        not in mission_state.active_artifact_refs
    )
    assert "artifact_lifecycle_state_changed" in event_names
    assert "mission_updated" in event_names


def test_orchestrator_inspects_long_horizon_goal_strategy_read_only() -> None:
    temp_dir = runtime_dir("orchestrator-long-horizon")
    service = OrchestratorService(
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(
            artifact_dir=str(temp_dir / "artifacts")
        ),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    mission_id = "mission-orchestrator-long-horizon"
    service.handle_input(
        InputContract(
            request_id=RequestId("req-orchestrator-long-horizon"),
            session_id=SessionId("sess-orchestrator-long-horizon"),
            mission_id=MissionId(mission_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content="Plan the controlled rollout.",
            timestamp="2026-05-20T00:00:00Z",
        )
    )
    service.transition_work_item(
        mission_id=mission_id,
        work_item_ref="work-item://mission-orchestrator-long-horizon/validate-plan",
        transition="create",
        session_id="sess-orchestrator-long-horizon",
        next_action_ref="next_action:operator-review",
    )
    service.transition_artifact_lifecycle(
        mission_id=mission_id,
        artifact_ref="artifact://mission-orchestrator-long-horizon/plan/v1",
        transition="register",
        session_id="sess-orchestrator-long-horizon",
        artifact_version=1,
    )

    result = service.inspect_long_horizon_goal_strategy(
        mission_id=mission_id,
        session_id="sess-orchestrator-long-horizon",
    )

    assert result.status == "ready"
    assert result.strategy is not None
    assert result.strategy.memory_write_mode == "read_only"
    assert result.strategy.autonomous_scheduling_allowed is False
    assert result.strategy.next_action_ref == "next_action:operator-review"
    assert result.events[0].event_name == "long_horizon_goal_strategy_declared"
    assert result.events[0].payload["memory_write_mode"] == "read_only"
    assert result.events[0].payload["autonomous_scheduling_allowed"] is False


def test_orchestrator_service_surfaces_adaptive_intervention_payload_from_synthesis() -> None:
    payload = OrchestratorService._adaptive_intervention_response_payload(
        synthesis_result=SynthesisResult(
            response_text="ok",
            output_validation_status="coherent",
            output_validation_errors=[],
            output_validation_retry_applied=False,
            workflow_output_status="coherent",
            workflow_output_errors=[],
            adaptive_intervention_workflow_priority_summary=(
                "workflow strategic direction workflow priorizou specialist "
                "reevaluation para proteger direcao recomendada, criterios e "
                "trade-offs dominantes, preservando checkpoint scenario framed "
                "e gate scenario scope confirmed"
            ),
            adaptive_intervention_preserved_checkpoint="scenario framed",
            adaptive_intervention_preserved_gate="scenario scope confirmed",
        )
    )

    assert payload["adaptive_intervention_workflow_priority_summary"]
    assert payload["adaptive_intervention_preserved_checkpoint"] == "scenario framed"
    assert payload["adaptive_intervention_preserved_gate"] == "scenario scope confirmed"


def test_orchestrator_service_handles_unitary_deliberative_planning() -> None:
    temp_dir = runtime_dir("orchestrator-low")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the first milestone.",
            timestamp="2026-03-17T00:00:00Z",
            surface_id="surface://jarvis_console",
            surface_kind="console",
            surface_session_id="sess-1",
            surface_capability_scope=["text_input"],
            operator_identity_ref="operator://local_console",
            canonical_user_ref="user://local_operator",
        )
    )
    assert isinstance(result, OrchestratorResponse)
    assert result.intent == "planning"
    assert result.directive.identity_mode == "structured_planning"
    assert result.directive.requires_clarification is False
    assert result.deliberative_plan.recommended_task_type == "draft_plan"
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.operation_result is not None
    assert result.operation_result.status == OperationStatus.COMPLETED
    assert result.operation_dispatch is not None
    assert (
        result.operation_dispatch.capability_decision_selected_mode
        == "core_with_local_operation"
    )
    assert (
        result.operation_dispatch.capability_decision_authorization_status
        == "authorized_with_conditions"
    )
    assert result.operation_dispatch.request_identity_status == "resolved"
    assert result.operation_dispatch.request_active_mission
    assert result.operation_dispatch.request_executive_posture == "structured_planning"
    assert result.operation_dispatch.request_authority_level == "bounded_execution"
    assert result.operation_dispatch.request_risk_profile == "governed_caution"
    assert (
        result.operation_dispatch.request_reversibility_mode
        == "prefer_reversible_change"
    )
    assert (
        result.operation_dispatch.request_confirmation_mode
        == "explicit_confirmation_required"
    )
    assert result.operation_dispatch.request_identity_summary
    assert result.operation_dispatch.request_identity_policy_refs == [
        "policy://request-identity/default"
    ]
    assert result.operation_dispatch.surface_id == "surface://jarvis_console"
    assert result.operation_dispatch.surface_kind == "console"
    assert result.operation_dispatch.surface_session_id == "sess-1"
    assert result.operation_dispatch.surface_capability_scope == ["text_input"]
    assert result.operation_dispatch.operator_identity_ref == "operator://local_console"
    assert result.operation_dispatch.canonical_user_ref == "user://local_operator"
    assert result.operation_dispatch.surface_continuity_status == "single_surface"
    input_event = next(event for event in result.events if event.event_name == "input_received")
    assert input_event.payload["surface_id"] == "surface://jarvis_console"
    assert input_event.payload["surface_kind"] == "console"
    assert input_event.payload["surface_continuity_status"] == "single_surface"
    for event_name in {
        "workflow_composed",
        "operation_dispatched",
        "response_synthesized",
        "memory_recorded",
    }:
        event = next(event for event in result.events if event.event_name == event_name)
        assert event.payload["surface_id"] == "surface://jarvis_console"
        assert event.payload["surface_kind"] == "console"
        assert event.payload["surface_session_id"] == "sess-1"
        assert event.payload["operator_identity_ref"] == "operator://local_console"
        assert event.payload["canonical_user_ref"] == "user://local_operator"
        assert event.payload["surface_continuity_status"] == "single_surface"
    assert result.operation_result.surface_id == "surface://jarvis_console"
    assert result.operation_dispatch.capability_decision_tool_class == "local_artifact_generation"
    assert result.operation_dispatch.canonical_domain_hints
    assert result.operation_dispatch.primary_canonical_domain == "estrategia_e_pensamento_sistemico"
    assert result.operation_dispatch.workflow_expected_deliverables == [
        "tradeoff_map",
        "decision_criteria",
        "recommended_direction",
    ]
    assert (
        result.operation_dispatch.mind_domain_specialist_contract_status
        == "authoritative_chain"
    )
    assert (
        result.operation_dispatch.mind_domain_specialist_consumer_mode
        == "authoritative_specialist"
    )
    assert (
        result.operation_dispatch.mind_domain_specialist_framing_mode
        == "route_and_specialist_locked"
    )
    assert (
        result.operation_dispatch.mind_domain_specialist_continuity_mode
        == "preserve_authoritative_chain"
    )
    assert result.operation_dispatch.specialist_hints == ["structured_analysis_specialist"]
    assert result.operation_dispatch.workflow_telemetry_focus == [
        "tradeoff_clarity",
        "decision_trace",
        "domain_alignment",
    ]
    assert (
        result.operation_dispatch.workflow_success_focus
        == "direcao recomendada com criterios explicitos"
    )
    assert (
        result.operation_dispatch.workflow_response_focus
        == "direcao recomendada, criterios e trade-offs dominantes"
    )
    assert result.operation_dispatch.workflow_objective == (
        "clarificar trade-offs estratégicos, enquadramento de cenário e direção recomendada"
    )
    assert result.operation_dispatch.expected_output == "tradeoff_map"
    assert result.operation_dispatch.ecosystem_state_status in {
        "operational_state_attached",
        "partial_operational_state",
    }
    assert result.operation_dispatch.active_work_items
    assert result.operation_dispatch.open_checkpoint_refs
    assert "surface:chat" in result.operation_dispatch.surface_presence
    assert result.operation_dispatch.project_ref == "project:mission:req-1"
    assert result.operation_dispatch.objective_ref == "objective:mission:req-1"
    assert result.operation_dispatch.work_item_refs
    assert result.operation_dispatch.checkpoint_refs
    assert result.operation_dispatch.objective_status in {
        "active",
        "requires_operator_decision",
    }
    assert result.operation_dispatch.next_action_ref
    assert result.operation_result is not None
    assert result.operation_result.ecosystem_state_status == "operational_state_attached"
    assert result.operation_result.active_artifact_refs
    assert result.operation_result.project_ref == result.operation_dispatch.project_ref
    assert result.operation_result.objective_ref == result.operation_dispatch.objective_ref
    assert result.operation_result.work_item_refs == result.operation_dispatch.work_item_refs
    assert result.operation_result.objective_status == "completed"
    assert result.knowledge_result is not None
    assert result.artifact_results
    assert result.active_domains == ["strategy", "documentation", "observability"]
    assert result.cognitive_tensions
    assert result.specialist_review is not None
    assert result.specialist_review.contributions
    assert result.deliberative_plan.canonical_domains
    assert result.deliberative_plan.primary_canonical_domain == "estrategia_e_pensamento_sistemico"
    assert result.deliberative_plan.primary_mind is not None
    assert result.deliberative_plan.primary_mind_family is not None
    assert result.deliberative_plan.primary_domain_driver == "estrategia_e_pensamento_sistemico"
    assert result.deliberative_plan.arbitration_source == "mind_registry"
    assert result.deliberative_plan.primary_route == "strategy"
    assert result.deliberative_plan.route_consumer_profile == "strategy_tradeoff_review"
    assert result.deliberative_plan.route_workflow_profile == "strategic_direction_workflow"
    assert result.deliberative_plan.capability_decision_status == "resolved"
    assert result.deliberative_plan.capability_decision_selected_mode == "core_with_local_operation"
    assert (
        result.deliberative_plan.capability_decision_authorization_status
        == "governance_review_required"
    )
    assert result.deliberative_plan.request_identity_status == "resolved"
    assert result.deliberative_plan.request_active_mission
    assert result.deliberative_plan.request_executive_posture == "structured_planning"
    assert result.deliberative_plan.request_authority_level == "bounded_execution"
    assert result.deliberative_plan.request_risk_profile == "governed_caution"
    assert (
        result.deliberative_plan.request_reversibility_mode
        == "prefer_reversible_change"
    )
    assert (
        result.deliberative_plan.request_confirmation_mode
        == "explicit_confirmation_required"
    )
    assert result.deliberative_plan.request_identity_summary
    assert result.deliberative_plan.request_identity_policy_refs == [
        "policy://request-identity/default"
    ]
    assert "tradeoff_map" in result.deliberative_plan.route_expected_deliverables
    assert "tradeoff_clarity" in result.deliberative_plan.route_telemetry_focus
    assert result.deliberative_plan.open_loops
    assert result.specialist_invocations
    assert result.specialist_boundary_summary is not None
    assert result.deliberative_plan.specialist_resolution_summary is not None
    assert "Contribuicoes especialistas" not in result.response_text
    assert result.experience_record is not None
    assert result.experience_record.mission_id == MissionId("mission:req-1")
    assert result.experience_record.user_intent == "planning"
    assert result.experience_record.route == "strategy"
    assert result.experience_record.workflow_profile == "strategic_direction_workflow"
    assert result.experience_record.primary_mind == result.deliberative_plan.primary_mind
    assert (
        result.experience_record.primary_domain_driver
        == "estrategia_e_pensamento_sistemico"
    )
    assert result.experience_record.specialist_used == [
        "structured_analysis_specialist"
    ]
    assert result.experience_record.plan_summary == result.deliberative_plan.plan_summary
    assert result.experience_record.execution_summary.startswith("operation completed")
    assert result.experience_record.outcome == "coherent"
    assert "local_artifact_generation" in result.experience_record.tools_used
    assert result.experience_record.checkpoints
    assert result.experience_record.evidence_refs == [
        "trace://request/req-1",
        f"memory://record/{result.memory_record.memory_record_id}",
    ]
    stored_experiences = service.memory_service.list_experience_reflections(
        mission_id="mission:req-1"
    )
    assert stored_experiences[0].experience.experience_id == (
        "experience://mission:req-1/req-1"
    )
    assert stored_experiences[0].reflection is not None
    assert stored_experiences[0].reflection.reflection_status == "candidate"
    assert stored_experiences[0].reflection.human_review_required is True
    assert stored_experiences[0].reflection.automatic_promotion_allowed is False
    assert stored_experiences[0].reflection.core_mutation_allowed is False
    assert result.post_task_reflection is not None
    assert result.post_task_reflection.experience_id == result.experience_record.experience_id
    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-1", limit=50)
    )
    event_names = [event.event_name for event in stored_events]
    assert event_names == [event.event_name for event in result.events]
    assert "directive_composed" in event_names
    assert "continuity_subflow_completed" in event_names
    assert "plan_built" in event_names
    assert "continuity_decided" in event_names
    assert "specialist_selection_decided" in event_names
    assert "specialist_shared_memory_linked" in event_names
    assert "specialist_contracts_composed" in event_names
    assert "specialist_handoff_governed" in event_names
    assert "specialist_subflow_completed" in event_names
    assert "workflow_composed" in event_names
    assert "workflow_governance_declared" in event_names
    assert "specialists_completed" in event_names
    assert "plan_refined" in event_names
    assert "plan_governed" in event_names
    assert "experience_record_declared" in event_names
    assert "post_task_reflection_declared" in event_names
    experience_event = next(
        event for event in stored_events if event.event_name == "experience_record_declared"
    )
    assert experience_event.payload["experience_id"] == "experience://mission:req-1/req-1"
    assert experience_event.payload["automatic_promotion_allowed"] is False
    assert experience_event.payload["core_mutation_allowed"] is False
    reflection_event = next(
        event for event in stored_events if event.event_name == "post_task_reflection_declared"
    )
    assert reflection_event.payload["reflection_status"] == "candidate"
    assert reflection_event.payload["human_review_required"] is True
    assert reflection_event.payload["automatic_promotion_allowed"] is False
    assert reflection_event.payload["core_mutation_allowed"] is False
    assert result.specialist_handoff_check is not None
    assert result.specialist_handoff_decision is not None
    assert result.specialist_handoff_decision.decision == PermissionDecision.ALLOW
    registry_event = next(
        event for event in stored_events if event.event_name == "domain_registry_resolved"
    )
    assert registry_event.payload["primary_canonical_domain"] == "estrategia_e_pensamento_sistemico"
    assert registry_event.payload["route_maturity"]["strategy"] == "active_specialist"
    assert (
        registry_event.payload["linked_specialist_type"]["strategy"]
        == "structured_analysis_specialist"
    )
    continuity_event = next(
        event for event in stored_events if event.event_name == "continuity_subflow_completed"
    )
    assert continuity_event.payload["runtime_mode"] == "native_pipeline"
    assert continuity_event.payload["subflow_name"] == "continuity_stateful"
    specialist_subflow_event = next(
        event for event in stored_events if event.event_name == "specialist_subflow_completed"
    )
    assert specialist_subflow_event.payload["runtime_mode"] == "native_pipeline"
    assert specialist_subflow_event.payload["subflow_name"] == "specialist_handoffs"
    assert specialist_subflow_event.payload["selection_status"] == "selected"
    assert specialist_subflow_event.payload["governance_status"] == "approved"
    assert specialist_subflow_event.payload["completion_status"] == "completed"
    assert registry_event.payload["specialist_mode"]["strategy"] == "guided"
    assert registry_event.payload["workflow_profile"]["strategy"] == "strategic_direction_workflow"
    assert (
        registry_event.payload["promoted_route_registry"]["strategy"]["linked_specialist_type"]
        == "structured_analysis_specialist"
    )
    assert registry_event.payload["promoted_route_registry"]["strategy"]["eligible"] is True


def test_orchestrator_service_applies_relevant_post_task_reflection() -> None:
    temp_dir = runtime_dir("orchestrator-reflection-influence")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    service.memory_service.record_experience_reflection(
        experience=ExperienceRecordContract(
            experience_id="experience://mission-reflection/seed",
            mission_id=MissionId("mission-reflection"),
            workflow_profile="strategic_direction_workflow",
            outcome_status="completed",
            route="strategy",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            evidence_refs=["trace://request/seed"],
            timestamp="2026-05-17T00:00:00Z",
        ),
        reflection=PostTaskReflectionContract(
            reflection_id="reflection://mission-reflection/seed",
            experience_id="experience://mission-reflection/seed",
            reflection_status="candidate",
            learning_candidate="prior planning worked when review stayed bounded",
            recommendation="keep the observed pattern as reviewable learning material",
            evidence_refs=["trace://request/seed"],
            timestamp="2026-05-17T00:00:01Z",
        ),
    )

    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-reflection"),
            session_id=SessionId("sess-reflection"),
            mission_id=MissionId("mission-reflection"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the next milestone.",
            timestamp="2026-05-17T00:01:00Z",
        )
    )

    assert result.deliberative_plan.reflection_influence_status == "applied"
    assert result.deliberative_plan.reflection_influence_refs == [
        "reflection://mission-reflection/seed"
    ]
    assert "reflection_influence=applied" in result.deliberative_plan.plan_summary
    assert "Reflexao aplicada" in result.response_text
    assert "sem promocao automatica" in result.response_text
    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-reflection", limit=80)
    )
    plan_event = next(event for event in stored_events if event.event_name == "plan_built")
    assert plan_event.payload["reflection_influence_status"] == "applied"
    response_event = next(
        event for event in stored_events if event.event_name == "response_synthesized"
    )
    assert response_event.payload["reflection_influence_status"] == "applied"
    workflow_event = next(
        event for event in stored_events if event.event_name == "workflow_composed"
    )
    assert workflow_event.payload["capability_decision_status"] == "resolved"
    assert (
        workflow_event.payload["capability_decision_selected_mode"]
        == "core_with_local_operation"
    )
    assert (
        workflow_event.payload["capability_decision_authorization_status"]
        == "authorized_with_conditions"
    )
    assert workflow_event.payload["workflow_profile"] == "strategic_direction_workflow"
    assert workflow_event.payload["workflow_domain_route"] == "strategy"
    assert workflow_event.payload["workflow_state"] == "composed"
    assert workflow_event.payload["request_identity_status"] == "resolved"
    assert workflow_event.payload["request_active_mission"]
    assert workflow_event.payload["request_executive_posture"] == "structured_planning"
    assert workflow_event.payload["request_authority_level"] == "bounded_execution"
    assert workflow_event.payload["request_risk_profile"] == "governed_caution"
    assert (
        workflow_event.payload["request_reversibility_mode"]
        == "prefer_reversible_change"
    )
    assert (
        workflow_event.payload["request_confirmation_mode"]
        == "explicit_confirmation_required"
    )
    assert workflow_event.payload["request_identity_summary"]
    assert workflow_event.payload["request_identity_policy_refs"] == [
        "policy://request-identity/default"
    ]
    assert (
        workflow_event.payload["mind_domain_specialist_consumer_mode"]
        == "authoritative_specialist"
    )
    assert (
        workflow_event.payload["mind_domain_specialist_framing_mode"]
        == "route_and_specialist_locked"
    )
    assert workflow_event.payload["workflow_expected_deliverables"] == [
        "tradeoff_map",
        "decision_criteria",
        "recommended_direction",
    ]
    assert workflow_event.payload["workflow_telemetry_focus"] == [
        "tradeoff_clarity",
        "decision_trace",
        "domain_alignment",
    ]
    assert (
        workflow_event.payload["workflow_success_focus"]
        == "direcao recomendada com criterios explicitos"
    )
    assert (
        workflow_event.payload["workflow_response_focus"]
        == "direcao recomendada, criterios e trade-offs dominantes"
    )
    assert workflow_event.payload["workflow_governance_mode"] == "core_mediated"
    assert workflow_event.payload["workflow_steps"]
    assert workflow_event.payload["workflow_decision_points"] == [
        "scenario_scope_confirmed",
        "tradeoff_criteria_governed",
        "direction_governed",
    ]
    specialist_contract_event = next(
        event for event in stored_events if event.event_name == "specialist_contracts_composed"
    )
    assert specialist_contract_event.payload["response_channel"] == "through_core"
    assert specialist_contract_event.payload["tool_access_mode"] == "none"
    assert specialist_contract_event.payload["shared_memory_attached"] is True
    assert specialist_contract_event.payload["invocation_ids"]
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    selected_specialist = result.specialist_invocations[0].specialist_type
    assert (
        shared_memory_event.payload["sharing_modes"][selected_specialist]
        == "core_mediated_read_only"
    )
    assert (
        shared_memory_event.payload["memory_class_policies"][selected_specialist]["mission"]["write_policy"]
        == "through_core_only"
    )
    assert shared_memory_event.payload["memory_ref_counts"][selected_specialist] >= 1
    assert shared_memory_event.payload["memory_refs_by_specialist"][selected_specialist]
    assert selected_specialist in shared_memory_event.payload["semantic_focus_by_specialist"]
    specialists_completed_event = next(
        event for event in stored_events if event.event_name == "specialists_completed"
    )
    assert specialists_completed_event.payload["output_hints"]
    specialist_selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert specialist_selection_event.payload["selected_specialists"]
    assert specialist_selection_event.payload["primary_route"] == "strategy"
    assert (
        specialist_selection_event.payload["primary_canonical_domain"]
        == "estrategia_e_pensamento_sistemico"
    )
    assert (
        specialist_selection_event.payload["registry_route_payloads"][selected_specialist][
            "route_name"
        ]
        == "strategy"
    )
    assert specialist_selection_event.payload["registry_link_matches"][selected_specialist] is True
    assert specialist_selection_event.payload["registry_mode_matches"][selected_specialist] is True
    assert (
        specialist_selection_event.payload["mind_domain_specialist_contract_status"]
        == "authoritative_chain"
    )
    assert specialist_selection_event.payload["primary_route_matches"][selected_specialist] is True
    assert (
        specialist_selection_event.payload["primary_canonical_matches"][selected_specialist]
        is True
    )
    assert (
        specialist_selection_event.payload["primary_domain_driver_matches"][
            selected_specialist
        ]
        is True
    )
    assert (
        specialist_selection_event.payload["registry_specialist_eligibility"][selected_specialist]
        is True
    )
    specialist_handoff_event = next(
        event for event in stored_events if event.event_name == "specialist_handoff_governed"
    )
    assert specialist_handoff_event.payload["decision"] == PermissionDecision.ALLOW.value
    domain_specialist_event = next(
        event for event in stored_events if event.event_name == "domain_specialist_completed"
    )
    assert (
        domain_specialist_event.payload["mind_domain_specialist_contract_status"]
        == "authoritative_chain"
    )
    assert domain_specialist_event.payload["primary_route"] == "strategy"
    assert (
        domain_specialist_event.payload["primary_canonical_domain"]
        == "estrategia_e_pensamento_sistemico"
    )
    assert (
        domain_specialist_event.payload["registry_route_payloads"][selected_specialist][
            "route_name"
        ]
        == "strategy"
    )
    assert domain_specialist_event.payload["primary_route_matches"][selected_specialist] is True
    assert (
        domain_specialist_event.payload["primary_canonical_matches"][selected_specialist]
        is True
    )
    assert (
        domain_specialist_event.payload["primary_domain_driver_matches"][
            selected_specialist
        ]
        is True
    )
    workflow_governance_event = next(
        event for event in stored_events if event.event_name == "workflow_governance_declared"
    )
    assert workflow_governance_event.payload["workflow_governance_mode"] == "core_mediated"
    assert workflow_governance_event.payload["workflow_domain_route"] == "strategy"
    assert (
        workflow_governance_event.payload["workflow_success_focus"]
        == "direcao recomendada com criterios explicitos"
    )
    assert workflow_governance_event.payload["workflow_decision_points"] == [
        "scenario_scope_confirmed",
        "tradeoff_criteria_governed",
        "direction_governed",
    ]
    workflow_completed_event = next(
        event for event in stored_events if event.event_name == "workflow_completed"
    )
    assert workflow_completed_event.payload["workflow_domain_route"] == "strategy"
    assert workflow_completed_event.payload["workflow_state"] == "completed"
    assert workflow_completed_event.payload["workflow_expected_deliverables"] == [
        "tradeoff_map",
        "decision_criteria",
        "recommended_direction",
    ]
    assert workflow_completed_event.payload["workflow_telemetry_focus"] == [
        "tradeoff_clarity",
        "decision_trace",
        "domain_alignment",
    ]
    assert (
        workflow_completed_event.payload["workflow_response_focus"]
        == "direcao recomendada, criterios e trade-offs dominantes"
    )
    assert workflow_completed_event.payload["workflow_decisions"] == [
        "scenario_scope_confirmed",
        "tradeoff_criteria_governed",
        "direction_governed",
    ]
    assert result.operation_result is not None
    assert result.operation_result.workflow_domain_route == "strategy"
    assert result.operation_result.workflow_state == "completed"
    assert result.operation_result.workflow_decisions == [
        "scenario_scope_confirmed",
        "tradeoff_criteria_governed",
        "direction_governed",
    ]
    assert all(
        invocation.boundary.user_visibility == "hidden_from_user"
        for invocation in result.specialist_invocations
    )
    assert all(
        invocation.shared_memory_context is not None for invocation in result.specialist_invocations
    )
    context_event = next(event for event in stored_events if event.event_name == "context_composed")
    assert context_event.payload["arbitration_source"] == "mind_registry"
    assert context_event.payload["primary_mind_family"]
    assert (
        context_event.payload["mind_domain_specialist_contract_status"]
        == "authoritative_chain"
    )
    assert context_event.payload["mind_domain_specialist_contract_chain"]
    assert len(context_event.payload["supporting_minds"]) <= (
        context_event.payload["supporting_mind_limit"]
    )
    assert len(context_event.payload["suppressed_minds"]) <= (
        context_event.payload["suppressed_mind_limit"]
    )
    assert context_event.payload["arbitration_summary"]
    directive_event = next(
        event for event in stored_events if event.event_name == "directive_composed"
    )
    assert directive_event.payload["identity_signature"] == "nucleo_soberano_unificado"
    assert directive_event.payload["response_style_preview"]
    continuity_event = next(
        event for event in stored_events if event.event_name == "continuity_decided"
    )
    plan_event = next(event for event in stored_events if event.event_name == "plan_built")
    assert plan_event.payload["primary_mind"] == context_event.payload["primary_mind"]
    assert (
        plan_event.payload["primary_domain_driver"]
        == context_event.payload["primary_domain_driver"]
    )
    assert (
        plan_event.payload["arbitration_source"]
        == context_event.payload["arbitration_source"]
    )
    assert (
        plan_event.payload["metacognitive_guidance_applied"]
        == result.deliberative_plan.metacognitive_guidance_applied
    )
    assert (
        plan_event.payload["metacognitive_guidance_summary"]
        == result.deliberative_plan.metacognitive_guidance_summary
    )
    assert (
        plan_event.payload["metacognitive_effects"]
        == result.deliberative_plan.metacognitive_effects
    )
    assert plan_event.payload["contract_validation_status"] == "coherent"
    assert plan_event.payload["contract_validation_errors"] == []
    assert plan_event.payload["contract_validation_retry_applied"] is False
    assert (
        plan_event.payload["mind_domain_specialist_contract_status"]
        == result.deliberative_plan.mind_domain_specialist_contract_status
    )
    assert (
        plan_event.payload["mind_domain_specialist_contract_chain"]
        == result.deliberative_plan.mind_domain_specialist_contract_chain
    )
    assert plan_event.payload["primary_route"] == result.deliberative_plan.primary_route
    assert (
        plan_event.payload["primary_canonical_domain"]
        == result.deliberative_plan.primary_canonical_domain
    )
    workflow_composed_event = next(
        event for event in stored_events if event.event_name == "workflow_composed"
    )
    ecosystem_state_event = next(
        event for event in stored_events if event.event_name == "ecosystem_state_declared"
    )
    objective_state_event = next(
        event for event in stored_events if event.event_name == "objective_state_declared"
    )
    operation_dispatched_event = next(
        event for event in stored_events if event.event_name == "operation_dispatched"
    )
    operation_completed_event = next(
        event for event in stored_events if event.event_name == "operation_completed"
    )
    workflow_completed_event = next(
        event for event in stored_events if event.event_name == "workflow_completed"
    )
    assert workflow_composed_event.payload["workflow_checkpoint_state"]
    assert workflow_composed_event.payload["ecosystem_state_status"] in {
        "operational_state_attached",
        "partial_operational_state",
    }
    assert workflow_composed_event.payload["active_work_items"]
    assert workflow_composed_event.payload["open_checkpoint_refs"]
    assert "surface:chat" in workflow_composed_event.payload["surface_presence"]
    assert ecosystem_state_event.payload["ecosystem_state_status"] == (
        workflow_composed_event.payload["ecosystem_state_status"]
    )
    assert objective_state_event.payload["objective_status"] == (
        workflow_composed_event.payload["objective_status"]
    )
    assert objective_state_event.payload["project_ref"] == (
        result.operation_dispatch.project_ref
    )
    assert operation_completed_event.payload["objective_status"] == "completed"
    assert workflow_composed_event.payload["workflow_resume_status"] in {
        "fresh_start",
        "resume_available",
        "manual_resume_required",
    }
    assert operation_dispatched_event.payload["workflow_checkpoint_state"] == (
        workflow_composed_event.payload["workflow_checkpoint_state"]
    )
    assert operation_dispatched_event.payload["workflow_resume_status"] in {
        "fresh_start",
        "resume_available",
        "manual_resume_required",
    }
    assert (
        operation_dispatched_event.payload["mind_domain_specialist_consumer_mode"]
        == "authoritative_specialist"
    )
    assert operation_dispatched_event.payload["specialist_hints"] == [
        "structured_analysis_specialist"
    ]
    assert operation_completed_event.payload["workflow_checkpoint_state"]
    assert operation_completed_event.payload["workflow_pending_checkpoints"] == []
    assert operation_completed_event.payload["ecosystem_state_status"] == (
        "operational_state_attached"
    )
    assert operation_completed_event.payload["active_artifact_refs"]
    assert workflow_completed_event.payload["workflow_pending_checkpoints"] == []
    assert workflow_completed_event.payload["workflow_resume_status"] in {
        "completed_without_resume",
        "resumed_from_checkpoint",
        "checkpointed_for_followup",
        "checkpointed_for_manual_resume",
        "resume_blocked",
    }
    governed_event = next(event for event in stored_events if event.event_name == "plan_governed")
    assert governed_event.payload["identity_signature"] == "nucleo_soberano_unificado"
    assert governed_event.payload["identity_guardrail"]
    refined_event = next(event for event in stored_events if event.event_name == "plan_refined")
    assert (
        refined_event.payload["cognitive_strategy_shift_applied"]
        == result.deliberative_plan.cognitive_strategy_shift_applied
    )
    assert (
        refined_event.payload["cognitive_strategy_shift_summary"]
        == result.deliberative_plan.cognitive_strategy_shift_summary
    )
    assert (
        refined_event.payload["cognitive_strategy_shift_trigger"]
        == result.deliberative_plan.cognitive_strategy_shift_trigger
    )
    response_event = next(
        event for event in stored_events if event.event_name == "response_synthesized"
    )
    assert response_event.payload["identity_signature"] == "nucleo_soberano_unificado"
    assert response_event.payload["response_style"]
    assert response_event.payload["primary_mind"] == context_event.payload["primary_mind"]
    assert (
        response_event.payload["primary_domain_driver"]
        == context_event.payload["primary_domain_driver"]
    )
    assert (
        response_event.payload["arbitration_source"]
        == context_event.payload["arbitration_source"]
    )
    assert (
        response_event.payload["metacognitive_guidance_applied"]
        == result.deliberative_plan.metacognitive_guidance_applied
    )
    assert (
        response_event.payload["metacognitive_guidance_summary"]
        == result.deliberative_plan.metacognitive_guidance_summary
    )
    assert (
        response_event.payload["metacognitive_effects"]
        == result.deliberative_plan.metacognitive_effects
    )
    assert (
        response_event.payload["cognitive_strategy_shift_applied"]
        == result.deliberative_plan.cognitive_strategy_shift_applied
    )
    assert (
        response_event.payload["cognitive_strategy_shift_summary"]
        == result.deliberative_plan.cognitive_strategy_shift_summary
    )
    assert (
        response_event.payload["cognitive_strategy_shift_trigger"]
        == result.deliberative_plan.cognitive_strategy_shift_trigger
    )
    assert (
        response_event.payload["cognitive_strategy_shift_effects"]
        == result.deliberative_plan.cognitive_strategy_shift_effects
    )
    assert (
        response_event.payload["mind_domain_specialist_contract_status"]
        == result.deliberative_plan.mind_domain_specialist_contract_status
    )
    assert (
        response_event.payload["mind_domain_specialist_consumer_mode"]
        == "authoritative_specialist"
    )
    assert (
        response_event.payload["mind_domain_specialist_framing_mode"]
        == "route_and_specialist_locked"
    )
    assert response_event.payload["dominant_tension"] == result.deliberative_plan.dominant_tension
    assert response_event.payload["contract_validation_status"] == "coherent"
    assert response_event.payload["contract_validation_errors"] == []
    assert response_event.payload["contract_validation_retry_applied"] is False
    assert response_event.payload["output_validation_status"] == "coherent"
    assert response_event.payload["output_validation_errors"] == []
    assert response_event.payload["output_validation_retry_applied"] is False
    assert response_event.payload["workflow_output_status"] == "coherent"
    assert response_event.payload["workflow_output_errors"] == []
    assert (
        response_event.payload["capability_decision_selected_mode"]
        == "core_with_local_operation"
    )
    assert (
        response_event.payload["capability_decision_authorization_status"]
        == "authorized_with_conditions"
    )
    assert response_event.payload["primary_route"] == result.deliberative_plan.primary_route
    assert (
        response_event.payload["primary_canonical_domain"]
        == result.deliberative_plan.primary_canonical_domain
    )
    assert (
        response_event.payload["workflow_profile"]
        == result.deliberative_plan.route_workflow_profile
    )
    assert response_event.payload["workflow_response_focus"]
    assert response_event.payload["guided_memory_specialists"]
    if result.deliberative_plan.adaptive_intervention_selected_action:
        assert response_event.payload["adaptive_intervention_workflow_priority_summary"]
        assert (
            response_event.payload["adaptive_intervention_preserved_checkpoint"]
            == result.deliberative_plan.route_workflow_checkpoints[0].replace("_", " ")
        )
        assert (
            response_event.payload["adaptive_intervention_preserved_gate"]
            == result.deliberative_plan.route_workflow_decision_points[0].replace("_", " ")
        )
        assert (
            response_event.payload["adaptive_intervention_workflow_priority_summary"]
            in result.response_text
        )
    else:
        assert response_event.payload["adaptive_intervention_workflow_priority_summary"] is None
        assert response_event.payload["adaptive_intervention_preserved_checkpoint"] is None
        assert response_event.payload["adaptive_intervention_preserved_gate"] is None
    memory_event = next(event for event in stored_events if event.event_name == "memory_recorded")
    assert continuity_event.payload["continuity_action"] == "continuar"
    assert response_event.payload["continuity_action"] == "continuar"
    assert memory_event.payload["continuity_mode"] == "continuar"
    assert memory_event.payload["procedural_artifact_status"] == "candidate"
    assert memory_event.payload["procedural_artifact_refs"]
    assert memory_event.payload["procedural_artifact_version"] == 1
    assert memory_event.payload["procedural_artifact_summary"] is not None


def test_orchestrator_service_applies_relevant_reviewed_learning_guidance() -> None:
    temp_dir = runtime_dir("orchestrator-reviewed-learning")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    service.memory_service.record_reviewed_learning_guidance(
        ReviewedLearningGuidanceContract(
            guidance_id="reviewed-learning-guidance://strategy/seed",
            source_review_decision_id="review-decision://proposal-reviewed/001",
            evolution_proposal_id="proposal-reviewed",
            review_status="approved",
            route="strategy",
            workflow_profile="strategic_direction_workflow",
            domain="estrategia_e_pensamento_sistemico",
            guidance_summary="prefer bounded milestone plans with direct evidence",
            allowed_usage=["planning_context", "synthesis_context"],
            evidence_refs=["trace://request/reviewed-seed"],
            rollback_plan_ref="rollback://proposal-reviewed",
            timestamp="2026-05-17T00:00:02Z",
        )
    )

    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-reviewed-learning"),
            session_id=SessionId("sess-reviewed-learning"),
            mission_id=MissionId("mission-reviewed-learning"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the next milestone.",
            timestamp="2026-05-17T00:01:00Z",
        )
    )

    assert result.deliberative_plan.reviewed_learning_influence_status == "applied"
    assert result.deliberative_plan.reviewed_learning_influence_refs == [
        "reviewed-learning-guidance://strategy/seed"
    ]
    assert "reviewed_learning_influence=applied" in (
        result.deliberative_plan.plan_summary
    )
    assert "Aprendizado revisado" in result.response_text
    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-reviewed-learning", limit=80)
    )
    plan_event = next(event for event in stored_events if event.event_name == "plan_built")
    assert plan_event.payload["reviewed_learning_influence_status"] == "applied"
    assert plan_event.payload["reviewed_learning_influence_refs"] == [
        "reviewed-learning-guidance://strategy/seed"
    ]
    response_event = next(
        event for event in stored_events if event.event_name == "response_synthesized"
    )
    assert response_event.payload["reviewed_learning_influence_status"] == "applied"


def test_orchestrator_service_blocks_reviewed_learning_guidance_outside_scope() -> None:
    temp_dir = runtime_dir("orchestrator-reviewed-learning-outside-scope")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    service.memory_service.record_reviewed_learning_guidance(
        ReviewedLearningGuidanceContract(
            guidance_id="reviewed-learning-guidance://analysis/seed",
            source_review_decision_id="review-decision://proposal-analysis/001",
            evolution_proposal_id="proposal-analysis",
            review_status="approved",
            route="analysis",
            workflow_profile="structured_analysis_workflow",
            domain="dados_estatistica_e_inteligencia_analitica",
            guidance_summary="analysis guidance must not leak into strategy planning",
            allowed_usage=["planning_context", "synthesis_context"],
            evidence_refs=["trace://request/analysis-seed"],
            rollback_plan_ref="rollback://proposal-analysis",
            timestamp="2026-05-17T00:00:02Z",
        )
    )

    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-reviewed-learning-blocked"),
            session_id=SessionId("sess-reviewed-learning-blocked"),
            mission_id=MissionId("mission-reviewed-learning-blocked"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the next milestone.",
            timestamp="2026-05-17T00:01:00Z",
        )
    )

    assert (
        result.deliberative_plan.reviewed_learning_influence_status
        == "no_relevant_guidance"
    )
    assert result.deliberative_plan.reviewed_learning_influence_refs == []
    assert "Aprendizado revisado" not in result.response_text


def test_orchestrator_service_requests_clarification_without_operation() -> None:
    temp_dir = runtime_dir("orchestrator-clarify")
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan and analyze the roadmap.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    assert result.directive.requires_clarification is True
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert result.deliberative_plan.recommended_task_type == "general_response"
    assert result.deliberative_plan.capability_decision_selected_mode == "clarification_only"
    assert (
        result.deliberative_plan.capability_decision_authorization_status
        == "clarification_required"
    )
    assert result.specialist_invocations == []
    clarification_event = next(
        event for event in result.events if event.event_name == "plan_governed"
    )
    assert clarification_event.payload["capability_decision_selected_mode"] == "clarification_only"
    assert (
        clarification_event.payload["capability_decision_authorization_status"]
        == "clarification_required"
    )
    assert "clarification_required" in [event.event_name for event in result.events]


def test_orchestrator_service_tracks_promoted_domain_specialist_without_breaking_core() -> None:
    temp_dir = runtime_dir("orchestrator-shadow-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-shadow"),
            session_id=SessionId("sess-shadow"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the Python service API rollout and compare the safest change.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-shadow", limit=60)
    )
    event_names = [event.event_name for event in stored_events]
    assert "domain_registry_resolved" in event_names
    assert "domain_specialist_completed" in event_names
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "software_change_specialist" in selection_event.payload["domain_specialists"]
    assert "software_change_specialist" in selection_event.payload["guided_specialists"]
    assert (
        selection_event.payload["domain_links"]["software_change_specialist"]
        == "software_development"
    )
    assert selection_event.payload["registry_link_matches"]["software_change_specialist"] is True
    assert selection_event.payload["registry_mode_matches"]["software_change_specialist"] is True
    assert (
        selection_event.payload["registry_specialist_eligibility"][
            "software_change_specialist"
        ]
        is True
    )
    domain_event = next(
        event for event in stored_events if event.event_name == "domain_specialist_completed"
    )
    assert domain_event.payload["linked_domains"]["software_change_specialist"] == (
        "software_development"
    )
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["software_change_specialist"]
        == "domain_guided_memory_packet"
    )
    assert (
        shared_memory_event.payload["consumer_profiles"]["software_change_specialist"]
        == "software_change_review"
    )
    assert (
        "recommended_patch_direction"
        in shared_memory_event.payload["expected_deliverables"][
            "software_change_specialist"
        ]
    )
    assert (
        "implementation_trace"
        in shared_memory_event.payload["telemetry_focus"][
            "software_change_specialist"
        ]
    )
    specialist_briefs = shared_memory_event.payload["context_briefs"][
        "software_change_specialist"
    ]
    assert specialist_briefs["mission"]
    assert specialist_briefs["domain"]
    assert specialist_briefs["continuity"]
    assert (
        domain_event.payload["consumer_profiles"]["software_change_specialist"]
        == "software_change_review"
    )
    assert any(
        invocation.specialist_type == "software_change_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "software_development"
        for invocation in result.specialist_invocations
    )
    assert result.operation_dispatch is None
    assert "workflow_completed" not in event_names
    assert result.response_text


def test_orchestrator_service_blocks_sensitive_action() -> None:
    temp_dir = runtime_dir("orchestrator-block")
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=ObservabilityService(
            database_path=str(temp_dir / "observability.db")
        ),
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-3"),
            session_id=SessionId("sess-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all project files now.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    assert result.intent == "sensitive_action"
    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.operation_dispatch is None
    assert result.operation_result is None
    assert "governance_blocked" in [event.event_name for event in result.events]
    assert "a governanca atual exige conter a acao" in result.response_text


def test_orchestrator_service_recovers_mission_continuity_across_instances() -> None:
    temp_dir = runtime_dir("orchestrator-persist")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first_contract = InputContract(
        request_id=RequestId("req-4"),
        session_id=SessionId("sess-4"),
        mission_id=MissionId("mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    second_contract = InputContract(
        request_id=RequestId("req-5"),
        session_id=SessionId("sess-4"),
        mission_id=MissionId("mission-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Analyze the previous plan.",
        timestamp="2026-03-17T00:01:00Z",
    )
    first.handle_input(first_contract)
    second_result = second.handle_input(second_contract)
    assert any("prior_plan=" in item for item in second_result.recovered_context)
    assert any("identity_continuity_brief=" in item for item in second_result.recovered_context)
    assert any("open_loops=" in item for item in second_result.recovered_context)
    assert any("mission_semantic_brief=" in item for item in second_result.recovered_context)
    assert any("mission_goal=" in item for item in second_result.recovered_context)
    assert any(
        item == "continuity_replay_status=resumable" for item in second_result.recovered_context
    )
    assert any(
        item.startswith("continuity_resume_point=") for item in second_result.recovered_context
    )
    assert any(
        item == "mission_ecosystem_state_status=operational_state_attached"
        for item in second_result.recovered_context
    )
    assert any(
        item.startswith("mission_active_work_items=")
        for item in second_result.recovered_context
    )
    assert any(
        item.startswith("mission_active_artifact_refs=")
        for item in second_result.recovered_context
    )
    assert second_result.deliberative_plan.recommended_task_type == "produce_analysis_brief"
    assert second_result.operation_result is None
    assert second_result.specialist_review is not None
    assert second_result.deliberative_plan.continuity_action == "continuar"
    assert second_result.deliberative_plan.continuity_source == "active_mission"
    assert second_result.deliberative_plan.open_loops
    assert any(
        item.startswith("session_continuity_brief=") for item in second_result.recovered_context
    )
    assert "Continuidade ativa:" in second_result.response_text
    assert "Julgamento" in second_result.response_text
    assert "missao ativa segue ancorada em" in second_result.response_text
    assert "Dominios:" not in second_result.response_text
    replay_event = next(
        event for event in second_result.events if event.event_name == "continuity_replay_loaded"
    )
    assert replay_event.payload["replay_status"] == "resumable"
    assert replay_event.payload["recovery_mode"] == "resume_operational_checkpoint"
    assert replay_event.payload["ecosystem_state_status"] == "operational_state_attached"


def test_orchestrator_service_surfaces_related_mission_candidate_in_same_session() -> None:
    temp_dir = runtime_dir("orchestrator-related")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    service = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    service.handle_input(
        InputContract(
            request_id=RequestId("req-related-a"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-a"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan milestone M3 rollout.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-related-b"),
            session_id=SessionId("sess-related"),
            mission_id=MissionId("mission-b"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze milestone M3 rollout risks.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )

    assert result.deliberative_plan.continuity_source == "related_mission"
    assert result.deliberative_plan.continuity_action == "retomar"
    assert result.mission_runtime_state is not None
    assert result.mission_runtime_state.mission_id == MissionId("mission-b")
    assert result.mission_runtime_state.related_mission_id == MissionId("mission-a")
    assert result.mission_runtime_state.continuity_source == "related_mission"
    assert result.deliberative_plan.continuity_reason is not None
    assert any(item == "related_mission_id=mission-a" for item in result.recovered_context)
    assert any(
        item == "continuity_recommendation=retomar_missao_relacionada"
        for item in result.recovered_context
    )
    assert any(item.startswith("session_continuity_mode=") for item in result.recovered_context)
    assert "continuity_decided" in [event.event_name for event in result.events]
    mission_runtime_event = next(
        event for event in result.events if event.event_name == "mission_runtime_state_declared"
    )
    assert mission_runtime_event.payload["mission_id"] == "mission-b"
    assert mission_runtime_event.payload["related_mission_id"] == "mission-a"
    assert mission_runtime_event.payload["continuity_source"] == "related_mission"
    assert "Continuidade ativa:" in result.response_text
    assert "missao_relacionada=Plan milestone M3 rollout." in result.deliberative_plan.rationale


def test_orchestrator_service_reformulates_conflicting_request_in_active_mission() -> None:
    temp_dir = runtime_dir("orchestrator-reframe")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-6"),
            session_id=SessionId("sess-5"),
            mission_id=MissionId("mission-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the sprint.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    result = second.handle_input(
        InputContract(
            request_id=RequestId("req-7"),
            session_id=SessionId("sess-5"),
            mission_id=MissionId("mission-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )
    assert result.deliberative_plan.continuity_action == "reformular"
    assert result.deliberative_plan.recommended_task_type == "general_response"
    assert result.deliberative_plan.capability_decision_selected_mode == "contained_guidance"
    assert (
        result.deliberative_plan.capability_decision_authorization_status
        == "human_validation_required"
    )
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.operation_result is None
    assert "tensiona a missao ativa" in result.response_text
    plan_governed_event = next(
        event for event in result.events if event.event_name == "plan_governed"
    )
    assert plan_governed_event.payload["capability_decision_selected_mode"] == "contained_guidance"
    assert (
        plan_governed_event.payload["capability_decision_authorization_status"]
        == "deferred_for_validation"
    )


def test_orchestrator_service_closes_active_loop_explicitly() -> None:
    temp_dir = runtime_dir("orchestrator-close")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-close-1"),
            session_id=SessionId("sess-close"),
            mission_id=MissionId("mission-close"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the sprint.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    result = second.handle_input(
        InputContract(
            request_id=RequestId("req-close-2"),
            session_id=SessionId("sess-close"),
            mission_id=MissionId("mission-close"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Encerrar checkpoint principal da sprint.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )
    assert result.deliberative_plan.continuity_action == "encerrar"
    assert any(
        step.startswith("fechar explicitamente o loop principal")
        for step in result.deliberative_plan.steps
    )
    assert "continuity_decided" in [event.event_name for event in result.events]
    assert "fechar o loop principal da missao" in result.response_text


def test_orchestrator_service_blocks_invalid_specialist_handoff_and_continues_without_contribution(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("orchestrator-specialist-block")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    original_plan_handoffs = service.specialist_engine.plan_handoffs

    def invalid_boundary_plan(**kwargs):  # type: ignore[no-untyped-def]
        handoff_plan = original_plan_handoffs(**kwargs)
        if handoff_plan.invocations:
            handoff_plan.invocations[0].boundary.response_channel = "direct_to_user"
        return handoff_plan

    monkeypatch.setattr(service.specialist_engine, "plan_handoffs", invalid_boundary_plan)

    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-specialist-block"),
            session_id=SessionId("sess-specialist-block"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the first milestone.",
            timestamp="2026-03-23T00:00:00Z",
        )
    )

    assert result.specialist_handoff_decision is not None
    assert result.specialist_handoff_decision.decision == PermissionDecision.BLOCK
    assert result.specialist_review is not None
    assert result.specialist_review.contributions == []
    assert result.deliberative_plan.specialist_resolution_summary is None
    assert "specialist_handoff_blocked" in [event.event_name for event in result.events]
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS


def test_orchestrator_service_preserves_mission_state_after_blocked_followup() -> None:
    temp_dir = runtime_dir("orchestrator-blocked-mission")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first_result = first.handle_input(
        InputContract(
            request_id=RequestId("req-8"),
            session_id=SessionId("sess-6"),
            mission_id=MissionId("mission-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the sprint.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    second.handle_input(
        InputContract(
            request_id=RequestId("req-9"),
            session_id=SessionId("sess-6"),
            mission_id=MissionId("mission-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all mission records now.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )

    mission_state = second.memory_service.get_mission_state("mission-3")

    assert mission_state is not None
    assert mission_state.mission_goal == "Please plan the sprint."
    assert mission_state.last_recommendation == first_result.deliberative_plan.plan_summary
    assert mission_state.open_loops
    assert mission_state.open_loops[0] != "Delete all mission records now."


def test_orchestrator_service_governs_replay_when_checkpoint_awaits_validation() -> None:
    temp_dir = runtime_dir("orchestrator-replay-governed")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-replay-1"),
            session_id=SessionId("sess-replay-governed"),
            mission_id=MissionId("mission-replay-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the sprint.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-replay-2"),
            session_id=SessionId("sess-replay-governed"),
            mission_id=MissionId("mission-replay-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )
    result = second.handle_input(
        InputContract(
            request_id=RequestId("req-replay-3"),
            session_id=SessionId("sess-replay-governed"),
            mission_id=MissionId("mission-replay-governed"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the sprint plan.",
            timestamp="2026-03-17T00:02:00Z",
        )
    )

    assert any(
        item == "continuity_replay_status=awaiting_validation" for item in result.recovered_context
    )
    assert result.deliberative_plan.continuity_recovery_mode == "governed_review"
    assert result.deliberative_plan.recommended_task_type == "general_response"
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    governed_event = next(
        event for event in result.events if event.event_name == "continuity_recovery_governed"
    )
    assert governed_event.payload["replay_status"] == "awaiting_validation"
    assert governed_event.payload["recovery_mode"] == "governed_review"
    continuity_event = next(
        event for event in result.events if event.event_name == "continuity_subflow_completed"
    )
    assert continuity_event.payload["runtime_mode"] == "native_pipeline"
    assert continuity_event.payload["replay_status"] == "awaiting_validation"
    assert continuity_event.payload["requires_manual_resume"] is True


def test_orchestrator_service_tracks_manual_resolution_of_continuity_pause() -> None:
    temp_dir = runtime_dir("orchestrator-replay-resolved")
    memory_db = f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    observability_db = str(temp_dir / "observability.db")
    artifact_dir = str(temp_dir / "artifacts")
    first = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    second = OrchestratorService(
        memory_service=MemoryService(database_url=memory_db),
        operational_service=OperationalService(artifact_dir=artifact_dir),
        observability_service=ObservabilityService(database_path=observability_db),
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-resolve-1"),
            session_id=SessionId("sess-replay-resolved"),
            mission_id=MissionId("mission-replay-resolved"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the sprint.",
            timestamp="2026-03-17T00:00:00Z",
        )
    )
    first.handle_input(
        InputContract(
            request_id=RequestId("req-resolve-2"),
            session_id=SessionId("sess-replay-resolved"),
            mission_id=MissionId("mission-replay-resolved"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Start a new marketing campaign instead.",
            timestamp="2026-03-17T00:01:00Z",
        )
    )
    result = second.handle_input(
        InputContract(
            request_id=RequestId("req-resolve-3"),
            session_id=SessionId("sess-replay-resolved"),
            mission_id=MissionId("mission-replay-resolved"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Continue the sprint plan.",
            timestamp="2026-03-17T00:02:00Z",
            metadata={
                "continuity_resume": {
                    "approved": True,
                    "resolved_by": "operator",
                    "resolution_note": "retomada aprovada apos revisao",
                }
            },
        )
    )

    assert any(item == "continuity_replay_status=resumable" for item in result.recovered_context)
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    resolved_event = next(
        event for event in result.events if event.event_name == "continuity_pause_resolved"
    )
    assert resolved_event.payload["resolution_status"] == "approved"
    assert resolved_event.payload["resolved_by"] == "operator"
    continuity_event = next(
        event for event in result.events if event.event_name == "continuity_subflow_completed"
    )
    assert continuity_event.payload["pause_resolution_status"] == "approved"
    assert continuity_event.payload["pause_resolved_by"] == "operator"




def test_orchestrator_service_tracks_guided_analysis_domain_specialist() -> None:
    temp_dir = runtime_dir("orchestrator-analysis-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-analysis-domain"),
            session_id=SessionId("sess-analysis-domain"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Compare the rollout trade-offs and identify the dominant decision criterion.",
            timestamp="2026-03-27T00:20:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-analysis-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "structured_analysis_specialist" in selection_event.payload["domain_specialists"]
    assert "structured_analysis_specialist" in selection_event.payload["guided_specialists"]
    assert selection_event.payload["domain_links"]["structured_analysis_specialist"] == "analysis"
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["structured_analysis_specialist"]
        == "domain_guided_memory_packet"
    )
    assert any(
        invocation.specialist_type == "structured_analysis_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "analysis"
        for invocation in result.specialist_invocations
    )



def test_orchestrator_service_tracks_guided_governance_domain_specialist() -> None:
    temp_dir = runtime_dir("orchestrator-governance-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-governance-domain"),
            session_id=SessionId("sess-governance-domain"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze governance limits, audit needs and risk containment for the release.",
            timestamp="2026-03-27T00:40:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-governance-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "governance_review_specialist" in selection_event.payload["domain_specialists"]
    assert "governance_review_specialist" in selection_event.payload["guided_specialists"]
    assert (
        selection_event.payload["domain_links"]["governance_review_specialist"]
        == "governance"
    )
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["governance_review_specialist"]
        == "domain_guided_memory_packet"
    )
    assert any(
        invocation.specialist_type == "governance_review_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "governance"
        for invocation in result.specialist_invocations
    )



def test_orchestrator_service_tracks_guided_operational_readiness_specialist() -> None:
    temp_dir = runtime_dir("orchestrator-readiness-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-readiness-domain"),
            session_id=SessionId("sess-readiness-domain"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the release readiness checks, checkpoints and rollback gates.",
            timestamp="2026-03-27T01:00:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-readiness-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "operational_planning_specialist" in selection_event.payload["domain_specialists"]
    assert "operational_planning_specialist" in selection_event.payload["guided_specialists"]
    assert (
        selection_event.payload["domain_links"]["operational_planning_specialist"]
        == "operational_readiness"
    )
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["operational_planning_specialist"]
        == "domain_guided_memory_packet"
    )
    assert any(
        invocation.specialist_type == "operational_planning_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "operational_readiness"
        for invocation in result.specialist_invocations
    )



def test_orchestrator_service_tracks_guided_strategy_specialist() -> None:
    temp_dir = runtime_dir("orchestrator-strategy-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-strategy-domain"),
            session_id=SessionId("sess-strategy-domain"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan strategic options for the release.",
            timestamp="2026-03-27T01:20:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-strategy-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "operational_planning_specialist" in selection_event.payload["domain_specialists"]
    assert "operational_planning_specialist" in selection_event.payload["guided_specialists"]
    assert (
        selection_event.payload["domain_links"]["operational_planning_specialist"]
        == "operational_readiness"
    )
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["operational_planning_specialist"]
        == "domain_guided_memory_packet"
    )
    assert any(
        invocation.specialist_type == "operational_planning_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "operational_readiness"
        for invocation in result.specialist_invocations
    )


def test_orchestrator_service_tracks_guided_decision_risk_specialist() -> None:
    temp_dir = runtime_dir("orchestrator-decision-risk-domain")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-decision-risk-domain"),
            session_id=SessionId("sess-decision-risk-domain"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Review decision risk, reversibility and the dominant containment gate.",
            timestamp="2026-03-27T01:40:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-decision-risk-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "governance_review_specialist" in selection_event.payload["domain_specialists"]
    assert "governance_review_specialist" in selection_event.payload["guided_specialists"]
    assert (
        selection_event.payload["domain_links"]["governance_review_specialist"]
        == "decision_risk"
    )
    shared_memory_event = next(
        event for event in stored_events if event.event_name == "specialist_shared_memory_linked"
    )
    assert (
        shared_memory_event.payload["consumer_modes"]["governance_review_specialist"]
        == "domain_guided_memory_packet"
    )
    assert any(
        invocation.specialist_type == "governance_review_specialist"
        and invocation.selection_mode == "guided"
        and invocation.linked_domain == "decision_risk"
        for invocation in result.specialist_invocations
    )




def test_orchestrator_service_emits_recurrent_specialist_memory_signals() -> None:
    temp_dir = runtime_dir("orchestrator-specialist-recurrence")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    service.handle_input(
        InputContract(
            request_id=RequestId("req-specialist-scope-1"),
            session_id=SessionId("sess-specialist-scope-1"),
            mission_id=MissionId("mission-specialist-scope-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the Python service API rollout and compare the safest change.",
            timestamp="2026-03-31T00:00:00Z",
            user_id="user-specialist-scope-1",
        )
    )
    second = service.handle_input(
        InputContract(
            request_id=RequestId("req-specialist-scope-2"),
            session_id=SessionId("sess-specialist-scope-2"),
            mission_id=MissionId("mission-specialist-scope-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the Python service API rollout and compare the safest change again.",
            timestamp="2026-03-31T00:01:00Z",
            user_id="user-specialist-scope-1",
        )
    )

    shared_memory_event = next(
        event for event in second.events if event.event_name == "specialist_shared_memory_linked"
    )

    statuses = shared_memory_event.payload["recurrent_context_statuses"]
    counts = shared_memory_event.payload["recurrent_interaction_counts"]
    briefs = shared_memory_event.payload["recurrent_context_briefs"]

    assert statuses
    assert any(status == "recoverable" for status in statuses.values())
    recoverable_specialists = [
        specialist for specialist, status in statuses.items() if status == "recoverable"
    ]
    assert all(counts[specialist] >= 2 for specialist in recoverable_specialists)
    assert all(briefs[specialist] for specialist in recoverable_specialists)


def test_orchestrator_service_emits_user_scope_memory_signals() -> None:
    temp_dir = runtime_dir("orchestrator-user-scope")
    observability = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(
            database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
        ),
        operational_service=OperationalService(artifact_dir=str(temp_dir / "artifacts")),
        observability_service=observability,
    )
    service.handle_input(
        InputContract(
            request_id=RequestId("req-user-scope-1"),
            session_id=SessionId("sess-user-scope-1"),
            mission_id=MissionId("mission-user-scope-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Plan the first milestone.",
            timestamp="2026-03-31T00:00:00Z",
            user_id="user-scope-1",
        )
    )
    second = service.handle_input(
        InputContract(
            request_id=RequestId("req-user-scope-2"),
            session_id=SessionId("sess-user-scope-2"),
            mission_id=MissionId("mission-user-scope-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Analyze the milestone trade-offs.",
            timestamp="2026-03-31T00:01:00Z",
            user_id="user-scope-1",
        )
    )

    memory_recovered_event = next(
        event for event in second.events if event.event_name == "memory_recovered"
    )
    memory_recorded_event = next(
        event for event in second.events if event.event_name == "memory_recorded"
    )

    assert memory_recovered_event.payload["user_scope_status"] == "seeded"
    assert (
        memory_recovered_event.payload["organization_scope_status"]
        == "no_go_without_canonical_consumer"
    )
    assert memory_recovered_event.payload["user_scope_interaction_count"] == 1
    assert memory_recovered_event.payload["user_scope_memory_refs"]
    assert memory_recovered_event.payload["context_compaction_status"] == "seeded_live_context"
    assert memory_recovered_event.payload["cross_session_recall_status"] == "seeded"
    assert memory_recovered_event.payload["context_live_summary"] is not None
    assert (
        memory_recorded_event.payload["organization_scope_status"]
        == "no_go_without_canonical_consumer"
    )
    assert memory_recorded_event.payload["user_scope_status"] == "recoverable"
    assert memory_recorded_event.payload["user_scope_interaction_count"] == 2


def test_orchestrator_service_uses_recovered_memory_hints_without_specialist_runtime() -> None:
    plan = DeliberativePlanContract(
        plan_summary="objetivo=Plan milestone M3; modo=structured_planning; continuidade=continuar",
        goal="Plan milestone M3",
        steps=["retomar o loop principal da missao: alinhar checkpoint principal"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="objetivo_dominante=Plan milestone M3; continuidade=ativo",
        specialist_hints=[],
        success_criteria=["resposta deve fechar ou avancar o loop principal da missao"],
        continuity_action="continuar",
        continuity_reason="existem loops ativos que mantem a missao atual ancorada",
        open_loops=["alinhar checkpoint principal"],
        canonical_domains=["estrategia_e_pensamento_sistemico"],
        primary_canonical_domain="estrategia_e_pensamento_sistemico",
        primary_route="strategy",
        route_workflow_profile="strategic_direction_workflow",
        smallest_safe_next_action="retomar alinhar checkpoint principal antes de abrir novo escopo",
    )
    review = SpecialistReview(
        specialist_hints=[],
        selections=[],
        invocations=[],
        contributions=[],
        summary="sem especialistas",
        findings=[],
        boundary_summary="sem handoff",
    )

    hints = OrchestratorService._guided_memory_runtime_hints(
        review,
        plan,
        [
            "mission_semantic_brief=objetivo=Plan milestone M3",
            "mission_focus=estrategia_e_pensamento_sistemico,strategy",
            "mission_recommendation=manter o ultimo fio de recomendacao governada",
        ],
    )

    assert hints["guided_memory_specialists"] == []
    assert hints["semantic_memory_available"] is True
    assert "estrategia_e_pensamento_sistemico" in hints["semantic_memory_focus"]
    assert "strategy" in hints["semantic_memory_focus"]
    assert hints["procedural_memory_available"] is True
    assert hints["procedural_memory_hint"] == "manter o ultimo fio de recomendacao governada"


def test_orchestrator_service_prioritizes_route_guidance_from_recovered_memory() -> None:
    guidance = OrchestratorService._memory_route_guidance(
        active_domains=["strategy", "analysis", "documentation"],
        recovered_context=[
            "mission_focus=dados_estatistica_e_inteligencia_analitica",
            "user_domain_focus=estrategia_e_pensamento_sistemico",
            "continuity_recommendation=retomar_missao_relacionada",
            "related_continuity_priority=0.91",
            "procedural_artifact_status=reusable",
        ],
    )

    assert guidance["status"] == "memory_guided"
    assert guidance["prioritized_domains"][:2] == ["analysis", "strategy"]
    assert guidance["prioritized_specialists"] == ["structured_analysis_specialist"]
    assert guidance["sources"] == [
        "mission_focus",
        "user_scope",
        "continuity_ranking",
        "procedural_artifact",
    ]
    assert "analysis:" in str(guidance["summary"])
