"""Memory registry derived from the Documento-Mestre."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from shared.types import MemoryClass


@dataclass(frozen=True)
class MemoryPolicy:
    memory_class: MemoryClass
    display_name: str
    stability: str
    sensitivity: str
    runtime_status: str
    retrieval_default: bool = False
    specialist_shared: bool = False
    domain_linked: bool = False
    retrieval_priority: int = 0
    sharing_priority: int = 0
    sharing_mode: str | None = None
    write_policy: str | None = None


@dataclass(frozen=True)
class WorkflowMemoryPolicy:
    workflow_profile: str | None
    reasoning_semantic_enabled: bool = True
    reasoning_procedural_enabled: bool = True
    specialist_semantic_enabled: bool = True
    specialist_procedural_enabled: bool = True


DEFAULT_WORKFLOW_MEMORY_POLICY = WorkflowMemoryPolicy(workflow_profile=None)

WORKFLOW_MEMORY_POLICIES: dict[str, WorkflowMemoryPolicy] = {
    "strategic_direction_workflow": WorkflowMemoryPolicy(
        workflow_profile="strategic_direction_workflow",
        specialist_procedural_enabled=False,
    ),
    "structured_analysis_workflow": WorkflowMemoryPolicy(
        workflow_profile="structured_analysis_workflow",
        specialist_procedural_enabled=False,
    ),
    "governance_boundary_workflow": WorkflowMemoryPolicy(
        workflow_profile="governance_boundary_workflow",
        specialist_procedural_enabled=False,
    ),
    "decision_risk_workflow": WorkflowMemoryPolicy(
        workflow_profile="decision_risk_workflow",
        specialist_procedural_enabled=False,
    ),
    "software_change_workflow": WorkflowMemoryPolicy(
        workflow_profile="software_change_workflow",
    ),
    "operational_readiness_workflow": WorkflowMemoryPolicy(
        workflow_profile="operational_readiness_workflow",
    ),
}


MEMORY_REGISTRY: dict[MemoryClass, MemoryPolicy] = {
    MemoryClass.IDENTITY: MemoryPolicy(
        memory_class=MemoryClass.IDENTITY,
        display_name="Memoria de identidade",
        stability="muito_alta",
        sensitivity="critica",
        runtime_status="tipado_documentado",
    ),
    MemoryClass.NORMATIVE: MemoryPolicy(
        memory_class=MemoryClass.NORMATIVE,
        display_name="Memoria normativa",
        stability="muito_alta",
        sensitivity="critica",
        runtime_status="tipado_documentado",
    ),
    MemoryClass.USER: MemoryPolicy(
        memory_class=MemoryClass.USER,
        display_name="Memoria do usuario",
        stability="alta",
        sensitivity="elevada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        retrieval_priority=95,
    ),
    MemoryClass.RELATIONAL: MemoryPolicy(
        memory_class=MemoryClass.RELATIONAL,
        display_name="Memoria social e relacional",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=90,
        sharing_priority=90,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.CONTEXTUAL: MemoryPolicy(
        memory_class=MemoryClass.CONTEXTUAL,
        display_name="Memoria contextual",
        stability="baixa",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=60,
        sharing_priority=60,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.EPISODIC: MemoryPolicy(
        memory_class=MemoryClass.EPISODIC,
        display_name="Memoria episodica",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=70,
        sharing_priority=70,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.SEMANTIC: MemoryPolicy(
        memory_class=MemoryClass.SEMANTIC,
        display_name="Memoria semantica",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_partial",
        specialist_shared=True,
        domain_linked=True,
        retrieval_priority=50,
        sharing_priority=50,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.PROCEDURAL: MemoryPolicy(
        memory_class=MemoryClass.PROCEDURAL,
        display_name="Memoria procedural",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_partial",
        specialist_shared=True,
        retrieval_priority=40,
        sharing_priority=40,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.MISSION: MemoryPolicy(
        memory_class=MemoryClass.MISSION,
        display_name="Memoria de projetos e missoes",
        stability="alta",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        retrieval_priority=100,
        sharing_priority=100,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.DOMAIN: MemoryPolicy(
        memory_class=MemoryClass.DOMAIN,
        display_name="Memoria de dominio",
        stability="alta",
        sensitivity="baixa",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
        domain_linked=True,
        retrieval_priority=80,
        sharing_priority=80,
        sharing_mode="core_mediated_read_only",
        write_policy="through_core_only",
    ),
    MemoryClass.EVOLUTIONARY: MemoryPolicy(
        memory_class=MemoryClass.EVOLUTIONARY,
        display_name="Memoria evolutiva",
        stability="media",
        sensitivity="moderada",
        runtime_status="tipado_documentado",
    ),
}


def policy_for(memory_class: MemoryClass) -> MemoryPolicy:
    """Return the canonical policy for a memory class."""

    return MEMORY_REGISTRY[memory_class]


def default_memory_scopes() -> list[MemoryClass]:
    """Return default recovery scopes ordered by runtime priority."""

    return sorted(
        (
            memory_class
            for memory_class, policy in MEMORY_REGISTRY.items()
            if policy.retrieval_default
        ),
        key=lambda memory_class: (
            -MEMORY_REGISTRY[memory_class].retrieval_priority,
            memory_class.value,
        ),
    )


def specialist_shared_memory_classes() -> list[MemoryClass]:
    """Return specialist-shareable classes ordered by runtime priority."""

    return sorted(
        (
            memory_class
            for memory_class, policy in MEMORY_REGISTRY.items()
            if policy.specialist_shared
        ),
        key=lambda memory_class: (
            -MEMORY_REGISTRY[memory_class].sharing_priority,
            memory_class.value,
        ),
    )


def workflow_memory_policy(workflow_profile: str | None) -> WorkflowMemoryPolicy:
    """Return the sovereign memory visibility policy for a workflow profile."""

    if workflow_profile is None:
        return DEFAULT_WORKFLOW_MEMORY_POLICY
    return WORKFLOW_MEMORY_POLICIES.get(workflow_profile, DEFAULT_WORKFLOW_MEMORY_POLICY)


def guided_optional_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the optional classes that a guided route may expose."""

    policy = workflow_memory_policy(workflow_profile)
    classes: list[MemoryClass] = []
    if domain_compatible and semantic_evidence and policy.reasoning_semantic_enabled:
        classes.append(MemoryClass.SEMANTIC)
    if domain_compatible and procedural_evidence and policy.reasoning_procedural_enabled:
        classes.append(MemoryClass.PROCEDURAL)
    return classes


