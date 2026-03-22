# CHANGELOG

Este changelog registra mudanças relevantes na documentação canônica, nos artefatos de continuidade e nas decisões estruturais do projeto `jarvis`.

Ele **não** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel é manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudança importa.

---

## 2026-03-22

### Execução das Sprints 2 e 3 do ciclo pós-v1

- concluída a Sprint 2 com recuperação e ranking determinístico de continuidade relacionada;
- `memory-service` passou a decidir de forma reproduzível entre missão ativa, loops abertos e missão relacionada, com recomendação explícita de continuidade;
- `planning-engine` passou a distinguir explicitamente `continuar`, `encerrar`, `reformular` e `retomar`, incluindo motivo de continuidade no plano deliberativo;
- `orchestrator-service` passou a registrar o evento `continuity_decided`, tornando a escolha de continuidade observável por `request_id`;
- `governance-service` passou a deferir retomada relacionada quando ela disputa direção com loops ainda abertos da missão ativa;
- `synthesis-engine` passou a refletir a retomada relacionada também no caminho governado, sem esconder a decisão no texto final;
- removido `POC` da nomenclatura técnica da trilha opcional de `LangGraph`, com rename para `langgraph_flow.py`, `LangGraphFlowRunner` e `handle_input_langgraph_flow()`.

### Refinamento do fluxo de análise e incorporação tecnológica

- ampliado `docs/architecture/technology-study.md` com perguntas mínimas obrigatórias de estudo, fluxo oficial de incorporação, formas corretas de entrada no sistema e relação explícita com programa, sprint cycle e handoff;
- explicitado no `technology-study.md` quem conduz a análise, como o agente deve estudar a tecnologia, como deve incorporar por recorte, quais evidências precisa produzir e quais condições bloqueiam promoção;
- reforçado `HANDOFF.md` com a regra curta de promoção tecnológica para evitar absorção direta de tecnologia externa no núcleo sem lacuna concreta, classificação e evidência.

### Revisao documental ampla do repositorio

- revisados e atualizados os documentos centrais e os derivados mais importantes para refletir o estado real do projeto: `v1` encerrado, `pos-v1` aberto e Sprint 2 como frente ativa;
- reescrito `HANDOFF.md` para reduzir historico excessivo, atualizar o commit de referencia e consolidar a retomada operacional;
- reescrito `README.md` para apresentar o baseline atual e a leitura correta da fase do projeto;
- atualizados documentos operacionais, executivos, de implementacao e de arquitetura para remover contradicoes sobre fechamento do `v1`, `GO CONDICIONAL`, porta local do PostgreSQL e foco do ciclo atual;
- refinado `docs/architecture/technology-study.md` para refletir melhor o peso atual de `CrewAI`, `AutoGen`, `Microsoft Agent Framework` e da camada de referencias arquiteturais por funcao.

### Restauracao de contexto apos enxugamento excessivo

- reforcado `HANDOFF.md` com um bloco curto de baseline materializado para preservar visibilidade operacional sem voltar ao historico gigante;
- ampliado `docs/operations/v1-operational-baseline.md` com criterios de ampliacao ou contencao e com a lista dos artefatos operacionais do baseline;
- ampliado `docs/implementation/implementation-strategy.md` com uma leitura historica mais concreta da sequencia que fechou o `v1` e das capacidades operacionais que emergiram desse caminho.

### Referencias arquiteturais por funcao formalizadas no Documento-Mestre

- complementado `documento_mestre_jarvis.md` com uma camada explicita de referencias arquiteturais por funcao, separando o eixo de posicionamento na stack do eixo de papel arquitetural;
- formalizada a leitura por `referencia central`, `referencia secundaria` e `benchmark conceitual` para orquestracao, agente de software, computer use, memoria persistente, assistencia operacional e contratos;
- atualizado `docs/architecture/technology-study.md` para refletir os dois eixos de decisao e ampliar a matriz de referencias externas;
- atualizado `docs/documentation/estrutura_de_documentos_derivados.md` para explicitar que o Documento-Mestre guarda tanto o posicionamento oficial de tecnologias quanto as referencias arquiteturais oficiais por funcao;
- atualizado `docs/executive/master-summary.md` e `HANDOFF.md` para refletir a nova regra documental e arquitetural.

