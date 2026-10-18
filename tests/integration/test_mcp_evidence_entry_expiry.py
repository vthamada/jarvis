"""Entry expiry must refuse before attestation, not masquerade as a drift result.

The clock advances only in the pilot module after real Core initialization;
MCP stdio, client deadlines, asyncio and UTC remain real. This demonstrates a
controlled failure path, not the cause of uncaptured historical gate failures.
"""

import asyncio
from types import SimpleNamespace

import pytest

from apps.jarvis_console import mcp_pilot, readiness_mcp_pilot


@pytest.mark.parametrize("module,entry", [
    (mcp_pilot, "run_mcp_core_pilot"),
    (readiness_mcp_pilot, "run_readiness_mcp_core_pilot"),
], ids=["fixture", "readiness"])
def test_entry_expiry_after_real_core_build_never_reaches_handle(tmp_path, monkeypatch,
                                                               module, entry):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    clock, built, handled = [0.0], [], []
    original = module._isolated_core

    def build(runtime):
        core = original(runtime)
        built.append(True)

        def forbidden(_contract):
            handled.append(True)
            pytest.fail("expired_entry_reached_core_handle")

        core.handle_input = forbidden
        clock[0] = 11.0
        return core

    monkeypatch.setattr(module, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(module, "_isolated_core", build)
    result = asyncio.run(getattr(module, entry)(
        authorized=True, workspace_root=workspace, timeout_seconds=10,
    ))
    assert result.status == "refused"
    assert result.reason == "report_entry_cancelled_or_expired"
    assert result.memory_record_id is None
    assert built == [True] and handled == []
    assert not list(workspace.iterdir())
