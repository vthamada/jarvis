from dataclasses import asdict, replace
from json import loads
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from observability_service.agentic import JsonlAgenticMirrorAdapter, LangSmithObservabilityAdapter
from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.contracts import (
    CapabilityReadinessContract,
    DecisionOutcomeAttributionRecordContract,
    EvolutionProposalContract,
    ExperienceRecordContract,
    LearningOutcomeObservationContract,
    LearningVersionTargetContract,
    MissionStateContract,
    OpenLoopStateContract,
    PostTaskReflectionContract,
    RecurringPatternReportContract,
    SkillCandidateContract,
)
from shared.decision_attribution import canonicalize_decision_attribution_record
from shared.events import InternalEventEnvelope
from shared.types import MissionStatus, RiskLevel


def learning_target(
    *,
    version_ref: str,
    baseline_version_ref: str | None = None,
    runtime_status: str = "active_reviewed_guidance",
    rollback_status: str = "not_observed",
    rollback_plan_ref: str | None = None,
) -> LearningVersionTargetContract:
    return LearningVersionTargetContract(
        target_id=f"learning-target://test/{version_ref.rsplit('/', 1)[-1]}",
        capability_kind="reviewed_memory",
        capability_id="software_change_workflow",
        version_ref=version_ref,
        lifecycle_status="reviewed_guidance",
        review_status="approved",
        runtime_status=runtime_status,
        evidence_refs=[f"evidence://{version_ref.rsplit('/', 1)[-1]}"],
        rollback_plan_ref=rollback_plan_ref,
        rollback_status=rollback_status,
        observed_at="2026-07-01T12:00:00Z",
        baseline_version_ref=baseline_version_ref,
    )


def learning_observation(
    *,
    observation_id: str,
    version_ref: str,
    success: bool,
    score: float,
    rework_count: int,
    feedback: str,
    regression_flags: list[str] | None = None,
) -> LearningOutcomeObservationContract:
    return LearningOutcomeObservationContract(
        observation_id=observation_id,
        capability_kind="reviewed_memory",
        capability_id="software_change_workflow",
        version_ref=version_ref,
        source_kind="runtime_mission",
        observed_at="2026-07-10T12:00:00Z",
        success=success,
        success_score=score,
        rework_count=rework_count,
        evidence_refs=[f"trace://{observation_id}"],
        mission_id=f"mission-{observation_id}",
        workflow_profile="software_change_workflow",
        route="software_development",
        feedback_assessment=feedback,
        regression_flags=regression_flags or [],
    )


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def decision_attribution_record(
    *,
    suffix: str,
    attribution_status: str = "correlation_only",
    attribution_record_id: str | None = None,
) -> DecisionOutcomeAttributionRecordContract:
    workflow_policy_ref = f"workflow-policy://software/{suffix}"
    memory_ref = f"semantic-memory://software/{suffix}"
    participating_refs = [workflow_policy_ref, memory_ref]
    if attribution_status not in {"correlation_only", "declared_causality"}:
        raise ValueError("test attribution_status must be canonical and observable")
    record = DecisionOutcomeAttributionRecordContract(
        attribution_record_id=(
            attribution_record_id
            or f"decision-outcome-attribution://{suffix}"
        ),
        request_id=f"req-attribution-{suffix}",
        session_id=f"sess-attribution-{suffix}",
        mission_id=f"mission-attribution-{suffix}",
        observed_at="2026-08-11T12:00:00+00:00",
        governance_decision_ref=f"governance-decision://{suffix}",
        governance_decision_status="allow",
        workflow_profile="software_change_workflow",
        route="software_development",
        outcome_ref=(
            f"experience://mission-attribution-{suffix}/"
            f"req-attribution-{suffix}"
        ),
        outcome_status="completed",
        experience_id=(
            f"experience://mission-attribution-{suffix}/"
            f"req-attribution-{suffix}"
        ),
        workflow_policy_ref=workflow_policy_ref,
        workflow_policy_version="1.0.0",
        workflow_policy_source_registry_ref="workflow-policy-registry://v1",
        workflow_policy_source_registry_fingerprint="sha256:test",
        workflow_policy_application_status="applied",
        workflow_policy_effects=(
            ["require_targeted_tests"]
            if attribution_status == "declared_causality"
            else []
        ),
        memory_policy_decision_ref=f"memory-influence-decision://{suffix}",
        memory_policy_status="applied",
        memory_policy_refs=["policy://memory/causal-use"],
        memory_selected_refs=[memory_ref],
        memory_use_reasons={memory_ref: "eligible_scoped_guidance"},
        memory_signal_kinds={memory_ref: "semantic"},
        memory_causal_use_allowed=(attribution_status == "declared_causality"),
        declared_effects_by_ref=(
            {memory_ref: ["planning_context"]}
            if attribution_status == "declared_causality"
            else {}
        ),
        evidence_refs=[f"evidence://attribution/{suffix}"],
    )
    canonical = canonicalize_decision_attribution_record(record)
    assert canonical.participating_refs == participating_refs
    assert canonical.attribution_status == attribution_status
    return canonical


def decision_attribution_event(
    record: DecisionOutcomeAttributionRecordContract,
    *,
    event_id: str,
    event_name: str = "decision_outcome_attribution_recorded",
    mission_id: str | None = None,
    payload_overrides: dict[str, object] | None = None,
) -> InternalEventEnvelope:
    payload: dict[str, object] = asdict(record)
    payload.update(payload_overrides or {})
    resolved_mission_id = (
        mission_id
        if mission_id is not None
        else str(record.mission_id) if record.mission_id is not None else None
    )
    return InternalEventEnvelope(
        event_id=event_id,
        event_name=event_name,
        timestamp="2026-08-11T12:00:01+00:00",
        source_service="orchestrator-service",
        payload=payload,
        request_id=str(record.request_id),
        session_id=str(record.session_id),
        mission_id=resolved_mission_id,
        correlation_id=str(record.request_id),
    )


def test_observability_service_name() -> None:
    assert ObservabilityService.name == "observability-service"


def test_daily_operator_utility_report_correlates_governed_outcomes() -> None:
    def event(
        event_id: str,
        event_name: str,
        timestamp: str,
        mission_id: str,
        payload: dict[str, object],
    ) -> InternalEventEnvelope:
        return InternalEventEnvelope(
            event_id=event_id,
            event_name=event_name,
            timestamp=timestamp,
            source_service="orchestrator-service",
            mission_id=mission_id,
            payload=payload,
        )

    events = [
        event(
            "event-resume",
            "open_loop_resumed",
            "2026-07-18T08:00:00+00:00",
            "mission-utility",
            {"next_action_ref": "next-action://utility/continue"},
        ),
        event(
            "event-work-create",
            "work_item_state_changed",
            "2026-07-18T08:05:00+00:00",
            "mission-utility",
            {
                "work_item_ref": "work-item://utility/1",
                "work_item_status": "active",
                "previous_work_item_status": None,
            },
        ),
        event(
            "event-work-complete",
            "work_item_state_changed",
            "2026-07-18T08:10:00+00:00",
            "mission-utility",
            {
                "work_item_ref": "work-item://utility/1",
                "work_item_status": "completed",
                "previous_work_item_status": "active",
            },
        ),
        event(
            "event-work-rework",
            "work_item_state_changed",
            "2026-07-18T08:20:00+00:00",
            "mission-utility",
            {
                "work_item_ref": "work-item://utility/1",
                "work_item_status": "active",
                "previous_work_item_status": "completed",
            },
        ),
        event(
            "event-artifact",
            "artifact_lifecycle_state_changed",
            "2026-07-18T08:30:00+00:00",
            "mission-utility",
            {"resulting_artifact_ref": "artifact://utility/1"},
        ),
        event(
            "event-feedback",
            "operator_feedback_recorded",
            "2026-07-18T08:40:00+00:00",
            "mission-utility",
            {"operator_feedback_assessment": "helpful"},
        ),
    ]
    states = [
        MissionStateContract(
            mission_id="mission-utility",
            mission_goal="Complete the operator utility slice",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-18T08:40:00+00:00",
        ),
        MissionStateContract(
            mission_id="mission-stale-loop",
            mission_goal="Resume an unattended loop",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-14T08:00:00+00:00",
            open_loops=["open-loop://stale/1"],
            open_loop_states=[
                OpenLoopStateContract(
                    open_loop_ref="open-loop://stale/1",
                    mission_id="mission-stale-loop",
                    loop_summary="Review the unattended mission.",
                )
            ],
        ),
    ]

    report = ObservabilityService.build_daily_operator_utility_report(
        report_id="operator-utility-report://test",
        events=events,
        mission_states=states,
        period_start="2026-07-18T00:00:00+00:00",
        period_end="2026-07-18T12:00:00+00:00",
        generated_at="2026-07-18T12:00:00+00:00",
    )

    assert report.mission_count == 2
    assert report.event_count == 6
    assert report.observed_work_item_count == 1
    assert report.completed_work_item_count == 1
    assert report.completion_rate == 1.0
    assert report.reworked_work_item_count == 1
    assert report.rework_rate == 1.0
    assert report.observed_artifact_count == 1
    assert report.resume_count == 1
    assert report.stale_open_loop_count == 1
    assert report.feedback_count == 1
    assert report.feedback_coverage == 0.5
    assert report.helpful_feedback_rate == 1.0
    assert report.time_to_next_action_observation_count == 1
    assert report.average_time_to_next_action_seconds == 300.0
    assert report.saved_time_claim_status == "not_claimed_without_controlled_baseline"
    assert report.read_only is True


def test_daily_operator_utility_report_surfaces_missing_period_evidence() -> None:
    report = ObservabilityService.build_daily_operator_utility_report(
        report_id="operator-utility-report://limited",
        events=[
            InternalEventEnvelope(
                event_id="event-invalid-time",
                event_name="work_item_state_changed",
                timestamp="invalid",
                source_service="orchestrator-service",
                mission_id="mission-limited",
                payload={"work_item_ref": "work-item://limited/1"},
            )
        ],
        mission_states=[],
        period_start="2026-07-17T00:00:00+00:00",
        period_end="2026-07-18T00:00:00+00:00",
        generated_at="2026-07-18T12:00:00+00:00",
        source_event_limit_reached=True,
    )

    assert report.report_status == "insufficient_evidence"
    assert report.completion_rate is None
    assert report.rework_rate is None
    assert report.helpful_feedback_rate is None
    assert report.average_time_to_next_action_seconds is None
    assert report.stale_open_loop_count is None
    assert "invalid_or_missing_event_timestamp" in report.limitations
    assert "event_query_limit_reached_period_may_be_incomplete" in report.limitations
    assert "historical_stale_loop_snapshot_not_available" in report.limitations


def test_longitudinal_learning_report_detects_sustained_runtime_gain() -> None:
    baseline_ref = "baseline://reviewed-memory/software-change"
    guidance_ref = "reviewed-learning-guidance://software-change/1.0.0"
    targets = [
        learning_target(version_ref=baseline_ref, runtime_status="active_baseline"),
        learning_target(
            version_ref=guidance_ref,
            baseline_version_ref=baseline_ref,
        ),
    ]
    observations = [
        learning_observation(
            observation_id="baseline-1",
            version_ref=baseline_ref,
            success=True,
            score=0.6,
            rework_count=1,
            feedback="not_helpful",
        ),
        learning_observation(
            observation_id="baseline-2",
            version_ref=baseline_ref,
            success=False,
            score=0.4,
            rework_count=1,
            feedback="not_helpful",
        ),
        learning_observation(
            observation_id="guidance-1",
            version_ref=guidance_ref,
            success=True,
            score=0.9,
            rework_count=0,
            feedback="helpful",
        ),
        learning_observation(
            observation_id="guidance-2",
            version_ref=guidance_ref,
            success=True,
            score=1.0,
            rework_count=0,
            feedback="helpful",
        ),
    ]

    report = ObservabilityService.build_longitudinal_learning_report(
        report_id="longitudinal-learning-report://sustained-gain",
        targets=targets,
        observations=observations,
        generated_at="2026-07-16T12:00:00Z",
        minimum_observations=2,
    )

    guidance_metric = next(
        metric for metric in report.version_metrics if metric.version_ref == guidance_ref
    )
    assert report.report_status == "sustained_gain_observed"
    assert guidance_metric.trend_status == "sustained_gain"
    assert guidance_metric.success_rate_delta == 0.5
    assert guidance_metric.rework_rate_delta == -1.0
    assert guidance_metric.helpful_feedback_rate == 1.0
    assert report.read_only is True
    assert report.promotion_authorized is False
    assert report.automatic_promotion_allowed is False
    assert report.core_mutation_allowed is False


def test_longitudinal_learning_report_surfaces_regression_and_rollback_once() -> None:
    baseline_ref = "baseline://reviewed-memory/software-change"
    guidance_ref = "reviewed-learning-guidance://software-change/2.0.0"
    report = ObservabilityService.build_longitudinal_learning_report(
        report_id="longitudinal-learning-report://rollback",
        targets=[
            learning_target(version_ref=baseline_ref, runtime_status="active_baseline"),
            learning_target(
                version_ref=guidance_ref,
                baseline_version_ref=baseline_ref,
                rollback_status="rolled_back",
                rollback_plan_ref="rollback://guidance/2.0.0",
            ),
        ],
        observations=[
            learning_observation(
                observation_id="baseline-1",
                version_ref=baseline_ref,
                success=True,
                score=1.0,
                rework_count=0,
                feedback="helpful",
            ),
            learning_observation(
                observation_id="baseline-2",
                version_ref=baseline_ref,
                success=True,
                score=1.0,
                rework_count=0,
                feedback="helpful",
            ),
            learning_observation(
                observation_id="guidance-1",
                version_ref=guidance_ref,
                success=False,
                score=0.2,
                rework_count=1,
                feedback="correction",
                regression_flags=["operator_feedback:correction"],
            ),
            learning_observation(
                observation_id="guidance-2",
                version_ref=guidance_ref,
                success=False,
                score=0.3,
                rework_count=1,
                feedback="not_helpful",
                regression_flags=["operator_feedback:not_helpful"],
            ),
        ],
        generated_at="2026-07-16T12:00:00Z",
    )

    guidance_metric = next(
        metric for metric in report.version_metrics if metric.version_ref == guidance_ref
    )
    assert report.report_status == "attention_required"
    assert guidance_metric.trend_status == "regression_or_rollback_observed"
    assert guidance_metric.regression_count == 2
    assert guidance_metric.rollback_count == 1
    assert report.rollback_refs == ["rollback://guidance/2.0.0"]


def test_longitudinal_learning_report_rejects_inactive_runtime_and_authority_claims() -> None:
    target = learning_target(
        version_ref="skill-candidate://unsafe/1.0.0",
        runtime_status="inactive_candidate",
    )
    target.runtime_activation_allowed = True
    observation = learning_observation(
        observation_id="inactive-runtime",
        version_ref=target.version_ref,
        success=True,
        score=1.0,
        rework_count=0,
        feedback="helpful",
    )
    observation.promotion_authorized = True

    report = ObservabilityService.build_longitudinal_learning_report(
        report_id="longitudinal-learning-report://blocked",
        targets=[target],
        observations=[observation],
        generated_at="2026-07-16T12:00:00Z",
    )

    metric = report.version_metrics[0]
    assert report.report_status == "attention_required"
    assert metric.trend_status == "blocked"
    assert metric.blockers == [
        "inactive_target_has_runtime_observation",
        "observation_authority_claim_not_allowed",
        "target_authority_claim_not_allowed",
    ]
    assert "inactive_versions_have_no_valid_runtime_claim" in report.limitations


