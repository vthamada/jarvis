"""Official engineering gate for the JARVIS repository."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from subprocess import run
from sys import executable


@dataclass(frozen=True)
class GateStep:
    """Single executable gate step."""

    label: str
    command: list[str]


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run the official JARVIS engineering gate.")
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "release"],
        default="standard",
        help="Gate strictness. 'release' includes baseline validation.",
    )
    parser.add_argument(
        "--include-controlled",
        action="store_true",
        help="Also run controlled-profile validation when using release mode.",
    )
    return parser.parse_args()


def build_gate_steps(*, mode: str, include_controlled: bool) -> list[GateStep]:
    steps = [
        GateStep(
            label="mojibake check",
            command=[executable, "tools/check_mojibake.py", "."],
        ),
        GateStep(
            label="ruff",
            command=[executable, "-m", "ruff", "check", "."],
        ),
    ]

    if mode in {"standard", "release"}:
        steps.append(
            GateStep(
                label="pytest",
                command=[executable, "-m", "pytest", "-q"],
            )
        )

    if mode == "release":
        steps.append(
            GateStep(
                label="baseline validation development",
                command=[
                    executable,
                    "tools/validate_baseline.py",
                    "--profile",
                    "development",
                ],
            )
        )
        if include_controlled:
            steps.append(
                GateStep(
                    label="baseline validation controlled",
                    command=[
                        executable,
                        "tools/validate_baseline.py",
                        "--profile",
                        "controlled",
                    ],
                )
            )

    return steps


def run_step(step: GateStep) -> None:
    result = run(step.command, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"Engineering gate failed during '{step.label}' "
            f"with exit code {result.returncode}."
        )


def main() -> None:
    args = parse_args()
    steps = build_gate_steps(
        mode=args.mode,
        include_controlled=args.include_controlled,
    )
    for step in steps:
        print(f"[engineering-gate] running: {step.label}")
        run_step(step)
    print("[engineering-gate] all checks passed")


if __name__ == "__main__":
    main()
