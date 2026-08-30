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

WORKFLOW_VARIANT_EVAL_METRICS = (
    "success_score",
    "contract_adherence",
    "rework_rate",
    "checkpoint_coverage",
    "memory_causality",
)
WORKFLOW_VARIANT_EVAL_COMPARISON_MODE = "controlled_paired_offline"
WORKFLOW_VARIANT_EVAL_METRICS_SOURCE = "derived_from_paired_observations"

TECHNOLOGY_EXPERIMENT_METRICS = (
    "success_score",
    "contract_adherence",
    "isolation_compliance",
    "sovereign_consumer_preservation",
    "rework_rate",
)
TECHNOLOGY_EXPERIMENT_COMPARISON_MODE = "controlled_paired_offline_attestation"
TECHNOLOGY_EXPERIMENT_METRICS_SOURCE = "derived_from_paired_observations"
TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE = "technology-isolation://offline-paired-attestation/v1"

WORK_ITEM_PRIORITY_LEVELS = ("p0", "p1", "p2", "p3")
ARTIFACT_LIFECYCLE_STATUSES = (
    "active",
    "archived",
    "superseded",
    "rolled_back",
)
ARTIFACT_PHYSICAL_SAGA_PURPOSES = ("apply", "rollback")
ARTIFACT_PHYSICAL_APPLY_PHASES = (
    "reserved",
    "effect_dispatched",
    "physical_applied",
    "canonical_committed",
    "completed",
    "failed",
    "reconciliation_required",
    "compensation_required",
    "compensated",
)
ARTIFACT_PHYSICAL_ROLLBACK_PHASES = (
    "rollback_reserved",
    "rollback_effect_dispatched",
    "physically_rolled_back",
    "canonical_rolled_back",
    "compensation_committed",
    "completed",
    "failed",
    "reconciliation_required",
)

DECISION_ATTRIBUTION_STATUSES = (
    "correlation_only",
    "declared_causality",
    "insufficient_evidence",
)
DECISION_ATTRIBUTION_CAUSALITY_SCOPE = "runtime_declared_participation_only"
DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS = "not_established_without_comparator"


@dataclass
class SurfaceIdentityContract:
    surface_id: str
    surface_kind: str
    surface_session_id: str
    surface_capability_scope: list[str] = field(default_factory=list)
    operator_identity_ref: str | None = None
    canonical_user_ref: str | None = None
    surface_continuity_status: str = "single_surface"


@dataclass
class ProjectObjectiveContinuityContract:
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str = "active"
    next_action_ref: str | None = None


@dataclass
class WorkItemStateContract:
    work_item_ref: str
    work_item_status: str
    mission_id: MissionId
    transition: str | None = None
    next_action_ref: str | None = None
    dependency_refs: list[str] = field(default_factory=list)
    priority_level: str = "p2"
    blocking_state: str = "ready"
    blocker_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    memory_write_mode: str = "through_core_only"


@dataclass
class WorkItemQueueContract:
    mission_id: MissionId
    queue_status: str
    ordered_work_items: list[WorkItemStateContract]
    executable_work_item_refs: list[str]
    blocked_work_item_refs: list[str]
    completed_work_item_refs: list[str]
    evidence_refs: list[str] = field(default_factory=list)
    ordering_policy: str = "dependency_topology_then_priority_p0_to_p3_then_ref"
    memory_write_mode: str = "read_only"
    read_only: bool = True
    autonomous_execution_allowed: bool = False


@dataclass
class ArtifactLifecycleStateContract:
    artifact_ref: str
    artifact_status: str
    mission_id: MissionId
    transition: str | None = None
    artifact_version: int | None = None
    owner_mission_id: MissionId | None = None
    objective_ref: str | None = None
    work_item_ref: str | None = None
    lineage_root_ref: str | None = None
    supersedes_artifact_ref: str | None = None
    replacement_artifact_ref: str | None = None
    rollback_plan_ref: str | None = None
    physical_version_fingerprint: str | None = None
    mutation_receipt_fingerprint: str | None = None
    canonical_saga_id: str | None = None
    physical_resource_ref: str | None = None
    physical_state_attestation_fingerprint: str | None = None
    physical_consistency_status: str | None = None
    created_at: CreatedAt | None = None
    updated_at: UpdatedAt | None = None
    checkpoint_refs: list[str] = field(default_factory=list)
    memory_write_mode: str = "through_core_only"


@dataclass
class ArtifactRegistryContract:
    mission_id: MissionId
    registry_status: str
    artifact_states: list[ArtifactLifecycleStateContract]
    active_artifact_refs: list[str]
    archived_artifact_refs: list[str]
    superseded_artifact_refs: list[str]
    rolled_back_artifact_refs: list[str]
    evidence_refs: list[str] = field(default_factory=list)
    ordering_policy: str = "lineage_root_then_version_then_ref"
    memory_write_mode: str = "read_only"
    read_only: bool = True
    external_file_mutation_allowed: bool = False


@dataclass(frozen=True)
class ArtifactPhysicalApplyPlanContract:
    """Content-free immutable reservation for one canonical physical version apply."""

    saga_id: str
    mission_id: MissionId
    artifact_ref: str
    artifact_version: int
    owner_mission_id: MissionId
    objective_ref: str | None
    work_item_ref: str
    lineage_root_ref: str
    supersedes_artifact_ref: str | None
    transition: str
    physical_operation_id: str
    resource_ref: str
    root_alias: str
    preflight_fingerprint: str
    root_config_fingerprint: str
    preflight_policy_version: str
    transaction_policy_version: str
    transaction_backend_version: str
    adapter_backend_version: str
    before_content_sha256: str
    desired_content_sha256: str
    rollback_plan_ref: str
    expected_lineage_revision: int
    created_at: CreatedAt
    plan_fingerprint: str
    purpose: str = "apply"
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalRollbackPlanContract:
    """Content-free immutable reservation for one separately authorized rollback."""

    saga_id: str
    mission_id: MissionId
    active_artifact_ref: str
    active_artifact_version: int
    restored_artifact_ref: str | None
    restored_artifact_version: int | None
    owner_mission_id: MissionId
    objective_ref: str | None
    work_item_ref: str
    lineage_root_ref: str
    physical_operation_id: str
    mutation_operation_id: str
    source_apply_saga_id: str
    rollback_mode: str
    canonical_effect_expected: bool
    mutation_receipt_fingerprint: str
    resource_ref: str
    root_alias: str
    expected_current_sha256: str
    restored_content_sha256: str
    expected_lineage_revision: int
    created_at: CreatedAt
    plan_fingerprint: str
    purpose: str = "rollback"
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalSagaEventContract:
    """One content-free append-only and hash-chained saga checkpoint."""

    event_id: str
    saga_id: str
    purpose: str
    phase: str
    sequence: int
    plan_fingerprint: str
    physical_operation_id: str
    occurred_at: Timestamp
    previous_event_fingerprint: str | None
    mutation_receipt_fingerprint: str | None
    rollback_receipt_fingerprint: str | None
    physical_state_attestation_fingerprint: str | None
    event_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalSagaStateContract:
    """Read-only projection of the latest verified saga checkpoint."""

    saga_id: str
    purpose: str
    mission_id: MissionId
    physical_operation_id: str
    plan_fingerprint: str
    phase: str
    latest_sequence: int
    latest_event_fingerprint: str
    mutation_receipt_fingerprint: str | None
    rollback_receipt_fingerprint: str | None
    physical_state_attestation_fingerprint: str | None
    updated_at: UpdatedAt
    state_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class PhysicalArtifactVersionContract:
    """Immutable physical binding for one canonical artifact version."""

    mission_id: MissionId
    artifact_ref: str
    artifact_version: int
    owner_mission_id: MissionId
    objective_ref: str | None
    work_item_ref: str
    lineage_root_ref: str
    supersedes_artifact_ref: str | None
    physical_operation_id: str
    mutation_receipt_fingerprint: str
    resource_ref: str
    root_alias: str
    preflight_fingerprint: str
    root_config_fingerprint: str
    preflight_policy_version: str
    transaction_policy_version: str
    transaction_backend_version: str
    adapter_backend_version: str
    before_content_sha256: str
    desired_content_sha256: str
    rollback_plan_ref: str
    physical_state_attestation_fingerprint: str
    canonical_saga_id: str
    canonicalized_at: Timestamp
    version_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalLineageContract:
    """CAS-protected active head for one normalized physical artifact lineage."""

    mission_id: MissionId
    lineage_root_ref: str
    revision: int
    active_artifact_ref: str
    last_saga_id: str
    last_event_fingerprint: str
    updated_at: UpdatedAt
    lineage_fingerprint: str
    read_only: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalOutboxItemContract:
    """Immutable content-free publication item created with the canonical commit."""

    outbox_id: str
    saga_id: str
    purpose: str
    event_name: str
    mission_id: MissionId
    artifact_ref: str
    lineage_root_ref: str
    canonical_event_fingerprint: str
    created_at: CreatedAt
    outbox_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalOutboxDeliveryContract:
    """Append-only proof that one canonical outbox item was published."""

    delivery_id: str
    outbox_id: str
    publisher_ref: str
    published_at: Timestamp
    delivery_fingerprint: str
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class ArtifactPhysicalCanonicalCommitReceiptContract:
    """Content-free proof that Memory atomically committed one canonical saga step."""

    commit_id: str
    purpose: str
    saga_id: str
    plan_fingerprint: str
    mission_id: MissionId
    artifact_ref: str | None
    artifact_version: int | None
    lineage_root_ref: str
    lineage_revision: int
    physical_operation_id: str
    resource_ref: str
    root_alias: str
    mutation_receipt_fingerprint: str
    rollback_receipt_fingerprint: str | None
    physical_state_attestation_fingerprint: str
    canonical_event_fingerprint: str
    committed_at: Timestamp
    commit_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass(frozen=True)
class LocalTextPhysicalStateAttestationContract:
    """Fresh content-free handle-safe observation bound to a physical receipt."""

    attestation_id: str
    purpose: str
    receipt_fingerprint: str
    mutation_operation_id: str
    rollback_operation_id: str | None
    resource_ref: str
    root_alias: str
    root_config_fingerprint: str
    physical_state: str
    observed_content_sha256: str
    observed_identity_fingerprint: str
    journal_event_fingerprint: str
    transaction_policy_version: str
    transaction_backend_version: str
    verified_at: Timestamp
    attestation_fingerprint: str
    contains_content: bool = False
    read_only: bool = True
    immutable: bool = True


@dataclass
class OpenLoopStateContract:
    open_loop_ref: str
    mission_id: MissionId
    loop_summary: str
    loop_status: str = "open"
    source_work_item_ref: str | None = None
    selected_at: Timestamp | None = None
    resumed_at: Timestamp | None = None
    next_action_ref: str | None = None
    next_action_summary: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    memory_write_mode: str = "through_core_only"


@dataclass
class OpenLoopRegistryContract:
    mission_id: MissionId
    registry_status: str
    freshness_status: str
    mission_age_hours: float | None
    open_loop_states: list[OpenLoopStateContract]
    eligible_open_loop_refs: list[str]
    blocked_open_loop_refs: list[str]
    blocking_reasons: dict[str, list[str]] = field(default_factory=dict)
    selected_work_item_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    generated_at: Timestamp | None = None
    memory_write_mode: str = "read_only"
    read_only: bool = True
    autonomous_resume_allowed: bool = False
    autonomous_scheduling_allowed: bool = False


@dataclass
class OpenLoopResumePlanContract:
    mission_id: MissionId
    open_loop_ref: str
    loop_summary: str
    next_action_ref: str
    next_action_summary: str
    selected_work_item_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    planning_mode: str = "bounded_open_loop_resume"
    generated_at: Timestamp | None = None
    autonomous_execution_allowed: bool = False


