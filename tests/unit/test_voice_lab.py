"""Voice research contracts, bounded subprocess lifecycle and private metadata."""

import hashlib
import json
import math
import os
import struct
import subprocess
import sys
import types
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab import run_voice_lab
from apps.jarvis_voice_lab.lab import prepare_reference, worker_environment


def write_wav(path, *, channels=1, rate=8000, seconds=1, silent=False):
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(channels)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        frame = struct.pack("<h", 0 if silent else 300)
        audio.writeframes(frame * int(rate * seconds) * channels)


@pytest.fixture
def arguments(tmp_path):
    reference = tmp_path / "original.wav"
    write_wav(reference, channels=2)
    model = tmp_path / "model"
    model.mkdir()
    return dict(
        engine="qwen3_tts",
        authorized=True,
        reference_path=reference,
        text="private synthesis sentence",
        model_dir=model,
        python_executable=Path(sys.executable).resolve(),
        workspace_root=tmp_path,
    )


def fixture_worker(request):
    write_wav(Path(request["output_path"]))
    return {"run_id": request["run_id"], "engine": request["engine"], "status": "completed"}


def test_fixture_flow_extracts_readonly_reference_unique_runs_and_content_free_metadata(arguments):
    original = arguments["reference_path"].read_bytes()
    result = run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=fixture_worker)
    again = run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=fixture_worker)
    assert result.status == again.status == "completed"
    assert result.reason == "fixture_only" and result.evidence_mode == "fixture"
    assert result.run_id != again.run_id and result.output_path != again.output_path
    assert arguments["reference_path"].read_bytes() == original
    assert result.output_digest == hashlib.sha256(Path(result.output_path).read_bytes()).hexdigest()
    assert result.sample_rate == 8000 and result.duration_seconds == 1
    assert "private synthesis sentence" not in json.dumps(result.metadata())
    assert "original.wav" not in json.dumps(result.metadata())
    assert "output_path" not in result.metadata()
    assert str(arguments["workspace_root"]) not in result.output_path
    reference = Path(result.output_path).parent / "reference.wav"
    with wave.open(str(reference), "rb") as audio:
        assert audio.getnchannels() == 1


def test_downmix_and_ten_second_limit(tmp_path):
    source, output = tmp_path / "source.wav", tmp_path / "reference.wav"
    with wave.open(str(source), "wb") as audio:
        audio.setnchannels(2)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(struct.pack("<hh", 100, 300) * 8000 * 11)
    assert prepare_reference(source, output) == (8000, 10)
    with wave.open(str(output), "rb") as audio:
        assert audio.getnframes() == 80000
        assert audio.readframes(1) == struct.pack("<h", 200)
    with pytest.raises(FileExistsError):
        prepare_reference(source, output)


@pytest.mark.parametrize("value", [False, None, 1, "yes"])
def test_authorization_not_implicit(arguments, value):
    arguments["authorized"] = value
    with pytest.raises(ValueError, match="authorization_required"):
        run_voice_lab(**arguments)
    assert not (arguments["workspace_root"] / ".research").exists()


@pytest.mark.parametrize(
    "changes",
    [
        {"engine": "remote"},
        {"device": "auto"},
        {"text": ""},
        {"text": "x" * 601},
        {"text": "bad\x00"},
        {"timeout_seconds": 0},
        {"timeout_seconds": float("inf")},
        {"evidence_mode": "fixture"},
        {"fixture_worker": fixture_worker},
    ],
)
def test_invalid_request_does_not_create_lab(arguments, changes):
    with pytest.raises(ValueError):
        run_voice_lab(**{**arguments, **changes})
    assert not (arguments["workspace_root"] / ".research").exists()


def test_silent_truncated_and_bad_format_source_denied(arguments):
    write_wav(arguments["reference_path"], silent=True)
    with pytest.raises(ValueError, match="silent_reference"):
        run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=fixture_worker)
    write_wav(arguments["reference_path"])
    data = arguments["reference_path"].read_bytes()
    arguments["reference_path"].write_bytes(data[:-10])
    with pytest.raises(ValueError, match="truncated_wav"):
        run_voice_lab(**arguments)


