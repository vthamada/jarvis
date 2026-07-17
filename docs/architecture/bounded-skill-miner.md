# Bounded Skill Miner

## Purpose

`MB-178` implements the controlled conversion step between recurring-pattern
evidence and an inactive skill candidate:

`pattern evidence -> bounded miner -> inactive registry candidate`

The miner is a deterministic compiler. It does not discover arbitrary behavior,
run autonomously, activate a skill or create release authority.

## Contracts

`SkillMiningRequestContract` supplies the explicit candidate interface:

- source pattern, logical skill ID, name and numeric semantic version;
- subordinate specialist type;
- inputs, outputs, bounded instructions and explicit allowed tools;
- risk, failure modes, tests and rollback;
- immutable safety flags that prohibit automatic mining, activation, promotion
  and Core mutation.

`SkillMiningResultContract` returns:

- eligibility and mining status;
- observed and required occurrence counts;
- source authority status;
- evidence and blockers;
- an optional `SkillCandidateContract`.

A blocked result always has `candidate=None`.

## Eligibility gate

Candidate generation requires all of the following:

1. source pattern status is `evidence_ready_for_human_review`;
2. occurrence and successful-outcome counts meet the effective threshold;
3. all source outcomes are successful;
4. distinct experience and reflection refs meet the threshold;
5. evidence refs exist;
6. confidence is `bounded_moderate` or `bounded_high`;
7. no pattern blocker or conflict exists;
8. source and request preserve human review and deny automatic authority;
9. the skill specification is complete, bounded and uses explicit tool names;
10. risk is at most `moderate` in this miner lane.

The effective threshold is the greater of the miner minimum and the threshold
recorded by the source pattern.

## Determinism and idempotence

The candidate identity is derived from:

`source pattern + logical skill ID + version`

The candidate timestamp comes from the source pattern evidence. Repeating the
same mining operation therefore yields the same registry identity and content.
Changing material content without incrementing the version is rejected by the
skill registry.

## Authority boundary

The source pattern remains `observation_only`. The miner is the explicit,
separate conversion boundary introduced after the pattern baseline, but its
output remains:

- `candidate_inactive`;
- `needs_review`;
- `inactive`;
- `sandbox_required=true`;
- automatic activation/promotion and Core mutation disabled.

Human review, sandbox eval and promotion checklist are later, independent
steps. A green miner result is not approval and is not runtime availability.
