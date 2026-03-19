"""Planning engine for operational task plans."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import DeliberativePlanContract


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


class PlanningEngine:
    """Build concise operational plans from intent, context, and knowledge."""

    name = "planning-engine"

    def build_task_plan(self, context: PlanningContext) -> DeliberativePlanContract:
        """Create a structured plan that is safe to pass into the operational layer."""

        steps = self._build_steps(context)
        constraints = [
            "manter escopo reversivel",
            "preservar rastreabilidade",
            "evitar efeitos externos nao validados",
        ]
        if context.requires_clarification:
            constraints.insert(0, "clarificar objetivo antes de operar")
        risks = self._build_risks(context)
        recommended_task_type = self._recommended_task_type(context)
        requires_human_validation = (
            bool(context.risk_markers) and recommended_task_type != "produce_analysis_brief"
        )
        plan_summary = self._build_summary(context, steps)
        rationale = self._build_rationale(context, risks)
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
        )

    @staticmethod
    def _build_steps(context: PlanningContext) -> list[str]:
        if context.requires_clarification:
            return [
                "clarificar a leitura atual do pedido",
                "pedir confirmacao do objetivo ou do resultado esperado",
                "adiar qualquer operacao ate haver direcao suficiente",
            ]
        if context.intent == "analysis":
            return [
                "consolidar contexto e sinais relevantes",
                "comparar trade-offs e implicacoes principais",
                "entregar recomendacao argumentada sem executar mudanca",
            ]
        if context.intent == "planning":
            return [
                "definir objetivo e criterio de aceite",
                "decompor em etapas reversiveis e priorizadas",
                "recomendar a menor proxima acao segura",
            ]
        return [
            "interpretar o objetivo imediato",
            "fornecer orientacao executiva compacta",
        ]

    @staticmethod
    def _build_risks(context: PlanningContext) -> list[str]:
        risks = []
        if context.risk_markers:
            risks.append("pedido contem sinais de risco operacional")
        if context.requires_clarification:
            risks.append("objetivo ainda ambiguo para execucao")
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
    def _build_summary(context: PlanningContext, steps: list[str]) -> str:
        leading_step = steps[0] if steps else "avaliar pedido"
        return (
            f"objetivo={context.query}; modo={context.preferred_response_mode}; "
            f"primeira_acao={leading_step}"
        )

    @staticmethod
    def _build_rationale(context: PlanningContext, risks: list[str]) -> str:
        context_hint = (
            context.recovered_context[-1]
            if context.recovered_context
            else "sem continuidade previa relevante"
        )
        knowledge_hint = (
            context.knowledge_snippets[0]
            if context.knowledge_snippets
            else "sem apoio extra de conhecimento"
        )
        return (
            f"contexto={context_hint}; apoio={knowledge_hint}; "
            f"mentes={', '.join(context.active_minds)}; riscos={'; '.join(risks)}"
        )
