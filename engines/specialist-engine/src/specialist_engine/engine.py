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

        contributions: list[SpecialistContributionContract] = []
        for specialist_hint in plan.specialist_hints:
            contribution = self._build_contribution(
                specialist_hint=specialist_hint,
                intent=intent,
                plan=plan,
                knowledge_snippets=knowledge_snippets,
            )
            if contribution:
                contributions.append(contribution)

        findings = [
            finding
            for contribution in contributions
            for finding in contribution.findings[:2]
        ]
        if contributions:
            summary = " | ".join(
                f"{item.specialist_type}: {item.recommendation}" for item in contributions
            )
        else:
            summary = "nenhuma contribuicao especializada adicional"
        return SpecialistReview(
            specialist_hints=list(plan.specialist_hints),
            contributions=contributions,
            summary=summary,
            findings=findings,
        )

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
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="planejamento_operacional_subordinado",
                focus="sequenciamento reversivel e checkpoints claros",
                findings=[
                    "priorizar a menor acao segura antes de expandir escopo",
                    "explicitar checkpoints intermediarios para preservar rastreabilidade",
                    f"usar apoio contextual: {knowledge_hint}",
                ],
                recommendation="executar o plano em etapas pequenas e verificaveis",
                confidence=0.78,
            )
        if specialist_hint == "especialista_analise_estruturada":
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="analise_estruturada_subordinada",
                focus="trade-offs, evidencia e criterio de decisao",
                findings=[
                    "separar observacao, implicacao e recomendacao final",
                    "explicitar o trade-off dominante antes de concluir",
                    f"apoiar a leitura em: {knowledge_hint}",
                ],
                recommendation="concluir com recomendacao argumentada e sem executar mudancas",
                confidence=0.81,
            )
        if specialist_hint == "especialista_revisao_governanca":
            return SpecialistContributionContract(
                specialist_type=specialist_hint,
                role="revisao_governanca_subordinada",
                focus="cautela operacional, auditoria e validacao",
                findings=[
                    "verificar se o plano permanece totalmente reversivel",
                    "reforcar trilha observavel e condicoes de auditoria",
                    "elevar para validacao humana se houver mutacao sensivel",
                ],
                recommendation="manter o plano no escopo local ate confirmacao explicita",
                confidence=0.84,
            )
        return None
