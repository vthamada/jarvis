# CHANGELOG

Este changelog registra mudancas relevantes na documentacao canonica, nos artefatos de continuidade e nas decisoes estruturais do projeto `jarvis`.

Ele **nao** substitui o Documento-Mestre, o `HANDOFF.md` ou futuros ADRs detalhados. Seu papel e manter rastreabilidade objetiva do que mudou, quando mudou e por que a mudanca importa.

---

## 2026-03-19

### Ciclo deliberativo do nucleo

### Memoria semantica curta de missao

- ampliado `MissionStateContract` com `semantic_brief` e `semantic_focus` para representar continuidade de missao em nivel semantico curto, sem criar servico novo;
- atualizados os repositorios `sqlite` e `PostgreSQL` do `memory-service` para persistir e recuperar os novos campos com migracao incremental de schema;
- ajustado o `memory-service` para emitir `mission_semantic_brief` e `mission_focus` como hints reutilizaveis no turno seguinte;
- ajustado o `planning-engine` para usar esses sinais como continuidade semantica explicita no plano e no rationale, sem substituir o contexto episodico;
- atualizados testes de memoria, planejamento, orquestracao e integracao PostgreSQL; `pytest -q` voltou a passar integralmente e `ruff check` passou nos arquivos alterados.

- introduzido `DeliberativePlanContract` como artefato estruturado do nucleo para resumir objetivo, etapas, riscos, restricoes e recomendacao operacional;
- ampliado o `executive-engine` para produzir diretiva com confianca, ambiguidade, modo preferido de resposta e controle de execucao;
- refeito o fluxo do `orchestrator-service` para operar como `entender -> decompor -> arbitrar -> decidir -> registrar -> responder`, incluindo os eventos `directive_composed`, `plan_built`, `plan_governed` e `clarification_required`;
- expandido o `memory-service` para persistir hints deliberativos de plano e resumo de missao, fortalecendo continuidade entre turnos;
- ajustado o `governance-service` para decidir com base no plano pretendido, nao apenas na intencao textual;
- ajustados `operational-service` e `synthesis-engine` para consumir e refletir o plano deliberativo no resultado final;
- atualizados os testes de engines, memoria, governanca, operacao e orquestracao; a suite `pytest -q` voltou a passar integralmente.

### Matriz de estudo tecnologico

- criado `docs/architecture/technology-study-matrix.md` para consolidar o estudo de tecnologias, frameworks, algoritmos e repositorios citados no Documento-Mestre;
- organizada a classificacao entre base do `v1`, complementos controlados, laboratorio, inspiracao arquitetural e itens a deferir para `v2`;
- registrada a ordem recomendada de estudo local de repositorios externos e as regras de seguranca para clonar e analisar tecnologias fora do repositorio principal do JARVIS.

### Benchmark harness e validacao local

- implementado o pacote `tools/benchmarks/` com harness executavel, dataset versionado e artefatos auditaveis em `.jarvis_runtime/benchmarks/`;
- adicionada exportacao `trace view` no `observability-service` para validar compatibilidade com tracing externo sem trocar o envelope interno;
- criada `.venv` local e instaladas as dependencias `.[dev]` para validacao do baseline no ambiente do projeto;
- validado o benchmark local com decisoes preliminares: `knowledge -> weighted_deterministic`, `observability -> adotar no v1`, `evolution -> manual_variants`, `memory -> manter baseline atual ate validar PostgreSQL`;
- validada a suite completa com `pytest -q` e os arquivos novos com `ruff check`.

### Baseline apos benchmark

- promovido o ranking ponderado deterministico para o `knowledge-service`, absorvendo no baseline a melhoria escolhida pelo benchmark;
- ajustado o `evolution-lab` para registrar `manual_variants` como estrategia sandbox prioritaria, sem promocao automatica;
- ampliados os testes de `knowledge-service` e `evolution-lab` para travar o comportamento promovido ao baseline;
- rerodado o benchmark e validado que `knowledge` agora aparece como `manter baseline atual`, refletindo que a melhoria ja foi incorporada ao sistema.

### Readiness de PostgreSQL e benchmark CLI

- adicionado suporte de CLI ao harness de benchmark com `--output-dir`, `--dataset-path`, `--postgres-url` e `--print-json`;
- isolado o escopo do benchmark de memoria com identificadores unicos por execucao para evitar colisao entre rodadas;
- adicionados testes opcionais de integracao PostgreSQL para o `memory-service` e para a trilha de memoria do benchmark, com `skip` quando `DATABASE_URL` ou `psycopg` nao estiverem disponiveis;
- atualizado o handoff com o fluxo correto de validacao da candidata PostgreSQL.

