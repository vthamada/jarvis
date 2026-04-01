"""Deterministic subordinated specialist engine for the v1 nucleus."""

from __future__ import annotations

from dataclasses import dataclass, replace
from unicodedata import normalize

from shared.contracts import (
    DeliberativePlanContract,
    DomainSpecialistRouteContract,
    SpecialistBoundaryContract,
    SpecialistContributionContract,
    SpecialistInvocationContract,
    SpecialistSelectionContract,
    SpecialistSharedMemoryContextContract,
)
from shared.domain_registry import (
    canonical_domain_refs_for_name,
    specialist_eligible_route,
    specialist_route_payload,
)
from shared.specialist_registry import (
    GOVERNANCE_REVIEW_SPECIALIST,
    OPERATIONAL_PLANNING_SPECIALIST,
    SOFTWARE_CHANGE_SPECIALIST,
    STRUCTURED_ANALYSIS_SPECIALIST,
    canonical_specialist_type,
    normalize_specialist_types,
)


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

        normalized_plan = replace(
            plan,
            specialist_hints=normalize_specialist_types(plan.specialist_hints),
        )
        normalized_routes = [
            replace(
                route,
                specialist_type=canonical_specialist_type(route.specialist_type),
            )
            for route in (domain_specialist_routes or [])
        ]
        normalized_contexts = {
            canonical_specialist_type(key): replace(
                value,
                specialist_type=canonical_specialist_type(value.specialist_type),
            )
            for key, value in (shared_memory_contexts or {}).items()
        }
        selections = self._select_handoffs(
            intent=intent,
            plan=normalized_plan,
            domain_specialist_routes=normalized_routes,
        )
        invocations: list[SpecialistInvocationContract] = []
        for index, selection in enumerate(
            [item for item in selections if item.selection_status == "selected"],
            start=1,
        ):
            shared_memory_context = normalized_contexts.get(selection.specialist_type)
            coherence_issue = self._validate_route_domain_memory_coherence(
                selection=selection,
                plan=normalized_plan,
                shared_memory_context=shared_memory_context,
            )
            if coherence_issue is not None:
                selection.selection_status = "not_eligible"
                selection.selection_score = 0.21
                selection.rationale = coherence_issue
                continue
            invocation = self._build_invocation(
                selection=selection,
                plan=normalized_plan,
                knowledge_snippets=knowledge_snippets,
                shared_memory_context=shared_memory_context,
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
                if item.selection_status == "selected" and item.invocation_id is not None
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

        def canonical_route_for(specialist_type: str) -> DomainSpecialistRouteContract | None:
            matched = specialist_eligible_route(plan.active_domains, specialist_type)
            if matched is None:
                return None
            route_name, entry = matched
            for route in domain_specialist_routes:
                if route.domain_name == route_name and route.specialist_type == specialist_type:
                    return route
            return DomainSpecialistRouteContract(
                domain_name=route_name,
                specialist_type=specialist_type,
                specialist_mode=entry.specialist_mode or "standard",
                routing_reason=entry.summary,
                canonical_domain_refs=list(entry.canonical_refs),
                routing_source="domain_registry",
            )

        has_decomposition = len(plan.steps) >= 3 or bool(plan.continuity_action)
        has_tradeoff = intent == "analysis" or any(
            word in (plan.dominant_tension or "")
            for word in ("trade-off", "equilibrar", "comparar")
        )
        has_risk = plan.requires_human_validation or any(
            "risco" in risk or "govern" in risk for risk in plan.risks
        )
        for specialist_hint in plan.specialist_hints:
            route = canonical_route_for(specialist_hint)
            selection_mode = (
                route.specialist_mode if route and route.specialist_mode else "standard"
            )
            linked_domain = route.domain_name if route else None
            if route is None:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="not_eligible",
                        selection_score=0.18,
                        rationale=(
                            "o registry soberano nao confirmou uma rota canonica ativa "
                            "para este especialista"
                        ),
                        linked_domain=None,
                        selection_mode="standard",
                    )
                )
                continue
            if specialist_hint == OPERATIONAL_PLANNING_SPECIALIST and has_decomposition:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.84,
                        rationale=(
                            "o plano exige decomposicao, checkpoints "
                            "e menor proxima acao segura em rota canonica ativa"
                        ),
                        linked_domain=linked_domain,
                        selection_mode=selection_mode,
                    )
                )
            elif specialist_hint == STRUCTURED_ANALYSIS_SPECIALIST and has_tradeoff:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.82,
                        rationale=(
                            "o contexto exige comparacao estruturada "
                            "e criterio explicito de decisao em rota canonica ativa"
                        ),
                        linked_domain=linked_domain,
                        selection_mode=selection_mode,
                    )
                )
            elif specialist_hint == GOVERNANCE_REVIEW_SPECIALIST and has_risk:
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=0.87,
                        rationale=(
                            "o plano exige cautela normativa, auditoria e revisao de limites "
                            "em rota canonica ativa"
                        ),
                        requires_governance_review=True,
                        linked_domain=linked_domain,
                        selection_mode=selection_mode,
                    )
                )
            elif specialist_hint == SOFTWARE_CHANGE_SPECIALIST:
                selection_score = 0.84 if selection_mode in {"guided", "active"} else 0.78
                rationale = (
                    "o dominio de software ativo abriu uma rota canonica promovida "
                    "para especialista subordinado, ainda mediada pelo nucleo"
                    if selection_mode in {"guided", "active"}
                    else (
                        "o dominio de software ativo abriu a primeira rota canonica "
                        "para especialista subordinado em shadow mode"
                    )
                )
                selections.append(
                    SpecialistSelectionContract(
                        specialist_type=specialist_hint,
                        selection_status="selected",
                        selection_score=selection_score,
                        rationale=rationale,
                        linked_domain=linked_domain,
                        selection_mode=selection_mode,
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
                        linked_domain=linked_domain,
                        selection_mode=selection_mode,
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
        if specialist_hint == OPERATIONAL_PLANNING_SPECIALIST:
            open_loop = (
                plan.goal
                if plan.continuity_action in {"continuar", "retomar"}
                else "checkpoint_principal"
            )
            is_promoted_mode = invocation.selection_mode in {"guided", "active"}
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role=(
                    "planejamento_operacional_guided"
                    if is_promoted_mode
                    else "planejamento_operacional_subordinado"
                ),
                focus=(
                    "sequenciamento guiado por dominio com checkpoints claros"
                    if is_promoted_mode
                    else "sequenciamento reversivel e checkpoints claros"
                ),
                findings=[
                    "success: plano deve preservar a menor proxima acao segura",
                    f"open_loop: {open_loop}",
                    f"constraint: validar checkpoint intermediario com base em {knowledge_hint}",
                ],
                recommendation=(
                    "encadear o plano em etapas pequenas, verificaveis "
                    "e conectadas a missao"
                ),
                confidence=0.81 if is_promoted_mode else 0.79,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "checkpoint_recommendation",
                    "domain_guided_specialist" if is_promoted_mode else "through_core_only",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == STRUCTURED_ANALYSIS_SPECIALIST:
            is_promoted_mode = invocation.selection_mode in {"guided", "active"}
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role=(
                    "analise_estruturada_guided"
                    if is_promoted_mode
                    else "analise_estruturada_subordinada"
                ),
                focus=(
                    "comparacao estruturada guiada por dominio, evidencia e criterio de decisao"
                    if is_promoted_mode
                    else "trade-offs, evidencia e criterio de decisao"
                ),
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
                confidence=0.84 if is_promoted_mode else 0.82,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "decision_criteria",
                    "domain_guided_specialist" if is_promoted_mode else "through_core_only",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == GOVERNANCE_REVIEW_SPECIALIST:
            is_promoted_mode = invocation.selection_mode in {"guided", "active"}
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role=(
                    "revisao_governanca_guided"
                    if is_promoted_mode
                    else "revisao_governanca_subordinada"
                ),
                focus=(
                    "governanca guiada por dominio, auditoria e validacao"
                    if is_promoted_mode
                    else "cautela operacional, auditoria e validacao"
                ),
                findings=[
                    "risk: plano exige cautela operacional reforcada antes de ampliar escopo",
                    "constraint: manter trilha observavel e condicoes de auditoria explicitas",
                    "open_loop: validar mudanca de objetivo antes de operar",
                ],
                recommendation=(
                    "manter o plano no escopo local ate que a governanca "
                    "confirme os limites"
                ),
                confidence=0.87 if is_promoted_mode else 0.85,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "governance_constraints",
                    "domain_guided_specialist" if is_promoted_mode else "through_core_only",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        if specialist_hint == SOFTWARE_CHANGE_SPECIALIST:
            is_promoted_mode = invocation.selection_mode in {"guided", "active"}
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role=(
                    "software_subordinado_guided"
                    if is_promoted_mode
                    else "software_subordinado_shadow"
                ),
                focus=(
                    "contratos, acoplamento e mudanca segura guiada por dominio"
                    if is_promoted_mode
                    else "contratos, acoplamento e menor mudanca segura"
                ),
                findings=[
                    "success: qualquer mudanca deve preservar contratos centrais e rollback claro",
                    (
                        "constraint: limitar a mudanca ao menor recorte verificavel "
                        f"com base em {knowledge_hint}"
                    ),
                    (
                        "constraint: manter execucao, escrita de memoria e resposta final "
                        "sempre through_core_only"
                        if is_promoted_mode
                        else (
                            "risk: acoplamento difuso entre servicos exige comparacao "
                            "controlada antes de promocao"
                        )
                    ),
                ],
                recommendation=(
                    "usar a leitura especializada como apoio canonico do dominio, "
                    "mantendo toda promocao e execucao mediadas pelo nucleo"
                    if is_promoted_mode
                    else (
                        "manter a leitura especializada em shadow mode e comparar o ganho "
                        "antes de torna-la parte do caminho principal"
                    )
                ),
                confidence=0.81 if is_promoted_mode else 0.74,
                invocation_id=invocation.invocation_id,
                output_hints=[
                    "structured_findings",
                    "domain_guided_specialist" if is_promoted_mode else "domain_shadow_specialist",
                    "through_core_only",
                ],
                handoff_channel=invocation.boundary.response_channel,
            )
        return None

    @staticmethod
    def _normalize_contract_text(value: object | None) -> str:
        if value is None:
            return ""
        collapsed = " ".join(str(value).split())
        normalized = normalize("NFKD", collapsed)
        return "".join(char for char in normalized if not ord(char) > 127).lower()

    @staticmethod
    def _build_summary(contributions: list[SpecialistContributionContract]) -> str:
        if not contributions:
            return "nenhuma contribuicao especializada adicional"
        recommendations = [item.recommendation for item in contributions if item.recommendation]
        return "; ".join(recommendations[:3])

    @staticmethod
    def _validate_route_domain_memory_coherence(
        *,
        selection: SpecialistSelectionContract,
        plan: DeliberativePlanContract,
        shared_memory_context: SpecialistSharedMemoryContextContract | None,
    ) -> str | None:
        if selection.linked_domain is None:
            return None
        if selection.linked_domain not in plan.active_domains:
            return "coerencia rota->dominio falhou: dominio vinculado nao esta no plano ativo"
        route_payload = specialist_route_payload(
            selection.linked_domain,
            selection.specialist_type,
        )
        if route_payload["eligible"] is not True or route_payload["link_matches"] is not True:
            return "coerencia rota->especialista falhou: registry soberano nao confirma o vinculo"
        if route_payload["specialist_mode"] != selection.selection_mode:
            return "coerencia rota->modo falhou: selection_mode diverge do registry soberano"
        if shared_memory_context is None:
            return "coerencia especialista->memoria falhou: contexto compartilhado ausente"
        if selection.selection_mode in {"guided", "active"} and (
            shared_memory_context.consumer_mode != "domain_guided_memory_packet"
        ):
            return "coerencia especialista->memoria falhou: rota guiada sem packet canonico"
        if selection.selection_mode in {"guided", "active"} and not (
            shared_memory_context.consumer_profile and shared_memory_context.consumer_objective
        ):
            return "coerencia especialista->memoria falhou: packet guiado sem consumer profile"
        if selection.selection_mode in {"guided", "active"} and (
            route_payload.get("consumer_profile")
            and shared_memory_context.consumer_profile != route_payload.get("consumer_profile")
        ):
            return "coerencia especialista->memoria falhou: consumer_profile diverge do registry"
        if selection.selection_mode in {"guided", "active"} and (
            route_payload.get("consumer_objective")
            and SpecialistEngine._normalize_contract_text(
                shared_memory_context.consumer_objective
            )
            != SpecialistEngine._normalize_contract_text(
                route_payload.get("consumer_objective")
            )
        ):
            return "coerencia especialista->memoria falhou: consumer_objective diverge do registry"
        if selection.selection_mode in {"guided", "active"} and (
            route_payload.get("expected_deliverables")
            and list(shared_memory_context.expected_deliverables)
            != list(route_payload.get("expected_deliverables", []))
        ):
            return (
                "coerencia especialista->memoria falhou: expected_deliverables divergem do registry"
            )
        if selection.selection_mode in {"guided", "active"} and (
            route_payload.get("telemetry_focus")
            and list(shared_memory_context.telemetry_focus)
            != list(route_payload.get("telemetry_focus", []))
        ):
            return "coerencia especialista->memoria falhou: telemetry_focus diverge do registry"
        consumed_classes = set(shared_memory_context.consumed_memory_classes)
        if not consumed_classes:
            consumed_classes = set(shared_memory_context.memory_class_policies)
        if not consumed_classes:
            consumed_classes = {
                ref.removeprefix("memory://").split("/", 1)[0]
                for ref in shared_memory_context.memory_refs
                if ref.startswith("memory://")
            }
        if not consumed_classes:
            return "coerencia especialista->memoria falhou: classes consumidas ausentes"
        if shared_memory_context.consumed_memory_classes and not {
            "domain",
            "mission",
            "contextual",
        }.issubset(consumed_classes):
            return "coerencia especialista->memoria falhou: classes minimas nao anexadas"
        memory_refs = set(shared_memory_context.memory_refs)
        if "semantic" in consumed_classes and not any(
            ref.startswith("memory://semantic") for ref in memory_refs
        ):
            return "coerencia especialista->memoria falhou: semantic sem ref guiado"
        if "procedural" in consumed_classes and not any(
            ref.startswith("memory://procedural") for ref in memory_refs
        ):
            return "coerencia especialista->memoria falhou: procedural sem ref guiado"
        linked_refs = set(canonical_domain_refs_for_name(selection.linked_domain))
        semantic_focus = set(shared_memory_context.semantic_focus)
        if linked_refs and not (
            linked_refs.intersection(semantic_focus) or selection.linked_domain in semantic_focus
        ):
            return (
                "coerencia dominio->memoria falhou: foco semantico nao reflete o dominio canonico"
            )
        if not (
            shared_memory_context.domain_mission_link_reason
            or shared_memory_context.domain_context_brief
            or shared_memory_context.mission_context_brief
        ):
            return "coerencia dominio->missao falhou: justificativa explicita ausente"
        return None

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
                    f"consumer_mode={shared_memory_context.consumer_mode}",
                    "consumed_memory_classes="
                    + ",".join(shared_memory_context.consumed_memory_classes),
                ]
            )
            if shared_memory_context.domain_mission_link_reason:
                handoff_inputs.append(
                    "domain_mission_link_reason="
                    f"{shared_memory_context.domain_mission_link_reason}"
                )
            if shared_memory_context.source_mission_goal:
                handoff_inputs.append(
                    f"source_mission_goal={shared_memory_context.source_mission_goal}"
                )
            if shared_memory_context.mission_context_brief:
                handoff_inputs.append(
                    f"mission_context_brief={shared_memory_context.mission_context_brief}"
                )
            if shared_memory_context.domain_context_brief:
                handoff_inputs.append(
                    f"domain_context_brief={shared_memory_context.domain_context_brief}"
                )
            if shared_memory_context.continuity_context_brief:
                handoff_inputs.append(
                    "continuity_context_brief="
                    f"{shared_memory_context.continuity_context_brief}"
                )
            handoff_inputs.append(
                "recurrent_context_status="
                f"{shared_memory_context.recurrent_context_status}"
            )
            handoff_inputs.append(
                "recurrent_interaction_count="
                f"{shared_memory_context.recurrent_interaction_count}"
            )
            if shared_memory_context.recurrent_context_brief:
                handoff_inputs.append(
                    "recurrent_context_brief="
                    f"{shared_memory_context.recurrent_context_brief}"
                )
            if shared_memory_context.recurrent_domain_focus:
                handoff_inputs.append(
                    "recurrent_domain_focus="
                    + ",".join(shared_memory_context.recurrent_domain_focus[:3])
                )
            if shared_memory_context.recurrent_continuity_modes:
                handoff_inputs.append(
                    "recurrent_continuity_modes="
                    + ",".join(shared_memory_context.recurrent_continuity_modes[:3])
                )
            if shared_memory_context.consumer_profile:
                handoff_inputs.append(
                    f"consumer_profile={shared_memory_context.consumer_profile}"
                )
            if shared_memory_context.consumer_objective:
                handoff_inputs.append(
                    f"consumer_objective={shared_memory_context.consumer_objective}"
                )
            if shared_memory_context.expected_deliverables:
                handoff_inputs.append(
                    "expected_deliverables="
                    + ",".join(shared_memory_context.expected_deliverables)
                )
            if shared_memory_context.telemetry_focus:
                handoff_inputs.append(
                    "telemetry_focus=" + ",".join(shared_memory_context.telemetry_focus)
                )
            if shared_memory_context.semantic_focus:
                handoff_inputs.append(
                    "semantic_focus=" + ",".join(shared_memory_context.semantic_focus[:4])
                )
            if shared_memory_context.open_loops:
                handoff_inputs.append(
                    "open_loops=" + ";".join(shared_memory_context.open_loops[:3])
                )
            if shared_memory_context.related_mission_ids:
                handoff_inputs.append(
                    "related_mission_ids="
                    + ",".join(str(item) for item in shared_memory_context.related_mission_ids)
                )
        expected_outputs = (
            list(shared_memory_context.expected_deliverables)
            if shared_memory_context and shared_memory_context.expected_deliverables
            else [
                "structured_findings",
                "subordinated_recommendation",
                "confidence_score",
            ]
        )
        expected_outputs.append("through_core_only")
        return SpecialistInvocationContract(
            invocation_id=invocation_id,
            specialist_type=specialist_hint,
            requested_by_service=requested_by_service,
            role=self._role_for_specialist(specialist_hint, selection.selection_mode),
            task_focus=self._task_focus_for_specialist(specialist_hint, selection.selection_mode),
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
    def _role_for_specialist(specialist_hint: str, selection_mode: str = "standard") -> str:
        if specialist_hint == OPERATIONAL_PLANNING_SPECIALIST:
            return (
                "planejamento_operacional_guided"
                if selection_mode in {"guided", "active"}
                else "planejamento_operacional_subordinado"
            )
        if specialist_hint == STRUCTURED_ANALYSIS_SPECIALIST:
            return "analise_estruturada_subordinada"
        if specialist_hint == GOVERNANCE_REVIEW_SPECIALIST:
            return (
                "revisao_governanca_guided"
                if selection_mode in {"guided", "active"}
                else "revisao_governanca_subordinada"
            )
        if specialist_hint == SOFTWARE_CHANGE_SPECIALIST:
            return (
                "software_subordinado_guided"
                if selection_mode in {"guided", "active"}
                else "software_subordinado_shadow"
            )
        return "especialista_subordinado"

    @staticmethod
    def _task_focus_for_specialist(specialist_hint: str, selection_mode: str = "standard") -> str:
        if specialist_hint == OPERATIONAL_PLANNING_SPECIALIST:
            return (
                "sequenciar etapas pequenas e checkpoints guiados por dominio"
                if selection_mode in {"guided", "active"}
                else "sequenciar etapas pequenas e checkpoints"
            )
        if specialist_hint == STRUCTURED_ANALYSIS_SPECIALIST:
            return "explicitar trade-offs e criterio de decisao"
        if specialist_hint == GOVERNANCE_REVIEW_SPECIALIST:
            return (
                "revisar limites, auditoria e cautela operacional guiadas por dominio"
                if selection_mode in {"guided", "active"}
                else "revisar limites, auditoria e cautela operacional"
            )
        if specialist_hint == SOFTWARE_CHANGE_SPECIALIST:
            return (
                "avaliar contratos, acoplamento e mudanca segura guiada por dominio"
                if selection_mode in {"guided", "active"}
                else "avaliar contratos, acoplamento e menor mudanca segura"
            )
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
