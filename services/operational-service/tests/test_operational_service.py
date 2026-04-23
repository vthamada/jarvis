from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from operational_service.service import OperationalExecution, OperationalService

from shared.contracts import OperationDispatchContract
from shared.types import OperationId, OperationStatus, RequestId, SessionId


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_operational_service_name() -> None:
    assert OperationalService.name == "operational-service"


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
