# Workflow Variant Eval

Status: active controlled baseline from `MB-183`, hardened through `MB-206`.

## Purpose

Workflow variant eval compares one inactive workflow candidate with its
versioned baseline under equivalent offline evidence cases. It does not bind the
candidate to routing or execute it as an active workflow.

The evaluator combines three versioned evidence classes:

- contract evidence from the real baseline and candidate definitions;
- one immutable control snapshot shared by both arms, including input, fixed
  clock, seed, workflow policy, governance policy and memory-policy refs;
- two preproduced sandbox observations for the same bounded scenario.

It does not call the Core, execute a workflow or dispatch a tool. The
observations are externally produced sandbox attestations, not proof that this
evaluator executed the claimed outcome. Registration fingerprints exactly what
was attested and fails closed when full definition snapshots, hashes, control,
outcome identity or authority flags are inconsistent. Authenticity of the
external producer remains an explicit limitation until a future governed
artifact-ingestion seam exists.

## Required Metrics

Every case derives baseline and candidate values between `0.0` and `1.0` for
exactly these dimensions:

- `success_score` (higher is better);
- `contract_adherence` (higher is better);
- `rework_rate` (lower is better);
- `checkpoint_coverage` (higher is better);
- `memory_causality` (higher is better).

There is no caller-supplied metrics API. Outcome status, contract checks,
rework, expected/observed checkpoints and declared memory participation are
the raw inputs. The evaluator derives metrics, checks, deltas, regressions and
conclusion, and observability independently derives them again. A candidate
must show at least one measurable improvement and no regression in any
dimension.

## Contract Checks

`run_workflow_variant_eval` requires:

- a current immutable side-registry containing the baseline and candidate;
- matching workflow, route, baseline ref and active-registry fingerprint;
- a distinct `candidate_inactive` definition with no runtime authority;
- recurring-pattern and persisted review evidence on the candidate;
- unique bounded case/scenario IDs and explicit expected candidate elements;
- complete definition snapshots whose hashes match the registered versions;
- the same declared contract-check dimensions in both arms;
- distinct outcome refs and observations under the exact same control;
- offline-only cases with human review still required.

Each case validates the required candidate steps, checkpoints, decision points
and success criteria against the versioned definition before comparing metrics.
Drift in input, clock, seed, policy, memory, definition, checkpoint, result or
authority fails closed.

## Persistence

The `evolution-lab` registers a canonical case pack, atomically claims a
`run_id` bound to the input/control and version hashes, and appends the
validated run. SQLite tables are append-only and fingerprinted; identical
retry is idempotent, while divergent collision or tampering is rejected on
read and write. Pack, claim and run never mutate the active workflow registry.

## Interpretation

- `candidate_improved_without_regression`: every case passed, at least one
  metric improved per case and none regressed.
- `candidate_regression_detected`: one or more metric dimensions degraded.
- `insufficient_or_invalid_evidence`: identity, contract, scope, metric or
  evidence checks failed.
- `candidate_ready_for_human_gate_review`: evidence may enter the next human
  gate; it is not release approval.
- `manual_gate_only`: `promotion_authorized` remains false.

`MB-184` consumes this result as one input to the promotion and rollback gate.
`MB-207` closes the manual lifecycle bridge: the eval, candidate-specific human
review, release checklist, promotion gate, tests, rollback plan and a separate
human authorization now form one immutable bundle before canonical Memory can
record an activation. A green result alone never changes the active registry;
see `docs/operations/workflow-lifecycle.md`.
