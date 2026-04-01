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
        specialist_hints=["operational_planning_specialist"],
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
        primary_mind="mente_executiva",
        primary_mind_family="estrategica_decisoria",
        primary_domain_driver="estrategia_e_pensamento_sistemico",
        arbitration_source="mind_registry",
        primary_route="strategy",
        route_consumer_profile="strategy_tradeoff_review",
        route_consumer_objective=(
            "clarificar trade-offs estrategicos, enquadramento de cenario e direcao recomendada"
        ),
        route_expected_deliverables=["tradeoff_map", "decision_criteria"],
        route_telemetry_focus=["tradeoff_clarity", "decision_trace"],
        route_workflow_profile="strategic_direction_workflow",
        route_workflow_steps=[
            "frame the strategic scenario and the decision horizon",
            "compare trade-offs, constraints and leverage points",
        ],
        route_workflow_checkpoints=["scenario_framed", "tradeoffs_compared"],
        route_workflow_decision_points=[
            "scenario_scope_confirmed",
            "tradeoff_criteria_governed",
        ],
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
            session_continuity_brief=(
                "sessao segue ancorada em 'Plan milestone M3', com continuidade ativa em "
                "'alinhar checkpoint principal'"
            ),
            session_continuity_mode="continuar",
            session_anchor_goal="Plan milestone M3",
        )
    )
    assert "Continuidade ativa" in response
    assert "sessao segue ancorada em 'Plan milestone M3'" in response
    assert "Leitura do objetivo" in response
    assert "Julgamento" in response
    assert "Recomendacao" in response
    assert "retomar alinhar checkpoint principal" in response
    assert "workflow ativo: strategic direction workflow" in response
    assert "foco final: direcao recomendada, criterios e trade-offs dominantes" in response
    assert "checkpoint ativo: scenario framed" in response
    assert "gate governado: scenario scope confirmed" in response
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
            session_continuity_brief=(
                "sessao entrou em reformulacao governada de 'Plan milestone M3' "
                "e aguarda validacao explicita"
            ),
            session_continuity_mode="reformular",
            session_anchor_goal="Plan milestone M3",
        )
    )
    assert "Continuidade ativa: sessao entrou em reformulacao governada" in response
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
            session_continuity_brief=(
                "sessao retoma continuidade relacionada em 'Analyze rollout risks.', "
                "preservando rastreabilidade do escopo atual"
            ),
            session_continuity_mode="retomar",
            session_anchor_goal="Analyze rollout risks.",
        )
    )
    assert "Continuidade ativa: sessao retoma continuidade relacionada" in response
    assert "retomada explicita de continuidade relacionada" in response
    assert "missao relacionada 'Analyze rollout risks.' deve ser retomada agora" in response
    assert "retomada relacionada precisa justificar por que supera os loops ativos" in response


def test_synthesis_engine_surfaces_governed_replay_recovery() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    replay_plan = sample_plan()
    replay_plan.continuity_replay_status = "awaiting_validation"
    replay_plan.continuity_recovery_mode = "governed_review"
    replay_plan.continuity_resume_point = "continuar:alinhar checkpoint principal"
    replay_plan.requires_human_validation = True
    replay_plan.risks = ["checkpoint recuperado ainda aguarda validacao explicita"]
    response = engine.compose(
        SynthesisInput(
            intent="planning",
            identity_profile=identity,
            response_style="estruturado",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-5"),
                governance_check_id=GovernanceCheckId("check-5"),
                risk_level=RiskLevel.MODERATE,
                decision=PermissionDecision.DEFER_FOR_VALIDATION,
                justification=(
                    "O checkpoint recuperado ainda aguarda validacao e nao pode "
                    "ser retomado automaticamente."
                ),
                timestamp="2026-03-18T00:00:00Z",
                conditions=["Manter apenas analise e rastreabilidade ate revisao explicita."],
            ),
            recovered_context=["continuity_replay_status=awaiting_validation"],
            active_minds=["mente_executiva"],
            active_domains=["strategy"],
            knowledge_snippets=[],
            deliberative_plan=replay_plan,
            specialist_contributions=[],
            operation_result=None,
            identity_mode="structured_planning",
            session_continuity_brief=(
                "sessao segue ancorada em 'Plan milestone M3', com continuidade ativa em "
                "'alinhar checkpoint principal'"
            ),
            session_continuity_mode="continuar",
            session_anchor_goal="Plan milestone M3",
        )
    )
    assert "checkpoint recuperado ainda aguarda validacao" in response
    assert "permanece em modo governado" in response
    assert "aguarda validacao explicita" in response


def test_synthesis_engine_uses_guided_semantic_and_procedural_memory_hints() -> None:
    engine = SynthesisEngine()
    identity = IdentityEngine().get_profile()
    response = engine.compose(
        SynthesisInput(
            intent="planning",
            identity_profile=identity,
            response_style="estruturado",
            governance_decision=GovernanceDecisionContract(
                decision_id=GovernanceDecisionId("decision-6"),
                governance_check_id=GovernanceCheckId("check-6"),
                risk_level=RiskLevel.LOW,
                decision=PermissionDecision.ALLOW_WITH_CONDITIONS,
                justification="ok",
                timestamp="2026-03-18T00:00:00Z",
            ),
            recovered_context=["context_summary=guided memory available"],
            active_minds=["mente_executiva"],
            active_domains=["strategy"],
            knowledge_snippets=["Preserve continuidade segura."],
            deliberative_plan=sample_plan(),
            specialist_contributions=[],
            operation_result=None,
            identity_mode="structured_planning",
            arbitration_summary="mente_executiva lidera com foco unico",
            session_continuity_brief=(
                "sessao segue ancorada em 'Plan milestone M3', com continuidade ativa em "
                "'alinhar checkpoint principal'"
            ),
            session_continuity_mode="continuar",
            session_anchor_goal="Plan milestone M3",
            guided_memory_specialists=["structured_analysis_specialist"],
            semantic_memory_focus=["estrategia_e_pensamento_sistemico", "strategy"],
            procedural_memory_hint="manter o ultimo fio de recomendacao governada",
        )
    )
    assert (
        "memoria guiada reforca framing estrategico e comparacao de trade-offs em "
        "estrategia_e_pensamento_sistemico, strategy" in response
    )
    assert (
        "mente executiva ancora o dominio primario estrategia e pensamento sistemico "
        "via rota strategy" in response
    )
    assert "strategy tradeoff review" in response
    assert "tradeoff map" in response
    assert "tradeoff clarity" in response
    assert "workflow ativo: strategic direction workflow" in response
    assert "foco final: direcao recomendada, criterios e trade-offs dominantes" in response
    assert "checkpoint ativo: scenario framed" in response
    assert "gate governado: scenario scope confirmed" in response
    assert (
        "apoio procedural orienta continuidade do fio decisorio e criterio de progressao: "
        "manter o ultimo fio de recomendacao governada" in response
    )
