// Public local player + public sphere; controlled WebAudio/DOM/RAF boundaries.
// This verifies wiring and lifecycle, not real hardware or browser rendering.
import test from "node:test";
import assert from "node:assert/strict";
import { createLivePresence } from "../live-presence.mjs";

const deferred = () => {
  let resolve; const promise = new Promise((yes) => { resolve = yes; });
  return { promise, resolve };
};
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
function wav({ sample = 8192, frames = 80 } = {}) {
  const buffer = new ArrayBuffer(44 + frames * 2), view = new DataView(buffer);
  const tag = (offset, value) => [...value].forEach((letter, i) => view.setUint8(offset + i, letter.charCodeAt(0)));
  tag(0, "RIFF"); tag(8, "WAVE"); tag(12, "fmt "); tag(36, "data");
  view.setUint32(4, buffer.byteLength - 8, true); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, 8000, true); view.setUint32(28, 16000, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  view.setUint32(40, frames * 2, true);
  for (let i = 0; i < frames; i++) view.setInt16(44 + i * 2, sample, true);
  return buffer;
}
const file = (buffer = wav()) => ({
  size: buffer.byteLength, arrayBuffer: async () => buffer,
  get name() { assert.fail("Local filename must not be read or reflected"); },
});
class Element {
  constructor() {
    this.listeners = new Map(); this.attributes = new Map(); this.files = [];
    this.textContent = ""; this.disabled = false; this.open = false; this._value = "";
  }
  get value() { return this._value; }
  set value(value) { this._value = value; if (!value) this.files = []; }
  addEventListener(name, fn) {
    const group = this.listeners.get(name) ?? new Set(); group.add(fn); this.listeners.set(name, group);
  }
  removeEventListener(name, fn) { this.listeners.get(name)?.delete(fn); }
  async dispatch(name, extra = {}) {
    await Promise.all([...(this.listeners.get(name) ?? [])].map((fn) => fn({ target: this, ...extra })));
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  getAttribute(name) { return this.attributes.get(name); }
  focus(...args) { this.focused = true; this.focusArguments = args; }
}
function scene({ reduced = false, resume = () => Promise.resolve(), makeError = false,
  getVoiceLevel = () => 0 } = {}) {
  const nodes = new Map(), frames = new Map(), contexts = [], sources = [];
  let sequence = 0, now = 0, forbiddenCalls = 0;
  const node = (id) => { if (!nodes.has(id)) nodes.set(id, new Element()); return nodes.get(id); };
  const document = new Element(); document.hidden = false; document.getElementById = node;
  const media = new Element(); media.matches = reduced;
  const canvas = node("live-particle-sphere"); canvas.localName = "canvas"; canvas.clientWidth = 320;
  canvas.getContext = () => ({ setTransform() {}, clearRect() {}, fillRect() {}, beginPath() {},
    moveTo() {}, lineTo() {}, stroke() {}, createRadialGradient: () => ({ addColorStop() {} }) });
  const forbidden = () => { forbiddenCalls++; assert.fail("No network, capture, storage, or synthesis"); };
  class AudioContext {
    constructor() {
      if (makeError) throw new Error("PRIVATE_AUDIO_DEVICE_PATH");
      contexts.push(this); this.state = "running"; this.destination = {}; this.closes = 0;
    }
    resume() { return resume(); }
    close() { this.closes++; this.state = "closed"; return Promise.resolve(); }
    createBuffer(channels, count) {
      const data = Array.from({ length: channels }, () => new Float32Array(count));
      return { getChannelData: (index) => data[index] };
    }
    createAnalyser() {
      return { connect() {}, disconnect() {}, getFloatTimeDomainData(values) {
        // Samples come from PCM converted by the actual public player.
        const pcm = sources.at(-1)?.buffer.getChannelData(0);
        for (let i = 0; i < values.length; i++) values[i] = pcm?.[i % pcm.length] ?? 0;
      } };
    }
    createBufferSource() {
      const source = { starts: 0, stops: 0, onended: null, connect() {}, disconnect() {},
        start() { this.starts++; }, stop() { this.stops++; } };
      sources.push(source); return source;
    }
  }
  const host = { document, AudioContext, devicePixelRatio: 1, matchMedia: () => media,
    requestAnimationFrame(fn) { frames.set(++sequence, fn); return sequence; },
    cancelAnimationFrame(key) { frames.delete(key); }, fetch: forbidden,
    navigator: { mediaDevices: { getUserMedia: forbidden } }, speechSynthesis: { speak: forbidden },
    localStorage: { getItem: forbidden, setItem: forbidden }, sessionStorage: { getItem: forbidden, setItem: forbidden } };
  const presence = createLivePresence({ document, host, getVoiceLevel,
    yieldTask: () => Promise.resolve() });
  return { presence, document, node, canvas, media, frames, sources, contexts,
    forbiddenCalls: () => forbiddenCalls,
    step() {
      assert.equal(frames.size, 1, "One visual animation loop only");
      const [id, callback] = frames.entries().next().value; frames.delete(id); callback(now += 40);
    },
    click: (id) => node(id).dispatch("click"),
    async select(selected = file()) {
      const input = node("live-audio-file"); input.files = selected ? [selected] : [];
      input._value = selected ? "PRIVATE_NATIVE_FILE.wav" : "";
      await input.dispatch("change"); await tick();
    },
    starts: () => sources.reduce((total, source) => total + source.starts, 0),
  };
}

test("canonical speech drives the same sphere from real output RMS, with zero silence/stop", () => {
  let amplitude = .28;
  const s = scene({ getVoiceLevel: () => amplitude });
  try {
    s.presence.update({ paired: true, status: "completed" });
    s.presence.setConversationState("playing"); s.step();
    assert.equal(s.canvas.getAttribute("data-visual-mode"), "speaking_local");
    assert.ok(Number(s.canvas.getAttribute("data-visual-level")) > 0);
    assert.match(s.node("live-presence-status").textContent, /final do Core/);
    amplitude = 0; for (let i = 0; i < 30; i++) s.step();
    assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
    amplitude = .5; s.presence.setConversationState("idle"); s.step();
    assert.equal(s.canvas.getAttribute("data-visual-mode"), "idle");
    assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
    assert.equal(s.forbiddenCalls(), 0);
  } finally { s.presence.dispose(); }
});

test("microphone state is honest text and never simulates JARVIS speaking", () => {
  const s = scene({ getVoiceLevel: () => .9 });
  try {
    s.presence.setConversationState("recording"); s.step();
    assert.match(s.node("live-presence-status").textContent, /Microfone ativo/);
    assert.notEqual(s.canvas.getAttribute("data-visual-mode"), "speaking_local");
    assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  } finally { s.presence.dispose(); }
});
function assertClosed(s) {
  s.presence.dispose(); assert.equal(s.frames.size, 0); assert.equal(s.forbiddenCalls(), 0);
}

test("missing presentation canvas is inert and does not construct audio or bind controls", () => {
  for (const canvas of [null, {}, { localName: "div", getContext() { assert.fail("Not a canvas"); } }]) {
    let calls = 0;
    const presence = createLivePresence({ document: { getElementById: () => canvas },
      createSphere() { calls++; }, createPlayback() { calls++; } });
    presence.update({ status: "waiting", paired: true }); presence.clear(); presence.pageHide();
    presence.refresh(); presence.dispose(); assert.equal(calls, 0);
  }
});

test("native selection removes filename before reading and requires a separate play gesture", async () => {
  const s = scene(); const buffer = wav(); let cleared = false;
  assert.equal(s.node("live-audio-play").disabled, true);
  await s.select({ size: buffer.byteLength, get name() { assert.fail("Filename read"); },
    arrayBuffer() { cleared = s.node("live-audio-file").value === ""; return Promise.resolve(buffer); } });
  assert.equal(cleared, true); assert.equal(s.node("live-audio-file").value, "");
  assert.equal(s.node("live-audio-play").disabled, false);
  assert.equal(s.contexts.length, 0); assert.equal(s.starts(), 0);
  s.presence.update({ status: "completed", paired: true }); assert.equal(s.starts(), 0);
  assert.match(s.node("live-audio-notice").textContent, /WAV pronto/); assertClosed(s);
});

test("the real local player drives sphere RMS for nonzero PCM and silence remains zero", async () => {
  for (const sample of [0, 8192]) {
    const s = scene(); await s.select(file(wav({ sample })));
    await s.click("live-audio-play"); assert.equal(s.starts(), 1); s.step();
    assert.equal(s.sources[0].buffer.getChannelData(0)[0], sample / 32768);
    assert.equal(s.canvas.getAttribute("data-visual-mode"), "speaking_local");
    const level = Number(s.canvas.getAttribute("data-visual-level"));
    if (sample === 0) assert.equal(level, 0);
    else assert.ok(level > 0 && level <= 1);
    assert.match(s.node("live-presence-status").textContent, /amplitude real · sem microfone/);
    await s.click("live-audio-stop"); s.step();
    assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
    assert.equal(s.canvas.getAttribute("data-visual-mode"), "idle");
    assert.equal(s.sources[0].stops, 1); assertClosed(s);
  }
});

test("Core updates are visual only: busy, error, paired idle, never fictitious listening or speech", () => {
  const s = scene();
  for (const status of ["connecting", "submitting", "waiting"]) {
    s.presence.update({ status, paired: true }); s.step();
    assert.equal(s.canvas.getAttribute("data-visual-mode"), "thinking");
  }
  s.presence.update({ status: "failed", paired: true, errorCode: "PRIVATE_ERROR" }); s.step();
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "error");
  assert.ok(!s.node("live-presence-status").textContent.includes("PRIVATE_ERROR"));
  s.presence.update({ status: "completed", paired: true }); s.step();
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "idle");
  assert.equal(s.contexts.length, 0); assertClosed(s);
});

