"""Explicit fixed-server MCP reader. No generic commands or authority dispatch."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from . import readiness_contracts as contract


class FixedReadinessMcpClient:
    """One bounded sequential session; Python labels are not human authentication."""

    def __init__(self, binding: contract.ReadinessBinding, *, authorized=False,
                 timeout_seconds=3.0):
        if authorized is not True:
            raise contract.ReadinessRejected("authorization_required")
        if type(binding) is not contract.ReadinessBinding:
            raise contract.ReadinessRejected("invalid_binding")
        binding.__post_init__()
        self._binding = contract.ReadinessBinding(binding.principal_ref, binding.session_ref,
                                                  binding.scope)
        self._binding_key = (binding.principal_ref, binding.session_ref, binding.scope)
        self._timeout = contract.validate_timeout(timeout_seconds)
        self._process, self._directory, self._deadline = None, None, None
        self._next_id, self._received, self._sent = 0, 0, 0
        self._events = []
        self._ready, self._starting, self._closed, self._busy = False, False, False, False
        self._start_finished = asyncio.Event()
        self._start_finished.set()

    @property
    def binding(self):
        return self._binding

    @property
    def events(self):
        return tuple(self._events)

    @property
    def process_running(self):
        return self._process is not None and self._process.returncode is None

    def _event(self, stage, status, reason=""):
        if len(self._events) < contract.MAX_EVENTS:
            self._events.append(contract.ReadinessEvent(stage, status, reason))

    def _fence_binding(self):
        if (type(self._binding) is not contract.ReadinessBinding
                or (self._binding.principal_ref, self._binding.session_ref, self._binding.scope)
                != self._binding_key):
            raise contract.ReadinessRejected("binding_mismatch")
        self._binding.__post_init__()

    def _remaining(self):
        value = self._deadline - time.monotonic()
        if value <= 0:
            raise contract.ReadinessRejected("collection_timeout")
        return value

    @staticmethod
    def _cancel_flag(cancel):
        if cancel is not None and not isinstance(cancel, asyncio.Event):
            raise contract.ReadinessRejected("invalid_cancellation")
        if cancel is not None and cancel.is_set():
            raise contract.ReadinessRejected("cancelled")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_args):
        await self.close()

    async def start(self, *, cancel=None):
        if self._process is not None or self._starting or self._closed:
            raise contract.ReadinessRejected("session_not_new")
        self._fence_binding()
        self._cancel_flag(cancel)
        self._starting = True
        self._start_finished.clear()
        self._deadline = time.monotonic() + self._timeout
        environment = {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if "SYSTEMROOT" in os.environ else {}
        try:
            self._directory = TemporaryDirectory(prefix="jarvis-mcp-readiness-")
            self._process = await asyncio.create_subprocess_exec(
                str(Path(sys.executable).resolve()), "-I", "-B",
                str(Path(__file__).with_name("readiness_server.py").resolve()), "--authorized",
                cwd=self._directory.name, env=environment, shell=False,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL, limit=contract.MAX_MESSAGE_BYTES,
            )
            if self._closed:
                raise contract.ReadinessRejected("session_closed_during_start")
            result = await self._rpc("initialize", {
                "protocolVersion": contract.PROTOCOL_VERSION, "capabilities": {},
                "clientInfo": contract.CLIENT_INFO}, cancel=cancel)
            if result != {"protocolVersion": contract.PROTOCOL_VERSION,
                          "capabilities": {"tools": {}}, "serverInfo": contract.SERVER_INFO}:
                raise contract.ReadinessRejected("initialize_not_allowlisted")
            await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            result = await self._rpc("tools/list", {}, cancel=cancel)
            if contract.encode_json(result, sort_keys=True) != contract.encode_json({
                    "tools": [contract.TOOL_DESCRIPTOR]}, sort_keys=True):
                raise contract.ReadinessRejected("descriptor_not_allowlisted")
            self._ready = True
            self._event("initialize", "completed")
        except BaseException as error:
            reason = (str(error) if isinstance(error, contract.ReadinessRejected)
                      else "startup_failed")
            self._event("initialize", "rejected", reason)
            self._starting = False
            self._start_finished.set()
            await self.close()
            if isinstance(error, (contract.ReadinessRejected, asyncio.CancelledError)):
                raise
            raise contract.ReadinessRejected("startup_failed") from None
        finally:
            self._starting = False
            self._start_finished.set()

    async def call(self, binding, tool_name, arguments, *, cancel=None):
        # Validate before dispatch; these refusals do not send a tool invocation.
        if not self._ready or self._closed:
            raise contract.ReadinessRejected("session_not_ready")
        self._fence_binding()
        if type(binding) is not contract.ReadinessBinding or binding != self._binding:
            raise contract.ReadinessRejected("binding_mismatch")
        binding.__post_init__()
        if tool_name != contract.TOOL_NAME or type(tool_name) is not str:
            raise contract.ReadinessRejected("tool_not_allowlisted")
        selection = contract.validate_arguments(arguments)
        try:
            self._cancel_flag(cancel)
        except contract.ReadinessRejected as error:
            if str(error) == "cancelled":
                self._event("call", "rejected", "cancelled")
                await self.close()
            raise
        if self._busy:
            raise contract.ReadinessRejected("concurrent_request_not_supported")
        if len(self._events) >= contract.MAX_EVENTS - 2:
            await self.close()
            raise contract.ReadinessRejected("event_limit_exceeded")
        self._busy = True
        try:
            result = await self._rpc("tools/call", {"name": tool_name,
                                     "arguments": {"front_id": selection}}, cancel=cancel)
            if (set(result) != {"content", "structuredContent", "isError"}
                    or result["isError"] is not False or type(result["content"]) is not list
                    or len(result["content"]) != 1 or type(result["content"][0]) is not dict
                    or set(result["content"][0]) != {"type", "text"}
                    or result["content"][0]["type"] != "text"
                    or type(result["content"][0]["text"]) is not str):
                raise contract.ReadinessRejected("invalid_tool_result")
            text = result["content"][0]["text"].encode("utf-8", "strict")
            if (len(text) > contract.MAX_SNAPSHOT_BYTES
                    or contract.encode_json(contract.parse_json(text), sort_keys=True)
                    != contract.encode_json(result["structuredContent"], sort_keys=True)):
                raise contract.ReadinessRejected("snapshot_mirror_mismatch")
            snapshot = contract.validate_snapshot(result["structuredContent"], selection)
            self._fence_binding()
            self._cancel_flag(cancel)
            self._remaining()
            observation = contract.ReadinessObservation(self._binding, self._next_id,
                                                        selection, contract.encode_json(snapshot))
            self._event("call", "completed")
            return observation
        except BaseException as error:
            reason = str(error) if isinstance(error, contract.ReadinessRejected) else "call_failed"
            self._event("call", "rejected", reason)
            await self.close()
            if isinstance(error, (contract.ReadinessRejected, asyncio.CancelledError)):
                raise
            raise contract.ReadinessRejected("call_failed") from None
        finally:
            self._busy = False

    async def _send(self, message):
        if self._process is None or self._process.stdin is None:
            raise contract.ReadinessRejected("transport_closed")
        self._remaining()
        encoded = contract.encode_json(message) + b"\n"
        self._sent += len(encoded)
        if (len(encoded) > contract.MAX_MESSAGE_BYTES
                or self._sent + self._received > contract.MAX_SESSION_BYTES):
            raise contract.ReadinessRejected("request_limit_exceeded")
        self._remaining()
        self._process.stdin.write(encoded)
        await asyncio.wait_for(self._process.stdin.drain(), timeout=self._remaining())

    async def _rpc(self, method, params, *, cancel):
        self._cancel_flag(cancel)
        if self._next_id >= contract.MAX_REQUESTS:
            raise contract.ReadinessRejected("request_limit_exceeded")
        self._next_id += 1
        identifier = self._next_id
        await self._send({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        reader = asyncio.create_task(self._process.stdout.readline())
        cancellation = asyncio.create_task(cancel.wait()) if cancel is not None else None
        tasks = {reader} if cancellation is None else {reader, cancellation}
        try:
            done, _ = await asyncio.wait(tasks, timeout=self._remaining(),
                                         return_when=asyncio.FIRST_COMPLETED)
            if cancellation is not None and cancellation in done:
                await self._cancel_request(identifier)
                raise contract.ReadinessRejected("cancelled")
            if reader not in done:
                await self._cancel_request(identifier)
                raise contract.ReadinessRejected("collection_timeout")
            try:
                raw = reader.result()
            except (ValueError, asyncio.LimitOverrunError):
                raise contract.ReadinessRejected("response_too_large") from None
            self._received += len(raw)
            if (not raw or not raw.endswith(b"\n") or b"\r" in raw[:-1]
                    or len(raw) > contract.MAX_MESSAGE_BYTES
                    or self._received + self._sent > contract.MAX_SESSION_BYTES):
                raise contract.ReadinessRejected("invalid_response_size")
            response = contract.parse_json(raw[:-1])
            if (type(response) is not dict or set(response) != {"jsonrpc", "id", "result"}
                    or response["jsonrpc"] != "2.0" or type(response["id"]) is not int
                    or response["id"] != identifier or type(response["result"]) is not dict):
                raise contract.ReadinessRejected("unexpected_rpc_response")
            self._cancel_flag(cancel)
            self._remaining()
            return response["result"]
        except asyncio.CancelledError:
            await self._cancel_request(identifier)
            raise
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _cancel_request(self, identifier):
        try:
            await self._send({"jsonrpc": "2.0", "method": "notifications/cancelled",
                              "params": {"requestId": identifier,
                                         "reason": "local_request_stopped"}})
        except (OSError, RuntimeError, TimeoutError, contract.ReadinessRejected):
            pass

    async def close(self):
        self._ready, self._closed = False, True
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
