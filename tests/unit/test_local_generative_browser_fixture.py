"""Browser harness requires explicit local authorization before runtime creation."""

import importlib.util
from pathlib import Path

import pytest


@pytest.mark.parametrize("arguments", [[], ["--untrusted", "private-secret"],
                                     ["--authorized", "--port", "private-secret"]])
def test_fixture_refuses_without_io_or_reflecting_input(arguments, monkeypatch, capsys):
    path = Path(__file__).resolve().parents[1] / "support/local_generative_web_fixture.py"
    spec = importlib.util.spec_from_file_location("owned_local_generative_browser", path)
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    from apps.jarvis_api import __main__ as startup
    monkeypatch.setattr(startup, "create_owned_runtime", lambda: pytest.fail("unexpected IO"))
    try:
        code = fixture.main(arguments)
    except SystemExit as error:
        code = error.code
    assert code == 2
    output = capsys.readouterr()
    assert output.err in {"fixture_authorization_required\n", "invalid_fixture_options\n"}
    assert not output.out and "private-secret" not in output.err
