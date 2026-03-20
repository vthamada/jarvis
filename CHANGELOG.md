# CHANGELOG

Este changelog registra mudancas relevantes na documentacao canônica, nos artefatos de continuidade e nas decisóes estruturais do projeto `jarvis`.

Ele **não** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel e manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudanca importa.

---

## 2026-03-19

### Internal pilot executável, comparação de paths e proposals evolutivas

- adicionada auditoria operacional de fluxo ao `observability-service`, com trilha mínima obrigatória, flags automáticas de anomalia e visão de requests recentes;
- ampliado `tools/internal_pilot_report.py` para refletir `trace_status`, `anomaly_flags` e `source_services` por request;
- criado `tools/internal_pilot_support.py` para unificar cenários, bootstrap e coleta estruturada do `internal pilot`;
- criado `tools/run_internal_pilot.py` para executar a janela mínima do piloto e persistir evidência local em `JSON` e `Markdown`;
- criado `tools/compare_orchestrator_paths.py` para comparar baseline e POC opcional de `LangGraph` nos mesmos cenários;
- ampliado o `evolution-lab` com entrada de `FlowEvaluationInput` e helpers para comparar sinais reais do piloto;
- criado `tools/evolution_from_pilot.py` para transformar trilhas recentes e comparações de paths em proposals sandbox-only;
- ampliado o corpus curado do `knowledge-service` com domínios de `observability` e `pilot_operations`, mantendo retrieval determinístico;
- atualizados testes de observabilidade, `internal_pilot_report`, `knowledge-service`, `evolution-lab` e utilitários do piloto.

### Preparacao do internal pilot e POC de LangGraph

- adicionado `tools/internal_pilot_report.py` para resumir trilhas recentes por `request_id`, status operacional, decisão de governança e eventos obrigatorios ausentes;
- criado `docs/operations/internal-pilot-plan.md` como plano mínimo da primeira janela controlada após o `GO CONDICIONAL`;
- endurecido o `JsonlAgenticMirrorAdapter` para espelhar `trace tree` local com root trace e child runs, permitindo validar a estrutura de rastreabilidade mesmo sem credencial externa;
- endurecido `tools/go_live_internal_checklist.py` para exigir arvore de trace no espelhamento agentic;
- adicionada POC opcional de `LangGraph` ao `orchestrator-service`, preservando `handle_input()` como caminho principal e expondo `handle_input_langgraph_poc()` como rota experimental sem breaking change;
- adicionado extra opcional `langgraph` no `pyproject.toml` para permitir a POC do orquestrador sem contaminar o bootstrap padrao do `v1`.

### LangSmith complementar e ADR de LangGraph

- endurecido o adaptador `LangSmith` do `observability-service` para espelhar fluxos como `trace tree` por `request_id`, com root trace, child runs e metadata consistente;
- adicionados suporte a `LANGSMITH_ENDPOINT` e `LANGSMITH_WORKSPACE_ID` para cloud, hybrid ou self-hosted;
- ampliados os testes do `observability-service` para validar agrupamento por request e estrutura da arvore de traces;
- criado `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` para formalizar a absorção parcial de `LangGraph` como próximo salto estrutural do núcleo, sem reescrita ampla imediata do `v1`.

### Estudo aplicado da stack principal

- criado `docs/architecture/technology-study-phase1-core-stack.md` para registrar a Fase 1 do estudo de reaproveitamento tecnologico;
- consolidada a leitura aplicada de `LangGraph`, `PostgreSQL + pgvector` e `LangSmith` contra o estado real do repositório;
- registrada a decisão refinada desta fase: `LangSmith` como complemento imediato do ciclo de `internal pilot`, `LangGraph` como próximo salto estrutural do núcleo sem reescrita ampla imediata, e `pgvector` aprovado arquiteturalmente mas fora do caminho crítico até existir consumidor semântico real.

### Ciclo deliberativo do núcleo

### Memória semântica curta de missão

- ampliado `MissionStateContract` com `semantic_brief` e `semantic_focus` para representar continuidade de missão em nivel semântico curto, sem criar serviço novo;
- atualizados os repositórios `sqlite` e `PostgreSQL` do `memory-service` para persistir e recuperar os novos campos com migracao incremental de schema;
- ajustado o `memory-service` para emitir `mission_semantic_brief` e `mission_focus` como hints reutilizaveis no turno seguinte;
- ajustado o `planning-engine` para usar esses sinais como continuidade semântica explícita no plano e no rationale, sem substituir o contexto episódico;
- atualizados testes de memória, planejamento, orquestracao e integração PostgreSQL; `pytest -q` voltou a passar integralmente e `ruff check` passou nos arquivos alterados.

