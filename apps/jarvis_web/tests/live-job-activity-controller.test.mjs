import test from "node:test";
import assert from "node:assert/strict";
import { createLiveController } from "../live-controller.mjs";

const sessionRef = "session://web-live/" + "a".repeat(32);
const csrf = "b".repeat(64);
const session = { schema_version: "jarvis-local-session-v1", authenticated: true,
  session_ref: sessionRef, csrf_token: csrf, expires_in_seconds: 900, last_ticket: null };
const response = (value, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { "Content-Type": "application/json; charset=utf-8" } });
const envelope = { schema_version: "jarvis-local-job-activity-v1", session_ref: sessionRef, activity: {} };

test("manual activity read carries private CSRF without issuing a conversation ticket", async () => {
  const calls = [], replies = [response(session), response(envelope)];
  const controller = createLiveController({ transport: async (path, init) => {
    calls.push({ path, init }); return replies.shift();
  } });
  try {
    await controller.initialize();
    assert.equal(calls.length, 1);
    const before = controller.getState(), abort = new AbortController();
    assert.deepEqual(await controller.readJobActivity({ signal: abort.signal }), envelope);
    assert.deepEqual(controller.getState(), before);
    assert.equal(calls[1].path, "/api/job-activity");
    assert.equal(calls[1].init.method, "GET");
    assert.equal(calls[1].init.headers["X-Jarvis-CSRF"], csrf);
    assert.equal(calls[1].init.headers["X-Jarvis-Client"], "local-web-v1");
    assert.equal(calls[1].init.credentials, "same-origin");
    assert.equal(calls[1].init.redirect, "error");
    assert.equal(calls[1].init.cache, "no-store");
    assert.equal(calls[1].init.signal, abort.signal);
    assert.equal(Object.hasOwn(calls[1].init, "body"), false);
  } finally { controller.pageHide(); }
});

test("unpaired activity read performs no network IO", async () => {
  const controller = createLiveController({ transport: () => assert.fail("unpaired network") });
  await assert.rejects(controller.readJobActivity(), /^Error: not_paired$/);
});

for (const code of ["job_activity_disabled", "job_activity_unavailable", "session_refused", "csrf_refused"]) {
  test(`activity failure ${code} is fixed and retires denied authentication only`, async () => {
    const replies = [response(session), response({ error_code: code }, code.endsWith("disabled") ? 409 : 503)];
    const controller = createLiveController({ transport: async () => replies.shift() });
    try {
      await controller.initialize();
      const before = controller.getState();
      await assert.rejects(controller.readJobActivity(), new RegExp(`^Error: ${code}$`));
      if (["session_refused", "csrf_refused"].includes(code)) {
        assert.equal(controller.getState().sessionRef, null);
        assert.equal(controller.getState().status, "disconnected");
      } else assert.deepEqual(controller.getState(), before);
    } finally { controller.pageHide(); }
  });
}

for (const bad of [
  { ...envelope, session_ref: "session://web-live/" + "c".repeat(32) },
  { ...envelope, authority: "execute" },
  { ...envelope, schema_version: "foreign" },
]) {
  test("activity response cannot change its bound envelope", async () => {
    const replies = [response(session), response(bad)];
    const controller = createLiveController({ transport: async () => replies.shift() });
    try {
      await controller.initialize();
      await assert.rejects(controller.readJobActivity(), /^Error: invalid_response$/);
      assert.equal(controller.getState().ticket, null);
    } finally { controller.pageHide(); }
  });
}

test("late activity response after pagehide cannot restore a retired session", async () => {
  let deliver;
  const pending = new Promise((resolve) => { deliver = resolve; });
  let reads = 0;
  const controller = createLiveController({ transport: async () => ++reads === 1 ? response(session) : pending });
  await controller.initialize();
  const reading = controller.readJobActivity();
  controller.pageHide(); deliver(response(envelope));
  await assert.rejects(reading, /^Error: not_paired$/);
  assert.equal(controller.getState().sessionRef, null);
});

test("activity wire response has a small independent byte budget", async () => {
  const replies = [response(session), response({ ...envelope, padding: "x".repeat(8192) })];
  const controller = createLiveController({ transport: async () => replies.shift() });
  try {
    await controller.initialize();
    await assert.rejects(controller.readJobActivity(), /^Error: invalid_response$/);
  } finally { controller.pageHide(); }
});

test("raw transport exceptions are not reflected by the activity method", async () => {
  let calls = 0;
  const controller = createLiveController({ transport: async () => {
    if (++calls === 1) return response(session);
    throw new Error("private database path or credentials");
  } });
  try {
    await controller.initialize();
    await assert.rejects(controller.readJobActivity(), /^Error: network_error$/);
  } finally { controller.pageHide(); }
});

test("same-session verification during activity does not retire valid authentication", async () => {
  let deliver;
  const pending = new Promise((resolve) => { deliver = resolve; });
  const controller = createLiveController({ transport: async (path) =>
    path === "/api/job-activity" ? pending : response(session) });
  try {
    await controller.initialize();
    const reading = controller.readJobActivity();
    await controller.initialize();
    const before = controller.getState();
    deliver(response(envelope));
    assert.deepEqual(await reading, envelope);
    assert.deepEqual(controller.getState(), before);
  } finally { controller.pageHide(); }
});

for (const late of [response({ error_code: "session_refused" }, 401),
  response({ error_code: "csrf_refused" }, 403), response(envelope)]) {
  test("a retired activity read cannot disconnect a subsequently adopted session", async () => {
    let deliver;
    const pending = new Promise((resolve) => { deliver = resolve; });
    let adopted = session;
    const controller = createLiveController({ transport: async (path) =>
      path === "/api/job-activity" ? pending : response(adopted) });
    try {
      await controller.initialize();
      const reading = controller.readJobActivity();
      controller.pageHide();
      adopted = { ...session, session_ref: "session://web-live/" + "c".repeat(32),
        csrf_token: "d".repeat(64) };
      await controller.initialize();
      const before = controller.getState();
      deliver(late);
      await assert.rejects(reading, /session_refused|csrf_refused|foreign_session/);
      assert.deepEqual(controller.getState(), before);
    } finally { controller.pageHide(); }
  });
}
