// WebAudio lifecycle doubles only: no hardware, browser, model or identity evidence.
import test from "node:test";
import assert from "node:assert/strict";
import { createLocalVoicePlayback, rmsLevel } from "../local-voice-playback.mjs";

const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
};
const tick = async () => { for (let i = 0; i < 6; i++) await Promise.resolve(); };
function wav(frames = 33000, channels = 1, rate = 16000) {
  const buffer = new ArrayBuffer(44 + frames * channels * 2), view = new DataView(buffer);
  const tag = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  tag(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); tag(8, "WAVE");
  tag(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, channels, true); view.setUint32(24, rate, true);
  view.setUint32(28, rate * channels * 2, true); view.setUint16(32, channels * 2, true);
  view.setUint16(34, 16, true); tag(36, "data"); view.setUint32(40, frames * channels * 2, true);
  for (let i = 0; i < frames * channels; i++) view.setInt16(44 + i * 2, i % 2 ? 16384 : -8192, true);
  return buffer;
}
const file = (buffer = wav()) => ({ size: buffer.byteLength, arrayBuffer: async () => buffer,
  get name() { throw new Error("private filename must never be inspected"); } });
function rig(options = {}) {
  const contexts = [], states = [], nodes = [];
  const makeContext = () => {
    if (options.makeError) throw new Error("PRIVATE_CONTEXT_PATH");
    const context = { state: "running", destination: {}, closeCount: 0, buffers: [],
      resume: () => options.resume ? options.resume() : Promise.resolve(),
      close() { this.closeCount++; if (options.closeError) throw new Error("PRIVATE_CLOSE"); return Promise.resolve(); },
      createBuffer(channels, frames, rate) {
        if (options.bufferError) throw new Error("PRIVATE_BUFFER");
        const values = Array.from({ length: channels }, () => new Float32Array(frames));
        const audio = { channels, frames, rate, values, getChannelData: (channel) => values[channel] };
        this.buffers.push(audio); return audio;
      },
      createAnalyser() {
        if (options.analyserError) throw new Error("PRIVATE_ANALYSER");
        const analyser = { fftSize: 0, disconnects: 0,
          connect() { if (options.connectError) throw new Error("PRIVATE_CONNECT"); },
          disconnect() { this.disconnects++; if (options.disconnectError) throw new Error("PRIVATE_DISCONNECT"); },
          getFloatTimeDomainData(samples) { samples.fill(options.level ?? 0.1); if (options.levelError) throw new Error("PRIVATE_LEVEL"); } };
        return analyser;
      },
      createBufferSource() {
        if (options.sourceError) throw new Error("PRIVATE_SOURCE");
        const source = { starts: 0, stops: 0, disconnects: 0, onended: null,
          connect() { if (options.connectError) throw new Error("PRIVATE_CONNECT"); },
          start() { this.starts++; if (options.startError) throw new Error("PRIVATE_START"); },
          stop() { this.stops++; if (options.stopError) throw new Error("PRIVATE_STOP"); },
          disconnect() { this.disconnects++; if (options.disconnectError) throw new Error("PRIVATE_DISCONNECT"); } };
        nodes.push(source); return source;
      } };
    contexts.push(context); return context;
  };
  const playback = createLocalVoicePlayback({ makeContext, yieldTask: options.yieldTask ?? (() => Promise.resolve()),
    onState(state) { states.push(state); options.onState?.(state, playback); } });
  return { playback, makeContext, contexts, states, nodes, starts: () => nodes.reduce((sum, node) => sum + node.starts, 0) };
}

test("selecting valid WAV is local and never creates context or autoplays", async () => {
  const r = rig(); assert.equal(await r.playback.selectFile(file()), true);
  assert.equal(r.playback.getStatus(), "ready"); assert.equal(r.contexts.length, 0);
  assert.equal(r.playback.getLevel(), 0);
  for (const state of r.states) { assert.equal(state.authority, "none"); assert.equal(Object.isFrozen(state), true); }
  r.playback.dispose();
});

test("actual conversion preserves mono/stereo PCM order and RMS is playback-only", async () => {
  const r = rig(); await r.playback.selectFile(file(wav(33000, 2))); await r.playback.play();
  const audio = r.contexts[0].buffers[0];
  assert.equal(audio.frames, 33000); assert.equal(audio.values[0][17000], -0.25);
  assert.equal(audio.values[1][17000], 0.5); assert.equal(r.starts(), 1);
  assert.ok(Math.abs(r.playback.getLevel() - 0.3) < 1e-6);
  r.playback.stop(); assert.equal(r.playback.getLevel(), 0); r.playback.dispose();
});

