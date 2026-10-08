import test from "node:test";
import assert from "node:assert/strict";
import { createLiveController } from "../live-controller.mjs";

const ticket = "web-request-" + "a".repeat(32);
const secondTicket = "web-request-" + "b".repeat(32);
const sessionRef = "session://web-live/" + "c".repeat(32);
const secret = "d".repeat(64), csrf = "e".repeat(64);
const query = "Compare documentation and observability pilot reports.";
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: csrf, expires_in_seconds: 900, last_ticket: null, ...changes });
const result = (changes = {}) => ({ query, response_text: "Final nativa.\r\n <script>alert(1)</script> 😀",
  intent: "analysis", governance_decision: "allow", memory_record_ref: "mem-record-0123abcd",
  timestamp: "2026-10-06T20:12:15.123456+00:00", evidence_mode: "core_local", generative_status: "disabled",
  authority: "none", ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: "jarvis-local-analysis-v1",
  status, ticket, error_code: status === "failed" ? "analysis_outcome_unknown" : null,
  result: status === "completed" ? result() : null, ...changes });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { resolve, promise }; };
const flush = () => new Promise((resolve) => setImmediate(resolve));
function rig(responses, options = {}) {
  const calls = [], states = [];
  const client = createLiveController({ pollIntervalMs: 0, waitTimeoutMs: 1000, ...options,
    onState: (state) => states.push(state), transport: async (url, init) => {
      calls.push({ url, ...init });
      const next = responses.shift(); if (typeof next === "function") return next(url, init);
      if (next instanceof Error) throw next;
      assert.ok(next, `unexpected request ${url}`); return next;
    } });
  return { client, calls, states };
}
async function run(responses, callback, options) {
  const fixture = rig(responses, options);
  try { await callback(fixture); } finally { fixture.client.pageHide(); }
}
const initial = () => [response(session()), response(envelope("issued"), 201),
  response(envelope("running"), 202), response(envelope())];

test("native full flow authenticates, issues exactly one ticket and one analysis, exact canonical final", async () => {
  await run(initial(), async ({ client, calls }) => {
    await client.initialize(); const state = await client.submit(query);
    assert.equal(state.status, "completed"); assert.deepEqual(state.result, result());
    assert.deepEqual(calls.map(({ url }) => url), ["/api/session", "/api/tickets", "/api/analysis", "/api/results/" + ticket]);
    assert.deepEqual(JSON.parse(calls[1].body), {});
    assert.deepEqual(JSON.parse(calls[2].body), { ticket, query });
    for (const call of calls) {
      assert.equal(call.headers["X-Jarvis-Client"], "local-web-v1");
      assert.equal(call.mode, "same-origin"); assert.equal(call.credentials, "same-origin");
      assert.equal(call.cache, "no-store"); assert.equal(call.redirect, "error");
      assert.equal(call.headers.Origin, undefined);
      assert.equal(call.headers["X-Jarvis-CSRF"], call.url === "/api/session" ? undefined : csrf);
    }
    assert.ok(Object.isFrozen(state)); assert.ok(Object.isFrozen(state.result));
    assert.equal(state.csrf_token, undefined); assert.equal(state.secret, undefined);
  });
});

test("pair sends only explicit secret, no CSRF and does not duplicate while busy", async () => {
  const gate = deferred();
  await run([() => gate.promise], async ({ client, calls }) => {
    const pending = client.pair(secret); await client.pair(secret);
    assert.equal(calls.length, 1); assert.equal(calls[0].url, "/api/pair");
    assert.deepEqual(JSON.parse(calls[0].body), { secret }); assert.equal(calls[0].headers["X-Jarvis-CSRF"], undefined);
    gate.resolve(response(session())); await pending; assert.equal(client.getState().status, "ready");
  });
});

for (const bad of [null, false, "", "D".repeat(64), "d".repeat(63), "d".repeat(65), { secret }]) {
  test(`invalid pairing secret ${JSON.stringify(bad)} performs no fetch`, async () => {
    await run([], async ({ client, calls }) => {
      await client.pair(bad); assert.equal(calls.length, 0); assert.equal(client.getState().errorCode, "invalid_secret");
    });
  });
}
for (const bad of ["", "   ", "a".repeat(4001), "x\u0000y", "x\u200by", "x\u2028y", "x\u2029y", "\ud800", null, 3]) {
  test(`invalid query ${JSON.stringify(bad).slice(0, 65)} never issues a ticket`, async () => {
    await run([response(session())], async ({ client, calls }) => {
      await client.initialize(); await client.submit(bad); assert.equal(calls.length, 1);
      assert.equal(client.getState().errorCode, "invalid_query");
    });
  });
}

