# HANDOFF

## Metadata

- Atualizado em: 2026-03-19
- Branch: `main`
- Commit de referencia: `fa80320`
- Artefato canônico do projeto: `documento_mestre_jarvis.md`
- Status do projeto: `v1` em `GO CONDICIONAL` para produção controlada, com baseline integrado validado, benchmark local fechado, PostgreSQL validado como backend operacional, observabilidade local persistida e espelhamento agentic endurecido, `internal pilot` preparado com plano e relatório executável, e POC opcional de `LangGraph` aberta no `orchestrator-service` sem quebrar o fluxo principal

---

## Meta Atual

Executar o **primeiro ciclo controlado do v1** com observação reforçada, coletar evidência operacional real do `internal pilot` e preparar a decisão sobre a absorção parcial de `LangGraph` após o piloto.

---

## Estado do Projeto

Hoje o repositório contém:

- Documento-Mestre consolidado como artefato canônico;
- handoff operacional e changelog ativos;
- pacote inicial de documentos derivados;
- estrutura real do monorepo criada;
- arquivos-base da raiz presentes;
- camada compartilhada inicial em `shared/` com tipos, enums, estados, contratos, schemas, eventos e identidade/principios;
- `orchestrator-service` coordenando o fluxo entre engines, memória, governança, conhecimento, observabilidade e operação;
- `governance-service` com decisóes `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `memory-service` com persistencia local por repositório, contexto de sessão, estado mínimo de missão e resumo semântico curto reutilizavel entre turnos;
- `operational-service` com geracao de artefatos textuais estruturados e hints de memória;
- `knowledge-service` com retrieval determinístico sobre dominios prioritários do `v1` a partir de corpus curado local;
- `observability-service` persistindo a trilha de eventos internos com campos de correlação;
- `observability-service` com espelhamento agentic complementar endurecido para `LangSmith` e para arvore local de traces em `JSONL`;
- `evolution-lab` persistindo propostas e decisóes sandbox-only entre baseline e candidata;
- `engines/` com componentes reais de identidade, executivo, planejamento, cognição e síntese;
- suite de testes cobrindo persistencia, governança, observabilidade, conhecimento, operação e o fluxo ponta a ponta do orquestrador;
- ciclo deliberativo implementado no núcleo, com diretiva executiva enriquecida, plano estruturado, governança sobre plano, memória com hints deliberativos, resumo semântico de missão e síntese mais executiva.
- `tools/internal_pilot_report.py` resumindo requests recentes por `request_id`, decisão de governança, status operacional e eventos ausentes da trilha mínima;
- `docs/operations/internal-pilot-plan.md` definindo a janela mínima do primeiro piloto interno;
- POC opcional de `LangGraph` aberta no `orchestrator-service` por `handle_input_langgraph_poc()`, preservando `handle_input()` como caminho principal.

Arquivo paralelo/histórico que não deve ser tratado como fonte principal sem decisão explícita:

- `documento_mestre_do_jarvis.md`

---

## O Que Foi Feito

- revisão estrutural relevante do Documento-Mestre;
- consolidacao e enxugamento do Documento-Mestre para reforcar seu papel canônico;
- criacao do `HANDOFF.md` em formato operacional;
- criacao do `CHANGELOG.md`;
- definicao da política de documentos derivados;
- criacao do pacote inicial de derivados de implementacao, operação, arquitetura e resumo executivo;
- materializacao da base real do repositório da Sprint 1;
- criacao dos esqueletos mínimos dos serviços centrais e engines centrais;
- implementacao inicial da Sprint 2 em `shared/` com contratos, tipos, schemas, eventos e identidade/principios;
- criacao de testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`;
- implementacao do primeiro fluxo funcional do `orchestrator-service` com classificação simples de intencao, governança inicial, trilha de eventos e síntese básica;
- extracao da governança mínima para o `governance-service`, que agora gera a checagem e a decisão usadas pelo orquestrador;
- implementacao do `memory-service` com recuperacao contextual por sessão e registro episódico simples em memória de processo;
- integração do `orchestrator-service` com o `memory-service`, adicionando recuperacao e gravacao de memória ao fluxo mínimo;
- implementacao do `operational-service` com execução segura e deterministica de operações de baixo risco;
- integração do `orchestrator-service` com o `operational-service`, adicionando `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliacao dos testes do `operational-service` e do `orchestrator-service` para cobrir despacho operacional permitido e bloqueio previo por governança.
- substituicao da memória em processo por repositório persistente com suporte local por `sqlite` e backend `PostgreSQL` via `DATABASE_URL`;
- adicao de persistencia de histórico episódico por `session_id`, resumo contextual de sessão e estado mínimo de missão por `mission_id`;
- implementacao do `observability-service` como coletor e consulta local de eventos internos;
- integração do `orchestrator-service` com o `observability-service`, preservando `InternalEventEnvelope` como backbone comum;
- implementacao do `knowledge-service` com retrieval local determinístico para dominios prioritários do `v1`;
- externalizacao do corpus inicial para `knowledge/curated/v1_corpus.json`;
- implementacao real das engines de identidade, executivo, planejamento, cognição e síntese;
- reducao do `orchestrator-service` ao papel de coordenador de fluxo, removendo heuristicas espalhadas do caminho principal;
- ampliacao da governança para cenarios condicionados, bloqueados e adiados para validação;
- ampliacao do `operational-service` para produzir artefatos textuais e preencher `artifacts`, `checkpoints` e `memory_record_hints`;
- implementacao do `evolution-lab` como primeiro corte de comparação local entre baseline e candidata, sem promoção automatica;
- declaracao do extra opcional `postgres` no `pyproject.toml` para readiness do backend operacional;
- adicao de `infra/local-postgres.compose.yml` como infraestrutura local padrao para PostgreSQL;
- ampliacao da fabrica de memória para normalizar URLs `postgres://` e `postgresql+psycopg://`;
- adicao de `conftest.py` na raiz para que testes isolados fora de `tests/` carreguem o bootstrap correto;
- reescrita da cobertura de testes para validar comportamento funcional, persistencia entre instancias e trilha ponta a ponta;
- validação da suite com `pytest -q` diretamente da raiz do repositório.
- implementacao do harness local de benchmark em `tools/benchmarks/`, com dataset versionado e artefatos `JSON` e `Markdown`.
- adicao de exportacao de trace view no `observability-service` para validação de compatibilidade com tracing externo.
- bootstrap de `.venv` local com `.[dev]` instalado para validação consistente do repositório.
- execução e validação local do benchmark dirigido do `v1`, com decisão preliminar de manter memória atual até validar PostgreSQL, incorporar a trilha atual de observabilidade e priorizar `manual_variants` no evolution-lab.
- promoção do ranking ponderado determinístico para o baseline do `knowledge-service`, absorvendo no serviço a melhoria indicada pelo benchmark.
- traducao do resultado do benchmark do `evolution-lab` para o serviço real, registrando `manual_variants` como estratégia sandbox prioritária e preservando `sandbox-only`.
- ampliacao do harness de benchmark com CLI util, escopo isolado por execução e testes específicos para a trilha PostgreSQL.
- validação real do `memory-service` contra PostgreSQL local com `psycopg`, teste de integração dedicado e benchmark rerodado com decisão `adotar no v1`.
- ajuste do `docker compose` local para publicar PostgreSQL em `5433`, evitando conflito com um `postgres.exe` local já ativo nesta maquina;
- criacao de `docs/architecture/technology-study-matrix.md` para consolidar a leitura do Documento-Mestre sobre stack, frameworks, algoritmos e repositórios a estudar;
- implementacao do ciclo deliberativo do `v1`, com `DeliberativePlanContract`, diretiva executiva enriquecida, plano estruturado no `planning-engine`, memória persistindo hints de plano, governança avaliando o plano pretendido, observabilidade expandida e síntese mais deliberativa;
- atualizacao dos testes de engines e serviços para travar o novo comportamento e validação da suite completa com `pytest -q`.
- aprofundamento da memória de missão para persistir `semantic_brief` e `semantic_focus`, com recuperacao explícita desses sinais no `planning-engine` e continuidade de raciocinio melhor entre turnos da mesma missão;
- atualizacao dos repositórios `sqlite` e `PostgreSQL` da memória para suportar os novos campos semânticos e cobertura de testes para persistencia, recuperacao e continuidade entre instancias;
- estudo aplicado da stack principal concluido para `LangGraph`, `PostgreSQL + pgvector` e `LangSmith`, com resultado consolidado em `docs/architecture/technology-study-phase1-core-stack.md`;
- endurecimento do adaptador `LangSmith` no `observability-service` para emitir `trace tree` por `request_id`, com root trace e child runs coerentes;
- endurecimento do espelhamento agentic local em `JSONL` para refletir a mesma estrutura de arvore de trace usada pelo checklist de go-live;
- criacao do `ADR-001` para formalizar a absorção parcial e progressiva de `LangGraph` no núcleo, sem reescrita ampla do baseline atual;
- criacao de `tools/internal_pilot_report.py` e de `docs/operations/internal-pilot-plan.md` para operacionalizar o primeiro `internal pilot`;
- endurecimento de `tools/go_live_internal_checklist.py` para exigir root trace e child runs no espelhamento agentic local;
- abertura da POC opcional de `LangGraph` no `orchestrator-service`, com teste dedicado e sem breaking change na API pública principal;
- validação local de `ruff check`, `pytest -q` e `python tools/go_live_internal_checklist.py --profile development` nesta rodada.

