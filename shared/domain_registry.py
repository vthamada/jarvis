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

# Mapa curto de compatibilidade: labels de runtime continuam estaveis,
# mas refs canonicas seguem como linguagem semantica principal do sistema.
LEGACY_LABEL_TO_CANONICAL_DOMAINS: dict[str, tuple[str, ...]] = {
    name: entry.canonical_refs for name, entry in RUNTIME_ROUTE_REGISTRY.items()
}

# Rotas elegiveis para ativacao em runtime (exclui entradas canonical_only).
RUNTIME_ELIGIBLE_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity != "canonical_only"
)

# Rotas em que um especialista ligado ao dominio ja foi conectado ao runtime.
SPECIALIST_ROUTE_MODES: frozenset[str] = frozenset({"shadow", "guided", "active"})
SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.linked_specialist_type and entry.specialist_mode in SPECIALIST_ROUTE_MODES
)

# Rotas em shadow permanecem observaveis para comparacoes e compatibilidade curta.
SHADOW_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.specialist_mode == "shadow"
)

# Rotas promovidas ficam acima de shadow, mas continuam subordinadas ao nucleo.
PROMOTED_SPECIALIST_ROUTES: frozenset[str] = frozenset(
    name
    for name, entry in RUNTIME_ROUTE_REGISTRY.items()
    if entry.specialist_mode in {"guided", "active"}
)

# Rota de fallback: ultima rota de runtime com maturity == "active_registry".
# Por convencao, a rota mais geral/operacional fica por ultimo no JSON.
_active_routes = [
    name for name, entry in RUNTIME_ROUTE_REGISTRY.items() if entry.maturity == "active_registry"
]
FALLBACK_RUNTIME_ROUTE: str = _active_routes[-1] if _active_routes else "productivity"


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
