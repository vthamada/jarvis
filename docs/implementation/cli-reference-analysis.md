# CLI Reference Analysis For JARVIS

Status: research and implementation guidance.

Date: 2026-07-04.

Purpose: compare the current JARVIS console with CLI patterns from Hermes Agent,
opencode, OpenAI Codex, OpenClaw and Claude Code public documentation, then
define practical improvements for a robust governed JARVIS operator CLI.

This document does not open a new functional implementation, does not alter the
active micro backlog, and does not authorize broad UI, browser, computer use,
voice, realtime, scheduler or autonomous evolution work.

## Sources Reviewed

| Project | Source | Reference |
| --- | --- | --- |
| JARVIS | local repository | `apps/jarvis_console/cli.py` |
| Hermes Agent | local checkout | `C:\Users\vtham\OneDrive\Area de Trabalho\hermes-agent` at `99ff375f7` |
| opencode | shallow clone | `https://github.com/sst/opencode` at `7a8e7c8` |
| OpenAI Codex | shallow clone | `https://github.com/openai/codex` at `98d28aa` |
| OpenClaw | shallow clone | `https://github.com/openclaw/openclaw` at `706443c7` |
| Claude Code | public docs only | `https://code.claude.com/docs/en/overview`, `settings`, `security` |

The cloned repositories were kept under `.research/cli-reference-repos/` for
local inspection and must not be committed. `.research/` is ignored by git.

## Current JARVIS CLI Baseline

The current JARVIS console is useful and test-covered, but still a minimum
operator surface rather than a mature product CLI.

Implemented strengths:

- Uses `argparse` with explicit subcommands.
- Runs through the governed core via `JarvisConsole` and `OrchestratorService`.
- Exposes operational commands for `ask`, `chat`, objectives, work items,
  artifacts, technology candidates, experience/reflection, evolution review,
  mission cycle, operator dashboard and mission workflow.
- Has meaningful tests in `apps/jarvis_console/tests/test_console.py` and
  `apps/jarvis_console/tests/test_console_end_to_end.py`.
- Preserves the sovereign core by routing mission interactions through current
  contracts and services instead of bypassing governance.

Current limits:

- Parser construction, command execution and renderers all live in one large
  file: `apps/jarvis_console/cli.py`.
- `main()` dispatch is an if/else chain, which will become fragile as commands
  grow.
- There is no command registry or command metadata layer.
- There is no global output mode contract, such as `--format text|json`.
- There is no standardized CLI result envelope, error taxonomy or exit-code
  policy.
- There is no `doctor` command for install/config/runtime diagnostics.
- There is no explicit profile/config layering for operator runtime settings.
- There is no shell completion support.
- There is no consolidated permission/autonomy preview command.
- There is no split between human rendering and machine-readable output.
- The current cockpit is useful but still command-fragmented for daily use.

## Cross-Project Findings

### Hermes Agent

Relevant files:

- `hermes_cli/main.py`
- `hermes_cli/commands.py`
- `hermes_cli/doctor.py`
- `website/docs/reference/cli-commands.md`
- `tests/hermes_cli/*`

Useful patterns:

- Central slash-command registry with `CommandDef`, aliases, categories,
  subcommands, gateway-only and CLI-only flags.
- `doctor` command checks environment, packages, config files, provider auth and
  optional integrations.
- Profiles are pre-parsed before module imports so the runtime home is stable.
- CLI docs are treated as a first-class command reference.
- Tests cover argparse edge cases, especially parent/subparser flag propagation.
- Session browsing, profiles, logs, skills, plugins, tools and gateway commands
  are grouped into domain families.

Risks to avoid copying:

- The main CLI entrypoint is very large and carries a lot of operational weight.
- Broad gateway, messaging, voice, cron and external tool surfaces are outside
  the current JARVIS phase.
- YOLO-style permission bypass is not compatible with the JARVIS sovereign-core
  posture unless represented only as an explicitly blocked or high-risk state.

