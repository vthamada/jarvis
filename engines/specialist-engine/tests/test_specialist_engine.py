from specialist_engine.engine import SpecialistEngine

from shared.contracts import (
    DeliberativePlanContract,
    DomainSpecialistRouteContract,
    SpecialistSharedMemoryContextContract,
)


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
        rationale="contexto=baseline; apoio=local",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["operational_planning_specialist"],
        success_criteria=["plano deve indicar a menor proxima acao segura"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="definir objetivo",
        continuity_action="continuar",
        open_loops=["fechar checkpoint principal"],
    )


def test_specialist_engine_name() -> None:
    assert SpecialistEngine.name == "specialist-engine"


def test_specialist_engine_returns_subordinated_contributions_only_when_rule_matches() -> None:
    engine = SpecialistEngine()
    handoff_plan = engine.plan_handoffs(
        intent="planning",
        plan=sample_plan(),
        knowledge_snippets=["Priorize clareza de objetivo."],
        shared_memory_contexts={
            "operational_planning_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="operational_planning_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=operational_planning_specialist "
                    "continuidade=continuar"
                ),
                write_policy="through_core_only",
                related_mission_ids=["mission-related"],
                memory_refs=["mem-record-1"],
                semantic_focus=["strategy"],
                open_loops=["fechar checkpoint principal"],
                source_mission_goal="Plan milestone M3",
            )
        },
        session_id="sess-specialist",
        mission_id="mission-specialist",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="planning",
        plan=sample_plan(),
        knowledge_snippets=["Priorize clareza de objetivo."],
        handoff_plan=handoff_plan,
    )
    assert handoff_plan.invocations[0].shared_memory_context is not None
    assert handoff_plan.invocations[0].shared_memory_context.write_policy == "through_core_only"
    assert any(
        item.startswith("shared_memory_brief=")
        for item in handoff_plan.invocations[0].handoff_inputs
    )
    assert review.specialist_hints == ["operational_planning_specialist"]
    assert review.invocations
    assert review.invocations[0].specialist_type == "operational_planning_specialist"
    assert review.invocations[0].boundary.response_channel == "through_core"
    assert review.invocations[0].boundary.tool_access_mode == "none"
    assert review.invocations[0].boundary.memory_write_mode == "through_core_only"
    assert review.contributions
    assert review.contributions[0].specialist_type == "operational_planning_specialist"
    assert review.contributions[0].invocation_id == review.invocations[0].invocation_id
    assert "through_core_only" in review.contributions[0].output_hints
    assert (
        "etapas pequenas" in review.summary
        or "etapas pequenas" in review.contributions[0].recommendation
    )
    assert review.findings
    assert "sem resposta direta ao usuario" in review.boundary_summary


