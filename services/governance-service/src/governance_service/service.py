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
    SpecialistInvocationContract,
    SpecialistSelectionContract,
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
        identity_mode: str | None = None,
        identity_signature: str | None = None,
        response_style: str | None = None,
    ) -> GovernanceAssessment:
        """Build and evaluate a governance check for an incoming request."""

        risk_hint = self.classify_risk(contract, intent)
        proposed_effect = self.proposed_effect(intent=intent, plan=plan)
        continuity_hint = self._continuity_hint(plan)
        identity_guardrail = self._identity_guardrail(
            intent=intent,
            proposed_effect=proposed_effect,
            identity_mode=identity_mode,
        )
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
                "capability_decision_status": (
                    plan.capability_decision_status if plan else None
                ),
                "capability_decision_selected_mode": (
                    plan.capability_decision_selected_mode if plan else None
                ),
                "capability_decision_authorization_status": (
                    plan.capability_decision_authorization_status if plan else None
                ),
                "capability_decision_tool_class": (
                    plan.capability_decision_tool_class if plan else None
                ),
                "capability_decision_handoff_mode": (
                    plan.capability_decision_handoff_mode if plan else None
                ),
                "continuity_replay_status": (
                    plan.continuity_replay_status if plan else None
                ),
                "continuity_recovery_mode": (
                    plan.continuity_recovery_mode if plan else None
                ),
                "continuity_resume_point": (
                    plan.continuity_resume_point if plan else None
                ),
                "identity_mode": identity_mode,
                "identity_signature": identity_signature,
                "response_style": response_style,
                "identity_guardrail": identity_guardrail,
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
            decision_frame=self._decision_frame(plan),
            mission_continuity_hint=continuity_hint,
            open_loops=self._extract_open_loops(plan),
        )
        governance_decision = self.make_decision(governance_check)
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_specialist_handoff(
        self,
        *,
        contract: InputContract,
        plan: DeliberativePlanContract,
        selections: list[SpecialistSelectionContract],
        invocations: list[SpecialistInvocationContract],
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Evaluate internal specialist handoffs before executing them."""

        selected = [item for item in selections if item.selection_status == "selected"]
        invalid_boundary = any(
            invocation.boundary.response_channel != "through_core"
            or invocation.boundary.tool_access_mode != "none"
            or invocation.boundary.memory_write_mode != "through_core_only"
            for invocation in invocations
        )
        requires_review = any(item.requires_governance_review for item in selected)
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="specialist_handoff",
            subject_action="dispatch",
            scope="session",
            context={
                "selected_specialists": [item.specialist_type for item in selected],
                "selection_statuses": {
                    item.specialist_type: item.selection_status for item in selections
                },
                "selected_invocation_ids": [item.invocation_id for item in selected],
                "response_channels": [
                    invocation.boundary.response_channel for invocation in invocations
                ],
                "tool_access_modes": [
                    invocation.boundary.tool_access_mode for invocation in invocations
                ],
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="internal_specialist_handoff",
            risk_hint=RiskLevel.MODERATE if selected else RiskLevel.LOW,
            requested_by_service=requested_by_service,
            declared_risks=list(plan.risks),
            requires_human_validation=False,
            decision_frame="specialist_handoff",
            mission_continuity_hint=self._continuity_hint(plan),
            open_loops=self._extract_open_loops(plan),
        )

        decision = PermissionDecision.ALLOW
        justification = "Convocacao interna de especialista permanece subordinada e rastreavel."
        conditions: list[str] = []
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://specialist-handoff/default"]

        if invalid_boundary:
            decision = PermissionDecision.BLOCK
            justification = (
                "A convocacao proposta viola a fronteira interna permitida para especialistas."
            )
            conditions = [
                "Especialista deve responder apenas pelo nucleo.",
                "Especialista nao pode acessar tools ou memoria fora das fronteiras internas.",
            ]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_invalid_specialist_boundary"
            policy_refs = ["policy://specialist-handoff/boundary-block"]
        elif selected and (
            requires_review
            or plan.continuity_recovery_mode in {"governed_review", "contained_recovery"}
            or plan.requires_human_validation
        ):
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = (
                "Convocacao interna permitida com trilha reforcada e limites explicitos "
                "de handoff subordinado."
            )
            conditions = [
                "Especialista nao responde diretamente ao usuario.",
                "Toda saida deve retornar ao nucleo por canal interno estruturado.",
                "Nao executar tools nem escrita direta de memoria no especialista.",
            ]
            requires_audit = True
            policy_refs = ["policy://specialist-handoff/allow-with-conditions"]
        elif not selected:
            justification = "Nenhum especialista ficou elegivel para convocacao nesta rodada."
            policy_refs = ["policy://specialist-handoff/no-selection"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=requires_audit,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
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
        justification = "Solicitacao reversivel e coerente com a missao ativa do v1."
        conditions: list[str] = []
        policy_refs = ["policy://request/default-low-risk"]
        requires_audit = False
        requires_rollback_plan = False
        containment_hint = None
        proposed_effect = governance_check.proposed_effect or "analysis_or_guidance_only"
        open_loops = list(governance_check.open_loops)
        continuity_hint = governance_check.mission_continuity_hint or "sem_continuidade"
        decision_frame = governance_check.decision_frame or "analysis"

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            decision = PermissionDecision.BLOCK
            justification = "Potencial destrutivo detectado; a execucao direta foi bloqueada."
            conditions = ["Exigir validacao forte fora do fluxo normal antes de qualquer acao."]
            policy_refs = ["policy://request/high-risk"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_direct_execution"
        elif self._should_defer(governance_check, proposed_effect, open_loops, continuity_hint):
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            if continuity_hint == "checkpoint_contido":
                justification = (
                    "A retomada parte de checkpoint contido e exige revisao explicita "
                    "antes de qualquer continuidade."
                )
            elif continuity_hint == "checkpoint_aguarda_validacao":
                justification = (
                    "O checkpoint recuperado ainda aguarda validacao e nao pode ser "
                    "retomado automaticamente."
                )
            elif continuity_hint == "retomada_relacionada":
                justification = (
                    "A retomada relacionada disputa direcao com loop ainda aberto e exige "
                    "validacao explicita."
                )
            else:
                justification = (
                    "O plano atual tenta ampliar ou reformular o escopo com "
                    "loop critico ainda aberto."
                )
            conditions = [
                "Manter apenas analise e rastreabilidade ate revisao explicita.",
                "Nao ampliar objetivo enquanto houver loop aberto relevante.",
            ]
            policy_refs = ["policy://request/defer-mission-reframe"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "defer_open_loop_reframe"
        elif self._should_allow_with_conditions(
            proposed_effect=proposed_effect,
            risk_level=risk_level,
            decision_frame=decision_frame,
            open_loops=open_loops,
        ):
            decision = PermissionDecision.ALLOW_WITH_CONDITIONS
            justification = "Operacao local segura permitida com rastreabilidade reforcada."
            conditions = [
                "Manter trilha de eventos completa.",
                "Restringir a artefatos locais e reversiveis.",
            ]
            if open_loops:
                conditions.append(
                    "Fechar explicitamente o loop principal da missao nesta resposta."
                )
            policy_refs = ["policy://request/local-safe-operation"]
            requires_audit = True
        elif decision_frame == "analysis":
            decision = PermissionDecision.ALLOW
            justification = "Analise reversivel permitida com continuidade coerente."
            policy_refs = ["policy://request/reversible-analysis"]

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
        if plan.capability_decision_selected_mode == "core_with_local_operation":
            return "local_safe_operation"
        if plan.capability_decision_selected_mode in {
            "clarification_only",
            "contained_guidance",
        }:
            return "analysis_or_guidance_only"
        if plan.requires_human_validation:
            return "external_or_sensitive_change"
        if plan.recommended_task_type in {"draft_plan", "general_response"}:
            return "local_safe_operation"
        return "analysis_or_guidance_only"

    @staticmethod
    def _decision_frame(plan: DeliberativePlanContract | None) -> str | None:
        if not plan:
            return None
        if plan.recommended_task_type == "produce_analysis_brief":
            return "analysis"
        if plan.recommended_task_type == "draft_plan":
            return "planning"
        if plan.recommended_task_type == "general_response" and plan.requires_human_validation:
            return "clarification"
        return "execution" if plan.smallest_safe_next_action else "planning"

    @staticmethod
    def _extract_open_loops(plan: DeliberativePlanContract | None) -> list[str]:
        if not plan:
            return []
        return list(plan.open_loops[:3])

    @staticmethod
    def _continuity_hint(plan: DeliberativePlanContract | None) -> str | None:
        if not plan:
            return None
        if plan.continuity_recovery_mode == "governed_review":
            return "checkpoint_aguarda_validacao"
        if plan.continuity_recovery_mode == "contained_recovery":
            return "checkpoint_contido"
        if plan.continuity_action == "reformular":
            return "reformulacao_de_objetivo"
        if plan.continuity_action == "retomar":
            return "retomada_relacionada"
        if plan.continuity_action == "continuar":
            return "continuidade_coerente"
        if plan.continuity_action == "encerrar":
            return "fechamento_de_loop"
        return None

    @staticmethod
    def _identity_guardrail(
        *,
        intent: str,
        proposed_effect: str,
        identity_mode: str | None,
    ) -> str:
        mode = identity_mode or "executive_guidance"
        if mode == "governed_refusal" or proposed_effect == "external_or_sensitive_change":
            return "preservar limites do nucleo antes de ampliar acao"
        if intent == "analysis":
            return "preservar rigor analitico antes de concluir"
        if intent == "planning":
            return "preservar unidade executiva e rastreabilidade do plano"
        return "preservar coerencia do nucleo e utilidade controlada"

    @staticmethod
    def _should_defer(
        governance_check: GovernanceCheckContract,
        proposed_effect: str,
        open_loops: list[str],
        continuity_hint: str,
    ) -> bool:
        if governance_check.requires_human_validation:
            return True
        if proposed_effect == "external_or_sensitive_change":
            return True
        if continuity_hint in {"checkpoint_aguarda_validacao", "checkpoint_contido"}:
            return True
        if continuity_hint == "retomada_relacionada" and bool(open_loops):
            return True
        if continuity_hint == "reformulacao_de_objetivo" and bool(open_loops):
            return True
        return False

    @staticmethod
    def _should_allow_with_conditions(
        *,
        proposed_effect: str,
        risk_level: RiskLevel,
        decision_frame: str,
        open_loops: list[str],
    ) -> bool:
        if proposed_effect == "local_safe_operation" and decision_frame in {
            "planning",
            "execution",
        }:
            return True
        if risk_level == RiskLevel.MODERATE:
            return True
        return decision_frame == "execution" and bool(open_loops)

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
