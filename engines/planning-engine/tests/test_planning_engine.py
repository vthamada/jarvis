from planning_engine.engine import PlanningContext, PlanningEngine

from shared.contracts import SpecialistContributionContract


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"


def test_planning_engine_builds_structured_plan_with_continuity() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=[
                "context_summary=previous plan created",
                (
                    "identity_continuity_brief=objetivo=Plan milestone M3; "
                    "prioridade=definir escopo final"
                ),
                "open_loops=definir escopo final;alinhar checkpoints",
                "mission_semantic_brief=objetivo=Plan milestone M3",
                "mission_focus=strategy,planning",
            ],
            active_domains=["strategy", "productivity"],
            active_minds=["mente_executiva", "mente_estrategica"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar ambicao estrategica com a menor proxima acao segura"],
            specialist_hints=["especialista_planejamento_operacional"],
            dominant_goal="definir um caminho executavel e seguro",
            secondary_goals=["preservar espaco para analise antes de executar"],
            identity_mode="structured_planning",
            primary_mind="mente_executiva",
            supporting_minds=["mente_estrategica", "mente_pragmatica"],
            dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
            arbitration_summary="mente_executiva lidera com apoio estrategico",
            identity_continuity_brief=(
                "objetivo=Plan milestone M3; prioridade=definir escopo final"
            ),
            open_loops=["definir escopo final", "alinhar checkpoints"],
            mission_semantic_brief="objetivo=Plan milestone M3",
            mission_focus=["strategy", "planning"],
            last_decision_frame="planning",
            mission_goal="Plan milestone M3",
            mission_recommendation="retomar o escopo final antes da proxima acao",
        )
    )
    assert plan.goal == "definir um caminho executavel e seguro"
    assert plan.recommended_task_type == "draft_plan"
    assert plan.continuity_action == "continuar"
    assert plan.open_loops == ["definir escopo final", "alinhar checkpoints"]
    assert plan.steps[0] == "retomar o loop principal da missao: definir escopo final"
    assert any("loop principal da missao" in criterion for criterion in plan.success_criteria)
    assert (
        plan.smallest_safe_next_action
        == "retomar definir escopo final antes de abrir novo escopo"
    )
    assert "conflito_missao=nenhum" in plan.rationale
    assert "recomendacao_previa=retomar o escopo final antes da proxima acao" in plan.rationale
    assert plan.continuity_source == "active_mission"


def test_planning_engine_marks_related_continuity_source_when_candidate_is_present() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the risk analysis.",
            recovered_context=["context_summary=milestone M3 teve dois fluxos proximos"],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_executiva"],
            knowledge_snippets=["Preserve continuidade entre missoes relacionadas."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="dar continuidade analitica segura",
            identity_mode="deep_analysis",
            related_mission_id="mission-a",
            related_mission_goal="Plan milestone M3 rollout.",
            related_continuity_reason="foco_compartilhado=strategy,planning",
            related_continuity_priority=0.8,
            related_continuity_confidence=0.7,
            continuity_recommendation="retomar_missao_relacionada",
            continuity_ranking_summary=(
                "missao relacionada mission-a venceu o ranking de continuidade com prioridade 0.80"
            ),
        )
    )
    assert plan.continuity_action == "continuar"
    assert plan.continuity_source == "related_mission"
    assert plan.continuity_target_mission_id == "mission-a"
    assert plan.continuity_target_goal == "Plan milestone M3 rollout."
    assert "missao_relacionada=Plan milestone M3 rollout." in plan.rationale
    assert "prioridade_relacionada=0.80" in plan.rationale
    assert "ranking_continuidade=missao relacionada mission-a venceu o ranking" in plan.rationale


def test_planning_engine_reformulates_when_new_request_conflicts_with_active_mission() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Start a new marketing campaign instead.",
            recovered_context=[
                (
                    "identity_continuity_brief=objetivo=Plan milestone M3; "
                    "prioridade=definir escopo final"
                ),
                "open_loops=definir escopo final;alinhar checkpoints",
                "mission_goal=Plan milestone M3",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Preserve rastreabilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            dominant_goal="definir um caminho executavel e seguro",
            identity_mode="structured_planning",
            primary_mind="mente_executiva",
            supporting_minds=["mente_estrategica"],
            arbitration_summary="mente_executiva lidera com foco em continuidade",
            identity_continuity_brief=(
                "objetivo=Plan milestone M3; prioridade=definir escopo final"
            ),
            open_loops=["definir escopo final", "alinhar checkpoints"],
            mission_goal="Plan milestone M3",
            mission_recommendation="retomar o escopo final antes da proxima acao",
            last_decision_frame="planning",
        )
    )
    assert plan.continuity_action == "reformular"
    assert plan.recommended_task_type == "general_response"
    assert plan.requires_human_validation is True
    assert (
        plan.steps[0]
        == "reformular a missao ativa sem perder rastreabilidade: Plan milestone M3"
    )
    assert any("deslocar a missao ativa" in risk for risk in plan.risks)
    assert (
        "conflito_missao=pedido atual desloca o foco da missao ativa 'Plan milestone M3'"
        in plan.rationale
    )


def test_planning_engine_refines_plan_and_consolidates_specialists() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze rollout options",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare custo, risco e reversibilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            tensions=["equilibrar profundidade analitica com conclusao util"],
            specialist_hints=[
                "especialista_planejamento_operacional",
                "especialista_analise_estruturada",
            ],
            dominant_goal="produzir leitura confiavel antes de agir",
            identity_mode="deep_analysis",
            primary_mind="mente_analitica",
            supporting_minds=["mente_critica", "mente_logica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_summary="mente_analitica lidera com apoio critico",
        )
    )
    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary="ajustar checkpoints e explicitar criterio dominante",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="especialista_planejamento_operacional",
                role="planejamento_operacional_subordinado",
                focus="sequenciamento reversivel e checkpoints claros",
                findings=[
                    "constraint: validar checkpoint intermediario com base em contexto local",
                    "open_loop: confirmar checkpoint principal",
                ],
                recommendation=(
                    "encadear o plano em etapas pequenas, verificaveis "
                    "e conectadas a missao"
                ),
                confidence=0.79,
            ),
            SpecialistContributionContract(
                specialist_type="especialista_analise_estruturada",
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "success: conclusao deve explicitar o criterio dominante de escolha",
                    "constraint: separar observacao, implicacao e recomendacao final",
                ],
                recommendation=(
                    "fundir comparacao, implicacao e recomendacao "
                    "em uma unica linha analitica"
                ),
                confidence=0.82,
            ),
        ],
    )
    assert refined.specialist_resolution_summary is not None
    assert refined.open_loops == ["confirmar checkpoint principal"]
    assert any("checkpoint intermediario" in step for step in refined.steps)
    assert any("criterio dominante" in criterion for criterion in refined.success_criteria)
    assert "resolucao_especialistas=" in refined.rationale
