"""Summarize recent internal pilot traces from local observability storage."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "services" / "observability-service" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from observability_service.service import DEFAULT_REQUIRED_FLOW_EVENTS, ObservabilityService


@dataclass(frozen=True)
class PilotTraceSummary:
    request_id: str
    session_id: str | None
    mission_id: str | None
    total_events: int
    event_names: list[str]
    missing_required_events: list[str]
    anomaly_flags: list[str]
    trace_status: str
    governance_decision: str | None
    operation_status: str | None
    duration_seconds: float
    source_services: list[str]


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Summarize JARVIS internal pilot traces.")
    parser.add_argument(
        "--database-path",
        default=str(ROOT / ".jarvis_runtime" / "observability.db"),
        help="Path to the local observability SQLite database.",
    )
    parser.add_argument("--request-id", help="Single request_id to summarize.")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of recent request traces to summarize.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for the report.",
    )
    return parser.parse_args()


def summarize_traces(
    database_path: str,
    *,
    request_id: str | None = None,
    limit: int = 10,
) -> list[PilotTraceSummary]:
    service = ObservabilityService(database_path=database_path)
    audits = (
        [service.audit_flow(query=service_query(request_id))]
        if request_id
        else service.summarize_recent_requests(limit=limit)
    )
    return [
        PilotTraceSummary(
            request_id=audit.request_id or "unknown",
            session_id=audit.session_id,
            mission_id=audit.mission_id,
            total_events=audit.total_events,
            event_names=audit.event_names,
            missing_required_events=audit.missing_required_events,
            anomaly_flags=audit.anomaly_flags,
            trace_status=_trace_status(audit),
            governance_decision=audit.governance_decision,
            operation_status=audit.operation_status,
            duration_seconds=audit.duration_seconds,
            source_services=audit.source_services,
        )
        for audit in audits
        if audit.total_events > 0
    ]


def service_query(request_id: str):
    from observability_service.service import ObservabilityQuery

    return ObservabilityQuery(
        request_id=request_id,
        limit=max(len(DEFAULT_REQUIRED_FLOW_EVENTS) * 4, 100),
    )


def _trace_status(audit) -> str:
    if audit.anomaly_flags:
        return "attention_required"
    if audit.missing_required_events:
        return "incomplete"
    return "healthy"


def render_text(summaries: list[PilotTraceSummary]) -> str:
    if not summaries:
        return "No internal pilot traces found."
    return "\n".join(
        (
            f"request_id={summary.request_id} "
            f"session_id={summary.session_id} "
            f"mission_id={summary.mission_id} "
            f"total_events={summary.total_events} "
            f"governance_decision={summary.governance_decision} "
            f"operation_status={summary.operation_status} "
            f"missing_required_events={','.join(summary.missing_required_events) or 'none'} "
            f"anomaly_flags={','.join(summary.anomaly_flags) or 'none'} "
            f"trace_status={summary.trace_status} "
            f"source_services={','.join(summary.source_services) or 'none'} "
            f"duration_seconds={summary.duration_seconds}"
        )
        for summary in summaries
    )


def main() -> None:
    args = parse_args()
    summaries = summarize_traces(
        args.database_path,
        request_id=args.request_id,
        limit=args.limit,
    )
    if args.format == "json":
        print(dumps([asdict(summary) for summary in summaries], ensure_ascii=True, indent=2))
        return
    print(render_text(summaries))


if __name__ == "__main__":
    main()
