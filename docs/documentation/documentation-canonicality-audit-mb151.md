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

- `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `docs/implementation/v2-repository-hygiene-doc-decisions.md`
- `docs/implementation/v2-repository-hygiene-inventory.md`
- `docs/implementation/v2-repository-hygiene-tool-decisions.md`
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

- `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md`
- `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md`
- `docs/implementation/v2-repository-hygiene-inventory.md`
- `docs/implementation/v2-repository-hygiene-doc-decisions.md`
- `docs/implementation/v2-repository-hygiene-tool-decisions.md`

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
