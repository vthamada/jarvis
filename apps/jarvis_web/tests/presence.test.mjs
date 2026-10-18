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

function scene({ reduced = false, getLevel = () => 0.5, width = 320, density = 4 } = {}) {
  const frames = new Map(), calls = [], rectangles = [], paths = [], strokes = [], gradients = [], attributes = new Map(); let id = 0, pathLength = 0, moves = 0, segments = 0, commands = [];
  const context = {
    setTransform() {},
    clearRect() { calls.push("draw"); rectangles.length = 0; paths.length = 0; strokes.length = 0; gradients.length = 0; },
    createRadialGradient() { const stops = []; gradients.push(stops); return { addColorStop(at, color) { stops.push({ at, color }); } }; },
    fillRect(...values) { rectangles.push(values); },
    beginPath() { pathLength = 0; moves = 0; segments = 0; commands = []; },
    moveTo(...values) { paths.push(values); commands.push(values); pathLength++; moves++; },
    lineTo(...values) { paths.push(values); commands.push(values); pathLength++; segments++; },
    stroke() { strokes.push({ color: this.strokeStyle, width: this.lineWidth, pathLength, moves, segments, commands, composition: this.globalCompositeOperation }); },
  };
  const listeners = new Map(), mediaListeners = new Map();
  const document = { hidden: false, addEventListener: (name, fn) => listeners.set(name, fn), removeEventListener: (name) => listeners.delete(name) };
  const media = { matches: reduced, addEventListener: (name, fn) => mediaListeners.set(name, fn), removeEventListener: (name) => mediaListeners.delete(name) };
  const observation = { target: null, disconnected: false, callback: null };
  const host = { document, devicePixelRatio: density, matchMedia: () => media, ResizeObserver: class {
    constructor(callback) { observation.callback = callback; }
    observe(target) { observation.target = target; }
    disconnect() { observation.disconnected = true; }
  } };
  const canvas = { clientWidth: width, getContext: () => context, setAttribute: (name, value) => attributes.set(name, value) };
  const sphere = createParticleSphere(canvas, { host, requestFrame: (fn) => { frames.set(++id, fn); return id; }, cancelFrame: (key) => frames.delete(key), getLevel });
  const step = (time) => { const [key, fn] = [...frames][0]; frames.delete(key); fn(time); };
  return { sphere, frames, canvas, document, media, listeners, mediaListeners, step, calls, rectangles, paths, strokes, gradients, attributes, observation, context };
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
  assert.equal(s.observation.disconnected, true);
  s.sphere.refresh(); assert.equal(s.frames.size, 0);
});

test("cinematic scene has bounded particles, finite holographic paths and restores composition", () => {
  const s = scene(); s.step(100);
  assert.equal(s.rectangles.length, 3982, "3,980 particles and two glow surfaces, including all volumes");
  assert.ok(s.strokes.length >= 20, "orbit arcs, instrument ticks, latitude ribbons and filaments are visible layers");
  assert.ok(s.paths.length >= 1000);
  assert.ok([...s.rectangles, ...s.paths].every((point) => point.every(Number.isFinite)));
  assert.ok(s.strokes.every((stroke) => Number.isFinite(stroke.width) && stroke.width > 0 && !stroke.color.includes("NaN")));
  assert.equal(s.context.globalCompositeOperation, "source-over");
  s.sphere.dispose();
});

test("connected constellations and luminous orbits stay bounded without a rectangular glow edge", () => {
  const s = scene(); s.step(100);
  assert.ok(s.strokes.filter((stroke) => stroke.pathLength > 500).length >= 2, "large batched paths connect the projected volume, not only circular outlines");
  assert.ok(s.paths.length > 5000 && s.paths.length < 12000, "fixed edge and orbital budgets bound every frame");
  assert.ok(s.strokes.some((stroke) => stroke.composition === "lighter" && stroke.width >= 2), "additive halo strokes surround the bright filaments");
  const luminousWhite = (color) => {
    const values = /^rgba\((\d+),(\d+),(\d+),([\d.]+)\)$/u.exec(color);
    return values && Number(values[1]) >= 210 && Number(values[2]) >= 240 && Number(values[3]) >= 240 && Number(values[4]) >= 0.9;
  };
  assert.ok(s.strokes.some((stroke) => luminousWhite(stroke.color)), "foreground orbital strands contain near-white light");
  assert.ok(s.gradients.some((stops) => stops.some((stop) => luminousWhite(stop.color))), "the core has a brilliant white center");
  assert.ok(s.gradients.every((stops) => stops.at(-1).at === 1 && stops.at(-1).color.endsWith(",0)")), "all radial light fades fully to transparency before its bounds");
  s.sphere.dispose();
});