### Execucao da Sprint 1 do ciclo rolante

- concluido o modelo interno minimo de continuidade entre missoes relacionadas;
- adicionados contratos compartilhados minimos para candidatas e contexto de continuidade relacionada;
- `memory-service` passou a recuperar candidatas de missao relacionada dentro da mesma sessao, inclusive no primeiro turno de uma nova missao;
- `orchestrator-service` passou a repassar a melhor candidata relacionada para o `planning-engine`;
- `planning-engine` passou a registrar a fonte da continuidade no plano deliberativo e a explicitar alvo e razao da continuidade relacionada na racionalizacao;
- adicionados testes de memoria, planejamento e orquestracao para travar a leitura de missao relacionada sem quebrar a API publica do `v1`.

### Sistema de planejamento em duas camadas ate `v3`

- criado `docs/roadmap/programa-ate-v3.md` como contrato de direcao do `pos-v1` ate `v3`, separando `pos-v1`, `v1.5`, `v2` e `v3` por objetivos, gates e limites;
- criado `docs/implementation/post-v1-sprint-cycle.md` como plano rolante oficial das proximas `6` sprints, com foco total em `continuidade profunda entre missoes`;
- formalizado o sistema documental em tres papeis: `HANDOFF.md` para retomada operacional, `programa-ate-v3.md` para direcao macro e `post-v1-sprint-cycle.md` para execucao imediata;
- atualizadas as referencias em `HANDOFF.md`, `README.md` e `docs/documentation/estrutura_de_documentos_derivados.md` para tornar o novo sistema de planejamento a leitura oficial do proximo ciclo.

---

## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
- explicitado que `Hermes Agent` entra no estudo como referencia de continuidade e runtime persistente, nao como referencia principal de autoaperfeicoamento;
- explicitado que a trilha de autoaperfeicoamento continua mais associada a `DSPy / MIPRO`, `TextGrad`, `AFlow`, `EvoAgentX`, `SEAL` e `Darwin Godel Machine`, ficando fora do foco imediato do primeiro ciclo pos-`v1`.

### Pacote final de robustez do `v1` e `jarvis-console`

- implementado `tools/operational_artifacts.py` para gerar `baseline snapshot`, `containment drill` e `incident evidence` em `.jarvis_runtime/operational/`;
- ampliado `tools/validate_v1.py` para validar coerencia entre missao, memoria e governanca, gerar snapshot do baseline e executar smoke do `jarvis-console`;
- ampliado `tools/go_live_internal_checklist.py` para validar `defer_for_validation` por conflito de missao, coerencia de `open_loops`, evidencia operacional e drill minimo de contencao/rollback;
- `tools/run_internal_pilot.py` passou a atualizar tambem `latest_pilot.json` e `latest_pilot.md`;
- criado `apps/jarvis_console/` como interface textual minima do `v1`, com modos `ask` e `chat` sobre o `orchestrator-service`;
- endurecido o `memory-service` para preservar o estado de missao aceito quando um turno posterior e bloqueado ou adiado para validacao;
- ampliado o `observability-service` com geracao de `incident evidence` para requests anomalas ou governadas;
- adicionados testes do console, dos artefatos operacionais, da preservacao de missao no orquestrador e da evidencia operacional;
- validados `pytest -q`, `ruff check .`, `python tools/check_mojibake.py .`, `python tools/validate_v1.py --profile development`, `python tools/validate_v1.py --profile controlled`, `python tools/go_live_internal_checklist.py --profile development`, `python tools/go_live_internal_checklist.py --profile controlled`, `python tools/run_internal_pilot.py --profile controlled` e `python tools/internal_pilot_report.py --limit 10`.

---
## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
### Incremento curto de continuidade entre missoes

