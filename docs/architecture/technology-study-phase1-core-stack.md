# Technology Study Phase 1: Core Stack

## 1. Objetivo

Este documento materializa a Fase 1 do estudo proposto em `docs/architecture/technology-study-matrix.md`.

Escopo desta fase:

- `LangGraph`
- `PostgreSQL + pgvector`
- `LangSmith`

O objetivo não e apenas estudar tecnologia. O objetivo e decidir:

- o que pode ser reaproveitado no JARVIS;
- o que deve permanecer fora do caminho crítico;
- em que momento cada tecnologia entra;
- qual parte deve ser absorvida pelo projeto sem terceirizar o núcleo.

Data da leitura: `2026-03-19`

---

## 2. Estado atual do JARVIS

Leitura do repositório no momento deste estudo:

- o JARVIS já possui baseline próprio do `v1`, com orquestracao, memória, governança, conhecimento, observabilidade e operação implementados;
- `PostgreSQL` já esta validado como backend operacional da memória;
- `sqlite` permanece como fallback local;
- `LangSmith` já aparece no codigo como espelhamento agentic opcional, mas ainda de forma mínima;
- `LangGraph` ainda não foi absorvido no núcleo real do repositório.

Inferencia:

- o projeto já tem um núcleo funcional suficiente para estudar reaproveitamento sem entrar em fase especulativa;
- por isso, o estudo agora deve focar em `encaixe`, `custo de migracao`, `ganho arquitetural` e `limites de adoção`.

---

## 3. Leitura consolidada por tecnologia

### 3.1 LangGraph

#### Leitura oficial relevante

Pelas docs oficiais, `LangGraph` se apresenta como um framework de baixo nivel para agentes e workflows stateful, com foco em:

- durable execution;
- persistence/checkpoints;
- human-in-the-loop;
- time travel;
- memória;
- subgraphs;
- integração com `LangSmith`.

Ponto importante: a própria documentacao enfatiza que `LangGraph` e infraestrutura de orquestracao, não arquitetura pronta de agente.

#### O que pode ser reaproveitado no JARVIS

- modelo de execução stateful para o fluxo central do `orchestrator-service`;
- checkpoints por etapa do fluxo;
- replay de execução para depuracao e auditoria;
- suporte mais natural a `human-in-the-loop` em pontos de governança;
- subgraphs para decompor:
  - entendimento;
  - planejamento;
  - governança;
  - operação;
  - síntese;
- mapeamento entre `session_id` ou `mission_id` do JARVIS e `threads`/estado persistido do runtime.

#### O que não deve ser terceirizado ao LangGraph

- identidade do JARVIS;
- contratos canônicos em `shared/`;
- política de governança;
- política de memória;
- síntese final e arbitragem cognitiva como decisão de produto.

#### Decisóo prática

`LangGraph` continua aprovado como `substrato principal de orquestracao stateful`, mas **não deve entrar como reescrita ampla imediata do `v1`**.

Decisóo desta fase:

- `adotar como próxima camada estrutural do núcleo`;
- `não reescrever o baseline inteiro antes do internal pilot`.

#### Motivo

O ganho real esta em durabilidade, checkpoints, replay e HITL. O risco real esta em parar um baseline funcional para fazer uma migracao ampla cedo demais.

#### Recomendacao para o JARVIS

Fazer a adoção em duas etapas:

1. `POC controlada`
   - envolver apenas o fluxo do orquestrador;
   - manter `shared/`, `memory-service`, `governance-service` e `operational-service` como lógica própria;
   - usar `LangGraph` como runtime de estado e execução;
2. `migracao parcial`
   - mover primeiro os caminhos com maior valor:
     - checkpoints;
     - replay;
     - pauses de governança;
     - continuidade de missão multi-etapa.

#### Gatilho correto para entrar

Depois da primeira janela de `internal pilot`, quando houver evidência suficiente dos gargalos reais do orquestrador atual.

---

### 3.2 PostgreSQL + pgvector

#### Leitura oficial relevante

`pgvector` permite manter vetores no próprio `Postgres`, com:

- busca exata e aproximada;
- `HNSW` e `IVFFlat`;
- operadores de distancia para `L2`, inner product, cosine, `L1`, Hamming e Jaccard;
- manutencao dos vetores no mesmo banco relacional;
- preservacao das propriedades operacionais do `Postgres`, incluindo `JOINs`, conformidade `ACID` e `point-in-time recovery`.

