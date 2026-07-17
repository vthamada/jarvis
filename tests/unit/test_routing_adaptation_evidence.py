from dataclasses import replace

from evolution_lab.service import EvolutionLabService
from observability_service.service import ObservabilityService

from shared.contract_validation import validate_contract_instance
from shared.contracts import (
    DomainEvalCaseContract,
    DomainEvalCaseResultContract,
    RoutingAdaptationObservationContract,
)
from shared.domain_registry import RUNTIME_ROUTE_REGISTRY, route_metadata_payload
from shared.schemas import (
    ROUTING_ADAPTATION_CANDIDATE_SCHEMA,
    ROUTING_ADAPTATION_OBSERVATION_SCHEMA,
    ROUTING_ADAPTATION_REPORT_SCHEMA,
)
from tools.routing_adaptation_evidence import build_routing_adaptation_evidence


def _case(case_id: str) -> DomainEvalCaseContract:
    return DomainEvalCaseContract(
        case_id=case_id,
        intent="analyze a bounded operational decision",
        input_text="Compare the alternatives using auditable evidence.",
        session_key=f"session-{case_id}",
        mission_key=f"mission-{case_id}",
        expected_decision="allow_with_conditions",
        expected_route="analysis",
        expected_canonical_domain_refs=["knowledge_and_communication"],
        expected_workflow_profile="structured_analysis_workflow",
        expected_specialist_type="structured_analysis_specialist",
        allowed_memory_causality_statuses=["causal_guidance"],
        required_response_fragments=["evidence"],
        required_events=["response_synthesized"],
    )


def _result(
    case_id: str,
    *,
    route: str = "strategy",
) -> DomainEvalCaseResultContract:
    route_metadata = route_metadata_payload(route)
    specialist = route_metadata["linked_specialist_type"]
    return DomainEvalCaseResultContract(
        eval_pack_id="eval-pack://domain/analysis/routing-adaptation",
        case_id=case_id,
        passed=False,
        checks={"route": False, "outcome": True},
        failures=["route_mismatch"],
        observed_governance_decision="allow_with_conditions",
        observed_route=route,
        observed_canonical_domain_refs=list(
            route_metadata["canonical_domain_refs"]
        ),
        observed_workflow_profile=str(route_metadata["workflow_profile"]),
        observed_specialist_types=[str(specialist)] if specialist else [],
        observed_memory_causality_status="causal_guidance",
        response_evidence=[f"evidence://routing/{case_id}"],
        response_length=500,
        observed_events=["response_synthesized"],
    )


def _run(
    *,
    second_route: str = "strategy",
    second_outcome: str = "completed",
):  # type: ignore[no-untyped-def]
    cases = [_case("case-1"), _case("case-2")]
    results = [_result("case-1"), _result("case-2", route=second_route)]
    return build_routing_adaptation_evidence(
        cases=cases,
        case_results=results,
        outcome_status_by_case={
            "case-1": "completed",
            "case-2": second_outcome,
        },
        report_id="routing-adaptation-report://analysis/001",
        generated_at="2026-07-16T21:00:00Z",
        evidence_refs_by_case={
            "case-1": ["trace://routing/case-1"],
            "case-2": ["trace://routing/case-2"],
        },
    )


def test_routing_evidence_creates_reviewable_candidate_without_registry_write(
    tmp_path,
) -> None:
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }

    report = _run()
    candidate = report.candidates[0]
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    proposal = service.create_proposal_from_routing_adaptation_candidate(candidate)
    queue = service.list_human_review_queue()

    assert report.report_status == "evidence_ready_for_human_review"
    assert report.observation_count == 2
    assert report.route_mismatch_count == 2
    assert report.candidate_count == 1
    assert candidate.current_route == "strategy"
    assert candidate.proposed_route == "analysis"
    assert candidate.workflow_profile == "structured_analysis_workflow"
    assert candidate.expected_specialist_type == "structured_analysis_specialist"
    assert candidate.outcome_statuses == ["completed"]
    assert candidate.memory_causality_statuses == ["causal_guidance"]
    assert candidate.candidate_status == "needs_review"
    assert candidate.routing_write_allowed is False
    assert proposal.proposal_type == "routing_adaptation_candidate"
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.optimization_safety_status == "sandbox_only"
    assert proposal.strategy_context["promotion_policy"]["active_registry_write"] is False
    assert len(queue) == 1
    assert queue[0].review_status == "needs_review"
    assert queue[0].requires_human_review is True
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before
    observation = RoutingAdaptationObservationContract(
        observation_id="routing-adaptation-observation://schema/1",
        source_case_id="case-schema",
        expected_route="analysis",
        observed_route="strategy",
        expected_workflow_profile="structured_analysis_workflow",
        observed_workflow_profile="strategic_direction_workflow",
        expected_specialist_type="structured_analysis_specialist",
        observed_specialist_types=["structured_analysis_specialist"],
        outcome_status="completed",
        memory_causality_status="causal_guidance",
        route_match=False,
        workflow_match=False,
        specialist_match=True,
        evidence_refs=["evidence://routing/schema/1"],
        timestamp="2026-07-16T21:00:00Z",
    )
    assert validate_contract_instance(
        observation,
        schema=ROUTING_ADAPTATION_OBSERVATION_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        candidate,
        schema=ROUTING_ADAPTATION_CANDIDATE_SCHEMA,
    ).status == "coherent"
    assert validate_contract_instance(
        report,
        schema=ROUTING_ADAPTATION_REPORT_SCHEMA,
    ).status == "coherent"


