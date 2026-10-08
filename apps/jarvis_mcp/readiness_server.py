"""Fixed stdio MCP server reading only the authored repository inventory.

No Core, network, account, subprocess, credential or operational runtime imports.
Running trusted Python is process hygiene, not an operating-system sandbox.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

if __package__:
    from . import readiness_contracts as contract
else:
    spec = importlib.util.spec_from_file_location(
        "jarvis_owned_readiness_contracts", Path(__file__).with_name("readiness_contracts.py"))
    contract = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = contract
    spec.loader.exec_module(contract)


class ReadinessServer:
    def __init__(self, *, root=None):
        self._root = root  # trusted in-process tests only; CLI offers no root/path argument
        self._handshake, self._initialized, self._last_id = False, False, 0

    @staticmethod
    def _error(identifier, code=-32600):
        return {"jsonrpc": "2.0", "id": identifier,
                "error": {"code": code, "message": "readiness_request_refused"}}

    def handle(self, message):
        if (type(message) is not dict or message.get("jsonrpc") != "2.0"
                or type(message.get("method")) is not str):
            return self._error(None)
        method = message["method"]
        if "id" not in message:
            if (message == {"jsonrpc": "2.0", "method": "notifications/initialized"}
                    and self._handshake and not self._initialized):
                self._initialized = True
                return None
            if (set(message) == {"jsonrpc", "method", "params"}
                    and method == "notifications/cancelled"
                    and type(message["params"]) is dict
                    and set(message["params"]) == {"requestId", "reason"}
                    and type(message["params"]["requestId"]) is int
                    and 1 <= message["params"]["requestId"] <= self._last_id
                    and message["params"]["reason"] == "local_request_stopped"):
                return None
            return self._error(None)
        identifier = message["id"]
        if (type(identifier) is not int or identifier != self._last_id + 1
                or identifier > contract.MAX_REQUESTS
                or set(message) != {"jsonrpc", "id", "method", "params"}
                or type(message["params"]) is not dict):
            return self._error(None)
        self._last_id = identifier
        params = message["params"]
        if method == "initialize" and not self._handshake:
            if params != {"protocolVersion": contract.PROTOCOL_VERSION,
                          "capabilities": {}, "clientInfo": contract.CLIENT_INFO}:
                return self._error(identifier, -32602)
            self._handshake = True
            result = {"protocolVersion": contract.PROTOCOL_VERSION, "capabilities": {"tools": {}},
                      "serverInfo": contract.SERVER_INFO}
        elif method == "tools/list" and self._initialized and params == {}:
            result = {"tools": [contract.TOOL_DESCRIPTOR]}
        elif method == "tools/call" and self._initialized:
            if (set(params) != {"name", "arguments"} or params["name"] != contract.TOOL_NAME):
                return self._error(identifier, -32602)
            try:
                selection = contract.validate_arguments(params["arguments"])
            except contract.ReadinessRejected:
                return self._error(identifier, -32602)
            try:
                snapshot = contract.build_snapshot(selection, root=self._root)
                result = {"content": [{"type": "text",
                                       "text": contract.encode_json(snapshot).decode("utf-8")}],
                          "structuredContent": snapshot, "isError": False}
                candidate = {"jsonrpc": "2.0", "id": identifier, "result": result}
                if len(contract.encode_json(candidate)) + 1 > contract.MAX_MESSAGE_BYTES:
                    raise contract.ReadinessRejected("response_too_large")
            except Exception:
                result = {"content": [{"type": "text", "text": "readiness_inventory_unavailable"}],
                          "isError": True}
        else:
            return self._error(identifier, -32601)
        return {"jsonrpc": "2.0", "id": identifier, "result": result}


def run(stream, output, *, root=None):
    server, total = ReadinessServer(root=root), 0
    while True:
        raw = stream.readline(contract.MAX_MESSAGE_BYTES + 1)
        if not raw:
            return 0
        total += len(raw)
        if (len(raw) > contract.MAX_MESSAGE_BYTES or total > contract.MAX_SESSION_BYTES
                or not raw.endswith(b"\n") or b"\n" in raw[:-1] or b"\r" in raw[:-1]):
            return 2
        try:
            message = contract.parse_json(raw[:-1])
        except contract.ReadinessRejected:
            response = server._error(None, -32700)
        else:
            response = server.handle(message)
        if response is not None:
            encoded = contract.encode_json(response) + b"\n"
            total += len(encoded)
            if (len(encoded) > contract.MAX_MESSAGE_BYTES or total > contract.MAX_SESSION_BYTES):
                return 2
            output.write(encoded)
            output.flush()
            if "error" in response:
                return 2


def main(argv=None):
    # Exact opt-in before loading any inventory; no arbitrary paths or modes.
    if (sys.argv[1:] if argv is None else argv) != ["--authorized"]:
        return 2
    try:
        return run(sys.stdin.buffer, sys.stdout.buffer)
    except Exception:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
