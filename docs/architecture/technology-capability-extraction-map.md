# Technology Capability Extraction Map

## 1. Objetivo

Este documento existe para responder a uma pergunta que o
`technology-study.md` ainda cobria apenas parcialmente:

**o que cada tecnologia, ferramenta ou algoritmo tem de melhor que pode ser
traduzido para o JARVIS sem terceirizar o nucleo.**

Ele nao substitui:

- `docs/architecture/technology-study.md`
- `docs/architecture/technology-absorption-order.md`
- `docs/architecture/technology-repository-review-framework.md`
- revisoes profundas de repositorio como `mem0-repository-review.md`

Leitura correta:

- este arquivo e um mapa de **extracao de valor**;
- ele nao e aprovacao automatica de adocao;
- "extrair" significa traduzir padroes, contratos, algoritmos e superficies
  uteis para a gramatica soberana do JARVIS;
- toda absorcao continua subordinada a dominio, mente, memoria, governanca e
  sintese final do sistema.

Estado desta revisao:

- consolidado em `2026-04-08`
- baseado em docs oficiais, repositorios oficiais, READMEs oficiais e papers
  oficiais quando aplicavel

---

## 2. Como ler este mapa

Cada tecnologia e lida por cinco angulos:

- **forca principal**: em que ela realmente se destaca
- **padrao extraivel**: o que vale traduzir para o JARVIS
- **camada JARVIS**: onde isso encaixa sem romper soberania
- **limite de absorcao**: o que nao deve ser importado inteiro
- **prioridade**: `alta`, `media`, `baixa` ou `deferred`

Regras permanentes:

- nao absorver stack inteira quando o ganho esta em um padrao pequeno;
- nao importar ontologia externa no lugar da ontologia do Documento-Mestre;
- nao usar tecnologia externa como cerebro real do sistema;
- preferir adaptadores pequenos, reversiveis e auditaveis.

---

## 3. Leitura executiva

O estudo aprofundado deixa uma imagem mais clara do ecossistema:

- **LangGraph**, **Mastra**, **OpenAI Agents SDK** e **Microsoft Agent Framework**
  sao mais fortes em orquestracao, durable execution, handoffs, guardrails e
  tipagem de workflow do que em identidade cognitiva.
- **Letta**, **Zep**, **Graphiti**, **Mem0**, **Hermes Agent** e **OpenClaw**
  sao mais fortes em memoria, continuidade, skills e runtime persistente do que
  em governanca soberana do nucleo.
- **OpenHands**, **browser-use**, **Open Interpreter** e **Claude Computer Use**
  sao mais fortes em substrate operacional e computer use do que em identidade
  do agente.
- **PydanticAI**, **Qwen-Agent** e **smolagents** sao mais fortes em contratos,
  tool use e simplicidade de composicao do que em arquitetura cognitiva.
- **DSPy/MIPROv2**, **TextGrad**, **AFlow**, **EvoAgentX**, **SEAL** e
  **Darwin Godel Machine** sao mais relevantes como fontes de algoritmos para
  evolucao governada do que como frameworks de produto.

Leitura central para o JARVIS:

- o melhor do ecossistema hoje esta menos em "um framework para substituir tudo"
  e mais em **padroes especializados por camada**;
- o JARVIS continua correto em preservar um nucleo proprio;
- o ganho real vem de absorver **primitivas boas**, nao de importar identidades
  prontas.

---

## 4. Familias e potencial de extracao

