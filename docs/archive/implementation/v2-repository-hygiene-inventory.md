# V2 Repository Hygiene Inventory

- cut: `v2-repository-hygiene-and-tools-review-cut`
- sprint: `sprint-1-regenerable-inventory`
- active_cut_doc: `v2-repository-hygiene-and-tools-review-cut.md`

## Summary

- implementation_docs: `9`
- implementation_closures: `2`
- supporting_implementation_docs: `4`
- archived_implementation_docs: `25`
- tool_scripts: `18`
- archived_tool_scripts: `15`
- baseline_validation_tools: `7`
- operational_evidence_tools: `6`
- render_tools: `3`
- closure_tools: `2`
- uncategorized_tools: `0`

## Implementation Docs

### Active Execution

- `v2-repository-hygiene-and-tools-review-cut.md`

### Foundational Support

- `implementation-strategy.md`
- `service-breakdown.md`

### Supporting Artifacts

- `v2-adherence-snapshot.md`
- `v2-repository-hygiene-doc-decisions.md`
- `v2-repository-hygiene-inventory.md`
- `v2-repository-hygiene-tool-decisions.md`

### Closure Docs

- `v2-native-memory-scope-hardening-cut-closure.md`
- `v2-repository-hygiene-and-tools-review-cut-closure.md`

### Archived History

- `first-milestone-plan.md`
- `post-v1-cycle-closure.md`
- `post-v1-sprint-cycle.md`
- `sprint-1-plan.md`
- `v1-5-cycle-closure.md`
- `v1-5-sprint-cycle.md`
- `v2-alignment-cycle.md`
- `v2-cycle-closure.md`
- `v2-domain-consumers-and-workflows-cut-closure.md`
- `v2-domain-consumers-and-workflows-cut.md`
- `v2-governed-benchmark-decisions.md`
- `v2-governed-benchmark-execution-cut-closure.md`
- `v2-governed-benchmark-execution-cut.md`
- `v2-governed-benchmark-execution-plan.md`
- `v2-governed-benchmark-matrix.md`
- `v2-governed-benchmark-scenario-specs.md`
- `v2-memory-gap-baseline-evidence.md`
- `v2-memory-gap-decision.md`
- `v2-memory-gap-evidence-cut-closure.md`
- `v2-memory-gap-evidence-cut.md`
- `v2-memory-gap-evidence-protocol.md`
- `v2-native-memory-scope-hardening-cut.md`
- `v2-sovereign-alignment-cut-closure.md`
- `v2-sovereign-alignment-cut.md`
- `v2-sprint-cycle.md`

## Tool Inventory

### Baseline Validation

- `check_mojibake.py`
- `engineering_gate.py`
- `fix_mojibake.py`
- `go_live_internal_checklist.py`
- `validate_baseline.py`
- `verify_active_cut_baseline.py`
- `verify_axis_artifacts.py`

### Operational Evidence

- `compare_orchestrator_paths.py`
- `evolution_from_pilot.py`
- `internal_pilot_report.py`
- `internal_pilot_support.py`
- `operational_artifacts.py`
- `run_internal_pilot.py`

### Render Artifacts

- `render_repository_hygiene_doc_decisions.py`
- `render_repository_hygiene_inventory.py`
- `render_repository_hygiene_tool_decisions.py`

### Active Cut Closures

- `close_native_memory_scope_hardening_cut.py`
- `close_repository_hygiene_and_tools_review_cut.py`

### Archived History

- `close_alignment_cycle.py`
- `close_continuity_cycle.py`
- `close_domain_consumers_and_workflows_cut.py`
- `close_governed_benchmark_execution_cut.py`
- `close_memory_gap_evidence_cut.py`
- `close_sovereign_alignment_cut.py`
- `close_specialization_cycle.py`
- `close_stateful_runtime_cycle.py`
- `render_governed_benchmark_decisions.py`
- `render_governed_benchmark_execution_plan.py`
- `render_governed_benchmark_matrix.py`
- `render_governed_benchmark_scenario_specs.py`
- `render_memory_gap_baseline_evidence.py`
- `render_memory_gap_decision.py`
- `render_memory_gap_evidence_protocol.py`

### Uncategorized


## Guardrails

- o inventario continua regeneravel mesmo apos a limpeza, para impedir que a superficie ativa volte a crescer sem rastreabilidade
- arquivos exigidos por engineering_gate ou verify_axis_artifacts permanecem fora de delete candidate sem substituto
- tools/archive e docs/archive preservam historico regeneravel sem poluir a area principal

## Next Step

- usar este inventario em conjunto com as decisoes e o closure do recorte para manter a superficie ativa enxuta antes da abertura do proximo corte funcional

