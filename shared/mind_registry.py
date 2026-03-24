"""Mind registry derived from the Documento-Mestre."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MindDefinition:
    mind_name: str
    display_name: str
    family: str
    runtime_status: str
    preferred_support: tuple[str, ...]


MIND_REGISTRY: dict[str, MindDefinition] = {
    "mente_logica": MindDefinition(
        mind_name="mente_logica",
        display_name="Mente logica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_analitica", "mente_cientifica", "mente_critica"),
    ),
    "mente_analitica": MindDefinition(
        mind_name="mente_analitica",
        display_name="Mente analitica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_logica", "mente_critica", "mente_probabilistica"),
    ),
    "mente_cientifica": MindDefinition(
        mind_name="mente_cientifica",
        display_name="Mente cientifica",
        family="fundamental",
        runtime_status="canonica",
        preferred_support=("mente_logica", "mente_cetica", "mente_investigativa"),
    ),
    "mente_sistemica": MindDefinition(
        mind_name="mente_sistemica",
        display_name="Mente sistemica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_integradora", "mente_estrategica", "mente_inventiva"),
    ),
    "mente_probabilistica": MindDefinition(
        mind_name="mente_probabilistica",
        display_name="Mente probabilistica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_decisoria", "mente_cetica", "mente_analitica"),
    ),
    "mente_estrategica": MindDefinition(
        mind_name="mente_estrategica",
        display_name="Mente estrategica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_tatica", "mente_decisoria", "mente_integradora"),
    ),
    "mente_tatica": MindDefinition(
        mind_name="mente_tatica",
        display_name="Mente tatica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_estrategica", "mente_executiva", "mente_pragmatica"),
    ),
    "mente_decisoria": MindDefinition(
        mind_name="mente_decisoria",
        display_name="Mente decisoria",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_probabilistica", "mente_estrategica", "mente_etica"),
    ),
    "mente_pragmatica": MindDefinition(
        mind_name="mente_pragmatica",
        display_name="Mente pragmatica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_executiva", "mente_analitica", "mente_estrategica"),
    ),
    "mente_executiva": MindDefinition(
        mind_name="mente_executiva",
        display_name="Mente executiva",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_pragmatica", "mente_tatica", "mente_estrategica"),
    ),
    "mente_criativa": MindDefinition(
        mind_name="mente_criativa",
        display_name="Mente criativa",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_inventiva", "mente_inovadora", "mente_integradora"),
    ),
    "mente_inventiva": MindDefinition(
        mind_name="mente_inventiva",
        display_name="Mente inventiva",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_cientifica", "mente_sistemica"),
    ),
    "mente_inovadora": MindDefinition(
        mind_name="mente_inovadora",
        display_name="Mente inovadora",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_inventiva", "mente_pragmatica"),
    ),
    "mente_integradora": MindDefinition(
        mind_name="mente_integradora",
        display_name="Mente integradora",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_sistemica", "mente_comunicacional", "mente_estrategica"),
    ),
    "mente_etica": MindDefinition(
        mind_name="mente_etica",
        display_name="Mente etica",
        family="humana_relacional",
        runtime_status="nuclear_active",
        preferred_support=("mente_decisoria", "mente_empatica", "mente_critica"),
    ),
    "mente_empatica": MindDefinition(
        mind_name="mente_empatica",
        display_name="Mente empatica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_psicologica", "mente_comunicacional", "mente_diplomatica"),
    ),
    "mente_psicologica": MindDefinition(
        mind_name="mente_psicologica",
        display_name="Mente psicologica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_empatica", "mente_comunicacional", "mente_analitica"),
    ),
    "mente_comunicacional": MindDefinition(
        mind_name="mente_comunicacional",
        display_name="Mente comunicacional",
        family="humana_relacional",
        runtime_status="nuclear_active",
        preferred_support=("mente_logica", "mente_integradora", "mente_empatica"),
    ),
    "mente_diplomatica": MindDefinition(
        mind_name="mente_diplomatica",
        display_name="Mente diplomatica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_etica", "mente_comunicacional", "mente_estrategica"),
    ),
    "mente_investigativa": MindDefinition(
        mind_name="mente_investigativa",
        display_name="Mente investigativa",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_cetica", "mente_cientifica"),
    ),
    "mente_critica": MindDefinition(
        mind_name="mente_critica",
        display_name="Mente critica",
        family="investigativa_evolutiva",
        runtime_status="nuclear_active",
        preferred_support=("mente_cetica", "mente_logica", "mente_cientifica"),
    ),
    "mente_cetica": MindDefinition(
        mind_name="mente_cetica",
        display_name="Mente cetica",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_probabilistica", "mente_decisoria"),
    ),
    "mente_exploratoria": MindDefinition(
        mind_name="mente_exploratoria",
        display_name="Mente exploratoria",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_investigativa", "mente_evolutiva"),
    ),
    "mente_evolutiva": MindDefinition(
        mind_name="mente_evolutiva",
        display_name="Mente evolutiva",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_executiva", "mente_investigativa"),
    ),
}

ACTIVE_MIND_REGISTRY: tuple[str, ...] = tuple(
    name
    for name, definition in MIND_REGISTRY.items()
    if definition.runtime_status == "nuclear_active"
)


def preferred_support_for(mind_name: str) -> tuple[str, ...]:
    """Return registry-backed support relations for a given mind."""

    definition = MIND_REGISTRY.get(mind_name)
    return definition.preferred_support if definition is not None else ()
