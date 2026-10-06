"""Synthetic SDK proof: bounded exact-text campaigns, one local model load."""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import math
import os
import stat
import sys
import types
import wave

import pytest

from apps.jarvis_voice_lab import worker


class Array(list):
    def __init__(self, values, *, ndim=1, reported_length=None):
        super().__init__(values)
        self.ndim = ndim
        self.shape = (len(values),)
        self.reported_length = reported_length

    def __len__(self):
        return super().__len__() if self.reported_length is None else self.reported_length

    def __ne__(self, value):
        return [item != value for item in self]


class Tensor:
    def __init__(self, values):
        self.values = values

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.values


@pytest.fixture
def batch_request(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    reference = tmp_path / "reference.wav"
    with wave.open(str(reference), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x01\x00" * 24)
    output = tmp_path / "private"
    output.mkdir(mode=0o700)
    source = tmp_path / "sdk"
    marker = source / "chatterbox" / "src" / "chatterbox" / "tts.py"
    marker.parent.mkdir(parents=True)
    marker.write_text("# Synthetic SDK marker only.\n", encoding="utf-8")
    parts = ["  Olá! e\u0301\r\n", "🚀 Continuação exata.\t", "Fim, sem truncagem.  "]
    return {
        "batch_version": worker.BATCH_VERSION,
        "authorized": True,
        "run_id": "c0" * 16,
        "engine": "qwen3_tts",
        "device": "cpu",
        "text": "".join(parts),
        "chunks": parts,
        "reference_path": str(reference),
        "model_dir": str(model),
        "output_dir": str(output),
        "sdk_source_dir": str(source),
        "voice_profile": "baseline",
        "reference_transcript": None,
        "transcript_confirmed": False,
        "seed": 42,
    }


@pytest.fixture
def sdk(monkeypatch):
    """Never import numpy, torch, soundfile or real model dependencies."""
    seen = {"loads": [], "generations": [], "writes": [], "seeds": []}

    class Model:
        sr = 24000

        @classmethod
        def from_pretrained(cls, path, **kwargs):
            seen["loads"].append(("qwen", path, kwargs))
            if seen.get("load_error"):
                raise seen["load_error"]
            return cls()

        @classmethod
        def from_local(cls, model_dir, device, t3_filename=None, s3gen_filename=None):
            seen["loads"].append(("chatterbox", model_dir, device, t3_filename, s3gen_filename))
            if seen.get("load_error"):
                raise seen["load_error"]
            return cls()

        def _part(self, text, options):
            seen["generations"].append((text, options))
            if len(seen["generations"]) == seen.get("fail_part"):
                raise seen.get("error", RuntimeError("PRIVATE_SDK_TEXT"))
            return seen.get("audio", Array([0.1, -0.2, 0.3]))

        def generate_voice_clone(self, **kwargs):
            text = kwargs.pop("text")
            audio = self._part(text, kwargs)
            return seen.get("wavs", [audio]), seen.get("rate", self.sr)

        def generate(self, text, **kwargs):
            return Tensor(self._part(text, kwargs))

    def write(handle, audio, rate, **kwargs):
        seen["writes"].append((handle.name, kwargs, rate))
        with wave.open(handle, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(b"\x01\x00" * len(audio))

    numpy = types.SimpleNamespace(
        asarray=lambda audio: audio,
        any=any,
        clip=lambda audio, minimum, maximum: audio,
        isfinite=lambda audio: types.SimpleNamespace(
            all=lambda: all(math.isfinite(value) for value in audio)
        ),
        random=types.SimpleNamespace(seed=lambda seed: seen["seeds"].append(("numpy", seed))),
    )
    torch = types.SimpleNamespace(
        float32="float32",
        bfloat16="bfloat16",
        manual_seed=lambda seed: seen["seeds"].append(("torch", seed)),
    )
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=write))
    monkeypatch.setitem(sys.modules, "qwen_tts", types.SimpleNamespace(Qwen3TTSModel=Model))
    module = types.ModuleType("chatterbox.src.chatterbox.tts")
    module.ChatterboxTTS = Model
    monkeypatch.setitem(sys.modules, "chatterbox.src.chatterbox.tts", module)
    monkeypatch.setattr(sys, "path", list(sys.path))
    import random

    monkeypatch.setattr(random, "seed", lambda seed: seen["seeds"].append(("random", seed)))
    seen["model"] = Model
    return seen


PROFILES = [
    ("qwen3_tts", "baseline"),
    ("qwen3_tts", "qwen_icl"),
    ("qwen3_tts", "qwen_icl_draft"),
    ("chatterbox_pt_br", "baseline"),
    ("chatterbox_pt_br", "chatterbox_conversational"),
]


@pytest.mark.parametrize("engine,profile", PROFILES)
@pytest.mark.parametrize("device", ["cpu", "cuda:0"])
def test_batch_loads_once_generates_exact_sequence_and_preserves_sdk_options(
    batch_request, sdk, engine, profile, device
):
    batch_request.update(engine=engine, voice_profile=profile, device=device)
    if profile in {"qwen_icl", "qwen_icl_draft"}:
        batch_request.update(
            reference_transcript="  Referência e\u0301 exata.\r\n",
            transcript_confirmed=profile == "qwen_icl",
        )
    state = {}
    worker._generate_batch(batch_request, state)
    assert len(sdk["loads"]) == 1
    assert [text for text, _ in sdk["generations"]] == batch_request["chunks"]
    assert sdk["seeds"] == [("random", 42), ("numpy", 42), ("torch", 42)]
    assert state["part_count"] == state["completed_parts"] == 3
    assert state["text_sha256"] == hashlib.sha256(batch_request["text"].encode("utf-8")).hexdigest()
    assert state["part_text_sha256"] == [
        hashlib.sha256(part.encode("utf-8")).hexdigest() for part in batch_request["chunks"]
    ]
    assert state["failure_stage"] == "save"
    if engine == "qwen3_tts":
        assert sdk["loads"][0][2] == {
            "device_map": device,
            "dtype": "float32" if device == "cpu" else "bfloat16",
            "attn_implementation": "sdpa",
            "local_files_only": True,
            "trust_remote_code": False,
        }
        options = {
            "language": "Portuguese",
            "ref_audio": batch_request["reference_path"],
            "x_vector_only_mode": profile == "baseline",
            "max_new_tokens": 1024,
        }
        if profile != "baseline":
            options["ref_text"] = batch_request["reference_transcript"]
    else:
        from pathlib import Path

        assert sdk["loads"][0] == (
            "chatterbox",
            Path(batch_request["model_dir"]),
            device,
            "t3_pt_br.safetensors",
            "s3gen_v3.pt",
        )
        options = {"language_id": "pt", "audio_prompt_path": batch_request["reference_path"]}
        if profile != "baseline":
            options.update(exaggeration=0.35, cfg_weight=0.3, temperature=0.75)
    assert all(arguments == options for _, arguments in sdk["generations"])
    from pathlib import Path

    for index in range(3):
        output = Path(batch_request["output_dir"]) / f"part-{index:04d}.wav"
        with wave.open(str(output), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 24000
            assert wav.getnframes() == 3
        if os.name != "nt":
            assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert all(options == {"format": "WAV", "subtype": "PCM_16"} for _, options, _ in sdk["writes"])


@pytest.mark.parametrize("engine", ["qwen3_tts", "chatterbox_pt_br"])
def test_failed_part_stops_without_retry_reload_or_aggregate_success(batch_request, sdk, engine):
    from pathlib import Path

    batch_request["engine"] = engine
    sdk["fail_part"] = 2
    state = {}
    with pytest.raises(RuntimeError, match="PRIVATE_SDK_TEXT"):
        worker._generate_batch(batch_request, state)
    assert len(sdk["loads"]) == 1
    assert len(sdk["generations"]) == 2
    assert state["completed_parts"] == 1
    assert state["failure_stage"] == "generate"
    assert (Path(batch_request["output_dir"]) / "part-0000.wav").is_file()
    assert not (Path(batch_request["output_dir"]) / "part-0001.wav").exists()
    assert not (Path(batch_request["output_dir"]) / "sample.wav").exists()


INVALID_FIELDS = [
    {"authorized": False},
    {"authorized": 1},
    {"batch_version": "other"},
    {"run_id": "unsafe"},
    {"run_id": "C0" * 16},
    {"run_id": 123},
    {"engine": "other"},
    {"device": "cuda:1"},
    {"extra": True},
    {"output_path": "other"},
    {"text": ""},
    {"text": " "},
    {"text": 1},
    {"text": "x" * 6001},
    {"text": "private\x00"},
    {"text": "private\x7f"},
    {"text": "private\u200b"},
    {"text": "private\ud800"},
    {"chunks": []},
    {"chunks": ["x"] * 17},
    {"chunks": [""]},
    {"chunks": ["x" * 601]},
    {"chunks": [" "]},
    {"chunks": [123]},
    {"chunks": "private"},
    {"chunks": ["replaced"]},
    {"seed": True},
    {"seed": -1},
    {"seed": 2**32},
    {"seed": 1.5},
    {"voice_profile": "unknown"},
    {"voice_profile": "chatterbox_conversational"},
    {"transcript_confirmed": 1},
    {"reference_transcript": "unused"},
    {
        "voice_profile": "qwen_icl",
        "reference_transcript": "reference",
        "transcript_confirmed": False,
    },
    {
        "voice_profile": "qwen_icl_draft",
        "reference_transcript": "reference",
        "transcript_confirmed": True,
    },
    {"voice_profile": "qwen_icl", "reference_transcript": " ", "transcript_confirmed": True},
    {"voice_profile": "qwen_icl", "reference_transcript": "x" * 2001, "transcript_confirmed": True},
    {"voice_profile": "qwen_icl", "reference_transcript": "x\u200b", "transcript_confirmed": True},
    {"reference_path": "relative.wav"},
    {"model_dir": None},
    {"output_dir": "relative"},
]


@pytest.mark.parametrize("changes", INVALID_FIELDS)
def test_invalid_batch_rejected_before_heavy_imports(batch_request, monkeypatch, changes):
    batch_request.update(changes)
    original = builtins.__import__
    seen = []

    def guard(name, *args, **kwargs):
        if name in {"numpy", "torch", "soundfile", "qwen_tts"} or name.startswith("chatterbox"):
            seen.append(name)
            raise AssertionError("heavy_import_before_validation")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guard)
    with pytest.raises((ValueError, TypeError)):
        worker._generate_batch(batch_request)
    assert seen == []


@pytest.mark.parametrize("field", ["text", "chunks", "output_dir", "run_id", "authorized"])
def test_missing_required_field_rejected(batch_request, field):
    del batch_request[field]
    with pytest.raises(ValueError, match="invalid_batch_fields"):
        worker._generate_batch(batch_request)


def test_existing_part_denied_before_model_load(batch_request, sdk):
    from pathlib import Path

    output = Path(batch_request["output_dir"]) / "part-0001.wav"
    output.write_bytes(b"Existing artifact must not be overwritten.")
    with pytest.raises(ValueError, match="output_already_exists"):
        worker._generate_batch(batch_request)
    assert sdk["loads"] == []
    assert output.read_bytes() == b"Existing artifact must not be overwritten."


def test_part_creation_race_remains_exclusive(batch_request, sdk):
    from pathlib import Path

    original = sdk["model"].generate_voice_clone
    target = Path(batch_request["output_dir"]) / "part-0000.wav"

    def race(self, **kwargs):
        target.write_bytes(b"raced artifact")
        return original(self, **kwargs)

    sdk["model"].generate_voice_clone = race
    state = {}
    with pytest.raises(FileExistsError):
        worker._generate_batch(batch_request, state)
    assert state["completed_parts"] == 0
    assert target.read_bytes() == b"raced artifact"


@pytest.mark.parametrize(
    "audio,rate",
    [
        (Array([]), 24000),
        (Array([0.0]), 24000),
        (Array([float("nan")]), 24000),
        (Array([float("inf")]), 24000),
        (Array([0.1], ndim=2), 24000),
        (Array([0.1], ndim=3), 24000),
        (Array([0.1]), 7999),
        (Array([0.1]), 96001),
        (Array([0.1]), True),
        (Array([0.1]), 24000.0),
        (Array([0.1], reported_length=8000 * 120 + 1), 8000),
    ],
)
def test_invalid_audio_shape_rate_signal_or_duration_has_no_completed_part(
    batch_request, sdk, audio, rate
):
    sdk.update(audio=audio, rate=rate)
    state = {}
    with pytest.raises(ValueError, match="invalid_generated_audio"):
        worker._generate_batch(batch_request, state)
    assert state["completed_parts"] == 0
    assert state["failure_stage"] == "save"
    assert sdk["writes"] == []


@pytest.mark.parametrize("wavs", [[], [Array([0.1]), Array([0.2])], None, "not-wave-list"])
def test_qwen_must_return_exactly_one_wave_per_part(batch_request, sdk, wavs):
    sdk["wavs"] = wavs
    state = {}
    with pytest.raises(ValueError, match="invalid_generated_audio"):
        worker._generate_batch(batch_request, state)
    assert state["failure_stage"] == "generate"
    assert state["completed_parts"] == 0


@pytest.mark.parametrize("missing", ["numpy", "qwen_tts", "torch", "soundfile"])
def test_unavailable_sdk_does_not_generate_or_reload(batch_request, sdk, monkeypatch, missing):
    monkeypatch.setitem(sys.modules, missing, None)
    state = {}
    with pytest.raises(ImportError):
        worker._generate_batch(batch_request, state)
    assert state["failure_stage"] == "import"
    assert state["completed_parts"] == 0
    assert sdk["loads"] == sdk["generations"] == []


@pytest.mark.parametrize("source", [None, "missing_marker"])
def test_chatterbox_incompatible_source_has_no_model_load(batch_request, sdk, source):
    from pathlib import Path

    batch_request["engine"] = "chatterbox_pt_br"
    if source is None:
        batch_request["sdk_source_dir"] = None
    else:
        (
            Path(batch_request["sdk_source_dir"]) / "chatterbox" / "src" / "chatterbox" / "tts.py"
        ).unlink()
    with pytest.raises(NotImplementedError, match="sdk_incompatible"):
        worker._generate_batch(batch_request)
    assert sdk["loads"] == []


def test_chatterbox_incompatible_loader_signature_has_no_model_load(batch_request, sdk):
    batch_request["engine"] = "chatterbox_pt_br"
    sdk["model"].from_local = lambda path, device: None
    with pytest.raises(NotImplementedError, match="sdk_incompatible"):
        worker._generate_batch(batch_request)
    assert sdk["loads"] == []


def call_main(batch_request, monkeypatch, *, raw=None):
    data = json.dumps(batch_request).encode("utf-8") if raw is None else raw
    buffer = io.BytesIO(data)
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(buffer=buffer))
    network = []
    monkeypatch.setattr(worker, "_deny_network", lambda: network.append("denied"))
    return worker.main(), network, buffer.tell()