### Validacao real de PostgreSQL

- instalado o extra `postgres` na `.venv` local para habilitar o backend real com `psycopg`;
- validado o `memory-service` contra PostgreSQL local com teste de integracao dedicado;
- ajustado o harness para isolar execucoes por identificadores unicos e medir paridade funcional de forma consistente com o comportamento real da memoria;
- recalibrados os limites de latencia do benchmark de memoria para comparar `sqlite` com PostgreSQL local sem exigir um teto irreal para um banco operacional;
- rerodado o benchmark com `DATABASE_URL` real e decisao final `memory -> adotar no v1`;
- alterado o `docker compose` local do PostgreSQL para publicar em `5433`, evitando conflito com um `postgres.exe` local ativo na maquina.

### Alinhamento dos derivados ao baseline consolidado

- atualizados `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md` e `docs/roadmap/v1-roadmap.md` para refletir o baseline benchmarkado do `v1`;
- atualizados `docs/operations/v1-production-controlled.md` e `docs/operations/go-live-readiness.md` para tratar `PostgreSQL` como backend operacional recomendado e explicitar que a decisao de `go/no-go` ainda esta pendente;
- atualizado `docs/architecture/evolution-lab.md` para refletir `manual_variants` como estrategia priorizada no sandbox do `v1`;
- atualizado `docs/executive/v1-scope-summary.md` para registrar o estado atual do `v1` e a pendencia de fechamento para producao controlada.

### Decisao formal de readiness do v1

- criado `docs/operations/v1-go-no-go-decision.md` para registrar a decisao formal de readiness do `v1`;
- registrada a decisao atual como `GO CONDICIONAL` para producao controlada em escopo reduzido;
- atualizado `docs/operations/go-live-readiness.md` para refletir que a decisao de `go/no-go` ja foi tomada;
- atualizado `docs/operations/v1-production-controlled.md` para incorporar o estado formal da decisao;
- atualizado `docs/executive/master-summary.md`, que ainda estava atrasado em relacao ao estado real do repositorio.

---

## 2026-03-18

### Benchmark dirigido do v1

- implementado um harness local unico em `tools/benchmarks/` para benchmarkar memoria, knowledge, observabilidade e evolution-lab;
- congelado um dataset versionado em `tools/benchmarks/datasets/v1_benchmark_cases.json` com cenarios de `planning`, `analysis`, `general_assistance`, bloqueio por governanca e continuidade de sessao;
- adicionada persistencia de artefatos auditaveis do benchmark em `JSON` e `Markdown`;
- adicionada exportacao de trace view no `observability-service` para validar compatibilidade com tracing externo sem substituir a trilha interna;
- adicionados testes do harness de benchmark e cobertura da exportacao de trace view;
- atualizado o `HANDOFF.md` para refletir o benchmark dirigido como proximo gate do fechamento do `v1`.


### Core v1 baseline

- implementado o primeiro baseline integrado do `v1`, conectando `orchestrator-service`, `memory-service`, `governance-service`, `knowledge-service`, `observability-service`, `operational-service` e `engines/`;
- reduzido o `orchestrator-service` ao papel de coordenador de fluxo, movendo classificacao, planejamento, composicao cognitiva e sintese para engines dedicadas;
- preservado `InternalEventEnvelope` como envelope canonico para observabilidade e rastreabilidade do fluxo ponta a ponta.

### Memory Service

- substituido o armazenamento em `dict` por uma camada de repositorio persistente;
- adicionado backend local por `sqlite` e suporte a `PostgreSQL` quando `DATABASE_URL` estiver configurada;
- adicionada persistencia de historico episodico por `session_id`, resumo contextual de sessao e estado minimo de missao por `mission_id`;
- ampliados os testes para validar continuidade entre instancias do servico e persistencia de estado de missao.

### Observability Service

- implementado o `observability-service` como coletor estruturado de eventos internos;
- adicionada persistencia local da trilha de eventos e consulta por `request_id`, `session_id`, `mission_id` e `correlation_id`;
- integrado o orquestrador a essa trilha persistente em vez de depender apenas do retorno em memoria.

### Knowledge e Engines

- implementado o `knowledge-service` com retrieval local deterministico sobre dominios prioritarios do `v1`;
- externalizado o corpus inicial do `knowledge-service` para `knowledge/curated/v1_corpus.json`;
- implementadas as engines de identidade, executivo, planejamento, cognicao e sintese;
- ampliada a cobertura de testes para validar classificacao de intencao, composicao de dominios ativos e sintese final.

