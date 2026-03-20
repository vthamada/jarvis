"""Governance service with explicit low, moderate, and high-risk policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from shared.contracts import (
    DeliberativePlanContract,
    GovernanceCheckContract,
    GovernanceDecisionContract,
    InputContract,
)
from shared.types import (
    GovernanceCheckId,
    GovernanceDecisionId,
    MemoryClass,
    PermissionDecision,
    RiskLevel,
)

HIGH_RISK_KEYWORDS = (
    "delete",
    "drop",
    "destroy",
    "excluir",
    "apagar",
    "deletar",
    "remover",
)

MODERATE_RISK_KEYWORDS = (
    "deploy",
    "publish",
    "release",
    "migrate",
    "update",
    "rewrite",
    "alter",
    "change",
)


@dataclass
class GovernanceAssessment:
    """Structured governance output for a request or memory assessment."""

    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract


class GovernanceService:
    """Apply explicit request and memory policies for the v1 flow."""

    name = "governance-service"

    def assess_request(
        self,
        contract: InputContract,
        intent: str,
        requested_by_service: str,
        *,
        plan: DeliberativePlanContract | None = None,
    ) -> GovernanceAssessment:
        """Build and evaluate a governance check for an incoming request."""

        risk_hint = self.classify_risk(contract, intent)
        proposed_effect = self.proposed_effect(intent=intent, plan=plan)
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="request",
            subject_action=intent,
            scope="session",
            context={
                "content": contract.content,
                "channel": contract.channel.value,
                "input_type": contract.input_type.value,
                "recommended_task_type": plan.recommended_task_type if plan else None,
                "plan_summary": plan.plan_summary if plan else None,
            },
            sensitivity="high" if risk_hint in {RiskLevel.HIGH, RiskLevel.CRITICAL} else "normal",
            reversibility=("low" if proposed_effect == "external_or_sensitive_change" else "high"),
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect=proposed_effect,
            risk_hint=risk_hint,
            requested_by_service=requested_by_service,
            declared_risks=list(plan.risks) if plan else [],
            requires_human_validation=bool(plan.requires_human_validation) if plan else False,
        )
        governance_decision = self.make_decision(governance_check)
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def classify_risk(self, contract: InputContract, intent: str) -> RiskLevel:
        """Classify the current request using a deterministic policy matrix."""

        content = contract.content.lower()
        if intent == "sensitive_action":
            return RiskLevel.HIGH
        if any(keyword in content for keyword in HIGH_RISK_KEYWORDS):
            return RiskLevel.HIGH
        if any(keyword in content for keyword in MODERATE_RISK_KEYWORDS):
            return RiskLevel.MODERATE
        return RiskLevel.LOW

    def make_decision(
        self,
        governance_check: GovernanceCheckContract,
    ) -> GovernanceDecisionContract:
        """Produce the v1 governance decision for request handling."""

        risk_level = governance_check.risk_hint or RiskLevel.LOW
        decision = PermissionDecision.ALLOW
        justification = "Solicitacao reversivel e compativel com o escopo controlado do v1."
        conditions: list[str] = []
        policy_refs = ["policy://request/default-low-risk"]
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None
        proposed_effect = governance_check.proposed_effect or "analysis_or_guidance_only"

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            decision = PermissionDecision.BLOCK
            justification = "Potencial destrutivo detectado; a execução direta foi bloqueada."
            conditions = ["Exigir validação forte fora do fluxo normal antes de qualquer ação."]
            policy_refs = ["policy://request/high-risk"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_direct_execution"
        elif (
            governance_check.requires_human_validation
            or proposed_effect == "external_or_sensitive_change"
        ):
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            justification = (
                "O plano pretendido exige validação humana antes de qualquer execução."
            )
            conditions = [
                "Manter apenas análise e rastreabilidade até revisão explícita."
            ]
            policy_refs = ["policy://request/defer-sensitive-plan"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "defer_sensitive_plan"
        elif proposed_effect == "local_safe_operation":
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = "Operação local segura permitida com trilha reforçada de auditoria."
            conditions = [
                "Manter trilha de eventos completa.",
                "Restringir a artefatos locais e reversiveis.",
            ]
            policy_refs = ["policy://request/local-safe-operation"]
            requires_audit = True
        elif risk_level == RiskLevel.MODERATE:
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = (
                "Sinais moderados exigem rastreabilidade reforçada, sem bloquear a análise."
            )
            conditions = ["Reforcar auditoria e evitar ampliar escopo operacional."]
            policy_refs = ["policy://request/moderate-risk"]
            requires_audit = True

        return GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=risk_level,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            conditions=conditions,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )

    @staticmethod
    def proposed_effect(intent: str, plan: DeliberativePlanContract | None) -> str:
        if intent == "sensitive_action":
            return "external_or_sensitive_change"
        if plan is None:
            return "analysis_or_guidance_only"
        if plan.requires_human_validation:
            return "external_or_sensitive_change"
        if plan.recommended_task_type in {"draft_plan", "general_response"}:
            return "local_safe_operation"
        return "analysis_or_guidance_only"

    def assess_memory_operation(
        self,
        *,
        memory_class: MemoryClass,
        action: str,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Evaluate access to critical memory classes with explicit policy."""

        is_critical = memory_class in {MemoryClass.IDENTITY, MemoryClass.NORMATIVE}
        check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="memory",
            subject_action=action,
            scope=memory_class.value,
            context={"memory_class": memory_class.value},
            sensitivity="critical" if is_critical else "normal",
            reversibility="low" if action in {"write", "promote", "delete"} else "high",
            risk_hint=RiskLevel.CRITICAL if is_critical else RiskLevel.LOW,
            requested_by_service=requested_by_service,
        )
        decision = PermissionDecision.ALLOW
        justification = "Memory action is compatible with the current policy."
        policy_refs = [f"policy://memory/{memory_class.value}/default"]
        conditions: list[str] = []
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None

        if is_critical and action in {"write", "promote", "delete"}:
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            justification = "Critical memory mutation requires explicit validation."
            policy_refs = [f"policy://memory/{memory_class.value}/critical-mutation"]
            conditions = ["Validate actor and intent before changing critical memory."]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "protect_critical_memory"

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=check.governance_check_id,
            risk_level=check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(governance_check=check, governance_decision=governance_decision)

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