@dataclass
class TechnologyAbsorptionCandidateContract:
    candidate_ref: str
    technology_name: str
    absorption_class: str
    target_gap_refs: list[str]
    hypothesis: str
    expected_gain: str
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    risk_hint: str | None = None
    status: str = "candidate"
    decision: str = "hold_in_lane"
    requested_core_role: str = "subordinate"
    sandbox_required: bool = True
    human_review_required: bool = True
    rollback_plan_ref: str | None = None
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TechnologyRadarIntakeContract:
    """Reviewed external reference that has no runtime or promotion authority."""

    intake_id: str
    candidate_ref: str
    intake_version: str
    technology_name: str
    source_kind: str
    source_locator: str
    source_version_ref: str
    source_content_sha256: str
    license_id: str
    license_status: str
    license_evidence_ref: str
    retrieved_at: Timestamp
    claims: list[str]
    risks: list[str]
    absorption_class: str
    target_gap_refs: list[str]
    research_approval_ref: str
    reviewed_payload_fingerprint: str
    reviewer_ref: str
    review_status: str
    review_evidence_refs: list[str]
    reviewed_at: Timestamp
    recorded_at: Timestamp
    previous_intake_id: str | None = None
    previous_intake_fingerprint: str | None = None
    source_trust_status: str = "operator_attested_untrusted_reference"
    intake_status: str = "reviewed_reference"
    read_only: bool = True
    immutable: bool = True
    human_review_required: bool = True
    network_fetch_allowed: bool = False
    knowledge_ingestion_allowed: bool = False
    dependency_installation_allowed: bool = False
    execution_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentControlSnapshotContract:
    """Deterministic, offline controls shared by both experiment arms."""

    control_snapshot_id: str
    input_fingerprint: str
    sandbox_policy_ref: str
    sandbox_policy_version: str
    evaluator_version: str
    deterministic_seed: int
    fixed_clock: Timestamp
    isolation_profile_ref: str
    isolation_fingerprint: str
    environment_fingerprint: str
    offline_only: bool = True
    sandbox_only: bool = True
    read_only: bool = True
    network_fetch_allowed: bool = False
    subprocess_allowed: bool = False
    dependency_installation_allowed: bool = False
    external_code_execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    host_filesystem_write_allowed: bool = False
    knowledge_ingestion_allowed: bool = False
    memory_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    registry_write_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentObservationContract:
    """Pre-produced inert observation; never an executable experiment request."""

    observation_id: str
    experiment_pack_id: str
    pack_version: str
    case_id: str
    case_version: str
    arm: str
    definition_ref: str
    definition_hash: str
    input_fingerprint: str
    control_snapshot_id: str
    control_snapshot_fingerprint: str
    outcome_ref: str
    outcome_status: str
    contract_checks: dict[str, bool]
    isolation_checks: dict[str, bool]
    success_criteria_results: dict[str, bool]
    action_count: int
    rework_count: int
    evidence_refs: list[str]
    limitations: list[str]
    observed_at: Timestamp
    source_mode: str = "preproduced_sandbox_attestation"
    offline_only: bool = True
    sandbox_only: bool = True
    read_only: bool = True
    network_fetch_allowed: bool = False
    subprocess_allowed: bool = False
    dependency_installation_allowed: bool = False
    external_code_execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    host_filesystem_write_allowed: bool = False
    knowledge_ingestion_allowed: bool = False
    memory_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    registry_write_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentCaseContract:
    """One controlled comparison over identical input and isolation controls."""

    experiment_pack_id: str
    pack_version: str
    case_id: str
    case_version: str
    scenario_ref: str
    input_fingerprint: str
    baseline_definition_ref: str
    baseline_definition_hash: str
    candidate_definition_ref: str
    candidate_definition_hash: str
    critical_contract_check_refs: list[str]
    critical_isolation_check_refs: list[str]
    success_criteria_refs: list[str]
    control_snapshot: TechnologyExperimentControlSnapshotContract
    baseline_observation: TechnologyExperimentObservationContract
    candidate_observation: TechnologyExperimentObservationContract
    evidence_refs: list[str]
    limitations: list[str] = field(default_factory=list)
    comparison_mode: str = TECHNOLOGY_EXPERIMENT_COMPARISON_MODE
    metrics_source: str = TECHNOLOGY_EXPERIMENT_METRICS_SOURCE
    offline_only: bool = True
    sandbox_only: bool = True
    read_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentPackContract:
    """Immutable translation of one reviewed reference into an inert sandbox pack."""

    experiment_pack_id: str
    pack_version: str
    intake_id: str
    intake_version: str
    intake_fingerprint: str
    reviewed_payload_fingerprint: str
    candidate_ref: str
    technology_name: str
    source_content_sha256: str
    absorption_class: str
    translation_kind: str
    pattern_id: str
    pattern_name: str
    pattern_summary: str
    selected_claim_fingerprints: list[str]
    selected_risk_fingerprints: list[str]
    hypothesis: str
    expected_gain: str
    sovereign_consumer_kind: str
    sovereign_consumer_ref: str
    consumer_contract_ref: str
    bounded_integration_seam: str
    target_gap_refs: list[str]
    baseline_definition_ref: str
    baseline_definition_hash: str
    candidate_definition_ref: str
    candidate_definition_hash: str
    isolation_profile_ref: str
    risk_control_refs: list[str]
    mitigation_refs: list[str]
    stop_condition_refs: list[str]
    license_id: str
    license_status: str
    license_evidence_ref: str
    rollback_plan_ref: str
    rollback_steps: list[str]
    rollback_verification_refs: list[str]
    selection_review_ref: str
    selected_by_ref: str
    cases: list[TechnologyExperimentCaseContract]
    required_pass_rate: float
    evidence_refs: list[str]
    generated_at: Timestamp
    pack_status: str = "sandbox_ready"
    source_mode: str = "registered_intake_only"
    external_framework_role: str = "subordinate_reference"
    requested_core_role: str = "subordinate"
    sandbox_only: bool = True
    read_only: bool = True
    immutable: bool = True
    human_review_required: bool = True
    network_fetch_allowed: bool = False
    subprocess_allowed: bool = False
    dependency_installation_allowed: bool = False
    external_code_execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    host_filesystem_write_allowed: bool = False
    knowledge_ingestion_allowed: bool = False
    memory_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    registry_write_allowed: bool = False
    evolution_proposal_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentCaseResultContract:
    """Canonical comparison derived from one paired case."""

    experiment_pack_id: str
    pack_version: str
    pack_fingerprint: str
    case_id: str
    case_version: str
    scenario_ref: str
    input_fingerprint: str
    control_snapshot_id: str
    control_snapshot_fingerprint: str
    baseline_outcome_ref: str
    baseline_outcome_status: str
    candidate_outcome_ref: str
    candidate_outcome_status: str
    passed: bool
    checks: dict[str, bool]
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    metric_deltas: dict[str, float]
    improvement_signals: list[str]
    regression_flags: list[str]
    failures: list[str]
    limitations: list[str]
    evidence_refs: list[str]
    comparison_mode: str = TECHNOLOGY_EXPERIMENT_COMPARISON_MODE
    metrics_source: str = TECHNOLOGY_EXPERIMENT_METRICS_SOURCE
    offline_only: bool = True
    sandbox_only: bool = True
    read_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass(frozen=True)
class TechnologyExperimentEvalRunClaimContract:
    """Atomic reservation of one pack/input/control evaluation identity."""

    run_id: str
    experiment_pack_id: str
    pack_version: str
    pack_fingerprint: str
    intake_id: str
    intake_fingerprint: str
    input_fingerprint: str
    control_fingerprint: str
    claimed_at: Timestamp


@dataclass(frozen=True)
class TechnologyExperimentEvalRunContract:
    """Append-only aggregate derived from a verified experiment pack."""

    run_id: str
    experiment_pack_id: str
    pack_version: str
    pack_fingerprint: str
    intake_id: str
    intake_version: str
    intake_fingerprint: str
    candidate_ref: str
    pattern_id: str
    sovereign_consumer_ref: str
    input_fingerprint: str
    control_fingerprint: str
    status: str
    readiness_status: str
    promotion_readiness: str
    comparison_conclusion: str
    pass_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    aggregate_baseline_metrics: dict[str, float]
    aggregate_candidate_metrics: dict[str, float]
    aggregate_metric_deltas: dict[str, float]
    case_results: list[TechnologyExperimentCaseResultContract]
    regression_flags: list[str]
    limitations: list[str]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    comparison_mode: str = TECHNOLOGY_EXPERIMENT_COMPARISON_MODE
    metrics_source: str = TECHNOLOGY_EXPERIMENT_METRICS_SOURCE
    offline_only: bool = True
    sandbox_only: bool = True
    read_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    priority_mutation_allowed: bool = False


@dataclass
class ExperienceRecordContract:
    experience_id: str
    mission_id: MissionId
    workflow_profile: str
    outcome_status: str
    timestamp: Timestamp
    user_intent: str | None = None
    route: str | None = None
    primary_mind: str | None = None
    primary_domain_driver: str | None = None
    specialist_used: list[str] = field(default_factory=list)
    plan_summary: str | None = None
    execution_summary: str | None = None
    outcome: str | None = None
    errors: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    user_feedback: str | None = None
    objective_ref: str | None = None
    surface_id: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    signal_refs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    decision_refs: list[str] = field(default_factory=list)
    learned_patterns: list[str] = field(default_factory=list)
    next_action_ref: str | None = None
    source_kind: str = "post_task_runtime"
    reusable_memory_status: str = "bounded"
    human_review_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class PostTaskReflectionContract:
    reflection_id: str
    experience_id: str
    reflection_status: str
    learning_candidate: str
    recommendation: str
    timestamp: Timestamp
    proposed_change_type: str = "memory"
    evidence_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None
    risk_hint: str | None = None
    human_review_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class OperatorFeedbackContract:
    feedback_id: str
    mission_id: MissionId
    experience_id: str
    assessment: str
    operator_ref: str
    timestamp: Timestamp
    rating: int | None = None
    comment: str | None = None
    correction: str | None = None
    next_expectation: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    feedback_status: str = "recorded_bounded"
    evolution_review_status: str = "needs_review"
    memory_write_mode: str = "through_core_only"
    human_review_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class RecurringPatternEvidenceContract:
    pattern_id: str
    pattern_type: str
    pattern_status: str
    workflow_profile: str
    route: str
    domain: str
    occurrence_count: int
    minimum_occurrences: int
    successful_occurrences: int
    non_successful_occurrences: int
    confidence_status: str
    outcome_summary: str
    pattern_summary: str
    experience_refs: list[str]
    reflection_refs: list[str]
    feedback_refs: list[str]
    evidence_refs: list[str]
    recurring_signals: list[str]
    conflict_flags: list[str]
    blockers: list[str]
    generated_at: Timestamp
    human_review_required: bool = True
    skill_candidate_generation_allowed: bool = False
    automatic_skill_creation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class RecurringPatternReportContract:
    report_id: str
    report_status: str
    records_analyzed: int
    compatible_group_count: int
    eligible_pattern_count: int
    minimum_occurrences: int
    scope_filters: dict[str, str]
    patterns: list[RecurringPatternEvidenceContract]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    sample_truncated: bool = False
    read_only: bool = True
    human_review_required: bool = True
    skill_candidate_generation_allowed: bool = False
    automatic_skill_creation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class SkillCandidateContract:
    skill_candidate_id: str
    skill_id: str
    skill_name: str
    version: str
    workflow_profile: str
    domain: str
    specialist_type: str
    inputs: list[str]
    outputs: list[str]
    allowed_tools: list[str]
    bounded_instructions: list[str]
    risk_level: RiskLevel
    evidence_refs: list[str]
    source_pattern_refs: list[str]
    failure_modes: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    timestamp: Timestamp
    registry_status: str = "candidate_inactive"
    review_status: str = "needs_review"
    activation_status: str = "inactive"
    blockers: list[str] = field(default_factory=list)
    sandbox_required: bool = True
    human_review_required: bool = True
    automatic_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    memory_write_mode: str = "through_core_only"


@dataclass
class SkillMiningRequestContract:
    mining_request_id: str
    source_pattern_ref: str
    skill_id: str
    skill_name: str
    version: str
    specialist_type: str
    inputs: list[str]
    outputs: list[str]
    allowed_tools: list[str]
    bounded_instructions: list[str]
    risk_level: RiskLevel
    failure_modes: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    timestamp: Timestamp
    human_review_required: bool = True
    automatic_mining_allowed: bool = False
    automatic_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class SkillMiningResultContract:
    mining_result_id: str
    mining_status: str
    eligibility_status: str
    source_pattern_ref: str
    source_authority_status: str
    threshold_occurrences: int
    observed_occurrences: int
    blockers: list[str]
    evidence_refs: list[str]
    generated_at: Timestamp
    candidate: SkillCandidateContract | None = None
    human_review_required: bool = True
    automatic_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class SkillSandboxCaseResultContract:
    case_id: str
    passed: bool
    checks: dict[str, bool]
    failed_checks: list[str]
    evidence_refs: list[str]