def test_observability_builds_bounded_regression_readiness_report() -> None:
    report = ObservabilityService.build_regression_readiness_report(
        report_id="regression-readiness://test",
        capability_results=[
            CapabilityReadinessContract(
                capability_id="OP-001",
                capability_name="Governed mission",
                source_status="implemented_baseline",
                scope_status="baseline",
                readiness_status="ready",
                score=100,
                target="Keep stable",
                dependencies="Core",
                next_slice="none",
                evidence_refs=["docs://map/OP-001"],
            ),
            CapabilityReadinessContract(
                capability_id="OBS-001",
                capability_name="Regression signal",
                source_status="missing",
                scope_status="candidate",
                readiness_status="missing",
                score=0,
                target="Add report",
                dependencies="Tools",
                next_slice="candidate",
                evidence_refs=["docs://map/OBS-001"],
            ),
        ],
        gate_mode="standard",
        gate_status="passed",
        test_status="passed",
        document_status="healthy",
        backlog_status="synchronized",
        next_ready_item="MB-174",
        status_drift=[],
        evidence_refs=["engineering-gate://standard/passed"],
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.status == "ready_with_known_gaps"
    assert report.overall_score == 65
    assert report.capability_counts["ready"] == 1
    assert report.capability_counts["missing"] == 1
    assert report.blockers == []
    assert report.warnings == [
        "longitudinal_learning_evidence:not_evaluated",
        "candidate_gaps:OBS-001",
    ]
    assert report.read_only is True
    assert report.autonomous_release_allowed is False


def test_observability_builds_bounded_recurring_pattern_report() -> None:
    experiences = [
        ExperienceRecordContract(
            experience_id=f"experience://pattern/{index}",
            mission_id=f"mission-pattern-{index}",
            workflow_profile="software_change_workflow",
            route="software_development",
            primary_domain_driver="software_engineering",
            outcome_status="completed",
            checkpoints=["run_targeted_tests", "run_standard_gate"],
            learned_patterns=["small_reversible_patch"],
            evidence_refs=[f"trace://pattern/{index}"],
            timestamp=f"2026-07-16T12:00:0{index}Z",
        )
        for index in (1, 2)
    ]
    reflections = [
        PostTaskReflectionContract(
            reflection_id=f"reflection://pattern/{index}",
            experience_id=f"experience://pattern/{index}",
            reflection_status="candidate",
            learning_candidate="small reversible patches reduced regression risk",
            recommendation="review the repeated workflow before reuse",
            evidence_refs=[f"trace://pattern/{index}"],
            timestamp=f"2026-07-16T12:01:0{index}Z",
        )
        for index in (1, 2)
    ]

    report = ObservabilityService.build_recurring_pattern_report(
        report_id="recurring-pattern-report://observability-test",
        experiences=experiences,
        reflections=reflections,
        minimum_occurrences=2,
        generated_at="2026-07-16T13:00:00Z",
    )

    assert report.report_status == "evidence_ready_for_human_review"
    assert report.eligible_pattern_count == 1
    assert report.patterns[0].pattern_type == "repeated_successful_workflow"
    assert report.patterns[0].recurring_signals == [
        "run_standard_gate",
        "run_targeted_tests",
        "small_reversible_patch",
    ]
    assert report.patterns[0].reflection_refs == [
        "reflection://pattern/1",
        "reflection://pattern/2",
    ]
    assert report.skill_candidate_generation_allowed is False
    assert report.automatic_skill_creation_allowed is False
    assert report.automatic_promotion_allowed is False


def test_observability_blocks_conflicting_recurring_pattern() -> None:
    experiences = [
        ExperienceRecordContract(
            experience_id="experience://pattern/completed",
            mission_id="mission-pattern-completed",
            workflow_profile="research_synthesis_workflow",
            route="research",
            primary_domain_driver="knowledge_and_communication",
            outcome_status="completed",
            evidence_refs=["trace://pattern/completed"],
            timestamp="2026-07-16T12:00:01Z",
        ),
        ExperienceRecordContract(
            experience_id="experience://pattern/partial",
            mission_id="mission-pattern-partial",
            workflow_profile="research_synthesis_workflow",
            route="research",
            primary_domain_driver="knowledge_and_communication",
            outcome_status="partial",
            evidence_refs=["trace://pattern/partial"],
            timestamp="2026-07-16T12:00:02Z",
        ),
    ]

    report = ObservabilityService.build_recurring_pattern_report(
        report_id="recurring-pattern-report://conflict-test",
        experiences=experiences,
        reflections=[],
        minimum_occurrences=2,
        generated_at="2026-07-16T13:00:00Z",
    )

    assert report.report_status == "attention_required"
    assert report.eligible_pattern_count == 0
    assert report.patterns[0].pattern_status == "conflict_detected"
    assert report.patterns[0].conflict_flags == ["mixed_outcomes"]
    assert "outcome_conflict_requires_review" in report.patterns[0].blockers
    assert report.patterns[0].skill_candidate_generation_allowed is False


def test_observability_requires_two_compatible_experiences() -> None:
    report = ObservabilityService.build_recurring_pattern_report(
        report_id="recurring-pattern-report://insufficient-test",
        experiences=[
            ExperienceRecordContract(
                experience_id="experience://pattern/single",
                mission_id="mission-pattern-single",
                workflow_profile="software_change_workflow",
                route="software_development",
                primary_domain_driver="software_engineering",
                outcome_status="completed",
                evidence_refs=["trace://pattern/single"],
                timestamp="2026-07-16T12:00:01Z",
            )
        ],
        reflections=[],
        minimum_occurrences=2,
        generated_at="2026-07-16T13:00:00Z",
    )

    assert report.report_status == "insufficient_evidence"
    assert report.patterns == []
    assert report.blockers == ["no_compatible_recurring_pattern"]


def skill_operator_pattern_report() -> RecurringPatternReportContract:
    experiences = [
        ExperienceRecordContract(
            experience_id=f"experience://skill-operator/{index}",
            mission_id=f"mission-skill-operator-{index}",
            workflow_profile="software_change_workflow",
            route="software_development",
            primary_domain_driver="software_engineering",
            outcome_status="completed",
            evidence_refs=[f"trace://skill-operator/{index}"],
            timestamp=f"2026-07-16T14:00:0{index}Z",
        )
        for index in (1, 2)
    ]
    reflections = [
        PostTaskReflectionContract(
            reflection_id=f"reflection://skill-operator/{index}",
            experience_id=f"experience://skill-operator/{index}",
            reflection_status="candidate",
            learning_candidate="verify release evidence before recommendation",
            recommendation="review bounded verification for reuse",
            evidence_refs=[f"trace://skill-operator/{index}"],
            timestamp=f"2026-07-16T14:01:0{index}Z",
        )
        for index in (1, 2)
    ]
    return ObservabilityService.build_recurring_pattern_report(
        report_id="recurring-pattern-report://skill-operator",
        experiences=experiences,
        reflections=reflections,
        minimum_occurrences=2,
        generated_at="2026-07-16T15:00:00Z",
    )


def skill_operator_candidate(pattern_id: str) -> SkillCandidateContract:
    return SkillCandidateContract(
        skill_candidate_id="skill-candidate://release-evidence/1.0.0",
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence and report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["trace://skill-operator/1", "trace://skill-operator/2"],
        source_pattern_refs=[pattern_id],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run skill sandbox tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T15:01:00Z",
    )


def skill_operator_proposal(
    candidate: SkillCandidateContract,
    *,
    review_status: str = "needs_review",
    sandbox_status: str | None = None,
    sandbox_blockers: list[str] | None = None,
) -> EvolutionProposalContract:
    strategy_context: dict[str, object] = {
        "evolution_review": {
            "review_status": review_status,
            "blockers": [],
            "requires_human_review": True,
        }
    }
    if sandbox_status is not None:
        strategy_context["skill_sandbox_eval"] = {
            "eval_id": "skill-sandbox-eval://release-evidence",
            "eval_status": sandbox_status,
            "pass_rate": 1.0 if not sandbox_blockers else 0.0,
            "blockers": list(sandbox_blockers or []),
        }
    return EvolutionProposalContract(
        evolution_proposal_id="proposal-skill-release-evidence",
        proposal_type="skill_candidate",
        target_scope="skill:skill://release-evidence@1.0.0",
        hypothesis="sandbox release evidence verification",
        expected_gain="bounded reusable verification",
        timestamp="2026-07-16T15:02:00Z",
        baseline_refs=["baseline://sovereign-core/current"],
        risk_hint="moderate",
        proposed_tests=list(candidate.proposed_tests),
        candidate_refs=[candidate.skill_candidate_id],
        optimization_candidate_status="candidate",
        optimization_safety_status="sandbox_only",
        strategy_context=strategy_context,
    )


def test_observability_builds_pending_skill_operator_view() -> None:
    report = skill_operator_pattern_report()
    candidate = skill_operator_candidate(report.patterns[0].pattern_id)
    proposal = skill_operator_proposal(candidate)

    view = ObservabilityService.build_skill_evolution_operator_view(
        view_id="skill-evolution-view://pending",
        pattern_report=report,
        candidates=[candidate],
        proposals=[proposal],
        generated_at="2026-07-16T16:00:00Z",
    )

    assert view.view_status == "operator_action_required"
    assert view.items[0].evolution_status == "human_review_pending"
    assert view.items[0].next_operator_action == "review_skill_candidate"
    assert view.items[0].occurrence_count == 2
    assert view.items[0].route == "software_development"
    assert view.items[0].runtime_activation_allowed is False


def test_observability_keeps_passing_skill_pending_human_release() -> None:
    report = skill_operator_pattern_report()
    candidate = skill_operator_candidate(report.patterns[0].pattern_id)
    proposal = skill_operator_proposal(
        candidate,
        review_status="sandboxed",
        sandbox_status="passed_pending_release_gate",
    )

    view = ObservabilityService.build_skill_evolution_operator_view(
        view_id="skill-evolution-view://passed",
        pattern_report=report,
        candidates=[candidate],
        proposals=[proposal],
        generated_at="2026-07-16T16:00:00Z",
    )

    assert view.view_status == "release_review_required"
    assert view.items[0].sandbox_pass_rate == 1.0
    assert view.items[0].next_operator_action == "prepare_human_release_review"
    assert view.promotion_authorized is False
    assert view.automatic_promotion_allowed is False


def test_observability_surfaces_skill_sandbox_blockers() -> None:
    report = skill_operator_pattern_report()
    candidate = skill_operator_candidate(report.patterns[0].pattern_id)
    proposal = skill_operator_proposal(
        candidate,
        review_status="sandboxed",
        sandbox_status="blocked",
        sandbox_blockers=["sandbox_pass_rate_below_threshold"],
    )

    view = ObservabilityService.build_skill_evolution_operator_view(
        view_id="skill-evolution-view://blocked",
        pattern_report=report,
        candidates=[candidate],
        proposals=[proposal],
        generated_at="2026-07-16T16:00:00Z",
    )

    assert view.view_status == "attention_required"
    assert view.items[0].evolution_status == "blocked"
    assert "sandbox_pass_rate_below_threshold" in view.items[0].blockers
    assert view.items[0].next_operator_action == "resolve_evolution_blockers"


def test_observability_service_persists_and_filters_events() -> None:
    temp_dir = runtime_dir("observability")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    events = [
        InternalEventEnvelope(
            event_id="evt-1",
            event_name="input_received",
            timestamp="2026-03-18T00:00:00Z",
            source_service="orchestrator-service",
            payload={"content": "hello"},
            request_id="req-1",
            session_id="sess-1",
            correlation_id="req-1",
            operation_id="op-1",
        ),
        InternalEventEnvelope(
            event_id="evt-2",
            event_name="memory_recorded",
            timestamp="2026-03-18T00:00:01Z",
            source_service="orchestrator-service",
            payload={"record": "ok"},
            request_id="req-2",
            session_id="sess-2",
            correlation_id="req-2",
        ),
    ]

    service.ingest_events(events)
    filtered = service.list_recent_events(ObservabilityQuery(request_id="req-1"))

    assert len(filtered) == 1
    assert filtered[0].event_name == "input_received"
    assert filtered[0].operation_id == "op-1"


def test_observability_event_delivery_is_exactly_idempotent() -> None:
    temp_dir = runtime_dir("observability-idempotent-delivery")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    event = InternalEventEnvelope(
        event_id="evt-outbox-stable",
        event_name="artifact_lifecycle_state_changed",
        timestamp="2026-08-30T12:00:00Z",
        source_service="orchestrator-service",
        payload={"outbox_id": "outbox://artifact/physical/stable"},
        mission_id="mission-artifact-physical",
        operation_id="operation-artifact-physical",
    )

    service.ingest_events([event, event])

    persisted = service.list_recent_events(
        ObservabilityQuery(mission_id="mission-artifact-physical")
    )
    assert persisted == [event]

    with pytest.raises(ValueError, match="event identity is immutable"):
        service.ingest_events(
            [
                replace(
                    event,
                    payload={"outbox_id": "outbox://artifact/physical/divergent"},
                )
            ]
        )


def test_observability_service_filters_event_names_before_limit() -> None:
    temp_dir = runtime_dir("observability-event-name-limit")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    relevant = InternalEventEnvelope(
        event_id="evt-relevant-before-noise",
        event_name="experience_recorded",
        timestamp="2026-03-18T00:00:00Z",
        source_service="orchestrator-service",
        payload={"experience_id": "experience://mission/1"},
        mission_id="mission-event-filter",
    )
    noise = [
        InternalEventEnvelope(
            event_id=f"evt-noise-{index}",
            event_name="unrelated_event",
            timestamp=f"2026-03-18T00:00:{index + 1:02d}Z",
            source_service="orchestrator-service",
            payload={},
            mission_id="mission-event-filter",
        )
        for index in range(10)
    ]
    service.ingest_events([relevant, *noise])

    filtered = service.list_recent_events(
        ObservabilityQuery(
            mission_id="mission-event-filter",
            event_names=("experience_recorded",),
            limit=1,
        )
    )

    assert [event.event_id for event in filtered] == [relevant.event_id]


def test_decision_outcome_attribution_report_links_only_exact_feedback() -> None:
    correlation = decision_attribution_record(suffix="correlation")
    declared = decision_attribution_record(
        suffix="declared",
        attribution_status="declared_causality",
    )
    feedback_events = [
        InternalEventEnvelope(
            event_id=f"evt-feedback-{index}",
            event_name="operator_feedback_recorded",
            timestamp=f"2026-08-11T12:00:0{index + 2}+00:00",
            source_service="orchestrator-service",
            payload={
                "operator_feedback_id": f"feedback://correlation/{index}",
                "operator_feedback_experience_id": correlation.experience_id,
                "operator_feedback_assessment": "helpful",
                "operator_feedback_rating": rating,
                "operator_feedback_evidence_refs": [
                    f"feedback-evidence://correlation/{index}"
                ],
            },
            mission_id=str(correlation.mission_id),
        )
        for index, rating in enumerate((5, 4), start=1)
    ]
    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://exact-feedback",
        records=[correlation, declared],
        events=[
            decision_attribution_event(
                correlation,
                event_id="evt-attribution-correlation",
            ),
            decision_attribution_event(
                declared,
                event_id="evt-attribution-declared",
            ),
            *feedback_events,
            InternalEventEnvelope(
                event_id="evt-unrelated-noise",
                event_name="response_synthesized",
                timestamp="2026-08-11T12:00:09+00:00",
                source_service="orchestrator-service",
                payload={"gain_claim_status": "gain_proven"},
                mission_id=str(correlation.mission_id),
            ),
        ],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "attribution_observed"
    assert report.record_count == 2
    assert report.correlation_only_count == 1
    assert report.declared_causality_count == 1
    assert report.insufficient_evidence_count == 0
    assert report.feedback_linked_count == 1
    assert report.comparator_count == 0
    assert report.failed_record_count == 0
    assert report.limitations == []
    correlation_item = report.items[0]
    assert correlation_item.attribution == correlation
    assert correlation_item.attribution.attribution_status == "correlation_only"
    assert correlation_item.feedback_status == "linked"
    assert correlation_item.feedback_refs == [
        "feedback://correlation/1",
        "feedback://correlation/2",
    ]
    assert correlation_item.feedback_assessments == ["helpful", "helpful"]
    assert correlation_item.feedback_ratings == [5, 4]
    assert correlation_item.comparator_status == "not_available"
    assert correlation_item.comparator_refs == []
    assert correlation_item.causal_effect_proven is False
    assert correlation_item.gain_claim_status == (
        "not_established_without_comparator"
    )
    assert correlation_item.promotion_authorized is False
    assert correlation_item.automatic_promotion_allowed is False
    assert report.causal_effect_proven is False
    assert report.gain_claim_status == "not_established_without_comparator"
    assert report.promotion_authorized is False
    assert report.automatic_promotion_allowed is False


def test_decision_outcome_attribution_report_contains_mismatch_and_conflict() -> None:
    record = decision_attribution_record(
        suffix="adversarial",
        attribution_status="declared_causality",
    )
    unsafe_recorded = replace(
        decision_attribution_event(
            record,
            event_id="evt-attribution-unsafe",
            mission_id="mission-other",
            payload_overrides={
                "mission_id": "mission-other",
                "causal_effect_proven": True,
                "gain_claim_status": "gain_proven",
                "promotion_authorized": True,
            },
        ),
        request_id="req-attribution-wrong-envelope",
    )
    failed = decision_attribution_event(
        record,
        event_id="evt-attribution-failed",
        event_name="decision_outcome_attribution_failed",
        payload_overrides={
            "attribution_status": "insufficient_evidence",
            "failure_reason": "canonical_record_write_failed",
        },
    )
    exact_feedback = [
        InternalEventEnvelope(
            event_id=f"evt-feedback-conflict-{index}",
            event_name="operator_feedback_recorded",
            timestamp=f"2026-08-11T12:01:0{index}+00:00",
            source_service="orchestrator-service",
            payload={
                "operator_feedback_id": f"feedback://adversarial/{index}",
                "operator_feedback_experience_id": record.experience_id,
                "operator_feedback_assessment": assessment,
                "operator_feedback_rating": rating,
            },
            mission_id=str(record.mission_id),
        )
        for index, (assessment, rating) in enumerate(
            (("helpful", 5), ("not_helpful", 1)),
            start=1,
        )
    ]
    wrong_mission_feedback = InternalEventEnvelope(
        event_id="evt-feedback-wrong-mission",
        event_name="operator_feedback_recorded",
        timestamp="2026-08-11T12:01:10+00:00",
        source_service="orchestrator-service",
        payload={
            "operator_feedback_id": "feedback://wrong-mission",
            "operator_feedback_experience_id": record.experience_id,
            "operator_feedback_assessment": "helpful",
        },
        mission_id="mission-other",
    )
    wrong_experience_feedback = InternalEventEnvelope(
        event_id="evt-feedback-wrong-experience",
        event_name="operator_feedback_recorded",
        timestamp="2026-08-11T12:01:11+00:00",
        source_service="orchestrator-service",
        payload={
            "operator_feedback_id": "feedback://wrong-experience",
            "operator_feedback_experience_id": "experience://unknown",
            "operator_feedback_assessment": "helpful",
        },
        mission_id=str(record.mission_id),
    )

    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://adversarial",
        records=[record],
        events=[
            unsafe_recorded,
            failed,
            *exact_feedback,
            wrong_mission_feedback,
            wrong_experience_feedback,
        ],
        generated_at="2026-08-11T13:00:00+00:00",
        source_event_limit_reached=True,
    )

    item = report.items[0]
    assert report.report_status == "measured_with_limitations"
    assert report.failed_record_count == 1
    assert report.feedback_linked_count == 1
    assert report.declared_causality_count == 0
    assert report.insufficient_evidence_count == 1
    assert item.attribution is record
    assert item.attribution.attribution_status == "declared_causality"
    assert (
        "effective_attribution_downgraded_to_insufficient_evidence"
        in item.limitations
    )
    assert item.feedback_status == "conflicting"
    assert item.feedback_refs == [
        "feedback://adversarial/1",
        "feedback://adversarial/2",
    ]
    assert item.feedback_assessments == ["helpful", "not_helpful"]
    assert item.feedback_ratings == [5, 1]
    assert "multiple_attribution_events_for_record" in item.limitations
    assert "attribution_failed_event_observed" in item.limitations
    assert "feedback_assessment_conflict" in item.limitations
    assert (
        "feedback_mission_mismatch:evt-feedback-wrong-mission"
        in item.limitations
    )
    assert any(
        "attribution_event_mission_id_mismatch" in limitation
        for limitation in item.limitations
    )
    assert any(
        "attribution_event_request_id_envelope_conflict" in limitation
        for limitation in item.limitations
    )
    assert any(
        "attribution_event_causal_effect_claim" in limitation
        for limitation in item.limitations
    )
    assert any(
        "attribution_event_gain_claim" in limitation
        for limitation in item.limitations
    )
    assert any(
        "attribution_event_authority_claim" in limitation
        for limitation in item.limitations
    )
    assert "source_event_limit_reached" in report.limitations
    assert any(
        "feedback_without_canonical_experience:evt-feedback-wrong-experience"
        == limitation
        for limitation in report.limitations
    )
    assert wrong_mission_feedback.event_id not in item.evidence_refs
    assert wrong_experience_feedback.event_id not in item.evidence_refs
    assert item.causal_effect_proven is False
    assert item.gain_claim_status == "not_established_without_comparator"
    assert report.causal_effect_proven is False
    assert report.promotion_authorized is False


def test_decision_outcome_attribution_report_preserves_duplicate_records() -> None:
    record = decision_attribution_record(suffix="duplicate")
    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://duplicates",
        records=[record, record],
        events=[
            decision_attribution_event(
                record,
                event_id="evt-attribution-duplicate",
            )
        ],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "measured_with_limitations"
    assert report.record_count == 2
    assert report.correlation_only_count == 0
    assert report.insufficient_evidence_count == 2
    assert len(report.items) == 2
    assert [item.attribution for item in report.items] == [record, record]
    assert report.items[0].item_id != report.items[1].item_id
    assert all(
        "duplicate_attribution_record_id" in item.limitations
        for item in report.items
    )


def test_decision_outcome_attribution_report_downgrades_missing_or_duplicate_event() -> None:
    missing = decision_attribution_record(suffix="missing-recorded-event")
    duplicate = decision_attribution_record(
        suffix="duplicate-recorded-event",
        attribution_status="declared_causality",
    )
    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://event-cardinality",
        records=[missing, duplicate],
        events=[
            decision_attribution_event(
                duplicate,
                event_id="evt-attribution-duplicate-recorded-1",
            ),
            decision_attribution_event(
                duplicate,
                event_id="evt-attribution-duplicate-recorded-2",
            ),
        ],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "measured_with_limitations"
    assert report.correlation_only_count == 0
    assert report.declared_causality_count == 0
    assert report.insufficient_evidence_count == 2
    assert "recorded_attribution_event_missing" in report.items[0].limitations
    assert (
        "duplicate_recorded_attribution_event"
        in report.items[1].limitations
    )
    assert all(
        "effective_attribution_downgraded_to_insufficient_evidence"
        in item.limitations
        for item in report.items
    )


def test_decision_outcome_attribution_report_validates_canonical_classification() -> None:
    canonical = decision_attribution_record(
        suffix="classification-drift",
        attribution_status="declared_causality",
    )
    drifted = replace(canonical, workflow_policy_effects=[])
    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://classification-drift",
        records=[drifted],
        events=[
            decision_attribution_event(
                drifted,
                event_id="evt-attribution-classification-drift",
            )
        ],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "insufficient_evidence"
    assert report.declared_causality_count == 0
    assert report.insufficient_evidence_count == 1
    assert report.items[0].attribution is drifted
    assert (
        "canonical_record_validation_failed"
        in report.items[0].limitations
    )
    assert (
        "effective_attribution_downgraded_to_insufficient_evidence"
        in report.items[0].limitations
    )


def test_decision_outcome_attribution_report_rejects_extra_event_payload_keys() -> None:
    record = decision_attribution_record(
        suffix="unexpected-event-key",
        attribution_status="declared_causality",
    )
    event = decision_attribution_event(
        record,
        event_id="evt-attribution-unexpected-key",
        payload_overrides={"unexpected_effect_claim": True},
    )

    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://unexpected-event-key",
        records=[record],
        events=[event],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "measured_with_limitations"
    assert report.declared_causality_count == 0
    assert report.insufficient_evidence_count == 1
    assert (
        "attribution_event_payload_keys_mismatch:evt-attribution-unexpected-key"
        in report.items[0].limitations
    )
    assert (
        "effective_attribution_downgraded_to_insufficient_evidence"
        in report.items[0].limitations
    )


