# V2 Sprint Cycle

## 1. Objetivo do ciclo atual

Este documento define o ciclo rolante oficial do `v2`.

Foco único do ciclo:

- `especialização controlada subordinada ao núcleo com memória relacional mais rica`

Ele sucede o primeiro ciclo do `v1.5` e transforma o runtime stateful de continuidade
em base para convocação governada de especialistas, sem antecipar superfícies amplas
ou autonomia agressiva.

Fontes de direção:

- `HANDOFF.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/archive/implementation/v1-5-cycle-closure.md`
- `docs/architecture/technology-study.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`

Status desta versão do ciclo:

- Sprint 1 concluída;
- Sprint 2 concluída;
- Sprint 3 concluída;
- Sprint 4 concluída;
- Sprint 5 concluída;
- Sprint 6 concluída;
- este documento passa a ser lido como histórico do primeiro corte do `v2`.

---

## 2. Regra de leitura

Este documento é a fonte oficial do que entra em execução agora para `v2`.

Ele não substitui:

- o Documento-Mestre como visão canônica;
- o programa até `v3` como direção macro;
- o `HANDOFF.md` como retomada operacional.

Ele deve ser lido junto da matriz de aderência para responder:

- qual lacuna do Documento-Mestre a sprint atual fecha;
- quais eixos do mestre continuam fora de cobertura no ciclo ativo.
- qual é o eixo principal movido pela sprint;
- qual lacuna dominante do eixo está sendo atacada;
- qual parte do mestre permanece conscientemente fora de cobertura após a entrega.

---

## 3. Sequência oficial das sprints

1. Sprint 1 - contratos e fronteiras de convocação de especialistas subordinados
2. Sprint 2 - seleção governada de especialistas e handoff interno
3. Sprint 3 - memória relacional compartilhada entre núcleo e especialistas
4. Sprint 4 - registry inicial de domínios e primeiro especialista subordinado em `shadow mode`
5. Sprint 5 - evals, observabilidade e governança de convocação
6. Sprint 6 - consolidação do primeiro corte do `v2`

---

## 4. Sprint 1

Status:

- concluída
- eixo principal do mestre: `especialistas subordinados`
- lacuna dominante fechada: fronteira formal entre núcleo, especialista e tool layer
- continua fora de cobertura: `domínios`, `memórias` compartilhadas e `mentes` com registry canônico

### Objetivo

Definir como especialistas subordinados entram no sistema sem competir com o núcleo
nem quebrar governança, memória e observabilidade.

### Entregas obrigatórias

- contratos internos mínimos para convocação de especialistas;
- fronteiras explícitas entre núcleo, especialista e tool layer;
- hints estruturados de entrada e saída para handoff interno.

### Ordem de implementação

1. contratos;
2. fronteiras de runtime;
3. integração mínima no núcleo.

### Testes obrigatórios

- contratos validados sem quebrar o fluxo atual do orquestrador;
- especialista não responde diretamente ao usuário;
- ausência de regressão no baseline do `v1` e no fechamento do `v1.5`.

### Evidência esperada

- contratos internos materializados;
- decisão explícita de quando um especialista pode ou não ser convocado.

### Definição de pronto

- o sistema consegue distinguir tecnicamente uma convocação de especialista de uma operação comum do núcleo.

### Risco de desvio arquitetural

- transformar especialistas em segunda identidade do sistema.

Resultado registrado nesta rodada:

- `shared/contracts` passou a expor contratos explícitos de fronteira e convocação de especialistas subordinados;
- `specialist-engine` passou a materializar invocações internas com limites de runtime, memória, tool layer e canal de resposta;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a registrar `specialist_contracts_composed`, distinguindo tecnicamente convocação de especialista de operação comum do núcleo;
- a resposta final continua consolidada apenas pelo núcleo, com especialista sempre escondido do usuário final e sem acesso direto a tools ou escrita de memória.

---

## 5. Sprint 2

Status:

- concluída
- eixo principal do mestre: `especialistas subordinados`
- lacuna dominante fechada: elegibilidade e handoff governado de especialistas
- continua fora de cobertura: `domínios`, `memórias` compartilhadas e cobertura canônica de `observabilidade`

