"""Verify minimum axis-adherence artifacts for release-grade promotion."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = (
    ROOT / "HANDOFF.md",
    ROOT / "README.md",
    ROOT / "docs" / "executive" / "master-summary.md",
    ROOT / "docs" / "documentation" / "matriz-de-aderencia-mestre.md",
    ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut.md",
    ROOT / "knowledge" / "curated" / "domain_registry.json",
    ROOT / "shared" / "mind_registry.py",
    ROOT / "shared" / "memory_registry.py",
)


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _read(path: Path) -> str:
    _ensure(path.exists(), f"Required artifact missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    for required in REQUIRED_FILES:
        _ensure(required.exists(), f"Required artifact missing: {required.relative_to(ROOT)}")

    handoff = _read(ROOT / "HANDOFF.md")
    readme = _read(ROOT / "README.md")
    master_summary = _read(ROOT / "docs" / "executive" / "master-summary.md")
    cut_doc = _read(ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut.md")

    _ensure(
        "docs/implementation/v2-sovereign-alignment-cut.md" in handoff,
        "HANDOFF.md does not point to the active v2 sovereign alignment cut.",
    )
    _ensure(
        "v2-sovereign-alignment-cut" in readme,
        "README.md does not name the active v2 sovereign alignment cut.",
    )
    _ensure(
        "v2-sovereign-alignment-cut" in master_summary,
        "master-summary.md does not name the active v2 sovereign alignment cut.",
    )
    _ensure(
        "v2-alignment-cycle` como execução oficial" not in handoff,
        "HANDOFF.md still treats v2-alignment-cycle as the active execution document.",
    )
    _ensure(
        "fonte oficial do que entra em execução agora" in cut_doc,
        "The active v2 cut document is missing its execution-source declaration.",
    )

    print("[verify-axis-artifacts] all minimum axis artifacts are coherent")


if __name__ == "__main__":
    main()
