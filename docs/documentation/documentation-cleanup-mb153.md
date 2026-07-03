# MB-153 Documentation Archive Move & Reference Rewrite

Status: executed conservative cleanup
Date: 2026-06-30
Scope: documentation only
Functional implementation: none

## Executive Summary

`MB-153` executes the first physical documentation cleanup after the `MB-151`
canonicality audit and the `MB-152` backlink map.

This pass did not delete documents and did not perform destructive content
merges. It moved only low/medium-risk implementation-history documents that were
already classified as archive candidates and had their backlinks identified.

Sensitive documents, canonical documents, future architecture, `v1-roadmap.md`
and `v1-operational-baseline.md` were not moved in this pass because they still
carry higher-level references or require human-reviewed phase decisions.

## Executed Moves

| Previous path | New path | Reason |
| --- | --- | --- |
| `docs/implementation/v2-native-memory-scope-hardening-cut-closure.md` | `docs/archive/implementation/v2-native-memory-scope-hardening-cut-closure.md` | Closed implementation-history closure. |
| `docs/implementation/v2-repository-hygiene-and-tools-review-cut.md` | `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut.md` | Closed repository hygiene cut. |
| `docs/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` | `docs/archive/implementation/v2-repository-hygiene-and-tools-review-cut-closure.md` | Closed repository hygiene closure. |
| `docs/implementation/v2-repository-hygiene-doc-decisions.md` | `docs/archive/implementation/v2-repository-hygiene-doc-decisions.md` | Closed documentation decision artifact. |
| `docs/implementation/v2-repository-hygiene-inventory.md` | `docs/archive/implementation/v2-repository-hygiene-inventory.md` | Closed repository hygiene inventory. |
| `docs/implementation/v2-repository-hygiene-tool-decisions.md` | `docs/archive/implementation/v2-repository-hygiene-tool-decisions.md` | Closed tool decision artifact. |

## Reference Rewrite

All literal Markdown references to the moved paths were rewritten to the new
`docs/archive/implementation/` locations.

Validation performed:

- searched for the old implementation paths after the move;
- no remaining operational backlink to the six previous paths was found outside
  this cleanup record;
- the moved files remain tracked as preserved historical records.

## Deletions

No deletion was executed.

Reason: `MB-151` found no document that was safe to remove immediately. The
correct action for historical material is preservation in `docs/archive/`, not
loss of traceability.

## Merge Handling

No destructive merge was executed.

Merge candidates from `MB-151` were handled as follows:

- `docs/documentation/repository-map-and-consistency-audit.md` remains as an
  older repository audit with explicit pointers to `MB-151`, `MB-152` and this
  cleanup record.
- `docs/executive/master-summary.md` was safely synchronized with the current
  baseline rather than merged into another document.
- `docs/architecture/technology-study.md` was not moved or merged because it
  has high backlink count and belongs to technology absorption traceability.
- `docs/implementation/implementation-strategy.md` was not moved in this pass
  because it has cross-phase references and should be handled separately if
  still desired.

## Not Moved In This Pass

- `docs/operations/v1-operational-baseline.md`: still referenced by the
  Documento-Mestre and operational docs; marked historical but kept in place.
- `docs/roadmap/v1-roadmap.md`: still referenced by the Documento-Mestre;
  marked historical but kept in place.
- `docs/implementation/pre-v3-protective-intelligence-foundation-cut.md`:
  deferred vertical requiring human decision.
- canonical, ADR, roadmap and future architecture documents: preserved in place.

## Resulting Policy

Physical documentation cleanup is allowed only when all of the following are
true:

- a backlink map exists;
- the document is not canonical or sensitive;
- references can be rewritten safely;
- historical traceability is preserved;
- standard gate passes after the change.

## Recommended Next Step

No new item is automatically ready. If further cleanup is desired, the next
decision should be explicit and choose between:

- `documentation_strategy_merge`: consolidate specific merge candidates by
  reference, without deleting source history;
- `documentation_sensitive_review`: human-reviewed decision for roadmap,
  future architecture and protective intelligence documents;
- `resume_product_backlog`: return to functional implementation after the
  documentation cleanup cut.
