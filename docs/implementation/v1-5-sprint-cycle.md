# V1.5 Sprint Cycle

## 1. Objetivo do ciclo atual

Este documento define o ciclo rolante oficial do `v1.5`.

Foco único do ciclo:

- `runtime stateful governado para continuidade profunda`

Ele sucede o primeiro ciclo do `pós-v1` e transforma continuidade profunda em um salto
estrutural acima do baseline do `v1`, sem antecipar especialização ampla de `v2`.

Fontes de direção:

- `HANDOFF.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/implementation/post-v1-cycle-closure.md`
- `docs/architecture/technology-study.md`

Status desta versão do ciclo:

- Sprint 1 concluída;
- Sprint 2 concluída;
- Sprint 3 concluída;
- Sprint 4 concluída;
- Sprint 5 concluída;
- Sprint 6 concluída;
- este ciclo está formalmente fechado e foi sucedido por `docs/implementation/v2-sprint-cycle.md`.

---

## 2. Regra de leitura

Este documento é a fonte oficial do que entra em execução agora para `v1.5`.

Ele não substitui:

- o Documento-Mestre como visão canônica;
- o programa até `v3` como direção macro;
- o `HANDOFF.md` como retomada operacional.

---

## 3. Sequência oficial das sprints

1. Sprint 1 - modelo de checkpoints e estado recuperável da continuidade
2. Sprint 2 - replay e recuperação governada
3. Sprint 3 - pausas `HITL` em conflitos de continuidade
4. Sprint 4 - absorção parcial de `LangGraph` no subfluxo stateful
5. Sprint 5 - evals e comparação do runtime de continuidade
6. Sprint 6 - consolidação do corte de `v1.5`

---

## 4. Sprint 1

Status:

- concluída

### Objetivo

Definir como a continuidade profunda vira estado recuperável, e não apenas decisão
deliberativa ou memória resumida.

### Entregas obrigatórias

- modelo explícito de checkpoint de continuidade;
- contrato interno mínimo para replay e recuperação;
- persistência do estado recuperável acima da missão atual.

### Ordem de implementação

1. tipos internos de checkpoint;
2. persistência;
3. recuperação e inspeção.

### Testes obrigatórios

- checkpoint persistido entre instâncias;
- recuperação do estado correto após reinício;
- ausência de regressão no baseline atual.

Resultado registrado nesta rodada:

- `memory-service` passou a persistir checkpoints explícitos da continuidade por sessão;
- a recuperação agora expõe `continuity_checkpoint_id`, `continuity_checkpoint_status`, resumo e replay mínimo como hints estruturais;
- a API de inspeção `get_session_continuity_checkpoint()` passou a expor o estado recuperável mais recente sem quebrar o baseline atual.

---

## 5. Sprint 2

Status:

- concluída

### Objetivo

Executar replay e recuperação governada do fluxo de continuidade.

### Entregas obrigatórias

- caminho explícito de replay;
- recuperação segura após interrupção;
- rastreabilidade do ponto de retomada.

### Ordem de implementação

1. replay mínimo;
2. recuperação;
3. integração com observabilidade.

Resultado registrado nesta rodada:

- `memory-service` passou a expor `ContinuityReplayContract` com `replay_status`, `recovery_mode` e `resume_point` por sessão;
- a recuperação passou a publicar hints estruturais de replay e retomada segura no contexto recuperado;
- `orchestrator-service` e a trilha opcional de `LangGraph` passaram a emitir `continuity_replay_loaded` e `continuity_recovery_governed` quando o checkpoint exige retomada governada;
- `planning-engine`, `governance-service` e `synthesis-engine` passaram a tratar checkpoint contido ou aguardando validação como fluxo de recuperação governada, sem retomada automática.

---

## 6. Sprint 3

Status:

- concluída

### Objetivo

Introduzir pausas `HITL` quando a continuidade disputar direção com o contexto atual.

### Entregas obrigatórias

- estado de pausa governada;
- retomada manual rastreável;
- integração com governança e síntese.

Resultado registrado nesta rodada:

- `memory-service` passou a expor `ContinuityPauseContract` e a persistir resolução manual de pausa governada por sessão;
- checkpoints em `awaiting_validation` ou `contained` agora geram pausa recuperável, com `pause_status`, `pause_reason`, `resolution_status` e agente responsável pela retomada;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a emitir `continuity_pause_resolved` quando a retomada manual é registrada via `metadata.continuity_resume`;
- `planning-engine`, `governance-service` e `synthesis-engine` passaram a respeitar pausa governada como estado explícito do runtime, sem retomada silenciosa acima de checkpoint contido ou aguardando validação.

---

## 7. Sprint 4

Status:

- concluída

