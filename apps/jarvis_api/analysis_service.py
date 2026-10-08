"""Single-flight local Core composition with ephemeral, server-owned tickets.

Revocation/expiry fences delivery, not a rollback of an already-running Core
commit. A failed outcome may have been persisted and is never rerun. Injected
factories are a test seam, not a promoted provider or execution capability.
"""

from __future__ import annotations

import json
import re
import stat
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite
from pathlib import Path
from threading import Event, RLock, Thread
from uuid import uuid4

from apps.jarvis_api.contracts import (
    ANALYSIS_GENERATIVE_SCHEMA,
    ANALYSIS_SCHEMA,
    GENERATIVE_ERROR_CODES,
    MAX_QUERY_CHARACTERS,
    MAX_RESPONSE_CHARACTERS,
    MAX_TICKETS,
    TICKET_PATTERN,
    TICKET_SECONDS,
    LocalWebRejected,
    SessionIdentity,
)
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER
from shared.types import ChannelType, InputType, RequestId, SessionId

_NAMES = ("input_received", "governance_checked", "response_synthesized", "memory_recorded")
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")
_INTENT = re.compile(r"[a-z][a-z_]{0,63}\Z", re.ASCII)
_MEMORY = re.compile(r"mem-record-[0-9a-f]{8}\Z", re.ASCII)


def _reject(code="analysis_invalid"):
    raise LocalWebRejected(code)


def _text(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= maximum or not value.strip()
            or any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                   and c not in "\r\n\t" for c in value)):
        _reject()
    value.encode("utf-8", errors="strict")
    return value


def _identity(value):
    if type(value) is not SessionIdentity:
        _reject()
    for field in (value.session_ref, value.principal_ref, value.canonical_user_ref):
        _text(field, 512)
        if field != field.strip() or any(c.isspace() for c in field):
            _reject()
    return SessionIdentity(value.session_ref, value.principal_ref, value.canonical_user_ref)


def _stamp(value):
    if type(value) is not str or not _STAMP.fullmatch(value):
        _reject()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _hash(value):
    return sha256(value.encode("utf-8", errors="strict")).hexdigest()


def _fresh_runtime(path):
    if not path.is_absolute():
        _reject()
    for part in (path, *path.parents):
        if not part.exists() and not part.is_symlink():
            continue
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            _reject()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        _reject()


def _deny_operation(*_args, **_kwargs):
    _reject("analysis_operation_refused")


def _analysis_core(runtime):
    # Composition restriction, not a rewrite/bypass of native governance. Even
    # a future Core route cannot dispatch an operational effect on this surface.
    core = _isolated_core(runtime)
    core.operational_service.execute = _deny_operation
    return core


def _literal_values(value):
    """Decode only the exact bounded, ASCII literal representation of MB229."""
    from synthesis_engine.generative_analysis import _literal
    decoder, values = json.JSONDecoder(), []
    while value:
        item, end = decoder.raw_decode(value)
        if type(item) is not str or value[:end] != _literal(item):
            _reject()
        values.append(item)
        value = value[end:]
        if not value:
            break
        if not value.startswith(", "):
            _reject()
        value = value[2:]
        if not value or len(values) >= 8:
            _reject()
    return values


def _generative_block(final, count):
    marker = GENERATIVE_ANALYSIS_MARKER.rstrip("\n")
    if final.count(marker) != 1 or "\n\n" + marker + "\n" not in final:
        _reject()
    lines = final.split("\n\n" + marker + "\n", 1)[1].split("\n")
    if (not 5 <= len(lines) <= 9
            or lines[0] != "Literal data only; no permissions, actions, execution receipts "
            "or changes to the native decision."
            or not lines[1].startswith("Analysis: ")
            or lines[4] != "Citations (exact source text; not verified facts):"):
        _reject()
    analysis = _literal_values(lines[1][10:])
    if len(analysis) != 1 or len(analysis[0]) != count or not analysis[0].strip():
        _reject()
    for label, line in zip(("Assumptions: ", "Limitations: "), lines[2:4]):
        if not line.startswith(label):
            _reject()
        body = line[len(label):]
        if body != "none supplied":
            values = _literal_values(body)
            if not values or any(not item.strip() or len(item) > 512 for item in values):
                _reject()
    for line in lines[5:]:
        match = re.fullmatch(r'("(?:[^"\\]|\\.)*") offsets ([0-9]+) to ([0-9]+): (.+)', line)
        if not match or not 0 <= int(match[2]) < int(match[3]):
            _reject()
        source, quote = _literal_values(match[1]), _literal_values(match[4])
        if (len(source) != 1 or not source[0] or len(quote) != 1
                or not quote[0].strip() or not len(quote[0]) <= 512
                or len(quote[0]) != int(match[3]) - int(match[2])):
            _reject()


