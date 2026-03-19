# Tools

Scripts utilitarios e ferramentas auxiliares do repositorio.

## Benchmarks

O harness local de benchmark do `v1` fica em `tools/benchmarks/`.

Execucao recomendada:

```powershell
python -m tools.benchmarks
```

Para validar explicitamente a trilha de memoria com PostgreSQL:

```powershell
python -m tools.benchmarks --postgres-url postgresql://postgres:postgres@localhost:5433/jarvis
```

Opcoes uteis:

- `--output-dir <path>` para isolar os artefatos de uma rodada;
- `--dataset-path <path>` para testar um dataset congelado alternativo;
- `--print-json` para imprimir o relatorio estruturado no stdout.

Os artefatos de saida sao persistidos em `.jarvis_runtime/benchmarks/` por padrao, com:

- relatorio `JSON` para metricas e detalhes por trilha;
- resumo `Markdown` para decisao humana.
