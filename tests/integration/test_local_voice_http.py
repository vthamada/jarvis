"""Actual loopback voice contracts; workers are explicit, non-model fixtures.

One test composes a native Core/SQLite turn with fixture TTS. Nothing here uses
accounts, a real microphone, human recordings, prepared models or SDK workers.
"""

import http.client
import json
import threading
import wave
from contextlib import contextmanager
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from time import monotonic

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.contracts import ANALYSIS_SCHEMA, MAX_BODY_BYTES, LocalWebRejected
from apps.jarvis_api.local_auth import LocalAuth
from apps.jarvis_api.local_server import CSP, LocalWebHandler, create_server
from apps.jarvis_api.voice_profile import LocalAsrConfig, LocalVoiceProfile
from apps.jarvis_api.voice_service import MAX_CAPTURE_BYTES, LocalVoiceService
from apps.jarvis_console.persistent_tts import LocalFinalTtsConfig
from apps.jarvis_console.voice_pilot import _isolated_core

TICKET = "web-request-" + "1" * 32
TRANSCRIPT = "Compare os relatórios de documentação e observabilidade do piloto."
FINAL = "Resposta canônica exata.\r\nNão substituir o texto por uma versão resumida."
JOB_FIELDS = {
    "schema_version", "job_id", "kind", "status", "error_code", "transcript",
    "audio_available",
}


def pcm_wav(*, frames=1600, rate=16000):
    stream = BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * frames)
    return stream.getvalue()


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


class AnalysisFixture:
    """A result/audit seam, never evidence of a real Core or inference call."""

    def __init__(self):
        self.owner = None
        self.lookups, self.audits, self.submissions, self.revocations = [], [], [], []
        self.result = {
            "schema_version": ANALYSIS_SCHEMA,
            "ticket": TICKET,
            "status": "completed",
            "error_code": None,
            "result": {
                "query": TRANSCRIPT, "response_text": FINAL, "intent": "analysis",
                "governance_decision": "allow", "memory_record_ref": "mem-record-1234abcd",
                "timestamp": "2026-10-17T12:00:00+00:00", "evidence_mode": "core_local",
                "generative_status": "disabled", "authority": "none",
            },
        }

    def current_ticket(self, _identity):
        return None

    def get_result(self, identity, ticket):
        self.lookups.append((identity, ticket))
        if identity != self.owner or ticket != TICKET:
            raise LocalWebRejected("analysis_ticket_refused")
        return deepcopy(self.result)

    def record_voice_event(self, identity, ticket, phase, metadata):
        assert identity == self.owner and ticket == TICKET
        self.audits.append((phase, deepcopy(metadata)))
        return True

    def submit(self, *args, **kwargs):
        self.submissions.append((args, kwargs))
        pytest.fail("voice must never submit an automatic or duplicate Core turn")

    submit_generative = submit
    issue_ticket = submit
    issue_generative_ticket = submit

    def revoke(self, identity):
        self.revocations.append(identity)

    def close(self):
        pass


def fixture_profile(*, asr=True, tts=True):
    # These synthetically named paths are never inspected: fixture workers must
    # be injected for every enabled operation. No real voice SDK is selected.
    absent = Path(__file__).resolve().parent / "synthetic-voice-never-opened"
    return LocalVoiceProfile(
        asr=LocalAsrConfig(absent / "asr", absent / "python.exe") if asr else None,
        tts=LocalFinalTtsConfig(
            authorized=True, engine="qwen3_tts", reference_path=absent / "reference.wav",
            model_dir=absent / "tts", python_executable=absent / "python.exe",
            workspace_root=absent, batch_mode=True,
        ) if tts else None,
    )


