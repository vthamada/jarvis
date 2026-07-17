# Implementation Master Map

Status: active implementation planning map
Date: 2026-07-02
Owner: governed execution backlog
Sovereign source: `documento_mestre_jarvis.md`

## 1. Purpose

This document maps the full implementation surface required for JARVIS to move
from the current governed core toward the long-term vision: a unified,
stateful, multi-domain, self-improving, governed operational intelligence.

It exists because the micro backlog is intentionally small and safe. That is
good for execution, but insufficient for seeing the complete path.

This map answers:

- what exists today;
- what is partial;
- what is missing;
- what is intentionally deferred;
- what depends on what;
- what should become a micro backlog slice next;
- what must not be implemented yet.

## 2. Relationship With Other Planning Documents

| Document | Role | This map does not replace it |
| --- | --- | --- |
| `documento_mestre_jarvis.md` | Constitutional source | It remains sovereign. |
| `docs/implementation/execution-backlog.md` | Micro execution queue | This map feeds it, but does not execute by itself. |
| `docs/implementation/unified-gap-and-absorption-backlog.md` | Macro gap and technology absorption map | This map turns those gaps into product/capability decomposition. |
| `docs/implementation/v2-adherence-snapshot.md` | State snapshot against the master vision | This map uses that snapshot as evidence. |
| `docs/architecture/documento_evolutivo_jarvis.md` | Evolution research and architecture reference | This map only schedules safe slices from it. |
| `docs/operations/operator-learning-loop.md` | Human operating loop | This map treats it as the current user-facing learning baseline. |

Rule: if this document conflicts with the Documento-Mestre, the
Documento-Mestre wins.

## 3. Status Grammar

| Status | Meaning |
| --- | --- |
| `implemented_baseline` | Present in runtime, tests and docs as part of the current baseline. |
| `minimum_baseline` | Present as a bounded MVP slice, not the full target capability. |
| `partial_runtime` | Exists in runtime but needs deeper causality, coverage or productization. |
| `documentation_only` | Documented, but not materially implemented. |
| `missing` | Required by the vision and not implemented in a meaningful way. |
| `deferred_by_phase` | Valid, but explicitly not for the current phase. |
| `research_only` | Horizon capability; no production implementation should be opened yet. |
| `human_decision_required` | Technically possible, but requires explicit operator direction. |

## 4. Current Baseline Reading

The current baseline has closed:

- governed orchestration through core services and engines;
- canonical memory and domain registries;
- planning, synthesis, governance, observability and operational artifacts;
- specialist selection and subordinate handoffs through the core;
- mission state, objective continuity and bounded project/task state;
- technology absorption candidates as sandbox-only proposals;
- experience records and post-task reflections;
- human review queue for evolution proposals;
- reviewed-learning guidance influencing planning/synthesis in a bounded way;
- baseline-vs-assisted measurement for reflection and reviewed learning;
- console commands for mission workflow, mission cycle, objectives and review;
- documentation canonicality audit, backlink map and conservative archive moves.
- minimum long-horizon goal strategy derived from mission state, work items,
  artifacts, checkpoints, memory anchors and auditable next action.

The current system is not yet a fluid daily product. The main gap is no longer
"does the core exist?". The main gap is "can an operator use it every day as a
practical mission partner across knowledge, tools, artifacts, goals and time?".

## 5. Implementation Tracks

### Track A -- Operator Product Loop

Goal: make JARVIS useful to a human operator in daily work.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `OP-001` | Start and close a governed mission | `implemented_baseline` | Keep stable | Operator Learning Loop | none |
| `OP-002` | Inspect mission route, plan, checkpoints and synthesis | `implemented_baseline` | Keep stable | Console, orchestrator | none |
| `OP-003` | Manage objective/project state | `implemented_baseline` | Validate cockpit through real operator use | MissionState, memory | none |
| `OP-004` | Manage tasks/work items as first-class operator objects | `minimum_baseline` | Create/update/close work items through governance | Objective continuity | expand after artifact lifecycle |
| `OP-005` | Manage artifacts as living outputs | `minimum_baseline` | Artifact registry, versions, owner, status | Operational service, memory | expand after metrics |
| `OP-006` | Daily operator dashboard | `implemented_baseline` | Validate usefulness and evolve from operator evidence | Console, memory, observability | none |
| `OP-007` | Operator feedback after mission | `implemented_baseline` | Validate usefulness through real operator feedback | Experience/reflection | none |
| `OP-008` | Human-readable progress report | `implemented_baseline` | Validate report usefulness with operator evidence | Synthesis, memory | none |
| `OP-009` | Multi-session daily continuity | `partial_runtime` | Resume work across days with active/open loops | Memory, mission state | candidate |
| `OP-010` | Human approval center | `implemented_baseline` | Keep decisions read-only until explicit action command | Evolution review, governance | none |

