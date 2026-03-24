from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from knowledge_service.service import KnowledgeService
from shared.domain_registry import FALLBACK_RUNTIME_ROUTE


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

    assert "strategy" in result.active_domains
    assert len(result.active_domains) == 3
    assert len(result.snippets) == 3


def test_knowledge_service_prioritizes_governance_for_risk_analysis() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze governance risk and audit implications for the release.",
    )

    assert result.active_domains[0] == "governance"
    assert "analysis" in result.active_domains[:3]
    assert "decision_risk" in result.active_domains[:3]


def test_knowledge_service_prioritizes_governance_in_ambiguous_planning() -> None:
    service = KnowledgeService()
    result = service.retrieve_for_intent(
        intent="planning",
        query="Plan execution changes with audit safety and governance checks.",
    )

    assert result.active_domains[0] == "governance"
    assert set(result.active_domains) == {"governance", "productivity", "strategy"}


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
    assert "computacao_e_desenvolvimento" in result.registry_domains
    assert "planejamento_e_coordenacao" in result.registry_domains
    assert any(
        route.specialist_type == "especialista_software_subordinado"
        and route.specialist_mode == "shadow"
        and route.canonical_domain_refs == ["computacao_e_desenvolvimento"]
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


def test_knowledge_service_exposes_domain_registry() -> None:
    service = KnowledgeService()

    registry_domains = service.list_registry_domains()

    assert "estrategia_e_pensamento_sistemico" in registry_domains
    assert "computacao_e_desenvolvimento" in registry_domains


def test_knowledge_service_exposes_runtime_route_domains() -> None:
    service = KnowledgeService()

    route_domains = service.list_runtime_route_domains()

    assert "strategy" in route_domains
    assert "software_development" in route_domains


def test_knowledge_service_fallback_is_derived_from_registry() -> None:
    temp_dir = runtime_dir("knowledge-fallback")
    corpus_path = temp_dir / "isolated_corpus.json"
    corpus_path.write_text(
        dumps(
            {
                "domains": [
                    {
                        "name": "isolated_domain_no_registry",
                        "keywords": ["zzz_unique_token"],
                        "snippets": ["Isolated snippet."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    service = KnowledgeService(corpus_path=str(corpus_path))
    result = service.retrieve_for_intent(
        intent="general_assistance",
        query="completely unrelated query with no matching tokens",
    )

    assert result.active_domains == [FALLBACK_RUNTIME_ROUTE]


def test_knowledge_service_intent_prior_uses_registry_scope() -> None:
    service = KnowledgeService()

    result_planning = service.retrieve_for_intent(
        intent="planning",
        query="go-live readiness check before release",
    )

    # operational_readiness has all-operational canonical_refs → prior=1.8 for planning
    # + keyword matches ("readiness", "go-live", "release") → highest total score → must rank first
    # strategy has all-primary refs → prior=1.4 → ranks lower
    assert result_planning.active_domains[0] == "operational_readiness"


def test_knowledge_service_excludes_canonical_only_domains_from_runtime() -> None:
    temp_dir = runtime_dir("knowledge-canonical-only")
    corpus_path = temp_dir / "corpus.json"
    registry_path = temp_dir / "registry.json"

    corpus_path.write_text(
        dumps(
            {
                "domains": [
                    {
                        "name": "blocked_route",
                        "keywords": ["blocked", "canonical"],
                        "snippets": ["This domain should not appear in runtime."],
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
    registry_path.write_text(
        dumps(
            {
                "canonical_domains": [],
                "runtime_routes": [
                    {
                        "route_name": "blocked_route",
                        "display_name": "Blocked route",
                        "domain_scope": "runtime_route",
                        "activation_stage": "canonical",
                        "maturity": "canonical_only",
                        "canonical_refs": [],
                        "summary": "Should be excluded from runtime.",
                    },
                    {
                        "route_name": "productivity",
                        "display_name": "Productivity",
                        "domain_scope": "runtime_route",
                        "activation_stage": "v2",
                        "maturity": "active_registry",
                        "canonical_refs": [],
                        "summary": "Active route.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    service = KnowledgeService(
        corpus_path=str(corpus_path),
        domain_registry_path=str(registry_path),
    )
    result = service.retrieve_for_intent(
        intent="general_assistance",
        query="blocked canonical route test",
    )

    assert "blocked_route" not in result.active_domains