@contextmanager
def running(*, analysis=None, enabled=True, transcriber=None, synthesizer=None,
            clock=None, voice_service=None, asr=True, tts=True):
    analysis = analysis if analysis is not None else AnalysisFixture()
    clock = clock if clock is not None else Clock()
    captures, speeches = [], []

    def recognize(raw, cancelled):
        captures.append(raw)
        assert cancelled() is False
        return TRANSCRIPT

    def render(text, cancelled):
        speeches.append(text)
        assert cancelled() is False
        return pcm_wav()

    if voice_service is None:
        voice_service = (
            LocalVoiceService(
                analysis, fixture_profile(asr=asr, tts=tts), clock=clock,
                transcriber=(transcriber or recognize) if asr else None,
                synthesizer=(synthesizer or render) if tts else None,
                evidence_mode="fixture",
            ) if enabled else LocalVoiceService(analysis, clock=clock)
        )
    auth = LocalAuth(clock=clock)
    server = create_server(analysis, auth=auth, voice_service=voice_service)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
    thread.start()
    ctx = {
        "server": server, "analysis": analysis, "voice": voice_service, "clock": clock,
        "captures": captures, "speeches": speeches,
        "origin": f"http://127.0.0.1:{server.server_port}",
    }
    try:
        yield ctx
    finally:
        server.shutdown()
        server.server_close()
        analysis.close()
        thread.join(timeout=2)
        assert not thread.is_alive()


def request(ctx, path, *, method="GET", body=None, headers=None):
    fields = {"X-Jarvis-Client": "local-web-v1"}
    if "cookie" in ctx:
        fields.update({"Cookie": ctx["cookie"], "X-Jarvis-CSRF": ctx["csrf"]})
    if method == "POST":
        fields["Origin"] = ctx["origin"]
    if type(body) is dict:
        body = json.dumps(body, ensure_ascii=True).encode("ascii")
        fields["Content-Type"] = "application/json"
    fields.update(headers or {})
    connection = http.client.HTTPConnection("127.0.0.1", ctx["server"].server_port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=fields)
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def pair(ctx, *, bind_fixture=True):
    status, headers, raw = request(ctx, "/api/pair", method="POST", body={
        "secret": ctx["server"].auth.pairing_secret,
    })
    assert status == 200
    value = json.loads(raw)
    ctx.update(cookie=headers["Set-Cookie"].split(";", 1)[0], csrf=value["csrf_token"],
               session=value["session_ref"])
    if bind_fixture and type(ctx["analysis"]) is AnalysisFixture:
        token = ctx["cookie"].split("=", 1)[1]
        ctx["analysis"].owner = ctx["server"].auth.authenticate(token)
    return value


def poll(ctx, job_id):
    deadline = monotonic() + 5
    wait = threading.Event()
    while monotonic() < deadline:
        status, _, raw = request(ctx, "/api/voice/jobs/" + job_id)
        assert status == 200
        value = json.loads(raw)
        if value["status"] != "running":
            return value
        wait.wait(0.002)
    pytest.fail("owned fixture voice job did not become terminal")


def start_speech(ctx, ticket=TICKET):
    status, _, raw = request(ctx, "/api/voice/speech", method="POST",
                             body={"ticket": ticket, "consent": True})
    assert status == 202
    return json.loads(raw)


def capture_headers():
    return {"Content-Type": "audio/wav", "X-Jarvis-Voice-Consent": "local-audio-v1"}


def assert_fixed_error(status, raw, allowed):
    assert status in allowed
    value = json.loads(raw)
    assert set(value) == {"error_code"}
    assert type(value["error_code"]) is str
    assert "synthetic-voice-never-opened" not in raw.decode("ascii")


def test_disabled_voice_default_keeps_microphone_policy_closed():
    with running(enabled=False) as ctx:
        pair(ctx)
        status, headers, raw = request(ctx, "/api/voice/config")
        assert status == 200
        config = json.loads(raw)
        assert config == {
            "schema_version": "jarvis-local-voice-config-v1", "asr_enabled": False,
            "tts_enabled": False, "engine": None, "max_capture_seconds": 30,
            "max_wav_bytes": MAX_CAPTURE_BYTES,
        }
        assert headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
        assert headers["Content-Security-Policy"] == CSP
        status, _, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                 body=pcm_wav(), headers=capture_headers())
        assert (status, json.loads(raw)) == (409, {"error_code": "voice_disabled"})
        status, _, raw = request(ctx, "/api/voice/speech", method="POST",
                                 body={"ticket": TICKET, "consent": True})
        assert (status, json.loads(raw)) == (409, {"error_code": "voice_disabled"})
        assert not ctx["analysis"].submissions and not ctx["analysis"].lookups


