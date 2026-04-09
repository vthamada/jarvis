from cognitive_engine.engine import CognitiveEngine

from shared.contracts import DomainSpecialistRouteContract
from shared.domain_registry import FALLBACK_RUNTIME_ROUTE


def test_cognitive_engine_name() -> None:
    assert CognitiveEngine.name == "cognitive-engine"


def test_cognitive_engine_selects_primary_supporting_and_suppressed_minds() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=["update"],
        retrieved_domains=["analysis", "strategy"],
    )
    assert snapshot.primary_mind == "mente_analitica"
    assert snapshot.primary_mind_family == "fundamental"
    assert "mente_logica" in snapshot.supporting_minds
    assert len(snapshot.supporting_minds) <= snapshot.supporting_mind_limit
    assert len(snapshot.suppressed_minds) <= snapshot.suppressed_mind_limit
    assert snapshot.suppressed_minds
    assert snapshot.active_domains == ["analysis", "strategy"]
    assert snapshot.dominant_tension == "equilibrar profundidade analitica com conclusao util"
    assert snapshot.arbitration_summary
    assert snapshot.arbitration_source == "mind_registry"
    assert snapshot.specialist_hints == ["structured_analysis_specialist"]
    assert snapshot.deliberation_notes
    assert "fonte_arbitragem=mind_registry" in snapshot.deliberation_notes


def test_cognitive_engine_prioritizes_sensitive_primary_from_registry_policy() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="sensitive_action",
        risk_markers=["destructive"],
        retrieved_domains=["governance"],
    )

    assert snapshot.primary_mind == "mente_etica"
    assert snapshot.supporting_minds == ["mente_decisoria", "mente_critica"]
    assert snapshot.dominant_tension == "equilibrar solicitacao do usuario com limites normativos"


def test_cognitive_engine_prioritizes_registry_backed_specialist_hint() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["software_development", "analysis"],
    )

    assert snapshot.active_domains == ["software_development", "analysis"]
    assert snapshot.specialist_hints[0] == "software_change_specialist"


def test_cognitive_engine_fallback_uses_registry_domain() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="general_assistance",
        risk_markers=[],
        retrieved_domains=[],
    )

    assert snapshot.active_domains == [FALLBACK_RUNTIME_ROUTE]




def test_cognitive_engine_deduplicates_guided_analysis_specialist_hint() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["analysis", "strategy"],
    )

    assert snapshot.specialist_hints[0] == "structured_analysis_specialist"
    assert snapshot.specialist_hints.count("structured_analysis_specialist") == 1


def test_cognitive_engine_prefers_explicit_route_contracts_over_local_reredivation() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["analysis", "governance"],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="analysis",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota canonica ja resolvida para analise",
            )
        ],
    )

    assert snapshot.specialist_hints == ["structured_analysis_specialist"]


def test_cognitive_engine_prioritizes_explicit_route_matching_primary_domain_driver() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["software_development", "analysis"],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="software_development",
                specialist_type="software_change_specialist",
                specialist_mode="guided",
                routing_reason="rota de software resolvida",
            ),
            DomainSpecialistRouteContract(
                domain_name="analysis",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota de analise resolvida",
            ),
        ],
    )

    assert snapshot.primary_domain_driver == "dados_estatistica_e_inteligencia_analitica"
    assert snapshot.specialist_hints[0] == "structured_analysis_specialist"


def test_cognitive_engine_applies_recomposition_on_specialist_route_impasse() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["analysis", "governance"],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="governance",
                specialist_type="governance_review_specialist",
                specialist_mode="guided",
                routing_reason="rota guiada de governanca resolvida",
            )
        ],
    )

    assert snapshot.primary_domain_driver == "dados_estatistica_e_inteligencia_analitica"
    assert snapshot.recomposition_applied is True
    assert snapshot.recomposition_trigger == "specialist_route_impasse"
    assert snapshot.recomposition_reason
    assert snapshot.arbitration_source == "mind_registry_recomposition"
    assert "mente_critica" in snapshot.supporting_minds
    assert "recomposicao_cognitiva=" in snapshot.deliberation_notes[-1]


def test_cognitive_engine_prioritizes_domains_and_specialists_from_memory_guidance() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["strategy", "analysis"],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="strategy",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota de estrategia resolvida",
            ),
            DomainSpecialistRouteContract(
                domain_name="analysis",
                specialist_type="structured_analysis_specialist",
                specialist_mode="guided",
                routing_reason="rota de analise resolvida",
            ),
        ],
        memory_priority_domains=["analysis"],
        memory_specialist_hints=["structured_analysis_specialist"],
        memory_priority_sources=["mission_focus", "continuity_ranking"],
        memory_priority_summary="analysis:6[mission_focus,continuity_ranking]",
    )

    assert snapshot.active_domains == ["analysis", "strategy"]
    assert snapshot.memory_priority_applied is True
    assert snapshot.memory_priority_domains == ["analysis"]
    assert snapshot.memory_priority_specialist_hints == [
        "structured_analysis_specialist"
    ]
    assert snapshot.memory_priority_sources == ["mission_focus", "continuity_ranking"]
    assert snapshot.memory_priority_summary == "analysis:6[mission_focus,continuity_ranking]"
    assert snapshot.specialist_hints[0] == "structured_analysis_specialist"
