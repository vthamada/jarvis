# JARVIS Console Command Reference

Status: generated active baseline from `MB-199`.

This file is generated from the typed command registry and its validated
`argparse` declarations. Do not edit it manually.

## Command Inventory

| Command | Category | Execution | Output | JSON | Description |
| --- | --- | --- | --- | --- | --- |
| `ask` | `mission` | `core` | `single` | `no` | Execute a single prompt. |
| `chat` | `mission` | `core` | `chat` | `no` | Run a simple multi-turn chat session. |
| `objectives` | `objective` | `core` | `single` | `yes` | Show the persisted objective state for a mission. |
| `goal-strategy` | `objective` | `core` | `single` | `yes` | Show read-only long-horizon strategy for a mission. |
| `objective` | `objective` | `core` | `single` | `no` | Apply a bounded operator transition to a mission objective. |
| `work-items` | `work` | `core` | `single` | `yes` | Show governed work items for a mission. |
| `work-item` | `work` | `core` | `single` | `no` | Apply a bounded operator transition to a mission work item. |
| `open-loops` | `work` | `core` | `single` | `yes` | Show governed open loops eligible for explicit resume. |
| `resume-loop` | `work` | `core` | `single` | `no` | Explicitly resume one governed open loop without autonomous execution. |
| `artifacts` | `artifact` | `core` | `single` | `yes` | Show governed living artifacts for a mission. |
| `artifact` | `artifact` | `core` | `single` | `no` | Apply a bounded lifecycle transition to a mission artifact. |
| `technology-candidates` | `evolution` | `standalone` | `single` | `yes` | Show recent governed technology absorption candidates. |
| `experience-reflections` | `memory` | `standalone` | `single` | `yes` | Show recent bounded post-task experience reflections. |
| `procedural-playbooks` | `memory` | `standalone` | `single` | `yes` | Show bounded procedural playbook candidates without activating them. |
| `skill-evolution` | `evolution` | `standalone` | `single` | `yes` | Show the read-only skill evidence, review and sandbox chain. |
| `evolution-review-queue` | `evolution` | `standalone` | `single` | `yes` | Show human-review evolution proposals without promoting them. |
| `evolution-review` | `evolution` | `standalone` | `single` | `no` | Apply a human review decision to an evolution proposal. |
| `memory-review-queue` | `memory` | `standalone` | `single` | `yes` | Show human-only consolidation, archive and expiration candidates. |
| `memory-review` | `memory` | `standalone` | `single` | `no` | Record a governed human decision without executing memory maintenance. |
| `mission-cycle` | `mission` | `core` | `single` | `yes` | Show a read-only operator learning loop for one mission. |
| `operator-dashboard` | `mission` | `core` | `single` | `yes` | Show a read-only daily operator dashboard. |
| `daily-workspace` | `mission` | `standalone` | `single` | `yes` | Show a read-only cross-session operator workspace. |
| `operator-outcomes` | `observability` | `standalone` | `single` | `yes` | Show evidence-backed daily operator utility outcomes. |
| `command-reference` | `observability` | `standalone` | `single` | `yes` | Show the deterministic registry-derived command reference. |
| `completion` | `observability` | `standalone` | `single` | `no` | Generate deterministic shell completion from the command registry. |
| `readiness-dashboard` | `observability` | `standalone` | `single` | `yes` | Show repository regression and readiness signals. |
| `doctor` | `observability` | `standalone` | `single` | `yes` | Run read-only local runtime and governance diagnostics. |
| `learning-report` | `observability` | `standalone` | `single` | `yes` | Show read-only longitudinal outcomes by reviewed version. |
| `progress-report` | `mission` | `core` | `single` | `yes` | Show a synthesized read-only mission progress report. |
| `mission-workflow` | `mission` | `core` | `single` | `no` | Run a governed mission and show the operator learning loop. |
| `mission-feedback` | `mission` | `core` | `single` | `no` | Record explicit bounded operator feedback after a mission. |

## Commands

### `ask`

Execute a single prompt.

Usage: `jarvis-console ask <prompt> [--session-id <value>] [--mission-id <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--debug] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `<prompt>` | yes | value | no | Single prompt to send to JARVIS. |
| `--session-id` | no | value | no | - |
| `--mission-id` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--debug` | no | flag | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `chat`

Run a simple multi-turn chat session.