### Governance e Operational

- expandido o `governance-service` para suportar `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- adicionadas condicoes, auditoria e protecao de mutacao em memoria critica na decisao de governanca;
- expandido o `operational-service` para produzir artefatos textuais reais e preencher `artifacts`, `checkpoints` e `memory_record_hints`.

### Evolution Lab

- implementado o `evolution-lab` como primeiro corte de sandbox evolutivo local;
- adicionada persistencia local de propostas e decisoes de comparacao entre baseline e candidata;
- estabelecido regime `sandbox-only`, sem promocao automatica, com rollback referenciado ao baseline.

### Bootstrap e validacao

- ajustado `tests/conftest.py` para incluir a raiz do repositorio no `sys.path` durante a execucao dos testes;
- adicionado `conftest.py` na raiz para que testes isolados de servicos e engines carreguem o bootstrap corretamente;
- ajustado `pyproject.toml` para incluir `shared` na descoberta de pacotes do projeto;
- adicionado extra opcional `postgres` em `pyproject.toml` para readiness do backend PostgreSQL;
- desabilitado o cache nativo do `pytest` em configuracao para evitar warnings recorrentes de permissao no ambiente local atual;
- validada a suite com `pytest -q` a partir da raiz, sem `PYTHONPATH` manual.

### PostgreSQL readiness

- ampliada a fabrica de memoria para normalizar `postgres://` e `postgresql+psycopg://` antes de instanciar o backend PostgreSQL;
- adicionados indices basicos nas tabelas de memoria para o caminho local e para o caminho PostgreSQL;
- criado `infra/local-postgres.compose.yml` como infraestrutura local padrao para validar a memoria persistente contra PostgreSQL;
- ampliada a cobertura de testes da memoria para selecao de backend e parsing de URL.

### Documentacao operacional

- atualizados `README.md`, `HANDOFF.md`, `docs/implementation/implementation-strategy.md`, `docs/implementation/service-breakdown.md`, `docs/roadmap/v1-roadmap.md`, `docs/architecture/evolution-lab.md` e documentos operacionais para refletir o baseline atual do `v1`.

---

## 2026-03-17

### Operational Service

- substituido o esqueleto vazio do `operational-service` por um primeiro servico funcional minimo para tarefas seguras e deterministicas;
- adicionado suporte a:
  - execucao de `draft_plan`;
  - execucao de `produce_analysis_brief`;
  - execucao de `general_response`;
  - retorno via `OperationResultContract` com status e outputs estruturados;
- ampliados os testes do `operational-service` para cobrir task suportada e task nao suportada.

### Orchestrator Service

- integrado o `orchestrator-service` ao `operational-service`;
- o fluxo permitido agora gera `OperationDispatchContract`, executa a operacao e incorpora o resultado na sintese final;
- adicionados os eventos `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliados os testes do `orchestrator-service` para validar despacho operacional permitido e a ausencia de operacao em fluxos bloqueados.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo minimo explicito `orchestrator -> governance -> memory -> operational`.

### Validacao

- validada por execucao Python direta a cadeia completa `orchestrator -> governance -> memory -> operational`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Memory Service

- substituido o esqueleto vazio do `memory-service` por um primeiro servico funcional minimo em memoria de processo;
- adicionado suporte a:
  - recuperacao contextual por sessao com `MemoryRecoveryContract`;
  - registro episodico simples de turno com `MemoryRecordContract`;
  - janela curta de recuperacao para o contexto recente da sessao;
- ampliados os testes do `memory-service` para cobrir sessao vazia e continuidade basica de contexto.

### Orchestrator Service

- integrado o `orchestrator-service` ao `memory-service`;
- o fluxo minimo agora recupera contexto antes da decisao e grava o turno ao final;
- adicionados os eventos `memory_recovered` e `memory_recorded` ao fluxo principal;
- ampliados os testes do `orchestrator-service` para validar recuperacao de contexto entre dois turnos da mesma sessao.

### HANDOFF

- atualizado para refletir que o projeto agora possui um fluxo minimo explicito `orchestrator -> governance -> memory`.

### Validacao

- validada por execucao Python direta a cadeia `memory-service -> orchestrator-service` com recuperacao contextual na segunda interacao da mesma sessao;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Governance Service

- substituido o esqueleto vazio do `governance-service` por um primeiro servico funcional minimo;
- adicionado suporte a:
  - avaliacao de request com base em `InputContract`;
  - classificacao deterministica de risco;
  - geracao de `GovernanceCheckContract`;
  - geracao de `GovernanceDecisionContract` com `allow` e `block`;
- ampliados os testes do `governance-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### Orchestrator Service

