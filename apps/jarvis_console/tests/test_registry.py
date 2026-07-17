from argparse import Namespace
from inspect import getsource

import pytest

from apps.jarvis_console import cli
from apps.jarvis_console.registry import (
    COMMAND_REGISTRY,
    CommandCategory,
    CommandDefinition,
    CommandExecutionMode,
    CommandOutputMode,
    CommandRegistry,
)


def parser_command_help() -> dict[str, str]:
    parser = cli.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if getattr(action, "choices", None)
    )
    return {
        action.dest: action.help
        for action in subparsers._choices_actions
    }


def definition(
    *,
    command_id: str = "test-command",
    handler_name: str = "run_test_command",
    execution_mode: CommandExecutionMode = CommandExecutionMode.STANDALONE,
    output_mode: CommandOutputMode = CommandOutputMode.SINGLE,
) -> CommandDefinition:
    return CommandDefinition(
        command_id=command_id,
        help_text="Test one command.",
        handler_name=handler_name,
        category=CommandCategory.OBSERVABILITY,
        execution_mode=execution_mode,
        output_mode=output_mode,
    )


def test_registry_matches_every_parser_command_help_and_handler() -> None:
    parser_help = parser_command_help()

    COMMAND_REGISTRY.validate_parser_commands(parser_help)

    assert len(COMMAND_REGISTRY.definitions) == 24
    assert set(parser_help) == {
        item.command_id for item in COMMAND_REGISTRY.definitions
    }
    assert all(
        callable(getattr(cli, item.handler_name, None))
        for item in COMMAND_REGISTRY.definitions
    )
    assert "if args.command ==" not in getsource(cli.main)


def test_registry_rejects_duplicate_ids_and_parser_drift() -> None:
    item = definition()
    with pytest.raises(ValueError, match="duplicate console command id"):
        CommandRegistry((item, item))

    registry = CommandRegistry((item,))
    with pytest.raises(ValueError, match="registry drift"):
        registry.validate_parser_commands({"unknown": "Unknown."})
    with pytest.raises(ValueError, match="help drift"):
        registry.validate_parser_commands({item.command_id: "Stale help."})


def test_standalone_dispatch_does_not_construct_core() -> None:
    registry = CommandRegistry((definition(),)).bind(
        {"run_test_command": lambda args: [f"value={args.value}"]}
    )

    command, outputs = registry.invoke(
        "test-command",
        args=Namespace(value="safe"),
        console_factory=lambda: pytest.fail("standalone command constructed Core"),
    )

    assert outputs == ["value=safe"]
    assert command.emitted_outputs(args=Namespace(), outputs=outputs) == outputs


def test_core_dispatch_constructs_once_and_chat_output_preserves_mode() -> None:
    calls: list[str] = []
    registry = CommandRegistry(
        (
            definition(
                execution_mode=CommandExecutionMode.CORE,
                output_mode=CommandOutputMode.CHAT,
            ),
        )
    ).bind(
        {
            "run_test_command": lambda console, args: [
                f"{console}:{item}" for item in args.message
            ]
        }
    )

    command, outputs = registry.invoke(
        "test-command",
        args=Namespace(message=["one", "two"]),
        console_factory=lambda: calls.append("built") or "core",
    )

    assert calls == ["built"]
    assert outputs == ["core:one", "core:two"]
    assert command.emitted_outputs(
        args=Namespace(message=["one", "two"]), outputs=outputs
    ) == outputs
    assert command.emitted_outputs(args=Namespace(message=[]), outputs=outputs) == []


def test_main_standalone_readiness_command_skips_console_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_build(*args, **kwargs):
        raise AssertionError("standalone readiness command constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", fail_build)

    exit_code = cli.main(
        [
            "readiness-dashboard",
            "--longitudinal-report",
            str(tmp_path / "missing.json"),
        ]
    )

    assert exit_code == 0
    assert "regression_readiness=read_only" in capsys.readouterr().out