### 4.1 Orquestracao, workflow e tracing

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| LangGraph | durable execution, interrupts, replay, subgraphs, resumability | checkpoints soberanos, resumabilidade por thread/run, subfluxos stateful, replay e HITL disciplinado | `orchestrator-service`, continuidade, workflows longos | nao terceirizar ontologia, governanca nem selecao cognitiva ao grafo | alta |
| OpenAI Agents SDK | handoffs como tools, sessions, tracing, guardrails de agente e tool | semantica de handoff, spans padronizados, session adapters, grammar de guardrails por borda do fluxo | tracing complementar, handoff semantics, test harness | nao usar sessions do SDK como memoria canonica do sistema | media-alta |
| CrewAI | crews + flows, memoria unificada, workflows event-driven, guardrails | split entre composicao colaborativa e fluxo operacional, event routing, state handoff entre etapas | laboratorio de automacoes e workflows secundarios | nao absorver memoria unificada deles como substituta do `memory_registry` | media |
| Microsoft Agent Framework | workflows tipados com executors/edges, checkpointing, context providers | linguagem mais forte para executor, edge e evento; tipagem de workflow e recuperacao | contratos de workflow e observabilidade | nao abrir lock-in de stack nem substituir runtime atual por framework externo | media |
| AutoGen | benchmark historico de conversacao entre agentes | padroes de debate, message passing e critic/reviewer | referencias conceituais para deliberacao controlada | nao retomar arquitectura multiagente solta como baseline | baixa |
| Mastra | workflows tipados, suspend/resume, snapshots, runtime context, evals e tracing | semantica forte de `workflow_profile`, snapshots, sleep/events, memory processors, taxonomy de evals | `planning`, `orchestrator`, `observability`, evals | nao importar stack inteira JS nem trocar o core por runtime Mastra | alta |

### 4.2 Coding agents e computer use

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| OpenHands | `CodeAct`, sandbox providers, workspace remoto/api, coding loop especializado | acao unificada baseada em codigo, especialista de software mais forte, isolamento por sandbox | `specialist-engine`, `operational-service`, futuros coding specialists | nao deixar um coding agent externo assumir a relacao soberana com o usuario | media-alta |
| browser-use | browser agent com perfis, auth, proxies, stealth infra e persistent workspaces | browser operator dedicado, perfis autenticados, browser sessions persistentes, browser-specific task loops | tool layer de web operations | nao acoplar o runtime do JARVIS ao cloud/browser stack deles | media |
| Open Interpreter | code execution local, computer API, multimodal screen control, offline mode | substrate local de execucao, computer primitives de alto nivel, multi-language execution | tool layer local e ambiente isolado de execucao | nao permitir execucao host sem governanca e isolamento | media |
| Claude Computer Use | schema de acoes de desktop, combinacao com bash/editor, safety guidance | contrato de acoes de GUI, resolucao segura, VM hygiene, agent loop explicito para tool execution | benchmark de computer-use soberano | nao depender do tool contract da Anthropic como formato canonico interno | media |

### 4.3 Memoria, contexto e continuidade

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| Letta / MemGPT | stateful agents, memory hierarchy, MemFS git-backed, self-editing memory, reflection/defrag | memoria como repositorio vivo, pinned vs archival memory, memory maintenance subagents, editable memory trees | `memory-service`, lifecycle nativo, continuity maintenance | nao importar a ontologia Letta no lugar das 11 classes canonicas | alta |
| Zep | user/session memory + temporal graph + high-level `memory.get()` | API de contexto de usuario, facts/summaries, session->user recall, business-data ingestion | memory retrieval facade, long-term recall, future organization memory | nao terceirizar memoria soberana inteira para um service externo | media-alta |
| Graphiti | temporal knowledge graph, episodes, bi-temporal edges, hybrid graph/text/semantic retrieval | memoria relacional temporal, episodic provenance, contradiction handling, point-in-time queries | fase futura de graph memory ou organization memory | nao puxar graph stack cedo demais sem consumidor canonico | media |
| Mem0 | ownership/scoping rico (`user`, `session`, `agent`, `org`, `project`, `run`), evented writes | modelagem de ownership e scope, write lifecycle, scope adapters | `memory-service` por adaptador estreito | nao absorver a fundacao inteira de vector/history store | media |
| Hermes Agent | skills como memoria procedural, FTS5 de sessoes, memory providers, context compression, bounded memory | memoria procedural versionada, recall cross-session, compressao de contexto, subagentes de reflexao, skills hub | `evolution-lab`, `memory-service`, runtime tooling | nao confundir self-improving operacional com autoevolucao cognitiva do nucleo | alta |
| OpenClaw | markdown memory local, memory_search/get, gateway e workspace local-first | memoria operacional transparente e editavel, local-first durability, workspace-bound memory | gateway e runtime operacional | nao reduzir memoria do JARVIS a arquivos markdown sem politica soberana | media |
| Manus | project memory, sandbox persistente, task/project continuity, connectors | workspaces persistentes por projeto, tarefas assincronas de longa duracao, connectors de produto | fase futura de projetos/async tasks | nao abrir nova vertical de produto antes de maturar mais o nucleo | baixa-media |

