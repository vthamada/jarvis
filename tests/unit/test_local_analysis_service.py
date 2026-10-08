"""Single-flight/cancellation/adversarial leaf tests using owned in-memory Core seams."""

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from threading import Barrier, Event
from types import SimpleNamespace as NS

import pytest

from apps.jarvis_api import analysis_service as module
from apps.jarvis_api.contracts import ANALYSIS_SCHEMA, LocalWebRejected, SessionIdentity
from shared.types import PermissionDecision

IDENTITY = SessionIdentity("session://web-live/" + "a" * 32,
                           "principal://web-live/" + "b" * 32,
                           "user://web-live/" + "c" * 32)
QUERY = "Compare documentation and observability pilot reports."
FINAL = "Public local Core final; policy and canonical memory retained. 📊"


def digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


class _Core:
    """Owned repository-shaped seam, not a native Core acceptance substitute."""

    def __init__(self, *, gate=None, failure=None, mutate=None):
        self.calls, self.turns, self.events = [], [], []
        self.entered, self.gate, self.failure, self.mutate = Event(), gate, failure, mutate
        self.memory_service = NS(repository=NS(fetch_recent_turns=lambda session, limit: [
            turn for turn in self.turns if turn.session_id == session
        ][:limit]))
        self.observability_service = NS(repository=NS(list_events=self.list_events))

    def list_events(self, *, limit, event_names, **filters):
        return [event for event in self.events if event.event_name in event_names
                and all(getattr(event, key) == value for key, value in filters.items())][:limit]

    def handle_input(self, contract):
        self.calls.append(contract)
        self.entered.set()
        if self.gate is not None:
            assert self.gate.wait(5), "owned blocked Core fixture was not released"
        if self.failure is not None:
            raise self.failure
        stamp = "2026-10-06T10:00:04+00:00"
        record = NS(record_type="interaction_turn", source_service="memory-service",
                    memory_record_id="mem-record-" + contract.request_id[-8:],
                    session_id=contract.session_id, user_id=contract.user_id, mission_id=None,
                    timestamp=stamp, payload={"request_content": contract.content,
                                              "response_text": FINAL, "intent": "analysis",
                                              "governance_decision": "allow"})
        turn = NS(session_id=contract.session_id, user_id=contract.user_id, mission_id=None,
                  timestamp=stamp, request_content=contract.content, response_text=FINAL,
                  intent="analysis")
        self.turns.append(turn)
        payloads = [
            {"content": contract.content, "canonical_user_ref": contract.user_id,
             "operator_identity_ref": contract.operator_identity_ref,
             "surface_id": contract.surface_id, "surface_kind": "web",
             "surface_session_id": contract.session_id, "surface_capability_scope": [],
             "requested_autonomy_level": "assist_only", "max_autonomy_level": "assist_only"},
            {"decision": "allow"},
            {"intent": "analysis", "generative_status": "disabled", "generative_error_code": None,
             "generative_evidence_mode": None, "generative_analysis_characters": 0},
            {"memory_record_id": record.memory_record_id, "record_type": "interaction_turn",
             "conversation_readback": {"schema_version": "jarvis-conversation-readback-v1",
                                       "record_timestamp": stamp,
                                       "principal_sha256": digest(contract.user_id),
                                       "request_content_sha256": digest(contract.content),
                                       "response_text_sha256": digest(FINAL)}},
        ]
        events = [NS(event_id=f"{contract.request_id}-{index}", event_name=name,
                     timestamp=f"2026-10-06T10:00:0{index if index < 4 else 5}+00:00",
                     request_id=contract.request_id, correlation_id=contract.request_id,
                     session_id=contract.session_id, mission_id=None,
                     source_service="orchestrator-service", payload=payload)
                  for index, (name, payload) in enumerate(zip(module._NAMES, payloads), start=1)]
        self.events.extend(copy.deepcopy(events))
        response = NS(request_id=contract.request_id, session_id=contract.session_id,
                      intent="analysis", response_text=FINAL, memory_record=record, events=events,
                      governance_decision=NS(decision=PermissionDecision.ALLOW))
        if self.mutate:
            self.mutate(self, response)
        return response


def service(tmp_path, **core_args):
    core = _Core(**core_args)
    value = module.AnalysisService(tmp_path / "owned", core_factory=lambda _: core)
    return value, core


