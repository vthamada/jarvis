from identity_engine.engine import IdentityEngine
from synthesis_engine.engine import SynthesisEngine, SynthesisInput

from shared.contracts import (
    DeliberativePlanContract,
    GovernanceDecisionContract,
    SpecialistContributionContract,
)
from shared.types import GovernanceCheckId, GovernanceDecisionId, PermissionDecision, RiskLevel


def test_synthesis_engine_name() -> None:
    assert SynthesisEngine.name == "synthesis-engine"


def sample_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="decompor objetivo em etapas reversiveis",
        goal="Plan milestone M3",
        steps=["definir objetivo", "listar etapas", "recomendar proxima acao"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=context_summary=previous context; apoio=Priorize clareza de objetivo.",
        tensions_considered=["equilibrar ambicao estrategica com proxima acao segura"],
        specialist_hints=["especialista_planejamento_operacional"],
    )


def sample_specialist_contributions() -> list[SpecialistContributionContract]:
    return [
        SpecialistContributionContract(
            specialist_type="especialista_planejamento_operacional",
            role="planejamento_operacional_subordinado",
            focus="sequenciamento reversivel e checkpoints claros",
            findings=[
                "priorizar a menor acao segura antes de expandir escopo",
                "explicitar checkpoints intermediarios para preservar rastreabilidade",
            ],
            recommendation="executar o plano em etapas pequenas e verificaveis",
            confidence=0.78,
        )
    ]


def test_synthesis_engine_composes_deliberative_allowed_response() -> None:
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
            deliberative_plan=sample_plan(),
            specialist_contributions=sample_specialist_contributions(),
            operation_result=None,
        )
    )

    assert "Leitura do objetivo" in response
    assert "Linha de raciocinio" in response
    assert "Plano ou recomendacao" in response
    assert "Arbitragem interna" in response
    assert "Especializacao subordinada" in response
    assert "Contribuicoes especialistas" in response


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
            deliberative_plan=sample_plan(),
            specialist_contributions=[],
            operation_result=None,
        )
    )

    assert "nao permite execucao direta" in response
    assert "Leitura atual" in response
