from copy import deepcopy
from dataclasses import replace
from json import dumps
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from knowledge_service.service import KnowledgeService

from shared.contracts import TechnologyRadarIntakeContract
from shared.domain_registry import FALLBACK_RUNTIME_ROUTE
from shared.technology_radar_intake import (
    technology_radar_intake_fingerprint,
    technology_radar_review_subject_fingerprint,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def technology_radar_intake(**overrides: object) -> TechnologyRadarIntakeContract:
    values: dict[str, object] = {
        "intake_id": "technology-radar-intake://openai-agents-sdk/1.0.0",
        "candidate_ref": "tech-candidate://openai-agents-sdk/handoff-adapters",
        "intake_version": "1.0.0",
        "technology_name": "OpenAI Agents SDK",
        "source_kind": "repository",
        "source_locator": "https://github.com/openai/openai-agents-python",
        "source_version_ref": "commit://openai-agents-python/0123456789abcdef",
        "source_content_sha256": "a" * 64,
        "license_id": "MIT",
        "license_status": "declared",
        "license_evidence_ref": "evidence://technology/license/openai-agents-sdk",
        "retrieved_at": "2026-08-12T12:00:00Z",
        "claims": ["Handoffs expose bounded delegation semantics."],
        "risks": ["The full runtime cannot replace the sovereign Core."],
        "absorption_class": "reference",
        "target_gap_refs": ["TA-005"],
        "research_approval_ref": "approval://technology-radar/openai-agents-sdk",
        "reviewed_payload_fingerprint": "0" * 64,
        "reviewer_ref": "operator://technology-radar/reviewer-1",
        "review_status": "approved_for_radar_intake",
        "review_evidence_refs": ["evidence://technology/review/openai-agents-sdk"],
        "reviewed_at": "2026-08-12T12:05:00Z",
        "recorded_at": "2026-08-12T12:06:00Z",
    }
    values.update(overrides)
    intake = TechnologyRadarIntakeContract(**values)  # type: ignore[arg-type]
    if "reviewed_payload_fingerprint" not in overrides:
        intake = replace(
            intake,
            reviewed_payload_fingerprint=(
                technology_radar_review_subject_fingerprint(intake)
            ),
        )
    return intake


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
    assert any(
        domain in result.active_domains[:3]
        for domain in {"decision_risk", "operational_readiness"}
    )


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
        route.specialist_type == "software_change_specialist"
        and route.specialist_mode == "guided"
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


def test_knowledge_service_prioritizes_canonical_domain_mentions_from_registry() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Preciso de apoio em computacao e desenvolvimento para revisar a mudanca do servico.",
    )

    assert result.active_domains[0] == "software_development"
    assert "computacao_e_desenvolvimento" in result.registry_domains


def test_knowledge_service_prioritizes_runtime_route_display_mentions_from_registry() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Acione a rota de runtime: governanca para revisar riscos e limites do release.",
    )

    assert result.active_domains[0] == "governance"


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



def test_knowledge_service_exposes_guided_analysis_specialist_route() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Compare trade-offs, evidence and decision criteria for the release path.",
    )

    assert "analysis" in result.active_domains
    assert any(
        route.domain_name == "analysis"
        and route.specialist_type == "structured_analysis_specialist"
        and route.specialist_mode == "guided"
        and route.canonical_domain_refs
        == [
            "dados_estatistica_e_inteligencia_analitica",
            "tomada_de_decisao_complexa",
        ]
        for route in result.specialist_routes
    )



def test_knowledge_service_exposes_guided_governance_specialist_route() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze governance risk, limits and audit constraints for the release.",
    )

    assert "governance" in result.active_domains
    assert any(
        route.domain_name == "governance"
        and route.specialist_type == "governance_review_specialist"
        and route.specialist_mode == "guided"
        and route.canonical_domain_refs
        == [
            "governanca_do_sistema",
            "defesa_seguranca_e_gestao_de_crises",
        ]
        for route in result.specialist_routes
    )



