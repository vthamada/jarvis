import test from "node:test";
import assert from "node:assert/strict";
import { createLiveController } from "../live-controller.mjs";

const sessionRef = "session://web-live/" + "a".repeat(32), csrf = "b".repeat(64);
const session = { schema_version: "jarvis-local-session-v1", authenticated: true, session_ref: sessionRef,
  csrf_token: csrf, expires_in_seconds: 900, last_ticket: null };
const json = (value, status = 200) => new Response(JSON.stringify(value), { status,
  headers: { "content-type": "application/json; charset=utf-8" } });
const job = "voice-job-" + "c".repeat(32);
function setup(reply) {
  const calls = []; let first = true;
  const controller = createLiveController({ transport: async (path, init) => {
    calls.push({ path, init }); if (first) { first = false; return json(session); }
    return typeof reply === "function" ? reply(path, init) : reply;
  } });
  return { controller, calls };
}
test("voice reads carry same-origin private binding but do not create or alter a Core ticket", async () => {
  const s = setup(json({ config: "test seam" }));
  try {
    await s.controller.initialize(); const before = s.controller.getState();
    await s.controller.voiceRequest("/api/voice/config");
    assert.deepEqual(s.controller.getState(), before);
    assert.equal(s.calls[1].init.headers["X-Jarvis-CSRF"], csrf);
    assert.equal(s.calls[1].init.credentials, "same-origin");
    assert.equal(s.calls[1].init.redirect, "error");
  } finally { s.controller.pageHide(); }
});
test("raw capture is posted as WAV, never JSON/base64 or an external URL", async () => {
  const s = setup(json({ accepted: true }, 202));
  try {
    await s.controller.initialize(); const body = new ArrayBuffer(46);
    await s.controller.voiceRequest("/api/voice/transcriptions", { method: "POST", body,
      headers: { "Content-Type": "audio/wav", "X-Jarvis-Voice-Consent": "local-audio-v1" } });
    assert.equal(s.calls[1].init.body, body);
    assert.equal(s.calls[1].init.headers["Content-Type"], "audio/wav");
  } finally { s.controller.pageHide(); }
});
for (const [path, options] of [
  ["https://evil.invalid", {}], ["/api/voice/audio/../../file", { binary: true }],
  ["/api/voice/config", { method: "POST" }], ["/api/voice/config", { headers: { Authorization: "secret" } }],
  ["/api/voice/speech", { method: "POST", body: { ticket: "web-request-" + "d".repeat(32), consent: true, text: "unbound" } }],
  ["/api/voice/transcriptions", { method: "POST", body: new ArrayBuffer(6 * 1024 * 1024 + 1),
    headers: { "Content-Type": "audio/wav", "X-Jarvis-Voice-Consent": "local-audio-v1" } }],
]) test("invalid voice operation is rejected without network", async () => {
  const s = setup(() => assert.fail("invalid voice network"));
  try { await s.controller.initialize(); await assert.rejects(s.controller.voiceRequest(path, options), /voice_invalid/); }
  finally { s.controller.pageHide(); }
});
test("bounded authenticated audio stream returns owned bytes with exact MIME and length", async () => {
  const bytes = new Uint8Array(46); bytes[0] = 82;
  const s = setup(new Response(bytes, { headers: { "content-type": "audio/wav", "content-length": "46" } }));
  try {
    await s.controller.initialize();
    const result = await s.controller.voiceRequest("/api/voice/audio/" + job, { binary: true });
    assert.equal(result.status, 200); assert.equal(new Uint8Array(result.value)[0], 82);
  } finally { s.controller.pageHide(); }
});
for (const headers of [
  { "content-type": "application/octet-stream", "content-length": "46" },
  { "content-type": "audio/wav", "content-length": "33554433" },
  { "content-type": "audio/wav", "content-length": "47" },
  { "content-type": "audio/wav" },
]) test("audio wire mismatch or unbounded body is refused", async () => {
  const s = setup(new Response(new Uint8Array(46), { headers }));
  try { await s.controller.initialize(); await assert.rejects(
    s.controller.voiceRequest("/api/voice/audio/" + job, { binary: true }), /invalid_response/); }
  finally { s.controller.pageHide(); }
});
test("voice cancellation never retires the otherwise valid Core session", async () => {
  const abort = new AbortController();
  const s = setup(() => { abort.abort(); return json({}); });
  try {
    await s.controller.initialize();
    await assert.rejects(s.controller.voiceRequest("/api/voice/config", { signal: abort.signal }), /voice_cancelled/);
    assert.equal(s.controller.getState().sessionRef, sessionRef);
  } finally { s.controller.pageHide(); }
});