def test_main_completed_batch_contract_is_bounded_and_content_free(
    batch_request, sdk, monkeypatch, capsys
):
    code, network, _ = call_main(batch_request, monkeypatch)
    captured = capsys.readouterr()
    assert code == 0 and network == ["denied"]
    result = json.loads(captured.out)
    assert set(result) == {
        "batch_version",
        "run_id",
        "engine",
        "status",
        "part_count",
        "completed_parts",
        "text_sha256",
        "part_text_sha256",
    }
    assert result["status"] == "completed"
    assert result["part_count"] == result["completed_parts"] == 3
    assert len(captured.out.encode("utf-8")) <= 4096
    for content in (
        batch_request["text"],
        batch_request["reference_path"],
        batch_request["output_dir"],
    ):
        assert content not in captured.out


@pytest.mark.parametrize(
    "error,reason,kind",
    [
        (ModuleNotFoundError("PRIVATE_SDK_TEXT"), "sdk_unavailable", "ModuleNotFoundError"),
        (NotImplementedError("PRIVATE_SDK_TEXT"), "sdk_incompatible", "NotImplementedError"),
        (RuntimeError("PRIVATE_SDK_TEXT"), "local_inference_failed", "RuntimeError"),
    ],
)
def test_main_failed_batch_has_no_success_and_sanitized_partial_metadata(
    batch_request, sdk, monkeypatch, capsys, error, reason, kind
):
    sdk.update(fail_part=2, error=error)
    code, _, _ = call_main(batch_request, monkeypatch)
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert code == 0
    assert result["status"] == "failed"
    assert result["reason"] == reason and result["error_type"] == kind
    assert result["failure_stage"] == "generate"
    assert result["completed_parts"] == 1
    assert result["part_count"] == 3
    assert "PRIVATE_SDK_TEXT" not in captured.out
    assert batch_request["output_dir"] not in captured.out
    assert batch_request["text"] not in captured.out