def test_knowledge_service_exposes_guided_operational_readiness_specialist_route() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="planning",
        query="Plan the rollout readiness checks, rollback points and release gates.",
    )

    assert result.active_domains[0] == "operational_readiness"
    assert any(
        route.domain_name == "operational_readiness"
        and route.specialist_type == "operational_planning_specialist"
        and route.specialist_mode == "guided"
        and route.canonical_domain_refs
        == [
            "planejamento_e_coordenacao",
            "monitoramento_e_vigilancia_contextual",
        ]
        for route in result.specialist_routes
    )



def test_knowledge_service_exposes_guided_strategy_specialist_route() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="planning",
        query="Plan the strategic direction, compare options and define the dominant criterion.",
    )

    assert "strategy" in result.active_domains[:3]
    assert any(
        route.domain_name == "strategy"
        and route.specialist_type == "structured_analysis_specialist"
        and route.specialist_mode == "guided"
        and route.canonical_domain_refs
        == [
            "estrategia_e_pensamento_sistemico",
            "tomada_de_decisao_complexa",
        ]
        for route in result.specialist_routes
    )


def test_knowledge_service_exposes_guided_decision_risk_specialist_route() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Review decision risk, reversibility and dominant containment gate for the release.",
    )

    assert "decision_risk" in result.active_domains[:3]
    assert any(
        route.domain_name == "decision_risk"
        and route.specialist_type == "governance_review_specialist"
        and route.specialist_mode == "guided"
        and route.canonical_domain_refs
        == [
            "tomada_de_decisao_complexa",
            "defesa_seguranca_e_gestao_de_crises",
        ]
        for route in result.specialist_routes
    )


def test_knowledge_service_exposes_current_curated_source_evidence() -> None:
    service = KnowledgeService()

    result = service.retrieve_for_intent(
        intent="analysis",
        query="Analyze governance risk and evidence for the release.",
        as_of="2026-07-16T12:00:00Z",
    )

    assert result.provenance_status == "complete"
    assert result.freshness_status == "current"
    assert result.conflict_status == "none_declared"
    assert result.uncertainty_notes == []
    assert result.source_evidence
    assert all(item.source_kind == "curated_internal" for item in result.source_evidence)
    assert all(
        item.source_ref.startswith("corpus://jarvis/curated/v1/")
        for item in result.source_evidence
    )


