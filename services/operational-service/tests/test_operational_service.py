from operational_service.service import OperationalExecution, OperationalService
from shared.contracts import OperationDispatchContract
from shared.types import OperationId, OperationStatus, RequestId


def test_operational_service_name() -> None:
    assert OperationalService.name == "operational-service"


def test_operational_service_executes_supported_task() -> None:
    service = OperationalService()
    result = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-1"),
            request_id=RequestId("req-1"),
            task_type="draft_plan",
            task_goal="create an initial sprint plan",
            task_plan="generate a short plan",
            constraints=["low-risk"],
            expected_output="text_brief",
        )
    )

    assert isinstance(result, OperationalExecution)
    assert result.operation_result.status == OperationStatus.COMPLETED
    assert "Plano inicial" in result.operation_result.outputs[0]



def test_operational_service_fails_unknown_task_type() -> None:
    service = OperationalService()
    result = service.execute(
        OperationDispatchContract(
            operation_id=OperationId("op-2"),
            request_id=RequestId("req-2"),
            task_type="unsupported_task",
            task_goal="unknown",
            task_plan="unknown",
            constraints=["low-risk"],
            expected_output="text_brief",
        )
    )

    assert result.operation_result.status == OperationStatus.FAILED
    assert "nao suportado" in result.operation_result.outputs[0]
