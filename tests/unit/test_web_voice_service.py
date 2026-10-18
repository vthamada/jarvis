"""Web voice jobs: explicit consent, exact Core finals and ephemeral delivery fences."""

import re
import wave
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from threading import Event
from time import monotonic

import pytest

from apps.jarvis_api.contracts import ANALYSIS_SCHEMA, LocalWebRejected, SessionIdentity
from apps.jarvis_api.voice_profile import LocalAsrConfig, LocalVoiceProfile
from apps.jarvis_api.voice_service import LocalVoiceService
from apps.jarvis_console.persistent_tts import LocalFinalTtsConfig

IDENTITY = SessionIdentity(
    "session://web-live/" + "a" * 32,
    "principal://web-live/" + "b" * 32,
    "user://web-live/" + "c" * 32,
)
OTHER_IDENTITY = SessionIdentity(
    "session://web-live/" + "d" * 32,
    "principal://web-live/" + "e" * 32,
    "user://web-live/" + "f" * 32,
)
TICKET = "web-request-" + "1" * 32
FINAL = "Resposta exata do Core.\nSem substituir ou resumir."
TRANSCRIPT = "Compare os relatorios de documentacao e observabilidade."
JOB_FIELDS = {
    "schema_version", "job_id", "kind", "status", "error_code", "transcript",
    "audio_available",
}


def bounded_case_id(value):
    """Keep synthetic payloads out of node ids, logs and Windows fixture paths."""
    if isinstance(value, (bytes, bytearray, memoryview, str)):
        return f"{type(value).__name__}-{len(value)}"
    return type(value).__name__


