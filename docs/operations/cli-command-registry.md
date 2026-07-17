# CLI Command Registry

Status: active baseline from `MB-191`.

## Purpose

The typed command registry is the canonical inventory and dispatch boundary for
the JARVIS operator CLI. It removes command selection from a monolithic branch
chain while preserving every existing parser, handler, service boundary and
governance decision.

The registry is not a second router or a new brain. It only selects an existing
console handler after `argparse` has validated operator input.

## Command Metadata

Every command declares:

- `command_id`: stable kebab-case CLI identity;
- `help_text`: operator-facing parser help;
- `handler_name`: bound existing handler;
- `category`: mission, objective, work, artifact, memory, evolution or
  observability;
- `execution_mode`: `core` or `standalone`;
- `output_mode`: `single` or `chat`.

Parser command IDs and help text are validated against the registry during
parser construction. Missing, unknown, duplicate or stale declarations fail
closed.

## Execution Modes

`core` commands construct `JarvisConsole` and continue through the sovereign
orchestrator, governance, canonical memory and final synthesis.

`standalone` commands are existing bounded read/review/report handlers that
construct only their explicit canonical services. They do not construct the
full Core merely to render readiness, learning, memory or evolution state.

Changing a command to `standalone` never grants a governance bypass. A
state-changing standalone handler, such as a human review command, still calls
its existing governance and canonical persistence path.

## Output Modes

- `single`: print at most the first handler output, preserving current command
  behavior;
- `chat`: print all scripted `--message` outputs; interactive chat continues to
  manage its prompt/output loop inside the existing handler.

`MB-192` now provides structured JSON for declared read/report commands,
stderr discipline, redaction and stable exit codes. The registry remains the
authority for whether a command supports JSON.

`MB-194` adds `daily-workspace` as a standalone read/report command. It reads
canonical stores and composes a cross-session projection without constructing
Core or authorizing resume/scheduling.

## Adding A Command

1. Implement and test the handler through the appropriate governed service.
2. Add the parser and arguments.
3. Add one `CommandDefinition` with matching help and handler identity.
4. Select `core` unless the command is a bounded service/report surface with an
   explicit sovereign boundary.
5. Add registry and behavior tests.
6. Run the standard engineering gate.

Do not add TUI, voice, browser/computer use, external gateway or permission
bypass behavior through the registry.
