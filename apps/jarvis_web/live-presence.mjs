import { createParticleSphere } from "./particle-sphere.mjs";
import { createLocalVoicePlayback } from "./local-voice-playback.mjs";

// Presentation for manual WAV rehearsal and the authenticated canonical speech
// bridge. This renderer itself never captures, synthesizes, fetches or dispatches.
const AUDIO_NOTICES = Object.freeze({
  empty: "Nenhum áudio local selecionado. Sem microfone ou voz automática.",
  loading: "Validando WAV local… O arquivo permanece neste navegador.",
  ready: "WAV pronto. Clique para reproduzir; arquivo não enviado ou salvo.",
  starting: "Preparando reprodução local… Você pode interromper.",
  playing: "Áudio local em reprodução. A esfera reage à amplitude real, não ao conteúdo.",
  error: "WAV incompatível ou áudio indisponível. Use PCM16 mono/estéreo, 8–96 kHz, até 600 s / 32 MiB.",
});
const INERT = Object.freeze({ update() {}, clear() {}, pageHide() {}, refresh() {}, dispose() {},
  setConversationState() {} });

export function createLivePresence({
  document = globalThis.document, host = globalThis,
  createSphere = createParticleSphere, createPlayback = createLocalVoicePlayback,
  makeContext, yieldTask, requestFrame, cancelFrame, getVoiceLevel = () => 0,
  beforeManualPlayback = () => {},
} = {}) {
  const node = (id) => document?.getElementById?.(id);
  const canvas = node("live-particle-sphere");
  // Older consumers and tests may not have the optional presentation surface.
  if (!canvas || typeof canvas.getContext !== "function" ||
      (canvas.localName && canvas.localName !== "canvas")) return INERT;
  const statusNode = node("live-presence-status"), motionButton = node("live-motion");
  const panel = node("live-audio-panel"), openButton = node("live-audio-open");
  const input = node("live-audio-file"), playButton = node("live-audio-play");
  const stopButton = node("live-audio-stop"), clearButton = node("live-audio-clear");
  const notice = node("live-audio-notice");
  const listeners = [];
  let disposed = false, suspended = false, motionPaused = false, sphere = null;
  let live = { status: "disconnected", paired: false, errorCode: null };
  let audioStatus = "empty";
  let conversationStatus = "idle";
  const playback = createPlayback({
    ...(makeContext ? { makeContext } : {
      makeContext: () => new host.AudioContext(),
    }),
    ...(yieldTask ? { yieldTask } : {}),
    onState(state) {
      audioStatus = Object.hasOwn(AUDIO_NOTICES, state.status) ? state.status : "error";
      render();
    },
  });
  const frameOptions = {
    ...(requestFrame ? { requestFrame } : host.requestAnimationFrame ? {
      requestFrame: (callback) => host.requestAnimationFrame(callback),
    } : {}),
    ...(cancelFrame ? { cancelFrame } : host.cancelAnimationFrame ? {
      cancelFrame: (id) => host.cancelAnimationFrame(id),
    } : {}),
  };
  try {
    sphere = createSphere(canvas, { host, ...frameOptions,
      getLevel: () => disposed || suspended ? 0 : conversationStatus === "playing" ?
        getVoiceLevel() : playback.getLevel() });
  } catch {
    // Canvas acceleration can be unavailable while the textual UI remains useful.
    sphere = null;
  }
  function listen(element, name, callback) {
    if (typeof element?.addEventListener !== "function") return;
    element.addEventListener(name, callback);
    listeners.push(() => element.removeEventListener?.(name, callback));
  }
  function render() {
    if (disposed) return;
    let mode = "idle", label = live.paired ? "Core conectado · em repouso" : "Em repouso · sessão não pareada";
    if (live.errorCode || live.status === "failed") {
      mode = "error"; label = "Sessão requer atenção · consulte o aviso";
    } else if (["connecting", "submitting", "waiting"].includes(live.status)) {
      mode = "thinking";
      label = live.status === "connecting" ? "Verificando sessão local…" : "Aguardando a resposta do Core…";
    }
    if (audioStatus === "playing") {
      mode = "speaking_local"; label = "Áudio local · amplitude real · sem microfone";
    }
    if (conversationStatus === "playing") {
      mode = "speaking_local"; label = "JARVIS falando · final do Core · amplitude real";
    } else if (["requesting_microphone", "recording", "capture_ready"].includes(conversationStatus)) {
      mode = "idle"; label = conversationStatus === "recording" ?
        "Microfone ativo · gravação local para revisão" : conversationStatus === "capture_ready" ?
          "Gravação encerrada · aguardando transcrição" : "Aguardando permissão do microfone…";
    } else if (["transcribing", "synthesizing", "starting_audio"].includes(conversationStatus)) {
      mode = "thinking"; label = conversationStatus === "transcribing" ?
        "Transcrevendo localmente…" : "Preparando a voz da resposta final…";
    }
    if (suspended || document?.hidden) {
      mode = "idle"; label = "Em repouso · página inativa";
    }
    sphere?.setMode(mode);
    if (statusNode) statusNode.textContent = label;
    if (notice) notice.textContent = AUDIO_NOTICES[audioStatus];
    if (playButton) playButton.disabled = suspended || audioStatus !== "ready";
    if (stopButton) stopButton.disabled = !["loading", "starting", "playing"].includes(audioStatus);
    if (clearButton) clearButton.disabled = audioStatus === "empty";
    canvas.setAttribute?.("data-audio-state", audioStatus);
    if (motionButton) {
      motionButton.setAttribute?.("aria-pressed", String(motionPaused));
      motionButton.textContent = motionPaused ? "Retomar animação" : "Pausar animação";
    }
  }
  function clear() {
    if (disposed) return;
    if (input) input.value = "";
    playback.clear(); render();
  }
  listen(input, "change", (event) => {
    const target = event.target ?? input;
    const file = target.files?.[0];
    target.value = ""; // Remove native filename before asynchronous or user-defined reads.
    if (!file || disposed || suspended || document?.hidden) return;
    return playback.selectFile(file);
  });
  listen(playButton, "click", () => {
    if (!disposed && !suspended && !document?.hidden) {
      beforeManualPlayback(); return playback.play();
    }
  });
  listen(stopButton, "click", () => { if (!disposed) playback.stop(); });
  listen(clearButton, "click", clear);
  listen(openButton, "click", () => {
    if (disposed || suspended) return;
    if (panel) panel.open = true;
    input?.focus?.(); // Reveal the controls below the orb on narrow/zoomed layouts.
  });
  listen(motionButton, "click", () => {
    if (disposed || suspended) return;
    motionPaused = !motionPaused;
    sphere?.setMotion(!motionPaused); render();
  });
  listen(document, "visibilitychange", () => {
    if (disposed) return;
    if (document.hidden) playback.stop();
    render();
  });
  render();
  return Object.freeze({
    update({ status = "disconnected", paired = false, errorCode = null } = {}) {
      if (disposed) return;
      live = { status, paired: paired === true, errorCode: errorCode ? true : null };
      render();
    },
    clear,
    setConversationState(status = "idle") {
      if (disposed) return;
      conversationStatus = status; render();
    },
    pageHide() {
      if (disposed) return;
      suspended = true;
      clear(); sphere?.setMotion(false); render();
    },
    refresh() {
      if (disposed) return;
      suspended = false;
      sphere?.setMotion(!motionPaused); render();
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      if (input) input.value = "";
      for (const remove of listeners) remove();
      playback.dispose(); sphere?.dispose();
    },
  });
}
