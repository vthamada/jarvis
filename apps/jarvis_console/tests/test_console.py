from pathlib import Path
from tempfile import gettempdir
from types import SimpleNamespace
from uuid import uuid4

from evolution_lab.service import (
    EvolutionLabService,
    PostTaskReflectionInput,
    TechnologyAbsorptionInput,
)
from memory_service.service import MemoryService

from apps.jarvis_console.cli import (
    JarvisConsole,
    LongHorizonGoalStrategyResult,
    build_parser,
    render_artifacts_state,
    render_evolution_review_queue,
    render_experience_reflections,
    render_goal_strategy,
    render_memory_lifecycle_review_queue,
    render_mission_cycle,
    render_objective_state,
    render_operator_dashboard,
    render_readiness_dashboard,
    render_response,
    render_skill_evolution_operator_view,
    render_work_items_state,
    run_artifact_command,
    run_artifacts_command,
    run_chat_command,
    run_evolution_review_command,
    run_evolution_review_queue_command,
    run_experience_reflections_command,
    run_goal_strategy_command,
    run_memory_lifecycle_review_command,
    run_memory_lifecycle_review_queue_command,
    run_mission_cycle_command,
    run_mission_feedback_command,
    run_mission_workflow_command,
    run_objective_command,
    run_objectives_command,
    run_operator_dashboard_command,
    run_procedural_playbooks_command,
    run_progress_report_command,
    run_readiness_dashboard_command,
    run_skill_evolution_command,
    run_technology_candidates_command,
    run_work_item_command,
    run_work_items_command,
)
from shared.contracts import (
    ExperienceRecordContract,
    MissionStateContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    RegressionReadinessReportContract,
    ReviewedLearningGuidanceContract,
    SkillEvolutionOperatorViewContract,
)
from shared.types import MissionId, MissionStatus


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_console_readiness_dashboard_is_read_only_and_does_not_run_gate() -> None:
    args = build_parser().parse_args(["readiness-dashboard"])

    outputs = run_readiness_dashboard_command(args)

    assert "regression_readiness=read_only" in outputs[0]
    assert "gate_mode=not_run" in outputs[0]
    assert "test_status=not_run" in outputs[0]
    assert "document_status=healthy" in outputs[0]
    assert "autonomous_release_allowed=False" in outputs[0]


def test_console_readiness_renderer_surfaces_drift_and_blockers() -> None:
    rendered = render_readiness_dashboard(
        RegressionReadinessReportContract(
            report_id="regression-readiness://console-test",
            status="blocked",
            overall_score=45,
            capability_counts={
                "ready": 1,
                "partial": 1,
                "attention_required": 0,
                "missing": 1,
                "deferred": 1,
            },
            capability_results=[],
            gate_mode="standard",
            gate_status="failed",
            test_status="failed",
            document_status="attention_required",
            backlog_status="status_drift",
            status_drift=["master_map_ready_mismatch:MB-174"],
            blockers=["engineering_gate_failed"],
            warnings=[],
            evidence_refs=[],
            generated_at="2026-07-16T12:00:00Z",
            next_ready_item="MB-174",
        )
    )

    assert "status=blocked" in rendered
    assert "status_drift=master_map_ready_mismatch:MB-174" in rendered
    assert "blockers=engineering_gate_failed" in rendered
    assert "capability_missing=1" in rendered


def test_console_ask_returns_orchestrated_response() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-ask"))
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console",
        mission_id="mission-console",
    )
    rendered = render_response(response, debug=True)

    assert response.intent == "planning"
    assert "Leitura do objetivo" in response.response_text
    assert "request_id=" in rendered
    assert "decision=" in rendered
    assert "semantic_memory_anchor_refs=" in rendered
    assert "semantic_memory_evidence_refs=" in rendered
    assert "semantic_memory_use_reason=" in rendered
    assert "semantic_memory_non_use_reason=" in rendered
    assert response.operation_dispatch is not None
    assert response.operation_dispatch.surface_id == "surface://jarvis_console"
    assert response.operation_dispatch.surface_kind == "console"
    assert response.operation_dispatch.surface_session_id == "sess-console"
    assert response.operation_dispatch.surface_continuity_status == "single_surface"


def test_console_accepts_operator_surface_identity_overrides() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-surface"))
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-surface",
        mission_id="mission-console-surface",
        operator_identity_ref="operator://ricardo",
        canonical_user_ref="user://ricardo",
    )

    assert response.operation_dispatch is not None
    assert response.operation_dispatch.operator_identity_ref == "operator://ricardo"
    assert response.operation_dispatch.canonical_user_ref == "user://ricardo"


def test_console_objectives_shows_persisted_project_objective_state() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objectives"))
    mission_id = "mission-console-objectives"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objectives",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(["objectives", "--mission-id", mission_id])

    outputs = run_objectives_command(console, args)

    assert len(outputs) == 1
    assert f"mission_id={mission_id}" in outputs[0]
    assert "project_ref=project:mission:mission-console-objectives" in outputs[0]
    assert "objective_ref=objective:mission:mission-console-objectives" in outputs[0]
    assert "objective_status=completed" in outputs[0]
    assert "next_action_ref=next_action:" in outputs[0]
    event_names = [
        event.event_name
        for event in console.orchestrator.observability_service.list_recent_events()
    ]
    assert "objective_state_inspected" in event_names


def test_console_objectives_handles_missing_mission_without_side_effects() -> None:
    rendered = render_objective_state(None, mission_id="missing-mission")

    assert rendered == "No objective state found for mission_id=missing-mission"