def test_decision_outcome_attribution_report_requires_observed_feedback_mission() -> None:
    record = decision_attribution_record(suffix="missing-feedback-mission")
    feedback = InternalEventEnvelope(
        event_id="evt-feedback-without-mission",
        event_name="operator_feedback_recorded",
        timestamp="2026-08-11T12:01:00+00:00",
        source_service="orchestrator-service",
        payload={
            "operator_feedback_id": "feedback://missing-mission",
            "operator_feedback_experience_id": record.experience_id,
            "operator_feedback_assessment": "helpful",
        },
    )
    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://missing-feedback-mission",
        records=[record],
        events=[
            decision_attribution_event(
                record,
                event_id="evt-attribution-missing-feedback-mission",
            ),
            feedback,
        ],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "measured_with_limitations"
    assert report.feedback_linked_count == 0
    assert report.items[0].feedback_status == "not_available"
    assert report.items[0].feedback_refs == []
    assert (
        "feedback_mission_mismatch:evt-feedback-without-mission"
        in report.items[0].limitations
    )
    assert (
        "feedback_event_missing_mission_id:evt-feedback-without-mission"
        in report.limitations
    )


def test_decision_outcome_attribution_report_never_materializes_event_only_item() -> None:
    unpersisted = decision_attribution_record(suffix="event-only")
    event = decision_attribution_event(
        unpersisted,
        event_id="evt-attribution-without-canonical-record",
    )

    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://event-only",
        records=[],
        events=[event],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "insufficient_evidence"
    assert report.record_count == 0
    assert report.items == []
    assert report.failed_record_count == 0
    assert report.limitations == [
        "attribution_event_without_canonical_record:"
        "evt-attribution-without-canonical-record"
    ]
    assert report.causal_effect_proven is False
    assert report.gain_claim_status == "not_established_without_comparator"
    assert report.promotion_authorized is False


def test_decision_outcome_attribution_report_counts_unique_failed_without_record() -> None:
    unpersisted = decision_attribution_record(suffix="failed-without-record")
    failed = decision_attribution_event(
        unpersisted,
        event_id="evt-attribution-failed-without-record",
        event_name="decision_outcome_attribution_failed",
        payload_overrides={
            "attribution_status": "insufficient_evidence",
            "failure_reason": "canonical_record_write_failed",
        },
    )
    duplicate_failed = replace(
        failed,
        timestamp="2026-08-11T12:00:02+00:00",
    )

    report = ObservabilityService.build_decision_outcome_attribution_report(
        report_id="decision-outcome-attribution-report://failed-without-record",
        records=[],
        events=[failed, duplicate_failed],
        generated_at="2026-08-11T13:00:00+00:00",
    )

    assert report.report_status == "insufficient_evidence"
    assert report.record_count == 0
    assert report.items == []
    assert report.failed_record_count == 1
    assert "failed_without_record" in report.limitations
    assert (
        "failed_without_record:evt-attribution-failed-without-record"
        in report.limitations
    )
    assert (
        "duplicate_failed_event_id:evt-attribution-failed-without-record"
        in report.limitations
    )
    assert report.evidence_refs == [
        "evt-attribution-failed-without-record"
    ]


def test_flow_audit_projects_decision_outcome_attribution_safely() -> None:
    temp_dir = runtime_dir("observability-decision-outcome-attribution-audit")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    recorded = decision_attribution_record(suffix="audit-recorded")
    failed = decision_attribution_record(suffix="audit-failed")
    recorded_event = decision_attribution_event(
        recorded,
        event_id="evt-attribution-audit-recorded",
    )
    failed_event = decision_attribution_event(
        failed,
        event_id="evt-attribution-audit-failed",
        event_name="decision_outcome_attribution_failed",
        payload_overrides={
            "attribution_status": "insufficient_evidence",
            "failure_reason": "canonical_record_unavailable",
            "causal_effect_proven": True,
            "gain_claim_status": "gain_proven",
        },
    )
    legacy_event = InternalEventEnvelope(
        event_id="evt-attribution-audit-legacy",
        event_name="response_synthesized",
        timestamp="2026-08-11T12:02:00+00:00",
        source_service="orchestrator-service",
        payload={},
        request_id="req-attribution-legacy",
        session_id="sess-attribution-legacy",
        mission_id="mission-attribution-legacy",
    )
    service.ingest_events([recorded_event, failed_event, legacy_event])

    recorded_audit = service.audit_flow(
        ObservabilityQuery(request_id=str(recorded.request_id))
    )
    failed_audit = service.audit_flow(
        ObservabilityQuery(request_id=str(failed.request_id))
    )
    legacy_audit = service.audit_flow(
        ObservabilityQuery(request_id="req-attribution-legacy")
    )

    assert recorded_audit.decision_outcome_attribution_record_id == (
        recorded.attribution_record_id
    )
    assert recorded_audit.decision_outcome_attribution_status == "correlation_only"
    assert recorded_audit.decision_outcome_attribution_evidence_refs == [
        recorded_event.event_id,
        *recorded.evidence_refs,
    ]
    assert recorded_audit.causal_effect_proven is False
    assert recorded_audit.gain_claim_status == (
        "not_established_without_comparator"
    )
    assert "decision_outcome_attribution_failed" not in recorded_audit.anomaly_flags

    assert failed_audit.decision_outcome_attribution_record_id == (
        failed.attribution_record_id
    )
    assert failed_audit.decision_outcome_attribution_status == "insufficient_evidence"
    assert failed_audit.causal_effect_proven is False
    assert failed_audit.gain_claim_status == "not_established_without_comparator"
    assert "decision_outcome_attribution_failed" in failed_audit.anomaly_flags
    assert (
        "decision_outcome_causal_effect_claim_not_allowed"
        in failed_audit.anomaly_flags
    )
    assert "decision_outcome_gain_claim_not_allowed" in failed_audit.anomaly_flags

    assert legacy_audit.decision_outcome_attribution_record_id is None
    assert legacy_audit.decision_outcome_attribution_status == "not_applicable"
    assert legacy_audit.decision_outcome_attribution_evidence_refs == []
    assert legacy_audit.causal_effect_proven is False
    assert legacy_audit.gain_claim_status == "not_applicable"


def test_observability_service_exports_trace_view() -> None:
    temp_dir = runtime_dir("observability-export")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:02Z",
                source_service="orchestrator-service",
                payload={"intent": "planning", "status": "ok"},
                request_id="req-3",
                session_id="sess-3",
                correlation_id="req-3",
            )
        ]
    )

    trace_view = service.export_trace_view(ObservabilityQuery(request_id="req-3"))

    assert len(trace_view) == 1
    assert trace_view[0]["name"] == "response_synthesized"
    assert trace_view[0]["payload_keys"] == ["intent", "status"]


def test_observability_service_mirrors_events_to_agentic_adapter() -> None:
    temp_dir = runtime_dir("observability-agentic")
    mirror_path = temp_dir / "agentic.jsonl"
    service = ObservabilityService(
        database_path=str(temp_dir / "observability.db"),
        agentic_adapter=JsonlAgenticMirrorAdapter(mirror_path),
    )
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:03Z",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-4",
                session_id="sess-4",
                correlation_id="req-4",
                operation_id="op-4",
            )
        ]
    )

    mirrored_lines = mirror_path.read_text(encoding="utf-8").splitlines()
    assert len(mirrored_lines) == 2
    root_event = loads(mirrored_lines[0])
    mirrored_event = loads(mirrored_lines[1])
    assert root_event["name"] == "jarvis_trace"
    assert root_event["total_events"] == 1
    assert mirrored_event["name"] == "response_synthesized"
    assert mirrored_event["operation_id"] == "op-4"


def test_observability_service_summarizes_flow_metrics() -> None:
    temp_dir = runtime_dir("observability-metrics")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "hello"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"status": "completed"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
                operation_id="op-5",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"record": "ok"},
                request_id="req-5",
                session_id="sess-5",
                correlation_id="req-5",
            ),
        ]
    )

    metrics = service.summarize_flow(ObservabilityQuery(request_id="req-5"))

    assert metrics.total_events == 3
    assert metrics.completed_operations == 1
    assert metrics.memory_writes == 1
    assert metrics.duration_seconds == 3.0


def test_observability_service_audits_flow_for_missing_events_and_anomalies() -> None:
    temp_dir = runtime_dir("observability-audit")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-a1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
            ),
            InternalEventEnvelope(
                event_id="evt-a2",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
            ),
            InternalEventEnvelope(
                event_id="evt-a3",
                event_name="operation_dispatched",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"operation_id": "op-audit"},
                request_id="req-audit",
                session_id="sess-audit",
                correlation_id="req-audit",
                operation_id="op-audit",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-audit"))

    assert audit.request_id == "req-audit"
    assert "memory_recovered" in audit.missing_required_events
    assert "continuity_decided" in audit.missing_required_events
    assert "operation_missing_completion" in audit.anomaly_flags
    assert audit.workflow_trace_status == "not_applicable"
    assert "continuity_decided" in audit.missing_continuity_signals
    assert audit.trace_complete is False


def test_observability_service_audits_technology_absorption_signals() -> None:
    temp_dir = runtime_dir("observability-technology-absorption")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-tech-1",
                event_name="technology_absorption_candidate_declared",
                timestamp="2026-05-17T00:00:00+00:00",
                source_service="evolution-lab",
                payload={
                    "technology_absorption_readiness": "ready_for_manual_review",
                    "technology_absorption_decision": "manual_promotion_review",
                    "technology_absorption_lane_status": "controlled_candidate",
                    "technology_absorption_promotion_readiness": "manual_review_only",
                    "technology_absorption_blockers": [],
                    "technology_absorption_candidate_refs": [
                        "tech-candidate://openai-agents-sdk/handoff-adapters"
                    ],
                },
                request_id="req-tech",
                session_id="sess-tech",
                correlation_id="req-tech",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-tech"))

    assert audit.technology_absorption_readiness == "ready_for_manual_review"
    assert audit.technology_absorption_decision == "manual_promotion_review"
    assert audit.technology_absorption_promotion_readiness == "manual_review_only"
    assert audit.technology_absorption_candidate_refs == [
        "tech-candidate://openai-agents-sdk/handoff-adapters"
    ]
    assert "technology_candidate_observed" in audit.technology_absorption_signals
    assert (
        "technology_absorption_manual_review_required"
        in audit.technology_absorption_signals
    )


def test_observability_service_audits_experience_reflection_signals() -> None:
    temp_dir = runtime_dir("observability-experience-reflection")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-er-1",
                event_name="post_task_reflection_declared",
                timestamp="2026-05-17T00:00:00+00:00",
                source_service="evolution-lab",
                payload={
                    "experience_reflection_status": "candidate",
                    "experience_reflection_change_type": "workflow",
                    "experience_reflection_refs": [
                        "experience://mission-er/001",
                        "reflection://mission-er/001",
                    ],
                    "experience_reflection_blockers": [],
                },
                request_id="req-er",
                session_id="sess-er",
                mission_id="mission-er",
                correlation_id="req-er",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-er"))

    assert audit.experience_reflection_status == "candidate"
    assert audit.experience_reflection_change_type == "workflow"
    assert audit.experience_reflection_refs == [
        "experience://mission-er/001",
        "reflection://mission-er/001",
    ]
    assert "experience_reflection_observed" in audit.experience_reflection_signals
    assert (
        "experience_reflection_manual_review_required"
        in audit.experience_reflection_signals
    )


def test_observability_service_audits_reflection_influence_signals() -> None:
    temp_dir = runtime_dir("observability-reflection-influence")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-ri-1",
                event_name="plan_built",
                timestamp="2026-03-19T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "reflection_influence_status": "applied",
                    "reflection_influence_refs": ["reflection://mission-ri/001"],
                    "reflection_influence_summary": "usar criterio anterior",
                },
                request_id="req-ri",
                session_id="sess-ri",
                mission_id="mission-ri",
                correlation_id="req-ri",
            ),
            InternalEventEnvelope(
                event_id="evt-ri-2",
                event_name="response_synthesized",
                timestamp="2026-03-19T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "reflection_influence_status": "applied",
                    "reflection_influence_refs": ["reflection://mission-ri/001"],
                },
                request_id="req-ri",
                session_id="sess-ri",
                mission_id="mission-ri",
                correlation_id="req-ri",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-ri"))

    assert audit.reflection_influence_status == "applied"
    assert audit.reflection_influence_refs == ["reflection://mission-ri/001"]
    assert audit.reflection_influence_summary == "usar criterio anterior"
    assert audit.reflection_assisted_eval_status == "reflection_assisted"


def test_observability_service_audits_reviewed_learning_influence_signals() -> None:
    temp_dir = runtime_dir("observability-reviewed-learning")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-rl-1",
                event_name="plan_built",
                timestamp="2026-05-17T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "reviewed_learning_influence_status": "applied",
                    "reviewed_learning_influence_refs": [
                        "reviewed-learning://guidance/001"
                    ],
                    "reviewed_learning_influence_summary": (
                        "preservar decisao revisada"
                    ),
                    "reviewed_learning_influence_reason": "workflow_match",
                },
                request_id="req-rl",
                session_id="sess-rl",
                mission_id="mission-rl",
                correlation_id="req-rl",
            ),
            InternalEventEnvelope(
                event_id="evt-rl-2",
                event_name="response_synthesized",
                timestamp="2026-05-17T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "reviewed_learning_influence_status": "applied",
                    "reviewed_learning_influence_refs": [
                        "reviewed-learning://guidance/001"
                    ],
                },
                request_id="req-rl",
                session_id="sess-rl",
                mission_id="mission-rl",
                correlation_id="req-rl",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-rl"))

    assert audit.reviewed_learning_influence_status == "applied"
    assert audit.reviewed_learning_influence_refs == [
        "reviewed-learning://guidance/001"
    ]
    assert audit.reviewed_learning_influence_summary == "preservar decisao revisada"
    assert audit.reviewed_learning_influence_reason == "workflow_match"
    assert audit.reviewed_learning_assisted_eval_status == (
        "reviewed_learning_assisted"
    )
    assert audit.reviewed_learning_release_conclusion == (
        "no_promotion_without_release_gate"
    )


def test_observability_service_audits_evolution_review_decision() -> None:
    temp_dir = runtime_dir("observability-evolution-review")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-review-1",
                event_name="evolution_review_decision_declared",
                timestamp="2026-05-17T00:00:00+00:00",
                source_service="evolution-lab",
                payload={
                    "evolution_review_decision_status": "approved",
                    "evolution_review_decision": "approve",
                    "evolution_proposal_id": "proposal-123",
                    "operator_ref": "operator://human",
                    "evolution_review_evidence_refs": ["evidence://eval/123"],
                    "rollback_plan_ref": "rollback://proposal-123",
                    "automatic_promotion_allowed": False,
                    "core_mutation_allowed": False,
                },
                request_id="req-review",
                session_id="sess-review",
                mission_id="mission-review",
                correlation_id="req-review",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-review"))

    assert audit.evolution_review_decision_status == "approved"
    assert audit.evolution_review_decision == "approve"
    assert audit.evolution_review_proposal_id == "proposal-123"
    assert audit.evolution_review_operator_ref == "operator://human"
    assert audit.evolution_review_evidence_refs == ["evidence://eval/123"]
    assert audit.evolution_review_rollback_plan_ref == "rollback://proposal-123"
    assert "automatic_promotion_blocked" in audit.evolution_review_limits
    assert "core_mutation_blocked" in audit.evolution_review_limits


def test_observability_service_audits_promotion_gate_decision() -> None:
    temp_dir = runtime_dir("observability-promotion-gate")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-promotion-gate-1",
                event_name="promotion_gate_evaluated",
                timestamp="2026-07-16T00:00:00+00:00",
                source_service="evolution-lab",
                payload={
                    "promotion_gate_id": "promotion-gate://proposal-123",
                    "promotion_gate_checklist_id": (
                        "sandbox-release-checklist://proposal-123"
                    ),
                    "evolution_proposal_id": "proposal-123",
                    "promotion_gate_release_scope": "workflow:software_change",
                    "promotion_gate_status": "blocked",
                    "promotion_gate_decision": "promotion_blocked",
                    "promotion_gate_release_conclusion": (
                        "promotion_blocked_by_release_gate"
                    ),
                    "promotion_gate_required_gates": [
                        "human_review",
                        "standard_engineering_gate",
                        "release_gate_before_promotion",
                    ],
                    "promotion_gate_completed_gates": [
                        "human_review",
                        "standard_engineering_gate",
                    ],
                    "promotion_gate_missing_gates": [
                        "release_gate_before_promotion"
                    ],
                    "promotion_gate_evidence_refs": ["evidence://eval/123"],
                    "promotion_gate_blockers": [
                        "gate_not_completed:release_gate_before_promotion"
                    ],
                    "promotion_gate_human_review_status": "approved",
                    "promotion_gate_promotion_eligible": False,
                    "promotion_gate_human_decision_required": True,
                    "promotion_gate_promotion_authorized": False,
                    "automatic_promotion_allowed": False,
                    "core_mutation_allowed": False,
                },
                request_id="req-promotion-gate",
                session_id="sess-promotion-gate",
                mission_id="mission-promotion-gate",
                correlation_id="req-promotion-gate",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-promotion-gate"))

    assert audit.promotion_gate_status == "blocked"
    assert audit.promotion_gate_decision == "promotion_blocked"
    assert audit.promotion_gate_id == "promotion-gate://proposal-123"
    assert audit.promotion_gate_checklist_id == (
        "sandbox-release-checklist://proposal-123"
    )
    assert audit.promotion_gate_release_scope == "workflow:software_change"
    assert audit.promotion_gate_release_conclusion == (
        "promotion_blocked_by_release_gate"
    )
    assert audit.promotion_gate_missing_gates == ["release_gate_before_promotion"]
    assert audit.promotion_gate_evidence_refs == ["evidence://eval/123"]
    assert audit.promotion_gate_blockers == [
        "gate_not_completed:release_gate_before_promotion"
    ]
    assert audit.promotion_gate_human_review_status == "approved"
    assert audit.promotion_gate_promotion_eligible is False
    assert audit.promotion_gate_human_decision_required is True
    assert audit.promotion_gate_promotion_authorized is False


def test_observability_service_audits_operator_feedback() -> None:
    temp_dir = runtime_dir("observability-operator-feedback")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-operator-feedback-1",
                event_name="operator_feedback_recorded",
                timestamp="2026-07-16T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "operator_feedback_status": "recorded_bounded",
                    "operator_feedback_id": "operator-feedback://mission-123/001",
                    "operator_feedback_experience_id": "experience://mission-123/001",
                    "operator_feedback_assessment": "not_helpful",
                    "operator_feedback_rating": 2,
                    "operator_feedback_evidence_refs": [
                        "evidence://mission-123/operator"
                    ],
                    "operator_feedback_evolution_review_status": "needs_review",
                    "operator_feedback_human_review_required": True,
                    "operator_feedback_automatic_promotion_allowed": False,
                    "operator_feedback_core_mutation_allowed": False,
                },
                request_id="req-operator-feedback",
                session_id="sess-operator-feedback",
                mission_id="mission-123",
                correlation_id="req-operator-feedback",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-operator-feedback"))

    assert audit.operator_feedback_status == "recorded_bounded"
    assert audit.operator_feedback_id == "operator-feedback://mission-123/001"
    assert audit.operator_feedback_experience_id == "experience://mission-123/001"
    assert audit.operator_feedback_assessment == "not_helpful"
    assert audit.operator_feedback_rating == 2
    assert audit.operator_feedback_evidence_refs == [
        "evidence://mission-123/operator"
    ]
    assert audit.operator_feedback_evolution_review_status == "needs_review"
    assert audit.operator_feedback_human_review_required is True
    assert audit.operator_feedback_automatic_promotion_allowed is False
    assert audit.operator_feedback_core_mutation_allowed is False


