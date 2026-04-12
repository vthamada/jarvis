from planning_engine.engine import AdaptiveIntervention, PlanningContext, PlanningEngine

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
        == "retomar definir escopo final antes de abrir novo escopo; "
        "ancora cognitiva: mente primaria mente executiva ancora a deliberacao "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )
    assert plan.metacognitive_guidance_applied is True
    assert plan.metacognitive_guidance_summary is not None
    assert "success_criteria" in plan.metacognitive_effects
    assert "smallest_safe_next_action" in plan.metacognitive_effects
    assert "conflito_missao=nenhum" in plan.rationale
    assert "recomendacao_previa=retomar o escopo final antes da proxima acao" in plan.rationale
    assert plan.continuity_source == "active_mission"
    assert plan.capability_decision_status == "resolved"
    assert plan.capability_decision_selected_mode == "core_with_local_operation"
    assert plan.capability_decision_authorization_status == "governance_review_required"
    assert plan.capability_decision_tool_class == "local_artifact_generation"
    assert plan.capability_decision_handoff_mode == "through_core_only"
    assert "local_safe_operation" in plan.capability_decision_selected_capabilities
    assert "specialist_handoff" in plan.capability_decision_selected_capabilities


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


def test_planning_engine_contains_capabilities_for_clarification_only() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Need help, but first clarify the target environment.",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=True,
            preferred_response_mode="analysis_only",
            dominant_goal="esclarecer o pedido antes de qualquer execucao",
        )
    )

    assert plan.capability_decision_status == "contained"
    assert plan.capability_decision_selected_mode == "clarification_only"
    assert plan.capability_decision_authorization_status == "clarification_required"
    assert plan.capability_decision_handoff_mode == "none"
    assert plan.capability_decision_tool_class is None
    assert plan.capability_decision_selected_capabilities == ["core_reasoning"]


def test_planning_engine_uses_memory_route_priority_and_mind_composition_guidance() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the governed analysis.",
            recovered_context=["context_summary=analysis mission already active"],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica", "mente_logica"],
            knowledge_snippets=["Preserve the analytical chain."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_scope_confirmed"],
            route_workflow_decision_points=["insight_governed"],
            route_expected_deliverables=["analysis_frame"],
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="aprofundar a leitura analitica sem perder continuidade",
            primary_mind="mente_analitica",
            primary_mind_family="fundamental",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            supporting_minds=["mente_logica", "mente_critica"],
            suppressed_minds=["mente_pragmatica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_summary="mente analitica lidera com revisao critica",
            mission_goal="Continue the governed analysis.",
            continuity_recommendation="retomar_missao_relacionada",
            related_mission_id="mission-analysis",
            related_mission_goal="Continue the governed analysis.",
            related_continuity_reason="foco_compartilhado=analysis",
            related_continuity_priority=0.92,
            continuity_ranking_summary="mission-analysis venceu o ranking de continuidade",
            memory_priority_status="memory_guided",
            memory_priority_domains=["analysis"],
            memory_priority_specialists=["structured_analysis_specialist"],
            memory_priority_sources=["mission_focus", "continuity_ranking"],
            memory_priority_summary="analysis:6[mission_focus,continuity_ranking]",
        )
    )

    assert "memory_priority_status=memory_guided" in plan.plan_summary
    assert "memory_priority_domains=analysis" in plan.rationale
    assert "reconciliar o apoio de mente_logica, mente_critica" in " ".join(plan.steps)
    assert any(
        "mente_pragmatica" in criterion for criterion in plan.success_criteria
    )
    assert "preservar a rota priorizada por memoria em analysis" in (
        plan.smallest_safe_next_action
    )


