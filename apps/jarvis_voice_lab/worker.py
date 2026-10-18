"""Standalone subprocess entrypoint; heavyweight SDK imports never reach the Core."""

from __future__ import annotations

import contextlib
import hashlib
import inspect
import json
import math
import os
import re
import socket
import stat
import sys
import time
import unicodedata
from pathlib import Path
from typing import Callable

BATCH_VERSION = "jarvis-voice-batch-v1"
MAX_BATCH_BYTES = 131072
DIAGNOSTICS_VERSION = "jarvis-voice-diagnostics-v1"
DIAGNOSTICS_NAME = "worker-diagnostics.jsonl"
MAX_DIAGNOSTICS_BYTES = 32768
MAX_DIAGNOSTICS_EVENTS = 80
_DIAGNOSTIC_RESOURCES = frozenset({
    "cuda_allocated_bytes", "cuda_reserved_bytes", "cuda_peak_allocated_bytes",
})


def _finite_number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def _diagnostic_identity(run_id, engine, device):
    if (type(run_id) is not str or re.fullmatch(r"[a-f0-9]{32}", run_id) is None
            or type(engine) is not str or engine not in {"qwen3_tts", "chatterbox_pt_br"}
            or type(device) is not str or device not in {"cpu", "cuda:0"}):
        raise ValueError("invalid_diagnostic_identity")


def _diagnostic_event(value, *, run_id, engine, device, sequence, previous_elapsed):
    if (type(value) is not dict or set(value) != {
        "schema_version", "sequence", "run_id", "engine", "device", "phase", "event",
        "elapsed_seconds", "part_index", "resources",
    } or value["schema_version"] != DIAGNOSTICS_VERSION
            or type(value["sequence"]) is not int or value["sequence"] != sequence
            or value["run_id"] != run_id or value["engine"] != engine
            or value["device"] != device):
        raise ValueError("invalid_diagnostic_event")
    phase, event, part = value["phase"], value["event"], value["part_index"]
    if (type(phase) is not str or phase not in {
        "imports", "model_load", "reference_conditioning", "generate", "save", "completion",
    } or type(event) is not str or event not in {"started", "completed", "failed"}
            or (phase == "completion" and event == "started")
            or (phase != "completion" and event == "failed")
            or (phase == "reference_conditioning" and engine != "qwen3_tts")
            or (phase in {"generate", "save"} and (type(part) is not int or not 0 <= part < 16))
            or (phase not in {"generate", "save"} and part is not None)):
        raise ValueError("invalid_diagnostic_phase")
    elapsed = value["elapsed_seconds"]
    if (not _finite_number(elapsed)
            or not previous_elapsed <= elapsed <= 86400):
        raise ValueError("invalid_diagnostic_clock")
    resources = value["resources"]
    if (type(resources) is not dict or not resources.keys() <= _DIAGNOSTIC_RESOURCES
            or (device == "cpu" and resources)
            or any(type(item) is not int or not 0 <= item < 2**63
                   for item in resources.values())):
        raise ValueError("invalid_diagnostic_resources")
    return value