- criado `docs/implementation/mission-continuity-final-increment.md` como plano executavel do ultimo incremento cognitivo curto antes do fechamento disciplinado do `v1`;
- ampliado o `planning-engine` para usar `mission_goal` e `mission_recommendation`, explicitar conflito entre o pedido atual e a missao ativa e escolher entre `continuar`, `encerrar` e `reformular` com mais rigor;
- ajustado o `memory-service` para priorizar hints de continuidade de missao na recuperacao e persistir um `identity_continuity_brief` mais util entre turnos;
- ajustado o `orchestrator-service` para repassar objetivo de missao e recomendacao anterior ao planejamento;
- ajustado o `synthesis-engine` para refletir continuidade, fechamento ou reformulacao da missao sem expor o pipeline interno;
- atualizados os testes de planejamento, sintese, memoria e orquestracao; `pytest -q`, `ruff check` e `python tools/validate_v1.py --profile development` passaram apos a implementacao.

---
## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.
### Enxugamento e reorganizacao de `docs/`

- consolidados `docs/operations/go-live-readiness.md`, `docs/operations/v1-go-no-go-decision.md` e `docs/operations/v1-production-controlled.md` em `docs/operations/v1-operational-baseline.md`;
- consolidado o estudo de tecnologia em `docs/architecture/technology-study.md`, substituindo a separacao entre matriz geral e fase 1 aplicada;
- movidos `docs/implementation/sprint-1-plan.md`, `docs/implementation/first-milestone-plan.md` e `docs/operations/internal-pilot-plan.md` para `docs/archive/`;
- movidos `docs/architecture/specialists-v2.md` e `docs/architecture/voice-runtime.md` para `docs/future/`;
- removidos o placeholder `docs/adr/README.md` e a revisao transitoria `docs/documentation/revisao_do_conjunto_documental_2026-03-20.md`;
- atualizadas as referencias vivas em `HANDOFF.md`, `docs/operations/incident-response.md`, `docs/roadmap/v1-roadmap.md` e `docs/documentation/estrutura_de_documentos_derivados.md`.

### Sincronização documental com o estado atual do repositório

- atualizados os documentos executivos, operacionais, arquiteturais e de implementação para refletir o ciclo cognitivo mais unitário já implementado no núcleo;
- atualizados os documentos de `go/no-go`, readiness e piloto para refletir que o `internal pilot` controlado já foi executado com resultado saudável;
- mantida a leitura de `GO CONDICIONAL`, mas com foco deslocado de "executar o piloto" para "consolidar a leitura do piloto e decidir o fechamento do v1";
- a revisao do conjunto documental foi absorvida pela propria reorganizacao de `docs/`, com consolidacao, arquivamento e separacao entre material ativo, historico e futuro;
- preservado o papel canônico de `documento_mestre_jarvis.md` como norte da visão de produto.

---

## 2026-03-19

### Internal pilot executável, comparação de paths e proposals evolutivas

- adicionada auditoria operacional de fluxo ao `observability-service`, com trilha mínima obrigatória, flags automáticas de anomalia e visão de requests recentes;
- ampliado `tools/internal_pilot_report.py` para refletir `trace_status`, `anomaly_flags` e `source_services` por request;
- criado `tools/internal_pilot_support.py` para unificar cenários, bootstrap e coleta estruturada do `internal pilot`;
- criado `tools/run_internal_pilot.py` para executar a janela mínima do piloto e persistir evidência local em `JSON` e `Markdown`;
- criado `tools/compare_orchestrator_paths.py` para comparar baseline e fluxo opcional de `LangGraph` nos mesmos cenários;
- ampliado o `evolution-lab` com entrada de `FlowEvaluationInput` e helpers para comparar sinais reais do piloto;
- criado `tools/evolution_from_pilot.py` para transformar trilhas recentes e comparações de paths em proposals sandbox-only;
- ampliado o corpus curado do `knowledge-service` com domínios de `observability` e `pilot_operations`, mantendo retrieval determinístico;
- atualizados testes de observabilidade, `internal_pilot_report`, `knowledge-service`, `evolution-lab` e utilitários do piloto.

### Preparação do internal pilot e fluxo experimental de LangGraph

