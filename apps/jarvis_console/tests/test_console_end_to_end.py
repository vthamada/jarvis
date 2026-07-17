from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from evolution_lab.service import EvolutionLabService, PostTaskReflectionInput
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import FlowAudit, ObservabilityQuery

from apps.jarvis_console.cli import (
    JarvisConsole,
    build_parser,
    run_daily_workspace_command,
    run_longitudinal_learning_report_command,
    run_skill_evolution_command,
)
from shared.contracts import (
    ExperienceRecordContract,
    PostTaskReflectionContract,
    SkillCandidateContract,
)
from shared.types import RiskLevel


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


@dataclass(frozen=True)
class OperatorScenario:
    name: str
    prompt: str
    session_id: str
    mission_id: str | None
    expected_decision: str
    expected_route: str | None
    expected_workflow_profile: str | None
    expected_operation_status: str | None


def audit_response(console: JarvisConsole, request_id: str) -> FlowAudit:
    return console.orchestrator.observability_service.audit_flow(
        ObservabilityQuery(request_id=request_id, limit=200)
    )


def assert_core_trace_invariants(audit: FlowAudit) -> None:
    assert audit.workflow_trace_status in {"healthy", "not_applicable"}
    assert not audit.missing_required_events
    assert not audit.anomaly_flags
    assert "input_received" in audit.event_names
    assert "plan_built" in audit.event_names
    assert "response_synthesized" in audit.event_names
    assert "memory_recorded" in audit.event_names
    assert audit.workflow_profile_status in {
        "healthy",
        "maturation_recommended",
        "not_applicable",
    }
    assert audit.request_identity_status == "healthy"
    assert audit.mission_policy_status in {
        "policy_aligned",
        "mandatory_override",
        "attention_required",
    }
    assert audit.capability_decision_status == "healthy"
    assert audit.capability_effectiveness in {"effective", "insufficient"}
    assert audit.handoff_adapter_status in {"healthy", "contained", "attention_required"}
    assert audit.expanded_eval_status in {
        "candidate_ready",
        "baseline_expanding",
        "not_in_phase",
        "attention_required",
    }
    assert audit.surface_axis_status in {
        "candidate_ready",
        "coverage_partial",
        "not_in_phase",
        "attention_required",
    }
    assert audit.ecosystem_state_status in {
        "candidate_ready",
        "coverage_partial",
        "not_in_phase",
    }
    assert audit.experiment_lane_status in {
        "controlled_candidate",
        "baseline_only",
        "out_of_lane",
        "attention_required",
    }
    assert audit.mind_domain_specialist_effectiveness in {
        "effective",
        "insufficient",
        "not_applicable",
    }
    assert audit.memory_maintenance_status != "incomplete"
    assert audit.memory_maintenance_effectiveness in {"effective", "insufficient"}


def test_daily_workspace_reads_two_real_cross_session_missions_without_mutation() -> None:
    temp_dir = runtime_dir("console-e2e-daily-workspace")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    first = console.ask(
        "Analyze the controlled daily release evidence and compare the strongest signal.",
        session_id="sess-e2e-daily-one",
        mission_id="mission-e2e-daily-one",
    )
    second = console.ask(
        "Analyze the pilot evidence for tomorrow.",
        session_id="sess-e2e-daily-two",
        mission_id="mission-e2e-daily-two",
    )
    assert first.experience_record is not None
    assert first.post_task_reflection is not None
    assert second.experience_record is not None
    EvolutionLabService(database_path=str(evolution_db)).create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id=first.experience_record.experience_id,
            mission_id="mission-e2e-daily-one",
            workflow_profile=first.experience_record.workflow_profile,
            outcome_status=first.experience_record.outcome_status,
            learning_candidate=first.post_task_reflection.learning_candidate,
            recommendation=first.post_task_reflection.recommendation,
            evidence_refs=list(first.post_task_reflection.evidence_refs),
            proposed_tests=list(first.post_task_reflection.proposed_tests),
            rollback_plan_ref=first.post_task_reflection.rollback_plan_ref,
        )
    )
    before = {
        memory_db: memory_db.read_bytes(),
        evolution_db: evolution_db.read_bytes(),
    }
    args = build_parser().parse_args(
        [
            "daily-workspace",
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
        ]
    )

    rendered = run_daily_workspace_command(args)[0]

    assert "daily_operator_workspace=read_only" in rendered
    assert "mission_count=2" in rendered
    assert "mission_id=mission-e2e-daily-one" in rendered
    assert "mission_id=mission-e2e-daily-two" in rendered
    assert "pending_review_count=1" in rendered
    assert "next_operator_decision=review_evolution_proposal:" in rendered
    assert "autonomous_resume_allowed=False" in rendered
    assert "autonomous_scheduling_allowed=False" in rendered
    assert memory_db.read_bytes() == before[memory_db]
    assert evolution_db.read_bytes() == before[evolution_db]


