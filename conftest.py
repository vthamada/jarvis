"""Repository-wide pytest bootstrap."""

import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "orchestrator-service" / "src",
    ROOT / "services" / "memory-service" / "src",
    ROOT / "services" / "governance-service" / "src",
    ROOT / "services" / "operational-service" / "src",
    ROOT / "services" / "knowledge-service" / "src",
    ROOT / "services" / "observability-service" / "src",
    ROOT / "engines" / "identity-engine" / "src",
    ROOT / "engines" / "executive-engine" / "src",
    ROOT / "engines" / "cognitive-engine" / "src",
    ROOT / "engines" / "planning-engine" / "src",
    ROOT / "engines" / "synthesis-engine" / "src",
    ROOT / "engines" / "specialist-engine" / "src",
]

for src_dir in SRC_DIRS:
    sys.path.insert(0, str(src_dir))


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session: pytest.Session, exitstatus: int):
    """Ignore environment-specific tmp cleanup failures from the gate basetemp."""

    outcome = yield
    try:
        outcome.get_result()
    except PermissionError as exc:
        warnings.warn(
            pytest.PytestWarning(
                "Ignoring pytest basetemp cleanup permission error in this "
                f"environment: {exc}"
            )
        )
        outcome.force_result(None)
