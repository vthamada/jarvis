# Governed Work Item Queue

Status: active baseline from `MB-195`.

## Purpose

The governed work-item queue makes explicit work dependencies, priority and
blocking state durable across sessions. It extends the existing Core-mediated
work-item lifecycle; it is not a parallel task manager or an autonomous
scheduler.

Canonical state is stored in `MissionStateContract.work_items`. The legacy
`work_item_refs` and `active_work_items` fields remain compatibility projections
for existing runtime consumers. Only `work-item://` references or items with an
auditable work-item transition are lifted from legacy state.

## Create And Inspect

Create an independent item with explicit priority:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action create --work-item-ref work-item://mission-demo/foundation --priority p1
```

Create a dependent item:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action create --work-item-ref work-item://mission-demo/release --depends-on work-item://mission-demo/foundation --priority p0
```

Inspect the governed read-only order:

```powershell
python -m apps.jarvis_console work-items --mission-id mission-demo
```

The output distinguishes:

- `ordered_work_item_refs`: deterministic dependency/priority presentation;
- `executable_work_item_refs`: active items whose dependencies are complete;
- `blocked_work_item_refs`: paused, explicitly blocked or dependency-blocked
  items;
- `blocking_state`: `ready`, `dependency_blocked`, `blocked`, `paused` or a
  mission-level containment state;
- `autonomous_execution_allowed=False`: the queue never starts an item.

Priority is bounded to `p0`, `p1`, `p2` and `p3`, with `p0` highest. A
dependency always appears before its dependent even when the dependent has
higher priority. Equal-priority items use their stable reference order.

## Update Dependencies Or Priority

Replace the dependency set and priority through the explicit `update`
transition:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action update --work-item-ref work-item://mission-demo/release --depends-on work-item://mission-demo/foundation --priority p1
```

Clear all dependencies explicitly:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action update --work-item-ref work-item://mission-demo/release --clear-dependencies
```

Dependencies must already belong to the same canonical mission. Duplicate,
self, unknown and cyclic dependencies fail closed without changing memory.
Priority/dependency changes are accepted only by `create` or `update`.

## Block And Resume

An explicit block requires at least one bounded cause:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action block --work-item-ref work-item://mission-demo/release --blocker-ref blocker://mission-demo/operator-approval
```

Resume clears explicit blocker refs only when every dependency is complete:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-demo --action resume --work-item-ref work-item://mission-demo/release
```

Completing a dependency refreshes the dependent item's blocking state in the
same governed canonical write. It does not resume, execute or schedule the
dependent item.

## Safety Boundaries

- every mutation enters through orchestrator and governance;
- SQLite and PostgreSQL use additive `work_items` JSON storage with safe empty
  defaults for existing databases;
- invalid transition, reference, priority, graph or blocker state fails closed;
- every successful transition records a reversible checkpoint and observable
  event;
- queue composition is read-only and deterministic;
- no scheduler, background worker, tool call or automatic resume is introduced;
- artifacts remain separate; version lineage is sequenced for `MB-196`.
