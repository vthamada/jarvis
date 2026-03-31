"""Render the formal hold-or-reopen decision for the memory gap evidence cut."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATASET_PATH = ROOT / "tools" / "benchmarks" / "datasets" / "v2_memory_gap_decision.json"
OUTPUT_PATH = (
    ROOT / "docs" / "archive" / "implementation" / "v2-memory-gap-decision.md"
)


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8-sig"))


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    return {
        "cut_id": dataset["cut_id"],
        "sprint_id": dataset["sprint_id"],
        "decision_id": dataset["decision_id"],
        "final_decision": dataset["final_decision"],
        "mem0_status": dataset["mem0_status"],
        "baseline_read": dataset["baseline_read"],
        "decision_rationale": dataset["decision_rationale"],
        "backlog_before_any_absorption": dataset["backlog_before_any_absorption"],
        "reopen_signals": dataset["reopen_signals"],
        "blocked_now_by": dataset["blocked_now_by"],
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Memory Gap Decision",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- decision_id: `{payload['decision_id']}`",
        f"- final_decision: `{payload['final_decision']}`",
        f"- mem0_status: `{payload['mem0_status']}`",
        f"- baseline_read: {payload['baseline_read']}",
        "",
        "## Decision Rationale",
        "",
    ]
    for item in payload["decision_rationale"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Backlog Before Any Absorption", ""])
    for item in payload["backlog_before_any_absorption"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Reopen Signals", ""])
    for item in payload["reopen_signals"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Blocked Now By", ""])
    for item in payload["blocked_now_by"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(
        f"rendered={OUTPUT_PATH.relative_to(ROOT)} decision={payload['final_decision']}"
    )


if __name__ == "__main__":
    main()
