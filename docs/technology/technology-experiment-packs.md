# Technology experiment packs

Status: active baseline from MB-209.

## Purpose and authority boundary

A technology experiment pack translates one selected, reviewed radar intake into
an inert hypothesis about an absorbable pattern. It does not install or import a
framework, execute candidate code, run a subprocess, fetch a source, dispatch a
tool, call Core, write Knowledge or Memory, create a generic Evolution proposal,
activate runtime behavior or authorize release or promotion.

The canonical sequence is:

```text
exact MB-208 intake + detached-digest local pack manifest
    -> strict translation and binding validation
    -> append-only inert pack
    -> detached-digest local run identity
    -> metrics derived from paired preproduced observations
    -> append-only sandbox-only result for human review
```

Only `translation_kind=absorbable_pattern` is accepted. Framework substitution
is not an experiment pack. The external technology remains a
`subordinate_reference`, while the selected consumer must be an allowlisted
sovereign JARVIS component with an explicit contract and bounded integration
seam.

## Exact intake binding

Pack selection starts from an exact persisted `TechnologyRadarIntakeContract`,
resolved by `intake_id` and canonical SemVer `intake_version`. The manifest must
carry its canonical intake fingerprint, but it cannot override source identity,
source content SHA-256, candidate identity, technology name, absorption class or
license evidence: those values are copied from the verified intake.

Selected claim and risk fingerprints and target gap refs must be subsets of that
same intake. The intake must be an immutable reviewed reference with an approved
human review, an eligible sandbox absorption class and a resolved declared
license. Evaluation resolves both the exact persisted pack and its exact intake
again; a missing, changed or invented binding fails closed before a run can be
recorded.

See [Technology radar intake](technology-radar-intake.md) for the source-review
contract and its operator-attestation limits.

## Local manifests and detached digests

Both state-changing commands consume one UTF-8 JSON object inside an explicitly
supplied local manifest root. The pack manifest is bounded to 128 KiB and the
evaluation manifest to 256 KiB. Each command requires the lowercase SHA-256 of
the exact reviewed file as a separate argument.

The loader rejects duplicate keys, non-finite numbers, missing or unknown
fields, BOMs, control characters, credentials, sensitive paths, executable or
dependency fields, remote/device paths, traversal, symlinks, hard links and a
file or root that changes while it is read. Digest mismatch fails before a
writer is used. The detached digest binds bytes; it is not a signature and does
not authenticate the operator.

The pack manifest defines:

- pack identity and exact intake identity/fingerprint;
- the absorbable pattern, hypothesis, expected gain, sovereign consumer,
  contract, bounded seam and target gaps;
- selected claim/risk fingerprints, risk controls, mitigations and stop
  conditions;
- baseline and candidate definition refs/hashes;
- license inherited from the intake, rollback plan/steps/checks and selection
  review;
- one or more paired cases with the same input fingerprint and fixed control
  snapshot;
- baseline and candidate observations, evidence refs, limitations and the
  required pass rate.

The much smaller evaluation manifest contains only `run_id`, exact pack
identity/version/fingerprint and `generated_at`. Caller-provided metrics,
status, readiness, blockers or promotion fields are rejected; all of them are
derived.

## Paired preproduced evidence

Each case compares baseline and candidate observations over the same input,
control snapshot, deterministic seed, fixed clock, isolation profile and check
universe. Observations use
`source_mode=preproduced_sandbox_attestation`. They are inert records produced
outside this evaluator by a separately controlled process; JARVIS does not run
the candidate to create them.

Both arms must report completed outcomes, preserve the sovereign-consumer
contract and pass all mandatory isolation checks:

- `dependencies_unchanged`;
- `external_code_not_executed`;
- `host_filesystem_unchanged`;
- `network_disabled`.

The candidate must pass its success criteria, show at least one improvement,
retain evidence and introduce no regression or limitation. A failed/blocked
outcome, invalid baseline, missing isolation, limitation or regression makes the
case fail. Chronology is ordered from the verified intake through the fixed
observations and pack to the claim/run; future or backdated evidence fails
closed.

The evaluator independently derives these metrics from the observation fields:

- `success_score`;
- `contract_adherence`;
- `isolation_compliance`;
- `sovereign_consumer_preservation`;
- `rework_rate`.

It then derives per-case deltas and aggregates, pass rate, regression flags,
blockers, comparison conclusion and readiness. A green run is still only
`passed_sandbox_only` and `eligible_for_human_experiment_review`;
`promotion_readiness` remains `not_applicable`, and every execution, release,
promotion, Core and priority authority flag remains false.

## Operator commands

Register an inert pack from a reviewed local manifest:

```powershell
python -m apps.jarvis_console technology-experiment-pack `
  --manifest-root .\reviewed-technology-experiments `
  --manifest pack-v1.json `
  --manifest-sha256 <lowercase-sha256-of-reviewed-pack-json>
```

Derive and append a result from the exact persisted pack:

```powershell
python -m apps.jarvis_console technology-experiment-eval `
  --manifest-root .\reviewed-technology-experiments `
  --manifest run-v1.json `
  --manifest-sha256 <lowercase-sha256-of-reviewed-run-json>
```

Inspect verified packs or runs without mutation:

```powershell
python -m apps.jarvis_console technology-experiments --view packs
python -m apps.jarvis_console technology-experiments --view runs --status blocked
python -m apps.jarvis_console technology-experiments --view runs --format json
```

Use `--evolution-db` to select a non-default local store. The pack and eval
commands are state-changing and intentionally text-only. The read command
supports text or JSON, exact identities and bounded filters/pagination.

Exact pack and run retries are idempotent. A divergent payload for an existing
identity is a collision. Run identity is reserved by an append-only claim before
the derived result is recorded, so a retry after an interrupted write cannot
silently rebind the run.

## Integrity and limitations

The Evolution store keeps packs, run claims and runs in dedicated tables. It
stores canonical JSON plus SHA-256, enforces identities and foreign-key bindings,
and has no-update/no-delete triggers. Reads reconstruct and revalidate the full
pack/intake/result chain; invalid rows are omitted. These records are not generic
evolution proposals and cannot be promoted by this workflow.

That persistence guarantee is stronger than the in-memory Python object model.
The contracts are frozen dataclasses and declare `immutable=True` where
applicable, which prevents field rebinding, but nested `list` and `dict` values
are still shallowly mutable. Callers must treat materialized contracts as
read-only. Public write/read boundaries recalculate fingerprints and revalidate
the canonical payload, so a mutated object is rejected or no longer matches its
persisted identity; the type itself does not provide deep immutability.

The evaluator verifies internal consistency, chronology, exact persisted
bindings and deterministic metric derivation. It does not cryptographically
verify who produced an observation, independently reproduce the external
sandbox, inspect the referenced evidence contents, prove the environment or
isolation fingerprints, verify upstream source/license authenticity or prove
causal benefit. A privileged actor able to remove database protections and
rewrite payloads and hashes is outside the local tamper-evidence model. Human
review and the separate governed promotion workflow remain mandatory.