- adicionado `tools/internal_pilot_report.py` para resumir trilhas recentes por `request_id`, status operacional, decisão de governança e eventos obrigatórios ausentes;
- criado `docs/operations/internal-pilot-plan.md` como plano mínimo da primeira janela controlada após o `GO CONDICIONAL`;
- endurecido o `JsonlAgenticMirrorAdapter` para espelhar `trace tree` local com root trace e child runs, permitindo validar a estrutura de rastreabilidade mesmo sem credencial externa;
- endurecido `tools/go_live_internal_checklist.py` para exigir árvore de trace no espelhamento agentic;
- adicionada integração experimental opcional de `LangGraph` ao `orchestrator-service`, preservando `handle_input()` como caminho principal e expondo `handle_input_langgraph_flow()` como rota experimental sem breaking change;
- adicionado extra opcional `langgraph` no `pyproject.toml` para permitir o fluxo experimental do orquestrador sem contaminar o bootstrap padrão do `v1`.

### LangSmith complementar e ADR de LangGraph

- endurecido o adaptador `LangSmith` do `observability-service` para espelhar fluxos como `trace tree` por `request_id`, com root trace, child runs e metadata consistente;
- adicionados suporte a `LANGSMITH_ENDPOINT` e `LANGSMITH_WORKSPACE_ID` para cloud, hybrid ou self-hosted;
- ampliados os testes do `observability-service` para validar agrupamento por request e estrutura da árvore de traces;
- criado `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` para formalizar a absorção parcial de `LangGraph` como próximo salto estrutural do núcleo, sem reescrita ampla imediata do `v1`.

### Estudo aplicado da stack principal

- criado `docs/architecture/technology-study-phase1-core-stack.md` para registrar a Fase 1 do estudo de reaproveitamento tecnológico;
- consolidada a leitura aplicada de `LangGraph`, `PostgreSQL + pgvector` e `LangSmith` contra o estado real do repositório;
- registrada a decisão refinada desta fase: `LangSmith` como complemento imediato do ciclo de `internal pilot`, `LangGraph` como próximo salto estrutural do núcleo sem reescrita ampla imediata, e `pgvector` aprovado arquiteturalmente mas fora do caminho crítico até existir consumidor semântico real.

### Ciclo deliberativo do núcleo

### Memória semântica curta de missão

- ampliado `MissionStateContract` com `semantic_brief` e `semantic_focus` para representar continuidade de missão em nível semântico curto, sem criar serviço novo;
- atualizados os repositórios `sqlite` e `PostgreSQL` do `memory-service` para persistir e recuperar os novos campos com migração incremental de schema;
- ajustado o `memory-service` para emitir `mission_semantic_brief` e `mission_focus` como hints reutilizáveis no turno seguinte;
- ajustado o `planning-engine` para usar esses sinais como continuidade semântica explícita no plano e no rationale, sem substituir o contexto episódico;
- atualizados testes de memória, planejamento, orquestração e integração PostgreSQL; `pytest -q` voltou a passar integralmente e `ruff check` passou nos arquivos alterados.

- introduzido `DeliberativePlanContract` como artefato estruturado do núcleo para resumir objetivo, etapas, riscos, restrições e recomendacao operacional;
 - ampliado o `executive-engine` para produzir diretiva com confiança, ambiguidade, modo preferido de resposta e controle de execução;
- refeito o fluxo do `orchestrator-service` para operar como `entender -> decompor -> arbitrar -> decidir -> registrar -> responder`, incluindo os eventos `directive_composed`, `plan_built`, `plan_governed` e `clarification_required`;
- expandido o `memory-service` para persistir hints deliberativos de plano e resumo de missão, fortalecendo continuidade entre turnos;
- ajustado o `governance-service` para decidir com base no plano pretendido, não apenas na intenção textual;
- ajustados `operational-service` e `synthesis-engine` para consumir e refletir o plano deliberativo no resultado final;
- atualizados os testes de engines, memória, governança, operação e orquestração; a suite `pytest -q` voltou a passar integralmente.

### Matriz de estudo tecnologico

- criado `docs/architecture/technology-study-matrix.md` para consolidar o estudo de tecnologias, frameworks, algoritmos e repositórios citados no Documento-Mestre;
- organizada a classificação entre base do `v1`, complementos controlados, laboratório, inspiracao arquitetural e itens a deferir para `v2`;
- registrada a ordem recomendada de estudo local de repositórios externos e as regras de segurança para clonar e analisar tecnologias fora do repositório principal do JARVIS.

