# Workflow Lifecycle And Rollback

Status: active manual baseline from `MB-207`.

## Purpose

The workflow lifecycle promotes one evaluated workflow candidate into runtime
only after a persisted human review, controlled eval, release checklist,
promotion gate, completed tests, rollback plan and independent human
authorization are bound into one immutable release bundle. It never rewrites
the sovereign static route registry and grants no execution or tool-dispatch
authority.

## Activation

Use `jarvis-console workflow-transition --action activate_candidate` with the
exact proposal and eval-run identifiers, typed human/operator refs, evidence,
completed tests and completed external gates. The console:

1. rebuilds the release bundle from persisted Evolution Lab artifacts;
2. verifies the exact bundle independently;
3. asks Governance to authorize only an append-only memory record;
4. records the transition through canonical Memory with CAS lineage;
5. leaves the static registry unchanged.

Both native and LangGraph runtimes read only the fully verified active tail.
Planning consumes the complete promoted steps, checkpoints, decision points
and success criteria. Synthesis and runtime events preserve active version,
definition hash, human authorization and every release-artifact reference and
fingerprint.

## Rollback

Rollback is never automatic. Use the same command with
`--action rollback_to_baseline` and at least one failure reference. A rollback
must point to the exact current transition and immutable release bundle, carry
a new human authorization and pass Governance again. The new append-only
revision restores the sovereign baseline definition; it does not edit the
candidate or registry.

## Inspection And Failure Behavior

`jarvis-console workflow-lifecycle --workflow-profile <profile> --route
<route>` shows the verified current binding and history. A missing binding uses
the versioned static baseline. Store failure, scope mismatch, lineage gap,
tampering or bundle-verification failure rejects the binding and falls back to
that baseline with explicit resolution reasons in runtime events and
`FlowAudit` drift/anomaly fields.

`FlowAudit` compares lifecycle provenance across planning, optional workflow
composition/governance, dispatch/completion and synthesis. Missing or divergent
version, hash, authorization, release artifact or a claim of registry write,
runtime execution, automatic promotion/rollback or Core mutation makes the
trace incomplete.

## Authority Boundary

- the transition is a read-only runtime definition binding;
- operation execution still requires the ordinary capability and Governance
  paths;
- the lifecycle never authorizes tool dispatch;
- promotion and rollback always require explicit human action;
- direct repository writes and unverified structural contracts are rejected;
- PostgreSQL integration tests require `DATABASE_URL`; SQLite and fake-PG
  parity remain part of the standard gate when it is absent.
