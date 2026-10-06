"""Standalone subprocess entrypoint; heavyweight SDK imports never reach the Core."""

from __future__ import annotations

import contextlib
import hashlib
import inspect
import json
import os
import re
import socket
import stat
import sys
import unicodedata
from pathlib import Path

BATCH_VERSION = "jarvis-voice-batch-v1"
MAX_BATCH_BYTES = 131072


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


def _generate_batch(request: dict, state: dict | None = None) -> None:
    """Load a single local model; generate each exact part once, in sequence.

    The parent owns one campaign deadline and process cancellation. Completed
    parts are diagnostic only: this worker never publishes aggregate success.
    """
    if state is None:
        state = {}
    state["failure_stage"] = "validate"
    state.update(_validate_batch(request))
    state["failure_stage"] = "import"
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

        state["failure_stage"] = "model_load"
        model = Qwen3TTSModel.from_pretrained(
            str(model_dir),
            device_map=device,
            dtype=torch.float32 if device == "cpu" else torch.bfloat16,
            attn_implementation="sdpa",
            local_files_only=True,
            trust_remote_code=False,
        )
        options = {"ref_text": request["reference_transcript"]} if profile != "baseline" else {}

        def generate(text):
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
        state["failure_stage"] = "model_load"
        model = ChatterboxTTS.from_local(
            model_dir,
            device=device,
            t3_filename="t3_pt_br.safetensors",
            s3gen_filename="s3gen_v3.pt",
        )
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
        audio, rate = generate(text)
        state["failure_stage"] = "save"
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


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_batch_field")
        result[key] = value
    return result


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_BATCH_BYTES + 1)
        if len(raw) > MAX_BATCH_BYTES:
            return 2
        request = json.loads(raw)
        batch = isinstance(request, dict) and "batch_version" in request
        if batch:
            request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
            _validate_batch(request)
        elif len(raw) > 16384:
            return 2
        if (
            request.get("authorized") is not True
            or request.get("engine") not in {"qwen3_tts", "chatterbox_pt_br"}
            or request.get("device") not in {"cpu", "cuda:0"}
        ):
            return 2
    except Exception:
        return 2
    result = {"run_id": request.get("run_id"), "engine": request.get("engine")}
    _deny_network()
    state = {}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if batch:
                _generate_batch(request, state)
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
    raise SystemExit(main())
