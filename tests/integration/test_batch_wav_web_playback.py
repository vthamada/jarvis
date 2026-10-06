"""Real Python PCM assembly -> real JS parser; synthesis/human voices excluded."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import struct
import subprocess
import time
import wave
from pathlib import Path

import pytest

from apps.jarvis_voice_lab.batch_audio import assemble_wavs, inspect_wav

ROOT = Path(__file__).resolve().parents[2]
MODULE = (ROOT / "apps/jarvis_web/local-voice-playback.mjs").as_uri()
NODE = shutil.which("node")
if NODE is None:
    bundled = Path("C:/Program Files/nodejs/node.exe")
    NODE = str(bundled) if bundled.is_file() else None


def create_playback_fixture(directory: Path, *, part_seconds: int = 100) -> Path:
    """Six quiet synthetic tones, no SDK, source recording or existing overwrite."""
    parts = []
    for index in range(6):
        path = directory / f"part-{index:04d}.wav"
        frequency = 220 + 20 * index
        pcm = b"".join(struct.pack("<h", round(512 * math.sin(2 * math.pi * frequency * i / 8000)))
                       for i in range(8000)) * part_seconds
        with path.open("xb") as stream, wave.open(stream, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(pcm)
        parts.append(path)
    output = directory / "sample.wav"
    assemble_wavs(parts, output, deadline=time.monotonic() + 60)
    return output


def _node(script: str, *args: str):
    if NODE is None:
        pytest.skip("Node unavailable for real Python -> JS interoperability")
    process = subprocess.run(
        [NODE, "--input-type=module", "-e", script, *args], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout)


@pytest.mark.parametrize("seconds", [21, 100])
def test_real_python_aggregate_beyond_old_limit_is_exactly_accepted_in_js(tmp_path, seconds):
    output = create_playback_fixture(tmp_path, part_seconds=seconds)
    expected = inspect_wav(output)
    with wave.open(str(output), "rb") as audio:
        pcm = audio.readframes(audio.getnframes())
    script = """
        import fs from 'node:fs';
        import {createHash} from 'node:crypto';
        const {inspectPcmWav, MAX_WAV_BYTES, MAX_WAV_SECONDS} = await import(process.argv[1]);
        const bytes = fs.readFileSync(process.argv[2]);
        const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
        const info = inspectPcmWav(buffer);
        const pcm = Buffer.from(buffer, info.offset, info.bytes);
        console.log(JSON.stringify({info, digest: createHash('sha256').update(pcm).digest('hex'),
          maxBytes: MAX_WAV_BYTES, maxSeconds: MAX_WAV_SECONDS}));
    """
    actual = _node(script, MODULE, str(output))
    assert actual["info"]["channels"] == expected[2] == 1
    assert actual["info"]["rate"] == expected[0] == 8000
    assert actual["info"]["frames"] == expected[1] == 8000 * 6 * seconds
    assert actual["info"]["duration"] == 6 * seconds
    assert actual["info"]["bytes"] == len(pcm)
    assert actual["digest"] == hashlib.sha256(pcm).hexdigest()
    assert actual["maxBytes"] == 32 * 1024 * 1024
    assert actual["maxSeconds"] == 600


@pytest.mark.parametrize("mode", ["duration", "truncated", "trailing", "order"])
def test_js_refuses_tampered_aggregate_without_echoing_private_input(tmp_path, mode):
    output = create_playback_fixture(tmp_path, part_seconds=21)
    script = """
        import fs from 'node:fs';
        const {inspectPcmWav} = await import(process.argv[1]);
        const bytes = fs.readFileSync(process.argv[2]);
        let value = bytes;
        const mode = process.argv[3];
        if (mode === 'duration') {
          value = Buffer.alloc(44 + 8000 * 601 * 2);
          bytes.copy(value, 0, 0, 44);
          value.writeUInt32LE(value.length - 8, 4);
          value.writeUInt32LE(value.length - 44, 40);
        } else if (mode === 'truncated') value = bytes.subarray(0, bytes.length - 2);
        else if (mode === 'trailing') value = Buffer.concat([bytes, Buffer.from('private-marker')]);
        else if (mode === 'order') {
          value = Buffer.concat([
            bytes.subarray(0, 12), bytes.subarray(36), bytes.subarray(12, 36)]);
        }
        try {
          inspectPcmWav(value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength));
          console.log(JSON.stringify({accepted: true}));
        } catch (error) {
          console.log(JSON.stringify({accepted: false, reason: error.message}));
        }
    """
    assert _node(script, MODULE, str(output), mode) == {
        "accepted": False, "reason": "invalid_local_wav",
    }
