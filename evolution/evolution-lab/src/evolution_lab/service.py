# ruff: noqa: E501
"""Local evolution lab for sandbox-only comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from os import getenv
from pathlib import Path
from uuid import uuid4

from evolution_lab.repository import EvolutionLabRepository
from shared.contracts import EvolutionDecisionContract, EvolutionProposalContract
from shared.eval_expansion import derive_expanded_eval_state
from shared.types import EvolutionDecisionId, EvolutionProposalId

DEFAULT_EVOLUTION_STRATEGY = "manual_variants"
SUPPORTED_EVOLUTION_STRATEGIES = (
    "manual_variants",
    "mipro_like_search",
    "textgrad_like_refinement",
)


@dataclass(frozen=True)
class ComparisonInput:
    """Input payload for comparing a candidate against the current baseline."""

    baseline_label: str
    candidate_label: str
    baseline_metrics: dict[str, float]
    candidate_metrics: dict[str, float]
    governance_refs: list[str]
    notes: list[str]
    strategy_name: str | None = None
    selection_criteria: dict[str, object] = field(default_factory=dict)
    candidate_refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FlowEvaluationInput:
    """Operational flow evaluation used to seed sandbox proposals and comparisons."""

    request_id: str
    session_id: str | None
    mission_id: str | None
    governance_decision: str | None
    operation_status: str | None
    total_events: int
    duration_seconds: float
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None = None
    continuity_source: str | None = None
    continuity_runtime_mode: str | None = None
    specialist_subflow_status: str | None = None
    mission_runtime_state_status: str | None = None
    registry_domains: list[str] = field(default_factory=list)
    shadow_specialists: list[str] = field(default_factory=list)
    domain_alignment_status: str | None = None
    mind_alignment_status: str | None = None
    identity_alignment_status: str | None = None
    memory_alignment_status: str | None = None
    specialist_sovereignty_status: str | None = None
    axis_gate_status: str | None = None
    workflow_profile_status: str | None = None
    workflow_output_status: str | None = None
    metacognitive_guidance_status: str | None = None
    mind_disagreement_status: str | None = None
    mind_validation_checkpoint_status: str | None = None
    adaptive_intervention_status: str | None = None
    adaptive_intervention_selected_action: str | None = None
    adaptive_intervention_effectiveness: str | None = None
    adaptive_intervention_policy_status: str | None = None
    memory_causality_status: str | None = None
    memory_maintenance_status: str | None = None
    memory_maintenance_effectiveness: str | None = None
    context_compaction_status: str | None = None
    cross_session_recall_status: str | None = None
    primary_mind: str | None = None
    primary_route: str | None = None
    dominant_tension: str | None = None
    arbitration_source: str | None = None
    primary_domain_driver: str | None = None
    mind_domain_specialist_status: str | None = None
    mind_domain_specialist_chain_status: str | None = None
    mind_domain_specialist_effectiveness: str | None = None
    mind_domain_specialist_mismatch_flags: list[str] = field(default_factory=list)
    semantic_memory_source: str | None = None
    procedural_memory_source: str | None = None
    semantic_memory_lifecycle: str | None = None
    procedural_memory_lifecycle: str | None = None
    memory_lifecycle_status: str | None = None
    memory_review_status: str | None = None
    memory_corpus_status: str | None = None
    memory_retention_pressure: str | None = None
    cognitive_recomposition_applied: bool = False
    cognitive_recomposition_reason: str | None = None
    cognitive_recomposition_trigger: str | None = None
    continuity_trace_status: str | None = None
    missing_continuity_signals: list[str] = field(default_factory=list)
    continuity_anomaly_flags: list[str] = field(default_factory=list)
    workflow_checkpoint_status: str | None = None
    workflow_resume_status: str | None = None
    workflow_pending_checkpoint_count: int = 0
    procedural_artifact_status: str | None = None
    procedural_artifact_ref_count: int = 0
    procedural_artifact_version: int | None = None
    capability_decision_status: str | None = None
    capability_decision_selected_mode: str | None = None
    capability_authorization_status: str | None = None
    capability_decision_tool_class: str | None = None
    capability_decision_handoff_mode: str | None = None
    capability_effectiveness: str | None = None
    handoff_adapter_status: str | None = None
    request_identity_status: str | None = None
    mission_policy_status: str | None = None
    request_identity_mismatch_flags: list[str] = field(default_factory=list)
    expanded_eval_status: str | None = None
    surface_axis_status: str | None = None
    ecosystem_state_status: str | None = None
    experiment_lane_status: str | None = None
    wave2_candidate_class: str | None = None
    experiment_entry_status: str | None = None
    experiment_exit_status: str | None = None
    promotion_readiness: str | None = None


@dataclass(frozen=True)
class EvolutionComparisonResult:
    """Structured output for a sandbox comparison."""

    proposal: EvolutionProposalContract
    decision: EvolutionDecisionContract
    metric_deltas: dict[str, float]


class EvolutionLabService:
    """Persist proposals and compare candidates without automatic promotion."""

    name = "evolution-lab"

    def __init__(self, database_path: str | None = None) -> None:
        runtime_path = database_path or getenv("JARVIS_EVOLUTION_DB")
        resolved = (
            Path(runtime_path) if runtime_path else Path.cwd() / ".jarvis_runtime" / "evolution.db"
        )
        self.repository = EvolutionLabRepository(resolved)

    def create_proposal(
        self,
        *,
        proposal_type: str,
        target_scope: str,
        hypothesis: str,
        expected_gain: str,
        baseline_refs: list[str],
        source_signals: list[str] | None = None,
        risk_hint: str | None = None,
        proposed_tests: list[str] | None = None,
        strategy_name: str | None = None,
        candidate_refs: list[str] | None = None,
        refinement_vectors: list[dict[str, object]] | None = None,
        evaluation_matrix: dict[str, dict[str, object]] | None = None,
        selection_criteria: dict[str, object] | None = None,
        strategy_context: dict[str, object] | None = None,
    ) -> EvolutionProposalContract:
        """Register a sandbox proposal for later comparison."""

        chosen_strategy = self.resolve_strategy_name(strategy_name)
        strategy_signal = f"strategy://{chosen_strategy}"
        signals = list(source_signals or [])
        if strategy_signal not in signals:
            signals.append(strategy_signal)

        proposal = EvolutionProposalContract(
            evolution_proposal_id=EvolutionProposalId(f"evo-proposal-{uuid4().hex[:8]}"),
            proposal_type=proposal_type,
            target_scope=target_scope,
            hypothesis=hypothesis,
            expected_gain=expected_gain,
            timestamp=self.now(),
            source_signals=signals,
            baseline_refs=baseline_refs,
            risk_hint=risk_hint,
            requires_sandbox=True,
            proposed_tests=proposed_tests or [],
            promotion_constraints=[
                "manual_review_required",
                "no_automatic_promotion",
                "rollback_plan_mandatory",
                f"preferred_strategy={chosen_strategy}",
            ],
            candidate_refs=list(candidate_refs or []),
            refinement_vectors=list(refinement_vectors or []),
            evaluation_matrix=dict(evaluation_matrix or {}),
            selection_criteria=dict(selection_criteria or {}),
            strategy_context=dict(strategy_context or {}),
        )
        self.repository.record_proposal(proposal)
        return proposal

    def compare_candidate(
        self,
        proposal: EvolutionProposalContract,
        comparison: ComparisonInput,
    ) -> EvolutionComparisonResult:
        """Compare a candidate against the baseline and keep the outcome sandbox-only."""

        chosen_strategy = self.resolve_strategy_name(comparison.strategy_name)
        selection_criteria = dict(
            comparison.selection_criteria or self._selection_criteria(chosen_strategy)
        )
        metric_deltas = {
            key: round(
                comparison.candidate_metrics.get(key, 0.0)
                - comparison.baseline_metrics.get(key, 0.0),
                4,
            )
            for key in sorted(set(comparison.baseline_metrics) | set(comparison.candidate_metrics))
        }
        stability_score = round(comparison.candidate_metrics.get("stability", 0.0), 4)
        risk_score = round(comparison.candidate_metrics.get("risk", 0.0), 4)
        improved = sum(1 for value in metric_deltas.values() if value > 0)
        degraded = sum(1 for value in metric_deltas.values() if value < 0)
        candidate_meets_selection = self._candidate_meets_selection_criteria(
            selection_criteria=selection_criteria,
            baseline_metrics=comparison.baseline_metrics,
            candidate_metrics=comparison.candidate_metrics,
            metric_deltas=metric_deltas,
        )
        decision_name = (
            "sandbox_candidate"
            if improved >= degraded
            and risk_score <= comparison.baseline_metrics.get("risk", risk_score)
            and candidate_meets_selection
            else "hold_baseline"
        )
        summary = (
            f"baseline={comparison.baseline_label}; candidate={comparison.candidate_label}; "
            f"strategy={chosen_strategy}; improved_metrics={improved}; degraded_metrics={degraded}; "
            f"stability={stability_score}; risk={risk_score}; "
            f"selection_ok={candidate_meets_selection}"
        )
        decision = EvolutionDecisionContract(
            evolution_decision_id=EvolutionDecisionId(f"evo-decision-{uuid4().hex[:8]}"),
            evolution_proposal_id=proposal.evolution_proposal_id,
            decision=decision_name,
            comparison_summary=summary,
            timestamp=self.now(),
            promoted_to=None,
            rollback_plan_ref=f"sandbox://rollback/{comparison.baseline_label}",
            governance_refs=comparison.governance_refs,
            stability_score=stability_score,
            risk_score=risk_score,
            notes=comparison.notes
            + [
                f"strategy={chosen_strategy}",
                f"metric_deltas={metric_deltas}",
                f"selection_criteria={selection_criteria}",
            ],
            baseline_label=comparison.baseline_label,
            candidate_label=comparison.candidate_label,
            selected_candidate_label=(
                comparison.candidate_label if decision_name == "sandbox_candidate" else None
            ),
            selection_criteria=selection_criteria,
            baseline_metrics=dict(comparison.baseline_metrics),
            candidate_metrics=dict(comparison.candidate_metrics),
            metric_deltas=metric_deltas,
        )
        self.repository.record_decision(decision)
        return EvolutionComparisonResult(
            proposal=proposal,
            decision=decision,
            metric_deltas=metric_deltas,
        )

    def create_proposal_from_flow_evaluation(
        self,
        evaluation: FlowEvaluationInput,
        *,
        target_scope: str,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a sandbox proposal from a pilot or runtime flow evaluation."""

        requires_refinement = self._requires_refinement(evaluation)
        hypothesis = (
            "Flow anomalies and alignment drifts should be reduced without relaxing governance "
            "or traceability."
            if requires_refinement
            else "Healthy flows may support a safer candidate path under the same controls."
        )
        expected_gain = (
            "Reduce trace gaps, workflow maturity drifts and route-alignment anomalies in the "
            "observed flow."
            if requires_refinement
            else "Preserve flow health while improving execution quality."
        )
        refinement_vectors = self._refinement_vectors_from_flow_evaluation(evaluation)
        evaluation_matrix = self._evaluation_matrix_from_flow_evaluation(evaluation)
        wave_two_readiness = self._wave_two_readiness_matrix_from_evaluation(evaluation)
        resolved_strategy = self.resolve_strategy_name(strategy_name)
        selection_criteria = self._selection_criteria(resolved_strategy)
        if refinement_vectors:
            top_vector = refinement_vectors[0]
            hypothesis = (
                f"{hypothesis} Prioritize {top_vector['axis']} on "
                f"{top_vector['workflow_profile']}."
            )
            expected_gain = (
                f"{expected_gain} Next gain: {top_vector['recommendation']}."
            )
        source_signals = [
            f"observability://request/{evaluation.request_id}",
            f"governance://decision/{evaluation.governance_decision or 'unknown'}",
        ]
        if evaluation.session_id:
            source_signals.append(f"observability://session/{evaluation.session_id}")
        if evaluation.mission_id:
            source_signals.append(f"observability://mission/{evaluation.mission_id}")
        if evaluation.continuity_action:
            source_signals.append(f"continuity://action/{evaluation.continuity_action}")
        if evaluation.continuity_runtime_mode:
            source_signals.append(
                f"continuity://runtime/{evaluation.continuity_runtime_mode}"
            )
        for domain in evaluation.registry_domains:
            source_signals.append(f"domain://registry/{domain}")
        for specialist in evaluation.shadow_specialists:
            source_signals.append(f"specialist://shadow/{specialist}")
        if evaluation.domain_alignment_status:
            source_signals.append(f"alignment://domain/{evaluation.domain_alignment_status}")
        if evaluation.mind_alignment_status:
            source_signals.append(f"alignment://mind/{evaluation.mind_alignment_status}")
        if evaluation.identity_alignment_status:
            source_signals.append(
                f"alignment://identity/{evaluation.identity_alignment_status}"
            )
        if evaluation.memory_alignment_status:
            source_signals.append(f"alignment://memory/{evaluation.memory_alignment_status}")
        if evaluation.specialist_sovereignty_status:
            source_signals.append(
                "alignment://specialist-sovereignty/"
                f"{evaluation.specialist_sovereignty_status}"
            )
        if evaluation.axis_gate_status:
            source_signals.append(f"alignment://axis-gate/{evaluation.axis_gate_status}")
        if evaluation.workflow_profile_status:
            source_signals.append(
                f"workflow://profile-status/{evaluation.workflow_profile_status}"
            )
        if evaluation.workflow_output_status:
            source_signals.append(
                f"workflow://output-status/{evaluation.workflow_output_status}"
            )
        if evaluation.metacognitive_guidance_status:
            source_signals.append(
                "mind://metacognitive-guidance/"
                f"{evaluation.metacognitive_guidance_status}"
            )
        if evaluation.mind_disagreement_status:
            source_signals.append(
                f"mind://disagreement/{evaluation.mind_disagreement_status}"
            )
        if evaluation.mind_validation_checkpoint_status:
            source_signals.append(
                "mind://validation-checkpoint/"
                f"{evaluation.mind_validation_checkpoint_status}"
            )
        if evaluation.capability_decision_status:
            source_signals.append(
                f"runtime://capability-decision/{evaluation.capability_decision_status}"
            )
        if evaluation.capability_decision_selected_mode:
            source_signals.append(
                "runtime://capability-mode/"
                f"{evaluation.capability_decision_selected_mode}"
            )
        if evaluation.capability_authorization_status:
            source_signals.append(
                "runtime://capability-authorization/"
                f"{evaluation.capability_authorization_status}"
            )
        if evaluation.capability_decision_tool_class:
            source_signals.append(
                f"runtime://capability-tool-class/{evaluation.capability_decision_tool_class}"
            )
        if evaluation.capability_decision_handoff_mode:
            source_signals.append(
                "runtime://capability-handoff/"
                f"{evaluation.capability_decision_handoff_mode}"
            )
        if evaluation.capability_effectiveness:
            source_signals.append(
                "runtime://capability-effectiveness/"
                f"{evaluation.capability_effectiveness}"
            )
        if evaluation.handoff_adapter_status:
            source_signals.append(
                f"runtime://handoff-adapter/{evaluation.handoff_adapter_status}"
            )
        if evaluation.request_identity_status:
            source_signals.append(
                f"runtime://request-identity/{evaluation.request_identity_status}"
            )
        if evaluation.mission_policy_status:
            source_signals.append(
                f"runtime://mission-policy/{evaluation.mission_policy_status}"
            )
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        source_signals.append(
            f"eval://expanded/{expanded_eval_state['expanded_eval_status']}"
        )
        source_signals.append(
            f"eval://surface-axis/{expanded_eval_state['surface_axis_status']}"
        )
        source_signals.append(
            f"eval://ecosystem-state/{expanded_eval_state['ecosystem_state_status']}"
        )
        source_signals.append(
            f"experiment://lane/{expanded_eval_state['experiment_lane_status']}"
        )
        source_signals.append(
            f"experiment://entry/{expanded_eval_state['experiment_entry_status']}"
        )
        source_signals.append(
            f"experiment://exit/{expanded_eval_state['experiment_exit_status']}"
        )
        source_signals.append(
            f"experiment://promotion/{expanded_eval_state['promotion_readiness']}"
        )
        for mismatch_flag in evaluation.request_identity_mismatch_flags:
            source_signals.append(
                f"runtime://request-identity-mismatch/{mismatch_flag}"
            )
        if evaluation.adaptive_intervention_status:
            source_signals.append(
                "runtime://adaptive-intervention/"
                f"{evaluation.adaptive_intervention_status}"
            )
        if evaluation.adaptive_intervention_selected_action:
            source_signals.append(
                "runtime://adaptive-intervention-action/"
                f"{evaluation.adaptive_intervention_selected_action}"
            )
        if evaluation.adaptive_intervention_effectiveness:
            source_signals.append(
                "runtime://adaptive-intervention-effectiveness/"
                f"{evaluation.adaptive_intervention_effectiveness}"
            )
        if evaluation.adaptive_intervention_policy_status:
            source_signals.append(
                "runtime://adaptive-intervention-policy/"
                f"{evaluation.adaptive_intervention_policy_status}"
            )
        if evaluation.memory_causality_status:
            source_signals.append(
                f"memory://causality/{evaluation.memory_causality_status}"
            )
        if evaluation.memory_maintenance_status:
            source_signals.append(
                f"memory://maintenance/{evaluation.memory_maintenance_status}"
            )
        if evaluation.memory_maintenance_effectiveness:
            source_signals.append(
                "memory://maintenance-effectiveness/"
                f"{evaluation.memory_maintenance_effectiveness}"
            )
        if evaluation.context_compaction_status:
            source_signals.append(
                f"memory://compaction/{evaluation.context_compaction_status}"
            )
        if evaluation.cross_session_recall_status:
            source_signals.append(
                f"memory://cross-session/{evaluation.cross_session_recall_status}"
            )
        if evaluation.semantic_memory_source:
            source_signals.append(
                f"memory://semantic-source/{evaluation.semantic_memory_source}"
            )
        if evaluation.procedural_memory_source:
            source_signals.append(
                f"memory://procedural-source/{evaluation.procedural_memory_source}"
            )
        if evaluation.memory_lifecycle_status:
            source_signals.append(
                f"memory://lifecycle/{evaluation.memory_lifecycle_status}"
            )
        if evaluation.memory_review_status:
            source_signals.append(
                f"memory://review/{evaluation.memory_review_status}"
            )
        if evaluation.memory_corpus_status:
            source_signals.append(
                f"memory://corpus/{evaluation.memory_corpus_status}"
            )
        if evaluation.memory_retention_pressure:
            source_signals.append(
                f"memory://retention-pressure/{evaluation.memory_retention_pressure}"
            )
        if evaluation.primary_mind:
            source_signals.append(f"mind://primary/{evaluation.primary_mind}")
        if evaluation.primary_route:
            source_signals.append(f"domain://primary-route/{evaluation.primary_route}")
        if evaluation.primary_domain_driver:
            source_signals.append(
                f"domain://primary-driver/{evaluation.primary_domain_driver}"
            )
        if evaluation.dominant_tension:
            source_signals.append(f"mind://tension/{evaluation.dominant_tension}")
        if evaluation.arbitration_source:
            source_signals.append(
                f"mind://arbitration-source/{evaluation.arbitration_source}"
            )
        if evaluation.mind_domain_specialist_status:
            source_signals.append(
                "alignment://mind-domain-specialist/"
                f"{evaluation.mind_domain_specialist_status}"
            )
        if evaluation.mind_domain_specialist_chain_status:
            source_signals.append(
                "alignment://mind-domain-specialist-chain/"
                f"{evaluation.mind_domain_specialist_chain_status}"
            )
        if evaluation.mind_domain_specialist_effectiveness:
            source_signals.append(
                "alignment://mind-domain-specialist-effectiveness/"
                f"{evaluation.mind_domain_specialist_effectiveness}"
            )
        for mismatch_flag in evaluation.mind_domain_specialist_mismatch_flags:
            source_signals.append(
                f"alignment://mind-domain-specialist-mismatch/{mismatch_flag}"
            )
        if evaluation.cognitive_recomposition_applied:
            source_signals.append("mind://recomposition/applied")
        if evaluation.cognitive_recomposition_trigger:
            source_signals.append(
                f"mind://recomposition-trigger/{evaluation.cognitive_recomposition_trigger}"
            )
        if evaluation.continuity_trace_status:
            source_signals.append(
                f"continuity://trace-status/{evaluation.continuity_trace_status}"
            )
        if evaluation.workflow_checkpoint_status:
            source_signals.append(
                "workflow://checkpoint-status/"
                f"{evaluation.workflow_checkpoint_status}"
            )
        if evaluation.workflow_resume_status:
            source_signals.append(
                f"workflow://resume-status/{evaluation.workflow_resume_status}"
            )
        if evaluation.procedural_artifact_status:
            source_signals.append(
                f"artifact://procedural-status/{evaluation.procedural_artifact_status}"
            )
        for vector in refinement_vectors[:3]:
            source_signals.append(
                "refinement://"
                f"{vector['priority']}/"
                f"{vector['workflow_profile']}/"
                f"{vector['axis']}"
            )
        return self.create_proposal(
            proposal_type="flow_evaluation_refinement",
            target_scope=target_scope,
            hypothesis=hypothesis,
            expected_gain=expected_gain,
            baseline_refs=[f"trace://{evaluation.request_id}"],
            source_signals=source_signals,
            risk_hint=self._risk_hint_from_flow(evaluation),
            proposed_tests=["python tools/go_live_internal_checklist.py --profile controlled"],
            strategy_name=strategy_name,
            candidate_refs=(
                [f"trace://{evaluation.request_id}"]
                + (
                    [f"artifact://procedural/{evaluation.request_id}"]
                    if evaluation.procedural_artifact_status not in {None, "not_applicable"}
                    else []
                )
            ),
            refinement_vectors=refinement_vectors,
            evaluation_matrix=evaluation_matrix,
            selection_criteria=selection_criteria,
            strategy_context={
                "compile_loop_mode": "metric_driven_sandbox",
                "strategy": resolved_strategy,
                "top_refinement_axis": (
                    refinement_vectors[0]["axis"] if refinement_vectors else "none"
                ),
                "controlled_wave2_experiment": expanded_eval_state,
                "wave_two_readiness_matrix": wave_two_readiness,
                "wave_two_ready_targets": [
                    technology
                    for technology, payload in wave_two_readiness.items()
                    if payload.get("status") == "ready_for_controlled_experiment"
                ],
            },
        )

    def compare_flow_evaluations(
        self,
        proposal: EvolutionProposalContract,
        *,
        baseline_label: str,
        candidate_label: str,
        baseline: FlowEvaluationInput,
        candidate: FlowEvaluationInput,
        governance_refs: list[str],
        notes: list[str],
        strategy_name: str | None = None,
    ) -> EvolutionComparisonResult:
        """Compare two observed flow evaluations under the sandbox policy."""

        return self.compare_candidate(
            proposal,
            ComparisonInput(
                baseline_label=baseline_label,
                candidate_label=candidate_label,
                baseline_metrics=self._metrics_from_flow_evaluation(baseline),
                candidate_metrics=self._metrics_from_flow_evaluation(candidate),
                governance_refs=governance_refs,
                notes=notes,
                strategy_name=strategy_name,
                selection_criteria=self._selection_criteria(
                    self.resolve_strategy_name(strategy_name)
                ),
                candidate_refs=[
                    f"trace://{candidate.request_id}",
                    *(
                        [f"artifact://procedural/{candidate.request_id}"]
                        if candidate.procedural_artifact_status
                        not in {None, "not_applicable"}
                        else []
                    ),
                ],
            ),
        )

    def list_recent_proposals(self, limit: int = 20) -> list[EvolutionProposalContract]:
        """Return recently registered sandbox proposals."""

        return self.repository.list_proposals(limit=limit)

    def list_recent_decisions(self, limit: int = 20) -> list[EvolutionDecisionContract]:
        """Return recent evolution decisions for local review."""

        return self.repository.list_decisions(limit=limit)

    def preferred_strategy(self) -> str:
        """Return the current sandbox-first evolution strategy."""

        return DEFAULT_EVOLUTION_STRATEGY

    def list_supported_strategies(self) -> list[str]:
        """Expose the supported evolution strategies for local review."""

        return list(SUPPORTED_EVOLUTION_STRATEGIES)

    def resolve_strategy_name(self, strategy_name: str | None) -> str:
        """Normalize strategy selection to the supported sandbox set."""

        if strategy_name in SUPPORTED_EVOLUTION_STRATEGIES:
            return str(strategy_name)
        return self.preferred_strategy()

    @staticmethod
    def _metrics_from_flow_evaluation(evaluation: FlowEvaluationInput) -> dict[str, float]:
        missing_penalty = float(len(evaluation.missing_required_events))
        anomaly_penalty = float(len(evaluation.anomaly_flags))
        continuity_missing_penalty = float(len(evaluation.missing_continuity_signals))
        continuity_anomaly_penalty = float(len(evaluation.continuity_anomaly_flags))
        successful_operation = evaluation.operation_status == "completed"
        healthy_governance = evaluation.governance_decision in {
            "allow",
            "allow_with_conditions",
            "block",
            "defer_for_validation",
        }
        return {
            "success": 1.0 if successful_operation or healthy_governance else 0.0,
            "stability": max(
                0.0,
                1.0 - (anomaly_penalty * 0.25) - (continuity_anomaly_penalty * 0.15),
            ),
            "trace_completeness": max(0.0, 1.0 - (missing_penalty * 0.15)),
            "continuity_health": max(
                0.0,
                1.0
                - (continuity_missing_penalty * 0.2)
                - (continuity_anomaly_penalty * 0.25),
            ),
            "domain_alignment": EvolutionLabService._status_score(
                evaluation.domain_alignment_status
            ),
            "mind_alignment": EvolutionLabService._status_score(
                evaluation.mind_alignment_status
            ),
            "identity_alignment": EvolutionLabService._status_score(
                evaluation.identity_alignment_status
            ),
            "memory_alignment": EvolutionLabService._status_score(
                evaluation.memory_alignment_status
            ),
            "specialist_sovereignty": EvolutionLabService._status_score(
                evaluation.specialist_sovereignty_status
            ),
            "axis_gate": EvolutionLabService._status_score(evaluation.axis_gate_status),
            "workflow_profile": EvolutionLabService._workflow_profile_score(
                evaluation.workflow_profile_status
            ),
            "workflow_output": EvolutionLabService._workflow_output_score(
                evaluation.workflow_output_status
            ),
            "metacognitive_guidance": EvolutionLabService._status_score(
                evaluation.metacognitive_guidance_status
            ),
            "mind_disagreement": EvolutionLabService._mind_disagreement_score(
                evaluation.mind_disagreement_status
            ),
            "capability_decision": EvolutionLabService._status_score(
                evaluation.capability_decision_status
            ),
            "capability_effectiveness": EvolutionLabService._capability_effectiveness_score(
                evaluation.capability_effectiveness
            ),
            "handoff_adapter": EvolutionLabService._handoff_adapter_score(
                evaluation.handoff_adapter_status
            ),
            "request_identity": EvolutionLabService._status_score(
                evaluation.request_identity_status
            ),
            "mission_policy": EvolutionLabService._mission_policy_score(
                EvolutionLabService._mission_policy_readiness(evaluation)
            ),
            "expanded_eval": EvolutionLabService._expanded_eval_score(
                EvolutionLabService._expanded_eval_state(evaluation)[
                    "expanded_eval_status"
                ]
            ),
            "surface_axis": EvolutionLabService._expanded_eval_score(
                EvolutionLabService._expanded_eval_state(evaluation)[
                    "surface_axis_status"
                ]
            ),
            "ecosystem_state": EvolutionLabService._expanded_eval_score(
                EvolutionLabService._expanded_eval_state(evaluation)[
                    "ecosystem_state_status"
                ]
            ),
            "experiment_lane": EvolutionLabService._expanded_eval_score(
                EvolutionLabService._expanded_eval_state(evaluation)[
                    "experiment_lane_status"
                ]
            ),
            "adaptive_intervention": EvolutionLabService._adaptive_intervention_score(
                evaluation.adaptive_intervention_status,
                evaluation.adaptive_intervention_effectiveness,
            ),
            "adaptive_intervention_policy": (
                EvolutionLabService._adaptive_intervention_policy_score(
                    EvolutionLabService._adaptive_intervention_policy_readiness(
                        evaluation
                    )
                )
            ),
            "memory_causality": EvolutionLabService._memory_causality_score(
                evaluation.memory_causality_status
            ),
            "memory_maintenance": EvolutionLabService._memory_maintenance_score(
                evaluation.memory_maintenance_effectiveness
            ),
            "memory_lifecycle": EvolutionLabService._memory_lifecycle_score(
                evaluation.memory_lifecycle_status
            ),
            "memory_corpus": EvolutionLabService._memory_corpus_score(
                evaluation.memory_corpus_status
            ),
            "workflow_checkpoint": EvolutionLabService._status_score(
                evaluation.workflow_checkpoint_status
            ),
            "workflow_resume": EvolutionLabService._workflow_resume_score(
                evaluation.workflow_resume_status
            ),
            "procedural_artifact": EvolutionLabService._procedural_artifact_score(
                evaluation.procedural_artifact_status
            ),
            "mind_domain_specialist": (
                EvolutionLabService._mind_domain_specialist_score(
                    evaluation.mind_domain_specialist_status
                )
            ),
            "mind_domain_specialist_chain": (
                EvolutionLabService._mind_domain_specialist_score(
                    evaluation.mind_domain_specialist_chain_status
                )
            ),
            "mind_domain_specialist_effectiveness": (
                EvolutionLabService._mind_domain_specialist_effectiveness_score(
                    evaluation.mind_domain_specialist_effectiveness
                )
            ),
            "mind_domain_specialist_mismatch": (
                EvolutionLabService._mind_domain_specialist_mismatch_score(
                    evaluation.mind_domain_specialist_mismatch_flags
                )
            ),
            "cognitive_recomposition_coherence": (
                EvolutionLabService._recomposition_coherence_score(evaluation)
            ),
            "shadow_coverage": 1.0 if evaluation.shadow_specialists else 0.0,
            "runtime_statefulness": (
                1.0 if evaluation.continuity_runtime_mode == "langgraph_subflow" else 0.5
            ),
            "throughput": float(evaluation.total_events),
            "latency": max(0.0, 1.0 - min(evaluation.duration_seconds / 30.0, 1.0)),
            "risk": anomaly_penalty
            + (missing_penalty * 0.5)
            + (continuity_missing_penalty * 0.35)
            + (continuity_anomaly_penalty * 0.5),
        }

    @staticmethod
    def _status_score(status: str | None) -> float:
        weights = {
            "healthy": 1.0,
            "partial": 0.6,
            "incomplete": 0.2,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.0)

    @staticmethod
    def _workflow_profile_score(status: str | None) -> float:
        weights = {
            "healthy": 1.0,
            "maturation_recommended": 0.8,
            "attention_required": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _workflow_output_score(status: str | None) -> float:
        weights = {
            "coherent": 1.0,
            "partial": 0.8,
            "misaligned": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _memory_causality_score(status: str | None) -> float:
        weights = {
            "causal_guidance": 1.0,
            "attached_only": 0.5,
            "not_applicable": 0.7,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _mind_disagreement_score(status: str | None) -> float:
        weights = {
            "not_applicable": 0.7,
            "contained": 1.0,
            "validation_required": 0.4,
            "deep_review_required": 0.2,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _memory_lifecycle_score(status: str | None) -> float:
        weights = {
            "promoted": 1.0,
            "retained": 1.0,
            "emerging": 0.7,
            "not_applicable": 0.7,
            "review_recommended": 0.3,
            "attention_required": 0.0,
            "incomplete": 0.2,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _memory_corpus_score(status: str | None) -> float:
        weights = {
            "stable": 1.0,
            "monitor": 0.6,
            "review_recommended": 0.2,
            "not_applicable": 0.7,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _workflow_resume_score(status: str | None) -> float:
        weights = {
            "resumed_from_checkpoint": 1.0,
            "resume_available": 0.9,
            "checkpointed_for_followup": 1.0,
            "checkpointed_for_manual_resume": 0.8,
            "completed_without_resume": 0.8,
            "fresh_start": 0.7,
            "manual_resume_required": 0.4,
            "resume_blocked": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _adaptive_intervention_score(
        status: str | None,
        effectiveness: str | None,
    ) -> float:
        if status in {None, "not_applicable"}:
            return 0.7
        weights = {
            "effective": 1.0,
            "insufficient": 0.3,
            "incomplete": 0.1,
            "not_applicable": 0.7,
        }
        return weights.get(effectiveness or "incomplete", 0.0)

    @staticmethod
    def _adaptive_intervention_policy_score(status: str | None) -> float:
        weights = {
            "policy_aligned": 1.0,
            "mandatory_override": 0.9,
            "review_recommended": 0.6,
            "attention_required": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _mission_policy_score(status: str | None) -> float:
        weights = {
            "policy_aligned": 1.0,
            "mandatory_override": 0.9,
            "review_recommended": 0.6,
            "attention_required": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _expanded_eval_score(status: str | None) -> float:
        weights = {
            "candidate_ready": 1.0,
            "controlled_candidate": 1.0,
            "manual_review_only": 0.9,
            "baseline_expanding": 0.7,
            "coverage_partial": 0.6,
            "baseline_only": 0.7,
            "not_in_phase": 0.7,
            "out_of_lane": 0.7,
            "blocked": 0.3,
            "blocked_by_phase": 0.5,
            "blocked_by_drift": 0.0,
            "hold_baseline": 0.7,
            "hold_in_lane": 0.9,
            "freeze_and_review": 0.0,
            "attention_required": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _procedural_artifact_score(status: str | None) -> float:
        weights = {
            "reusable": 1.0,
            "candidate": 0.8,
            "archivable": 0.4,
            "blocked": 0.0,
            "not_applicable": 0.7,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _mind_domain_specialist_score(status: str | None) -> float:
        weights = {
            "aligned": 1.0,
            "evidence_partial": 0.6,
            "not_applicable": 0.7,
            "incomplete": 0.4,
            "attention_required": 0.0,
            "mismatch": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _mind_domain_specialist_effectiveness_score(status: str | None) -> float:
        weights = {
            "effective": 1.0,
            "not_applicable": 0.7,
            "incomplete": 0.2,
            "insufficient": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _mind_domain_specialist_mismatch_score(flags: list[str]) -> float:
        return 1.0 if not flags else 0.0

    @staticmethod
    def _mind_domain_specialist_mismatch_assessment(evaluation: FlowEvaluationInput) -> str:
        if evaluation.mind_domain_specialist_mismatch_flags:
            return "mismatch"
        if evaluation.mind_domain_specialist_effectiveness == "not_applicable":
            return "not_applicable"
        return "aligned"

    @staticmethod
    def _capability_effectiveness_score(status: str | None) -> float:
        weights = {
            "effective": 1.0,
            "not_applicable": 0.7,
            "incomplete": 0.2,
            "insufficient": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _memory_maintenance_score(status: str | None) -> float:
        weights = {
            "effective": 1.0,
            "not_applicable": 0.7,
            "incomplete": 0.2,
            "insufficient": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _handoff_adapter_score(status: str | None) -> float:
        weights = {
            "healthy": 1.0,
            "contained": 0.9,
            "not_applicable": 0.7,
            "incomplete": 0.2,
            "attention_required": 0.0,
        }
        return weights.get(status, 0.7 if status is None else 0.0)

    @staticmethod
    def _recomposition_coherence_score(evaluation: FlowEvaluationInput) -> float:
        if evaluation.cognitive_recomposition_applied:
            return (
                1.0
                if evaluation.cognitive_recomposition_reason
                and evaluation.cognitive_recomposition_trigger
                else 0.0
            )
        return (
            1.0
            if evaluation.cognitive_recomposition_reason is None
            and evaluation.cognitive_recomposition_trigger is None
            else 0.0
        )

    @staticmethod
    def _requires_refinement(evaluation: FlowEvaluationInput) -> bool:
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        if evaluation.anomaly_flags or evaluation.missing_required_events:
            return True
        if evaluation.continuity_anomaly_flags or evaluation.missing_continuity_signals:
            return True
        if evaluation.workflow_profile_status in {
            "maturation_recommended",
            "attention_required",
        }:
            return True
        if evaluation.workflow_output_status in {"partial", "misaligned"}:
            return True
        if evaluation.metacognitive_guidance_status in {"incomplete", "attention_required"}:
            return True
        if evaluation.mind_disagreement_status in {
            "validation_required",
            "deep_review_required",
            "attention_required",
        }:
            return True
        if evaluation.mind_validation_checkpoint_status == "attention_required":
            return True
        if evaluation.capability_decision_status in {"incomplete", "attention_required"}:
            return True
        if evaluation.capability_effectiveness in {"insufficient", "incomplete"}:
            return True
        if evaluation.handoff_adapter_status in {"incomplete", "attention_required"}:
            return True
        if evaluation.request_identity_status in {"incomplete", "attention_required"}:
            return True
        if (
            EvolutionLabService._mission_policy_readiness(evaluation)
            in {"attention_required", "review_recommended"}
        ):
            return True
        if expanded_eval_state["expanded_eval_status"] == "attention_required":
            return True
        if expanded_eval_state["experiment_lane_status"] == "attention_required":
            return True
        if evaluation.adaptive_intervention_status == "attention_required":
            return True
        if (
            EvolutionLabService._adaptive_intervention_policy_readiness(evaluation)
            in {"attention_required", "review_recommended"}
        ):
            return True
        if evaluation.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}:
            return True
        if evaluation.memory_causality_status in {"attached_only", "attention_required"}:
            return True
        if evaluation.memory_maintenance_effectiveness in {"insufficient", "incomplete"}:
            return True
        if evaluation.memory_lifecycle_status in {"review_recommended", "attention_required"}:
            return True
        if evaluation.memory_corpus_status in {"monitor", "review_recommended"}:
            return True
        if evaluation.workflow_checkpoint_status in {"incomplete", "attention_required"}:
            return True
        if evaluation.workflow_resume_status in {"manual_resume_required", "resume_blocked"}:
            return True
        if evaluation.procedural_artifact_status in {"candidate", "blocked"}:
            return True
        if evaluation.mind_domain_specialist_status in {
            "incomplete",
            "evidence_partial",
            "attention_required",
            "mismatch",
        }:
            return True
        if evaluation.mind_domain_specialist_chain_status in {
            "incomplete",
            "evidence_partial",
            "attention_required",
            "mismatch",
        }:
            return True
        if evaluation.mind_domain_specialist_effectiveness in {
            "insufficient",
            "incomplete",
        }:
            return True
        if evaluation.mind_domain_specialist_mismatch_flags:
            return True
        return EvolutionLabService._recomposition_coherence_score(evaluation) < 1.0

    @staticmethod
    def _risk_hint_from_flow(evaluation: FlowEvaluationInput) -> str:
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        if evaluation.anomaly_flags or evaluation.continuity_anomaly_flags:
            return "moderate"
        if evaluation.metacognitive_guidance_status == "attention_required":
            return "moderate"
        if evaluation.mind_disagreement_status in {
            "deep_review_required",
            "attention_required",
        }:
            return "moderate"
        if evaluation.mind_validation_checkpoint_status == "attention_required":
            return "moderate"
        if evaluation.capability_decision_status == "attention_required":
            return "moderate"
        if evaluation.handoff_adapter_status == "attention_required":
            return "moderate"
        if evaluation.request_identity_status == "attention_required":
            return "moderate"
        if EvolutionLabService._mission_policy_readiness(evaluation) == "attention_required":
            return "moderate"
        if expanded_eval_state["expanded_eval_status"] == "attention_required":
            return "moderate"
        if expanded_eval_state["experiment_lane_status"] == "attention_required":
            return "moderate"
        if evaluation.capability_effectiveness in {"insufficient", "incomplete"}:
            return "moderate"
        if evaluation.adaptive_intervention_policy_status == "attention_required":
            return "moderate"
        if evaluation.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}:
            return "moderate"
        if evaluation.memory_causality_status == "attention_required":
            return "moderate"
        if evaluation.memory_maintenance_effectiveness in {"insufficient", "incomplete"}:
            return "moderate"
        if evaluation.memory_lifecycle_status == "attention_required":
            return "moderate"
        if evaluation.memory_corpus_status == "review_recommended":
            return "moderate"
        if evaluation.workflow_checkpoint_status == "attention_required":
            return "moderate"
        if evaluation.workflow_resume_status == "resume_blocked":
            return "moderate"
        if evaluation.mind_domain_specialist_status in {"attention_required", "mismatch"}:
            return "moderate"
        if evaluation.mind_domain_specialist_chain_status in {
            "attention_required",
            "mismatch",
        }:
            return "moderate"
        if evaluation.mind_domain_specialist_effectiveness in {"insufficient", "incomplete"}:
            return "moderate"
        if evaluation.mind_domain_specialist_mismatch_flags:
            return "moderate"
        if evaluation.workflow_output_status == "misaligned":
            return "moderate"
        if (
            EvolutionLabService._adaptive_intervention_policy_readiness(evaluation)
            == "review_recommended"
        ):
            return "low_to_moderate"
        if evaluation.axis_gate_status not in {None, "healthy"}:
            return "low_to_moderate"
        if evaluation.workflow_profile_status in {"maturation_recommended", "attention_required"}:
            return "low_to_moderate"
        if evaluation.workflow_output_status == "partial":
            return "low_to_moderate"
        if expanded_eval_state["expanded_eval_status"] == "baseline_expanding":
            return "low_to_moderate"
        if evaluation.memory_causality_status == "attached_only":
            return "low_to_moderate"
        if evaluation.memory_maintenance_effectiveness in {"insufficient", "incomplete"}:
            return "low_to_moderate"
        if evaluation.memory_lifecycle_status == "review_recommended":
            return "low_to_moderate"
        if evaluation.memory_corpus_status == "monitor":
            return "low_to_moderate"
        if evaluation.workflow_resume_status == "manual_resume_required":
            return "low_to_moderate"
        if evaluation.procedural_artifact_status == "candidate":
            return "low_to_moderate"
        if evaluation.mind_domain_specialist_status == "incomplete":
            return "low_to_moderate"
        if evaluation.mind_domain_specialist_chain_status in {"incomplete", "evidence_partial"}:
            return "low_to_moderate"
        if evaluation.mind_domain_specialist_effectiveness in {
            "insufficient",
            "incomplete",
        }:
            return "low_to_moderate"
        if evaluation.missing_required_events or evaluation.missing_continuity_signals:
            return "low_to_moderate"
        return "low"

    @staticmethod
    def _workflow_key(evaluation: FlowEvaluationInput) -> str:
        if evaluation.primary_route:
            return evaluation.primary_route
        if evaluation.registry_domains:
            return evaluation.registry_domains[0]
        return "baseline_runtime"

    @staticmethod
    def _refinement_vectors_from_flow_evaluation(
        evaluation: FlowEvaluationInput,
    ) -> list[dict[str, str]]:
        workflow_profile = EvolutionLabService._workflow_key(evaluation)
        vectors: list[dict[str, str]] = []
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        adaptive_policy_readiness = (
            EvolutionLabService._adaptive_intervention_policy_readiness(evaluation)
        )

        def add_vector(axis: str, priority: str, recommendation: str) -> None:
            vectors.append(
                {
                    "axis": axis,
                    "priority": priority,
                    "workflow_profile": workflow_profile,
                    "recommendation": recommendation,
                }
            )

        if evaluation.metacognitive_guidance_status in {"incomplete", "attention_required"}:
            add_vector(
                "metacognitive_guidance",
                "p0",
                "endurecer a ancora metacognitiva ate ela alterar criterio de saida de forma coerente",
            )
        if evaluation.workflow_output_status in {"partial", "misaligned"}:
            add_vector(
                "workflow_output",
                "p0" if evaluation.workflow_output_status == "misaligned" else "p1",
                "alinhar a resposta final ao contrato do workflow ativo com clausulas e foco coerentes",
            )
        if evaluation.mind_disagreement_status in {
            "validation_required",
            "deep_review_required",
            "attention_required",
        } or evaluation.mind_validation_checkpoint_status == "attention_required":
            add_vector(
                "mind_composition",
                "p0",
                "transformar a discordancia entre mentes em checkpoint governado do workflow ativo",
            )
        if evaluation.capability_decision_status in {"incomplete", "attention_required"}:
            add_vector(
                "capability_decision",
                "p0",
                "formalizar o contrato soberano de capabilities, autorizacao e fallback sem lacunas observaveis",
            )
        if evaluation.capability_effectiveness in {"insufficient", "incomplete"}:
            add_vector(
                "capability_effectiveness",
                "p0",
                "alinhar capability mode, autorizacao e efeito final para preservar operacao bounded ou contencao coerente",
            )
        if evaluation.handoff_adapter_status in {"incomplete", "attention_required"}:
            add_vector(
                "handoff_adapter",
                "p0",
                "restaurar o adapter through_core_only para que handoffs sejam aprovados ou contidos com evidencias coerentes",
            )
        if evaluation.request_identity_status in {"incomplete", "attention_required"}:
            add_vector(
                "request_identity",
                "p0",
                "explicitar missao ativa, postura executiva e autoridade bounded como contrato soberano rastreavel",
            )
        mission_policy_readiness = EvolutionLabService._mission_policy_readiness(
            evaluation
        )
        if mission_policy_readiness == "attention_required":
            add_vector(
                "mission_policy",
                "p0",
                "realinhar confirmacao, reversibilidade e autonomia final ao contrato de identidade por request",
            )
        if expanded_eval_state["expanded_eval_status"] == "attention_required":
            add_vector(
                "expanded_eval_scope",
                "p0",
                "restaurar a leitura comparativa entre baseline, superficie e estado operacional antes de abrir a lane experimental",
            )
        elif expanded_eval_state["expanded_eval_status"] == "baseline_expanding":
            add_vector(
                "expanded_eval_scope",
                "p1",
                "consolidar a cobertura comparativa para capacidade, superficie e estado operacional",
            )
        if expanded_eval_state["experiment_lane_status"] == "attention_required":
            add_vector(
                "controlled_wave2_experiment",
                "p0",
                "conter a lane da Onda 2 ate os blockers voltarem a um baseline comparavel",
            )
        if evaluation.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}:
            add_vector(
                "adaptive_intervention",
                "p0",
                "fazer a intervencao adaptativa alterar steps, contencao ou revisao com efeito observavel",
            )
        if adaptive_policy_readiness == "attention_required":
            add_vector(
                "adaptive_intervention_policy",
                "p0",
                "realinhar a prioridade soberana do workflow com a intervencao que realmente preserva o checkpoint ativo",
            )
        elif adaptive_policy_readiness == "review_recommended":
            add_vector(
                "adaptive_intervention_policy",
                "p1",
                "revisar a prioridade soberana do workflow porque a politica escolhida segue valida, mas ainda fecha mal o checkpoint preservado",
            )
        if evaluation.memory_causality_status in {"attached_only", "attention_required"}:
            add_vector(
                "memory_causality",
                "p0",
                "fazer semantic e procedural alterarem framing, continuidade e proxima acao de forma causal",
            )
        if evaluation.memory_maintenance_effectiveness in {"insufficient", "incomplete"}:
            add_vector(
                "memory_maintenance",
                "p0",
                "alinhar review, compaction e recall cross-session para manter memoria viva bounded e auditavel",
            )
        if evaluation.memory_lifecycle_status in {"review_recommended", "attention_required"}:
            add_vector(
                "memory_lifecycle",
                "p1",
                "reduzir revisao pendente e estabilizar retencao/promocao no corpus guiado",
            )
        if evaluation.memory_corpus_status in {"monitor", "review_recommended"}:
            add_vector(
                "memory_corpus",
                "p1",
                "revisar pressao de retencao por classe antes de ampliar memoria guiada",
            )
        if evaluation.workflow_profile_status in {"maturation_recommended", "attention_required"}:
            add_vector(
                "workflow_profile",
                "p1",
                "alinhar o contrato do workflow ativo com passos, checkpoints e criterio de resposta",
            )
        if evaluation.workflow_checkpoint_status in {"incomplete", "attention_required"}:
            add_vector(
                "workflow_checkpointing",
                "p1",
                "materializar checkpoints completos e retomada observavel no workflow ativo",
            )
        if evaluation.procedural_artifact_status == "candidate":
            add_vector(
                "procedural_artifacts",
                "p1",
                "promover know-how procedural candidato para artefato reutilizavel through_core_only",
            )
        if evaluation.mind_domain_specialist_chain_status in {
            "incomplete",
            "evidence_partial",
            "attention_required",
            "mismatch",
        }:
            add_vector(
                "mind_domain_specialist_chain",
                "p0",
                "restaurar coerencia evidence-first entre mente primaria, dominio e especialista guiado",
            )
        if evaluation.mind_domain_specialist_mismatch_flags:
            add_vector(
                "mind_domain_specialist_effectiveness",
                "p0",
                "eliminar mismatch entre cadeia autoritativa, framing final e especialista efetivamente consumido",
            )
        elif evaluation.mind_domain_specialist_effectiveness in {
            "insufficient",
            "incomplete",
        }:
            add_vector(
                "mind_domain_specialist_effectiveness",
                "p0"
                if evaluation.mind_domain_specialist_effectiveness == "insufficient"
                else "p1",
                "fazer a arbitragem declarativa produzir consumo final coerente com a cadeia autoritativa e o fallback governado",
            )
        return vectors

    @staticmethod
    def _evaluation_matrix_from_flow_evaluation(
        evaluation: FlowEvaluationInput,
    ) -> dict[str, dict[str, object]]:
        workflow = EvolutionLabService._workflow_key(evaluation)
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        return {
            workflow: {
                "workflow_profile": evaluation.workflow_profile_status or "not_applicable",
                "workflow_output": evaluation.workflow_output_status or "not_applicable",
                "metacognitive_guidance": (
                    evaluation.metacognitive_guidance_status or "not_applicable"
                ),
                "mind_disagreement": evaluation.mind_disagreement_status or "not_applicable",
                "mind_validation_checkpoint": (
                    evaluation.mind_validation_checkpoint_status or "not_applicable"
                ),
                "capability_decision": (
                    evaluation.capability_decision_status or "not_applicable"
                ),
                "capability_effectiveness": (
                    evaluation.capability_effectiveness or "not_applicable"
                ),
                "handoff_adapter": evaluation.handoff_adapter_status or "not_applicable",
                "request_identity": (
                    evaluation.request_identity_status or "not_applicable"
                ),
                "mission_policy": EvolutionLabService._mission_policy_readiness(
                    evaluation
                ),
                "expanded_eval": expanded_eval_state["expanded_eval_status"],
                "surface_axis": expanded_eval_state["surface_axis_status"],
                "ecosystem_state": expanded_eval_state["ecosystem_state_status"],
                "experiment_lane": expanded_eval_state["experiment_lane_status"],
                "wave2_candidate_class": expanded_eval_state["wave2_candidate_class"],
                "experiment_entry": expanded_eval_state["experiment_entry_status"],
                "experiment_exit": expanded_eval_state["experiment_exit_status"],
                "promotion_readiness": expanded_eval_state["promotion_readiness"],
                "adaptive_intervention": (
                    evaluation.adaptive_intervention_effectiveness
                    if evaluation.adaptive_intervention_status not in {None, "not_applicable"}
                    else "not_applicable"
                ),
                "adaptive_intervention_policy": (
                    EvolutionLabService._adaptive_intervention_policy_readiness(
                        evaluation
                    )
                ),
                "mind_composition": EvolutionLabService._mind_composition_assessment(
                    evaluation
                ),
                "memory_causality": evaluation.memory_causality_status or "not_applicable",
                "memory_maintenance": evaluation.memory_maintenance_status or "not_applicable",
                "memory_maintenance_effectiveness": (
                    evaluation.memory_maintenance_effectiveness or "not_applicable"
                ),
                "context_compaction": evaluation.context_compaction_status or "not_applicable",
                "cross_session_recall": (
                    evaluation.cross_session_recall_status or "not_applicable"
                ),
                "memory_lifecycle": evaluation.memory_lifecycle_status or "not_applicable",
                "memory_corpus": evaluation.memory_corpus_status or "not_applicable",
                "workflow_checkpoint": (
                    evaluation.workflow_checkpoint_status or "not_applicable"
                ),
                "workflow_resume": evaluation.workflow_resume_status or "not_applicable",
                "procedural_artifact": (
                    evaluation.procedural_artifact_status or "not_applicable"
                ),
                "mind_domain_specialist": (
                    evaluation.mind_domain_specialist_status or "not_applicable"
                ),
                "mind_domain_specialist_chain": (
                    evaluation.mind_domain_specialist_chain_status or "not_applicable"
                ),
                "mind_domain_specialist_effectiveness": (
                    evaluation.mind_domain_specialist_effectiveness or "not_applicable"
                ),
                "mind_domain_specialist_mismatch": (
                    EvolutionLabService._mind_domain_specialist_mismatch_assessment(
                        evaluation
                    )
                ),
                "mind_domain_specialist_mismatch_flags": list(
                    evaluation.mind_domain_specialist_mismatch_flags
                ),
            }
        }

    @staticmethod
    def _adaptive_intervention_policy_readiness(
        evaluation: FlowEvaluationInput,
    ) -> str:
        status = evaluation.adaptive_intervention_policy_status
        if status in {None, "not_applicable"}:
            return "not_applicable"
        if status == "attention_required":
            return "attention_required"
        if (
            status in {"policy_aligned", "mandatory_override"}
            and evaluation.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}
        ):
            return "review_recommended"
        return status

    @staticmethod
    def _mission_policy_readiness(
        evaluation: FlowEvaluationInput,
    ) -> str:
        status = evaluation.mission_policy_status
        if status in {None, "not_applicable"}:
            return "not_applicable"
        if evaluation.request_identity_status in {"incomplete", "attention_required"}:
            return "attention_required"
        if evaluation.request_identity_mismatch_flags:
            return "attention_required"
        return status

    @staticmethod
    def _expanded_eval_state(evaluation: FlowEvaluationInput) -> dict[str, str]:
        state = derive_expanded_eval_state(
            capability_decision_status=evaluation.capability_decision_status,
            capability_effectiveness=evaluation.capability_effectiveness,
            handoff_adapter_status=evaluation.handoff_adapter_status,
            request_identity_status=evaluation.request_identity_status,
            mission_policy_status=EvolutionLabService._mission_policy_readiness(
                evaluation
            ),
            continuity_trace_status=evaluation.continuity_trace_status,
            workflow_checkpoint_status=evaluation.workflow_checkpoint_status,
            workflow_resume_status=evaluation.workflow_resume_status,
            specialist_subflow_status=evaluation.specialist_subflow_status,
            mission_runtime_state_status=evaluation.mission_runtime_state_status,
        )
        if evaluation.expanded_eval_status is not None:
            state["expanded_eval_status"] = evaluation.expanded_eval_status
        if evaluation.surface_axis_status is not None:
            state["surface_axis_status"] = evaluation.surface_axis_status
        if evaluation.ecosystem_state_status is not None:
            state["ecosystem_state_status"] = evaluation.ecosystem_state_status
        if evaluation.experiment_lane_status is not None:
            state["experiment_lane_status"] = evaluation.experiment_lane_status
        if evaluation.wave2_candidate_class is not None:
            state["wave2_candidate_class"] = evaluation.wave2_candidate_class
        if evaluation.experiment_entry_status is not None:
            state["experiment_entry_status"] = evaluation.experiment_entry_status
        if evaluation.experiment_exit_status is not None:
            state["experiment_exit_status"] = evaluation.experiment_exit_status
        if evaluation.promotion_readiness is not None:
            state["promotion_readiness"] = evaluation.promotion_readiness
        return state

    @staticmethod
    def _mind_composition_assessment(evaluation: FlowEvaluationInput) -> str:
        if evaluation.mind_domain_specialist_chain_status in {
            "attention_required",
            "mismatch",
        }:
            return "attention_required"
        if evaluation.mind_domain_specialist_effectiveness == "insufficient":
            return "attention_required"
        if evaluation.mind_domain_specialist_mismatch_flags:
            return "attention_required"
        if evaluation.mind_domain_specialist_status in {"attention_required", "mismatch"}:
            return "attention_required"
        if evaluation.mind_validation_checkpoint_status == "attention_required":
            return "attention_required"
        if evaluation.mind_disagreement_status == "deep_review_required":
            return "attention_required"
        if evaluation.mind_domain_specialist_chain_status in {
            "incomplete",
            "evidence_partial",
        }:
            return "maturation_recommended"
        if evaluation.mind_domain_specialist_effectiveness == "incomplete":
            return "maturation_recommended"
        if evaluation.mind_domain_specialist_status in {"incomplete", "evidence_partial"}:
            return "maturation_recommended"
        if evaluation.mind_disagreement_status == "validation_required":
            return "maturation_recommended"
        if evaluation.mind_disagreement_status in {None, "not_applicable", "contained"} and (
            evaluation.mind_validation_checkpoint_status
            in {None, "not_applicable", "healthy"}
        ):
            return "baseline_saudavel"
        return "maturation_recommended"

    @staticmethod
    def _wave_two_readiness_matrix_from_evaluation(
        evaluation: FlowEvaluationInput,
    ) -> dict[str, dict[str, object]]:
        matrix = EvolutionLabService._evaluation_matrix_from_flow_evaluation(evaluation)
        workflow = next(iter(matrix.keys()))
        row = matrix[workflow]
        requirements: dict[str, dict[str, set[str]]] = {
            "openai_agents_sdk": {
                "workflow_checkpoint": {"healthy"},
                "workflow_resume": {"healthy", "resume_available", "fresh_start"},
                "workflow_output": {"coherent", "not_applicable"},
                "adaptive_intervention": {"effective", "not_applicable"},
                "mind_domain_specialist_chain": {"aligned", "not_applicable"},
                "mind_domain_specialist_effectiveness": {"effective", "not_applicable"},
                "mind_domain_specialist_mismatch": {"aligned", "not_applicable"},
            },
            "qwen_agent": {
                "workflow_profile": {"healthy", "maturation_recommended", "not_applicable"},
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
                "workflow_profile": {"healthy", "maturation_recommended", "not_applicable"},
            },
            "openhands": {
                "workflow_output": {"coherent", "not_applicable"},
                "procedural_artifact": {"reusable", "not_applicable"},
                "mind_domain_specialist_chain": {"aligned", "not_applicable"},
            },
            "browser_use": {
                "workflow_checkpoint": {"healthy"},
                "workflow_resume": {"healthy", "resume_available", "fresh_start"},
                "workflow_output": {"coherent", "partial", "not_applicable"},
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
                "workflow_profile": {"healthy", "not_applicable"},
                "workflow_output": {"coherent", "not_applicable"},
            },
        }
        readiness: dict[str, dict[str, object]] = {}
        for technology, axes in requirements.items():
            blockers = [
                f"{axis}={row.get(axis, 'not_applicable')}"
                for axis, accepted in axes.items()
                if str(row.get(axis, "not_applicable")) not in accepted
            ]
            readiness[technology] = {
                "status": (
                    "ready_for_controlled_experiment"
                    if not blockers
                    else "stabilize_nucleus_first"
                ),
                "workflow_profile": workflow,
                "blockers": blockers[:4],
            }
        return readiness

    @staticmethod
    def _selection_criteria(strategy_name: str) -> dict[str, object]:
        return {
            "strategy": strategy_name,
            "risk_must_not_increase": True,
            "stability_min_delta": 0.0,
            "trace_completeness_floor": 0.7,
            "axis_gate_floor": 0.6,
        }

    @staticmethod
    def _candidate_meets_selection_criteria(
        *,
        selection_criteria: dict[str, object],
        baseline_metrics: dict[str, float],
        candidate_metrics: dict[str, float],
        metric_deltas: dict[str, float],
    ) -> bool:
        if selection_criteria.get("risk_must_not_increase") and (
            candidate_metrics.get("risk", 0.0) > baseline_metrics.get("risk", 0.0)
        ):
            return False
        if metric_deltas.get("stability", 0.0) < float(
            selection_criteria.get("stability_min_delta", 0.0)
        ):
            return False
        if (
            "trace_completeness" in candidate_metrics
            and candidate_metrics.get("trace_completeness", 0.0)
            < float(selection_criteria.get("trace_completeness_floor", 0.0))
        ):
            return False
        if (
            "axis_gate" in candidate_metrics
            and candidate_metrics.get("axis_gate", 0.0)
            < float(selection_criteria.get("axis_gate_floor", 0.0))
        ):
            return False
        return True

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