@dataclass
class SkillSandboxEvalContract:
    eval_id: str
    skill_candidate_id: str
    skill_id: str
    version: str
    evolution_proposal_id: EvolutionProposalId
    review_decision_id: str
    eval_status: str
    required_pass_rate: float
    pass_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[SkillSandboxCaseResultContract]
    evidence_refs: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    blockers: list[str]
    generated_at: Timestamp
    sandbox_only: bool = True
    human_review_required: bool = True
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class SkillEvolutionOperatorItemContract:
    skill_candidate_id: str
    skill_id: str
    skill_name: str
    version: str
    workflow_profile: str
    route: str | None
    domain: str
    specialist_type: str
    risk_level: str
    registry_status: str
    review_status: str
    activation_status: str
    evolution_status: str
    source_pattern_refs: list[str]
    pattern_status: str | None
    pattern_summary: str | None
    occurrence_count: int | None
    minimum_occurrences: int | None
    confidence_status: str | None
    proposal_id: str | None
    proposal_status: str | None
    sandbox_eval_ref: str | None
    sandbox_eval_status: str | None
    sandbox_pass_rate: float | None
    allowed_tools: list[str]
    evidence_refs: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    blockers: list[str]
    next_operator_action: str
    read_only: bool = True
    human_review_required: bool = True
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class SkillEvolutionOperatorViewContract:
    view_id: str
    view_status: str
    pattern_report_id: str
    pattern_report_status: str
    pattern_count: int
    candidate_count: int
    items: list[SkillEvolutionOperatorItemContract]
    unregistered_pattern_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    read_only: bool = True
    human_review_required: bool = True
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowPolicyDecisionContract:
    policy_ref: str
    policy_version: str
    source_registry_ref: str
    source_registry_fingerprint: str
    workflow_profile: str | None
    route: str | None
    resolution_status: str
    application_status: str
    application_reason: str
    planning_focus: str
    success_focus: str
    semantic_memory_role: str
    procedural_memory_role: str
    response_focus: str
    adaptive_intervention_priority: list[str]
    effects: list[str]
    evidence_refs: list[str]
    non_use_reason: str | None = None
    read_only: bool = True
    autonomous_execution_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowProfileVersionContract:
    workflow_version_id: str
    workflow_profile: str
    version: str
    route: str
    lifecycle_status: str
    definition_hash: str
    workflow_steps: list[str]
    workflow_checkpoints: list[str]
    workflow_decision_points: list[str]
    success_criteria: list[str]
    evidence_refs: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    source_registry_ref: str
    source_registry_fingerprint: str
    timestamp: Timestamp
    baseline_version_ref: str | None = None
    change_summary: str | None = None
    risk_level: str = "moderate"
    review_status: str = "needs_review"
    runtime_binding_status: str = "inactive_candidate"
    blockers: list[str] = field(default_factory=list)
    human_review_required: bool = True
    sandbox_required: bool = True
    active_registry_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowProfileVersionRegistryContract:
    registry_id: str
    registry_version: str
    registry_status: str
    active_registry_ref: str
    active_registry_fingerprint: str
    workflow_count: int
    baseline_count: int
    candidate_count: int
    versions: list[WorkflowProfileVersionContract]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    read_only: bool = True
    human_review_required: bool = True
    active_registry_mutation_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowEvolutionRequestContract:
    workflow_evolution_request_id: str
    source_pattern_ref: str
    source_review_decision_id: str
    baseline_version_ref: str
    candidate_version: str
    step_additions: list[str]
    step_removals: list[str]
    checkpoint_additions: list[str]
    checkpoint_removals: list[str]
    decision_point_additions: list[str]
    decision_point_removals: list[str]
    success_criteria_additions: list[str]
    success_criteria_removals: list[str]
    change_summary: str
    evidence_refs: list[str]
    proposed_tests: list[str]
    rollback_plan_ref: str
    risk_level: str
    timestamp: Timestamp
    human_review_required: bool = True
    automatic_build_allowed: bool = False
    active_registry_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowEvolutionBuildResultContract:
    workflow_evolution_result_id: str
    build_status: str
    source_pattern_ref: str
    source_review_decision_id: str
    baseline_version_ref: str
    source_authority_status: str
    delta_summary: dict[str, list[str]]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    candidate: WorkflowProfileVersionContract | None = None
    human_review_required: bool = True
    active_registry_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalControlSnapshotContract:
    control_snapshot_id: str
    workflow_policy_ref: str
    workflow_policy_version: str
    workflow_policy_source_registry_ref: str
    workflow_policy_source_registry_fingerprint: str
    governance_policy_ref: str
    governance_policy_version: str
    input_fingerprint: str
    memory_policy_refs: list[str]
    memory_policy_version_refs: dict[str, str]
    memory_input_fingerprint: str
    evaluator_version: str
    deterministic_seed: int
    fixed_clock: Timestamp
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalObservationContract:
    observation_id: str
    case_id: str
    case_version: str
    arm: str
    workflow_version_ref: str
    definition_hash: str
    input_snapshot_fingerprint: str
    control_snapshot_id: str
    control_snapshot_fingerprint: str
    outcome_ref: str
    outcome_status: str
    contract_checks: dict[str, bool]
    action_count: int
    rework_count: int
    expected_workflow_steps: list[str]
    expected_checkpoint_refs: list[str]
    expected_decision_points: list[str]
    expected_success_criteria: list[str]
    observed_checkpoint_refs: list[str]
    memory_participating_refs: list[str]
    memory_declared_causal_refs: list[str]
    evidence_refs: list[str]
    limitations: list[str]
    observed_at: Timestamp
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalCaseContract:
    case_pack_id: str
    case_pack_version: str
    case_id: str
    case_version: str
    scenario_ref: str
    input_snapshot_fingerprint: str
    workflow_profile: str
    route: str
    baseline_version_ref: str
    candidate_version_ref: str
    required_candidate_steps: list[str]
    required_candidate_checkpoints: list[str]
    required_candidate_decision_points: list[str]
    required_candidate_success_criteria: list[str]
    contract_check_refs: list[str]
    control_snapshot: WorkflowVariantEvalControlSnapshotContract
    baseline_observation: WorkflowVariantEvalObservationContract
    candidate_observation: WorkflowVariantEvalObservationContract
    evidence_refs: list[str]
    limitations: list[str] = field(default_factory=list)
    comparison_mode: str = WORKFLOW_VARIANT_EVAL_COMPARISON_MODE
    metrics_source: str = WORKFLOW_VARIANT_EVAL_METRICS_SOURCE
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalCasePackContract:
    case_pack_id: str
    case_pack_version: str
    workflow_profile: str
    route: str
    baseline_version_ref: str
    candidate_version_ref: str
    scope_refs: list[str]
    cases: list[WorkflowVariantEvalCaseContract]
    evidence_refs: list[str]
    generated_at: Timestamp
    comparison_mode: str = WORKFLOW_VARIANT_EVAL_COMPARISON_MODE
    metrics_source: str = WORKFLOW_VARIANT_EVAL_METRICS_SOURCE
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalCaseResultContract:
    case_pack_id: str
    case_pack_version: str
    case_pack_fingerprint: str
    case_id: str
    case_version: str
    scenario_ref: str
    input_snapshot_fingerprint: str
    workflow_profile: str
    route: str
    baseline_version_ref: str
    candidate_version_ref: str
    baseline_definition_hash: str
    candidate_definition_hash: str
    control_snapshot_id: str
    control_snapshot_fingerprint: str
    baseline_outcome_ref: str
    candidate_outcome_ref: str
    baseline_outcome_status: str
    candidate_outcome_status: str
    passed: bool
    checks: dict[str, bool]
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    metric_deltas: dict[str, float]
    improvement_signals: list[str]
    regression_flags: list[str]
    failures: list[str]
    limitations: list[str]
    evidence_refs: list[str]
    comparison_mode: str = WORKFLOW_VARIANT_EVAL_COMPARISON_MODE
    metrics_source: str = WORKFLOW_VARIANT_EVAL_METRICS_SOURCE
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowVariantEvalRunContract:
    run_id: str
    case_pack_id: str
    case_pack_version: str
    case_pack_fingerprint: str
    workflow_profile: str
    route: str
    baseline_version_ref: str
    candidate_version_ref: str
    baseline_definition_hashes: list[str]
    candidate_definition_hashes: list[str]
    control_snapshot_ids: list[str]
    control_snapshot_fingerprints: list[str]
    baseline_outcome_refs: list[str]
    candidate_outcome_refs: list[str]
    status: str
    readiness_status: str
    promotion_readiness: str
    comparison_conclusion: str
    pass_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    aggregate_baseline_metrics: dict[str, float]
    aggregate_candidate_metrics: dict[str, float]
    aggregate_metric_deltas: dict[str, float]
    case_results: list[WorkflowVariantEvalCaseResultContract]
    regression_flags: list[str]
    limitations: list[str]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    comparison_mode: str = WORKFLOW_VARIANT_EVAL_COMPARISON_MODE
    metrics_source: str = WORKFLOW_VARIANT_EVAL_METRICS_SOURCE
    offline_only: bool = True
    read_only: bool = True
    sandbox_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    release_authorized: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class WorkflowRollbackPlanContract:
    rollback_plan_id: str
    rollback_plan_ref: str
    workflow_profile: str
    route: str
    baseline_version_ref: str
    candidate_version_ref: str
    plan_status: str
    execution_mode: str
    trigger_conditions: list[str]
    procedure_steps: list[str]
    verification_tests: list[str]
    evidence_refs: list[str]
    blockers: list[str]
    operator_ref: str
    generated_at: Timestamp
    human_review_required: bool = True
    execution_authorized: bool = False
    active_registry_write_allowed: bool = False
    automatic_rollback_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowLifecycleTransitionContract:
    """Append-only human-authorized binding beside the sovereign route registry."""

    transition_id: str
    workflow_profile: str
    route: str
    transition_action: str
    transition_status: str
    revision: int
    previous_transition_id: str | None
    previous_transition_fingerprint: str | None
    source_registry_ref: str
    source_registry_fingerprint: str
    baseline_version_ref: str
    baseline_definition_hash: str
    candidate_version_ref: str
    candidate_definition_hash: str
    active_version_ref: str
    active_definition_hash: str
    active_workflow_steps: list[str]
    active_workflow_checkpoints: list[str]
    active_workflow_decision_points: list[str]
    active_success_criteria: list[str]
    evolution_proposal_id: str
    proposal_fingerprint: str
    review_decision_id: str
    review_decision_fingerprint: str
    release_checklist_id: str
    release_checklist_fingerprint: str
    promotion_gate_id: str
    promotion_gate_fingerprint: str
    workflow_eval_run_id: str
    workflow_eval_run_fingerprint: str
    rollback_plan_id: str
    rollback_plan_fingerprint: str
    human_authorization_ref: str
    operator_ref: str
    evidence_refs: list[str]
    completed_test_refs: list[str]
    failure_refs: list[str]
    timestamp: Timestamp
    read_only: bool = True
    immutable: bool = True
    human_authorized: bool = True
    memory_write_mode: str = "through_core_only"
    active_registry_write_allowed: bool = False
    runtime_execution_allowed: bool = False
    automatic_promotion_allowed: bool = False
    automatic_rollback_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class WorkflowLifecycleGovernanceAssessmentContract:
    """Fail-closed governance decision for recording one lifecycle transition."""

    assessment_id: str
    transition_id: str
    transition_action: str
    transition_fingerprint: str
    status: str
    blockers: list[str]
    conditions: list[str]
    policy_refs: list[str]
    timestamp: Timestamp
    human_review_required: bool = True
    human_authorization_verified: bool = False
    transition_recording_authorized: bool = False
    memory_write_mode: str = "through_core_only"
    read_only: bool = True
    active_registry_write_allowed: bool = False
    runtime_execution_allowed: bool = False
    automatic_promotion_allowed: bool = False
    automatic_rollback_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class ProceduralPlaybookCandidateContract:
    playbook_candidate_id: str
    procedure_name: str
    workflow_profile: str
    bounded_steps: list[str]
    evidence_refs: list[str]
    timestamp: Timestamp
    route: str | None = None
    domain: str | None = None
    source_artifact_refs: list[str] = field(default_factory=list)
    source_reflection_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None
    risk_hint: str | None = None
    review_status: str = "candidate"
    blockers: list[str] = field(default_factory=list)
    human_review_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False
    memory_write_mode: str = "through_core_only"


