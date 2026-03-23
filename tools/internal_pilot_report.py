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
    continuity_action: str | None
    continuity_source: str | None
    continuity_runtime_mode: str | None
    registry_domains: list[str]
    shadow_specialists: list[str]
    domain_alignment_status: str
    memory_alignment_status: str
    specialist_sovereignty_status: str
    expectation_status: str
    continuity_trace_status: str
    missing_continuity_signals: list[str]
    continuity_anomaly_flags: list[str]
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
            continuity_action=audit.continuity_action,
            continuity_source=audit.continuity_source,
            continuity_runtime_mode=audit.continuity_runtime_mode,
            registry_domains=list(audit.registry_domains),
            shadow_specialists=list(audit.shadow_specialists),
            domain_alignment_status=audit.domain_alignment_status,
            memory_alignment_status=audit.memory_alignment_status,
            specialist_sovereignty_status=audit.specialist_sovereignty_status,
            expectation_status=_expectation_status(
                governance_decision=audit.governance_decision,
                operation_status=audit.operation_status,
                continuity_action=audit.continuity_action,
            ),
            continuity_trace_status=audit.continuity_trace_status,
            missing_continuity_signals=audit.missing_continuity_signals,
            continuity_anomaly_flags=audit.continuity_anomaly_flags,
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
    if audit.anomaly_flags or audit.continuity_anomaly_flags:
        return "attention_required"
    if audit.missing_required_events or audit.missing_continuity_signals:
        return "incomplete"
    return "healthy"


def _expectation_status(
    *,
    governance_decision: str | None,
    operation_status: str | None,
    continuity_action: str | None,
) -> str:
    if governance_decision == "block":
        return "guardrail_expected"
    if governance_decision == "defer_for_validation":
        return "manual_validation_expected"
    if continuity_action in {"continuar", "retomar"} and operation_status in {None, "completed"}:
        return "continuity_progressing"
    if operation_status == "completed":
        return "operation_completed"
    return "review_required"


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
            f"continuity_action={summary.continuity_action or 'none'} "
            f"continuity_source={summary.continuity_source or 'none'} "
            f"continuity_runtime_mode={summary.continuity_runtime_mode or 'none'} "
            "registry_domains="
            f"{','.join(getattr(summary, 'registry_domains', [])) or 'none'} "
            "shadow_specialists="
            f"{','.join(getattr(summary, 'shadow_specialists', [])) or 'none'} "
            "domain_alignment_status="
            f"{getattr(summary, 'domain_alignment_status', 'incomplete')} "
            "memory_alignment_status="
            f"{getattr(summary, 'memory_alignment_status', 'incomplete')} "
            "specialist_sovereignty_status="
            f"{getattr(summary, 'specialist_sovereignty_status', 'incomplete')} "
            f"expectation_status={summary.expectation_status} "
            "missing_continuity_signals="
            f"{','.join(summary.missing_continuity_signals) or 'none'} "
            "continuity_anomaly_flags="
            f"{','.join(summary.continuity_anomaly_flags) or 'none'} "
            f"continuity_trace_status={summary.continuity_trace_status} "
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
