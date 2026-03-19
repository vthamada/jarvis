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


def test_orchestrator_service_handles_deliberative_planning_with_refined_plan() -> None:
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
    assert result.directive.requires_clarification is False
    assert result.deliberative_plan.recommended_task_type == "draft_plan"
    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.operation_result is not None
    assert result.operation_result.status == OperationStatus.COMPLETED
    assert result.knowledge_result is not None
    assert result.artifact_results
    assert result.active_domains == ["strategy", "productivity"]
    assert result.cognitive_tensions
    assert result.specialist_hints == ["especialista_planejamento_operacional"]
    assert result.specialist_review is not None
    assert result.specialist_review.contributions
    assert any("checkpoint intermediario" in step for step in result.deliberative_plan.steps)
    assert "Contribuicoes especialistas" in result.response_text
    stored_events = observability.list_recent_events(ObservabilityQuery(request_id="req-1"))
    event_names = [event.event_name for event in stored_events]
    assert event_names == [event.event_name for event in result.events]
    assert "plan_built" in event_names
    assert "specialists_completed" in event_names
    assert "plan_refined" in event_names
    assert "plan_governed" in event_names


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
    assert "nao permite execucao direta" in result.response_text


def test_orchestrator_service_recovers_previous_plan_hints_across_instances() -> None:
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
    assert any("mission_recommendation=" in item for item in second_result.recovered_context)
    assert any("mission_semantic_brief=" in item for item in second_result.recovered_context)
    assert any("mission_focus=" in item for item in second_result.recovered_context)
    assert second_result.deliberative_plan.recommended_task_type == "produce_analysis_brief"
    assert second_result.operation_result is None
    assert "especialista_analise_estruturada" in second_result.specialist_hints
    assert second_result.specialist_review is not None
    assert second_result.specialist_review.summary
    assert "missao=objetivo=Please plan the sprint." in second_result.deliberative_plan.rationale
    assert any(
        "criterio de decisao dominante" in step
        for step in second_result.deliberative_plan.steps
    )
