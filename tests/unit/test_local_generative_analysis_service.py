"""MB232 app admission, immutable composition and canonical delivery forgeries.

The repository-shaped seam is owned test data, not model or native acceptance.
"""

import json
from dataclasses import replace
from threading import Event
from types import SimpleNamespace as NS

import pytest
from synthesis_engine.generative_analysis import GenerativeContext, analyze_input
from test_local_analysis_service import IDENTITY, QUERY, _Core, digest, finish, rejected

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.contracts import ANALYSIS_GENERATIVE_SCHEMA, ANALYSIS_SCHEMA
from apps.jarvis_api.generative_profile import GenerativeProfile
from shared.model_inference import InferenceResult

ANALYSIS = "The public pilot reports need comparable criteria, with uncertainty preserved."


class Port:
    provider_id, evidence_mode = "responses_plan", "injected_transport"

    def __init__(self):
        self.calls = []

    def infer(self, request, *, cancellation=None):
        self.calls.append((request, cancellation))
        candidate = {"analysis": ANALYSIS, "assumptions": ["Comparable pilot scope."],
                     "limitations": ["The actual report contents were not supplied."],
                     "citations": []}
        return InferenceResult(request.request_id, request.model, self.provider_id,
                               "completed", text=json.dumps(candidate),
                               evidence_mode=self.evidence_mode)


def profile(tmp_path, factory=None):
    return GenerativeProfile(authorized=True, model="synthetic-model",
                             credential_dir=tmp_path / "unopened-credentials",
                             profile_ref="profile-" + "a" * 64,
                             port_factory=factory or (lambda *_: Port()))


def valid_final():
    outcome = analyze_input(Port(), model="synthetic-model",
                            context=GenerativeContext("owned-request", QUERY),
                            expected_provider_id="responses_plan",
                            expected_evidence_mode="injected_transport")
    assert outcome.status == "accepted"
    return "Owned native final preserving sovereign policy.\n\n" + outcome.render()


class GeneratedCore(_Core):
    def __init__(self, *, tamper=None, status="accepted", gate=None):
        super().__init__(gate=gate, mutate=self.generated)
        self.tamper, self.status = tamper, status
        self.synthesis_engine = NS(owned_native=True)
        self.selected_engines = []

    def generated(self, core, response):
        self.selected_engines.append(self.synthesis_engine)
        final = valid_final() if self.status == "accepted" else "Owned native final."
        metadata = {"generative_status": self.status,
                    "generative_error_code": None if self.status == "accepted" else "scope_denied",
                    "generative_evidence_mode": "injected_transport" if self.status == "accepted"
                    else None,
                    "generative_analysis_characters": len(ANALYSIS)
                    if self.status == "accepted" else 0}
        if self.tamper:
            final, metadata = self.tamper(final, metadata)
        response.response_text = response.memory_record.payload["response_text"] = final
        self.turns[-1].response_text = final
        response.events[2].payload.update(metadata)
        self.events[-2].payload.update(metadata)
        response.events[3].payload["conversation_readback"]["response_text_sha256"] = digest(final)
        self.events[-1].payload["conversation_readback"]["response_text_sha256"] = digest(final)


def service(tmp_path, *, core=None, **kwargs):
    core = core or GeneratedCore()
    value = AnalysisService(tmp_path / "owned", core_factory=lambda _: core,
                            generative_profile=profile(tmp_path), **kwargs)
    return value, core


