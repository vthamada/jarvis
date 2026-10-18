import test from "node:test";
import assert from "node:assert/strict";
import { createMicrophoneCapture, encodeMonoPcmWav, MAX_CAPTURE_BYTES } from "../microphone-capture.mjs";
import { inspectPcmWav } from "../local-voice-playback.mjs";

const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { resolve, reject, promise }; };
const tick = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
class Events {
  constructor() { this.handlers = new Map(); }
  addEventListener(name, fn) { const set = this.handlers.get(name) ?? new Set(); set.add(fn); this.handlers.set(name, set); }
  removeEventListener(name, fn) { this.handlers.get(name)?.delete(fn); }
  dispatch(name) { for (const fn of this.handlers.get(name) ?? []) fn(); }
}
function scene({ permission, resume = () => Promise.resolve(), maxSeconds = 30, maxBytes = MAX_CAPTURE_BYTES, rate = 8000 } = {}) {
  const document = new Events(), host = new Events(), track = new Events();
  document.hidden = false; host.document = document; track.stops = 0; track.readyState = "live";
  track.stop = () => { track.stops++; track.readyState = "ended"; };
  const stream = { getTracks: () => [track], getAudioTracks: () => [track] };
  const timers = new Map(), nodes = [], states = [], contexts = [], requests = [];
  let sequence = 0;
  const node = () => { const value = { connections: [], disconnects: 0,
    connect(target) { this.connections.push(target); }, disconnect() { this.disconnects++; } }; nodes.push(value); return value; };
  const capture = createMicrophoneCapture({ host, maxSeconds, maxBytes,
    onState: (state) => states.push(state),
    getUserMedia(options) { requests.push(options); return permission ? permission() : Promise.resolve(stream); },
    setTimer(fn, ms) { timers.set(++sequence, { fn, ms }); return sequence; }, clearTimer: (id) => timers.delete(id),
    makeContext() {
      const context = { sampleRate: rate, destination: {}, closes: 0,
        resume, close() { this.closes++; return Promise.resolve(); },
        createMediaStreamSource: () => node(), createScriptProcessor: (...args) => {
          const processor = node(); processor.arguments = args; context.processor = processor; return processor;
        }, createGain: () => { const gain = node(); gain.gain = { value: 1 }; context.gain = gain; return gain; } };
      contexts.push(context); return context;
    } });
  return { capture, states, contexts, requests, track, stream, timers, document, host, nodes,
    input(samples = new Float32Array([0, .25, -.5, 1])) {
      const output = new Float32Array(samples.length).fill(1);
      contexts.at(-1).processor.onaudioprocess({ inputBuffer: { getChannelData: () => samples }, outputBuffer: { getChannelData: () => output } });
      return output;
    } };
}

test("PCM encoder emits interoperable mono16 WAV with exact independent signed samples", () => {
  const buffer = encodeMonoPcmWav([new Float32Array([-2, -1, -.5]), new Float32Array([0, .5, 1, 2])], 8000);
  const info = inspectPcmWav(buffer), view = new DataView(buffer);
  assert.deepEqual(info, { channels: 1, rate: 8000, offset: 44, bytes: 14, frames: 7, duration: 7 / 8000 });
  assert.deepEqual(Array.from({ length: 7 }, (_, i) => view.getInt16(44 + i * 2, true)), [-32768, -32768, -16384, 0, 16384, 32767, 32767]);
});
for (const rate of [7999, 96001, 8000.5, NaN, "8000"]) test(`PCM refuses unsupported rate ${String(rate)}`, () => {
  assert.throws(() => encodeMonoPcmWav([new Float32Array([0])], rate), /invalid_capture/);
});
for (const chunks of [[], [new Float32Array()], [[0]], [new Float32Array([NaN])], [new Float32Array([Infinity])]])
  test(`PCM refuses empty/nonfinite/foreign chunks ${JSON.stringify(chunks)}`, () => {
    assert.throws(() => encodeMonoPcmWav(chunks, 8000), /invalid_capture|empty_capture/);
  });
test("PCM bounds both real sample duration and byte count, including exact maximum", () => {
  assert.equal(encodeMonoPcmWav([new Float32Array(240000)], 8000).byteLength, 480044);
  assert.throws(() => encodeMonoPcmWav([new Float32Array(240001)], 8000), /capture_limit/);
  assert.throws(() => encodeMonoPcmWav([new Float32Array(2)], 8000, { maxBytes: 46 }), /capture_limit/);
  assert.throws(() => encodeMonoPcmWav([new Float32Array(1)], 8000, { maxSeconds: 31 }), /invalid_capture/);
});

