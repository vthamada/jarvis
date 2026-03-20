"""Persistent memory service backed by canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from uuid import uuid4

from memory_service.repository import StoredTurn, build_memory_repository
from shared.contracts import (
    DeliberativePlanContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    MissionStateContract,
    SpecialistContributionContract,
)
from shared.types import (
    MemoryClass,
    MemoryQueryId,
    MemoryRecordId,
    MissionStatus,
    PermissionDecision,
    RecoveryType,
    RiskLevel,
    TimeWindow,
)


@dataclass
class MemoryRecoveryResult:
    """Structured result for contextual recovery."""

    recovery_contract: MemoryRecoveryContract
    session_context: list[str]
    mission_hints: list[str]
    plan_hints: list[str]

    @property
    def recovered_items(self) -> list[str]:
        return [*self.session_context, *self.mission_hints, *self.plan_hints]


@dataclass
class MemoryRecordResult:
    """Structured result for memory recording."""

    record_contract: MemoryRecordContract


class MemoryService:
    """Handles contextual continuity with persistent episodic and mission memory."""

    name = "memory-service"

    def __init__(self, database_url: str | None = None) -> None:
        configured_url = database_url or getenv("DATABASE_URL")
        self.repository = build_memory_repository(configured_url)

    def recover_for_input(self, contract: InputContract) -> MemoryRecoveryResult:
        """Recover contextual, episodic, and mission hints for the current session."""

        recovery_contract = MemoryRecoveryContract(
            memory_query_id=MemoryQueryId(f"mem-query-{uuid4().hex[:8]}"),
            recovery_type=RecoveryType.CONTEXTUAL,
            session_id=contract.session_id,
            requested_scopes=[MemoryClass.CONTEXTUAL, MemoryClass.EPISODIC, MemoryClass.MISSION],
            context_window=TimeWindow(label="current-session"),
            mission_id=contract.mission_id,
            user_id=contract.user_id,
            max_items=4,
            sensitivity_ceiling=RiskLevel.MODERATE,
        )
        session_context, mission_hints, plan_hints = self._compose_recovered_items(
            contract,
            recovery_contract.max_items or 4,
        )
        return MemoryRecoveryResult(
            recovery_contract=recovery_contract,
            session_context=session_context,
            mission_hints=mission_hints,
            plan_hints=plan_hints,
        )

    def record_turn(
        self,
        contract: InputContract,
        intent: str,
        response_text: str,
        *,
        deliberative_plan: DeliberativePlanContract | None = None,
        specialist_contributions: list[SpecialistContributionContract] | None = None,
        governance_decision: PermissionDecision | None = None,
    ) -> MemoryRecordResult:
        """Persist a minimal episodic entry and refresh contextual continuity."""

        specialist_contributions = specialist_contributions or []
        open_loops = self._extract_open_loops(deliberative_plan, specialist_contributions)
        decision_frame = self._decision_frame(deliberative_plan)
        dominant_goal = deliberative_plan.goal if deliberative_plan else contract.content
        record_contract = MemoryRecordContract(
            memory_record_id=MemoryRecordId(f"mem-record-{uuid4().hex[:8]}"),
            record_type="interaction_turn",
            source_service=self.name,
            payload={
                "request_content": contract.content,
                "intent": intent,
                "response_text": response_text,
                "dominant_goal": dominant_goal,
                "decision_frame": decision_frame,
                "governance_decision": governance_decision.value if governance_decision else None,
                "open_loops": open_loops,
                "plan_summary": deliberative_plan.plan_summary if deliberative_plan else None,
                "plan_steps": deliberative_plan.steps if deliberative_plan else [],
                "recommended_task_type": (
                    deliberative_plan.recommended_task_type if deliberative_plan else None
                ),
                "requires_human_validation": (
                    deliberative_plan.requires_human_validation if deliberative_plan else False
                ),
                "tensions_considered": (
                    deliberative_plan.tensions_considered if deliberative_plan else []
                ),
                "specialist_hints": (
                    deliberative_plan.specialist_hints if deliberative_plan else []
                ),
                "specialist_resolution_summary": (
                    deliberative_plan.specialist_resolution_summary if deliberative_plan else None
                ),
                "specialist_summary": (
                    " | ".join(
                        contribution.recommendation for contribution in specialist_contributions
                    )
                    if specialist_contributions
                    else None
                ),
                "specialist_types": [
                    contribution.specialist_type for contribution in specialist_contributions
                ],
            },
            timestamp=self.now(),
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            user_id=contract.user_id,
            proposed_memory_class=MemoryClass.EPISODIC,
            sensitivity_hint=RiskLevel.LOW,
            promotion_candidate=False,
        )
        self.repository.record_turn(
            StoredTurn(
                session_id=str(contract.session_id),
                mission_id=str(contract.mission_id) if contract.mission_id else None,
                user_id=contract.user_id,
                request_content=contract.content,
                intent=intent,
                response_text=response_text,
                timestamp=record_contract.timestamp,
                plan_summary=deliberative_plan.plan_summary if deliberative_plan else None,
                plan_steps=list(deliberative_plan.steps) if deliberative_plan else [],
                recommended_task_type=(
                    deliberative_plan.recommended_task_type if deliberative_plan else None
                ),
            )
        )
        if contract.mission_id:
            mission_state = self._build_mission_state(
                contract,
                record_contract.memory_record_id,
                intent,
                deliberative_plan,
                open_loops=open_loops,
                decision_frame=decision_frame,
                governance_decision=governance_decision,
            )
            if mission_state is not None:
                self.repository.upsert_mission_state(mission_state)
        return MemoryRecordResult(record_contract=record_contract)

    def get_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Expose the latest mission snapshot for validation and orchestration."""

        return self.repository.fetch_mission_state(mission_id)

    def _compose_recovered_items(
        self,
        contract: InputContract,
        limit: int,
    ) -> tuple[list[str], list[str], list[str]]:
        session_context: list[str] = []
        mission_hints: list[str] = []
        plan_hints: list[str] = []
        summary = self.repository.fetch_context_summary(str(contract.session_id))
        if summary:
            session_context.append(f"context_summary={summary}")
        turns = self.repository.fetch_recent_turns(str(contract.session_id), max(limit, 3))
        for turn in turns:
            session_context.append(
                "user="
                f"{turn.request_content} | intent={turn.intent} | "
                f"response={turn.response_text}"
            )
            if turn.plan_summary:
                plan_hints.append(f"prior_plan={turn.plan_summary}")
            if turn.plan_steps:
                plan_hints.append(f"prior_steps={' ; '.join(turn.plan_steps[:3])}")
        if contract.mission_id:
            mission_state = self.repository.fetch_mission_state(str(contract.mission_id))
            if mission_state:
                if mission_state.identity_continuity_brief:
                    mission_hints.append(
                        f"identity_continuity_brief={mission_state.identity_continuity_brief}"
                    )
                if mission_state.open_loops:
                    mission_hints.append(f"open_loops={';'.join(mission_state.open_loops[:3])}")
                if mission_state.semantic_brief:
                    mission_hints.append(f"mission_semantic_brief={mission_state.semantic_brief}")
                mission_hints.append(f"mission_goal={mission_state.mission_goal}")
                if mission_state.last_recommendation:
                    mission_hints.append(
                        f"mission_recommendation={mission_state.last_recommendation}"
                    )
                if mission_state.last_decision_frame:
                    mission_hints.append(f"last_decision_frame={mission_state.last_decision_frame}")
                if mission_state.semantic_focus:
                    mission_hints.append(
                        f"mission_focus={','.join(mission_state.semantic_focus[:3])}"
                    )
                mission_hints.append(
                    f"mission_state={mission_state.mission_status.value}:{','.join(mission_state.active_tasks[-3:])}"
                )
                if mission_state.recent_plan_steps:
                    mission_hints.append(
                        f"mission_steps={' ; '.join(mission_state.recent_plan_steps[:3])}"
                    )
        return session_context[-limit:], mission_hints[:8], plan_hints[-2:]

    def _build_mission_state(
        self,
        contract: InputContract,
        memory_record_id: MemoryRecordId,
        intent: str,
        deliberative_plan: DeliberativePlanContract | None,
        *,
        open_loops: list[str],
        decision_frame: str,
        governance_decision: PermissionDecision | None,
    ) -> MissionStateContract | None:
        mission_id = str(contract.mission_id)
        previous = self.repository.fetch_mission_state(mission_id)
        accepted = governance_decision not in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }
        if previous is None and not accepted:
            return None

        checkpoints = list(previous.checkpoints) if previous else []
        active_tasks = list(previous.active_tasks) if previous else []
        related_memories = list(previous.related_memories) if previous else []
        related_artifacts = list(previous.related_artifacts) if previous else []
        recent_plan_steps = list(previous.recent_plan_steps) if previous else []
        semantic_focus = list(previous.semantic_focus) if previous else []
        checkpoints.append(f"request:{contract.request_id}")
        related_memories.append(str(memory_record_id))
        if accepted:
            active_tasks.append(intent)
            if deliberative_plan:
                recent_plan_steps = list(deliberative_plan.steps[-3:])
                for domain in deliberative_plan.active_domains:
                    if domain not in semantic_focus:
                        semantic_focus.append(domain)
            if intent not in semantic_focus:
                semantic_focus.append(intent)

        mission_goal = previous.mission_goal if previous else contract.content
        last_recommendation = (
            deliberative_plan.plan_summary
            if accepted and deliberative_plan
            else (previous.last_recommendation if previous else None)
        )
        semantic_brief = self._build_semantic_brief(
            mission_goal=mission_goal,
            intent=intent,
            semantic_focus=semantic_focus,
            deliberative_plan=deliberative_plan if accepted else None,
            previous=previous,
        )
        persisted_open_loops = (
            list(previous.open_loops)
            if previous and not accepted
            else open_loops[:3]
        )
        persisted_frame = (
            previous.last_decision_frame
            if previous and not accepted
            else decision_frame
        )
        identity_continuity_brief = self._build_identity_continuity_brief(
            mission_goal=mission_goal,
            open_loops=persisted_open_loops,
            decision_frame=persisted_frame or decision_frame,
            recommendation=last_recommendation,
            previous=previous,
        )
        return MissionStateContract(
            mission_id=contract.mission_id,
            mission_goal=mission_goal,
            mission_status=MissionStatus.ACTIVE,
            checkpoints=checkpoints[-5:],
            active_tasks=active_tasks[-5:],
            related_memories=related_memories[-5:],
            related_artifacts=related_artifacts[-5:],
            recent_plan_steps=recent_plan_steps,
            last_recommendation=last_recommendation,
            semantic_brief=semantic_brief,
            semantic_focus=semantic_focus[-4:],
            identity_continuity_brief=identity_continuity_brief,
            open_loops=persisted_open_loops,
            last_decision_frame=persisted_frame,
            updated_at=self.now(),
        )

    def _build_semantic_brief(
        self,
        *,
        mission_goal: str,
        intent: str,
        semantic_focus: list[str],
        deliberative_plan: DeliberativePlanContract | None,
        previous: MissionStateContract | None,
    ) -> str:
        focus_hint = ", ".join(semantic_focus[:3]) if semantic_focus else intent
        if deliberative_plan:
            recommendation = deliberative_plan.plan_summary
            return f"objetivo={mission_goal}; foco={focus_hint}; recomendacao={recommendation}"
        if previous and previous.semantic_brief:
            return previous.semantic_brief
        return (
            f"objetivo={mission_goal}; foco={focus_hint}; "
            "recomendacao=persistir continuidade segura"
        )

    @staticmethod
    def _build_identity_continuity_brief(
        *,
        mission_goal: str,
        open_loops: list[str],
        decision_frame: str,
        recommendation: str | None,
        previous: MissionStateContract | None,
    ) -> str:
        focus = open_loops[0] if open_loops else "consolidar a proxima decisao segura"
        if recommendation:
            return (
                f"objetivo={mission_goal}; prioridade={focus}; "
                f"frame={decision_frame}; ultimo_ajuste={recommendation}"
            )
        if previous and previous.identity_continuity_brief:
            return previous.identity_continuity_brief
        return f"objetivo={mission_goal}; prioridade={focus}; frame={decision_frame}"

    @staticmethod
    def _extract_open_loops(
        deliberative_plan: DeliberativePlanContract | None,
        specialist_contributions: list[SpecialistContributionContract],
    ) -> list[str]:
        if deliberative_plan and deliberative_plan.open_loops:
            return list(deliberative_plan.open_loops[:3])
        loops: list[str] = []
        for contribution in specialist_contributions:
            for finding in contribution.findings:
                if finding.startswith("open_loop:"):
                    loop = finding.removeprefix("open_loop:").strip()
                    if loop and loop not in loops:
                        loops.append(loop)
        if not loops and deliberative_plan and deliberative_plan.continuity_action == "continuar":
            loops.append(deliberative_plan.goal)
        return loops[:3]

    @staticmethod
    def _decision_frame(deliberative_plan: DeliberativePlanContract | None) -> str:
        if not deliberative_plan:
            return "clarification"
        if deliberative_plan.recommended_task_type == "produce_analysis_brief":
            return "analysis"
        if deliberative_plan.recommended_task_type == "draft_plan":
            return "planning"
        if deliberative_plan.requires_human_validation:
            return "clarification"
        return "execution"

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