Ao mesmo tempo, a documentacao oficial do `PostgreSQL` reforca que indices sempre trazem custo operacional e devem ser usados com critério.

#### O que pode ser reaproveitado no JARVIS

- manter o `PostgreSQL` como única base operacional de memória e persistência;
- adicionar `pgvector` no mesmo backbone, sem criar outro banco só para retrieval;
- usar modelo hábrido:
  - memória relacional canônica;
  - embeddings e busca vetorial no mesmo banco;
- preservar filtros relacionais, `JOINs`, status, datas, escopos e classes de memória em volta da busca vetorial.

#### O que não deve entrar agora

- indexacao vetorial ampla sem consumidor real;
- embeddings em todas as classes de memória por default;
- dependencia de retrieval semântico antes de existir política clara de:
  - ingestao;
  - atualizacao;
  - invalidacao;
  - ranking;
  - auditoria.

#### Decisóo prática

Para o JARVIS atual, a decisão correta e:

- `PostgreSQL`: já adotado e confirmado;
- `pgvector`: aprovado arquiteturalmente, mas **ainda não entra no baseline do codigo como caminho crítico**.

#### Motivo

Hoje o repositório já usa `PostgreSQL` com valor operacional real. Já `pgvector` ainda não tem:

- pipeline de embeddings;
- consumidor canônico no `knowledge-service`;
- retrieval semântico entre missóes;
- benchmark de relevancia e custo no contexto do JARVIS.

Sem isso, adicionar `pgvector` agora seria mais promessa arquitetural do que ganho concreto.

#### Recomendacao para o JARVIS

Absorção em duas etapas:

1. `preparacao`
   - definir quais entidades ganham embedding primeiro;
   - provavelmente:
     - resumos de missão;
     - memórias promovidas;
     - corpus curado do knowledge-service;
2. `entrada controlada`
   - comecar com busca exata ou indexacao mínima;
   - usar `HNSW` apenas quando o volume justificar;
   - manter a trilha relacional e filtros de governança como camada primaria.

#### Gatilho correto para entrar

Quando o `knowledge-service` sair do corpus curado mínimo e quando a memória entre missóes exigir recall semântico real.

---

### 3.3 LangSmith

#### Leitura oficial relevante

Pelas docs oficiais, `LangSmith` cobre:

- traces e runs;
- dashboards prebuilt e customizaveis;
- monitoramento com laténcia, erro, custo, tokens e feedback;
- avaliação offline com datasets e experimentos;
- avaliação online sobre traces/runs/threads em produção;
- automações e alertas;
- configuração por variáveis de ambiente ou de forma programatica;
- suporte a cloud, hybrid e self-hosted.

Ponto crítico: as dashboards e agrupamentos dependem fortemente de `metadata` e `tags` bem modelados, e a própria documentacao alerta que metadados não propagam automaticamente entre trace e child runs.

#### O que pode ser reaproveitado no JARVIS

- observabilidade agentic complementar ao `observability-service` local;
- trilha por `request_id`, `session_id`, `mission_id` e `operation_id`;
- dashboards por:
  - tipo de fluxo;
  - decisão de governança;
  - status operacional;
  - especialista convocado;
- datasets e experimentos para avaliar:
  - `planning`;
  - `analysis`;
  - bloqueios de governança;
  - continuidade de missão;
- online evaluators para escopo reduzido do `internal pilot`.

#### O que não deve virar dependencia central

- a trilha canônica do JARVIS;
- a única fonte de auditoria;
- o único repositório de sinais de qualidade;
- a única estratégia de debug operacional.

#### Decisóo prática

`LangSmith` permanece como `complementar no v1`, e essa decisão esta correta.

Para o JARVIS atual:

- a trilha local persistida continua sendo a fonte primaria;
- `LangSmith` entra como espelhamento e camada de monitoramento/eval.

#### Motivo

Isso preserva:

- independencia operacional;
- fallback local;
- rastreabilidade mesmo sem conectividade externa ou conta ativa.

E ao mesmo tempo permite capturar o melhor do produto:

- visualizacao;
- análise de traces;
- dashboards;
- experiments;
- online evaluators.

#### Ajuste necessario no codigo atual

Inferencia a partir das docs e do adaptador atual:

- o adaptador existente em `services/observability-service/src/observability_service/agentic.py` já espelha eventos para `LangSmith`;
- mas hoje ele faz isso de forma muito plana, um `run` por evento;
- isso e util como espelhamento inicial, mas ainda não aproveita bem o modelo de `trace -> runs -> metadata`.

