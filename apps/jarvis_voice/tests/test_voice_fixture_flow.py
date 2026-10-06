"""Surface E2E with explicitly declared STT/Core/TTS doubles, not real audio/Core."""

from apps.jarvis_voice import (
    AudioFixture,
    FixtureCorePort,
    FixtureSttPort,
    FixtureTtsPort,
    VoiceHarness,
)
from shared.contracts import SurfaceIdentityContract


def test_push_to_talk_review_core_final_text_speech_and_interrupt_with_doubles():
    identity = SurfaceIdentityContract(
        "voice-fixture", "voice", "session-fixture", [], "operator://fixture", "user://fixture",
    )
    stt = FixtureSttPort("Uma transcrição final simulada, ainda não enviada.")
    core, tts = FixtureCorePort("Síntese final do Core double."), FixtureTtsPort()
    voice = VoiceHarness(identity=identity, stt=stt, tts=tts, core=core)
    assert voice.consent(identity, granted=True)
    ticket = voice.start_capture(identity)
    assert voice.finish_capture(ticket, AudioFixture(b"\x01\x00" * 16))
    assert core.requests == []
    reviewed_revision = voice.revise_transcript(ticket, "Texto revisto pelo operador.")
    assert voice.confirm_submission(
        ticket, identity=identity, transcript_revision=reviewed_revision,
    )
    assert core.requests[0].text == "Texto revisto pelo operador."
    assert voice.snapshot()["final_text"] == "Síntese final do Core double."
    assert voice.snapshot()["final_evidence_mode"] == "fixture"
    assert voice.speak_final(ticket)
    assert voice.interrupt_playback()
    assert voice.snapshot()["final_text"] == "Síntese final do Core double."
    assert tts.stop_count == 1
    assert not voice.complete_playback(ticket)
    assert voice.snapshot()["hardware_audio"] is False
    assert voice.snapshot()["tool_authority"] == "none"


def test_fixture_completion_never_claims_real_playback():
    identity = SurfaceIdentityContract("v", "voice", "s", [], "operator:fixture", "user:fixture")
    voice = VoiceHarness(identity=identity, stt=FixtureSttPort(), tts=FixtureTtsPort(),
                         core=FixtureCorePort())
    voice.consent(identity, granted=True)
    ticket = voice.start_capture(identity)
    voice.finish_capture(ticket, AudioFixture(b"\x01\x00"))
    assert voice.confirm_submission(ticket, identity=identity,
                                    transcript_revision=voice.snapshot()["transcript_revision"])
    assert voice.speak_final(ticket)
    assert voice.complete_playback(ticket)
    assert voice.snapshot()["state"] == "completed"
    assert voice.snapshot()["voice_identity"] == "synthetic_fixture"
    assert "voice_fixture_playback_completed" in [event["name"] for event in voice.events()]
