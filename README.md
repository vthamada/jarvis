# JARVIS

JARVIS é um sistema cognitivo unificado, stateful, governado e orientado à continuidade operacional.

Este repositório materializa o baseline encerrado do `v1` e a abertura disciplinada do `pós-v1`, sempre guiado por `documento_mestre_jarvis.md` e pelos derivados técnicos em `docs/`.

Ponte operacional entre visão e implementação:

- `docs/documentation/matriz-de-aderencia-mestre.md`

Leitura correta dessa ponte:

- a matriz agora registra a auditoria completa dos eixos canônicos do mestre;
- ela é a referência prática para dizer o que está implementado, deferido por fase ou em descompasso.

## Estado atual

O projeto já fechou o `v1` para uso controlado e opera hoje com um baseline integrado funcional:

- `orchestrator-service` coordena engines, memória, governança, conhecimento, observabilidade e operação;
- `memory-service` persiste histórico episódico, resumo contextual de sessão e estado mínimo de missão;
- `governance-service` diferencia fluxos `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` executa retrieval local determinístico para intents de `analysis` e `planning`;
- `knowledge-service` carrega o corpus curado inicial de `knowledge/curated/v1_corpus.json`;
- `knowledge-service` separa o mapa canônico de domínios em `knowledge/curated/domain_registry.json` das rotas runtime ativas do ciclo;
- `operational-service` produz artefatos textuais reais e retorna resultados estruturados;
- `observability-service` grava a trilha de eventos com correlação por `request_id`, `session_id` e `mission_id`;
- `observability-service` suporta espelhamento agentic complementar sem substituir a trilha local;
- `observability-service` audita fluxos recentes com trilha mínima obrigatória e flags automáticas de anomalia;
- `evolution-lab` compara baseline e candidata em sandbox local sem promoção automática;
- `engines/` contém os componentes ativos de identidade, execução, planejamento, cognição e síntese;
- `jarvis-console` fornece a interface textual mínima do baseline;
- `tools/validate_baseline.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py`, `tools/evolution_from_pilot.py` e `tools/archive/close_stateful_runtime_cycle.py` tornam validação, piloto, comparação, fechamento de ciclo e proposals `sandbox-only` executáveis;
- a suíte `pytest -q` passa a partir da raiz do repositório.

Leitura prática correta deste momento:

- `v1` encerrado e congelado para uso controlado;
- primeiro ciclo do `pós-v1` encerrado com continuidade profunda demonstrada;
- primeiro ciclo do `v1.5` encerrado com runtime stateful governado para continuidade;
- `v2` aberto com foco em especialização controlada subordinada ao núcleo e memória relacional mais rica;
- Sprint 1 do `v2` concluída com contratos e fronteiras mínimas de convocação de especialistas;
- Sprint 2 do `v2` concluída com seleção governada e handoff interno observável;
- Sprint 3 do `v2` concluída com memória relacional compartilhada mediada pelo núcleo e contexto persistido por especialista;
- Sprint 4 do `v2` concluída com registry inicial de domínios e primeiro especialista subordinado em `shadow mode`;
- Sprint 5 do `v2` concluída com evals de aderência do recorte de especialistas aos eixos do mestre;
- Sprint 6 do `v2` concluída com fechamento formal do primeiro corte do ciclo;
- `shared/memory_registry.py` e `shared/mind_registry.py` passaram a registrar, respectivamente, as 11 memórias e as 24 mentes do mestre como base formal do runtime progressivo;
- o ultimo recorte funcional concluido do programa agora e `v2-native-memory-scope-hardening-cut`, fechado formalmente para endurecer user scope e contexto recorrente de especialistas sem absorcao externa;
- o ultimo recorte estrutural concluido do programa agora e `v2-repository-hygiene-and-tools-review-cut`, fechado para reduzir a superficie ativa de docs e `tools` sem quebrar o baseline;
- a Sprint 1 desse novo recorte foi concluida com inventario regeneravel da superficie estrutural do repositorio;
- a Sprint 2 desse novo recorte foi concluida com decisao regeneravel de classificacao dos docs ativos da pasta `docs/implementation`;
- a Sprint 3 desse novo recorte foi concluida com decisao regeneravel de classificacao dos entrypoints da raiz de `tools/`;
- a Sprint 4 desse novo recorte foi concluida com limpeza segura, migracao para `archive` e fechamento formal do recorte;
- a auditoria completa do Documento-Mestre continua orientando o backlog real por eixo;
- o fechamento formal do corte soberano permanece regenerável por `tools/archive/close_sovereign_alignment_cut.py` em `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md`;
- o fechamento formal do corte de consumers/workflows passou a ser regenerável por `tools/archive/close_domain_consumers_and_workflows_cut.py` em `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md`.
- o plano regenerável do corte ativo passou a ser emitido por `tools/archive/render_governed_benchmark_execution_plan.py` em `docs/archive/implementation/v2-governed-benchmark-execution-plan.md`.

