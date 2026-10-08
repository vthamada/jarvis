"""Optional browser proof stays inert without exact authorization/configuration."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "arguments,reason",
    [
        ([], "projection_browser_authorization_required"),
        (["--untrusted", "private-secret"], "projection_browser_authorization_required"),
        (["--authorized", "--untrusted"], "projection_browser_authorization_required"),
        (["--authorized"], "invalid_projection_browser_options"),
    ],
)
def test_browser_harness_no_implicit_launch_or_argument_reflection(arguments, reason):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; browser proof not inferred")
    script = Path(__file__).resolve().parents[1] / "support/local_generative_projection_browser.cjs"
    environment = {"SystemRoot": os.environ["SystemRoot"]} if "SystemRoot" in os.environ else {}
    completed = subprocess.run(
        [node, str(script), *arguments],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=5,
        check=False,
    )
    assert completed.returncode == 2
    assert completed.stderr == reason + "\n" and not completed.stdout
