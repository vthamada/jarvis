import { createController, handlePageHide } from "./controller.mjs";
import { createVoiceController, handleVoicePageHide } from "./voice-controller.mjs";
import { createParticleSphere } from "./particle-sphere.mjs";
import { createLocalVoicePlayback } from "./local-voice-playback.mjs";
import { createTranscriptReview, handleTranscriptPageHide } from "./transcript-review.mjs";
import { createConversationPackController, renderConversationPack,
  CONVERSATION_PACK_ORIGIN_LABEL } from "./conversation-pack.mjs";

const controller = createController();
const voice = createVoiceController({ conversation: controller });
const byId = (id) => document.getElementById(id);
let conversationPackConsent = false;
function renderCanonicalConversation(state) {
  renderConversationPack(state, { status: byId("conversation-pack-notice"),
    query: byId("conversation-pack-query"), response: byId("conversation-pack-response"),
    metadata: byId("conversation-pack-metadata") });
  if (state.errorCode === "conversation_pack_context_mismatch") {
    byId("conversation-pack-notice").textContent =
      CONVERSATION_PACK_ORIGIN_LABEL +
      " · Sujeito ou sessão diferentes: pacote recusado, conteúdo anterior removido. Descarte antes de trocar de contexto.";
  }
  byId("conversation-pack-consent").checked = conversationPackConsent;
  byId("conversation-pack-file").disabled = !conversationPackConsent;
  byId("conversation-pack-clear").disabled = !conversationPackConsent && state.status === "empty";
  byId("conversation-pack-content").hidden = state.status !== "ready";
  byId("conversation-pack-turn").hidden = state.pack?.content_included !== true;
  byId("conversation-pack-panel").setAttribute("aria-busy", String(state.status === "loading"));
}
const conversationPack = createConversationPackController({ onState: renderCanonicalConversation });
renderCanonicalConversation(conversationPack.getState());
function discardConversationPack() {
  conversationPackConsent = false;
  byId("conversation-pack-file").value = "";
  conversationPack.clear();
}
byId("conversation-pack-consent").addEventListener("change", (event) => {
  conversationPackConsent = event.target.checked === true;
  byId("conversation-pack-file").value = "";
  // Consent changes invalidate pending reads and clear the adopted offline context.
  conversationPack.clear();
});
byId("conversation-pack-file").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!conversationPackConsent) { conversationPack.clear(); return; }
  if (!file) return;
  await conversationPack.importFile(file);
});
byId("conversation-pack-clear").addEventListener("click", () => {
  discardConversationPack(); byId("conversation-pack-consent").focus();
});
const transcript = createTranscriptReview();
let transcriptPackage = "";
let transcriptDraftInvalid = false;
function transcriptView() {
  try { return transcript.getReview(); } catch { return null; }
}
function renderTranscript(state) {
  const view = transcriptView(), status = state.state;
  if (status !== "exported") transcriptPackage = "";
  if (status !== "reviewed") transcriptDraftInvalid = false;
  const notices = { idle: "Nenhum arquivo importado.", loading: "Validando transcrição local…",
    reviewed: "Revise o texto. Preparar pacote não envia ao Core.", exporting: "Preparando pacote local…",
    exported: "Pacote preparado. Copiar não envia; o console exige novo consentimento explícito.",
    revoked: "Permissão revogada; dados locais descartados.", cancelled: "Revisão descartada.",
    expired: "Prazo de revisão encerrado. Importe novamente e revise.",
    error: "Transcrição recusada. Verifique o formato e os limites; nenhum texto foi enviado.",
    disposed: "Revisão encerrada." };
  byId("transcript-consent").checked = state.review_consent;
  byId("transcript-file").disabled = !state.review_consent || status === "exporting";
  byId("transcript-notice").textContent = notices[status] || "Revisão local indisponível.";
  if (transcriptDraftInvalid) {
    byId("transcript-notice").textContent = "Texto recusado; corrija antes de preparar o pacote.";
  }
  byId("transcript-state").textContent = `Estado: ${status} · origem não verificada · authority=none`;
  byId("transcript-form").hidden = !view;
  if (view) {
    // Textareas normalize CR/CRLF for display. Preserve the controller's exact
    // source until a real input event explicitly creates an edited revision.
    const visible = view.text.replace(/\r\n?/gu, "\n");
    if (!transcriptDraftInvalid && byId("transcript-text").value !== visible) {
      byId("transcript-text").value = view.text;
    }
    byId("transcript-revision").textContent = `Revisão ${view.revision} · até 120 s · quebras originais preservadas se não editar`;
  } else { byId("transcript-text").value = ""; byId("transcript-revision").textContent = ""; }
  byId("transcript-export").disabled = !view || status !== "reviewed" || transcriptDraftInvalid;
  byId("transcript-text").disabled = status !== "reviewed";
  byId("transcript-cancel").disabled = ["idle", "cancelled", "revoked", "disposed"].includes(status);
  byId("transcript-output").hidden = !transcriptPackage;
  byId("transcript-package").value = transcriptPackage;
  byId("transcript-panel").setAttribute("aria-busy", String(["loading", "exporting"].includes(status)));
}
transcript.subscribe(renderTranscript);
let transcriptTimer = window.setInterval(() => renderTranscript(transcript.getSnapshot()), 1000);
window.addEventListener("pageshow", () => {
  if (transcriptTimer === null) {
    transcriptTimer = window.setInterval(() => renderTranscript(transcript.getSnapshot()), 1000);
  }
});
byId("transcript-consent").addEventListener("change", (event) => {
  transcriptPackage = ""; transcriptDraftInvalid = false; byId("transcript-file").value = "";
  transcript.setConsent(event.target.checked);
});
byId("transcript-file").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  // Native picker cancellation preserves the current review/package. Clear the
  // selected name before async I/O, never an unrelated later file selection.
  event.target.value = "";
  if (!file) return;
  transcriptPackage = ""; transcriptDraftInvalid = false;
  try { await transcript.importFile(file); } catch { renderTranscript(transcript.getSnapshot()); }
});
byId("transcript-text").addEventListener("input", (event) => {
  transcriptDraftInvalid = false;
  try { transcript.revise(event.target.value); }
  catch { transcriptDraftInvalid = true; renderTranscript(transcript.getSnapshot()); }
});
byId("transcript-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (transcriptDraftInvalid) return;
  const view = transcriptView();
  if (!view || byId("transcript-text").value !== view.text.replace(/\r\n?/gu, "\n")) return;
  try {
    const result = await transcript.exportPackage({ generation: view.generation,
      revision: view.revision, text: view.text });
    const completed = transcript.getSnapshot();
    if (typeof result !== "string" || completed.state !== "exported" ||
        completed.generation !== view.generation + 1) return;
    transcriptPackage = result; renderTranscript(transcript.getSnapshot());
    byId("transcript-select").focus();
  } catch { renderTranscript(transcript.getSnapshot()); }
});
byId("transcript-cancel").addEventListener("click", () => {
  transcriptPackage = ""; transcript.cancel(); byId("transcript-file").value = "";
  byId("transcript-consent").focus();
});
byId("transcript-select").addEventListener("click", () => {
  byId("transcript-package").focus(); byId("transcript-package").select();
});
// Examples only prepare text. They never submit or acquire authority.
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    byId("message").value = button.dataset.prompt;
    byId("message").focus();
  });
});
function syncNavigation() {
  const target = window.location.hash || "#conversation";
  document.querySelectorAll(".nav-item").forEach((link) => {
    const current = link.getAttribute("href") === target;
    link.classList.toggle("selected", current);
    if (current) link.setAttribute("aria-current", "location");
    else link.removeAttribute("aria-current");
  });
  if (target === "#voice-panel") byId("voice-panel").open = true;
}
document.querySelectorAll(".nav-item").forEach((link) => {
  link.addEventListener("click", () => {
    if (link.getAttribute("href") === "#voice-panel") byId("voice-panel").open = true;
  });
});
window.addEventListener("hashchange", syncNavigation);
syncNavigation();
let presence = null, motionPaused = false;
const localPlayback = createLocalVoicePlayback({ onState: renderLocalPlayback });
presence = createParticleSphere(byId("particle-sphere"), { getLevel: () => localPlayback.getLevel() });
function updatePresence() {
  const local = localPlayback.getStatus(), simulated = voice.getSnapshot().status;
  let mode = "idle", label = "Em repouso · visual local";
  if (local === "playing") { mode = "speaking_local"; label = "Reproduzindo WAV local · amplitude real"; }
  else if (simulated === "playing") { mode = "speaking_fixture"; label = "Simulação de fala · sem áudio real"; }
  else if (simulated === "capturing") { mode = "listening_fixture"; label = "Captura simulada · sem microfone"; }
  else if (controller.getSnapshot().requestStatus === "loading") { mode = "thinking"; label = "Pedido simulado em andamento · sem Core"; }
  if (document.hidden) { mode = "idle"; label = "Em repouso · página inativa"; }
  presence?.setMode(mode); byId("presence-status").textContent = label;
}
function renderLocalPlayback({ status, reason }) {
  const notices = { empty: "Nenhum áudio selecionado.", loading: "Validando WAV local…", ready: "WAV pronto. Clique para reproduzir; arquivo não enviado ou salvo.", starting: "Preparando reprodução local… Você pode interromper.", playing: "Ensaio local em reprodução. Esfera reage à amplitude, não ao conteúdo.", error: "WAV incompatível ou reprodução indisponível. Use PCM16 mono/estéreo, 8–96 kHz, até 600 s / 32 MiB." };
  byId("presence-audio-notice").textContent = notices[status] + (reason ? ` Diagnóstico: ${reason}.` : "");
  byId("presence-play").disabled = status !== "ready";
  byId("presence-stop").disabled = !["playing", "starting", "loading"].includes(status);
  byId("presence-clear").disabled = status === "empty";
  updatePresence();
}
byId("presence-audio-file").addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (file) return localPlayback.selectFile(file);
});
byId("presence-play").addEventListener("click", () => localPlayback.play());
byId("presence-stop").addEventListener("click", () => localPlayback.stop());
byId("presence-clear").addEventListener("click", () => { localPlayback.clear(); byId("presence-audio-file").value = ""; });
byId("presence-motion").addEventListener("click", () => {
  motionPaused = !motionPaused; presence.setMotion(!motionPaused);
  byId("presence-motion").setAttribute("aria-pressed", String(motionPaused));
  byId("presence-motion").textContent = motionPaused ? "Retomar animação" : "Pausar animação";
});
document.addEventListener("visibilitychange", () => { if (document.hidden) localPlayback.stop(); updatePresence(); });
window.addEventListener("pageshow", () => { presence.refresh(); updatePresence(); });
const make = (tag, text = "", className = "") => {
  const element = document.createElement(tag);
  element.textContent = text;
  if (className) element.className = className;
  return element;
};
const inspector = byId("inspector");
let inspectorTrigger = null;
function inspect(title, content, trigger) {
  inspectorTrigger = trigger;
  byId("inspector-title").textContent = title;
  byId("inspector-content").textContent = content;
  inspector.showModal();
}
inspector.addEventListener("close", () => {
  if (inspectorTrigger?.isConnected) inspectorTrigger.focus();
  else byId("message").focus();
});
byId("close-inspector").addEventListener("click", () => inspector.close());

