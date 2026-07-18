"""Regenerate deterministic JARVIS console reference and completion assets."""

from __future__ import annotations

from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.cli import build_parser
from apps.jarvis_console.reference import (
    render_command_reference,
    render_shell_completion,
)
from apps.jarvis_console.registry import COMMAND_REGISTRY

REFERENCE_PATH = ROOT / "docs" / "operations" / "jarvis-console-command-reference.md"
COMPLETION_PATHS = {
    "powershell": ROOT / "tools" / "completions" / "jarvis-console.ps1",
    "bash": ROOT / "tools" / "completions" / "jarvis-console.bash",
    "zsh": ROOT / "tools" / "completions" / "_jarvis-console",
}


def generate_cli_assets() -> dict[Path, str]:
    """Return every deterministic asset without touching the filesystem."""

    parser = build_parser()
    assets = {
        REFERENCE_PATH: render_command_reference(COMMAND_REGISTRY, parser),
    }
    assets.update(
        {
            path: render_shell_completion(
                COMMAND_REGISTRY,
                parser,
                shell=shell,
            )
            for shell, path in COMPLETION_PATHS.items()
        }
    )
    return assets


def write_cli_assets() -> list[Path]:
    """Write generated assets to their versioned repository locations."""

    written: list[Path] = []
    for path, content in generate_cli_assets().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main() -> int:
    for path in write_cli_assets():
        print(path.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
