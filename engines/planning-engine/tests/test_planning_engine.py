from planning_engine.engine import PlanningContext, PlanningEngine


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"


def test_planning_engine_builds_contextual_plan() -> None:
    engine = PlanningEngine()
    plan = engine.build_task_plan(
        PlanningContext(
            intent="planning",
            query="Plan milestone M3",
            recovered_context=["previous plan created"],
            active_domains=["strategy", "productivity"],
            knowledge_snippets=["Priorize clareza de objetivo."],
        )
    )

    assert "estruturar etapas praticas" in plan
    assert "strategy" in plan