def test_main_suppresses_sdk_stdout_and_sanitizes_unknown_error_type(
    batch_request, sdk, monkeypatch, capsys
):
    class PrivateSdkException(Exception):
        pass

    original = sdk["model"].generate_voice_clone

    def noisy(self, **kwargs):
        print("PRIVATE_SDK_TEXT")
        return original(self, **kwargs)

    sdk["model"].generate_voice_clone = noisy
    sdk.update(fail_part=2, error=PrivateSdkException("PRIVATE_SDK_TEXT"))
    code, _, _ = call_main(batch_request, monkeypatch)
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["error_type"] == "SdkError"
    assert "PRIVATE_SDK_TEXT" not in captured.out
    assert "PRIVATE_SDK_TEXT" in captured.err


@pytest.mark.parametrize(
    "raw",
    [
        b"[]",
        b"null",
        b"{}",
        b"invalid",
        b"x" * 131073,
        b'{"batch_version":"jarvis-voice-batch-v1","batch_version":"bad"}',
    ],
    ids=["list", "null", "empty", "invalid-json", "over-limit", "duplicate"],
)
def test_main_invalid_bounded_input_never_activates_network_or_sdk(
    batch_request, sdk, monkeypatch, capsys, raw
):
    code, network, consumed = call_main(batch_request, monkeypatch, raw=raw)
    assert code == 2 and network == []
    assert consumed <= 131073
    assert sdk["loads"] == []
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "changes", [{"authorized": False}, {"authorized": 1}, {"device": "cuda:2"}]
)
def test_main_authorization_and_shape_validated_before_worker(
    batch_request, sdk, monkeypatch, capsys, changes
):
    batch_request.update(changes)
    code, network, _ = call_main(batch_request, monkeypatch)
    assert code == 2 and network == []
    assert sdk["loads"] == []
    assert capsys.readouterr().out == ""


