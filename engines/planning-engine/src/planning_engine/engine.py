"""Planning engine for operational task plans."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanningContext:
    """Inputs that influence the task plan produced for an operation."""

    intent: str
    query: str
    recovered_context: list[str]
    active_domains: list[str]
    knowledge_snippets: list[str]


class PlanningEngine:
    """Build concise operational plans from intent, context, and knowledge."""

    name = "planning-engine"

    def build_task_plan(self, context: PlanningContext) -> str:
        """Create a short plan that is safe to pass into the operational layer."""

        focus = {
            "planning": "estruturar etapas praticas e priorizadas",
            "analysis": "examinar contexto, trade-offs e implicacoes",
            "general_assistance": "responder com orientacao direta e util",
        }.get(context.intent, "responder com seguranca e clareza")
        context_hint = (
            f"contexto previo: {context.recovered_context[-1]}"
            if context.recovered_context
            else "contexto previo: nenhum relevante"
        )
        knowledge_hint = (
            f"apoio de conhecimento: {context.knowledge_snippets[0]}"
            if context.knowledge_snippets
            else "apoio de conhecimento: heuristica local basica"
        )
        domains_hint = (
            f"dominios ativos: {', '.join(context.active_domains)}"
            if context.active_domains
            else "dominios ativos: assistencia geral"
        )
        return " | ".join([focus, context_hint, knowledge_hint, domains_hint])
