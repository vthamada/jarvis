// Real app + parser against actual HTML IDs, with native-details default actions modeled.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { webcrypto } from "node:crypto";
const markup = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const ticket = "web-request-" + "a".repeat(32), otherTicket = "web-request-" + "d".repeat(32);
const sessionRef = "session://web-live/" + "b".repeat(32), query = "Compare documentation and observability pilot reports.";
const prose = "Readable unverified analysis";
const canonical = (analysis = prose) => "Native final\r\nexact prefix 😀 \n\n" +
  "Model-generated analysis (unverified; not facts, grants or action confirmations):\n" +
  "Literal data only; no permissions, actions, execution receipts or changes to the native decision.\n" +
  'Analysis: "' + analysis + '"\nAssumptions: none supplied\nLimitations: none supplied\nCitations (exact source text; not verified facts):';
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: "c".repeat(64), expires_in_seconds: 900, last_ticket: null, ...changes });
const final = (changes = {}) => ({ query, response_text: canonical(), intent: "analysis", governance_decision: "allow",
  memory_record_ref: "mem-record-0123abcd", timestamp: "2026-10-06T12:00:00Z", evidence_mode: "core_local",
  generative_status: "accepted", authority: "none", generative_error_code: null,
  generative_evidence_mode: "injected_transport", generative_analysis_characters: prose.length, ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: "jarvis-local-analysis-v2", status, ticket,
  error_code: null, result: status === "completed" ? final() : null, ...changes });
