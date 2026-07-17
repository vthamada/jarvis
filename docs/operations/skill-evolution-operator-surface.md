# Skill Evolution Operator Surface

## Purpose

`MB-180` exposes the governed skill evolution chain to the human operator:

`recurring pattern -> inactive candidate -> proposal -> human review -> sandbox eval -> release review`

The surface is read-only. It does not mine, register, execute, activate,
promote or roll back a skill. It correlates records already held by canonical
memory and the evolution lab through the observability projection.

## Commands

Inspect the current bounded view:

```powershell
python -m apps.jarvis_console skill-evolution
```

Filter one logical skill and version:

```powershell
python -m apps.jarvis_console skill-evolution --skill-id skill://release-evidence --version 1.0.0
```

Filter an operational scope:

```powershell
python -m apps.jarvis_console skill-evolution --workflow-profile software_change_workflow --route software_development --domain software_engineering
```

Use explicit local stores when needed:

```powershell
python -m apps.jarvis_console skill-evolution --memory-db .jarvis_runtime/memory.db --evolution-db .jarvis_runtime/evolution.db
```

The bounded `--limit` defaults to `10` and cannot exceed `100`.

## What the view shows

The header reports:

- report and view status;
- recurring-pattern and candidate counts;
- eligible patterns without a registered candidate;
- aggregate blockers;
- explicit read-only, human-review and sovereignty flags.

Each candidate reports:

- skill identity, name and version;
- source pattern refs, recurrence threshold and confidence;
- workflow, route, domain and specialist scope;
- risk and allowed tools;
- registry, review, activation, proposal and sandbox statuses;
- evidence, proposed tests and rollback;
- blockers and the next operator action label.

`next_operator_action` is guidance, not an executable command. The inspection
does not perform that action.

## Status interpretation

| View status | Meaning |
| --- | --- |
| `empty` | No recurring pattern or candidate exists in the selected scope. |
| `pattern_review_required` | Recurring evidence exists without a registered candidate. |
| `operator_action_required` | At least one candidate awaits proposal, review or sandbox evidence. |
| `attention_required` | Candidate, pattern, review or sandbox blockers must be resolved. |
| `release_review_required` | Sandbox evidence passed, but release and promotion remain human decisions. |

A green sandbox result is `passed_pending_release_gate`; it is not activation
or promotion. The output must continue to show:

- `runtime_activation_allowed=False`;
- `promotion_authorized=False`;
- `automatic_promotion_allowed=False`;
- `core_mutation_allowed=False`.

## Data and trust boundary

The command reads:

- recurring evidence rebuilt from canonical experience/reflection memory;
- immutable inactive candidates from the memory registry;
- skill proposals, human review context and sandbox summaries from the
  evolution lab.

Correlation uses `skill_candidate_id` and source `pattern_id`. Persisted text
is sanitized before rendering. Missing source evidence remains visible as a
blocker rather than being inferred or silently accepted.

## Current limitation

This baseline has no skill runtime activation command and no final human
promotion command. That boundary is intentional. Future release work must use
the existing checklist and promotion gates and must not bypass the sovereign
Core.
