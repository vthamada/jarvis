# MB-151 Documentation Canonicality Audit

Status: official audit record
Date: 2026-06-30
Scope: documentation only
Functional implementation: none

## Executive Summary

This audit reviewed the active documentation surface after `MB-150`, when the
system closed the governed loop:

`usar -> registrar -> refletir -> propor -> revisar -> influenciar -> medir`.

No file was deleted, moved, renamed, merged or functionally changed during the
audit pass. The goal was to identify which documents are active, stale,
historical, duplicated, merge candidates, archive candidates or require human
decision before any cleanup.

The constitutional source remains `documento_mestre_jarvis.md`. Derived
documents must not contradict it. The active execution queue remains
`docs/implementation/execution-backlog.md`.

Main conclusion: the repository has enough information to execute a safe second
documentation pass, but not enough to move, delete or merge files without a
backlink map. The next safe item is `MB-152 -- Documentation Backlink Map & Safe
Active Docs Sync`.

## Reviewed Documents

Total documents reviewed: 73.

Reviewed areas:

- `docs/adr`
- `docs/architecture`
- `docs/archive`
- `docs/documentation`
- `docs/executive`
- `docs/future/architecture`
- `docs/implementation`
- `docs/operations`
- `docs/roadmap`
- relevant root documents: `documento_mestre_jarvis.md`, `HANDOFF.md`,
  `CHANGELOG.md`, `README.md`, `AGENTS.md`

## Active Canonical Documents

- `documento_mestre_jarvis.md`
- `AGENTS.md`
- `docs/documentation/engineering-constitution.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `docs/architecture/technology-absorption-order.md`
- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-repository-review-framework.md`
- `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md`

## Active Operational Documents

- `HANDOFF.md`
- `CHANGELOG.md`
- `README.md`
- `docs/operations/chat-transition-template.md`
- `docs/operations/operator-learning-loop.md`
- `docs/operations/incident-response.md`
- `docs/operations/release-and-change-management.md`
- `docs/documentation/engineering-constitution.md`

## Active Implementation Documents

- `docs/implementation/execution-backlog.md`
- `docs/implementation/unified-gap-and-absorption-backlog.md`
- `docs/implementation/v2-adherence-snapshot.md`

These three documents must remain separate:

- `execution-backlog.md` is the micro queue.
- `unified-gap-and-absorption-backlog.md` is the macro gap and absorption map.
- `v2-adherence-snapshot.md` is the state snapshot against the master vision.

## Documents Requiring Post-MB-150 Update

- `README.md`
- `docs/architecture/documento_evolutivo_jarvis.md`
- `docs/architecture/evolution-lab.md`
- `docs/architecture/ecosystem-verticals-map.md`
- `docs/documentation/repository-map-and-consistency-audit.md`
- `docs/executive/master-summary.md`
- `docs/implementation/service-breakdown.md`
- `docs/operations/chat-transition-template.md`
- `docs/operations/incident-response.md`
- `docs/operations/release-and-change-management.md`
- `docs/operations/v1-operational-baseline.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/roadmap/programa-de-excelencia.md`

These updates should be bounded to active-state synchronization. They must not
open new functionality or rewrite canonical architecture.

## Merge Candidates

| Document | Recommended destination | Reason |
| --- | --- | --- |
| `docs/architecture/technology-study.md` | `docs/architecture/technology-capability-extraction-map.md` and `docs/architecture/technology-absorption-order.md` | Useful content overlaps with the active absorption framework. |
| `docs/documentation/repository-map-and-consistency-audit.md` | this audit or a successor backlink map | The older audit needs synchronization with post-`MB-150` state. |
| `docs/implementation/implementation-strategy.md` | `docs/implementation/execution-backlog.md` or `docs/roadmap/programa-ate-v3.md` | Strategy content is useful but should not compete with the active queue. |
| `docs/executive/master-summary.md` | update from `v2-adherence-snapshot.md` and `unified-gap-and-absorption-backlog.md` | Executive state appears stale against the current baseline. |

No merge should be executed before `MB-152` produces a backlink map.

## Archive Candidates

