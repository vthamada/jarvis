"""One bounded offline SDK campaign; only its complete aggregate is returned."""

from __future__ import annotations

import hashlib
import json
import math
import os
import stat
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .batch_audio import assemble_wavs, inspect_wav, segment_text
from .lab import (
    ENGINES,
    LabResult,
    _local_tree,
    _plain_path,
    _stop,
    _wav_metadata,
    prepare_reference,
    worker_environment,
)
from .quality import validate_quality_options

BATCH_VERSION = "jarvis-voice-batch-v1"
MAX_REQUEST_BYTES = 131_072
MAX_METADATA_BYTES = 4096


@dataclass(frozen=True)
class BatchLabResult(LabResult):
    part_count: int = 0
    completed_parts: int = 0
    text_sha256: str | None = field(default=None, repr=False)
    part_text_sha256: tuple[str, ...] = field(default=(), repr=False)

    def metadata(self) -> dict[str, object]:
        value = super().metadata()
        value.pop("text_sha256", None)
        value.pop("part_text_sha256", None)
        value.pop("output_digest", None)
        value["batch_mode"] = True
        value["voice_quality_approved"] = False
        return value


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_worker_metadata")
        result[key] = value
    return result


def _metadata(raw: bytes) -> dict:
    if not 1 <= len(raw) <= MAX_METADATA_BYTES or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("invalid_worker_metadata")
    value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(
                           ValueError("invalid_worker_metadata")))
    if type(value) is not dict:
        raise ValueError("invalid_worker_metadata")
    return value


def _boundary(deadline, cancelled, clock):
    if cancelled():
        raise InterruptedError("cancelled")
    now = clock()
    if type(now) not in (int, float) or not math.isfinite(now) or now >= deadline:
        raise TimeoutError("deadline_exceeded")


def _remove_owned(path: Path | None, identity: tuple[int, int] | None) -> None:
    """No directory cleanup: remove only a regular artifact inode we created."""
    if path is None or identity is None:
        return
    try:
        info = path.lstat()
        if stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity:
            path.unlink()
    except OSError:
        pass


