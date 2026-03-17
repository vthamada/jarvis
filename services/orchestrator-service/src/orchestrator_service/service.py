"""Minimal orchestrator flow built on top of shared canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from operational_service.service import OperationalService
from shared.contracts import (
    GovernanceCheckContract,
    GovernanceDecisionContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    OperationDispatchContract,
    OperationResultContract,
)
from shared.events import InternalEventEnvelope
from shared.state import SYSTEM_IDENTITY
from shared.types import OperationId, PermissionDecision, RequestId


HIGH_RISK_KEYWORDS = (
    "delete",
    "drop",
    "destroy",
    "excluir",
    "apagar",
    "deletar",
    "remover",
)


@dataclass
class OrchestratorResponse:
    """Structured result of the first functional orchestrator pass."""

    request_id: str
    session_id: str
    intent: str
    response_text: str
    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract
    memory_recovery: MemoryRecoveryContract
    memory_record: MemoryRecordContract
    recovered_context: list[str]
    operation_dispatch: OperationDispatchContract | None = None
    operation_result: OperationResultContract | None = None
    events: list[InternalEventEnvelope] = field(default_factory=list)


class OrchestratorService:
    """Coordinates the first minimal request flow."""

    name = "orchestrator-service"

    def __init__(
        self,
        governance_service: GovernanceService | None = None,
        memory_service: MemoryService | None = None,
        operational_service: OperationalService | None = None,
    ) -> None:
        self.governance_service = governance_service or GovernanceService()
        self.memory_service = memory_service or MemoryService()
        self.operational_service = operational_service or OperationalService()

    def handle_input(self, contract: InputContract) -> OrchestratorResponse:
        """Execute the first orchestrated flow for a normalized input contract."""

        memory_recovery_result = self.memory_service.recover_for_input(contract)
        intent = self.classify_intent(contract)
        assessment = self.governance_service.assess_request(
            contract,
            intent=intent,
            requested_by_service=self.name,
        )
        governance_check = assessment.governance_check
        governance_decision = assessment.governance_decision
        operation_dispatch = None
        operation_result = None
        if governance_decision.decision == PermissionDecision.ALLOW:
            operation_dispatch = self.build_operation_dispatch(contract, intent)
            execution = self.operational_service.execute(operation_dispatch)
            operation_result = execution.operation_result
        response_text = self.synthesize_response(
            intent,
            governance_decision,
            memory_recovery_result.recovered_items,
            operation_result,
        )
        memory_record_result = self.memory_service.record_turn(
            contract,
            intent=intent,
            response_text=response_text,
        )
        events = self.build_events(
            contract,
            intent,
            memory_recovery_result.recovery_contract,
            governance_check,
            governance_decision,
            memory_record_result.record_contract,
            operation_dispatch,
            operation_result,
        )
        return OrchestratorResponse(
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            intent=intent,
            response_text=response_text,
            governance_check=governance_check,
            governance_decision=governance_decision,
            memory_recovery=memory_recovery_result.recovery_contract,
            memory_record=memory_record_result.record_contract,
            recovered_context=memory_recovery_result.recovered_items,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
            events=events,
        )

    def classify_intent(self, contract: InputContract) -> str:
        """Classify the incoming request into a small canonical set."""

        content = contract.content.lower()
        if any(keyword in content for keyword in HIGH_RISK_KEYWORDS):
            return "sensitive_action"
        if "plan" in content or "planej" in content:
            return "planning"
        if "analis" in content or "analy" in content:
            return "analysis"
        return "general_assistance"

    def build_operation_dispatch(
        self,
        contract: InputContract,
        intent: str,
    ) -> OperationDispatchContract:
        """Create a minimal operational dispatch for allowed requests."""

        task_type = {
            "planning": "draft_plan",
            "analysis": "produce_analysis_brief",
            "general_assistance": "general_response",
        }.get(intent, "general_response")
        return OperationDispatchContract(
            operation_id=OperationId(f"op-{uuid4().hex[:8]}"),
            request_id=RequestId(str(contract.request_id)),
            task_type=task_type,
            task_goal=contract.content,
            task_plan=f"Handle intent '{intent}' with a safe local operation.",
            constraints=["low-risk", "local-only", "no external side effects"],
            expected_output="text_brief",
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            priority_hint=contract.priority_hint,
        )

    def build_events(
        self,
        contract: InputContract,
        intent: str,
        memory_recovery: MemoryRecoveryContract,
        governance_check: GovernanceCheckContract,
        governance_decision: GovernanceDecisionContract,
        memory_record: MemoryRecordContract,
        operation_dispatch: OperationDispatchContract | None,
        operation_result: OperationResultContract | None,
    ) -> list[InternalEventEnvelope]:
        """Emit a minimal ordered event trail for the request."""

        events = [
            self.make_event(
                "input_received",
                contract,
                {"content": contract.content, "channel": contract.channel.value},
            ),
            self.make_event(
                "memory_recovered",
                contract,
                {
                    "memory_query_id": str(memory_recovery.memory_query_id),
                    "recovery_type": memory_recovery.recovery_type.value,
                },
            ),
            self.make_event(
                "intent_classified",
                contract,
                {"intent": intent},
            ),
            self.make_event(
                "governance_checked",
                contract,
                {
                    "governance_check_id": str(governance_check.governance_check_id),
                    "risk_hint": governance_check.risk_hint.value
                    if governance_check.risk_hint
                    else None,
                },
            ),
        ]
        if governance_decision.decision == PermissionDecision.BLOCK:
            events.append(
                self.make_event(
                    "governance_blocked",
                    contract,
                    {
                        "decision_id": str(governance_decision.decision_id),
                        "justification": governance_decision.justification,
                    },
                )
            )
        if operation_dispatch is not None:
            events.append(
                self.make_event(
                    "operation_dispatched",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "task_type": operation_dispatch.task_type,
                    },
                )
            )
        if operation_result is not None:
            events.append(
                self.make_event(
                    "operation_completed",
                    contract,
                    {
                        "operation_id": str(operation_result.operation_id),
                        "status": operation_result.status.value,
                    },
                )
            )
        events.append(
            self.make_event(
                "memory_recorded",
                contract,
                {
                    "memory_record_id": str(memory_record.memory_record_id),
                    "record_type": memory_record.record_type,
                },
            )
        )
        return events

    def synthesize_response(
        self,
        intent: str,
        governance_decision: GovernanceDecisionContract,
        recovered_context: list[str],
        operation_result: OperationResultContract | None,
    ) -> str:
        """Produce a first JARVIS-style textual synthesis."""

        if governance_decision.decision == PermissionDecision.BLOCK:
            return (
                "Solicitacao recebida, mas bloqueada pela governanca inicial. "
                "O fluxo exige validacao explicita antes de qualquer execucao sensivel."
            )
        operation_summary = operation_result.outputs[0] if operation_result else ""
        if recovered_context:
            return (
                f"Solicitacao recebida com intencao '{intent}'. "
                f"Recuperei {len(recovered_context)} item(ns) de contexto recente. "
                f"Resultado operacional: {operation_summary} "
                f"O fluxo segue alinhado a {SYSTEM_IDENTITY.core_traits[0]} e {SYSTEM_IDENTITY.core_traits[3]}."
            )
        return (
            f"Solicitacao recebida com intencao '{intent}'. "
            f"Nao havia contexto previo relevante nesta sessao. "
            f"Resultado operacional: {operation_summary} "
            f"O fluxo segue alinhado a {SYSTEM_IDENTITY.core_traits[0]} e "
            f"{SYSTEM_IDENTITY.core_traits[3]} como postura inicial do JARVIS."
        )

    def make_event(
        self,
        event_name: str,
        contract: InputContract,
        payload: dict[str, object],
    ) -> InternalEventEnvelope:
        """Build a canonical internal event envelope."""

        return InternalEventEnvelope(
            event_id=f"evt-{uuid4().hex[:8]}",
            event_name=event_name,
            timestamp=self.now(),
            source_service=self.name,
            payload=payload,
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            correlation_id=str(contract.request_id),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
