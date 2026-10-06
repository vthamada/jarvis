"""Real isolated Core pipeline, with explicitly synthetic lab/final test doubles."""

from __future__ import annotations

import io
import json
import sys
import wave
from dataclasses import replace
from pathlib import Path

import pytest
from synthesis_engine.engine import SynthesisEngine

from apps.jarvis_console import local_tts_pilot as pilot
from apps.jarvis_voice_lab import LabResult, run_voice_lab


def arguments(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return {
        "authorized": True,
        "reviewed_text": "Pedido privado revisado, sem autorização de ação.",
        "reference_path": tmp_path / "reference.wav",
        "model_dir": tmp_path / "weights",
        "python_executable": Path(sys.executable),
        "engine": "qwen3_tts",
        "workspace_root": workspace,
    }


def short_final(monkeypatch, text="Resposta final fixture do sintetizador, distinta do pedido."):
    original = SynthesisEngine.compose_result
    composed = []

    def compose(self, synthesis_input):
        # The bounded final is an explicit test double. Governance/planning/memory
        # and all normal Core orchestration still run; no real model is claimed.
        result = replace(original(self, synthesis_input), response_text=text)
        composed.append(result)
        return result

    monkeypatch.setattr(SynthesisEngine, "compose_result", compose)
    return composed


def fixture_result(kwargs, *, status="completed", reason="fixture_only"):
    return LabResult(status, reason, "fixture-run", kwargs["engine"], "fixture")


def test_only_bound_persisted_core_final_reaches_fixture_lab(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    composed = short_final(monkeypatch)
    forwarded = []
    cores = []
    original_build = pilot._isolated_core

    def build(runtime):
        core = original_build(runtime)
        original_handle = core.handle_input
        contracts = []
        core.handle_input = lambda contract: (
            contracts.append(contract),
            original_handle(contract),
        )[1]
        cores.append((core, runtime, contracts))
        return core

    def lab_runner(**kwargs):
        forwarded.append(kwargs)
        assert kwargs["evidence_mode"] == "fixture"
        assert kwargs["text"] == composed[-1].response_text
        assert kwargs["text"] != values["reviewed_text"]
        core, _, contracts = cores[-1]
        contract = contracts[-1]
        assert contract.channel.value == "voice" and contract.input_type.value == "text"
        assert contract.content == values["reviewed_text"]
        assert not contract.surface_capability_scope
        assert contract.max_autonomy_level == "assist_only"
        assert contract.requested_autonomy_level == "assist_only"
        assert (
            contract.action_confirmation_receipt_id is None
            and contract.adapter_action_request is None
        )
        turns = core.memory_service.repository.fetch_recent_turns(contract.session_id, 1)
        assert turns[-1].response_text == kwargs["text"]
        assert turns[-1].request_content == values["reviewed_text"]
        assert core.observability_service.agentic_adapter is None
        return fixture_result(kwargs)

    monkeypatch.setattr(pilot, "_isolated_core", build)
    monkeypatch.setenv("DATABASE_URL", "postgresql://must-never-connect")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    result = pilot.run_local_tts_pilot(**values, lab_runner=lab_runner)
    assert result.status == "completed" and len(forwarded) == 1
    assert result.metadata()["audio_evidence_mode"] == "fixture"
    assert result.metadata()["core_evidence_mode"] == "core_local"
    assert not result.metadata()["operation_dispatched"]
    assert result.metadata()["authority"] == "none"
    assert not result.metadata()["runtime_capability_promoted"]
    assert all(not runtime.exists() for _, runtime, _ in cores)
    serialized = json.dumps(result.metadata())
    assert values["reviewed_text"] not in serialized
    assert composed[-1].response_text not in serialized
    assert str(tmp_path) not in serialized


def test_actual_default_core_long_final_is_refused_without_calling_lab(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    monkeypatch.setattr(
        pilot, "run_voice_lab", lambda **kwargs: pytest.fail("TTS must not receive truncated final")
    )
    result = pilot.run_local_tts_pilot(**values)
    assert result.status == "refused" and result.reason == "final_text_too_long"
    assert result.final_character_count > 600
    assert result.lab_result is None and result.output_path is None
    assert result.metadata()["audio_evidence_mode"] == "not_run"
    assert result.core_event_count > 0 and result.memory_record_id
    assert list(values["workspace_root"].iterdir()) == []


def test_real_lab_composition_with_fixture_worker_and_core_final(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    short_final(monkeypatch)
    values["model_dir"].mkdir()
    with wave.open(str(values["reference_path"]), "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x01\x00" * 1600)
    # Owned pytest temporary directory, outside the designated workspace.
    monkeypatch.setattr(pilot.tempfile, "gettempdir", lambda: str(tmp_path))
    received = []

    def worker(request):
        received.append(request)
        with wave.open(request["output_path"], "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            output.writeframes(b"\x02\x00" * 1600)
        return {"status": "completed", "run_id": request["run_id"], "engine": request["engine"]}

    def runner(**kwargs):
        return run_voice_lab(**kwargs, fixture_worker=worker)

    result = pilot.run_local_tts_pilot(**values, lab_runner=runner)
    assert result.status == "completed" and result.lab_result.evidence_mode == "fixture"
    assert result.lab_result.reason == "fixture_only"
    assert result.output_path and Path(result.output_path).is_file()
    assert str(tmp_path) not in json.dumps(result.metadata())
    assert received[0]["text"] != values["reviewed_text"]
    assert list(values["workspace_root"].iterdir()) == []


@pytest.mark.parametrize(
    "patch",
    [
        {"authorized": False},
        {"authorized": "yes"},
        {"authorized": 1},
        {"reviewed_text": ""},
        {"reviewed_text": " "},
        {"reviewed_text": "x" * 601},
        {"reviewed_text": "\x00private"},
        {"reviewed_text": "\ud800"},
        {"engine": "remote"},
        {"device": "cuda:1"},
    ],
)
def test_invalid_consent_input_and_engine_never_enter_core_or_lab(tmp_path, monkeypatch, patch):
    values = arguments(tmp_path)
    values.update(patch)
    monkeypatch.setattr(
        pilot, "_isolated_core", lambda _: pytest.fail("invalid input reached Core")
    )
    with pytest.raises(ValueError):
        pilot.run_local_tts_pilot(
            **values, lab_runner=lambda **_: pytest.fail("invalid input reached lab")
        )


@pytest.mark.parametrize(
    "change",
    [
        {"request_id": "voice-other"},
        {"confirmed": False},
        {"status": "incomplete"},
        {"evidence_mode": "fixture"},
        {"synthesis_ref": "foreign-record"},
        {"text": "External forged final"},
    ],
)
def test_mismatched_final_never_reaches_tts(tmp_path, monkeypatch, change):
    values = arguments(tmp_path)
    short_final(monkeypatch)
    original = pilot.ReviewedVoiceCorePort.interact
    monkeypatch.setattr(
        pilot.ReviewedVoiceCorePort,
        "interact",
        lambda self, request: replace(original(self, request), **change),
    )
    with pytest.raises(ValueError, match="core_final_binding_refused"):
        pilot.run_local_tts_pilot(
            **values, lab_runner=lambda **_: pytest.fail("forged final reached TTS")
        )


def test_missing_canonical_memory_or_events_never_reaches_tts(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    short_final(monkeypatch)
    original = pilot._isolated_core

    def build(runtime):
        core = original(runtime)
        core.memory_service.repository.fetch_recent_turns = lambda *args: []
        return core

    monkeypatch.setattr(pilot, "_isolated_core", build)
    with pytest.raises(ValueError, match="core_final_evidence_refused"):
        pilot.run_local_tts_pilot(
            **values, lab_runner=lambda **_: pytest.fail("unpersisted final reached TTS")
        )


def test_injected_lab_cannot_claim_real_model_or_other_engine(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    short_final(monkeypatch)
    for record in [
        LabResult("completed", "local_sample_generated", "test", "qwen3_tts", "model_real"),
        LabResult("completed", "fixture_only", "test", "chatterbox_pt_br", "fixture"),
    ]:
        with pytest.raises(ValueError, match="lab_result_binding_refused"):
            pilot.run_local_tts_pilot(**values, lab_runner=lambda **_: record)


def test_sdk_unavailable_is_redacted_and_never_claimed_success(tmp_path, monkeypatch):
    values = arguments(tmp_path)
    short_final(monkeypatch)
    result = pilot.run_local_tts_pilot(
        **values,
        lab_runner=lambda **kwargs: fixture_result(
            kwargs, status="failed", reason="sdk_unavailable"
        ),
    )
    assert result.status == "failed" and result.reason == "sdk_unavailable"
    assert result.metadata()["audio_evidence_mode"] == "fixture"
    assert result.output_path is None


@pytest.mark.parametrize("show_path", [False, True])
def test_cli_reads_private_stdin_and_output_path_requires_explicit_flag(
    tmp_path, monkeypatch, capsys, show_path
):
    values = arguments(tmp_path)
    received = []
    lab = LabResult(
        "completed",
        "fixture_only",
        "fixture",
        "qwen3_tts",
        "fixture",
        output_path=str(tmp_path / "private-temp" / "sample.wav"),
    )
    result = pilot.LocalTtsPilotResult(
        "completed", "fixture_only", "voice-fixture", "memory-fixture", "allow", 3, 10, lab
    )
    monkeypatch.setattr(
        pilot, "run_local_tts_pilot", lambda **kwargs: (received.append(kwargs), result)[1]
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(values["reviewed_text"]))
    command = [
        "--authorized",
        "--engine",
        "qwen3_tts",
        "--reference",
        str(values["reference_path"]),
        "--model-dir",
        str(values["model_dir"]),
        "--python",
        str(values["python_executable"]),
        "--text-stdin",
    ]
    if show_path:
        command.append("--show-output-path")
    assert pilot.main(command) == 0
    serialized = capsys.readouterr().out
    assert values["reviewed_text"] not in serialized
    assert ("output_path" in json.loads(serialized)) is show_path
    assert received[0]["reviewed_text"] == values["reviewed_text"]


def test_cli_errors_never_print_private_content_or_paths(tmp_path, monkeypatch, capsys):
    values = arguments(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("private text"))
    monkeypatch.setattr(
        pilot,
        "run_local_tts_pilot",
        lambda **_: (_ for _ in ()).throw(ValueError("private secret")),
    )
    assert (
        pilot.main(
            [
                "--authorized",
                "--engine",
                "qwen3_tts",
                "--reference",
                str(values["reference_path"]),
                "--model-dir",
                str(values["model_dir"]),
                "--python",
                str(values["python_executable"]),
                "--text-stdin",
            ]
        )
        == 2
    )
    output = capsys.readouterr().out
    assert (
        "private secret" not in output
        and "private text" not in output
        and str(tmp_path) not in output
    )