- introduzido `DeliberativePlanContract` como artefato estruturado do núcleo para resumir objetivo, etapas, riscos, restrições e recomendacao operacional;
- ampliado o `executive-engine` para produzir diretiva com confianca, ambiguidade, modo preferido de resposta e controle de execução;
- refeito o fluxo do `orchestrator-service` para operar como `entender -> decompor -> arbitrar -> decidir -> registrar -> responder`, incluindo os eventos `directive_composed`, `plan_built`, `plan_governed` e `clarification_required`;
- expandido o `memory-service` para persistir hints deliberativos de plano e resumo de missão, fortalecendo continuidade entre turnos;
- ajustado o `governance-service` para decidir com base no plano pretendido, não apenas na intencao textual;
- ajustados `operational-service` e `synthesis-engine` para consumir e refletir o plano deliberativo no resultado final;
- atualizados os testes de engines, memória, governança, operação e orquestracao; a suite `pytest -q` voltou a passar integralmente.

### Matriz de estudo tecnologico

- criado `docs/architecture/technology-study-matrix.md` para consolidar o estudo de tecnologias, frameworks, algoritmos e repositórios citados no Documento-Mestre;
- organizada a classificação entre base do `v1`, complementos controlados, laboratório, inspiracao arquitetural e itens a deferir para `v2`;
- registrada a ordem recomendada de estudo local de repositórios externos e as regras de segurança para clonar e analisar tecnologias fora do repositório principal do JARVIS.

### Benchmark harness e validação local

- implementado o pacote `tools/benchmarks/` com harness executável, dataset versionado e artefatos auditaveis em `.jarvis_runtime/benchmarks/`;
- adicionada exportacao `trace view` no `observability-service` para validar compatibilidade com tracing externo sem trocar o envelope interno;
- criada `.venv` local e instaladas as dependencias `.[dev]` para validação do baseline no ambiente do projeto;
- validado o benchmark local com decisóes preliminares: `knowledge -> weighted_deterministic`, `observability -> adotar no v1`, `evolution -> manual_variants`, `memory -> manter baseline atual até validar PostgreSQL`;
- validada a suite completa com `pytest -q` e os arquivos novos com `ruff check`.

### Baseline após benchmark

- promovido o ranking ponderado determinístico para o `knowledge-service`, absorvendo no baseline a melhoria escolhida pelo benchmark;
- ajustado o `evolution-lab` para registrar `manual_variants` como estratégia sandbox prioritária, sem promoção automatica;
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
- recalibrados os limites de laténcia do benchmark de memória para comparar `sqlite` com PostgreSQL local sem exigir um teto irreal para um banco operacional;
- rerodado o benchmark com `DATABASE_URL` real e decisão final `memory -> adotar no v1`;
- alterado o `docker compose` local do PostgreSQL para publicar em `5433`, evitando conflito com um `postgres.exe` local ativo na maquina.

### Alinhamento dos derivados ao baseline consolidado

- atualizados `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md` e `docs/roadmap/v1-roadmap.md` para refletir o baseline benchmarkado do `v1`;
- atualizados `docs/operations/v1-production-controlled.md` e `docs/operations/go-live-readiness.md` para tratar `PostgreSQL` como backend operacional recomendado e explicitar que a decisão de `go/no-go` ainda esta pendente;
- atualizado `docs/architecture/evolution-lab.md` para refletir `manual_variants` como estratégia priorizada no sandbox do `v1`;
- atualizado `docs/executive/v1-scope-summary.md` para registrar o estado atual do `v1` e a pendencia de fechamento para produção controlada.

### Decisóo formal de readiness do v1

- criado `docs/operations/v1-go-no-go-decision.md` para registrar a decisão formal de readiness do `v1`;
- registrada a decisão atual como `GO CONDICIONAL` para produção controlada em escopo reduzido;
- atualizado `docs/operations/go-live-readiness.md` para refletir que a decisão de `go/no-go` já foi tomada;
- atualizado `docs/operations/v1-production-controlled.md` para incorporar o estado formal da decisão;
- atualizado `docs/executive/master-summary.md`, que ainda estava atrasado em relação ao estado real do repositório.

---

## 2026-03-18

### Benchmark dirigido do v1

- implementado um harness local único em `tools/benchmarks/` para benchmarkar memória, knowledge, observabilidade e evolution-lab;
- congelado um dataset versionado em `tools/benchmarks/datasets/v1_benchmark_cases.json` com cenarios de `planning`, `analysis`, `general_assistance`, bloqueio por governança e continuidade de sessão;
- adicionada persistencia de artefatos auditaveis do benchmark em `JSON` e `Markdown`;
- adicionada exportacao de trace view no `observability-service` para validar compatibilidade com tracing externo sem substituir a trilha interna;
- adicionados testes do harness de benchmark e cobertura da exportacao de trace view;
- atualizado o `HANDOFF.md` para refletir o benchmark dirigido como próximo gate do fechamento do `v1`.


