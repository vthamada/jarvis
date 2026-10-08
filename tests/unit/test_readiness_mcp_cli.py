"""Standalone readonly MCP CLI authorization, redaction and lifecycle contracts."""

import json

import pytest

from apps.jarvis_console import readiness_mcp_cli as cli
from tools.product_readiness_report import build_report, load_inventory

REFS = ["--principal-ref", "operator://synthetic", "--session-ref", "session://synthetic"]


def test_no_authorization_before_collect(monkeypatch, capsys):
    async def forbidden(*_args):
        pytest.fail("unauthorized collection")

    monkeypatch.setattr(cli, "_collect", forbidden)
    assert cli.main(REFS) == 2
    output = capsys.readouterr()
    assert output.err == "readiness_mcp_authorization_required\n" and not output.out


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--server", "private-secret"],
        ["--front-id", "private-secret"],
        ["--format", "private-secret"],
        ["--timeout-seconds", "private-secret"],
        ["--inventory", "private-secret"],
        ["--scope", "private-secret"],
    ],
)
def test_bad_arguments_not_reflected(extra, monkeypatch, capsys):
    async def forbidden(*_args):
        pytest.fail("invalid options collection")

    monkeypatch.setattr(cli, "_collect", forbidden)
    arguments = extra if not extra else ["--authorized", *REFS, *extra]
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.err == "invalid_readiness_mcp_options\n" and not output.out


@pytest.mark.parametrize(
    "front_id", ["all", *(f"F{i:02d}" for i in range(1, 14)), *(f"T{i:02d}" for i in range(1, 4))]
)
def test_exact_selection_and_json_output(front_id, monkeypatch, capsys):
    calls = []
    report = build_report(load_inventory())

    async def fake(binding, selection, timeout):
        calls.append(
            (binding.principal_ref, binding.session_ref, binding.scope, selection, timeout)
        )
        return report, {"authority": "none", "evidence_mode": "local_repository_snapshot"}

    monkeypatch.setattr(cli, "_collect", fake)
    assert cli.main(["--authorized", *REFS, "--front-id", front_id, "--format", "json"]) == 0
    output = capsys.readouterr()
    assert not output.err
    serialized = json.loads(output.out)
    assert serialized["snapshot"] == report
    assert serialized["metadata"]["authority"] == "none"
    assert serialized["snapshot"]["product_ready"] is False
    assert calls == [
        ("operator://synthetic", "session://synthetic", ("readiness.snapshot.read",), front_id, 3.0)
    ]
    assert "operator://synthetic" not in output.out and "session://synthetic" not in output.out


def test_text_explicitly_authoral_and_not_human_identity(monkeypatch, capsys):
    async def fake(*_args):
        return build_report(load_inventory()), {"authority": "none"}

    monkeypatch.setattr(cli, "_collect", fake)
    assert cli.main(["--authorized", *REFS]) == 0
    output = capsys.readouterr()
    assert "authored repository snapshot; no Core authority" in output.out
    assert "No runtime verification or human authentication" in output.out
    assert not output.err


@pytest.mark.parametrize(
    "error",
    [
        ValueError("private-secret"),
        OSError("private-path"),
        RuntimeError("private-message"),
        KeyboardInterrupt(),
    ],
)
def test_failure_never_displays_exception(error, monkeypatch, capsys):
    async def fail(*_args):
        raise error

    monkeypatch.setattr(cli, "_collect", fail)
    assert cli.main(["--authorized", *REFS]) == 2
    output = capsys.readouterr()
    assert output.err == "readiness_mcp_failed\n" and not output.out


@pytest.mark.parametrize("stage", ["start", "call", "snapshot", "none"])
def test_collection_closes_own_client_in_all_outcomes(stage, monkeypatch):
    import asyncio

    from apps.jarvis_mcp import readiness_client
    from apps.jarvis_mcp.readiness_contracts import ReadinessBinding

    calls = []

    class Observation:
        def snapshot(self):
            if stage == "snapshot":
                raise ValueError("synthetic-failure")
            return {"product_ready": False}

        def metadata(self):
            return {"authority": "none"}

    class Client:
        def __init__(self, binding, *, authorized, timeout_seconds):
            assert authorized is True and timeout_seconds == 3.0
            self.binding = binding

        async def start(self):
            calls.append("start")
            if stage == "start":
                raise ValueError("synthetic-failure")

        async def call(self, binding, tool, arguments):
            calls.append("call")
            assert binding == self.binding and tool == "read_product_readiness"
            assert arguments == {"front_id": "all"}
            if stage == "call":
                raise ValueError("synthetic-failure")
            return Observation()

        async def close(self):
            calls.append("close")

    monkeypatch.setattr(readiness_client, "FixedReadinessMcpClient", Client)
    binding = ReadinessBinding("operator://synthetic", "session://synthetic")
    if stage != "none":
        with pytest.raises(ValueError, match="synthetic-failure"):
            asyncio.run(cli._collect(binding, "all", 3.0))
    else:
        assert asyncio.run(cli._collect(binding, "all", 3.0)) == (
            {"product_ready": False},
            {"authority": "none"},
        )
    assert calls[-1] == "close"


@pytest.mark.parametrize("stage", ["reconfigure", "write"])
@pytest.mark.parametrize(
    "error",
    [BrokenPipeError("private-pipe"), OSError("private-path"), UnicodeError("private-text")],
)
def test_output_failures_use_fixed_diagnostic(stage, error, monkeypatch, capsys):
    async def fake(*_args):
        return build_report(load_inventory()), {"authority": "none"}

    class FailingOutput:
        def reconfigure(self, **options):
            assert options == {"encoding": "utf-8", "errors": "strict"}
            if stage == "reconfigure":
                raise error

        def write(self, _value):
            raise error

    monkeypatch.setattr(cli, "_collect", fake)
    monkeypatch.setattr(cli.sys, "stdout", FailingOutput())
    assert cli.main(["--authorized", *REFS]) == 2
    output = capsys.readouterr()
    assert output.err == "readiness_mcp_failed\n" and not output.out
