import { createConversationVoice } from "./live-conversation-voice.mjs";

// View binding only: review copies into the existing composer, never submits it.
export function createLiveVoiceControls({ document = globalThis.document, host = globalThis,
  request, onVoiceState = () => {}, beforeVoice = () => {}, createVoice = createConversationVoice } = {}) {
  const node = (id) => document?.getElementById?.(id);
  if (!node("live-mic-start")) return Object.freeze({ updateCore() {}, clear() {}, pageHide() {},
    refresh() {}, dispose() {}, cancel() {}, getLevel: () => 0 });
  const listeners = []; let paired = false, busy = false, disposed = false, sessionRef = null;
  let voice;
  const notices = {
    idle: "Voz local desligada até você preparar os motores. Nenhum microfone aberto.",
    loading_config: "Verificando os motores locais…",
    requesting_microphone: "Aguardando sua permissão para o microfone…",
    recording: "Gravando no navegador · até 30 segundos. Clique em Transcrever para revisar.",
    capture_ready: "Gravação encerrada. Clique em Transcrever; nada foi enviado ao Core.",
    transcribing: "Transcrevendo no computador. Aguarde para revisar; nada enviado ao Core.",
    transcript_ready: "Transcrição pronta para revisão. Use no pedido e clique em Enviar quando concordar.",
    synthesizing: "Gerando a fala local da resposta final do Core…",
    audio_ready: "Resposta em áudio pronta. Se não tocar, clique em Reproduzir resposta.",
    starting_audio: "Preparando a reprodução da resposta…",
    playing: "JARVIS falando · esfera sincronizada com a amplitude real.",
  };
  function render(state) {
    if (disposed) return;
    const capturing = ["requesting_microphone", "recording", "capture_ready"].includes(state.status);
    const active = capturing || ["transcribing", "synthesizing", "starting_audio", "playing"].includes(state.status);
    node("live-voice-enable").disabled = !paired || busy || active || state.status === "loading_config";
    node("live-mic-start").disabled = !paired || busy || !state.asrEnabled ||
      (active && !["recording", "capture_ready"].includes(state.status));
    node("live-mic-start").setAttribute?.("aria-label", state.status === "recording" ?
      "Encerrar gravação e transcrever localmente" : state.status === "capture_ready" ?
        "Transcrever gravação encerrada" : "Gravar microfone para revisão local");
    node("live-mic-finish").disabled = !paired || !["recording", "capture_ready"].includes(state.status);
    node("live-voice-cancel").disabled = !active && !state.audioReady;
    node("live-voice-play").disabled = !paired || busy || !state.audioReady || state.status === "playing";
    node("live-auto-speak").disabled = !paired || !state.ttsEnabled;
    node("live-auto-speak").checked = state.autoSpeak;
    node("live-voice-apply").disabled = !paired || busy || !node("live-voice-transcript").value.trim();
    node("live-mic-start").setAttribute?.("aria-pressed", String(state.status === "recording"));
    node("live-voice-status").textContent = state.status === "error" ?
      `Voz indisponível (${state.errorCode}). O texto e a final do Core continuam disponíveis.` :
      state.status === "idle" && (state.asrEnabled || state.ttsEnabled) ?
        `Motores locais preparados · fala ${state.engine ?? "não configurada"} experimental, qualidade não homologada.` :
        state.status === "idle" && paired && node("live-voice-enable").dataset.prepared === "true" ?
          "Motores de voz não habilitados ou indisponíveis no host. O modo textual continua disponível." :
          notices[state.status] ?? "Voz local em repouso.";
    onVoiceState(state);
  }
  voice = createVoice({ request, host, onState: render, onTranscript(text) {
    if (!paired || disposed) return;
    node("live-voice-transcript").value = text;
    node("live-voice-review").open = true;
    node("live-voice-transcript").focus?.();
    render(voice.getState());
  } });
  function listen(id, event, action) {
    const element = node(id); element.addEventListener(event, action);
    listeners.push(() => element.removeEventListener?.(event, action));
  }
  listen("live-voice-enable", "click", async () => {
    if (!paired || busy) return;
    node("live-voice-enable").dataset.prepared = "true";
    await voice.initialize();
  });
  listen("live-mic-start", "click", () => {
    if (!paired || busy) return;
    if (["recording", "capture_ready"].includes(voice.getState().status)) return voice.finishCapture();
    beforeVoice(); return voice.startCapture();
  });
  listen("live-mic-finish", "click", () => voice.finishCapture());
  listen("live-voice-cancel", "click", () => voice.cancel());
  listen("live-voice-play", "click", () => { beforeVoice(); return voice.playPending(); });
  listen("live-auto-speak", "change", () => {
    const selected = node("live-auto-speak").checked === true;
    if (selected) { beforeVoice(); void voice.arm(); }
    voice.setAutoSpeak(selected);
  });
  listen("live-voice-transcript", "input", () => render(voice.getState()));
  listen("live-voice-apply", "click", () => {
    const text = node("live-voice-transcript").value;
    if (!paired || busy || !text.trim() || [...text].length > 4000) return;
    node("live-query").value = text; node("live-voice-review").open = false;
    node("live-query").focus?.();
  });
  function clearReview() {
    node("live-voice-transcript").value = ""; node("live-voice-review").open = false;
  }
  return Object.freeze({
    updateCore(state) {
      paired = state.paired === true;
      busy = ["connecting", "submitting", "waiting"].includes(state.status);
      if (!paired || sessionRef !== state.sessionRef) {
        clearReview(); node("live-voice-enable").dataset.prepared = "false";
      }
      sessionRef = paired ? state.sessionRef : null;
      voice.updateCore(state); render(voice.getState());
    },
    getLevel: () => voice.getLevel(),
    cancel() { voice.cancel(); },
    clear() { clearReview(); voice.clear(); },
    pageHide() { clearReview(); voice.pageHide(); },
    refresh() { voice.refresh(); },
    dispose() { if (disposed) return; for (const remove of listeners) remove();
      voice.dispose(); clearReview(); disposed = true; },
  });
}
