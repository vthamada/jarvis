# Human Memory Lifecycle Review

Status: active baseline from `MB-187`.

## Purpose

The memory lifecycle review queue exposes bounded maintenance candidates to a
human operator. It does not consolidate, archive, expire, delete or rewrite
memory. A review decision is a disposition only; maintenance execution remains
a separate future workflow.

The governed cycle is:

`canonical signals -> candidate -> human review -> governance -> persisted disposition`

## Candidate Sources

- `consolidate`: canonical corpus telemetry reports records in
  `consolidating` state;
- `archive`: canonical corpus telemetry reports records in `aging` or
  archivable state;
- `expire`: a `ReviewedLearningGuidanceContract` reached its explicit
  `expires_at` timestamp.

Candidate identity includes its evidence snapshot. A changed count or evidence
set creates a new candidate and requires a new review.

## Console

List candidates:

```powershell
python -m apps.jarvis_console memory-review-queue --limit 10
```

Filter by maintenance action or review status:

```powershell
python -m apps.jarvis_console memory-review-queue --maintenance-action archive --review-status needs_review
```

Record an approval disposition:

```powershell
python -m apps.jarvis_console memory-review --candidate-id <candidate-id> --action approve --evidence-ref trace://review/001 --rollback-plan-ref rollback://memory/restore
```

Supported human decisions are `approve`, `reject`, `needs-review` and
`rollback`. Approval and rollback require explicit evidence and rollback refs.
Rollback is accepted only after an approved review.

## Safety Invariants

- `execution_authorized=false` for every assessment and decision;
- `automatic_execution_allowed=false` and `core_mutation_allowed=false`;
- approval never changes the source corpus or guidance;
- rollback changes only the review disposition because no maintenance ran;
- persistence remains in the canonical memory repository for SQLite and
  PostgreSQL;
- a forged assessment without the required policy trace is rejected.

Actual consolidation, archive, expiration or deletion requires a distinct,
governed, reversible workflow and is outside `MB-187`.