def test_knowledge_service_marks_missing_source_metadata_as_unknown() -> None:
    temp_dir = runtime_dir("knowledge-missing-provenance")
    corpus_path = temp_dir / "custom_corpus.json"
    corpus_path.write_text(
        dumps(
            {
                "domains": [
                    {
                        "name": "strategy",
                        "keywords": ["strategy"],
                        "snippets": ["Use a bounded strategy."],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = KnowledgeService(corpus_path=str(corpus_path)).retrieve_for_intent(
        intent="planning",
        query="Plan the strategy.",
        as_of="2026-07-16T12:00:00Z",
    )

    assert result.provenance_status == "missing"
    assert result.freshness_status == "unknown"
    assert result.conflict_status == "unknown"
    assert "source metadata missing for strategy" in result.uncertainty_notes
    assert "source freshness window missing" in result.uncertainty_notes


def test_knowledge_service_surfaces_stale_and_conflicting_source_evidence() -> None:
    temp_dir = runtime_dir("knowledge-stale-conflict")
    corpus_path = temp_dir / "custom_corpus.json"
    corpus_path.write_text(
        dumps(
            {
                "source_policy": {
                    "source_ref_prefix": "corpus://test/stale",
                    "source_kind": "curated_internal",
                    "reviewed_at": "2025-01-01T00:00:00Z",
                    "valid_until": "2025-12-31T23:59:59Z",
                    "confidence_status": "review_required",
                    "conflict_refs": ["source://conflicting-review"],
                },
                "domains": [
                    {
                        "name": "strategy",
                        "keywords": ["strategy"],
                        "snippets": ["Use a bounded strategy."],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = KnowledgeService(corpus_path=str(corpus_path)).retrieve_for_intent(
        intent="planning",
        query="Plan the strategy.",
        as_of="2026-07-16T12:00:00Z",
    )

    assert result.provenance_status == "complete"
    assert result.freshness_status == "stale"
    assert result.conflict_status == "conflict_detected"
    assert result.source_evidence[0].conflict_refs == ["source://conflicting-review"]
    assert any("freshness expired" in note for note in result.uncertainty_notes)


def test_knowledge_service_qualifies_reviewed_technology_radar_intake_read_only() -> None:
    service = KnowledgeService()
    intake = technology_radar_intake()
    domains_before = deepcopy(service.domains)
    canonical_registry_before = deepcopy(service.canonical_domain_registry)
    route_registry_before = deepcopy(service.domain_routes)

    assessment = service.assess_technology_radar_intake(intake)

    assert assessment.status == "eligible_for_reviewed_registry"
    assert assessment.blockers == []
    assert assessment.source_identity == (
        "https://github.com/openai/openai-agents-python",
        "commit://openai-agents-python/0123456789abcdef",
    )
    assert assessment.intake_fingerprint == technology_radar_intake_fingerprint(
        intake
    )
    assert assessment.eligible_for_reviewed_registry is True
    assert assessment.source_trusted is False
    assert assessment.read_only is True
    assert assessment.registry_write_authorized is False
    assert assessment.network_fetch_allowed is False
    assert assessment.knowledge_ingestion_allowed is False
    assert assessment.evolution_proposal_allowed is False
    assert assessment.dependency_installation_allowed is False
    assert assessment.execution_allowed is False
    assert assessment.runtime_activation_allowed is False
    assert assessment.promotion_authorized is False
    assert assessment.automatic_promotion_allowed is False
    assert assessment.core_mutation_allowed is False
    assert assessment.priority_mutation_allowed is False
    assert service.domains == domains_before
    assert service.canonical_domain_registry == canonical_registry_before
    assert service.domain_routes == route_registry_before


def test_knowledge_service_blocks_tampered_or_sensitive_radar_intake() -> None:
    service = KnowledgeService()

    tampered = service.assess_technology_radar_intake(
        technology_radar_intake(reviewed_payload_fingerprint="f" * 64)
    )
    sensitive = service.assess_technology_radar_intake(
        technology_radar_intake(
            claims=["api_key=top-secret must never enter the reviewed registry"]
        )
    )

    assert tampered.status == "blocked"
    assert tampered.eligible_for_reviewed_registry is False
    assert "reviewed_payload_fingerprint_mismatch" in tampered.blockers
    assert sensitive.status == "blocked"
    assert sensitive.eligible_for_reviewed_registry is False
    assert "sensitive_material_detected:claims" in sensitive.blockers
    assert sensitive.registry_write_authorized is False
    assert sensitive.knowledge_ingestion_allowed is False
    assert sensitive.evolution_proposal_allowed is False


def test_knowledge_service_hides_invalid_radar_source_identity_and_grants_no_authority() -> None:
    service = KnowledgeService()
    invalid = technology_radar_intake(
        source_locator="https://operator:password@example.com/repository",
        network_fetch_allowed=True,
        execution_allowed=True,
    )

    assessment = service.assess_technology_radar_intake(invalid)

    assert assessment.status == "blocked"
    assert assessment.source_identity is None
    assert "source_locator_userinfo_forbidden" in assessment.blockers
    assert "network_fetch_allowed_must_be_false" in assessment.blockers
    assert "execution_allowed_must_be_false" in assessment.blockers
    assert assessment.intake_fingerprint == technology_radar_intake_fingerprint(
        invalid
    )
    assert assessment.registry_write_authorized is False
    assert assessment.network_fetch_allowed is False
    assert assessment.knowledge_ingestion_allowed is False
    assert assessment.execution_allowed is False
    assert assessment.runtime_activation_allowed is False
    assert assessment.promotion_authorized is False
    assert assessment.core_mutation_allowed is False
