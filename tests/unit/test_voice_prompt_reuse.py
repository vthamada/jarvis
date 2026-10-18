"""Experimental batch-local Qwen conditioning; synthetic SDK, no process or GPU."""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import math
import random
import sys
import types
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import lab_batch, worker


def _wav(path, frames=24000):
    with wave.open(str(path), "wb") as output:
        output.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
        output.writeframes(b"\x01\x00" * frames)


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    model, output, workspace = tmp_path / "model", tmp_path / "run", tmp_path / "workspace"
    for directory in (model, output, workspace):
        directory.mkdir()
    reference, executable = tmp_path / "reference.wav", tmp_path / "never-executed"
    _wav(reference)
    executable.write_bytes(b"synthetic executable only")
    chunks = ["  Exact e\u0301.\r\n", "🚀 Second exact part.  "]
    request = {
        "batch_version": worker.BATCH_VERSION, "authorized": True, "run_id": "ea" * 16,
        "engine": "qwen3_tts", "device": "cpu", "text": "".join(chunks), "chunks": chunks,
        "model_dir": str(model), "output_dir": str(output), "reference_path": str(reference),
        "voice_profile": "baseline", "reference_transcript": None,
        "transcript_confirmed": False, "seed": 42,
    }
    monkeypatch.chdir(output)
    monkeypatch.setattr(lab_batch.tempfile, "gettempdir", lambda: str(tmp_path))
    return request, {"engine": "qwen3_tts", "authorized": True, "reference_path": reference,
                     "model_dir": model, "python_executable": executable,
                     "workspace_root": workspace, "text": "Exact. " * 90,
                     "reference_duration_seconds": 3, "timeout_seconds": 30,
                     "evidence_mode": "fixture", "seed": 42}


@pytest.fixture
def sdk(monkeypatch):
    seen = {"loads": [], "prompts": [], "generation": [], "seeds": []}

    class Audio(list):
        ndim = 1

        def __ne__(self, value):
            return [item != value for item in self]

    class Model:
        @classmethod
        def from_pretrained(cls, path, **kwargs):
            seen["loads"].append((path, kwargs))
            return cls()

        def create_voice_clone_prompt(self, ref_audio, ref_text=None, x_vector_only_mode=False):
            seen["prompts"].append((ref_audio, ref_text, x_vector_only_mode))
            if seen.get("prompt_error"):
                raise RuntimeError("PRIVATE_REFERENCE_SECRET")
            if "prompt_result" in seen:
                return seen["prompt_result"]
            return [types.SimpleNamespace(private_embedding=object(), ref_text=ref_text,
                                          x_vector_only_mode=x_vector_only_mode)]

        def generate_voice_clone(self, text, language=None, ref_audio=None, ref_text=None,
                                 x_vector_only_mode=False, voice_clone_prompt=None, **kwargs):
            # Model the SDK's legacy per-part internal conditioning independently.
            prompt = voice_clone_prompt
            if prompt is None:
                seen["prompts"].append((ref_audio, ref_text, x_vector_only_mode))
                prompt = [types.SimpleNamespace(private_embedding=object(), ref_text=ref_text,
                                                x_vector_only_mode=x_vector_only_mode)]
            seen["generation"].append({"text": text, "language": language, "ref_audio": ref_audio,
                                       "ref_text": ref_text, "xvector": x_vector_only_mode,
                                       "prompt": prompt, "kwargs": kwargs})
            if seen.get("fail_part") == len(seen["generation"]):
                raise RuntimeError("PRIVATE_PART_SECRET")
            return [Audio([0.1, -0.2, 0.3])], 8000

    def write(handle, audio, rate, **kwargs):
        assert kwargs == {"format": "WAV", "subtype": "PCM_16"}
        with wave.open(handle, "wb") as output:
            output.setparams((1, 2, rate, 0, "NONE", "not compressed"))
            output.writeframes(b"\x01\x00" * len(audio))

    monkeypatch.setitem(sys.modules, "numpy", types.SimpleNamespace(
        asarray=lambda audio: audio, any=any, clip=lambda audio, *args: audio,
        isfinite=lambda audio: types.SimpleNamespace(all=lambda: all(map(math.isfinite, audio))),
        random=types.SimpleNamespace(seed=lambda seed: seen["seeds"].append(("numpy", seed)))))
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(
        float32="float32", bfloat16="bfloat16",
        manual_seed=lambda seed: seen["seeds"].append(("torch", seed))))
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=write))
    monkeypatch.setitem(sys.modules, "qwen_tts", types.SimpleNamespace(Qwen3TTSModel=Model))
    monkeypatch.setattr(random, "seed", lambda seed: seen["seeds"].append(("random", seed)))
    monkeypatch.setattr(worker, "_deny_network", lambda: None)
    seen["model"] = Model
    return seen


