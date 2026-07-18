"""Deterministic command reference and shell completion generation."""

from __future__ import annotations

from argparse import SUPPRESS, Action, ArgumentParser
from dataclasses import dataclass
from re import fullmatch

from apps.jarvis_console.registry import CommandDefinition, CommandRegistry

SAFE_COMPLETION_TOKEN = r"[A-Za-z0-9_./:+-]+"


@dataclass(frozen=True)
class CommandArgumentReference:
    name: str
    option_strings: tuple[str, ...]
    required: bool
    takes_value: bool
    choices: tuple[str, ...]
    repeatable: bool
    help_text: str | None

    @property
    def positional(self) -> bool:
        return not self.option_strings

    @property
    def completion_options(self) -> tuple[str, ...]:
        return self.option_strings


@dataclass(frozen=True)
class CommandReference:
    definition: CommandDefinition
    arguments: tuple[CommandArgumentReference, ...]


def build_reference_model(
    registry: CommandRegistry,
    parser: ArgumentParser,
) -> tuple[CommandReference, ...]:
    """Build the validated model used by docs and completion generators."""

    subparser_action, subparsers = _command_parsers(parser)
    registry.validate_parser_commands(
        {
            action.dest: str(action.help)
            for action in subparser_action._choices_actions
        }
    )
    model: list[CommandReference] = []
    for definition in registry.definitions:
        command_parser = subparsers[definition.command_id]
        arguments = tuple(
            _argument_reference(action)
            for action in command_parser._actions
            if action.dest != "help" and action.help != SUPPRESS
        )
        model.append(CommandReference(definition=definition, arguments=arguments))
    return tuple(model)