- `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md`
- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md`
- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md`
- `docs/archive/implementation/v2-repository-hygiene-inventory.md`
- `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md`
- `docs/implementation/implementation-strategy.md`
- `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`
- `docs/operations/v1-operational-baseline.md`
- `docs/roadmap/v1-roadmap.md`

These documents should be preserved. They are candidates for archive movement,
not deletion.

## Removal Candidates

None.

There is no document that is safe to remove immediately. Any removal must be a
separate, explicitly approved action after backlink review.

## Human Decision Required

- `documento_mestre_jarvis.md`
- `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md`
- `docs/architecture/documento_evolutivo_jarvis.md`
- `docs/architecture/protective-intelligence-architecture.md`
- `docs/architecture/visao_ajuste_arquitetural_jarvis.md`
- `docs/documentation/matriz-de-aderencia-mestre.md`
- `docs/executive/master-summary.md`
- `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`
- `docs/roadmap/programa-ate-v3.md`
- `docs/roadmap/programa-de-excelencia.md`
- `docs/future/architecture/voice-runtime.md`
- `docs/future/architecture/specialists-v2.md`

Reason: these documents either define direction, carry governance weight,
describe deferred architecture, or may affect the sovereign core.

## Documentation Clusters

### Evolution and Operator Learning Loop

Primary document: `docs/operations/operator-learning-loop.md`.

Supporting documents:

- `docs/implementation/execution-backlog.md`
- `docs/implementation/v2-adherence-snapshot.md`
- `docs/architecture/evolution-lab.md`

Decision: do not merge the operational runbook with the backlog. The runbook
serves humans; the backlog controls implementation.

### Technology Absorption

Primary document: `docs/architecture/technology-absorption-order.md`.

Supporting documents:

- `docs/architecture/technology-capability-extraction-map.md`
- `docs/architecture/technology-repository-review-framework.md`
- `docs/architecture/technology-study.md`

Decision: keep the absorption order active. Treat the technology study as a
merge candidate or historical support after backlink review.

### Roadmap V1/V2/V3

Primary document: `docs/roadmap/programa-ate-v3.md`.

Supporting documents:

- `docs/roadmap/programa-de-excelencia.md`
- `docs/roadmap/v1-roadmap.md`

Decision: preserve `v1-roadmap.md` as historical once references are mapped.

### Repository Hygiene

Primary historical set:

- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md`
- `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `docs/archive/implementation/v2-repository-hygiene-inventory.md`
- `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md`
- `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md`

Decision: archive candidates, but only after backlink map.

### Protective Intelligence

Primary document: `docs/architecture/protective-intelligence-architecture.md`.

Supporting document:

- `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`

Decision: human decision required. This is a valid deferred vertical, not an
active implementation queue.

### Release and Change Management

Primary document: `docs/operations/release-and-change-management.md`.

Supporting documents:

- `docs/operations/incident-response.md`
- `docs/documentation/engineering-constitution.md`
- `AGENTS.md`

Decision: update active operational docs, do not merge them into one document.

### Architecture Adjustment

Primary documents:

- `documento_mestre_jarvis.md`
- `docs/architecture/documento_evolutivo_jarvis.md`
- `docs/architecture/visao_ajuste_arquitetural_jarvis.md`

Decision: human decision required for hierarchy and wording. No automatic merge.

### Implementation Backlog

Primary document: `docs/implementation/execution-backlog.md`.

Supporting documents:

- `docs/implementation/unified-gap-and-absorption-backlog.md`
- `docs/implementation/v2-adherence-snapshot.md`

Decision: do not merge. These documents have different operational roles.

## Target Documentation Organization

Proposed target structure, not executed in `MB-151`:

- `docs/architecture/`: active derived architecture and governed technology
  absorption architecture.
- `docs/operations/`: active runbooks, operator guides, release/change
  procedures and incident response.
- `docs/implementation/`: active backlog, snapshots and current implementation
  decisions.
- `docs/roadmap/`: active future plans and phase direction.
- `docs/adr/`: immutable architecture decision records.
- `docs/archive/`: closed cuts, old plans, closure records, historical
  inventories and superseded implementation material.
- Optional future `docs/research/` or `docs/technology/`: only if technology
  studies continue growing and a human decision approves the split.

## Execution Risks

