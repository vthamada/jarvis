from json import loads
from pathlib import Path

from memory_service.service import MemoryService
from observability_service.service import ObservabilityService

from shared.contracts import MissionStateContract
from shared.events import InternalEventEnvelope
from shared.types import MissionStatus
from tools.daily_operator_utility_report import (
    build_daily_operator_utility_report,
    save_report,
)


def test_tool_builds_and_saves_read_only_operator_utility_evidence(
    tmp_path: Path,
) -> None:
    observability_db = tmp_path / "observability.db"
    memory_db = tmp_path / "memory.db"
    observability = ObservabilityService(database_path=str(observability_db))
    memory = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    memory.repository.upsert_mission_state(
        MissionStateContract(
            mission_id="mission-tool-utility",
            mission_goal="Validate utility evidence",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-18T10:10:00+00:00",
        )
    )
    observability.ingest_events(
        [
            InternalEventEnvelope(
                event_id="event-tool-resume",
                event_name="open_loop_resumed",
                timestamp="2026-07-18T10:00:00+00:00",
                source_service="orchestrator-service",
                mission_id="mission-tool-utility",
                payload={"next_action_ref": "next-action://tool/validate"},
            ),
            InternalEventEnvelope(
                event_id="event-tool-work",
                event_name="work_item_state_changed",
                timestamp="2026-07-18T10:10:00+00:00",
                source_service="orchestrator-service",
                mission_id="mission-tool-utility",
                payload={
                    "work_item_ref": "work-item://tool/validate",
                    "work_item_status": "completed",
                    "previous_work_item_status": "active",
                },
            ),
        ]
    )
    before = {
        observability_db: observability_db.read_bytes(),
        memory_db: memory_db.read_bytes(),
    }

    report = build_daily_operator_utility_report(
        observability_service=observability,
        memory_service=memory,
        period_start="2026-07-18T09:00:00+00:00",
        period_end="2026-07-18T11:00:00+00:00",
        generated_at="2026-07-18T11:00:00+00:00",
    )
    latest_path, history_path = save_report(
        report,
        output_dir=tmp_path / "reports",
    )

    assert report.mission_count == 1
    assert report.completion_rate == 1.0
    assert report.average_time_to_next_action_seconds == 600.0
    assert report.saved_time_claim_status == "not_claimed_without_controlled_baseline"
    assert loads(latest_path.read_text(encoding="utf-8"))["read_only"] is True
    assert history_path.exists()
    assert observability_db.read_bytes() == before[observability_db]
    assert memory_db.read_bytes() == before[memory_db]
