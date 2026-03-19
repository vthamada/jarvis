from cognitive_engine.engine import CognitiveEngine


def test_cognitive_engine_name() -> None:
    assert CognitiveEngine.name == "cognitive-engine"


def test_cognitive_engine_selects_minds_tensions_and_specialist_hints_for_analysis() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=["update"],
        retrieved_domains=["analysis", "strategy"],
    )

    assert snapshot.primary_mind == "mente_executiva"
    assert "mente_analitica" in snapshot.active_minds
    assert "mente_probabilistica" in snapshot.active_minds
    assert snapshot.active_domains == ["analysis", "strategy"]
    assert snapshot.tensions
    assert "equilibrar profundidade analitica com conclusao util" in snapshot.tensions
    assert "especialista_analise_estruturada" in snapshot.specialist_hints
    assert snapshot.deliberation_notes