const nativeFinal = (changes = {}) => {
  const value = final({ generative_status: "disabled", response_text: "Native only final 😀\r\nexact", ...changes });
  delete value.generative_error_code; delete value.generative_evidence_mode; delete value.generative_analysis_characters; return value;
};
const nativeEnvelope = (status = "completed", changes = {}) => envelope(status, { schema_version: "jarvis-local-analysis-v1",
  result: status === "completed" ? nativeFinal() : null, ...changes });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const flow = (value = final()) => [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), response(envelope("completed", { result: value }))];
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
const flush = () => new Promise((yes) => setImmediate(yes));
async function waitFor(predicate) {
  const deadline = Date.now() + 2000;
  while (!predicate() && Date.now() < deadline) await new Promise((yes) => setTimeout(yes, 1));
  assert.ok(predicate(), "expected actual async parser/render publication");
}
let sequence = 0;
async function withApp(responses, callback, { digest = (...args) => webcrypto.subtle.digest(...args) } = {}) {
  const savedKeys = ["document", "window", "fetch", "crypto", "localStorage", "sessionStorage", "Audio", "AudioContext", "navigator"];
  const saved = new Map(savedKeys.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const calls = [], focusCalls = [], hashes = [], pendingHashes = [];
  let document;
  const parent = new Map([
    ...["live-secret", "live-pair", "live-pair-form", "live-pair-help", "live-pairing-summary"].map((id) => [id, "live-pairing-details"]),
    ["live-final", "live-canonical-details"], ["live-canonical-summary", "live-canonical-details"],
    ["live-canonical-details", "live-result"], ["live-projection", "live-result"],
    ["live-result-query", "live-result"], ["live-projection-analysis", "live-projection"],
  ]);
  class Element {
    constructor(id) {
      this.id = id; this.handlers = new Map(); this.disabled = false; this.hidden = false; this.value = "";
      this.checked = false; this.dataset = {}; this.attributes = new Map(); this._text = "";
      this.open = markup.includes(`id="${id}"`) && new RegExp(`<details[^>]*id="${id}"[^>]*\\bopen\\b`).test(markup);
    }
    set textContent(value) { this._text = String(value); }
    get textContent() { return this._text; }
    set disabled(value) { this._disabled = value; if (value && document?.activeElement === this) document.activeElement = document.body; }
    get disabled() { return this._disabled; }
    set innerHTML(_value) { assert.fail("HTML sink forbidden"); }
    setAttribute(name, value) { this.attributes.set(name, value); }
    addEventListener(name, callback) { const list = this.handlers.get(name) ?? []; list.push(callback); this.handlers.set(name, list); }
    async dispatch(name, changes = {}) {
      await Promise.all((this.handlers.get(name) ?? []).map((fn) => fn({ type: name, target: this, preventDefault() {}, ...changes })));
    }
    contains(element) {
      let id = element.id;
      while (id) { if (id === this.id) return true; id = parent.get(id); }
      return false;
    }
    focus(options) { document.activeElement = this; focusCalls.push({ id: this.id, options });
      for (const listener of document.handlers.get("focusin") ?? []) listener({ target: this }); }
  }
  const elements = new Map(ids.map((id) => [id, new Element(id)]));
  const node = (id) => { assert.ok(elements.has(id), `missing actual compact HTML ID ${id}`); return elements.get(id); };
  const page = new Element("window"), body = new Element("body");
  const prohibited = () => assert.fail("storage/audio/external IO forbidden");
  document = { activeElement: body, body, handlers: new Map(), getElementById: node,
    addEventListener(name, listener) { const items = this.handlers.get(name) ?? []; items.push(listener); this.handlers.set(name, items); },
    querySelectorAll(selector) { assert.equal(selector, "[data-prompt]"); return []; } };
  const values = {
    document, window: { addEventListener: page.addEventListener.bind(page) },
    fetch: async (url, init) => {
      assert.match(url, /^\/api\/(?:session|pair|tickets|analysis|generative-tickets|generative-analysis|disconnect|results\/web-request-[a-f0-9]{32})$/);
      calls.push({ url, ...init }); const next = responses.shift(); assert.ok(next, `unexpected fetch ${url}`);
      if (typeof next === "function") return next(url, init, { node, calls }); if (next instanceof Error) throw next; return next;
    },
    crypto: { subtle: { digest: (...args) => {
      hashes.push(args); const pending = Promise.resolve().then(() => digest(...args)); pendingHashes.push(pending); return pending;
    } } },
    localStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    sessionStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    Audio: class { constructor() { prohibited(); } }, AudioContext: class { constructor() { prohibited(); } },
    navigator: { mediaDevices: { getUserMedia: prohibited } },
  };
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, value });
  try {
    await import(`../live-app.mjs?real-compact-app=${++sequence}`); await flush();
    await callback({ node, calls, focusCalls, document, hashes,
      finishHashes: async () => { await Promise.allSettled(pendingHashes); await flush(); await flush(); },
      submit: async (consent = true, content = query) => {
        node("live-query").value = content; node("live-generative-consent").checked = consent;
        await node("live-form").dispatch("submit");
      }, click: (id) => node(id).dispatch("click"), page: (name, persisted = false) => page.dispatch(name, { persisted }),
      pointer: (target = document.body) => { for (const listener of document.handlers.get("pointerdown") ?? []) listener({ target }); },
      toggle: async (id, key = null) => {
        const summary = node(id), details = node(parent.get(id)); summary.focus();
        if (key !== null) await summary.dispatch("keydown", { key });
        await summary.dispatch("click"); details.open = !details.open; await details.dispatch("toggle");
      },
    });
  } finally {
    await page.dispatch("pagehide");
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
}
test("unpaired defaults open and shell flag false without discovery or premature canonical closure", async () => {
  await withApp([response({ error_code: "session_refused" }, 401)], async ({ node, calls, hashes }) => {
    assert.equal(node("live-shell").dataset.paired, "false"); assert.equal(node("live-pairing-details").open, true);
    assert.equal(node("live-canonical-details").open, true); assert.equal(calls.length, 1); assert.equal(hashes.length, 0);
  });
});
test("boot paired closes pairing once without stealing untouched document focus", async () => {
  await withApp([response(session())], async ({ node, focusCalls, document }) => {
    assert.equal(node("live-shell").dataset.paired, "true"); assert.equal(node("live-pairing-details").open, false);
    assert.equal(focusCalls.length, 0); assert.equal(document.activeElement.id, "body");
  });
});
test("explicit pairing moves hidden form focus to enabled composer without scrolling", async () => {
  await withApp([response({ error_code: "session_refused" }, 401), response(session())], async ({ node, document, focusCalls }) => {
    node("live-secret").value = "f".repeat(64); node("live-pair").focus(); await node("live-pair-form").dispatch("submit");
    assert.equal(node("live-secret").value, ""); assert.equal(node("live-pairing-details").open, false);
    assert.equal(document.activeElement.id, "live-query"); assert.equal(node("live-query").disabled, false);
    assert.deepEqual(focusCalls.at(-1), { id: "live-query", options: { preventScroll: true } });
  });
});
test("manually opened pairing stays open throughout submission/poll/recovery", async () => {
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope())], async ({ node, submit, toggle, click }) => {
    await toggle("live-pairing-summary"); assert.equal(node("live-pairing-details").open, true);
    await submit(); await click("live-recover"); assert.equal(node("live-pairing-details").open, true);
  });
});
test("pairing summary focus remains visible when connection closes the form", async () => {
  const gate = deferred();
  await withApp([() => gate.promise], async ({ node, document, focusCalls }) => {
    node("live-pairing-summary").focus(); const prior = focusCalls.length; gate.resolve(response(session()));
    await waitFor(() => node("live-pairing-details").open === false);
    assert.equal(document.activeElement.id, "live-pairing-summary"); assert.equal(focusCalls.length, prior);
  });
});
test("pairing success does not steal focus deliberately moved after disabled input blurs to body", async () => {
  const gate = deferred();
  await withApp([response({ error_code: "session_refused" }, 401), () => gate.promise], async ({ node, document, focusCalls }) => {
    node("live-secret").value = "f".repeat(64); node("live-pair").focus(); const pairing = node("live-pair-form").dispatch("submit");
    assert.equal(document.activeElement.id, "body"); node("live-pairing-summary").focus(); const previous = focusCalls.length;
    gate.resolve(response(session())); await pairing; assert.equal(document.activeElement.id, "live-pairing-summary");
    assert.equal(focusCalls.length, previous); assert.equal(node("live-pairing-details").open, false);
  });
});
test("explicit background pointer intent while pairing prevents body fallback from stealing focus", async () => {
  const gate = deferred();
  await withApp([response({ error_code: "session_refused" }, 401), () => gate.promise], async ({ node, document, pointer, focusCalls }) => {
    node("live-secret").value = "f".repeat(64); node("live-pair").focus(); const pairing = node("live-pair-form").dispatch("submit");
    assert.equal(document.activeElement.id, "body"); pointer(); const count = focusCalls.length;
    gate.resolve(response(session())); await pairing; assert.equal(document.activeElement.id, "body"); assert.equal(focusCalls.length, count);
  });
});
test("accepted flag alone keeps full final open until current parser+hash validates", async () => {
  const gate = deferred();
  await withApp(flow(), async ({ node, submit, hashes, finishHashes }) => {
    await submit(); await waitFor(() => hashes.length === 1);
    assert.equal(node("live-canonical-details").open, true); assert.equal(node("live-final").textContent, final().response_text);
    gate.resolve(); await finishHashes(); assert.equal(node("live-projection").hidden, false);
    assert.equal(node("live-canonical-details").open, false); assert.equal(node("live-final").textContent, final().response_text);
  }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("parser failure never automatically conceals an accepted raw final", async () => {
  const value = final({ response_text: "Native final + incompatible proposed complement" });
  await withApp(flow(value), async ({ node, submit, finishHashes }) => {
    await submit(); await finishHashes(); assert.equal(node("live-canonical-details").open, true);
    assert.equal(node("live-projection").hidden, true); assert.equal(node("live-final").textContent, value.response_text);
  });
});
for (const error of [new Error("private-secret"), new ArrayBuffer(31)]) {
  test(`hash failure retains open canonical fallback ${error.constructor.name}`, async () => {
    await withApp(flow(), async ({ node, submit, finishHashes }) => {
      await submit(); await finishHashes(); assert.equal(node("live-canonical-details").open, true);
      assert.equal(node("live-final").textContent, final().response_text); assert.equal(node("live-projection").hidden, true);
    }, { digest: async () => { if (error instanceof Error) throw error; return error; } });
  });
}
test("failed current hash reopens fallback even if user closed canonical before validation", async () => {
  const gate = deferred();
  await withApp(flow(), async ({ node, submit, hashes, toggle, finishHashes }) => {
    await submit(); await waitFor(() => hashes.length === 1); await toggle("live-canonical-summary");
    assert.equal(node("live-canonical-details").open, false); gate.resolve(); await finishHashes();
    assert.equal(node("live-canonical-details").open, true); assert.equal(node("live-final").textContent, final().response_text);
  }, { digest: async () => { await gate.promise; throw new Error("private-crypto-error"); } });
});
for (const kind of ["native", "rejected", "withheld"]) {
  test(`${kind} initially exposes complete canonical final`, async () => {
    const value = kind === "native" ? nativeFinal() : final({ generative_status: kind, generative_error_code: "scope_denied",
      generative_evidence_mode: null, generative_analysis_characters: 0, response_text: "Final nativa preservada" });
    const responses = kind === "native" ? [response(session()), response(nativeEnvelope("issued"), 201), response(nativeEnvelope("running"), 202), response(nativeEnvelope())] : flow(value);
    await withApp(responses, async ({ node, submit, hashes }) => {
      await submit(kind !== "native"); assert.equal(node("live-canonical-details").open, true);
      assert.equal(node("live-final").textContent, value.response_text); assert.equal(hashes.length, 0);
    });
  });
}
for (const key of [null, "Enter", " "]) {
  test(`manual canonical disclosure opening survives same-result GET recovery ${JSON.stringify(key)}`, async () => {
    await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope())], async ({ node, submit, toggle, click, finishHashes }) => {
      await submit(); await finishHashes(); assert.equal(node("live-canonical-details").open, false);
      await toggle("live-canonical-summary", key); assert.equal(node("live-canonical-details").open, true);
      await click("live-recover"); await finishHashes(); assert.equal(node("live-canonical-details").open, true);
      assert.equal(node("live-final").textContent, final().response_text);
    });
  });
}
test("manual opening while hash is pending prevents callback from closing it or stealing focus", async () => {
  const gate = deferred();
  await withApp(flow(), async ({ node, submit, hashes, toggle, document, focusCalls, finishHashes }) => {
    await submit(); await waitFor(() => hashes.length === 1);
    await toggle("live-canonical-summary"); await toggle("live-canonical-summary");
    const previous = focusCalls.length; gate.resolve(); await finishHashes();
    assert.equal(node("live-canonical-details").open, true); assert.equal(document.activeElement.id, "live-canonical-summary");
    assert.equal(focusCalls.length, previous);
  }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("manual closure survives repeated same-result recovery only after revalidation", async () => {
  const gate = deferred(); let hashes = 0;
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope())], async ({ node, submit, toggle, click, finishHashes }) => {
    await submit(); await finishHashes(); await toggle("live-canonical-summary"); await toggle("live-canonical-summary");
    await click("live-recover"); assert.equal(node("live-canonical-details").open, true);
    gate.resolve(); await finishHashes(); assert.equal(node("live-canonical-details").open, false);
  }, { digest: async (...args) => { if (++hashes === 2) await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("native manual choice survives identical recovery without an unnecessary hash", async () => {
  await withApp([response(session()), response(nativeEnvelope("issued"), 201), response(nativeEnvelope("running"), 202), response(nativeEnvelope()),
    response(session({ last_ticket: ticket })), response(nativeEnvelope())], async ({ node, submit, toggle, click, hashes }) => {
    await submit(false); await toggle("live-canonical-summary"); assert.equal(node("live-canonical-details").open, false);
    await click("live-recover"); assert.equal(node("live-canonical-details").open, false); assert.equal(hashes.length, 0);
  });
});
test("automatic closure relocates focus only when it would hide the focused canonical content", async () => {
  const gate = deferred();
  await withApp(flow(), async ({ node, submit, hashes, document, finishHashes, focusCalls }) => {
    await submit(); await waitFor(() => hashes.length === 1); node("live-final").focus(); gate.resolve(); await finishHashes();
    assert.equal(node("live-canonical-details").open, false); assert.equal(document.activeElement.id, "live-canonical-summary");
    assert.deepEqual(focusCalls.at(-1), { id: "live-canonical-summary", options: { preventScroll: true } });
  }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
for (const focusId of ["live-query", "live-canonical-summary", "live-recover"]) {
  test(`hash completion does not steal external/visible focus ${focusId}`, async () => {
    const gate = deferred();
    await withApp(flow(), async ({ node, submit, hashes, document, finishHashes, focusCalls }) => {
      await submit(); await waitFor(() => hashes.length === 1); node(focusId).focus(); const count = focusCalls.length;
      gate.resolve(); await finishHashes(); assert.equal(document.activeElement.id, focusId); assert.equal(focusCalls.length, count);
    }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
  });
}
for (const action of ["stop", "disconnect", "pagehide", "refresh", "foreign"]) {
  test(`late validated hash cannot close/show stale content after ${action}`, async () => {
    const gate = deferred(); const responses = flow();
    if (action === "disconnect") responses.push(response({ status: "disconnected" }));
    if (action === "refresh") responses.push(response(session({ last_ticket: ticket })));
    if (action === "foreign") responses.push(response(session({ last_ticket: ticket, session_ref: "session://web-live/" + "f".repeat(32) })));
    await withApp(responses, async ({ node, submit, hashes, click, page, finishHashes }) => {
      await submit(); await waitFor(() => hashes.length === 1);
      if (action === "pagehide") await page("pagehide"); else await click({ stop: "live-stop", disconnect: "live-disconnect", refresh: "live-refresh", foreign: "live-recover" }[action]);
      gate.resolve(); await finishHashes(); assert.equal(node("live-canonical-details").open, true);
      assert.equal(node("live-projection").hidden, true);
      if (["disconnect", "pagehide", "foreign"].includes(action)) {
        assert.equal(node("live-shell").dataset.paired, "false"); assert.equal(node("live-pairing-details").open, true);
      }
    }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
  });
}
test("new native ticket resets earlier manual/auto closure and stale hash cannot close it", async () => {
  const gate = deferred(); const issued = nativeEnvelope("issued", { ticket: otherTicket }), running = nativeEnvelope("running", { ticket: otherTicket });
  await withApp([...flow(), response(issued, 201), response(running, 202), response(nativeEnvelope("completed", { ticket: otherTicket }))],
    async ({ node, submit, hashes, finishHashes }) => {
      await submit(); await waitFor(() => hashes.length === 1); await submit(false); gate.resolve(); await finishHashes();
      assert.equal(node("live-canonical-details").open, true); assert.equal(node("live-final").textContent, nativeFinal().response_text);
      assert.equal(node("live-projection").hidden, true);
    }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("old same-ticket hash cannot close a newer incompatible final or revive previous manual choice", async () => {
  const gate = deferred(), incompatible = final({ response_text: "New native final + incompatible complement" });
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope("completed", { result: incompatible }))],
    async ({ node, submit, hashes, toggle, click, finishHashes }) => {
      await submit(); await waitFor(() => hashes.length === 1); await toggle("live-canonical-summary");
      assert.equal(node("live-canonical-details").open, false); await click("live-recover"); gate.resolve(); await finishHashes();
      assert.equal(node("live-canonical-details").open, true); assert.equal(node("live-final").textContent, incompatible.response_text);
      assert.equal(node("live-projection").hidden, true);
    }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("pending result focus is not abandoned inside a newly hidden result on recovery", async () => {
  const held = deferred();
  await withApp([...flow(), () => held.promise], async ({ node, submit, click, document, finishHashes }) => {
    await submit(); await finishHashes(); node("live-canonical-summary").focus(); const recovering = click("live-recover");
    assert.equal(document.activeElement.id, "live-stop"); assert.equal(node("live-stop").disabled, false);
    await click("live-stop"); await recovering; held.resolve(response(session({ last_ticket: ticket })));
  });
});
