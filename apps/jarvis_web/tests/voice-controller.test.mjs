import test from "node:test";
import assert from "node:assert/strict";
import { createController } from "../controller.mjs";
import { createVoiceController, handleVoicePageHide } from "../voice-controller.mjs";

function rig() {
  let now = 0;
  const chatTimers = [];
  const voiceTimers = [];
  const chat = createController({ schedule(fn) { chatTimers.push(fn); return chatTimers.length; }, unschedule() {} });
  const voice = createVoiceController({ conversation: chat, clock: () => now,
    schedule(fn) { voiceTimers.push(fn); return voiceTimers.length; }, unschedule() {} });
  const review = () => { voice.setConsent(true); voice.startCapture(); voiceTimers.at(-1)(); };
  const confirmation = () => { const state = voice.getSnapshot(); return { generation: state.generation,
    revision: state.revision, text: state.transcript, principalId: state.principalId, sessionId: state.sessionId }; };
  return { voice, chat, chatTimers, voiceTimers, review, confirmation, time(value) { now = value; } };
}

test("reviewed voice fixture completes through existing conversation with text-only simulated playback", () => {
  const { voice, chat, review, confirmation, chatTimers, voiceTimers } = rig();
  assert.equal(voice.startCapture(), false);
  assert.equal(voice.play(), false);
  review(); assert.equal(chat.getSnapshot().messages.length, 2);
  assert.equal(voice.getSnapshot().status, "review");
  const text = "  Pedido revisado\n com espaços exatos  ";
  voice.revise(text); assert.equal(voice.confirm(confirmation()), true);
  assert.equal(chat.getSnapshot().messages.at(-1).text, text);
  assert.equal(voice.confirm(confirmation()), false);
  chatTimers.at(-1)();
  assert.equal(voice.getSnapshot().status, "completed");
  assert.match(voice.getSnapshot().finalText, /Resposta simulada/);
  assert.equal(voice.play(), true); assert.equal(voice.getSnapshot().status, "playing");
  voiceTimers.at(-1)(); assert.equal(voice.getSnapshot().status, "completed");
  assert.equal(voice.getSnapshot().authority, "none");
  assert.equal(voice.getSnapshot().evidenceMode, "synthetic_fixture");
  assert.ok(voice.getSnapshot().events.every((event) => !JSON.stringify(event).includes(text)));
});

test("confirmation binds exact review, revision, generation, principal and session", () => {
  const { voice, chat, review, confirmation } = rig(); review();
  for (const patch of [{ text: "Other" }, { revision: 0 }, { generation: -1 },
    { principalId: "other" }, { sessionId: "other" }]) {
    assert.equal(voice.confirm({ ...confirmation(), ...patch }), false);
    assert.equal(chat.getSnapshot().messages.length, 2);
  }
  const previous = confirmation(); voice.revise(previous.text);
  assert.equal(voice.confirm(previous), false);
  assert.equal(voice.confirm(), false);
  assert.equal(voice.confirm(confirmation()), true);
});

for (const phase of ["capture", "review", "sending", "playing"]) {
  test(`revoking consent during ${phase} invalidates callbacks and erases voice content`, () => {
    const { voice, chat, voiceTimers, chatTimers, review, confirmation } = rig();
    if (phase === "capture") { voice.setConsent(true); voice.startCapture(); }
    else review();
    if (["sending", "playing"].includes(phase)) voice.confirm(confirmation());
    if (phase === "playing") { chatTimers.at(-1)(); voice.play(); }
    voice.setConsent(false);
    for (const callback of [...voiceTimers, ...chatTimers]) callback();
    const state = voice.getSnapshot();
    assert.equal(state.consent, false); assert.equal(state.status, "cancelled");
    assert.equal(state.transcript, ""); assert.equal(state.finalText, "");
    assert.equal(voice.startCapture(), false); assert.equal(voice.play(), false);
    // Confirmed text was already appended to the in-memory fixture conversation;
    // revocation discards voice state, not history belonging to another surface.
    assert.equal(chat.getSnapshot().messages.length, ["sending", "playing"].includes(phase) ?
      (phase === "playing" ? 4 : 3) : 2);
  });
}

for (const scenario of ["error", "incomplete", "empty"]) {
  test(`${scenario} transcription cannot submit; ${scenario} final cannot play`, () => {
    const first = rig(); first.voice.setScenario(scenario); first.review();
    assert.equal(first.voice.getSnapshot().status, scenario);
    assert.equal(first.voice.confirm(first.confirmation()), false);
    assert.equal(first.chat.getSnapshot().messages.length, 2);
    const second = rig(); second.chat.setScenario(scenario); second.review();
    second.voice.confirm(second.confirmation()); second.chatTimers.at(-1)();
    assert.equal(second.voice.getSnapshot().status, scenario);
    assert.equal(second.voice.getSnapshot().finalText, "");
    assert.equal(second.voice.play(), false);
  });
}

