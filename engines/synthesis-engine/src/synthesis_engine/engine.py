"""Synthesis engine for the final JARVIS response."""

from __future__ import annotations

from dataclasses import dataclass

from identity_engine.engine import IdentityProfile
from shared.contracts import GovernanceDecisionContract, OperationResultContract
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
                f"Motivo: {synthesis_input.governance_decision.justification}"
            )

        snippets = synthesis_input.knowledge_snippets[:2]
        knowledge_brief = " | ".join(snippets) if snippets else "sem suporte adicional de conhecimento"
        context_brief = (
            synthesis_input.recovered_context[-1]
            if synthesis_input.recovered_context
            else "sem continuidade relevante previa"
        )
        operation_brief = (
            synthesis_input.operation_result.outputs[0]
            if synthesis_input.operation_result and synthesis_input.operation_result.outputs
            else "sem resultado operacional adicional"
        )
        return (
            f"JARVIS em modo {synthesis_input.response_style}. "
            f"Missao: {synthesis_input.identity_profile.mission_statement} "
            f"Contexto: {context_brief}. "
            f"Dominios ativos: {', '.join(synthesis_input.active_domains)}. "
            f"Mentes ativas: {', '.join(synthesis_input.active_minds)}. "
            f"Apoio: {knowledge_brief}. "
            f"Resultado: {operation_brief}"
        )
