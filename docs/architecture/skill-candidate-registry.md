# Skill Candidate Registry

## Purpose

The `MB-177` registry separates four concepts that must not collapse into one:

1. recurring-pattern evidence;
2. an inactive skill candidate;
3. a sandbox-evaluated candidate;
4. an active, human-promoted runtime skill.

This baseline implements only item 2. Registration never means activation,
approval, sandbox success or promotion.

## Canonical contract

`SkillCandidateContract` defines:

- `skill_candidate_id`, logical `skill_id` and numeric semantic `version`;
- name, workflow, domain and subordinate specialist type;
- explicit inputs, outputs, bounded instructions and allowed tools;
- risk level, evidence refs and source recurring-pattern refs;
- known failure modes, proposed tests and rollback plan;
- registry, review and activation status;
- sandbox, human review and sovereign-memory invariants.

The default and enforced lifecycle state is:

```text
registry_status=candidate_inactive
review_status=needs_review
activation_status=inactive
sandbox_required=true
human_review_required=true
```

## Identity and versioning

The persistent registry uses:

- primary identity: `skill_candidate_id`;
- unique logical version: `(skill_id, version)`;
- version format: numeric semantic version `major.minor.patch`.

An identical retry is idempotent. Changing an already registered candidate or
using a different candidate ID for the same logical version is rejected. A
material change therefore requires a new version and its own evidence.

## Persistence

`memory-service` owns the canonical registry through SQLite and PostgreSQL
repositories. Queries are bounded and may filter by skill, version, domain and
review status. There is no alternate evolution database and no direct write
path outside the sovereign memory service.

## Containment

The service normalizes or blocks unsafe declarations:

- active/approved states are forced back to inactive/needs-review;
- sandbox opt-out becomes a blocker;
- automatic activation and promotion remain false;
- Core mutation remains false;
- memory writes remain `through_core_only`;
- high or critical risk requires explicit sandbox review;
- missing scope, contracts, pattern/evidence refs, failure modes, tests or
  rollback remain visible blockers;
- lists and values are bounded before persistence.

## Non-goals

This baseline does not:

- convert pattern evidence into a candidate automatically;
- create an evolution proposal;
- run sandbox evals;
- expose a console command;
- activate a candidate in routing, planning or tool execution;
- authorize release or mutate Core behavior.

Those steps remain separately gated by `MB-178` onward.
