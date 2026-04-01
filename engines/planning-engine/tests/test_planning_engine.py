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
            specialist_hints=["operational_planning_specialist"],
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
    assert plan.continuity_action == "retomar"
    assert plan.continuity_source == "related_mission"
    assert plan.continuity_target_mission_id == "mission-a"
    assert plan.continuity_target_goal == "Plan milestone M3 rollout."
    assert plan.steps[0] == "retomar explicitamente a missao relacionada antes de abrir novo escopo"
    assert plan.continuity_reason is not None
    assert "missao_relacionada=Plan milestone M3 rollout." in plan.rationale
    assert "prioridade_relacionada=0.80" in plan.rationale
    assert "motivo_continuidade=missao relacionada mission-a venceu o ranking" in plan.rationale
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


def test_planning_engine_closes_active_loop_explicitly() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Encerrar checkpoint principal da sprint.",
            recovered_context=[
                "identity_continuity_brief=objetivo=Plan milestone M3; prioridade=checkpoint",
                "open_loops=checkpoint principal;alinhar aprovacao final",
                "mission_goal=Plan milestone M3",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Feche loops explicitamente antes de abrir nova frente."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            dominant_goal="fechar o ciclo atual com clareza",
            identity_mode="structured_planning",
            open_loops=["checkpoint principal", "alinhar aprovacao final"],
            mission_goal="Plan milestone M3",
        )
    )
    assert plan.continuity_action == "encerrar"
    assert plan.steps[0] == "fechar explicitamente o loop principal: checkpoint principal"
    assert (
        plan.continuity_reason
        == "pedido explicita fechamento do loop principal checkpoint principal"
    )
    assert (
        plan.smallest_safe_next_action
        == "fechar checkpoint principal com criterio explicito"
    )


def test_planning_engine_carries_primary_route_contract_into_plan() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan strategic options for the release.",
            recovered_context=[],
            active_domains=["strategy", "analysis"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=["Priorize criterio explicito de decisao."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            canonical_domains=[
                "estrategia_e_pensamento_sistemico",
                "tomada_de_decisao_complexa",
            ],
            primary_canonical_domain="estrategia_e_pensamento_sistemico",
            primary_route="strategy",
            route_consumer_profile="strategy_tradeoff_review",
            route_consumer_objective=(
                "clarificar trade-offs estrategicos, enquadramento de cenario e direcao recomendada"
            ),
            route_expected_deliverables=[
                "tradeoff_map",
                "decision_criteria",
                "recommended_direction",
            ],
            route_telemetry_focus=[
                "tradeoff_clarity",
                "decision_trace",
                "domain_alignment",
            ],
            route_workflow_profile="strategic_direction_workflow",
            cognitive_rationale="intent=planning; mente_primaria=mente_decisoria",
            dominant_goal="comparar direcoes estrategicas do release",
            identity_mode="structured_planning",
            primary_mind="mente_decisoria",
            dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        )
    )

    assert plan.primary_route == "strategy"
    assert plan.route_consumer_profile == "strategy_tradeoff_review"
    assert "tradeoff_map" in plan.route_expected_deliverables
    assert "tradeoff_clarity" in plan.route_telemetry_focus
    assert plan.route_workflow_profile == "strategic_direction_workflow"
    assert "consumer_profile=strategy_tradeoff_review" in plan.rationale
    assert any("tradeoff_map" in criterion for criterion in plan.success_criteria)
    assert any(
        "orientar a saida para tradeoff map e decision criteria" in step
        for step in plan.steps
    )
    assert any(
        "preservar o foco observavel da rota ativa: tradeoff clarity" in constraint
        for constraint in plan.constraints
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
                "operational_planning_specialist",
                "structured_analysis_specialist",
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
                specialist_type="operational_planning_specialist",
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
                specialist_type="structured_analysis_specialist",
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


def test_planning_engine_routes_governed_replay_to_safe_recovery() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Continue the sprint plan.",
            recovered_context=[
                "continuity_replay_status=awaiting_validation",
                "continuity_recovery_mode=governed_review",
                "continuity_resume_point=continuar:fechar checkpoint principal",
            ],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=["Retome com revisao explicita quando houver checkpoint governado."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            mission_goal="Plan milestone M3",
            open_loops=["fechar checkpoint principal"],
            continuity_replay_status="awaiting_validation",
            continuity_recovery_mode="governed_review",
            continuity_resume_point="continuar:fechar checkpoint principal",
            continuity_requires_manual_resume=True,
        )
    )
    assert plan.recommended_task_type == "general_response"
    assert plan.requires_human_validation is True
    assert plan.steps[0].startswith("revisar o ponto de retomada antes de continuar")
    assert any("checkpoint governado" in constraint for constraint in plan.constraints)
    assert any("aguarda validacao" in risk for risk in plan.risks)
    assert plan.continuity_replay_status == "awaiting_validation"
    assert plan.continuity_recovery_mode == "governed_review"
    assert plan.continuity_resume_point == "continuar:fechar checkpoint principal"
