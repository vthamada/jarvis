# Workflow Variant Eval

Status: active offline baseline from `MB-183`.

## Purpose

Workflow variant eval compares one inactive workflow candidate with its
versioned baseline under equivalent offline evidence cases. It does not bind the
candidate to routing or execute it as an active workflow.

The evaluator combines two evidence classes:

- contract evidence from the real baseline and candidate definitions;
- normalized outcome evidence supplied for the same bounded scenario.

## Required Metrics

Every case must provide baseline and candidate values between `0.0` and `1.0`
for exactly these dimensions:

- `success_score` (higher is better);
- `contract_adherence` (higher is better);
- `rework_rate` (lower is better);
- `checkpoint_coverage` (higher is better);
- `memory_causality` (higher is better).

Missing, extra or out-of-range metrics invalidate the case. A candidate must
show at least one measurable improvement and no regression in any dimension.

## Contract Checks

`run_workflow_variant_eval` requires:

- a current immutable side-registry containing the baseline and candidate;
- matching workflow, route, baseline ref and active-registry fingerprint;
- a distinct `candidate_inactive` definition with no runtime authority;
- recurring-pattern and persisted review evidence on the candidate;
- unique bounded case/scenario IDs and explicit expected candidate elements;
- offline-only cases with human review still required.

Each case validates the required candidate steps, checkpoints, decision points
and success criteria against the versioned definition before comparing metrics.

## Interpretation

- `candidate_improved_without_regression`: every case passed, at least one
  metric improved per case and none regressed.
- `candidate_regression_detected`: one or more metric dimensions degraded.
- `insufficient_or_invalid_evidence`: identity, contract, scope, metric or
  evidence checks failed.
- `candidate_ready_for_human_gate_review`: evidence may enter the next human
  gate; it is not release approval.
- `manual_gate_only`: `promotion_authorized` remains false.

`MB-184` may consume this result as one input to the existing promotion and
rollback gate. A green result alone never changes the active registry.
