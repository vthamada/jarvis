# HANDOFF

## Metadata

- Atualizado em: 2026-03-19
- Branch: `main`
- Commit de referencia: `3edf609`
- Artefato canonico do projeto: `documento_mestre_jarvis.md`
- Status do projeto: baseline integrado do `v1` com benchmark local implementado, retrieval ponderado absorvido no baseline, observabilidade validada, evolution-lab com estrategia sandbox priorizada, PostgreSQL validado como backend operacional do v1 local e decisao formal atual de `GO CONDICIONAL` para producao controlada, com ciclo deliberativo do nucleo implementado e validado por testes

---

## Meta Atual

Consolidar o **primeiro baseline integrado do v1** do JARVIS, saindo do fluxo funcional minimo para um nucleo testavel com continuidade, governanca mais robusta, observabilidade local e operacao util.

---

## Estado do Projeto

Hoje o repositorio contem:

- Documento-Mestre consolidado como artefato canonico;
- handoff operacional e changelog ativos;
- pacote inicial de documentos derivados;
- estrutura real do monorepo criada;
- arquivos-base da raiz presentes;
- camada compartilhada inicial em `shared/` com tipos, enums, estados, contratos, schemas, eventos e identidade/principios;
- `orchestrator-service` coordenando o fluxo entre engines, memoria, governanca, conhecimento, observabilidade e operacao;
- `governance-service` com decisoes `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `memory-service` com persistencia local por repositorio, contexto de sessao e estado minimo de missao;
- `operational-service` com geracao de artefatos textuais estruturados e hints de memoria;
- `knowledge-service` com retrieval deterministico sobre dominios prioritarios do `v1` a partir de corpus curado local;
- `observability-service` persistindo a trilha de eventos internos com campos de correlacao;
- `evolution-lab` persistindo propostas e decisoes sandbox-only entre baseline e candidata;
- `engines/` com componentes reais de identidade, executivo, planejamento, cognicao e sintese;
- suite de testes cobrindo persistencia, governanca, observabilidade, conhecimento, operacao e o fluxo ponta a ponta do orquestrador;
- ciclo deliberativo implementado no nucleo, com diretiva executiva enriquecida, plano estruturado, governanca sobre plano, memoria com hints deliberativos e sintese mais executiva.

Arquivo paralelo/historico que nao deve ser tratado como fonte principal sem decisao explicita:

- `documento_mestre_do_jarvis.md`

---

## O Que Foi Feito

- revisao estrutural relevante do Documento-Mestre;
- consolidacao e enxugamento do Documento-Mestre para reforcar seu papel canonico;
- criacao do `HANDOFF.md` em formato operacional;
- criacao do `CHANGELOG.md`;
- definicao da politica de documentos derivados;
- criacao do pacote inicial de derivados de implementacao, operacao, arquitetura e resumo executivo;
- materializacao da base real do repositorio da Sprint 1;
- criacao dos esqueletos minimos dos servicos centrais e engines centrais;
- implementacao inicial da Sprint 2 em `shared/` com contratos, tipos, schemas, eventos e identidade/principios;
- criacao de testes iniciais de regressao estrutural em `tests/unit/test_shared_layer.py`;
- implementacao do primeiro fluxo funcional do `orchestrator-service` com classificacao simples de intencao, governanca inicial, trilha de eventos e sintese basica;
- extracao da governanca minima para o `governance-service`, que agora gera a checagem e a decisao usadas pelo orquestrador;
- implementacao do `memory-service` com recuperacao contextual por sessao e registro episodico simples em memoria de processo;
- integracao do `orchestrator-service` com o `memory-service`, adicionando recuperacao e gravacao de memoria ao fluxo minimo;
- implementacao do `operational-service` com execucao segura e deterministica de operacoes de baixo risco;
- integracao do `orchestrator-service` com o `operational-service`, adicionando `operation_dispatched` e `operation_completed` ao fluxo permitido;
- ampliacao dos testes do `operational-service` e do `orchestrator-service` para cobrir despacho operacional permitido e bloqueio previo por governanca.
- substituicao da memoria em processo por repositorio persistente com suporte local por `sqlite` e backend `PostgreSQL` via `DATABASE_URL`;
- adicao de persistencia de historico episodico por `session_id`, resumo contextual de sessao e estado minimo de missao por `mission_id`;
- implementacao do `observability-service` como coletor e consulta local de eventos internos;
- integracao do `orchestrator-service` com o `observability-service`, preservando `InternalEventEnvelope` como backbone comum;
- implementacao do `knowledge-service` com retrieval local deterministico para dominios prioritarios do `v1`;
- externalizacao do corpus inicial para `knowledge/curated/v1_corpus.json`;
- implementacao real das engines de identidade, executivo, planejamento, cognicao e sintese;
- reducao do `orchestrator-service` ao papel de coordenador de fluxo, removendo heuristicas espalhadas do caminho principal;
- ampliacao da governanca para cenarios condicionados, bloqueados e adiados para validacao;
- ampliacao do `operational-service` para produzir artefatos textuais e preencher `artifacts`, `checkpoints` e `memory_record_hints`;
- implementacao do `evolution-lab` como primeiro corte de comparacao local entre baseline e candidata, sem promocao automatica;
- declaracao do extra opcional `postgres` no `pyproject.toml` para readiness do backend operacional;
- adicao de `infra/local-postgres.compose.yml` como infraestrutura local padrao para PostgreSQL;
- ampliacao da fabrica de memoria para normalizar URLs `postgres://` e `postgresql+psycopg://`;
- adicao de `conftest.py` na raiz para que testes isolados fora de `tests/` carreguem o bootstrap correto;
- reescrita da cobertura de testes para validar comportamento funcional, persistencia entre instancias e trilha ponta a ponta;
- validacao da suite com `pytest -q` diretamente da raiz do repositorio.
- implementacao do harness local de benchmark em `tools/benchmarks/`, com dataset versionado e artefatos `JSON` e `Markdown`.
- adicao de exportacao de trace view no `observability-service` para validacao de compatibilidade com tracing externo.
- bootstrap de `.venv` local com `.[dev]` instalado para validacao consistente do repositório.
- execucao e validacao local do benchmark dirigido do `v1`, com decisao preliminar de manter memoria atual ate validar PostgreSQL, incorporar a trilha atual de observabilidade e priorizar `manual_variants` no evolution-lab.
- promocao do ranking ponderado deterministico para o baseline do `knowledge-service`, absorvendo no servico a melhoria indicada pelo benchmark.
- traducao do resultado do benchmark do `evolution-lab` para o servico real, registrando `manual_variants` como estrategia sandbox prioritaria e preservando `sandbox-only`.
- ampliacao do harness de benchmark com CLI util, escopo isolado por execucao e testes especificos para a trilha PostgreSQL.
- validacao real do `memory-service` contra PostgreSQL local com `psycopg`, teste de integracao dedicado e benchmark rerodado com decisao `adotar no v1`.
- ajuste do `docker compose` local para publicar PostgreSQL em `5433`, evitando conflito com um `postgres.exe` local ja ativo nesta maquina;
- criacao de `docs/architecture/technology-study-matrix.md` para consolidar a leitura do Documento-Mestre sobre stack, frameworks, algoritmos e repositorios a estudar;
- implementacao do ciclo deliberativo do `v1`, com `DeliberativePlanContract`, diretiva executiva enriquecida, plano estruturado no `planning-engine`, memoria persistindo hints de plano, governanca avaliando o plano pretendido, observabilidade expandida e sintese mais deliberativa;
- atualizacao dos testes de engines e servicos para travar o novo comportamento e validacao da suite completa com `pytest -q`.

