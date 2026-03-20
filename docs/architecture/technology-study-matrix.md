# Technology Study Matrix

## 1. Objetivo

Este documento deriva principalmente dos capitulos de stack, posicionamento oficial de tecnologias e referencias algoritmicas do `documento_mestre_jarvis.md`.

Seu papel e transformar o inventario tecnologico do Documento-Mestre em uma matriz prática de estudo, benchmark e reaproveitamento para o JARVIS.

Ele responde a quatro perguntas:

- qual tecnologia entra como base real do `v1`;
- qual tecnologia entra apenas como complemento controlado;
- qual tecnologia deve ser estudada como referencia arquitetural ou laboratório;
- quais estudos ainda faltam antes de qualquer adoção maior.

---

## 2. Regra de leitura

Este documento não redefine a arquitetura do JARVIS.

Ele organiza o estudo de tecnologias, frameworks, algoritmos e repositórios segundo o papel arquitetural já definido pelo Documento-Mestre.

Em caso de conflito:

1. o `documento_mestre_jarvis.md` prevalece;
2. um ADR formal pode alterar o posicionamento oficial;
3. esta matriz serve para estudo, benchmark e priorizacao de reaproveitamento.

---

## 3. Classes de decisão

Cada item desta matriz deve cair em uma destas classes:

- `adotar no v1`: entra como parte prática do baseline do `v1`;
- `complementar no v1`: pode ser usado de forma controlada, sem substituir o núcleo;
- `laboratório`: deve influenciar benchmark e experimentação, não o caminho crítico;
- `inspiracao arquitetural`: serve como referencia de desenho, não como fundação do sistema;
- `deferir para v2`: relevante, mas fora do centro do `v1`;
- `não adotar como núcleo`: pode ser forte, mas não deve virar fundação do JARVIS.

---

## 4. Critérios de estudo

Toda tecnologia ou repositório citado no Documento-Mestre deve ser estudado segundo estes critérios:

- aderencia ao papel arquitetural previsto para o JARVIS;
- maturidade do repositório e ritmo de manutencao;
- clareza de licenca e possibilidade de uso real no projeto;
- modelo de persistencia e isolamento;
- observabilidade nativa ou facilidade de instrumentacao;
- risco de lock-in;
- facilidade de uso local e em produção controlada;
- compatibilidade com identidade unificada, governança e rastreabilidade;
- possibilidade de reaproveitamento parcial, sem terceirizar o núcleo.

---

## 5. Matriz principal

| Tecnologia / Referencia | Papel no JARVIS | Repositório / fonte principal a estudar | O que estudar primeiro | Decisóo atual |
| --- | --- | --- | --- | --- |
| LangGraph | Substrato principal de orquestracao stateful | `langchain-ai/langgraph` e documentacao oficial | durable execution, checkpoints, HITL, replay, composicao de fluxos | `adotar no v1` |
| PostgreSQL + pgvector | Backbone de memória e persistencia | `postgres/postgres` e `pgvector/pgvector` | schema, indices, paridade com `sqlite`, operação local, migracao | `adotar no v1` |
| LangSmith | Observabilidade agentic principal | documentacao oficial LangSmith | traces, evals, dashboards, correlação, comparação com trilha interna | `complementar no v1` |
| OpenAI Realtime / Voice stack | Camada moderna de voz e realtime | documentacao oficial OpenAI | speech-to-speech, handoffs, laténcia, modelo de sessão e segurança | `complementar no v1` |
| OpenHands Software Agent SDK | Especialista subordinado de software | `All-Hands-AI/OpenHands` | ACI, tool model, isolamento, integração como especialista convocavel | `complementar no v1` |
| OpenHands / Open Operator | Referencia operacional e extensao técnica | ecossistema OpenHands | operador técnico, execução controlada, tarefas técnicas e ambientes isolados | `deferir para v2` |
| Zep | Memória contextual complementar | `getzep/zep` | modelo de memória, modo de deploy, estado atual do projeto e custo de integração | `laboratório` |
| Graphiti | Memória temporal e relacional complementar | `getzep/graphiti` | grafo temporal, relações, maturidade real, custo operacional | `laboratório` |
| LlamaIndex | Ingestao e retrieval complementar | `run-llama/llama_index` | ingestao, parsing, retrieval pipeline, workflows, durabilidade | `laboratório` |
| Hermes Agent | Referencia arquitetural forte para memória viva e runtime persistente | repositório e site oficial Hermes Agent | skills, memória, canais, scheduler, persistencia agentic | `inspiracao arquitetural` |
| Hermes Agent Self-Evolution | Referencia prática de melhoria por skills e loop evolutivo | ecossistema Hermes | como trata melhoria, limites de autoaplicacao, papel de skill growth | `laboratório` |
| OpenClaw | Referencia arquitetural forte para gateway, canais e operação | `openclaw/openclaw` e docs oficiais | session model, gateway, canais, skills, security model | `inspiracao arquitetural` |
| TextGrad | Otimizacao textual offline | `zou-group/textgrad` | prompt/program optimization, avaliação, custo e estabilidade | `laboratório` |
| DSPy / MIPROv2 | Otimizacao de programas LM | `stanfordnlp/dspy` e docs oficiais | programas declarativos, tuning de prompt e busca discreta | `laboratório` |
| AFlow | Otimizacao automatizada de workflows | `FoundationAgents/AFlow` | search de workflow, avaliação e integração com benchmark | `laboratório` |
| EvoAgentX | Evolução automatizada de workflows e agentes | `EvoAgentX/EvoAgentX` | loop de melhoria, comparação de workflows, utilidade no evolution-lab | `laboratório` |
| SEAL | Auto-adaptacao persistente em nivel de modelo | repositório oficial SEAL | mecanismo de self-edit, dependencia de treino, risco operacional | `deferir para v2` |
| Darwin Godel Machine | Autoaperfeicoamento empirico com modificacao de codigo | `jennyzzt/dgm` | benchmark, validação empirica, risco de execução, isolamento | `deferir para v2` |

