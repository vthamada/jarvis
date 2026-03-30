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
    arbitration_priority: int
    intent_affinities: tuple[str, ...] = ()
    domain_affinities: tuple[str, ...] = ()
    dominant_tension: str = "manter foco executivo suficiente"
    risk_bias: str | None = None
    max_supporting_minds: int = 2
    max_suppressed_minds: int = 3


MIND_REGISTRY: dict[str, MindDefinition] = {
    "mente_logica": MindDefinition(
        mind_name="mente_logica",
        display_name="Mente logica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_analitica", "mente_cientifica", "mente_critica"),
        arbitration_priority=5,
        intent_affinities=("analysis",),
        domain_affinities=(
            "matematica_e_logica_formal",
            "comunicacao_linguagem_e_argumentacao",
        ),
        dominant_tension="equilibrar profundidade analitica com conclusao util",
    ),
    "mente_analitica": MindDefinition(
        mind_name="mente_analitica",
        display_name="Mente analitica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_logica", "mente_critica", "mente_probabilistica"),
        arbitration_priority=4,
        intent_affinities=("analysis",),
        domain_affinities=(
            "dados_estatistica_e_inteligencia_analitica",
            "tomada_de_decisao_complexa",
        ),
        dominant_tension="equilibrar profundidade analitica com conclusao util",
    ),
    "mente_cientifica": MindDefinition(
        mind_name="mente_cientifica",
        display_name="Mente cientifica",
        family="fundamental",
        runtime_status="canonica",
        preferred_support=("mente_logica", "mente_cetica", "mente_investigativa"),
        arbitration_priority=9,
        intent_affinities=("analysis",),
        domain_affinities=("pesquisa_e_inteligencia", "fisica_e_ciencias_naturais"),
        dominant_tension="equilibrar rigor investigativo com conclusao verificavel",
    ),
    "mente_sistemica": MindDefinition(
        mind_name="mente_sistemica",
        display_name="Mente sistemica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_integradora", "mente_estrategica", "mente_inventiva"),
        arbitration_priority=6,
        intent_affinities=("planning", "general_assistance"),
        domain_affinities=(
            "estrategia_e_pensamento_sistemico",
            "monitoramento_e_vigilancia_contextual",
            "coordenacao_de_identidade",
        ),
        dominant_tension="integrar dominios sem diluir o objetivo dominante",
    ),
    "mente_probabilistica": MindDefinition(
        mind_name="mente_probabilistica",
        display_name="Mente probabilistica",
        family="fundamental",
        runtime_status="nuclear_active",
        preferred_support=("mente_decisoria", "mente_cetica", "mente_analitica"),
        arbitration_priority=8,
        intent_affinities=("sensitive_action",),
        domain_affinities=(
            "dados_estatistica_e_inteligencia_analitica",
            "governanca_do_sistema",
            "monitoramento_e_vigilancia_contextual",
        ),
        dominant_tension="equilibrar velocidade de resposta com cautela operacional",
        risk_bias="operational_caution",
    ),
    "mente_estrategica": MindDefinition(
        mind_name="mente_estrategica",
        display_name="Mente estrategica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_tatica", "mente_decisoria", "mente_integradora"),
        arbitration_priority=2,
        intent_affinities=("planning",),
        domain_affinities=(
            "estrategia_e_pensamento_sistemico",
            "planejamento_e_coordenacao",
            "tomada_de_decisao_complexa",
        ),
        dominant_tension="equilibrar ambicao estrategica com a menor proxima acao segura",
    ),
    "mente_tatica": MindDefinition(
        mind_name="mente_tatica",
        display_name="Mente tatica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_estrategica", "mente_executiva", "mente_pragmatica"),
        arbitration_priority=7,
        intent_affinities=("planning",),
        domain_affinities=(
            "planejamento_e_coordenacao",
            "computacao_e_desenvolvimento",
            "produtividade_execucao_e_coordenacao",
        ),
        dominant_tension="equilibrar sequenciamento tatico com progresso verificavel",
    ),
    "mente_decisoria": MindDefinition(
        mind_name="mente_decisoria",
        display_name="Mente decisoria",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_probabilistica", "mente_estrategica", "mente_etica"),
        arbitration_priority=3,
        intent_affinities=("planning", "sensitive_action"),
        domain_affinities=(
            "tomada_de_decisao_complexa",
            "governanca_do_sistema",
            "defesa_seguranca_e_gestao_de_crises",
        ),
        dominant_tension="equilibrar decisao executavel com exposicao de risco aceitavel",
        risk_bias="decision",
    ),
    "mente_pragmatica": MindDefinition(
        mind_name="mente_pragmatica",
        display_name="Mente pragmatica",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_executiva", "mente_analitica", "mente_estrategica"),
        arbitration_priority=10,
        intent_affinities=("planning", "general_assistance"),
        domain_affinities=(
            "assistencia_pessoal_e_operacional",
            "produtividade_execucao_e_coordenacao",
            "computacao_e_desenvolvimento",
        ),
        dominant_tension="equilibrar utilidade imediata com rastreabilidade suficiente",
    ),
    "mente_executiva": MindDefinition(
        mind_name="mente_executiva",
        display_name="Mente executiva",
        family="estrategica_decisoria",
        runtime_status="nuclear_active",
        preferred_support=("mente_pragmatica", "mente_tatica", "mente_estrategica"),
        arbitration_priority=1,
        intent_affinities=("planning", "general_assistance"),
        domain_affinities=(
            "assistencia_pessoal_e_operacional",
            "planejamento_e_coordenacao",
            "coordenacao_de_identidade",
        ),
        dominant_tension="equilibrar clareza executiva com a menor proxima acao segura",
    ),
    "mente_criativa": MindDefinition(
        mind_name="mente_criativa",
        display_name="Mente criativa",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_inventiva", "mente_inovadora", "mente_integradora"),
        arbitration_priority=13,
        intent_affinities=("general_assistance",),
        domain_affinities=("criatividade_design_arte_e_inovacao", "producao_de_artefatos"),
        dominant_tension="equilibrar originalidade com coerencia estrutural",
    ),
    "mente_inventiva": MindDefinition(
        mind_name="mente_inventiva",
        display_name="Mente inventiva",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_cientifica", "mente_sistemica"),
        arbitration_priority=15,
        intent_affinities=("general_assistance",),
        domain_affinities=("computacao_e_desenvolvimento", "criatividade_design_arte_e_inovacao"),
        dominant_tension="equilibrar exploracao criativa com viabilidade tecnica",
    ),
    "mente_inovadora": MindDefinition(
        mind_name="mente_inovadora",
        display_name="Mente inovadora",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_inventiva", "mente_pragmatica"),
        arbitration_priority=16,
        intent_affinities=("general_assistance",),
        domain_affinities=(
            "criatividade_design_arte_e_inovacao",
            "estrategia_e_pensamento_sistemico",
        ),
        dominant_tension="equilibrar novidade com aderencia ao objetivo central",
    ),
    "mente_integradora": MindDefinition(
        mind_name="mente_integradora",
        display_name="Mente integradora",
        family="criativa_construtiva",
        runtime_status="canonica",
        preferred_support=("mente_sistemica", "mente_comunicacional", "mente_estrategica"),
        arbitration_priority=11,
        intent_affinities=("planning", "general_assistance"),
        domain_affinities=(
            "estrategia_e_pensamento_sistemico",
            "comunicacao_linguagem_e_argumentacao",
            "dados_estatistica_e_inteligencia_analitica",
        ),
        dominant_tension="integrar contribuicoes sem fragmentar a voz do sistema",
    ),
    "mente_etica": MindDefinition(
        mind_name="mente_etica",
        display_name="Mente etica",
        family="humana_relacional",
        runtime_status="nuclear_active",
        preferred_support=("mente_decisoria", "mente_empatica", "mente_critica"),
        arbitration_priority=1,
        intent_affinities=("sensitive_action",),
        domain_affinities=(
            "governanca_do_sistema",
            "filosofia_etica_e_epistemologia",
            "assistencia_pessoal_e_operacional",
        ),
        dominant_tension="equilibrar solicitacao do usuario com limites normativos",
        risk_bias="governance",
    ),
    "mente_empatica": MindDefinition(
        mind_name="mente_empatica",
        display_name="Mente empatica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_psicologica", "mente_comunicacional", "mente_diplomatica"),
        arbitration_priority=12,
        intent_affinities=("general_assistance",),
        domain_affinities=(
            "psicologia_e_comportamento_humano",
            "assistencia_pessoal_e_operacional",
        ),
        dominant_tension="equilibrar acolhimento com utilidade objetiva",
    ),
    "mente_psicologica": MindDefinition(
        mind_name="mente_psicologica",
        display_name="Mente psicologica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_empatica", "mente_comunicacional", "mente_analitica"),
        arbitration_priority=18,
        intent_affinities=("general_assistance",),
        domain_affinities=(
            "psicologia_e_comportamento_humano",
            "cognicao_aprendizado_e_inteligencia",
        ),
        dominant_tension="equilibrar leitura humana com estabilidade da resposta",
    ),
    "mente_comunicacional": MindDefinition(
        mind_name="mente_comunicacional",
        display_name="Mente comunicacional",
        family="humana_relacional",
        runtime_status="nuclear_active",
        preferred_support=("mente_logica", "mente_integradora", "mente_empatica"),
        arbitration_priority=9,
        intent_affinities=("general_assistance", "planning"),
        domain_affinities=(
            "comunicacao_linguagem_e_argumentacao",
            "assistencia_pessoal_e_operacional",
            "producao_de_artefatos",
        ),
        dominant_tension="equilibrar clareza narrativa com densidade suficiente",
    ),
    "mente_diplomatica": MindDefinition(
        mind_name="mente_diplomatica",
        display_name="Mente diplomatica",
        family="humana_relacional",
        runtime_status="canonica",
        preferred_support=("mente_etica", "mente_comunicacional", "mente_estrategica"),
        arbitration_priority=17,
        intent_affinities=("general_assistance",),
        domain_affinities=("governanca_do_sistema", "politica_geopolitica_e_governanca_publica"),
        dominant_tension="equilibrar firmeza normativa com tato relacional",
    ),
    "mente_investigativa": MindDefinition(
        mind_name="mente_investigativa",
        display_name="Mente investigativa",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_cetica", "mente_cientifica"),
        arbitration_priority=14,
        intent_affinities=("analysis",),
        domain_affinities=(
            "pesquisa_e_inteligencia",
            "computacao_e_desenvolvimento",
            "dados_estatistica_e_inteligencia_analitica",
        ),
        dominant_tension="equilibrar exploracao de evidencia com fechamento pratico",
    ),
    "mente_critica": MindDefinition(
        mind_name="mente_critica",
        display_name="Mente critica",
        family="investigativa_evolutiva",
        runtime_status="nuclear_active",
        preferred_support=("mente_cetica", "mente_logica", "mente_cientifica"),
        arbitration_priority=6,
        intent_affinities=("sensitive_action",),
        domain_affinities=(
            "dados_estatistica_e_inteligencia_analitica",
            "governanca_do_sistema",
            "computacao_e_desenvolvimento",
        ),
        dominant_tension="equilibrar escrutinio critico com decisao utilizavel",
        risk_bias="governance",
    ),
    "mente_cetica": MindDefinition(
        mind_name="mente_cetica",
        display_name="Mente cetica",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_probabilistica", "mente_decisoria"),
        arbitration_priority=19,
        intent_affinities=("analysis",),
        domain_affinities=(
            "avaliacao_e_verificacao",
            "governanca_do_sistema",
            "dados_estatistica_e_inteligencia_analitica",
        ),
        dominant_tension="equilibrar confianca operacional com verificacao adicional",
        risk_bias="operational_caution",
    ),
    "mente_exploratoria": MindDefinition(
        mind_name="mente_exploratoria",
        display_name="Mente exploratoria",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_criativa", "mente_investigativa", "mente_evolutiva"),
        arbitration_priority=20,
        intent_affinities=("general_assistance",),
        domain_affinities=("pesquisa_e_inteligencia", "criatividade_design_arte_e_inovacao"),
        dominant_tension="equilibrar descoberta ampla com foco no problema atual",
    ),
    "mente_evolutiva": MindDefinition(
        mind_name="mente_evolutiva",
        display_name="Mente evolutiva",
        family="investigativa_evolutiva",
        runtime_status="canonica",
        preferred_support=("mente_critica", "mente_executiva", "mente_investigativa"),
        arbitration_priority=21,
        intent_affinities=("analysis", "planning"),
        domain_affinities=(
            "aprendizado_do_sistema",
            "auto_observacao",
            "estrategia_e_pensamento_sistemico",
        ),
        dominant_tension="equilibrar melhoria futura com estabilidade do baseline atual",
    ),
}

ACTIVE_MIND_REGISTRY: tuple[str, ...] = tuple(
    name
    for name, definition in MIND_REGISTRY.items()
    if definition.runtime_status == "nuclear_active"
)


def definition_for(mind_name: str) -> MindDefinition | None:
    """Return the canonical definition for a given mind."""

    return MIND_REGISTRY.get(mind_name)


def preferred_support_for(mind_name: str) -> tuple[str, ...]:
    """Return registry-backed support relations for a given mind."""

    definition = definition_for(mind_name)
    return definition.preferred_support if definition is not None else ()


def arbitration_limits_for(mind_name: str) -> tuple[int, int]:
    """Return the registry-backed support and suppression limits for a mind."""

    definition = definition_for(mind_name)
    if definition is None:
        return (2, 3)
    return (definition.max_supporting_minds, definition.max_suppressed_minds)