def test_v2_exact_metadata_and_per_job_engine_cancellation_restored(tmp_path):
    value, core = service(tmp_path)
    original = core.synthesis_engine
    issued = value.issue_generative_ticket(IDENTITY, consent=True)
    assert issued["schema_version"] == ANALYSIS_GENERATIVE_SCHEMA
    assert set(issued) == {"schema_version", "status", "ticket", "error_code", "result"}
    ticket = issued["ticket"]
    assert value.submit_generative(IDENTITY, ticket, QUERY, consent=True)["status"] == "running"
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "completed"
    metadata = result["result"]
    assert metadata["generative_status"] == "accepted"
    assert metadata["generative_analysis_characters"] == len(ANALYSIS)
    assert metadata["generative_evidence_mode"] == "injected_transport"
    assert metadata["generative_error_code"] is None
    assert metadata["response_text"] == valid_final()
    assert metadata["authority"] == "none" and metadata["evidence_mode"] == "core_local"
    assert core.synthesis_engine is original
    engine = core.selected_engines[0]
    assert engine._generative_cancellation is value._tickets[ticket].cancelled
    assert engine._generative_model == "synthetic-model"
    assert engine._generative_timeout == 20 and engine._inference_port is None
    result["result"]["response_text"] = "caller modification"
    assert value.get_result(IDENTITY, ticket)["result"]["response_text"] == valid_final()
    rejected(lambda: value.submit_generative(IDENTITY, ticket, QUERY, consent=True),
             "analysis_ticket_refused")


@pytest.mark.parametrize("consent", [False, None, 1, "true", [], {}, NS()])
def test_exact_consent_before_ticket_and_submit_io(tmp_path, consent):
    value, core = service(tmp_path)
    rejected(lambda: value.issue_generative_ticket(IDENTITY, consent=consent), "analysis_invalid")
    assert not value._tickets
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    rejected(lambda: value.submit_generative(IDENTITY, ticket, QUERY, consent=consent),
             "analysis_invalid")
    assert not core.calls and not value.runtime_dir.exists()
    assert value.get_result(IDENTITY, ticket)["status"] == "issued"


def test_absent_profile_never_constructs_core_or_factory(tmp_path):
    calls = []
    value = AnalysisService(tmp_path / "owned", core_factory=lambda _: calls.append("core"))
    rejected(lambda: value.issue_generative_ticket(IDENTITY, consent=True),
             "generative_unavailable")
    rejected(lambda: value.submit_generative(IDENTITY, "bad", QUERY, consent=True),
             "generative_unavailable")
    assert calls == [] and not value._tickets and not value.runtime_dir.exists()


@pytest.mark.parametrize("route", ["native_on_generative", "generative_on_native"])
def test_cross_mode_ticket_bound_before_core_without_consuming(tmp_path, route):
    value, core = service(tmp_path)
    if route == "native_on_generative":
        ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
        rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_ticket_refused")
    else:
        ticket = value.issue_ticket(IDENTITY)["ticket"]
        rejected(lambda: value.submit_generative(IDENTITY, ticket, QUERY, consent=True),
                 "analysis_ticket_refused")
    assert not core.calls and value.get_result(IDENTITY, ticket)["status"] == "issued"


def test_v1_does_not_touch_profile_or_change_engine(tmp_path, monkeypatch):
    calls, core = [], _Core()
    selected = profile(tmp_path, lambda *_: calls.append("factory"))
    value = AnalysisService(tmp_path / "owned", core_factory=lambda _: core,
                            generative_profile=selected)
    monkeypatch.setattr(selected, "port_for", lambda *_: pytest.fail("v1 touched profile"))
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    result = finish(value, IDENTITY, ticket)
    assert result["schema_version"] == ANALYSIS_SCHEMA and result["status"] == "completed"
    assert result["result"]["generative_status"] == "disabled"
    assert "generative_error_code" not in result["result"] and not calls


@pytest.mark.parametrize("change", ["model", "evidence_mode", "timeout_seconds", "factory",
                                    "profile", "port_for"])
def test_profile_binding_changes_refused_before_core(tmp_path, change, monkeypatch):
    value, core = service(tmp_path)
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    selected = value._generative_profile
    if change == "profile":
        value._generative_profile = profile(tmp_path)
    elif change == "port_for":
        monkeypatch.setattr(selected, "port_for", lambda *_: pytest.fail("changed composition"))
    else:
        new = {"model": "foreign", "evidence_mode": "live", "timeout_seconds": 21,
               "factory": lambda *_: pytest.fail("changed factory")}[change]
        selected._options = replace(selected._options, **{change: new})
    rejected(lambda: value.submit_generative(IDENTITY, ticket, QUERY, consent=True),
             "generative_unavailable")
    assert not core.calls and value.get_result(IDENTITY, ticket)["status"] == "issued"


