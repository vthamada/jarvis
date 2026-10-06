import { createFixture, FIXTURE_VERSION } from "./fixtures.mjs";
import { readSnapshotFile } from "./snapshot.mjs";

const clone = (value) => structuredClone(value);
const scenarios = new Set(["completed", "error", "incomplete", "empty"]);

// This controller is deliberately not a transport or an authorization service.
export function createController({ fixture = createFixture(), delayMs = 850,
  schedule = setTimeout, unschedule = clearTimeout } = {}) {
  if (fixture.version !== FIXTURE_VERSION || fixture.mode !== "fixture" ||
      !fixture.principalId || !fixture.sessionId) {
    throw new Error("Unsupported fixture identity or version");
  }
  const initial = clone(fixture);
  const snapshotDefaults = () => ({ importedSnapshot: null, snapshotStatus: "idle", snapshotNotice: "" });
  let state = { ...clone(initial), ...snapshotDefaults(), requestStatus: "idle", notice: "", scenario: "completed" };
  let generation = 0;
  let importGeneration = 0;
  let timer = null;
  let disposed = false;
  const listeners = new Set();
  const snapshot = () => clone(state);
  const emit = () => { for (const listener of listeners) listener(snapshot()); };
  const stop = () => { generation += 1; if (timer !== null) unschedule(timer); timer = null; };
  return {
    getSnapshot: snapshot,
    async importSnapshotFile(file) {
      if (disposed) return false;
      const ticket = ++importGeneration;
      state.snapshotStatus = "loading";
      state.snapshotNotice = "Lendo arquivo local, sem transmissão ou verificação de autenticidade…";
      emit();
      try {
        const imported = await readSnapshotFile(file);
        if (disposed || ticket !== importGeneration) return false;
        state.importedSnapshot = imported;
        state.snapshotStatus = "loaded";
        state.snapshotNotice = "Snapshot local/offline de origem não verificada. Não é conexão live nem autenticação. Conversa permanece simulada.";
        emit(); return true;
      } catch {
        if (disposed || ticket !== importGeneration) return false;
        state.snapshotStatus = "error";
        state.snapshotNotice = "Importação recusada: JSON, schema ou limites inválidos. A visão anterior foi preservada.";
        emit(); return false;
      }
    },
    cancelSnapshotImport() {
      if (disposed || state.snapshotStatus !== "loading") return false;
      importGeneration += 1; state.snapshotStatus = "cancelled";
      state.snapshotNotice = "Importação local cancelada; visão anterior preservada.";
      emit(); return true;
    },
    subscribe(listener) {
      if (disposed) return () => {};
      listeners.add(listener); listener(snapshot()); return () => listeners.delete(listener);
    },
    setScenario(scenario) {
      if (disposed) return false;
      if (!scenarios.has(scenario)) throw new Error("Unknown fixture scenario");
      if (state.requestStatus === "loading") return false;
      state.scenario = scenario; emit(); return true;
    },
    submit(text, { principalId = state.principalId, sessionId = state.sessionId, exactText = false } = {}) {
      if (disposed) return false;
      if (principalId !== state.principalId || sessionId !== state.sessionId) {
        state.notice = "Identidade ou sessão divergente. Pedido descartado."; emit(); return false;
      }
      if (state.requestStatus === "loading") return false;
      if (typeof text !== "string" || !text.trim() || text.length > 4000) {
        state.notice = "Escreva de 1 a 4.000 caracteres para simular um pedido."; emit(); return false;
      }
      stop();
      const ticket = generation;
      const scenario = state.scenario;
      state.messages.push({ role: "user", text: exactText === true ? text : text.trim() });
      state.requestStatus = "loading";
      state.notice = "Simulação em andamento. Sem modelo, ferramentas ou efeitos reais.";
      state.activity.unshift({ title: "Pedido de exemplo recebido", detail: "Fixture local · nenhuma chamada externa", status: "fixture" });
      emit();
      timer = schedule(() => {
        if (ticket !== generation || state.requestStatus !== "loading") return;
        timer = null;
        state.requestStatus = scenario;
        if (scenario === "completed") {
          state.messages.push({ role: "assistant", text: "Resposta simulada: eu prepararia uma proposta, reuniria evidências e apresentaria os limites antes de qualquer ação. Não analisei seu pedido com um modelo e não executei ferramentas. A integração com o Core ainda não está ativa neste cockpit.", status: "completed" });
          state.notice = "Demonstração concluída; nenhum resultado real foi produzido.";
        } else if (scenario === "error") {
          state.notice = "Falha simulada de transporte. Nenhuma execução ocorreu. Você pode tentar novamente.";
        } else if (scenario === "incomplete") {
          state.messages.push({ role: "assistant", text: "Trecho simulado recebido antes da interrupção. Não é uma resposta final nem uma entrega confirmada.", status: "incomplete" });
          state.notice = "Resposta incompleta simulada. Não tratar como sucesso.";
        } else {
          state.notice = "Simulação retornou sem conteúdo. Nenhum resultado confirmado.";
        }
        state.activity.unshift({ title: `Simulação: ${scenario}`, detail: "Resultado local de interface; sem receipt de execução", status: scenario });
        emit();
      }, delayMs);
      return true;
    },
    cancel() {
      if (disposed) return false;
      if (state.requestStatus !== "loading") return false;
      stop(); state.requestStatus = "cancelled";
      state.notice = "Simulação cancelada. Nenhum efeito foi executado.";
      state.activity.unshift({ title: "Pedido simulado cancelado", detail: "Callback descartado · sem execução", status: "cancelled" });
      emit(); return true;
    },
    reset() {
      if (disposed) return false;
      importGeneration += 1;
      stop(); state = { ...clone(initial), ...snapshotDefaults(), requestStatus: "idle", notice: "Sessão de demonstração reiniciada; sem persistência.", scenario: "completed" };
      emit();
      return true;
    },
    dispose() {
      if (disposed) return;
      if (state.requestStatus === "loading") {
        state.requestStatus = "cancelled";
        state.notice = "Simulação descartada ao encerrar a página; sem execução.";
      }
      importGeneration += 1;
      disposed = true; stop(); listeners.clear();
    },
  };
}

export function handlePageHide(controller, { persisted = false } = {}) {
  // BFCache preserves the document and its subscribers. Cancel a pending
  // fixture turn, but keep the controller usable when the page returns.
  if (persisted) { controller.cancel(); controller.cancelSnapshotImport(); }
  else controller.dispose();
}