def test_observability_service_audits_mission_progress_report() -> None:
    temp_dir = runtime_dir("observability-mission-progress")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mission-progress-1",
                event_name="mission_progress_report_generated",
                timestamp="2026-07-16T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "mission_progress_report_id": (
                        "mission-progress-report://mission-123"
                    ),
                    "mission_progress_report_status": "needs_operator_decision",
                    "mission_progress_summary": "pending_decisions=1",
                    "mission_progress_next_action_ref": "next_action:review",
                    "mission_progress_pending_decisions": [
                        "review_learning_candidate"
                    ],
                    "mission_progress_evidence_refs": ["evidence://mission-123"],
                    "mission_progress_memory_influence_refs": [
                        "memory://mission-123"
                    ],
                    "mission_progress_learning_refs": [
                        "reflection://mission-123/001"
                    ],
                    "mission_progress_risk_refs": ["risk://release-review"],
                    "memory_write_mode": "read_only",
                    "autonomous_execution_allowed": False,
                },
                request_id="req-mission-progress",
                session_id="sess-mission-progress",
                mission_id="mission-123",
                correlation_id="req-mission-progress",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-mission-progress"))

    assert audit.mission_progress_report_status == "needs_operator_decision"
    assert audit.mission_progress_report_id == (
        "mission-progress-report://mission-123"
    )
    assert audit.mission_progress_summary == "pending_decisions=1"
    assert audit.mission_progress_next_action_ref == "next_action:review"
    assert audit.mission_progress_pending_decisions == [
        "review_learning_candidate"
    ]
    assert audit.mission_progress_evidence_refs == ["evidence://mission-123"]
    assert audit.mission_progress_memory_influence_refs == [
        "memory://mission-123"
    ]
    assert audit.mission_progress_learning_refs == [
        "reflection://mission-123/001"
    ]
    assert audit.mission_progress_risk_refs == ["risk://release-review"]


def test_observability_service_audits_surface_continuity_signals() -> None:
    temp_dir = runtime_dir("observability-surface")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-surface-1",
                event_name="mission_runtime_state_declared",
                timestamp="2026-05-05T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "surface_continuity_status": "linked_surface",
                    "linked_surface_ids": [
                        "surface://jarvis_console",
                        "surface://operator_web",
                    ],
                    "surface_identity_conflict_flags": [],
                },
                request_id="req-surface",
                session_id="sess-surface",
                correlation_id="req-surface",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-surface"))

    assert audit.surface_continuity_status == "linked_surface"
    assert audit.linked_surface_count == 2
    assert audit.surface_identity_conflict_flags == []
    assert audit.multi_surface_readiness == "observable_not_promoted"


def test_observability_service_audits_project_objective_continuity_signals() -> None:
    temp_dir = runtime_dir("observability-objective")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-objective-1",
                event_name="objective_state_declared",
                timestamp="2026-05-13T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "project_ref": "project://jarvis",
                    "objective_ref": "objective://jarvis/persistent-objectives",
                    "work_item_refs": ["work-item://mb-110"],
                    "checkpoint_refs": ["checkpoint://contract-ready"],
                    "artifact_refs": ["artifact://plan.md"],
                    "objective_status": "active",
                    "next_action_ref": "next-action://define-contract",
                },
                request_id="req-objective",
                session_id="sess-objective",
                correlation_id="req-objective",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-objective"))

    assert audit.objective_continuity_status == "active"
    assert audit.active_work_item_count == 1
    assert audit.open_checkpoint_count == 1
    assert audit.artifact_continuity_status == "attached"
    assert audit.next_action_status == "ready"


def test_observability_service_audits_objective_operational_utility_signals() -> None:
    temp_dir = runtime_dir("observability-objective-utility")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-objective-read",
                event_name="objective_state_inspected",
                timestamp="2026-05-16T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "objective_consulted": True,
                    "objective_found": True,
                    "objective_status": "paused",
                    "work_item_refs": ["work-item://mb-118"],
                    "checkpoint_refs": ["checkpoint://operator-review"],
                    "artifact_refs": [],
                    "next_action_ref": None,
                },
                request_id="req-objective-utility",
                session_id="sess-objective-utility",
                correlation_id="req-objective-utility",
            ),
            InternalEventEnvelope(
                event_id="evt-objective-pause",
                event_name="mission_updated",
                timestamp="2026-05-16T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "transition": "pause",
                    "objective_status": "paused",
                    "next_action_ref": None,
                    "artifact_refs": [],
                },
                request_id="req-objective-utility",
                session_id="sess-objective-utility",
                correlation_id="req-objective-utility",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-objective-utility"))

    assert audit.objective_consulted is True
    assert audit.objective_transition_counts["pause"] == 1
    assert audit.objective_missing_next_action is True
    assert audit.objective_missing_artifact is True
    assert "objective_consulted" in audit.objective_utility_signals
    assert "objective_paused" in audit.objective_utility_signals
    assert "objective_missing_next_action" in audit.objective_utility_signals
    assert "objective_missing_artifact" in audit.objective_utility_signals
    assert audit.operator_usefulness_status == "partial"
    assert audit.operator_usefulness_score == 2
    assert "operator_checked_state" in audit.operator_usefulness_signals
    assert "operator_has_work_items" in audit.operator_usefulness_signals
    assert "operator_missing_next_action" in audit.operator_usefulness_signals
    assert "operator_missing_artifact" in audit.operator_usefulness_signals


def test_observability_service_audits_continuity_signals() -> None:
    temp_dir = runtime_dir("observability-continuity")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-c1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "retomar_missao_relacionada"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_logica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_logica", "mente_critica"],
                    "suppressed_minds": ["mente_probabilistica"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente_analitica lidera a resposta com apoio de "
                        "mente_logica, mente_critica"
                    ),
                    "arbitration_source": "mind_registry",
                },
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar", "continuity_source": "related_mission"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c6",
                event_name="continuity_subflow_completed",
                timestamp="2026-03-18T00:00:04.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "langgraph_subflow",
                    "subflow_name": "continuity_stateful",
                },
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c6b",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "retomar",
                    "continuity_source": "related_mission",
                },
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
            InternalEventEnvelope(
                event_id="evt-c9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cont",
                session_id="sess-cont",
                correlation_id="req-cont",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-cont"))

    assert audit.continuity_action == "retomar"
    assert audit.continuity_source == "related_mission"
    assert audit.continuity_runtime_mode == "langgraph_subflow"
    assert audit.workflow_trace_status == "not_applicable"
    assert audit.continuity_trace_status == "attention_required"
    assert "retomar_missing_target_mission" in audit.continuity_anomaly_flags
    assert "memory_continuity_mismatch" in audit.continuity_anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_audits_capability_decision_and_handoff_adapter() -> None:
    temp_dir = runtime_dir("observability-capability")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    capability_payload = {
        "capability_decision_status": "resolved",
        "capability_decision_objective": "compare the strongest pilot signal safely",
        "capability_decision_reason": "guided analysis keeps specialist review through core",
        "capability_decision_selected_mode": "core_with_specialist_handoff",
        "capability_decision_authorization_status": "authorized",
        "capability_decision_fallback_mode": "core_guidance_without_handoff",
        "capability_decision_tool_class": None,
        "capability_decision_handoff_mode": "through_core_only",
        "capability_decision_eligible_capabilities": [
            "core_reasoning",
            "specialist_handoff",
        ],
        "capability_decision_selected_capabilities": [
            "core_reasoning",
            "specialist_handoff",
        ],
    }
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-k1",
                event_name="input_received",
                timestamp="2026-03-21T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "analyze the strongest pilot risk"},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k2",
                event_name="memory_recovered",
                timestamp="2026-03-21T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k3",
                event_name="intent_classified",
                timestamp="2026-03-21T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k4",
                event_name="context_composed",
                timestamp="2026-03-21T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "primary_route": "analysis",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k5",
                event_name="plan_built",
                timestamp="2026-03-21T00:00:04+00:00",
                source_service="orchestrator-service",
                payload=capability_payload,
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k6",
                event_name="continuity_decided",
                timestamp="2026-03-21T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k7",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-21T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={
                    "response_channel": "through_core",
                    "tool_access_mode": "none",
                    "invocation_ids": ["inv-1"],
                },
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k8",
                event_name="specialist_handoff_governed",
                timestamp="2026-03-21T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow", **capability_payload},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k9",
                event_name="governance_checked",
                timestamp="2026-03-21T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow"},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k10",
                event_name="response_synthesized",
                timestamp="2026-03-21T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    **capability_payload,
                    "capability_decision_authorization_status": "authorized",
                    "workflow_output_status": "coherent",
                },
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
            InternalEventEnvelope(
                event_id="evt-k11",
                event_name="memory_recorded",
                timestamp="2026-03-21T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-capability",
                session_id="sess-capability",
                correlation_id="req-capability",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-capability"))

    assert audit.capability_decision_status == "healthy"
    assert audit.capability_decision_selected_mode == "core_with_specialist_handoff"
    assert audit.capability_authorization_status == "authorized"
    assert audit.handoff_adapter_status == "healthy"
    assert audit.capability_effectiveness == "effective"


def test_observability_service_audits_metacognitive_guidance() -> None:
    temp_dir = runtime_dir("observability-metacognition")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-m1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan strategic options for the release."},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_missao_ativa"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_decisoria", "mente_estrategica"],
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "supporting_minds": ["mente_estrategica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "arbitration_summary": (
                        "mente_decisoria lidera com apoio estrategico e foco unico"
                    ),
                    "arbitration_source": "mind_registry",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "canonical_domains": ["estrategia_e_pensamento_sistemico"],
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "metacognitive_guidance_applied": True,
                    "metacognitive_guidance_summary": (
                        "mente decisoria ancora estrategia e pensamento sistemico via "
                        "strategy sob tensao equilibrar ambicao estrategica com a "
                        "menor proxima acao segura"
                    ),
                    "metacognitive_effects": [
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                    "metacognitive_containment_recommendation": None,
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "metacognitive_guidance_applied": True,
                    "metacognitive_guidance_summary": (
                        "mente decisoria ancora estrategia e pensamento sistemico via "
                        "strategy sob tensao equilibrar ambicao estrategica com a "
                        "menor proxima acao segura"
                    ),
                    "metacognitive_effects": [
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                    "metacognitive_containment_recommendation": None,
                },
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
            InternalEventEnvelope(
                event_id="evt-m9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-meta",
                session_id="sess-meta",
                correlation_id="req-meta",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-meta"))

    assert audit.metacognitive_guidance_status == "healthy"
    assert audit.metacognitive_guidance_summary is not None
    assert audit.metacognitive_effects == [
        "success_criteria",
        "smallest_safe_next_action",
    ]


def test_observability_service_distinguishes_contract_and_output_validation_failures() -> None:
    temp_dir = runtime_dir("observability-validation")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-v1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "pilot"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_executiva",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "dominant_tension": "equilibrar ambicao com a menor proxima acao segura",
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "contract_validation_status": "repaired",
                    "contract_validation_errors": ["missing_required_field:active_minds"],
                    "contract_validation_retry_applied": True,
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v8",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "contract_validation_status": "repaired",
                    "contract_validation_errors": ["missing_required_field:active_minds"],
                    "contract_validation_retry_applied": True,
                    "output_validation_status": "invalid",
                    "output_validation_errors": ["missing_clause:recommendation"],
                    "output_validation_retry_applied": True,
                },
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
            InternalEventEnvelope(
                event_id="evt-v9",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-val",
                session_id="sess-val",
                correlation_id="req-val",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-val"))
    evidence = service.build_incident_evidence(ObservabilityQuery(request_id="req-val"))

    assert audit.contract_validation_status == "repaired"
    assert audit.contract_validation_retry_applied is True
    assert audit.output_validation_status == "invalid"
    assert audit.output_validation_retry_applied is True
    assert "output_validation_failed" in audit.anomaly_flags
    assert audit.trace_complete is False
    assert (
        evidence.recommended_operator_action
        == "contain_response_and_recompose_with_last_valid_plan"
    )


def test_observability_service_audits_domain_memory_and_sovereignty_alignment() -> None:
    temp_dir = runtime_dir("observability-specialist-alignment")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-s1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze the Python service rollout."},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s3b",
                event_name="directive_composed",
                timestamp="2026-03-18T00:00:02.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style_preview": "analitico, sintetico e rigoroso",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s4",
                event_name="domain_registry_resolved",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_domains": ["software_development", "analysis"],
                    "registry_domains": [
                        "computacao_e_desenvolvimento",
                        "dados_estatistica_e_inteligencia_analitica",
                        "tomada_de_decisao_complexa",
                    ],
                    "route_domains": ["software_development", "analysis"],
                    "primary_canonical_domain": "computacao_e_desenvolvimento",
                    "canonical_domain_refs_by_route": {
                        "software_development": ["computacao_e_desenvolvimento"],
                        "analysis": [
                            "dados_estatistica_e_inteligencia_analitica",
                            "tomada_de_decisao_complexa",
                        ],
                    },
                    "route_maturity": {
                        "software_development": "active_specialist",
                        "analysis": "active_specialist",
                    },
                    "route_modes": {
                        "software_development": "guided",
                        "analysis": "guided",
                    },
                    "linked_specialist_types": {
                        "software_development": "software_change_specialist",
                        "analysis": "structured_analysis_specialist",
                    },
                    "workflow_profiles": {
                        "software_development": "software_change_workflow",
                        "analysis": "structured_analysis_workflow",
                    },
                    "routing_sources": {
                        "software_development": "domain_registry",
                        "analysis": "domain_registry",
                    },
                    "shadow_domains": [],
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s5",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_logica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_logica", "mente_critica"],
                    "suppressed_minds": ["mente_probabilistica"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente_analitica lidera a resposta com apoio de "
                        "mente_logica, mente_critica"
                    ),
                    "arbitration_source": "mind_registry",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s6",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s7",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "software_change_specialist": "core_mediated_read_only"
                    },
                    "consumer_modes": {
                        "software_change_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "consumer_objectives": {
                        "software_change_specialist": (
                            "avaliar segurança da mudança, impacto de implementação e "
                            "direção de patch recomendada"
                        )
                    },
                    "expected_deliverables": {
                        "software_change_specialist": [
                            "implementation_findings",
                            "change_risk_summary",
                            "recommended_patch_direction",
                        ]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": [
                            "contract_impact",
                            "change_safety",
                            "implementation_trace",
                        ]
                    },
                    "consumed_memory_classes": {
                        "software_change_specialist": ["mission", "domain"]
                    },
                    "memory_write_policies": {
                        "software_change_specialist": {
                            "mission": "through_core_only",
                            "domain": "through_core_only",
                        }
                    },
                    "domain_mission_link_reasons": {
                        "software_change_specialist": (
                            "route=software_development "
                            "canonicos=computacao_e_desenvolvimento "
                            "missao=Review Python service rollout"
                        )
                    },
                    "memory_class_policies": {
                        "software_change_specialist": {
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "domain": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s9",
                event_name="specialist_contracts_composed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "response_channel": "through_core",
                    "tool_access_mode": "none",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s10",
                event_name="domain_specialist_completed",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["software_change_specialist"],
                    "linked_domains": {"software_change_specialist": "software_development"},
                    "selection_modes": {"software_change_specialist": "guided"},
                    "route_maturity": {"software_change_specialist": "active_specialist"},
                    "canonical_domain_refs": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "canonical_domain_refs_resolved": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "expected_deliverables": {
                        "software_change_specialist": [
                            "implementation_findings",
                            "change_risk_summary",
                            "recommended_patch_direction",
                        ]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": [
                            "contract_impact",
                            "change_safety",
                            "implementation_trace",
                        ]
                    },
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s10b",
                event_name="plan_governed",
                timestamp="2026-03-18T00:00:09.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "decision_frame": "analysis",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style": "analitico, sintetico e rigoroso",
                    "identity_guardrail": "preservar rigor analitico antes de concluir",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s11",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s12",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "identity_mode": "deep_analysis",
                    "identity_signature": "nucleo_soberano_unificado",
                    "response_style": "analitico, sintetico e rigoroso",
                },
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
            InternalEventEnvelope(
                event_id="evt-s13",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:12+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-specialist-align",
                session_id="sess-specialist-align",
                correlation_id="req-specialist-align",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-specialist-align"))

    assert audit.registry_domains == [
        "computacao_e_desenvolvimento",
        "dados_estatistica_e_inteligencia_analitica",
        "tomada_de_decisao_complexa",
    ]
    assert audit.domain_specialists == ["software_change_specialist"]
    assert audit.shadow_specialists == []
    assert audit.domain_alignment_status == "healthy"
    assert audit.workflow_trace_status == "not_applicable"
    assert audit.mind_alignment_status == "healthy"
    assert audit.identity_alignment_status == "healthy"
    assert audit.memory_alignment_status == "healthy"
    assert audit.specialist_sovereignty_status == "healthy"


def test_langsmith_adapter_emits_trace_tree() -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def create_run(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            calls.append(kwargs)

    adapter = LangSmithObservabilityAdapter(client=FakeClient(), project_name="jarvis-test")
    adapter.emit(
        [
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "hello"},
                request_id="req-8",
                session_id="sess-8",
                correlation_id="req-8",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"status": "completed"},
                request_id="req-8",
                session_id="sess-8",
                correlation_id="req-8",
                operation_id="op-8",
            ),
        ]
    )

    assert len(calls) == 3
    root_run, first_child, second_child = calls
    assert root_run["name"] == "jarvis_trace"
    assert root_run["id"] == root_run["trace_id"]
    assert root_run["outputs"]["total_events"] == 2
    assert root_run["extra"]["metadata"]["request_id"] == "req-8"
    assert first_child["parent_run_id"] == root_run["id"]
    assert first_child["trace_id"] == root_run["trace_id"]
    assert first_child["extra"]["metadata"]["event_id"] == "evt-8"
    assert second_child["run_type"] == "tool"
    assert second_child["extra"]["metadata"]["operation_id"] == "op-8"


def test_langsmith_adapter_groups_events_by_request() -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def create_run(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
            calls.append(kwargs)

    adapter = LangSmithObservabilityAdapter(client=FakeClient(), project_name="jarvis-test")
    adapter.emit(
        [
            InternalEventEnvelope(
                event_id="evt-10",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "a"},
                request_id="req-a",
                session_id="sess-a",
                correlation_id="req-a",
            ),
            InternalEventEnvelope(
                event_id="evt-11",
                event_name="input_received",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"content": "b"},
                request_id="req-b",
                session_id="sess-b",
                correlation_id="req-b",
            ),
        ]
    )

    root_runs = [call for call in calls if call["name"] == "jarvis_trace"]
    child_runs = [call for call in calls if call["name"] != "jarvis_trace"]
    assert len(root_runs) == 2
    assert len(child_runs) == 2
    root_ids = {call["id"] for call in root_runs}
    assert all(call["parent_run_id"] in root_ids for call in child_runs)


def test_observability_service_builds_incident_evidence_for_governed_flow() -> None:
    temp_dir = runtime_dir("observability-incident")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-i1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "delete records"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
            InternalEventEnvelope(
                event_id="evt-i2",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"decision": "block"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
            InternalEventEnvelope(
                event_id="evt-i3",
                event_name="governance_blocked",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"justification": "blocked"},
                request_id="req-incident",
                session_id="sess-incident",
                correlation_id="req-incident",
            ),
        ]
    )

    evidence = service.build_incident_evidence(ObservabilityQuery(request_id="req-incident"))

    assert evidence.request_id == "req-incident"
    assert evidence.governance_decision == "block"
    assert evidence.recommended_operator_action == "keep_contained_and_require_manual_review"
    assert "memory_recovered" in evidence.missing_required_events



