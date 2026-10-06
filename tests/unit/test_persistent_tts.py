"""Adversarial local final TTS complement; synthetic WAVs, no real models/audio."""

from __future__ import annotations

import hashlib
import json
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console import persistent_tts as tts
from apps.jarvis_console.voice_pilot import ReviewedVoiceCorePort, _isolated_core, pilot_identity
from apps.jarvis_voice import VoiceRequest
from apps.jarvis_voice_lab import LabResult


def wav(path, *, seconds=3, channels=1, signal=b"\x01\x00"):
    with wave.open(str(path), "wb") as audio:
        audio.setparams((channels, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(signal * (int(seconds * 16000) * channels))


@pytest.fixture
def config(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    model = tmp_path / "model"
    model.mkdir()
    reference = tmp_path / "reference.wav"
    wav(reference)
    executable = tmp_path / "python-stub.exe"
    executable.write_bytes(b"not executed")
    monkeypatch.setattr(tts.tempfile, "gettempdir", lambda: str(tmp_path))
    return tts.LocalFinalTtsConfig(True, "qwen3_tts", reference, model, executable, workspace,
                                  reference_duration_seconds=3)


@pytest.fixture
def turn(tmp_path, monkeypatch):
    original = SynthesisEngine.compose_result
    monkeypatch.setattr(SynthesisEngine, "compose_result", lambda self, value: replace(
        original(self, value), response_text="  Final soberana fixture.\r\nSem executar ação.  "
    ))
    core = _isolated_core(tmp_path / "runtime")
    port = ReviewedVoiceCorePort(core, pilot_identity())
    request = VoiceRequest("voice-unit-fixture", port.identity, "Pergunta revisada privada.",
                           time.monotonic() + 120)
    final = port.interact(request)
    core.handle_input = lambda *_: pytest.fail("No Core retry is authorized")
    return port, request, final


def successful_lab(config, tmp_path):
    folder = tmp_path / "jarvis-voice-lab-fixture-run-owned"
    folder.mkdir()
    output = folder / "sample.wav"
    wav(output, seconds=0.1)
    return LabResult(
        "completed", "fixture_only", "fixture-run", config.engine, "fixture", str(output),
        16000, 0.1, hashlib.sha256(output.read_bytes()).hexdigest(),
        voice_profile=config.voice_profile,
        reference_transcript_reviewed=config.transcript_confirmed
        if config.voice_profile in {"qwen_icl", "qwen_icl_draft"} else None,
    )


def speak(config, turn, runner):
    port, request, final = turn
    return tts.speak_persisted_final(config=config, port=port, request=request, final=final,
                                    lab_runner=runner)


@pytest.mark.parametrize("patch", [
    {"authorized": False}, {"authorized": 1}, {"authorized": "yes"}, {"engine": "remote"},
    {"engine": []}, {"device": "cuda:1"}, {"device": []}, {"timeout_seconds": True},
    {"timeout_seconds": 0}, {"timeout_seconds": 1801}, {"timeout_seconds": float("nan")},
    {"timeout_seconds": float("inf")}, {"voice_profile": "unknown"}, {"voice_profile": []},
    {"voice_profile": "chatterbox_conversational"}, {"reference_start_seconds": -1},
    {"reference_start_seconds": True}, {"reference_duration_seconds": 2.9},
    {"reference_duration_seconds": 16}, {"seed": True}, {"seed": -1}, {"seed": 2**32},
    {"reference_transcript": "unused secret"}, {"transcript_confirmed": True},
    {"voice_profile": "qwen_icl"}, {"voice_profile": "qwen_icl_draft"},
])
def test_pure_invalid_options_do_not_touch_files(config, monkeypatch, patch):
    monkeypatch.setattr(tts, "_plain_path", lambda *_a, **_k: pytest.fail("Filesystem IO"))
    with pytest.raises(ValueError):
        tts.validate_local_tts_config(replace(config, **patch))


@pytest.mark.parametrize("path", [
    Path("relative.wav"), Path("~/reference.wav"), Path("C:/one/../reference.wav"),
    Path("//server/share/reference.wav"), Path("C:/private/reference.wav:stream"),
    Path("C:/private/nul.wav"), Path("C:/private/reference. "), Path("C:/private/\x00.wav"),
    Path("C:/private/\u202e.wav"), Path("C:/private/\ud800.wav"), "C:/private/reference.wav",
])
def test_unsafe_local_path_syntax_is_purely_refused(config, monkeypatch, path):
    monkeypatch.setattr(tts, "_plain_path", lambda *_a, **_k: pytest.fail("Filesystem IO"))
    with pytest.raises(ValueError):
        tts.validate_local_tts_config(replace(config, reference_path=path))


def test_pure_validator_accepts_nonexistent_absolute_paths(config, monkeypatch):
    monkeypatch.setattr(tts, "_plain_path", lambda *_a, **_k: pytest.fail("Filesystem IO"))
    tts.validate_local_tts_config(replace(config, reference_path=config.reference_path.with_name(
        "does-not-exist.wav")))


def test_preflight_never_creates_files(config):
    root = config.workspace_root.parent
    before = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    tts.preflight_local_tts_config(config)
    after = {str(path): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert before == after and list(config.workspace_root.iterdir()) == []


@pytest.mark.parametrize("change", ["missing", "truncated", "silent", "short", "stereo_cancel",
                                         "window_overrun", "model_file", "workspace_file"])
def test_invalid_preflight_refused(config, change):
    if change == "missing":
        config.reference_path.unlink()
    elif change == "truncated":
        config.reference_path.write_bytes(b"RIFFbroken")
    elif change == "silent":
        wav(config.reference_path, signal=b"\x00\x00")
    elif change == "short":
        wav(config.reference_path, seconds=2)
    elif change == "stereo_cancel":
        with wave.open(str(config.reference_path), "wb") as audio:
            audio.setparams((2, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x01\x00\xff\xff" * 48000)
    elif change == "window_overrun":
        config = replace(config, reference_start_seconds=0.001)
    elif change == "model_file":
        config = replace(config, model_dir=config.python_executable)
    else:
        config = replace(config, workspace_root=config.python_executable)
    with pytest.raises(ValueError, match="local_tts_preflight_refused"):
        tts.preflight_local_tts_config(config)


def test_temp_inside_workspace_refused(config, monkeypatch):
    monkeypatch.setattr(tts.tempfile, "gettempdir", lambda: str(config.workspace_root))
    with pytest.raises(ValueError, match="local_tts_preflight_refused"):
        tts.preflight_local_tts_config(config)


def test_success_is_exact_persisted_final_metadata_private(config, turn, tmp_path):
    received = []
    lab = successful_lab(config, tmp_path)
    result = speak(config, turn, lambda **kwargs: (received.append(kwargs), lab)[1])
    assert result.status == "completed" and result.output_path == lab.output_path
    assert received[0]["text"] == turn[2].text != turn[1].text
    assert received[0]["evidence_mode"] == "fixture"
    assert result.metadata()["artifact_available"] and result.audit_event_recorded
    serialized = json.dumps(result.metadata())
    assert str(tmp_path) not in serialized and lab.output_digest not in serialized
    assert turn[1].text not in serialized and turn[2].text not in serialized
    assert "output_path" not in serialized
    events = turn[0].core.observability_service.repository.list_events(limit=100,
                event_names=("local_final_tts_requested", "local_final_tts_finished"))
    assert len(events) == 2
    assert events[-1].payload["status"] == "completed"
    assert all(str(tmp_path) not in json.dumps(event.payload) for event in events)


@pytest.mark.parametrize("patch", [
    {"request_id": "voice-forged"}, {"text": "Forged private final"},
    {"synthesis_ref": "forged-record"}, {"evidence_mode": "fixture"}, {"confirmed": False},
    {"status": "incomplete"},
])
def test_unbound_finals_do_not_run_lab(config, turn, patch):
    port, request, final = turn
    result = tts.speak_persisted_final(config=config, port=port, request=request,
        final=replace(final, **patch), lab_runner=lambda **_: pytest.fail("Unbound final spoke"))
    assert result.status == "refused" and result.reason == "core_final_binding_refused"


@pytest.mark.parametrize("target", ["memory", "events", "mirror", "record_payload", "record_id"])
def test_absent_or_forged_persistence_and_external_tracing_refused(config, turn, target):
    port, _, _ = turn
    if target == "memory":
        port.core.memory_service.repository.fetch_recent_turns = lambda *_: []
    elif target == "events":
        port.core.observability_service.repository.list_events = lambda **_: []
    elif target == "mirror":
        port.core.observability_service.agentic_adapter = object()
    elif target == "record_payload":
        port.response.memory_record.payload["request_content"] = "foreign private request"
    else:
        # Both in-memory identifiers forged consistently: durable memory event
        # must still reject this association.
        port.response.memory_record.memory_record_id = "forged-record"
        turn = (*turn[:2], replace(turn[2], synthesis_ref="forged-record"))
    result = speak(config, turn, lambda **_: pytest.fail("Invalid persistence spoke"))
    assert result.reason == "core_final_binding_refused"


@pytest.mark.parametrize("patch", [
    {"engine": "chatterbox_pt_br"}, {"evidence_mode": "model_real"}, {"status": "mystery"},
    {"reason": "private trace and token"}, {"output_path": None},
    {"output_digest": "0" * 64}, {"sample_rate": True}, {"duration_seconds": float("nan")},
    {"duration_seconds": float("inf")}, {"duration_seconds": 1.0},
    {"voice_profile": "qwen_icl"}, {"reference_transcript_reviewed": True},
    {"run_id": "private/../run"},
])
def test_malformed_lab_never_exposes_success_or_private_metadata(config, turn, tmp_path, patch):
    lab = replace(successful_lab(config, tmp_path), **patch)
    result = speak(config, turn, lambda **_: lab)
    assert result.status == "failed" and result.output_path is None
    assert not result.metadata()["artifact_available"] and result.text_fallback_available
    assert "private trace" not in json.dumps(result.metadata())


@pytest.mark.parametrize("damage", ["missing", "silent", "truncated", "stereo", "foreign_path"])
def test_partial_or_unrelated_audio_never_accepted(config, turn, tmp_path, damage):
    lab = successful_lab(config, tmp_path)
    output = Path(lab.output_path)
    if damage == "missing":
        output.unlink()
    elif damage == "silent":
        wav(output, seconds=0.1, signal=b"\x00\x00")
    elif damage == "truncated":
        output.write_bytes(output.read_bytes()[:-2])
    elif damage == "stereo":
        wav(output, seconds=0.1, channels=2)
    else:
        lab = replace(lab, output_path=str(config.reference_path))
    result = speak(config, turn, lambda **_: lab)
    assert result.status == "failed" and not result.metadata()["artifact_available"]


def test_failure_is_content_free_text_kept_and_no_retry(config, turn):
    calls = []
    final = turn[2]
    def fail(**kwargs):
        calls.append(kwargs)
        raise RuntimeError("private filesystem path and token")
    result = speak(config, turn, fail)
    assert result.status == "failed" and result.reason == "local_tts_generation_failed"
    assert turn[0].response.response_text == final.text
    again = speak(config, turn, fail)
    assert again.reason == "final_tts_already_attempted" and len(calls) == 1
    assert "private filesystem" not in json.dumps(result.metadata())


@pytest.mark.parametrize("status,reason", [("failed", "sdk_unavailable"),
    ("timed_out", "deadline_exceeded"), ("cancelled", "cancelled")])
def test_known_failures_preserve_sanitized_status(config, turn, status, reason):
    result = speak(config, turn, lambda **_: LabResult(status, reason, "fixture", config.engine,
                                                     "fixture", output_path="private-partial"))
    assert result.status == status and result.reason == reason
    assert result.output_path is None and result.audit_event_recorded


def test_audit_failure_prevents_inference(config, turn):
    turn[0].core.observability_service.repository.record_event = lambda *_: (_ for _ in ()).throw(
        OSError("private audit failure"))
    result = speak(config, turn, lambda **_: pytest.fail("Unobserved inference"))
    assert result.reason == "local_tts_audit_unavailable" and not result.audit_event_recorded


def test_changed_reference_after_core_is_safe_fallback(config, turn):
    config.reference_path.unlink()
    result = speak(config, turn, lambda **_: pytest.fail("Invalid changed source"))
    assert result.reason == "local_tts_preflight_refused" and result.text_fallback_available


def test_default_runner_requires_real_mode_but_fixture_cannot_claim_real(config, turn, monkeypatch):
    received = []
    monkeypatch.setattr(tts, "run_voice_lab", lambda **kwargs: (received.append(kwargs), LabResult(
        "failed", "sdk_unavailable", "not-run", config.engine, "model_real"))[1])
    result = tts.speak_persisted_final(config=config, port=turn[0], request=turn[1], final=turn[2])
    assert received[0]["evidence_mode"] == "model_real"
    assert result.audio_evidence_mode == "model_real"
    assert not result.metadata()["voice_quality_approved"]


def test_final_audit_failure_does_not_promote_existing_artifact(config, turn, tmp_path):
    repository = turn[0].core.observability_service.repository
    original = repository.record_event
    def record(event):
        if event.event_name == "local_final_tts_finished":
            raise OSError("private final audit failure")
        original(event)
    repository.record_event = record
    lab = successful_lab(config, tmp_path)
    result = speak(config, turn, lambda **_: lab)
    assert result.status == "failed" and result.reason == "local_tts_audit_unavailable"
    assert result.output_path is None and not result.metadata()["artifact_available"]
    assert Path(lab.output_path).is_file()  # No destructive cleanup after failure.


def test_audit_success_requires_readback(config, turn):
    turn[0].core.observability_service.repository.record_event = lambda *_: None
    result = speak(config, turn, lambda **_: pytest.fail("Undurable audit"))
    assert result.reason == "local_tts_audit_unavailable"


def test_concurrent_attempts_emit_only_one_audio(config, turn, tmp_path):
    ready, release = Event(), Event()
    calls = []
    lab = successful_lab(config, tmp_path)
    def runner(**kwargs):
        calls.append(kwargs)
        ready.set()
        assert release.wait(10)
        return lab
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(speak, config, turn, runner)
        assert ready.wait(10)
        second = pool.submit(speak, config, turn, runner).result(timeout=10)
        release.set()
        result = first.result(timeout=10)
    assert result.status == "completed" and second.reason == "final_tts_already_attempted"
    assert len(calls) == 1


def test_reentrant_attempt_refused_before_audit_callback_returns(config, turn, tmp_path):
    repository = turn[0].core.observability_service.repository
    original = repository.record_event
    reentries = []
    def record(event):
        if event.event_name == "local_final_tts_requested":
            reentries.append(speak(config, turn, lambda **_: pytest.fail("Reentrant inference")))
        original(event)
    repository.record_event = record
    lab = successful_lab(config, tmp_path)
    result = speak(config, turn, lambda **_: lab)
    assert result.status == "completed"
    assert reentries[0].reason == "final_tts_already_attempted"


def test_unhashable_config_engine_returns_safe_fallback(config, turn):
    result = speak(replace(config, engine=[]), turn, lambda **_: pytest.fail("Invalid config"))
    assert result.status == "refused" and result.engine == "unavailable"


def test_cold_temp_preflight_never_probes_or_initializes_cache(config, monkeypatch):
    monkeypatch.setattr(tts.tempfile, "tempdir", None)
    monkeypatch.setattr(tts.tempfile, "gettempdir", lambda: pytest.fail("Cold temp probe write"))
    monkeypatch.setattr(tts.tempfile, "_candidate_tempdir_list",
                        lambda: [str(config.workspace_root.parent)])
    tts.preflight_local_tts_config(config)
    assert tts.tempfile.tempdir is None


def test_mapped_network_volume_refused_before_source_lstat(config, monkeypatch):
    def remote(path):
        raise ValueError("private remote drive mapping")
    monkeypatch.setattr(tts, "_local_volume", remote)
    monkeypatch.setattr(tts, "_plain_path", lambda *_a, **_k: pytest.fail("Remote lstat"))
    with pytest.raises(ValueError, match="local_tts_preflight_refused"):
        tts.preflight_local_tts_config(config)


def test_new_explicit_core_turn_on_same_port_can_speak(config, turn, tmp_path):
    lab = successful_lab(config, tmp_path)
    first = speak(config, turn, lambda **_: lab)
    assert first.status == "completed"
    port = turn[0]
    # Only the explicit human-turn boundary may call Core again; the complement
    # itself still cannot retry or reinterpret a previous final.
    port.core.handle_input = type(port.core).handle_input.__get__(port.core)
    request = VoiceRequest("voice-second-unit-turn", port.identity, "Outro pedido revisado.",
                           time.monotonic() + 120)
    final = port.interact(request)
    port.core.handle_input = lambda *_: pytest.fail("Complement attempted Core retry")
    second = speak(config, (port, request, final), lambda **_: lab)
    assert second.status == "completed"