def test_main_legacy_keeps_16384_byte_limit_and_dispatch(batch_request, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(worker, "_generate", lambda value, state: calls.append(value))
    legacy = {"authorized": True, "run_id": "legacy", "engine": "qwen3_tts", "device": "cpu"}
    minimal = json.dumps(legacy).encode("utf-8")
    raw = minimal + b" " * (16384 - len(minimal))
    code, network, consumed = call_main(batch_request, monkeypatch, raw=raw)
    assert code == 0 and network == ["denied"] and consumed == 16384
    assert calls == [legacy]
    assert json.loads(capsys.readouterr().out) == {
        "run_id": "legacy",
        "engine": "qwen3_tts",
        "status": "completed",
    }
    code, network, _ = call_main(batch_request, monkeypatch, raw=raw + b" ")
    assert code == 2 and network == [] and calls == [legacy]
    assert capsys.readouterr().out == ""


def test_main_reads_no_more_than_batch_bound(batch_request, monkeypatch, capsys):
    class BoundedReader:
        def read(self, limit):
            assert limit == 131073
            return b"x" * limit

    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(buffer=BoundedReader()))
    assert worker.main() == 2
    assert capsys.readouterr().out == ""


def test_maximum_text_batch_has_exact_hashes_and_loads_once(batch_request, sdk):
    batch_request["chunks"] = ["🚀" * 600] * 10
    batch_request["text"] = "".join(batch_request["chunks"])
    state = {}
    worker._generate_batch(batch_request, state)
    assert state["completed_parts"] == 10
    assert len(sdk["loads"]) == 1
    assert "".join(text for text, _ in sdk["generations"]) == batch_request["text"]


