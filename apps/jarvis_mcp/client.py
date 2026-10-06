"""Strict stdio MCP fixture client; descriptors and output confer no authority."""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from .fixture_server import INPUT_SCHEMA, PROTOCOL_VERSION, SCENARIOS, TOOL_NAME

MAX_MESSAGE_BYTES = 65536
MAX_SESSION_BYTES = 262144
MAX_TEXT_LENGTH = 4096
MAX_EVENTS = 128
MAX_REQUESTS = 32
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}\Z")


class McpRejected(ValueError):
    """A content-free, stable rejection reason; never includes server output."""


@dataclass(frozen=True)
class FixtureBinding:
    principal_ref: str
    session_ref: str
    scope: tuple[str, ...] = ("fixture.read",)

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not _REF.fullmatch(value)
            for value in (self.principal_ref, self.session_ref)
        ):
            raise McpRejected("invalid_binding")
        if not isinstance(self.scope, tuple) or self.scope != ("fixture.read",):
            raise McpRejected("unsupported_scope")


@dataclass(frozen=True)
class McpEvent:
    stage: str
    status: str
    reason: str = ""


@dataclass(frozen=True)
class McpObservation:
    binding: FixtureBinding
    text: str = field(repr=False)
    request_id: int
    tool_name: str = TOOL_NAME
    server_ref: str = "fixture://jarvis-mcp"
    protocol_version: str = PROTOCOL_VERSION
    evidence_mode: str = "local_subprocess_fixture"
    authority: str = "none"

    def metadata(self) -> dict[str, object]:
        """Content-free evidence; bindings remain labels, not authentication."""
        return {
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "server_ref": self.server_ref,
            "protocol_version": self.protocol_version,
            "evidence_mode": self.evidence_mode,
            "authority": self.authority,
            "text_length": len(self.text),
            "status": "completed",
        }


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise McpRejected("duplicate_json_key")
        result[key] = value
    return result


def _safe_text(value: object, limit: int = MAX_TEXT_LENGTH) -> bool:
    return (
        isinstance(value, str)
        and 0 < len(value) <= limit
        and not any(
            ord(char) < 32 and char not in "\n\r\t" or 0xD800 <= ord(char) <= 0xDFFF
            for char in value
        )
    )