def test_planning_engine_uses_compaction_and_cross_session_recall_as_constraints() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Continue the release trade-off analysis.",
            recovered_context=[
                "context_summary=release analysis already exists",
                "context_compaction_status=compressed_live_context",
                "context_live_summary=turns=2;user_scope=recoverable;continuity=none;cross_session=active",
                "cross_session_recall_status=active",
                (
                    "cross_session_recall_summary="
                    "user_scope=intents=planning,analysis | "
                    "related=Plan milestone M3 rollout"
                ),
                "mission_semantic_brief=objetivo=Continue the release trade-off analysis.",
            ],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_executiva"],
            knowledge_snippets=["Preserve trade-off clarity."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            dominant_goal="aprofundar a leitura comparativa com continuidade",
            primary_mind="mente_analitica",
            primary_domain_driver="analise_estruturada_e_modelagem",
            mission_goal="Continue the release trade-off analysis.",
            context_compaction_status="compressed_live_context",
            context_compaction_summary="live_turns=2;continuity_hints=0;recalled_sources=2",
            context_live_summary=(
                "turns=2;user_scope=recoverable;continuity=none;cross_session=active"
            ),
            cross_session_recall_status="active",
            cross_session_recall_summary=(
                "user_scope=intents=planning,analysis | related=Plan milestone M3 rollout"
            ),
        )
    )

    assert any(
        "contexto vivo compactado" in constraint for constraint in plan.constraints
    )
    assert any(
        "recall cross-session" in constraint for constraint in plan.constraints
    )
    assert "context_compaction=compressed_live_context" in plan.plan_summary
    assert "cross_session_recall=active" in plan.rationale


def test_planning_engine_repairs_missing_required_contract_fields() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Stabilize the next step safely.",
            recovered_context=[],
            active_domains=[],
            active_minds=[],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
        )
    )

    assert plan.contract_validation_status == "repaired"
    assert plan.contract_validation_retry_applied is True
    assert "missing_required_field:active_minds" in plan.contract_validation_errors
    assert plan.active_minds == ["mente_executiva"]
    assert plan.steps
    assert plan.success_criteria


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
    assert plan.metacognitive_guidance_applied is True
    assert "containment_recommendation" in plan.metacognitive_effects
    assert plan.metacognitive_containment_recommendation is not None
    assert plan.capability_decision_status == "contained"
    assert plan.capability_decision_selected_mode == "contained_guidance"
    assert plan.capability_decision_authorization_status == "human_validation_required"
    assert plan.capability_decision_handoff_mode == "none"
    assert (
        "conflito_missao=pedido atual desloca o foco da missao ativa 'Plan milestone M3'"
        in plan.rationale
    )


