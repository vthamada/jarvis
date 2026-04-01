"""Registry de dominios derivado do mapa canonico do Documento-Mestre."""

from __future__ import annotations

from dataclasses import dataclass, field
from json import loads
from pathlib import Path

from shared.specialist_registry import canonical_specialist_type

_REGISTRY_PATH = Path(__file__).parent.parent / "knowledge" / "curated" / "domain_registry.json"


@dataclass(frozen=True)
class DomainEntry:
    """Entrada unica do mapa canonico ou do registry de rotas de runtime."""

    domain_name: str
    display_name: str
    domain_scope: str
    activation_stage: str
    maturity: str
    summary: str
    canonical_refs: tuple[str, ...] = field(default_factory=tuple)
    linked_specialist_type: str | None = None
    specialist_mode: str | None = None
    consumer_profile: str | None = None
    consumer_objective: str | None = None
    expected_deliverables: tuple[str, ...] = field(default_factory=tuple)
    telemetry_focus: tuple[str, ...] = field(default_factory=tuple)
    workflow_profile: str | None = None
    workflow_steps: tuple[str, ...] = field(default_factory=tuple)
    workflow_checkpoints: tuple[str, ...] = field(default_factory=tuple)
    workflow_decision_points: tuple[str, ...] = field(default_factory=tuple)


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
            linked_specialist_type=(
                canonical_specialist_type(item["linked_specialist_type"])
                if item.get("linked_specialist_type")
                else None
            ),
            specialist_mode=item.get("specialist_mode"),
            consumer_profile=item.get("consumer_profile"),
            consumer_objective=item.get("consumer_objective"),
            expected_deliverables=tuple(item.get("expected_deliverables", [])),
            telemetry_focus=tuple(item.get("telemetry_focus", [])),
            workflow_profile=item.get("workflow_profile"),
            workflow_steps=tuple(item.get("workflow_steps", [])),
            workflow_checkpoints=tuple(item.get("workflow_checkpoints", [])),
            workflow_decision_points=tuple(item.get("workflow_decision_points", [])),
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
            linked_specialist_type=(
                canonical_specialist_type(item["linked_specialist_type"])
                if item.get("linked_specialist_type")
                else None
            ),
            specialist_mode=item.get("specialist_mode"),
            consumer_profile=item.get("consumer_profile"),
            consumer_objective=item.get("consumer_objective"),
            expected_deliverables=tuple(item.get("expected_deliverables", [])),
            telemetry_focus=tuple(item.get("telemetry_focus", [])),
            workflow_profile=item.get("workflow_profile"),
            workflow_steps=tuple(item.get("workflow_steps", [])),
            workflow_checkpoints=tuple(item.get("workflow_checkpoints", [])),
            workflow_decision_points=tuple(item.get("workflow_decision_points", [])),
        )
        routes[entry.domain_name] = entry
    return canonical, routes


def load_domain_registries(
    path: Path | None = None,
) -> tuple[dict[str, DomainEntry], dict[str, DomainEntry]]:
    """Load canonical and runtime registries from the given path or the default."""

    return _load_registries(path or _REGISTRY_PATH)


CANONICAL_DOMAIN_REGISTRY, RUNTIME_ROUTE_REGISTRY = load_domain_registries()

LEGACY_LABEL_TO_CANONICAL_DOMAINS: dict[str, tuple[str, ...]] = {
    name: entry.canonical_refs for name, entry in RUNTIME_ROUTE_REGISTRY.items()
}

RUNTIME_ELIGIBLE_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity != "canonical_only"
)

SPECIALIST_ROUTE_MODES: frozenset[str] = frozenset({"shadow", "guided", "active"})
SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.linked_specialist_type and entry.specialist_mode in SPECIALIST_ROUTE_MODES
)
SHADOW_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.specialist_mode == "shadow"
)
PROMOTED_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.specialist_mode in {"guided", "active"}
)
_ACTIVE_ROUTES = [
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity == "active_registry"
]
FALLBACK_RUNTIME_ROUTE: str = _ACTIVE_ROUTES[-1] if _ACTIVE_ROUTES else "productivity"


def is_shadow_route(route_name: str) -> bool:
    """Retorna True se a rota estiver em modo shadow no registry."""

    return route_name in SHADOW_SPECIALIST_ROUTES