class LocalFixtureMcpClient:
    """One sequential, fixed-server session. No arbitrary command/configuration API.

    This is process isolation hygiene, not an OS sandbox. Only the trusted repository
    fixture is launched; never substitute downloaded or user-selected scripts.
    """

    def __init__(
        self,
        binding: FixtureBinding,
        *,
        timeout_seconds: float = 3.0,
        fixture_scenario: str = "normal",
    ) -> None:
        if not isinstance(binding, FixtureBinding):
            raise McpRejected("invalid_binding")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (float, int))
            or not math.isfinite(timeout_seconds)
            or not 0.01 <= timeout_seconds <= 10
        ):
            raise McpRejected("invalid_timeout")
        if fixture_scenario not in SCENARIOS:
            raise McpRejected("unknown_fixture_scenario")
        self._binding = binding
        self.timeout_seconds = float(timeout_seconds)
        self._scenario = fixture_scenario
        self._process: asyncio.subprocess.Process | None = None
        self._directory: TemporaryDirectory[str] | None = None
        self._events: list[McpEvent] = []
        self._ready = False
        self._starting = False
        self._start_finished = asyncio.Event()
        self._start_finished.set()
        self._closed = False
        self._busy = False
        self._next_id = 0
        self._bytes = 0

    @property
    def binding(self) -> FixtureBinding:
        return self._binding

    @property
    def events(self) -> tuple[McpEvent, ...]:
        return tuple(self._events)

    @property
    def process_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    def _event(self, stage: str, status: str, reason: str = "") -> None:
        if len(self._events) < MAX_EVENTS:
            self._events.append(McpEvent(stage, status, reason))

    async def __aenter__(self) -> LocalFixtureMcpClient:
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def start(self, *, cancel: asyncio.Event | None = None) -> None:
        if self._process is not None or self._closed or self._starting:
            raise McpRejected("session_not_new")
        if cancel is not None and cancel.is_set():
            self._event("initialize", "rejected", "cancelled")
            raise McpRejected("cancelled")
        self._starting = True
        self._start_finished.clear()
        # Absolute interpreter, isolated Python, no shell, environment or credentials
        # forwarded. SystemRoot is required by Windows process/runtime plumbing only.
        environment = {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if "SYSTEMROOT" in os.environ else {}
        try:
            self._directory = TemporaryDirectory(prefix="jarvis-mcp-fixture-")
            self._process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-I",
                "-B",
                str(Path(__file__).with_name("fixture_server.py")),
                "--scenario",
                self._scenario,
                cwd=self._directory.name,
                env=environment,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                limit=MAX_MESSAGE_BYTES,
            )
            if self._closed:
                raise McpRejected("session_closed_during_start")
            result = await self._rpc(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "jarvis-local-fixture", "version": "1.0.0"},
                },
                cancel=cancel,
            )
            if (
                result.get("protocolVersion") != PROTOCOL_VERSION
                or result.get("capabilities") != {"tools": {}}
                or result.get("serverInfo") != {"name": "jarvis-fixture", "version": "1.0.0"}
                or set(result) != {"protocolVersion", "capabilities", "serverInfo"}
            ):
                raise McpRejected("unsupported_initialize_result")
            await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            listed = await self._rpc("tools/list", {}, cancel=cancel)
            expected = {
                "tools": [
                    {
                        "name": TOOL_NAME,
                        "description": "Read synthetic status only.",
                        "inputSchema": INPUT_SCHEMA,
                        "annotations": {"readOnlyHint": True},
                    }
                ]
            }
            if json.dumps(listed, sort_keys=True) != json.dumps(expected, sort_keys=True):
                raise McpRejected("tool_descriptor_not_allowlisted")
            self._ready = True
            self._event("initialize", "completed")
        except BaseException as error:
            reason = str(error) if isinstance(error, McpRejected) else "startup_failed"
            self._event("initialize", "rejected", reason)
            self._starting = False
            self._start_finished.set()
            await self.close()
            if isinstance(error, (McpRejected, asyncio.CancelledError)):
                raise
            raise McpRejected("startup_failed") from None
        finally:
            self._starting = False
            self._start_finished.set()

    async def call(
        self,
        binding: FixtureBinding,
        tool_name: str,
        arguments: dict[str, object],
        *,
        cancel: asyncio.Event | None = None,
    ) -> McpObservation:
        reason = ""
        if len(self._events) >= MAX_EVENTS - 2:
            self._event("call", "rejected", "event_limit_exceeded")
            await self.close()
            raise McpRejected("event_limit_exceeded")
        if not self._ready or self._closed:
            reason = "session_not_ready"
        elif binding != self.binding:
            reason = "binding_mismatch"
        elif tool_name != TOOL_NAME:
            reason = "tool_not_allowlisted"
        elif (
            type(arguments) is not dict
            or set(arguments) != {"record_id"}
            or type(arguments["record_id"]) is not str
            or arguments["record_id"] != "health"
        ):
            reason = "invalid_tool_arguments"
        elif self._busy:
            reason = "concurrent_request_not_supported"
        if reason:
            self._event("call", "rejected", reason)
            raise McpRejected(reason)
        self._busy = True
        try:
            result = await self._rpc(
                "tools/call", {"name": TOOL_NAME, "arguments": arguments}, cancel=cancel
            )
            if set(result) != {"content", "isError"} or result["isError"] is not False:
                raise McpRejected("invalid_or_error_tool_result")
            content = result["content"]
            if (
                not isinstance(content, list)
                or len(content) != 1
                or not isinstance(content[0], dict)
                or set(content[0]) != {"type", "text"}
                or content[0]["type"] != "text"
                or not _safe_text(content[0]["text"])
            ):
                raise McpRejected("unsupported_tool_content")
            observation = McpObservation(self.binding, content[0]["text"], self._next_id)
            self._event("call", "completed")
            return observation
        except BaseException as error:
            reason = str(error) if isinstance(error, McpRejected) else "call_failed"
            self._event("call", "rejected", reason)
            await self.close()
            if isinstance(error, (McpRejected, asyncio.CancelledError)):
                raise
            raise McpRejected("call_failed") from None
        finally:
            self._busy = False

    async def _send(self, message: dict[str, object]) -> None:
        if self._process is None or self._process.stdin is None:
            raise McpRejected("transport_closed")
        encoded = (json.dumps(message, separators=(",", ":"), allow_nan=False) + "\n").encode()
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise McpRejected("request_too_large")
        self._process.stdin.write(encoded)
        await asyncio.wait_for(self._process.stdin.drain(), timeout=self.timeout_seconds)

    async def _rpc(
        self, method: str, params: dict[str, object], *, cancel: asyncio.Event | None
    ) -> dict[str, Any]:
        if cancel is not None and cancel.is_set():
            raise McpRejected("cancelled")
        if self._next_id >= MAX_REQUESTS:
            raise McpRejected("request_limit_exceeded")
        self._next_id += 1
        request_id = self._next_id
        await self._send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
        if self._process is None or self._process.stdout is None:
            raise McpRejected("transport_closed")
        reader = asyncio.create_task(self._process.stdout.readline())
        cancelled = asyncio.create_task(cancel.wait()) if cancel is not None else None
        tasks = {reader} if cancelled is None else {reader, cancelled}
        try:
            done, _ = await asyncio.wait(
                tasks, timeout=self.timeout_seconds, return_when=asyncio.FIRST_COMPLETED
            )
            if cancelled is not None and cancelled in done:
                await self._cancel_request(request_id)
                raise McpRejected("cancelled")
            if reader not in done:
                await self._cancel_request(request_id)
                raise McpRejected("request_timeout")
            try:
                line = reader.result()
            except (ValueError, asyncio.LimitOverrunError):
                raise McpRejected("response_too_large") from None
            self._bytes += len(line)
            if (
                not line
                or not line.endswith(b"\n")
                or len(line) > MAX_MESSAGE_BYTES
                or self._bytes > MAX_SESSION_BYTES
            ):
                raise McpRejected("invalid_response_size")
            try:
                message = json.loads(
                    line.decode("utf-8"),
                    object_pairs_hook=_object,
                    parse_constant=lambda _value: (_ for _ in ()).throw(
                        McpRejected("invalid_json_number")
                    ),
                )
            except (ValueError, UnicodeError, RecursionError):
                raise McpRejected("invalid_response_json") from None
            if (
                not isinstance(message, dict)
                or set(message) != {"jsonrpc", "id", "result"}
                or message["jsonrpc"] != "2.0"
                or type(message["id"]) is not int
                or message["id"] != request_id
                or not isinstance(message["result"], dict)
            ):
                raise McpRejected("unexpected_rpc_response")
            return message["result"]
        except asyncio.CancelledError:
            await self._cancel_request(request_id)
            raise
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _cancel_request(self, request_id: int) -> None:
        try:
            await self._send(
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/cancelled",
                    "params": {"requestId": request_id, "reason": "local_request_stopped"},
                }
            )
        except (OSError, RuntimeError, TimeoutError, McpRejected):
            pass

    async def close(self) -> None:
        self._ready = False
        self._closed = True
        if self._starting:
            await self._start_finished.wait()
        process = self._process
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.returncode is None:
                try:
                    await asyncio.wait_for(process.wait(), timeout=0.2)
                except TimeoutError:
                    try:
                        process.terminate()
                    except ProcessLookupError:
                        pass
                    try:
                        await asyncio.wait_for(process.wait(), timeout=0.2)
                    except TimeoutError:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                        await process.wait()
            if process.stdin is not None:
                try:
                    await process.stdin.wait_closed()
                except (OSError, RuntimeError):
                    pass
        if self._directory is not None:
            self._directory.cleanup()
            self._directory = None
        if not self._events or self._events[-1].stage != "close":
            self._event("close", "completed")
