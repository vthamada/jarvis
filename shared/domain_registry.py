"""Registry de dominios derivado do mapa canonico do Documento-Mestre."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from re import fullmatch

from shared.contracts import (
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
)
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


@dataclass(frozen=True)
class WorkflowRuntimeGuidance:
    """Route-specific planning and synthesis guidance keyed by workflow profile."""

    planning_focus: str
    success_focus: str
    semantic_memory_role: str
    procedural_memory_role: str
    response_focus: str
    adaptive_intervention_priority: tuple[str, ...] = (
        "memory_review_checkpoint",
        "specialist_reevaluation",
    )


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

ACTIVE_WORKFLOW_MATURITIES = frozenset({"active_registry", "active_specialist"})
ACTIVE_WORKFLOW_REGISTRY_REF = "domain-registry://runtime-routes/current"
WORKFLOW_VERSION_LIFECYCLE_STATUSES = (
    "baseline_snapshot",
    "candidate_inactive",
    "needs_review",
    "sandboxed",
    "eval_passed_pending_release",
    "approved_pending_promotion",
    "rejected",
    "rolled_back",
    "promoted_snapshot",
)

DEFAULT_WORKFLOW_RUNTIME_GUIDANCE = WorkflowRuntimeGuidance(
    planning_focus="progressao governada da rota ativa",
    success_focus="saida governada e auditavel",
    semantic_memory_role="framing do objetivo ativo",
    procedural_memory_role="continuidade segura da proxima acao",
    response_focus="leitura final coerente com o contrato da rota",
    adaptive_intervention_priority=(
        "memory_review_checkpoint",
        "specialist_reevaluation",
    ),
)

WORKFLOW_RUNTIME_GUIDANCE_REGISTRY: dict[str, WorkflowRuntimeGuidance] = {
    "strategic_direction_workflow": WorkflowRuntimeGuidance(
        planning_focus="enquadramento de cenario, trade-offs e direcao recomendada",
        success_focus="direcao recomendada com criterios explicitos",
        semantic_memory_role="framing estrategico e comparacao de trade-offs",
        procedural_memory_role="continuidade do fio decisorio e criterio de progressao",
        response_focus="direcao recomendada, criterios e trade-offs dominantes",
        adaptive_intervention_priority=(
            "specialist_reevaluation",
            "memory_review_checkpoint",
        ),
    ),
    "structured_analysis_workflow": WorkflowRuntimeGuidance(
        planning_focus="enquadramento da pergunta, evidencia e interpretacao recomendada",
        success_focus="achados estruturados com interpretacao recomendada",
        semantic_memory_role="enquadramento analitico e leitura de evidencia",
        procedural_memory_role="continuidade da trilha de analise e recomendacao",
        response_focus="achados estruturados, comparacao e interpretacao recomendada",
        adaptive_intervention_priority=(
            "specialist_reevaluation",
            "memory_review_checkpoint",
        ),
    ),
    "governance_boundary_workflow": WorkflowRuntimeGuidance(
        planning_focus="limites, condicoes e trilha de contencao governada",
        success_focus="caminho governado com condicoes explicitas",
        semantic_memory_role="framing de limites, exposicao e contencao",
        procedural_memory_role="sequenciamento de contencao e validacao",
        response_focus="limites, condicoes e caminho governado",
        adaptive_intervention_priority=(
            "specialist_reevaluation",
            "memory_review_checkpoint",
        ),
    ),
    "software_change_workflow": WorkflowRuntimeGuidance(
        planning_focus="escopo da mudanca, impacto de contrato e direcao de patch",
        success_focus="direcao de patch segura e bounded",
        semantic_memory_role="framing de impacto contratual e seguranca da mudanca",
        procedural_memory_role="sequenciamento do patch e checkpoints de implementacao",
        response_focus="impacto, risco de implementacao e direcao de patch",
        adaptive_intervention_priority=(
            "specialist_reevaluation",
            "memory_review_checkpoint",
        ),
    ),
    "operational_readiness_workflow": WorkflowRuntimeGuidance(
        planning_focus="checkpoints, dependencias e proxima acao operacional",
        success_focus="proxima acao operacional com readiness explicito",
        semantic_memory_role="framing de readiness e cobertura de checkpoints",
        procedural_memory_role="sequenciamento da proxima acao e continuidade operacional",
        response_focus="readiness, lacunas e proxima acao operacional",
        adaptive_intervention_priority=(
            "memory_review_checkpoint",
            "specialist_reevaluation",
        ),
    ),
    "decision_risk_workflow": WorkflowRuntimeGuidance(
        planning_focus="gate de decisao, reversibilidade e incerteza governada",
        success_focus="gate seguro para progressao",
        semantic_memory_role="framing de risco, impacto e reversibilidade",
        procedural_memory_role="sequenciamento do gate e da progressao segura",
        response_focus="risco, reversibilidade e gate seguro",
        adaptive_intervention_priority=(
            "specialist_reevaluation",
            "memory_review_checkpoint",
        ),
    ),
}


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


def workflow_runtime_guidance(workflow_profile: str | None) -> WorkflowRuntimeGuidance:
    """Return the sovereign guidance attached to a workflow profile."""

    if workflow_profile is None:
        return DEFAULT_WORKFLOW_RUNTIME_GUIDANCE
    return WORKFLOW_RUNTIME_GUIDANCE_REGISTRY.get(
        workflow_profile,
        DEFAULT_WORKFLOW_RUNTIME_GUIDANCE,
    )


def workflow_definition_hash(
    *,
    workflow_steps: list[str] | tuple[str, ...],
    workflow_checkpoints: list[str] | tuple[str, ...],
    workflow_decision_points: list[str] | tuple[str, ...],
    success_criteria: list[str] | tuple[str, ...],
) -> str:
    """Return a stable hash for a complete workflow behavior definition."""

    payload = {
        "workflow_steps": list(workflow_steps),
        "workflow_checkpoints": list(workflow_checkpoints),
        "workflow_decision_points": list(workflow_decision_points),
        "success_criteria": list(success_criteria),
    }
    encoded = dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _numeric_semver(value: str) -> tuple[int, int, int]:
    if fullmatch(r"\d+\.\d+\.\d+", value) is None:
        raise ValueError("workflow version must use numeric semver")
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def active_workflow_registry_fingerprint() -> str:
    """Fingerprint the active authority without creating a writable copy of it."""

    definitions = []
    for route_name, entry in sorted(RUNTIME_ROUTE_REGISTRY.items()):
        if entry.maturity not in ACTIVE_WORKFLOW_MATURITIES or not entry.workflow_profile:
            continue
        guidance = workflow_runtime_guidance(entry.workflow_profile)
        definitions.append(
            {
                "route": route_name,
                "workflow_profile": entry.workflow_profile,
                "definition_hash": workflow_definition_hash(
                    workflow_steps=entry.workflow_steps,
                    workflow_checkpoints=entry.workflow_checkpoints,
                    workflow_decision_points=entry.workflow_decision_points,
                    success_criteria=[
                        *entry.expected_deliverables,
                        guidance.success_focus,
                    ],
                ),
            }
        )
    encoded = dumps(
        definitions,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_active_workflow_version_registry(
    *,
    registry_version: str,
    generated_at: str,
    evidence_refs: list[str] | None = None,
    rollback_plan_ref: str = "rollback://domain-registry/runtime-routes/current",
) -> WorkflowProfileVersionRegistryContract:
    """Snapshot active workflow definitions beside, never into, the live registry."""

    _numeric_semver(registry_version)
    if not rollback_plan_ref:
        raise ValueError("workflow registry snapshot requires rollback evidence")
    fingerprint = active_workflow_registry_fingerprint()
    base_evidence = list(
        dict.fromkeys(
            [
                ACTIVE_WORKFLOW_REGISTRY_REF,
                f"domain-registry-fingerprint://{fingerprint}",
                *(evidence_refs or []),
            ]
        )
    )
    versions: list[WorkflowProfileVersionContract] = []
    seen_profiles: set[str] = set()
    for route_name, entry in sorted(RUNTIME_ROUTE_REGISTRY.items()):
        if entry.maturity not in ACTIVE_WORKFLOW_MATURITIES or not entry.workflow_profile:
            continue
        if entry.workflow_profile in seen_profiles:
            raise ValueError("active workflow profiles must map to one route")
        seen_profiles.add(entry.workflow_profile)
        guidance = workflow_runtime_guidance(entry.workflow_profile)
        success_criteria = list(
            dict.fromkeys([*entry.expected_deliverables, guidance.success_focus])
        )
        versions.append(
            WorkflowProfileVersionContract(
                workflow_version_id=(
                    f"workflow-version://{entry.workflow_profile}/{registry_version}"
                ),
                workflow_profile=entry.workflow_profile,
                version=registry_version,
                route=route_name,
                lifecycle_status="baseline_snapshot",
                definition_hash=workflow_definition_hash(
                    workflow_steps=entry.workflow_steps,
                    workflow_checkpoints=entry.workflow_checkpoints,
                    workflow_decision_points=entry.workflow_decision_points,
                    success_criteria=success_criteria,
                ),
                workflow_steps=list(entry.workflow_steps),
                workflow_checkpoints=list(entry.workflow_checkpoints),
                workflow_decision_points=list(entry.workflow_decision_points),
                success_criteria=success_criteria,
                evidence_refs=list(
                    dict.fromkeys(
                        [
                            *base_evidence,
                            f"domain-registry-route://{route_name}",
                            f"workflow-guidance://{entry.workflow_profile}",
                        ]
                    )
                ),
                proposed_tests=["tests/unit/test_domain_registry_workflows.py"],
                rollback_plan_ref=rollback_plan_ref,
                source_registry_ref=ACTIVE_WORKFLOW_REGISTRY_REF,
                source_registry_fingerprint=fingerprint,
                timestamp=generated_at,
                change_summary="snapshot of the active sovereign workflow definition",
                risk_level="low",
                review_status="not_applicable",
                runtime_binding_status="observed_active_baseline",
                human_review_required=False,
                sandbox_required=False,
            )
        )
    blockers = [] if versions else ["no_active_workflow_definitions"]
    return WorkflowProfileVersionRegistryContract(
        registry_id=(
            f"workflow-version-registry://active/{fingerprint[:16]}/{registry_version}"
        ),
        registry_version=registry_version,
        registry_status=(
            "baseline_snapshot_ready" if versions else "attention_required"
        ),
        active_registry_ref=ACTIVE_WORKFLOW_REGISTRY_REF,
        active_registry_fingerprint=fingerprint,
        workflow_count=len(versions),
        baseline_count=len(versions),
        candidate_count=0,
        versions=versions,
        evidence_refs=base_evidence,
        blockers=blockers,
        generated_at=generated_at,
    )


def register_workflow_candidate_version(
    registry: WorkflowProfileVersionRegistryContract,
    candidate: WorkflowProfileVersionContract,
) -> WorkflowProfileVersionRegistryContract:
    """Return a new side-registry snapshot with one inactive workflow candidate."""

    if registry.active_registry_mutation_allowed:
        raise ValueError("workflow version registry cannot mutate the active registry")
    if registry.active_registry_fingerprint != active_workflow_registry_fingerprint():
        raise ValueError("active workflow registry drift requires a fresh snapshot")
    if candidate.lifecycle_status != "candidate_inactive":
        raise ValueError("workflow candidate must remain candidate_inactive")
    expected_version_id = (
        f"workflow-version://{candidate.workflow_profile}/{candidate.version}"
    )
    if candidate.workflow_version_id != expected_version_id:
        raise ValueError("workflow candidate identity must match profile and version")
    if candidate.runtime_binding_status != "inactive_candidate":
        raise ValueError("workflow candidate cannot claim an active runtime binding")
    if candidate.review_status != "needs_review" or not candidate.human_review_required:
        raise ValueError("workflow candidate requires explicit human review")
    if not candidate.sandbox_required:
        raise ValueError("workflow candidate requires sandbox evaluation")
    if (
        candidate.active_registry_write_allowed
        or candidate.runtime_activation_allowed
        or candidate.automatic_promotion_allowed
        or candidate.core_mutation_allowed
    ):
        raise ValueError("workflow candidate cannot claim runtime or mutation authority")
    candidate_semver = _numeric_semver(candidate.version)
    if candidate.source_registry_ref != registry.active_registry_ref:
        raise ValueError("workflow candidate source registry mismatch")
    if candidate.source_registry_fingerprint != registry.active_registry_fingerprint:
        raise ValueError("workflow candidate source fingerprint mismatch")
    baselines = [
        version
        for version in registry.versions
        if version.workflow_profile == candidate.workflow_profile
        and version.lifecycle_status == "baseline_snapshot"
    ]
    if len(baselines) != 1:
        raise ValueError("workflow candidate requires one baseline version")
    baseline = baselines[0]
    if candidate.route != baseline.route:
        raise ValueError("workflow candidate route must match its baseline")
    if candidate.baseline_version_ref != baseline.workflow_version_id:
        raise ValueError("workflow candidate baseline ref mismatch")
    if candidate_semver <= _numeric_semver(baseline.version):
        raise ValueError("workflow candidate version must advance its baseline")
    expected_hash = workflow_definition_hash(
        workflow_steps=candidate.workflow_steps,
        workflow_checkpoints=candidate.workflow_checkpoints,
        workflow_decision_points=candidate.workflow_decision_points,
        success_criteria=candidate.success_criteria,
    )
    if candidate.definition_hash != expected_hash:
        raise ValueError("workflow candidate definition hash mismatch")
    if candidate.definition_hash == baseline.definition_hash:
        raise ValueError("workflow candidate must change the baseline definition")
    for field_name, values in (
        ("workflow_steps", candidate.workflow_steps),
        ("workflow_checkpoints", candidate.workflow_checkpoints),
        ("workflow_decision_points", candidate.workflow_decision_points),
        ("success_criteria", candidate.success_criteria),
        ("evidence_refs", candidate.evidence_refs),
        ("proposed_tests", candidate.proposed_tests),
    ):
        if not values or len(values) > 50 or any(len(value) > 500 for value in values):
            raise ValueError(f"{field_name} must be present and bounded")
    if (
        not candidate.rollback_plan_ref
        or len(candidate.rollback_plan_ref) > 500
        or not candidate.change_summary
        or len(candidate.change_summary) > 500
        or not candidate.timestamp
        or len(candidate.timestamp) > 100
    ):
        raise ValueError("workflow candidate requires change summary and rollback")
    if candidate.blockers:
        raise ValueError("blocked workflow candidate cannot enter the version registry")
    if candidate.risk_level not in {"low", "moderate"}:
        raise ValueError("workflow candidate risk exceeds registry baseline")
    for existing in registry.versions:
        if existing.workflow_version_id == candidate.workflow_version_id:
            if existing == candidate:
                return registry
            raise ValueError("workflow version identifiers are immutable")
        if (
            existing.workflow_profile == candidate.workflow_profile
            and existing.version == candidate.version
        ):
            raise ValueError("workflow profile and version already exist")

    safe_candidate = replace(
        candidate,
        lifecycle_status="candidate_inactive",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
        active_registry_write_allowed=False,
        runtime_activation_allowed=False,
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
    )
    registry_seed = f"{registry.registry_id}:{candidate.workflow_version_id}"
    registry_hash = sha256(registry_seed.encode("utf-8")).hexdigest()[:16]
    return replace(
        registry,
        registry_id=f"workflow-version-registry://candidate/{registry_hash}",
        registry_status="candidate_registered_inactive",
        workflow_count=registry.workflow_count,
        candidate_count=registry.candidate_count + 1,
        versions=[*registry.versions, safe_candidate],
        evidence_refs=list(
            dict.fromkeys([*registry.evidence_refs, *candidate.evidence_refs])
        ),
        generated_at=candidate.timestamp,
        read_only=True,
        human_review_required=True,
        active_registry_mutation_allowed=False,
        runtime_activation_allowed=False,
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
    )


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
        "workflow_steps": list(entry.workflow_steps) if entry is not None else [],
        "workflow_checkpoints": list(entry.workflow_checkpoints) if entry is not None else [],
        "workflow_decision_points": (
            list(entry.workflow_decision_points) if entry is not None else []
        ),
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
