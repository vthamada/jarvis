"""Minimal in-process memory service backed by shared canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from shared.contracts import InputContract, MemoryRecordContract, MemoryRecoveryContract
from shared.types import (
    MemoryClass,
    MemoryQueryId,
    MemoryRecordId,
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
    """Handles contextual continuity with a first in-process store."""

    name = "memory-service"

    def __init__(self) -> None:
        self.session_history: dict[str, list[str]] = {}

    def recover_for_input(self, contract: InputContract) -> MemoryRecoveryResult:
        """Recover a small contextual window for the current session."""

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
        recovered_items = self.session_history.get(str(contract.session_id), [])[-3:]
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
        """Persist a minimal episodic entry for the current turn."""

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
        entry = f"user={contract.content} | intent={intent} | response={response_text}"
        self.session_history.setdefault(str(contract.session_id), []).append(entry)
        return MemoryRecordResult(record_contract=record_contract)

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
