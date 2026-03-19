from identity_engine.engine import IdentityEngine


def test_identity_engine_name() -> None:
    assert IdentityEngine.name == "identity-engine"


def test_identity_engine_builds_profile_and_style() -> None:
    engine = IdentityEngine()
    profile = engine.get_profile()

    assert "Sistema Cognitivo Geral" in profile.official_definition
    assert engine.build_response_style(intent="planning", blocked=False).startswith("estruturado")