### Track B -- Core Cognitive Depth

Goal: deepen the reasoning core without replacing it with external frameworks.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `COG-001` | Identity and mission policy by request | `implemented_baseline` | Keep as contract | Planning/governance | none |
| `COG-002` | Mind registry and dominant tension | `implemented_baseline` | More causal use in final decisions | Mind registry | candidate |
| `COG-003` | Domain -> route -> specialist chain | `implemented_baseline` | Expand routes safely | Domain registry | candidate |
| `COG-004` | Metacognitive guidance | `implemented_baseline` | Stronger operator-visible reasoning traces | Planning/synthesis | candidate |
| `COG-005` | Adaptive intervention mid-flow | `implemented_baseline` | More scenario coverage | Observability/evals | candidate |
| `COG-006` | Workflow profile as behavioral policy | `partial_runtime` | Declarative policy per route/workflow | Domain registry | high-priority |
| `COG-007` | Decision memory shaping planning | `partial_runtime` | Evidence-based policy choice | Memory lifecycle | candidate |
| `COG-008` | Conflict handling between active mission and new request | `implemented_baseline` | Keep stable | Mission state | none |
| `COG-009` | Causal route comparison | `missing` | Compare alternative route/plan choices before finalizing | Planning, evals | later |
| `COG-010` | Long-horizon goal reasoning | `minimum_baseline` | Multi-step goal strategy across sessions | Project/objective state | expand after operator validation |

### Track C -- Memory System

Goal: make memory reliable, causal, reviewable and useful over long time.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `MEM-001` | Episodic memory | `implemented_baseline` | Keep stable | Memory service | none |
| `MEM-002` | Mission state persistence | `implemented_baseline` | Keep stable | MissionStateContract | none |
| `MEM-003` | Experience/reflection memory | `implemented_baseline` | Keep stable | Operator Learning Loop | none |
| `MEM-004` | Reviewed-learning guidance memory | `implemented_baseline` | Keep stable | Human review | none |
| `MEM-005` | Semantic memory influence | `partial_runtime` | More causal use with evidence refs | Memory registry | high-priority |
| `MEM-006` | Procedural memory influence | `partial_runtime` | Reusable procedures and playbooks | Memory registry, artifacts | high-priority |
| `MEM-007` | Memory review queue | `minimum_baseline` | Human-reviewable memory maintenance | Observability, console | candidate |
| `MEM-008` | Memory consolidation | `partial_runtime` | Scheduled/manual consolidation with evidence | Memory lifecycle | candidate |
| `MEM-009` | Memory expiration/forgetting | `partial_runtime` | Explicit retention and archival policy | Memory registry | candidate |
| `MEM-010` | Temporal/relational memory | `deferred_by_phase` | Graph/time-aware memory when justified | TA-004, Graphiti/Zep/Mem0 | later |
| `MEM-011` | Organization scope memory | `deferred_by_phase` | Only with sovereign consumer | Governance | later |
| `MEM-012` | Vector/semantic retrieval at scale | `deferred_by_phase` | Only under real retrieval pressure | TA-008, pgvector | later |

### Track D -- Evolution And Learning