@pytest.mark.parametrize("reuse", [False, True])
@pytest.mark.parametrize("profile", ["baseline", "qwen_icl", "qwen_icl_draft"])
@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
def test_exact_two_parts_condition_once_only_on_opt_in(campaign, sdk, reuse, profile, device):
    request, _ = campaign
    request.update(voice_profile=profile, device=device)
    if reuse:
        request["reuse_voice_prompt"] = True
    if profile != "baseline":
        request.update(reference_transcript="  Exact reference e\u0301.\r\n",
                       transcript_confirmed=profile == "qwen_icl")
    state = {}
    worker._generate_batch(request, state)
    assert len(sdk["loads"]) == 1
    assert len(sdk["prompts"]) == (1 if reuse else 2)
    assert sdk["prompts"] == [(request["reference_path"], request["reference_transcript"],
                                profile == "baseline")] * (1 if reuse else 2)
    assert [item["text"] for item in sdk["generation"]] == request["chunks"]
    assert all(item["language"] == "Portuguese" and item["kwargs"] == {"max_new_tokens": 1024}
               for item in sdk["generation"])
    assert sdk["seeds"] == [("random", 42), ("numpy", 42), ("torch", 42)]
    if reuse:
        assert sdk["generation"][0]["prompt"] is sdk["generation"][1]["prompt"]
        assert all(item["ref_audio"] is None and item["ref_text"] is None
                   for item in sdk["generation"])
        assert all(item["prompt"][0].ref_text == request["reference_transcript"]
                   and item["prompt"][0].x_vector_only_mode is (profile == "baseline")
                   for item in sdk["generation"])
    else:
        assert all(item["ref_audio"] == request["reference_path"]
                   and item["ref_text"] == request["reference_transcript"]
                   and item["xvector"] is (profile == "baseline") for item in sdk["generation"])
    assert state["part_count"] == state["completed_parts"] == 2
    assert state["text_sha256"] == hashlib.sha256(request["text"].encode()).hexdigest()
    assert state["part_text_sha256"] == [hashlib.sha256(text.encode()).hexdigest()
                                         for text in request["chunks"]]
    assert sorted(path.name for path in Path(request["output_dir"]).iterdir()) == [
        "part-0000.wav", "part-0001.wav"]


def _main(request, monkeypatch, capsys, *, diagnostics=False):
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(
        buffer=io.BytesIO(json.dumps(request).encode())))
    code = worker.main(diagnostics=diagnostics)
    raw = capsys.readouterr().out
    return code, json.loads(raw) if raw else None, raw


def test_private_conditioning_phase_is_optional_and_preserves_public_schema(
    campaign, sdk, monkeypatch, capsys,
):
    request, _ = campaign
    request["reuse_voice_prompt"] = True
    code, result, raw = _main(request, monkeypatch, capsys, diagnostics=True)
    assert code == 0 and result["status"] == "completed"
    assert set(result) == {"run_id", "engine", "status", "batch_version", "part_count",
                           "completed_parts", "text_sha256", "part_text_sha256"}
    events = worker.read_voice_diagnostics(Path(request["output_dir"]), run_id=request["run_id"],
                                           engine="qwen3_tts", device="cpu", part_count=2)
    assert [(event["phase"], event["event"]) for event in events[2:7]] == [
        ("model_load", "started"), ("model_load", "completed"),
        ("reference_conditioning", "started"), ("reference_conditioning", "completed"),
        ("generate", "started")]
    assert "PRIVATE" not in raw and "private_embedding" not in json.dumps(events)
    assert "reuse_voice_prompt" not in raw and "reference_conditioning" not in raw


@pytest.mark.parametrize("mutation", ["repeat", "late", "part_index", "other_engine"])
def test_private_conditioning_reader_refuses_invalid_placement_or_engine(
    campaign, sdk, monkeypatch, capsys, mutation,
):
    request, _ = campaign
    request["reuse_voice_prompt"] = True
    code, result, _ = _main(request, monkeypatch, capsys, diagnostics=True)
    assert code == 0 and result["status"] == "completed"
    directory = Path(request["output_dir"])
    path = directory / worker.DIAGNOSTICS_NAME
    events = [json.loads(line) for line in path.read_bytes().splitlines()]
    if mutation == "repeat":
        events[6:6] = [dict(event) for event in events[4:6]]
    elif mutation == "late":
        conditioning = events[4:6]
        del events[4:6]
        events[8:8] = conditioning
    elif mutation == "part_index":
        events[4]["part_index"] = 0
    else:
        for event in events:
            event["engine"] = "chatterbox_pt_br"
    for sequence, event in enumerate(events):
        event["sequence"], event["elapsed_seconds"] = sequence, float(sequence)
    path.write_bytes(b"".join(json.dumps(event).encode() + b"\n" for event in events))
    with pytest.raises(ValueError):
        worker.read_voice_diagnostics(
            directory, run_id=request["run_id"], device="cpu", part_count=2,
            engine="chatterbox_pt_br" if mutation == "other_engine" else "qwen3_tts")


