from shared.contracts import (
    ArtifactLifecycleStateContract,
    AutonomyLadderContract,
    DailyOperatorWorkspaceContract,
    DailyWorkspaceMissionContract,
    DeliberativePlanContract,
    EvolutionReviewDecisionContract,
    EvolutionReviewQueueItemContract,
    ExperienceRecordContract,
    GovernanceDecisionContract,
    InputContract,
    LearningOutcomeObservationContract,
    LearningVersionTargetContract,
    LongHorizonGoalStrategyContract,
    LongitudinalLearningReportContract,
    LongitudinalVersionMetricsContract,
    MemoryLifecycleCandidateContract,
    MemoryLifecycleGovernanceAssessmentContract,
    MemoryLifecycleReviewDecisionContract,
    MissionProgressReportContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    ProjectObjectiveContinuityContract,
    PromotionGateDecisionContract,
    RecurringPatternEvidenceContract,
    RecurringPatternReportContract,
    ReviewedLearningGuidanceContract,
    SandboxToReleaseChecklistContract,
    SkillCandidateContract,
    SkillEvolutionOperatorItemContract,
    SkillEvolutionOperatorViewContract,
    SkillMiningRequestContract,
    SkillMiningResultContract,
    SkillSandboxCaseResultContract,
    SkillSandboxEvalContract,
    SurfaceIdentityContract,
    TechnologyAbsorptionCandidateContract,
    WorkflowEvolutionBuildResultContract,
    WorkflowEvolutionRequestContract,
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkItemStateContract,
)
from shared.events import INTERNAL_EVENT_NAMES
from shared.schemas import (
    ARTIFACT_LIFECYCLE_STATE_SCHEMA,
    AUTONOMY_LADDER_SCHEMA,
    DAILY_OPERATOR_WORKSPACE_SCHEMA,
    DAILY_WORKSPACE_MISSION_SCHEMA,
    DELIBERATIVE_PLAN_SCHEMA,
    EVOLUTION_REVIEW_DECISION_SCHEMA,
    EVOLUTION_REVIEW_QUEUE_ITEM_SCHEMA,
    EXPERIENCE_RECORD_SCHEMA,
    INPUT_SCHEMA,
    LEARNING_OUTCOME_OBSERVATION_SCHEMA,
    LEARNING_VERSION_TARGET_SCHEMA,
    LONG_HORIZON_GOAL_STRATEGY_SCHEMA,
    LONGITUDINAL_LEARNING_REPORT_SCHEMA,
    LONGITUDINAL_VERSION_METRICS_SCHEMA,
    MEMORY_LIFECYCLE_CANDIDATE_SCHEMA,
    MEMORY_LIFECYCLE_GOVERNANCE_ASSESSMENT_SCHEMA,
    MEMORY_LIFECYCLE_REVIEW_DECISION_SCHEMA,
    MISSION_PROGRESS_REPORT_SCHEMA,
    OPERATOR_FEEDBACK_SCHEMA,
    POST_TASK_REFLECTION_SCHEMA,
    PROCEDURAL_PLAYBOOK_CANDIDATE_SCHEMA,
    PROJECT_OBJECTIVE_CONTINUITY_SCHEMA,
    PROMOTION_GATE_DECISION_SCHEMA,
    RECURRING_PATTERN_EVIDENCE_SCHEMA,
    RECURRING_PATTERN_REPORT_SCHEMA,
    REGRESSION_READINESS_REPORT_SCHEMA,
    REVIEWED_LEARNING_GUIDANCE_SCHEMA,
    SANDBOX_TO_RELEASE_CHECKLIST_SCHEMA,
    SKILL_CANDIDATE_SCHEMA,
    SKILL_EVOLUTION_OPERATOR_ITEM_SCHEMA,
    SKILL_EVOLUTION_OPERATOR_VIEW_SCHEMA,
    SKILL_MINING_REQUEST_SCHEMA,
    SKILL_MINING_RESULT_SCHEMA,
    SKILL_SANDBOX_CASE_RESULT_SCHEMA,
    SKILL_SANDBOX_EVAL_SCHEMA,
    SURFACE_IDENTITY_SCHEMA,
    TECHNOLOGY_ABSORPTION_CANDIDATE_SCHEMA,
    WORK_ITEM_STATE_SCHEMA,
    WORKFLOW_EVOLUTION_BUILD_RESULT_SCHEMA,
    WORKFLOW_EVOLUTION_REQUEST_SCHEMA,
    WORKFLOW_PROFILE_VERSION_REGISTRY_SCHEMA,
    WORKFLOW_PROFILE_VERSION_SCHEMA,
)
from shared.state import SYSTEM_IDENTITY
from shared.types import (
    ChannelType,
    GovernanceCheckId,
    GovernanceDecisionId,
    InputType,
    PermissionDecision,
    RequestId,
    RiskLevel,
    SessionId,
)


def test_input_schema_matches_contract_name() -> None:
    assert INPUT_SCHEMA.contract_name == "InputContract"