def test_console_goal_strategy_shows_read_only_long_horizon_state() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-goal-strategy"))
    mission_id = "mission-console-goal-strategy"
    work_item_ref = "work-item://mission-console-goal-strategy/validate-plan"
    artifact_ref = "artifact://mission-console-goal-strategy/plan/v1"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-goal-strategy",
        mission_id=mission_id,
    )
    console.transition_work_item(
        mission_id=mission_id,
        work_item_ref=work_item_ref,
        transition="create",
        session_id="sess-console-goal-strategy",
        next_action_ref="next_action:operator-review",
    )
    console.transition_artifact_lifecycle(
        mission_id=mission_id,
        artifact_ref=artifact_ref,
        transition="register",
        session_id="sess-console-goal-strategy",
        artifact_version=1,
    )
    args = build_parser().parse_args(
        [
            "goal-strategy",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-goal-strategy",
        ]
    )

    outputs = run_goal_strategy_command(console, args)

    assert f"mission_id={mission_id}" in outputs[0]
    assert "strategy_status=ready" in outputs[0]
    assert work_item_ref in outputs[0]
    assert artifact_ref in outputs[0]
    assert "next_action_ref=next_action:operator-review" in outputs[0]
    assert "memory_write_mode=read_only" in outputs[0]
    assert "autonomous_scheduling_allowed=False" in outputs[0]
    event_names = [
        event.event_name
        for event in console.orchestrator.observability_service.list_recent_events()
    ]
    assert "long_horizon_goal_strategy_declared" in event_names


def test_console_goal_strategy_handles_missing_mission() -> None:
    rendered = render_goal_strategy(
        LongHorizonGoalStrategyResult(
            mission_id="missing-mission",
            status="missing",
            strategy=None,
        )
    )

    assert rendered == "No goal strategy found for mission_id=missing-mission"


def test_console_technology_candidates_shows_recent_absorption_candidate() -> None:
    temp_dir = runtime_dir("console-technology-candidates")
    evolution_db = temp_dir / "evolution.db"
    service = EvolutionLabService(database_path=str(evolution_db))
    service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://openai-agents-sdk/handoff-adapters",
            technology_name="OpenAI Agents SDK",
            absorption_class="promotable_translation",
            target_gap_refs=["TA-005"],
            hypothesis="Handoff adapters can improve bounded edge tracing.",
            expected_gain="Better trace evidence without replacing the core.",
            evidence_refs=["evidence://comparison/handoff-adapter"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            status="validated",
            requested_core_role="adapter",
            rollback_plan_ref="rollback://sovereign-core/current",
        )
    )
    args = build_parser().parse_args(
        [
            "technology-candidates",
            "--evolution-db",
            str(evolution_db),
            "--limit",
            "3",
        ]
    )

    outputs = run_technology_candidates_command(args)

    assert len(outputs) == 1
    assert "candidate_ref=tech-candidate://openai-agents-sdk/handoff-adapters" in outputs[0]
    assert "technology_name=OpenAI Agents SDK" in outputs[0]
    assert "absorption_decision=manual_promotion_review" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_replacement_allowed=False" in outputs[0]


def test_console_evolution_review_queue_shows_human_review_items() -> None:
    temp_dir = runtime_dir("console-review-queue")
    evolution_db = temp_dir / "evolution.db"
    service = EvolutionLabService(database_path=str(evolution_db))
    service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-review/001",
            mission_id="mission-review",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="bounded review improved workflow reliability",
            recommendation="keep proposal in human review before promotion",
            evidence_refs=["trace://req-review"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )
    args = build_parser().parse_args(
        [
            "evolution-review-queue",
            "--evolution-db",
            str(evolution_db),
            "--limit",
            "5",
        ]
    )

    outputs = run_evolution_review_queue_command(args)

    assert "proposal_type=post_task_reflection_improvement" in outputs[0]
    assert "review_status=needs_review" in outputs[0]
    assert "requires_human_review=True" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "rollback_plan_ref=rollback://workflow/current" in outputs[0]


def test_console_evolution_review_queue_handles_empty_items() -> None:
    assert render_evolution_review_queue([]) == "No evolution review items found."


