"""Voice fixture traverses real governance, canonical memory and final synthesis."""

import json
from dataclasses import replace

import pytest
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console import voice_pilot
from apps.jarvis_voice import (
    AudioFixture,
    FixtureSttPort,
    FixtureTtsPort,
    VoiceHarness,
    VoiceRequest,
)


def test_voice_pilot_uses_core_final_and_cleans_runtime(tmp_path, monkeypatch):
    composed = []
    compose = SynthesisEngine.compose_result
    cores = []
    build = voice_pilot._isolated_core

    def tracked_compose(self, synthesis_input):
        result = compose(self, synthesis_input)
        composed.append(result)
        return result

    def tracked_build(runtime):
        core = build(runtime)
        cores.append((core, runtime))
        return core

    monkeypatch.setattr(SynthesisEngine, "compose_result", tracked_compose)
    monkeypatch.setattr(voice_pilot, "_isolated_core", tracked_build)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-not-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.chdir(tmp_path)
    result = voice_pilot.run_voice_pilot()
    assert result["state"] == "completed"
    assert result["core_evidence_mode"] == "core_local"
    assert result["audio_evidence_mode"] == "synthetic_fixture"
    assert result["synthetic_speech_count"] == 1
    assert result["operation_dispatched"] is False
    assert result["hardware_audio"] is False
    assert result["operator_authenticated"] is False
    assert result["runtime_capability_promoted"] is False
    assert result["memory_record_id"] and result["core_event_count"]
    assert composed and composed[-1].response_text
    assert all(not runtime.exists() for _, runtime in cores)
    assert not list(tmp_path.iterdir())
    assert "transcript" not in json.dumps(result)


def test_reviewed_text_not_audio_or_confirmation_is_recorded(tmp_path):
    identity = voice_pilot.pilot_identity()
    core = voice_pilot._isolated_core(tmp_path / "runtime")
    port = voice_pilot.ReviewedVoiceCorePort(core, identity, clock=lambda: 0.0)
    requests = []
    handle = core.handle_input

    def tracked_handle(contract):
        requests.append(contract)
        return handle(contract)

    core.handle_input = tracked_handle
    tts = FixtureTtsPort()
    harness = VoiceHarness(
        identity=identity,
        stt=FixtureSttPort("texto incorreto"),
        tts=tts,
        core=port,
        clock=lambda: 0.0,
    )
    harness.consent(identity, granted=True)
    ticket = harness.start_capture(identity)
    assert harness.finish_capture(ticket, AudioFixture(b"\x01\x00" * 32))
    assert not requests
    revision = harness.revise_transcript(ticket, "Analise o estado do objetivo de teste.")
    assert harness.confirm_submission(ticket, identity=identity, transcript_revision=revision)
    contract = requests[0]
    assert contract.channel.value == "voice" and contract.input_type.value == "text"
    assert contract.content == "Analise o estado do objetivo de teste."
    assert contract.surface_session_id == identity.surface_session_id
    assert not contract.surface_capability_scope
    assert contract.max_autonomy_level == "assist_only"
    assert contract.action_confirmation_receipt_id is None
    assert contract.adapter_action_request is None
    turns = core.memory_service.repository.fetch_recent_turns(identity.surface_session_id, 10)
    assert turns and turns[-1].request_content == contract.content
    assert turns[-1].response_text == port.response.response_text
    assert harness.snapshot()["final_text"] == port.response.response_text
    assert tts.synthesis_count == 0
    assert harness.speak_final(ticket)
    assert tts.synthesis_count == 1


@pytest.mark.parametrize(
    "change",
    [
        {"authority": "allow"},
        {"input_mode": "raw_audio"},
        {"deadline": -1},
        {"deadline": float("nan")},
        {"text": ""},
        {"text": "\x00"},
        {"request_id": "other"},
        {"request_id": "voice-\ncontrol"},
        {"request_id": "voice-space control"},
        {"request_id": "voice-\x00control"},
        {"request_id": "voice-"},
        {"text": "x" * 4001},
    ],
)
def test_invalid_voice_requests_never_enter_core(change):
    class NeverCore:
        def handle_input(self, contract):
            pytest.fail("invalid input reached Core")

    identity = voice_pilot.pilot_identity()
    port = voice_pilot.ReviewedVoiceCorePort(NeverCore(), identity, clock=lambda: 0.0)
    request = VoiceRequest("voice-test", port.identity, "teste", 30.0)
    with pytest.raises(ValueError, match="voice_core_input_refused"):
        port.interact(replace(request, **change))


def test_foreign_identity_never_enters_core():
    class NeverCore:
        def handle_input(self, contract):
            pytest.fail("foreign identity reached Core")

    identity = voice_pilot.pilot_identity()
    port = voice_pilot.ReviewedVoiceCorePort(NeverCore(), identity, clock=lambda: 0.0)
    foreign = replace(port.identity, canonical_user_ref="user://other")
    with pytest.raises(ValueError, match="voice_core_input_refused"):
        port.interact(VoiceRequest("voice-test", foreign, "teste", 30.0))
