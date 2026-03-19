"""Deterministic local knowledge service for the v1 core."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeDomain:
    """Curated local knowledge entry used by deterministic retrieval."""

    name: str
    keywords: list[str]
    snippets: list[str]


@dataclass(frozen=True)
class KnowledgeRetrievalResult:
    """Structured retrieval result for planning and analysis flows."""

    intent: str
    query: str
    active_domains: list[str]
    snippets: list[str]
    sources: list[str]


DEFAULT_CORPUS_PATH = Path.cwd() / "knowledge" / "curated" / "v1_corpus.json"


class KnowledgeService:
    """Provide deterministic retrieval from a local curated corpus."""

    name = "knowledge-service"

    def __init__(self, corpus_path: str | None = None) -> None:
        resolved_path = Path(corpus_path) if corpus_path else DEFAULT_CORPUS_PATH
        self.corpus_path = resolved_path
        self.domains = self._load_domains(resolved_path)

    def retrieve_for_intent(self, *, intent: str, query: str) -> KnowledgeRetrievalResult:
        """Return the most relevant domains and snippets for the given intent."""

        active_domains = self._select_domains(intent, query)
        snippets = [self.domains[domain].snippets[0] for domain in active_domains]
        sources = [f"local://knowledge/{domain}" for domain in active_domains]
        return KnowledgeRetrievalResult(
            intent=intent,
            query=query,
            active_domains=active_domains,
            snippets=snippets,
            sources=sources,
        )

    def list_domains(self) -> list[str]:
        """Expose the curated domains available to deterministic retrieval."""

        return list(self.domains.keys())

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
            priorities = {"strategy": 2.0, "productivity": 1.0}
        elif intent == "analysis":
            priorities = {"analysis": 2.0, "strategy": 1.5}
        else:
            priorities = {"productivity": 0.5}
        return priorities.get(domain_name, 0.0)

    @staticmethod
    def _load_domains(corpus_path: Path) -> dict[str, KnowledgeDomain]:
        payload = loads(corpus_path.read_text(encoding="utf-8"))
        return {
            item["name"]: KnowledgeDomain(
                name=item["name"],
                keywords=item.get("keywords", []),
                snippets=item.get("snippets", []),
            )
            for item in payload.get("domains", [])
        }