def test_planning_engine_prefers_specialist_handoff_for_guided_analysis() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze the strongest pilot risk and explain the trade-offs.",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Preserve evidence-first reasoning."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            dominant_goal="aprofundar a leitura analitica com apoio especialista",
            route_workflow_profile="structured_analysis_workflow",
            specialist_hints=["structured_analysis_specialist"],
        )
    )

    assert plan.recommended_task_type == "produce_analysis_brief"
    assert plan.capability_decision_status == "resolved"
    assert plan.capability_decision_selected_mode == "core_with_specialist_handoff"
    assert plan.capability_decision_authorization_status == "pre_authorized_internal"
    assert plan.capability_decision_handoff_mode == "through_core_only"
    assert plan.capability_decision_tool_class is None
    assert "specialist_handoff" in plan.capability_decision_selected_capabilities


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
            route_workflow_steps=[
                "frame the strategic scenario and the decision horizon",
                "compare trade-offs, constraints and leverage points",
                "recommend a direction with explicit criteria",
            ],
            route_workflow_checkpoints=[
                "scenario_framed",
                "tradeoffs_compared",
                "direction_recommended",
            ],
            route_workflow_decision_points=[
                "scenario_scope_confirmed",
                "tradeoff_criteria_governed",
                "direction_governed",
            ],
            cognitive_rationale="intent=planning; mente_primaria=mente_decisoria",
            dominant_goal="comparar direcoes estrategicas do release",
            identity_mode="structured_planning",
            primary_mind="mente_decisoria",
            primary_mind_family="estrategica_decisoria",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            arbitration_source="mind_registry",
            mission_semantic_brief="objetivo=Plan strategic options; foco=trade-offs do release",
            mission_focus=["estrategia_e_pensamento_sistemico", "strategy"],
            mission_recommendation="manter o ultimo fio decisorio governado",
            procedural_artifact_status="candidate",
            procedural_artifact_ref="artifact://procedural/strategy/strategic_direction_workflow/v1",
            procedural_artifact_version=1,
            procedural_artifact_summary="procedimento guiado para revisao de trade-offs",
            last_decision_frame="strategic_tradeoff_review",
            dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        )
    )

    assert plan.primary_mind == "mente_decisoria"
    assert plan.primary_mind_family == "estrategica_decisoria"
    assert plan.primary_domain_driver == "estrategia_e_pensamento_sistemico"
    assert plan.arbitration_source == "mind_registry"
    assert plan.primary_route == "strategy"
    assert plan.route_consumer_profile == "strategy_tradeoff_review"
    assert "tradeoff_map" in plan.route_expected_deliverables
    assert "tradeoff_clarity" in plan.route_telemetry_focus
    assert plan.route_workflow_profile == "strategic_direction_workflow"
    assert plan.route_workflow_checkpoints[0] == "scenario_framed"
    assert plan.route_workflow_decision_points[0] == "scenario_scope_confirmed"
    assert plan.procedural_artifact_status == "candidate"
    assert (
        plan.procedural_artifact_ref
        == "artifact://procedural/strategy/strategic_direction_workflow/v1"
    )
    assert plan.procedural_artifact_version == 1
    assert "consumer_profile=strategy_tradeoff_review" in plan.rationale
    assert "dominio_primario=estrategia_e_pensamento_sistemico" in plan.rationale
    assert "procedural_artifact_status=candidate" in plan.rationale
    assert "artifact://procedural/strategy/strategic_direction_workflow/v1" in plan.rationale
    assert any("tradeoff_map" in criterion for criterion in plan.success_criteria)
    assert any(
        "direcao recomendada com criterios explicitos" in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "manter framing estrategico e comparacao de trade-offs" in criterion
        for criterion in plan.success_criteria
    )
    assert any("scenario framed" in criterion for criterion in plan.success_criteria)
    assert any(
        "preservar continuidade do fio decisorio e criterio de progressao" in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "ancora cognitiva mente decisoria deve manter estrategia e pensamento sistemico"
        in criterion
        for criterion in plan.success_criteria
    )
    assert any(
        "usar memoria semantica para framing estrategico e comparacao de trade-offs"
        in step
        for step in plan.steps
    )
    assert any(
        "usar memoria procedural para continuidade do fio decisorio e criterio de progressao"
        in step
        for step in plan.steps
    )
    assert any(
        "governar o decision point ativo: scenario scope confirmed" in constraint
        for constraint in plan.constraints
    )
    assert any(
        "usar memoria semantica apenas para framing estrategico e comparacao de trade-offs"
        in constraint
        for constraint in plan.constraints
    )
    assert any(
        "usar memoria procedural apenas para continuidade do fio decisorio e criterio de progressao"
        in constraint
        for constraint in plan.constraints
    )
    assert (
        plan.smallest_safe_next_action
        == "retomar comparar direcoes estrategicas do release preservando "
        "continuidade do fio decisorio e criterio de progressao: "
        "manter o ultimo fio decisorio governado; ancora cognitiva: "
        "mente decisoria ancora estrategia e pensamento sistemico via strategy "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )
    assert plan.metacognitive_guidance_applied is True
    assert plan.metacognitive_guidance_summary == (
        "mente decisoria ancora estrategia e pensamento sistemico via strategy "
        "sob tensao equilibrar ambicao estrategica com a menor proxima acao segura"
    )


def test_planning_engine_adds_priority_and_recommendation_memory_guidance() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Recommend the safest strategic direction.",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_decisoria"],
            knowledge_snippets=["Preserve strategic continuity."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            canonical_domains=["estrategia_e_pensamento_sistemico"],
            primary_canonical_domain="estrategia_e_pensamento_sistemico",
            primary_route="strategy",
            route_workflow_profile="strategic_direction_workflow",
            dominant_goal="clarificar a direcao recomendada",
            primary_mind="mente_decisoria",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            mission_goal="Recommend the safest strategic direction.",
            mission_semantic_brief="objetivo=Recommend the safest strategic direction.",
            mission_focus=["strategy", "tradeoff"],
            mission_recommendation="retomar o ultimo criterio estrategico governado",
            last_decision_frame="strategy",
        )
    )

    assert "priority" in plan.semantic_memory_effects
    assert "recommendation" in plan.semantic_memory_effects
    assert "priority" in plan.procedural_memory_effects
    assert "recommendation" in plan.procedural_memory_effects
    assert any("priorizar a leitura semantica" in step for step in plan.steps)
    assert any(
        "framing semantico dominante" in criterion for criterion in plan.success_criteria
    )
    assert any(
        "continuidade procedural do workflow" in criterion
        for criterion in plan.success_criteria
    )
    assert plan.metacognitive_effects == [
        "success_criteria",
        "smallest_safe_next_action",
    ]


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