### 4.4 Agentes operacionais, gateway e superficies de produto

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| AutoGPT Platform | blocks, agent blocks, webhook-triggered blocks, visual workflow composition | blocos reutilizaveis, triggers/webhooks, workflows compostos, automacoes de longa duracao | futuras automacoes governadas e connectors operacionais | nao mover o programa atual para builder-centric architecture | media |
| OpenClaw | gateway multicanal, skills registry, router, heartbeat autonomy | gateway unico, adapters de canais, installation/update loop de skills, local operator UI | camada futura de canais e operacao pessoal | nao abrir multicanal cedo demais | media |
| Manus | async cloud execution, projects, connectors, desktop bridge, project skills | tarefas assincronas, projects como unidade de continuidade, connectors e "my computer" como superficie unificada | frente futura de agent platform | nao antecipar product surface antes da excelencia do baseline | baixa |
| Hermes Agent | CLI + gateway + cron + subagentes + terminal backends | plataforma operacional coesa, scheduled automation, remote backends, agent-managed skills | etapa futura de runtime operacional mais largo | nao deslocar o projeto para product surface antes de fechar prioridades do nucleo | media |

### 4.5 Contratos, tool use e previsibilidade

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| PydanticAI | output typing, validation context, output validators, retries, multi-agent patterns | contratos estruturados, validation gates, retry semantics, typed outputs por etapa | shared contracts, specialist outputs, workflow validators | nao trocar toda a gramatica de contrato do JARVIS pela API deles | alta |
| Qwen-Agent | planning + tool calling + MCP + context management + typed schema | estrategias de truncacao/compaction, parser fallback de tool calls, MCP-native adapter, benchmark de planning | context management, MCP adapters, local tool agents | nao acoplar o runtime ao ecossistema Qwen nem a ferramentas built-in deles | media |
| smolagents | `CodeAgent`, `ToolCallingAgent`, managed agents, planning interval, sandbox support | code-as-action quando fizer sentido, agentes leves e embutiveis, managed_agents pequenos | laboratorio de especialistas leves e execution adapters | nao assumir sua API experimental como contrato estavel do nucleo | media |

### 4.6 Algoritmos e frameworks de autoaperfeicoamento

