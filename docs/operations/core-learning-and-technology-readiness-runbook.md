# Core Learning And Technology Readiness Runbook

Status: active baseline from `MB-210`.

## Purpose

Use this runbook to close the `MB-202` through `MB-210` learning-and-technology
queue without converting evidence into execution or release authority. The
operator verifies the evidence matrix, runs the focused closure test, refreshes
document and engineering evidence, evaluates the read-only readiness dashboard
and stops with an exhausted queue.

The companion closure record is
`docs/implementation/core-learning-and-technology-readiness-closure-mb210.md`.

## Non-negotiable boundary

This workflow is read-only except for the ordinary local test/gate artifacts
already produced by repository tooling. It must not:

- create or select a new `ready` backlog item;
- invoke an action adapter, dispatch a tool or activate runtime behavior;
- install, fetch, ingest or execute candidate technology;
- promote a workflow, memory item, playbook, experiment or capability;
- mutate Core policy, project priority or deferred scope;
- expose `SFC-005` or any public API.

The closing value of every authority field is `false`, including
`autonomous_release_allowed`, `execution_authorized`,
`execution_allowed`, `tool_dispatch_allowed`, `runtime_activation_allowed`,
`automatic_activation_allowed`, `release_authorized`, `promotion_authorized`,
`automatic_promotion_allowed`, `core_mutation_allowed`,
`priority_mutation_allowed`, `adapter_activation_allowed` and
`public_api_activation_allowed`.

## 1. Verify the evidence matrix

Read the matrix in the companion closure record and resolve each row back to
its cited source. The required sequence is exact:

```text
MB-202 workflow policy
  -> MB-203 semantic-memory causality
  -> MB-204 reviewed procedural playbooks
  -> MB-205 decision/outcome attribution
  -> MB-206 paired workflow evaluation
  -> MB-207 manual lifecycle and rollback
  -> MB-208 technology-radar intake
  -> MB-209 inert technology experiment packs
  -> MB-210 readiness closure
```

Stop if a contract, service, tool, operator document or focused test cited by a
row is absent, stale or contradicts its closure invariant. Record the gap; do
not infer evidence from a neighboring slice.

## 2. Run the focused closure contract

```powershell
python -m pytest tests/unit/test_core_learning_and_technology_readiness_closure.py -q
```

The test validates the complete `MB-202` through `MB-209` evidence matrix, this
runbook, the Governed Action Foundation decision and a synthetic synchronized
repository snapshot. It also proves that unsafe longitudinal evidence blocks
the report while `autonomous_release_allowed` remains false.

Stop on any failure. A documentary assertion failure is a closure failure, not
an invitation to weaken the expected contract.

## 3. Verify document guardrails

```powershell
python tools/verify_document_guardrails.py --format json
```

Expected result:

```text
decision=document_guardrails_ok
```

When JSON output is used, inspect the `decision` field and every document
record. Stop if the decision is not `document_guardrails_ok`. Restore the
canonical identity and required history of the affected document before
continuing; never replace a reserved project document with a short status note.

## 4. Refresh the standard gate and readiness snapshot

```powershell
python tools/readiness_dashboard.py --run-gate standard --format json --no-save
```

This command runs the standard engineering gate and then creates a read-only
repository readiness report. The closure shape is:

```text
status=ready_with_known_gaps|ready
backlog_status=queue_exhausted
next_ready_item=null
status_drift=[]
blockers=[]
document_status=healthy
gate_status=passed
test_status=passed
read_only=true
autonomous_release_allowed=false
```

`ready_with_known_gaps` is acceptable because the known candidate gaps and
deferred capabilities remain visible. It does not mean an action, release or
new backlog item is ready.

## 5. Apply fail-closed triage

Stop closure and preserve the evidence when any of these conditions appears:

| Signal | Required response |
| --- | --- |
| `status_drift` is non-empty | Synchronize the reserved status documents through the normal project update; rerun all checks. |
| `backlog_status` is not `queue_exhausted` | Reconcile the executable queue. Do not silently complete or fabricate an item. |
| `next_ready_item` is not `null` | Treat the closure as invalid until the queue state is intentionally reconciled. |
| `blockers` is non-empty | Resolve the named blocker and rerun the focused test, documents check and standard gate. |
| Gate or test is not `passed` | Keep `MB-210` open; diagnose the failing evidence. |
| Document status is not `healthy` | Restore the canonical document contract before closure. |
| Any authority value is `true` | Treat the evidence as unsafe, reject it and investigate the producing boundary. |
| A deferred capability appears current | Restore the phase boundary; no capability is promoted by queue exhaustion. |

Do not edit generated evidence to make a failed signal look green.

## 6. Record the phase boundary

After all checks pass, the current queue ends with `MB-210` completed and no
`ready` item. Record only this sequencing decision for the next phase:

```text
Governed Action Foundation
  1. GOV-007 autonomy enforcement
  2. GOV-005 per-adapter permission scopes and confirmations
  3. ACT-005 safe local-file adapter with allowlist and rollback
  4. only then consider SFC-005 / public API
```

This runbook does not open that phase. A separate reprioritization must define
the next numbered queue, acceptance evidence, gate and rollback, synchronize the
reserved project documents and select exactly one `ready` item under WIP=1.

## 7. Preserve deferred scope

Voice/realtime, rich UI/web UI/mobile UI, browser automation, computer use,
autonomous scheduler, external integrations, `SO-001`, `TA-004`, `TA-006`, the
`DV` horizon and the `RH` horizon remain deferred. `SFC-005` remains after the
three Governed Action Foundation slices.

Queue exhaustion does not change those decisions.

## Closure checklist

- [ ] All eight evidence rows, `MB-202` through `MB-209`, resolve to their cited
  implementation and focused tests.
- [ ] The focused `MB-210` closure test passes.
- [ ] Document guardrails report `document_guardrails_ok`.
- [ ] The standard engineering gate and test evidence pass.
- [ ] The readiness dashboard reports `queue_exhausted`, no next item, zero
  drift and no blockers.
- [ ] Every authority field remains false.
- [ ] Known limitations and deferred capabilities remain explicit.
- [ ] No `ready` item is created; the next queue waits for separate
  reprioritization.