const sessionMutations = [
  { schema_version: "other" }, { authenticated: false }, { authenticated: "true" },
  { session_ref: "session://web-live/" + "C".repeat(32) }, { session_ref: sessionRef + "x" },
  { csrf_token: "a".repeat(63) }, { csrf_token: "A".repeat(64) }, { expires_in_seconds: 0 },
  { expires_in_seconds: 901 }, { expires_in_seconds: 1.5 }, { last_ticket: "foreign" }, { authority: "admin" },
  { session_ref: [sessionRef] }, { csrf_token: [csrf] }, { last_ticket: [ticket] },
];
for (const mutation of sessionMutations) {
  test(`invalid session fails closed ${JSON.stringify(mutation)}`, async () => {
    await run([response(session(mutation))], async ({ client }) => {
      await client.initialize(); assert.equal(client.getState().sessionRef, null);
      assert.equal(client.getState().errorCode, "invalid_response");
    });
  });
}

const resultMutations = [
  { authority: "admin" }, { model: "SECRET" }, { generative_status: "accepted" },
  { evidence_mode: "fixture" }, { intent: "Analysis" }, { intent: "a".repeat(65) },
  { memory_record_ref: "mem-record-0123ABCD" }, { timestamp: "2026-02-30T12:00:00Z" },
  { timestamp: "2026-10-06T12:00:00-03:00" }, { timestamp: "0000-01-01T00:00:00Z" },
  { timestamp: "2026-01-01T24:00:00Z" }, { timestamp: "2026-01-01T00:00:60Z" },
  { response_text: "\u0000" }, { response_text: "\u200b" }, { response_text: "\ud800" },
  { response_text: "\u2028" }, { response_text: "\u2029" }, { response_text: " " },
  { response_text: "a".repeat(131073) }, { query: query + " foreign" },
  { governance_decision: "ALLOW" }, { response_text: null },
  { memory_record_ref: ["mem-record-0123abcd"] },
];
for (const mutation of resultMutations) {
  test(`invalid canonical final refused ${Object.keys(mutation)[0]} ${String(Object.values(mutation)[0]).slice(0, 50)}`, async () => {
    const responses = initial(); responses[3] = response(envelope("completed", { result: result(mutation) }));
    await run(responses, async ({ client }) => {
      await client.initialize(); await client.submit(query);
      assert.equal(client.getState().result, null); assert.equal(client.getState().errorCode, "invalid_response");
    });
  });
}
for (const decision of ["allow", "block", "defer_for_validation"]) {
  test(`canonical governance ${decision} remains literal, no synthetic success`, async () => {
    const responses = initial(); responses[3] = response(envelope("completed", { result: result({ governance_decision: decision }) }));
    await run(responses, async ({ client }) => {
      await client.initialize(); await client.submit(query); assert.equal(client.getState().result.governance_decision, decision);
    });
  });
}
for (const mutation of [{ ticket: secondTicket }, { ticket: "invalid" }, { schema_version: "other" },
  { status: "dispatched" }, { error_code: "grant_admin" }, { extra: true },
  { ticket: [ticket] }, { status: "running", result: result() },
  { status: "failed", error_code: "analysis_busy", result: null }, { status: "failed", error_code: null, result: null }]) {
  test(`invalid envelope ${JSON.stringify(mutation).slice(0, 80)} clears result`, async () => {
    const responses = initial(); responses[3] = response(envelope("completed", mutation));
    await run(responses, async ({ client }) => {
      await client.initialize(); await client.submit(query); assert.equal(client.getState().result, null);
      assert.equal(client.getState().errorCode, "invalid_response");
    });
  });
}

for (const code of ["analysis_outcome_unknown", "analysis_expired"]) {
  test(`failed Core ${code} does not retry/rollback`, async () => {
    const responses = initial(); responses[3] = response(envelope("failed", { error_code: code }));
    await run(responses, async ({ client, calls }) => {
      await client.initialize(); await client.submit(query); assert.equal(client.getState().status, "failed");
      assert.equal(client.getState().errorCode, code); assert.equal(calls.length, 4);
      assert.equal(client.getState().ticket, ticket);
    });
  });
}