class VoiceDiagnostics:
    """Private, bounded metadata only; its output is never an audio-success oracle."""

    def __init__(self, directory: Path, *, run_id: str, engine: str, device: str,
                 clock: Callable[[], float] = time.monotonic):
        _diagnostic_identity(run_id, engine, device)
        directory = _batch_path(str(directory), directory=True)
        if directory != Path.cwd():
            raise ValueError("diagnostic_cwd_mismatch")
        self.path = directory / DIAGNOSTICS_NAME
        self.run_id, self.engine, self.device = run_id, engine, device
        self.clock = clock
        self.started = clock()
        if not _finite_number(self.started):
            raise ValueError("invalid_diagnostic_clock")
        self.sequence, self.size, self.elapsed = 0, 0, 0.0
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL
                          | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0), 0o600)
        try:
            info = os.fstat(self.fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError("invalid_diagnostic_file")
            self.identity = (info.st_dev, info.st_ino)
        except BaseException:
            self.close()
            raise

    def emit(self, phase, event, *, part_index=None, torch_module=None):
        if self.fd is None or self.sequence >= MAX_DIAGNOSTICS_EVENTS:
            raise ValueError("diagnostic_event_limit")
        now = self.clock()
        if not _finite_number(now):
            raise ValueError("invalid_diagnostic_clock")
        resources = {}
        if self.device == "cuda:0" and torch_module is not None:
            # Never import Torch, query names, initialize CUDA or synchronize here.
            try:
                cuda = torch_module.cuda
                if cuda.is_initialized():
                    resources = {
                        "cuda_allocated_bytes": cuda.memory_allocated(0),
                        "cuda_reserved_bytes": cuda.memory_reserved(0),
                        "cuda_peak_allocated_bytes": cuda.max_memory_allocated(0),
                    }
            except Exception:
                resources = {}
        value = _diagnostic_event({
            "schema_version": DIAGNOSTICS_VERSION, "sequence": self.sequence,
            "run_id": self.run_id, "engine": self.engine, "device": self.device,
            "phase": phase, "event": event, "elapsed_seconds": now - self.started,
            "part_index": part_index, "resources": resources,
        }, run_id=self.run_id, engine=self.engine, device=self.device,
            sequence=self.sequence, previous_elapsed=self.elapsed)
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False,
                         separators=(",", ":")).encode("ascii") + b"\n"
        if self.size + len(raw) > MAX_DIAGNOSTICS_BYTES:
            raise ValueError("diagnostic_byte_limit")
        _batch_path(str(self.path), directory=False)
        info = self.path.lstat()
        if ((info.st_dev, info.st_ino) != self.identity or info.st_size != self.size
                or os.fstat(self.fd).st_nlink != 1):
            raise ValueError("diagnostic_file_changed")
        # Unbuffered writes leave completed phase records available after a kill.
        offset = 0
        while offset < len(raw):
            count = os.write(self.fd, raw[offset:])
            if count <= 0:
                raise OSError("diagnostic_write_failed")
            offset += count
        self.sequence += 1
        self.size += len(raw)
        self.elapsed = value["elapsed_seconds"]

    def close(self):
        descriptor, self.fd = getattr(self, "fd", None), None
        if descriptor is not None:
            os.close(descriptor)


def read_voice_diagnostics(directory: Path, *, run_id: str, engine: str, device: str,
                           part_count: int | None = None):
    """Strict offline inspection; callers select a private run, never a model path."""
    _diagnostic_identity(run_id, engine, device)
    if part_count is not None and (type(part_count) is not int or not 1 <= part_count <= 16):
        raise ValueError("invalid_diagnostic_part_count")
    directory = _batch_path(str(directory), directory=True)
    path = _batch_path(str(directory / DIAGNOSTICS_NAME), directory=False)
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        raw = handle.read(MAX_DIAGNOSTICS_BYTES + 1)
        after = path.lstat()
        if ((before.st_dev, before.st_ino) != (after.st_dev, after.st_ino)
                or not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
                or (getattr(before, "st_file_attributes", 0)
                    | getattr(after, "st_file_attributes", 0)) & 0x400):
            raise ValueError("diagnostic_file_changed")
    if (not 1 <= len(raw) <= MAX_DIAGNOSTICS_BYTES or not raw.endswith(b"\n")
            or raw.startswith(b"\xef\xbb\xbf")):
        raise ValueError("invalid_diagnostic_bytes")
    lines = raw.splitlines()
    if not 1 <= len(lines) <= MAX_DIAGNOSTICS_EVENTS:
        raise ValueError("diagnostic_event_limit")
    result, elapsed = [], 0.0
    pending, next_phase, next_part, terminal = None, "imports", 0, False
    conditioned = False
    for sequence, line in enumerate(lines):
        value = json.loads(line.decode("ascii", errors="strict"),
                           object_pairs_hook=_unique_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               ValueError("invalid_diagnostic_number")))
        value = _diagnostic_event(value, run_id=run_id, engine=engine, device=device,
                                  sequence=sequence, previous_elapsed=elapsed)
        phase, event, part = value["phase"], value["event"], value["part_index"]
        if terminal:
            raise ValueError("diagnostic_after_completion")
        if phase == "completion":
            if event == "completed" and (pending is not None or next_phase != "generate"
                                          or next_part < 1
                                          or (part_count is not None and next_part != part_count)):
                raise ValueError("invalid_diagnostic_completion")
            terminal = True
        elif pending is None:
            expected_part = next_part if phase in {"generate", "save"} else None
            conditioning = (phase == "reference_conditioning" and next_phase == "generate"
                            and next_part == 0 and not conditioned)
            if (event != "started" or (phase != next_phase and not conditioning)
                    or part != expected_part
                    or (part is not None and part_count is not None and part >= part_count)):
                raise ValueError("invalid_diagnostic_part_binding")
            pending = (phase, part)
        elif event != "completed" or pending != (phase, part):
            raise ValueError("invalid_diagnostic_phase_pair")
        else:
            pending = None
            next_phase = {"imports": "model_load", "model_load": "generate",
                          "reference_conditioning": "generate",
                          "generate": "save", "save": "generate"}[phase]
            if phase == "reference_conditioning":
                conditioned = True
            if phase == "save":
                next_part += 1
        elapsed = value["elapsed_seconds"]
        result.append(value)
    return tuple(result)


