"""Persistent reviewed transcript -> real Core -> explicit fixture audio complement.

SQLite/governance/synthesis/memory are real and survive restart. Short synthesis
and generated WAVs are explicit synthetic fixtures, not model/voice-quality,
microphone, identity, playback or production-runtime evidence.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import sys
import tempfile
import wave
from argparse import Namespace
from dataclasses import replace
from pathlib import Path

import pytest
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console.runtime import ConsoleCommandError
from apps.jarvis_console.transcript_review_cli import run_transcript_review
from apps.jarvis_console.voice_pilot import _isolated_core
from apps.jarvis_voice_lab import LabResult, run_voice_lab

SESSION = "persistent-transcript-tts-e2e"
REVIEWED = "  Explique o significado de agente.\r\nAção, café, e\u0301 e 🧠.\t "
FINAL = "  Síntese final fixture: ação, café, e\u0301 e 🧠.\r\nSem executar operações.  "


def _envelope(text=REVIEWED):
    document = {
        "review_required": True,
        "language": "Portuguese",
        "audio_duration_seconds": 10,
        "segments": [
            {
                "start_seconds": 0,
                "end_seconds": 10,
                "timestamps_estimated": False,
                "text": "Rascunho não confiável.",
            }
        ],
    }
    raw = json.dumps(document, ensure_ascii=False).encode()
    return {
        "schema_version": "jarvis-transcript-handoff-v1",
        "authority": "none",
        "source_origin": "unverified",
        "document_utf8_b64": base64.b64encode(raw).decode(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "reviewed_text": text,
        "reviewed_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "review_revision": 37,
    }


def _stdin(monkeypatch, envelope=None):
    envelope = _envelope() if envelope is None else envelope
    source = envelope if isinstance(envelope, str) else json.dumps(envelope, ensure_ascii=True)
    monkeypatch.setattr(sys, "stdin", io.StringIO(source))


def _wav(path, *, seconds=0.1, rate=16000):
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x02\x00" * int(rate * seconds))


@pytest.fixture
def tts_args(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    reference = tmp_path / "reference.wav"
    _wav(reference, seconds=15)
    model = tmp_path / "model"
    model.mkdir()
    python = tmp_path / "python-stub.exe"
    python.write_bytes(b"fixture executable is never executed")
    return Namespace(
        authorized=True,
        include_content=False,
        session_id=SESSION,
        tts_authorized=True,
        tts_engine="qwen3_tts",
        tts_reference=str(reference),
        tts_model_dir=str(model),
        tts_python=str(python),
        tts_workspace=str(workspace),
        tts_device="cpu",
        tts_sdk_source_dir=None,
        tts_timeout=30,
        tts_voice_profile="baseline",
        tts_reference_start=0,
        tts_reference_duration=10,
        tts_reference_transcript=None,
        tts_transcript_confirmed=False,
        tts_seed=None,
        tts_show_output_path=False,
    )


def _short_final(monkeypatch, text=FINAL):
    original = SynthesisEngine.compose_result
    composed = []

    def compose(self, synthesis_input):
        result = replace(original(self, synthesis_input), response_text=text)
        composed.append(result)
        return result

    monkeypatch.setattr(SynthesisEngine, "compose_result", compose)
    return composed


def _core(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    core = _isolated_core(runtime)
    calls = []
    handle = core.handle_input

    def tracked(contract):
        calls.append(contract)
        return handle(contract)

    monkeypatch.setattr(core, "handle_input", tracked)
    monkeypatch.setattr(
        core.operational_service,
        "execute",
        lambda *_a, **_kw: pytest.fail("transcript/TTS dispatched an operation"),
    )
    return core, calls, runtime


def _assert_persisted(core, calls, runtime, *, reviewed=REVIEWED, final=None):
    assert len(calls) == 1
    contract = calls[0]
    assert contract.content == reviewed and contract.channel.value == "voice"
    assert contract.requested_autonomy_level == contract.max_autonomy_level == "assist_only"
    assert contract.surface_capability_scope == []
    assert contract.action_confirmation_receipt_id is None
    assert contract.adapter_action_request is None
    turns = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == 1 and turns[0].request_content == reviewed
    if final is not None:
        assert turns[0].response_text == final
    events = core.observability_service.repository.list_events(
        request_id=contract.request_id, session_id=SESSION, limit=100
    )
    names = [event.event_name for event in events]
    for name in ("governance_checked", "response_synthesized", "memory_recorded"):
        assert names.count(name) == 1
    restarted = _isolated_core(runtime)
    records = restarted.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(records) == 1
    assert records[0].request_content == reviewed
    assert records[0].response_text == turns[0].response_text
    return turns[0], events


def _assert_audio_audit(core, calls, runtime, *, requested=True):
    events = core.observability_service.repository.list_events(
        request_id=calls[0].request_id, session_id=SESSION, limit=100
    )
    names = [event.event_name for event in events]
    assert names.count("local_final_tts_requested") == int(requested)
    assert names.count("local_final_tts_finished") == 1
    assert names.index("memory_recorded") < names.index("local_final_tts_finished")
    if requested:
        assert names.index("memory_recorded") < names.index("local_final_tts_requested")
        assert names.index("local_final_tts_requested") < names.index("local_final_tts_finished")
    records = [event for event in events if event.event_name.startswith("local_final_tts_")]
    for event in records:
        assert event.request_id == calls[0].request_id and event.session_id == SESSION
        assert event.payload["authority"] == "none"
        assert event.payload["hardware_audio"] is False
        assert event.payload["runtime_capability_promoted"] is False
        serialized = json.dumps(event.payload, ensure_ascii=False)
        for private in (REVIEWED, FINAL, str(runtime.parent), "reference.wav", "sample.wav"):
            assert private not in serialized
    repository = core.observability_service.repository
    # Both actual builders are exercised: the standalone console uses a
    # different observability filename from the isolated Core helper.
    restarted_repository = type(repository)(repository.database_path)
    persisted = restarted_repository.list_events(
        request_id=calls[0].request_id,
        session_id=SESSION,
        event_names=("local_final_tts_requested", "local_final_tts_finished"),
        limit=10,
    )
    assert [event.event_id for event in persisted] == [event.event_id for event in records]


def _fixture_lab(tmp_path, forwarded, **changes):
    def runner(**kwargs):
        forwarded.append(kwargs)

        def worker(request):
            output = Path(request["output_path"])
            assert output.is_relative_to(tmp_path)
            _wav(output)
            return {"status": "completed", "run_id": request["run_id"], "engine": request["engine"]}

        result = run_voice_lab(**kwargs, fixture_worker=worker)
        return replace(result, **changes)

    return runner


@pytest.mark.parametrize(
    "engine,profile",
    [
        ("qwen3_tts", "baseline"),
        ("qwen3_tts", "qwen_icl"),
        ("qwen3_tts", "qwen_icl_draft"),
        ("chatterbox_pt_br", "baseline"),
        ("chatterbox_pt_br", "chatterbox_conversational"),
    ],
)
def test_exact_persisted_final_only_reaches_explicit_fixture_audio(
    engine, profile, tts_args, tmp_path, monkeypatch
):
    composed = _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.tts_engine, tts_args.tts_voice_profile = engine, profile
    tts_args.tts_seed = 123
    if profile in {"qwen_icl", "qwen_icl_draft"}:
        tts_args.tts_reference_transcript = "Transcrição exata da referência sintética."
        tts_args.tts_transcript_confirmed = profile == "qwen_icl"
        tts_args.tts_reference_start = 2
        tts_args.tts_reference_duration = 12
    forwarded = []
    runner = _fixture_lab(tmp_path, forwarded)

    def verify_before_audio(**kwargs):
        turn, _ = _assert_persisted(core, calls, runtime, final=FINAL)
        assert kwargs["text"] == turn.response_text == composed[0].response_text
        assert kwargs["text"] != REVIEWED
        return runner(**kwargs)

    _stdin(monkeypatch)
    encoded = run_transcript_review(tts_args, lambda: core, lab_runner=verify_before_audio).outputs[
        0
    ]
    payload = json.loads(encoded)
    assert payload["canonical_turn_recorded"] is True
    assert payload["operation_dispatched"] is False
    tts = payload["tts"]
    assert tts["status"] == "completed" and tts["audio_evidence_mode"] == "fixture"
    assert tts["artifact_available"] is True
    assert tts["voice_quality_approved"] is False
    assert tts["final_character_count"] == len(FINAL)
    assert tts["text_fallback_available"] is True and tts["audit_event_recorded"] is True
    assert len(forwarded) == 1 and len(composed) == 1
    args = forwarded[0]
    assert args["authorized"] is True and args["evidence_mode"] == "fixture"
    assert args["engine"] == engine and args["voice_profile"] == profile
    assert args["reference_path"] == Path(tts_args.tts_reference)
    assert args["model_dir"] == Path(tts_args.tts_model_dir)
    assert args["python_executable"] == Path(tts_args.tts_python)
    assert args["workspace_root"] == Path(tts_args.tts_workspace)
    assert args["reference_start_seconds"] == tts_args.tts_reference_start
    assert args["reference_duration_seconds"] == tts_args.tts_reference_duration
    assert args["reference_transcript"] == tts_args.tts_reference_transcript
    assert args["transcript_confirmed"] is tts_args.tts_transcript_confirmed
    assert args["seed"] == 123
    for private in (
        REVIEWED,
        FINAL,
        str(tmp_path),
        "sample.wav",
        "Transcrição exata da referência sintética.",
    ):
        assert private not in encoded
    assert "final_text" not in payload and "output_path" not in tts
    _assert_persisted(core, calls, runtime, final=FINAL)
    _assert_audio_audit(core, calls, runtime)


@pytest.mark.parametrize("failure", ["failed", "timed_out", "cancelled", "throw"])
def test_audio_failure_preserves_persisted_text_without_second_core(
    failure, tts_args, tmp_path, monkeypatch
):
    _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.include_content = True
    forwarded = []

    def runner(**kwargs):
        forwarded.append(kwargs)
        if failure == "throw":
            raise RuntimeError("private-audio-path-password=never-display")
        return LabResult(
            failure,
            {
                "failed": "sdk_unavailable",
                "timed_out": "deadline_exceeded",
                "cancelled": "cancelled",
            }[failure],
            "fixture-failure",
            kwargs["engine"],
            "fixture",
        )

    _stdin(monkeypatch)
    encoded = run_transcript_review(tts_args, lambda: core, lab_runner=runner).outputs[0]
    payload = json.loads(encoded)
    assert payload["final_text"] == FINAL and payload["reviewed_text"] == REVIEWED
    assert payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] != "completed"
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["text_fallback_available"] is True
    assert payload["tts"]["audit_event_recorded"] is True
    assert "private-audio-path" not in encoded
    assert len(forwarded) == 1 and forwarded[0]["text"] == FINAL
    _assert_persisted(core, calls, runtime, final=FINAL)
    _assert_audio_audit(core, calls, runtime)


def test_actual_default_core_long_final_kept_exact_without_truncation(
    tts_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.include_content = True
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(
            tts_args, lambda: core, lab_runner=lambda **_: pytest.fail("long final entered audio")
        ).outputs[0]
    )
    turn, _ = _assert_persisted(core, calls, runtime)
    assert len(turn.response_text) > 600
    assert payload["final_text"] == turn.response_text
    assert payload["tts"]["status"] == "refused"
    assert payload["tts"]["reason"] == "final_text_too_long"
    assert payload["tts"]["final_character_count"] == len(turn.response_text)
    assert payload["tts"]["artifact_available"] is False
    _assert_audio_audit(core, calls, runtime, requested=False)


@pytest.mark.parametrize("size", [600, 601])
def test_audio_limit_applies_to_canonical_final_not_reviewed_input(
    size, tts_args, tmp_path, monkeypatch
):
    final = "🧠" * size
    _short_final(monkeypatch, final)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    forwarded = []
    _stdin(monkeypatch)
    result = json.loads(
        run_transcript_review(
            tts_args, lambda: core, lab_runner=_fixture_lab(tmp_path, forwarded)
        ).outputs[0]
    )
    assert result["tts"]["final_character_count"] == size
    assert result["tts"]["status"] == ("completed" if size == 600 else "refused")
    assert len(forwarded) == (1 if size == 600 else 0)
    if forwarded:
        assert forwarded[0]["text"] == final
    _assert_persisted(core, calls, runtime, final=final)


@pytest.mark.parametrize(
    "updates",
    [
        {"tts_authorized": False},
        {"tts_authorized": "yes"},
        {"tts_authorized": 1},
        {"tts_engine": "remote"},
        {"tts_device": "cuda:1"},
        {"tts_timeout": float("nan")},
        {"tts_timeout": 0},
        {"tts_timeout": 1801},
        {"tts_timeout": True},
        {"tts_voice_profile": "unknown"},
        {"tts_seed": True},
        {"tts_seed": -1},
        {"tts_seed": 2**32},
        {"tts_reference_start": -1},
        {"tts_reference_duration": 2},
        {"tts_reference_duration": 16},
        {"tts_reference_start": float("inf")},
        {"tts_reference_transcript": "unused-private-reference"},
        {"tts_transcript_confirmed": True},
        {"tts_show_output_path": 1},
        {"tts_voice_profile": "qwen_icl", "tts_reference_transcript": "unconfirmed"},
        {
            "tts_engine": "chatterbox_pt_br",
            "tts_voice_profile": "qwen_icl",
            "tts_reference_transcript": "confirmed",
            "tts_transcript_confirmed": True,
        },
    ],
)
def test_invalid_audio_config_or_absent_audio_consent_prevents_core_and_lab(
    updates, tts_args, monkeypatch
):
    for key, value in updates.items():
        setattr(tts_args, key, value)

    class NeverRead:
        def isatty(self):
            pytest.fail("invalid audio config inspected stdin")

        def read(self, *_args):
            pytest.fail("invalid audio config consumed stdin")

    monkeypatch.setattr(sys, "stdin", NeverRead())
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(
            tts_args,
            lambda: pytest.fail("invalid audio config bootstrapped Core"),
            lab_runner=lambda **_: pytest.fail("invalid audio config entered lab"),
        )


@pytest.mark.parametrize("mutation", ["hash", "authority", "extra", "duplicate", "bom"])
def test_invalid_envelope_with_audio_consent_prevents_core_and_lab(mutation, tts_args, monkeypatch):
    envelope = _envelope()
    if mutation == "hash":
        envelope["reviewed_sha256"] = "f" * 64
    elif mutation == "authority":
        envelope["authority"] = "trusted"
    elif mutation == "extra":
        envelope["tts_authorized"] = True
    elif mutation == "duplicate":
        envelope = json.dumps(envelope)[:-1] + ',"authority":"none"}'
    else:
        envelope = "\ufeff" + json.dumps(envelope)
    _stdin(monkeypatch, envelope)
    monkeypatch.setattr(
        "apps.jarvis_console.persistent_tts.preflight_local_tts_config",
        lambda _: pytest.fail("invalid envelope inspected audio files"),
    )
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(
            tts_args,
            lambda: pytest.fail("invalid envelope bootstrapped Core"),
            lab_runner=lambda **_: pytest.fail("invalid envelope entered audio"),
        )


def test_explicit_sensitive_content_display_is_withheld_without_mutating_canonical_text(
    tts_args, tmp_path, monkeypatch
):
    final = "Resposta literal: password=synthetic-private-final"
    reviewed = "Explique esta nota: password=synthetic-private-review"
    _short_final(monkeypatch, final)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.include_content = True
    forwarded = []
    _stdin(monkeypatch, _envelope(reviewed))
    encoded = run_transcript_review(
        tts_args, lambda: core, lab_runner=_fixture_lab(tmp_path, forwarded)
    ).outputs[0]
    payload = json.loads(encoded)
    assert payload["content_withheld"] is True and payload["content_included"] is False
    assert "final_text" not in payload and "reviewed_text" not in payload
    assert "synthetic-private" not in encoded
    assert forwarded[0]["text"] == final
    _assert_persisted(core, calls, runtime, reviewed=reviewed, final=final)


@pytest.mark.parametrize(
    "bad_lab",
    [
        {"engine": "chatterbox_pt_br"},
        {"evidence_mode": "model_real"},
        {"output_path": None},
        {"output_digest": "f" * 64},
        {"duration_seconds": 999},
        {"sample_rate": 1},
    ],
)
def test_malformed_audio_result_cannot_claim_completion_or_erase_final(
    bad_lab, tts_args, tmp_path, monkeypatch
):
    _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    forwarded = []
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(
            tts_args, lambda: core, lab_runner=_fixture_lab(tmp_path, forwarded, **bad_lab)
        ).outputs[0]
    )
    assert payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] != "completed"
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["text_fallback_available"] is True
    assert len(forwarded) == 1
    _assert_persisted(core, calls, runtime, final=FINAL)
    _assert_audio_audit(core, calls, runtime)


def test_audio_artifact_locator_is_explicit_relative_and_resolves_generated_fixture(
    tts_args, tmp_path, monkeypatch
):
    _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.tts_show_output_path = True
    forwarded = []
    _stdin(monkeypatch)
    encoded = run_transcript_review(
        tts_args, lambda: core, lab_runner=_fixture_lab(tmp_path, forwarded)
    ).outputs[0]
    payload = json.loads(encoded)
    assert payload["tts"]["status"] == "completed"
    assert payload["tts"]["output_location_available"] is True
    location = payload["tts"]["output_location"]
    assert location["base"] == "system_temporary_directory"
    relative = Path(location["relative_path"])
    assert not relative.is_absolute() and len(relative.parts) == 2
    assert ".." not in relative.parts and relative.name == "sample.wav"
    output = tmp_path / relative
    assert output.is_file()
    with wave.open(str(output), "rb") as audio:
        assert audio.getframerate() == 16000 and audio.getnframes() == 1600
    assert str(tmp_path) not in encoded
    assert "output_path" not in payload["tts"]
    _assert_persisted(core, calls, runtime, final=FINAL)


@pytest.mark.parametrize(
    "preflight_failure",
    [
        "missing_reference",
        "reference_directory",
        "silent_reference",
        "window_outside",
        "missing_model",
        "missing_python",
    ],
)
def test_readonly_audio_preflight_refusal_creates_no_core_or_output(
    preflight_failure, tts_args, tmp_path, monkeypatch
):
    if preflight_failure == "missing_reference":
        tts_args.tts_reference = str(tmp_path / "missing.wav")
    elif preflight_failure == "reference_directory":
        tts_args.tts_reference = tts_args.tts_model_dir
    elif preflight_failure == "silent_reference":
        with wave.open(tts_args.tts_reference, "wb") as audio:
            audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            audio.writeframes(b"\x00\x00" * 16000 * 15)
    elif preflight_failure == "window_outside":
        tts_args.tts_reference_start = 10
        tts_args.tts_reference_duration = 10
    elif preflight_failure == "missing_model":
        tts_args.tts_model_dir = str(tmp_path / "missing-model")
    else:
        tts_args.tts_python = str(tmp_path / "missing-python")
    before = {path.relative_to(tmp_path) for path in tmp_path.rglob("*")}
    _stdin(monkeypatch)
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(
            tts_args,
            lambda: pytest.fail("failed preflight created Core"),
            lab_runner=lambda **_: pytest.fail("failed preflight created audio"),
        )
    assert {path.relative_to(tmp_path) for path in tmp_path.rglob("*")} == before


@pytest.mark.parametrize("audio_status", ["completed", "failed"])
def test_actual_registered_cli_preserves_persistent_final_with_audio_complement(
    audio_status, tts_args, tmp_path, monkeypatch, capsys
):
    from apps.jarvis_console import cli, transcript_review_cli
    from apps.jarvis_console.bootstrap import ROOT

    _short_final(monkeypatch)
    real_build = cli.JarvisConsole.build
    original_run = transcript_review_cli.run_transcript_review
    constructions = []
    calls = []
    cores = []
    runtime = tmp_path / "runtime"

    def build(**kwargs):
        assert kwargs == {
            "runtime_dir": ROOT / ".jarvis_runtime" / "console",
            "local_observability_only": True,
        }
        constructions.append(kwargs)
        console = real_build(runtime_dir=runtime, local_observability_only=True)
        core = console.orchestrator
        handle = core.handle_input

        def tracked(contract):
            calls.append(contract)
            return handle(contract)

        monkeypatch.setattr(core, "handle_input", tracked)
        monkeypatch.setattr(
            core.operational_service,
            "execute",
            lambda *_a, **_kw: pytest.fail("CLI audio dispatched an operation"),
        )
        cores.append(core)
        return console

    forwarded = []
    runner = _fixture_lab(tmp_path, forwarded)

    def fixture_lab(**kwargs):
        if audio_status == "failed":
            forwarded.append(kwargs)
            return LabResult(
                "failed", "sdk_unavailable", "fixture-failed", kwargs["engine"], "fixture"
            )
        return runner(**kwargs)

    # Only the lab is injected. The real registry/parser/wrapper, late persistent
    # builder, transcript review and sovereign Core execute normally.
    def with_explicit_fixture(args, core_factory):
        return original_run(args, core_factory, lab_runner=fixture_lab)

    monkeypatch.setattr(cli.JarvisConsole, "build", build)
    monkeypatch.setattr(transcript_review_cli, "run_transcript_review", with_explicit_fixture)
    _stdin(monkeypatch)
    argv = [
        "--format",
        "json",
        "transcript-review",
        "--authorized",
        "--include-content",
        "--session-id",
        SESSION,
        "--tts-authorized",
        "--tts-engine",
        "qwen3_tts",
        "--tts-reference",
        tts_args.tts_reference,
        "--tts-model-dir",
        tts_args.tts_model_dir,
        "--tts-python",
        tts_args.tts_python,
        "--tts-workspace",
        tts_args.tts_workspace,
        "--tts-show-output-path",
    ]
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert not captured.err and len(constructions) == 1
    result = json.loads(captured.out)
    assert result["command_id"] == "transcript-review" and result["status"] == "success"
    payload = json.loads(result["outputs"][0])
    assert payload["final_text"] == FINAL and payload["reviewed_text"] == REVIEWED
    assert payload["tts"]["status"] == audio_status
    assert payload["tts"]["audio_evidence_mode"] == "fixture"
    assert payload["tts"]["output_location_available"] is (audio_status == "completed")
    assert len(forwarded) == 1 and forwarded[0]["text"] == FINAL
    assert str(tmp_path) not in captured.out
    _assert_persisted(cores[0], calls, runtime, final=FINAL)
    _assert_audio_audit(cores[0], calls, runtime)


def test_unexpected_audio_adapter_exception_cannot_hide_or_repeat_committed_core_turn(
    tts_args, tmp_path, monkeypatch
):
    _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.include_content = True
    tts_args.tts_show_output_path = True

    def failed_adapter(**_kwargs):
        raise RuntimeError("password=private-adapter-path-and-content")

    monkeypatch.setattr("apps.jarvis_console.persistent_tts.speak_persisted_final", failed_adapter)
    _stdin(monkeypatch)
    encoded = run_transcript_review(
        tts_args,
        lambda: core,
        lab_runner=lambda **_: pytest.fail("unexpected adapter failure invoked lab"),
    ).outputs[0]
    payload = json.loads(encoded)
    assert payload["final_text"] == FINAL and payload["reviewed_text"] == REVIEWED
    assert payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] == "failed"
    assert payload["tts"]["reason"] == "local_tts_unavailable"
    assert payload["tts"]["text_fallback_available"] is True
    assert payload["tts"]["artifact_available"] is False
    assert "private-adapter" not in encoded
    _assert_persisted(core, calls, runtime, final=FINAL)


def test_missing_finished_audio_audit_refuses_artifact_claim_and_keeps_final(
    tts_args, tmp_path, monkeypatch
):
    _short_final(monkeypatch)
    core, calls, runtime = _core(tmp_path, monkeypatch)
    tts_args.include_content = True
    tts_args.tts_show_output_path = True
    repository = core.observability_service.repository
    original_record = repository.record_event

    def record(event):
        if event.event_name == "local_final_tts_finished":
            raise RuntimeError("private-event-store-password=do-not-display")
        return original_record(event)

    monkeypatch.setattr(repository, "record_event", record)
    forwarded = []
    _stdin(monkeypatch)
    encoded = run_transcript_review(
        tts_args, lambda: core, lab_runner=_fixture_lab(tmp_path, forwarded)
    ).outputs[0]
    payload = json.loads(encoded)
    assert payload["final_text"] == FINAL and payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] == "failed"
    assert payload["tts"]["reason"] == "local_tts_audit_unavailable"
    assert payload["tts"]["audit_event_recorded"] is False
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["output_location_available"] is False
    assert "private-event-store" not in encoded and str(tmp_path) not in encoded
    assert len(forwarded) == 1
    _, events = _assert_persisted(core, calls, runtime, final=FINAL)
    names = [event.event_name for event in events]
    assert names.count("local_final_tts_requested") == 1
    assert "local_final_tts_finished" not in names
