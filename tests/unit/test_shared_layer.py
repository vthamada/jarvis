from shared.contracts import (
    ExperienceRecordContract,
    GovernanceDecisionContract,
    InputContract,
    PostTaskReflectionContract,
    ProjectObjectiveContinuityContract,
    SurfaceIdentityContract,
    TechnologyAbsorptionCandidateContract,
)
from shared.events import INTERNAL_EVENT_NAMES
from shared.schemas import (
    EXPERIENCE_RECORD_SCHEMA,
    INPUT_SCHEMA,
    POST_TASK_REFLECTION_SCHEMA,
    PROJECT_OBJECTIVE_CONTINUITY_SCHEMA,
    SURFACE_IDENTITY_SCHEMA,
    TECHNOLOGY_ABSORPTION_CANDIDATE_SCHEMA,
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
    assert "technology_absorption_candidate_declared" in INTERNAL_EVENT_NAMES
    assert "experience_record_declared" in INTERNAL_EVENT_NAMES
    assert "post_task_reflection_declared" in INTERNAL_EVENT_NAMES


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
    assert POST_TASK_REFLECTION_SCHEMA.contract_name == "PostTaskReflectionContract"


def test_system_identity_has_core_principles() -> None:
    assert "truth_and_quality" in SYSTEM_IDENTITY.nuclear_principles
    assert "utility" in SYSTEM_IDENTITY.nuclear_principles
