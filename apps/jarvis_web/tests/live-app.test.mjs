// Imports the actual LIVE app and measures DOM IDs from the actual served HTML.
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const markup = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
const ids = [...markup.matchAll(/\bid="([^"]+)"/g)].map((match) => match[1]);
assert.equal(new Set(ids).size, ids.length);
const ticket = "web-request-" + "a".repeat(32), csrf = "b".repeat(64);
const sessionRef = "session://web-live/" + "c".repeat(32), secret = "d".repeat(64);
const query = "Compare os relatórios de documentação e observabilidade do piloto.";
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: csrf, expires_in_seconds: 900, last_ticket: null, ...changes });
const final = (changes = {}) => ({ query, response_text: '<script>fetch("https://evil.invalid")</script> 😀\r\n **literal Markdown**',
  intent: "analysis", governance_decision: "allow", memory_record_ref: "mem-record-0123abcd",
  timestamp: "2026-10-06T12:00:00Z", evidence_mode: "core_local", generative_status: "disabled", authority: "none", ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: "jarvis-local-analysis-v1",
  status, ticket, error_code: null, result: status === "completed" ? final() : null, ...changes });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
const flush = () => new Promise((resolve) => setImmediate(resolve));
let sequence = 0;
class Element {
  constructor(id) { this.id = id; this.handlers = new Map(); this.disabled = false; this.hidden = false;
    this.value = ""; this.dataset = {}; this.attributes = new Map(); this._text = ""; this.focusCount = 0; }
  set textContent(value) { this._text = String(value); }
  get textContent() { return this._text; }
  set innerHTML(_value) { assert.fail("LIVE app used an HTML sink"); }
  setAttribute(name, value) { this.attributes.set(name, value); }
  addEventListener(name, callback) { const list = this.handlers.get(name) ?? []; list.push(callback); this.handlers.set(name, list); }
  async dispatch(name, changes = {}) { await Promise.all((this.handlers.get(name) ?? []).map((fn) => fn({
    target: this, preventDefault() {}, ...changes }))); }
  focus() { this.focusCount++; }
}
async function withApp(responses, callback) {
  const keys = ["document", "window", "fetch", "localStorage", "sessionStorage", "Audio", "AudioContext", "navigator"];
  const saved = new Map(keys.map((key) => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  const elements = new Map(ids.map((id) => [id, new Element(id)]));
  const node = (id) => { assert.ok(elements.has(id), `missing actual HTML ID ${id}`); return elements.get(id); };
  const windowEvents = new Element("window"), calls = [];
  const suggestions = [...markup.matchAll(/data-prompt="([^"]+)"/g)].map((match) => {
    const button = new Element(""); button.dataset.prompt = match[1]; return button;
  });
  const prohibited = () => assert.fail("storage/audio/external IO prohibited");
  const values = {
    document: { getElementById: node, querySelectorAll(selector) { assert.equal(selector, "[data-prompt]"); return suggestions; } },
    window: { addEventListener: windowEvents.addEventListener.bind(windowEvents) },
    fetch: async (url, init) => {
      assert.match(url, /^\/api\/(?:session|pair|tickets|analysis|disconnect|results\/web-request-[a-f0-9]{32})$/);
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
    await import(`../live-app.mjs?real-live-app=${++sequence}`); await flush();
    await callback({ node, calls, suggestions, page: (name, persisted = false) => windowEvents.dispatch(name, { persisted }),
      submit: async (value = query) => { node("live-query").value = value; await node("live-form").dispatch("submit"); },
      click: (id) => node(id).dispatch("click") });
  } finally {
    await windowEvents.dispatch("pagehide");
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
}
const flow = () => [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), response(envelope())];

test("actual live HTML/module/style are separate from fixtures and make no voice/action claims", () => {
  assert.match(markup, /src="\/live-app\.mjs"/); assert.match(markup, /href="\/live-style\.css"/);
  assert.doesNotMatch(markup, /fixtures\.mjs|voice-controller|<audio|<iframe/);
  assert.equal([...markup.matchAll(/type="file"/g)].length, 1);
  assert.match(markup, /id="live-audio-file" type="file" accept="\.wav,audio\/wav"/);
  assert.match(markup, /Não é voz automática nem fala ao vivo do Core/);
  assert.match(markup, /não uma identidade humana/); assert.match(markup, /Não cancela o Core/);
  assert.match(markup, /Sem modelo generativo, voz ou execução/);
  const style = readFileSync(new URL("../live-style.css", import.meta.url), "utf8");
  assert.match(style, /min-height:44px/); assert.match(style, /max-width:560px/);
  assert.match(style, /overflow-wrap:anywhere/); assert.match(style, /focus-visible/);
});
test("actual app boot only checks session, unauthenticated cannot dispatch analysis", async () => {
  await withApp([response({ error_code: "session_refused" }, 401)], async ({ node, calls, submit }) => {
    assert.equal(node("live-query").disabled, true); assert.equal(node("live-send").disabled, true);
    assert.equal(node("live-secret").disabled, false); await submit(); assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/session"); assert.equal(node("live-final").textContent, "");
  });
});
test("pairing password is cleared before actual fetch and secret never enters visible status", async () => {
  await withApp([response({ error_code: "session_refused" }, 401), (_url, init, { node }) => {
    assert.equal(node("live-secret").value, ""); assert.deepEqual(JSON.parse(init.body), { secret });
    return response(session());
  }], async ({ node, calls }) => {
    node("live-secret").value = secret; await node("live-pair-form").dispatch("submit");
    assert.equal(calls.length, 2); assert.equal(node("live-query").disabled, false);
    assert.match(node("live-session").textContent, /não identidade humana/);
    assert.doesNotMatch(node("live-notice").textContent, new RegExp(secret));
  });
});
for (const decision of ["allow", "block", "defer_for_validation"]) {
  test(`actual app preserves exact canonical text and ${decision} without HTML execution`, async () => {
    const responses = flow(); responses[3] = response(envelope("completed", { result: final({ governance_decision: decision }) }));
    await withApp(responses, async ({ node, submit, calls }) => {
      await submit(); assert.equal(node("live-final").textContent, final().response_text);
      assert.equal(node("live-result-query").textContent, query); assert.equal(node("live-result").hidden, false);
      assert.match(node("live-governance").textContent, new RegExp({ allow: "ALLOW", block: "BLOCK", defer_for_validation: "DEFER" }[decision]));
      assert.equal(calls.length, 4); assert.equal(node("live-form").attributes.get("aria-busy"), "false");
      assert.match(node("live-metadata").textContent, /modelo generativo desativado/);
    });
  });
}
test("suggestions only fill real Portuguese query, no automatic dispatch", async () => {
  await withApp([response(session())], async ({ node, suggestions, calls }) => {
    await suggestions[0].dispatch("click"); assert.equal(node("live-query").value, query);
    assert.equal(calls.length, 1); assert.equal(node("live-query").focusCount, 1);
    await suggestions[1].dispatch("click"); assert.equal(node("live-query").value, "Revise a documentação, o painel de telemetria e o relatório de baseline do piloto.");
    assert.equal(calls.length, 1);
  });
});
test("reload offers explicit recovery but no result request on boot", async () => {
  await withApp([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope())],
    async ({ node, calls, click }) => {
      assert.equal(calls.length, 1); assert.equal(node("live-recover").disabled, false);
      assert.equal(node("live-final").textContent, ""); await click("live-recover");
      assert.equal(node("live-final").textContent, final().response_text); assert.ok(calls.every((call) => call.method === "GET"));
    });
});
test("network uncertainty retains ticket and actual recovery performs only GET", async () => {
  await withApp([response(session()), response(envelope("issued"), 201), new Error("PRIVATE_QUERY_URL"),
    response(session({ last_ticket: ticket })), response(envelope())], async ({ node, calls, submit, click }) => {
    await submit(); assert.match(node("live-notice").textContent, /Não houve reenvio automático/);
    assert.doesNotMatch(node("live-notice").textContent, /PRIVATE_QUERY_URL/); assert.match(node("live-ticket").textContent, new RegExp(ticket));
    await click("live-recover"); assert.equal(node("live-final").textContent, final().response_text);
    assert.ok(calls.slice(3).every((call) => call.method === "GET"));
  });
});
for (const code of ["analysis_outcome_unknown", "analysis_expired"]) {
  test(`actual failed ${code} shows fixed notice without success or retry`, async () => {
    const responses = flow(); responses[3] = response(envelope("failed", { error_code: code }));
    await withApp(responses, async ({ node, submit, calls }) => {
      await submit(); assert.equal(node("live-result").hidden, true); assert.equal(node("live-final").textContent, "");
      assert.match(node("live-notice").textContent, code === "analysis_expired" ? /expirou/ : /Pode haver registro canônico/);
      assert.equal(calls.filter((call) => call.method === "POST").length, 2);
    });
  });
}
test("invalid replacement clears every prior canonical display", async () => {
  await withApp([...flow(), response(session({ last_ticket: ticket })),
    response(envelope("completed", { result: final({ authority: "admin" }) }))], async ({ node, submit, click }) => {
    await submit(); await click("live-recover"); assert.equal(node("live-final").textContent, "");
    assert.equal(node("live-result-query").textContent, ""); assert.equal(node("live-metadata").textContent, "");
    assert.equal(node("live-governance").textContent, ""); assert.equal(node("live-result").hidden, true);
    assert.match(node("live-notice").textContent, /Resposta incompatível recusada/);
  });
});
test("foreign session removes prior canonical and composer text without fetching foreign result", async () => {
  await withApp([...flow(), response(session({ session_ref: "session://web-live/" + "f".repeat(32), last_ticket: ticket }))],
    async ({ node, submit, click, calls }) => {
      await submit(); await click("live-recover"); assert.equal(calls.length, 5);
      assert.equal(node("live-final").textContent, ""); assert.equal(node("live-query").value, "");
      assert.equal(node("live-ticket").textContent, ""); assert.equal(node("live-send").disabled, true);
      assert.match(node("live-notice").textContent, /sessão mudou/);
    });
});
for (const action of ["stop", "disconnect", "pagehide", "bfcache"]) {
  test(`actual ${action} invalidates pending result and never reports Core rollback`, async () => {
    const gate = deferred();
    const responses = [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), () => gate.promise];
    if (action === "disconnect") responses.push(response({ status: "disconnected" }));
    if (action === "bfcache") responses.push(response(session({ last_ticket: ticket })));
    await withApp(responses, async ({ node, calls, submit, click, page }) => {
      const pending = submit(); await flush(); const prior = calls.at(-1);
      if (action === "stop") await click("live-stop");
      else if (action === "disconnect") await click("live-disconnect");
      else await page("pagehide", action === "bfcache");
      assert.equal(prior.signal.aborted, true); assert.equal(node("live-final").textContent, "");
      if (action === "stop") {
        assert.match(node("live-notice").textContent, /Core pode continuar/); assert.equal(node("live-recover").disabled, false);
      } else { assert.equal(node("live-ticket").textContent, ""); assert.equal(node("live-query").value, ""); }
      gate.resolve(response(envelope())); await pending; assert.equal(node("live-final").textContent, "");
      if (action === "bfcache") {
        await page("pageshow", true); await flush(); assert.equal(node("live-recover").disabled, false);
        assert.equal(node("live-final").textContent, ""); assert.equal(calls.at(-1).url, "/api/session");
      }
    });
  });
}
test("direct duplicate form events while pending issue no second POST", async () => {
  const gate = deferred();
  await withApp([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ submit, calls, click }) => {
    const pending = submit(); await flush(); await submit(); assert.equal(calls.length, 3);
    await click("live-stop"); gate.resolve(response(envelope("running"), 202)); await pending;
    assert.equal(calls.filter((call) => call.url === "/api/analysis").length, 1);
  });
});

