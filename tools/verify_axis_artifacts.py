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
    ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-domain-consumers-and-workflows-cut.md",
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
    sovereign_cut_doc = _read(ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut.md")
    closure_doc = _read(
        ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut-closure.md"
    )
    active_cut_doc = _read(
        ROOT / "docs" / "implementation" / "v2-domain-consumers-and-workflows-cut.md"
    )

    _ensure(
        "docs/implementation/v2-domain-consumers-and-workflows-cut.md" in handoff,
        "HANDOFF.md does not point to the active v2 domain consumers/workflows cut.",
    )
    _ensure(
        "v2-domain-consumers-and-workflows-cut" in readme,
        "README.md does not name the active v2 domain consumers/workflows cut.",
    )
    _ensure(
        "v2-domain-consumers-and-workflows-cut" in master_summary,
        "master-summary.md does not name the active v2 domain consumers/workflows cut.",
    )
    _ensure(
        "v2-alignment-cycle` como execução oficial" not in handoff,
        "HANDOFF.md still treats v2-alignment-cycle as the active execution document.",
    )
    _ensure(
        "v2-sovereign-alignment-cut.md` como execução oficial do corte ativo" not in handoff,
        "HANDOFF.md still treats the sovereign cut as the active execution document.",
    )
    _ensure(
        "Sprint 6 concluída" in sovereign_cut_doc,
        "The sovereign cut document does not reflect the completed sprint status.",
    )
    _ensure(
        "tools/close_sovereign_alignment_cut.py" in closure_doc,
        "The sovereign cut closure document is missing its regenerable closure tool.",
    )
    _ensure(
        "O que este corte assume como baseline obrigatorio:" in active_cut_doc,
        "The active v2 cut document is missing its baseline declaration.",
    )
    _ensure(
        "tools/engineering_gate.py --mode release" in active_cut_doc,
        "The active v2 cut document does not anchor release-grade gating.",
    )

    print("[verify-axis-artifacts] all minimum axis artifacts are coherent")


if __name__ == "__main__":
    main()