"""Local, one-shot human review of supplied evidence; no I/O or Core authority."""

from __future__ import annotations

import math
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from threading import RLock

from shared.reviewed_knowledge import (
    KnowledgeReviewBinding,
    ReviewedKnowledgeContext,
    context_fingerprint,
    validate_binding,
    validate_context,
    validate_source,
)

from .research import INPUT_SCHEMA, build_offline_research_dossier

MAX_EVENTS = 256
MAX_DEADLINE_SECONDS = 120
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


def _utc_now():
    return datetime.now(UTC).isoformat()


def _number(value):
    if type(value) not in (int, float):
        raise ValueError()
    number = float(value)
    if not math.isfinite(number):
        raise ValueError()
    return number


@dataclass(frozen=True, slots=True)
class KnowledgeReviewTicket:
    generation: int
    binding: KnowledgeReviewBinding = field(repr=False)
    deadline: float = field(repr=False)


@dataclass(frozen=True, slots=True)
class KnowledgeReviewView:
    start: int
    end: int
    quote: str = field(repr=False)
    fingerprint: str = field(repr=False)
    revision: int
    authority: str = "none"
    origin_status: str = "declared_unverified"


class LocalKnowledgeReview:
    """One request-bound review. Cancellation after consumption cannot unsend Core work."""

    def __init__(self, binding, *, clock=time.monotonic, wall_clock=_utc_now):
        try:
            self._binding = validate_binding(binding)
            if not callable(clock) or not callable(wall_clock):
                raise ValueError()
        except Exception:
            raise ValueError("invalid_knowledge_review") from None
        self._clock, self._wall_clock = clock, wall_clock
        self._callbacks = (clock, wall_clock)
        self._lock = RLock()
        self._busy = False
        self._last_time = -math.inf
        self._last_wall = None
        self._generation = 0
        self._consent = False
        self._ticket = self._candidate = self._context = self._expected = self._deadline = None
        self._state, self._error = "idle", None
        self._events = []

    def __repr__(self):
        return "LocalKnowledgeReview(local_text_only=True, authority='none')"

    def _emit(self, name):
        self._events.append({"name": name, "generation": self._generation, "state": self._state})
        del self._events[:-MAX_EVENTS]

    def _invalidate(self, state, error=None):
        self._generation += 1
        self._ticket = self._candidate = self._context = self._expected = self._deadline = None
        self._state, self._error = state, error

    def _fail(self, code):
        self._invalidate("error", code)
        self._emit("knowledge_review_refused")
        raise ValueError(code) from None

    def _scope(self, binding):
        try:
            return validate_binding(binding) == self._binding
        except Exception:
            return False

    @contextmanager
    def _operation(self):
        with self._lock:
            if self._busy:
                self._fail("knowledge_review_reentrant")
            self._busy = True
            try:
                yield
            finally:
                self._busy = False

    def _tick(self, generation):
        try:
            clock, wall_clock = self._callbacks
            now = _number(clock())
            if (now < self._last_time or self._clock is not clock
                    or self._wall_clock is not wall_clock):
                raise ValueError()
        except Exception:
            self._fail("invalid_knowledge_clock")
        if generation != self._generation:
            raise ValueError("knowledge_review_invalidated") from None
        self._last_time = now
        return now

    def _times(self):
        generation = self._generation
        self._tick(generation)
        try:
            clock, wall_clock = self._callbacks
            stamp = wall_clock()
            if type(stamp) is not str or len(stamp) > 64 or not _STAMP.fullmatch(stamp):
                raise ValueError()
            wall = datetime.fromisoformat(stamp).astimezone(UTC)
            if (self._last_wall is not None and wall < self._last_wall
                    or self._clock is not clock or self._wall_clock is not wall_clock):
                raise ValueError()
        except Exception:
            self._fail("invalid_knowledge_wall_clock")
        if generation != self._generation:
            raise ValueError("knowledge_review_invalidated") from None
        self._last_wall = wall
        return self._tick(generation), stamp

    def _ticket_matches(self, ticket):
        try:
            return (type(ticket.generation) is int and ticket.generation == self._generation
                    and type(ticket.deadline) is float and ticket.deadline == self._deadline
                    and validate_binding(ticket.binding) == self._binding)
        except Exception:
            return False

    def _current(self, ticket, states):
        if (type(ticket) is not KnowledgeReviewTicket or ticket is not self._ticket
                or not self._consent or self._state not in states):
            return None
        if not self._ticket_matches(ticket):
            self._fail("invalid_knowledge_ticket")
        now, stamp = self._times()
        if not self._ticket_matches(ticket):
            self._fail("invalid_knowledge_ticket")
        if now >= self._deadline:
            self._invalidate("expired", "deadline_exceeded")
            self._emit("knowledge_review_expired")
            return None
        try:
            validate_context(self._candidate, binding=self._binding, as_of=stamp)
        except Exception:
            self._fail("invalid_knowledge_source")
        return stamp

    def consent(self, binding, granted=True):
        with self._lock:
            if not self._scope(binding) or type(granted) is not bool:
                raise ValueError("knowledge_consent_scope_mismatch") from None
            self._invalidate("consented" if granted else "revoked")
            self._consent = granted
            self._emit("knowledge_consent_granted" if granted else "knowledge_consent_revoked")
            return granted

    def propose(self, source, query, *, binding, deadline_seconds=120):
        with self._operation():
            if not self._scope(binding) or not self._consent:
                self._fail("knowledge_review_requires_scoped_consent")
            try:
                seconds = _number(deadline_seconds)
                if not 0 < seconds <= MAX_DEADLINE_SECONDS:
                    raise ValueError()
                source = validate_source(source)
            except Exception:
                self._fail("invalid_knowledge_proposal")
            now = self._tick(self._generation)
            _, stamp = self._times()
            generation = self._generation
            try:
                source = validate_source(source, as_of=stamp)
                dossier = build_offline_research_dossier({
                    "schema_version": INPUT_SCHEMA, "query": query, "as_of": stamp,
                    "sources": [{"source_ref": source.source_ref, "text": source.text,
                                 "observed_at": source.observed_at,
                                 "expires_at": source.expires_at}],
                }, include_content=True)
                candidates = dossier["review_candidates"]
                if not candidates:
                    raise ValueError()
                chosen = candidates[0]
                if (chosen["source_ref"] != source.source_ref
                        or chosen["text_sha256"] != source.content_sha256):
                    raise ValueError()
                span = chosen["span"]
                candidate = validate_context(ReviewedKnowledgeContext(
                    self._binding, query, source, span["start"], span["end"], chosen["quote"],
                    stamp, 1,
                ), binding=self._binding, as_of=stamp)
            except Exception:
                self._fail("invalid_knowledge_proposal")
            finished, final_stamp = self._times()
            if generation != self._generation or not self._consent:
                raise ValueError("knowledge_review_invalidated") from None
            if finished >= now + seconds or not math.isfinite(now + seconds):
                self._fail("knowledge_deadline_exceeded")
            try:
                validate_context(candidate, as_of=final_stamp)
            except Exception:
                self._fail("invalid_knowledge_source")
            self._invalidate("proposed")
            self._deadline = float(now + seconds)
            self._ticket = KnowledgeReviewTicket(
                self._generation, validate_binding(self._binding), self._deadline,
            )
            self._candidate = candidate
            self._emit("knowledge_review_required")
            return self._ticket

    def _view(self):
        value = self._candidate
        return KnowledgeReviewView(value.start, value.end, value.quote,
                                   context_fingerprint(value), value.revision)

    def review(self, ticket, *, binding):
        with self._operation():
            if not self._scope(binding):
                return None
            stamp = self._current(ticket, ("proposed", "reviewed"))
            if stamp is None:
                return None
            if self._state == "proposed":
                self._candidate = validate_context(
                    replace(self._candidate, reviewed_at=stamp),
                    binding=self._binding, as_of=stamp,
                )
            self._state = "reviewed"
            self._emit("knowledge_candidate_reviewed")
            return self._view()

    def select(self, ticket, *, binding, start, end):
        with self._operation():
            if not self._scope(binding):
                return None
            stamp = self._current(ticket, ("proposed", "reviewed"))
            if stamp is None:
                return None
            old = self._candidate
            try:
                if type(start) is not int or type(end) is not int:
                    raise ValueError()
                self._candidate = validate_context(ReviewedKnowledgeContext(
                    self._binding, old.query, old.source, start, end, old.source.text[start:end],
                    stamp, old.revision + 1,
                ), binding=self._binding, as_of=stamp)
            except Exception:
                self._fail("invalid_knowledge_selection")
            self._state = "reviewed"
            self._emit("knowledge_candidate_selected")
            return self._view()

    def confirm(self, ticket, *, binding, fingerprint, revision):
        with self._operation():
            if not self._scope(binding):
                return None
            stamp = self._current(ticket, ("reviewed",))
            if stamp is None:
                return None
            if (type(fingerprint) is not str or fingerprint != context_fingerprint(self._candidate)
                    or type(revision) is not int or revision != self._candidate.revision):
                return None
            self._context = validate_context(self._candidate, binding=self._binding, as_of=stamp)
            self._expected = context_fingerprint(self._context)
            self._state = "confirmed"
            self._emit("knowledge_context_confirmed")
            return self._context

    def take_context(self, context):
        """Consume before Core dispatch; no external dispatch is performed here."""
        with self._operation():
            if context is not self._context or self._context is None:
                return False
            stamp = self._current(self._ticket, ("confirmed",))
            if stamp is None:
                return False
            try:
                validated = validate_context(context, binding=self._binding,
                                             query=self._candidate.query, as_of=stamp)
                if context_fingerprint(validated) != self._expected:
                    raise ValueError()
            except Exception:
                self._fail("invalid_knowledge_context")
            self._invalidate("handed_off")
            self._emit("knowledge_context_handed_off")
            return True

    def cancel(self, binding):
        with self._lock:
            if not self._scope(binding):
                raise ValueError("knowledge_cancel_scope_mismatch") from None
            self._invalidate("cancelled")
            self._emit("knowledge_review_cancelled")

    def snapshot(self):
        with self._lock:
            return {"mode": "local_knowledge_review", "state": self._state,
                    "review_consent": self._consent, "generation": self._generation,
                    "revision": self._candidate.revision if self._candidate else None,
                    "error_code": self._error, "authority": "none",
                    "origin_status": "declared_unverified", "network_io": False}

    def events(self):
        with self._lock:
            return tuple(dict(event) for event in self._events)