| Algoritmo / framework | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| DSPy / MIPROv2 | programas LM declarativos + compilacao/otimizacao de prompts e demos | compile loops, surrogate search, prompt/program optimization por metrica | `evolution-lab`, eval loops, proposal generation | nao substituir o runtime por uma DSL externa | alta |
| TextGrad | "gradientes textuais" para otimizar prompts, respostas e cadeias de raciocinio | refinement loops guiados por critica textual, loss textual, optimizer metaphor | `evolution-lab`, local prompt/workflow refinement | nao usar como justificativa para autoedicao solta de producao | media-alta |
| AFlow | busca por workflow via MCTS | search sobre workflows, escolha de operadores e passos por arvore de busca | sandbox de evolucao de workflow | nao abrir evolucao estrutural automatica no runtime principal | media |
| EvoAgentX | plataforma integrada de autoconstruction + evaluation + evolution de workflows | encadeamento entre gerar fluxo, avaliar e evoluir; refinement vectors e comparative loops | `evolution-lab`, benchmark orchestration | nao importar framework inteiro nem memoria/agentes nativos | media |
| SEAL | self-edits que geram dados de finetuning e diretivas de adaptacao | ideia de "self-edit" persistente e reward-based adaptation | pesquisa de fase futura | nao tentar auto-atualizacao de pesos no baseline atual | deferred |
| Darwin Godel Machine | auto-modificacao de codigo com validacao empirica e arquivo de variantes | arquivo de candidatos, open-ended exploration, benchmark-gated self-modification | pesquisa de longo prazo para evolucao governada | nao permitir self-modification do nucleo sem sandbox, oversight e gates muito mais fortes | deferred |

### 4.7 Infraestrutura inferencial e vector retrieval

| Tecnologia | Forca principal | Padrao extraivel para o JARVIS | Camada JARVIS | Limite de absorcao | Prioridade |
| --- | --- | --- | --- | --- | --- |
| TurboQuant | online vector quantization para `KV cache` e `vector search`, com baixa sobrecarga e foco em distorcao/retrieval | gramatica de compressao vetorial por bitwidth, benchmark de `recall x latencia x memoria`, referencia para `KV cache` comprimido e retrieval vetorial de alta escala | futuro substrate inferencial, `voice/realtime` de contexto longo e retrieval semantico tardio | nao confundir com memoria canonica, nem tratar como justificativa para substituir `PostgreSQL`, `pgvector` ou o nucleo antes de existir consumidor real | baixa |

---

## 5. Algoritmos e padroes que mais valem ouro para o JARVIS

### 5.1 Padroes de maior valor imediato

- **durable execution + interrupt/resume**
  - fonte principal: LangGraph e Mastra
  - valor: completar continuidade, checkpointing e workflows governados de longa duracao
- **typed workflow contracts**
  - fonte principal: Mastra, Microsoft Agent Framework, PydanticAI
  - valor: tornar `workflow_profile`, deliverables e criterios de saida ainda mais formais
- **skill lifecycle como memoria procedural**
  - fonte principal: Hermes Agent e OpenClaw
  - valor: transformar know-how repetido em artefatos reutilizaveis, sem confundir isso com memoria canonica
- **context compaction disciplinada**
  - fonte principal: Qwen-Agent, Letta, Hermes
  - valor: gerenciar contexto longo sem depender de janela infinita
- **graph/temporal memory**
  - fonte principal: Graphiti e Zep
  - valor: fase futura para relacionamento temporal, fatos mutaveis e queries point-in-time
- **proposal optimization por metrica**
  - fonte principal: DSPy/MIPROv2, TextGrad, EvoAgentX
  - valor: evolucao governada baseada em datasets, traces e metricas

### 5.2 Padroes de alto valor, mas nao para agora

- connectors e project skills de produto ampla;
- compressao inferencial e vector retrieval em escala: fonte principal
  `TurboQuant`; valor para futuro `long-context`, `voice/realtime` pesado e
  retrieval vetorial quando houver pressao real de memoria/latencia;
- desktop bridge generalista;
- cloud async execution como superficie principal;
- auto-adaptacao de pesos;
- auto-modificacao de codigo do proprio nucleo.

---

## 6. Prioridade recomendada de traducao para o JARVIS

Esta priorizacao agora foi convertida em ordem operacional em:

- `docs/architecture/technology-absorption-order.md`

### 6.1 Prioridade alta agora

1. **LangGraph**
   - durable execution, resumability, subgraphs, replay
2. **Mastra**
   - semantica de workflow tipado, snapshots, suspend/resume, eval taxonomy
3. **PydanticAI**
   - contracts, validators, retries, typed outputs
4. **Letta / MemGPT**
   - memory lifecycle vivo, pinned vs archival, memory maintenance