Recomendacao:

- criar um root trace por `request_id`;
- emitir child runs por evento relevante;
- anexar `metadata` tanto no root quanto nos child runs;
- padronizar:
  - `request_id`
  - `session_id`
  - `mission_id`
  - `operation_id`
  - `intent`
  - `governance_decision`
  - `task_type`
  - `active_domains`

#### Gatilho correto para aprofundar

Antes da janela de `internal pilot`, porque `LangSmith` tem mais valor quando entra junto com monitoramento e avaliação do primeiro uso real.

---

## 4. Decisóo consolidada da Fase 1

| Tecnologia | Decisóo refinada para o JARVIS | O que reaproveitar | O que adiar |
| --- | --- | --- | --- |
| `LangGraph` | absorver no próximo salto do núcleo, sem reescrita total imediata | checkpoints, replay, HITL, runtime stateful, subgraphs | migracao completa do baseline antes do `internal pilot` |
| `PostgreSQL` | manter como backbone operacional | memória transacional, estado de missão, continuidade e auditoria | nada estrutural |
| `pgvector` | aprovado, mas fora do caminho crítico imediato | busca vetorial no mesmo banco, schema hábrido relacional + vetorial | embeddings amplos, indexacao pesada e retrieval semântico global |
| `LangSmith` | complementar imediato do `v1` | traces, dashboards, evals, online evaluators, alertas | tornar-se fonte canônica única de observabilidade |

---

## 5. Reaproveitamento recomendado no projeto

### 5.1 Entrar no próximo bloco de trabalho

- aprofundar o adaptador `LangSmith` atual para refletir `trace tree` real;
- preparar o `observability-service` para metadados consistentes;
- manter `PostgreSQL` como backend padrao do perfil `controlled`.

### 5.2 Entrar depois do `internal pilot`

- `POC` de `LangGraph` sobre o fluxo do orquestrador;
- comparar:
  - orquestrador atual;
  - orquestrador com `LangGraph` como runtime stateful;
- medir ganho em:
  - replay;
  - fault tolerance;
  - HITL;
  - legibilidade de fluxo.

### 5.3 Entrar só quando houver consumidor real

- `pgvector`;
- embedding de memória de missão;
- retrieval semântico entre missóes;
- retrieval semântico do corpus curado.

---

## 6. Próxima ordem recomendada

1. endurecer `LangSmith` como complemento real do `internal pilot`;
2. abrir `ADR` de absorção parcial de `LangGraph` no núcleo;
3. desenhar o schema mínimo de `pgvector`, sem ainda ativar indexacao no caminho crítico.

---

## 7. Sóntese executiva

Conclusao desta fase:

- `LangGraph` deve entrar, mas no momento certo e como substrato técnico, não como substituto da arquitetura do JARVIS;
- `PostgreSQL` já esta corretamente reaproveitado;
- `pgvector` ainda não deve ser colocado no caminho crítico sem memória semântica e retrieval reais;
- `LangSmith` e o melhor complemento imediato para o próximo ciclo real de uso controlado.

Em termos pragmaticos:

- `LangSmith` entra primeiro;
- `LangGraph` entra depois;
- `pgvector` entra por ultimo, quando houver consumidor canônico.

---

## 8. Fontes oficiais usadas

- LangGraph overview: `https://docs.langchain.com/oss/python/langgraph/overview`
- LangGraph persistence: `https://docs.langchain.com/oss/javascript/langgraph/persistence`
- LangGraph GitHub repository: `https://github.com/langchain-ai/langgraph`
- LangSmith tracing quickstart: `https://docs.langchain.com/langsmith/observability-quickstart`
- LangSmith evaluation overview: `https://docs.langchain.com/langsmith/evaluation`
- LangSmith dashboards: `https://docs.langchain.com/langsmith/dashboards`
- LangSmith custom tracing config: `https://docs.langchain.com/langsmith/trace-without-env-vars`
- LangSmith self-hosted usage: `https://docs.langchain.com/langsmith/self-host-usage`
- LangSmith SDK repository: `https://github.com/langchain-ai/langsmith-sdk`
- PostgreSQL indexes docs: `https://www.postgresql.org/docs/current/indexes.html`
- pgvector repository and README: `https://github.com/pgvector/pgvector`
