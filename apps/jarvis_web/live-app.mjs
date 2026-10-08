import { createLiveController, LIVE_SESSION_LABEL } from "./live-controller.mjs";
import { projectGenerativeResult } from "./live-generative-projection.mjs";

const node = (id) => document.getElementById(id);
let projectionEpoch = 0, projectionContext = null;
let lastPaired = false, canonicalChoice = null, pairingFocusIntent = null;
const sameResult = (left, right) => left && right && Object.keys(left).length === Object.keys(right).length &&
  Object.keys(left).every((field) => left[field] === right[field]);
function setDisclosure(id, summaryId, open, preferredFocusId = summaryId) {
  const details = node(id), summary = node(summaryId), active = document.activeElement;
  if (!open && details.open && active && active !== summary && details.contains?.(active)) {
    const preferred = node(preferredFocusId);
    (preferred.disabled ? summary : preferred).focus({ preventScroll: true });
  }
  details.open = open;
}
function choiceMatches(state) {
  return canonicalChoice && canonicalChoice.session === state.sessionRef && canonicalChoice.ticket === state.ticket &&
    sameResult(canonicalChoice.result, state.result);
}
function bindCanonicalChoice(state) {
  if (!state.result) {
    if (!state.sessionRef || (canonicalChoice && canonicalChoice.session !== state.sessionRef)) canonicalChoice = null;
    return;
  }
  if (!choiceMatches(state)) canonicalChoice = { session: state.sessionRef, ticket: state.ticket,
    result: Object.freeze({ ...state.result }), manualOpen: null };
  // Accepted alone is insufficient: a prior manual closure is restored only after the current parser validates.
  if (state.result.generative_status !== "accepted" && canonicalChoice.manualOpen !== null) {
    setDisclosure("live-canonical-details", "live-canonical-summary", canonicalChoice.manualOpen);
  }
}
function clearProjection() {
  projectionEpoch++; projectionContext = null;
  node("live-projection").hidden = true;
  for (const id of ["live-projection-origin", "live-projection-analysis", "live-projection-assumptions",
    "live-projection-limitations", "live-projection-citations"]) node(id).textContent = "";
  node("live-canonical-details").open = true; // Full canonical fallback while any optional projection is pending/refused.
}
function scheduleProjection(state) {
  if (state.status !== "completed" || !state.sessionRef || !state.ticket ||
    state.result?.generative_status !== "accepted" || state.result.governance_decision !== "allow") return;
  const snapshot = Object.freeze({ ...state.result });
  const context = { epoch: projectionEpoch, session: state.sessionRef, ticket: state.ticket,
    query: snapshot.query, final: snapshot.response_text, result: snapshot };
  projectionContext = context;
  const current = () => {
    if (projectionContext !== context || projectionEpoch !== context.epoch) return false;
    const latest = controller.getState();
    return latest.status === "completed" && latest.sessionRef === context.session && latest.ticket === context.ticket &&
      latest.result?.query === context.query && latest.result.response_text === context.final &&
      Object.keys(snapshot).length === Object.keys(latest.result).length &&
      Object.keys(snapshot).every((field) => latest.result[field] === snapshot[field]);
  };
  void Promise.resolve().then(() => current() ? projectGenerativeResult(snapshot) : null).then((projection) => {
    if (!current()) return;
    if (!projection) { node("live-canonical-details").open = true; return; }
    node("live-projection-origin").textContent = projection.evidenceMode === "injected_transport" ?
      "Transporte injetado de teste; não comprova modelo real, qualidade ou verdade." :
      "Transporte live declarado; não comprova qualidade, verdade ou origem autenticada.";
    node("live-projection-analysis").textContent = projection.analysis;
    node("live-projection-assumptions").textContent = projection.assumptions.length ?
      projection.assumptions.map((value) => "• " + value).join("\n\n") : "Nenhuma premissa declarada pelo complemento.";
    node("live-projection-limitations").textContent = projection.limitations.length ?
      projection.limitations.map((value) => "• " + value).join("\n\n") : "Nenhuma limitação declarada pelo complemento; isso não comprova ausência de limites.";
    node("live-projection-citations").textContent = projection.citations.length ? projection.citations.map((citation) =>
      `${citation.sourceRef} · caracteres ${citation.start} a ${citation.end} (fim exclusivo)\n${citation.quote}`).join("\n\n") :
      "Nenhuma citação declarada. Citações são trechos exatos da pergunta, não fatos verificados.";
    node("live-projection").hidden = false;
    if (choiceMatches(controller.getState())) {
      setDisclosure("live-canonical-details", "live-canonical-summary", canonicalChoice.manualOpen ?? false);
    }
  }).catch(() => { if (current()) clearProjection(); }); // Optional view failure must not erase the canonical final.
}
const messages = {
  invalid_response: "Resposta incompatível recusada. O conteúdo anterior foi removido.",
  network_error: "A conexão falhou. Não houve reenvio automático. Consulte o mesmo ticket, se disponível.",
  session_expired: "A sessão local expirou. Pareie novamente.",
  foreign_session: "A sessão mudou. Conteúdo e contexto anteriores foram descartados.",
  invalid_query: "Revise o pedido: entre 1 e 4.000 caracteres, sem caracteres de controle.",
  invalid_secret: "O segredo deve conter exatamente 64 caracteres hexadecimais minúsculos.",
  not_paired: "Pareie uma sessão local antes de enviar o pedido.",
  wait_stopped: "A espera foi interrompida somente no browser. O Core pode continuar; consulte o mesmo ticket.",
  wait_timeout: "O limite de espera foi atingido. O Core pode continuar; consulte o mesmo ticket.",
  analysis_invalid: "Pedido inválido recusado pelo servidor.",
  analysis_busy: "O Core está ocupado. Nenhum pedido foi reenviado automaticamente.",
  analysis_ticket_refused: "O servidor recusou este ticket.",
  analysis_closed: "A análise local está indisponível.",
  analysis_outcome_unknown: "O resultado não pôde ser confirmado. Pode haver registro canônico. Não reenvie automaticamente.",
  analysis_expired: "Este ticket expirou no servidor. Nenhum pedido foi reenviado.",
  session_refused: "Sessão local ausente ou expirada. Pareie novamente.",
  csrf_refused: "A sessão não pôde ser validada. Pareie novamente.",
  pairing_refused: "Segredo recusado, expirado ou já utilizado.",
  pairing_rate_limited: "Muitas tentativas de pareamento. Aguarde antes de tentar novamente.",
  pairing_unavailable: "O pareamento não está disponível nesta sessão do servidor.",
  auth_unavailable: "Autenticação local indisponível.",
  consent_required: "Autorize explicitamente o complemento para esta pergunta antes do envio.",
  generative_unavailable: "O complemento generativo não está habilitado neste host. Nenhum pedido foi reenviado.",
};
function render(state) {
  clearProjection();
  const paired = state.sessionRef !== null;
  const busy = ["connecting", "submitting", "waiting"].includes(state.status);
  if (["foreign_session", "session_expired", "session_refused", "csrf_refused"].includes(state.errorCode)) {
    node("live-query").value = ""; node("live-secret").value = "";
  }
  node("live-session").textContent = paired ? LIVE_SESSION_LABEL : "Não pareado · sessão local";
  node("live-secret").disabled = paired || busy;
  node("live-pair").disabled = paired || busy;
  node("live-refresh").disabled = busy;
  node("live-disconnect").disabled = !paired;
  node("live-query").disabled = !paired || busy;
  node("live-generative-consent").disabled = !paired || busy;
  node("live-generative-consent").checked = false;
  node("live-send").disabled = !paired || busy;
  node("live-stop").disabled = !busy;
  node("live-recover").disabled = !paired || !state.ticket || busy;
  node("live-form").setAttribute("aria-busy", String(busy));
  node("live-notice").textContent = state.errorCode ? (messages[state.errorCode] ?? "Solicitação recusada. Nenhum reenvio automático.") :
    ({ disconnected: "Pareie a sessão local para começar.", connecting: "Verificando sessão local…",
      ready: state.ticket ? "Sessão recuperada. Consulte explicitamente o resultado do último ticket." : "Core local conectado. Pronto para um pedido.",
      submitting: "Enviando um pedido ao Core…", waiting: "Aguardando a síntese final canônica…",
      completed: "Resposta final recebida da memória canônica do Core.", failed: "A análise não retornou um resultado confirmado.",
      stopped: "A espera foi interrompida. Consulte o mesmo ticket." }[state.status] ?? "Sessão indisponível.");
  node("live-ticket").textContent = state.ticket ? "Ticket: " + state.ticket : "";
  const active = document.activeElement;
  if (!state.result && active && node("live-result").contains?.(active)) {
    node(busy ? "live-stop" : paired ? "live-query" : "live-pairing-summary").focus({ preventScroll: true });
  }
  node("live-result").hidden = !state.result;
  node("live-result-query").textContent = state.result?.query ?? "";
  node("live-final").textContent = state.result?.response_text ?? "";
  node("live-governance").textContent = state.result ?
    ({ allow: "ALLOW · resposta permitida", block: "BLOCK · bloqueado", defer_for_validation: "DEFER · requer validação" }[state.result.governance_decision]) : "";
  let generativeLabel = "modelo generativo desativado";
  if (state.result?.generative_status === "accepted") {
    generativeLabel = "complemento não verificado · " + (state.result.generative_evidence_mode === "injected_transport" ?
      "transporte injetado de teste; não comprova modelo real" : "transporte live; não comprova qualidade ou verdade");
  } else if (["rejected", "withheld"].includes(state.result?.generative_status)) {
    generativeLabel = (state.result.generative_status === "withheld" ? "complemento retido" : "complemento recusado") +
      ` · ${state.result.generative_error_code} · final nativa preservada`;
  }
  node("live-metadata").textContent = state.result ?
    `Core local · ${generativeLabel} · ${state.result.memory_record_ref} · ${state.result.timestamp} · nenhuma autoridade para ações` : "";
  node("live-shell").dataset.paired = String(paired);
  if (paired !== lastPaired) {
    setDisclosure("live-pairing-details", "live-pairing-summary", !paired, "live-query");
    if (paired && pairingFocusIntent && (!document.activeElement || document.activeElement === document.body ||
      document.activeElement === pairingFocusIntent)) node("live-query").focus({ preventScroll: true });
    lastPaired = paired;
  }
  if (state.status !== "connecting") pairingFocusIntent = null;
  bindCanonicalChoice(state);
  scheduleProjection(state);
}
const controller = createLiveController({ onState: render });
render(controller.getState());
function rememberCanonicalIntent(event) {
  if (event.type === "keydown" && !["Enter", " ", "Spacebar"].includes(event.key)) return;
  if (choiceMatches(controller.getState())) canonicalChoice.manualOpen = !node("live-canonical-details").open;
}
node("live-canonical-summary").addEventListener("click", rememberCanonicalIntent);
node("live-canonical-summary").addEventListener("keydown", rememberCanonicalIntent);
document.addEventListener?.("focusin", (event) => {
  if (pairingFocusIntent && event.target !== pairingFocusIntent && event.target !== document.body) pairingFocusIntent = null;
});
document.addEventListener?.("pointerdown", (event) => {
  if (pairingFocusIntent && !node("live-pairing-details").contains?.(event.target)) pairingFocusIntent = null;
});
node("live-pair-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const secret = node("live-secret").value;
  const active = document.activeElement;
  pairingFocusIntent = active && active !== node("live-pairing-summary") &&
    node("live-pairing-details").contains?.(active) ? active : null;
  node("live-secret").value = ""; await controller.pair(secret); pairingFocusIntent = null;
});
node("live-form").addEventListener("submit", async (event) => {
  event.preventDefault(); canonicalChoice = null; clearProjection(); const consent = node("live-generative-consent").checked === true;
  node("live-generative-consent").checked = false;
  if (consent) await controller.submitGenerative(node("live-query").value, { consent: true });
  else await controller.submit(node("live-query").value);
});
node("live-refresh").addEventListener("click", () => controller.initialize());
node("live-recover").addEventListener("click", () => controller.recover());
node("live-stop").addEventListener("click", () => controller.stopWaiting());
node("live-disconnect").addEventListener("click", () => {
  pairingFocusIntent = null; canonicalChoice = null; clearProjection();
  node("live-secret").value = ""; node("live-query").value = ""; node("live-generative-consent").checked = false;
  return controller.disconnect();
});
for (const button of document.querySelectorAll("[data-prompt]")) {
  button.addEventListener("click", () => {
    if (node("live-query").disabled) return;
    node("live-query").value = button.dataset.prompt; node("live-query").focus();
  });
}
window.addEventListener("pagehide", () => {
  pairingFocusIntent = null; canonicalChoice = null; clearProjection();
  node("live-secret").value = ""; node("live-query").value = ""; node("live-generative-consent").checked = false; controller.pageHide();
});
window.addEventListener("pageshow", (event) => { if (event.persisted === true) controller.initialize(); });
void controller.initialize();