### Benchmark harness e validação local

 - implementado o pacote `tools/benchmarks/` com harness executável, dataset versionado e artefatos auditáveis em `.jarvis_runtime/benchmarks/`;
 - adicionada exportação `trace view` no `observability-service` para validar compatibilidade com tracing externo sem trocar o envelope interno;
 - criada `.venv` local e instaladas as dependências `.[dev]` para validação do baseline no ambiente do projeto;
 - validado o benchmark local com decisões preliminares: `knowledge -> weighted_deterministic`, `observability -> adotar no v1`, `evolution -> manual_variants`, `memory -> manter baseline atual até validar PostgreSQL`;
- validada a suite completa com `pytest -q` e os arquivos novos com `ruff check`.

### Baseline após benchmark

- promovido o ranking ponderado determinístico para o `knowledge-service`, absorvendo no baseline a melhoria escolhida pelo benchmark;
- ajustado o `evolution-lab` para registrar `manual_variants` como estratégia sandbox prioritária, sem promoção automática;
- ampliados os testes de `knowledge-service` e `evolution-lab` para travar o comportamento promovido ao baseline;
- rerodado o benchmark e validado que `knowledge` agora aparece como `manter baseline atual`, refletindo que a melhoria já foi incorporada ao sistema.

### Readiness de PostgreSQL e benchmark CLI

- adicionado suporte de CLI ao harness de benchmark com `--output-dir`, `--dataset-path`, `--postgres-url` e `--print-json`;
- isolado o escopo do benchmark de memória com identificadores únicos por execução para evitar colisão entre rodadas;
- adicionados testes opcionais de integração PostgreSQL para o `memory-service` e para a trilha de memória do benchmark, com `skip` quando `DATABASE_URL` ou `psycopg` não estiverem disponíveis;
- atualizado o handoff com o fluxo correto de validação da candidata PostgreSQL.

### Validação real de PostgreSQL

- instalado o extra `postgres` na `.venv` local para habilitar o backend real com `psycopg`;
- validado o `memory-service` contra PostgreSQL local com teste de integração dedicado;
- ajustado o harness para isolar execuções por identificadores únicos e medir paridade funcional de forma consistente com o comportamento real da memória;
 - recalibrados os limites de latência do benchmark de memória para comparar `sqlite` com PostgreSQL local sem exigir um teto irreal para um banco operacional;
 - rerodado o benchmark com `DATABASE_URL` real e decisão final `memory -> adotar no v1`;
 - alterado o `docker compose` local do PostgreSQL para publicar em `5433`, evitando conflito com um `postgres.exe` local ativo na máquina.

### Alinhamento dos derivados ao baseline consolidado

- atualizados `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md` e `docs/roadmap/v1-roadmap.md` para refletir o baseline benchmarkado do `v1`;
- atualizados `docs/operations/v1-production-controlled.md` e `docs/operations/go-live-readiness.md` para tratar `PostgreSQL` como backend operacional recomendado e explicitar que a decisão de `go/no-go` ainda está pendente;
- atualizado `docs/architecture/evolution-lab.md` para refletir `manual_variants` como estratégia priorizada no sandbox do `v1`;
- atualizado `docs/executive/v1-scope-summary.md` para registrar o estado atual do `v1` e a pendencia de fechamento para produção controlada.

### Decisão formal de readiness do v1

- criado `docs/operations/v1-go-no-go-decision.md` para registrar a decisão formal de readiness do `v1`;
- registrada a decisão atual como `GO CONDICIONAL` para produção controlada em escopo reduzido;
- atualizado `docs/operations/go-live-readiness.md` para refletir que a decisão de `go/no-go` já foi tomada;
- atualizado `docs/operations/v1-production-controlled.md` para incorporar o estado formal da decisão;
- atualizado `docs/executive/master-summary.md`, que ainda estava atrasado em relação ao estado real do repositório.

---

## 2026-03-18

### Benchmark dirigido do v1