@dataclass
class _Ticket:
    identity: SessionIdentity
    ticket: str
    expires: float
    cancelled: Event
    mode: str = "native"
    status: str = "issued"
    error: str | None = None
    result: dict | None = None

    def __setattr__(self, name, value):
        if name == "mode" and name in self.__dict__:
            raise AttributeError("ticket_mode_immutable")
        super().__setattr__(name, value)


class AnalysisService:
    """One active Core call globally, with bounded in-memory ticket history."""

    def __init__(self, runtime_dir: Path, *, core_factory=None, clock=time.monotonic,
                 generative_profile=None):
        try:
            self.runtime_dir = Path(runtime_dir)
            _fresh_runtime(self.runtime_dir)
            if not callable(clock) or (core_factory is not None and not callable(core_factory)):
                _reject()
        except Exception:
            _reject()
        self._factory = core_factory if core_factory is not None else _analysis_core
        self._generative_profile = generative_profile
        self._profile_binding = None
        if generative_profile is not None:
            from apps.jarvis_api.generative_profile import GenerativeProfile
            if type(generative_profile) is not GenerativeProfile:
                _reject("generative_unavailable")
            try:
                self._profile_binding = (generative_profile.model, generative_profile.provider_id,
                                         generative_profile.evidence_mode,
                                         generative_profile.timeout_seconds,
                                         generative_profile.port_for,
                                         generative_profile._snapshot())
                self._profile_fence()
            except Exception:
                _reject("generative_unavailable")
        self._clock, self._last = clock, None
        self._lock = RLock()
        self._tickets, self._current, self._identities = {}, {}, {}
        self._revoked = set()
        self._closed, self._core, self._active, self._worker = False, None, None, None

    def _now(self):
        try:
            now = self._clock()
            if (type(now) not in {int, float} or not isfinite(now)
                    or (self._last is not None and now < self._last)):
                _reject()
            self._last = now
            return now
        except Exception:
            _reject()

    def _bound(self, identity):
        identity = _identity(identity)
        if self._closed:
            _reject("analysis_closed")
        if (identity.session_ref in self._revoked
                or self._identities.get(identity.session_ref, identity) != identity):
            _reject("analysis_ticket_refused")
        return identity

    def _expire(self, job, now):
        if now >= job.expires:
            job.cancelled.set()
            job.status, job.error, job.result = "failed", "analysis_expired", None

    @staticmethod
    def _envelope(job):
        schema = ANALYSIS_GENERATIVE_SCHEMA if job.mode == "generative" else ANALYSIS_SCHEMA
        return {"schema_version": schema, "status": job.status, "ticket": job.ticket,
                "error_code": job.error, "result": dict(job.result) if job.result else None}

    def _profile_fence(self):
        profile, binding = self._generative_profile, self._profile_binding
        if profile is None or binding is None:
            _reject("generative_unavailable")
        try:
            from apps.jarvis_api.generative_profile import GenerativeProfile
            if (type(profile) is not GenerativeProfile
                    or (profile.model, profile.provider_id, profile.evidence_mode,
                        profile.timeout_seconds, profile.port_for) != binding[:5]
                    or binding[1] != "responses_plan"
                    or binding[2] not in {"live", "injected_transport"}
                    or type(binding[3]) not in {int, float} or not isfinite(binding[3])
                    or not 0 < binding[3] <= 20 or not callable(binding[4])):
                _reject("generative_unavailable")
            profile._fence(binding[5])
        except Exception:
            _reject("generative_unavailable")

    def _consent(self, consent):
        if consent is not True:
            _reject("analysis_invalid")
        self._profile_fence()

    def _lookup(self, identity, ticket):
        identity = self._bound(identity)
        if type(ticket) is not str or not TICKET_PATTERN.fullmatch(ticket):
            _reject("analysis_ticket_refused")
        job = self._tickets.get(ticket)
        if job is None or job.identity != identity:
            _reject("analysis_ticket_refused")
        self._expire(job, self._now())
        return job

    def issue_ticket(self, identity: SessionIdentity):
        return self._issue(identity, "native")

    def issue_generative_ticket(self, identity: SessionIdentity, *, consent=False):
        with self._lock:
            self._consent(consent)
            return self._issue(identity, "generative")

    def _issue(self, identity, mode):
        with self._lock:
            identity, now = self._bound(identity), self._now()
            previous = self._tickets.get(self._current.get(identity.session_ref))
            if previous is not None:
                self._expire(previous, now)
                if previous.status in {"issued", "running"}:
                    _reject("analysis_busy")
            if len(self._tickets) >= MAX_TICKETS:
                _reject("analysis_busy")
            ticket = "web-request-" + uuid4().hex
            if ticket in self._tickets:
                _reject("analysis_busy")
            job = _Ticket(identity, ticket, now + TICKET_SECONDS, Event(), mode)
            self._tickets[ticket] = job
            self._identities[identity.session_ref] = identity
            self._current[identity.session_ref] = ticket
            return self._envelope(job)

    def current_ticket(self, identity: SessionIdentity):
        with self._lock:
            identity, now = self._bound(identity), self._now()
            job = self._tickets.get(self._current.get(identity.session_ref))
            if job is None:
                return None
            self._expire(job, now)
            return job.ticket if now < job.expires else None

    def submit(self, identity: SessionIdentity, ticket, query):
        return self._submit(identity, ticket, query, "native")

    def submit_generative(self, identity: SessionIdentity, ticket, query, *, consent=False):
        with self._lock:
            self._consent(consent)
            return self._submit(identity, ticket, query, "generative")

    def _submit(self, identity, ticket, query, mode):
        with self._lock:
            job = self._lookup(identity, ticket)
            if job.mode != mode:
                _reject("analysis_ticket_refused")
            _text(query, MAX_QUERY_CHARACTERS)
            if job.status != "issued":
                _reject("analysis_ticket_refused")
            if self._active is not None:
                _reject("analysis_busy")
            job.status, self._active = "running", job.ticket
            envelope = self._envelope(job)
            self._worker = Thread(target=self._run, args=(job, query), daemon=True,
                                  name="jarvis-local-analysis")
            try:
                self._worker.start()
            except Exception:
                self._active = None
                job.status, job.error = "failed", "analysis_outcome_unknown"
                return self._envelope(job)
            return envelope

    def get_result(self, identity: SessionIdentity, ticket):
        with self._lock:
            return self._envelope(self._lookup(identity, ticket))

    def revoke(self, identity: SessionIdentity):
        with self._lock:
            identity = _identity(identity)
            if self._identities.get(identity.session_ref) != identity:
                return
            self._revoked.add(identity.session_ref)
            self._current.pop(identity.session_ref, None)
            for job in self._tickets.values():
                if job.identity == identity:
                    job.cancelled.set()
                    job.status, job.error, job.result = "failed", "analysis_outcome_unknown", None

    def close(self):
        with self._lock:
            self._closed = True
            for job in self._tickets.values():
                job.cancelled.set()
                job.status, job.error, job.result = "failed", "analysis_outcome_unknown", None
            worker = self._worker
        if worker is not None and worker.is_alive():
            worker.join(timeout=0.2)

    def _run(self, job, query):
        result = None
        original_engine, composed = None, False
        try:
            with self._lock:
                self._expire(job, self._now())
                if job.cancelled.is_set() or self._closed:
                    return
            if self._core is None:
                _fresh_runtime(self.runtime_dir)
                self._core = self._factory(self.runtime_dir)
            contract = InputContract(
                RequestId(job.ticket), SessionId(job.identity.session_ref), ChannelType.WEB,
                InputType.TEXT, query, datetime.now(UTC).isoformat(),
                user_id=job.identity.canonical_user_ref,
                surface_id="surface://local-analysis", surface_kind="web",
                surface_session_id=job.identity.session_ref, surface_capability_scope=[],
                operator_identity_ref=job.identity.principal_ref,
                canonical_user_ref=job.identity.canonical_user_ref,
                requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
            )
            with self._lock:
                self._expire(job, self._now())
                if job.cancelled.is_set() or self._closed:
                    return
            if job.mode == "generative":
                from synthesis_engine.engine import SynthesisEngine
                self._profile_fence()
                binding = self._profile_binding
                port = binding[4](job.cancelled)
                self._profile_fence()
                original_engine = getattr(self._core, "synthesis_engine", None)
                self._core.synthesis_engine = SynthesisEngine(
                    generative_port=port, generative_model=binding[0],
                    generative_provider_id=binding[1], generative_evidence_mode=binding[2],
                    generative_timeout_seconds=binding[3], generative_cancellation=job.cancelled,
                )
                composed = True
            response = self._core.handle_input(contract)
            if job.mode == "generative":
                self._profile_fence()
            result = self._readback(response, contract, mode=job.mode)
        except Exception:
            result = None
        finally:
            if composed:
                if original_engine is None:
                    del self._core.synthesis_engine
                else:
                    self._core.synthesis_engine = original_engine
            with self._lock:
                try:
                    self._expire(job, self._now())
                    valid = not job.cancelled.is_set() and not self._closed
                except Exception:
                    valid = False
                if valid and result is not None:
                    job.status, job.result, job.error = "completed", result, None
                elif job.error != "analysis_expired":
                    job.status, job.result, job.error = "failed", None, "analysis_outcome_unknown"
                self._active = None

    def _readback(self, response, contract, *, mode="native"):
        """Use initialized Core repository seams, never quiescent DB export."""
        if (response.request_id != contract.request_id or response.session_id != contract.session_id
                or any(getattr(response, key, None) is not None for key in (
                    "operation_result", "operation_dispatch", "adapter_grant",
                    "adapter_grant_claim", "action_confirmation_claim",
                    "action_confirmation_challenge"))):
            _reject()
        query, final = contract.content, _text(response.response_text, MAX_RESPONSE_CHARACTERS)
        intent = response.intent
        decision = response.governance_decision.decision.value
        if (type(intent) is not str or not _INTENT.fullmatch(intent)
                or decision not in {"allow", "block", "defer_for_validation"}):
            _reject()
        record = response.memory_record
        if (record.record_type != "interaction_turn" or record.source_service != "memory-service"
                or record.session_id != contract.session_id or record.mission_id is not None
                or record.user_id != contract.user_id
                or record.payload.get("request_content") != query
                or record.payload.get("response_text") != final
                or record.payload.get("intent") != intent
                or record.payload.get("governance_decision") != decision
                or not _MEMORY.fullmatch(record.memory_record_id)):
            _reject()
        recorded = _stamp(record.timestamp)
        turns = self._core.memory_service.repository.fetch_recent_turns(
            contract.session_id, MAX_TICKETS + 1,
        )
        if len(turns) > MAX_TICKETS:
            _reject()
        selected = [turn for turn in turns if turn.timestamp == record.timestamp]
        if len(selected) != 1:
            _reject()
        turn = selected[0]
        if (turn.session_id != contract.session_id or turn.user_id != contract.user_id
                or turn.mission_id is not None or turn.intent != intent
                or turn.request_content != query or turn.response_text != final):
            _reject()
        repository = self._core.observability_service.repository
        rows = {}
        for filters in ({"request_id": contract.request_id},
                        {"correlation_id": contract.request_id}):
            events = repository.list_events(limit=5, event_names=_NAMES, **filters)
            if len(events) > 4:
                _reject()
            for event in events:
                if event.event_id in rows and rows[event.event_id] != event:
                    _reject()
                rows[event.event_id] = event
        if len(rows) != 4 or {row.event_name for row in rows.values()} != set(_NAMES):
            _reject()
        envelopes = {row.event_name: row for row in rows.values()}
        for event in envelopes.values():
            if (event.request_id != contract.request_id
                    or event.correlation_id != contract.request_id
                    or event.session_id != contract.session_id or event.mission_id is not None
                    or event.source_service != "orchestrator-service"
                    or type(event.payload) is not dict):
                _reject()
        timeline = [_stamp(envelopes[name].timestamp) for name in _NAMES]
        if not timeline[0] <= timeline[1] <= timeline[2] <= recorded <= timeline[3]:
            _reject()
        payloads = {name: event.payload for name, event in envelopes.items()}
        received, synthesis = payloads["input_received"], payloads["response_synthesized"]
        if (received.get("content") != query
                or received.get("canonical_user_ref") != contract.user_id
                or received.get("operator_identity_ref") != contract.operator_identity_ref
                or received.get("surface_id") != contract.surface_id
                or received.get("surface_kind") != "web"
                or received.get("surface_session_id") != contract.session_id
                or received.get("surface_capability_scope") != []
                or received.get("requested_autonomy_level") != "assist_only"
                or received.get("max_autonomy_level") != "assist_only"
                or payloads["governance_checked"].get("decision") != decision
                or synthesis.get("intent") != intent):
            _reject()
        generation = {key: synthesis.get(key) for key in (
            "generative_status", "generative_error_code", "generative_evidence_mode",
            "generative_analysis_characters")}
        status, code, evidence, count = generation.values()
        if mode == "native":
            if (status != "disabled" or code is not None or evidence is not None
                    or type(count) is not int or count != 0):
                _reject()
        else:
            if type(status) is not str or status not in {"accepted", "rejected", "withheld"}:
                _reject()
            if status == "accepted":
                if (decision != "allow" or code is not None
                        or type(evidence) is not str or evidence != self._profile_binding[2]
                        or type(count) is not int or not 1 <= count <= 4000):
                    _reject()
                _generative_block(final, count)
            elif (type(code) is not str or code not in GENERATIVE_ERROR_CODES
                    or (status == "withheld" and code not in {
                        "scope_denied", "reviewed_source_invalid"})
                    or type(count) is not int or count != 0 or evidence is not None
                    or GENERATIVE_ANALYSIS_MARKER.rstrip("\n") in final):
                _reject()
        memory = payloads["memory_recorded"]
        expected = {"schema_version": "jarvis-conversation-readback-v1",
                    "record_timestamp": record.timestamp,
                    "principal_sha256": _hash(contract.user_id),
                    "request_content_sha256": _hash(query), "response_text_sha256": _hash(final)}
        if (memory.get("memory_record_id") != record.memory_record_id
                or memory.get("record_type") != "interaction_turn"
                or memory.get("conversation_readback") != expected):
            _reject()
        records = repository.list_events(limit=MAX_TICKETS + 1, event_names=("memory_recorded",))
        if (len(records) > MAX_TICKETS or any(type(event.payload) is not dict for event in records)
                or sum(event.payload.get("memory_record_id") == record.memory_record_id
                       for event in records) != 1):
            _reject()
        # Exactly the correlated persisted events must also be the events the
        # native call returned. A forged response cannot borrow a different trail.
        returned = [event for event in response.events if event.event_name in _NAMES]
        if len(returned) != 4 or any(event not in returned for event in envelopes.values()):
            _reject()
        result = {"query": query, "response_text": final, "intent": intent,
                "governance_decision": decision, "memory_record_ref": record.memory_record_id,
                "timestamp": record.timestamp, "evidence_mode": "core_local",
                  "generative_status": status, "authority": "none"}
        if mode == "generative":
            result.update(generation)
        return result
