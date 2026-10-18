import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createLiveVoiceControls } from "../live-voice-controls.mjs";

const html = readFileSync(new URL("../live-index.html", import.meta.url), "utf8");
class Element {
  constructor(id) { this.id = id; this.value = ""; this.disabled = false; this.checked = false;
    this.open = false; this.dataset = {}; this.events = new Map(); this.textContent = ""; }
  addEventListener(name, fn) { this.events.set(name, fn); }
  removeEventListener(name) { this.events.delete(name); }
  setAttribute() {}
  focus() { this.focused = true; }
  trigger(name) { return this.events.get(name)?.({ target: this }); }
}
function scene() {
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map((match) => [match[1], new Element(match[1])]));
  const node = (id) => { assert.ok(nodes.has(id), id); return nodes.get(id); };
  const calls = [], visual = []; let options;
  let state = { status: "idle", asrEnabled: false, ttsEnabled: false, autoSpeak: false, audioReady: false };
  const set = (change) => { state = { ...state, ...change }; options.onState(state); };
  const voice = { getState: () => state, getLevel: () => .37,
    initialize: async () => { calls.push("initialize"); set({ asrEnabled: true, ttsEnabled: true, engine: "qwen3_tts" }); },
    startCapture: () => calls.push("capture"), finishCapture: () => calls.push("finish"),
    cancel: () => calls.push("cancel"), clear: () => calls.push("clear"),
    pageHide: () => calls.push("hide"), refresh: () => calls.push("refresh"),
    dispose: () => calls.push("dispose"), updateCore: (value) => calls.push(["core", value]),
    arm: async () => { calls.push("arm"); }, setAutoSpeak: (value) => { calls.push(["auto", value]); set({ autoSpeak: value }); },
    playPending: () => calls.push("play") };
  const controls = createLiveVoiceControls({ document: { getElementById: node }, request() { assert.fail("no direct HTTP"); },
    createVoice(value) { options = value; return voice; }, beforeVoice: () => calls.push("arbitrate"),
    onVoiceState: (value) => visual.push(value.status) });
  return { controls, node, calls, set, visual, transcript: (text) => options.onTranscript(text),
    paired: (sessionRef = "one", status = "ready") => controls.updateCore({ paired: true, sessionRef, status }) };
}

test("real markup has explicit disabled capture and opt-in speech; no permission on preparation", async () => {
  assert.match(html, /id="live-mic-start"[^>]+disabled/);
  assert.match(html, /id="live-auto-speak"[^>]+disabled/);
  assert.doesNotMatch(html.match(/<input id="live-auto-speak"[^>]*>/)[0], /checked/);
  const s = scene(); assert.equal(s.calls.length, 0);
  s.paired(); assert.equal(s.node("live-mic-start").disabled, true);
  await s.node("live-voice-enable").trigger("click");
  assert.equal(s.node("live-mic-start").disabled, false);
  assert.equal(s.calls.filter((item) => item === "capture").length, 0);
});
test("microphone and response playback explicitly arbitrate the manual audio player", async () => {
  const s = scene(); s.paired(); await s.node("live-voice-enable").trigger("click");
  s.node("live-mic-start").trigger("click");
  assert.deepEqual(s.calls.slice(-2), ["arbitrate", "capture"]);
  s.set({ audioReady: true, status: "audio_ready" }); s.node("live-voice-play").trigger("click");
  assert.deepEqual(s.calls.slice(-2), ["arbitrate", "play"]);
});
test("the dock microphone can explicitly finish a recording or transcribe its retained bounded clip", async () => {
  const s = scene(); s.paired(); await s.node("live-voice-enable").trigger("click");
  for (const status of ["recording", "capture_ready"]) {
    s.set({ status }); assert.equal(s.node("live-mic-start").disabled, false);
    s.node("live-mic-start").trigger("click"); assert.equal(s.calls.at(-1), "finish");
  }
});
test("ASR creates a separate editable review without overwriting or submitting the composer", () => {
  const s = scene(); s.paired(); s.node("live-query").value = "Existing draft";
  s.transcript("Texto exato\n<literal> 😀");
  assert.equal(s.node("live-query").value, "Existing draft");
  assert.equal(s.node("live-voice-review").open, true);
  assert.equal(s.node("live-voice-transcript").focused, true);
  s.node("live-voice-transcript").value = "Texto revisado";
  s.node("live-voice-apply").trigger("click");
  assert.equal(s.node("live-query").value, "Texto revisado");
  assert.equal(s.node("live-query").focused, true);
  assert.equal(s.node("live-voice-review").open, false);
  assert.equal(s.calls.some((item) => item === "submit"), false);
});
test("busy Core never accepts review and a foreign session discards the visible draft", () => {
  const s = scene(); s.paired(); s.transcript("private draft"); s.paired("one", "waiting");
  s.node("live-voice-apply").trigger("click"); assert.equal(s.node("live-query").value, "");
  s.paired("two"); assert.equal(s.node("live-voice-transcript").value, "");
  assert.equal(s.node("live-voice-review").open, false);
});
test("speech consent uses a gesture arm and is reflected honestly without a microphone call", async () => {
  const s = scene(); s.paired(); await s.node("live-voice-enable").trigger("click");
  s.node("live-auto-speak").checked = true; s.node("live-auto-speak").trigger("change");
  assert.deepEqual(s.calls.slice(-2), ["arm", ["auto", true]]);
  assert.equal(s.calls.includes("capture"), false);
  s.set({ status: "playing" }); assert.match(s.node("live-voice-status").textContent, /JARVIS falando/);
  assert.equal(s.controls.getLevel(), .37);
});
test("hide and disposal clear review and remove every input listener", () => {
  const s = scene(); s.paired(); s.transcript("private draft"); s.controls.pageHide();
  assert.equal(s.node("live-voice-transcript").value, "");
  s.controls.dispose(); const before = s.calls.length;
  s.node("live-mic-start").trigger("click"); assert.equal(s.calls.length, before);
});
