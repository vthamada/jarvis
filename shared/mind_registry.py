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


def rank_active_minds(
    *,
    intent: str,
    risk_markers: list[str],
    canonical_domains: list[str],
    mind_hints: list[str] | None = None,
) -> list[str]:
    """Rank active minds using sovereign registry policy."""

    hinted_minds = {
        mind_name for mind_name in (mind_hints or []) if mind_name in ACTIVE_MIND_REGISTRY
    }
    scored_minds: list[tuple[int, int, str]] = []
    for mind_name in ACTIVE_MIND_REGISTRY:
        definition = MIND_REGISTRY[mind_name]
        score = 0
        if mind_name in hinted_minds:
            score += 50
        if intent in definition.intent_affinities:
            score += 20
        score += sum(4 for domain in canonical_domains if domain in definition.domain_affinities)
        if len(canonical_domains) > 1 and definition.family in {
            "fundamental",
            "estrategica_decisoria",
        }:
            score += 2
        if risk_markers:
            if definition.risk_bias == "governance":
                score += 8 if intent == "sensitive_action" else 4
            elif definition.risk_bias == "decision":
                score += 6 if intent == "sensitive_action" else 3
            elif definition.risk_bias == "operational_caution":
                score += 5 if intent != "analysis" else 0
        if intent == "sensitive_action" and mind_name == "mente_etica":
            score += 4
        if definition.runtime_status == "nuclear_active":
            score += 5
        scored_minds.append((score, definition.arbitration_priority, mind_name))

    scored_minds.sort(key=lambda item: (-item[0], item[1], item[2]))
    ordered = [mind_name for score, _, mind_name in scored_minds if score > 0]
    if not ordered:
        ordered = ["mente_executiva", "mente_pragmatica"]
    return ordered


def select_supporting_minds(
    *,
    primary_mind: str,
    ordered_minds: list[str],
    limit: int,
) -> list[str]:
    """Return registry-backed supporting minds."""

    supporting: list[str] = []
    chosen = {primary_mind}
    for supporting_mind in preferred_support_for(primary_mind):
        if supporting_mind in ACTIVE_MIND_REGISTRY and supporting_mind not in chosen:
            supporting.append(supporting_mind)
            chosen.add(supporting_mind)
        if len(supporting) >= limit:
            return supporting[:limit]
    for supporting_mind in ordered_minds:
        if supporting_mind not in chosen:
            supporting.append(supporting_mind)
            chosen.add(supporting_mind)
        if len(supporting) >= limit:
            break
    return supporting[:limit]


def select_suppressed_minds(
    *,
    primary_mind: str,
    ordered_minds: list[str],
    supporting_minds: list[str],
    limit: int,
) -> list[str]:
    """Return the registry-backed suppressed set for observability."""

    chosen = {primary_mind, *supporting_minds}
    return [mind_name for mind_name in ordered_minds if mind_name not in chosen][:limit]


def select_tensions(
    *,
    intent: str,
    risk_markers: list[str],
    domains: list[str],
    primary_mind: str,
    supporting_minds: list[str],
) -> list[str]:
    """Return dominant tensions implied by the current sovereign arbitration."""

    tensions: list[str] = []
    primary_definition = definition_for(primary_mind)
    if primary_definition is not None:
        tensions.append(primary_definition.dominant_tension)
    if intent == "sensitive_action":
        tensions.append("equilibrar solicitacao do usuario com limites normativos")
    elif intent == "planning":
        tensions.append("equilibrar ambicao estrategica com a menor proxima acao segura")
    elif intent == "analysis":
        tensions.append("equilibrar profundidade analitica com conclusao util")
    else:
        tensions.append("equilibrar clareza executiva com contexto suficiente")
    if len(domains) > 1:
        tensions.append("integrar dominios sem diluir o objetivo dominante")
    if risk_markers:
        tensions.append("equilibrar velocidade de resposta com cautela operacional")
    if supporting_minds and "mente_critica" in supporting_minds:
        tensions.append("preservar escrutinio suficiente antes de concluir")
    return list(dict.fromkeys(tensions))


def primary_domain_driver(
    *,
    primary_mind: str,
    canonical_domains: list[str],
) -> str | None:
    """Resolve the dominant canonical domain associated with the primary mind."""

    definition = definition_for(primary_mind)
    if definition is None:
        return canonical_domains[0] if canonical_domains else None
    for domain in canonical_domains:
        if domain in definition.domain_affinities:
            return domain
    return canonical_domains[0] if canonical_domains else None


def build_arbitration_summary(
    *,
    primary_mind: str,
    supporting_minds: list[str],
    suppressed_minds: list[str],
    dominant_tension: str,
    domains: list[str],
) -> str:
    """Build a stable human-readable arbitration summary."""

    support = ", ".join(supporting_minds) if supporting_minds else "sem apoio adicional"
    suppressed = ", ".join(suppressed_minds) if suppressed_minds else "sem supressao relevante"
    domain_hint = ", ".join(domains[:2])
    return (
        f"{primary_mind} lidera a resposta com apoio de {support}, "
        f"suprimindo {suppressed} para manter foco em {domain_hint} "
        f"enquanto arbitra {dominant_tension}"
    )


def build_deliberation_notes(
    *,
    intent: str,
    primary_mind: str,
    supporting_minds: list[str],
    dominant_tension: str,
    specialist_hints: list[str],
    primary_domain_driver: str | None,
) -> list[str]:
    """Expose compact observability notes for the current arbitration."""

    notes = [
        f"linha_primaria={primary_mind}",
        f"modo={intent}",
        f"tensao_central={dominant_tension}",
        "fonte_arbitragem=mind_registry",
    ]
    if primary_domain_driver:
        notes.append(f"dominio_primario={primary_domain_driver}")
    if supporting_minds:
        notes.append(f"apoio={', '.join(supporting_minds)}")
    if specialist_hints:
        notes.append(f"apoio_subordinado={', '.join(specialist_hints[:2])}")
    return notes
