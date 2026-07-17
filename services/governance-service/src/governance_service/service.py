"""Governance service with explicit low, moderate, and high-risk policies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from shared.autonomy_ladder import capability_mode_exceeds_autonomy_limit
from shared.contracts import (
    DeliberativePlanContract,
    GovernanceCheckContract,
    GovernanceDecisionContract,
    InputContract,
    KnowledgeEvidenceGovernanceContract,
    MissionStateContract,
    OperatorFeedbackContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
)
from shared.types import (
    GovernanceCheckId,
    GovernanceDecisionId,
    MemoryClass,
    MissionStatus,
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

    def assess_knowledge_evidence(
        self,
        *,
        provenance_status: str,
        freshness_status: str,
        conflict_status: str,
        source_refs: list[str],
        uncertainty_notes: list[str],
        assessed_at: str | None = None,
    ) -> KnowledgeEvidenceGovernanceContract:
        """Qualify evidence use without changing the request permission decision."""

        status = "evidence_ready"
        use_mode = "bounded_grounding"
        conditions = ["Expose source refs in the observable response trail."]
        blockers: list[str] = []
        human_review_required = False

        if conflict_status == "conflict_detected":
            status = "review_required"
            use_mode = "do_not_assert_as_verified"
            blockers.append("Declared source conflicts require explicit resolution.")
            human_review_required = True
        elif provenance_status == "missing":
            status = "review_required"
            use_mode = "do_not_assert_as_verified"
            blockers.append("Source provenance is missing.")
            human_review_required = True
        elif freshness_status == "stale":
            status = "review_required"
            use_mode = "historical_context_only"
            blockers.append("Source freshness window has expired.")
            human_review_required = True
        elif (
            provenance_status != "complete"
            or freshness_status != "current"
            or conflict_status != "none_declared"
        ):
            status = "conditional_use"
            use_mode = "qualified_grounding"
            conditions.append("Surface uncertainty and avoid unqualified factual claims.")
            human_review_required = True

        if uncertainty_notes:
            conditions.append("Preserve retrieval uncertainty in final synthesis.")

        return KnowledgeEvidenceGovernanceContract(
            assessment_id=f"knowledge-evidence-assessment://{uuid4().hex[:12]}",
            status=status,
            use_mode=use_mode,
            provenance_status=provenance_status,
            freshness_status=freshness_status,
            conflict_status=conflict_status,
            source_refs=list(dict.fromkeys(source_refs)),
            conditions=conditions,
            blockers=blockers,
            uncertainty_notes=list(dict.fromkeys(uncertainty_notes)),
            timestamp=assessed_at or self.now(),
            human_review_required=human_review_required,
            request_decision_mutation_allowed=False,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

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
        request_confirmation_mode = plan.request_confirmation_mode if plan else None
        request_reversibility_mode = plan.request_reversibility_mode if plan else None
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
                "request_identity_status": (
                    plan.request_identity_status if plan else None
                ),
                "request_active_mission": (
                    plan.request_active_mission if plan else None
                ),
                "request_executive_posture": (
                    plan.request_executive_posture if plan else None
                ),
                "request_authority_level": (
                    plan.request_authority_level if plan else None
                ),
                "request_risk_profile": (
                    plan.request_risk_profile if plan else None
                ),
                "request_reversibility_mode": request_reversibility_mode,
                "request_confirmation_mode": request_confirmation_mode,
                "request_identity_summary": (
                    plan.request_identity_summary if plan else None
                ),
                "request_identity_policy_refs": (
                    list(plan.request_identity_policy_refs) if plan else []
                ),
                "requested_autonomy_level": (
                    plan.requested_autonomy_level if plan else None
                ),
                "max_autonomy_level": plan.max_autonomy_level if plan else None,
                "effective_autonomy_level": (
                    plan.effective_autonomy_level if plan else None
                ),
                "autonomy_ladder_status": (
                    plan.autonomy_ladder_status if plan else None
                ),
                "max_autonomy_capability_mode": (
                    plan.max_autonomy_capability_mode if plan else None
                ),
                "autonomy_human_confirmation_required": (
                    plan.autonomy_human_confirmation_required if plan else None
                ),
                "autonomy_confirmation_mode": (
                    plan.autonomy_confirmation_mode if plan else None
                ),
                "autonomy_allowed_runtime_actions": (
                    list(plan.autonomy_allowed_runtime_actions) if plan else []
                ),
                "autonomy_blocked_runtime_actions": (
                    list(plan.autonomy_blocked_runtime_actions) if plan else []
                ),
                "autonomy_policy_refs": (
                    list(plan.autonomy_policy_refs) if plan else []
                ),
                "autonomy_summary": plan.autonomy_summary if plan else None,
                "autonomy_automatic_promotion_allowed": (
                    plan.autonomy_automatic_promotion_allowed if plan else False
                ),
                "autonomy_core_mutation_allowed": (
                    plan.autonomy_core_mutation_allowed if plan else False
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
            reversibility=self._reversibility_level(
                proposed_effect=proposed_effect,
                request_reversibility_mode=request_reversibility_mode,
            ),
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect=proposed_effect,
            risk_hint=risk_hint,
            policy_hint=request_confirmation_mode,
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

    def assess_objective_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_next_action_ref: str | None,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven objective state changes."""

        current_status = (
            current_state.mission_status.value if current_state is not None else None
        )
        current_objective_status = (
            current_state.objective_status if current_state is not None else None
        )
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="objective_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "current_mission_status": current_status,
                "current_objective_status": current_objective_status,
                "requested_next_action_ref": requested_next_action_ref,
                "memory_write_mode": "through_core_only",
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="objective_state_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="objective_transition",
            mission_continuity_hint="operator_bounded_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = (
            "Transicao operacional bounded permitida pelo nucleo com memoria canonica."
        )
        conditions = [
            "Persistir somente via memoria canonica.",
            "Registrar evento auditavel com estado anterior e novo.",
            "Manter especialistas e automacoes fora da escrita direta.",
        ]
        requires_audit = True
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://objective-transition/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber transicao operacional."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://objective-transition/missing-state"]
        elif (
            requested_transition == "resume"
            and current_state.mission_status
            in {MissionStatus.COMPLETED, MissionStatus.CANCELED}
        ):
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode ser retomada por comando bounded."
            conditions = ["Abrir nova missao ou revisao explicita em vez de reativar estado final."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_resume"
            policy_refs = ["policy://objective-transition/terminal-state"]
        elif requested_transition == "redefine-next-action" and not requested_next_action_ref:
            decision = PermissionDecision.BLOCK
            justification = "Redefinir proxima acao exige referencia explicita."
            conditions = ["Informar --next-action-ref com uma referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_next_action_ref"
            policy_refs = ["policy://objective-transition/missing-next-action"]
        elif requested_next_action_ref and not self._is_bounded_reference(
            requested_next_action_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de proxima acao fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_next_action_ref"
            policy_refs = ["policy://objective-transition/unbounded-reference"]

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

    def assess_work_item_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_work_item_ref: str | None,
        requested_next_action_ref: str | None,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven work item state changes."""

        current_status = (
            current_state.mission_status.value if current_state is not None else None
        )
        existing_refs = set(current_state.work_item_refs if current_state else [])
        active_refs = set(current_state.active_work_items if current_state else [])
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="work_item_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "current_mission_status": current_status,
                "requested_work_item_ref": requested_work_item_ref,
                "requested_next_action_ref": requested_next_action_ref,
                "existing_work_item_count": len(existing_refs),
                "active_work_item_count": len(active_refs),
                "memory_write_mode": "through_core_only",
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="work_item_state_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="work_item_transition",
            mission_continuity_hint="operator_bounded_work_item_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = (
            "Transicao bounded de work item permitida via nucleo e memoria canonica."
        )
        conditions = [
            "Persistir somente via MissionStateContract canonico.",
            "Registrar evento auditavel com work item, transicao e checkpoint.",
            "Nao executar ou agendar o work item automaticamente.",
        ]
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://work-item-transition/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber work item."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://work-item-transition/missing-state"]
        elif current_state.mission_status in {MissionStatus.COMPLETED, MissionStatus.CANCELED}:
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode receber mutacao de work item."
            conditions = ["Abrir nova missao ou revisao explicita antes de alterar tarefas."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_mission"
            policy_refs = ["policy://work-item-transition/terminal-state"]
        elif not requested_work_item_ref:
            decision = PermissionDecision.BLOCK
            justification = "Transicao de work item exige referencia explicita."
            conditions = ["Informar --work-item-ref com referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_work_item_ref"
            policy_refs = ["policy://work-item-transition/missing-work-item-ref"]
        elif not self._is_bounded_reference(requested_work_item_ref):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de work item fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_work_item_ref"
            policy_refs = ["policy://work-item-transition/unbounded-reference"]
        elif requested_next_action_ref and not self._is_bounded_reference(
            requested_next_action_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de proxima acao fora do formato bounded permitido."
            conditions = [
                "Usar referencia curta com letras, numeros, dois-pontos, barra, "
                "ponto, hifen ou underscore."
            ]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_next_action_ref"
            policy_refs = ["policy://work-item-transition/unbounded-next-action"]
        elif requested_transition == "create" and requested_work_item_ref in existing_refs:
            decision = PermissionDecision.BLOCK
            justification = "Work item ja existe na missao canonica."
            conditions = ["Usar resume, pause, block, complete ou redefinir proxima acao."]
            requires_rollback_plan = True
            containment_hint = "block_duplicate_work_item"
            policy_refs = ["policy://work-item-transition/duplicate-ref"]
        elif requested_transition != "create" and requested_work_item_ref not in existing_refs:
            decision = PermissionDecision.BLOCK
            justification = "Work item inexistente nao pode receber transicao."
            conditions = ["Criar o work item antes de atualizar seu estado."]
            requires_rollback_plan = True
            containment_hint = "block_missing_work_item"
            policy_refs = ["policy://work-item-transition/missing-work-item"]
        elif requested_transition == "redefine-next-action" and not requested_next_action_ref:
            decision = PermissionDecision.BLOCK
            justification = "Redefinir proxima acao exige referencia explicita."
            conditions = ["Informar --next-action-ref com uma referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_next_action_ref"
            policy_refs = ["policy://work-item-transition/missing-next-action"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    def assess_artifact_lifecycle_transition(
        self,
        *,
        contract: InputContract,
        current_state: MissionStateContract | None,
        requested_transition: str,
        requested_artifact_ref: str | None,
        requested_replacement_artifact_ref: str | None,
        requested_rollback_plan_ref: str | None,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern bounded operator-driven artifact lifecycle changes."""

        existing_refs = set(current_state.artifact_refs if current_state else [])
        active_refs = set(current_state.active_artifact_refs if current_state else [])
        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="artifact_lifecycle_transition",
            subject_action=requested_transition,
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "requested_artifact_ref": requested_artifact_ref,
                "requested_replacement_artifact_ref": requested_replacement_artifact_ref,
                "requested_rollback_plan_ref": requested_rollback_plan_ref,
                "existing_artifact_count": len(existing_refs),
                "active_artifact_count": len(active_refs),
                "memory_write_mode": "through_core_only",
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="artifact_lifecycle_transition",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="artifact_lifecycle_transition",
            mission_continuity_hint="operator_bounded_artifact_transition",
        )

        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = "Transicao bounded de artefato permitida via memoria canonica."
        conditions = [
            "Persistir somente via MissionStateContract canonico.",
            "Registrar evento auditavel com artefato, transicao e checkpoint.",
            "Nao ler, mover, deletar ou editar arquivos reais nesta transicao.",
        ]
        requires_rollback_plan = False
        containment_hint = None
        policy_refs = ["policy://artifact-lifecycle/bounded-core-write"]

        if current_state is None:
            decision = PermissionDecision.BLOCK
            justification = "Missao inexistente nao pode receber artefato."
            conditions = ["Criar ou recuperar estado canonico da missao antes da transicao."]
            requires_rollback_plan = True
            containment_hint = "block_missing_mission_state"
            policy_refs = ["policy://artifact-lifecycle/missing-state"]
        elif current_state.mission_status in {MissionStatus.COMPLETED, MissionStatus.CANCELED}:
            decision = PermissionDecision.BLOCK
            justification = "Missao finalizada nao pode receber mutacao de artefato."
            conditions = ["Abrir nova missao ou revisao explicita antes de alterar artefatos."]
            requires_rollback_plan = True
            containment_hint = "block_terminal_mission"
            policy_refs = ["policy://artifact-lifecycle/terminal-state"]
        elif not requested_artifact_ref:
            decision = PermissionDecision.BLOCK
            justification = "Transicao de artefato exige referencia explicita."
            conditions = ["Informar --artifact-ref com referencia bounded."]
            requires_rollback_plan = True
            containment_hint = "block_missing_artifact_ref"
            policy_refs = ["policy://artifact-lifecycle/missing-artifact-ref"]
        elif not self._is_bounded_reference(requested_artifact_ref):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de artefato fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como artifact://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_artifact_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-reference"]
        elif requested_replacement_artifact_ref and not self._is_bounded_reference(
            requested_replacement_artifact_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de substituicao fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como artifact://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_replacement_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-replacement"]
        elif requested_rollback_plan_ref and not self._is_bounded_reference(
            requested_rollback_plan_ref
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencia de rollback fora do formato bounded permitido."
            conditions = ["Usar uma referencia curta e bounded, como rollback://..."]
            requires_rollback_plan = True
            containment_hint = "block_unbounded_rollback_ref"
            policy_refs = ["policy://artifact-lifecycle/unbounded-rollback"]
        elif requested_transition == "register" and requested_artifact_ref in existing_refs:
            decision = PermissionDecision.BLOCK
            justification = "Artefato ja existe na missao canonica."
            conditions = ["Usar activate, archive, replace ou rollback."]
            requires_rollback_plan = True
            containment_hint = "block_duplicate_artifact"
            policy_refs = ["policy://artifact-lifecycle/duplicate-ref"]
        elif requested_transition != "register" and requested_artifact_ref not in existing_refs:
            decision = PermissionDecision.BLOCK
            justification = "Artefato inexistente nao pode receber transicao."
            conditions = ["Registrar o artefato antes de atualizar seu estado."]
            requires_rollback_plan = True
            containment_hint = "block_missing_artifact"
            policy_refs = ["policy://artifact-lifecycle/missing-artifact"]
        elif requested_transition == "replace" and not requested_replacement_artifact_ref:
            decision = PermissionDecision.BLOCK
            justification = "Substituir artefato exige referencia de substituicao."
            conditions = ["Informar --replacement-artifact-ref."]
            requires_rollback_plan = True
            containment_hint = "block_missing_replacement_ref"
            policy_refs = ["policy://artifact-lifecycle/missing-replacement"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=governance_check.risk_hint or RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=requires_rollback_plan,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
        return GovernanceAssessment(
            governance_check=governance_check,
            governance_decision=governance_decision,
        )

    @staticmethod
    def _is_bounded_reference(value: str) -> bool:
        if not value or len(value) > 160:
            return False
        allowed = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:/._-"
        )
        return all(character in allowed for character in value)

    def assess_operator_feedback(
        self,
        *,
        contract: InputContract,
        feedback: OperatorFeedbackContract,
        experience_mission_id: str | None,
        reflection_available: bool,
        requested_by_service: str,
    ) -> GovernanceAssessment:
        """Govern an explicit bounded post-mission operator feedback write."""

        governance_check = GovernanceCheckContract(
            governance_check_id=GovernanceCheckId(f"gov-check-{uuid4().hex[:8]}"),
            subject_type="operator_feedback",
            subject_action="record",
            scope="mission",
            context={
                "mission_id": str(contract.mission_id) if contract.mission_id else None,
                "experience_id": feedback.experience_id,
                "experience_mission_id": experience_mission_id,
                "reflection_available": reflection_available,
                "assessment": feedback.assessment,
                "rating": feedback.rating,
                "comment_length": len(feedback.comment or ""),
                "correction_length": len(feedback.correction or ""),
                "next_expectation_length": len(feedback.next_expectation or ""),
                "evidence_ref_count": len(feedback.evidence_refs),
                "memory_write_mode": feedback.memory_write_mode,
                "operator_identity_ref": contract.operator_identity_ref,
                "canonical_user_ref": contract.canonical_user_ref,
                "automatic_promotion_allowed": feedback.automatic_promotion_allowed,
                "core_mutation_allowed": feedback.core_mutation_allowed,
            },
            sensitivity="normal",
            reversibility="high",
            mission_id=contract.mission_id,
            session_id=contract.session_id,
            proposed_effect="append_bounded_operator_feedback",
            risk_hint=RiskLevel.LOW,
            requested_by_service=requested_by_service,
            requires_human_validation=False,
            decision_frame="operator_feedback_write",
            mission_continuity_hint="post_mission_operator_learning",
        )
        decision = PermissionDecision.ALLOW_WITH_CONDITIONS
        justification = (
            "Feedback explicito bounded permitido via nucleo e memoria canonica."
        )
        conditions = [
            "Persistir o feedback somente via experiencia/reflexao canonica.",
            "Enviar qualquer proposta evolutiva para revisao humana.",
            "Nao autorizar promocao automatica ou mutacao do nucleo.",
        ]
        containment_hint = None
        policy_refs = ["policy://operator-feedback/bounded-core-write"]

        if experience_mission_id is None:
            decision = PermissionDecision.BLOCK
            justification = "Feedback exige experiencia canonica existente."
            containment_hint = "block_missing_experience"
            policy_refs = ["policy://operator-feedback/missing-experience"]
        elif str(contract.mission_id) != experience_mission_id:
            decision = PermissionDecision.BLOCK
            justification = "Experiencia nao pertence a missao informada."
            containment_hint = "block_experience_mission_mismatch"
            policy_refs = ["policy://operator-feedback/mission-mismatch"]
        elif not reflection_available:
            decision = PermissionDecision.BLOCK
            justification = "Feedback pos-missao exige reflexao canonica existente."
            containment_hint = "block_missing_reflection"
            policy_refs = ["policy://operator-feedback/missing-reflection"]
        elif feedback.assessment not in {
            "helpful",
            "partially_helpful",
            "not_helpful",
            "correction",
        }:
            decision = PermissionDecision.BLOCK
            justification = "Assessment de feedback nao suportado."
            containment_hint = "block_unsupported_assessment"
            policy_refs = ["policy://operator-feedback/unsupported-assessment"]
        elif feedback.rating is not None and (
            isinstance(feedback.rating, bool)
            or feedback.rating < 1
            or feedback.rating > 5
        ):
            decision = PermissionDecision.BLOCK
            justification = "Rating deve estar entre 1 e 5."
            containment_hint = "block_invalid_rating"
            policy_refs = ["policy://operator-feedback/invalid-rating"]
        elif feedback.assessment == "correction" and not feedback.correction:
            decision = PermissionDecision.BLOCK
            justification = "Feedback corretivo exige texto de correcao."
            containment_hint = "block_missing_correction"
            policy_refs = ["policy://operator-feedback/missing-correction"]
        elif any(
            len(value or "") > limit
            for value, limit in (
                (feedback.comment, 1000),
                (feedback.correction, 1000),
                (feedback.next_expectation, 500),
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Conteudo de feedback excede os limites bounded."
            containment_hint = "block_unbounded_feedback_content"
            policy_refs = ["policy://operator-feedback/unbounded-content"]
        elif not all(
            self._is_bounded_reference(value)
            for value in (
                feedback.feedback_id,
                feedback.experience_id,
                feedback.operator_ref,
            )
        ):
            decision = PermissionDecision.BLOCK
            justification = "Referencias de feedback fora do formato bounded."
            containment_hint = "block_unbounded_feedback_reference"
            policy_refs = ["policy://operator-feedback/unbounded-reference"]
        elif len(feedback.evidence_refs) > 20 or any(
            not self._is_bounded_reference(value) for value in feedback.evidence_refs
        ):
            decision = PermissionDecision.BLOCK
            justification = "Evidence refs de feedback fora do formato bounded."
            containment_hint = "block_unbounded_feedback_evidence"
            policy_refs = ["policy://operator-feedback/unbounded-evidence"]
        elif feedback.memory_write_mode != "through_core_only":
            decision = PermissionDecision.BLOCK
            justification = "Feedback deve ser persistido somente pelo nucleo."
            containment_hint = "block_feedback_memory_bypass"
            policy_refs = ["policy://operator-feedback/core-write-required"]
        elif feedback.automatic_promotion_allowed or feedback.core_mutation_allowed:
            decision = PermissionDecision.BLOCK
            justification = "Feedback nao pode autorizar promocao ou mutacao autonoma."
            containment_hint = "block_autonomous_feedback_mutation"
            policy_refs = ["policy://operator-feedback/no-autonomous-mutation"]

        governance_decision = GovernanceDecisionContract(
            decision_id=GovernanceDecisionId(f"gov-decision-{uuid4().hex[:8]}"),
            governance_check_id=governance_check.governance_check_id,
            risk_level=RiskLevel.LOW,
            decision=decision,
            justification=justification,
            timestamp=self.now(),
            conditions=conditions,
            requires_audit=True,
            requires_rollback_plan=False,
            containment_hint=containment_hint,
            policy_refs=policy_refs,
        )
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
        request_confirmation_mode = governance_check.context.get(
            "request_confirmation_mode"
        )
        autonomy_violation = self._autonomy_ladder_violation(governance_check)

        if risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            decision = PermissionDecision.BLOCK
            justification = "Potencial destrutivo detectado; a execucao direta foi bloqueada."
            conditions = ["Exigir validacao forte fora do fluxo normal antes de qualquer acao."]
            policy_refs = ["policy://request/high-risk"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_direct_execution"
        elif autonomy_violation == "forbidden_autonomy_claim":
            decision = PermissionDecision.BLOCK
            justification = (
                "O contrato de autonomia tentou permitir autopromocao ou mutacao "
                "do nucleo, o que e proibido."
            )
            conditions = [
                "Manter automatic_promotion_allowed=false.",
                "Manter core_mutation_allowed=false.",
            ]
            policy_refs = ["policy://autonomy-ladder/forbidden-claim"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "block_forbidden_autonomy_claim"
        elif autonomy_violation == "capability_above_autonomy_limit":
            decision = PermissionDecision.DEFER_FOR_VALIDATION
            justification = (
                "A capability selecionada excede o nivel maximo de autonomia "
                "permitido para a request/missao."
            )
            conditions = [
                "Rebaixar a capability ao max_autonomy_capability_mode.",
                "Solicitar confirmacao humana antes de qualquer execucao acima do limite.",
                "Registrar o limite aplicado em eventos e console.",
            ]
            policy_refs = ["policy://autonomy-ladder/enforce-max-capability"]
            requires_audit = True
            requires_rollback_plan = True
            containment_hint = "defer_capability_above_autonomy_limit"
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
            if request_confirmation_mode == "explicit_confirmation_required":
                conditions.append(
                    "Nao ampliar a autonomia sem confirmacao explicita do operador."
                )
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
    def _autonomy_ladder_violation(
        governance_check: GovernanceCheckContract,
    ) -> str | None:
        context = governance_check.context
        if context.get("autonomy_automatic_promotion_allowed") is True:
            return "forbidden_autonomy_claim"
        if context.get("autonomy_core_mutation_allowed") is True:
            return "forbidden_autonomy_claim"
        if capability_mode_exceeds_autonomy_limit(
            selected_mode=str(context.get("capability_decision_selected_mode") or ""),
            max_capability_mode=str(context.get("max_autonomy_capability_mode") or ""),
        ):
            return "capability_above_autonomy_limit"
        return None

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

    @staticmethod
    def _reversibility_level(
        *,
        proposed_effect: str,
        request_reversibility_mode: str | None,
    ) -> str:
        if request_reversibility_mode == "prefer_reversible_change":
            return "high"
        if proposed_effect == "external_or_sensitive_change":
            return "low"
        return "high"

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
