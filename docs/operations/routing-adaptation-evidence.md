# Routing Adaptation Evidence

Status: active read-only baseline from `MB-185`.

## Purpose

Routing adaptation evidence compares the route, workflow and specialist
expected by an existing domain eval case with the path observed at runtime. It
also carries the operational outcome and memory-causality status so repeated
mismatches are not interpreted without execution context.

This mechanism measures and proposes. It never changes the active router,
registry, specialist binding or Core policy.

## Evidence Flow

`tools/routing_adaptation_evidence.py` correlates existing
`DomainEvalCaseContract` and `DomainEvalCaseResultContract` records by
`case_id`. Each bounded observation records:

- expected and observed route;
- expected and observed workflow;
- expected and observed specialist;
- operational outcome;
- memory-causality status;
- mission, eval and trace evidence.

`ObservabilityService.build_routing_adaptation_report` groups only route
mismatches from promoted expected routes. At least two coherent observations
are required. A group does not become a candidate when it has conflicting
observed routes, mixed outcomes, conflicting memory status, conflicting
specialist sets, missing evidence or an authority claim.

## Interpretation

- `evidence_ready_for_human_review`: at least one recurring and coherent
  mismatch produced a `needs_review` candidate.
- `no_adaptation_candidate`: evidence is valid but recurrence is insufficient
  or every route matched.
- `attention_required`: evidence conflicts and needs human interpretation.
- `blocked`: input, registry, scope or authority invariants failed.

The candidate treats the observed route as the current measured path and the
promoted expected route as the proposed correction target. This is a review
hypothesis, not proof that the router should change.

## Evolution Review

`EvolutionLabService.create_proposal_from_routing_adaptation_candidate`
persists the candidate as `routing_adaptation_candidate`. The proposal includes
observations, evidence, equivalent eval requirements, tests and a rollback ref.
It appears in the existing human review queue with `sandbox_only` safety.

All of these values remain false:

- `routing_write_allowed`;
- `runtime_activation_allowed`;
- `promotion_authorized`;
- `automatic_promotion_allowed`;
- `core_mutation_allowed`.

Any later routing change requires a separate sandbox comparison, release gate
and explicit human decision.
