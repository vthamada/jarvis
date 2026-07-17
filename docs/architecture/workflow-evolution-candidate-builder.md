# Workflow Evolution Candidate Builder

## Purpose

`MB-182` connects reviewed recurring-pattern evidence to an explicit workflow
delta without changing the sovereign active workflow registry.

The bounded chain is:

`experience/reflection -> recurring pattern -> human pattern review -> explicit
delta -> inactive workflow candidate -> side registry`

Pattern review only authorizes construction of a candidate. It does not approve
the resulting workflow version, activate it or promote it.

## Contracts

`WorkflowEvolutionRequestContract` declares:

- pattern, persisted review decision and baseline refs;
- candidate numeric semver;
- additions and removals for steps, checkpoints, decision points and success
  criteria;
- evidence, proposed tests, risk, change summary and rollback;
- explicit denial of automatic build, active-registry write, runtime activation,
  automatic promotion and Core mutation.

`WorkflowEvolutionBuildResultContract` records the normalized delta, evidence,
blockers and optional `WorkflowProfileVersionContract`. A blocked build always
returns `candidate=None`.

## Review integrity

`create_workflow_pattern_review_proposal` persists the eligible pattern,
baseline identity, baseline definition hash and sovereignty policy in the
existing evolution review queue.

The builder accepts only `approved` or `sandboxed` decisions whose ID, status,
action, operator and timestamp match the latest review persisted on that
proposal. An object that merely claims an approved status is insufficient.

The pattern and baseline are revalidated at build time. Changed route, profile,
definition, conflicts, non-successful recurrence or insufficient evidence block
the build even if an earlier proposal was reviewed.

## Delta boundary

Every delta is explicit, ordered and bounded. The builder rejects:

- empty or no-op deltas;
- duplicate additions/removals;
- additions already present in the baseline;
- removals absent from the baseline;
- add/remove conflicts;
- empty or oversized resulting workflow sections;
- candidate versions that do not advance the baseline;
- missing evidence, tests, change summary or rollback;
- risk above `moderate` or any authority claim.

A successful result is still `candidate_inactive`, `needs_review`,
`inactive_candidate` and sandbox-required. Registration creates a new immutable
side-registry snapshot. It never writes to the active route registry.

## Next gate

`MB-183` must compare baseline and candidate under equivalent offline cases.
Even a passing comparison cannot authorize promotion; workflow release and
rollback remain reserved for the later human-governed gate.
