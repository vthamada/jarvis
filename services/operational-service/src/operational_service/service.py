"""Low-risk operational service with real text artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from shared.contracts import ArtifactResultContract, OperationDispatchContract, OperationResultContract
from shared.types import ArtifactId, ArtifactStatus, OperationStatus


@dataclass
class OperationalExecution:
    """Structured result of an operational execution."""

    operation_result: OperationResultContract
    artifact_results: list[ArtifactResultContract]


class OperationalService:
    """Execute low-risk tasks and persist text artifacts."""

    name = "operational-service"

    def __init__(self, artifact_dir: str | None = None) -> None:
        resolved_dir = Path(artifact_dir) if artifact_dir else Path.cwd() / ".jarvis_runtime" / "artifacts"
        resolved_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir = resolved_dir

    def execute(self, dispatch: OperationDispatchContract) -> OperationalExecution:
        """Execute a low-risk operation using a deterministic local policy."""

        artifact_results: list[ArtifactResultContract] = []
        if dispatch.task_type == "draft_plan":
            content = self._build_plan_content(dispatch)
            status = OperationStatus.COMPLETED
        elif dispatch.task_type == "produce_analysis_brief":
            content = self._build_analysis_content(dispatch)
            status = OperationStatus.COMPLETED
        elif dispatch.task_type == "general_response":
            content = self._build_general_content(dispatch)
            status = OperationStatus.COMPLETED
        else:
            content = f"Task type nao suportado: {dispatch.task_type}"
            status = OperationStatus.FAILED

        outputs = [content.splitlines()[0]]
        if status == OperationStatus.COMPLETED:
            artifact_results.append(self._write_artifact(dispatch, content))
        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            artifacts=[artifact.location_ref for artifact in artifact_results if artifact.location_ref],
            checkpoints=["operational_execution_started", "operational_execution_finished"],
            next_recommendation=(
                "continue" if status == OperationStatus.COMPLETED else "review_dispatch"
            ),
            memory_record_hints=(["artifact_generated"] if artifact_results else ["dispatch_review_required"]),
        )
        return OperationalExecution(operation_result=result, artifact_results=artifact_results)

    def _write_artifact(
        self,
        dispatch: OperationDispatchContract,
        content: str,
    ) -> ArtifactResultContract:
        artifact_id = ArtifactId(f"artifact-{uuid4().hex[:8]}")
        target_dir = Path(dispatch.artifact_destination) if dispatch.artifact_destination else self.artifact_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = target_dir / f"{artifact_id}.md"
        artifact_path.write_text(content, encoding="utf-8")
        return ArtifactResultContract(
            artifact_id=artifact_id,
            artifact_type="text_document",
            artifact_status=ArtifactStatus.GENERATED,
            produced_by=self.name,
            timestamp=self.now(),
            location_ref=str(artifact_path),
            summary=content.splitlines()[0],
            format="text/markdown",
            request_id=dispatch.request_id,
        )

    @staticmethod
    def _build_plan_content(dispatch: OperationDispatchContract) -> str:
        return (
            f"Plano inicial para: {dispatch.task_goal}\n\n"
            f"Objetivo esperado: {dispatch.expected_output}\n"
            f"Plano executivo: {dispatch.task_plan}\n"
            f"Restricoes: {', '.join(dispatch.constraints)}\n"
            "1. Clarificar objetivo e criterio de aceite.\n"
            "2. Executar a menor etapa reversivel disponivel.\n"
            "3. Validar o resultado antes de expandir escopo.\n"
        )

    @staticmethod
    def _build_analysis_content(dispatch: OperationDispatchContract) -> str:
        return (
            f"Analise inicial estruturada para: {dispatch.task_goal}\n\n"
            f"Plano de analise: {dispatch.task_plan}\n"
            f"Dominios sugeridos: {', '.join(dispatch.domain_hints) if dispatch.domain_hints else 'assistencia_geral'}\n"
            "Observacoes:\n"
            "- contexto avaliado localmente;\n"
            "- trade-offs priorizados para baixo risco;\n"
            "- recomendacao final depende de confirmacao do objetivo.\n"
        )

    @staticmethod
    def _build_general_content(dispatch: OperationDispatchContract) -> str:
        return (
            f"Resposta operacional segura preparada para: {dispatch.task_goal}\n\n"
            f"Plano de apoio: {dispatch.task_plan}\n"
            "A saida foi produzida dentro do escopo local e reversivel do v1.\n"
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
