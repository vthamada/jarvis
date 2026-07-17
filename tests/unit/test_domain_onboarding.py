from copy import deepcopy

from shared.contract_validation import validate_contract_instance
from shared.contracts import (
    DomainKnowledgePackContract,
    DomainOnboardingCandidateContract,
)
from shared.domain_onboarding import assess_domain_onboarding_candidate
from shared.domain_registry import CANONICAL_DOMAIN_REGISTRY, RUNTIME_ROUTE_REGISTRY
from shared.schemas import (
    DOMAIN_KNOWLEDGE_PACK_SCHEMA,
    DOMAIN_ONBOARDING_CANDIDATE_SCHEMA,
)
from shared.specialist_registry import CANONICAL_SPECIALIST_TYPES


def _pack() -> DomainKnowledgePackContract:
    return DomainKnowledgePackContract(
        knowledge_pack_id="knowledge-pack://education_learning/1.0.0",
        version="1.0.0",
        canonical_domain_refs=["educacao_ensino_e_desenvolvimento_humano"],
        source_refs=["document://master/domain-map"],
        content_refs=["knowledge://education/source-1"],
        coverage_topics=["learning_objectives"],
        evidence_refs=["evidence://pack/review"],
        timestamp="2026-07-16T00:00:00Z",
    )


def _candidate() -> DomainOnboardingCandidateContract:
    return DomainOnboardingCandidateContract(
        onboarding_candidate_id="domain-onboarding-candidate://education_learning/1.0.0",
        route_name="education_learning",
        display_name="Education and Learning",
        canonical_domain_refs=["educacao_ensino_e_desenvolvimento_humano"],
        knowledge_pack_id="knowledge-pack://education_learning/1.0.0",
        onboarding_workflow_profile="domain_onboarding_workflow",
        runtime_workflow_profile="education_learning_workflow",
        workflow_steps=["frame_objective", "retrieve_evidence", "compose_guidance"],
        workflow_checkpoints=["scope_review", "evidence_review"],
        workflow_decision_points=["evidence_sufficient"],
        proposed_tests=["education_learning_eval_pack_baseline"],
        eval_pack_ref="eval-pack://domain/education_learning/1.0.0",
        rollback_plan_ref="rollback://domain/education_learning",
        evidence_refs=["evidence://mb-171/protocol"],
        timestamp="2026-07-16T00:00:00Z",
    )


def _assess(
    candidate: DomainOnboardingCandidateContract | None = None,
    pack: DomainKnowledgePackContract | None = None,
):
    return assess_domain_onboarding_candidate(
        candidate=candidate or _candidate(),
        knowledge_pack=pack or _pack(),
        canonical_domains=CANONICAL_DOMAIN_REGISTRY,
        runtime_routes=RUNTIME_ROUTE_REGISTRY,
        canonical_specialist_types=CANONICAL_SPECIALIST_TYPES,
    )


def test_domain_onboarding_contracts_match_canonical_schemas() -> None:
    assert validate_contract_instance(
        _candidate(), schema=DOMAIN_ONBOARDING_CANDIDATE_SCHEMA
    ).status == "coherent"
    assert validate_contract_instance(_pack(), schema=DOMAIN_KNOWLEDGE_PACK_SCHEMA).status == (
        "coherent"
    )


def test_valid_domain_candidate_only_reaches_human_review() -> None:
    assessment = _assess()

    assert assessment.readiness_status == "ready_for_human_review"
    assert assessment.decision == "queue_human_review"
    assert assessment.blockers == []
    assert assessment.human_review_required is True
    assert assessment.registry_write_allowed is False
    assert assessment.specialist_promotion_allowed is False
    assert assessment.automatic_activation_allowed is False
    assert assessment.automatic_promotion_allowed is False
    assert assessment.core_mutation_allowed is False
    assert assessment.registry_preview["maturity"] == "candidate"


def test_domain_onboarding_assessment_never_mutates_active_registries() -> None:
    canonical_before = deepcopy(CANONICAL_DOMAIN_REGISTRY)
    routes_before = deepcopy(RUNTIME_ROUTE_REGISTRY)

    assessment = _assess()

    assert assessment.readiness_status == "ready_for_human_review"
    assert CANONICAL_DOMAIN_REGISTRY == canonical_before
    assert RUNTIME_ROUTE_REGISTRY == routes_before
    assert "education_learning" not in RUNTIME_ROUTE_REGISTRY


def test_existing_route_and_unknown_domain_are_blocked() -> None:
    candidate = _candidate()
    candidate.route_name = "strategy"
    candidate.canonical_domain_refs = ["unknown_domain"]

    assessment = _assess(candidate=candidate)

    assert assessment.readiness_status == "blocked"
    assert "route_already_registered" in assessment.blockers
    assert "unknown_canonical_domain:unknown_domain" in assessment.blockers


def test_deep_specialist_promotion_request_is_blocked() -> None:
    candidate = _candidate()
    candidate.linked_specialist_type = "structured_analysis_specialist"
    candidate.specialist_mode = "guided"

    assessment = _assess(candidate=candidate)

    assert assessment.readiness_status == "blocked"
    assert "specialist_promotion_requested" in assessment.blockers


def test_existing_specialist_can_only_enter_as_shadow_candidate() -> None:
    candidate = _candidate()
    candidate.linked_specialist_type = "structured_analysis_specialist"
    candidate.specialist_mode = "shadow"

    assessment = _assess(candidate=candidate)

    assert assessment.readiness_status == "ready_for_human_review"
    assert assessment.registry_preview["specialist_mode"] == "shadow"


def test_missing_eval_rollback_and_pack_evidence_are_blocked() -> None:
    candidate = _candidate()
    candidate.proposed_tests = []
    candidate.eval_pack_ref = ""
    candidate.rollback_plan_ref = ""
    pack = _pack()
    pack.source_refs = []
    pack.evidence_refs = []

    assessment = _assess(candidate=candidate, pack=pack)

    assert assessment.readiness_status == "blocked"
    assert "missing_proposed_tests" in assessment.blockers
    assert "missing_eval_pack_ref" in assessment.blockers
    assert "missing_rollback_plan" in assessment.blockers
    assert "missing_knowledge_pack_sources" in assessment.blockers
    assert "missing_knowledge_pack_evidence_refs" in assessment.blockers


def test_candidate_cannot_request_registry_write_or_activation() -> None:
    candidate = _candidate()
    candidate.registry_write_allowed = True
    candidate.automatic_activation_allowed = True
    candidate.requested_maturity = "active_registry"

    assessment = _assess(candidate=candidate)

    assert assessment.readiness_status == "blocked"
    assert "registry_write_requested" in assessment.blockers
    assert "automatic_activation_requested" in assessment.blockers
    assert "unsafe_requested_maturity" in assessment.blockers