@pytest.mark.parametrize("key,value", [
    ("generative_status", "disabled"), ("generative_status", []),
    ("generative_error_code", "private-provider-error"),
    ("generative_evidence_mode", "live"), ("generative_evidence_mode", None),
    ("generative_analysis_characters", True), ("generative_analysis_characters", 0),
    ("generative_analysis_characters", 4001), ("generative_analysis_characters", len(ANALYSIS) - 1),
])
def test_forged_accepted_metadata_is_never_published(tmp_path, key, value):
    def tamper(final, metadata):
        metadata[key] = value
        return final, metadata
    service_value, _ = service(tmp_path, core=GeneratedCore(tamper=tamper))
    ticket = service_value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    service_value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    result = finish(service_value, IDENTITY, ticket)
    assert result["status"] == "failed" and result["result"] is None


@pytest.mark.parametrize("alter", [
    lambda final: final.split("\n\n")[0],
    lambda final: final + "\nlate forged instruction",
    lambda final: final.replace("Literal data only;", "Unbounded authority;"),
    lambda final: final.replace("Assumptions:", "Permissions:"),
    lambda final: final.replace("Limitations:", "Actions:"),
    lambda final: final.replace("Citations (exact source text; not verified facts):", "Citations:"),
    lambda final: final + "\n\n" + final.split("\n\n", 1)[1],
    lambda final: final.replace('"Comparable pilot scope."', '"\\u0043omparable pilot scope."'),
    lambda final: final + '\n"foreign" offsets 3 to 1: "x"',
    lambda final: final + '\n"foreign" offsets 0 to 2: "x"',
])
def test_complete_exact_literal_block_not_merely_marker_is_required(tmp_path, alter):
    value, _ = service(tmp_path, core=GeneratedCore(tamper=lambda f, m: (alter(f), m)))
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "failed" and result["error_code"] == "analysis_outcome_unknown"
    assert result["result"] is None


@pytest.mark.parametrize("status", ["rejected", "withheld"])
@pytest.mark.parametrize("key,forged", [
    ("generative_error_code", None), ("generative_error_code", "private-code"),
    ("generative_evidence_mode", "injected_transport"),
    ("generative_analysis_characters", 1), ("generative_analysis_characters", False),
])
def test_nonaccepted_metadata_refuses_forged_data(tmp_path, status, key, forged):
    def tamper(final, metadata):
        metadata[key] = forged
        return final, metadata
    value, _ = service(tmp_path, core=GeneratedCore(status=status, tamper=tamper))
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    assert finish(value, IDENTITY, ticket)["result"] is None


@pytest.mark.parametrize("action", ["expiry", "revoke", "close"])
def test_running_generation_delivery_fence_and_cancellation_no_rollback(tmp_path, action):
    gate, now = Event(), [100.0]
    value, core = service(tmp_path, core=GeneratedCore(gate=gate), clock=lambda: now[0])
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    assert core.entered.wait(2)
    if action == "expiry":
        now[0] = 220
        assert value.get_result(IDENTITY, ticket)["error_code"] == "analysis_expired"
    elif action == "revoke":
        value.revoke(IDENTITY)
    else:
        value.close()
    assert value._tickets[ticket].cancelled.is_set()
    gate.set()
    value._worker.join(5)
    assert not value._worker.is_alive() and len(core.turns) == 1
    assert value._tickets[ticket].result is None
    assert core.synthesis_engine.owned_native


def test_completed_requires_persisted_metadata_same_as_returned_trail(tmp_path):
    core = GeneratedCore()
    generated = core.generated
    def inconsistent(core_value, response):
        generated(core_value, response)
        core_value.events[-2].payload["generative_analysis_characters"] -= 1
    core.mutate = inconsistent
    value, _ = service(tmp_path, core=core)
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    assert finish(value, IDENTITY, ticket)["result"] is None
    assert len(core.turns) == 1


