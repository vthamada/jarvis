# JARVIS

JARVIS é um sistema cognitivo unificado, stateful, governado e orientado à continuidade operacional.

Este repositório materializa o baseline encerrado do `v1` e a abertura disciplinada do `pós-v1`, sempre guiado por `documento_mestre_jarvis.md` e pelos derivados técnicos em `docs/`.

## Estado atual

O projeto já fechou o `v1` para uso controlado e opera hoje com um baseline integrado funcional:

- `orchestrator-service` coordena engines, memória, governança, conhecimento, observabilidade e operação;
- `memory-service` persiste histórico episódico, resumo contextual de sessão e estado mínimo de missão;
- `governance-service` diferencia fluxos `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` executa retrieval local determinístico para intents de `analysis` e `planning`;
- `knowledge-service` carrega o corpus curado inicial de `knowledge/curated/v1_corpus.json`;
- `operational-service` produz artefatos textuais reais e retorna resultados estruturados;
- `observability-service` grava a trilha de eventos com correlação por `request_id`, `session_id` e `mission_id`;
- `observability-service` suporta espelhamento agentic complementar sem substituir a trilha local;
- `observability-service` audita fluxos recentes com trilha mínima obrigatória e flags automáticas de anomalia;
- `evolution-lab` compara baseline e candidata em sandbox local sem promoção automática;
- `engines/` contém os componentes ativos de identidade, execução, planejamento, cognição e síntese;
- `jarvis-console` fornece a interface textual mínima do baseline;
- `tools/validate_v1.py`, `tools/go_live_internal_checklist.py`, `tools/run_internal_pilot.py`, `tools/compare_orchestrator_paths.py` e `tools/evolution_from_pilot.py` tornam validação, piloto, comparação e proposals `sandbox-only` executáveis;
- a suíte `pytest -q` passa a partir da raiz do repositório.

Leitura prática correta deste momento:

- `v1` encerrado e congelado para uso controlado;
- primeiro ciclo do `pós-v1` encerrado com continuidade profunda demonstrada;
- `v1.5` aberto com foco em runtime stateful governado para continuidade;
- Sprint 1 do `v1.5` aberta como próxima frente ativa do ciclo rolante.

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
- `docs/roadmap/programa-ate-v3.md`
- `docs/implementation/post-v1-sprint-cycle.md`
- `docs/architecture/technology-study.md`
- `docs/implementation/implementation-strategy.md`
- `docs/roadmap/v1-roadmap.md`

Leitura recomendada do estado atual:

1. `HANDOFF.md`
2. `documento_mestre_jarvis.md`
3. `docs/roadmap/programa-ate-v3.md`
4. `docs/implementation/post-v1-sprint-cycle.md`
5. `docs/architecture/technology-study.md`

## Console mínimo do baseline

O baseline inclui uma interface textual mínima para uso direto do núcleo:

```powershell
python -m apps.jarvis_console ask "Plan the next continuity increment."
python -m apps.jarvis_console chat --session-id demo --mission-id mission-demo
```

O console é uma casca fina sobre o `orchestrator-service`. Web, voz e configuração plugável de LLM permanecem fora do escopo do `v1` e do primeiro ciclo do `pós-v1`.