Goal: make improvement continuous, measured and governed.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `EVL-001` | Technology candidate contract | `implemented_baseline` | Keep stable | Evolution lab | none |
| `EVL-002` | Post-task reflection proposal | `implemented_baseline` | Keep stable | Memory/evolution lab | none |
| `EVL-003` | Human review decision | `implemented_baseline` | Keep stable | Console/evolution lab | none |
| `EVL-004` | Reviewed-learning guidance | `implemented_baseline` | Keep stable | Review decisions | none |
| `EVL-005` | Baseline vs assisted evals | `implemented_baseline` | Keep stable | Observability/tools | none |
| `EVL-006` | Promotion gate from sandbox to runtime | `implemented_baseline` | Validate with real release candidates | Engineering gate | none |
| `EVL-007` | Skill evolution from repeated patterns | `minimum_baseline` | Reusable skills/playbooks from reviewed evidence | Memory, artifacts | candidate |
| `EVL-008` | Workflow optimization loop | `partial_runtime` | Compare and promote workflow variants manually | Evolution lab | candidate |
| `EVL-009` | Parametric adaptation | `research_only` | Isolated components only | Future V3+ | not now |
| `EVL-010` | Deep self-modification | `research_only` | Research only, no production mutation | Human decision | not now |

### Track E -- Tools, Actions And Operational Substrate

Goal: let JARVIS act safely beyond text generation.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `ACT-001` | Low-risk text artifact production | `implemented_baseline` | Keep stable | Operational service | none |
| `ACT-002` | Capability/tool decision contract | `implemented_baseline` | Keep stable | Planning/governance | none |
| `ACT-003` | Tool authorization and denial reasons | `implemented_baseline` | Keep stable | Governance | none |
| `ACT-004` | Artifact lifecycle and registry | `minimum_baseline` | Durable artifact state, versions and refs | OP-005, memory | expand after metrics |
| `ACT-005` | File operations through governed adapter | `missing` | Safe local file adapter with allowlist and rollback | Governance, artifacts | later |
| `ACT-006` | Browser automation | `deferred_by_phase` | Bounded tool, not core replacement | TA-006 | not now |
| `ACT-007` | Computer use | `deferred_by_phase` | Bounded tool, not autonomy bypass | TA-006 | not now |
| `ACT-008` | Software specialist substrate | `deferred_by_phase` | OpenHands-like subordinate specialist | Specialist governance | later |
| `ACT-009` | Scheduler/long async work | `deferred_by_phase` | Human-approved async queue | Project state, governance | later |
| `ACT-010` | External integrations | `deferred_by_phase` | Per-adapter contracts and scopes | Security/governance | later |

### Track F -- Specialists And Domains

Goal: turn domains into reliable subordinate expertise without fragmenting the
core.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `SPC-001` | Domain registry | `implemented_baseline` | Keep stable | Knowledge curated registry | none |
| `SPC-002` | Specialist registry | `implemented_baseline` | Keep stable | Shared registry | none |
| `SPC-003` | Specialist boundary contract | `implemented_baseline` | Keep stable | Governance | none |
| `SPC-004` | Promoted route eligibility | `implemented_baseline` | Keep stable | Domain registry | none |
| `SPC-005` | Specialist effectiveness metrics | `implemented_baseline` | Keep stable | Observability | none |
| `SPC-006` | New domain onboarding protocol | `minimum_baseline` | Apply protocol and domain evals before each real promotion | Domain registry | later |
| `SPC-007` | Deep specialist state | `partial_runtime` | Per-specialist bounded memory through core | Memory registry | candidate |
| `SPC-008` | Software engineering specialist | `documentation_only` | Subordinate software agent, no identity split | ACT-008 | later |
| `SPC-009` | Research/intelligence specialist | `documentation_only` | Domain-specific retrieval and synthesis | Knowledge, evals | later |
| `SPC-010` | Protective intelligence vertical | `deferred_by_phase` | Separate vertical after core consumer exists | DV-001 | not now |

### Track G -- Knowledge And Research

Goal: keep JARVIS current and useful without uncontrolled ingestion.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `KNW-001` | Curated local corpus | `implemented_baseline` | Keep stable | Knowledge service | none |
| `KNW-002` | Domain registry-backed retrieval | `implemented_baseline` | Keep stable | Domain registry | none |
| `KNW-003` | Knowledge freshness policy | `implemented_baseline` | Temporal validity and review status | Memory/knowledge | none |
| `KNW-004` | Source provenance in answers | `implemented_baseline` | Stronger provenance and evidence refs | Synthesis, knowledge | none |
| `KNW-005` | External research ingestion | `missing` | Governed import queue, no auto-trust | Governance | later |
| `KNW-006` | Technology radar refresh loop | `minimum_baseline` | Scheduled/manual technology review cycle | Tech absorption | candidate |
| `KNW-007` | Domain knowledge packs | `minimum_baseline` | Expand reviewed versioned packs after eval evidence | Domain onboarding | later |
| `KNW-008` | Knowledge conflict resolution | `minimum_baseline` | Compare sources and surface uncertainty | Governance, synthesis | later |

