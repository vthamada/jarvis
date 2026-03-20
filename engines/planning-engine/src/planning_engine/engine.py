"""Planning engine for operational task plans."""

from __future__ import annotations

from dataclasses import dataclass, replace

from shared.contracts import (
    DeliberativePlanContract,
    SpecialistContributionContract,
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
    cognitive_rationale: str = ""
    tensions: list[str] | None = None
    specialist_hints: list[str] | None = None
    dominant_goal: str | None = None
    secondary_goals: list[str] | None = None
    ambiguity_reason: str | None = None
    identity_mode: str | None = None
    primary_mind: str | None = None
    supporting_minds: list[str] | None = None
    dominant_tension: str | None = None
    arbitration_summary: str | None = None
    identity_continuity_brief: str | None = None
    open_loops: list[str] | None = None
    mission_semantic_brief: str | None = None
    mission_focus: list[str] | None = None
    last_decision_frame: str | None = None
    mission_goal: str | None = None
    mission_recommendation: str | None = None


class PlanningEngine:
    """Build concise operational plans from intent, context, and knowledge."""

    name = "planning-engine"

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
        open_loops = list(context.open_loops or [])[:3]
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
        )
        constraints = self._build_constraints(
            context,
            continuity_action=continuity_action,
            open_loops=open_loops,
            goal_conflict=goal_conflict,
        )
        risks = self._build_risks(context, goal_conflict=goal_conflict)
        success_criteria = self._build_success_criteria(
            context,
            continuity_action=continuity_action,
            open_loops=open_loops,
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
            continuity_action=continuity_action,
        )
        rationale = self._build_rationale(
            context,
            risks=risks,
            dominant_goal=dominant_goal,
            mission_goal=mission_goal,
            dominant_tension=dominant_tension,
            continuity_action=continuity_action,
            goal_conflict=goal_conflict,
        )
        return DeliberativePlanContract(
            plan_summary=plan_summary,
            goal=dominant_goal,
            steps=steps,
            active_domains=context.active_domains or ["assistencia_geral"],
            active_minds=context.active_minds,
            constraints=constraints,
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
            continuity_action=continuity_action,
            open_loops=open_loops,
        )

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
            if contribution.specialist_type == "especialista_revisao_governanca":
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

    @staticmethod
    def _specialist_step(specialist_type: str) -> str | None:
        if specialist_type == "especialista_planejamento_operacional":
            return "validar checkpoint intermediario apos a primeira etapa"
        if specialist_type == "especialista_analise_estruturada":
            return "explicitar criterio dominante antes da conclusao final"
        if specialist_type == "especialista_revisao_governanca":
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
        if context.requires_clarification:
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

        if continuity_action == "continuar" and len(steps) < 5:
            if loop_focus:
                steps.insert(0, f"retomar o loop principal da missao: {loop_focus}")
            else:
                steps.insert(0, "continuar o fio condutor da missao antes de abrir novo escopo")
        elif continuity_action == "encerrar" and len(steps) < 5:
            if loop_focus:
                steps.insert(0, f"fechar explicitamente o loop principal: {loop_focus}")
            else:
                steps.insert(0, "fechar explicitamente o loop ativo antes de abrir nova frente")
        elif continuity_action == "reformular" and len(steps) < 5 and goal_conflict:
            steps.insert(
                0,
                f"reformular a missao ativa sem perder rastreabilidade: {mission_goal}",
            )

        if context.mission_recommendation and len(steps) < 5:
            steps.append(
                "usar a recomendacao anterior como checkpoint antes da conclusao final"
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
        if open_loops:
            constraints.append("tratar a missao ativa como referencia antes de expandir escopo")
        if continuity_action == "reformular" and goal_conflict:
            constraints.append("nao permitir desvio silencioso da missao ativa")
        return constraints

    def _build_risks(
        self,
        context: PlanningContext,
        *,
        goal_conflict: str | None,
    ) -> list[str]:
        risks: list[str] = []
        if context.risk_markers:
            risks.append("pedido contem sinais de risco operacional")
        if context.requires_clarification:
            risks.append("objetivo ainda ambiguo para execucao")
        if not context.knowledge_snippets:
            risks.append("sem apoio adicional de conhecimento alem do baseline local")
        if context.open_loops:
            risks.append("existem loops abertos que podem ampliar escopo da missao")
        if goal_conflict:
            risks.append(
                "pedido atual pode deslocar a missao ativa sem reformulacao explicita"
            )
        return risks or ["sem risco material alem do escopo controlado do v1"]

    def _build_success_criteria(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
        open_loops: list[str],
    ) -> list[str]:
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
        elif continuity_action == "reformular":
            criteria.append(
                "reformulacao da missao deve declarar o conflito com a meta ativa"
            )
        if open_loops and len(criteria) < 4:
            criteria.append("loop principal deve permanecer rastreavel na resposta final")
        return criteria[:4]

    def _recommended_task_type(
        self,
        context: PlanningContext,
        *,
        continuity_action: str,
    ) -> str:
        if context.requires_clarification:
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
        if any(marker for marker in context.risk_markers):
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
        continuity_action: str,
    ) -> str:
        mode = context.identity_mode or context.preferred_response_mode
        return (
            f"objetivo={dominant_goal}; missao_ativa={mission_goal}; modo={mode}; "
            f"continuidade={continuity_action}; tensao={dominant_tension}; "
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
        continuity_action: str,
        goal_conflict: str | None,
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
        secondary = ", ".join((context.secondary_goals or [])[:2]) or "nenhum"
        arbitration = context.arbitration_summary or context.cognitive_rationale
        risk_text = "; ".join(risks)
        previous_recommendation = context.mission_recommendation or "sem recomendacao previa"
        conflict_text = goal_conflict or "nenhum"
        return (
            f"objetivo_dominante={dominant_goal}; missao_ativa={mission_goal}; "
            f"objetivos_secundarios={secondary}; continuidade={continuity_hint}; "
            f"loops_abertos={open_loops}; acao_continuidade={continuity_action}; "
            f"conflito_missao={conflict_text}; contexto={context_hint}; apoio={knowledge_hint}; "
            f"arbitragem={arbitration}; tensao={dominant_tension}; "
            f"memoria_semantica={semantic_hint}; recomendacao_previa={previous_recommendation}; "
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
    ) -> str:
        loop_focus = self._open_loop_focus(open_loops)
        if context.requires_clarification:
            return "pedir confirmacao antes de qualquer execucao"
        if continuity_action == "reformular":
            if loop_focus:
                return f"explicitar como o novo pedido afeta {loop_focus}"
            if goal_conflict:
                return "explicitar se o novo pedido substitui ou adia a missao ativa"
        if continuity_action == "encerrar" and loop_focus:
            return f"fechar {loop_focus} com criterio explicito"
        if continuity_action == "continuar" and loop_focus:
            return f"retomar {loop_focus} antes de abrir novo escopo"
        if context.intent == "analysis":
            return "explicitar o trade-off dominante antes de recomendar"
        if steps:
            return steps[0]
        return "avaliar pedido sem ampliar escopo"

    def _resolve_dominant_tension(
        self,
        context: PlanningContext,
        goal_conflict: str | None,
    ) -> str:
        if goal_conflict:
            return "equilibrar continuidade da missao com a pressao por mudanca de objetivo"
        if context.dominant_tension:
            return context.dominant_tension
        tensions = list(context.tensions or [])
        if tensions:
            return tensions[0]
        return "manter foco executivo suficiente"

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
    def _select_context_hint(recovered_context: list[str]) -> str:
        skipped_prefixes = (
            "mission_",
            "prior_",
            "identity_continuity_",
            "open_loops=",
            "last_decision_frame=",
        )
        for item in reversed(recovered_context):
            if not item.startswith(skipped_prefixes):
                return item
        return recovered_context[-1] if recovered_context else "sem continuidade previa relevante"