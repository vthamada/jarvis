"""Cognitive engine for active minds, tensions, and specialist hints."""

from __future__ import annotations

from dataclasses import dataclass

from shared.contracts import DomainSpecialistRouteContract
from shared.domain_registry import (
    FALLBACK_RUNTIME_ROUTE,
    canonical_domain_refs_for_name,
    route_is_specialist_eligible,
    route_linked_specialist_type,
)
from shared.mind_registry import (
    arbitration_limits_for,
    build_arbitration_summary,
    build_deliberation_notes,
    definition_for,
    rank_active_minds,
    select_supporting_minds,
    select_suppressed_minds,
    select_tensions,
)
from shared.mind_registry import (
    primary_domain_driver as resolve_primary_domain_driver,
)


@dataclass(frozen=True)
class CognitiveSnapshot:
    """Selected minds, tensions, and specialist hints for the current request."""

    active_minds: list[str]
    active_domains: list[str]
    canonical_domains: list[str]
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
    primary_domain_driver: str | None
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
        canonical_domains = self._resolve_canonical_domains(active_domains)
        ordered_minds = rank_active_minds(
            intent=intent,
            risk_markers=risk_markers,
            canonical_domains=canonical_domains,
            mind_hints=mind_hints,
        )
        primary_mind = ordered_minds[0]
        primary_definition = definition_for(primary_mind)
        primary_family = (
            primary_definition.family if primary_definition is not None else "desconhecida"
        )
        supporting_limit, suppressed_limit = arbitration_limits_for(primary_mind)
        supporting_minds = select_supporting_minds(
            primary_mind=primary_mind,
            ordered_minds=ordered_minds,
            limit=supporting_limit,
        )
        suppressed_minds = select_suppressed_minds(
            primary_mind=primary_mind,
            ordered_minds=ordered_minds,
            supporting_minds=supporting_minds,
            limit=suppressed_limit,
        )
        tensions = select_tensions(
            intent=intent,
            risk_markers=risk_markers,
            domains=active_domains,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
        )
        dominant_tension = tensions[0]
        dominant_domain_driver = resolve_primary_domain_driver(
            primary_mind=primary_mind,
            canonical_domains=canonical_domains,
        )
        specialist_hints = self._select_specialist_hints(
            intent=intent,
            domains=active_domains,
            dominant_tension=dominant_tension,
            risk_markers=risk_markers,
            domain_specialist_routes=domain_specialist_routes or [],
            primary_domain_driver=dominant_domain_driver,
        )
        arbitration_summary = build_arbitration_summary(
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            suppressed_minds=suppressed_minds,
            dominant_tension=dominant_tension,
            domains=active_domains,
        )
        deliberation_notes = build_deliberation_notes(
            intent=intent,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            dominant_tension=dominant_tension,
            specialist_hints=specialist_hints,
            primary_domain_driver=dominant_domain_driver,
        )
        rationale = (
            f"mente_primaria={primary_mind}; familia={primary_family}; "
            f"suporte={', '.join(supporting_minds) or 'nenhum'}; "
            f"suprimidas={', '.join(suppressed_minds) or 'nenhuma'}; "
            f"limites={supporting_limit}/{suppressed_limit}; "
            f"tensao_dominante={dominant_tension}; dominios={active_domains}; "
            f"dominios_canonicos={canonical_domains}; "
            f"dominio_primario={dominant_domain_driver or 'none'}; "
            f"arbitragem={arbitration_summary}"
        )
        return CognitiveSnapshot(
            active_minds=[primary_mind, *supporting_minds],
            active_domains=active_domains,
            canonical_domains=canonical_domains,
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
            primary_domain_driver=dominant_domain_driver,
            supporting_mind_limit=supporting_limit,
            suppressed_mind_limit=suppressed_limit,
        )

    @staticmethod
    def _select_specialist_hints(
        *,
        intent: str,
        domains: list[str],
        dominant_tension: str,
        risk_markers: list[str],
        domain_specialist_routes: list[DomainSpecialistRouteContract],
        primary_domain_driver: str | None,
    ) -> list[str]:
        del (
            intent,
            dominant_tension,
            risk_markers,
            domain_specialist_routes,
            primary_domain_driver,
        )
        hints: list[str] = []
        for route_name in domains:
            specialist_type = route_linked_specialist_type(route_name)
            if specialist_type is None:
                continue
            if not route_is_specialist_eligible(route_name, specialist_type):
                continue
            if specialist_type not in hints:
                hints.append(specialist_type)
        return hints[:3]

    @staticmethod
    def _resolve_canonical_domains(domains: list[str]) -> list[str]:
        canonical_domains: list[str] = []
        for domain in domains:
            for canonical_ref in canonical_domain_refs_for_name(domain):
                if canonical_ref not in canonical_domains:
                    canonical_domains.append(canonical_ref)
        return canonical_domains

