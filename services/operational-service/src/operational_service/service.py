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
        workflow_checkpoint_tokens = [
            f"workflow:{item}" for item in dispatch.workflow_checkpoints
        ] or [
            "workflow:composed",
            "workflow:executed",
        ]
        workflow_state = "completed" if status == OperationStatus.COMPLETED else "failed"
        workflow_completed_steps = (
            list(dispatch.workflow_steps) if status == OperationStatus.COMPLETED else []
        )
        workflow_checkpoint_state = self._workflow_checkpoint_state(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
        )
        workflow_pending_checkpoints = [
            checkpoint
            for checkpoint, checkpoint_status in workflow_checkpoint_state.items()
            if checkpoint_status != "completed"
        ]
        workflow_resume_status, workflow_resume_point = self._workflow_resume_outcome(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
            pending_checkpoints=workflow_pending_checkpoints,
        )
        workflow_decisions = self._workflow_decisions(
            dispatch,
            successful=(status == OperationStatus.COMPLETED),
        )
        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            artifacts=[
                artifact.location_ref for artifact in artifact_results if artifact.location_ref
            ],
            checkpoints=[
                "operational_execution_started",
                f"workflow_route:{dispatch.workflow_domain_route or 'fallback'}",
                f"workflow_state:{dispatch.workflow_state or 'composed'}",
                f"workflow_resume_status:{dispatch.workflow_resume_status or 'fresh_start'}",
                "workflow_state:executing",
                *workflow_checkpoint_tokens,
                f"workflow_state:{workflow_state}",
                f"workflow_resume_outcome:{workflow_resume_status}",
                "operational_execution_finished",
            ],
            workflow_domain_route=dispatch.workflow_domain_route,
            workflow_state=workflow_state,
            workflow_completed_steps=workflow_completed_steps,
            workflow_decisions=workflow_decisions,
            workflow_checkpoint_state=workflow_checkpoint_state,
            workflow_pending_checkpoints=workflow_pending_checkpoints,
            workflow_resume_point=workflow_resume_point,
            workflow_resume_status=workflow_resume_status,
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
        success = "; ".join(dispatch.success_criteria[:3]) or (
            "manter resposta coerente e reversivel"
        )
        internal_alignment = dispatch.specialist_summary or "sem ajuste interno adicional"
        next_action = dispatch.smallest_safe_next_action or "preservar a menor proxima acao segura"
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        return (
            f"Plano deliberativo para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Criterios de sucesso: {success}\n"
            f"Proxima acao segura: {next_action}\n"
            f"Restricoes: {constraints}\n"
            f"Riscos: {risks}\n"
            f"Ajuste interno: {internal_alignment}\n"
            f"{arbitration_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
            f"Etapas:\n{steps}\n"
        )

    @staticmethod
    def _build_analysis_content(dispatch: OperationDispatchContract) -> str:
        domains = OperationalService._domain_line(dispatch.domain_hints)
        risks = OperationalService._risk_line(
            dispatch.plan_risks,
            "nenhum relevante no escopo local",
        )
        success = "; ".join(dispatch.success_criteria[:3]) or ("explicitar a melhor recomendacao")
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        return (
            f"Analise deliberativa para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Dominios sugeridos: {domains}\n"
            f"Criterios de sucesso: {success}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"Riscos mapeados: {risks}\n"
            f"{arbitration_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
        )

    @staticmethod
    def _build_general_content(dispatch: OperationDispatchContract) -> str:
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        return (
            f"Resposta deliberativa segura para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Orientacao principal: {dispatch.plan_rationale or 'sem rationale adicional'}\n"
            f"Proxima acao segura: "
            f"{dispatch.smallest_safe_next_action or 'preservar direcao segura'}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"{arbitration_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
            "A saida foi produzida dentro do escopo local e reversivel do v1.\n"
        )

    @staticmethod
    def _mind_domain_specialist_lines(dispatch: OperationDispatchContract) -> str:
        status = dispatch.mind_domain_specialist_contract_status or "not_applicable"
        summary = (
            dispatch.mind_domain_specialist_contract_summary
            or "contrato nao explicitado"
        )
        chain = dispatch.mind_domain_specialist_contract_chain or "none"
        consumer_mode = dispatch.mind_domain_specialist_consumer_mode or "not_defined"
        framing_mode = dispatch.mind_domain_specialist_framing_mode or "not_defined"
        continuity_mode = dispatch.mind_domain_specialist_continuity_mode or "not_defined"
        return (
            f"Mind-domain-specialist status: {status}\n"
            f"Mind-domain-specialist summary: {summary}\n"
            f"Mind-domain-specialist chain: {chain}\n"
            f"Mind-domain-specialist consumer mode: {consumer_mode}\n"
            f"Mind-domain-specialist framing mode: {framing_mode}\n"
            f"Mind-domain-specialist continuity mode: {continuity_mode}"
        )


    @staticmethod
    def _workflow_lines(dispatch: OperationDispatchContract) -> str:
        if not dispatch.workflow_profile:
            return "Workflow: not_defined"
        objective = dispatch.workflow_objective or dispatch.task_goal
        deliverables = "; ".join(dispatch.workflow_expected_deliverables) or "none"
        telemetry_focus = "; ".join(dispatch.workflow_telemetry_focus) or "none"
        steps = "; ".join(dispatch.workflow_steps) or "none"
        governance_mode = dispatch.workflow_governance_mode or "not_defined"
        return (
            f"Workflow: {dispatch.workflow_profile}\n"
            f"Workflow domain route: {dispatch.workflow_domain_route or 'fallback'}\n"
            f"Objetivo do workflow: {objective}\n"
            f"Workflow deliverables: {deliverables}\n"
            f"Workflow telemetry focus: {telemetry_focus}\n"
            f"Workflow success focus: {dispatch.workflow_success_focus or 'not_defined'}\n"
            f"Workflow response focus: {dispatch.workflow_response_focus or 'not_defined'}\n"
            f"Workflow state inicial: {dispatch.workflow_state or 'composed'}\n"
            f"Workflow governance: {governance_mode}\n"
            f"Workflow steps: {steps}"
        )

    @staticmethod
    def _workflow_decision_line(dispatch: OperationDispatchContract) -> str:
        decision_points = "; ".join(dispatch.workflow_decision_points) or "none"
        return f"Workflow decision points: {decision_points}"

    @staticmethod
    def _workflow_decisions(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
    ) -> list[str]:
        decision_points = list(dispatch.workflow_decision_points)
        if not successful:
            return decision_points[:1]
        return decision_points

    @staticmethod
    def _workflow_checkpoint_state(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
    ) -> dict[str, str]:
        if not dispatch.workflow_checkpoints:
            return {}
        if successful:
            return {checkpoint: "completed" for checkpoint in dispatch.workflow_checkpoints}
        state = dict(dispatch.workflow_checkpoint_state)
        if not state:
            return {}
        first_checkpoint = dispatch.workflow_checkpoints[0]
        state[first_checkpoint] = "completed"
        for checkpoint in dispatch.workflow_checkpoints[1:]:
            state[checkpoint] = "pending"
        return state

    @staticmethod
    def _workflow_resume_outcome(
        dispatch: OperationDispatchContract,
        *,
        successful: bool,
        pending_checkpoints: list[str],
    ) -> tuple[str, str | None]:
        resume_point = dispatch.workflow_resume_point or dispatch.smallest_safe_next_action
        if not successful:
            return ("resume_blocked", resume_point)
        if dispatch.workflow_resume_status == "resume_available":
            return ("resumed_from_checkpoint", resume_point)
        if dispatch.requires_human_validation and resume_point:
            return ("checkpointed_for_manual_resume", resume_point)
        if resume_point or pending_checkpoints:
            return ("checkpointed_for_followup", resume_point)
        return ("completed_without_resume", None)

    @staticmethod
    def _domain_line(domain_hints: list[str]) -> str:
        return ", ".join(domain_hints) if domain_hints else "assistencia_pessoal_e_operacional"

    @staticmethod
    def _risk_line(plan_risks: list[str], fallback: str) -> str:
        return ", ".join(plan_risks) if plan_risks else fallback

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
