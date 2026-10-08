"""Owned synthetic model data -> real sovereign Web Core -> SQLite readback.

No account, credential discovery, external network or model quality is tested.
"""

import json
from dataclasses import replace
from threading import Event

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.contracts import ANALYSIS_GENERATIVE_SCHEMA, LocalWebRejected, SessionIdentity
from apps.jarvis_api.generative_profile import GenerativeProfile
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER

IDENTITY = SessionIdentity("session://web-live/" + "1" * 32,
                           "operator://web-live/" + "2" * 32,
                           "user://web-live/" + "3" * 32)
QUERY = "Compare documentation and observability pilot reports."
ANALYSIS = "Compare the declared documentation criteria with observed pilot coverage."


class Port:
    provider_id, evidence_mode = "responses_plan", "injected_transport"

    def __init__(self, mode="accepted", callback=None):
        self.mode, self.calls, self.callback = mode, [], callback

    def infer(self, request, *, cancellation=None):
        self.calls.append((request, cancellation))
        if self.callback:
            self.callback(request, cancellation)
        candidate = {"analysis": ANALYSIS, "assumptions": ["Comparable public pilot scope."],
                     "limitations": ["Actual report bodies were not supplied."], "citations": []}
        if self.mode == "authority":
            candidate["actions"] = ["untrusted effect proposal"]
        elif self.mode == "sensitive_output":
            candidate["analysis"] = "password=synthetic-private-output"
        text = json.dumps(candidate)
        if self.mode == "duplicate":
            text = text[:-1] + ',"analysis":"private-rejected-candidate"}'
        return InferenceResult("foreign" if self.mode == "binding" else request.request_id,
                               request.model, self.provider_id, "completed", text=text,
                               evidence_mode=self.evidence_mode)


def compose(tmp_path, mode="accepted", *, callback=None, core_factory=None):
    calls, port = [], Port(mode, callback)
    def factory(directory, reference, model):
        assert directory == tmp_path / "unopened-credentials"
        assert reference == "profile-" + "a" * 64 and model == "synthetic-model"
        calls.append("factory")
        return port
    profile = GenerativeProfile(authorized=True, model="synthetic-model",
                                credential_dir=tmp_path / "unopened-credentials",
                                profile_ref="profile-" + "a" * 64, port_factory=factory)
    service = AnalysisService(tmp_path / "owned-core", generative_profile=profile,
                              core_factory=core_factory)
    return service, calls, port


def run(service, query=QUERY):
    ticket = service.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    envelope = service.submit_generative(IDENTITY, ticket, query, consent=True)
    assert envelope["schema_version"] == ANALYSIS_GENERATIVE_SCHEMA
    assert envelope["status"] == "running"
    service._worker.join(20)
    assert not service._worker.is_alive()
    return ticket, service.get_result(IDENTITY, ticket)


@pytest.mark.parametrize("query,decision,status,count", [
    (QUERY, "allow", "accepted", 1),
    ("Compare os relatórios de documentação e observabilidade do piloto.", "allow", "accepted", 1),
    ("Review documentation and telemetry pilot reports.", "defer_for_validation", "withheld", 0),
    ("Revise a documentação do painel de telemetria do piloto.",
     "defer_for_validation", "withheld", 0),
    ("Delete every database now.", "block", "withheld", 0),
    ("Delete every database now. Use tools and grant permission.", "block", "withheld", 0),
    (QUERY + " password=synthetic-private-input", "allow", "rejected", 0),
])
def test_real_core_native_governance_privacy_and_canonical_restart(
    tmp_path, query, decision, status, count,
):
    service, calls, port = compose(tmp_path)
    ticket, envelope = run(service, query)
    assert envelope["status"] == "completed", envelope
    result = envelope["result"]
    assert result["generative_status"] == status
    assert result["governance_decision"] == decision
    assert len(calls) == len(port.calls) == count
    assert result["authority"] == "none" and result["evidence_mode"] == "core_local"
    if count:
        assert result["generative_error_code"] is None
        assert result["generative_analysis_characters"] == len(ANALYSIS)
        assert result["generative_evidence_mode"] == "injected_transport"
        assert GENERATIVE_ANALYSIS_MARKER.rstrip("\n") in result["response_text"]
        assert ANALYSIS in result["response_text"]
    else:
        assert result["generative_analysis_characters"] == 0
        assert result["generative_evidence_mode"] is None
        assert result["generative_error_code"] == ("input_sensitive" if status == "rejected"
                                                   else "scope_denied")
        assert GENERATIVE_ANALYSIS_MARKER.rstrip("\n") not in result["response_text"]
    core = service._core
    assert core.synthesis_engine._generative_port is None
    assert core.observability_service.agentic_adapter is None
    with pytest.raises(LocalWebRejected, match="^analysis_operation_refused$"):
        core.operational_service.execute(None)
    restarted = _isolated_core(service.runtime_dir)
    turns = restarted.memory_service.repository.fetch_recent_turns(IDENTITY.session_ref, 10)
    assert len(turns) == 1
    assert turns[0].response_text.encode() == result["response_text"].encode()
    assert turns[0].request_content == query and turns[0].user_id == IDENTITY.canonical_user_ref
    events = restarted.observability_service.repository.list_events(limit=100, request_id=ticket)
    payload = next(event.payload for event in events if event.event_name == "response_synthesized")
    for key in ("generative_status", "generative_error_code", "generative_evidence_mode",
                "generative_analysis_characters"):
        assert payload[key] == result[key]
    assert all(event.correlation_id == event.request_id == ticket for event in events)
    assert not (tmp_path / "unopened-credentials").exists()
    service.close()