### Objetivo

Executar seleção governada de especialistas e handoff interno observável.

### Entregas obrigatórias

- modelo explícito de elegibilidade de especialista;
- handoff interno governado;
- rastreabilidade do especialista escolhido e do racional da escolha.

### Ordem de implementação

1. elegibilidade;
2. handoff;
3. integração com governança e observabilidade.

### Testes obrigatórios

- cenários com e sem especialista;
- bloqueio governado quando a convocação for inadequada;
- rastreabilidade do racional de escolha.

### Evidência esperada

- trilha observável da decisão de convocação;
- coerência entre intenção, contexto e especialista escolhido.

### Definição de pronto

- outro agente consegue entender por que um especialista foi ou não chamado sem inferir a partir do texto final.

### Risco de desvio arquitetural

- handoffs opacos ou convocações por heurística solta.

Resultado registrado nesta rodada:

- `specialist-engine` passou a separar `plan_handoffs` de `review_handoffs`, tornando elegibilidade, contrato e execução fases distintas;
- `governance-service` passou a avaliar handoffs internos de especialistas antes da execução, com decisão explícita entre permitir, condicionar ou bloquear a convocação;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a registrar `specialist_selection_decided`, `specialist_handoff_governed` e `specialist_handoff_blocked` quando aplicável;
- a resposta final continua pertencendo ao núcleo, mas agora a trilha explica por que um especialista foi chamado, condicionado ou contido, sem inferência a partir do texto final.

---

## 6. Sprint 3

Status:

- concluída
- eixo principal do mestre: `memórias`
- lacuna dominante fechada: sair de continuidade ampliada para memória relacional compartilhada auditável
- continua fora de cobertura: registry canônico de `domínios` e composição formal de `mentes`

### Objetivo

Criar memória relacional compartilhada entre núcleo e especialistas, como avanço explícito do eixo de `memórias` e preparação indireta do eixo de `domínios`.

### Entregas obrigatórias

- estrutura mínima de memória relacional;
- ligação entre continuidade da sessão e contexto especializado;
- recuperação contextual útil para handoffs repetidos.

### Ordem de implementação

1. modelo relacional mínimo;
2. persistência e recuperação;
3. integração com handoff e síntese.

### Testes obrigatórios

- relações persistidas e recuperadas entre sessões relacionadas;
- especialista recebe contexto suficiente sem duplicar memória inteira;
- ausência de regressão na continuidade do `v1.5`.

### Evidência esperada

- recuperação relacional acima do estado atual de continuidade;
- ganho perceptível no contexto dos handoffs.

### Definição de pronto

- o núcleo mantém unidade enquanto compartilha contexto relacional útil com especialistas.

### Risco de desvio arquitetural

- criar memória especializada fragmentada e sem governo do núcleo.

Resultado registrado nesta rodada:

- `shared/contracts` passou a expor `SpecialistSharedMemoryContextContract` como contrato canônico de contexto compartilhado mediado pelo núcleo;
- `memory-service` passou a preparar e persistir contexto relacional compartilhado por especialista, com `sharing_mode=core_mediated_read_only` e `write_policy=through_core_only`;
- `specialist-engine` passou a compor handoffs com `shared_memory_context`, sem permitir escrita direta do especialista fora do núcleo;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a registrar `specialist_shared_memory_linked`, anexando memória compartilhada auditável antes do handoff;
- a Sprint 3 fechou o recorte de `memórias` do `v2` sem quebrar a continuidade do `v1.5` e deixou a Sprint 4 pronta para abrir o registry de `domínios`.

---

## 7. Sprint 4

Status:

- concluída
- eixo principal do mestre: `domínios`
- lacuna dominante fechada: ausência de registry canônico e de vínculo explícito entre domínio e especialista
- continua fora de cobertura: composição formal de `mentes` e superfícies amplas

### Objetivo

Abrir o registry inicial de domínios do `v2` e ligar o primeiro especialista subordinado em `shadow mode`, sem torná-lo superfície soberana.

### Entregas obrigatórias

- registry inicial dos domínios ativos do `v2`;
- primeiro especialista convocável em regime controlado;
- vínculo explícito entre domínio, memória compartilhada e especialista;
- resposta final ainda consolidada pelo núcleo;
- caminho de comparação entre fluxo com e sem especialista.