def render_command_reference(
    registry: CommandRegistry,
    parser: ArgumentParser,
) -> str:
    """Render stable Markdown without machine-specific defaults or timestamps."""

    model = build_reference_model(registry, parser)
    lines = [
        "# JARVIS Console Command Reference",
        "",
        "Status: generated active baseline from `MB-199`.",
        "",
        "This file is generated from the typed command registry and its validated",
        "`argparse` declarations. Do not edit it manually.",
        "",
        "## Command Inventory",
        "",
        "| Command | Category | Execution | Output | JSON | Description |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for command in model:
        definition = command.definition
        lines.append(
            "| "
            f"`{definition.command_id}` | `{definition.category.value}` | "
            f"`{definition.execution_mode.value}` | `{definition.output_mode.value}` | "
            f"`{'yes' if definition.supports_json else 'no'}` | "
            f"{_markdown(definition.help_text)} |"
        )
    lines.extend(["", "## Commands"])
    for command in model:
        definition = command.definition
        lines.extend(
            [
                "",
                f"### `{definition.command_id}`",
                "",
                definition.help_text,
                "",
                f"Usage: `{_usage(command)}`",
                "",
                "| Argument | Required | Values | Repeatable | Description |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for argument in command.arguments:
            name = (
                ", ".join(f"`{item}`" for item in argument.option_strings)
                if argument.option_strings
                else f"`<{argument.name}>`"
            )
            values = (
                ", ".join(f"`{item}`" for item in argument.choices)
                if argument.choices
                else "value"
                if argument.takes_value
                else "flag"
            )
            lines.append(
                f"| {name} | {'yes' if argument.required else 'no'} | {values} | "
                f"{'yes' if argument.repeatable else 'no'} | "
                f"{_markdown(argument.help_text or '-')} |"
            )
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- completion and reference generation are read-only;",
            "- command execution mode does not grant or bypass authority;",
            "- state-changing commands still cross their existing governance path;",
            "- generated assets contain no runtime paths, secrets, ids or timestamps.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_shell_completion(
    registry: CommandRegistry,
    parser: ArgumentParser,
    *,
    shell: str,
) -> str:
    """Render completion for supported shells without evaluating operator input."""

    model = build_reference_model(registry, parser)
    _validate_completion_tokens(model)
    if shell == "powershell":
        return _powershell_completion(model)
    if shell == "bash":
        return _bash_completion(model)
    if shell == "zsh":
        return _zsh_completion(model)
    raise ValueError(f"unsupported completion shell: {shell}")


def _command_parsers(
    parser: ArgumentParser,
) -> tuple[Action, dict[str, ArgumentParser]]:
    action = next(
        (
            candidate
            for candidate in parser._actions
            if candidate.dest == "command" and hasattr(candidate, "choices")
        ),
        None,
    )
    choices = getattr(action, "choices", None)
    if not isinstance(choices, dict):
        raise ValueError("console parser is missing command subparsers")
    return action, choices


def _argument_reference(action: Action) -> CommandArgumentReference:
    positional = not action.option_strings
    required = bool(action.required) or (
        positional and action.nargs not in {"?", "*"}
    )
    takes_value = action.nargs != 0
    choices = tuple(str(item) for item in (action.choices or ()))
    return CommandArgumentReference(
        name=str(action.dest),
        option_strings=tuple(action.option_strings),
        required=required,
        takes_value=takes_value,
        choices=choices,
        repeatable=action.__class__.__name__ == "_AppendAction",
        help_text=str(action.help) if action.help else None,
    )


def _usage(command: CommandReference) -> str:
    tokens = ["jarvis-console", command.definition.command_id]
    for argument in command.arguments:
        if argument.positional:
            token = f"<{argument.name}>"
        else:
            token = argument.option_strings[-1]
            if argument.takes_value:
                token += " <value>"
        if argument.repeatable:
            token += " ..."
        tokens.append(token if argument.required else f"[{token}]")
    return " ".join(tokens)


def _markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _validate_completion_tokens(model: tuple[CommandReference, ...]) -> None:
    tokens = [
        token
        for command in model
        for token in (
            command.definition.command_id,
            *(option for argument in command.arguments for option in argument.option_strings),
            *(choice for argument in command.arguments for choice in argument.choices),
        )
    ]
    unsafe = sorted(
        {token for token in tokens if fullmatch(SAFE_COMPLETION_TOKEN, token) is None}
    )
    if unsafe:
        raise ValueError(f"unsafe shell completion tokens: {','.join(unsafe)}")


def _command_options(command: CommandReference) -> tuple[str, ...]:
    values = ["-h", "--help"]
    values.extend(
        option
        for argument in command.arguments
        for option in argument.completion_options
    )
    return tuple(dict.fromkeys(values))


def _choice_entries(
    model: tuple[CommandReference, ...],
) -> list[tuple[str, str, tuple[str, ...]]]:
    return [
        (command.definition.command_id, option, argument.choices)
        for command in model
        for argument in command.arguments
        if argument.choices
        for option in argument.option_strings
    ]


def _powershell_completion(model: tuple[CommandReference, ...]) -> str:
    commands = ", ".join(_ps_quote(item.definition.command_id) for item in model)
    lines = [
        "# Generated by JARVIS MB-199. Do not edit.",
        f"$JarvisConsoleCommands = @({commands})",
        "$JarvisConsoleOptions = @{",
    ]
    for command in model:
        options = ", ".join(_ps_quote(item) for item in _command_options(command))
        lines.append(f"    {_ps_quote(command.definition.command_id)} = @({options})")
    lines.extend(["}", "$JarvisConsoleChoices = @{"])
    for command_id, option, choices in _choice_entries(model):
        values = ", ".join(_ps_quote(item) for item in choices)
        lines.append(f"    {_ps_quote(f'{command_id}|{option}')} = @({values})")
    lines.extend(
        [
            "}",
            "Register-ArgumentCompleter -Native -CommandName jarvis-console -ScriptBlock {",
            "    param($wordToComplete, $commandAst, $cursorPosition)",
            "    $tokens = @($commandAst.CommandElements | ForEach-Object { $_.Extent.Text })",
            "    $command = $tokens | Where-Object { "
            "$_ -in $JarvisConsoleCommands } | Select-Object -First 1",
            "    $previous = if ($tokens.Count -gt 1) { $tokens[-2] } else { '' }",
            "    $choiceKey = \"$command|$previous\"",
            "    if (-not $command -and $previous -eq '--format') {",
            "        $candidates = @('text', 'json')",
            "    } elseif ($JarvisConsoleChoices.ContainsKey($choiceKey)) {",
            "        $candidates = $JarvisConsoleChoices[$choiceKey]",
            "    } elseif ($command) {",
            "        $candidates = $JarvisConsoleOptions[$command]",
            "    } else {",
            "        $candidates = @('--format') + $JarvisConsoleCommands",
            "    }",
            "    $candidates | Where-Object { $_ -like \"$wordToComplete*\" } | ForEach-Object {",
            "        [System.Management.Automation.CompletionResult]::new("
            "$_, $_, 'ParameterValue', $_)",
            "    }",
            "}",
        ]
    )
    return "\n".join(lines) + "\n"


def _bash_completion(model: tuple[CommandReference, ...]) -> str:
    command_ids = " ".join(item.definition.command_id for item in model)
    lines = [
        "# Generated by JARVIS MB-199. Do not edit.",
        "_jarvis_console() {",
        "    local cur prev command candidates",
        "    cur=\"${COMP_WORDS[COMP_CWORD]}\"",
        "    prev=\"${COMP_WORDS[COMP_CWORD-1]}\"",
        "    command=''",
        "    for token in \"${COMP_WORDS[@]:1}\"; do",
        f"        if [[ \" {command_ids} \" == *\" $token \"* ]]; then",
        "            command=\"$token\"",
        "            break",
        "        fi",
        "    done",
        "    if [[ $prev == '--format' ]]; then",
        "        COMPREPLY=( $(compgen -W \"text json\" -- \"$cur\") )",
        "        return",
        "    fi",
        "    if [[ -z $command ]]; then",
        f"        COMPREPLY=( $(compgen -W \"--format {command_ids}\" -- \"$cur\") )",
        "        return",
        "    fi",
        "    case \"$command:$prev\" in",
    ]
    for command_id, option, choices in _choice_entries(model):
        lines.append(
            f"        {command_id}:{option}) candidates=\"{' '.join(choices)}\" ;;"
        )
    lines.extend(
        [
            "        *) candidates='' ;;",
            "    esac",
            "    if [[ -z $candidates ]]; then",
            "        case \"$command\" in",
        ]
    )
    for command in model:
        options = " ".join(_command_options(command))
        lines.append(
            f"            {command.definition.command_id}) candidates=\"{options}\" ;;"
        )
    lines.extend(
        [
            "        esac",
            "    fi",
            "    COMPREPLY=( $(compgen -W \"$candidates\" -- \"$cur\") )",
            "}",
            "complete -F _jarvis_console jarvis-console",
        ]
    )
    return "\n".join(lines) + "\n"


def _zsh_completion(model: tuple[CommandReference, ...]) -> str:
    command_pattern = "|".join(item.definition.command_id for item in model)
    lines = [
        "#compdef jarvis-console",
        "# Generated by JARVIS MB-199. Do not edit.",
        "_jarvis_console() {",
        "    local command previous",
        "    command=''",
        "    previous=$words[CURRENT-1]",
        "    local token",
        "    for token in $words; do",
        f"        case $token in ({command_pattern}) command=$token; break ;; esac",
        "    done",
        "    if [[ $previous == '--format' ]]; then",
        "        _values 'format' text json",
        "        return",
        "    fi",
        "    if [[ -z $command ]]; then",
        "        _values 'command' --format "
        + " ".join(_zsh_quote(item.definition.command_id) for item in model),
        "        return",
        "    fi",
        "    case \"$command:$previous\" in",
    ]
    for command_id, option, choices in _choice_entries(model):
        lines.extend(
            [
                f"        {command_id}:{option})",
                "            _values 'value' "
                + " ".join(_zsh_quote(item) for item in choices),
                "            return ;;",
            ]
        )
    lines.extend(["    esac", "    case \"$command\" in"])
    for command in model:
        lines.extend(
            [
                f"        {command.definition.command_id})",
                "            _values 'option' "
                + " ".join(_zsh_quote(item) for item in _command_options(command)),
                "            ;;",
            ]
        )
    lines.extend(["    esac", "}", "_jarvis_console \"$@\""])
    return "\n".join(lines) + "\n"


def _ps_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _zsh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