---

## Decisóes Fechadas

Não rediscutir sem evidência forte ou mudanca explícita de direção:

- o JARVIS e um sistema unificado, não um chatbot simples;
- o repositório principal e `jarvis`;
- a estratégia base e monorepo modular;
- `Python` e a linguagem principal;
- `TypeScript` e linguagem secundaria para interface, web e voz quando necessario;
- `LangGraph` e a base principal de orquestracao stateful;
- `PostgreSQL + pgvector` e o backbone inicial de memória e persistencia;
- `LangSmith` e a principal camada de observabilidade agentic;
- a trilha local persistida continua sendo a fonte primaria de debug e auditoria, com `LangSmith` apenas como complemento;
- `LangGraph` entra por absorção parcial e progressiva, com POC opcional no orquestrador antes de qualquer migracao mais ampla;
- `OpenHands` e o principal especialista subordinado de software;
- especialistas sóo subordinados ao núcleo, não competidores de identidade;
- governança e autoevolucao sóo partes nucleares do sistema;
- o Documento-Mestre continua sendo o artefato canônico do projeto.

---

## O Que Ainda Falta

Pendencias principais agora:

- executar e registrar a primeira janela pequena do `internal pilot` em perfil `controlled`;
- coletar e revisar o relatório operacional inicial com `tools/internal_pilot_report.py`;
- comparar o baseline principal com a POC opcional de `LangGraph` após evidência real do piloto;
- decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Próximos Passos Imediatos

