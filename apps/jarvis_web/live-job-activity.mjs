// Manual, read-only projection of selected existing jobs. No transport, storage,
// Core invocation, polling, percentage estimation or action authority lives here.
const states = ["registered", "running", "succeeded", "failed", "needs_decision", "cancelled", "expired"];
const labels = ["Registrados", "Em andamento", "Concluídos", "Falharam", "Aguardando decisão", "Cancelados", "Expirados"];
const activityKeys = ["schema_version", "read_only", "authority", "operator_authenticated", "scope_binding", "source_mode",
  "activity_scope", "selected_job_count", "status_counts", "evidence_counts", "attempts_recorded", "progress"];
const progressKeys = ["basis", "pending_count", "active_count", "awaiting_decision_count", "terminal_count"];
const sessionPattern = /^session:\/\/web-live\/[0-9a-f]{32}$/;
const notices = {
  disconnected: "Pareie esta sessão para consultar a atividade local.",
  idle: "Consulta manual disponível. Nenhuma leitura automática.",
  loading: "Consultando os jobs selecionados…",
  ready: "Resumo de metadados somente leitura; sem execução automática.",
  disposed: "Consulta encerrada.",
  invalid_response: "Resumo recusado: contrato de atividade inválido.",
  unavailable: "Atividade indisponível: perfil local não configurado ou desativado.",
  timeout: "A consulta excedeu o prazo e foi interrompida. Atualize manualmente para tentar novamente.",
  read_failed: "Não foi possível consultar a atividade local. Nenhuma ação foi executada.",
};
class PanelFailure extends Error {
  constructor(code) { super(code); this.code = code; }
}
const refuse = () => { throw new PanelFailure("invalid_response"); };

// Snapshot only plain, exact, own enumerable data fields. Accessors and symbols
// are not data from the JSON wire and must not be consulted or reflected.
function record(value, keys) {
  if (value === null || typeof value !== "object" || Array.isArray(value) ||
    ![Object.prototype, null].includes(Object.getPrototypeOf(value)) || Reflect.ownKeys(value).length !== keys.length) refuse();
  const descriptors = Object.getOwnPropertyDescriptors(value);
  if (keys.some((key) => !Object.hasOwn(descriptors, key) || !descriptors[key].enumerable ||
    !Object.hasOwn(descriptors[key], "value"))) refuse();
  return Object.fromEntries(keys.map((key) => [key, descriptors[key].value]));
}
const count = (value, maximum) => Number.isSafeInteger(value) && value >= 0 && value <= maximum;
const validSession = (value) => typeof value === "string" && value.length === 51 && sessionPattern.test(value);

function validate(value, sessionRef) {
  const envelope = record(value, ["schema_version", "session_ref", "activity"]);
  if (envelope.schema_version !== "jarvis-local-job-activity-v1" || !validSession(envelope.session_ref) ||
    envelope.session_ref !== sessionRef) refuse();
  const activity = record(envelope.activity, activityKeys);
  if (activity.schema_version !== "jarvis-job-activity-v1" || activity.read_only !== true ||
    activity.authority !== "none" || activity.operator_authenticated !== false ||
    activity.scope_binding !== "caller_supplied_not_authentication" ||
    activity.source_mode !== "quiescent_existing_local_sqlite" ||
    activity.activity_scope !== "explicit_selected_jobs_not_full_ledger" ||
    !count(activity.selected_job_count, 32) || activity.selected_job_count < 1) refuse();
  const selected = activity.selected_job_count;
  const counts = record(activity.status_counts, states);
  const evidence = record(activity.evidence_counts, ["fixture", "metadata_ledger"]);
  const progress = record(activity.progress, progressKeys);
  if (Object.values(counts).some((value) => !count(value, selected)) ||
    Object.values(counts).reduce((sum, value) => sum + value, 0) !== selected ||
    Object.values(evidence).some((value) => !count(value, selected)) ||
    evidence.fixture + evidence.metadata_ledger !== selected ||
    !count(activity.attempts_recorded, selected * 10) || activity.attempts_recorded < counts.running ||
    progress.basis !== "selected_ledger_states_not_execution_percentage" ||
    progressKeys.slice(1).some((key) => !count(progress[key], selected)) ||
    progress.pending_count !== counts.registered || progress.active_count !== counts.running ||
    progress.awaiting_decision_count !== counts.needs_decision ||
    progress.terminal_count !== counts.succeeded + counts.failed + counts.cancelled + counts.expired) refuse();
  return { ...activity, status_counts: counts, evidence_counts: evidence, progress };
}
function summary(activity) {
  return [
    `${activity.selected_job_count} jobs selecionados pelo host; não representa o ledger completo.`,
    ...states.map((key, index) => `${labels[index]}: ${activity.status_counts[key]}`),
    `Pendentes: ${activity.progress.pending_count} · Ativos: ${activity.progress.active_count} · ` +
      `Aguardando decisão: ${activity.progress.awaiting_decision_count} · Terminais: ${activity.progress.terminal_count}`,
    `Tentativas registradas: ${activity.attempts_recorded}`,
    `Fixture: ${activity.evidence_counts.fixture} (dados de teste) · Metadados do ledger: ${activity.evidence_counts.metadata_ledger}`,
    "Progresso por estados registrados; não é percentual de execução nem confirmação de efeito externo.",
    "O scope foi informado pelo host e não autentica o operador nem concede autoridade. Sem reconciliação de leases ou execução automática.",
  ].join("\n");
}
function readError(error) {
  if (error instanceof PanelFailure) return error.code;
  try {
    if (["job_activity_unavailable", "job_activity_disabled", "disabled"].includes(error?.message)) return "unavailable";
  } catch { /* Never reflect arbitrary source exceptions or error accessors. */ }
  return "read_failed";
}

