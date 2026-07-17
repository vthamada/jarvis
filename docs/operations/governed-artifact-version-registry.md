# Governed Artifact Version Registry

## Purpose

The artifact registry preserves living outputs as canonical, auditable versions
owned by one mission and sourced from a governed work item. It records lineage;
it does not read, edit, move or delete the referenced external file.

## Canonical state

Each explicitly governed version in `MissionStateContract.artifact_states`
records:

- `artifact_ref` and positive `artifact_version`;
- `owner_mission_id`, `objective_ref` and source `work_item_ref`;
- `lineage_root_ref` and `supersedes_artifact_ref`;
- `replacement_artifact_ref` on the superseded version;
- `rollback_plan_ref`, lifecycle status, timestamps and checkpoint refs.

Version identity, owner, source work item and lineage are immutable. Lifecycle
status and audit checkpoints may change through the governed transitions.
Legacy `artifact_refs` remain visible as compatibility projections but are not
silently promoted into the structured version registry.

## State machine

- `register`: creates version 1 or another explicitly positive initial version;
- `replace`: only from `active`, creates exactly the next version and marks the
  previous version `superseded`;
- `archive`: moves an `active` version to `archived`;
- `activate`: reactivates an `archived` version;
- `rollback`: reactivates a `superseded` version and marks its active successor
  `rolled_back`.

`replace` requires a distinct new artifact ref, the next sequential version and
a bounded rollback ref. `rollback` requires the recorded successor and an
explicit rollback ref. Invalid states, duplicate refs, unknown source work
items and version jumps fail closed before canonical memory is written.

## Console use

Create the source work item first:

```powershell
python -m apps.jarvis_console work-item --mission-id mission-1 --action create --work-item-ref work-item://mission-1/plan
```

Register the first version:

```powershell
python -m apps.jarvis_console artifact --mission-id mission-1 --action register --artifact-ref artifact://mission-1/plan/v1 --artifact-version 1 --work-item-ref work-item://mission-1/plan --rollback-plan-ref rollback://mission-1/plan/v1
```

Create a replacement version:

```powershell
python -m apps.jarvis_console artifact --mission-id mission-1 --action replace --artifact-ref artifact://mission-1/plan/v1 --artifact-version 2 --replacement-artifact-ref artifact://mission-1/plan/v2 --rollback-plan-ref rollback://mission-1/plan/v1
```

Inspect or roll back:

```powershell
python -m apps.jarvis_console artifacts --mission-id mission-1
python -m apps.jarvis_console artifact --mission-id mission-1 --action rollback --artifact-ref artifact://mission-1/plan/v1 --rollback-plan-ref rollback://mission-1/plan/v1
```

The `artifacts` output is a read-only registry ordered by lineage and version.
It explicitly reports `external_file_mutation_allowed=False`.

## Safety boundaries

- all lifecycle writes pass through orchestrator, governance and canonical
  memory;
- SQLite and PostgreSQL persist the same additive structured state;
- no transition writes the external artifact file;
- the registry does not schedule work or authorize tool execution;
- a rollback changes canonical lifecycle state only;
- external file adapters remain a separate, deferred capability.
