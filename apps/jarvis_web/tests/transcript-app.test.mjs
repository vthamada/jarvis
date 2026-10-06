// Exercise actual app handlers. Fake DOM supplies browser normalization and events,
// not an alternate transcript implementation, network transport or Core fixture.
import test from "node:test";
import assert from "node:assert/strict";

let importSequence = 0;
const encoder = new TextEncoder();
const source = (text = "  Olá\r\nJARVIS\r😀  ") => encoder.encode(JSON.stringify({
  review_required: true, language: "Portuguese", audio_duration_seconds: 10,
  segments: [{ start_seconds: 0, end_seconds: 7, timestamps_estimated: false, text }],
}));
const file = (data = source()) => ({ size: data.length, arrayBuffer: async () => data.slice().buffer });
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
};

class FakeElement {
  constructor(id = "") {
    this.id = id; this.handlers = new Map(); this.attributes = new Map();
    this.dataset = {}; this.children = []; this.hidden = false; this.disabled = false;
    this.checked = false; this.open = false; this.textContent = "";
    this.files = []; this.isConnected = true; this.focusCount = 0; this.selectCount = 0;
    this.classList = { toggle() {} };
    this._value = "";
  }
  get value() { return this._value; }
  set value(value) {
    this._value = this.id === "transcript-text" ? String(value).replace(/\r\n?/gu, "\n") : String(value);
  }
  addEventListener(name, callback) {
    const listeners = this.handlers.get(name) ?? [];
    listeners.push(callback); this.handlers.set(name, listeners);
  }
  async dispatch(name, extra = {}) {
    const event = { target: this, preventDefault() {}, ...extra };
    await Promise.all((this.handlers.get(name) ?? []).map((callback) => callback(event)));
  }
  setAttribute(name, value) { this.attributes.set(name, value); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = [...children]; }
  focus() { this.focusCount += 1; }
  select() { this.selectCount += 1; }
  getContext() { return null; } // No animation/hardware needed for transcript wiring.
  showModal() { this.open = true; }
  close() { this.open = false; }
}