def _record(diagnostics, phase, event, *, part_index=None, torch_module=None):
    if diagnostics is not None:
        try:
            diagnostics.emit(phase, event, part_index=part_index, torch_module=torch_module)
        except Exception:
            # Metadata failure cannot authorize a WAV, reset time or retry the SDK.
            with contextlib.suppress(Exception):
                diagnostics.close()


def _batch_path(value: object, *, directory: bool) -> Path:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= 4096
        or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValueError("invalid_local_paths")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("absolute_path_required")
    for component in (path, *path.parents):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("redirected_path_denied")
    info = path.stat()
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("directory_required")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("regular_single_link_file_required")
    return path


def _validate_batch(request: dict) -> dict:
    """Bound the untrusted wire before importing any model or numeric SDK."""
    required = {
        "batch_version",
        "authorized",
        "run_id",
        "engine",
        "device",
        "text",
        "chunks",
        "reference_path",
        "model_dir",
        "output_dir",
    }
    optional = {
        "sdk_source_dir",
        "voice_profile",
        "reference_transcript",
        "transcript_confirmed",
        "seed",
        "reuse_voice_prompt",
    }
    if not isinstance(request, dict) or not required <= request.keys() <= required | optional:
        raise ValueError("invalid_batch_fields")
    if request["batch_version"] != BATCH_VERSION or request["authorized"] is not True:
        raise ValueError("authorization_or_version_required")
    if (
        request["engine"] not in {"qwen3_tts", "chatterbox_pt_br"}
        or request["device"] not in {"cpu", "cuda:0"}
        or not isinstance(request["run_id"], str)
        or re.fullmatch(r"[a-f0-9]{32}", request["run_id"]) is None
    ):
        raise ValueError("invalid_batch_identity")
    reuse_prompt = request.get("reuse_voice_prompt", False)
    if type(reuse_prompt) is not bool:
        raise ValueError("invalid_voice_prompt_reuse_flag")
    if reuse_prompt and request["engine"] != "qwen3_tts":
        raise ValueError("voice_prompt_reuse_requires_qwen")
    text, chunks = request["text"], request["chunks"]
    if (
        not isinstance(text, str)
        or not 1 <= len(text) <= 6000
        or not text.strip()
        or any(
            unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in "\r\n\t"
            for char in text
        )
        or not isinstance(chunks, list)
        or not 1 <= len(chunks) <= 16
        or any(
            not isinstance(chunk, str) or not 1 <= len(chunk) <= 600 or not chunk.strip()
            for chunk in chunks
        )
        or "".join(chunks) != text
    ):
        raise ValueError("invalid_batch_text")
    seed = request.get("seed")
    if seed is not None and (type(seed) is not int or not 0 <= seed <= 2**32 - 1):
        raise ValueError("invalid_seed")
    profile = request.get("voice_profile", "baseline")
    transcript = request.get("reference_transcript")
    confirmed = request.get("transcript_confirmed", False)
    if type(confirmed) is not bool:
        raise ValueError("invalid_transcript_confirmation")
    if profile in {"qwen_icl", "qwen_icl_draft"}:
        if (
            request["engine"] != "qwen3_tts"
            or confirmed is not (profile == "qwen_icl")
            or not isinstance(transcript, str)
            or not 1 <= len(transcript) <= 2000
            or not transcript.strip()
            or any(
                unicodedata.category(char) in {"Cc", "Cf", "Cs"} and char not in "\r\n\t"
                for char in transcript
            )
        ):
            raise ValueError("invalid_reference_transcript")
    elif profile not in {"baseline", "chatterbox_conversational"} or (
        profile == "chatterbox_conversational" and request["engine"] != "chatterbox_pt_br"
    ):
        raise ValueError("profile_engine_mismatch")
    elif transcript is not None or confirmed:
        raise ValueError("unused_reference_transcript")
    raw = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_BATCH_BYTES:
        raise ValueError("batch_payload_too_large")
    # Hashes describe the exact text, not a normalized or substituted version.
    metadata = {
        "batch_version": BATCH_VERSION,
        "part_count": len(chunks),
        "completed_parts": 0,
        "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "part_text_sha256": [hashlib.sha256(part.encode("utf-8")).hexdigest() for part in chunks],
    }
    _batch_path(request["model_dir"], directory=True)
    _batch_path(request["reference_path"], directory=False)
    output_dir = _batch_path(request["output_dir"], directory=True)
    if request.get("sdk_source_dir") is not None:
        _batch_path(request["sdk_source_dir"], directory=True)
    for index in range(len(chunks)):
        output = output_dir / f"part-{index:04d}.wav"
        if output.exists() or output.is_symlink():
            raise ValueError("output_already_exists")
    return metadata


