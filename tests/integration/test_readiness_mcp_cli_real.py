"""Standalone CLI -> isolated stdio -> actual authored inventory, no Core/account."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.product_readiness_report import build_report, load_inventory

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("selection", ["all", "F06", "F13"])
def test_cli_real_readonly_snapshot_exact_selection(selection):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.jarvis_console.readiness_mcp_cli",
            "--authorized",
            "--principal-ref",
            "operator://synthetic",
            "--session-ref",
            "session://synthetic",
            "--front-id",
            selection,
            "--format",
            "json",
            "--timeout-seconds",
            "10",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    report = build_report(load_inventory())
    snapshot = result["snapshot"]
    assert snapshot["fronts"] == [
        front for front in report["fronts"] if selection == "all" or front["id"] == selection
    ]
    assert snapshot["counts"] == report["counts"]
    assert snapshot["last_validated_mb"] == report["last_validated_mb"]
    assert snapshot["active_mb"] == report["active_mb"]
    assert snapshot["evidence_scope"] == "authored_snapshot"
    assert snapshot["origin"] == "local_repository_snapshot" and snapshot["authority"] == "none"
    assert snapshot["product_ready"] is snapshot["runtime_verified"] is False
    assert result["metadata"]["front_id"] == selection and result["metadata"]["request_id"] == 3
    assert result["metadata"]["authority"] == "none"
    assert not completed.stderr
    assert "operator://synthetic" not in completed.stdout
    assert "session://synthetic" not in completed.stdout
