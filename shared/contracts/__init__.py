"""Canonical contracts for JARVIS."""

from dataclasses import dataclass, field

from shared.types import (
    ArtifactId,
    ArtifactStatus,
    ChannelType,
    CreatedAt,
    EvolutionDecisionId,
    EvolutionProposalId,
    GovernanceCheckId,
    GovernanceDecisionId,
    InputType,
    MemoryClass,
    MemoryQueryId,
    MemoryRecordId,
    MissionId,
    MissionStatus,
    OperationId,
    OperationStatus,
    PermissionDecision,
    RecoveryType,
    RequestId,
    RiskLevel,
    SessionId,
    Timestamp,
    TimeWindow,
    UpdatedAt,
)


@dataclass
class InputContract:
    request_id: RequestId
    session_id: SessionId
    channel: ChannelType
    input_type: InputType
    content: str
    timestamp: Timestamp
    mission_id: MissionId | None = None
    user_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    attachments: list[str] = field(default_factory=list)
    locale: str | None = None
    priority_hint: str | None = None


@dataclass
class MemoryRecoveryContract:
    memory_query_id: MemoryQueryId
    recovery_type: RecoveryType
    session_id: SessionId
    requested_scopes: list[MemoryClass]
    context_window: TimeWindow
    mission_id: MissionId | None = None
    user_id: str | None = None
    domain_hints: list[str] = field(default_factory=list)
    priority_rules: list[str] = field(default_factory=list)
    max_items: int | None = None
    sensitivity_ceiling: RiskLevel | None = None


@dataclass
class MemoryRecordContract:
    memory_record_id: MemoryRecordId
    record_type: str
    source_service: str
    payload: dict[str, object]
    timestamp: Timestamp
    session_id: SessionId | None = None
    mission_id: MissionId | None = None
    user_id: str | None = None
    proposed_memory_class: MemoryClass | None = None
    sensitivity_hint: RiskLevel | None = None
    stability_hint: str | None = None
    domain_hint: str | None = None
    promotion_candidate: bool = False


@dataclass
class DeliberativePlanContract:
    plan_summary: str
    goal: str
    steps: list[str]
    active_domains: list[str]
    active_minds: list[str]
    constraints: list[str]
    risks: list[str]
    recommended_task_type: str
    requires_human_validation: bool
    rationale: str
    tensions_considered: list[str] = field(default_factory=list)
    specialist_hints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    specialist_resolution_summary: str | None = None
    dominant_tension: str | None = None
    smallest_safe_next_action: str | None = None
    continuity_action: str | None = None
    open_loops: list[str] = field(default_factory=list)
    continuity_source: str | None = None
    continuity_target_mission_id: MissionId | None = None
    continuity_target_goal: str | None = None


@dataclass
class SpecialistContributionContract:
    specialist_type: str
    role: str
    focus: str
    findings: list[str]
    recommendation: str
    confidence: float


@dataclass
class OperationDispatchContract:
    operation_id: OperationId
    request_id: RequestId
    task_type: str
    task_goal: str
    task_plan: str
    constraints: list[str]
    expected_output: str
    plan_summary: str | None = None
    planned_steps: list[str] = field(default_factory=list)
    plan_risks: list[str] = field(default_factory=list)
    plan_rationale: str | None = None
    specialist_summary: str | None = None
    specialist_findings: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    smallest_safe_next_action: str | None = None
    requires_human_validation: bool = False
    session_id: SessionId | None = None
    mission_id: MissionId | None = None
    risk_hint: RiskLevel | None = None
    domain_hints: list[str] = field(default_factory=list)
    specialist_hints: list[str] = field(default_factory=list)
    tool_hints: list[str] = field(default_factory=list)
    deadline_hint: str | None = None
    priority_hint: str | None = None
    artifact_destination: str | None = None


@dataclass
class OperationResultContract:
    operation_id: OperationId
    status: OperationStatus
    outputs: list[str]
    timestamp: Timestamp
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    next_recommendation: str | None = None
    governance_flags: list[str] = field(default_factory=list)
    memory_record_hints: list[str] = field(default_factory=list)


