"""Low-risk operational service with real text artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from shared.contracts import (
    ArtifactResultContract,
    OperationDispatchContract,
    OperationResultContract,
)
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
        resolved_dir = (
            Path(artifact_dir) if artifact_dir else Path.cwd() / ".jarvis_runtime" / "artifacts"
        )
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

        outputs = [dispatch.plan_summary or content.splitlines()[0]]
        if status == OperationStatus.COMPLETED:
            artifact_results.append(self._write_artifact(dispatch, content))
        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            artifacts=[
                artifact.location_ref for artifact in artifact_results if artifact.location_ref
            ],
            checkpoints=["operational_execution_started", "operational_execution_finished"],
            next_recommendation=(
                "continue" if status == OperationStatus.COMPLETED else "review_dispatch"
            ),
            memory_record_hints=(
                ["artifact_generated", dispatch.plan_summary or "plan_executed"]
                if artifact_results
                else ["dispatch_review_required"]
            ),
        )
        return OperationalExecution(operation_result=result, artifact_results=artifact_results)

    def _write_artifact(
        self,
        dispatch: OperationDispatchContract,
        content: str,
    ) -> ArtifactResultContract:
        artifact_id = ArtifactId(f"artifact-{uuid4().hex[:8]}")
        target_dir = (
            Path(dispatch.artifact_destination)
            if dispatch.artifact_destination
            else self.artifact_dir
        )
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
            summary=dispatch.plan_summary or content.splitlines()[0],
            format="text/markdown",
            request_id=dispatch.request_id,
        )

    @staticmethod
    def _build_plan_content(dispatch: OperationDispatchContract) -> str:
        steps = (
            "\n".join(
                f"{index}. {step}" for index, step in enumerate(dispatch.planned_steps, start=1)
            )
            or "1. Revisar objetivo e confirmar proxima acao segura."
        )
        constraints = ", ".join(dispatch.constraints)
        risks = OperationalService._risk_line(
            dispatch.plan_risks,
            "sem risco material relevante",
        )
        specialists = OperationalService._specialist_line(dispatch.specialist_hints)
        specialist_summary = dispatch.specialist_summary or "sem resumo especializado adicional"
        findings = OperationalService._specialist_findings(dispatch.specialist_findings)
        return (
            f"Plano deliberativo para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Restricoes: {constraints}\n"
            f"Riscos: {risks}\n"
            f"Especializacao subordinada: {specialists}\n"
            f"Resumo especializado: {specialist_summary}\n"
            f"Achados especializados: {findings}\n\n"
            f"Etapas:\n{steps}\n"
        )

    @staticmethod
    def _build_analysis_content(dispatch: OperationDispatchContract) -> str:
        domains = OperationalService._domain_line(dispatch.domain_hints)
        risks = OperationalService._risk_line(
            dispatch.plan_risks,
            "nenhum relevante no escopo local",
        )
        specialists = OperationalService._specialist_line(dispatch.specialist_hints)
        specialist_summary = dispatch.specialist_summary or "sem resumo especializado adicional"
        findings = OperationalService._specialist_findings(dispatch.specialist_findings)
        return (
            f"Analise deliberativa para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Dominios sugeridos: {domains}\n"
            f"Especializacao subordinada: {specialists}\n"
            f"Resumo especializado: {specialist_summary}\n"
            f"Achados especializados: {findings}\n"
            f"Riscos mapeados: {risks}\n"
        )

    @staticmethod
    def _build_general_content(dispatch: OperationDispatchContract) -> str:
        specialists = OperationalService._specialist_line(dispatch.specialist_hints)
        specialist_summary = dispatch.specialist_summary or "sem resumo especializado adicional"
        findings = OperationalService._specialist_findings(dispatch.specialist_findings)
        return (
            f"Resposta deliberativa segura para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Orientacao principal: {dispatch.plan_rationale or 'sem rationale adicional'}\n"
            f"Especializacao subordinada: {specialists}\n"
            f"Resumo especializado: {specialist_summary}\n"
            f"Achados especializados: {findings}\n"
            "A saida foi produzida dentro do escopo local e reversivel do v1.\n"
        )

    @staticmethod
    def _domain_line(domain_hints: list[str]) -> str:
        return ", ".join(domain_hints) if domain_hints else "assistencia_geral"

    @staticmethod
    def _risk_line(plan_risks: list[str], fallback: str) -> str:
        return ", ".join(plan_risks) if plan_risks else fallback

    @staticmethod
    def _specialist_line(specialist_hints: list[str]) -> str:
        if specialist_hints:
            return ", ".join(specialist_hints)
        return "nenhum apoio especializado adicional"

    @staticmethod
    def _specialist_findings(specialist_findings: list[str]) -> str:
        if specialist_findings:
            return "; ".join(specialist_findings[:3])
        return "nenhum achado especializado adicional"

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
