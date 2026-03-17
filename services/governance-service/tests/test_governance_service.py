from governance_service.service import GovernanceAssessment, GovernanceService
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, PermissionDecision, RequestId, SessionId


def test_governance_service_name() -> None:
    assert GovernanceService.name == "governance-service"


def test_governance_service_allows_low_risk_request() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the next sprint.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
    )

    assert isinstance(result, GovernanceAssessment)
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.governance_check.requested_by_service == "orchestrator-service"



def test_governance_service_blocks_sensitive_request() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all project files now.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="sensitive_action",
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.requires_audit is True
