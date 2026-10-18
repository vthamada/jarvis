// Local PCM capture only. Permission is requested exclusively by start().
// ScriptProcessor is used as a compatibility fallback without a remote worklet,
// blob URL, encoder dependency, or an audible microphone monitoring route.
export const MAX_CAPTURE_SECONDS = 30;
export const MAX_CAPTURE_BYTES = 6 * 1024 * 1024;

export function encodeMonoPcmWav(chunks, sampleRate, {
  maxSeconds = MAX_CAPTURE_SECONDS, maxBytes = MAX_CAPTURE_BYTES,
} = {}) {
  if (!Number.isInteger(sampleRate) || sampleRate < 8000 || sampleRate > 96000 ||
      !Number.isFinite(maxSeconds) || maxSeconds <= 0 || maxSeconds > MAX_CAPTURE_SECONDS ||
      !Number.isSafeInteger(maxBytes) || maxBytes < 46 || maxBytes > MAX_CAPTURE_BYTES ||
      !Array.isArray(chunks)) throw new Error("invalid_capture");
  let frames = 0;
  for (const chunk of chunks) {
    if (!(chunk instanceof Float32Array)) throw new Error("invalid_capture");
    frames += chunk.length;
    if (frames > Math.floor(sampleRate * maxSeconds) || 44 + frames * 2 > maxBytes)
      throw new Error("capture_limit");
  }
  if (!frames) throw new Error("empty_capture");
  const buffer = new ArrayBuffer(44 + frames * 2), view = new DataView(buffer);
  const tag = (offset, value) => [...value].forEach((letter, i) => view.setUint8(offset + i, letter.charCodeAt(0)));
  tag(0, "RIFF"); tag(8, "WAVE"); tag(12, "fmt "); tag(36, "data");
  view.setUint32(4, buffer.byteLength - 8, true); view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  view.setUint32(40, frames * 2, true);
  let offset = 44;
  for (const chunk of chunks) for (const sample of chunk) {
    if (!Number.isFinite(sample)) throw new Error("invalid_capture");
    const bounded = Math.max(-1, Math.min(1, sample));
    view.setInt16(offset, Math.round(bounded * (bounded < 0 ? 32768 : 32767)), true);
    offset += 2;
  }
  return buffer;
}

