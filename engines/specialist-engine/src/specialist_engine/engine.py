"""Deterministic subordinated specialist engine for the v1 nucleus."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import DeliberativePlanContract, SpecialistContributionContract


@dataclass(frozen=True)
class SpecialistReview:
    """Structured output of subordinated specialist contributions."""

    specialist_hints: list[str]
    contributions: list[SpecialistContributionContract]
    summary: str
    findings: list[str]


class SpecialistEngine:
    """Produce subordinated specialist contributions without breaking unitary identity."""

    name = "specialist-engine"

    def review(
        self,
        *,
        intent: str,
        plan: DeliberativePlanContract,
        knowledge_snippets: list[str],
    ) -> SpecialistReview:
        """Build deterministic specialist contributions for the current plan."""

        active_hints = self._select_hints(intent=intent, plan=plan)
        contributions: list[SpecialistContributionContract] = []
        for specialist_hint in active_hints:
            contribution = self._build_contribution(
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
            specialist_hints=active_hints,
            contributions=contributions,
            summary=summary,
            findings=findings,
        )

    @staticmethod
    def _select_hints(*, intent: str, plan: DeliberativePlanContract) -> list[str]:
        active_hints: list[str] = []
        has_decomposition = len(plan.steps) >= 3 or bool(plan.continuity_action)
        has_tradeoff = intent == "analysis" or any(
            word in (plan.dominant_tension or "")
            for word in ("trade-off", "equilibrar", "comparar")
        )
        has_risk = plan.requires_human_validation or any(
            "risco" in risk or "govern" in risk for risk in plan.risks
        )
        for specialist_hint in plan.specialist_hints:
            if specialist_hint == "especialista_planejamento_operacional" and has_decomposition:
                active_hints.append(specialist_hint)
            elif specialist_hint == "especialista_analise_estruturada" and has_tradeoff:
                active_hints.append(specialist_hint)
            elif specialist_hint == "especialista_revisao_governanca" and has_risk:
                active_hints.append(specialist_hint)
        return active_hints[:3]

    def _build_contribution(
        self,
        *,
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
                plan.goal if plan.continuity_action == "continuar" else "checkpoint_principal"
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
            )
        return None

    @staticmethod
    def _build_summary(contributions: list[SpecialistContributionContract]) -> str:
        if not contributions:
            return "nenhuma contribuicao especializada adicional"
        recommendations = [item.recommendation for item in contributions if item.recommendation]
        return "; ".join(recommendations[:3])