function assertPublicPresenceContext(node) {
  const text = ["live-title", "live-context-model", "live-context-memory", "live-context-session"]
    .map((id) => node(id).textContent).join("\n");
  assert.doesNotMatch(text, /estou ouvindo|estou escutando|microfone ativo|fala ao vivo/iu);
  assert.doesNotMatch(text, /session:\/\/|\b(?:gpt|claude|gemini)[-_0-9]/iu);
  for (const privateValue of [sessionRef, secret, csrf]) assert.equal(text.includes(privateValue), false);
}

for (const paired of [false, true]) {
  test(`cinematic boot reflects ${paired ? "paired" : "unpaired"} state without invented model, memory, or listening`, async () => {
    await withApp([paired ? response(session()) : response({ error_code: "session_refused" }, 401)],
      async ({ node, calls }) => {
        assert.equal(calls.length, 1); assert.equal(calls[0].url, "/api/session");
        assert.equal(node("live-context-model").textContent, "Não informado pelo host");
        assert.equal(node("live-context-memory").textContent, "Sem registro nesta tela");
        assert.equal(node("live-context-session").textContent, paired ? "Sessão local pareada" : "Não pareada");
        assert.equal(node("live-title").textContent, paired ? "Pronto para conversar" : "Um ajuste antes de continuar");
        assert.equal(node("live-generative-consent").checked, false);
        assert.equal(node("live-final").textContent, ""); assertPublicPresenceContext(node);
      });
  });
}

