from planning_engine.engine import PlanningContext, PlanningEngine


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"


def test_planning_engine_builds_structured_plan_for_planning() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=["context_summary=previous plan created"],
            active_domains=["strategy", "productivity"],
            active_minds=["mente_executiva", "mente_estrategica"],
            knowledge_snippets=["Priorize clareza de objetivo."],
            risk_markers=[],
            requires_clarification=False,
            preferred_response_mode="plan_and_operate",
        )
    )

    assert plan.goal == "Plan milestone M3"
    assert plan.recommended_task_type == "draft_plan"
    assert len(plan.steps) >= 3
    assert "strategy" in plan.active_domains
    assert "context_summary=previous plan created" in plan.rationale


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
        )
    )

    assert plan.recommended_task_type == "produce_analysis_brief"
    assert plan.requires_human_validation is False
    assert any("comparar" in step for step in plan.steps)


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
        )
    )

    assert plan.recommended_task_type == "general_response"
    assert any("clarificar" in step for step in plan.steps)
    assert any("ambiguo" in risk for risk in plan.risks)