test("unknown HTTP failure text never becomes visible error", async () => {
  await run([response({ error_code: "PRIVATE_URL_QUERY_SECRET" }, 403)], async ({ client }) => {
    await client.initialize(); assert.equal(client.getState().errorCode, "invalid_response");
  });
});
for (const code of ["session_refused", "csrf_refused"]) {
  test(`auth failure ${code} invalidates session and stale canonical final`, async () => {
    await run([...initial(), response({ error_code: code }, 401)], async ({ client }) => {
      await client.initialize(); await client.submit(query); await client.recover();
      assert.equal(client.getState().sessionRef, null); assert.equal(client.getState().ticket, null);
      assert.equal(client.getState().result, null); assert.equal(client.getState().errorCode, code);
    });
  });
}

test("network error after POST retains ticket; explicit recovery sends GET only, never repeats POST", async () => {
  await run([response(session()), response(envelope("issued"), 201), new Error("PRIVATE"),
    response(session({ last_ticket: ticket })), response(envelope())], async ({ client, calls }) => {
    await client.initialize(); await client.submit(query);
    assert.equal(client.getState().ticket, ticket); assert.equal(client.getState().errorCode, "network_error");
    assert.equal(calls.length, 3); await client.recover();
    assert.equal(client.getState().status, "completed"); assert.deepEqual(calls.slice(3).map((call) => call.method), ["GET", "GET"]);
    assert.equal(calls.filter((call) => call.url === "/api/analysis").length, 1);
  });
});

test("reload initializes last_ticket but only explicit recover polls result", async () => {
  await run([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope())],
    async ({ client, calls }) => {
      await client.initialize(); assert.equal(calls.length, 1); assert.equal(client.getState().result, null);
      assert.equal(client.getState().ticket, ticket); await client.recover(); assert.equal(client.getState().status, "completed");
      assert.ok(calls.every((call) => call.method === "GET"));
    });
});
test("foreign session on recovery discards content/ticket/context before result fetch", async () => {
  await run([...initial(), response(session({ session_ref: "session://web-live/" + "f".repeat(32), last_ticket: ticket }))],
    async ({ client, calls }) => {
      await client.initialize(); await client.submit(query); await client.recover();
      assert.equal(client.getState().errorCode, "foreign_session"); assert.equal(client.getState().sessionRef, null);
      assert.equal(client.getState().result, null); assert.equal(client.getState().ticket, null); assert.equal(calls.length, 5);
    });
});
test("expired session blocks all new network IO", async () => {
  let now = 0;
  await run([response(session({ expires_in_seconds: 1 }))], async ({ client, calls }) => {
    await client.initialize(); now = 1000; await client.submit(query);
    assert.equal(calls.length, 1); assert.equal(client.getState().sessionRef, null);
    assert.equal(client.getState().errorCode, "session_expired");
  }, { now: () => now });
});

for (const stage of ["session", "ticket", "analysis", "result"]) {
  for (const action of ["stop", "pagehide", "disconnect"]) {
    test(`${action} fences stale ${stage} completion and aborts browser signal`, async () => {
      const gate = deferred(), responses = initial(), index = { session: 0, ticket: 1, analysis: 2, result: 3 }[stage];
      const original = responses[index]; responses[index] = () => gate.promise;
      if (action === "disconnect" && stage !== "session") responses.splice(index + 1, 0, response({ status: "disconnected" }));
      await run(responses, async ({ client, calls }) => {
        let pending;
        if (stage === "session") pending = client.initialize();
        else { await client.initialize(); pending = client.submit(query); }
        await flush(); const last = calls.at(-1);
        if (action === "stop") client.stopWaiting();
        else if (action === "pagehide") client.pageHide();
        else await client.disconnect();
        assert.equal(last.signal.aborted, true); gate.resolve(original); await pending;
        assert.equal(client.getState().result, null);
        if (action !== "stop") assert.equal(client.getState().sessionRef, null);
        assert.equal(calls.filter((call) => call.url === "/api/analysis").length, index >= 2 ? 1 : 0);
      });
    });
  }
}

