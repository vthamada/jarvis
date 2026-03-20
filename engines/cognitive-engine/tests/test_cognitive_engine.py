from cognitive_engine.engine import CognitiveEngine


def test_cognitive_engine_name() -> None:
    assert CognitiveEngine.name == "cognitive-engine"


def test_cognitive_engine_selects_primary_supporting_and_suppressed_minds() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=["update"],
        retrieved_domains=["analysis", "strategy"],
    )
    assert snapshot.primary_mind == "mente_analitica"
    assert "mente_critica" in snapshot.supporting_minds
    assert len(snapshot.supporting_minds) <= 2
    assert snapshot.suppressed_minds
    assert snapshot.active_domains == ["analysis", "strategy"]
    assert snapshot.dominant_tension == "equilibrar profundidade analitica com conclusao util"
    assert snapshot.arbitration_summary
    assert "especialista_analise_estruturada" in snapshot.specialist_hints
    assert snapshot.deliberation_notes