for (const [id, expected] of [
  ["live-briefing-compare", query],
  ["live-briefing-review", "Revise a documentação, o painel de telemetria e o relatório de baseline do piloto."],
]) {
  test(`${id} only fills and focuses the composer without network, consent, or canonical changes`, async () => {
    await withApp([response(session())], async ({ node, calls, click }) => {
      const before = calls.length, focus = node("live-query").focusCount;
      assert.equal(node(id).disabled, false); assert.equal(node("live-generative-consent").checked, false);
      await click(id);
      assert.equal(node("live-query").value, expected); assert.equal(node("live-query").focusCount, focus + 1);
      assert.equal(calls.length, before); assert.equal(node("live-generative-consent").checked, false);
      assert.equal(node("live-final").textContent, ""); assert.equal(node("live-result").hidden, true);
      assertPublicPresenceContext(node);
    });
  });
  test(`${id} cannot prepare or dispatch a query in an unpaired session even with a forged click`, async () => {
    await withApp([response({ error_code: "session_refused" }, 401)], async ({ node, calls, click }) => {
      const focus = node("live-query").focusCount;
      node("live-query").value = "Rascunho local não enviado";
      assert.equal(node(id).disabled, true); await click(id);
      assert.equal(node("live-query").value, "Rascunho local não enviado");
      assert.equal(node("live-query").focusCount, focus); assert.equal(calls.length, 1);
      assert.equal(node("live-generative-consent").checked, false);
    });
  });
}