test("opening audio controls uses default scrolling focus without selecting, capturing, or autoplay", async () => {
  const s = scene(); await s.click("live-audio-open");
  assert.equal(s.node("live-audio-panel").open, true);
  assert.equal(s.node("live-audio-file").focused, true);
  assert.deepEqual(s.node("live-audio-file").focusArguments, [],
    "Native focus must be allowed to reveal the WAV input on narrow/zoomed layouts");
  assert.equal(s.contexts.length, 0); assert.equal(s.starts(), 0);
  assert.match(s.node("live-audio-notice").textContent, /Sem microfone/); assertClosed(s);
});

test("cancelled picker preserves ready selection; repeated selection is deliberate without remembered names", async () => {
  const s = scene(); const buffer = wav(); let reads = 0;
  const selected = { size: buffer.byteLength, arrayBuffer: async () => { reads++; return buffer; } };
  await s.select(selected); const notice = s.node("live-audio-notice").textContent;
  await s.select(null); assert.equal(s.node("live-audio-notice").textContent, notice);
  await s.select(selected); assert.equal(reads, 2); assert.equal(s.starts(), 0);
  await s.click("live-audio-play"); assert.equal(s.starts(), 1); assertClosed(s);
});

test("a replacement remains selected after the older file read resolves late", async () => {
  const s = scene(), gate = deferred(), old = wav({ sample: 1000 });
  const first = s.select({ size: old.byteLength, arrayBuffer: () => gate.promise });
  await tick(); await s.select(file(wav({ sample: 2000 })));
  gate.resolve(old); await first;
  assert.equal(s.canvas.getAttribute("data-audio-state"), "ready");
  await s.click("live-audio-play");
  assert.equal(s.sources[0].buffer.getChannelData(0)[0], 2000 / 32768); assertClosed(s);
});

