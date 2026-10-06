// Explicit local WAV rehearsal only. No microphone, URLs, network or Core authority.
export const MAX_WAV_BYTES = 32 * 1024 * 1024;
export const MAX_WAV_SECONDS = 600;
export const PCM_BLOCK_FRAMES = 16384;

export function inspectPcmWav(buffer) {
  try {
    return inspectWav(buffer);
  } catch {
    // Includes detached/forged ArrayBuffers and throwing getters, never their details.
    throw new Error("invalid_local_wav");
  }
}

function inspectWav(buffer) {
  if (!(buffer instanceof ArrayBuffer)) throw new Error("invalid_local_wav");
  const view = new DataView(buffer);
  // A caller can shadow ArrayBuffer.byteLength; the native view measures storage.
  const byteLength = view.byteLength;
  if (byteLength < 44 || byteLength > MAX_WAV_BYTES) throw new Error("invalid_local_wav");
  const tag = (offset) => String.fromCharCode(...new Uint8Array(buffer, offset, 4));
  if (tag(0) !== "RIFF" || tag(8) !== "WAVE" || view.getUint32(4, true) + 8 !== byteLength)
    throw new Error("invalid_local_wav");
  let format = null, data = null, offset = 12, chunks = 0;
  while (offset < byteLength) {
    if (++chunks > 64 || offset + 8 > byteLength) throw new Error("invalid_local_wav");
    const name = tag(offset), size = view.getUint32(offset + 4, true), start = offset + 8;
    const end = start + size;
    if (end + (size % 2) > byteLength) throw new Error("invalid_local_wav");
    if (name === "fmt ") {
      if (format || data || size !== 16 || view.getUint16(start, true) !== 1) throw new Error("invalid_local_wav");
      const channels = view.getUint16(start + 2, true), rate = view.getUint32(start + 4, true);
      if (![1, 2].includes(channels) || rate < 8000 || rate > 96000 ||
          view.getUint16(start + 14, true) !== 16 || view.getUint16(start + 12, true) !== channels * 2 ||
          view.getUint32(start + 8, true) !== rate * channels * 2) throw new Error("invalid_local_wav");
      format = { channels, rate };
    } else if (name === "data") {
      if (!format || data) throw new Error("invalid_local_wav");
      data = { offset: start, bytes: size };
    }
    offset = end + (size % 2);
  }
  if (offset !== byteLength || !format || !data || !data.bytes || data.bytes % (format.channels * 2)) throw new Error("invalid_local_wav");
  const frames = data.bytes / (format.channels * 2), duration = frames / format.rate;
  if (duration > MAX_WAV_SECONDS) throw new Error("invalid_local_wav");
  return Object.freeze({ ...format, ...data, frames, duration });
}

export function rmsLevel(samples) {
  if (!samples?.length) return 0;
  let power = 0;
  for (const sample of samples) {
    if (!Number.isFinite(sample)) return 0;
    power += Math.min(1, sample * sample);
  }
  return Math.min(1, Math.sqrt(power / samples.length) * 3);
}

