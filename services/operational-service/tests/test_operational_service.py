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
            task_plan="priorizar memória persistente",
            constraints=["low-risk"],
            expected_output="text_brief",
            plan_summary="decompor milestone em etapas reversiveis",
            planned_steps=["definir objetivo", "listar etapas"],
            plan_risks=["sem risco material relevante"],
            plan_rationale="contexto=nenhum; apoio=baseline local",
            specialist_summary="especialista_planejamento_operacional: executar em etapas pequenas",
            specialist_findings=["priorizar a menor ação segura antes de expandir escopo"],
            specialist_hints=["especialista_planejamento_operacional"],
        )
    )

    assert isinstance(execution, OperationalExecution)
    assert execution.operation_result.status == OperationStatus.COMPLETED
    assert execution.artifact_results
    artifact_path = Path(execution.artifact_results[0].location_ref or "")
    assert artifact_path.exists()
    content = artifact_path.read_text(encoding="utf-8")
    assert "Plano deliberativo para" in content
    assert "Especializacao subordinada" in content
    assert "Achados especializados" in content


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