test("bounded wait timeout aborts pending native IO and retains recoverable ticket", async () => {
  const gate = deferred();
  await run([response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), () => gate.promise],
    async ({ client, calls }) => {
      await client.initialize(); const pending = client.submit(query);
      await new Promise((resolve) => setTimeout(resolve, 35));
      assert.equal(client.getState().errorCode, "wait_timeout"); assert.equal(client.getState().ticket, ticket);
      assert.equal(calls.at(-1).signal.aborted, true); gate.resolve(response(envelope())); await pending;
      assert.equal(client.getState().result, null);
    }, { waitTimeoutMs: 20 });
});
test("duplicate submit while waiting never allocates second ticket", async () => {
  const gate = deferred();
  await run([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ client, calls }) => {
    await client.initialize(); const pending = client.submit(query); await flush(); await client.submit(query);
    assert.equal(calls.length, 3); client.stopWaiting(); gate.resolve(response(envelope("running"), 202)); await pending;
  });
});
test("issued ticket recovery performs no analysis and does not pretend execution", async () => {
  await run([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope("issued"))],
    async ({ client, calls }) => {
      await client.initialize(); await client.recover(); assert.equal(client.getState().status, "stopped");
      assert.equal(client.getState().errorCode, "analysis_outcome_unknown"); assert.ok(calls.every((call) => call.method === "GET"));
    });
});

for (const source of [JSON.stringify(session()).replace('"authenticated":true', '"authenticated":true,"authenticated":true'),
  JSON.stringify(session()).replace('"authenticated":true', '"authenticated":true,"authenti\\u0063ated":true'),
  "\ufeff" + JSON.stringify(session()), JSON.stringify(session()).replace('"expires_in_seconds":900', '"expires_in_seconds":9e2'),
  JSON.stringify(session()) + " trailing", JSON.stringify(session()).slice(0, -1)]) {
  test(`strict JSON rejects malformed/ambiguous wire ${source.slice(-65)}`, async () => {
    await run([new Response(source, { headers: { "content-type": "application/json" } })], async ({ client }) => {
      await client.initialize(); assert.equal(client.getState().sessionRef, null);
      assert.equal(client.getState().errorCode, "invalid_response");
    });
  });
}
test("fatal UTF8 decode rejects malformed response before session adoption", async () => {
  await run([new Response(new Uint8Array([0xc3, 0x28]), { headers: { "content-type": "application/json" } })], async ({ client }) => {
    await client.initialize(); assert.equal(client.getState().sessionRef, null);
    assert.equal(client.getState().errorCode, "invalid_response");
  });
});
test("declared oversized wire rejects before body read", async () => {
  let reads = 0;
  await run([{ ok: true, status: 200, headers: new Headers({ "content-length": "2097153", "content-type": "application/json" }),
    body: { getReader() { reads++; assert.fail(); } } }], async ({ client }) => {
    await client.initialize(); assert.equal(reads, 0); assert.equal(client.getState().errorCode, "invalid_response");
  });
});
test("actual oversized stream stops and cancels bounded reader", async () => {
  let reads = 0, cancelled = 0;
  await run([{ ok: true, status: 200, headers: new Headers({ "content-type": "application/json" }), body: { getReader: () => ({
    async read() { reads++; return { done: false, value: new Uint8Array(1048576) }; },
    async cancel() { cancelled++; },
  }) } }], async ({ client }) => {
    await client.initialize(); assert.equal(reads, 3); assert.equal(cancelled, 1);
    assert.equal(client.getState().errorCode, "invalid_response");
  });
});

