import test from "node:test";
import assert from "node:assert/strict";
import { createJobActivityPanel } from "../live-job-activity.mjs";

const sessionRef = "session://web-live/" + "a".repeat(32);
const otherSession = "session://web-live/" + "b".repeat(32);
const clone = (value) => structuredClone(value);
const payload = () => ({ schema_version: "jarvis-local-job-activity-v1", session_ref: sessionRef, activity: {
  schema_version: "jarvis-job-activity-v1", read_only: true, authority: "none", operator_authenticated: false,
  scope_binding: "caller_supplied_not_authentication", source_mode: "quiescent_existing_local_sqlite",
  activity_scope: "explicit_selected_jobs_not_full_ledger", selected_job_count: 7,
  status_counts: { registered: 1, running: 1, succeeded: 1, failed: 1, needs_decision: 1, cancelled: 1, expired: 1 },
  evidence_counts: { fixture: 2, metadata_ledger: 5 }, attempts_recorded: 6,
  progress: { basis: "selected_ledger_states_not_execution_percentage", pending_count: 1, active_count: 1,
    awaiting_decision_count: 1, terminal_count: 4 },
} });
const deferred = () => { let resolve, reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject }; };
const flush = () => new Promise((resolve) => setImmediate(resolve));
class Element {
  constructor() { this.disabled = false; this.textContent = ""; this.events = new Map(); }
  set innerHTML(_value) { assert.fail("HTML sink used"); }
  addEventListener(name, fn) { this.events.set(name, fn); }
  removeEventListener(name, fn) { if (this.events.get(name) === fn) this.events.delete(name); }
  async click() { return this.events.get("click")?.({ preventDefault() {} }); }
}
function rig(read, options = {}) {
  const nodes = Object.fromEntries(["live-job-refresh", "live-job-status", "live-job-summary"].map((id) => [id, new Element()]));
  const calls = [];
  const panel = createJobActivityPanel({ document: { getElementById: (id) => nodes[id] },
    read: (args) => { calls.push(args); return read(args); }, ...options });
  const text = () => nodes["live-job-status"].textContent + " " + nodes["live-job-summary"].textContent;
  return { panel, nodes, calls, text };
}
test("panel is manual-only, paired-only and renders seven fixed states without authority claims", async () => {
  const r = rig(() => payload());
  try {
    assert.equal(r.calls.length, 0); assert.equal(r.nodes["live-job-refresh"].disabled, true);
    await r.nodes["live-job-refresh"].click(); assert.equal(r.calls.length, 0);
    r.panel.setSession(sessionRef); assert.equal(r.calls.length, 0);
    assert.equal(r.nodes["live-job-refresh"].disabled, false);
    await r.nodes["live-job-refresh"].click();
    assert.equal(r.calls.length, 1); assert.ok(r.calls[0].signal instanceof AbortSignal);
    assert.equal(r.panel.getState().status, "ready");
    for (const label of ["Registrados: 1", "Em andamento: 1", "Concluídos: 1", "Falharam: 1", "Aguardando decisão: 1", "Cancelados: 1", "Expirados: 1"]) assert.ok(r.text().includes(label), label);
    assert.match(r.text(), /7 jobs selecionados/); assert.match(r.text(), /não é percentual/);
    assert.match(r.text(), /não autentica/); assert.match(r.text(), /sem execução automática/i);
    assert.match(r.text(), /Fixture: 2/); assert.match(r.text(), /Metadados do ledger: 5/);
    assert.doesNotMatch(r.text(), /session:\/\/|%|<script/);
    assert.ok(Object.isFrozen(r.panel.getState()));
    await flush(); assert.equal(r.calls.length, 1);
  } finally { r.panel.dispose(); }
});

