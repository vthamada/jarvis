# Decision-Memory Outcome Attribution

Status: active baseline from MB-205.

## Purpose

This baseline links the workflow policy and governed memory guidance that
participated in one runtime decision to the outcome observed for the same
request. It produces read-only evidence for inspection and later evaluation;
it does not prove a counterfactual effect, establish gain, authorize promotion,
dispatch tools, or mutate Core state.

## Canonical classifications

- `correlation_only`: the same governed trace contains a participant and an
  observed outcome, but no explicit bounded runtime effect was declared;
- `declared_causality`: the governed runtime explicitly declared how the
  participant affected planning or guidance. This means declared participation
  only, not proof that the participant caused the outcome;
- `insufficient_evidence`: identity, outcome, provenance, governance, authority
  boundaries, or another required part of the trace is missing or inconsistent.

Any classification-time limitation clears `declared_causal_refs`. Participants
may remain visible only as correlated evidence. Later report or feedback
limitations do not mutate the immutable record. `causal_effect_proven` is
always `false`, and `gain_claim_status` remains
`not_established_without_comparator`.

## Runtime sequence

The native and LangGraph paths use the same sequence:

1. atomically claim the `request_id -> session_id` binding in canonical memory
   before any other runtime side effect; sequential, concurrent or cross-session
   reuse fails closed;
2. resolve the versioned workflow policy and memory influence decision;
3. assess memory influence through governance;
4. build and synthesize the governed response, with operation execution only
   through the existing operation boundary;
5. persist the experience/outcome, preserving the actual operation status,
   including `failed`;
6. classify and append one `DecisionOutcomeAttributionRecordContract` for the
   same request;
7. emit `decision_outcome_attribution_recorded` with the complete canonical
   `asdict(record)` payload, or emit
   `decision_outcome_attribution_failed` without retrying the operation;
8. let `FlowAudit` project the event, while the report/tool/CLI/longitudinal
   consumers require the canonical record and perform exact feedback joins.

An operational failure and an attribution failure are separate axes. A failed
operation produces a valid persisted experience and attribution with
`outcome_status=failed`. A later attribution write/classification failure emits
`decision_outcome_attribution_failed`, normally without a canonical attribution
record, and never retries the completed operation.

Attribution is never used by `recover_for_input`, planning, dispatch, or
promotion. It is evidence about a completed trace, not a new memory signal.

## Immutable storage

SQLite and PostgreSQL store one canonical JSON payload and SHA-256 fingerprint
per `attribution_record_id`, with `request_id` also unique. Inserts are atomic;
an identical retry is idempotent and a divergent reuse of either identity is a
conflict. Database guards reject update and delete operations.

The runtime request claim is also atomic and append-only. A record is accepted
only when its request/session pair matches that claim, its `experience_id` is
exactly `experience://{mission_id}/{request_id}`, `outcome_ref` equals that
`experience_id`, and the experience already exists with the same mission,
workflow, route, outcome status and timestamp. Experience identity and outcome
fields are immutable at the repository boundary. Feedback through the Core may
only enrich `user_feedback`, experience evidence/signal refs, and reflection
evidence/proposed tests without rewriting the observed identity or outcome.

Reads revalidate payload, fingerprint, indexed identity, canonical
classification, and authority flags. Scoped listing applies request, mission,
and workflow filters before storage limits, paginates past invalid rows, and
applies the public offset only to verified records. Direct or malformed rows
cannot starve a valid attribution result.

## Evidence and feedback

Each record preserves request, session, mission, experience, governance
decision, workflow policy identity/version/fingerprint/effects, memory policy
decision, selected and ignored refs, use/non-use reasons, signal kinds,
playbook version/review refs, outcome, limitations, and event evidence refs.
The recorded event must contain every field from `asdict(record)` with equal
values; an absent or mismatched field downgrades the effective report
classification to `insufficient_evidence`.

Operator feedback is joined only by the exact `experience_id` and matching
mission. All matching append-only feedback within the bounded source window
remains visible. Simple absence yields `feedback_status=not_available` and is
not a limitation. A feedback event with missing identity, an orphaned
experience, mission mismatch, malformed fields or conflicting assessments does
become a limitation, but never mutates or raises the attribution classification.
Source truncation is reported explicitly.

## Report and operator surface

Use either form:

```powershell
python tools/decision_attribution_report.py
python -m apps.jarvis_console decision-attribution
```

The report requires canonical memory records and matching attribution events.
It exposes counts for all three classifications, exact feedback, evidence and
limitations. `failed_record_count` counts validated
`decision_outcome_attribution_failed` events, including failures without a
canonical record; it does not count successful attribution records whose
observed operational `outcome_status` is `failed`. Text and JSON output keep the
following boundaries explicit:

```text
decision_attribution=read_only
causality_scope=runtime_declared_participation_only
causal_effect_proven=False
gain_claim_status=not_established_without_comparator
promotion_authorized=False
automatic_promotion_allowed=False
core_mutation_allowed=False
```

## Operational limitations

- MB-205 records participation and observed outcomes; it does not create the
  controlled, equivalent comparator required for a gain claim;
- evidence carrying
  `gain-claim-status:not_established_without_comparator` cannot produce
  `sustained_gain` in the longitudinal report;
- old traces are not heuristically backfilled;
- a consumed request claim is never released automatically after a partial
  failure; operator inspection is required instead of unsafe replay;
- correlation and positive feedback do not prove improvement;
- `declared_causality` is a runtime statement about guidance application, not
  causal-effect identification;
- PostgreSQL integration tests require an explicit `DATABASE_URL`; the same
  append-only SQL path remains covered by deterministic repository tests when a
  live database is unavailable.
