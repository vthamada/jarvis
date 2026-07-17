# Workflow Profile Version Registry

## Purpose

`MB-181` introduces a versioned side registry for workflow definitions without
changing the sovereign active registry in
`knowledge/curated/domain_registry.json`.

The active registry remains the only runtime authority. The version registry
exists for comparison, candidate review and later sandbox evaluation.

## Contracts

`WorkflowProfileVersionContract` records:

- workflow identity, numeric semver and route;
- lifecycle and runtime-binding status;
- definition hash;
- ordered steps, checkpoints and decision points;
- success criteria;
- evidence, proposed tests and rollback;
- active-registry ref and fingerprint;
- baseline ref, change summary, risk and blockers for candidates;
- explicit human-review, sandbox and sovereignty controls.

`WorkflowProfileVersionRegistryContract` records the immutable snapshot ID,
active-registry fingerprint, baseline/candidate counts, versions, evidence and
aggregate safety controls.

## Baseline snapshots

`build_active_workflow_version_registry` selects only routes whose maturity is
`active_registry` or `active_specialist` and which have a complete
`workflow_profile`. It derives one deterministic baseline version per active
workflow.

Each baseline contains the live steps, checkpoints and decision points plus
success criteria from expected deliverables and sovereign runtime guidance.
The definition and whole active workflow set receive stable SHA-256 hashes.

A baseline has:

- `lifecycle_status=baseline_snapshot`;
- `runtime_binding_status=observed_active_baseline`;
- no authority to write or activate runtime state.

The status describes what was observed. It does not grant authority.

## Candidate registration

`register_workflow_candidate_version` returns a new side-registry object. It
never writes to `RUNTIME_ROUTE_REGISTRY`, guidance or the curated JSON.

A candidate is accepted only when it:

- uses numeric semver greater than its baseline;
- matches one route, workflow, baseline ref and active-registry fingerprint;
- has a definition hash derived from complete bounded content;
- differs from the baseline definition;
- carries evidence, tests, change summary and rollback;
- has low or moderate risk and no blockers;
- remains `candidate_inactive`, `needs_review` and sandbox-required;
- claims no registry write, runtime activation, automatic promotion or Core
  mutation authority.

Identical retries are idempotent. Candidate ID mutation and logical
`workflow_profile + version` collisions are rejected.

## Lifecycle boundary

The shared lifecycle vocabulary anticipates review, sandbox, eval, release and
rollback states so later contracts can use stable names. `MB-181` produces
only:

- `baseline_snapshot`;
- `candidate_inactive`.

`MB-182` may build a candidate from reviewed recurring evidence. `MB-183` may
evaluate it offline. `MB-184` may connect evidence to human release and
rollback gates. None of those stages may mutate the active registry by direct
assignment.

## Evolution lab role

`EvolutionLabService` exposes snapshot construction and inactive candidate
registration as thin delegates. The lab does not persist an active workflow,
bind a candidate to routing or promote a version. It remains subordinate to
the sovereign Core and future human release gates.