Applicable to JARVIS:

- Add a typed command registry before adding more commands.
- Add `doctor`.
- Add tests for global flag behavior before introducing global flags.
- Create operator-facing CLI reference docs generated from or aligned with the
  command registry.

### opencode

Relevant files:

- `packages/opencode/src/cli/cmd/*.ts`
- `packages/opencode/src/cli/effect-cmd.ts`
- `packages/opencode/src/cli/bootstrap.ts`
- `packages/opencode/src/cli/cmd/run.ts`
- `packages/opencode/src/cli/cmd/session.ts`

Useful patterns:

- Commands are modular files under `cli/cmd`.
- Command handlers are wrapped in a common effect/runtime command factory.
- Some commands can opt out of project-instance loading for faster diagnostics.
- `run` supports non-interactive mode, interactive mode, attach mode, session
  continuation, file attachment, model/agent selection and JSON event output.
- `session list` supports table and JSON formats.
- Runtime lifecycle disposal is enforced around command execution.

Risks to avoid copying:

- Rich interactive split-footer/TUI behavior should not be pulled before the
  text cockpit is stable.
- Remote attach/server operation is not the next JARVIS step.
- Broad plugin/provider ecosystems should remain governed technology absorption
  candidates, not core replacements.

Applicable to JARVIS:

- Introduce a command module boundary and command registry.
- Introduce `--format text|json` per read/report command first.
- Separate command execution from renderers and service wiring.
- Make lifecycle/runtime setup explicit instead of hidden in command branches.

### OpenAI Codex

Relevant files:

- `codex-rs/cli/src/main.rs`
- `codex-rs/cli/src/doctor.rs`
- `codex-rs/cli/src/lib.rs`
- `codex-rs/exec/src/lib.rs`
- `codex-rs/tui/src/**`

Useful patterns:

- Top-level CLI has explicit subcommands: `exec`, `review`, `login`, `logout`,
  `mcp`, `plugin`, `completion`, `doctor`, `sandbox`, `debug`, `resume`,
  `archive`, `delete`, `fork` and others.
- Global options are flattened/shared instead of redefined manually in every
  command.
- `exec` enforces strict stdout semantics: final output or JSONL on stdout;
  diagnostics go to stderr.
- `doctor` is intentionally read-mostly, redacted and machine-readable.
- Sandbox and approval concepts are first-class CLI surfaces.
- TUI has extensive snapshot tests for visible behavior.
- Shell completion is a normal command, not an afterthought.

Risks to avoid copying:

- Rewriting JARVIS CLI in Rust or adopting a full TUI is not justified now.
- Plugin marketplace and app-server concepts should not become core dependencies.
- Sandbox modes must map to JARVIS governance, not replace it.

Applicable to JARVIS:

- Add strict stdout/stderr and JSON output rules for automation-safe commands.
- Add `doctor --json` style diagnostics.
- Add `completion` after command registry exists.
- Add snapshot/golden tests for console output once renderers are split.
- Add an autonomy/permission status command that reports allowed, blocked and
  human-review states without granting new powers.

### OpenClaw

Relevant files:

- `openclaw.mjs`
- `src/index.ts`
- `src/cli/system-cli.ts`
- `src/cli/tui-cli.ts`
- `src/infra/cli-root-options.ts`
- `src/infra/approval-view-model.ts`
- `src/infra/command-analysis/*`
- `src/cli/*.test.ts`

Useful patterns:

- Package launcher validates runtime version before loading the application.
- Global error handlers format failures and restore terminal state.
- CLI modules register command families into a root `commander` program.
- Gateway/system commands use centralized runtime methods for `writeJson`,
  `log`, `error` and `exit`.
- Approval display is built through view-models separate from execution.
- Command risk analysis and approval rendering are explicit components.
- Extensive CLI tests cover startup, completions, approvals, command analysis,
  runtime boundaries and plugin behavior.