### Track H -- Observability, Evals And Quality

Goal: know whether JARVIS is actually improving.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `OBS-001` | Event trail | `implemented_baseline` | Keep stable | Observability service | none |
| `OBS-002` | Internal pilot | `implemented_baseline` | Keep stable | Tools | none |
| `OBS-003` | Baseline comparison | `implemented_baseline` | Keep stable | compare_orchestrator_paths | none |
| `OBS-004` | Release signal verification | `implemented_baseline` | Keep stable | engineering_gate | none |
| `OBS-005` | Operator usefulness metrics | `minimum_baseline` | Measure daily utility, task completion, saved effort | Operator product loop | expand after long-horizon goals |
| `OBS-006` | Domain-specific eval packs | `minimum_baseline` | Expand packs across promoted routes/domains | Domain onboarding | later |
| `OBS-007` | Regression dashboard | `implemented_baseline` | Compact CLI/report of health over time | Observability/tools | none |
| `OBS-008` | Production-readiness score | `implemented_baseline` | Unified readiness per capability | Gates/docs | none |
| `OBS-009` | Longitudinal learning metrics | `minimum_baseline` | Does learning improve future decisions over weeks? | Memory/evolution | candidate |
| `OBS-010` | Security and misuse metrics | `partial_runtime` | Risk trend and incident evidence | Governance/security | later |

### Track I -- Governance, Security And Sovereignty

Goal: preserve control while increasing autonomy.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `GOV-001` | Risk classification | `implemented_baseline` | Keep stable | Governance service | none |
| `GOV-002` | Allow/condition/block/defer decisions | `implemented_baseline` | Keep stable | Governance service | none |
| `GOV-003` | Human review for evolution | `implemented_baseline` | Keep stable | Evolution lab | none |
| `GOV-004` | Policy for memory mutation | `partial_runtime` | Explicit memory governance by class and risk | Memory registry | candidate |
| `GOV-005` | Tool permission model | `minimum_baseline` | Per-adapter scopes and confirmations | ACT tracks | candidate |
| `GOV-006` | Incident response for documentation/runtime | `minimum_baseline` | Practical incident drills and recovery | Operations docs | later |
| `GOV-007` | Autonomy ladder enforcement | `partial_runtime_enforced` | Runtime-enforced autonomy levels | Mission policy | high-priority |
| `GOV-008` | Secrets and sensitive data policy | `partial_runtime` | Stronger local rules and tests | Security | later |
| `GOV-009` | Release promotion workflow | `implemented_baseline` | Keep human authorization separate from gate evaluation | Evolution, gates | none |
| `GOV-010` | Protective intelligence controls | `deferred_by_phase` | SecurityOS-like vertical only after core readiness | DV-001 | not now |

### Track J -- Surfaces And Interfaces

Goal: expose the same sovereign entity through multiple interfaces.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `SFC-001` | CLI console | `implemented_baseline` | Keep stable | apps/jarvis_console | none |
| `SFC-002` | Mission-cycle console | `implemented_baseline` | Keep stable | Operator loop | none |
| `SFC-003` | Objective console | `implemented_baseline` | Validate practical cockpit through operator pilots | OP track | none |
| `SFC-004` | Evolution review console | `implemented_baseline` | Keep stable | Evolution review | none |
| `SFC-005` | API surface | `missing` | Governed API exposing same core | Surface identity | later |
| `SFC-006` | Web UI | `deferred_by_phase` | Thin operator interface over core | API, security | later |
| `SFC-007` | Voice/realtime | `deferred_by_phase` | Subordinate surface, not new brain | SO-001 | not now |
| `SFC-008` | Mobile/multichannel | `deferred_by_phase` | Same entity across surfaces | Multisurface continuity | later |
| `SFC-009` | Surface identity conflict handling | `minimum_baseline` | Full conflict policy across surfaces | Surface contract | later |
| `SFC-010` | Notification layer | `missing` | Human-approved reminders, not autonomous scheduler | Governance | later |