def pcm_wav(*, frames=1600, sample_rate=16000, channels=1, sample_width=2):
    stream = BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((channels, sample_width, sample_rate, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * (frames * channels)
                          if sample_width == 2 else b"\x01" * frames * channels * sample_width)
    return stream.getvalue()


class Analysis:
    """Public result/audit seam; this double never creates another Core turn."""

    def __init__(self):
        self.lookups, self.events = [], []
        self.audit_allowed = True
        self.audit_hook = None
        self.lookup_hook = None
        self.result = {
            "schema_version": ANALYSIS_SCHEMA,
            "ticket": TICKET,
            "status": "completed",
            "error_code": None,
            "result": {
                "query": TRANSCRIPT,
                "response_text": FINAL,
                "intent": "analysis",
                "governance_decision": "allow",
                "memory_record_ref": "mem-record-1234abcd",
                "timestamp": "2026-10-17T12:00:00+00:00",
                "evidence_mode": "core_local",
                "generative_status": "disabled",
                "authority": "none",
            },
        }

    def get_result(self, identity, ticket):
        self.lookups.append((identity, ticket))
        if identity != IDENTITY or ticket != TICKET:
            raise LocalWebRejected("analysis_ticket_refused")
        if self.lookup_hook is not None:
            self.lookup_hook()
        return deepcopy(self.result)

    def record_voice_event(self, identity, ticket, phase, metadata):
        self.events.append((identity, ticket, phase, deepcopy(metadata)))
        if self.audit_hook is not None:
            return self.audit_hook(identity, ticket, phase, metadata)
        return self.audit_allowed

    def submit(self, *_args, **_kwargs):
        pytest.fail("voice processing must not submit another Core turn")

    submit_generative = submit
    issue_ticket = submit
    issue_generative_ticket = submit


class HeldWorker:
    """A real thread boundary controlled by Events instead of scheduling sleeps."""

    def __init__(self, result):
        self.result, self.calls = result, []
        self.entered, self.release, self.returned = Event(), Event(), Event()

    def __call__(self, value, cancelled):
        self.calls.append((value, cancelled))
        self.entered.set()
        assert self.release.wait(3), "owned fixture worker was not released"
        self.returned.set()
        return self.result


def rejected(call, code):
    with pytest.raises(LocalWebRejected) as error:
        call()
    assert error.value.code == code
    assert str(error.value) == code


def finish(service, job, *, identity=IDENTITY):
    deadline, wait = monotonic() + 3, Event()
    while monotonic() < deadline:
        result = service.get(identity, job["job_id"])
        if result["status"] != "running":
            return result
        wait.wait(0.002)
    pytest.fail("voice job did not reach a terminal state within the bounded fixture deadline")


def assert_job(job, kind, status):
    assert type(job) is dict and set(job) == JOB_FIELDS
    assert job["schema_version"] == "jarvis-local-voice-job-v1"
    assert job["kind"] == kind and job["status"] == status
    assert re.fullmatch(r"voice-job-[0-9a-f]{32}", job["job_id"])
    assert type(job["audio_available"]) is bool


@pytest.fixture
def voice_factory(tmp_path):
    services, held = [], []
    asr = LocalAsrConfig(tmp_path / "asr", tmp_path / "python.exe")
    tts = LocalFinalTtsConfig(
        authorized=True, engine="qwen3_tts", reference_path=tmp_path / "reference.wav",
        model_dir=tmp_path / "tts", python_executable=tmp_path / "python.exe",
        workspace_root=tmp_path / "workspace", batch_mode=True,
    )

    def make(*, analysis=None, transcriber=None, synthesizer=None, clock=monotonic,
             asr_enabled=True, tts_enabled=True):
        analysis = analysis or Analysis()
        transcriber = transcriber or (lambda _raw, _cancelled: TRANSCRIPT)
        synthesizer = synthesizer or (lambda _text, _cancelled: pcm_wav())
        for worker in (transcriber, synthesizer):
            if isinstance(worker, HeldWorker):
                held.append(worker)
        service = LocalVoiceService(
            analysis, LocalVoiceProfile(asr if asr_enabled else None,
                                        tts if tts_enabled else None),
            transcriber=transcriber, synthesizer=synthesizer, clock=clock,
            evidence_mode="fixture",
        )
        services.append(service)
        return service, analysis

    yield make
    for worker in held:
        worker.release.set()
    for service in services:
        service.close()


def start_when_available(call):
    deadline, wait = monotonic() + 3, Event()
    while monotonic() < deadline:
        try:
            return call()
        except LocalWebRejected as error:
            if error.code != "voice_busy":
                raise
        wait.wait(0.002)
    pytest.fail("owned worker did not release its single-flight slot")


def test_disabled_configuration_is_inert_and_has_no_paths_or_prompt(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("disabled voice configuration performed filesystem IO")

    with monkeypatch.context() as patch:
        for name in ("open", "exists", "stat", "mkdir", "read_bytes", "read_text"):
            patch.setattr(Path, name, forbidden)
        service = LocalVoiceService(Analysis())
        try:
            config = service.config()
            assert config == {
                "schema_version": "jarvis-local-voice-config-v1",
                "asr_enabled": False, "tts_enabled": False, "engine": None,
                "max_capture_seconds": 30, "max_wav_bytes": 6 * 1024 * 1024,
            }
            assert "model_dir" not in repr(config) and "reference_path" not in repr(config)
            assert FINAL not in repr(config) and TRANSCRIPT not in repr(config)
        finally:
            service.close()


def test_disabled_service_refuses_both_workers():
    service = LocalVoiceService(Analysis())
    try:
        rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
                 "voice_disabled")
        rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_disabled")
    finally:
        service.close()


def test_enabled_config_is_explicit_and_does_not_read_host_paths(voice_factory, monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("voice construction/configuration must not read configured model paths")

    with monkeypatch.context() as patch:
        for name in ("open", "exists", "stat", "mkdir", "read_bytes", "read_text"):
            patch.setattr(Path, name, forbidden)
        service, _ = voice_factory()
        assert service.config() == {
            "schema_version": "jarvis-local-voice-config-v1",
            "asr_enabled": True, "tts_enabled": True, "engine": "qwen3_tts",
            "max_capture_seconds": 30, "max_wav_bytes": 6 * 1024 * 1024,
        }


@pytest.mark.parametrize("mode,worker", [
    ("model_real", lambda *_args: TRANSCRIPT),
    ("live", lambda *_args: TRANSCRIPT),
    ("fixture", 7),
    ("fixture", False),
])
def test_injected_workers_cannot_claim_real_evidence_or_be_noncallable(mode, worker):
    with pytest.raises(ValueError, match="^invalid_voice_worker$"):
        LocalVoiceService(Analysis(), transcriber=worker, evidence_mode=mode)


def test_fixture_evidence_requires_an_explicit_injected_worker():
    with pytest.raises(ValueError, match="^invalid_voice_worker$"):
        LocalVoiceService(Analysis(), evidence_mode="fixture")


@pytest.mark.parametrize("consent", [False, None, 1, "yes", []])
def test_consent_must_be_true_before_audio_or_core_access(voice_factory, consent):
    entered = []
    service, analysis = voice_factory(transcriber=lambda *_args: entered.append(True))
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=consent),
             "voice_invalid")
    rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=consent), "voice_invalid")
    assert not entered and not analysis.lookups and not analysis.events


