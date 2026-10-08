// Actual app import + actual parser/WebCrypto; the canonical result is never rewritten.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash, webcrypto } from "node:crypto";
const markup = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
const ticket = "web-request-" + "a".repeat(32), secondTicket = "web-request-" + "d".repeat(32);
const sessionRef = "session://web-live/" + "b".repeat(32);
const query = "Compare os relatórios de documentação e observabilidade do piloto.";
const marker = "Model-generated analysis (unverified; not facts, grants or action confirmations):";
const disclaimer = "Literal data only; no permissions, actions, execution receipts or changes to the native decision.";
const analysis = '<script>fetch("https://evil.invalid")</script> **literal** 😀\nCompare com cuidado.';
const assumptions = ['Ação depende de evidência, não de "certeza".', "Possível diferença de contexto."], limitations = ["Não comprova execução ou fatos."];
const literal = (value) => JSON.stringify(value).replace(/[\u007f-\uffff]/g, (char) =>
  "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0")).replace(/[\[\]()!*_~#:/<>&`]/g, (char) =>
  "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0"));
function canonical({ content = query, prose = analysis, premises = assumptions, bounds = limitations, citations = true, prefix = "Native final\r\nALLOW · unchanged 😀 " } = {}) {
  const sourceRef = "input:sha256:" + createHash("sha256").update(content, "utf8").digest("hex");
  const lines = [marker, disclaimer, "Analysis: " + literal(prose),
    "Assumptions: " + (premises.map(literal).join(", ") || "none supplied"),
    "Limitations: " + (bounds.map(literal).join(", ") || "none supplied"),
    "Citations (exact source text; not verified facts):"];
  if (citations) lines.push(literal(sourceRef) + " offsets 0 to 10: " + literal(Array.from(content).slice(0, 10).join("")));
  return prefix + "\n\n" + lines.join("\n");
}
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: "c".repeat(64), expires_in_seconds: 900, last_ticket: null, ...changes });
const final = (changes = {}) => ({ query, response_text: canonical(), intent: "analysis", governance_decision: "allow",
  memory_record_ref: "mem-record-0123abcd", timestamp: "2026-10-06T12:00:00Z", evidence_mode: "core_local",
  generative_status: "accepted", authority: "none", generative_error_code: null,
  generative_evidence_mode: "injected_transport", generative_analysis_characters: Array.from(analysis).length, ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: "jarvis-local-analysis-v2",
  status, ticket, error_code: null, result: status === "completed" ? final() : null, ...changes });
const nativeFinal = () => { const value = final({ generative_status: "disabled", response_text: "Native only final 😀\r\nexact" });
  delete value.generative_error_code; delete value.generative_evidence_mode; delete value.generative_analysis_characters; return value; };