test("construction is inert; explicit start requests audio-only and connects only a zero gain output", async () => {
  const s = scene(); assert.equal(s.requests.length, 0); assert.equal(s.contexts.length, 0);
  assert.equal(await s.capture.start(), true); assert.equal(s.requests.length, 1);
  assert.deepEqual(s.requests[0], { audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: false }, video: false });
  assert.deepEqual(s.contexts[0].processor.arguments, [4096, 1, 1]); assert.equal(s.contexts[0].gain.gain.value, 0);
  assert.deepEqual([...s.input()], [0, 0, 0, 0]); assert.ok(s.capture.getLevel() > 0);
  const buffer = await s.capture.stop(); assert.equal(inspectPcmWav(buffer).frames, 4);
  assert.equal(s.track.stops, 1); assert.equal(s.contexts[0].closes, 1); assert.equal(s.timers.size, 0);
  assert.equal(s.capture.getLevel(), 0); assert.equal(await s.capture.stop(), null);
  assert.ok(s.nodes.every((node) => node.disconnects === 1)); s.capture.dispose();
});
test("silence RMS is zero and recorded input is copied before the browser reuses its buffer", async () => {
  const s = scene(); await s.capture.start(); const samples = new Float32Array([0, 0]); s.input(samples);
  assert.equal(s.capture.getLevel(), 0); samples.fill(1);
  const buffer = await s.capture.stop(); assert.equal(new DataView(buffer).getInt16(44, true), 0); s.capture.dispose();
});
test("byte/sample ceiling automatically releases hardware but never uploads or consumes the review clip", async () => {
  const s = scene({ maxBytes: 46 }); await s.capture.start(); s.input(new Float32Array([.5, 1]));
  assert.equal(s.capture.getState().status, "ready"); assert.equal(s.track.stops, 1); assert.equal(s.capture.getLevel(), 0);
  const buffer = await s.capture.stop(); assert.equal(buffer.byteLength, 46); assert.equal(inspectPcmWav(buffer).frames, 1);
  assert.equal(await s.capture.stop(), null); s.capture.dispose();
});
test("wall-time bound closes hardware and retains one local clip until explicit finish", async () => {
  const s = scene(); await s.capture.start(); s.input();
  const { fn, ms } = [...s.timers.values()][0]; assert.equal(ms, 30000); fn();
  assert.equal(s.capture.getState().status, "ready"); assert.equal(s.track.stops, 1);
  assert.ok(await s.capture.stop() instanceof ArrayBuffer); s.capture.dispose();
});
for (const action of ["cancel", "stop", "dispose", "hidden", "pagehide"]) {
  test(`${action} fences a pending permission and releases a late granted stream`, async () => {
    const gate = deferred(), s = scene({ permission: () => gate.promise });
    const pending = s.capture.start(); assert.equal(s.requests.length, 1);
    if (action === "hidden") { s.document.hidden = true; s.document.dispatch("visibilitychange"); }
    else if (action === "pagehide") s.host.dispatch("pagehide");
    else await s.capture[action]();
    assert.equal(await pending, false); gate.resolve(s.stream); await tick();
    assert.ok(s.track.stops >= 1); assert.equal(s.contexts.length, 0); assert.equal(s.capture.getLevel(), 0); s.capture.dispose();
  });
}
for (const action of ["cancel", "dispose", "hidden"]) test(`${action} fences a delayed AudioContext resume promptly`, async () => {
  const gate = deferred(), s = scene({ resume: () => gate.promise });
  const pending = s.capture.start(); await tick();
  if (action === "hidden") { s.document.hidden = true; s.document.dispatch("visibilitychange"); }
  else s.capture[action]();
  assert.equal(await pending, false); gate.resolve(); await tick();
  assert.equal(s.track.stops, 1); assert.equal(s.contexts[0].closes, 1); assert.equal(s.nodes.length, 0); s.capture.dispose();
});
test("permission refusal and invalid hardware expose fixed diagnostics, never native details", async () => {
  const refusal = Object.assign(new Error("PRIVATE_DEVICE_OR_PATH"), { name: "NotAllowedError" });
  for (const options of [{ permission: () => Promise.reject(refusal) }, { rate: 192000 }]) {
    const s = scene(options); assert.equal(await s.capture.start(), false);
    assert.equal(s.capture.getState().status, "error"); assert.ok(!JSON.stringify(s.states).includes("PRIVATE")); s.capture.dispose();
  }
});
test("hidden start, duplicate start, track loss, and disposal cannot leave a live capture", async () => {
  const s = scene(); s.document.hidden = true; assert.equal(await s.capture.start(), false); assert.equal(s.requests.length, 0);
  s.document.hidden = false; await s.capture.start(); assert.equal(await s.capture.start(), false); assert.equal(s.requests.length, 1);
  s.track.dispatch("ended"); assert.equal(s.capture.getState().status, "error"); assert.equal(s.track.stops, 1);
  s.capture.dispose(); assert.equal(await s.capture.start(), false);
  assert.ok([...s.document.handlers.values(), ...s.host.handlers.values(), ...s.track.handlers.values()].every((set) => !set.size));
});
test("a detached processor callback after cancellation cannot append or recreate capture data", async () => {
  const s = scene(); await s.capture.start(); const callback = s.contexts[0].processor.onaudioprocess;
  s.input(); s.capture.cancel();
  callback({ inputBuffer: { getChannelData() { assert.fail("Late callback must not read hardware samples"); } } });
  assert.equal(await s.capture.stop(), null); assert.equal(s.capture.getLevel(), 0); s.capture.dispose();
});
test("nonfinite hardware samples abort capture without retaining a usable WAV", async () => {
  const s = scene(); await s.capture.start(); s.input(new Float32Array([NaN]));
  assert.equal(s.capture.getState().status, "error"); assert.equal(s.track.stops, 1);
  assert.equal(await s.capture.stop(), null); s.capture.dispose();
});
