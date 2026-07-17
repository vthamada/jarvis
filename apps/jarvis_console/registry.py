"""Typed command metadata and dispatch for the JARVIS operator console."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from re import fullmatch

ConsoleFactory = Callable[[], object]


class CommandExecutionMode(StrEnum):
    CORE = "core"
    STANDALONE = "standalone"


class CommandOutputMode(StrEnum):
    SINGLE = "single"
    CHAT = "chat"


class CommandCategory(StrEnum):
    MISSION = "mission"
    OBJECTIVE = "objective"
    WORK = "work"
    ARTIFACT = "artifact"
    MEMORY = "memory"
    EVOLUTION = "evolution"
    OBSERVABILITY = "observability"


JSON_OUTPUT_COMMAND_IDS = frozenset(
    {
        "objectives",
        "goal-strategy",
        "work-items",
        "artifacts",
        "technology-candidates",
        "experience-reflections",
        "procedural-playbooks",
        "skill-evolution",
        "evolution-review-queue",
        "memory-review-queue",
        "mission-cycle",
        "operator-dashboard",
        "daily-workspace",
        "readiness-dashboard",
        "doctor",
        "learning-report",
        "progress-report",
    }
)


@dataclass(frozen=True)
class CommandDefinition:
    command_id: str
    help_text: str
    handler_name: str
    category: CommandCategory
    execution_mode: CommandExecutionMode
    output_mode: CommandOutputMode = CommandOutputMode.SINGLE
    supports_json: bool = False


@dataclass(frozen=True)
class CommandExecutionResult:
    outputs: list[str]
    status: str = "success"
    exit_code: int = 0
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in {"success", "degraded", "failed"}:
            raise ValueError(f"invalid command result status: {self.status}")
        if self.exit_code not in {0, 1, 2, 3}:
            raise ValueError(f"invalid command result exit code: {self.exit_code}")
        if self.status in {"success", "degraded"} and self.exit_code != 0:
            raise ValueError("non-failed command result requires exit code 0")
        if self.status == "failed" and self.exit_code == 0:
            raise ValueError("failed command result requires nonzero exit code")


CommandHandler = Callable[..., list[str] | CommandExecutionResult]


@dataclass(frozen=True)
class BoundCommand:
    definition: CommandDefinition
    handler: CommandHandler

    def invoke(
        self,
        *,
        args: Namespace,
        console_factory: ConsoleFactory,
    ) -> CommandExecutionResult:
        if self.definition.execution_mode == CommandExecutionMode.CORE:
            result = self.handler(console_factory(), args)
        else:
            result = self.handler(args)
        if isinstance(result, CommandExecutionResult):
            return result
        return CommandExecutionResult(outputs=list(result))

    def emitted_outputs(self, *, args: Namespace, outputs: list[str]) -> list[str]:
        if self.definition.output_mode == CommandOutputMode.CHAT:
            return outputs if bool(getattr(args, "message", [])) else []
        return outputs[:1]


class BoundCommandRegistry:
    def __init__(self, commands: list[BoundCommand]) -> None:
        self._commands = {
            command.definition.command_id: command for command in commands
        }

    def require(self, command_id: str) -> BoundCommand:
        try:
            return self._commands[command_id]
        except KeyError as exc:
            raise ValueError(f"unknown console command: {command_id}") from exc

    def invoke(
        self,
        command_id: str,
        *,
        args: Namespace,
        console_factory: ConsoleFactory,
    ) -> tuple[BoundCommand, CommandExecutionResult]:
        command = self.require(command_id)
        return command, command.invoke(args=args, console_factory=console_factory)


class CommandRegistry:
    def __init__(self, definitions: tuple[CommandDefinition, ...]) -> None:
        command_ids = [definition.command_id for definition in definitions]
        if len(command_ids) != len(set(command_ids)):
            raise ValueError("duplicate console command id")
        for definition in definitions:
            if fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", definition.command_id) is None:
                raise ValueError(f"invalid console command id: {definition.command_id}")
            if not definition.help_text.strip():
                raise ValueError(f"missing help text: {definition.command_id}")
            if not definition.handler_name.startswith("run_") or not (
                definition.handler_name.endswith("_command")
            ):
                raise ValueError(f"invalid handler name: {definition.handler_name}")
            if (
                definition.supports_json
                and definition.output_mode != CommandOutputMode.SINGLE
            ):
                raise ValueError(
                    f"JSON requires single output mode: {definition.command_id}"
                )
        self._definitions = definitions
        self._by_id = {
            definition.command_id: definition for definition in definitions
        }

    @property
    def definitions(self) -> tuple[CommandDefinition, ...]:
        return self._definitions

    def require(self, command_id: str) -> CommandDefinition:
        try:
            return self._by_id[command_id]
        except KeyError as exc:
            raise ValueError(f"unknown console command: {command_id}") from exc

    def validate_parser_commands(self, parser_help: Mapping[str, str]) -> None:
        declared_ids = set(self._by_id)
        parser_ids = set(parser_help)
        if declared_ids != parser_ids:
            missing = sorted(declared_ids - parser_ids)
            unknown = sorted(parser_ids - declared_ids)
            raise ValueError(
                f"console command registry drift: missing={missing}, unknown={unknown}"
            )
        mismatched_help = sorted(
            command_id
            for command_id, help_text in parser_help.items()
            if help_text != self._by_id[command_id].help_text
        )
        if mismatched_help:
            raise ValueError(
                f"console command help drift: {','.join(mismatched_help)}"
            )

    def bind(self, handlers: Mapping[str, object]) -> BoundCommandRegistry:
        commands: list[BoundCommand] = []
        for definition in self._definitions:
            handler = handlers.get(definition.handler_name)
            if not callable(handler):
                raise ValueError(
                    f"console command handler unavailable: {definition.handler_name}"
                )
            commands.append(BoundCommand(definition=definition, handler=handler))
        return BoundCommandRegistry(commands)


def _command(
    command_id: str,
    help_text: str,
    handler_name: str,
    category: CommandCategory,
    execution_mode: CommandExecutionMode,
    output_mode: CommandOutputMode = CommandOutputMode.SINGLE,
) -> CommandDefinition:
    return CommandDefinition(
        command_id=command_id,
        help_text=help_text,
        handler_name=handler_name,
        category=category,
        execution_mode=execution_mode,
        output_mode=output_mode,
        supports_json=command_id in JSON_OUTPUT_COMMAND_IDS,
    )


CORE = CommandExecutionMode.CORE
STANDALONE = CommandExecutionMode.STANDALONE

COMMAND_REGISTRY = CommandRegistry(
    (
        _command(
            "ask",
            "Execute a single prompt.",
            "run_ask_command",
            CommandCategory.MISSION,
            CORE,
        ),
        _command(
            "chat",
            "Run a simple multi-turn chat session.",
            "run_chat_command",
            CommandCategory.MISSION,
            CORE,
            CommandOutputMode.CHAT,
        ),
        _command(
            "objectives",
            "Show the persisted objective state for a mission.",
            "run_objectives_command",
            CommandCategory.OBJECTIVE,
            CORE,
        ),
        _command(
            "goal-strategy",
            "Show read-only long-horizon strategy for a mission.",
            "run_goal_strategy_command",
            CommandCategory.OBJECTIVE,
            CORE,
        ),
        _command(
            "objective",
            "Apply a bounded operator transition to a mission objective.",
            "run_objective_command",
            CommandCategory.OBJECTIVE,
            CORE,
        ),
        _command(
            "work-items",
            "Show governed work items for a mission.",
            "run_work_items_command",
            CommandCategory.WORK,
            CORE,
        ),
        _command(
            "work-item",
            "Apply a bounded operator transition to a mission work item.",
            "run_work_item_command",
            CommandCategory.WORK,
            CORE,
        ),
        _command(
            "artifacts",
            "Show governed living artifacts for a mission.",
            "run_artifacts_command",
            CommandCategory.ARTIFACT,
            CORE,
        ),
        _command(
            "artifact",
            "Apply a bounded lifecycle transition to a mission artifact.",
            "run_artifact_command",
            CommandCategory.ARTIFACT,
            CORE,
        ),
        _command(
            "technology-candidates",
            "Show recent governed technology absorption candidates.",
            "run_technology_candidates_command",
            CommandCategory.EVOLUTION,
            STANDALONE,
        ),
        _command(
            "experience-reflections",
            "Show recent bounded post-task experience reflections.",
            "run_experience_reflections_command",
            CommandCategory.MEMORY,
            STANDALONE,
        ),
        _command(
            "procedural-playbooks",
            "Show bounded procedural playbook candidates without activating them.",
            "run_procedural_playbooks_command",
            CommandCategory.MEMORY,
            STANDALONE,
        ),
        _command(
            "skill-evolution",
            "Show the read-only skill evidence, review and sandbox chain.",
            "run_skill_evolution_command",
            CommandCategory.EVOLUTION,
            STANDALONE,
        ),
        _command(
            "evolution-review-queue",
            "Show human-review evolution proposals without promoting them.",
            "run_evolution_review_queue_command",
            CommandCategory.EVOLUTION,
            STANDALONE,
        ),
        _command(
            "evolution-review",
            "Apply a human review decision to an evolution proposal.",
            "run_evolution_review_command",
            CommandCategory.EVOLUTION,
            STANDALONE,
        ),
        _command(
            "memory-review-queue",
            "Show human-only consolidation, archive and expiration candidates.",
            "run_memory_lifecycle_review_queue_command",
            CommandCategory.MEMORY,
            STANDALONE,
        ),
        _command(
            "memory-review",
            "Record a governed human decision without executing memory maintenance.",
            "run_memory_lifecycle_review_command",
            CommandCategory.MEMORY,
            STANDALONE,
        ),
        _command(
            "mission-cycle",
            "Show a read-only operator learning loop for one mission.",
            "run_mission_cycle_command",
            CommandCategory.MISSION,
            CORE,
        ),
        _command(
            "operator-dashboard",
            "Show a read-only daily operator dashboard.",
            "run_operator_dashboard_command",
            CommandCategory.MISSION,
            CORE,
        ),
        _command(
            "daily-workspace",
            "Show a read-only cross-session operator workspace.",
            "run_daily_workspace_command",
            CommandCategory.MISSION,
            STANDALONE,
        ),
        _command(
            "readiness-dashboard",
            "Show repository regression and readiness signals.",
            "run_readiness_dashboard_command",
            CommandCategory.OBSERVABILITY,
            STANDALONE,
        ),
        _command(
            "doctor",
            "Run read-only local runtime and governance diagnostics.",
            "run_doctor_command",
            CommandCategory.OBSERVABILITY,
            STANDALONE,
        ),
        _command(
            "learning-report",
            "Show read-only longitudinal outcomes by reviewed version.",
            "run_longitudinal_learning_report_command",
            CommandCategory.OBSERVABILITY,
            STANDALONE,
        ),
        _command(
            "progress-report",
            "Show a synthesized read-only mission progress report.",
            "run_progress_report_command",
            CommandCategory.MISSION,
            CORE,
        ),
        _command(
            "mission-workflow",
            "Run a governed mission and show the operator learning loop.",
            "run_mission_workflow_command",
            CommandCategory.MISSION,
            CORE,
        ),
        _command(
            "mission-feedback",
            "Record explicit bounded operator feedback after a mission.",
            "run_mission_feedback_command",
            CommandCategory.MISSION,
            CORE,
        ),
    )
)
