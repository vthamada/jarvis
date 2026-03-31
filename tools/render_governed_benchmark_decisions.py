"""Render formal technology decisions for the governed benchmark execution cut."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "tools" / "benchmarks" / "datasets" / "v2_governed_benchmark_decisions.json"
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-governed-benchmark-decisions.md"


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8"))


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    decisions = dataset["decisions"]
    return {
        "cut_id": dataset["cut_id"],
        "sprint_id": dataset["sprint_id"],
        "decision_count": len(decisions),
        "technology_ids": [decision["technology_id"] for decision in decisions],
        "decisions": decisions,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Governed Benchmark Decisions",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- decision_count: `{payload['decision_count']}`",
        "",
    ]
    for decision in payload["decisions"]:
        lines.extend(
            [
                f"## {decision['display_name']}",
                "",
                f"- technology_id: `{decision['technology_id']}`",
                f"- family_id: `{decision['family_id']}`",
                f"- final_decision: `{decision['final_decision']}`",
                f"- baseline_read: {decision['baseline_read']}",
                "- decision_rationale:",
            ]
        )
        for item in decision["decision_rationale"]:
            lines.append(f"  - {item}")
        lines.append("- recommended_entry_surface:")
        for item in decision["recommended_entry_surface"]:
            lines.append(f"  - `{item}`")
        lines.append("- reopen_signals:")
        for item in decision["reopen_signals"]:
            lines.append(f"  - {item}")
        lines.append("- blocked_now_by:")
        for item in decision["blocked_now_by"]:
            lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(f"rendered={OUTPUT_PATH.relative_to(ROOT)} decisions={payload['decision_count']}")


if __name__ == "__main__":
    main()