### Ordem de implementação

1. registry inicial de domínios;
2. especialista inicial vinculado a domínio;
3. shadow mode;
4. comparação controlada.

### Testes obrigatórios

- domínio ativo do especialista resolvido pelo registry, não por heurística solta;
- especialista opera como extensão do núcleo;
- sombra comparativa sem regressão do caminho principal;
- saída estruturada compatível com síntese final do núcleo.

### Evidência esperada

- correspondência explícita entre domínio ativo, memória compartilhada e especialista convocado;
- cenários em que o especialista agrega valor real;
- cenários em que o núcleo corretamente não o convoca.

### Definição de pronto

- o primeiro especialista existe como capacidade útil, subordinada e ancorada em domínio explícito.

### Risco de desvio arquitetural

- ampliar especialistas cedo demais sem ganho mensurável.

Resultado registrado nesta rodada:

- `knowledge-service` passou a carregar `domain_registry.json` como registry inicial dos domínios ativos do ciclo;
- `software_development` passou a abrir a primeira rota canônica `domínio -> especialista` do `v2`, ligando `software_change_specialist` em `shadow mode`;
- `cognitive-engine` passou a priorizar hints vindos do registry antes de ampliar heurística solta de especialista;
- `specialist-engine` passou a materializar `linked_domain` e `selection_mode`, deixando explícito quando a convocação é domínio-dirigida e quando ela roda em `shadow`;
- `orchestrator-service` e o fluxo opcional de `LangGraph` passaram a registrar `domain_registry_resolved` e `specialist_shadow_mode_completed`, tornando o recorte comparável sem quebrar a soberania do núcleo.

---

## 8. Sprint 5

Status:

- concluída
- eixo principal do mestre: `observabilidade, validação e evals`
- lacuna dominante fechada: ausência de medição explícita da aderência dos especialistas aos eixos do mestre
- continua fora de cobertura: expansão de `mentes`, voz oficial e tool layer ampla

### Objetivo

Transformar convocação de especialistas em comportamento avaliável, comparável e governável, medindo também aderência a `domínios`, `memórias` e soberania do núcleo.

### Entregas obrigatórias

- evals da convocação;
- observabilidade de handoff e retorno;
- sinalização explícita de aderência aos eixos do mestre;
- critérios explícitos para manter, ajustar ou recuar.

### Ordem de implementação

1. métricas;
2. trilha observável;
3. integração com `evolution-lab`.

### Testes obrigatórios

- comparação entre núcleo puro e fluxo com especialista;
- anomalias e sinais ausentes detectáveis;
- proposals sandbox-only derivadas dos achados.

### Evidência esperada

- decisão baseada em evidência sobre utilidade do especialista;
- leitura explícita do que o recorte do `v2` aproximou ou não do Documento-Mestre;
- sinais suficientes para promoção ou contenção.

### Definição de pronto

- a convocação de especialistas pode ser julgada por evidência, não por impressão subjetiva.

### Risco de desvio arquitetural

- tratar benchmark ou framework externo como validação automática do desenho.

Resultado registrado nesta rodada:

- `observability-service` passou a auditar `domain_alignment_status`, `memory_alignment_status` e `specialist_sovereignty_status` no fluxo de especialistas;
- `internal_pilot_support` passou a cobrir o cenário `software_shadow_review`, preservando comparação entre núcleo puro, especialista estrutural e especialista em `shadow mode`;
- `compare_orchestrator_paths` passou a emitir `baseline_axis_adherence_score`, `candidate_axis_adherence_score` e a comparar explicitamente sinais de aderência por eixo;
- a rodada local de comparação do `v2` fechou com `overall_verdict=equivalent`, `matched_scenarios=7/7` e `comparison_decision=candidate_ready_for_eval_gate`;
- `evolution_from_pilot` e `evolution-lab` passaram a carregar sinais de domínio, `shadow mode` e aderência aos eixos para proposals sandbox-only.

---

## 9. Sprint 6

Status:

- concluída
- eixo principal do mestre: `implementação, operação, release e incidentes`
- lacuna dominante a atacar: fechamento do ciclo sem classificar o que foi corrigido, deferido ou mantido apenas como visão
- continua fora de cobertura: tudo o que permanecer corretamente deferido por fase

### Objetivo

Consolidar o primeiro corte do `v2` e decidir o que segue para o ciclo seguinte, agora com registries canônicos de `dominios`, `memorias` e `mentes` já abertos no runtime.

### Entregas obrigatórias

- fechamento do ciclo com backlog classificado;
- decisão formal do que permanece no corte do `v2`;
- explicitação do que continua fora do foco imediato;
- classificação final dos eixos em `corrigir agora`, `manter deferido` ou `apenas preservar como visão`.

Critérios explícitos desta consolidação:

- `domain_registry.json` deve ser tratado como mapa canônico soberano, enquanto o subset runtime continua deliberadamente menor;
- `shared/memory_registry.py` deve ser lido como registry formal das 11 classes, e a Sprint 6 deve decidir quais classes sobem de `tipado/documentado` para `runtime parcial` no próximo ciclo;
- `shared/mind_registry.py` deve ser tratado como registry oficial das 24 mentes, e a Sprint 6 deve decidir quanto da composição entre mentes sai do nível implícito para regras soberanas de runtime.

Resultado registrado nesta rodada:

- o primeiro corte do `v2` foi fechado com classificação explícita entre `corrigir agora`, `manter deferido` e `preservar como visão`;
- `tools/close_specialization_cycle.py` passou a gerar o artefato formal de fechamento orientado pelos eixos do Documento-Mestre;
- `docs/archive/implementation/v2-cycle-closure.md` passou a registrar a decisão formal do corte;
- o próximo artefato de execução passou a ser `docs/archive/implementation/v2-alignment-cycle.md`, com foco em `domínios`, `memórias`, `mentes`, identidade auditável e gates por eixo.

---

## 10. Definição de pronto do ciclo

O primeiro ciclo do `v2` será considerado pronto quando:

- especialistas subordinados operarem sem quebrar a unidade do núcleo;
- houver memória relacional mínima útil acima da continuidade do `v1.5`;
- houver vínculo explícito entre pelo menos um especialista inicial e o registry dos domínios ativos do ciclo;
- a convocação de especialistas estiver observável, comparável e governada;
- a matriz de aderência permitir dizer quais eixos do mestre avançaram de fato no `v2`;
- o sistema tiver dado o primeiro salto real rumo à especialização controlada sem ampliar superfícies prematuramente.

---

## 11. Estudos externos autorizados neste ciclo

Os estudos externos continuam subordinados ao ciclo ativo.

Eles entram apenas quando ajudam diretamente o objetivo de `v2`:

- contratos de especialistas;
- handoffs internos;
- memória relacional e contexto compartilhado;
- convocação governada e observável.

Perguntas permitidas agora:

- `OpenHands`: ajuda a modelar o primeiro especialista técnico subordinado sem terceirizar o núcleo?
- `PydanticAI`: melhora contratos, outputs estruturados e previsibilidade de handoff sem substituir contratos canônicos?
- `Hermes Agent`: oferece referência útil de runtime persistente e estado compartilhado para especialistas?
- `Graphiti`: oferece modelo útil de memória relacional e timeline sem exigir absorção ampla imediata?
- `Zep`: oferece ideia reutilizável para memória temporal e recuperação contextual no recorte do `v2`?
- `LangGraph`: justifica absorção mais forte em handoffs internos além do subfluxo de continuidade já consolidado?
- `OpenAI Agents SDK`: ensina algo útil sobre handoffs e tracing interno sem transformar o JARVIS em colagem de agentes?

Regra:

- estudo não bloqueia sprint;
- estudo não redefine a prioridade do ciclo;
- estudo entra para responder uma lacuna concreta de especialistas, memória ou handoff;
- conclusão de estudo deve cair em uma destas classes:
  - `absorver depois`
  - `usar como referência`
  - `rejeitar`

Fica explicitamente fora do foco deste ciclo:

- `computer use` amplo;
- voz como superfície oficial;
- memória profunda com `pgvector` como base obrigatória;
- assistente operacional amplo;
- autoaperfeiçoamento promotivo.
