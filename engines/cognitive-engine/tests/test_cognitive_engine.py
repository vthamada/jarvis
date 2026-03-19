from cognitive_engine.engine import CognitiveEngine


def test_cognitive_engine_name() -> None:
    assert CognitiveEngine.name == "cognitive-engine"


def test_cognitive_engine_selects_minds_for_analysis() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=["update"],
        retrieved_domains=["analysis", "strategy"],
    )

    assert "mente_analitica" in snapshot.active_minds
    assert "mente_probabilistica" in snapshot.active_minds
    assert snapshot.active_domains == ["analysis", "strategy"]
