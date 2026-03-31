# V2 Repository Hygiene Tool Decisions

- cut: `v2-repository-hygiene-and-tools-review-cut`
- sprint: `sprint-3-tools-classification`
- scope_note: esta sprint classifica os entrypoints da raiz de tools. internals de tools/benchmarks permanecem fora da limpeza imediata por ainda sustentarem benchmark local e validacao auxiliar

## Summary

- keep_active: `17`
- archive_candidates: `15`
- delete_candidates: `0`
- total_classified: `32`

## Keep Active

- `check_mojibake.py`
  decisao: `manter`; racional: continua sendo validacao basica de hygiene e encoding do repositorio
- `engineering_gate.py`
  decisao: `manter`; racional: e o gate central do baseline e nao pode sair da superficie ativa
- `fix_mojibake.py`
  decisao: `manter`; racional: segue util como ferramenta de reparo controlado quando houver contaminacao real
- `go_live_internal_checklist.py`
  decisao: `manter`; racional: permanece no baseline de validacao operacional e readiness local
- `validate_baseline.py`
  decisao: `manter`; racional: continua como validacao executavel do baseline oficial
- `verify_active_cut_baseline.py`
  decisao: `manter`; racional: ainda ancora o estado release-grade do ultimo recorte funcional fechado
- `verify_axis_artifacts.py`
  decisao: `manter`; racional: continua como verificador de coerencia minima entre artefatos vivos do programa
- `compare_orchestrator_paths.py`
  decisao: `manter`; racional: segue util para comparacao operacional entre baseline e fluxo opcional
- `evolution_from_pilot.py`
  decisao: `manter`; racional: continua traduzindo sinais do piloto em propostas sandbox-only
- `internal_pilot_report.py`
  decisao: `manter`; racional: permanece como leitura curta das evidencias recentes do piloto
- `internal_pilot_support.py`
  decisao: `manter`; racional: continua fornecendo agregacao de suporte ao piloto e comparadores
- `operational_artifacts.py`
  decisao: `manter`; racional: permanece util na persistencia e leitura de artefatos operacionais locais
- `run_internal_pilot.py`
  decisao: `manter`; racional: segue como entrypoint executavel do internal pilot oficial
- `render_repository_hygiene_inventory.py`
  decisao: `manter`; racional: e o renderizador base do corte ativo de higiene do repositorio
- `render_repository_hygiene_doc_decisions.py`
  decisao: `manter`; racional: e o artefato regeneravel que ancora a classificacao dos docs ativos
- `render_repository_hygiene_tool_decisions.py`
  decisao: `manter`; racional: passa a registrar de forma regeneravel a classificacao dos entrypoints de tools
- `close_native_memory_scope_hardening_cut.py`
  decisao: `manter`; racional: closure funcional mais recente ainda ancora a transicao para o corte estrutural atual

## Archive Candidates

- `close_alignment_cycle.py`
  decisao: `arquivar`; racional: fecha ciclo historico ja encerrado e fora do caminho critico atual
- `close_continuity_cycle.py`
  decisao: `arquivar`; racional: closure historico do pos-v1, preservavel sem ficar na superficie principal
- `close_domain_consumers_and_workflows_cut.py`
  decisao: `arquivar`; racional: closure de recorte funcional encerrado e ja sucedido por cortes posteriores
- `close_governed_benchmark_execution_cut.py`
  decisao: `arquivar`; racional: closure de benchmark encerrado, relevante como historico mas nao como tooling ativo
- `close_memory_gap_evidence_cut.py`
  decisao: `arquivar`; racional: closure de recorte encerrado, preservavel sem permanecer na area viva
- `close_sovereign_alignment_cut.py`
  decisao: `arquivar`; racional: closure importante do corte soberano, mas hoje ja e historico
- `close_specialization_cycle.py`
  decisao: `arquivar`; racional: closure historico de especializacao, fora do recorte operacional atual
- `close_stateful_runtime_cycle.py`
  decisao: `arquivar`; racional: closure historico do ciclo stateful, preservavel como auditoria
- `render_governed_benchmark_decisions.py`
  decisao: `arquivar`; racional: renderizador de artefato fechado do benchmark governado
- `render_governed_benchmark_execution_plan.py`
  decisao: `arquivar`; racional: artefato regeneravel de recorte encerrado, nao mais parte da superficie ativa
- `render_governed_benchmark_matrix.py`
  decisao: `arquivar`; racional: matriz historica do benchmark, preservavel sem continuar no topo do tooling vivo
- `render_governed_benchmark_scenario_specs.py`
  decisao: `arquivar`; racional: scenario specs de benchmark pertencem ao historico regeneravel do recorte encerrado
- `render_memory_gap_baseline_evidence.py`
  decisao: `arquivar`; racional: evidencia de lacuna de memoria ja usada e sucedida pelo endurecimento nativo
- `render_memory_gap_decision.py`
  decisao: `arquivar`; racional: decisao formal de recorte encerrado, relevante para auditoria e nao para uso diario
- `render_memory_gap_evidence_protocol.py`
  decisao: `arquivar`; racional: protocolo regeneravel de recorte encerrado, fora da superficie ativa atual

## Delete Candidates

- nenhuma ferramenta entra em delete candidate nesta sprint

## Guardrails

- nenhuma ferramenta exigida por engineering_gate ou verify_axis_artifacts entra em archive ou delete sem substituto explicito
- closures e renderizadores de recortes fechados so migram de fato na Sprint 4, apos checagem de referencias vivas
- nenhuma ferramenta entra em delete candidate nesta sprint porque o foco ainda e reduzir ruido sem perder auditabilidade

## Decision Rationale

a classificacao desta sprint separa tooling realmente vivo do baseline atual do tooling regeneravel historico. permanecem ativos os gates, verificadores, ferramentas do piloto, artefatos do corte de higiene e o ultimo closure funcional. renderizadores e closures de recortes ja encerrados passam a archive candidate. nao ha delete candidate nesta fase porque a limpeza segura ainda depende da Sprint 4 e da checagem final de referencias.

