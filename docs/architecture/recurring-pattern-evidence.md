# Recurring Pattern Evidence Baseline

## Purpose

This document defines the `MB-176` baseline that turns canonical operational
experience into bounded recurrence evidence. It implements only the observation
step of the governed evolution path:

`experience -> recurring pattern -> human review -> later skill candidate`

It does not create a skill, activate a workflow, authorize promotion or mutate
the sovereign Core.

## Canonical inputs

The report reads existing canonical records only:

- `ExperienceRecordContract` for workflow, route, domain, outcome and runtime
  evidence;
- `PostTaskReflectionContract` for bounded learning and recommendation refs;
- operator feedback already attached to the experience/reflection through the
  sovereign memory path.

No new learning store or parallel memory path is introduced.

## Compatibility boundary

Experiences belong to the same recurrence group only when these fields match:

1. `workflow_profile`;
2. `route`;
3. `primary_domain_driver`.

At least two distinct `experience_id` values are required. Missing scope,
mixed outcomes and absence of a successful outcome remain visible blockers.
The aggregation is bounded by `max_records` and `max_patterns`, and duplicate
experience IDs are ignored.

## Contracts

`RecurringPatternEvidenceContract` records:

- exact workflow, route and domain scope;
- occurrence and outcome counts;
- bounded confidence;
- experience, reflection, feedback and evidence refs;
- recurring checkpoints or learned-pattern signals;
- conflicts and blockers;
- explicit prohibition of skill generation, automatic skill creation,
  automatic promotion and Core mutation.

`RecurringPatternReportContract` provides a read-only aggregate with sample
size, compatible groups, eligible patterns, filters, evidence and blockers.

## Status semantics

| Status | Meaning |
| --- | --- |
| `insufficient_evidence` | Fewer than two compatible experiences exist. |
| `attention_required` | Recurrence exists, but no pattern is eligible. |
| `conflict_detected` | A group contains successful and non-successful outcomes. |
| `evidence_ready_for_human_review` | Compatible recurrence exists without a blocking conflict. |

Confidence is always bounded. Two compatible records produce
`bounded_moderate`; three or more consistent records may produce
`bounded_high`. Neither status is a promotion decision.

## Service roles

- `memory-service` reads canonical experience/reflection records and exposes a
  report builder without persisting a derived authority;
- `observability-service` exposes the same pure, read-only projection for evals
  and later operator surfaces;
- `shared/recurring_patterns.py` owns deterministic aggregation and contains no
  runtime execution or mutation path.

## Governance invariants

- `human_review_required=true`;
- `skill_candidate_generation_allowed=false`;
- `automatic_skill_creation_allowed=false`;
- `automatic_promotion_allowed=false`;
- `core_mutation_allowed=false`;
- no report status changes request governance or release authority;
- only a later, separately gated backlog item may create an inactive skill
  candidate from eligible evidence.

## Verification baseline

The automated suite covers successful recurrence, insufficient evidence,
mixed-outcome conflict, canonical memory persistence and repeated operator
corrections. The standard engineering gate remains mandatory before this
baseline is considered closed.
