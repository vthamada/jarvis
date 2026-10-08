import test from "node:test";
import assert from "node:assert/strict";
import { createLiveController } from "../live-controller.mjs";

const ticket = "web-request-" + "a".repeat(32), otherTicket = "web-request-" + "b".repeat(32);
const sessionRef = "session://web-live/" + "c".repeat(32), csrf = "e".repeat(64);
const query = "Compare documentation and observability pilot reports.";
const v1 = "jarvis-local-analysis-v1", v2 = "jarvis-local-analysis-v2";
const session = (changes = {}) => ({ schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: csrf, expires_in_seconds: 900, last_ticket: null, ...changes });
const final = (changes = {}) => ({ query, response_text: "Sovereign final\r\n<script>literal</script> 😀 ",
  intent: "analysis", governance_decision: "allow", memory_record_ref: "mem-record-0123abcd",
  timestamp: "2026-10-06T12:00:00Z", evidence_mode: "core_local", generative_status: "accepted",
  authority: "none", generative_error_code: null, generative_evidence_mode: "injected_transport",
  generative_analysis_characters: 4000, ...changes });
const envelope = (status = "completed", changes = {}) => ({ schema_version: v2, status, ticket,
  error_code: status === "failed" ? "analysis_outcome_unknown" : null,
  result: status === "completed" ? final() : null, ...changes });
const response = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const rawResponse = (value) => new Response(value, { headers: { "content-type": "application/json" } });
const flow = () => [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), response(envelope())];
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { promise, resolve }; };
const flush = () => new Promise((yes) => setImmediate(yes));
async function rig(responses, callback, options = {}) {
  const calls = [], states = [];
  const client = createLiveController({ waitTimeoutMs: 1000, pollIntervalMs: 0, ...options,
    onState: (state) => states.push(state), transport: async (url, init) => {
      calls.push({ url, ...init }); const next = responses.shift();
      assert.ok(next, `unexpected request ${url}`); if (typeof next === "function") return next(url, init);
      if (next instanceof Error) throw next; return next;
    } });
  try { await callback({ client, calls, states }); } finally { client.pageHide(); }
}
const send = (client, value = query) => client.submitGenerative(value, { consent: true });

