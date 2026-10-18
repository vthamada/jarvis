"""Bounded offline voice jobs, tied to the paired session and canonical Core final."""

from __future__ import annotations

import math
import re
import struct
import time
import unicodedata
from dataclasses import dataclass, field
from threading import Event, RLock, Thread
from uuid import uuid4

from .contracts import TICKET_PATTERN, LocalWebRejected, SessionIdentity
from .voice_profile import LocalVoiceProfile, synthesize_bytes, transcribe_bytes

MAX_CAPTURE_BYTES = 6 * 1024 * 1024
MAX_AUDIO_BYTES = 32 * 1024 * 1024
JOB_PATTERN = re.compile(r"voice-job-[0-9a-f]{32}\Z", re.ASCII)


def _reject(code="voice_invalid"):
    raise LocalWebRejected(code)


def validate_wav(raw, *, capture=False):
    """Only canonical mono PCM16 WAV; no codecs, URLs or media decoders."""
    maximum = MAX_CAPTURE_BYTES if capture else MAX_AUDIO_BYTES
    if type(raw) is not bytes or not 44 < len(raw) <= maximum:
        _reject()
    if (raw[:4] != b"RIFF" or raw[8:16] != b"WAVEfmt " or raw[36:40] != b"data"
            or struct.unpack_from("<I", raw, 4)[0] != len(raw) - 8):
        _reject()
    size, fmt, channels, rate, byte_rate, align, bits = struct.unpack_from("<IHHIIHH", raw, 16)
    data_size = struct.unpack_from("<I", raw, 40)[0]
    if (size != 16 or fmt != 1 or channels != 1 or not 8000 <= rate <= 96000
            or byte_rate != rate * 2 or align != 2 or bits != 16
            or data_size != len(raw) - 44 or data_size % 2
            or data_size / (rate * 2) > (30 if capture else 600)
            or not any(raw[44:])):
        _reject()


def _text(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= maximum or not value.strip()
            or any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                   and c not in "\r\n\t" for c in value)):
        _reject()
    return value


@dataclass
class _Job:
    identity: SessionIdentity
    job_id: str
    kind: str
    deadline: float
    cancelled: Event = field(default_factory=Event)
    ticket: str | None = None
    status: str = "running"
    error: str | None = None
    transcript: str | None = None
    audio: bytes | None = None
    audit_requested: bool = False
    terminal_audited: bool = False