def test_routing_evidence_blocks_conflict_mixed_outcome_and_low_recurrence() -> None:
    conflicting = _run(second_route="software_development")
    mixed_outcome = _run(second_outcome="failed")
    low_recurrence = build_routing_adaptation_evidence(
        cases=[_case("case-1")],
        case_results=[_result("case-1")],
        outcome_status_by_case={"case-1": "completed"},
        report_id="routing-adaptation-report://analysis/low-recurrence",
        generated_at="2026-07-16T21:10:00Z",
    )

    assert conflicting.report_status == "attention_required"
    assert conflicting.candidates == []
    assert any(
        flag.endswith("conflicting_observed_routes")
        for flag in conflicting.conflict_flags
    )
    assert mixed_outcome.report_status == "attention_required"
    assert mixed_outcome.candidates == []
    assert any(
        flag.endswith("conflicting_outcomes")
        for flag in mixed_outcome.conflict_flags
    )
    assert low_recurrence.report_status == "no_adaptation_candidate"
    assert low_recurrence.candidates == []
    assert validate_contract_instance(
        low_recurrence,
        schema=ROUTING_ADAPTATION_REPORT_SCHEMA,
    ).status == "coherent"


def test_routing_evidence_and_proposal_reject_authority_claims(tmp_path) -> None:
    report = _run()
    candidate = report.candidates[0]
    unsafe_observation = RoutingAdaptationObservationContract(
        observation_id="routing-adaptation-observation://unsafe/1",
        source_case_id="case-unsafe",
        expected_route="analysis",
        observed_route="strategy",
        expected_workflow_profile="structured_analysis_workflow",
        observed_workflow_profile="strategic_direction_workflow",
        expected_specialist_type="structured_analysis_specialist",
        observed_specialist_types=["structured_analysis_specialist"],
        outcome_status="completed",
        memory_causality_status="causal_guidance",
        route_match=False,
        workflow_match=False,
        specialist_match=True,
        evidence_refs=["evidence://routing/unsafe/1"],
        timestamp="2026-07-16T21:20:00Z",
        routing_write_allowed=True,
    )
    blocked_report = ObservabilityService.build_routing_adaptation_report(
        report_id="routing-adaptation-report://unsafe",
        observations=[unsafe_observation, replace(unsafe_observation, observation_id="routing-adaptation-observation://unsafe/2")],
        minimum_occurrences=2,
        generated_at="2026-07-16T21:20:00Z",
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    blocked_proposal = service.create_proposal_from_routing_adaptation_candidate(
        replace(candidate, routing_write_allowed=True)
    )
    forged_recurrence = service.create_proposal_from_routing_adaptation_candidate(
        replace(candidate, observation_count=3)
    )

    assert blocked_report.report_status == "blocked"
    assert blocked_report.candidates == []
    assert any(
        blocker.endswith("routing_authority_claim_not_allowed")
        for blocker in blocked_report.blockers
    )
    assert blocked_proposal.optimization_candidate_status == "blocked"
    assert blocked_proposal.optimization_safety_status == "blocked_by_safety"
    assert "routing_candidate_authority_claim_not_allowed" in (
        blocked_proposal.optimization_blockers
    )
    assert forged_recurrence.optimization_candidate_status == "blocked"
    assert "routing_candidate_observation_count_mismatch" in (
        forged_recurrence.optimization_blockers
    )
