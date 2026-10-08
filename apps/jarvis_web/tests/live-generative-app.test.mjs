// Execute the actual module against IDs from the actual live HTML, no model/account IO.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const markup = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const ticket = "web-request-" + "a".repeat(32), sessionRef = "session://web-live/" + "b".repeat(32);
const query = "Compare os relatórios de documentação e observabilidade do piloto.";
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: "c".repeat(64), expires_in_seconds: 900, last_ticket: null, ...changes });
const final = (changes = {}) => ({ query, response_text: '<script>fetch("https://evil.invalid")</script> 😀\r\n **literal** ',
  intent: "analysis", governance_decision: "allow", memory_record_ref: "mem-record-0123abcd",
  timestamp: "2026-10-06T12:00:00Z", evidence_mode: "core_local", generative_status: "accepted", authority: "none",
  generative_error_code: null, generative_evidence_mode: "injected_transport", generative_analysis_characters: 1, ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: "jarvis-local-analysis-v2",
  status, ticket, error_code: null, result: status === "completed" ? final() : null, ...changes });
const nativeFinal = () => { const value = final({ generative_status: "disabled" });
  delete value.generative_error_code; delete value.generative_evidence_mode; delete value.generative_analysis_characters; return value; };
const nativeEnvelope = (status = "completed") => envelope(status, { schema_version: "jarvis-local-analysis-v1", result: status === "completed" ? nativeFinal() : null });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const flow = () => [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), response(envelope())];
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
const flush = () => new Promise((yes) => setImmediate(yes));
let sequence = 0;
class Element {
  constructor(id) { this.id = id; this.handlers = new Map(); this.disabled = false; this.hidden = false;
    this.value = ""; this.checked = false; this.dataset = {}; this.attributes = new Map(); this._text = ""; }
  set textContent(value) { this._text = String(value); }
  get textContent() { return this._text; }
  set innerHTML(_value) { assert.fail("HTML sink forbidden"); }
  setAttribute(name, value) { this.attributes.set(name, value); }
  addEventListener(name, callback) { const list = this.handlers.get(name) ?? []; list.push(callback); this.handlers.set(name, list); }
  async dispatch(name, changes = {}) { await Promise.all((this.handlers.get(name) ?? []).map((fn) => fn({
    target: this, preventDefault() {}, ...changes }))); }
  focus() {}
}
async function withApp(responses, callback) {
  const keys = ["document", "window", "fetch", "localStorage", "sessionStorage", "Audio", "AudioContext", "navigator"];
  const saved = new Map(keys.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const elements = new Map(ids.map((id) => [id, new Element(id)]));
  const node = (id) => { assert.ok(elements.has(id), `missing actual HTML ID ${id}`); return elements.get(id); };
  const page = new Element("window"), calls = [];
  const prohibited = () => assert.fail("browser storage/audio/external IO forbidden");
  const values = {
    document: { getElementById: node, querySelectorAll(selector) { assert.equal(selector, "[data-prompt]"); return []; } },
    window: { addEventListener: page.addEventListener.bind(page) },
    fetch: async (url, init) => {
      assert.match(url, /^\/api\/(?:session|pair|tickets|analysis|generative-tickets|generative-analysis|disconnect|results\/web-request-[a-f0-9]{32})$/);
      calls.push({ url, ...init }); const next = responses.shift(); assert.ok(next, `unexpected fetch ${url}`);
      if (typeof next === "function") return next(url, init, { node, calls });
      if (next instanceof Error) throw next; return next;
    },
    localStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    sessionStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    Audio: class { constructor() { prohibited(); } }, AudioContext: class { constructor() { prohibited(); } },
    navigator: { mediaDevices: { getUserMedia: prohibited } },
  };
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, value });
  try {
    await import(`../live-app.mjs?real-generative-app=${++sequence}`); await flush();
    await callback({ node, calls, submit: async (consent = false, value = query) => {
      node("live-query").value = value; node("live-generative-consent").checked = consent;
      await node("live-form").dispatch("submit");
    }, click: (id) => node(id).dispatch("click"), page: (name, persisted = false) => page.dispatch(name, { persisted }) });
  } finally {
    await page.dispatch("pagehide");
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
}
test("actual checkbox is accessible, initially off, scoped to question, explains host transport and no authority", () => {
  const input = markup.match(/<input[^>]+id="live-generative-consent"[^>]*>/)?.[0];
  assert.ok(input); assert.match(input, /type="checkbox"/); assert.match(input, /disabled/); assert.doesNotMatch(input, /\bchecked\b/);
  assert.match(input, /aria-describedby="live-generative-help"/); assert.match(markup, /for="live-generative-consent"/);
  assert.match(markup, /somente para esta pergunta/); assert.match(markup, /transporte do perfil selecionado pelo host/);
  assert.match(markup, /sem envio de histórico/); assert.match(markup, /não habilita voz, ferramentas ou ações/);
  assert.match(markup, /não desfaz uma análise já iniciada/); assert.doesNotMatch(markup, /<audio|<iframe|localStorage|sessionStorage/);
  const style = readFileSync(new URL("../live-style.css", import.meta.url), "utf8");
  assert.match(style, /\.consent[^}]*min-height:44px/); assert.match(style, /input\[type=checkbox\]:focus-visible/);
});
test("boot authenticates only and never discovers or enables profile automatically", async () => {
  await withApp([response(session())], async ({ node, calls }) => {
    assert.equal(calls.length, 1); assert.equal(calls[0].url, "/api/session");
    assert.equal(node("live-generative-consent").checked, false); assert.equal(node("live-generative-consent").disabled, false);
  });
});
test("unpaired checkbox disabled and forged checked state cannot dispatch", async () => {
  await withApp([response({ error_code: "session_refused" }, 401)], async ({ node, calls, submit }) => {
    assert.equal(node("live-generative-consent").disabled, true); await submit(true); assert.equal(calls.length, 1);
    assert.equal(node("live-generative-consent").checked, false);
  });
});
test("unchecked submit retains exact v1 path and no implicit consent", async () => {
  await withApp([response(session()), response(nativeEnvelope("issued"), 201), response(nativeEnvelope("running"), 202),
    response(nativeEnvelope())], async ({ node, calls, submit }) => {
    await submit(); assert.equal(calls[1].url, "/api/tickets"); assert.equal(calls[2].url, "/api/analysis");
    assert.deepEqual(JSON.parse(calls[2].body), { ticket, query });
    assert.match(node("live-metadata").textContent, /modelo generativo desativado/);
  });
});
for (const mode of ["live", "injected_transport"]) {
  test(`actual accepted ${mode} preserves literal final and labels evidence without claiming truth`, async () => {
    const responses = flow(); responses[3] = response(envelope("completed", { result: final({ generative_evidence_mode: mode }) }));
    await withApp(responses, async ({ node, calls, submit }) => {
      await submit(true); assert.equal(node("live-final").textContent, final().response_text);
      assert.equal(node("live-result-query").textContent, query); assert.equal(node("live-result").hidden, false);
      assert.match(node("live-metadata").textContent, /complemento não verificado/);
      assert.match(node("live-metadata").textContent, mode === "live" ? /não comprova qualidade ou verdade/ : /injetado de teste; não comprova modelo real/);
      assert.match(node("live-metadata").textContent, /nenhuma autoridade para ações/);
      assert.equal(node("live-generative-consent").checked, false);
      assert.equal(calls[1].url, "/api/generative-tickets"); assert.equal(calls[2].url, "/api/generative-analysis");
      assert.deepEqual(JSON.parse(calls[2].body), { ticket, query, consent: true });
    });
  });
}
test("consent is cleared before first fetch, not retained for next native request", async () => {
  const responses = flow(); responses[1] = (_url, init, { node }) => {
    assert.equal(node("live-generative-consent").checked, false); assert.equal(node("live-generative-consent").disabled, true);
    assert.deepEqual(JSON.parse(init.body), { consent: true }); return response(envelope("issued"), 201);
  };
  responses.push(response(nativeEnvelope("issued"), 201), response(nativeEnvelope("running"), 202), response(nativeEnvelope()));
  await withApp(responses, async ({ node, calls, submit }) => {
    await submit(true); await submit(); assert.equal(node("live-generative-consent").checked, false);
    assert.deepEqual(calls.filter((call) => call.method === "POST").map((call) => call.url),
      ["/api/generative-tickets", "/api/generative-analysis", "/api/tickets", "/api/analysis"]);
  });
});
for (const status of ["rejected", "withheld"]) {
  for (const decision of ["allow", "block", "defer_for_validation"]) {
    test(`actual ${status} ${decision} preserves exact native final, not generative success`, async () => {
      const value = final({ generative_status: status, governance_decision: decision,
        generative_error_code: status === "withheld" ? "scope_denied" : "input_sensitive",
        generative_evidence_mode: null, generative_analysis_characters: 0 });
      const responses = flow(); responses[3] = response(envelope("completed", { result: value }));
      await withApp(responses, async ({ node, submit }) => {
        await submit(true); assert.equal(node("live-final").textContent, value.response_text);
        assert.match(node("live-metadata").textContent, /final nativa preservada/);
        assert.match(node("live-metadata").textContent, status === "withheld" ? /complemento retido/ : /complemento recusado/);
        assert.doesNotMatch(node("live-metadata").textContent, /complemento não verificado/);
      });
    });
  }
}
test("full canonical long final never clipped or segmented by UI", async () => {
  const value = final({ response_text: "😀".repeat(131072) }); const responses = flow();
  responses[3] = response(envelope("completed", { result: value }));
  await withApp(responses, async ({ node, submit }) => { await submit(true); assert.equal(node("live-final").textContent, value.response_text); });
});
test("unavailable host shows fixed notice, no fallback or silent resend", async () => {
  await withApp([response(session()), response({ error_code: "generative_unavailable" }, 409)], async ({ node, calls, submit }) => {
    await submit(true); assert.match(node("live-notice").textContent, /não está habilitado neste host/);
    assert.equal(calls.length, 2); assert.equal(node("live-generative-consent").checked, false);
    assert.equal(node("live-final").textContent, "");
  });
});
test("reload v2 requires explicit recovery and sends no POST nor fresh consent", async () => {
  await withApp([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope())],
    async ({ node, calls, click }) => {
      assert.equal(calls.length, 1); assert.equal(node("live-generative-consent").checked, false);
      assert.equal(node("live-final").textContent, ""); await click("live-recover");
      assert.equal(node("live-final").textContent, final().response_text); assert.ok(calls.every((call) => call.method === "GET"));
    });
});
test("uncertain generative request retains ticket and uses GET only to recover", async () => {
  await withApp([response(session()), response(envelope("issued"), 201), new Error("PRIVATE_MODEL"),
    response(session({ last_ticket: ticket })), response(envelope())], async ({ node, calls, submit, click }) => {
    await submit(true); assert.equal(node("live-generative-consent").checked, false);
    assert.doesNotMatch(node("live-notice").textContent, /PRIVATE_MODEL/); await click("live-recover");
    assert.equal(node("live-final").textContent, final().response_text); assert.ok(calls.slice(3).every((call) => call.method === "GET"));
  });
});
for (const action of ["stop", "pagehide", "disconnect", "bfcache"]) {
  test(`actual generative ${action} clears consent and fences late final without claiming rollback`, async () => {
    const gate = deferred(); const responses = [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), () => gate.promise];
    if (action === "disconnect") responses.push(response({ status: "disconnected" }));
    if (action === "bfcache") responses.push(response(session({ last_ticket: ticket })));
    await withApp(responses, async ({ node, calls, submit, click, page }) => {
      const pending = submit(true); await flush(); const signal = calls.at(-1).signal;
      node("live-generative-consent").checked = true;
      if (action === "stop") await click("live-stop"); else if (action === "disconnect") await click("live-disconnect");
      else await page("pagehide");
      assert.equal(node("live-generative-consent").checked, false); assert.equal(signal.aborted, true);
      await pending; gate.resolve(response(envelope())); await flush(); assert.equal(node("live-final").textContent, "");
      if (action === "stop") { assert.match(node("live-notice").textContent, /Core pode continuar/); assert.equal(node("live-recover").disabled, false); }
      if (action === "bfcache") {
        await page("pageshow", true); await flush(); assert.equal(node("live-generative-consent").checked, false);
        assert.equal(calls.at(-1).url, "/api/session"); assert.equal(node("live-recover").disabled, false);
      }
    });
  });
}
test("foreign session clears consent/query/results before any foreign ticket delivery", async () => {
  await withApp([...flow(), response(session({ last_ticket: ticket, session_ref: "session://web-live/" + "f".repeat(32) }))],
    async ({ node, calls, submit, click }) => {
      await submit(true); node("live-generative-consent").checked = true; await click("live-recover");
      assert.equal(calls.length, 5); assert.equal(node("live-final").textContent, "");
      assert.equal(node("live-generative-consent").checked, false); assert.equal(node("live-query").value, "");
    });
});
test("invalid replacement removes all prior canonical display and generative labels", async () => {
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope("completed", {
    result: final({ generative_evidence_mode: "fixture" }) }))], async ({ node, submit, click }) => {
    await submit(true); await click("live-recover");
    for (const id of ["live-final", "live-result-query", "live-metadata", "live-governance"]) assert.equal(node(id).textContent, "");
    assert.equal(node("live-result").hidden, true); assert.equal(node("live-generative-consent").checked, false);
    assert.match(node("live-notice").textContent, /Resposta incompatível recusada/);
  });
});
test("checked duplicate form while busy cannot allocate another generative ticket", async () => {
  const gate = deferred();
  await withApp([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ node, calls, submit, click }) => {
    const pending = submit(true); await flush(); await submit(true); assert.equal(calls.length, 3);
    assert.equal(node("live-generative-consent").checked, false); await click("live-stop"); await pending;
    gate.resolve(response(envelope("running"), 202));
  });
});