@dataclass
class ReviewedProceduralPlaybookContract:
    playbook_id: str
    version: str
    source_candidate_id: str
    source_review_decision_id: str
    evolution_proposal_id: EvolutionProposalId
    review_status: str
    procedure_name: str
    route: str
    workflow_profile: str
    domain: str
    bounded_steps: list[str]
    allowed_usage: list[str]
    evidence_refs: list[str]
    rollback_plan_ref: str
    timestamp: Timestamp
    revoked_at: Timestamp | None = None
    revocation_ref: str | None = None
    read_only: bool = True
    human_review_required: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    memory_write_mode: str = "read_only"
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class ActionIntentContract:
    """Exact, expiring action identity awaiting independent authorization."""

    intent_id: str
    origin_request_id: RequestId
    session_id: SessionId
    mission_id: MissionId | None
    operator_identity_ref: str
    handler_id: str
    handler_version: str
    operation: str
    target_ref: str
    content_digest: str
    precondition_digest: str
    risk_level: RiskLevel
    policy_version: str
    nonce: str
    issued_at: Timestamp
    expires_at: Timestamp
    action_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class ActionConfirmationChallengeContract:
    """Operator-visible challenge bound to one exact, expiring action intent."""

    challenge_id: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    origin_request_id: RequestId
    session_id: SessionId
    mission_id: MissionId | None
    operator_identity_ref: str
    operation: str
    nonce: str
    issued_at: Timestamp
    expires_at: Timestamp
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class HumanConfirmationReceiptContract:
    """Local operator attestation; it is evidence and never execution authority."""

    receipt_id: str
    challenge_id: str
    challenge_fingerprint: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    origin_request_id: RequestId
    session_id: SessionId
    mission_id: MissionId | None
    operator_identity_ref: str
    operation: str
    confirmed_at: Timestamp
    expires_at: Timestamp
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class ActionConfirmationClaimContract:
    """Single-use claim binding one receipt to one concrete runtime operation."""

    claim_id: str
    receipt_id: str
    receipt_fingerprint: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    operation_id: OperationId
    origin_request_id: RequestId
    session_id: SessionId
    mission_id: MissionId | None
    operator_identity_ref: str
    operation: str
    claimed_at: Timestamp
    expires_at: Timestamp
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


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
    surface_id: str | None = None
    surface_kind: str | None = None
    surface_session_id: str | None = None
    surface_capability_scope: list[str] = field(default_factory=list)
    operator_identity_ref: str | None = None
    canonical_user_ref: str | None = None
    surface_continuity_status: str = "single_surface"
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str = "active"
    next_action_ref: str | None = None
    requested_autonomy_level: str | None = None
    max_autonomy_level: str | None = None
    autonomy_confirmation_mode: str | None = None
    autonomy_policy_refs: list[str] = field(default_factory=list)
    action_confirmation_receipt_id: str | None = None
    action_confirmation_origin_request_id: str | None = None
    adapter_action_request: "AdapterActionRequestContract | None" = None


@dataclass
class AutonomyLadderContract:
    requested_autonomy_level: str
    max_autonomy_level: str
    effective_autonomy_level: str
    autonomy_ladder_status: str
    max_capability_mode: str
    human_confirmation_required: bool
    human_confirmation_mode: str
    autonomy_action_kind: str | None = None
    autonomy_validation_errors: list[str] = field(default_factory=list)
    allowed_runtime_actions: list[str] = field(default_factory=list)
    blocked_runtime_actions: list[str] = field(default_factory=list)
    policy_refs: list[str] = field(default_factory=list)
    summary: str | None = None
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AutonomyActionPolicyDecisionContract:
    """Fail-closed policy result for one canonical runtime action."""

    policy_version: str
    decision: str
    requested_autonomy_level: str | None
    max_autonomy_level: str | None
    effective_autonomy_level: str | None
    autonomy_ladder_status: str | None
    action_kind: str | None
    selected_capability_mode: str | None
    max_capability_mode: str | None
    confirmation_required: bool
    confirmation_requirement: str
    confirmation_evidence_state: str
    side_effect_allowed: bool
    reason_codes: tuple[str, ...]
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterActionRequestContract:
    """Exact adapter action requested by a caller; metadata only."""

    adapter_id: str
    adapter_version: str
    action_kind: str
    operation: str
    resource_scope: str
    resource_ref: str


@dataclass(frozen=True)
class AdapterDescriptorContract:
    """Allowlisted prepare-only adapter metadata; never an executor."""

    adapter_id: str
    adapter_version: str
    action_kind: str
    allowed_operations: tuple[str, ...]
    allowed_resource_scopes: tuple[str, ...]
    descriptor_fingerprint: str
    prepare_only: bool = True
    executor_ref: str | None = None
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterRegistrySnapshotContract:
    """Immutable exact-key adapter allowlist snapshot."""

    registry_id: str
    registry_version: str
    descriptors: tuple[AdapterDescriptorContract, ...]
    registry_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterGrantContract:
    """Expiring single-use permission bound to one exact prepared action."""

    grant_id: str
    subject_ref: str
    adapter_request: AdapterActionRequestContract
    descriptor_fingerprint: str
    registry_fingerprint: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    autonomy_policy_decision_fingerprint: str
    policy_version: str
    nonce: str
    confirmation_required: bool
    issued_at: Timestamp
    expires_at: Timestamp
    grant_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterGrantClaimContract:
    """Single-use claim of one grant; confirmation is evidence only."""

    claim_id: str
    grant_id: str
    grant_fingerprint: str
    operation_id: OperationId
    subject_ref: str
    adapter_request: AdapterActionRequestContract
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    claimed_at: Timestamp
    expires_at: Timestamp
    claim_fingerprint: str
    confirmation_receipt_id: str | None = None
    confirmation_claim_id: str | None = None
    confirmation_claim_fingerprint: str | None = None
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFilePreflightRequestContract:
    """Ephemeral, exactly bound input for a side-effect-free text-file preflight."""

    grant_id: str
    grant_fingerprint: str
    action_fingerprint: str
    intent_fingerprint: str
    descriptor_fingerprint: str
    registry_fingerprint: str
    subject_ref: str
    adapter_request: AdapterActionRequestContract
    desired_text: str
    expected_root_config_fingerprint: str
    preflight_policy_version: str
    diff_algorithm: str
    diff_algorithm_version: str
    prepared_at: Timestamp
    expires_at: Timestamp
    authorization_expires_at: Timestamp
    expected_current_sha256: str | None = None
    persistence_allowed: bool = False
    telemetry_allowed: bool = False
    contains_sensitive_content: bool = True


@dataclass(frozen=True)
class LocalTextFileRollbackPlanContract:
    """Content-free rollback metadata for a prepared local text-file action."""

    strategy: str
    operation: str
    resource_ref: str
    root_config_fingerprint: str
    before_content_sha256: str
    desired_content_sha256: str
    preflight_policy_version: str
    precondition_content_sha256: str
    restore_content_sha256: str | None
    rollback_fingerprint: str
    manual_execution_required: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFilePreflightContract:
    """Immutable metadata prepared without writing to the configured text root."""

    grant_id: str
    grant_fingerprint: str
    action_fingerprint: str
    intent_fingerprint: str
    descriptor_fingerprint: str
    registry_fingerprint: str
    subject_ref: str
    adapter_request: AdapterActionRequestContract
    operation: str
    resource_ref: str
    root_alias: str
    relative_path: str
    expected_current_sha256: str | None
    before_exists: bool
    before_content_sha256: str
    desired_content_sha256: str
    before_size_bytes: int
    desired_size_bytes: int
    unified_diff: str
    diff_sha256: str
    root_config_fingerprint: str
    filesystem_snapshot_fingerprint: str
    rollback_plan: LocalTextFileRollbackPlanContract
    preflight_fingerprint: str
    preflight_policy_version: str
    diff_algorithm: str
    diff_algorithm_version: str
    prepared_at: Timestamp
    expires_at: Timestamp
    authorization_expires_at: Timestamp
    filesystem_snapshot_algorithm: str
    filesystem_snapshot_algorithm_version: str
    adapter_backend_version: str
    change_status: str
    encoding: str = "utf-8"
    execution_grant_required: bool = True
    preflight_grant_reusable_for_execution: bool = False
    persistence_allowed: bool = False
    telemetry_allowed: bool = False
    contains_sensitive_diff: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterExecutionDescriptorContract:
    """Versioned mutating capability metadata; never authority by itself."""

    adapter_id: str
    adapter_version: str
    action_kind: str
    allowed_operations: tuple[str, ...]
    allowed_resource_scopes: tuple[str, ...]
    executor_ref: str
    execution_policy_version: str
    execution_backend_version: str
    descriptor_fingerprint: str
    execution_only: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterExecutionRegistrySnapshotContract:
    """Immutable allowlist for mutating adapter versions, separate from prepare."""

    registry_id: str
    registry_version: str
    descriptors: tuple[AdapterExecutionDescriptorContract, ...]
    registry_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFilePreflightAttestationContract:
    """Content-free trusted-boundary evidence emitted for one exact preflight."""

    attestation_id: str
    attestation_nonce: str
    trusted_boundary_ref: str
    subject_ref: str
    operation: str
    resource_scope: str
    resource_ref: str
    source_preflight_grant_id: str
    source_preflight_grant_fingerprint: str
    source_action_fingerprint: str
    source_intent_fingerprint: str
    source_descriptor_fingerprint: str
    source_registry_fingerprint: str
    preflight_fingerprint: str
    preflight_prepared_at: Timestamp
    preflight_expires_at: Timestamp
    preflight_authorization_expires_at: Timestamp
    root_config_fingerprint: str
    filesystem_snapshot_fingerprint: str
    rollback_fingerprint: str
    before_exists: bool
    expected_current_sha256: str | None
    before_content_sha256: str
    desired_content_sha256: str
    preflight_policy_version: str
    preflight_backend_version: str
    attested_at: Timestamp
    attestation_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterExecutionRequestContract:
    """Content-free exact projection of one valid local-text preflight."""

    adapter_id: str
    adapter_version: str
    action_kind: str
    operation: str
    resource_scope: str
    resource_ref: str
    subject_ref: str
    preflight_attestation_id: str
    preflight_attestation_fingerprint: str
    source_preflight_grant_id: str
    source_preflight_grant_fingerprint: str
    source_action_fingerprint: str
    source_intent_fingerprint: str
    source_descriptor_fingerprint: str
    source_registry_fingerprint: str
    preflight_fingerprint: str
    preflight_prepared_at: Timestamp
    preflight_expires_at: Timestamp
    preflight_authorization_expires_at: Timestamp
    root_config_fingerprint: str
    filesystem_snapshot_fingerprint: str
    rollback_fingerprint: str
    before_exists: bool
    expected_current_sha256: str | None
    before_content_sha256: str
    precondition_content_sha256: str
    desired_content_sha256: str
    postcondition_content_sha256: str
    preflight_policy_version: str
    preflight_backend_version: str
    execution_policy_version: str
    execution_backend_version: str
    requested_at: Timestamp
    execution_request_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterExecutionGrantContract:
    """Expiring single-effect authority evidence bound to one preflight."""

    grant_id: str
    subject_ref: str
    execution_request: AdapterExecutionRequestContract
    descriptor_fingerprint: str
    registry_fingerprint: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    autonomy_policy_decision_fingerprint: str
    policy_version: str
    nonce: str
    confirmation_required: bool
    issued_at: Timestamp
    expires_at: Timestamp
    grant_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class AdapterExecutionGrantClaimContract:
    """Atomic claim evidence; active verification still gates effect start."""

    claim_id: str
    grant_id: str
    grant_fingerprint: str
    operation_id: OperationId
    journal_reservation_fingerprint: str
    subject_ref: str
    execution_request: AdapterExecutionRequestContract
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    claimed_at: Timestamp
    expires_at: Timestamp
    claim_fingerprint: str
    confirmation_receipt_id: str
    confirmation_claim_id: str
    confirmation_claim_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextMutationReceipt:
    """Content-free durable evidence that one governed local-text mutation applied."""

    operation_id: str
    execution_grant_id: str
    execution_claim_id: str
    operation: str
    resource_ref: str
    subject_ref: str
    preflight_fingerprint: str
    before_content_sha256: str
    desired_content_sha256: str
    root_config_fingerprint: str
    applied_event_fingerprint: str
    committed_at: str
    mutation_status: str
    receipt_fingerprint: str
    rollback_available: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False


