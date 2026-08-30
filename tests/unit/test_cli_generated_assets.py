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

    assert len(model) == len(COMMAND_REGISTRY.definitions) == 40
    assert [item.definition.command_id for item in model] == [
        item.command_id for item in COMMAND_REGISTRY.definitions
    ]
    assert first == second
    assert str(Path.cwd()) not in first
    assert "`command-reference`" in first
    assert "`completion`" in first
    assert "`action-confirm`" in first


@pytest.mark.parametrize("shell", ["powershell", "bash", "zsh"])
def test_completion_is_deterministic_and_contains_registry_commands(shell: str) -> None:
    first = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell=shell)
    second = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell=shell)

    assert first == second
    assert "jarvis-console" in first
    assert "operator-outcomes" in first
    assert "workflow-lifecycle" in first
    assert "workflow-transition" in first
    assert "action-confirm" in first
    assert "completion" in first
    assert "\neval " not in first
    assert "\teval " not in first
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


def test_completion_keeps_mutating_command_format_choices_text_only() -> None:
    bash = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell="bash")
    zsh = render_shell_completion(COMMAND_REGISTRY, build_parser(), shell="zsh")
    powershell = render_shell_completion(
        COMMAND_REGISTRY,
        build_parser(),
        shell="powershell",
    )

    assert "if [[ -z $command && $prev == '--format' ]]" in bash
    assert 'technology-experiment-pack:--format) candidates="text"' in bash
    assert 'action-confirm:--format) candidates="text"' in bash
    assert "if [[ -z $command && $previous == '--format' ]]" in zsh
    assert "technology-experiment-pack:--format)" in zsh
    assert "action-confirm:--format)" in zsh
    assert "_values 'value' 'text'" in zsh
    assert (
        "'technology-experiment-pack|--format' = @('text')" in powershell
    )
    assert "'action-confirm|--format' = @('text')" in powershell
