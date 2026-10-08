"""Default live-local service -> real native Core SQLite persistence/readback."""

from dataclasses import replace

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.contracts import LocalWebRejected, SessionIdentity
from apps.jarvis_console.voice_pilot import _isolated_core

IDENTITY = SessionIdentity("session://web-live/" + "1" * 32,
                           "principal://web-live/" + "2" * 32,
                           "user://web-live/" + "3" * 32)


def finish(service, ticket):
    service._worker.join(20)
    assert not service._worker.is_alive()
    return service.get_result(IDENTITY, ticket)


@pytest.mark.parametrize("query,decision", [
    ("Compare documentation and observability pilot reports.", "allow"),
    ("Compare os relatórios de documentação e observabilidade do piloto.", "allow"),
    ("Review documentation and telemetry pilot reports.", "defer_for_validation"),
    ("Delete every database now.", "block"),
])
def test_default_core_policy_final_and_canonical_user_survive_sqlite_restart(
    tmp_path, query, decision,
):
    runtime = tmp_path / "owned-local-core"
    service = AnalysisService(runtime)
    ticket = service.issue_ticket(IDENTITY)["ticket"]
    assert service.submit(IDENTITY, ticket, query)["status"] == "running"
    envelope = finish(service, ticket)
    assert envelope["status"] == "completed", envelope["error_code"]
    result = envelope["result"]
    assert result["query"] == query and result["governance_decision"] == decision
    assert result["evidence_mode"] == "core_local" and result["generative_status"] == "disabled"
    assert result["authority"] == "none"
    core = service._core
    assert core.synthesis_engine._generative_port is None
    assert core.synthesis_engine._inference_port is None
    assert core.observability_service.agentic_adapter is None
    with pytest.raises(LocalWebRejected, match="^analysis_operation_refused$"):
        core.operational_service.execute(None)
    restarted = _isolated_core(runtime)
    turns = restarted.memory_service.repository.fetch_recent_turns(IDENTITY.session_ref, 10)
    assert len(turns) == 1
    turn = turns[0]
    assert turn.user_id == IDENTITY.canonical_user_ref
    assert turn.timestamp == result["timestamp"] and turn.intent == result["intent"]
    assert turn.request_content == query
    assert turn.response_text.encode("utf-8") == result["response_text"].encode("utf-8")
    events = restarted.observability_service.repository.list_events(
        limit=100, request_id=ticket,
    )
    assert all(event.request_id == event.correlation_id == ticket for event in events)
    assert all(event.session_id == IDENTITY.session_ref for event in events)
    received = next(event.payload for event in events if event.event_name == "input_received")
    assert received["canonical_user_ref"] == IDENTITY.canonical_user_ref
    assert received["operator_identity_ref"] == IDENTITY.principal_ref
    assert received["surface_capability_scope"] == []
    memory = next(event.payload for event in events if event.event_name == "memory_recorded")
    assert memory["memory_record_id"] == result["memory_record_ref"]
    assert memory["conversation_readback"]["record_timestamp"] == turn.timestamp
    with pytest.raises(LocalWebRejected, match="^analysis_ticket_refused$"):
        service.submit(IDENTITY, ticket, query)
    assert len(restarted.memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )) == 1
    service.close()


def test_real_core_owns_serialized_new_turns_but_tickets_are_not_restart_resumable(tmp_path):
    runtime = tmp_path / "owned-local-core"
    service = AnalysisService(runtime)
    first = service.issue_ticket(IDENTITY)["ticket"]
    service.submit(IDENTITY, first, "Compare documentation and observability pilot reports.")
    assert finish(service, first)["status"] == "completed"
    second = service.issue_ticket(IDENTITY)["ticket"]
    service.submit(IDENTITY, second, "Review documentation and telemetry pilot reports.")
    assert finish(service, second)["status"] == "completed"
    turns = _isolated_core(runtime).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )
    assert len(turns) == 2 and first != second
    fresh = AnalysisService(tmp_path / "other-fresh-runtime")
    assert fresh.current_ticket(IDENTITY) is None
    with pytest.raises(LocalWebRejected, match="^analysis_ticket_refused$"):
        fresh.get_result(IDENTITY, first)
    service.revoke(IDENTITY)
    with pytest.raises(LocalWebRejected, match="^analysis_ticket_refused$"):
        service.get_result(IDENTITY, second)
    assert len(_isolated_core(runtime).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )) == 2  # revocation fences delivery, never claims a memory rollback
    service.close()


@pytest.mark.parametrize("tamper", ["turn_final", "binding_hash", "missing_event"])
def test_native_commit_then_bad_readback_is_unknown_not_success_or_rollback(tmp_path, tamper):
    def factory(runtime):
        core = _isolated_core(runtime)
        original = core.handle_input

        def handle(contract):
            response = original(contract)
            if tamper == "turn_final":
                fetch = core.memory_service.repository.fetch_recent_turns
                core.memory_service.repository.fetch_recent_turns = lambda s, n: [
                    replace(turn, response_text="Owned tampered readback") for turn in fetch(s, n)
                ]
            else:
                listing = core.observability_service.repository.list_events

                def list_events(**kwargs):
                    events = listing(**kwargs)
                    if tamper == "missing_event":
                        return [event for event in events if event.event_name != "memory_recorded"]
                    for event in events:
                        if event.event_name == "memory_recorded":
                            binding = event.payload["conversation_readback"]
                            binding["response_text_sha256"] = "0" * 64
                    return events

                core.observability_service.repository.list_events = list_events
            return response

        core.handle_input = handle
        return core

    runtime = tmp_path / "owned-local-core"
    service = AnalysisService(runtime, core_factory=factory)
    ticket = service.issue_ticket(IDENTITY)["ticket"]
    service.submit(IDENTITY, ticket, "Compare documentation and observability pilot reports.")
    result = finish(service, ticket)
    assert result["status"] == "failed" and result["result"] is None
    assert result["error_code"] == "analysis_outcome_unknown"
    turns = _isolated_core(runtime).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )
    assert len(turns) == 1 and turns[0].response_text != "Owned tampered readback"
    service.close()