def test_output_invalid_or_binding_mismatch_never_completed(arguments):
    result = run_voice_lab(
        **arguments,
        evidence_mode="fixture",
        fixture_worker=lambda r: {
            "run_id": "foreign",
            "engine": r["engine"],
            "status": "completed",
        },
    )
    assert result.reason == "worker_binding_mismatch" and result.output_path is None
    result = run_voice_lab(
        **arguments,
        evidence_mode="fixture",
        fixture_worker=lambda r: {
            "run_id": r["run_id"],
            "engine": r["engine"],
            "status": "completed",
        },
    )
    assert result.reason == "invalid_audio_output"


def test_fixture_exception_no_raw_error_leak(arguments):
    def fail(request):
        raise RuntimeError("secret")

    result = run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=fail)
    assert result.reason == "fixture_worker_failed"
    assert "secret" not in json.dumps(result.metadata())


def test_environment_has_no_inherited_credentials_or_proxies(arguments, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "secret")
    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setenv("HTTPS_PROXY", "secret")
    env = worker_environment(arguments["python_executable"], arguments["workspace_root"])
    assert not {"HF_TOKEN", "OPENAI_API_KEY", "HTTPS_PROXY", "PYTHONPATH"} & env.keys()
    assert env["HF_HUB_OFFLINE"] == env["TRANSFORMERS_OFFLINE"] == "1"
    assert "secret" not in json.dumps(env)


def test_subprocess_private_stdin_and_verified_output(arguments, monkeypatch):
    seen = {}

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            seen.update(command=command, kwargs=kwargs)
            self.stdout = kwargs["stdout"]

        def communicate(self, input=None, timeout=None):
            request = json.loads(input)
            seen["request"] = request
            response = fixture_worker(request)
            self.stdout.write(json.dumps(response).encode())
            self.stdout.flush()
            return None, None

    monkeypatch.setattr(subprocess, "Popen", Process)
    result = run_voice_lab(**arguments)
    assert result.status == "completed" and result.evidence_mode == "model_real"
    assert seen["command"][1] == "-I"
    assert arguments["text"] not in " ".join(seen["command"])
    assert arguments["text"] == seen["request"]["text"]
    assert seen["kwargs"]["stderr"] == subprocess.DEVNULL
    # Mock lifecycle validates composition; does not prove a real model generated sound.


@pytest.mark.parametrize("control", ["deadline", "cancel"])
def test_subprocess_timeout_or_cancel_kills_and_reaps(arguments, monkeypatch, control):
    seen = {"kills": 0, "calls": 0}

    class Process:
        returncode = None

        def __init__(self, *args, **kwargs):
            pass

        def communicate(self, input=None, timeout=None):
            seen["calls"] += 1
            if self.returncode is not None:
                return b"", None
            raise subprocess.TimeoutExpired("worker", timeout)

        def poll(self):
            return self.returncode

        def kill(self):
            seen["kills"] += 1
            self.returncode = -1

    monkeypatch.setattr(subprocess, "Popen", Process)
    if control == "deadline":
        result = run_voice_lab(**arguments, timeout_seconds=0.001)
        assert result.status == "timed_out"
    else:
        result = run_voice_lab(**arguments, cancelled=lambda: seen["calls"] > 0)
        assert result.status == "cancelled"
    assert seen["kills"] == 1
    assert seen["calls"] >= (1 if control == "deadline" else 2)