for (const mode of ["live", "injected_transport"]) {
  test(`explicit generative ${mode} preserves exact final and request-only consent`, async () => {
    const responses = flow(); responses[3] = response(envelope("completed", { result: final({ generative_evidence_mode: mode }) }));
    await rig(responses, async ({ client, calls }) => {
      await client.initialize(); const state = await send(client);
      assert.equal(state.status, "completed"); assert.deepEqual(state.result, final({ generative_evidence_mode: mode }));
      assert.deepEqual(calls.map((call) => call.url), ["/api/session", "/api/generative-tickets", "/api/generative-analysis", "/api/results/" + ticket]);
      assert.deepEqual(JSON.parse(calls[1].body), { consent: true });
      assert.deepEqual(JSON.parse(calls[2].body), { ticket, query, consent: true });
      for (const call of calls.slice(1)) {
        assert.equal(call.headers["X-Jarvis-CSRF"], csrf); assert.equal(call.credentials, "same-origin");
        assert.equal(call.mode, "same-origin"); assert.equal(call.cache, "no-store"); assert.equal(call.redirect, "error");
      }
      assert.equal(state.consent, undefined); assert.equal(state.csrf_token, undefined);
      assert.ok(Object.isFrozen(state.result));
    });
  });
}
for (const options of [undefined, {}, null, false, true, { consent: false }, { consent: 1 },
  { consent: "true" }, { consent: [true] }, { consent: true, model: "hidden" }, [true]]) {
  test(`consent strict and no request when ${JSON.stringify(options)}`, async () => {
    await rig([response(session())], async ({ client, calls }) => {
      await client.initialize(); const state = await client.submitGenerative(query, options);
      assert.equal(state.errorCode, "consent_required"); assert.equal(calls.length, 1); assert.equal(state.result, null);
    });
  });
}
for (const value of ["", " ", "a".repeat(4001), "x\u0000y", "x\u200by", "\ud800", "x\u2028y", null, 42]) {
  test(`generative query validation before ticket ${String(value).slice(0, 30)}`, async () => {
    await rig([response(session())], async ({ client, calls }) => {
      await client.initialize(); assert.equal((await send(client, value)).errorCode, "invalid_query"); assert.equal(calls.length, 1);
    });
  });
}
test("unpaired consent does not grant authentication or start Core", async () => {
  await rig([], async ({ client, calls }) => { assert.equal((await send(client)).errorCode, "not_paired"); assert.equal(calls.length, 0); });
});
test("unavailable host is terminal, never falls back to native or retries", async () => {
  await rig([response(session()), response({ error_code: "generative_unavailable" }, 409)], async ({ client, calls }) => {
    await client.initialize(); const state = await send(client); assert.equal(state.errorCode, "generative_unavailable");
    assert.equal(state.ticket, null); assert.equal(calls.length, 2);
  });
});
test("known-sensitive query travels only as query, never model/account/credentials fields", async () => {
  const sensitive = "api_key=not-a-real-key";
  const responses = flow(); responses[3] = response(envelope("completed", { result: final({ query: sensitive,
    generative_status: "rejected", generative_error_code: "input_sensitive", generative_evidence_mode: null,
    generative_analysis_characters: 0 }) }));
  await rig(responses, async ({ client, calls }) => {
    await client.initialize(); const state = await send(client, sensitive);
    assert.equal(state.result.generative_status, "rejected");
    assert.deepEqual(JSON.parse(calls[2].body), { ticket, query: sensitive, consent: true });
  });
});
for (const stage of [1, 2, 3]) {
  for (const schema of [v1, "unknown", [v2], null]) {
    test(`generative version binding refuses stage ${stage} ${JSON.stringify(schema)}`, async () => {
      const responses = flow(); responses[stage] = response(envelope(["", "issued", "running", "completed"][stage], { schema_version: schema }), [200, 201, 202, 200][stage]);
      await rig(responses, async ({ client, calls }) => {
        await client.initialize(); const state = await send(client); assert.equal(state.errorCode, "invalid_response");
        assert.equal(state.result, null); assert.equal(calls.length, stage + 1);
      });
    });
  }
}
test("native path never accepts a v2 ticket", async () => {
  await rig([response(session()), response(envelope("issued"), 201)], async ({ client, calls }) => {
    await client.initialize(); assert.equal((await client.submit(query)).errorCode, "invalid_response");
    assert.equal(calls[1].url, "/api/tickets"); assert.equal(calls.length, 2);
  });
});
const mutations = [
  { generative_status: "disabled" }, { generative_status: "ACCEPTED" }, { generative_status: ["accepted"] },
  { generative_evidence_mode: "fixture" }, { generative_evidence_mode: null }, { generative_evidence_mode: ["live"] },
  { generative_analysis_characters: 0 }, { generative_analysis_characters: 4001 }, { generative_analysis_characters: -1 },
  { generative_analysis_characters: 1.5 }, { generative_analysis_characters: "1" }, { generative_analysis_characters: true },
  { generative_error_code: "inference_failed" }, { generative_error_code: [null] },
  { governance_decision: "block" }, { governance_decision: "defer_for_validation" }, { authority: "execute" },
  { query: query + "x" }, { memory_record_ref: ["mem-record-0123abcd"] }, { evidence_mode: "live" },
  { response_text: "\u0000" }, { model: "secret-host-model" }, { csrf_token: csrf }, { consent: true },
  { generative_status: "rejected", generative_analysis_characters: 0, generative_evidence_mode: null, generative_error_code: null },
  { generative_status: "rejected", generative_analysis_characters: 0, generative_evidence_mode: null, generative_error_code: "private-secret" },
  { generative_status: "rejected", generative_analysis_characters: 0, generative_evidence_mode: null, generative_error_code: ["input_sensitive"] },
  { generative_status: "withheld", generative_analysis_characters: 0, generative_evidence_mode: null, generative_error_code: "input_sensitive" },
  { generative_status: "rejected", generative_error_code: "input_sensitive" },
  { generative_status: "rejected", generative_analysis_characters: 0, generative_error_code: "input_sensitive" },
];
for (const [index, mutation] of mutations.entries()) {
  test(`invalid v2 final cross-field/type/extras ${index}`, async () => {
    const responses = flow(); responses[3] = response(envelope("completed", { result: final(mutation) }));
    await rig(responses, async ({ client }) => {
      await client.initialize(); const state = await send(client); assert.equal(state.errorCode, "invalid_response"); assert.equal(state.result, null);
    });
  });
}
const errors = ["invalid_context", "invalid_composition", "input_sensitive", "cancelled", "invalid_clock",
  "timed_out", "invalid_result", "binding_mismatch", "inference_failed", "output_limit", "invalid_candidate",
  "invalid_citation", "candidate_limit", "output_sensitive", "render_limit", "context_changed", "result_changed",
  "inference_unavailable", "scope_denied", "reviewed_source_invalid"];