test("constellation strands have bounded flowing segments instead of disconnected short ticks", () => {
  const s = scene(); s.step(100);
  const networks = s.strokes.filter((stroke) => stroke.moves > 100 && stroke.segments === stroke.moves * 3);
  assert.ok(networks.length >= 2, "front and rear batches contain three-segment strands");
  assert.ok(networks.every((stroke) => stroke.segments < 1500), "longer strands do not expand the fixed network work budget");
  assert.ok(networks.some((stroke) => stroke.color.endsWith(",0.29)")), "white network strands remain secondary to luminous vertices and orbit ribbons");
  const batches = [...new Set(networks.map((stroke) => stroke.commands))], endpoints = [];
  let longStrands = 0;
  for (const commands of batches) {
    for (let index = 0; index < commands.length; index += 4) {
      const start = commands[index], end = commands[index + 3];
      endpoints.push(start.join(","), end.join(","));
      if (Math.hypot(end[0] - start[0], end[1] - start[1]) > 30) longStrands++;
    }
  }
  assert.ok(new Set(endpoints).size < endpoints.length / 2, "many strands actually meet at the same projected vertices");
  assert.ok(longStrands > 100, "connections visibly span the volume instead of resembling short instrument ticks");
  s.sphere.dispose();
});

test("local voice amplitude drives the envelope and stop immediately removes voice energy", () => {
  let amplitude = 0;
  const s = scene({ getLevel: () => amplitude }); s.sphere.setMode("speaking_local"); s.step(0);
  assert.equal(s.attributes.get("data-visual-mode"), "speaking_local");
  assert.equal(s.attributes.get("data-visual-level"), "0");
  amplitude = 0.2; s.step(40); const quiet = Number(s.attributes.get("data-visual-level"));
  assert.ok(quiet > 0 && quiet < 0.2);
  amplitude = 0.9; s.step(80); const loud = Number(s.attributes.get("data-visual-level"));
  assert.ok(loud > quiet && loud < 0.9);
  amplitude = 0; s.step(120); assert.ok(Number(s.attributes.get("data-visual-level")) < loud);
  s.sphere.setMode("idle"); s.step(160);
  assert.equal(s.attributes.get("data-visual-level"), "0");
  assert.equal(s.attributes.get("data-visual-mode"), "idle");
  s.sphere.dispose();
});

test("fixture, idle and static modes never consult local audio or claim local speech", () => {
  let reads = 0;
  const s = scene({ getLevel: () => { reads++; return 1; } });
  for (const [i, mode] of ["idle", "thinking", "listening_fixture", "speaking_fixture", "error"].entries()) {
    s.sphere.setMode(mode); s.step(i * 40);
    assert.equal(s.attributes.get("data-visual-mode"), mode);
  }
  assert.equal(reads, 0);
  s.sphere.setMotion(false); s.sphere.setMode("speaking_local");
  assert.equal(reads, 0); assert.equal(s.attributes.get("data-visual-level"), "0");
  s.sphere.dispose();
});

test("analyser faults and malformed audio levels fail silent without breaking the animation", () => {
  for (const value of [NaN, Infinity, -Infinity, -1, "0.8", null, {}]) {
    const s = scene({ getLevel: () => value }); s.sphere.setMode("speaking_local"); s.step(0);
    assert.equal(s.attributes.get("data-visual-level"), "0"); assert.equal(s.frames.size, 1); s.sphere.dispose();
  }
  const broken = scene({ getLevel: () => { throw new Error("disconnected analyser"); } });
  broken.sphere.setMode("speaking_local"); assert.doesNotThrow(() => broken.step(0));
  assert.equal(broken.attributes.get("data-visual-level"), "0"); assert.equal(broken.frames.size, 1);
  broken.sphere.dispose();
  const saturated = scene({ getLevel: () => 100 }); saturated.sphere.setMode("speaking_local");
  for (let i = 0; i < 12; i++) saturated.step(i * 40);
  assert.ok(Number(saturated.attributes.get("data-visual-level")) > 0);
  assert.ok(Number(saturated.attributes.get("data-visual-level")) <= 1); saturated.sphere.dispose();
});

test("draw frequency is at most thirty fps and resize cannot create another loop", () => {
  const s = scene(); s.step(0); const before = s.calls.length;
  for (const time of [8, 16, 24, 32]) s.step(time);
  assert.equal(s.calls.length, before); s.step(34); assert.equal(s.calls.length, before + 1);
  assert.equal(s.observation.target, s.canvas);
  s.canvas.clientWidth = 440; s.observation.callback();
  assert.equal(s.frames.size, 1); s.step(80); assert.equal(s.canvas.width, 880);
  s.sphere.dispose(); const draws = s.calls.length;
  s.sphere.setMode("speaking_local"); s.sphere.setMotion(true); s.sphere.refresh();
  assert.equal(s.calls.length, draws); assert.equal(s.frames.size, 0);
});

test("invalid viewport values cannot create nonfinite or unbounded backing stores", () => {
  for (const settings of [{ width: Infinity, density: NaN }, { width: 0, density: -1 }, { width: 4000, density: 10 }]) {
    const s = scene(settings);
    assert.ok(Number.isFinite(s.canvas.width) && s.canvas.width > 0 && s.canvas.width <= 1040);
    assert.equal(s.canvas.width, s.canvas.height);
    assert.ok([...s.rectangles, ...s.paths].every((point) => point.every(Number.isFinite)));
    s.sphere.dispose();
  }
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
