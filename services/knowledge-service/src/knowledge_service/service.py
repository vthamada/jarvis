"""Deterministic local knowledge service aligned to the canonical domain map."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path

from shared.contracts import DomainRegistryEntryContract, DomainSpecialistRouteContract


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

    def __init__(
        self,
        corpus_path: str | None = None,
        domain_registry_path: str | None = None,
    ) -> None:
        resolved_path = Path(corpus_path) if corpus_path else DEFAULT_CORPUS_PATH
        self.corpus_path = resolved_path
        registry_path = (
            Path(domain_registry_path)
            if domain_registry_path
            else DEFAULT_DOMAIN_REGISTRY_PATH
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
        snippets = [self.domains[domain].snippets[0] for domain in active_domains]
        sources = [f"local://knowledge/{domain}" for domain in active_domains]
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

    def _select_domains(self, intent: str, query: str) -> list[str]:
        lowered = query.lower()
        scores: dict[str, float] = {}
        for domain_name, entry in self.domains.items():
            score = self._intent_prior(intent, domain_name)
            if domain_name in lowered:
                score += 1.6
            score += sum(1.25 for keyword in entry.keywords if keyword in lowered)
            if "audit" in lowered and domain_name == "governance":
                score += 1.5
            scores[domain_name] = score
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        selected = [name for name, score in ranked if score > 0.0]
        return selected[:3] or ["productivity"]

    @staticmethod
    def _intent_prior(intent: str, domain_name: str) -> float:
        if intent == "planning":
            priorities = {
                "strategy": 2.0,
                "productivity": 1.3,
                "documentation": 0.9,
                "pilot_operations": 0.8,
                "operational_readiness": 0.7,
            }
        elif intent == "analysis":
            priorities = {
                "analysis": 2.0,
                "strategy": 1.5,
                "decision_risk": 1.2,
                "governance": 1.0,
                "observability": 0.9,
                "operational_readiness": 0.8,
                "pilot_operations": 0.7,
            }
        else:
            priorities = {
                "productivity": 0.5,
                "documentation": 0.4,
                "pilot_operations": 0.35,
            }
        return priorities.get(domain_name, 0.0)

    @staticmethod
    def _load_domain_registry(
        registry_path: Path,
    ) -> tuple[dict[str, DomainRegistryEntryContract], dict[str, DomainRegistryEntryContract]]:
        if not registry_path.exists():
            return {}, {}
        payload = loads(registry_path.read_text(encoding="utf-8"))
        canonical_domains = {
            item["domain_name"]: DomainRegistryEntryContract(
                domain_name=item["domain_name"],
                display_name=item.get("display_name"),
                domain_scope=item.get("domain_scope"),
                activation_stage=item.get("activation_stage", "canonical"),
                maturity=item.get("maturity", "canonical"),
                canonical_family=item.get("canonical_family"),
                canonical_refs=list(item.get("canonical_refs", [])),
                linked_specialist_type=item.get("linked_specialist_type"),
                specialist_mode=item.get("specialist_mode"),
                summary=item.get("summary"),
            )
            for item in payload.get("canonical_domains", [])
        }
        runtime_routes = {
            item["route_name"]: DomainRegistryEntryContract(
                domain_name=item["route_name"],
                display_name=item.get("display_name"),
                domain_scope=item.get("domain_scope", "runtime_route"),
                activation_stage=item["activation_stage"],
                maturity=item["maturity"],
                canonical_family=item.get("canonical_family"),
                canonical_refs=list(item.get("canonical_refs", [])),
                linked_specialist_type=item.get("linked_specialist_type"),
                specialist_mode=item.get("specialist_mode"),
                summary=item.get("summary"),
            )
            for item in payload.get("runtime_routes", [])
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
            entry = self.domains[domain_name].registry_entry
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
            entry = self.domains[domain_name].registry_entry
            if not entry or not entry.linked_specialist_type or not entry.specialist_mode:
                continue
            routes.append(
                DomainSpecialistRouteContract(
                    domain_name=domain_name,
                    specialist_type=entry.linked_specialist_type,
                    specialist_mode=entry.specialist_mode,
                    routing_reason=entry.summary
                    or f"rota canônica ativa para o domínio {domain_name}",
                    canonical_domain_refs=list(entry.canonical_refs),
                )
            )
        return routes
