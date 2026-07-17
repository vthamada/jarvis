# ruff: noqa: E501
"""Local evolution lab for sandbox-only comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from hashlib import sha256
from os import getenv
from pathlib import Path
from uuid import uuid4

from evolution_lab.repository import EvolutionLabRepository
from shared.contracts import (
    EvolutionDecisionContract,
    EvolutionProposalContract,
    EvolutionReviewDecisionContract,
    EvolutionReviewQueueItemContract,
    ExperienceRecordContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    PromotionGateDecisionContract,
    RecurringPatternEvidenceContract,
    ReviewedLearningGuidanceContract,
    SandboxToReleaseChecklistContract,
    SkillCandidateContract,
    SkillMiningRequestContract,
    SkillMiningResultContract,
    SkillSandboxCaseResultContract,
    SkillSandboxEvalContract,
    TechnologyAbsorptionCandidateContract,
    WorkflowEvolutionBuildResultContract,
    WorkflowEvolutionRequestContract,
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
)
from shared.domain_registry import (
    build_active_workflow_version_registry,
    register_workflow_candidate_version,
    workflow_definition_hash,
)
from shared.eval_expansion import derive_expanded_eval_state
from shared.optimization_state import derive_optimization_state
from shared.technology_absorption import derive_technology_absorption_state
from shared.types import EvolutionDecisionId, EvolutionProposalId, RiskLevel

DEFAULT_EVOLUTION_STRATEGY = "manual_variants"
SUPPORTED_EVOLUTION_STRATEGIES = (
    "manual_variants",
    "mipro_like_search",
    "textgrad_like_refinement",
)
EVOLUTION_REVIEW_STATUSES = (
    "observed",
    "candidate",
    "needs_review",
    "approved",
    "rejected",
    "sandboxed",
    "promoted",
    "rolled_back",
)
EVOLUTION_REVIEW_ACTIONS = {
    "approve": "approved",
    "reject": "rejected",
    "sandbox": "sandboxed",
    "needs_review": "needs_review",
    "rollback": "rolled_back",
}
RISKY_REVIEW_ACTIONS = {"approve", "sandbox"}
REVIEWED_LEARNING_GUIDANCE_STATUSES = {"approved", "sandboxed"}


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
    operational_ecosystem_state_status: str | None = None
    active_work_items: list[str] = field(default_factory=list)
    active_artifact_refs: list[str] = field(default_factory=list)
    open_checkpoint_refs: list[str] = field(default_factory=list)
    surface_presence: list[str] = field(default_factory=list)
    surface_continuity_status: str | None = None
    linked_surface_count: int = 0
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    multi_surface_readiness: str | None = None
    experiment_lane_status: str | None = None
    wave2_candidate_class: str | None = None
    experiment_entry_status: str | None = None
    experiment_exit_status: str | None = None
    promotion_readiness: str | None = None


@dataclass(frozen=True)
class TechnologyAbsorptionInput:
    """External technology candidate kept subordinate to the sovereign core."""

    candidate_ref: str
    technology_name: str
    absorption_class: str
    target_gap_refs: list[str]
    hypothesis: str
    expected_gain: str
    source_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    proposed_tests: list[str] = field(default_factory=list)
    risk_hint: str | None = None
    status: str = "candidate"
    requested_core_role: str = "subordinate"
    rollback_plan_ref: str | None = None
    blockers: list[str] = field(default_factory=list)
    human_review_required: bool = True


@dataclass(frozen=True)
class PostTaskReflectionInput:
    """Bounded post-task reflection used as sandbox-only evolution material."""

    experience_id: str
    mission_id: str
    workflow_profile: str
    outcome_status: str
    learning_candidate: str
    recommendation: str
    evidence_refs: list[str] = field(default_factory=list)
    signal_refs: list[str] = field(default_factory=list)
    failure_modes: list[str] = field(default_factory=list)
    decision_refs: list[str] = field(default_factory=list)
    learned_patterns: list[str] = field(default_factory=list)
    proposed_change_type: str = "memory"
    proposed_tests: list[str] = field(default_factory=list)
    rollback_plan_ref: str | None = None
    risk_hint: str | None = None
    objective_ref: str | None = None
    surface_id: str | None = None
    next_action_ref: str | None = None
    automatic_promotion_allowed: bool = False
    core_mutation_allowed: bool = False


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
        optimization_scope: str | None = None,
        optimization_target_kind: str | None = None,
        optimization_candidate_status: str | None = None,
        optimization_safety_status: str | None = None,
        optimization_blockers: list[str] | None = None,
    ) -> EvolutionProposalContract:
        """Register a sandbox proposal for later comparison."""

        chosen_strategy = self.resolve_strategy_name(strategy_name)
        strategy_signal = f"strategy://{chosen_strategy}"
        signals = list(source_signals or [])
        if strategy_signal not in signals:
            signals.append(strategy_signal)
        blockers = list(optimization_blockers or [])
        review_context = self._review_context(
            status="needs_review",
            blockers=blockers,
            rollback_plan_ref=None,
        )
        merged_strategy_context = dict(strategy_context or {})
        merged_strategy_context.setdefault("evolution_review", review_context)

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
            optimization_scope=optimization_scope,
            optimization_target_kind=optimization_target_kind,
            optimization_candidate_status=optimization_candidate_status,
            optimization_safety_status=optimization_safety_status,
            optimization_blockers=blockers,
            candidate_refs=list(candidate_refs or []),
            refinement_vectors=list(refinement_vectors or []),
            evaluation_matrix=dict(evaluation_matrix or {}),
            selection_criteria=dict(selection_criteria or {}),
            strategy_context=merged_strategy_context,
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
            "hold_baseline"
            if proposal.optimization_candidate_status == "blocked"
            or proposal.optimization_safety_status == "blocked_by_safety"
            else (
                "sandbox_candidate"
                if improved >= degraded
                and risk_score <= comparison.baseline_metrics.get("risk", risk_score)
                and candidate_meets_selection
                else "hold_baseline"
            )
        )
        optimization_state = dict(
            proposal.strategy_context.get("optimization_state", {})
            if isinstance(proposal.strategy_context, dict)
            else {}
        )
        summary = (
            f"baseline={comparison.baseline_label}; candidate={comparison.candidate_label}; "
            f"strategy={chosen_strategy}; improved_metrics={improved}; degraded_metrics={degraded}; "
            f"stability={stability_score}; risk={risk_score}; "
            f"selection_ok={candidate_meets_selection}; "
            f"optimization_target={proposal.optimization_target_kind or 'not_applicable'}; "
            f"optimization_readiness={optimization_state.get('optimization_readiness', 'not_applicable')}; "
            f"optimization_release={optimization_state.get('optimization_release_status', 'not_applicable')}"
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
                f"optimization_state={optimization_state}",
            ],
            optimization_scope=proposal.optimization_scope,
            optimization_target_kind=proposal.optimization_target_kind,
            optimization_readiness=str(
                optimization_state.get("optimization_readiness", "not_applicable")
            ),
            optimization_release_status=str(
                optimization_state.get("optimization_release_status", "not_applicable")
            ),
            optimization_safety_status=proposal.optimization_safety_status,
            optimization_blockers=list(proposal.optimization_blockers),
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
        optimization_state = self._optimization_state(
            evaluation,
            refinement_vectors=refinement_vectors,
        )
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
        if evaluation.operational_ecosystem_state_status:
            source_signals.append(
                "runtime://ecosystem-operational-state/"
                f"{evaluation.operational_ecosystem_state_status}"
            )
        if evaluation.active_work_items:
            source_signals.append("runtime://ecosystem-active-work-items/present")
        if evaluation.active_artifact_refs:
            source_signals.append("runtime://ecosystem-active-artifacts/present")
        if evaluation.open_checkpoint_refs:
            source_signals.append("runtime://ecosystem-open-checkpoints/present")
        if evaluation.surface_presence:
            source_signals.append("runtime://ecosystem-surface-presence/present")
        if evaluation.surface_continuity_status:
            source_signals.append(
                "runtime://surface-continuity/"
                f"{evaluation.surface_continuity_status}"
            )
        if evaluation.linked_surface_count:
            source_signals.append(
                f"runtime://linked-surface-count/{evaluation.linked_surface_count}"
            )
        if evaluation.surface_identity_conflict_flags:
            source_signals.append("runtime://surface-identity-conflict/present")
        if evaluation.multi_surface_readiness:
            source_signals.append(
                "runtime://multi-surface-readiness/"
                f"{evaluation.multi_surface_readiness}"
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
        source_signals.append(
            f"optimization://scope/{optimization_state['optimization_scope']}"
        )
        source_signals.append(
            "optimization://target/"
            f"{optimization_state['optimization_target_kind']}"
        )
        source_signals.append(
            "optimization://candidate/"
            f"{optimization_state['optimization_candidate_status']}"
        )
        source_signals.append(
            "optimization://safety/"
            f"{optimization_state['optimization_safety_status']}"
        )
        source_signals.append(
            "optimization://release/"
            f"{optimization_state['optimization_release_status']}"
        )
        for blocker in optimization_state["optimization_blockers"]:
            source_signals.append(f"optimization://blocker/{blocker}")
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
            optimization_scope=str(optimization_state["optimization_scope"]),
            optimization_target_kind=str(optimization_state["optimization_target_kind"]),
            optimization_candidate_status=str(
                optimization_state["optimization_candidate_status"]
            ),
            optimization_safety_status=str(
                optimization_state["optimization_safety_status"]
            ),
            optimization_blockers=list(optimization_state["optimization_blockers"]),
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
                "optimization_state": optimization_state,
                "controlled_wave2_experiment": expanded_eval_state,
                "wave_two_readiness_matrix": wave_two_readiness,
                "wave_two_ready_targets": [
                    technology
                    for technology, payload in wave_two_readiness.items()
                    if payload.get("status") == "ready_for_controlled_experiment"
                ],
            },
        )

    def create_proposal_from_technology_absorption_candidate(
        self,
        candidate: TechnologyAbsorptionInput,
        *,
        target_scope: str | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a sandbox-only proposal from a governed technology candidate."""

        absorption_state = derive_technology_absorption_state(
            absorption_class=candidate.absorption_class,
            candidate_status=candidate.status,
            requested_core_role=candidate.requested_core_role,
            evidence_refs=candidate.evidence_refs,
            proposed_tests=candidate.proposed_tests,
            blockers=candidate.blockers,
            human_review_required=candidate.human_review_required,
            rollback_plan_ref=candidate.rollback_plan_ref,
        )
        contract = TechnologyAbsorptionCandidateContract(
            candidate_ref=candidate.candidate_ref,
            technology_name=candidate.technology_name,
            absorption_class=candidate.absorption_class,
            target_gap_refs=list(candidate.target_gap_refs),
            hypothesis=candidate.hypothesis,
            expected_gain=candidate.expected_gain,
            source_refs=list(candidate.source_refs),
            evidence_refs=list(candidate.evidence_refs),
            proposed_tests=list(candidate.proposed_tests),
            risk_hint=candidate.risk_hint,
            status=candidate.status,
            decision=str(absorption_state["absorption_decision"]),
            requested_core_role=candidate.requested_core_role,
            sandbox_required=bool(absorption_state["requires_sandbox"]),
            human_review_required=bool(absorption_state["requires_human_review"]),
            rollback_plan_ref=candidate.rollback_plan_ref,
            blockers=list(absorption_state["blockers"]),
        )
        source_signals = [
            f"technology://candidate/{contract.candidate_ref}",
            f"technology://name/{self._signal_value(contract.technology_name)}",
            f"technology://absorption-class/{contract.absorption_class}",
            f"technology://status/{contract.status}",
            f"technology://readiness/{absorption_state['absorption_readiness']}",
            f"technology://decision/{absorption_state['absorption_decision']}",
        ]
        source_signals.extend(
            f"technology://target-gap/{self._signal_value(ref)}"
            for ref in contract.target_gap_refs
        )
        source_signals.extend(contract.source_refs)
        source_signals.extend(contract.evidence_refs)
        source_signals.extend(
            f"technology://blocker/{blocker}" for blocker in contract.blockers
        )

        return self.create_proposal(
            proposal_type="technology_absorption_candidate",
            target_scope=target_scope or f"technology:{contract.technology_name}",
            hypothesis=contract.hypothesis,
            expected_gain=contract.expected_gain,
            baseline_refs=[
                "baseline://sovereign-core/current",
                *[f"gap://{ref}" for ref in contract.target_gap_refs],
            ],
            source_signals=source_signals,
            risk_hint=contract.risk_hint,
            proposed_tests=contract.proposed_tests,
            strategy_name=strategy_name,
            candidate_refs=[contract.candidate_ref],
            evaluation_matrix={
                "technology_absorption": {
                    "technology_name": contract.technology_name,
                    "absorption_class": contract.absorption_class,
                    "candidate_status": contract.status,
                    "requested_core_role": contract.requested_core_role,
                    "absorption_readiness": absorption_state["absorption_readiness"],
                    "absorption_decision": absorption_state["absorption_decision"],
                    "experiment_lane_status": absorption_state["experiment_lane_status"],
                    "promotion_readiness": absorption_state["promotion_readiness"],
                    "blockers": list(absorption_state["blockers"]),
                }
            },
            strategy_context={
                "technology_absorption_candidate": {
                    "candidate_ref": contract.candidate_ref,
                    "technology_name": contract.technology_name,
                    "target_gap_refs": list(contract.target_gap_refs),
                    "requires_sandbox": contract.sandbox_required,
                    "requires_human_review": contract.human_review_required,
                    "rollback_plan_ref": contract.rollback_plan_ref,
                },
                "technology_absorption_state": absorption_state,
                "promotion_policy": {
                    "automatic_promotion": False,
                    "core_replacement_allowed": False,
                    "manual_review_required": contract.human_review_required,
                },
            },
        )

    def create_proposal_from_post_task_reflection(
        self,
        reflection_input: PostTaskReflectionInput,
        *,
        target_scope: str | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a sandbox-only proposal from bounded post-task reflection."""

        blockers = list(reflection_input.failure_modes)
        if reflection_input.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if reflection_input.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if not reflection_input.evidence_refs:
            blockers.append("evidence_required")
        experience = ExperienceRecordContract(
            experience_id=reflection_input.experience_id,
            mission_id=reflection_input.mission_id,
            workflow_profile=reflection_input.workflow_profile,
            outcome_status=reflection_input.outcome_status,
            timestamp=self.now(),
            objective_ref=reflection_input.objective_ref,
            surface_id=reflection_input.surface_id,
            evidence_refs=list(reflection_input.evidence_refs),
            signal_refs=list(reflection_input.signal_refs),
            failure_modes=list(reflection_input.failure_modes),
            decision_refs=list(reflection_input.decision_refs),
            learned_patterns=list(reflection_input.learned_patterns),
            next_action_ref=reflection_input.next_action_ref,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )
        reflection = PostTaskReflectionContract(
            reflection_id=f"reflection://{self._signal_value(experience.experience_id)}",
            experience_id=experience.experience_id,
            reflection_status="blocked" if blockers else "candidate",
            learning_candidate=reflection_input.learning_candidate,
            recommendation=reflection_input.recommendation,
            proposed_change_type=reflection_input.proposed_change_type,
            evidence_refs=list(reflection_input.evidence_refs),
            proposed_tests=list(reflection_input.proposed_tests),
            blockers=self._unique_values(blockers),
            rollback_plan_ref=reflection_input.rollback_plan_ref,
            risk_hint=reflection_input.risk_hint,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
            timestamp=self.now(),
        )
        source_signals = [
            f"experience://mission/{self._signal_value(str(experience.mission_id))}",
            f"experience://workflow/{self._signal_value(experience.workflow_profile)}",
            f"experience://outcome/{self._signal_value(experience.outcome_status)}",
            f"reflection://status/{reflection.reflection_status}",
            f"reflection://change-type/{self._signal_value(reflection.proposed_change_type)}",
        ]
        source_signals.extend(experience.signal_refs)
        source_signals.extend(experience.evidence_refs)
        source_signals.extend(f"reflection://blocker/{item}" for item in reflection.blockers)

        return self.create_proposal(
            proposal_type="post_task_reflection_improvement",
            target_scope=target_scope or f"workflow:{experience.workflow_profile}",
            hypothesis=reflection.learning_candidate,
            expected_gain=reflection.recommendation,
            baseline_refs=[
                "baseline://sovereign-core/current",
                f"experience://{experience.experience_id}",
            ],
            source_signals=source_signals,
            risk_hint=reflection.risk_hint,
            proposed_tests=reflection.proposed_tests,
            strategy_name=strategy_name,
            candidate_refs=[experience.experience_id, reflection.reflection_id],
            evaluation_matrix={
                "post_task_reflection": {
                    "workflow_profile": experience.workflow_profile,
                    "outcome_status": experience.outcome_status,
                    "reflection_status": reflection.reflection_status,
                    "proposed_change_type": reflection.proposed_change_type,
                    "blockers": list(reflection.blockers),
                    "manual_review_required": reflection.human_review_required,
                }
            },
            strategy_context={
                "experience_record": {
                    "experience_id": experience.experience_id,
                    "mission_id": str(experience.mission_id),
                    "objective_ref": experience.objective_ref,
                    "surface_id": experience.surface_id,
                    "reusable_memory_status": experience.reusable_memory_status,
                },
                "post_task_reflection": {
                    "reflection_id": reflection.reflection_id,
                    "learning_candidate": reflection.learning_candidate,
                    "recommendation": reflection.recommendation,
                    "rollback_plan_ref": reflection.rollback_plan_ref,
                },
                "promotion_policy": {
                    "automatic_promotion": False,
                    "core_mutation_allowed": False,
                    "manual_review_required": True,
                },
                "evolution_review": self._review_context(
                    status="needs_review",
                    blockers=list(reflection.blockers),
                    rollback_plan_ref=reflection.rollback_plan_ref,
                ),
            },
            optimization_candidate_status=(
                "blocked" if reflection.blockers else "candidate"
            ),
            optimization_safety_status=(
                "blocked_by_safety" if reflection.blockers else "sandbox_only"
            ),
            optimization_blockers=list(reflection.blockers),
        )

    def create_proposal_from_operator_feedback(
        self,
        feedback: OperatorFeedbackContract,
        *,
        experience: ExperienceRecordContract,
        reflection: PostTaskReflectionContract,
        target_scope: str | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a human-review-only proposal from explicit operator feedback."""

        if feedback.experience_id != experience.experience_id:
            raise ValueError("operator feedback does not match experience")
        if reflection.experience_id != experience.experience_id:
            raise ValueError("reflection does not match operator feedback experience")
        if str(feedback.mission_id) != str(experience.mission_id):
            raise ValueError("operator feedback does not match experience mission")
        if feedback.automatic_promotion_allowed or feedback.core_mutation_allowed:
            raise ValueError("operator feedback cannot authorize autonomous mutation")
        if feedback.feedback_status != "recorded_bounded":
            raise ValueError("operator feedback must be recorded before proposal creation")

        blockers = self._unique_values(list(reflection.blockers))
        source_signals = self._unique_values(
            [
                feedback.feedback_id,
                f"operator-feedback://assessment/{feedback.assessment}",
                *(
                    [f"operator-feedback://rating/{feedback.rating}"]
                    if feedback.rating is not None
                    else []
                ),
                *feedback.evidence_refs,
                experience.experience_id,
                reflection.reflection_id,
            ]
        )
        expected_gain = (
            feedback.next_expectation
            or feedback.correction
            or feedback.comment
            or "align future governed decisions with explicit operator assessment"
        )
        hypothesis = (
            "Explicit operator feedback can improve the bounded workflow without "
            "changing the sovereign core autonomously."
        )
        proposed_tests = self._unique_values(
            [
                *reflection.proposed_tests,
                "compare_future_decision_with_operator_feedback_baseline",
            ]
        )
        return self.create_proposal(
            proposal_type="operator_feedback_improvement",
            target_scope=target_scope or f"workflow:{experience.workflow_profile}",
            hypothesis=hypothesis,
            expected_gain=expected_gain,
            baseline_refs=[
                "baseline://sovereign-core/current",
                experience.experience_id,
                reflection.reflection_id,
            ],
            source_signals=source_signals,
            risk_hint=reflection.risk_hint or "low",
            proposed_tests=proposed_tests,
            strategy_name=strategy_name,
            candidate_refs=[
                feedback.feedback_id,
                experience.experience_id,
                reflection.reflection_id,
            ],
            evaluation_matrix={
                "operator_feedback": {
                    "feedback_status": feedback.feedback_status,
                    "assessment": feedback.assessment,
                    "rating": feedback.rating,
                    "workflow_profile": experience.workflow_profile,
                    "route": experience.route,
                    "domain": experience.primary_domain_driver,
                    "manual_review_required": True,
                    "automatic_promotion_allowed": False,
                }
            },
            strategy_context={
                "operator_feedback": {
                    "feedback_id": feedback.feedback_id,
                    "experience_id": feedback.experience_id,
                    "mission_id": str(feedback.mission_id),
                    "assessment": feedback.assessment,
                    "rating": feedback.rating,
                    "comment": feedback.comment,
                    "correction": feedback.correction,
                    "next_expectation": feedback.next_expectation,
                    "operator_ref": feedback.operator_ref,
                    "evidence_refs": list(feedback.evidence_refs),
                    "feedback_status": feedback.feedback_status,
                },
                "promotion_policy": {
                    "automatic_promotion": False,
                    "core_mutation_allowed": False,
                    "manual_review_required": True,
                },
                "evolution_review": self._review_context(
                    status="needs_review",
                    blockers=blockers,
                    rollback_plan_ref=reflection.rollback_plan_ref,
                ),
            },
            optimization_candidate_status="blocked" if blockers else "candidate",
            optimization_safety_status=(
                "blocked_by_safety" if blockers else "sandbox_only"
            ),
            optimization_blockers=blockers,
        )

    @classmethod
    def mine_skill_candidate(
        cls,
        *,
        pattern: RecurringPatternEvidenceContract,
        request: SkillMiningRequestContract,
        minimum_occurrences: int = 2,
    ) -> SkillMiningResultContract:
        """Compile eligible recurrence evidence into one inactive skill candidate."""

        if minimum_occurrences < 2:
            raise ValueError("skill mining requires at least two occurrences")
        threshold = max(minimum_occurrences, pattern.minimum_occurrences)
        blockers = list(pattern.blockers)
        if request.source_pattern_ref != pattern.pattern_id:
            blockers.append("source_pattern_ref_mismatch")
        if pattern.pattern_status != "evidence_ready_for_human_review":
            blockers.append("pattern_not_eligible_for_skill_mining")
        if pattern.occurrence_count < threshold:
            blockers.append("recurrence_threshold_not_met")
        if pattern.successful_occurrences < threshold:
            blockers.append("successful_outcome_threshold_not_met")
        if pattern.non_successful_occurrences:
            blockers.append("non_successful_outcomes_require_review")
        if pattern.conflict_flags:
            blockers.append("pattern_conflict_requires_review")
        if pattern.confidence_status not in {"bounded_moderate", "bounded_high"}:
            blockers.append("bounded_confidence_required")
        if len(set(pattern.experience_refs)) < threshold:
            blockers.append("distinct_experience_evidence_required")
        if len(set(pattern.reflection_refs)) < threshold:
            blockers.append("distinct_reflection_evidence_required")
        if not pattern.evidence_refs:
            blockers.append("pattern_evidence_required")
        if not pattern.human_review_required:
            blockers.append("human_review_invariant_required")
        if pattern.automatic_skill_creation_allowed:
            blockers.append("source_claims_automatic_skill_creation")
        if pattern.automatic_promotion_allowed:
            blockers.append("source_claims_automatic_promotion")
        if pattern.core_mutation_allowed:
            blockers.append("source_claims_core_mutation")

        scalar_fields = {
            "mining_request_id": request.mining_request_id,
            "skill_id": request.skill_id,
            "skill_name": request.skill_name,
            "specialist_type": request.specialist_type,
            "rollback_plan_ref": request.rollback_plan_ref,
        }
        for field_name, value in scalar_fields.items():
            if not value or len(value) > 240:
                blockers.append(f"{field_name}_required_and_bounded")
        if cls._numeric_semver(request.version) is False:
            blockers.append("numeric_semver_required")
        try:
            risk_level = RiskLevel(str(request.risk_level))
        except ValueError:
            risk_level = RiskLevel.CRITICAL
            blockers.append("valid_risk_level_required")
        if risk_level not in {RiskLevel.LOW, RiskLevel.MODERATE}:
            blockers.append("risk_exceeds_bounded_miner_limit")

        bounded_fields: dict[str, list[str]] = {}
        for field_name, values, max_items, item_limit in (
            ("inputs", request.inputs, 20, 200),
            ("outputs", request.outputs, 20, 200),
            ("allowed_tools", request.allowed_tools, 20, 200),
            ("bounded_instructions", request.bounded_instructions, 12, 500),
            ("failure_modes", request.failure_modes, 20, 200),
            ("proposed_tests", request.proposed_tests, 20, 500),
        ):
            unique_values = cls._unique_values(values)
            if len(unique_values) > max_items or any(
                len(value) > item_limit for value in unique_values
            ):
                blockers.append(f"{field_name}_must_be_bounded")
            bounded_fields[field_name] = [
                value[:item_limit] for value in unique_values[:max_items]
            ]
        for required_field in (
            "inputs",
            "outputs",
            "bounded_instructions",
            "failure_modes",
            "proposed_tests",
        ):
            if not bounded_fields[required_field]:
                blockers.append(f"{required_field}_required")
        if any(
            tool.strip().lower() in {"*", "all", "any", "unrestricted"}
            for tool in bounded_fields["allowed_tools"]
        ):
            blockers.append("allowed_tools_must_be_explicit")
        if request.automatic_mining_allowed:
            blockers.append("automatic_mining_not_allowed")
        if request.automatic_activation_allowed:
            blockers.append("automatic_activation_not_allowed")
        if request.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if request.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if not request.human_review_required:
            blockers.append("human_review_invariant_required")

        resolved_blockers = cls._unique_values(blockers)
        evidence_refs = cls._unique_values(
            [
                pattern.pattern_id,
                *pattern.experience_refs,
                *pattern.reflection_refs,
                *pattern.feedback_refs,
                *pattern.evidence_refs,
            ]
        )[:200]
        result_seed = (
            f"{request.mining_request_id}:{pattern.pattern_id}:"
            f"{request.skill_id}:{request.version}"
        )
        result_hash = sha256(result_seed.encode("utf-8")).hexdigest()[:16]
        candidate_seed = f"{pattern.pattern_id}:{request.skill_id}:{request.version}"
        candidate_hash = sha256(candidate_seed.encode("utf-8")).hexdigest()[:16]
        candidate: SkillCandidateContract | None = None
        if not resolved_blockers:
            candidate = SkillCandidateContract(
                skill_candidate_id=(
                    f"skill-candidate://{candidate_hash}/{request.version}"
                ),
                skill_id=request.skill_id,
                skill_name=request.skill_name,
                version=request.version,
                workflow_profile=pattern.workflow_profile,
                domain=pattern.domain,
                specialist_type=request.specialist_type,
                inputs=bounded_fields["inputs"],
                outputs=bounded_fields["outputs"],
                allowed_tools=bounded_fields["allowed_tools"],
                bounded_instructions=bounded_fields["bounded_instructions"],
                risk_level=risk_level,
                evidence_refs=evidence_refs,
                source_pattern_refs=[pattern.pattern_id],
                failure_modes=bounded_fields["failure_modes"],
                proposed_tests=bounded_fields["proposed_tests"],
                rollback_plan_ref=request.rollback_plan_ref,
                timestamp=pattern.generated_at,
            )

        return SkillMiningResultContract(
            mining_result_id=f"skill-mining-result://{result_hash}",
            mining_status=(
                "candidate_created_inactive" if candidate is not None else "blocked"
            ),
            eligibility_status="eligible" if candidate is not None else "ineligible",
            source_pattern_ref=pattern.pattern_id,
            source_authority_status="observation_only_requires_miner_and_review",
            threshold_occurrences=threshold,
            observed_occurrences=pattern.occurrence_count,
            blockers=resolved_blockers,
            evidence_refs=evidence_refs,
            generated_at=request.timestamp,
            candidate=candidate,
        )

    @staticmethod
    def _numeric_semver(value: str) -> bool:
        parts = value.split(".")
        return len(parts) == 3 and all(part.isdigit() for part in parts)

    def create_proposal_from_skill_candidate(
        self,
        candidate: SkillCandidateContract,
        *,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Persist a sandbox-only proposal without activating the skill candidate."""

        blockers = list(candidate.blockers)
        if candidate.registry_status != "candidate_inactive":
            blockers.append("inactive_registry_candidate_required")
        if candidate.review_status != "needs_review":
            blockers.append("human_review_required_before_skill_proposal")
        if candidate.activation_status != "inactive":
            blockers.append("inactive_skill_candidate_required")
        if not candidate.sandbox_required:
            blockers.append("sandbox_required")
        if not candidate.evidence_refs or not candidate.source_pattern_refs:
            blockers.append("pattern_and_evidence_refs_required")
        if not candidate.proposed_tests:
            blockers.append("tests_required")
        if not candidate.rollback_plan_ref:
            blockers.append("rollback_plan_required")
        if candidate.automatic_activation_allowed:
            blockers.append("automatic_activation_not_allowed")
        if candidate.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if candidate.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        blockers = self._unique_values(blockers)
        candidate_refs = self._unique_values(
            [
                candidate.skill_candidate_id,
                candidate.skill_id,
                *candidate.source_pattern_refs,
            ]
        )
        source_signals = self._unique_values(
            [
                f"skill://candidate/{self._signal_value(candidate.skill_candidate_id)}",
                f"skill://identity/{self._signal_value(candidate.skill_id)}",
                f"skill://version/{candidate.version}",
                f"skill://workflow/{self._signal_value(candidate.workflow_profile)}",
                f"skill://domain/{self._signal_value(candidate.domain)}",
                "skill://activation/inactive",
                "skill://promotion/manual_review_and_release_gate_required",
                *candidate.evidence_refs,
                *candidate.source_pattern_refs,
                *(f"skill://blocker/{item}" for item in blockers),
            ]
        )
        return self.create_proposal(
            proposal_type="skill_candidate",
            target_scope=f"skill:{candidate.skill_id}@{candidate.version}",
            hypothesis=f"sandbox skill candidate {candidate.skill_name}",
            expected_gain=(
                "reuse reviewed recurring behavior after sandbox and human release"
            ),
            baseline_refs=self._unique_values(
                ["baseline://sovereign-core/current", *candidate.evidence_refs]
            ),
            source_signals=source_signals,
            risk_hint=str(candidate.risk_level),
            proposed_tests=list(candidate.proposed_tests),
            strategy_name=strategy_name,
            candidate_refs=candidate_refs,
            evaluation_matrix={
                "skill_candidate": {
                    "skill_candidate_id": candidate.skill_candidate_id,
                    "skill_id": candidate.skill_id,
                    "skill_name": candidate.skill_name,
                    "version": candidate.version,
                    "workflow_profile": candidate.workflow_profile,
                    "domain": candidate.domain,
                    "specialist_type": candidate.specialist_type,
                    "risk_level": str(candidate.risk_level),
                    "registry_status": candidate.registry_status,
                    "review_status": candidate.review_status,
                    "activation_status": candidate.activation_status,
                    "blockers": blockers,
                    "runtime_activation_allowed": False,
                }
            },
            strategy_context={
                "skill_candidate": {
                    "skill_candidate_id": candidate.skill_candidate_id,
                    "skill_id": candidate.skill_id,
                    "skill_name": candidate.skill_name,
                    "version": candidate.version,
                    "workflow_profile": candidate.workflow_profile,
                    "domain": candidate.domain,
                    "specialist_type": candidate.specialist_type,
                    "inputs": list(candidate.inputs),
                    "outputs": list(candidate.outputs),
                    "allowed_tools": list(candidate.allowed_tools),
                    "bounded_instructions": list(candidate.bounded_instructions),
                    "failure_modes": list(candidate.failure_modes),
                    "source_pattern_refs": list(candidate.source_pattern_refs),
                    "rollback_plan_ref": candidate.rollback_plan_ref,
                    "activation_status": "inactive",
                },
                "promotion_policy": {
                    "automatic_activation": False,
                    "automatic_promotion": False,
                    "core_mutation_allowed": False,
                    "human_review_required": True,
                    "sandbox_eval_required": True,
                    "release_gate_required": True,
                },
                "evolution_review": self._review_context(
                    status="needs_review",
                    blockers=blockers,
                    rollback_plan_ref=candidate.rollback_plan_ref,
                ),
            },
            optimization_candidate_status="blocked" if blockers else "candidate",
            optimization_safety_status=(
                "blocked_by_safety" if blockers else "sandbox_only"
            ),
            optimization_blockers=blockers,
        )

    def evaluate_skill_candidate_in_sandbox(
        self,
        *,
        candidate: SkillCandidateContract,
        proposal: EvolutionProposalContract,
        review_decision: EvolutionReviewDecisionContract,
        test_cases: dict[str, dict[str, bool]],
        evidence_refs: list[str],
        generated_at: str,
        required_pass_rate: float = 1.0,
    ) -> SkillSandboxEvalContract:
        """Derive sandbox evidence while keeping runtime activation impossible."""

        if not 0.0 < required_pass_rate <= 1.0:
            raise ValueError("required_pass_rate must be greater than zero and at most one")
        if str(review_decision.evolution_proposal_id) != str(
            proposal.evolution_proposal_id
        ):
            raise ValueError("review decision does not belong to the skill proposal")
        blockers = list(candidate.blockers)
        skill_context = dict(proposal.evaluation_matrix.get("skill_candidate", {}))
        if proposal.proposal_type != "skill_candidate":
            blockers.append("skill_candidate_proposal_required")
        if candidate.skill_candidate_id not in proposal.candidate_refs:
            blockers.append("skill_candidate_ref_mismatch")
        if skill_context.get("skill_id") != candidate.skill_id:
            blockers.append("skill_identity_mismatch")
        if skill_context.get("version") != candidate.version:
            blockers.append("skill_version_mismatch")
        if review_decision.review_status not in {"approved", "sandboxed"}:
            blockers.append("human_sandbox_review_required")
        if review_decision.candidate_identity_ref != candidate.skill_id:
            blockers.append("review_skill_identity_mismatch")
        if review_decision.candidate_version != candidate.version:
            blockers.append("review_skill_version_mismatch")
        if review_decision.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if review_decision.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if candidate.activation_status != "inactive":
            blockers.append("inactive_skill_candidate_required")
        if not test_cases:
            blockers.append("sandbox_test_cases_required")
        if len(test_cases) > 50:
            blockers.append("sandbox_test_case_limit_exceeded")

        case_results: list[SkillSandboxCaseResultContract] = []
        for case_id, checks in list(test_cases.items())[:50]:
            case_blockers: list[str] = []
            if not case_id or len(case_id) > 160:
                case_blockers.append("case_id_required_and_bounded")
            if not checks:
                case_blockers.append("case_checks_required")
            if len(checks) > 50:
                case_blockers.append("case_check_limit_exceeded")
            if any(not isinstance(value, bool) for value in checks.values()):
                case_blockers.append("case_checks_must_be_boolean")
            safe_checks = {
                str(name)[:160]: bool(value)
                for name, value in list(checks.items())[:50]
            }
            failed_checks = [
                name for name, passed in safe_checks.items() if not passed
            ]
            failed_checks.extend(case_blockers)
            passed = bool(safe_checks) and not failed_checks
            case_evidence = [
                f"skill-sandbox-case://{self._signal_value(case_id or 'invalid')}"
            ]
            case_results.append(
                SkillSandboxCaseResultContract(
                    case_id=case_id[:160] or "invalid_case",
                    passed=passed,
                    checks=safe_checks,
                    failed_checks=self._unique_values(failed_checks),
                    evidence_refs=case_evidence,
                )
            )
            blockers.extend(
                f"case:{case_id or 'invalid'}:{item}" for item in case_blockers
            )

        total_cases = len(case_results)
        passed_cases = sum(result.passed for result in case_results)
        failed_cases = total_cases - passed_cases
        pass_rate = round(passed_cases / total_cases, 4) if total_cases else 0.0
        if pass_rate < required_pass_rate:
            blockers.append("sandbox_pass_rate_below_threshold")
        safe_evidence_refs = self._unique_values(
            [
                candidate.skill_candidate_id,
                candidate.skill_id,
                f"skill-version://{candidate.version}",
                str(proposal.evolution_proposal_id),
                review_decision.review_decision_id,
                *candidate.evidence_refs,
                *review_decision.evidence_refs,
                *evidence_refs,
                *(
                    ref
                    for result in case_results
                    for ref in result.evidence_refs
                ),
            ]
        )[:250]
        if not evidence_refs:
            blockers.append("external_sandbox_evidence_required")
        if not review_decision.proposed_tests or not candidate.proposed_tests:
            blockers.append("proposed_tests_required")
        if review_decision.rollback_plan_ref != candidate.rollback_plan_ref:
            blockers.append("rollback_plan_mismatch")
        resolved_blockers = self._unique_values(blockers)
        eval_seed = (
            f"{candidate.skill_candidate_id}:"
            f"{proposal.evolution_proposal_id}:{review_decision.review_decision_id}"
        )
        eval_id = (
            "skill-sandbox-eval://"
            f"{sha256(eval_seed.encode('utf-8')).hexdigest()[:16]}"
        )
        eval_result = SkillSandboxEvalContract(
            eval_id=eval_id,
            skill_candidate_id=candidate.skill_candidate_id,
            skill_id=candidate.skill_id,
            version=candidate.version,
            evolution_proposal_id=proposal.evolution_proposal_id,
            review_decision_id=review_decision.review_decision_id,
            eval_status=(
                "passed_pending_release_gate" if not resolved_blockers else "blocked"
            ),
            required_pass_rate=required_pass_rate,
            pass_rate=pass_rate,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            case_results=case_results,
            evidence_refs=safe_evidence_refs,
            proposed_tests=self._unique_values(
                [*candidate.proposed_tests, *review_decision.proposed_tests]
            ),
            rollback_plan_ref=candidate.rollback_plan_ref,
            blockers=resolved_blockers,
            generated_at=generated_at,
        )
        current_proposal = self.repository.fetch_proposal(
            str(proposal.evolution_proposal_id)
        ) or proposal
        context = dict(current_proposal.strategy_context)
        context["skill_sandbox_eval"] = {
            "eval_id": eval_result.eval_id,
            "skill_candidate_id": eval_result.skill_candidate_id,
            "skill_id": eval_result.skill_id,
            "version": eval_result.version,
            "eval_status": eval_result.eval_status,
            "pass_rate": eval_result.pass_rate,
            "blockers": list(eval_result.blockers),
            "runtime_activation_allowed": False,
            "promotion_authorized": False,
        }
        self.repository.record_proposal(
            replace(current_proposal, strategy_context=context)
        )
        return eval_result

    def create_proposal_from_procedural_playbook_candidate(
        self,
        candidate: ProceduralPlaybookCandidateContract,
        *,
        target_scope: str | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Create a sandbox-only proposal from a procedural playbook candidate."""

        blockers = list(candidate.blockers)
        if candidate.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if candidate.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if not candidate.evidence_refs:
            blockers.append("evidence_required")
        if not candidate.rollback_plan_ref:
            blockers.append("rollback_plan_required")
        if candidate.review_status not in {"candidate", "needs_review"}:
            blockers.append("manual_review_required_before_promotion")
        bounded_steps = list(candidate.bounded_steps)[:8]
        source_signals = [
            f"playbook://candidate/{self._signal_value(candidate.playbook_candidate_id)}",
            f"playbook://workflow/{self._signal_value(candidate.workflow_profile)}",
            f"playbook://status/{candidate.review_status}",
            "playbook://promotion/manual_review_required",
        ]
        source_signals.extend(candidate.evidence_refs)
        source_signals.extend(candidate.source_artifact_refs)
        source_signals.extend(candidate.source_reflection_refs)
        source_signals.extend(f"playbook://blocker/{item}" for item in blockers)

        return self.create_proposal(
            proposal_type="procedural_playbook_candidate",
            target_scope=target_scope or f"workflow:{candidate.workflow_profile}",
            hypothesis=(
                f"candidate procedural playbook for {candidate.procedure_name}"
            ),
            expected_gain="reuse bounded procedure after human review and release gate",
            baseline_refs=[
                "baseline://sovereign-core/current",
                *candidate.source_artifact_refs,
                *candidate.source_reflection_refs,
            ],
            source_signals=self._unique_values(source_signals),
            risk_hint=candidate.risk_hint,
            proposed_tests=list(candidate.proposed_tests),
            strategy_name=strategy_name,
            candidate_refs=[candidate.playbook_candidate_id],
            evaluation_matrix={
                "procedural_playbook_candidate": {
                    "procedure_name": candidate.procedure_name,
                    "workflow_profile": candidate.workflow_profile,
                    "route": candidate.route,
                    "domain": candidate.domain,
                    "bounded_step_count": len(bounded_steps),
                    "review_status": candidate.review_status,
                    "blockers": self._unique_values(blockers),
                    "manual_review_required": True,
                }
            },
            strategy_context={
                "procedural_playbook_candidate": {
                    "playbook_candidate_id": candidate.playbook_candidate_id,
                    "procedure_name": candidate.procedure_name,
                    "bounded_steps": bounded_steps,
                    "rollback_plan_ref": candidate.rollback_plan_ref,
                    "memory_write_mode": candidate.memory_write_mode,
                },
                "promotion_policy": {
                    "automatic_promotion": False,
                    "core_mutation_allowed": False,
                    "manual_review_required": True,
                    "release_gate_required": True,
                },
                "evolution_review": self._review_context(
                    status="needs_review",
                    blockers=self._unique_values(blockers),
                    rollback_plan_ref=candidate.rollback_plan_ref,
                ),
            },
            optimization_candidate_status="blocked" if blockers else "candidate",
            optimization_safety_status=(
                "blocked_by_safety" if blockers else "sandbox_only"
            ),
            optimization_blockers=self._unique_values(blockers),
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

    def list_human_review_queue(
        self,
        limit: int = 20,
    ) -> list[EvolutionReviewQueueItemContract]:
        """Return reviewable evolution proposals without promoting anything."""

        proposals = self.repository.list_proposals(limit=limit)
        return [self._proposal_to_review_item(proposal) for proposal in proposals]

    def list_recent_decisions(self, limit: int = 20) -> list[EvolutionDecisionContract]:
        """Return recent evolution decisions for local review."""

        return self.repository.list_decisions(limit=limit)

    def review_proposal(
        self,
        *,
        evolution_proposal_id: str,
        action: str,
        operator_ref: str,
        evidence_refs: list[str] | None = None,
        proposed_tests: list[str] | None = None,
        rollback_plan_ref: str | None = None,
        risk_acceptance: str | None = None,
        review_notes: list[str] | None = None,
    ) -> EvolutionReviewDecisionContract:
        """Record a human review decision without automatic promotion."""

        proposal = self.repository.fetch_proposal(evolution_proposal_id)
        if proposal is None:
            raise ValueError(f"unknown evolution proposal: {evolution_proposal_id}")
        normalized_action = action.replace("-", "_")
        if normalized_action not in EVOLUTION_REVIEW_ACTIONS:
            raise ValueError(f"unsupported evolution review action: {action}")

        safe_evidence_refs = self._unique_values(list(evidence_refs or []))
        safe_tests = self._unique_values(list(proposed_tests or proposal.proposed_tests))
        safe_notes = list(review_notes or [])
        safe_rollback_ref = rollback_plan_ref or self._proposal_rollback_plan_ref(proposal)
        blockers = self._review_action_blockers(
            action=normalized_action,
            evidence_refs=safe_evidence_refs,
            proposed_tests=safe_tests,
            rollback_plan_ref=safe_rollback_ref,
        )
        review_status = (
            "needs_review"
            if blockers and normalized_action in RISKY_REVIEW_ACTIONS
            else EVOLUTION_REVIEW_ACTIONS[normalized_action]
        )
        candidate_identity_ref, candidate_version = self._proposal_candidate_metadata(
            proposal
        )
        decision = EvolutionReviewDecisionContract(
            review_decision_id=(
                f"review-decision://{proposal.evolution_proposal_id}/{uuid4().hex[:8]}"
            ),
            evolution_proposal_id=proposal.evolution_proposal_id,
            review_status=review_status,
            decision=normalized_action,
            operator_ref=operator_ref,
            evidence_refs=safe_evidence_refs,
            proposed_tests=safe_tests,
            rollback_plan_ref=safe_rollback_ref,
            risk_acceptance=risk_acceptance,
            review_notes=safe_notes + blockers,
            candidate_identity_ref=candidate_identity_ref,
            candidate_version=candidate_version,
            timestamp=self.now(),
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )
        self.repository.record_proposal(
            replace(
                proposal,
                strategy_context=self._strategy_context_with_review_decision(
                    proposal=proposal,
                    decision=decision,
                    blockers=blockers,
                ),
            )
        )
        self.repository.record_decision(
            self._review_decision_to_evolution_decision(
                proposal=proposal,
                decision=decision,
                blockers=blockers,
            )
        )
        return decision

    def derive_reviewed_learning_guidance(
        self,
        decision: EvolutionReviewDecisionContract,
        *,
        expires_at: str | None = None,
    ) -> ReviewedLearningGuidanceContract:
        """Derive bounded runtime guidance from an approved human review."""

        if decision.review_status not in REVIEWED_LEARNING_GUIDANCE_STATUSES:
            raise ValueError(
                "reviewed learning guidance requires approved or sandboxed review"
            )
        if decision.automatic_promotion_allowed or decision.core_mutation_allowed:
            raise ValueError("review decision cannot authorize autonomous mutation")
        proposal = self.repository.fetch_proposal(str(decision.evolution_proposal_id))
        if proposal is None:
            raise ValueError(
                f"unknown evolution proposal: {decision.evolution_proposal_id}"
            )
        route, workflow_profile, domain = self._reviewed_guidance_scope(proposal)
        guidance_summary = self._reviewed_guidance_summary(proposal)
        return ReviewedLearningGuidanceContract(
            guidance_id=(
                "reviewed-learning-guidance://"
                f"{self._signal_value(decision.review_decision_id)}"
            ),
            source_review_decision_id=decision.review_decision_id,
            evolution_proposal_id=proposal.evolution_proposal_id,
            review_status=decision.review_status,
            route=route,
            workflow_profile=workflow_profile,
            domain=domain,
            guidance_summary=guidance_summary,
            allowed_usage=self._reviewed_guidance_allowed_usage(decision.review_status),
            evidence_refs=self._unique_values(
                [*decision.evidence_refs, *proposal.baseline_refs]
            ),
            rollback_plan_ref=decision.rollback_plan_ref
            or self._proposal_rollback_plan_ref(proposal),
            timestamp=self.now(),
            expires_at=expires_at,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

    def build_sandbox_to_release_checklist(
        self,
        proposal: EvolutionProposalContract,
        *,
        review_decision: EvolutionReviewDecisionContract | None = None,
        skill_sandbox_eval: SkillSandboxEvalContract | None = None,
    ) -> SandboxToReleaseChecklistContract:
        """Build an executable checklist without authorizing promotion."""

        if review_decision is not None and str(
            review_decision.evolution_proposal_id
        ) != str(proposal.evolution_proposal_id):
            raise ValueError(
                "review decision does not belong to the evolution proposal"
            )
        if skill_sandbox_eval is not None and str(
            skill_sandbox_eval.evolution_proposal_id
        ) != str(proposal.evolution_proposal_id):
            raise ValueError("skill sandbox eval does not belong to the proposal")
        review_context = dict(proposal.strategy_context.get("evolution_review", {}))
        human_review_status = (
            review_decision.review_status
            if review_decision is not None
            else str(review_context.get("review_status") or "needs_review")
        )
        review_evidence = list(
            review_decision.evidence_refs if review_decision else []
        )
        evidence_refs = self._unique_values(
            [
                *(review_evidence or self._proposal_evidence_refs(proposal)),
                *list(skill_sandbox_eval.evidence_refs if skill_sandbox_eval else []),
            ]
        )
        proposed_tests = self._unique_values(
            [
                *list(proposal.proposed_tests),
                *list(review_decision.proposed_tests if review_decision else []),
                *list(skill_sandbox_eval.proposed_tests if skill_sandbox_eval else []),
            ]
        )
        rollback_plan_ref = (
            review_decision.rollback_plan_ref
            if review_decision is not None
            else self._proposal_rollback_plan_ref(proposal)
        )
        blockers = list(proposal.optimization_blockers)
        if human_review_status not in {"approved", "sandboxed"}:
            blockers.append("human_approval_required")
        if review_decision is not None and (
            review_decision.automatic_promotion_allowed
            or review_decision.core_mutation_allowed
        ):
            blockers.append("review_decision_cannot_authorize_autonomous_mutation")
        if not evidence_refs:
            blockers.append("evidence_required")
        if not proposed_tests:
            blockers.append("tests_required")
        if not rollback_plan_ref:
            blockers.append("rollback_plan_required")
        if not proposal.requires_sandbox:
            blockers.append("sandbox_required")
        candidate_type: str | None = None
        candidate_identity_ref: str | None = None
        candidate_version: str | None = None
        sandbox_eval_ref: str | None = None
        sandbox_eval_status: str | None = None
        required_gates = [
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ]
        if proposal.proposal_type == "skill_candidate":
            candidate_type = "skill_candidate"
            candidate_identity_ref, candidate_version = (
                self._proposal_candidate_metadata(proposal)
            )
            required_gates.append("skill_sandbox_eval")
            if not candidate_identity_ref or not candidate_version:
                blockers.append("skill_identity_and_version_required")
            if review_decision is None:
                blockers.append("skill_human_review_decision_required")
            elif (
                review_decision.candidate_identity_ref != candidate_identity_ref
                or review_decision.candidate_version != candidate_version
            ):
                blockers.append("skill_review_metadata_mismatch")
            if skill_sandbox_eval is None:
                blockers.append("skill_sandbox_eval_required")
            else:
                sandbox_eval_ref = skill_sandbox_eval.eval_id
                sandbox_eval_status = skill_sandbox_eval.eval_status
                if skill_sandbox_eval.skill_id != candidate_identity_ref:
                    blockers.append("skill_sandbox_eval_identity_mismatch")
                if skill_sandbox_eval.version != candidate_version:
                    blockers.append("skill_sandbox_eval_version_mismatch")
                if skill_sandbox_eval.review_decision_id != (
                    review_decision.review_decision_id if review_decision else None
                ):
                    blockers.append("skill_sandbox_eval_review_mismatch")
                if skill_sandbox_eval.eval_status != "passed_pending_release_gate":
                    blockers.append("skill_sandbox_eval_not_passed")
                if skill_sandbox_eval.runtime_activation_allowed:
                    blockers.append("runtime_activation_not_allowed")
                if skill_sandbox_eval.promotion_authorized:
                    blockers.append("sandbox_eval_cannot_authorize_promotion")
                blockers.extend(skill_sandbox_eval.blockers)
        blockers = self._unique_values(blockers)
        return SandboxToReleaseChecklistContract(
            checklist_id=(
                "sandbox-release-checklist://"
                f"{self._signal_value(proposal.evolution_proposal_id)}"
            ),
            evolution_proposal_id=proposal.evolution_proposal_id,
            release_scope=proposal.target_scope,
            checklist_status=(
                "ready_for_release_review" if not blockers else "blocked"
            ),
            human_review_status=human_review_status,
            required_gates=required_gates,
            evidence_refs=evidence_refs,
            proposed_tests=proposed_tests,
            rollback_plan_ref=rollback_plan_ref,
            blockers=blockers,
            candidate_type=candidate_type,
            candidate_identity_ref=candidate_identity_ref,
            candidate_version=candidate_version,
            sandbox_eval_ref=sandbox_eval_ref,
            sandbox_eval_status=sandbox_eval_status,
            sandbox_required=True,
            release_gate_required=True,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

    @staticmethod
    def evaluate_promotion_gate(
        checklist: SandboxToReleaseChecklistContract,
        *,
        completed_gates: list[str],
    ) -> PromotionGateDecisionContract:
        """Evaluate release readiness without authorizing promotion."""

        mandatory_gates = [
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ]
        if checklist.candidate_type == "skill_candidate":
            mandatory_gates.append("skill_sandbox_eval")
        required_gates = EvolutionLabService._unique_values(
            [*checklist.required_gates, *mandatory_gates]
        )
        declared_completed = EvolutionLabService._unique_values(completed_gates)
        intrinsic_gates: list[str] = []
        if checklist.human_review_status in {"approved", "sandboxed"}:
            intrinsic_gates.append("human_review")
        if checklist.evidence_refs:
            intrinsic_gates.append("evidence")
        if checklist.proposed_tests:
            intrinsic_gates.append("proposed_tests")
        if checklist.rollback_plan_ref:
            intrinsic_gates.append("rollback_plan")
        if (
            checklist.candidate_type == "skill_candidate"
            and checklist.candidate_identity_ref
            and checklist.candidate_version
            and checklist.sandbox_eval_ref
            and checklist.sandbox_eval_status == "passed_pending_release_gate"
        ):
            intrinsic_gates.append("skill_sandbox_eval")
        externally_verifiable = {
            "standard_engineering_gate",
            "release_gate_before_promotion",
        }
        validated_external_gates = [
            gate
            for gate in declared_completed
            if gate in externally_verifiable and gate in required_gates
        ]
        validated_completed = EvolutionLabService._unique_values(
            [*intrinsic_gates, *validated_external_gates]
        )
        missing_gates = [
            gate for gate in required_gates if gate not in validated_completed
        ]
        blockers = list(checklist.blockers)
        if checklist.checklist_status != "ready_for_release_review":
            blockers.append("checklist_not_ready_for_release_review")
        if not checklist.release_scope.strip():
            blockers.append("release_scope_required")
        if not checklist.sandbox_required:
            blockers.append("sandbox_required")
        if not checklist.release_gate_required:
            blockers.append("release_gate_required")
        if checklist.automatic_promotion_allowed:
            blockers.append("automatic_promotion_not_allowed")
        if checklist.core_mutation_allowed:
            blockers.append("core_mutation_not_allowed")
        if checklist.candidate_type == "skill_candidate" and (
            not checklist.candidate_identity_ref
            or not checklist.candidate_version
            or not checklist.sandbox_eval_ref
        ):
            blockers.append("skill_release_metadata_required")
        blockers.extend(f"gate_not_completed:{gate}" for gate in missing_gates)
        blockers = EvolutionLabService._unique_values(blockers)
        gate_passed = not blockers
        return PromotionGateDecisionContract(
            promotion_gate_id=(
                "promotion-gate://"
                f"{EvolutionLabService._signal_value(checklist.checklist_id)}"
            ),
            checklist_id=checklist.checklist_id,
            evolution_proposal_id=checklist.evolution_proposal_id,
            release_scope=checklist.release_scope,
            gate_status="passed" if gate_passed else "blocked",
            decision=(
                "eligible_for_human_promotion_decision"
                if gate_passed
                else "promotion_blocked"
            ),
            release_conclusion=(
                "release_gate_passed_pending_human_decision"
                if gate_passed
                else "promotion_blocked_by_release_gate"
            ),
            required_gates=required_gates,
            completed_gates=validated_completed,
            missing_gates=missing_gates,
            evidence_refs=EvolutionLabService._unique_values(
                checklist.evidence_refs
            ),
            blockers=blockers,
            human_review_status=checklist.human_review_status,
            promotion_eligible=gate_passed,
            human_decision_required=True,
            promotion_authorized=False,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

    @staticmethod
    def promotion_gate_event_payload(
        decision: PromotionGateDecisionContract,
    ) -> dict[str, object]:
        """Expose the canonical audit payload for a promotion gate decision."""

        return {
            "promotion_gate_id": decision.promotion_gate_id,
            "promotion_gate_checklist_id": decision.checklist_id,
            "evolution_proposal_id": str(decision.evolution_proposal_id),
            "promotion_gate_release_scope": decision.release_scope,
            "promotion_gate_status": decision.gate_status,
            "promotion_gate_decision": decision.decision,
            "promotion_gate_release_conclusion": decision.release_conclusion,
            "promotion_gate_required_gates": list(decision.required_gates),
            "promotion_gate_completed_gates": list(decision.completed_gates),
            "promotion_gate_missing_gates": list(decision.missing_gates),
            "promotion_gate_evidence_refs": list(decision.evidence_refs),
            "promotion_gate_blockers": list(decision.blockers),
            "promotion_gate_human_review_status": decision.human_review_status,
            "promotion_gate_promotion_eligible": decision.promotion_eligible,
            "promotion_gate_human_decision_required": (
                decision.human_decision_required
            ),
            "promotion_gate_promotion_authorized": decision.promotion_authorized,
            "automatic_promotion_allowed": decision.automatic_promotion_allowed,
            "core_mutation_allowed": decision.core_mutation_allowed,
        }

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

    def create_workflow_pattern_review_proposal(
        self,
        *,
        pattern: RecurringPatternEvidenceContract,
        baseline: WorkflowProfileVersionContract,
        proposed_tests: list[str] | None = None,
        rollback_plan_ref: str | None = None,
        strategy_name: str | None = None,
    ) -> EvolutionProposalContract:
        """Persist recurring workflow evidence for explicit human review."""

        blockers = list(pattern.blockers)
        if pattern.pattern_status != "evidence_ready_for_human_review":
            blockers.append("workflow_pattern_not_eligible_for_review")
        if pattern.conflict_flags:
            blockers.append("workflow_pattern_conflict_requires_review")
        if pattern.successful_occurrences < pattern.minimum_occurrences:
            blockers.append("successful_recurrence_threshold_not_met")
        if pattern.non_successful_occurrences:
            blockers.append("non_successful_pattern_cannot_seed_workflow_delta")
        if not pattern.evidence_refs or not pattern.experience_refs:
            blockers.append("workflow_pattern_evidence_required")
        if pattern.workflow_profile != baseline.workflow_profile:
            blockers.append("workflow_pattern_profile_mismatch")
        if pattern.route != baseline.route:
            blockers.append("workflow_pattern_route_mismatch")
        if baseline.lifecycle_status != "baseline_snapshot":
            blockers.append("workflow_baseline_snapshot_required")
        if (
            pattern.skill_candidate_generation_allowed
            or pattern.automatic_skill_creation_allowed
            or pattern.automatic_promotion_allowed
            or pattern.core_mutation_allowed
        ):
            blockers.append("workflow_pattern_authority_claim_not_allowed")
        blockers = self._unique_values(blockers)
        safe_tests = self._unique_values(
            list(proposed_tests or ["test://workflow/pattern-reviewed-delta"])
        )
        safe_rollback = rollback_plan_ref or baseline.rollback_plan_ref
        return self.create_proposal(
            proposal_type="workflow_pattern_evidence",
            target_scope=f"workflow:{baseline.workflow_profile}",
            hypothesis=(
                "reviewed recurring evidence may justify a bounded workflow variant"
            ),
            expected_gain=(
                "improve the affected workflow without mutating the active registry"
            ),
            baseline_refs=self._unique_values(
                [baseline.workflow_version_id, *pattern.evidence_refs]
            ),
            source_signals=self._unique_values(
                [
                    pattern.pattern_id,
                    f"workflow://profile/{self._signal_value(pattern.workflow_profile)}",
                    f"workflow://route/{self._signal_value(pattern.route)}",
                    "workflow://candidate-generation/human-review-required",
                    "workflow://active-registry-write/forbidden",
                    *pattern.experience_refs,
                    *pattern.reflection_refs,
                ]
            ),
            risk_hint="moderate",
            proposed_tests=safe_tests,
            strategy_name=strategy_name,
            candidate_refs=[pattern.pattern_id, baseline.workflow_version_id],
            evaluation_matrix={
                "workflow_pattern_evidence": {
                    "pattern_id": pattern.pattern_id,
                    "pattern_status": pattern.pattern_status,
                    "workflow_profile": pattern.workflow_profile,
                    "route": pattern.route,
                    "domain": pattern.domain,
                    "occurrence_count": pattern.occurrence_count,
                    "successful_occurrences": pattern.successful_occurrences,
                    "confidence_status": pattern.confidence_status,
                    "blockers": blockers,
                }
            },
            strategy_context={
                "workflow_pattern_evidence": {
                    "pattern_id": pattern.pattern_id,
                    "workflow_profile": pattern.workflow_profile,
                    "route": pattern.route,
                    "domain": pattern.domain,
                    "baseline_version_ref": baseline.workflow_version_id,
                    "baseline_definition_hash": baseline.definition_hash,
                    "evidence_refs": list(pattern.evidence_refs),
                },
                "promotion_policy": {
                    "automatic_build": False,
                    "active_registry_write": False,
                    "runtime_activation": False,
                    "automatic_promotion": False,
                    "core_mutation_allowed": False,
                    "human_review_required": True,
                    "sandbox_eval_required": True,
                    "release_gate_required": True,
                },
                "evolution_review": self._review_context(
                    status="needs_review",
                    blockers=blockers,
                    rollback_plan_ref=safe_rollback,
                ),
            },
            optimization_candidate_status="blocked" if blockers else "candidate",
            optimization_safety_status=(
                "blocked_by_safety" if blockers else "human_review_required"
            ),
            optimization_blockers=blockers,
        )

    def build_workflow_candidate_from_reviewed_pattern(
        self,
        *,
        pattern: RecurringPatternEvidenceContract,
        baseline: WorkflowProfileVersionContract,
        review_decision: EvolutionReviewDecisionContract,
        request: WorkflowEvolutionRequestContract,
    ) -> WorkflowEvolutionBuildResultContract:
        """Build one inactive workflow delta only from persisted reviewed evidence."""

        delta_summary = self._workflow_delta_summary(request)
        blockers = self._workflow_candidate_build_blockers(
            pattern=pattern,
            baseline=baseline,
            review_decision=review_decision,
            request=request,
            delta_summary=delta_summary,
        )
        proposal = self.repository.fetch_proposal(
            str(review_decision.evolution_proposal_id)
        )
        if proposal is None:
            blockers.append("persisted_workflow_pattern_proposal_required")
        else:
            blockers.extend(
                self._persisted_workflow_review_blockers(
                    proposal=proposal,
                    pattern=pattern,
                    baseline=baseline,
                    decision=review_decision,
                )
            )

        steps = self._apply_workflow_delta(
            baseline.workflow_steps,
            additions=delta_summary["step_additions"],
            removals=delta_summary["step_removals"],
            field_name="steps",
            blockers=blockers,
        )
        checkpoints = self._apply_workflow_delta(
            baseline.workflow_checkpoints,
            additions=delta_summary["checkpoint_additions"],
            removals=delta_summary["checkpoint_removals"],
            field_name="checkpoints",
            blockers=blockers,
        )
        decision_points = self._apply_workflow_delta(
            baseline.workflow_decision_points,
            additions=delta_summary["decision_point_additions"],
            removals=delta_summary["decision_point_removals"],
            field_name="decision_points",
            blockers=blockers,
        )
        success_criteria = self._apply_workflow_delta(
            baseline.success_criteria,
            additions=delta_summary["success_criteria_additions"],
            removals=delta_summary["success_criteria_removals"],
            field_name="success_criteria",
            blockers=blockers,
        )
        definition_hash = workflow_definition_hash(
            workflow_steps=steps,
            workflow_checkpoints=checkpoints,
            workflow_decision_points=decision_points,
            success_criteria=success_criteria,
        )
        if definition_hash == baseline.definition_hash:
            blockers.append("workflow_delta_must_change_baseline")
        blockers = self._unique_values(blockers)

        evidence_refs = self._unique_values(
            [
                pattern.pattern_id,
                baseline.workflow_version_id,
                review_decision.review_decision_id,
                str(review_decision.evolution_proposal_id),
                *request.evidence_refs,
                *review_decision.evidence_refs,
                *pattern.evidence_refs,
            ]
        )[:50]
        candidate = None
        if not blockers:
            candidate = WorkflowProfileVersionContract(
                workflow_version_id=(
                    f"workflow-version://{baseline.workflow_profile}/"
                    f"{request.candidate_version}"
                ),
                workflow_profile=baseline.workflow_profile,
                version=request.candidate_version,
                route=baseline.route,
                lifecycle_status="candidate_inactive",
                definition_hash=definition_hash,
                workflow_steps=steps,
                workflow_checkpoints=checkpoints,
                workflow_decision_points=decision_points,
                success_criteria=success_criteria,
                evidence_refs=evidence_refs,
                proposed_tests=self._unique_values(request.proposed_tests),
                rollback_plan_ref=request.rollback_plan_ref,
                source_registry_ref=baseline.source_registry_ref,
                source_registry_fingerprint=baseline.source_registry_fingerprint,
                timestamp=request.timestamp,
                baseline_version_ref=baseline.workflow_version_id,
                change_summary=request.change_summary.strip(),
                risk_level=request.risk_level,
                review_status="needs_review",
                runtime_binding_status="inactive_candidate",
                blockers=[],
                human_review_required=True,
                sandbox_required=True,
                active_registry_write_allowed=False,
                runtime_activation_allowed=False,
                automatic_promotion_allowed=False,
                core_mutation_allowed=False,
            )

        result_seed = (
            f"{request.workflow_evolution_request_id}:"
            f"{review_decision.review_decision_id}:{baseline.definition_hash}"
        )
        result_hash = sha256(result_seed.encode("utf-8")).hexdigest()[:16]
        return WorkflowEvolutionBuildResultContract(
            workflow_evolution_result_id=(
                f"workflow-evolution-result://{result_hash}"
            ),
            build_status=(
                "candidate_created_inactive" if candidate is not None else "blocked"
            ),
            source_pattern_ref=pattern.pattern_id,
            source_review_decision_id=review_decision.review_decision_id,
            baseline_version_ref=baseline.workflow_version_id,
            source_authority_status=(
                "reviewed_evidence_requires_candidate_review_sandbox_and_release_gate"
            ),
            delta_summary=delta_summary,
            evidence_refs=evidence_refs,
            blockers=blockers,
            generated_at=request.timestamp,
            candidate=candidate,
        )

    def build_workflow_version_registry(
        self,
        *,
        registry_version: str = "1.0.0",
        generated_at: str | None = None,
        evidence_refs: list[str] | None = None,
        rollback_plan_ref: str = "rollback://domain-registry/runtime-routes/current",
    ) -> WorkflowProfileVersionRegistryContract:
        """Snapshot active workflows without granting the lab registry authority."""

        return build_active_workflow_version_registry(
            registry_version=registry_version,
            generated_at=generated_at or self.now(),
            evidence_refs=[
                "evolution-lab://workflow-version-registry",
                *(evidence_refs or []),
            ],
            rollback_plan_ref=rollback_plan_ref,
        )

    @staticmethod
    def register_workflow_candidate_version(
        registry: WorkflowProfileVersionRegistryContract,
        candidate: WorkflowProfileVersionContract,
    ) -> WorkflowProfileVersionRegistryContract:
        """Register an inactive candidate in a new immutable side snapshot."""

        return register_workflow_candidate_version(registry, candidate)

    @staticmethod
    def _workflow_delta_summary(
        request: WorkflowEvolutionRequestContract,
    ) -> dict[str, list[str]]:
        return {
            field_name: [
                normalized
                for item in getattr(request, field_name)
                if (normalized := str(item).strip())
            ]
            for field_name in (
                "step_additions",
                "step_removals",
                "checkpoint_additions",
                "checkpoint_removals",
                "decision_point_additions",
                "decision_point_removals",
                "success_criteria_additions",
                "success_criteria_removals",
            )
        }

    @classmethod
    def _workflow_candidate_build_blockers(
        cls,
        *,
        pattern: RecurringPatternEvidenceContract,
        baseline: WorkflowProfileVersionContract,
        review_decision: EvolutionReviewDecisionContract,
        request: WorkflowEvolutionRequestContract,
        delta_summary: dict[str, list[str]],
    ) -> list[str]:
        blockers = list(pattern.blockers)
        if pattern.pattern_status != "evidence_ready_for_human_review":
            blockers.append("workflow_pattern_not_eligible")
        if pattern.conflict_flags:
            blockers.append("workflow_pattern_conflict_detected")
        if pattern.successful_occurrences < pattern.minimum_occurrences:
            blockers.append("successful_recurrence_threshold_not_met")
        if pattern.non_successful_occurrences:
            blockers.append("non_successful_pattern_cannot_seed_workflow_delta")
        if pattern.workflow_profile != baseline.workflow_profile:
            blockers.append("workflow_pattern_profile_mismatch")
        if pattern.route != baseline.route:
            blockers.append("workflow_pattern_route_mismatch")
        if baseline.lifecycle_status != "baseline_snapshot":
            blockers.append("workflow_baseline_snapshot_required")
        if request.source_pattern_ref != pattern.pattern_id:
            blockers.append("workflow_request_pattern_ref_mismatch")
        if request.source_review_decision_id != review_decision.review_decision_id:
            blockers.append("workflow_request_review_ref_mismatch")
        if request.baseline_version_ref != baseline.workflow_version_id:
            blockers.append("workflow_request_baseline_ref_mismatch")
        if review_decision.review_status not in REVIEWED_LEARNING_GUIDANCE_STATUSES:
            blockers.append("approved_or_sandboxed_pattern_review_required")
        if (
            review_decision.automatic_promotion_allowed
            or review_decision.core_mutation_allowed
        ):
            blockers.append("review_decision_authority_claim_not_allowed")
        if not request.human_review_required:
            blockers.append("workflow_candidate_human_review_required")
        if (
            request.automatic_build_allowed
            or request.active_registry_write_allowed
            or request.runtime_activation_allowed
            or request.automatic_promotion_allowed
            or request.core_mutation_allowed
        ):
            blockers.append("workflow_request_authority_claim_not_allowed")
        if not cls._numeric_semver(baseline.version):
            blockers.append("baseline_numeric_semver_required")
        if not cls._numeric_semver(request.candidate_version):
            blockers.append("numeric_semver_required")
        elif cls._numeric_semver(baseline.version):
            candidate_version = tuple(
                int(part) for part in request.candidate_version.split(".")
            )
            baseline_version = tuple(int(part) for part in baseline.version.split("."))
            if candidate_version <= baseline_version:
                blockers.append("candidate_version_must_advance_baseline")
        if request.risk_level not in {"low", "moderate"}:
            blockers.append("workflow_candidate_risk_exceeds_bounded_limit")
        if (
            not request.workflow_evolution_request_id
            or len(request.workflow_evolution_request_id) > 500
        ):
            blockers.append("bounded_workflow_evolution_request_id_required")
        if not request.change_summary.strip() or len(request.change_summary) > 500:
            blockers.append("bounded_change_summary_required")
        if not request.rollback_plan_ref or len(request.rollback_plan_ref) > 500:
            blockers.append("bounded_rollback_plan_required")
        if not request.timestamp or len(request.timestamp) > 100:
            blockers.append("bounded_timestamp_required")
        for field_name, values in delta_summary.items():
            raw_values = list(getattr(request, field_name))
            if len(raw_values) > 20 or any(len(str(item)) > 500 for item in raw_values):
                blockers.append(f"{field_name}_must_be_bounded")
            if len(values) != len(raw_values):
                blockers.append(f"{field_name}_cannot_contain_blank_values")
            if len(values) != len(set(values)):
                blockers.append(f"{field_name}_must_be_unique")
        if not any(delta_summary.values()):
            blockers.append("explicit_workflow_delta_required")
        for field_name, values in (
            ("evidence_refs", request.evidence_refs),
            ("proposed_tests", request.proposed_tests),
        ):
            if (
                not values
                or len(values) > 50
                or any(not str(item).strip() or len(str(item)) > 500 for item in values)
            ):
                blockers.append(f"{field_name}_must_be_present_and_bounded")
        return cls._unique_values(blockers)

    @staticmethod
    def _persisted_workflow_review_blockers(
        *,
        proposal: EvolutionProposalContract,
        pattern: RecurringPatternEvidenceContract,
        baseline: WorkflowProfileVersionContract,
        decision: EvolutionReviewDecisionContract,
    ) -> list[str]:
        blockers: list[str] = []
        if proposal.proposal_type != "workflow_pattern_evidence":
            blockers.append("workflow_pattern_proposal_type_required")
        if str(proposal.evolution_proposal_id) != str(decision.evolution_proposal_id):
            blockers.append("workflow_review_proposal_mismatch")
        context = dict(proposal.strategy_context)
        pattern_context = dict(context.get("workflow_pattern_evidence", {}))
        if pattern_context.get("pattern_id") != pattern.pattern_id:
            blockers.append("persisted_pattern_ref_mismatch")
        if pattern_context.get("workflow_profile") != pattern.workflow_profile:
            blockers.append("persisted_pattern_profile_mismatch")
        if pattern_context.get("route") != pattern.route:
            blockers.append("persisted_pattern_route_mismatch")
        if pattern_context.get("baseline_version_ref") != baseline.workflow_version_id:
            blockers.append("persisted_baseline_ref_mismatch")
        if pattern_context.get("baseline_definition_hash") != baseline.definition_hash:
            blockers.append("persisted_baseline_definition_mismatch")
        review = dict(context.get("evolution_review", {}))
        if review.get("last_review_decision_id") != decision.review_decision_id:
            blockers.append("persisted_human_review_decision_required")
        if review.get("review_status") != decision.review_status:
            blockers.append("persisted_human_review_status_mismatch")
        if review.get("last_decision") != decision.decision:
            blockers.append("persisted_human_review_action_mismatch")
        if review.get("last_operator_ref") != decision.operator_ref:
            blockers.append("persisted_human_reviewer_mismatch")
        if review.get("last_reviewed_at") != decision.timestamp:
            blockers.append("persisted_human_review_timestamp_mismatch")
        if review.get("blockers"):
            blockers.append("persisted_human_review_has_blockers")
        return blockers

    @staticmethod
    def _apply_workflow_delta(
        baseline_values: list[str],
        *,
        additions: list[str],
        removals: list[str],
        field_name: str,
        blockers: list[str],
    ) -> list[str]:
        overlap = set(additions) & set(removals)
        if overlap:
            blockers.append(f"{field_name}_delta_add_remove_conflict")
        missing = [value for value in removals if value not in baseline_values]
        if missing:
            blockers.append(f"{field_name}_removal_not_in_baseline")
        already_present = [value for value in additions if value in baseline_values]
        if already_present:
            blockers.append(f"{field_name}_addition_already_in_baseline")
        result = [value for value in baseline_values if value not in removals]
        result.extend(value for value in additions if value not in result)
        if not result:
            blockers.append(f"{field_name}_cannot_be_empty")
        if len(result) > 50 or any(len(value) > 500 for value in result):
            blockers.append(f"{field_name}_result_must_be_bounded")
        return result

    @staticmethod
    def _review_context(
        *,
        status: str,
        blockers: list[str],
        rollback_plan_ref: str | None,
    ) -> dict[str, object]:
        safe_status = status if status in EVOLUTION_REVIEW_STATUSES else "needs_review"
        return {
            "review_status": safe_status,
            "allowed_statuses": list(EVOLUTION_REVIEW_STATUSES),
            "requires_human_review": True,
            "promotion_blocked_without_gate": True,
            "blockers": list(blockers),
            "rollback_plan_ref": rollback_plan_ref,
        }

    @staticmethod
    def _proposal_to_review_item(
        proposal: EvolutionProposalContract,
    ) -> EvolutionReviewQueueItemContract:
        review = dict(proposal.strategy_context.get("evolution_review", {}))
        blockers = list(review.get("blockers", proposal.optimization_blockers))
        status = str(review.get("review_status") or "needs_review")
        if status not in EVOLUTION_REVIEW_STATUSES:
            status = "needs_review"
        rollback_plan_ref = review.get("rollback_plan_ref")
        return EvolutionReviewQueueItemContract(
            review_item_id=f"review://{proposal.evolution_proposal_id}",
            evolution_proposal_id=proposal.evolution_proposal_id,
            proposal_type=proposal.proposal_type,
            review_status=status,
            review_reason=(
                "manual review required before promotion or runtime change"
            ),
            requires_human_review=bool(review.get("requires_human_review", True)),
            requires_sandbox=proposal.requires_sandbox,
            risk_hint=proposal.risk_hint,
            target_scope=proposal.target_scope,
            candidate_refs=list(proposal.candidate_refs),
            blockers=blockers,
            proposed_tests=list(proposal.proposed_tests),
            rollback_plan_ref=(
                str(rollback_plan_ref) if rollback_plan_ref is not None else None
            ),
        )

    @staticmethod
    def _proposal_rollback_plan_ref(
        proposal: EvolutionProposalContract,
    ) -> str | None:
        review = dict(proposal.strategy_context.get("evolution_review", {}))
        rollback_plan_ref = review.get("rollback_plan_ref")
        return str(rollback_plan_ref) if rollback_plan_ref is not None else None

    @staticmethod
    def _proposal_evidence_refs(proposal: EvolutionProposalContract) -> list[str]:
        prefixes = (
            "trace://",
            "evidence://",
            "eval://",
            "baseline://",
            "artifact://",
        )
        values = [
            str(item)
            for item in [*proposal.source_signals, *proposal.baseline_refs]
            if str(item).startswith(prefixes)
        ]
        return EvolutionLabService._unique_values(values)

    @staticmethod
    def _proposal_candidate_metadata(
        proposal: EvolutionProposalContract,
    ) -> tuple[str | None, str | None]:
        skill_context = dict(proposal.evaluation_matrix.get("skill_candidate", {}))
        skill_id = skill_context.get("skill_id")
        version = skill_context.get("version")
        return (
            str(skill_id) if skill_id else None,
            str(version) if version else None,
        )

    @staticmethod
    def _reviewed_guidance_scope(
        proposal: EvolutionProposalContract,
    ) -> tuple[str, str, str]:
        reflection_matrix = dict(proposal.evaluation_matrix.get("post_task_reflection", {}))
        workflow_profile = str(
            reflection_matrix.get("workflow_profile")
            or EvolutionLabService._scope_value(proposal.target_scope, "workflow")
            or "unknown_workflow"
        )
        route = str(
            EvolutionLabService._source_signal_value(
                proposal.source_signals,
                "domain://primary-route/",
            )
            or EvolutionLabService._scope_value(proposal.target_scope, "route")
            or workflow_profile
            or "unknown_route"
        )
        domain = str(
            EvolutionLabService._source_signal_value(
                proposal.source_signals,
                "domain://primary-driver/",
            )
            or EvolutionLabService._source_signal_value(
                proposal.source_signals,
                "domain://registry/",
            )
            or route
            or "unknown_domain"
        )
        return route, workflow_profile, domain

    @staticmethod
    def _reviewed_guidance_summary(proposal: EvolutionProposalContract) -> str:
        reflection = dict(proposal.strategy_context.get("post_task_reflection", {}))
        recommendation = reflection.get("recommendation")
        learning_candidate = reflection.get("learning_candidate")
        return str(recommendation or learning_candidate or proposal.expected_gain)

    @staticmethod
    def _reviewed_guidance_allowed_usage(review_status: str) -> list[str]:
        if review_status == "sandboxed":
            return [
                "sandbox_planning_context",
                "sandbox_synthesis_context",
                "evaluation_context",
            ]
        return [
            "planning_context",
            "synthesis_context",
            "evaluation_context",
        ]

    @staticmethod
    def _scope_value(target_scope: str | None, prefix: str) -> str | None:
        if target_scope is None:
            return None
        marker = f"{prefix}:"
        if target_scope.startswith(marker):
            return target_scope[len(marker) :]
        return None

    @staticmethod
    def _source_signal_value(signals: list[str], prefix: str) -> str | None:
        for signal in signals:
            if signal.startswith(prefix):
                return signal[len(prefix) :]
        return None

    @staticmethod
    def _review_action_blockers(
        *,
        action: str,
        evidence_refs: list[str],
        proposed_tests: list[str],
        rollback_plan_ref: str | None,
    ) -> list[str]:
        blockers: list[str] = []
        if action in RISKY_REVIEW_ACTIONS:
            if not evidence_refs:
                blockers.append("evidence_required_for_human_approval")
            if not proposed_tests:
                blockers.append("tests_required_for_human_approval")
            if not rollback_plan_ref:
                blockers.append("rollback_required_for_human_approval")
        if action == "rollback" and not rollback_plan_ref:
            blockers.append("rollback_plan_required")
        return blockers

    @staticmethod
    def _strategy_context_with_review_decision(
        *,
        proposal: EvolutionProposalContract,
        decision: EvolutionReviewDecisionContract,
        blockers: list[str],
    ) -> dict[str, object]:
        context = dict(proposal.strategy_context)
        review = dict(context.get("evolution_review", {}))
        history = list(review.get("review_history", []))
        history.append(
            {
                "review_decision_id": decision.review_decision_id,
                "review_status": decision.review_status,
                "decision": decision.decision,
                "operator_ref": decision.operator_ref,
                "evidence_refs": list(decision.evidence_refs),
                "proposed_tests": list(decision.proposed_tests),
                "rollback_plan_ref": decision.rollback_plan_ref,
                "risk_acceptance": decision.risk_acceptance,
                "review_notes": list(decision.review_notes),
                "timestamp": decision.timestamp,
                "automatic_promotion_allowed": False,
                "core_mutation_allowed": False,
            }
        )
        review.update(
            {
                "review_status": decision.review_status,
                "last_decision": decision.decision,
                "last_operator_ref": decision.operator_ref,
                "last_review_decision_id": decision.review_decision_id,
                "last_reviewed_at": decision.timestamp,
                "blockers": list(blockers),
                "rollback_plan_ref": decision.rollback_plan_ref,
                "requires_human_review": True,
                "promotion_blocked_without_gate": True,
                "automatic_promotion_allowed": False,
                "core_mutation_allowed": False,
                "review_history": history,
            }
        )
        context["evolution_review"] = review
        return context

    def _review_decision_to_evolution_decision(
        self,
        *,
        proposal: EvolutionProposalContract,
        decision: EvolutionReviewDecisionContract,
        blockers: list[str],
    ) -> EvolutionDecisionContract:
        return EvolutionDecisionContract(
            evolution_decision_id=EvolutionDecisionId(f"evo-decision-{uuid4().hex[:8]}"),
            evolution_proposal_id=proposal.evolution_proposal_id,
            decision=f"human_{decision.decision}",
            comparison_summary=(
                f"human_review_status={decision.review_status}; "
                f"action={decision.decision}; blockers={','.join(blockers) or 'none'}"
            ),
            timestamp=decision.timestamp,
            promoted_to=None,
            rollback_plan_ref=decision.rollback_plan_ref,
            governance_refs=[
                f"human_review://{decision.operator_ref}",
                f"review_decision://{decision.review_decision_id}",
            ],
            notes=[
                *decision.review_notes,
                "automatic_promotion_allowed=False",
                "core_mutation_allowed=False",
            ],
            optimization_scope=proposal.optimization_scope,
            optimization_target_kind=proposal.optimization_target_kind,
            optimization_safety_status=proposal.optimization_safety_status,
            optimization_blockers=list(proposal.optimization_blockers) + blockers,
            baseline_label="current_baseline",
            candidate_label=str(proposal.evolution_proposal_id),
            selected_candidate_label=(
                str(proposal.evolution_proposal_id)
                if decision.review_status in {"approved", "sandboxed"}
                else None
            ),
        )

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
    def _signal_value(value: str) -> str:
        return (
            value.strip().lower().replace(" ", "-").replace("/", "-").replace(":", "-")
        )

    @staticmethod
    def _unique_values(values: list[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            if value and value not in unique:
                unique.append(value)
        return unique

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
        optimization_state = EvolutionLabService._optimization_state(
            evaluation,
            refinement_vectors=EvolutionLabService._refinement_vectors_from_flow_evaluation(
                evaluation
            ),
        )
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
                "operational_ecosystem_state": (
                    evaluation.operational_ecosystem_state_status
                    or "not_applicable"
                ),
                "active_work_items": len(evaluation.active_work_items),
                "active_artifact_refs": len(evaluation.active_artifact_refs),
                "open_checkpoint_refs": len(evaluation.open_checkpoint_refs),
                "surface_presence": len(evaluation.surface_presence),
                "surface_continuity": (
                    evaluation.surface_continuity_status or "not_applicable"
                ),
                "linked_surface_count": evaluation.linked_surface_count,
                "surface_identity_conflicts": list(
                    evaluation.surface_identity_conflict_flags
                ),
                "multi_surface_readiness": (
                    evaluation.multi_surface_readiness or "not_applicable"
                ),
                "experiment_lane": expanded_eval_state["experiment_lane_status"],
                "wave2_candidate_class": expanded_eval_state["wave2_candidate_class"],
                "experiment_entry": expanded_eval_state["experiment_entry_status"],
                "experiment_exit": expanded_eval_state["experiment_exit_status"],
                "promotion_readiness": expanded_eval_state["promotion_readiness"],
                "optimization_target_kind": optimization_state["optimization_target_kind"],
                "optimization_candidate": optimization_state[
                    "optimization_candidate_status"
                ],
                "optimization_safety": optimization_state["optimization_safety_status"],
                "optimization_readiness": optimization_state["optimization_readiness"],
                "optimization_release": optimization_state[
                    "optimization_release_status"
                ],
                "optimization_blockers": list(
                    optimization_state["optimization_blockers"]
                ),
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
    def _optimization_state(
        evaluation: FlowEvaluationInput,
        *,
        refinement_vectors: list[dict[str, object]],
    ) -> dict[str, object]:
        expanded_eval_state = EvolutionLabService._expanded_eval_state(evaluation)
        return derive_optimization_state(
            refinement_vectors=refinement_vectors,
            trace_status=(
                "attention_required"
                if evaluation.anomaly_flags
                or evaluation.missing_required_events
                or evaluation.missing_continuity_signals
                or evaluation.continuity_anomaly_flags
                else "healthy"
            ),
            request_identity_status=evaluation.request_identity_status,
            mission_policy_status=EvolutionLabService._mission_policy_readiness(
                evaluation
            ),
            capability_decision_status=evaluation.capability_decision_status,
            handoff_adapter_status=evaluation.handoff_adapter_status,
            expanded_eval_status=expanded_eval_state["expanded_eval_status"],
            experiment_lane_status=expanded_eval_state["experiment_lane_status"],
            promotion_readiness=expanded_eval_state["promotion_readiness"],
            adaptive_intervention_effectiveness=(
                evaluation.adaptive_intervention_effectiveness
            ),
            memory_maintenance_effectiveness=(
                evaluation.memory_maintenance_effectiveness
            ),
            mind_domain_specialist_effectiveness=(
                evaluation.mind_domain_specialist_effectiveness
            ),
            workflow_profile_status=evaluation.workflow_profile_status,
            workflow_output_status=evaluation.workflow_output_status,
        )

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