- implementado um harness local único em `tools/benchmarks/` para benchmarkar memória, knowledge, observabilidade e evolution-lab;
- congelado um dataset versionado em `tools/benchmarks/datasets/v1_benchmark_cases.json` com cenários de `planning`, `analysis`, `general_assistance`, bloqueio por governança e continuidade de sessão;
 - adicionada persistência de artefatos auditáveis do benchmark em `JSON` e `Markdown`;
 - adicionada exportação de trace view no `observability-service` para validar compatibilidade com tracing externo sem substituir a trilha interna;
- adicionados testes do harness de benchmark e cobertura da exportação de trace view;
- atualizado o `HANDOFF.md` para refletir o benchmark dirigido como próximo gate do fechamento do `v1`.


### Core v1 baseline

- implementado o primeiro baseline integrado do `v1`, conectando `orchestrator-service`, `memory-service`, `governance-service`, `knowledge-service`, `observability-service`, `operational-service` e `engines/`;
- reduzido o `orchestrator-service` ao papel de coordenador de fluxo, movendo classificação, planejamento, composicao cognitiva e síntese para engines dedicadas;
- preservado `InternalEventEnvelope` como envelope canônico para observabilidade e rastreabilidade do fluxo ponta a ponta.

### Memory Service

- substituido o armazenamento em `dict` por uma camada de repositório persistente;
- adicionado backend local por `sqlite` e suporte a `PostgreSQL` quando `DATABASE_URL` estiver configurada;
 - adicionada persistência de histórico episódico por `session_id`, resumo contextual de sessão e estado mínimo de missão por `mission_id`;
 - ampliados os testes para validar continuidade entre instâncias do serviço e persistência de estado de missão.

### Observability Service

 - implementado o `observability-service` como coletor estruturado de eventos internos;
 - adicionada persistência local da trilha de eventos e consulta por `request_id`, `session_id`, `mission_id` e `correlation_id`;
- integrado o orquestrador a essa trilha persistente em vez de depender apenas do retorno em memória.

### Knowledge e Engines

 - implementado o `knowledge-service` com retrieval local determinístico sobre domínios prioritários do `v1`;
- externalizado o corpus inicial do `knowledge-service` para `knowledge/curated/v1_corpus.json`;
- implementadas as engines de identidade, executivo, planejamento, cognição e síntese;
- ampliada a cobertura de testes para validar classificação de intenção, composição de domínios ativos e síntese final.

### Governance e Operational

- expandido o `governance-service` para suportar `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- adicionadas condições, auditoria e proteção de mutação em memória crítica na decisão de governança;
- expandido o `operational-service` para produzir artefatos textuais reais e preencher `artifacts`, `checkpoints` e `memory_record_hints`.

### Evolution Lab

- implementado o `evolution-lab` como primeiro corte de sandbox evolutivo local;
 - adicionada persistência local de propostas e decisões de comparação entre baseline e candidata;
 - estabelecido regime `sandbox-only`, sem promoção automática, com rollback referenciado ao baseline.

### Bootstrap e validação

- ajustado `tests/conftest.py` para incluir a raiz do repositório no `sys.path` durante a execução dos testes;
- adicionado `conftest.py` na raiz para que testes isolados de serviços e engines carreguem o bootstrap corretamente;
- ajustado `pyproject.toml` para incluir `shared` na descoberta de pacotes do projeto;
- adicionado extra opcional `postgres` em `pyproject.toml` para readiness do backend PostgreSQL;
- desabilitado o cache nativo do `pytest` em configuração para evitar warnings recorrentes de permissão no ambiente local atual;
- validada a suite com `pytest -q` a partir da raiz, sem `PYTHONPATH` manual.

### PostgreSQL readiness

- ampliada a fabrica de memória para normalizar `postgres://` e `postgresql+psycopg://` antes de instanciar o backend PostgreSQL;
- adicionados indices básicos nas tabelas de memória para o caminho local e para o caminho PostgreSQL;
- criado `infra/local-postgres.compose.yml` como infraestrutura local padrao para validar a memória persistente contra PostgreSQL;
- ampliada a cobertura de testes da memória para selecao de backend e parsing de URL.

### Documentação operacional