const nativeEnvelope = (status = "completed") => envelope(status, { schema_version: "jarvis-local-analysis-v1", result: status === "completed" ? nativeFinal() : null });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const flow = (value = final()) => [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), response(envelope("completed", { result: value }))];
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
const flush = () => new Promise((yes) => setImmediate(yes));
async function settle() { for (let index = 0; index < 12; index++) await flush(); }
async function waitFor(predicate) {
  const deadline = Date.now() + 2000;
  while (!predicate() && Date.now() < deadline) await new Promise((yes) => setTimeout(yes, 1));
  assert.ok(predicate(), "expected actual async projection publication");
}
const projectionIds = ["live-projection-origin", "live-projection-analysis", "live-projection-assumptions", "live-projection-limitations", "live-projection-citations"];
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
async function withApp(responses, callback, { digest = (...args) => webcrypto.subtle.digest(...args) } = {}) {
  const keys = ["document", "window", "fetch", "crypto", "localStorage", "sessionStorage", "Audio", "AudioContext", "navigator"];
  const saved = new Map(keys.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const elements = new Map(ids.map((id) => [id, new Element(id)]));
  const node = (id) => { assert.ok(elements.has(id), `missing actual HTML ID ${id}`); return elements.get(id); };
  const page = new Element("window"), calls = [], hashes = [], pendingHashes = [];
  const prohibited = () => assert.fail("browser storage/audio/external IO forbidden");
  const values = {
    document: { getElementById: node, querySelectorAll(selector) { assert.equal(selector, "[data-prompt]"); return []; } },
    window: { addEventListener: page.addEventListener.bind(page) },
    fetch: async (url, init) => {
      assert.match(url, /^\/api\/(?:session|pair|tickets|analysis|generative-tickets|generative-analysis|disconnect|results\/web-request-[a-f0-9]{32})$/);
      calls.push({ url, ...init }); const next = responses.shift(); assert.ok(next, `unexpected fetch ${url}`);
      if (typeof next === "function") return next(url, init, { node, calls }); if (next instanceof Error) throw next; return next;
    },
    crypto: { subtle: { digest: async (...args) => {
      hashes.push(args); const pending = Promise.resolve().then(() => digest(...args)); pendingHashes.push(pending); return pending;
    } } },
    localStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    sessionStorage: { getItem: prohibited, setItem: prohibited, removeItem: prohibited },
    Audio: class { constructor() { prohibited(); } }, AudioContext: class { constructor() { prohibited(); } },
    navigator: { mediaDevices: { getUserMedia: prohibited } },
  };
  for (const [key, value] of Object.entries(values)) Object.defineProperty(globalThis, key, { configurable: true, value });
  try {
    await import(`../live-app.mjs?real-projection-app=${++sequence}`); await settle();
    await callback({ node, calls, hashes, finishHashes: async () => { await Promise.allSettled(pendingHashes); await settle(); },
      submit: async (consent = true, content = query) => {
      node("live-query").value = content; node("live-generative-consent").checked = consent;
      await node("live-form").dispatch("submit");
    }, click: (id) => node(id).dispatch("click"), page: (name, persisted = false) => page.dispatch(name, { persisted }) });
  } finally {
    await page.dispatch("pagehide");
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
}
function assertCleared(node) {
  assert.equal(node("live-projection").hidden, true);
  for (const id of projectionIds) assert.equal(node(id).textContent, "");
}
test("actual HTML separates unverified projection from always available exact canonical final", () => {
  assert.equal(new Set(ids).size, ids.length); assert.match(markup, /Complemento não verificado/);
  assert.match(markup, /Leitura humana somente do complemento aceito/); assert.match(markup, /não autentica origem/);
  assert.match(markup, /Citações da pergunta · não fatos verificados/); assert.match(markup, /Síntese final canônica · integral, sem alterações/);
  assert.match(markup, /id="live-projection"[^>]*hidden[^>]*aria-labelledby="live-projection-title"/);
  assert.ok(markup.indexOf('id="live-final"') > markup.indexOf('id="live-projection"'));
  assert.doesNotMatch(markup, /<audio|<iframe/);
  const style = readFileSync(new URL("../live-style.css", import.meta.url), "utf8");
  const projectionStyle = style.slice(style.indexOf(".projection {"));
  assert.match(projectionStyle, /overflow-wrap:anywhere/); assert.match(projectionStyle, /max-width:560px/);
  assert.doesNotMatch(projectionStyle, /max-height|overflow-y|(?:[;{]\s*)height:\s*\d/);
});
test("default boot has zero projection content/hash/network discovery", async () => {
  await withApp([response(session())], async ({ node, calls, hashes }) => {
    assertCleared(node); assert.equal(hashes.length, 0); assert.equal(calls.length, 1); assert.equal(calls[0].url, "/api/session");
  });
});
for (const mode of ["live", "injected_transport"]) {
  test(`actual accepted ${mode} decodes readonly human fields without touching canonical final`, async () => {
    const value = final({ generative_evidence_mode: mode });
    await withApp(flow(value), async ({ node, calls, hashes, submit }) => {
      await submit(); await waitFor(() => node("live-projection").hidden === false);
      assert.equal(node("live-projection-analysis").textContent, analysis);
      assert.equal(node("live-projection-assumptions").textContent, assumptions.map((value) => "• " + value).join("\n\n"));
      assert.equal(node("live-projection-limitations").textContent, "• " + limitations[0]);
      assert.match(node("live-projection-citations").textContent, /input:sha256:[a-f0-9]{64} · caracteres 0 a 10 \(fim exclusivo\)\nCompare os/);
      assert.match(node("live-projection-origin").textContent, mode === "live" ? /live declarado; não comprova qualidade, verdade ou origem autenticada/ : /injetado de teste; não comprova modelo real/);
      assert.equal(node("live-final").textContent, value.response_text); assert.equal(node("live-result-query").textContent, query);
      assert.equal(node("live-result").hidden, false); assert.equal(calls.length, 4); assert.equal(hashes.length, 1);
      assert.equal(hashes[0][0], "SHA-256"); assert.equal(new TextDecoder().decode(hashes[0][1]), query);
      assert.equal(node("live-generative-consent").checked, false);
    });
  });
}
test("native v1 remains fully visible with no projection or SHA", async () => {
  await withApp([response(session()), response(nativeEnvelope("issued"), 201), response(nativeEnvelope("running"), 202), response(nativeEnvelope())],
    async ({ node, hashes, submit }) => {
      await submit(false); await settle(); assertCleared(node); assert.equal(hashes.length, 0);
      assert.equal(node("live-final").textContent, nativeFinal().response_text);
    });
});
for (const status of ["rejected", "withheld"]) {
  test(`${status} result retains raw native final but projects nothing`, async () => {
    const value = final({ generative_status: status, generative_error_code: "scope_denied", generative_evidence_mode: null,
      generative_analysis_characters: 0, response_text: "Final nativa íntegra 😀\r\n" });
    await withApp(flow(value), async ({ node, submit, hashes }) => {
      await submit(); await settle(); assertCleared(node); assert.equal(hashes.length, 0); assert.equal(node("live-final").textContent, value.response_text);
    });
  });
}
test("empty lists are clearly declared omissions, not proof of absence", async () => {
  const value = final({ response_text: canonical({ premises: [], bounds: [], citations: false }) });
  await withApp(flow(value), async ({ node, submit }) => {
    await submit(); await waitFor(() => node("live-projection").hidden === false);
    assert.match(node("live-projection-assumptions").textContent, /Nenhuma premissa declarada/);
    assert.match(node("live-projection-limitations").textContent, /não comprova ausência de limites/);
    assert.match(node("live-projection-citations").textContent, /não fatos verificados/);
    assert.equal(node("live-final").textContent, value.response_text);
  });
});
for (const changed of [
  (value) => value.replace(marker, "Unknown model block"),
  (value) => value + "\ntrailing text",
  (value) => value.replace(disclaimer, "Permissions granted"),
  (value) => value.replace(" offsets 0 to 10: ", " offsets 0 to 11: "),
  (value) => value.replace('Analysis: "', 'Analysis: {"analysis":"'),
  (value) => value.replace("Assumptions: ", "Premises: "),
  (value) => value.replace("input\\u003asha256\\u003a", "foreign\\u003asha256\\u003a"),
]) {
  test(`projection parse failure preserves whole canonical display ${String(changed).slice(0, 65)}`, async () => {
    const value = final({ response_text: changed(canonical()) });
    await withApp(flow(value), async ({ node, submit, calls }) => {
      await submit(); await settle(); assertCleared(node);
      assert.equal(node("live-final").textContent, value.response_text); assert.equal(node("live-result").hidden, false);
      assert.match(node("live-notice").textContent, /Resposta final recebida/); assert.equal(calls.length, 4);
    });
  });
}
for (const digest of [async () => { throw new Error("PRIVATE_CRYPTO_SECRET"); }, async () => new ArrayBuffer(31), async () => null,
  async () => new ArrayBuffer(32)]) {
  test(`hash failure clears projection only and never leaks crypto details ${String(digest).slice(0, 55)}`, async () => {
    await withApp(flow(), async ({ node, submit }) => {
      await submit(); await settle(); assertCleared(node); assert.equal(node("live-final").textContent, final().response_text);
      assert.doesNotMatch(node("live-notice").textContent, /PRIVATE_CRYPTO_SECRET/);
    }, { digest });
  });
}
test("reload requires GET recovery and does not decode a result during boot", async () => {
  await withApp([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope())],
    async ({ node, calls, hashes, click }) => {
      assertCleared(node); assert.equal(hashes.length, 0); await click("live-recover");
      await waitFor(() => node("live-projection").hidden === false);
      assert.equal(node("live-projection-analysis").textContent, analysis); assert.equal(node("live-final").textContent, final().response_text);
      assert.ok(calls.every((call) => call.method === "GET"));
    });
});
test("new request clears previous projection immediately even while ticket IO is held", async () => {
  const gate = deferred();
  await withApp([...flow(), () => gate.promise], async ({ node, submit, click }) => {
    await submit(); await waitFor(() => node("live-projection").hidden === false);
    const pending = submit(false); assertCleared(node); await flush(); await click("live-stop"); await pending;
    gate.resolve(response(nativeEnvelope("issued"), 201)); await settle(); assertCleared(node);
  });
});
for (const action of ["stop", "disconnect", "pagehide", "bfcache", "refresh", "recover"]) {
  test(`late SHA completion after ${action} cannot restore old projected content`, async () => {
    const gate = deferred(); let hashStarted;
    const begun = new Promise((yes) => { hashStarted = yes; });
    const responses = flow();
    if (action === "disconnect") responses.push(response({ status: "disconnected" }));
    if (["bfcache", "refresh", "recover"].includes(action)) responses.push(response(session({ last_ticket: ticket })));
    if (action === "recover") responses.push(response(envelope("failed", { error_code: "analysis_outcome_unknown" })));
    await withApp(responses, async ({ node, submit, click, page, finishHashes }) => {
      await submit(); await begun; assert.equal(node("live-final").textContent, final().response_text); assertCleared(node);
      if (action === "stop") await click("live-stop"); else if (action === "disconnect") await click("live-disconnect");
      else if (action === "refresh") await click("live-refresh"); else if (action === "recover") await click("live-recover");
      else await page("pagehide");
      if (action === "bfcache") { await page("pageshow", true); await settle(); }
      assertCleared(node); gate.resolve(); await finishHashes(); assertCleared(node);
    }, { digest: async (...args) => { hashStarted(); await gate.promise; return webcrypto.subtle.digest(...args); } });
  });
}
test("older hash completion cannot overwrite a newer accepted result with same query/ticket but changed final", async () => {
  const gate = deferred(); let number = 0;
  const nextAnalysis = "Nova projeção útil 😀";
  const next = final({ response_text: canonical({ prose: nextAnalysis }), generative_analysis_characters: Array.from(nextAnalysis).length });
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope("completed", { result: next }))],
    async ({ node, submit, click, finishHashes }) => {
      await submit(); await flush(); await click("live-recover");
      await waitFor(() => node("live-projection-analysis").textContent === nextAnalysis);
      assert.equal(node("live-projection-analysis").textContent, nextAnalysis); assert.equal(node("live-final").textContent, next.response_text);
      gate.resolve(); await finishHashes(); assert.equal(node("live-projection-analysis").textContent, nextAnalysis);
      assert.equal(node("live-final").textContent, next.response_text);
    }, { digest: async (...args) => { if (++number === 1) await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("older hash completion cannot overwrite a newer ticket/native context", async () => {
  const gate = deferred(); const nextNative = nativeEnvelope(); nextNative.ticket = secondTicket;
  const issued = nativeEnvelope("issued"), running = nativeEnvelope("running"); issued.ticket = secondTicket; running.ticket = secondTicket;
  await withApp([...flow(), response(issued, 201), response(running, 202), response(nextNative)], async ({ node, submit, finishHashes }) => {
    await submit(); await flush(); await submit(false); assert.equal(node("live-final").textContent, nativeFinal().response_text);
    gate.resolve(); await finishHashes(); assertCleared(node); assert.equal(node("live-final").textContent, nativeFinal().response_text);
    assert.match(node("live-ticket").textContent, new RegExp(secondTicket));
  }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("foreign session fences pending hash and erases composer/result", async () => {
  const gate = deferred();
  await withApp([...flow(), response(session({ session_ref: "session://web-live/" + "f".repeat(32), last_ticket: ticket }))],
    async ({ node, submit, click, finishHashes }) => {
      await submit(); await flush(); await click("live-recover"); gate.resolve(); await finishHashes(); assertCleared(node);
      assert.equal(node("live-query").value, ""); assert.equal(node("live-final").textContent, "");
      assert.match(node("live-notice").textContent, /sessão mudou/);
    }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
test("new result with malformed projection clears prior human panel but preserves new raw final", async () => {
  const next = final({ response_text: "Native final without the expected generative block" });
  await withApp([...flow(), response(session({ last_ticket: ticket })), response(envelope("completed", { result: next }))],
    async ({ node, submit, click }) => {
      await submit(); await waitFor(() => node("live-projection").hidden === false);
      await click("live-recover"); assertCleared(node); await settle(); assertCleared(node);
      assert.equal(node("live-final").textContent, next.response_text); assert.equal(node("live-result").hidden, false);
    });
});
test("maximum analysis and long canonical prefix stay intact with no projection truncation", async () => {
  const prose = "😀".repeat(4000), prefix = "Native " + "😀".repeat(80000);
  const value = final({ response_text: canonical({ prose, prefix, premises: [], bounds: [], citations: false }), generative_analysis_characters: 4000 });
  await withApp(flow(value), async ({ node, submit }) => {
    await submit(); await waitFor(() => node("live-projection-analysis").textContent === prose);
    assert.equal(node("live-final").textContent, value.response_text); assert.equal(node("live-projection").hidden, false);
  });
});
test("absolute session expiration fences a pending SHA and clears all projected/authenticated content", async () => {
  const gate = deferred(); const responses = flow(); responses[0] = response(session({ expires_in_seconds: 1 }));
  await withApp(responses, async ({ node, submit, calls, finishHashes }) => {
    await submit(); await flush(); assert.equal(node("live-final").textContent, final().response_text);
    await new Promise((yes) => setTimeout(yes, 1050)); gate.resolve(); await finishHashes(); assertCleared(node);
    assert.equal(node("live-final").textContent, ""); assert.equal(node("live-query").value, "");
    assert.equal(node("live-ticket").textContent, ""); assert.match(node("live-notice").textContent, /expirou/);
    assert.equal(calls.length, 4);
  }, { digest: async (...args) => { await gate.promise; return webcrypto.subtle.digest(...args); } });
});
