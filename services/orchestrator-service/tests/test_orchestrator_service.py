from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorResponse, OrchestratorService
from shared.contracts import InputContract
from shared.types import (
    ChannelType,
    InputType,
    OperationStatus,
    PermissionDecision,
    RequestId,
    SessionId,
)


def test_orchestrator_service_name() -> None:
    assert OrchestratorService.name == "orchestrator-service"


def test_orchestrator_service_handles_low_risk_input() -> None:
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(),
        operational_service=OperationalService(),
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
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.recovered_context == []
    assert result.operation_result is not None
    assert result.operation_result.status == OperationStatus.COMPLETED
    assert [event.event_name for event in result.events] == [
        "input_received",
        "memory_recovered",
        "intent_classified",
        "governance_checked",
        "operation_dispatched",
        "operation_completed",
        "memory_recorded",
    ]



def test_orchestrator_service_blocks_sensitive_action() -> None:
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(),
        operational_service=OperationalService(),
    )
    result = service.handle_input(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
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
    assert result.events[-2].event_name == "governance_blocked"
    assert result.events[-1].event_name == "memory_recorded"
    assert "bloqueada" in result.response_text



def test_orchestrator_service_recovers_previous_context_for_same_session() -> None:
    service = OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=MemoryService(),
        operational_service=OperationalService(),
    )
    first_contract = InputContract(
        request_id=RequestId("req-3"),
        session_id=SessionId("sess-3"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Please plan the sprint.",
        timestamp="2026-03-17T00:00:00Z",
    )
    second_contract = InputContract(
        request_id=RequestId("req-4"),
        session_id=SessionId("sess-3"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Analyze the previous plan.",
        timestamp="2026-03-17T00:01:00Z",
    )

    service.handle_input(first_contract)
    second_result = service.handle_input(second_contract)

    assert len(second_result.recovered_context) == 1
    assert "Please plan the sprint." in second_result.recovered_context[0]
    assert second_result.operation_result is not None
