"""Render the protocol for proving or rejecting a memory gap in the current baseline."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_memory_gap_evidence_hypotheses.json"
)
OUTPUT_PATH = (
    ROOT
    / "docs"
    / "archive"
    / "implementation"
    / "v2-memory-gap-evidence-protocol.md"
)


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8"))


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    hypotheses = dataset["hypotheses"]
    return {
        "cut_id": dataset["cut_id"],
        "sprint_id": dataset["sprint_id"],
        "hypothesis_count": len(hypotheses),
        "hypotheses": hypotheses,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Memory Gap Evidence Protocol",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- hypothesis_count: `{payload['hypothesis_count']}`",
        "",
    ]
    for item in payload["hypotheses"]:
        lines.extend(
            [
                f"## {item['title']}",
                "",
                f"- hypothesis_id: `{item['hypothesis_id']}`",
                f"- why_it_matters: {item['why_it_matters']}",
                "- baseline_signals:",
            ]
        )
        for signal in item["baseline_signals"]:
            lines.append(f"  - {signal}")
        lines.append("- proof_signals:")
        for signal in item["proof_signals"]:
            lines.append(f"  - {signal}")
        lines.append("- hold_signals:")
        for signal in item["hold_signals"]:
            lines.append(f"  - {signal}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(f"rendered={OUTPUT_PATH.relative_to(ROOT)} hypotheses={payload['hypothesis_count']}")


if __name__ == "__main__":
    main()