@dataclass(frozen=True)
class LocalTextRollbackReceipt:
    """Content-free durable evidence that one separately governed rollback applied."""

    operation_id: str
    mutation_operation_id: str
    rollback_grant_id: str
    rollback_claim_id: str
    mutation_receipt_fingerprint: str
    resource_ref: str
    restored_content_sha256: str
    rolled_back_at: str
    rolled_back_event_fingerprint: str
    rollback_receipt_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFileRollbackDescriptorContract:
    """Versioned rollback-only adapter metadata; never authority by itself."""

    adapter_id: str
    adapter_version: str
    action_kind: str
    purpose: str
    allowed_operations: tuple[str, ...]
    allowed_resource_scopes: tuple[str, ...]
    executor_ref: str
    rollback_policy_version: str
    rollback_backend_version: str
    descriptor_fingerprint: str
    rollback_only: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFileRollbackRegistrySnapshotContract:
    """Immutable allowlist dedicated to local-text rollback capability versions."""

    registry_id: str
    registry_version: str
    descriptors: tuple[LocalTextFileRollbackDescriptorContract, ...]
    registry_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFileRollbackRequestContract:
    """Exact rollback request derived from a persisted mutation receipt and EXEC chain."""

    purpose: str
    adapter_id: str
    adapter_version: str
    action_kind: str
    operation: str
    resource_scope: str
    resource_ref: str
    subject_ref: str
    rollback_operation_id: OperationId
    mutation_operation_id: OperationId
    mutation_receipt_fingerprint: str
    mutation_applied_event_fingerprint: str
    mutation_committed_at: Timestamp
    source_execution_grant_id: str
    source_execution_grant_fingerprint: str
    source_execution_claim_id: str
    source_execution_claim_fingerprint: str
    source_execution_request_fingerprint: str
    source_preflight_attestation_id: str
    source_preflight_attestation_fingerprint: str
    source_preflight_fingerprint: str
    source_action_fingerprint: str
    source_intent_fingerprint: str
    original_operation: str
    root_config_fingerprint: str
    expected_current_sha256: str
    restored_content_sha256: str
    original_before_content_sha256: str
    original_desired_content_sha256: str
    rollback_plan_fingerprint: str
    source_preflight_policy_version: str
    source_preflight_backend_version: str
    source_execution_policy_version: str
    source_execution_backend_version: str
    transaction_policy_version: str
    transaction_backend_version: str
    rollback_policy_version: str
    rollback_backend_version: str
    requested_at: Timestamp
    expires_at: Timestamp
    rollback_request_fingerprint: str
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFileRollbackGrantContract:
    """Confirmation-required single-use rollback authority for one mutation receipt."""

    grant_id: str
    subject_ref: str
    rollback_request: LocalTextFileRollbackRequestContract
    descriptor_fingerprint: str
    registry_fingerprint: str
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    autonomy_policy_decision_fingerprint: str
    policy_version: str
    nonce: str
    confirmation_required: bool
    issued_at: Timestamp
    expires_at: Timestamp
    grant_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class LocalTextFileRollbackGrantClaimContract:
    """Atomic rollback and confirmation claim with a distinct journal reservation."""

    claim_id: str
    grant_id: str
    grant_fingerprint: str
    rollback_operation_id: OperationId
    rollback_journal_reservation_fingerprint: str
    subject_ref: str
    rollback_request: LocalTextFileRollbackRequestContract
    intent_id: str
    intent_fingerprint: str
    action_fingerprint: str
    claimed_at: Timestamp
    expires_at: Timestamp
    claim_fingerprint: str
    confirmation_receipt_id: str
    confirmation_claim_id: str
    confirmation_claim_fingerprint: str
    single_use: bool = True
    read_only: bool = True
    immutable: bool = True
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


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
class SemanticMemoryCandidateContract:
    anchor_ref: str
    source_kind: str
    summary: str
    evidence_refs: list[str]
    observed_at: Timestamp
    freshness_status: str
    relevance_score: float
    relevance_reason: str
    domain_hints: list[str] = field(default_factory=list)
    lifecycle_status: str = "retained"
    read_only: bool = True
    memory_write_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryInfluenceSignalContract:
    signal_ref: str
    source_kind: str
    summary: str
    evidence_refs: list[str]
    conflict_group: str
    directive: str
    route: str | None = None
    workflow_profile: str | None = None
    domain: str | None = None
    lifecycle_status: str | None = None
    review_status: str | None = None
    observed_at: Timestamp | None = None
    freshness_status: str | None = None
    relevance_score: float | None = None
    relevance_reason: str | None = None
    version_ref: str | None = None
    review_decision_ref: str | None = None
    allowed_usage: list[str] = field(default_factory=lambda: ["planning_context"])
    read_only: bool = True
    memory_write_allowed: bool = False
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryInfluencePolicyDecisionContract:
    decision_id: str
    decision_status: str
    route: str | None
    workflow_profile: str | None
    domain: str | None
    selected_refs: list[str]
    ignored_refs: list[str]
    priority_order: list[str]
    conflict_refs: list[str]
    use_reasons: dict[str, str]
    non_use_reasons: dict[str, str]
    evidence_refs: list[str]
    policy_refs: list[str]
    generated_at: Timestamp
    signal_kinds: dict[str, str] = field(default_factory=dict)
    freshness_statuses: dict[str, str] = field(default_factory=dict)
    relevance_scores: dict[str, float] = field(default_factory=dict)
    version_refs: dict[str, str] = field(default_factory=dict)
    review_decision_refs: dict[str, str] = field(default_factory=dict)
    read_only: bool = True
    memory_write_allowed: bool = False
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryInfluenceGovernanceAssessmentContract:
    assessment_id: str
    assessment_status: str
    decision_id: str
    blockers: list[str]
    policy_refs: list[str]
    timestamp: Timestamp
    causal_use_allowed: bool
    human_review_required: bool = False
    decision_mutation_allowed: bool = False
    memory_write_allowed: bool = False
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class DecisionAttributionClassificationContract:
    attribution_status: str
    participating_refs: list[str]
    declared_causal_refs: list[str]
    correlated_refs: list[str]
    attribution_reasons: list[str]
    limitations: list[str]
    causality_scope: str = DECISION_ATTRIBUTION_CAUSALITY_SCOPE
    causal_effect_proven: bool = False
    gain_claim_status: str = DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS
    read_only: bool = True
    human_review_required: bool = True
    memory_write_allowed: bool = False
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class DecisionOutcomeAttributionRecordContract:
    attribution_record_id: str
    request_id: RequestId
    session_id: SessionId
    mission_id: MissionId | None
    observed_at: Timestamp
    governance_decision_ref: str
    governance_decision_status: str
    workflow_profile: str | None
    route: str | None
    outcome_ref: str | None
    outcome_status: str | None
    experience_id: str | None = None
    workflow_policy_ref: str | None = None
    workflow_policy_version: str | None = None
    workflow_policy_source_registry_ref: str | None = None
    workflow_policy_source_registry_fingerprint: str | None = None
    workflow_policy_application_status: str = "not_evaluated"
    workflow_policy_effects: list[str] = field(default_factory=list)
    memory_policy_decision_ref: str | None = None
    memory_policy_status: str = "not_evaluated"
    memory_policy_refs: list[str] = field(default_factory=list)
    memory_selected_refs: list[str] = field(default_factory=list)
    memory_ignored_refs: list[str] = field(default_factory=list)
    memory_use_reasons: dict[str, str] = field(default_factory=dict)
    memory_non_use_reasons: dict[str, str] = field(default_factory=dict)
    memory_signal_kinds: dict[str, str] = field(default_factory=dict)
    memory_version_refs: dict[str, str] = field(default_factory=dict)
    memory_review_decision_refs: dict[str, str] = field(default_factory=dict)
    memory_causal_use_allowed: bool = False
    declared_effects_by_ref: dict[str, list[str]] = field(default_factory=dict)
    participating_refs: list[str] = field(default_factory=list)
    declared_causal_refs: list[str] = field(default_factory=list)
    correlated_refs: list[str] = field(default_factory=list)
    attribution_status: str = "insufficient_evidence"
    attribution_reasons: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    causality_scope: str = DECISION_ATTRIBUTION_CAUSALITY_SCOPE
    causal_effect_proven: bool = False
    gain_claim_status: str = DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS
    read_only: bool = True
    immutable: bool = True
    human_review_required: bool = True
    memory_write_allowed: bool = False
    execution_allowed: bool = False
    tool_dispatch_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class DecisionOutcomeAttributionItemContract:
    item_id: str
    attribution: DecisionOutcomeAttributionRecordContract
    feedback_status: str
    feedback_refs: list[str]
    feedback_assessments: list[str]
    feedback_ratings: list[int]
    comparator_status: str = "not_available"
    comparator_refs: list[str] = field(default_factory=list)
    gain_claim_status: str = DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS
    limitations: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    causal_effect_proven: bool = False
    read_only: bool = True
    human_review_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass(frozen=True)
