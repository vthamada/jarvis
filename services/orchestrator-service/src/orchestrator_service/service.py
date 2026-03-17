"""Minimal orchestrator flow built on top of shared canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from shared.contracts import GovernanceCheckContract, GovernanceDecisionContract, InputContract
from shared.events import InternalEventEnvelope
from shared.state import SYSTEM_IDENTITY
from shared.types import GovernanceCheckId, GovernanceDecisionId, PermissionDecision, RiskLevel


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
    events: list[InternalEventEnvelope] = field(default_factory=list)


class OrchestratorService:
    """Coordinates the first minimal request flow."""

    name = "orchestrator-service"

    def handle_input(self, contract: InputContract) -> OrchestratorResponse:
        """Execute the first orchestrated flow for a normalized input contract."""

        intent = self.classify_intent(contract)
        governance_check = self.build_governance_check(contract, intent)
        governance_decision = self.evaluate_governance(governance_check)
        events = self.build_events(contract, intent, governance_check, governance_decision)
        response_text = self.synthesize_response(intent, governance_decision)
        return OrchestratorResponse(
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            intent=intent,
            response_text=response_text,
            governance_check=governance_check,
            governance_decision=governance_decision,
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

    def build_governance_check(
        self,
        contract: InputContract,
        intent: str,
    ) -> GovernanceCheckContract:
        """Create a minimal governance check for the current input."""

        risk_hint = RiskLevel.HIGH if intent == "sensitive_action" else RiskLevel.LOW
        return GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="request",
            subject_action=intent,
            scope="session",
            context={
                "content": contract.content,
                "channel": contract.channel.value,
                "input_type": contract.input_type.value,
            },
            sensitivity="high" if intent == "sensitive_action" else "normal",
            reversibility="low" if intent == "sensitive_action" else "high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            risk_hint=risk_hint,
            requested_by_service=self.name,
        )

    def evaluate_governance(
        self,
        governance_check: GovernanceCheckContract,
    ) -> GovernanceDecisionContract:
        """Apply a first deterministic governance policy."""

        blocked = governance_check.risk_hint == RiskLevel.HIGH
        return GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=RiskLevel.HIGH if blocked else RiskLevel.LOW,
            decision=(PermissionDecision.BLOCK if blocked else PermissionDecision.ALLOW),
            justification=(
                "Potentially destructive request requires stronger validation."
                if blocked
                else "No critical signal detected in the current request."
            ),
            timestamp=self.now(),
            requires_audit=blocked,
            conditions=(
                ["Require explicit validation before execution."] if blocked else []
            ),
        )

    def build_events(
        self,
        contract: InputContract,
        intent: str,
        governance_check: GovernanceCheckContract,
        governance_decision: GovernanceDecisionContract,
    ) -> list[InternalEventEnvelope]:
        """Emit a minimal ordered event trail for the request."""

        events = [
            self.make_event(
                "input_received",
                contract,
                {"content": contract.content, "channel": contract.channel.value},
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
        return events

    def synthesize_response(
        self,
        intent: str,
        governance_decision: GovernanceDecisionContract,
    ) -> str:
        """Produce a first JARVIS-style textual synthesis."""

        if governance_decision.decision == PermissionDecision.BLOCK:
            return (
                "Solicitacao recebida, mas bloqueada pela governanca inicial. "
                "O fluxo exige validacao explicita antes de qualquer execucao sensivel."
            )
        return (
            f"Solicitacao recebida com intencao '{intent}'. "
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
