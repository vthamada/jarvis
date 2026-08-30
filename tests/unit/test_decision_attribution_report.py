from __future__ import annotations

from dataclasses import asdict, replace
from json import loads
from pathlib import Path

from memory_service.service import MemoryService
from observability_service.service import ObservabilityService

from shared.contracts import (
    DecisionOutcomeAttributionRecordContract,
    ExperienceRecordContract,
)
from shared.decision_attribution import canonicalize_decision_attribution_record
from shared.events import InternalEventEnvelope
from shared.types import MissionId, RequestId, SessionId
from tools.decision_attribution_report import (
    build_decision_attribution_report,
    save_report,
)


def _record(
    suffix: str,
    *,
    request_id: str,
    mission_id: str,
    workflow_profile: str,
    observed_at: str,
) -> DecisionOutcomeAttributionRecordContract:
    return canonicalize_decision_attribution_record(
        DecisionOutcomeAttributionRecordContract(
            attribution_record_id=f"decision-attribution://{suffix}",
            request_id=RequestId(request_id),
            session_id=SessionId(f"session-{suffix}"),
            mission_id=MissionId(mission_id),
            observed_at=observed_at,
            governance_decision_ref=f"governance-decision://{suffix}",
            governance_decision_status="allow_with_conditions",
            workflow_profile=workflow_profile,
            route="software_engineering",
            outcome_ref=f"experience://{mission_id}/{request_id}",
            outcome_status="completed",
            experience_id=f"experience://{mission_id}/{request_id}",
            workflow_policy_ref=f"workflow-policy://{suffix}",
            workflow_policy_version="1.0.0",
            workflow_policy_source_registry_ref="registry://domains/v1",
            workflow_policy_source_registry_fingerprint="sha256:registry-v1",
            workflow_policy_application_status="applied",
            workflow_policy_effects=["bounded_plan"],
            evidence_refs=[f"trace://{suffix}"],
        )
    )


def _recorded_event(
    record: DecisionOutcomeAttributionRecordContract,
    *,
    timestamp: str,
    include_envelope_mission: bool = True,
) -> InternalEventEnvelope:
    return InternalEventEnvelope(
        event_id=f"event-recorded-{record.request_id}",
        event_name="decision_outcome_attribution_recorded",
        timestamp=timestamp,
        source_service="orchestrator-service",
        request_id=record.request_id,
        session_id=record.session_id,
        mission_id=record.mission_id if include_envelope_mission else None,
        payload=asdict(record),
    )


def _feedback_event(
    record: DecisionOutcomeAttributionRecordContract,
    *,
    suffix: str,
    timestamp: str,
) -> InternalEventEnvelope:
    return InternalEventEnvelope(
        event_id=f"event-feedback-{suffix}",
        event_name="operator_feedback_recorded",
        timestamp=timestamp,
        source_service="orchestrator-service",
        request_id=record.request_id,
        session_id=record.session_id,
        mission_id=None,
        payload={
            "mission_id": str(record.mission_id),
            "operator_feedback_id": f"operator-feedback://{suffix}",
            "operator_feedback_experience_id": record.experience_id,
            "operator_feedback_assessment": "helpful",
            "operator_feedback_rating": 5,
            "operator_feedback_evidence_refs": [f"feedback-evidence://{suffix}"],
        },
    )


def _services(
    tmp_path: Path,
) -> tuple[MemoryService, ObservabilityService, Path, Path]:
    memory_db = tmp_path / "memory.db"
    observability_db = tmp_path / "observability.db"
    return (
        MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}"),
        ObservabilityService(database_path=str(observability_db)),
        memory_db,
        observability_db,
    )


def _persist_record(
    memory: MemoryService,
    record: DecisionOutcomeAttributionRecordContract,
) -> None:
    memory.claim_runtime_request(
        request_id=str(record.request_id),
        session_id=str(record.session_id),
        claimed_at=record.observed_at,
    )
    memory.record_experience(
        experience=ExperienceRecordContract(
            experience_id=str(record.experience_id),
            mission_id=MissionId(str(record.mission_id)),
            workflow_profile=str(record.workflow_profile),
            outcome_status=str(record.outcome_status),
            timestamp=record.observed_at,
            route=record.route,
            evidence_refs=[f"experience-evidence://{record.request_id}"],
        )
    )
    memory.record_decision_outcome_attribution(record)