test("failed start is a terminal unknown canonical outcome, without polling or retry", async () => {
  await run([response(session()), response(envelope("issued"), 201),
    response(envelope("failed", { error_code: "analysis_outcome_unknown" }), 202)], async ({ client, calls }) => {
    await client.initialize(); await client.submit(query); assert.equal(client.getState().status, "failed");
    assert.equal(client.getState().errorCode, "analysis_outcome_unknown"); assert.equal(client.getState().ticket, ticket);
    assert.equal(calls.length, 3); assert.equal(client.getState().result, null);
  });
});
for (const type of [null, "text/html", "text/plain", "application/json; charset=latin1"]) {
  test(`content type ${type} fails before consuming body`, async () => {
    let reads = 0;
    await run([{ ok: true, status: 200, headers: { get: (name) => name === "content-type" ? type : null },
      body: { getReader() { reads++; assert.fail(); } } }], async ({ client }) => {
      await client.initialize(); assert.equal(client.getState().errorCode, "invalid_response"); assert.equal(reads, 0);
    });
  });
}
test("declared smaller response than actual stream fails exact byte count", async () => {
  const wire = JSON.stringify(session());
  await run([new Response(wire, { headers: { "content-type": "application/json", "content-length": "1" } })], async ({ client }) => {
    await client.initialize(); assert.equal(client.getState().errorCode, "invalid_response");
  });
});
test("maximum codepoint query and final retain exact whitespace and supplementary Unicode", async () => {
  const input = " " + "😀".repeat(3998) + "\t", output = "😀".repeat(131072);
  const responses = initial(); responses[3] = response(envelope("completed", { result: result({ query: input, response_text: output }) }));
  await run(responses, async ({ client, calls }) => {
    await client.initialize(); await client.submit(input); assert.equal(client.getState().result.query, input);
    assert.equal(client.getState().result.response_text, output); assert.equal(JSON.parse(calls[2].body).query, input);
  });
});
test("escaped surrogate pair worst-case canonical final fits bounded wire without normalization", async () => {
  const output = "😀".repeat(131072), value = envelope("completed", { result: result({ response_text: output }) });
  const wire = JSON.stringify(value).replaceAll("😀", "\\ud83d\\ude00");
  const responses = initial(); responses[3] = new Response(wire, { headers: { "content-type": "application/json" } });
  await run(responses, async ({ client }) => {
    await client.initialize(); await client.submit(query); assert.equal(client.getState().result.response_text, output);
  });
});
test("stop resolves browser operation even if injected transport ignores abort", async () => {
  const gate = deferred();
  await run([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ client }) => {
    await client.initialize(); const pending = client.submit(query); await flush(); client.stopWaiting();
    const state = await pending; assert.equal(state.errorCode, "wait_stopped"); assert.equal(state.ticket, ticket);
    gate.resolve(response(envelope("running"), 202)); await flush(); assert.equal(client.getState().result, null);
  });
});
test("timeout resolves browser operation even if injected transport ignores abort", async () => {
  const gate = deferred();
  await run([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ client }) => {
    await client.initialize(); const state = await client.submit(query);
    assert.equal(state.errorCode, "wait_timeout"); assert.equal(state.ticket, ticket);
    gate.resolve(response(envelope("running"), 202)); await flush(); assert.equal(client.getState().result, null);
  }, { waitTimeoutMs: 20 });
});
test("pagehide during result bytes aborts and rejects late valid decoded content", async () => {
  const gate = deferred(), bytes = new TextEncoder().encode(JSON.stringify(envelope()));
  let reads = 0, cancelled = 0;
  const responses = initial(); responses[3] = { ok: true, status: 200,
    headers: new Headers({ "content-type": "application/json" }), body: { getReader: () => ({
      async read() { if (++reads === 1) return gate.promise; return { done: true }; },
      async cancel() { cancelled++; },
    }) } };
  await run(responses, async ({ client }) => {
    await client.initialize(); const pending = client.submit(query); await flush(); assert.equal(reads, 1);
    client.pageHide(); await pending; gate.resolve({ done: false, value: bytes }); await flush();
    assert.equal(client.getState().result, null); assert.equal(client.getState().ticket, null); assert.equal(cancelled, 1);
  });
});
test("expiration during pending final refuses commit even with valid envelope", async () => {
  const gate = deferred(); let now = 0;
  const responses = initial(); responses[0] = response(session({ expires_in_seconds: 1 })); responses[3] = () => gate.promise;
  await run(responses, async ({ client }) => {
    await client.initialize(); const pending = client.submit(query); await flush(); now = 1000;
    gate.resolve(response(envelope())); await pending; assert.equal(client.getState().result, null);
    assert.equal(client.getState().ticket, null); assert.equal(client.getState().errorCode, "session_expired");
  }, { now: () => now });
});
test("malformed replacement session clears authenticated context and canonical final", async () => {
  await run([...initial(), response(session({ authenticated: "true" }))], async ({ client }) => {
    await client.initialize(); await client.submit(query); await client.recover();
    assert.equal(client.getState().sessionRef, null); assert.equal(client.getState().result, null);
    assert.equal(client.getState().ticket, null); assert.equal(client.getState().errorCode, "invalid_response");
  });
});
for (const code of ["session_refused", "csrf_refused"]) {
  test(`stale auth failure ${code} cannot clear a freshly adopted session`, async () => {
    const gate = deferred();
    await run([() => gate.promise, response(session())], async ({ client }) => {
      const old = client.initialize(); client.pageHide(); await client.initialize();
      gate.resolve(response({ error_code: code }, 401)); await old; await flush();
      assert.equal(client.getState().sessionRef, sessionRef); assert.equal(client.getState().errorCode, null);
    });
  });
}
