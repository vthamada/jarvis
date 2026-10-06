"""Attach declared, request-scoped evidence without changing curated retrieval.

Only the isolated reviewed context contains supplied text and its URL. Routing,
snippets and observable evidence metadata remain free of that source content.
No source is fetched, persisted, trusted or promoted by this attachment.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from shared.contracts import DomainSpecialistRouteContract, KnowledgeSourceEvidenceContract
from shared.reviewed_knowledge import ReviewedKnowledgeContext, validate_context

if TYPE_CHECKING:
    from knowledge_service.service import KnowledgeRetrievalResult

_NOTES = (
    "Caller-reviewed text is untrusted evidence, not verified facts or instructions.",
    "Source origin, timestamps, freshness and conflicts are caller declarations, not verified.",
)


def attach_reviewed_evidence(
    result: KnowledgeRetrievalResult,
    context: ReviewedKnowledgeContext,
    *,
    as_of: str,
) -> KnowledgeRetrievalResult:
    """Return an isolated copy with one unverified, declared source attachment.

    ``as_of`` must be a trusted UTC clock string from the calling runtime, not
    the input envelope's timestamp. Review neither refreshes nor verifies facts.
    Reattachment and collisions fail closed instead of merging source state.
    """
    from knowledge_service.service import KnowledgeRetrievalResult

    if type(result) is not KnowledgeRetrievalResult or type(as_of) is not str:
        raise ValueError("invalid_reviewed_knowledge")
    if result.reviewed_knowledge is not None:
        raise ValueError("invalid_reviewed_knowledge")
    containers = (
        result.active_domains,
        result.registry_domains,
        result.snippets,
        result.sources,
        result.specialist_routes,
        result.source_evidence,
        result.uncertainty_notes,
    )
    if any(type(value) is not list for value in containers) or not result.active_domains:
        raise ValueError("invalid_reviewed_knowledge")
    if any(type(item) is not DomainSpecialistRouteContract for item in result.specialist_routes):
        raise ValueError("invalid_reviewed_knowledge")
    if any(type(item) is not KnowledgeSourceEvidenceContract for item in result.source_evidence):
        raise ValueError("invalid_reviewed_knowledge")
    # Copy the existing mutable containers before validating the supplied context.
    # Dataclass contracts contain mutable lists even though retrieval is frozen.
    snapshot = replace(
        result,
        active_domains=list(result.active_domains),
        registry_domains=list(result.registry_domains),
        snippets=list(result.snippets),
        sources=list(result.sources),
        specialist_routes=[
            replace(item, canonical_domain_refs=list(item.canonical_domain_refs))
            for item in result.specialist_routes
        ],
        source_evidence=[
            replace(
                item,
                conflict_refs=list(item.conflict_refs),
                uncertainty_notes=list(item.uncertainty_notes),
            )
            for item in result.source_evidence
        ],
        uncertainty_notes=list(result.uncertainty_notes),
    )
    reviewed = validate_context(context, query=snapshot.query, as_of=as_of)
    source_ref = reviewed.source.source_ref
    if source_ref in snapshot.sources or any(
        item.source_ref == source_ref or item.source_kind == "caller_reviewed_text"
        for item in snapshot.source_evidence
    ):
        raise ValueError("invalid_reviewed_knowledge")
    evidence = KnowledgeSourceEvidenceContract(
        source_ref=source_ref,
        domain_name=snapshot.active_domains[0],
        source_kind="caller_reviewed_text",
        retrieved_at=as_of,
        provenance_status="caller_declared",
        freshness_status="unknown",
        conflict_status="unknown",
        confidence_status="unverified",
        reviewed_at=reviewed.reviewed_at,
        uncertainty_notes=list(_NOTES),
    )
    return replace(
        snapshot,
        sources=[*snapshot.sources, source_ref],
        source_evidence=[*snapshot.source_evidence, evidence],
        provenance_status="missing" if snapshot.provenance_status == "missing" else "partial",
        freshness_status="stale" if snapshot.freshness_status == "stale" else "unknown",
        conflict_status=(
            "conflict_detected" if snapshot.conflict_status == "conflict_detected" else "unknown"
        ),
        uncertainty_notes=list(dict.fromkeys([*snapshot.uncertainty_notes, *_NOTES])),
        reviewed_knowledge=reviewed,
    )