def test_observability_service_audits_healthy_workflow_trace() -> None:
    temp_dir = runtime_dir("observability-workflow")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-w1",
                event_name="input_received",
                timestamp="2026-03-18T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan rollout checkpoints."},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w2",
                event_name="memory_recovered",
                timestamp="2026-03-18T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w3",
                event_name="intent_classified",
                timestamp="2026-03-18T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w4",
                event_name="context_composed",
                timestamp="2026-03-18T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_planejadora", "mente_logica"],
                    "primary_mind": "mente_planejadora",
                    "supporting_minds": ["mente_logica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "transformar meta em checkpoints seguros",
                    "arbitration_summary": "mente_planejadora lidera com apoio logico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w5",
                event_name="plan_built",
                timestamp="2026-03-18T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w6",
                event_name="continuity_decided",
                timestamp="2026-03-18T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w7",
                event_name="governance_checked",
                timestamp="2026-03-18T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w8",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoints": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                            "next_action_governed",
                        ],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending",
                            "step_sequence_validated": "pending",
                            "next_action_governed": "pending",
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
                        "workflow_decision_points": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w9",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                        "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_decision_points": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w10",
                event_name="operation_dispatched",
                timestamp="2026-03-18T00:00:07.800000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "task_type": "draft_plan",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_response_focus": (
                            "direcao recomendada, criterios e trade-offs dominantes"
                        ),
                        "workflow_state": "dispatched",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending",
                            "step_sequence_validated": "pending",
                            "next_action_governed": "pending",
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
                        "workflow_decision_points": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                        "next_action_governed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w11",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_completed_steps": [
                        "structure the goal and success criteria",
                        "sequence the smallest safe steps",
                        "emit checkpoints and the next safe action",
                    ],
                        "workflow_decisions": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                            "next_action_governed",
                        ],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed",
                            "step_sequence_validated": "completed",
                            "next_action_governed": "completed",
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                    },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w12",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed",
                            "step_sequence_validated": "completed",
                            "next_action_governed": "completed",
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                        "workflow_decision_points": [
                            "goal_scope_confirmed",
                            "step_sequence_validated",
                        "next_action_governed",
                    ],
                    "workflow_decisions": [
                        "goal_scope_confirmed",
                        "step_sequence_validated",
                        "next_action_governed",
                    ],
                    "status": "completed",
                    "checkpoints": [
                        "workflow_state:composed",
                        "workflow:goal_structured",
                        "workflow_state:completed",
                    ],
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
                operation_id="op-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w13",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_planejadora",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "workflow_output_status": "coherent",
                    "workflow_output_errors": [],
                    "guided_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_focus": [
                        "estrategia_e_pensamento_sistemico",
                        "strategy",
                    ],
                    "procedural_memory_hint": "preservar o ultimo fio decisorio governado",
                },
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
            InternalEventEnvelope(
                event_id="evt-w14",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-workflow",
                session_id="sess-workflow",
                correlation_id="req-workflow",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow"))

    assert audit.workflow_domain_route == "strategy"
    assert audit.workflow_profile == "strategic_direction_workflow"
    assert audit.workflow_governance_mode == "core_mediated"
    assert audit.workflow_trace_status == "healthy"
    assert audit.workflow_profile_status == "healthy"
    assert audit.missing_required_events == []
    assert audit.anomaly_flags == []
    assert audit.trace_complete is True



def test_observability_service_flags_workflow_contract_drift() -> None:
    temp_dir = runtime_dir("observability-workflow-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-d1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoints": ["goal_scope_confirmed"],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "pending"
                        },
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_resume_eligible": False,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                        "workflow_success_focus": "direcao recomendada com criterios explicitos",
                        "workflow_state": "composed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_resume_status": "fresh_start",
                        "workflow_resume_point": None,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d3",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_completed_steps": [
                        "frame the strategic scenario and the decision horizon",
                    ],
                    "workflow_decisions": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d4",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-drift",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [],
                    "workflow_telemetry_focus": ["tradeoff_clarity"],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_decision_points": ["goal_scope_confirmed"],
                    "workflow_decisions": ["goal_scope_confirmed"],
                    "status": "completed",
                    "checkpoints": [
                        "workflow_state:composed",
                        "workflow_state:completed",
                    ],
                },
                request_id="req-workflow-drift",
                session_id="sess-workflow-drift",
                correlation_id="req-workflow-drift",
                operation_id="op-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow-drift"))

    assert audit.workflow_trace_status == "attention_required"


def test_observability_service_marks_workflow_profile_maturation_recommended() -> None:
    temp_dir = runtime_dir("observability-workflow-maturation")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mw1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoints": ["goal_scope_confirmed"],
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "pending"
                    },
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_resume_eligible": False,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw3",
                event_name="operation_completed",
                timestamp="2026-03-18T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "status": "completed",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                        "workflow_response_focus": (
                            "direcao recomendada, criterios e trade-offs dominantes"
                        ),
                        "workflow_state": "completed",
                        "workflow_decisions": ["goal_scope_confirmed"],
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed"
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                    },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw4",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-maturation",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                        "recommended_direction",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                        "domain_alignment",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                        "workflow_state": "completed",
                        "workflow_governance_mode": "core_mediated",
                        "workflow_checkpoint_state": {
                            "goal_scope_confirmed": "completed"
                        },
                        "workflow_pending_checkpoints": [],
                        "workflow_resume_status": "completed_without_resume",
                        "workflow_resume_point": None,
                        "workflow_decision_points": ["goal_scope_confirmed"],
                        "workflow_decisions": ["goal_scope_confirmed"],
                    },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
                operation_id="op-maturation",
            ),
            InternalEventEnvelope(
                event_id="evt-mw5",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "workflow_output_status": "partial",
                    "workflow_output_errors": ["missing_clause:workflow_checkpoint"],
                },
                request_id="req-workflow-maturation",
                session_id="sess-workflow-maturation",
                correlation_id="req-workflow-maturation",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-workflow-maturation"))

    assert audit.workflow_trace_status == "healthy"
    assert audit.workflow_profile_status == "maturation_recommended"
    assert audit.trace_complete is False


def test_observability_service_flags_workflow_output_misalignment() -> None:
    temp_dir = runtime_dir("observability-workflow-output-misaligned")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-wom1",
                event_name="workflow_composed",
                timestamp="2026-03-18T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoints": ["goal_scope_confirmed"],
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "pending"
                    },
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_resume_eligible": False,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom2",
                event_name="workflow_governance_declared",
                timestamp="2026-03-18T00:00:07.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_state": "composed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_resume_status": "fresh_start",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom3",
                event_name="workflow_completed",
                timestamp="2026-03-18T00:00:08.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "operation_id": "op-workflow-output-misaligned",
                    "workflow_profile": "strategic_direction_workflow",
                    "workflow_domain_route": "strategy",
                    "workflow_objective": "clarify strategic tradeoffs and recommend a direction",
                    "workflow_expected_deliverables": [
                        "tradeoff_map",
                        "decision_criteria",
                    ],
                    "workflow_telemetry_focus": [
                        "tradeoff_clarity",
                        "decision_trace",
                    ],
                    "workflow_success_focus": "direcao recomendada com criterios explicitos",
                    "workflow_response_focus": (
                        "direcao recomendada, criterios e trade-offs dominantes"
                    ),
                    "workflow_state": "completed",
                    "workflow_governance_mode": "core_mediated",
                    "workflow_checkpoint_state": {
                        "goal_scope_confirmed": "completed"
                    },
                    "workflow_pending_checkpoints": [],
                    "workflow_resume_status": "completed_without_resume",
                    "workflow_resume_point": None,
                    "workflow_decision_points": ["goal_scope_confirmed"],
                    "workflow_decisions": ["goal_scope_confirmed"],
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
                operation_id="op-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom4",
                event_name="response_synthesized",
                timestamp="2026-03-18T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_planejadora",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "workflow_output_status": "misaligned",
                    "workflow_output_errors": [
                        "mismatched_clause:workflow_response_focus"
                    ],
                    "guided_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_focus": [
                        "estrategia_e_pensamento_sistemico",
                        "strategy",
                    ],
                    "procedural_memory_hint": "preservar o ultimo fio decisorio governado",
                },
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
            ),
            InternalEventEnvelope(
                event_id="evt-wom5",
                event_name="memory_recorded",
                timestamp="2026-03-18T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-workflow-output-misaligned",
                session_id="sess-workflow-output-misaligned",
                correlation_id="req-workflow-output-misaligned",
            ),
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-workflow-output-misaligned")
    )

    assert audit.workflow_output_status == "misaligned"
    assert "mismatched_clause:workflow_response_focus" in audit.workflow_output_errors
    assert audit.workflow_profile_status == "attention_required"
    assert "workflow_output_misaligned" in audit.anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_tracks_organization_scope_no_go() -> None:
    temp_dir = runtime_dir("observability-organization-scope")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-og1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Keep organization scope outside baseline."},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"organization_scope_status": "no_go_without_canonical_consumer"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "preservar guardrails do baseline",
                    "arbitration_summary": "mente analitica lidera o fluxo",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og8",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-og9",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_mode": "continuar",
                    "organization_scope_status": "no_go_without_canonical_consumer",
                },
                request_id="req-organization-scope",
                session_id="sess-organization-scope",
                correlation_id="req-organization-scope",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-organization-scope"))

    assert audit.organization_scope_status == "no_go_without_canonical_consumer"


def test_observability_service_tracks_specialist_recurrence_status() -> None:
    temp_dir = runtime_dir("observability-specialist-recurrence")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-sr1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review software rollout again."},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "aprofundar contexto recorrente",
                    "arbitration_summary": "mente analitica lidera o fluxo",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "guided_specialists": ["software_change_specialist"],
                    "recurrent_context_statuses": {"software_change_specialist": "recoverable"},
                    "recurrent_interaction_counts": {"software_change_specialist": 2},
                },
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr9",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
            InternalEventEnvelope(
                event_id="evt-sr10",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-specialist-recurrence",
                session_id="sess-specialist-recurrence",
                correlation_id="req-specialist-recurrence",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-specialist-recurrence"))

    assert audit.specialist_recurrence_status == "recoverable"


def test_observability_service_tracks_user_scope_status() -> None:
    temp_dir = runtime_dir("observability-user-scope")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-us1",
                event_name="input_received",
                timestamp="2026-03-31T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze rollout context."},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us2",
                event_name="memory_recovered",
                timestamp="2026-03-31T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"user_scope_status": "seeded"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us3",
                event_name="intent_classified",
                timestamp="2026-03-31T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us4",
                event_name="context_composed",
                timestamp="2026-03-31T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "consolidar contexto do usuario sem perder rigor",
                    "arbitration_summary": "mente_analitica lidera a leitura do contexto",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us5",
                event_name="plan_built",
                timestamp="2026-03-31T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us6",
                event_name="continuity_decided",
                timestamp="2026-03-31T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us7",
                event_name="governance_checked",
                timestamp="2026-03-31T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us8",
                event_name="response_synthesized",
                timestamp="2026-03-31T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
            InternalEventEnvelope(
                event_id="evt-us9",
                event_name="memory_recorded",
                timestamp="2026-03-31T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar", "user_scope_status": "recoverable"},
                request_id="req-user-scope",
                session_id="sess-user-scope",
                correlation_id="req-user-scope",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-user-scope"))

    assert audit.user_scope_status == "recoverable"




def test_observability_service_marks_mind_alignment_attention_when_plan_drifts() -> None:
    temp_dir = runtime_dir("observability-mind-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-md1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review rollout trade-offs."},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md4",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_logica"],
                    "canonical_domains": ["dados_estatistica_e_inteligencia_analitica"],
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "supporting_minds": ["mente_logica"],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": "mente_analitica lidera a resposta com apoio logico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md5",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "tomada_de_decisao_complexa",
                    "arbitration_source": "mind_registry",
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md6",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md7",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md8",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-md9",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-mind-drift",
                session_id="sess-mind-drift",
                correlation_id="req-mind-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-mind-drift"))

    assert audit.mind_alignment_status == "attention_required"

def test_observability_service_marks_domain_alignment_attention_when_selection_drifts() -> None:
    temp_dir = runtime_dir("observability-selection-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-d1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Review software rollout."},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d4",
                event_name="domain_registry_resolved",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "registry_domains": ["computacao_e_desenvolvimento"],
                    "route_domains": ["software_development"],
                    "canonical_domain_refs_by_route": {
                        "software_development": ["computacao_e_desenvolvimento"]
                    },
                    "route_maturity": {"software_development": "active_specialist"},
                    "route_modes": {"software_development": "guided"},
                    "linked_specialist_types": {
                        "software_development": "software_change_specialist"
                    },
                    "workflow_profiles": {
                        "software_development": "software_change_workflow"
                    },
                    "routing_sources": {"software_development": "domain_registry"},
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d5",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": "mente_analitica lidera a resposta",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d6",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d7",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d8",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d9",
                event_name="specialist_selection_decided",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "selected_specialists": ["software_change_specialist"],
                    "domain_links": {"software_change_specialist": "software_development"},
                    "selection_modes": {"software_change_specialist": "shadow"},
                    "route_maturity": {"software_change_specialist": "active_specialist"},
                    "canonical_domain_refs_resolved": {
                        "software_change_specialist": ["computacao_e_desenvolvimento"]
                    },
                    "registry_link_matches": {"software_change_specialist": True},
                    "registry_mode_matches": {"software_change_specialist": False},
                    "registry_specialist_eligibility": {"software_change_specialist": False},
                },
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d10",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-d11",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-selection-drift",
                session_id="sess-selection-drift",
                correlation_id="req-selection-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-selection-drift"))

    assert audit.domain_alignment_status == "attention_required"


def test_observability_service_flags_primary_driver_specialist_drift() -> None:
    temp_dir = runtime_dir("observability-primary-driver-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-pd1",
                event_name="input_received",
                timestamp="2026-04-01T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Compare strategic options for the release."},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd2",
                event_name="memory_recovered",
                timestamp="2026-04-01T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "priorizar_loop_ativo"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd3",
                event_name="intent_classified",
                timestamp="2026-04-01T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd4",
                event_name="domain_registry_resolved",
                timestamp="2026-04-01T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "registry_domains": [
                        "estrategia_e_pensamento_sistemico",
                        "dados_estatistica_e_inteligencia_analitica",
                    ],
                    "route_domains": ["strategy", "analysis"],
                    "canonical_domain_refs_by_route": {
                        "strategy": ["estrategia_e_pensamento_sistemico"],
                        "analysis": ["dados_estatistica_e_inteligencia_analitica"],
                    },
                    "route_maturity": {
                        "strategy": "active_specialist",
                        "analysis": "active_specialist",
                    },
                    "route_modes": {"strategy": "guided", "analysis": "guided"},
                    "linked_specialist_types": {
                        "strategy": "structured_analysis_specialist",
                        "analysis": "structured_analysis_specialist",
                    },
                    "workflow_profiles": {
                        "strategy": "strategic_direction_workflow",
                        "analysis": "structured_analysis_workflow",
                    },
                    "routing_sources": {
                        "strategy": "domain_registry",
                        "analysis": "domain_registry",
                    },
                    "promoted_route_registry": {
                        "strategy": {
                            "canonical_domain_refs": ["estrategia_e_pensamento_sistemico"],
                            "linked_specialist_type": "structured_analysis_specialist",
                            "specialist_mode": "guided",
                            "maturity": "active_specialist",
                            "mode_is_governed": True,
                            "eligible": True,
                        },
                        "analysis": {
                            "canonical_domain_refs": [
                                "dados_estatistica_e_inteligencia_analitica"
                            ],
                            "linked_specialist_type": "structured_analysis_specialist",
                            "specialist_mode": "guided",
                            "maturity": "active_specialist",
                            "mode_is_governed": True,
                            "eligible": True,
                        },
                    },
                    "consumer_profiles": {
                        "strategy": "strategy_tradeoff_review",
                        "analysis": "analysis_evidence_review",
                    },
                    "consumer_objectives": {
                        "strategy": "clarificar trade-offs estrategicos",
                        "analysis": "estruturar leitura de evidencia",
                    },
                    "expected_deliverables": {
                        "strategy": ["tradeoff_map"],
                        "analysis": ["analysis_findings"],
                    },
                    "telemetry_focus": {
                        "strategy": ["tradeoff_clarity"],
                        "analysis": ["evidence_clarity"],
                    },
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd5",
                event_name="context_composed",
                timestamp="2026-04-01T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_decisoria"],
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": (
                        "equilibrar ambicao estrategica com a menor proxima acao segura"
                    ),
                    "arbitration_summary": "mente_decisoria lidera a resposta",
                    "arbitration_source": "mind_registry",
                    "canonical_domains": [
                        "estrategia_e_pensamento_sistemico",
                        "dados_estatistica_e_inteligencia_analitica",
                    ],
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd6",
                event_name="plan_built",
                timestamp="2026-04-01T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd7",
                event_name="continuity_decided",
                timestamp="2026-04-01T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd8",
                event_name="governance_checked",
                timestamp="2026-04-01T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd9",
                event_name="specialist_selection_decided",
                timestamp="2026-04-01T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "selected_specialists": ["structured_analysis_specialist"],
                    "domain_links": {"structured_analysis_specialist": "analysis"},
                    "selection_modes": {"structured_analysis_specialist": "guided"},
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "primary_route": "strategy",
                    "primary_canonical_domain": "estrategia_e_pensamento_sistemico",
                    "route_maturity": {"structured_analysis_specialist": "active_specialist"},
                    "canonical_domain_refs_resolved": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                    "registry_route_payloads": {
                        "structured_analysis_specialist": {
                            "route_name": "analysis",
                            "linked_specialist_type": "structured_analysis_specialist",
                            "canonical_domain_refs": [
                                "dados_estatistica_e_inteligencia_analitica"
                            ],
                        }
                    },
                    "registry_link_matches": {"structured_analysis_specialist": True},
                    "registry_mode_matches": {"structured_analysis_specialist": True},
                    "registry_specialist_eligibility": {"structured_analysis_specialist": True},
                    "primary_route_matches": {"structured_analysis_specialist": False},
                    "primary_canonical_matches": {"structured_analysis_specialist": False},
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": False
                    },
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd10",
                event_name="response_synthesized",
                timestamp="2026-04-01T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_decisoria",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-pd11",
                event_name="memory_recorded",
                timestamp="2026-04-01T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-primary-driver-drift",
                session_id="sess-primary-driver-drift",
                correlation_id="req-primary-driver-drift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-primary-driver-drift"))

    assert audit.domain_alignment_status == "attention_required"


