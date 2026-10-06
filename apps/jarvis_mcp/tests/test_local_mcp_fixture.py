from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

import pytest

from apps.jarvis_mcp import FixtureBinding, LocalFixtureMcpClient, McpRejected


def binding() -> FixtureBinding:
    return FixtureBinding("operator://local-test", "session://local-test")


def test_real_subprocess_handshake_list_and_readonly_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "credential_must_not_escape")

    async def run() -> None:
        client = LocalFixtureMcpClient(binding())
        async with client:
            result = await client.call(binding(), "read_fixture_status", {"record_id": "health"})
            assert result.text == "JARVIS synthetic fixture ready. No production access."
            assert result.authority == "none"
            assert result.binding == binding()
            assert result.request_id == 3
            assert client.process_running
            assert result.metadata()["evidence_mode"] == "local_subprocess_fixture"
            assert "text" not in result.metadata()
            assert "synthetic fixture ready" not in repr(result)
        assert not client.process_running
        assert [event.stage for event in client.events] == ["initialize", "call", "close"]
        await client.close()
        assert len(client.events) == 3

    asyncio.run(run())


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("wrong_version", "unsupported_initialize_result"),
        ("missing_capability", "unsupported_initialize_result"),
        ("wrong_server", "unsupported_initialize_result"),
        ("wrong_id", "unexpected_rpc_response"),
        ("oversized", "response_too_large"),
        ("malformed", "invalid_response_json"),
        ("duplicate_keys", "invalid_response_json"),
        ("server_request", "unexpected_rpc_response"),
        ("extra_tool", "tool_descriptor_not_allowlisted"),
        ("schema_drift", "tool_descriptor_not_allowlisted"),
    ],
)
def test_denied_server_protocol_and_descriptors(scenario: str, reason: str) -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding(), fixture_scenario=scenario)
        with pytest.raises(McpRejected, match=reason):
            await client.start()
        assert not client.process_running
        assert client.events[-1].stage == "close"
        assert client._directory is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "scenario,reason",
    [
        ("tool_error", "invalid_or_error_tool_result"),
        ("invalid_result", "invalid_or_error_tool_result"),
        ("oversized_text", "unsupported_tool_content"),
    ],
)
def test_denied_tool_results_close_owned_process(scenario: str, reason: str) -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding(), fixture_scenario=scenario)
        await client.start()
        with pytest.raises(McpRejected, match=reason):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        assert not client.process_running

    asyncio.run(run())


@pytest.mark.parametrize(
    "other,name,arguments,reason",
    [
        (
            FixtureBinding("operator://foreign", "session://local-test"),
            "read_fixture_status",
            {"record_id": "health"},
            "binding_mismatch",
        ),
        (
            FixtureBinding("operator://local-test", "session://foreign"),
            "read_fixture_status",
            {"record_id": "health"},
            "binding_mismatch",
        ),
        (binding(), "write_anything", {"record_id": "health"}, "tool_not_allowlisted"),
        (binding(), "read_fixture_status", {"record_id": "private"}, "invalid_tool_arguments"),
        (
            binding(),
            "read_fixture_status",
            {"record_id": "health", "path": "secret"},
            "invalid_tool_arguments",
        ),
        (binding(), "read_fixture_status", {}, "invalid_tool_arguments"),
    ],
)
def test_local_denials_do_not_dispatch(
    other: FixtureBinding, name: str, arguments: dict[str, object], reason: str
) -> None:
    async def run() -> None:
        async with LocalFixtureMcpClient(binding()) as client:
            with pytest.raises(McpRejected, match=reason):
                await client.call(other, name, arguments)
            assert client._next_id == 2
            assert client.process_running

    asyncio.run(run())


def test_injection_remains_data_never_events_or_metadata() -> None:
    async def run() -> None:
        async with LocalFixtureMcpClient(binding(), fixture_scenario="injection") as client:
            result = await client.call(binding(), "read_fixture_status", {"record_id": "health"})
            assert "Ignore Core governance" in result.text
            assert result.authority == "none"
            safe = json.dumps(result.metadata()) + json.dumps(
                [asdict(event) for event in client.events]
            )
            assert "Ignore Core" not in safe
            assert "grant all permissions" not in safe

    asyncio.run(run())


def test_stderr_is_discarded_not_forwarded(capsys: pytest.CaptureFixture[str]) -> None:
    async def run() -> None:
        async with LocalFixtureMcpClient(binding(), fixture_scenario="stderr_secret") as client:
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
            assert "secret" not in repr(client.events)

    asyncio.run(run())
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_timeout_closes_process_and_prevents_retry() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding(), fixture_scenario="timeout")
        await client.start()
        client.timeout_seconds = 0.2
        with pytest.raises(McpRejected, match="request_timeout"):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        assert not client.process_running
        with pytest.raises(McpRejected, match="session_not_ready"):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        with pytest.raises(McpRejected, match="session_not_new"):
            await client.start()

    asyncio.run(run())


