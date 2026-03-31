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
    ROOT / "docs" / "archive" / "implementation" / "v2-sovereign-alignment-cut-closure.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-domain-consumers-and-workflows-cut-closure.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-governed-benchmark-decisions.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-governed-benchmark-execution-cut-closure.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-memory-gap-evidence-cut-closure.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-native-memory-scope-hardening-cut.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-memory-gap-evidence-protocol.md",
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-memory-gap-baseline-evidence.md",
    ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-decision.md",
    ROOT / "docs" / "implementation" / "v2-native-memory-scope-hardening-cut-closure.md",
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-and-tools-review-cut.md",
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-inventory.md",
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-doc-decisions.md",
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-tool-decisions.md",
    ROOT / "docs" / "implementation" / "v2-repository-hygiene-and-tools-review-cut-closure.md",
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
        ROOT / "docs" / "archive" / "implementation" / "v2-sovereign-alignment-cut-closure.md"
    )
    domain_workflows_closure = _read(
        ROOT
        / "docs"
        / "archive"
        / "implementation"
        / "v2-domain-consumers-and-workflows-cut-closure.md"
    )
    benchmark_decisions_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-governed-benchmark-decisions.md"
    )
    benchmark_cut_closure = _read(
        ROOT
        / "docs"
        / "archive"
        / "implementation"
        / "v2-governed-benchmark-execution-cut-closure.md"
    )
    memory_gap_cut_closure = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-evidence-cut-closure.md"
    )
    native_memory_cut_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-native-memory-scope-hardening-cut.md"
    )
    native_memory_cut_closure = _read(
        ROOT / "docs" / "implementation" / "v2-native-memory-scope-hardening-cut-closure.md"
    )
    repository_hygiene_cut_doc = _read(
        ROOT / "docs" / "implementation" / "v2-repository-hygiene-and-tools-review-cut.md"
    )
    repository_hygiene_inventory_doc = _read(
        ROOT / "docs" / "implementation" / "v2-repository-hygiene-inventory.md"
    )
    repository_hygiene_doc_decisions = _read(
        ROOT / "docs" / "implementation" / "v2-repository-hygiene-doc-decisions.md"
    )
    repository_hygiene_tool_decisions = _read(
        ROOT / "docs" / "implementation" / "v2-repository-hygiene-tool-decisions.md"
    )
    repository_hygiene_cut_closure = _read(
        ROOT
        / "docs"
        / "implementation"
        / "v2-repository-hygiene-and-tools-review-cut-closure.md"
    )
    protocol_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-evidence-protocol.md"
    )
    baseline_evidence_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-baseline-evidence.md"
    )
    decision_doc = _read(
        ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-decision.md"
    )

    _ensure(
        "v2-repository-hygiene-and-tools-review-cut" in handoff,
        "HANDOFF.md does not reference the repository hygiene cut.",
    )
    _ensure(
        "v2-repository-hygiene-and-tools-review-cut-closure.md" in handoff,
        "HANDOFF.md does not reference the repository hygiene cut closure.",
    )
    _ensure(
        "v2-repository-hygiene-and-tools-review-cut" in readme,
        "README.md does not name the repository hygiene cut.",
    )
    _ensure(
        "v2-repository-hygiene-and-tools-review-cut-closure.md" in readme,
        "README.md does not reference the repository hygiene cut closure.",
    )
    _ensure(
        "v2-repository-hygiene-and-tools-review-cut" in master_summary,
        "master-summary.md does not name the repository hygiene cut.",
    )
    _ensure(
        "v2-repository-hygiene-and-tools-review-cut-closure.md" in master_summary,
        "master-summary.md does not reference the repository hygiene cut closure.",
    )
    _ensure(
        "Sprint 6 conclu" in sovereign_cut_doc,
        "The sovereign cut document does not reflect the completed sprint status.",
    )
    _ensure(
        "tools/archive/close_sovereign_alignment_cut.py" in sovereign_cut_closure,
        "The sovereign cut closure document is missing its archived closure tool reference.",
    )
    _ensure(
        "tools/archive/close_domain_consumers_and_workflows_cut.py" in domain_workflows_closure,
        "The domain consumers/workflows closure document is missing its "
        "archived closure tool reference.",
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
    native_memory_sprint_4_closed = (
        "### Sprint 4. Cut closure" in native_memory_cut_doc
        and "- concluida." in native_memory_cut_doc
    )
    _ensure(
        native_memory_sprint_4_closed,
        "The archived native memory cut document does not reflect the concluded Sprint 4 state.",
    )
    _ensure(
        "complete_v2_native_memory_scope_hardening_cut" in native_memory_cut_closure,
        "The native memory cut closure is missing its formal completion decision.",
    )
    repository_hygiene_sprint_4_closed = (
        "### Sprint 4. Cleanup and closure" in repository_hygiene_cut_doc
        and "- concluida." in repository_hygiene_cut_doc
    )
    _ensure(
        repository_hygiene_sprint_4_closed,
        "The repository hygiene cut document does not reflect the concluded Sprint 4 state.",
    )
    _ensure(
        "V2 Repository Hygiene Inventory" in repository_hygiene_inventory_doc,
        "The repository hygiene inventory document is missing its rendered inventory.",
    )
    _ensure(
        "V2 Repository Hygiene Doc Decisions" in repository_hygiene_doc_decisions,
        "The repository hygiene doc decisions document is missing its rendered classification.",
    )
    _ensure(
        "V2 Repository Hygiene Tool Decisions" in repository_hygiene_tool_decisions,
        "The repository hygiene tool decisions document is missing its rendered classification.",
    )
    _ensure(
        "complete_v2_repository_hygiene_and_tools_review_cut" in repository_hygiene_cut_closure,
        "The repository hygiene cut closure is missing its formal completion decision.",
    )

    print("[verify-axis-artifacts] all minimum axis artifacts are coherent")


if __name__ == "__main__":
    main()
