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


def workflow_output_assessment(result: PilotExecutionResult) -> str:
    status = result.workflow_output_status
    if status == "coherent":
        return "baseline_saudavel"
    if status == "partial":
        return "maturation_recommended"
    if status in {None, "not_applicable"}:
        return "not_applicable"
    return "attention_required"


def metacognitive_guidance_assessment(result: PilotExecutionResult) -> str:
    return result.metacognitive_guidance_status


def mind_disagreement_assessment(result: PilotExecutionResult) -> str:
    return result.mind_disagreement_status


def mind_validation_checkpoint_assessment(result: PilotExecutionResult) -> str:
    return result.mind_validation_checkpoint_status


def adaptive_intervention_assessment(result: PilotExecutionResult) -> str:
    if result.adaptive_intervention_status in {None, "not_applicable"}:
        return "not_applicable"
    return result.adaptive_intervention_effectiveness


def memory_causality_assessment(result: PilotExecutionResult) -> str:
    return result.memory_causality_status


def memory_lifecycle_assessment(result: PilotExecutionResult) -> str:
    return result.memory_lifecycle_status


def memory_corpus_assessment(result: PilotExecutionResult) -> str:
    return result.memory_corpus_status


def workflow_checkpoint_assessment(result: PilotExecutionResult) -> str:
    return result.workflow_checkpoint_status


def workflow_resume_assessment(result: PilotExecutionResult) -> str:
    return result.workflow_resume_status


def procedural_artifact_assessment(result: PilotExecutionResult) -> str:
    return result.procedural_artifact_status


def mind_domain_specialist_assessment(result: PilotExecutionResult) -> str:
    return result.mind_domain_specialist_status


def mind_domain_specialist_chain_assessment(result: PilotExecutionResult) -> str:
    return result.mind_domain_specialist_chain_status


def mind_composition_assessment(result: PilotExecutionResult) -> str:
    if result.mind_domain_specialist_chain_status in {"attention_required", "mismatch"}:
        return "attention_required"
    if result.mind_domain_specialist_status in {"attention_required", "mismatch"}:
        return "attention_required"
    if result.mind_validation_checkpoint_status == "attention_required":
        return "attention_required"
    if result.mind_disagreement_status == "deep_review_required":
        return "attention_required"
    if result.mind_domain_specialist_chain_status in {"incomplete", "evidence_partial"}:
        return "maturation_recommended"
    if result.mind_domain_specialist_status in {"incomplete", "evidence_partial"}:
        return "maturation_recommended"
    if result.mind_disagreement_status == "validation_required":
        return "maturation_recommended"
    if result.mind_disagreement_status in {None, "not_applicable", "contained"} and (
        result.mind_validation_checkpoint_status in {None, "not_applicable", "healthy"}
    ):
        return "baseline_saudavel"
    return "maturation_recommended"


def specialist_subflow_assessment(result: PilotExecutionResult) -> str:
    return result.specialist_subflow_status


def mission_runtime_state_assessment(result: PilotExecutionResult) -> str:
    return result.mission_runtime_state_status


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


def workflow_key(result: PilotExecutionResult) -> str:
    return result.expected_workflow_profile or result.workflow_domain_route or "baseline_runtime"


def refinement_vectors(result: PilotExecutionResult) -> list[dict[str, str]]:
    workflow_profile = workflow_key(result)
    vectors: list[dict[str, str]] = []

    def add_vector(axis: str, priority: str, recommendation: str) -> None:
        vectors.append(
            {
                "workflow_profile": workflow_profile,
                "axis": axis,
                "priority": priority,
                "recommendation": recommendation,
            }
        )

    if result.metacognitive_guidance_status in {"incomplete", "attention_required"}:
        add_vector(
            "metacognitive_guidance",
            "p0",
            "endurecer a ancora metacognitiva ate ela alterar criterio de saida de forma coerente",
        )
    if result.workflow_output_status in {"partial", "misaligned"}:
        add_vector(
            "workflow_output",
            "p0" if result.workflow_output_status == "misaligned" else "p1",
            "alinhar a resposta final ao contrato do workflow ativo com clausulas e foco coerentes",
        )
    if result.mind_disagreement_status in {
        "validation_required",
        "deep_review_required",
        "attention_required",
    } or result.mind_validation_checkpoint_status == "attention_required":
        add_vector(
            "mind_composition",
            "p0",
            "transformar a discordancia entre mentes em checkpoint governado do workflow ativo",
        )
    if result.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}:
        add_vector(
            "adaptive_intervention",
            "p0",
            (
                "fazer a intervencao adaptativa fechar o trigger causal "
                "sem degradar a saida nem a governanca"
            ),
        )
    if result.memory_causality_status in {"attached_only", "attention_required"}:
        add_vector(
            "memory_causality",
            "p0",
            (
                "fazer semantic e procedural alterarem framing, continuidade "
                "e proxima acao de forma causal"
            ),
        )
    if result.mind_domain_specialist_chain_status in {
        "incomplete",
        "evidence_partial",
        "attention_required",
        "mismatch",
    }:
        add_vector(
            "mind_domain_specialist_chain",
            "p0",
            (
                "restaurar coerencia evidence-first entre mente primaria, "
                "dominio e especialista guiado"
            ),
        )
    if result.workflow_profile_status in {"maturation_recommended", "attention_required"}:
        add_vector(
            "workflow_profile",
            "p1",
            "alinhar o contrato do workflow ativo com passos, checkpoints e criterio de resposta",
        )
    if result.memory_lifecycle_status in {"review_recommended", "attention_required"}:
        add_vector(
            "memory_lifecycle",
            "p1",
            "reduzir revisao pendente e estabilizar retencao/promocao no corpus guiado",
        )
    if result.memory_corpus_status in {"monitor", "review_recommended"}:
        add_vector(
            "memory_corpus",
            "p1",
            "revisar pressao de retencao por classe antes de ampliar memoria guiada",
        )
    if result.workflow_checkpoint_status in {"incomplete", "attention_required"}:
        add_vector(
            "workflow_checkpointing",
            "p1",
            "materializar checkpoints completos e retomada observavel no workflow ativo",
        )
    if result.workflow_resume_status in {"manual_resume_required", "resume_blocked"}:
        add_vector(
            "workflow_resume",
            "p1",
            "reduzir retomada manual e preservar resume points governados por workflow",
        )
    if result.procedural_artifact_status == "candidate":
        add_vector(
            "procedural_artifacts",
            "p1",
            "promover know-how procedural candidato para artefato reutilizavel through_core_only",
        )
    return vectors


def _priority_rank(priority: str) -> int:
    return {"p0": 0, "p1": 1, "p2": 2}.get(priority, 9)


def aggregate_refinement_vectors(
    results: list[PilotExecutionResult],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], dict[str, str]] = {}
    for result in results:
        for vector in refinement_vectors(result):
            key = (vector["workflow_profile"], vector["axis"])
            current = grouped.get(key)
            if current is None or _priority_rank(vector["priority"]) < _priority_rank(
                current["priority"]
            ):
                grouped[key] = vector
    return sorted(
        grouped.values(),
        key=lambda item: (
            _priority_rank(item["priority"]),
            item["workflow_profile"],
            item["axis"],
        ),
    )