class DecisionOutcomeAttributionReportContract:
    report_id: str
    report_status: str
    generated_at: Timestamp
    record_count: int
    correlation_only_count: int
    declared_causality_count: int
    insufficient_evidence_count: int
    feedback_linked_count: int
    comparator_count: int
    failed_record_count: int
    items: list[DecisionOutcomeAttributionItemContract]
    limitations: list[str]
    evidence_refs: list[str]
    source_record_limit_reached: bool = False
    source_event_limit_reached: bool = False
    causality_scope: str = DECISION_ATTRIBUTION_CAUSALITY_SCOPE
    causal_effect_proven: bool = False
    gain_claim_status: str = DECISION_ATTRIBUTION_GAIN_CLAIM_STATUS
    read_only: bool = True
    human_review_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class UserScopeContextContract:
    user_id: str
    context_status: str
    interaction_count: int = 0
    user_context_brief: str | None = None
    recent_intents: list[str] = field(default_factory=list)
    recent_domain_focus: list[str] = field(default_factory=list)
    active_mission_ids: list[MissionId] = field(default_factory=list)
    recent_session_ids: list[SessionId] = field(default_factory=list)
    last_recommended_task_type: str | None = None
    continuity_preference: str | None = None
    memory_refs: list[str] = field(default_factory=list)


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
    canonical_domains: list[str] = field(default_factory=list)
    primary_canonical_domain: str | None = None
    primary_mind: str | None = None
    primary_mind_family: str | None = None
    primary_domain_driver: str | None = None
    arbitration_source: str | None = None
    primary_route: str | None = None
    mind_domain_specialist_contract_status: str | None = None
    mind_domain_specialist_contract_summary: str | None = None
    mind_domain_specialist_contract_chain: str | None = None
    mind_domain_specialist_active_specialist: str | None = None
    mind_domain_specialist_override_mode: str | None = None
    mind_domain_specialist_fallback_mode: str | None = None
    route_consumer_profile: str | None = None
    route_consumer_objective: str | None = None
    route_expected_deliverables: list[str] = field(default_factory=list)
    route_telemetry_focus: list[str] = field(default_factory=list)
    route_workflow_profile: str | None = None
    route_workflow_steps: list[str] = field(default_factory=list)
    route_workflow_checkpoints: list[str] = field(default_factory=list)
    route_workflow_decision_points: list[str] = field(default_factory=list)
    workflow_policy_decision: WorkflowPolicyDecisionContract | None = None
    workflow_lifecycle_transition: WorkflowLifecycleTransitionContract | None = None
    workflow_lifecycle_resolution_status: str = "static_baseline"
    workflow_lifecycle_resolution_reasons: list[str] = field(default_factory=list)
    tensions_considered: list[str] = field(default_factory=list)
    specialist_hints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    contract_validation_status: str = "not_evaluated"
    contract_validation_errors: list[str] = field(default_factory=list)
    contract_validation_retry_applied: bool = False
    specialist_resolution_summary: str | None = None
    dominant_tension: str | None = None
    smallest_safe_next_action: str | None = None
    metacognitive_guidance_applied: bool = False
    metacognitive_guidance_summary: str | None = None
    metacognitive_effects: list[str] = field(default_factory=list)
    metacognitive_containment_recommendation: str | None = None
    semantic_memory_source: str | None = None
    procedural_memory_source: str | None = None
    semantic_memory_effects: list[str] = field(default_factory=list)
    procedural_memory_effects: list[str] = field(default_factory=list)
    semantic_memory_lifecycle: str | None = None
    procedural_memory_lifecycle: str | None = None
    semantic_memory_state: str | None = None
    procedural_memory_state: str | None = None
    semantic_memory_anchor_refs: list[str] = field(default_factory=list)
    semantic_memory_evidence_refs: list[str] = field(default_factory=list)
    semantic_memory_use_reason: str | None = None
    semantic_memory_non_use_reason: str | None = None
    memory_influence_policy_decision: MemoryInfluencePolicyDecisionContract | None = None
    memory_lifecycle_status: str | None = None
    memory_review_status: str | None = None
    memory_maintenance_status: str | None = None
    memory_maintenance_reason: str | None = None
    memory_maintenance_fallback_mode: str | None = None
    context_compaction_status: str | None = None
    cross_session_recall_status: str | None = None
    memory_consolidation_status: str | None = None
    memory_fixation_status: str | None = None
    memory_archive_status: str | None = None
    reflection_influence_status: str | None = None
    reflection_influence_refs: list[str] = field(default_factory=list)
    reflection_influence_summary: str | None = None
    reflection_influence_workflow_profile: str | None = None
    reviewed_learning_influence_status: str | None = None
    reviewed_learning_influence_refs: list[str] = field(default_factory=list)
    reviewed_learning_influence_summary: str | None = None
    reviewed_learning_influence_reason: str | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_ref: str | None = None
    procedural_artifact_version: int | None = None
    procedural_artifact_summary: str | None = None
    mind_disagreement_status: str | None = None
    mind_validation_checkpoints: list[str] = field(default_factory=list)
    capability_decision_status: str | None = None
    capability_decision_objective: str | None = None
    capability_decision_reason: str | None = None
    capability_decision_selected_mode: str | None = None
    capability_decision_authorization_status: str | None = None
    capability_decision_fallback_mode: str | None = None
    capability_decision_tool_class: str | None = None
    capability_decision_handoff_mode: str | None = None
    capability_decision_eligible_capabilities: list[str] = field(default_factory=list)
    capability_decision_selected_capabilities: list[str] = field(default_factory=list)
    request_identity_status: str | None = None
    request_active_mission: str | None = None
    request_executive_posture: str | None = None
    request_authority_level: str | None = None
    request_risk_profile: str | None = None
    request_reversibility_mode: str | None = None
    request_confirmation_mode: str | None = None
    request_identity_summary: str | None = None
    request_identity_policy_refs: list[str] = field(default_factory=list)
    requested_autonomy_level: str | None = None
    max_autonomy_level: str | None = None
    effective_autonomy_level: str | None = None
    autonomy_ladder_status: str | None = None
    max_autonomy_capability_mode: str | None = None
    autonomy_human_confirmation_required: bool = True
    autonomy_confirmation_mode: str | None = None
    autonomy_action_kind: str | None = None
    adapter_action_request: AdapterActionRequestContract | None = None
    autonomy_validation_errors: list[str] = field(default_factory=list)
    autonomy_allowed_runtime_actions: list[str] = field(default_factory=list)
    autonomy_blocked_runtime_actions: list[str] = field(default_factory=list)
    autonomy_policy_refs: list[str] = field(default_factory=list)
    autonomy_summary: str | None = None
    autonomy_automatic_promotion_allowed: bool = False
    autonomy_core_mutation_allowed: bool = False
    adaptive_intervention_status: str | None = None
    adaptive_intervention_reason: str | None = None
    adaptive_intervention_trigger: str | None = None
    adaptive_intervention_selected_action: str | None = None
    adaptive_intervention_expected_effect: str | None = None
    adaptive_intervention_effects: list[str] = field(default_factory=list)
    cognitive_strategy_shift_applied: bool = False
    cognitive_strategy_shift_summary: str | None = None
    cognitive_strategy_shift_trigger: str | None = None
    cognitive_strategy_shift_effects: list[str] = field(default_factory=list)
    continuity_action: str | None = None
    continuity_reason: str | None = None
    open_loops: list[str] = field(default_factory=list)
    continuity_source: str | None = None
    continuity_target_mission_id: MissionId | None = None
    continuity_target_goal: str | None = None
    continuity_replay_status: str | None = None
    continuity_recovery_mode: str | None = None
    continuity_resume_point: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None


@dataclass
class DomainRegistryEntryContract:
    domain_name: str
    activation_stage: str
    maturity: str
    display_name: str | None = None
    domain_scope: str | None = None
    canonical_family: str | None = None
    canonical_refs: list[str] = field(default_factory=list)
    linked_specialist_type: str | None = None
    specialist_mode: str | None = None
    summary: str | None = None


@dataclass
class DomainSpecialistRouteContract:
    domain_name: str
    specialist_type: str
    specialist_mode: str
    routing_reason: str
    canonical_domain_refs: list[str] = field(default_factory=list)
    routing_source: str = "domain_registry"


@dataclass
class DomainKnowledgePackContract:
    knowledge_pack_id: str
    version: str
    canonical_domain_refs: list[str]
    source_refs: list[str]
    content_refs: list[str]
    coverage_topics: list[str]
    evidence_refs: list[str]
    timestamp: Timestamp
    pack_status: str = "candidate"
    freshness_status: str = "unverified"
    review_status: str = "needs_review"
    human_review_required: bool = True
    automatic_activation_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class DomainOnboardingCandidateContract:
    onboarding_candidate_id: str
    route_name: str
    display_name: str
    canonical_domain_refs: list[str]
    knowledge_pack_id: str
    onboarding_workflow_profile: str
    runtime_workflow_profile: str
    workflow_steps: list[str]
    workflow_checkpoints: list[str]
    workflow_decision_points: list[str]
    proposed_tests: list[str]
    eval_pack_ref: str
    rollback_plan_ref: str
    evidence_refs: list[str]
    timestamp: Timestamp
    linked_specialist_type: str | None = None
    specialist_mode: str = "registry_only"
    requested_maturity: str = "candidate"
    activation_stage: str = "candidate"
    human_review_required: bool = True
    registry_write_allowed: bool = False
    specialist_promotion_allowed: bool = False
    automatic_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class DomainOnboardingAssessmentContract:
    assessment_id: str
    onboarding_candidate_id: str
    route_name: str
    knowledge_pack_id: str
    readiness_status: str
    decision: str
    criteria: dict[str, bool]
    blockers: list[str]
    warnings: list[str]
    registry_preview: dict[str, object]
    timestamp: Timestamp
    human_review_required: bool = True
    registry_write_allowed: bool = False
    specialist_promotion_allowed: bool = False
    automatic_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class DomainEvalCaseContract:
    case_id: str
    intent: str
    input_text: str
    session_key: str
    expected_decision: str
    expected_route: str
    expected_canonical_domain_refs: list[str]
    expected_workflow_profile: str
    expected_specialist_type: str
    allowed_memory_causality_statuses: list[str]
    required_response_fragments: list[str]
    required_events: list[str]
    mission_key: str | None = None
    minimum_response_length: int = 120


@dataclass
class DomainEvalPackContract:
    eval_pack_id: str
    version: str
    route_name: str
    canonical_domain_refs: list[str]
    workflow_profile: str
    specialist_type: str
    cases: list[DomainEvalCaseContract]
    evidence_refs: list[str]
    timestamp: Timestamp
    minimum_pass_rate: float = 1.0
    offline_only: bool = True
    human_review_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class DomainEvalCaseResultContract:
    eval_pack_id: str
    case_id: str
    passed: bool
    checks: dict[str, bool]
    failures: list[str]
    observed_governance_decision: str | None
    observed_route: str | None
    observed_canonical_domain_refs: list[str]
    observed_workflow_profile: str | None
    observed_specialist_types: list[str]
    observed_memory_causality_status: str
    response_evidence: list[str]
    response_length: int
    observed_events: list[str]


@dataclass
class DomainEvalRunContract:
    run_id: str
    eval_pack_id: str
    pack_version: str
    route_name: str
    status: str
    readiness_status: str
    promotion_readiness: str
    pass_rate: float
    total_cases: int
    passed_cases: int
    failed_cases: int
    case_results: list[DomainEvalCaseResultContract]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    offline_only: bool = True
    human_review_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class RoutingAdaptationObservationContract:
    observation_id: str
    source_case_id: str
    expected_route: str
    observed_route: str | None
    expected_workflow_profile: str
    observed_workflow_profile: str | None
    expected_specialist_type: str
    observed_specialist_types: list[str]
    outcome_status: str
    memory_causality_status: str
    route_match: bool
    workflow_match: bool
    specialist_match: bool
    evidence_refs: list[str]
    timestamp: Timestamp
    mission_id: str | None = None
    read_only: bool = True
    human_review_required: bool = True
    routing_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class RoutingAdaptationCandidateContract:
    candidate_id: str
    candidate_status: str
    current_route: str
    proposed_route: str
    workflow_profile: str
    expected_specialist_type: str
    observed_specialist_types: list[str]
    observation_count: int
    minimum_occurrences: int
    outcome_statuses: list[str]
    memory_causality_statuses: list[str]
    observation_refs: list[str]
    evidence_refs: list[str]
    rationale: str
    proposed_tests: list[str]
    rollback_plan_ref: str
    risk_level: str
    blockers: list[str]
    generated_at: Timestamp
    human_review_required: bool = True
    routing_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class RoutingAdaptationReportContract:
    report_id: str
    report_status: str
    observation_count: int
    route_match_count: int
    route_mismatch_count: int
    candidate_count: int
    candidates: list[RoutingAdaptationCandidateContract]
    conflict_flags: list[str]
    evidence_refs: list[str]
    blockers: list[str]
    generated_at: Timestamp
    read_only: bool = True
    human_review_required: bool = True
    routing_write_allowed: bool = False
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class KnowledgeSourceEvidenceContract:
    source_ref: str
    domain_name: str
    source_kind: str
    retrieved_at: Timestamp
    provenance_status: str
    freshness_status: str
    conflict_status: str
    confidence_status: str = "unverified"
    published_at: Timestamp | None = None
    reviewed_at: Timestamp | None = None
    valid_until: Timestamp | None = None
    conflict_refs: list[str] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)


@dataclass
class KnowledgeEvidenceGovernanceContract:
    assessment_id: str
    status: str
    use_mode: str
    provenance_status: str
    freshness_status: str
    conflict_status: str
    source_refs: list[str]
    conditions: list[str]
    blockers: list[str]
    uncertainty_notes: list[str]
    timestamp: Timestamp
    human_review_required: bool = False
    request_decision_mutation_allowed: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class CapabilityReadinessContract:
    capability_id: str
    capability_name: str
    source_status: str
    scope_status: str
    readiness_status: str
    score: int
    target: str
    dependencies: str
    next_slice: str
    evidence_refs: list[str]
    blockers: list[str] = field(default_factory=list)


@dataclass
class RegressionReadinessReportContract:
    report_id: str
    status: str
    overall_score: int
    capability_counts: dict[str, int]
    capability_results: list[CapabilityReadinessContract]
    gate_mode: str
    gate_status: str
    test_status: str
    document_status: str
    backlog_status: str
    status_drift: list[str]
    blockers: list[str]
    warnings: list[str]
    evidence_refs: list[str]
    generated_at: Timestamp
    next_ready_item: str | None = None
    longitudinal_learning_status: str = "not_evaluated"
    longitudinal_regression_flags: list[str] = field(default_factory=list)
    longitudinal_learning_evidence_ref: str | None = None
    longitudinal_learning_authority_safe: bool = True
    read_only: bool = True
    autonomous_release_allowed: bool = False


