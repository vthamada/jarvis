from shared.contracts import (
    ArtifactLifecycleStateContract,
    AutonomyLadderContract,
    DeliberativePlanContract,
    EvolutionReviewDecisionContract,
    EvolutionReviewQueueItemContract,
    ExperienceRecordContract,
    GovernanceDecisionContract,
    InputContract,
    LongHorizonGoalStrategyContract,
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
    SurfaceIdentityContract,
    TechnologyAbsorptionCandidateContract,
    WorkItemStateContract,
)
from shared.events import INTERNAL_EVENT_NAMES
from shared.schemas import (
    ARTIFACT_LIFECYCLE_STATE_SCHEMA,
    AUTONOMY_LADDER_SCHEMA,
    DELIBERATIVE_PLAN_SCHEMA,
    EVOLUTION_REVIEW_DECISION_SCHEMA,
    EVOLUTION_REVIEW_QUEUE_ITEM_SCHEMA,
    EXPERIENCE_RECORD_SCHEMA,
    INPUT_SCHEMA,
    LONG_HORIZON_GOAL_STRATEGY_SCHEMA,
    MISSION_PROGRESS_REPORT_SCHEMA,
    OPERATOR_FEEDBACK_SCHEMA,
    POST_TASK_REFLECTION_SCHEMA,
    PROCEDURAL_PLAYBOOK_CANDIDATE_SCHEMA,
    PROJECT_OBJECTIVE_CONTINUITY_SCHEMA,
    PROMOTION_GATE_DECISION_SCHEMA,
    RECURRING_PATTERN_EVIDENCE_SCHEMA,
    RECURRING_PATTERN_REPORT_SCHEMA,
    REVIEWED_LEARNING_GUIDANCE_SCHEMA,
    SANDBOX_TO_RELEASE_CHECKLIST_SCHEMA,
    SKILL_CANDIDATE_SCHEMA,
    SURFACE_IDENTITY_SCHEMA,
    TECHNOLOGY_ABSORPTION_CANDIDATE_SCHEMA,
    WORK_ITEM_STATE_SCHEMA,
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


def test_system_identity_has_core_principles() -> None:
    assert "truth_and_quality" in SYSTEM_IDENTITY.nuclear_principles
    assert "utility" in SYSTEM_IDENTITY.nuclear_principles