- Breaking internal links from `HANDOFF.md`, `README.md`, `CHANGELOG.md` or
  implementation snapshots.
- Losing historical traceability of closed cuts.
- Archiving documents that still serve as gate evidence.
- Merging operational runbooks into backlog material and reducing usability.
- Accidentally promoting deferred architecture to active implementation.
- Creating contradictions with `documento_mestre_jarvis.md`.

## Recommended Next MB

`MB-152 -- Documentation Backlink Map & Safe Active Docs Sync`

Post-`MB-152` note: this recommendation was executed in
`docs/documentation/documentation-backlink-map-mb152.md`. The historical
recommendation remains here to preserve the `MB-151` audit trail.

Scope:

- generate a backlink map for documentation references;
- update only active stale documents;
- do not move files yet;
- do not delete files;
- do not merge sensitive documents;
- mark historical documents when safe;
- prepare a separate plan for future moves or archive actions.

Out of scope:

- deleting documents;
- moving documents to archive;
- merging canonical documents;
- changing `documento_mestre_jarvis.md`;
- changing architecture;
- opening new functionality;
- voice, realtime, browser/computer use, broad UI work or SecurityOS.

## MB-151 Closure

`MB-151` is closed as a documentation audit and reprioritization item. It did
not implement runtime functionality and did not execute broad documentation
cleanup.

## Appendix A -- Complete Reviewed Document Inventory

