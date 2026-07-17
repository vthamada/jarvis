# Knowledge Provenance And Freshness

## 1. Purpose

This document defines the minimum governed baseline introduced by `MB-173` for
knowledge-backed responses.

The baseline makes source provenance, temporal validity, declared conflicts and
uncertainty visible from retrieval through final synthesis. It does not turn the
local corpus into external truth and does not authorize autonomous ingestion,
promotion or Core mutation.

## 2. Authoritative Flow

The runtime flow is:

`curated corpus -> knowledge-service -> governance qualification -> synthesis -> observable events`

The Core remains responsible for the final response. Knowledge evidence only
qualifies the material available to planning and synthesis; it cannot change the
request permission decision by itself.

## 3. Contracts

`KnowledgeSourceEvidenceContract` records one retrieved source with:

- source and domain refs;
- source kind and confidence status;
- retrieval, publication, review and validity timestamps;
- provenance and freshness status;
- declared conflict refs and uncertainty notes.

`KnowledgeEvidenceGovernanceContract` records the bounded-use assessment with:

- aggregate provenance, freshness and conflict status;
- allowed use mode;
- conditions, blockers and uncertainty;
- human-review requirement;
- explicit prohibition of request-decision mutation, automatic promotion and
  Core mutation.

## 4. Status Semantics

Provenance:

- `complete`: source ref, source kind and review timestamp are present;
- `partial`: some source metadata exists, but the set is incomplete;
- `missing`: the retrieval has no reliable source metadata.

Freshness:

- `current`: the request timestamp is inside the declared validity window;
- `stale`: the validity window expired before the request;
- `unknown`: no valid temporal window can be evaluated.

Conflict:

- `none_declared`: the source policy declares no known conflict;
- `conflict_detected`: one or more conflict refs are declared;
- `unknown`: conflict status was not declared.

`none_declared` does not mean that independent verification proved the absence
of conflict.

## 5. Governance Policy

| Evidence state | Use mode | Human review |
| --- | --- | --- |
| Complete, current, no conflict declared | `bounded_grounding` | no |
| Partial or unknown signal | `qualified_grounding` | yes |
| Missing provenance or declared conflict | `do_not_assert_as_verified` | yes |
| Stale evidence | `historical_context_only` | yes |

This assessment is advisory for evidence use. The field
`request_decision_mutation_allowed` is always `false` in this baseline.

## 6. Observable Response

When knowledge is used, final synthesis includes a `Conhecimento:` clause with
provenance, freshness, conflict, use mode, one bounded source ref and relevant
uncertainty. `knowledge_retrieved` and `response_synthesized` retain the full
structured evidence and governance assessment for audit.

Missing metadata must remain visible as `provenance=missing` and
`freshness=unknown`; the runtime must never infer that an undated source is
current.

## 7. Current Corpus

`knowledge/curated/v1_corpus.json` is identified as `curated_internal`. Its
review and validity dates describe maintenance of this repository artifact, not
independent validation of every statement against an external authority.

## 8. Known Limits

- There is no governed external research ingestion queue yet.
- Conflict refs are surfaced but not automatically reconciled.
- Confidence remains a declared corpus property, not a probabilistic truth score.
- Only the first bounded source ref appears in human synthesis; all retrieved
  evidence remains available in events.
- Promotion, automatic learning and Core mutation remain prohibited.

## 9. Validation

The baseline is covered by knowledge, governance and synthesis unit tests plus
orchestrator end-to-end tests for current curated evidence and missing
provenance. The standard engineering gate remains mandatory.
