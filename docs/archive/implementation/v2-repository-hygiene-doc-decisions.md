# V2 Repository Hygiene Doc Decisions

- cut: `v2-repository-hygiene-and-tools-review-cut`
- sprint: `sprint-2-docs-classification`

## Summary

- keep_active: `6`
- archive_candidates: `15`
- delete_candidates: `0`
- total_classified: `21`

## Keep Active

- `implementation-strategy.md`
  decisao: `manter`; racional: continua sendo referencia estrutural curta para a organizacao do repositorio e nao duplica o corte ativo
- `service-breakdown.md`
  decisao: `manter`; racional: continua util para leitura de topologia tecnica e onboarding do baseline
- `v2-adherence-snapshot.md`
  decisao: `manter`; racional: funciona como leitura transversal por eixo e ainda orienta backlog estrutural
- `v2-repository-hygiene-and-tools-review-cut.md`
  decisao: `manter`; racional: e o documento ativo de execucao do corte corrente
- `v2-repository-hygiene-inventory.md`
  decisao: `manter`; racional: e o artefato regeneravel base da revisao estrutural ativa
- `v2-native-memory-scope-hardening-cut-closure.md`
  decisao: `manter`; racional: e o fechamento funcional mais recente e ancora a transicao para a revisao atual

## Archive Candidates

- `v2-domain-consumers-and-workflows-cut.md`
  decisao: `arquivar`; racional: cut funcional ja encerrado e sucedido por closure e cortes posteriores
- `v2-domain-consumers-and-workflows-cut-closure.md`
  decisao: `arquivar`; racional: closure historico preservavel, mas nao precisa ficar na superficie principal
- `v2-governed-benchmark-execution-cut.md`
  decisao: `arquivar`; racional: cut funcional ja encerrado e sem papel de execucao atual
- `v2-governed-benchmark-execution-plan.md`
  decisao: `arquivar`; racional: artefato de apoio de recorte encerrado, util como historico regeneravel
- `v2-governed-benchmark-scenario-specs.md`
  decisao: `arquivar`; racional: scenario specs de benchmark continuam uteis, mas ja nao pertencem a area ativa
- `v2-governed-benchmark-matrix.md`
  decisao: `arquivar`; racional: a matriz continua relevante como historico de decisao, nao como doc ativo do momento
- `v2-governed-benchmark-decisions.md`
  decisao: `arquivar`; racional: decisao formal preservavel, mas ja sucedida por cortes posteriores
- `v2-governed-benchmark-execution-cut-closure.md`
  decisao: `arquivar`; racional: closure historico de benchmark, sem uso operacional direto no corte atual
- `v2-memory-gap-evidence-cut.md`
  decisao: `arquivar`; racional: cut funcional encerrado e sucedido pelo endurecimento nativo e pela revisao atual
- `v2-memory-gap-evidence-protocol.md`
  decisao: `arquivar`; racional: protocolo de recorte encerrado, melhor mantido como historico regeneravel
- `v2-memory-gap-baseline-evidence.md`
  decisao: `arquivar`; racional: evidencia importante, mas ja usada e sucedida pelo cut nativo subsequente
- `v2-memory-gap-decision.md`
  decisao: `arquivar`; racional: decisao formal preservavel, porem nao precisa ocupar a superficie ativa
- `v2-memory-gap-evidence-cut-closure.md`
  decisao: `arquivar`; racional: closure historico de recorte encerrado
- `v2-native-memory-scope-hardening-cut.md`
  decisao: `arquivar`; racional: ultimo cut funcional ja encerrado e sucedido por closure mais novo
- `v2-sovereign-alignment-cut-closure.md`
  decisao: `arquivar`; racional: closure importante, mas suficientemente historico para sair da superficie ativa

## Delete Candidates

- nenhum documento entra em delete candidate nesta sprint

## Guardrails

- nenhum arquivo classificado como arquivar deve ser movido antes da Sprint 4 do corte
- nenhum documento em delete candidate pode existir sem checagem previa de referencias vivas
- closures mais recentes continuam preservadas ativas ate a limpeza final confirmar substitutos e navegacao

## Decision Rationale

a classificacao desta sprint privilegia reducao de ruido sem perder rastreabilidade. por isso, os documentos que ainda explicam a fase atual ou a topologia do repositorio permanecem ativos, enquanto cuts, planos e evidencias de recortes ja encerrados passam a candidatos de arquivamento. nao ha delete candidate nesta fase porque todos os documentos restantes ainda possuem valor de auditoria.