def test_consent_defaults_off(voice_factory):
    service, analysis = voice_factory()
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav()), "voice_invalid")
    rejected(lambda: service.start_speech(IDENTITY, TICKET), "voice_invalid")
    assert not analysis.lookups


@pytest.mark.parametrize("raw", [
    b"", b"RIFF", b"not a wave", bytearray(pcm_wav()), memoryview(pcm_wav()),
    pcm_wav()[:-1], pcm_wav() + b"extra", pcm_wav(sample_width=1),
    pcm_wav(channels=2), pcm_wav(sample_rate=7999), pcm_wav(sample_rate=96001),
    pcm_wav(frames=0), pcm_wav(frames=8000 * 30 + 1, sample_rate=8000),
    b"x" * (6 * 1024 * 1024 + 1),
], ids=bounded_case_id)
def test_malformed_capture_is_rejected_before_worker_or_core(voice_factory, raw):
    entered = []
    service, analysis = voice_factory(transcriber=lambda *_args: entered.append(True))
    rejected(lambda: service.start_transcription(IDENTITY, raw, consent=True), "voice_invalid")
    assert not entered and not analysis.lookups and not analysis.events


@pytest.mark.parametrize("offset,replacement", [
    (0, b"RIFX"), (8, b"AVI "), (12, b"JUNK"), (16, b"\x12\x00\x00\x00"),
    (20, b"\x03\x00"), (28, b"\x00\x00\x00\x00"), (32, b"\x04\x00"),
    (34, b"\x18\x00"), (36, b"LIST"), (40, b"\xff\xff\xff\x7f"),
], ids=bounded_case_id)
def test_capture_requires_unambiguous_canonical_pcm_header(voice_factory, offset, replacement):
    source = pcm_wav()
    raw = source[:offset] + replacement + source[offset + len(replacement):]
    service, analysis = voice_factory()
    rejected(lambda: service.start_transcription(IDENTITY, raw, consent=True), "voice_invalid")
    assert not analysis.lookups


def test_silent_capture_does_not_invent_transcript(voice_factory):
    raw = pcm_wav()
    service, _ = voice_factory()
    rejected(lambda: service.start_transcription(
        IDENTITY, raw[:44] + b"\x00" * (len(raw) - 44), consent=True), "voice_invalid")


@pytest.mark.parametrize("sample_rate", [8000, 16000, 48000, 96000])
def test_capture_rate_boundaries_and_exact_bytes_reach_asr_only(voice_factory, sample_rate):
    source, calls = pcm_wav(sample_rate=sample_rate), []

    def transcribe(raw, cancelled):
        assert callable(cancelled) and cancelled() is False
        calls.append(raw)
        return TRANSCRIPT

    service, analysis = voice_factory(transcriber=transcribe)
    started = service.start_transcription(IDENTITY, source, consent=True)
    assert_job(started, "transcription", "running")
    assert started["transcript"] is None and started["audio_available"] is False
    completed = finish(service, started)
    assert_job(completed, "transcription", "completed")
    assert completed["transcript"] == TRANSCRIPT and completed["error_code"] is None
    assert completed["audio_available"] is False and calls == [source]
    assert not analysis.lookups and not analysis.events
    rejected(lambda: service.audio(IDENTITY, started["job_id"]), "voice_unavailable")