| Document | Category | Recommended status | Recommended action | Risk | Human decision required? | Notes |
| -------- | -------- | ------------------ | ------------------ | ---- | ------------------------ | ----- |
| `docs/future/architecture/voice-runtime.md` | future architecture | human_decision_required | needs_human_review | high | yes | Future voice/realtime material remains out of current phase. |
| `docs/future/architecture/specialists-v2.md` | future architecture | human_decision_required | needs_human_review | high | yes | Specialist evolution can affect core routing and must stay gated. |
| `docs/adr/adr-001-absorcao-parcial-de-langgraph-no-nucleo.md` | ADR | canonical_active | keep_as_is | high | yes | Immutable decision record for governed LangGraph absorption. |
| `docs/operations/operator-learning-loop.md` | operations | operational_active | keep_as_is | medium | no | Primary runbook for the current operator learning loop. |
| `docs/operations/incident-response.md` | operations | update_required | update | medium | no | Useful runbook, but should reflect post-`MB-150` signals. |
| `docs/operations/chat-transition-template.md` | operations | update_required | update | medium | no | Active handoff template should mention post-`MB-150` baseline and MB-152. |
| `docs/operations/release-and-change-management.md` | operations | update_required | update | medium | no | Release guidance should reflect current gates and learning loop evidence. |
| `docs/operations/v1-operational-baseline.md` | operations | archive_candidate | move_to_archive | medium | no | Historical baseline; preserve only after backlink map. |
| `docs/roadmap/v1-roadmap.md` | roadmap | archive_candidate | move_to_archive | medium | no | Historical roadmap; should not guide active execution. |
| `docs/roadmap/programa-de-excelencia.md` | roadmap | update_required | update | high | yes | Strategic roadmap; update only without changing phase direction. |
| `docs/roadmap/programa-ate-v3.md` | roadmap | update_required | update | high | yes | Primary active roadmap; sensitive to phase decisions. |
| `docs/executive/master-summary.md` | executive | merge_candidate | update | high | yes | Executive state appears stale; should be synced from active snapshot/backlog. |
| `docs/documentation/engineering-constitution.md` | documentation | canonical_active | keep_as_is | high | no | Engineering guardrail document used by agents and gates. |
| `docs/documentation/matriz-de-aderencia-mestre.md` | documentation | canonical_active | needs_human_review | high | yes | Bridge between master vision and implementation; avoid casual rewrites. |
| `docs/documentation/repository-map-and-consistency-audit.md` | documentation | merge_candidate | update | medium | no | Older repository audit should be reconciled with MB-151/MB-152. |
| `docs/architecture/protective-intelligence-architecture.md` | architecture | human_decision_required | needs_human_review | high | yes | Valid deferred vertical; do not promote by cleanup. |
| `docs/architecture/mem0-repository-review.md` | architecture/research | historical_keep | mark_historical | low | no | Technology review supporting absorption decisions. |
| `docs/architecture/hermes-agent-repository-review.md` | architecture/research | historical_keep | mark_historical | low | no | Technology review supporting absorption decisions. |
| `docs/architecture/evolution-lab.md` | architecture | update_required | update | medium | no | Active architecture doc should reflect reviewed learning feedback loop. |
| `docs/architecture/ecosystem-verticals-map.md` | architecture | update_required | update | high | yes | Vertical map is sensitive to deferred/active boundaries. |
| `docs/architecture/documento_evolutivo_jarvis.md` | architecture | update_required | needs_human_review | high | yes | Evolution document should align with master vision and current baseline. |
| `docs/architecture/technology-repository-review-framework.md` | architecture | canonical_active | keep_as_is | medium | no | Active framework for reviewing external repositories. |
| `docs/architecture/technology-capability-extraction-map.md` | architecture | canonical_active | keep_as_is | medium | no | Active map for extracting capabilities from technology references. |
| `docs/architecture/technology-absorption-order.md` | architecture | canonical_active | keep_as_is | medium | no | Active order for disciplined technology absorption. |
| `docs/architecture/turboquant-review.md` | architecture/research | historical_keep | mark_historical | low | no | Technology review; keep as supporting evidence. |
| `docs/architecture/technology-study.md` | architecture/research | merge_candidate | merge_into | medium | no | Useful study overlaps with active absorption docs; wait for backlinks. |
| `docs/architecture/visao_ajuste_arquitetural_jarvis.md` | architecture | human_decision_required | needs_human_review | high | yes | Architecture adjustment material can affect canonical hierarchy. |
| `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md` | implementation/history | archive_candidate | move_to_archive | low | no | Closed hygiene decision artifact; preserve traceability. |
| `docs/archive/implementation/v2-repository-hygiene-inventory.md` | implementation/history | archive_candidate | move_to_archive | low | no | Closed inventory; archive only after backlink map. |
| `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md` | implementation/history | archive_candidate | move_to_archive | low | no | Closed documentation decision artifact. |
| `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md` | implementation/history | archive_candidate | move_to_archive | medium | no | Historical cut; may still be referenced by audits. |
| `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` | implementation/history | archive_candidate | move_to_archive | medium | no | Historical closure; preserve evidence. |
| `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md` | implementation/history | archive_candidate | move_to_archive | medium | no | Historical closure for memory hardening. |
| `docs/implementation/v2-adherence-snapshot.md` | implementation | implementation_active | update | medium | no | Active snapshot; keep current with MB-151/MB-152. |
| `docs/implementation/unified-gap-and-absorption-backlog.md` | implementation | implementation_active | update | medium | no | Active macro gap map; keep separate from micro queue. |
| `docs/implementation/service-breakdown.md` | implementation | update_required | update | medium | no | Service map should reflect current post-`MB-150` capabilities. |
| `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md` | implementation/deferred | human_decision_required | needs_human_review | high | yes | Deferred vertical cut; do not activate without phase decision. |
| `docs/implementation/implementation-strategy.md` | implementation/history | merge_candidate | merge_into | medium | no | Useful strategy content should not compete with active queue. |
| `docs/implementation/execution-backlog.md` | implementation | implementation_active | keep_as_is | high | no | Canonical micro execution queue; MB-152 was the next ready item at MB-151 closure. |
| `docs/archive/executive/v1-scope-summary.md` | archive | historical_keep | keep_as_is | low | no | Preserved executive history. |
| `docs/archive/operations/internal-pilot-plan.md` | archive | historical_keep | keep_as_is | low | no | Historical pilot plan; useful for traceability. |
| `docs/archive/documentation/estrutura_de_documentos_derivados.md` | archive | historical_keep | keep_as_is | low | no | Historical documentation structure reference. |
| `docs/archive/documentation/auditoria-primaria-documento-mestre.md` | archive | historical_keep | keep_as_is | medium | no | Preserved master-document audit history. |
| `docs/archive/implementation/v2-sprint-cycle.md` | archive | historical_keep | keep_as_is | low | no | Closed sprint cycle history. |
| `docs/archive/implementation/v2-sovereign-alignment-cut.md` | archive | historical_keep | keep_as_is | low | no | Closed sovereign alignment cut. |
| `docs/archive/implementation/v2-sovereign-alignment-cut-closure.md` | archive | historical_keep | keep_as_is | low | no | Closure evidence for sovereign alignment cut. |
| `docs/archive/implementation/v2-native-memory-scope-hardening-cut.md` | archive | historical_keep | keep_as_is | low | no | Historical memory hardening cut. |
| `docs/archive/implementation/v2-memory-gap-evidence-protocol.md` | archive | historical_keep | keep_as_is | low | no | Historical evidence protocol. |
| `docs/archive/implementation/v2-memory-gap-evidence-cut.md` | archive | historical_keep | keep_as_is | low | no | Historical memory evidence cut. |
| `docs/archive/implementation/v2-memory-gap-evidence-cut-closure.md` | archive | historical_keep | keep_as_is | low | no | Closure evidence for memory gap cut. |
| `docs/archive/implementation/v2-memory-gap-decision.md` | archive | historical_keep | keep_as_is | low | no | Historical memory gap decision. |
| `docs/archive/implementation/v2-memory-gap-baseline-evidence.md` | archive | historical_keep | keep_as_is | low | no | Historical baseline evidence. |
| `docs/archive/implementation/v2-governed-benchmark-scenario-specs.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark scenario specs. |
| `docs/archive/implementation/v2-governed-benchmark-matrix.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark matrix. |
| `docs/archive/implementation/v2-governed-benchmark-execution-plan.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark execution plan. |
| `docs/archive/implementation/v2-governed-benchmark-execution-cut.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark execution cut. |
| `docs/archive/implementation/v2-governed-benchmark-execution-cut-closure.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark closure. |
| `docs/archive/implementation/v2-governed-benchmark-decisions.md` | archive | historical_keep | keep_as_is | low | no | Historical benchmark decisions. |
| `docs/archive/implementation/v2-domain-consumers-and-workflows-cut.md` | archive | historical_keep | keep_as_is | low | no | Historical domain/workflow cut. |
| `docs/archive/implementation/v2-domain-consumers-and-workflows-cut-closure.md` | archive | historical_keep | keep_as_is | low | no | Historical domain/workflow closure. |
| `docs/archive/implementation/v2-cycle-closure.md` | archive | historical_keep | keep_as_is | low | no | Closed V2 cycle record. |
| `docs/archive/implementation/v2-alignment-cycle.md` | archive | historical_keep | keep_as_is | low | no | Historical alignment cycle. |
| `docs/archive/implementation/v1-5-sprint-cycle.md` | archive | historical_keep | keep_as_is | low | no | Historical V1.5 sprint cycle. |
| `docs/archive/implementation/v1-5-cycle-closure.md` | archive | historical_keep | keep_as_is | low | no | Historical V1.5 closure. |
| `docs/archive/implementation/sprint-1-plan.md` | archive | historical_keep | keep_as_is | low | no | Early sprint plan history. |
| `docs/archive/implementation/post-v1-sprint-cycle.md` | archive | historical_keep | keep_as_is | low | no | Historical post-V1 sprint cycle. |
| `docs/archive/implementation/post-v1-cycle-closure.md` | archive | historical_keep | keep_as_is | low | no | Historical post-V1 closure. |
| `docs/archive/implementation/first-milestone-plan.md` | archive | historical_keep | keep_as_is | low | no | First milestone history. |
| `AGENTS.md` | root/governance | canonical_active | keep_as_is | high | no | Agent operating rules and gate requirements. |
| `CHANGELOG.md` | root/operations | operational_active | update | medium | no | Active change log; keep synchronized with backlog state. |
| `HANDOFF.md` | root/operations | operational_active | update | medium | no | Active resumption document; keep synchronized with MB state. |
| `README.md` | root/operations | update_required | update | medium | no | Entry point should reflect current post-`MB-150` state. |
| `documento_mestre_jarvis.md` | root/canonical | canonical_active | needs_human_review | high | yes | Sovereign constitutional source; do not change in cleanup pass. |
