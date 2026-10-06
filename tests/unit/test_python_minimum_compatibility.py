"""Keep report tools parseable under the project's declared Python minimum."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "relative",
    [
        "tools/compare_orchestrator_paths.py",
        "tools/evolution_from_pilot.py",
        "tools/internal_pilot_report.py",
    ],
)
def test_report_tools_parse_with_python_311_grammar(relative):
    # This checks syntax, not complete runtime or optional-backend compatibility.
    ast.parse((ROOT / relative).read_text(encoding="utf-8"), feature_version=(3, 11))