def test_exact_thirty_second_capture_is_accepted(voice_factory):
    service, _ = voice_factory()
    job = service.start_transcription(
        IDENTITY, pcm_wav(frames=8000 * 30, sample_rate=8000), consent=True)
    assert finish(service, job)["transcript"] == TRANSCRIPT


@pytest.mark.parametrize("result", [None, "", " ", "\x00", "\ud800", "x" * 4001, {}],
                         ids=bounded_case_id)
def test_invalid_asr_output_publishes_no_partial_transcript(voice_factory, result):
    service, analysis = voice_factory(transcriber=lambda *_args: result)
    job = service.start_transcription(IDENTITY, pcm_wav(), consent=True)
    failed = finish(service, job)
    assert_job(failed, "transcription", "failed")
    assert failed["error_code"] == "voice_unavailable"
    assert failed["transcript"] is None and failed["audio_available"] is False
    assert not analysis.lookups and not analysis.events


@pytest.mark.parametrize("kind", ["transcription", "speech"])
def test_worker_exception_does_not_publish_exception_content_or_retry(voice_factory, kind):
    calls = []

    def failure(value, _cancelled):
        calls.append(value)
        raise RuntimeError("private token=secret source-path C:/private/audio.wav")

    service, _ = voice_factory(transcriber=failure, synthesizer=failure)
    started = (service.start_transcription(IDENTITY, pcm_wav(), consent=True)
               if kind == "transcription" else service.start_speech(IDENTITY, TICKET, consent=True))
    failed = finish(service, started)
    assert_job(failed, kind, "failed")
    assert failed["error_code"] == "voice_unavailable"
    assert failed["transcript"] is None and failed["audio_available"] is False
    assert len(calls) == 1 and "secret" not in repr(failed)


def test_exact_core_final_is_spoken_once_and_audited_without_content(voice_factory):
    rendered, calls = pcm_wav(), []

    def synthesize(text, cancelled):
        assert callable(cancelled) and cancelled() is False
        calls.append(text)
        return rendered

    service, analysis = voice_factory(synthesizer=synthesize)
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    assert_job(job, "speech", "running")
    completed = finish(service, job)
    assert_job(completed, "speech", "completed")
    assert completed["error_code"] is None and completed["transcript"] is None
    assert completed["audio_available"] is True
    assert service.audio(IDENTITY, job["job_id"]) == rendered and calls == [FINAL]
    assert analysis.lookups and all(item == (IDENTITY, TICKET) for item in analysis.lookups)
    assert [event[2] for event in analysis.events] == ["requested", "finished"]
    for identity, ticket, phase, metadata in analysis.events:
        assert identity == IDENTITY and ticket == TICKET
        assert phase in {"requested", "finished"}
        assert metadata["authority"] == "none" and metadata["evidence_mode"] == "fixture"
        assert FINAL not in repr(metadata) and TRANSCRIPT not in repr(metadata)
        assert "response_text" not in metadata and "audio" not in metadata
    repeated = service.start_speech(IDENTITY, TICKET, consent=True)
    assert repeated == completed and calls == [FINAL] and len(analysis.events) == 2


@pytest.mark.parametrize("change", [
    {"status": "running"}, {"status": "failed"}, {"result": None},
    {"ticket": "web-request-" + "2" * 32},
])
def test_only_completed_matching_core_ticket_may_be_narrated(voice_factory, change):
    calls, analysis = [], Analysis()
    analysis.result.update(change)
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda *_args: calls.append(True))
    rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_ticket_refused")
    assert not calls and not analysis.events


