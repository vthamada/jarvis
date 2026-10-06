"""Command adapter for the opt-in physical console, with sanitized failures."""

import json
import os
import stat
import sys
from argparse import Namespace
from pathlib import Path

from apps.jarvis_console.physical_bootstrap import _reject_redirects, build_physical_orchestrator
from apps.jarvis_console.registry import CommandExecutionResult
from apps.jarvis_console.runtime import ConsoleCommandError, ConsoleExitCode


def _required(args: Namespace, *names: str) -> None:
    if any(getattr(args, name, None) is None for name in names):
        raise ConsoleCommandError(
            "Required physical action fields are missing.",
            error_code="invalid_physical_fields", exit_code=ConsoleExitCode.USAGE_ERROR,
        )


def _read_desired_text(source: Path) -> str:
    """Bound the opted-in read and validate the opened object, not just its path.

    Linux nonblocking/no-follow flags prevent a raced FIFO from hanging the CLI.
    Windows remains prepare-only; ancestor checks are not a same-user sandbox.
    """
    source = Path(source).absolute()
    _reject_redirects(source)
    flags = (
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    fd = os.open(source, flags)
    try:
        observed = os.fstat(fd)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_nlink != 1
            or observed.st_size > 262_144
        ):
            raise ValueError("invalid_desired_file")
        _reject_redirects(source)
        with os.fdopen(fd, "rb", closefd=False) as handle:
            data = handle.read(262_145)
        if len(data) > 262_144:
            raise ValueError("desired_text_limit")
        return data.decode("utf-8")
    finally:
        os.close(fd)


def run_physical(args: Namespace) -> list[str] | CommandExecutionResult:
    # Imported after console bootstrap and only when the operator selects this command.
    from apps.jarvis_console.physical_operations import PhysicalOperationsConsole

    if args.action == "prepare":
        _required(
            args, "mission_id", "work_item_ref", "artifact_ref", "resource_ref", "desired_file",
        )
    else:
        _required(args, "request_id")
    if args.action in {"confirm", "confirm-rollback", "execute", "recover", "rollback"}:
        _required(args, "challenge_id", "action_fingerprint")
    if args.action in {"execute", "recover", "rollback"}:
        _required(args, "confirmation_receipt_id")
        if not args.enable_execution:
            raise ConsoleCommandError(
                "Physical execution requires explicit Linux opt-in.",
                error_code="physical_execution_not_enabled",
                exit_code=ConsoleExitCode.GOVERNANCE_BLOCKED,
            )
    console = None
    try:
        roots = {}
        for entry in args.root:
            alias, separator, directory = entry.partition("=")
            if not separator or alias in roots:
                raise ValueError("invalid_root")
            roots[alias] = Path(directory)
        # Windows supports a prepare-only preview; no restart claim is made.
        if sys.platform != "linux" and args.action != "prepare":
            raise ValueError("durable_physical_console_unavailable")
        desired_text = None
        if args.action == "prepare":
            desired_text = _read_desired_text(args.desired_file)
        core = build_physical_orchestrator(
            runtime_dir=args.runtime_dir, roots=roots, enable_execution=args.enable_execution,
        )
        console = PhysicalOperationsConsole(
            core, args.operator_identity_ref, args.canonical_user_ref,
            runtime_dir=(
                args.runtime_dir / "physical-requests" if sys.platform == "linux" else None
            ),
        )
        exact = {"challenge_id": args.challenge_id, "action_fingerprint": args.action_fingerprint}
        authorized = {**exact, "confirmation_receipt_id": args.confirmation_receipt_id}
        if args.action == "prepare":
            result = console.prepare(
                mission_id=args.mission_id, work_item_ref=args.work_item_ref,
                artifact_ref=args.artifact_ref, resource_ref=args.resource_ref,
                desired_text=desired_text, session_id=args.session_id,
                operation=args.operation, expected_current_sha256=args.expected_current_sha256,
                supersedes_artifact_ref=args.supersedes_artifact_ref,
            )
        elif args.action == "prepare-rollback":
            result = console.prepare_rollback(args.request_id, session_id=args.session_id)
        elif args.action in {"confirm", "confirm-rollback"}:
            method = console.confirm if args.action == "confirm" else console.confirm_rollback
            result = method(args.request_id, **exact)
        elif args.action in {"execute", "recover", "rollback"}:
            result = getattr(console, args.action)(args.request_id, **authorized)
        else:
            result = getattr(console, args.action)(args.request_id)
        if not args.show_diff:
            result.pop("preview", None)
        outputs = [json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)]
        if args.action in {"execute", "recover", "rollback"} and result.get("phase") != "completed":
            return CommandExecutionResult(
                outputs=outputs, status="failed", exit_code=ConsoleExitCode.GOVERNANCE_BLOCKED,
                warnings=["Physical saga requires inspection; operation is not completed."],
            )
        return outputs
    except Exception:
        raise ConsoleCommandError(
            "Physical operation unavailable or refused; no authority was broadened.",
            error_code="physical_operation_refused", exit_code=ConsoleExitCode.GOVERNANCE_BLOCKED,
        ) from None
    finally:
        if console is not None:
            console.close()
