# Fechamento do Primeiro Ciclo Pós-v1

## 1. Objetivo

Este documento registra o fechamento formal do primeiro ciclo do `pós-v1`, cuja
trilha principal foi `continuidade profunda entre missões`.

Ele existe para:

- consolidar a evidência funcional e operacional produzida nas Sprints 1 a 5;
- declarar o corte formal entre `v1.5` e `v2`;
- deixar explícito o que sobe para a próxima fase e o que continua fora do corte;
- permitir que o próximo agente retome o programa sem reinterpretar o ciclo anterior.

---

## 2. O que o ciclo entregou

O primeiro ciclo do `pós-v1` fechou estas capacidades:

- modelo explícito de continuidade entre missão ativa e missão relacionada;
- recuperação e ranking determinístico de continuidade;
- decisão explícita entre `continuar`, `encerrar`, `reformular` e `retomar`;
- snapshot persistente de continuidade da sessão acima da missão atual;
- síntese orientada a continuidade, sem expor o pipeline interno;
- observabilidade da continuidade com trilha mínima, anomalias e comparação entre paths;
- integração da saúde de continuidade com `internal pilot report` e `evolution-lab`.

---

## 3. Evidência consolidada

Artefatos operacionais e técnicos que sustentam o fechamento:

- `tools/run_internal_pilot.py`
- `tools/internal_pilot_report.py`
- `tools/compare_orchestrator_paths.py`
- `tools/evolution_from_pilot.py`
- `tools/close_post_v1_cycle.py`
- `.jarvis_runtime/pilot/`
- `.jarvis_runtime/post_v1_cycle/`

Leitura correta da evidência:

- a continuidade profunda deixou de ser apenas heurística de texto;
- ela passou a existir em memória, planejamento, síntese e observabilidade;
- o sistema já consegue comparar qualidade de continuidade entre fluxos e usar esses sinais
  para decisões `sandbox-only`.

---

## 4. Decisão formal de corte

Decisão do ciclo:

- o primeiro ciclo do `pós-v1` está encerrado;
- o programa sobe para `v1.5`;
- `v1.5` será tratado como o primeiro salto estrutural acima do baseline do `v1`;
- `v2` continua explicitamente fora do corte imediato.

Racional:

- o problema principal do ciclo foi resolvido no recorte certo;
- o próximo salto útil não é especialização ampla;
- o próximo salto útil é transformar continuidade profunda em runtime stateful,
  recuperável e governado.

---

## 5. Entra em v1.5

Itens promovidos para `v1.5`:

1. checkpoint e replay governados da continuidade;
2. pausas `HITL` em conflitos de continuidade;
3. absorção parcial de `LangGraph` no subfluxo de continuidade;
4. evals operacionais da continuidade profunda.

Regra:

- cada item entra como ampliação controlada do núcleo;
- nenhuma promoção reabre o baseline do `v1`;
- o foco continua sendo runtime, continuidade e governança.

---

## 6. Fica para v2

Itens explicitamente fora do corte de `v1.5`:

1. especialistas subordinados maduros por domínio;
2. memória semântica profunda com `pgvector` e retrieval mais rico;
3. `computer use` governado e operação ampla do computador;
4. voz e runtime realtime como superfície oficial;
5. assistência operacional ampla e workflows pessoais.

Racional:

- todos esses itens ampliam superfície, risco ou profundidade estrutural além do salto
  correto para o momento atual.

---

## 7. Definição de pronto do fechamento

O primeiro ciclo do `pós-v1` deve ser considerado formalmente fechado quando:

- o corte entre `v1.5` e `v2` estiver documentado;
- a próxima versão do sprint cycle estiver pronta;
- `HANDOFF.md` e os resumos executivos apontarem para o novo ciclo;
- os artefatos de fechamento puderem ser regenerados via tooling local.

---

## 8. Próximo artefato de execução

O ciclo seguinte passa a ser executado por:

- `docs/implementation/v1-5-sprint-cycle.md`

Este documento permanece como fechamento histórico do primeiro ciclo do `pós-v1`.