@pytest.mark.parametrize("asr", [False, True], ids=["tts-only", "asr-enabled"])
def test_permission_policy_only_allows_same_origin_microphone_with_asr(asr):
    with running(asr=asr) as ctx:
        pair(ctx)
        status, headers, raw = request(ctx, "/api/voice/config")
        assert status == 200 and json.loads(raw)["asr_enabled"] is asr
        expected = "(self)" if asr else "()"
        assert headers["Permissions-Policy"] == f"camera=(), microphone={expected}, geolocation=()"
        assert headers["Content-Security-Policy"] == CSP
        assert "media-src 'none'" in CSP and "connect-src 'self'" in CSP
        assert not any(key.lower().startswith("access-control") for key in headers)


@pytest.mark.parametrize("attack", [
    "unpaired", "csrf", "expired", "revoked", "client", "origin", "cross-site", "host",
])
def test_auth_and_origin_guard_before_audio_parser_or_worker(monkeypatch, attack):
    with running() as ctx:
        if attack != "unpaired":
            pair(ctx)
        headers = capture_headers()
        if attack == "csrf":
            headers["X-Jarvis-CSRF"] = "0" * 64
        elif attack == "expired":
            ctx["clock"].value += 900
        elif attack == "revoked":
            ctx["server"].auth.revoke(ctx["cookie"].split("=", 1)[1])
        elif attack == "client":
            headers["X-Jarvis-Client"] = "foreign"
        elif attack == "origin":
            headers["Origin"] = "https://foreign.invalid"
        elif attack == "cross-site":
            headers["Sec-Fetch-Site"] = "cross-site"
        elif attack == "host":
            headers["Host"] = "foreign.invalid"

        def forbidden(_handler):
            pytest.fail("denied boundary reached the audio body parser")

        monkeypatch.setattr(LocalWebHandler, "_voice_body", forbidden)
        status, _, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                 body=pcm_wav(), headers=headers)
        assert_fixed_error(status, raw, {401, 403})
        assert not ctx["captures"] and not ctx["speeches"]
        assert not ctx["analysis"].submissions and not ctx["analysis"].lookups


@pytest.mark.parametrize("case", ["mime", "consent", "format", "truncated", "empty"])
def test_malformed_capture_never_starts_asr(case):
    with running() as ctx:
        pair(ctx)
        headers, body = capture_headers(), pcm_wav()
        if case == "mime":
            headers["Content-Type"] = "audio/webm"
        elif case == "consent":
            headers["X-Jarvis-Voice-Consent"] = "true"
        elif case == "format":
            body = b"not an audio file"
        elif case == "truncated":
            body = body[:-2]
        else:
            body = b""
        status, _, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                 body=body, headers=headers)
        assert_fixed_error(status, raw, {400})
        assert not ctx["captures"] and not ctx["analysis"].submissions


def test_capture_route_has_its_own_size_cap_without_widening_json_routes():
    with running() as ctx:
        pair(ctx)
        # More than the ordinary JSON cap, but a valid small PCM utterance.
        capture = pcm_wav(frames=20000)
        assert MAX_BODY_BYTES < len(capture) < MAX_CAPTURE_BYTES
        status, _, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                 body=capture, headers=capture_headers())
        assert status == 202
        assert poll(ctx, json.loads(raw)["job_id"])["transcript"] == TRANSCRIPT
        assert ctx["captures"] == [capture]
        too_large = dict(capture_headers(), **{"Content-Length": str(MAX_CAPTURE_BYTES + 1)})
        status, _, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                 body=b"x", headers=too_large)
        assert (status, json.loads(raw)) == (413, {"error_code": "request_too_large"})
        status, _, raw = request(ctx, "/api/voice/speech", method="POST", body=b"x", headers={
            "Content-Type": "application/json", "Content-Length": str(MAX_BODY_BYTES + 1),
        })
        assert (status, json.loads(raw)) == (413, {"error_code": "request_too_large"})
        assert ctx["captures"] == [capture] and not ctx["speeches"]


