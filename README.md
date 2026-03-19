# JARVIS

JARVIS e um sistema agente stateful, governado e orientado a continuidade operacional.

Este repositorio materializa o caminho para o `v1` definido em `documento_mestre_jarvis.md` e nos derivados tecnicos em `docs/`.

## Estado atual

O projeto ja saiu da fundacao estrutural e possui um fluxo integrado funcional:

- `orchestrator-service` coordena engines, memoria, governanca, conhecimento, observabilidade e operacao;
- `memory-service` persiste historico episodico, resumo contextual de sessao e estado minimo de missao;
- `governance-service` diferencia fluxos `allow`, `allow_with_conditions`, `block` e `defer_for_validation`;
- `knowledge-service` executa retrieval local deterministico para intents de `analysis` e `planning`;
- `knowledge-service` carrega o corpus curado inicial de `knowledge/curated/v1_corpus.json`;
- `operational-service` produz artefatos textuais reais e retorna resultados estruturados;
- `observability-service` grava a trilha de eventos com correlacao por `request_id`, `session_id` e `mission_id`;
- `evolution-lab` compara baseline e candidata em sandbox local sem promocao automatica;
- `engines/` contem os componentes iniciais de identidade, execucao, planejamento, cognicao e sintese;
- a suite `pytest -q` passa a partir da raiz do repositorio.

Leitura pratica de milestone:

- `M1`: concluida
- `M2`: parcialmente concluida
- `M3`: substancialmente implementada
- `M4`: parcialmente implementada
- `M5`: parcialmente implementada
- `M6`: iniciada no baseline local

## Estrutura principal

- `apps/`: interfaces e superficies de produto
- `services/`: servicos centrais do sistema
- `engines/`: engines cognitivas e executivas
- `memory/`: componentes de memoria
- `knowledge/`: componentes de conhecimento e retrieval
- `governance/`: politicas e mecanismos de governanca
- `observability/`: logs, traces e correlacao
- `evolution/`: laboratorio evolutivo
- `shared/`: contratos, schemas, tipos, eventos e estado
- `infra/`: infraestrutura e automacao local
- `tests/`: testes compartilhados do repositorio
- `tools/`: scripts e utilitarios

## Bootstrap

### Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
pytest -q
ruff check .
```

Para validar o backend operacional de memoria em PostgreSQL:

```powershell
python -m pip install -e ".[dev,postgres]"
docker compose -f infra/local-postgres.compose.yml up -d
```

Runtime local padrao:

- memoria persistente: `.jarvis_runtime/memory.db`
- observabilidade local: `.jarvis_runtime/observability.db`
- evolution lab local: `.jarvis_runtime/evolution.db`

Para usar PostgreSQL na memoria persistente, defina `DATABASE_URL`.

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