5. **Hermes Agent**
   - skills como memoria procedural, cross-session recall, context compression
6. **DSPy / MIPROv2**
   - compile/eval loops e proposal optimization no `evolution-lab`

### 6.2 Prioridade media

1. **OpenAI Agents SDK**
   - handoff semantics, tracing grammar, session adapters
2. **OpenHands**
   - coding substrate e sandbox patterns para especialistas de software
3. **Graphiti / Zep**
   - memoria temporal/relacional como fase seguinte de profundidade
4. **Qwen-Agent**
   - context management e MCP patterns
5. **browser-use**
   - browser operator especializado
6. **AutoGPT Platform**
   - triggers, webhooks e blocos reutilizaveis para automacoes futuras

### 6.3 Prioridade baixa ou deferred

1. **OpenClaw**
   - excelente referencia de gateway e skills, mas nao e o foco atual
2. **Manus**
   - mais forte como vertical de produto ampla do que como prioridade do baseline
3. **TurboQuant**
   - promissor para compressao de `KV cache` e retrieval vetorial, mas ainda
     sem consumidor canonico no JARVIS atual
4. **SEAL**
   - relevante como pesquisa, prematuro para o sistema atual
5. **Darwin Godel Machine**
   - relevante como horizonte de autoevolucao forte, ainda muito cedo

---

## 7. O que nao pode ser confundido daqui para frente

- `Hermes Agent` nao e a referencia principal de autoevolucao profunda; ele e
  principalmente referencia de runtime persistente, skills e memoria procedural.
- `Mem0` nao e a resposta natural para toda memoria do JARVIS; seu melhor valor
  esta em ownership/scoping, nao em substituir o `memory_registry`.
- `TurboQuant` nao e resposta para memoria canonica nem para os gaps centrais
  do nucleo; seu valor esta em compressao inferencial e retrieval vetorial de
  escala tardia.
- `Mastra` nao compete com o nucleo cognitivo do JARVIS; ela e uma referencia
  forte de semantica de workflow e observabilidade.
- `OpenHands` nao deve virar identidade do sistema; ele e substrate de coding.
- `DSPy`, `TextGrad`, `AFlow` e `EvoAgentX` importam mais como algoritmos de
  refinamento do que como produtos finais.
- `SEAL` e `Darwin Godel Machine` sao horizonte de pesquisa, nao backlog do
  ciclo atual.

---

## 8. Fontes oficiais principais desta revisao

### 8.1 Orquestracao e workflow

- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- LangGraph interrupts: https://docs.langchain.com/oss/javascript/langgraph/interrupts
- OpenAI Agents SDK handoffs: https://openai.github.io/openai-agents-python/handoffs/
- OpenAI Agents SDK sessions: https://openai.github.io/openai-agents-python/sessions/
- OpenAI Agents SDK guardrails: https://openai.github.io/openai-agents-python/guardrails/
- OpenAI Agents SDK tracing: https://openai.github.io/openai-agents-python/tracing/
- CrewAI docs: https://docs.crewai.com/
- CrewAI memory: https://docs.crewai.com/en/concepts/memory
- CrewAI flows: https://docs.crewai.com/en/concepts/flows
- Microsoft Agent Framework overview: https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview
- Microsoft Agent Framework workflows: https://learn.microsoft.com/en-us/agent-framework/workflows/
- Mastra overview: https://mastra.ai/en/docs/evals/overview
- Mastra suspend/resume: https://mastra.ai/en/docs/workflows/suspend-and-resume
- Mastra runtime context: https://mastra.ai/en/docs/agents/runtime-variables

### 8.2 Coding agents e computer use

