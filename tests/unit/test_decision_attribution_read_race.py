"""Deterministic independent-read races over disposable real SQLite storage."""

from dataclasses import replace

import pytest
from memory_service.service import MemoryService

from shared.contracts import DecisionOutcomeAttributionRecordContract, ExperienceRecordContract
from shared.decision_attribution import canonicalize_decision_attribution_record
from shared.types import MissionId, RequestId, SessionId


def _record():
    # Same persisted-claim/experience fixture pattern as test_memory_service.py.
    experience_id = "experience://mission-attribution-read-race/request-attribution-read-race"
    return canonicalize_decision_attribution_record(
        DecisionOutcomeAttributionRecordContract(
            attribution_record_id="decision-attribution://read-race",
            request_id=RequestId("request-attribution-read-race"),
            session_id=SessionId("session://attribution-read-race"),
            mission_id=MissionId("mission-attribution-read-race"),
            observed_at="2026-10-04T12:00:00Z",
            governance_decision_ref="governance-decision://attribution-read-race",
            governance_decision_status="allow_with_conditions",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            outcome_ref=experience_id,
            outcome_status="completed",
            experience_id=experience_id,
            evidence_refs=["trace://attribution-read-race"],
        )
    )


def _persist_links(service, record):
    service.claim_runtime_request(
        request_id=str(record.request_id),
        session_id=str(record.session_id),
        claimed_at=record.observed_at,
    )
    service.record_experience(
        experience=ExperienceRecordContract(
            experience_id=record.experience_id,
            mission_id=record.mission_id,
            workflow_profile=record.workflow_profile,
            outcome_status=record.outcome_status,
            timestamp=record.observed_at,
            route=record.route,
            evidence_refs=["experience-evidence://attribution-read-race"],
        )
    )


def _insert_between_reads(service, writer, monkeypatch, winner):
    original_fetch = service.repository.fetch_decision_outcome_attribution
    observed_queries = []

    def fetch(**kwargs):
        observed_queries.append(kwargs)
        result = original_fetch(**kwargs)
        if len(observed_queries) == 1:
            assert kwargs == {"attribution_record_id": "decision-attribution://read-race"}
            assert result is None
            _persist_links(writer, winner)
            writer.record_decision_outcome_attribution(winner)
        return result

    monkeypatch.setattr(service.repository, "fetch_decision_outcome_attribution", fetch)
    return observed_queries


def test_identical_insert_between_id_and_request_reads_is_idempotent(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'memory.db'}"
    service = MemoryService(database_url=database_url)
    writer = MemoryService(database_url=database_url)
    record = _record()
    _persist_links(service, record)
    queries = _insert_between_reads(service, writer, monkeypatch, record)
    assert service.record_decision_outcome_attribution(record) == record
    assert queries[:3] == [
        {"attribution_record_id": record.attribution_record_id},
        {"request_id": str(record.request_id)},
        {"attribution_record_id": record.attribution_record_id},
    ]
    assert writer.list_decision_outcome_attributions() == [record]


@pytest.mark.parametrize("collision", ["same_id", "same_request", "different_payload"])
def test_concurrent_identity_or_payload_conflict_remains_immutable(
    tmp_path, monkeypatch, collision
):
    database_url = f"sqlite:///{tmp_path / 'memory.db'}"
    service = MemoryService(database_url=database_url)
    writer = MemoryService(database_url=database_url)
    record = _record()
    _persist_links(service, record)
    if collision == "same_id":
        foreign_experience = (
            "experience://mission-attribution-read-race/request-attribution-read-race-foreign"
        )
        winner = replace(
            record,
            request_id=RequestId("request-attribution-read-race-foreign"),
            experience_id=foreign_experience,
            outcome_ref=foreign_experience,
        )
    elif collision == "same_request":
        winner = replace(record, attribution_record_id="decision-attribution://foreign")
    else:
        winner = replace(record, governance_decision_ref="governance-decision://foreign")
    winner = canonicalize_decision_attribution_record(winner)
    _insert_between_reads(service, writer, monkeypatch, winner)
    with pytest.raises(ValueError, match="identity is immutable"):
        service.record_decision_outcome_attribution(record)
    assert writer.list_decision_outcome_attributions() == [winner]
    assert (
        writer.get_decision_outcome_attribution(attribution_record_id=winner.attribution_record_id)
        == winner
    )


def test_reread_does_not_skip_exact_persisted_storage_links(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'memory.db'}"
    service = MemoryService(database_url=database_url)
    writer = MemoryService(database_url=database_url)
    record = _record()
    _persist_links(service, record)
    _insert_between_reads(service, writer, monkeypatch, record)
    monkeypatch.setattr(service.repository, "fetch_runtime_request_claim", lambda _request: None)
    with pytest.raises(ValueError, match="requires a runtime request claim"):
        service.record_decision_outcome_attribution(record)
    assert writer.list_decision_outcome_attributions() == [record]


def test_exact_present_counterpart_does_not_authorize_a_still_missing_identity(
    tmp_path, monkeypatch
):
    service = MemoryService(database_url=f"sqlite:///{tmp_path / 'memory.db'}")
    record = _record()
    _persist_links(service, record)
    service.record_decision_outcome_attribution(record)
    original_fetch = service.repository.fetch_decision_outcome_attribution
    missing_reads = []

    def inconsistent_fetch(**kwargs):
        if "attribution_record_id" in kwargs:
            missing_reads.append(kwargs)
            return None
        return original_fetch(**kwargs)

    monkeypatch.setattr(
        service.repository, "fetch_decision_outcome_attribution", inconsistent_fetch
    )
    with pytest.raises(ValueError, match="identity is immutable"):
        service.record_decision_outcome_attribution(record)
    assert len(missing_reads) == 2
    assert service.list_decision_outcome_attributions() == [record]
