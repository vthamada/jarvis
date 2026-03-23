from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from knowledge_service.service import KnowledgeService


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_knowledge_service_name() -> None:
    assert KnowledgeService.name == "knowledge-service"


def test_knowledge_service_returns_domains_and_snippets_for_planning() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(intent="planning", query="Plan the next milestone safely.")

    assert result.active_domains == ["strategy", "productivity", "documentation"]
    assert len(result.snippets) == 3


def test_knowledge_service_prioritizes_governance_for_risk_analysis() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze governance risk and audit implications for the release.",
    )

    assert result.active_domains[:3] == ["governance", "analysis", "decision_risk"]


def test_knowledge_service_prioritizes_governance_in_ambiguous_planning() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(
        intent="planning",
        query="Plan execution changes with audit safety and governance checks.",
    )

    assert result.active_domains[:3] == ["governance", "strategy", "productivity"]


def test_knowledge_service_loads_curated_domains_from_custom_corpus() -> None:
    temp_dir = runtime_dir("knowledge-corpus")
    corpus_path = temp_dir / "custom_corpus.json"
    corpus_path.write_text(
        dumps(
            {
                "domains": [
                    {
                        "name": "architecture",
                        "keywords": ["arch"],
                        "snippets": ["Arquitetura first."],
                    },
                    {
                        "name": "productivity",
                        "keywords": ["execute"],
                        "snippets": ["Execute o menor passo."],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    service = KnowledgeService(corpus_path=str(corpus_path))

    assert service.list_domains() == ["architecture", "productivity"]
    result = service.retrieve_for_intent(intent="general_assistance", query="Review arch options.")
    assert result.active_domains == ["architecture", "productivity"]


def test_knowledge_service_covers_operational_readiness_and_software_domains() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze go-live readiness for the Python service API rollout.",
    )

    assert "operational_readiness" in result.active_domains
    assert "software_development" in result.active_domains
    assert "software_development" in result.registry_domains
    assert any(
        route.specialist_type == "especialista_software_subordinado"
        and route.specialist_mode == "shadow"
        for route in result.specialist_routes
    )


def test_knowledge_service_supports_pilot_and_observability_queries() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze pilot telemetry anomalies and trace gaps before the rollout comparison.",
    )

    assert "observability" in result.active_domains
    assert "pilot_operations" in result.active_domains


def test_knowledge_service_exposes_initial_v2_domain_registry() -> None:
    service = KnowledgeService()

    registry_domains = service.list_registry_domains()

    assert "strategy" in registry_domains
    assert "software_development" in registry_domains
