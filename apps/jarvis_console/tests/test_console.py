from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from json import dumps, loads
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
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService

from apps.jarvis_console.cli import (
    JarvisConsole,
    LongHorizonGoalStrategyResult,
    build_parser,
    main,
    render_action_confirmation_receipt,
    render_artifacts_state,
    render_daily_operator_utility_report,
    render_daily_operator_workspace,
    render_decision_attribution_report,
    render_evolution_review_queue,
    render_experience_reflections,
    render_goal_strategy,
    render_longitudinal_learning_report,
    render_memory_lifecycle_review_queue,
    render_mission_cycle,
    render_objective_state,
    render_operator_dashboard,
    render_readiness_dashboard,
    render_response,
    render_skill_evolution_operator_view,
    render_work_items_state,
    render_workflow_lifecycle_view,
    render_workflow_transition_result,
    run_action_confirm_command,
    run_artifact_command,
    run_artifacts_command,
    run_ask_command,
    run_chat_command,
    run_daily_workspace_command,
    run_decision_attribution_command,
    run_evolution_review_command,
    run_evolution_review_queue_command,
    run_experience_reflections_command,
    run_goal_strategy_command,
    run_longitudinal_learning_report_command,
    run_memory_lifecycle_review_command,
    run_memory_lifecycle_review_queue_command,
    run_mission_cycle_command,
    run_mission_feedback_command,
    run_mission_workflow_command,
    run_objective_command,
    run_objectives_command,
    run_operator_dashboard_command,
    run_operator_outcomes_command,
    run_procedural_playbooks_command,
    run_progress_report_command,
    run_readiness_dashboard_command,
    run_skill_evolution_command,
    run_technology_candidates_command,
    run_technology_experiment_eval_command,
    run_technology_experiment_pack_command,
    run_technology_experiments_command,
    run_technology_radar_command,
    run_technology_radar_intake_command,
    run_work_item_command,
    run_work_items_command,
)
from shared.action_confirmation import build_action_intent
from shared.contracts import (
    ActionIntentContract,
    DailyOperatorMissionOutcomeContract,
    DailyOperatorUtilityReportContract,
    DecisionOutcomeAttributionReportContract,
    ExperienceRecordContract,
    LongitudinalLearningReportContract,
    MissionStateContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    RegressionReadinessReportContract,
    ReviewedLearningGuidanceContract,
    SkillEvolutionOperatorViewContract,
)
from shared.events import InternalEventEnvelope
from shared.technology_experiment import technology_experiment_pack_fingerprint
from shared.types import MissionId, MissionStatus, RequestId, RiskLevel, SessionId
from tests.unit.test_technology_experiment_tool import (
    _intake as _experiment_intake,
)
from tests.unit.test_technology_experiment_tool import _pack_selection
from tests.unit.test_technology_radar_intake_tool import _intake


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


def action_confirmation_intent() -> ActionIntentContract:
    issued_at = datetime.now(UTC)
    return build_action_intent(
        intent_id=f"action-intent://console/{uuid4().hex}",
        origin_request_id=RequestId("request://console/confirmation-origin"),
        session_id=SessionId("session://console/confirmation"),
        mission_id=MissionId("mission://console/confirmation"),
        operator_identity_ref="operator://console/confirmation",
        handler_id="handler://operational/local-file",
        handler_version="1.0.0",
        operation="write_local_file",
        target_ref="artifact://operational/confirmation-test",
        content_digest="a" * 64,
        precondition_digest="b" * 64,
        risk_level=RiskLevel.MODERATE,
        policy_version="action-confirmation/v1",
        nonce=f"nonce_{uuid4().hex}",
        issued_at=issued_at.isoformat(),
        expires_at=(issued_at + timedelta(minutes=5)).isoformat(),
        now=issued_at,
    )


def test_console_readiness_dashboard_is_read_only_and_does_not_run_gate() -> None:
    missing_report = runtime_dir("console-readiness-empty") / "missing.json"
    args = build_parser().parse_args(
        ["readiness-dashboard", "--longitudinal-report", str(missing_report)]
    )

    outputs = run_readiness_dashboard_command(args)

    assert "regression_readiness=read_only" in outputs[0]
    assert "gate_mode=not_run" in outputs[0]
    assert "test_status=not_run" in outputs[0]
    assert "document_status=healthy" in outputs[0]
    assert "longitudinal_learning_status=not_evaluated" in outputs[0]
    assert "longitudinal_learning_authority_safe=True" in outputs[0]
    assert "autonomous_release_allowed=False" in outputs[0]


