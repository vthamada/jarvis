# Longitudinal Learning Metrics

Status: active baseline from `MB-188`.

## Purpose

The longitudinal learning report compares versioned learning evidence over
time. It answers whether reviewed memory, skill candidates and workflow
variants are associated with better mission outcomes without turning a score
into promotion authority.

The measured cycle is:

`version target -> runtime/eval observations -> baseline comparison -> human review`

## Evidence Sources

- reviewed memory: runtime missions that cite a reviewed guidance version;
- reviewed memory baseline: missions in the same workflow without reviewed
  guidance influence;
- skill candidates: sandbox eval evidence only while the candidate is inactive;
- workflow candidates: registered version and baseline identity; runtime claims
  remain invalid while the candidate is inactive;
- operator feedback: helpful, not helpful and correction signals correlated by
  mission;
- regression and rollback: audit anomalies, missing events, corrective feedback
  and reviewed rollback state.

Offline evals are useful evidence but are not longitudinal runtime evidence.
Inactive versions cannot claim production impact.

## Console

Build the report from the default canonical stores:

```powershell
python -m apps.jarvis_console learning-report
```

Use explicit stores and a larger observation threshold:

```powershell
python -m apps.jarvis_console learning-report --observability-db .jarvis_runtime/observability.db --memory-db .jarvis_runtime/memory.db --evolution-db .jarvis_runtime/evolution.db --minimum-observations 5
```

Persist `latest.json` and immutable timestamped evidence:

```powershell
python tools/longitudinal_learning_report.py --output-dir .jarvis_runtime/learning/longitudinal
```

## Interpretation

- `sustained_gain`: enough candidate and baseline observations, higher success,
  no higher rework and at least half of explicit feedback is helpful;
- `stable_or_mixed`: sufficient evidence without a clear gain or regression;
- `insufficient_evidence`: the version has fewer than the required observations;
- `insufficient_baseline_evidence`: the candidate has evidence but its baseline
  does not;
- `regression_detected`: success fell or rework increased;
- `regression_or_rollback_observed`: explicit regression or rollback evidence;
- `blocked`: malformed, unauthorized or causally invalid evidence was found.

Historical baseline regressions remain visible even if a newer version shows a
comparative gain. The report is evidence for human review, not a release verdict.

## Safety Invariants

- report and per-version metrics are read-only;
- `promotion_authorized=false` and `automatic_promotion_allowed=false`;
- `core_mutation_allowed=false`;
- runtime evidence for inactive targets fails closed;
- duplicate targets, duplicate observations and observations without a target
  are surfaced as regressions;
- rollback is counted once from lifecycle state, not once per later mission;
- no registry, memory record, proposal or active workflow is changed by report
  generation.

