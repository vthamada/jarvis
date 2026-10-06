"""Bounded, in-process voice fixture. Ports are trusted composition, not authority.

No microphone/speaker, networking, credential access, memory store or tool dispatch
exists here. A confirmed text request goes to the injected Core port; the Core
still owns interpretation, governance, memory and the final synthesis.
"""

from __future__ import annotations

import hashlib
import math
import re
import time
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Protocol

from shared.contracts import SurfaceIdentityContract

MAX_AUDIO_BYTES = 640_000
MAX_TEXT_LENGTH = 4_000
MAX_EVENTS = 256
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}\Z")


def _reference(value: object) -> str:
    if not isinstance(value, str) or not _REF.fullmatch(value):
        raise ValueError("invalid_voice_identity")
    return value


def _text(value: object) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= MAX_TEXT_LENGTH
        or not value.strip()
        or any(ord(char) < 32 and char not in "\n\r\t" for char in value)
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValueError("invalid_voice_text")
    return value


@dataclass(frozen=True)
class VoiceIdentity:
    surface_id: str
    surface_kind: str
    surface_session_id: str
    operator_identity_ref: str
    canonical_user_ref: str

    @classmethod
    def from_surface(cls, identity: SurfaceIdentityContract) -> VoiceIdentity:
        if not isinstance(identity, SurfaceIdentityContract):
            raise ValueError("invalid_voice_identity")
        if (
            identity.surface_kind != "voice"
            or type(identity.surface_capability_scope) is not list
            or identity.surface_capability_scope
            or identity.surface_continuity_status != "single_surface"
        ):
            raise ValueError("voice_scope_must_not_grant_authority")
        return cls(*(_reference(value) for value in (
            identity.surface_id, identity.surface_kind, identity.surface_session_id,
            identity.operator_identity_ref, identity.canonical_user_ref,
        )))


@dataclass(frozen=True)
class CaptureTicket:
    request_id: str
    generation: int
    identity: VoiceIdentity
    deadline: float


@dataclass(frozen=True)
class AudioFixture:
    data: bytes = field(repr=False)
    sample_rate: int = 16_000
    channels: int = 1
    sample_format: str = "pcm_s16le"
    evidence_mode: str = "synthetic_fixture"


@dataclass(frozen=True)
class Transcription:
    text: str = field(repr=False)
    status: str = "completed"
    evidence_mode: str = "fixture"


@dataclass(frozen=True)
class VoiceRequest:
    request_id: str
    identity: VoiceIdentity
    text: str = field(repr=False)
    deadline: float
    authority: str = "none"
    input_mode: str = "reviewed_voice_fixture"


@dataclass(frozen=True)
class FinalSynthesis:
    request_id: str
    identity: VoiceIdentity
    text: str = field(repr=False)
    synthesis_ref: str
    status: str = "completed"
    confirmed: bool = True
    evidence_mode: str = "fixture"


@dataclass(frozen=True)
class SpeechFixture:
    data: bytes = field(repr=False)
    request_id: str
    synthesis_ref: str
    status: str = "completed"
    evidence_mode: str = "synthetic_fixture"


class SttPort(Protocol):
    def transcribe(self, audio: AudioFixture, ticket: CaptureTicket) -> Transcription: ...


class CorePort(Protocol):
    def interact(self, request: VoiceRequest) -> FinalSynthesis: ...


class TtsPort(Protocol):
    def synthesize(self, final: FinalSynthesis, ticket: CaptureTicket) -> SpeechFixture: ...

    def stop(self, request_id: str) -> None: ...


def _validate_audio(audio: AudioFixture) -> None:
    if (
        not isinstance(audio, AudioFixture)
        or type(audio.data) is not bytes
        or not 2 <= len(audio.data) <= MAX_AUDIO_BYTES
        or len(audio.data) % 2
        or type(audio.sample_rate) is not int
        or audio.sample_rate != 16_000
        or type(audio.channels) is not int
        or audio.channels != 1
        or audio.sample_format != "pcm_s16le"
        or audio.evidence_mode != "synthetic_fixture"
    ):
        raise ValueError("invalid_audio_fixture")
    if not any(audio.data):
        raise ValueError("silence")


