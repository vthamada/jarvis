"""Synthesis engine for the final JARVIS response."""

from __future__ import annotations

from dataclasses import dataclass, field

from identity_engine.engine import IdentityProfile

from shared.contracts import (
    DeliberativePlanContract,
    GovernanceDecisionContract,
    OperationResultContract,
    SpecialistContributionContract,
)
from shared.domain_registry import workflow_runtime_guidance
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
    session_continuity_brief: str | None = None
    session_continuity_mode: str | None = None
    session_anchor_goal: str | None = None
    guided_memory_specialists: list[str] = field(default_factory=list)
    semantic_memory_focus: list[str] = field(default_factory=list)
    procedural_memory_hint: str | None = None


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

        parts: list[str] = []
        continuity_line = self._continuity_line(synthesis_input)
        if continuity_line:
            parts.append(f"Continuidade ativa: {continuity_line}.")
        parts.extend(
            [
                f"Leitura do objetivo: {plan.goal}.",
            f"Julgamento: {self._judgment_line(synthesis_input)}.",
            f"Recomendacao: {self._recommendation_line(synthesis_input)}.",
            ]
        )
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
        elif plan and plan.continuity_recovery_mode == "contained_recovery":
            judgment = (
                "a continuidade recuperada partiu de checkpoint contido e precisa "
                "de revisao explicita antes de qualquer retomada"
            )
            recommendation = synthesis_input.governance_decision.justification
        elif plan and plan.continuity_recovery_mode == "governed_review":
            judgment = (
                "o checkpoint recuperado ainda aguarda validacao e a retomada "
                "permanece em modo governado"
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
        if plan and plan.metacognitive_guidance_applied and plan.metacognitive_guidance_summary:
            judgment = (
                f"{judgment}; ancora metacognitiva: "
                f"{plan.metacognitive_guidance_summary}"
            )
        if (
            plan
            and plan.metacognitive_containment_recommendation
            and synthesis_input.governance_decision.decision
            in {
                PermissionDecision.BLOCK,
                PermissionDecision.DEFER_FOR_VALIDATION,
            }
        ):
            recommendation = (
                f"{recommendation}; contencao recomendada: "
                f"{plan.metacognitive_containment_recommendation}"
            )
        continuity_line = self._continuity_line(synthesis_input)
        response = (
            f"{f'Continuidade ativa: {continuity_line}. ' if continuity_line else ''}"
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

    def _continuity_line(self, synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        brief = synthesis_input.session_continuity_brief
        mode = synthesis_input.session_continuity_mode or (plan.continuity_action if plan else None)
        if brief:
            return brief
        if not plan or not mode:
            return None
        anchor_goal = synthesis_input.session_anchor_goal or plan.goal
        loop_focus = plan.open_loops[0] if plan.open_loops else None
        if mode == "retomar" and plan.continuity_target_goal:
            return (
                f"sessao retoma continuidade relacionada em '{plan.continuity_target_goal}'"
            )
        if mode == "encerrar":
            if loop_focus:
                return (
                    f"sessao entra em fechamento controlado de '{anchor_goal}', "
                    f"encerrando '{loop_focus}'"
                )
            return f"sessao entra em fechamento controlado de '{anchor_goal}'"
        if mode == "reformular":
            return f"sessao reformula o objetivo ativo '{anchor_goal}' de forma governada"
        if mode == "continuar":
            if loop_focus:
                return (
                    f"sessao segue ancorada em '{anchor_goal}', com continuidade ativa em "
                    f"'{loop_focus}'"
                )
            return f"sessao segue ancorada em '{anchor_goal}'"
        return None

    def _judgment_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        arbitration = synthesis_input.arbitration_summary or plan.specialist_resolution_summary
        metacognitive_clause = (
            f"; ancora metacognitiva: {plan.metacognitive_guidance_summary}"
            if plan.metacognitive_guidance_applied and plan.metacognitive_guidance_summary
            else ""
        )
        if plan.continuity_action == "reformular":
            return (
                "o pedido atual tensiona a missao ativa e precisa de reformulacao "
                "governavel antes de qualquer desvio"
                f"{metacognitive_clause}"
            )
        if plan.continuity_action == "encerrar" and plan.open_loops:
            return (
                "o pedido atual permite fechar o loop principal da missao: "
                f"{plan.open_loops[0]}"
                f"{metacognitive_clause}"
            )
        if plan.continuity_action == "retomar" and plan.continuity_target_goal:
            return (
                "o pedido atual pede retomada explicita de continuidade relacionada em "
                f"{plan.continuity_target_goal}"
                f"{metacognitive_clause}"
            )
        guidance = workflow_runtime_guidance(plan.route_workflow_profile)
        semantic_focus = ", ".join(synthesis_input.semantic_memory_focus[:2])
        route_objective = plan.route_consumer_objective
        route_profile = self._present_contract_label(plan.route_consumer_profile)
        workflow_profile = self._present_contract_label(plan.route_workflow_profile)
        semantic_role = self._present_contract_label(guidance.semantic_memory_role)
        semantic_source = self._present_contract_label(plan.semantic_memory_source)
        semantic_lifecycle = self._present_contract_label(plan.semantic_memory_lifecycle)
        cognitive_anchor = self._cognitive_anchor_clause(plan)
        metacognitive_guidance = plan.metacognitive_guidance_summary
        if plan.continuity_action == "continuar" and plan.open_loops:
            base = arbitration or plan.rationale.split(";", maxsplit=1)[0]
            if cognitive_anchor:
                base = f"{base}; {cognitive_anchor}"
            if plan.metacognitive_guidance_applied and metacognitive_guidance:
                base = f"{base}; ancora metacognitiva: {metacognitive_guidance}"
            if plan.dominant_tension:
                base = f"{base}; tensao dominante: {plan.dominant_tension}"
            if plan.arbitration_source == "mind_registry_recomposition":
                base = (
                    f"{base}; recomposicao cognitiva manteve o alinhamento com o "
                    "dominio primario"
                )
            if semantic_focus and route_objective:
                memory_clause = ""
                if semantic_source:
                    memory_clause = f"; fonte semantica: {semantic_source}"
                if semantic_lifecycle:
                    memory_clause = f"{memory_clause}; lifecycle semantico: {semantic_lifecycle}"
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"rota {route_profile or 'ativa'} orienta {route_objective}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{memory_clause}"
                )
            if semantic_focus:
                memory_clause = ""
                if semantic_source:
                    memory_clause = f"; fonte semantica: {semantic_source}"
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{memory_clause}"
                )
            if route_objective:
                workflow_clause = (
                    f"; workflow ativo: {workflow_profile}" if workflow_profile else ""
                )
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"rota {route_profile or 'ativa'} orienta {route_objective}"
                    f"{workflow_clause}"
                )
            return f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}"
        if arbitration:
            base = arbitration
            if cognitive_anchor:
                base = f"{base}; {cognitive_anchor}"
            if plan.metacognitive_guidance_applied and metacognitive_guidance:
                base = f"{base}; ancora metacognitiva: {metacognitive_guidance}"
            if plan.dominant_tension:
                base = f"{base}; tensao dominante: {plan.dominant_tension}"
            if plan.arbitration_source == "mind_registry_recomposition":
                base = (
                    f"{base}; recomposicao cognitiva manteve o alinhamento com o "
                    "dominio primario"
                )
            if semantic_focus and route_objective:
                workflow_clause = (
                    f"; workflow ativo: {workflow_profile}" if workflow_profile else ""
                )
                memory_clause = ""
                if semantic_source:
                    memory_clause = f"; fonte semantica: {semantic_source}"
                if semantic_lifecycle:
                    memory_clause = f"{memory_clause}; lifecycle semantico: {semantic_lifecycle}"
                return (
                    f"{base}; rota {route_profile or 'ativa'} orienta {route_objective}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{memory_clause}"
                    f"{workflow_clause}"
                )
            if semantic_focus:
                memory_clause = (
                    f"; fonte semantica: {semantic_source}" if semantic_source else ""
                )
                return (
                    f"{base}; memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{memory_clause}"
                )
            if route_objective:
                workflow_clause = (
                    f"; workflow ativo: {workflow_profile}" if workflow_profile else ""
                )
                return (
                    f"{base}; rota {route_profile or 'ativa'} orienta {route_objective}"
                    f"{workflow_clause}"
                )
            return base
        base = plan.rationale.split(";", maxsplit=1)[0]
        if cognitive_anchor:
            base = f"{base}; {cognitive_anchor}"
        if plan.metacognitive_guidance_applied and metacognitive_guidance:
            base = f"{base}; ancora metacognitiva: {metacognitive_guidance}"
        if plan.dominant_tension:
            base = f"{base}; tensao dominante: {plan.dominant_tension}"
        if plan.arbitration_source == "mind_registry_recomposition":
            base = (
                f"{base}; recomposicao cognitiva manteve o alinhamento com o dominio "
                "primario"
            )
        if cognitive_anchor:
            return base
        return base

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
        guidance = workflow_runtime_guidance(plan.route_workflow_profile)
        deliverable_hint = (
            plan.route_expected_deliverables[0] if plan.route_expected_deliverables else None
        )
        telemetry_hint = (
            plan.route_telemetry_focus[0] if plan.route_telemetry_focus else None
        )
        procedural_role = self._present_contract_label(guidance.procedural_memory_role)
        response_focus = self._present_contract_label(guidance.response_focus)
        primary_domain_driver = self._present_contract_label(plan.primary_domain_driver)
        procedural_source = self._present_contract_label(plan.procedural_memory_source)
        procedural_lifecycle = self._present_contract_label(plan.procedural_memory_lifecycle)
        if synthesis_input.procedural_memory_hint:
            recommendation = (
                f"{next_action}; apoio procedural orienta {procedural_role}: "
                f"{synthesis_input.procedural_memory_hint}; "
                "proxima acao deve preservar esse fio; "
                f"criterio de sucesso: {success}"
            )
        else:
            recommendation = f"{next_action}; criterio de sucesso: {success}"
        if deliverable_hint:
            recommendation = (
                f"{recommendation}; entrega esperada: "
                f"{self._present_contract_label(deliverable_hint)}"
            )
        if telemetry_hint:
            recommendation = (
                f"{recommendation}; foco de leitura: "
                f"{self._present_contract_label(telemetry_hint)}"
            )
        workflow_hint = self._present_contract_label(plan.route_workflow_profile)
        if workflow_hint:
            recommendation = f"{recommendation}; workflow ativo: {workflow_hint}"
        if primary_domain_driver:
            recommendation = (
                f"{recommendation}; dominio primario: {primary_domain_driver}"
            )
        if response_focus:
            recommendation = f"{recommendation}; foco final: {response_focus}"
        if plan.dominant_tension:
            recommendation = (
                f"{recommendation}; tensao dominante: {plan.dominant_tension}"
            )
        if plan.mind_disagreement_status and plan.mind_disagreement_status != "not_applicable":
            recommendation = (
                f"{recommendation}; discordancia cognitiva: "
                f"{self._present_contract_label(plan.mind_disagreement_status)}"
            )
        if plan.mind_validation_checkpoints:
            recommendation = (
                f"{recommendation}; checkpoint cognitivo: "
                f"{self._present_contract_label(plan.mind_validation_checkpoints[0])}"
            )
        if plan.arbitration_source == "mind_registry_recomposition":
            recommendation = (
                f"{recommendation}; recomposicao cognitiva: preservar o dominio "
                "primario antes de ampliar o escopo"
            )
        workflow_checkpoint = self._present_contract_label(
            plan.route_workflow_checkpoints[0]
            if plan.route_workflow_checkpoints
            else None
        )
        if workflow_checkpoint:
            recommendation = (
                f"{recommendation}; checkpoint ativo: {workflow_checkpoint}"
            )
        workflow_decision = self._present_contract_label(
            plan.route_workflow_decision_points[0]
            if plan.route_workflow_decision_points
            else None
        )
        if workflow_decision:
            recommendation = f"{recommendation}; gate governado: {workflow_decision}"
        if procedural_source:
            recommendation = (
                f"{recommendation}; fonte procedural: {procedural_source}"
            )
        if procedural_lifecycle:
            recommendation = (
                f"{recommendation}; lifecycle procedural: {procedural_lifecycle}"
            )
        if plan.memory_review_status and plan.memory_review_status != "not_needed":
            recommendation = (
                f"{recommendation}; revisao de memoria: "
                f"{self._present_contract_label(plan.memory_review_status)}"
            )
        if plan.metacognitive_guidance_applied and plan.metacognitive_effects:
            recommendation = (
                f"{recommendation}; efeitos metacognitivos: "
                f"{', '.join(plan.metacognitive_effects)}"
            )
        if plan.metacognitive_containment_recommendation:
            recommendation = (
                f"{recommendation}; contencao preferencial: "
                f"{plan.metacognitive_containment_recommendation}"
            )
        return recommendation

    def _limitation_line(self, synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        limits: list[str] = []
        if plan.continuity_action == "reformular" and plan.open_loops:
            limits.append(
                "a missao ativa ainda tem loop aberto e nao pode ser desviada em silencio"
            )
        if plan.continuity_recovery_mode == "contained_recovery":
            limits.append("o checkpoint anterior ficou contido e exige revisao manual")
        if plan.continuity_recovery_mode == "governed_review":
            limits.append("o checkpoint recuperado ainda aguarda validacao explicita")
        if plan.continuity_action == "retomar" and plan.open_loops:
            limits.append(
                "a retomada relacionada precisa justificar por que supera os loops ativos"
            )
        if synthesis_input.governance_decision.conditions:
            limits.append(synthesis_input.governance_decision.conditions[0])
        if plan.requires_human_validation:
            limits.append("o plano ainda pede validacao humana antes de ampliar escopo")
        if plan.memory_review_status == "review_recommended":
            limits.append("a memoria guiada entrou em faixa de revisao recomendada")
        if plan.mind_disagreement_status == "deep_review_required":
            limits.append("a tensao dominante ainda pede revisao cognitiva mais profunda")
        elif plan.mind_disagreement_status == "validation_required":
            limits.append(
                "a resposta ainda precisa validar como a discordancia "
                "entre mentes foi resolvida"
            )
        material_risks = [risk for risk in plan.risks if "sem risco material" not in risk.lower()]
        if material_risks:
            limits.append(material_risks[0])
        return limits[0] if limits else None

    @staticmethod
    def _present_contract_label(value: str | None) -> str | None:
        if not value:
            return None
        return value.replace("_", " ")

    @classmethod
    def _cognitive_anchor_clause(cls, plan: DeliberativePlanContract) -> str | None:
        primary_mind = cls._present_contract_label(plan.primary_mind)
        primary_domain_driver = cls._present_contract_label(plan.primary_domain_driver)
        primary_route = cls._present_contract_label(plan.primary_route)
        if primary_mind and primary_domain_driver and primary_route:
            return (
                f"{primary_mind} ancora o dominio primario {primary_domain_driver} "
                f"via rota {primary_route}"
            )
        if primary_mind and primary_domain_driver:
            return f"{primary_mind} ancora o dominio primario {primary_domain_driver}"
        if primary_domain_driver:
            return f"dominio primario {primary_domain_driver} ancora a resposta"
        if primary_mind:
            return f"{primary_mind} ancora a resposta"
        return None

    @staticmethod
    def _operational_line(synthesis_input: SynthesisInput) -> str | None:
        operation_result = synthesis_input.operation_result
        if not operation_result:
            return None
        if operation_result.outputs:
            return operation_result.outputs[0]
        return "saida operacional produzida sem resumo adicional"