def test_tool_filters_canonical_records_and_only_reads_relevant_events(
    tmp_path: Path,
) -> None:
    memory, observability, memory_db, observability_db = _services(tmp_path)
    records = [
        _record(
            "target",
            request_id="request-target",
            mission_id="mission-shared",
            workflow_profile="software_change_workflow",
            observed_at="2026-08-11T12:00:00Z",
        ),
        _record(
            "sibling",
            request_id="request-sibling",
            mission_id="mission-shared",
            workflow_profile="analysis_workflow",
            observed_at="2026-08-11T12:01:00Z",
        ),
        _record(
            "external",
            request_id="request-external",
            mission_id="mission-external",
            workflow_profile="software_change_workflow",
            observed_at="2026-08-11T12:02:00Z",
        ),
    ]
    for record in records:
        _persist_record(memory, record)
    observability.ingest_events(
        [
            _recorded_event(
                records[0],
                timestamp=records[0].observed_at,
                include_envelope_mission=False,
            ),
            _feedback_event(
                records[0],
                suffix="target-one",
                timestamp="2026-08-11T12:00:10Z",
            ),
            _feedback_event(
                records[0],
                suffix="target-two",
                timestamp="2026-08-11T12:00:20Z",
            ),
            _recorded_event(records[1], timestamp=records[1].observed_at),
            _recorded_event(records[2], timestamp=records[2].observed_at),
            InternalEventEnvelope(
                event_id="event-unrelated-plan",
                event_name="plan_built",
                timestamp="2026-08-11T12:03:00Z",
                source_service="orchestrator-service",
                request_id=RequestId("request-target"),
                mission_id=MissionId("mission-shared"),
                payload={"workflow_profile": "software_change_workflow"},
            ),
        ]
    )
    before = {
        memory_db: memory_db.read_bytes(),
        observability_db: observability_db.read_bytes(),
    }

    by_request = build_decision_attribution_report(
        memory_service=memory,
        observability_service=observability,
        request_id="request-target",
        generated_at="2026-08-11T13:00:00Z",
    )
    by_mission = build_decision_attribution_report(
        memory_service=memory,
        observability_service=observability,
        mission_id="mission-shared",
        generated_at="2026-08-11T13:00:00Z",
    )
    by_profile = build_decision_attribution_report(
        memory_service=memory,
        observability_service=observability,
        workflow_profile="software_change_workflow",
        generated_at="2026-08-11T13:00:00Z",
    )

    assert [item.attribution for item in by_request.items] == [records[0]]
    assert {item.attribution.request_id for item in by_mission.items} == {
        RequestId("request-target"),
        RequestId("request-sibling"),
    }
    assert {item.attribution.request_id for item in by_profile.items} == {
        RequestId("request-target"),
        RequestId("request-external"),
    }
    assert "event-unrelated-plan" not in by_request.evidence_refs
    assert all("event-unrelated-plan" not in item for item in by_request.limitations)
    assert by_request.report_status == "attribution_observed"
    assert by_request.feedback_linked_count == 1
    assert by_request.items[0].feedback_refs == [
        "operator-feedback://target-one",
        "operator-feedback://target-two",
    ]
    assert "attribution_event_missing" not in by_request.items[0].limitations
    assert by_request.source_event_limit_reached is False
    assert by_request.causal_effect_proven is False
    assert by_request.gain_claim_status == "not_established_without_comparator"
    assert by_request.promotion_authorized is False
    assert by_request.automatic_promotion_allowed is False
    assert by_request.core_mutation_allowed is False
    assert memory_db.read_bytes() == before[memory_db]
    assert observability_db.read_bytes() == before[observability_db]


def test_tool_marks_truncation_and_saves_report_outside_canonical_stores(
    tmp_path: Path,
) -> None:
    memory, observability, memory_db, observability_db = _services(tmp_path)
    older = _record(
        "older",
        request_id="request-older",
        mission_id="mission-limit",
        workflow_profile="software_change_workflow",
        observed_at="2026-08-11T12:00:00Z",
    )
    newer = _record(
        "newer",
        request_id="request-newer",
        mission_id="mission-limit",
        workflow_profile="software_change_workflow",
        observed_at="2026-08-11T12:01:00Z",
    )
    for record in (older, newer):
        _persist_record(memory, record)
        observability.ingest_events(
            [_recorded_event(record, timestamp=record.observed_at)]
        )
    observability.ingest_events(
        [
            _feedback_event(
                newer,
                suffix=f"limit-{index:03d}",
                timestamp=f"2026-08-11T12:02:00.{index:06d}Z",
            )
            for index in range(101)
        ]
    )
    before = {
        memory_db: memory_db.read_bytes(),
        observability_db: observability_db.read_bytes(),
    }

    report = build_decision_attribution_report(
        memory_service=memory,
        observability_service=observability,
        mission_id="mission-limit",
        limit=1,
        generated_at="2026-08-11T13:00:00Z",
    )
    latest_path, history_path = save_report(
        report,
        output_dir=tmp_path / "reports",
    )
    payload = loads(latest_path.read_text(encoding="utf-8"))

    assert report.record_count == 1
    assert report.source_record_limit_reached is True
    assert report.source_event_limit_reached is True
    assert payload["read_only"] is True
    assert payload["causal_effect_proven"] is False
    assert payload["gain_claim_status"] == "not_established_without_comparator"
    assert payload["promotion_authorized"] is False
    assert payload["automatic_promotion_allowed"] is False
    assert payload["core_mutation_allowed"] is False
    assert history_path.exists()
    assert memory_db.read_bytes() == before[memory_db]
    assert observability_db.read_bytes() == before[observability_db]


def test_tool_downgrades_attribution_when_full_recorded_payload_is_tampered(
    tmp_path: Path,
) -> None:
    memory, observability, _, _ = _services(tmp_path)
    record = canonicalize_decision_attribution_record(
        replace(
            _record(
                "tampered",
                request_id="request-tampered",
                mission_id="mission-tampered",
                workflow_profile="software_change_workflow",
                observed_at="2026-08-11T12:00:00Z",
            ),
            memory_ignored_refs=["memory://ignored/canonical"],
        )
    )
    _persist_record(memory, record)
    canonical_event = _recorded_event(
        record,
        timestamp=record.observed_at,
    )
    observability.ingest_events(
        [
            replace(
                canonical_event,
                payload={
                    **canonical_event.payload,
                    "memory_ignored_refs": ["memory://ignored/forged"],
                },
            )
        ]
    )

    report = build_decision_attribution_report(
        memory_service=memory,
        observability_service=observability,
        request_id=str(record.request_id),
        generated_at="2026-08-11T13:00:00Z",
    )

    assert record.attribution_status == "declared_causality"
    assert report.declared_causality_count == 0
    assert report.insufficient_evidence_count == 1
    assert (
        "effective_attribution_downgraded_to_insufficient_evidence"
        in report.items[0].limitations
    )
