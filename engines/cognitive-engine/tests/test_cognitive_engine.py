from cognitive_engine.engine import CognitiveEngine


def test_cognitive_engine_name() -> None:
    assert CognitiveEngine.name == "cognitive-engine"
