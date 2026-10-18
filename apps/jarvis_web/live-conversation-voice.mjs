import { createLocalVoicePlayback, inspectPcmWav } from "./local-voice-playback.mjs";
import { createMicrophoneCapture, MAX_CAPTURE_BYTES, MAX_CAPTURE_SECONDS } from "./microphone-capture.mjs";

const JOB = /^voice-job-[a-f0-9]{32}$/, TICKET = /^web-request-[a-f0-9]{32}$/;
const SESSION = /^session:\/\/web-live\/[a-f0-9]{32}$/;
const ERRORS = new Set(["voice_disabled", "voice_busy", "voice_invalid", "voice_unavailable",
  "voice_cancelled", "voice_expired", "voice_ticket_refused", "voice_timeout", "invalid_response",
  "microphone_refused", "capture_unavailable", "empty_capture", "audio_device_unavailable"]);
const JOB_ERRORS = new Set(["voice_disabled", "voice_busy", "voice_invalid", "voice_unavailable",
  "voice_cancelled", "voice_expired", "voice_ticket_refused"]);
const exact = (value, fields) => value && typeof value === "object" && !Array.isArray(value) &&
  Object.keys(value).length === fields.length && fields.every((field) => Object.hasOwn(value, field));
const fail = (code = "invalid_response") => { throw new Error(code); };
function configuration(value) {
  if (!exact(value, ["schema_version", "asr_enabled", "tts_enabled", "engine", "max_capture_seconds", "max_wav_bytes"]) ||
      value.schema_version !== "jarvis-local-voice-config-v1" || typeof value.asr_enabled !== "boolean" ||
      typeof value.tts_enabled !== "boolean" ||
      !(value.engine === null || (typeof value.engine === "string" && /^[a-zA-Z0-9_.-]{1,80}$/.test(value.engine))) ||
      (value.tts_enabled && value.engine === null) ||
      (!value.tts_enabled && value.engine !== null) ||
      !Number.isFinite(value.max_capture_seconds) || value.max_capture_seconds <= 0 || value.max_capture_seconds > MAX_CAPTURE_SECONDS ||
      !Number.isSafeInteger(value.max_wav_bytes) || value.max_wav_bytes < 46 || value.max_wav_bytes > MAX_CAPTURE_BYTES) fail();
  return Object.freeze({ ...value });
}
function jobEnvelope(value, kind, expected = null) {
  if (!exact(value, ["schema_version", "job_id", "kind", "status", "error_code", "transcript", "audio_available"]) ||
      value.schema_version !== "jarvis-local-voice-job-v1" || typeof value.job_id !== "string" || !JOB.test(value.job_id) ||
      (expected !== null && value.job_id !== expected) || value.kind !== kind ||
      !["running", "completed", "failed"].includes(value.status) || typeof value.audio_available !== "boolean") fail();
  if (value.status === "failed") {
    if (!JOB_ERRORS.has(value.error_code) || value.transcript !== null || value.audio_available) fail();
  } else if (value.error_code !== null) fail();
  if (value.status === "running" && (value.transcript !== null || value.audio_available)) fail();
  if (value.status === "completed") {
    if (kind === "speech" && (value.transcript !== null || !value.audio_available)) fail();
    if (kind === "transcription" && (value.audio_available || typeof value.transcript !== "string" ||
        !value.transcript.trim() || [...value.transcript].length > 4000 ||
        /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\u200b\u2028\u2029]/u.test(value.transcript) ||
        /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value.transcript))) fail();
  }
  return value;
}

