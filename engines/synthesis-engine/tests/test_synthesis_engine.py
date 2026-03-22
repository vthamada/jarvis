from identity_engine.engine import IdentityEngine
from synthesis_engine.engine import SynthesisEngine, SynthesisInput

from shared.contracts import DeliberativePlanContract, GovernanceDecisionContract
from shared.types import GovernanceCheckId, GovernanceDecisionId, PermissionDecision, RiskLevel


def test_synthesis_engine_name() -> None:
    assert SynthesisEngine.name == "synthesis-engine"


def sample_plan() -> DeliberativePlanContract:
    return DeliberativePlanContract(
        plan_summary="objetivo=Plan milestone M3; modo=structured_planning; continuidade=continuar",
        goal="Plan milestone M3",
        steps=[
            "retomar o loop principal da missao: alinhar checkpoint principal",
            "decompor etapas",
        ],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["low-risk"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="objetivo_dominante=Plan milestone M3; continuidade=ativo",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["especialista_planejamento_operacional"],
        success_criteria=["resposta deve fechar ou avancar o loop principal da missao"],
        specialist_resolution_summary="encadear o plano em etapas pequenas",
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="retomar alinhar checkpoint principal antes de abrir novo escopo",
        continuity_action="continuar",
        continuity_reason=(
            "existem loops ativos que mantem a missao atual ancorada em "
            "alinhar checkpoint principal"
        ),
        open_loops=["alinhar checkpoint principal"],
    )


def test_synthesis_engine_composes_unitary_allowed_response() -> None:
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
            specialist_contributions=[],
            operation_result=None,
            identity_mode="structured_planning",
            arbitration_summary="mente_executiva lidera com apoio estrategico e foco unico",
        )
    )
    assert "Leitura do objetivo" in response
    assert "Julgamento" in response
    assert "Recomendacao" in response
    assert "retomar alinhar checkpoint principal" in response
    assert "Contribuicoes especialistas" not in response
    assert "Dominios:" not in response
    assert "Mentes:" not in response


def test_synthesis_engine_surfaces_reformulation_without_pipeline_listing() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    reformulation_plan = sample_plan()
    reformulation_plan.continuity_action = "reformular"
    reformulation_plan.requires_human_validation = True
    reformulation_plan.risks = [
        "pedido atual pode deslocar a missao ativa sem reformulacao explicita"
    ]
    response = engine.compose(
        SynthesisInput(
            intent="planning",
            identity_profile=identity,
            response_style="estruturado",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-3"),
                governance_check_id=GovernanceCheckId("check-3"),
                risk_level=RiskLevel.MODERATE,
                decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
                justification="ok",
                timestamp="2026-03-18T00:00:00Z",
                conditions=["manter a resposta rastreavel"],
            ),
            recovered_context=["context_summary=previous context"],
            active_minds=["mente_executiva"],
            active_domains=["strategy"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            deliberative_plan=reformulation_plan,
            specialist_contributions=[],
            operation_result=None,
            identity_mode="structured_planning",
            arbitration_summary="mente_executiva lidera com foco em continuidade",
        )
    )
    assert "tensiona a missao ativa" in response
    assert "explicitar como o novo pedido afeta alinhar checkpoint principal" in response
    assert "Dominios:" not in response


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
            identity_mode="governed_refusal",
        )
    )
    assert "Leitura do objetivo" in response
    assert "a governanca atual exige conter a acao" in response


def test_synthesis_engine_surfaces_related_resumption_cleanly() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    resumed_plan = sample_plan()
    resumed_plan.continuity_action = "retomar"
    resumed_plan.continuity_reason = "missao relacionada venceu o ranking de continuidade"
    resumed_plan.continuity_source = "related_mission"
    resumed_plan.continuity_target_mission_id = "mission-a"
    resumed_plan.continuity_target_goal = "Analyze rollout risks."
    resumed_plan.open_loops = ["alinhar checkpoint principal"]
    response = engine.compose(
        SynthesisInput(
            intent="analysis",
            identity_profile=identity,
            response_style="estruturado",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-4"),
                governance_check_id=GovernanceCheckId("check-4"),
                risk_level=RiskLevel.MODERATE,
                decision=PermissionDecision.DEFER_FOR_VALIDATION,
                justification="validar disputa de direcao antes de retomar",
                timestamp="2026-03-18T00:00:00Z",
                conditions=["manter apenas analise e rastreabilidade ate revisao explicita"],
            ),
            recovered_context=["context_summary=related continuity available"],
            active_minds=["mente_analitica"],
            active_domains=["analysis"],
            knowledge_snippets=["Retome continuidade relacionada sem parecer deriva arbitraria."],
            deliberative_plan=resumed_plan,
            specialist_contributions=[],
            operation_result=None,
            identity_mode="deep_analysis",
            arbitration_summary="mente_analitica lidera com foco em continuidade relacionada",
        )
    )
    assert "retomada explicita de continuidade relacionada" in response
    assert "missao relacionada 'Analyze rollout risks.' deve ser retomada agora" in response
    assert "retomada relacionada precisa justificar por que supera os loops ativos" in response
