"""Deterministic local knowledge service aligned to the canonical domain map."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path
from unicodedata import normalize

from shared.contracts import DomainRegistryEntryContract, DomainSpecialistRouteContract
from shared.domain_registry import (
    FALLBACK_RUNTIME_ROUTE,
    DomainEntry,
    canonical_scopes_for_route,
    load_domain_registries,
    route_routing_source,
)


@dataclass(frozen=True)
class KnowledgeDomain:
    """Curated local knowledge entry used by deterministic retrieval."""

    name: str
    keywords: list[str]
    snippets: list[str]
    registry_entry: DomainRegistryEntryContract | None = None


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """Structured retrieval result for planning and analysis flows."""

    intent: str
    query: str
    active_domains: list[str]
    registry_domains: list[str]
    snippets: list[str]
    sources: list[str]
    specialist_routes: list[DomainSpecialistRouteContract]


DEFAULT_CORPUS_PATH = Path.cwd() / "knowledge" / "curated" / "v1_corpus.json"
DEFAULT_DOMAIN_REGISTRY_PATH = Path.cwd() / "knowledge" / "curated" / "domain_registry.json"


class KnowledgeService:
    """Provide deterministic retrieval from a local curated corpus."""

    name = "knowledge-service"
    _DOMAIN_NAME_MATCH_WEIGHT: float = 1.6
    _KEYWORD_MATCH_WEIGHT: float = 1.25
    _REGISTRY_ROUTE_MATCH_WEIGHT: float = 6.0
    _REGISTRY_CANONICAL_MATCH_WEIGHT: float = 5.0

    def __init__(
        self,
        corpus_path: str | None = None,
        domain_registry_path: str | None = None,
    ) -> None:
        resolved_path = Path(corpus_path) if corpus_path else DEFAULT_CORPUS_PATH
        self.corpus_path = resolved_path
        registry_path = (
            Path(domain_registry_path) if domain_registry_path else DEFAULT_DOMAIN_REGISTRY_PATH
        )
        (
            self.canonical_domain_registry,
            self.domain_routes,
        ) = self._load_domain_registry(registry_path)
        self.domains = self._load_domains(resolved_path)

    def retrieve_for_intent(self, *, intent: str, query: str) -> KnowledgeRetrievalResult:
        """Return the most relevant domains and snippets for the given intent."""

        active_domains = self._select_domains(intent, query)
        registry_domains = self._resolve_canonical_domains(active_domains)
        snippets = [
            self.domains[domain].snippets[0] for domain in active_domains if domain in self.domains
        ]
        sources = [
            f"local://knowledge/{domain}" for domain in active_domains if domain in self.domains
        ]
        specialist_routes = self._resolve_specialist_routes(active_domains)
        return KnowledgeRetrievalResult(
            intent=intent,
            query=query,
            active_domains=active_domains,
            registry_domains=registry_domains,
            snippets=snippets,
            sources=sources,
            specialist_routes=specialist_routes,
        )

    def list_domains(self) -> list[str]:
        """Expose the curated runtime domains available to deterministic retrieval."""

        return list(self.domains.keys())

    def list_registry_domains(self) -> list[str]:
        """Expose the canonical registry domains available to the system."""

        return list(self.canonical_domain_registry.keys())

    def list_runtime_route_domains(self) -> list[str]:
        """Expose runtime route labels currently wired into retrieval."""

        return list(self.domain_routes.keys())

    @staticmethod
    def _normalize_text(value: str) -> str:
        folded = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        return folded.lower().replace("_", " ")

    def _select_domains(self, intent: str, query: str) -> list[str]:
        normalized_query = self._normalize_text(query)
        scores: dict[str, float] = {}
        for domain_name, entry in self.domains.items():
            route_entry = self.domain_routes.get(domain_name)
            if route_entry is not None and route_entry.maturity == "canonical_only":
                scores[domain_name] = 0.0
                continue
            score = self._intent_prior(intent, domain_name)
            score += self._registry_declaration_boost(domain_name, normalized_query)
            normalized_domain_name = self._normalize_text(domain_name)
            if normalized_domain_name and normalized_domain_name in normalized_query:
                score += self._DOMAIN_NAME_MATCH_WEIGHT
            score += sum(
                self._KEYWORD_MATCH_WEIGHT
                for keyword in entry.keywords
                if self._normalize_text(keyword) in normalized_query
            )
            scores[domain_name] = score
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        selected = [name for name, score in ranked if score > 0.0]
        return selected[:3] or [FALLBACK_RUNTIME_ROUTE]

    def _registry_declaration_boost(self, route_name: str, normalized_query: str) -> float:
        entry = self.domain_routes.get(route_name)
        if entry is None:
            return 0.0
        boost = 0.0
        route_tokens = {
            self._normalize_text(route_name),
            self._normalize_text(route_name.replace("_", " ")),
            self._normalize_text(entry.display_name),
        }
        if any(token and token in normalized_query for token in route_tokens):
            boost = max(boost, self._REGISTRY_ROUTE_MATCH_WEIGHT)
        for canonical_ref in entry.canonical_refs:
            canonical_entry = self.canonical_domain_registry.get(canonical_ref)
            canonical_tokens = {
                self._normalize_text(canonical_ref),
                self._normalize_text(canonical_ref.replace("_", " ")),
            }
            if canonical_entry is not None:
                canonical_tokens.add(self._normalize_text(canonical_entry.display_name))
            if any(token and token in normalized_query for token in canonical_tokens):
                boost = max(boost, self._REGISTRY_CANONICAL_MATCH_WEIGHT)
        if boost and entry.maturity == "active_specialist":
            boost += 0.4
        elif boost and entry.maturity == "active_registry":
            boost += 0.2
        return boost

    def _intent_prior(self, intent: str, domain_name: str) -> float:
        route_entry = self.domain_routes.get(domain_name)
        if route_entry is None:
            return 0.0
        scopes = canonical_scopes_for_route(domain_name)
        maturity = route_entry.maturity
        if intent == "planning":
            if "operational" in scopes:
                return 1.8
            if "primary" in scopes:
                return 1.4
            return 0.4
        if intent == "analysis":
            if maturity in {"shadow_specialist", "active_specialist"}:
                return 1.7 if maturity == "active_specialist" else 1.6
            if "primary" in scopes:
                return 1.3
            if "operational" in scopes:
                return 0.8
            return 0.5
        return 0.4

    @staticmethod
    def _to_registry_contract(entry: DomainEntry) -> DomainRegistryEntryContract:
        return DomainRegistryEntryContract(
            domain_name=entry.domain_name,
            display_name=entry.display_name,
            domain_scope=entry.domain_scope,
            activation_stage=entry.activation_stage,
            maturity=entry.maturity,
            canonical_refs=list(entry.canonical_refs),
            linked_specialist_type=entry.linked_specialist_type,
            specialist_mode=entry.specialist_mode,
            summary=entry.summary,
        )

    def _load_domain_registry(
        self,
        registry_path: Path,
    ) -> tuple[dict[str, DomainRegistryEntryContract], dict[str, DomainRegistryEntryContract]]:
        canonical_entries, runtime_entries = load_domain_registries(registry_path)
        canonical_domains = {
            name: self._to_registry_contract(entry) for name, entry in canonical_entries.items()
        }
        runtime_routes = {
            name: self._to_registry_contract(entry) for name, entry in runtime_entries.items()
        }
        return canonical_domains, runtime_routes

    def _load_domains(self, corpus_path: Path) -> dict[str, KnowledgeDomain]:
        payload = loads(corpus_path.read_text(encoding="utf-8"))
        return {
            item["name"]: KnowledgeDomain(
                name=item["name"],
                keywords=item.get("keywords", []),
                snippets=item.get("snippets", []),
                registry_entry=self.domain_routes.get(item["name"]),
            )
            for item in payload.get("domains", [])
        }

    def _resolve_canonical_domains(self, active_domains: list[str]) -> list[str]:
        canonical_domains: list[str] = []
        for domain_name in active_domains:
            entry = self.domain_routes.get(domain_name)
            if entry is None:
                continue
            for canonical_ref in entry.canonical_refs:
                if canonical_ref not in canonical_domains:
                    canonical_domains.append(canonical_ref)
        return canonical_domains

    def _resolve_specialist_routes(
        self,
        active_domains: list[str],
    ) -> list[DomainSpecialistRouteContract]:
        routes: list[DomainSpecialistRouteContract] = []
        for domain_name in active_domains:
            entry = self.domain_routes.get(domain_name)
            if not entry or not entry.linked_specialist_type or not entry.specialist_mode:
                continue
            routes.append(
                DomainSpecialistRouteContract(
                    domain_name=domain_name,
                    specialist_type=entry.linked_specialist_type,
                    specialist_mode=entry.specialist_mode,
                    routing_reason=entry.summary
                    or f"rota canonica ativa para o dominio {domain_name}",
                    canonical_domain_refs=list(entry.canonical_refs),
                    routing_source=route_routing_source(domain_name),
                )
            )
        return routes
