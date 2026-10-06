import test from "node:test";
import assert from "node:assert/strict";
import { createController, handlePageHide } from "../controller.mjs";
import { createFixture } from "../fixtures.mjs";

function rig(fixture = createFixture()) {
  let callback;
  let cancelled = false;
  const controller = createController({ fixture,
    schedule(fn) { callback = fn; cancelled = false; return 1; },
    unschedule() { cancelled = true; },
  });
  return { controller, run() { callback(); }, cancelled: () => cancelled };
}

test("explicit fixture identity/version only", () => {
  for (const patch of [{ mode: "live" }, { version: "v0" }, { principalId: "" }, { sessionId: "" }]) {
    assert.throws(() => createController({ fixture: { ...createFixture(), ...patch } }));
  }
});
test("submits local demonstration without claiming real success", () => {
  const { controller, run } = rig();
  assert.equal(controller.submit("Prepare a report"), true);
  assert.equal(controller.getSnapshot().requestStatus, "loading");
  assert.equal(controller.submit("Duplicate"), false);
  run();
  const state = controller.getSnapshot();
  assert.equal(state.requestStatus, "completed");
  assert.equal(state.mode, "fixture");
  assert.match(state.messages.at(-1).text, /Resposta simulada/);
  assert.match(state.notice, /nenhum resultado real/);
  assert.equal(state.approvals[0].status, "Somente inspeção");
});
test("cancelled stream cannot later become completed", () => {
  const { controller, run, cancelled } = rig();
  controller.submit("Report");
  assert.equal(controller.cancel(), true);
  assert.equal(cancelled(), true);
  run(); // A race or a stale callback must not deliver content.
  assert.equal(controller.getSnapshot().requestStatus, "cancelled");
  assert.equal(controller.getSnapshot().messages.length, 3);
  assert.equal(controller.cancel(), false);
});
test("reset invalidates pending generation and restores context", () => {
  const { controller, run } = rig();
  controller.submit("Report"); controller.reset(); run();
  assert.equal(controller.getSnapshot().messages.length, 2);
  assert.equal(controller.getSnapshot().requestStatus, "idle");
  assert.equal(controller.getSnapshot().scenario, "completed");
});
for (const scenario of ["error", "incomplete", "empty"]) {
  test(`${scenario} is distinguishable from confirmed output`, () => {
    const { controller, run } = rig();
    controller.setScenario(scenario); controller.submit("Report"); run();
    const state = controller.getSnapshot();
    assert.equal(state.requestStatus, scenario);
    assert.equal(state.messages.length, scenario === "incomplete" ? 4 : 3);
    if (scenario === "incomplete") assert.equal(state.messages.at(-1).status, "incomplete");
    assert.notEqual(state.notice, "Demonstração concluída; nenhum resultado real foi produzido.");
  });
}
test("identity/session confusion fail closed without appending request", () => {
  const { controller } = rig();
  for (const identity of [{ principalId: "other" }, { sessionId: "other" }]) {
    assert.equal(controller.submit("Private", identity), false);
    assert.equal(controller.getSnapshot().messages.length, 2);
  }
});
test("rejects invalid input/scenario; pending scenario cannot change", () => {
  const { controller } = rig();
  for (const value of ["", "  ", null, "x".repeat(4001)]) assert.equal(controller.submit(value), false);
  assert.throws(() => controller.setScenario("live"));
  controller.submit("OK"); assert.equal(controller.setScenario("error"), false);
});
test("snapshots and subscriptions cannot mutate controller state", () => {
  const { controller } = rig();
  let calls = 0;
  const unsubscribe = controller.subscribe((state) => { calls += 1; state.mode = "live"; });
  controller.getSnapshot().messages.length = 0;
  assert.equal(controller.getSnapshot().mode, "fixture");
  assert.equal(controller.getSnapshot().messages.length, 2);
  unsubscribe(); controller.reset(); assert.equal(calls, 1);
});
test("untrusted text remains data; dispose prevents stale delivery", () => {
  const { controller, run } = rig();
  const payload = '<img src=x onerror="alert(1)">';
  controller.submit(payload);
  assert.equal(controller.getSnapshot().messages.at(-1).text, payload);
  controller.dispose(); run();
  assert.equal(controller.getSnapshot().messages.length, 3);
});
test("disposed controller cannot schedule or mutate another request", () => {
  const { controller } = rig();
  controller.dispose();
  assert.equal(controller.submit("New request"), false);
  assert.equal(controller.cancel(), false);
  assert.equal(controller.reset(), false);
  assert.equal(controller.setScenario("error"), false);
  let calls = 0;
  controller.subscribe(() => { calls += 1; });
  assert.equal(calls, 0);
  assert.equal(controller.getSnapshot().requestStatus, "idle");
});
test("BFCache pagehide cancels pending turn but retains subscribers and usability", () => {
  const { controller, run } = rig();
  let calls = 0;
  controller.subscribe(() => { calls += 1; });
  controller.submit("Pending"); handlePageHide(controller, { persisted: true }); run();
  assert.equal(controller.getSnapshot().requestStatus, "cancelled");
  const previousCalls = calls;
  assert.equal(controller.submit("After return"), true);
  assert.equal(calls, previousCalls + 1);
  run(); assert.equal(controller.getSnapshot().requestStatus, "completed");
  handlePageHide(controller, { persisted: false });
  assert.equal(controller.submit("After unload"), false);
});