---

## Decisoes Fechadas

Nao rediscutir sem evidencia forte ou mudanca explicita de direcao:

- o JARVIS e um sistema unificado, nao um chatbot simples;
- o repositorio principal e `jarvis`;
- a estrategia base e monorepo modular;
- `Python` e a linguagem principal;
- `TypeScript` e linguagem secundaria para interface, web e voz quando necessario;
- `LangGraph` e a base principal de orquestracao stateful;
- `PostgreSQL + pgvector` e o backbone inicial de memoria e persistencia;
- `LangSmith` e a principal camada de observabilidade agentic;
- `OpenHands` e o principal especialista subordinado de software;
- especialistas sao subordinados ao nucleo, nao competidores de identidade;
- governanca e autoevolucao sao partes nucleares do sistema;
- o Documento-Mestre continua sendo o artefato canonico do projeto.

---

## O Que Ainda Falta

Pendencias principais agora:

- decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Proximos Passos Imediatos

Ordem recomendada:

1. registrar o escopo inicial do primeiro uso real controlado;
2. executar a primeira janela pequena de producao controlada com observacao reforcada;
3. decidir formalmente o destino de `documento_mestre_do_jarvis.md`.

---

## Riscos / Bloqueios

- `sqlite` continua como fallback local, mas o backend operacional recomendado do `v1` agora e `PostgreSQL`;
- nesta maquina ha um `postgres.exe` local ativo na `5432`, por isso o `docker compose` do JARVIS publica o banco em `5433`;
- o corpus do `knowledge-service` continua local e curado manualmente, agora com ranking ponderado ja absorvido no baseline;
- o `operational-service` continua deliberadamente restrito a tarefas seguras e deterministicas, sem adaptadores de alto risco;
- o `evolution-lab` segue sandbox-only e ainda nao traduz automaticamente o resultado do benchmark em mudanca do baseline;
- o lint com `ruff check` ainda ficou com pendencias de estilo nos arquivos reescritos nesta rodada, embora a suite funcional esteja verde.

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
- `services/observability-service/src/observability_service/service.py`
- `services/observability-service/tests/test_observability_service.py`
- `evolution/evolution-lab/src/evolution_lab/service.py`
- `evolution/evolution-lab/src/evolution_lab/repository.py`
- `evolution/evolution-lab/tests/test_evolution_lab_service.py`
- `tools/benchmarks/harness.py`
- `tools/benchmarks/dataset.py`
- `tools/benchmarks/datasets/v1_benchmark_cases.json`
- `tests/benchmark/test_benchmark_harness.py`
- `services/operational-service/src/operational_service/service.py`
- `services/operational-service/tests/test_operational_service.py`
- `engines/identity-engine/src/identity_engine/engine.py`
- `engines/executive-engine/src/executive_engine/engine.py`
- `engines/planning-engine/src/planning_engine/engine.py`
- `engines/cognitive-engine/src/cognitive_engine/engine.py`
- `engines/synthesis-engine/src/synthesis_engine/engine.py`
- `tests/unit/test_shared_layer.py`
- `docs/implementation/service-breakdown.md`
- `docs/architecture/technology-study-matrix.md`
- `docs/implementation/implementation-strategy.md`