def test_specialist_engine_links_promoted_domain_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    software_plan = DeliberativePlanContract(
        plan_summary="avaliar ajuste em serviço Python com impacto controlado",
        goal="Review Python service rollout",
        steps=["mapear contratos", "comparar mudança", "recomendar próximo passo"],
        active_domains=["software_development", "analysis"],
        active_minds=["mente_analitica"],
        constraints=["through_core_only"],
        risks=["sem risco material alem do escopo controlado do v1"],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=False,
        rationale="contexto=software; apoio=local",
        tensions_considered=["equilibrar profundidade analitica com conclusao util"],
        specialist_hints=["software_change_specialist"],
        success_criteria=["comparacao deve preservar contratos e rollback"],
        dominant_tension="equilibrar profundidade analitica com conclusao util",
        smallest_safe_next_action="mapear contratos ativos",
        continuity_action="continuar",
        open_loops=["comparar mudança no serviço"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=software_plan,
        knowledge_snippets=["Prefira interfaces estáveis."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="software_development",
                specialist_type="software_change_specialist",
                specialist_mode="guided",
                routing_reason="rota canônica de software em modo guiado",
            )
        ],
        shared_memory_contexts={
            "software_change_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="software_change_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=software_change_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Review Python service rollout",
                mission_context_brief=(
                    "goal=Review Python service rollout | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=software_development,analysis | "
                    "semantic_focus=software_development, analysis | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=comparar mudanca no servico | "
                    "source_mission_id=mission-software"
                ),
                consumer_profile="software_change_review",
                consumer_objective=(
                    "avaliar segurança da mudança, impacto de implementação "
                    "e direção de patch recomendada"
                ),
                expected_deliverables=[
                    "implementation_findings",
                    "change_risk_summary",
                    "recommended_patch_direction",
                ],
                telemetry_focus=[
                    "contract_impact",
                    "change_safety",
                    "implementation_trace",
                ],
                related_mission_ids=["mission-software-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["software_development", "analysis"],
                open_loops=["comparar mudanca no servico"],
                recurrent_context_status="recoverable",
                recurrent_interaction_count=3,
                recurrent_context_brief=(
                    "specialist=software_change_specialist | interactions=3 | "
                    "domains=software_development,analysis"
                ),
                recurrent_domain_focus=["software_development", "analysis"],
                recurrent_continuity_modes=["continuar"],
            )
        },
        session_id="sess-software",
        mission_id="mission-software",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="analysis",
        plan=software_plan,
        knowledge_snippets=["Prefira interfaces estáveis."],
        handoff_plan=handoff_plan,
    )

    specialist_inputs = handoff_plan.invocations[0].handoff_inputs
    assert handoff_plan.selections[0].linked_domain == "software_development"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert handoff_plan.invocations[0].linked_domain == "software_development"
    assert handoff_plan.invocations[0].selection_mode == "guided"
    assert review.contributions[0].specialist_type == "software_change_specialist"
    assert "domain_guided_specialist" in review.contributions[0].output_hints
    assert any(
        item.startswith("consumer_mode=domain_guided_memory_packet")
        for item in specialist_inputs
    )
    assert any(item.startswith("mission_context_brief=") for item in specialist_inputs)
    assert any(item.startswith("domain_context_brief=") for item in specialist_inputs)
    assert any(item.startswith("continuity_context_brief=") for item in specialist_inputs)
    assert any(
        item.startswith("consumer_profile=software_change_review")
        for item in specialist_inputs
    )
    assert any(item.startswith("consumer_objective=") for item in specialist_inputs)
    assert any(item.startswith("expected_deliverables=") for item in specialist_inputs)
    assert any(item.startswith("telemetry_focus=") for item in specialist_inputs)
    assert any(
        item.startswith("recurrent_context_status=recoverable")
        for item in specialist_inputs
    )
    assert any(item.startswith("recurrent_interaction_count=3") for item in specialist_inputs)
    assert any(item.startswith("recurrent_context_brief=") for item in specialist_inputs)
    assert handoff_plan.invocations[0].expected_outputs == [
        "implementation_findings",
        "change_risk_summary",
        "recommended_patch_direction",
        "through_core_only",
    ]


def test_specialist_engine_rejects_software_specialist_if_not_shadow_route() -> None:
    engine = SpecialistEngine()
    non_shadow_plan = DeliberativePlanContract(
        plan_summary="avaliar estrategia sem especialista de software",
        goal="Review strategy options",
        steps=["mapear opcoes", "comparar", "recomendar"],
        active_domains=["strategy"],
        active_minds=["mente_analitica"],
        constraints=["through_core_only"],
        risks=[],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=False,
        rationale="contexto=strategy",
        tensions_considered=[],
        specialist_hints=["software_change_specialist"],
        success_criteria=["recomendacao clara"],
        dominant_tension="equilibrar profundidade analitica com conclusao util",
        smallest_safe_next_action="mapear opcoes",
        continuity_action=None,
        open_loops=[],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=non_shadow_plan,
        knowledge_snippets=["Priorize clareza de objetivo."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="strategy",
                specialist_type="software_change_specialist",
                specialist_mode="standard",
                routing_reason="rota nao-shadow — deve ser rejeitada pelo registry",
            )
        ],
        session_id="sess-non-shadow",
        mission_id="mission-non-shadow",
        requested_by_service="orchestrator-service",
    )

    # "strategy" is not a software specialist route in the registry,
    # so the software specialist must be rejected regardless of specialist_mode in the route.
    assert handoff_plan.selections[0].specialist_type == "software_change_specialist"
    assert handoff_plan.selections[0].selection_status == "not_eligible"
    assert not handoff_plan.invocations