def test_observability_service_tracks_memory_causality_status() -> None:
    temp_dir = runtime_dir("observability-memory-causality")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mc1",
                event_name="input_received",
                timestamp="2026-04-02T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Compare release options with prior context."},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc2",
                event_name="memory_recovered",
                timestamp="2026-04-02T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc3",
                event_name="intent_classified",
                timestamp="2026-04-02T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc4",
                event_name="context_composed",
                timestamp="2026-04-02T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica"],
                    "primary_mind": "mente_analitica",
                    "supporting_minds": [],
                    "suppressed_minds": [],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 2,
                    "dominant_tension": "conectar contexto previo com decisao atual",
                    "arbitration_summary": "mente analitica lidera a resposta",
                    "arbitration_source": "mind_registry",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "canonical_domains": ["dados_estatistica_e_inteligencia_analitica"],
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc5",
                event_name="plan_built",
                timestamp="2026-04-02T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc6",
                event_name="continuity_decided",
                timestamp="2026-04-02T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc7",
                event_name="governance_checked",
                timestamp="2026-04-02T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc8",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-04-02T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "structured_analysis_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "structured_analysis_specialist": {
                            "semantic": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "procedural": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                    "consumed_memory_classes": {
                        "structured_analysis_specialist": ["semantic", "procedural"]
                    },
                    "memory_write_policies": {
                        "structured_analysis_specialist": {
                            "semantic": "through_core_only",
                            "procedural": "through_core_only",
                        }
                    },
                    "memory_refs_by_specialist": {
                        "structured_analysis_specialist": [
                            "memory://semantic/release-context",
                            "memory://procedural/release-checklist",
                        ]
                    },
                    "semantic_focus_by_specialist": {
                        "structured_analysis_specialist": [
                            "dados_estatistica_e_inteligencia_analitica"
                        ]
                    },
                    "consumer_modes": {
                        "structured_analysis_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "structured_analysis_specialist": "structured_analysis"
                    },
                    "consumer_objectives": {
                        "structured_analysis_specialist": "compare_safe_options"
                    },
                    "expected_deliverables": {
                        "structured_analysis_specialist": ["comparison_frame"]
                    },
                    "telemetry_focus": {
                        "structured_analysis_specialist": ["analysis_trace"]
                    },
                    "domain_mission_link_reasons": {
                        "structured_analysis_specialist": (
                            "analysis linked to active mission and canonical domain"
                        )
                    },
                    "semantic_memory_specialists": ["structured_analysis_specialist"],
                    "procedural_memory_specialists": ["structured_analysis_specialist"],
                    "semantic_memory_states": {
                        "structured_analysis_specialist": "operational"
                    },
                    "procedural_memory_states": {
                        "structured_analysis_specialist": "operational"
                    },
                    "memory_consolidation_statuses": {
                        "structured_analysis_specialist": "in_progress"
                    },
                    "memory_fixation_statuses": {
                        "structured_analysis_specialist": "not_fixed"
                    },
                    "memory_archive_statuses": {
                        "structured_analysis_specialist": "active_memory"
                    },
                    "memory_review_statuses": {
                        "structured_analysis_specialist": "monitor"
                    },
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc9",
                event_name="response_synthesized",
                timestamp="2026-04-02T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry",
                    "semantic_memory_available": True,
                    "procedural_memory_available": True,
                    "semantic_memory_focus": [
                        "dados_estatistica_e_inteligencia_analitica"
                    ],
                    "semantic_memory_anchor_refs": [
                        "memory://mission/mission-memory-causality/semantic"
                    ],
                    "semantic_memory_evidence_refs": [
                        "memory://mission/mission-memory-causality/semantic#evidence",
                        "workflow://structured_analysis_workflow",
                    ],
                    "semantic_memory_use_reason": (
                        "matched active_mission to structured_analysis_workflow/analysis"
                    ),
                    "procedural_memory_hint": "preservar a moldura de comparacao mais recente",
                    "procedural_artifact_status": "candidate",
                    "procedural_artifact_refs": [
                        "artifact://procedural/structured-analysis/v1"
                    ],
                },
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
            InternalEventEnvelope(
                event_id="evt-mc10",
                event_name="memory_recorded",
                timestamp="2026-04-02T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-memory-causality",
                session_id="sess-memory-causality",
                correlation_id="req-memory-causality",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-memory-causality"))

    assert audit.memory_causality_status == "causal_guidance"
    assert audit.semantic_memory_focus == ["dados_estatistica_e_inteligencia_analitica"]
    assert audit.semantic_memory_anchor_refs == [
        "memory://mission/mission-memory-causality/semantic"
    ]
    assert "workflow://structured_analysis_workflow" in (
        audit.semantic_memory_evidence_refs
    )
    assert audit.semantic_memory_use_reason == (
        "matched active_mission to structured_analysis_workflow/analysis"
    )
    assert audit.semantic_memory_non_use_reason is None
    assert audit.memory_influence_used_refs == [
        "memory://mission/mission-memory-causality/semantic",
        "artifact://procedural/structured-analysis/v1",
    ]
    assert audit.memory_influence_ignored_refs == []
    assert audit.memory_influence_reasons == [
        (
            "semantic_used:"
            "matched active_mission to structured_analysis_workflow/analysis"
        ),
        "procedural_artifact_used:candidate",
    ]
    assert audit.memory_influence_evidence_refs == [
        "memory://mission/mission-memory-causality/semantic#evidence",
        "workflow://structured_analysis_workflow",
        "artifact://procedural/structured-analysis/v1",
    ]
    assert (
        audit.procedural_memory_hint
        == "preservar a moldura de comparacao mais recente"
    )
    assert audit.semantic_memory_specialists == ["structured_analysis_specialist"]
    assert audit.procedural_memory_specialists == ["structured_analysis_specialist"]
    assert audit.memory_consolidation_status == "in_progress"
    assert audit.memory_fixation_status == "not_fixed"
    assert audit.memory_archive_status == "active_memory"


def test_observability_service_audits_reviewed_playbook_separately_from_legacy_artifact() -> None:
    temp_dir = runtime_dir("observability-reviewed-procedural-playbook")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    playbook_ref = "reviewed-playbook://software/release@2.1.0"
    review_decision_ref = "review-decision://software/release-v2.1.0"
    legacy_artifact_ref = "artifact://procedural/software-release/v1"
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-governed",
                event_name="memory_influence_governed",
                timestamp="2026-07-18T13:04:59+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_governance_status": "governed",
                    "memory_influence_governance_blockers": [],
                },
                request_id="req-reviewed-playbook-selected",
                session_id="sess-reviewed-playbook-selected",
                correlation_id="req-reviewed-playbook-selected",
            ),
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-selected",
                event_name="response_synthesized",
                timestamp="2026-07-18T13:05:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_selected_refs": [playbook_ref],
                    "memory_influence_ignored_refs": [],
                    "memory_influence_non_use_reasons": {},
                    "memory_influence_signal_kinds": {playbook_ref: "procedural"},
                    "memory_influence_version_refs": {playbook_ref: "2.1.0"},
                    "memory_influence_review_decision_refs": {
                        playbook_ref: review_decision_ref
                    },
                    "memory_influence_execution_allowed": False,
                    "memory_influence_tool_dispatch_allowed": False,
                    "procedural_artifact_status": "candidate",
                    "procedural_artifact_refs": [legacy_artifact_ref],
                    "procedural_artifact_version": 1,
                },
                request_id="req-reviewed-playbook-selected",
                session_id="sess-reviewed-playbook-selected",
                correlation_id="req-reviewed-playbook-selected",
            )
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-reviewed-playbook-selected")
    )

    assert audit.memory_influence_selected_refs == [playbook_ref]
    assert audit.memory_influence_non_use_reasons == {}
    assert audit.memory_influence_signal_kinds == {playbook_ref: "procedural"}
    assert audit.memory_influence_version_refs == {playbook_ref: "2.1.0"}
    assert audit.memory_influence_review_decision_refs == {
        playbook_ref: review_decision_ref
    }
    assert audit.memory_influence_execution_allowed is False
    assert audit.memory_influence_tool_dispatch_allowed is False
    assert audit.memory_influence_governance_status == "governed"
    assert audit.memory_influence_governance_blockers == []
    assert audit.memory_influence_governance_drift_flags == []
    assert audit.selected_reviewed_procedural_playbook_refs == [playbook_ref]
    assert audit.memory_influence_used_refs == [
        playbook_ref,
        legacy_artifact_ref,
    ]
    assert audit.memory_influence_ignored_refs == []
    assert audit.memory_influence_reasons == [
        f"reviewed_procedural_playbook_used:{playbook_ref}",
        "procedural_artifact_used:candidate",
    ]
    assert audit.procedural_artifact_refs == [legacy_artifact_ref]
    assert audit.procedural_artifact_version == 1
    assert audit.operation_status is None


def test_observability_service_flags_reviewed_playbook_governance_drift() -> None:
    temp_dir = runtime_dir("observability-reviewed-playbook-governance-drift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    playbook_ref = "reviewed-playbook://software/release@3.0.0"
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-unsafe-plan",
                event_name="plan_built",
                timestamp="2026-07-18T13:05:30+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_selected_refs": [playbook_ref],
                    "memory_influence_signal_kinds": {playbook_ref: "procedural"},
                    "memory_influence_execution_allowed": True,
                    "memory_influence_tool_dispatch_allowed": True,
                },
                request_id="req-reviewed-playbook-governance-drift",
                session_id="sess-reviewed-playbook-governance-drift",
                correlation_id="req-reviewed-playbook-governance-drift",
            ),
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-unsafe-dispatch",
                event_name="operation_dispatched",
                timestamp="2026-07-18T13:05:31+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-reviewed-playbook-governance-drift",
                session_id="sess-reviewed-playbook-governance-drift",
                correlation_id="req-reviewed-playbook-governance-drift",
            ),
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-reviewed-playbook-governance-drift")
    )

    expected_drift = [
        "memory_influence_governance_event_missing",
        "reviewed_procedural_version_trace_missing",
        "reviewed_procedural_human_review_trace_missing",
        "memory_influence_execution_authority_claim_not_allowed",
        "memory_influence_tool_dispatch_authority_claim_not_allowed",
        "reviewed_procedural_playbook_dispatched",
    ]
    assert audit.memory_influence_governance_status is None
    assert audit.memory_influence_governance_blockers == []
    assert audit.selected_reviewed_procedural_playbook_refs == [playbook_ref]
    assert audit.memory_influence_governance_drift_flags == expected_drift
    assert all(flag in audit.anomaly_flags for flag in expected_drift)
    assert audit.trace_complete is False


def test_observability_service_flags_blocked_memory_influence_governance() -> None:
    temp_dir = runtime_dir("observability-memory-influence-governance-blocked")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    playbook_ref = "reviewed-playbook://strategy/checkpoint@1.2.0"
    blocker = "memory_influence_priority_policy_mismatch"
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-governance-blocked",
                event_name="memory_influence_governed",
                timestamp="2026-07-18T13:05:45+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_selected_refs": [playbook_ref],
                    "memory_influence_signal_kinds": {playbook_ref: "procedural"},
                    "memory_influence_version_refs": {playbook_ref: "1.2.0"},
                    "memory_influence_review_decision_refs": {
                        playbook_ref: "review-decision://strategy/checkpoint-v1.2.0"
                    },
                    "memory_influence_governance_status": "blocked",
                    "memory_influence_governance_blockers": [blocker],
                    "memory_influence_execution_allowed": False,
                    "memory_influence_tool_dispatch_allowed": False,
                },
                request_id="req-memory-influence-governance-blocked",
                session_id="sess-memory-influence-governance-blocked",
                correlation_id="req-memory-influence-governance-blocked",
            )
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-memory-influence-governance-blocked")
    )

    assert audit.memory_influence_governance_status == "blocked"
    assert audit.memory_influence_governance_blockers == [blocker]
    assert audit.memory_influence_governance_drift_flags == [
        "memory_influence_governance_blocked"
    ]
    assert "memory_influence_governance_blocked" in audit.anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_audits_revoked_and_mismatched_playbook_non_use() -> None:
    temp_dir = runtime_dir("observability-reviewed-playbook-non-use")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    revoked_ref = "reviewed-playbook://strategy/revoked@1.0.0"
    mismatch_ref = "reviewed-playbook://analysis/mismatch@1.3.0"
    non_use_reasons = {
        revoked_ref: "review_status_not_eligible:revoked",
        mismatch_ref: "scope_mismatch:route",
    }
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-reviewed-playbook-ignored",
                event_name="plan_built",
                timestamp="2026-07-18T13:06:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_selected_refs": [],
                    "memory_influence_ignored_refs": [revoked_ref, mismatch_ref],
                    "memory_influence_non_use_reasons": non_use_reasons,
                    "memory_influence_signal_kinds": {
                        revoked_ref: "procedural",
                        mismatch_ref: "procedural",
                    },
                    "memory_influence_version_refs": {
                        revoked_ref: "1.0.0",
                        mismatch_ref: "1.3.0",
                    },
                    "memory_influence_review_decision_refs": {
                        revoked_ref: "review-decision://strategy/revoked",
                        mismatch_ref: "review-decision://analysis/mismatch",
                    },
                    "memory_influence_execution_allowed": False,
                    "memory_influence_tool_dispatch_allowed": False,
                },
                request_id="req-reviewed-playbook-ignored",
                session_id="sess-reviewed-playbook-ignored",
                correlation_id="req-reviewed-playbook-ignored",
            )
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-reviewed-playbook-ignored")
    )

    assert audit.memory_influence_selected_refs == []
    assert audit.memory_influence_used_refs == []
    assert audit.memory_influence_ignored_refs == [revoked_ref, mismatch_ref]
    assert audit.memory_influence_non_use_reasons == non_use_reasons
    assert audit.memory_influence_reasons == [
        "reviewed_procedural_playbook_ignored:"
        f"{revoked_ref}:review_status_not_eligible:revoked",
        "reviewed_procedural_playbook_ignored:"
        f"{mismatch_ref}:scope_mismatch:route",
    ]
    assert audit.procedural_artifact_refs == []
    assert audit.memory_influence_execution_allowed is False
    assert audit.memory_influence_tool_dispatch_allowed is False
    assert audit.operation_status is None


def test_observability_service_surfaces_unsafe_memory_influence_authority_flags() -> None:
    temp_dir = runtime_dir("observability-memory-influence-authority")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-memory-authority-safe",
                event_name="memory_influence_governed",
                timestamp="2026-07-18T13:07:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_execution_allowed": False,
                    "memory_influence_tool_dispatch_allowed": False,
                },
                request_id="req-memory-authority",
                session_id="sess-memory-authority",
                correlation_id="req-memory-authority",
            ),
            InternalEventEnvelope(
                event_id="evt-memory-authority-unsafe",
                event_name="plan_built",
                timestamp="2026-07-18T13:07:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "memory_influence_execution_allowed": True,
                    "memory_influence_tool_dispatch_allowed": True,
                },
                request_id="req-memory-authority",
                session_id="sess-memory-authority",
                correlation_id="req-memory-authority",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-memory-authority"))

    assert audit.memory_influence_execution_allowed is True
    assert audit.memory_influence_tool_dispatch_allowed is True
    assert audit.memory_influence_governance_drift_flags == [
        "memory_influence_execution_authority_claim_not_allowed",
        "memory_influence_tool_dispatch_authority_claim_not_allowed",
    ]
    assert all(
        flag in audit.anomaly_flags
        for flag in audit.memory_influence_governance_drift_flags
    )
    assert audit.operation_status is None


def test_observability_service_flags_archivable_guided_memory_reuse() -> None:
    temp_dir = runtime_dir("observability-archivable-guided-memory")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-archivable-memory",
                event_name="specialist_shared_memory_linked",
                timestamp="2026-04-09T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={
                    "sharing_modes": {
                        "software_change_specialist": "core_mediated_read_only"
                    },
                    "memory_class_policies": {
                        "software_change_specialist": {
                            "mission": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                            "semantic": {
                                "specialist_shared": True,
                                "sharing_mode": "core_mediated_read_only",
                                "write_policy": "through_core_only",
                            },
                        }
                    },
                    "consumed_memory_classes": {
                        "software_change_specialist": ["mission", "semantic"]
                    },
                    "memory_write_policies": {
                        "software_change_specialist": {
                            "mission": "through_core_only",
                            "semantic": "through_core_only",
                        }
                    },
                    "memory_refs_by_specialist": {
                        "software_change_specialist": [
                            "memory://mission",
                            "memory://semantic/mission/old",
                        ]
                    },
                    "semantic_focus_by_specialist": {
                        "software_change_specialist": ["software_development"]
                    },
                    "consumer_modes": {
                        "software_change_specialist": "domain_guided_memory_packet"
                    },
                    "consumer_profiles": {
                        "software_change_specialist": "software_change_review"
                    },
                    "consumer_objectives": {
                        "software_change_specialist": "review rollout change"
                    },
                    "expected_deliverables": {
                        "software_change_specialist": ["change_assessment"]
                    },
                    "telemetry_focus": {
                        "software_change_specialist": ["change_trace"]
                    },
                    "domain_mission_link_reasons": {
                        "software_change_specialist": "software route linked to active mission"
                    },
                    "semantic_memory_states": {
                        "software_change_specialist": "archivable"
                    },
                    "procedural_memory_states": {
                        "software_change_specialist": "archivable"
                    },
                    "memory_consolidation_statuses": {
                        "software_change_specialist": "revisit_before_reuse"
                    },
                    "memory_fixation_statuses": {
                        "software_change_specialist": "not_fixed"
                    },
                    "memory_archive_statuses": {
                        "software_change_specialist": "archive_candidate"
                    },
                    "memory_review_statuses": {
                        "software_change_specialist": "review_recommended"
                    },
                },
                request_id="req-archivable-memory",
                session_id="sess-archivable-memory",
                correlation_id="req-archivable-memory",
            )
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-archivable-memory"))

    assert audit.memory_alignment_status == "attention_required"


def test_observability_service_tracks_cognitive_recomposition_alignment() -> None:
    temp_dir = runtime_dir("observability-cognitive-recomposition")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-cr1",
                event_name="input_received",
                timestamp="2026-04-02T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Resolve the domain impasse before answering."},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr2",
                event_name="memory_recovered",
                timestamp="2026-04-02T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr3",
                event_name="intent_classified",
                timestamp="2026-04-02T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr4",
                event_name="context_composed",
                timestamp="2026-04-02T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_analitica", "mente_critica"],
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "supporting_minds": ["mente_critica"],
                    "suppressed_minds": ["mente_expressiva"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar profundidade analitica com conclusao util",
                    "arbitration_summary": (
                        "mente analitica lidera com recomposicao critica"
                    ),
                    "arbitration_source": "mind_registry_recomposition",
                    "canonical_domains": [
                        "dados_estatistica_e_inteligencia_analitica"
                    ],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr5",
                event_name="cognitive_recomposition_applied",
                timestamp="2026-04-02T00:00:03.500000+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "supporting_minds": ["mente_critica"],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr6",
                event_name="plan_built",
                timestamp="2026-04-02T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr7",
                event_name="continuity_decided",
                timestamp="2026-04-02T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr8",
                event_name="governance_checked",
                timestamp="2026-04-02T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr9",
                event_name="domain_specialist_completed",
                timestamp="2026-04-02T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_types": ["structured_analysis_specialist"],
                    "primary_domain_driver": (
                        "dados_estatistica_e_inteligencia_analitica"
                    ),
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": True
                    },
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr10",
                event_name="response_synthesized",
                timestamp="2026-04-02T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_analitica",
                    "primary_mind_family": "fundamental",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                    "arbitration_source": "mind_registry_recomposition",
                    "cognitive_recomposition_applied": True,
                    "cognitive_recomposition_reason": (
                        "primary domain driver has no matching guided specialist route"
                    ),
                    "cognitive_recomposition_trigger": "specialist_route_impasse",
                },
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
            InternalEventEnvelope(
                event_id="evt-cr11",
                event_name="memory_recorded",
                timestamp="2026-04-02T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cognitive-recomposition",
                session_id="sess-cognitive-recomposition",
                correlation_id="req-cognitive-recomposition",
            ),
        ]
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-cognitive-recomposition")
    )

    assert audit.mind_alignment_status == "healthy"
    assert audit.mind_domain_specialist_status == "aligned"
    assert audit.cognitive_recomposition_applied is True
    assert (
        audit.cognitive_recomposition_trigger == "specialist_route_impasse"
    )


