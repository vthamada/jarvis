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
        domains: list[str] = []
        if intent == "planning":
            domains.extend(["strategy", "productivity"])
        elif intent == "analysis":
            domains.extend(["analysis", "strategy"])
        else:
            domains.append("productivity")
        for entry in self.domains.values():
            if any(token in lowered for token in entry.keywords):
                domains.append(entry.name)
        return list(dict.fromkeys(domains))

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
