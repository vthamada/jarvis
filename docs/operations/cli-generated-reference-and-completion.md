# CLI Generated Reference And Completion

Status: active baseline from `MB-199`.

## Purpose

The typed command registry defines command identity, category, execution mode,
output mode and JSON support. The validated `argparse` declarations define the
arguments. `apps/jarvis_console/reference.py` combines both without duplicating
argument declarations and generates deterministic operator assets.

Generated assets never execute a command, construct the Core, write canonical
memory or grant authority.

## Command Reference

The versioned reference is:

- `docs/operations/jarvis-console-command-reference.md`.

It can also be printed without constructing the Core:

```powershell
python -m apps.jarvis_console command-reference
python -m apps.jarvis_console command-reference --format json
```

The document excludes machine-specific defaults, runtime paths, ids, secrets
and generation timestamps.

## Shell Completion

The console emits completion directly from the same validated model:

```powershell
python -m apps.jarvis_console completion --shell powershell
python -m apps.jarvis_console completion --shell bash
python -m apps.jarvis_console completion --shell zsh
```

Versioned scripts are stored in `tools/completions/`:

- `jarvis-console.ps1`;
- `jarvis-console.bash`;
- `_jarvis-console`.

Example local activation after a `jarvis-console` launcher is available:

```powershell
. .\tools\completions\jarvis-console.ps1
```

```bash
source tools/completions/jarvis-console.bash
```

For Zsh, source `tools/completions/_jarvis-console` or place it in a directory
from `fpath` and run `compinit` according to the local shell policy.

Completion is suggestion-only. It does not validate permission, execute a
handler or bypass governance. Tokens outside the allowed shell grammar make
generation fail closed.

## Regeneration

After changing registry or parser metadata, run:

```powershell
python tools/generate_cli_assets.py
```

`tests/unit/test_cli_generated_assets.py` compares every generated asset with
the committed file byte for byte. Any unregenerated change fails the test.

## Golden Outputs

Critical deterministic outputs are versioned under
`apps/jarvis_console/tests/golden/`:

- daily workspace text;
- operator outcomes text;
- JSON runtime success envelope.

Golden fixtures use fixed ids and timestamps. Runtime-generated identifiers,
current timestamps, absolute paths and secrets must not enter them.

## Maintenance Rule

1. Change parser and registry metadata together.
2. Regenerate assets.
3. Review the reference and all three completion scripts.
4. Update golden files only for an intentional output-contract change.
5. Run focused tests, document guardrails and the standard engineering gate.
