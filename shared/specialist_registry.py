"""Canonical specialist identifiers and compatibility helpers."""

from __future__ import annotations

OPERATIONAL_PLANNING_SPECIALIST = "operational_planning_specialist"
STRUCTURED_ANALYSIS_SPECIALIST = "structured_analysis_specialist"
GOVERNANCE_REVIEW_SPECIALIST = "governance_review_specialist"
SOFTWARE_CHANGE_SPECIALIST = "software_change_specialist"

CANONICAL_SPECIALIST_TYPES: tuple[str, ...] = (
    OPERATIONAL_PLANNING_SPECIALIST,
    STRUCTURED_ANALYSIS_SPECIALIST,
    GOVERNANCE_REVIEW_SPECIALIST,
    SOFTWARE_CHANGE_SPECIALIST,
)

LEGACY_TO_CANONICAL_SPECIALIST_TYPE: dict[str, str] = {
    "especialista_planejamento_operacional": OPERATIONAL_PLANNING_SPECIALIST,
    "especialista_analise_estruturada": STRUCTURED_ANALYSIS_SPECIALIST,
    "especialista_revisao_governanca": GOVERNANCE_REVIEW_SPECIALIST,
    "especialista_software_subordinado": SOFTWARE_CHANGE_SPECIALIST,
}

CANONICAL_TO_LEGACY_SPECIALIST_TYPE: dict[str, str] = {
    canonical: legacy for legacy, canonical in LEGACY_TO_CANONICAL_SPECIALIST_TYPE.items()
}


def canonical_specialist_type(specialist_type: str) -> str:
    """Return the canonical runtime identifier for a specialist type."""

    return LEGACY_TO_CANONICAL_SPECIALIST_TYPE.get(specialist_type, specialist_type)



def legacy_specialist_type(specialist_type: str) -> str:
    """Return the legacy label when available for compatibility text/history."""

    return CANONICAL_TO_LEGACY_SPECIALIST_TYPE.get(specialist_type, specialist_type)



def normalize_specialist_types(items: list[str]) -> list[str]:
    """Normalize a list of specialist ids without duplicating aliases."""

    normalized: list[str] = []
    for item in items:
        canonical = canonical_specialist_type(item)
        if canonical not in normalized:
            normalized.append(canonical)
    return normalized