def finish(value, identity, ticket):
    value._worker.join(5)
    assert not value._worker.is_alive()
    return value.get_result(identity, ticket)


def rejected(call, code):
    with pytest.raises(LocalWebRejected, match="^" + code + "$") as error:
        call()
    assert error.value.code == code


def test_issued_running_completed_exact_envelope_and_server_owned_core_identity(tmp_path):
    gate = Event()
    value, core = service(tmp_path, gate=gate)
    issued = value.issue_ticket(IDENTITY)
    ticket = issued["ticket"]
    assert issued == {"schema_version": ANALYSIS_SCHEMA, "status": "issued", "ticket": ticket,
                      "error_code": None, "result": None}
    assert module.TICKET_PATTERN.fullmatch(ticket)
    assert value.current_ticket(IDENTITY) == ticket
    running = value.submit(IDENTITY, ticket, QUERY)
    assert running == {**issued, "status": "running"}
    assert core.entered.wait(2)
    assert value.get_result(IDENTITY, ticket) == running
    contract = core.calls[0]
    assert contract.request_id == ticket and contract.session_id == IDENTITY.session_ref
    assert contract.user_id == contract.canonical_user_ref == IDENTITY.canonical_user_ref
    assert contract.operator_identity_ref == IDENTITY.principal_ref
    assert contract.channel.value == "web" and contract.input_type.value == "text"
    assert contract.surface_id == "surface://local-analysis" and contract.surface_kind == "web"
    assert contract.surface_session_id == IDENTITY.session_ref
    assert contract.requested_autonomy_level == contract.max_autonomy_level == "assist_only"
    assert contract.surface_capability_scope == contract.attachments == []
    assert contract.adapter_action_request is None
    assert contract.action_confirmation_receipt_id is None
    gate.set()
    completed = finish(value, IDENTITY, ticket)
    assert completed == {**issued, "status": "completed", "result": {
        "query": QUERY, "response_text": FINAL, "intent": "analysis",
        "governance_decision": "allow",
        "memory_record_ref": "mem-record-" + ticket[-8:], "timestamp": "2026-10-06T10:00:04+00:00",
        "evidence_mode": "core_local", "generative_status": "disabled", "authority": "none",
    }}
    completed["result"]["response_text"] = "caller alteration"
    assert value.get_result(IDENTITY, ticket)["result"]["response_text"] == FINAL
    assert len(core.calls) == 1


@pytest.mark.parametrize("query", [None, 1, "", " \t", "a" * 4001, "a\x00b", "a\x1bb",
                                    "a\u200bb", "a\ud800b", "a\u2028b", "a\u2029b"])
def test_exact_query_bounds_fail_before_worker_without_consuming_ticket(tmp_path, query):
    value, core = service(tmp_path)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    rejected(lambda: value.submit(IDENTITY, ticket, query), "analysis_invalid")
    assert not core.calls and value.get_result(IDENTITY, ticket)["status"] == "issued"


@pytest.mark.parametrize("query", ["a" * 4000, "Exact\r\npublic\tquery 📊.", "a" * 3999 + "📊"])
def test_valid_query_preserved_codepoint_exact(tmp_path, query):
    value, core = service(tmp_path)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, query)
    assert finish(value, IDENTITY, ticket)["result"]["query"] == query
    assert core.calls[0].content == query


@pytest.mark.parametrize("ticket", [None, "", "web-request-" + "a" * 31,
                                     "web-request-" + "a" * 32 + "\n",
                                     "web-request-" + "f" * 32])
def test_unissued_or_invalid_ticket_never_dispatches(tmp_path, ticket):
    value, core = service(tmp_path)
    rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_ticket_refused")
    rejected(lambda: value.get_result(IDENTITY, ticket), "analysis_ticket_refused")
    assert not core.calls


@pytest.mark.parametrize("field", ["session_ref", "principal_ref", "canonical_user_ref"])
def test_cross_identity_cannot_submit_poll_or_rebind(tmp_path, field):
    value, core = service(tmp_path)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    other = replace(IDENTITY, **{field: "foreign://public"})
    rejected(lambda: value.submit(other, ticket, QUERY), "analysis_ticket_refused")
    rejected(lambda: value.get_result(other, ticket), "analysis_ticket_refused")
    if field != "session_ref":
        rejected(lambda: value.issue_ticket(other), "analysis_ticket_refused")
    assert not core.calls


