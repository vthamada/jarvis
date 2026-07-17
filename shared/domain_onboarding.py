"""Governed, no-mutation validation for domain onboarding candidates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from json import loads
from pathlib import Path
from re import fullmatch

from shared.contract_validation import validate_contract_instance
from shared.contracts import (
    DomainKnowledgePackContract,
    DomainOnboardingAssessmentContract,
    DomainOnboardingCandidateContract,
)
from shared.schemas import (
    DOMAIN_KNOWLEDGE_PACK_SCHEMA,
    DOMAIN_ONBOARDING_CANDIDATE_SCHEMA,
)

DEFAULT_DOMAIN_ONBOARDING_BASELINE_PATH = (
    Path(__file__).parent.parent / "knowledge" / "curated" / "domain_onboarding_baseline.json"
)

_ROUTE_PATTERN = r"[a-z][a-z0-9_]{2,63}"
_SEMVER_PATTERN = r"[0-9]+\.[0-9]+\.[0-9]+"
_SAFE_CANDIDATE_MATURITIES = {"candidate", "sandbox"}
_SAFE_ACTIVATION_STAGES = {"candidate", "sandbox"}
_MAX_MANIFEST_BYTES = 262_144
_MAX_LIST_ITEMS = 32
_MAX_TEXT_LENGTH = 512


def load_domain_onboarding_manifest(
    path: Path | str = DEFAULT_DOMAIN_ONBOARDING_BASELINE_PATH,
) -> tuple[DomainOnboardingCandidateContract, DomainKnowledgePackContract]:
    """Load a bounded local candidate manifest without activating it."""

    resolved_path = Path(path)
    if resolved_path.stat().st_size > _MAX_MANIFEST_BYTES:
        raise ValueError("domain onboarding manifest exceeds the bounded size limit")
    payload = loads(resolved_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("domain onboarding manifest must be a JSON object")
    candidate_payload = payload.get("candidate")
    pack_payload = payload.get("knowledge_pack")
    if not isinstance(candidate_payload, dict) or not isinstance(pack_payload, dict):
        raise ValueError("domain onboarding manifest requires candidate and knowledge_pack objects")
    return (
        DomainOnboardingCandidateContract(**candidate_payload),
        DomainKnowledgePackContract(**pack_payload),
    )


def assess_domain_onboarding_candidate(
    *,
    candidate: DomainOnboardingCandidateContract,
    knowledge_pack: DomainKnowledgePackContract,
    canonical_domains: Mapping[str, object] | Iterable[str],
    runtime_routes: Mapping[str, object] | Iterable[str],
    canonical_specialist_types: Iterable[str],
) -> DomainOnboardingAssessmentContract:
    """Assess a candidate and return an advisory result with no registry writes."""

    canonical_names = _names(canonical_domains)
    route_names = _names(runtime_routes)
    specialist_types = {str(item) for item in canonical_specialist_types}
    blockers: list[str] = []
    warnings: list[str] = []

    candidate_contract = validate_contract_instance(
        candidate,
        schema=DOMAIN_ONBOARDING_CANDIDATE_SCHEMA,
    )
    pack_contract = validate_contract_instance(
        knowledge_pack,
        schema=DOMAIN_KNOWLEDGE_PACK_SCHEMA,
    )
    blockers.extend(f"candidate_contract:{error}" for error in candidate_contract.errors)
    blockers.extend(f"knowledge_pack_contract:{error}" for error in pack_contract.errors)

    route_identifier_valid = fullmatch(_ROUTE_PATTERN, candidate.route_name or "") is not None
    if not route_identifier_valid:
        blockers.append("invalid_route_identifier")
    route_available = candidate.route_name not in route_names
    if not route_available:
        blockers.append("route_already_registered")

    candidate_domain_refs = _clean_items(candidate.canonical_domain_refs)
    pack_domain_refs = _clean_items(knowledge_pack.canonical_domain_refs)
    unknown_domains = sorted(set(candidate_domain_refs) - canonical_names)
    blockers.extend(f"unknown_canonical_domain:{name}" for name in unknown_domains)
    canonical_domains_known = bool(candidate_domain_refs) and not unknown_domains

    knowledge_pack_linked = candidate.knowledge_pack_id == knowledge_pack.knowledge_pack_id
    if not knowledge_pack_linked:
        blockers.append("knowledge_pack_reference_mismatch")
    knowledge_pack_domains_aligned = set(candidate_domain_refs) == set(pack_domain_refs)
    if not knowledge_pack_domains_aligned:
        blockers.append("knowledge_pack_domain_mismatch")

    pack_evidence_complete = _knowledge_pack_is_complete(knowledge_pack, blockers)
    workflow_contract_complete = _workflow_contract_is_complete(candidate, blockers)
    specialist_boundary_safe = _specialist_boundary_is_safe(
        candidate,
        specialist_types,
        blockers,
        warnings,
    )
    test_and_eval_complete = bool(_clean_items(candidate.proposed_tests)) and bool(
        str(candidate.eval_pack_ref or "").strip()
    )
    if not _clean_items(candidate.proposed_tests):
        blockers.append("missing_proposed_tests")
    if not str(candidate.eval_pack_ref or "").strip():
        blockers.append("missing_eval_pack_ref")
    rollback_defined = bool(str(candidate.rollback_plan_ref or "").strip())
    if not rollback_defined:
        blockers.append("missing_rollback_plan")
    candidate_evidence_present = bool(_clean_items(candidate.evidence_refs))
    if not candidate_evidence_present:
        blockers.append("missing_candidate_evidence_refs")

    governance_controls_preserved = _governance_controls_are_safe(
        candidate,
        knowledge_pack,
        blockers,
    )
    bounded_payload = _payload_is_bounded(candidate, knowledge_pack, blockers)

    criteria = {
        "candidate_contract_coherent": candidate_contract.status == "coherent",
        "knowledge_pack_contract_coherent": pack_contract.status == "coherent",
        "route_identifier_valid": route_identifier_valid,
        "route_available": route_available,
        "canonical_domains_known": canonical_domains_known,
        "knowledge_pack_linked": knowledge_pack_linked,
        "knowledge_pack_domains_aligned": knowledge_pack_domains_aligned,
        "knowledge_pack_evidence_complete": pack_evidence_complete,
        "workflow_contract_complete": workflow_contract_complete,
        "specialist_boundary_safe": specialist_boundary_safe,
        "test_and_eval_evidence_complete": test_and_eval_complete,
        "rollback_defined": rollback_defined,
        "candidate_evidence_present": candidate_evidence_present,
        "governance_controls_preserved": governance_controls_preserved,
        "bounded_payload": bounded_payload,
    }
    resolved_blockers = sorted(set(blockers))
    readiness_status = "ready_for_human_review" if not resolved_blockers else "blocked"
    decision = "queue_human_review" if not resolved_blockers else "return_for_revision"

    return DomainOnboardingAssessmentContract(
        assessment_id=(
            f"domain-onboarding-assessment://{candidate.route_name}/{knowledge_pack.version}"
        ),
        onboarding_candidate_id=candidate.onboarding_candidate_id,
        route_name=candidate.route_name,
        knowledge_pack_id=knowledge_pack.knowledge_pack_id,
        readiness_status=readiness_status,
        decision=decision,
        criteria=criteria,
        blockers=resolved_blockers,
        warnings=sorted(set(warnings)),
        registry_preview={
            "route_name": candidate.route_name,
            "display_name": candidate.display_name,
            "domain_scope": "runtime_route",
            "activation_stage": candidate.activation_stage,
            "maturity": candidate.requested_maturity,
            "canonical_refs": list(candidate_domain_refs),
            "linked_specialist_type": candidate.linked_specialist_type,
            "specialist_mode": candidate.specialist_mode,
            "workflow_profile": candidate.runtime_workflow_profile,
            "workflow_steps": list(candidate.workflow_steps),
            "workflow_checkpoints": list(candidate.workflow_checkpoints),
            "workflow_decision_points": list(candidate.workflow_decision_points),
        },
        timestamp=candidate.timestamp,
    )


def _names(values: Mapping[str, object] | Iterable[str]) -> set[str]:
    if isinstance(values, Mapping):
        return {str(item) for item in values}
    return {str(item) for item in values}


def _clean_items(values: Iterable[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _knowledge_pack_is_complete(
    knowledge_pack: DomainKnowledgePackContract,
    blockers: list[str],
) -> bool:
    complete = True
    required_lists = {
        "sources": knowledge_pack.source_refs,
        "content": knowledge_pack.content_refs,
        "coverage_topics": knowledge_pack.coverage_topics,
        "evidence_refs": knowledge_pack.evidence_refs,
    }
    for label, values in required_lists.items():
        if not _clean_items(values):
            blockers.append(f"missing_knowledge_pack_{label}")
            complete = False
    if fullmatch(_SEMVER_PATTERN, str(knowledge_pack.version or "")) is None:
        blockers.append("invalid_knowledge_pack_version")
        complete = False
    if knowledge_pack.pack_status != "candidate":
        blockers.append("knowledge_pack_not_candidate")
        complete = False
    return complete


def _workflow_contract_is_complete(
    candidate: DomainOnboardingCandidateContract,
    blockers: list[str],
) -> bool:
    complete = True
    if candidate.onboarding_workflow_profile != "domain_onboarding_workflow":
        blockers.append("invalid_onboarding_workflow_profile")
        complete = False
    if not str(candidate.runtime_workflow_profile or "").endswith("_workflow"):
        blockers.append("invalid_runtime_workflow_profile")
        complete = False
    required_lists = {
        "steps": candidate.workflow_steps,
        "checkpoints": candidate.workflow_checkpoints,
        "decision_points": candidate.workflow_decision_points,
    }
    for label, values in required_lists.items():
        if not _clean_items(values):
            blockers.append(f"missing_workflow_{label}")
            complete = False
    return complete


def _specialist_boundary_is_safe(
    candidate: DomainOnboardingCandidateContract,
    specialist_types: set[str],
    blockers: list[str],
    warnings: list[str],
) -> bool:
    specialist_type = str(candidate.linked_specialist_type or "").strip()
    if not specialist_type:
        if candidate.specialist_mode != "registry_only":
            blockers.append("specialist_mode_requires_linked_specialist")
            return False
        warnings.append("no_deep_specialist_requested")
        return True
    if specialist_type not in specialist_types:
        blockers.append("unknown_specialist_type")
        return False
    if candidate.specialist_mode != "shadow":
        blockers.append("specialist_promotion_requested")
        return False
    return True


def _governance_controls_are_safe(
    candidate: DomainOnboardingCandidateContract,
    knowledge_pack: DomainKnowledgePackContract,
    blockers: list[str],
) -> bool:
    controls = {
        "human_review_not_required": candidate.human_review_required,
        "registry_write_requested": not candidate.registry_write_allowed,
        "specialist_promotion_requested": not candidate.specialist_promotion_allowed,
        "automatic_activation_requested": not candidate.automatic_activation_allowed,
        "automatic_promotion_requested": not candidate.automatic_promotion_allowed,
        "core_mutation_requested": not candidate.core_mutation_allowed,
        "knowledge_pack_human_review_not_required": knowledge_pack.human_review_required,
        "knowledge_pack_automatic_activation_requested": (
            not knowledge_pack.automatic_activation_allowed
        ),
        "knowledge_pack_core_mutation_requested": not knowledge_pack.core_mutation_allowed,
        "unsafe_requested_maturity": candidate.requested_maturity in _SAFE_CANDIDATE_MATURITIES,
        "unsafe_activation_stage": candidate.activation_stage in _SAFE_ACTIVATION_STAGES,
    }
    for blocker, safe in controls.items():
        if not safe:
            blockers.append(blocker)
    return all(controls.values())


def _payload_is_bounded(
    candidate: DomainOnboardingCandidateContract,
    knowledge_pack: DomainKnowledgePackContract,
    blockers: list[str],
) -> bool:
    collections = (
        candidate.canonical_domain_refs,
        candidate.workflow_steps,
        candidate.workflow_checkpoints,
        candidate.workflow_decision_points,
        candidate.proposed_tests,
        candidate.evidence_refs,
        knowledge_pack.canonical_domain_refs,
        knowledge_pack.source_refs,
        knowledge_pack.content_refs,
        knowledge_pack.coverage_topics,
        knowledge_pack.evidence_refs,
    )
    bounded = all(
        len(values) <= _MAX_LIST_ITEMS
        and all(len(str(value)) <= _MAX_TEXT_LENGTH for value in values)
        for values in collections
    )
    if not bounded:
        blockers.append("unbounded_onboarding_payload")
    return bounded
