from identity_engine.engine import IdentityEngine
from shared.contracts import GovernanceDecisionContract
from shared.types import GovernanceCheckId, GovernanceDecisionId, PermissionDecision, RiskLevel
from synthesis_engine.engine import SynthesisEngine, SynthesisInput


def test_synthesis_engine_name() -> None:
    assert SynthesisEngine.name == "synthesis-engine"


def test_synthesis_engine_composes_allowed_response() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    response = engine.compose(
        SynthesisInput(
            intent="planning",
            identity_profile=identity,
            response_style="estruturado",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-1"),
                governance_check_id=GovernanceCheckId("check-1"),
                risk_level=RiskLevel.LOW,
                decision=PermissionDecision.ALLOW,
                justification="ok",
                timestamp="2026-03-18T00:00:00Z",
            ),
            recovered_context=["context_summary=previous context"],
            active_minds=["mente_executiva"],
            active_domains=["strategy"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            operation_result=None,
        )
    )

    assert "JARVIS em modo estruturado" in response


def test_synthesis_engine_blocks_when_governance_blocks() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    response = engine.compose(
        SynthesisInput(
            intent="sensitive_action",
            identity_profile=identity,
            response_style="firme",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-2"),
                governance_check_id=GovernanceCheckId("check-2"),
                risk_level=RiskLevel.HIGH,
                decision=PermissionDecision.BLOCK,
                justification="blocked",
                timestamp="2026-03-18T00:00:00Z",
            ),
            recovered_context=[],
            active_minds=["mente_etica"],
            active_domains=["governance"],
            knowledge_snippets=[],
            operation_result=None,
        )
    )

    assert "nao permite execucao direta" in response
