"""Explicit synthetic voice demonstration; never uses an audio device."""

import json
from argparse import ArgumentParser

from shared.contracts import SurfaceIdentityContract

from .harness import (
    AudioFixture,
    FixtureCorePort,
    FixtureSttPort,
    FixtureTtsPort,
    VoiceHarness,
)


def main(argv: list[str] | None = None) -> int:
    parser = ArgumentParser(description="Demonstrador de voz fixture, sem áudio real.")
    parser.add_argument("--consent", action="store_true", help="Consentir com captura simulada.")
    parser.add_argument("--scenario", choices=("completed", "interrupted", "incomplete", "silence"),
                        default="completed")
    args = parser.parse_args(argv)
    if not args.consent:
        print(json.dumps({"mode": "isolated_voice_fixture", "error_code": "consent_required"}))
        return 2
    identity = SurfaceIdentityContract(
        "voice-fixture", "voice", "voice-fixture-session", [], "operator:fixture", "user:fixture",
    )
    voice = VoiceHarness(
        identity=identity, stt=FixtureSttPort(status=(
            "incomplete" if args.scenario == "incomplete" else "completed"
        )), tts=FixtureTtsPort(), core=FixtureCorePort(),
    )
    voice.consent(identity, granted=True)
    ticket = voice.start_capture(identity)
    audio = b"\x00\x00" if args.scenario == "silence" else b"\x01\x00"
    if voice.finish_capture(ticket, AudioFixture(audio)):
        if voice.confirm_submission(
            ticket, identity=identity, transcript_revision=voice.snapshot()["transcript_revision"],
        ) and voice.speak_final(ticket):
            if args.scenario == "interrupted":
                voice.interrupt_playback()
            else:
                voice.complete_playback(ticket)
    print(json.dumps(voice.snapshot(), ensure_ascii=True))
    return 0 if voice.snapshot()["state"] in ("completed", "interrupted") else 1


if __name__ == "__main__":
    raise SystemExit(main())