for (const action of ["stop", "clear", "dispose"]) {
  test(`${action} during resume invalidates continuation before allocating PCM or source`, async () => {
    const gate = deferred(), r = rig({ resume: () => gate.promise });
    await r.playback.selectFile(file()); const pending = r.playback.play();
    assert.equal(r.playback.getStatus(), "starting"); r.playback[action]();
    gate.resolve(); assert.equal(await pending, false); assert.equal(r.starts(), 0);
    assert.equal(r.contexts[0].buffers.length, 0); assert.equal(r.playback.getLevel(), 0);
    if (action !== "stop") assert.equal(r.contexts[0].closeCount, 1);
    r.playback.dispose();
  });
  test(`${action} during cooperative conversion yield prevents late start`, async () => {
    const gate = deferred(); let yields = 0;
    const r = rig({ yieldTask: () => { yields++; return gate.promise; } });
    await r.playback.selectFile(file()); const pending = r.playback.play(); await tick();
    assert.ok(yields > 0, "conversion must yield after at most 16k frames");
    r.playback[action](); gate.resolve(); assert.equal(await pending, false);
    assert.equal(r.starts(), 0); assert.equal(r.playback.getLevel(), 0); r.playback.dispose();
  });
}

test("parallel explicit play creates one context, buffer and source only", async () => {
  const gate = deferred(), r = rig({ resume: () => gate.promise });
  await r.playback.selectFile(file()); const first = r.playback.play();
  assert.equal(await r.playback.play(), false); gate.resolve(); assert.equal(await first, true);
  assert.equal(r.contexts.length, 1); assert.equal(r.contexts[0].buffers.length, 1);
  assert.equal(r.starts(), 1); r.playback.dispose();
});

test("late yield from previous play cannot resume or alter a newer explicit play", async () => {
  const gate = deferred(); let calls = 0;
  const r = rig({ yieldTask: () => ++calls === 1 ? gate.promise : Promise.resolve() });
  await r.playback.selectFile(file()); const old = r.playback.play(); await tick();
  r.playback.stop(); assert.equal(await r.playback.play(), true);
  const current = r.nodes.at(-1); gate.resolve(); assert.equal(await old, false);
  assert.equal(r.playback.getStatus(), "playing"); assert.equal(current.stops, 0);
  assert.equal(r.starts(), 1); r.playback.dispose();
});

test("new file selection during pending resume closes old context and prevents stale playback", async () => {
  const gate = deferred(), r = rig({ resume: () => gate.promise });
  await r.playback.selectFile(file()); const old = r.playback.play();
  await r.playback.selectFile(file(wav(100))); gate.resolve(); assert.equal(await old, false);
  assert.equal(r.playback.getStatus(), "ready"); assert.equal(r.contexts[0].closeCount, 1);
  assert.equal(r.starts(), 0); r.playback.dispose();
});

test("late onended from a stopped node cannot stop a newer source", async () => {
  const r = rig(); await r.playback.selectFile(file(wav(100))); await r.playback.play();
  const end = r.nodes[0].onended; r.playback.stop(); await r.playback.play();
  end(); assert.equal(r.playback.getStatus(), "playing"); assert.equal(r.nodes[1].stops, 0);
  r.nodes[1].onended(); assert.equal(r.playback.getStatus(), "ready"); r.playback.dispose();
});

for (const fault of ["makeError", "bufferError", "analyserError", "sourceError", "connectError", "startError"]) {
  test(`${fault} stays sanitized and leaves no playing source`, async () => {
    const r = rig({ [fault]: true }); await r.playback.selectFile(file(wav(100)));
    assert.equal(await r.playback.play(), false); assert.equal(r.playback.getStatus(), "error");
    assert.equal(r.playback.getLevel(), 0); assert.ok(!JSON.stringify(r.states).includes("PRIVATE_"));
    r.playback.dispose();
  });
}

test("yield rejection is sanitized, cannot start, and stale rejection cannot break newer play", async () => {
  const gate = deferred(); let calls = 0;
  const r = rig({ yieldTask: () => ++calls === 1 ? gate.promise : Promise.resolve() });
  await r.playback.selectFile(file()); const old = r.playback.play(); await tick();
  r.playback.stop(); await r.playback.play(); gate.reject(new Error("PRIVATE_YIELD_PATH"));
  assert.equal(await old, false); assert.equal(r.playback.getStatus(), "playing");
  assert.ok(!JSON.stringify(r.states).includes("PRIVATE_")); r.playback.dispose();
});

