# Technology Absorption Order

## 1. Objetivo

Este documento transforma o estudo tecnologico ampliado do JARVIS em uma
ordem oficial de traducao e absorcao disciplinada.

Ele responde:

- o que deve ser traduzido primeiro para o sistema;
- o que deve ficar como complemento futuro;
- o que deve permanecer em laboratorio ou horizonte de pesquisa.

Ele nao substitui:

- `docs/architecture/technology-study.md`
- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-repository-review-framework.md`
- `docs/implementation/execution-backlog.md`

Leitura correta:

- este arquivo nao e permissao para importar stacks inteiras;
- ele organiza a **ordem de traducao de padroes** para o JARVIS;
- backlog micro continua vivendo em `docs/implementation/execution-backlog.md`.

---

## 2. Regra central

O JARVIS absorve tecnologias em quatro niveis, sempre nesta ordem:

1. **padroes e primitivas**
2. **adaptadores pequenos**
3. **complementos controlados**
4. **baseline de fase futura**

Regra permanente:

- o sistema absorve primeiro o **que ha de melhor** em uma tecnologia;
- so absorve a tecnologia inteira quando isso for inevitavel e ainda assim
  delimitado;
- nada externo assume identidade, memoria canonica, governanca final ou sintese
  soberana do nucleo.

---

## 3. Criterio de ordenacao

Uma tecnologia sobe na ordem quando combina:

- forte aderencia ao gap atual do JARVIS;
- traducao pequena e reversivel;
- ganho claro de robustez ou profundidade;
- baixo risco de terceirizacao do nucleo.

Uma tecnologia desce na ordem quando:

- resolve um problema mais de produto do que de nucleo;
- exige importar plataforma demais para colher valor pequeno;
- pressupoe uma fase que o JARVIS ainda nao abriu;
- traz mais superficie do que necessidade real.

---

## 4. Ordem oficial de absorcao

### 4.1 Onda 1: traducao imediata para o nucleo

Estas sao as referencias cujo valor ja conversa diretamente com os gaps centrais
do baseline atual.

#### 1. `PydanticAI`

O que absorver:

- contratos estruturados;
- validadores de output;
- retries e falhas controladas;
- tipagem de outputs por etapa.

Onde encaixa:

- `shared/contracts`
- `planning-engine`
- `synthesis-engine`
- outputs de especialistas

O que nao absorver:

- a API inteira como substituta da gramatica do JARVIS.

#### 2. `Letta / MemGPT`

O que absorver:

- memoria viva com manutencao;
- distincao entre memoria fixada e memoria arquivada;
- ciclos de limpeza, consolidacao e review;
- memoria como sistema vivo, nao apenas store.

Onde encaixa:

- `memory-service`
- `memory_registry`
- lifecycle nativo de memoria

O que nao absorver:

- ontologia de memoria deles no lugar das 11 classes canonicas.

#### 3. `Hermes Agent`

O que absorver:

- skills como memoria procedural reutilizavel;
- busca cross-session;
- compressao disciplinada de contexto;
- subagentes isolados para pesquisa e execucao paralela.

Onde encaixa:

- `memory-service`
- `evolution-lab`
- futuras camadas de runtime operacional

O que nao absorver:

- o runtime inteiro do Hermes como cerebro do sistema.

#### 4. `LangGraph`

O que absorver:

- durable execution;
- resumabilidade;
- subgraphs stateful;
- replay e interrupts governados.

Onde encaixa:

- `orchestrator-service`
- continuidade longa
- workflows stateful

O que nao absorver:

- selecao cognitiva, dominio ou governanca como responsabilidade do grafo.

#### 5. `Mastra`

O que absorver:

- semantica forte de workflow tipado;
- snapshots;
- `suspend/resume`;
- taxonomia de evals e leitura de runtime.

Onde encaixa:

- `planning-engine`
- `orchestrator-service`
- `observability-service`
- gramaticas de workflow

O que nao absorver:

- stack inteira de agentes/workflows como baseline JS do sistema.

#### 6. `DSPy / MIPROv2`

O que absorver:

- compile loops;
- optimization by metric;
- surrogate-guided refinement;
- programa LM como objeto de evolucao governada.

Onde encaixa:

- `evolution-lab`
- comparadores
- proposal generation

O que nao absorver:

- uma DSL externa como forma principal de descrever o runtime do JARVIS.

### 4.2 Onda 2: complementos controlados

Estas tecnologias ja sao importantes, mas devem entrar depois que a Onda 1
estiver mais bem traduzida.

#### 7. `OpenAI Agents SDK`

Absorver:

- semantica de handoff;
- spans/tracing;
- adapters de session;
- guardrails por borda do fluxo.

#### 8. `Qwen-Agent`

Absorver:

- context compaction;
- parser fallback de tool calls;
- MCP patterns;
- benchmark de planning com documentos e retrieval.

#### 9. `Graphiti / Zep`

Absorver:

- memoria relacional e temporal;
- facts/summaries;
- point-in-time recall;
- camada futura de graph memory.

#### 10. `Mem0`

Absorver:

- ownership e scoping;
- write lifecycle;
- separacao mais rica entre `user`, `session`, `agent`, `org`, `project`.

Leitura correta:

- o melhor valor aqui e modelagem de escopo, nao substituicao da fundacao de
  memoria.

#### 11. `OpenHands`

Absorver:

- substrate de coding;
- isolamento por sandbox;
- especialista de software mais forte.

#### 12. `browser-use`

Absorver:

- browser operator dedicado;
- browser profiles persistentes;
- superfice de navegacao autenticada e repetivel.

#### 13. `Open Interpreter`

Absorver:

- substrate local de execucao;
- computer primitives de alto nivel;
- multi-language execution governada.

#### 14. `AutoGPT Platform`

Absorver:

- blocos reutilizaveis;
- triggers e webhooks;
- automacoes compostas.

### 4.3 Onda 3: referencias de produto e operacao tardia

Estas tecnologias valem como referencia forte, mas so fazem sentido depois de o
nucleo estar mais maduro.

#### 15. `OpenClaw`

Absorver:

- gateway multicanal;
- lifecycle de skills;
- runtime operacional local-first.

#### 16. `Manus`

Absorver:

- projects persistentes;
- tarefas assincronas de longa duracao;
- superficie mais ampla de agent platform.

### 4.4 Onda 4: horizonte de pesquisa

Estas referencias devem ficar fora do backlog implementavel atual.

#### 17. `TextGrad`

Valor:

- refinement loops textuais locais no laboratorio evolutivo.

#### 18. `AFlow`

Valor:

- busca sobre workflows via arvore/MCTS.

#### 19. `EvoAgentX`

Valor:

- encadear gerar, avaliar e evoluir workflows.

#### 20. `SEAL`

Valor:

- horizonte de adaptacao persistente.

#### 21. `Darwin Godel Machine`

Valor:

- horizonte de auto-modificacao empiricamente validada.

Regra:

- `TextGrad`, `AFlow` e `EvoAgentX` podem orientar `evolution-lab`;
- `SEAL` e `Darwin Godel Machine` permanecem pesquisa, nao backlog da fase.

---

## 5. Leitura sintetica por camada do JARVIS

### 5.1 Mais urgente agora

- contratos e validacao: `PydanticAI`
- memoria viva e lifecycle: `Letta / MemGPT`
- memoria procedural e recall cross-session: `Hermes Agent`
- durable execution e workflows stateful: `LangGraph`
- semantica de workflow e snapshots: `Mastra`
- evolucao por metrica: `DSPy / MIPROv2`

### 5.2 Depois disso

- handoff/tracing/session adapters: `OpenAI Agents SDK`
- context management e MCP patterns: `Qwen-Agent`
- memoria temporal/graph: `Graphiti`, `Zep`
- ownership/scoping: `Mem0`
- coding specialist substrate: `OpenHands`
- browser/computer substrate: `browser-use`, `Open Interpreter`
- automacoes compostas: `AutoGPT Platform`

### 5.3 Mais tarde

- gateway e canais: `OpenClaw`
- product surface ampla e projetos async: `Manus`

### 5.4 Horizonte

- `TextGrad`
- `AFlow`
- `EvoAgentX`
- `SEAL`
- `Darwin Godel Machine`

---

## 6. Traducao para backlog

A ordem acima vira backlog assim:

- **Onda 1** gera itens `ready` e `blocked` no backlog micro atual;
- **Onda 2** gera itens `blocked` ou `deferred`, dependendo da maturidade do
  baseline;
- **Onda 3** fica mapeada, mas nao entra como fila ativa;
- **Onda 4** entra no radar do `evolution-lab` e em estudos/papers, nao em
  backlog implementavel.

Regra pratica:

- backlog de absorcao significa backlog de **traducao disciplinada**;
- cada item deve dizer explicitamente qual padrao sera traduzido e em qual
  camada do JARVIS;
- nenhum item deve ser escrito como "adotar tecnologia X".

---

## 7. Relacao com os docs vivos

Leitura conjunta recomendada:

- `docs/architecture/technology-study.md` para papel e classe de decisao
- `docs/architecture/technology-capability-extraction-map.md` para o que vale
  extrair
- `docs/architecture/hermes-agent-repository-review.md` e outros reviews
  profundos para tecnologias candidatas
- `docs/implementation/execution-backlog.md` para o lote micro executavel
- `HANDOFF.md` para a leitura tatica da rodada

---

## 8. Conclusao

O JARVIS nao precisa adotar mais tecnologia.

Ele precisa:

- absorver primeiro o que aumenta profundidade do nucleo;
- deixar produto, gateway e superfices amplas para depois;
- usar algoritmos de autoaperfeicoamento como laboratorio, nao como permissao
  para desgovernar o sistema.

Em resumo:

- a ordem correta de absorcao e primeiro **contrato, memoria viva, memoria
  procedural, workflow stateful e evolucao por metrica**;
- depois **hubs de tools, graph memory, coding/browser substrates e automacoes**;
- e so muito depois **product surfaces amplas e auto-modificacao forte**.
