"""Promote internal pilot signals into sandbox-only evolution proposals."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict
from json import dumps, loads
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))

from evolution_lab.service import EvolutionLabService, FlowEvaluationInput
from observability_service.service import ObservabilityService


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Create sandbox evolution proposals from pilot traces.")
    parser.add_argument(
        "--observability-db",
        default=str(ROOT / ".jarvis_runtime" / "observability.db"),
        help="Path to the local observability database.",
    )
    parser.add_argument(
        "--evolution-db",
        default=str(ROOT / ".jarvis_runtime" / "evolution.db"),
        help="Path to the local evolution database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of recent requests to inspect.",
    )
    parser.add_argument(
        "--comparison-json",
        help="Optional comparison artifact from tools/compare_orchestrator_paths.py.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    return parser.parse_args()


def _evaluation_from_dict(payload: dict[str, object]) -> FlowEvaluationInput:
    return FlowEvaluationInput(
        request_id=str(payload["request_id"]),
        session_id=str(payload["session_id"]) if payload.get("session_id") else None,
        mission_id=str(payload["mission_id"]) if payload.get("mission_id") else None,
        governance_decision=(
            str(payload["governance_decision"])
            if payload.get("governance_decision") is not None
            else None
        ),
        operation_status=(
            str(payload["operation_status"])
            if payload.get("operation_status") is not None
            else None
        ),
        total_events=int(payload["total_events"]),
        duration_seconds=float(payload["duration_seconds"]),
        missing_required_events=list(payload.get("missing_required_events", [])),
        anomaly_flags=list(payload.get("anomaly_flags", [])),
        continuity_action=(
            str(payload["continuity_action"])
            if payload.get("continuity_action") is not None
            else None
        ),
        continuity_source=(
            str(payload["continuity_source"])
            if payload.get("continuity_source") is not None
            else None
        ),
        continuity_trace_status=(
            str(payload["continuity_trace_status"])
            if payload.get("continuity_trace_status") is not None
            else None
        ),
        missing_continuity_signals=list(payload.get("missing_continuity_signals", [])),
        continuity_anomaly_flags=list(payload.get("continuity_anomaly_flags", [])),
    )


def resolve_path(value: str) -> Path:
    target = Path(value)
    return target if target.is_absolute() else ROOT / target


def build_payload(args: Namespace) -> dict[str, object]:
    observability = ObservabilityService(database_path=str(resolve_path(args.observability_db)))
    evolution = EvolutionLabService(database_path=str(resolve_path(args.evolution_db)))
    audits = observability.summarize_recent_requests(limit=args.limit)
    proposals = []
    for audit in audits:
        if not audit.anomaly_flags and not audit.missing_required_events:
            continue
        proposal = evolution.create_proposal_from_flow_evaluation(
            FlowEvaluationInput(
                request_id=audit.request_id or "unknown",
                session_id=audit.session_id,
                mission_id=audit.mission_id,
                governance_decision=audit.governance_decision,
                operation_status=audit.operation_status,
                total_events=audit.total_events,
                duration_seconds=audit.duration_seconds,
                missing_required_events=audit.missing_required_events,
                anomaly_flags=audit.anomaly_flags,
                continuity_action=audit.continuity_action,
                continuity_source=audit.continuity_source,
                continuity_trace_status=audit.continuity_trace_status,
                missing_continuity_signals=audit.missing_continuity_signals,
                continuity_anomaly_flags=audit.continuity_anomaly_flags,
            ),
            target_scope="orchestrator-service",
        )
        proposals.append(asdict(proposal))

    comparisons = []
    if args.comparison_json:
        payload = loads(resolve_path(args.comparison_json).read_text(encoding="utf-8"))
        for item in payload.get("scenario_results", []):
            candidate = item.get("candidate")
            if candidate is None:
                continue
            baseline_eval = _evaluation_from_dict(item["baseline"])
            candidate_eval = _evaluation_from_dict(candidate)
            proposal = evolution.create_proposal_from_flow_evaluation(
                baseline_eval,
                target_scope="orchestrator-service",
                strategy_name="manual_variants",
            )
            comparison = evolution.compare_flow_evaluations(
                proposal,
                baseline_label=f"baseline:{item['scenario_id']}",
                candidate_label=f"langgraph:{item['scenario_id']}",
                baseline=baseline_eval,
                candidate=candidate_eval,
                governance_refs=["policy://sandbox/manual-review"],
                notes=[f"comparison_scenario={item['scenario_id']}"],
            )
            comparisons.append(
                {
                    "scenario_id": item["scenario_id"],
                    "proposal": asdict(comparison.proposal),
                    "decision": asdict(comparison.decision),
                    "metric_deltas": comparison.metric_deltas,
                }
            )

    return {
        "recent_trace_proposals": proposals,
        "comparison_decisions": comparisons,
    }


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"recent_trace_proposals={len(payload['recent_trace_proposals'])}",
        f"comparison_decisions={len(payload['comparison_decisions'])}",
    ]
    for item in payload["comparison_decisions"]:
        lines.append(
            " ".join(
                [
                    f"scenario_id={item['scenario_id']}",
                    f"decision={item['decision']['decision']}",
                    f"rollback_plan_ref={item['decision']['rollback_plan_ref']}",
                ]
            )
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
