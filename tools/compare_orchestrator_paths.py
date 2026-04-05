"""Compare the baseline orchestrator flow with the optional LangGraph flow."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from json import dumps
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))

from tools.internal_pilot_support import (
    PilotExecutionResult,
    result_to_dict,
    run_pilot_scenarios,
)


@dataclass(frozen=True)
class PathComparisonResult:
    """Comparison for a single scenario across baseline and LangGraph flow paths."""

    scenario_id: str
    mismatch_fields: list[str]
    baseline: PilotExecutionResult
    candidate: PilotExecutionResult | None

    @property
    def core_match(self) -> bool:
        return not self.mismatch_fields and self.candidate is not None


def expectation_score(result: PilotExecutionResult) -> float:
    checks = [
        result.decision_matches_expectation,
        result.operation_matches_expectation,
    ]
    if result.continuity_matches_expectation is not None:
        checks.append(result.continuity_matches_expectation)
    return round(sum(1 for item in checks if item) / len(checks), 4)


def axis_adherence_score(result: PilotExecutionResult) -> float:
    statuses = [
        result.domain_alignment_status,
        result.mind_alignment_status,
        result.identity_alignment_status,
        result.memory_alignment_status,
        result.specialist_sovereignty_status,
    ]
    weights = {"healthy": 1.0, "partial": 0.6, "incomplete": 0.2, "attention_required": 0.0}
    return round(sum(weights.get(status, 0.0) for status in statuses) / len(statuses), 4)


def axis_gate_status(result: PilotExecutionResult) -> str:
    return result.axis_gate_status


def workflow_profile_assessment(result: PilotExecutionResult) -> str:
    status = result.workflow_profile_status
    if status == "healthy":
        return "baseline_saudavel"
    if status == "maturation_recommended":
        return "maturation_recommended"
    if status in {None, "not_applicable"}:
        return "not_applicable"
    return "attention_required"


def memory_causality_assessment(result: PilotExecutionResult) -> str:
    return result.memory_causality_status


def mind_domain_specialist_assessment(result: PilotExecutionResult) -> str:
    return result.mind_domain_specialist_status


def cognitive_recomposition_assessment(result: PilotExecutionResult) -> str:
    if not result.cognitive_recomposition_applied:
        if (
            result.cognitive_recomposition_reason is None
            and result.cognitive_recomposition_trigger is None
        ):
            return "not_applicable"
        return "attention_required"
    if (
        result.cognitive_recomposition_reason is not None
        and result.cognitive_recomposition_trigger is not None
    ):
        return "coherent"
    return "attention_required"


def summarize_comparisons(
    comparisons: list[PathComparisonResult],
    *,
    langgraph_status: str,
) -> dict[str, object]:
    total = len(comparisons)
    if total == 0:
        return {
            "scenario_count": 0,
            "matched_scenarios": 0,
            "divergent_scenarios": 0,
            "baseline_expectation_score": 0.0,
            "candidate_expectation_score": 0.0,
            "candidate_runtime_coverage": 0.0,
            "baseline_workflow_profile_decision": "not_applicable",
            "candidate_workflow_profile_decision": "not_applicable",
            "baseline_workflow_baseline_rate": 0.0,
            "baseline_workflow_maturation_rate": 0.0,
            "candidate_workflow_baseline_rate": 0.0,
            "candidate_workflow_maturation_rate": 0.0,
            "baseline_memory_causality_decision": "not_applicable",
            "candidate_memory_causality_decision": "not_applicable",
            "baseline_memory_causal_rate": 0.0,
            "candidate_memory_causal_rate": 0.0,
            "baseline_memory_attached_only_rate": 0.0,
            "candidate_memory_attached_only_rate": 0.0,
            "baseline_mind_domain_specialist_decision": "not_applicable",
            "candidate_mind_domain_specialist_decision": "not_applicable",
            "baseline_mind_domain_specialist_alignment_rate": 0.0,
            "candidate_mind_domain_specialist_alignment_rate": 0.0,
            "baseline_cognitive_recomposition_decision": "not_applicable",
            "candidate_cognitive_recomposition_decision": "not_applicable",
            "baseline_cognitive_recomposition_coherent_rate": 0.0,
            "candidate_cognitive_recomposition_coherent_rate": 0.0,
            "decision": "no_scenarios",
        }
    matched = sum(1 for item in comparisons if item.core_match)
    divergent = total - matched
    baseline_score = round(
        sum(expectation_score(item.baseline) for item in comparisons) / total,
        4,
    )
    available_candidates = [item.candidate for item in comparisons if item.candidate is not None]
    candidate_score = round(
        (
            sum(expectation_score(item) for item in available_candidates)
            / len(available_candidates)
        )
        if available_candidates
        else 0.0,
        4,
    )
    runtime_coverage = round(
        (
            sum(
                1
                for item in available_candidates
                if item.continuity_runtime_mode == "langgraph_subflow"
            )
            / len(available_candidates)
        )
        if available_candidates
        else 0.0,
        4,
    )
    baseline_gate_pass_rate = round(
        sum(1 for item in comparisons if axis_gate_status(item.baseline) == "healthy") / total,
        4,
    )
    candidate_gate_pass_rate = round(
        (
            sum(1 for item in available_candidates if axis_gate_status(item) == "healthy")
            / len(available_candidates)
        )
        if available_candidates
        else 0.0,
        4,
    )
    baseline_workflow_assessments = [
        workflow_profile_assessment(item.baseline) for item in comparisons
    ]
    candidate_workflow_assessments = [
        workflow_profile_assessment(item) for item in available_candidates
    ]
    baseline_memory_causality = [
        memory_causality_assessment(item.baseline) for item in comparisons
    ]
    candidate_memory_causality = [
        memory_causality_assessment(item) for item in available_candidates
    ]
    baseline_mind_domain_specialist = [
        mind_domain_specialist_assessment(item.baseline) for item in comparisons
    ]
    candidate_mind_domain_specialist = [
        mind_domain_specialist_assessment(item) for item in available_candidates
    ]
    baseline_cognitive_recomposition = [
        cognitive_recomposition_assessment(item.baseline) for item in comparisons
    ]
    candidate_cognitive_recomposition = [
        cognitive_recomposition_assessment(item) for item in available_candidates
    ]
    if langgraph_status != "available":
        decision = "candidate_unavailable"
    elif (
        divergent == 0
        and candidate_score >= baseline_score
        and runtime_coverage > 0.0
        and candidate_gate_pass_rate == 1.0
    ):
        decision = "candidate_ready_for_eval_gate"
    elif candidate_score < baseline_score:
        decision = "keep_baseline"
    else:
        decision = "candidate_requires_iteration"
    return {
        "scenario_count": total,
        "matched_scenarios": matched,
        "divergent_scenarios": divergent,
        "baseline_expectation_score": baseline_score,
        "candidate_expectation_score": candidate_score,
        "candidate_runtime_coverage": runtime_coverage,
        "baseline_axis_gate_pass_rate": baseline_gate_pass_rate,
        "candidate_axis_gate_pass_rate": candidate_gate_pass_rate,
        "baseline_workflow_profile_decision": summarize_workflow_profile_assessments(
            baseline_workflow_assessments
        ),
        "candidate_workflow_profile_decision": summarize_workflow_profile_assessments(
            candidate_workflow_assessments
        ),
        "baseline_workflow_baseline_rate": workflow_profile_rate(
            baseline_workflow_assessments,
            "baseline_saudavel",
        ),
        "baseline_workflow_maturation_rate": workflow_profile_rate(
            baseline_workflow_assessments,
            "maturation_recommended",
        ),
        "candidate_workflow_baseline_rate": workflow_profile_rate(
            candidate_workflow_assessments,
            "baseline_saudavel",
        ),
        "candidate_workflow_maturation_rate": workflow_profile_rate(
            candidate_workflow_assessments,
            "maturation_recommended",
        ),
        "baseline_memory_causality_decision": summarize_statuses(
            baseline_memory_causality
        ),
        "candidate_memory_causality_decision": summarize_statuses(
            candidate_memory_causality
        ),
        "baseline_memory_causal_rate": status_rate(
            baseline_memory_causality,
            "causal_guidance",
        ),
        "candidate_memory_causal_rate": status_rate(
            candidate_memory_causality,
            "causal_guidance",
        ),
        "baseline_memory_attached_only_rate": status_rate(
            baseline_memory_causality,
            "attached_only",
        ),
        "candidate_memory_attached_only_rate": status_rate(
            candidate_memory_causality,
            "attached_only",
        ),
        "baseline_mind_domain_specialist_decision": summarize_statuses(
            baseline_mind_domain_specialist
        ),
        "candidate_mind_domain_specialist_decision": summarize_statuses(
            candidate_mind_domain_specialist
        ),
        "baseline_mind_domain_specialist_alignment_rate": status_rate(
            baseline_mind_domain_specialist,
            "aligned",
        ),
        "candidate_mind_domain_specialist_alignment_rate": status_rate(
            candidate_mind_domain_specialist,
            "aligned",
        ),
        "baseline_cognitive_recomposition_decision": summarize_recomposition_statuses(
            baseline_cognitive_recomposition
        ),
        "candidate_cognitive_recomposition_decision": summarize_recomposition_statuses(
            candidate_cognitive_recomposition
        ),
        "baseline_cognitive_recomposition_coherent_rate": status_rate(
            baseline_cognitive_recomposition,
            "coherent",
        ),
        "candidate_cognitive_recomposition_coherent_rate": status_rate(
            candidate_cognitive_recomposition,
            "coherent",
        ),
        "decision": decision,
    }


def workflow_profile_rate(assessments: list[str], target: str) -> float:
    if not assessments:
        return 0.0
    return round(sum(1 for item in assessments if item == target) / len(assessments), 4)


def status_rate(statuses: list[str], target: str) -> float:
    if not statuses:
        return 0.0
    return round(sum(1 for item in statuses if item == target) / len(statuses), 4)


def summarize_workflow_profile_assessments(assessments: list[str]) -> str:
    if not assessments:
        return "not_applicable"
    if any(item == "attention_required" for item in assessments):
        return "attention_required"
    if any(item == "maturation_recommended" for item in assessments):
        return "maturation_recommended"
    if any(item == "baseline_saudavel" for item in assessments):
        return "baseline_saudavel"
    return "not_applicable"


def summarize_statuses(statuses: list[str]) -> str:
    if not statuses:
        return "not_applicable"
    if any(item == "attention_required" for item in statuses):
        return "attention_required"
    if any(item == "mismatch" for item in statuses):
        return "mismatch"
    if any(item == "causal_guidance" for item in statuses):
        return "causal_guidance"
    if any(item == "attached_only" for item in statuses):
        return "attached_only"
    if any(item == "aligned" for item in statuses):
        return "aligned"
    if any(item == "not_applicable" for item in statuses):
        return "not_applicable"
    return "incomplete"


def summarize_recomposition_statuses(statuses: list[str]) -> str:
    if not statuses:
        return "not_applicable"
    if any(item == "attention_required" for item in statuses):
        return "attention_required"
    if any(item == "coherent" for item in statuses):
        return "coherent"
    return "not_applicable"


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Compare baseline and LangGraph orchestrator paths.")
    parser.add_argument(
        "--profile",
        choices=["development", "controlled"],
        default="development",
        help="Operational profile used for the comparison.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for stdout.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for comparison artifacts.",
    )
    return parser.parse_args()


def compare_results(
    baseline_results: list[PilotExecutionResult],
    candidate_results: list[PilotExecutionResult] | None,
) -> list[PathComparisonResult]:
    candidate_index = {
        result.scenario_id: result for result in (candidate_results or [])
    }
    comparisons: list[PathComparisonResult] = []
    for baseline in baseline_results:
        candidate = candidate_index.get(baseline.scenario_id)
        mismatch_fields: list[str] = []
        if candidate is None:
            mismatch_fields.append("candidate_unavailable")
        else:
            if baseline.intent != candidate.intent:
                mismatch_fields.append("intent")
            if baseline.governance_decision != candidate.governance_decision:
                mismatch_fields.append("governance_decision")
            if baseline.operation_status != candidate.operation_status:
                mismatch_fields.append("operation_status")
            if baseline.continuity_action != candidate.continuity_action:
                mismatch_fields.append("continuity_action")
            if baseline.continuity_source != candidate.continuity_source:
                mismatch_fields.append("continuity_source")
            if baseline.workflow_domain_route != candidate.workflow_domain_route:
                mismatch_fields.append("workflow_domain_route")
            if baseline.workflow_trace_status != candidate.workflow_trace_status:
                mismatch_fields.append("workflow_trace_status")
            if baseline.workflow_profile_status != candidate.workflow_profile_status:
                mismatch_fields.append("workflow_profile_status")
            if baseline.memory_causality_status != candidate.memory_causality_status:
                mismatch_fields.append("memory_causality_status")
            if baseline.dominant_tension != candidate.dominant_tension:
                mismatch_fields.append("dominant_tension")
            if baseline.arbitration_source != candidate.arbitration_source:
                mismatch_fields.append("arbitration_source")
            if baseline.primary_domain_driver != candidate.primary_domain_driver:
                mismatch_fields.append("primary_domain_driver")
            if (
                baseline.mind_domain_specialist_status
                != candidate.mind_domain_specialist_status
            ):
                mismatch_fields.append("mind_domain_specialist_status")
            if (
                baseline.cognitive_recomposition_applied
                != candidate.cognitive_recomposition_applied
            ):
                mismatch_fields.append("cognitive_recomposition_applied")
            if (
                baseline.cognitive_recomposition_reason
                != candidate.cognitive_recomposition_reason
            ):
                mismatch_fields.append("cognitive_recomposition_reason")
            if (
                baseline.cognitive_recomposition_trigger
                != candidate.cognitive_recomposition_trigger
            ):
                mismatch_fields.append("cognitive_recomposition_trigger")
            if baseline.semantic_memory_focus != candidate.semantic_memory_focus:
                mismatch_fields.append("semantic_memory_focus")
            if baseline.procedural_memory_hint != candidate.procedural_memory_hint:
                mismatch_fields.append("procedural_memory_hint")
            if (
                baseline.semantic_memory_specialists
                != candidate.semantic_memory_specialists
            ):
                mismatch_fields.append("semantic_memory_specialists")
            if (
                baseline.procedural_memory_specialists
                != candidate.procedural_memory_specialists
            ):
                mismatch_fields.append("procedural_memory_specialists")
            if baseline.continuity_trace_status != candidate.continuity_trace_status:
                mismatch_fields.append("continuity_trace_status")
            if baseline.missing_continuity_signals != candidate.missing_continuity_signals:
                mismatch_fields.append("missing_continuity_signals")
            if baseline.continuity_anomaly_flags != candidate.continuity_anomaly_flags:
                mismatch_fields.append("continuity_anomaly_flags")
            if baseline.domain_alignment_status != candidate.domain_alignment_status:
                mismatch_fields.append("domain_alignment_status")
            if baseline.mind_alignment_status != candidate.mind_alignment_status:
                mismatch_fields.append("mind_alignment_status")
            if baseline.identity_alignment_status != candidate.identity_alignment_status:
                mismatch_fields.append("identity_alignment_status")
            if baseline.memory_alignment_status != candidate.memory_alignment_status:
                mismatch_fields.append("memory_alignment_status")
            if (
                baseline.specialist_sovereignty_status
                != candidate.specialist_sovereignty_status
            ):
                mismatch_fields.append("specialist_sovereignty_status")
            if baseline.axis_gate_status != candidate.axis_gate_status:
                mismatch_fields.append("axis_gate_status")
            if baseline.trace_status != candidate.trace_status:
                mismatch_fields.append("trace_status")
            if baseline.missing_required_events != candidate.missing_required_events:
                mismatch_fields.append("missing_required_events")
            if baseline.anomaly_flags != candidate.anomaly_flags:
                mismatch_fields.append("anomaly_flags")
        comparisons.append(
            PathComparisonResult(
                scenario_id=baseline.scenario_id,
                mismatch_fields=mismatch_fields,
                baseline=baseline,
                candidate=candidate,
            )
        )
    return comparisons


def render_text(payload: dict[str, object]) -> str:
    lines = [
        f"profile={payload['profile']}",
        f"overall_verdict={payload['overall_verdict']}",
        f"langgraph_status={payload['langgraph_status']}",
    ]
    for item in payload["scenario_results"]:
        lines.append(
            " ".join(
                [
                    f"scenario_id={item['scenario_id']}",
                    f"core_match={item['core_match']}",
                    f"mismatch_fields={','.join(item['mismatch_fields']) or 'none'}",
                    f"baseline_continuity={item['baseline']['continuity_action'] or 'none'}",
                    "candidate_continuity="
                    f"{item['candidate']['continuity_action'] if item['candidate'] else 'n/a'}",
                    f"baseline_runtime={item['baseline']['continuity_runtime_mode'] or 'none'}",
                    (
                        "baseline_workflow_route="
                        f"{item['baseline']['workflow_domain_route'] or 'none'}"
                    ),
                    f"baseline_workflow_trace={item['baseline']['workflow_trace_status']}",
                    (
                        "candidate_runtime="
                        f"{item['candidate']['continuity_runtime_mode']}"
                        if item["candidate"]
                        else "candidate_runtime=n/a"
                    ),
                    (
                        "candidate_workflow_route="
                        f"{item['candidate']['workflow_domain_route'] or 'none'}"
                        if item["candidate"]
                        else "candidate_workflow_route=n/a"
                    ),
                    (
                        "candidate_workflow_trace="
                        f"{item['candidate']['workflow_trace_status']}"
                        if item["candidate"]
                        else "candidate_workflow_trace=n/a"
                    ),
                    (
                        "baseline_workflow_profile_status="
                        f"{item['baseline']['workflow_profile_status']}"
                    ),
                    (
                        "baseline_workflow_profile_assessment="
                        f"{item['baseline_workflow_profile_assessment']}"
                    ),
                    (
                        "baseline_memory_causality_status="
                        f"{item['baseline']['memory_causality_status']}"
                    ),
                    (
                        "baseline_dominant_tension="
                        f"{item['baseline']['dominant_tension'] or 'none'}"
                    ),
                    (
                        "baseline_primary_domain_driver="
                        f"{item['baseline']['primary_domain_driver'] or 'none'}"
                    ),
                    (
                        "baseline_mind_domain_specialist_status="
                        f"{item['baseline']['mind_domain_specialist_status']}"
                    ),
                    (
                        "baseline_cognitive_recomposition_applied="
                        f"{item['baseline']['cognitive_recomposition_applied']}"
                    ),
                    (
                        "baseline_cognitive_recomposition_assessment="
                        f"{item['baseline_cognitive_recomposition_assessment']}"
                    ),
                    (
                        "baseline_cognitive_recomposition_trigger="
                        f"{item['baseline']['cognitive_recomposition_trigger'] or 'none'}"
                    ),
                    (
                        "candidate_workflow_profile_status="
                        f"{item['candidate']['workflow_profile_status']}"
                        if item["candidate"]
                        else "candidate_workflow_profile_status=n/a"
                    ),
                    (
                        "candidate_workflow_profile_assessment="
                        f"{item['candidate_workflow_profile_assessment']}"
                        if item["candidate_workflow_profile_assessment"] is not None
                        else "candidate_workflow_profile_assessment=n/a"
                    ),
                    (
                        "candidate_memory_causality_status="
                        f"{item['candidate']['memory_causality_status']}"
                        if item["candidate"]
                        else "candidate_memory_causality_status=n/a"
                    ),
                    (
                        "candidate_dominant_tension="
                        f"{item['candidate']['dominant_tension'] or 'none'}"
                        if item["candidate"]
                        else "candidate_dominant_tension=n/a"
                    ),
                    (
                        "candidate_primary_domain_driver="
                        f"{item['candidate']['primary_domain_driver'] or 'none'}"
                        if item["candidate"]
                        else "candidate_primary_domain_driver=n/a"
                    ),
                    (
                        "candidate_mind_domain_specialist_status="
                        f"{item['candidate']['mind_domain_specialist_status']}"
                        if item["candidate"]
                        else "candidate_mind_domain_specialist_status=n/a"
                    ),
                    (
                        "candidate_cognitive_recomposition_applied="
                        f"{item['candidate']['cognitive_recomposition_applied']}"
                        if item["candidate"]
                        else "candidate_cognitive_recomposition_applied=n/a"
                    ),
                    (
                        "candidate_cognitive_recomposition_assessment="
                        f"{item['candidate_cognitive_recomposition_assessment']}"
                        if item["candidate_cognitive_recomposition_assessment"] is not None
                        else "candidate_cognitive_recomposition_assessment=n/a"
                    ),
                    (
                        "candidate_cognitive_recomposition_trigger="
                        f"{item['candidate']['cognitive_recomposition_trigger'] or 'none'}"
                        if item["candidate"]
                        else "candidate_cognitive_recomposition_trigger=n/a"
                    ),
                    f"baseline_expectation_score={item['baseline_expectation_score']}",
                    f"baseline_axis_adherence_score={item['baseline_axis_adherence_score']}",
                    f"baseline_axis_gate_status={item['baseline_axis_gate_status']}",
                    (
                        "candidate_expectation_score="
                        f"{item['candidate_expectation_score']}"
                        if item["candidate_expectation_score"] is not None
                        else "candidate_expectation_score=n/a"
                    ),
                    (
                        "candidate_axis_adherence_score="
                        f"{item['candidate_axis_adherence_score']}"
                        if item["candidate_axis_adherence_score"] is not None
                        else "candidate_axis_adherence_score=n/a"
                    ),
                    (
                        "candidate_axis_gate_status="
                        f"{item['candidate_axis_gate_status']}"
                        if item["candidate_axis_gate_status"] is not None
                        else "candidate_axis_gate_status=n/a"
                    ),
                    f"baseline_decision={item['baseline']['governance_decision']}",
                    "candidate_decision="
                    f"{item['candidate']['governance_decision'] if item['candidate'] else 'n/a'}",
                ]
            )
        )
    summary = payload["comparison_summary"]
    lines.append(
        " ".join(
            [
                f"comparison_decision={summary['decision']}",
                f"scenario_count={summary['scenario_count']}",
                f"matched_scenarios={summary['matched_scenarios']}",
                f"divergent_scenarios={summary['divergent_scenarios']}",
                f"baseline_expectation_score={summary['baseline_expectation_score']}",
                f"candidate_expectation_score={summary['candidate_expectation_score']}",
                f"candidate_runtime_coverage={summary['candidate_runtime_coverage']}",
                f"baseline_axis_gate_pass_rate={summary['baseline_axis_gate_pass_rate']}",
                f"candidate_axis_gate_pass_rate={summary['candidate_axis_gate_pass_rate']}",
                "baseline_workflow_profile_decision="
                f"{summary['baseline_workflow_profile_decision']}",
                "candidate_workflow_profile_decision="
                f"{summary['candidate_workflow_profile_decision']}",
                "baseline_workflow_baseline_rate="
                f"{summary['baseline_workflow_baseline_rate']}",
                "baseline_workflow_maturation_rate="
                f"{summary['baseline_workflow_maturation_rate']}",
                "candidate_workflow_baseline_rate="
                f"{summary['candidate_workflow_baseline_rate']}",
                "candidate_workflow_maturation_rate="
                f"{summary['candidate_workflow_maturation_rate']}",
                "baseline_memory_causality_decision="
                f"{summary['baseline_memory_causality_decision']}",
                "candidate_memory_causality_decision="
                f"{summary['candidate_memory_causality_decision']}",
                "baseline_memory_causal_rate="
                f"{summary['baseline_memory_causal_rate']}",
                "candidate_memory_causal_rate="
                f"{summary['candidate_memory_causal_rate']}",
                "baseline_memory_attached_only_rate="
                f"{summary['baseline_memory_attached_only_rate']}",
                "candidate_memory_attached_only_rate="
                f"{summary['candidate_memory_attached_only_rate']}",
                "baseline_mind_domain_specialist_decision="
                f"{summary['baseline_mind_domain_specialist_decision']}",
                "candidate_mind_domain_specialist_decision="
                f"{summary['candidate_mind_domain_specialist_decision']}",
                "baseline_mind_domain_specialist_alignment_rate="
                f"{summary['baseline_mind_domain_specialist_alignment_rate']}",
                "candidate_mind_domain_specialist_alignment_rate="
                f"{summary['candidate_mind_domain_specialist_alignment_rate']}",
                "baseline_cognitive_recomposition_decision="
                f"{summary['baseline_cognitive_recomposition_decision']}",
                "candidate_cognitive_recomposition_decision="
                f"{summary['candidate_cognitive_recomposition_decision']}",
                "baseline_cognitive_recomposition_coherent_rate="
                f"{summary['baseline_cognitive_recomposition_coherent_rate']}",
                "candidate_cognitive_recomposition_coherent_rate="
                f"{summary['candidate_cognitive_recomposition_coherent_rate']}",
            ]
        )
    )
    return "\n".join(lines)


def resolve_output_dir(output_dir: str | None) -> Path:
    if output_dir is None:
        return ROOT / ".jarvis_runtime" / "path_comparison_v2"
    target = Path(output_dir)
    return target if target.is_absolute() else ROOT / target


def serialize_comparisons(
    comparisons: list[PathComparisonResult],
    *,
    profile: str,
    langgraph_status: str,
) -> dict[str, object]:
    overall_verdict = (
        "langgraph_unavailable"
        if langgraph_status != "available"
        else ("equivalent" if all(item.core_match for item in comparisons) else "divergent")
    )
    comparison_summary = summarize_comparisons(
        comparisons,
        langgraph_status=langgraph_status,
    )
    return {
        "profile": profile,
        "langgraph_status": langgraph_status,
        "overall_verdict": overall_verdict,
        "comparison_summary": comparison_summary,
        "scenario_results": [
            {
                "scenario_id": item.scenario_id,
                "core_match": item.core_match,
                "mismatch_fields": item.mismatch_fields,
                "baseline_expectation_score": expectation_score(item.baseline),
                "baseline_axis_adherence_score": axis_adherence_score(item.baseline),
                "baseline_axis_gate_status": axis_gate_status(item.baseline),
                "baseline_workflow_profile_assessment": workflow_profile_assessment(
                    item.baseline
                ),
                "baseline_memory_causality_assessment": memory_causality_assessment(
                    item.baseline
                ),
                "baseline_mind_domain_specialist_assessment": (
                    mind_domain_specialist_assessment(item.baseline)
                ),
                "baseline_cognitive_recomposition_assessment": (
                    cognitive_recomposition_assessment(item.baseline)
                ),
                "candidate_expectation_score": (
                    expectation_score(item.candidate) if item.candidate else None
                ),
                "candidate_axis_adherence_score": (
                    axis_adherence_score(item.candidate) if item.candidate else None
                ),
                "candidate_axis_gate_status": (
                    axis_gate_status(item.candidate) if item.candidate else None
                ),
                "candidate_workflow_profile_assessment": (
                    workflow_profile_assessment(item.candidate) if item.candidate else None
                ),
                "candidate_memory_causality_assessment": (
                    memory_causality_assessment(item.candidate) if item.candidate else None
                ),
                "candidate_mind_domain_specialist_assessment": (
                    mind_domain_specialist_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_cognitive_recomposition_assessment": (
                    cognitive_recomposition_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "baseline": result_to_dict(item.baseline),
                "candidate": result_to_dict(item.candidate) if item.candidate else None,
            }
            for item in comparisons
        ],
    }


def main() -> None:
    args = parse_args()
    target_dir = resolve_output_dir(args.output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    baseline_results = run_pilot_scenarios(
        profile=args.profile,
        workdir=target_dir / "baseline",
        path_name="baseline",
        use_langgraph_flow=False,
    )

    candidate_results: list[PilotExecutionResult] | None = None
    langgraph_status = "available"
    try:
        candidate_results = run_pilot_scenarios(
            profile=args.profile,
            workdir=target_dir / "langgraph",
            path_name="langgraph",
            use_langgraph_flow=True,
        )
    except RuntimeError as exc:
        if "LangGraph is not installed" not in str(exc):
            raise
        langgraph_status = "not_installed"

    comparisons = compare_results(baseline_results, candidate_results)
    payload = serialize_comparisons(
        comparisons,
        profile=args.profile,
        langgraph_status=langgraph_status,
    )
    (target_dir / "path_comparison.json").write_text(
        dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    (target_dir / "path_comparison.md").write_text(render_text(payload), encoding="utf-8")
    if args.format == "json":
        print(dumps(payload, ensure_ascii=True, indent=2))
        return
    print(render_text(payload))


if __name__ == "__main__":
    main()
