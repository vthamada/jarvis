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
    assert result.knowledge_result is not None
    assert result.artifact_results
    assert result.active_domains == ["strategy", "documentation", "observability"]
    assert result.cognitive_tensions
    assert result.specialist_review is not None
    assert result.specialist_review.contributions
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
    assert "specialists_completed" in event_names
    assert "plan_refined" in event_names
    assert "plan_governed" in event_names
    assert result.specialist_handoff_check is not None
    assert result.specialist_handoff_decision is not None
    assert result.specialist_handoff_decision.decision == PermissionDecision.ALLOW
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
    assert shared_memory_event.payload["sharing_modes"][
        "especialista_planejamento_operacional"
    ] == "core_mediated_read_only"
    specialists_completed_event = next(
        event for event in stored_events if event.event_name == "specialists_completed"
    )
    assert specialists_completed_event.payload["output_hints"]
    specialist_selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert specialist_selection_event.payload["selected_specialists"]
    specialist_handoff_event = next(
        event for event in stored_events if event.event_name == "specialist_handoff_governed"
    )
    assert specialist_handoff_event.payload["decision"] == PermissionDecision.ALLOW.value
    assert all(
        invocation.boundary.user_visibility == "hidden_from_user"
        for invocation in result.specialist_invocations
    )
    assert all(
        invocation.shared_memory_context is not None
        for invocation in result.specialist_invocations
    )
    continuity_event = next(
        event for event in stored_events if event.event_name == "continuity_decided"
    )
    response_event = next(
        event for event in stored_events if event.event_name == "response_synthesized"
    )
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


def test_orchestrator_service_tracks_domain_shadow_specialist_without_breaking_core() -> None:
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
    assert "specialist_shadow_mode_completed" in event_names
    selection_event = next(
        event for event in stored_events if event.event_name == "specialist_selection_decided"
    )
    assert "especialista_software_subordinado" in selection_event.payload["shadow_specialists"]
    assert (
        selection_event.payload["domain_links"]["especialista_software_subordinado"]
        == "software_development"
    )
    shadow_event = next(
        event for event in stored_events if event.event_name == "specialist_shadow_mode_completed"
    )
    assert shadow_event.payload["linked_domains"]["especialista_software_subordinado"] == (
        "software_development"
    )
    assert any(
        invocation.specialist_type == "especialista_software_subordinado"
        and invocation.selection_mode == "shadow"
        and invocation.linked_domain == "software_development"
        for invocation in result.specialist_invocations
    )
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
        item == "continuity_replay_status=resumable"
        for item in second_result.recovered_context
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
    assert any(
        item.startswith("session_continuity_mode=") for item in result.recovered_context
    )
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
    assert mission_state.open_loops == first_result.deliberative_plan.open_loops


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
        item == "continuity_replay_status=awaiting_validation"
        for item in result.recovered_context
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

    assert any(
        item == "continuity_replay_status=resumable"
        for item in result.recovered_context
    )
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    resolved_event = next(
        event for event in result.events if event.event_name == "continuity_pause_resolved"
    )
    assert resolved_event.payload["resolution_status"] == "approved"
    assert resolved_event.payload["resolved_by"] == "operator"