function render(state) {
  updatePresence();
  const active = state.messages.length > 2;
  byId("conversation").dataset.active = String(active);
  byId("conversation-history").open = active;
  byId("conversation-title").textContent = active ? "Vamos ao próximo passo." : "O que vamos fazer hoje?";
  document.querySelector(".suggestions").hidden = active;
  const imported = state.importedSnapshot;
  const messages = byId("messages");
  messages.replaceChildren();
  for (const message of state.messages) {
    const row = make("article", "", `message ${message.role}`);
    row.append(make("div", message.role === "user" ? "OP" : "J", "message-avatar"));
    const body = make("div", "", "message-body");
    body.append(make("p", message.role === "user" ? "Você · exemplo" : "JARVIS · resposta simulada", "message-author"));
    body.append(make("p", message.text, "message-text"));
    if (message.status === "incomplete") body.append(make("span", "INCOMPLETA · NÃO FINAL", "badge"));
    row.append(body); messages.append(row);
  }
  const loading = state.requestStatus === "loading";
  byId("voice-start").disabled = loading || !voice.getSnapshot().consent ||
    ["capturing", "sending", "playing"].includes(voice.getSnapshot().status);
  if (loading) messages.append(make("p", "Preparando demonstração…", "loading-line"));
  byId("notice").textContent = state.notice;
  byId("request-status").textContent = `Estado: ${state.requestStatus} · fixture`;
  byId("submit").disabled = loading;
  byId("cancel").hidden = !loading;
  byId("scenario").disabled = loading;
  byId("snapshot-notice").textContent = state.snapshotNotice || "Nenhum snapshot importado. Origem de arquivos não é verificada.";
  byId("objective-badge").textContent = imported ? "OFFLINE" : "EXEMPLO";
  byId("artifacts-badge").textContent = imported ? "OFFLINE" : "FIXTURE";
  byId("objective-title").textContent = imported ? imported.mission.goal : state.objective.title;
  byId("objective-description").textContent = imported ? `Missão: ${imported.mission.mission_id} · estado declarado: ${imported.mission.status}` : state.objective.description;
  byId("objective-status").textContent = imported ? `Origem não verificada · ${imported.generated_at} · principal declarado: ${imported.principal_ref}. Identidade atual não alterada.` : state.objective.status;
  const steps = imported ? imported.work_items.map((item) => `${item.ref} · ${item.status}`) : state.objective.steps;
  byId("steps").replaceChildren(...steps.map((step) => make("li", step)));
  const activity = imported ? imported.activity.map((entry) => ({ title: entry.name, detail: `Estado declarado: ${entry.status} · snapshot não verificado` })) : state.activity;
  byId("activity-count").textContent = String(activity.length);
  byId("activity-list").replaceChildren(...activity.slice(0, 5).map((entry) => {
    const item = make("li"); item.append(make("p", entry.title), make("small", entry.detail)); return item;
  }));
  const artifacts = imported ? imported.artifacts.map((entry) => ({ title: entry.ref,
    type: `v${entry.version} · ${entry.status} · ${entry.physical_status}`,
    content: `Snapshot local/offline não verificado. Somente metadados; conteúdo do artefato não importado.\n\n${JSON.stringify(entry, null, 2)}` })) : state.artifacts;
  byId("artifact-list").replaceChildren(...artifacts.map((artifact) => {
    const button = make("button", "", "artifact-button");
    button.type = "button";
    button.append(make("span", "▤", "artifact-icon"), make("span", artifact.title), make("small", artifact.type));
    button.addEventListener("click", () => inspect(artifact.title, artifact.content, button));
    return button;
  }));
  byId("approval-list").replaceChildren(...(imported ? [] : state.approvals).map((approval) => {
    const card = make("div", "", "approval-card");
    card.append(make("h3", approval.title), make("p", approval.scope, "muted"), make("code", approval.resource));
    const button = make("button", "Inspecionar proposta", "secondary"); button.type = "button";
    button.addEventListener("click", () => inspect("Proposta de exemplo", JSON.stringify(approval, null, 2), button));
    card.append(button); return card;
  }));
  if (imported) byId("approval-list").append(make("p", "Nenhuma autorização ou challenge foi importado. Este arquivo não concede autoridade.", "footnote"));
}
controller.subscribe(render);
byId("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  if (controller.submit(byId("message").value)) byId("message").value = "";
});
byId("message").addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault(); byId("composer").requestSubmit();
  }
});
byId("cancel").addEventListener("click", () => { controller.cancel(); byId("message").focus(); });
byId("reset").addEventListener("click", () => {
  discardConversationPack();
  transcriptPackage = ""; transcript.reset(); byId("transcript-file").value = "";
  localPlayback.clear(); byId("presence-audio-file").value = "";
  if (inspector.open) inspector.close();
  voice.reset();
  controller.reset(); byId("scenario").value = "completed"; byId("message").value = ""; byId("message").focus();
  byId("snapshot-file").value = "";
});
byId("snapshot-file").addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (file) controller.importSnapshotFile(file);
});
byId("scenario").addEventListener("change", (event) => controller.setScenario(event.target.value));
function renderVoice(state) {
  updatePresence();
  byId("voice-consent").checked = state.consent;
  byId("voice-notice").textContent = state.notice;
  byId("voice-state").textContent = `Estado: ${state.status} · ${state.evidenceMode} · authority=${state.authority}`;
  byId("voice-start").disabled = !state.consent || ["capturing", "sending", "playing"].includes(state.status) ||
    controller.getSnapshot().requestStatus === "loading";
  byId("voice-cancel").disabled = state.status === "idle" || state.status === "cancelled";
  byId("voice-scenario").disabled = ["capturing", "sending", "playing"].includes(state.status);
  byId("voice-scenario").value = state.scenario;
  byId("voice-review").hidden = state.status !== "review";
  if (byId("voice-transcript").value !== state.transcript) byId("voice-transcript").value = state.transcript;
  byId("voice-revision").textContent = `Revisão ${state.revision} · confirmar envia somente este texto à conversa simulada · Ctrl + Enter`;
  byId("voice-confirm").disabled = !state.transcript.trim() || state.status !== "review";
  byId("voice-final").hidden = !state.finalText;
  byId("voice-final-text").textContent = state.finalText;
  byId("voice-play").disabled = state.status !== "completed";
  byId("voice-interrupt").hidden = state.status !== "playing";
  byId("voice-panel").setAttribute("aria-busy", String(["capturing", "sending", "playing"].includes(state.status)));
}
voice.subscribe(renderVoice);
byId("voice-consent").addEventListener("change", (event) => voice.setConsent(event.target.checked));
byId("voice-start").addEventListener("click", () => {
  if (voice.startCapture()) byId("voice-cancel").focus();
});
byId("voice-scenario").addEventListener("change", (event) => voice.setScenario(event.target.value));
byId("voice-transcript").addEventListener("input", (event) => voice.revise(event.target.value));
byId("voice-review").addEventListener("submit", (event) => {
  event.preventDefault();
  const state = voice.getSnapshot();
  if (voice.confirm({ generation: state.generation, revision: state.revision, text: byId("voice-transcript").value,
    principalId: state.principalId, sessionId: state.sessionId })) byId("voice-cancel").focus();
});
byId("voice-transcript").addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault(); byId("voice-review").requestSubmit();
  }
});
byId("voice-cancel").addEventListener("click", () => { voice.cancel(); byId("voice-start").focus(); });
byId("voice-play").addEventListener("click", () => voice.play());
byId("voice-interrupt").addEventListener("click", () => { voice.interruptPlayback(); byId("voice-play").focus(); });
window.addEventListener("pagehide", (event) => {
  discardConversationPack();
  window.clearInterval(transcriptTimer); transcriptTimer = null;
  transcriptPackage = ""; byId("transcript-file").value = "";
  handleTranscriptPageHide(transcript, event);
  localPlayback.clear(); byId("presence-audio-file").value = "";
  if (!event.persisted) { localPlayback.dispose(); presence.dispose(); }
  handleVoicePageHide(voice, event); handlePageHide(controller, event);
});
