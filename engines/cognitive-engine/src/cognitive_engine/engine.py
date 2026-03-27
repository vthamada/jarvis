"""Cognitive engine for active minds, tensions, and specialist hints."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import DomainSpecialistRouteContract
from shared.domain_registry import FALLBACK_RUNTIME_ROUTE
from shared.mind_registry import (
    ACTIVE_MIND_REGISTRY,
    MIND_REGISTRY,
    arbitration_limits_for,
    definition_for,
    preferred_support_for,
)


@dataclass(frozen=True)
class CognitiveSnapshot:
    """Selected minds, tensions, and specialist hints for the current request."""

    active_minds: list[str]
    active_domains: list[str]
    rationale: str
    primary_mind: str
    tensions: list[str]
    specialist_hints: list[str]
    deliberation_notes: list[str]
    supporting_minds: list[str]
    suppressed_minds: list[str]
    dominant_tension: str
    arbitration_summary: str
    arbitration_source: str
    primary_mind_family: str
    supporting_mind_limit: int
    suppressed_mind_limit: int


class CognitiveEngine:
    """Select the first meaningful minds and tensions for the v1 nucleus."""

    name = "cognitive-engine"

    def build_snapshot(
        self,
        *,
        intent: str,
        risk_markers: list[str],
        retrieved_domains: list[str],
        domain_specialist_routes: list[DomainSpecialistRouteContract] | None = None,
        mind_hints: list[str] | None = None,
    ) -> CognitiveSnapshot:
        """Return an initial cognitive decomposition for the request."""

        active_domains = retrieved_domains or [FALLBACK_RUNTIME_ROUTE]
        ordered_minds = self._rank_minds(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
            mind_hints=mind_hints,
        )
        primary_mind = ordered_minds[0]
        primary_definition = definition_for(primary_mind)
        primary_family = (
            primary_definition.family if primary_definition is not None else "desconhecida"
        )
        supporting_limit, suppressed_limit = arbitration_limits_for(primary_mind)
        supporting_minds = self._select_supporting_minds(
            primary_mind=primary_mind,
            ordered_minds=ordered_minds,
            limit=supporting_limit,
        )
        suppressed_minds = self._select_suppressed_minds(
            primary_mind=primary_mind,
            ordered_minds=ordered_minds,
            supporting_minds=supporting_minds,
            limit=suppressed_limit,
        )
        tensions = self._select_tensions(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
        )
        dominant_tension = tensions[0]
        specialist_hints = self._select_specialist_hints(
            intent=intent,
            domains=active_domains,
            dominant_tension=dominant_tension,
            risk_markers=risk_markers,
            domain_specialist_routes=domain_specialist_routes or [],
        )
        arbitration_summary = self._build_arbitration_summary(
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            suppressed_minds=suppressed_minds,
            dominant_tension=dominant_tension,
            domains=active_domains,
        )
        deliberation_notes = self._build_deliberation_notes(
            intent=intent,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            dominant_tension=dominant_tension,
            specialist_hints=specialist_hints,
        )
        rationale = (
            f"mente_primaria={primary_mind}; familia={primary_family}; "
            f"suporte={', '.join(supporting_minds) or 'nenhum'}; "
            f"suprimidas={', '.join(suppressed_minds) or 'nenhuma'}; "
            f"limites={supporting_limit}/{suppressed_limit}; "
            f"tensao_dominante={dominant_tension}; dominios={active_domains}; "
            f"arbitragem={arbitration_summary}"
        )
        return CognitiveSnapshot(
            active_minds=[primary_mind, *supporting_minds],
            active_domains=active_domains,
            rationale=rationale,
            primary_mind=primary_mind,
            tensions=tensions,
            specialist_hints=specialist_hints,
            deliberation_notes=deliberation_notes,
            supporting_minds=supporting_minds,
            suppressed_minds=suppressed_minds,
            dominant_tension=dominant_tension,
            arbitration_summary=arbitration_summary,
            arbitration_source="mind_registry",
            primary_mind_family=primary_family,
            supporting_mind_limit=supporting_limit,
            suppressed_mind_limit=suppressed_limit,
        )

    @staticmethod
    def _rank_minds(
        *,
        intent: str,
        risk_markers: list[str],
        domains: list[str],
        mind_hints: list[str] | None = None,
    ) -> list[str]:
        hinted_minds = {
            mind_name for mind_name in (mind_hints or []) if mind_name in ACTIVE_MIND_REGISTRY
        }
        scored_minds: list[tuple[int, int, str]] = []
        for mind_name in ACTIVE_MIND_REGISTRY:
            definition = MIND_REGISTRY[mind_name]
            score = 0
            if mind_name in hinted_minds:
                score += 50
            if intent in definition.intent_affinities:
                score += 20
            score += sum(4 for domain in domains if domain in definition.domain_affinities)
            if len(domains) > 1 and definition.family in {
                "fundamental",
                "estrategica_decisoria",
            }:
                score += 2
            if risk_markers:
                if definition.risk_bias == "governance":
                    score += 8 if intent == "sensitive_action" else 4
                elif definition.risk_bias == "decision":
                    score += 6 if intent == "sensitive_action" else 3
                elif definition.risk_bias == "operational_caution":
                    score += 5 if intent != "analysis" else 0
            if definition.runtime_status == "nuclear_active":
                score += 5
            scored_minds.append((score, definition.arbitration_priority, mind_name))

        scored_minds.sort(key=lambda item: (-item[0], item[1], item[2]))
        ordered = [mind_name for score, _, mind_name in scored_minds if score > 0]
        if not ordered:
            ordered = ["mente_executiva", "mente_pragmatica"]
        return ordered

    @staticmethod
    def _select_supporting_minds(
        *,
        primary_mind: str,
        ordered_minds: list[str],
        limit: int,
    ) -> list[str]:
        supporting: list[str] = []
        chosen = {primary_mind}
        for supporting_mind in preferred_support_for(primary_mind):
            if supporting_mind in ACTIVE_MIND_REGISTRY and supporting_mind not in chosen:
                supporting.append(supporting_mind)
                chosen.add(supporting_mind)
            if len(supporting) >= limit:
                return supporting[:limit]
        for supporting_mind in ordered_minds:
            if supporting_mind not in chosen:
                supporting.append(supporting_mind)
                chosen.add(supporting_mind)
            if len(supporting) >= limit:
                break
        return supporting[:limit]

    @staticmethod
    def _select_suppressed_minds(
        *,
        primary_mind: str,
        ordered_minds: list[str],
        supporting_minds: list[str],
        limit: int,
    ) -> list[str]:
        chosen = {primary_mind, *supporting_minds}
        return [mind_name for mind_name in ordered_minds if mind_name not in chosen][:limit]

    @staticmethod
    def _select_tensions(
        *,
        intent: str,
        risk_markers: list[str],
        domains: list[str],
        primary_mind: str,
        supporting_minds: list[str],
    ) -> list[str]:
        tensions: list[str] = []
        primary_definition = definition_for(primary_mind)
        if primary_definition is not None:
            tensions.append(primary_definition.dominant_tension)
        if intent == "sensitive_action":
            tensions.append("equilibrar solicitacao do usuario com limites normativos")
        elif intent == "planning":
            tensions.append("equilibrar ambicao estrategica com a menor proxima acao segura")
        elif intent == "analysis":
            tensions.append("equilibrar profundidade analitica com conclusao util")
        else:
            tensions.append("equilibrar clareza executiva com contexto suficiente")
        if len(domains) > 1:
            tensions.append("integrar dominios sem diluir o objetivo dominante")
        if risk_markers:
            tensions.append("equilibrar velocidade de resposta com cautela operacional")
        if supporting_minds and "mente_critica" in supporting_minds:
            tensions.append("preservar escrutinio suficiente antes de concluir")
        return list(dict.fromkeys(tensions))

    @staticmethod
    def _select_specialist_hints(
        *,
        intent: str,
        domains: list[str],
        dominant_tension: str,
        risk_markers: list[str],
        domain_specialist_routes: list[DomainSpecialistRouteContract],
    ) -> list[str]:
        hints: list[str] = [
            route.specialist_type for route in domain_specialist_routes[:2]
        ]
        if intent == "planning" or "continuidade" in dominant_tension or len(domains) > 1:
            hints.append("especialista_planejamento_operacional")
        if intent == "analysis" or any(domain in domains for domain in ["analysis", "strategy"]):
            hints.append("especialista_analise_estruturada")
        if risk_markers or "governance" in domains or "normativos" in dominant_tension:
            hints.append("especialista_revisao_governanca")
        unique_hints: list[str] = []
        for hint in hints:
            if hint not in unique_hints:
                unique_hints.append(hint)
        return unique_hints[:3]

    @staticmethod
    def _build_arbitration_summary(
        *,
        primary_mind: str,
        supporting_minds: list[str],
        suppressed_minds: list[str],
        dominant_tension: str,
        domains: list[str],
    ) -> str:
        support = ", ".join(supporting_minds) if supporting_minds else "sem apoio adicional"
        suppressed = ", ".join(suppressed_minds) if suppressed_minds else "sem supressao relevante"
        domain_hint = ", ".join(domains[:2])
        return (
            f"{primary_mind} lidera a resposta com apoio de {support}, "
            f"suprimindo {suppressed} para manter foco em {domain_hint} "
            f"enquanto arbitra {dominant_tension}"
        )

    @staticmethod
    def _build_deliberation_notes(
        *,
        intent: str,
        primary_mind: str,
        supporting_minds: list[str],
        dominant_tension: str,
        specialist_hints: list[str],
    ) -> list[str]:
        notes = [
            f"linha_primaria={primary_mind}",
            f"modo={intent}",
            f"tensao_central={dominant_tension}",
            "fonte_arbitragem=mind_registry",
        ]
        if supporting_minds:
            notes.append(f"apoio={', '.join(supporting_minds)}")
        if specialist_hints:
            notes.append(f"apoio_subordinado={', '.join(specialist_hints[:2])}")
        return notes