@pytest.mark.parametrize("field,value", [
    ("governance_decision", "deny"), ("governance_decision", "review"),
    ("evidence_mode", "fixture"), ("evidence_mode", "live"),
    ("authority", "execute"), ("authority", None),
])
def test_speech_requires_allowed_local_core_final_without_authority(
        voice_factory, field, value):
    analysis, calls = Analysis(), []
    analysis.result["result"][field] = value
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda *_args: calls.append(True))
    rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_ticket_refused")
    assert not calls and not analysis.events


@pytest.mark.parametrize("envelope", [None, [], "secret token", 3])
def test_malformed_core_envelope_is_a_content_free_refusal(voice_factory, envelope):
    analysis, calls = Analysis(), []
    analysis.result = envelope
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda *_args: calls.append(True))
    rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_ticket_refused")
    assert not calls and not analysis.events


@pytest.mark.parametrize("text", [None, "", " ", "\x00", "\ud800", "x" * 6001],
                         ids=bounded_case_id)
def test_invalid_or_oversized_core_final_is_not_summarized_to_fit(voice_factory, text):
    analysis, calls = Analysis(), []
    analysis.result["result"]["response_text"] = text
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda *_args: calls.append(True))
    rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_invalid")
    assert not calls and not analysis.events


@pytest.mark.parametrize("phase", ["requested", "finished"])
@pytest.mark.parametrize("failure", [False, 1, "yes", "raise"])
def test_audit_must_succeed_before_worker_and_before_audio_delivery(
        voice_factory, phase, failure):
    analysis, calls = Analysis(), []

    def audit(_identity, _ticket, observed_phase, _metadata):
        if observed_phase != phase:
            return True
        if failure == "raise":
            raise RuntimeError("private audit failure token=secret")
        return failure

    analysis.audit_hook = audit
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda text, _cancelled: (
        calls.append(text) or pcm_wav()))
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    failed = finish(service, job)
    assert_job(failed, "speech", "failed")
    assert failed["error_code"] == "voice_unavailable"
    assert failed["audio_available"] is False and failed["transcript"] is None
    assert len(calls) == (0 if phase == "requested" else 1)
    rejected(lambda: service.audio(IDENTITY, job["job_id"]), "voice_unavailable")
    assert service.start_speech(IDENTITY, TICKET, consent=True) == failed
    assert len(calls) == (0 if phase == "requested" else 1)


def test_missing_speech_audit_boundary_fails_closed(voice_factory):
    analysis, calls = Analysis(), []
    analysis.record_voice_event = None
    service, _ = voice_factory(analysis=analysis, synthesizer=lambda *_args: calls.append(True))
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    assert finish(service, job)["error_code"] == "voice_unavailable" and not calls


@pytest.mark.parametrize("output", [b"", b"private audio failure", pcm_wav()[:-2],
                                   pcm_wav(channels=2), pcm_wav(sample_width=1)],
                         ids=bounded_case_id)
def test_malformed_tts_output_never_becomes_downloadable(voice_factory, output):
    service, _ = voice_factory(synthesizer=lambda *_args: output)
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    failed = finish(service, job)
    assert failed["status"] == "failed" and failed["audio_available"] is False
    rejected(lambda: service.audio(IDENTITY, job["job_id"]), "voice_unavailable")


@pytest.mark.parametrize("kind", ["transcription", "speech"])
def test_global_single_flight_includes_both_kinds_and_other_sessions(voice_factory, kind):
    worker = HeldWorker(TRANSCRIPT if kind == "transcription" else pcm_wav())
    service, _ = voice_factory(transcriber=worker, synthesizer=worker)
    job = (service.start_transcription(IDENTITY, pcm_wav(), consent=True)
           if kind == "transcription" else service.start_speech(IDENTITY, TICKET, consent=True))
    assert worker.entered.wait(2)
    rejected(lambda: service.start_transcription(OTHER_IDENTITY, pcm_wav(), consent=True),
             "voice_busy")
    if kind == "transcription":
        rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True), "voice_busy")
    else:
        assert service.start_speech(IDENTITY, TICKET, consent=True) == job
    worker.release.set()
    assert finish(service, job)["status"] == "completed" and len(worker.calls) == 1


