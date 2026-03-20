"""Compare the baseline orchestrator flow with the optional LangGraph POC."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from json import dumps
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))

from tools.internal_pilot_support import (
    PilotExecutionResult,
    result_to_dict,
    run_pilot_scenarios,
    runtime_dir,
)


@dataclass(frozen=True)
class PathComparisonResult:
    """Comparison for a single scenario across baseline and LangGraph POC paths."""

    scenario_id: str
    mismatch_fields: list[str]
    baseline: PilotExecutionResult
    candidate: PilotExecutionResult | None

    @property
    def core_match(self) -> bool:
        return not self.mismatch_fields and self.candidate is not None


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Compare baseline and LangGraph orchestrator paths.")
    parser.add_argument(
        "--profile",
        choices=["development", "controlled"],
        default="development",
        help="Operational profile used for the comparison.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for comparison artifacts.",
    )
    return parser.parse_args()


def compare_results(
    baseline_results: list[PilotExecutionResult],
    candidate_results: list[PilotExecutionResult] | None,
) -> list[PathComparisonResult]:
    candidate_index = {
        result.scenario_id: result for result in (candidate_results or [])
    }
    comparisons: list[PathComparisonResult] = []
    for baseline in baseline_results:
        candidate = candidate_index.get(baseline.scenario_id)
        mismatch_fields: list[str] = []
        if candidate is None:
            mismatch_fields.append("candidate_unavailable")
        else:
            if baseline.intent != candidate.intent:
                mismatch_fields.append("intent")
            if baseline.governance_decision != candidate.governance_decision:
                mismatch_fields.append("governance_decision")
            if baseline.operation_status != candidate.operation_status:
                mismatch_fields.append("operation_status")
            if baseline.trace_status != candidate.trace_status:
                mismatch_fields.append("trace_status")
            if baseline.missing_required_events != candidate.missing_required_events:
                mismatch_fields.append("missing_required_events")
            if baseline.anomaly_flags != candidate.anomaly_flags:
                mismatch_fields.append("anomaly_flags")
        comparisons.append(
            PathComparisonResult(
                scenario_id=baseline.scenario_id,
                mismatch_fields=mismatch_fields,
                baseline=baseline,
                candidate=candidate,
            )
        )
    return comparisons


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"profile={payload['profile']}",
        f"overall_verdict={payload['overall_verdict']}",
        f"langgraph_status={payload['langgraph_status']}",
    ]
    for item in payload["scenario_results"]:
        lines.append(
            " ".join(
                [
                    f"scenario_id={item['scenario_id']}",
                    f"core_match={item['core_match']}",
                    f"mismatch_fields={','.join(item['mismatch_fields']) or 'none'}",
                    f"baseline_decision={item['baseline']['governance_decision']}",
                    "candidate_decision="
                    f"{item['candidate']['governance_decision'] if item['candidate'] else 'n/a'}",
                ]
            )
        )
    return "\n".join(lines)


def resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir is None:
        return runtime_dir("pilot-compare")
    target = Path(output_dir)
    return target if target.is_absolute() else ROOT / target


def serialize_comparisons(
    comparisons: list[PathComparisonResult],
    *,
    profile: str,
    langgraph_status: str,
) -> dict[str, object]:
    overall_verdict = (
        "langgraph_unavailable"
        if langgraph_status != "available"
        else ("equivalent" if all(item.core_match for item in comparisons) else "divergent")
    )
    return {
        "profile": profile,
        "langgraph_status": langgraph_status,
        "overall_verdict": overall_verdict,
        "scenario_results": [
            {
                "scenario_id": item.scenario_id,
                "core_match": item.core_match,
                "mismatch_fields": item.mismatch_fields,
                "baseline": result_to_dict(item.baseline),
                "candidate": result_to_dict(item.candidate) if item.candidate else None,
            }
            for item in comparisons
        ],
    }


def main() -> None:
    args = parse_args()
    target_dir = resolve_output_dir(args.output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    baseline_results = run_pilot_scenarios(
        profile=args.profile,
        workdir=target_dir / "baseline",
        path_name="baseline",
        use_langgraph_poc=False,
    )

    candidate_results: list[PilotExecutionResult] | None = None
    langgraph_status = "available"
    try:
        candidate_results = run_pilot_scenarios(
            profile=args.profile,
            workdir=target_dir / "langgraph",
            path_name="langgraph",
            use_langgraph_poc=True,
        )
    except RuntimeError as exc:
        if "LangGraph is not installed" not in str(exc):
            raise
        langgraph_status = "not_installed"

    comparisons = compare_results(baseline_results, candidate_results)
    payload = serialize_comparisons(
        comparisons,
        profile=args.profile,
        langgraph_status=langgraph_status,
    )
    (target_dir / "path_comparison.json").write_text(
        dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "path_comparison.md").write_text(render_text(payload), encoding="utf-8")
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