def test_console_skill_evolution_empty_view_is_explicitly_read_only(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("console-skill-evolution-empty")
    monkeypatch.chdir(temp_dir)
    args = build_parser().parse_args(
        [
            "skill-evolution",
            "--memory-db",
            "memory.db",
            "--evolution-db",
            "evolution.db",
        ]
    )

    rendered = run_skill_evolution_command(args)[0]

    assert "skill_evolution_view=read_only" in rendered
    assert "view_status=empty" in rendered
    assert "candidate_count=0" in rendered
    assert "runtime_activation_allowed=False" in rendered
    assert "promotion_authorized=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered
    assert (temp_dir / "memory.db").exists()
    assert (temp_dir / "evolution.db").exists()


def test_console_skill_evolution_renderer_sanitizes_persisted_values() -> None:
    view = SkillEvolutionOperatorViewContract(
        view_id="skill-evolution-view://safe\nview_status=spoofed",
        view_status="empty",
        pattern_report_id="recurring-pattern-report://safe",
        pattern_report_status="insufficient_evidence",
        pattern_count=0,
        candidate_count=0,
        items=[],
        unregistered_pattern_refs=[],
        blockers=["bounded\rblocker"],
        generated_at="2026-07-16T17:00:00Z",
    )

    rendered = render_skill_evolution_operator_view(view)

    assert "view_id=skill-evolution-view://safe view_status=spoofed" in rendered
    assert "\nview_status=spoofed" not in rendered
    assert "view_blockers=bounded blocker" in rendered


def test_console_evolution_review_approves_with_evidence_and_rollback() -> None:
    temp_dir = runtime_dir("console-review-decision")
    evolution_db = temp_dir / "evolution.db"
    service = EvolutionLabService(database_path=str(evolution_db))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-review-decision/001",
            mission_id="mission-review-decision",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="human review can approve bounded sandbox learning",
            recommendation="approve only with evidence and rollback",
            evidence_refs=["trace://req-review-decision"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )
    args = build_parser().parse_args(
        [
            "evolution-review",
            "--evolution-db",
            str(evolution_db),
            "--proposal-id",
            str(proposal.evolution_proposal_id),
            "--action",
            "approve",
            "--evidence-ref",
            "trace://req-review-decision",
            "--proposed-test",
            "python tools/engineering_gate.py --mode standard",
            "--rollback-plan-ref",
            "rollback://workflow/current",
            "--risk-acceptance",
            "bounded_sandbox_only",
        ]
    )

    outputs = run_evolution_review_command(args)

    assert "decision=approve" in outputs[0]
    assert "review_status=approved" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_mutation_allowed=False" in outputs[0]
    assert "rollback_plan_ref=rollback://workflow/current" in outputs[0]


def test_console_evolution_review_blocks_approval_without_required_evidence() -> None:
    temp_dir = runtime_dir("console-review-decision-blocked")
    evolution_db = temp_dir / "evolution.db"
    service = EvolutionLabService(database_path=str(evolution_db))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-review-decision-blocked/001",
            mission_id="mission-review-decision-blocked",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="approval without evidence should stay in review",
            recommendation="keep pending",
        )
    )
    args = build_parser().parse_args(
        [
            "evolution-review",
            "--evolution-db",
            str(evolution_db),
            "--proposal-id",
            str(proposal.evolution_proposal_id),
            "--action",
            "approve",
        ]
    )

    outputs = run_evolution_review_command(args)

    assert "decision=approve" in outputs[0]
    assert "review_status=needs_review" in outputs[0]
    assert "evidence_required_for_human_approval" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]


def test_console_mission_cycle_shows_operator_learning_loop() -> None:
    temp_dir = runtime_dir("console-mission-cycle")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    mission_id = "mission-console-cycle"
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-cycle",
        mission_id=mission_id,
    )
    assert response.experience_record is not None
    assert response.post_task_reflection is not None
    EvolutionLabService(database_path=str(evolution_db)).create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id=response.experience_record.experience_id,
            mission_id=mission_id,
            workflow_profile=response.experience_record.workflow_profile,
            outcome_status=response.experience_record.outcome_status,
            learning_candidate=response.post_task_reflection.learning_candidate,
            recommendation=response.post_task_reflection.recommendation,
            evidence_refs=list(response.post_task_reflection.evidence_refs),
            proposed_tests=list(response.post_task_reflection.proposed_tests),
            rollback_plan_ref=response.post_task_reflection.rollback_plan_ref,
        )
    )
    args = build_parser().parse_args(
        [
            "mission-cycle",
            "--mission-id",
            mission_id,
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
        ]
    )

    outputs = run_mission_cycle_command(console, args)

    assert "operator_learning_loop=read_only" in outputs[0]
    assert "mission_id=mission-console-cycle" in outputs[0]
    assert "objective_status=completed" in outputs[0]
    assert "route=strategy" in outputs[0]
    assert "plan_summary=" in outputs[0]
    assert "specialist_used=structured_analysis_specialist" in outputs[0]
    assert "experience_id=experience://mission-console-cycle/" in outputs[0]
    assert "reflection_status=candidate" in outputs[0]
    assert "reviewed_learning_influence_status=no_relevant_guidance" in outputs[0]
    assert "reviewed_learning_influence_reason=no_scope_match" in outputs[0]
    assert (
        "reviewed_learning_assisted_eval_status=baseline_no_reviewed_learning"
        in outputs[0]
    )
    assert (
        "reviewed_learning_release_conclusion=no_promotion_without_release_gate"
        in outputs[0]
    )
    assert "review_status=needs_review" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "next_operator_step=review_evolution_proposal" in outputs[0]


def test_console_mission_cycle_handles_empty_records() -> None:
    rendered = render_mission_cycle(
        mission_id="missing-mission",
        mission_state=None,
        records=[],
        review_items=[],
    )

    assert rendered == "No mission cycle found for mission_id=missing-mission"


def test_console_mission_cycle_shows_reviewed_learning_influence() -> None:
    flow_audit = type(
        "FlowAuditStub",
        (),
        {
            "reviewed_learning_influence_status": "applied",
            "reviewed_learning_influence_refs": [
                "reviewed-learning://guidance/001"
            ],
            "reviewed_learning_influence_reason": "workflow_match",
            "reviewed_learning_assisted_eval_status": "reviewed_learning_assisted",
            "reviewed_learning_release_conclusion": (
                "no_promotion_without_release_gate"
            ),
        },
    )()

    rendered = render_mission_cycle(
        mission_id="mission-reviewed-learning",
        mission_state=MissionStateContract(
            mission_id=MissionId("mission-reviewed-learning"),
            mission_goal="Validate reviewed learning guidance",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-17T00:00:00Z",
        ),
        records=[],
        review_items=[],
        flow_audit=flow_audit,
    )

    assert "reviewed_learning_influence_status=applied" in rendered
    assert (
        "reviewed_learning_influence_refs=reviewed-learning://guidance/001"
        in rendered
    )
    assert "reviewed_learning_influence_reason=workflow_match" in rendered
    assert (
        "reviewed_learning_assisted_eval_status=reviewed_learning_assisted"
        in rendered
    )
    assert (
        "reviewed_learning_release_conclusion=no_promotion_without_release_gate"
        in rendered
    )


