// Actual app handlers + fake DOM/WebAudio. No browser rendering/hardware evidence.
import test from "node:test";
import assert from "node:assert/strict";

let importSequence = 0;
const tick = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
function wav(frames = 100, rate = 16000) {
  const buffer = new ArrayBuffer(44 + frames * 2), view = new DataView(buffer);
  const tag = (offset, text) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)));
  tag(0, "RIFF"); view.setUint32(4, buffer.byteLength - 8, true); tag(8, "WAVE");
  tag(12, "fmt "); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  tag(36, "data"); view.setUint32(40, frames * 2, true);
  for (let i = 0; i < frames; i++) view.setInt16(44 + i * 2, 8192, true);
  return buffer;
}
const file = (buffer = wav()) => ({ size: buffer.byteLength, arrayBuffer: async () => buffer,
  get name() { throw new Error("PRIVATE_FILE_NAME"); } });
class Element {
  constructor(id = "") {
    this.id = id; this.handlers = new Map(); this.attributes = new Map(); this.dataset = {};
    this.children = []; this.hidden = false;
    this.disabled = ["presence-play", "presence-stop", "presence-clear"].includes(id); this.checked = false;
    this.open = false; this.textContent = ""; this.files = []; this.isConnected = true;
    this.classList = { toggle() {} }; this._value = "";
  }
  get value() { return this._value; }
  set value(value) { this._value = String(value); if (this.id === "presence-audio-file" && !value) this.files = []; }
  addEventListener(name, callback) { const handlers = this.handlers.get(name) ?? []; handlers.push(callback); this.handlers.set(name, handlers); }
  async dispatch(name, extra = {}) { await Promise.all((this.handlers.get(name) ?? []).map((cb) => cb({ target: this, preventDefault() {}, ...extra }))); }
  setAttribute(name, value) { this.attributes.set(name, value); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  focus() {} select() {} getContext() { return null; } showModal() { this.open = true; } close() { this.open = false; }
}
async function withApp(run, { resume = () => Promise.resolve(), makeError = false } = {}) {
  const keys = ["document", "window", "performance", "fetch", "AudioContext", "localStorage", "sessionStorage", "navigator"];
  const saved = new Map(keys.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const nodes = new Map(), contexts = [], sources = [], timers = new Map();
  const node = (id) => { if (!nodes.has(id)) nodes.set(id, new Element(id)); return nodes.get(id); };
  const windowEvents = new Element("window"), documentEvents = new Element("document");
  let timerSequence = 0, forbiddenIO = 0;
  const forbidden = () => { forbiddenIO++; throw new Error("PRIVATE_FORBIDDEN_IO"); };
  const document = { hidden: false, getElementById: node, querySelector: node, querySelectorAll: () => [],
    createElement: () => new Element(), addEventListener: documentEvents.addEventListener.bind(documentEvents) };
  const window = { location: { hash: "#conversation" },
    setInterval(callback) { timers.set(++timerSequence, callback); return timerSequence; },
    clearInterval(id) { timers.delete(id); }, addEventListener: windowEvents.addEventListener.bind(windowEvents) };
  class AudioContext {
    constructor() {
      if (makeError) throw new Error("PRIVATE_AUDIO_DRIVER");
      this.state = "running"; this.destination = {}; this.closeCount = 0; this.buffers = [];
      contexts.push(this);
    }
    resume() { return resume(); }
    close() { this.closeCount++; return Promise.resolve(); }
    createBuffer(channels, frames, rate) {
      const values = Array.from({ length: channels }, () => new Float32Array(frames));
      const buffer = { frames, channels, rate, getChannelData: (channel) => values[channel] };
      this.buffers.push(buffer); return buffer;
    }
    createAnalyser() { return { fftSize: 0, connect() {}, disconnect() {}, getFloatTimeDomainData(values) { values.fill(0.2); } }; }
    createBufferSource() {
      const source = { starts: 0, stops: 0, onended: null, connect() {}, disconnect() {},
        start() { this.starts++; }, stop() { this.stops++; } };
      sources.push(source); return source;
    }
  }
  const values = { document, window, performance: { now: () => 0 }, fetch: forbidden, AudioContext,
    localStorage: { setItem: forbidden, getItem: forbidden }, sessionStorage: { setItem: forbidden, getItem: forbidden },
    navigator: { mediaDevices: { getUserMedia: forbidden }, clipboard: { writeText: forbidden } } };
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
  try {
    await import(`../app.mjs?local-playback-app=${++importSequence}`);
    const initialMessages = JSON.stringify(node("messages").children);
    const app = { node, contexts, sources, initialMessages, starts: () => sources.reduce((sum, item) => sum + item.starts, 0),
      async select(selected = file()) {
        node("presence-audio-file").files = selected ? [selected] : [];
        node("presence-audio-file").value = selected ? "PRIVATE_NATIVE_NAME.wav" : "";
        await node("presence-audio-file").dispatch("change"); await tick();
      },
      click(id) { return node(id).dispatch("click"); },
      page(name, persisted = false) { return windowEvents.dispatch(name, { persisted }); },
      async hide(hidden = true) { document.hidden = hidden; await documentEvents.dispatch("visibilitychange"); },
      unchanged() { assert.equal(JSON.stringify(node("messages").children), initialMessages); },
    };
    await run(app); app.unchanged(); assert.equal(forbiddenIO, 0);
    await windowEvents.dispatch("pagehide", { persisted: false }); assert.equal(timers.size, 0);
  } finally {
    for (const [key, descriptor] of saved) { if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key]; }
  }
}

test("native selection clears filename before reading and never autoplays or changes conversation", async () => {
  await withApp(async (app) => {
    assert.equal(app.node("presence-play").disabled, true);
    const buffer = wav(); let cleared = false;
    await app.select({ size: buffer.byteLength, arrayBuffer() { cleared = app.node("presence-audio-file").value === ""; return Promise.resolve(buffer); } });
    assert.equal(cleared, true); assert.equal(app.node("presence-audio-file").value, "");
    assert.equal(app.node("presence-play").disabled, false); assert.equal(app.contexts.length, 0);
    assert.match(app.node("presence-audio-notice").textContent, /WAV pronto/); app.unchanged();
  });
});

test("the same native File can be deliberately selected twice without remembered filename", async () => {
  await withApp(async (app) => {
    const buffer = wav(); let reads = 0;
    const selected = { size: buffer.byteLength, arrayBuffer: async () => { reads++; return buffer; } };
    await app.select(selected); await app.select(selected);
    assert.equal(reads, 2); assert.equal(app.node("presence-audio-file").value, "");
    assert.equal(app.contexts.length, 0); assert.equal(app.node("presence-play").disabled, false);
  });
});

test("cancelled native picker preserves current ready selection without clearing it", async () => {
  await withApp(async (app) => {
    await app.select(); const notice = app.node("presence-audio-notice").textContent;
    await app.select(null); assert.equal(app.node("presence-audio-notice").textContent, notice);
    assert.equal(app.node("presence-play").disabled, false); await app.click("presence-play");
    assert.equal(app.starts(), 1);
  });
});

test("explicit play updates real-amplitude label and stop returns ready without a Core request", async () => {
  await withApp(async (app) => {
    await app.select(); await app.click("presence-play");
    assert.equal(app.starts(), 1); assert.match(app.node("presence-status").textContent, /amplitude real/);
    await app.click("presence-stop"); assert.equal(app.sources[0].stops, 1);
    assert.equal(app.node("presence-play").disabled, false); assert.match(app.node("presence-status").textContent, /repouso/);
    app.unchanged();
  });
});

for (const action of ["stop", "clear", "reset", "pagehide", "bfcache", "visibility"]) {
  test(`${action} while starting prevents a late source and keeps fixture conversation intact`, async () => {
    const gate = deferred();
    await withApp(async (app) => {
      await app.select(); const pending = app.click("presence-play"); await tick();
      assert.match(app.node("presence-audio-notice").textContent, /Preparando/);
      if (action === "pagehide" || action === "bfcache") await app.page("pagehide", action === "bfcache");
      else if (action === "visibility") await app.hide();
      else await app.click(action === "reset" ? "reset" : `presence-${action}`);
      gate.resolve(); await pending; await tick(); assert.equal(app.starts(), 0);
      if (!["stop", "visibility"].includes(action)) {
        assert.equal(app.contexts[0].closeCount, 1); assert.equal(app.node("presence-audio-file").value, "");
        assert.equal(app.node("presence-play").disabled, true);
      }
      app.unchanged();
    }, { resume: () => gate.promise });
  });
}

test("BFcache restore requires a new local selection and a fresh explicit play", async () => {
  await withApp(async (app) => {
    await app.select(); await app.click("presence-play"); await app.page("pagehide", true);
    assert.equal(app.contexts[0].closeCount, 1); await app.page("pageshow", true);
    assert.equal(app.node("presence-play").disabled, true);
    await app.select(); assert.equal(app.starts(), 1); await app.click("presence-play");
    assert.equal(app.starts(), 2); assert.equal(app.contexts.length, 2);
  });
});

test("clear while reading erases selection and stale read cannot restore ready", async () => {
  await withApp(async (app) => {
    const gate = deferred(), buffer = wav();
    const pending = app.select({ size: buffer.byteLength, arrayBuffer: () => gate.promise });
    await tick(); await app.click("presence-clear"); gate.resolve(buffer); await pending; await tick();
    assert.equal(app.node("presence-play").disabled, true); assert.equal(app.contexts.length, 0);
    assert.match(app.node("presence-audio-notice").textContent, /Nenhum áudio/);
  });
});

test("invalid file input error is sanitized and the 600-second UI limit is current", async () => {
  await withApp(async (app) => {
    await app.select({ size: 44, arrayBuffer() { throw new Error("PRIVATE_WAV_CONTENT_PATH"); } });
    const notice = app.node("presence-audio-notice").textContent;
    assert.ok(!notice.includes("PRIVATE_")); assert.match(notice, /600 s/);
    assert.equal(app.node("presence-play").disabled, true); assert.equal(app.contexts.length, 0);
    assert.equal(app.node("presence-audio-file").value, "");
  });
});

test("WebAudio construction errors remain sanitized instead of exposing driver/path details", async () => {
  await withApp(async (app) => {
    await app.select(); await app.click("presence-play");
    assert.equal(app.node("presence-play").disabled, true);
    assert.ok(!app.node("presence-audio-notice").textContent.includes("PRIVATE_AUDIO_DRIVER"));
    assert.match(app.node("presence-audio-notice").textContent, /indisponível/);
  }, { makeError: true });
});

test("UI stop during cooperative PCM conversion prevents the late start", async () => {
  await withApp(async (app) => {
    await app.select(file(wav(33000))); const pending = app.click("presence-play"); await tick();
    assert.match(app.node("presence-audio-notice").textContent, /Preparando/);
    await app.click("presence-stop"); await pending;
    assert.equal(app.starts(), 0); assert.equal(app.node("presence-play").disabled, false);
    assert.match(app.node("presence-status").textContent, /repouso/);
  });
});

test("native aggregate longer than 120s is selectable under the 600s contract", async () => {
  await withApp(async (app) => {
    await app.select(file(wav(121 * 8000, 8000)));
    assert.equal(app.node("presence-play").disabled, false);
    assert.match(app.node("presence-audio-notice").textContent, /WAV pronto/);
    assert.equal(app.contexts.length, 0); assert.equal(app.starts(), 0);
  });
});