class VoiceHarness:
    """Single-turn fixture with generation fencing and explicit review/confirmation.

    Port calls are synchronous and outside the state lock. Cancellation/identity
    changes discard late results, but cannot retract a Core request already handed
    off or forcibly terminate a blocking provider. Deadlines are checked before and
    after calls; a real provider must implement its own bounded transport timeout.
    """

    def __init__(
        self, *, identity: SurfaceIdentityContract, stt: SttPort, tts: TtsPort,
        core: CorePort, clock: Callable[[], float] = time.monotonic,
    ):
        self._identity = VoiceIdentity.from_surface(identity)
        self.stt, self.tts, self.core = stt, tts, core
        self._clock = clock
        self._lock = RLock()
        self._generation = 0
        self._ticket: CaptureTicket | None = None
        self._consent = False
        self._state = "idle"
        self._transcript: str | None = None
        self._revision: str | None = None
        self._final: FinalSynthesis | None = None
        self._speech: SpeechFixture | None = None
        self._error: str | None = None
        self._events: list[dict[str, object]] = []
        self._last_time = -math.inf

    @property
    def identity(self) -> VoiceIdentity:
        return self._identity

    def _now(self) -> float:
        value = self._clock()
        if type(value) not in (int, float) or not math.isfinite(value) or value < self._last_time:
            raise ValueError("invalid_voice_clock")
        self._last_time = value
        return value

    def _emit(self, name: str) -> None:
        self._events.append({"name": name, "state": self._state, "generation": self._generation})
        del self._events[:-MAX_EVENTS]

    def _current(self, ticket: CaptureTicket, states: tuple[str, ...]) -> bool:
        if (
            not isinstance(ticket, CaptureTicket)
            or ticket != self._ticket
            or ticket.generation != self._generation
            or ticket.identity != self.identity
            or self._state not in states
            or not self._consent
        ):
            return False
        try:
            expired = self._now() >= ticket.deadline
        except Exception:
            self._fail("invalid_clock")
            return False
        if expired:
            self._fail("deadline_exceeded")
            return False
        return True

    def _fail(self, code: str) -> None:
        self._state, self._error = "error", code
        self._transcript, self._revision, self._speech = None, None, None
        self._emit("voice_refused")

    def consent(self, identity: SurfaceIdentityContract, *, granted: bool) -> bool:
        with self._lock:
            if VoiceIdentity.from_surface(identity) != self.identity or type(granted) is not bool:
                raise ValueError("voice_consent_identity_mismatch")
            if not granted:
                self._consent = False
            else:
                self._consent = True
                self._emit("voice_capture_consent_granted")
                return True
        self.cancel()
        with self._lock:
            self._emit("voice_consent_revoked")
        return False

    def start_capture(
        self, identity: SurfaceIdentityContract, *, deadline_seconds: float = 30,
    ) -> CaptureTicket:
        with self._lock:
            if VoiceIdentity.from_surface(identity) != self.identity or not self._consent:
                raise ValueError("voice_capture_requires_scoped_consent")
            if self._state in (
                "capturing", "transcribing", "submitting", "synthesizing", "playing",
            ):
                raise ValueError("voice_turn_busy")
            if (
                type(deadline_seconds) not in (int, float)
                or not math.isfinite(deadline_seconds)
                or not 0 < deadline_seconds <= 60
            ):
                raise ValueError("invalid_voice_deadline")
            self._generation += 1
            self._ticket = CaptureTicket(
                "voice-" + uuid.uuid4().hex, self._generation, self.identity,
                self._now() + deadline_seconds,
            )
            self._transcript, self._revision, self._final, self._speech = None, None, None, None
            self._state, self._error = "capturing", None
            self._emit("voice_capture_started")
            return self._ticket

    def finish_capture(self, ticket: CaptureTicket, audio: AudioFixture) -> bool:
        with self._lock:
            if not self._current(ticket, ("capturing",)):
                return False
            try:
                _validate_audio(audio)
            except ValueError as error:
                self._fail("silence" if str(error) == "silence" else "invalid_audio")
                return False
            self._state = "transcribing"
            self._emit("voice_transcription_started")
        try:
            result = self.stt.transcribe(audio, ticket)
        except Exception:
            with self._lock:
                if self._current(ticket, ("transcribing",)):
                    self._fail("stt_failed")
            return False
        with self._lock:
            if not self._current(ticket, ("transcribing",)):
                return False
            try:
                if (
                    not isinstance(result, Transcription)
                    or result.status != "completed"
                    or result.evidence_mode != "fixture"
                ):
                    raise ValueError("incomplete_transcription")
                text = _text(result.text)
            except ValueError:
                self._fail("transcription_unusable")
                return False
            self._transcript = text
            self._revision = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._state = "reviewing"
            self._emit("voice_transcription_review_required")
            return True

    def revise_transcript(self, ticket: CaptureTicket, text: str) -> str | None:
        with self._lock:
            if not self._current(ticket, ("reviewing",)):
                return None
            text = _text(text)
            self._transcript = text
            self._revision = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self._emit("voice_transcription_revised")
            return self._revision

    def confirm_submission(
        self, ticket: CaptureTicket, *, identity: SurfaceIdentityContract,
        transcript_revision: str,
    ) -> bool:
        with self._lock:
            if VoiceIdentity.from_surface(identity) != self.identity:
                return False
            if not self._current(ticket, ("reviewing",)) or transcript_revision != self._revision:
                return False
            request = VoiceRequest(
                ticket.request_id, self.identity, self._transcript, ticket.deadline,
            )
            self._state = "submitting"
            self._emit("voice_reviewed_text_submitted")
        try:
            final = self.core.interact(request)
        except Exception:
            with self._lock:
                if self._current(ticket, ("submitting",)):
                    self._fail("core_failed")
            return False
        with self._lock:
            if not self._current(ticket, ("submitting",)):
                return False
            try:
                if (
                    not isinstance(final, FinalSynthesis)
                    or final.request_id != ticket.request_id
                    or final.identity != self.identity
                    or final.status != "completed"
                    or final.confirmed is not True
                    or final.evidence_mode not in ("fixture", "core_local")
                ):
                    raise ValueError("unconfirmed_final")
                _text(final.text)
                _reference(final.synthesis_ref)
            except ValueError:
                self._fail("final_synthesis_unusable")
                return False
            self._final = final
            self._transcript, self._revision = None, None
            self._state = "final_text"
            self._emit("voice_final_synthesis_confirmed")
            return True

    def speak_final(self, ticket: CaptureTicket) -> bool:
        self.poll_deadline()
        with self._lock:
            if not self._current(ticket, ("final_text",)) or self._final is None:
                return False
            final = self._final
            self._state = "synthesizing"
            self._emit("voice_fixture_speech_started")
        try:
            speech = self.tts.synthesize(final, ticket)
        except Exception:
            self.poll_deadline()
            self._stop(ticket.request_id)
            with self._lock:
                if self._current(ticket, ("synthesizing",)):
                    self._fail("tts_failed")
            return False
        self.poll_deadline()
        invalid_speech = (
            not isinstance(speech, SpeechFixture)
            or speech.request_id != ticket.request_id
            or speech.synthesis_ref != final.synthesis_ref
            or speech.status != "completed"
            or speech.evidence_mode != "synthetic_fixture"
            or type(speech.data) is not bytes
            or not 2 <= len(speech.data) <= MAX_AUDIO_BYTES
            or len(speech.data) % 2
        )
        if invalid_speech:
            self._stop(ticket.request_id)
        with self._lock:
            if not self._current(ticket, ("synthesizing",)):
                return False
            if invalid_speech:
                self._fail("speech_fixture_unusable")
                return False
            self._speech, self._state = speech, "playing"
            self._emit("voice_fixture_playback_pending")
            return True

    def complete_playback(self, ticket: CaptureTicket) -> bool:
        self.poll_deadline()
        with self._lock:
            if not self._current(ticket, ("playing",)):
                return False
            self._speech, self._state = None, "completed"
            self._emit("voice_fixture_playback_completed")
            return True

    def poll_deadline(self) -> bool:
        """Caller-driven deadline check; no hidden timer/scheduler is started."""
        with self._lock:
            if self._ticket is None or self._state not in (
                "capturing", "transcribing", "reviewing", "submitting",
                "final_text", "synthesizing", "playing",
            ):
                return False
            try:
                expired = self._now() >= self._ticket.deadline
                code = "deadline_exceeded"
            except Exception:
                expired, code = True, "invalid_clock"
            if not expired:
                return False
            request_id = (
                self._ticket.request_id if self._state in ("synthesizing", "playing") else None
            )
            self._generation += 1
            self._fail(code)
        self._stop(request_id)
        return True

    def _stop(self, request_id: str | None) -> None:
        if request_id:
            try:
                self.tts.stop(request_id)
            except Exception:
                with self._lock:
                    self._emit("voice_fixture_stop_failed")

    def interrupt_playback(self) -> bool:
        with self._lock:
            if self._state not in ("synthesizing", "playing"):
                return False
            request_id = self._ticket.request_id if self._ticket else None
            self._generation += 1
            self._state, self._speech = "interrupted", None
            self._emit("voice_fixture_playback_interrupted")
        self._stop(request_id)
        return True

    def cancel(self) -> None:
        with self._lock:
            active_playback = self._state in ("synthesizing", "playing")
            request_id = self._ticket.request_id if active_playback and self._ticket else None
            self._generation += 1
            self._state, self._error = "cancelled", None
            self._transcript, self._revision, self._final, self._speech = None, None, None, None
            self._ticket = None
            self._emit("voice_turn_cancelled")
        self._stop(request_id)

    def switch_identity(self, identity: SurfaceIdentityContract) -> None:
        replacement = VoiceIdentity.from_surface(identity)
        with self._lock:
            request_id = (
                self._ticket.request_id
                if self._ticket and self._state in ("synthesizing", "playing") else None
            )
            self._generation += 1
            self._ticket = None
            self._identity, self._consent = replacement, False
            self._transcript, self._revision, self._final, self._speech = None, None, None, None
            self._state, self._error = "idle", None
            self._emit("voice_identity_changed")
        self._stop(request_id)

    def snapshot(self) -> dict[str, object]:
        """Explicit local display only; transcript/final text must not enter telemetry."""
        with self._lock:
            return {
                "mode": "isolated_voice_fixture", "state": self._state,
                "capture_consent": self._consent, "transcript": self._transcript,
                "transcript_revision": self._revision,
                "final_text": self._final.text if self._final else None,
                "final_evidence_mode": self._final.evidence_mode if self._final else None,
                "error_code": self._error, "hardware_audio": False,
                "tool_authority": "none", "voice_identity": "synthetic_fixture",
            }

    def events(self) -> tuple[dict[str, object], ...]:
        with self._lock:
            return tuple(dict(item) for item in self._events)


