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
from shared.specialist_registry import canonical_specialist_type


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
    recomposition_applied: bool
    recomposition_reason: str | None
    recomposition_trigger: str | None
    memory_priority_applied: bool
    memory_priority_domains: list[str]
    memory_priority_specialist_hints: list[str]
    memory_priority_sources: list[str]
    memory_priority_summary: str | None


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
        memory_priority_domains: list[str] | None = None,
        memory_specialist_hints: list[str] | None = None,
        memory_priority_sources: list[str] | None = None,
        memory_priority_summary: str | None = None,
    ) -> CognitiveSnapshot:
        """Return an initial cognitive decomposition for the request."""

        active_domains = self._prioritize_domains_with_memory(
            retrieved_domains or [FALLBACK_RUNTIME_ROUTE],
            memory_priority_domains or [],
        )
        canonical_domains = self._resolve_canonical_domains(active_domains)
        normalized_routes = [
            DomainSpecialistRouteContract(
                domain_name=route.domain_name,
                specialist_type=canonical_specialist_type(route.specialist_type),
                specialist_mode=route.specialist_mode,
                routing_reason=route.routing_reason,
                canonical_domain_refs=list(route.canonical_domain_refs),
                routing_source=route.routing_source,
            )
            for route in (domain_specialist_routes or [])
        ]
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
        (
            supporting_minds,
            suppressed_minds,
            arbitration_source,
            recomposition_applied,
            recomposition_reason,
            recomposition_trigger,
        ) = self._maybe_recompose_for_impasse(
            primary_mind=primary_mind,
            ordered_minds=ordered_minds,
            supporting_minds=supporting_minds,
            supporting_limit=supporting_limit,
            suppressed_limit=suppressed_limit,
            active_domains=active_domains,
            primary_domain_driver=dominant_domain_driver,
            domain_specialist_routes=normalized_routes,
        )
        specialist_hints = self._select_specialist_hints(
            intent=intent,
            domains=active_domains,
            dominant_tension=dominant_tension,
            risk_markers=risk_markers,
            domain_specialist_routes=normalized_routes,
            primary_domain_driver=dominant_domain_driver,
            memory_specialist_hints=memory_specialist_hints or [],
        )
        arbitration_summary = build_arbitration_summary(
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            suppressed_minds=suppressed_minds,
            dominant_tension=dominant_tension,
            domains=active_domains,
        )
        if recomposition_applied and recomposition_reason and recomposition_trigger:
            arbitration_summary = (
                f"{arbitration_summary}; recomposicao={recomposition_trigger}:"
                f" {recomposition_reason}"
            )
        deliberation_notes = build_deliberation_notes(
            intent=intent,
            primary_mind=primary_mind,
            supporting_minds=supporting_minds,
            dominant_tension=dominant_tension,
            specialist_hints=specialist_hints,
            primary_domain_driver=dominant_domain_driver,
        )
        if recomposition_applied and recomposition_reason and recomposition_trigger:
            deliberation_notes.append(
                "recomposicao_cognitiva="
                f"{recomposition_trigger}:{recomposition_reason}"
            )
        rationale = (
            f"mente_primaria={primary_mind}; familia={primary_family}; "
            f"suporte={', '.join(supporting_minds) or 'nenhum'}; "
            f"suprimidas={', '.join(suppressed_minds) or 'nenhuma'}; "
            f"limites={supporting_limit}/{suppressed_limit}; "
            f"tensao_dominante={dominant_tension}; dominios={active_domains}; "
            f"dominios_canonicos={canonical_domains}; "
            f"dominio_primario={dominant_domain_driver or 'none'}; "
            f"fonte_arbitragem={arbitration_source}; "
            f"arbitragem={arbitration_summary}; "
            f"recomposicao_aplicada={recomposition_applied}; "
            "memoria_prioridade="
            f"{'on' if memory_priority_domains else 'off'};"
            f"memoria_dominios={memory_priority_domains or ['none']}; "
            f"memoria_hints={memory_specialist_hints or ['none']}"
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
            arbitration_source=arbitration_source,
            primary_mind_family=primary_family,
            primary_domain_driver=dominant_domain_driver,
            supporting_mind_limit=supporting_limit,
            suppressed_mind_limit=suppressed_limit,
            recomposition_applied=recomposition_applied,
            recomposition_reason=recomposition_reason,
            recomposition_trigger=recomposition_trigger,
            memory_priority_applied=bool(memory_priority_domains or memory_specialist_hints),
            memory_priority_domains=list(memory_priority_domains or []),
            memory_priority_specialist_hints=list(memory_specialist_hints or []),
            memory_priority_sources=list(memory_priority_sources or []),
            memory_priority_summary=memory_priority_summary,
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
        memory_specialist_hints: list[str],
    ) -> list[str]:
        del (intent, dominant_tension, risk_markers)
        hints: list[str] = []
        for specialist_type in memory_specialist_hints:
            canonical_type = canonical_specialist_type(specialist_type)
            if canonical_type not in hints:
                hints.append(canonical_type)
        route_map = {
            route.domain_name: route
            for route in domain_specialist_routes
            if route.domain_name in domains
        }
        prioritized_domains: list[str] = []
        if primary_domain_driver is not None and route_map:
            for route_name in domains:
                route_contract = route_map.get(route_name)
                if route_contract is not None:
                    canonical_refs = list(route_contract.canonical_domain_refs) or list(
                        canonical_domain_refs_for_name(route_name)
                    )
                else:
                    canonical_refs = list(canonical_domain_refs_for_name(route_name))
                if (
                    primary_domain_driver in canonical_refs
                    and route_name not in prioritized_domains
                ):
                    prioritized_domains.append(route_name)
        ordered_domains = prioritized_domains + [
            route_name for route_name in domains if route_name not in prioritized_domains
        ]
        for route_name in ordered_domains:
            route_contract = route_map.get(route_name)
            if route_contract is not None:
                specialist_type = canonical_specialist_type(route_contract.specialist_type)
                if route_is_specialist_eligible(route_name, specialist_type):
                    if specialist_type not in hints:
                        hints.append(specialist_type)
                continue
            if route_map:
                continue
            specialist_type = route_linked_specialist_type(route_name)
            if specialist_type is None:
                continue
            if not route_is_specialist_eligible(route_name, specialist_type):
                continue
            if specialist_type not in hints:
                hints.append(specialist_type)
        return hints[:3]

    @staticmethod
    def _prioritize_domains_with_memory(
        domains: list[str],
        memory_priority_domains: list[str],
    ) -> list[str]:
        prioritized = [domain for domain in memory_priority_domains if domain in domains]
        if not prioritized:
            return list(domains)
        return prioritized + [domain for domain in domains if domain not in prioritized]

    @staticmethod
    def _resolve_canonical_domains(domains: list[str]) -> list[str]:
        canonical_domains: list[str] = []
        for domain in domains:
            for canonical_ref in canonical_domain_refs_for_name(domain):
                if canonical_ref not in canonical_domains:
                    canonical_domains.append(canonical_ref)
        return canonical_domains

    @staticmethod
    def _maybe_recompose_for_impasse(
        *,
        primary_mind: str,
        ordered_minds: list[str],
        supporting_minds: list[str],
        supporting_limit: int,
        suppressed_limit: int,
        active_domains: list[str],
        primary_domain_driver: str | None,
        domain_specialist_routes: list[DomainSpecialistRouteContract],
    ) -> tuple[list[str], list[str], str, bool, str | None, str | None]:
        active_routes = [
            route
            for route in domain_specialist_routes
            if route.specialist_mode in {"guided", "active"}
        ]
        if (
            primary_domain_driver is None
            or primary_mind == "mente_critica"
            or not active_routes
            or (len(active_domains) < 2 and len(active_routes) < 2)
        ):
            return supporting_minds, [
                mind
                for mind in ordered_minds
                if mind not in {primary_mind, *supporting_minds}
            ][:suppressed_limit], "mind_registry", False, None, None

        if any(
            primary_domain_driver in (
                list(route.canonical_domain_refs)
                or list(canonical_domain_refs_for_name(route.domain_name))
            )
            for route in active_routes
        ):
            return supporting_minds, [
                mind
                for mind in ordered_minds
                if mind not in {primary_mind, *supporting_minds}
            ][:suppressed_limit], "mind_registry", False, None, None

        recomposed_support = [
            "mente_critica",
            *[mind for mind in supporting_minds if mind != "mente_critica"],
        ]
        deduped_support: list[str] = []
        for mind in recomposed_support:
            if mind == primary_mind or mind in deduped_support:
                continue
            deduped_support.append(mind)
        deduped_support = deduped_support[:supporting_limit]
        recomposed_suppressed = [
            mind
            for mind in ordered_minds
            if mind not in {primary_mind, *deduped_support}
        ][:suppressed_limit]
        return (
            deduped_support,
            recomposed_suppressed,
            "mind_registry_recomposition",
            True,
            "primary domain driver has no matching guided specialist route",
            "specialist_route_impasse",
        )