@dataclass
class GovernanceCheckContract:
    governance_check_id: GovernanceCheckId
    subject_type: str
    subject_action: str
    scope: str
    context: dict[str, object]
    sensitivity: str
    reversibility: str
    mission_id: MissionId | None = None
    session_id: SessionId | None = None
    proposed_effect: str | None = None
    risk_hint: RiskLevel | None = None
    policy_hint: str | None = None
    requested_by_service: str | None = None
    artifact_refs: list[str] = field(default_factory=list)
    declared_risks: list[str] = field(default_factory=list)
    requires_human_validation: bool = False
    decision_frame: str | None = None
    mission_continuity_hint: str | None = None
    open_loops: list[str] = field(default_factory=list)


@dataclass
class GovernanceDecisionContract:
    decision_id: GovernanceDecisionId
    governance_check_id: GovernanceCheckId
    risk_level: RiskLevel
    decision: PermissionDecision
    justification: str
    timestamp: Timestamp
    conditions: list[str] = field(default_factory=list)
    requires_audit: bool = False
    requires_rollback_plan: bool = False
    containment_hint: str | None = None
    policy_refs: list[str] = field(default_factory=list)


@dataclass
class MissionContinuityCandidateContract:
    mission_id: MissionId
    relation_type: str
    mission_goal: str
    continuity_reason: str
    priority_score: float
    confidence_score: float
    open_loops: list[str] = field(default_factory=list)
    semantic_focus: list[str] = field(default_factory=list)
    last_recommendation: str | None = None


@dataclass
class MissionContinuityContextContract:
    active_mission_id: MissionId | None
    active_mission_goal: str | None = None
    active_continuity_brief: str | None = None
    related_candidates: list[MissionContinuityCandidateContract] = field(default_factory=list)
    recommended_action: str | None = None


@dataclass
class MissionStateContract:
    mission_id: MissionId
    mission_goal: str
    mission_status: MissionStatus
    checkpoints: list[str]
    updated_at: UpdatedAt
    created_at: CreatedAt | None = None
    session_origin: str | None = None
    active_tasks: list[str] = field(default_factory=list)
    related_memories: list[str] = field(default_factory=list)
    related_artifacts: list[str] = field(default_factory=list)
    recent_plan_steps: list[str] = field(default_factory=list)
    last_recommendation: str | None = None
    semantic_brief: str | None = None
    semantic_focus: list[str] = field(default_factory=list)
    identity_continuity_brief: str | None = None
    open_loops: list[str] = field(default_factory=list)
    last_decision_frame: str | None = None
    priority_level: str | None = None
    owner_context: str | None = None
    completion_criteria: list[str] = field(default_factory=list)


@dataclass
class ArtifactResultContract:
    artifact_id: ArtifactId
    artifact_type: str
    artifact_status: ArtifactStatus
    produced_by: str
    timestamp: Timestamp
    location_ref: str | None = None
    summary: str | None = None
    format: str | None = None
    mission_id: MissionId | None = None
    request_id: RequestId | None = None
    quality_flags: list[str] = field(default_factory=list)
    related_artifacts: list[str] = field(default_factory=list)


@dataclass
class EvolutionProposalContract:
    evolution_proposal_id: EvolutionProposalId
    proposal_type: str
    target_scope: str
    hypothesis: str
    expected_gain: str
    timestamp: Timestamp
    source_signals: list[str] = field(default_factory=list)
    baseline_refs: list[str] = field(default_factory=list)
    risk_hint: str | None = None
    requires_sandbox: bool = True
    proposed_tests: list[str] = field(default_factory=list)
    promotion_constraints: list[str] = field(default_factory=list)


@dataclass
class EvolutionDecisionContract:
    evolution_decision_id: EvolutionDecisionId
    evolution_proposal_id: EvolutionProposalId
    decision: str
    comparison_summary: str
    timestamp: Timestamp
    promoted_to: str | None = None
    rollback_plan_ref: str | None = None
    governance_refs: list[str] = field(default_factory=list)
    stability_score: float | None = None
    risk_score: float | None = None
    notes: list[str] = field(default_factory=list)
