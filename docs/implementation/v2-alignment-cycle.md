# V2 Alignment Cycle

## 1. Objetivo do ciclo atual

Este documento define o próximo ciclo rolante do `v2`.

Foco único do ciclo:

- `alinhar o runtime do sistema aos eixos do Documento-Mestre sem ampliar superfícies cedo demais`

Ele sucede o primeiro corte do `v2` e assume que o salto estrutural minimo de
especialistas subordinados já foi provado.

Fontes de direcao:

- `HANDOFF.md`
- `docs/implementation/v2-cycle-closure.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `documento_mestre_jarvis.md`

Status desta versão do ciclo:

- Sprint 1 concluída;
- Sprint 2 concluída;
- Sprint 3 concluída;
- Sprint 4 concluída;
- Sprint 5 concluída;
- Sprint 6 concluída.

---

## 2. Regra de leitura

Este documento é a fonte oficial do que entra em execução agora para o próximo
recorte do `v2`.

Ele deve ser lido junto da matriz de aderência para responder:

- qual eixo do mestre a sprint move;
- qual lacuna dominante ela fecha;
- o que continua conscientemente fora de cobertura apos a entrega.

---

## 3. Conexao entre eixos e tecnologias

Regra estrutural deste ciclo:

- `dominios`, `mentes` e `memorias` sao eixos canônicos do sistema;
- tecnologias entram apenas como mecanismos de implementacao desses eixos;
- nenhuma tecnologia redefine a ontologia do JARVIS;
- toda absorcao deve responder qual eixo melhora, em que recorte entra e o que continua soberano no nucleo.

Leitura correta dos eixos:

- `dominios`: sobre o que o sistema pensa, recupera, roteia e especializa;
- `mentes`: como o sistema raciocina, arbitra tensoes e combina modos cognitivos;
- `memorias`: o que o sistema preserva, recupera, compartilha e promove ao longo do tempo.

### 3.1 Matriz completa de conexao por tecnologia

| Tecnologia | Eixo dominante | Como se conecta a `dominios`, `mentes` e `memorias` | Regra de absorcao no sistema |
| --- | --- | --- | --- |
| `LangGraph` | `mentes` | ajuda o fluxo stateful da arbitragem, checkpoints, replay e handoffs sem redefinir o mapa cognitivo | entra por subfluxos e coordenacao stateful; nao substitui o nucleo |
| `OpenAI Agents SDK` | `mentes` | ajuda handoffs, tools e tracing entre camadas cognitivas e especialistas | entra como complemento pontual; nao vira runtime soberano |
| `CrewAI` | `mentes` | serve como benchmark de delegacao e times de agentes, util para comparar composicao entre especialistas | fica como referencia arquitetural; nao entra no nucleo agora |
| `Microsoft Agent Framework` | `mentes` | serve como benchmark moderno de orquestracao agentic e integracao de ecossistema | fica como referencia arquitetural; nao entra no runtime atual |
| `AutoGen` | `mentes` | ajuda a comparar multiagentes e conversa entre agentes | permanece como benchmark historico, sem absorcao direta |
| `PostgreSQL` | `memorias` | e a base de persistencia das classes de memoria e do estado relacional do sistema | ja e backbone operacional oficial |
| `pgvector` | `memorias` | pode ampliar memoria semantica e retrieval mais profundo por dominio | continua deferido; so entra quando houver consumidor canonico real |
| `LangSmith` | `mentes` | ajuda tracing e evals da coordenacao interna, inclusive handoffs e subfluxos | permanece complementar; trilha local segue primaria |
| `OpenAI Realtime / Voice` | `mentes` | impacta a superficie de interacao, nao a ontologia de dominios, mentes ou memorias | manter deferido enquanto superficie oficial |
| `OpenHands` | `dominios` | conecta um dominio explicito de software a um especialista subordinado com memoria mediada pelo nucleo | entra por shadow mode e dominio explicito; nunca como segunda identidade |
| `browser-use` | `dominios` | pode ampliar dominios operacionais ligados a browser e computer use | fica em laboratorio; so entra com governanca forte e foco de fase |
| `Open Interpreter` | `dominios` | pode ampliar dominios operacionais ligados a shell e operacao local | fica em laboratorio; nao entra no corte atual |
| `Claude Computer Use` | `dominios` | serve como benchmark conceitual de operacao computacional | permanece como referencia, sem absorcao direta |
| `Letta / MemGPT` | `memorias` | ajuda a pensar memoria persistente orientada a agente e estado cognitivo | fica em laboratorio; nao substitui a politica propria de memoria |
| `Zep` | `memorias` | pode ajudar memoria contextual, temporal e continuidade por historico | entra so como experimento delimitado de memoria, nao como camada total |
| `Graphiti` | `memorias` | pode ajudar memoria relacional e timeline entre missoes e dominios relacionados | entra so como experimento relacional delimitado |
| `LlamaIndex` | `dominios` | pode ajudar ingestao e retrieval complementar por dominio | fica em laboratorio; nao governa o conhecimento ativo do nucleo |
| `Hermes Agent` | `memorias` | inspira runtime persistente, skills e memoria viva, com impacto em especialistas e estado | permanece como inspiracao arquitetural, sem absorcao direta agora |
| `OpenClaw` | `dominios` | inspira a camada de assistencia operacional e canais | permanece como referencia arquitetural para fase futura |
| `Manus` | `dominios` | ajuda a comparar assistencia operacional ampla e fluxos de execucao | fica como benchmark conceitual, fora do corte atual |
| `PydanticAI` | `mentes` | ajuda contratos previsiveis entre nucleo, memoria, dominio e especialistas | entra por contratos e outputs delimitados, nao como fundacao total do sistema |
| `Qwen-Agent` | `mentes` | ajuda a comparar modularidade leve e estrutura de agentes | fica em laboratorio como referencia secundaria |
| `smolagents` | `mentes` | ajuda a comparar composicao leve de tools e contratos | fica como benchmark conceitual |
| `TextGrad` | `memorias` | afeta mais a camada evolutiva e o ajuste de artefatos cognitivos persistidos | permanece em laboratorio offline, fora do nucleo |
| `DSPy / MIPROv2` | `mentes` | ajuda a comparar otimizacao de programas LM e cadeias cognitivas avaliaveis | permanece em laboratorio offline |
| `AFlow` | `mentes` | ajuda a comparar otimizacao automatizada de workflows e pipelines internos | permanece em laboratorio offline |
| `EvoAgentX` | `mentes` | ajuda a pensar evolucao automatizada de workflows e composicoes agentic | permanece em laboratorio offline |
| `SEAL` | `memorias` | afeta a camada evolutiva mais agressiva e a adaptacao persistente | segue deferido para fase futura, fora do nucleo atual |
| `Darwin Godel Machine` | `mentes` | afeta a camada evolutiva mais agressiva com mudanca de codigo | segue deferido para fase futura, fora do nucleo atual |

### 3.2 Regras operacionais de leitura

- tecnologias de `domínios` devem responder como melhoram roteamento, corpus ativo ou especialização subordinada;
- tecnologias de `mentes` devem responder como melhoram composição, arbitragem, contracts ou fluxo stateful;
- tecnologias de `memórias` devem responder como melhoram classes de memória, persistência, recuperação, compartilhamento ou promoção;
- se uma tecnologia não melhora nenhum desses eixos de forma verificável, ela não entra no backlog do ciclo.

### 3.3 Por que este ciclo vem antes da absorção ampla

Este ciclo existe para fortalecer os eixos soberanos do JARVIS antes de qualquer absorção tecnológica mais agressiva.

Leitura correta:

- primeiro `domínios`, `memórias` e `mentes` precisam governar o runtime com gramática própria;
- só depois a absorção de frameworks, repositórios, algoritmos ou camadas evolutivas pode acontecer sem dissolver a identidade do sistema;
- a função do ciclo atual é preparar o núcleo para absorver valor arquitetural do ecossistema sem virar uma colagem de tecnologias externas.

---

## 4. Sequencia oficial das sprints

1. Sprint 1 - soberania do registry de dominios no runtime
2. Sprint 2 - politicas operacionais por classe de memoria
3. Sprint 3 - composicao e arbitragem explicita entre mentes
4. Sprint 4 - identidade auditavel do nucleo em planejamento e sintese
5. Sprint 5 - gates de aderencia por eixo em evals e observabilidade
6. Sprint 6 - fechamento do ciclo de alinhamento do `v2`

---

## 5. Sprint 1

Status:

- concluida
- eixo principal do mestre: `dominios`
- lacuna dominante fechada: registry existente sem soberania plena sobre roteamento e ativacao
- continua fora de cobertura: mapeamento total de todas as maturidades de dominio ao mesmo tempo

### Objetivo

Tornar o registry de dominios a fonte primaria de roteamento do runtime, do
subset ativo do corpus e da relacao `dominio -> especialista`.

### Entregas obrigatorias

- roteamento do `knowledge-service` soberano pelo registry;
- separacao explicita entre `dominio principal`, `dominio operacional` e `dominio meta`;
- ativacao do subset runtime sempre derivada do registry;
- shadow specialist ligado a dominio canonico sem heuristica solta residual.

### Resultado registrado nesta rodada

- `shared/domain_registry.py` foi criado como modulo soberano do registry de dominios, analogo a `memory_registry.py` e `mind_registry.py`, expondo `CANONICAL_DOMAIN_REGISTRY`, `RUNTIME_ROUTE_REGISTRY`, `RUNTIME_ELIGIBLE_ROUTES`, `SHADOW_SPECIALIST_ROUTES`, `FALLBACK_RUNTIME_ROUTE` e funcoes utilitarias `is_shadow_route`, `resolve_route` e `canonical_scopes_for_route`;
- `knowledge-service` passou a derivar o prior de intencao de `domain_scope` dos canonical_refs de cada rota, removendo o dicionario hardcoded de pesos; dominios com `maturity=canonical_only` sao excluidos do runtime; o fallback e derivado do registry (`FALLBACK_RUNTIME_ROUTE`); os pesos de matching foram nomeados como constantes do modulo;
- `specialist-engine` passou a verificar `is_shadow_route()` antes de acionar `especialista_software_subordinado`, eliminando a heuristica residual de shadow mode;
- `cognitive-engine` passou a usar `FALLBACK_RUNTIME_ROUTE` em vez de string hardcoded no fallback de dominios ativos;
- todos os testes dos tres modulos passam sem regressao; dois testes de terceiros (`orchestrator-service` e benchmark de knowledge) foram recalibrados para refletir o novo comportamento soberano do registry.

---

## 6. Sprint 2

Status:

- concluída
- eixo principal do mestre: `memórias`
- lacuna dominante fechada: registry formal promovido a política operacional por classe
- continua fora de cobertura: plenitude do sistema vivo das 11 memórias

### Objetivo

Transformar o registry de memórias em política operacional por classe, indo
além de continuidade, missão e relacional.

### Resultado registrado nesta rodada

- `shared/memory_registry.py` passou a definir prioridade de recovery, prioridade de compartilhamento, `sharing_mode` e `write_policy` por classe de memória;
- `memory-service` passou a compor recovery, compartilhamento com especialistas e contexto relacional usando políticas explícitas por classe;
- `memory-service/repository` passou a persistir políticas por classe no contexto compartilhado com especialistas, em `sqlite` e `PostgreSQL`;
- `observability-service` passou a exigir coerência por classe para classificar `memory_alignment_status` como `healthy`;
- `knowledge-service` foi alinhado ao loader compartilhado de domínios, reduzindo duplicação estrutural paralela ao endurecimento do eixo de memória.

## 7. Sprint 3

Status:

- concluída
- eixo principal do mestre: `mentes`
- lacuna dominante fechada: arbitragem antes implícita agora governada pelo registry soberano
- continua fora de cobertura: ecologia completa das 24 mentes em maturidade plena

### Objetivo

Promover o registry de mentes para composição e arbitragem soberanas do
runtime.

### Resultado registrado nesta rodada

- `shared/mind_registry.py` passou a governar prioridade, afinidades e limites formais da arbitragem entre mentes;
- `cognitive-engine` passou a selecionar mente primária, mentes de apoio e mentes suprimidas a partir da política do registry, com tensão dominante e resumo explícito de arbitragem;
- `orchestrator-service` passou a publicar o contexto cognitivo enriquecido como parte observável do fluxo principal;
- `observability-service` passou a auditar `mind_alignment_status`, tornando a aderência do eixo de mentes verificável por request.

## 8. Sprint 4

Status:

- concluída
- eixo principal do mestre: `identidade, missão, princípios e filosofia`
- lacuna dominante fechada: identidade deixou de ser implícita e passou a ser rastreável ao longo do fluxo
- continua fora de cobertura: expansão ampla de superfícies

### Objetivo

Transformar identidade e unidade do núcleo em critério observável de
planejamento, governança e síntese.

### Resultado registrado nesta rodada

- `identity-engine` passou a expor assinatura do núcleo, postura, foco de princípios e guardrails compatíveis com a governança do sistema;
- `governance-service` passou a receber `identity_mode`, `identity_signature` e `response_style`, registrando `identity_guardrail` como parte da decisão;
- `orchestrator-service` passou a propagar sinais explícitos de identidade em `directive_composed`, `plan_governed` e `response_synthesized`;
- `observability-service` passou a auditar `identity_alignment_status`, preparando a Sprint 5 para usar esse eixo como gate explícito de aderência.

## 9. Sprint 5

Status:

- concluída
- eixo principal do mestre: `observabilidade, validacao e evals`
- lacuna dominante fechada: aderência por eixo promovida a gate explícito em piloto, comparação e sandbox
- continua fora de cobertura: fechamento formal do ciclo e decisão final de promoção

### Objetivo

Usar observabilidade e evals para julgar aderencia do runtime aos eixos do
mestre, e nao apenas utilidade local.

### Resultado registrado nesta rodada

- `tools/internal_pilot_support.py` passou a carregar `mind_alignment_status`, `identity_alignment_status` e `axis_gate_status` como parte do resultado estruturado de cada cenario;
- `tools/internal_pilot_report.py` passou a expor os cinco eixos de aderencia e o gate agregado de eixo por request;
- `tools/compare_orchestrator_paths.py` passou a comparar os cinco eixos, exigir gate saudavel para `candidate_ready_for_eval_gate` e publicar taxa explicita de aprovacao por eixo;
- `evolution-lab` e `tools/evolution_from_pilot.py` passaram a tratar `mind`, `identity` e `axis_gate` como sinais formais de proposta e comparacao sandbox-only.

---

## 10. Sprint 6

Status:

- concluída
- eixo principal do mestre: `implementação, operação, release e incidentes`
- lacuna dominante fechada: ciclo encerrado com decisão formal de continuidade baseada em aderência por eixo
- continua fora de cobertura: tudo o que permanece corretamente deferido para o próximo corte do `v2`

### Objetivo

Fechar o ciclo de alinhamento do `v2`, classificar o backlog imediato e abrir o próximo corte sem reabrir superfícies cedo demais.

### Resultado registrado nesta rodada

- `tools/close_alignment_cycle.py` passou a gerar o artefato formal de encerramento do `v2-alignment-cycle`, usando observabilidade, comparação local e backlog classificado por `next_cut`, `deferred` e `vision`;
- `tools/compare_orchestrator_paths.py` passou a persistir seu artefato default em `.jarvis_runtime/path_comparison_v2/`, alinhando o fluxo real de comparação ao fechamento do ciclo;
- o encerramento formal do ciclo passou a abrir explicitamente o próximo corte do `v2` com quatro frentes: especialistas de domínio além do shadow mode, consumidores canônicos de memória mais rica, absorção tecnológica governada em sandbox e promoção sempre subordinada a gates por eixo;
- `computer use` amplo, voz oficial, `pgvector` como fundação obrigatória e autoevolução promotiva agressiva permanecem formalmente deferidos.
