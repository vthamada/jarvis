"""Render scenario specs for the governed benchmark execution cut."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "tools" / "benchmarks" / "datasets" / "v2_governed_benchmark_scenarios.json"
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-governed-benchmark-scenario-specs.md"


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8"))


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    scenarios = dataset["scenarios"]
    return {
        "cut_id": dataset["cut_id"],
        "sprint_id": dataset["sprint_id"],
        "scenario_count": len(scenarios),
        "technology_ids": [scenario["technology_id"] for scenario in scenarios],
        "scenarios": scenarios,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Governed Benchmark Scenario Specs",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- scenario_count: `{payload['scenario_count']}`",
        "",
    ]
    for scenario in payload["scenarios"]:
        lines.extend(
            [
                f"## {scenario['display_name']}",
                "",
                f"- scenario_id: `{scenario['scenario_id']}`",
                f"- scenario_title: {scenario['scenario_title']}",
                f"- goal: {scenario['goal']}",
                "- minimal_execution_shape:",
            ]
        )
        for item in scenario["minimal_execution_shape"]:
            lines.append(f"  - {item}")
        lines.append("- success_signals:")
        for item in scenario["success_signals"]:
            lines.append(f"  - {item}")
        lines.append("- failure_signals:")
        for item in scenario["failure_signals"]:
            lines.append(f"  - {item}")
        lines.append("- evidence_required:")
        for item in scenario["evidence_required"]:
            lines.append(f"  - `{item}`")
        lines.append("- sandbox_boundaries:")
        for item in scenario["sandbox_boundaries"]:
            lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(f"rendered={OUTPUT_PATH.relative_to(ROOT)} scenarios={payload['scenario_count']}")


if __name__ == "__main__":
    main()