test("natural audio end returns to the current Core state without implying speech synthesis", async () => {
  const s = scene(); await s.select(); s.presence.update({ status: "waiting", paired: true });
  await s.click("live-audio-play"); s.step();
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "speaking_local");
  s.sources[0].onended(); s.step();
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "thinking");
  assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  assert.equal(s.node("live-audio-play").disabled, false);
  assert.equal(s.starts(), 1); assertClosed(s);
});

for (const action of ["stop", "clear", "pageHide", "dispose"]) {
  test(`${action} invalidates a pending file read without a stale ready state`, async () => {
    const s = scene(), gate = deferred(), buffer = wav();
    const selecting = s.select({ size: buffer.byteLength, arrayBuffer: () => gate.promise });
    await tick();
    if (action === "stop") await s.click("live-audio-stop");
    else s.presence[action]();
    gate.resolve(buffer); await selecting; assert.equal(s.contexts.length, 0); assert.equal(s.starts(), 0);
    if (action !== "dispose") {
      assert.equal(s.node("live-audio-play").disabled, true);
      assert.equal(s.canvas.getAttribute("data-audio-state"), "empty");
    }
    assertClosed(s);
  });
}

for (const action of ["stop", "clear", "pageHide", "dispose", "hidden"]) {
  test(`${action} during AudioContext resume prevents a late source from starting`, async () => {
    const gate = deferred(), s = scene({ resume: () => gate.promise });
    await s.select(); const playing = s.click("live-audio-play"); await tick();
    assert.equal(s.canvas.getAttribute("data-audio-state"), "starting");
    if (action === "stop") await s.click("live-audio-stop");
    else if (action === "hidden") { s.document.hidden = true; await s.document.dispatch("visibilitychange"); }
    else s.presence[action]();
    gate.resolve(); await playing; assert.equal(s.starts(), 0);
    if (["clear", "pageHide", "dispose"].includes(action)) assert.equal(s.contexts[0].closes, 1);
    assertClosed(s);
  });
}