def test_console_operator_dashboard_shows_daily_state_for_mission() -> None:
    temp_dir = runtime_dir("console-operator-dashboard")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    mission_id = "mission-console-dashboard"
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-dashboard",
        mission_id=mission_id,
    )
    assert response.experience_record is not None
    assert response.post_task_reflection is not None
    EvolutionLabService(database_path=str(evolution_db)).create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id=response.experience_record.experience_id,
            mission_id=mission_id,
            workflow_profile=response.experience_record.workflow_profile,
            outcome_status=response.experience_record.outcome_status,
            learning_candidate=response.post_task_reflection.learning_candidate,
            recommendation=response.post_task_reflection.recommendation,
            evidence_refs=list(response.post_task_reflection.evidence_refs),
            proposed_tests=list(response.post_task_reflection.proposed_tests),
            rollback_plan_ref=response.post_task_reflection.rollback_plan_ref,
        )
    )
    args = build_parser().parse_args(
        [
            "operator-dashboard",
            "--mission-id",
            mission_id,
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
        ]
    )

    outputs = run_operator_dashboard_command(console, args)

    assert "operator_dashboard=read_only" in outputs[0]
    assert "dashboard_scope=mission" in outputs[0]
    assert "mission_id=mission-console-dashboard" in outputs[0]
    assert "objective_status=completed" in outputs[0]
    assert "objective_continuity_status=" in outputs[0]
    assert "next_action_ref=next_action:" in outputs[0]
    assert "next_action_status=" in outputs[0]
    assert "work_item_refs=" in outputs[0]
    assert "work_item_count=" in outputs[0]
    assert "artifact_count=" in outputs[0]
    assert "artifact_continuity_status=" in outputs[0]
    assert "latest_experience_id=experience://mission-console-dashboard/" in outputs[0]
    assert "latest_reflection_status=candidate" in outputs[0]
    assert "pending_review_count=1" in outputs[0]
    assert "pending_review_proposal_ids=evo-proposal-" in outputs[0]
    assert "primary_review_status=needs_review" in outputs[0]
    assert "primary_review_blockers=" in outputs[0]
    assert "primary_review_tests=" in outputs[0]
    assert "primary_review_rollback_plan_ref=" in outputs[0]
    assert "reviewed_learning_influence_status=no_relevant_guidance" in outputs[0]
    assert (
        "reviewed_learning_assisted_eval_status=baseline_no_reviewed_learning"
        in outputs[0]
    )
    assert "operator_usefulness_status=" in outputs[0]
    assert "operator_usefulness_score=" in outputs[0]
    assert "operator_usefulness_signals=" in outputs[0]
    assert "semantic_memory_anchor_refs=" in outputs[0]
    assert "semantic_memory_evidence_refs=" in outputs[0]
    assert "semantic_memory_use_reason=" in outputs[0]
    assert "semantic_memory_non_use_reason=" in outputs[0]
    assert "memory_influence_used_refs=" in outputs[0]
    assert "memory_influence_ignored_refs=" in outputs[0]
    assert "memory_influence_reasons=" in outputs[0]
    assert "memory_influence_evidence_refs=" in outputs[0]
    assert "effective_autonomy_level=" in outputs[0]
    assert "autonomy_ladder_status=" in outputs[0]
    assert "max_autonomy_capability_mode=" in outputs[0]
    assert "autonomy_human_confirmation_required=" in outputs[0]
    assert "autonomy_confirmation_mode=" in outputs[0]
    assert "autonomy_blocked_runtime_actions=" in outputs[0]
    assert "promotion_gate_status=not_applicable" in outputs[0]
    assert "promotion_gate_decision=not_applicable" in outputs[0]
    assert "promotion_gate_release_conclusion=no_promotion_gate_evidence" in outputs[0]
    assert "promotion_gate_promotion_authorized=False" in outputs[0]
    assert "cockpit_status=operator_decision_required" in outputs[0]
    assert "pending_decision_count=" in outputs[0]
    assert "pending_decisions=review_evolution_proposal:" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "next_operator_decision=review_evolution_proposal:" in outputs[0]
    assert "next_operator_step=review_evolution_proposal" in outputs[0]


def test_console_operator_dashboard_consolidates_pending_human_decisions() -> None:
    review_item = SimpleNamespace(
        evolution_proposal_id="proposal-123",
        review_status="needs_review",
        candidate_refs=[],
        blockers=["human_approval_required"],
        proposed_tests=["pytest tests/unit/test_release.py"],
        rollback_plan_ref="rollback://proposal-123",
    )
    flow_audit = SimpleNamespace(
        objective_continuity_status="active",
        artifact_continuity_status="active",
        next_action_status="ready",
        promotion_gate_id="promotion-gate://proposal-123",
        promotion_gate_status="blocked",
        promotion_gate_decision="promotion_blocked",
        promotion_gate_release_conclusion="promotion_blocked_by_release_gate",
        promotion_gate_missing_gates=["release_gate_before_promotion"],
        promotion_gate_blockers=[
            "gate_not_completed:release_gate_before_promotion"
        ],
        promotion_gate_evidence_refs=["evidence://proposal-123"],
        promotion_gate_human_decision_required=True,
        promotion_gate_promotion_authorized=False,
        effective_autonomy_level="confirm_before_action",
        autonomy_human_confirmation_required=True,
        autonomy_confirmation_mode="explicit",
    )

    rendered = render_operator_dashboard(
        mission_id="mission-operator-decisions",
        mission_state=None,
        records=[],
        review_items=[review_item],
        flow_audit=flow_audit,
    )

    assert "primary_review_status=needs_review" in rendered
    assert "promotion_gate_status=blocked" in rendered
    assert "promotion_gate_decision=promotion_blocked" in rendered
    assert "promotion_gate_missing_gates=release_gate_before_promotion" in rendered
    assert "promotion_gate_evidence_refs=evidence://proposal-123" in rendered
    assert "promotion_gate_promotion_authorized=False" in rendered
    assert "cockpit_status=operator_decision_required" in rendered
    assert "pending_decision_count=3" in rendered
    assert "review_evolution_proposal:proposal-123" in rendered
    assert "resolve_promotion_gate_blockers:promotion-gate://proposal-123" in rendered
    assert "confirm_autonomy_action:explicit" in rendered
    assert "next_operator_decision=review_evolution_proposal:proposal-123" in rendered