export function createLocalVoicePlayback({
  makeContext = () => new globalThis.AudioContext(), onState = () => {},
  yieldTask = () => new Promise((resolve) => globalThis.setTimeout(resolve, 0)),
} = {}) {
  let status = "empty", generation = 0, raw = null, info = null;
  let context = null, source = null, analyser = null, samples = null, disposed = false;
  let notifying = false, externalDepth = 0;
  const releasedSources = new WeakSet(), releasedAnalysers = new WeakSet();
  function invoke(callback) {
    externalDepth++;
    try { return callback(); } finally { externalDepth--; }
  }
  function safely(callback) { try { invoke(callback); } catch {} }
  function emit(next, reason = null) {
    status = next;
    if (notifying) return;
    notifying = true;
    try {
      invoke(() => onState(Object.freeze({ status, evidenceMode: "local_audio_rehearsal", authority: "none", ...(reason ? { reason } : {}) })));
    } catch {} finally { notifying = false; }
  }
  function releaseNodes(oldSource, oldAnalyser) {
    const object = (value) => value !== null && (typeof value === "object" || typeof value === "function");
    if (object(oldSource) && !releasedSources.has(oldSource)) {
      releasedSources.add(oldSource);
      safely(() => { oldSource.onended = null; });
      safely(() => oldSource.stop());
      safely(() => oldSource.disconnect());
    }
    if (object(oldAnalyser) && !releasedAnalysers.has(oldAnalyser)) {
      releasedAnalysers.add(oldAnalyser);
      safely(() => oldAnalyser.disconnect());
    }
  }
  function stopNodes() {
    const oldSource = source, oldAnalyser = analyser;
    source = null; analyser = null; samples = null;
    releaseNodes(oldSource, oldAnalyser);
  }
  function closeContext(old) {
    if (old) safely(() => Promise.resolve(old.close()).catch(() => {}));
  }
  function stop() {
    if (disposed) return;
    const token = ++generation;
    stopNodes();
    if (!disposed && token === generation) emit(raw ? "ready" : "empty");
  }
  function clearSelection() {
    const token = ++generation;
    raw = null; info = null;
    const old = context; context = null;
    stopNodes(); closeContext(old);
    if (token === generation) emit("empty");
    return token;
  }
  function clear() {
    if (!disposed) clearSelection();
  }
  async function selectFile(file) {
    if (disposed || notifying || externalDepth) return false;
    const token = clearSelection();
    const current = () => !disposed && token === generation;
    let stage = "invalid_file_selection";
    try {
      if (!current()) return false;
      const size = invoke(() => file?.size);
      if (!current()) return false;
      const read = invoke(() => file?.arrayBuffer);
      if (!Number.isSafeInteger(size) || size < 44 || size > MAX_WAV_BYTES ||
          typeof read !== "function") throw new Error("invalid_file_selection");
      if (!current()) return false;
      emit("loading");
      if (!current()) return false;
      stage = "file_read_unavailable";
      const buffer = await invoke(() => read.call(file));
      if (!current()) return false;
      stage = "invalid_wav_format";
      if (new DataView(buffer).byteLength !== size) throw new Error("invalid_local_wav");
      const selectedInfo = inspectPcmWav(buffer);
      if (!current()) return false;
      info = selectedInfo; raw = buffer; emit("ready");
      return current() && status === "ready" && raw === buffer;
    } catch {
      if (current()) { raw = null; info = null; emit("error", stage); }
      return false;
    }
  }
  async function play() {
    if (disposed || notifying || externalDepth || status !== "ready" || !raw || !info) return false;
    const token = ++generation;
    const selectedRaw = raw, selectedInfo = info;
    const selected = () => !disposed && token === generation && raw === selectedRaw && info === selectedInfo;
    let activeContext = context, localSource = null, localAnalyser = null;
    const current = () => selected() && context === activeContext;
    emit("starting");
    try {
      if (!selected()) return false;
      if (!activeContext) {
        activeContext = invoke(() => makeContext());
        if (!selected()) { closeContext(activeContext); return false; }
        context = activeContext;
      }
      if (!current()) return false;
      await invoke(() => activeContext.resume());
      if (!current()) return false;
      const audio = invoke(() => activeContext.createBuffer(selectedInfo.channels, selectedInfo.frames, selectedInfo.rate));
      if (!current()) return false;
      const channels = [];
      for (let channel = 0; channel < selectedInfo.channels; channel++) {
        const values = invoke(() => audio.getChannelData(channel));
        if (!current()) return false;
        if (!(values instanceof Float32Array) || values.length !== selectedInfo.frames)
          throw new Error("invalid_audio_buffer");
        channels.push(values);
      }
      const view = new DataView(selectedRaw);
      for (let start = 0; start < selectedInfo.frames; start += PCM_BLOCK_FRAMES) {
        if (!current()) return false;
        const end = Math.min(start + PCM_BLOCK_FRAMES, selectedInfo.frames);
        for (let channel = 0; channel < selectedInfo.channels; channel++) {
          const values = channels[channel];
          for (let frame = start; frame < end; frame++)
            values[frame] = view.getInt16(selectedInfo.offset + (frame * selectedInfo.channels + channel) * 2, true) / 32768;
        }
        if (end < selectedInfo.frames) {
          await invoke(() => yieldTask());
          if (!current()) return false;
        }
      }
      if (!current()) return false;
      localAnalyser = invoke(() => activeContext.createAnalyser());
      if (!current()) return false;
      invoke(() => { localAnalyser.fftSize = 1024; });
      if (!current()) return false;
      const localSamples = new Float32Array(1024);
      localSource = invoke(() => activeContext.createBufferSource());
      if (!current()) return false;
      invoke(() => { localSource.buffer = audio; });
      if (!current()) return false;
      invoke(() => localSource.connect(localAnalyser));
      if (!current()) return false;
      invoke(() => localAnalyser.connect(activeContext.destination));
      if (!current()) return false;
      invoke(() => {
        localSource.onended = () => {
          if (!disposed && token === generation && context === activeContext && source === localSource) {
            stopNodes();
            if (!disposed && token === generation) emit(raw ? "ready" : "empty");
          }
        };
      });
      if (!current()) return false;
      source = localSource; analyser = localAnalyser; samples = localSamples;
      invoke(() => localSource.start());
      if (!current() || source !== localSource || analyser !== localAnalyser) return false;
      emit("playing");
      return current() && source === localSource && status === "playing";
    } catch {
      if (selected()) { stopNodes(); if (selected()) emit("error", "audio_device_unavailable"); }
      return false;
    } finally {
      if (source !== localSource || analyser !== localAnalyser)
        releaseNodes(source === localSource ? null : localSource, analyser === localAnalyser ? null : localAnalyser);
    }
  }
  return Object.freeze({
    selectFile, play, stop, clear,
    getStatus: () => status,
    getLevel: () => {
      try {
        const token = generation, activeAnalyser = analyser, activeContext = context, activeSamples = samples;
        if (disposed || status !== "playing" || !activeAnalyser || !activeContext ||
            invoke(() => activeContext.state) !== "running") return 0;
        if (disposed || token !== generation || status !== "playing") return 0;
        invoke(() => activeAnalyser.getFloatTimeDomainData(activeSamples));
        if (disposed || token !== generation || status !== "playing" ||
            analyser !== activeAnalyser || context !== activeContext) return 0;
        return rmsLevel(activeSamples);
      } catch { return 0; }
    },
    dispose: () => { if (!disposed) { disposed = true; clearSelection(); } },
  });
}
