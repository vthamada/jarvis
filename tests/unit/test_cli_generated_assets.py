from argparse import ArgumentParser
from pathlib import Path

import pytest

from apps.jarvis_console.cli import build_parser
from apps.jarvis_console.reference import (
    build_reference_model,
    render_command_reference,
    render_shell_completion,
)
from apps.jarvis_console.registry import (
    COMMAND_REGISTRY,
    CommandCategory,
    CommandDefinition,
    CommandExecutionMode,
    CommandRegistry,
)
from tools.generate_cli_assets import generate_cli_assets


def test_generated_cli_assets_match_versioned_files_byte_for_byte() -> None:
    assets = generate_cli_assets()

    assert len(assets) == 4
    for path, expected in assets.items():
        assert path.read_text(encoding="utf-8") == expected


def test_reference_model_is_complete_deterministic_and_path_free() -> None:
    parser = build_parser()
    model = build_reference_model(COMMAND_REGISTRY, parser)
    first = render_command_reference(COMMAND_REGISTRY, parser)
    second = render_command_reference(COMMAND_REGISTRY, build_parser())

    assert len(model) == len(COMMAND_REGISTRY.definitions) == 31
    assert [item.definition.command_id for item in model] == [
        item.command_id for item in COMMAND_REGISTRY.definitions
    ]
    assert first == second
    assert str(Path.cwd()) not in first
    assert "`command-reference`" in first
    assert "`completion`" in first


@pytest.mark.parametrize("shell", ["powershell", "bash", "zsh"])
def test_completion_is_deterministic_and_contains_registry_commands(shell: str) -> None:
    first = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell=shell)
    second = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell=shell)

    assert first == second
    assert "jarvis-console" in first
    assert "operator-outcomes" in first
    assert "completion" in first
    assert "eval " not in first
    assert "Invoke-Expression" not in first


def test_completion_rejects_unsafe_parser_choices() -> None:
    definition = CommandDefinition(
        command_id="unsafe-test",
        help_text="Exercise completion validation.",
        handler_name="run_unsafe_test_command",
        category=CommandCategory.OBSERVABILITY,
        execution_mode=CommandExecutionMode.STANDALONE,
    )
    registry = CommandRegistry((definition,))
    parser = ArgumentParser(prog="jarvis-console")
    subparsers = parser.add_subparsers(dest="command", required=True)
    command_parser = subparsers.add_parser(
        "unsafe-test",
        help=definition.help_text,
    )
    command_parser.add_argument("--value", choices=["safe", "unsafe;command"])

    with pytest.raises(ValueError, match="unsafe shell completion tokens"):
        render_shell_completion(registry, parser, shell="bash")