### Track K -- Documentation And Program Control

Goal: keep planning clear without turning documentation into bureaucracy.

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `DOC-001` | Engineering constitution | `implemented_baseline` | Keep stable | AGENTS/gates | none |
| `DOC-002` | Execution backlog | `implemented_baseline` | Keep stable | This map | none |
| `DOC-003` | Unified gap/absorption backlog | `implemented_baseline` | Feed from this map | Macro planning | candidate |
| `DOC-004` | Adherence snapshot | `implemented_baseline` | Keep synchronized | Documento-Mestre | candidate |
| `DOC-005` | Documentation canonicality audit | `implemented_baseline` | Keep as historical evidence | MB-151 | none |
| `DOC-006` | Backlink map | `implemented_baseline` | Refresh before physical cleanup | MB-152 | none |
| `DOC-007` | Implementation master map | `implemented_baseline` | Primary capability decomposition | MB-154 | none |
| `DOC-008` | Roadmap consolidation | `partial_runtime` | Reduce ambiguity across roadmap docs | Human decision | later |
| `DOC-009` | Architecture-sensitive doc review | `human_decision_required` | Decide future architecture hierarchy | Human decision | later |
| `DOC-010` | Automated doc consistency checks | `implemented_baseline` | More coverage for stale references/status drift | engineering_gate | none |

## 6. Current Highest-Value Gaps

The next functional phase should focus on making the system useful to an
operator, not on adding speculative technology.

Highest-value gaps after `MB-174`:

1. Reprioritize the next queue from operator utility, memory maturity and
   bounded action gaps using measured readiness instead of queue inertia.
2. Preserve the closed onboarding, eval, provenance and readiness baselines
   before expanding domains or surfaces.

## 7. Dependency Map

### Immediate foundation

These are already present and should be preserved:

- sovereign core orchestration;
- canonical contracts and registries;
- mission/objective state;
- experience/reflection/review/guidance loop;
- observability and gates;
- console commands for core operator loop.

### Next functional chain

Recommended chain for the next few implementation slices:

1. Preserve the closed `MB-171` governed domain onboarding protocol.
2. Preserve the closed `MB-172` offline domain eval baseline.
3. Preserve the closed `MB-173` knowledge provenance/freshness baseline.
4. Preserve the closed `MB-174` integrated readiness baseline.

The queue is exhausted after `MB-174`; the next item must be created by an
explicit reprioritization from this map.

Why this order:

- it makes the current core visible and usable;
- it creates real operator data;
- it gives memory/evolution something concrete to improve;
- it avoids premature voice, browser, computer use or broad UI.

### Deferred chain

Only after the operator product loop is useful:

1. richer temporal/relational memory (`TA-004`);
2. governed file/tool adapters;
3. software specialist substrate (`TA-006`);
4. API/web surfaces;
5. voice/realtime;
6. protective intelligence vertical;
7. stronger self-evolution research.

## 8. Phase Model

| Phase | Goal | Allowed | Not allowed |
| --- | --- | --- | --- |
| `v2_core_depth` | Deepen current core and operator usefulness | CLI, memory, objectives, artifacts, evals, review gates | Voice, broad browser/computer use, autonomous scheduler |
| `v2_to_v3_bridge` | Add richer state and controlled adapters | temporal memory, file/tool adapters, API skeleton | High autonomy, core mutation |
| `v3_product_surface` | Expose the same entity across surfaces | web/API/voice if core is stable | parallel brains, identity split |
| `post_v3_research` | Advanced self-evolution | isolated research, parametric components | unsupervised core self-modification |

## 9. Rules For Deriving Micro Backlog Items

Every new micro item must cite:

- one or more IDs from this map;
- the corresponding master-document axis;
- impacted contracts/services;
- expected observable signals;
- local tests and affected end-to-end tests;
- rollback or no-mutation rule;
- explicit out-of-scope list.

No item should enter `ready` only because a technology is attractive.

No item should implement a deferred capability without a phase decision.

## 10. Suggested MB-155 To MB-159 Slice

This lote was opened after explicit operator direction. `MB-155` to `MB-159`
are closed as minimum baselines; no next item is ready without explicit
reprioritization.

