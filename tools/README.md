# Tools

Scripts utilitarios e ferramentas auxiliares do repositório.

## Benchmarks

O harness local de benchmark do `v1` fica em `tools/benchmarks/`.

Execução recomendada:

```powershell
python -m tools.benchmarks
```

Para validar explicitamente a trilha de memória com PostgreSQL:

```powershell
python -m tools.benchmarks --postgres-url postgresql://postgres:postgres@localhost:5433/jarvis
```

Opcoes uteis:

- `--output-dir <path>` para isolar os artefatos de uma rodada;
- `--dataset-path <path>` para testar um dataset congelado alternativo;
- `--print-json` para imprimir o relatório estruturado no stdout.

Os artefatos de saida sóo persistidos em `.jarvis_runtime/benchmarks/` por padrao, com:

- relatório `JSON` para métricas e detalhes por trilha;
- resumo `Markdown` para decisão humana.

## Internal Pilot

Para resumir as trilhas recentes do `internal pilot` a partir da observabilidade local:

```powershell
python tools/internal_pilot_report.py --limit 5
```

Para inspecionar uma execução específica:

```powershell
python tools/internal_pilot_report.py --request-id req-123 --format json
```

Os gates executáveis do `v1` continuam sendo:

```powershell
python tools/validate_v1.py --profile development
python tools/go_live_internal_checklist.py --profile development
```