## Estrutura principal

- `apps/`: interfaces e superfícies de produto
- `services/`: serviços centrais do sistema
- `engines/`: engines cognitivas e executivas
- `memory/`: componentes de memória
- `knowledge/`: componentes de conhecimento e retrieval
- `governance/`: políticas e mecanismos de governança
- `observability/`: logs, traces e correlação
- `evolution/`: laboratório evolutivo
- `shared/`: contratos, schemas, tipos, eventos e estado
- `infra/`: infraestrutura e automação local
- `tests/`: testes compartilhados do repositório
- `tools/`: scripts e utilitários

## Bootstrap

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pytest -q
ruff check .
python tools/validate_baseline.py --profile development
```

Para validar o backend operacional de memória em PostgreSQL:

```powershell
python -m pip install -e ".[dev,postgres]"
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/jarvis"
python -m tools.benchmarks --postgres-url $env:DATABASE_URL
pytest services/memory-service/tests/test_memory_postgres_integration.py -q
python tools/validate_baseline.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

Para preparar o fluxo opcional de `LangGraph` no orquestrador:

```powershell
python -m pip install -e ".[dev,langgraph]"
```

Os scripts de `v1` fazem preflight explícito. Se o ambiente não estiver pronto, eles falham cedo com razões de `no-go`, incluindo `ruff` ausente e `DATABASE_URL` inválida, inacessível ou com credenciais incorretas.

Runtime local padrão:

- memória persistente: `.jarvis_runtime/memory.db`
- observabilidade local: `.jarvis_runtime/observability.db`
- evolution lab local: `.jarvis_runtime/evolution.db`
- espelhamento agentic local: `.jarvis_runtime/agentic_observability.jsonl`
- PostgreSQL local do compose: `localhost:5433`

Para aprofundar o espelhamento agentic com `LangSmith`, use:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- opcionalmente `LANGSMITH_ENDPOINT` e `LANGSMITH_WORKSPACE_ID`

O baseline atual preserva a trilha local como fonte primária e usa `LangSmith` apenas como camada complementar.

Para resumir as trilhas recentes do `internal pilot`:

```powershell
python tools/internal_pilot_report.py --limit 5
```

Para executar a janela mínima do piloto com evidência local:

```powershell
python tools/run_internal_pilot.py --profile development
```

Para comparar o baseline atual com o fluxo experimental de `LangGraph`:

```powershell
python tools/compare_orchestrator_paths.py --profile development
```

Para transformar sinais do piloto em proposals `sandbox-only` do `evolution-lab`:

```powershell
python tools/evolution_from_pilot.py --limit 10
```

### Node

```powershell
npm install
npm run lint
```

## Documentos principais

Leitura recomendada:

- `documento_mestre_jarvis.md` define o posicionamento oficial das tecnologias na stack e as referências arquiteturais por função;
- `docs/architecture/technology-study.md` aprofunda essas referências sem substituir o papel canônico do mestre.

Arquivos principais:

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut.md`
- `docs/archive/implementation/v2-memory-gap-baseline-evidence.md`
- `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md`
- `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md`
- `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`
- `docs/implementation/v2-repository-hygiene-inventory.md`
- `docs/implementation/v2-repository-hygiene-doc-decisions.md`
- `docs/implementation/v2-repository-hygiene-tool-decisions.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md`
- `docs/archive/implementation/v2-governed-benchmark-matrix.md`
- `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md`
- `docs/architecture/technology-study.md`
- `docs/implementation/implementation-strategy.md`
- `docs/implementation/service-breakdown.md`
- `docs/archive/implementation/`

Leitura recomendada do estado atual:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `docs/roadmap/programa-ate-v3.md`
4. `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md`
5. `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md`
6. `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md`
7. `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`
8. `docs/implementation/v2-repository-hygiene-inventory.md`
9. `docs/implementation/v2-repository-hygiene-doc-decisions.md`
10. `docs/implementation/v2-repository-hygiene-tool-decisions.md`
11. `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
12. `docs/archive/implementation/v2-memory-gap-decision.md`
13. `docs/archive/implementation/v2-memory-gap-baseline-evidence.md`
14. `docs/documentation/matriz-de-aderencia-mestre.md`
13. `docs/architecture/technology-study.md`
