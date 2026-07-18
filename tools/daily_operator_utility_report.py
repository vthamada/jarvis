"""Build evidence-backed daily operator utility outcomes from canonical stores."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from json import dumps
from pathlib import Path

from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.contracts import DailyOperatorUtilityReportContract

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "observability" / "operator-utility"


def build_daily_operator_utility_report(
    *,
    observability_service: ObservabilityService,
    memory_service: MemoryService,
    period_start: str | None = None,
    period_end: str | None = None,
    generated_at: str | None = None,
    event_limit: int = 1000,
    mission_limit: int = 200,
) -> DailyOperatorUtilityReportContract:
    """Collect bounded evidence and build one read-only period report."""

    safe_generated = _parse_timestamp(
        generated_at or datetime.now(UTC).isoformat(),
        field_name="generated_at",
    )
    safe_end = _parse_timestamp(
        period_end or safe_generated.isoformat(),
        field_name="period_end",
    )
    safe_start = _parse_timestamp(
        period_start or (safe_end - timedelta(hours=24)).isoformat(),
        field_name="period_start",
    )
    if safe_start > safe_end:
        raise ValueError("period_start must be before or equal to period_end")

    safe_event_limit = max(1, min(event_limit, 5000))
    safe_mission_limit = max(1, min(mission_limit, 200))
    events = observability_service.list_recent_events(
        ObservabilityQuery(limit=safe_event_limit)
    )
    mission_states = memory_service.list_mission_states(
        limit=safe_mission_limit,
        include_closed=True,
    )
    seed = "|".join(
        [
            safe_start.isoformat(),
            safe_end.isoformat(),
            *(event.event_id for event in events),
            *(str(state.mission_id) for state in mission_states),
        ]
    )
    return ObservabilityService.build_daily_operator_utility_report(
        report_id=f"operator-utility-report://{sha256(seed.encode()).hexdigest()[:16]}",
        events=events,
        mission_states=mission_states,
        period_start=safe_start.isoformat(),
        period_end=safe_end.isoformat(),
        generated_at=safe_generated.isoformat(),
        source_event_limit_reached=len(events) == safe_event_limit,
        source_mission_limit_reached=len(mission_states) == safe_mission_limit,
    )


def save_report(
    report: DailyOperatorUtilityReportContract,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Persist report evidence outside canonical runtime stores."""

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = dumps(asdict(report), indent=2, sort_keys=True)
    latest_path = output_dir / "latest.json"
    history_path = output_dir / f"{_safe_timestamp(report.generated_at)}.json"
    latest_path.write_text(payload + "\n", encoding="utf-8")
    history_path.write_text(payload + "\n", encoding="utf-8")
    return latest_path, history_path


def _parse_timestamp(value: str, *, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an ISO timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "-").replace("+", "_").replace("/", "-")


def main() -> int:
    parser = ArgumentParser(description="Build daily operator utility evidence.")
    parser.add_argument("--observability-db")
    parser.add_argument("--memory-db")
    parser.add_argument("--period-start")
    parser.add_argument("--period-end")
    parser.add_argument("--event-limit", type=int, default=1000)
    parser.add_argument("--mission-limit", type=int, default=200)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    observability_db = Path(
        args.observability_db
        or ROOT / ".jarvis_runtime" / "console" / "observability.db"
    ).expanduser()
    memory_db = Path(
        args.memory_db or ROOT / ".jarvis_runtime" / "console" / "memory.db"
    ).expanduser()
    report = build_daily_operator_utility_report(
        observability_service=ObservabilityService(
            database_path=str(observability_db.resolve())
        ),
        memory_service=MemoryService(
            database_url=f"sqlite:///{memory_db.resolve().as_posix()}"
        ),
        period_start=args.period_start,
        period_end=args.period_end,
        event_limit=args.event_limit,
        mission_limit=args.mission_limit,
    )
    latest_path, _ = save_report(
        report,
        output_dir=Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR,
    )
    print(latest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