def is_specialist_route(route_name: str) -> bool:
    """Retorna True se a rota tiver especialista ligado ao dominio no registry."""

    return route_name in SPECIALIST_ROUTES


def is_promoted_specialist_route(route_name: str) -> bool:
    """Retorna True se a rota estiver acima de shadow, mas ainda subordinada ao nucleo."""

    return route_name in PROMOTED_SPECIALIST_ROUTES


def resolve_route(route_name: str) -> DomainEntry | None:
    """Retorna a DomainEntry de uma rota de runtime, ou None se nao existir."""

    return RUNTIME_ROUTE_REGISTRY.get(route_name)


def resolve_primary_route(
    route_names: list[str] | tuple[str, ...],
) -> tuple[str, DomainEntry] | None:
    """Return the first runtime route present in the ordered route list."""

    for route_name in route_names:
        entry = resolve_route(route_name)
        if entry is not None:
            return route_name, entry
    fallback_entry = resolve_route(FALLBACK_RUNTIME_ROUTE)
    if fallback_entry is None:
        return None
    return FALLBACK_RUNTIME_ROUTE, fallback_entry


def resolve_workflow_route(
    route_names: list[str] | tuple[str, ...],
) -> tuple[str, DomainEntry] | None:
    """Return the first active route with an explicit workflow definition."""

    for route_name in route_names:
        entry = resolve_route(route_name)
        if entry is not None and entry.workflow_profile:
            return route_name, entry
    return None


def route_routing_source(route_name: str) -> str:
    """Retorna a origem que autorizou o identificador atual da rota."""

    return "domain_registry" if route_name in RUNTIME_ROUTE_REGISTRY else "legacy_label_adapter"


def canonical_domain_refs_for_name(domain_name: str) -> tuple[str, ...]:
    """Resolve refs canonicas para uma rota de runtime ou nome de dominio canonico."""

    if domain_name in CANONICAL_DOMAIN_REGISTRY:
        return (domain_name,)
    route_entry = resolve_route(domain_name)
    if route_entry is not None:
        return route_entry.canonical_refs
    return LEGACY_LABEL_TO_CANONICAL_DOMAINS.get(domain_name, ())


def primary_canonical_domain_for_name(domain_name: str) -> str | None:
    """Retorna o primeiro dominio canonico associado a uma rota ou nome de dominio."""

    refs = canonical_domain_refs_for_name(domain_name)
    return refs[0] if refs else None


def canonical_scopes_for_route(route_name: str) -> frozenset[str]:
    """Retorna os valores de domain_scope das canonical_refs de uma rota."""

    refs = canonical_domain_refs_for_name(route_name)
    if not refs:
        return frozenset()
    scopes: set[str] = set()
    for ref in refs:
        canonical_entry = CANONICAL_DOMAIN_REGISTRY.get(ref)
        if canonical_entry is not None:
            scopes.add(canonical_entry.domain_scope)
    return frozenset(scopes)


def route_maturity(route_name: str) -> str | None:
    entry = resolve_route(route_name)
    return entry.maturity if entry is not None else None


def route_linked_specialist_type(route_name: str) -> str | None:
    entry = resolve_route(route_name)
    return entry.linked_specialist_type if entry is not None else None


def route_specialist_mode(route_name: str) -> str | None:
    entry = resolve_route(route_name)
    return entry.specialist_mode if entry is not None else None


def route_consumer_profile(route_name: str) -> str | None:
    entry = resolve_route(route_name)
    return entry.consumer_profile if entry is not None else None


def route_workflow_profile(route_name: str) -> str | None:
    entry = resolve_route(route_name)
    return entry.workflow_profile if entry is not None else None