def _deny_network() -> None:
    class OfflineSocket(socket.socket):
        def __new__(cls, *args, **kwargs):
            raise OSError("offline_voice_worker")

    def denied(*args, **kwargs):
        raise OSError("offline_voice_worker")

    socket.socket = OfflineSocket
    socket.create_connection = denied
    socket.getaddrinfo = denied


def _generate(request: dict, state: dict | None = None) -> None:
    if state is None:
        state = {}
    state["failure_stage"] = "import"
    import numpy as np
    import soundfile as sf
    import torch

    if request.get("seed") is not None:
        import random

        seed = request["seed"]
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise ValueError("invalid_seed")
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    model_dir = Path(request["model_dir"])
    reference = Path(request["reference_path"])
    output = Path(request["output_path"])
    if not model_dir.is_dir() or not reference.is_file() or output.exists():
        raise ValueError("invalid_local_paths")
    device = request["device"]
    if request["engine"] == "qwen3_tts":
        from qwen_tts import Qwen3TTSModel

        state["failure_stage"] = "model_load"
        model = Qwen3TTSModel.from_pretrained(
            str(model_dir),
            device_map=device,
            dtype=torch.float32 if device == "cpu" else torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
            trust_remote_code=False,
        )
        state["failure_stage"] = "generate"
        profile = request.get("voice_profile", "baseline")
        clone_options = {}
        if profile in {"qwen_icl", "qwen_icl_draft"}:
            transcript = request.get("reference_transcript")
            if (
                request.get("transcript_confirmed") is not (profile == "qwen_icl")
                or not isinstance(transcript, str)
                or not transcript.strip()
                or len(transcript) > 2000
            ):
                raise ValueError(
                    "confirmed_reference_transcript_required"
                    if profile == "qwen_icl"
                    else "unconfirmed_draft_transcript_required"
                )
            clone_options["ref_text"] = transcript
        elif profile != "baseline":
            raise ValueError("profile_engine_mismatch")
        wavs, rate = model.generate_voice_clone(
            text=request["text"],
            language="Portuguese",
            ref_audio=str(reference),
            x_vector_only_mode=profile not in {"qwen_icl", "qwen_icl_draft"},
            max_new_tokens=1024,
            **clone_options,
        )
        audio = wavs[0]
    elif request["engine"] == "chatterbox_pt_br":
        if not request.get("sdk_source_dir"):
            raise NotImplementedError("sdk_incompatible")
        source = Path(request["sdk_source_dir"])
        if not (source / "chatterbox" / "src" / "chatterbox" / "tts.py").is_file():
            raise NotImplementedError("sdk_incompatible")
        sys.path.insert(0, str(source))
        from chatterbox.src.chatterbox.tts import ChatterboxTTS

        parameters = inspect.signature(ChatterboxTTS.from_local).parameters
        if not {"t3_filename", "s3gen_filename"} <= parameters.keys():
            raise NotImplementedError("sdk_incompatible")
        state["failure_stage"] = "model_load"
        model = ChatterboxTTS.from_local(
            model_dir,
            device=device,
            t3_filename="t3_pt_br.safetensors",
            s3gen_filename="s3gen_v3.pt",
        )
        # Standard generation applies the SDK watermark; do not remove/replace it.
        state["failure_stage"] = "generate"
        profile = request.get("voice_profile", "baseline")
        generation_options = {}
        if profile == "chatterbox_conversational":
            generation_options = {"exaggeration": 0.35, "cfg_weight": 0.3, "temperature": 0.75}
        elif profile != "baseline":
            raise ValueError("profile_engine_mismatch")
        audio = (
            model.generate(
                request["text"],
                language_id="pt",
                audio_prompt_path=str(reference),
                **generation_options,
            )
            .detach()
            .cpu()
            .numpy()
        )
        if audio.ndim == 2 and audio.shape[0] == 1:
            audio = audio[0]
        rate = model.sr
    else:
        raise ValueError("unsupported_engine")
    state["failure_stage"] = "save"
    audio = np.asarray(audio)
    if (
        audio.ndim != 1
        or not isinstance(rate, int)
        or not 8000 <= rate <= 96000
        or not 0 < len(audio) <= rate * 120
        or not np.isfinite(audio).all()
        or not np.any(audio != 0)
    ):
        raise ValueError("invalid_generated_audio")
    with output.open("xb") as handle:
        os.chmod(output, 0o600)
        sf.write(handle, np.clip(audio, -1, 1), rate, format="WAV", subtype="PCM_16")