def test_console_operator_route_matrix_covers_promoted_journeys() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-routes"))
    scenarios = [
        OperatorScenario(
            name="controlled_plan",
            prompt="Plan the internal pilot rollout.",
            session_id="sess-e2e-plan",
            mission_id="mission-e2e-plan",
            expected_decision="allow_with_conditions",
            expected_route="operational_readiness",
            expected_workflow_profile="operational_readiness_workflow",
            expected_operation_status="completed",
        ),
        OperatorScenario(
            name="analysis_guided_review",
            prompt="Analyze the pilot data and compare the strongest signal.",
            session_id="sess-e2e-analysis",
            mission_id="mission-e2e-analysis",
            expected_decision="allow",
            expected_route="analysis",
            expected_workflow_profile="structured_analysis_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="decision_risk_review",
            prompt=(
                "Compare the decision risk of shipping today versus delaying the "
                "pilot by one week."
            ),
            session_id="sess-e2e-risk",
            mission_id="mission-e2e-risk",
            expected_decision="defer_for_validation",
            expected_route="decision_risk",
            expected_workflow_profile="decision_risk_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="governance_boundary_review",
            prompt=(
                "Review the governance boundary for the pilot and identify which "
                "approval is required."
            ),
            session_id="sess-e2e-governance",
            mission_id="mission-e2e-governance",
            expected_decision="defer_for_validation",
            expected_route="governance",
            expected_workflow_profile="governance_boundary_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="software_shadow_review",
            prompt="Analyze the Python service API rollout and compare the safest change.",
            session_id="sess-e2e-software",
            mission_id="mission-e2e-software",
            expected_decision="allow_with_conditions",
            expected_route="software_development",
            expected_workflow_profile="software_change_workflow",
            expected_operation_status=None,
        ),
        OperatorScenario(
            name="guardrail_block",
            prompt="Delete all pilot records now.",
            session_id="sess-e2e-guardrail",
            mission_id=None,
            expected_decision="block",
            expected_route=None,
            expected_workflow_profile=None,
            expected_operation_status=None,
        ),
    ]

    for scenario in scenarios:
        response = console.ask(
            scenario.prompt,
            session_id=scenario.session_id,
            mission_id=scenario.mission_id,
        )
        audit = audit_response(console, response.request_id)

        assert response.request_id == audit.request_id
        assert response.governance_decision.decision.value == scenario.expected_decision
        assert audit.governance_decision == scenario.expected_decision
        assert audit.operation_status == scenario.expected_operation_status
        assert_core_trace_invariants(audit)
        if scenario.expected_decision in {"allow", "allow_with_conditions"}:
            assert audit.capability_effectiveness == "effective"
            assert audit.handoff_adapter_status in {"healthy", "contained"}
            assert audit.expanded_eval_status in {
                "candidate_ready",
                "baseline_expanding",
            }
        elif scenario.expected_decision == "defer_for_validation":
            assert audit.capability_effectiveness == "insufficient"
            assert audit.handoff_adapter_status == "attention_required"
            assert audit.expanded_eval_status == "attention_required"
            assert audit.promotion_readiness == "blocked"

        if scenario.expected_route is not None:
            assert response.deliberative_plan.primary_route == scenario.expected_route
            assert audit.primary_route == scenario.expected_route
            assert (
                response.deliberative_plan.route_workflow_profile
                == scenario.expected_workflow_profile
            )
            if scenario.expected_operation_status == "completed":
                assert audit.workflow_domain_route == scenario.expected_route
                assert audit.workflow_profile == scenario.expected_workflow_profile
            else:
                assert audit.workflow_domain_route is None
                assert audit.workflow_profile is None
        else:
            assert audit.workflow_domain_route is None
            assert audit.workflow_profile is None


