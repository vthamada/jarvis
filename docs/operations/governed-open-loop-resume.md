# Governed Open-Loop Resume

Status: active baseline from `MB-197`.

## Purpose

The open-loop resume workflow lets an operator continue one unfinished mission
across sessions without authorizing a scheduler or autonomous execution. The
operator first reads the eligible loops, selects an exact canonical reference
and then asks the Core to resume that loop.

The governed flow is:

```text
list -> select -> revalidate -> plan -> persist -> synthesize
```

## Usage

```powershell
python -m apps.jarvis_console open-loops --mission-id <mission-id>
python -m apps.jarvis_console resume-loop --mission-id <mission-id> --open-loop-ref <open-loop-ref>
```

`open-loops` supports text and JSON output. `resume-loop` is a mutating command
and intentionally supports text output only.

## Eligibility

The read-only registry derives eligibility from canonical mission state:

- the mission and objective are active;
- the loop status is `open`;
- mission freshness is `fresh` or `aging`;
- no surface identity conflict is present;
- when structured work items exist, at least one is active and ready;
- the selected reference belongs to the mission.

Freshness follows the daily workspace policy: up to 24 hours is `fresh`, over
24 and up to 72 hours is `aging`, and over 72 hours is `stale`. Invalid or
future-skewed timestamps are `unknown`. `stale` and `unknown` fail closed.

## Governed Write

`resume-loop` re-reads canonical state, runs governance and records:

- selected loop and timestamp;
- canonical evidence and checkpoint references;
- selected executable work item, when available;
- bounded next-action reference and summary;
- loop status `resumed`.

The memory write requires the same mission `updated_at` that governance
validated. A concurrent state change contains the resume instead of overwriting
newer state. Repeating a completed resume is blocked.

## Output

The operator receives the governance decision, resume status, loop summary,
selected work item, next action, evidence and final Core synthesis. Events
`governance_checked`, `open_loop_resumed`, `mission_updated` and
`response_synthesized` make an allowed resume auditable.

## Safety Boundaries

- selection is explicit and bounded;
- reads do not mutate mission state;
- writes occur only through Core and canonical memory;
- no tool or work item is executed by resume;
- no background task or schedule is created;
- `autonomous_resume_allowed=False`;
- `autonomous_scheduling_allowed=False`;
- `autonomous_execution_allowed=False`;
- conflicts, stale state, missing evidence and state races fail closed.

After resume, the operator must inspect the synthesized next action and use an
explicit governed command to perform any subsequent work.
