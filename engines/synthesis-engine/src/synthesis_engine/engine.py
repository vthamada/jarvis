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
from shared.domain_registry import route_linked_specialist_type, workflow_runtime_guidance
from shared.mind_domain_specialist_contract import (
    build_mind_domain_specialist_runtime_policy,
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
    session_continuity_brief: str | None = None
    session_continuity_mode: str | None = None
    session_anchor_goal: str | None = None
    context_compaction_status: str | None = None
    context_live_summary: str | None = None
    cross_session_recall_status: str | None = None
    cross_session_recall_summary: str | None = None
    guided_memory_specialists: list[str] = field(default_factory=list)
    semantic_memory_focus: list[str] = field(default_factory=list)
    procedural_memory_hint: str | None = None
    procedural_artifact_status: str | None = None
    procedural_artifact_ref: str | None = None
    procedural_artifact_summary: str | None = None


@dataclass(frozen=True)
class SynthesisResult:
    """Structured synthesis output plus lightweight validation metadata."""

    response_text: str
    output_validation_status: str
    output_validation_errors: list[str]
    output_validation_retry_applied: bool
    workflow_output_status: str
    workflow_output_errors: list[str]
    adaptive_intervention_workflow_priority_summary: str | None
    adaptive_intervention_preserved_checkpoint: str | None
    adaptive_intervention_preserved_gate: str | None


class SynthesisEngine:
    """Compose the final textual synthesis of the current flow."""

    name = "synthesis-engine"

    def compose(self, synthesis_input: SynthesisInput) -> str:
        return self.compose_result(synthesis_input).response_text

    def compose_result(self, synthesis_input: SynthesisInput) -> SynthesisResult:
        """Create a response that reflects identity, context, and outcome."""

        response_text = self._compose_raw_response(synthesis_input)
        validation_errors = self._validate_output(response_text)
        (
            adaptive_intervention_summary,
            adaptive_intervention_checkpoint,
            adaptive_intervention_gate,
        ) = self._adaptive_intervention_workflow_priority_details(synthesis_input)
        workflow_output_status, workflow_output_errors = self._assess_workflow_output(
            response_text,
            synthesis_input=synthesis_input,
        )
        if not validation_errors:
            return SynthesisResult(
                response_text=response_text,
                output_validation_status="coherent",
                output_validation_errors=[],
                output_validation_retry_applied=False,
                workflow_output_status=workflow_output_status,
                workflow_output_errors=workflow_output_errors,
                adaptive_intervention_workflow_priority_summary=(
                    adaptive_intervention_summary
                ),
                adaptive_intervention_preserved_checkpoint=(
                    adaptive_intervention_checkpoint
                ),
                adaptive_intervention_preserved_gate=adaptive_intervention_gate,
            )

        repaired_response = self._repair_output(
            response_text,
            synthesis_input=synthesis_input,
            errors=validation_errors,
        )
        repaired_errors = self._validate_output(repaired_response)
        repaired_workflow_status, repaired_workflow_errors = self._assess_workflow_output(
            repaired_response,
            synthesis_input=synthesis_input,
        )
        repaired_status = "repaired" if not repaired_errors else "invalid"
        return SynthesisResult(
            response_text=repaired_response,
            output_validation_status=repaired_status,
            output_validation_errors=(
                list(validation_errors)
                if repaired_status == "repaired"
                else list(repaired_errors)
            ),
            output_validation_retry_applied=True,
            workflow_output_status=repaired_workflow_status,
            workflow_output_errors=repaired_workflow_errors,
            adaptive_intervention_workflow_priority_summary=adaptive_intervention_summary,
            adaptive_intervention_preserved_checkpoint=adaptive_intervention_checkpoint,
            adaptive_intervention_preserved_gate=adaptive_intervention_gate,
        )

    def _compose_raw_response(self, synthesis_input: SynthesisInput) -> str:
        """Create the raw response before output validation/recovery."""

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
        adaptive_intervention_line = self._adaptive_intervention_workflow_priority_line(
            synthesis_input
        )
        if adaptive_intervention_line:
            parts.append(f"Intervencao adaptativa: {adaptive_intervention_line}.")
        artifact_line = self._procedural_artifact_line(synthesis_input)
        if artifact_line:
            parts.append(f"Artefato procedural: {artifact_line}.")
        limitation = self._limitation_line(synthesis_input)
        if limitation:
            parts.append(f"Limite atual: {limitation}.")
        operational_result = self._operational_line(synthesis_input)
        if operational_result:
            parts.append(f"Resultado operacional: {operational_result}.")
        return " ".join(parts)

    @staticmethod
    def _validate_output(response_text: str) -> list[str]:
        errors: list[str] = []
        if not response_text.strip():
            errors.append("empty_response")
        if "Leitura do objetivo:" not in response_text:
            errors.append("missing_clause:goal_read")
        if "Julgamento:" not in response_text:
            errors.append("missing_clause:judgment")
        if "Recomendacao:" not in response_text:
            errors.append("missing_clause:recommendation")
        return errors

    def _repair_output(
        self,
        response_text: str,
        *,
        synthesis_input: SynthesisInput,
        errors: list[str],
    ) -> str:
        plan = synthesis_input.deliberative_plan
        goal_line = self._goal_line(synthesis_input)
        if plan is not None:
            recommendation = (
                f"{self._recommendation_line(synthesis_input)}; manter framing governado "
                "enquanto o output e recomposto"
            )
        else:
            recommendation = (
                "manter framing governado e recompor a resposta a partir do ultimo "
                "plano coerente"
            )
        judgment = (
            "o output inicial nao preservou o contrato minimo de resposta e foi "
            "recomposto em modo seguro"
        )
        if response_text.strip():
            judgment = f"{judgment}; falhas detectadas: {', '.join(errors)}"
        repaired = (
            f"Leitura do objetivo: {goal_line}. "
            f"Julgamento: {judgment}. "
            f"Recomendacao: {recommendation}"
        )
        adaptive_intervention_line = self._adaptive_intervention_workflow_priority_line(
            synthesis_input
        )
        if adaptive_intervention_line:
            repaired = (
                f"{repaired}. Intervencao adaptativa: {adaptive_intervention_line}"
            )
        limitation = self._limitation_line(synthesis_input)
        if limitation:
            repaired = f"{repaired}. Limite atual: {limitation}"
        return repaired

    def _assess_workflow_output(
        self,
        response_text: str,
        *,
        synthesis_input: SynthesisInput,
    ) -> tuple[str, list[str]]:
        plan = synthesis_input.deliberative_plan
        if plan is None or not plan.route_workflow_profile:
            return ("not_applicable", [])
        errors = self._validate_workflow_output(
            response_text,
            synthesis_input=synthesis_input,
        )
        if not errors:
            return ("coherent", [])
        if any(error.startswith("mismatched_clause:") for error in errors):
            return ("misaligned", errors)
        return ("partial", errors)

    def _validate_workflow_output(
        self,
        response_text: str,
        *,
        synthesis_input: SynthesisInput,
    ) -> list[str]:
        plan = synthesis_input.deliberative_plan
        if plan is None or not plan.route_workflow_profile:
            return []
        guidance = workflow_runtime_guidance(plan.route_workflow_profile)
        errors: list[str] = []
        workflow_label = self._present_contract_label(plan.route_workflow_profile)
        if workflow_label:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_profile",
                    clause_prefix="workflow ativo:",
                    expected_value=workflow_label,
                )
            )
        response_focus = self._present_contract_label(guidance.response_focus)
        if response_focus:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_response_focus",
                    clause_prefix="foco final:",
                    expected_value=response_focus,
                )
            )
        workflow_checkpoint = self._present_contract_label(
            plan.route_workflow_checkpoints[0] if plan.route_workflow_checkpoints else None
        )
        if workflow_checkpoint:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_checkpoint",
                    clause_prefix="checkpoint ativo:",
                    expected_value=workflow_checkpoint,
                )
            )
        workflow_decision = self._present_contract_label(
            plan.route_workflow_decision_points[0]
            if plan.route_workflow_decision_points
            else None
        )
        if workflow_decision:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_gate",
                    clause_prefix="gate governado:",
                    expected_value=workflow_decision,
                )
            )
        adaptive_intervention_line = self._adaptive_intervention_workflow_priority_line(
            synthesis_input
        )
        if adaptive_intervention_line:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="adaptive_intervention_workflow_priority",
                    clause_prefix="Intervencao adaptativa:",
                    expected_value=adaptive_intervention_line,
                )
            )
        expected_deliverable = self._present_contract_label(
            plan.route_expected_deliverables[0] if plan.route_expected_deliverables else None
        )
        if expected_deliverable:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_deliverable",
                    clause_prefix="entrega esperada:",
                    expected_value=expected_deliverable,
                )
            )
        telemetry_focus = self._present_contract_label(
            plan.route_telemetry_focus[0] if plan.route_telemetry_focus else None
        )
        if telemetry_focus:
            errors.extend(
                self._validate_expected_clause(
                    response_text,
                    clause_name="workflow_telemetry_focus",
                    clause_prefix="foco de leitura:",
                    expected_value=telemetry_focus,
                )
            )
        return errors

    @staticmethod
    def _validate_expected_clause(
        response_text: str,
        *,
        clause_name: str,
        clause_prefix: str,
        expected_value: str,
    ) -> list[str]:
        expected_clause = f"{clause_prefix} {expected_value}"
        if expected_clause in response_text:
            return []
        if clause_prefix in response_text:
            return [f"mismatched_clause:{clause_name}"]
        return [f"missing_clause:{clause_name}"]

    @staticmethod
    def _procedural_artifact_line(synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        status = (
            synthesis_input.procedural_artifact_status
            or (plan.procedural_artifact_status if plan is not None else None)
        )
        artifact_ref = (
            synthesis_input.procedural_artifact_ref
            or (plan.procedural_artifact_ref if plan is not None else None)
        )
        if status in {None, "not_applicable"} or not artifact_ref:
            return None
        summary = (
            synthesis_input.procedural_artifact_summary
            or (plan.procedural_artifact_summary if plan is not None else None)
            or "procedimento guiado consolidado"
        )
        return f"{status} ({artifact_ref}) | {summary}"

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
        adaptive_intervention_line = self._adaptive_intervention_workflow_priority_line(
            synthesis_input
        )
        if adaptive_intervention_line:
            response = (
                f"{response}. Intervencao adaptativa: {adaptive_intervention_line}"
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
        policy_clause = self._mind_domain_specialist_policy_clause(
            plan,
            clause_type="continuity",
        )
        if brief:
            return f"{brief}; {policy_clause}" if policy_clause else brief
        if not plan or not mode:
            return None
        anchor_goal = synthesis_input.session_anchor_goal or plan.goal
        loop_focus = plan.open_loops[0] if plan.open_loops else None
        if mode == "retomar" and plan.continuity_target_goal:
            line = (
                f"sessao retoma continuidade relacionada em '{plan.continuity_target_goal}'"
            )
            return f"{line}; {policy_clause}" if policy_clause else line
        if mode == "encerrar":
            if loop_focus:
                line = (
                    f"sessao entra em fechamento controlado de '{anchor_goal}', "
                    f"encerrando '{loop_focus}'"
                )
                return f"{line}; {policy_clause}" if policy_clause else line
            line = f"sessao entra em fechamento controlado de '{anchor_goal}'"
            return f"{line}; {policy_clause}" if policy_clause else line
        if mode == "reformular":
            line = f"sessao reformula o objetivo ativo '{anchor_goal}' de forma governada"
            return f"{line}; {policy_clause}" if policy_clause else line
        if mode == "continuar":
            if loop_focus:
                line = (
                    f"sessao segue ancorada em '{anchor_goal}', com continuidade ativa em "
                    f"'{loop_focus}'"
                )
                return f"{line}; {policy_clause}" if policy_clause else line
            line = f"sessao segue ancorada em '{anchor_goal}'"
            return f"{line}; {policy_clause}" if policy_clause else line
        return None

    def _judgment_line(self, synthesis_input: SynthesisInput) -> str:
        plan = synthesis_input.deliberative_plan
        arbitration = synthesis_input.arbitration_summary or plan.specialist_resolution_summary
        cross_session_clause = self._cross_session_recall_clause(synthesis_input)
        metacognitive_clause = (
            f"; ancora metacognitiva: {plan.metacognitive_guidance_summary}"
            if plan.metacognitive_guidance_applied and plan.metacognitive_guidance_summary
            else ""
        )
        strategy_shift_clause = (
            f"; mudanca de estrategia mid-flow: {plan.cognitive_strategy_shift_summary}"
            if plan.cognitive_strategy_shift_applied
            and plan.cognitive_strategy_shift_summary
            else ""
        )
        if plan.continuity_action == "reformular":
            return (
                "o pedido atual tensiona a missao ativa e precisa de reformulacao "
                "governavel antes de qualquer desvio"
                f"{metacognitive_clause}"
                f"{strategy_shift_clause}"
                f"{f'; {cross_session_clause}' if cross_session_clause else ''}"
            )
        if plan.continuity_action == "encerrar" and plan.open_loops:
            return (
                "o pedido atual permite fechar o loop principal da missao: "
                f"{plan.open_loops[0]}"
                f"{metacognitive_clause}"
                f"{strategy_shift_clause}"
                f"{f'; {cross_session_clause}' if cross_session_clause else ''}"
            )
        if plan.continuity_action == "retomar" and plan.continuity_target_goal:
            return (
                "o pedido atual pede retomada explicita de continuidade relacionada em "
                f"{plan.continuity_target_goal}"
                f"{metacognitive_clause}"
                f"{strategy_shift_clause}"
                f"{f'; {cross_session_clause}' if cross_session_clause else ''}"
            )
        guidance = workflow_runtime_guidance(plan.route_workflow_profile)
        semantic_focus = ", ".join(synthesis_input.semantic_memory_focus[:2])
        route_objective = plan.route_consumer_objective
        route_profile = self._present_contract_label(plan.route_consumer_profile)
        workflow_profile = self._present_contract_label(plan.route_workflow_profile)
        chain_clause = self._mind_domain_specialist_clause(plan)
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
            if (
                plan.cognitive_strategy_shift_applied
                and plan.cognitive_strategy_shift_summary
            ):
                base = (
                    f"{base}; mudanca de estrategia mid-flow: "
                    f"{plan.cognitive_strategy_shift_summary}"
                )
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
                if cross_session_clause:
                    memory_clause = f"{memory_clause}; {cross_session_clause}"
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"rota {route_profile or 'ativa'} orienta {route_objective}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{f'; {chain_clause}' if chain_clause else ''}"
                    f"{memory_clause}"
                )
            if semantic_focus:
                memory_clause = ""
                if semantic_source:
                    memory_clause = f"; fonte semantica: {semantic_source}"
                if cross_session_clause:
                    memory_clause = f"{memory_clause}; {cross_session_clause}"
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{f'; {chain_clause}' if chain_clause else ''}"
                    f"{memory_clause}"
                )
            if route_objective:
                workflow_clause = (
                    f"; workflow ativo: {workflow_profile}" if workflow_profile else ""
                )
                if chain_clause:
                    workflow_clause = f"{workflow_clause}; {chain_clause}"
                if cross_session_clause:
                    workflow_clause = f"{workflow_clause}; {cross_session_clause}"
                return (
                    f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}; "
                    f"rota {route_profile or 'ativa'} orienta {route_objective}"
                    f"{workflow_clause}"
                )
            suffix = f"; {cross_session_clause}" if cross_session_clause else ""
            return f"{base}; a missao ativa segue ancorada em {plan.open_loops[0]}{suffix}"
        if arbitration:
            base = arbitration
            if cognitive_anchor:
                base = f"{base}; {cognitive_anchor}"
            if plan.metacognitive_guidance_applied and metacognitive_guidance:
                base = f"{base}; ancora metacognitiva: {metacognitive_guidance}"
            if (
                plan.cognitive_strategy_shift_applied
                and plan.cognitive_strategy_shift_summary
            ):
                base = (
                    f"{base}; mudanca de estrategia mid-flow: "
                    f"{plan.cognitive_strategy_shift_summary}"
                )
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
                if cross_session_clause:
                    memory_clause = f"{memory_clause}; {cross_session_clause}"
                return (
                    f"{base}; rota {route_profile or 'ativa'} orienta {route_objective}; "
                    f"memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{memory_clause}"
                    f"{f'; {chain_clause}' if chain_clause else ''}"
                    f"{workflow_clause}"
                )
            if semantic_focus:
                memory_clause = (
                    f"; fonte semantica: {semantic_source}" if semantic_source else ""
                )
                if cross_session_clause:
                    memory_clause = f"{memory_clause}; {cross_session_clause}"
                return (
                    f"{base}; memoria guiada reforca {semantic_role} em {semantic_focus}; "
                    f"framing final deve permanecer coerente com {semantic_role}"
                    f"{f'; {chain_clause}' if chain_clause else ''}"
                    f"{memory_clause}"
                )
            if route_objective:
                workflow_clause = (
                    f"; workflow ativo: {workflow_profile}" if workflow_profile else ""
                )
                if chain_clause:
                    workflow_clause = f"{workflow_clause}; {chain_clause}"
                if cross_session_clause:
                    workflow_clause = f"{workflow_clause}; {cross_session_clause}"
                return (
                    f"{base}; rota {route_profile or 'ativa'} orienta {route_objective}"
                    f"{workflow_clause}"
                )
            if cross_session_clause:
                return f"{base}; {cross_session_clause}"
            return base
        base = plan.rationale.split(";", maxsplit=1)[0]
        if cognitive_anchor:
            base = f"{base}; {cognitive_anchor}"
        if plan.metacognitive_guidance_applied and metacognitive_guidance:
            base = f"{base}; ancora metacognitiva: {metacognitive_guidance}"
        if plan.cognitive_strategy_shift_applied and plan.cognitive_strategy_shift_summary:
            base = (
                f"{base}; mudanca de estrategia mid-flow: "
                f"{plan.cognitive_strategy_shift_summary}"
            )
        if plan.dominant_tension:
            base = f"{base}; tensao dominante: {plan.dominant_tension}"
        if plan.arbitration_source == "mind_registry_recomposition":
            base = (
                f"{base}; recomposicao cognitiva manteve o alinhamento com o dominio "
                "primario"
            )
        if cross_session_clause:
            base = f"{base}; {cross_session_clause}"
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
        semantic_effect_clause = self._semantic_effect_clause(plan)
        if semantic_effect_clause:
            recommendation = f"{recommendation}; {semantic_effect_clause}"
        procedural_effect_clause = self._procedural_effect_clause(plan)
        if procedural_effect_clause:
            recommendation = f"{recommendation}; {procedural_effect_clause}"
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
        if (
            plan.cognitive_strategy_shift_applied
            and plan.cognitive_strategy_shift_summary
        ):
            recommendation = (
                f"{recommendation}; mudanca de estrategia mid-flow: "
                f"{plan.cognitive_strategy_shift_summary}"
            )
        if (
            plan.cognitive_strategy_shift_applied
            and plan.cognitive_strategy_shift_trigger
        ):
            recommendation = (
                f"{recommendation}; gatilho de estrategia: "
                f"{self._present_contract_label(plan.cognitive_strategy_shift_trigger)}"
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
        compaction_clause = self._context_compaction_clause(synthesis_input)
        if compaction_clause:
            recommendation = f"{recommendation}; {compaction_clause}"
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
        if (
            plan.cognitive_strategy_shift_applied
            and plan.cognitive_strategy_shift_effects
        ):
            recommendation = (
                f"{recommendation}; efeitos da estrategia: "
                f"{', '.join(plan.cognitive_strategy_shift_effects)}"
            )
        if plan.metacognitive_containment_recommendation:
            recommendation = (
                f"{recommendation}; contencao preferencial: "
                f"{plan.metacognitive_containment_recommendation}"
            )
        policy_clause = self._mind_domain_specialist_policy_clause(
            plan,
            clause_type="recommendation",
        )
        if policy_clause:
            recommendation = f"{recommendation}; {policy_clause}"
        return recommendation

    def _semantic_effect_clause(self, plan: DeliberativePlanContract) -> str | None:
        effects = list(plan.semantic_memory_effects or [])
        if not effects:
            return None
        clauses: list[str] = []
        if "priority" in effects:
            clauses.append("memoria semantica prioriza o framing antes do fechamento")
        if "depth" in effects:
            clauses.append("memoria semantica pede profundidade adicional na leitura final")
        if "recommendation" in effects:
            clauses.append("memoria semantica orienta a direcao recomendada")
        return "; ".join(clauses) if clauses else None

    def _procedural_effect_clause(self, plan: DeliberativePlanContract) -> str | None:
        effects = list(plan.procedural_memory_effects or [])
        if not effects:
            return None
        clauses: list[str] = []
        if "priority" in effects:
            clauses.append("memoria procedural prioriza a ordem da proxima acao")
        if "depth" in effects:
            clauses.append("memoria procedural exige validacao adicional antes do fechamento")
        if "recommendation" in effects:
            clauses.append("memoria procedural ancora a recomendacao final")
        return "; ".join(clauses) if clauses else None

    def _adaptive_intervention_workflow_priority_line(
        self,
        synthesis_input: SynthesisInput,
    ) -> str | None:
        summary, _, _ = self._adaptive_intervention_workflow_priority_details(
            synthesis_input
        )
        return summary

    def _adaptive_intervention_workflow_priority_details(
        self,
        synthesis_input: SynthesisInput,
    ) -> tuple[str | None, str | None, str | None]:
        plan = synthesis_input.deliberative_plan
        if (
            plan is None
            or plan.adaptive_intervention_status in {None, "not_applicable"}
            or not plan.adaptive_intervention_selected_action
        ):
            return (None, None, None)
        guidance = workflow_runtime_guidance(plan.route_workflow_profile)
        workflow_label = self._present_contract_label(plan.route_workflow_profile)
        action_label = self._present_contract_label(
            plan.adaptive_intervention_selected_action
        )
        if workflow_label is None or action_label is None:
            return (None, None, None)
        preserved_checkpoint = self._present_contract_label(
            plan.route_workflow_checkpoints[0]
            if plan.route_workflow_checkpoints
            else None
        )
        preserved_gate = self._present_contract_label(
            plan.route_workflow_decision_points[0]
            if plan.route_workflow_decision_points
            else None
        )
        focus_map = {
            "clarification_checkpoint": "clareza operacional antes da resposta final",
            "safe_containment": "o caminho governado antes de qualquer retomada",
            "memory_review_checkpoint": self._present_contract_label(
                guidance.procedural_memory_role
            )
            or "continuidade segura da proxima acao",
            "specialist_reevaluation": self._present_contract_label(
                guidance.response_focus
            )
            or "o foco final do workflow ativo",
        }
        protected_focus = focus_map.get(
            plan.adaptive_intervention_selected_action,
            self._present_contract_label(guidance.response_focus)
            or "o foco final do workflow ativo",
        )
        preservation_clause = ""
        if preserved_checkpoint and preserved_gate:
            preservation_clause = (
                f", preservando checkpoint {preserved_checkpoint} "
                f"e gate {preserved_gate}"
            )
        elif preserved_checkpoint:
            preservation_clause = (
                f", preservando checkpoint {preserved_checkpoint}"
            )
        elif preserved_gate:
            preservation_clause = f", preservando gate {preserved_gate}"
        return (
            f"workflow {workflow_label} priorizou {action_label} "
            f"para proteger {protected_focus}{preservation_clause}",
            preserved_checkpoint,
            preserved_gate,
        )

    def _limitation_line(self, synthesis_input: SynthesisInput) -> str | None:
        plan = synthesis_input.deliberative_plan
        limits: list[str] = []
        if plan is None:
            if synthesis_input.governance_decision.conditions:
                return synthesis_input.governance_decision.conditions[0]
            return None
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
        if plan.cognitive_strategy_shift_applied:
            limits.append(
                "o impasse mid-flow ainda precisa ser resolvido antes do fechamento final"
            )
        material_risks = [risk for risk in plan.risks if "sem risco material" not in risk.lower()]
        if material_risks:
            limits.append(material_risks[0])
        policy_limit = self._mind_domain_specialist_policy_clause(
            plan,
            clause_type="limitation",
        )
        if policy_limit:
            limits.append(policy_limit)
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

    @classmethod
    def _mind_domain_specialist_clause(cls, plan: DeliberativePlanContract) -> str | None:
        contract_status = cls._present_contract_label(
            plan.mind_domain_specialist_contract_status
        )
        contract_chain = cls._present_contract_label(
            plan.mind_domain_specialist_contract_chain
        )
        contract_summary = plan.mind_domain_specialist_contract_summary
        override_mode = cls._present_contract_label(
            plan.mind_domain_specialist_override_mode
        )
        fallback_mode = cls._present_contract_label(
            plan.mind_domain_specialist_fallback_mode
        )
        if contract_summary and contract_chain:
            clause = (
                f"contrato mind domain specialist: {contract_status or 'active'}; "
                f"{contract_summary}; cadeia {contract_chain}"
            )
            if override_mode:
                clause = f"{clause}; override bounded: {override_mode}"
            if fallback_mode:
                clause = f"{clause}; fallback governado: {fallback_mode}"
            return clause
        if not plan.primary_mind or not plan.primary_domain_driver or not plan.primary_route:
            return None
        if not plan.specialist_hints:
            return None
        specialist_label = cls._present_contract_label(plan.specialist_hints[0])
        if specialist_label is None:
            return None
        return (
            "cadeia evidence-first: "
            f"{cls._present_contract_label(plan.primary_mind)} -> "
            f"{cls._present_contract_label(plan.primary_domain_driver)} -> "
            f"{cls._present_contract_label(plan.primary_route)} -> {specialist_label}"
        )

    @classmethod
    def _mind_domain_specialist_policy_clause(
        cls,
        plan: DeliberativePlanContract | None,
        *,
        clause_type: str,
    ) -> str | None:
        if plan is None:
            return None
        policy = build_mind_domain_specialist_runtime_policy(
            contract_status=plan.mind_domain_specialist_contract_status,
            active_specialist=plan.mind_domain_specialist_active_specialist,
            planned_specialists=list(plan.specialist_hints),
            authoritative_specialist_hint=(
                route_linked_specialist_type(plan.primary_route)
                if plan.primary_route
                else None
            ),
            override_mode=plan.mind_domain_specialist_override_mode,
            fallback_mode=plan.mind_domain_specialist_fallback_mode,
        )
        specialist = cls._present_contract_label(policy.authoritative_specialist)
        fallback = cls._present_contract_label(policy.fallback_note)
        if clause_type == "continuity":
            if policy.continuity_mode == "preserve_authoritative_chain" and specialist:
                return (
                    f"continuidade preserva cadeia autoritativa ate {specialist}"
                )
            if (
                policy.continuity_mode == "preserve_override_without_reopening_chain"
                and specialist
            ):
                return (
                    f"continuidade preserva override bounded em {specialist} "
                    "sem reabrir a cadeia soberana"
                )
            if policy.continuity_mode == "continue_without_specialist_handoff":
                return (
                    "continuidade permanece contida no nucleo sem novo handoff "
                    f"especializado{f' ({fallback})' if fallback else ''}"
                )
            if policy.continuity_mode == "contain_partial_chain" and specialist:
                return (
                    f"continuidade contem a cadeia parcial ate {specialist}"
                )
            return None
        if clause_type == "recommendation":
            if policy.consumer_mode == "authoritative_specialist" and specialist:
                return f"consumo final deve permanecer ancorado em {specialist}"
            if policy.consumer_mode == "bounded_override_specialist" and specialist:
                return (
                    f"framing final deve respeitar override bounded em {specialist}"
                )
            if policy.consumer_mode == "core_only_fallback":
                return (
                    "fechar pelo nucleo sem reacender handoff especializado"
                    f"{f' ({fallback})' if fallback else ''}"
                )
            if policy.consumer_mode == "degraded_specialist" and specialist:
                return (
                    f"manter especialista bounded {specialist} sob mediacao do nucleo"
                )
            return None
        if clause_type == "limitation":
            if policy.consumer_mode == "core_only_fallback":
                return (
                    "a ultima milha permaneceu em fallback governado no nucleo"
                    f"{f' ({fallback})' if fallback else ''}"
                )
            if policy.consumer_mode == "degraded_specialist":
                return "a cadeia mente dominio especialista segue parcial na ultima milha"
            return None
        return None

    @staticmethod
    def _cross_session_recall_clause(
        synthesis_input: SynthesisInput,
    ) -> str | None:
        if synthesis_input.cross_session_recall_status != "active":
            return None
        if synthesis_input.cross_session_recall_summary:
            return f"recall cross-session: {synthesis_input.cross_session_recall_summary}"
        return "recall cross-session ativo"

    @staticmethod
    def _context_compaction_clause(
        synthesis_input: SynthesisInput,
    ) -> str | None:
        if synthesis_input.context_compaction_status not in {
            "compressed_live_context",
            "seeded_live_context",
        }:
            return None
        return "contexto vivo compactado sem reabrir historico bruto"

    @staticmethod
    def _operational_line(synthesis_input: SynthesisInput) -> str | None:
        operation_result = synthesis_input.operation_result
        if not operation_result:
            return None
        if operation_result.outputs:
            return operation_result.outputs[0]
        return "saida operacional produzida sem resumo adicional"