def test_capture_returns_only_review_draft_without_submitting_core_or_exposing_paths():
    with running() as ctx:
        pair(ctx)
        capture = pcm_wav()
        status, headers, raw = request(ctx, "/api/voice/transcriptions", method="POST",
                                       body=capture, headers=capture_headers())
        assert status == 202 and headers["Cache-Control"] == "no-store"
        result = poll(ctx, json.loads(raw)["job_id"])
        assert set(result) == JOB_FIELDS
        assert result["kind"] == "transcription" and result["status"] == "completed"
        assert result["transcript"] == TRANSCRIPT and result["audio_available"] is False
        assert result["error_code"] is None
        rendered = json.dumps(result)
        for marker in ("model_dir", "reference_path", "transcript_path", "segments_path", "C:\\"):
            assert marker not in rendered
        assert ctx["captures"] == [capture]
        assert not ctx["analysis"].submissions and not ctx["analysis"].lookups
        assert not ctx["analysis"].audits
        status, _, raw = request(ctx, "/api/voice/audio/" + result["job_id"])
        assert (status, json.loads(raw)) == (503, {"error_code": "voice_unavailable"})


@pytest.mark.parametrize("case", ["text", "reference", "model", "missing-consent", "false-consent"])
def test_owned_speech_ticket_does_not_accept_browser_selected_text_paths_or_model(case):
    with running() as ctx:
        pair(ctx)
        body = {"ticket": TICKET, "consent": True}
        if case == "missing-consent":
            body.pop("consent")
        elif case == "false-consent":
            body["consent"] = False
        else:
            body[case] = "synthetic-browser-override"
        status, _, raw = request(ctx, "/api/voice/speech", method="POST", body=body)
        assert_fixed_error(status, raw, {400})
        assert not ctx["speeches"] and not ctx["analysis"].submissions
        assert not ctx["analysis"].lookups and not ctx["analysis"].audits


@pytest.mark.parametrize("decision", ["block", "defer_for_validation"])
def test_non_allow_core_decision_cannot_start_narration(decision):
    with running() as ctx:
        pair(ctx)
        ctx["analysis"].result["result"]["governance_decision"] = decision
        status, _, raw = request(ctx, "/api/voice/speech", method="POST",
                                 body={"ticket": TICKET, "consent": True})
        assert (status, json.loads(raw)) == (403, {"error_code": "voice_ticket_refused"})
        assert not ctx["speeches"] and not ctx["analysis"].audits
        assert not ctx["analysis"].submissions


def test_speech_is_audited_exact_final_once_with_auth_only_wav_delivery():
    with running() as ctx:
        pair(ctx)
        before = deepcopy(ctx["analysis"].result)
        started = start_speech(ctx)
        result = poll(ctx, started["job_id"])
        assert set(result) == JOB_FIELDS
        assert result["status"] == "completed" and result["audio_available"] is True
        assert result["transcript"] is None and ctx["speeches"] == [FINAL]
        assert start_speech(ctx)["job_id"] == started["job_id"]
        assert ctx["speeches"] == [FINAL]  # Repeated HTTP request is not another inference.
        status, headers, raw = request(ctx, "/api/voice/audio/" + result["job_id"])
        assert status == 200 and raw == pcm_wav()
        assert headers["Content-Type"] == "audio/wav"
        assert headers["Content-Length"] == str(len(raw))
        assert headers["Cache-Control"] == "no-store"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Content-Security-Policy"] == CSP
        assert ctx["analysis"].audits == [
            ("requested", {"kind": "speech", "status": "running", "authority": "none",
                           "evidence_mode": "fixture"}),
            ("finished", {"kind": "speech", "status": "completed", "authority": "none",
                          "evidence_mode": "fixture"}),
        ]
        assert ctx["analysis"].result == before and not ctx["analysis"].submissions