### MB-155 -- Operator Daily Dashboard Baseline

Map IDs: `OP-006`, `SFC-003`, `OBS-005`.

Goal: show current missions, active objective, open work items, pending
evolution reviews, latest experience/reflection, reviewed-learning influence
and next operator action in one console command.

Status: closed as minimum baseline through `apps/jarvis_console operator-dashboard`.

### MB-156 -- Governed Work Item Lifecycle

Map IDs: `OP-004`, `COG-010`, `GOV-007`.

Goal: create/update/pause/block/complete work items through governance and
memory, not as loose notes.

Status: closed as minimum baseline through `apps/jarvis_console work-item` and
`apps/jarvis_console work-items`.

### MB-157 -- Artifact Lifecycle Registry

Map IDs: `OP-005`, `ACT-004`, `MEM-006`.

Goal: track living artifacts with refs, versions, status, owner mission,
related objective and rollback/replace metadata.

Status: closed as minimum baseline through `apps/jarvis_console artifact` and
`apps/jarvis_console artifacts`.

### MB-158 -- Operator Usefulness Metrics

Map IDs: `OBS-005`, `OBS-009`, `EVL-005`.

Goal: measure whether the system is helping the operator: resumed work,
closed tasks, reused memory, reduced repeated planning and reviewed-learning
impact.

Status: closed as minimum baseline through `FlowAudit.operator_usefulness_*`
and `apps/jarvis_console operator-dashboard`.

### MB-159 -- Long-Horizon Goal Reasoning

Map IDs: `COG-010`, `MEM-005`, `MEM-006`.

Goal: make objectives span multiple sessions with explicit strategy, milestones,
risks, memory anchors and next-action evolution.

Status: closed as minimum baseline through `LongHorizonGoalStrategyContract`,
`MemoryService.build_long_horizon_goal_strategy()`,
`OrchestratorService.inspect_long_horizon_goal_strategy()`,
`long_horizon_goal_strategy_declared`, synthesis output and
`apps/jarvis_console goal-strategy`.

## 11. Suggested MB-160 To MB-174 Queue

This queue is the next larger implementation line derived from the current
highest-value gaps. It keeps the phase inside `v2_core_depth`: deepen memory,
governance, operator usefulness, release discipline, domain onboarding and
quality signals before opening broad surfaces or autonomous tooling.

Execution rule: only the first technical item should be `ready` at a time in
`execution-backlog.md`. The queue is larger for visibility, not for parallel
WIP.

### MB-160 -- Reprioritize From Implementation Master Map

Map IDs: `DOC-002`, `DOC-003`, `DOC-004`, `DOC-007`.

Goal: convert the post-`MB-159` state into a larger ordered queue without
opening deferred capabilities.

Status: closed as planning/reprioritization documentation.

### MB-161 -- Semantic Memory Evidence Anchors

Map IDs: `MEM-005`, `COG-007`, `OBS-005`.

Goal: make semantic memory influence planning and synthesis with explicit
evidence anchors, relevance reasons and auditable non-use reasons.

Status: closed in `MB-161`; next execution item is `MB-162`.

### MB-162 -- Procedural Memory Playbook Baseline

Map IDs: `MEM-006`, `ACT-004`, `EVL-007`.

Goal: turn repeated procedures, artifacts and reviewed reflections into bounded
playbook candidates without automatic promotion.

Status: closed in `MB-162`; next execution item is `MB-163`.

### MB-163 -- Memory Influence Audit Surface

Map IDs: `MEM-005`, `MEM-006`, `OP-006`, `OBS-005`.

Goal: expose which memories/procedures influenced a mission, why they were
selected and what was ignored.

Status: closed in `MB-163`; next execution item is `MB-164`.

### MB-164 -- Runtime Autonomy Ladder Contract

Map IDs: `GOV-007`, `COG-001`, `ACT-002`.

Goal: make autonomy levels a runtime contract rather than documentation-only
policy.

Status: closed in `MB-164`; next execution item is `MB-165`.

### MB-165 -- Autonomy Enforcement In Governance And Dispatch

Map IDs: `GOV-007`, `GOV-005`, `ACT-002`, `ACT-003`.

Goal: enforce autonomy level limits in governance, operation dispatch and
console-visible decisions.