def test_input_contract_can_be_instantiated() -> None:
    contract = InputContract(
        request_id=RequestId("req-1"),
        session_id=SessionId("sess-1"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="hello",
        timestamp="2026-03-16T00:00:00Z",
    )
    assert contract.content == "hello"


def test_longitudinal_learning_contracts_are_read_only_shared_schemas() -> None:
    target = LearningVersionTargetContract(
        target_id="learning-target://test",
        capability_kind="workflow",
        capability_id="software_change_workflow",
        version_ref="workflow-version://software-change/1.0.0",
        lifecycle_status="candidate_inactive",
        review_status="needs_review",
        runtime_status="inactive_candidate",
        evidence_refs=["eval://workflow/1.0.0"],
        rollback_plan_ref="rollback://workflow/1.0.0",
        rollback_status="available",
        observed_at="2026-07-16T12:00:00Z",
    )
    observation = LearningOutcomeObservationContract(
        observation_id="learning-observation://offline/test",
        capability_kind="workflow",
        capability_id="software_change_workflow",
        version_ref=target.version_ref,
        source_kind="offline_eval",
        observed_at="2026-07-16T12:00:00Z",
        success=True,
        success_score=1.0,
        rework_count=0,
        evidence_refs=["eval://workflow/1.0.0"],
    )
    metrics = LongitudinalVersionMetricsContract(
        capability_kind="workflow",
        capability_id="software_change_workflow",
        version_ref=target.version_ref,
        lifecycle_status=target.lifecycle_status,
        runtime_status=target.runtime_status,
        observation_count=1,
        runtime_observation_count=0,
        offline_observation_count=1,
        mission_count=0,
        success_rate=1.0,
        average_success_score=1.0,
        rework_rate=0.0,
        feedback_count=0,
        helpful_feedback_rate=0.0,
        regression_count=0,
        rollback_count=0,
        trend_status="insufficient_evidence",
        evidence_refs=observation.evidence_refs,
        blockers=[],
    )
    report = LongitudinalLearningReportContract(
        report_id="longitudinal-learning-report://test",
        report_status="insufficient_evidence",
        minimum_observations=2,
        target_count=1,
        observation_count=1,
        observed_version_count=1,
        version_metrics=[metrics],
        missing_evidence_refs=[target.version_ref],
        regression_flags=[],
        rollback_refs=[],
        limitations=["measurement_does_not_authorize_promotion"],
        evidence_refs=observation.evidence_refs,
        generated_at="2026-07-16T12:00:00Z",
    )

    assert LEARNING_VERSION_TARGET_SCHEMA.contract_name == type(target).__name__
    assert LEARNING_OUTCOME_OBSERVATION_SCHEMA.contract_name == type(observation).__name__
    assert LONGITUDINAL_VERSION_METRICS_SCHEMA.contract_name == type(metrics).__name__
    assert LONGITUDINAL_LEARNING_REPORT_SCHEMA.contract_name == type(report).__name__
    assert report.read_only is True
    assert report.promotion_authorized is False
    assert report.automatic_promotion_allowed is False
    assert report.core_mutation_allowed is False


def test_regression_readiness_schema_includes_longitudinal_closure_fields() -> None:
    assert "longitudinal_learning_status" in (
        REGRESSION_READINESS_REPORT_SCHEMA.optional_fields
    )
    assert "longitudinal_regression_flags" in (
        REGRESSION_READINESS_REPORT_SCHEMA.optional_fields
    )
    assert "longitudinal_learning_authority_safe" in (
        REGRESSION_READINESS_REPORT_SCHEMA.optional_fields
    )


def test_surface_identity_contract_declares_minimum_continuity_fields() -> None:
    contract = SurfaceIdentityContract(
        surface_id="surface://jarvis_console",
        surface_kind="console",
        surface_session_id="sess-1",
        surface_capability_scope=["text_input", "core_orchestrated_response"],
        operator_identity_ref="operator://local_console",
        canonical_user_ref="user://local_operator",
    )

    assert contract.surface_continuity_status == "single_surface"
    assert SURFACE_IDENTITY_SCHEMA.contract_name == "SurfaceIdentityContract"
    assert "surface_id" in INPUT_SCHEMA.optional_fields


def test_project_objective_continuity_contract_declares_minimum_fields() -> None:
    contract = ProjectObjectiveContinuityContract(
        project_ref="project://jarvis",
        objective_ref="objective://jarvis/persistent-objectives",
        work_item_refs=["work-item://mb-110"],
        checkpoint_refs=["checkpoint://contract-ready"],
        artifact_refs=["artifact://plan.md"],
        objective_status="active",
        next_action_ref="next-action://define-contract",
    )

    assert contract.objective_status == "active"
    assert contract.work_item_refs == ["work-item://mb-110"]
    assert PROJECT_OBJECTIVE_CONTINUITY_SCHEMA.contract_name == (
        "ProjectObjectiveContinuityContract"
    )
    assert "project_ref" in INPUT_SCHEMA.optional_fields


def test_daily_workspace_contract_is_read_only_and_non_scheduling() -> None:
    mission = DailyWorkspaceMissionContract(
        mission_id="mission-daily-workspace",
        mission_goal="Resume the governed daily loop",
        mission_status="active",
        objective_status="active",
        updated_at="2026-07-17T09:00:00+00:00",
        freshness_status="fresh",
        operator_attention_status="ready",
        next_action_status="ready",
        next_action_ref="next-action://daily/review",
    )
    workspace = DailyOperatorWorkspaceContract(
        workspace_id="daily-workspace://test",
        workspace_status="ready_for_next_action",
        generated_at="2026-07-17T10:00:00+00:00",
        missions=[mission],
        mission_count=1,
        active_objective_count=1,
        active_work_item_count=0,
        active_artifact_count=0,
        open_checkpoint_count=0,
        pending_review_count=0,
        stale_mission_count=0,
        next_operator_decision="continue_mission:mission-daily-workspace",
    )

    assert DAILY_WORKSPACE_MISSION_SCHEMA.contract_name == type(mission).__name__
    assert DAILY_OPERATOR_WORKSPACE_SCHEMA.contract_name == type(workspace).__name__
    assert workspace.read_only is True
    assert workspace.memory_write_mode == "read_only"
    assert workspace.autonomous_resume_allowed is False
    assert workspace.autonomous_scheduling_allowed is False


def test_technology_absorption_candidate_contract_is_subordinate_by_default() -> None:
    contract = TechnologyAbsorptionCandidateContract(
        candidate_ref="tech-candidate://openai-agents-sdk/handoff-adapters",
        technology_name="OpenAI Agents SDK",
        absorption_class="sandbox_experiment",
        target_gap_refs=["TA-005"],
        hypothesis="Handoff adapter semantics can improve edge tracing.",
        expected_gain="Clearer bounded handoff evidence without replacing the core.",
    )

    assert contract.requested_core_role == "subordinate"
    assert contract.sandbox_required is True
    assert contract.human_review_required is True
    assert TECHNOLOGY_ABSORPTION_CANDIDATE_SCHEMA.contract_name == (
        "TechnologyAbsorptionCandidateContract"
    )


def test_governance_decision_uses_canonical_enums() -> None:
    decision = GovernanceDecisionContract(
        decision_id=GovernanceDecisionId("decision-1"),
        governance_check_id=GovernanceCheckId("check-1"),
        risk_level=RiskLevel.MODERATE,
        decision=PermissionDecision.ALLOW,
        justification="safe enough",
        timestamp="2026-03-16T00:00:00Z",
    )
    assert decision.decision == PermissionDecision.ALLOW


def test_internal_event_names_include_governance_blocked() -> None:
    assert "governance_blocked" in INTERNAL_EVENT_NAMES
    assert "knowledge_retrieved" in INTERNAL_EVENT_NAMES
    assert "surface_identity_declared" in INTERNAL_EVENT_NAMES
    assert "objective_state_declared" in INTERNAL_EVENT_NAMES
    assert "objective_state_inspected" in INTERNAL_EVENT_NAMES
    assert "long_horizon_goal_strategy_declared" in INTERNAL_EVENT_NAMES
    assert "mission_progress_report_generated" in INTERNAL_EVENT_NAMES
    assert "work_item_state_changed" in INTERNAL_EVENT_NAMES
    assert "artifact_lifecycle_state_changed" in INTERNAL_EVENT_NAMES
    assert "technology_absorption_candidate_declared" in INTERNAL_EVENT_NAMES
    assert "experience_record_declared" in INTERNAL_EVENT_NAMES
    assert "post_task_reflection_declared" in INTERNAL_EVENT_NAMES
    assert "operator_feedback_recorded" in INTERNAL_EVENT_NAMES
    assert "evolution_review_decision_declared" in INTERNAL_EVENT_NAMES
    assert "reviewed_learning_guidance_declared" in INTERNAL_EVENT_NAMES
    assert "promotion_gate_evaluated" in INTERNAL_EVENT_NAMES


def test_work_item_state_contract_is_shared_schema() -> None:
    contract = WorkItemStateContract(
        work_item_ref="work-item://mission-1/validate-plan",
        work_item_status="active",
        mission_id="mission-1",
        transition="create",
        next_action_ref="next_action:validate-plan",
        checkpoint_refs=["work_item_transition:create:work-item://mission-1/validate-plan:1"],
    )

    assert contract.memory_write_mode == "through_core_only"
    assert WORK_ITEM_STATE_SCHEMA.contract_name == "WorkItemStateContract"
    assert "work_item_status" in WORK_ITEM_STATE_SCHEMA.required_fields


def test_artifact_lifecycle_state_contract_is_shared_schema() -> None:
    contract = ArtifactLifecycleStateContract(
        artifact_ref="artifact://mission-1/plan/v1",
        artifact_status="active",
        mission_id="mission-1",
        transition="register",
        artifact_version=1,
        owner_mission_id="mission-1",
        objective_ref="objective://mission-1",
        work_item_ref="work-item://mission-1/validate-plan",
        rollback_plan_ref="rollback://mission-1/plan/v1",
    )

    assert contract.memory_write_mode == "through_core_only"
    assert ARTIFACT_LIFECYCLE_STATE_SCHEMA.contract_name == (
        "ArtifactLifecycleStateContract"
    )
    assert "artifact_status" in ARTIFACT_LIFECYCLE_STATE_SCHEMA.required_fields


def test_long_horizon_goal_strategy_contract_is_read_only_schema() -> None:
    contract = LongHorizonGoalStrategyContract(
        mission_id="mission-long-horizon",
        strategy_status="ready",
        strategy_summary="status=ready; mode=read_only_no_scheduler",
        milestone_refs=["work-item://mission-long-horizon/validate-plan"],
        risk_refs=["open_loop:validate operator direction"],
        memory_anchor_refs=["semantic_focus:strategy"],
        next_action_ref="next_action:operator-review",
        evidence_refs=["artifact://mission-long-horizon/plan/v1"],
    )

    assert contract.memory_write_mode == "read_only"
    assert contract.autonomous_scheduling_allowed is False
    assert LONG_HORIZON_GOAL_STRATEGY_SCHEMA.contract_name == (
        "LongHorizonGoalStrategyContract"
    )
    assert "strategy_status" in LONG_HORIZON_GOAL_STRATEGY_SCHEMA.required_fields


def test_mission_progress_report_contract_is_read_only_schema() -> None:
    report = MissionProgressReportContract(
        report_id="mission-progress-report://mission-1",
        mission_id="mission-1",
        report_status="needs_operator_decision",
        progress_summary="status=needs_operator_decision; pending_decisions=1",
        report_text="Missao: validate the release",
        mission_goal="validate the release",
        mission_status="active",
        objective_status="active",
        generated_at="2026-07-16T00:00:00+00:00",
        pending_decisions=["review_learning_candidate"],
        next_action_ref="next_action:review",
    )

    assert report.memory_write_mode == "read_only"
    assert report.autonomous_execution_allowed is False
    assert MISSION_PROGRESS_REPORT_SCHEMA.contract_name == (
        "MissionProgressReportContract"
    )
    assert "report_text" in MISSION_PROGRESS_REPORT_SCHEMA.required_fields


def test_experience_reflection_contracts_are_shared_schemas() -> None:
    experience = ExperienceRecordContract(
        experience_id="experience://mission-1/001",
        mission_id="mission-1",
        workflow_profile="software_change_workflow",
        outcome_status="completed",
        timestamp="2026-05-17T00:00:00Z",
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-1/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="contract-first implementation",
        recommendation="keep proposal in sandbox",
        timestamp="2026-05-17T00:00:01Z",
    )

    assert experience.automatic_promotion_allowed is False
    assert reflection.core_mutation_allowed is False
    assert EXPERIENCE_RECORD_SCHEMA.contract_name == "ExperienceRecordContract"
    assert "user_intent" in EXPERIENCE_RECORD_SCHEMA.optional_fields
    assert "route" in EXPERIENCE_RECORD_SCHEMA.optional_fields
    assert "specialist_used" in EXPERIENCE_RECORD_SCHEMA.optional_fields
    assert POST_TASK_REFLECTION_SCHEMA.contract_name == "PostTaskReflectionContract"
    assert "reflection_influence_status" in DELIBERATIVE_PLAN_SCHEMA.optional_fields


def test_operator_feedback_contract_is_bounded_and_human_reviewed() -> None:
    feedback = OperatorFeedbackContract(
        feedback_id="operator-feedback://mission-1/001",
        mission_id="mission-1",
        experience_id="experience://mission-1/001",
        assessment="correction",
        operator_ref="operator://local_console",
        rating=2,
        correction="Use the verified rollback evidence before recommending release.",
        evidence_refs=["evidence://mission-1/rollback"],
        timestamp="2026-07-16T00:00:00+00:00",
    )

    assert feedback.feedback_status == "recorded_bounded"
    assert feedback.evolution_review_status == "needs_review"
    assert feedback.memory_write_mode == "through_core_only"
    assert feedback.human_review_required is True
    assert feedback.automatic_promotion_allowed is False
    assert feedback.core_mutation_allowed is False
    assert OPERATOR_FEEDBACK_SCHEMA.contract_name == "OperatorFeedbackContract"
    assert "assessment" in OPERATOR_FEEDBACK_SCHEMA.required_fields


def test_recurring_pattern_contracts_are_observational_only() -> None:
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://software-change",
        pattern_type="repeated_successful_workflow",
        pattern_status="evidence_ready_for_human_review",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=2,
        non_successful_occurrences=0,
        confidence_status="bounded_moderate",
        outcome_summary="completed=2",
        pattern_summary="two compatible completed experiences",
        experience_refs=["experience://1", "experience://2"],
        reflection_refs=["reflection://1", "reflection://2"],
        feedback_refs=[],
        evidence_refs=["trace://1", "trace://2"],
        recurring_signals=["run_targeted_tests"],
        conflict_flags=[],
        blockers=[],
        generated_at="2026-07-16T12:00:00Z",
    )
    report = RecurringPatternReportContract(
        report_id="recurring-pattern-report://test",
        report_status="evidence_ready_for_human_review",
        records_analyzed=2,
        compatible_group_count=1,
        eligible_pattern_count=1,
        minimum_occurrences=2,
        scope_filters={},
        patterns=[pattern],
        evidence_refs=["trace://1", "trace://2"],
        blockers=[],
        generated_at="2026-07-16T12:00:00Z",
    )

    assert pattern.skill_candidate_generation_allowed is False
    assert pattern.automatic_skill_creation_allowed is False
    assert pattern.automatic_promotion_allowed is False
    assert pattern.core_mutation_allowed is False
    assert report.read_only is True
    assert report.skill_candidate_generation_allowed is False
    assert RECURRING_PATTERN_EVIDENCE_SCHEMA.contract_name == (
        "RecurringPatternEvidenceContract"
    )
    assert RECURRING_PATTERN_REPORT_SCHEMA.contract_name == (
        "RecurringPatternReportContract"
    )
    assert (
        "automatic_skill_creation_allowed"
        in RECURRING_PATTERN_REPORT_SCHEMA.optional_fields
    )