### Objetivo

Absorver `LangGraph` parcialmente no subfluxo stateful de continuidade.

### Entregas obrigatórias

- subfluxo stateful isolado;
- checkpoints e replay sobre esse recorte;
- comparação com o baseline anterior.

### Regra

- `LangGraph` entra por recorte;
- o núcleo soberano do JARVIS continua próprio.

Resultado registrado nesta rodada:

- o fluxo opcional de `LangGraph` passou a isolar a continuidade em um subfluxo stateful próprio, sem arrastar todo o orquestrador para o runtime externo;
- checkpoint, replay e pausa governada passaram a ser executados dentro desse subfluxo dedicado antes do restante do caminho deliberativo;
- o fluxo passou a emitir `continuity_subflow_completed` com `runtime_mode=langgraph_subflow`, tornando a absorção parcial observável e comparável;
- `observability-service`, `internal_pilot_report` e `compare_orchestrator_paths` passaram a expor `continuity_runtime_mode`, preservando comparação com o baseline linear anterior.

---

## 8. Sprint 5

Status:

- concluída

### Objetivo

Transformar o runtime de continuidade em comportamento avaliável e comparável.

### Entregas obrigatórias

- evals do runtime de continuidade;
- comparação entre baseline e subfluxo absorvido;
- decisão baseada em evidência, não em preferência tecnológica.

Resultado registrado nesta rodada:

- o piloto passou a incluir cenários explícitos de conflito de continuidade e retomada manual após pausa governada;
- `internal_pilot_support` passou a medir aderência a expectativas de decisão, operação e continuidade por cenário;
- `compare_orchestrator_paths` passou a emitir `baseline_expectation_score`, `candidate_expectation_score`, `candidate_runtime_coverage` e decisão explícita de comparação;
- a rodada local de comparação fechou com `overall_verdict=equivalent`, `matched_scenarios=6/6` e `comparison_decision=candidate_ready_for_eval_gate`;
- `evolution_from_pilot` e `evolution-lab` passaram a carregar `continuity_runtime_mode`, permitindo proposals e comparações sandbox-only com o runtime absorvido.

---

## 9. Sprint 6

Status:

- concluída

### Objetivo

Consolidar `v1.5` e decidir o que segue para preparação de `v2`.

### Entregas obrigatórias

- fechamento do ciclo;
- backlog classificado;
- decisão formal sobre o que permanece em `v1.5` e o que amadurece para `v2`.

Resultado registrado nesta rodada:

- o primeiro ciclo do `v1.5` foi formalmente encerrado;
- `tools/close_stateful_runtime_cycle.py` passou a gerar artefatos executáveis de fechamento do ciclo com evidência observável e comparativa do runtime;
- `docs/implementation/v1-5-cycle-closure.md` passou a registrar o corte formal para `v2`;
- `docs/implementation/v2-sprint-cycle.md` passou a ser o novo plano rolante ativo da fase seguinte.

---

## 10. Definição de pronto do ciclo

O ciclo de `v1.5` será considerado pronto quando:

- continuidade profunda operar com estado recuperável;
- replay e pausa governada estiverem funcionais;
- a absorção parcial de `LangGraph` estiver provada ou rejeitada com evidência;
- o núcleo tiver dado o primeiro salto estrutural acima do baseline do `v1`
  sem perder unidade, governança e rastreabilidade.

---

## 11. Estudos externos autorizados neste ciclo

Os estudos externos continuam subordinados ao ciclo ativo.

Eles entram apenas quando ajudam diretamente o objetivo de `v1.5`:

- checkpoint;
- replay;
- pausa `HITL`;
- runtime stateful governado para continuidade profunda.

Perguntas permitidas agora:

- `LangGraph`: melhora checkpoint, replay ou `HITL` do subfluxo stateful de continuidade?
- `Hermes Agent`: oferece referência útil de runtime persistente e continuidade recuperável?
- `Graphiti`: oferece modelo útil de relações e timeline para continuidade, sem exigir absorção imediata?
- `Zep`: oferece ideia reutilizável para memória temporal e recuperação de contexto no recorte do `v1.5`?

Regra:

- estudo não bloqueia sprint;
- estudo não redefine a prioridade do ciclo;
- estudo entra para responder uma lacuna concreta do runtime de continuidade;
- conclusão de estudo deve cair em uma destas classes:
  - `absorver depois`
  - `usar como referência`
  - `rejeitar`

Fica explicitamente fora do foco deste ciclo:

- especialistas amplos por domínio;
- `computer use` forte;
- voz como superfície oficial;
- memória profunda com `pgvector` como base obrigatória;
- assistência operacional ampla;
- autoaperfeiçoamento agressivo.
