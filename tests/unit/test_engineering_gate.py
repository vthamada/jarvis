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
