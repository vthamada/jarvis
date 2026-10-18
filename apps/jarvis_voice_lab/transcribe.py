"""Opt-in local ASR: private original WAV -> unconfirmed transcript, never Core input."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from uuid import uuid4

from .asr_worker import DECODING_BEAMS, validate_decoding_profile
from .lab import _local_tree, _plain_path, _stop, _wav_metadata, worker_environment
from .worker_lifecycle import (
    OwnedWorkerSupervisor,
    WorkerExitUnconfirmed,
    expected_worker_image,
    new_binding,
)

MAX_TRANSCRIPT_BYTES = 256 * 1024


def transcribe_local_wav(
    *, authorized, source, model_dir, python_executable, device="cuda:0", timeout_seconds=900,
    cancelled=lambda: False, private_output_root=None,
    decoding_profile="quality", confirm_worker_exit=False,
):
    if authorized is not True:
        raise ValueError("authorization_required")
    validate_decoding_profile(decoding_profile)
    if type(confirm_worker_exit) is not bool:
        raise ValueError("invalid_local_asr_lifecycle_option")
    if device not in {"cpu", "cuda:0"} or type(timeout_seconds) not in (int, float):
        raise ValueError("invalid_local_asr_request")
    if not 0 < timeout_seconds <= 1800 or not callable(cancelled):
        raise ValueError("invalid_local_asr_request")
    source = _plain_path(Path(source))
    rate, frames, _ = _wav_metadata(source, source=True)
    model_dir = _plain_path(Path(model_dir), directory=True)
    _local_tree(model_dir)
    python_executable = _plain_path(Path(python_executable))
    selected_base = (Path(tempfile.gettempdir()) if private_output_root is None
                     else private_output_root)
    if not isinstance(selected_base, Path) or not selected_base.is_absolute():
        raise ValueError("invalid_private_output_root")
    base = _plain_path(selected_base, directory=True)
    workspace = Path(__file__).resolve().parents[2]
    if base == workspace or workspace in base.parents:
        raise ValueError("temporary_directory_inside_workspace_denied")
    if cancelled():
        raise InterruptedError("local_asr_cancelled")
    run_id = uuid4().hex
    runtime = Path(tempfile.mkdtemp(prefix=f"jarvis-voice-transcript-{run_id}-", dir=base))
    for name in ("home", "tmp", "cache"):
        (runtime / name).mkdir(mode=0o700)
    request = dict(
        authorized=True,
        run_id=run_id,
        source=str(source),
        model_dir=str(model_dir),
        device=device,
        output_directory=str(runtime),
        duration_seconds=frames / rate,
    )
    if decoding_profile != "quality":
        request["decoding_profile"] = decoding_profile
    lifecycle_enabled = confirm_worker_exit and sys.platform == "win32"
    if lifecycle_enabled:
        image = expected_worker_image(python_executable)
        request["worker_lifecycle"] = new_binding(run_id)
    status_path = runtime / "worker-status.tmp"
    start = time.monotonic()
    with status_path.open("xb") as status:
        process = subprocess.Popen(
            [str(python_executable), "-I", str(Path(__file__).with_name("asr_worker.py"))],
            cwd=runtime,
            stdin=subprocess.PIPE,
            stdout=status,
            stderr=subprocess.DEVNULL,
            env=worker_environment(python_executable, runtime),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        first, supervisor = True, None
        try:
            if lifecycle_enabled:
                supervisor = OwnedWorkerSupervisor(
                    process=process, directory=runtime, binding=request["worker_lifecycle"],
                    expected_image=image,
                )
            while True:
                if cancelled():
                    raise InterruptedError("local_asr_cancelled")
                remaining = timeout_seconds - (time.monotonic() - start)
                if remaining <= 0 or status_path.stat().st_size > 4096:
                    raise ValueError("local_asr_deadline_or_metadata_limit")
                if supervisor is not None:
                    supervisor.poll_handshake()
                try:
                    process.communicate(
                        input=json.dumps(request).encode() if first else None,
                        timeout=min(0.2, remaining),
                    )
                    if supervisor is not None:
                        supervisor.confirm_exit()
                    break
                except subprocess.TimeoutExpired:
                    first = False
        except BaseException:
            if lifecycle_enabled:
                try:
                    if supervisor is None:
                        raise WorkerExitUnconfirmed()
                    supervisor.confirm_exit(terminate=True)
                    _stop(process)
                except Exception:
                    # Only the Popen launcher is known here. Never guess another
                    # PID or allow callers to remove a possibly held recording.
                    try:
                        _stop(process)
                    except Exception:
                        pass
                    raise WorkerExitUnconfirmed() from None
            else:
                _stop(process)
            raise
        finally:
            if supervisor is not None:
                supervisor.close()
    try:
        if process.returncode != 0 or status_path.stat().st_size > 4096:
            raise ValueError("local_asr_worker_failed")
        if cancelled():
            raise InterruptedError("local_asr_cancelled")
        response = json.loads(status_path.read_bytes())
        if response.get("run_id") != run_id or response.get("status") != "completed":
            raise ValueError("local_asr_unavailable")
        for name in ("transcript.txt", "transcript.json"):
            artifact = _plain_path(runtime / name)
            if not 0 < artifact.stat().st_size <= MAX_TRANSCRIPT_BYTES:
                raise ValueError("invalid_transcript_artifact")
        return dict(
            status="completed",
            evidence_mode="local_asr",
            review_required=True,
            speaker_identity_verified=False,
            audio_duration_seconds=frames / rate,
            elapsed_seconds=round(time.monotonic() - start, 2),
            transcript_path=str(runtime / "transcript.txt"),
            segments_path=str(runtime / "transcript.json"),
        )
    finally:
        status_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda:0"], default="cuda:0")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--decoding-profile", choices=sorted(DECODING_BEAMS), default="quality")
    args = parser.parse_args()
    try:
        result = transcribe_local_wav(
            authorized=args.authorized,
            source=args.source,
            model_dir=args.model_dir,
            python_executable=args.python,
            device=args.device,
            timeout_seconds=args.timeout,
            decoding_profile=args.decoding_profile,
        )
    except Exception:
        print(json.dumps(dict(status="failed", reason="local_transcription_unavailable")))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
