from dataclasses import dataclass, replace
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
    render_response,
    run_action_confirm_command,
    run_artifact_command,
    run_artifacts_command,
    run_daily_workspace_command,
    run_decision_attribution_command,
    run_longitudinal_learning_report_command,
    run_objective_command,
    run_open_loops_command,
    run_operator_outcomes_command,
    run_resume_loop_command,
    run_skill_evolution_command,
    run_work_item_command,
    run_work_items_command,
    run_workflow_lifecycle_command,
    run_workflow_transition_command,
)
from shared.contracts import (
    ExperienceRecordContract,
    PostTaskReflectionContract,
    SkillCandidateContract,
)
from shared.open_loop_policy import open_loop_ref
from shared.types import RiskLevel
from tests.unit.test_workflow_lifecycle import _activation, _rollback
from tests.unit.test_workflow_variant_eval import _run as _run_workflow_variant_eval


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def ask_with_bounded_autonomy(
    console: JarvisConsole,
    prompt: str,
    **kwargs: object,
):
    """Make operation-producing test intent explicit at the console boundary."""

    kwargs.setdefault("requested_autonomy_level", "bounded_core_action")
    kwargs.setdefault("max_autonomy_level", "bounded_core_action")
    kwargs.setdefault("autonomy_confirmation_mode", "not_required")
    return console.ask(prompt, **kwargs)


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
    first = ask_with_bounded_autonomy(
        console,
        "Analyze the controlled daily release evidence and compare the strongest signal.",
        session_id="sess-e2e-daily-one",
        mission_id="mission-e2e-daily-one",
    )
    second = ask_with_bounded_autonomy(
        console,
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


def test_console_governs_work_item_graph_across_sessions_without_execution() -> None:
    temp_dir = runtime_dir("console-e2e-work-item-graph")
    mission_id = "mission-e2e-work-item-graph"
    foundation_ref = f"work-item://{mission_id}/foundation"
    release_ref = f"work-item://{mission_id}/release"
    first_console = JarvisConsole.build(runtime_dir=temp_dir)
    ask_with_bounded_autonomy(
        first_console,
        "Plan the controlled rollout.",
        session_id="sess-e2e-work-item-one",
        mission_id=mission_id,
    )
    parser = build_parser()
    create_foundation = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-e2e-work-item-one",
            "--action",
            "create",
            "--work-item-ref",
            foundation_ref,
            "--priority",
            "p2",
        ]
    )
    create_release = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-e2e-work-item-one",
            "--action",
            "create",
            "--work-item-ref",
            release_ref,
            "--depends-on",
            foundation_ref,
            "--priority",
            "p0",
        ]
    )

    run_work_item_command(first_console, create_foundation)
    created_release = run_work_item_command(first_console, create_release)[0]
    second_console = JarvisConsole.build(runtime_dir=temp_dir)
    list_args = parser.parse_args(["work-items", "--mission-id", mission_id])
    before_completion = run_work_items_command(second_console, list_args)[0]
    cyclic_update = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-e2e-work-item-two",
            "--action",
            "update",
            "--work-item-ref",
            foundation_ref,
            "--depends-on",
            release_ref,
        ]
    )
    blocked_cycle = run_work_item_command(second_console, cyclic_update)[0]
    premature_complete = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-e2e-work-item-two",
            "--action",
            "complete",
            "--work-item-ref",
            release_ref,
        ]
    )
    blocked_completion = run_work_item_command(
        second_console,
        premature_complete,
    )[0]
    complete_foundation = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-e2e-work-item-two",
            "--action",
            "complete",
            "--work-item-ref",
            foundation_ref,
        ]
    )
    run_work_item_command(second_console, complete_foundation)
    after_completion = run_work_items_command(second_console, list_args)[0]

    assert "priority_level=p0" in created_release
    assert "blocking_state=dependency_blocked" in created_release
    assert f"ordered_work_item_refs={foundation_ref},{release_ref}" in before_completion
    assert f"executable_work_item_refs={foundation_ref}" in before_completion
    assert f"blocked_work_item_refs={release_ref}" in before_completion
    assert "transition_status=blocked" in blocked_cycle
    assert "governance_decision=block" in blocked_cycle
    assert "transition_status=blocked" in blocked_completion
    assert "governance_decision=block" in blocked_completion
    assert f"executable_work_item_refs={release_ref}" in after_completion
    assert "autonomous_execution_allowed=False" in after_completion


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
        response = ask_with_bounded_autonomy(
            console,
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

    ask_with_bounded_autonomy(
        console,
        "Plan the internal pilot rollout.",
        session_id=session_id,
        mission_id=mission_id,
    )
    followup = ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
        "Plan a bounded Python service rollout with reversible checkpoints.",
        session_id="sess-e2e-memory-review",
        mission_id=mission_id,
    )
    ask_with_bounded_autonomy(
        console,
        "Plan the next Python rollout checkpoint and preserve prior evidence.",
        session_id="sess-e2e-memory-review",
        mission_id=mission_id,
    )
    ask_with_bounded_autonomy(
        console,
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
        response = ask_with_bounded_autonomy(
            console,
            prompt,
            session_id=session_id,
            mission_id=mission_id,
        )
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


def test_artifact_lineage_persists_and_rolls_back_across_console_sessions() -> None:
    temp_dir = runtime_dir("console-e2e-artifact-lineage")
    mission_id = "mission-e2e-artifact-lineage"
    work_item_ref = f"work-item://{mission_id}/produce-plan"
    artifact_v1 = f"artifact://{mission_id}/plan/v1"
    artifact_v2 = f"artifact://{mission_id}/plan/v2"
    rollback_ref = f"rollback://{mission_id}/plan/v1"
    parser = build_parser()
    first_console = JarvisConsole.build(runtime_dir=temp_dir)
    ask_with_bounded_autonomy(
        first_console,
        "Plan the controlled rollout.",
        session_id="sess-artifact-lineage-one",
        mission_id=mission_id,
    )
    work_item_args = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-artifact-lineage-one",
            "--action",
            "create",
            "--work-item-ref",
            work_item_ref,
        ]
    )
    run_work_item_command(first_console, work_item_args)
    files_before = sorted(
        path.relative_to(temp_dir).as_posix()
        for path in temp_dir.rglob("*")
        if path.is_file()
    )
    register_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-artifact-lineage-one",
            "--action",
            "register",
            "--artifact-ref",
            artifact_v1,
            "--artifact-version",
            "1",
            "--work-item-ref",
            work_item_ref,
            "--rollback-plan-ref",
            rollback_ref,
        ]
    )
    registered = run_artifact_command(first_console, register_args)[0]

    second_console = JarvisConsole.build(runtime_dir=temp_dir)
    replace_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-artifact-lineage-two",
            "--action",
            "replace",
            "--artifact-ref",
            artifact_v1,
            "--artifact-version",
            "2",
            "--replacement-artifact-ref",
            artifact_v2,
            "--rollback-plan-ref",
            rollback_ref,
        ]
    )
    replaced = run_artifact_command(second_console, replace_args)[0]

    third_console = JarvisConsole.build(runtime_dir=temp_dir)
    rollback_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-artifact-lineage-three",
            "--action",
            "rollback",
            "--artifact-ref",
            artifact_v1,
            "--rollback-plan-ref",
            rollback_ref,
        ]
    )
    rolled_back = run_artifact_command(third_console, rollback_args)[0]
    listed = run_artifacts_command(
        third_console,
        parser.parse_args(["artifacts", "--mission-id", mission_id]),
    )[0]
    mission_state = third_console.get_objective_state(mission_id=mission_id)
    files_after = sorted(
        path.relative_to(temp_dir).as_posix()
        for path in temp_dir.rglob("*")
        if path.is_file()
    )

    assert "transition_status=updated" in registered
    assert f"resulting_artifact_ref={artifact_v2}" in replaced
    assert f"supersedes_artifact_ref={artifact_v1}" in replaced
    assert "transition_status=updated" in rolled_back
    assert "active_artifact_refs=" in listed
    assert artifact_v1 in listed
    assert "rolled_back_artifact_refs=" in listed
    assert artifact_v2 in listed
    assert "external_file_mutation_allowed=False" in listed
    assert mission_state is not None
    status_by_ref = {
        item.artifact_ref: item.artifact_status for item in mission_state.artifact_states
    }
    assert status_by_ref[artifact_v1] == "active"
    assert status_by_ref[artifact_v2] == "rolled_back"
    assert artifact_v1 in mission_state.active_artifact_refs
    assert files_after == files_before


