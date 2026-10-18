import test from "node:test";
import assert from "node:assert/strict";
import { createConversationVoice } from "../live-conversation-voice.mjs";
import { encodeMonoPcmWav } from "../microphone-capture.mjs";

const ticket = "web-request-" + "a".repeat(32), secondTicket = "web-request-" + "b".repeat(32);
const sessionRef = "session://web-live/" + "c".repeat(32), jobId = "voice-job-" + "d".repeat(32);
const config = (changes = {}) => ({ schema_version: "jarvis-local-voice-config-v1", asr_enabled: true,
  tts_enabled: true, engine: "qwen3_tts", max_capture_seconds: 30, max_wav_bytes: 6 * 1024 * 1024, ...changes });
const job = (kind, status = "completed", changes = {}) => ({ schema_version: "jarvis-local-voice-job-v1",
  job_id: jobId, kind, status, error_code: null,
  transcript: kind === "transcription" && status === "completed" ? "Compare os relatórios do piloto." : null,
  audio_available: kind === "speech" && status === "completed", ...changes });
const result = (changes = {}) => ({ response_text: "Final canônica exata.\nSem substituição.", governance_decision: "allow",
  evidence_mode: "core_local", authority: "none", ...changes });
const wav = (sample = .25) => encodeMonoPcmWav([new Float32Array(80).fill(sample)], 8000);
const reply = (value, status = 200) => ({ value, status });
const deferred = () => { let resolve; const promise = new Promise((yes) => { resolve = yes; }); return { resolve, promise }; };
const flush = () => new Promise((resolve) => setTimeout(resolve, 5));
class Events {
  constructor() { this.handlers = new Map(); this.hidden = false; }
  addEventListener(name, fn) { const set = this.handlers.get(name) ?? new Set(); set.add(fn); this.handlers.set(name, set); }
  removeEventListener(name, fn) { this.handlers.get(name)?.delete(fn); }
  dispatch(name) { for (const fn of this.handlers.get(name) ?? []) fn(); }
}
function capturePort(buffer = wav()) {
  let status = "idle"; const listeners = new Set();
  const emit = (next) => { status = next; for (const listener of listeners) listener({ status }); };
  return { starts: 0, stops: 0, cancels: 0, disposed: 0,
    async start() { this.starts++; emit("recording"); return true; },
    async stop() { this.stops++; emit("ready"); return buffer; },
    cancel() { this.cancels++; emit("idle"); }, dispose() { this.disposed++; emit("idle"); },
    getState: () => ({ status }), subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }, emit };
}
function scene(responses = [], options = {}) {
  const calls = [], states = [], transcripts = [], contexts = [], sources = [], document = new Events();
  const capture = options.capture ?? capturePort();
  const host = { document, setTimeout, clearTimeout };
  const voice = createConversationVoice({ host, capture, pollIntervalMs: 0,
    onState: (state) => { states.push(state); options.onState?.(state); }, onTranscript: (text) => transcripts.push(text),
    makeContext() {
      const context = { state: "running", destination: {}, resumes: 0, closes: 0,
        async resume() { this.resumes++; if (options.rejectPlayback && this.resumes > 1) throw new Error("PRIVATE_DEVICE"); },
        close() { this.closes++; this.state = "closed"; return Promise.resolve(); },
        createBuffer(channels, frames) { const values = Array.from({ length: channels }, () => new Float32Array(frames));
          return { getChannelData: (index) => values[index] }; },
        createAnalyser() { return { disconnect() {}, connect() {}, getFloatTimeDomainData(values) {
          const pcm = sources.at(-1)?.buffer.getChannelData(0); values.fill(pcm?.[0] ?? 0);
        } }; },
        createBufferSource() { const source = { starts: 0, stops: 0, connect() {}, disconnect() {},
          start() { this.starts++; }, stop() { this.stops++; } }; sources.push(source); return source; } };
      contexts.push(context); return context;
    },
    request: async (path, init) => {
      calls.push({ path, ...init });
      if (path === "/api/voice/cancel") return reply(job("speech", "failed", { error_code: "voice_cancelled", audio_available: false }));
      const next = responses.shift(); assert.ok(next, `Unexpected request ${path}`);
      return typeof next === "function" ? next(path, init) : next;
    }, ...options });
  const core = (status = "ready", changes = {}) => voice.updateCore({ paired: true, sessionRef, status, ticket: null, ...changes });
  return { voice, calls, states, transcripts, contexts, sources, capture, document, core,
    async initialize() { core(); assert.equal(await voice.initialize(), true); },
    complete(changes = {}) { core("submitting", { ticket }); core("waiting", { ticket }); core("completed", { ticket, result: result(), ...changes }); },
  };
}