def test_console_operator_dashboard_handles_empty_global_state() -> None:
    rendered = render_operator_dashboard(
        mission_id=None,
        mission_state=None,
        records=[],
        review_items=[],
    )

    assert "operator_dashboard=read_only" in rendered
    assert "dashboard_scope=global" in rendered
    assert "pending_review_count=0" in rendered
    assert "cockpit_status=idle" in rendered
    assert "pending_decision_count=0" in rendered
    assert "next_operator_step=start_governed_mission" in rendered


def test_console_progress_report_synthesizes_canonical_mission_state() -> None:
    temp_dir = runtime_dir("console-progress-report")
    console = JarvisConsole.build(runtime_dir=temp_dir)
    mission_id = "mission-console-progress-report"
    response = console.ask(
        "Plan and review the controlled release.",
        session_id="sess-console-progress-report",
        mission_id=mission_id,
    )
    assert response.experience_record is not None
    assert response.post_task_reflection is not None
    console.transition_work_item(
        mission_id=mission_id,
        work_item_ref=f"work-item://{mission_id}/review-release",
        transition="create",
        session_id="sess-console-progress-report",
        next_action_ref="next_action:operator-review",
    )
    console.transition_artifact_lifecycle(
        mission_id=mission_id,
        artifact_ref=f"artifact://{mission_id}/release-plan/v1",
        transition="register",
        session_id="sess-console-progress-report",
        artifact_version=1,
    )
    args = build_parser().parse_args(
        [
            "progress-report",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-progress-report",
        ]
    )

    outputs = run_progress_report_command(console, args)

    assert "mission_progress_report=read_only" in outputs[0]
    assert f"mission_id={mission_id}" in outputs[0]
    assert "report_status=needs_operator_decision" in outputs[0]
    assert f"work-item://{mission_id}/review-release" in outputs[0]
    assert f"artifact://{mission_id}/release-plan/v1" in outputs[0]
    assert "learning_refs=experience://" in outputs[0]
    assert "reflection://" in outputs[0]
    assert "pending_decisions=review_learning_candidate" in outputs[0]
    assert "next_action_ref=next_action:operator-review" in outputs[0]
    assert "memory_write_mode=read_only" in outputs[0]
    assert "autonomous_execution_allowed=False" in outputs[0]
    assert "Missao: Plan and review the controlled release." in outputs[0]
    assert "Proxima acao: next_action:operator-review" in outputs[0]


def test_console_mission_workflow_runs_governed_loop_end_to_end() -> None:
    temp_dir = runtime_dir("console-mission-workflow")
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    args = build_parser().parse_args(
        [
            "mission-workflow",
            "Plan the controlled rollout.",
            "--session-id",
            "sess-console-workflow",
            "--mission-id",
            "mission-console-workflow",
            "--evolution-db",
            str(evolution_db),
        ]
    )

    outputs = run_mission_workflow_command(console, args)

    assert "mission_workflow_status=closed_with_human_review_pending" in outputs[0]
    assert "governance_decision=allow_with_conditions" in outputs[0]
    assert "mission_started=mission-console-workflow" in outputs[0]
    assert "plan_status=created" in outputs[0]
    assert "execution_status=completed" in outputs[0]
    assert "experience_recorded=True" in outputs[0]
    assert "post_task_reflection_recorded=True" in outputs[0]
    assert "evolution_proposal_id=evo-proposal-" in outputs[0]
    assert "review_status=needs_review" in outputs[0]
    assert "operator_learning_loop=read_only" in outputs[0]
    assert "next_operator_step=review_evolution_proposal" in outputs[0]


def test_console_mission_feedback_records_learning_and_review_proposal() -> None:
    temp_dir = runtime_dir("console-mission-feedback")
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    mission_id = "mission-console-feedback"
    response = console.ask(
        "Plan the controlled release.",
        session_id="sess-console-feedback",
        mission_id=mission_id,
    )
    assert response.experience_record is not None
    args = build_parser().parse_args(
        [
            "mission-feedback",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-feedback",
            "--experience-id",
            response.experience_record.experience_id,
            "--assessment",
            "correction",
            "--rating",
            "2",
            "--comment",
            "The answer omitted release evidence.",
            "--correction",
            "Require verified evidence before recommending release.",
            "--next-expectation",
            "Show evidence and rollback references.",
            "--evidence-ref",
            "evidence://console-feedback/release",
            "--evolution-db",
            str(evolution_db),
        ]
    )

    outputs = run_mission_feedback_command(console, args)
    stored = console.orchestrator.memory_service.get_experience_reflection(
        response.experience_record.experience_id
    )
    review_items = EvolutionLabService(
        database_path=str(evolution_db)
    ).list_human_review_queue(limit=5)

    assert "operator_feedback_status=recorded" in outputs[0]
    assert "governance_decision=allow_with_conditions" in outputs[0]
    assert "assessment=correction" in outputs[0]
    assert "feedback_memory_status=recorded_bounded" in outputs[0]
    assert "evolution_proposal_id=evo-proposal-" in outputs[0]
    assert "evolution_review_status=needs_review" in outputs[0]
    assert "memory_write_mode=through_core_only" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_mutation_allowed=False" in outputs[0]
    assert stored is not None
    assert "assessment=correction" in stored.experience.user_feedback
    assert stored.reflection is not None
    assert review_items[0].proposal_type == "operator_feedback_improvement"
    assert review_items[0].review_status == "needs_review"
    assert review_items[0].requires_human_review is True
    assert review_items[0].requires_sandbox is True