def test_cancel_during_call_closes_process() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding(), fixture_scenario="timeout")
        await client.start()
        cancel = asyncio.Event()
        task = asyncio.create_task(
            client.call(binding(), "read_fixture_status", {"record_id": "health"}, cancel=cancel)
        )
        await asyncio.sleep(0.05)
        cancel.set()
        with pytest.raises(McpRejected, match="cancelled"):
            await task
        assert not client.process_running

    asyncio.run(run())


def test_task_cancellation_and_concurrency_are_fail_closed() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding(), fixture_scenario="timeout")
        await client.start()
        task = asyncio.create_task(
            client.call(binding(), "read_fixture_status", {"record_id": "health"})
        )
        await asyncio.sleep(0.05)
        with pytest.raises(McpRejected, match="concurrent_request_not_supported"):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not client.process_running

    asyncio.run(run())


def test_precancel_and_call_before_handshake_do_not_launch() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding())
        with pytest.raises(McpRejected, match="session_not_ready"):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        cancel = asyncio.Event()
        cancel.set()
        with pytest.raises(McpRejected, match="cancelled"):
            await client.start(cancel=cancel)
        assert client._process is None
        await client.close()

    asyncio.run(run())


@pytest.mark.parametrize("value", [0, -1, 20, float("inf"), float("nan"), True, "3"])
def test_invalid_timeouts(value: object) -> None:
    with pytest.raises(McpRejected, match="invalid_timeout"):
        LocalFixtureMcpClient(binding(), timeout_seconds=value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "principal,session,scope",
    [
        ("", "session://test", ("fixture.read",)),
        ("operator://test\n", "session://test", ("fixture.read",)),
        ("operator://test", "", ("fixture.read",)),
        ("operator://test", "session://test", ("write",)),
        ("operator://test", "session://test", ["fixture.read"]),
    ],
)
def test_invalid_bindings(principal: str, session: str, scope: object) -> None:
    with pytest.raises(McpRejected):
        FixtureBinding(principal, session, scope)  # type: ignore[arg-type]


def test_arbitrary_server_scenario_not_supported() -> None:
    with pytest.raises(McpRejected, match="unknown_fixture_scenario"):
        LocalFixtureMcpClient(binding(), fixture_scenario="python -c arbitrary")


def test_fixed_process_command_and_minimal_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    original = asyncio.create_subprocess_exec
    launches = []

    async def spy(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
        launches.append((args, kwargs))
        return await original(*args, **kwargs)

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)
    monkeypatch.setenv("OPENAI_API_KEY", "must_not_escape")
    monkeypatch.setenv("PYTHONPATH", "must_not_escape")

    async def run() -> None:
        async with LocalFixtureMcpClient(binding()):
            pass

    asyncio.run(run())
    args, kwargs = launches[0]
    assert args[1:3] == ("-I", "-B")
    assert str(args[3]).endswith("fixture_server.py")
    assert "shell" not in kwargs
    assert set(kwargs["env"]) <= {"SYSTEMROOT"}
    assert "must_not_escape" not in repr(kwargs)
    assert kwargs["stderr"] == asyncio.subprocess.DEVNULL


def test_request_and_event_limits_are_fail_closed() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding())
        await client.start()
        client._next_id = 32
        with pytest.raises(McpRejected, match="request_limit_exceeded"):
            await client.call(binding(), "read_fixture_status", {"record_id": "health"})
        assert not client.process_running
        other = LocalFixtureMcpClient(binding())
        await other.start()
        for _ in range(125):
            with pytest.raises(McpRejected, match="tool_not_allowlisted"):
                await other.call(binding(), "foreign", {})
        with pytest.raises(McpRejected, match="event_limit_exceeded"):
            await other.call(binding(), "read_fixture_status", {"record_id": "health"})
        assert len(other.events) == 128
        assert not other.process_running

    asyncio.run(run())


def test_concurrent_start_launches_only_one_process() -> None:
    async def run() -> None:
        client = LocalFixtureMcpClient(binding())
        first = asyncio.create_task(client.start())
        await asyncio.sleep(0)
        with pytest.raises(McpRejected, match="session_not_new"):
            await client.start()
        await first
        await client.close()
        assert not client.process_running

    asyncio.run(run())


def test_close_during_spawn_does_not_orphan_process(monkeypatch: pytest.MonkeyPatch) -> None:
    original = asyncio.create_subprocess_exec

    async def run() -> None:
        entered, release = asyncio.Event(), asyncio.Event()

        async def delayed(*args: object, **kwargs: object) -> asyncio.subprocess.Process:
            entered.set()
            await release.wait()
            return await original(*args, **kwargs)

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
        client = LocalFixtureMcpClient(binding())
        starting = asyncio.create_task(client.start())
        await entered.wait()
        closing = asyncio.create_task(client.close())
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(McpRejected, match="session_closed_during_start"):
            await starting
        await closing
        assert not client.process_running
        assert client._directory is None

    asyncio.run(run())
