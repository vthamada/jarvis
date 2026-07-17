# CLI Runtime Output Contract

Status: active baseline from `MB-192`.

## Purpose

The console runtime separates command dispatch from output, errors and process
exit semantics. It preserves existing text behavior while adding bounded,
machine-readable JSON to declared read/report commands.

The runtime does not change Core decisions, governance, memory or synthesis.

## Output Selection

`--format text|json` works before or after the subcommand:

```powershell
python -m apps.jarvis_console --format json readiness-dashboard
python -m apps.jarvis_console readiness-dashboard --format json
```

Text remains the default. JSON support is declared per command in the typed
registry. The baseline supports objectives, goal strategy, work-item and
artifact lists, bounded memory/evolution queues, mission/readiness/learning and
progress reports, plus the read-only doctor and daily workspace.

State-changing commands intentionally reject JSON in this baseline. Rejection
happens before constructing the Core or invoking the handler.

## Success Envelope

```json
{
  "schema_version": "jarvis-console/v1",
  "command_id": "readiness-dashboard",
  "status": "success",
  "outputs": ["regression_readiness=read_only\n..."],
  "warnings": [],
  "redacted": false
}
```

Success is written only to stdout. The `outputs` list contains the current
stable human rendering; domain-specific JSON payloads can evolve later without
changing sovereign service contracts.

Read-only diagnostics may return `degraded` with exit `0`, or `failed` with a
nonzero exit code, in the same result envelope. Warnings and outputs are both
redacted before emission.

## Error Envelope

Runtime, command and `argparse` usage failures are written only to stderr. JSON
errors use:

```json
{
  "schema_version": "jarvis-console/v1",
  "command_id": "objective",
  "status": "error",
  "error_code": "invalid_cli_usage",
  "message": "the following arguments are required: --mission-id, --action",
  "redacted": false
}
```

Text errors use `error[code]: message` on stderr.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | success |
| `1` | runtime error or failed read-only diagnostic |
| `2` | invalid usage/input or unsupported output mode |
| `3` | explicit governance-blocked console error |

The runtime catches command exceptions at the process boundary. Direct service
and handler tests still receive their native exceptions.

## Redaction

Before output, the runtime redacts:

- API keys, access tokens, generic tokens, passwords and secrets in assignments;
- bearer tokens;
- credentials embedded in URLs;
- configured workspace/home paths and their descendants;
- Windows absolute paths and sensitive Unix home/temp/config paths.

Redaction applies to success and error output. JSON reports whether any value
was changed through `redacted=true`.

## Boundaries

- JSON never authorizes an action unavailable in text mode;
- unsupported JSON never invokes a state-changing handler;
- no traceback or exception type is emitted by default;
- the runtime does not persist output or create a parallel event store;
- shell completion and registry-derived golden/reference output remain in
  `MB-199`.
