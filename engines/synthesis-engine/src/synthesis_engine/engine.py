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
            return (
                "Leitura do objetivo: manter a orientacao executiva dentro do "
                "escopo controlado do v1."
            )

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
        plan = synthesis_input.deliberative_plan
        if plan and plan.continuity_action == "reformular" and plan.open_loops:
            judgment = (
                "o pedido atual tensiona a missao ativa e a governanca exige conter "
                "o desvio antes de reformular o objetivo"
            )
            recommendation = synthesis_input.governance_decision.justification
        elif plan and plan.continuity_action == "retomar" and plan.continuity_target_goal:
            judgment = (
                "a retomada explicita de continuidade relacionada exige validacao "
                "antes de disputar direcao com a missao ativa"
            )
            recommendation = (
                "explicitar por que a missao relacionada "
                f"'{plan.continuity_target_goal}' deve ser retomada agora"
            )
        else:
            judgment = (
                "a governanca atual exige conter a acao para preservar coerencia e "
                "seguranca"
            )
            recommendation = synthesis_input.governance_decision.justification
        response = (
            f"Leitura do objetivo: {goal_line}. "
            f"Julgamento: {judgment}. "
            f"Recomendacao: {recommendation}"
        )
        limitation = self._limitation_line(synthesis_input)
        if limitation:
            response = f"{response}. Limite atual: {limitation}"
        return response

    @staticmethod
    def _goal_line(synthesis_input: SynthesisInput) -> str:
        if synthesis_input.deliberative_plan:
            return synthesis_input.deliberative_plan.goal
        return synthesis_input.identity_profile.mission_statement

    def _judgment_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        arbitration = synthesis_input.arbitration_summary or plan.specialist_resolution_summary
        if plan.continuity_action == "reformular":
            return (
                "o pedido atual tensiona a missao ativa e precisa de reformulacao "
                "governavel antes de qualquer desvio"
            )
        if plan.continuity_action == "encerrar" and plan.open_loops:
            return (
                "o pedido atual permite fechar o loop principal da missao: "
                f"{plan.open_loops[0]}"
            )
        if plan.continuity_action == "retomar" and plan.continuity_target_goal:
            return (
                "o pedido atual pede retomada explicita de continuidade relacionada em "
                f"{plan.continuity_target_goal}"
            )
        if plan.continuity_action == "continuar" and plan.open_loops:
            base = arbitration or plan.rationale.split(";", maxsplit=1)[0]
            return f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}"
        if arbitration:
            return arbitration
        return plan.rationale.split(";", maxsplit=1)[0]

    def _recommendation_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        success = (
            plan.success_criteria[0]
            if plan.success_criteria
            else "manter resposta coerente e reversivel"
        )
        loop_focus = plan.open_loops[0] if plan.open_loops else None
        if plan.continuity_action == "reformular":
            if loop_focus:
                next_action = f"explicitar como o novo pedido afeta {loop_focus}"
            else:
                next_action = "explicitar se o novo pedido substitui ou adia a missao ativa"
        elif plan.continuity_action == "encerrar" and loop_focus:
            next_action = f"fechar {loop_focus} com criterio explicito"
        elif plan.continuity_action == "retomar" and plan.continuity_target_goal:
            next_action = (
                "explicitar por que a missao relacionada "
                f"'{plan.continuity_target_goal}' deve ser retomada agora"
            )
        elif plan.continuity_action == "continuar" and loop_focus:
            next_action = f"retomar {loop_focus} antes de abrir novo escopo"
        elif plan.smallest_safe_next_action:
            next_action = plan.smallest_safe_next_action
        elif plan.steps:
            next_action = plan.steps[0]
        else:
            next_action = "preservar uma proxima acao segura"
        return f"{next_action}; criterio de sucesso: {success}"

    def _limitation_line(self, synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        limits: list[str] = []
        if plan.continuity_action == "reformular" and plan.open_loops:
            limits.append(
                "a missao ativa ainda tem loop aberto e nao pode ser desviada em silencio"
            )
        if plan.continuity_action == "retomar" and plan.open_loops:
            limits.append(
                "a retomada relacionada precisa justificar por que supera os loops ativos"
            )
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