test("page hide closes local audio and animation; BFCache refresh does not restore or autoplay it", async () => {
  const s = scene(); await s.select(); await s.click("live-audio-play"); s.step();
  const oldEnded = s.sources[0].onended;
  s.presence.pageHide(); assert.equal(s.frames.size, 0); assert.equal(s.contexts[0].closes, 1);
  assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  oldEnded(); s.presence.refresh(); assert.equal(s.frames.size, 1); s.step();
  assert.equal(s.node("live-audio-play").disabled, true); assert.equal(s.starts(), 1);
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "idle");
  await s.click("live-audio-play"); assert.equal(s.starts(), 1);
  await s.select(); assert.equal(s.starts(), 1); await s.click("live-audio-play");
  assert.equal(s.starts(), 2); assert.equal(s.contexts.length, 2); assertClosed(s);
});

test("hidden visibility stops audio and RAF; returning does not resume audio", async () => {
  const s = scene(); await s.select(); await s.click("live-audio-play");
  s.document.hidden = true; await s.document.dispatch("visibilitychange");
  assert.equal(s.frames.size, 0); assert.equal(s.sources[0].stops, 1);
  assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  s.document.hidden = false; await s.document.dispatch("visibilitychange");
  assert.equal(s.frames.size, 1); s.step(); assert.equal(s.starts(), 1);
  assert.equal(s.canvas.getAttribute("data-visual-mode"), "idle"); assertClosed(s);
});

test("manual pause and reduced motion keep the sphere static without breaking explicit local audio", async () => {
  const s = scene({ reduced: true }); assert.equal(s.frames.size, 0);
  await s.select(); await s.click("live-audio-play"); assert.equal(s.starts(), 1);
  assert.equal(s.frames.size, 0); assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  s.media.matches = false; await s.media.dispatch("change"); assert.equal(s.frames.size, 1);
  await s.click("live-motion"); assert.equal(s.frames.size, 0);
  assert.equal(s.node("live-motion").getAttribute("aria-pressed"), "true");
  s.presence.pageHide(); s.presence.refresh(); assert.equal(s.frames.size, 0);
  await s.click("live-motion"); assert.equal(s.frames.size, 1); assertClosed(s);
});

test("clear disconnects audio; permanent disposal removes listeners and cannot be revived", async () => {
  const s = scene(); await s.select(); await s.click("live-audio-play");
  s.presence.clear(); s.step(); assert.equal(s.contexts[0].closes, 1);
  assert.equal(s.node("live-audio-play").disabled, true);
  assert.equal(s.canvas.getAttribute("data-visual-level"), "0");
  s.presence.dispose(); s.presence.dispose(); s.presence.refresh();
  s.presence.update({ status: "waiting", paired: true }); await s.select(); await s.click("live-audio-play");
  assert.equal(s.frames.size, 0); assert.equal(s.starts(), 1);
  assert.ok([...s.document.listeners.values()].every((handlers) => handlers.size === 0));
  assert.ok([...s.media.listeners.values()].every((handlers) => handlers.size === 0));
  for (const id of ["live-motion", "live-audio-open", "live-audio-file", "live-audio-play", "live-audio-stop", "live-audio-clear"])
    assert.ok([...s.node(id).listeners.values()].every((handlers) => handlers.size === 0));
  assert.equal(s.forbiddenCalls(), 0);
});

test("invalid files and audio device failures expose only fixed local diagnostics", async () => {
  for (const makeError of [false, true]) {
    const s = scene({ makeError });
    if (makeError) { await s.select(); await s.click("live-audio-play"); }
    else await s.select({ size: 44, arrayBuffer() { throw new Error("PRIVATE_FILE_PATH"); } });
    assert.equal(s.canvas.getAttribute("data-audio-state"), "error");
    assert.match(s.node("live-audio-notice").textContent, /600 s \/ 32 MiB/);
    assert.ok(!s.node("live-audio-notice").textContent.includes("PRIVATE_"));
    assert.equal(s.node("live-audio-play").disabled, true); assert.equal(s.starts(), 0);
    assertClosed(s);
  }
});
