# Governed Domain Onboarding Protocol

Status: active minimum baseline from `MB-171`.

## Purpose

This protocol defines the safe transition from a domain listed in the canonical
map to a candidate runtime route. A document, corpus fragment or attractive
technology is not enough to activate a domain.

The protocol preserves the sovereign core: assessment is advisory, registry
writes are disabled, deep specialist promotion is disabled and human review is
mandatory.

## Required Candidate Package

Every candidate must provide:

1. A canonical domain reference already present in the domain registry.
2. A unique bounded runtime route identifier.
3. A versioned `DomainKnowledgePackContract` with sources, content references,
   coverage topics, evidence and freshness status.
4. A `domain_onboarding_workflow` declaration and a complete proposed runtime
   workflow with steps, checkpoints and decision points.
5. Proposed tests, an eval pack reference, evidence and a rollback plan.
6. Either no specialist (`registry_only`) or an existing canonical specialist
   in `shadow` mode.
7. Human review with all automatic activation, promotion and core mutation
   permissions disabled.

## Assessment Result

`assess_domain_onboarding_candidate` returns one of two states:

- `ready_for_human_review`: all minimum criteria are coherent; no activation is
  performed.
- `blocked`: the candidate must return for revision with explicit blockers.

The assessment includes a `registry_preview` for review. It never modifies
`CANONICAL_DOMAIN_REGISTRY`, `RUNTIME_ROUTE_REGISTRY` or the specialist
registry.

## Promotion Boundary

`MB-171` does not promote a domain. Promotion requires a later human decision,
real eval evidence, a governed registry change, targeted tests and the standard
engineering gate. A linked specialist may only enter this onboarding stage in
`shadow` mode. `guided` or `active` requests are blocked.

## Reproducible Baseline

`knowledge/curated/domain_onboarding_baseline.json` is a non-active candidate
manifest used to prove the protocol. It references the canonical education
domain, but it does not add `education_learning` to runtime retrieval.

`MB-172` materialized the reusable offline domain eval pattern with the
promoted `analysis` route. The education candidate still requires its own pack
and passing evidence before any real promotion can be considered.