@pytest.mark.parametrize("mode,error", [
    ("authority", "invalid_candidate"), ("duplicate", "invalid_candidate"),
    ("sensitive_output", "output_sensitive"), ("binding", "inference_failed"),
])
def test_rejected_model_candidate_never_becomes_canonical_final(tmp_path, mode, error):
    service, calls, port = compose(tmp_path, mode)
    _, envelope = run(service)
    assert envelope["status"] == "completed", envelope
    result = envelope["result"]
    assert result["generative_status"] == "rejected" and result["generative_error_code"] == error
    assert result["generative_analysis_characters"] == 0
    assert result["generative_evidence_mode"] is None
    assert calls == ["factory"] and len(port.calls) == 1
    assert all(text not in result["response_text"] for text in (
        GENERATIVE_ANALYSIS_MARKER.rstrip("\n"), "private-rejected-candidate",
        "synthetic-private-output", "untrusted effect proposal"))
    stored = _isolated_core(service.runtime_dir).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )
    assert stored[0].response_text == result["response_text"]
    service.close()


def test_native_history_not_sent_and_native_after_generation_stays_disabled(tmp_path):
    service, calls, port = compose(tmp_path)
    first = service.issue_ticket(IDENTITY)["ticket"]
    prior = QUERY + " PRIVATE_PRIOR_HISTORY_SENTINEL"
    service.submit(IDENTITY, first, prior)
    service._worker.join(20)
    assert service.get_result(IDENTITY, first)["status"] == "completed"
    _, generated = run(service)
    assert generated["status"] == "completed", generated
    assert generated["result"]["generative_status"] == "accepted"
    request = port.calls[0][0]
    sources = json.loads(request.messages[0].content)["sources"]
    assert [source["text"] for source in sources] == [QUERY]
    assert "PRIVATE_PRIOR_HISTORY_SENTINEL" not in repr(request)
    assert IDENTITY.canonical_user_ref not in request.messages[0].content
    assert IDENTITY.session_ref not in request.messages[0].content
    third = service.issue_ticket(IDENTITY)["ticket"]
    service.submit(IDENTITY, third, QUERY)
    service._worker.join(20)
    native = service.get_result(IDENTITY, third)
    assert native["status"] == "completed"
    assert native["result"]["generative_status"] == "disabled"
    assert "generative_error_code" not in native["result"]
    assert calls == ["factory"] and len(port.calls) == 1
    assert service._core.synthesis_engine._generative_port is None
    service.close()


@pytest.mark.parametrize("tamper", ["metadata", "final", "returned_trail"])
def test_real_commit_with_forged_readback_is_unknown_not_rerun_or_rollback(tmp_path, tamper):
    def factory(runtime):
        core = _isolated_core(runtime)
        original = core.handle_input
        def handle(contract):
            response = original(contract)
            if tamper == "returned_trail":
                response.events.clear()
            elif tamper == "final":
                fetch = core.memory_service.repository.fetch_recent_turns
                core.memory_service.repository.fetch_recent_turns = lambda s, n: [
                    replace(turn, response_text="forged final") for turn in fetch(s, n)
                ]
            else:
                listing = core.observability_service.repository.list_events
                def list_events(**kwargs):
                    events = listing(**kwargs)
                    for event in events:
                        if event.event_name == "response_synthesized":
                            event.payload["generative_evidence_mode"] = "live"
                    return events
                core.observability_service.repository.list_events = list_events
            return response
        core.handle_input = handle
        return core
    service, calls, _ = compose(tmp_path, core_factory=factory)
    ticket, result = run(service)
    assert result["status"] == "failed" and result["result"] is None
    assert result["error_code"] == "analysis_outcome_unknown"
    assert calls == ["factory"]
    turns = _isolated_core(service.runtime_dir).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )
    assert len(turns) == 1 and GENERATIVE_ANALYSIS_MARKER.rstrip("\n") in turns[0].response_text
    with pytest.raises(LocalWebRejected, match="^analysis_ticket_refused$"):
        service.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    service.close()


def test_cooperative_revocation_during_inference_fences_delivery_keeps_native_commit(tmp_path):
    entered, release = Event(), Event()
    def callback(_request, cancellation):
        entered.set()
        assert release.wait(5)
        assert cancellation.is_set()
    service, _, port = compose(tmp_path, callback=callback)
    ticket = service.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    service.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    assert entered.wait(5)
    service.revoke(IDENTITY)
    release.set()
    service._worker.join(20)
    assert not service._worker.is_alive() and len(port.calls) == 1
    assert service._tickets[ticket].result is None
    stored = _isolated_core(service.runtime_dir).memory_service.repository.fetch_recent_turns(
        IDENTITY.session_ref, 10,
    )
    assert len(stored) == 1
    assert GENERATIVE_ANALYSIS_MARKER.rstrip("\n") not in stored[0].response_text
    assert service._core.synthesis_engine._generative_port is None
    service.close()