def test_specialist_engine_links_guided_analysis_domain_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    analysis_plan = DeliberativePlanContract(
        plan_summary="comparar trade-offs do rollout com criterio explicito",
        goal="Compare rollout evidence",
        steps=["observar", "comparar", "recomendar"],
        active_domains=["analysis", "decision_risk"],
        active_minds=["mente_analitica"],
        constraints=["through_core_only"],
        risks=[],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=False,
        rationale="contexto=analysis; apoio=local",
        tensions_considered=["equilibrar profundidade analitica com conclusao util"],
        specialist_hints=["structured_analysis_specialist"],
        success_criteria=["criterio dominante deve ficar explicito"],
        dominant_tension="equilibrar profundidade analitica com conclusao util",
        smallest_safe_next_action="comparar trade-offs centrais",
        continuity_action="continuar",
        open_loops=["consolidar criterio dominante"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=analysis_plan,
        knowledge_snippets=["Priorize criterio explicito de decisao."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="analysis",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de analise estruturada em modo guiado",
            )
        ],
        shared_memory_contexts={
            "structured_analysis_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="structured_analysis_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=structured_analysis_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Compare rollout evidence",
                mission_context_brief=(
                    "goal=Compare rollout evidence | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=analysis,decision_risk | "
                    "semantic_focus=analysis, decision_risk | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=consolidar criterio dominante | "
                    "source_mission_id=mission-analysis"
                ),
                related_mission_ids=["mission-analysis-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["analysis", "decision_risk"],
                open_loops=["consolidar criterio dominante"],
            )
        },
        session_id="sess-analysis",
        mission_id="mission-analysis",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="analysis",
        plan=analysis_plan,
        knowledge_snippets=["Priorize criterio explicito de decisao."],
        handoff_plan=handoff_plan,
    )

    assert handoff_plan.selections[0].linked_domain == "analysis"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert review.contributions[0].role == "analise_estruturada_guided"
    assert "domain_guided_specialist" in review.contributions[0].output_hints



def test_specialist_engine_links_guided_governance_domain_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    governance_plan = DeliberativePlanContract(
        plan_summary="avaliar limites do rollout com governanca explicita",
        goal="Review governance limits",
        steps=["mapear risco", "comparar limites", "recomendar contenção"],
        active_domains=["governance", "decision_risk"],
        active_minds=["mente_etica"],
        constraints=["through_core_only"],
        risks=["governance_risk"],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=True,
        rationale="contexto=governance; apoio=local",
        tensions_considered=["equilibrar solicitacao do usuario com limites normativos"],
        specialist_hints=["governance_review_specialist"],
        success_criteria=["limite dominante deve ficar explicito"],
        dominant_tension="equilibrar solicitacao do usuario com limites normativos",
        smallest_safe_next_action="explicitar o limite dominante antes de operar",
        continuity_action="continuar",
        open_loops=["validar limite dominante"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=governance_plan,
        knowledge_snippets=["Priorize trilha auditavel."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="governance",
                specialist_type="governance_review_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de governanca em modo guiado",
            )
        ],
        shared_memory_contexts={
            "governance_review_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="governance_review_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=governance_review_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Review governance limits",
                mission_context_brief=(
                    "goal=Review governance limits | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=governance,decision_risk | "
                    "semantic_focus=governance, decision_risk | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=validar limite dominante | "
                    "source_mission_id=mission-governance"
                ),
                related_mission_ids=["mission-governance-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["governance", "decision_risk"],
                open_loops=["validar limite dominante"],
            )
        },
        session_id="sess-governance",
        mission_id="mission-governance",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="analysis",
        plan=governance_plan,
        knowledge_snippets=["Priorize trilha auditavel."],
        handoff_plan=handoff_plan,
    )

    assert handoff_plan.selections[0].linked_domain == "governance"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert review.contributions[0].role == "revisao_governanca_guided"
    assert "domain_guided_specialist" in review.contributions[0].output_hints