@pytest.mark.parametrize("case", ["unpaired", "csrf", "expired", "revoked", "foreign-cookie"])
def test_finished_wav_cannot_be_fetched_without_current_paired_authority(case):
    with running() as ctx:
        pair(ctx)
        job_id = start_speech(ctx)["job_id"]
        assert poll(ctx, job_id)["status"] == "completed"
        headers = {}
        if case == "unpaired":
            headers["Cookie"] = ""
        elif case == "csrf":
            headers["X-Jarvis-CSRF"] = "0" * 64
        elif case == "expired":
            ctx["clock"].value += 900
        elif case == "revoked":
            status, _, _ = request(ctx, "/api/disconnect", method="POST", body={})
            assert status == 200
        else:
            headers["Cookie"] = "jarvis_local_session=" + "0" * 64
        status, _, raw = request(ctx, "/api/voice/audio/" + job_id, headers=headers)
        assert_fixed_error(status, raw, {401, 403})
        assert b"RIFF" not in raw and not ctx["analysis"].submissions


def test_another_valid_paired_session_cannot_fetch_known_job():
    with running() as owner:
        pair(owner)
        job_id = start_speech(owner)["job_id"]
        assert poll(owner, job_id)["status"] == "completed"
        with running(analysis=owner["analysis"], voice_service=owner["voice"]) as foreign:
            pair(foreign, bind_fixture=False)
            assert foreign["session"] != owner["session"]
            for prefix in ("/api/voice/jobs/", "/api/voice/audio/"):
                status, _, raw = request(foreign, prefix + job_id)
                assert (status, json.loads(raw)) == (403, {"error_code": "voice_ticket_refused"})


@pytest.mark.parametrize("case", ["revoke", "expire"])
def test_auth_fence_after_audio_lookup_withholds_racing_wav(monkeypatch, case):
    with running() as ctx:
        pair(ctx)
        job_id = start_speech(ctx)["job_id"]
        assert poll(ctx, job_id)["status"] == "completed"
        original = ctx["voice"].audio

        def raced(identity, requested_id):
            result = original(identity, requested_id)
            if case == "revoke":
                ctx["server"].auth.revoke(ctx["cookie"].split("=", 1)[1])
            else:
                ctx["clock"].value += 900
            return result

        monkeypatch.setattr(ctx["voice"], "audio", raced)
        status, _, raw = request(ctx, "/api/voice/audio/" + job_id)
        assert (status, json.loads(raw)) == (401, {"error_code": "session_refused"})
        assert b"RIFF" not in raw


@pytest.mark.parametrize("case", ["file", "encoded", "unknown", "traversal", "extra-segment"])
@pytest.mark.parametrize("kind", ["jobs", "audio"])
def test_job_urls_never_select_files_or_accept_nested_aliases(case, kind):
    with running() as ctx:
        pair(ctx)
        job_id = start_speech(ctx)["job_id"]
        assert poll(ctx, job_id)["status"] == "completed"
        suffix = {
            "file": "C:/synthetic-secret.wav", "encoded": "%2e%2e%2fsynthetic-secret.wav",
            "unknown": "voice-job-" + "0" * 32, "traversal": "../" + job_id,
            "extra-segment": "extra/" + job_id,
        }[case]
        status, _, raw = request(ctx, "/api/voice/" + kind + "/" + suffix)
        assert_fixed_error(status, raw, {400, 403})
        assert b"RIFF" not in raw and FINAL.encode("utf-8") not in raw


