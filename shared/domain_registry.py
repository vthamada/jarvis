"""Domain registry derived from the Documento-Mestre canonical domain map."""

from __future__ import annotations

from dataclasses import dataclass, field
from json import loads
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent.parent / "knowledge" / "curated" / "domain_registry.json"


@dataclass(frozen=True)
class DomainEntry:
    """Single entry from the canonical domain map or runtime route registry."""

    domain_name: str
    display_name: str
    domain_scope: str
    activation_stage: str
    maturity: str
    summary: str
    canonical_refs: tuple[str, ...] = field(default_factory=tuple)
    linked_specialist_type: str | None = None
    specialist_mode: str | None = None


def _load_registries(
    path: Path,
) -> tuple[dict[str, DomainEntry], dict[str, DomainEntry]]:
    if not path.exists():
        return {}, {}
    payload = loads(path.read_text(encoding="utf-8"))
    canonical: dict[str, DomainEntry] = {}
    for item in payload.get("canonical_domains", []):
        entry = DomainEntry(
            domain_name=item["domain_name"],
            display_name=item.get("display_name", item["domain_name"]),
            domain_scope=item.get("domain_scope", "primary"),
            activation_stage=item.get("activation_stage", "canonical"),
            maturity=item.get("maturity", "canonical_only"),
            summary=item.get("summary", ""),
            canonical_refs=tuple(item.get("canonical_refs", [])),
            linked_specialist_type=item.get("linked_specialist_type"),
            specialist_mode=item.get("specialist_mode"),
        )
        canonical[entry.domain_name] = entry
    routes: dict[str, DomainEntry] = {}
    for item in payload.get("runtime_routes", []):
        entry = DomainEntry(
            domain_name=item["route_name"],
            display_name=item.get("display_name", item["route_name"]),
            domain_scope=item.get("domain_scope", "runtime_route"),
            activation_stage=item.get("activation_stage", "v2"),
            maturity=item.get("maturity", "active_registry"),
            summary=item.get("summary", ""),
            canonical_refs=tuple(item.get("canonical_refs", [])),
            linked_specialist_type=item.get("linked_specialist_type"),
            specialist_mode=item.get("specialist_mode"),
        )
        routes[entry.domain_name] = entry
    return canonical, routes


def load_domain_registries(
    path: Path | None = None,
) -> tuple[dict[str, DomainEntry], dict[str, DomainEntry]]:
    """Load canonical and runtime registries from the given path or the default."""

    return _load_registries(path or _REGISTRY_PATH)


CANONICAL_DOMAIN_REGISTRY, RUNTIME_ROUTE_REGISTRY = load_domain_registries()

# Short-term compatibility map: runtime route labels remain stable identifiers,
# but canonical domain refs are the only long-term semantic language.
LEGACY_LABEL_TO_CANONICAL_DOMAINS: dict[str, tuple[str, ...]] = {
    name: entry.canonical_refs for name, entry in RUNTIME_ROUTE_REGISTRY.items()
}

# Routes eligible for runtime activation (excludes canonical_only entries).
RUNTIME_ELIGIBLE_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity != "canonical_only"
)

# Routes where a domain-linked specialist is wired into the runtime.
SPECIALIST_ROUTE_MODES: frozenset[str] = frozenset({"shadow", "guided", "active"})
SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.linked_specialist_type and entry.specialist_mode in SPECIALIST_ROUTE_MODES
)

# Shadow specialist routes remain observable for backward-compatible comparisons.
SHADOW_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.specialist_mode == "shadow"
)

# Promoted specialist routes are above shadow mode but still subordinated to the core.
PROMOTED_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.specialist_mode in {"guided", "active"}
)

# Fallback route: last runtime route with maturity == "active_registry".
# By convention, the most general/operational route is listed last in the JSON.
_active_routes = [
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity == "active_registry"
]
FALLBACK_RUNTIME_ROUTE: str = _active_routes[-1] if _active_routes else "productivity"


def is_shadow_route(route_name: str) -> bool:
    """Return True if the route is a shadow specialist route in the registry."""
    return route_name in SHADOW_SPECIALIST_ROUTES


def is_specialist_route(route_name: str) -> bool:
    """Return True if the route has a domain-linked specialist in the registry."""
    return route_name in SPECIALIST_ROUTES


def is_promoted_specialist_route(route_name: str) -> bool:
    """Return True if the route is above shadow mode but still core-subordinated."""
    return route_name in PROMOTED_SPECIALIST_ROUTES


def resolve_route(route_name: str) -> DomainEntry | None:
    """Return the DomainEntry for a runtime route, or None if not found."""
    return RUNTIME_ROUTE_REGISTRY.get(route_name)


def route_routing_source(route_name: str) -> str:
    """Return the source that authorized the current route identifier."""

    return "domain_registry" if route_name in RUNTIME_ROUTE_REGISTRY else "legacy_label_adapter"


def canonical_domain_refs_for_name(domain_name: str) -> tuple[str, ...]:
    """Resolve canonical domain refs for a runtime route or canonical domain name."""

    if domain_name in CANONICAL_DOMAIN_REGISTRY:
        return (domain_name,)
    route_entry = resolve_route(domain_name)
    if route_entry is not None:
        return route_entry.canonical_refs
    return LEGACY_LABEL_TO_CANONICAL_DOMAINS.get(domain_name, ())


def primary_canonical_domain_for_name(domain_name: str) -> str | None:
    """Return the first canonical domain associated with a route or domain name."""

    refs = canonical_domain_refs_for_name(domain_name)
    return refs[0] if refs else None


def canonical_scopes_for_route(route_name: str) -> frozenset[str]:
    """Return the domain_scope values of all canonical_refs for a runtime route."""
    refs = canonical_domain_refs_for_name(route_name)
    if not refs:
        return frozenset()
    scopes: set[str] = set()
    for ref in refs:
        canonical_entry = CANONICAL_DOMAIN_REGISTRY.get(ref)
        if canonical_entry is not None:
            scopes.add(canonical_entry.domain_scope)
    return frozenset(scopes)