def test_planning_engine_applies_mid_flow_cognitive_strategy_shift_when_impasse_persists() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze rollout options",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare custo, risco e reversibilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_framed"],
            route_workflow_decision_points=["analysis_scope_governed"],
            dominant_goal="produzir leitura confiavel antes de agir",
            primary_mind="mente_analitica",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            supporting_minds=["mente_critica", "mente_logica"],
            suppressed_minds=["mente_expressiva"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
        )
    )
    base_plan.mind_disagreement_status = "validation_required"
    base_plan.mind_validation_checkpoints = [
        (
            "validar a tensao dominante antes de concluir: equilibrar "
            "profundidade analitica com conclusao util"
        )
    ]
    base_plan.smallest_safe_next_action = "comparar os cenarios antes da sintese final"

    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary="trade-offs seguem abertos sob checkpoint governado",
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="structured_analysis_specialist",
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "risk: impasse analitico ainda pede validacao adicional",
                    "open_loop: consolidar criterio dominante",
                ],
                recommendation="manter comparacao governada antes da recomendacao final",
                confidence=0.82,
            ),
        ],
    )

    assert refined.cognitive_strategy_shift_applied is True
    assert refined.cognitive_strategy_shift_trigger == "guided_validation_impasse"
    assert refined.cognitive_strategy_shift_summary is not None
    assert "steps" in refined.cognitive_strategy_shift_effects
    assert refined.steps[0].startswith(
        "executar mudanca de estrategia cognitiva mid-flow:"
    )
    assert refined.smallest_safe_next_action == "revisar analysis framed antes da sintese final"
    assert any(
        "discordancia" in criterion or "criterio dominante" in criterion
        for criterion in refined.success_criteria
    )
    assert "mudanca_estrategia_mid_flow=guided_validation_impasse:" in refined.rationale
    assert refined.adaptive_intervention_selected_action == "specialist_reevaluation"
    assert refined.requires_human_validation is False


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


def test_planning_engine_prioritizes_specialist_reevaluation_for_analysis_workflows() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Compare the rollout trade-offs and decide the safest path.",
            recovered_context=[],
            active_domains=["analysis", "strategy"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare evidence before closing the recommendation."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            route_workflow_profile="structured_analysis_workflow",
            route_workflow_checkpoints=["analysis_framed"],
            route_workflow_decision_points=["tradeoff_review_governed"],
            supporting_minds=["mente_critica", "mente_logica"],
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            memory_retention_pressure="high",
        )
    )

    assert plan.adaptive_intervention_status == "applied"
    assert plan.adaptive_intervention_selected_action == "specialist_reevaluation"
    assert plan.adaptive_intervention_trigger == "mind_validation_required"
    assert "prioridade soberana de structured_analysis_workflow" in (
        plan.adaptive_intervention_reason or ""
    )


def test_planning_engine_prioritizes_memory_review_for_readiness_workflows() -> None:
    engine = PlanningEngine()
    selected = engine._select_workflow_adaptive_intervention(
        workflow_profile="operational_readiness_workflow",
        candidates=[
            AdaptiveIntervention(
                applied=True,
                status="applied",
                reason="pressao de memoria pede revisao antes de prosseguir",
                trigger="memory_retention_pressure_high",
                selected_action="memory_review_checkpoint",
                expected_effect="stabilize recall usage before final synthesis or reuse expansion",
                effects=["steps", "constraints"],
            ),
            AdaptiveIntervention(
                applied=True,
                status="applied",
                reason="discordancia especializada pede reavaliacao antes do fechamento",
                trigger="mind_validation_required",
                selected_action="specialist_reevaluation",
                expected_effect="force governed specialist reevaluation before closing",
                effects=["steps", "success_criteria"],
            ),
        ],
    )

    assert selected is not None
    assert selected.selected_action == "memory_review_checkpoint"
    assert selected.trigger == "memory_retention_pressure_high"
    assert "prioridade soberana de operational_readiness_workflow" in (
        selected.reason or ""
    )