@pytest.mark.parametrize("seed", [None, 0, 2**32 - 1])
def test_seed_boundary_kept_exact_and_optional(batch_request, sdk, seed):
    batch_request["seed"] = seed
    worker._generate_batch(batch_request)
    assert sdk["seeds"] == (
        [] if seed is None else [("random", seed), ("numpy", seed), ("torch", seed)]
    )


@pytest.mark.parametrize("field", ["model_dir", "output_dir", "reference_path", "sdk_source_dir"])
@pytest.mark.parametrize("redirect", ["symlink", "reparse"])
def test_redirected_paths_rejected_before_any_model_load(
    batch_request, sdk, monkeypatch, field, redirect
):
    from pathlib import Path

    target = Path(batch_request[field])
    original = Path.lstat

    def changed(path):
        info = original(path)
        if path != target:
            return info
        return types.SimpleNamespace(
            st_mode=stat.S_IFLNK if redirect == "symlink" else info.st_mode,
            st_file_attributes=0x400 if redirect == "reparse" else 0,
        )

    monkeypatch.setattr(Path, "lstat", changed)
    with pytest.raises(ValueError, match="redirected_path_denied"):
        worker._generate_batch(batch_request)
    assert sdk["loads"] == []


def test_reference_hardlink_refused_before_any_model_load(batch_request, sdk, monkeypatch):
    from pathlib import Path

    reference = Path(batch_request["reference_path"])
    original = Path.stat

    def changed(path, *args, **kwargs):
        info = original(path, *args, **kwargs)
        if path != reference:
            return info
        return types.SimpleNamespace(st_mode=info.st_mode, st_nlink=2)

    monkeypatch.setattr(Path, "stat", changed)
    with pytest.raises(ValueError, match="regular_single_link_file_required"):
        worker._generate_batch(batch_request)
    assert sdk["loads"] == []