Risks to avoid copying:

- Gateway control plane, multichannel integrations and broad extension runtime
  are outside current JARVIS scope.
- OpenClaw's plugin breadth would dilute the current operator-learning focus if
  imported prematurely.

Applicable to JARVIS:

- Add a central CLI runtime abstraction for output and exits.
- Build approval/review/status view-models before rendering them.
- Add startup diagnostics and runtime preflight checks.
- Keep command families modular: mission, objective, work item, artifact,
  memory, evolution, observability, admin.

### Claude Code

Source limitation: no official open-source repository was used. The analysis is
based on public Claude Code documentation, not private or leaked code.

Useful documented patterns:

- CLI is one of multiple surfaces, but settings and context are shared across
  surfaces.
- Configuration uses scopes such as managed, command-line, local, project and
  user.
- Permission configuration supports allow and deny rules.
- Security posture emphasizes explicit approval for state-changing operations,
  sandboxing, trust verification, prompt-injection defenses, sensitive-file
  exclusion and auditability.
- CLI supports piping and scripted use, so machine-readable behavior matters.

Risks to avoid copying:

- Browser, desktop, mobile, recurring tasks and broad remote control are outside
  the current JARVIS phase.
- Permission bypass modes are dangerous for JARVIS and should remain blocked or
  explicitly governed.
- Any behavior inferred from non-official leaked code must not be used as a
  design source.

Applicable to JARVIS:

- Define settings precedence early, before multiple surfaces exist.
- Make permission/autonomy state visible to the operator.
- Exclude sensitive files and secrets from console diagnostics.
- Keep CLI scriptability as a first-class constraint.

## Recommended JARVIS CLI Principles

1. The CLI is an operator cockpit, not a second brain.
2. Every state-changing command must route through governance and canonical
   memory.
3. Every command should have text output and, where useful, JSON output.
4. Human-readable rendering and machine-readable data must be separate.
5. CLI errors should be typed, redacted and mapped to stable exit codes.
6. Diagnostics should be read-mostly by default.
7. Global flags must be tested before broad use.
8. Command metadata must become the source for help, docs and completion.
9. Permission/autonomy state must be visible before any broader automation.
10. No CLI feature should promote evolution proposals or bypass human review.

## Recommended CLI Architecture Target

Proposed structure:

```text
apps/jarvis_console/
  cli.py                    # thin entrypoint, keeps backward compatibility
  runtime.py                # output, json, stderr, exit codes, redaction
  registry.py               # command metadata and registration
  context.py                # service/runtime construction
  commands/
    ask.py
    chat.py
    mission.py
    objectives.py
    work_items.py
    artifacts.py
    memory.py
    evolution.py
    observability.py
    doctor.py
    completion.py
  renderers/
    response.py
    mission.py
    objective.py
    work_item.py
    artifact.py
    evolution.py
  view_models/
    operator_dashboard.py
    evolution_review.py
    autonomy_status.py
```

Migration rule: do not rewrite everything at once. Introduce the registry and
runtime around the existing commands first, then move command families in small
MBs.

## Gap Analysis Against Current JARVIS

| Capability | Current state | Recommended target |
| --- | --- | --- |
| Command registry | missing | typed registry with metadata, handlers and docs hooks |
| Global output mode | missing | `--format text|json` for read/report commands |
| Exit-code policy | implicit | stable success, usage, governance-blocked, runtime-error codes |
| Error rendering | ad hoc | redacted typed errors with stderr discipline |
| Doctor command | missing | read-only diagnostics for runtime, config, services and gates |
| Config profiles | missing | minimal local operator profile after command registry |
| Shell completion | missing | generated from registry |
| Snapshot tests | partial renderer tests | golden tests for command output and JSON envelopes |
| Permission/autonomy view | fragmented | explicit read-only autonomy/governance status command |
| CLI docs | operational docs exist | command reference tied to registry |
| TUI | missing | defer until text cockpit is stable |
| External integrations | intentionally constrained | defer unless governed by technology absorption |