### Core v1 baseline

- implementado o primeiro baseline integrado do `v1`, conectando `orchestrator-service`, `memory-service`, `governance-service`, `knowledge-service`, `observability-service`, `operational-service` e `engines/`;
- reduzido o `orchestrator-service` ao papel de coordenador de fluxo, movendo classificação, planejamento, composicao cognitiva e síntese para engines dedicadas;
- preservado `InternalEventEnvelope` como envelope canônico para observabilidade e rastreabilidade do fluxo ponta a ponta.

### Memory Service

- substituido o armazenamento em `dict` por uma camada de repositório persistente;
- adicionado backend local por `sqlite` e suporte a `PostgreSQL` quando `DATABASE_URL` estiver configurada;
- adicionada persistencia de histórico episódico por `session_id`, resumo contextual de sessão e estado mínimo de missão por `mission_id`;
- ampliados os testes para validar continuidade entre instancias do serviço e persistencia de estado de missão.

### Observability Service

- implementado o `observability-service` como coletor estruturado de eventos internos;
- adicionada persistencia local da trilha de eventos e consulta por `request_id`, `session_id`, `mission_id` e `correlation_id`;
- integrado o orquestrador a essa trilha persistente em vez de depender apenas do retorno em memória.

### Knowledge e Engines

- implementado o `knowledge-service` com retrieval local determinístico sobre dominios prioritários do `v1`;
- externalizado o corpus inicial do `knowledge-service` para `knowledge/curated/v1_corpus.json`;
- implementadas as engines de identidade, executivo, planejamento, cognição e síntese;
- ampliada a cobertura de testes para validar classificação de intencao, composicao de dominios ativos e síntese final.

### Governance e Operational

- expandido o `governance-service` para suportar `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- adicionadas condições, auditoria e protecao de mutação em memória crítica na decisão de governança;
- expandido o `operational-service` para produzir artefatos textuais reais e preencher `artifacts`, `checkpoints` e `memory_record_hints`.

### Evolution Lab

- implementado o `evolution-lab` como primeiro corte de sandbox evolutivo local;
- adicionada persistencia local de propostas e decisóes de comparação entre baseline e candidata;
- estabelecido regime `sandbox-only`, sem promoção automatica, com rollback referenciado ao baseline.

### Bootstrap e validação

- ajustado `tests/conftest.py` para incluir a raiz do repositório no `sys.path` durante a execução dos testes;
- adicionado `conftest.py` na raiz para que testes isolados de serviços e engines carreguem o bootstrap corretamente;
- ajustado `pyproject.toml` para incluir `shared` na descoberta de pacotes do projeto;
- adicionado extra opcional `postgres` em `pyproject.toml` para readiness do backend PostgreSQL;
- desabilitado o cache nativo do `pytest` em configuração para evitar warnings recorrentes de permissao no ambiente local atual;
- validada a suite com `pytest -q` a partir da raiz, sem `PYTHONPATH` manual.

### PostgreSQL readiness

- ampliada a fabrica de memória para normalizar `postgres://` e `postgresql+psycopg://` antes de instanciar o backend PostgreSQL;
- adicionados indices básicos nas tabelas de memória para o caminho local e para o caminho PostgreSQL;
- criado `infra/local-postgres.compose.yml` como infraestrutura local padrao para validar a memória persistente contra PostgreSQL;
- ampliada a cobertura de testes da memória para selecao de backend e parsing de URL.

