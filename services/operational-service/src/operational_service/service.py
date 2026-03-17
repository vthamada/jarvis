"""Minimal low-risk operational service backed by shared canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from shared.contracts import OperationDispatchContract, OperationResultContract
from shared.types import OperationStatus


@dataclass
class OperationalExecution:
    """Structured result of an operational execution."""

    operation_result: OperationResultContract


class OperationalService:
    """Executes the first safe operational tasks."""

    name = "operational-service"

    def execute(self, dispatch: OperationDispatchContract) -> OperationalExecution:
        """Execute a low-risk operation using a deterministic local policy."""

        if dispatch.task_type == "draft_plan":
            outputs = [f"Plano inicial gerado para: {dispatch.task_goal}"]
            status = OperationStatus.COMPLETED
        elif dispatch.task_type == "produce_analysis_brief":
            outputs = [f"Analise inicial estruturada para: {dispatch.task_goal}"]
            status = OperationStatus.COMPLETED
        elif dispatch.task_type == "general_response":
            outputs = [f"Resposta operacional segura preparada para: {dispatch.task_goal}"]
            status = OperationStatus.COMPLETED
        else:
            outputs = [f"Task type nao suportado: {dispatch.task_type}"]
            status = OperationStatus.FAILED

        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            checkpoints=["operational_execution_finished"],
            next_recommendation=(
                "continue" if status == OperationStatus.COMPLETED else "review_dispatch"
            ),
        )
        return OperationalExecution(operation_result=result)

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
