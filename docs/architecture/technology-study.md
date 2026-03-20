# Technology Study

## 1. Objetivo

Este documento consolida o estudo tecnologico do JARVIS em um unico artefato.

Ele substitui a separacao anterior entre uma matriz geral e um estudo aplicado da
fase 1. O objetivo aqui e manter uma leitura unica sobre:

- o que o `v1` realmente adota;
- o que entra apenas como complemento controlado;
- o que e referencia arquitetural;
- o que deve continuar em laboratorio ou pos-`v1`.

Em caso de conflito, `documento_mestre_jarvis.md` continua prevalecendo.

---

## 2. Classes de decisao

Cada tecnologia citada deve cair em uma destas classes:

- `adotar no v1`
- `complementar no v1`
- `laboratorio`
- `inspiracao arquitetural`
- `deferir para v2`
- `nao adotar como nucleo`

---

## 3. Criterios de estudo

Toda tecnologia deve ser avaliada por:

- aderencia ao papel arquitetural do JARVIS;
- maturidade e manutencao do repositorio;
- licenca e risco de uso;
- persistencia e isolamento;
- observabilidade e depuracao;
- risco de lock-in;
- reaproveitamento parcial sem terceirizar o nucleo.

---

## 4. Matriz consolidada

| Tecnologia | Papel no JARVIS | Decisao atual |
| --- | --- | --- |
| LangGraph | runtime stateful e checkpoints para o orquestrador | `complementar no v1` |
| PostgreSQL | backbone operacional de memoria e persistencia | `adotar no v1` |
| pgvector | extensao vetorial do backbone relacional | `deferir para pos-v1` |
| LangSmith | observabilidade agentic complementar | `complementar no v1` |
| OpenAI Realtime / Voice | camada moderna de voz e realtime | `complementar no v1` |
| OpenHands | especialista subordinado de software | `complementar no v1` |
| Zep | memoria contextual complementar | `laboratorio` |
| Graphiti | memoria temporal e relacional complementar | `laboratorio` |
| LlamaIndex | ingestao e retrieval complementar | `laboratorio` |
| Hermes Agent | referencia de runtime persistente e skills | `inspiracao arquitetural` |
| OpenClaw | referencia de gateway, canais e operacao | `inspiracao arquitetural` |
| TextGrad | otimizacao textual offline | `laboratorio` |
| DSPy / MIPROv2 | otimizacao de programas LM | `laboratorio` |
| AFlow | otimizacao automatizada de workflows | `laboratorio` |
| EvoAgentX | evolucao automatizada de workflows e agentes | `laboratorio` |
| SEAL | auto-adaptacao persistente em nivel de modelo | `deferir para v2` |
| Darwin Godel Machine | autoaperfeicoamento com mudanca de codigo | `deferir para v2` |

---

## 5. Leitura aplicada da fase 1

### 5.1 LangGraph

O que interessa ao JARVIS:

- durable execution;
- checkpoints;
- replay;
- `human-in-the-loop`;
- subgraphs para partes do fluxo.

O que nao deve ser terceirizado:

- identidade do JARVIS;
- contratos canonicos;
- governanca;
- politica de memoria;
- arbitragem cognitiva como decisao de produto.

Decisao atual:

- aprovado como proximo salto estrutural do nucleo;
- mantido fora do caminho critico do `v1`;
- continua como POC opcional no repositorio atual.

### 5.2 PostgreSQL + pgvector

Leitura atual:

- `PostgreSQL` ja foi validado e entrou como backend operacional recomendado;
- `pgvector` continua aprovado arquiteturalmente, mas ainda nao tem consumidor
  canonico suficiente para virar parte obrigatoria do baseline.

Decisao atual:

- `PostgreSQL`: `adotar no v1`;
- `pgvector`: `deferir para pos-v1`.

### 5.3 LangSmith

Leitura atual:

- a trilha local persistida continua sendo a fonte primaria;
- `LangSmith` agrega valor como espelhamento, dashboards, experiments e evals;
- nao deve se tornar a unica fonte de auditoria.

Decisao atual:

- `complementar no v1`.

---

## 6. Reaproveitamento recomendado

Entrou no baseline do `v1`:

- `PostgreSQL` como backend operacional recomendado.

Permanece complementar no `v1`:

- `LangSmith`;
- `LangGraph` apenas como POC opcional;
- stack de voz e realtime;
- OpenHands como referencia e complemento futuro controlado.

Permanece fora do caminho critico:

- `pgvector`;
- laboratorios de memoria externa;
- frameworks de evolucao mais agressivos;
- referencias arquiteturais como Hermes e OpenClaw.

---

## 7. Ordem recomendada de estudo externo

Se o projeto abrir uma pasta separada para pesquisa, a ordem continua sendo:

1. `langchain-ai/langgraph`
2. `All-Hands-AI/OpenHands`
3. `openclaw/openclaw`
4. Hermes Agent
5. `getzep/graphiti`
6. `run-llama/llama_index`
7. `zou-group/textgrad`
8. `stanfordnlp/dspy`
9. `FoundationAgents/AFlow`
10. `EvoAgentX/EvoAgentX`

Regra:

- estudar fora do repositorio principal;
- preferir clone raso;
- nao executar marketplaces, installers ou scripts de terceiros sem isolamento.

---

## 8. Sintese executiva

A leitura consolidada mais segura hoje e:

- o `v1` deve fechar sobre uma base propria;
- `PostgreSQL` foi o reaproveitamento mais forte ja absorvido;
- `LangSmith` continua sendo complemento util;
- `LangGraph` continua sendo direcao arquitetural forte, mas nao foi promovido
  ao baseline do `v1`;
- memoria vetorial, frameworks de autoevolucao mais fortes e referencias de
  runtime externo ficam para ciclos posteriores.
