"""Planning engine for operational task plans."""

from __future__ import annotations

from dataclasses import dataclass, replace

from shared.contract_validation import validate_contract_instance
from shared.contracts import (
    DeliberativePlanContract,
    SpecialistContributionContract,
)
from shared.domain_registry import workflow_runtime_guidance
from shared.memory_registry import guided_memory_decision
from shared.schemas import DELIBERATIVE_PLAN_SCHEMA
from shared.specialist_registry import (
    GOVERNANCE_REVIEW_SPECIALIST,
    OPERATIONAL_PLANNING_SPECIALIST,
    STRUCTURED_ANALYSIS_SPECIALIST,
)

MISSION_SHIFT_KEYWORDS = (
    "new",
    "novo",
    "nova",
    "outro",
    "outra",
    "different",
    "instead",
    "mudar",
    "mudanca",
    "trocar",
    "switch",
)

MISSION_CLOSE_KEYWORDS = (
    "finish",
    "close",
    "encerrar",
    "concluir",
    "fechar",
)

IGNORED_TOKENS = {
    "a",
    "ao",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "for",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "para",
    "plan",
    "planejar",
    "please",
    "por",
    "the",
    "uma",
    "um",
}

DEEP_COGNITIVE_WORKFLOWS = {
    "structured_analysis_workflow",
    "decision_risk_workflow",
    "governance_boundary_workflow",
    "strategic_direction_workflow",
}


@dataclass(frozen=True)
class PlanningContext:
    """Inputs that influence the task plan produced for an operation."""

    intent: str
    query: str
    recovered_context: list[str]
    active_domains: list[str]
    active_minds: list[str]
    knowledge_snippets: list[str]
    risk_markers: list[str]
    requires_clarification: bool
    preferred_response_mode: str
    canonical_domains: list[str] | None = None
    primary_canonical_domain: str | None = None
    primary_route: str | None = None
    route_consumer_profile: str | None = None
    route_consumer_objective: str | None = None
    route_expected_deliverables: list[str] | None = None
    route_telemetry_focus: list[str] | None = None
    route_workflow_profile: str | None = None
    route_workflow_steps: list[str] | None = None
    route_workflow_checkpoints: list[str] | None = None
    route_workflow_decision_points: list[str] | None = None
    cognitive_rationale: str = ""
    tensions: list[str] | None = None
    specialist_hints: list[str] | None = None
    dominant_goal: str | None = None
    secondary_goals: list[str] | None = None
    ambiguity_reason: str | None = None
    identity_mode: str | None = None
    primary_mind: str | None = None
    primary_mind_family: str | None = None
    primary_domain_driver: str | None = None
    arbitration_source: str | None = None
    supporting_minds: list[str] | None = None
    suppressed_minds: list[str] | None = None
    dominant_tension: str | None = None
    arbitration_summary: str | None = None
    identity_continuity_brief: str | None = None
    open_loops: list[str] | None = None
    mission_semantic_brief: str | None = None
    mission_focus: list[str] | None = None
    last_decision_frame: str | None = None
    mission_goal: str | None = None
    mission_recommendation: str | None = None
    related_mission_id: str | None = None
    related_mission_goal: str | None = None
    related_continuity_reason: str | None = None
    related_continuity_priority: float | None = None
    related_continuity_confidence: float | None = None
    related_open_loops: list[str] | None = None
    continuity_recommendation: str | None = None
    continuity_ranking_summary: str | None = None
    continuity_replay_status: str | None = None
    continuity_recovery_mode: str | None = None
    continuity_resume_point: str | None = None
    continuity_requires_manual_resume: bool = False
    user_scope_status: str | None = None
    user_domain_focus: list[str] | None = None
    user_last_recommended_task_type: str | None = None
    user_continuity_preference: str | None = None
    context_compaction_status: str | None = None
    context_compaction_summary: str | None = None
    context_live_summary: str | None = None
    cross_session_recall_status: str | None = None
    cross_session_recall_summary: str | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_ref: str | None = None
    procedural_artifact_version: int | None = None
    procedural_artifact_summary: str | None = None


@dataclass(frozen=True)
class MetacognitiveGuidance:
    """Bounded metacognitive effects propagated into the runtime plan."""

    applied: bool
    summary: str | None
    effects: list[str]
    containment_recommendation: str | None


