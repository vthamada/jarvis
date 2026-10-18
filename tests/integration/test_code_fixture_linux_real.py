"""Opt-in Docker fixtures; skips are never evidence of physical Linux execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools.run_code_fixture_linux import IMAGE, fixture_sha256

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(
    os.environ.get("JARVIS_CODE_FIXTURE_TEST_AUTHORIZED") != "yes",
    reason="Physical Docker fixtures require explicit operator opt-in",
)
@pytest.mark.parametrize("scenario,counts", [
    ("baseline", (3, 0, 3)), ("candidate", (3, 3, 0)),
    ("isolation", (5, 5, 0)), ("timeout", (0, 0, 0)),
])
def test_fixed_linux_fixture_real_child_protocol_and_cleanup(tmp_path, scenario, counts):
    before = tuple(tmp_path.iterdir())
    child = subprocess.run(
        [sys.executable, str(ROOT / "tools/run_code_fixture_linux.py"),
         "--authorized", "--scenario", scenario],
        cwd=tmp_path, capture_output=True, timeout=90,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    assert child.returncode == 0, "controlled_fixture_failed"
    assert not child.stderr and len(child.stdout) <= 4096
    report = json.loads(child.stdout)
    assert report["schema_version"] == "jarvis-code-fixture-proof-v1"
    assert report["status"] == "passed" and report["cleanup_verified"] is True
    assert report["execution_started"] is True
    assert report["evidence_mode"] == "controlled_linux_fixture"
    assert report["scenario"] == scenario
    assert report["image_sha256"] == IMAGE
    assert report["fixture_sha256"] == fixture_sha256(scenario)
    assert (report["test_count"], report["passed_count"], report["failed_count"]) == counts
    assert report["reason"] == (
        "expected_timeout" if scenario == "timeout" else "expected_fixture_outcome"
    )
    assert report["authority"] == "none" and report["capability_promoted"] is False
    assert tuple(tmp_path.iterdir()) == before