def test_cancelling_voice_does_not_cancel_erase_or_resubmit_core_final():
    entered, release, returned = threading.Event(), threading.Event(), threading.Event()
    calls = []

    def held(text, cancelled):
        calls.append(text)
        entered.set()
        try:
            assert release.wait(5), "owned fixture synthesizer was not released"
            assert cancelled() is True
            return pcm_wav()
        finally:
            returned.set()

    with running(synthesizer=held) as ctx:
        pair(ctx)
        before = deepcopy(ctx["analysis"].result)
        try:
            job_id = start_speech(ctx)["job_id"]
            assert entered.wait(3)
            status, _, raw = request(ctx, "/api/voice/cancel", method="POST",
                                     body={"job_id": job_id})
            assert status == 200
            value = json.loads(raw)
            assert value["status"] == "failed" and value["error_code"] == "voice_cancelled"
            assert value["audio_available"] is False
        finally:
            release.set()
            assert returned.wait(3)
        assert poll(ctx, job_id)["error_code"] == "voice_cancelled"
        status, _, raw = request(ctx, "/api/voice/audio/" + job_id)
        assert (status, json.loads(raw)) == (503, {"error_code": "voice_unavailable"})
        assert calls == [FINAL] and not ctx["analysis"].submissions
        assert ctx["analysis"].result == before
        assert [phase for phase, _ in ctx["analysis"].audits] == ["requested", "finished"]
        assert ctx["analysis"].audits[-1][1]["status"] == "failed"


def test_native_core_persisted_final_reaches_fixture_tts_once_and_audit_survives_restart(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://synthetic-never-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    analysis = AnalysisService(tmp_path / "owned-core")
    with running(analysis=analysis) as ctx:
        pair(ctx)
        status, _, raw = request(ctx, "/api/tickets", method="POST", body={})
        assert status == 201
        ticket = json.loads(raw)["ticket"]
        status, _, _ = request(ctx, "/api/analysis", method="POST", body={
            "ticket": ticket, "query": TRANSCRIPT,
        })
        assert status == 202
        analysis._worker.join(20)
        assert not analysis._worker.is_alive()
        status, _, raw = request(ctx, "/api/results/" + ticket)
        result = json.loads(raw)
        assert status == 200 and result["status"] == "completed", result.get("error_code")
        final = result["result"]
        assert final["governance_decision"] == "allow"
        assert final["evidence_mode"] == "core_local" and final["authority"] == "none"
        job_id = start_speech(ctx, ticket)["job_id"]
        assert poll(ctx, job_id)["status"] == "completed"
        assert ctx["speeches"] == [final["response_text"]]
        assert start_speech(ctx, ticket)["job_id"] == job_id
        assert ctx["speeches"] == [final["response_text"]]
        status, headers, raw = request(ctx, "/api/voice/audio/" + job_id)
        assert status == 200 and headers["Content-Type"] == "audio/wav" and raw == pcm_wav()
        status, _, raw = request(ctx, "/api/results/" + ticket)
        assert status == 200 and json.loads(raw) == result
        restarted = _isolated_core(analysis.runtime_dir)
        turns = restarted.memory_service.repository.fetch_recent_turns(ctx["session"], 10)
        assert len(turns) == 1
        assert turns[0].request_content == TRANSCRIPT
        assert turns[0].response_text == final["response_text"]
        events = restarted.observability_service.repository.list_events(
            limit=100, request_id=ticket,
        )
        for name in ("input_received", "response_synthesized", "memory_recorded"):
            assert sum(event.event_name == name for event in events) == 1
        vocal = [event for event in events if event.event_name.startswith("web_voice_")]
        assert [event.event_name for event in vocal] == [
            "web_voice_requested", "web_voice_finished",
        ]
        assert [event.payload["status"] for event in vocal] == ["running", "completed"]
        assert all(event.request_id == ticket and event.session_id == ctx["session"]
                   for event in vocal)
        assert all(event.source_service == "jarvis-web-voice" for event in vocal)
        assert all(event.payload["evidence_mode"] == "fixture" for event in vocal)
        assert all(event.payload["authority"] == "none" for event in vocal)
        assert all(set(event.payload) == {"kind", "status", "authority", "evidence_mode"}
                   for event in vocal)