def vector_axes(vectors: list[dict[str, str]]) -> str:
    axes = ",".join(vector["axis"] for vector in vectors)
    return axes or "none"


def matrix_workflows(matrix: dict[str, dict[str, object]]) -> str:
    workflows = ",".join(matrix.keys())
    return workflows or "none"


def evaluation_matrix(
    results: list[PilotExecutionResult],
) -> dict[str, dict[str, object]]:
    workflows = sorted({workflow_key(result) for result in results})
    matrix: dict[str, dict[str, object]] = {}
    for workflow in workflows:
        workflow_results = [result for result in results if workflow_key(result) == workflow]
        matrix[workflow] = {
            "workflow_profile": summarize_workflow_profile_assessments(
                [workflow_profile_assessment(result) for result in workflow_results]
            ),
            "workflow_output": summarize_workflow_profile_assessments(
                [workflow_output_assessment(result) for result in workflow_results]
            ),
            "metacognitive_guidance": summarize_statuses(
                [metacognitive_guidance_assessment(result) for result in workflow_results]
            ),
            "mind_disagreement": summarize_statuses(
                [mind_disagreement_assessment(result) for result in workflow_results]
            ),
            "mind_validation_checkpoint": summarize_statuses(
                [
                    mind_validation_checkpoint_assessment(result)
                    for result in workflow_results
                ]
            ),
            "adaptive_intervention": summarize_statuses(
                [adaptive_intervention_assessment(result) for result in workflow_results]
            ),
            "mind_composition": summarize_workflow_profile_assessments(
                [mind_composition_assessment(result) for result in workflow_results]
            ),
            "memory_causality": summarize_statuses(
                [memory_causality_assessment(result) for result in workflow_results]
            ),
            "memory_lifecycle": summarize_statuses(
                [memory_lifecycle_assessment(result) for result in workflow_results]
            ),
            "memory_corpus": summarize_statuses(
                [memory_corpus_assessment(result) for result in workflow_results]
            ),
            "workflow_checkpoint": summarize_statuses(
                [workflow_checkpoint_assessment(result) for result in workflow_results]
            ),
            "workflow_resume": summarize_statuses(
                [workflow_resume_assessment(result) for result in workflow_results]
            ),
            "procedural_artifact": summarize_statuses(
                [procedural_artifact_assessment(result) for result in workflow_results]
            ),
            "mind_domain_specialist_chain": summarize_statuses(
                [mind_domain_specialist_chain_assessment(result) for result in workflow_results]
            ),
            "priority_vectors": aggregate_refinement_vectors(workflow_results),
        }
    return matrix


WAVE_TWO_READINESS_REQUIREMENTS: dict[str, dict[str, set[str]]] = {
    "openai_agents_sdk": {
        "workflow_checkpoint": {"healthy"},
        "workflow_resume": {"healthy", "resume_available", "fresh_start"},
        "workflow_output": {"baseline_saudavel", "not_applicable"},
        "adaptive_intervention": {"effective", "not_applicable"},
        "mind_domain_specialist_chain": {"aligned", "not_applicable"},
    },
    "qwen_agent": {
        "workflow_profile": {"baseline_saudavel", "maturation_recommended", "not_applicable"},
        "memory_causality": {"causal_guidance", "not_applicable"},
        "memory_corpus": {"stable", "not_applicable"},
    },
    "graphiti_zep": {
        "memory_lifecycle": {"retained", "promoted", "not_applicable"},
        "memory_corpus": {"stable", "not_applicable"},
        "memory_causality": {"causal_guidance", "not_applicable"},
    },
    "mem0": {
        "memory_lifecycle": {"retained", "promoted", "not_applicable"},
        "memory_corpus": {"stable", "not_applicable"},
        "workflow_profile": {"baseline_saudavel", "maturation_recommended", "not_applicable"},
    },
    "openhands": {
        "workflow_output": {"baseline_saudavel", "not_applicable"},
        "procedural_artifact": {"reusable", "not_applicable"},
        "mind_domain_specialist_chain": {"aligned", "not_applicable"},
    },
    "browser_use": {
        "workflow_checkpoint": {"healthy"},
        "workflow_resume": {"healthy", "resume_available", "fresh_start"},
        "workflow_output": {"baseline_saudavel", "maturation_recommended", "not_applicable"},
        "adaptive_intervention": {"effective", "not_applicable"},
    },
    "open_interpreter": {
        "workflow_checkpoint": {"healthy"},
        "workflow_resume": {"healthy", "resume_available", "fresh_start"},
        "procedural_artifact": {"reusable", "not_applicable"},
    },
    "autogpt_platform": {
        "workflow_checkpoint": {"healthy"},
        "workflow_resume": {"healthy", "resume_available", "fresh_start"},
        "workflow_profile": {"baseline_saudavel", "not_applicable"},
        "workflow_output": {"baseline_saudavel", "not_applicable"},
    },
}