export function createMicrophoneCapture({
  host = globalThis, onState = () => {}, makeContext,
  getUserMedia, setTimer = (fn, ms) => host.setTimeout(fn, ms),
  clearTimer = (id) => host.clearTimeout(id),
  maxSeconds = MAX_CAPTURE_SECONDS, maxBytes = MAX_CAPTURE_BYTES,
} = {}) {
  if (!Number.isFinite(maxSeconds) || maxSeconds <= 0 || maxSeconds > MAX_CAPTURE_SECONDS ||
      !Number.isSafeInteger(maxBytes) || maxBytes < 46 || maxBytes > MAX_CAPTURE_BYTES)
    throw new Error("invalid_capture_limits");
  const document = host.document, subscribers = new Set();
  let status = "idle", errorCode = null, generation = 0, disposed = false;
  let context = null, stream = null, source = null, processor = null, gain = null, timer = null;
  let chunks = [], frames = 0, rate = 0, level = 0, captured = null, cancelPending = null;
  const trackListeners = [];
  const getState = () => Object.freeze({ status, errorCode, seconds: rate ? frames / rate : 0 });
  const safely = (fn) => { try { return fn(); } catch {} };
  function emit(next, code = null) {
    status = next; errorCode = code;
    const snapshot = getState();
    for (const listener of [onState, ...subscribers]) safely(() => listener(snapshot));
  }
  function stopTracks(value) {
    for (const track of safely(() => value?.getTracks()) ?? []) safely(() => track.stop());
  }
  function release() {
    if (timer !== null) safely(() => clearTimer(timer));
    timer = null; level = 0;
    for (const remove of trackListeners.splice(0)) safely(remove);
    const oldProcessor = processor, oldSource = source, oldGain = gain, oldContext = context, oldStream = stream;
    processor = null; source = null; gain = null; context = null; stream = null;
    if (oldProcessor) safely(() => { oldProcessor.onaudioprocess = null; });
    for (const node of [oldSource, oldProcessor, oldGain]) if (node) safely(() => node.disconnect());
    stopTracks(oldStream);
    if (oldContext) safely(() => Promise.resolve(oldContext.close()).catch(() => {}));
  }
  function cancel() {
    if (disposed) return;
    generation++;
    const pending = cancelPending; cancelPending = null; pending?.();
    chunks = []; captured = null; frames = 0; rate = 0; release(); emit("idle");
  }
  function finish() {
    if (disposed || status !== "recording") return;
    generation++; release();
    try { captured = encodeMonoPcmWav(chunks, rate, { maxSeconds, maxBytes }); chunks = []; emit("ready"); }
    catch (error) { chunks = []; captured = null; emit("error", error?.message === "empty_capture" ? "empty_capture" : "capture_unavailable"); }
  }
  async function start() {
    if (disposed || ["requesting", "recording"].includes(status) || document?.hidden) return false;
    cancel(); const token = ++generation;
    const current = () => !disposed && token === generation && !document?.hidden;
    let localStream = null;
    emit("requesting");
    if (!current()) return false;
    try {
      const cancelled = new Promise((resolve) => { cancelPending = () => resolve(null); });
      const acquire = getUserMedia ?? ((options) => host.navigator.mediaDevices.getUserMedia(options));
      // Invoke synchronously inside the explicit start gesture, before any await.
      const permission = Promise.resolve(acquire({ audio: {
        channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: false,
      }, video: false }));
      permission.then((late) => { if (!current()) stopTracks(late); }, () => {});
      localStream = await Promise.race([permission, cancelled]);
      if (!current() || !localStream) { stopTracks(localStream); return false; }
      stream = localStream;
      const tracks = stream.getAudioTracks();
      if (!tracks.length || tracks.some((track) => track.readyState === "ended")) throw new Error("capture_unavailable");
      context = makeContext ? makeContext() : new (host.AudioContext ?? host.webkitAudioContext)();
      if (!current()) { release(); return false; }
      rate = context.sampleRate;
      if (!Number.isInteger(rate) || rate < 8000 || rate > 96000) throw new Error("capture_unavailable");
      await Promise.race([context.resume(), cancelled]);
      if (!current()) return false;
      source = context.createMediaStreamSource(stream);
      processor = context.createScriptProcessor(4096, 1, 1);
      gain = context.createGain(); gain.gain.value = 0;
      const bound = Math.min(Math.floor(rate * maxSeconds), Math.floor((maxBytes - 44) / 2));
      processor.onaudioprocess = (event) => {
        if (!current() || status !== "recording") return;
        try {
          // Output is always zero; microphone samples never reach the speakers.
          event.outputBuffer.getChannelData(0).fill(0);
          const input = event.inputBuffer.getChannelData(0);
          if (!(input instanceof Float32Array)) throw new Error("capture_unavailable");
          const length = Math.min(input.length, bound - frames);
          if (length > 0) {
            const copy = input.slice(0, length); let power = 0;
            for (const sample of copy) {
              if (!Number.isFinite(sample)) throw new Error("capture_unavailable");
              power += Math.min(1, sample * sample);
            }
            chunks.push(copy); frames += length;
            level = Math.min(1, Math.sqrt(power / length) * 3);
          }
          if (frames >= bound) finish();
        } catch { if (current()) { generation++; release(); chunks = []; emit("error", "capture_unavailable"); } }
      };
      for (const track of tracks) {
        const ended = () => { if (current()) { cancel(); emit("error", "capture_unavailable"); } };
        track.addEventListener?.("ended", ended);
        trackListeners.push(() => track.removeEventListener?.("ended", ended));
      }
      source.connect(processor); processor.connect(gain); gain.connect(context.destination);
      timer = setTimer(() => { if (current()) finish(); }, maxSeconds * 1000);
      cancelPending = null;
      emit("recording"); return current() && status === "recording";
    } catch (error) {
      if (!current()) { if (localStream !== stream) stopTracks(localStream); return false; }
      release(); chunks = []; cancelPending = null;
      emit("error", ["NotAllowedError", "SecurityError"].includes(error?.name) ? "microphone_refused" : "capture_unavailable");
      return false;
    }
  }
  const hidden = () => { if (document?.hidden) cancel(); };
  const pageHide = () => cancel();
  document?.addEventListener?.("visibilitychange", hidden);
  host.addEventListener?.("pagehide", pageHide);
  return Object.freeze({
    start,
    async stop() {
      if (status === "requesting") { cancel(); return null; }
      finish(); const result = captured; captured = null; return result;
    },
    cancel, getState, getLevel: () => status === "recording" && !disposed ? level : 0,
    subscribe(listener) {
      if (disposed || typeof listener !== "function") return () => {};
      subscribers.add(listener); return () => subscribers.delete(listener);
    },
    dispose() {
      if (disposed) return;
      cancel(); disposed = true; status = "disposed";
      document?.removeEventListener?.("visibilitychange", hidden);
      host.removeEventListener?.("pagehide", pageHide); subscribers.clear();
    },
  });
}
