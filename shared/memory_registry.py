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
        runtime_status="tipado_documentado",
    ),
    MemoryClass.PROCEDURAL: MemoryPolicy(
        memory_class=MemoryClass.PROCEDURAL,
        display_name="Memoria procedural",
        stability="alta",
        sensitivity="baixa",
        runtime_status="tipado_documentado",
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


def default_priority_rules() -> list[str]:
    """Expose the runtime ordering rules implied by the registry."""

    ordered = ">".join(memory_class.value for memory_class in default_memory_scopes())
    return [
        f"default_recovery_order={ordered}",
        "mission_and_user_memory_before_recent_context",
        "domain_memory_requires_runtime_domain_link",
        "user_memory_recovers_when_user_id_is_available",
        "identity_and_normative_memory_are_not_default_recovery_scopes",
    ]


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
