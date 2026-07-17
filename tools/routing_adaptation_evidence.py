"""Build governed routing adaptation evidence from existing domain eval results."""

from __future__ import annotations

from observability_service.service import ObservabilityService

from shared.contracts import (
    DomainEvalCaseContract,
    DomainEvalCaseResultContract,
    RoutingAdaptationObservationContract,
    RoutingAdaptationReportContract,
)


def build_routing_adaptation_evidence(
    *,
    cases: list[DomainEvalCaseContract],
    case_results: list[DomainEvalCaseResultContract],
    outcome_status_by_case: dict[str, str],
    report_id: str,
    generated_at: str,
    minimum_occurrences: int = 2,
    evidence_refs_by_case: dict[str, list[str]] | None = None,
) -> RoutingAdaptationReportContract:
    """Correlate expected and observed routing without writing to the router."""

    blockers: list[str] = []
    if len(cases) > 100 or len(case_results) > 100:
        blockers.append("routing_adaptation_input_limit_exceeded")
    case_ids = [case.case_id for case in cases]
    result_ids = [result.case_id for result in case_results]
    if len(case_ids) != len(set(case_ids)):
        blockers.append("duplicate_routing_adaptation_case_id")
    if len(result_ids) != len(set(result_ids)):
        blockers.append("duplicate_routing_adaptation_result_case_id")

    cases_by_id = {case.case_id: case for case in cases[:100]}
    results_by_id = {result.case_id: result for result in case_results[:100]}
    missing_results = sorted(set(cases_by_id) - set(results_by_id))
    unknown_results = sorted(set(results_by_id) - set(cases_by_id))
    blockers.extend(f"case:{case_id}:result_required" for case_id in missing_results)
    blockers.extend(f"result:{case_id}:case_required" for case_id in unknown_results)

    extra_evidence = evidence_refs_by_case or {}
    observations: list[RoutingAdaptationObservationContract] = []
    for case_id, case in sorted(cases_by_id.items()):
        result = results_by_id.get(case_id)
        if result is None:
            continue
        evidence_refs = list(
            dict.fromkeys(
                [
                    f"domain-eval://{result.eval_pack_id}/{case.case_id}",
                    *result.response_evidence,
                    *extra_evidence.get(case_id, []),
                ]
            )
        )[:100]
        observed_route = result.observed_route
        observations.append(
            RoutingAdaptationObservationContract(
                observation_id=(
                    f"routing-adaptation-observation://{result.eval_pack_id}/"
                    f"{case.case_id}"
                ),
                source_case_id=case.case_id,
                expected_route=case.expected_route,
                observed_route=observed_route,
                expected_workflow_profile=case.expected_workflow_profile,
                observed_workflow_profile=result.observed_workflow_profile,
                expected_specialist_type=case.expected_specialist_type,
                observed_specialist_types=list(result.observed_specialist_types),
                outcome_status=outcome_status_by_case.get(case_id, ""),
                memory_causality_status=(
                    result.observed_memory_causality_status
                ),
                route_match=case.expected_route == observed_route,
                workflow_match=(
                    case.expected_workflow_profile
                    == result.observed_workflow_profile
                ),
                specialist_match=(
                    case.expected_specialist_type
                    in result.observed_specialist_types
                ),
                evidence_refs=evidence_refs,
                timestamp=generated_at,
                mission_id=case.mission_key,
            )
        )

    return ObservabilityService.build_routing_adaptation_report(
        report_id=report_id,
        observations=observations,
        minimum_occurrences=minimum_occurrences,
        generated_at=generated_at,
        blockers=sorted(set(blockers)),
    )