const invalid = [
  ["schema", (v) => { v.schema_version = "wrong"; }],
  ["session foreign", (v) => { v.session_ref = otherSession; }],
  ["session coercion", (v) => { v.session_ref = [sessionRef]; }],
  ["envelope extra", (v) => { v.secret = "<script>private</script>"; }],
  ["activity extra", (v) => { v.activity.jobs = ["private-job"]; }],
  ["activity schema", (v) => { v.activity.schema_version = "wrong"; }],
  ["boolean read", (v) => { v.activity.read_only = 1; }],
  ["authority", (v) => { v.activity.authority = "allow"; }],
  ["authenticated", (v) => { v.activity.operator_authenticated = true; }],
  ["scope", (v) => { v.activity.scope_binding = "authenticated"; }],
  ["source", (v) => { v.activity.source_mode = "live"; }],
  ["full ledger", (v) => { v.activity.activity_scope = "full_ledger"; }],
  ["empty selection", (v) => { v.activity.selected_job_count = 0; }],
  ["too many selected", (v) => { v.activity.selected_job_count = 33; }],
  ["count bool", (v) => { v.activity.selected_job_count = true; }],
  ["fraction", (v) => { v.activity.status_counts.running = 0.5; }],
  ["negative", (v) => { v.activity.status_counts.running = -1; }],
  ["unsafe", (v) => { v.activity.attempts_recorded = 2 ** 53; }],
  ["NaN", (v) => { v.activity.attempts_recorded = NaN; }],
  ["attempt limit", (v) => { v.activity.attempts_recorded = 71; }],
  ["running without attempt", (v) => { v.activity.attempts_recorded = 0; }],
  ["states mismatch", (v) => { v.activity.status_counts.registered = 2; }],
  ["extra state", (v) => { v.activity.status_counts.paused = 0; }],
  ["missing state", (v) => { delete v.activity.status_counts.expired; }],
  ["evidence mismatch", (v) => { v.activity.evidence_counts.fixture = 3; }],
  ["evidence extra", (v) => { v.activity.evidence_counts.live = 0; }],
  ["evidence coercion", (v) => { v.activity.evidence_counts.fixture = "2"; }],
  ["progress percentage", (v) => { v.activity.progress.percentage = 50; }],
  ["progress basis", (v) => { v.activity.progress.basis = "execution_percentage"; }],
  ...["pending_count", "active_count", "awaiting_decision_count", "terminal_count"].map((key) =>
    ["derived " + key, (v) => { v.activity.progress[key]++; }]),
  ["array activity", (v) => { v.activity = []; }],
  ["null counts", (v) => { v.activity.status_counts = null; }],
  ["prototype activity", (v) => { Object.setPrototypeOf(v.activity, { secret: true }); }],
  ["getter", (v) => { Object.defineProperty(v.activity, "authority", { enumerable: true, get() { throw new Error("PRIVATE"); } }); }],
  ["symbol", (v) => { v[Symbol("PRIVATE")] = true; }],
];
for (const [label, mutate] of invalid) test("strict refusal: " + label, async () => {
  const v = payload(); mutate(v); const r = rig(() => v);
  try {
    r.panel.setSession(sessionRef); await r.panel.refresh();
    assert.equal(r.panel.getState().status, "error"); assert.equal(r.panel.getState().errorCode, "invalid_response");
    assert.equal(r.nodes["live-job-summary"].textContent, "");
    assert.doesNotMatch(r.text(), /PRIVATE|private|<script|session:\/\//);
  } finally { r.panel.dispose(); }
});
for (const value of [null, false, [], "", sessionRef.toUpperCase(), sessionRef + "\n", {}, 1])
  test("invalid or missing session never invokes read: " + JSON.stringify(value), async () => {
    const r = rig(() => payload());
    try { r.panel.setSession(value); await r.panel.refresh(); assert.equal(r.calls.length, 0);
      assert.equal(r.nodes["live-job-refresh"].disabled, true); } finally { r.panel.dispose(); }
  });

test("disconnect aborts and fences a pending result, clears prior text, no automatic read on reconnect", async () => {
  const gate = deferred(); const r = rig(() => gate.promise);
  try {
    r.panel.setSession(sessionRef); const pending = r.panel.refresh(); await flush();
    assert.equal(r.nodes["live-job-refresh"].disabled, true);
    r.panel.setSession(null); assert.equal(r.calls[0].signal.aborted, true);
    await pending; gate.resolve(payload()); await flush();
    assert.equal(r.panel.getState().status, "disconnected"); assert.equal(r.nodes["live-job-summary"].textContent, "");
    r.panel.setSession(sessionRef); assert.equal(r.calls.length, 1);
  } finally { r.panel.dispose(); }
});
test("out-of-order reads cannot repaint a newer success", async () => {
  const a = deferred(), b = deferred(); let index = 0; const r = rig(() => [a, b][index++].promise);
  try {
    r.panel.setSession(sessionRef); const first = r.panel.refresh(); await flush();
    const second = r.panel.refresh(); await flush(); assert.equal(r.calls[0].signal.aborted, true);
    b.resolve(payload()); await second; const accepted = r.text();
    a.resolve({ secret: "PRIVATE" }); await first; await flush(); assert.equal(r.text(), accepted);
  } finally { r.panel.dispose(); }
});
test("session replacement aborts and fences old reads, even if returning correct new binding", async () => {
  const gate = deferred(); const r = rig(() => gate.promise);
  try {
    r.panel.setSession(sessionRef); const pending = r.panel.refresh(); await flush();
    r.panel.setSession(otherSession); await pending;
    const value = payload(); value.session_ref = otherSession; gate.resolve(value); await flush();
    assert.equal(r.panel.getState().status, "idle"); assert.equal(r.nodes["live-job-summary"].textContent, "");
    assert.equal(r.nodes["live-job-refresh"].disabled, false); assert.equal(r.calls.length, 1);
  } finally { r.panel.dispose(); }
});
test("timeout settles ignored cancellation and late completion cannot overwrite fixed failure", async () => {
  const gate = deferred(); const r = rig(() => gate.promise, { timeoutMs: 10 });
  try {
    r.panel.setSession(sessionRef); await r.panel.refresh();
    assert.equal(r.calls[0].signal.aborted, true); assert.equal(r.panel.getState().errorCode, "timeout");
    assert.equal(r.nodes["live-job-refresh"].disabled, false); const prior = r.text();
    gate.resolve(payload()); await flush(); assert.equal(r.text(), prior);
  } finally { r.panel.dispose(); }
});
for (const code of ["job_activity_unavailable", "job_activity_disabled", "disabled", "PRIVATE <script>"])
  test("fixed refusal without echoing source errors: " + code, async () => {
    const r = rig(() => { throw new Error(code); });
    try { r.panel.setSession(sessionRef); await r.panel.refresh();
      assert.equal(r.panel.getState().errorCode, code.includes("PRIVATE") ? "read_failed" : "unavailable");
      assert.doesNotMatch(r.text(), /PRIVATE|<script>|job_activity/); } finally { r.panel.dispose(); }
  });
test("dispose aborts, removes listener, prevents repaint and repeated calls", async () => {
  const gate = deferred(); const r = rig(() => gate.promise);
  r.panel.setSession(sessionRef); const pending = r.panel.refresh(); await flush(); r.panel.dispose();
  assert.equal(r.calls[0].signal.aborted, true); await pending;
  gate.resolve(payload()); await flush(); r.panel.setSession(sessionRef); await r.panel.refresh();
  await r.nodes["live-job-refresh"].click(); r.panel.dispose();
  assert.equal(r.calls.length, 1); assert.equal(r.panel.getState().status, "disposed");
  assert.equal(r.nodes["live-job-refresh"].events.size, 0); assert.equal(r.nodes["live-job-summary"].textContent, "");
});
test("same session notification preserves snapshot and does not trigger read", async () => {
  const r = rig(() => payload());
  try { r.panel.setSession(sessionRef); await r.panel.refresh(); const prior = r.text(); r.panel.setSession(sessionRef);
    assert.equal(r.text(), prior); assert.equal(r.calls.length, 1); } finally { r.panel.dispose(); }
});
test("boundary selection 32 and fully terminal metadata remain counts, not completion percentage", async () => {
  const v = clone(payload()); Object.keys(v.activity.status_counts).forEach((key) => { v.activity.status_counts[key] = 0; });
  v.activity.selected_job_count = 32; v.activity.status_counts.succeeded = 32;
  v.activity.evidence_counts = { fixture: 0, metadata_ledger: 32 }; v.activity.attempts_recorded = 320;
  v.activity.progress = { basis: "selected_ledger_states_not_execution_percentage", pending_count: 0, active_count: 0,
    awaiting_decision_count: 0, terminal_count: 32 };
  const r = rig(() => v);
  try { r.panel.setSession(sessionRef); await r.panel.refresh(); assert.equal(r.panel.getState().status, "ready");
    assert.match(r.text(), /Terminais: 32/); assert.doesNotMatch(r.text(), /%|todos os jobs/); } finally { r.panel.dispose(); }
});
test("a prior accepted summary is cleared on expiry or failed manual refresh", async () => {
  let fail = false; const r = rig(() => { if (fail) throw new Error("PRIVATE"); return payload(); });
  try {
    r.panel.setSession(sessionRef); await r.panel.refresh(); assert.notEqual(r.nodes["live-job-summary"].textContent, "");
    fail = true; await r.panel.refresh(); assert.equal(r.nodes["live-job-summary"].textContent, "");
    fail = false; await r.panel.refresh(); r.panel.setSession(null);
    assert.equal(r.panel.getState().status, "disconnected"); assert.equal(r.nodes["live-job-summary"].textContent, "");
  } finally { r.panel.dispose(); }
});
test("successful read clears its deadline without future abort or retry", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] }); const r = rig(() => payload(), { timeoutMs: 1000 });
  try {
    r.panel.setSession(sessionRef); await r.panel.refresh(); const prior = r.text();
    t.mock.timers.tick(5000); await flush(); assert.equal(r.text(), prior);
    assert.equal(r.calls[0].signal.aborted, false); assert.equal(r.calls.length, 1);
  } finally { r.panel.dispose(); t.mock.timers.reset(); }
});
test("reentrant data trap cannot paint after disconnect", async () => {
  const value = payload(); let r;
  value.activity = new Proxy(value.activity, { ownKeys(target) { r.panel.setSession(null); return Reflect.ownKeys(target); } });
  r = rig(() => value);
  try {
    r.panel.setSession(sessionRef); await r.panel.refresh();
    assert.equal(r.panel.getState().status, "disconnected"); assert.equal(r.nodes["live-job-summary"].textContent, "");
  } finally { r.panel.dispose(); }
});
test("late rejection after timeout remains handled without repaint", async () => {
  const gate = deferred(); const r = rig(() => gate.promise, { timeoutMs: 10 });
  try { r.panel.setSession(sessionRef); await r.panel.refresh(); const prior = r.text();
    gate.reject(new Error("PRIVATE")); await flush(); assert.equal(r.text(), prior); } finally { r.panel.dispose(); }
});
test("one selected registered job with no attempts is valid", async () => {
  const value = payload(), a = value.activity;
  a.selected_job_count = 1; Object.keys(a.status_counts).forEach((key) => { a.status_counts[key] = key === "registered" ? 1 : 0; });
  a.evidence_counts = { fixture: 0, metadata_ledger: 1 }; a.attempts_recorded = 0;
  a.progress = { basis: "selected_ledger_states_not_execution_percentage", pending_count: 1, active_count: 0,
    awaiting_decision_count: 0, terminal_count: 0 }; const r = rig(() => value);
  try { r.panel.setSession(sessionRef); await r.panel.refresh(); assert.equal(r.panel.getState().status, "ready");
    assert.match(r.text(), /1 jobs selecionados/); } finally { r.panel.dispose(); }
});
test("immediate disconnect before read microtask prevents even the injected callback", async () => {
  const r = rig(() => payload());
  try {
    r.panel.setSession(sessionRef); const pending = r.panel.refresh(); r.panel.setSession(null);
    await pending; assert.equal(r.calls.length, 0); assert.equal(r.panel.getState().status, "disconnected");
  } finally { r.panel.dispose(); }
});
test("invalid root payloads and hostile error getters have only fixed failures", async () => {
  for (const value of [null, [], 42, false, "<script>PRIVATE</script>"]) {
    const r = rig(() => value);
    try { r.panel.setSession(sessionRef); await r.panel.refresh(); assert.equal(r.panel.getState().errorCode, "invalid_response");
      assert.doesNotMatch(r.text(), /PRIVATE|<script>/); } finally { r.panel.dispose(); }
  }
  const r = rig(() => { throw { get message() { throw new Error("PRIVATE"); } }; });
  try { r.panel.setSession(sessionRef); await r.panel.refresh(); assert.equal(r.panel.getState().errorCode, "read_failed");
    assert.doesNotMatch(r.text(), /PRIVATE/); } finally { r.panel.dispose(); }
});
for (const timeoutMs of [0, -1, 1.2, NaN, Infinity, 60001, "10", null])
  test("invalid timeout fails before listeners or reads: " + timeoutMs, () => {
    assert.throws(() => rig(() => payload(), { timeoutMs }), /invalid_job_activity_options/);
  });