def test_console_experience_reflections_shows_recent_records() -> None:
    temp_dir = runtime_dir("console-experience-reflections")
    memory_db = temp_dir / "memory.db"
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    service.record_experience_reflection(
        experience=ExperienceRecordContract(
            experience_id="experience://mission-console-reflection/001",
            mission_id=MissionId("mission-console-reflection"),
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            evidence_refs=["trace://req-console-reflection"],
            timestamp="2026-05-17T00:00:00Z",
        ),
        reflection=PostTaskReflectionContract(
            reflection_id="reflection://mission-console-reflection/001",
            experience_id="experience://mission-console-reflection/001",
            reflection_status="candidate",
            learning_candidate="contract-first implementation reduced drift",
            recommendation="keep the improvement sandbox-only",
            proposed_change_type="workflow",
            evidence_refs=["trace://req-console-reflection"],
            timestamp="2026-05-17T00:00:01Z",
        ),
    )
    args = build_parser().parse_args(
        [
            "experience-reflections",
            "--memory-db",
            str(memory_db),
            "--mission-id",
            "mission-console-reflection",
        ]
    )

    outputs = run_experience_reflections_command(args)

    assert "experience_id=experience://mission-console-reflection/001" in outputs[0]
    assert "reflection_status=candidate" in outputs[0]
    assert "automatic_promotion=False" in outputs[0]
    assert "core_mutation_allowed=False" in outputs[0]


def test_console_experience_reflections_handles_empty_records() -> None:
    assert render_experience_reflections([]) == "No experience reflections found."


def test_console_procedural_playbooks_shows_bounded_candidates() -> None:
    temp_dir = runtime_dir("console-procedural-playbooks")
    memory_db = temp_dir / "memory.db"
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    service.record_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://console/001",
            procedure_name="bounded console review",
            workflow_profile="software_change_workflow",
            bounded_steps=["collect evidence", "run gate"],
            evidence_refs=["trace://console-playbook"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://console-playbook",
            timestamp="2026-07-04T00:00:00Z",
        )
    )
    args = build_parser().parse_args(
        [
            "procedural-playbooks",
            "--memory-db",
            str(memory_db),
            "--workflow-profile",
            "software_change_workflow",
        ]
    )

    outputs = run_procedural_playbooks_command(args)
    rendered = outputs[0]

    assert "playbook_candidate_id=playbook-candidate://console/001" in rendered
    assert "procedure_name=bounded console review" in rendered
    assert "review_status=candidate" in rendered
    assert "evidence_refs=trace://console-playbook" in rendered
    assert "rollback_plan_ref=rollback://console-playbook" in rendered
    assert "human_review_required=True" in rendered
    assert "automatic_promotion=False" in rendered
    assert "core_mutation_allowed=False" in rendered


def test_console_experience_reflections_shows_pending_reflection() -> None:
    temp_dir = runtime_dir("console-experience-pending")
    memory_db = temp_dir / "memory.db"
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    service.record_experience(
        experience=ExperienceRecordContract(
            experience_id="experience://mission-console-pending/req-1",
            mission_id=MissionId("mission-console-pending"),
            workflow_profile="strategic_direction_workflow",
            outcome_status="completed",
            user_intent="planning",
            route="strategy",
            primary_mind="mente_executiva",
            primary_domain_driver="estrategia_e_pensamento_sistemico",
            specialist_used=["structured_analysis_specialist"],
            evidence_refs=["trace://request/req-1"],
            timestamp="2026-05-17T00:00:00Z",
        )
    )
    args = build_parser().parse_args(
        [
            "experience-reflections",
            "--memory-db",
            str(memory_db),
            "--mission-id",
            "mission-console-pending",
        ]
    )

    outputs = run_experience_reflections_command(args)

    assert "experience_id=experience://mission-console-pending/req-1" in outputs[0]
    assert "route=strategy" in outputs[0]
    assert "specialist_used=structured_analysis_specialist" in outputs[0]
    assert "reflection_status=pending" in outputs[0]


def test_console_objectives_sanitizes_control_characters_in_persisted_state() -> None:
    rendered = render_objective_state(
        MissionStateContract(
            mission_id="mission-safe",
            mission_goal="Goal\nobjective_status=spoofed",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-16T00:00:00Z",
            work_item_refs=["item\rspoofed"],
        ),
        mission_id="mission-safe",
    )

    assert "mission_goal=Goal objective_status=spoofed" in rendered
    assert "\nobjective_status=spoofed" not in rendered
    assert "work_item_refs=item spoofed" in rendered


