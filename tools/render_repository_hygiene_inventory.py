"""Render a regenerable inventory for repository hygiene review."""

from __future__ import annotations

from json import dumps
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / ".jarvis_runtime" / "v2_repository_hygiene_and_tools_review_cut"
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-repository-hygiene-inventory.md"
ACTIVE_CUT_DOC = "v2-repository-hygiene-and-tools-review-cut.md"
FOUNDATIONAL_DOCS = {"implementation-strategy.md", "service-breakdown.md"}
BASELINE_VALIDATION_TOOLS = {
    "check_mojibake.py",
    "engineering_gate.py",
    "fix_mojibake.py",
    "go_live_internal_checklist.py",
    "validate_baseline.py",
    "verify_active_cut_baseline.py",
    "verify_axis_artifacts.py",
}
OPERATIONAL_EVIDENCE_TOOLS = {
    "compare_orchestrator_paths.py",
    "evolution_from_pilot.py",
    "internal_pilot_report.py",
    "internal_pilot_support.py",
    "operational_artifacts.py",
    "run_internal_pilot.py",
}


def _sorted_file_names(path: Path) -> list[str]:
    return sorted(item.name for item in path.iterdir() if item.is_file())


def build_payload() -> dict[str, object]:
    implementation_files = _sorted_file_names(ROOT / "docs" / "implementation")
    archive_implementation_files = _sorted_file_names(
        ROOT / "docs" / "archive" / "implementation"
    )
    tool_files = [
        name
        for name in _sorted_file_names(ROOT / "tools")
        if name not in {"README.md", "__init__.py"}
    ]
    archived_tool_files = [
        name
        for name in _sorted_file_names(ROOT / "tools" / "archive")
        if name != "__init__.py"
    ]
    closure_docs = [name for name in implementation_files if name.endswith("-closure.md")]
    closure_tools = sorted(name for name in tool_files if name.startswith("close_"))
    render_tools = sorted(name for name in tool_files if name.startswith("render_"))
    baseline_validation_tools = sorted(
        name for name in tool_files if name in BASELINE_VALIDATION_TOOLS
    )
    operational_evidence_tools = sorted(
        name for name in tool_files if name in OPERATIONAL_EVIDENCE_TOOLS
    )
    supporting_docs = sorted(
        name
        for name in implementation_files
        if name not in FOUNDATIONAL_DOCS
        and name != ACTIVE_CUT_DOC
        and name not in closure_docs
    )
    uncategorized_tools = sorted(
        name
        for name in tool_files
        if name
        not in set(baseline_validation_tools)
        | set(operational_evidence_tools)
        | set(closure_tools)
        | set(render_tools)
    )
    return {
        "cut_id": "v2-repository-hygiene-and-tools-review-cut",
        "sprint_id": "sprint-1-regenerable-inventory",
        "active_cut_doc": ACTIVE_CUT_DOC,
        "summary": {
            "implementation_docs": len(implementation_files),
            "implementation_closures": len(closure_docs),
            "supporting_implementation_docs": len(supporting_docs),
            "archived_implementation_docs": len(archive_implementation_files),
            "tool_scripts": len(tool_files),
            "archived_tool_scripts": len(archived_tool_files),
            "baseline_validation_tools": len(baseline_validation_tools),
            "operational_evidence_tools": len(operational_evidence_tools),
            "render_tools": len(render_tools),
            "closure_tools": len(closure_tools),
            "uncategorized_tools": len(uncategorized_tools),
        },
        "implementation_docs": {
            "active_execution": [ACTIVE_CUT_DOC],
            "foundational_support": sorted(FOUNDATIONAL_DOCS),
            "supporting_artifacts": supporting_docs,
            "closure_docs": closure_docs,
            "archived_history": archive_implementation_files,
        },
        "tool_inventory": {
            "baseline_validation": baseline_validation_tools,
            "operational_evidence": operational_evidence_tools,
            "render_artifacts": render_tools,
            "active_cut_closures": closure_tools,
            "archived_history": archived_tool_files,
            "uncategorized": uncategorized_tools,
        },
        "guardrails": [
            (
                "o inventario continua regeneravel mesmo apos a limpeza, "
                "para impedir que a superficie ativa volte a crescer sem "
                "rastreabilidade"
            ),
            (
                "arquivos exigidos por engineering_gate ou "
                "verify_axis_artifacts permanecem fora de delete candidate "
                "sem substituto"
            ),
            (
                "tools/archive e docs/archive preservam historico regeneravel "
                "sem poluir a area principal"
            ),
        ],
        "next_step": (
            "usar este inventario em conjunto com as decisoes e o closure do "
            "recorte para manter a superficie ativa enxuta antes da abertura "
            "do proximo corte funcional"
        ),
    }


def render_markdown(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    implementation_docs = payload["implementation_docs"]
    tool_inventory = payload["tool_inventory"]
    lines = [
        "# V2 Repository Hygiene Inventory",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- active_cut_doc: `{payload['active_cut_doc']}`",
        "",
        "## Summary",
        "",
        f"- implementation_docs: `{summary['implementation_docs']}`",
        f"- implementation_closures: `{summary['implementation_closures']}`",
        (
            "- supporting_implementation_docs: "
            f"`{summary['supporting_implementation_docs']}`"
        ),
        (
            "- archived_implementation_docs: "
            f"`{summary['archived_implementation_docs']}`"
        ),
        f"- tool_scripts: `{summary['tool_scripts']}`",
        f"- archived_tool_scripts: `{summary['archived_tool_scripts']}`",
        f"- baseline_validation_tools: `{summary['baseline_validation_tools']}`",
        f"- operational_evidence_tools: `{summary['operational_evidence_tools']}`",
        f"- render_tools: `{summary['render_tools']}`",
        f"- closure_tools: `{summary['closure_tools']}`",
        f"- uncategorized_tools: `{summary['uncategorized_tools']}`",
        "",
        "## Implementation Docs",
        "",
    ]
    for label, items in implementation_docs.items():
        lines.append(f"### {label.replace('_', ' ').title()}")
        lines.append("")
        for item in items:
            lines.append(f"- `{item}`")
        lines.append("")
    lines.append("## Tool Inventory")
    lines.append("")
    for label, items in tool_inventory.items():
        lines.append(f"### {label.replace('_', ' ').title()}")
        lines.append("")
        for item in items:
            lines.append(f"- `{item}`")
        lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    for item in payload["guardrails"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Step", "", f"- {payload['next_step']}", ""])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "inventory.json").write_text(
        dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"rendered={OUTPUT_PATH.relative_to(ROOT)} "
        f"docs={payload['summary']['implementation_docs']} "
        f"tools={payload['summary']['tool_scripts']} "
        f"archived_tools={payload['summary']['archived_tool_scripts']}"
    )


if __name__ == "__main__":
    main()
