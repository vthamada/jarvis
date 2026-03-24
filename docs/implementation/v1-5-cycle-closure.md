# Fechamento do Ciclo V1.5

## 1. Objetivo

Este documento registra o fechamento formal do primeiro ciclo do `v1.5`, cuja trilha
principal foi `runtime stateful governado para continuidade profunda`.

Ele existe para:

- consolidar a evidência funcional, observável e comparativa produzida nas Sprints 1 a 5;
- declarar o corte formal entre `v1.5` e `v2`;
- deixar explícito o que sobe para o primeiro ciclo do `v2` e o que continua fora do corte imediato;
- permitir que o próximo agente retome a fase seguinte sem reinterpretar o `v1.5`.

---

## 2. O que o ciclo entregou

O primeiro ciclo do `v1.5` fechou estas capacidades:

- checkpoints explícitos de continuidade por sessão;
- replay e recuperação governada com ponto de retomada rastreável;
- pausas `HITL` persistentes com resolução manual auditável;
- absorção parcial de `LangGraph` em um subfluxo stateful isolado de continuidade;
- evals comparativas entre baseline linear e runtime absorvido;
- integração da saúde do runtime com `internal_pilot_report`, comparação de paths e `evolution-lab`.

---

## 3. Evidência consolidada

Artefatos operacionais e técnicos que sustentam o fechamento:

- `tools/compare_orchestrator_paths.py`
- `tools/internal_pilot_report.py`
- `tools/evolution_from_pilot.py`
- `tools/close_stateful_runtime_cycle.py`
- `.jarvis_runtime/path-comparison/`
- `.jarvis_runtime/v1_5_cycle/`

Leitura correta da evidência:

- a continuidade profunda deixou de ser apenas contexto recuperado e passou a operar como runtime stateful;
- o recorte absorvido de `LangGraph` foi comparado contra o baseline e permaneceu equivalente nos cenários do piloto;
- os sinais do runtime ficaram observáveis o suficiente para orientar o `v2` sem reabrir o baseline do `v1`.

---

## 4. Decisão formal de corte

Decisão do ciclo:

- o primeiro ciclo do `v1.5` está encerrado;
- o programa sobe para `v2`;
- o primeiro ciclo do `v2` será tratado como a abertura disciplinada de especialistas subordinados e memória relacional mais rica;
- superfícies amplas e autonomia agressiva continuam explicitamente fora do corte imediato.

Racional:

- o problema principal do `v1.5` foi resolvido no recorte certo;
- o próximo salto útil não é ampliar interface nem superfície operacional;
- o próximo salto útil é transformar continuidade stateful em base para especialistas subordinados, contexto relacional compartilhado e handoff interno governado.

---

## 5. Entra no primeiro ciclo do v2

Itens promovidos para o primeiro ciclo do `v2`:

1. contratos e runtime inicial de especialistas subordinados;
2. seleção governada de especialistas e handoff interno;
3. memória relacional compartilhada entre núcleo e especialistas;
4. primeiro especialista subordinado em `shadow mode`;
5. evals e governança de convocação de especialistas.

Regra:

- cada item entra como ampliação controlada do núcleo;
- nenhuma promoção reabre o baseline do `v1`;
- o foco passa a ser especialização subordinada, memória relacional e governança de handoff.

---

## 6. Fica fora do corte imediato

Itens explicitamente fora do corte inicial do `v2`:

1. `computer use` amplo e operação extensa do computador;
2. voz e realtime como superfície oficial;
3. memória semântica profunda com `pgvector` como base canônica;
4. assistência operacional ampla e workflows pessoais;
5. autoevolução promotiva e mudança estrutural agressiva.

Racional:

- todos esses itens ampliam superfície, risco ou profundidade estrutural além do salto correto para o momento atual.

---

## 7. Definição de pronto do fechamento

O primeiro ciclo do `v1.5` deve ser considerado formalmente fechado quando:

- o corte entre `v1.5` e `v2` estiver documentado;
- a próxima versão do sprint cycle estiver pronta;
- `HANDOFF.md` e os resumos executivos apontarem para o novo ciclo;
- os artefatos de fechamento puderem ser regenerados via tooling local.

---

## 8. Próximo artefato de execução

O ciclo seguinte passa a ser executado por:

- `docs/implementation/v2-sprint-cycle.md`

Este documento permanece como fechamento histórico do primeiro ciclo do `v1.5`.
