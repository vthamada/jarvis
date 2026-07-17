# Regression And Readiness Dashboard

## 1. Purpose

`MB-174` adds a compact read-only view of repository health. It consolidates
existing sources instead of introducing a second status authority:

- capability maturity from `implementation-master-map.md`;
- executable queue status from `execution-backlog.md`;
- active-document identity from `verify_document_guardrails.py`;
- test and quality evidence from `engineering_gate.py`.

The report never authorizes release, promotion or Core mutation.

## 2. Console Use

Read the current repository state without running a gate:

```powershell
python -m apps.jarvis_console readiness-dashboard
```

Refresh quick static evidence explicitly:

```powershell
python -m apps.jarvis_console readiness-dashboard --run-gate quick
```

Refresh test and standard-gate evidence explicitly:

```powershell
python -m apps.jarvis_console readiness-dashboard --run-gate standard
```

Without `--run-gate`, `gate_status` and `test_status` remain `not_run`. The
dashboard does not treat old or absent evidence as a pass.

## 3. Standalone Report And History

The standalone tool emits text or JSON and, by default, writes `latest.json`
plus a timestamped history entry under `.jarvis_runtime/readiness/`:

```powershell
python tools/readiness_dashboard.py --run-gate standard
python tools/readiness_dashboard.py --format json
python tools/readiness_dashboard.py --no-save
```

Historical artifacts are operational evidence only and remain outside Git.

## 4. Capability Semantics

- `ready`: implemented baseline.
- `partial`: minimum or partial runtime baseline.
- `attention_required`: documented or candidate capability needing work.
- `missing`: active candidate without implementation.
- `deferred`: later-phase or research capability; it is visible but does not
  block the current baseline.

The report separates `baseline`, `candidate` and `deferred` scope before
calculating the score. Future voice, web, computer use and deep self-evolution
therefore do not become false current-release failures.

## 5. Repository Status

The report checks whether:

- the executable backlog has zero or one `ready` item;
- a `ready` item is also marked ready in the master map;
- active status documents mention the current item or latest closed item;
- critical document guardrails pass.

An exhausted queue is a valid state and is reported as `queue_exhausted`; it
requires reprioritization, not a fabricated ready item.

## 6. Overall Status

- `ready`: gate/tests/docs/backlog pass and active capabilities are healthy.
- `ready_with_known_gaps`: current evidence passes, with partial or candidate
  gaps still visible.
- `evidence_required`: no fresh gate or test evidence was requested.
- `blocked`: gate failure, document failure, status drift or missing baseline
  capability.

Even `ready` means evidence is coherent for human release review. The contract
keeps `autonomous_release_allowed=false`.

## 7. Limits

- The dashboard does not replace release gates or human approval.
- It does not execute gates implicitly.
- It does not claim production readiness for deferred capabilities.
- Longitudinal comparison currently depends on saved JSON history; trend
  analytics remain a later capability.
