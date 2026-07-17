from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from memory_service.service import MemoryService

from shared.contracts import (
    ExperienceRecordContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ReviewedLearningGuidanceContract,
)
from shared.types import MissionId


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_experience_reflection_contracts_are_manual_review_only() -> None:
    experience = ExperienceRecordContract(
        experience_id="experience://mission-1/001",
        mission_id=MissionId("mission-1"),
        workflow_profile="software_change_workflow",
        outcome_status="completed",
        timestamp="2026-05-17T00:00:00Z",
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-1/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="tests should be created before implementation",
        recommendation="create a reusable implementation checklist",
        timestamp="2026-05-17T00:00:01Z",
    )

    assert experience.human_review_required is True
    assert experience.automatic_promotion_allowed is False
    assert experience.core_mutation_allowed is False
    assert reflection.human_review_required is True
    assert reflection.automatic_promotion_allowed is False
    assert reflection.core_mutation_allowed is False


def test_memory_service_persists_bounded_experience_reflection() -> None:
    temp_dir = runtime_dir("memory-experience-reflection")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    experience = ExperienceRecordContract(
        experience_id="experience://mission-exp/001",
        mission_id=MissionId("mission-exp"),
        workflow_profile="software_change_workflow",
        outcome_status="completed",
        objective_ref="objective://jarvis/experience",
        surface_id="surface://jarvis_console",
        evidence_refs=["trace://req-1"],
        signal_refs=["workflow_output_status:coherent"],
        learned_patterns=["test_first_contract_slice"],
        timestamp="2026-05-17T00:00:00Z",
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-exp/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="contract-first implementation reduced drift",
        recommendation="promote a bounded checklist only after tests",
        proposed_change_type="workflow",
        evidence_refs=["trace://req-1"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/current",
        timestamp="2026-05-17T00:00:01Z",
    )

    stored = service.record_experience_reflection(
        experience=experience,
        reflection=reflection,
    )
    records = service.list_experience_reflections(mission_id="mission-exp")

    assert stored.reflection.blockers == []
    assert records[0].experience.experience_id == "experience://mission-exp/001"
    assert records[0].experience.reusable_memory_status == "bounded"
    assert records[0].reflection.recommendation == (
        "promote a bounded checklist only after tests"
    )


def test_memory_service_attaches_operator_feedback_to_experience_and_reflection() -> None:
    temp_dir = runtime_dir("memory-operator-feedback")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    service.record_experience_reflection(
        experience=ExperienceRecordContract(
            experience_id="experience://mission-feedback/001",
            mission_id=MissionId("mission-feedback"),
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            evidence_refs=["trace://mission-feedback"],
            timestamp="2026-07-16T00:00:00+00:00",
        ),
        reflection=PostTaskReflectionContract(
            reflection_id="reflection://mission-feedback/001",
            experience_id="experience://mission-feedback/001",
            reflection_status="candidate",
            learning_candidate="Use release evidence consistently.",
            recommendation="Keep the change in sandbox until reviewed.",
            evidence_refs=["trace://mission-feedback"],
            timestamp="2026-07-16T00:00:01+00:00",
        ),
    )

    result = service.record_operator_feedback(
        OperatorFeedbackContract(
            feedback_id="operator-feedback://mission-feedback/001",
            mission_id=MissionId("mission-feedback"),
            experience_id="experience://mission-feedback/001",
            assessment="correction",
            operator_ref="operator://local_console",
            rating=2,
            comment="The answer omitted the release evidence.",
            correction="Require verified release evidence before recommendation.",
            next_expectation="Show the evidence reference in the next answer.",
            evidence_refs=["evidence://mission-feedback/release"],
            timestamp="2026-07-16T00:00:02+00:00",
        )
    )
    reloaded = service.get_experience_reflection(
        "experience://mission-feedback/001"
    )

    assert result.feedback.feedback_status == "recorded_bounded"
    assert reloaded is not None
    assert "assessment=correction" in reloaded.experience.user_feedback
    assert "operator-feedback://mission-feedback/001" in (
        reloaded.experience.signal_refs
    )
    assert "evidence://mission-feedback/release" in (
        reloaded.experience.evidence_refs
    )
    assert reloaded.reflection is not None
    assert "operator-feedback://mission-feedback/001" in (
        reloaded.reflection.evidence_refs
    )
    assert "evaluate_decision_against_explicit_operator_feedback" in (
        reloaded.reflection.proposed_tests
    )
    assert reloaded.experience.automatic_promotion_allowed is False
    assert reloaded.reflection.core_mutation_allowed is False


def test_memory_service_builds_recurring_correction_evidence_end_to_end() -> None:
    temp_dir = runtime_dir("memory-recurring-pattern")
    service = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    for index in (1, 2):
        experience_id = f"experience://mission-pattern/{index}"
        mission_id = MissionId(f"mission-pattern-{index}")
        service.record_experience_reflection(
            experience=ExperienceRecordContract(
                experience_id=experience_id,
                mission_id=mission_id,
                workflow_profile="software_change_workflow",
                route="software_development",
                primary_domain_driver="software_engineering",
                outcome_status="completed",
                checkpoints=["run_targeted_tests", "run_standard_gate"],
                evidence_refs=[f"trace://mission-pattern/{index}"],
                timestamp=f"2026-07-16T10:00:0{index}Z",
            ),
            reflection=PostTaskReflectionContract(
                reflection_id=f"reflection://mission-pattern/{index}",
                experience_id=experience_id,
                reflection_status="candidate",
                learning_candidate="release evidence should be explicit",
                recommendation="review a bounded evidence checklist",
                evidence_refs=[f"trace://mission-pattern/{index}"],
                timestamp=f"2026-07-16T10:01:0{index}Z",
            ),
        )
        service.record_operator_feedback(
            OperatorFeedbackContract(
                feedback_id=f"operator-feedback://mission-pattern/{index}",
                mission_id=mission_id,
                experience_id=experience_id,
                assessment="correction",
                operator_ref="operator://local_console",
                correction="Show verified release evidence before recommendation.",
                evidence_refs=[f"evidence://mission-pattern/{index}/release"],
                timestamp=f"2026-07-16T10:02:0{index}Z",
            )
        )

    report = service.build_recurring_pattern_report(
        report_id="recurring-pattern-report://memory-e2e",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        generated_at="2026-07-16T11:00:00Z",
    )

    assert report.report_status == "evidence_ready_for_human_review"
    assert report.records_analyzed == 2
    assert report.compatible_group_count == 1
    assert report.eligible_pattern_count == 1
    assert report.patterns[0].pattern_type == "recurring_operator_correction"
    assert report.patterns[0].feedback_refs == [
        "operator-feedback://mission-pattern/2",
        "operator-feedback://mission-pattern/1",
    ]
    assert report.patterns[0].reflection_refs == [
        "reflection://mission-pattern/2",
        "reflection://mission-pattern/1",
    ]
    assert report.patterns[0].automatic_skill_creation_allowed is False
    assert report.patterns[0].automatic_promotion_allowed is False
    assert report.patterns[0].core_mutation_allowed is False


def test_memory_service_persists_experience_before_reflection() -> None:
    temp_dir = runtime_dir("memory-experience-only")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    experience = ExperienceRecordContract(
        experience_id="experience://mission-auto/req-1",
        mission_id=MissionId("mission-auto"),
        workflow_profile="strategic_direction_workflow",
        outcome_status="completed",
        user_intent="planning",
        route="strategy",
        primary_mind="mente_executiva",
        primary_domain_driver="estrategia_e_pensamento_sistemico",
        specialist_used=["structured_analysis_specialist"],
        plan_summary="decompor objetivo em etapas reversiveis",
        execution_summary="operation completed with 1 artifact(s)",
        outcome="coherent",
        tools_used=["local_artifact_generation"],
        checkpoints=["scenario framed"],
        evidence_refs=["trace://request/req-1"],
        signal_refs=["workflow_output_status:coherent"],
        timestamp="2026-05-17T00:00:00Z",
    )

    stored = service.record_experience(experience=experience)
    records = service.list_experience_reflections(mission_id="mission-auto")

    assert stored.reflection is None
    assert records[0].reflection is None
    assert records[0].experience.user_intent == "planning"
    assert records[0].experience.route == "strategy"
    assert records[0].experience.specialist_used == ["structured_analysis_specialist"]
    assert records[0].experience.automatic_promotion_allowed is False
    assert records[0].experience.core_mutation_allowed is False


def test_memory_service_blocks_experience_reflection_without_evidence_or_manual_review() -> None:
    temp_dir = runtime_dir("memory-experience-blocked")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    experience = ExperienceRecordContract(
        experience_id="experience://mission-blocked/001",
        mission_id=MissionId("mission-blocked"),
        workflow_profile="strategic_direction_workflow",
        outcome_status="partial",
        timestamp="2026-05-17T00:00:00Z",
        automatic_promotion_allowed=True,
        core_mutation_allowed=True,
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-blocked/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="mutate the core automatically",
        recommendation="apply without review",
        timestamp="2026-05-17T00:00:01Z",
        automatic_promotion_allowed=True,
        core_mutation_allowed=True,
    )

    stored = service.record_experience_reflection(
        experience=experience,
        reflection=reflection,
    )

    assert stored.experience.reusable_memory_status == "blocked"
    assert stored.experience.automatic_promotion_allowed is False
    assert stored.experience.core_mutation_allowed is False
    assert "automatic_promotion_not_allowed" in stored.reflection.blockers
    assert "core_mutation_not_allowed" in stored.reflection.blockers
    assert "evidence_required" in stored.reflection.blockers


def test_memory_service_persists_reviewed_learning_guidance() -> None:
    temp_dir = runtime_dir("memory-reviewed-guidance")
    service = MemoryService(database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}")
    guidance = ReviewedLearningGuidanceContract(
        guidance_id="reviewed-learning-guidance://review-1",
        source_review_decision_id="review-decision://proposal-1/001",
        evolution_proposal_id="proposal-1",
        review_status="approved",
        route="software_development",
        workflow_profile="software_change_workflow",
        domain="engenharia_de_software",
        guidance_summary="prefer small reversible patches with direct tests",
        allowed_usage=["planning_context", "synthesis_context"],
        evidence_refs=["trace://req-reviewed"],
        rollback_plan_ref="rollback://proposal-1",
        timestamp="2026-05-17T00:00:02Z",
    )

    stored = service.record_reviewed_learning_guidance(guidance)
    records = service.list_reviewed_learning_guidance(
        route="software_development",
        workflow_profile="software_change_workflow",
        domain="engenharia_de_software",
    )

    assert stored.guidance.automatic_promotion_allowed is False
    assert stored.guidance.core_mutation_allowed is False
    assert records[0].guidance.guidance_id == guidance.guidance_id
    assert records[0].guidance.guidance_summary == guidance.guidance_summary
    assert records[0].guidance.allowed_usage == [
        "planning_context",
        "synthesis_context",
    ]