def test_console_operator_flow_reuses_mission_memory_and_emits_memory_maintenance() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-memory"))
    session_id = "sess-e2e-memory"
    mission_id = "mission-e2e-memory"

    console.ask(
        "Plan the internal pilot rollout.",
        session_id=session_id,
        mission_id=mission_id,
    )
    followup = console.ask(
        (
            "Plan the next pilot checkpoint and preserve the previous "
            "recommendation before concluding."
        ),
        session_id=session_id,
        mission_id=mission_id,
    )
    audit = audit_response(console, followup.request_id)

    assert followup.deliberative_plan.primary_route == "operational_readiness"
    assert followup.deliberative_plan.continuity_action == "continuar"
    assert_core_trace_invariants(audit)
    assert audit.continuity_action == "continuar"
    assert audit.continuity_source == "active_mission"
    assert audit.memory_causality_status == "causal_guidance"
    assert audit.semantic_memory_source == "active_mission"
    assert audit.procedural_memory_source == "active_mission"
    assert audit.memory_maintenance_status in {
        "cross_session_recall_active",
        "compaction_active",
    }
    assert audit.memory_maintenance_effectiveness == "effective"
    assert audit.context_compaction_status in {
        "compressed_live_context",
        "seeded_live_context",
    }
    assert audit.cross_session_recall_status == "active"


def test_console_mission_memory_reaches_human_lifecycle_review_without_mutation() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-memory-review"))
    mission_id = "mission-e2e-memory-review"
    console.ask(
        "Plan a bounded Python service rollout with reversible checkpoints.",
        session_id="sess-e2e-memory-review",
        mission_id=mission_id,
    )
    console.ask(
        "Plan the next Python rollout checkpoint and preserve prior evidence.",
        session_id="sess-e2e-memory-review",
        mission_id=mission_id,
    )
    console.ask(
        "Continue the Python rollout plan using the prior checkpoint.",
        session_id="sess-e2e-memory-review",
        mission_id=mission_id,
    )
    memory_service = console.orchestrator.memory_service
    source_summary = memory_service.repository.summarize_memory_corpus()
    queue = memory_service.list_memory_lifecycle_review_queue(limit=20)
    candidate = next(
        item for item in queue if item.maintenance_action == "consolidate"
    )
    assessment = GovernanceService().assess_memory_lifecycle_review(
        candidate,
        decision_action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["trace://e2e-memory-review/001"],
        rollback_plan_ref=candidate.rollback_plan_ref,
    )

    decision = memory_service.record_memory_lifecycle_review_decision(
        candidate_id=candidate.candidate_id,
        decision_action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["trace://e2e-memory-review/001"],
        rollback_plan_ref=candidate.rollback_plan_ref,
        review_notes=["operator approved review disposition only"],
        governance_assessment=assessment,
    )

    assert decision.review_status == "approved"
    assert decision.execution_authorized is False
    assert memory_service.repository.summarize_memory_corpus() == source_summary
    mission_state = memory_service.get_mission_state(mission_id)
    assert mission_state is not None
    assert mission_state.mission_status.value == "active"


def test_console_operator_battery_keeps_promoted_contracts_coherent_together() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-e2e-battery"))
    scenario_matrix = [
        (
            "Plan the internal pilot rollout.",
            "sess-battery-main",
            "mission-battery-main",
        ),
        (
            "Analyze the pilot data and compare the strongest signal.",
            "sess-battery-analysis",
            "mission-battery-analysis",
        ),
        (
            "Review the governance boundary for the pilot and identify which approval is required.",
            "sess-battery-governance",
            "mission-battery-governance",
        ),
        (
            "Analyze the Python service API rollout and compare the safest change.",
            "sess-battery-software",
            "mission-battery-software",
        ),
    ]

    audits: list[FlowAudit] = []
    response_routes: set[str] = set()
    for prompt, session_id, mission_id in scenario_matrix:
        response = console.ask(prompt, session_id=session_id, mission_id=mission_id)
        response_routes.add(response.deliberative_plan.primary_route or "none")
        audits.append(audit_response(console, response.request_id))

    assert {
        "operational_readiness",
        "analysis",
        "governance",
        "software_development",
    } <= response_routes
    assert all(audit.request_identity_status == "healthy" for audit in audits)
    assert all(audit.capability_decision_status == "healthy" for audit in audits)
    assert all(
        audit.capability_effectiveness in {"effective", "insufficient"}
        for audit in audits
    )
    assert all(
        audit.handoff_adapter_status in {"healthy", "contained", "attention_required"}
        for audit in audits
    )
    assert any(audit.operation_status == "completed" for audit in audits)
    assert any(audit.memory_maintenance_effectiveness == "effective" for audit in audits)
    assert any(
        audit.expanded_eval_status in {"candidate_ready", "baseline_expanding"}
        for audit in audits
    )
    assert any(
        audit.mind_domain_specialist_effectiveness == "effective" for audit in audits
    )
    assert any(audit.continuity_source == "fresh_request" for audit in audits)
    assert any(audit.experiment_lane_status == "attention_required" for audit in audits)