def test_observability_service_tracks_mid_flow_cognitive_strategy_shift() -> None:
    temp_dir = runtime_dir("observability-cognitive-strategy-shift")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-css1",
                event_name="input_received",
                timestamp="2026-04-09T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Resolve the strategic impasse before concluding."},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css2",
                event_name="memory_recovered",
                timestamp="2026-04-09T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css3",
                event_name="intent_classified",
                timestamp="2026-04-09T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css4",
                event_name="context_composed",
                timestamp="2026-04-09T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "active_minds": ["mente_executiva", "mente_critica"],
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "supporting_minds": ["mente_critica"],
                    "suppressed_minds": ["mente_expressiva"],
                    "supporting_mind_limit": 2,
                    "suppressed_mind_limit": 3,
                    "dominant_tension": "equilibrar direcao estrategica com checkpoint governado",
                    "arbitration_summary": "mente executiva lidera com apoio critico",
                    "arbitration_source": "mind_registry",
                    "canonical_domains": ["estrategia_e_pensamento_sistemico"],
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css5",
                event_name="plan_built",
                timestamp="2026-04-09T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "mind_disagreement_status": "validation_required",
                    "mind_validation_checkpoints": ["validar o checkpoint estrategico"],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css6",
                event_name="continuity_decided",
                timestamp="2026-04-09T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css7",
                event_name="plan_refined",
                timestamp="2026-04-09T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={
                    "cognitive_strategy_shift_applied": True,
                    "cognitive_strategy_shift_summary": (
                        "revisao especializada manteve tensao aberta sob workflow governado; "
                        "checkpoint ativo scenario framed; loop alinhar checkpoint principal"
                    ),
                    "cognitive_strategy_shift_trigger": "guided_validation_impasse",
                    "cognitive_strategy_shift_effects": [
                        "steps",
                        "constraints",
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css8",
                event_name="governance_checked",
                timestamp="2026-04-09T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css9",
                event_name="response_synthesized",
                timestamp="2026-04-09T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "continuar",
                    "primary_mind": "mente_executiva",
                    "primary_mind_family": "estrategica_decisoria",
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                    "workflow_output_status": "coherent",
                    "cognitive_strategy_shift_applied": True,
                    "cognitive_strategy_shift_summary": (
                        "revisao especializada manteve tensao aberta sob workflow governado; "
                        "checkpoint ativo scenario framed; loop alinhar checkpoint principal"
                    ),
                    "cognitive_strategy_shift_trigger": "guided_validation_impasse",
                    "cognitive_strategy_shift_effects": [
                        "steps",
                        "constraints",
                        "success_criteria",
                        "smallest_safe_next_action",
                    ],
                },
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
            InternalEventEnvelope(
                event_id="evt-css10",
                event_name="memory_recorded",
                timestamp="2026-04-09T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-cognitive-shift",
                session_id="sess-cognitive-shift",
                correlation_id="req-cognitive-shift",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-cognitive-shift"))

    assert audit.cognitive_strategy_shift_status == "healthy"
    assert audit.cognitive_strategy_shift_applied is True
    assert audit.cognitive_strategy_shift_trigger == "guided_validation_impasse"
    assert "steps" in audit.cognitive_strategy_shift_effects


def test_observability_service_tracks_specialist_subflow_and_mission_runtime_state() -> None:
    temp_dir = runtime_dir("observability-pre-v3-hardening")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-p1",
                event_name="input_received",
                timestamp="2026-04-03T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan the pilot checkpoint."},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p2",
                event_name="memory_recovered",
                timestamp="2026-04-03T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p3",
                event_name="intent_classified",
                timestamp="2026-04-03T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "planning"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p4",
                event_name="context_composed",
                timestamp="2026-04-03T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_domain_driver": "estrategia_e_pensamento_sistemico",
                    "arbitration_source": "mind_registry",
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p5",
                event_name="plan_built",
                timestamp="2026-04-03T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p6",
                event_name="continuity_decided",
                timestamp="2026-04-03T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p7",
                event_name="specialist_selection_decided",
                timestamp="2026-04-03T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"domain_specialists": ["structured_analysis_specialist"]},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p8",
                event_name="specialist_subflow_completed",
                timestamp="2026-04-03T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "native_pipeline",
                    "subflow_name": "specialist_handoffs",
                    "selection_status": "selected",
                    "governance_status": "approved",
                    "dispatch_status": "dispatched",
                    "completion_status": "completed",
                    "selection_count": 1,
                    "invocation_count": 1,
                    "contribution_count": 1,
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p9",
                event_name="mission_runtime_state_declared",
                timestamp="2026-04-03T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={
                    "runtime_mode": "native_pipeline",
                    "mission_id": "mission-pre-v3",
                    "mission_goal": "Plan the pilot checkpoint.",
                    "mission_status": "active",
                    "continuity_action": "continuar",
                    "continuity_source": "active_mission",
                    "primary_route": "strategy",
                    "workflow_profile": "strategic_direction_workflow",
                    "active_task_count": 2,
                    "open_loop_count": 1,
                },
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p10",
                event_name="governance_checked",
                timestamp="2026-04-03T00:00:09+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p11",
                event_name="response_synthesized",
                timestamp="2026-04-03T00:00:10+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
            InternalEventEnvelope(
                event_id="evt-p12",
                event_name="memory_recorded",
                timestamp="2026-04-03T00:00:11+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "continuar"},
                request_id="req-pre-v3",
                session_id="sess-pre-v3",
                mission_id="mission-pre-v3",
                correlation_id="req-pre-v3",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-pre-v3"))

    assert audit.specialist_subflow_status == "healthy"
    assert audit.specialist_subflow_runtime_mode == "native_pipeline"
    assert audit.mission_runtime_state_status == "healthy"
    assert audit.trace_complete is True


def _adaptive_intervention_policy_events(
    *,
    request_id: str,
    session_id: str,
    workflow_profile: str,
    selected_action: str,
    trigger: str,
    reason: str,
    mind_disagreement_status: str = "not_applicable",
    memory_review_status: str = "stable",
    memory_corpus_status: str | None = None,
    memory_retention_pressure: str | None = None,
) -> list[InternalEventEnvelope]:
    shared_memory_payload: dict[str, object] = {}
    if memory_corpus_status is not None:
        shared_memory_payload["memory_corpus_statuses"] = {
            "structured_analysis_specialist": memory_corpus_status
        }
    if memory_retention_pressure is not None:
        shared_memory_payload["memory_retention_pressures"] = {
            "structured_analysis_specialist": memory_retention_pressure
        }

    return [
        InternalEventEnvelope(
            event_id=f"{request_id}-1",
            event_name="input_received",
            timestamp="2026-04-10T00:00:00+00:00",
            source_service="orchestrator-service",
            payload={"content": "audit adaptive intervention policy"},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-2",
            event_name="memory_recovered",
            timestamp="2026-04-10T00:00:01+00:00",
            source_service="orchestrator-service",
            payload={},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-3",
            event_name="intent_classified",
            timestamp="2026-04-10T00:00:02+00:00",
            source_service="orchestrator-service",
            payload={"intent": "analysis"},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-4",
            event_name="context_composed",
            timestamp="2026-04-10T00:00:03+00:00",
            source_service="orchestrator-service",
            payload={
                "primary_mind": "mente_analitica",
                "primary_mind_family": "fundamental",
                "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                "arbitration_source": "mind_registry",
                "dominant_tension": "equilibrar profundidade analitica com fechamento util",
            },
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-5",
            event_name="workflow_composed",
            timestamp="2026-04-10T00:00:04+00:00",
            source_service="orchestrator-service",
            payload={
                "workflow_profile": workflow_profile,
                "workflow_domain_route": "analysis",
                "workflow_governance_mode": "guided_runtime_contract",
            },
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-6",
            event_name="plan_built",
            timestamp="2026-04-10T00:00:05+00:00",
            source_service="orchestrator-service",
            payload={
                "mind_disagreement_status": mind_disagreement_status,
                "mind_validation_checkpoints": ["validar a proxima decisao"],
                "memory_review_status": memory_review_status,
                "adaptive_intervention_status": "applied",
                "adaptive_intervention_reason": reason,
                "adaptive_intervention_trigger": trigger,
                "adaptive_intervention_selected_action": selected_action,
                "adaptive_intervention_expected_effect": "preserve a governed next step",
                "adaptive_intervention_effects": [
                    "steps",
                    "constraints",
                    "success_criteria",
                    "smallest_safe_next_action",
                ],
            },
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-7",
            event_name="continuity_decided",
            timestamp="2026-04-10T00:00:06+00:00",
            source_service="orchestrator-service",
            payload={"continuity_action": "continuar", "continuity_source": "active_mission"},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-8",
            event_name="governance_checked",
            timestamp="2026-04-10T00:00:07+00:00",
            source_service="orchestrator-service",
            payload={"decision": "allow_with_conditions"},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-9",
            event_name="response_synthesized",
            timestamp="2026-04-10T00:00:08+00:00",
            source_service="orchestrator-service",
            payload={
                "continuity_action": "continuar",
                "workflow_output_status": "coherent",
                "mind_disagreement_status": mind_disagreement_status,
                "adaptive_intervention_status": "applied",
                "adaptive_intervention_reason": reason,
                "adaptive_intervention_trigger": trigger,
                "adaptive_intervention_selected_action": selected_action,
                "adaptive_intervention_expected_effect": "preserve a governed next step",
                "adaptive_intervention_effects": [
                    "steps",
                    "constraints",
                    "success_criteria",
                    "smallest_safe_next_action",
                ],
            },
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-10",
            event_name="memory_recorded",
            timestamp="2026-04-10T00:00:09+00:00",
            source_service="orchestrator-service",
            payload={"continuity_mode": "continuar"},
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
        InternalEventEnvelope(
            event_id=f"{request_id}-11",
            event_name="specialist_shared_memory_linked",
            timestamp="2026-04-10T00:00:10+00:00",
            source_service="orchestrator-service",
            payload=shared_memory_payload,
            request_id=request_id,
            session_id=session_id,
            correlation_id=request_id,
        ),
    ]


def test_observability_service_marks_workflow_priority_as_policy_aligned() -> None:
    temp_dir = runtime_dir("observability-adaptive-policy-aligned")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        _adaptive_intervention_policy_events(
            request_id="req-adaptive-policy-aligned",
            session_id="sess-adaptive-policy-aligned",
            workflow_profile="operational_readiness_workflow",
            selected_action="memory_review_checkpoint",
            trigger="memory_review_recommended",
            reason="pressao de memoria exige checkpoint de revisao",
            mind_disagreement_status="validation_required",
            memory_review_status="review_recommended",
            memory_corpus_status="review_recommended",
        )
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-adaptive-policy-aligned")
    )

    assert audit.adaptive_intervention_status == "healthy"
    assert audit.adaptive_intervention_policy_status == "policy_aligned"


def _workflow_lifecycle_payload(
    *,
    status: str,
    action: str | None,
    transition_id: str | None,
    revision: int | None,
    active_version_ref: str | None,
    active_definition_hash: str | None,
    human_authorized: bool,
    operator_ref: str | None,
    resolution_reasons: list[str] | None = None,
) -> dict[str, object]:
    lifecycle_recorded = status in {"active_promoted", "baseline_restored"}
    resolved_active_version_ref = active_version_ref or (
        "workflow-version://software_change_workflow/1.0.0"
    )
    resolved_active_definition_hash = active_definition_hash or "0" * 64
    baseline_version_ref = (
        resolved_active_version_ref
        if status in {"static_baseline", "static_baseline_fallback", "baseline_restored"}
        else "workflow-version://software_change_workflow/1.0.0"
    )
    baseline_definition_hash = (
        resolved_active_definition_hash
        if status in {"static_baseline", "static_baseline_fallback", "baseline_restored"}
        else "0" * 64
    )
    candidate_version_ref = (
        resolved_active_version_ref
        if status == "active_promoted"
        else (
            "workflow-version://software_change_workflow/1.1.0"
            if status == "baseline_restored"
            else None
        )
    )
    candidate_definition_hash = (
        resolved_active_definition_hash
        if status == "active_promoted"
        else "a" * 64 if status == "baseline_restored" else None
    )
    human_authorization_ref = (
        "human-authorization://workflow/software-change/test"
        if lifecycle_recorded
        else None
    )
    evolution_proposal_id = (
        "proposal://workflow/software-change/test" if lifecycle_recorded else None
    )
    review_decision_id = (
        "review://workflow/software-change/test" if lifecycle_recorded else None
    )
    release_checklist_id = (
        "checklist://workflow/software-change/test" if lifecycle_recorded else None
    )
    promotion_gate_id = (
        "gate://workflow/software-change/test" if lifecycle_recorded else None
    )
    eval_run_id = (
        "eval://workflow/software-change/test" if lifecycle_recorded else None
    )
    rollback_plan_id = (
        "rollback://workflow/software-change/test" if lifecycle_recorded else None
    )
    evidence_refs = (
        [
            evolution_proposal_id,
            review_decision_id,
            release_checklist_id,
            promotion_gate_id,
            eval_run_id,
            rollback_plan_id,
            human_authorization_ref,
        ]
        if lifecycle_recorded
        else []
    )
    return {
        "workflow_lifecycle_status": status,
        "workflow_lifecycle_resolution_reasons": list(resolution_reasons or []),
        "workflow_lifecycle_transition_id": transition_id,
        "workflow_lifecycle_revision": revision,
        "workflow_lifecycle_action": action,
        "workflow_lifecycle_active_version_ref": resolved_active_version_ref,
        "workflow_lifecycle_active_definition_hash": resolved_active_definition_hash,
        "workflow_lifecycle_baseline_version_ref": baseline_version_ref,
        "workflow_lifecycle_baseline_definition_hash": baseline_definition_hash,
        "workflow_lifecycle_candidate_version_ref": candidate_version_ref,
        "workflow_lifecycle_candidate_definition_hash": candidate_definition_hash,
        "workflow_lifecycle_source_registry_ref": "active-workflow-registry://v1",
        "workflow_lifecycle_source_registry_fingerprint": "9" * 64,
        "workflow_lifecycle_human_authorization_ref": human_authorization_ref,
        "workflow_lifecycle_human_authorized": human_authorized,
        "workflow_lifecycle_operator_ref": operator_ref,
        "workflow_lifecycle_evidence_refs": evidence_refs,
        "workflow_lifecycle_completed_test_refs": (
            ["test://workflow/software-change/release"]
            if lifecycle_recorded
            else []
        ),
        "workflow_lifecycle_failure_refs": (
            ["failure://workflow/software-change/regression"]
            if status == "baseline_restored"
            else []
        ),
        "workflow_lifecycle_evolution_proposal_id": evolution_proposal_id,
        "workflow_lifecycle_proposal_fingerprint": (
            "1" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_review_decision_id": review_decision_id,
        "workflow_lifecycle_review_decision_fingerprint": (
            "2" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_release_checklist_id": release_checklist_id,
        "workflow_lifecycle_release_checklist_fingerprint": (
            "3" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_promotion_gate_id": promotion_gate_id,
        "workflow_lifecycle_promotion_gate_fingerprint": (
            "4" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_eval_run_id": eval_run_id,
        "workflow_lifecycle_eval_run_fingerprint": (
            "5" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_rollback_plan_id": rollback_plan_id,
        "workflow_lifecycle_rollback_plan_fingerprint": (
            "6" * 64 if lifecycle_recorded else None
        ),
        "workflow_lifecycle_active_registry_write_allowed": False,
        "workflow_lifecycle_runtime_execution_allowed": False,
        "workflow_lifecycle_automatic_promotion_allowed": False,
        "workflow_lifecycle_automatic_rollback_allowed": False,
        "workflow_lifecycle_core_mutation_allowed": False,
    }


def _workflow_lifecycle_event(
    *,
    request_id: str,
    event_name: str,
    position: int,
    payload: dict[str, object],
) -> InternalEventEnvelope:
    return InternalEventEnvelope(
        event_id=f"evt-{request_id}-{event_name}",
        event_name=event_name,
        timestamp=f"2026-08-12T12:00:{position:02d}+00:00",
        source_service="orchestrator-service",
        payload=payload,
        request_id=request_id,
        session_id=f"session-{request_id}",
        correlation_id=request_id,
    )


def _audit_workflow_lifecycle(
    service: ObservabilityService,
    *,
    request_id: str,
):
    return service.audit_flow(
        ObservabilityQuery(request_id=request_id),
        required_events=("plan_built", "response_synthesized"),
    )


def test_flow_audit_projects_active_workflow_lifecycle_across_runtime_stages() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-active")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-active"
    payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/1",
        revision=1,
        active_version_ref="workflow-version://software_change_workflow/1.1.0",
        active_definition_hash="a" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=dict(payload),
            )
            for position, event_name in enumerate(
                (
                    "plan_built",
                    "response_synthesized",
                    "operation_dispatched",
                    "operation_completed",
                ),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)
    report = service.build_incident_evidence(
        ObservabilityQuery(request_id=request_id),
        required_events=("plan_built", "response_synthesized"),
    )

    assert audit.workflow_lifecycle_status == "active_promoted"
    assert audit.workflow_lifecycle_action == "activate_candidate"
    assert audit.workflow_lifecycle_transition_id == (
        "workflow-lifecycle-transition://software-change/1"
    )
    assert audit.workflow_lifecycle_revision == 1
    assert audit.workflow_lifecycle_active_version_ref == (
        "workflow-version://software_change_workflow/1.1.0"
    )
    assert audit.workflow_lifecycle_active_definition_hash == "a" * 64
    assert audit.workflow_lifecycle_baseline_version_ref.endswith("/1.0.0")
    assert audit.workflow_lifecycle_baseline_definition_hash == "0" * 64
    assert audit.workflow_lifecycle_candidate_version_ref == (
        audit.workflow_lifecycle_active_version_ref
    )
    assert audit.workflow_lifecycle_candidate_definition_hash == "a" * 64
    assert audit.workflow_lifecycle_source_registry_ref == (
        "active-workflow-registry://v1"
    )
    assert audit.workflow_lifecycle_source_registry_fingerprint == "9" * 64
    assert audit.workflow_lifecycle_human_authorization_ref == (
        "human-authorization://workflow/software-change/test"
    )
    assert audit.workflow_lifecycle_human_authorized is True
    assert audit.workflow_lifecycle_operator_ref == "operator://primary"
    assert audit.workflow_lifecycle_authority_safe is True
    assert audit.workflow_lifecycle_trace_status == "healthy"
    assert audit.workflow_lifecycle_drift_flags == []
    assert audit.workflow_lifecycle_evolution_proposal_id == (
        "proposal://workflow/software-change/test"
    )
    assert audit.workflow_lifecycle_proposal_fingerprint == "1" * 64
    assert audit.workflow_lifecycle_review_decision_fingerprint == "2" * 64
    assert audit.workflow_lifecycle_release_checklist_fingerprint == "3" * 64
    assert audit.workflow_lifecycle_promotion_gate_fingerprint == "4" * 64
    assert audit.workflow_lifecycle_eval_run_fingerprint == "5" * 64
    assert audit.workflow_lifecycle_rollback_plan_fingerprint == "6" * 64
    assert report.workflow_lifecycle_status == "active_promoted"
    assert report.workflow_lifecycle_action == "activate_candidate"
    assert report.workflow_lifecycle_transition_id == (
        audit.workflow_lifecycle_transition_id
    )
    assert report.workflow_lifecycle_revision == 1
    assert report.workflow_lifecycle_active_version_ref == (
        audit.workflow_lifecycle_active_version_ref
    )
    assert report.workflow_lifecycle_active_definition_hash == "a" * 64
    assert report.workflow_lifecycle_baseline_definition_hash == "0" * 64
    assert report.workflow_lifecycle_candidate_definition_hash == "a" * 64
    assert report.workflow_lifecycle_human_authorization_ref == (
        audit.workflow_lifecycle_human_authorization_ref
    )
    assert report.workflow_lifecycle_proposal_fingerprint == "1" * 64
    assert report.workflow_lifecycle_rollback_plan_fingerprint == "6" * 64
    assert report.workflow_lifecycle_human_authorized is True
    assert report.workflow_lifecycle_operator_ref == "operator://primary"
    assert report.workflow_lifecycle_authority_safe is True
    assert report.workflow_lifecycle_drift_flags == []


def test_flow_audit_projects_human_workflow_rollback() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-rollback")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-rollback"
    payload = _workflow_lifecycle_payload(
        status="baseline_restored",
        action="rollback_to_baseline",
        transition_id="workflow-lifecycle-transition://software-change/2",
        revision=2,
        active_version_ref="workflow-version://software_change_workflow/1.0.0",
        active_definition_hash="b" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=dict(payload),
            )
            for position, event_name in enumerate(
                ("plan_built", "response_synthesized"),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_status == "baseline_restored"
    assert audit.workflow_lifecycle_action == "rollback_to_baseline"
    assert audit.workflow_lifecycle_revision == 2
    assert audit.workflow_lifecycle_active_version_ref.endswith("/1.0.0")
    assert audit.workflow_lifecycle_human_authorized is True
    assert audit.workflow_lifecycle_trace_status == "healthy"
    assert audit.workflow_lifecycle_drift_flags == []


def test_flow_audit_projects_explicit_and_inferred_static_workflow_baseline() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-static")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    explicit_request_id = "req-workflow-lifecycle-static-explicit"
    inferred_request_id = "req-workflow-lifecycle-static-inferred"
    static_payload = _workflow_lifecycle_payload(
        status="static_baseline",
        action=None,
        transition_id=None,
        revision=None,
        active_version_ref=None,
        active_definition_hash=None,
        human_authorized=False,
        operator_ref=None,
    )
    service.ingest_events(
        [
            *[
                _workflow_lifecycle_event(
                    request_id=explicit_request_id,
                    event_name=event_name,
                    position=position,
                    payload=dict(static_payload),
                )
                for position, event_name in enumerate(
                    ("plan_built", "response_synthesized"),
                    start=1,
                )
            ],
            *[
                _workflow_lifecycle_event(
                    request_id=inferred_request_id,
                    event_name=event_name,
                    position=position,
                    payload={},
                )
                for position, event_name in enumerate(
                    ("plan_built", "response_synthesized"),
                    start=1,
                )
            ],
        ]
    )

    explicit = _audit_workflow_lifecycle(service, request_id=explicit_request_id)
    inferred = _audit_workflow_lifecycle(service, request_id=inferred_request_id)

    assert explicit.workflow_lifecycle_status == "static_baseline"
    assert explicit.workflow_lifecycle_trace_status == "healthy"
    assert explicit.workflow_lifecycle_active_version_ref == (
        explicit.workflow_lifecycle_baseline_version_ref
    )
    assert explicit.workflow_lifecycle_active_definition_hash == (
        explicit.workflow_lifecycle_baseline_definition_hash
    )
    assert explicit.workflow_lifecycle_source_registry_ref == (
        "active-workflow-registry://v1"
    )
    assert explicit.workflow_lifecycle_source_registry_fingerprint == "9" * 64
    assert explicit.workflow_lifecycle_transition_id is None
    assert explicit.workflow_lifecycle_human_authorization_ref is None
    assert explicit.workflow_lifecycle_operator_ref is None
    assert explicit.workflow_lifecycle_human_authorized is False
    assert explicit.workflow_lifecycle_authority_safe is True
    assert explicit.workflow_lifecycle_drift_flags == []
    assert inferred.workflow_lifecycle_status == "static_baseline"
    assert inferred.workflow_lifecycle_trace_status == "static_inferred"
    assert inferred.workflow_lifecycle_drift_flags == []


def test_flow_audit_fails_closed_when_lifecycle_runtime_event_is_missing() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-missing")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-missing"
    payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/missing",
        revision=3,
        active_version_ref="workflow-version://software_change_workflow/1.2.0",
        active_definition_hash="c" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name="plan_built",
                position=1,
                payload=payload,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert audit.workflow_lifecycle_drift_flags == [
        "workflow_lifecycle_event_missing:response_synthesized"
    ]
    assert all(
        flag in audit.anomaly_flags
        for flag in audit.workflow_lifecycle_drift_flags
    )
    assert audit.trace_complete is False


def test_flow_audit_fails_closed_on_lifecycle_projection_mismatch() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-mismatch")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-mismatch"
    plan_payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/mismatch",
        revision=4,
        active_version_ref="workflow-version://software_change_workflow/1.3.0",
        active_definition_hash="d" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    response_payload = dict(plan_payload)
    response_payload["workflow_lifecycle_active_version_ref"] = (
        "workflow-version://software_change_workflow/forged"
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name="plan_built",
                position=1,
                payload=plan_payload,
            ),
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name="response_synthesized",
                position=2,
                payload=response_payload,
            ),
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert (
        "workflow_lifecycle_projection_mismatch:active_version_ref"
        in audit.workflow_lifecycle_drift_flags
    )
    assert audit.trace_complete is False


def test_flow_audit_compares_optional_workflow_lifecycle_runtime_events() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-intermediate-mismatch")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-intermediate-mismatch"
    payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/intermediate",
        revision=7,
        active_version_ref="workflow-version://software_change_workflow/1.6.0",
        active_definition_hash="7" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    workflow_composed_payload = dict(payload)
    workflow_composed_payload["workflow_lifecycle_active_version_ref"] = (
        "workflow-version://software_change_workflow/9.9.9"
    )
    workflow_governance_payload = dict(payload)
    workflow_governance_payload["workflow_lifecycle_promotion_gate_fingerprint"] = (
        "f" * 64
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=(
                    workflow_composed_payload
                    if event_name == "workflow_composed"
                    else (
                        workflow_governance_payload
                        if event_name == "workflow_governance_declared"
                        else dict(payload)
                    )
                ),
            )
            for position, event_name in enumerate(
                (
                    "plan_built",
                    "workflow_composed",
                    "workflow_governance_declared",
                    "operation_dispatched",
                    "operation_completed",
                    "workflow_completed",
                    "response_synthesized",
                ),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert (
        "workflow_lifecycle_projection_mismatch:active_version_ref"
        in audit.workflow_lifecycle_drift_flags
    )
    assert (
        "workflow_lifecycle_projection_mismatch:promotion_gate_fingerprint"
        in audit.workflow_lifecycle_drift_flags
    )
    assert audit.trace_complete is False


def test_flow_audit_surfaces_static_baseline_fallback_as_anomaly() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-fallback")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-fallback"
    fallback_reason = "workflow_lifecycle_store_unavailable:RuntimeError"
    payload = _workflow_lifecycle_payload(
        status="static_baseline_fallback",
        action=None,
        transition_id=None,
        revision=None,
        active_version_ref="workflow-version://software_change_workflow/1.0.0",
        active_definition_hash="8" * 64,
        human_authorized=False,
        operator_ref=None,
        resolution_reasons=[fallback_reason],
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=dict(payload),
            )
            for position, event_name in enumerate(
                ("plan_built", "response_synthesized"),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_status == "static_baseline_fallback"
    assert audit.workflow_lifecycle_resolution_reasons == [fallback_reason]
    assert audit.workflow_lifecycle_active_version_ref.endswith("/1.0.0")
    assert audit.workflow_lifecycle_baseline_version_ref == (
        audit.workflow_lifecycle_active_version_ref
    )
    assert audit.workflow_lifecycle_source_registry_fingerprint == "9" * 64
    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert "workflow_lifecycle_static_baseline_fallback" in (
        audit.workflow_lifecycle_drift_flags
    )
    assert f"workflow_lifecycle_resolution_reason:{fallback_reason}" in (
        audit.anomaly_flags
    )
    assert audit.trace_complete is False


def test_flow_audit_rejects_lifecycle_authority_claims() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-authority")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-authority"
    unsafe_payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/unsafe",
        revision=5,
        active_version_ref="workflow-version://software_change_workflow/1.4.0",
        active_definition_hash="e" * 64,
        human_authorized=True,
        operator_ref="operator://primary",
    )
    unsafe_payload.update(
        {
            "workflow_lifecycle_active_registry_write_allowed": True,
            "workflow_lifecycle_runtime_execution_allowed": True,
            "workflow_lifecycle_automatic_promotion_allowed": True,
            "workflow_lifecycle_automatic_rollback_allowed": True,
            "workflow_lifecycle_core_mutation_allowed": True,
        }
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=dict(unsafe_payload),
            )
            for position, event_name in enumerate(
                ("plan_built", "response_synthesized"),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)
    report = service.build_incident_evidence(
        ObservabilityQuery(request_id=request_id),
        required_events=("plan_built", "response_synthesized"),
    )

    expected_authority_drift = {
        "workflow_lifecycle_active_registry_write_claim_not_allowed",
        "workflow_lifecycle_runtime_execution_claim_not_allowed",
        "workflow_lifecycle_automatic_promotion_claim_not_allowed",
        "workflow_lifecycle_automatic_rollback_claim_not_allowed",
        "workflow_lifecycle_core_mutation_claim_not_allowed",
    }
    assert audit.workflow_lifecycle_authority_safe is False
    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert expected_authority_drift.issubset(audit.workflow_lifecycle_drift_flags)
    assert expected_authority_drift.issubset(audit.anomaly_flags)
    assert report.workflow_lifecycle_trace_status == "attention_required"
    assert report.workflow_lifecycle_authority_safe is False
    assert expected_authority_drift.issubset(
        report.workflow_lifecycle_drift_flags
    )
    assert audit.trace_complete is False


def test_flow_audit_requires_human_authorization_for_lifecycle() -> None:
    temp_dir = runtime_dir("observability-workflow-lifecycle-human-authorization")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    request_id = "req-workflow-lifecycle-human-authorization"
    unauthorized_payload = _workflow_lifecycle_payload(
        status="active_promoted",
        action="activate_candidate",
        transition_id="workflow-lifecycle-transition://software-change/no-human",
        revision=6,
        active_version_ref="workflow-version://software_change_workflow/1.5.0",
        active_definition_hash="f" * 64,
        human_authorized=False,
        operator_ref="operator://primary",
    )
    service.ingest_events(
        [
            _workflow_lifecycle_event(
                request_id=request_id,
                event_name=event_name,
                position=position,
                payload=dict(unauthorized_payload),
            )
            for position, event_name in enumerate(
                ("plan_built", "response_synthesized"),
                start=1,
            )
        ]
    )

    audit = _audit_workflow_lifecycle(service, request_id=request_id)

    assert audit.workflow_lifecycle_human_authorized is False
    assert audit.workflow_lifecycle_trace_status == "attention_required"
    assert audit.workflow_lifecycle_drift_flags == [
        "workflow_lifecycle_human_authorization_missing"
    ]
    assert "workflow_lifecycle_human_authorization_missing" in audit.anomaly_flags
    assert audit.trace_complete is False


def test_observability_service_marks_mandatory_override_for_clarification() -> None:
    temp_dir = runtime_dir("observability-adaptive-policy-override")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        _adaptive_intervention_policy_events(
            request_id="req-adaptive-policy-override",
            session_id="sess-adaptive-policy-override",
            workflow_profile="structured_analysis_workflow",
            selected_action="clarification_checkpoint",
            trigger="clarification_required",
            reason="pedido ainda exige checkpoint soberano de clarificacao",
        )
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-adaptive-policy-override")
    )

    assert audit.adaptive_intervention_status == "healthy"
    assert audit.adaptive_intervention_policy_status == "mandatory_override"


def test_observability_service_flags_adaptive_intervention_policy_mismatch() -> None:
    temp_dir = runtime_dir("observability-adaptive-policy-mismatch")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        _adaptive_intervention_policy_events(
            request_id="req-adaptive-policy-mismatch",
            session_id="sess-adaptive-policy-mismatch",
            workflow_profile="structured_analysis_workflow",
            selected_action="memory_review_checkpoint",
            trigger="memory_review_recommended",
            reason="pressao de memoria exige checkpoint de revisao",
            mind_disagreement_status="validation_required",
            memory_review_status="review_recommended",
            memory_corpus_status="review_recommended",
        )
    )

    audit = service.audit_flow(
        ObservabilityQuery(request_id="req-adaptive-policy-mismatch")
    )

    assert audit.adaptive_intervention_status == "healthy"
    assert audit.adaptive_intervention_policy_status == "attention_required"


def test_observability_service_marks_mind_domain_specialist_effective(
) -> None:
    temp_dir = runtime_dir("observability-mds-effective")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mds-eff-1",
                event_name="input_received",
                timestamp="2026-04-14T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze the release trade-offs."},
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-2",
                event_name="context_composed",
                timestamp="2026-04-14T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-3",
                event_name="specialist_selection_decided",
                timestamp="2026-04-14T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={
                    "domain_specialists": ["structured_analysis_specialist"],
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": True
                    },
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-4",
                event_name="workflow_composed",
                timestamp="2026-04-14T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_consumer_mode": (
                        "authoritative_specialist"
                    ),
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-5",
                event_name="operation_dispatched",
                timestamp="2026-04-14T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_hints": ["structured_analysis_specialist"],
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_consumer_mode": (
                        "authoritative_specialist"
                    ),
                    "mind_domain_specialist_framing_mode": (
                        "route_and_specialist_locked"
                    ),
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-6",
                event_name="domain_specialist_completed",
                timestamp="2026-04-14T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "domain_specialists": ["structured_analysis_specialist"],
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": True
                    },
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-eff-7",
                event_name="response_synthesized",
                timestamp="2026-04-14T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_chain_status": "aligned",
                    "mind_domain_specialist_chain": (
                        "mente_analitica -> dados_estatistica_e_inteligencia_analitica "
                        "-> analysis -> structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_consumer_mode": (
                        "authoritative_specialist"
                    ),
                    "mind_domain_specialist_framing_mode": (
                        "route_and_specialist_locked"
                    ),
                },
                request_id="req-mds-effective",
                session_id="sess-mds-effective",
                correlation_id="req-mds-effective",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-mds-effective"))

    assert audit.mind_domain_specialist_status == "aligned"
    assert audit.mind_domain_specialist_chain_status == "aligned"
    assert audit.mind_domain_specialist_effectiveness == "effective"
    assert audit.mind_domain_specialist_mismatch_flags == []


