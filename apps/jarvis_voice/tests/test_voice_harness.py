from dataclasses import replace

import pytest

from apps.jarvis_voice import (
    AudioFixture,
    FinalSynthesis,
    FixtureCorePort,
    FixtureSttPort,
    FixtureTtsPort,
    SpeechFixture,
    Transcription,
    VoiceHarness,
)
from apps.jarvis_voice.harness import MAX_AUDIO_BYTES, MAX_EVENTS
from shared.contracts import SurfaceIdentityContract


def identity(session="voice-session", operator="operator://fixture"):
    return SurfaceIdentityContract(
        "fixture-voice", "voice", session, [], operator, "user://fixture",
    )


class Clock:
    now = 10.0

    def __call__(self):
        return self.now


@pytest.fixture
def system():
    clock, stt, tts, core = Clock(), FixtureSttPort(), FixtureTtsPort(), FixtureCorePort()
    harness = VoiceHarness(identity=identity(), stt=stt, tts=tts, core=core, clock=clock)
    return harness, clock, stt, tts, core


def capture(system):
    harness, _, _, _, _ = system
    harness.consent(identity(), granted=True)
    ticket = harness.start_capture(identity())
    return ticket


def reviewed(system):
    ticket = capture(system)
    assert system[0].finish_capture(ticket, AudioFixture(b"\x01\x00" * 16))
    return ticket


def finalized(system):
    ticket = reviewed(system)
    assert system[0].confirm_submission(
        ticket, identity=identity(),
        transcript_revision=system[0].snapshot()["transcript_revision"],
    )
    return ticket


def test_capture_requires_explicit_scoped_consent(system):
    harness, _, stt, tts, core = system
    with pytest.raises(ValueError, match="scoped_consent"):
        harness.start_capture(identity())
    assert stt.calls == tts.synthesis_count == len(core.requests) == 0
    with pytest.raises(ValueError):
        harness.consent(identity(session="other"), granted=True)
    with pytest.raises(ValueError):
        harness.consent(identity(), granted=1)
    assert harness.consent(identity(), granted=False) is False


@pytest.mark.parametrize("field,value", [
    ("surface_id", ""), ("surface_kind", "web"), ("surface_session_id", "x\nsecret"),
    ("operator_identity_ref", None), ("canonical_user_ref", ""),
    ("surface_capability_scope", ["execute"]), ("surface_id", "a" * 201),
    ("surface_session_id", 5),
    ("surface_capability_scope", None), ("surface_continuity_status", "switched"),
], ids=lambda value: type(value).__name__)
def test_invalid_or_authoritative_identity_refused(field, value):
    source = identity()
    setattr(source, field, value)
    with pytest.raises(ValueError):
        VoiceHarness(identity=source, stt=FixtureSttPort(), tts=FixtureTtsPort(),
                     core=FixtureCorePort())


def test_identity_is_frozen_copy_not_mutable_shared_contract(system):
    original = identity()
    harness = VoiceHarness(identity=original, stt=FixtureSttPort(), tts=FixtureTtsPort(),
                           core=FixtureCorePort())
    original.operator_identity_ref = "operator://attacker"
    original.surface_capability_scope.append("execute")
    assert harness.identity.operator_identity_ref == "operator://fixture"
    with pytest.raises(ValueError):
        harness.consent(original, granted=True)
    with pytest.raises(AttributeError):
        harness.identity = harness.identity


@pytest.mark.parametrize("seconds", [0, -1, 61, True, float("nan"), float("inf"), "30"])
def test_invalid_deadline(system, seconds):
    system[0].consent(identity(), granted=True)
    with pytest.raises(ValueError):
        system[0].start_capture(identity(), deadline_seconds=seconds)


