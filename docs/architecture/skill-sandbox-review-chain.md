# Skill Review And Sandbox Chain

## Purpose

`MB-179` connects an inactive skill candidate to the existing governed
evolution chain without making it available to runtime:

`inactive candidate -> proposal -> human review -> sandbox eval -> checklist -> release gate -> separate human promotion decision`

The final step remains outside this baseline. Even a fully green gate has
`promotion_authorized=false`.

## Proposal boundary

`EvolutionLabService.create_proposal_from_skill_candidate` persists a
`skill_candidate` proposal containing:

- candidate and logical skill identities;
- version, workflow, domain, specialist and risk;
- interface, bounded instructions and allowed tools;
- source patterns, evidence, failure modes, tests and rollback;
- inactive runtime status and explicit sandbox/release policy.

Malformed or unsafe candidates remain blocked proposals. The proposal does not
write to routing, planning, tool dispatch or any active skill registry.

## Human review

The existing review queue and `review_proposal` path remain authoritative. A
skill review decision now also carries `candidate_identity_ref` and
`candidate_version`, in addition to evidence, tests and rollback. Approval or
sandbox selection records human intent only; it does not activate or promote
the candidate.

## Sandbox eval

`SkillSandboxEvalContract` derives each case result from declared boolean
checks. Callers cannot provide an independent optimistic `passed` value.

The eval validates:

- proposal, review and candidate identities;
- skill ID and version across all records;
- human review status `approved` or `sandboxed`;
- candidate remains inactive;
- non-empty bounded test cases;
- required pass rate;
- external eval evidence;
- proposed tests and matching rollback.

A passing result is `passed_pending_release_gate`. A failed or malformed run is
`blocked`. Both keep runtime activation and promotion authorization false. The
eval summary is merged into the latest persisted proposal so prior human review
history is not overwritten.

## Checklist and promotion gate

For a skill proposal, `SandboxToReleaseChecklistContract` additionally carries:

- `candidate_type=skill_candidate`;
- logical skill identity and version;
- sandbox eval ref and status;
- mandatory `skill_sandbox_eval` gate.

Missing, failed or mismatched eval evidence blocks the checklist. The promotion
gate derives `skill_sandbox_eval` only from a passing, linked eval and cannot be
spoofed through the caller-provided completed-gate list.

A passed promotion gate means only
`release_gate_passed_pending_human_decision`. Activation requires a later,
explicit human promotion path and is not implemented here.