def test_observability_service_flags_mind_domain_specialist_final_consumption_mismatch() -> None:
    temp_dir = runtime_dir("observability-mds-mismatch")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-mds-mm-1",
                event_name="input_received",
                timestamp="2026-04-14T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Analyze the release trade-offs."},
                request_id="req-mds-mismatch",
                session_id="sess-mds-mismatch",
                correlation_id="req-mds-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-mm-2",
                event_name="context_composed",
                timestamp="2026-04-14T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "primary_mind": "mente_analitica",
                    "primary_domain_driver": "dados_estatistica_e_inteligencia_analitica",
                },
                request_id="req-mds-mismatch",
                session_id="sess-mds-mismatch",
                correlation_id="req-mds-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-mm-3",
                event_name="specialist_selection_decided",
                timestamp="2026-04-14T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={
                    "domain_specialists": ["structured_analysis_specialist"],
                    "primary_domain_driver_matches": {
                        "structured_analysis_specialist": True
                    },
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                },
                request_id="req-mds-mismatch",
                session_id="sess-mds-mismatch",
                correlation_id="req-mds-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-mm-4",
                event_name="operation_dispatched",
                timestamp="2026-04-14T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "specialist_hints": ["operational_planning_specialist"],
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_consumer_mode": (
                        "authoritative_specialist"
                    ),
                    "mind_domain_specialist_framing_mode": (
                        "route_and_specialist_locked"
                    ),
                },
                request_id="req-mds-mismatch",
                session_id="sess-mds-mismatch",
                correlation_id="req-mds-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-mds-mm-5",
                event_name="response_synthesized",
                timestamp="2026-04-14T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "mind_domain_specialist_contract_status": "authoritative_chain",
                    "mind_domain_specialist_chain_status": "aligned",
                    "mind_domain_specialist_active_specialist": (
                        "structured_analysis_specialist"
                    ),
                    "mind_domain_specialist_consumer_mode": (
                        "authoritative_specialist"
                    ),
                    "mind_domain_specialist_framing_mode": (
                        "route_and_specialist_locked"
                    ),
                },
                request_id="req-mds-mismatch",
                session_id="sess-mds-mismatch",
                correlation_id="req-mds-mismatch",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-mds-mismatch"))

    assert audit.mind_domain_specialist_status == "aligned"
    assert audit.mind_domain_specialist_effectiveness == "insufficient"
    assert "dispatch_specialist_mismatch" in audit.mind_domain_specialist_mismatch_flags


def test_observability_service_marks_request_identity_policy_aligned() -> None:
    temp_dir = runtime_dir("observability-request-identity-aligned")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-rip-1",
                event_name="input_received",
                timestamp="2026-04-20T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Plan the release milestone."},
                request_id="req-rip-aligned",
                session_id="sess-rip-aligned",
                correlation_id="req-rip-aligned",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-2",
                event_name="plan_built",
                timestamp="2026-04-20T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "plan the release milestone safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                    "request_identity_summary": (
                        "mission=plan the release milestone safely; "
                        "authority=bounded_execution; "
                        "confirmation=explicit_confirmation_required"
                    ),
                    "request_identity_policy_refs": [
                        "policy://request-identity/default"
                    ],
                },
                request_id="req-rip-aligned",
                session_id="sess-rip-aligned",
                correlation_id="req-rip-aligned",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-3",
                event_name="governance_checked",
                timestamp="2026-04-20T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={
                    "decision": "allow_with_conditions",
                    "request_identity_status": "resolved",
                    "request_active_mission": "plan the release milestone safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                },
                request_id="req-rip-aligned",
                session_id="sess-rip-aligned",
                correlation_id="req-rip-aligned",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-4",
                event_name="operation_dispatched",
                timestamp="2026-04-20T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "plan the release milestone safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                    "capability_decision_selected_mode": "core_with_local_operation",
                },
                request_id="req-rip-aligned",
                session_id="sess-rip-aligned",
                correlation_id="req-rip-aligned",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-5",
                event_name="response_synthesized",
                timestamp="2026-04-20T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "plan the release milestone safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                },
                request_id="req-rip-aligned",
                session_id="sess-rip-aligned",
                correlation_id="req-rip-aligned",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-rip-aligned"))

    assert audit.request_identity_status == "healthy"
    assert audit.mission_policy_status == "policy_aligned"
    assert audit.request_identity_mismatch_flags == []
    assert audit.expanded_eval_status == "attention_required"
    assert audit.surface_axis_status == "attention_required"
    assert audit.ecosystem_state_status == "attention_required"
    assert audit.experiment_lane_status == "attention_required"
    assert audit.promotion_readiness == "blocked"


def test_observability_service_flags_request_identity_confirmation_mismatch() -> None:
    temp_dir = runtime_dir("observability-request-identity-mismatch")
    service = ObservabilityService(database_path=str(temp_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-rip-mm-1",
                event_name="input_received",
                timestamp="2026-04-20T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "Apply the change directly."},
                request_id="req-rip-mismatch",
                session_id="sess-rip-mismatch",
                correlation_id="req-rip-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-mm-2",
                event_name="plan_built",
                timestamp="2026-04-20T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "apply the change safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                },
                request_id="req-rip-mismatch",
                session_id="sess-rip-mismatch",
                correlation_id="req-rip-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-mm-3",
                event_name="governance_checked",
                timestamp="2026-04-20T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow"},
                request_id="req-rip-mismatch",
                session_id="sess-rip-mismatch",
                correlation_id="req-rip-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-mm-4",
                event_name="operation_dispatched",
                timestamp="2026-04-20T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "apply the change safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                    "capability_decision_selected_mode": "core_with_local_operation",
                },
                request_id="req-rip-mismatch",
                session_id="sess-rip-mismatch",
                correlation_id="req-rip-mismatch",
            ),
            InternalEventEnvelope(
                event_id="evt-rip-mm-5",
                event_name="response_synthesized",
                timestamp="2026-04-20T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={
                    "request_identity_status": "resolved",
                    "request_active_mission": "apply the change safely",
                    "request_executive_posture": "structured_planning",
                    "request_authority_level": "bounded_execution",
                    "request_risk_profile": "governed_caution",
                    "request_reversibility_mode": "prefer_reversible_change",
                    "request_confirmation_mode": "explicit_confirmation_required",
                },
                request_id="req-rip-mismatch",
                session_id="sess-rip-mismatch",
                correlation_id="req-rip-mismatch",
            ),
        ]
    )

    audit = service.audit_flow(ObservabilityQuery(request_id="req-rip-mismatch"))

    assert audit.request_identity_status == "healthy"
    assert audit.mission_policy_status == "attention_required"
    assert "confirmation_mode_mismatch" in audit.request_identity_mismatch_flags
