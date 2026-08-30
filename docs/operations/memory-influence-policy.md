# Governed Memory Influence Policy

Status: active baseline from `MB-186`, hardened by `MB-203` and `MB-204`.

## Purpose

The memory influence policy decides which already-recovered inputs may affect
planning and synthesis. It does not retrieve, persist, consolidate, expire or
promote memory. Existing canonical memory repositories remain the only source
of runtime records.

The governed cycle is:

`recover -> scope -> verify evidence -> order -> resolve conflict -> apply or ignore -> audit`

## Inputs

`MemoryInfluenceSignalContract` normalizes four existing influence classes:

- `reviewed_learning`: guidance explicitly approved or sandboxed by a human;
- `procedural`: bounded execution sequence from canonical mission/artifact memory;
- `semantic`: domain or mission framing with anchor and evidence refs;
- `reflection`: bounded post-task learning not yet equivalent to reviewed guidance.

Every signal declares source ref, route/workflow/domain scope, evidence,
lifecycle/review status, conflict group, directive and allowed usage.
Retrieval alone never grants causal use.

`MB-203` adds `SemanticMemoryCandidateContract` as the bounded recovery input
for real mission flows. The canonical mission state supplies the anchor,
summary, evidence refs, observation timestamp and domain hints. Recovery marks
freshness and relevance but remains read-only; the influence policy, not the
retriever, decides causal use.

Semantic freshness is recalculated at decision time from `observed_at` and the
request timestamp. A claimed freshness value that differs from the computed
value fails closed. `current` and `aging` may be eligible; `stale`, `unknown`
or missing timestamps are never presumed usable. Relevance must be explicit,
bounded to `0..1`, justified and at least `0.5`.

## Reviewed Procedural Playbooks

`MB-204` adds `ReviewedProceduralPlaybookContract` as the only reviewed
procedural artifact that can become runtime guidance. A
`ProceduralPlaybookCandidateContract` remains sandbox-only and cannot be used
directly. The `evolution-lab` derives a reviewed playbook only when all of the
following refer to the same immutable candidate snapshot:

- a persisted human review has a non-empty bounded operator identity, is
  `approved` and names canonical ASCII semver
  (`major.minor.patch`, without leading-zero aliases);
- the proposal, candidate identity, scope, steps, evidence, tests and rollback
  still match the reviewed snapshot;
- the sandbox-to-release checklist is `ready_for_release_review`;
- the promotion gate is `passed` with
  `release_gate_passed_pending_human_decision` and both the standard
  engineering gate and release gate recorded;
- execution, tool dispatch, memory write, automatic promotion and Core
  mutation authority are all false.

The release gate makes the evidence complete; it does not authorize promotion.
Each version requires its own human review. The evolution verifier reconstructs
and validates the persisted proposal/review/release chain fail-closed. The
`memory-service` refuses to store, revoke or return a reviewed playbook when
that verifier is absent or returns false. The normal console runtime binds the
memory reader to the persisted `evolution-lab` database, so the same candidate,
review, release timestamp and gate chain are reverified after restart. The
repository write methods are internal storage seams and never grant runtime
eligibility by themselves.

SQLite and PostgreSQL atomically insert `(playbook_id, version)` without
overwriting an existing payload. Revocation is a separate atomic transition
from `approved` to `revoked`; it preserves the artifact and adds revocation
evidence. Runtime recovery filters route, workflow and domain in the repository
and pages through matching rows until verification is applied before the
caller-visible result limit. Unrelated, revoked or unverified recent rows
therefore cannot starve an eligible scoped playbook.

## Priority

The fixed priority is:

1. `reviewed_learning`
2. `procedural`
3. `semantic`
4. `reflection`

Different conflict groups may coexist. Two signals conflict only when they
declare the same group and different directives. The higher-priority signal is
selected; the lower one is ignored with
`conflict_with_higher_priority:<ref>`. Equal directives may coexist as
corroborating evidence.

Eligibility and ordering run over the complete bounded input before any
application cap. Duplicate signal identity fails closed. For reviewed
procedural playbooks, newer canonical semver ranks ahead of older versions and
only one playbook may be applied to a plan; every otherwise eligible excess
playbook receives an explicit non-use reason.

## Fail-Closed Rules

A signal is ignored when it has:

- missing evidence;
- route, workflow or domain mismatch;
- blocked lifecycle or review status;
- no planning usage permission;
- unsupported source kind;
- duplicate or unbounded identity;
- missing/invalid playbook semver or persisted review ref;
- candidate-only, revoked or scope-mismatched playbook;
- automatic promotion or Core mutation authority;
- writable or non-read-only memory authority;
- execution or tool-dispatch authority;
- stale, unknown or forged semantic freshness;
- missing, invalid or low semantic relevance;
- unbounded evidence refs or relevance reason.

`MemoryInfluencePolicyDecisionContract` records selected, ignored and conflict
refs, priority order, use and non-use reasons, evidence and policy refs. It
also records version and human-review refs by signal plus explicit execution
and tool-dispatch flags.
`GovernanceService.assess_memory_influence_policy` verifies the complete trail
and emits `memory_influence_governed`.

## Runtime Interpretation

- `applied`: one or more eligible signals were used without conflict.
- `applied_with_conflict_resolution`: a higher-priority signal won an explicit
  conflict.
- `blocked_no_eligible_signal`: signals existed but none could be used.
- `not_applicable`: no influence signal existed.

Planning suppresses effects from ignored sources. Synthesis shows priority,
used refs, ignored refs and non-use reasons and does not claim an ignored
reflection was applied.

An eligible reviewed playbook contributes bounded textual guidance to planning
only. Its steps are not operation specs, scripts or tool calls. The plan keeps
the playbook version and review decision visible and states that execution,
tool dispatch, memory write and promotion remain unavailable. Even when the
request directive would otherwise be executable, both the native orchestrator
path and the optional LangGraph path assess the same memory governance before
the dispatch boundary. A blocked or incomplete trace fails closed, and selected
playbook guidance leaves `operation_dispatch` and `operation_result` empty.

For semantic candidates, the decision also records signal kind, computed
freshness and relevance score. `memory_influence_governed`, `plan_built` and
`response_synthesized` expose the same maps. A route, workflow or domain
mismatch remains non-use even when the candidate belongs to the same mission.
An empty candidate set produces no semantic anchors, evidence or effects.

For reviewed playbooks, `memory_influence_governed`, `plan_built` and
`response_synthesized` expose the same version map, review-decision map,
application/non-use reasons and false execution/tool-dispatch flags. Final
synthesis repeats this provenance in the human-readable response. `FlowAudit`
reconstructs the same trail and treats missing review/version provenance or an
authority claim as drift rather than silently accepting it.

All decisions remain read-only with memory writes, decision mutation,
automatic promotion and Core mutation disabled.