def test_open_loop_resume_is_explicit_governed_and_persistent_across_sessions() -> None:
    temp_dir = runtime_dir("console-e2e-open-loop-resume")
    mission_id = "mission-e2e-open-loop-resume"
    work_item_ref = f"work-item://{mission_id}/validate-next-step"
    parser = build_parser()

    first_console = JarvisConsole.build(runtime_dir=temp_dir)
    ask_with_bounded_autonomy(
        first_console,
        "Plan the next controlled implementation step.",
        session_id="sess-open-loop-one",
        mission_id=mission_id,
    )
    initial_state = first_console.get_objective_state(mission_id=mission_id)
    assert initial_state is not None and initial_state.open_loops
    selected_loop_ref = open_loop_ref(mission_id, initial_state.open_loops[0])
    run_objective_command(
        first_console,
        parser.parse_args(
            [
                "objective",
                "--mission-id",
                mission_id,
                "--session-id",
                "sess-open-loop-one",
                "--action",
                "resume",
            ]
        ),
    )
    run_work_item_command(
        first_console,
        parser.parse_args(
            [
                "work-item",
                "--mission-id",
                mission_id,
                "--session-id",
                "sess-open-loop-one",
                "--action",
                "create",
                "--work-item-ref",
                work_item_ref,
                "--priority",
                "p1",
            ]
        ),
    )

    second_console = JarvisConsole.build(runtime_dir=temp_dir)
    listed_before = run_open_loops_command(
        second_console,
        parser.parse_args(["open-loops", "--mission-id", mission_id]),
    )[0]
    resumed = run_resume_loop_command(
        second_console,
        parser.parse_args(
            [
                "resume-loop",
                "--mission-id",
                mission_id,
                "--open-loop-ref",
                selected_loop_ref,
                "--session-id",
                "sess-open-loop-two",
            ]
        ),
    )[0]

    third_console = JarvisConsole.build(runtime_dir=temp_dir)
    run_work_item_command(
        third_console,
        parser.parse_args(
            [
                "work-item",
                "--mission-id",
                mission_id,
                "--session-id",
                "sess-open-loop-three",
                "--action",
                "complete",
                "--work-item-ref",
                work_item_ref,
            ]
        ),
    )
    listed_after = run_open_loops_command(
        third_console,
        parser.parse_args(["open-loops", "--mission-id", mission_id]),
    )[0]
    final_state = third_console.get_objective_state(mission_id=mission_id)
    events = third_console.orchestrator.observability_service.list_recent_events(
        ObservabilityQuery(mission_id=mission_id, limit=100)
    )
    outcomes = run_operator_outcomes_command(
        parser.parse_args(
            [
                "operator-outcomes",
                "--memory-db",
                str(temp_dir / "memory.db"),
                "--observability-db",
                str(temp_dir / "observability.db"),
                "--period-start",
                "2026-01-01T00:00:00+00:00",
                "--period-end",
                "2030-01-01T00:00:00+00:00",
            ]
        )
    )[0]

    assert selected_loop_ref in listed_before
    assert "registry_status=resume_available" in listed_before
    assert f"selected_work_item_ref={work_item_ref}" in listed_before
    assert "autonomous_resume_allowed=False" in listed_before
    assert "resume_status=resumed" in resumed
    assert "governance_decision=allow_with_conditions" in resumed
    assert f"selected_work_item_ref={work_item_ref}" in resumed
    assert "autonomous_execution_allowed=False" in resumed
    assert "open_loop_resumed" in resumed
    assert "loop_status=resumed" in listed_after
    assert "registry_status=blocked" in listed_after
    assert final_state is not None
    assert final_state.open_loops == []
    assert final_state.open_loop_states[0].open_loop_ref == selected_loop_ref
    assert final_state.open_loop_states[0].loop_status == "resumed"
    assert final_state.next_action_ref is not None
    resume_event_names = {
        event.event_name
        for event in events
        if event.session_id == "sess-open-loop-two"
    }
    assert "open_loop_resumed" in resume_event_names
    assert "operation_dispatched" not in resume_event_names
    assert "operator_outcomes=read_only" in outcomes
    assert "observed_work_item_count=1" in outcomes
    assert "completed_work_item_count=1" in outcomes
    assert "resume_count=1" in outcomes
    assert "time_to_next_action_observation_count=1" in outcomes
    assert "saved_time_claim_status=not_claimed_without_controlled_baseline" in outcomes