/** read({signal}) is injected by the paired local controller, which owns CSRF. */
export function createJobActivityPanel({ document, read, timeoutMs = 10000 }) {
  if (typeof read !== "function" || !Number.isSafeInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 60000)
    throw new TypeError("invalid_job_activity_options");
  const button = document?.getElementById("live-job-refresh");
  const statusNode = document?.getElementById("live-job-status");
  const summaryNode = document?.getElementById("live-job-summary");
  if (!button || !statusNode || !summaryNode) throw new TypeError("missing_job_activity_elements");
  let sessionRef = null, generation = 0, current = null, disposed = false;
  let state = Object.freeze({ status: "disconnected", sessionRef: null, errorCode: null });
  const getState = () => state;
  function render(status, errorCode = null, content = "") {
    state = Object.freeze({ status, sessionRef, errorCode });
    button.disabled = disposed || !sessionRef || status === "loading";
    statusNode.textContent = notices[errorCode ?? status];
    summaryNode.textContent = content;
  }
  function invalidate() {
    generation++;
    const operation = current;
    current = null;
    if (operation) {
      clearTimeout(operation.timer);
      operation.controller.abort();
      operation.reject(new PanelFailure("cancelled"));
    }
  }
  function setSession(value) {
    if (disposed) return getState();
    const next = validSession(value) ? value : null;
    if (next === sessionRef) return getState();
    invalidate(); sessionRef = next; render(next ? "idle" : "disconnected");
    return getState();
  }
  async function refresh() {
    if (disposed || !sessionRef) return getState();
    // Repeated explicit requests supersede, rather than accumulate or race.
    invalidate();
    const token = generation, binding = sessionRef, controller = new AbortController();
    let reject;
    const cancellation = new Promise((_resolve, no) => { reject = no; });
    const operation = { controller, reject, timer: null };
    current = operation; render("loading");
    operation.timer = setTimeout(() => {
      if (current !== operation) return;
      controller.abort(); reject(new PanelFailure("timeout"));
    }, timeoutMs);
    try {
      const value = await Promise.race([Promise.resolve().then(() => {
        if (controller.signal.aborted) throw new PanelFailure("cancelled");
        return read({ signal: controller.signal });
      }), cancellation]);
      if (disposed || token !== generation || binding !== sessionRef || current !== operation) return getState();
      let activity;
      try { activity = validate(value, binding); } catch { refuse(); }
      if (disposed || token !== generation || binding !== sessionRef || current !== operation) return getState();
      render("ready", null, summary(activity));
    } catch (error) {
      if (!disposed && token === generation && binding === sessionRef && current === operation)
        render("error", readError(error));
    } finally {
      clearTimeout(operation.timer);
      if (current === operation) current = null;
    }
    return getState();
  }
  const onClick = (event) => { event.preventDefault(); return refresh(); };
  function dispose() {
    if (disposed) return;
    disposed = true; invalidate(); sessionRef = null;
    button.removeEventListener("click", onClick); render("disposed");
  }
  button.addEventListener("click", onClick); render("disconnected");
  return Object.freeze({ setSession, refresh, dispose, getState });
}
