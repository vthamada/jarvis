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
            specialist_hints=["operational_planning_specialist"],
            workflow_profile="strategic_direction_workflow",
            workflow_domain_route="strategy",
            workflow_objective="Plan milestone M3",
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
    assert "Workflow steps:" in content
    assert "Workflow governance: core_mediated" in content
    assert "Workflow decision points:" in content
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