class FixtureSttPort:
    def __init__(self, text: str = "Qual é o estado do meu objetivo?", status: str = "completed"):
        self.text, self.status = text, status
        self.calls = 0

    def transcribe(self, audio: AudioFixture, ticket: CaptureTicket) -> Transcription:
        self.calls += 1
        return Transcription(self.text, self.status)


class FixtureCorePort:
    """Declared double: does not exercise real governance/memory/synthesis."""

    def __init__(
        self, text: str = "Esta é uma síntese final simulada; nenhuma ação foi executada.",
    ):
        self.text = text
        self.requests: list[VoiceRequest] = []

    def interact(self, request: VoiceRequest) -> FinalSynthesis:
        self.requests.append(request)
        return FinalSynthesis(request.request_id, request.identity, self.text, "fixture:final")


class FixtureTtsPort:
    """Returns synthetic bytes only; never opens an audio device."""

    def __init__(self):
        self.synthesis_count = 0
        self.stop_count = 0

    def synthesize(self, final: FinalSynthesis, ticket: CaptureTicket) -> SpeechFixture:
        self.synthesis_count += 1
        return SpeechFixture(b"\x01\x00" * 16, final.request_id, final.synthesis_ref)

    def stop(self, request_id: str) -> None:
        self.stop_count += 1