@pytest.mark.parametrize("audio,error", [
    (AudioFixture(b""), "invalid_audio"),
    (AudioFixture(b"\x01"), "invalid_audio"),
    (AudioFixture(b"\x00\x00" * 16), "silence"),
    (AudioFixture(b"\x01\x00", sample_rate=48000), "invalid_audio"),
    (AudioFixture(b"\x01\x00", channels=True), "invalid_audio"),
    (AudioFixture(b"\x01\x00", channels=2), "invalid_audio"),
    (AudioFixture(b"\x01\x00", sample_format="mp3"), "invalid_audio"),
    (AudioFixture(b"\x01\x00", evidence_mode="microphone"), "invalid_audio"),
    (AudioFixture(bytearray(b"\x01\x00")), "invalid_audio"),
    (AudioFixture(b"\x01\x00" * (MAX_AUDIO_BYTES // 2 + 1)), "invalid_audio"),
    (None, "invalid_audio"),
], ids=lambda value: type(value).__name__)
def test_audio_silence_format_size_before_stt(system, audio, error):
    ticket = capture(system)
    assert system[0].finish_capture(ticket, audio) is False
    assert system[0].snapshot()["error_code"] == error
    assert system[2].calls == 0
    assert system[4].requests == []


@pytest.mark.parametrize("text,status", [
    ("partial", "incomplete"), ("partial", "error"), ("partial", "unknown"),
    ("", "completed"), ("  ", "completed"), ("a" * 4001, "completed"),
    ("secret\x00", "completed"), ("\ud800", "completed"), (None, "completed"),
], ids=lambda value: type(value).__name__)
def test_partial_or_invalid_transcript_never_submitted(system, text, status):
    system[2].text, system[2].status = text, status
    assert not system[0].finish_capture(capture(system), AudioFixture(b"\x01\x00"))
    assert system[0].snapshot()["transcript"] is None
    assert system[4].requests == []


def test_review_is_explicit_exact_and_one_shot(system):
    ticket = reviewed(system)
    harness, _, _, tts, core = system
    revision = harness.snapshot()["transcript_revision"]
    assert core.requests == []
    assert not harness.speak_final(ticket)
    assert not harness.confirm_submission(ticket, identity=identity(), transcript_revision="wrong")
    assert not harness.confirm_submission(ticket, identity=identity(session="other"),
                                          transcript_revision=revision)
    new_revision = harness.revise_transcript(ticket, "Excluir tudo é somente texto a revisar.")
    assert new_revision != revision
    assert not harness.confirm_submission(ticket, identity=identity(), transcript_revision=revision)
    assert harness.confirm_submission(ticket, identity=identity(), transcript_revision=new_revision)
    assert core.requests[0].text == "Excluir tudo é somente texto a revisar."
    assert core.requests[0].authority == "none"
    assert core.requests[0].input_mode == "reviewed_voice_fixture"
    assert not harness.confirm_submission(ticket, identity=identity(),
                                          transcript_revision=new_revision)
    assert len(core.requests) == 1
    assert tts.synthesis_count == 0


def test_ticket_replay_after_new_capture_refused(system):
    old = reviewed(system)
    new = system[0].start_capture(identity())
    assert new.generation > old.generation
    assert not system[0].finish_capture(old, AudioFixture(b"\x01\x00"))
    assert not system[0].finish_capture(replace(new, request_id="forged"),
                                       AudioFixture(b"\x01\x00"))
    assert system[2].calls == 1


@pytest.mark.parametrize("field,value", [
    ("request_id", "another"), ("identity", None), ("status", "incomplete"),
    ("confirmed", False), ("confirmed", 1), ("evidence_mode", "provider"),
    ("synthesis_ref", ""), ("text", ""), ("text", "a" * 4001),
], ids=lambda value: type(value).__name__)
def test_only_exact_confirmed_core_final_is_speakable(system, field, value):
    harness, _, _, tts, core = system
    original = core.interact
    core.interact = lambda request: replace(original(request), **{field: value})
    ticket = reviewed(system)
    assert not harness.confirm_submission(
        ticket, identity=identity(), transcript_revision=harness.snapshot()["transcript_revision"],
    )
    assert harness.snapshot()["final_text"] is None
    assert not harness.speak_final(ticket)
    assert tts.synthesis_count == 0


def test_late_stt_cancelled_during_port_call_discarded(system):
    harness, _, stt, _, _ = system
    stt.transcribe = lambda audio, ticket: (harness.cancel(), Transcription("late"))[1]
    assert not harness.finish_capture(capture(system), AudioFixture(b"\x01\x00"))
    assert harness.snapshot()["state"] == "cancelled"
    assert harness.snapshot()["transcript"] is None


def test_identity_switch_during_core_call_discards_final_and_revokes_consent(system):
    harness, _, _, _, core = system
    original = core.interact

    def changed(request):
        harness.switch_identity(identity(session="second-session"))
        return original(request)

    core.interact = changed
    ticket = reviewed(system)
    assert not harness.confirm_submission(
        ticket, identity=identity(), transcript_revision=harness.snapshot()["transcript_revision"],
    )
    assert harness.snapshot()["final_text"] is None
    assert harness.snapshot()["capture_consent"] is False
    assert harness.snapshot()["state"] == "idle"
    assert not harness.speak_final(ticket)


@pytest.mark.parametrize("stage", ["stt", "core", "tts"])
def test_deadline_after_provider_call_discards_late_result(system, stage):
    harness, clock, stt, tts, core = system
    port, method = {"stt": (stt, "transcribe"), "core": (core, "interact"),
                    "tts": (tts, "synthesize")}[stage]
    original = getattr(port, method)

    def expired(*args):
        clock.now += 31
        return original(*args)

    setattr(port, method, expired)
    if stage == "stt":
        assert not harness.finish_capture(capture(system), AudioFixture(b"\x01\x00"))
    elif stage == "core":
        ticket = reviewed(system)
        assert not harness.confirm_submission(
            ticket, identity=identity(),
            transcript_revision=harness.snapshot()["transcript_revision"],
        )
    else:
        assert not harness.speak_final(finalized(system))
        assert harness.snapshot()["final_text"] == core.text
        assert tts.stop_count == 1
    assert harness.snapshot()["error_code"] == "deadline_exceeded"


@pytest.mark.parametrize("stage", ["stt", "core", "tts"])
def test_port_errors_are_redacted_and_final_text_survives_tts_failure(system, stage):
    harness, _, stt, tts, core = system

    def broken(*args):
        raise RuntimeError("private-token-123")

    if stage == "stt":
        stt.transcribe = broken
        assert not harness.finish_capture(capture(system), AudioFixture(b"\x01\x00"))
    elif stage == "core":
        core.interact = broken
        ticket = reviewed(system)
        assert not harness.confirm_submission(
            ticket, identity=identity(),
            transcript_revision=harness.snapshot()["transcript_revision"],
        )
    else:
        ticket = finalized(system)
        tts.synthesize = broken
        assert not harness.speak_final(ticket)
        assert harness.snapshot()["final_text"] == core.text
    assert "private-token" not in str(harness.snapshot()) + str(harness.events())
    assert harness.snapshot()["error_code"] == stage + "_failed"


def test_interrupt_during_tts_discards_late_audio_keeps_text(system):
    harness, _, _, tts, core = system
    original = tts.synthesize
    tts.synthesize = lambda final, ticket: (harness.interrupt_playback(),
                                           original(final, ticket))[1]
    assert not harness.speak_final(finalized(system))
    assert harness.snapshot()["state"] == "interrupted"
    assert harness.snapshot()["final_text"] == core.text
    assert tts.stop_count == 1


@pytest.mark.parametrize("field,value", [
    ("request_id", "wrong"), ("synthesis_ref", "wrong"), ("status", "incomplete"),
    ("evidence_mode", "recorded_actor"), ("data", b""), ("data", b"\x01"),
    ("data", bytearray(b"\x01\x00")), ("data", b"\x01\x00" * (MAX_AUDIO_BYTES // 2 + 1)),
], ids=lambda value: type(value).__name__)
def test_invalid_or_partial_speech_preserves_text_without_playing(system, field, value):
    harness, _, _, tts, core = system
    original = tts.synthesize
    tts.synthesize = lambda final, ticket: replace(original(final, ticket), **{field: value})
    assert not harness.speak_final(finalized(system))
    assert harness.snapshot()["final_text"] == core.text
    assert harness.snapshot()["state"] == "error"


def test_playback_expiry_is_caller_driven_and_stops_fixture(system):
    harness, clock, _, tts, core = system
    ticket = finalized(system)
    assert harness.speak_final(ticket)
    clock.now += 30
    assert not harness.complete_playback(ticket)
    assert harness.snapshot()["error_code"] == "deadline_exceeded"
    assert harness.snapshot()["final_text"] == core.text
    assert tts.stop_count == 1


def test_revoke_stops_fixture_and_clears_sensitive_display(system):
    ticket = finalized(system)
    assert system[0].speak_final(ticket)
    assert not system[0].consent(identity(), granted=False)
    assert system[0].snapshot()["final_text"] is None
    assert system[0].snapshot()["capture_consent"] is False
    assert system[3].stop_count == 1
    assert not system[0].complete_playback(ticket)


def test_identity_switch_is_atomic_before_stop_callback(system):
    harness, _, _, tts, _ = system
    ticket = finalized(system)
    assert harness.speak_final(ticket)
    attempted = []

    def stopped(request_id):
        attempted.append(harness.snapshot()["capture_consent"])
        with pytest.raises(ValueError):
            harness.start_capture(identity())

    tts.stop = stopped
    harness.switch_identity(identity(session="next"))
    assert attempted == [False]
    assert harness.snapshot()["state"] == "idle"
    assert harness.snapshot()["transcript"] is None
    assert harness.snapshot()["final_text"] is None


def test_busy_capture_does_not_restart_or_duplicate_ports(system):
    capture(system)
    with pytest.raises(ValueError, match="busy"):
        system[0].start_capture(identity())
    assert system[2].calls == 0


def test_deadline_before_stt_and_before_confirm_prevents_port_calls(system):
    ticket = capture(system)
    system[1].now += 30
    assert not system[0].finish_capture(ticket, AudioFixture(b"\x01\x00"))
    assert system[2].calls == 0
    system[0].cancel()
    ticket = reviewed(system)
    revision = system[0].snapshot()["transcript_revision"]
    system[1].now += 30
    assert not system[0].confirm_submission(ticket, identity=identity(),
                                           transcript_revision=revision)
    assert system[4].requests == []


def test_stop_failure_redacted_does_not_restore_playback(system):
    harness, _, _, tts, _ = system
    assert harness.speak_final(finalized(system))

    def broken(request_id):
        raise RuntimeError("private-secret-stop")

    tts.stop = broken
    assert harness.interrupt_playback()
    assert harness.snapshot()["state"] == "interrupted"
    assert "private-secret" not in str(harness.events())
    assert "voice_fixture_stop_failed" in [event["name"] for event in harness.events()]


def test_events_bounded_detached_content_free(system):
    finalized(system)
    harness = system[0]
    events = harness.events()
    assert not any(word in str(events) for word in (
        system[2].text, system[4].text, "operator://fixture", "user://fixture", "voice-session",
    ))
    events[0]["name"] = "tampered"
    assert harness.events()[0]["name"] != "tampered"
    for _ in range(MAX_EVENTS + 5):
        harness.cancel()
    assert len(harness.events()) == MAX_EVENTS


def test_clock_regression_or_nonfinite_fail_closed(system):
    ticket = capture(system)
    system[1].now = 9
    assert not system[0].finish_capture(ticket, AudioFixture(b"\x01\x00"))
    assert system[0].snapshot()["error_code"] == "invalid_clock"


def test_display_repr_omits_sensitive_content():
    assert "secret" not in repr(AudioFixture(b"secret"))
    assert "secret" not in repr(Transcription("secret"))
    assert "secret" not in repr(SpeechFixture(b"secret", "request", "synthesis"))
    assert "secret" not in repr(FinalSynthesis("request", None, "secret", "synthesis"))