def test_specialist_engine_links_guided_operational_readiness_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    readiness_plan = DeliberativePlanContract(
        plan_summary="estruturar readiness checks do release",
        goal="Plan readiness checks",
        steps=["mapear readiness", "definir checkpoints", "sugerir rollback"],
        active_domains=["operational_readiness", "observability"],
        active_minds=["mente_executiva"],
        constraints=["through_core_only"],
        risks=[],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=readiness; apoio=local",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["operational_planning_specialist"],
        success_criteria=["checkpoint dominante deve ficar explicito"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="explicitar o checkpoint dominante",
        continuity_action="continuar",
        open_loops=["fechar checkpoint de readiness"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="planning",
        plan=readiness_plan,
        knowledge_snippets=["Priorize checkpoints reversiveis."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="operational_readiness",
                specialist_type="operational_planning_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de readiness operacional em modo guiado",
            )
        ],
        shared_memory_contexts={
            "operational_planning_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="operational_planning_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=operational_planning_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Plan readiness checks",
                mission_context_brief=(
                    "goal=Plan readiness checks | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=operational_readiness,observability | "
                    "semantic_focus=operational_readiness, observability | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=fechar checkpoint de readiness | "
                    "source_mission_id=mission-readiness"
                ),
                related_mission_ids=["mission-readiness-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["operational_readiness", "observability"],
                open_loops=["fechar checkpoint de readiness"],
            )
        },
        session_id="sess-readiness",
        mission_id="mission-readiness",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="planning",
        plan=readiness_plan,
        knowledge_snippets=["Priorize checkpoints reversiveis."],
        handoff_plan=handoff_plan,
    )

    assert handoff_plan.selections[0].linked_domain == "operational_readiness"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert review.contributions[0].role == "planejamento_operacional_guided"
    assert "domain_guided_specialist" in review.contributions[0].output_hints



def test_specialist_engine_links_guided_strategy_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    strategy_plan = DeliberativePlanContract(
        plan_summary="comparar direcoes estrategicas do release",
        goal="Plan strategic options",
        steps=["mapear opcoes", "comparar trade-offs", "recomendar criterio"],
        active_domains=["strategy", "decision_risk"],
        active_minds=["mente_decisoria"],
        constraints=["through_core_only"],
        risks=[],
        recommended_task_type="draft_plan",
        requires_human_validation=False,
        rationale="contexto=strategy; apoio=local",
        tensions_considered=["equilibrar ambicao estrategica com a menor proxima acao segura"],
        specialist_hints=["structured_analysis_specialist"],
        success_criteria=["criterio estrategico dominante deve ficar explicito"],
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
        smallest_safe_next_action="comparar trade-offs centrais",
        continuity_action="continuar",
        open_loops=["fechar criterio estrategico dominante"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="planning",
        plan=strategy_plan,
        knowledge_snippets=["Priorize criterio explicito de decisao."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="strategy",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de estrategia em modo guiado",
            )
        ],
        shared_memory_contexts={
            "structured_analysis_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="structured_analysis_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=structured_analysis_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Plan strategic options",
                mission_context_brief=(
                    "goal=Plan strategic options | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=strategy,decision_risk | "
                    "semantic_focus=strategy, decision_risk | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=fechar criterio estrategico dominante | "
                    "source_mission_id=mission-strategy"
                ),
                related_mission_ids=["mission-strategy-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["strategy", "decision_risk"],
                open_loops=["fechar criterio estrategico dominante"],
            )
        },
        session_id="sess-strategy",
        mission_id="mission-strategy",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="planning",
        plan=strategy_plan,
        knowledge_snippets=["Priorize criterio explicito de decisao."],
        handoff_plan=handoff_plan,
    )

    assert handoff_plan.selections[0].linked_domain == "strategy"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert review.contributions[0].role == "analise_estruturada_guided"
    assert "domain_guided_specialist" in review.contributions[0].output_hints


def test_specialist_engine_links_guided_decision_risk_specialist_explicitly() -> None:
    engine = SpecialistEngine()
    decision_risk_plan = DeliberativePlanContract(
        plan_summary="avaliar reversibilidade e gate dominante da decisao",
        goal="Review decision risk",
        steps=["mapear risco", "comparar reversibilidade", "recomendar gate dominante"],
        active_domains=["decision_risk", "governance"],
        active_minds=["mente_etica"],
        constraints=["through_core_only"],
        risks=["decision_risk"],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=True,
        rationale="contexto=decision_risk; apoio=local",
        tensions_considered=["equilibrar urgencia de decisao com reversibilidade segura"],
        specialist_hints=["governance_review_specialist"],
        success_criteria=["gate dominante deve ficar explicito"],
        dominant_tension="equilibrar urgencia de decisao com reversibilidade segura",
        smallest_safe_next_action="explicitar o gate dominante antes de operar",
        continuity_action="continuar",
        open_loops=["fechar gate dominante de decisao"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=decision_risk_plan,
        knowledge_snippets=["Priorize reversibilidade explicita."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="decision_risk",
                specialist_type="governance_review_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de decision risk em modo guiado",
            )
        ],
        shared_memory_contexts={
            "governance_review_specialist": SpecialistSharedMemoryContextContract(
                specialist_type="governance_review_specialist",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=governance_review_specialist continuidade=continuar"
                ),
                write_policy="through_core_only",
                consumer_mode="domain_guided_memory_packet",
                source_mission_goal="Review decision risk",
                mission_context_brief=(
                    "goal=Review decision risk | related=nenhuma | "
                    "recommendation=sem recomendacao dominante"
                ),
                domain_context_brief=(
                    "active_domains=decision_risk,governance | "
                    "semantic_focus=decision_risk, governance | "
                    "memory_refs=memory://mission,memory://relational"
                ),
                continuity_context_brief=(
                    "continuity_mode=continuar | "
                    "open_loops=fechar gate dominante de decisao | "
                    "source_mission_id=mission-decision-risk"
                ),
                related_mission_ids=["mission-decision-risk-related"],
                memory_refs=["memory://mission", "memory://relational"],
                semantic_focus=["decision_risk", "governance"],
                open_loops=["fechar gate dominante de decisao"],
            )
        },
        session_id="sess-decision-risk",
        mission_id="mission-decision-risk",
        requested_by_service="orchestrator-service",
    )
    review = engine.review_handoffs(
        intent="analysis",
        plan=decision_risk_plan,
        knowledge_snippets=["Priorize reversibilidade explicita."],
        handoff_plan=handoff_plan,
    )

    assert handoff_plan.selections[0].linked_domain == "decision_risk"
    assert handoff_plan.selections[0].selection_mode == "guided"
    assert review.contributions[0].role == "revisao_governanca_guided"
    assert "domain_guided_specialist" in review.contributions[0].output_hints