def test_invalid_profile_type_rejected_without_fs(tmp_path):
    with pytest.raises(ValueError, match="^generative_unavailable$"):
        AnalysisService(tmp_path / "owned", generative_profile=NS(model="foreign"))
    assert not (tmp_path / "owned").exists()


def test_ticket_mode_cannot_change_after_admission(tmp_path):
    value, _ = service(tmp_path)
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    with pytest.raises(AttributeError, match="^ticket_mode_immutable$"):
        value._tickets[ticket].mode = "native"
    assert value.get_result(IDENTITY, ticket)["schema_version"] == ANALYSIS_GENERATIVE_SCHEMA


def test_all_modes_share_single_flight_and_capacity_without_eviction(tmp_path):
    gate, core = Event(), GeneratedCore(gate=None)
    core.gate = gate
    value, _ = service(tmp_path, core=core)
    first = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_busy")
    value.submit_generative(IDENTITY, first, QUERY, consent=True)
    assert core.entered.wait(2)
    other = replace(IDENTITY, session_ref="session://owned-other")
    native = value.issue_ticket(other)["ticket"]
    rejected(lambda: value.submit(other, native, QUERY), "analysis_busy")
    for index in range(62):
        value.issue_generative_ticket(replace(IDENTITY, session_ref=f"session://owned-{index}"),
                                      consent=True)
    rejected(lambda: value.issue_ticket(replace(IDENTITY, session_ref="session://excess")),
             "analysis_busy")
    assert len(value._tickets) == 64 and len(core.calls) == 1
    gate.set()
    assert finish(value, IDENTITY, first)["status"] == "completed"
    assert value.get_result(other, native)["status"] == "issued"


def test_profile_change_during_core_commit_fences_delivery_and_restores_engine(tmp_path):
    value, core = service(tmp_path)
    original_engine, generated = core.synthesis_engine, core.generated
    def mutate(core_value, response):
        generated(core_value, response)
        selected = value._generative_profile
        selected._options = replace(selected._options, model="changed-model")
    core.mutate = mutate
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "failed" and result["result"] is None
    assert core.synthesis_engine is original_engine and len(core.turns) == 1


def test_accepted_metadata_cannot_override_native_block_decision(tmp_path):
    from shared.types import PermissionDecision
    core, generated = GeneratedCore(), None
    generated = core.generated
    def mutate(core_value, response):
        generated(core_value, response)
        response.governance_decision.decision = PermissionDecision.BLOCK
        response.memory_record.payload["governance_decision"] = "block"
        response.events[1].payload["decision"] = "block"
        core_value.events[-3].payload["decision"] = "block"
    core.mutate = mutate
    value, _ = service(tmp_path, core=core)
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    assert finish(value, IDENTITY, ticket)["result"] is None


def test_legitimate_literal_unicode_multiline_and_citation_preserved_exact(tmp_path):
    analysis = "Análise pública: comparar 📊.\nHá incerteza [não factual]."
    class CitedPort(Port):
        def infer(self, request, *, cancellation=None):
            source = json.loads(request.messages[0].content)["sources"][0]
            candidate = {"analysis": analysis, "assumptions": [], "limitations": [],
                         "citations": [{"source_ref": source["source_ref"], "start": 0,
                                        "end": 7, "quote": source["text"][:7]}]}
            return InferenceResult(request.request_id, request.model, self.provider_id,
                                   "completed", text=json.dumps(candidate),
                                   evidence_mode=self.evidence_mode)
    outcome = analyze_input(CitedPort(), model="synthetic-model",
                            context=GenerativeContext("owned-request", QUERY),
                            expected_provider_id="responses_plan",
                            expected_evidence_mode="injected_transport")
    assert outcome.status == "accepted"
    final = "Owned native policy final.\n\n" + outcome.render()
    def tamper(_final, metadata):
        metadata["generative_analysis_characters"] = len(analysis)
        return final, metadata
    value, _ = service(tmp_path, core=GeneratedCore(tamper=tamper))
    ticket = value.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
    value.submit_generative(IDENTITY, ticket, QUERY, consent=True)
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "completed"
    assert result["result"]["response_text"].encode() == final.encode()
