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

from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.events import InternalEventEnvelope

REQUIRED_TRACE_EVENTS = (
    "input_received",
    "memory_recovered",
    "intent_classified",
    "context_composed",
    "plan_built",
    "governance_checked",
    "response_synthesized",
    "memory_recorded",
)


@dataclass(frozen=True)
class PilotTraceSummary:
    request_id: str
    session_id: str | None
    mission_id: str | None
    total_events: int
    event_names: list[str]
    missing_required_events: list[str]
    governance_decision: str | None
    operation_status: str | None
    duration_seconds: float


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
    request_ids = [request_id] if request_id else _recent_request_ids(service, limit)
    summaries: list[PilotTraceSummary] = []
    for item in request_ids:
        events = service.list_recent_events(ObservabilityQuery(request_id=item, limit=100))
        if not events:
            continue
        metrics = service.summarize_flow(ObservabilityQuery(request_id=item, limit=100))
        event_names = [event.event_name for event in events]
        decision_event = _first_event(events, "governance_checked")
        operation_event = _first_event(events, "operation_completed")
        first_event = events[0]
        summaries.append(
            PilotTraceSummary(
                request_id=item,
                session_id=first_event.session_id,
                mission_id=first_event.mission_id,
                total_events=len(events),
                event_names=event_names,
                missing_required_events=[
                    name for name in REQUIRED_TRACE_EVENTS if name not in event_names
                ],
                governance_decision=(
                    str(decision_event.payload.get("decision")) if decision_event else None
                ),
                operation_status=(
                    str(operation_event.payload.get("status")) if operation_event else None
                ),
                duration_seconds=metrics.duration_seconds,
            )
        )
    return summaries


def _recent_request_ids(service: ObservabilityService, limit: int) -> list[str]:
    events = service.list_recent_events(ObservabilityQuery(limit=max(limit * 20, 20)))
    request_ids: list[str] = []
    for event in reversed(events):
        if event.request_id and event.request_id not in request_ids:
            request_ids.append(event.request_id)
    return list(reversed(request_ids[-limit:]))


def _first_event(
    events: list[InternalEventEnvelope], event_name: str
) -> InternalEventEnvelope | None:
    for event in events:
        if event.event_name == event_name:
            return event
    return None


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