@pytest.mark.parametrize("method", ["get", "audio", "cancel"])
def test_job_delivery_and_cancellation_are_bound_to_full_identity(voice_factory, method):
    service, _ = voice_factory()
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    assert finish(service, job)["status"] == "completed"
    for impostor in (
        OTHER_IDENTITY,
        SessionIdentity(IDENTITY.session_ref, OTHER_IDENTITY.principal_ref,
                        IDENTITY.canonical_user_ref),
        SessionIdentity(IDENTITY.session_ref, IDENTITY.principal_ref,
                        OTHER_IDENTITY.canonical_user_ref),
    ):
        rejected(lambda: getattr(service, method)(impostor, job["job_id"]),
                 "voice_ticket_refused")
    assert service.audio(IDENTITY, job["job_id"]) == pcm_wav()


def test_same_session_cannot_be_rebound_to_another_principal_or_user(voice_factory):
    service, _ = voice_factory()
    job = service.start_transcription(IDENTITY, pcm_wav(), consent=True)
    assert finish(service, job)["status"] == "completed"
    for impostor in (
        SessionIdentity(IDENTITY.session_ref, OTHER_IDENTITY.principal_ref,
                        IDENTITY.canonical_user_ref),
        SessionIdentity(IDENTITY.session_ref, IDENTITY.principal_ref,
                        OTHER_IDENTITY.canonical_user_ref),
    ):
        rejected(lambda: service.start_transcription(impostor, pcm_wav(), consent=True),
                 "voice_ticket_refused")


@pytest.mark.parametrize("job_id", [None, "", "voice-job-" + "f" * 32,
                                   "voice-job-" + "F" * 32, "../capture.wav", {}, 1])
@pytest.mark.parametrize("method", ["get", "audio", "cancel"])
def test_missing_or_malformed_job_ids_do_not_disclose_records(voice_factory, job_id, method):
    service, _ = voice_factory()
    rejected(lambda: getattr(service, method)(IDENTITY, job_id), "voice_ticket_refused")


@pytest.mark.parametrize("kind", ["transcription", "speech"])
def test_cancelled_worker_cannot_publish_late_audio_or_transcript(voice_factory, kind):
    worker = HeldWorker(TRANSCRIPT if kind == "transcription" else pcm_wav())
    service, _ = voice_factory(transcriber=worker, synthesizer=worker)
    job = (service.start_transcription(IDENTITY, pcm_wav(), consent=True)
           if kind == "transcription" else service.start_speech(IDENTITY, TICKET, consent=True))
    assert worker.entered.wait(2)
    cancelled = service.cancel(IDENTITY, job["job_id"])
    assert cancelled["status"] == "failed" and cancelled["error_code"] == "voice_cancelled"
    assert worker.calls[0][1]() is True
    rejected(lambda: service.start_transcription(OTHER_IDENTITY, pcm_wav(), consent=True),
             "voice_busy")
    worker.release.set()
    assert worker.returned.wait(2)
    next_job = start_when_available(lambda: service.start_transcription(
        OTHER_IDENTITY, pcm_wav(), consent=True))
    finish(service, next_job, identity=OTHER_IDENTITY)
    assert service.get(IDENTITY, job["job_id"]) == cancelled
    assert cancelled["transcript"] is None and cancelled["audio_available"] is False
    rejected(lambda: service.audio(IDENTITY, job["job_id"]), "voice_unavailable")
    if kind == "speech":
        assert service.start_speech(IDENTITY, TICKET, consent=True) == cancelled
        assert sum(isinstance(value, str) for value, _ in worker.calls) == 1


