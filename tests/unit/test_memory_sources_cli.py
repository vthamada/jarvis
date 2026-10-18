"""Standalone commands require opt-in before source IO; fixed refusals only."""

import importlib
import io
import json
import sys

import pytest

COMMANDS = ("memory_retention_cli", "source_comparison_cli")


class NoInput:
    def isatty(self):
        pytest.fail("unauthorized stdin inspection")

    def read(self, *_args):
        pytest.fail("unauthorized stdin read")


@pytest.mark.parametrize("name", COMMANDS)
def test_authorization_precedes_any_stdin_or_store_access(name, monkeypatch, capsys):
    module = importlib.import_module("apps.jarvis_console." + name)
    monkeypatch.setattr(sys, "stdin", NoInput())
    assert module.main([]) == 2
    value = json.loads(capsys.readouterr().err)
    assert value == {"error_code": name.removesuffix("_cli") + "_refused"}


@pytest.mark.parametrize("name", COMMANDS)
def test_unknown_options_do_not_echo_private_values(name, capsys):
    module = importlib.import_module("apps.jarvis_console." + name)
    assert module.main(["--authorized", "--private-secret", "private-marker"]) == 2
    value = capsys.readouterr()
    assert not value.out and "private-marker" not in value.err
    assert json.loads(value.err) == {"error_code": name.removesuffix("_cli") + "_refused"}


@pytest.mark.parametrize("name", COMMANDS)
def test_invalid_input_cannot_reflect_source_or_parser_details(name, monkeypatch, capsys):
    module = importlib.import_module("apps.jarvis_console." + name)
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"private": "invalid'))
    assert module.main(["--authorized"]) == 2
    value = capsys.readouterr()
    assert not value.out and "private" not in value.err
