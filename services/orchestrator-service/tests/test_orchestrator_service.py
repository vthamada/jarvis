from orchestrator_service.service import OrchestratorResponse, OrchestratorService
from shared.contracts import InputContract
from shared.types import (
    ChannelType,
    InputType,
    PermissionDecision,
    RequestId,
    SessionId,
)


def test_orchestrator_service_name() -> None:
    assert OrchestratorService.name == "orchestrator-service"


def test_orchestrator_service_handles_low_risk_input() -> None:
    service = OrchestratorService()
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
    assert [event.event_name for event in result.events] == [
        "input_received",
        "intent_classified",
        "governance_checked",
    ]


def test_orchestrator_service_blocks_sensitive_action() -> None:
    service = OrchestratorService()
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
    assert result.events[-1].event_name == "governance_blocked"
    assert "bloqueada" in result.response_text
