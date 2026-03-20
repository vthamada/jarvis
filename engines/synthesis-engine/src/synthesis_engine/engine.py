"""Synthesis engine for the final JARVIS response."""

from __future__ import annotations

from dataclasses import dataclass

from identity_engine.engine import IdentityProfile

from shared.contracts import (
    DeliberativePlanContract,
    GovernanceDecisionContract,
    OperationResultContract,
    SpecialistContributionContract,
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
    specialist_contributions: list[SpecialistContributionContract]
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
                "Solicitacao recebida, mas a governança atual não permite execução direta. "
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
            else "nenhuma operação executada"
        )
        steps_brief = self._steps_brief(plan)
        risks_brief = "; ".join(plan.risks[:2]) if plan else "sem risco material relevante"
        rationale = plan.rationale if plan else "deliberacao compacta indisponivel"
        arbitration = self._arbitration_brief(plan)
        specialists = self._specialist_brief(plan, synthesis_input.specialist_contributions)
        specialist_findings = self._specialist_findings_brief(
            synthesis_input.specialist_contributions
        )
        return (
            f"JARVIS em modo {synthesis_input.response_style}. "
            f"Leitura do objetivo: {self._goal_line(synthesis_input)}. "
            f"Linha de raciocinio: {rationale}. "
            f"Arbitragem interna: {arbitration}. "
            f"Plano ou recomendacao: {steps_brief}. "
            f"Especializacao subordinada: {specialists}. "
            f"Contribuições especialistas: {specialist_findings}. "
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

    @staticmethod
    def _steps_brief(plan: DeliberativePlanContract | None) -> str:
        if not plan:
            return "sem plano estruturado adicional"
        return "; ".join(plan.steps[:3])

    @staticmethod
    def _arbitration_brief(plan: DeliberativePlanContract | None) -> str:
        if not plan or not plan.tensions_considered:
            return "sem tensao material alem do baseline atual"
        return "; ".join(plan.tensions_considered[:2])

    @staticmethod
    def _specialist_brief(
        plan: DeliberativePlanContract | None,
        specialist_contributions: list[SpecialistContributionContract],
    ) -> str:
        if specialist_contributions:
            return ", ".join(item.specialist_type for item in specialist_contributions[:2])
        if not plan or not plan.specialist_hints:
            return "nenhum apoio especializado adicional necessario"
        return ", ".join(plan.specialist_hints[:2])

    @staticmethod
    def _specialist_findings_brief(
        specialist_contributions: list[SpecialistContributionContract],
    ) -> str:
        if not specialist_contributions:
            return "nenhuma contribuição especializada adicional"
        findings = [
            contribution.findings[0]
            for contribution in specialist_contributions
            if contribution.findings
        ]
        return "; ".join(findings[:2])