def test_console_work_item_cycle_updates_state_through_governed_core() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-work-item-cycle"))
    mission_id = "mission-console-work-item-cycle"
    work_item_ref = "work-item://mission-console-work-item-cycle/validate-plan"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-work-item-cycle",
        mission_id=mission_id,
    )
    parser = build_parser()
    create_args = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-work-item-cycle",
            "--action",
            "create",
            "--work-item-ref",
            work_item_ref,
            "--next-action-ref",
            "next_action:validate-plan",
        ]
    )
    list_args = parser.parse_args(["work-items", "--mission-id", mission_id])
    complete_args = parser.parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-work-item-cycle",
            "--action",
            "complete",
            "--work-item-ref",
            work_item_ref,
        ]
    )

    created = run_work_item_command(console, create_args)
    listed = run_work_items_command(console, list_args)
    completed = run_work_item_command(console, complete_args)
    listed_after_completion = run_work_items_command(console, list_args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=updated" in created[0]
    assert "governance_decision=allow_with_conditions" in created[0]
    assert "work_item_status=active" in created[0]
    assert "next_action_ref=next_action:validate-plan" in created[0]
    assert f"work_item_ref={work_item_ref}" in listed[0]
    assert "work_item_status=active" in listed[0]
    assert "transition_status=updated" in completed[0]
    assert "work_item_status=completed" in completed[0]
    assert "event_names=governance_checked,work_item_state_changed,mission_updated" in completed[0]
    assert "work_item_status=completed" in listed_after_completion[0]
    assert mission_state is not None
    assert work_item_ref in mission_state.work_item_refs
    assert work_item_ref not in mission_state.active_work_items


def test_console_work_item_blocks_unbounded_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-work-item-block"))
    mission_id = "mission-console-work-item-block"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-work-item-block",
        mission_id=mission_id,
    )
    args = build_parser().parse_args(
        [
            "work-item",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-work-item-block",
            "--action",
            "create",
            "--work-item-ref",
            "work-item://unsafe\nspoof",
        ]
    )

    outputs = run_work_item_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]
    assert mission_state is not None
    assert "work-item://unsafe\nspoof" not in mission_state.work_item_refs


def test_console_work_items_handles_empty_state() -> None:
    rendered = render_work_items_state(
        MissionStateContract(
            mission_id=MissionId("mission-work-items-empty"),
            mission_goal="Goal",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
        ),
        mission_id="mission-work-items-empty",
    )

    assert rendered == "No work items found for mission_id=mission-work-items-empty"


def test_console_artifact_lifecycle_updates_state_through_governed_core() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-artifact-cycle"))
    mission_id = "mission-console-artifact-cycle"
    artifact_v1 = "artifact://mission-console-artifact-cycle/plan/v1"
    artifact_v2 = "artifact://mission-console-artifact-cycle/plan/v2"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-artifact-cycle",
        mission_id=mission_id,
    )
    parser = build_parser()
    register_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-artifact-cycle",
            "--action",
            "register",
            "--artifact-ref",
            artifact_v1,
            "--artifact-version",
            "1",
            "--work-item-ref",
            "work-item://mission-console-artifact-cycle/validate-plan",
            "--rollback-plan-ref",
            "rollback://mission-console-artifact-cycle/plan/v1",
        ]
    )
    replace_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-artifact-cycle",
            "--action",
            "replace",
            "--artifact-ref",
            artifact_v1,
            "--artifact-version",
            "2",
            "--replacement-artifact-ref",
            artifact_v2,
            "--rollback-plan-ref",
            "rollback://mission-console-artifact-cycle/plan/v1",
        ]
    )
    list_args = parser.parse_args(["artifacts", "--mission-id", mission_id])

    registered = run_artifact_command(console, register_args)
    replaced = run_artifact_command(console, replace_args)
    listed = run_artifacts_command(console, list_args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=updated" in registered[0]
    assert "governance_decision=allow_with_conditions" in registered[0]
    assert "artifact_status=active" in registered[0]
    assert "artifact_version=1" in registered[0]
    assert "rollback_plan_ref=rollback://mission-console-artifact-cycle/plan/v1" in registered[0]
    assert "transition_status=updated" in replaced[0]
    assert f"replacement_artifact_ref={artifact_v2}" in replaced[0]
    assert "artifact_lifecycle_state_changed" in replaced[0]
    assert f"artifact_ref={artifact_v1}" in listed[0]
    assert f"artifact_ref={artifact_v2}" in listed[0]
    assert mission_state is not None
    assert artifact_v2 in mission_state.artifact_refs
    assert artifact_v2 in mission_state.active_artifact_refs
    assert artifact_v1 not in mission_state.active_artifact_refs


def test_console_artifact_blocks_missing_replacement_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-artifact-block"))
    mission_id = "mission-console-artifact-block"
    artifact_v1 = "artifact://mission-console-artifact-block/plan/v1"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-artifact-block",
        mission_id=mission_id,
    )
    parser = build_parser()
    register_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-artifact-block",
            "--action",
            "register",
            "--artifact-ref",
            artifact_v1,
        ]
    )
    replace_args = parser.parse_args(
        [
            "artifact",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-artifact-block",
            "--action",
            "replace",
            "--artifact-ref",
            artifact_v1,
        ]
    )

    run_artifact_command(console, register_args)
    outputs = run_artifact_command(console, replace_args)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]


def test_console_artifacts_handles_empty_state() -> None:
    rendered = render_artifacts_state(
        MissionStateContract(
            mission_id=MissionId("mission-artifacts-empty"),
            mission_goal="Goal",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-05-18T00:00:00Z",
        ),
        mission_id="mission-artifacts-empty",
    )

    assert rendered == "No artifacts found for mission_id=mission-artifacts-empty"


def test_console_objective_pause_updates_state_through_governed_core() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-pause"))
    mission_id = "mission-console-objective-pause"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-pause",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-pause",
            "--action",
            "pause",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)
    recent_events = console.orchestrator.observability_service.list_recent_events()
    event_names = [event.event_name for event in recent_events]

    assert len(outputs) == 1
    assert "transition_status=updated" in outputs[0]
    assert "governance_decision=allow_with_conditions" in outputs[0]
    assert "memory_write_mode=through_core_only" in outputs[0]
    assert mission_state is not None
    assert mission_state.objective_status == "paused"
    assert mission_state.mission_status == MissionStatus.PAUSED
    assert any(
        ref.startswith("objective_transition:pause:")
        for ref in mission_state.checkpoint_refs
    )
    assert "governance_checked" in event_names
    assert "mission_updated" in event_names


