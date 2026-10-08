"""Compact optional browser proof refuses before loading or launching a browser."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


def run_harness(arguments, *, options=None):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; browser proof not inferred")
    script = Path(__file__).resolve().parents[1] / "support/compact_live_web_browser.cjs"
    environment = {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if "SYSTEMROOT" in os.environ else {}
    environment.update(options or {})
    return subprocess.run([node, str(script), *arguments], env=environment,
                          capture_output=True, text=True, encoding="utf-8", timeout=5,
                          check=False)


@pytest.mark.parametrize("arguments,reason", [
    ([], "compact_browser_authorization_required"),
    (["--untrusted", "private-secret"], "compact_browser_authorization_required"),
    (["--authorized", "--untrusted"], "compact_browser_authorization_required"),
    (["--authorized"], "invalid_compact_browser_options"),
    (["--baseline"], "compact_browser_authorization_required"),
    (["--authorized", "--baseline"], "compact_browser_authorization_required"),
])
def test_compact_harness_exact_authorization_no_launch_or_argument_reflection(arguments, reason):
    completed = run_harness(arguments)
    assert completed.returncode == 2
    assert completed.stderr == reason + "\n" and not completed.stdout


@pytest.mark.parametrize("key,value", [
    ("JARVIS_PROJECTION_TEST_URL", "http://127.0.0.1:65536/"),
    ("JARVIS_PROJECTION_TEST_URL", "http://localhost:8765/"),
    ("JARVIS_PROJECTION_TEST_URL", "https://127.0.0.1:8765/"),
    ("JARVIS_PROJECTION_TEST_URL", "http://127.0.0.1:8765/?private-secret"),
    ("JARVIS_PROJECTION_TEST_SECRET", "A" * 64),
    ("JARVIS_PROJECTION_TEST_SECRET", "a" * 63),
    ("JARVIS_PROJECTION_TEST_PACKAGE", "private-untrusted-module.cjs"),
    ("JARVIS_PROJECTION_TEST_BROWSER", "private-untrusted-browser.exe"),
])
def test_invalid_compact_configuration_before_external_require_or_launch(tmp_path, key, value):
    # Absolute nonexistent dependencies deliberately cannot load or launch. A
    # fixed options refusal therefore demonstrates validation precedes both.
    options = {
        "JARVIS_PROJECTION_TEST_URL": "http://127.0.0.1:8765/",
        "JARVIS_PROJECTION_TEST_SECRET": "a" * 64,
        "JARVIS_PROJECTION_TEST_PACKAGE": str(tmp_path / "private-never-required.cjs"),
        "JARVIS_PROJECTION_TEST_BROWSER": str(tmp_path / "private-never-launched.exe"),
    }
    options[key] = value
    completed = run_harness(["--authorized"], options=options)
    assert completed.returncode == 2
    assert completed.stderr == "invalid_compact_browser_options\n" and not completed.stdout
