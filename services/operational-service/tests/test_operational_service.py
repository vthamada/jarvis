from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from operational_service.service import OperationalExecution, OperationalService

from shared.contracts import MissionStateContract, OperationDispatchContract
from shared.types import (
    MissionId,
    MissionStatus,
    OperationId,
    OperationStatus,
    RequestId,
    SessionId,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_operational_service_name() -> None:
    assert OperationalService.name == "operational-service"


def test_operational_service_builds_cross_session_daily_workspace() -> None:
    service = OperationalService(
        artifact_dir=str(runtime_dir("operational-daily-workspace"))
    )
    fresh = MissionStateContract(
        mission_id=MissionId("mission-fresh"),
        mission_goal="Continue the current release",
        mission_status=MissionStatus.ACTIVE,
        checkpoints=[],
        updated_at="2026-07-17T09:00:00+00:00",
        project_ref="project://release",
        objective_ref="objective://release/controlled",
        objective_status="active",
        work_item_refs=["work-item://release/validate"],
        active_work_items=["work-item://release/validate"],
        artifact_refs=["artifact://release/plan/v1"],
        active_artifact_refs=["artifact://release/plan/v1"],
        next_action_ref="next-action://release/validate",
    )
    stale_blocked = MissionStateContract(
        mission_id=MissionId("mission-stale"),
        mission_goal="Resolve the blocked migration",
        mission_status=MissionStatus.BLOCKED,
        checkpoints=[],
        updated_at="2026-07-12T08:00:00+00:00",
        objective_status="blocked",
        open_checkpoint_refs=["checkpoint://migration/approval"],
    )

    workspace = service.build_daily_operator_workspace(
        mission_states=[stale_blocked, fresh],
        pending_evolution_review_refs=["proposal-001", "proposal-001"],
        pending_memory_review_refs=["memory-candidate-001"],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_id.startswith("daily-workspace://")
    assert workspace.workspace_status == "operator_decision_required"
    assert workspace.mission_count == 2
    assert workspace.active_objective_count == 2
    assert workspace.active_work_item_count == 1
    assert workspace.active_artifact_count == 1
    assert workspace.open_checkpoint_count == 1
    assert workspace.pending_review_count == 2
    assert workspace.stale_mission_count == 1
    assert [str(item.mission_id) for item in workspace.missions] == [
        "mission-fresh",
        "mission-stale",
    ]
    assert workspace.missions[0].freshness_status == "fresh"
    assert workspace.missions[0].next_action_status == "ready"
    assert workspace.missions[1].freshness_status == "stale"
    assert workspace.missions[1].operator_attention_status == "blocked"
    assert workspace.next_operator_decision == (
        "review_evolution_proposal:proposal-001"
    )
    assert "resolve_blocked_mission:mission-stale" in workspace.next_decision_refs
    assert "review_stale_mission:mission-stale" in workspace.next_decision_refs
    assert workspace.ordering_policy == "updated_at_desc_no_priority_inference"
    assert workspace.read_only is True
    assert workspace.autonomous_resume_allowed is False
    assert workspace.autonomous_scheduling_allowed is False
    assert fresh.active_work_items == ["work-item://release/validate"]


def test_operational_service_builds_idle_workspace_without_inventing_work() -> None:
    service = OperationalService(
        artifact_dir=str(runtime_dir("operational-empty-workspace"))
    )

    workspace = service.build_daily_operator_workspace(
        mission_states=[],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_status == "idle"
    assert workspace.mission_count == 0
    assert workspace.next_decision_refs == []
    assert workspace.next_operator_decision is None
    assert workspace.evidence_refs == []


def test_operational_service_requires_decision_for_open_mission_without_next_action() -> None:
    workspace = OperationalService.build_daily_operator_workspace(
        mission_states=[
            MissionStateContract(
                mission_id=MissionId("mission-needs-next-action"),
                mission_goal="Define the next governed action",
                mission_status=MissionStatus.ACTIVE,
                checkpoints=[],
                updated_at="2026-07-17T09:00:00+00:00",
                objective_status="active",
            )
        ],
        generated_at="2026-07-17T10:00:00+00:00",
    )

    assert workspace.workspace_status == "operator_decision_required"
    assert workspace.missions[0].operator_attention_status == "decision_required"
    assert workspace.next_operator_decision == (
        "define_next_action:mission-needs-next-action"
    )


def test_operational_service_blocks_dispatch_above_autonomy_limit() -> None:
    temp_dir = runtime_dir("operational-autonomy-block")
    service = OperationalService(artifact_dir=str(temp_dir))
    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-autonomy-block"),
            request_id=RequestId("req-autonomy-block"),
            session_id=SessionId("sess-autonomy-block"),
            task_type="draft_plan",
            task_goal="Execute local operation",
            task_plan="attempt operation above autonomy limit",
            constraints=["bounded"],
            expected_output="text_brief",
            capability_decision_selected_mode="core_with_local_operation",
            max_autonomy_capability_mode="contained_guidance",
            effective_autonomy_level="assist_only",
        )
    )

    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
    assert "capability_above_autonomy_limit" in execution.operation_result.errors
    assert "autonomy_capability_above_limit" in (
        execution.operation_result.governance_flags
    )
    assert execution.operation_result.next_recommendation == (
        "request_human_confirmation"
    )


def test_operational_service_generates_text_artifact_for_supported_task() -> None:
    temp_dir = runtime_dir("operational-artifact")
    service = OperationalService(artifact_dir=str(temp_dir))
    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-1"),
            request_id=RequestId("req-1"),
            session_id=SessionId("sess-1"),
            task_type="draft_plan",
            task_goal="Plan milestone M3",
            task_plan="priorizar memoria persistente",
            constraints=["low-risk"],
            expected_output="text_brief",
            plan_summary="decompor milestone em etapas reversiveis",
            planned_steps=["definir objetivo", "listar etapas"],
            plan_risks=["sem risco material relevante"],
            plan_rationale="contexto=nenhum; apoio=baseline local",
            specialist_summary="encadear o plano em etapas pequenas",
            specialist_findings=["open_loop: fechar checkpoint principal"],
            mind_domain_specialist_contract_status="authoritative_chain",
            mind_domain_specialist_contract_summary=(
                "cadeia soberana autoritativa preserva mente_executiva -> "
                "estrategia_e_pensamento_sistemico -> strategy -> "
                "operational_planning_specialist"
            ),
            mind_domain_specialist_contract_chain=(
                "mente_executiva -> estrategia_e_pensamento_sistemico -> strategy -> "
                "operational_planning_specialist"
            ),
            mind_domain_specialist_active_specialist="operational_planning_specialist",
            mind_domain_specialist_consumer_mode="authoritative_specialist",
            mind_domain_specialist_framing_mode="route_and_specialist_locked",
            mind_domain_specialist_continuity_mode="preserve_authoritative_chain",
            specialist_hints=["operational_planning_specialist"],
            workflow_profile="strategic_direction_workflow",
            workflow_domain_route="strategy",
            workflow_objective="Plan milestone M3",
            workflow_expected_deliverables=[
                "tradeoff_map",
                "decision_criteria",
                "recommended_direction",
            ],
            workflow_telemetry_focus=[
                "tradeoff_clarity",
                "decision_trace",
                "domain_alignment",
            ],
            workflow_success_focus="direcao recomendada com criterios explicitos",
            workflow_response_focus="direcao recomendada, criterios e trade-offs dominantes",
            workflow_state="composed",
            workflow_governance_mode="core_mediated",
            workflow_steps=[
                "structure the goal and success criteria",
                "sequence the smallest safe steps",
                "emit checkpoints and the next safe action",
            ],
            workflow_checkpoints=["goal_structured", "steps_sequenced", "next_action_defined"],
            workflow_decision_points=[
                "goal_scope_confirmed",
                "step_sequence_validated",
                "next_action_governed",
            ],
            ecosystem_state_status="operational_state_attached",
            active_work_items=["mission_task:Plan milestone M3"],
            active_artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
            open_checkpoint_refs=[
                "workflow_checkpoint:goal_structured:pending",
                "workflow_checkpoint:steps_sequenced:pending",
            ],
            surface_presence=["surface:chat", "session:sess-1"],
            ecosystem_state_summary=(
                "work_items=1; artifacts=1; open_checkpoints=2; surfaces=2"
            ),
            project_ref="project://jarvis/persistent-objectives",
            objective_ref="objective://jarvis/persistent-objectives/mb-110",
            work_item_refs=["work-item://mb-110/contracts"],
            checkpoint_refs=["checkpoint://mb-110/contract-ready"],
            artifact_refs=["artifact://procedural/strategy/milestone-plan/v1"],
            objective_status="active",
            next_action_ref="next-action://mb-110/define-contract",
            success_criteria=["plano deve indicar a menor proxima acao segura"],
            smallest_safe_next_action="definir objetivo",
        )
    )
    assert isinstance(execution, OperationalExecution)
    assert execution.operation_result.status == OperationStatus.COMPLETED
    assert execution.artifact_results
    artifact_path = Path(execution.artifact_results[0].location_ref or "")
    assert artifact_path.exists()
    content = artifact_path.read_text(encoding="utf-8")
    assert "Plano deliberativo para" in content
    assert "Criterios de sucesso" in content
    assert "Workflow: strategic_direction_workflow" in content
    assert "Workflow domain route: strategy" in content
    assert (
        "Workflow deliverables: tradeoff_map; decision_criteria; recommended_direction"
        in content
    )
    assert (
        "Workflow telemetry focus: tradeoff_clarity; decision_trace; domain_alignment"
        in content
    )
    assert "Workflow success focus: direcao recomendada com criterios explicitos" in content
    assert (
        "Workflow response focus: direcao recomendada, criterios e trade-offs dominantes"
        in content
    )
    assert "Workflow steps:" in content
    assert "Workflow governance: core_mediated" in content
    assert "Workflow decision points:" in content
    assert "Mind-domain-specialist status: authoritative_chain" in content
    assert "Mind-domain-specialist consumer mode: authoritative_specialist" in content
    assert "Mind-domain-specialist framing mode: route_and_specialist_locked" in content
    assert "Ecosystem state status: operational_state_attached" in content
    assert "Active work items: mission_task:Plan milestone M3" in content
    assert "Open checkpoint refs:" in content
    assert "Surface presence: surface:chat; session:sess-1" in content
    assert "Project objective status: active" in content
    assert "Project ref: project://jarvis/persistent-objectives" in content
    assert "Objective ref: objective://jarvis/persistent-objectives/mb-110" in content
    assert "Next action ref: next-action://mb-110/define-contract" in content
    assert "Ajuste interno" in content
    assert execution.operation_result.workflow_domain_route == "strategy"
    assert execution.operation_result.workflow_state == "completed"
    assert execution.operation_result.workflow_completed_steps == [
        "structure the goal and success criteria",
        "sequence the smallest safe steps",
        "emit checkpoints and the next safe action",
    ]
    assert execution.operation_result.workflow_decisions == [
        "goal_scope_confirmed",
        "step_sequence_validated",
        "next_action_governed",
    ]
    assert "workflow_route:strategy" in execution.operation_result.checkpoints
    assert "workflow:goal_structured" in execution.operation_result.checkpoints
    assert "workflow_state:completed" in execution.operation_result.checkpoints
    assert execution.operation_result.ecosystem_state_status == (
        "operational_state_attached"
    )
    assert execution.operation_result.active_work_items == [
        "mission_task:Plan milestone M3"
    ]
    assert "artifact://procedural/strategy/milestone-plan/v1" in (
        execution.operation_result.active_artifact_refs
    )
    assert execution.operation_result.surface_presence == ["surface:chat", "session:sess-1"]
    assert execution.operation_result.project_ref == "project://jarvis/persistent-objectives"
    assert execution.operation_result.objective_ref == (
        "objective://jarvis/persistent-objectives/mb-110"
    )
    assert execution.operation_result.objective_status == "completed"
    assert execution.operation_result.next_action_ref == (
        "next-action://mb-110/define-contract"
    )


def test_operational_service_fails_for_unsupported_task() -> None:
    temp_dir = runtime_dir("operational-fail")
    service = OperationalService(artifact_dir=str(temp_dir))
    execution = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-2"),
            request_id=RequestId("req-2"),
            session_id=SessionId("sess-2"),
            task_type="unknown_task",
            task_goal="Do something unsupported",
            task_plan="n/a",
            constraints=["low-risk"],
            expected_output="text_brief",
        )
    )
    assert execution.operation_result.status == OperationStatus.FAILED
    assert execution.artifact_results == []