---

## Como Validar / Retomar

Leitura minima para qualquer novo agente:

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

Checagens rapidas recomendadas:

- confirmar que `shared/` contem a camada canonica minima;
- validar que o `memory-service` persiste contexto entre instancias do servico;
- validar que o `governance-service` produz checagem, decisao e condicoes coerentes;
- validar que o `knowledge-service` retorna dominios e snippets para `analysis` e `planning`;
- validar que o `knowledge-service` carrega o corpus curado local esperado;
- validar que o `observability-service` registra a trilha completa de eventos;
- validar que o `evolution-lab` registra proposta e decisao sandbox-only sem promocao automatica;
- validar que o `operational-service` executa apenas tarefas seguras e produz artefatos textuais;
- executar `python -m tools.benchmarks` e revisar as decisoes por trilha;
- executar `pytest -q` diretamente da raiz e `ruff check .` na `.venv` local.

Comandos uteis:

```powershell
rg --files
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip install -e .[dev,postgres]
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/jarvis"
.\.venv\Scripts\python.exe -m tools.benchmarks --postgres-url $env:DATABASE_URL
.\.venv\Scripts\python.exe -m pytest services/memory-service/tests/test_memory_postgres_integration.py -q
```

---

## Regra Para o Proximo Agente

- tratar `documento_mestre_jarvis.md` como artefato canonico;
- usar `HANDOFF.md` como documento operacional de estado;
- atualizar `CHANGELOG.md` sempre que houver mudanca relevante;
- priorizar agora consolidacao do baseline integrado do `v1`;
- reutilizar `shared/` em vez de redefinir contratos localmente nos servicos.

---

## Criterio de Encerramento Deste Handoff

Este handoff continua util enquanto o projeto estiver consolidando o baseline integrado do `v1`.

Ele deve ser reavaliado quando:

- a primeira janela de producao controlada do `v1` tiver sido executada e registrada;
- o `knowledge-service` sair do corpus local minimo e entrar em retrieval mais robusto;
- o baseline de `M6` sair do sandbox evolutivo minimo e entrar em benchmark mais formal;
- houver mudanca arquitetural relevante que torne este handoff obsoleto.