- atualizados `README.md`, `HANDOFF.md`, `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md`, `docs/roadmap/v1-roadmap.md`, `docs/architecture/evolution-lab.md` e documentos operacionais para refletir o baseline atual do `v1`.

---

## 2026-03-17

### Operational Service

- substituido o esqueleto vazio do `operational-service` por um primeiro serviço funcional mínimo para tarefas seguras e deterministicas;
- adicionado suporte a:
  - execução de `draft_plan`;
  - execução de `produce_analysis_brief`;
  - execução de `general_response`;
  - retorno via `OperationResultContract` com status e outputs estruturados;
- ampliados os testes do `operational-service` para cobrir task suportada e task não suportada.

### Orchestrator Service

- integrado o `orchestrator-service` ao `operational-service`;
- o fluxo permitido agora gera `OperationDispatchContract`, executa a operação e incorpora o resultado na síntese final;
- adicionados os eventos `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliados os testes do `orchestrator-service` para validar despacho operacional permitido e a ausência de operação em fluxos bloqueados.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory -> operational`.

### Validação

- validada por execução Python direta a cadeia completa `orchestrator -> governance -> memory -> operational`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Memory Service

- substituido o esqueleto vazio do `memory-service` por um primeiro serviço funcional mínimo em memória de processo;
- adicionado suporte a:
  - recuperação contextual por sessão com `MemoryRecoveryContract`;
  - registro episódico simples de turno com `MemoryRecordContract`;
  - janela curta de recuperação para o contexto recente da sessão;
- ampliados os testes do `memory-service` para cobrir sessão vazia e continuidade básica de contexto.

### Orchestrator Service