@dataclass
class LearningVersionTargetContract:
    target_id: str
    capability_kind: str
    capability_id: str
    version_ref: str
    lifecycle_status: str
    review_status: str
    runtime_status: str
    evidence_refs: list[str]
    rollback_plan_ref: str | None
    rollback_status: str
    observed_at: Timestamp
    baseline_version_ref: str | None = None
    human_review_required: bool = True
    runtime_activation_allowed: bool = False
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class LearningOutcomeObservationContract:
    observation_id: str
    capability_kind: str
    capability_id: str
    version_ref: str
    source_kind: str
    observed_at: Timestamp
    success: bool
    success_score: float
    rework_count: int
    evidence_refs: list[str]
    mission_id: str | None = None
    request_id: str | None = None
    workflow_profile: str | None = None
    route: str | None = None
    feedback_assessment: str | None = None
    feedback_rating: int | None = None
    regression_flags: list[str] = field(default_factory=list)
    rollback_observed: bool = False
    human_review_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class LongitudinalVersionMetricsContract:
    capability_kind: str
    capability_id: str
    version_ref: str
    lifecycle_status: str
    runtime_status: str
    observation_count: int
    runtime_observation_count: int
    offline_observation_count: int
    mission_count: int
    success_rate: float
    average_success_score: float
    rework_rate: float
    feedback_count: int
    helpful_feedback_rate: float
    regression_count: int
    rollback_count: int
    trend_status: str
    evidence_refs: list[str]
    blockers: list[str]
    baseline_version_ref: str | None = None
    success_rate_delta: float | None = None
    rework_rate_delta: float | None = None
    read_only: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class LongitudinalLearningReportContract:
    report_id: str
    report_status: str
    minimum_observations: int
    target_count: int
    observation_count: int
    observed_version_count: int
    version_metrics: list[LongitudinalVersionMetricsContract]
    missing_evidence_refs: list[str]
    regression_flags: list[str]
    rollback_refs: list[str]
    limitations: list[str]
    evidence_refs: list[str]
    generated_at: Timestamp
    period_start: Timestamp | None = None
    period_end: Timestamp | None = None
    read_only: bool = True
    human_review_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class DailyOperatorMissionOutcomeContract:
    mission_id: MissionId
    work_item_event_count: int
    observed_work_item_count: int
    completed_work_item_count: int
    reworked_work_item_count: int
    artifact_event_count: int
    observed_artifact_count: int
    resume_count: int
    feedback_count: int
    helpful_feedback_count: int
    time_to_next_action_observation_count: int
    completion_rate: float | None
    rework_rate: float | None
    helpful_feedback_rate: float | None
    average_time_to_next_action_seconds: float | None
    stale_open_loop_count: int | None
    evidence_refs: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class DailyOperatorUtilityReportContract:
    report_id: str
    report_status: str
    period_start: Timestamp
    period_end: Timestamp
    generated_at: Timestamp
    mission_count: int
    mission_metrics: list[DailyOperatorMissionOutcomeContract]
    event_count: int
    work_item_event_count: int
    observed_work_item_count: int
    completed_work_item_count: int
    reworked_work_item_count: int
    completion_rate: float | None
    rework_rate: float | None
    artifact_event_count: int
    observed_artifact_count: int
    resume_count: int
    stale_open_loop_count: int | None
    feedback_count: int
    feedback_mission_count: int
    feedback_coverage: float | None
    helpful_feedback_count: int
    helpful_feedback_rate: float | None
    time_to_next_action_observation_count: int
    average_time_to_next_action_seconds: float | None
    limitations: list[str]
    evidence_refs: list[str]
    time_to_next_action_definition: str = (
        "open_loop_resumed_to_next_recorded_work_or_artifact_transition"
    )
    saved_time_claim_status: str = "not_claimed_without_controlled_baseline"
    read_only: bool = True
    memory_write_mode: str = "read_only"
    autonomous_action_allowed: bool = False


@dataclass
class SpecialistBoundaryContract:
    specialist_type: str
    runtime_scope: str
    user_visibility: str
    response_channel: str
    tool_access_mode: str
    memory_write_mode: str
    operation_mode: str
    allowed_tool_classes: list[str] = field(default_factory=list)
    blocked_tool_classes: list[str] = field(default_factory=list)


@dataclass
class SpecialistSharedMemoryContextContract:
    specialist_type: str
    sharing_mode: str
    continuity_mode: str
    shared_memory_brief: str
    write_policy: str
    consumer_mode: str = "baseline_shared_context"
    source_mission_id: MissionId | None = None
    source_mission_goal: str | None = None
    mission_context_brief: str | None = None
    domain_context_brief: str | None = None
    continuity_context_brief: str | None = None
    consumer_profile: str | None = None
    consumer_objective: str | None = None
    expected_deliverables: list[str] = field(default_factory=list)
    telemetry_focus: list[str] = field(default_factory=list)
    related_mission_ids: list[MissionId] = field(default_factory=list)
    memory_refs: list[str] = field(default_factory=list)
    memory_class_policies: dict[str, dict[str, object]] = field(default_factory=dict)
    consumed_memory_classes: list[str] = field(default_factory=list)
    memory_write_policies: dict[str, str] = field(default_factory=dict)
    semantic_focus: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    last_recommendation: str | None = None
    semantic_memory_source: str | None = None
    procedural_memory_source: str | None = None
    semantic_memory_effects: list[str] = field(default_factory=list)
    procedural_memory_effects: list[str] = field(default_factory=list)
    semantic_memory_lifecycle: str | None = None
    procedural_memory_lifecycle: str | None = None
    semantic_memory_state: str | None = None
    procedural_memory_state: str | None = None
    memory_lifecycle_status: str | None = None
    memory_review_status: str | None = None
    memory_maintenance_status: str | None = None
    memory_maintenance_reason: str | None = None
    memory_maintenance_fallback_mode: str | None = None
    context_compaction_status: str | None = None
    cross_session_recall_status: str | None = None
    memory_consolidation_status: str | None = None
    memory_fixation_status: str | None = None
    memory_archive_status: str | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_refs: list[str] = field(default_factory=list)
    procedural_artifact_version: int | None = None
    procedural_artifact_summary: str | None = None
    memory_corpus_status: str | None = None
    memory_retention_pressure: str | None = None
    memory_corpus_summary: dict[str, int] = field(default_factory=dict)
    domain_mission_link_reason: str | None = None
    recurrent_context_status: str = "not_applicable"
    recurrent_interaction_count: int = 0
    recurrent_context_brief: str | None = None
    recurrent_domain_focus: list[str] = field(default_factory=list)
    recurrent_memory_refs: list[str] = field(default_factory=list)
    recurrent_continuity_modes: list[str] = field(default_factory=list)


@dataclass
class SpecialistInvocationContract:
    invocation_id: str
    specialist_type: str
    requested_by_service: str
    role: str
    task_focus: str
    entry_summary: str
    handoff_inputs: list[str]
    expected_outputs: list[str]
    boundary: SpecialistBoundaryContract
    session_id: SessionId | None = None
    mission_id: MissionId | None = None
    shared_memory_context: SpecialistSharedMemoryContextContract | None = None
    linked_domain: str | None = None
    selection_mode: str = "standard"


@dataclass
class SpecialistSelectionContract:
    specialist_type: str
    selection_status: str
    selection_score: float
    rationale: str
    requires_governance_review: bool = False
    invocation_id: str | None = None
    linked_domain: str | None = None
    selection_mode: str = "standard"


@dataclass
class SpecialistContributionContract:
    specialist_type: str
    role: str
    focus: str
    findings: list[str]
    recommendation: str
    confidence: float
    invocation_id: str | None = None
    output_hints: list[str] = field(default_factory=list)
    handoff_channel: str | None = None


@dataclass
class EcosystemOperationalStateContract:
    ecosystem_state_status: str
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    state_summary: str | None = None


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
    mind_domain_specialist_contract_status: str | None = None
    mind_domain_specialist_contract_summary: str | None = None
    mind_domain_specialist_contract_chain: str | None = None
    mind_domain_specialist_active_specialist: str | None = None
    mind_domain_specialist_override_mode: str | None = None
    mind_domain_specialist_fallback_mode: str | None = None
    mind_domain_specialist_consumer_mode: str | None = None
    mind_domain_specialist_framing_mode: str | None = None
    mind_domain_specialist_continuity_mode: str | None = None
    success_criteria: list[str] = field(default_factory=list)
    smallest_safe_next_action: str | None = None
    requires_human_validation: bool = False
    capability_decision_status: str | None = None
    capability_decision_objective: str | None = None
    capability_decision_reason: str | None = None
    capability_decision_selected_mode: str | None = None
    capability_decision_authorization_status: str | None = None
    capability_decision_fallback_mode: str | None = None
    capability_decision_tool_class: str | None = None
    capability_decision_handoff_mode: str | None = None
    capability_decision_eligible_capabilities: list[str] = field(default_factory=list)
    capability_decision_selected_capabilities: list[str] = field(default_factory=list)
    request_identity_status: str | None = None
    request_active_mission: str | None = None
    request_executive_posture: str | None = None
    request_authority_level: str | None = None
    request_risk_profile: str | None = None
    request_reversibility_mode: str | None = None
    request_confirmation_mode: str | None = None
    request_identity_summary: str | None = None
    request_identity_policy_refs: list[str] = field(default_factory=list)
    requested_autonomy_level: str | None = None
    max_autonomy_level: str | None = None
    effective_autonomy_level: str | None = None
    autonomy_ladder_status: str | None = None
    max_autonomy_capability_mode: str | None = None
    autonomy_human_confirmation_required: bool = True
    autonomy_confirmation_mode: str | None = None
    autonomy_action_kind: str | None = None
    adapter_action_request: AdapterActionRequestContract | None = None
    autonomy_validation_errors: list[str] = field(default_factory=list)
    autonomy_allowed_runtime_actions: list[str] = field(default_factory=list)
    autonomy_blocked_runtime_actions: list[str] = field(default_factory=list)
    autonomy_policy_refs: list[str] = field(default_factory=list)
    autonomy_summary: str | None = None
    autonomy_automatic_promotion_allowed: bool = False
    autonomy_core_mutation_allowed: bool = False
    adaptive_intervention_status: str | None = None
    adaptive_intervention_reason: str | None = None
    adaptive_intervention_trigger: str | None = None
    adaptive_intervention_selected_action: str | None = None
    adaptive_intervention_expected_effect: str | None = None
    adaptive_intervention_effects: list[str] = field(default_factory=list)
    session_id: SessionId | None = None
    mission_id: MissionId | None = None
    risk_hint: RiskLevel | None = None
    domain_hints: list[str] = field(default_factory=list)
    canonical_domain_hints: list[str] = field(default_factory=list)
    primary_canonical_domain: str | None = None
    specialist_hints: list[str] = field(default_factory=list)
    tool_hints: list[str] = field(default_factory=list)
    workflow_profile: str | None = None
    workflow_domain_route: str | None = None
    workflow_objective: str | None = None
    workflow_expected_deliverables: list[str] = field(default_factory=list)
    workflow_telemetry_focus: list[str] = field(default_factory=list)
    workflow_success_focus: str | None = None
    workflow_response_focus: str | None = None
    workflow_state: str | None = None
    workflow_governance_mode: str | None = None
    workflow_steps: list[str] = field(default_factory=list)
    workflow_checkpoints: list[str] = field(default_factory=list)
    workflow_decision_points: list[str] = field(default_factory=list)
    workflow_checkpoint_state: dict[str, str] = field(default_factory=dict)
    workflow_resume_point: str | None = None
    workflow_resume_status: str | None = None
    workflow_resume_eligible: bool = False
    workflow_policy_decision: WorkflowPolicyDecisionContract | None = None
    workflow_lifecycle_transition: WorkflowLifecycleTransitionContract | None = None
    workflow_lifecycle_resolution_status: str = "static_baseline"
    workflow_lifecycle_resolution_reasons: list[str] = field(default_factory=list)
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    surface_id: str | None = None
    surface_kind: str | None = None
    surface_session_id: str | None = None
    surface_capability_scope: list[str] = field(default_factory=list)
    operator_identity_ref: str | None = None
    canonical_user_ref: str | None = None
    surface_continuity_status: str = "single_surface"
    deadline_hint: str | None = None
    priority_hint: str | None = None
    artifact_destination: str | None = None
    receipt_id: str | None = None
    claim_id: str | None = None
    origin_request_id: RequestId | None = None
    action_fingerprint: str | None = None
    intent_fingerprint: str | None = None
    claimed_at: Timestamp | None = None