class LocalVoiceService:
    """One model worker globally. No automatic retries, provider fallback or Core input."""

    def __init__(self, analysis_service, profile=None, *, transcriber=None, synthesizer=None,
                 clock=time.monotonic, evidence_mode="model_real"):
        if profile is not None and type(profile) is not LocalVoiceProfile:
            raise ValueError("invalid_voice_profile")
        injected = transcriber is not None or synthesizer is not None
        if (evidence_mode not in {"model_real", "fixture"}
                or injected != (evidence_mode == "fixture") or not callable(clock)
                or any(worker is not None and not callable(worker)
                       for worker in (transcriber, synthesizer))):
            raise ValueError("invalid_voice_worker")
        self._analysis, self._profile, self._clock = analysis_service, profile, clock
        self._transcriber, self._synthesizer = transcriber, synthesizer
        self._evidence_mode = evidence_mode
        self._lock, self._jobs, self._revoked, self._identities = RLock(), {}, set(), {}
        self._active, self._closed, self._last = None, False, -math.inf
        self._unavailable = False

    def config(self):
        profile = None if self._unavailable else self._profile
        return {"schema_version": "jarvis-local-voice-config-v1",
                "asr_enabled": bool(profile and profile.asr and (
                    self._evidence_mode == "model_real" or self._transcriber is not None)),
                "tts_enabled": bool(profile and profile.tts and (
                    self._evidence_mode == "model_real" or self._synthesizer is not None)),
                "engine": profile.tts.engine if profile and profile.tts else None,
                "max_capture_seconds": 30, "max_wav_bytes": MAX_CAPTURE_BYTES}

    def _now(self):
        now = self._clock()
        if type(now) not in {int, float} or not math.isfinite(now) or now < self._last:
            _reject("voice_unavailable")
        self._last = now
        return now

    def _bound(self, identity):
        if (type(identity) is not SessionIdentity or self._closed
                or identity.session_ref in self._revoked
                or self._identities.get(identity.session_ref, identity) != identity):
            _reject("voice_ticket_refused")
        for value in (identity.session_ref, identity.principal_ref, identity.canonical_user_ref):
            try:
                _text(value, 512)
                if any(c.isspace() for c in value):
                    _reject("voice_ticket_refused")
            except Exception:
                _reject("voice_ticket_refused")

    def _envelope(self, job):
        return {"schema_version": "jarvis-local-voice-job-v1", "job_id": job.job_id,
                "kind": job.kind, "status": job.status, "error_code": job.error,
                "transcript": job.transcript, "audio_available": job.audio is not None}

    def _retire(self, job, error):
        job.cancelled.set()
        job.status, job.error, job.transcript, job.audio = "failed", error, None, None
        if job.audit_requested and not job.terminal_audited:
            job.terminal_audited = True  # Fence a reentrant audit/cancel callback.
            self._audit(job, "finished", "failed")

    def _lookup(self, identity, job_id):
        self._bound(identity)
        if (type(job_id) is not str or not JOB_PATTERN.fullmatch(job_id)
                or job_id not in self._jobs or self._jobs[job_id].identity != identity):
            _reject("voice_ticket_refused")
        job = self._jobs[job_id]
        if self._now() >= job.deadline:
            self._retire(job, "voice_expired")
        return job

    def get(self, identity, job_id):
        with self._lock:
            return self._envelope(self._lookup(identity, job_id))

    def audio(self, identity, job_id):
        with self._lock:
            job = self._lookup(identity, job_id)
            if job.status != "completed" or job.audio is None:
                _reject("voice_unavailable")
            return job.audio

    def cancel(self, identity, job_id):
        with self._lock:
            job = self._lookup(identity, job_id)
            self._retire(job, "voice_cancelled")
            return self._envelope(job)

    def _new(self, identity, kind, consent, ticket=None):
        self._bound(identity)
        if consent is not True:
            _reject()
        if self._unavailable:
            _reject("voice_unavailable")
        if not self.config()["asr_enabled" if kind == "transcription" else "tts_enabled"]:
            _reject("voice_disabled")
        if ticket is not None:
            for job in self._jobs.values():
                if job.identity == identity and job.ticket == ticket:
                    return job, False  # One attempt per Core ticket, even after failure/cancel.
        now = self._now()
        for job_id, old in list(self._jobs.items()):
            if old.deadline <= now and job_id != self._active:
                self._retire(old, "voice_expired")
                del self._jobs[job_id]
        if self._active is not None or len(self._jobs) >= 32:
            _reject("voice_busy")
        self._identities[identity.session_ref] = identity
        job = _Job(identity, "voice-job-" + uuid4().hex, kind, now + 900, ticket=ticket)
        self._jobs[job.job_id], self._active = job, job.job_id
        return job, True

    def start_transcription(self, identity, raw, *, consent=False):
        with self._lock:
            self._bound(identity)
            if consent is not True:
                _reject()
            validate_wav(raw, capture=True)
            job, created = self._new(identity, "transcription", consent)
            if created:
                self._launch(job, raw)
            return self._envelope(job)

    def start_speech(self, identity, ticket, *, consent=False):
        with self._lock:
            self._bound(identity)
            if (consent is not True or type(ticket) is not str
                    or not TICKET_PATTERN.fullmatch(ticket)):
                _reject()
            if not self.config()["tts_enabled"]:
                _reject("voice_disabled")
            # Only server-owned completed final. Browser cannot choose narration text.
            try:
                envelope = self._analysis.get_result(identity, ticket)
            except Exception:
                _reject("voice_ticket_refused")
            result = envelope.get("result") if type(envelope) is dict else None
            if (type(envelope) is not dict or envelope.get("status") != "completed"
                    or envelope.get("ticket") != ticket or envelope.get("error_code") is not None
                    or type(result) is not dict
                    or result.get("governance_decision") != "allow"
                    or result.get("evidence_mode") != "core_local"
                    or result.get("authority") != "none"):
                _reject("voice_ticket_refused")
            text = _text(result.get("response_text"), 6000)
            job, created = self._new(identity, "speech", consent, ticket)
            if created:
                self._launch(job, text)
            return self._envelope(job)

    def _audit(self, job, phase, status):
        if job.kind != "speech":
            return True
        try:
            return self._analysis.record_voice_event(job.identity, job.ticket, phase, {
                "kind": job.kind, "status": status, "authority": "none",
                "evidence_mode": self._evidence_mode,
            }) is True
        except Exception:
            return False

    def _launch(self, job, value):
        try:
            Thread(target=self._run, args=(job, value), daemon=True).start()
        except Exception:
            self._retire(job, "voice_unavailable")
            self._active = None

    def _run(self, job, value):
        try:
            with self._lock:
                if job.cancelled.is_set() or self._closed:
                    return
                if not self._audit(job, "requested", "running"):
                    _reject("voice_unavailable")
                job.audit_requested = job.kind == "speech"
                if job.cancelled.is_set() or self._closed or self._now() >= job.deadline:
                    self._retire(job, job.error or "voice_expired")
                    return
            if job.kind == "transcription":
                worker = self._transcriber or (lambda raw, cancelled: transcribe_bytes(
                    self._profile.asr, raw, cancelled))
                output = _text(worker(value, job.cancelled.is_set), 4000)
            else:
                worker = self._synthesizer or (lambda text, cancelled: synthesize_bytes(
                    self._profile.tts, text, cancelled))
                output = worker(value, job.cancelled.is_set)
                validate_wav(output)
            with self._lock:
                if job.cancelled.is_set() or self._closed or self._now() >= job.deadline:
                    if not job.cancelled.is_set():
                        self._retire(job, "voice_expired")
                    return
                if not self._audit(job, "finished", "completed"):
                    _reject("voice_unavailable")
                if job.cancelled.is_set() or self._closed or self._now() >= job.deadline:
                    self._retire(job, job.error or "voice_expired")
                    return
                job.terminal_audited = True
                job.status = "completed"
                if job.kind == "transcription":
                    job.transcript = output
                else:
                    job.audio = output
        except Exception:
            with self._lock:
                if self._evidence_mode == "model_real":
                    # A failing external SDK may not have confirmed child cleanup.
                    # Never launch a second model after that uncertain boundary.
                    self._unavailable = True
                if not job.cancelled.is_set():
                    self._retire(job, "voice_unavailable")
        finally:
            with self._lock:
                if self._active == job.job_id:
                    self._active = None

    def revoke(self, identity):
        with self._lock:
            self._revoked.add(identity.session_ref)
            for job in self._jobs.values():
                if job.identity == identity:
                    self._retire(job, "voice_cancelled")

    def close(self):
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                self._retire(job, "voice_cancelled")
