"""Render the execution plan for the governed benchmark sandbox cut."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_governed_benchmark_execution_profiles.json"
)
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-governed-benchmark-execution-plan.md"


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8"))


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    profiles = dataset["benchmark_now_profiles"]
    return {
        "cut_id": dataset["cut_id"],
        "source_matrix": dataset["source_matrix"],
        "benchmark_now_count": len(profiles),
        "technology_ids": [profile["technology_id"] for profile in profiles],
        "profiles": profiles,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Governed Benchmark Execution Plan",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- source_matrix: `{payload['source_matrix']}`",
        f"- benchmark_now_count: `{payload['benchmark_now_count']}`",
        "",
        "## Perfis de execucao",
        "",
    ]
    for profile in payload["profiles"]:
        lines.extend(
            [
                f"### {profile['display_name']}",
                "",
                f"- technology_id: `{profile['technology_id']}`",
                f"- family_id: `{profile['family_id']}`",
                f"- benchmark_goal: {profile['benchmark_goal']}",
                "- jarvis_baseline_surface:",
            ]
        )
        for surface in profile["jarvis_baseline_surface"]:
            lines.append(f"  - `{surface}`")
        lines.append("- evaluation_questions:")
        for question in profile["evaluation_questions"]:
            lines.append(f"  - {question}")
        lines.append("- expected_artifacts:")
        for artifact in profile["expected_artifacts"]:
            lines.append(f"  - `{artifact}`")
        lines.append("- target_decisions:")
        for decision in profile["target_decisions"]:
            lines.append(f"  - `{decision}`")
        lines.append("- blocked_absorption_conditions:")
        for blocker in profile["blocked_absorption_conditions"]:
            lines.append(f"  - {blocker}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(f"rendered={OUTPUT_PATH.relative_to(ROOT)} profiles={payload['benchmark_now_count']}")


if __name__ == "__main__":
    main()