@dataclass
class OperationResultContract:
    operation_id: OperationId
    status: OperationStatus
    outputs: list[str]
    timestamp: Timestamp
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    checkpoints: list[str] = field(default_factory=list)
    workflow_domain_route: str | None = None
    workflow_state: str | None = None
    workflow_completed_steps: list[str] = field(default_factory=list)
    workflow_decisions: list[str] = field(default_factory=list)
    workflow_checkpoint_state: dict[str, str] = field(default_factory=dict)
    workflow_pending_checkpoints: list[str] = field(default_factory=list)
    workflow_resume_point: str | None = None
    workflow_resume_status: str | None = None
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    surface_id: str | None = None
    surface_kind: str | None = None
    surface_session_id: str | None = None
    surface_capability_scope: list[str] = field(default_factory=list)
    operator_identity_ref: str | None = None
    canonical_user_ref: str | None = None
    surface_continuity_status: str = "single_surface"
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
    recommended_reason: str | None = None
    active_priority_score: float | None = None
    related_priority_score: float | None = None


@dataclass
class ContinuityCheckpointContract:
    checkpoint_id: str
    session_id: SessionId
    continuity_action: str
    checkpoint_status: str
    checkpoint_summary: str
    updated_at: UpdatedAt
    mission_id: MissionId | None = None
    continuity_source: str | None = None
    target_mission_id: MissionId | None = None
    target_goal: str | None = None
    origin_request_id: RequestId | None = None
    replay_summary: str | None = None
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)


@dataclass
class ContinuityReplayContract:
    checkpoint_id: str
    session_id: SessionId
    replay_status: str
    recovery_mode: str
    resume_point: str
    checkpoint_status: str
    continuity_action: str
    updated_at: UpdatedAt
    mission_id: MissionId | None = None
    target_mission_id: MissionId | None = None
    target_goal: str | None = None
    origin_request_id: RequestId | None = None
    replay_summary: str | None = None
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    requires_manual_resume: bool = False


@dataclass
class ContinuityPauseContract:
    pause_id: str
    session_id: SessionId
    checkpoint_id: str
    pause_status: str
    recovery_mode: str
    resume_point: str
    pause_reason: str
    issued_at: UpdatedAt
    resolved_at: UpdatedAt | None = None
    resolution_status: str | None = None
    resolved_by: str | None = None
    resolution_note: str | None = None
    requires_human_input: bool = True


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
    related_artifacts: list[dict[str, object]] = field(default_factory=list)
    recent_plan_steps: list[str] = field(default_factory=list)
    last_recommendation: str | None = None
    semantic_brief: str | None = None
    semantic_focus: list[str] = field(default_factory=list)
    identity_continuity_brief: str | None = None
    open_loops: list[str] = field(default_factory=list)
    open_loop_states: list[OpenLoopStateContract] = field(default_factory=list)
    last_decision_frame: str | None = None
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    work_items: list[WorkItemStateContract] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    artifact_states: list[ArtifactLifecycleStateContract] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    priority_level: str | None = None
    owner_context: str | None = None
    completion_criteria: list[str] = field(default_factory=list)


@dataclass
class DailyWorkspaceMissionContract:
    mission_id: MissionId
    mission_goal: str
    mission_status: MissionStatus
    objective_status: str
    updated_at: UpdatedAt
    freshness_status: str
    operator_attention_status: str
    next_action_status: str
    project_ref: str | None = None
    objective_ref: str | None = None
    next_action_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    active_work_items: list[str] = field(default_factory=list)
    ordered_work_item_refs: list[str] = field(default_factory=list)
    executable_work_item_refs: list[str] = field(default_factory=list)
    blocked_work_item_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    pending_decision_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    freshness_age_hours: float | None = None


@dataclass
class DailyOperatorWorkspaceContract:
    workspace_id: str
    workspace_status: str
    generated_at: Timestamp
    missions: list[DailyWorkspaceMissionContract]
    mission_count: int
    active_objective_count: int
    active_work_item_count: int
    active_artifact_count: int
    open_checkpoint_count: int
    pending_review_count: int
    stale_mission_count: int
    pending_evolution_review_refs: list[str] = field(default_factory=list)
    pending_memory_review_refs: list[str] = field(default_factory=list)
    next_decision_refs: list[str] = field(default_factory=list)
    next_operator_decision: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    freshness_policy: str = "fresh_24h_aging_72h_stale_after_72h"
    ordering_policy: str = "updated_at_desc_no_priority_inference"
    memory_write_mode: str = "read_only"
    read_only: bool = True
    autonomous_resume_allowed: bool = False
    autonomous_scheduling_allowed: bool = False


@dataclass
class LongHorizonGoalStrategyContract:
    mission_id: MissionId
    strategy_status: str
    strategy_summary: str
    milestone_refs: list[str] = field(default_factory=list)
    risk_refs: list[str] = field(default_factory=list)
    memory_anchor_refs: list[str] = field(default_factory=list)
    next_action_ref: str | None = None
    evidence_refs: list[str] = field(default_factory=list)
    memory_write_mode: str = "read_only"
    autonomous_scheduling_allowed: bool = False
    generated_from_state_refs: list[str] = field(default_factory=list)


@dataclass
class MissionProgressReportContract:
    report_id: str
    mission_id: MissionId
    report_status: str
    progress_summary: str
    report_text: str
    mission_goal: str
    mission_status: str
    objective_status: str
    generated_at: Timestamp
    work_item_refs: list[str] = field(default_factory=list)
    active_work_items: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    milestone_refs: list[str] = field(default_factory=list)
    risk_refs: list[str] = field(default_factory=list)
    memory_influence_refs: list[str] = field(default_factory=list)
    learning_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    pending_decisions: list[str] = field(default_factory=list)
    latest_experience_id: str | None = None
    latest_experience_outcome: str | None = None
    latest_reflection_id: str | None = None
    latest_reflection_status: str | None = None
    operator_usefulness_status: str = "insufficient_signal"
    next_action_ref: str | None = None
    memory_write_mode: str = "read_only"
    autonomous_execution_allowed: bool = False


@dataclass
class MissionRuntimeStateContract:
    mission_id: MissionId
    mission_goal: str
    mission_status: MissionStatus
    continuity_action: str | None
    continuity_source: str | None
    updated_at: UpdatedAt
    continuity_target_mission_id: MissionId | None = None
    continuity_target_goal: str | None = None
    continuity_recommendation: str | None = None
    continuity_replay_status: str | None = None
    continuity_recovery_mode: str | None = None
    continuity_resume_point: str | None = None
    requires_manual_resume: bool = False
    primary_route: str | None = None
    workflow_profile: str | None = None
    active_tasks: list[str] = field(default_factory=list)
    open_loops: list[str] = field(default_factory=list)
    last_recommendation: str | None = None
    related_mission_id: MissionId | None = None
    related_mission_goal: str | None = None
    ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    ecosystem_state_summary: str | None = None
    project_ref: str | None = None
    objective_ref: str | None = None
    work_item_refs: list[str] = field(default_factory=list)
    checkpoint_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    objective_status: str | None = None
    next_action_ref: str | None = None
    linked_surface_ids: list[str] = field(default_factory=list)
    active_surface_id: str | None = None
    last_surface_id: str | None = None
    surface_continuity_status: str | None = None
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    runtime_mode: str | None = None


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
class SandboxToReleaseChecklistContract:
    checklist_id: str
    evolution_proposal_id: EvolutionProposalId
    release_scope: str
    checklist_status: str
    human_review_status: str
    required_gates: list[str]
    evidence_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None
    blockers: list[str] = field(default_factory=list)
    candidate_type: str | None = None
    candidate_identity_ref: str | None = None
    candidate_version: str | None = None
    sandbox_eval_ref: str | None = None
    sandbox_eval_status: str | None = None
    baseline_version_ref: str | None = None
    rollback_verification_ref: str | None = None
    rollback_verification_status: str | None = None
    sandbox_required: bool = True
    release_gate_required: bool = True
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class PromotionGateDecisionContract:
    promotion_gate_id: str
    checklist_id: str
    evolution_proposal_id: EvolutionProposalId
    release_scope: str
    gate_status: str
    decision: str
    release_conclusion: str
    required_gates: list[str]
    completed_gates: list[str]
    missing_gates: list[str]
    evidence_refs: list[str]
    blockers: list[str]
    human_review_status: str
    promotion_eligible: bool
    human_decision_required: bool = True
    promotion_authorized: bool = False
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


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
    optimization_scope: str | None = None
    optimization_target_kind: str | None = None
    optimization_candidate_status: str | None = None
    optimization_safety_status: str | None = None
    optimization_blockers: list[str] = field(default_factory=list)
    candidate_refs: list[str] = field(default_factory=list)
    refinement_vectors: list[dict[str, object]] = field(default_factory=list)
    evaluation_matrix: dict[str, dict[str, object]] = field(default_factory=dict)
    selection_criteria: dict[str, object] = field(default_factory=dict)
    strategy_context: dict[str, object] = field(default_factory=dict)


@dataclass
class EvolutionReviewQueueItemContract:
    review_item_id: str
    evolution_proposal_id: EvolutionProposalId
    proposal_type: str
    review_status: str
    review_reason: str
    requires_human_review: bool
    requires_sandbox: bool
    risk_hint: str | None = None
    target_scope: str | None = None
    candidate_refs: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None


@dataclass
class EvolutionReviewDecisionContract:
    review_decision_id: str
    evolution_proposal_id: EvolutionProposalId
    review_status: str
    decision: str
    operator_ref: str
    timestamp: Timestamp
    evidence_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None
    risk_acceptance: str | None = None
    review_notes: list[str] = field(default_factory=list)
    candidate_identity_ref: str | None = None
    candidate_version: str | None = None
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryLifecycleCandidateContract:
    candidate_id: str
    maintenance_action: str
    target_scope: str
    target_refs: list[str]
    reason: str
    evidence_refs: list[str]
    rollback_plan_ref: str
    review_status: str
    execution_status: str
    generated_at: Timestamp
    last_review_decision_id: str | None = None
    last_reviewed_by: str | None = None
    last_reviewed_at: Timestamp | None = None
    human_review_required: bool = True
    automatic_execution_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryLifecycleGovernanceAssessmentContract:
    assessment_id: str
    candidate_id: str
    maintenance_action: str
    decision_action: str
    status: str
    timestamp: Timestamp
    blockers: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    policy_refs: list[str] = field(default_factory=list)
    human_review_required: bool = True
    execution_authorized: bool = False
    automatic_execution_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class MemoryLifecycleReviewDecisionContract:
    review_decision_id: str
    candidate_id: str
    maintenance_action: str
    decision_action: str
    review_status: str
    operator_ref: str
    evidence_refs: list[str]
    rollback_plan_ref: str
    governance_assessment_id: str
    timestamp: Timestamp
    review_notes: list[str] = field(default_factory=list)
    execution_authorized: bool = False
    automatic_execution_allowed: bool = False
    core_mutation_allowed: bool = False


@dataclass
class ReviewedLearningGuidanceContract:
    guidance_id: str
    source_review_decision_id: str
    evolution_proposal_id: EvolutionProposalId
    review_status: str
    route: str
    workflow_profile: str
    domain: str
    guidance_summary: str
    allowed_usage: list[str]
    evidence_refs: list[str]
    rollback_plan_ref: str | None
    timestamp: Timestamp
    expires_at: Timestamp | None = None
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


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
    optimization_scope: str | None = None
    optimization_target_kind: str | None = None
    optimization_readiness: str | None = None
    optimization_release_status: str | None = None
    optimization_safety_status: str | None = None
    optimization_blockers: list[str] = field(default_factory=list)
    baseline_label: str | None = None
    candidate_label: str | None = None
    selected_candidate_label: str | None = None
    selection_criteria: dict[str, object] = field(default_factory=dict)
    baseline_metrics: dict[str, float] = field(default_factory=dict)
    candidate_metrics: dict[str, float] = field(default_factory=dict)
    metric_deltas: dict[str, float] = field(default_factory=dict)