Ordem recomendada:

1. registrar o escopo inicial do primeiro uso real controlado;
2. executar a primeira janela pequena de produção controlada com observação reforçada;
3. extrair o relatório do piloto via `python tools/internal_pilot_report.py --limit 10`;
4. comparar o baseline atual com a POC opcional de `LangGraph`;
5. decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Riscos / Bloqueios

- `sqlite` continua como fallback local, mas o backend operacional recomendado do `v1` agora e `PostgreSQL`;
- nesta maquina há um `postgres.exe` local ativo na `5432`, por isso o `docker compose` do JARVIS pública o banco em `5433`;
- o corpus do `knowledge-service` continua local e curado manualmente, agora com ranking ponderado já absorvido no baseline;
- o `operational-service` continua deliberadamente restrito a tarefas seguras e deterministicas, sem adaptadores de alto risco;
- o `evolution-lab` segue sandbox-only e ainda não promove automaticamente nenhuma candidata ao baseline;
- a POC de `LangGraph` ainda e opcional, não roda no bootstrap padrao e depende do extra `.[langgraph]`;
- o checklist de go-live em `development` esta verde nesta rodada; a execução em `controlled` depende de `DATABASE_URL` ativo no ambiente de uso;
- a suite completa `pytest -q` e os arquivos tocados por esta rodada passam em `ruff check`; o risco atual esta mais em profundidade cognitiva e coleta de evidência real do piloto do que em estabilidade local.

---

## Arquivos Relevantes

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `shared/types/__init__.py`
- `shared/contracts/__init__.py`
- `engines/executive-engine/src/executive_engine/engine.py`
- `engines/planning-engine/src/planning_engine/engine.py`
- `engines/synthesis-engine/src/synthesis_engine/engine.py`
- `shared/schemas/__init__.py`
- `shared/events/__init__.py`
- `shared/state/__init__.py`
- `services/memory-service/src/memory_service/repository.py`
- `services/orchestrator-service/src/orchestrator_service/service.py`
- `services/orchestrator-service/tests/test_orchestrator_service.py`
- `services/governance-service/src/governance_service/service.py`
- `services/governance-service/tests/test_governance_service.py`
- `services/knowledge-service/src/knowledge_service/service.py`
- `services/knowledge-service/tests/test_knowledge_service.py`
- `knowledge/curated/v1_corpus.json`
- `infra/local-postgres.compose.yml`
- `conftest.py`
- `services/memory-service/src/memory_service/service.py`
- `services/memory-service/tests/test_memory_service.py`
- `services/observability-service/src/observability_service/repository.py`
- `services/observability-service/src/observability_service/agentic.py`
- `services/observability-service/src/observability_service/service.py`
- `services/observability-service/tests/test_observability_service.py`
- `services/orchestrator-service/src/orchestrator_service/langgraph_poc.py`
- `services/orchestrator-service/tests/test_langgraph_poc.py`
- `evolution/evolution-lab/src/evolution_lab/service.py`
- `evolution/evolution-lab/src/evolution_lab/repository.py`
- `evolution/evolution-lab/tests/test_evolution_lab_service.py`
- `tools/benchmarks/harness.py`
- `tools/benchmarks/dataset.py`
- `tools/benchmarks/datasets/v1_benchmark_cases.json`
- `tools/go_live_internal_checklist.py`
- `tools/internal_pilot_report.py`
- `tests/benchmark/test_benchmark_harness.py`
- `tests/unit/test_internal_pilot_report.py`
- `services/operational-service/src/operational_service/service.py`
- `services/operational-service/tests/test_operational_service.py`
- `engines/identity-engine/src/identity_engine/engine.py`
- `engines/executive-engine/src/executive_engine/engine.py`
- `engines/planning-engine/src/planning_engine/engine.py`
- `engines/cognitive-engine/src/cognitive_engine/engine.py`
- `engines/synthesis-engine/src/synthesis_engine/engine.py`
- `tests/unit/test_shared_layer.py`
- `docs/implementation/service-breakdown.md`
- `docs/operations/internal-pilot-plan.md`
- `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md`
- `docs/architecture/technology-study-matrix.md`
- `docs/architecture/technology-study-phase1-core-stack.md`
- `docs/implementation/implementation-strategy.md`

