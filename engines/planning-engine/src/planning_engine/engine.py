"""Planning engine for operational task plans."""

from __future__ import annotations

from dataclasses import dataclass, replace

from shared.contracts import DeliberativePlanContract, SpecialistContributionContract


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


class PlanningEngine:
    """Build concise operational plans from intent, context, and knowledge."""

    name = "planning-engine"

    def build_task_plan(self, context: PlanningContext) -> DeliberativePlanContract:
        """Create a structured plan that is safe to pass into the operational layer."""

        tensions = list(context.tensions or [])
        specialist_hints = list(context.specialist_hints or [])
        semantic_brief = self._extract_context_hint(
            context.recovered_context, "mission_semantic_brief="
        )
        semantic_focus = self._extract_context_hint(context.recovered_context, "mission_focus=")
        steps = self._build_steps(context, specialist_hints, semantic_brief)
        constraints = [
            "manter escopo reversivel",
            "preservar rastreabilidade",
            "evitar efeitos externos não validados",
        ]
        if tensions:
            constraints.append("arbitrar tensoes internas antes de operar")
        if specialist_hints:
            constraints.append("manter especializacao subordinada ao núcleo")
        if context.requires_clarification:
            constraints.insert(0, "clarificar objetivo antes de operar")
        risks = self._build_risks(context)
        recommended_task_type = self._recommended_task_type(context)
        requires_human_validation = (
            bool(context.risk_markers) and recommended_task_type != "produce_analysis_brief"
        )
        plan_summary = self._build_summary(context, steps, tensions, semantic_brief)
        rationale = self._build_rationale(
            context,
            risks,
            tensions,
            specialist_hints,
            semantic_brief,
            semantic_focus,
        )
        return DeliberativePlanContract(
            plan_summary=plan_summary,
            goal=context.query,
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
        requires_human_validation = plan.requires_human_validation
        specialist_constraint = "incorporar contribuições especialistas antes da execução"

        if specialist_constraint not in refined_constraints:
            refined_constraints.append(specialist_constraint)

        for contribution in specialist_contributions:
            extra_step = self._specialist_step(contribution.specialist_type)
            if extra_step and extra_step not in refined_steps:
                refined_steps.append(extra_step)
            if contribution.specialist_type == "especialista_revisao_governanca":
                risk = "especialista recomenda cautela operacional reforçada"
                if risk not in refined_risks:
                    refined_risks.append(risk)
                requires_human_validation = True

        refined_summary = f"{plan.plan_summary}; especialistas={specialist_summary}"
        refined_rationale = f"{plan.rationale}; especialistas={specialist_summary}"
        return replace(
            plan,
            plan_summary=refined_summary,
            steps=refined_steps,
            constraints=refined_constraints,
            risks=refined_risks,
            requires_human_validation=requires_human_validation,
            rationale=refined_rationale,
        )

    @staticmethod
    def _specialist_step(specialist_type: str) -> str | None:
        if specialist_type == "especialista_planejamento_operacional":
            return "validar checkpoint intermediario após a primeira etapa"
        if specialist_type == "especialista_analise_estruturada":
            return "explicitar critério de decisão dominante antes da conclusao"
        if specialist_type == "especialista_revisao_governanca":
            return "confirmar limites normativos e condições de auditoria"
        return None

    @staticmethod
    def _build_steps(
        context: PlanningContext,
        specialist_hints: list[str],
        semantic_brief: str | None,
    ) -> list[str]:
        specialist_step = None
        if specialist_hints:
            specialist_step = (
                f"usar a lente subordinada {specialist_hints[0]} sem perder unidade de resposta"
            )
        if context.requires_clarification:
            steps = [
                "clarificar a leitura atual do pedido",
                "pedir confirmacao do objetivo ou do resultado esperado",
                "adiar qualquer operação até haver direção suficiente",
            ]
        elif context.intent == "analysis":
            steps = [
                "consolidar contexto e sinais relevantes",
                "comparar trade-offs e implicações principais",
                "entregar recomendacao argumentada sem executar mudanca",
            ]
        elif context.intent == "planning":
            steps = [
                "definir objetivo e critério de aceite",
                "decompor em etapas reversiveis e priorizadas",
                "recomendar a menor próxima ação segura",
            ]
        else:
            steps = [
                "interpretar o objetivo imediato",
                "fornecer orientacao executiva compacta",
            ]
        if semantic_brief and len(steps) < 5:
            continuity_step = "reconectar a resposta ao fio condutor semântico da missão atual"
            if continuity_step not in steps:
                steps.insert(1 if len(steps) > 1 else 0, continuity_step)
        if specialist_step and specialist_step not in steps and len(steps) < 5:
            steps.append(specialist_step)
        return steps

    @staticmethod
    def _build_risks(context: PlanningContext) -> list[str]:
        risks = []
        if context.risk_markers:
            risks.append("pedido contém sinais de risco operacional")
        if context.requires_clarification:
            risks.append("objetivo ainda ambiguo para execução")
        if not context.knowledge_snippets:
            risks.append("sem apoio adicional de conhecimento alem do baseline local")
        return risks or ["sem risco material alem do escopo controlado do v1"]

    @staticmethod
    def _recommended_task_type(context: PlanningContext) -> str:
        if context.requires_clarification:
            return "general_response"
        if context.intent == "analysis" or context.preferred_response_mode == "analysis_only":
            return "produce_analysis_brief"
        if context.intent == "planning":
            return "draft_plan"
        return "general_response"

    @staticmethod
    def _build_summary(
        context: PlanningContext,
        steps: list[str],
        tensions: list[str],
        semantic_brief: str | None,
    ) -> str:
        leading_step = steps[0] if steps else "avaliar pedido"
        tension = tensions[0] if tensions else "sem tensao material destacada"
        mission_hint = (
            "continuidade_semantica_ativa"
            if semantic_brief
            else "sem_continuidade_semantica"
        )
        return (
            f"objetivo={context.query}; modo={context.preferred_response_mode}; "
            f"primeira_acao={leading_step}; tensao={tension}; missão={mission_hint}"
        )

    @staticmethod
    def _build_rationale(
        context: PlanningContext,
        risks: list[str],
        tensions: list[str],
        specialist_hints: list[str],
        semantic_brief: str | None,
        semantic_focus: str | None,
    ) -> str:
        context_hint = PlanningEngine._select_context_hint(context.recovered_context)
        knowledge_hint = (
            context.knowledge_snippets[0]
            if context.knowledge_snippets
            else "sem apoio extra de conhecimento"
        )
        tension_hint = tensions[0] if tensions else "sem arbitragem adicional"
        specialist_hint = specialist_hints[0] if specialist_hints else "sem apoio especializado"
        cognitive_hint = context.cognitive_rationale or "sem rationale cognitivo adicional"
        mission_hint = semantic_brief or "sem continuidade semântica consolidada"
        focus_hint = semantic_focus or "sem foco semântico explícito"
        return (
            f"contexto={context_hint}; apoio={knowledge_hint}; "
            f"mentes={', '.join(context.active_minds)}; riscos={'; '.join(risks)}; "
            f"arbitragem={tension_hint}; especialista={specialist_hint}; "
            f"missão={mission_hint}; foco={focus_hint}; cognição={cognitive_hint}"
        )

    @staticmethod
    def _extract_context_hint(recovered_context: list[str], prefix: str) -> str | None:
        for item in reversed(recovered_context):
            if item.startswith(prefix):
                return item.removeprefix(prefix)
        return None

    @staticmethod
    def _select_context_hint(recovered_context: list[str]) -> str:
        for item in reversed(recovered_context):
            if not item.startswith(("mission_", "prior_")):
                return item
        return (
            recovered_context[-1]
            if recovered_context
            else "sem continuidade previa relevante"
        )