## Proposed Implementation Sequence

This sequence should be considered input to future reprioritization, not an
automatic change to the current ready item.

### CLI-001 - Command Registry Baseline

Goal: introduce command metadata and a dispatch table while preserving all
existing command behavior.

Files likely affected:

- `apps/jarvis_console/cli.py`
- `apps/jarvis_console/registry.py`
- `apps/jarvis_console/tests/test_console.py`

Done when:

- existing commands are registered by id, help text and handler;
- `main()` dispatch no longer depends on a long if/else chain;
- existing tests pass unchanged or with minimal adaptation.

### CLI-002 - Runtime Output Contract

Goal: define `ConsoleRuntime` with text/json output helpers, redaction and
exit-code constants.

Done when:

- read/report commands can emit structured JSON without changing core services;
- stdout/stderr behavior is documented and tested;
- no secrets or local sensitive paths are exposed by default.

### CLI-003 - Doctor Command

Goal: add `jarvis-console doctor` as read-only diagnostics.

Checks should include:

- Python/runtime availability;
- import health for core services;
- writable runtime directory;
- memory/evolution/observability DB reachability;
- engineering gate discoverability;
- backlog state read;
- governance mode visible;
- warnings for missing optional capabilities without failing.

### CLI-004 - Command Families And Renderer Split

Goal: move command families into modules without changing behavior.

Suggested families:

- `mission`;
- `objectives`;
- `work_items`;
- `artifacts`;
- `memory`;
- `evolution`;
- `observability`;
- `admin`.

### CLI-005 - Operator Cockpit Consolidation

Goal: improve MB-168 by making the cockpit a single read-only command that
combines mission, objective, work items, artifacts, reviews, autonomy state,
memory influence and next operator decision.

This should reuse existing services, not create a new architecture.

### CLI-006 - Completion And CLI Reference

Goal: generate shell completion and maintain an operator command reference from
the registry.

### CLI-007 - Golden/Snapshot Output Tests

Goal: preserve CLI UX and machine-readable contracts against regression.

## What Should Not Be Implemented From This Research Yet

- Full TUI.
- Browser automation.
- Computer use.
- Voice/realtime.
- External gateway or messaging surfaces.
- Autonomous scheduler.
- Plugin marketplace.
- Auto-promotion of evolution proposals.
- YOLO or permission bypass modes.
- Remote attach/control server.
- Rewriting the console in another language.

## Integration With Existing Backlog

At the time this analysis was created, the active micro queue kept `MB-161` as
the only ready item. After `MB-161` closed, this CLI research still should not
displace the ordered queue automatically; it should feed the CLI-related MBs.

Best fit for adoption:

- `CLI-001` and `CLI-002` should be considered enabling work before or inside
  `MB-168 - Operator Cockpit Expansion`.
- `CLI-003` can also support `MB-174 - Regression And Readiness Dashboard`.
- `CLI-005` maps directly to `MB-168`.

Recommended next decision:

- Keep following the ordered micro queue unless the operator explicitly
  reprioritizes toward CLI hardening.
- When CLI hardening is pulled, start with `CLI-001` and `CLI-002`; do not jump
  directly to TUI or broad cockpit expansion.

## Architectural Conclusion

The JARVIS CLI is directionally correct because it already routes operator use
through the governed core and exposes the operator learning loop. The next
quality jump is not adding many more commands. The next jump is turning the CLI
into a stable product surface:

- command registry;
- output contract;
- typed errors and exit codes;
- doctor diagnostics;
- JSON mode;
- command-family modules;
- cockpit consolidation;
- golden tests.

This keeps the system aligned with the Documento-Mestre: the CLI becomes a
robust operator surface without replacing the sovereign core, bypassing
governance or opening premature autonomy.