test("observer exceptions cannot turn selected input into an uncaught operation", async () => {
  const r = rig({ onState() { throw new Error("PRIVATE_OBSERVER"); } });
  assert.equal(await r.playback.selectFile(file(wav(100))), true);
  assert.equal(await r.playback.play(), true); assert.doesNotThrow(() => r.playback.clear());
  assert.equal(r.playback.getStatus(), "empty"); assert.ok(!JSON.stringify(r.states).includes("PRIVATE_"));
  r.playback.dispose();
});

test("reentrant observer stop at starting never creates an audio context", async () => {
  const r = rig({ onState(state, playback) { if (state.status === "starting") playback.stop(); } });
  await r.playback.selectFile(file(wav(100))); assert.equal(await r.playback.play(), false);
  assert.equal(r.contexts.length, 0); assert.equal(r.playback.getStatus(), "ready"); r.playback.dispose();
});

test("node shutdown errors are swallowed and clear closes exactly one context", async () => {
  const r = rig({ stopError: true, disconnectError: true, closeError: true });
  await r.playback.selectFile(file(wav(100))); await r.playback.play();
  assert.doesNotThrow(() => r.playback.clear()); assert.equal(r.playback.getStatus(), "empty");
  assert.equal(r.contexts[0].closeCount, 1); r.playback.clear(); r.playback.dispose();
  assert.equal(r.contexts[0].closeCount, 1);
});

test("RMS refuses unavailable/nonfinite readings and inactive audio context", async () => {
  assert.equal(rmsLevel(new Float32Array([NaN, 0.1])), 0); assert.equal(rmsLevel([]), 0);
  const r = rig(); await r.playback.selectFile(file(wav(100))); await r.playback.play();
  r.contexts[0].state = "suspended"; assert.equal(r.playback.getLevel(), 0); r.playback.dispose();
});

test("active yield rejection is sanitized and cannot start any source", async () => {
  const r = rig({ yieldTask: () => Promise.reject(new Error("PRIVATE_ACTIVE_YIELD")) });
  await r.playback.selectFile(file()); assert.equal(await r.playback.play(), false);
  assert.equal(r.playback.getStatus(), "error"); assert.equal(r.starts(), 0);
  assert.equal(r.playback.getLevel(), 0); assert.ok(!JSON.stringify(r.states).includes("PRIVATE_"));
  r.playback.dispose();
});

test("resume rejection cannot leak diagnostic details or allocate a decoded buffer", async () => {
  const r = rig({ resume: () => Promise.reject(new Error("PRIVATE_RESUME_DEVICE")) });
  await r.playback.selectFile(file()); assert.equal(await r.playback.play(), false);
  assert.equal(r.contexts[0].buffers.length, 0); assert.equal(r.starts(), 0);
  assert.equal(r.playback.getStatus(), "error"); assert.ok(!JSON.stringify(r.states).includes("PRIVATE_"));
  r.playback.dispose();
});

test("observer revocation during loading performs no private file read", async () => {
  let reads = 0;
  const r = rig({ onState(state, playback) { if (state.status === "loading") playback.dispose(); } });
  const buffer = wav(100);
  assert.equal(await r.playback.selectFile({ size: buffer.byteLength, arrayBuffer: async () => { reads++; return buffer; } }), false);
  assert.equal(reads, 0); assert.equal(r.playback.getStatus(), "empty"); assert.equal(r.contexts.length, 0);
});

test("nested play/select from observer cannot acquire playback or replace selected file", async () => {
  const attempts = []; let nesting = false;
  const r = rig({ onState(state, playback) {
    if (state.status !== "ready" || nesting) return;
    nesting = true; attempts.push(playback.play(), playback.selectFile(file(wav(20)))); nesting = false;
  } });
  await r.playback.selectFile(file(wav(100))); assert.deepEqual(await Promise.all(attempts), [false, false]);
  assert.equal(r.contexts.length, 0); assert.equal(r.playback.getStatus(), "ready"); r.playback.dispose();
});

test("default scheduler yields a macrotask so a UI stop can interrupt PCM conversion", async () => {
  const base = rig();
  const playback = createLocalVoicePlayback({ makeContext: base.makeContext });
  await playback.selectFile(file(wav(33000))); const pending = playback.play(); await tick();
  assert.equal(playback.getStatus(), "starting");
  await new Promise((resolve) => setTimeout(() => { playback.stop(); resolve(); }, 0));
  assert.equal(await pending, false); assert.equal(playback.getStatus(), "ready");
  assert.equal(base.contexts.length, 1); assert.equal(base.nodes.length, 0);
  playback.dispose(); base.playback.dispose();
});