- OpenHands agents: https://docs.openhands.dev/openhands/usage/agents
- OpenHands sandboxes: https://docs.openhands.dev/openhands/usage/runtimes/overview
- OpenHands API sandbox: https://docs.openhands.dev/sdk/guides/agent-server/api-sandbox
- Browser Use quickstart: https://docs.browser-use.com/
- Browser Use open-source quickstart: https://docs.browser-use.com/open-source/quickstart
- Open Interpreter intro: https://docs.openinterpreter.com/
- Open Interpreter Computer API: https://docs.openinterpreter.com/code-execution/computer-api
- Anthropic computer use: https://docs.anthropic.com/en/docs/build-with-claude/computer-use

### 8.3 Memoria, contexto e continuidade

- Letta stateful agents: https://docs.letta.com/guides/core-concepts/stateful-agents/
- Letta memory: https://docs.letta.com/letta-code/memory/
- Letta shared memory: https://docs.letta.com/guides/core-concepts/memory/shared-memory/
- Zep concepts: https://help.getzep.com/v2/concepts
- Zep sessions: https://help.getzep.com/v2/sessions
- Zep facts and summaries: https://help.getzep.com/chat-history-memory/facts
- Graphiti overview: https://help.getzep.com/graphiti/getting-started/overview
- Graphiti product page: https://www.getzep.com/product/open-source
- Mem0 OSS overview: https://docs.mem0.ai/open-source/overview
- Mem0 add memories: https://docs.mem0.ai/api-reference/memory/add-memories
- Hermes Agent README: https://raw.githubusercontent.com/NousResearch/hermes-agent/main/README.md
- Hermes features overview: https://hermes-agent.nousresearch.com/docs/user-guide/features/overview
- Hermes tools: https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/
- Hermes skills: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/
- Hermes memory: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/
- Hermes delegation: https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns/
- Hermes architecture: https://hermes-agent.nousresearch.com/docs/developer-guide/architecture/
- OpenClaw overview: https://docs.openclaw.ai/
- OpenClaw skills: https://docs.openclaw.ai/skills
- OpenClaw memory overview: https://docs.openclaw.ai/concepts/memory
- OpenClaw architecture: https://clawdocs.org/architecture/overview/
- Manus docs: https://manus.im/docs
- Manus API docs: https://open.manus.im/docs

### 8.4 Contratos, tools e previsibilidade

- PydanticAI agents: https://ai.pydantic.dev/agents/
- PydanticAI output: https://ai.pydantic.dev/output/
- PydanticAI retries: https://ai.pydantic.dev/retries/
- PydanticAI multi-agent: https://ai.pydantic.dev/multi-agent-applications/
- Qwen-Agent overview: https://qwenlm.github.io/Qwen-Agent/en/guide/
- Qwen-Agent RAG: https://qwenlm.github.io/Qwen-Agent/en/guide/core_moduls/rag/
- Qwen-Agent context management: https://qwenlm.github.io/Qwen-Agent/en/guide/core_moduls/context/
- Qwen-Agent MCP: https://qwenlm.github.io/Qwen-Agent/en/guide/core_moduls/mcp/
- smolagents docs: https://huggingface.co/docs/smolagents/en/index
- smolagents agents: https://huggingface.co/docs/smolagents/en/reference/agents

### 8.5 Autoaperfeicoamento e evolucao

- DSPy home and MIPROv2: https://dspy.ai/
- TextGrad official repo: https://github.com/zou-group/textgrad
- AFlow paper page: https://huggingface.co/papers/2410.10762
- EvoAgentX docs: https://evoagentx.github.io/EvoAgentX/
- EvoAgentX repo: https://github.com/EvoAgentX/EvoAgentX
- SEAL repo: https://github.com/Continual-Intelligence/SEAL
- SEAL paper page: https://huggingface.co/papers/2506.10943
- Darwin Godel Machine paper page: https://huggingface.co/papers/2505.22954

### 8.6 Infraestrutura inferencial e vector retrieval

- Google Research blog on TurboQuant: https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
- TurboQuant paper: https://arxiv.org/abs/2504.19874
