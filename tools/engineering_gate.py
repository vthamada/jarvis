"""Official engineering gate for the JARVIS repository."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from os import environ
from pathlib import Path
from subprocess import run
from sys import executable
from tempfile import gettempdir
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
PROJECT_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
RUNNER = str(PROJECT_PYTHON) if PROJECT_PYTHON.exists() else executable


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
    parser.add_argument(
        "--temp-root",
        type=Path,
        metavar="ABSOLUTE_DIRECTORY",
        help="Existing parent outside the repository for fresh gate temporary files.",
    )
    return parser.parse_args()


def _temporary_parent(parent: Path) -> Path:
    message = "Gate temporary parent must be an existing absolute directory outside the repository."
    if not isinstance(parent, Path) or not parent.is_absolute():
        raise ValueError(message)
    try:
        resolved = parent.resolve(strict=True)
        if not resolved.is_dir() or resolved.is_relative_to(ROOT.resolve()):
            raise ValueError(message)
    except OSError:
        raise ValueError(message) from None
    return resolved


def _new_temp_root(parent: Path | None = None) -> Path:
    # Private-runtime tests deliberately reject any location inside ROOT. An
    # explicit private parent supports sandboxes with an inaccessible system TEMP.
    # Keep the external run name outside scanners' .tmp_/.pytest_/.audit_
    # exclusions: their iterators inspect every absolute ancestor of a fixture.
    selected = _temporary_parent(parent if parent is not None else Path(gettempdir()))
    return selected / f"jarvis-engineering-gate-{uuid4().hex}"


def build_gate_steps(
    *, mode: str, include_controlled: bool, temp_root: Path | None = None,
) -> list[GateStep]:
    """Describe checks without creating or removing any temporary directory."""
    steps = [
        GateStep(
            label="mojibake check",
            command=[RUNNER, "tools/check_mojibake.py", "."],
        ),
        GateStep(
            label="document guardrails",
            command=[RUNNER, "tools/verify_document_guardrails.py"],
        ),
        GateStep(
            label="ruff",
            command=[RUNNER, "-m", "ruff", "check", "."],
        ),
    ]

    if mode in {"standard", "release"}:
        pytest_basetemp = (temp_root if temp_root is not None else _new_temp_root()) / "pytest"
        steps.append(
            GateStep(
                label="pytest",
                command=[
                    RUNNER,
                    "-m",
                    "pytest",
                    "-q",
                    "--basetemp",
                    str(pytest_basetemp),
                    "--junitxml",
                    str(pytest_basetemp.parent / "pytest-results.xml"),
                ],
            )
        )

    if mode == "release":
        steps.append(
            GateStep(
                label="axis artifact verification",
                command=[RUNNER, "tools/verify_axis_artifacts.py"],
            )
        )
        steps.append(
            GateStep(
                label="release signal baseline verification",
                command=[RUNNER, "tools/verify_release_signal_baseline.py"],
            )
        )
        steps.append(
            GateStep(
                label="active cut baseline verification",
                # Module execution finds shared sources without an editable install.
                command=[RUNNER, "-m", "tools.verify_active_cut_baseline"],
            )
        )
        steps.append(
            GateStep(
                label="current cut closure verification",
                command=[
                    RUNNER,
                    "tools/close_repository_hygiene_and_tools_review_cut.py",
                    "--check",
                ],
            )
        )
        steps.append(
            GateStep(
                label="baseline validation development",
                command=[
                    RUNNER,
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
                        RUNNER,
                        "tools/validate_baseline.py",
                        "--profile",
                        "controlled",
                    ],
                )
            )

    return steps


def _validate_pytest_environment() -> None:
    if environ.get("PYTEST_ADDOPTS", "").strip():
        raise RuntimeError(
            "Unset PYTEST_ADDOPTS before running the standard/release gate; "
            "inherited options can change test selection or verification."
        )


def run_step(step: GateStep, *, temp_root: Path | None = None) -> None:
    if step.label == "pytest":
        _validate_pytest_environment()
    child_env = None
    if temp_root is not None:
        child_env = dict(environ)
        child_env.update({name: str(temp_root) for name in ("TEMP", "TMP", "TMPDIR")})
    result = run(step.command, check=False, env=child_env)
    if result.returncode != 0:
        raise RuntimeError(
            f"Engineering gate failed during '{step.label}' "
            f"with exit code {result.returncode}."
        )


def main() -> None:
    args = parse_args()
    selected_parent = getattr(args, "temp_root", None)
    if selected_parent is not None:
        selected_parent = _temporary_parent(selected_parent)
    temp_root = None
    if args.mode in {"standard", "release"}:
        _validate_pytest_environment()
        temp_root = _new_temp_root(selected_parent)
        # Only a fresh UUID-scoped child is owned by this invocation. Never
        # clear an existing path or remove its parent; retain failure artifacts.
        temp_root.mkdir(exist_ok=False)
        print(f"[engineering-gate] temporary files: {temp_root}")
    steps = build_gate_steps(
        mode=args.mode,
        include_controlled=args.include_controlled,
        temp_root=temp_root,
    )
    for step in steps:
        print(f"[engineering-gate] running: {step.label}")
        run_step(step, temp_root=temp_root)
    print("[engineering-gate] all checks passed")


if __name__ == "__main__":
    main()
