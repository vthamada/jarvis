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
    assert "especialista_analise_estruturada" in snapshot.specialist_hints
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


def test_cognitive_engine_prioritizes_domain_linked_shadow_specialist_hint() -> None:
    engine = CognitiveEngine()
    snapshot = engine.build_snapshot(
        intent="analysis",
        risk_markers=[],
        retrieved_domains=["software_development", "analysis"],
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="software_development",
                specialist_type="especialista_software_subordinado",
                specialist_mode="shadow",
                routing_reason="rota canonica de software em shadow mode",
            )
        ],
    )

    assert snapshot.active_domains == ["software_development", "analysis"]
    assert snapshot.specialist_hints[0] == "especialista_software_subordinado"


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
        domain_specialist_routes=[
            DomainSpecialistRouteContract(
                domain_name="analysis",
                specialist_type="especialista_analise_estruturada",
                specialist_mode="guided",
                routing_reason="rota canonica de analise estruturada em modo guiado",
            )
        ],
    )

    assert snapshot.specialist_hints[0] == "especialista_analise_estruturada"
    assert snapshot.specialist_hints.count("especialista_analise_estruturada") == 1
