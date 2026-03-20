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
    identity_mode: str | None = None
    arbitration_summary: str | None = None


class SynthesisEngine:
    """Compose the final textual synthesis of the current flow."""

    name = "synthesis-engine"

    def compose(self, synthesis_input: SynthesisInput) -> str:
        """Create a response that reflects identity, context, and outcome."""

        if synthesis_input.governance_decision.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            return self._compose_governed_response(synthesis_input)

        plan = synthesis_input.deliberative_plan
        if not plan:
            return "Leitura atual: manter a orientacao executiva dentro do escopo controlado do v1."

        parts = [
            f"Leitura do objetivo: {plan.goal}.",
            f"Julgamento: {self._judgment_line(synthesis_input)}.",
            f"Recomendacao: {self._recommendation_line(synthesis_input)}.",
        ]
        limitation = self._limitation_line(synthesis_input)
        if limitation:
            parts.append(f"Limite atual: {limitation}.")
        operational_result = self._operational_line(synthesis_input)
        if operational_result:
            parts.append(f"Resultado operacional: {operational_result}.")
        return " ".join(parts)

    def _compose_governed_response(self, synthesis_input: SynthesisInput) -> str:
        goal_line = self._goal_line(synthesis_input)
        judgment = (
            "a governanca atual exige conter a acao "
            "para preservar coerencia e seguranca"
        )
        return (
            f"Leitura do objetivo: {goal_line}. "
            f"Julgamento: {judgment}. "
            f"Recomendacao: {synthesis_input.governance_decision.justification}"
        )

    @staticmethod
    def _goal_line(synthesis_input: SynthesisInput) -> str:
        if synthesis_input.deliberative_plan:
            return synthesis_input.deliberative_plan.goal
        return synthesis_input.identity_profile.mission_statement

    def _judgment_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        arbitration = synthesis_input.arbitration_summary or plan.specialist_resolution_summary
        if arbitration:
            return arbitration
        return plan.rationale.split(";", maxsplit=1)[0]

    def _recommendation_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        if plan.smallest_safe_next_action:
            next_action = plan.smallest_safe_next_action
        elif plan.steps:
            next_action = plan.steps[0]
        else:
            next_action = "preservar uma proxima acao segura"
        success = (
            plan.success_criteria[0]
            if plan.success_criteria
            else "manter resposta coerente e reversivel"
        )
        recommendation = f"{next_action}; criterio de sucesso: {success}"
        if plan.specialist_resolution_summary:
            recommendation = (
                f"{recommendation}; ajuste interno: {plan.specialist_resolution_summary}"
            )
        return recommendation

    def _limitation_line(self, synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        limits: list[str] = []
        if synthesis_input.governance_decision.conditions:
            limits.append(synthesis_input.governance_decision.conditions[0])
        if plan.requires_human_validation:
            limits.append("o plano ainda pede validacao humana antes de ampliar escopo")
        material_risks = [risk for risk in plan.risks if "sem risco material" not in risk.lower()]
        if material_risks:
            limits.append(material_risks[0])
        return limits[0] if limits else None

    @staticmethod
    def _operational_line(synthesis_input: SynthesisInput) -> str | None:
        operation_result = synthesis_input.operation_result
        if not operation_result:
            return None
        if operation_result.outputs:
            return operation_result.outputs[0]
        return "saida operacional produzida sem resumo adicional"