def test_specialist_engine_prefers_active_domain_order_when_routes_share_specialist() -> None:
    engine = SpecialistEngine()
    plan = DeliberativePlanContract(
        plan_summary="avaliar risco e limite dominante da decisao",
        goal="Review decision risk",
        steps=["mapear risco", "comparar reversibilidade", "definir gate"],
        active_domains=["decision_risk", "governance"],
        active_minds=["mente_etica"],
        constraints=["through_core_only"],
        risks=["decision_risk"],
        recommended_task_type="produce_analysis_brief",
        requires_human_validation=True,
        rationale="contexto=decision_risk; apoio=local",
        tensions_considered=["equilibrar urgencia com reversibilidade"],
        specialist_hints=["governance_review_specialist"],
        success_criteria=["gate dominante deve ficar explicito"],
        dominant_tension="equilibrar urgencia com reversibilidade",
        smallest_safe_next_action="comparar gates de contencao",
        continuity_action="continuar",
        open_loops=["fechar gate dominante"],
    )

    handoff_plan = engine.plan_handoffs(
        intent="analysis",
        plan=plan,
        knowledge_snippets=["Priorize reversibilidade explicita."],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="governance",
                specialist_type="governance_review_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de governanca em modo guiado",
            ),
            DomainSpecialistRouteContract(
                domain_name="decision_risk",
                specialist_type="governance_review_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica de decision risk em modo guiado",
            ),
        ],
        shared_memory_contexts={},
        session_id="sess-shared-governance-specialist",
        mission_id="mission-shared-governance-specialist",
        requested_by_service="orchestrator-service",
    )

    assert handoff_plan.selections[0].linked_domain == "decision_risk"
    assert handoff_plan.selections[0].selection_mode == "guided"