test("interruption preserves final text but no stale playback can finish", () => {
  const { voice, review, confirmation, chatTimers, voiceTimers } = rig();
  review(); voice.confirm(confirmation()); chatTimers.at(-1)(); voice.play();
  const stale = voiceTimers.at(-1); const final = voice.getSnapshot().finalText;
  assert.equal(voice.interruptPlayback(), true);
  stale(); assert.equal(voice.getSnapshot().finalText, final);
  assert.match(voice.getSnapshot().notice, /interrompida/);
  assert.equal(voice.interruptPlayback(), false);
});

test("reset and BFCache require fresh consent, invalidate review and retain subscriptions", () => {
  const { voice, review, confirmation, voiceTimers } = rig();
  let calls = 0; voice.subscribe(() => { calls += 1; });
  review(); const old = confirmation(); const stale = voiceTimers[0];
  handleVoicePageHide(voice, { persisted: true }); stale();
  assert.equal(voice.getSnapshot().status, "idle");
  assert.equal(voice.getSnapshot().consent, false); assert.equal(voice.confirm(old), false);
  const count = calls; review(); assert.ok(calls > count);
  handleVoicePageHide(voice, { persisted: false });
  for (const callback of voiceTimers) callback();
  assert.equal(voice.reset(), false); assert.equal(voice.startCapture(), false);
  assert.equal(voice.setConsent(true), false); assert.equal(voice.revise("x"), false);
  assert.equal(voice.setScenario("completed"), false); assert.equal(voice.play(), false);
  assert.equal(voice.cancel(), false);
  let postDispose = 0; voice.subscribe(() => { postDispose += 1; }); assert.equal(postDispose, 0);
});

test("conversation reset invalidates even an already completed voice final", () => {
  const { voice, chat, review, confirmation, chatTimers } = rig();
  review(); voice.confirm(confirmation()); chatTimers.at(-1)(); chat.reset();
  assert.equal(voice.getSnapshot().finalText, ""); assert.equal(voice.getSnapshot().consent, false);
  assert.equal(voice.play(), false);
});

test("expired capture, review, response and playback never yield voice success", () => {
  for (const stage of ["capture", "review", "sending", "playing"]) {
    const value = rig(); const { voice, voiceTimers, chatTimers, review, confirmation, time } = value;
    if (stage === "capture") { voice.setConsent(true); voice.startCapture(); }
    else review();
    if (["sending", "playing"].includes(stage)) voice.confirm(confirmation());
    if (stage === "playing") { chatTimers.at(-1)(); voice.play(); }
    time(30001);
    if (stage === "review") assert.equal(voice.confirm(confirmation()), false);
    else if (stage === "sending") chatTimers.at(-1)();
    else voiceTimers.at(-1)();
    assert.equal(voice.getSnapshot().finalText, ""); assert.equal(voice.play(), false);
  }
});

test("busy conversation rejects capture and confirmation without clearing valid review", () => {
  const { voice, chat, review, confirmation } = rig(); review();
  chat.submit("Existing unrelated text");
  assert.equal(voice.startCapture(), false); assert.equal(voice.confirm(confirmation()), false);
  assert.equal(voice.getSnapshot().status, "review");
  assert.equal(chat.getSnapshot().messages.at(-1).text, "Existing unrelated text");
});

test("text remains data, no invalid text or content leaks into event metadata", () => {
  const { voice, chat, review, confirmation } = rig(); review();
  for (const value of ["", "   ", "\u0000secret", "\ud800", "x".repeat(4001)]) {
    voice.revise(value); assert.equal(voice.confirm(confirmation()), false);
  }
  const payload = '<img src=x onerror="alert(1)">'; voice.revise(payload);
  assert.equal(voice.confirm(confirmation()), true);
  assert.equal(chat.getSnapshot().messages.at(-1).text, payload);
  assert.ok(voice.getSnapshot().events.every((entry) => !JSON.stringify(entry).includes("img")));
  const value = voice.getSnapshot(); value.events.length = 0; value.consent = false;
  assert.equal(voice.getSnapshot().consent, true); assert.ok(voice.getSnapshot().events.length > 0);
});

test("divergent identity fails closed during capture and before confirmation", () => {
  for (const stage of ["capture", "review"]) {
    const value = rig(); const original = value.chat.getSnapshot.bind(value.chat);
    if (stage === "capture") { value.voice.setConsent(true); value.voice.startCapture(); }
    else value.review();
    value.chat.getSnapshot = () => ({ ...original(), sessionId: "different" });
    if (stage === "capture") value.voiceTimers.at(-1)();
    else assert.equal(value.voice.confirm(value.confirmation()), false);
    assert.equal(original().messages.length, 2); assert.equal(value.voice.play(), false);
  }
});

test("fixture-only initialization, strict consent/scenario, bounded event history", () => {
  assert.throws(() => createVoiceController());
  assert.throws(() => createVoiceController({ conversation: { getSnapshot: () => ({ mode: "live" }),
    subscribe() {}, submit() {} } }));
  const { voice } = rig();
  assert.equal(voice.setConsent("yes"), false); assert.equal(voice.setScenario("live"), false);
  for (let index = 0; index < 100; index += 1) voice.setConsent(true);
  assert.equal(voice.getSnapshot().events.length, 64);
});