def run_voice_lab_batch(
    *, engine: str, authorized: bool, reference_path: Path, text: str,
    model_dir: Path, python_executable: Path, workspace_root: Path,
    device: str = "cpu", timeout_seconds: float = 300,
    cancelled: Callable[[], bool] = lambda: False, evidence_mode: str = "model_real",
    fixture_worker: Callable | None = None, sdk_source_dir: Path | None = None,
    voice_profile: str = "baseline", reference_start_seconds: float = 0,
    reference_duration_seconds: float = 10, reference_transcript: str | None = None,
    transcript_confirmed: bool = False, seed: int | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> BatchLabResult:
    """Explicit complement, not playback. No retries, remote SDK or partial result.

    The single deadline starts before file inspection and never resets by part.
    A synchronous fixture cannot be preempted; late returns are still refused.
    Real SDK processes are killed at the deadline by the supervising parent.
    """
    if authorized is not True:
        raise ValueError("authorization_required")
    if (type(engine) is not str or engine not in ENGINES
            or type(device) is not str or device not in {"cpu", "cuda:0"}):
        raise ValueError("invalid_engine_or_device")
    if (type(timeout_seconds) not in (int, float) or not 0 < timeout_seconds <= 1800
            or not math.isfinite(timeout_seconds) or not callable(cancelled)
            or not callable(clock)):
        raise ValueError("invalid_timeout_or_callback")
    if (type(evidence_mode) is not str or evidence_mode not in {"fixture", "model_real"}
            or (fixture_worker is not None) != (evidence_mode == "fixture")
            or (fixture_worker is not None and not callable(fixture_worker))):
        raise ValueError("fixture_mode_requires_explicit_worker")
    try:
        started = clock()
        if type(started) not in (int, float) or not math.isfinite(started):
            raise ValueError("invalid_clock")
        deadline = started + timeout_seconds
        if not math.isfinite(deadline):
            raise ValueError("invalid_clock")
    except Exception:
        raise ValueError("invalid_clock") from None
    chunks = segment_text(text)
    validate_quality_options(
        engine=engine, profile=voice_profile, reference_start_seconds=reference_start_seconds,
        reference_duration_seconds=reference_duration_seconds,
        reference_transcript=reference_transcript, transcript_confirmed=transcript_confirmed,
        seed=seed,
    )
    run_id = uuid.uuid4().hex
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    part_hashes = tuple(hashlib.sha256(part.encode("utf-8")).hexdigest() for part in chunks)

    def result(status: str, reason: str, *, completed_parts: int = 0, **fields):
        return BatchLabResult(
            status, reason, run_id, engine, evidence_mode, voice_profile=voice_profile,
            reference_transcript_reviewed=transcript_confirmed
            if voice_profile in {"qwen_icl", "qwen_icl_draft"} else None,
            part_count=len(chunks), completed_parts=completed_parts, **fields,
        )

    try:
        _boundary(deadline, cancelled, clock)
        workspace = _plain_path(Path(workspace_root), directory=True)
        source = _plain_path(Path(reference_path))
        model = _plain_path(Path(model_dir), directory=True)
        _local_tree(model)
        executable = _plain_path(Path(python_executable))
        sdk = None
        if sdk_source_dir is not None:
            if engine != "chatterbox_pt_br":
                raise ValueError("sdk_source_engine_mismatch")
            sdk = _plain_path(Path(sdk_source_dir), directory=True)
            _plain_path(sdk / "chatterbox" / "src" / "chatterbox" / "tts.py")
            _local_tree(sdk)
        _wav_metadata(source, source=True)
        base = _plain_path(Path(tempfile.gettempdir()), directory=True)
        if base == workspace or workspace in base.parents:
            raise ValueError("temporary_directory_inside_workspace_denied")
        _boundary(deadline, cancelled, clock)
    except InterruptedError:
        return result("cancelled", "cancelled")
    except TimeoutError:
        return result("timed_out", "deadline_exceeded")
    except Exception:
        raise ValueError("local_batch_preflight_refused") from None

    directory = Path(tempfile.mkdtemp(prefix=f"jarvis-voice-lab-{run_id}-", dir=base))
    try:
        _plain_path(directory, directory=True)
        for child in ("home", "tmp", "cache"):
            (directory / child).mkdir(mode=0o700)
        reference = directory / "reference.wav"
        prepare_reference(source, reference, start_seconds=reference_start_seconds,
                          duration_seconds=reference_duration_seconds,
                          exact_window=voice_profile in {"qwen_icl", "qwen_icl_draft"})
        _boundary(deadline, cancelled, clock)
    except InterruptedError:
        return result("cancelled", "cancelled")
    except TimeoutError:
        return result("timed_out", "deadline_exceeded")
    except Exception:
        return result("failed", "reference_preparation_failed")
    request = {
        "batch_version": BATCH_VERSION, "run_id": run_id, "engine": engine,
        "authorized": True, "text": text, "chunks": list(chunks), "output_dir": str(directory),
        "reference_path": str(reference), "model_dir": str(model), "device": device,
        "sdk_source_dir": str(sdk) if sdk is not None else None, "voice_profile": voice_profile,
        "reference_transcript": reference_transcript, "transcript_confirmed": transcript_confirmed,
        "seed": seed,
    }
    payload = json.dumps(request, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(payload) > MAX_REQUEST_BYTES:
        return result("failed", "batch_request_too_large")
    spool_path = directory / "worker-status.tmp"
    process = None
    staging = directory / ".batch-aggregate.wav"
    output = directory / "sample.wav"
    artifact_identity = None
    successful = False
    try:
        _boundary(deadline, cancelled, clock)
        if fixture_worker is not None:
            # Separate untrusted callback containers from our immutable plan.
            response = fixture_worker(json.loads(payload))
            encoded = json.dumps(response, ensure_ascii=True, allow_nan=False).encode("ascii")
            response = _metadata(encoded)
        else:
            with spool_path.open("xb") as spool:
                process = subprocess.Popen(
                    [str(executable), "-I", str(Path(__file__).with_name("worker.py"))],
                    stdin=subprocess.PIPE, stdout=spool, stderr=subprocess.DEVNULL,
                    cwd=directory, env=worker_environment(executable, directory),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                first = True
                while True:
                    _boundary(deadline, cancelled, clock)
                    if spool_path.stat().st_size > MAX_METADATA_BYTES:
                        raise ValueError("invalid_worker_metadata")
                    remaining = deadline - clock()
                    if remaining <= 0:
                        raise TimeoutError("deadline_exceeded")
                    try:
                        process.communicate(input=payload if first else None,
                                            timeout=min(0.2, remaining))
                        break
                    except subprocess.TimeoutExpired:
                        first = False
            if (type(process.returncode) is not int or process.returncode != 0
                    or process.poll() != 0):
                return result("failed", "worker_failed")
            _plain_path(spool_path)
            with spool_path.open("rb") as handle:
                response = _metadata(handle.read(MAX_METADATA_BYTES + 1))
        _boundary(deadline, cancelled, clock)
        if (response.get("batch_version") != BATCH_VERSION or response.get("run_id") != run_id
                or response.get("engine") != engine):
            return result("failed", "worker_binding_mismatch")
        if response.get("status") != "completed":
            reason = response.get("reason")
            if type(reason) is not str or reason not in {
                "sdk_unavailable", "sdk_incompatible", "local_inference_failed",
            }:
                reason = "worker_failed"
            progress = response.get("completed_parts", 0)
            if type(progress) is not int or not 0 <= progress < len(chunks):
                progress = 0
            return result("failed", reason, completed_parts=progress)
        if (set(response) != {"batch_version", "run_id", "engine", "status", "part_count",
                              "completed_parts", "text_sha256", "part_text_sha256"}
                or type(response["part_count"]) is not int
                or type(response["completed_parts"]) is not int
                or response["part_count"] != len(chunks)
                or response["completed_parts"] != len(chunks)
                or response["text_sha256"] != text_hash
                or type(response["part_text_sha256"]) is not list
                or tuple(response["part_text_sha256"]) != part_hashes):
            return result("failed", "batch_manifest_refused")
        parts = tuple(directory / f"part-{index:04d}.wav" for index in range(len(chunks)))
        rate, frames, channels = assemble_wavs(
            parts, staging, deadline=deadline, cancelled=cancelled, clock=clock,
        )
        info = staging.lstat()
        artifact_identity = (info.st_dev, info.st_ino)
        _boundary(deadline, cancelled, clock)
        if channels != 1 or inspect_wav(staging) != (rate, frames, channels):
            raise ValueError("invalid_aggregate_audio")
        digest = hashlib.sha256(staging.read_bytes()).hexdigest()
        _boundary(deadline, cancelled, clock)
        os.link(staging, output)
        _remove_owned(staging, artifact_identity)
        _plain_path(output)  # Final inode must again be a regular single-link file.
        _boundary(deadline, cancelled, clock)
        completed = result(
            "completed", "fixture_only" if evidence_mode == "fixture" else "local_sample_generated",
            completed_parts=len(chunks), output_path=str(output), sample_rate=rate,
            duration_seconds=frames / rate, output_digest=digest,
            text_sha256=text_hash, part_text_sha256=part_hashes,
        )
        successful = True
        return completed
    except InterruptedError:
        return result("cancelled", "cancelled")
    except TimeoutError:
        return result("timed_out", "deadline_exceeded")
    except Exception:
        return result("failed", "local_batch_generation_failed")
    finally:
        candidate_success = successful
        termination_unconfirmed = False
        try:
            termination_unconfirmed = process is not None and process.poll() is None
        except Exception:
            termination_unconfirmed = process is not None
        if termination_unconfirmed:
            successful = False
            try:
                _stop(process)
            except Exception:
                # Preserve the sanitized failure. Never report an unconfirmed
                # child termination as success; success requires exit code0 above.
                successful = False
        if not successful:
            _remove_owned(output, artifact_identity)
        _remove_owned(staging, artifact_identity)
        # Only our own bounded status spool; audio/reference stay private lab artifacts.
        try:
            spool_path.unlink(missing_ok=True)
        except OSError:
            pass
        if termination_unconfirmed and candidate_success:
            # A computed success is invalid if its child is still unconfirmed.
            # Preserve existing failure/cancellation results in every other case.
            return result("failed", "worker_termination_unconfirmed")
        if successful:
            # Termination checks and private-spool cleanup cannot reset the
            # campaign deadline or bypass a cancellation before handoff.
            try:
                _boundary(deadline, cancelled, clock)
            except Exception as error:
                _remove_owned(output, artifact_identity)
                if isinstance(error, InterruptedError):
                    return result("cancelled", "cancelled")
                if isinstance(error, TimeoutError):
                    return result("timed_out", "deadline_exceeded")
                return result("failed", "local_batch_generation_failed")
