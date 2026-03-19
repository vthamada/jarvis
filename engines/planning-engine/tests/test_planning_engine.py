from planning_engine.engine import PlanningContext, PlanningEngine

from shared.contracts import SpecialistContributionContract


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"


def test_planning_engine_builds_structured_plan_for_planning() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=[
                "context_summary=previous plan created",
                "mission_semantic_brief=mission_goal=Plan milestone M3",
                "mission_focus=strategy,planning",
            ],
            active_domains=["strategy", "productivity"],
            active_minds=["mente_executiva", "mente_estrategica"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar ambicao estrategica com proxima acao segura"],
            specialist_hints=["especialista_planejamento_operacional"],
        )
    )

    assert plan.goal == "Plan milestone M3"
    assert plan.recommended_task_type == "draft_plan"
    assert len(plan.steps) >= 3
    assert "strategy" in plan.active_domains
    assert "context_summary=previous plan created" in plan.rationale
    assert plan.tensions_considered == ["equilibrar ambicao estrategica com proxima acao segura"]
    assert plan.specialist_hints == ["especialista_planejamento_operacional"]
    assert any("fio condutor semantico" in step for step in plan.steps)
    assert "mission_goal=Plan milestone M3" in plan.rationale
    assert "foco=strategy,planning" in plan.rationale


def test_planning_engine_refines_plan_with_specialist_contributions() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_executiva", "mente_estrategica"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar ambicao estrategica com proxima acao segura"],
            specialist_hints=["especialista_planejamento_operacional"],
        )
    )
    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary=(
            "especialista_planejamento_operacional: executar o plano em etapas pequenas "
            "e verificaveis"
        ),
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="especialista_planejamento_operacional",
                role="planejamento_operacional_subordinado",
                focus="sequenciamento reversivel e checkpoints claros",
                findings=["priorizar a menor acao segura antes de expandir escopo"],
                recommendation="executar o plano em etapas pequenas e verificaveis",
                confidence=0.78,
            )
        ],
    )

    assert any("checkpoint intermediario" in step for step in refined.steps)
    assert any("incorporar contribuicoes especialistas" in item for item in refined.constraints)
    assert "especialistas=" in refined.rationale
    assert "especialistas=" in refined.plan_summary


def test_planning_engine_refines_plan_for_governance_specialist() -> None:
    engine = PlanningEngine()
    base_plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan governance update",
            recovered_context=[],
            active_domains=["governance"],
            active_minds=["mente_executiva", "mente_etica"],
            knowledge_snippets=["Priorize cautela operacional."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar solicitacao do usuario com limites normativos"],
            specialist_hints=["especialista_revisao_governanca"],
        )
    )
    refined = engine.refine_task_plan(
        base_plan,
        specialist_summary=(
            "especialista_revisao_governanca: manter o plano no escopo local ate "
            "confirmacao explicita"
        ),
        specialist_contributions=[
            SpecialistContributionContract(
                specialist_type="especialista_revisao_governanca",
                role="revisao_governanca_subordinada",
                focus="cautela operacional, auditoria e validacao",
                findings=["verificar se o plano permanece totalmente reversivel"],
                recommendation="manter o plano no escopo local ate confirmacao explicita",
                confidence=0.84,
            )
        ],
    )

    assert refined.requires_human_validation is True
    assert any("cautela operacional reforcada" in risk for risk in refined.risks)
    assert any("condicoes de auditoria" in step for step in refined.steps)


def test_planning_engine_builds_analysis_plan_without_operation_escalation() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="analysis",
            query="Analyze the current rollout trade-offs",
            recovered_context=[],
            active_domains=["analysis"],
            active_minds=["mente_analitica", "mente_critica"],
            knowledge_snippets=["Compare custo, risco e reversibilidade."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="analysis_only",
            cognitive_rationale="intent=analysis; mente_primaria=mente_analitica",
            tensions=["equilibrar profundidade analitica com conclusao util"],
            specialist_hints=["especialista_analise_estruturada"],
        )
    )

    assert plan.recommended_task_type == "produce_analysis_brief"
    assert plan.requires_human_validation is False
    assert any("comparar" in step for step in plan.steps)
    assert "especialista_analise_estruturada" in plan.specialist_hints


def test_planning_engine_marks_ambiguous_request_for_clarification() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan and analyze the roadmap",
            recovered_context=[],
            active_domains=["strategy"],
            active_minds=["mente_executiva"],
            knowledge_snippets=[],
            risk_markers=[],
            requires_clarification=True,
            preferred_response_mode="clarifying_guidance",
            cognitive_rationale="intent=planning; mente_primaria=mente_executiva",
            tensions=["equilibrar ambicao estrategica com proxima acao segura"],
            specialist_hints=["especialista_planejamento_operacional"],
        )
    )

    assert plan.recommended_task_type == "general_response"
    assert any("clarificar" in step for step in plan.steps)
    assert any("ambiguo" in risk for risk in plan.risks)
