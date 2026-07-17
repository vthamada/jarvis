# Daily Operator Workspace

Status: active baseline from `MB-194`, extended by `MB-195`.

## Purpose

`jarvis-console daily-workspace` provides one read-only view of open canonical
missions across sessions. It shows active objectives, work items, artifacts,
checkpoints, pending evolution/memory reviews, freshness and the next operator
decision without reconstructing context manually.

This command complements rather than replaces `operator-dashboard`:

- `daily-workspace` selects and summarizes open work across missions;
- `operator-dashboard --mission-id ...` inspects one mission in depth.

## Usage

```powershell
python -m apps.jarvis_console daily-workspace
python -m apps.jarvis_console daily-workspace --format json
python -m apps.jarvis_console daily-workspace --limit 20
```

The default memory store is `.jarvis_runtime/console/memory.db`, matching the
CLI Core. `--memory-db` and `--evolution-db` accept explicit local stores for a
different governed environment. The limit is bounded between 1 and 200.

## Canonical Inputs

The workspace is derived at request time from:

- open `MissionStateContract` records in canonical memory;
- human evolution review items already persisted by `evolution-lab`;
- memory lifecycle candidates derived from canonical memory evidence.

Completed and canceled missions are excluded. No workspace table, cache or
parallel source of truth is created.

## Freshness

| Status | Age |
| --- | --- |
| `fresh` | up to 24 hours |
| `aging` | over 24 and up to 72 hours |
| `stale` | over 72 hours |
| `unknown` | invalid timestamp or relevant clock skew |

Freshness is evidence for operator attention, not authorization to close,
resume or mutate a mission.

## Decision Order

The first `next_operator_decision` follows a deterministic bounded order:

1. evolution review;
2. memory lifecycle review;
3. blocked or paused mission;
4. stale mission;
5. open checkpoint;
6. blocked work-item review;
7. explicit next action, first executable governed work-item selection or
   next-action definition.

Mission ordering remains `updated_at` descending. Inside each mission, `MB-195`
exposes `ordered_work_item_refs`, `executable_work_item_refs` and
`blocked_work_item_refs`. That order comes only from canonical dependencies and
explicit `p0..p3` priority; it is not an execution schedule.

## Safety Boundaries

- the command is standalone and does not construct the Core;
- list and composition paths do not write canonical state;
- outputs are redacted through `jarvis-console/v1` in text and JSON modes;
- `memory_write_mode=read_only` is fixed;
- `autonomous_resume_allowed=False` is fixed;
- `autonomous_scheduling_allowed=False` is fixed;
- a suggested decision is never executed by the report;
- cross-store or multi-user federation is outside this local baseline.

Use the explicit governed objective/work-item/review commands to apply a human
decision. Governed open-loop resume remains sequenced for `MB-197`.
