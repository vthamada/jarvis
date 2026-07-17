"""Low-risk operational service with real text artifacts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from shared.autonomy_ladder import capability_mode_exceeds_autonomy_limit
from shared.contracts import (
    ArtifactResultContract,
    DailyOperatorWorkspaceContract,
    DailyWorkspaceMissionContract,
    MissionStateContract,
    OperationDispatchContract,
    OperationResultContract,
    WorkItemQueueContract,
)
from shared.types import ArtifactId, ArtifactStatus, MissionStatus, OperationStatus
from shared.work_item_policy import canonical_work_items_from_mission, order_work_items


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

    @classmethod
    def build_work_item_queue(
        cls,
        mission_state: MissionStateContract,
    ) -> WorkItemQueueContract:
        """Build a read-only governed queue without scheduling or execution."""

        ordered = order_work_items(canonical_work_items_from_mission(mission_state))
        mission_blocking_state = {
            MissionStatus.PAUSED: "mission_paused",
            MissionStatus.BLOCKED: "mission_blocked",
            MissionStatus.COMPLETED: "mission_completed",
            MissionStatus.CANCELED: "mission_canceled",
        }.get(mission_state.mission_status)
        if mission_blocking_state:
            ordered = [
                replace(item, blocking_state=mission_blocking_state)
                if item.work_item_status != "completed"
                else item
                for item in ordered
            ]
        executable_refs = [
            item.work_item_ref
            for item in ordered
            if item.work_item_status == "active" and item.blocking_state == "ready"
        ]
        blocked_refs = [
            item.work_item_ref
            for item in ordered
            if item.work_item_status != "completed"
            and item.work_item_ref not in executable_refs
        ]
        completed_refs = [
            item.work_item_ref
            for item in ordered
            if item.work_item_status == "completed"
        ]
        queue_status = (
            "empty"
            if not ordered
            else "ready_with_blocked"
            if executable_refs and blocked_refs
            else "ready"
            if executable_refs
            else "blocked"
            if blocked_refs
            else "completed"
        )
        return WorkItemQueueContract(
            mission_id=mission_state.mission_id,
            queue_status=queue_status,
            ordered_work_items=ordered,
            executable_work_item_refs=executable_refs,
            blocked_work_item_refs=blocked_refs,
            completed_work_item_refs=completed_refs,
            evidence_refs=[
                f"mission-state://{mission_state.mission_id}@{mission_state.updated_at}",
                *mission_state.checkpoint_refs,
            ],
        )

    @classmethod
    def build_daily_operator_workspace(
        cls,
        *,
        mission_states: list[MissionStateContract],
        pending_evolution_review_refs: list[str] | None = None,
        pending_memory_review_refs: list[str] | None = None,
        generated_at: str | None = None,
    ) -> DailyOperatorWorkspaceContract:
        """Build a read-only cross-session workspace from canonical state."""

        safe_generated_at = generated_at or cls.now()
        evolution_refs = cls._unique_values(pending_evolution_review_refs or [])
        memory_refs = cls._unique_values(pending_memory_review_refs or [])
        ordered_states = sorted(
            mission_states[:200],
            key=lambda state: str(state.mission_id),
        )
        ordered_states.sort(
            key=lambda state: cls._workspace_sort_timestamp(state.updated_at),
            reverse=True,
        )
        missions = [
            cls._daily_workspace_mission(state, generated_at=safe_generated_at)
            for state in ordered_states
        ]
        next_decision_refs = cls._unique_values(
            [f"review_evolution_proposal:{item}" for item in evolution_refs]
            + [f"review_memory_lifecycle:{item}" for item in memory_refs]
            + [
                decision
                for mission in missions
                for decision in mission.pending_decision_refs
            ]
        )
        requires_operator_decision = bool(evolution_refs or memory_refs) or any(
            mission.operator_attention_status
            in {"blocked", "paused", "stale", "unknown", "decision_required"}
            for mission in missions
        )
        ready_for_next_action = any(
            mission.next_action_status in {"ready", "derive_from_work_item"}
            for mission in missions
        )
        workspace_status = (
            "operator_decision_required"
            if requires_operator_decision
            else "ready_for_next_action"
            if ready_for_next_action
            else "idle"
        )
        evidence_refs = cls._unique_values(
            [evidence for mission in missions for evidence in mission.evidence_refs]
            + [f"evolution-review://{item}" for item in evolution_refs]
            + [f"memory-review://{item}" for item in memory_refs]
        )
        fingerprint = "|".join(
            [
                safe_generated_at,
                *(f"{mission.mission_id}@{mission.updated_at}" for mission in missions),
                *evolution_refs,
                *memory_refs,
            ]
        )
        return DailyOperatorWorkspaceContract(
            workspace_id=(
                "daily-workspace://"
                + sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
            ),
            workspace_status=workspace_status,
            generated_at=safe_generated_at,
            missions=missions,
            mission_count=len(missions),
            active_objective_count=sum(
                mission.objective_status not in {"completed", "canceled"}
                for mission in missions
            ),
            active_work_item_count=sum(
                len(mission.active_work_items) for mission in missions
            ),
            active_artifact_count=sum(
                len(mission.active_artifact_refs) for mission in missions
            ),
            open_checkpoint_count=sum(
                len(mission.open_checkpoint_refs) for mission in missions
            ),
            pending_review_count=len(evolution_refs) + len(memory_refs),
            stale_mission_count=sum(
                mission.freshness_status in {"stale", "unknown"}
                for mission in missions
            ),
            pending_evolution_review_refs=evolution_refs,
            pending_memory_review_refs=memory_refs,
            next_decision_refs=next_decision_refs,
            next_operator_decision=(next_decision_refs[0] if next_decision_refs else None),
            evidence_refs=evidence_refs,
        )

    @classmethod
    def _daily_workspace_mission(
        cls,
        state: MissionStateContract,
        *,
        generated_at: str,
    ) -> DailyWorkspaceMissionContract:
        mission_id = str(state.mission_id)
        work_item_queue = cls.build_work_item_queue(state)
        objective_status = state.objective_status or state.mission_status.value
        freshness_status, freshness_age_hours = cls._workspace_freshness(
            state.updated_at,
            generated_at,
        )
        blocked = (
            state.mission_status == MissionStatus.BLOCKED
            or objective_status == "blocked"
        )
        paused = state.mission_status == MissionStatus.PAUSED
        pending_decisions: list[str] = []
        if blocked:
            pending_decisions.append(f"resolve_blocked_mission:{mission_id}")
        elif paused:
            pending_decisions.append(f"review_paused_mission:{mission_id}")
        if freshness_status in {"stale", "unknown"}:
            pending_decisions.append(f"review_stale_mission:{mission_id}")
        if state.open_checkpoint_refs:
            pending_decisions.append(f"review_open_checkpoints:{mission_id}")
        if work_item_queue.blocked_work_item_refs:
            pending_decisions.append(f"review_blocked_work_items:{mission_id}")
        if not blocked and not paused:
            if state.next_action_ref:
                pending_decisions.append(
                    f"continue_mission:{mission_id}:{state.next_action_ref}"
                )
            elif work_item_queue.executable_work_item_refs:
                pending_decisions.append(
                    "select_work_item:"
                    + work_item_queue.executable_work_item_refs[0]
                )
            else:
                pending_decisions.append(f"define_next_action:{mission_id}")
        next_action_status = (
            "blocked"
            if blocked
            else "paused"
            if paused
            else "ready"
            if state.next_action_ref
            else "derive_from_work_item"
            if work_item_queue.executable_work_item_refs
            else "blocked_by_work_item"
            if work_item_queue.blocked_work_item_refs
            else "missing"
        )
        operator_attention_status = (
            "blocked"
            if blocked
            else "paused"
            if paused
            else freshness_status
            if freshness_status in {"stale", "unknown"}
            else "decision_required"
            if state.open_checkpoint_refs
            else "ready"
            if next_action_status in {"ready", "derive_from_work_item"}
            else "decision_required"
        )
        return DailyWorkspaceMissionContract(
            mission_id=state.mission_id,
            mission_goal=state.mission_goal,
            mission_status=state.mission_status,
            objective_status=objective_status,
            updated_at=state.updated_at,
            freshness_status=freshness_status,
            freshness_age_hours=freshness_age_hours,
            operator_attention_status=operator_attention_status,
            next_action_status=next_action_status,
            project_ref=state.project_ref,
            objective_ref=state.objective_ref,
            next_action_ref=state.next_action_ref,
            work_item_refs=list(state.work_item_refs),
            active_work_items=list(state.active_work_items),
            ordered_work_item_refs=[
                item.work_item_ref for item in work_item_queue.ordered_work_items
            ],
            executable_work_item_refs=list(
                work_item_queue.executable_work_item_refs
            ),
            blocked_work_item_refs=list(work_item_queue.blocked_work_item_refs),
            artifact_refs=list(state.artifact_refs),
            active_artifact_refs=list(state.active_artifact_refs),
            open_checkpoint_refs=list(state.open_checkpoint_refs),
            open_loops=list(state.open_loops),
            pending_decision_refs=cls._unique_values(pending_decisions),
            evidence_refs=[f"mission-state://{mission_id}@{state.updated_at}"],
        )

    @staticmethod
    def _workspace_freshness(
        updated_at: str,
        generated_at: str,
    ) -> tuple[str, float | None]:
        try:
            updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            generated = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=UTC)
            if generated.tzinfo is None:
                generated = generated.replace(tzinfo=UTC)
            age_hours = (generated - updated).total_seconds() / 3600
        except (TypeError, ValueError):
            return "unknown", None
        if age_hours < -0.084:
            return "unknown", None
        safe_age = round(max(0.0, age_hours), 2)
        if safe_age <= 24:
            return "fresh", safe_age
        if safe_age <= 72:
            return "aging", safe_age
        return "stale", safe_age

    @staticmethod
    def _workspace_sort_timestamp(value: str) -> float:
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return float("-inf")
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.timestamp()

    @staticmethod
    def _unique_values(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))

    def execute(self, dispatch: OperationDispatchContract) -> OperationalExecution:
        """Execute a low-risk operation using a deterministic local policy."""

        artifact_results: list[ArtifactResultContract] = []
        autonomy_violation = capability_mode_exceeds_autonomy_limit(
            selected_mode=dispatch.capability_decision_selected_mode,
            max_capability_mode=dispatch.max_autonomy_capability_mode,
        )
        governance_flags: list[str] = []
        errors: list[str] = []
        if autonomy_violation:
            content = (
                "Dispatch bloqueado: capability acima do limite de autonomia "
                "permitido."
            )
            status = OperationStatus.FAILED
            governance_flags.append("autonomy_capability_above_limit")
            errors.append("capability_above_autonomy_limit")
        elif dispatch.task_type == "draft_plan":
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
        active_artifact_refs = self._active_artifact_refs(dispatch, artifact_results)
        open_checkpoint_refs = [
            f"workflow_checkpoint:{checkpoint}:{checkpoint_status}"
            for checkpoint, checkpoint_status in workflow_checkpoint_state.items()
            if checkpoint_status != "completed"
        ]
        ecosystem_state_status = self._ecosystem_state_status(
            active_work_items=dispatch.active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=dispatch.surface_presence,
        )
        result = OperationResultContract(
            operation_id=dispatch.operation_id,
            status=status,
            outputs=outputs,
            timestamp=self.now(),
            errors=errors,
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
            ecosystem_state_status=ecosystem_state_status,
            active_work_items=list(dispatch.active_work_items),
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=list(dispatch.surface_presence),
            ecosystem_state_summary=self._ecosystem_state_summary(
                active_work_items=dispatch.active_work_items,
                active_artifact_refs=active_artifact_refs,
                open_checkpoint_refs=open_checkpoint_refs,
                surface_presence=dispatch.surface_presence,
            ),
            project_ref=dispatch.project_ref,
            objective_ref=dispatch.objective_ref,
            work_item_refs=list(dispatch.work_item_refs),
            checkpoint_refs=list(dispatch.checkpoint_refs),
            artifact_refs=self._project_artifact_refs(dispatch, artifact_results),
            objective_status=(
                "completed" if status == OperationStatus.COMPLETED else dispatch.objective_status
            ),
            next_action_ref=dispatch.next_action_ref,
            surface_id=dispatch.surface_id,
            surface_kind=dispatch.surface_kind,
            surface_session_id=dispatch.surface_session_id,
            surface_capability_scope=list(dispatch.surface_capability_scope),
            operator_identity_ref=dispatch.operator_identity_ref,
            canonical_user_ref=dispatch.canonical_user_ref,
            surface_continuity_status=dispatch.surface_continuity_status,
            next_recommendation=(
                "continue"
                if status == OperationStatus.COMPLETED
                else (
                    "request_human_confirmation"
                    if autonomy_violation
                    else "review_dispatch"
                )
            ),
            governance_flags=governance_flags,
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
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
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
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
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
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
        return (
            f"Analise deliberativa para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Rationale: {dispatch.plan_rationale or 'nao informado'}\n"
            f"Dominios sugeridos: {domains}\n"
            f"Criterios de sucesso: {success}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"Riscos mapeados: {risks}\n"
            f"{arbitration_lines}\n"
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
            f"{workflow_lines}\n"
            f"{workflow_decisions}\n"
        )

    @staticmethod
    def _build_general_content(dispatch: OperationDispatchContract) -> str:
        workflow_lines = OperationalService._workflow_lines(dispatch)
        workflow_decisions = OperationalService._workflow_decision_line(dispatch)
        arbitration_lines = OperationalService._mind_domain_specialist_lines(dispatch)
        ecosystem_lines = OperationalService._ecosystem_state_lines(dispatch)
        objective_lines = OperationalService._project_objective_lines(dispatch)
        return (
            f"Resposta deliberativa segura para: {dispatch.task_goal}\n\n"
            f"Resumo: {dispatch.plan_summary or dispatch.task_plan}\n"
            f"Orientacao principal: {dispatch.plan_rationale or 'sem rationale adicional'}\n"
            f"Proxima acao segura: "
            f"{dispatch.smallest_safe_next_action or 'preservar direcao segura'}\n"
            f"Ajuste interno: {dispatch.specialist_summary or 'sem ajuste interno adicional'}\n"
            f"{arbitration_lines}\n"
            f"{ecosystem_lines}\n"
            f"{objective_lines}\n"
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
    def _ecosystem_state_lines(dispatch: OperationDispatchContract) -> str:
        work_items = "; ".join(dispatch.active_work_items) or "none"
        artifact_refs = "; ".join(dispatch.active_artifact_refs) or "none"
        checkpoint_refs = "; ".join(dispatch.open_checkpoint_refs) or "none"
        surface_presence = "; ".join(dispatch.surface_presence) or "none"
        status = dispatch.ecosystem_state_status or "not_applicable"
        summary = dispatch.ecosystem_state_summary or "state not summarized"
        return (
            f"Ecosystem state status: {status}\n"
            f"Ecosystem state summary: {summary}\n"
            f"Active work items: {work_items}\n"
            f"Active artifact refs: {artifact_refs}\n"
            f"Open checkpoint refs: {checkpoint_refs}\n"
            f"Surface presence: {surface_presence}"
        )

    @staticmethod
    def _project_objective_lines(dispatch: OperationDispatchContract) -> str:
        work_items = "; ".join(dispatch.work_item_refs) or "none"
        checkpoints = "; ".join(dispatch.checkpoint_refs) or "none"
        artifacts = "; ".join(dispatch.artifact_refs) or "none"
        return (
            f"Project objective status: {dispatch.objective_status or 'not_applicable'}\n"
            f"Project ref: {dispatch.project_ref or 'none'}\n"
            f"Objective ref: {dispatch.objective_ref or 'none'}\n"
            f"Work item refs: {work_items}\n"
            f"Checkpoint refs: {checkpoints}\n"
            f"Artifact refs: {artifacts}\n"
            f"Next action ref: {dispatch.next_action_ref or 'none'}"
        )

    @staticmethod
    def _project_artifact_refs(
        dispatch: OperationDispatchContract,
        artifacts: list[ArtifactResultContract],
    ) -> list[str]:
        refs: list[str] = []
        for item in [
            *list(dispatch.artifact_refs),
            *(artifact.location_ref for artifact in artifacts if artifact.location_ref),
        ]:
            if item and item not in refs:
                refs.append(item)
        return refs


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
    def _active_artifact_refs(
        dispatch: OperationDispatchContract,
        artifact_results: list[ArtifactResultContract],
    ) -> list[str]:
        refs = list(dispatch.active_artifact_refs)
        for artifact in artifact_results:
            if artifact.location_ref and artifact.location_ref not in refs:
                refs.append(artifact.location_ref)
        return refs

    @staticmethod
    def _ecosystem_state_status(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        if not (
            active_work_items
            or active_artifact_refs
            or open_checkpoint_refs
            or surface_presence
        ):
            return "not_applicable"
        if surface_presence and active_work_items and (
            active_artifact_refs or open_checkpoint_refs
        ):
            return "operational_state_attached"
        return "partial_operational_state"

    @staticmethod
    def _ecosystem_state_summary(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        return (
            f"work_items={len(active_work_items)}; "
            f"artifacts={len(active_artifact_refs)}; "
            f"open_checkpoints={len(open_checkpoint_refs)}; "
            f"surfaces={len(surface_presence)}"
        )

    @staticmethod
    def _domain_line(domain_hints: list[str]) -> str:
        return ", ".join(domain_hints) if domain_hints else "assistencia_pessoal_e_operacional"

    @staticmethod
    def _risk_line(plan_risks: list[str], fallback: str) -> str:
        return ", ".join(plan_risks) if plan_risks else fallback

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
