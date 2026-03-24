"""Deterministic subordinated specialist engine for the v1 nucleus."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import (
    DeliberativePlanContract,
    DomainSpecialistRouteContract,
    SpecialistBoundaryContract,
    SpecialistContributionContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
    SpecialistSharedMemoryContextContract,
)
from shared.domain_registry import is_shadow_route


@dataclass(frozen=True)
class SpecialistHandoffPlan:
    """Explicit handoff plan between the core and subordinated specialists."""

    specialist_hints: list[str]
    selections: list[SpecialistSelectionContract]
    invocations: list[SpecialistInvocationContract]
    boundary_summary: str


@dataclass(frozen=True)
class SpecialistReview:
    """Structured output of subordinated specialist contributions."""

    specialist_hints: list[str]
    selections: list[SpecialistSelectionContract]
    invocations: list[SpecialistInvocationContract]
    contributions: list[SpecialistContributionContract]
    summary: str
    findings: list[str]
    boundary_summary: str


class SpecialistEngine:
    """Produce subordinated specialist contributions without breaking unitary identity."""

    name = "specialist-engine"

    def review(
        self,
        *,
        intent: str,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
        session_id: str | None = None,
        mission_id: str | None = None,
        requested_by_service: str | None = None,
    ) -> SpecialistReview:
        """Build deterministic specialist contributions for the current plan."""

        handoff_plan = self.plan_handoffs(
            intent=intent,
            plan=plan,
            knowledge_snippets=knowledge_snippets,
            session_id=session_id,
            mission_id=mission_id,
            requested_by_service=requested_by_service,
        )
        return self.review_handoffs(
            intent=intent,
            plan=plan,
            knowledge_snippets=knowledge_snippets,
            handoff_plan=handoff_plan,
        )

    def plan_handoffs(
        self,
        *,
        intent: str,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
        domain_specialist_routes: list[DomainSpecialistRouteContract] | None = None,
        shared_memory_contexts: dict[str, SpecialistSharedMemoryContextContract] | None = None,
        session_id: str | None = None,
        mission_id: str | None = None,
        requested_by_service: str | None = None,
    ) -> SpecialistHandoffPlan:
        """Build the explicit selection and boundary plan for specialist handoffs."""

        selections = self._select_handoffs(
            intent=intent,
            plan=plan,
            domain_specialist_routes=domain_specialist_routes or [],
        )
        invocations: list[SpecialistInvocationContract] = []
        for index, selection in enumerate(
            [item for item in selections if item.selection_status == "selected"],
            start=1,
        ):
            invocation = self._build_invocation(
                selection=selection,
                plan=plan,
                knowledge_snippets=knowledge_snippets,
                shared_memory_context=(
                    shared_memory_contexts or {}
                ).get(selection.specialist_type),
                session_id=session_id,
                mission_id=mission_id,
                requested_by_service=requested_by_service or "orchestrator-service",
                sequence=index,
            )
            invocations.append(invocation)
            selection.invocation_id = invocation.invocation_id
        boundary_summary = self._build_boundary_summary(invocations)
        return SpecialistHandoffPlan(
            specialist_hints=[
                item.specialist_type
                for item in selections
                if item.selection_status == "selected"
            ],
            selections=selections,
            invocations=invocations,
            boundary_summary=boundary_summary,
        )

    def review_handoffs(
        self,
        *,
        intent: str,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
        handoff_plan: SpecialistHandoffPlan,
    ) -> SpecialistReview:
        """Execute subordinated specialist contributions only for approved handoffs."""

        contributions: list[SpecialistContributionContract] = []
        invocation_index = {
            item.specialist_type: item for item in handoff_plan.invocations
        }
        for specialist_hint in handoff_plan.specialist_hints:
            invocation = invocation_index[specialist_hint]
            contribution = self._build_contribution(
                invocation=invocation,
                specialist_hint=specialist_hint,
                intent=intent,
                plan=plan,
                knowledge_snippets=knowledge_snippets,
            )
            if contribution:
                contributions.append(contribution)
        findings = [
            finding for contribution in contributions for finding in contribution.findings[:3]
        ]
        summary = self._build_summary(contributions)
        return SpecialistReview(
            specialist_hints=handoff_plan.specialist_hints,
            selections=handoff_plan.selections,
            invocations=handoff_plan.invocations,
            contributions=contributions,
            summary=summary,
            findings=findings,
            boundary_summary=handoff_plan.boundary_summary,
        )

    @staticmethod
    def _select_handoffs(
        *,
        intent: str,
        plan: DeliberativePlanContract,
        domain_specialist_routes: list[DomainSpecialistRouteContract],
    ) -> list[SpecialistSelectionContract]:
        selections: list[SpecialistSelectionContract] = []
        route_map = {
            route.specialist_type: route for route in domain_specialist_routes
        }
        has_decomposition = len(plan.steps) >= 3 or bool(plan.continuity_action)
        has_tradeoff = intent == "analysis" or any(
            word in (plan.dominant_tension or "")
            for word in ("trade-off", "equilibrar", "comparar")
        )
        has_risk = plan.requires_human_validation or any(
            "risco" in risk or "govern" in risk for risk in plan.risks
        )
        for specialist_hint in plan.specialist_hints:
            route = route_map.get(specialist_hint)
            if specialist_hint == "especialista_planejamento_operacional" and has_decomposition:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.84,
                        rationale=(
                            "o plano exige decomposicao, checkpoints "
                            "e menor proxima acao segura"
                        ),
                        linked_domain=route.domain_name if route else None,
                        selection_mode=route.specialist_mode if route else "standard",
                    )
                )
            elif specialist_hint == "especialista_analise_estruturada" and has_tradeoff:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.82,
                        rationale=(
                            "o contexto exige comparacao estruturada "
                            "e criterio explicito de decisao"
                        ),
                        linked_domain=route.domain_name if route else None,
                        selection_mode=route.specialist_mode if route else "standard",
                    )
                )
            elif specialist_hint == "especialista_revisao_governanca" and has_risk:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.87,
                        rationale="o plano exige cautela normativa, auditoria e revisao de limites",
                        requires_governance_review=True,
                        linked_domain=route.domain_name if route else None,
                        selection_mode=route.specialist_mode if route else "standard",
                    )
                )
            elif (
                specialist_hint == "especialista_software_subordinado"
                and route is not None
                and route.domain_name in plan.active_domains
                and is_shadow_route(route.domain_name)
            ):
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.78,
                        rationale=(
                            "o domínio de software ativo abriu a primeira rota canônica "
                            "para especialista subordinado em shadow mode"
                        ),
                        linked_domain=route.domain_name,
                        selection_mode=route.specialist_mode,
                    )
                )
            else:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="not_eligible",
                        selection_score=0.25,
                        rationale=(
                            "o contexto atual nao justifica convocacao "
                            "especializada deste tipo"
                        ),
                        linked_domain=route.domain_name if route else None,
                        selection_mode=route.specialist_mode if route else "standard",
                    )
                )
        return selections[:3]

    def _build_contribution(
        self,
        *,
        invocation: SpecialistInvocationContract,
        specialist_hint: str,
        intent: str,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
    ) -> SpecialistContributionContract | None:
        knowledge_hint = (
            knowledge_snippets[0] if knowledge_snippets else "sem apoio extra de conhecimento"
        )
        if specialist_hint == "especialista_planejamento_operacional":
            open_loop = (
                plan.goal
                if plan.continuity_action in {"continuar", "retomar"}
                else "checkpoint_principal"
            )
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="planejamento_operacional_subordinado",
                focus="sequenciamento reversivel e checkpoints claros",
                findings=[
                    "success: plano deve preservar a menor proxima acao segura",
                    f"open_loop: {open_loop}",
                    f"constraint: validar checkpoint intermediario com base em {knowledge_hint}",
                ],
                recommendation=(
                    "encadear o plano em etapas pequenas, verificaveis "
                    "e conectadas a missao"
                ),
                confidence=0.79,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "checkpoint_recommendation",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == "especialista_analise_estruturada":
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "success: conclusao deve explicitar o criterio dominante de escolha",
                    "constraint: separar observacao, implicacao e recomendacao final",
                    (
                        "risk: falta de evidencia comparativa exige cautela "
                        f"se ignorar {knowledge_hint}"
                    ),
                ],
                recommendation=(
                    "fundir comparacao, implicacao e recomendacao "
                    "em uma unica linha analitica"
                ),
                confidence=0.82,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "decision_criteria",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == "especialista_revisao_governanca":
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="revisao_governanca_subordinada",
                focus="cautela operacional, auditoria e validacao",
                findings=[
                    "risk: plano exige cautela operacional reforcada antes de ampliar escopo",
                    "constraint: manter trilha observavel e condicoes de auditoria explicitas",
                    "open_loop: validar mudanca de objetivo antes de operar",
                ],
                recommendation=(
                    "manter o plano no escopo local ate que a governanca "
                    "confirme os limites"
                ),
                confidence=0.85,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "governance_constraints",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == "especialista_software_subordinado":
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="software_subordinado_shadow",
                focus="contratos, acoplamento e menor mudanca segura",
                findings=[
                    "success: qualquer mudanca deve preservar contratos centrais e rollback claro",
                    (
                        "constraint: limitar a mudanca ao menor recorte verificavel "
                        f"com base em {knowledge_hint}"
                    ),
                    (
                        "risk: acoplamento difuso entre servicos exige comparacao "
                        "controlada antes de promocao"
                    ),
                ],
                recommendation=(
                    "manter a leitura especializada em shadow mode e comparar o ganho "
                    "antes de torná-la parte do caminho principal"
                ),
                confidence=0.74,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "domain_shadow_specialist",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        return None

    @staticmethod
    def _build_summary(contributions: list[SpecialistContributionContract]) -> str:
        if not contributions:
            return "nenhuma contribuicao especializada adicional"
        recommendations = [item.recommendation for item in contributions if item.recommendation]
        return "; ".join(recommendations[:3])

    def _build_invocation(
        self,
        *,
        selection: SpecialistSelectionContract,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
        shared_memory_context: SpecialistSharedMemoryContextContract | None,
        session_id: str | None,
        mission_id: str | None,
        requested_by_service: str,
        sequence: int,
    ) -> SpecialistInvocationContract:
        specialist_hint = selection.specialist_type
        boundary = self._build_boundary(specialist_hint)
        knowledge_hint = (
            knowledge_snippets[0] if knowledge_snippets else "sem apoio extra de conhecimento"
        )
        session_token = (session_id or "local").replace(" ", "-")[-12:]
        invocation_id = f"{specialist_hint}-{session_token}-{sequence}"
        handoff_inputs = [
            f"goal={plan.goal}",
            f"plan_summary={plan.plan_summary}",
            f"continuity_action={plan.continuity_action or 'none'}",
            f"smallest_safe_next_action={plan.smallest_safe_next_action or 'none'}",
            f"knowledge_hint={knowledge_hint}",
        ]
        if shared_memory_context is not None:
            handoff_inputs.extend(
                [
                    f"shared_memory_brief={shared_memory_context.shared_memory_brief}",
                    f"shared_memory_mode={shared_memory_context.sharing_mode}",
                    f"memory_write_policy={shared_memory_context.write_policy}",
                ]
            )
            if shared_memory_context.source_mission_goal:
                handoff_inputs.append(
                    f"source_mission_goal={shared_memory_context.source_mission_goal}"
                )
            if shared_memory_context.related_mission_ids:
                handoff_inputs.append(
                    "related_mission_ids="
                    + ",".join(str(item) for item in shared_memory_context.related_mission_ids)
                )
        expected_outputs = [
            "structured_findings",
            "subordinated_recommendation",
            "confidence_score",
            "through_core_only",
        ]
        return SpecialistInvocationContract(
            invocation_id=invocation_id,
            specialist_type=specialist_hint,
            requested_by_service=requested_by_service,
            role=self._role_for_specialist(specialist_hint),
            task_focus=self._task_focus_for_specialist(specialist_hint),
            entry_summary=plan.plan_summary,
            handoff_inputs=handoff_inputs,
            expected_outputs=expected_outputs,
            boundary=boundary,
            session_id=session_id,
            mission_id=mission_id,
            shared_memory_context=shared_memory_context,
            linked_domain=selection.linked_domain,
            selection_mode=selection.selection_mode,
        )

    @staticmethod
    def _build_boundary(specialist_hint: str) -> SpecialistBoundaryContract:
        return SpecialistBoundaryContract(
            specialist_type=specialist_hint,
            runtime_scope="subordinated_internal",
            user_visibility="hidden_from_user",
            response_channel="through_core",
            tool_access_mode="none",
            memory_write_mode="through_core_only",
            operation_mode="advisory_only",
            allowed_tool_classes=[],
            blocked_tool_classes=[
                "shell",
                "browser",
                "external_api",
                "memory_write_direct",
                "direct_user_response",
            ],
        )

    @staticmethod
    def _role_for_specialist(specialist_hint: str) -> str:
        if specialist_hint == "especialista_planejamento_operacional":
            return "planejamento_operacional_subordinado"
        if specialist_hint == "especialista_analise_estruturada":
            return "analise_estruturada_subordinada"
        if specialist_hint == "especialista_revisao_governanca":
            return "revisao_governanca_subordinada"
        if specialist_hint == "especialista_software_subordinado":
            return "software_subordinado_shadow"
        return "especialista_subordinado"

    @staticmethod
    def _task_focus_for_specialist(specialist_hint: str) -> str:
        if specialist_hint == "especialista_planejamento_operacional":
            return "sequenciar etapas pequenas e checkpoints"
        if specialist_hint == "especialista_analise_estruturada":
            return "explicitar trade-offs e criterio de decisao"
        if specialist_hint == "especialista_revisao_governanca":
            return "revisar limites, auditoria e cautela operacional"
        if specialist_hint == "especialista_software_subordinado":
            return "avaliar contratos, acoplamento e menor mudanca segura"
        return "apoio especializado subordinado"

    @staticmethod
    def _build_boundary_summary(invocations: list[SpecialistInvocationContract]) -> str:
        if not invocations:
            return "nenhuma convocacao especializada adicional"
        return (
            "especialistas operam como runtime interno subordinado, "
            "sem resposta direta ao usuario, "
            "sem tools proprias e com memoria ou operacao mediadas pelo nucleo"
        )