@pytest.mark.parametrize("kind", ["transcription", "speech"])
def test_revocation_withholds_running_and_late_results(voice_factory, kind):
    worker = HeldWorker(TRANSCRIPT if kind == "transcription" else pcm_wav())
    service, _ = voice_factory(transcriber=worker, synthesizer=worker)
    job = (service.start_transcription(IDENTITY, pcm_wav(), consent=True)
           if kind == "transcription" else service.start_speech(IDENTITY, TICKET, consent=True))
    assert worker.entered.wait(2)
    service.revoke(IDENTITY)
    assert worker.calls[0][1]() is True
    worker.release.set()
    assert worker.returned.wait(2)
    for method in (service.get, service.audio, service.cancel):
        rejected(lambda: method(IDENTITY, job["job_id"]), "voice_ticket_refused")
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
             "voice_ticket_refused")


def test_close_revokes_completed_audio_and_refuses_new_jobs(voice_factory):
    service, _ = voice_factory()
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    assert finish(service, job)["audio_available"] is True
    service.close()
    for method in (service.get, service.audio, service.cancel):
        rejected(lambda: method(IDENTITY, job["job_id"]), "voice_ticket_refused")
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
             "voice_ticket_refused")
    service.close()


@pytest.mark.parametrize("kind", ["transcription", "speech"])
def test_expiry_at_ttl_boundary_drops_completed_payload(voice_factory, kind):
    current = [10.0]
    service, _ = voice_factory(clock=lambda: current[0])
    job = (service.start_transcription(IDENTITY, pcm_wav(), consent=True)
           if kind == "transcription" else service.start_speech(IDENTITY, TICKET, consent=True))
    assert finish(service, job)["status"] == "completed"
    current[0] = 909.999
    assert service.get(IDENTITY, job["job_id"])["status"] == "completed"
    current[0] = 910.0
    expired = service.get(IDENTITY, job["job_id"])
    assert expired["status"] == "failed" and expired["error_code"] == "voice_expired"
    assert expired["transcript"] is None and expired["audio_available"] is False
    rejected(lambda: service.audio(IDENTITY, job["job_id"]), "voice_unavailable")


def test_worker_completing_after_expiry_does_not_publish_transcript(voice_factory):
    current, worker = [0.0], HeldWorker(TRANSCRIPT)
    service, _ = voice_factory(transcriber=worker, clock=lambda: current[0])
    job = service.start_transcription(IDENTITY, pcm_wav(), consent=True)
    assert worker.entered.wait(2)
    current[0] = 900.0
    worker.release.set()
    failed = finish(service, job)
    assert failed["status"] == "failed" and failed["error_code"] == "voice_expired"
    assert failed["transcript"] is None and failed["audio_available"] is False


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "now"])
def test_invalid_clock_refuses_job_before_asr(voice_factory, value):
    calls = []
    service, _ = voice_factory(clock=lambda: value,
                               transcriber=lambda *_args: calls.append(True))
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
             "voice_unavailable")
    assert not calls


def test_clock_rollback_withholds_previous_transcript(voice_factory):
    current = [10.0]
    service, _ = voice_factory(clock=lambda: current[0])
    job = service.start_transcription(IDENTITY, pcm_wav(), consent=True)
    assert finish(service, job)["status"] == "completed"
    current[0] = 9.0
    rejected(lambda: service.get(IDENTITY, job["job_id"]), "voice_unavailable")


def test_retained_record_limit_fails_closed_without_overwriting_existing_jobs(voice_factory):
    service, _ = voice_factory()
    records = []
    for _ in range(32):
        job = start_when_available(lambda: service.start_transcription(
            IDENTITY, pcm_wav(), consent=True))
        records.append(finish(service, job))
    assert len({item["job_id"] for item in records}) == 32
    rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True), "voice_busy")
    assert service.get(IDENTITY, records[0]["job_id"]) == records[0]


