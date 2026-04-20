"""Schema metadata for canonical contracts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalSchema:
    """Declarative schema metadata derived from the master document."""

    name: str
    contract_name: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    version: str = "v1"


INPUT_SCHEMA = CanonicalSchema(
    name="InputSchema",
    contract_name="InputContract",
    required_fields=(
        "request_id",
        "session_id",
        "channel",
        "input_type",
        "content",
        "timestamp",
    ),
    optional_fields=(
        "mission_id",
        "user_id",
        "metadata",
        "attachments",
        "locale",
        "priority_hint",
    ),
)

MEMORY_RECOVERY_SCHEMA = CanonicalSchema(
    name="MemoryRecoverySchema",
    contract_name="MemoryRecoveryContract",
    required_fields=(
        "memory_query_id",
        "recovery_type",
        "session_id",
        "requested_scopes",
        "context_window",
    ),
    optional_fields=(
        "mission_id",
        "user_id",
        "domain_hints",
        "priority_rules",
        "max_items",
        "sensitivity_ceiling",
    ),
)

MEMORY_RECORD_SCHEMA = CanonicalSchema(
    name="MemoryRecordSchema",
    contract_name="MemoryRecordContract",
    required_fields=(
        "memory_record_id",
        "record_type",
        "source_service",
        "payload",
        "timestamp",
    ),
    optional_fields=(
        "session_id",
        "mission_id",
        "user_id",
        "proposed_memory_class",
        "sensitivity_hint",
        "stability_hint",
        "domain_hint",
        "promotion_candidate",
    ),
)

GOVERNANCE_CHECK_SCHEMA = CanonicalSchema(
    name="GovernanceCheckSchema",
    contract_name="GovernanceCheckContract",
    required_fields=(
        "governance_check_id",
        "subject_type",
        "subject_action",
        "scope",
        "context",
        "sensitivity",
        "reversibility",
    ),
    optional_fields=(
        "mission_id",
        "session_id",
        "proposed_effect",
        "risk_hint",
        "policy_hint",
        "requested_by_service",
        "artifact_refs",
        "decision_frame",
        "mission_continuity_hint",
        "open_loops",
    ),
)

GOVERNANCE_DECISION_SCHEMA = CanonicalSchema(
    name="GovernanceDecisionSchema",
    contract_name="GovernanceDecisionContract",
    required_fields=(
        "decision_id",
        "governance_check_id",
        "risk_level",
        "decision",
        "justification",
        "timestamp",
    ),
    optional_fields=(
        "conditions",
        "requires_audit",
        "requires_rollback_plan",
        "containment_hint",
        "policy_refs",
    ),
)

OPERATION_DISPATCH_SCHEMA = CanonicalSchema(
    name="OperationDispatchSchema",
    contract_name="OperationDispatchContract",
    required_fields=(
        "operation_id",
        "request_id",
        "task_type",
        "task_goal",
        "task_plan",
        "constraints",
        "expected_output",
    ),
    optional_fields=(
        "session_id",
        "mission_id",
        "risk_hint",
        "domain_hints",
        "tool_hints",
        "deadline_hint",
        "priority_hint",
        "artifact_destination",
        "capability_decision_status",
        "capability_decision_objective",
        "capability_decision_reason",
        "capability_decision_selected_mode",
        "capability_decision_authorization_status",
        "capability_decision_fallback_mode",
        "capability_decision_tool_class",
        "capability_decision_handoff_mode",
        "capability_decision_eligible_capabilities",
        "capability_decision_selected_capabilities",
        "request_identity_status",
        "request_active_mission",
        "request_executive_posture",
        "request_authority_level",
        "request_risk_profile",
        "request_reversibility_mode",
        "request_confirmation_mode",
        "request_identity_summary",
        "request_identity_policy_refs",
        "adaptive_intervention_status",
        "adaptive_intervention_reason",
        "adaptive_intervention_trigger",
        "adaptive_intervention_selected_action",
        "adaptive_intervention_expected_effect",
        "adaptive_intervention_effects",
    ),
)

OPERATION_RESULT_SCHEMA = CanonicalSchema(
    name="OperationResultSchema",
    contract_name="OperationResultContract",
    required_fields=("operation_id", "status", "outputs", "timestamp"),
    optional_fields=(
        "artifacts",
        "errors",
        "checkpoints",
        "next_recommendation",
        "governance_flags",
        "memory_record_hints",
    ),
)

DELIBERATIVE_PLAN_SCHEMA = CanonicalSchema(
    name="DeliberativePlanSchema",
    contract_name="DeliberativePlanContract",
    required_fields=(
        "plan_summary",
        "goal",
        "steps",
        "active_domains",
        "active_minds",
        "constraints",
        "risks",
        "recommended_task_type",
        "rationale",
        "success_criteria",
    ),
    optional_fields=(
        "canonical_domains",
        "primary_canonical_domain",
        "primary_mind",
        "primary_mind_family",
        "primary_domain_driver",
        "arbitration_source",
        "primary_route",
        "mind_domain_specialist_contract_status",
        "mind_domain_specialist_contract_summary",
        "mind_domain_specialist_contract_chain",
        "mind_domain_specialist_active_specialist",
        "mind_domain_specialist_override_mode",
        "mind_domain_specialist_fallback_mode",
        "route_consumer_profile",
        "route_consumer_objective",
        "route_expected_deliverables",
        "route_telemetry_focus",
        "route_workflow_profile",
        "route_workflow_steps",
        "route_workflow_checkpoints",
        "route_workflow_decision_points",
        "tensions_considered",
        "specialist_hints",
        "specialist_resolution_summary",
        "dominant_tension",
        "smallest_safe_next_action",
        "metacognitive_guidance_applied",
        "metacognitive_guidance_summary",
        "metacognitive_effects",
        "metacognitive_containment_recommendation",
        "semantic_memory_source",
        "procedural_memory_source",
        "semantic_memory_effects",
        "procedural_memory_effects",
        "semantic_memory_lifecycle",
        "procedural_memory_lifecycle",
        "semantic_memory_state",
        "procedural_memory_state",
        "memory_lifecycle_status",
        "memory_review_status",
        "memory_maintenance_status",
        "memory_maintenance_reason",
        "memory_maintenance_fallback_mode",
        "context_compaction_status",
        "cross_session_recall_status",
        "memory_consolidation_status",
        "memory_fixation_status",
        "memory_archive_status",
        "procedural_artifact_status",
        "procedural_artifact_ref",
        "procedural_artifact_version",
        "procedural_artifact_summary",
        "mind_disagreement_status",
        "mind_validation_checkpoints",
        "capability_decision_status",
        "capability_decision_objective",
        "capability_decision_reason",
        "capability_decision_selected_mode",
        "capability_decision_authorization_status",
        "capability_decision_fallback_mode",
        "capability_decision_tool_class",
        "capability_decision_handoff_mode",
        "capability_decision_eligible_capabilities",
        "capability_decision_selected_capabilities",
        "request_identity_status",
        "request_active_mission",
        "request_executive_posture",
        "request_authority_level",
        "request_risk_profile",
        "request_reversibility_mode",
        "request_confirmation_mode",
        "request_identity_summary",
        "request_identity_policy_refs",
        "adaptive_intervention_status",
        "adaptive_intervention_reason",
        "adaptive_intervention_trigger",
        "adaptive_intervention_selected_action",
        "adaptive_intervention_expected_effect",
        "adaptive_intervention_effects",
        "cognitive_strategy_shift_applied",
        "cognitive_strategy_shift_summary",
        "cognitive_strategy_shift_trigger",
        "cognitive_strategy_shift_effects",
        "continuity_action",
        "continuity_reason",
        "open_loops",
        "continuity_source",
        "continuity_target_mission_id",
        "continuity_target_goal",
        "continuity_replay_status",
        "continuity_recovery_mode",
        "continuity_resume_point",
        "contract_validation_status",
        "contract_validation_errors",
        "contract_validation_retry_applied",
    ),
)

MISSION_STATE_SCHEMA = CanonicalSchema(
    name="MissionStateSchema",
    contract_name="MissionStateContract",
    required_fields=(
        "mission_id",
        "mission_goal",
        "mission_status",
        "checkpoints",
        "updated_at",
    ),
    optional_fields=(
        "created_at",
        "session_origin",
        "active_tasks",
        "related_memories",
        "related_artifacts",
        "semantic_brief",
        "semantic_focus",
        "identity_continuity_brief",
        "open_loops",
        "last_decision_frame",
        "priority_level",
        "owner_context",
        "completion_criteria",
    ),
)

ARTIFACT_RESULT_SCHEMA = CanonicalSchema(
    name="ArtifactResultSchema",
    contract_name="ArtifactResultContract",
    required_fields=(
        "artifact_id",
        "artifact_type",
        "artifact_status",
        "produced_by",
        "timestamp",
    ),
    optional_fields=(
        "location_ref",
        "summary",
        "format",
        "mission_id",
        "request_id",
        "quality_flags",
        "related_artifacts",
    ),
)

EVOLUTION_PROPOSAL_SCHEMA = CanonicalSchema(
    name="EvolutionProposalSchema",
    contract_name="EvolutionProposalContract",
    required_fields=(
        "evolution_proposal_id",
        "proposal_type",
        "target_scope",
        "hypothesis",
        "expected_gain",
        "timestamp",
    ),
    optional_fields=(
        "source_signals",
        "baseline_refs",
        "risk_hint",
        "requires_sandbox",
        "proposed_tests",
        "promotion_constraints",
    ),
)

EVOLUTION_DECISION_SCHEMA = CanonicalSchema(
    name="EvolutionDecisionSchema",
    contract_name="EvolutionDecisionContract",
    required_fields=(
        "evolution_decision_id",
        "evolution_proposal_id",
        "decision",
        "comparison_summary",
        "timestamp",
    ),
    optional_fields=(
        "promoted_to",
        "rollback_plan_ref",
        "governance_refs",
        "stability_score",
        "risk_score",
        "notes",
    ),
)

VOICE_SESSION_START_SCHEMA = CanonicalSchema(
    name="VoiceSessionStartSchema",
    contract_name="VoiceSessionStartContract",
    required_fields=(),
    optional_fields=(),
    notes=(
        "Placeholder canonical schema until field-level voice contracts are formalized in code.",
    ),
)

VOICE_TURN_SCHEMA = CanonicalSchema(
    name="VoiceTurnSchema",
    contract_name="VoiceTurnContract",
    required_fields=(),
    optional_fields=(),
    notes=(
        "Placeholder canonical schema until field-level voice contracts are formalized in code.",
    ),
)

VOICE_RESPONSE_SCHEMA = CanonicalSchema(
    name="VoiceResponseSchema",
    contract_name="VoiceResponseContract",
    required_fields=(),
    optional_fields=(),
    notes=(
        "Placeholder canonical schema until field-level voice contracts are formalized in code.",
    ),
)