---

## 6. Leitura consolidada por classe

### 6.1 Base recomendada do v1

Itens que devem sustentar o `v1` diretamente:

- `LangGraph`;
- `PostgreSQL + pgvector`;
- camada própria do JARVIS para contratos, governança, memória e orquestracao.

### 6.2 Complementos controlados do v1

Itens fortes, mas subordinados ao núcleo:

- `LangSmith`;
- `OpenAI Realtime / Voice stack`;
- `OpenHands Software Agent SDK`.

### 6.3 Laboratorio e benchmark

Itens que devem alimentar benchmark e experimentação, não a fundação central:

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

Itens relevantes, mas que não devem entrar como núcleo no `v1`:

- `OpenHands / Open Operator` como camada operacional ampla;
- `SEAL`;
- `Darwin Godel Machine`.

---

## 7. Repositórios prioritários para estudo local

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

Regra de segurança para o estudo:

- clonar fora do repositório principal do JARVIS;
- preferir `--depth 1`;
- estudar primeiro `README`, docs, estrutura, runtime, memória, observabilidade e segurança;
- evitar executar installers, marketplaces de skills ou scripts de terceiros sem isolamento;
- tratar `OpenClaw` em modo especialmente conservador por risco de ecossistema externo.

---

## 8. O que ainda precisa ser estudado

Ainda falta estudar de forma disciplinada:

- maturidade real, manutencao recente e estabilidade de API de cada repositório;
- licencas e restrições de uso para cada componente externo;
- facilidade real de isolar cada tecnologia no monorepo do JARVIS;
- custo de observabilidade, testes e rollback quando cada componente e acoplado ao baseline;
- possibilidade de reaproveitamento parcial, em vez de adoção integral;
- risco de confundir referencia arquitetural com dependencia central.

---

## 9. Próximos derivados naturais

Os próximos artefatos naturais depois desta matriz sóo:

1. `docs/architecture/technology-study-phase1-core-stack.md`, com a Fase 1 do estudo aplicado a `LangGraph`, `PostgreSQL + pgvector` e `LangSmith`;
2. um `ADR` curto sobre o papel de `Hermes Agent` e `OpenClaw` no projeto;
3. uma matriz separada de benchmark para algoritmos evolutivos alem do baseline atual do `evolution-lab`.

---

## 10. Sóntese

A leitura oficial mais segura, no estado atual do projeto, e esta:

- o `v1` deve ser fechado sobre uma base própria e controlada;
- tecnologias fortes devem ser reaproveitadas de forma localizada e subordinada;
- referencias como `Hermes Agent` e `OpenClaw` devem influenciar a arquitetura, não substitui-la;
- algoritmos evolutivos e frameworks de autoaperfeicoamento devem permanecer no laboratório até prova forte de utilidade e segurança.

