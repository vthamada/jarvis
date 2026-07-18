# Governed Memory Influence Policy

Status: active baseline from `MB-186`, hardened by `MB-203`.

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

## Fail-Closed Rules

A signal is ignored when it has:

- missing evidence;
- route, workflow or domain mismatch;
- blocked lifecycle or review status;
- no planning usage permission;
- unsupported source kind;
- duplicate or unbounded identity;
- automatic promotion or Core mutation authority.
- writable or non-read-only memory authority;
- stale, unknown or forged semantic freshness;
- missing, invalid or low semantic relevance;
- unbounded evidence refs or relevance reason.

`MemoryInfluencePolicyDecisionContract` records selected, ignored and conflict
refs, priority order, use and non-use reasons, evidence and policy refs.
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

For semantic candidates, the decision also records signal kind, computed
freshness and relevance score. `memory_influence_governed`, `plan_built` and
`response_synthesized` expose the same maps. A route, workflow or domain
mismatch remains non-use even when the candidate belongs to the same mission.
An empty candidate set produces no semantic anchors, evidence or effects.

All decisions remain read-only with memory writes, decision mutation,
automatic promotion and Core mutation disabled.
