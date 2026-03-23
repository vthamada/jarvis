from specialist_engine.engine import SpecialistEngine

from shared.contracts import DeliberativePlanContract, SpecialistSharedMemoryContextContract


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
