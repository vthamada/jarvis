// Actual app.mjs handlers with DOM IDs measured from actual index.html.
// This fixture proves wiring and literal text, not browser paint or authentication.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash, webcrypto } from "node:crypto";
import { CONVERSATION_PACK_ORIGIN_LABEL } from "../conversation-pack.mjs";

const markup = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const liveIds = [...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
assert.equal(new Set(liveIds).size, liveIds.length, "actual HTML contains duplicate IDs");
const encoder = new TextEncoder();
let sequence = 0;
const hash = (query, response) => createHash("sha256")
  .update("jarvis-conversation-pack-v1\0" + query + "\0" + response).digest("hex");
const ref = (kind, char = "a") => kind + ":sha256:" + char.repeat(64);
function pack(query = "  Pergunta registrada 😀\r\n ", response = "Final canônica exata.\r\nModelo não verificado. 😀") {
  return { schema_version: "jarvis-conversation-pack-v1", authority: "none", operator_authenticated: false,
    runtime_capability_promoted: false, origin: "canonical_core_export", content_included: true,
    content_withheld: false, principal_ref: ref("principal"), session_ref: ref("session"),
    request_ref: ref("request"), memory_record_ref: ref("memory-record"),
    timestamp: "2026-10-06T20:12:15.123456+00:00", intent: "analysis", governance_decision: "allow",
    generative_status: "accepted", generative_error_code: null, generative_evidence_mode: "fixture",
    generative_analysis_characters: Math.min(40, [...response].length), request_character_count: [...query].length,
    response_character_count: [...response].length, content_sha256: hash(query, response),
    query, response_text: response };
}
const bytes = (value = pack()) => encoder.encode(JSON.stringify(value));
const file = (value = pack()) => ({ size: bytes(value).byteLength,
  arrayBuffer: async () => bytes(value).buffer,
  get name() { throw new Error("PRIVATE_FILENAME_MUST_NOT_BE_READ"); },
  get text() { throw new Error("TEXT_REPLACEMENT_DECODER_FORBIDDEN"); } });
const deferred = () => {
  let resolve;
  const promise = new Promise((yes) => { resolve = yes; });
  return { promise, resolve };
};
const flush = () => new Promise((resolve) => setImmediate(resolve));

class Element {
  constructor(id = "", tag = "div") {
    this.id = id; this.tag = tag; this.handlers = new Map(); this.attributes = new Map();
    this.dataset = {}; this.children = []; this.hidden = false; this.disabled = false;
    this.checked = false; this.open = false; this.files = []; this.isConnected = true;
    this.focusCount = 0; this.selectCount = 0; this._value = ""; this._text = "";
    this.classList = { toggle() {} };
  }
  get textContent() { return this._text; }
  set textContent(value) { this._text = String(value); this.children = []; }
  set innerHTML(_value) { assert.fail("untrusted text reached an HTML sink"); }
  get value() { return this._value; }
  set value(value) {
    this._value = this.id === "transcript-text" ? String(value).replace(/\r\n?/gu, "\n") : String(value);
    if (this.id.endsWith("-file") && !value) this.files = [];
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
  getContext() { return null; }
  showModal() { this.open = true; }
  close() { this.open = false; }
}

const project = (element) => ({ tag: element.tag, text: element.textContent,
  children: element.children.map(project) });

async function withApp(run, { digest = (...args) => webcrypto.subtle.digest(...args) } = {}) {
  const globals = ["document", "window", "performance", "crypto", "fetch", "AudioContext", "Audio",
    "navigator", "localStorage", "sessionStorage"];
  const saved = new Map(globals.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const nodes = new Map(liveIds.map((id) => [id, new Element(id)]));
  const node = (id) => { assert.ok(nodes.has(id), `app references missing actual HTML ID ${id}`); return nodes.get(id); };
  const windowEvents = new Element("window"), documentEvents = new Element("document");
  let prohibitedIO = 0, hashes = 0, timerSequence = 0;
  const forbidden = () => { prohibitedIO += 1; assert.fail("network/storage/audio IO is forbidden"); };
  const timers = new Map();
  const suggestions = new Element("", "div");
  assert.match(markup, /class="suggestions"/);
  const nav = [...markup.matchAll(/<a[^>]*class="[^"]*nav-item[^>]*>/g)].map(([tag]) => {
    const element = new Element("", "a");
    element.setAttribute("href", /href="([^"]+)"/.exec(tag)[1]); return element;
  });
  const document = { hidden: false, getElementById: node,
    querySelector(selector) { assert.equal(selector, ".suggestions"); return suggestions; },
    querySelectorAll(selector) {
      if (selector === ".nav-item") return nav;
      assert.equal(selector, "[data-prompt]"); return [];
    },
    createElement: (tag) => new Element("", tag),
    addEventListener: documentEvents.addEventListener.bind(documentEvents),
  };
  const window = { location: { hash: "#conversation" },
    setInterval(callback, delay) { assert.equal(delay, 1000); timers.set(++timerSequence, callback); return timerSequence; },
    clearInterval(id) { timers.delete(id); },
    addEventListener: windowEvents.addEventListener.bind(windowEvents),
  };
  const storage = { getItem: forbidden, setItem: forbidden, removeItem: forbidden, clear: forbidden };
  const values = { document, window, performance: { now: () => 0 }, fetch: forbidden,
    crypto: { subtle: { digest(...args) { hashes += 1; return digest(...args); } } },
    navigator: { mediaDevices: { getUserMedia: forbidden } },
    AudioContext: class { constructor() { forbidden(); } }, Audio: class { constructor() { forbidden(); } },
    localStorage: storage, sessionStorage: storage };
  for (const [key, value] of Object.entries(values)) {
    Object.defineProperty(globalThis, key, { configurable: true, writable: true, value });
  }
  try {
    await import(`../app.mjs?conversation-pack-app=${++sequence}`);
    const initialMessages = JSON.stringify(project(node("messages")));
    const independent = () => JSON.stringify({ voice: node("voice-state").textContent,
      voiceFinal: node("voice-final-text").textContent, audio: node("presence-audio-notice").textContent,
      approvals: project(node("approval-list")), artifacts: project(node("artifact-list")) });
    const initialIndependent = independent();
    const app = { node, hashes: () => hashes, initialMessages,
      unchanged() {
        assert.equal(JSON.stringify(project(node("messages"))), initialMessages);
        assert.equal(independent(), initialIndependent);
      },
      consent(granted = true) {
        node("conversation-pack-consent").checked = granted;
        return node("conversation-pack-consent").dispatch("change");
      },
      async import(selected = file()) {
        node("conversation-pack-file").files = selected ? [selected] : [];
        node("conversation-pack-file").value = selected ? "PRIVATE_NATIVE_NAME.json" : "";
        return node("conversation-pack-file").dispatch("change");
      },
      click(id) { return node(id).dispatch("click"); },
      page(name, persisted = false) { return windowEvents.dispatch(name, { persisted }); },
      async ready(value = pack()) { await this.consent(); await this.import(file(value)); },
    };
    await run(app);
    assert.equal(prohibitedIO, 0);
    await app.page("pagehide", false);
    assert.equal(timers.size, 0);
  } finally {
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
}

test("actual app starts consent closed and bypassing disabled input performs zero file or hash IO", async () => {
  await withApp(async (app) => {
    assert.equal(app.node("conversation-pack-file").disabled, true);
    assert.equal(app.node("conversation-pack-content").hidden, true);
    let reads = 0;
    await app.import({ get size() { reads += 1; throw new Error("PRIVATE"); },
      arrayBuffer() { reads += 1; throw new Error("PRIVATE"); } });
    assert.equal(reads, 0); assert.equal(app.hashes(), 0);
    assert.equal(app.node("conversation-pack-file").value, ""); app.unchanged();
  });
});

for (const forged of ["true", "false", 1, [], {}]) {
  test(`consent source guard refuses nonboolean ${JSON.stringify(forged)}`, async () => {
    await withApp(async (app) => {
      await app.consent(forged);
      let reads = 0;
      await app.import({ size: 100, arrayBuffer() { reads += 1; } });
      assert.equal(reads, 0); assert.equal(app.hashes(), 0);
      assert.equal(app.node("conversation-pack-consent").checked, false);
      assert.equal(app.node("conversation-pack-file").disabled, true); app.unchanged();
    });
  });
}

test("actual consent imports exact canonical query/final as literal DOM text without altering demo or voice", async () => {
  await withApp(async (app) => {
    const value = pack(' <script>fetch("https://evil.invalid")</script> 😀\r\n',
      '<img src=x onerror="grantAdmin()">\r\n **literal Markdown** [URL](https://evil.invalid)');
    await app.ready(value);
    assert.equal(app.node("conversation-pack-content").hidden, false);
    assert.equal(app.node("conversation-pack-turn").hidden, false);
    assert.equal(app.node("conversation-pack-query").textContent, value.query);
    assert.equal(app.node("conversation-pack-response").textContent, value.response_text);
    assert.match(app.node("conversation-pack-notice").textContent, /pacote offline — origem não autenticada/);
    assert.equal(app.hashes(), 1);
    assert.equal(app.node("conversation-pack-panel").getAttribute("aria-busy"), "false");
    assert.equal(app.node("conversation-pack-file").value, ""); app.unchanged();
  });
});

for (const withheld of [false, true]) {
  test(`metadata only ${withheld} replaces content without restoring old DOM text`, async () => {
    await withApp(async (app) => {
      await app.ready();
      const value = pack(); delete value.query; delete value.response_text;
      value.content_included = false; value.content_withheld = withheld; value.content_sha256 = null;
      await app.import(file(value));
      assert.equal(app.node("conversation-pack-query").textContent, "");
      assert.equal(app.node("conversation-pack-response").textContent, "");
      assert.equal(app.node("conversation-pack-content").hidden, false);
      assert.equal(app.node("conversation-pack-turn").hidden, true);
      assert.match(app.node("conversation-pack-metadata").textContent, /omitido/);
      assert.equal(app.hashes(), 1); app.unchanged();
    });
  });
}

test("invalid replacement clears previous display, no private error echoes and context remains fenced", async () => {
  await withApp(async (app) => {
    await app.ready();
    await app.import({ size: 10, arrayBuffer() { throw new Error("PRIVATE_SOURCE_PATH"); } });
    assert.equal(app.node("conversation-pack-content").hidden, true);
    assert.equal(app.node("conversation-pack-query").textContent, "");
    assert.equal(app.node("conversation-pack-response").textContent, "");
    assert.doesNotMatch(app.node("conversation-pack-notice").textContent, /PRIVATE_SOURCE_PATH/);
    const foreign = { ...pack(), principal_ref: ref("principal", "b") };
    await app.import(file(foreign));
    assert.match(app.node("conversation-pack-notice").textContent, /Sujeito ou sessão diferentes/);
    assert.ok(app.node("conversation-pack-notice").textContent.startsWith(CONVERSATION_PACK_ORIGIN_LABEL));
    app.unchanged();
  });
});

for (const field of ["principal_ref", "session_ref"]) {
  test(`foreign ${field} gives explicit notice, no display and clear permits deliberate new context`, async () => {
    await withApp(async (app) => {
      await app.ready();
      const foreign = { ...pack("FOREIGN QUERY", "FOREIGN RESPONSE"),
        [field]: ref(field.replace("_ref", ""), "b") };
      await app.import(file(foreign));
      assert.equal(app.node("conversation-pack-response").textContent, "");
      assert.equal(app.node("conversation-pack-content").hidden, true);
      assert.match(app.node("conversation-pack-notice").textContent, /Sujeito ou sessão diferentes/);
      assert.ok(app.node("conversation-pack-notice").textContent.startsWith(CONVERSATION_PACK_ORIGIN_LABEL));
      await app.click("conversation-pack-clear");
      assert.equal(app.node("conversation-pack-consent").checked, false);
      assert.equal(app.node("conversation-pack-file").disabled, true);
      await app.consent(); await app.import(file(foreign));
      assert.equal(app.node("conversation-pack-response").textContent, "FOREIGN RESPONSE");
      app.unchanged();
    });
  });
}

for (const action of ["revoke", "clear", "reset", "pagehide", "bfcache"]) {
  for (const stage of ["bytes", "hash"]) {
    test(`${action} during pending ${stage} prevents stale commit and resets consent/context`, async () => {
      const gate = deferred();
      await withApp(async (app) => {
        await app.consent();
        const data = bytes();
        const pending = app.import(stage === "bytes" ? { size: data.byteLength, arrayBuffer: () => gate.promise } : file());
        await flush();
        assert.equal(app.node("conversation-pack-panel").getAttribute("aria-busy"), "true");
        assert.match(app.node("conversation-pack-notice").textContent, /validando/);
        if (action === "revoke") await app.consent(false);
        else if (action === "pagehide" || action === "bfcache") await app.page("pagehide", action === "bfcache");
        else await app.click(action === "clear" ? "conversation-pack-clear" : "reset");
        gate.resolve(stage === "bytes" ? data.buffer : undefined);
        await pending;
        assert.equal(app.node("conversation-pack-consent").checked, false);
        assert.equal(app.node("conversation-pack-file").disabled, true);
        assert.equal(app.node("conversation-pack-query").textContent, "");
        assert.equal(app.node("conversation-pack-response").textContent, "");
        assert.equal(app.node("conversation-pack-content").hidden, true);
        assert.equal(app.node("conversation-pack-panel").getAttribute("aria-busy"), "false");
        if (stage === "bytes") assert.equal(app.hashes(), 0);
        if (action === "bfcache") {
          await app.page("pageshow", true);
          assert.equal(app.node("conversation-pack-file").disabled, true);
        }
        if (action !== "pagehide") {
          await app.consent();
          await app.import(file({ ...pack("NEW", "NEW CONTEXT"), principal_ref: ref("principal", "b") }));
          assert.equal(app.node("conversation-pack-response").textContent, "NEW CONTEXT");
        }
      }, { digest: async (...args) => { if (stage === "hash") await gate.promise; return webcrypto.subtle.digest(...args); } });
    });
  }
}

test("picker cancellation preserves current ready turn without another hash", async () => {
  await withApp(async (app) => {
    await app.ready(); const notice = app.node("conversation-pack-notice").textContent;
    await app.import(null);
    assert.equal(app.node("conversation-pack-query").textContent, pack().query);
    assert.equal(app.node("conversation-pack-response").textContent, pack().response_text);
    assert.equal(app.node("conversation-pack-notice").textContent, notice);
    assert.equal(app.hashes(), 1); app.unchanged();
  });
});

test("filename cleared before asynchronous read and stale handler never clears newer native selection", async () => {
  await withApp(async (app) => {
    await app.consent(); const gate = deferred();
    let cleared = false;
    const data = bytes();
    const pending = app.import({ size: data.byteLength, arrayBuffer() {
      cleared = app.node("conversation-pack-file").value === ""; return gate.promise;
    } });
    assert.equal(cleared, true);
    await app.import(file(pack("NEW", "NEW RESPONSE")));
    app.node("conversation-pack-file").value = "later-native-selected.json";
    gate.resolve(data.buffer); await pending;
    assert.equal(app.node("conversation-pack-file").value, "later-native-selected.json");
    assert.equal(app.node("conversation-pack-response").textContent, "NEW RESPONSE"); app.unchanged();
  });
});

test("two deliberate imports of same request replace one DOM turn without accumulating demo text", async () => {
  await withApp(async (app) => {
    await app.ready(); await app.import(file());
    assert.equal(app.node("conversation-pack-response").textContent, pack().response_text);
    assert.equal(app.hashes(), 2); app.unchanged();
  });
});