// This module has no authority to submit a Core request. ASR ends at review;
// speech uses a server-bound canonical ticket, never text supplied by the client.
export function createConversationVoice({
  request, capture, createPlayback = createLocalVoicePlayback,
  host = globalThis, onState = () => {}, onTranscript = () => {}, makeContext,
  setTimer = (fn, ms) => host.setTimeout(fn, ms), clearTimer = (id) => host.clearTimeout(id),
  pollIntervalMs = 500, timeoutMs = 300000,
} = {}) {
  if (typeof request !== "function" || !Number.isFinite(pollIntervalMs) || pollIntervalMs < 0 ||
      pollIntervalMs > 10000 || !Number.isFinite(timeoutMs) || timeoutMs < 1 || timeoutMs > 300000)
    throw new Error("invalid_voice_options");
  let disposed = false, suspended = false, generation = 0, config = null, autoSpeak = false;
  let status = "idle", errorCode = null, abort = null, timer = null, activeJob = null, candidate = null;
  let context = null, audioReady = false, playing = false, playbackState = "empty", pendingAudio = null;
  const audioWaiters = new Set();
  let core = { paired: false, sessionRef: null, status: "disconnected", ticket: null };
  const mic = capture ?? createMicrophoneCapture({ host });
  const safely = (fn) => { try { return fn(); } catch {} };
  const validSession = () => core.paired === true && typeof core.sessionRef === "string" && SESSION.test(core.sessionRef);
  const available = () => !disposed && !suspended && !host.document?.hidden && validSession();
  const getState = () => Object.freeze({ status, errorCode, autoSpeak,
    asrEnabled: config?.asr_enabled === true, ttsEnabled: config?.tts_enabled === true,
    engine: config?.engine ?? null, captureStatus: mic.getState?.().status ?? "idle", audioReady });
  function emit(next = status, code = null) {
    if (disposed) return;
    status = next; errorCode = code; safely(() => onState(getState()));
  }
  function closeContext() {
    const old = context; context = null;
    if (old && old.state !== "closed") safely(() => Promise.resolve(old.close()).catch(() => {}));
  }
  const playback = createPlayback({ makeContext: () => {
    if (!context || context.state === "closed")
      context = makeContext ? makeContext() : new (host.AudioContext ?? host.webkitAudioContext)();
    return context;
  }, onState(value) {
    playbackState = value.status; playing = value.status === "playing";
    if (disposed) return;
    if (value.status === "playing") emit("playing");
    else if (value.status === "starting") emit("starting_audio");
    else if (value.status === "error") emit("error", "audio_device_unavailable");
    else if (value.status === "ready" && ["playing", "starting_audio"].includes(status)) emit("audio_ready");
  } });
  const unsubscribe = mic.subscribe?.((state) => {
    if (disposed || suspended) return;
    if (state.status === "recording") emit("recording");
    else if (state.status === "requesting") emit("requesting_microphone");
    else if (state.status === "ready") emit("capture_ready");
    else if (state.status === "error") emit("error", ERRORS.has(state.errorCode) ? state.errorCode : "capture_unavailable");
  }) ?? (() => {});
  function cancelJob(job, sessionRef) {
    if (!job || !validSession() || core.sessionRef !== sessionRef || disposed) return;
    safely(() => Promise.resolve(request("/api/voice/cancel", {
      method: "POST", body: { job_id: job },
    })).catch(() => {}));
  }
  function cancel({ keepUnusedArm = false } = {}) {
    if (disposed) return;
    const job = activeJob, sessionRef = core.sessionRef;
    generation++; abort?.abort(); abort = null;
    for (const resolve of audioWaiters) resolve(false);
    audioWaiters.clear();
    if (timer !== null) safely(() => clearTimer(timer));
    timer = null; activeJob = null;
    // Only an explicitly armed, not-yet-used context may survive a new Core
    // submission. Stop/hide/session cancellation always closes it.
    const retained = keepUnusedArm && playbackState === "empty" ? context : null;
    mic.cancel(); playback.clear();
    if (!retained) closeContext();
    audioReady = false; playing = false; playbackState = "empty"; pendingAudio = null;
    cancelJob(job, sessionRef); emit("idle");
  }
  function clear() { cancel(); config = null; autoSpeak = false; candidate = null; emit("idle"); }
  function begin(next, keepUnusedArm = false) {
    cancel({ keepUnusedArm }); const token = ++generation, sessionRef = core.sessionRef;
    const controller = new AbortController(); abort = controller;
    const current = () => !disposed && token === generation && available() && core.sessionRef === sessionRef;
    const check = () => { if (!current()) fail("voice_cancelled"); };
    timer = setTimer(() => {
      if (!current()) return;
      cancel(); emit("error", "voice_timeout");
    }, timeoutMs);
    emit(next);
    async function send(path, options = {}) {
      check();
      let remove = () => {};
      const interrupted = new Promise((_, reject) => {
        const listener = () => reject(new Error("voice_cancelled"));
        controller.signal.addEventListener("abort", listener, { once: true });
        remove = () => controller.signal.removeEventListener("abort", listener);
      });
      try {
        const reply = await Promise.race([
          Promise.resolve(request(path, { method: "GET", ...options, signal: controller.signal })), interrupted,
        ]);
        check(); return reply;
      } finally { remove(); }
    }
    async function pause() {
      check(); let id = null, remove = () => {};
      try {
        await new Promise((resolve, reject) => {
          const listener = () => reject(new Error("voice_cancelled"));
          controller.signal.addEventListener("abort", listener, { once: true });
          remove = () => controller.signal.removeEventListener("abort", listener);
          id = setTimer(resolve, pollIntervalMs);
        }); check();
      } finally { if (id !== null) safely(() => clearTimer(id)); remove(); }
    }
    function done() {
      if (!current()) return;
      if (timer !== null) safely(() => clearTimer(timer));
      timer = null; activeJob = null; abort = null;
    }
    function error(value) {
      if (!current()) return;
      const code = ERRORS.has(value?.message) ? value.message : "voice_unavailable";
      cancel(); emit("error", code);
    }
    return { current, check, send, pause, done, error };
  }
  async function poll(operation, kind, initial) {
    let job = jobEnvelope(initial, kind); activeJob = job.job_id;
    // The monotonic operation deadline bounds this loop, including stalled IO.
    while (job.status === "running") {
      await operation.pause();
      const reply = await operation.send("/api/voice/jobs/" + job.job_id);
      if (reply?.status !== 200) fail();
      job = jobEnvelope(reply.value, kind, job.job_id);
    }
    if (job.status === "failed") fail(job.error_code);
    return job;
  }
  async function initialize() {
    if (!available()) return false;
    config = null; autoSpeak = false;
    const operation = begin("loading_config");
    try {
      const reply = await operation.send("/api/voice/config");
      if (reply?.status !== 200) fail();
      config = configuration(reply.value); operation.done(); emit("idle"); return true;
    } catch (error) { operation.error(error); return false; }
  }
  async function audioWait(promise, token) {
    const pending = Promise.resolve(promise);
    if (disposed || token !== generation || !available()) { pending.catch(() => {}); return false; }
    let interrupt;
    const cancelled = new Promise((resolve) => { interrupt = resolve; audioWaiters.add(resolve); });
    try { return await Promise.race([pending, cancelled]); }
    finally { audioWaiters.delete(interrupt); }
  }
  async function arm() {
    if (!available() || !config?.tts_enabled) return false;
    const token = generation, sessionRef = core.sessionRef;
    try {
      if (!context || context.state === "closed")
        context = makeContext ? makeContext() : new (host.AudioContext ?? host.webkitAudioContext)();
      const armed = context;
      const resumed = await audioWait(Promise.resolve(armed.resume()).then(() => true), token);
      if (!resumed) return false;
      return !disposed && token === generation && available() && core.sessionRef === sessionRef && context === armed;
    } catch { if (!disposed && token === generation) emit("error", "audio_device_unavailable"); return false; }
  }
  async function startCapture() {
    if (!available() || !config?.asr_enabled || ["submitting", "waiting"].includes(core.status) ||
        ["requesting", "recording"].includes(mic.getState?.().status)) return false;
    cancel(); const token = generation, sessionRef = core.sessionRef;
    let started = false;
    try { started = await mic.start(); }
    catch { if (!disposed && token === generation) emit("error", "capture_unavailable"); }
    if (disposed || token !== generation || !available() || core.sessionRef !== sessionRef) return false;
    if (started) emit("recording");
    else if (mic.getState?.().status === "error") emit("error", ERRORS.has(mic.getState().errorCode) ? mic.getState().errorCode : "capture_unavailable");
    return started;
  }
  async function finishCapture() {
    if (!available() || !config?.asr_enabled) return false;
    const token = generation, sessionRef = core.sessionRef;
    let buffer;
    try { buffer = await mic.stop(); }
    catch { if (!disposed && token === generation) emit("error", "capture_unavailable"); return false; }
    if (disposed || token !== generation || !available() || core.sessionRef !== sessionRef || buffer === null) return false;
    const operation = begin("transcribing");
    try {
      let info;
      try { info = inspectPcmWav(buffer); } catch { fail("voice_invalid"); }
      if (info.channels !== 1 || info.duration > config.max_capture_seconds || buffer.byteLength > config.max_wav_bytes) fail("voice_invalid");
      const reply = await operation.send("/api/voice/transcriptions", { method: "POST", body: buffer,
        headers: { "Content-Type": "audio/wav", "X-Jarvis-Voice-Consent": "local-audio-v1" } });
      if (reply?.status !== 202) fail();
      const job = await poll(operation, "transcription", reply.value);
      operation.check(); operation.done(); emit("transcript_ready");
      // Review only. The containing UI must retain the explicit Send action.
      operation.check();
      safely(() => onTranscript(job.transcript)); return true;
    } catch (error) { operation.error(error); return false; }
  }
  async function playPending() {
    if (!available() || !audioReady || playing || !["ready", "error"].includes(playbackState)) return false;
    if (playbackState === "error") {
      const buffer = pendingAudio, token = generation;
      if (!buffer || !await playback.selectFile({ size: buffer.byteLength, arrayBuffer: async () => buffer }) ||
          token !== generation || !available()) return false;
    }
    return audioWait(playback.play(), generation);
  }
  async function speak(ticket) {
    const operation = begin("synthesizing", true);
    try {
      const reply = await operation.send("/api/voice/speech", { method: "POST", body: { ticket, consent: true } });
      if (reply?.status !== 202) fail();
      const job = await poll(operation, "speech", reply.value);
      const audio = await operation.send("/api/voice/audio/" + job.job_id, { binary: true });
      if (audio?.status !== 200 || !(audio.value instanceof ArrayBuffer)) fail();
      try { inspectPcmWav(audio.value); } catch { fail("voice_invalid"); }
      operation.check();
      const buffer = audio.value;
      if (!await playback.selectFile({ size: buffer.byteLength, arrayBuffer: async () => buffer })) fail("voice_invalid");
      operation.check(); pendingAudio = buffer; audioReady = true; operation.done(); emit("audio_ready");
      return await audioWait(playback.play(), generation);
    } catch (error) { operation.error(error); return false; }
  }
  function updateCore(next = {}) {
    if (disposed) return;
    const paired = next.paired === true && typeof next.sessionRef === "string" && SESSION.test(next.sessionRef);
    const changed = !paired || next.sessionRef !== core.sessionRef;
    if (changed) { clear(); core = { paired, sessionRef: paired ? next.sessionRef : null,
      status: next.status, ticket: next.ticket ?? null }; emit("idle"); return; }
    const previous = core;
    core = { paired, sessionRef: next.sessionRef, status: next.status, ticket: next.ticket ?? null };
    if (next.status !== "submitting" && (previous.ticket !== core.ticket ||
        (next.status === "waiting" && candidate !== core.ticket) ||
        (next.status === "ready" && previous.status !== "ready"))) {
      candidate = null; cancel();
    }
    if (next.status === "submitting") {
      if (previous.status !== "submitting" || previous.ticket !== next.ticket) cancel({ keepUnusedArm: true });
      candidate = typeof next.ticket === "string" && TICKET.test(next.ticket) ? next.ticket : null;
    } else if (["stopped", "failed", "disconnected", "error", "connecting"].includes(next.status)) {
      candidate = null; cancel();
    } else if (next.status === "completed") {
      const eligible = candidate !== null && candidate === next.ticket;
      candidate = null;
      const result = next.result;
      if (eligible && autoSpeak && config?.tts_enabled && available() &&
          result?.governance_decision === "allow" && result.evidence_mode === "core_local" &&
          result.authority === "none" && typeof result.response_text === "string" && result.response_text.trim()) {
        void speak(next.ticket);
      }
    }
    emit();
  }
  const visibility = () => { if (host.document?.hidden) cancel(); };
  host.document?.addEventListener?.("visibilitychange", visibility);
  return Object.freeze({ initialize, updateCore, startCapture, finishCapture, playPending, arm, unlockPlayback: arm,
    setAutoSpeak(value) { if (disposed) return; autoSpeak = value === true && available() && config?.tts_enabled === true;
      if (!autoSpeak && ["synthesizing", "starting_audio", "playing", "audio_ready"].includes(status)) cancel(); emit(); },
    getState, getLevel: () => !available() || !playing ? 0 : playback.getLevel(), cancel, clear,
    pageHide() { if (disposed) return; clear(); suspended = true; },
    refresh() { if (!disposed) { suspended = false; emit(); } },
    dispose() {
      if (disposed) return;
      clear(); disposed = true; unsubscribe(); mic.dispose(); playback.dispose(); closeContext();
      host.document?.removeEventListener?.("visibilitychange", visibility);
    },
  });
}
