from planning_engine.engine import PlanningEngine


def test_planning_engine_name() -> None:
    assert PlanningEngine.name == "planning-engine"