@pytest.mark.parametrize("value", [None, 1, "true", [], {}],
                         ids=["none", "int", "str", "list", "dict"])
def test_invalid_request_flag_precedes_files_and_heavy_imports(campaign, monkeypatch, value):
    request, _ = campaign
    request["reuse_voice_prompt"] = value
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name in {"numpy", "torch", "soundfile", "qwen_tts"}:
            pytest.fail("heavy SDK imported for invalid flag")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(worker, "_batch_path", lambda *args, **kwargs: pytest.fail("file I/O"))
    with pytest.raises(ValueError, match="invalid_voice_prompt_reuse_flag"):
        worker._generate_batch(request)


def test_reuse_refuses_other_engine_before_sdk_or_files(campaign, monkeypatch):
    request, _ = campaign
    request.update(engine="chatterbox_pt_br", reuse_voice_prompt=True)
    monkeypatch.setattr(worker, "_batch_path", lambda *args, **kwargs: pytest.fail("file I/O"))
    with pytest.raises(ValueError, match="voice_prompt_reuse_requires_qwen"):
        worker._generate_batch(request)


@pytest.mark.parametrize("unknown", ["voice_prompt", "prompt_path", "cache_prompt", "extra"])
def test_request_supersets_never_enable_unrequested_prompt_storage(campaign, monkeypatch, unknown):
    request, _ = campaign
    request.update(reuse_voice_prompt=True)
    request[unknown] = "PRIVATE_DESTINATION"
    monkeypatch.setattr(worker, "_batch_path", lambda *args, **kwargs: pytest.fail("file I/O"))
    with pytest.raises(ValueError, match="invalid_batch_fields"):
        worker._generate_batch(request)


@pytest.mark.parametrize("api", ["missing", "not_callable", "kwargs_only", "no_prompt_arg",
                                 "extra_required", "positional_only"])
def test_incompatible_sdk_fails_without_fallback(campaign, sdk, monkeypatch, capsys, api):
    request, _ = campaign
    request["reuse_voice_prompt"] = True
    model = sdk["model"]
    if api == "missing":
        del model.create_voice_clone_prompt
    elif api == "not_callable":
        model.create_voice_clone_prompt = None
    elif api == "kwargs_only":
        model.create_voice_clone_prompt = lambda self, **kwargs: []
    elif api == "no_prompt_arg":
        model.generate_voice_clone = lambda self, text, **kwargs: None
    elif api == "extra_required":
        model.create_voice_clone_prompt = (
            lambda self, ref_audio, ref_text, x_vector_only_mode, missing: [])
    else:
        model.create_voice_clone_prompt = (
            lambda self, ref_audio, /, ref_text=None, x_vector_only_mode=False: [])
    code, result, raw = _main(request, monkeypatch, capsys)
    assert code == 0 and result["status"] == "failed"
    assert result["reason"] == "sdk_incompatible" and result["completed_parts"] == 0
    assert sdk["prompts"] == sdk["generation"] == []
    assert not tuple(Path(request["output_dir"]).glob("*.wav"))
    assert "PRIVATE" not in raw


@pytest.mark.parametrize("prompt", [None, [], [1, 2], {}, (1,)],
                         ids=["none", "empty", "two", "dict", "tuple"])
def test_malformed_prompt_result_refused_without_generation(
    campaign, sdk, monkeypatch, capsys, prompt,
):
    request, _ = campaign
    request["reuse_voice_prompt"] = True
    sdk["prompt_result"] = prompt
    code, result, _ = _main(request, monkeypatch, capsys)
    assert code == 0 and result["reason"] == "sdk_incompatible"
    assert result["status"] == "failed" and result["completed_parts"] == 0
    assert len(sdk["prompts"]) == 1 and sdk["generation"] == []