def test_reentrant_cancellation_at_finished_audit_cannot_resurrect_audio(voice_factory):
    worker, analysis = HeldWorker(pcm_wav()), Analysis()
    service, _ = voice_factory(analysis=analysis, synthesizer=worker)
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    assert worker.entered.wait(2)

    def cancel_when_finished(_identity, _ticket, phase, _metadata):
        if phase == "finished":
            cancelled = service.cancel(IDENTITY, job["job_id"])
            assert cancelled["error_code"] == "voice_cancelled"
        return True

    analysis.audit_hook = cancel_when_finished
    worker.release.set()
    failed = finish(service, job)
    assert failed["status"] == "failed" and failed["error_code"] == "voice_cancelled"
    assert failed["audio_available"] is False and failed["transcript"] is None
    rejected(lambda: service.audio(IDENTITY, job["job_id"]), "voice_unavailable")


@pytest.mark.parametrize("injected_kind", ["transcription", "speech"])
def test_partial_fixture_injection_never_falls_back_to_real_worker(tmp_path, injected_kind):
    profile = LocalVoiceProfile(
        asr=LocalAsrConfig(tmp_path / "asr", tmp_path / "python.exe"),
        tts=LocalFinalTtsConfig(
            authorized=True, engine="qwen3_tts", reference_path=tmp_path / "reference.wav",
            model_dir=tmp_path / "tts", python_executable=tmp_path / "python.exe",
            workspace_root=tmp_path / "workspace", batch_mode=True,
        ),
    )
    injected = ({"transcriber": lambda *_args: TRANSCRIPT} if injected_kind == "transcription"
                else {"synthesizer": lambda *_args: pcm_wav()})
    service = LocalVoiceService(Analysis(), profile, evidence_mode="fixture", **injected)
    try:
        config = service.config()
        assert config["asr_enabled"] is (injected_kind == "transcription")
        assert config["tts_enabled"] is (injected_kind == "speech")
        if injected_kind == "transcription":
            rejected(lambda: service.start_speech(IDENTITY, TICKET, consent=True),
                     "voice_disabled")
        else:
            rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
                     "voice_disabled")
    finally:
        service.close()


def test_real_worker_failure_quarantines_further_models_without_retry(tmp_path, monkeypatch):
    from apps.jarvis_api import voice_service as module

    calls = []

    def failed_worker(*_args):
        calls.append("started")
        raise OSError("private SDK failure, cleanup not confirmed")

    monkeypatch.setattr(module, "transcribe_bytes", failed_worker)
    profile = LocalVoiceProfile(asr=LocalAsrConfig(tmp_path / "asr", tmp_path / "python.exe"))
    service = LocalVoiceService(Analysis(), profile)
    try:
        job = service.start_transcription(IDENTITY, pcm_wav(), consent=True)
        assert finish(service, job)["error_code"] == "voice_unavailable"
        rejected(lambda: service.start_transcription(IDENTITY, pcm_wav(), consent=True),
                 "voice_unavailable")
        assert calls == ["started"]
    finally:
        service.close()


def test_deadline_crossed_in_audit_records_corrective_failure_without_audio(voice_factory):
    now = [0.0]
    service, analysis = voice_factory(clock=lambda: now[0])

    def crossing(_identity, _ticket, phase, metadata):
        if phase == "finished" and metadata["status"] == "completed":
            now[0] = 901
        return True

    analysis.audit_hook = crossing
    job = service.start_speech(IDENTITY, TICKET, consent=True)
    result = finish(service, job)
    assert result["status"] == "failed" and result["audio_available"] is False
    assert analysis.events[-1][2:] == ("finished", {
        "kind": "speech", "status": "failed", "authority": "none", "evidence_mode": "fixture",
    })


def test_expired_retained_jobs_do_not_permanently_exhaust_a_live_server(voice_factory):
    now = [0.0]
    service, _ = voice_factory(clock=lambda: now[0])
    for _ in range(32):
        job = start_when_available(lambda: service.start_transcription(
            IDENTITY, pcm_wav(), consent=True))
        assert finish(service, job)["status"] == "completed"
    now[0] = 901
    fresh = start_when_available(lambda: service.start_transcription(
        IDENTITY, pcm_wav(), consent=True))
    assert finish(service, fresh)["status"] == "completed"