def test_per_session_and_global_single_flight_no_queue_replay_or_autorerun(tmp_path):
    gate = Event()
    value, core = service(tmp_path, gate=gate)
    first = value.issue_ticket(IDENTITY)["ticket"]
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_busy")
    value.submit(IDENTITY, first, QUERY)
    assert core.entered.wait(2)
    rejected(lambda: value.submit(IDENTITY, first, QUERY), "analysis_ticket_refused")
    other = replace(IDENTITY, session_ref="session://web-live/" + "d" * 32)
    second = value.issue_ticket(other)["ticket"]
    rejected(lambda: value.submit(other, second, QUERY), "analysis_busy")
    assert value.get_result(other, second)["status"] == "issued"
    gate.set()
    assert finish(value, IDENTITY, first)["status"] == "completed"
    rejected(lambda: value.submit(IDENTITY, first, QUERY), "analysis_ticket_refused")
    value.submit(other, second, QUERY)
    assert finish(value, other, second)["status"] == "completed"
    assert len(core.calls) == 2


def test_capacity_never_silently_evicted_or_durably_resumed(tmp_path):
    value, core = service(tmp_path)
    for index in range(module.MAX_TICKETS):
        identity = replace(IDENTITY, session_ref=f"session://owned-{index}")
        value.issue_ticket(identity)
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_busy")
    assert len(value._tickets) == 64 and not core.calls
    assert module.AnalysisService(tmp_path / "other").current_ticket(IDENTITY) is None


def test_expiry_running_fences_delivery_but_stays_globally_busy_until_core_finishes(tmp_path):
    gate, now = Event(), [100.0]
    core = _Core(gate=gate)
    value = module.AnalysisService(tmp_path / "owned", core_factory=lambda _: core,
                                   clock=lambda: now[0])
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    assert core.entered.wait(2)
    now[0] = 220.0
    failed = value.get_result(IDENTITY, ticket)
    assert failed["status"] == "failed" and failed["error_code"] == "analysis_expired"
    assert failed["result"] is None and value.current_ticket(IDENTITY) is None
    next_ticket = value.issue_ticket(IDENTITY)["ticket"]
    rejected(lambda: value.submit(IDENTITY, next_ticket, QUERY), "analysis_busy")
    gate.set()
    value._worker.join(5)
    assert value.get_result(IDENTITY, ticket) == failed
    assert len(core.calls) == len(core.turns) == 1  # expiry is not rollback


def test_revoke_discards_content_and_does_not_release_global_execution_lock(tmp_path):
    gate = Event()
    value, core = service(tmp_path, gate=gate)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    assert core.entered.wait(2)
    value.revoke(IDENTITY)
    rejected(lambda: value.get_result(IDENTITY, ticket), "analysis_ticket_refused")
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_ticket_refused")
    other = replace(IDENTITY, session_ref="session://owned-other")
    second = value.issue_ticket(other)["ticket"]
    rejected(lambda: value.submit(other, second, QUERY), "analysis_busy")
    gate.set()
    value._worker.join(5)
    assert value._tickets[ticket].result is None and len(core.turns) == 1


def test_close_bounded_fences_worker_and_refuses_new_submits(tmp_path):
    gate = Event()
    value, core = service(tmp_path, gate=gate)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    assert core.entered.wait(2)
    value.close()
    assert value._worker.is_alive()  # join bounded, not a fictitious rollback
    rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_closed")
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_closed")
    rejected(lambda: value.get_result(IDENTITY, ticket), "analysis_closed")
    gate.set()
    value._worker.join(5)
    assert value._tickets[ticket].result is None


def test_failed_exception_never_leaks_data_or_retries(tmp_path):
    value, core = service(tmp_path, failure=RuntimeError("secret=/home/private token=synthetic"))
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    failed = finish(value, IDENTITY, ticket)
    assert failed["result"] is None and failed["error_code"] == "analysis_outcome_unknown"
    assert "private" not in repr(failed) and "secret" not in repr(failed)
    rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_ticket_refused")
    assert len(core.calls) == 1