@pytest.mark.parametrize("failure", ["conditioning", "second_part"])
def test_sdk_failure_does_not_retry_or_publish_aggregate(
    campaign, sdk, monkeypatch, capsys, failure,
):
    request, _ = campaign
    request["reuse_voice_prompt"] = True
    sdk["prompt_error" if failure == "conditioning" else "fail_part"] = (
        True if failure == "conditioning" else 2)
    code, result, raw = _main(request, monkeypatch, capsys, diagnostics=True)
    assert code == 0 and result["status"] == "failed"
    assert result["reason"] == "local_inference_failed" and result["failure_stage"] == "generate"
    assert len(sdk["loads"]) == len(sdk["prompts"]) == 1
    assert len(sdk["generation"]) == (0 if failure == "conditioning" else 2)
    assert result["completed_parts"] == (0 if failure == "conditioning" else 1)
    assert not (Path(request["output_dir"]) / "sample.wav").exists()
    assert "PRIVATE" not in raw


def _fixture_campaign(sdk, seen_request, control=None, supersets=False):
    def execute(request):
        seen_request.append(dict(request))
        state = {}
        worker._generate_batch(request, state)
        if control is not None:
            control["cancelled"] = True
        result = {"batch_version": worker.BATCH_VERSION, "run_id": request["run_id"],
                  "engine": request["engine"], "status": "completed",
                  **{key: state[key] for key in ("part_count", "completed_parts", "text_sha256",
                                                "part_text_sha256")}}
        if supersets:
            result["private_prompt"] = "PRIVATE_EMBEDDING"
        return result
    return execute


@pytest.mark.parametrize("reuse", [False, True])
def test_supervisor_opt_in_keeps_full_manifest_and_never_serializes_embedding(campaign, sdk, reuse):
    _, values = campaign
    seen = []
    result = lab_batch.run_voice_lab_batch(
        **values, fixture_worker=_fixture_campaign(sdk, seen), reuse_voice_prompt=reuse)
    assert result.status == "completed" and result.part_count == result.completed_parts == 2
    assert ("reuse_voice_prompt" in seen[0]) is reuse
    if reuse:
        assert seen[0]["reuse_voice_prompt"] is True
    assert "".join(seen[0]["chunks"]) == values["text"]
    assert result.text_sha256 == hashlib.sha256(values["text"].encode()).hexdigest()
    with wave.open(result.output_path, "rb") as audio:
        assert audio.getnframes() == 6
    assert len(sdk["prompts"]) == (1 if reuse else 2)
    assert "private_embedding" not in json.dumps(result.metadata())
    assert "reuse_voice_prompt" not in json.dumps(result.metadata())
    assert sorted(path.name for path in Path(result.output_path).parent.iterdir()) == [
        "cache", "home", "part-0000.wav", "part-0001.wav", "reference.wav", "sample.wav", "tmp"]


@pytest.mark.parametrize("reason", ["cancel", "manifest_superset"])
def test_supervisor_refuses_late_cancel_or_manifest_extras_without_partial_final(
    campaign, sdk, reason,
):
    _, values = campaign
    seen, control = [], {"cancelled": False}
    result = lab_batch.run_voice_lab_batch(
        **values, reuse_voice_prompt=True, cancelled=lambda: control["cancelled"],
        fixture_worker=_fixture_campaign(sdk, seen, control if reason == "cancel" else None,
                                         supersets=reason == "manifest_superset"))
    assert result.status == ("cancelled" if reason == "cancel" else "failed")
    assert result.output_path is None
    assert not (Path(seen[0]["output_dir"]) / "sample.wav").exists()
    assert len(sdk["prompts"]) == 1
    assert "PRIVATE" not in json.dumps(result.metadata())


@pytest.mark.parametrize("value", [None, 1, "true", [], {}],
                         ids=["none", "int", "str", "list", "dict"])
def test_supervisor_invalid_flag_precedes_file_io(campaign, monkeypatch, value):
    _, values = campaign
    monkeypatch.setattr(lab_batch, "_plain_path", lambda *args, **kwargs: pytest.fail("file I/O"))
    with pytest.raises(ValueError, match="invalid_voice_prompt_reuse_flag"):
        lab_batch.run_voice_lab_batch(**values, reuse_voice_prompt=value)


def test_supervisor_other_engine_refused_before_file_io(campaign, monkeypatch):
    _, values = campaign
    values["engine"] = "chatterbox_pt_br"
    monkeypatch.setattr(lab_batch, "_plain_path", lambda *args, **kwargs: pytest.fail("file I/O"))
    with pytest.raises(ValueError, match="voice_prompt_reuse_requires_qwen"):
        lab_batch.run_voice_lab_batch(**values, reuse_voice_prompt=True)


def test_single_request_cannot_silently_accept_batch_only_reuse(campaign, sdk, monkeypatch, capsys):
    request, _ = campaign
    request.pop("batch_version")
    request["reuse_voice_prompt"] = True
    code, result, raw = _main(request, monkeypatch, capsys)
    assert code == 2 and result is None and raw == ""
    assert sdk["loads"] == []
