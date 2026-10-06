import test from "node:test";
import assert from "node:assert/strict";
import { createLocalVoicePlayback, inspectPcmWav, rmsLevel } from "../local-voice-playback.mjs";
import { createParticleSphere, particleCloud, smoothEnvelope } from "../particle-sphere.mjs";

function wav({ channels = 1, rate = 8000, frames = 80, sample = 1000 } = {}) {
  const buffer = new ArrayBuffer(44 + frames * channels * 2), v = new DataView(buffer);
  const tag = (at, value) => [...value].forEach((c, i) => v.setUint8(at + i, c.charCodeAt()));
  tag(0, "RIFF"); tag(8, "WAVE"); tag(12, "fmt "); tag(36, "data");
  v.setUint32(4, buffer.byteLength - 8, true); v.setUint32(16, 16, true);
  v.setUint16(20, 1, true); v.setUint16(22, channels, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * channels * 2, true); v.setUint16(32, channels * 2, true);
  v.setUint16(34, 16, true); v.setUint32(40, frames * channels * 2, true);
  for (let i = 44; i < buffer.byteLength; i += 2) v.setInt16(i, sample, true);
  return buffer;
}
const file = (buffer) => ({ size: buffer.byteLength, arrayBuffer: async () => buffer });
const deferred = () => { let resolve; const promise = new Promise((fn) => { resolve = fn; }); return { promise, resolve }; };

function audioContext(resume = async () => {}) {
  const sources = [];
  const context = { state: "running", destination: {}, closed: false, resume,
    close() { this.closed = true; this.state = "closed"; },
    createBuffer(channels, frames, rate) { const data = Array.from({ length: channels }, () => new Float32Array(frames)); return { rate, getChannelData: (i) => data[i] }; },
    createAnalyser() { return { fftSize: 1024, connect() {}, disconnect() {}, getFloatTimeDomainData(values) { values.fill(0.1); } }; },
    createBufferSource() { const node = { connect() {}, disconnect() {}, start() { this.started = true; }, stop() { this.stopped = true; }, onended: null }; sources.push(node); return node; },
  };
  return { context, sources };
}

test("PCM mono/stereo metadata is bounded and silent frames are legitimate", () => {
  for (const channels of [1, 2]) {
    const result = inspectPcmWav(wav({ channels, sample: 0 }));
    assert.equal(result.channels, channels); assert.equal(result.frames, 80); assert.equal(result.duration, 0.01);
  }
  for (const mutate of [
    (v) => v.setUint32(4, 0, true), (v) => v.setUint32(40, 9999, true),
    (v) => v.setUint16(20, 3, true), (v) => v.setUint16(22, 3, true),
    (v) => v.setUint32(24, 1000, true), (v) => v.setUint16(34, 32, true),
    (v) => v.setUint16(32, 4, true), (v) => v.setUint32(28, 1, true),
    (v) => v.setUint32(40, 0, true), (v) => v.setUint32(16, 99, true),
  ]) { const value = wav(); mutate(new DataView(value)); assert.throws(() => inspectPcmWav(value), /invalid_local_wav/); }
  assert.throws(() => inspectPcmWav(new ArrayBuffer(44)), /invalid_local_wav/);
  assert.throws(() => inspectPcmWav(wav({ frames: 8000 * 601 })), /invalid_local_wav/);
});

test("level is amplitude only: silence zero, bounded output and nonfinite fail closed", () => {
  assert.equal(rmsLevel(new Float32Array(20)), 0);
  assert.equal(rmsLevel([NaN, 1]), 0); assert.equal(rmsLevel([Infinity]), 0);
  assert.equal(rmsLevel([10]), 1); assert.ok(rmsLevel([0.1, -0.1]) > 0);
});

test("real composition: explicit selection -> play -> analyser -> end; never autoplay", async () => {
  const { context, sources } = audioContext(); const states = []; let allocations = 0;
  const playback = createLocalVoicePlayback({ makeContext: () => { allocations++; return context; }, onState: (s) => states.push(s) });
  assert.equal(await playback.play(), false);
  assert.equal(await playback.selectFile(file(wav({ channels: 2 }))), true);
  assert.equal(allocations, 0); assert.equal(playback.getLevel(), 0);
  assert.equal(await playback.play(), true); assert.equal(sources.length, 1);
  assert.ok(sources[0].started); assert.ok(playback.getLevel() > 0);
  assert.equal(sources[0].buffer.getChannelData(1)[0], 1000 / 32768);
  assert.equal(await playback.play(), false);
  sources[0].onended(); assert.equal(playback.getStatus(), "ready"); assert.equal(playback.getLevel(), 0);
  playback.clear(); assert.equal(playback.getStatus(), "empty"); assert.ok(context.closed);
  assert.ok(states.every((s) => s.authority === "none" && s.evidenceMode === "local_audio_rehearsal"));
  assert.ok(states.every((s) => Object.keys(s).length === 3));
});

test("stop, replacement, reset and disposal invalidate pending file reads", async () => {
  for (const action of ["stop", "clear", "dispose"]) {
    const wait = deferred(); const playback = createLocalVoicePlayback({ makeContext: () => assert.fail("context before click") });
    const reading = playback.selectFile({ size: wav().byteLength, arrayBuffer: () => wait.promise });
    playback[action](); wait.resolve(wav()); assert.equal(await reading, false);
    assert.equal(playback.getLevel(), 0); assert.equal(await playback.play(), false);
  }
  const wait = deferred(); const playback = createLocalVoicePlayback();
  const first = playback.selectFile({ size: wav().byteLength, arrayBuffer: () => wait.promise });
  assert.equal(await playback.selectFile(file(wav({ sample: 2000 }))), true);
  wait.resolve(wav()); assert.equal(await first, false); assert.equal(playback.getStatus(), "ready");
});