def test_cancel_before_subprocess(arguments, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("worker should not start")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = run_voice_lab(**arguments, cancelled=lambda: True)
    assert result.status == "cancelled"


def test_model_id_not_local_directory(arguments):
    arguments["model_dir"] = Path("Qwen/remote-model")
    with pytest.raises(OSError):
        run_voice_lab(**arguments)


def test_cli_requires_authorized_and_never_echoes_text(arguments):
    command = [sys.executable, "-m", "apps.jarvis_voice_lab"]
    denied = subprocess.run(command, capture_output=True, text=True)
    assert denied.returncode == 2
    assert "--authorized" in denied.stderr


def test_sdk_imports_lazy():

    assert "qwen_tts" not in sys.modules
    assert "chatterbox" not in sys.modules


def test_silent_output_and_truncated_data_with_junk_are_rejected(arguments):
    def silent(request):
        write_wav(Path(request["output_path"]), silent=True)
        return {"run_id": request["run_id"], "engine": request["engine"], "status": "completed"}

    result = run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=silent)
    assert result.reason == "invalid_audio_output"
    fmt = struct.pack("<HHIIHH", 1, 1, 8000, 16000, 2, 16)
    body = (
        b"WAVEfmt "
        + struct.pack("<I", 16)
        + fmt
        + b"JUNK"
        + struct.pack("<I", 20000)
        + b"x" * 20000
        + b"data"
        + struct.pack("<I", 16000)
        + b"x" * 100
    )
    arguments["reference_path"].write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)
    with pytest.raises(ValueError, match="truncated_wav"):
        run_voice_lab(**arguments)


def test_redirected_asset_or_hardlink_denied(arguments):
    asset = arguments["model_dir"] / "model.safetensors"
    try:
        os.link(arguments["reference_path"], asset)
    except OSError:
        pytest.skip("hardlink unavailable on this filesystem")
    with pytest.raises(ValueError, match="regular_single_link_file_required"):
        run_voice_lab(**arguments)


def test_native_stdout_oversize_bounded_and_spool_removed(arguments, monkeypatch):
    seen = {}

    class Process:
        returncode = 0

        def __init__(self, command, **kwargs):
            self.stdout = kwargs["stdout"]
            seen["spool"] = Path(self.stdout.name)

        def communicate(self, input=None, timeout=None):
            self.stdout.write(b"x" * 4097)
            self.stdout.flush()
            return None, None

    monkeypatch.setattr(subprocess, "Popen", Process)
    result = run_voice_lab(**arguments)
    assert result.reason == "invalid_worker_metadata"
    assert not seen["spool"].exists()


def test_diagnostics_only_allowlisted_class_stage(arguments):
    def failed(request):
        return {
            "run_id": request["run_id"],
            "engine": request["engine"],
            "status": "failed",
            "reason": "local_inference_failed",
            "failure_stage": "model_load",
            "error_type": "RuntimeError",
            "message": "secret",
        }

    result = run_voice_lab(**arguments, evidence_mode="fixture", fixture_worker=failed)
    assert result.failure_stage == "model_load" and result.error_type == "RuntimeError"
    assert "secret" not in json.dumps(result.metadata())


