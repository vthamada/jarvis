# JARVIS

JARVIS e um sistema agente stateful, governado e orientado a continuidade operacional.

Este repositório materializa o caminho para o `v1` definido em `documento_mestre_jarvis.md` e nos derivados técnicos em `docs/`.

## Estado atual

O projeto já saiu da fundação estrutural e possui um fluxo integrado funcional:

- `orchestrator-service` coordena engines, memória, governança, conhecimento, observabilidade e operação;
- `memory-service` persiste histórico episódico, resumo contextual de sessão e estado mínimo de missão;
- `governance-service` diferencia fluxos `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` executa retrieval local determinístico para intents de `analysis` e `planning`;
- `knowledge-service` carrega o corpus curado inicial de `knowledge/curated/v1_corpus.json`;
- `operational-service` produz artefatos textuais reais e retorna resultados estruturados;
- `observability-service` grava a trilha de eventos com correlação por `request_id`, `session_id` e `mission_id`;
- `observability-service` suporta espelhamento agentic inicial sem substituir a trilha local;
- `observability-service` audita fluxos recentes com trilha mínima obrigatória e flags automáticas de anomalia;
- `evolution-lab` compara baseline e candidata em sandbox local sem promoção automatica;
- `engines/` contém os componentes iniciais de identidade, execução, planejamento, cognição e síntese;
- `tools/validate_v1.py` e `tools/go_live_internal_checklist.py` tornam a validação e o go-live interno executáveis;
- `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py` e `tools/evolution_from_pilot.py` operacionalizam piloto, comparação e proposals sandbox-only;
- a suite `pytest -q` passa a partir da raiz do repositório.

Leitura prática de milestone:

- `M1`: concluida
- `M2`: parcialmente concluida
- `M3`: substancialmente implementada
- `M4`: parcialmente implementada
- `M5`: parcialmente implementada
- `M6`: iniciada no baseline local

## Estrutura principal

- `apps/`: interfaces e superficies de produto
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
- `tools/`: scripts e utilitarios

## Bootstrap

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pytest -q
ruff check .
python tools/validate_v1.py --profile development
```

Para validar o backend operacional de memória em PostgreSQL:

```powershell
python -m pip install -e ".[dev,postgres]"
docker compose -f infra/local-postgres.compose.yml up -d
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5433/jarvis"
python -m tools.benchmarks --postgres-url $env:DATABASE_URL
pytest services/memory-service/tests/test_memory_postgres_integration.py -q
python tools/validate_v1.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

Para preparar a POC opcional de `LangGraph` no orquestrador:

```powershell
python -m pip install -e ".[dev,langgraph]"
```

Os scripts de `v1` fazem preflight explícito. Se o ambiente não estiver pronto, eles falham cedo com razões de `no-go`, incluindo `ruff` ausente e `DATABASE_URL` invalida, inacessivel ou com credenciais incorretas.

Runtime local padrao:

- memória persistente: `.jarvis_runtime/memory.db`
- observabilidade local: `.jarvis_runtime/observability.db`
- evolution lab local: `.jarvis_runtime/evolution.db`
- espelhamento agentic local: `.jarvis_runtime/agentic_observability.jsonl`
- PostgreSQL local do compose: `localhost:5433`

Para usar PostgreSQL na memória persistente, defina `DATABASE_URL`.

Para aprofundar o espelhamento agentic com `LangSmith`, use:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- opcionalmente `LANGSMITH_ENDPOINT` e `LANGSMITH_WORKSPACE_ID`

O baseline atual preserva a trilha local como fonte primaria e usa `LangSmith` apenas como camada complementar.

Para resumir as trilhas recentes do `internal pilot`:

```powershell
python tools/internal_pilot_report.py --limit 5
```

Para executar a janela mínima do piloto com evidência local:

```powershell
python tools/run_internal_pilot.py --profile development
```

Para comparar o baseline atual com a POC de `LangGraph`:

```powershell
python tools/compare_orchestrator_paths.py --profile development
```

Para transformar sinais do piloto em proposals sandbox-only do `evolution-lab`:

```powershell
python tools/evolution_from_pilot.py --limit 10
```

### Node

```powershell
npm install
npm run lint
```

## Documentos principais

- `documento_mestre_jarvis.md`
- `HANDOFF.md`
- `CHANGELOG.md`
- `docs/implementation/implementation-strategy.md`
- `docs/roadmap/v1-roadmap.md`