def test_skill_candidate_contract_is_versioned_inactive_and_review_bound() -> None:
    candidate = SkillCandidateContract(
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence", "report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["trace://release-evidence/1"],
        source_pattern_refs=["recurring-pattern://release-evidence"],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run targeted release tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T14:00:00Z",
    )

    assert candidate.registry_status == "candidate_inactive"
    assert candidate.review_status == "needs_review"
    assert candidate.activation_status == "inactive"
    assert candidate.sandbox_required is True
    assert candidate.human_review_required is True
    assert candidate.automatic_activation_allowed is False
    assert candidate.automatic_promotion_allowed is False
    assert candidate.core_mutation_allowed is False
    assert candidate.memory_write_mode == "through_core_only"
    assert SKILL_CANDIDATE_SCHEMA.contract_name == "SkillCandidateContract"
    assert "version" in SKILL_CANDIDATE_SCHEMA.required_fields
    assert "allowed_tools" in SKILL_CANDIDATE_SCHEMA.required_fields


def test_skill_mining_contracts_never_grant_activation_or_promotion() -> None:
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://release-evidence/1",
        source_pattern_ref="recurring-pattern://release-evidence",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        specialist_type="software_change_specialist",
        inputs=["release_evidence"],
        outputs=["bounded_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence"],
        risk_level=RiskLevel.MODERATE,
        failure_modes=["missing_evidence"],
        proposed_tests=["run release evidence tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T15:00:00Z",
    )
    result = SkillMiningResultContract(
        mining_result_id="skill-mining-result://release-evidence/1",
        mining_status="blocked",
        eligibility_status="ineligible",
        source_pattern_ref=request.source_pattern_ref,
        source_authority_status="observation_only_requires_miner_and_review",
        threshold_occurrences=2,
        observed_occurrences=1,
        blockers=["recurrence_threshold_not_met"],
        evidence_refs=[request.source_pattern_ref],
        generated_at=request.timestamp,
    )

    assert request.automatic_mining_allowed is False
    assert request.automatic_activation_allowed is False
    assert result.candidate is None
    assert result.automatic_activation_allowed is False
    assert result.automatic_promotion_allowed is False
    assert result.core_mutation_allowed is False
    assert SKILL_MINING_REQUEST_SCHEMA.contract_name == (
        "SkillMiningRequestContract"
    )
    assert SKILL_MINING_RESULT_SCHEMA.contract_name == "SkillMiningResultContract"
    assert "candidate" in SKILL_MINING_RESULT_SCHEMA.optional_fields


