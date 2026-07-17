"""Integration coverage for governed domain onboarding in knowledge-service."""

from knowledge_service.service import KnowledgeService

from shared.domain_onboarding import DEFAULT_DOMAIN_ONBOARDING_BASELINE_PATH
from shared.domain_registry import RUNTIME_ROUTE_REGISTRY


def test_knowledge_service_assesses_baseline_manifest_without_activation() -> None:
    service = KnowledgeService()
    route_names_before = service.list_runtime_route_domains()

    assessment = service.assess_domain_onboarding_manifest()

    assert DEFAULT_DOMAIN_ONBOARDING_BASELINE_PATH.exists()
    assert assessment.route_name == "education_learning"
    assert assessment.readiness_status == "ready_for_human_review"
    assert assessment.decision == "queue_human_review"
    assert assessment.registry_write_allowed is False
    assert assessment.specialist_promotion_allowed is False
    assert service.list_runtime_route_domains() == route_names_before
    assert "education_learning" not in RUNTIME_ROUTE_REGISTRY


def test_knowledge_service_rejects_manifest_route_collision(tmp_path) -> None:
    manifest = DEFAULT_DOMAIN_ONBOARDING_BASELINE_PATH.read_text(encoding="utf-8")
    manifest = manifest.replace('"route_name": "education_learning"', '"route_name": "strategy"')
    candidate_path = tmp_path / "colliding-domain.json"
    candidate_path.write_text(manifest, encoding="utf-8")

    assessment = KnowledgeService().assess_domain_onboarding_manifest(str(candidate_path))

    assert assessment.readiness_status == "blocked"
    assert "route_already_registered" in assessment.blockers
