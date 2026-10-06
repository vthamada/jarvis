"""Host callbacks cannot turn private/forged error codes into output or I/O."""

from __future__ import annotations

import ast
import threading
import tomllib
from pathlib import Path

import pytest
from operational_service.adapters.browser import (
    CredentiallessHttpsReader,
    HttpsReadRequest,
    HttpsReadScope,
    https_reader,
)
from operational_service.adapters.browser.https_contracts import HttpsReadRefused

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "code", ["private-code", ["private-code"], {"private": "code"}, None, True]
)
def test_callback_refusal_code_is_sanitized_before_io(monkeypatch, code):
    scope = HttpsReadScope("operator:a", "session:a", "scope:a", "purpose:read",
                           "https://example.test/", "8.8.8.8")
    request = HttpsReadRequest(scope.principal_ref, scope.session_ref, scope.scope_ref,
                               scope.purpose_ref, scope.url, scope.ipv4_pin)

    class Cancel(threading.Event):
        def is_set(self):
            raise HttpsReadRefused(code)

    monkeypatch.setattr(https_reader, "PinnedTlsConnection", lambda *args: pytest.fail("I/O"))
    result = CredentiallessHttpsReader(scope).observe(request, authorized=True, cancel=Cancel())
    assert result.status == "refused" and result.error_code == "transport_unavailable"
    assert "private" not in str(result.telemetry())


def test_https_runtime_uses_no_cryptography_or_http_sdk_dependency():
    directory = ROOT / "services/operational-service/src/operational_service/adapters/browser"
    for path in directory.glob("https_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                roots.add(node.module.split(".")[0])
        assert not roots & {"cryptography", "requests", "httpx", "aiohttp"}
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert metadata["project"]["dependencies"] == []
    assert any(value.startswith("cryptography>=")
               for value in metadata["project"]["optional-dependencies"]["dev"])