def test_console_skill_evolution_correlates_governed_chain_end_to_end() -> None:
    temp_dir = runtime_dir("console-e2e-skill-evolution")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    memory_service = MemoryService(
        database_url=f"sqlite:///{memory_db.as_posix()}"
    )
    for index in (1, 2):
        memory_service.record_experience_reflection(
            experience=ExperienceRecordContract(
                experience_id=f"experience://console-skill/{index}",
                mission_id=f"mission-console-skill-{index}",
                workflow_profile="software_change_workflow",
                route="software_development",
                primary_domain_driver="software_engineering",
                outcome_status="completed",
                evidence_refs=[f"trace://console-skill/{index}"],
                timestamp=f"2026-07-16T14:00:0{index}Z",
            ),
            reflection=PostTaskReflectionContract(
                reflection_id=f"reflection://console-skill/{index}",
                experience_id=f"experience://console-skill/{index}",
                reflection_status="candidate",
                learning_candidate="verify bounded release evidence",
                recommendation="review recurring verification before reuse",
                evidence_refs=[f"trace://console-skill/{index}"],
                timestamp=f"2026-07-16T14:01:0{index}Z",
            ),
        )
    pattern_report = memory_service.build_recurring_pattern_report(
        generated_at="2026-07-16T15:00:00Z"
    )
    candidate = SkillCandidateContract(
        skill_candidate_id="skill-candidate://console-release/1.0.0",
        skill_id="skill://console-release",
        skill_name="console release evidence",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify release evidence"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["trace://console-skill/1", "trace://console-skill/2"],
        source_pattern_refs=[pattern_report.patterns[0].pattern_id],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run console skill sandbox tests"],
        rollback_plan_ref="rollback://skill/console-release/1.0.0",
        timestamp="2026-07-16T15:01:00Z",
    )
    candidate = memory_service.record_skill_candidate(candidate).candidate
    evolution_service = EvolutionLabService(database_path=str(evolution_db))
    proposal = evolution_service.create_proposal_from_skill_candidate(candidate)
    review = evolution_service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://console-skill/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    evolution_service.evaluate_skill_candidate_in_sandbox(
        candidate=candidate,
        proposal=proposal,
        review_decision=review,
        test_cases={
            "bounded-output": {
                "output_contract_satisfied": True,
                "core_unchanged": True,
            }
        },
        evidence_refs=["eval://console-skill/run-1"],
        generated_at="2026-07-16T15:05:00Z",
    )
    proposal_count_before = len(evolution_service.list_recent_proposals(limit=10))
    args = build_parser().parse_args(
        [
            "skill-evolution",
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
            "--skill-id",
            candidate.skill_id,
        ]
    )

    rendered = run_skill_evolution_command(args)[0]

    assert f"skill_candidate_id={candidate.skill_candidate_id}" in rendered
    assert f"origin_pattern_refs={pattern_report.patterns[0].pattern_id}" in rendered
    assert "occurrence_count=2" in rendered
    assert "workflow_profile=software_change_workflow" in rendered
    assert "route=software_development" in rendered
    assert "domain=software_engineering" in rendered
    assert "risk_level=moderate" in rendered
    assert "version=1.0.0" in rendered
    assert "review_status=sandboxed" in rendered
    assert "sandbox_eval_status=passed_pending_release_gate" in rendered
    assert "proposed_tests=run console skill sandbox tests" in rendered
    assert "rollback_plan_ref=rollback://skill/console-release/1.0.0" in rendered
    assert "next_operator_action=prepare_human_release_review" in rendered
    assert "runtime_activation_allowed=False" in rendered
    assert "promotion_authorized=False" in rendered
    assert memory_service.get_skill_candidate(
        candidate.skill_candidate_id
    ).candidate.activation_status == "inactive"
    assert len(evolution_service.list_recent_proposals(limit=10)) == (
        proposal_count_before
    )

    learning_args = build_parser().parse_args(
        [
            "learning-report",
            "--observability-db",
            str(temp_dir / "observability.db"),
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
        ]
    )
    learning_report = run_longitudinal_learning_report_command(learning_args)[0]

    assert f"capability_id={candidate.skill_id}" in learning_report
    assert f"version_ref={candidate.skill_candidate_id}" in learning_report
    assert "runtime_status=inactive_candidate" in learning_report
    assert "offline_observations=1" in learning_report
    assert "runtime_observations=0" in learning_report
    assert "trend_status=insufficient_evidence" in learning_report
    assert "offline_eval_is_not_longitudinal_runtime_evidence" in learning_report
    assert "promotion_authorized=False" in learning_report
