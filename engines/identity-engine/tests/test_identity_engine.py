from identity_engine.engine import IdentityEngine


def test_identity_engine_name() -> None:
    assert IdentityEngine.name == "identity-engine"