def test_skill_sandbox_eval_contract_remains_pending_human_release() -> None:
    case = SkillSandboxCaseResultContract(
        case_id="case-release-evidence",
        passed=True,
        checks={"expected_output": True, "tool_scope": True},
        failed_checks=[],
        evidence_refs=["eval://skill/release-evidence/case-1"],
    )
    evaluation = SkillSandboxEvalContract(
        eval_id="skill-sandbox-eval://release-evidence",
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        version="1.0.0",
        evolution_proposal_id="proposal-skill-release-evidence",
        review_decision_id="review-decision://skill-release-evidence",
        eval_status="passed_pending_release_gate",
        required_pass_rate=1.0,
        pass_rate=1.0,
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        case_results=[case],
        evidence_refs=["eval://skill/release-evidence"],
        proposed_tests=["run skill sandbox tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        blockers=[],
        generated_at="2026-07-16T16:00:00Z",
    )

    assert evaluation.sandbox_only is True
    assert evaluation.runtime_activation_allowed is False
    assert evaluation.promotion_authorized is False
    assert evaluation.automatic_promotion_allowed is False
    assert evaluation.core_mutation_allowed is False
    assert SKILL_SANDBOX_CASE_RESULT_SCHEMA.contract_name == (
        "SkillSandboxCaseResultContract"
    )
    assert SKILL_SANDBOX_EVAL_SCHEMA.contract_name == "SkillSandboxEvalContract"
    assert "runtime_activation_allowed" in SKILL_SANDBOX_EVAL_SCHEMA.optional_fields
    assert "candidate_version" in (
        SANDBOX_TO_RELEASE_CHECKLIST_SCHEMA.optional_fields
    )
    assert "candidate_version" in EVOLUTION_REVIEW_DECISION_SCHEMA.optional_fields


def test_skill_evolution_operator_view_is_read_only_and_review_bound() -> None:
    item = SkillEvolutionOperatorItemContract(
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        risk_level="moderate",
        registry_status="candidate_inactive",
        review_status="sandboxed",
        activation_status="inactive",
        evolution_status="sandbox_passed_pending_release_review",
        source_pattern_refs=["recurring-pattern://release-evidence"],
        pattern_status="evidence_ready_for_human_review",
        pattern_summary="two compatible successful experiences",
        occurrence_count=2,
        minimum_occurrences=2,
        confidence_status="bounded_moderate",
        proposal_id="proposal-skill-release-evidence",
        proposal_status="sandbox_only",
        sandbox_eval_ref="skill-sandbox-eval://release-evidence",
        sandbox_eval_status="passed_pending_release_gate",
        sandbox_pass_rate=1.0,
        allowed_tools=["local_test_runner"],
        evidence_refs=["trace://release-evidence/1"],
        proposed_tests=["run skill sandbox tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        blockers=[],
        next_operator_action="prepare_human_release_review",
    )
    view = SkillEvolutionOperatorViewContract(
        view_id="skill-evolution-view://test",
        view_status="release_review_required",
        pattern_report_id="recurring-pattern-report://test",
        pattern_report_status="evidence_ready_for_human_review",
        pattern_count=1,
        candidate_count=1,
        items=[item],
        unregistered_pattern_refs=[],
        blockers=[],
        generated_at="2026-07-16T17:00:00Z",
    )

    assert view.read_only is True
    assert view.human_review_required is True
    assert view.runtime_activation_allowed is False
    assert view.promotion_authorized is False
    assert item.runtime_activation_allowed is False
    assert item.promotion_authorized is False
    assert SKILL_EVOLUTION_OPERATOR_ITEM_SCHEMA.contract_name == (
        "SkillEvolutionOperatorItemContract"
    )
    assert SKILL_EVOLUTION_OPERATOR_VIEW_SCHEMA.contract_name == (
        "SkillEvolutionOperatorViewContract"
    )
    assert "next_operator_action" in (
        SKILL_EVOLUTION_OPERATOR_ITEM_SCHEMA.required_fields
    )


def test_workflow_version_registry_contract_cannot_mutate_active_runtime() -> None:
    version = WorkflowProfileVersionContract(
        workflow_version_id="workflow-version://software_change_workflow/1.0.0",
        workflow_profile="software_change_workflow",
        version="1.0.0",
        route="software_development",
        lifecycle_status="baseline_snapshot",
        definition_hash="a" * 64,
        workflow_steps=["frame change", "evaluate risk", "recommend patch"],
        workflow_checkpoints=["scope_framed", "risk_checked", "patch_ready"],
        workflow_decision_points=["scope_gate", "risk_gate", "patch_gate"],
        success_criteria=["bounded patch direction"],
        evidence_refs=["domain-registry://runtime-routes/current"],
        proposed_tests=["tests/unit/test_domain_registry_workflows.py"],
        rollback_plan_ref="rollback://domain-registry/runtime-routes/current",
        source_registry_ref="domain-registry://runtime-routes/current",
        source_registry_fingerprint="b" * 64,
        timestamp="2026-07-16T18:00:00Z",
        risk_level="low",
        review_status="not_applicable",
        runtime_binding_status="observed_active_baseline",
        human_review_required=False,
        sandbox_required=False,
    )
    registry = WorkflowProfileVersionRegistryContract(
        registry_id="workflow-version-registry://active/test/1.0.0",
        registry_version="1.0.0",
        registry_status="baseline_snapshot_ready",
        active_registry_ref="domain-registry://runtime-routes/current",
        active_registry_fingerprint="b" * 64,
        workflow_count=1,
        baseline_count=1,
        candidate_count=0,
        versions=[version],
        evidence_refs=["domain-registry://runtime-routes/current"],
        blockers=[],
        generated_at="2026-07-16T18:00:00Z",
    )

    assert registry.read_only is True
    assert registry.active_registry_mutation_allowed is False
    assert registry.runtime_activation_allowed is False
    assert registry.automatic_promotion_allowed is False
    assert registry.core_mutation_allowed is False
    assert version.active_registry_write_allowed is False
    assert version.runtime_activation_allowed is False
    assert WORKFLOW_PROFILE_VERSION_SCHEMA.contract_name == (
        "WorkflowProfileVersionContract"
    )
    assert WORKFLOW_PROFILE_VERSION_REGISTRY_SCHEMA.contract_name == (
        "WorkflowProfileVersionRegistryContract"
    )
    assert "source_registry_fingerprint" in (
        WORKFLOW_PROFILE_VERSION_SCHEMA.required_fields
    )


def test_workflow_evolution_contracts_are_explicit_and_inactive() -> None:
    request = WorkflowEvolutionRequestContract(
        workflow_evolution_request_id="workflow-evolution-request://software/1.1.0",
        source_pattern_ref="recurring-pattern://software-release",
        source_review_decision_id="review-decision://software-release/001",
        baseline_version_ref=(
            "workflow-version://software_change_workflow/1.0.0"
        ),
        candidate_version="1.1.0",
        step_additions=["record verified release evidence"],
        step_removals=[],
        checkpoint_additions=["release_evidence_recorded"],
        checkpoint_removals=[],
        decision_point_additions=[],
        decision_point_removals=[],
        success_criteria_additions=["release evidence is auditable"],
        success_criteria_removals=[],
        change_summary="record release evidence before recommendation",
        evidence_refs=["evidence://software-release/pattern"],
        proposed_tests=["test://workflow/software-release"],
        rollback_plan_ref="rollback://workflow/software/1.0.0",
        risk_level="moderate",
        timestamp="2026-07-16T19:00:00Z",
    )
    result = WorkflowEvolutionBuildResultContract(
        workflow_evolution_result_id="workflow-evolution-result://software-1",
        build_status="blocked",
        source_pattern_ref=request.source_pattern_ref,
        source_review_decision_id=request.source_review_decision_id,
        baseline_version_ref=request.baseline_version_ref,
        source_authority_status=(
            "reviewed_evidence_requires_candidate_review_sandbox_and_release_gate"
        ),
        delta_summary={"step_additions": list(request.step_additions)},
        evidence_refs=list(request.evidence_refs),
        blockers=["persisted_human_review_decision_required"],
        generated_at=request.timestamp,
    )

    assert request.automatic_build_allowed is False
    assert request.active_registry_write_allowed is False
    assert request.runtime_activation_allowed is False
    assert result.candidate is None
    assert result.active_registry_write_allowed is False
    assert result.runtime_activation_allowed is False
    assert result.automatic_promotion_allowed is False
    assert result.core_mutation_allowed is False
    assert WORKFLOW_EVOLUTION_REQUEST_SCHEMA.contract_name == (
        "WorkflowEvolutionRequestContract"
    )
    assert WORKFLOW_EVOLUTION_BUILD_RESULT_SCHEMA.contract_name == (
        "WorkflowEvolutionBuildResultContract"
    )
    assert "step_additions" in WORKFLOW_EVOLUTION_REQUEST_SCHEMA.optional_fields
    assert "candidate" in WORKFLOW_EVOLUTION_BUILD_RESULT_SCHEMA.optional_fields


def test_deliberative_plan_schema_declares_semantic_memory_evidence_fields() -> None:
    plan = DeliberativePlanContract(
        plan_summary="objetivo=test; semantic_memory_anchor_refs=memory://mission/1/semantic",
        goal="test",
        steps=["avaliar"],
        active_domains=["strategy"],
        active_minds=["mente_executiva"],
        constraints=["bounded"],
        risks=["none"],
        recommended_task_type="analysis",
        requires_human_validation=False,
        rationale="semantic_memory_use_reason=matched active_mission",
        semantic_memory_anchor_refs=["memory://mission/1/semantic"],
        semantic_memory_evidence_refs=["memory://mission/1/semantic#evidence"],
        semantic_memory_use_reason="matched active_mission to workflow",
    )

    assert plan.semantic_memory_anchor_refs == ["memory://mission/1/semantic"]
    assert plan.semantic_memory_non_use_reason is None
    assert "semantic_memory_anchor_refs" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "semantic_memory_evidence_refs" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "semantic_memory_use_reason" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "semantic_memory_non_use_reason" in DELIBERATIVE_PLAN_SCHEMA.optional_fields


def test_autonomy_ladder_contract_is_runtime_declared_not_promotional() -> None:
    ladder = AutonomyLadderContract(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="confirm_before_action",
        effective_autonomy_level="confirm_before_action",
        autonomy_ladder_status="downgraded_to_max",
        max_capability_mode="core_with_specialist_handoff",
        human_confirmation_required=True,
        human_confirmation_mode="explicit",
    )

    assert ladder.automatic_promotion_allowed is False
    assert ladder.core_mutation_allowed is False
    assert AUTONOMY_LADDER_SCHEMA.contract_name == "AutonomyLadderContract"
    assert "requested_autonomy_level" in INPUT_SCHEMA.optional_fields
    assert "effective_autonomy_level" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    assert "autonomy_automatic_promotion_allowed" in (
        DELIBERATIVE_PLAN_SCHEMA.optional_fields
    )
    assert "autonomy_ladder_declared" in INTERNAL_EVENT_NAMES


def test_sandbox_to_release_checklist_contract_is_not_promotion_permit() -> None:
    checklist = SandboxToReleaseChecklistContract(
        checklist_id="sandbox-release-checklist://proposal-1",
        evolution_proposal_id="proposal-1",
        release_scope="workflow:software_change_workflow",
        checklist_status="ready_for_release_review",
        human_review_status="approved",
        required_gates=["human_review", "standard_engineering_gate"],
    )

    assert checklist.sandbox_required is True
    assert checklist.release_gate_required is True
    assert checklist.automatic_promotion_allowed is False
    assert checklist.core_mutation_allowed is False
    assert SANDBOX_TO_RELEASE_CHECKLIST_SCHEMA.contract_name == (
        "SandboxToReleaseChecklistContract"
    )
    assert "required_gates" in SANDBOX_TO_RELEASE_CHECKLIST_SCHEMA.required_fields


def test_promotion_gate_decision_is_not_human_promotion_authorization() -> None:
    decision = PromotionGateDecisionContract(
        promotion_gate_id="promotion-gate://proposal-1",
        checklist_id="sandbox-release-checklist://proposal-1",
        evolution_proposal_id="proposal-1",
        release_scope="workflow:software_change_workflow",
        gate_status="passed",
        decision="eligible_for_human_promotion_decision",
        release_conclusion="release_gate_passed_pending_human_decision",
        required_gates=["human_review", "release_gate_before_promotion"],
        completed_gates=["human_review", "release_gate_before_promotion"],
        missing_gates=[],
        evidence_refs=["evidence://proposal-1"],
        blockers=[],
        human_review_status="approved",
        promotion_eligible=True,
    )

    assert decision.promotion_eligible is True
    assert decision.human_decision_required is True
    assert decision.promotion_authorized is False
    assert decision.automatic_promotion_allowed is False
    assert decision.core_mutation_allowed is False
    assert PROMOTION_GATE_DECISION_SCHEMA.contract_name == (
        "PromotionGateDecisionContract"
    )
    assert "release_conclusion" in PROMOTION_GATE_DECISION_SCHEMA.required_fields


def test_procedural_playbook_candidate_contract_is_bounded_schema() -> None:
    candidate = ProceduralPlaybookCandidateContract(
        playbook_candidate_id="playbook-candidate://workflow/001",
        procedure_name="bounded release checklist",
        workflow_profile="software_change_workflow",
        bounded_steps=["collect evidence", "run tests", "prepare rollback"],
        evidence_refs=["trace://req-1"],
        rollback_plan_ref="rollback://playbook/001",
        timestamp="2026-07-04T00:00:00Z",
    )

    assert candidate.human_review_required is True
    assert candidate.automatic_promotion_allowed is False
    assert candidate.core_mutation_allowed is False
    assert candidate.memory_write_mode == "through_core_only"
    assert PROCEDURAL_PLAYBOOK_CANDIDATE_SCHEMA.contract_name == (
        "ProceduralPlaybookCandidateContract"
    )
    assert "bounded_steps" in PROCEDURAL_PLAYBOOK_CANDIDATE_SCHEMA.required_fields
    assert "rollback_plan_ref" in PROCEDURAL_PLAYBOOK_CANDIDATE_SCHEMA.optional_fields
    assert "reflection_influence_refs" in DELIBERATIVE_PLAN_SCHEMA.optional_fields
    review_item = EvolutionReviewQueueItemContract(
        review_item_id="review://proposal-1",
        evolution_proposal_id="proposal-1",
        proposal_type="post_task_reflection_improvement",
        review_status="needs_review",
        review_reason="manual review required before promotion or runtime change",
        requires_human_review=True,
        requires_sandbox=True,
    )
    assert review_item.review_status == "needs_review"
    assert EVOLUTION_REVIEW_QUEUE_ITEM_SCHEMA.contract_name == (
        "EvolutionReviewQueueItemContract"
    )
    review_decision = EvolutionReviewDecisionContract(
        review_decision_id="review-decision://proposal-1/001",
        evolution_proposal_id="proposal-1",
        review_status="approved",
        decision="approve",
        operator_ref="operator://local_console",
        timestamp="2026-05-17T00:00:02Z",
        evidence_refs=["trace://req-1"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/current",
    )
    assert review_decision.automatic_promotion_allowed is False
    assert review_decision.core_mutation_allowed is False
    assert EVOLUTION_REVIEW_DECISION_SCHEMA.contract_name == (
        "EvolutionReviewDecisionContract"
    )
    guidance = ReviewedLearningGuidanceContract(
        guidance_id="reviewed-learning-guidance://proposal-1/001",
        source_review_decision_id=review_decision.review_decision_id,
        evolution_proposal_id=review_decision.evolution_proposal_id,
        review_status=review_decision.review_status,
        route="strategy",
        workflow_profile="strategy_workflow",
        domain="business_strategy",
        guidance_summary="prefer evidence-backed rollout plans",
        allowed_usage=["planning_context", "synthesis_context"],
        evidence_refs=["trace://req-1"],
        rollback_plan_ref="rollback://workflow/current",
        timestamp="2026-05-17T00:00:03Z",
    )
    assert guidance.automatic_promotion_allowed is False
    assert guidance.core_mutation_allowed is False
    assert REVIEWED_LEARNING_GUIDANCE_SCHEMA.contract_name == (
        "ReviewedLearningGuidanceContract"
    )
    assert "allowed_usage" in REVIEWED_LEARNING_GUIDANCE_SCHEMA.required_fields


def test_memory_lifecycle_review_contracts_never_authorize_maintenance() -> None:
    candidate = MemoryLifecycleCandidateContract(
        candidate_id="memory-lifecycle-candidate://archive/001",
        maintenance_action="archive",
        target_scope="semantic_procedural_corpus",
        target_refs=["memory-corpus://semantic-procedural/archivable"],
        reason="one record is archivable",
        evidence_refs=["memory-telemetry://archivable-records/1"],
        rollback_plan_ref="rollback://memory/archive/restore",
        review_status="needs_review",
        execution_status="not_executed",
        generated_at="2026-07-16T00:00:00Z",
    )
    assessment = MemoryLifecycleGovernanceAssessmentContract(
        assessment_id="memory-lifecycle-assessment://001",
        candidate_id=candidate.candidate_id,
        maintenance_action=candidate.maintenance_action,
        decision_action="approve",
        status="governed",
        timestamp="2026-07-16T00:00:01Z",
    )
    decision = MemoryLifecycleReviewDecisionContract(
        review_decision_id="memory-lifecycle-review://001",
        candidate_id=candidate.candidate_id,
        maintenance_action=candidate.maintenance_action,
        decision_action="approve",
        review_status="approved",
        operator_ref="operator://local_console",
        evidence_refs=list(candidate.evidence_refs),
        rollback_plan_ref=candidate.rollback_plan_ref,
        governance_assessment_id=assessment.assessment_id,
        timestamp="2026-07-16T00:00:02Z",
    )

    assert candidate.automatic_execution_allowed is False
    assert assessment.execution_authorized is False
    assert decision.execution_authorized is False
    assert decision.core_mutation_allowed is False
    assert MEMORY_LIFECYCLE_CANDIDATE_SCHEMA.contract_name == (
        "MemoryLifecycleCandidateContract"
    )
    assert MEMORY_LIFECYCLE_GOVERNANCE_ASSESSMENT_SCHEMA.contract_name == (
        "MemoryLifecycleGovernanceAssessmentContract"
    )
    assert MEMORY_LIFECYCLE_REVIEW_DECISION_SCHEMA.contract_name == (
        "MemoryLifecycleReviewDecisionContract"
    )
def test_system_identity_has_core_principles() -> None:
    assert "truth_and_quality" in SYSTEM_IDENTITY.nuclear_principles
    assert "utility" in SYSTEM_IDENTITY.nuclear_principles