Status: closed in `MB-165`.

### MB-166 -- Sandbox-To-Release Promotion Checklist

Map IDs: `EVL-006`, `GOV-009`, `DOC-010`.

Goal: define the explicit promotion checklist for reviewed learning and
sandbox candidates, including tests, rollback and release gates.

Status: closed in `MB-166`.

### MB-167 -- Promotion Gate Runtime Enforcement

Map IDs: `EVL-006`, `GOV-009`, `OBS-004`.

Goal: make the promotion checklist executable through evolution/release
services and observable events.

Status: closed in `MB-167`.

### MB-168 -- Operator Cockpit Expansion

Map IDs: `SFC-003`, `OP-003`, `OP-006`, `OP-010`.

Goal: expand the CLI cockpit for objectives, work items, artifacts, reviews,
autonomy state and next operator decisions in one governed view.

Status: closed in `MB-168`.

### MB-169 -- Human-Readable Progress Report

Map IDs: `OP-008`, `OBS-005`, `COG-010`.

Goal: generate a compact mission/project progress report from canonical state,
experience, reflection, artifacts and long-horizon strategy.

Status: closed in `MB-169`; next execution item is `MB-170`.

### MB-170 -- Operator Feedback Loop

Map IDs: `OP-007`, `MEM-003`, `EVL-002`, `OBS-009`.

Goal: capture explicit operator feedback after missions and feed it into
bounded experience/reflection records.

Status: closed in `MB-170`; next execution item is `MB-171`.

### MB-171 -- Domain Onboarding Protocol

Map IDs: `SPC-006`, `KNW-007`, `OBS-006`.

Goal: define the minimum protocol to promote a new domain: registry entry,
knowledge pack, route, specialist, tests and evals.

Status: closed in `MB-171`; candidate assessment is no-mutation and human-review-bound.

### MB-172 -- Domain-Specific Eval Pack Baseline

Map IDs: `OBS-006`, `SPC-006`, `KNW-004`.

Goal: create the first reusable eval pack pattern for promoted routes/domains.

Status: closed in `MB-172`; the analysis pack passes route, response, memory,
specialist and trace checks while remaining `manual_review_only`.

### MB-173 -- Knowledge Provenance And Freshness

Map IDs: `KNW-003`, `KNW-004`, `KNW-008`.

Goal: strengthen source provenance, freshness status and uncertainty/conflict
signals in knowledge-backed answers.

Status: closed in `MB-173`; source, freshness, conflict and uncertainty signals
reach governed synthesis and events without changing request permission.

### MB-174 -- Regression And Readiness Dashboard

Map IDs: `OBS-007`, `OBS-008`, `DOC-010`.

Goal: consolidate capability readiness, regression signals and stale-doc/status
drift into a compact CLI/report.

Status: closed in `MB-174`; capability, gate/test, document and backlog signals
are available in a read-only report and console command.

## 12. Suggested MB-175 To MB-189 Queue

This queue continues inside `v2_core_depth`. It materializes the path already
defined by the Documento Evolutivo:

`experience -> recurring pattern -> skill candidate -> review -> sandbox -> workflow candidate -> eval -> manual gate -> longitudinal measurement`

Execution remains sequential with WIP 1.

### MB-175 -- Reprioritize Governed Skill And Workflow Evolution

Map IDs: `EVL-007`, `MEM-003`, `MEM-006`, `EVL-008`, `OBS-009`.

Status: closed as explicit post-`MB-174` reprioritization; the queue has
advanced through `MB-176`.

### MB-176 -- Recurrent Pattern Evidence Baseline

Map IDs: `EVL-007`, `MEM-003`, `OBS-009`.

Goal: aggregate compatible experiences, reflections and feedback into bounded,
auditable recurring-pattern evidence without creating a skill automatically.

Status: closed in `MB-176`; compatible experience, reflection and feedback
records now produce bounded, read-only pattern evidence.

### MB-177 -- Candidate Skill Registry Contracts

Map IDs: `EVL-007`, `MEM-006`, `GOV-004`.

Goal: define a versioned, inactive and human-review-bound skill candidate.

Status: closed in `MB-177`; the persistent registry enforces inactive,
human-review-bound, immutable logical versions.

### MB-178 -- Bounded Skill Miner