Usage: `jarvis-console chat [--session-id <value>] [--mission-id <value>] [--message <value> ...] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--debug] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--session-id` | no | value | no | - |
| `--mission-id` | no | value | no | - |
| `--message` | no | value | yes | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--debug` | no | flag | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `objectives`

Show the persisted objective state for a mission.

Usage: `jarvis-console objectives --mission-id <value> [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `goal-strategy`

Show read-only long-horizon strategy for a mission.

Usage: `jarvis-console goal-strategy --mission-id <value> [--session-id <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `objective`

Apply a bounded operator transition to a mission objective.

Usage: `jarvis-console objective --mission-id <value> [--session-id <value>] --action <value> [--next-action-ref <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--action` | yes | `resume`, `pause`, `block`, `complete`, `redefine-next-action` | no | - |
| `--next-action-ref` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `work-items`

Show governed work items for a mission.

Usage: `jarvis-console work-items --mission-id <value> [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `work-item`

Apply a bounded operator transition to a mission work item.

Usage: `jarvis-console work-item --mission-id <value> [--session-id <value>] --action <value> --work-item-ref <value> [--next-action-ref <value>] [--depends-on <value> ...] [--clear-dependencies] [--priority <value>] [--blocker-ref <value> ...] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--action` | yes | `create`, `update`, `resume`, `pause`, `block`, `complete`, `redefine-next-action` | no | - |
| `--work-item-ref` | yes | value | no | - |
| `--next-action-ref` | no | value | no | - |
| `--depends-on` | no | value | yes | Add a governed dependency ref; repeat for multiple dependencies. |
| `--clear-dependencies` | no | flag | no | Replace the dependency set with an empty governed set. |
| `--priority` | no | `p0`, `p1`, `p2`, `p3` | no | - |
| `--blocker-ref` | no | value | yes | Declare an explicit blocker; required by the block action. |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `open-loops`

Show governed open loops eligible for explicit resume.

Usage: `jarvis-console open-loops --mission-id <value> [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `resume-loop`

Explicitly resume one governed open loop without autonomous execution.

Usage: `jarvis-console resume-loop --mission-id <value> --open-loop-ref <value> [--session-id <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--open-loop-ref` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `artifacts`

Show governed living artifacts for a mission.

Usage: `jarvis-console artifacts --mission-id <value> [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `artifact`

Apply a bounded lifecycle transition to a mission artifact.

Usage: `jarvis-console artifact --mission-id <value> [--session-id <value>] --action <value> --artifact-ref <value> [--artifact-version <value>] [--work-item-ref <value>] [--replacement-artifact-ref <value>] [--rollback-plan-ref <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--action` | yes | `register`, `activate`, `archive`, `replace`, `rollback` | no | - |
| `--artifact-ref` | yes | value | no | - |
| `--artifact-version` | no | value | no | - |
| `--work-item-ref` | no | value | no | - |
| `--replacement-artifact-ref` | no | value | no | - |
| `--rollback-plan-ref` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `technology-candidates`

Show recent governed technology absorption candidates.

Usage: `jarvis-console technology-candidates [--evolution-db <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--evolution-db` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `experience-reflections`

Show recent bounded post-task experience reflections.

Usage: `jarvis-console experience-reflections [--memory-db <value>] [--mission-id <value>] [--workflow-profile <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | - |
| `--mission-id` | no | value | no | - |
| `--workflow-profile` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `procedural-playbooks`

Show bounded procedural playbook candidates without activating them.

Usage: `jarvis-console procedural-playbooks [--memory-db <value>] [--workflow-profile <value>] [--review-status <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | - |
| `--workflow-profile` | no | value | no | - |
| `--review-status` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `skill-evolution`

Show the read-only skill evidence, review and sandbox chain.

Usage: `jarvis-console skill-evolution [--memory-db <value>] [--evolution-db <value>] [--skill-id <value>] [--version <value>] [--workflow-profile <value>] [--route <value>] [--domain <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--skill-id` | no | value | no | - |
| `--version` | no | value | no | - |
| `--workflow-profile` | no | value | no | - |
| `--route` | no | value | no | - |
| `--domain` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `evolution-review-queue`

Show human-review evolution proposals without promoting them.

Usage: `jarvis-console evolution-review-queue [--evolution-db <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--evolution-db` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `evolution-review`

Apply a human review decision to an evolution proposal.

Usage: `jarvis-console evolution-review [--evolution-db <value>] --proposal-id <value> --action <value> [--operator-ref <value>] [--evidence-ref <value> ...] [--proposed-test <value> ...] [--rollback-plan-ref <value>] [--risk-acceptance <value>] [--note <value> ...] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--evolution-db` | no | value | no | - |
| `--proposal-id` | yes | value | no | - |
| `--action` | yes | `approve`, `reject`, `sandbox`, `needs-review`, `rollback` | no | - |
| `--operator-ref` | no | value | no | - |
| `--evidence-ref` | no | value | yes | - |
| `--proposed-test` | no | value | yes | - |
| `--rollback-plan-ref` | no | value | no | - |
| `--risk-acceptance` | no | value | no | - |
| `--note` | no | value | yes | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `memory-review-queue`

Show human-only consolidation, archive and expiration candidates.

Usage: `jarvis-console memory-review-queue [--memory-db <value>] [--maintenance-action <value>] [--review-status <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | - |
| `--maintenance-action` | no | `consolidate`, `archive`, `expire` | no | - |
| `--review-status` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `memory-review`

Record a governed human decision without executing memory maintenance.

Usage: `jarvis-console memory-review [--memory-db <value>] --candidate-id <value> --action <value> [--operator-ref <value>] [--evidence-ref <value> ...] [--rollback-plan-ref <value>] [--note <value> ...] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | - |
| `--candidate-id` | yes | value | no | - |
| `--action` | yes | `approve`, `reject`, `needs-review`, `rollback` | no | - |
| `--operator-ref` | no | value | no | - |
| `--evidence-ref` | no | value | yes | - |
| `--rollback-plan-ref` | no | value | no | - |
| `--note` | no | value | yes | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `mission-cycle`

Show a read-only operator learning loop for one mission.

Usage: `jarvis-console mission-cycle --mission-id <value> [--memory-db <value>] [--evolution-db <value>] [--workflow-profile <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--memory-db` | no | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--workflow-profile` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `operator-dashboard`

Show a read-only daily operator dashboard.

Usage: `jarvis-console operator-dashboard [--mission-id <value>] [--memory-db <value>] [--evolution-db <value>] [--workflow-profile <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | no | value | no | - |
| `--memory-db` | no | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--workflow-profile` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `daily-workspace`

Show a read-only cross-session operator workspace.

Usage: `jarvis-console daily-workspace [--memory-db <value>] [--evolution-db <value>] [--limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--memory-db` | no | value | no | Use an explicit canonical memory store (defaults to the console store). |
| `--evolution-db` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `operator-outcomes`

Show evidence-backed daily operator utility outcomes.

Usage: `jarvis-console operator-outcomes [--observability-db <value>] [--memory-db <value>] [--period-start <value>] [--period-end <value>] [--event-limit <value>] [--mission-limit <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--observability-db` | no | value | no | - |
| `--memory-db` | no | value | no | - |
| `--period-start` | no | value | no | - |
| `--period-end` | no | value | no | - |
| `--event-limit` | no | value | no | - |
| `--mission-limit` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `command-reference`

Show the deterministic registry-derived command reference.

Usage: `jarvis-console command-reference [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `completion`

Generate deterministic shell completion from the command registry.

Usage: `jarvis-console completion --shell <value> [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--shell` | yes | `powershell`, `bash`, `zsh` | no | Select the target shell. |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `readiness-dashboard`

Show repository regression and readiness signals.

Usage: `jarvis-console readiness-dashboard [--run-gate <value>] [--longitudinal-report <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--run-gate` | no | `quick`, `standard` | no | Explicitly refresh engineering gate evidence before reporting. |
| `--longitudinal-report` | no | value | no | Use an explicit MB-188 longitudinal report JSON artifact. |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `doctor`

Run read-only local runtime and governance diagnostics.

Usage: `jarvis-console doctor [--runtime-dir <value>] [--memory-db <value>] [--evolution-db <value>] [--observability-db <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--runtime-dir` | no | value | no | - |
| `--memory-db` | no | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--observability-db` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `learning-report`

Show read-only longitudinal outcomes by reviewed version.

Usage: `jarvis-console learning-report [--observability-db <value>] [--memory-db <value>] [--evolution-db <value>] [--limit <value>] [--minimum-observations <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--observability-db` | no | value | no | - |
| `--memory-db` | no | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--limit` | no | value | no | - |
| `--minimum-observations` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `progress-report`

Show a synthesized read-only mission progress report.

Usage: `jarvis-console progress-report --mission-id <value> [--session-id <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `mission-workflow`

Run a governed mission and show the operator learning loop.

Usage: `jarvis-console mission-workflow <prompt> [--session-id <value>] --mission-id <value> [--evolution-db <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `<prompt>` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--mission-id` | yes | value | no | - |
| `--evolution-db` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

### `mission-feedback`

Record explicit bounded operator feedback after a mission.

Usage: `jarvis-console mission-feedback --mission-id <value> [--session-id <value>] [--experience-id <value>] --assessment <value> [--rating <value>] [--comment <value>] [--correction <value>] [--next-expectation <value>] [--evidence-ref <value> ...] [--evolution-db <value>] [--operator-identity-ref <value>] [--canonical-user-ref <value>] [--format <value>]`

| Argument | Required | Values | Repeatable | Description |
| --- | --- | --- | --- | --- |
| `--mission-id` | yes | value | no | - |
| `--session-id` | no | value | no | - |
| `--experience-id` | no | value | no | - |
| `--assessment` | yes | `helpful`, `partially-helpful`, `not-helpful`, `correction` | no | - |
| `--rating` | no | value | no | - |
| `--comment` | no | value | no | - |
| `--correction` | no | value | no | - |
| `--next-expectation` | no | value | no | - |
| `--evidence-ref` | no | value | yes | - |
| `--evolution-db` | no | value | no | - |
| `--operator-identity-ref` | no | value | no | - |
| `--canonical-user-ref` | no | value | no | - |
| `--format` | no | `text`, `json` | no | Select human text or supported machine-readable JSON output. |

## Boundaries

- completion and reference generation are read-only;
- command execution mode does not grant or bypass authority;
- state-changing commands still cross their existing governance path;
- generated assets contain no runtime paths, secrets, ids or timestamps.