test("late resume/end after stop or dispose cannot start or restore playback", async () => {
  for (const action of ["stop", "clear", "dispose"]) {
    const wait = deferred(); const { context, sources } = audioContext(() => wait.promise);
    const playback = createLocalVoicePlayback({ makeContext: () => context });
    await playback.selectFile(file(wav())); const playing = playback.play(); playback[action]();
    wait.resolve(); assert.equal(await playing, false); assert.equal(sources.length, 0);
  }
  const { context, sources } = audioContext(); const playback = createLocalVoicePlayback({ makeContext: () => context });
  await playback.selectFile(file(wav())); await playback.play(); const late = sources[0].onended;
  playback.clear(); late(); assert.equal(playback.getStatus(), "empty"); assert.ok(sources[0].stopped);
});

test("invalid files and failed audio devices stay local with sanitized status", async () => {
  const states = []; const playback = createLocalVoicePlayback({ onState: (s) => states.push(s), makeContext: () => { throw new Error("private-token-path"); } });
  for (const invalid of [null, { size: 33 * 1024 * 1024 }, { size: 44, arrayBuffer: async () => new ArrayBuffer(12) }, file(new ArrayBuffer(44))]) {
    assert.equal(await playback.selectFile(invalid), false); assert.equal(playback.getStatus(), "error");
  }
  await playback.selectFile(file(wav())); assert.equal(await playback.play(), false);
  assert.equal(playback.getStatus(), "error"); assert.ok(!JSON.stringify(states).includes("private"));
  playback.dispose(); assert.equal(await playback.selectFile(file(wav())), false);
});

function scene({ reduced = false } = {}) {
  const frames = new Map(), calls = []; let id = 0;
  const context = { setTransform() {}, clearRect() { calls.push("draw"); }, createRadialGradient: () => ({ addColorStop() {} }), fillRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {} };
  const listeners = new Map(), mediaListeners = new Map();
  const document = { hidden: false, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: (name) => listeners.delete(name) };
  const media = { matches: reduced, addEventListener: (name, fn) => mediaListeners.set(name, fn), removeEventListener: (name) => mediaListeners.delete(name) };
  const host = { document, devicePixelRatio: 4, matchMedia: () => media };
  const canvas = { clientWidth: 320, getContext: () => context };
  const sphere = createParticleSphere(canvas, { host, requestFrame: (fn) => { frames.set(++id, fn); return id; }, cancelFrame: (key) => frames.delete(key), getLevel: () => 0.5 });
  const step = (time) => { const [key, fn] = [...frames][0]; frames.delete(key); fn(time); };
  return { sphere, frames, canvas, document, media, listeners, mediaListeners, step, calls };
}

test("bounded sphere geometry and envelope are finite and smooth", () => {
  const cloud = particleCloud(); assert.equal(cloud.length, 2400);
  assert.ok(cloud.every((p) => Math.abs(p.x * p.x + p.y * p.y + p.z * p.z - 1) < 1e-10));
  assert.throws(() => particleCloud(99999)); assert.throws(() => particleCloud(NaN));
  const attack = smoothEnvelope(0, 1, 0.03); assert.ok(attack > 0 && attack < 1);
  assert.ok(smoothEnvelope(attack, 0, 0.03) < attack); assert.equal(smoothEnvelope(0, NaN, 1), 0);
});

test("renderer composes both voice modes without extra loops, bounds DPR and pauses hidden", () => {
  const s = scene(); assert.equal(s.frames.size, 1); assert.equal(s.canvas.width, 640);
  for (const mode of ["idle", "thinking", "speaking_fixture", "speaking_local", "listening_fixture"]) { s.sphere.setMode(mode); s.step(100); assert.equal(s.frames.size, 1); }
  assert.throws(() => s.sphere.setMode("authenticated"));
  s.document.hidden = true; s.listeners.get("visibilitychange")(); assert.equal(s.frames.size, 0);
  s.document.hidden = false; s.listeners.get("visibilitychange")(); assert.equal(s.frames.size, 1);
  s.sphere.setMotion(false); assert.equal(s.frames.size, 0); s.sphere.setMotion(true); assert.equal(s.frames.size, 1);
  s.sphere.dispose(); assert.equal(s.frames.size, 0); assert.equal(s.listeners.size, 0); assert.equal(s.mediaListeners.size, 0);
  s.sphere.refresh(); assert.equal(s.frames.size, 0);
});

test("reduced motion is static even while speaking; preference changes do not duplicate RAF", () => {
  const s = scene({ reduced: true }); assert.equal(s.frames.size, 0);
  s.sphere.setMode("speaking_local"); assert.equal(s.frames.size, 0);
  s.media.matches = false; s.mediaListeners.get("change")(); assert.equal(s.frames.size, 1);
  s.media.matches = true; s.mediaListeners.get("change")(); assert.equal(s.frames.size, 0);
  s.sphere.dispose();
});

test("canvas unavailable gracefully leaves textual interface intact", () => {
  const s = createParticleSphere({ getContext: () => null });
  s.setMode("idle"); s.setMotion(true); s.refresh(); s.dispose();
});