test("construction and recovered finals are inert; microphone and network require explicit operations", async () => {
  const s = scene(); assert.equal(s.calls.length, 0); assert.equal(s.capture.starts, 0); assert.equal(s.contexts.length, 0);
  s.voice.setAutoSpeak(true); assert.equal(s.voice.getState().autoSpeak, false);
  s.core("completed", { ticket, result: result() }); assert.equal(s.calls.length, 0);
  assert.equal(await s.voice.startCapture(), false); s.voice.dispose();
});
test("explicit config is session-bound and no disabled capability requests a microphone", async () => {
  const s = scene([reply(config({ asr_enabled: false, tts_enabled: false, engine: null }))]);
  await s.initialize(); assert.deepEqual(s.calls.map(({ path }) => path), ["/api/voice/config"]);
  assert.equal(await s.voice.startCapture(), false); assert.equal(await s.voice.arm(), false);
  s.voice.setAutoSpeak(true); s.complete(); assert.equal(s.calls.length, 1); assert.equal(s.contexts.length, 0); s.voice.dispose();
});
for (const mutation of [{ extra: true }, { asr_enabled: "true" }, { tts_enabled: true, engine: null },
  { max_capture_seconds: 31 }, { max_wav_bytes: 6291457 }, { engine: "PRIVATE/path" }, { schema_version: "other" }])
  test(`malformed configuration fails closed ${JSON.stringify(mutation)}`, async () => {
    const s = scene([reply(config(mutation))]); s.core(); assert.equal(await s.voice.initialize(), false);
    assert.equal(s.voice.getState().errorCode, "invalid_response"); assert.equal(await s.voice.startCapture(), false); s.voice.dispose();
  });

test("microphone -> local ASR -> exact review text never submits a Core task", async () => {
  const expected = "  Compare documentação e observabilidade.\n😀  ";
  const s = scene([reply(config()), reply(job("transcription", "running"), 202), reply(job("transcription", "completed", { transcript: expected }))]);
  await s.initialize(); assert.equal(await s.voice.startCapture(), true); assert.equal(s.capture.starts, 1);
  assert.equal(await s.voice.finishCapture(), true); assert.deepEqual(s.transcripts, [expected]);
  assert.deepEqual(s.calls.map(({ path }) => path), ["/api/voice/config", "/api/voice/transcriptions", "/api/voice/jobs/" + jobId]);
  assert.equal(s.calls[1].body instanceof ArrayBuffer, true);
  assert.deepEqual(s.calls[1].headers, { "Content-Type": "audio/wav", "X-Jarvis-Voice-Consent": "local-audio-v1" });
  assert.equal(s.calls[1].binary, undefined); assert.equal(s.voice.getState().status, "transcript_ready");
  assert.equal(s.sources.length, 0); s.voice.dispose();
});
test("auto-stop changes only local review readiness; there is no duration-limit upload", async () => {
  const s = scene([reply(config())]); await s.initialize(); await s.voice.startCapture();
  s.capture.emit("ready"); await flush(); assert.equal(s.voice.getState().status, "capture_ready");
  assert.equal(s.calls.length, 1); assert.equal(s.transcripts.length, 0); s.voice.dispose();
});
test("ASR refuses invalid captured audio before HTTP and exposes only a fixed code", async () => {
  const s = scene([reply(config())], { capture: capturePort(new ArrayBuffer(44)) }); await s.initialize();
  assert.equal(await s.voice.finishCapture(), false); assert.equal(s.calls.length, 1);
  assert.ok(["voice_invalid", "voice_unavailable"].includes(s.voice.getState().errorCode)); s.voice.dispose();
});

test("new allowed canonical completion uses only the bound ticket and real PCM drives RMS", async () => {
  const s = scene([reply(config()), reply(job("speech", "running"), 202), reply(job("speech")), reply(wav())]);
  await s.initialize(); s.voice.setAutoSpeak(true); assert.equal(await s.voice.arm(), true);
  const armed = s.contexts[0]; s.complete(); await flush(); await flush();
  assert.deepEqual(s.calls.map(({ path }) => path), ["/api/voice/config", "/api/voice/speech", "/api/voice/jobs/" + jobId, "/api/voice/audio/" + jobId]);
  assert.deepEqual(s.calls[1].body, { ticket, consent: true }); assert.equal(s.calls[3].binary, true);
  assert.equal(s.contexts.length, 1, "Use the context unlocked by the explicit opt-in gesture");
  assert.equal(armed.closes, 0); assert.equal(s.sources[0].starts, 1); assert.equal(s.voice.getState().status, "playing");
  assert.equal(s.voice.getLevel(), .75); assert.ok(!JSON.stringify(s.calls).includes("Final canônica"));
  s.sources[0].onended(); assert.equal(s.voice.getLevel(), 0); assert.equal(s.voice.getState().status, "audio_ready");
  s.voice.dispose(); assert.ok(armed.closes >= 1);
});
test("silent synthesized PCM never manufactures amplitude", async () => {
  const s = scene([reply(config()), reply(job("speech"), 202), reply(wav(0))]); await s.initialize();
  s.voice.setAutoSpeak(true); s.complete(); await flush(); assert.equal(s.voice.getState().status, "playing");
  assert.equal(s.voice.getLevel(), 0); s.voice.cancel(); assert.equal(s.voice.getLevel(), 0); s.voice.dispose();
});
for (const changes of [{ governance_decision: "block" }, { governance_decision: "defer_for_validation" },
  { authority: "admin" }, { evidence_mode: "fixture" }, { response_text: " " }])
  test(`non-eligible canonical result never speaks ${JSON.stringify(changes)}`, async () => {
    const s = scene([reply(config())]); await s.initialize(); s.voice.setAutoSpeak(true);
    s.complete({ result: result(changes) }); await flush(); assert.equal(s.calls.length, 1); s.voice.dispose();
  });