async function withApp(run) {
  const saved = new Map(["document", "window", "performance", "fetch", "AudioContext"].map((key) =>
    [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const nodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, new FakeElement(id));
    return nodes.get(id);
  };
  const windowEvents = new FakeElement("window");
  const documentEvents = new FakeElement("document");
  let time = 0, timerSequence = 0, prohibitedIO = 0;
  const timers = new Map();
  const document = {
    hidden: false, getElementById: node, querySelector: node, querySelectorAll: () => [],
    createElement: () => new FakeElement(),
    addEventListener: documentEvents.addEventListener.bind(documentEvents),
  };
  const window = {
    location: { hash: "#conversation" },
    setInterval(callback, delay) { assert.equal(delay, 1000); timers.set(++timerSequence, callback); return timerSequence; },
    clearInterval(id) { timers.delete(id); },
    addEventListener: windowEvents.addEventListener.bind(windowEvents),
  };
  const values = { document, window, performance: { now: () => time },
    fetch() { prohibitedIO += 1; throw new Error("network forbidden"); },
    AudioContext: class { constructor() { prohibitedIO += 1; throw new Error("audio forbidden"); } } };
  for (const [key, value] of Object.entries(values)) {
    Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
  }
  try {
    await import(`../app.mjs?transcript-app-test=${++importSequence}`);
    const initialMessages = JSON.stringify(node("messages").children);
    const rig = {
      node, timers, initialMessages,
      time(value) { time = value; },
      tick() { for (const callback of [...timers.values()]) callback(); },
      page(name, persisted = false) { return windowEvents.dispatch(name, { persisted }); },
      async consent(granted = true) {
        node("transcript-consent").checked = granted;
        await node("transcript-consent").dispatch("change");
      },
      async import(selected = file()) {
        node("transcript-file").files = [selected];
        node("transcript-file").value = "synthetic.json";
        await node("transcript-file").dispatch("change");
      },
      async ready(data = source()) { await this.consent(); await this.import(file(data)); },
      submit() { return node("transcript-form").dispatch("submit"); },
    };
    await run(rig);
    assert.equal(prohibitedIO, 0);
    await windowEvents.dispatch("pagehide", { persisted: false });
    assert.equal(timers.size, 0);
  } finally {
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
}

test("app starts closed and unauthorized file handler performs zero file IO", async () => {
  await withApp(async ({ node, import: importFile, initialMessages }) => {
    assert.equal(node("transcript-file").disabled, true);
    assert.equal(node("transcript-export").disabled, true);
    assert.equal(node("transcript-form").hidden, true);
    let reads = 0;
    await importFile({ size: 100, arrayBuffer() { reads += 1; throw new Error("forbidden"); } });
    assert.equal(reads, 0);
    assert.equal(node("transcript-file").value, "");
    assert.equal(JSON.stringify(node("messages").children), initialMessages);
  });
});

test("untouched textarea exports original CRLF/CR without sending fixture conversation", async () => {
  await withApp(async (app) => {
    const originalText = "  Olá\r\nJARVIS\r😀  ";
    await app.ready(source(originalText));
    assert.equal(app.node("transcript-text").value, originalText.replace(/\r\n?/gu, "\n"));
    assert.equal(app.node("transcript-form").hidden, false);
    assert.equal(app.node("transcript-file").value, "");
    await app.submit();
    const output = JSON.parse(app.node("transcript-package").value);
    assert.equal(output.reviewed_text, originalText);
    assert.equal(output.review_revision, 1);
    assert.equal(output.document_utf8_b64, Buffer.from(source(originalText)).toString("base64"));
    assert.equal(app.node("transcript-text").value, "");
    assert.equal(app.node("transcript-output").hidden, false);
    assert.equal(app.node("transcript-select").focusCount, 1);
    await app.node("transcript-select").dispatch("click");
    assert.equal(app.node("transcript-package").selectCount, 1);
    assert.equal(JSON.stringify(app.node("messages").children), app.initialMessages);
  });
});

test("invalid draft stays visible across timer and blocks even direct submit callback", async () => {
  await withApp(async (app) => {
    await app.ready();
    const previous = app.node("transcript-text").value;
    app.node("transcript-text").value = "bad\u0007text";
    await app.node("transcript-text").dispatch("input"); app.tick();
    assert.equal(app.node("transcript-text").value, "bad\u0007text");
    assert.equal(app.node("transcript-export").disabled, true);
    assert.match(app.node("transcript-notice").textContent, /Texto recusado/);
    // Disabled UI isn't the handler's authority boundary. A submit event must
    // remain refused until an actual valid input explicitly creates a revision.
    app.node("transcript-text").value = previous;
    await app.submit();
    assert.equal(app.node("transcript-package").value, "");
    assert.match(app.node("transcript-state").textContent, /reviewed/);
  });
});

test("valid correction after invalid draft clears block and exports explicit revised text", async () => {
  await withApp(async (app) => {
    await app.ready(); app.node("transcript-text").value = "";
    await app.node("transcript-text").dispatch("input");
    app.node("transcript-text").value = "  corrected\n text 😀  ";
    await app.node("transcript-text").dispatch("input"); app.tick();
    assert.equal(app.node("transcript-export").disabled, false);
    await app.submit();
    const output = JSON.parse(app.node("transcript-package").value);
    assert.equal(output.review_revision, 2);
    assert.equal(output.reviewed_text, "  corrected\n text 😀  ");
  });
});

test("timer renders local expiry and erases review/invalid draft from DOM", async () => {
  await withApp(async (app) => {
    await app.ready(); app.node("transcript-text").value = "invalid\u0000";
    await app.node("transcript-text").dispatch("input");
    app.time(120000); app.tick();
    assert.equal(app.node("transcript-text").value, "");
    assert.equal(app.node("transcript-form").hidden, true);
    assert.equal(app.node("transcript-export").disabled, true);
    assert.match(app.node("transcript-state").textContent, /expired/);
    await app.submit(); assert.equal(app.node("transcript-package").value, "");
  });
});

test("cancel during actual pending file handler cannot restore source to DOM", async () => {
  await withApp(async (app) => {
    await app.consent(); const wait = deferred();
    const pending = app.import({ size: source().length, arrayBuffer: () => wait.promise });
    assert.match(app.node("transcript-state").textContent, /loading/);
    await app.node("transcript-cancel").dispatch("click");
    wait.resolve(source().buffer); await pending; app.tick();
    assert.equal(app.node("transcript-text").value, "");
    assert.equal(app.node("transcript-package").value, "");
    assert.match(app.node("transcript-state").textContent, /cancelled/);
  });
});

test("revocation while real export awaits crypto never displays stale package", async () => {
  await withApp(async (app) => {
    await app.ready(); const gate = deferred();
    const original = globalThis.crypto.subtle.digest;
    globalThis.crypto.subtle.digest = async function (...args) {
      await gate.promise; return original.apply(this, args);
    };
    try {
      const pending = app.submit();
      assert.match(app.node("transcript-state").textContent, /exporting/);
      await app.consent(false); gate.resolve(); await pending;
      assert.equal(app.node("transcript-package").value, "");
      assert.equal(app.node("transcript-output").hidden, true);
      assert.equal(app.node("transcript-text").value, "");
      assert.match(app.node("transcript-state").textContent, /revoked/);
    } finally { globalThis.crypto.subtle.digest = original; }
  });
});

test("BFcache restore clears package/consent and restarts exactly one deadline timer", async () => {
  await withApp(async (app) => {
    await app.ready(); await app.submit();
    assert.ok(app.node("transcript-package").value);
    await app.page("pagehide", true);
    assert.equal(app.timers.size, 0);
    assert.equal(app.node("transcript-package").value, "");
    assert.equal(app.node("transcript-consent").checked, false);
    await app.page("pageshow", true); await app.page("pageshow", true);
    assert.equal(app.timers.size, 1);
    assert.equal(app.node("transcript-file").disabled, true);
    await app.ready(source("new deliberate review")); await app.submit();
    assert.equal(JSON.parse(app.node("transcript-package").value).reviewed_text, "new deliberate review");
  });
});

test("permanent pagehide clears package and disposes pending review", async () => {
  await withApp(async (app) => {
    await app.ready(); await app.page("pagehide", false);
    assert.equal(app.timers.size, 0);
    assert.equal(app.node("transcript-text").value, "");
    assert.equal(app.node("transcript-consent").checked, false);
    assert.match(app.node("transcript-state").textContent, /disposed/);
    await app.submit(); assert.equal(app.node("transcript-package").value, "");
  });
});

test("concurrent form callbacks yield only one package and never fixture submission", async () => {
  await withApp(async (app) => {
    await app.ready(); await Promise.all([app.submit(), app.submit()]);
    assert.equal(JSON.parse(app.node("transcript-package").value).review_revision, 1);
    assert.equal(app.node("transcript-select").focusCount, 1);
    assert.equal(JSON.stringify(app.node("messages").children), app.initialMessages);
  });
});

test("reset conversation also clears prepared local package and requires fresh consent", async () => {
  await withApp(async (app) => {
    await app.ready(); await app.submit(); await app.node("reset").dispatch("click");
    assert.equal(app.node("transcript-package").value, "");
    assert.equal(app.node("transcript-output").hidden, true);
    assert.equal(app.node("transcript-consent").checked, false);
    assert.equal(app.node("transcript-file").disabled, true);
    assert.match(app.node("transcript-state").textContent, /idle/);
  });
});

test("untrusted file error never displays contents/path and doesn't replace fixture conversation", async () => {
  await withApp(async (app) => {
    await app.consent();
    await app.import({ size: 10, arrayBuffer() { throw new Error("PRIVATE_SOURCE_PATH"); } });
    assert.match(app.node("transcript-state").textContent, /error/);
    assert.ok(!app.node("transcript-notice").textContent.includes("PRIVATE_SOURCE_PATH"));
    assert.equal(app.node("transcript-text").value, "");
    assert.equal(app.node("transcript-package").value, "");
    assert.equal(JSON.stringify(app.node("messages").children), app.initialMessages);
  });
});

test("empty picker selection preserves exact current review and prepared package", async () => {
  await withApp(async (app) => {
    await app.ready();
    const reviewed = app.node("transcript-text").value;
    app.node("transcript-file").files = [];
    await app.node("transcript-file").dispatch("change"); app.tick();
    assert.equal(app.node("transcript-text").value, reviewed);
    assert.equal(app.node("transcript-export").disabled, false);
    await app.submit();
    const prepared = app.node("transcript-package").value;
    assert.ok(prepared);
    app.node("transcript-file").files = [];
    await app.node("transcript-file").dispatch("change"); app.tick();
    assert.equal(app.node("transcript-package").value, prepared);
    assert.equal(app.node("transcript-output").hidden, false);
    assert.match(app.node("transcript-state").textContent, /exported/);
  });
});

test("file input name cleared before IO and stale completion never clears newer selection", async () => {
  await withApp(async (app) => {
    await app.consent(); const wait = deferred();
    let clearedBeforeRead = false;
    const pending = app.import({ size: source().length, arrayBuffer() {
      clearedBeforeRead = app.node("transcript-file").value === "";
      return wait.promise;
    } });
    assert.equal(clearedBeforeRead, true);
    assert.equal(app.node("transcript-file").value, "");
    await app.import(file(source("newer reviewed file")));
    // A later native selection can update the input before its change callback.
    // The earlier handler must not erase this value when its own read resolves.
    app.node("transcript-file").value = "later-native-selection.json";
    wait.resolve(source().buffer); await pending;
    assert.equal(app.node("transcript-file").value, "later-native-selection.json");
    assert.equal(app.node("transcript-text").value, "newer reviewed file");
    await app.submit();
    assert.equal(JSON.parse(app.node("transcript-package").value).reviewed_text, "newer reviewed file");
  });
});