def wave_two_readiness_matrix(
    matrix: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    readiness: dict[str, dict[str, object]] = {}
    if not matrix:
        return readiness
    for technology, requirements in WAVE_TWO_READINESS_REQUIREMENTS.items():
        blockers: list[str] = []
        covered_workflows: list[str] = []
        for workflow_name, workflow_matrix in matrix.items():
            for axis, accepted in requirements.items():
                value = str(workflow_matrix.get(axis, "not_applicable"))
                if value not in accepted:
                    blockers.append(f"{workflow_name}:{axis}={value}")
                else:
                    covered_workflows.append(workflow_name)
        readiness[technology] = {
            "status": (
                "ready_for_controlled_experiment"
                if not blockers
                else "stabilize_nucleus_first"
            ),
            "covered_workflows": sorted(set(covered_workflows)),
            "blockers": blockers[:6],
        }
    return readiness


def wave_two_readiness_summary(matrix: dict[str, dict[str, object]]) -> str:
    readiness = wave_two_readiness_matrix(matrix)
    if not readiness:
        return "none"
    return ",".join(
        f"{technology}:{payload['status']}"
        for technology, payload in sorted(readiness.items())
    )


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
            "baseline_workflow_output_decision": "not_applicable",
            "candidate_workflow_output_decision": "not_applicable",
            "baseline_workflow_output_baseline_rate": 0.0,
            "candidate_workflow_output_baseline_rate": 0.0,
            "baseline_workflow_output_maturation_rate": 0.0,
            "candidate_workflow_output_maturation_rate": 0.0,
            "baseline_metacognitive_guidance_decision": "not_applicable",
            "candidate_metacognitive_guidance_decision": "not_applicable",
            "baseline_metacognitive_guidance_healthy_rate": 0.0,
            "candidate_metacognitive_guidance_healthy_rate": 0.0,
            "baseline_mind_disagreement_decision": "not_applicable",
            "candidate_mind_disagreement_decision": "not_applicable",
            "baseline_mind_validation_checkpoint_decision": "not_applicable",
            "candidate_mind_validation_checkpoint_decision": "not_applicable",
            "baseline_adaptive_intervention_decision": "not_applicable",
            "candidate_adaptive_intervention_decision": "not_applicable",
            "baseline_memory_causality_decision": "not_applicable",
            "candidate_memory_causality_decision": "not_applicable",
            "baseline_memory_causal_rate": 0.0,
            "candidate_memory_causal_rate": 0.0,
            "baseline_memory_attached_only_rate": 0.0,
            "candidate_memory_attached_only_rate": 0.0,
            "baseline_memory_lifecycle_decision": "not_applicable",
            "candidate_memory_lifecycle_decision": "not_applicable",
            "baseline_memory_lifecycle_retained_rate": 0.0,
            "candidate_memory_lifecycle_retained_rate": 0.0,
            "baseline_memory_lifecycle_review_rate": 0.0,
            "candidate_memory_lifecycle_review_rate": 0.0,
            "baseline_memory_corpus_decision": "not_applicable",
            "candidate_memory_corpus_decision": "not_applicable",
            "baseline_workflow_checkpoint_decision": "not_applicable",
            "candidate_workflow_checkpoint_decision": "not_applicable",
            "baseline_workflow_checkpoint_healthy_rate": 0.0,
            "candidate_workflow_checkpoint_healthy_rate": 0.0,
            "baseline_workflow_resume_decision": "not_applicable",
            "candidate_workflow_resume_decision": "not_applicable",
            "baseline_workflow_resume_available_rate": 0.0,
            "candidate_workflow_resume_available_rate": 0.0,
            "baseline_procedural_artifact_decision": "not_applicable",
            "candidate_procedural_artifact_decision": "not_applicable",
            "baseline_procedural_artifact_reusable_rate": 0.0,
            "candidate_procedural_artifact_reusable_rate": 0.0,
            "baseline_procedural_artifact_candidate_rate": 0.0,
            "candidate_procedural_artifact_candidate_rate": 0.0,
            "baseline_mind_domain_specialist_decision": "not_applicable",
            "candidate_mind_domain_specialist_decision": "not_applicable",
            "baseline_mind_domain_specialist_alignment_rate": 0.0,
            "candidate_mind_domain_specialist_alignment_rate": 0.0,
            "baseline_mind_domain_specialist_chain_decision": "not_applicable",
            "candidate_mind_domain_specialist_chain_decision": "not_applicable",
            "baseline_mind_domain_specialist_chain_alignment_rate": 0.0,
            "candidate_mind_domain_specialist_chain_alignment_rate": 0.0,
            "baseline_specialist_subflow_decision": "not_applicable",
            "candidate_specialist_subflow_decision": "not_applicable",
            "baseline_specialist_subflow_healthy_rate": 0.0,
            "candidate_specialist_subflow_healthy_rate": 0.0,
            "candidate_specialist_runtime_coverage": 0.0,
            "baseline_mission_runtime_state_decision": "not_applicable",
            "candidate_mission_runtime_state_decision": "not_applicable",
            "baseline_mission_runtime_state_healthy_rate": 0.0,
            "candidate_mission_runtime_state_healthy_rate": 0.0,
            "baseline_cognitive_recomposition_decision": "not_applicable",
            "candidate_cognitive_recomposition_decision": "not_applicable",
            "baseline_cognitive_recomposition_coherent_rate": 0.0,
            "candidate_cognitive_recomposition_coherent_rate": 0.0,
            "baseline_refinement_vectors": [],
            "candidate_refinement_vectors": [],
            "baseline_evaluation_matrix": {},
            "candidate_evaluation_matrix": {},
            "baseline_wave_two_readiness_matrix": {},
            "candidate_wave_two_readiness_matrix": {},
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
    baseline_workflow_output_assessments = [
        workflow_output_assessment(item.baseline) for item in comparisons
    ]
    candidate_workflow_output_assessments = [
        workflow_output_assessment(item) for item in available_candidates
    ]
    baseline_metacognitive_guidance = [
        metacognitive_guidance_assessment(item.baseline) for item in comparisons
    ]
    candidate_metacognitive_guidance = [
        metacognitive_guidance_assessment(item) for item in available_candidates
    ]
    baseline_mind_disagreement = [
        mind_disagreement_assessment(item.baseline) for item in comparisons
    ]
    candidate_mind_disagreement = [
        mind_disagreement_assessment(item) for item in available_candidates
    ]
    baseline_mind_validation_checkpoint = [
        mind_validation_checkpoint_assessment(item.baseline) for item in comparisons
    ]
    candidate_mind_validation_checkpoint = [
        mind_validation_checkpoint_assessment(item) for item in available_candidates
    ]
    baseline_adaptive_intervention = [
        adaptive_intervention_assessment(item.baseline) for item in comparisons
    ]
    candidate_adaptive_intervention = [
        adaptive_intervention_assessment(item) for item in available_candidates
    ]
    baseline_memory_causality = [
        memory_causality_assessment(item.baseline) for item in comparisons
    ]
    candidate_memory_causality = [
        memory_causality_assessment(item) for item in available_candidates
    ]
    baseline_memory_lifecycle = [
        memory_lifecycle_assessment(item.baseline) for item in comparisons
    ]
    candidate_memory_lifecycle = [
        memory_lifecycle_assessment(item) for item in available_candidates
    ]
    baseline_memory_corpus = [
        memory_corpus_assessment(item.baseline) for item in comparisons
    ]
    candidate_memory_corpus = [
        memory_corpus_assessment(item) for item in available_candidates
    ]
    baseline_workflow_checkpoint = [
        workflow_checkpoint_assessment(item.baseline) for item in comparisons
    ]
    candidate_workflow_checkpoint = [
        workflow_checkpoint_assessment(item) for item in available_candidates
    ]
    baseline_workflow_resume = [
        workflow_resume_assessment(item.baseline) for item in comparisons
    ]
    candidate_workflow_resume = [
        workflow_resume_assessment(item) for item in available_candidates
    ]
    baseline_procedural_artifact = [
        procedural_artifact_assessment(item.baseline) for item in comparisons
    ]
    candidate_procedural_artifact = [
        procedural_artifact_assessment(item) for item in available_candidates
    ]
    baseline_mind_domain_specialist = [
        mind_domain_specialist_assessment(item.baseline) for item in comparisons
    ]
    candidate_mind_domain_specialist = [
        mind_domain_specialist_assessment(item) for item in available_candidates
    ]
    baseline_mind_domain_specialist_chain = [
        mind_domain_specialist_chain_assessment(item.baseline) for item in comparisons
    ]
    candidate_mind_domain_specialist_chain = [
        mind_domain_specialist_chain_assessment(item) for item in available_candidates
    ]
    baseline_specialist_subflow = [
        specialist_subflow_assessment(item.baseline) for item in comparisons
    ]
    candidate_specialist_subflow = [
        specialist_subflow_assessment(item) for item in available_candidates
    ]
    baseline_mission_runtime_state = [
        mission_runtime_state_assessment(item.baseline) for item in comparisons
    ]
    candidate_mission_runtime_state = [
        mission_runtime_state_assessment(item) for item in available_candidates
    ]
    baseline_cognitive_recomposition = [
        cognitive_recomposition_assessment(item.baseline) for item in comparisons
    ]
    candidate_cognitive_recomposition = [
        cognitive_recomposition_assessment(item) for item in available_candidates
    ]
    specialist_runtime_coverage = round(
        (
            sum(
                1
                for item in available_candidates
                if item.specialist_subflow_runtime_mode == "langgraph_subflow"
            )
            / len(available_candidates)
        )
        if available_candidates
        else 0.0,
        4,
    )
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
    baseline_matrix = evaluation_matrix([item.baseline for item in comparisons])
    candidate_matrix = evaluation_matrix(available_candidates)
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
        "baseline_workflow_output_decision": summarize_workflow_profile_assessments(
            baseline_workflow_output_assessments
        ),
        "candidate_workflow_output_decision": summarize_workflow_profile_assessments(
            candidate_workflow_output_assessments
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
        "baseline_workflow_output_baseline_rate": workflow_profile_rate(
            baseline_workflow_output_assessments,
            "baseline_saudavel",
        ),
        "candidate_workflow_output_baseline_rate": workflow_profile_rate(
            candidate_workflow_output_assessments,
            "baseline_saudavel",
        ),
        "baseline_workflow_output_maturation_rate": workflow_profile_rate(
            baseline_workflow_output_assessments,
            "maturation_recommended",
        ),
        "candidate_workflow_output_maturation_rate": workflow_profile_rate(
            candidate_workflow_output_assessments,
            "maturation_recommended",
        ),
        "baseline_metacognitive_guidance_decision": summarize_statuses(
            baseline_metacognitive_guidance
        ),
        "candidate_metacognitive_guidance_decision": summarize_statuses(
            candidate_metacognitive_guidance
        ),
        "baseline_metacognitive_guidance_healthy_rate": status_rate(
            baseline_metacognitive_guidance,
            "healthy",
        ),
        "candidate_metacognitive_guidance_healthy_rate": status_rate(
            candidate_metacognitive_guidance,
            "healthy",
        ),
        "baseline_mind_disagreement_decision": summarize_statuses(
            baseline_mind_disagreement
        ),
        "candidate_mind_disagreement_decision": summarize_statuses(
            candidate_mind_disagreement
        ),
        "baseline_mind_validation_checkpoint_decision": summarize_statuses(
            baseline_mind_validation_checkpoint
        ),
        "candidate_mind_validation_checkpoint_decision": summarize_statuses(
            candidate_mind_validation_checkpoint
        ),
        "baseline_adaptive_intervention_decision": summarize_statuses(
            baseline_adaptive_intervention
        ),
        "candidate_adaptive_intervention_decision": summarize_statuses(
            candidate_adaptive_intervention
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
        "baseline_memory_lifecycle_decision": summarize_statuses(
            baseline_memory_lifecycle
        ),
        "candidate_memory_lifecycle_decision": summarize_statuses(
            candidate_memory_lifecycle
        ),
        "baseline_memory_lifecycle_retained_rate": status_rate(
            baseline_memory_lifecycle,
            "retained",
        ),
        "candidate_memory_lifecycle_retained_rate": status_rate(
            candidate_memory_lifecycle,
            "retained",
        ),
        "baseline_memory_lifecycle_review_rate": status_rate(
            baseline_memory_lifecycle,
            "review_recommended",
        ),
        "candidate_memory_lifecycle_review_rate": status_rate(
            candidate_memory_lifecycle,
            "review_recommended",
        ),
        "baseline_memory_corpus_decision": summarize_statuses(
            baseline_memory_corpus
        ),
        "candidate_memory_corpus_decision": summarize_statuses(
            candidate_memory_corpus
        ),
        "baseline_workflow_checkpoint_decision": summarize_statuses(
            baseline_workflow_checkpoint
        ),
        "candidate_workflow_checkpoint_decision": summarize_statuses(
            candidate_workflow_checkpoint
        ),
        "baseline_workflow_checkpoint_healthy_rate": status_rate(
            baseline_workflow_checkpoint,
            "healthy",
        ),
        "candidate_workflow_checkpoint_healthy_rate": status_rate(
            candidate_workflow_checkpoint,
            "healthy",
        ),
        "baseline_workflow_resume_decision": summarize_statuses(
            baseline_workflow_resume
        ),
        "candidate_workflow_resume_decision": summarize_statuses(
            candidate_workflow_resume
        ),
        "baseline_workflow_resume_available_rate": status_rate(
            baseline_workflow_resume,
            "resume_available",
        ),
        "candidate_workflow_resume_available_rate": status_rate(
            candidate_workflow_resume,
            "resume_available",
        ),
        "baseline_procedural_artifact_decision": summarize_statuses(
            baseline_procedural_artifact
        ),
        "candidate_procedural_artifact_decision": summarize_statuses(
            candidate_procedural_artifact
        ),
        "baseline_procedural_artifact_reusable_rate": status_rate(
            baseline_procedural_artifact,
            "reusable",
        ),
        "candidate_procedural_artifact_reusable_rate": status_rate(
            candidate_procedural_artifact,
            "reusable",
        ),
        "baseline_procedural_artifact_candidate_rate": status_rate(
            baseline_procedural_artifact,
            "candidate",
        ),
        "candidate_procedural_artifact_candidate_rate": status_rate(
            candidate_procedural_artifact,
            "candidate",
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
        "baseline_mind_domain_specialist_chain_decision": summarize_statuses(
            baseline_mind_domain_specialist_chain
        ),
        "candidate_mind_domain_specialist_chain_decision": summarize_statuses(
            candidate_mind_domain_specialist_chain
        ),
        "baseline_mind_domain_specialist_chain_alignment_rate": status_rate(
            baseline_mind_domain_specialist_chain,
            "aligned",
        ),
        "candidate_mind_domain_specialist_chain_alignment_rate": status_rate(
            candidate_mind_domain_specialist_chain,
            "aligned",
        ),
        "baseline_specialist_subflow_decision": summarize_statuses(
            baseline_specialist_subflow
        ),
        "candidate_specialist_subflow_decision": summarize_statuses(
            candidate_specialist_subflow
        ),
        "baseline_specialist_subflow_healthy_rate": status_rate(
            baseline_specialist_subflow,
            "healthy",
        ),
        "candidate_specialist_subflow_healthy_rate": status_rate(
            candidate_specialist_subflow,
            "healthy",
        ),
        "candidate_specialist_runtime_coverage": specialist_runtime_coverage,
        "baseline_mission_runtime_state_decision": summarize_statuses(
            baseline_mission_runtime_state
        ),
        "candidate_mission_runtime_state_decision": summarize_statuses(
            candidate_mission_runtime_state
        ),
        "baseline_mission_runtime_state_healthy_rate": status_rate(
            baseline_mission_runtime_state,
            "healthy",
        ),
        "candidate_mission_runtime_state_healthy_rate": status_rate(
            candidate_mission_runtime_state,
            "healthy",
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
        "baseline_refinement_vectors": aggregate_refinement_vectors(
            [item.baseline for item in comparisons]
        ),
        "candidate_refinement_vectors": aggregate_refinement_vectors(
            available_candidates
        ),
        "baseline_evaluation_matrix": baseline_matrix,
        "candidate_evaluation_matrix": candidate_matrix,
        "baseline_wave_two_readiness_matrix": wave_two_readiness_matrix(
            baseline_matrix
        ),
        "candidate_wave_two_readiness_matrix": wave_two_readiness_matrix(
            candidate_matrix
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
    if any(item == "resume_blocked" for item in statuses):
        return "resume_blocked"
    if any(item == "manual_resume_required" for item in statuses):
        return "manual_resume_required"
    if any(item == "attention_required" for item in statuses):
        return "attention_required"
    if any(item == "deep_review_required" for item in statuses):
        return "deep_review_required"
    if any(item == "insufficient" for item in statuses):
        return "insufficient"
    if any(item == "incomplete" for item in statuses):
        return "incomplete"
    if any(item == "effective" for item in statuses):
        return "effective"
    if any(item == "validation_required" for item in statuses):
        return "validation_required"
    if any(item == "review_recommended" for item in statuses):
        return "review_recommended"
    if any(item == "monitor" for item in statuses):
        return "monitor"
    if any(item == "candidate" for item in statuses):
        return "candidate"
    if any(item == "blocked" for item in statuses):
        return "blocked"
    if any(item == "contained" for item in statuses):
        return "contained"
    if any(item == "stable" for item in statuses):
        return "stable"
    if any(item == "retained" for item in statuses):
        return "retained"
    if any(item == "promoted" for item in statuses):
        return "promoted"
    if any(item == "resume_available" for item in statuses):
        return "resume_available"
    if any(item == "reusable" for item in statuses):
        return "reusable"
    if any(item == "aligned" for item in statuses):
        return "aligned"
    if any(item == "fresh_start" for item in statuses):
        return "fresh_start"
    if any(item == "emerging" for item in statuses):
        return "emerging"
    if any(item == "healthy" for item in statuses):
        return "healthy"
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
            if (
                baseline.workflow_checkpoint_status
                != candidate.workflow_checkpoint_status
            ):
                mismatch_fields.append("workflow_checkpoint_status")
            if baseline.workflow_resume_status != candidate.workflow_resume_status:
                mismatch_fields.append("workflow_resume_status")
            if (
                baseline.workflow_pending_checkpoint_count
                != candidate.workflow_pending_checkpoint_count
            ):
                mismatch_fields.append("workflow_pending_checkpoint_count")
            if baseline.workflow_profile_status != candidate.workflow_profile_status:
                mismatch_fields.append("workflow_profile_status")
            if baseline.workflow_output_status != candidate.workflow_output_status:
                mismatch_fields.append("workflow_output_status")
            if (
                baseline.metacognitive_guidance_status
                != candidate.metacognitive_guidance_status
            ):
                mismatch_fields.append("metacognitive_guidance_status")
            if baseline.mind_disagreement_status != candidate.mind_disagreement_status:
                mismatch_fields.append("mind_disagreement_status")
            if (
                baseline.mind_validation_checkpoint_status
                != candidate.mind_validation_checkpoint_status
            ):
                mismatch_fields.append("mind_validation_checkpoint_status")
            if baseline.memory_causality_status != candidate.memory_causality_status:
                mismatch_fields.append("memory_causality_status")
            if baseline.memory_lifecycle_status != candidate.memory_lifecycle_status:
                mismatch_fields.append("memory_lifecycle_status")
            if baseline.memory_review_status != candidate.memory_review_status:
                mismatch_fields.append("memory_review_status")
            if baseline.memory_corpus_status != candidate.memory_corpus_status:
                mismatch_fields.append("memory_corpus_status")
            if baseline.memory_retention_pressure != candidate.memory_retention_pressure:
                mismatch_fields.append("memory_retention_pressure")
            if (
                baseline.adaptive_intervention_status
                != candidate.adaptive_intervention_status
            ):
                mismatch_fields.append("adaptive_intervention_status")
            if (
                baseline.adaptive_intervention_selected_action
                != candidate.adaptive_intervention_selected_action
            ):
                mismatch_fields.append("adaptive_intervention_selected_action")
            if (
                baseline.adaptive_intervention_effectiveness
                != candidate.adaptive_intervention_effectiveness
            ):
                mismatch_fields.append("adaptive_intervention_effectiveness")
            if (
                baseline.procedural_artifact_status
                != candidate.procedural_artifact_status
            ):
                mismatch_fields.append("procedural_artifact_status")
            if baseline.procedural_artifact_refs != candidate.procedural_artifact_refs:
                mismatch_fields.append("procedural_artifact_refs")
            if (
                baseline.procedural_artifact_version
                != candidate.procedural_artifact_version
            ):
                mismatch_fields.append("procedural_artifact_version")
            if baseline.primary_mind != candidate.primary_mind:
                mismatch_fields.append("primary_mind")
            if baseline.primary_route != candidate.primary_route:
                mismatch_fields.append("primary_route")
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
                baseline.mind_domain_specialist_chain_status
                != candidate.mind_domain_specialist_chain_status
            ):
                mismatch_fields.append("mind_domain_specialist_chain_status")
            if (
                baseline.mind_domain_specialist_chain
                != candidate.mind_domain_specialist_chain
            ):
                mismatch_fields.append("mind_domain_specialist_chain")
            if baseline.specialist_subflow_status != candidate.specialist_subflow_status:
                mismatch_fields.append("specialist_subflow_status")
            if (
                baseline.mission_runtime_state_status
                != candidate.mission_runtime_state_status
            ):
                mismatch_fields.append("mission_runtime_state_status")
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
            if baseline.semantic_memory_source != candidate.semantic_memory_source:
                mismatch_fields.append("semantic_memory_source")
            if baseline.procedural_memory_source != candidate.procedural_memory_source:
                mismatch_fields.append("procedural_memory_source")
            if baseline.semantic_memory_focus != candidate.semantic_memory_focus:
                mismatch_fields.append("semantic_memory_focus")
            if baseline.procedural_memory_hint != candidate.procedural_memory_hint:
                mismatch_fields.append("procedural_memory_hint")
            if baseline.semantic_memory_effects != candidate.semantic_memory_effects:
                mismatch_fields.append("semantic_memory_effects")
            if baseline.procedural_memory_effects != candidate.procedural_memory_effects:
                mismatch_fields.append("procedural_memory_effects")
            if (
                baseline.semantic_memory_lifecycle
                != candidate.semantic_memory_lifecycle
            ):
                mismatch_fields.append("semantic_memory_lifecycle")
            if (
                baseline.procedural_memory_lifecycle
                != candidate.procedural_memory_lifecycle
            ):
                mismatch_fields.append("procedural_memory_lifecycle")
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
                        "baseline_workflow_checkpoint_status="
                        f"{item['baseline']['workflow_checkpoint_status']}"
                    ),
                    (
                        "baseline_workflow_checkpoint_assessment="
                        f"{item['baseline_workflow_checkpoint_assessment']}"
                    ),
                    (
                        "baseline_workflow_resume_status="
                        f"{item['baseline']['workflow_resume_status']}"
                    ),
                    (
                        "baseline_workflow_resume_assessment="
                        f"{item['baseline_workflow_resume_assessment']}"
                    ),
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
                        "candidate_workflow_checkpoint_status="
                        f"{item['candidate']['workflow_checkpoint_status']}"
                        if item["candidate"]
                        else "candidate_workflow_checkpoint_status=n/a"
                    ),
                    (
                        "candidate_workflow_checkpoint_assessment="
                        f"{item['candidate_workflow_checkpoint_assessment']}"
                        if item["candidate_workflow_checkpoint_assessment"] is not None
                        else "candidate_workflow_checkpoint_assessment=n/a"
                    ),
                    (
                        "candidate_workflow_resume_status="
                        f"{item['candidate']['workflow_resume_status']}"
                        if item["candidate"]
                        else "candidate_workflow_resume_status=n/a"
                    ),
                    (
                        "candidate_workflow_resume_assessment="
                        f"{item['candidate_workflow_resume_assessment']}"
                        if item["candidate_workflow_resume_assessment"] is not None
                        else "candidate_workflow_resume_assessment=n/a"
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
                        "baseline_workflow_output_status="
                        f"{item['baseline']['workflow_output_status']}"
                    ),
                    (
                        "baseline_workflow_output_assessment="
                        f"{item['baseline_workflow_output_assessment']}"
                    ),
                    (
                        "baseline_metacognitive_guidance_status="
                        f"{item['baseline']['metacognitive_guidance_status']}"
                    ),
                    (
                        "baseline_mind_disagreement_status="
                        f"{item['baseline']['mind_disagreement_status']}"
                    ),
                    (
                        "baseline_mind_disagreement_assessment="
                        f"{item['baseline_mind_disagreement_assessment']}"
                    ),
                    (
                        "baseline_mind_validation_checkpoint_status="
                        f"{item['baseline']['mind_validation_checkpoint_status']}"
                    ),
                    (
                        "baseline_mind_validation_checkpoint_assessment="
                        f"{item['baseline_mind_validation_checkpoint_assessment']}"
                    ),
                    (
                        "baseline_adaptive_intervention_status="
                        f"{item['baseline']['adaptive_intervention_status']}"
                    ),
                    (
                        "baseline_adaptive_intervention_selected_action="
                        f"{item['baseline']['adaptive_intervention_selected_action'] or 'none'}"
                    ),
                    (
                        "baseline_adaptive_intervention_assessment="
                        f"{item['baseline_adaptive_intervention_assessment']}"
                    ),
                    (
                        "baseline_memory_causality_status="
                        f"{item['baseline']['memory_causality_status']}"
                    ),
                    (
                        "baseline_memory_lifecycle_status="
                        f"{item['baseline']['memory_lifecycle_status']}"
                    ),
                    (
                        "baseline_memory_corpus_status="
                        f"{item['baseline']['memory_corpus_status']}"
                    ),
                    (
                        "baseline_memory_corpus_assessment="
                        f"{item['baseline_memory_corpus_assessment']}"
                    ),
                    (
                        "baseline_memory_retention_pressure="
                        f"{item['baseline']['memory_retention_pressure'] or 'none'}"
                    ),
                    (
                        "baseline_procedural_artifact_status="
                        f"{item['baseline']['procedural_artifact_status']}"
                    ),
                    (
                        "baseline_procedural_artifact_assessment="
                        f"{item['baseline_procedural_artifact_assessment']}"
                    ),
                    (
                        "baseline_procedural_artifact_version="
                        f"{item['baseline']['procedural_artifact_version'] or 'none'}"
                    ),
                    (
                        "baseline_primary_mind="
                        f"{item['baseline']['primary_mind'] or 'none'}"
                    ),
                    (
                        "baseline_primary_route="
                        f"{item['baseline']['primary_route'] or 'none'}"
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
                        "baseline_mind_domain_specialist_chain_status="
                        f"{item['baseline']['mind_domain_specialist_chain_status']}"
                    ),
                    (
                        "baseline_specialist_subflow_status="
                        f"{item['baseline']['specialist_subflow_status']}"
                    ),
                    (
                        "baseline_mission_runtime_state_status="
                        f"{item['baseline']['mission_runtime_state_status']}"
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
                        "candidate_workflow_output_status="
                        f"{item['candidate']['workflow_output_status']}"
                        if item["candidate"] is not None
                        else "candidate_workflow_output_status=n/a"
                    ),
                    (
                        "candidate_workflow_output_assessment="
                        f"{item['candidate_workflow_output_assessment']}"
                        if item["candidate_workflow_output_assessment"] is not None
                        else "candidate_workflow_output_assessment=n/a"
                    ),
                    (
                        "candidate_metacognitive_guidance_status="
                        f"{item['candidate']['metacognitive_guidance_status']}"
                        if item["candidate"]
                        else "candidate_metacognitive_guidance_status=n/a"
                    ),
                    (
                        "candidate_mind_disagreement_status="
                        f"{item['candidate']['mind_disagreement_status']}"
                        if item["candidate"]
                        else "candidate_mind_disagreement_status=n/a"
                    ),
                    (
                        "candidate_mind_disagreement_assessment="
                        f"{item['candidate_mind_disagreement_assessment']}"
                        if item["candidate_mind_disagreement_assessment"] is not None
                        else "candidate_mind_disagreement_assessment=n/a"
                    ),
                    (
                        "candidate_mind_validation_checkpoint_status="
                        f"{item['candidate']['mind_validation_checkpoint_status']}"
                        if item["candidate"]
                        else "candidate_mind_validation_checkpoint_status=n/a"
                    ),
                    (
                        "candidate_mind_validation_checkpoint_assessment="
                        f"{item['candidate_mind_validation_checkpoint_assessment']}"
                        if item["candidate_mind_validation_checkpoint_assessment"] is not None
                        else "candidate_mind_validation_checkpoint_assessment=n/a"
                    ),
                    (
                        "candidate_adaptive_intervention_status="
                        f"{item['candidate']['adaptive_intervention_status']}"
                        if item["candidate"]
                        else "candidate_adaptive_intervention_status=n/a"
                    ),
                    (
                        "candidate_adaptive_intervention_selected_action="
                        f"{item['candidate']['adaptive_intervention_selected_action'] or 'none'}"
                        if item["candidate"]
                        else "candidate_adaptive_intervention_selected_action=n/a"
                    ),
                    (
                        "candidate_adaptive_intervention_assessment="
                        f"{item['candidate_adaptive_intervention_assessment']}"
                        if item["candidate_adaptive_intervention_assessment"] is not None
                        else "candidate_adaptive_intervention_assessment=n/a"
                    ),
                    (
                        "candidate_memory_causality_status="
                        f"{item['candidate']['memory_causality_status']}"
                        if item["candidate"]
                        else "candidate_memory_causality_status=n/a"
                    ),
                    (
                        "candidate_memory_lifecycle_status="
                        f"{item['candidate']['memory_lifecycle_status']}"
                        if item["candidate"]
                        else "candidate_memory_lifecycle_status=n/a"
                    ),
                    (
                        "candidate_memory_corpus_status="
                        f"{item['candidate']['memory_corpus_status']}"
                        if item["candidate"]
                        else "candidate_memory_corpus_status=n/a"
                    ),
                    (
                        "candidate_memory_corpus_assessment="
                        f"{item['candidate_memory_corpus_assessment']}"
                        if item["candidate_memory_corpus_assessment"] is not None
                        else "candidate_memory_corpus_assessment=n/a"
                    ),
                    (
                        "candidate_memory_retention_pressure="
                        f"{item['candidate']['memory_retention_pressure'] or 'none'}"
                        if item["candidate"]
                        else "candidate_memory_retention_pressure=n/a"
                    ),
                    (
                        "candidate_procedural_artifact_status="
                        f"{item['candidate']['procedural_artifact_status']}"
                        if item["candidate"]
                        else "candidate_procedural_artifact_status=n/a"
                    ),
                    (
                        "candidate_procedural_artifact_assessment="
                        f"{item['candidate_procedural_artifact_assessment']}"
                        if item["candidate_procedural_artifact_assessment"] is not None
                        else "candidate_procedural_artifact_assessment=n/a"
                    ),
                    (
                        "candidate_procedural_artifact_version="
                        f"{item['candidate']['procedural_artifact_version'] or 'none'}"
                        if item["candidate"]
                        else "candidate_procedural_artifact_version=n/a"
                    ),
                    (
                        "candidate_primary_mind="
                        f"{item['candidate']['primary_mind'] or 'none'}"
                        if item["candidate"]
                        else "candidate_primary_mind=n/a"
                    ),
                    (
                        "candidate_primary_route="
                        f"{item['candidate']['primary_route'] or 'none'}"
                        if item["candidate"]
                        else "candidate_primary_route=n/a"
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
                        "candidate_mind_domain_specialist_chain_status="
                        f"{item['candidate']['mind_domain_specialist_chain_status']}"
                        if item["candidate"]
                        else "candidate_mind_domain_specialist_chain_status=n/a"
                    ),
                    (
                        "candidate_specialist_subflow_status="
                        f"{item['candidate']['specialist_subflow_status']}"
                        if item["candidate"]
                        else "candidate_specialist_subflow_status=n/a"
                    ),
                    (
                        "candidate_mission_runtime_state_status="
                        f"{item['candidate']['mission_runtime_state_status']}"
                        if item["candidate"]
                        else "candidate_mission_runtime_state_status=n/a"
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
                    (
                        "baseline_refinement_axes="
                        f"{vector_axes(item['baseline_refinement_vectors'])}"
                    ),
                    (
                        "candidate_refinement_axes="
                        f"{vector_axes(item['candidate_refinement_vectors'])}"
                        if item["candidate"]
                        else "candidate_refinement_axes=n/a"
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
                "baseline_workflow_output_decision="
                f"{summary['baseline_workflow_output_decision']}",
                "candidate_workflow_output_decision="
                f"{summary['candidate_workflow_output_decision']}",
                "baseline_workflow_baseline_rate="
                f"{summary['baseline_workflow_baseline_rate']}",
                "baseline_workflow_maturation_rate="
                f"{summary['baseline_workflow_maturation_rate']}",
                "candidate_workflow_baseline_rate="
                f"{summary['candidate_workflow_baseline_rate']}",
                "candidate_workflow_maturation_rate="
                f"{summary['candidate_workflow_maturation_rate']}",
                "baseline_workflow_output_baseline_rate="
                f"{summary['baseline_workflow_output_baseline_rate']}",
                "baseline_workflow_output_maturation_rate="
                f"{summary['baseline_workflow_output_maturation_rate']}",
                "candidate_workflow_output_baseline_rate="
                f"{summary['candidate_workflow_output_baseline_rate']}",
                "candidate_workflow_output_maturation_rate="
                f"{summary['candidate_workflow_output_maturation_rate']}",
                "baseline_metacognitive_guidance_decision="
                f"{summary['baseline_metacognitive_guidance_decision']}",
                "candidate_metacognitive_guidance_decision="
                f"{summary['candidate_metacognitive_guidance_decision']}",
                "baseline_metacognitive_guidance_healthy_rate="
                f"{summary['baseline_metacognitive_guidance_healthy_rate']}",
                "candidate_metacognitive_guidance_healthy_rate="
                f"{summary['candidate_metacognitive_guidance_healthy_rate']}",
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
                "baseline_memory_lifecycle_decision="
                f"{summary['baseline_memory_lifecycle_decision']}",
                "candidate_memory_lifecycle_decision="
                f"{summary['candidate_memory_lifecycle_decision']}",
                "baseline_memory_lifecycle_retained_rate="
                f"{summary['baseline_memory_lifecycle_retained_rate']}",
                "candidate_memory_lifecycle_retained_rate="
                f"{summary['candidate_memory_lifecycle_retained_rate']}",
                "baseline_memory_lifecycle_review_rate="
                f"{summary['baseline_memory_lifecycle_review_rate']}",
                "candidate_memory_lifecycle_review_rate="
                f"{summary['candidate_memory_lifecycle_review_rate']}",
                "baseline_mind_disagreement_decision="
                f"{summary['baseline_mind_disagreement_decision']}",
                "candidate_mind_disagreement_decision="
                f"{summary['candidate_mind_disagreement_decision']}",
                "baseline_mind_validation_checkpoint_decision="
                f"{summary['baseline_mind_validation_checkpoint_decision']}",
                "candidate_mind_validation_checkpoint_decision="
                f"{summary['candidate_mind_validation_checkpoint_decision']}",
                "baseline_adaptive_intervention_decision="
                f"{summary['baseline_adaptive_intervention_decision']}",
                "candidate_adaptive_intervention_decision="
                f"{summary['candidate_adaptive_intervention_decision']}",
                "baseline_memory_corpus_decision="
                f"{summary['baseline_memory_corpus_decision']}",
                "candidate_memory_corpus_decision="
                f"{summary['candidate_memory_corpus_decision']}",
                "baseline_workflow_checkpoint_decision="
                f"{summary['baseline_workflow_checkpoint_decision']}",
                "candidate_workflow_checkpoint_decision="
                f"{summary['candidate_workflow_checkpoint_decision']}",
                "baseline_workflow_checkpoint_healthy_rate="
                f"{summary['baseline_workflow_checkpoint_healthy_rate']}",
                "candidate_workflow_checkpoint_healthy_rate="
                f"{summary['candidate_workflow_checkpoint_healthy_rate']}",
                "baseline_workflow_resume_decision="
                f"{summary['baseline_workflow_resume_decision']}",
                "candidate_workflow_resume_decision="
                f"{summary['candidate_workflow_resume_decision']}",
                "baseline_workflow_resume_available_rate="
                f"{summary['baseline_workflow_resume_available_rate']}",
                "candidate_workflow_resume_available_rate="
                f"{summary['candidate_workflow_resume_available_rate']}",
                "baseline_procedural_artifact_decision="
                f"{summary['baseline_procedural_artifact_decision']}",
                "candidate_procedural_artifact_decision="
                f"{summary['candidate_procedural_artifact_decision']}",
                "baseline_procedural_artifact_reusable_rate="
                f"{summary['baseline_procedural_artifact_reusable_rate']}",
                "candidate_procedural_artifact_reusable_rate="
                f"{summary['candidate_procedural_artifact_reusable_rate']}",
                "baseline_procedural_artifact_candidate_rate="
                f"{summary['baseline_procedural_artifact_candidate_rate']}",
                "candidate_procedural_artifact_candidate_rate="
                f"{summary['candidate_procedural_artifact_candidate_rate']}",
                "baseline_mind_domain_specialist_decision="
                f"{summary['baseline_mind_domain_specialist_decision']}",
                "candidate_mind_domain_specialist_decision="
                f"{summary['candidate_mind_domain_specialist_decision']}",
                "baseline_mind_domain_specialist_alignment_rate="
                f"{summary['baseline_mind_domain_specialist_alignment_rate']}",
                "candidate_mind_domain_specialist_alignment_rate="
                f"{summary['candidate_mind_domain_specialist_alignment_rate']}",
                "baseline_mind_domain_specialist_chain_decision="
                f"{summary['baseline_mind_domain_specialist_chain_decision']}",
                "candidate_mind_domain_specialist_chain_decision="
                f"{summary['candidate_mind_domain_specialist_chain_decision']}",
                "baseline_mind_domain_specialist_chain_alignment_rate="
                f"{summary['baseline_mind_domain_specialist_chain_alignment_rate']}",
                "candidate_mind_domain_specialist_chain_alignment_rate="
                f"{summary['candidate_mind_domain_specialist_chain_alignment_rate']}",
                "baseline_specialist_subflow_decision="
                f"{summary['baseline_specialist_subflow_decision']}",
                "candidate_specialist_subflow_decision="
                f"{summary['candidate_specialist_subflow_decision']}",
                "baseline_specialist_subflow_healthy_rate="
                f"{summary['baseline_specialist_subflow_healthy_rate']}",
                "candidate_specialist_subflow_healthy_rate="
                f"{summary['candidate_specialist_subflow_healthy_rate']}",
                "candidate_specialist_runtime_coverage="
                f"{summary['candidate_specialist_runtime_coverage']}",
                "baseline_mission_runtime_state_decision="
                f"{summary['baseline_mission_runtime_state_decision']}",
                "candidate_mission_runtime_state_decision="
                f"{summary['candidate_mission_runtime_state_decision']}",
                "baseline_mission_runtime_state_healthy_rate="
                f"{summary['baseline_mission_runtime_state_healthy_rate']}",
                "candidate_mission_runtime_state_healthy_rate="
                f"{summary['candidate_mission_runtime_state_healthy_rate']}",
                "baseline_cognitive_recomposition_decision="
                f"{summary['baseline_cognitive_recomposition_decision']}",
                "candidate_cognitive_recomposition_decision="
                f"{summary['candidate_cognitive_recomposition_decision']}",
                "baseline_cognitive_recomposition_coherent_rate="
                f"{summary['baseline_cognitive_recomposition_coherent_rate']}",
                "candidate_cognitive_recomposition_coherent_rate="
                f"{summary['candidate_cognitive_recomposition_coherent_rate']}",
                "baseline_refinement_axes="
                f"{vector_axes(summary['baseline_refinement_vectors'])}",
                "candidate_refinement_axes="
                f"{vector_axes(summary['candidate_refinement_vectors'])}",
                "baseline_evaluation_matrix_workflows="
                f"{matrix_workflows(summary['baseline_evaluation_matrix'])}",
                "candidate_evaluation_matrix_workflows="
                f"{matrix_workflows(summary['candidate_evaluation_matrix'])}",
                "baseline_wave_two_readiness="
                f"{wave_two_readiness_summary(summary['baseline_evaluation_matrix'])}",
                "candidate_wave_two_readiness="
                f"{wave_two_readiness_summary(summary['candidate_evaluation_matrix'])}",
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
                "baseline_workflow_output_assessment": workflow_output_assessment(
                    item.baseline
                ),
                "baseline_metacognitive_guidance_assessment": (
                    metacognitive_guidance_assessment(item.baseline)
                ),
                "baseline_workflow_checkpoint_assessment": workflow_checkpoint_assessment(
                    item.baseline
                ),
                "baseline_workflow_resume_assessment": workflow_resume_assessment(
                    item.baseline
                ),
                "baseline_mind_disagreement_assessment": mind_disagreement_assessment(
                    item.baseline
                ),
                "baseline_mind_validation_checkpoint_assessment": (
                    mind_validation_checkpoint_assessment(item.baseline)
                ),
                "baseline_adaptive_intervention_assessment": (
                    adaptive_intervention_assessment(item.baseline)
                ),
                "baseline_memory_causality_assessment": memory_causality_assessment(
                    item.baseline
                ),
                "baseline_memory_lifecycle_assessment": memory_lifecycle_assessment(
                    item.baseline
                ),
                "baseline_memory_corpus_assessment": memory_corpus_assessment(
                    item.baseline
                ),
                "baseline_procedural_artifact_assessment": procedural_artifact_assessment(
                    item.baseline
                ),
                "baseline_mind_domain_specialist_assessment": (
                    mind_domain_specialist_assessment(item.baseline)
                ),
                "baseline_mind_domain_specialist_chain_assessment": (
                    mind_domain_specialist_chain_assessment(item.baseline)
                ),
                "baseline_specialist_subflow_assessment": specialist_subflow_assessment(
                    item.baseline
                ),
                "baseline_mission_runtime_state_assessment": (
                    mission_runtime_state_assessment(item.baseline)
                ),
                "baseline_cognitive_recomposition_assessment": (
                    cognitive_recomposition_assessment(item.baseline)
                ),
                "baseline_refinement_vectors": refinement_vectors(item.baseline),
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
                "candidate_workflow_output_assessment": (
                    workflow_output_assessment(item.candidate) if item.candidate else None
                ),
                "candidate_metacognitive_guidance_assessment": (
                    metacognitive_guidance_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_workflow_checkpoint_assessment": (
                    workflow_checkpoint_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_workflow_resume_assessment": (
                    workflow_resume_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_mind_disagreement_assessment": (
                    mind_disagreement_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_mind_validation_checkpoint_assessment": (
                    mind_validation_checkpoint_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_adaptive_intervention_assessment": (
                    adaptive_intervention_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_memory_causality_assessment": (
                    memory_causality_assessment(item.candidate) if item.candidate else None
                ),
                "candidate_memory_lifecycle_assessment": (
                    memory_lifecycle_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_memory_corpus_assessment": (
                    memory_corpus_assessment(item.candidate) if item.candidate else None
                ),
                "candidate_procedural_artifact_assessment": (
                    procedural_artifact_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_mind_domain_specialist_assessment": (
                    mind_domain_specialist_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_mind_domain_specialist_chain_assessment": (
                    mind_domain_specialist_chain_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_specialist_subflow_assessment": (
                    specialist_subflow_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_mission_runtime_state_assessment": (
                    mission_runtime_state_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_cognitive_recomposition_assessment": (
                    cognitive_recomposition_assessment(item.candidate)
                    if item.candidate
                    else None
                ),
                "candidate_refinement_vectors": (
                    refinement_vectors(item.candidate) if item.candidate else []
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