def _generate_batch(request: dict, state: dict | None = None, *, diagnostics=None) -> None:
    """Load a single local model; generate each exact part once, in sequence.

    The parent owns one campaign deadline and process cancellation. Completed
    parts are diagnostic only: this worker never publishes aggregate success.
    """
    if state is None:
        state = {}
    state["failure_stage"] = "validate"
    state.update(_validate_batch(request))
    state["failure_stage"] = "import"
    _record(diagnostics, "imports", "started")
    import numpy as np
    import soundfile as sf
    import torch

    if request.get("seed") is not None:
        import random

        seed = request["seed"]
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)

    model_dir = Path(request["model_dir"])
    reference = Path(request["reference_path"])
    device = request["device"]
    profile = request.get("voice_profile", "baseline")
    if request["engine"] == "qwen3_tts":
        from qwen_tts import Qwen3TTSModel

        _record(diagnostics, "imports", "completed", torch_module=torch)
        state["failure_stage"] = "model_load"
        _record(diagnostics, "model_load", "started", torch_module=torch)
        model = Qwen3TTSModel.from_pretrained(
            str(model_dir),
            device_map=device,
            dtype=torch.float32 if device == "cpu" else torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
            trust_remote_code=False,
        )
        _record(diagnostics, "model_load", "completed", torch_module=torch)
        options = {"ref_text": request["reference_transcript"]} if profile != "baseline" else {}
        reuse_prompt = request.get("reuse_voice_prompt", False)
        prompt = None
        if reuse_prompt:
            state["failure_stage"] = "generate"
            try:
                create_prompt = model.create_voice_clone_prompt
                generate_clone = model.generate_voice_clone
                if (not callable(create_prompt) or not callable(generate_clone)
                        or not {"ref_audio", "ref_text", "x_vector_only_mode"}
                        <= inspect.signature(create_prompt).parameters.keys()
                        or "voice_clone_prompt"
                        not in inspect.signature(generate_clone).parameters):
                    raise NotImplementedError("sdk_incompatible")
                inspect.signature(create_prompt).bind(
                    ref_audio=str(reference), x_vector_only_mode=profile == "baseline", **options)
                inspect.signature(generate_clone).bind(
                    text=request["chunks"][0], language="Portuguese", voice_clone_prompt=[],
                    max_new_tokens=1024)
            except (AttributeError, TypeError, ValueError):
                raise NotImplementedError("sdk_incompatible") from None
            _record(diagnostics, "reference_conditioning", "started", torch_module=torch)
            prompt = create_prompt(ref_audio=str(reference),
                                   x_vector_only_mode=profile == "baseline", **options)
            if not isinstance(prompt, list) or len(prompt) != 1:
                raise NotImplementedError("sdk_incompatible")
            _record(diagnostics, "reference_conditioning", "completed", torch_module=torch)

        def generate(text):
            if reuse_prompt:
                wavs, rate = model.generate_voice_clone(
                    text=text, language="Portuguese", voice_clone_prompt=prompt,
                    max_new_tokens=1024,
                )
            else:
                wavs, rate = model.generate_voice_clone(
                    text=text,
                    language="Portuguese",
                    ref_audio=str(reference),
                    x_vector_only_mode=profile == "baseline",
                    max_new_tokens=1024,
                    **options,
                )
            if not isinstance(wavs, (list, tuple)) or len(wavs) != 1:
                raise ValueError("invalid_generated_audio")
            return wavs[0], rate

    else:
        if not request.get("sdk_source_dir"):
            raise NotImplementedError("sdk_incompatible")
        source = Path(request["sdk_source_dir"])
        if not (source / "chatterbox" / "src" / "chatterbox" / "tts.py").is_file():
            raise NotImplementedError("sdk_incompatible")
        _batch_path(str(source / "chatterbox" / "src" / "chatterbox" / "tts.py"), directory=False)
        sys.path.insert(0, str(source))
        from chatterbox.src.chatterbox.tts import ChatterboxTTS

        parameters = inspect.signature(ChatterboxTTS.from_local).parameters
        if not {"t3_filename", "s3gen_filename"} <= parameters.keys():
            raise NotImplementedError("sdk_incompatible")
        _record(diagnostics, "imports", "completed", torch_module=torch)
        state["failure_stage"] = "model_load"
        _record(diagnostics, "model_load", "started", torch_module=torch)
        model = ChatterboxTTS.from_local(
            model_dir,
            device=device,
            t3_filename="t3_pt_br.safetensors",
            s3gen_filename="s3gen_v3.pt",
        )
        _record(diagnostics, "model_load", "completed", torch_module=torch)
        options = (
            {"exaggeration": 0.35, "cfg_weight": 0.3, "temperature": 0.75}
            if profile == "chatterbox_conversational"
            else {}
        )

        def generate(text):
            # Use the standard SDK path, including its watermark, for every part.
            audio = (
                model.generate(text, language_id="pt", audio_prompt_path=str(reference), **options)
                .detach()
                .cpu()
                .numpy()
            )
            if audio.ndim == 2 and audio.shape[0] == 1:
                audio = audio[0]
            return audio, model.sr

    output_dir = Path(request["output_dir"])
    for index, text in enumerate(request["chunks"]):
        state["failure_stage"] = "generate"
        # Legacy calls still condition internally; reuse is explicit and batch-local.
        _record(diagnostics, "generate", "started", part_index=index, torch_module=torch)
        audio, rate = generate(text)
        _record(diagnostics, "generate", "completed", part_index=index, torch_module=torch)
        state["failure_stage"] = "save"
        _record(diagnostics, "save", "started", part_index=index, torch_module=torch)
        audio = np.asarray(audio)
        if (
            audio.ndim != 1
            or type(rate) is not int
            or not 8000 <= rate <= 96000
            or not 0 < len(audio) <= rate * 120
            or not np.isfinite(audio).all()
            or not np.any(audio != 0)
        ):
            raise ValueError("invalid_generated_audio")
        # Exclusive creation never replaces existing outputs, including races.
        output = output_dir / f"part-{index:04d}.wav"
        with output.open("xb") as handle:
            os.chmod(output, 0o600)
            sf.write(handle, np.clip(audio, -1, 1), rate, format="WAV", subtype="PCM_16")
        state["completed_parts"] = index + 1
        _record(diagnostics, "save", "completed", part_index=index, torch_module=torch)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_batch_field")
        result[key] = value
    return result


