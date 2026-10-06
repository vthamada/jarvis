"""Local ASR draft review, with no audio I/O, inference, Core call or authority.

The caller supplies a document and its digest through trusted composition. That
digest is a read-only source binding, not a file path, authentication, speaker
identity or evidence that a model actually ran. Confirmation only returns text;
the sovereign Core still owns interpretation, governance and final synthesis.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import unicodedata
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from apps.jarvis_voice.harness import VoiceIdentity, VoiceRequest
from shared.contracts import SurfaceIdentityContract

MAX_TEXT_LENGTH = 4_000
MAX_SEGMENTS = 1_000
MAX_EVENTS = 256
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object) -> str:
    if (
        type(value) is not str
        or not 1 <= len(value) <= MAX_TEXT_LENGTH
        or not value.strip()
        or any(
            unicodedata.category(char) in ("Cc", "Cf", "Cs") and char not in "\n\r\t"
            for char in value
        )
    ):
        raise ValueError("invalid_transcript_text")
    return value


def _number(value: object) -> float:
    if type(value) not in (int, float):
        raise ValueError("invalid_transcript_time")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError("invalid_transcript_time") from None
    if not math.isfinite(number):
        raise ValueError("invalid_transcript_time")
    return number


@dataclass(frozen=True)
class TranscriptSegment:
    start_seconds: float
    end_seconds: float
    timestamps_estimated: bool


@dataclass(frozen=True)
class TranscriptReviewTicket:
    request_id: str
    generation: int
    identity: VoiceIdentity = field(repr=False)
    deadline: float


@dataclass(frozen=True)
class TranscriptReviewView:
    text: str = field(repr=False)
    candidate_hash: str = field(repr=False)
    revision: int
    source_sha256: str = field(repr=False)
    segments: tuple[TranscriptSegment, ...]
    audio_duration_seconds: float
    language: str = "Portuguese"
    concatenation_method: str = "exact_segment_texts_joined_with_newline"
    speaker_identification: bool = False
    tool_authority: str = "none"


def _document(value: object) -> tuple[str, tuple[TranscriptSegment, ...], float]:
    if (
        type(value) is not dict
        or set(value) != {"review_required", "language", "audio_duration_seconds", "segments"}
        or value["review_required"] is not True
        or value["language"] != "Portuguese"
        or type(value["segments"]) is not list
        or not 1 <= len(value["segments"]) <= MAX_SEGMENTS
    ):
        raise ValueError("invalid_transcript_document")
    duration = _number(value["audio_duration_seconds"])
    if not 0 < duration <= 900:
        raise ValueError("invalid_transcript_duration")
    texts: list[str] = []
    segments: list[TranscriptSegment] = []
    total, previous_start = 0, 0.0
    for segment in value["segments"]:
        if (
            type(segment) is not dict
            or set(segment) != {"start_seconds", "end_seconds", "timestamps_estimated", "text"}
            or type(segment["timestamps_estimated"]) is not bool
        ):
            raise ValueError("invalid_transcript_segment")
        start, end = _number(segment["start_seconds"]), _number(segment["end_seconds"])
        if not previous_start <= start <= end <= duration:
            raise ValueError("invalid_transcript_time")
        text = _text(segment["text"])
        total += len(text) + (1 if texts else 0)
        if total > MAX_TEXT_LENGTH:
            raise ValueError("transcript_candidate_limit_exceeded")
        previous_start = start
        texts.append(text)
        segments.append(TranscriptSegment(start, end, segment["timestamps_estimated"]))
    return "\n".join(texts), tuple(segments), duration


class LocalTranscriptReview:
    """Single local review with lock-serialized consent, revisions and one-shot confirmation.

    Before handoff the Core port must atomically consume ``take_request``. After
    this boundary cancellation cannot retract an already handed-off request.
    These checks are not an authorization registry or a replacement for Core.
    """

    def __init__(
        self, *, identity: SurfaceIdentityContract,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._identity = VoiceIdentity.from_surface(identity)
        self._clock = clock
        self._lock = RLock()
        self._last_time = -math.inf
        self._generation = 0
        self._consent = False
        self._ticket: TranscriptReviewTicket | None = None
        self._view: TranscriptReviewView | None = None
        self._request: VoiceRequest | None = None
        self._state = "idle"
        self._error: str | None = None
        self._events: list[dict[str, object]] = []

    def __repr__(self) -> str:
        return "LocalTranscriptReview(local_text_only=True, authority='none')"

    def _scope(self, identity: SurfaceIdentityContract) -> bool:
        return VoiceIdentity.from_surface(identity) == self._identity

    def _emit(self, name: str) -> None:
        self._events.append({"name": name, "generation": self._generation, "state": self._state})
        del self._events[:-MAX_EVENTS]

    def _invalidate(self, state: str, error: str | None = None) -> None:
        self._generation += 1
        self._ticket = self._view = self._request = None
        self._state, self._error = state, error

    def _now(self) -> float:
        try:
            now = _number(self._clock())
            if now < self._last_time:
                raise ValueError("non_monotonic_clock")
        except Exception:
            self._invalidate("error", "invalid_clock")
            self._emit("transcript_review_refused")
            raise ValueError("invalid_transcript_clock") from None
        self._last_time = now
        return now

    def _current(self, ticket: TranscriptReviewTicket, states: tuple[str, ...]) -> bool:
        if (
            type(ticket) is not TranscriptReviewTicket
            or ticket != self._ticket
            or ticket.generation != self._generation
            or ticket.identity != self._identity
            or not self._consent
            or self._state not in states
        ):
            return False
        if self._now() >= ticket.deadline:
            self._invalidate("expired", "deadline_exceeded")
            self._emit("transcript_review_expired")
            return False
        return True

    def consent(self, identity: SurfaceIdentityContract, *, granted: bool) -> bool:
        with self._lock:
            if not self._scope(identity) or type(granted) is not bool:
                raise ValueError("transcript_consent_scope_mismatch")
            self._consent = granted
            if not granted:
                self._invalidate("revoked")
            self._emit("transcript_consent_granted" if granted else "transcript_consent_revoked")
            return granted

    def propose(
        self, document: object, *, identity: SurfaceIdentityContract,
        source_sha256: str, deadline_seconds: float = 120,
    ) -> TranscriptReviewTicket:
        with self._lock:
            if not self._scope(identity) or not self._consent:
                raise ValueError("transcript_review_requires_scoped_consent")
            seconds = _number(deadline_seconds)
            if not 0 < seconds <= 120:
                raise ValueError("invalid_transcript_deadline")
            if type(source_sha256) is not str or not _SHA256.fullmatch(source_sha256):
                raise ValueError("invalid_transcript_source_binding")
            text, segments, duration = _document(document)
            now = self._now()
            self._invalidate("proposed")
            self._ticket = TranscriptReviewTicket(
                "voice-" + uuid.uuid4().hex, self._generation, self._identity, now + seconds,
            )
            self._view = TranscriptReviewView(
                text, hashlib.sha256(text.encode("utf-8")).hexdigest(), 1,
                source_sha256, segments, duration,
            )
            self._emit("transcript_review_required")
            return self._ticket

    def review(
        self, ticket: TranscriptReviewTicket, *, identity: SurfaceIdentityContract,
    ) -> TranscriptReviewView | None:
        """Explicit local content display; never send the returned view to telemetry."""
        with self._lock:
            if not self._scope(identity) or not self._current(ticket, ("proposed", "reviewed")):
                return None
            self._state = "reviewed"
            self._emit("transcript_candidate_reviewed")
            return self._view

    def edit(
        self, ticket: TranscriptReviewTicket, text: str, *, identity: SurfaceIdentityContract,
    ) -> TranscriptReviewView | None:
        with self._lock:
            if not self._scope(identity) or not self._current(ticket, ("proposed", "reviewed")):
                return None
            text = _text(text)
            old = self._view
            self._view = TranscriptReviewView(
                text, hashlib.sha256(text.encode("utf-8")).hexdigest(), old.revision + 1,
                old.source_sha256, old.segments, old.audio_duration_seconds,
            )
            self._state = "reviewed"
            self._emit("transcript_candidate_edited")
            return self._view

    def confirm(
        self, ticket: TranscriptReviewTicket, *, identity: SurfaceIdentityContract,
        candidate_hash: str, revision: int,
    ) -> VoiceRequest | None:
        with self._lock:
            if not self._scope(identity) or not self._current(ticket, ("reviewed",)):
                return None
            if (
                type(revision) is not int or revision != self._view.revision
                or type(candidate_hash) is not str or candidate_hash != self._view.candidate_hash
            ):
                return None
            self._request = VoiceRequest(
                ticket.request_id, self._identity, self._view.text, ticket.deadline,
                authority="none", input_mode="reviewed_local_transcript",
            )
            self._view = None
            self._state = "confirmed"
            self._emit("transcript_text_confirmed")
            return self._request

    def is_current_request(self, request: VoiceRequest) -> bool:
        """Pre-handoff fence only; an already dispatched request cannot be unsent."""
        with self._lock:
            return request is self._request and self._current(self._ticket, ("confirmed",))

    def take_request(self, request: VoiceRequest) -> bool:
        """Atomically consume one exact request at the Core handoff boundary.

        Only a trusted Core port should call this before its real dispatch.
        Consent revoked before this lock acquisition refuses handoff; revocation
        afterwards cannot undo or cancel the now-owned Core request.
        """
        with self._lock:
            if request is not self._request or not self._current(self._ticket, ("confirmed",)):
                return False
            self._invalidate("handed_off")
            self._emit("transcript_request_handed_off")
            return True

    def cancel(self) -> None:
        with self._lock:
            self._invalidate("cancelled")
            self._emit("transcript_review_cancelled")

    def revoke(self, identity: SurfaceIdentityContract) -> None:
        self.consent(identity, granted=False)

    def switch_identity(self, identity: SurfaceIdentityContract) -> None:
        replacement = VoiceIdentity.from_surface(identity)
        with self._lock:
            self._identity, self._consent = replacement, False
            self._invalidate("idle")
            self._emit("transcript_identity_changed")

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "mode": "local_transcript_review", "state": self._state,
                "review_consent": self._consent, "generation": self._generation,
                "revision": self._view.revision if self._view else None,
                "error_code": self._error, "hardware_audio": False,
                "speaker_identification": False, "tool_authority": "none",
            }

    def events(self) -> tuple[dict[str, object], ...]:
        with self._lock:
            return tuple(dict(event) for event in self._events)