test("enabling, duplicate render, recovery, and a stopped submission never replay a final", async () => {
  const s = scene([reply(config())]); await s.initialize();
  s.complete(); s.voice.setAutoSpeak(true); s.core("completed", { ticket, result: result() });
  s.core("waiting", { ticket }); s.core("completed", { ticket, result: result() });
  s.core("submitting", { ticket: secondTicket }); s.core("stopped", { ticket: secondTicket });
  s.core("waiting", { ticket: secondTicket }); s.core("completed", { ticket: secondTicket, result: result() });
  await flush(); assert.equal(s.calls.length, 1); s.voice.dispose();
});
for (const action of ["cancel", "clear", "pageHide", "dispose", "hidden", "foreign_session", "unpair"]) {
  test(`${action} aborts stalled speech and ignores a late successful job without playback`, async () => {
    const gate = deferred(), s = scene([reply(config()), () => gate.promise]); await s.initialize();
    s.voice.setAutoSpeak(true); s.complete(); await flush(); assert.equal(s.calls.length, 2);
    if (action === "hidden") { s.document.hidden = true; s.document.dispatch("visibilitychange"); }
    else if (action === "foreign_session") s.core("ready", { sessionRef: "session://web-live/" + "e".repeat(32) });
    else if (action === "unpair") s.voice.updateCore({ paired: false });
    else s.voice[action]();
    assert.equal(s.calls[1].signal.aborted, true); gate.resolve(reply(job("speech"), 202)); await flush();
    assert.equal(s.calls.length, 2); assert.equal(s.sources.length, 0); assert.equal(s.voice.getLevel(), 0); s.voice.dispose();
  });
}
test("timeout settles stalled transport without retry and never exposes transport exception details", async () => {
  const gate = deferred(), s = scene([reply(config()), () => gate.promise], { timeoutMs: 20 }); await s.initialize();
  s.voice.setAutoSpeak(true); s.complete(); await new Promise((resolve) => setTimeout(resolve, 35));
  assert.equal(s.voice.getState().errorCode, "voice_timeout"); assert.equal(s.calls[1].signal.aborted, true);
  gate.resolve(reply(job("speech"), 202)); await flush(); assert.equal(s.calls.length, 2); s.voice.dispose();
});
test("cancelling a running known job sends one explicit cancellation and stops its polling", async () => {
  const s = scene([reply(config()), reply(job("speech", "running"), 202)], { pollIntervalMs: 1000 });
  await s.initialize(); s.voice.setAutoSpeak(true); s.complete(); await flush(); s.voice.cancel(); await flush();
  assert.equal(s.calls.filter(({ path }) => path === "/api/voice/cancel").length, 1);
  assert.deepEqual(s.calls.at(-1).body, { job_id: jobId }); assert.equal(s.sources.length, 0); s.voice.dispose();
});
test("session retirement while ASR resolves never fills a foreign composer", async () => {
  const gate = deferred(), s = scene([reply(config()), () => gate.promise]); await s.initialize();
  await s.voice.startCapture(); const finishing = s.voice.finishCapture(); await flush();
  s.voice.updateCore({ paired: false }); assert.equal(await finishing, false);
  gate.resolve(reply(job("transcription"), 202)); await flush(); assert.equal(s.transcripts.length, 0); s.voice.dispose();
});
for (const mutation of [{ extra: true }, { job_id: [jobId] }, { kind: "speech" }, { transcript: "\u0000" },
  { transcript: "a".repeat(4001) }, { transcript: "\ud800" }, { audio_available: true },
  { status: "failed", error_code: "PRIVATE_PATH", transcript: null }])
  test(`ASR job boundary rejects malformed envelope ${Object.keys(mutation)[0]}`, async () => {
    const s = scene([reply(config()), reply(job("transcription", "completed", mutation), 202)]); await s.initialize();
    await s.voice.startCapture(); assert.equal(await s.voice.finishCapture(), false); assert.equal(s.transcripts.length, 0);
    assert.equal(s.voice.getState().errorCode, "invalid_response"); assert.ok(!JSON.stringify(s.states).includes("PRIVATE")); s.voice.dispose();
  });
