from shared.contracts import GovernanceDecisionContract, InputContract
from shared.events import INTERNAL_EVENT_NAMES
from shared.schemas import INPUT_SCHEMA
from shared.state import SYSTEM_IDENTITY
from shared.types import (
    ChannelType,
    GovernanceCheckId,
    GovernanceDecisionId,
    InputType,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)


def test_input_schema_matches_contract_name() -> None:
    assert INPUT_SCHEMA.contract_name == "InputContract"


def test_input_contract_can_be_instantiated() -> None:
    contract = InputContract(
        request_id=RequestId("req-1"),
        session_id=SessionId("sess-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="hello",
        timestamp="2026-03-16T00:00:00Z",
    )
    assert contract.content == "hello"


def test_governance_decision_uses_canonical_enums() -> None:
    decision = GovernanceDecisionContract(
        decision_id=GovernanceDecisionId("decision-1"),
        governance_check_id=GovernanceCheckId("check-1"),
        risk_level=RiskLevel.MODERATE,
        decision=PermissionDecision.ALLOW,
        justification="safe enough",
        timestamp="2026-03-16T00:00:00Z",
    )
    assert decision.decision == PermissionDecision.ALLOW


def test_internal_event_names_include_governance_blocked() -> None:
    assert "governance_blocked" in INTERNAL_EVENT_NAMES


def test_system_identity_has_core_principles() -> None:
    assert "truth_and_quality" in SYSTEM_IDENTITY.nuclear_principles
    assert "utility" in SYSTEM_IDENTITY.nuclear_principles