class PlanningEngine:
    """Build concise operational plans from intent, context, and knowledge."""

    name = "planning-engine"

    @staticmethod
    def _present_contract_label(value: str | None) -> str | None:
        if not value:
            return None
        return value.replace("_", " ")

    def build_task_plan(self, context: PlanningContext) -> DeliberativePlanContract:
        """Create a structured plan that is safe to pass into the operational layer."""

        tensions = list(context.tensions or [])
        specialist_hints = list(context.specialist_hints or [])
        dominant_goal = context.dominant_goal or context.query
        mission_goal = context.mission_goal or dominant_goal
        goal_conflict = self._mission_goal_conflict(context, mission_goal)
        dominant_tension = self._resolve_dominant_tension(context, goal_conflict)
        continuity_action = self._continuity_action(
            context,
            mission_goal=mission_goal,
            goal_conflict=goal_conflict,
        )
        continuity_reason = self._continuity_reason(
            context,
            mission_goal=mission_goal,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
        )
        open_loops = self._seed_open_loops(
            context,
            mission_goal=mission_goal,
            dominant_goal=dominant_goal,
            continuity_action=continuity_action,
        )
        continuity_source = self._continuity_source(context, open_loops=open_loops)
        steps = self._build_steps(
            context,
            continuity_action=continuity_action,
            mission_goal=mission_goal,
            goal_conflict=goal_conflict,
            open_loops=open_loops,
        )
        smallest_safe_next_action = self._smallest_safe_next_action(
            context,
            steps,
            continuity_action=continuity_action,
            open_loops=open_loops,
            goal_conflict=goal_conflict,
            dominant_tension=dominant_tension,
        )
        constraints = self._build_constraints(
            context,
            continuity_action=continuity_action,
            open_loops=open_loops,
            goal_conflict=goal_conflict,
        )
        risks = self._build_risks(
            context,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
        )
        success_criteria = self._build_success_criteria(
            context,
            continuity_action=continuity_action,
            open_loops=open_loops,
            dominant_tension=dominant_tension,
        )
        mind_disagreement_status = self._mind_disagreement_status(
            context,
            dominant_tension=dominant_tension,
        )
        mind_validation_checkpoints = self._mind_validation_checkpoints(
            context,
            dominant_tension=dominant_tension,
            disagreement_status=mind_disagreement_status,
        )
        steps, constraints, success_criteria = self._apply_mind_validation_guidance(
            steps=steps,
            constraints=constraints,
            success_criteria=success_criteria,
            mind_validation_checkpoints=mind_validation_checkpoints,
            disagreement_status=mind_disagreement_status,
        )
        metacognitive_guidance = self._build_metacognitive_guidance(
            context,
            dominant_tension=dominant_tension,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
            success_criteria=success_criteria,
            smallest_safe_next_action=smallest_safe_next_action,
        )
        memory_decision = self._guided_memory_decision(
            context,
            continuity_source=continuity_source,
        )
        steps, constraints, success_criteria = self._apply_memory_causality_guidance(
            steps=steps,
            constraints=constraints,
            success_criteria=success_criteria,
            context=context,
            memory_decision=memory_decision,
        )
        smallest_safe_next_action = self._apply_guided_memory_to_next_action(
            smallest_safe_next_action,
            context=context,
            memory_decision=memory_decision,
        )
        recommended_task_type = self._recommended_task_type(
            context,
            continuity_action=continuity_action,
        )
        requires_human_validation = self._requires_human_validation(
            context,
            risks=risks,
            continuity_action=continuity_action,
            open_loops=open_loops,
        )
        plan_summary = self._build_summary(
            context,
            dominant_goal=dominant_goal,
            mission_goal=mission_goal,
            dominant_tension=dominant_tension,
            smallest_safe_next_action=smallest_safe_next_action,
            metacognitive_guidance=metacognitive_guidance,
            memory_decision=memory_decision,
            continuity_action=continuity_action,
            continuity_reason=continuity_reason,
            continuity_source=continuity_source,
        )
        rationale = self._build_rationale(
            context,
            risks=risks,
            dominant_goal=dominant_goal,
            mission_goal=mission_goal,
            dominant_tension=dominant_tension,
            metacognitive_guidance=metacognitive_guidance,
            memory_decision=memory_decision,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
            continuity_reason=continuity_reason,
        )
        plan = DeliberativePlanContract(
            plan_summary=plan_summary,
            goal=dominant_goal,
            steps=steps,
            active_domains=context.active_domains or ["assistencia_pessoal_e_operacional"],
            active_minds=context.active_minds,
            constraints=constraints,
            canonical_domains=list(context.canonical_domains or []),
            primary_canonical_domain=context.primary_canonical_domain,
            primary_mind=context.primary_mind,
            primary_mind_family=context.primary_mind_family,
            primary_domain_driver=context.primary_domain_driver,
            arbitration_source=context.arbitration_source,
            primary_route=context.primary_route,
            route_consumer_profile=context.route_consumer_profile,
            route_consumer_objective=context.route_consumer_objective,
            route_expected_deliverables=list(context.route_expected_deliverables or []),
            route_telemetry_focus=list(context.route_telemetry_focus or []),
            route_workflow_profile=context.route_workflow_profile,
            route_workflow_steps=list(context.route_workflow_steps or []),
            route_workflow_checkpoints=list(context.route_workflow_checkpoints or []),
            route_workflow_decision_points=list(
                context.route_workflow_decision_points or []
            ),
            risks=risks,
            recommended_task_type=recommended_task_type,
            requires_human_validation=requires_human_validation,
            rationale=rationale,
            tensions_considered=tensions[:3],
            specialist_hints=specialist_hints[:3],
            success_criteria=success_criteria,
            specialist_resolution_summary=None,
            dominant_tension=dominant_tension,
            smallest_safe_next_action=smallest_safe_next_action,
            metacognitive_guidance_applied=metacognitive_guidance.applied,
            metacognitive_guidance_summary=metacognitive_guidance.summary,
            metacognitive_effects=metacognitive_guidance.effects,
            metacognitive_containment_recommendation=(
                metacognitive_guidance.containment_recommendation
            ),
            semantic_memory_source=memory_decision.semantic_source,
            procedural_memory_source=memory_decision.procedural_source,
            semantic_memory_effects=list(memory_decision.semantic_effects),
            procedural_memory_effects=list(memory_decision.procedural_effects),
            semantic_memory_lifecycle=memory_decision.semantic_lifecycle,
            procedural_memory_lifecycle=memory_decision.procedural_lifecycle,
            semantic_memory_state=memory_decision.semantic_memory_state,
            procedural_memory_state=memory_decision.procedural_memory_state,
            memory_lifecycle_status=memory_decision.lifecycle_status,
            memory_review_status=memory_decision.review_status,
            memory_consolidation_status=memory_decision.consolidation_status,
            memory_fixation_status=memory_decision.fixation_status,
            memory_archive_status=memory_decision.archive_status,
            procedural_artifact_status=context.procedural_artifact_status,
            procedural_artifact_ref=context.procedural_artifact_ref,
            procedural_artifact_version=context.procedural_artifact_version,
            procedural_artifact_summary=context.procedural_artifact_summary,
            mind_disagreement_status=mind_disagreement_status,
            mind_validation_checkpoints=mind_validation_checkpoints,
            continuity_action=continuity_action,
            continuity_reason=continuity_reason,
            open_loops=open_loops,
            continuity_source=continuity_source,
            continuity_target_mission_id=(
                context.related_mission_id if continuity_source == "related_mission" else None
            ),
            continuity_target_goal=(
                context.related_mission_goal
                if continuity_source == "related_mission"
                else mission_goal
            ),
            continuity_replay_status=context.continuity_replay_status,
            continuity_recovery_mode=context.continuity_recovery_mode,
            continuity_resume_point=context.continuity_resume_point,
        )
        return self._validate_plan_contract(plan, context=context)

    def refine_task_plan(
        self,
        plan: DeliberativePlanContract,
        *,
        specialist_summary: str,
        specialist_contributions: list[SpecialistContributionContract],
    ) -> DeliberativePlanContract:
        """Refine a plan with subordinated specialist contributions."""

        if not specialist_contributions:
            return plan

        refined_steps = list(plan.steps)
        refined_constraints = list(plan.constraints)
        refined_risks = list(plan.risks)
        success_criteria = list(plan.success_criteria)
        requires_human_validation = plan.requires_human_validation
        open_loop_hints = list(plan.open_loops)

        for contribution in specialist_contributions:
            extra_step = self._specialist_step(contribution.specialist_type)
            if extra_step and extra_step not in refined_steps:
                refined_steps.append(extra_step)
            for finding in contribution.findings:
                if finding.startswith("constraint:"):
                    constraint = finding.removeprefix("constraint:").strip()
                    if constraint and constraint not in refined_constraints:
                        refined_constraints.append(constraint)
                elif finding.startswith("risk:"):
                    risk = finding.removeprefix("risk:").strip()
                    if risk and risk not in refined_risks:
                        refined_risks.append(risk)
                elif finding.startswith("open_loop:"):
                    loop = finding.removeprefix("open_loop:").strip()
                    if loop and loop not in open_loop_hints:
                        open_loop_hints.append(loop)
                elif finding.startswith("success:"):
                    criterion = finding.removeprefix("success:").strip()
                    if criterion and criterion not in success_criteria:
                        success_criteria.append(criterion)
            if contribution.specialist_type == GOVERNANCE_REVIEW_SPECIALIST:
                requires_human_validation = True

        if open_loop_hints:
            loop_constraint = (
                f"manter loops abertos sob controle: {', '.join(open_loop_hints[:2])}"
            )
            if loop_constraint not in refined_constraints:
                refined_constraints.append(loop_constraint)

        resolution_summary = self._specialist_resolution_summary(
            specialist_contributions,
            specialist_summary,
        )
        return replace(
            plan,
            steps=refined_steps,
            constraints=refined_constraints,
            risks=refined_risks,
            requires_human_validation=requires_human_validation,
            success_criteria=success_criteria,
            specialist_resolution_summary=resolution_summary,
            open_loops=open_loop_hints[:3],
            rationale=f"{plan.rationale}; resolucao_especialistas={resolution_summary}",
        )

    def _validate_plan_contract(
        self,
        plan: DeliberativePlanContract,
        *,
        context: PlanningContext,
    ) -> DeliberativePlanContract:
        validation = validate_contract_instance(
            plan,
            schema=DELIBERATIVE_PLAN_SCHEMA,
        )
        if validation.status == "coherent":
            return replace(
                plan,
                contract_validation_status="coherent",
                contract_validation_errors=[],
                contract_validation_retry_applied=False,
            )

        repaired_plan = self._repair_plan_contract(
            plan,
            context=context,
            errors=validation.errors,
        )
        repaired_validation = validate_contract_instance(
            repaired_plan,
            schema=DELIBERATIVE_PLAN_SCHEMA,
        )
        repaired_status = (
            "repaired" if repaired_validation.status == "coherent" else "invalid"
        )
        return replace(
            repaired_plan,
            contract_validation_status=repaired_status,
            contract_validation_errors=(
                list(validation.errors)
                if repaired_status == "repaired"
                else list(repaired_validation.errors)
            ),
            contract_validation_retry_applied=True,
        )

    def _repair_plan_contract(
        self,
        plan: DeliberativePlanContract,
        *,
        context: PlanningContext,
        errors: list[str],
    ) -> DeliberativePlanContract:
        missing_fields = {
            error.removeprefix("missing_required_field:")
            for error in errors
            if error.startswith("missing_required_field:")
        }
        if not missing_fields:
            return plan

        goal = plan.goal or context.dominant_goal or context.query
        repair_fields: dict[str, object] = {}
        if "goal" in missing_fields:
            repair_fields["goal"] = goal or "manter leitura segura do objetivo atual"
        if "plan_summary" in missing_fields:
            repair_fields["plan_summary"] = (
                f"objetivo={goal or 'manter leitura segura do objetivo atual'}; "
                "validacao=repair_applied"
            )
        if "steps" in missing_fields:
            fallback_step = (
                plan.smallest_safe_next_action
                or "clarificar a menor proxima acao segura antes de operar"
            )
            repair_fields["steps"] = [fallback_step]
        if "active_domains" in missing_fields:
            repair_fields["active_domains"] = list(
                plan.active_domains
                or context.active_domains
                or ["assistencia_pessoal_e_operacional"]
            )
        if "active_minds" in missing_fields:
            repair_fields["active_minds"] = list(
                plan.active_minds or context.active_minds or ["mente_executiva"]
            )
        if "constraints" in missing_fields:
            repair_fields["constraints"] = list(plan.constraints) or [
                "preservar governanca, rastreabilidade e reversibilidade",
            ]
        if "risks" in missing_fields:
            repair_fields["risks"] = list(plan.risks) or [
                "nenhum risco material explicitado; manter revisao governada",
            ]
        if "recommended_task_type" in missing_fields:
            repair_fields["recommended_task_type"] = (
                plan.recommended_task_type or "general_response"
            )
        if "rationale" in missing_fields:
            repair_fields["rationale"] = (
                f"validacao_canonicidade=repair_applied; "
                f"objetivo_dominante={goal or 'indefinido'}"
            )
        if "success_criteria" in missing_fields:
            repair_fields["success_criteria"] = list(plan.success_criteria) or [
                "resposta deve permanecer coerente com o objetivo e a governanca",
            ]
        return replace(plan, **repair_fields)

    @staticmethod
    def _specialist_step(specialist_type: str) -> str | None:
        if specialist_type == OPERATIONAL_PLANNING_SPECIALIST:
            return "validar checkpoint intermediario apos a primeira etapa"
        if specialist_type == STRUCTURED_ANALYSIS_SPECIALIST:
            return "explicitar criterio dominante antes da conclusao final"
        if specialist_type == GOVERNANCE_REVIEW_SPECIALIST:
            return "confirmar limites normativos e condicoes de auditoria"
        return None

    def _build_steps(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
        mission_goal: str,
        goal_conflict: str | None,
        open_loops: list[str],
    ) -> list[str]:
        loop_focus = self._open_loop_focus(open_loops)
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        if context.continuity_requires_manual_resume:
            resume_point = context.continuity_resume_point or "ultimo checkpoint consistente"
            steps = [
                f"revisar o ponto de retomada antes de continuar: {resume_point}",
                "conter a continuidade em modo governado ate validacao explicita",
                "retomar o fluxo apenas depois de confirmar a direcao segura",
            ]
        elif context.requires_clarification:
            steps = [
                "clarificar a leitura atual do pedido",
                "pedir confirmacao do objetivo ou do resultado esperado",
                "adiar qualquer operacao ate haver direcao suficiente",
            ]
        elif continuity_action == "reformular":
            steps = [
                "explicitar o conflito entre o novo pedido e a missao ativa",
                "decidir se o objetivo atual substitui, adia ou preserva a missao em curso",
                "manter a resposta em orientacao governavel antes de qualquer operacao",
            ]
        elif continuity_action == "retomar":
            related_goal = context.related_mission_goal or mission_goal
            steps = [
                f"retomar a linha de continuidade relacionada: {related_goal}",
                "explicitar por que a retomada relacionada vence abrir um escopo novo",
                "reancorar a resposta no objetivo relacionado antes de operar",
            ]
        elif context.intent == "analysis":
            steps = [
                "consolidar o contexto e a evidencia relevante",
                "comparar trade-offs e implicacoes principais",
                "entregar recomendacao argumentada sem executar mudanca",
            ]
        elif context.intent == "planning":
            steps = [
                "definir o objetivo dominante e o criterio de sucesso",
                "decompor em etapas reversiveis e priorizadas",
                "executar apenas a menor proxima acao segura quando apropriado",
            ]
        else:
            steps = [
                "interpretar o objetivo imediato sem ampliar escopo",
                "fornecer orientacao executiva compacta e coerente",
            ]

        if (
            continuity_action == "continuar"
            and len(steps) < 5
            and not context.continuity_requires_manual_resume
        ):
            if loop_focus:
                steps.insert(0, f"retomar o loop principal da missao: {loop_focus}")
            else:
                steps.insert(0, "continuar o fio condutor da missao antes de abrir novo escopo")
        elif continuity_action == "encerrar" and len(steps) < 5:
            if loop_focus:
                steps.insert(0, f"fechar explicitamente o loop principal: {loop_focus}")
            else:
                steps.insert(0, "fechar explicitamente o loop ativo antes de abrir nova frente")
        elif continuity_action == "retomar" and len(steps) < 5:
            steps.insert(
                0,
                "retomar explicitamente a missao relacionada antes de abrir novo escopo",
            )
        elif continuity_action == "reformular" and len(steps) < 5 and goal_conflict:
            steps.insert(
                0,
                f"reformular a missao ativa sem perder rastreabilidade: {mission_goal}",
            )

        if context.mission_recommendation and len(steps) < 4:
            steps.append(
                "usar a recomendacao anterior como checkpoint antes da conclusao final"
            )
        semantic_step = self._semantic_memory_step(context, guidance=guidance)
        if semantic_step and semantic_step not in steps:
            steps.insert(1 if steps else 0, semantic_step)
            steps = steps[:5]
        procedural_step = self._procedural_memory_step(context, guidance=guidance)
        if procedural_step and procedural_step not in steps:
            steps.insert(2 if len(steps) > 1 else len(steps), procedural_step)
            steps = steps[:5]
        workflow_step_label = self._present_contract_label(
            (context.route_workflow_steps or [None])[0]
        )
        if workflow_step_label and len(steps) < 5:
            steps.append(f"cobrir a etapa do workflow ativo: {workflow_step_label}")
        deliverable_labels = [
            label
            for item in (context.route_expected_deliverables or [])[:2]
            if (label := self._present_contract_label(item))
        ]
        if deliverable_labels and len(steps) < 5:
            if len(deliverable_labels) == 1:
                deliverable_hint = deliverable_labels[0]
            else:
                deliverable_hint = " e ".join(deliverable_labels)
            steps.append(f"orientar a saida para {deliverable_hint} da rota ativa")
        workflow_label = self._present_contract_label(context.route_workflow_profile)
        if workflow_label and len(steps) < 5:
            steps.append(
                f"manter o workflow ativo: {workflow_label}, priorizando {guidance.planning_focus}"
            )
        return steps[:5]

    def _build_constraints(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
        open_loops: list[str],
        goal_conflict: str | None,
    ) -> list[str]:
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        constraints = [
            "manter escopo reversivel",
            "preservar rastreabilidade",
            "evitar efeitos externos nao validados",
        ]
        if context.dominant_tension:
            constraints.append("manter a tensao dominante resolvida antes de operar")
        if context.supporting_minds:
            constraints.append("fundir apoio cognitivo em uma unica linha de resposta")
        if context.requires_clarification:
            constraints.insert(0, "clarificar objetivo antes de operar")
        if context.continuity_requires_manual_resume:
            constraints.insert(
                0,
                "nao retomar automaticamente a partir de checkpoint governado ou contido",
            )
        if open_loops:
            constraints.append("tratar a missao ativa como referencia antes de expandir escopo")
        if context.route_consumer_profile:
            constraints.append(
                f"preservar o contrato guiado da rota ativa: {context.route_consumer_profile}"
            )
        workflow_decision_label = self._present_contract_label(
            (context.route_workflow_decision_points or [None])[0]
        )
        if workflow_decision_label:
            constraints.append(
                f"governar o decision point ativo: {workflow_decision_label}"
            )
        telemetry_label = self._present_contract_label(
            (context.route_telemetry_focus or [None])[0]
        )
        if telemetry_label:
            constraints.append(f"preservar o foco observavel da rota ativa: {telemetry_label}")
        semantic_anchor = self._semantic_memory_anchor(context)
        if semantic_anchor:
            constraints.append(
                "usar memoria semantica apenas para "
                f"{guidance.semantic_memory_role}: {semantic_anchor}"
            )
        procedural_anchor = self._procedural_memory_anchor(context)
        if procedural_anchor:
            constraints.append(
                "usar memoria procedural apenas para "
                f"{guidance.procedural_memory_role}: {procedural_anchor}"
            )
        if context.context_compaction_status in {
            "compressed_live_context",
            "seeded_live_context",
        }:
            constraints.append(
                "preservar contexto vivo compactado sem reabrir historico bruto da sessao"
            )
        if context.cross_session_recall_status == "active":
            constraints.append(
                "usar recall cross-session apenas por resumo soberano e rastreavel"
            )
        if continuity_action == "retomar":
            constraints.append(
                "explicitar por que a retomada relacionada vence abrir um escopo novo"
            )
        if continuity_action == "reformular" and goal_conflict:
            constraints.append("nao permitir desvio silencioso da missao ativa")
        return constraints

    def _build_risks(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
        goal_conflict: str | None,
    ) -> list[str]:
        risks: list[str] = []
        if context.risk_markers:
            risks.append("pedido contem sinais de risco operacional")
        if context.requires_clarification:
            risks.append("objetivo ainda ambiguo para execucao")
        if context.continuity_recovery_mode == "governed_review":
            risks.append("checkpoint recuperado ainda aguarda validacao explicita")
        if context.continuity_recovery_mode == "contained_recovery":
            risks.append("checkpoint recuperado partiu de uma contencao governada")
        if not context.knowledge_snippets:
            risks.append("sem apoio adicional de conhecimento alem do baseline local")
        if context.open_loops:
            risks.append("existem loops abertos que podem ampliar escopo da missao")
        if continuity_action == "retomar" and context.open_loops:
            risks.append(
                "retomada relacionada pode competir com loops ainda abertos da missao ativa"
            )
        if goal_conflict:
            risks.append(
                "pedido atual pode deslocar a missao ativa sem reformulacao explicita"
            )
        return risks or ["sem risco material alem do escopo controlado do v1"]

    def _mind_disagreement_status(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
    ) -> str:
        if not dominant_tension:
            return "not_applicable"
        supporting_count = len(context.supporting_minds or [])
        suppressed_count = len(context.suppressed_minds or [])
        if supporting_count == 0 and suppressed_count == 0:
            return "not_applicable"
        deep_workflow = context.route_workflow_profile in DEEP_COGNITIVE_WORKFLOWS
        if suppressed_count > 0 and deep_workflow:
            return "deep_review_required"
        if suppressed_count > 0 or (supporting_count >= 2 and deep_workflow):
            return "validation_required"
        return "contained"

    def _mind_validation_checkpoints(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
        disagreement_status: str,
    ) -> list[str]:
        if disagreement_status == "not_applicable":
            return []
        checkpoints: list[str] = [
            f"validar a tensao dominante antes de concluir: {dominant_tension}"
        ]
        workflow_checkpoint_label = self._present_contract_label(
            (context.route_workflow_checkpoints or [None])[0]
        )
        if workflow_checkpoint_label:
            checkpoints.append(
                f"passar pelo checkpoint governado: {workflow_checkpoint_label}"
            )
        workflow_decision_label = self._present_contract_label(
            (context.route_workflow_decision_points or [None])[0]
        )
        if workflow_decision_label:
            checkpoints.append(
                f"revisar o decision point ativo sob discordancia: {workflow_decision_label}"
            )
        if context.suppressed_minds:
            suppressed = ", ".join((context.suppressed_minds or [])[:2])
            checkpoints.append(
                f"conferir se a linha final absorveu a discordancia de {suppressed}"
            )
        return checkpoints[:3]

    def _apply_mind_validation_guidance(
        self,
        *,
        steps: list[str],
        constraints: list[str],
        success_criteria: list[str],
        mind_validation_checkpoints: list[str],
        disagreement_status: str,
    ) -> tuple[list[str], list[str], list[str]]:
        if disagreement_status == "not_applicable":
            return steps, constraints, success_criteria

        updated_steps = list(steps)
        updated_constraints = list(constraints)
        updated_success = list(success_criteria)

        if mind_validation_checkpoints:
            validation_step = (
                f"executar validacao cognitiva: {mind_validation_checkpoints[0]}"
            )
            if validation_step not in updated_steps:
                updated_steps.append(validation_step)
        if disagreement_status in {"validation_required", "deep_review_required"}:
            constraint = "nao encerrar a resposta sem validacao cognitiva governada"
            if constraint not in updated_constraints:
                updated_constraints.append(constraint)
            criterion = (
                "saida final deve deixar explicito como a discordancia "
                "entre mentes foi resolvida"
            )
            if criterion not in updated_success:
                updated_success.append(criterion)
        if disagreement_status == "deep_review_required":
            deep_step = "adicionar um passo extra de revisao antes da conclusao final"
            if deep_step not in updated_steps:
                updated_steps.append(deep_step)
            deep_constraint = (
                "manter checkpoint adicional quando a tensao dominante exigir profundidade maior"
            )
            if deep_constraint not in updated_constraints:
                updated_constraints.append(deep_constraint)
        return updated_steps[:6], updated_constraints[:9], updated_success[:8]

    def _build_success_criteria(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
        open_loops: list[str],
        dominant_tension: str,
    ) -> list[str]:
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        criteria = [
            "resposta deve manter voz unificada e objetivo dominante explicito",
            "recomendacao deve ser executavel dentro do escopo controlado do v1",
        ]
        if context.intent == "analysis":
            criteria.append("conclusao deve explicitar o trade-off dominante")
        if context.intent == "planning":
            criteria.append("plano deve indicar a menor proxima acao segura")
        if continuity_action == "continuar":
            criteria.append("resposta deve fechar ou avancar o loop principal da missao")
        elif continuity_action == "encerrar":
            criteria.append("resposta deve fechar explicitamente o loop principal da missao")
        elif continuity_action == "retomar":
            criteria.append(
                "retomada relacionada deve parecer continuidade intencional, nao deriva arbitraria"
            )
        elif continuity_action == "reformular":
            criteria.append(
                "reformulacao da missao deve declarar o conflito com a meta ativa"
            )
        if open_loops and len(criteria) < 4:
            criteria.append("loop principal deve permanecer rastreavel na resposta final")
        semantic_anchor = self._semantic_memory_anchor(context)
        procedural_anchor = self._procedural_memory_anchor(context)
        if context.route_expected_deliverables and len(criteria) < 7:
            criterion = (
                f"saida deve refletir {context.route_expected_deliverables[0]} da rota ativa"
            )
            if semantic_anchor:
                criterion = (
                    f"{criterion} e manter {guidance.semantic_memory_role}"
                )
            criteria.append(criterion)
        primary_mind_label = self._present_contract_label(context.primary_mind)
        primary_domain_label = self._present_contract_label(context.primary_domain_driver)
        if primary_domain_label and dominant_tension and len(criteria) < 7:
            if primary_mind_label:
                criteria.append(
                    "ancora cognitiva "
                    f"{primary_mind_label} deve manter {primary_domain_label} "
                    f"explicito sob tensao {dominant_tension}"
                )
            else:
                criteria.append(
                    "dominio primario deve permanecer explicito em torno de "
                    f"{primary_domain_label} sob tensao {dominant_tension}"
                )
        elif primary_mind_label and dominant_tension and len(criteria) < 7:
            criteria.append(
                f"mente primaria {primary_mind_label} deve governar o criterio de saida "
                f"sob tensao {dominant_tension}"
            )
        workflow_checkpoint_label = self._present_contract_label(
            (context.route_workflow_checkpoints or [None])[0]
        )
        if workflow_checkpoint_label and len(criteria) < 7:
            criterion = (
                "checkpoint do workflow ativo deve chegar a "
                f"{workflow_checkpoint_label} e sustentar {guidance.success_focus}"
            )
            if procedural_anchor:
                criterion = (
                    f"{criterion} e preservar {guidance.procedural_memory_role}"
                )
            criteria.append(criterion)
        workflow_label = self._present_contract_label(context.route_workflow_profile)
        if workflow_label and len(criteria) < 7:
            criteria.append(
                "resposta deve manter o workflow ativo: "
                f"{workflow_label} com foco em {guidance.success_focus}"
            )
        elif context.route_workflow_profile and len(criteria) < 7:
            criteria.append(f"saida deve sustentar {guidance.success_focus}")
        return criteria[:7]

    def _recommended_task_type(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
    ) -> str:
        if context.requires_clarification:
            return "general_response"
        if context.continuity_requires_manual_resume:
            return "general_response"
        if continuity_action == "reformular":
            return "general_response"
        if context.intent == "analysis" or context.preferred_response_mode == "analysis_only":
            return "produce_analysis_brief"
        if context.intent == "planning":
            return "draft_plan"
        return "general_response"

    def _requires_human_validation(
        self,
        context: PlanningContext,
        *,
        risks: list[str],
        continuity_action: str,
        open_loops: list[str],
    ) -> bool:
        if context.intent == "analysis" and continuity_action != "reformular":
            return False
        if context.requires_clarification:
            return False
        if context.continuity_requires_manual_resume:
            return True
        if any(marker for marker in context.risk_markers):
            return True
        if continuity_action == "retomar" and bool(open_loops):
            return True
        if continuity_action == "reformular" and bool(
            open_loops or context.identity_continuity_brief
        ):
            return True
        return any("risco operacional" in risk for risk in risks)

    def _build_summary(
        self,
        context: PlanningContext,
        *,
        dominant_goal: str,
        mission_goal: str,
        dominant_tension: str,
        smallest_safe_next_action: str,
        metacognitive_guidance: MetacognitiveGuidance,
        memory_decision,
        continuity_action: str,
        continuity_reason: str,
        continuity_source: str,
    ) -> str:
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        mode = context.identity_mode or context.preferred_response_mode
        route_profile = context.route_consumer_profile or "none"
        workflow_profile = context.route_workflow_profile or "none"
        primary_mind = context.primary_mind or "none"
        primary_mind_family = context.primary_mind_family or "none"
        primary_domain_driver = context.primary_domain_driver or "none"
        arbitration_source = context.arbitration_source or "none"
        semantic_anchor = self._semantic_memory_anchor(context) or "none"
        procedural_anchor = self._procedural_memory_anchor(context) or "none"
        procedural_artifact_status = context.procedural_artifact_status or "none"
        procedural_artifact_ref = context.procedural_artifact_ref or "none"
        return (
            f"objetivo={dominant_goal}; missao_ativa={mission_goal}; modo={mode}; "
            f"mente_primaria={primary_mind}; familia_primaria={primary_mind_family}; "
            f"dominio_primario={primary_domain_driver}; arbitragem_fonte={arbitration_source}; "
            f"rota_primaria={context.primary_route or 'none'}; consumer_profile={route_profile}; "
            f"workflow_profile={workflow_profile}; workflow_focus={guidance.planning_focus}; "
            f"semantic_memory_anchor={semantic_anchor}; "
            f"procedural_memory_anchor={procedural_anchor}; "
            f"semantic_memory_source={memory_decision.semantic_source or 'none'}; "
            f"procedural_memory_source={memory_decision.procedural_source or 'none'}; "
            f"procedural_artifact_status={procedural_artifact_status}; "
            f"procedural_artifact_ref={procedural_artifact_ref}; "
            f"context_compaction={context.context_compaction_status or 'none'}; "
            f"cross_session_recall={context.cross_session_recall_status or 'none'}; "
            "semantic_memory_effects="
            f"{','.join(memory_decision.semantic_effects) or 'none'}; "
            "procedural_memory_effects="
            f"{','.join(memory_decision.procedural_effects) or 'none'}; "
            f"memory_lifecycle={memory_decision.lifecycle_status}; "
            f"memory_review={memory_decision.review_status}; "
            f"continuidade={continuity_action}; "
            f"fonte_continuidade={continuity_source}; "
            f"replay_status={context.continuity_replay_status or 'none'}; "
            f"recovery_mode={context.continuity_recovery_mode or 'none'}; "
            f"motivo_continuidade={continuity_reason}; "
            f"tensao={dominant_tension}; "
            f"metacognitive_guidance={metacognitive_guidance.summary or 'none'}; "
            f"metacognitive_effects={','.join(metacognitive_guidance.effects) or 'none'}; "
            f"proxima_acao={smallest_safe_next_action}"
        )

    def _build_rationale(
        self,
        context: PlanningContext,
        *,
        risks: list[str],
        dominant_goal: str,
        mission_goal: str,
        dominant_tension: str,
        metacognitive_guidance: MetacognitiveGuidance,
        memory_decision,
        continuity_action: str,
        goal_conflict: str | None,
        continuity_reason: str,
    ) -> str:
        context_hint = self._select_context_hint(context.recovered_context)
        knowledge_hint = (
            context.knowledge_snippets[0]
            if context.knowledge_snippets
            else "sem apoio extra de conhecimento"
        )
        continuity_hint = context.identity_continuity_brief or "sem fio de continuidade consolidado"
        semantic_hint = context.mission_semantic_brief or "sem memoria semantica de missao"
        open_loops = ", ".join((context.open_loops or [])[:3]) or "nenhum"
        related_goal = context.related_mission_goal or "nenhuma"
        related_reason = context.related_continuity_reason or "nenhuma"
        related_priority = (
            f"{context.related_continuity_priority:.2f}"
            if context.related_continuity_priority is not None
            else "0.00"
        )
        secondary = ", ".join((context.secondary_goals or [])[:2]) or "nenhum"
        arbitration = context.arbitration_summary or context.cognitive_rationale
        risk_text = "; ".join(risks)
        previous_recommendation = context.mission_recommendation or "sem recomendacao previa"
        ranking_summary = context.continuity_ranking_summary or "sem ranking explicito"
        conflict_text = goal_conflict or "nenhum"
        replay_status = context.continuity_replay_status or "none"
        recovery_mode = context.continuity_recovery_mode or "none"
        resume_point = context.continuity_resume_point or "nenhum"
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        route_profile = context.route_consumer_profile or "none"
        route_objective = context.route_consumer_objective or "none"
        route_deliverables = ",".join((context.route_expected_deliverables or [])[:3]) or "none"
        route_telemetry = ",".join((context.route_telemetry_focus or [])[:3]) or "none"
        route_workflow = context.route_workflow_profile or "none"
        workflow_checkpoints = ",".join((context.route_workflow_checkpoints or [])[:3]) or "none"
        workflow_decisions = ",".join((context.route_workflow_decision_points or [])[:3]) or "none"
        primary_mind = context.primary_mind or "none"
        primary_mind_family = context.primary_mind_family or "none"
        primary_domain_driver = context.primary_domain_driver or "none"
        arbitration_source = context.arbitration_source or "none"
        semantic_anchor = self._semantic_memory_anchor(context) or "none"
        procedural_anchor = self._procedural_memory_anchor(context) or "none"
        procedural_artifact_status = context.procedural_artifact_status or "none"
        procedural_artifact_ref = context.procedural_artifact_ref or "none"
        procedural_artifact_version = (
            str(context.procedural_artifact_version)
            if context.procedural_artifact_version is not None
            else "none"
        )
        procedural_artifact_summary = context.procedural_artifact_summary or "none"
        user_scope_status = context.user_scope_status or "none"
        user_domain_focus = ",".join((context.user_domain_focus or [])[:3]) or "none"
        user_task_type = context.user_last_recommended_task_type or "none"
        user_continuity_preference = context.user_continuity_preference or "none"
        context_compaction = context.context_compaction_status or "none"
        context_compaction_summary = context.context_compaction_summary or "none"
        context_live_summary = context.context_live_summary or "none"
        cross_session_recall = context.cross_session_recall_status or "none"
        cross_session_summary = context.cross_session_recall_summary or "none"
        return (
            f"objetivo_dominante={dominant_goal}; missao_ativa={mission_goal}; "
            f"objetivos_secundarios={secondary}; continuidade={continuity_hint}; "
            f"mente_primaria={primary_mind}; familia_primaria={primary_mind_family}; "
            f"dominio_primario={primary_domain_driver}; arbitragem_fonte={arbitration_source}; "
            f"loops_abertos={open_loops}; acao_continuidade={continuity_action}; "
            f"rota_primaria={context.primary_route or 'none'}; consumer_profile={route_profile}; "
            f"consumer_objective={route_objective}; deliverables={route_deliverables}; "
            f"telemetry_focus={route_telemetry}; workflow_profile={route_workflow}; "
            f"workflow_focus={guidance.planning_focus}; response_focus={guidance.response_focus}; "
            f"workflow_checkpoints={workflow_checkpoints}; "
            f"workflow_decision_points={workflow_decisions}; "
            f"semantic_memory_anchor={semantic_anchor}; "
            f"procedural_memory_anchor={procedural_anchor}; "
            f"semantic_memory_source={memory_decision.semantic_source or 'none'}; "
            f"procedural_memory_source={memory_decision.procedural_source or 'none'}; "
            f"procedural_artifact_status={procedural_artifact_status}; "
            f"procedural_artifact_ref={procedural_artifact_ref}; "
            f"procedural_artifact_version={procedural_artifact_version}; "
            f"procedural_artifact_summary={procedural_artifact_summary}; "
            "semantic_memory_effects="
            f"{','.join(memory_decision.semantic_effects) or 'none'}; "
            "procedural_memory_effects="
            f"{','.join(memory_decision.procedural_effects) or 'none'}; "
            f"semantic_memory_lifecycle={memory_decision.semantic_lifecycle or 'none'}; "
            f"procedural_memory_lifecycle={memory_decision.procedural_lifecycle or 'none'}; "
            f"semantic_memory_state={memory_decision.semantic_memory_state or 'none'}; "
            f"procedural_memory_state={memory_decision.procedural_memory_state or 'none'}; "
            f"memory_lifecycle={memory_decision.lifecycle_status}; "
            f"memory_review={memory_decision.review_status}; "
            f"memory_consolidation={memory_decision.consolidation_status}; "
            f"memory_fixation={memory_decision.fixation_status}; "
            f"memory_archive={memory_decision.archive_status}; "
            f"user_scope_status={user_scope_status}; "
            f"user_domain_focus={user_domain_focus}; "
            f"user_last_recommended_task_type={user_task_type}; "
            f"user_continuity_preference={user_continuity_preference}; "
            f"context_compaction={context_compaction}; "
            f"context_compaction_summary={context_compaction_summary}; "
            f"context_live_summary={context_live_summary}; "
            f"cross_session_recall={cross_session_recall}; "
            f"cross_session_summary={cross_session_summary}; "
            f"replay_status={replay_status}; recovery_mode={recovery_mode}; "
            f"resume_point={resume_point}; "
            f"motivo_continuidade={continuity_reason}; "
            f"conflito_missao={conflict_text}; contexto={context_hint}; apoio={knowledge_hint}; "
            f"arbitragem={arbitration}; tensao={dominant_tension}; "
            f"metacognitive_guidance={metacognitive_guidance.summary or 'none'}; "
            f"metacognitive_effects={','.join(metacognitive_guidance.effects) or 'none'}; "
            f"metacognitive_containment="
            f"{metacognitive_guidance.containment_recommendation or 'none'}; "
            f"memoria_semantica={semantic_hint}; recomendacao_previa={previous_recommendation}; "
            f"missao_relacionada={related_goal}; razao_relacionada={related_reason}; "
            f"prioridade_relacionada={related_priority}; ranking_continuidade={ranking_summary}; "
            f"riscos={risk_text}"
        )

    def _continuity_action(
        self,
        context: PlanningContext,
        *,
        mission_goal: str,
        goal_conflict: str | None,
    ) -> str:
        if goal_conflict:
            return "reformular"
        lowered_query = context.query.lower()
        if any(word in lowered_query for word in MISSION_CLOSE_KEYWORDS):
            return "encerrar"
        if (
            context.continuity_recommendation == "retomar_missao_relacionada"
            and context.related_mission_id
        ):
            return "retomar"
        if context.open_loops:
            return "continuar"
        if context.identity_continuity_brief or mission_goal or context.mission_semantic_brief:
            return "continuar"
        return "encerrar"

    def _smallest_safe_next_action(
        self,
        context: PlanningContext,
        steps: list[str],
        *,
        continuity_action: str,
        open_loops: list[str],
        goal_conflict: str | None,
        dominant_tension: str,
    ) -> str:
        loop_focus = self._open_loop_focus(open_loops)
        guidance = workflow_runtime_guidance(context.route_workflow_profile)
        semantic_anchor = self._semantic_memory_anchor(context)
        procedural_anchor = self._procedural_memory_anchor(context)
        action_anchor = self._metacognitive_action_anchor(
            context,
            dominant_tension=dominant_tension,
        )
        deliverable_label = self._present_contract_label(
            (context.route_expected_deliverables or [None])[0]
        )
        if context.requires_clarification:
            return "pedir confirmacao antes de qualquer execucao"
        if continuity_action == "reformular":
            if loop_focus:
                if action_anchor:
                    return f"explicitar como o novo pedido afeta {loop_focus}; {action_anchor}"
                return f"explicitar como o novo pedido afeta {loop_focus}"
            if goal_conflict:
                if action_anchor:
                    return (
                        "explicitar se o novo pedido substitui ou adia a missao ativa; "
                        f"{action_anchor}"
                    )
                return "explicitar se o novo pedido substitui ou adia a missao ativa"
        if context.continuity_requires_manual_resume:
            if context.continuity_resume_point:
                return (
                    "explicitar o ponto de retomada e pedir validacao antes de "
                    f"continuar: {context.continuity_resume_point}"
                )
            return "pedir validacao antes de retomar qualquer continuidade"
        if continuity_action == "retomar":
            if context.related_mission_goal:
                if action_anchor:
                    return (
                        "explicitar por que a missao relacionada deve ser retomada antes de "
                        f"abrir novo escopo; {action_anchor}"
                    )
                return (
                    "explicitar por que a missao relacionada deve ser retomada antes de "
                    "abrir novo escopo"
                )
            if action_anchor:
                return (
                    "retomar a continuidade relacionada antes de abrir novo escopo; "
                    f"{action_anchor}"
                )
            return "retomar a continuidade relacionada antes de abrir novo escopo"
        if continuity_action == "encerrar" and loop_focus:
            if action_anchor:
                return f"fechar {loop_focus} com criterio explicito; {action_anchor}"
            return f"fechar {loop_focus} com criterio explicito"
        if continuity_action == "continuar" and loop_focus:
            if procedural_anchor and context.route_workflow_profile:
                action = (
                    f"retomar {loop_focus} preservando "
                    f"{guidance.procedural_memory_role}: {procedural_anchor}"
                )
                if action_anchor:
                    return f"{action}; {action_anchor}"
                return action
            if action_anchor:
                return f"retomar {loop_focus} antes de abrir novo escopo; {action_anchor}"
            return f"retomar {loop_focus} antes de abrir novo escopo"
        if (
            continuity_action == "continuar"
            and context.related_mission_id
            and context.related_continuity_priority
            and context.related_continuity_priority >= 0.6
        ):
            return "explicitar se a nova missao deve herdar continuidade de uma missao relacionada"
        if context.intent == "analysis":
            if semantic_anchor and context.route_workflow_profile:
                action = (
                    "explicitar o trade-off dominante usando "
                    f"{guidance.semantic_memory_role}: {semantic_anchor}"
                )
                if action_anchor:
                    return f"{action}; {action_anchor}"
                return action
            if action_anchor:
                return f"explicitar o trade-off dominante antes de recomendar; {action_anchor}"
            return "explicitar o trade-off dominante antes de recomendar"
        if (
            context.intent == "planning"
            and procedural_anchor
            and context.route_workflow_profile
            and deliverable_label
        ):
            action = (
                f"preservar {guidance.procedural_memory_role}: {procedural_anchor}; "
                f"convergir para {deliverable_label}"
            )
            if action_anchor:
                return f"{action}; {action_anchor}"
            return action
        if steps:
            return steps[0]
        return "avaliar pedido sem ampliar escopo"

    def _build_metacognitive_guidance(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
        continuity_action: str,
        goal_conflict: str | None,
        success_criteria: list[str],
        smallest_safe_next_action: str,
    ) -> MetacognitiveGuidance:
        summary = self._metacognitive_guidance_summary(
            context,
            dominant_tension=dominant_tension,
        )
        if summary is None:
            return MetacognitiveGuidance(
                applied=False,
                summary=None,
                effects=[],
                containment_recommendation=None,
            )
        effects: list[str] = []
        if any(
            criterion.startswith("ancora cognitiva")
            or criterion.startswith("mente primaria")
            for criterion in success_criteria
        ):
            effects.append("success_criteria")
        if "ancora cognitiva" in smallest_safe_next_action:
            effects.append("smallest_safe_next_action")
        containment_recommendation = self._metacognitive_containment_recommendation(
            context,
            dominant_tension=dominant_tension,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
        )
        if containment_recommendation is not None:
            effects.append("containment_recommendation")
        return MetacognitiveGuidance(
            applied=bool(effects),
            summary=summary,
            effects=effects,
            containment_recommendation=containment_recommendation,
        )

    def _metacognitive_guidance_summary(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
    ) -> str | None:
        if not dominant_tension:
            return None
        primary_mind_label = self._present_contract_label(context.primary_mind)
        primary_domain_label = self._present_contract_label(context.primary_domain_driver)
        primary_route_label = self._present_contract_label(context.primary_route)
        if primary_mind_label and primary_domain_label and primary_route_label:
            return (
                f"{primary_mind_label} ancora {primary_domain_label} via "
                f"{primary_route_label} sob tensao {dominant_tension}"
            )
        if primary_mind_label and primary_domain_label:
            return (
                f"{primary_mind_label} ancora {primary_domain_label} "
                f"sob tensao {dominant_tension}"
            )
        if primary_domain_label:
            return (
                f"dominio primario {primary_domain_label} ancora a deliberacao "
                f"sob tensao {dominant_tension}"
            )
        if primary_mind_label:
            return (
                f"mente primaria {primary_mind_label} ancora a deliberacao "
                f"sob tensao {dominant_tension}"
            )
        return None

    def _metacognitive_action_anchor(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
    ) -> str | None:
        summary = self._metacognitive_guidance_summary(
            context,
            dominant_tension=dominant_tension,
        )
        if summary is None:
            return None
        return f"ancora cognitiva: {summary}"

    def _metacognitive_containment_recommendation(
        self,
        context: PlanningContext,
        *,
        dominant_tension: str,
        continuity_action: str,
        goal_conflict: str | None,
    ) -> str | None:
        summary = self._metacognitive_guidance_summary(
            context,
            dominant_tension=dominant_tension,
        )
        if summary is None:
            return None
        if goal_conflict or continuity_action == "reformular":
            return (
                "conter ampliacao de escopo ate "
                f"{summary} explicitar como o pedido atual afeta a missao ativa"
            )
        if context.continuity_requires_manual_resume:
            return (
                "conter retomada automatica ate "
                f"{summary} validar o checkpoint recuperado"
            )
        if context.route_workflow_profile == "governance_boundary_workflow":
            return (
                "conter progressao ate "
                f"{summary} explicitar limites, condicoes e trilha governada"
            )
        return None

    def _resolve_dominant_tension(
        self,
        context: PlanningContext,
        goal_conflict: str | None,
    ) -> str:
        if goal_conflict:
            return "equilibrar continuidade da missao com a pressao por mudanca de objetivo"
        if context.continuity_requires_manual_resume:
            return "equilibrar retomada segura com validacao governada do checkpoint"
        if context.continuity_recommendation == "retomar_missao_relacionada" and context.open_loops:
            return "equilibrar loops ativos com a retomada de uma missao relacionada"
        if context.dominant_tension:
            return context.dominant_tension
        tensions = list(context.tensions or [])
        if tensions:
            return tensions[0]
        if context.related_mission_id:
            return "equilibrar a missao ativa com sinais de continuidade relacionada"
        return "manter foco executivo suficiente"

    @staticmethod
    def _continuity_source(
        context: PlanningContext,
        *,
        open_loops: list[str],
    ) -> str:
        if (
            context.continuity_recommendation == "retomar_missao_relacionada"
            and context.related_mission_id
        ):
            return "related_mission"
        if context.continuity_recommendation in {
            "priorizar_loop_ativo",
            "priorizar_missao_ativa",
        }:
            return "active_mission"
        if context.continuity_recommendation == "seguir_novo_pedido":
            return "fresh_request"
        if open_loops or context.identity_continuity_brief or context.mission_goal:
            return "active_mission"
        if context.related_mission_id:
            return "related_mission"
        return "fresh_request"

    def _continuity_reason(
        self,
        context: PlanningContext,
        *,
        mission_goal: str,
        continuity_action: str,
        goal_conflict: str | None,
    ) -> str:
        loop_focus = self._open_loop_focus(list(context.open_loops or []))
        if continuity_action == "reformular":
            return goal_conflict or "pedido atual exige reformulacao explicita da missao"
        if context.continuity_requires_manual_resume and context.continuity_resume_point:
            return (
                "checkpoint recuperado exige retomada governada a partir de "
                f"{context.continuity_resume_point}"
            )
        if continuity_action == "encerrar":
            if loop_focus:
                return f"pedido explicita fechamento do loop principal {loop_focus}"
            return "pedido atual indica encerramento controlado do escopo em curso"
        if continuity_action == "retomar":
            if context.continuity_ranking_summary:
                return context.continuity_ranking_summary
            if context.related_continuity_reason:
                return context.related_continuity_reason
            return (
                "retomar a continuidade relacionada oferece melhor ancora do que "
                "abrir um escopo novo"
            )
        if loop_focus:
            return f"existem loops ativos que mantem a missao atual ancorada em {loop_focus}"
        if context.mission_recommendation:
            return context.mission_recommendation
        if mission_goal:
            return f"manter a missao ativa como ancora principal: {mission_goal}"
        return "sem ancora suficiente para manter continuidade forte"

    def _mission_goal_conflict(
        self,
        context: PlanningContext,
        mission_goal: str,
    ) -> str | None:
        if not mission_goal or not (context.open_loops or context.identity_continuity_brief):
            return None
        lowered_query = context.query.lower()
        if any(word in lowered_query for word in MISSION_CLOSE_KEYWORDS):
            return None
        mission_tokens = self._meaningful_tokens(mission_goal)
        query_tokens = self._meaningful_tokens(context.query)
        if not mission_tokens or not query_tokens:
            return None
        overlap = mission_tokens.intersection(query_tokens)
        scope_shift = any(word in lowered_query for word in MISSION_SHIFT_KEYWORDS)
        if scope_shift and not overlap:
            return f"pedido atual desloca o foco da missao ativa '{mission_goal}'"
        return None

    @staticmethod
    def _seed_open_loops(
        context: PlanningContext,
        *,
        mission_goal: str,
        dominant_goal: str,
        continuity_action: str,
    ) -> list[str]:
        open_loops = list(context.open_loops or [])[:3]
        if open_loops or continuity_action != "continuar":
            return open_loops
        if context.intent != "planning":
            return open_loops
        for candidate in (mission_goal, dominant_goal, context.mission_recommendation):
            if candidate:
                return [candidate]
        return open_loops

    @staticmethod
    def _meaningful_tokens(text: str) -> set[str]:
        return {
            token
            for token in "".join(
                char if char.isalnum() else " " for char in text.lower()
            ).split()
            if len(token) > 3 and token not in IGNORED_TOKENS
        }

    @staticmethod
    def _open_loop_focus(open_loops: list[str]) -> str | None:
        return open_loops[0] if open_loops else None

    @staticmethod
    def _specialist_resolution_summary(
        contributions: list[SpecialistContributionContract],
        fallback_summary: str,
    ) -> str:
        if not contributions:
            return fallback_summary
        resolutions = [
            contribution.recommendation
            for contribution in contributions
            if contribution.recommendation
        ]
        return "; ".join(resolutions[:3]) or fallback_summary

    @staticmethod
    def _semantic_memory_anchor(context: PlanningContext) -> str | None:
        focus = ", ".join((context.mission_focus or [])[:2])
        if focus:
            return focus
        user_focus = ", ".join((context.user_domain_focus or [])[:2])
        if user_focus:
            return user_focus
        if context.related_mission_goal:
            return context.related_mission_goal
        return context.mission_semantic_brief

    def _semantic_memory_step(
        self,
        context: PlanningContext,
        *,
        guidance,
    ) -> str | None:
        if not self._semantic_memory_anchor(context) or not context.route_workflow_profile:
            return None
        route_objective = self._present_contract_label(context.route_consumer_objective)
        if route_objective:
            return (
                "usar memoria semantica para "
                f"{guidance.semantic_memory_role} antes de fechar {route_objective}"
            )
        deliverable_label = self._present_contract_label(
            (context.route_expected_deliverables or [None])[0]
        )
        if deliverable_label:
            return (
                "usar memoria semantica para "
                f"{guidance.semantic_memory_role} antes de consolidar {deliverable_label}"
            )
        return f"usar memoria semantica para {guidance.semantic_memory_role} antes da direcao final"

    @staticmethod
    def _procedural_memory_anchor(context: PlanningContext) -> str | None:
        return (
            context.mission_recommendation
            or context.last_decision_frame
            or context.continuity_resume_point
            or context.user_last_recommended_task_type
            or context.user_continuity_preference
        )

    def _procedural_memory_step(
        self,
        context: PlanningContext,
        *,
        guidance,
    ) -> str | None:
        if not self._procedural_memory_anchor(context) or not context.route_workflow_profile:
            return None
        deliverable_label = self._present_contract_label(
            (context.route_expected_deliverables or [None])[0]
        )
        if deliverable_label:
            return (
                "usar memoria procedural para "
                f"{guidance.procedural_memory_role} e sustentar {deliverable_label}"
            )
        return (
            "usar memoria procedural para "
            f"{guidance.procedural_memory_role} na proxima acao"
        )

    @staticmethod
    def _select_context_hint(recovered_context: list[str]) -> str:
        skipped_prefixes = (
            "mission_",
            "prior_",
            "identity_continuity_",
            "open_loops=",
            "last_decision_frame=",
            "context_compaction_",
            "context_live_summary=",
            "cross_session_recall_",
        )
        for item in reversed(recovered_context):
            if not item.startswith(skipped_prefixes):
                return item
        return recovered_context[-1] if recovered_context else "sem continuidade previa relevante"

    def _guided_memory_decision(
        self,
        context: PlanningContext,
        *,
        continuity_source: str,
    ):
        return guided_memory_decision(
            semantic_sources=self._semantic_memory_sources(context),
            procedural_sources=self._procedural_memory_sources(context),
            domain_compatible=bool(
                context.primary_route
                or context.primary_canonical_domain
                or context.route_workflow_profile
            ),
            workflow_profile=context.route_workflow_profile,
            continuity_source=continuity_source,
        )

    @staticmethod
    def _semantic_memory_sources(context: PlanningContext) -> list[str]:
        sources: list[str] = []
        if context.mission_focus or context.mission_semantic_brief:
            sources.append("active_mission")
        if context.related_mission_id and (
            context.related_mission_goal
            or context.related_continuity_reason
            or context.related_open_loops
        ):
            sources.append("related_mission")
        if (
            context.user_scope_status not in {None, "not_applicable", "incomplete"}
            and (
                context.user_domain_focus
                or context.user_continuity_preference
                or context.primary_canonical_domain
            )
        ):
            sources.append("user_scope")
        return sources

    @staticmethod
    def _procedural_memory_sources(context: PlanningContext) -> list[str]:
        sources: list[str] = []
        if (
            context.mission_recommendation
            or context.last_decision_frame
            or context.continuity_resume_point
        ):
            sources.append("active_mission")
        if context.related_mission_id and (
            context.related_continuity_reason
            or context.related_open_loops
            or context.related_mission_goal
        ):
            sources.append("related_mission")
        if (
            context.user_scope_status not in {None, "not_applicable", "incomplete"}
            and (
                context.user_last_recommended_task_type
                or context.user_continuity_preference
            )
        ):
            sources.append("user_scope")
        return sources

    def _apply_guided_memory_to_next_action(
        self,
        action: str,
        *,
        context: PlanningContext,
        memory_decision,
    ) -> str:
        if (
            not memory_decision.procedural_source
            or "next_action" not in memory_decision.procedural_effects
        ):
            return action
        anchor = self._procedural_memory_anchor(context)
        if not anchor or anchor in action:
            return action
        role = workflow_runtime_guidance(context.route_workflow_profile).procedural_memory_role
        return f"{action}; preservar {role}: {anchor}"

    def _apply_memory_causality_guidance(
        self,
        *,
        steps: list[str],
        constraints: list[str],
        success_criteria: list[str],
        context: PlanningContext,
        memory_decision,
    ) -> tuple[list[str], list[str], list[str]]:
        updated_steps = list(steps)
        updated_constraints = list(constraints)
        updated_success = list(success_criteria)
        guidance = workflow_runtime_guidance(context.route_workflow_profile)

        if "priority" in memory_decision.semantic_effects:
            semantic_step = (
                "priorizar a leitura semantica antes de consolidar o fechamento "
                f"do workflow: {guidance.semantic_memory_role}"
            )
            if semantic_step not in updated_steps:
                updated_steps.insert(0, semantic_step)
        if "depth" in memory_decision.semantic_effects:
            depth_constraint = (
                "nao reduzir a leitura final enquanto a memoria semantica ainda "
                f"estiver aprofundando {guidance.semantic_memory_role}"
            )
            if depth_constraint not in updated_constraints:
                updated_constraints.append(depth_constraint)
        if "recommendation" in memory_decision.semantic_effects:
            semantic_criterion = (
                "recomendacao final deve refletir o framing semantico dominante "
                "do workflow ativo"
            )
            if semantic_criterion not in updated_success:
                updated_success.append(semantic_criterion)

        if "priority" in memory_decision.procedural_effects:
            procedural_step = (
                "priorizar a memoria procedural na ordenacao da proxima acao segura"
            )
            if procedural_step not in updated_steps:
                updated_steps.append(procedural_step)
        if "depth" in memory_decision.procedural_effects:
            procedural_constraint = (
                "manter validacao procedural extra antes de concluir a resposta final"
            )
            if procedural_constraint not in updated_constraints:
                updated_constraints.append(procedural_constraint)
        if "recommendation" in memory_decision.procedural_effects:
            procedural_criterion = (
                "recomendacao final deve preservar a continuidade procedural do workflow"
            )
            if procedural_criterion not in updated_success:
                updated_success.append(procedural_criterion)

        return updated_steps[:7], updated_constraints[:10], updated_success[:9]
