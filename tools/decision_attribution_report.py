"""Build read-only decision/outcome attribution reports from canonical stores."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from pathlib import Path

from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.contracts import (
    DecisionOutcomeAttributionRecordContract,
    DecisionOutcomeAttributionReportContract,
)
from shared.events import InternalEventEnvelope

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = (
    ROOT / ".jarvis_runtime" / "observability" / "decision-attribution"
)
DECISION_ATTRIBUTION_EVENT_NAMES = (
    "decision_outcome_attribution_recorded",
    "decision_outcome_attribution_failed",
    "operator_feedback_recorded",
)
DECISION_ATTRIBUTION_EVENTS_PER_RECORD_LIMIT = 100
DECISION_ATTRIBUTION_FAILED_EVENT_LIMIT = 100


def build_decision_attribution_report(
    *,
    observability_service: ObservabilityService,
    memory_service: MemoryService,
    request_id: str | None = None,
    mission_id: str | None = None,
    workflow_profile: str | None = None,
    limit: int = 20,
    generated_at: str | None = None,
) -> DecisionOutcomeAttributionReportContract:
    """Collect bounded canonical evidence without mutating either source store."""

    safe_limit = max(1, min(limit, 100))
    safe_generated_at = generated_at or datetime.now(UTC).isoformat()
    record_filters = {
        "request_id": request_id,
        "mission_id": mission_id,
        "workflow_profile": workflow_profile,
    }
    records = memory_service.list_decision_outcome_attributions(
        **record_filters,
        limit=safe_limit,
    )
    source_record_limit_reached = bool(
        len(records) == safe_limit
        and memory_service.list_decision_outcome_attributions(
            **record_filters,
            limit=1,
            offset=safe_limit,
        )
    )

    events, source_event_limit_reached = _collect_attribution_events(
        observability_service=observability_service,
        records=records,
        request_id=request_id,
        mission_id=mission_id,
        workflow_profile=workflow_profile,
    )
    report_seed = "|".join(
        [
            safe_generated_at,
            request_id or "",
            mission_id or "",
            workflow_profile or "",
            *(record.attribution_record_id for record in records),
            *(event.event_id for event in events),
        ]
    )
    return ObservabilityService.build_decision_outcome_attribution_report(
        report_id=(
            "decision-outcome-attribution-report://"
            f"{sha256(report_seed.encode()).hexdigest()[:16]}"
        ),
        records=records,
        events=events,
        generated_at=safe_generated_at,
        source_record_limit_reached=source_record_limit_reached,
        source_event_limit_reached=source_event_limit_reached,
    )


def _collect_attribution_events(
    *,
    observability_service: ObservabilityService,
    records: list[DecisionOutcomeAttributionRecordContract],
    request_id: str | None,
    mission_id: str | None,
    workflow_profile: str | None,
) -> tuple[list[InternalEventEnvelope], bool]:
    events_by_id: dict[str, InternalEventEnvelope] = {}
    source_limit_reached = False
    for record in records:
        record_request_id = str(record.request_id)
        lane = observability_service.list_recent_events(
            ObservabilityQuery(
                limit=DECISION_ATTRIBUTION_EVENTS_PER_RECORD_LIMIT + 1,
                event_names=DECISION_ATTRIBUTION_EVENT_NAMES,
                request_id=record_request_id,
            )
        )
        if len(lane) > DECISION_ATTRIBUTION_EVENTS_PER_RECORD_LIMIT:
            source_limit_reached = True
        for event in lane[-DECISION_ATTRIBUTION_EVENTS_PER_RECORD_LIMIT:]:
            events_by_id[event.event_id] = event

    failed_lane = observability_service.list_recent_events(
        ObservabilityQuery(
            limit=DECISION_ATTRIBUTION_FAILED_EVENT_LIMIT + 1,
            event_names=("decision_outcome_attribution_failed",),
            request_id=request_id,
        )
    )
    if len(failed_lane) > DECISION_ATTRIBUTION_FAILED_EVENT_LIMIT:
        source_limit_reached = True
    for event in failed_lane[-DECISION_ATTRIBUTION_FAILED_EVENT_LIMIT:]:
        if _failed_event_matches_scope(
            event,
            records=records,
            request_id=request_id,
            mission_id=mission_id,
            workflow_profile=workflow_profile,
        ):
            events_by_id[event.event_id] = event
    return (
        sorted(
            events_by_id.values(),
            key=lambda event: (event.timestamp, event.event_id),
        ),
        source_limit_reached,
    )


def _failed_event_matches_scope(
    event: InternalEventEnvelope,
    *,
    records: list[DecisionOutcomeAttributionRecordContract],
    request_id: str | None,
    mission_id: str | None,
    workflow_profile: str | None,
) -> bool:
    record_request_ids = {str(record.request_id) for record in records}
    record_ids = {record.attribution_record_id for record in records}
    event_request_id = _event_text(event, "request_id") or (
        str(event.request_id) if event.request_id else None
    )
    event_record_id = _event_text(event, "attribution_record_id")
    if event_request_id in record_request_ids or event_record_id in record_ids:
        return True
    if request_id is not None and event_request_id != request_id:
        return False
    if mission_id is not None:
        effective_mission_id = _event_text(event, "mission_id") or (
            str(event.mission_id) if event.mission_id else None
        )
        if effective_mission_id != mission_id:
            return False
    if (
        workflow_profile is not None
        and _event_text(event, "workflow_profile") != workflow_profile
    ):
        return False
    return True


def _event_text(event: InternalEventEnvelope, field_name: str) -> str | None:
    value = event.payload.get(field_name)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def save_report(
    report: DecisionOutcomeAttributionReportContract,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Persist derived report evidence outside canonical runtime stores."""

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = dumps(asdict(report), ensure_ascii=False, indent=2, sort_keys=True)
    latest_path = output_dir / "latest.json"
    history_path = output_dir / f"{_safe_timestamp(report.generated_at)}.json"
    latest_path.write_text(payload + "\n", encoding="utf-8")
    history_path.write_text(payload + "\n", encoding="utf-8")
    return latest_path, history_path


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "-").replace("+", "_").replace("/", "-")


def _resolve_path(value: str | None, default: Path) -> Path:
    path = Path(value).expanduser() if value else default
    return path.resolve() if not path.is_absolute() else path


def main() -> int:
    parser = ArgumentParser(
        description="Build a read-only decision/outcome attribution report."
    )
    parser.add_argument("--observability-db")
    parser.add_argument("--memory-db")
    parser.add_argument("--request-id")
    parser.add_argument("--mission-id")
    parser.add_argument("--workflow-profile")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    observability_db = _resolve_path(
        args.observability_db,
        ROOT / ".jarvis_runtime" / "console" / "observability.db",
    )
    memory_db = _resolve_path(
        args.memory_db,
        ROOT / ".jarvis_runtime" / "console" / "memory.db",
    )
    report = build_decision_attribution_report(
        observability_service=ObservabilityService(
            database_path=str(observability_db)
        ),
        memory_service=MemoryService(
            database_url=f"sqlite:///{memory_db.as_posix()}"
        ),
        request_id=args.request_id,
        mission_id=args.mission_id,
        workflow_profile=args.workflow_profile,
        limit=args.limit,
    )
    latest_path, _ = save_report(
        report,
        output_dir=(
            _resolve_path(args.output_dir, DEFAULT_OUTPUT_DIR)
            if args.output_dir
            else DEFAULT_OUTPUT_DIR
        ),
    )
    print(latest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
