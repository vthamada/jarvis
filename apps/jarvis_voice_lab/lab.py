"""Read-only source audio and bounded, isolated SDK subprocess composition."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import struct
import subprocess
import tempfile
import time
import uuid
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .quality import validate_quality_options

ENGINES = frozenset({"chatterbox_pt_br", "qwen3_tts"})
MAX_SOURCE_BYTES = 128 * 1024 * 1024
MAX_OUTPUT_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class LabResult:
    status: str
    reason: str
    run_id: str
    engine: str
    evidence_mode: str
    output_path: str | None = None
    sample_rate: int | None = None
    duration_seconds: float | None = None
    output_digest: str | None = None
    failure_stage: str | None = None
    error_type: str | None = None
    voice_profile: str = "baseline"
    reference_transcript_reviewed: bool | None = None

    def metadata(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("output_path")
        result["artifact_available"] = self.output_path is not None
        if self.voice_profile == "qwen_icl_draft":
            result["review_required"] = True
        return result


def _plain_path(path: Path, *, directory: bool = False) -> Path:
    path = path.absolute()
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
    return Path(os.path.abspath(path))


def _wav_metadata(path: Path, *, source: bool) -> tuple[int, int, int]:
    _plain_path(path)
    limit = MAX_SOURCE_BYTES if source else MAX_OUTPUT_BYTES
    if not 44 <= path.stat().st_size <= limit:
        raise ValueError("wav_size_out_of_bounds")
    with wave.open(str(path), "rb") as audio:
        rate, frames, channels = audio.getframerate(), audio.getnframes(), audio.getnchannels()
        if (
            audio.getsampwidth() != 2
            or audio.getcomptype() != "NONE"
            or channels not in (1, 2)
            or not 8000 <= rate <= 96000
        ):
            raise ValueError("unsupported_wav_format")
        if not 0 < frames / rate <= (900 if source else 120):
            raise ValueError("wav_duration_out_of_bounds")
        if 44 + frames * channels * 2 > path.stat().st_size:
            raise ValueError("truncated_wav")
        remaining = frames
        has_signal = False
        while remaining:
            count = min(16384, remaining)
            raw = audio.readframes(count)
            if len(raw) != count * channels * 2:
                raise ValueError("truncated_wav")
            has_signal = has_signal or any(raw)
            remaining -= count
        if not has_signal:
            raise ValueError("silent_reference" if source else "silent_output")
        return rate, frames, channels


def _local_tree(directory: Path) -> None:
    """Reject redirected descendant weights/modules; bounded metadata inspection only."""
    count = 0
    total = 0
    for path in directory.rglob("*"):
        count += 1
        if count > 6000:
            raise ValueError("local_tree_limit_exceeded")
        info = path.lstat()
        _plain_path(path, directory=stat.S_ISDIR(info.st_mode))
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
            if total > 32 * 1024**3:
                raise ValueError("local_tree_limit_exceeded")


def prepare_reference(
    source: Path,
    destination: Path,
    *,
    start_seconds: float = 0,
    duration_seconds: float = 10,
    exact_window: bool = False,
) -> tuple[int, float]:
    """Extract an explicit bounded window; original is never opened for writing."""
    rate, frames, channels = _wav_metadata(source, source=True)
    for value in (start_seconds, duration_seconds):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("invalid_reference_window")
    if not 0 <= start_seconds <= 900 or not 3 <= duration_seconds <= 15:
        raise ValueError("invalid_reference_window")
    start = int(start_seconds * rate)
    count = int(duration_seconds * rate)
    if start >= frames or (exact_window and start + count > frames):
        raise ValueError("reference_window_out_of_bounds")
    count = min(frames - start, count)
    with wave.open(str(source), "rb") as audio:
        audio.setpos(start)
        raw = audio.readframes(count)
    if len(raw) != count * channels * 2:
        raise ValueError("truncated_wav")
    if channels == 2:
        mono = bytearray()
        for left, right in struct.iter_unpack("<hh", raw):
            mono.extend(struct.pack("<h", (left + right) // 2))
        raw = bytes(mono)
    if not any(raw):
        raise ValueError("silent_reference")
    with destination.open("xb") as handle:
        os.chmod(destination, 0o600)
        with wave.open(handle, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            audio.writeframes(raw)
    return rate, count / rate


def worker_environment(python_executable: Path, run_directory: Path) -> dict[str, str]:
    """No inherited provider tokens, proxy, user config or tracing environment."""
    environment = {
        "PATH": str(python_executable.parent),
        "HOME": str(run_directory / "home"),
        "USERPROFILE": str(run_directory / "home"),
        "TEMP": str(run_directory / "tmp"),
        "TMP": str(run_directory / "tmp"),
        "HF_HOME": str(run_directory / "cache"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_IMPLICIT_TOKEN": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
        "NUMBA_NUM_THREADS": "2",
    }
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        environment["SystemRoot"] = system_root
        environment["WINDIR"] = system_root
        environment["PATH"] += os.pathsep + str(Path(system_root) / "System32")
    return environment


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.kill()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_voice_lab(
    *,
    engine: str,
    authorized: bool,
    reference_path: Path,
    text: str,
    model_dir: Path,
    python_executable: Path,
    workspace_root: Path,
    device: str = "cpu",
    timeout_seconds: float = 300,
    cancelled: Callable[[], bool] = lambda: False,
    evidence_mode: str = "model_real",
    fixture_worker: Callable | None = None,
    sdk_source_dir: Path | None = None,
    voice_profile: str = "baseline",
    reference_start_seconds: float = 0,
    reference_duration_seconds: float = 10,
    reference_transcript: str | None = None,
    transcript_confirmed: bool = False,
    seed: int | None = None,
) -> LabResult:
    """Never activated by normal voice/runtime paths. Explicit authorization required."""
    if authorized is not True:
        raise ValueError("authorization_required")
    if engine not in ENGINES or device not in {"cpu", "cuda:0"}:
        raise ValueError("invalid_engine_or_device")
    validate_quality_options(
        engine=engine,
        profile=voice_profile,
        reference_start_seconds=reference_start_seconds,
        reference_duration_seconds=reference_duration_seconds,
        reference_transcript=reference_transcript,
        transcript_confirmed=transcript_confirmed,
        seed=seed,
    )
    if (
        not isinstance(text, str)
        or not 1 <= len(text) <= 600
        or not text.strip()
        or any(ord(c) < 32 and c not in "\r\n\t" for c in text)
        or any(0xD800 <= ord(c) <= 0xDFFF for c in text)
    ):
        raise ValueError("invalid_text")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or not 0 < timeout_seconds <= 1800
    ):
        raise ValueError("invalid_timeout")
    if evidence_mode not in {"fixture", "model_real"}:
        raise ValueError("invalid_evidence_mode")
    if (fixture_worker is not None) != (evidence_mode == "fixture"):
        raise ValueError("fixture_mode_requires_explicit_worker")
    workspace_root = _plain_path(Path(workspace_root), directory=True)
    reference_path = _plain_path(Path(reference_path))
    model_dir = _plain_path(Path(model_dir), directory=True)
    _local_tree(model_dir)
    python_executable = _plain_path(Path(python_executable))
    if sdk_source_dir is not None:
        sdk_source_dir = _plain_path(Path(sdk_source_dir), directory=True)
        _plain_path(sdk_source_dir / "chatterbox" / "src" / "chatterbox" / "tts.py")
        _local_tree(sdk_source_dir)
    _wav_metadata(reference_path, source=True)
    base = _plain_path(Path(tempfile.gettempdir()), directory=True)
    if base == workspace_root or workspace_root in base.parents:
        raise ValueError("temporary_directory_inside_workspace_denied")
    run_id = uuid.uuid4().hex
    run_directory = Path(tempfile.mkdtemp(prefix=f"jarvis-voice-lab-{run_id}-", dir=base))
    _plain_path(run_directory, directory=True)
    for child in ("home", "tmp", "cache"):
        (run_directory / child).mkdir(mode=0o700)
    reference = run_directory / "reference.wav"
    output = run_directory / "sample.wav"
    prepare_reference(
        reference_path,
        reference,
        start_seconds=reference_start_seconds,
        duration_seconds=reference_duration_seconds,
        exact_window=voice_profile in {"qwen_icl", "qwen_icl_draft"},
    )
    request = {
        "engine": engine,
        "authorized": True,
        "run_id": run_id,
        "text": text,
        "reference_path": str(reference),
        "output_path": str(output),
        "model_dir": str(model_dir),
        "device": device,
        "sdk_source_dir": str(sdk_source_dir) if sdk_source_dir is not None else None,
        "voice_profile": voice_profile,
        "reference_transcript": reference_transcript,
        "transcript_confirmed": transcript_confirmed,
        "seed": seed,
    }

    def result(status: str, reason: str) -> LabResult:
        return LabResult(status, reason, run_id, engine, evidence_mode)

    if cancelled():
        return result("cancelled", "cancelled")
    started = time.monotonic()
    if fixture_worker is not None:
        try:
            response = fixture_worker(dict(request))
        except Exception:
            return result("failed", "fixture_worker_failed")
    else:
        command = [str(python_executable), "-I", str(Path(__file__).with_name("worker.py"))]
        metadata_file = run_directory / "worker-status.tmp"
        try:
            with metadata_file.open("xb") as spool:
                try:
                    process = subprocess.Popen(
                        command,
                        stdin=subprocess.PIPE,
                        stdout=spool,
                        stderr=subprocess.DEVNULL,
                        cwd=run_directory,
                        env=worker_environment(python_executable, run_directory),
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                except OSError:
                    return result("failed", "worker_start_failed")
                payload = json.dumps(request, ensure_ascii=True).encode("utf-8")
                first = True
                try:
                    while True:
                        if cancelled():
                            _stop(process)
                            return result("cancelled", "cancelled")
                        if metadata_file.stat().st_size > 4096:
                            _stop(process)
                            return result("failed", "invalid_worker_metadata")
                        remaining = timeout_seconds - (time.monotonic() - started)
                        if remaining <= 0:
                            _stop(process)
                            return result("timed_out", "deadline_exceeded")
                        try:
                            process.communicate(
                                input=payload if first else None,
                                timeout=min(0.2, remaining),
                            )
                            break
                        except subprocess.TimeoutExpired:
                            first = False
                except Exception:
                    _stop(process)
                    return result("failed", "worker_control_failed")
            if process.returncode != 0:
                return result("failed", "worker_failed")
            if metadata_file.stat().st_size > 4096:
                return result("failed", "invalid_worker_metadata")
            with metadata_file.open("rb") as handle:
                response = json.loads(handle.read(4097))
        except Exception:
            return result("failed", "worker_control_failed")
        finally:
            metadata_file.unlink(missing_ok=True)
    if cancelled():
        return result("cancelled", "cancelled")
    if time.monotonic() - started >= timeout_seconds:
        return result("timed_out", "deadline_exceeded")
    if (
        not isinstance(response, dict)
        or response.get("run_id") != run_id
        or response.get("engine") != engine
    ):
        return result("failed", "worker_binding_mismatch")
    if response.get("status") != "completed":
        reason = response.get("reason")
        if reason not in {"sdk_unavailable", "sdk_incompatible", "local_inference_failed"}:
            reason = "worker_failed"
        stage = response.get("failure_stage")
        error_type = response.get("error_type")
        if stage not in {"import", "model_load", "generate", "save"}:
            stage = None
        if error_type not in {
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
            "SdkError",
        }:
            error_type = None
        return LabResult(
            "failed",
            reason,
            run_id,
            engine,
            evidence_mode,
            failure_stage=stage,
            error_type=error_type,
        )
    try:
        rate, frames, channels = _wav_metadata(output, source=False)
        if channels != 1:
            raise ValueError("mono_required")
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
    except (OSError, ValueError, wave.Error):
        return result("failed", "invalid_audio_output")
    return LabResult(
        "completed",
        "local_sample_generated" if evidence_mode == "model_real" else "fixture_only",
        run_id,
        engine,
        evidence_mode,
        str(output),
        rate,
        frames / rate,
        digest,
        voice_profile=voice_profile,
        reference_transcript_reviewed=(
            transcript_confirmed if voice_profile in {"qwen_icl", "qwen_icl_draft"} else None
        ),
    )