def test_decision_attribution_command_reads_completed_runtime_trace_without_mutation() -> None:
    temp_dir = runtime_dir("console-e2e-decision-attribution")
    console = JarvisConsole.build(runtime_dir=temp_dir)
    response = ask_with_bounded_autonomy(
        console,
        "Analyze the bounded implementation evidence and report the next validation.",
        session_id="session-e2e-decision-attribution",
        mission_id="mission-e2e-decision-attribution",
    )
    attribution = response.decision_outcome_attribution
    assert attribution is not None
    memory_db = temp_dir / "memory.db"
    observability_db = temp_dir / "observability.db"
    before = {
        memory_db: memory_db.read_bytes(),
        observability_db: observability_db.read_bytes(),
    }
    events_before = console.orchestrator.observability_service.list_recent_events(
        ObservabilityQuery(
            request_id=str(response.request_id),
            limit=200,
        )
    )

    rendered = run_decision_attribution_command(
        build_parser().parse_args(
            [
                "decision-attribution",
                "--memory-db",
                str(memory_db),
                "--observability-db",
                str(observability_db),
                "--request-id",
                str(response.request_id),
                "--mission-id",
                "mission-e2e-decision-attribution",
                "--workflow-profile",
                str(attribution.workflow_profile),
                "--limit",
                "10",
            ]
        )
    )[0]
    events_after = console.orchestrator.observability_service.list_recent_events(
        ObservabilityQuery(
            request_id=str(response.request_id),
            limit=200,
        )
    )

    assert "decision_attribution=read_only" in rendered
    assert "record_count=1" in rendered
    assert f"request_id={response.request_id}" in rendered
    assert f"attribution_record_id={attribution.attribution_record_id}" in rendered
    assert "causal_effect_proven=False" in rendered
    assert "gain_claim_status=not_established_without_comparator" in rendered
    assert "memory_write_allowed=False" in rendered
    assert "execution_allowed=False" in rendered
    assert "tool_dispatch_allowed=False" in rendered
    assert "promotion_authorized=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered
    assert events_after == events_before
    assert memory_db.read_bytes() == before[memory_db]
    assert observability_db.read_bytes() == before[observability_db]


