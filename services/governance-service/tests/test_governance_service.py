from governance_service.service import GovernanceAssessment, GovernanceService
from shared.contracts import InputContract
from shared.types import (
    ChannelType,
    InputType,
    MemoryClass,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)


def test_governance_service_name() -> None:
    assert GovernanceService.name == "governance-service"


def test_governance_service_allows_low_risk_requests() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please plan the milestone.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
    )

    assert isinstance(result, GovernanceAssessment)
    assert result.governance_decision.decision == PermissionDecision.ALLOW
    assert result.governance_decision.risk_level == RiskLevel.LOW


def test_governance_service_conditions_moderate_risk_requests() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Please update the rollout plan.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="planning",
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
    assert result.governance_decision.requires_audit is True
    assert result.governance_decision.conditions


def test_governance_service_blocks_sensitive_action() -> None:
    service = GovernanceService()
    result = service.assess_request(
        InputContract(
            request_id=RequestId("req-3"),
            session_id=SessionId("sess-3"),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content="Delete all project files now.",
            timestamp="2026-03-17T00:00:00Z",
        ),
        intent="sensitive_action",
        requested_by_service="orchestrator-service",
    )

    assert result.governance_decision.decision == PermissionDecision.BLOCK
    assert result.governance_decision.risk_level == RiskLevel.HIGH


def test_governance_service_defers_critical_memory_mutation() -> None:
    service = GovernanceService()
    result = service.assess_memory_operation(
        memory_class=MemoryClass.IDENTITY,
        action="write",
        requested_by_service="memory-service",
    )

    assert result.governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION
    assert result.governance_decision.requires_rollback_plan is True
