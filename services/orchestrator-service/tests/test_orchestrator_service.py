from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorResponse, OrchestratorService

from shared.contracts import InputContract
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
    assert result.operation_dispatch.canonical_domain_hints
    assert result.operation_dispatch.primary_canonical_domain == "estrategia_e_pensamento_sistemico"
    assert result.knowledge_result is not None
    assert result.artifact_results
    assert result.active_domains == ["strategy", "documentation", "observability"]
    assert result.cognitive_tensions
    assert result.specialist_review is not None
    assert result.specialist_review.contributions
    assert result.deliberative_plan.canonical_domains
    assert result.deliberative_plan.primary_canonical_domain == "estrategia_e_pensamento_sistemico"
    assert result.deliberative_plan.open_loops
    assert result.specialist_invocations
    assert result.specialist_boundary_summary is not None
    assert result.deliberative_plan.specialist_resolution_summary is not None
    assert "Contribuicoes especialistas" not in result.response_text
    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-1", limit=50)
    )
    event_names = [event.event_name for event in stored_events]
    assert event_names == [event.event_name for event in result.events]
    assert "directive_composed" in event_names
    assert "plan_built" in event_names
    assert "continuity_decided" in event_names
    assert "specialist_selection_decided" in event_names
    assert "specialist_shared_memory_linked" in event_names
    assert "specialist_contracts_composed" in event_names
    assert "specialist_handoff_governed" in event_names
    assert "workflow_composed" in event_names
    assert "workflow_governance_declared" in event_names
    assert "specialists_completed" in event_names
    assert "plan_refined" in event_names
    assert "plan_governed" in event_names
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
    assert registry_event.payload["specialist_mode"]["strategy"] == "guided"
    assert registry_event.payload["workflow_profile"]["strategy"] == "strategic_direction_workflow"
    assert (
        registry_event.payload["promoted_route_registry"]["strategy"]["linked_specialist_type"]
        == "structured_analysis_specialist"
    )
    assert registry_event.payload["promoted_route_registry"]["strategy"]["eligible"] is True
    workflow_event = next(
        event for event in stored_events if event.event_name == "workflow_composed"
    )
    assert workflow_event.payload["workflow_profile"] == "strategic_direction_workflow"
    assert workflow_event.payload["workflow_domain_route"] == "strategy"
    assert workflow_event.payload["workflow_state"] == "composed"
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
    assert (
        specialist_selection_event.payload["registry_route_payloads"][selected_specialist]["route_name"]
        == "strategy"
    )
    assert specialist_selection_event.payload["registry_link_matches"][selected_specialist] is True
    assert specialist_selection_event.payload["registry_mode_matches"][selected_specialist] is True
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
        domain_specialist_event.payload["registry_route_payloads"][selected_specialist]["route_name"]
        == "strategy"
    )
    workflow_governance_event = next(
        event for event in stored_events if event.event_name == "workflow_governance_declared"
    )
    assert workflow_governance_event.payload["workflow_governance_mode"] == "core_mediated"
    assert workflow_governance_event.payload["workflow_domain_route"] == "strategy"
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
    governed_event = next(event for event in stored_events if event.event_name == "plan_governed")
    assert governed_event.payload["identity_signature"] == "nucleo_soberano_unificado"
    assert governed_event.payload["identity_guardrail"]
    response_event = next(
        event for event in stored_events if event.event_name == "response_synthesized"
    )
    assert response_event.payload["identity_signature"] == "nucleo_soberano_unificado"
    assert response_event.payload["response_style"]
    assert response_event.payload["guided_memory_specialists"]
    memory_event = next(event for event in stored_events if event.event_name == "memory_recorded")
    assert continuity_event.payload["continuity_action"] == "continuar"
    assert response_event.payload["continuity_action"] == "continuar"
    assert memory_event.payload["continuity_mode"] == "continuar"


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
    assert replay_event.payload["recovery_mode"] == "resume_active_mission"


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
    assert result.deliberative_plan.continuity_reason is not None
    assert any(item == "related_mission_id=mission-a" for item in result.recovered_context)
    assert any(
        item == "continuity_recommendation=retomar_missao_relacionada"
        for item in result.recovered_context
    )
    assert any(item.startswith("session_continuity_mode=") for item in result.recovered_context)
    assert "continuity_decided" in [event.event_name for event in result.events]
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
    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.operation_result is None
    assert "tensiona a missao ativa" in result.response_text
    assert "plan_governed" in [event.event_name for event in result.events]


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
    assert result.deliberative_plan.steps[0].startswith("fechar explicitamente o loop principal")
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
            content=(
                "Plan the strategic direction, compare options and define the dominant criterion."
            ),
            timestamp="2026-03-27T01:20:00Z",
        )
    )

    stored_events = observability.list_recent_events(
        ObservabilityQuery(request_id="req-strategy-domain", limit=60)
    )
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "structured_analysis_specialist" in selection_event.payload["domain_specialists"]
    assert "structured_analysis_specialist" in selection_event.payload["guided_specialists"]
    assert selection_event.payload["domain_links"]["structured_analysis_specialist"] == "strategy"
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
        and invocation.linked_domain == "strategy"
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
    assert (
        memory_recorded_event.payload["organization_scope_status"]
        == "no_go_without_canonical_consumer"
    )
    assert memory_recorded_event.payload["user_scope_status"] == "recoverable"
    assert memory_recorded_event.payload["user_scope_interaction_count"] == 2
