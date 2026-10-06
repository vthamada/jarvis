from pathlib import Path
from subprocess import run
from sys import executable

from tools.engineering_gate import build_gate_steps


def test_engineering_gate_quick_mode() -> None:
    steps = build_gate_steps(mode="quick", include_controlled=False)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
    ]


def test_engineering_gate_standard_mode() -> None:
    steps = build_gate_steps(mode="standard", include_controlled=False)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
        "pytest",
    ]
    assert "--basetemp" in steps[-1].command


def test_engineering_gate_release_mode_with_controlled() -> None:
    steps = build_gate_steps(mode="release", include_controlled=True)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
        "pytest",
        "axis artifact verification",
        "release signal baseline verification",
        "active cut baseline verification",
        "current cut closure verification",
        "baseline validation development",
        "baseline validation controlled",
    ]
    assert "--basetemp" in steps[3].command
    assert steps[7].command[-1] == "--check"


def test_release_active_cut_uses_source_module_without_editable_install() -> None:
    steps = build_gate_steps(mode="release", include_controlled=False)
    assert steps[6].command[1:] == ["-m", "tools.verify_active_cut_baseline"]
    # A fresh process without site initialization cannot rely on editable installs
    # or pytest's sys.path setup. Help must load the public CLI without writing.
    result = run(
        [executable, "-E", "-S", "-m", "tools.verify_active_cut_baseline", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--output-dir" in result.stdout