test("Briefing configuration link opens and focuses pairing without a submission or new request", async () => {
  await withApp([response(session())], async ({ node, calls, click }) => {
    node("live-pairing-details").open = false;
    const focus = node("live-pairing-summary").focusCount;
    await click("live-briefing-settings");
    assert.equal(node("live-pairing-details").open, true);
    assert.equal(node("live-pairing-summary").focusCount, focus + 1);
    assert.equal(node("live-query").value, ""); assert.equal(node("live-generative-consent").checked, false);
    assert.equal(calls.length, 1); assert.equal(node("live-context-session").textContent, "Sessão local pareada");
  });
});

test("pairing changes the cinematic context only after the verified local response and never displays its secret", async () => {
  const gate = deferred();
  await withApp([response({ error_code: "session_refused" }, 401), () => gate.promise],
    async ({ node, calls }) => {
      node("live-secret").value = secret;
      const pairing = node("live-pair-form").dispatch("submit"); await flush();
      assert.equal(node("live-secret").value, "");
      assert.equal(node("live-title").textContent, "Conectando ao seu Core…");
      assert.equal(node("live-context-session").textContent, "Verificando…");
      assert.equal(node("live-context-model").textContent, "Não informado pelo host");
      assertPublicPresenceContext(node);
      gate.resolve(response(session())); await pairing;
      assert.equal(node("live-title").textContent, "Pronto para conversar");
      assert.equal(node("live-context-session").textContent, "Sessão local pareada");
      assert.equal(node("live-context-memory").textContent, "Sem registro nesta tela");
      assert.equal(calls.length, 2); assertPublicPresenceContext(node);
    });
});

