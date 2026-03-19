# Technology Study Matrix

## 1. Objetivo

Este documento deriva principalmente dos capitulos de stack, posicionamento oficial de tecnologias e referencias algoritmicas do `documento_mestre_jarvis.md`.

Seu papel e transformar o inventario tecnologico do Documento-Mestre em uma matriz pratica de estudo, benchmark e reaproveitamento para o JARVIS.

Ele responde a quatro perguntas:

- qual tecnologia entra como base real do `v1`;
- qual tecnologia entra apenas como complemento controlado;
- qual tecnologia deve ser estudada como referencia arquitetural ou laboratorio;
- quais estudos ainda faltam antes de qualquer adocao maior.

---

## 2. Regra de leitura

Este documento nao redefine a arquitetura do JARVIS.

Ele organiza o estudo de tecnologias, frameworks, algoritmos e repositorios segundo o papel arquitetural ja definido pelo Documento-Mestre.

Em caso de conflito:

1. o `documento_mestre_jarvis.md` prevalece;
2. um ADR formal pode alterar o posicionamento oficial;
3. esta matriz serve para estudo, benchmark e priorizacao de reaproveitamento.

---

## 3. Classes de decisao

Cada item desta matriz deve cair em uma destas classes:

- `adotar no v1`: entra como parte pratica do baseline do `v1`;
- `complementar no v1`: pode ser usado de forma controlada, sem substituir o nucleo;
- `laboratorio`: deve influenciar benchmark e experimentacao, nao o caminho critico;
- `inspiracao arquitetural`: serve como referencia de desenho, nao como fundacao do sistema;
- `deferir para v2`: relevante, mas fora do centro do `v1`;
- `nao adotar como nucleo`: pode ser forte, mas nao deve virar fundacao do JARVIS.

---

## 4. Criterios de estudo

Toda tecnologia ou repositorio citado no Documento-Mestre deve ser estudado segundo estes criterios:

- aderencia ao papel arquitetural previsto para o JARVIS;
- maturidade do repositorio e ritmo de manutencao;
- clareza de licenca e possibilidade de uso real no projeto;
- modelo de persistencia e isolamento;
- observabilidade nativa ou facilidade de instrumentacao;
- risco de lock-in;
- facilidade de uso local e em producao controlada;
- compatibilidade com identidade unificada, governanca e rastreabilidade;
- possibilidade de reaproveitamento parcial, sem terceirizar o nucleo.

---

## 5. Matriz principal

| Tecnologia / Referencia | Papel no JARVIS | Repositorio / fonte principal a estudar | O que estudar primeiro | Decisao atual |
| --- | --- | --- | --- | --- |
| LangGraph | Substrato principal de orquestracao stateful | `langchain-ai/langgraph` e documentacao oficial | durable execution, checkpoints, HITL, replay, composicao de fluxos | `adotar no v1` |
| PostgreSQL + pgvector | Backbone de memoria e persistencia | `postgres/postgres` e `pgvector/pgvector` | schema, indices, paridade com `sqlite`, operacao local, migracao | `adotar no v1` |
| LangSmith | Observabilidade agentic principal | documentacao oficial LangSmith | traces, evals, dashboards, correlacao, comparacao com trilha interna | `complementar no v1` |
| OpenAI Realtime / Voice stack | Camada moderna de voz e realtime | documentacao oficial OpenAI | speech-to-speech, handoffs, latencia, modelo de sessao e seguranca | `complementar no v1` |
| OpenHands Software Agent SDK | Especialista subordinado de software | `All-Hands-AI/OpenHands` | ACI, tool model, isolamento, integracao como especialista convocavel | `complementar no v1` |
| OpenHands / Open Operator | Referencia operacional e extensao tecnica | ecossistema OpenHands | operador tecnico, execucao controlada, tarefas tecnicas e ambientes isolados | `deferir para v2` |
| Zep | Memoria contextual complementar | `getzep/zep` | modelo de memoria, modo de deploy, estado atual do projeto e custo de integracao | `laboratorio` |
| Graphiti | Memoria temporal e relacional complementar | `getzep/graphiti` | grafo temporal, relacoes, maturidade real, custo operacional | `laboratorio` |
| LlamaIndex | Ingestao e retrieval complementar | `run-llama/llama_index` | ingestao, parsing, retrieval pipeline, workflows, durabilidade | `laboratorio` |
| Hermes Agent | Referencia arquitetural forte para memoria viva e runtime persistente | repositorio e site oficial Hermes Agent | skills, memoria, canais, scheduler, persistencia agentic | `inspiracao arquitetural` |
| Hermes Agent Self-Evolution | Referencia pratica de melhoria por skills e loop evolutivo | ecossistema Hermes | como trata melhoria, limites de autoaplicacao, papel de skill growth | `laboratorio` |
| OpenClaw | Referencia arquitetural forte para gateway, canais e operacao | `openclaw/openclaw` e docs oficiais | session model, gateway, canais, skills, security model | `inspiracao arquitetural` |
| TextGrad | Otimizacao textual offline | `zou-group/textgrad` | prompt/program optimization, avaliacao, custo e estabilidade | `laboratorio` |
| DSPy / MIPROv2 | Otimizacao de programas LM | `stanfordnlp/dspy` e docs oficiais | programas declarativos, tuning de prompt e busca discreta | `laboratorio` |
| AFlow | Otimizacao automatizada de workflows | `FoundationAgents/AFlow` | search de workflow, avaliacao e integracao com benchmark | `laboratorio` |
| EvoAgentX | Evolucao automatizada de workflows e agentes | `EvoAgentX/EvoAgentX` | loop de melhoria, comparacao de workflows, utilidade no evolution-lab | `laboratorio` |
| SEAL | Auto-adaptacao persistente em nivel de modelo | repositorio oficial SEAL | mecanismo de self-edit, dependencia de treino, risco operacional | `deferir para v2` |
| Darwin Godel Machine | Autoaperfeicoamento empirico com modificacao de codigo | `jennyzzt/dgm` | benchmark, validacao empirica, risco de execucao, isolamento | `deferir para v2` |

