from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from memory_service.service import MemoryService

from shared.contracts import ExperienceRecordContract, PostTaskReflectionContract
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