Map IDs: `EVL-007`, `MEM-003`, `MEM-006`.

Goal: convert only eligible recurring-pattern evidence into a skill candidate.

Status: closed in `MB-178`; deterministic eligibility checks return an inactive
candidate or a blocked result with no candidate.

### MB-179 -- Skill Review And Sandbox Eval

Map IDs: `EVL-007`, `EVL-005`, `EVL-006`, `GOV-009`.

Goal: connect skill candidates to human review, sandbox eval and promotion
checklist without runtime activation.

Status: closed in `MB-179`; skill identity and version now cross proposal,
human review, derived sandbox eval, checklist and promotion gate while runtime
activation remains disabled. `MB-180` is the only technical item ready.

### MB-180 -- Skill Operator Surface

Map IDs: `EVL-007`, `OP-010`, `SFC-004`.

Goal: expose pattern, candidate, eval, review, risk and rollback in the console.

Status: ready after `MB-179`.

### MB-181 -- Workflow Profile Version Registry

Map IDs: `COG-006`, `EVL-008`, `DOC-004`.

Goal: version baseline/candidate workflows without mutating the active registry.

### MB-182 -- Workflow Evolution Candidate Builder

Map IDs: `EVL-008`, `COG-006`, `COG-007`.

Goal: derive a workflow variant only from reviewed pattern evidence.

### MB-183 -- Workflow Variant Eval

Map IDs: `EVL-005`, `EVL-008`, `OBS-009`.

Goal: compare workflow baseline and candidate under equivalent offline cases.

### MB-184 -- Workflow Promotion And Rollback Gate

Map IDs: `EVL-006`, `EVL-008`, `GOV-009`.

Goal: reuse human review, release gates and rollback for workflow candidates.

### MB-185 -- Routing Adaptation Evidence

Map IDs: `COG-003`, `COG-007`, `EVL-008`, `OBS-009`.

Goal: measure route/specialist fit and produce reviewable adaptation evidence.

### MB-186 -- Semantic And Procedural Influence Policy Hardening

Map IDs: `MEM-005`, `MEM-006`, `COG-007`, `GOV-004`.

Goal: govern priority, conflict, use and non-use across reviewed memory inputs.

### MB-187 -- Human Memory Review And Consolidation

Map IDs: `MEM-007`, `MEM-008`, `MEM-009`, `GOV-004`.

Goal: expose evidence-bound consolidation/archive/expiration decisions without
an autonomous scheduler.

### MB-188 -- Longitudinal Learning Metrics

Map IDs: `OBS-005`, `OBS-009`, `EVL-005`, `EVL-008`.

Goal: measure sustained utility and regressions by reviewed skill/workflow
version over time.

### MB-189 -- Skill And Workflow Evolution Readiness Closure

Map IDs: `OBS-007`, `OBS-008`, `DOC-010`.

Goal: close the slice with dashboard, regression and documentation evidence.

## 13. What Must Not Be Pulled Next By Inertia

Do not open these without explicit phase decision:

- voice/realtime;
- rich web UI;
- mobile;
- browser automation;
- computer use;
- autonomous scheduler;
- broad external integrations;
- SecurityOS/protective intelligence vertical;
- self-modification;
- model weight changes;
- autonomous promotion of evolution proposals.

## 14. Maintenance Policy

This map should be updated when:

- a capability moves from `missing` to `minimum_baseline`;
- a capability moves from `minimum_baseline` to `implemented_baseline`;
- a deferred capability becomes eligible by phase decision;
- a new technology absorption candidate changes implementation order;
- a micro backlog lote closes and changes the real baseline.

The `execution-backlog.md` should remain the only micro queue. This map should
remain the complete capability decomposition.

## 15. Executive Conclusion

The system is no longer just scattered infrastructure. It has a governed core,
memory, planning, synthesis, observability, evolution lab, console and learning
loop.

The next strategic challenge is product utility: making JARVIS a daily
operator-facing system that can manage missions, objectives, work items,
artifacts and learning over time.

The strongest next direction is therefore:

`operator dashboard -> work item lifecycle -> artifact lifecycle -> usefulness metrics -> long-horizon goal reasoning`

That path increases real utility without violating the sovereign core or
prematurely pulling voice, browser, computer use or strong self-evolution.