@pytest.mark.parametrize("case", [
    "request", "session", "final", "intent", "operation_result", "operation_dispatch",
    "adapter_grant", "adapter_grant_claim", "action_confirmation_claim",
    "action_confirmation_challenge",
    "record_user", "record_timestamp", "record_final", "record_intent", "record_decision",
    "record_reuse", "turn_query", "turn_final",
    "turn_user", "turn_duplicate", "event_missing", "event_duplicate", "event_source",
    "event_session", "event_correlation", "event_timeline", "input_content", "input_principal",
    "input_operator", "input_scope", "input_autonomy",
    "decision", "generation", "binding_hash", "binding_missing", "returned_trail",
])
def test_completed_requires_exact_canonical_readback_not_only_a_core_string(tmp_path, case):
    def mutate(core, response):
        if case in {"request", "session", "final", "intent"}:
            key = {"request": "request_id", "session": "session_id", "final": "response_text",
                   "intent": "intent"}[case]
            setattr(response, key, "foreign public value")
        elif case in {"operation_result", "operation_dispatch", "adapter_grant",
                      "adapter_grant_claim",
                      "action_confirmation_claim", "action_confirmation_challenge"}:
            setattr(response, case, NS())
        elif case.startswith("record_"):
            if case == "record_user":
                response.memory_record.user_id = "foreign"
            elif case == "record_timestamp":
                response.memory_record.timestamp = "2026-10-06T10:00:07+00:00"
            elif case == "record_intent":
                response.memory_record.payload["intent"] = "planning"
            elif case == "record_decision":
                response.memory_record.payload["governance_decision"] = "block"
            elif case == "record_reuse":
                duplicate = copy.deepcopy(core.events[-1])
                duplicate.event_id = "public-other-event"
                duplicate.request_id = duplicate.correlation_id = "public-other-request"
                duplicate.session_id = "session://other-owned"
                core.events.append(duplicate)
            else:
                response.memory_record.payload["response_text"] = "altered final"
        elif case.startswith("turn_"):
            if case == "turn_duplicate":
                core.turns.append(copy.deepcopy(core.turns[0]))
            else:
                setattr(core.turns[0], {"turn_query": "request_content",
                                        "turn_final": "response_text",
                                        "turn_user": "user_id"}[case], "foreign")
        elif case.startswith("event_"):
            if case == "event_missing":
                core.events.pop()
            elif case == "event_duplicate":
                duplicate = copy.deepcopy(core.events[0])
                duplicate.event_id = "public-duplicate-event"
                core.events.append(duplicate)
            elif case == "event_timeline":
                core.events[0].timestamp = "2026-10-06T10:00:08+00:00"
            else:
                setattr(core.events[0], {"event_source": "source_service",
                                        "event_session": "session_id",
                                        "event_correlation": "correlation_id"}[case], "foreign")
        elif case == "input_content":
            core.events[0].payload["content"] = "foreign"
        elif case == "input_principal":
            core.events[0].payload["canonical_user_ref"] = "foreign"
        elif case in {"input_operator", "input_scope", "input_autonomy"}:
            key, value = {"input_operator": ("operator_identity_ref", "foreign"),
                          "input_scope": ("surface_capability_scope", ["execute"]),
                          "input_autonomy": ("max_autonomy_level", "execute")}[case]
            core.events[0].payload[key] = value
        elif case == "decision":
            core.events[1].payload["decision"] = "block"
        elif case == "generation":
            core.events[2].payload["generative_status"] = "accepted"
        elif case == "binding_hash":
            core.events[3].payload["conversation_readback"]["response_text_sha256"] = "0" * 64
        elif case == "binding_missing":
            del core.events[3].payload["conversation_readback"]
        else:
            response.events = []

    value, _ = service(tmp_path, mutate=mutate)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "failed" and result["result"] is None
    assert result["error_code"] == "analysis_outcome_unknown"


@pytest.mark.parametrize("clock", [lambda: float("nan"), lambda: float("inf"), lambda: True])
def test_invalid_clock_refuses_ticket(tmp_path, clock):
    value = module.AnalysisService(tmp_path / "owned", clock=clock)
    rejected(lambda: value.issue_ticket(IDENTITY), "analysis_invalid")


def test_backward_clock_and_fresh_runtime_requirement(tmp_path):
    now = [100.0]
    value = module.AnalysisService(tmp_path / "owned", clock=lambda: now[0])
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    now[0] = 99.0
    rejected(lambda: value.get_result(IDENTITY, ticket), "analysis_invalid")
    runtime = tmp_path / "nonempty"
    runtime.mkdir()
    (runtime / "do-not-open.db").write_bytes(b"owned marker; not a human store")
    rejected(lambda: module.AnalysisService(runtime), "analysis_invalid")
    rejected(lambda: module.AnalysisService(Path("relative")), "analysis_invalid")
    assert (runtime / "do-not-open.db").read_bytes() == b"owned marker; not a human store"