def test_workflow_lifecycle_console_fails_closed_when_verifier_rejects_tail(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("console-e2e-workflow-lifecycle")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    activation = _activation()
    prepared_calls: list[dict[str, object]] = []

    class VerifiedEvolutionBoundary:
        rejected_transition_ids: set[str] = set()

        def prepare_workflow_lifecycle_transition(self, **kwargs):  # type: ignore[no-untyped-def]
            prepared_calls.append(dict(kwargs))
            if kwargs["action"] == "activate_candidate":
                assert kwargs["current_transition"] is None
                return activation
            current = kwargs["current_transition"]
            assert current == activation
            return _rollback(current)

        def verify_persisted_workflow_lifecycle_transition(
            self,
            transition,
        ):  # type: ignore[no-untyped-def]
            known_action = transition.transition_action in {
                "activate_candidate",
                "rollback_to_baseline",
            }
            return (
                transition.transition_id not in self.rejected_transition_ids
                and known_action
            )

    evolution_boundary = VerifiedEvolutionBoundary()
    monkeypatch.setattr(
        "apps.jarvis_console.cli._evolution_service_from_args",
        lambda args: evolution_boundary,
    )
    common_args = [
        "--memory-db",
        str(memory_db),
        "--evolution-db",
        str(evolution_db),
        "--workflow-profile",
        activation.workflow_profile,
        "--route",
        activation.route,
        "--proposal-id",
        activation.evolution_proposal_id,
        "--workflow-eval-run-id",
        activation.workflow_eval_run_id,
        "--operator-ref",
        activation.operator_ref,
        "--completed-test-ref",
        activation.completed_test_refs[0],
        "--completed-external-gate",
        "standard_engineering_gate",
        "--completed-external-gate",
        "release_gate_before_promotion",
    ]
    activation_result = run_workflow_transition_command(
        build_parser().parse_args(
            [
                "workflow-transition",
                *common_args,
                "--action",
                "activate_candidate",
                "--human-authorization-ref",
                activation.human_authorization_ref,
                "--evidence-ref",
                "evidence://workflow/software-change/activation/1",
            ]
        )
    )

    assert isinstance(activation_result, list)
    assert "workflow_transition_status=recorded" in activation_result[0]
    assert "release_bundle_verified=True" in activation_result[0]
    assert "governance_status=approved" in activation_result[0]
    assert "transition_recorded=True" in activation_result[0]
    assert "active_registry_write_allowed=False" in activation_result[0]
    assert "runtime_execution_allowed=False" in activation_result[0]
    assert "automatic_promotion_allowed=False" in activation_result[0]

    active_view = run_workflow_lifecycle_command(
        build_parser().parse_args(
            [
                "workflow-lifecycle",
                "--memory-db",
                str(memory_db),
                "--evolution-db",
                str(evolution_db),
                "--workflow-profile",
                activation.workflow_profile,
                "--route",
                activation.route,
            ]
        )
    )[0]
    assert "workflow_lifecycle_view=read_only" in active_view
    assert "active_transition_status=found" in active_view
    assert "active_transition_action=activate_candidate" in active_view
    assert "active_revision=1" in active_view
    assert "history_count=1" in active_view

    evolution_boundary.rejected_transition_ids.add(activation.transition_id)
    rejected_genesis_view = run_workflow_lifecycle_command(
        build_parser().parse_args(
            [
                "workflow-lifecycle",
                "--memory-db",
                str(memory_db),
                "--evolution-db",
                str(evolution_db),
                "--workflow-profile",
                activation.workflow_profile,
                "--route",
                activation.route,
            ]
        )
    )[0]
    assert "active_transition_status=unavailable_unverified_tail" in (
        rejected_genesis_view
    )
    assert "integrity_attention_required=True" in rejected_genesis_view
    assert "integrity_reasons=workflow_lifecycle_persisted_chain_rejected" in (
        rejected_genesis_view
    )
    assert "history_count=0" in rejected_genesis_view
    evolution_boundary.rejected_transition_ids.clear()

    rollback = _rollback(activation)
    rollback_result = run_workflow_transition_command(
        build_parser().parse_args(
            [
                "workflow-transition",
                *common_args,
                "--action",
                "rollback_to_baseline",
                "--human-authorization-ref",
                rollback.human_authorization_ref,
                "--evidence-ref",
                "evidence://workflow/software-change/rollback/1",
                "--failure-ref",
                rollback.failure_refs[0],
            ]
        )
    )

    assert isinstance(rollback_result, list)
    assert "workflow_transition_status=recorded" in rollback_result[0]
    assert "transition_action=rollback_to_baseline" in rollback_result[0]
    assert "transition_status=baseline_restored" in rollback_result[0]
    assert "revision=2" in rollback_result[0]
    assert "automatic_rollback_allowed=False" in rollback_result[0]

    rolled_back_view = run_workflow_lifecycle_command(
        build_parser().parse_args(
            [
                "workflow-lifecycle",
                "--memory-db",
                str(memory_db),
                "--evolution-db",
                str(evolution_db),
                "--workflow-profile",
                activation.workflow_profile,
                "--route",
                activation.route,
            ]
        )
    )[0]
    assert "active_transition_action=rollback_to_baseline" in rolled_back_view
    assert "active_transition_status=baseline_restored" in rolled_back_view
    assert "active_revision=2" in rolled_back_view
    assert "history_count=2" in rolled_back_view
    assert prepared_calls[0]["completed_external_gates"] == [
        "standard_engineering_gate",
        "release_gate_before_promotion",
    ]
    assert prepared_calls[1]["failure_refs"] == rollback.failure_refs

    evolution_boundary.rejected_transition_ids.add(rollback.transition_id)
    unverified_view = run_workflow_lifecycle_command(
        build_parser().parse_args(
            [
                "workflow-lifecycle",
                "--memory-db",
                str(memory_db),
                "--evolution-db",
                str(evolution_db),
                "--workflow-profile",
                activation.workflow_profile,
                "--route",
                activation.route,
            ]
        )
    )[0]
    assert "active_transition_status=unavailable_unverified_tail" in unverified_view
    assert "integrity_attention_required=True" in unverified_view
    assert "integrity_reasons=workflow_lifecycle_persisted_chain_rejected" in (
        unverified_view
    )
    assert "history_count=1" in unverified_view
    assert activation.transition_id in unverified_view
    assert rollback.transition_id not in unverified_view


def test_workflow_transition_console_does_not_record_governance_blocked_candidate(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("console-workflow-lifecycle-governance-blocked")
    memory_db = temp_dir / "memory.db"
    transition = replace(
        _activation(),
        human_authorization_ref="invalid-unbounded-human-authorization",
    )

    class StructurallyUntrustedEvolutionBoundary:
        def prepare_workflow_lifecycle_transition(self, **_kwargs):  # type: ignore[no-untyped-def]
            return transition

        @staticmethod
        def verify_persisted_workflow_lifecycle_transition(
            _transition,
        ):  # type: ignore[no-untyped-def]
            return True

    monkeypatch.setattr(
        "apps.jarvis_console.cli._evolution_service_from_args",
        lambda args: StructurallyUntrustedEvolutionBoundary(),
    )
    result = run_workflow_transition_command(
        build_parser().parse_args(
            [
                "workflow-transition",
                "--memory-db",
                str(memory_db),
                "--evolution-db",
                str(temp_dir / "evolution.db"),
                "--workflow-profile",
                transition.workflow_profile,
                "--route",
                transition.route,
                "--action",
                "activate_candidate",
                "--proposal-id",
                transition.evolution_proposal_id,
                "--workflow-eval-run-id",
                transition.workflow_eval_run_id,
                "--human-authorization-ref",
                transition.human_authorization_ref,
                "--evidence-ref",
                "evidence://workflow/governance-blocked/1",
                "--completed-test-ref",
                transition.completed_test_refs[0],
                "--completed-external-gate",
                "standard_engineering_gate",
                "--completed-external-gate",
                "release_gate_before_promotion",
            ]
        )
    )

    assert not isinstance(result, list)
    assert result.status == "failed"
    assert result.exit_code == 3
    assert "workflow_transition_status=governance_blocked" in result.outputs[0]
    assert "transition_recorded=False" in result.outputs[0]
    assert "governance_status=blocked" in result.outputs[0]
    assert "human_authorization_ref must be typed" in result.outputs[0]
    assert (
        MemoryService(
            database_url=f"sqlite:///{memory_db.as_posix()}",
            workflow_lifecycle_transition_verifier=lambda _candidate: True,
        ).get_active_workflow_lifecycle(
            workflow_profile=transition.workflow_profile,
            route=transition.route,
        )
        is None
    )


def test_workflow_lifecycle_console_uses_real_release_bundle_in_runtime_and_rollback() -> None:
    temp_dir = runtime_dir("console-e2e-workflow-lifecycle-real")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    baseline, candidate, _registry, evolution, _pack, eval_run = (
        _run_workflow_variant_eval(
            temp_dir,
            run_id="workflow-variant-eval://console-real/1",
        )
    )
    proposal = evolution.create_proposal_from_workflow_candidate(candidate)
    review = evolution.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://console/workflow-release-manager",
        evidence_refs=["evidence://console/workflow/review/1"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    common_args = [
        "--memory-db",
        str(memory_db),
        "--evolution-db",
        str(evolution_db),
        "--workflow-profile",
        candidate.workflow_profile,
        "--route",
        candidate.route,
        "--proposal-id",
        str(proposal.evolution_proposal_id),
        "--workflow-eval-run-id",
        eval_run.run_id,
        "--operator-ref",
        "operator://console/workflow-release-manager",
        "--completed-test-ref",
        candidate.proposed_tests[0],
        "--completed-external-gate",
        "standard_engineering_gate",
        "--completed-external-gate",
        "release_gate_before_promotion",
    ]

    activation_output = run_workflow_transition_command(
        build_parser().parse_args(
            [
                "workflow-transition",
                *common_args,
                "--action",
                "activate_candidate",
                "--human-authorization-ref",
                "human-authorization://console/workflow/activate/1",
                "--evidence-ref",
                "evidence://console/workflow/activation/1",
            ]
        )
    )

    assert isinstance(activation_output, list)
    assert "workflow_transition_status=recorded" in activation_output[0]
    assert "release_bundle_verified=True" in activation_output[0]
    assert f"review_decision_id={review.review_decision_id}" in activation_output[0]
    assert "release_checklist_id=none" not in activation_output[0]
    assert "promotion_gate_id=none" not in activation_output[0]
    assert "rollback_plan_id=none" not in activation_output[0]
    assert "governance_policy_refs=policy://workflow-lifecycle/" in (
        activation_output[0]
    )
    memory = MemoryService(
        database_url=f"sqlite:///{memory_db.as_posix()}",
        workflow_lifecycle_transition_verifier=(
            evolution.verify_persisted_workflow_lifecycle_transition
        ),
    )
    activation = memory.get_active_workflow_lifecycle(
        workflow_profile=candidate.workflow_profile,
        route=candidate.route,
    )
    assert activation is not None
    assert activation.transition_status == "active_promoted"
    assert activation.active_version_ref == candidate.workflow_version_id
    assert evolution.get_workflow_lifecycle_release_bundle(
        activation.transition_id
    ) is not None
    assert evolution.verify_persisted_workflow_lifecycle_transition(activation)

    console = JarvisConsole.build(runtime_dir=temp_dir)
    promoted_response = console.ask(
        "Analyze the Python service change and preserve bounded release evidence.",
        session_id="session-console-real-workflow-activation",
        mission_id="mission-console-real-workflow-activation",
    )
    promoted_binding = promoted_response.deliberative_plan.workflow_lifecycle_transition
    assert promoted_binding == activation
    assert promoted_response.deliberative_plan.primary_route == candidate.route
    assert "record verified release evidence" in (
        promoted_response.deliberative_plan.route_workflow_steps
    )
    assert candidate.success_criteria[-1] in (
        promoted_response.deliberative_plan.success_criteria
    )

    rollback_output = run_workflow_transition_command(
        build_parser().parse_args(
            [
                "workflow-transition",
                *common_args,
                "--action",
                "rollback_to_baseline",
                "--human-authorization-ref",
                "human-authorization://console/workflow/rollback/1",
                "--evidence-ref",
                "evidence://console/workflow/rollback/1",
                "--failure-ref",
                "failure://console/workflow/runtime-regression/1",
            ]
        )
    )

    assert isinstance(rollback_output, list)
    assert "workflow_transition_status=recorded" in rollback_output[0]
    assert "transition_status=baseline_restored" in rollback_output[0]
    rolled_back = memory.get_active_workflow_lifecycle(
        workflow_profile=candidate.workflow_profile,
        route=candidate.route,
    )
    assert rolled_back is not None
    assert rolled_back.transition_status == "baseline_restored"
    assert rolled_back.active_version_ref == baseline.workflow_version_id
    assert rolled_back.previous_transition_id == activation.transition_id
    assert evolution.verify_persisted_workflow_lifecycle_transition(rolled_back)

    rolled_back_response = JarvisConsole.build(runtime_dir=temp_dir).ask(
        "Analyze the Python service change after the explicit rollback.",
        session_id="session-console-real-workflow-rollback",
        mission_id="mission-console-real-workflow-rollback",
    )
    rollback_binding = (
        rolled_back_response.deliberative_plan.workflow_lifecycle_transition
    )
    assert rollback_binding == rolled_back
    assert rollback_binding.active_version_ref == baseline.workflow_version_id
    assert "record verified release evidence" not in (
        rolled_back_response.deliberative_plan.route_workflow_steps
    )


def test_console_action_confirmation_survives_restart_and_blocks_replay() -> None:
    temp_dir = runtime_dir("console-e2e-action-confirmation")
    prompt = "Plan the controlled rollout."
    request_context = {
        "session_id": "session-console-e2e-confirmation",
        "mission_id": "mission-console-e2e-confirmation",
        "operator_identity_ref": "operator://console/e2e-confirmation",
        "requested_autonomy_level": "supervised_external_action",
        "max_autonomy_level": "supervised_external_action",
        "autonomy_confirmation_mode": "explicit",
    }

    first = JarvisConsole.build(runtime_dir=temp_dir).ask(
        prompt,
        **request_context,
    )

    challenge = first.action_confirmation_challenge
    assert challenge is not None
    assert first.action_confirmation_claim is None
    assert first.operation_dispatch is None
    assert first.operation_result is None
    assert first.artifact_results == []
    first_event_names = [event.event_name for event in first.events]
    assert "action_confirmation_challenged" in first_event_names
    assert "action_confirmation_blocked" in first_event_names
    assert "operation_dispatched" not in first_event_names
    assert "operation_completed" not in first_event_names
    rendered_challenge = render_response(first, debug=False)
    assert f"challenge_id={challenge.challenge_id}" in rendered_challenge
    assert f"origin_request_id={challenge.origin_request_id}" in rendered_challenge
    assert f"action_fingerprint={challenge.action_fingerprint}" in rendered_challenge
    assert f"expires_at={challenge.expires_at}" in rendered_challenge

    confirmation_console = JarvisConsole.build(runtime_dir=temp_dir)
    confirmation_output = run_action_confirm_command(
        confirmation_console,
        build_parser().parse_args(
            [
                "action-confirm",
                "--challenge-id",
                challenge.challenge_id,
                "--action-fingerprint",
                challenge.action_fingerprint,
                "--operator-identity-ref",
                request_context["operator_identity_ref"],
            ]
        ),
    )[0]
    receipt_id = next(
        line.partition("=")[2]
        for line in confirmation_output.splitlines()
        if line.startswith("receipt_id=")
    )
    assert "confirmation_evidence_only=True" in confirmation_output
    assert "execution_allowed=False" in confirmation_output
    assert "tool_dispatch_allowed=False" in confirmation_output
    assert (temp_dir / "governance.db").is_file()

    executed = JarvisConsole.build(runtime_dir=temp_dir).ask(
        prompt,
        **request_context,
        action_confirmation_receipt_id=receipt_id,
        action_confirmation_origin_request_id=str(challenge.origin_request_id),
    )

    assert executed.action_confirmation_challenge is None
    assert executed.action_confirmation_claim is not None
    assert executed.operation_dispatch is not None
    assert executed.operation_result is not None
    assert executed.operation_result.status.value == "completed"
    assert len(executed.operation_result.artifacts) == 1
    assert len(executed.artifact_results) == 1
    executed_event_names = [event.event_name for event in executed.events]
    assert "action_confirmation_claimed" in executed_event_names
    assert "operation_dispatched" in executed_event_names
    assert "operation_completed" in executed_event_names
    artifact_paths = list((temp_dir / "artifacts").glob("*.md"))
    assert len(artifact_paths) == 1

    replay = JarvisConsole.build(runtime_dir=temp_dir).ask(
        prompt,
        **request_context,
        action_confirmation_receipt_id=receipt_id,
        action_confirmation_origin_request_id=str(challenge.origin_request_id),
    )

    assert replay.action_confirmation_challenge is not None
    assert replay.action_confirmation_claim is None
    assert replay.operation_dispatch is None
    assert replay.operation_result is None
    assert replay.artifact_results == []
    replay_event_names = [event.event_name for event in replay.events]
    assert "action_confirmation_blocked" in replay_event_names
    assert "operation_dispatched" not in replay_event_names
    assert "operation_completed" not in replay_event_names
    assert len(list((temp_dir / "artifacts").glob("*.md"))) == 1