def guided_reasoning_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the optional guided-memory classes visible to planning and synthesis."""

    return guided_optional_memory_classes(
        semantic_evidence=semantic_evidence,
        procedural_evidence=procedural_evidence,
        domain_compatible=domain_compatible,
        workflow_profile=workflow_profile,
    )


def guided_specialist_memory_classes(
    *,
    semantic_evidence: bool,
    procedural_evidence: bool,
    domain_compatible: bool,
    workflow_profile: str | None = None,
) -> list[MemoryClass]:
    """Return the specialist-visible classes for a guided route packet."""

    policy = workflow_memory_policy(workflow_profile)
    classes = [
        memory_class
        for memory_class in specialist_shared_memory_classes()
        if memory_class not in {MemoryClass.SEMANTIC, MemoryClass.PROCEDURAL}
    ]
    optional_classes = guided_reasoning_memory_classes(
        semantic_evidence=semantic_evidence,
        procedural_evidence=procedural_evidence,
        domain_compatible=domain_compatible,
        workflow_profile=workflow_profile,
    )
    if MemoryClass.SEMANTIC in optional_classes and policy.specialist_semantic_enabled:
        classes.append(MemoryClass.SEMANTIC)
    if MemoryClass.PROCEDURAL in optional_classes and policy.specialist_procedural_enabled:
        classes.append(MemoryClass.PROCEDURAL)
    return classes


def default_priority_rules() -> list[str]:
    """Expose the runtime ordering rules implied by the registry."""

    ordered = ">".join(memory_class.value for memory_class in default_memory_scopes())
    return [
        f"default_recovery_order={ordered}",
        "mission_and_user_memory_before_recent_context",
        "domain_memory_requires_runtime_domain_link",
        "user_memory_recovers_when_user_id_is_available",
        "identity_and_normative_memory_are_not_default_recovery_scopes",
        "organization_scope_blocked_without_canonical_consumer",
    ]


def organization_scope_guard_payload() -> dict[str, str]:
    """Return the baseline guardrail that keeps organization scope out of runtime."""

    return {
        "status": "no_go_without_canonical_consumer",
        "reason": "baseline_keeps_organization_scope_out_until_a_sovereign_consumer_exists",
        "reopen_signal": "canonical_consumer_required_for_reopen",
    }


def specialist_memory_policy_payload(
    memory_classes: Iterable[MemoryClass],
) -> dict[str, dict[str, object]]:
    """Serialize specialist-facing policy metadata by memory class."""

    payload: dict[str, dict[str, object]] = {}
    for memory_class in memory_classes:
        policy = MEMORY_REGISTRY[memory_class]
        payload[memory_class.value] = {
            "runtime_status": policy.runtime_status,
            "stability": policy.stability,
            "sensitivity": policy.sensitivity,
            "specialist_shared": policy.specialist_shared,
            "domain_linked": policy.domain_linked,
            "sharing_mode": policy.sharing_mode,
            "write_policy": policy.write_policy,
        }
    return payload


DEFAULT_MEMORY_SCOPES: list[MemoryClass] = default_memory_scopes()

SHARED_MEMORY_CLASSES: list[MemoryClass] = specialist_shared_memory_classes()
