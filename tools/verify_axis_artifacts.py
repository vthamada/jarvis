"""Verify minimum axis-adherence artifacts for release-grade promotion."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = (
    ROOT / "HANDOFF.md",
    ROOT / "README.md",
    ROOT / "docs" / "executive" / "master-summary.md",
    ROOT / "docs" / "documentation" / "matriz-de-aderencia-mestre.md",
    ROOT / "docs" / "archive" / "implementation" / "v2-sovereign-alignment-cut.md",
    ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-domain-consumers-and-workflows-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-governed-benchmark-decisions.md",
    ROOT / "docs" / "implementation" / "v2-governed-benchmark-execution-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-memory-gap-evidence-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-native-memory-scope-hardening-cut.md",
    ROOT / "docs" / "implementation" / "v2-memory-gap-evidence-protocol.md",
    ROOT / "docs" / "implementation" / "v2-memory-gap-baseline-evidence.md",
    ROOT / "docs" / "implementation" / "v2-memory-gap-decision.md",
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
    sovereign_cut_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-sovereign-alignment-cut.md"
    )
    sovereign_cut_closure = _read(
        ROOT / "docs" / "implementation" / "v2-sovereign-alignment-cut-closure.md"
    )
    domain_workflows_closure = _read(
        ROOT / "docs" / "implementation" / "v2-domain-consumers-and-workflows-cut-closure.md"
    )
    benchmark_decisions_doc = _read(
        ROOT / "docs" / "implementation" / "v2-governed-benchmark-decisions.md"
    )
    benchmark_cut_closure = _read(
        ROOT / "docs" / "implementation" / "v2-governed-benchmark-execution-cut-closure.md"
    )
    memory_gap_cut_closure = _read(
        ROOT / "docs" / "implementation" / "v2-memory-gap-evidence-cut-closure.md"
    )
    active_cut_doc = _read(
        ROOT / "docs" / "implementation" / "v2-native-memory-scope-hardening-cut.md"
    )
    protocol_doc = _read(
        ROOT / "docs" / "implementation" / "v2-memory-gap-evidence-protocol.md"
    )
    baseline_evidence_doc = _read(
        ROOT / "docs" / "implementation" / "v2-memory-gap-baseline-evidence.md"
    )
    decision_doc = _read(
        ROOT / "docs" / "implementation" / "v2-memory-gap-decision.md"
    )

    _ensure(
        "docs/implementation/v2-native-memory-scope-hardening-cut.md" in handoff,
        "HANDOFF.md does not point to the current native memory scope hardening cut.",
    )
    _ensure(
        "v2-native-memory-scope-hardening-cut" in readme,
        "README.md does not name the current native memory scope hardening cut.",
    )
    _ensure(
        "v2-native-memory-scope-hardening-cut" in master_summary,
        "master-summary.md does not name the current native memory scope hardening cut.",
    )
    governed_execution_marker = (
        "docs/implementation/v2-governed-benchmark-execution-cut.md` como execucao oficial "
        "do corte ativo"
    )
    governed_execution_active = governed_execution_marker in handoff
    _ensure(
        not governed_execution_active,
        (
            "HANDOFF.md still treats the governed benchmark execution cut as the active "
            "execution document."
        ),
    )
    _ensure(
        "v2-alignment-cycle` como execucao oficial" not in handoff,
        "HANDOFF.md still treats v2-alignment-cycle as the active execution document.",
    )
    _ensure(
        "v2-sovereign-alignment-cut.md` como execucao oficial do corte ativo" not in handoff,
        "HANDOFF.md still treats the sovereign cut as the active execution document.",
    )
    _ensure(
        "Sprint 6 conclu" in sovereign_cut_doc,
        "The sovereign cut document does not reflect the completed sprint status.",
    )
    _ensure(
        "tools/close_sovereign_alignment_cut.py" in sovereign_cut_closure,
        "The sovereign cut closure document is missing its regenerable closure tool.",
    )
    _ensure(
        "tools/close_domain_consumers_and_workflows_cut.py" in domain_workflows_closure,
        "The domain consumers/workflows closure document is missing its regenerable closure tool.",
    )
    _ensure(
        "V2 Governed Benchmark Decisions" in benchmark_decisions_doc,
        "The governed benchmark decisions document is missing its rendered decision set.",
    )
    _ensure(
        "complete_v2_governed_benchmark_execution_cut" in benchmark_cut_closure,
        "The governed benchmark execution cut closure is missing its formal completion decision.",
    )
    _ensure(
        "V2 Memory Gap Evidence Protocol" in protocol_doc,
        "The memory gap evidence protocol document is missing its rendered protocol.",
    )
    _ensure(
        "V2 Memory Gap Baseline Evidence" in baseline_evidence_doc,
        "The memory gap baseline evidence document is missing its rendered evidence set.",
    )
    _ensure(
        "V2 Memory Gap Decision" in decision_doc,
        "The memory gap decision document is missing its rendered decision set.",
    )
    _ensure(
        "complete_v2_memory_gap_evidence_cut" in memory_gap_cut_closure,
        "The memory gap evidence cut closure is missing its formal completion decision.",
    )
    _ensure(
        "tools/engineering_gate.py --mode release" in active_cut_doc,
        "The current v2 cut document does not anchor release-grade gating.",
    )
    sprint_1_open = (
        "### Sprint 1. User scope hardening" in active_cut_doc
        and "- aberta." in active_cut_doc
    )
    _ensure(
        sprint_1_open,
        "The current native memory scope hardening cut does not reflect the opened Sprint 1 state.",
    )

    print("[verify-axis-artifacts] all minimum axis artifacts are coherent")


if __name__ == "__main__":
    main()
