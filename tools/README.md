# Tools

Scripts utilitarios e ferramentas auxiliares do repositorio.

## Encoding e Mojibake

Para reparar texto ja contaminado e normalizar arquivos em `UTF-8` sem BOM com `LF`:

```powershell
python tools/fix_mojibake.py
```

Para validar que nao ha mojibake nem BOM nos arquivos de texto varridos pelo projeto:

```powershell
python tools/check_mojibake.py
```

Para validar que documentos vivos criticos mantem identidade e piso historico minimo:

```powershell
python tools/verify_document_guardrails.py
```

## Gates do baseline

Os gates executaveis do `v1` continuam sendo:

```powershell
python tools/validate_baseline.py --profile development
python tools/go_live_internal_checklist.py --profile development
python tools/validate_baseline.py --profile controlled
python tools/go_live_internal_checklist.py --profile controlled
```

A validacao agora tambem gera artefatos operacionais em `.jarvis_runtime/operational/`:

- `*-baseline-snapshot.json|md`
- `*-containment-drill.json|md`
- `*-incident-<request_id>.json|md`

## Console minimo

Para usar a interface textual minima do `v1`:

```powershell
python -m apps.jarvis_console ask "Plan the final validation window."
python -m apps.jarvis_console chat --session-id demo --mission-id mission-demo
```

Use `--debug` para expor apenas metadados minimos de request e governanca.

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

Para regenerar a matriz de benchmark governado do corte ativo:

```powershell
python tools/archive/render_governed_benchmark_matrix.py
```

Para regenerar o plano de execucao do corte ativo de benchmark sandbox:

```powershell
python tools/archive/render_governed_benchmark_execution_plan.py
```

Para regenerar os scenario specs do corte ativo de benchmark sandbox:

```powershell
python tools/archive/render_governed_benchmark_scenario_specs.py
```

Para regenerar o protocolo do corte ativo de evidencia de memoria:

```powershell
python tools/archive/render_memory_gap_evidence_protocol.py
```

Para regenerar a evidencia local por escopo do corte ativo de memoria:

```powershell
python tools/archive/render_memory_gap_baseline_evidence.py
```

Para regenerar a decisao formal do corte ativo de memoria:

```powershell
python tools/archive/render_memory_gap_decision.py
```

Para regenerar o inventario estrutural do corte ativo de revisao do repositorio:

```powershell
python tools/render_repository_hygiene_inventory.py
```

Para regenerar a decisao de classificacao dos docs ativos do corte de revisao do repositorio:

```powershell
python tools/render_repository_hygiene_doc_decisions.py
```

Para regenerar a decisao de classificacao dos entrypoints de `tools/` do corte de revisao do repositorio:

```powershell
python tools/render_repository_hygiene_tool_decisions.py
```

Para regenerar as decisoes formais do corte ativo de benchmark sandbox:

```powershell
python tools/archive/render_governed_benchmark_decisions.py
```

Para verificar o baseline `release-grade` do corte atual:

```powershell
python tools/verify_active_cut_baseline.py
```

Para fechar formalmente o `v2-governed-benchmark-execution-cut`:

```powershell
python tools/archive/close_governed_benchmark_execution_cut.py
```

Para fechar formalmente o `v2-domain-consumers-and-workflows-cut`:

```powershell
python tools/archive/close_domain_consumers_and_workflows_cut.py
```

Para fechar formalmente o `v2-memory-gap-evidence-cut`:

```powershell
python tools/archive/close_memory_gap_evidence_cut.py
```

Para fechar formalmente o `v2-native-memory-scope-hardening-cut`:

```powershell
python tools/close_native_memory_scope_hardening_cut.py
```

Para fechar formalmente o `v2-repository-hygiene-and-tools-review-cut`:

```powershell
python tools/close_repository_hygiene_and_tools_review_cut.py
```

## Internal Pilot

Para executar a janela minima do `internal pilot` e registrar evidencia local:

```powershell
python tools/run_internal_pilot.py --profile development
```

A ultima rodada do piloto passa a ser persistida tambem em `.jarvis_runtime/pilot/latest_pilot.json`.

Para resumir as trilhas recentes do `internal pilot` a partir da observabilidade local:

```powershell
python tools/internal_pilot_report.py --limit 5
```

Para comparar o baseline atual com o fluxo opcional de `LangGraph`:

```powershell
python tools/compare_orchestrator_paths.py --profile development
```

O artefato default dessa comparação passa a ser persistido em `.jarvis_runtime/path_comparison_v2/`.

Para transformar lacunas do piloto em proposals sandbox-only do `evolution-lab`:

```powershell
python tools/evolution_from_pilot.py --limit 10
python tools/evolution_from_pilot.py --comparison-json .jarvis_runtime/path_comparison.json
```

## Fechamento de ciclo histórico

Para consolidar o primeiro ciclo de continuidade profunda e emitir o corte formal entre `v1.5` e `v2`:

```powershell
python tools/archive/close_continuity_cycle.py --limit 20
```

Esse script gera artefatos em `.jarvis_runtime/post_v1_cycle/`:

- `cycle_closure.json`
- `cycle_closure.md`

Para consolidar o primeiro ciclo de runtime stateful e emitir o corte formal para `v2`:

```powershell
python tools/archive/close_stateful_runtime_cycle.py --limit 20
```

Esse script gera artefatos em `.jarvis_runtime/v1_5_cycle/`:

- `cycle_closure.json`
- `cycle_closure.md`

Para consolidar o primeiro corte de especializacao subordinada do `v2` e emitir
o fechamento orientado pelos eixos do Documento-Mestre:

```powershell
python tools/archive/close_specialization_cycle.py --limit 20
```

Esse script gera artefatos em `.jarvis_runtime/specialization_cycle/`:

- `cycle_closure.json`
- `cycle_closure.md`


Para fechar o `v2-alignment-cycle` e abrir formalmente o corte ativo seguinte do `v2`:

```powershell
python tools/archive/close_alignment_cycle.py --limit 20
```

Esse script gera artefatos em `.jarvis_runtime/v2_alignment_cycle/`:

- `cycle_closure.json`
- `cycle_closure.md`

Para fechar formalmente o `v2-sovereign-alignment-cut`:

```powershell
python tools/archive/close_sovereign_alignment_cut.py --limit 20
```

Esse script gera artefatos em `.jarvis_runtime/v2_sovereign_alignment_cut/`:

- `cut_closure.json`
- `cut_closure.md`

## Gate oficial de engenharia

O gate mínimo oficial do repositório agora é:

```powershell
python tools/engineering_gate.py --mode standard
```

Esse gate executa:

- `check_mojibake`
- `ruff check .`
- `pytest -q`

Para uma rodada mais curta:

```powershell
python tools/engineering_gate.py --mode quick
```

Para uma rodada de liberação local:

```powershell
python tools/engineering_gate.py --mode release
```

Quando houver backend controlado disponível:

```powershell
python tools/engineering_gate.py --mode release --include-controlled
```



Para verificar o baseline `release-grade` do corte ativo:

```powershell
python tools/verify_active_cut_baseline.py
```
