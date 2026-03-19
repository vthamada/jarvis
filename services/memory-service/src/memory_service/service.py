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
)
from shared.types import (
    MemoryClass,
    MemoryQueryId,
    MemoryRecordId,
    MissionStatus,
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
    ) -> MemoryRecordResult:
        """Persist a minimal episodic entry and refresh contextual continuity."""

        record_contract = MemoryRecordContract(
            memory_record_id=MemoryRecordId(f"mem-record-{uuid4().hex[:8]}"),
            record_type="interaction_turn",
            source_service=self.name,
            payload={
                "request_content": contract.content,
                "intent": intent,
                "response_text": response_text,
                "plan_summary": deliberative_plan.plan_summary if deliberative_plan else None,
                "plan_steps": deliberative_plan.steps if deliberative_plan else [],
                "recommended_task_type": (
                    deliberative_plan.recommended_task_type if deliberative_plan else None
                ),
                "requires_human_validation": (
                    deliberative_plan.requires_human_validation if deliberative_plan else False
                ),
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
            self.repository.upsert_mission_state(
                self._build_mission_state(
                    contract, record_contract.memory_record_id, intent, deliberative_plan
                )
            )
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
                f"user={turn.request_content} | intent={turn.intent} | "
                f"response={turn.response_text}"
            )
            if turn.plan_summary:
                plan_hints.append(f"prior_plan={turn.plan_summary}")
            if turn.plan_steps:
                plan_hints.append(f"prior_steps={' ; '.join(turn.plan_steps[:3])}")
        if contract.mission_id:
            mission_state = self.repository.fetch_mission_state(str(contract.mission_id))
            if mission_state:
                mission_hints.append(f"mission_goal={mission_state.mission_goal}")
                mission_hints.append(
                    f"mission_state={mission_state.mission_status.value}:{','.join(mission_state.active_tasks[-3:])}"
                )
                if mission_state.last_recommendation:
                    mission_hints.append(
                        f"mission_recommendation={mission_state.last_recommendation}"
                    )
                if mission_state.recent_plan_steps:
                    mission_hints.append(
                        f"mission_steps={' ; '.join(mission_state.recent_plan_steps[:3])}"
                    )
        return session_context[-limit:], mission_hints[-2:], plan_hints[-2:]

    def _build_mission_state(
        self,
        contract: InputContract,
        memory_record_id: MemoryRecordId,
        intent: str,
        deliberative_plan: DeliberativePlanContract | None,
    ) -> MissionStateContract:
        mission_id = str(contract.mission_id)
        previous = self.repository.fetch_mission_state(mission_id)
        checkpoints = list(previous.checkpoints) if previous else []
        active_tasks = list(previous.active_tasks) if previous else []
        related_memories = list(previous.related_memories) if previous else []
        related_artifacts = list(previous.related_artifacts) if previous else []
        recent_plan_steps = list(previous.recent_plan_steps) if previous else []
        checkpoints.append(f"request:{contract.request_id}")
        active_tasks.append(intent)
        related_memories.append(str(memory_record_id))
        if deliberative_plan:
            recent_plan_steps = list(deliberative_plan.steps[-3:])
        return MissionStateContract(
            mission_id=contract.mission_id,
            mission_goal=previous.mission_goal if previous else contract.content,
            mission_status=MissionStatus.ACTIVE,
            checkpoints=checkpoints[-5:],
            active_tasks=active_tasks[-5:],
            related_memories=related_memories[-5:],
            related_artifacts=related_artifacts[-5:],
            recent_plan_steps=recent_plan_steps,
            last_recommendation=(
                deliberative_plan.plan_summary
                if deliberative_plan
                else (previous.last_recommendation if previous else None)
            ),
            updated_at=self.now(),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