for (const code of errors) {
  test(`rejected ${code} preserves exact native final and no extra POST`, async () => {
    const value = final({ generative_status: "rejected", generative_error_code: code,
      generative_evidence_mode: null, generative_analysis_characters: 0 });
    const responses = flow(); responses[3] = response(envelope("completed", { result: value }));
    await rig(responses, async ({ client, calls }) => {
      await client.initialize(); assert.deepEqual((await send(client)).result, value); assert.equal(calls.length, 4);
    });
  });
}
for (const code of ["scope_denied", "reviewed_source_invalid"]) {
  for (const decision of ["allow", "block", "defer_for_validation"]) {
    test(`withheld ${code} ${decision} is not inference success`, async () => {
      const value = final({ governance_decision: decision, generative_status: "withheld", generative_error_code: code,
        generative_evidence_mode: null, generative_analysis_characters: 0 });
      const responses = flow(); responses[3] = response(envelope("completed", { result: value }));
      await rig(responses, async ({ client }) => { await client.initialize(); assert.deepEqual((await send(client)).result, value); });
    });
  }
}
for (const field of ["generative_error_code", "generative_evidence_mode", "generative_analysis_characters"]) {
  test(`missing v2 result field ${field} rejected`, async () => {
    const value = final(); delete value[field]; const responses = flow(); responses[3] = response(envelope("completed", { result: value }));
    await rig(responses, async ({ client }) => { await client.initialize(); assert.equal((await send(client)).errorCode, "invalid_response"); });
  });
  test(`escaped duplicate v2 field ${field} rejected before adoption`, async () => {
    const source = JSON.stringify(envelope()).replace('"result":{', '"result":{"' + field.replace("g", "\\u0067") + '":null,');
    const responses = flow(); responses[3] = rawResponse(source);
    await rig(responses, async ({ client }) => { await client.initialize(); assert.equal((await send(client)).errorCode, "invalid_response"); });
  });
}
for (const code of ["analysis_outcome_unknown", "analysis_expired"]) {
  test(`failed v2 ${code} start terminal, no GET/retry`, async () => {
    await rig([response(session()), response(envelope("issued"), 201), response(envelope("failed", { error_code: code }), 202)], async ({ client, calls }) => {
      await client.initialize(); assert.equal((await send(client)).status, "failed"); assert.equal(calls.length, 3);
    });
  });
}
test("uncertain generative start recovers same v2 ticket using GET only", async () => {
  await rig([response(session()), response(envelope("issued"), 201), new Error("private-transport"),
    response(session({ last_ticket: ticket })), response(envelope())], async ({ client, calls }) => {
    await client.initialize(); assert.equal((await send(client)).status, "stopped");
    assert.equal((await client.recover()).status, "completed"); assert.ok(calls.slice(3).every((call) => call.method === "GET"));
  });
});
for (const stage of ["issued", "running", "completed", "failed"]) {
  test(`reload adopts validated v2 ${stage} via explicit GET only`, async () => {
    const responses = [response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })), response(envelope(stage))];
    if (stage === "running") responses.push(response(envelope()));
    await rig(responses, async ({ client, calls }) => {
      await client.initialize(); assert.equal(calls.length, 1); const state = await client.recover();
      assert.equal(state.status, { issued: "stopped", running: "completed", completed: "completed", failed: "failed" }[stage]);
      assert.ok(calls.every((call) => call.method === "GET"));
    });
  });
}
test("reload adoption refuses ticket switch before accepting version", async () => {
  await rig([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })),
    response(envelope("completed", { ticket: otherTicket }))], async ({ client }) => {
    await client.initialize(); assert.equal((await client.recover()).errorCode, "invalid_response");
  });
});
test("reload first running v2 fences later switch to v1", async () => {
  await rig([response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })),
    response(envelope("running")), response(envelope("failed", { schema_version: v1 }))], async ({ client }) => {
    await client.initialize(); assert.equal((await client.recover()).errorCode, "invalid_response");
  });
});
test("explicit refresh same ticket cannot reset version binding", async () => {
  await rig([...flow(), response(session({ last_ticket: ticket })), response(session({ last_ticket: ticket })),
    response(envelope("failed", { schema_version: v1 }))], async ({ client }) => {
    await client.initialize(); await send(client); await client.initialize();
    assert.equal((await client.recover()).errorCode, "invalid_response");
  });
});
for (const action of ["stop", "pagehide", "disconnect", "timeout"]) {
  test(`generative ${action} abort-ignoring IO resolves and fences stale v2`, async () => {
    const gate = deferred(); const responses = [response(session()), response(envelope("issued"), 201), response(envelope("running"), 202), () => gate.promise];
    if (action === "disconnect") responses.push(response({ status: "disconnected" }));
    await rig(responses, async ({ client, calls }) => {
      await client.initialize(); const pending = send(client); await flush(); const signal = calls.at(-1).signal;
      if (action === "stop") client.stopWaiting(); else if (action === "pagehide") client.pageHide();
      else if (action === "disconnect") await client.disconnect();
      await pending; assert.equal(signal.aborted, true); assert.equal(client.getState().result, null);
      gate.resolve(response(envelope())); await flush(); assert.equal(client.getState().result, null);
      if (["stop", "timeout"].includes(action)) assert.equal(client.getState().ticket, ticket);
      else assert.equal(client.getState().ticket, null);
    }, { waitTimeoutMs: action === "timeout" ? 35 : 1000 });
  });
}
for (const code of ["session_refused", "csrf_refused"]) {
  test(`late generative ${code} cannot invalidate a fresh session`, async () => {
    const gate = deferred();
    await rig([response(session()), response(envelope("issued"), 201), () => gate.promise, response(session())], async ({ client }) => {
      await client.initialize(); const pending = send(client); await flush(); client.pageHide(); await pending;
      await client.initialize(); gate.resolve(response({ error_code: code }, 401)); await flush();
      assert.equal(client.getState().sessionRef, sessionRef); assert.equal(client.getState().status, "ready");
    });
  });
}
test("generative duplicate submission while waiting issues no second ticket", async () => {
  const gate = deferred();
  await rig([response(session()), response(envelope("issued"), 201), () => gate.promise], async ({ client, calls }) => {
    await client.initialize(); const pending = send(client); await flush(); await send(client); await client.submit(query);
    assert.equal(calls.length, 3); client.stopWaiting(); await pending; gate.resolve(response(envelope("running"), 202));
  });
});