def test_maximum_part_count_has_one_load_and_bounded_response(
    batch_request, sdk, monkeypatch, capsys
):
    batch_request["chunks"] = ["Exact part. 🚀\r\n" + "x" * 300 for _ in range(16)]
    batch_request["text"] = "".join(batch_request["chunks"])
    code, _, _ = call_main(batch_request, monkeypatch)
    output = capsys.readouterr().out
    result = json.loads(output)
    assert code == 0 and result["status"] == "completed"
    assert result["part_count"] == result["completed_parts"] == 16
    assert len(result["part_text_sha256"]) == 16
    assert len(output.encode("utf-8")) <= 4096
    assert len(sdk["loads"]) == 1 and len(sdk["generations"]) == 16


def test_serialized_batch_bound_is_checked_before_import_or_filesystem(batch_request, monkeypatch):
    batch_request["sdk_source_dir"] = "x" * 131073
    seen = []
    monkeypatch.setattr(worker, "_batch_path", lambda *args, **kwargs: seen.append(args))
    with pytest.raises(ValueError, match="batch_payload_too_large"):
        worker._generate_batch(batch_request)
    assert seen == []


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "utf-32"])
def test_main_batch_requires_strict_unmarked_utf8(
    batch_request, sdk, monkeypatch, capsys, encoding
):
    raw = json.dumps(batch_request).encode(encoding)
    code, network, _ = call_main(batch_request, monkeypatch, raw=raw)
    assert code == 2 and network == [] and sdk["loads"] == []
    assert capsys.readouterr().out == ""


def test_main_batch_duplicate_field_refused_even_when_final_value_valid(
    batch_request, sdk, monkeypatch, capsys
):
    raw = json.dumps(batch_request).encode("utf-8")
    raw = b'{"authorized":false,' + raw[1:]
    code, network, _ = call_main(batch_request, monkeypatch, raw=raw)
    assert code == 2 and network == [] and sdk["loads"] == []
    assert capsys.readouterr().out == ""


def test_main_unavailable_sdk_has_canonical_bounded_failure(
    batch_request, sdk, monkeypatch, capsys
):
    monkeypatch.setitem(sys.modules, "qwen_tts", None)
    code, _, _ = call_main(batch_request, monkeypatch)
    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert result["status"] == "failed" and result["reason"] == "sdk_unavailable"
    assert result["error_type"] == "ModuleNotFoundError"
    assert result["failure_stage"] == "import" and result["completed_parts"] == 0
    assert result["part_count"] == 3 and len(result["part_text_sha256"]) == 3


def test_model_load_failure_has_zero_parts_and_no_generate(batch_request, sdk, monkeypatch, capsys):
    sdk["load_error"] = RuntimeError("PRIVATE_MODEL_PATH")
    code, _, _ = call_main(batch_request, monkeypatch)
    output = capsys.readouterr().out
    result = json.loads(output)
    assert code == 0
    assert result["status"] == "failed" and result["reason"] == "local_inference_failed"
    assert result["failure_stage"] == "model_load" and result["completed_parts"] == 0
    assert sdk["generations"] == [] and len(sdk["loads"]) == 1
    assert "PRIVATE_MODEL_PATH" not in output