---

## 6. Leitura consolidada por classe

### 6.1 Base recomendada do v1

Itens que devem sustentar o `v1` diretamente:

- `LangGraph`;
- `PostgreSQL + pgvector`;
- camada propria do JARVIS para contratos, governanca, memoria e orquestracao.

### 6.2 Complementos controlados do v1

Itens fortes, mas subordinados ao nucleo:

- `LangSmith`;
- `OpenAI Realtime / Voice stack`;
- `OpenHands Software Agent SDK`.

### 6.3 Laboratorio e benchmark

Itens que devem alimentar benchmark e experimentacao, nao a fundacao central:

- `Zep`;
- `Graphiti`;
- `LlamaIndex`;
- `TextGrad`;
- `DSPy / MIPROv2`;
- `AFlow`;
- `EvoAgentX`;
- `Hermes Agent Self-Evolution`.

### 6.4 Inspiracao arquitetural

Itens que devem influenciar o desenho, sem substituir o JARVIS:

- `Hermes Agent`;
- `OpenClaw`.

### 6.5 Fora do centro do v1

Itens relevantes, mas que nao devem entrar como nucleo no `v1`:

- `OpenHands / Open Operator` como camada operacional ampla;
- `SEAL`;
- `Darwin Godel Machine`.

---

## 7. Repositorios prioritarios para estudo local

Se o projeto abrir uma pasta separada de pesquisa, a ordem recomendada de estudo e esta:

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

Regra de seguranca para o estudo:

- clonar fora do repositorio principal do JARVIS;
- preferir `--depth 1`;
- estudar primeiro `README`, docs, estrutura, runtime, memoria, observabilidade e seguranca;
- evitar executar installers, marketplaces de skills ou scripts de terceiros sem isolamento;
- tratar `OpenClaw` em modo especialmente conservador por risco de ecossistema externo.

---

## 8. O que ainda precisa ser estudado

Ainda falta estudar de forma disciplinada:

- maturidade real, manutencao recente e estabilidade de API de cada repositorio;
- licencas e restricoes de uso para cada componente externo;
- facilidade real de isolar cada tecnologia no monorepo do JARVIS;
- custo de observabilidade, testes e rollback quando cada componente e acoplado ao baseline;
- possibilidade de reaproveitamento parcial, em vez de adocao integral;
- risco de confundir referencia arquitetural com dependencia central.

---

## 9. Proximos derivados naturais

Os proximos artefatos naturais depois desta matriz sao:

1. um estudo comparativo operacional por repositorio, fora do repositorio principal do JARVIS;
2. um `ADR` curto sobre o papel de `Hermes Agent` e `OpenClaw` no projeto;
3. uma matriz separada de benchmark para algoritmos evolutivos alem do baseline atual do `evolution-lab`.

---

## 10. Sintese

A leitura oficial mais segura, no estado atual do projeto, e esta:

- o `v1` deve ser fechado sobre uma base propria e controlada;
- tecnologias fortes devem ser reaproveitadas de forma localizada e subordinada;
- referencias como `Hermes Agent` e `OpenClaw` devem influenciar a arquitetura, nao substitui-la;
- algoritmos evolutivos e frameworks de autoaperfeicoamento devem permanecer no laboratorio ate prova forte de utilidade e seguranca.

