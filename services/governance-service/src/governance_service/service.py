"""Minimal governance service backed by shared canonical contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from shared.contracts import GovernanceCheckContract, GovernanceDecisionContract, InputContract
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
class GovernanceAssessment:
    """Structured governance output for a request assessment."""

    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract


class GovernanceService:
    """Applies the first explicit policy and risk controls."""

    name = "governance-service"

    def assess_request(
        self,
        contract: InputContract,
        intent: str,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Build and evaluate a governance check for an incoming request."""

        risk_hint = self.classify_risk(contract, intent)
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="request",
            subject_action=intent,
            scope="session",
            context={
                "content": contract.content,
                "channel": contract.channel.value,
                "input_type": contract.input_type.value,
            },
            sensitivity="high" if risk_hint == RiskLevel.HIGH else "normal",
            reversibility="low" if risk_hint == RiskLevel.HIGH else "high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            risk_hint=risk_hint,
            requested_by_service=requested_by_service,
        )
        governance_decision = self.make_decision(governance_check)
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def classify_risk(self, contract: InputContract, intent: str) -> RiskLevel:
        """Classify the current request using a simple deterministic policy."""

        content = contract.content.lower()
        if intent == "sensitive_action":
            return RiskLevel.HIGH
        if any(keyword in content for keyword in HIGH_RISK_KEYWORDS):
            return RiskLevel.HIGH
        return RiskLevel.LOW

    def make_decision(
        self,
        governance_check: GovernanceCheckContract,
    ) -> GovernanceDecisionContract:
        """Produce the first explicit allow-or-block decision."""

        blocked = governance_check.risk_hint == RiskLevel.HIGH
        return GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=RiskLevel.HIGH if blocked else RiskLevel.LOW,
            decision=PermissionDecision.BLOCK if blocked else PermissionDecision.ALLOW,
            justification=(
                "Potentially destructive request requires stronger validation."
                if blocked
                else "No critical signal detected in the current request."
            ),
            timestamp=self.now(),
            requires_audit=blocked,
            conditions=(
                ["Require explicit validation before execution."]
                if blocked
                else []
            ),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
