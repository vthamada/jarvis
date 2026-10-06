"""Native persistent Core final -> explicitly opted-in, exact synthetic batch audio.

The principal case does not replace Core synthesis: governance, final, memory
and SQLite restart are real. Only PCM/audio inference is a declared fixture;
neither model execution, quality, playback nor human speaker identity is proved.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import struct
import sys
import tempfile
import wave
from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from apps.jarvis_console.runtime import ConsoleCommandError
from apps.jarvis_console.transcript_review_cli import run_transcript_review
from apps.jarvis_console.voice_pilot import _isolated_core

SESSION = "persistent-batch-tts-e2e"
REVIEWED = "  Explique o significado de agente.\r\nAção, café, e\u0301 e 🧠.\t "


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
                "text": "Rascunho sem autoridade.",
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


def _stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(_envelope(), ensure_ascii=True)))


def _wav(path, raw, *, rate=16000):
    with wave.open(str(path), "wb") as audio:
        audio.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        audio.writeframes(raw)


@pytest.fixture
def batch_args(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    reference = tmp_path / "reference.wav"
    _wav(reference, b"\x02\x00" * 16000 * 15)
    model = tmp_path / "model"
    model.mkdir()
    python = tmp_path / "python-stub.exe"
    python.write_bytes(b"synthetic executable never launched")
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
        tts_seed=123,
        tts_show_output_path=False,
        tts_batch=True,
    )


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
        lambda *_a, **_kw: pytest.fail("batch TTS dispatched an operation"),
    )
    return core, calls, runtime


def _persistent_final(core, calls, runtime):
    assert len(calls) == 1
    contract = calls[0]
    assert contract.content == REVIEWED and contract.channel.value == "voice"
    assert contract.requested_autonomy_level == contract.max_autonomy_level == "assist_only"
    assert contract.surface_capability_scope == []
    assert contract.action_confirmation_receipt_id is None
    assert contract.adapter_action_request is None
    turns = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(turns) == 1 and turns[0].request_content == REVIEWED
    events = core.observability_service.repository.list_events(
        request_id=contract.request_id, session_id=SESSION, limit=100
    )
    names = [event.event_name for event in events]
    for name in ("governance_checked", "response_synthesized", "memory_recorded"):
        assert names.count(name) == 1
    restarted = _isolated_core(runtime)
    persisted = restarted.memory_service.repository.fetch_recent_turns(SESSION, 10)
    assert len(persisted) == 1 and persisted[0].response_text == turns[0].response_text
    assert persisted[0].request_content == REVIEWED
    return turns[0].response_text, events


def _worker_records(request, *, fault=None):
    assert request["batch_version"] == "jarvis-voice-batch-v1"
    chunks = request["chunks"]
    assert isinstance(chunks, list) and 2 <= len(chunks) <= 16
    assert all(isinstance(text, str) and 1 <= len(text) <= 600 for text in chunks)
    assert "".join(chunks) == request["text"]
    output = Path(request["output_dir"])
    expected = []
    hashes = [hashlib.sha256(text.encode()).hexdigest() for text in chunks]
    for index, _text in enumerate(chunks):
        raw = struct.pack("<h", index + 1) * (1000 + index * 100)
        expected.append(raw)
        if fault == "missing_part" and index == 1:
            continue
        if fault == "midpart" and index == 1:
            return {
                "batch_version": request["batch_version"],
                "run_id": request["run_id"],
                "engine": request["engine"],
                "status": "failed",
                "reason": "local_inference_failed",
                "part_count": len(chunks),
                "completed_parts": 1,
                "text_sha256": hashlib.sha256(request["text"].encode()).hexdigest(),
                "part_text_sha256": hashes,
            }, expected
        if fault == "duration_bound":
            raw = b"\x01\x00" * 16000 * 120
        if fault == "part_duration_bound":
            raw = b"\x01\x00" * 16000 * 121
        if fault == "size_bound":
            raw = b"\x01\x00" * 96000 * 100
        path = output / f"part-{index:04d}.wav"
        rate = (
            96000
            if fault == "size_bound"
            else (8000 if fault == "rate_mismatch" and index == 1 else 16000)
        )
        _wav(path, raw, rate=rate)
        if fault == "truncated" and index == 1:
            path.write_bytes(path.read_bytes()[:-3])
    response = {
        "batch_version": request["batch_version"],
        "run_id": request["run_id"],
        "engine": request["engine"],
        "status": "completed",
        "part_count": len(chunks),
        "completed_parts": len(chunks),
        "text_sha256": hashlib.sha256(request["text"].encode()).hexdigest(),
        "part_text_sha256": hashes,
    }
    if fault == "full_hash":
        response["text_sha256"] = "f" * 64
    elif fault == "part_hash":
        response["part_text_sha256"][1] = "f" * 64
    elif fault == "count":
        response["part_count"] += 1
    elif fault == "completed_count":
        response["completed_parts"] -= 1
    return response, expected


def _runner(records, *, fault=None, cancelled=None, timeout_after_worker=False, monkeypatch=None):
    from apps.jarvis_voice_lab import lab_batch

    def runner(**kwargs):
        record = {"kwargs": kwargs}
        records.append(record)
        clock = [0.0]

        def worker(request):
            record["request"] = request
            response, raw = _worker_records(request, fault=fault)
            record["raw_parts"] = raw
            if timeout_after_worker:
                # A deterministic deadline fixture, never a blocking sleep.
                clock[0] = kwargs["timeout_seconds"] + 1
            return response

        extra = {} if cancelled is None else {"cancelled": cancelled}
        if timeout_after_worker:
            extra["clock"] = lambda: clock[0]
        result = lab_batch.run_voice_lab_batch(**kwargs, fixture_worker=worker, **extra)
        record["result"] = result
        return result

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
def test_native_core_final_survives_restart_and_exact_ordered_batch_aggregation(
    engine, profile, batch_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.tts_engine, batch_args.tts_voice_profile = engine, profile
    if profile in {"qwen_icl", "qwen_icl_draft"}:
        batch_args.tts_reference_transcript = "Transcrição exata fixture sem áudio humano."
        batch_args.tts_transcript_confirmed = profile == "qwen_icl"
        batch_args.tts_reference_start = 2
        batch_args.tts_reference_duration = 12
    records = []
    runner = _runner(records)

    def verify_persisted_before_lab(**kwargs):
        final, _ = _persistent_final(core, calls, runtime)
        assert kwargs["text"] == final and final != REVIEWED and len(final) > 600
        return runner(**kwargs)

    _stdin(monkeypatch)
    encoded = run_transcript_review(
        batch_args, lambda: core, lab_runner=verify_persisted_before_lab
    ).outputs[0]
    payload = json.loads(encoded)
    tts = payload["tts"]
    final, events = _persistent_final(core, calls, runtime)
    assert payload["canonical_turn_recorded"] is True and payload["operation_dispatched"] is False
    assert tts["status"] == "completed" and tts["batch_mode"] is True
    assert tts["audio_evidence_mode"] == "fixture" and tts["voice_quality_approved"] is False
    assert tts["artifact_available"] is True and tts["audit_event_recorded"] is True
    assert tts["final_character_count"] == len(final)
    assert len(records) == 1
    record = records[0]
    request = record["request"]
    assert request["text"] == final and "".join(request["chunks"]) == final
    assert request["voice_profile"] == profile
    assert request["reference_transcript"] == batch_args.tts_reference_transcript
    assert request["transcript_confirmed"] is batch_args.tts_transcript_confirmed
    assert request["seed"] == 123
    assert tts["part_count"] == tts["completed_parts"] == len(request["chunks"])
    output = Path(record["result"].output_path)
    with wave.open(str(output), "rb") as audio:
        raw = audio.readframes(audio.getnframes())
        assert audio.getframerate() == 16000 and audio.getnchannels() == 1
        assert raw == b"".join(record["raw_parts"])
        assert audio.getnframes() == sum(len(part) // 2 for part in record["raw_parts"])
    assert record["result"].text_sha256 == hashlib.sha256(final.encode()).hexdigest()
    assert tuple(record["result"].part_text_sha256) == tuple(
        hashlib.sha256(part.encode()).hexdigest() for part in request["chunks"]
    )
    for private in (
        REVIEWED,
        final,
        str(tmp_path),
        "sample.wav",
        "reference.wav",
        record["result"].text_sha256,
        *record["result"].part_text_sha256,
    ):
        assert private not in encoded
    audio_events = [event for event in events if event.event_name.startswith("local_final_tts_")]
    assert [event.event_name for event in audio_events] == [
        "local_final_tts_requested",
        "local_final_tts_finished",
    ]
    for event in audio_events:
        content = json.dumps(event.payload, ensure_ascii=False)
        assert final not in content and str(tmp_path) not in content
        assert event.payload["batch_mode"] is True


@pytest.mark.parametrize(
    "fault",
    [
        "midpart",
        "missing_part",
        "full_hash",
        "part_hash",
        "count",
        "completed_count",
        "rate_mismatch",
        "truncated",
    ],
)
def test_partial_invalid_batch_cannot_claim_artifact_or_repeat_core_turn(
    fault, batch_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    batch_args.tts_show_output_path = True
    records = []
    _stdin(monkeypatch)
    encoded = run_transcript_review(
        batch_args, lambda: core, lab_runner=_runner(records, fault=fault)
    ).outputs[0]
    payload = json.loads(encoded)
    final, _ = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final and payload["reviewed_text"] == REVIEWED
    assert payload["tts"]["status"] != "completed"
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["output_location_available"] is False
    assert payload["tts"]["text_fallback_available"] is True
    assert payload["tts"]["audit_event_recorded"] is True
    assert len(records) == 1 and records[0]["kwargs"]["text"] == final
    assert str(tmp_path) not in encoded
    assert records[0]["result"].output_path is None
    output = Path(records[0]["request"]["output_dir"]) / "sample.wav"
    assert not output.exists()


@pytest.mark.parametrize("condition", ["cancel_before", "cancel_after", "deadline"])
def test_cancelled_or_expired_batch_retains_native_text_and_no_partial_audio(
    condition, batch_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    records = []
    cancelled = None
    if condition.startswith("cancel"):

        def cancelled():
            return condition == "cancel_before" or bool(records and "request" in records[0])

    _stdin(monkeypatch)
    encoded = run_transcript_review(
        batch_args,
        lambda: core,
        lab_runner=_runner(
            records,
            cancelled=cancelled,
            timeout_after_worker=condition == "deadline",
            monkeypatch=monkeypatch,
        ),
    ).outputs[0]
    payload = json.loads(encoded)
    final, _ = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final
    assert payload["tts"]["status"] == ("timed_out" if condition == "deadline" else "cancelled")
    assert payload["tts"]["artifact_available"] is False
    assert len(records) == 1 and records[0]["result"].output_path is None
    if "request" in records[0]:
        assert not (Path(records[0]["request"]["output_dir"]) / "sample.wav").exists()


@pytest.mark.parametrize("authorized", [None, False, "yes", 1])
def test_batch_flag_never_grants_audio_consent_or_consumes_stdin(
    authorized, batch_args, monkeypatch
):
    batch_args.tts_authorized = authorized

    class NeverRead:
        def isatty(self):
            pytest.fail("batch without consent inspected stdin")

        def read(self, *_args):
            pytest.fail("batch without consent consumed stdin")

    monkeypatch.setattr(sys, "stdin", NeverRead())
    with pytest.raises(ConsoleCommandError):
        run_transcript_review(
            batch_args,
            lambda: pytest.fail("batch without consent bootstrapped Core"),
            lab_runner=lambda **_: pytest.fail("batch without consent opened lab"),
        )


def test_real_cli_batch_flag_without_authorization_refuses_before_stdin_or_store(
    monkeypatch, capsys
):
    from apps.jarvis_console import cli

    class NeverRead:
        def isatty(self):
            pytest.fail("CLI batch-only inspected stdin")

        def read(self, *_args):
            pytest.fail("CLI batch-only consumed stdin")

    monkeypatch.setattr(sys, "stdin", NeverRead())
    monkeypatch.setattr(
        cli.JarvisConsole, "build", lambda **_: pytest.fail("CLI batch-only initialized runtime")
    )
    assert cli.main(["--format", "json", "transcript-review", "--authorized", "--tts-batch"]) == 2
    output = capsys.readouterr()
    payload = json.loads(output.out or output.err)
    assert payload["status"] == "error" and payload["command_id"] == "transcript-review"


def test_unicode_edges_preserved_exactly_in_canonical_final_and_batch_chunks(
    batch_args, tmp_path, monkeypatch
):
    from synthesis_engine.engine import SynthesisEngine

    # Explicit synthesis fixture for forms not naturally present in the native
    # Core final. The principal batch cases above use unmodified synthesis.
    final = ("  e\u0301, café e 🧠: conteúdo literal.\r\n" * 35) + " Fim.  "
    original = SynthesisEngine.compose_result
    monkeypatch.setattr(
        SynthesisEngine,
        "compose_result",
        lambda self, value: replace(original(self, value), response_text=final),
    )
    core, calls, runtime = _core(tmp_path, monkeypatch)
    records = []
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(batch_args, lambda: core, lab_runner=_runner(records)).outputs[0]
    )
    canonical, _ = _persistent_final(core, calls, runtime)
    assert canonical == final and payload["tts"]["status"] == "completed"
    chunks = records[0]["request"]["chunks"]
    assert "".join(chunks).encode() == final.encode()
    assert records[0]["result"].text_sha256 == hashlib.sha256(final.encode()).hexdigest()


@pytest.mark.parametrize(
    "mutation",
    [
        {"text_sha256": "f" * 64},
        {"part_text_sha256": ("f" * 64,)},
        {"part_count": 1},
        {"completed_parts": 0},
        {"evidence_mode": "model_real"},
    ],
)
def test_forged_completed_batch_result_is_refused_at_persistent_adapter_boundary(
    mutation, batch_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    records = []
    original = _runner(records)

    def forged(**kwargs):
        return replace(original(**kwargs), **mutation)

    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(batch_args, lambda: core, lab_runner=forged).outputs[0]
    )
    final, _ = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final
    assert payload["tts"]["status"] != "completed"
    assert payload["tts"]["artifact_available"] is False
    assert len(records) == 1


@pytest.mark.parametrize("size", [6000, 6001])
def test_full_batch_text_bound_never_truncates_or_repeats_canonical_turn(
    size, batch_args, tmp_path, monkeypatch
):
    from synthesis_engine.engine import SynthesisEngine

    final = "🧠" * size
    original = SynthesisEngine.compose_result
    monkeypatch.setattr(
        SynthesisEngine,
        "compose_result",
        lambda self, value: replace(original(self, value), response_text=final),
    )
    core, calls, runtime = _core(tmp_path, monkeypatch)
    records = []
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(batch_args, lambda: core, lab_runner=_runner(records)).outputs[0]
    )
    canonical, _ = _persistent_final(core, calls, runtime)
    assert canonical == final and len(canonical) == size
    assert payload["tts"]["final_character_count"] == size
    assert payload["tts"]["status"] == ("completed" if size == 6000 else "refused")
    assert len(records) == int(size == 6000)
    if records:
        assert "".join(records[0]["request"]["chunks"]) == final
        assert records[0]["result"].part_count == 10


@pytest.mark.parametrize("bound", ["duration_bound", "part_duration_bound", "size_bound"])
def test_real_audio_bounds_refuse_complete_or_partial_publication_with_text_preserved(
    bound, batch_args, tmp_path, monkeypatch
):
    if bound == "duration_bound":
        from synthesis_engine.engine import SynthesisEngine

        # Seven individually legal 120s parts exceed the real aggregate 600s
        # contract. This final is an explicit bound-testing synthesis fixture.
        original = SynthesisEngine.compose_result
        monkeypatch.setattr(
            SynthesisEngine,
            "compose_result",
            lambda self, value: replace(original(self, value), response_text="x" * 3601),
        )
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    records = []
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(
            batch_args, lambda: core, lab_runner=_runner(records, fault=bound)
        ).outputs[0]
    )
    final, _ = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final and len(records) == 1
    assert payload["tts"]["status"] != "completed"
    assert payload["tts"]["artifact_available"] is False
    directory = Path(records[0]["request"]["output_dir"])
    assert not (directory / "sample.wav").exists()
    assert not list(directory.glob("*.pending"))


def test_actual_registered_cli_native_long_final_batch_preserves_core_and_pcm(
    batch_args, tmp_path, monkeypatch, capsys
):
    from apps.jarvis_console import cli, transcript_review_cli
    from apps.jarvis_console.bootstrap import ROOT

    real_build = cli.JarvisConsole.build
    original_run = transcript_review_cli.run_transcript_review
    constructions = []
    cores = []
    calls = []
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
        cores.append(core)
        return console

    records = []

    def fixture_runner(args, core_factory):
        return original_run(args, core_factory, lab_runner=_runner(records))

    monkeypatch.setattr(cli.JarvisConsole, "build", build)
    monkeypatch.setattr(transcript_review_cli, "run_transcript_review", fixture_runner)
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
        "--tts-batch",
        "--tts-engine",
        "qwen3_tts",
        "--tts-reference",
        batch_args.tts_reference,
        "--tts-model-dir",
        batch_args.tts_model_dir,
        "--tts-python",
        batch_args.tts_python,
        "--tts-workspace",
        batch_args.tts_workspace,
        "--tts-show-output-path",
    ]
    assert cli.main(argv) == 0
    captured = capsys.readouterr()
    assert not captured.err and len(constructions) == 1
    result = json.loads(captured.out)
    assert result["status"] == "success" and result["command_id"] == "transcript-review"
    payload = json.loads(result["outputs"][0])
    final, _ = _persistent_final(cores[0], calls, runtime)
    assert len(final) > 600 and payload["final_text"] == final
    assert payload["tts"]["status"] == "completed" and payload["tts"]["batch_mode"] is True
    assert payload["tts"]["output_location_available"] is True
    assert records[0]["request"]["text"] == final and len(records) == 1
    location = payload["tts"]["output_location"]
    assert location["base"] == "system_temporary_directory"
    relative = Path(location["relative_path"])
    assert not relative.is_absolute() and ".." not in relative.parts
    output = tmp_path / relative
    with wave.open(str(output), "rb") as audio:
        assert audio.readframes(audio.getnframes()) == b"".join(records[0]["raw_parts"])
    assert str(tmp_path) not in captured.out


def test_finished_batch_audit_failure_never_promotes_aggregate_or_erases_core_text(
    batch_args, tmp_path, monkeypatch
):
    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    batch_args.tts_show_output_path = True
    repository = core.observability_service.repository
    original_record = repository.record_event

    def record(event):
        if event.event_name == "local_final_tts_finished":
            raise RuntimeError("password=private-batch-audit-store")
        return original_record(event)

    monkeypatch.setattr(repository, "record_event", record)
    records = []
    _stdin(monkeypatch)
    encoded = run_transcript_review(batch_args, lambda: core, lab_runner=_runner(records)).outputs[
        0
    ]
    payload = json.loads(encoded)
    final, events = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final and payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] == "failed"
    assert payload["tts"]["reason"] == "local_tts_audit_unavailable"
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["output_location_available"] is False
    assert payload["tts"]["audit_event_recorded"] is False
    assert payload["tts"]["text_fallback_available"] is True
    assert len(records) == 1 and records[0]["result"].status == "completed"
    # The complete private WAV can exist after generation, but it is not a
    # successfully audited/delivered artifact. It is never exposed as completed.
    assert Path(records[0]["result"].output_path).is_file()
    assert "private-batch-audit-store" not in encoded and str(tmp_path) not in encoded
    names = [event.event_name for event in events]
    assert names.count("local_final_tts_requested") == 1
    assert "local_final_tts_finished" not in names


def test_reentrant_concurrent_and_repeated_batch_callbacks_cannot_start_second_campaign(
    batch_args, tmp_path, monkeypatch
):
    from apps.jarvis_console.persistent_tts import speak_persisted_final
    from apps.jarvis_console.transcript_tts_options import transcript_tts_config
    from apps.jarvis_console.voice_pilot import ReviewedVoiceCorePort

    core, calls, runtime = _core(tmp_path, monkeypatch)
    capture = {}
    interact = ReviewedVoiceCorePort.interact

    def tracked_interact(port, request):
        final = interact(port, request)
        capture.update(port=port, request=request, final=final)
        return final

    monkeypatch.setattr(ReviewedVoiceCorePort, "interact", tracked_interact)
    config = transcript_tts_config(batch_args)
    records = []
    batch_runner = _runner(records)
    refused = []

    def again():
        return speak_persisted_final(
            config=config,
            **capture,
            lab_runner=lambda **_: pytest.fail("reentry opened a second batch campaign"),
        )

    def callback(**kwargs):
        # Synchronous recursion and simultaneous callbacks occur while the
        # first authorized campaign is already consumed, before it completes.
        refused.append(again())
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(again) for _ in range(2)]
            refused.extend(future.result(timeout=10) for future in futures)
        return batch_runner(**kwargs)

    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(batch_args, lambda: core, lab_runner=callback).outputs[0]
    )
    refused.append(again())
    assert payload["tts"]["status"] == "completed"
    assert len(records) == 1 and len(refused) == 4
    for result in refused:
        assert result.status == "refused" and result.reason == "final_tts_already_attempted"
        assert result.output_path is None and result.metadata()["artifact_available"] is False
    final, events = _persistent_final(core, calls, runtime)
    assert records[0]["request"]["text"] == final
    assert sum(event.event_name == "local_final_tts_requested" for event in events) == 1
    finished = [event for event in events if event.event_name == "local_final_tts_finished"]
    assert sum(event.payload["status"] == "completed" for event in finished) == 1
    assert sum(event.payload["reason"] == "final_tts_already_attempted" for event in finished) == 4


@pytest.mark.parametrize("expire_phase", ["record", "readback"])
@pytest.mark.parametrize("fail_corrective", [False, True])
def test_deadline_expiring_during_finished_audit_withholds_batch_and_records_terminal_timeout(
    expire_phase, fail_corrective, batch_args, tmp_path, monkeypatch
):
    from apps.jarvis_console import persistent_tts

    core, calls, runtime = _core(tmp_path, monkeypatch)
    batch_args.include_content = True
    batch_args.tts_show_output_path = True
    clock = [persistent_tts.time.monotonic()]
    monkeypatch.setattr(persistent_tts.time, "monotonic", lambda: clock[0])
    repository = core.observability_service.repository
    original_record = repository.record_event
    original_list = repository.list_events
    expired = [False]

    def expire():
        if not expired[0]:
            clock[0] += batch_args.tts_timeout + 1
            expired[0] = True

    def record(event):
        if (
            fail_corrective
            and event.event_name == "local_final_tts_finished"
            and event.payload["status"] == "timed_out"
        ):
            raise RuntimeError("password=private-corrective-audit-error")
        original_record(event)
        if (
            expire_phase == "record"
            and event.event_name == "local_final_tts_finished"
            and event.payload["status"] == "completed"
        ):
            expire()

    def list_events(**kwargs):
        events = original_list(**kwargs)
        if expire_phase == "readback" and kwargs.get("event_names") == (
            "local_final_tts_finished",
        ):
            expire()
        return events

    monkeypatch.setattr(repository, "record_event", record)
    monkeypatch.setattr(repository, "list_events", list_events)
    records = []
    _stdin(monkeypatch)
    payload = json.loads(
        run_transcript_review(batch_args, lambda: core, lab_runner=_runner(records)).outputs[0]
    )
    final, events = _persistent_final(core, calls, runtime)
    assert payload["final_text"] == final and payload["canonical_turn_recorded"] is True
    assert payload["tts"]["status"] == "timed_out"
    assert payload["tts"]["reason"] == "deadline_exceeded"
    assert payload["tts"]["artifact_available"] is False
    assert payload["tts"]["output_location_available"] is False
    assert payload["tts"]["audit_event_recorded"] is (not fail_corrective)
    assert payload["tts"]["text_fallback_available"] is True
    assert len(records) == 1 and records[0]["result"].status == "completed"
    finished = [event for event in events if event.event_name == "local_final_tts_finished"]
    assert len(finished) == (1 if fail_corrective else 2)
    assert finished[0].payload["status"] == "completed"
    if not fail_corrective:
        assert finished[-1].payload["status"] == "timed_out"
        assert finished[-1].payload["reason"] == "deadline_exceeded"
        assert finished[-1].payload["artifact_available"] is False