- removida a politica minima de governanca que ainda estava embutida localmente no `orchestrator-service`;
- o `orchestrator-service` agora depende do `governance-service` para obter checagem e decisao;
- preservado o papel do orquestrador como coordenador do fluxo, emissor de eventos e sintetizador de resposta.

### HANDOFF

- atualizado para refletir que o projeto agora possui integracao minima explicita entre `orchestrator-service` e `governance-service`.

### Validacao

- validada por execucao Python direta a cadeia `governance-service -> orchestrator-service`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-17

### Orchestrator Service

- substituido o esqueleto vazio do `orchestrator-service` por um primeiro fluxo funcional minimo;
- adicionado suporte a:
  - recebimento de `InputContract`;
  - classificacao simples de intencao;
  - geracao de `GovernanceCheckContract`;
  - avaliacao inicial de governanca com `allow` e `block`;
  - emissao de eventos internos prioritarios;
  - sintese textual basica coerente com a identidade inicial do sistema;
- ampliados os testes do `orchestrator-service` para cobrir um fluxo de baixo risco e um fluxo sensivel bloqueado.

### HANDOFF

- atualizado para refletir que o projeto saiu do estado de esqueleto puro do orquestrador e entrou no primeiro fluxo funcional minimo.

### Validacao

- validado o fluxo do `orchestrator-service` por execucao Python direta com carga manual de `sys.path`;
- `pytest` continua pendente por ausencia de dependencia instalada no ambiente local atual.

---

## 2026-03-16

### Documento-Mestre

- preenchida a secao `236.1 Blocos essenciais`, que estava vazia;
- adicionada a secao `235.5 Continuidade editorial e rastreabilidade` para formalizar a preservacao historica de numeracao e o papel de capitulos de `Encaminhamento` e `Proximo passo`;
- ampliada a secao `236.2 Itens que podem virar documentos derivados`;
- substituido o fechamento duplicado do fim do documento por capitulos operacionais e de maturidade;
- enxugado o bloco final do Documento-Mestre para manter no arquivo principal apenas definicoes canonicas e referencias para derivados operacionais;
- enxugados os blocos de roadmap de milestones e de implementacao, preservando no arquivo principal a sequencia canonica e deslocando a leitura tatica para derivados;
- realizado pente fino final para reduzir linguagem exploratoria em decisoes tecnologicas ja consolidadas.

### HANDOFF

- reestruturado para formato operacional de continuidade;
- removida a duplicacao excessiva do conteudo do Documento-Mestre;
- alinhado ao estado do projeto apos a consolidacao documental;
- atualizado para refletir a materializacao da Sprint 1 no repositorio real;
- atualizado novamente para refletir o inicio da Sprint 2 com base semantica compartilhada minima.

### Estrutura documental

- consolidada a separacao pratica entre:
  - `documento_mestre_jarvis.md` como artefato canonico;
  - `HANDOFF.md` como documento operacional de continuidade;
  - `CHANGELOG.md` como registro de mudancas relevantes;
- criada a politica de desmembramento em `docs/documentation/estrutura_de_documentos_derivados.md`;
- criado o pacote inicial de derivados de implementacao, operacao, arquitetura, executive summary e roadmap.

### Repositorio real

- criada a base estrutural do monorepo na raiz com:
  - `README.md`
  - `.gitignore`
  - `.editorconfig`
  - `.env.example`
  - `pyproject.toml`
  - `package.json`;
- criada a arvore principal do repositorio;
- criados os esqueletos minimos dos servicos centrais e das engines centrais;
- preparada a base compartilhada para a Sprint 2 em `shared/contracts`, `shared/schemas`, `shared/types`, `shared/events` e `shared/state`;
- implementada a primeira camada canonica de `shared/` com tipos, contratos, schemas, eventos e identidade/principios;
- adicionados testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`.

### Validacao

- validada a estrutura criada com `rg --files` e inspecao recursiva de diretorios;
- validada a importacao dos esqueletos de servicos e engines com `python`;
- validada a importacao da nova camada `shared/` com `python`;
- a execucao de `python -m pytest` ainda nao foi concluida porque `pytest` nao esta instalado no ambiente local atual.






