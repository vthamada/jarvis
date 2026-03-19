"""Persistent memory service backed by canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from os import getenv
from uuid import uuid4

from memory_service.repository import StoredTurn, build_memory_repository
from shared.contracts import (
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
    recovered_items: list[str]


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
            requested_scopes=[MemoryClass.CONTEXTUAL, MemoryClass.EPISODIC],
            context_window=TimeWindow(label="current-session"),
            mission_id=contract.mission_id,
            user_id=contract.user_id,
            max_items=3,
            sensitivity_ceiling=RiskLevel.MODERATE,
        )
        recovered_items = self._compose_recovered_items(contract, recovery_contract.max_items or 3)
        return MemoryRecoveryResult(
            recovery_contract=recovery_contract,
            recovered_items=recovered_items,
        )

    def record_turn(
        self,
        contract: InputContract,
        intent: str,
        response_text: str,
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
            )
        )
        if contract.mission_id:
            self.repository.upsert_mission_state(
                self._build_mission_state(contract, record_contract.memory_record_id, intent)
            )
        return MemoryRecordResult(record_contract=record_contract)

    def get_mission_state(self, mission_id: str) -> MissionStateContract | None:
        """Expose the latest mission snapshot for validation and orchestration."""

        return self.repository.fetch_mission_state(mission_id)

    def _compose_recovered_items(self, contract: InputContract, limit: int) -> list[str]:
        recovered_items: list[str] = []
        summary = self.repository.fetch_context_summary(str(contract.session_id))
        if summary:
            recovered_items.append(f"context_summary={summary}")
        turns = self.repository.fetch_recent_turns(str(contract.session_id), max(limit, 3))
        recovered_items.extend(
            [
                (
                    f"user={turn.request_content} | intent={turn.intent} "
                    f"| response={turn.response_text}"
                )
                for turn in turns
            ]
        )
        if contract.mission_id:
            mission_state = self.repository.fetch_mission_state(str(contract.mission_id))
            if mission_state:
                recovered_items.append(
                    (
                        "mission_state="
                        f"{mission_state.mission_status.value}:{mission_state.mission_goal}"
                    )
                )
        return recovered_items[-limit:]

    def _build_mission_state(
        self,
        contract: InputContract,
        memory_record_id: MemoryRecordId,
        intent: str,
    ) -> MissionStateContract:
        mission_id = str(contract.mission_id)
        previous = self.repository.fetch_mission_state(mission_id)
        checkpoints = list(previous.checkpoints) if previous else []
        active_tasks = list(previous.active_tasks) if previous else []
        related_memories = list(previous.related_memories) if previous else []
        checkpoints.append(f"request:{contract.request_id}")
        active_tasks.append(intent)
        related_memories.append(str(memory_record_id))
        return MissionStateContract(
            mission_id=contract.mission_id,
            mission_goal=previous.mission_goal if previous else contract.content,
            mission_status=MissionStatus.ACTIVE,
            checkpoints=checkpoints[-5:],
            active_tasks=active_tasks[-5:],
            related_memories=related_memories[-5:],
            updated_at=self.now(),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
