"""Explicit consent CLI; synthesis text is supplied privately through stdin."""

import argparse
import json
import sys
import wave
from pathlib import Path

from .lab import ENGINES, _plain_path, run_voice_lab
from .quality import PROFILES


def main() -> int:
    parser = argparse.ArgumentParser(description="Opt-in offline TTS research lab")
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--engine", choices=sorted(ENGINES), required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--sdk-source-dir", type=Path)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--device", choices=["cpu", "cuda:0"], default="cpu")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--text-stdin", action="store_true", required=True)
    parser.add_argument("--show-output-path", action="store_true")
    parser.add_argument("--voice-profile", choices=sorted(PROFILES), default="baseline")
    parser.add_argument("--reference-start", type=float, default=0)
    parser.add_argument("--reference-duration", type=float, default=10)
    parser.add_argument("--reference-transcript-file", type=Path)
    parser.add_argument("--transcript-confirmed", action="store_true")
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    text = sys.stdin.read(601)
    try:
        transcript = None
        if args.reference_transcript_file is not None:
            path = _plain_path(args.reference_transcript_file)
            with path.open("rb") as stream:
                raw = stream.read(8001)
            if len(raw) > 8000:
                raise ValueError("reference_transcript_limit_exceeded")
            transcript = raw.decode("utf-8")
        result = run_voice_lab(
            engine=args.engine,
            authorized=args.authorized,
            reference_path=args.reference,
            text=text,
            model_dir=args.model_dir,
            python_executable=args.python,
            workspace_root=args.workspace,
            device=args.device,
            timeout_seconds=args.timeout,
            sdk_source_dir=args.sdk_source_dir,
            voice_profile=args.voice_profile,
            reference_start_seconds=args.reference_start,
            reference_duration_seconds=args.reference_duration,
            reference_transcript=transcript,
            transcript_confirmed=args.transcript_confirmed,
            seed=args.seed,
        )
    except (ValueError, OSError, wave.Error):
        print(json.dumps({"status": "failed", "reason": "invalid_local_request"}))
        return 2
    metadata = result.metadata()
    metadata["voice_profile"] = args.voice_profile
    metadata["reference_start_seconds"] = args.reference_start
    metadata["reference_duration_seconds"] = args.reference_duration
    metadata["seed"] = args.seed
    if args.voice_profile in {"qwen_icl", "qwen_icl_draft"}:
        metadata["reference_transcript_reviewed"] = args.transcript_confirmed
        metadata["review_required"] = not args.transcript_confirmed
    if args.show_output_path and result.output_path is not None:
        metadata["output_path"] = result.output_path
    print(json.dumps(metadata, ensure_ascii=True))
    return 0 if result.status == "completed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