def route_metadata_payload(route_name: str) -> dict[str, object]:
    """Serialize stable runtime-route metadata used across the runtime."""

    entry = resolve_route(route_name)
    if entry is None:
        return {
            "route_name": route_name,
            "maturity": None,
            "linked_specialist_type": None,
            "specialist_mode": None,
            "consumer_profile": None,
            "consumer_objective": None,
            "expected_deliverables": [],
            "telemetry_focus": [],
            "workflow_profile": None,
            "workflow_steps": [],
            "workflow_checkpoints": [],
            "workflow_decision_points": [],
            "canonical_domain_refs": [],
            "is_promoted_specialist_route": False,
        }
    return {
        "route_name": route_name,
        "maturity": entry.maturity,
        "linked_specialist_type": entry.linked_specialist_type,
        "specialist_mode": entry.specialist_mode,
        "consumer_profile": entry.consumer_profile,
        "consumer_objective": entry.consumer_objective,
        "expected_deliverables": list(entry.expected_deliverables),
        "telemetry_focus": list(entry.telemetry_focus),
        "workflow_profile": entry.workflow_profile,
        "workflow_steps": list(entry.workflow_steps),
        "workflow_checkpoints": list(entry.workflow_checkpoints),
        "workflow_decision_points": list(entry.workflow_decision_points),
        "canonical_domain_refs": list(entry.canonical_refs),
        "is_promoted_specialist_route": is_promoted_specialist_route(route_name),
    }


def primary_route_payload(
    route_names: list[str] | tuple[str, ...],
) -> tuple[str, dict[str, object]] | None:
    """Return the first runtime route payload for the ordered active route list."""

    primary_route = resolve_primary_route(route_names)
    if primary_route is None:
        return None
    route_name, entry = primary_route
    payload = route_metadata_payload(route_name)
    if entry.linked_specialist_type is not None:
        payload = specialist_route_payload(route_name, entry.linked_specialist_type)
    return route_name, payload


def specialist_route_payload(
    route_name: str,
    specialist_type: str | None = None,
) -> dict[str, object]:
    """Return stable route-specialist governance metadata for runtime checks."""

    entry = resolve_route(route_name)
    canonical_type = (
        canonical_specialist_type(specialist_type) if specialist_type is not None else None
    )
    linked_specialist = entry.linked_specialist_type if entry is not None else None
    specialist_mode = entry.specialist_mode if entry is not None else None
    return {
        "route_name": route_name,
        "maturity": entry.maturity if entry is not None else None,
        "canonical_domain_refs": list(entry.canonical_refs) if entry is not None else [],
        "linked_specialist_type": linked_specialist,
        "specialist_mode": specialist_mode,
        "consumer_profile": entry.consumer_profile if entry is not None else None,
        "consumer_objective": entry.consumer_objective if entry is not None else None,
        "expected_deliverables": list(entry.expected_deliverables) if entry is not None else [],
        "telemetry_focus": list(entry.telemetry_focus) if entry is not None else [],
        "workflow_profile": entry.workflow_profile if entry is not None else None,
        "is_promoted": bool(entry is not None and is_promoted_specialist_route(route_name)),
        "eligible": route_is_specialist_eligible(route_name, canonical_type),
        "link_matches": (
            linked_specialist == canonical_type
            if canonical_type is not None
            else linked_specialist is not None
        ),
        "mode_is_governed": specialist_mode in {"guided", "active"},
    }


def promoted_specialist_route_payloads(
    route_names: list[str] | tuple[str, ...],
) -> dict[str, dict[str, object]]:
    """Return the sovereign promoted specialist registry slice for the given active routes."""

    payloads: dict[str, dict[str, object]] = {}
    for route_name in route_names:
        entry = resolve_route(route_name)
        if entry is None or not is_promoted_specialist_route(route_name):
            continue
        payloads[route_name] = specialist_route_payload(
            route_name,
            entry.linked_specialist_type,
        )
    return payloads


def route_is_specialist_eligible(route_name: str, specialist_type: str | None = None) -> bool:
    """Return whether a route is promoted and eligible for governed specialist use."""

    entry = resolve_route(route_name)
    if entry is None or not is_promoted_specialist_route(route_name):
        return False
    if specialist_type is None:
        return entry.linked_specialist_type is not None
    return entry.linked_specialist_type == canonical_specialist_type(specialist_type)


def specialist_eligible_route(
    route_names: list[str] | tuple[str, ...],
    specialist_type: str,
) -> tuple[str, DomainEntry] | None:
    """Return the first route whose promoted specialist link matches the given specialist."""

    canonical_type = canonical_specialist_type(specialist_type)
    for route_name in route_names:
        entry = resolve_route(route_name)
        if entry is None:
            continue
        if not route_is_specialist_eligible(route_name, canonical_type):
            continue
        return route_name, entry
    return None