def main(*, diagnostics: bool = False) -> int:
    try:
        if type(diagnostics) is not bool:
            return 2
        raw = sys.stdin.buffer.read(MAX_BATCH_BYTES + 1)
        if len(raw) > MAX_BATCH_BYTES:
            return 2
        request = json.loads(raw)
        batch = isinstance(request, dict) and "batch_version" in request
        if batch:
            request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
            _validate_batch(request)
        elif len(raw) > 16384 or "reuse_voice_prompt" in request:
            return 2
        if (
            request.get("authorized") is not True
            or request.get("engine") not in {"qwen3_tts", "chatterbox_pt_br"}
            or request.get("device") not in {"cpu", "cuda:0"}
        ):
            return 2
        observer = None
        if diagnostics:
            if not batch:
                return 2
            observer = VoiceDiagnostics(Path(request["output_dir"]), run_id=request["run_id"],
                                        engine=request["engine"], device=request["device"])
    except Exception:
        return 2
    result = {"run_id": request.get("run_id"), "engine": request.get("engine")}
    _deny_network()
    state = {}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if batch:
                _generate_batch(request, state, diagnostics=observer)
            else:
                _generate(request, state)
        result.update(status="completed")
    except Exception as error:
        reason = (
            "sdk_unavailable"
            if isinstance(error, ImportError)
            else "sdk_incompatible"
            if isinstance(error, NotImplementedError)
            else "local_inference_failed"
        )
        kind = type(error).__name__
        if kind not in {
            "ImportError",
            "ModuleNotFoundError",
            "NotImplementedError",
            "ValueError",
            "TypeError",
            "RuntimeError",
            "OSError",
            "FileNotFoundError",
            "AttributeError",
            "KeyError",
            "AssertionError",
        }:
            kind = "SdkError"
        result.update(
            status="failed",
            reason=reason,
            failure_stage=state.get("failure_stage"),
            error_type=kind,
        )
    finally:
        _record(observer, "completion", "completed" if result.get("status") == "completed"
                else "failed")
        if observer is not None:
            with contextlib.suppress(Exception):
                observer.close()
    if batch:
        result.update(
            batch_version=BATCH_VERSION,
            **{
                key: state.get(key)
                for key in ("part_count", "completed_parts", "text_sha256", "part_text_sha256")
            },
        )
        if len(json.dumps(result).encode("utf-8")) > 4096:
            return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["--diagnostics"]):
        raise SystemExit(2)
    raise SystemExit(main(diagnostics=sys.argv[1:] == ["--diagnostics"]))