### Documentacao operacional

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
- ampliados os testes do `orchestrator-service` para validar despacho operacional permitido e a ausencia de operação em fluxos bloqueados.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory -> operational`.

### Validação

- validada por execução Python direta a cadeia completa `orchestrator -> governance -> memory -> operational`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Memory Service

- substituido o esqueleto vazio do `memory-service` por um primeiro serviço funcional mínimo em memória de processo;
- adicionado suporte a:
  - recuperacao contextual por sessão com `MemoryRecoveryContract`;
  - registro episódico simples de turno com `MemoryRecordContract`;
  - janela curta de recuperacao para o contexto recente da sessão;
- ampliados os testes do `memory-service` para cobrir sessão vazia e continuidade básica de contexto.

### Orchestrator Service

- integrado o `orchestrator-service` ao `memory-service`;
- o fluxo mínimo agora recupera contexto antes da decisão e grava o turno ao final;
- adicionados os eventos `memory_recovered` e `memory_recorded` ao fluxo principal;
- ampliados os testes do `orchestrator-service` para validar recuperacao de contexto entre dois turnos da mesma sessão.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo mínimo explícito `orchestrator -> governance -> memory`.

### Validação

- validada por execução Python direta a cadeia `memory-service -> orchestrator-service` com recuperacao contextual na segunda interação da mesma sessão;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Governance Service

- substituido o esqueleto vazio do `governance-service` por um primeiro serviço funcional mínimo;
- adicionado suporte a:
  - avaliação de request com base em `InputContract`;
  - classificação deterministica de risco;
  - geracao de `GovernanceCheckContract`;
  - geracao de `GovernanceDecisionContract` com `allow` e `block`;
- ampliados os testes do `governance-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### Orchestrator Service

- removida a política mínima de governança que ainda estava embutida localmente no `orchestrator-service`;
- o `orchestrator-service` agora depende do `governance-service` para obter checagem e decisão;
- preservado o papel do orquestrador como coordenador do fluxo, emissor de eventos e sintetizador de resposta.

### HANDOFF

- atualizado para refletir que o projeto agora possui integração mínima explícita entre `orchestrator-service` e `governance-service`.

### Validação

- validada por execução Python direta a cadeia `governance-service -> orchestrator-service`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Orchestrator Service

- substituido o esqueleto vazio do `orchestrator-service` por um primeiro fluxo funcional mínimo;
- adicionado suporte a:
  - recebimento de `InputContract`;
  - classificação simples de intencao;
  - geracao de `GovernanceCheckContract`;
  - avaliação inicial de governança com `allow` e `block`;
  - emissao de eventos internos prioritários;
  - síntese textual básica coerente com a identidade inicial do sistema;
- ampliados os testes do `orchestrator-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### HANDOFF

- atualizado para refletir que o projeto saiu do estado de esqueleto puro do orquestrador e entrou no primeiro fluxo funcional mínimo.

### Validação

- validado o fluxo do `orchestrator-service` por execução Python direta com carga manual de `sys.path`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-16

### Documento-Mestre

- preenchida a secao `236.1 Blocos essenciais`, que estava vazia;
- adicionada a secao `235.5 Continuidade editorial e rastreabilidade` para formalizar a preservacao historica de numeracao e o papel de capitulos de `Encaminhamento` e `Próximo passo`;
- ampliada a secao `236.2 Itens que podem virar documentos derivados`;
- substituido o fechamento duplicado do fim do documento por capitulos operacionais e de maturidade;
- enxugado o bloco final do Documento-Mestre para manter no arquivo principal apenas definicoes canônicas e referencias para derivados operacionais;
- enxugados os blocos de roadmap de milestones e de implementacao, preservando no arquivo principal a sequencia canônica e deslocando a leitura tatica para derivados;
- realizado pente fino final para reduzir linguagem exploratoria em decisóes tecnologicas já consolidadas.

### HANDOFF

- reestruturado para formato operacional de continuidade;
- removida a duplicacao excessiva do conteúdo do Documento-Mestre;
- alinhado ao estado do projeto após a consolidacao documental;
- atualizado para refletir a materializacao da Sprint 1 no repositório real;
- atualizado novamente para refletir o inicio da Sprint 2 com base semântica compartilhada mínima.

### Estrutura documental

- consolidada a separacao prática entre:
  - `documento_mestre_jarvis.md` como artefato canônico;
  - `HANDOFF.md` como documento operacional de continuidade;
  - `CHANGELOG.md` como registro de mudancas relevantes;
- criada a política de desmembramento em `docs/documentation/estrutura_de_documentos_derivados.md`;
- criado o pacote inicial de derivados de implementacao, operação, arquitetura, executive summary e roadmap.

### Repositório real

- criada a base estrutural do monorepo na raiz com:
  - `README.md`
  - `.gitignore`
  - `.editorconfig`
  - `.env.example`
  - `pyproject.toml`
  - `package.json`;
- criada a arvore principal do repositório;
- criados os esqueletos mínimos dos serviços centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementada a primeira camada canônica de `shared/` com tipos, contratos, schemas, eventos e identidade/principios;
- adicionados testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`.

### Validação

- validada a estrutura criada com `rg --files` e inspecao recursiva de diretorios;
- validada a importacao dos esqueletos de serviços e engines com `python`;
- validada a importacao da nova camada `shared/` com `python`;
- a execução de `python -m pytest` ainda não foi concluida porque `pytest` não esta instalado no ambiente local atual.




