from synthesis_engine.engine import SynthesisEngine


def test_synthesis_engine_name() -> None:
    assert SynthesisEngine.name == "synthesis-engine"
