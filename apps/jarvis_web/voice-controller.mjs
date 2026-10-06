// UI rehearsal only. This module never captures, decodes, uploads or plays audio.
const scenarios = new Set(["completed", "error", "incomplete", "empty"]);
const validText = (text) => typeof text === "string" && text.trim().length > 0 &&
  text.length <= 4000 && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f\uD800-\uDFFF]/u.test(text);
const clone = (value) => structuredClone(value);

export function createVoiceController({ conversation, schedule = setTimeout,
  unschedule = clearTimeout, delayMs = 600, clock = () => performance.now() } = {}) {
  if (!conversation?.getSnapshot || !conversation?.subscribe || !conversation?.submit) {
    throw new Error("Fixture conversation controller required");
  }
  const identity = conversation.getSnapshot();
  if (identity.mode !== "fixture" || !identity.principalId || !identity.sessionId) {
    throw new Error("Fixture identity required");
  }
  const defaults = () => ({ mode: "fixture", evidenceMode: "synthetic_fixture", authority: "none",
    principalId: identity.principalId, sessionId: identity.sessionId, consent: false,
    status: "idle", scenario: "completed", transcript: "", revision: 0, finalText: "",
    notice: "Ensaio local: sem microfone, STT, TTS ou voz clonada.", events: [] });
  let state = defaults();
  let generation = 0;
  let timer = null;
  let deadline = 0;
  let pending = null;
  let disposed = false;
  const listeners = new Set();
  const snapshot = () => clone({ ...state, generation });
  const emit = () => { for (const listener of listeners) listener(snapshot()); };
  const record = (name) => { state.events.push({ name, evidenceMode: "synthetic_fixture", authority: "none" });
    state.events = state.events.slice(-64); };
  const stop = () => { generation += 1; if (timer !== null) unschedule(timer); timer = null; };
  const sameIdentity = (value) => value.mode === "fixture" &&
    value.principalId === state.principalId && value.sessionId === state.sessionId;
  const clearContent = () => { state.transcript = ""; state.finalText = ""; state.revision = 0; };
  function cancel(notice = "Ensaio cancelado; texto e resposta de voz descartados.") {
    if (disposed) return false;
    const owned = pending;
    pending = null; stop(); clearContent();
    state.status = "cancelled"; state.notice = notice; record("voice_fixture_cancelled");
    if (owned && conversation.getSnapshot().requestStatus === "loading") conversation.cancel();
    emit(); return true;
  }
  let previousMessageCount = identity.messages.length;
  const unsubscribeConversation = conversation.subscribe((chat) => {
    if (disposed) return;
    const reset = chat.requestStatus === "idle" && chat.messages.length < previousMessageCount;
    previousMessageCount = chat.messages.length;
    if ((!sameIdentity(chat) || reset) && (state.consent || state.transcript || state.finalText)) {
      state.consent = false;
      cancel("Sessão reiniciada ou divergente; conceda nova permissão para o ensaio."); return;
    }
    if (!pending) return;
    const owned = pending;
    if (!sameIdentity(chat) || clock() > deadline ||
        chat.messages.length < owned.messageCount ||
        chat.messages[owned.messageCount - 1]?.role !== "user" ||
        chat.messages[owned.messageCount - 1]?.text !== owned.text) {
      cancel("Pedido de voz descartado: vínculo, prazo ou sessão divergente."); return;
    }
    if (chat.requestStatus === "loading") return;
    pending = null;
    const final = chat.messages.at(-1);
    if (chat.requestStatus === "completed" && chat.messages.length === owned.messageCount + 1 &&
        final?.role === "assistant" && final.status === "completed" && validText(final.text)) {
      state.finalText = final.text; state.status = "completed";
      state.notice = "Resposta final simulada disponível como texto. Não veio do Core nem de um modelo.";
      record("voice_fixture_final_ready");
    } else {
      state.finalText = ""; state.status = ["error", "incomplete", "empty"].includes(chat.requestStatus)
        ? chat.requestStatus : "cancelled";
      state.notice = "Sem resposta final simulada confirmada; reprodução indisponível.";
      record("voice_fixture_final_unavailable");
    }
    emit();
  });
  const api = {
    getSnapshot: snapshot,
    subscribe(listener) {
      if (disposed) return () => {};
      listeners.add(listener); listener(snapshot()); return () => listeners.delete(listener);
    },
    setConsent(value) {
      if (disposed || typeof value !== "boolean") return false;
      if (!value) cancel("Permissão do ensaio revogada; conteúdo descartado, sem acesso ao microfone.");
      state.consent = value; record(value ? "voice_fixture_consent_granted" : "voice_fixture_consent_revoked");
      emit(); return true;
    },
    setScenario(value) {
      if (disposed || !scenarios.has(value) || ["capturing", "sending", "playing"].includes(state.status)) return false;
      state.scenario = value; emit(); return true;
    },
    startCapture() {
      if (disposed || !state.consent || ["capturing", "sending", "playing"].includes(state.status) ||
          !sameIdentity(conversation.getSnapshot()) || conversation.getSnapshot().requestStatus === "loading") return false;
      stop(); clearContent(); deadline = clock() + 30000;
      const ticket = generation;
      const scenario = state.scenario;
      state.status = "capturing"; state.notice = "Captura e transcrição SIMULADAS; nenhum microfone aberto.";
      record("voice_fixture_capture_started"); emit();
      timer = schedule(() => {
        if (disposed || ticket !== generation) return;
        timer = null;
        if (!state.consent || clock() > deadline || !sameIdentity(conversation.getSnapshot())) {
          cancel("Ensaio expirou ou perdeu o vínculo da sessão; conteúdo descartado."); return;
        }
        if (scenario === "completed") {
          state.transcript = "JARVIS, ajude-me a organizar o próximo passo.";
          state.revision = 1; state.status = "review";
          state.notice = "Texto de fixture pronto. Revise antes de confirmar este texto exato; não autoriza ações.";
        } else {
          state.status = scenario;
          state.notice = "Transcrição simulada falhou, ficou incompleta ou vazia. Nada foi enviado.";
        }
        record("voice_fixture_transcription_finished"); emit();
      }, delayMs);
      return true;
    },
    revise(text) {
      if (disposed || state.status !== "review" || typeof text !== "string") return false;
      if (text.length > 4000) return false;
      state.transcript = text; state.revision += 1; record("voice_fixture_transcript_revised"); emit(); return true;
    },
    confirm({ generation: ticket, revision, text, principalId, sessionId } = {}) {
      if (disposed || state.status !== "review" || !state.consent) return false;
      if (ticket !== generation || revision !== state.revision || text !== state.transcript ||
          principalId !== state.principalId || sessionId !== state.sessionId ||
          !sameIdentity(conversation.getSnapshot()) || clock() > deadline || !validText(text)) {
        state.notice = "Confirmação recusada: revise texto, revisão, sessão e prazo. Nada foi enviado.";
        record("voice_fixture_confirmation_rejected"); emit(); return false;
      }
      pending = { text, messageCount: conversation.getSnapshot().messages.length + 1 };
      state.status = "sending"; state.notice = "Enviando texto revisado à conversa SIMULADA, sem autoridade.";
      record("voice_fixture_text_confirmed");
      if (!conversation.submit(text, { principalId, sessionId, exactText: true })) {
        pending = null; state.status = "review";
        state.notice = "Conversa ocupada ou indisponível; texto preservado para revisão.";
        emit(); return false;
      }
      emit(); return true;
    },
    play() {
      if (disposed || !state.consent || state.status !== "completed" || !validText(state.finalText) ||
          !sameIdentity(conversation.getSnapshot()) || clock() > deadline) return false;
      stop(); const ticket = generation;
      state.status = "playing"; state.notice = "Reprodução SIMULADA. Nenhum áudio é gerado ou tocado.";
      record("voice_fixture_playback_started"); emit();
      timer = schedule(() => {
        if (disposed || ticket !== generation) return;
        timer = null;
        if (!state.consent || !sameIdentity(conversation.getSnapshot()) || clock() > deadline) {
          cancel("Reprodução simulada descartada por prazo ou vínculo da sessão."); return;
        }
        state.status = "completed"; state.notice = "Reprodução simulada concluída; alternativa textual preservada.";
        record("voice_fixture_playback_finished"); emit();
      }, delayMs * 3);
      return true;
    },
    interruptPlayback() {
      if (disposed || state.status !== "playing") return false;
      stop(); state.status = "completed";
      state.notice = "Reprodução simulada interrompida; texto preservado.";
      record("voice_fixture_playback_interrupted"); emit(); return true;
    },
    cancel,
    reset() {
      if (disposed) return false;
      cancel(); state = defaults(); record("voice_fixture_reset"); emit(); return true;
    },
    dispose() {
      if (disposed) return;
      cancel(); disposed = true; unsubscribeConversation(); listeners.clear();
    },
  };
  return api;
}

export function handleVoicePageHide(controller, { persisted = false } = {}) {
  // A restored page needs fresh explicit consent; no stale review or playback survives.
  if (persisted) controller.reset();
  else controller.dispose();
}
