from argparse import Namespace
from io import StringIO
from json import loads
from pathlib import Path

import pytest

from apps.jarvis_console import cli
from apps.jarvis_console.registry import (
    CommandCategory,
    CommandDefinition,
    CommandExecutionMode,
    CommandRegistry,
)
from apps.jarvis_console.runtime import (
    ConsoleExitCode,
    ConsoleRuntime,
    GovernanceBlockedConsoleError,
)


def bound_registry(
    handler,
    *,
    supports_json: bool = True,
):
    definition = CommandDefinition(
        command_id="test-command",
        help_text="Test command output.",
        handler_name="run_test_command",
        category=CommandCategory.OBSERVABILITY,
        execution_mode=CommandExecutionMode.STANDALONE,
        supports_json=supports_json,
    )
    return CommandRegistry((definition,)).bind({"run_test_command": handler})


def test_parser_accepts_global_format_before_and_after_subcommand() -> None:
    parser = cli.build_parser()

    before = parser.parse_args(["--format", "json", "readiness-dashboard"])
    after = parser.parse_args(["readiness-dashboard", "--format", "json"])

    assert before.output_format == "json"
    assert after.output_format == "json"
    assert parser.parse_args(["readiness-dashboard"]).output_format == "text"


def test_json_runtime_emits_versioned_redacted_success_envelope() -> None:
    stdout = StringIO()
    stderr = StringIO()
    runtime = ConsoleRuntime(
        output_format="json",
        stdout_stream=stdout,
        stderr_stream=stderr,
        sensitive_paths=(r"C:\Users\operator\jarvis",),
    )
    registry = bound_registry(
        lambda args: [
            r"database=C:\Users\operator\jarvis\runtime.db api_key=top-secret"
        ]
    )

    exit_code = runtime.execute(
        registry=registry,
        command_id="test-command",
        args=Namespace(),
        console_factory=lambda: pytest.fail("standalone command constructed Core"),
    )

    payload = loads(stdout.getvalue())
    assert exit_code == ConsoleExitCode.SUCCESS
    assert stderr.getvalue() == ""
    assert payload == {
        "command_id": "test-command",
        "outputs": ["database=<redacted-path> api_key=<redacted>"],
        "redacted": True,
        "schema_version": "jarvis-console/v1",
        "status": "success",
        "warnings": [],
    }


def test_json_not_supported_fails_before_handler_or_core() -> None:
    stdout = StringIO()
    stderr = StringIO()
    calls: list[str] = []
    runtime = ConsoleRuntime(
        output_format="json",
        stdout_stream=stdout,
        stderr_stream=stderr,
    )
    registry = bound_registry(
        lambda args: calls.append("handler") or ["unexpected"],
        supports_json=False,
    )

    exit_code = runtime.execute(
        registry=registry,
        command_id="test-command",
        args=Namespace(),
        console_factory=lambda: calls.append("core"),
    )

    payload = loads(stderr.getvalue())
    assert exit_code == ConsoleExitCode.USAGE_ERROR
    assert stdout.getvalue() == ""
    assert calls == []
    assert payload["error_code"] == "json_not_supported"
    assert payload["status"] == "error"


def test_runtime_error_uses_stderr_stable_code_and_redaction() -> None:
    stdout = StringIO()
    stderr = StringIO()
    runtime = ConsoleRuntime(
        output_format="text",
        stdout_stream=stdout,
        stderr_stream=stderr,
    )

    def raise_runtime_error(args):
        raise RuntimeError(r"token=private-value at C:\Users\operator\runtime.db")

    exit_code = runtime.execute(
        registry=bound_registry(raise_runtime_error),
        command_id="test-command",
        args=Namespace(),
        console_factory=lambda: None,
    )

    assert exit_code == ConsoleExitCode.RUNTIME_ERROR
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "error[runtime_error]: token=<redacted> at <redacted-path>\n"
    )


def test_governance_blocked_error_has_distinct_exit_code() -> None:
    stderr = StringIO()
    runtime = ConsoleRuntime(
        output_format="text",
        stdout_stream=StringIO(),
        stderr_stream=stderr,
    )

    def raise_governance_block(args):
        raise GovernanceBlockedConsoleError("human approval required")

    exit_code = runtime.execute(
        registry=bound_registry(raise_governance_block),
        command_id="test-command",
        args=Namespace(),
        console_factory=lambda: None,
    )

    assert exit_code == ConsoleExitCode.GOVERNANCE_BLOCKED
    assert stderr.getvalue() == (
        "error[governance_blocked]: human approval required\n"
    )


def test_main_json_readiness_is_machine_readable_and_skips_core(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_build(*args, **kwargs):
        raise AssertionError("read-only JSON command constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", fail_build)

    exit_code = cli.main(
        [
            "readiness-dashboard",
            "--format",
            "json",
            "--longitudinal-report",
            str(tmp_path / "missing.json"),
        ]
    )

    captured = capsys.readouterr()
    payload = loads(captured.out)
    assert exit_code == ConsoleExitCode.SUCCESS
    assert captured.err == ""
    assert payload["command_id"] == "readiness-dashboard"
    assert payload["status"] == "success"
    assert "regression_readiness=read_only" in payload["outputs"][0]


def test_main_rejects_json_for_state_change_before_core_build(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_build(*args, **kwargs):
        raise AssertionError("unsupported JSON command constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", fail_build)

    exit_code = cli.main(
        [
            "objective",
            "--mission-id",
            "mission-json-blocked",
            "--action",
            "pause",
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = loads(captured.err)
    assert exit_code == ConsoleExitCode.USAGE_ERROR
    assert captured.out == ""
    assert payload["error_code"] == "json_not_supported"


def test_main_parser_error_uses_json_stderr_contract(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_build(*args, **kwargs):
        raise AssertionError("invalid CLI usage constructed Core")

    monkeypatch.setattr(cli.JarvisConsole, "build", fail_build)

    exit_code = cli.main(["objective", "--format=json"])

    captured = capsys.readouterr()
    payload = loads(captured.err)
    assert exit_code == ConsoleExitCode.USAGE_ERROR
    assert captured.out == ""
    assert payload["command_id"] == "objective"
    assert payload["status"] == "error"
    assert payload["error_code"] == "invalid_cli_usage"
    assert "required" in payload["message"]
