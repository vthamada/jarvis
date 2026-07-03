# MB-152 Documentation Backlink Map & Safe Active Docs Sync

Status: official backlink map and safe sync record
Date: 2026-06-30
Scope: documentation only
Functional implementation: none

## Executive Summary

`MB-152` follows the `MB-151` documentation canonicality audit. Its purpose is
to make documentation cleanup safer by mapping backlinks before any physical
cleanup action.

No document was moved, deleted, renamed or merged in this pass. Sensitive
canonical documents remained separate. The only synchronization allowed here is
bounded active-state correction in stale active documents and safe historical
marking where the document is clearly not the active execution source.

Main conclusion: several archive candidates still have active backlinks from
`README.md`, `HANDOFF.md`, `CHANGELOG.md`, the older repository audit and active
snapshots. A future cleanup must therefore be a separate MB with an explicit
move/archive plan and reference updates.

## Method

The backlink map was produced by scanning the 73 documents reviewed in `MB-151`
for literal mentions of each reviewed document path or filename.

Limits:

- this is a static documentation reference map, not a semantic dependency graph;
- implicit references without path or filename may be missing;
- generated/local runtime artifacts were not treated as sources of truth;
- this pass does not authorize moves, deletes or merges.

## Complete Backlink Inventory

| Document | Inbound refs | Representative referrers | MB-152 reading |
| --- | ---: | --- | --- |
| `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` | 2 | `repository-map-and-consistency-audit.md`, `CHANGELOG.md` | Keep as ADR/canonical. |
| `docs/architecture/documento_evolutivo_jarvis.md` | 1 | `execution-backlog.md` | Active but sensitive; needs human-reviewed sync. |
| `docs/architecture/ecosystem-verticals-map.md` | 1 | `CHANGELOG.md` | Active architecture; update only with phase care. |
| `docs/architecture/evolution-lab.md` | 3 | `repository-map-and-consistency-audit.md`, `CHANGELOG.md` | Active architecture; safe to sync current baseline. |
| `docs/architecture/hermes-agent-repository-review.md` | 2 | `technology-absorption-order.md`, `technology-study.md` | Historical technology review. |
| `docs/architecture/mem0-repository-review.md` | 5 | `technology-capability-extraction-map.md`, `technology-study.md`, `HANDOFF.md` | Historical/reference technology review. |
| `docs/architecture/protective-intelligence-architecture.md` | 5 | `ecosystem-verticals-map.md`, `execution-backlog.md`, `CHANGELOG.md` | Human decision required; deferred vertical. |
| `docs/architecture/technology-absorption-order.md` | 8 | `technology-capability-extraction-map.md`, `execution-backlog.md`, `HANDOFF.md` | Active canonical derived architecture. |
| `docs/architecture/technology-capability-extraction-map.md` | 7 | `technology-absorption-order.md`, `unified-gap-and-absorption-backlog.md`, `HANDOFF.md` | Active canonical derived architecture. |
| `docs/architecture/technology-repository-review-framework.md` | 5 | `technology-absorption-order.md`, `technology-study.md`, `HANDOFF.md` | Active canonical derived architecture. |
| `docs/architecture/technology-study.md` | 22 | `technology-absorption-order.md`, `technology-capability-extraction-map.md`, archived cuts | High backlink count; do not move before dedicated plan. |
| `docs/architecture/turboquant-review.md` | 3 | `technology-absorption-order.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical/reference technology review. |
| `docs/architecture/visao_ajuste_arquitetural_jarvis.md` | 1 | `CHANGELOG.md` | Human decision required. |
| `docs/archive/documentation/auditoria-primaria-documento-mestre.md` | 3 | `repository-map-and-consistency-audit.md`, `programa-de-excelencia.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/documentation/estrutura_de_documentos_derivados.md` | 2 | `repository-map-and-consistency-audit.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/executive/v1-scope-summary.md` | 3 | `estrutura_de_documentos_derivados.md`, `repository-map-and-consistency-audit.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/implementation/first-milestone-plan.md` | 3 | `estrutura_de_documentos_derivados.md`, `v2-repository-hygiene-inventory.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/implementation/post-v1-cycle-closure.md` | 5 | `post-v1-sprint-cycle.md`, `v1-5-sprint-cycle.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/implementation/post-v1-sprint-cycle.md` | 6 | `implementation-strategy.md`, `v1-roadmap.md`, `documento_mestre_jarvis.md` | Historical keep. |
| `docs/archive/implementation/sprint-1-plan.md` | 4 | `first-milestone-plan.md`, `v2-repository-hygiene-inventory.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/implementation/v1-5-cycle-closure.md` | 6 | `v1-5-sprint-cycle.md`, `v2-sprint-cycle.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v1-5-sprint-cycle.md` | 6 | `post-v1-cycle-closure.md`, `v2-sprint-cycle.md`, `documento_mestre_jarvis.md` | Historical keep. |
| `docs/archive/implementation/v2-alignment-cycle.md` | 6 | `v2-cycle-closure.md`, `v2-sovereign-alignment-cut.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-cycle-closure.md` | 6 | `v2-alignment-cycle.md`, `v2-sprint-cycle.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` | 9 | `execution-backlog.md`, `README.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md` | 6 | `technology-study.md`, `README.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-governed-benchmark-decisions.md` | 6 | `v2-governed-benchmark-execution-cut.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` | 6 | `v2-governed-benchmark-execution-cut.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-governed-benchmark-execution-cut.md` | 3 | `v2-repository-hygiene-doc-decisions.md`, `CHANGELOG.md` | Historical keep. |
| `docs/archive/implementation/v2-governed-benchmark-execution-plan.md` | 6 | `master-summary.md`, `README.md`, `CHANGELOG.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-governed-benchmark-matrix.md` | 11 | `technology-study.md`, `v2-governed-benchmark-execution-cut.md`, hygiene docs | Historical keep with high backlinks. |
| `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md` | 5 | `v2-governed-benchmark-execution-cut.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-memory-gap-baseline-evidence.md` | 7 | `v2-memory-gap-evidence-cut.md`, `README.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-memory-gap-decision.md` | 7 | `v2-memory-gap-evidence-cut.md`, `README.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md` | 6 | `v2-native-memory-scope-hardening-cut.md`, `README.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-memory-gap-evidence-cut.md` | 5 | `README.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-memory-gap-evidence-protocol.md` | 5 | `v2-memory-gap-evidence-cut.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md` | 6 | `master-summary.md`, `README.md`, `HANDOFF.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md` | 7 | `master-summary.md`, `README.md`, `CHANGELOG.md` | Historical keep with active backlinks. |
| `docs/archive/implementation/v2-sovereign-alignment-cut.md` | 4 | `v2-domain-consumers-and-workflows-cut.md`, `CHANGELOG.md`, `HANDOFF.md` | Historical keep. |
| `docs/archive/implementation/v2-sprint-cycle.md` | 6 | `v1-5-cycle-closure.md`, `v1-5-sprint-cycle.md`, `documento_mestre_jarvis.md` | Historical keep. |
| `docs/archive/operations/internal-pilot-plan.md` | 3 | `repository-map-and-consistency-audit.md`, `v1-operational-baseline.md`, `CHANGELOG.md` | Historical keep. |
| `docs/documentation/engineering-constitution.md` | 5 | `AGENTS.md`, `CHANGELOG.md`, `HANDOFF.md` | Active canonical guardrail. |
| `docs/documentation/matriz-de-aderencia-mestre.md` | 15 | `protective-intelligence-architecture.md`, archived cuts, `CHANGELOG.md` | Active canonical bridge; human-reviewed changes only. |
| `docs/documentation/repository-map-and-consistency-audit.md` | 3 | `execution-backlog.md`, `CHANGELOG.md`, `HANDOFF.md` | Active but now superseded for docs by MB-151/MB-152. |
| `docs/executive/master-summary.md` | 10 | archived cuts, `repository-map-and-consistency-audit.md`, `CHANGELOG.md` | Active executive summary; safe sync required. |
| `docs/future/architecture/specialists-v2.md` | 2 | `estrutura_de_documentos_derivados.md`, `CHANGELOG.md` | Future architecture; human decision required. |
| `docs/future/architecture/voice-runtime.md` | 2 | `estrutura_de_documentos_derivados.md`, `CHANGELOG.md` | Future architecture; human decision required. |
| `docs/implementation/execution-backlog.md` | 9 | `documento_evolutivo_jarvis.md`, `programa-ate-v3.md`, `CHANGELOG.md` | Active micro queue. |
| `docs/implementation/implementation-strategy.md` | 7 | `repository-map-and-consistency-audit.md`, `README.md`, `documento_mestre_jarvis.md` | Merge/archive candidate with backlinks; do not move yet. |
| `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md` | 3 | `execution-backlog.md`, `CHANGELOG.md`, `HANDOFF.md` | Deferred vertical; human decision required. |
| `docs/implementation/service-breakdown.md` | 8 | `repository-map-and-consistency-audit.md`, `programa-de-excelencia.md`, `README.md` | Active support doc; safe sync later. |
| `docs/implementation/unified-gap-and-absorption-backlog.md` | 7 | `documento_evolutivo_jarvis.md`, `execution-backlog.md`, `HANDOFF.md` | Active macro map. |
| `docs/implementation/v2-adherence-snapshot.md` | 12 | `repository-map-and-consistency-audit.md`, `master-summary.md`, `execution-backlog.md` | Active snapshot. |
| `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md` | 9 | `repository-map-and-consistency-audit.md`, `master-summary.md`, `HANDOFF.md` | Archive candidate with active backlinks. |
| `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` | 7 | `repository-map-and-consistency-audit.md`, `master-summary.md`, `README.md` | Archive candidate with active backlinks. |
| `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md` | 8 | `repository-map-and-consistency-audit.md`, `programa-ate-v3.md`, `README.md` | Archive candidate with active backlinks. |
| `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md` | 5 | `repository-map-and-consistency-audit.md`, `HANDOFF.md`, `README.md` | Archive candidate with active backlinks. |
| `docs/archive/implementation/v2-repository-hygiene-inventory.md` | 5 | `repository-map-and-consistency-audit.md`, `HANDOFF.md`, `README.md` | Archive candidate with active backlinks. |
| `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md` | 5 | `repository-map-and-consistency-audit.md`, `HANDOFF.md`, `README.md` | Archive candidate with active backlinks. |
| `docs/operations/chat-transition-template.md` | 3 | `execution-backlog.md`, `CHANGELOG.md`, `HANDOFF.md` | Active operational template; safe sync required. |
| `docs/operations/incident-response.md` | 6 | `repository-map-and-consistency-audit.md`, `v1-operational-baseline.md`, `CHANGELOG.md` | Active runbook; safe sync required. |
| `docs/operations/operator-learning-loop.md` | 5 | `execution-backlog.md`, `unified-gap-and-absorption-backlog.md`, `HANDOFF.md` | Active operator runbook. |
| `docs/operations/release-and-change-management.md` | 6 | `repository-map-and-consistency-audit.md`, `incident-response.md`, `v1-operational-baseline.md` | Active runbook; safe sync required. |
| `docs/operations/v1-operational-baseline.md` | 8 | `repository-map-and-consistency-audit.md`, `programa-ate-v3.md`, `HANDOFF.md` | Historical baseline with active backlinks; mark historical, do not move. |
| `docs/roadmap/programa-ate-v3.md` | 16 | `technology-study.md`, `matriz-de-aderencia-mestre.md`, `execution-backlog.md` | Active roadmap; human-reviewed updates only. |
| `docs/roadmap/programa-de-excelencia.md` | 4 | `execution-backlog.md`, `v2-adherence-snapshot.md`, `HANDOFF.md` | Strategic roadmap; human-reviewed updates only. |
| `docs/roadmap/v1-roadmap.md` | 2 | `CHANGELOG.md`, `documento_mestre_jarvis.md` | Historical roadmap; already safe-marked. |
| `AGENTS.md` | 3 | `chat-transition-template.md`, `CHANGELOG.md`, `HANDOFF.md` | Active governance instructions. |
| `CHANGELOG.md` | 11 | archived docs, `execution-backlog.md`, operations docs | Active operational log. |
| `HANDOFF.md` | 36 | architecture docs, archived cuts, implementation docs | Active operational handoff; highest backlink hub. |
| `README.md` | 17 | technology reviews, archived cuts, hygiene docs | Active entry point; safe sync required. |
| `documento_mestre_jarvis.md` | 21 | architecture docs, archived cycles, `CHANGELOG.md` | Sovereign constitutional source; no changes here. |

## High-Coupling Documents

Documents with high inbound references require extra care before any future
archive or merge:

- `HANDOFF.md`: 36 inbound references.
- `docs/architecture/technology-study.md`: 22 inbound references.
- `documento_mestre_jarvis.md`: 21 inbound references.
- `README.md`: 17 inbound references.
- `docs/roadmap/programa-ate-v3.md`: 16 inbound references.
- `docs/documentation/matriz-de-aderencia-mestre.md`: 15 inbound references.
- `docs/implementation/v2-adherence-snapshot.md`: 12 inbound references.
- `CHANGELOG.md`: 11 inbound references.
- `docs/archive/implementation/v2-governed-benchmark-matrix.md`: 11 inbound references.
- `docs/executive/master-summary.md`: 10 inbound references.

## Safe Sync Performed In MB-152

This MB may update only active-state reading and historical markers. The safe
sync target is:

- mark the older repository map as superseded for documentation canonicality by
  `MB-151` and `MB-152`, without deleting it;
- update active entry-point documents so a human sees the post-`MB-150` baseline
  and the documentation audit state;
- mark `docs/operations/v1-operational-baseline.md` as historical context, not
  current operational baseline;
- preserve `docs/roadmap/v1-roadmap.md` as historical roadmap;
- leave canonical and sensitive architecture documents untouched.

## Deferred Cleanup Plan

Any future physical cleanup must be a separate MB and must:

- update backlinks before moves;
- preserve historical traceability;
- avoid changing `documento_mestre_jarvis.md`;
- avoid merging canonical documents;
- keep runbooks separate from backlog documents;
- run the standard gate after every bounded cleanup pass.

Recommended future item after human approval:

`MB-153 -- Documentation Archive Move Plan & Reference Rewrite`

This future item should prepare a move plan only for low-risk archive candidates
with backlinks already identified. It must still require explicit approval
before moving files.

Post-`MB-153` note: the conservative subset of this plan was executed in
`docs/documentation/documentation-cleanup-mb153.md`. Six implementation-history
documents were moved to `docs/archive/implementation/`; no document was deleted
and no destructive content merge was performed.
