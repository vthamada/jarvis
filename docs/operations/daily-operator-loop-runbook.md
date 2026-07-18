# Daily Operator Loop Runbook

Status: active baseline from `MB-200`.

## Purpose

This runbook is the end-to-end operating path for the current text console. It
connects the existing governed commands without creating a second workflow
authority. Command metadata remains canonical in the CLI registry, mission data
remains canonical in memory, and every mutation still crosses the Core.

The bounded loop is:

```text
preflight -> inspect -> select -> act -> record -> reflect -> review -> measure
```

## 1. Preflight

Run the read-only doctor before changing mission state:

```powershell
python -m apps.jarvis_console doctor
```

Stop when a required check is `failed`. A `warning` must be understood before
continuing; it is not an implicit authorization to bypass governance.

## 2. Inspect The Daily Workspace

Read the bounded multi-mission snapshot:

```powershell
python -m apps.jarvis_console daily-workspace
```

Use the reported `next_operator_decision` to select a mission. The workspace is
read-only: it does not infer a hidden priority, resume work or schedule a task.

For the selected mission, inspect its consolidated cockpit and current work:

```powershell
python -m apps.jarvis_console operator-dashboard --mission-id <mission-id>
python -m apps.jarvis_console work-items --mission-id <mission-id>
python -m apps.jarvis_console artifacts --mission-id <mission-id>
```

## 3. Start Or Continue A Mission

Start a governed mission and produce the first experience/reflection cycle:

```powershell
python -m apps.jarvis_console mission-workflow "<operator intent>" --mission-id <mission-id>
```

For a mission already in progress, list eligible loops before selecting one:

```powershell
python -m apps.jarvis_console open-loops --mission-id <mission-id>
python -m apps.jarvis_console resume-loop --mission-id <mission-id> --open-loop-ref <open-loop-ref>
```

Resume only revalidates and records one bounded next action. It does not execute
a tool, dispatch a work item or create a background schedule.

## 4. Manage Governed Work And Artifacts

Use explicit mutation commands for the next operator-approved transition:

```powershell
python -m apps.jarvis_console work-item --mission-id <mission-id> --action <action> --work-item-ref <work-item-ref>
python -m apps.jarvis_console artifact --mission-id <mission-id> --action <action> --artifact-ref <artifact-ref>
```

Re-read the mission after every material transition:

```powershell
python -m apps.jarvis_console progress-report --mission-id <mission-id>
python -m apps.jarvis_console mission-cycle --mission-id <mission-id>
```

Dependencies, blockers, ownership, versions and lineage come from canonical
state. Do not edit stores directly to repair an invalid transition.

## 5. Record Operator Feedback

When the mission result is observable, record explicit feedback:

```powershell
python -m apps.jarvis_console mission-feedback --mission-id <mission-id> --assessment <assessment> --comment "<bounded feedback>"
```

Feedback can create a sandbox-only learning candidate. It cannot promote a
change or mutate the Core by itself.

## 6. Inspect Reflection And Human Review

Inspect the generated experience, bounded reflection and review queue:

```powershell
python -m apps.jarvis_console experience-reflections --mission-id <mission-id>
python -m apps.jarvis_console evolution-review-queue
```

Apply a review decision only with the required evidence, tests and rollback
reference:

```powershell
python -m apps.jarvis_console evolution-review --proposal-id <proposal-id> --action <action> --evidence-ref <evidence-ref> --proposed-test <test-ref> --rollback-plan-ref <rollback-ref>
```

An approved or sandboxed proposal remains bounded by the separate promotion and
release gates. Review is not automatic activation.

## 7. Measure Outcomes And Readiness

Read observed outcomes without treating missing evidence as a gain:

```powershell
python -m apps.jarvis_console operator-outcomes
```

Run repository readiness explicitly when closing an implementation cut:

```powershell
python tools/readiness_dashboard.py --run-gate standard
```

Interpret `queue_exhausted` as a valid planning state. It requires explicit
reprioritization and is not a reason to fabricate a new ready item.

## 8. End-Of-Session Checklist

- the selected mission and objective are explicit;
- the next action, blocker or human decision is visible;
- work-item and artifact state matches the observed result;
- experience and reflection exist when the mission produced relevant evidence;
- evolution proposals remain in human review or a bounded sandbox;
- missing outcome evidence is recorded as a limitation;
- no direct store edit, autonomous resume, schedule or promotion occurred.

## Failure Paths

- If `doctor` fails, repair the local prerequisite before operating.
- If mission state is stale or has an identity conflict, do not resume it.
- If dependencies or artifact lineage conflict, use an explicit governed
  correction rather than bypassing canonical state.
- If evidence is insufficient, keep the proposal in review and collect more
  observations.
- If readiness reports drift or a failed gate, stop the closure and investigate.

## Current Boundaries

This baseline does not authorize voice/realtime, rich UI, public API, browser or
computer use, autonomous scheduling, broad integrations, self-modification,
model-weight changes or autonomous promotion. Those capabilities remain
deferred until an explicit phase decision and their own governed slices.
