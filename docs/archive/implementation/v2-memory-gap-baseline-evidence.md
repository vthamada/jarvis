# V2 Memory Gap Baseline Evidence

- cut: `v2-memory-gap-evidence-cut`
- sprint: `sprint-2-baseline-evidence-collection`
- scope_count: `6`
- overall_decision: `hold_mem0_as_conditional_candidate`

## Summary

- implemented scopes: `3`
- typed tracking only scopes: `1`
- core mediated handoff only scopes: `1`
- future shape only scopes: `1`
- inconsistent scopes: `0`

## conversation scope is already operational in the baseline

- scope_id: `conversation_scope`
- status: `implemented`
- gap_read: `baseline_sufficient_now`
- baseline_read:
  - the baseline already persists raw interaction turns and a derived session summary
  - this scope is not the current source of a multilayer memory gap
- rule_evidence:
  - `interaction_turns_table` from `repository`: expected `present`, found `present`; conversation turns are persisted as the lowest baseline memory trace
  - `context_summary_table` from `repository`: expected `present`, found `present`; conversation scope is compacted into a session summary
  - `record_turn_entrypoint` from `service`: expected `present`, found `present`; memory-service records conversation turns through a canonical entrypoint

## session scope is operational and recoverable

- scope_id: `session_scope`
- status: `implemented`
- gap_read: `baseline_sufficient_now`
- baseline_read:
  - session scope already exceeds plain chat history because it has continuity, replay and pause resolution
  - there is no evidence here of a missing multilayer capability for the current cut
- rule_evidence:
  - `session_continuity_table` from `repository`: expected `present`, found `present`; session continuity is persisted as its own scope
  - `continuity_checkpoint_table` from `repository`: expected `present`, found `present`; session replay and governed resume are checkpointed
  - `session_replay_entrypoint` from `service`: expected `present`, found `present`; the runtime can recover session continuity explicitly

## mission scope is operational and richer than simple session state

- scope_id: `mission_scope`
- status: `implemented`
- gap_read: `baseline_sufficient_now`
- baseline_read:
  - mission scope is already treated as a first-class continuity artifact
  - the current gap is not that mission memory is absent, but whether richer cross-scope escalation is needed
- rule_evidence:
  - `mission_state_contract` from `contracts`: expected `present`, found `present`; mission state has an explicit canonical contract
  - `mission_state_table` from `repository`: expected `present`, found `present`; mission state is persisted independently from session context
  - `mission_state_entrypoint` from `service`: expected `present`, found `present`; the runtime exposes mission continuity as a recoverable object

## user scope is typed and tracked, but not yet runtime rich

- scope_id: `user_scope`
- status: `typed_tracking_only`
- gap_read: `partial_gap_supported`
- baseline_read:
  - the baseline can track who the user is, but it does not yet recover a richer user scope comparable to session or mission continuity
  - this supports the hypothesis that user scope is typed but not yet operationally rich
- rule_evidence:
  - `input_contract_user_id` from `contracts`: expected `present`, found `present`; user identity is part of the canonical contracts
  - `interaction_turns_user_id` from `repository`: expected `present`, found `present`; user_id is persisted in the low-level interaction history
  - `dedicated_user_memory_contract_absent` from `contracts`: expected `absent`, found `absent`; there is still no dedicated user memory contract above ids and turn history
  - `dedicated_user_memory_entrypoint_absent` from `service`: expected `absent`, found `absent`; memory-service still has no dedicated runtime entrypoint for user memory
- supports_hypotheses:
  - `user_scope_is_typed_but_not_runtime_rich`

## specialist shared memory covers handoff, but not a stronger agent scope

- scope_id: `specialist_shared_scope`
- status: `core_mediated_handoff_only`
- gap_read: `partial_gap_supported`
- baseline_read:
  - the current baseline is good at guided handoff, not at proving a richer long-lived agent scope
  - this supports the hypothesis that shared specialist memory is not the same thing as a stronger agent scope
- rule_evidence:
  - `specialist_shared_contract` from `contracts`: expected `present`, found `present`; specialist-facing shared memory is formally modeled
  - `specialist_shared_table` from `repository`: expected `present`, found `present`; shared memory is persisted per session and specialist
  - `specialist_shared_entrypoint` from `service`: expected `present`, found `present`; the runtime can assemble and persist core-mediated specialist memory packets
  - `stronger_agent_scope_absent` from `service`: expected `absent`, found `absent`; the baseline still does not expose a stronger persistent scope per agent or participant
- supports_hypotheses:
  - `shared_memory_does_not_equal_agent_scope`

## organization scope is still only a future shape

- scope_id: `organization_scope`
- status: `future_shape_only`
- gap_read: `not_proven_gap`
- baseline_read:
  - organization scope is absent, but the absence is not yet a proven failure of the runtime
  - for the current baseline this remains a future shape, not a reopen-ready gap
- rule_evidence:
  - `organization_contract_absent` from `contracts`: expected `absent`, found `absent`; there is no organization-level identifier in the current canonical contracts
  - `organization_memory_class_absent` from `registry`: expected `absent`, found `absent`; memory registry does not currently expose organization scope as a canonical runtime class
  - `organization_runtime_entrypoint_absent` from `service`: expected `absent`, found `absent`; memory-service has no organization memory entrypoint because no canonical consumer depends on it yet
- supports_hypotheses:
  - `organization_scope_is_still_only_a_future_shape`

## Hypothesis Read

### organization_scope_is_still_only_a_future_shape

- evidence_state: `not_yet_proven`
- supporting_scopes:
  - `organization_scope`

### shared_memory_does_not_equal_agent_scope

- evidence_state: `supported_by_baseline_read`
- supporting_scopes:
  - `specialist_shared_scope`

### user_scope_is_typed_but_not_runtime_rich

- evidence_state: `supported_by_baseline_read`
- supporting_scopes:
  - `user_scope`

## Current Read

- conversation, session and mission scopes are already operational in the baseline;
- user scope is typed and tracked, but still not runtime rich enough to count as a stronger layer;
- specialist shared memory is strong for handoff, but it still does not prove a stronger persistent agent scope;
- organization scope remains a future shape and is not yet a proven baseline failure;
- the current read supports `Mem0` staying as `absorver_depois`, not as a reopen-ready dependency.