- integrado o `orchestrator-service` ao `memory-service`;
- o fluxo mínimo agora recupera contexto antes da decisão e grava o turno ao final;
- adicionados os eventos `memory_recovered` e `memory_recorded` ao fluxo principal;
- ampliados os testes do `orchestrator-service` para validar recuperação de contexto entre dois turnos da mesma sessão.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory`.

### Validação

- validada por execução Python direta a cadeia `memory-service -> orchestrator-service` com recuperação contextual na segunda interação da mesma sessão;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Governance Service

- substituído o esqueleto vazio do `governance-service` por um primeiro serviço funcional mínimo;
- adicionado suporte a:
  - avaliação de request com base em `InputContract`;
  - classificação determinística de risco;
  - geração de `GovernanceCheckContract`;
  - geração de `GovernanceDecisionContract` com `allow` e `block`;
- ampliados os testes do `governance-service` para cobrir um fluxo de baixo risco e um fluxo sensível bloqueado.

### Orchestrator Service

- removida a política mínima de governança que ainda estava embutida localmente no `orchestrator-service`;
- o `orchestrator-service` agora depende do `governance-service` para obter checagem e decisão;
- preservado o papel do orquestrador como coordenador do fluxo, emissor de eventos e sintetizador de resposta.

### HANDOFF

- atualizado para refletir que o projeto agora possui integração mínima explícita entre `orchestrator-service` e `governance-service`.

### Validação

- validada por execução Python direta a cadeia `governance-service -> orchestrator-service`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-17

### Orchestrator Service

 - substituído o esqueleto vazio do `orchestrator-service` por um primeiro fluxo funcional mínimo;
 - adicionado suporte a:
  - recebimento de `InputContract`;
  - classificação simples de intenção;
  - geração de `GovernanceCheckContract`;
  - avaliação inicial de governança com `allow` e `block`;
  - emissão de eventos internos prioritários;
  - síntese textual básica coerente com a identidade inicial do sistema;
 - ampliados os testes do `orchestrator-service` para cobrir um fluxo de baixo risco e um fluxo sensível bloqueado.

### HANDOFF

- atualizado para refletir que o projeto saiu do estado de esqueleto puro do orquestrador e entrou no primeiro fluxo funcional mínimo.

### Validação

- validado o fluxo do `orchestrator-service` por execução Python direta com carga manual de `sys.path`;
- `pytest` continua pendente por ausência de dependência instalada no ambiente local atual.

---

## 2026-03-16

### Documento-Mestre

- preenchida a seção `236.1 Blocos essenciais`, que estava vazia;
- adicionada a seção `235.5 Continuidade editorial e rastreabilidade` para formalizar a preservação histórica de numeração e o papel de capítulos de `Encaminhamento` e `Próximo passo`;
- ampliada a seção `236.2 Itens que podem virar documentos derivados`;
- substituído o fechamento duplicado do fim do documento por capítulos operacionais e de maturidade;
- enxugado o bloco final do Documento-Mestre para manter no arquivo principal apenas definições canônicas e referências para derivados operacionais;
- enxugados os blocos de roadmap de milestones e de implementação, preservando no arquivo principal a sequência canônica e deslocando a leitura tática para derivados;
- realizado pente fino final para reduzir linguagem exploratória em decisões tecnológicas já consolidadas.

### HANDOFF

- reestruturado para formato operacional de continuidade;
- removida a duplicacao excessiva do conteúdo do Documento-Mestre;
- alinhado ao estado do projeto após a consolidação documental;
- atualizado para refletir a materialização da Sprint 1 no repositório real;
- atualizado novamente para refletir o início da Sprint 2 com base semântica compartilhada mínima.

### Estrutura documental

- consolidada a separação prática entre:
  - `documento_mestre_jarvis.md` como artefato canônico;
  - `HANDOFF.md` como documento operacional de continuidade;
  - `CHANGELOG.md` como registro de mudanças relevantes;
- criada a política de desmembramento em `docs/documentation/estrutura_de_documentos_derivados.md`;
- criado o pacote inicial de derivados de implementação, operação, arquitetura, executive summary e roadmap.

### Repositório real

- criada a base estrutural do monorepo na raiz com:
  - `README.md`
  - `.gitignore`
  - `.editorconfig`
  - `.env.example`
  - `pyproject.toml`
  - `package.json`;
- criada a árvore principal do repositório;
- criados os esqueletos mínimos dos serviços centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementada a primeira camada canônica de `shared/` com tipos, contratos, schemas, eventos e identidade/princípios;
- adicionados testes iniciais de regressão estrutural em `tests/unit/test_shared_layer.py`.

### Validação

- validada a estrutura criada com `rg --files` e inspeção recursiva de diretórios;
- validada a importação dos esqueletos de serviços e engines com `python`;
- validada a importação da nova camada `shared/` com `python`;
- a execução de `python -m pytest` ainda não foi concluída porque `pytest` não está instalado no ambiente local atual.








## 2026-03-20

### Abertura disciplinada do pos-v1

- encerramento do `v1` seguido de abertura disciplinada do `pos-v1` no proprio `HANDOFF.md`;
- definida a trilha prioritaria do `pos-v1` como `continuidade profunda entre missoes`;
- centralizadas as orientacoes operacionais do proximo ciclo no `HANDOFF.md`, sem criar documento novo;
- autorizado estudo externo curto para `LangGraph`, `Hermes Agent`, `Graphiti` e `Zep`, sempre como apoio dirigido e nao como bloqueio da implementacao principal.

### Pacote final de robustez e console minimo do v1

- criado `tools/operational_artifacts.py` para gerar `baseline snapshot`, `containment drill` e `incident evidence` do baseline controlado;
- ampliado `tools/validate_v1.py` com verificacao de consistencia entre missao, memoria e governanca, smoke do `jarvis-console` e geracao de snapshot operacional do baseline;
- ampliado `tools/go_live_internal_checklist.py` com checagem de `defer_for_validation` em conflito de missao, coerencia de `open_loops`, evidencia operacional minima e drill de contenimento/rollback simples;
- endurecido o `memory-service` para preservar o estado aceito de missao quando um turno posterior e bloqueado ou diferido pela governanca;
- ampliado o `observability-service` com `IncidentEvidence` para consolidar request, decisao, flags e acao recomendada ao operador;
- criado `apps/jarvis_console/` como interface textual minima do `v1`, com modos `ask` e `chat` sobre o fluxo real do orquestrador;
- `tools/run_internal_pilot.py` passou a publicar a ultima rodada em `.jarvis_runtime/pilot/latest_pilot.json` e `.md`;
- atualizados testes de memoria, observabilidade, orquestracao, artefatos operacionais e console.
