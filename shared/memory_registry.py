"""Memory registry derived from the Documento-Mestre."""

from __future__ import annotations

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
        runtime_status="tipado_documentado",
    ),
    MemoryClass.RELATIONAL: MemoryPolicy(
        memory_class=MemoryClass.RELATIONAL,
        display_name="Memoria social e relacional",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
    ),
    MemoryClass.CONTEXTUAL: MemoryPolicy(
        memory_class=MemoryClass.CONTEXTUAL,
        display_name="Memoria contextual",
        stability="baixa",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
    ),
    MemoryClass.EPISODIC: MemoryPolicy(
        memory_class=MemoryClass.EPISODIC,
        display_name="Memoria episodica",
        stability="media",
        sensitivity="moderada",
        runtime_status="runtime_parcial",
        retrieval_default=True,
        specialist_shared=True,
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
    ),
    MemoryClass.EVOLUTIONARY: MemoryPolicy(
        memory_class=MemoryClass.EVOLUTIONARY,
        display_name="Memoria evolutiva",
        stability="media",
        sensitivity="moderada",
        runtime_status="tipado_documentado",
    ),
}

DEFAULT_MEMORY_SCOPES: list[MemoryClass] = [
    memory_class
    for memory_class, policy in MEMORY_REGISTRY.items()
    if policy.retrieval_default
]

SHARED_MEMORY_CLASSES: list[MemoryClass] = [
    memory_class
    for memory_class, policy in MEMORY_REGISTRY.items()
    if policy.specialist_shared
]