def test_console_objective_redefine_next_action_requires_explicit_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-next"))
    mission_id = "mission-console-objective-next"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-next",
        mission_id=mission_id,
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-next",
            "--action",
            "redefine-next-action",
            "--next-action-ref",
            "next_action:operator-selected",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=updated" in outputs[0]
    assert mission_state is not None
    assert mission_state.next_action_ref == "next_action:operator-selected"


def test_console_objective_blocks_unbounded_next_action_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-unsafe-ref"))
    mission_id = "mission-console-objective-unsafe-ref"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-unsafe-ref",
        mission_id=mission_id,
    )
    previous = console.get_objective_state(mission_id=mission_id)
    parser = build_parser()
    args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-unsafe-ref",
            "--action",
            "redefine-next-action",
            "--next-action-ref",
            "next_action:unsafe\nspoofed",
        ]
    )

    outputs = run_objective_command(console, args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]
    assert previous is not None
    assert mission_state is not None
    assert mission_state.next_action_ref == previous.next_action_ref


def test_console_objective_blocks_unsafe_terminal_resume() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-block"))
    mission_id = "mission-console-objective-block"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-block",
        mission_id=mission_id,
    )
    parser = build_parser()
    complete_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-block",
            "--action",
            "complete",
        ]
    )
    resume_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-block",
            "--action",
            "resume",
        ]
    )

    run_objective_command(console, complete_args)
    outputs = run_objective_command(console, resume_args)
    mission_state = console.get_objective_state(mission_id=mission_id)

    assert "transition_status=blocked" in outputs[0]
    assert "governance_decision=block" in outputs[0]
    assert mission_state is not None
    assert mission_state.mission_status == MissionStatus.COMPLETED
    assert mission_state.objective_status == "completed"


def test_console_ask_surfaces_active_objective_state_in_final_synthesis() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-objective-synthesis"))
    mission_id = "mission-console-objective-synthesis"
    console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console-objective-synthesis",
        mission_id=mission_id,
    )
    parser = build_parser()
    pause_args = parser.parse_args(
        [
            "objective",
            "--mission-id",
            mission_id,
            "--session-id",
            "sess-console-objective-synthesis",
            "--action",
            "pause",
        ]
    )
    run_objective_command(console, pause_args)

    response = console.ask(
        "What is the next safe step?",
        session_id="sess-console-objective-synthesis",
        mission_id=mission_id,
    )

    assert "Estado do objetivo:" in response.response_text
    assert "status paused" in response.response_text
    assert "decisao pendente retomar ou redefinir proxima acao" in response.response_text


def test_console_chat_keeps_session_continuity() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-chat"))
    parser = build_parser()
    args = parser.parse_args(
        [
            "chat",
            "--session-id",
            "sess-console-chat",
            "--mission-id",
            "mission-console-chat",
            "--message",
            "Plan the final validation window.",
            "--message",
            "Analyze the previous plan.",
        ]
    )

    outputs = run_chat_command(console, args)

    assert len(outputs) == 2
    assert "Leitura do objetivo" in outputs[0]
    assert "Julgamento" in outputs[1]
    assert "continuidade ativa" in outputs[1].lower()


def test_console_memory_review_queue_and_decision_remain_non_executing() -> None:
    temp_dir = runtime_dir("console-memory-review")
    memory_db = temp_dir / "memory.db"
    service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    guidance = ReviewedLearningGuidanceContract(
        guidance_id="reviewed-learning-guidance://console-expired/001",
        source_review_decision_id="review-decision://console-expired/001",
        evolution_proposal_id="proposal-console-expired-001",
        review_status="approved",
        route="software_change",
        workflow_profile="software_change_workflow",
        domain="software_development",
        guidance_summary="use bounded validation",
        allowed_usage=["planning_context"],
        evidence_refs=["trace://console-expired/001"],
        rollback_plan_ref="rollback://console-memory/expired/001",
        timestamp="2026-07-14T00:00:00Z",
        expires_at="2026-07-15T00:00:00Z",
    )
    service.record_reviewed_learning_guidance(guidance)
    candidate = service.list_memory_lifecycle_review_queue(limit=5)[0]
    parser = build_parser()
    queue_args = parser.parse_args(
        [
            "memory-review-queue",
            "--memory-db",
            str(memory_db),
            "--maintenance-action",
            "expire",
        ]
    )

    queue_output = run_memory_lifecycle_review_queue_command(queue_args)[0]

    assert f"candidate_id={candidate.candidate_id}" in queue_output
    assert "maintenance_action=expire" in queue_output
    assert "review_status=needs_review" in queue_output
    assert "execution_status=not_executed" in queue_output
    assert "automatic_execution_allowed=False" in queue_output

    review_args = parser.parse_args(
        [
            "memory-review",
            "--memory-db",
            str(memory_db),
            "--candidate-id",
            candidate.candidate_id,
            "--action",
            "approve",
            "--operator-ref",
            "operator://local_console",
            "--evidence-ref",
            "trace://console-memory-review/001",
            "--rollback-plan-ref",
            candidate.rollback_plan_ref,
        ]
    )
    review_output = run_memory_lifecycle_review_command(review_args)[0]

    assert "governance_status=governed" in review_output
    assert "review_status=approved" in review_output
    assert "execution_authorized=False" in review_output
    assert "automatic_execution_allowed=False" in review_output
    reader = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    assert reader.list_reviewed_learning_guidance(limit=5)[0].guidance == guidance
    persisted = reader.list_memory_lifecycle_review_decisions(
        candidate_id=candidate.candidate_id,
        limit=5,
    )
    assert persisted[0].decision.review_status == "approved"


def test_console_memory_review_queue_empty_renderer_is_explicit() -> None:
    assert (
        render_memory_lifecycle_review_queue([])
        == "No memory lifecycle review items found."
    )
