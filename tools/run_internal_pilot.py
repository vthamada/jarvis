"""Execute the minimum internal pilot scenario pack for the JARVIS v1."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from json import dumps
from pathlib import Path
from sys import path as sys_path
from time import time

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))

from tools.internal_pilot_support import result_to_dict, run_pilot_scenarios, runtime_dir


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run the JARVIS internal pilot scenario pack.")
    parser.add_argument(
        "--profile",
        choices=["development", "controlled"],
        default="development",
        help="Operational profile used for the pilot run.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for pilot evidence artifacts.",
    )
    return parser.parse_args()


def render_text(payload: dict[str, object]) -> str:
    run_id = payload["run_id"]
    profile = payload["profile"]
    overall_status = payload["overall_status"]
    lines = [f"run_id={run_id} profile={profile} overall_status={overall_status}"]
    for item in payload["results"]:
        lines.append(
            " ".join(
                [
                    f"scenario_id={item['scenario_id']}",
                    f"path={item['path_name']}",
                    f"decision={item['governance_decision']}",
                    f"operation_status={item['operation_status'] or 'none'}",
                    f"trace_status={item['trace_status']}",
                    "missing_required_events="
                    f"{','.join(item['missing_required_events']) or 'none'}",
                    f"anomaly_flags={','.join(item['anomaly_flags']) or 'none'}",
                    f"duration_seconds={item['duration_seconds']}",
                ]
            )
        )
    return "\n".join(lines)


def resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir is None:
        return runtime_dir("pilot-run")
    target = Path(output_dir)
    return target if target.is_absolute() else ROOT / target


def main() -> None:
    args = parse_args()
    target_dir = resolve_output_dir(args.output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    started_at = int(time())
    results = run_pilot_scenarios(profile=args.profile, workdir=target_dir)
    overall_status = (
        "attention_required"
        if any(
            result.anomaly_flags
            or (
                result.governance_decision != "block"
                and result.missing_required_events
            )
            for result in results
        )
        else "healthy"
    )
    payload = {
        "run_id": f"pilot-{started_at}",
        "profile": args.profile,
        "overall_status": overall_status,
        "results": [result_to_dict(result) for result in results],
    }
    (target_dir / "pilot_results.json").write_text(
        dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "pilot_results.md").write_text(render_text(payload), encoding="utf-8")
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