def test_console_readiness_dashboard_loads_explicit_longitudinal_evidence() -> None:
    temp_dir = runtime_dir("console-readiness-learning")
    report_path = temp_dir / "longitudinal.json"
    report_path.write_text(
        dumps(
            {
                "report_id": "longitudinal-learning-report://console-readiness",
                "report_status": "sustained_gain_observed",
                "regression_flags": [],
                "read_only": True,
                "promotion_authorized": False,
                "automatic_promotion_allowed": False,
                "core_mutation_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    args = build_parser().parse_args(
        ["readiness-dashboard", "--longitudinal-report", str(report_path)]
    )

    rendered = run_readiness_dashboard_command(args)[0]

    assert "longitudinal_learning_status=sustained_gain_observed" in rendered
    assert (
        "longitudinal_learning_evidence_ref="
        "longitudinal-learning-report://console-readiness"
    ) in rendered
    assert "longitudinal_learning_authority_safe=True" in rendered
    assert "autonomous_release_allowed=False" in rendered


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
    assert "longitudinal_learning_status=not_evaluated" in rendered


def test_console_longitudinal_learning_report_is_explicitly_non_authoritative() -> None:
    rendered = render_longitudinal_learning_report(
        LongitudinalLearningReportContract(
            report_id="longitudinal-learning-report://console-test",
            report_status="insufficient_evidence",
            minimum_observations=2,
            target_count=1,
            observation_count=0,
            observed_version_count=0,
            version_metrics=[],
            missing_evidence_refs=["skill-candidate://test/1.0.0"],
            regression_flags=[],
            rollback_refs=[],
            limitations=["measurement_does_not_authorize_promotion"],
            evidence_refs=["skill-candidate://test/1.0.0"],
            generated_at="2026-07-16T12:00:00Z",
        )
    )

    assert "longitudinal_learning=read_only" in rendered
    assert "report_status=insufficient_evidence" in rendered
    assert "measurement_does_not_authorize_promotion" in rendered
    assert "promotion_authorized=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered


def test_console_learning_report_command_handles_empty_canonical_stores() -> None:
    temp_dir = runtime_dir("console-learning-report-empty")
    args = build_parser().parse_args(
        [
            "learning-report",
            "--observability-db",
            str(temp_dir / "observability.db"),
            "--memory-db",
            str(temp_dir / "memory.db"),
            "--evolution-db",
            str(temp_dir / "evolution.db"),
        ]
    )

    rendered = run_longitudinal_learning_report_command(args)[0]

    assert "longitudinal_learning=read_only" in rendered
    assert "report_status=no_version_targets" in rendered
    assert "target_count=0" in rendered
    assert "observation_count=0" in rendered
    assert "promotion_authorized=False" in rendered


def test_console_operator_outcomes_correlates_stores_without_mutation() -> None:
    temp_dir = runtime_dir("console-operator-outcomes")
    memory_db = temp_dir / "memory.db"
    observability_db = temp_dir / "observability.db"
    memory = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    observability = ObservabilityService(database_path=str(observability_db))
    memory.repository.upsert_mission_state(
        MissionStateContract(
            mission_id=MissionId("mission-console-outcomes"),
            mission_goal="Measure the daily operator loop",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-18T10:05:00+00:00",
        )
    )
    observability.ingest_events(
        [
            InternalEventEnvelope(
                event_id="event-console-outcomes-resume",
                event_name="open_loop_resumed",
                timestamp="2026-07-18T10:00:00+00:00",
                source_service="orchestrator-service",
                mission_id="mission-console-outcomes",
                payload={"next_action_ref": "next-action://console/outcomes"},
            ),
            InternalEventEnvelope(
                event_id="event-console-outcomes-complete",
                event_name="work_item_state_changed",
                timestamp="2026-07-18T10:05:00+00:00",
                source_service="orchestrator-service",
                mission_id="mission-console-outcomes",
                payload={
                    "work_item_ref": "work-item://console/outcomes",
                    "work_item_status": "completed",
                    "previous_work_item_status": "active",
                },
            ),
        ]
    )
    before = {
        memory_db: memory_db.read_bytes(),
        observability_db: observability_db.read_bytes(),
    }
    args = build_parser().parse_args(
        [
            "operator-outcomes",
            "--memory-db",
            str(memory_db),
            "--observability-db",
            str(observability_db),
            "--period-start",
            "2026-07-18T09:00:00+00:00",
            "--period-end",
            "2026-07-19T00:00:00+00:00",
        ]
    )

    rendered = run_operator_outcomes_command(args)[0]

    assert "operator_outcomes=read_only" in rendered
    assert "mission_count=1" in rendered
    assert "completion_rate=1.0" in rendered
    assert "resume_count=1" in rendered
    assert "average_time_to_next_action_seconds=300.0" in rendered
    assert "saved_time_claim_status=not_claimed_without_controlled_baseline" in rendered
    assert "memory_write_mode=read_only" in rendered
    assert "autonomous_action_allowed=False" in rendered
    assert memory_db.read_bytes() == before[memory_db]
    assert observability_db.read_bytes() == before[observability_db]


def test_console_operator_outcomes_renderer_exposes_unavailable_metrics() -> None:
    mission = DailyOperatorMissionOutcomeContract(
        mission_id="mission-no-evidence",
        work_item_event_count=0,
        observed_work_item_count=0,
        completed_work_item_count=0,
        reworked_work_item_count=0,
        artifact_event_count=0,
        observed_artifact_count=0,
        resume_count=0,
        feedback_count=0,
        helpful_feedback_count=0,
        time_to_next_action_observation_count=0,
        completion_rate=None,
        rework_rate=None,
        helpful_feedback_rate=None,
        average_time_to_next_action_seconds=None,
        stale_open_loop_count=None,
        limitations=["canonical_mission_snapshot_missing"],
    )
    report = DailyOperatorUtilityReportContract(
        report_id="operator-utility-report://console-limited",
        report_status="measured_with_limitations",
        period_start="2026-07-17T00:00:00+00:00",
        period_end="2026-07-18T00:00:00+00:00",
        generated_at="2026-07-18T12:00:00+00:00",
        mission_count=1,
        mission_metrics=[mission],
        event_count=0,
        work_item_event_count=0,
        observed_work_item_count=0,
        completed_work_item_count=0,
        reworked_work_item_count=0,
        completion_rate=None,
        rework_rate=None,
        artifact_event_count=0,
        observed_artifact_count=0,
        resume_count=0,
        stale_open_loop_count=None,
        feedback_count=0,
        feedback_mission_count=0,
        feedback_coverage=0.0,
        helpful_feedback_count=0,
        helpful_feedback_rate=None,
        time_to_next_action_observation_count=0,
        average_time_to_next_action_seconds=None,
        limitations=["historical_stale_loop_snapshot_not_available"],
        evidence_refs=[],
    )

    rendered = render_daily_operator_utility_report(report)

    assert "completion_rate=unavailable" in rendered
    assert "stale_open_loop_count=unavailable" in rendered
    assert "historical_stale_loop_snapshot_not_available" in rendered


def test_console_decision_attribution_renderer_is_explicitly_non_authoritative() -> None:
    rendered = render_decision_attribution_report(
        DecisionOutcomeAttributionReportContract(
            report_id="decision-outcome-attribution-report://console-test",
            report_status="insufficient_evidence",
            generated_at="2026-08-11T13:00:00Z",
            record_count=0,
            correlation_only_count=0,
            declared_causality_count=0,
            insufficient_evidence_count=0,
            feedback_linked_count=0,
            comparator_count=0,
            failed_record_count=0,
            items=[],
            limitations=["canonical_attribution_record_required"],
            evidence_refs=[],
        )
    )

    assert "decision_attribution=read_only" in rendered
    assert "report_status=insufficient_evidence" in rendered
    assert "causality_scope=runtime_declared_participation_only" in rendered
    assert "causal_effect_proven=False" in rendered
    assert "gain_claim_status=not_established_without_comparator" in rendered
    assert "memory_write_allowed=False" in rendered
    assert "execution_allowed=False" in rendered
    assert "tool_dispatch_allowed=False" in rendered
    assert "promotion_authorized=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered


def test_console_decision_attribution_reads_stores_and_saves_derived_report() -> None:
    temp_dir = runtime_dir("console-decision-attribution-empty")
    memory_db = temp_dir / "memory.db"
    observability_db = temp_dir / "observability.db"
    MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    ObservabilityService(database_path=str(observability_db))
    before = {
        memory_db: memory_db.read_bytes(),
        observability_db: observability_db.read_bytes(),
    }
    args = build_parser().parse_args(
        [
            "decision-attribution",
            "--memory-db",
            str(memory_db),
            "--observability-db",
            str(observability_db),
            "--request-id",
            "request-console-filter",
            "--mission-id",
            "mission-console-filter",
            "--workflow-profile",
            "software_change_workflow",
            "--limit",
            "5",
            "--output-dir",
            str(temp_dir / "reports"),
        ]
    )

    rendered = run_decision_attribution_command(args)[0]

    assert "decision_attribution=read_only" in rendered
    assert "report_status=insufficient_evidence" in rendered
    assert "record_count=0" in rendered
    assert "causal_effect_proven=False" in rendered
    assert (temp_dir / "reports" / "latest.json").exists()
    assert memory_db.read_bytes() == before[memory_db]
    assert observability_db.read_bytes() == before[observability_db]


def test_console_decision_attribution_supports_json_envelope(capsys) -> None:
    temp_dir = runtime_dir("console-decision-attribution-json")
    exit_code = main(
        [
            "decision-attribution",
            "--memory-db",
            str(temp_dir / "memory.db"),
            "--observability-db",
            str(temp_dir / "observability.db"),
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["schema_version"] == "jarvis-console/v1"
    assert payload["command_id"] == "decision-attribution"
    assert payload["status"] == "success"
    assert "decision_attribution=read_only" in payload["outputs"][0]
    assert "causal_effect_proven=False" in payload["outputs"][0]
    assert "promotion_authorized=False" in payload["outputs"][0]


def test_console_ask_returns_orchestrated_response() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-ask"))
    response = ask_with_bounded_autonomy(
        console,
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


def test_console_ask_cli_forwards_exact_action_confirmation_context() -> None:
    captured_contracts: list[object] = []
    response = SimpleNamespace(response_text="confirmation context captured")
    orchestrator = SimpleNamespace(
        handle_input=lambda contract: captured_contracts.append(contract) or response
    )
    console = JarvisConsole(orchestrator=orchestrator)  # type: ignore[arg-type]
    args = build_parser().parse_args(
        [
            "ask",
            "Prepare the bounded action.",
            "--session-id",
            "session-confirmation-cli",
            "--mission-id",
            "mission-confirmation-cli",
            "--operator-identity-ref",
            "operator://confirmation-cli",
            "--requested-autonomy-level",
            "supervised_external_action",
            "--max-autonomy-level",
            "supervised_external_action",
            "--autonomy-confirmation-mode",
            "explicit",
            "--action-confirmation-receipt-id",
            "confirmation-receipt://exact",
            "--origin-request-id",
            "request://confirmation/origin",
        ]
    )

    outputs = run_ask_command(console, args)

    assert outputs == ["confirmation context captured"]
    assert len(captured_contracts) == 1
    contract = captured_contracts[0]
    assert contract.requested_autonomy_level == "supervised_external_action"
    assert contract.max_autonomy_level == "supervised_external_action"
    assert contract.autonomy_confirmation_mode == "explicit"
    assert (
        contract.action_confirmation_receipt_id
        == "confirmation-receipt://exact"
    )
    assert (
        contract.action_confirmation_origin_request_id
        == "request://confirmation/origin"
    )


def test_console_renders_only_safe_confirmation_challenge_metadata() -> None:
    challenge = SimpleNamespace(
        challenge_id="confirmation-challenge://console-safe",
        origin_request_id="request://console/safe-origin",
        action_fingerprint="a" * 64,
        expires_at="2026-08-29T23:00:00+00:00",
        target_ref="C:\\private\\should-not-render.txt",
        content="should-not-render",
    )
    response = SimpleNamespace(
        response_text="Explicit confirmation is required.",
        action_confirmation_challenge=challenge,
    )

    rendered = render_response(response, debug=False)  # type: ignore[arg-type]

    assert "challenge_id=confirmation-challenge://console-safe" in rendered
    assert "origin_request_id=request://console/safe-origin" in rendered
    assert f"action_fingerprint={'a' * 64}" in rendered
    assert "expires_at=2026-08-29T23:00:00+00:00" in rendered
    assert "confirmation_evidence_only=True" in rendered
    assert "confirmation_execution_allowed=False" in rendered
    assert "should-not-render" not in rendered
    assert "C:\\private" not in rendered


def test_console_runtime_wires_workflow_lifecycle_verifier_to_paired_store() -> None:
    temp_dir = runtime_dir("console-workflow-lifecycle-verifier")
    console = JarvisConsole.build(runtime_dir=temp_dir)

    verifier = (
        console.orchestrator.memory_service._workflow_lifecycle_transition_verifier
    )

    assert callable(verifier)
    assert verifier.__self__.repository.database_path == temp_dir / "evolution.db"


def test_console_runtime_persists_and_wires_action_confirmation_ledger() -> None:
    temp_dir = runtime_dir("console-action-confirmation-wiring")
    console = JarvisConsole.build(runtime_dir=temp_dir)
    governance = console.orchestrator.governance_service
    verifier = console.orchestrator.operational_service.action_confirmation_verifier

    assert Path(governance.action_confirmation_repository.database_path) == (
        temp_dir / "governance.db"
    )
    assert (temp_dir / "governance.db").is_file()
    assert callable(verifier)
    assert verifier == governance.verify_action_confirmation_claim


def test_action_confirm_command_records_non_authorizing_receipt_after_restart() -> None:
    temp_dir = runtime_dir("console-action-confirmation-command")
    initial_console = JarvisConsole.build(runtime_dir=temp_dir)
    intent = action_confirmation_intent()
    challenge = initial_console.orchestrator.governance_service.issue_action_confirmation_challenge(
        intent
    )
    restarted_console = JarvisConsole.build(runtime_dir=temp_dir)
    args = build_parser().parse_args(
        [
            "action-confirm",
            "--challenge-id",
            challenge.challenge_id,
            "--action-fingerprint",
            intent.action_fingerprint,
            "--operator-identity-ref",
            intent.operator_identity_ref,
        ]
    )

    outputs = run_action_confirm_command(restarted_console, args)

    assert len(outputs) == 1
    rendered = outputs[0]
    assert "receipt_id=confirmation-receipt://" in rendered
    assert f"challenge_id={challenge.challenge_id}" in rendered
    assert f"origin_request_id={intent.origin_request_id}" in rendered
    assert f"action_fingerprint={intent.action_fingerprint}" in rendered
    assert "receipt_fingerprint=" in rendered
    assert "confirmation_evidence_only=True" in rendered
    assert "single_use=True" in rendered
    assert "execution_allowed=False" in rendered
    assert "tool_dispatch_allowed=False" in rendered
    assert "runtime_activation_allowed=False" in rendered
    assert "promotion_authorized=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered

    receipt_id = next(
        line.partition("=")[2]
        for line in rendered.splitlines()
        if line.startswith("receipt_id=")
    )
    context = restarted_console.orchestrator.governance_service.load_action_confirmation_context(
        receipt_id
    )
    assert context.intent == intent
    assert context.challenge == challenge
    assert render_action_confirmation_receipt(context.receipt) == rendered


def test_console_accepts_operator_surface_identity_overrides() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-surface"))
    response = ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
        work_item_ref=work_item_ref,
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


def test_console_technology_radar_registers_and_reads_reviewed_manifest() -> None:
    temp_dir = runtime_dir("console-technology-radar")
    intake_root = temp_dir / "intake"
    intake_root.mkdir()
    manifest = intake_root / "reviewed-reference.json"
    manifest.write_text(
        dumps(asdict(_intake()), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    evolution_db = temp_dir / "evolution.db"
    intake_args = build_parser().parse_args(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(evolution_db),
            "--intake-root",
            str(intake_root),
            "--manifest",
            manifest.name,
            "--manifest-sha256",
            sha256(manifest.read_bytes()).hexdigest(),
        ]
    )

    intake_output = run_technology_radar_intake_command(intake_args)[0]

    assert "assessment_status=eligible_for_reviewed_registry" in intake_output
    assert "source_trusted=False" in intake_output
    assert "network_fetch_performed=False" in intake_output
    assert "knowledge_ingestion_performed=False" in intake_output
    assert "evolution_proposal_created=False" in intake_output
    assert "runtime_activation_performed=False" in intake_output
    assert "promotion_performed=False" in intake_output
    read_args = build_parser().parse_args(
        [
            "technology-radar",
            "--evolution-db",
            str(evolution_db),
            "--target-gap-ref",
            "KNW-006",
        ]
    )
    rendered = run_technology_radar_command(read_args)[0]
    assert "intake_id=technology-intake://openai-agents-sdk/1.0.0" in rendered
    assert "license_id=MIT" in rendered
    assert "source_trust_status=operator_attested_untrusted_reference" in rendered
    assert "automatic_promotion_allowed=False" in rendered


def test_console_technology_radar_rejects_json_for_mutating_intake(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(tmp_path / "evolution.db"),
            "--intake-root",
            str(tmp_path),
            "--manifest",
            "missing.json",
            "--manifest-sha256",
            "0" * 64,
            "--format",
            "json",
        ]
    )

    assert exit_code == 2
    envelope = loads(capsys.readouterr().err)
    assert envelope["error_code"] == "json_not_supported"
    assert envelope["command_id"] == "technology-radar-intake"


def test_console_technology_radar_rejects_secret_without_persistence_or_echo(
    tmp_path: Path,
    capsys,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    secret = "never-persist-or-echo-this-secret"
    unsafe = _intake()
    unsafe_payload = asdict(unsafe)
    unsafe_payload["claims"] = [f"api_key={secret}"]
    manifest = intake_root / "unsafe.json"
    manifest.write_text(dumps(unsafe_payload), encoding="utf-8")
    evolution_db = tmp_path / "evolution.db"

    exit_code = main(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(evolution_db),
            "--intake-root",
            str(intake_root),
            "--manifest",
            manifest.name,
            "--manifest-sha256",
            sha256(manifest.read_bytes()).hexdigest(),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert secret not in captured.out
    assert secret not in captured.err
    assert "sensitive_material_detected" in captured.err
    assert EvolutionLabService(
        database_path=str(evolution_db)
    ).list_technology_radar_intakes() == []


def test_console_technology_radar_read_does_not_create_missing_store(
    tmp_path: Path,
    capsys,
) -> None:
    evolution_db = tmp_path / "missing" / "evolution.db"

    exit_code = main(
        [
            "technology-radar",
            "--evolution-db",
            str(evolution_db),
            "--format",
            "json",
        ]
    )

    envelope = loads(capsys.readouterr().out)
    assert exit_code == 0
    assert envelope["status"] == "success"
    assert envelope["outputs"] == ["No reviewed technology radar intakes found."]
    assert not evolution_db.exists()
    assert not evolution_db.parent.exists()


def test_console_invalid_intake_fails_before_creating_writer_store(
    tmp_path: Path,
    capsys,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = intake_root / "invalid.json"
    manifest.write_text("[]", encoding="utf-8")
    evolution_db = tmp_path / "missing" / "evolution.db"

    exit_code = main(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(evolution_db),
            "--intake-root",
            str(intake_root),
            "--manifest",
            manifest.name,
            "--manifest-sha256",
            sha256(manifest.read_bytes()).hexdigest(),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "manifest root must be an object" in captured.err
    assert not evolution_db.exists()
    assert not evolution_db.parent.exists()


def test_console_manifest_digest_mismatch_fails_before_creating_writer_store(
    tmp_path: Path,
    capsys,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = intake_root / "reviewed.json"
    manifest.write_text(dumps(asdict(_intake())), encoding="utf-8")
    evolution_db = tmp_path / "missing" / "evolution.db"

    exit_code = main(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(evolution_db),
            "--intake-root",
            str(intake_root),
            "--manifest",
            manifest.name,
            "--manifest-sha256",
            "f" * 64,
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "manifest SHA-256 mismatch" in captured.err
    assert not evolution_db.exists()
    assert not evolution_db.parent.exists()


def test_console_technology_experiment_full_reviewed_intake_to_restart_read(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    evolution_db = tmp_path / "evolution.db"
    intake = _experiment_intake()

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("technology experiment crossed an execution boundary")

    monkeypatch.setattr("os.system", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)

    intake_manifest = manifests / "intake.json"
    intake_manifest.write_text(
        dumps(asdict(intake), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    intake_args = build_parser().parse_args(
        [
            "technology-radar-intake",
            "--evolution-db",
            str(evolution_db),
            "--intake-root",
            str(manifests),
            "--manifest",
            intake_manifest.name,
            "--manifest-sha256",
            sha256(intake_manifest.read_bytes()).hexdigest(),
        ]
    )
    assert "assessment_status=eligible_for_reviewed_registry" in (
        run_technology_radar_intake_command(intake_args)[0]
    )

    pack_manifest = manifests / "pack.json"
    pack_manifest.write_text(
        dumps(_pack_selection(intake), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    pack_args = build_parser().parse_args(
        [
            "technology-experiment-pack",
            "--evolution-db",
            str(evolution_db),
            "--manifest-root",
            str(manifests),
            "--manifest",
            pack_manifest.name,
            "--manifest-sha256",
            sha256(pack_manifest.read_bytes()).hexdigest(),
        ]
    )
    pack_output = run_technology_experiment_pack_command(pack_args)[0]
    assert "pack_status=sandbox_ready" in pack_output
    assert "candidate_executed=False" in pack_output
    assert "promotion_performed=False" in pack_output
    assert "core_mutated=False" in pack_output

    restarted = EvolutionLabService(database_path=str(evolution_db))
    pack = restarted.get_technology_experiment_pack(
        experiment_pack_id="technology-experiment-pack://handoff/1.0.0",
        pack_version="1.0.0",
    )
    assert pack is not None
    proposal_snapshot = restarted.list_recent_proposals()
    decision_snapshot = restarted.list_recent_decisions()

    eval_manifest = manifests / "eval.json"
    eval_manifest.write_text(
        dumps(
            {
                "run_id": "technology-experiment-run://handoff/console/1.0.0",
                "experiment_pack_id": pack.experiment_pack_id,
                "pack_version": pack.pack_version,
                "pack_fingerprint": technology_experiment_pack_fingerprint(pack),
                "generated_at": "2026-08-12T10:11:00Z",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    eval_args = build_parser().parse_args(
        [
            "technology-experiment-eval",
            "--evolution-db",
            str(evolution_db),
            "--manifest-root",
            str(manifests),
            "--manifest",
            eval_manifest.name,
            "--manifest-sha256",
            sha256(eval_manifest.read_bytes()).hexdigest(),
        ]
    )
    run_output = run_technology_experiment_eval_command(eval_args)[0]
    assert "status=passed_sandbox_only" in run_output
    assert "readiness_status=eligible_for_human_experiment_review" in run_output
    assert "promotion_readiness=not_applicable" in run_output
    assert "execution_allowed=False" in run_output
    assert "promotion_authorized=False" in run_output

    read_args = build_parser().parse_args(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--view",
            "runs",
            "--run-id",
            "technology-experiment-run://handoff/console/1.0.0",
        ]
    )
    assert "status=passed_sandbox_only" in (
        run_technology_experiments_command(read_args)[0]
    )
    filtered_run_args = build_parser().parse_args(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--view",
            "runs",
            "--pack-version",
            pack.pack_version,
            "--candidate-ref",
            pack.candidate_ref,
        ]
    )
    assert "status=passed_sandbox_only" in (
        run_technology_experiments_command(filtered_run_args)[0]
    )
    wrong_scope_args = build_parser().parse_args(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--view",
            "runs",
            "--run-id",
            "technology-experiment-run://handoff/console/1.0.0",
            "--intake-id",
            "technology-intake://different/1.0.0",
        ]
    )
    assert run_technology_experiments_command(wrong_scope_args) == [
        "No verified technology experiment evaluation runs found."
    ]
    wrong_pack_scope_args = build_parser().parse_args(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--experiment-pack-id",
            pack.experiment_pack_id,
            "--pack-version",
            pack.pack_version,
            "--candidate-ref",
            "technology-candidate://different",
        ]
    )
    assert run_technology_experiments_command(wrong_pack_scope_args) == [
        "No verified technology experiment packs found."
    ]
    assert main(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--view",
            "runs",
            "--format",
            "json",
        ]
    ) == 0
    envelope = loads(capsys.readouterr().out)
    assert envelope["status"] == "success"
    assert "status=passed_sandbox_only" in envelope["outputs"][0]

    after_restart = EvolutionLabService(database_path=str(evolution_db))
    assert after_restart.list_recent_proposals() == proposal_snapshot == []
    assert after_restart.list_recent_decisions() == decision_snapshot == []
    assert sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) == [
        "evolution.db",
        "manifests/eval.json",
        "manifests/intake.json",
        "manifests/pack.json",
    ]


def test_console_technology_experiment_reads_are_json_safe_and_non_creating(
    tmp_path: Path,
    capsys,
) -> None:
    evolution_db = tmp_path / "missing" / "evolution.db"

    exit_code = main(
        [
            "technology-experiments",
            "--evolution-db",
            str(evolution_db),
            "--format",
            "json",
        ]
    )

    envelope = loads(capsys.readouterr().out)
    assert exit_code == 0
    assert envelope["status"] == "success"
    assert envelope["outputs"] == [
        "No verified technology experiment packs found."
    ]
    assert not evolution_db.exists()
    assert not evolution_db.parent.exists()


def test_console_technology_experiment_mutations_reject_json_before_writes(
    tmp_path: Path,
    capsys,
) -> None:
    evolution_db = tmp_path / "evolution.db"
    common = [
        "--evolution-db",
        str(evolution_db),
        "--manifest-root",
        str(tmp_path),
        "--manifest",
        "missing.json",
        "--manifest-sha256",
        "0" * 64,
        "--format",
        "json",
    ]

    for command in ("technology-experiment-pack", "technology-experiment-eval"):
        assert main([command, *common]) == 2
        envelope = loads(capsys.readouterr().err)
        assert envelope["error_code"] == "json_not_supported"
        assert envelope["command_id"] == command

    assert not evolution_db.exists()


def test_console_invalid_experiment_pack_fails_before_writer_store(
    tmp_path: Path,
    capsys,
) -> None:
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    manifest = manifests / "invalid.json"
    manifest.write_text("[]", encoding="utf-8")
    evolution_db = tmp_path / "missing" / "evolution.db"

    exit_code = main(
        [
            "technology-experiment-pack",
            "--evolution-db",
            str(evolution_db),
            "--manifest-root",
            str(manifests),
            "--manifest",
            manifest.name,
            "--manifest-sha256",
            sha256(manifest.read_bytes()).hexdigest(),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "manifest root must be an object" in captured.err
    assert not evolution_db.exists()
    assert not evolution_db.parent.exists()


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


def test_console_workflow_lifecycle_renderer_is_read_only_and_sanitizes_refs() -> None:
    transition = SimpleNamespace(
        transition_id=(
            "workflow-lifecycle-transition://safe\nworkflow_transition=forged"
        ),
        workflow_profile="software_change_workflow",
        route="software_development",
        transition_action="activate_candidate",
        transition_status="active_promoted",
        revision=1,
        previous_transition_id=None,
        active_version_ref="workflow-version://software_change_workflow/1.1.0",
        active_definition_hash="a" * 64,
        baseline_version_ref="workflow-version://software_change_workflow/1.0.0",
        candidate_version_ref="workflow-version://software_change_workflow/1.1.0",
        evolution_proposal_id="evolution-proposal://workflow/1",
        workflow_eval_run_id="workflow-eval-run://workflow/1",
        human_authorization_ref="human-authorization://workflow/1",
        operator_ref="operator://primary",
        evidence_refs=["evidence://workflow/1"],
        completed_test_refs=["test://workflow/1"],
        failure_refs=[],
        timestamp="2026-08-12T10:30:00Z",
    )

    rendered = render_workflow_lifecycle_view(
        current_transition=transition,
        transitions=[transition],
        workflow_profile="software_change_workflow",
        route="software_development",
        offset=0,
    )

    assert "workflow_lifecycle_view=read_only" in rendered
    assert "active_transition_status=found" in rendered
    assert "integrity_attention_required=False" in rendered
    assert "history_count=1" in rendered
    assert "verified_records_only=True" in rendered
    assert "memory_write_allowed=False" in rendered
    assert "runtime_execution_allowed=False" in rendered
    assert "active_registry_write_allowed=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "automatic_rollback_allowed=False" in rendered
    assert "core_mutation_allowed=False" in rendered
    assert "safe workflow_transition=forged" in rendered
    assert "\nworkflow_transition=forged\n" not in rendered


def test_console_workflow_transition_renderer_exposes_governed_manual_boundary() -> None:
    transition = SimpleNamespace(
        transition_id="workflow-lifecycle-transition://software-change/1",
        workflow_profile="software_change_workflow",
        route="software_development",
        transition_action="activate_candidate",
        transition_status="active_promoted",
        revision=1,
        previous_transition_id=None,
        active_version_ref="workflow-version://software_change_workflow/1.1.0",
        active_definition_hash="a" * 64,
        baseline_version_ref="workflow-version://software_change_workflow/1.0.0",
        candidate_version_ref="workflow-version://software_change_workflow/1.1.0",
        evolution_proposal_id="evolution-proposal://workflow/1",
        workflow_eval_run_id="workflow-eval-run://workflow/1",
        human_authorization_ref="human-authorization://workflow/1",
        operator_ref="operator://primary",
        evidence_refs=["evidence://workflow/1"],
        completed_test_refs=["test://workflow/1"],
        failure_refs=[],
        timestamp="2026-08-12T10:30:00Z",
    )
    assessment = SimpleNamespace(
        assessment_id="workflow-lifecycle-assessment://workflow/1",
        status="approved",
        blockers=[],
        human_authorization_verified=True,
        transition_recording_authorized=True,
    )

    rendered = render_workflow_transition_result(
        transition=transition,
        assessment=assessment,
        transition_recorded=True,
        release_bundle_verified=True,
    )

    assert "workflow_transition=explicit_human_action" in rendered
    assert "workflow_transition_status=recorded" in rendered
    assert "release_bundle_verified=True" in rendered
    assert "human_authorization_verified=True" in rendered
    assert "transition_recording_authorized=True" in rendered
    assert "runtime_execution_allowed=False" in rendered
    assert "tool_dispatch_allowed=False" in rendered
    assert "automatic_promotion_allowed=False" in rendered
    assert "automatic_rollback_allowed=False" in rendered
    assert "next_operator_step=verify_active_runtime_binding" in rendered


def test_console_workflow_rollback_requires_explicit_failure_before_store_access(
    capsys,
) -> None:
    temp_dir = runtime_dir("console-workflow-rollback-missing-failure")
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"

    exit_code = main(
        [
            "workflow-transition",
            "--memory-db",
            str(memory_db),
            "--evolution-db",
            str(evolution_db),
            "--workflow-profile",
            "software_change_workflow",
            "--route",
            "software_development",
            "--action",
            "rollback_to_baseline",
            "--proposal-id",
            "evolution-proposal://workflow/software-change/1",
            "--workflow-eval-run-id",
            "workflow-eval-run://software-change/1",
            "--human-authorization-ref",
            "human-authorization://workflow/software-change/rollback/1",
            "--evidence-ref",
            "evidence://workflow/software-change/rollback/1",
            "--completed-test-ref",
            "test://workflow/software-change/release",
            "--completed-external-gate",
            "standard_engineering_gate",
            "--completed-external-gate",
            "release_gate_before_promotion",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "error[invalid_command_input]" in captured.err
    assert "rollback requires at least one failure reference" in captured.err
    assert not memory_db.exists()
    assert not evolution_db.exists()


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
    response = ask_with_bounded_autonomy(
        console,
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
    response = ask_with_bounded_autonomy(
        console,
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


def test_console_daily_workspace_reads_multiple_sessions_without_mutation(
    monkeypatch,
) -> None:
    temp_dir = runtime_dir("console-daily-workspace")
    monkeypatch.setattr(
        OperationalService,
        "now",
        staticmethod(lambda: "2026-07-18T03:00:00+00:00"),
    )
    memory_db = temp_dir / "memory.db"
    evolution_db = temp_dir / "evolution.db"
    memory_service = MemoryService(database_url=f"sqlite:///{memory_db.as_posix()}")
    for mission in (
        MissionStateContract(
            mission_id=MissionId("mission-daily-fresh"),
            mission_goal="Continue the daily release",
            mission_status=MissionStatus.ACTIVE,
            checkpoints=[],
            updated_at="2026-07-17T03:00:00+00:00",
            objective_status="active",
            active_work_items=["work-item://daily/validate"],
            next_action_ref="next-action://daily/validate",
        ),
        MissionStateContract(
            mission_id=MissionId("mission-daily-stale"),
            mission_goal="Review the paused migration",
            mission_status=MissionStatus.PAUSED,
            checkpoints=[],
            updated_at="2026-07-10T03:00:00+00:00",
            objective_status="paused",
            open_checkpoint_refs=["checkpoint://daily/migration"],
        ),
    ):
        memory_service.repository.upsert_mission_state(mission)
    evolution_service = EvolutionLabService(database_path=str(evolution_db))
    proposal = evolution_service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-daily-fresh/001",
            mission_id="mission-daily-fresh",
            workflow_profile="operational_readiness_workflow",
            outcome_status="completed",
            learning_candidate="Preserve daily validation evidence.",
            recommendation="Review the evidence before the next action.",
            evidence_refs=["evidence://daily/001"],
            proposed_tests=["tests/unit/test_daily_workspace.py"],
            rollback_plan_ref="rollback://daily/001",
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

    output = run_daily_workspace_command(args)[0]

    assert "daily_operator_workspace=read_only" in output
    assert "workspace_status=operator_decision_required" in output
    assert "mission_count=2" in output
    assert "active_work_item_count=1" in output
    assert "open_checkpoint_count=1" in output
    assert "pending_review_count=1" in output
    assert "stale_mission_count=1" in output
    assert "mission_id=mission-daily-fresh" in output
    assert "mission_id=mission-daily-stale" in output
    assert "freshness_status=stale" in output
    assert f"pending_evolution_review_refs={proposal.evolution_proposal_id}" in output
    assert "next_operator_decision=review_evolution_proposal:" in output
    assert "ordering_policy=updated_at_desc_no_priority_inference" in output
    assert "memory_write_mode=read_only" in output
    assert "autonomous_resume_allowed=False" in output
    assert "autonomous_scheduling_allowed=False" in output
    assert render_daily_operator_workspace(
        OperationalService.build_daily_operator_workspace(
            mission_states=[],
            generated_at="2026-07-17T04:00:00+00:00",
        )
    ).startswith("daily_operator_workspace=read_only")
    assert memory_db.read_bytes() == before[memory_db]
    assert evolution_db.read_bytes() == before[evolution_db]


def test_console_progress_report_synthesizes_canonical_mission_state() -> None:
    temp_dir = runtime_dir("console-progress-report")
    console = JarvisConsole.build(runtime_dir=temp_dir)
    mission_id = "mission-console-progress-report"
    response = ask_with_bounded_autonomy(
        console,
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
        work_item_ref=f"work-item://{mission_id}/review-release",
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


def test_console_mission_workflow_runs_governed_loop_end_to_end(monkeypatch) -> None:
    temp_dir = runtime_dir("console-mission-workflow")
    evolution_db = temp_dir / "evolution.db"
    console = JarvisConsole.build(runtime_dir=temp_dir)
    bounded_console = JarvisConsole(orchestrator=console.orchestrator)
    monkeypatch.setattr(
        console,
        "ask",
        lambda prompt, **kwargs: ask_with_bounded_autonomy(
            bounded_console,
            prompt,
            **kwargs,
        ),
    )
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


def test_console_runtime_reloads_only_evolution_verified_reviewed_playbooks() -> None:
    temp_dir = runtime_dir("console-reviewed-playbook-verifier")
    evolution = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = ProceduralPlaybookCandidateContract(
        playbook_candidate_id="playbook-candidate://console/reviewed-001",
        procedure_name="reviewed console planning guidance",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="computacao_e_desenvolvimento",
        bounded_steps=[
            "collect contract evidence",
            "keep the rollback path explicit",
        ],
        evidence_refs=["evidence://console/reviewed-001"],
        proposed_tests=["pytest apps/jarvis_console/tests/test_console.py"],
        rollback_plan_ref="rollback://console/reviewed-001",
        timestamp="2026-07-18T12:00:00Z",
    )
    proposal = evolution.create_proposal_from_procedural_playbook_candidate(
        candidate
    )
    review = evolution.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://console/reviewed-001/human-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
        release_version="1.0.0",
    )
    checklist = evolution.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
    )
    gate = evolution.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    playbook = evolution.derive_reviewed_procedural_playbook(
        candidate,
        review,
        version="1.0.0",
        release_checklist=checklist,
        promotion_gate=gate,
    )

    first_console = JarvisConsole.build(runtime_dir=temp_dir)
    stored = (
        first_console.orchestrator.memory_service.record_reviewed_procedural_playbook(
            playbook
        )
    )
    reloaded_console = JarvisConsole.build(runtime_dir=temp_dir)

    assert (
        reloaded_console.orchestrator.memory_service.list_reviewed_procedural_playbooks(
            workflow_profile=candidate.workflow_profile,
            route=str(candidate.route),
            domain=str(candidate.domain),
            review_status="approved",
        )
        == [stored]
    )


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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
        "Plan the controlled rollout.",
        session_id="sess-console-artifact-cycle",
        mission_id=mission_id,
    )
    console.transition_work_item(
        mission_id=mission_id,
        work_item_ref="work-item://mission-console-artifact-cycle/validate-plan",
        transition="create",
        session_id="sess-console-artifact-cycle",
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
    assert f"resulting_artifact_ref={artifact_v2}" in replaced[0]
    assert f"supersedes_artifact_ref={artifact_v1}" in replaced[0]
    assert "artifact_lifecycle_state_changed" in replaced[0]
    assert f"artifact_ref={artifact_v1}" in listed[0]
    assert f"artifact_ref={artifact_v2}" in listed[0]
    assert "artifact_status=superseded" in listed[0]
    assert "external_file_mutation_allowed=False" in listed[0]
    assert mission_state is not None
    assert artifact_v2 in mission_state.artifact_refs
    assert artifact_v2 in mission_state.active_artifact_refs
    assert artifact_v1 not in mission_state.active_artifact_refs


def test_console_artifact_blocks_missing_replacement_ref() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-artifact-block"))
    mission_id = "mission-console-artifact-block"
    artifact_v1 = "artifact://mission-console-artifact-block/plan/v1"
    ask_with_bounded_autonomy(
        console,
        "Plan the controlled rollout.",
        session_id="sess-console-artifact-block",
        mission_id=mission_id,
    )
    work_item_ref = "work-item://mission-console-artifact-block/plan"
    console.transition_work_item(
        mission_id=mission_id,
        work_item_ref=work_item_ref,
        transition="create",
        session_id="sess-console-artifact-block",
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
            "--artifact-version",
            "1",
            "--work-item-ref",
            work_item_ref,
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
            "--artifact-version",
            "2",
            "--rollback-plan-ref",
            "rollback://mission-console-artifact-block/plan/v1",
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
    ask_with_bounded_autonomy(
        console,
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