test("job polling cannot switch identifiers and cannot fall back to unbound audio", async () => {
  const s = scene([reply(config()), reply(job("speech", "running"), 202), reply(job("speech", "completed", { job_id: "voice-job-" + "f".repeat(32) }))]);
  await s.initialize(); s.voice.setAutoSpeak(true); s.complete(); await flush(); await flush();
  assert.equal(s.voice.getState().errorCode, "invalid_response"); assert.equal(s.sources.length, 0);
  assert.equal(s.calls.filter(({ path }) => path.startsWith("/api/voice/audio/")).length, 0); s.voice.dispose();
});
test("page refresh restores no microphone, audio, configuration, or auto-speech consent", async () => {
  const s = scene([reply(config()), reply(job("speech"), 202), reply(wav())]); await s.initialize();
  s.voice.setAutoSpeak(true); s.complete(); await flush(); s.voice.pageHide(); s.voice.refresh();
  assert.equal(s.voice.getState().autoSpeak, false); assert.equal(s.voice.getState().ttsEnabled, false);
  assert.equal(s.voice.getState().audioReady, false); assert.equal(s.voice.getLevel(), 0); assert.equal(s.sources[0].stops, 1);
  assert.equal(s.capture.starts, 0); assert.equal(s.calls.length, 3); s.voice.dispose();
});
test("explicit opt-in context unlock is cancelled promptly if its device resume stalls", async () => {
  const gate = deferred(); let closes = 0;
  const s = scene([reply(config())], { makeContext: () => ({ state: "suspended", resume: () => gate.promise,
    close() { closes++; return Promise.resolve(); } }) });
  await s.initialize(); const arming = s.voice.arm(); s.voice.cancel();
  assert.equal(await arming, false); assert.ok(closes >= 1); gate.resolve(); await flush();
  assert.equal(s.calls.length, 1); assert.equal(s.voice.getLevel(), 0); s.voice.dispose();
});
test("browser autoplay rejection keeps exact WAV for an explicit retry without another synthesis", async () => {
  const settings = { rejectPlayback: true };
  const s = scene([reply(config()), reply(job("speech"), 202), reply(wav())], settings); await s.initialize();
  s.voice.setAutoSpeak(true); await s.voice.arm(); s.complete(); await flush();
  assert.equal(s.voice.getState().status, "error"); assert.equal(s.voice.getState().audioReady, true);
  assert.equal(s.voice.getLevel(), 0); assert.equal(s.sources.length, 0);
  // Device/browser policy changes only because the user explicitly retries.
  settings.rejectPlayback = false;
  assert.equal(await s.voice.playPending(), true); assert.equal(s.sources[0].starts, 1);
  assert.equal(s.calls.length, 3); assert.equal(s.voice.getLevel(), .75); s.voice.dispose();
});
test("reconfiguration failure retires prior capabilities and consent instead of reusing stale config", async () => {
  const s = scene([reply(config()), reply(config({ extra: true }))]); await s.initialize(); s.voice.setAutoSpeak(true);
  assert.equal(await s.voice.initialize(), false); assert.equal(s.voice.getState().ttsEnabled, false);
  assert.equal(s.voice.getState().autoSpeak, false); assert.equal(await s.voice.startCapture(), false); s.voice.dispose();
});
test("retirement in transcript-ready state notification prevents the review callback too", async () => {
  let voice;
  const s = scene([reply(config()), reply(job("transcription"), 202)], {
    onState(state) { if (state.status === "transcript_ready") voice.clear(); },
  }); voice = s.voice; await s.initialize(); await s.voice.startCapture();
  assert.equal(await s.voice.finishCapture(), false); assert.equal(s.transcripts.length, 0); s.voice.dispose();
});
test("recovery waiting and an unrelated ticket stop prior narration without rearming it", async () => {
  for (const changed of [false, true]) {
    const s = scene([reply(config()), reply(job("speech"), 202), reply(wav())]); await s.initialize();
    s.voice.setAutoSpeak(true); s.complete(); await flush(); assert.equal(s.voice.getState().status, "playing");
    s.core("waiting", { ticket: changed ? secondTicket : ticket });
    assert.equal(s.voice.getLevel(), 0); assert.equal(s.sources[0].stops, 1);
    s.core("completed", { ticket: changed ? secondTicket : ticket, result: result() }); await flush();
    assert.equal(s.calls.length, 3); s.voice.dispose();
  }
});
