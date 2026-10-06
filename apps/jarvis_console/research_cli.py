"""Console adapter for the pure offline research review builder."""

from __future__ import annotations


def build_research_dossier(document: dict, *, include_content: bool = False) -> dict:
    # The console bootstraps package paths; the adapter does not instantiate Core.
    from knowledge_service.research import build_offline_research_dossier

    return build_offline_research_dossier(document, include_content=include_content)