test("submitting, waiting, and completed update the cinematic context while preserving exact native final bytes", async () => {
  const issued = deferred(), completed = deferred();
  await withApp([response(session()), () => issued.promise, response(envelope("running"), 202), () => completed.promise],
    async ({ node, calls, click, submit }) => {
      assert.equal(node("live-title").textContent, "Pronto para conversar");
      const pending = submit(); await flush();
      assert.equal(node("live-title").textContent, "Seu pedido está a caminho");
      assert.equal(node("live-context-session").textContent, "Sessão local pareada");
      assert.equal(node("live-context-memory").textContent, "Sem registro nesta tela");
      assert.equal(node("live-context-model").textContent, "Não informado pelo host");
      assert.equal(node("live-final").textContent, "");
      const before = calls.length, focus = node("live-query").focusCount;
      for (const id of ["live-briefing-compare", "live-briefing-review"]) {
        assert.equal(node(id).disabled, true); await click(id);
      }
      assert.equal(node("live-query").value, query); assert.equal(node("live-query").focusCount, focus);
      assert.equal(calls.length, before); assert.equal(node("live-generative-consent").checked, false);
      issued.resolve(response(envelope("issued"), 201)); await flush();
      assert.equal(node("live-title").textContent, "Preparando sua resposta…");
      assert.equal(node("live-context-memory").textContent, "Sem registro nesta tela");
      assert.equal(node("live-context-model").textContent, "Não informado pelo host");
      assertPublicPresenceContext(node);
      completed.resolve(response(envelope())); await pending;
      assert.equal(node("live-title").textContent, "Aqui está sua resposta");
      assert.equal(node("live-context-memory").textContent, "Final canônica recebida");
      assert.equal(node("live-context-model").textContent, "Resposta nativa");
      assert.equal(node("live-final").textContent, final().response_text);
      assert.equal(node("live-result-query").textContent, query); assert.equal(calls.length, 4);
      assertPublicPresenceContext(node);
    });
});

for (const [status, evidenceMode, expected] of [
  ["accepted", "injected_transport", "Complemento de teste"],
  ["accepted", "live", "Complemento não verificado"],
  ["rejected", null, "Complemento recusado"],
  ["withheld", null, "Complemento retido"],
]) {
  test(`recovered ${status}/${evidenceMode} context labels only the public status, not an invented model`, async () => {
    const value = final({ generative_status: status, generative_evidence_mode: evidenceMode,
      generative_error_code: status === "accepted" ? null : "scope_denied",
      generative_analysis_characters: status === "accepted" ? 1 : 0 });
    await withApp([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })),
      response(envelope("completed", { schema_version: "jarvis-local-analysis-v2", result: value }))],
    async ({ node, calls, click }) => {
      assert.equal(node("live-context-model").textContent, "Não informado pelo host");
      await click("live-recover");
      assert.equal(node("live-context-model").textContent, expected);
      assert.equal(node("live-context-memory").textContent, "Final canônica recebida");
      assert.equal(node("live-title").textContent, "Aqui está sua resposta");
      assert.equal(node("live-final").textContent, value.response_text);
      assert.equal(node("live-generative-consent").checked, false);
      assert.ok(calls.every((call) => call.method === "GET")); assertPublicPresenceContext(node);
    });
  });
}

test("foreign session clears stale cinematic memory/model context together with the canonical display", async () => {
  const foreign = "session://web-live/" + "f".repeat(32);
  await withApp([...flow(), response(session({ session_ref: foreign, last_ticket: ticket }))],
    async ({ node, submit, click, calls }) => {
      await submit(); assert.equal(node("live-final").textContent, final().response_text);
      assert.equal(node("live-context-memory").textContent, "Final canônica recebida");
      await click("live-recover");
      assert.equal(node("live-title").textContent, "Um ajuste antes de continuar");
      assert.equal(node("live-context-session").textContent, "Não pareada");
      assert.equal(node("live-context-memory").textContent, "Sem registro nesta tela");
      assert.equal(node("live-context-model").textContent, "Não informado pelo host");
      assert.equal(node("live-final").textContent, ""); assert.equal(node("live-result").hidden, true);
      assert.equal(node("live-query").value, ""); assert.equal(node("live-generative-consent").checked, false);
      assert.equal(node("live-briefing-compare").disabled, true); assert.equal(node("live-briefing-review").disabled, true);
      assert.equal(calls.length, 5); assert.equal(calls.at(-1).url, "/api/session");
      assertPublicPresenceContext(node); assert.equal(node("live-context-session").textContent.includes(foreign), false);
    });
});