---

## Como Validar / Retomar

Leitura mínima para qualquer novo agente:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `services/orchestrator-service/src/orchestrator_service/service.py`
4. `services/memory-service/src/memory_service/repository.py`
5. `services/governance-service/src/governance_service/service.py`
6. `services/knowledge-service/src/knowledge_service/service.py`
7. `services/observability-service/src/observability_service/service.py`
8. `evolution/evolution-lab/src/evolution_lab/service.py`
9. `services/operational-service/src/operational_service/service.py`
10. `tools/benchmarks/harness.py`
11. `tools/internal_pilot_report.py`
12. `docs/operations/internal-pilot-plan.md`

Checagens rapidas recomendadas:

- confirmar que `shared/` contém a camada canônica mínima;
- validar que o `memory-service` persiste contexto entre instancias do serviço;
- validar que o `governance-service` produz checagem, decisão e condições coerentes;
- validar que o `knowledge-service` retorna dominios e snippets para `analysis` e `planning`;
- validar que o `knowledge-service` carrega o corpus curado local esperado;
- validar que o `observability-service` registra a trilha completa de eventos;
- validar que o espelhamento agentic local gera root trace e child runs;
- validar que o `evolution-lab` registra proposta e decisão sandbox-only sem promoção automatica;
- validar que o `operational-service` executa apenas tarefas seguras e produz artefatos textuais;
- executar `python -m tools.benchmarks` e revisar as decisóes por trilha;
- executar `python tools/internal_pilot_report.py --limit 5` para leitura rapida das trilhas recentes;
- executar `pytest -q` diretamente da raiz e `ruff check .` na `.venv` local.

Comandos uteis:

```powershell
rg --files
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe tools\go_live_internal_checklist.py --profile development
.\.venv\Scripts\python.exe tools\internal_pilot_report.py --limit 5
.\.venv\Scripts\python.exe -m pip install -e .[dev,postgres]
.\.venv\Scripts\python.exe -m pip install -e ".[dev,langgraph]"
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/jarvis"
.\.venv\Scripts\python.exe -m tools.benchmarks --postgres-url $env:DATABASE_URL
.\.venv\Scripts\python.exe -m pytest services/memory-service/tests/test_memory_postgres_integration.py -q
.\.venv\Scripts\python.exe tools\go_live_internal_checklist.py --profile controlled
```

---

## Regra Para o Próximo Agente

- tratar `documento_mestre_jarvis.md` como artefato canônico;
- usar `HANDOFF.md` como documento operacional de estado;
- atualizar `CHANGELOG.md` sempre que houver mudanca relevante;
- priorizar agora execução observada do `internal pilot` e coleta de evidência operacional real;
- reutilizar `shared/` em vez de redefinir contratos localmente nos serviços.

---

## Critério de Encerramento Deste Handoff

Este handoff continua util enquanto o projeto estiver conduzindo o `internal pilot` do `v1` e decidindo a absorção parcial de `LangGraph` no pos-piloto.

Ele deve ser reavaliado quando:

- a primeira janela de produção controlada do `v1` tiver sido executada e registrada;
- o `knowledge-service` sair do corpus local mínimo e entrar em retrieval mais robusto;
- o baseline de `M6` sair do sandbox evolutivo mínimo e entrar em benchmark mais formal;
- houver mudanca arquitetural relevante que torne este handoff obsoleto.