def test_actual_simultaneous_replay_dispatches_only_once(tmp_path):
    gate, barrier = Event(), Barrier(8)
    value, core = service(tmp_path, gate=gate)
    ticket = value.issue_ticket(IDENTITY)["ticket"]

    def submit():
        barrier.wait(timeout=3)
        try:
            return value.submit(IDENTITY, ticket, QUERY)["status"]
        except LocalWebRejected as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(lambda _: submit(), range(8)))
    assert outcomes.count("running") == 1
    assert outcomes.count("analysis_ticket_refused") == 7
    assert core.entered.wait(2) and len(core.calls) == 1
    gate.set()
    assert finish(value, IDENTITY, ticket)["status"] == "completed"


def test_actual_simultaneous_sessions_have_no_queued_core_calls(tmp_path):
    gate, barrier = Event(), Barrier(4)
    value, core = service(tmp_path, gate=gate)
    identities = [replace(IDENTITY, session_ref=f"session://owned-parallel-{n}") for n in range(4)]
    tickets = [value.issue_ticket(identity)["ticket"] for identity in identities]

    def submit(index):
        barrier.wait(timeout=3)
        try:
            return value.submit(identities[index], tickets[index], QUERY)["status"]
        except LocalWebRejected as error:
            return error.code

    with ThreadPoolExecutor(max_workers=4) as executor:
        outcomes = list(executor.map(submit, range(4)))
    assert outcomes.count("running") == 1 and outcomes.count("analysis_busy") == 3
    assert core.entered.wait(2) and len(core.calls) == 1
    gate.set()
    value._worker.join(5)
    assert len(core.calls) == 1
    assert sum(value.get_result(identity, ticket)["status"] == "completed"
               for identity, ticket in zip(identities, tickets)) == 1


def test_revoked_issued_ticket_never_constructs_core(tmp_path):
    calls = []
    value = module.AnalysisService(tmp_path / "owned", core_factory=lambda path: calls.append(path))
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.revoke(IDENTITY)
    rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_ticket_refused")
    assert calls == [] and not value.runtime_dir.exists()


def test_factory_failure_and_worker_start_failure_have_fixed_unknown_outcome(tmp_path, monkeypatch):
    def failed_factory(_path):
        raise RuntimeError("/home/private.db; token=synthetic")

    value = module.AnalysisService(tmp_path / "owned", core_factory=failed_factory)
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    value.submit(IDENTITY, ticket, QUERY)
    result = finish(value, IDENTITY, ticket)
    assert result["status"] == "failed" and result["error_code"] == "analysis_outcome_unknown"
    assert result["result"] is None and "private" not in repr(result)
    next_ticket = value.issue_ticket(IDENTITY)["ticket"]
    monkeypatch.setattr(module.Thread, "start", lambda _: (_ for _ in ()).throw(RuntimeError()))
    result = value.submit(IDENTITY, next_ticket, QUERY)
    assert result["status"] == "failed" and result["error_code"] == "analysis_outcome_unknown"
    assert value._active is None


@pytest.mark.parametrize("identity", [None, NS(), replace(IDENTITY, principal_ref="a\u200bb"),
                                      replace(IDENTITY, canonical_user_ref="bad user")])
def test_invalid_identity_fails_fixed_before_ticket_creation(tmp_path, identity):
    value, core = service(tmp_path)
    rejected(lambda: value.issue_ticket(identity), "analysis_invalid")
    assert not value._tickets and not core.calls


def test_expired_unsubmitted_ticket_never_runs_and_consumed_ticket_is_not_evicted(tmp_path):
    now, core = [100.0], _Core()
    value = module.AnalysisService(tmp_path / "owned", core_factory=lambda _: core,
                                   clock=lambda: now[0])
    ticket = value.issue_ticket(IDENTITY)["ticket"]
    now[0] = 220.0
    rejected(lambda: value.submit(IDENTITY, ticket, QUERY), "analysis_ticket_refused")
    assert value.get_result(IDENTITY, ticket)["error_code"] == "analysis_expired"
    assert ticket in value._tickets and not core.calls
