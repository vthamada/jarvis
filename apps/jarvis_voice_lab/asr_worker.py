"""Private, offline Whisper inference with local artifacts and no speaker identification."""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path


def transcript_document(result, duration):
    if not isinstance(result, dict) or not isinstance(result.get("chunks"), list):
        raise ValueError("invalid_asr_result")
    if (
        type(duration) not in (float, int)
        or not 0 < duration <= 900
        or not 0 < len(result["chunks"]) <= 1000
        or not math.isfinite(duration)
    ):
        raise ValueError("invalid_asr_result")
    segments = []
    previous = 0.0
    for chunk in result["chunks"]:
        text, times = chunk.get("text"), chunk.get("timestamp")
        if (
            not isinstance(text, str)
            or not text.strip()
            or not 0 < len(text) <= 4000
            or any(ord(c) < 32 and c not in "\r\n\t" for c in text)
            or any(0xD800 <= ord(c) <= 0xDFFF for c in text)
            or not isinstance(times, (tuple, list))
            or len(times) != 2
        ):
            raise ValueError("invalid_asr_segment")
        start, end = times
        estimated = start is None or end is None or chunk.get("timestamps_estimated") is True
        start = previous if start is None else start
        end = duration if end is None else end
        if (
            any(type(v) not in (float, int) or not math.isfinite(v) for v in (start, end))
            or not previous <= start <= end <= duration + 2
        ):
            raise ValueError("invalid_asr_timestamps")
        previous = start
        segments.append(
            dict(
                start_seconds=start,
                end_seconds=min(duration, end),
                timestamps_estimated=estimated,
                text=text.strip(),
            )
        )
    total = sum(len(s["text"]) for s in segments)
    if not 0 < total <= 50000:
        raise ValueError("transcript_limit_exceeded")
    lines = [
        "TRANSCRIÇÃO AUTOMÁTICA LOCAL — RASCUNHO NÃO REVISADO",
        "Marcações de tempo aproximadas. Não identifica falantes; pode conter erros.",
        "",
    ]
    for s in segments:

        def stamp(value):
            return f"{int(value) // 60:02}:{value % 60:05.2f}"

        lines.append(f"[{stamp(s['start_seconds'])}–{stamp(s['end_seconds'])}] {s['text']}")
    return "\n".join(lines) + "\n", dict(
        review_required=True,
        language="Portuguese",
        audio_duration_seconds=duration,
        segments=segments,
    )


def transcribe_windows(asr, audio, rate, duration):
    """Independent 20s windows; timestamps locate windows, not individual words."""
    chunks = []
    window_frames = rate * 20
    for offset in range(0, len(audio), window_frames):
        piece = audio[offset : offset + window_frames]
        result = asr(
            dict(array=piece, sampling_rate=rate),
            return_timestamps=False,
            generate_kwargs=dict(
                language="portuguese",
                task="transcribe",
                num_beams=5,
                max_new_tokens=256,
                no_repeat_ngram_size=4,
            ),
        )
        text = result.get("text") if isinstance(result, dict) else None
        if not isinstance(text, str):
            raise ValueError("invalid_asr_window")
        chunks.append(
            dict(
                text=text.strip() or "[Sem fala reconhecida nesta janela.]",
                timestamp=(offset / rate, min(duration, (offset + len(piece)) / rate)),
                timestamps_estimated=True,
            )
        )
    return dict(chunks=chunks)


def generate(request):
    import librosa
    import numpy as np
    import soundfile as sf
    import torch
    from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

    model_dir = request["model_dir"]
    dtype = torch.float16 if request["device"] == "cuda:0" else torch.float32
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_dir,
        dtype=dtype,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        attn_implementation="sdpa",
    ).to(request["device"])
    processor = AutoProcessor.from_pretrained(
        model_dir, local_files_only=True, trust_remote_code=False
    )
    audio, rate = sf.read(request["source"], dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if not np.isfinite(audio).all():
        raise ValueError("invalid_audio")
    if rate != 16000:
        audio = librosa.resample(audio, orig_sr=rate, target_sr=16000)
    asr = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        dtype=dtype,
        device=request["device"],
        batch_size=1,
        return_timestamps=False,
    )
    result = transcribe_windows(asr, audio, 16000, request["duration_seconds"])
    text, data = transcript_document(result, request["duration_seconds"])
    output = Path(request["output_directory"])
    for name, value in (
        ("transcript.txt", text),
        ("transcript.json", json.dumps(data, ensure_ascii=False, indent=2)),
    ):
        path = output / name
        raw = value.encode("utf-8")
        if len(raw) > 256 * 1024:
            raise ValueError("transcript_limit_exceeded")
        with path.open("xb") as handle:
            os.chmod(path, 0o600)
            handle.write(raw)


def main():
    result = {}
    try:
        raw = sys.stdin.buffer.read(16385)
        if len(raw) > 16384:
            return 2
        request = json.loads(raw)
        if request.get("authorized") is not True or request.get("device") not in {"cpu", "cuda:0"}:
            return 2
        result["run_id"] = request["run_id"]
        spec = importlib.util.spec_from_file_location(
            "offline_voice_guard", Path(__file__).with_name("worker.py")
        )
        guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guard)
        guard._deny_network()
        with contextlib.redirect_stdout(sys.stderr):
            generate(request)
        result["status"] = "completed"
    except Exception as error:
        result.update(status="failed", error_type=type(error).__name__[:50])
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
