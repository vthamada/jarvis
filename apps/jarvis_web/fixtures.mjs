export const FIXTURE_VERSION = "jarvis-cockpit-fixture-v1";

export function createFixture() {
  return {
    version: FIXTURE_VERSION,
    mode: "fixture",
    principalId: "fixture-operator",
    sessionId: "fixture-session-01",
    objective: {
      title: "Construir um JARVIS útil",
      description: "Transformar a fundação em entregas que você pode inspecionar.",
      status: "Demonstração · sem execução",
      steps: ["Preparar uma proposta", "Revisar evidências e limites", "Integrar somente após validação"],
    },
    messages: [
      { role: "user", text: "JARVIS, mostre como vamos acompanhar uma tarefa." },
      { role: "assistant", text: "Aqui você acompanha a conversa, as evidências e as decisões pendentes no mesmo lugar. Este cockpit usa dados de demonstração: nenhuma ferramenta está conectada e nenhuma ação será executada.", status: "completed" },
    ],
    activity: [
      { title: "Contexto preparado", detail: "Fixture local · sem memória canônica", status: "fixture" },
      { title: "Proposta disponível para inspeção", detail: "Sem chamada a modelo ou ferramenta", status: "fixture" },
    ],
    artifacts: [
      { title: "Plano de implementação", type: "Texto de exemplo", content: "EXEMPLO · Nenhum arquivo foi criado.\n\n1. Contratos de cliente e inferência.\n2. Cockpit local com modo explícito.\n3. Propostas de código em ambiente isolado.\n\nA integração real ainda exige os gates do JARVIS." },
    ],
    approvals: [
      { title: "Alteração de artefato local", resource: "fixture://workspace/plan.txt", scope: "Exemplo de proposta de escrita", challenge: "fixture-challenge-01", status: "Somente inspeção" },
    ],
  };
}
