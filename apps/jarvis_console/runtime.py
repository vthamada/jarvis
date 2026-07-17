"""Output, redaction and exit semantics for the JARVIS operator console."""

from __future__ import annotations

import sys
from argparse import Namespace
from dataclasses import asdict, dataclass
from enum import IntEnum
from json import dumps
from re import IGNORECASE, escape, sub
from re import compile as compile_pattern
from typing import TextIO

from apps.jarvis_console.registry import (
    BoundCommandRegistry,
    ConsoleFactory,
)


class ConsoleExitCode(IntEnum):
    SUCCESS = 0
    RUNTIME_ERROR = 1
    USAGE_ERROR = 2
    GOVERNANCE_BLOCKED = 3


@dataclass(frozen=True)
class ConsoleResultEnvelope:
    schema_version: str
    command_id: str
    status: str
    outputs: list[str]
    warnings: list[str]
    redacted: bool


@dataclass(frozen=True)
class ConsoleErrorEnvelope:
    schema_version: str
    command_id: str
    status: str
    error_code: str
    message: str
    redacted: bool


class ConsoleCommandError(Exception):
    def __init__(
        self,
        message: str,
        *,
        error_code: str,
        exit_code: ConsoleExitCode,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.exit_code = exit_code


class GovernanceBlockedConsoleError(ConsoleCommandError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="governance_blocked",
            exit_code=ConsoleExitCode.GOVERNANCE_BLOCKED,
        )


_SENSITIVE_ASSIGNMENT = compile_pattern(
    r"\b(api[-_]?key|access[-_]?token|token|password|secret)\s*[:=]\s*([^\s,;]+)",
    IGNORECASE,
)
_BEARER_TOKEN = compile_pattern(r"\bBearer\s+[^\s,;]+", IGNORECASE)
_AUTHENTICATED_URL = compile_pattern(r"(://[^\s:/]+:)[^@\s]+(@)")
_WINDOWS_PATH = compile_pattern(r"\b[A-Za-z]:\\[^\r\n\s,;]+")
_SENSITIVE_UNIX_PATH = compile_pattern(
    r"(?<![:\w])/(?:Users|home|tmp|var|etc)/[^\r\n,;]+"
)


class ConsoleRuntime:
    def __init__(
        self,
        *,
        output_format: str,
        stdout_stream: TextIO | None = None,
        stderr_stream: TextIO | None = None,
        sensitive_paths: tuple[str, ...] = (),
    ) -> None:
        self.output_format = output_format
        self.stdout = stdout_stream or sys.stdout
        self.stderr = stderr_stream or sys.stderr
        self.sensitive_paths = tuple(
            sorted(
                {
                    path.rstrip("/\\")
                    for path in sensitive_paths
                    if path and path not in {"/", "\\"}
                },
                key=len,
                reverse=True,
            )
        )

    def execute(
        self,
        *,
        registry: BoundCommandRegistry,
        command_id: str,
        args: Namespace,
        console_factory: ConsoleFactory,
    ) -> int:
        try:
            command = registry.require(command_id)
            if self.output_format not in {"text", "json"}:
                raise ConsoleCommandError(
                    f"unsupported output format: {self.output_format}",
                    error_code="invalid_output_format",
                    exit_code=ConsoleExitCode.USAGE_ERROR,
                )
            if self.output_format == "json" and not command.definition.supports_json:
                raise ConsoleCommandError(
                    f"JSON output is not supported for command: {command_id}",
                    error_code="json_not_supported",
                    exit_code=ConsoleExitCode.USAGE_ERROR,
                )
            command, outputs = registry.invoke(
                command_id,
                args=args,
                console_factory=console_factory,
            )
            emitted = command.emitted_outputs(args=args, outputs=outputs)
            self._emit_success(command_id=command_id, outputs=emitted)
            return int(ConsoleExitCode.SUCCESS)
        except ConsoleCommandError as exc:
            self._emit_error(
                command_id=command_id,
                error_code=exc.error_code,
                message=str(exc),
            )
            return int(exc.exit_code)
        except ValueError as exc:
            self._emit_error(
                command_id=command_id,
                error_code="invalid_command_input",
                message=str(exc),
            )
            return int(ConsoleExitCode.USAGE_ERROR)
        except Exception as exc:
            self._emit_error(
                command_id=command_id,
                error_code="runtime_error",
                message=str(exc) or "command execution failed",
            )
            return int(ConsoleExitCode.RUNTIME_ERROR)

    def report_error(
        self,
        *,
        command_id: str,
        error: ConsoleCommandError,
    ) -> int:
        self._emit_error(
            command_id=command_id,
            error_code=error.error_code,
            message=str(error),
        )
        return int(error.exit_code)

    def redact(self, value: str) -> tuple[str, bool]:
        redacted = value
        for path in self.sensitive_paths:
            for path_variant in {path, path.replace("\\", "/")}:
                redacted = sub(
                    escape(path_variant) + r"(?:(?:\\|/)[^\r\n\s,;]+)*",
                    "<redacted-path>",
                    redacted,
                    flags=IGNORECASE,
                )
        redacted = _SENSITIVE_ASSIGNMENT.sub(
            lambda match: f"{match.group(1)}=<redacted>",
            redacted,
        )
        redacted = _BEARER_TOKEN.sub("Bearer <redacted>", redacted)
        redacted = _AUTHENTICATED_URL.sub(r"\1<redacted>\2", redacted)
        redacted = _WINDOWS_PATH.sub("<redacted-path>", redacted)
        redacted = _SENSITIVE_UNIX_PATH.sub("<redacted-path>", redacted)
        return redacted, redacted != value

    def _emit_success(self, *, command_id: str, outputs: list[str]) -> None:
        redacted_outputs: list[str] = []
        redaction_applied = False
        for output in outputs:
            safe_output, changed = self.redact(output)
            redacted_outputs.append(safe_output)
            redaction_applied = redaction_applied or changed
        if self.output_format == "json":
            envelope = ConsoleResultEnvelope(
                schema_version="jarvis-console/v1",
                command_id=command_id,
                status="success",
                outputs=redacted_outputs,
                warnings=[],
                redacted=redaction_applied,
            )
            self.stdout.write(dumps(asdict(envelope), ensure_ascii=False, sort_keys=True))
            self.stdout.write("\n")
            return
        for output in redacted_outputs:
            self.stdout.write(output)
            self.stdout.write("\n")

    def _emit_error(
        self,
        *,
        command_id: str,
        error_code: str,
        message: str,
    ) -> None:
        safe_message, redaction_applied = self.redact(message)
        if self.output_format == "json":
            envelope = ConsoleErrorEnvelope(
                schema_version="jarvis-console/v1",
                command_id=command_id,
                status="error",
                error_code=error_code,
                message=safe_message,
                redacted=redaction_applied,
            )
            self.stderr.write(dumps(asdict(envelope), ensure_ascii=False, sort_keys=True))
            self.stderr.write("\n")
            return
        self.stderr.write(f"error[{error_code}]: {safe_message}\n")
