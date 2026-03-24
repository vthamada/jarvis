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
        specialist_hints=["especialista_planejamento_operacional"],
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
            "especialista_planejamento_operacional": SpecialistSharedMemoryContextContract(
                specialist_type="especialista_planejamento_operacional",
                sharing_mode="core_mediated_read_only",
                continuity_mode="continuar",
                shared_memory_brief=(
                    "specialist=especialista_planejamento_operacional "
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
    assert review.specialist_hints == ["especialista_planejamento_operacional"]
    assert review.invocations
    assert review.invocations[0].specialist_type == "especialista_planejamento_operacional"
    assert review.invocations[0].boundary.response_channel == "through_core"
    assert review.invocations[0].boundary.tool_access_mode == "none"
    assert review.invocations[0].boundary.memory_write_mode == "through_core_only"
    assert review.contributions
    assert review.contributions[0].specialist_type == "especialista_planejamento_operacional"
    assert review.contributions[0].invocation_id == review.invocations[0].invocation_id
    assert "through_core_only" in review.contributions[0].output_hints
    assert (
        "etapas pequenas" in review.summary
        or "etapas pequenas" in review.contributions[0].recommendation
    )
    assert review.findings
    assert "sem resposta direta ao usuario" in review.boundary_summary


def test_specialist_engine_links_domain_shadow_specialist_explicitly() -> None:
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
        specialist_hints=["especialista_software_subordinado"],
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
                specialist_type="especialista_software_subordinado",
                specialist_mode="shadow",
                routing_reason="rota canônica de software em shadow mode",
            )
        ],
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

    assert handoff_plan.selections[0].linked_domain == "software_development"
    assert handoff_plan.selections[0].selection_mode == "shadow"
    assert handoff_plan.invocations[0].linked_domain == "software_development"
    assert handoff_plan.invocations[0].selection_mode == "shadow"
    assert review.contributions[0].specialist_type == "especialista_software_subordinado"
    assert "domain_shadow_specialist" in review.contributions[0].output_hints


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
        specialist_hints=["especialista_software_subordinado"],
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
                specialist_type="especialista_software_subordinado",
                specialist_mode="standard",
                routing_reason="rota nao-shadow — deve ser rejeitada pelo registry",
            )
        ],
        session_id="sess-non-shadow",
        mission_id="mission-non-shadow",
        requested_by_service="orchestrator-service",
    )

    # "strategy" is not a shadow_specialist route in the registry,
    # so the software specialist must be rejected regardless of specialist_mode in the route.
    assert handoff_plan.selections[0].specialist_type == "especialista_software_subordinado"
    assert handoff_plan.selections[0].selection_status == "not_eligible"
    assert not handoff_plan.invocations
