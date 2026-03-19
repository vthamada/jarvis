"""Synthesis engine for the final JARVIS response."""

from __future__ import annotations

from dataclasses import dataclass

from identity_engine.engine import IdentityProfile

from shared.contracts import (
    DeliberativePlanContract,
    GovernanceDecisionContract,
    OperationResultContract,
)
from shared.types import PermissionDecision


@dataclass(frozen=True)
class SynthesisInput:
    """Inputs required to build the final response."""

    intent: str
    identity_profile: IdentityProfile
    response_style: str
    governance_decision: GovernanceDecisionContract
    recovered_context: list[str]
    active_minds: list[str]
    active_domains: list[str]
    knowledge_snippets: list[str]
    deliberative_plan: DeliberativePlanContract | None
    operation_result: OperationResultContract | None


class SynthesisEngine:
    """Compose the final textual synthesis of the current flow."""

    name = "synthesis-engine"

    def compose(self, synthesis_input: SynthesisInput) -> str:
        """Create a response that reflects identity, context, and outcome."""

        if synthesis_input.governance_decision.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            return (
                "Solicitacao recebida, mas a governanca atual nao permite execucao direta. "
                f"Motivo: {synthesis_input.governance_decision.justification} "
                f"Leitura atual: {self._goal_line(synthesis_input)}"
            )

        plan = synthesis_input.deliberative_plan
        context_brief = (
            synthesis_input.recovered_context[-1]
            if synthesis_input.recovered_context
            else "sem continuidade relevante previa"
        )
        knowledge_brief = (
            synthesis_input.knowledge_snippets[0]
            if synthesis_input.knowledge_snippets
            else "baseline local sem apoio extra"
        )
        operation_brief = (
            synthesis_input.operation_result.outputs[0]
            if synthesis_input.operation_result and synthesis_input.operation_result.outputs
            else "nenhuma operacao executada"
        )
        steps_brief = "; ".join(plan.steps[:3]) if plan else "sem plano estruturado adicional"
        risks_brief = "; ".join(plan.risks[:2]) if plan else "sem risco material relevante"
        rationale = plan.rationale if plan else "deliberacao compacta indisponivel"
        return (
            f"JARVIS em modo {synthesis_input.response_style}. "
            f"Leitura do objetivo: {self._goal_line(synthesis_input)}. "
            f"Linha de raciocinio: {rationale}. "
            f"Plano ou recomendacao: {steps_brief}. "
            f"Limites e riscos: {risks_brief}. "
            f"Contexto ativo: {context_brief}. "
            f"Dominios: {', '.join(synthesis_input.active_domains)}. "
            f"Mentes: {', '.join(synthesis_input.active_minds)}. "
            f"Apoio: {knowledge_brief}. "
            f"Resultado operacional: {operation_brief}"
        )

    @staticmethod
    def _goal_line(synthesis_input: SynthesisInput) -> str:
        if synthesis_input.deliberative_plan:
            return synthesis_input.deliberative_plan.goal
        return synthesis_input.identity_profile.mission_statement
