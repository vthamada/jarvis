# CLI Doctor And Read-Only Preflight

## Purpose

`jarvis-console doctor` diagnoses whether the local operator environment can
reach the JARVIS runtime boundaries without initializing, repairing or mutating
them. It complements `readiness-dashboard`: the dashboard evaluates repository
readiness evidence, while doctor inspects the current local runtime preflight.

## Usage

```powershell
python -m apps.jarvis_console doctor
python -m apps.jarvis_console doctor --format json
python -m apps.jarvis_console doctor --runtime-dir .jarvis_runtime
```

Optional paths can be selected with `--memory-db`, `--evolution-db` and
`--observability-db`. Relative paths are resolved from the current working
directory. Paths are never printed in the report.

## Checks

| Check | Behavior |
| --- | --- |
| Python runtime | Requires Python 3.11 or newer |
| Core imports | Imports the governed service boundaries without building Core |
| Runtime directory | Checks existing access or whether its parent can initialize it later |
| Canonical stores | Opens existing SQLite stores with `mode=ro` and runs a read-only query |
| Backlog state | Reuses the readiness status-sync policy for backlog, master map and active docs |
| Governance boundary | Verifies that the governance service boundary is available |
| Engineering gate | Verifies gate discoverability without executing it |

A missing runtime directory or store is an initialization warning and returns a
degraded report. A store that exists but is not a reachable SQLite database is
a failure. Import, governance, backlog or gate failures also fail the preflight.

## Status And Exit Semantics

| Doctor status | Exit code | Meaning |
| --- | --- | --- |
| `healthy` | `0` | All checks passed |
| `degraded` | `0` | Only initialization/optional warnings exist |
| `failed` | `1` | At least one present or required boundary failed |

In JSON mode, the `jarvis-console/v1` envelope uses `success`, `degraded` or
`failed`; warning check ids appear in `warnings`. Usage errors remain exit `2`
and governed command blocks remain exit `3` under the common runtime contract.

## Safety Invariants

- doctor never creates the runtime directory or a database;
- existing stores are opened through a read-only SQLite URI;
- doctor does not execute the engineering gate or repair a failed check;
- no check promotes evolution, writes memory or changes Core state;
- evidence refs are logical ids, not local paths or secrets;
- a failed report requires explicit operator remediation followed by a new run.

The implementation and tests are in
`apps/jarvis_console/commands/doctor.py` and
`apps/jarvis_console/tests/test_doctor.py`.
