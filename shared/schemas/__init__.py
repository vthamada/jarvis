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