@pytest.mark.parametrize(
    "values,expected",
    [
        ([0.2, 0.1], "valid"),
        ([float("nan")], "invalid"),
        ([float("inf")], "invalid"),
        ([0.0, 0.0], "invalid"),
        ([], "invalid"),
    ],
)
@pytest.mark.parametrize("profile", ["baseline", "qwen_icl", "qwen_icl_draft"])
def test_worker_qwen_exact_local_api_and_numeric_guards(
    arguments,
    monkeypatch,
    values,
    expected,
    profile,
):
    from apps.jarvis_voice_lab.worker import _generate

    class Array(list):
        ndim = 1

        def __ne__(self, value):
            return [item != value for item in self]

    seen = {}

    class Model:
        @classmethod
        def from_pretrained(cls, path, **kwargs):
            seen.update(path=path, load=kwargs)
            return cls()

        def generate_voice_clone(self, **kwargs):
            seen["generate"] = kwargs
            return [Array(values)], 24000

    def write(handle, audio, rate, **kwargs):
        with wave.open(handle, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(b"\x01\x00" * len(audio))

    numpy = types.SimpleNamespace(
        asarray=lambda value: value,
        isfinite=lambda value: types.SimpleNamespace(
            all=lambda: all(math.isfinite(v) for v in value)
        ),
        any=any,
        clip=lambda value, minimum, maximum: value,
    )
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    monkeypatch.setitem(
        sys.modules, "torch", types.SimpleNamespace(float32="fp32", bfloat16="bf16")
    )
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=write))
    monkeypatch.setitem(sys.modules, "qwen_tts", types.SimpleNamespace(Qwen3TTSModel=Model))
    output = arguments["workspace_root"] / "output.wav"
    request = {
        "model_dir": str(arguments["model_dir"]),
        "reference_path": str(arguments["reference_path"]),
        "output_path": str(output),
        "device": "cpu",
        "engine": "qwen3_tts",
        "text": arguments["text"],
        "voice_profile": profile,
        "reference_transcript": "Referencia exata fixture." if profile != "baseline" else None,
        "transcript_confirmed": profile == "qwen_icl",
    }
    state = {}
    if expected == "invalid":
        with pytest.raises(ValueError, match="invalid_generated_audio"):
            _generate(request, state)
        assert not output.exists()
    else:
        _generate(request, state)
        assert output.exists()
    assert seen["path"] == str(arguments["model_dir"])
    assert seen["load"] == {
        "device_map": "cpu",
        "dtype": "fp32",
        "attn_implementation": "sdpa",
        "local_files_only": True,
        "trust_remote_code": False,
    }
    assert seen["generate"]["language"] == "Portuguese"
    assert seen["generate"]["x_vector_only_mode"] is (profile == "baseline")
    if profile != "baseline":
        assert seen["generate"]["ref_text"] == "Referencia exata fixture."
    else:
        assert "ref_text" not in seen["generate"]
    assert state["failure_stage"] == "save"


@pytest.mark.parametrize("profile", ["baseline", "chatterbox_conversational"])
def test_chatterbox_loader_uses_reviewed_v3_source_and_standard_generation(
    arguments,
    monkeypatch,
    profile,
):
    from apps.jarvis_voice_lab.worker import _generate

    class Array(list):
        ndim = 1

        def __ne__(self, value):
            return [item != value for item in self]

    class Tensor:
        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return Array([0.1, 0.2])

    seen = {}

    class Model:
        sr = 24000

        @classmethod
        def from_local(cls, model_dir, device, t3_filename=None, s3gen_filename=None):
            seen["load"] = (model_dir, device, t3_filename, s3gen_filename)
            return cls()

        def generate(self, text, **kwargs):
            seen["generate"] = (text, kwargs)
            return Tensor()

    def write(handle, audio, rate, **kwargs):
        with wave.open(handle, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(b"\x01\x00" * len(audio))

    source = arguments["workspace_root"] / "source"
    script = source / "chatterbox" / "src" / "chatterbox" / "tts.py"
    script.parent.mkdir(parents=True)
    script.write_text("# fixture source marker", encoding="utf-8")
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setitem(
        sys.modules,
        "numpy",
        types.SimpleNamespace(
            asarray=lambda value: value,
            any=any,
            clip=lambda value, minimum, maximum: value,
            isfinite=lambda value: types.SimpleNamespace(all=lambda: True),
        ),
    )
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace())
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=write))
    module = types.ModuleType("chatterbox.src.chatterbox.tts")
    module.ChatterboxTTS = Model
    monkeypatch.setitem(sys.modules, "chatterbox.src.chatterbox.tts", module)
    _generate(
        {
            "engine": "chatterbox_pt_br",
            "device": "cpu",
            "model_dir": str(arguments["model_dir"]),
            "sdk_source_dir": str(source),
            "reference_path": str(arguments["reference_path"]),
            "output_path": str(arguments["workspace_root"] / "chatter.wav"),
            "text": arguments["text"],
            "voice_profile": profile,
        }
    )
    assert seen["load"] == (arguments["model_dir"], "cpu", "t3_pt_br.safetensors", "s3gen_v3.pt")
    assert seen["generate"] == (
        arguments["text"],
        {
            "language_id": "pt",
            "audio_prompt_path": str(arguments["reference_path"]),
            **(
                {"exaggeration": 0.35, "cfg_weight": 0.3, "temperature": 0.75}
                if profile == "chatterbox_conversational"
                else {}
            ),
        },
    )
