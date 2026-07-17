# ruff: noqa: E501
"""Structured local observability service."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from os import getenv
from pathlib import Path

from observability_service.agentic import (
    AgenticObservabilityAdapter,
    JsonlAgenticMirrorAdapter,
    LangSmithObservabilityAdapter,
)
from observability_service.repository import ObservabilityRepository
from shared.contracts import (
    WORKFLOW_VARIANT_EVAL_METRICS,
    CapabilityReadinessContract,
    DomainEvalCaseResultContract,
    DomainEvalRunContract,
    EvolutionProposalContract,
    ExperienceRecordContract,
    LearningOutcomeObservationContract,
    LearningVersionTargetContract,
    LongitudinalLearningReportContract,
    LongitudinalVersionMetricsContract,
    PostTaskReflectionContract,
    RecurringPatternReportContract,
    RegressionReadinessReportContract,
    RoutingAdaptationCandidateContract,
    RoutingAdaptationObservationContract,
    RoutingAdaptationReportContract,
    SkillCandidateContract,
    SkillEvolutionOperatorItemContract,
    SkillEvolutionOperatorViewContract,
    WorkflowVariantEvalCaseResultContract,
    WorkflowVariantEvalRunContract,
)
from shared.domain_registry import (
    is_promoted_specialist_route,
    route_metadata_payload,
    workflow_runtime_guidance,
)
from shared.eval_expansion import derive_expanded_eval_state
from shared.events import InternalEventEnvelope
from shared.recurring_patterns import build_recurring_pattern_report


@dataclass(frozen=True)
class FlowMetrics:
    """Minimal correlated metrics for a traced flow."""

    total_events: int
    blocked_events: int
    completed_operations: int
    memory_writes: int
    error_events: int
    duration_seconds: float


DEFAULT_REQUIRED_FLOW_EVENTS = (
    "input_received",
    "memory_recovered",
    "intent_classified",
    "context_composed",
    "plan_built",
    "continuity_decided",
    "governance_checked",
    "response_synthesized",
    "memory_recorded",
)


@dataclass(frozen=True)
class FlowAudit:
    """Operational audit view for a correlated request flow."""

    request_id: str | None
    session_id: str | None
    mission_id: str | None
    total_events: int
    workflow_domain_route: str | None
    workflow_profile: str | None
    workflow_governance_mode: str | None
    workflow_trace_status: str
    workflow_checkpoint_status: str
    workflow_resume_status: str
    workflow_resume_point: str | None
    workflow_pending_checkpoint_count: int
    workflow_profile_status: str
    contract_validation_status: str
    contract_validation_errors: list[str]
    contract_validation_retry_applied: bool
    output_validation_status: str
    output_validation_errors: list[str]
    output_validation_retry_applied: bool
    workflow_output_status: str
    workflow_output_errors: list[str]
    memory_causality_status: str
    primary_mind: str | None
    primary_route: str | None
    dominant_tension: str | None
    arbitration_source: str | None
    primary_domain_driver: str | None
    metacognitive_guidance_status: str
    metacognitive_guidance_summary: str | None
    metacognitive_effects: list[str]
    metacognitive_containment_recommendation: str | None
    mind_disagreement_status: str
    mind_validation_checkpoint_status: str
    capability_decision_status: str
    capability_decision_objective: str | None
    capability_decision_reason: str | None
    capability_decision_selected_mode: str | None
    capability_authorization_status: str
    capability_decision_tool_class: str | None
    capability_decision_handoff_mode: str | None
    capability_decision_eligible_capabilities: list[str]
    capability_decision_selected_capabilities: list[str]
    effective_autonomy_level: str | None
    autonomy_ladder_status: str | None
    max_autonomy_capability_mode: str | None
    autonomy_human_confirmation_required: bool
    autonomy_confirmation_mode: str | None
    autonomy_blocked_runtime_actions: list[str]
    capability_effectiveness: str
    handoff_adapter_status: str
    request_identity_status: str
    mission_policy_status: str
    request_identity_mismatch_flags: list[str]
    expanded_eval_status: str
    surface_axis_status: str
    ecosystem_state_status: str
    operational_ecosystem_state_status: str
    active_work_items: list[str]
    active_artifact_refs: list[str]
    open_checkpoint_refs: list[str]
    surface_presence: list[str]
    experiment_lane_status: str
    wave2_candidate_class: str
    experiment_entry_status: str
    experiment_exit_status: str
    promotion_readiness: str
    mind_domain_specialist_status: str
    mind_domain_specialist_chain_status: str
    mind_domain_specialist_chain: str | None
    mind_domain_specialist_effectiveness: str
    mind_domain_specialist_mismatch_flags: list[str]
    cognitive_recomposition_applied: bool
    cognitive_recomposition_reason: str | None
    cognitive_recomposition_trigger: str | None
    adaptive_intervention_status: str
    adaptive_intervention_reason: str | None
    adaptive_intervention_trigger: str | None
    adaptive_intervention_selected_action: str | None
    adaptive_intervention_expected_effect: str | None
    adaptive_intervention_effects: list[str]
    adaptive_intervention_effectiveness: str
    adaptive_intervention_policy_status: str
    cognitive_strategy_shift_status: str
    cognitive_strategy_shift_applied: bool
    cognitive_strategy_shift_summary: str | None
    cognitive_strategy_shift_trigger: str | None
    cognitive_strategy_shift_effects: list[str]
    semantic_memory_source: str | None
    procedural_memory_source: str | None
    semantic_memory_focus: list[str]
    semantic_memory_anchor_refs: list[str]
    semantic_memory_evidence_refs: list[str]
    semantic_memory_use_reason: str | None
    semantic_memory_non_use_reason: str | None
    memory_influence_used_refs: list[str]
    memory_influence_ignored_refs: list[str]
    memory_influence_reasons: list[str]
    memory_influence_evidence_refs: list[str]
    procedural_memory_hint: str | None
    semantic_memory_effects: list[str]
    procedural_memory_effects: list[str]
    semantic_memory_lifecycle: str | None
    procedural_memory_lifecycle: str | None
    memory_lifecycle_status: str
    memory_review_status: str
    memory_maintenance_status: str
    memory_maintenance_reason: str | None
    memory_maintenance_fallback_mode: str | None
    context_compaction_status: str | None
    cross_session_recall_status: str | None
    memory_consolidation_status: str
    memory_fixation_status: str
    memory_archive_status: str
    procedural_artifact_status: str
    procedural_artifact_refs: list[str]
    procedural_artifact_version: int | None
    memory_corpus_status: str
    memory_retention_pressure: str | None
    memory_maintenance_effectiveness: str
    semantic_memory_specialists: list[str]
    procedural_memory_specialists: list[str]
    event_names: list[str]
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None
    continuity_source: str | None
    continuity_target_mission_id: str | None
    continuity_target_goal: str | None
    continuity_runtime_mode: str | None
    specialist_subflow_status: str
    specialist_subflow_runtime_mode: str | None
    mission_runtime_state_status: str
    registry_domains: list[str]
    domain_specialists: list[str]
    shadow_specialists: list[str]
    domain_alignment_status: str
    mind_alignment_status: str
    identity_alignment_status: str
    memory_alignment_status: str
    user_scope_status: str
    organization_scope_status: str
    specialist_recurrence_status: str
    specialist_sovereignty_status: str
    missing_continuity_signals: list[str]
    continuity_anomaly_flags: list[str]
    continuity_trace_status: str
    governance_decision: str | None
    operation_status: str | None
    duration_seconds: float
    source_services: list[str]
    surface_continuity_status: str = "not_applicable"
    linked_surface_count: int = 0
    surface_identity_conflict_flags: list[str] = field(default_factory=list)
    multi_surface_readiness: str = "not_applicable"
    objective_continuity_status: str = "not_applicable"
    active_work_item_count: int = 0
    open_checkpoint_count: int = 0
    artifact_continuity_status: str = "not_applicable"
    next_action_status: str = "not_applicable"
    objective_consulted: bool = False
    objective_transition_counts: dict[str, int] = field(default_factory=dict)
    objective_utility_signals: list[str] = field(default_factory=list)
    objective_missing_next_action: bool = False
    objective_missing_artifact: bool = False
    operator_usefulness_status: str = "insufficient_signal"
    operator_usefulness_score: int = 0
    operator_usefulness_signals: list[str] = field(default_factory=list)
    technology_absorption_readiness: str = "not_applicable"
    technology_absorption_decision: str = "not_applicable"
    technology_absorption_lane_status: str = "not_applicable"
    technology_absorption_promotion_readiness: str = "not_applicable"
    technology_absorption_blockers: list[str] = field(default_factory=list)
    technology_absorption_candidate_refs: list[str] = field(default_factory=list)
    technology_absorption_signals: list[str] = field(default_factory=list)
    experience_reflection_status: str = "not_applicable"
    experience_reflection_change_type: str = "not_applicable"
    experience_reflection_blockers: list[str] = field(default_factory=list)
    experience_reflection_refs: list[str] = field(default_factory=list)
    experience_reflection_signals: list[str] = field(default_factory=list)
    operator_feedback_status: str = "not_applicable"
    operator_feedback_id: str | None = None
    operator_feedback_experience_id: str | None = None
    operator_feedback_assessment: str = "not_applicable"
    operator_feedback_rating: int | None = None
    operator_feedback_evidence_refs: list[str] = field(default_factory=list)
    operator_feedback_evolution_review_status: str = "not_applicable"
    operator_feedback_human_review_required: bool = True
    operator_feedback_automatic_promotion_allowed: bool = False
    operator_feedback_core_mutation_allowed: bool = False
    reflection_influence_status: str = "not_applicable"
    reflection_influence_refs: list[str] = field(default_factory=list)
    reflection_influence_summary: str | None = None
    reflection_assisted_eval_status: str = "baseline_no_reflection"
    reviewed_learning_influence_status: str = "not_applicable"
    reviewed_learning_influence_refs: list[str] = field(default_factory=list)
    reviewed_learning_influence_summary: str | None = None
    reviewed_learning_influence_reason: str | None = None
    reviewed_learning_assisted_eval_status: str = "baseline_no_reviewed_learning"
    reviewed_learning_release_conclusion: str = "no_promotion_without_release_gate"
    evolution_review_decision_status: str = "not_applicable"
    evolution_review_decision: str = "not_applicable"
    evolution_review_proposal_id: str | None = None
    evolution_review_operator_ref: str | None = None
    evolution_review_evidence_refs: list[str] = field(default_factory=list)
    evolution_review_rollback_plan_ref: str | None = None
    evolution_review_limits: list[str] = field(default_factory=list)
    promotion_gate_status: str = "not_applicable"
    promotion_gate_decision: str = "not_applicable"
    promotion_gate_id: str | None = None
    promotion_gate_checklist_id: str | None = None
    promotion_gate_release_scope: str | None = None
    promotion_gate_release_conclusion: str = "no_promotion_gate_evidence"
    promotion_gate_required_gates: list[str] = field(default_factory=list)
    promotion_gate_completed_gates: list[str] = field(default_factory=list)
    promotion_gate_missing_gates: list[str] = field(default_factory=list)
    promotion_gate_evidence_refs: list[str] = field(default_factory=list)
    promotion_gate_blockers: list[str] = field(default_factory=list)
    promotion_gate_human_review_status: str = "not_applicable"
    promotion_gate_promotion_eligible: bool = False
    promotion_gate_human_decision_required: bool = True
    promotion_gate_promotion_authorized: bool = False
    mission_progress_report_status: str = "not_applicable"
    mission_progress_report_id: str | None = None
    mission_progress_summary: str | None = None
    mission_progress_next_action_ref: str | None = None
    mission_progress_pending_decisions: list[str] = field(default_factory=list)
    mission_progress_evidence_refs: list[str] = field(default_factory=list)
    mission_progress_memory_influence_refs: list[str] = field(default_factory=list)
    mission_progress_learning_refs: list[str] = field(default_factory=list)
    mission_progress_risk_refs: list[str] = field(default_factory=list)

    @property
    def trace_complete(self) -> bool:
        return (
            not self.missing_required_events
            and not self.anomaly_flags
            and not self.missing_continuity_signals
            and not self.continuity_anomaly_flags
            and self.workflow_trace_status in {"healthy", "not_applicable"}
            and self.workflow_checkpoint_status in {"healthy", "not_applicable"}
            and self.workflow_profile_status in {"healthy", "not_applicable"}
            and self.contract_validation_status in {"coherent", "repaired", "not_applicable"}
            and self.output_validation_status in {"coherent", "repaired", "not_applicable"}
            and self.workflow_output_status in {"coherent", "not_applicable"}
            and self.capability_decision_status in {"healthy", "not_applicable"}
            and self.capability_effectiveness in {"effective", "not_applicable"}
            and self.handoff_adapter_status in {"healthy", "not_applicable", "contained"}
            and self.request_identity_status in {"healthy", "not_applicable"}
            and self.mission_policy_status
            in {"policy_aligned", "mandatory_override", "not_applicable"}
            and not self.request_identity_mismatch_flags
            and self.expanded_eval_status
            in {"candidate_ready", "baseline_expanding", "not_in_phase"}
            and self.surface_axis_status
            in {"candidate_ready", "coverage_partial", "not_in_phase"}
            and self.ecosystem_state_status
            in {"candidate_ready", "coverage_partial", "not_in_phase"}
            and self.experiment_lane_status
            in {"controlled_candidate", "baseline_only", "out_of_lane"}
            and self.promotion_readiness
            in {"manual_review_only", "not_applicable", "blocked"}
            and self.mind_domain_specialist_effectiveness
            in {"effective", "not_applicable"}
            and self.adaptive_intervention_status in {"healthy", "not_applicable"}
            and self.adaptive_intervention_effectiveness
            in {"effective", "not_applicable"}
            and self.adaptive_intervention_policy_status
            in {"policy_aligned", "mandatory_override", "not_applicable"}
            and self.memory_maintenance_effectiveness in {"effective", "not_applicable"}
            and self.cognitive_strategy_shift_status in {"healthy", "not_applicable"}
            and self.specialist_subflow_status
            in {"healthy", "not_applicable", "contained"}
            and self.mission_runtime_state_status in {"healthy", "not_applicable"}
            and not self.surface_identity_conflict_flags
            and self.multi_surface_readiness != "attention_required"
            and self.objective_continuity_status
            in {
                "active",
                "blocked",
                "completed",
                "paused",
                "requires_operator_decision",
                "not_applicable",
            }
            and self.artifact_continuity_status != "attention_required"
            and self.next_action_status != "attention_required"
            and self.technology_absorption_decision
            not in {"block_absorption", "attention_required"}
            and self.experience_reflection_status not in {"blocked", "attention_required"}
            and self.operator_feedback_status
            in {"not_applicable", "recorded_bounded"}
            and self.evolution_review_decision_status
            in {
                "not_applicable",
                "approved",
                "rejected",
                "sandboxed",
                "needs_review",
                "rolled_back",
            }
            and self.promotion_gate_status in {"not_applicable", "passed", "blocked"}
        )


@dataclass(frozen=True)
class IncidentEvidence:
    """Compact operational evidence for anomalous request handling."""

    request_id: str | None
    session_id: str | None
    mission_id: str | None
    governance_decision: str | None
    operation_status: str | None
    flow_summary: str
    anomaly_flags: list[str]
    missing_required_events: list[str]
    recommended_operator_action: str
    source_services: list[str]


@dataclass(frozen=True)
class ObservabilityQuery:
    """Query filters for recent event inspection."""

    limit: int = 20
    request_id: str | None = None
    session_id: str | None = None
    mission_id: str | None = None
    correlation_id: str | None = None
    operation_id: str | None = None


class ObservabilityService:
    """Collect and query structured telemetry from orchestrated flows."""

    name = "observability-service"

    def __init__(
        self,
        database_path: str | None = None,
        agentic_adapter: AgenticObservabilityAdapter | None = None,
    ) -> None:
        runtime_path = database_path or getenv("JARVIS_OBSERVABILITY_DB")
        resolved = (
            Path(runtime_path)
            if runtime_path
            else Path.cwd() / ".jarvis_runtime" / "observability.db"
        )
        self.repository = ObservabilityRepository(resolved)
        self.agentic_adapter = agentic_adapter or self._build_agentic_adapter()

    def ingest_events(self, events: list[InternalEventEnvelope]) -> None:
        """Persist the event trail for later inspection."""

        for event in events:
            self.repository.record_event(event)
        if self.agentic_adapter is not None:
            self.agentic_adapter.emit(events)

    def list_recent_events(
        self, query: ObservabilityQuery | None = None
    ) -> list[InternalEventEnvelope]:
        """Return recent events filtered by the most relevant correlation fields."""

        filters = query or ObservabilityQuery()
        return self.repository.list_events(
            limit=filters.limit,
            request_id=filters.request_id,
            session_id=filters.session_id,
            mission_id=filters.mission_id,
            correlation_id=filters.correlation_id,
            operation_id=filters.operation_id,
        )

    def export_trace_view(self, query: ObservabilityQuery | None = None) -> list[dict[str, object]]:
        """Return a trace-friendly projection of the stored internal events."""

        events = self.list_recent_events(query)
        return [
            {
                "span_id": event.event_id,
                "name": event.event_name,
                "timestamp": event.timestamp,
                "service": event.source_service,
                "request_id": event.request_id,
                "session_id": event.session_id,
                "mission_id": event.mission_id,
                "correlation_id": event.correlation_id,
                "tags": list(event.tags),
                "payload_keys": sorted(event.payload.keys()),
            }
            for event in events
        ]

    def summarize_flow(self, query: ObservabilityQuery) -> FlowMetrics:
        """Summarize a correlated request/session/mission flow for governance and evolution."""

        events = self.list_recent_events(query)
        if not events:
            return FlowMetrics(
                total_events=0,
                blocked_events=0,
                completed_operations=0,
                memory_writes=0,
                error_events=0,
                duration_seconds=0.0,
            )
        timestamps = [event.timestamp for event in events]
        duration = 0.0
        if len(timestamps) > 1:
            from datetime import datetime

            started = datetime.fromisoformat(timestamps[0].replace("Z", "+00:00"))
            ended = datetime.fromisoformat(timestamps[-1].replace("Z", "+00:00"))
            duration = round((ended - started).total_seconds(), 4)
        return FlowMetrics(
            total_events=len(events),
            blocked_events=sum(1 for event in events if event.event_name == "governance_blocked"),
            completed_operations=sum(
                1 for event in events if event.event_name == "operation_completed"
            ),
            memory_writes=sum(1 for event in events if event.event_name == "memory_recorded"),
            error_events=sum(1 for event in events if event.event_name == "error_raised"),
            duration_seconds=duration,
        )

    @staticmethod
    def build_domain_eval_run(
        *,
        run_id: str,
        eval_pack_id: str,
        pack_version: str,
        route_name: str,
        case_results: list[DomainEvalCaseResultContract],
        minimum_pass_rate: float,
        evidence_refs: list[str],
        generated_at: str,
        blockers: list[str] | None = None,
    ) -> DomainEvalRunContract:
        """Aggregate domain eval evidence without turning it into promotion authority."""

        resolved_blockers = list(blockers or [])
        if not 0.0 < minimum_pass_rate <= 1.0:
            resolved_blockers.append("invalid_minimum_pass_rate")
        total_cases = len(case_results)
        passed_cases = sum(1 for result in case_results if result.passed)
        failed_cases = total_cases - passed_cases
        pass_rate = round(passed_cases / total_cases, 4) if total_cases else 0.0
        if total_cases == 0:
            resolved_blockers.append("no_domain_eval_results")
        for result in case_results:
            resolved_blockers.extend(
                f"case:{result.case_id}:{failure}" for failure in result.failures
            )
        resolved_blockers = sorted(set(resolved_blockers))
        passed = not resolved_blockers and pass_rate >= minimum_pass_rate
        return DomainEvalRunContract(
            run_id=run_id,
            eval_pack_id=eval_pack_id,
            pack_version=pack_version,
            route_name=route_name,
            status="passed" if passed else "failed",
            readiness_status=(
                "candidate_ready_for_human_review" if passed else "attention_required"
            ),
            promotion_readiness="manual_review_only" if passed else "blocked",
            pass_rate=pass_rate,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            case_results=list(case_results),
            evidence_refs=list(evidence_refs),
            blockers=resolved_blockers,
            generated_at=generated_at,
        )

    @staticmethod
    def build_workflow_variant_eval_run(
        *,
        run_id: str,
        workflow_profile: str,
        route: str,
        baseline_version_ref: str,
        candidate_version_ref: str,
        case_results: list[WorkflowVariantEvalCaseResultContract],
        minimum_pass_rate: float,
        evidence_refs: list[str],
        generated_at: str,
        blockers: list[str] | None = None,
    ) -> WorkflowVariantEvalRunContract:
        """Aggregate equivalent workflow comparisons without release authority."""

        resolved_blockers = list(blockers or [])
        if not 0.0 < minimum_pass_rate <= 1.0:
            resolved_blockers.append("invalid_minimum_pass_rate")
        if not case_results:
            resolved_blockers.append("no_workflow_variant_eval_results")
        if len(case_results) > 32:
            resolved_blockers.append("too_many_workflow_variant_eval_results")
        case_ids = [result.case_id for result in case_results]
        if len(case_ids) != len(set(case_ids)):
            resolved_blockers.append("duplicate_workflow_variant_case_id")
        regression_flags: list[str] = []
        for result in case_results:
            if (
                result.workflow_profile != workflow_profile
                or result.route != route
                or result.baseline_version_ref != baseline_version_ref
                or result.candidate_version_ref != candidate_version_ref
            ):
                resolved_blockers.append(f"case:{result.case_id}:scope_mismatch")
            if (
                set(result.baseline_metrics) != set(WORKFLOW_VARIANT_EVAL_METRICS)
                or set(result.candidate_metrics) != set(WORKFLOW_VARIANT_EVAL_METRICS)
                or set(result.metric_deltas) != set(WORKFLOW_VARIANT_EVAL_METRICS)
            ):
                resolved_blockers.append(
                    f"case:{result.case_id}:metric_dimensions_mismatch"
                )
            resolved_blockers.extend(
                f"case:{result.case_id}:{failure}" for failure in result.failures
            )
            regression_flags.extend(
                f"case:{result.case_id}:{flag}" for flag in result.regression_flags
            )

        total_cases = len(case_results)
        passed_cases = sum(result.passed for result in case_results)
        failed_cases = total_cases - passed_cases
        pass_rate = round(passed_cases / total_cases, 4) if total_cases else 0.0

        def aggregate(attribute: str) -> dict[str, float]:
            if not total_cases:
                return {metric: 0.0 for metric in WORKFLOW_VARIANT_EVAL_METRICS}
            return {
                metric: round(
                    sum(
                        getattr(result, attribute).get(metric, 0.0)
                        for result in case_results
                    )
                    / total_cases,
                    4,
                )
                for metric in WORKFLOW_VARIANT_EVAL_METRICS
            }

        baseline_metrics = aggregate("baseline_metrics")
        candidate_metrics = aggregate("candidate_metrics")
        metric_deltas = {
            metric: round(candidate_metrics[metric] - baseline_metrics[metric], 4)
            for metric in WORKFLOW_VARIANT_EVAL_METRICS
        }
        resolved_blockers.extend(regression_flags)
        resolved_blockers = sorted(set(resolved_blockers))
        passed = (
            not resolved_blockers
            and pass_rate >= minimum_pass_rate
            and all(result.improvement_signals for result in case_results)
        )
        comparison_conclusion = (
            "candidate_improved_without_regression"
            if passed
            else (
                "candidate_regression_detected"
                if regression_flags
                else "insufficient_or_invalid_evidence"
            )
        )
        return WorkflowVariantEvalRunContract(
            run_id=run_id,
            workflow_profile=workflow_profile,
            route=route,
            baseline_version_ref=baseline_version_ref,
            candidate_version_ref=candidate_version_ref,
            status="passed" if passed else "failed",
            readiness_status=(
                "candidate_ready_for_human_gate_review"
                if passed
                else "attention_required"
            ),
            promotion_readiness="manual_gate_only" if passed else "blocked",
            comparison_conclusion=comparison_conclusion,
            pass_rate=pass_rate,
            total_cases=total_cases,
            passed_cases=passed_cases,
            failed_cases=failed_cases,
            aggregate_baseline_metrics=baseline_metrics,
            aggregate_candidate_metrics=candidate_metrics,
            aggregate_metric_deltas=metric_deltas,
            case_results=list(case_results),
            regression_flags=sorted(set(regression_flags)),
            evidence_refs=list(dict.fromkeys(evidence_refs))[:100],
            blockers=resolved_blockers,
            generated_at=generated_at,
        )

    @staticmethod
    def build_recurring_pattern_report(
        *,
        report_id: str,
        experiences: list[ExperienceRecordContract],
        reflections: list[PostTaskReflectionContract] | None,
        minimum_occurrences: int,
        generated_at: str,
        workflow_profile: str | None = None,
        route: str | None = None,
        domain: str | None = None,
        max_records: int = 100,
        max_patterns: int = 20,
    ) -> RecurringPatternReportContract:
        """Expose bounded recurrence aggregation as an observability projection."""

        return build_recurring_pattern_report(
            report_id=report_id,
            experiences=experiences,
            reflections=reflections,
            minimum_occurrences=minimum_occurrences,
            generated_at=generated_at,
            workflow_profile=workflow_profile,
            route=route,
            domain=domain,
            max_records=max_records,
            max_patterns=max_patterns,
        )

    @staticmethod
    def build_routing_adaptation_report(
        *,
        report_id: str,
        observations: list[RoutingAdaptationObservationContract],
        minimum_occurrences: int,
        generated_at: str,
        max_observations: int = 100,
        max_candidates: int = 20,
        blockers: list[str] | None = None,
    ) -> RoutingAdaptationReportContract:
        """Aggregate route mismatch evidence without changing runtime routing."""

        resolved_blockers = list(blockers or [])
        if minimum_occurrences < 2 or minimum_occurrences > 20:
            resolved_blockers.append("invalid_routing_adaptation_minimum_occurrences")
        if max_observations < 1 or max_observations > 100:
            resolved_blockers.append("invalid_routing_adaptation_observation_limit")
        if max_candidates < 1 or max_candidates > 20:
            resolved_blockers.append("invalid_routing_adaptation_candidate_limit")
        if not observations:
            resolved_blockers.append("no_routing_adaptation_observations")
        if len(observations) > max_observations:
            resolved_blockers.append("routing_adaptation_observation_limit_exceeded")

        bounded_observations = list(observations[:max_observations])
        observation_ids = [item.observation_id for item in bounded_observations]
        if len(observation_ids) != len(set(observation_ids)):
            resolved_blockers.append("duplicate_routing_adaptation_observation_id")
        source_case_ids = [item.source_case_id for item in bounded_observations]
        if len(source_case_ids) != len(set(source_case_ids)):
            resolved_blockers.append("duplicate_routing_adaptation_source_case_id")

        mismatches: dict[
            tuple[str, str, str], list[RoutingAdaptationObservationContract]
        ] = {}
        observed_routes_by_scope: dict[tuple[str, str], set[str]] = {}
        all_evidence: list[str] = []
        for observation in bounded_observations:
            all_evidence.extend(observation.evidence_refs)
            expected_metadata = route_metadata_payload(observation.expected_route)
            observed_metadata = route_metadata_payload(observation.observed_route or "")
            expected_route_valid = is_promoted_specialist_route(
                observation.expected_route
            )
            if not expected_route_valid:
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:expected_promoted_route_required"
                )
            if observed_metadata["maturity"] is None:
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:observed_route_not_registered"
                )
            if (
                expected_metadata["workflow_profile"]
                != observation.expected_workflow_profile
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:expected_workflow_registry_mismatch"
                )
            if (
                expected_metadata["linked_specialist_type"]
                != observation.expected_specialist_type
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:expected_specialist_registry_mismatch"
                )
            if observation.route_match != (
                observation.expected_route == observation.observed_route
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:route_comparison_inconsistent"
                )
            if observation.workflow_match != (
                observation.expected_workflow_profile
                == observation.observed_workflow_profile
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:workflow_comparison_inconsistent"
                )
            if observation.specialist_match != (
                observation.expected_specialist_type
                in observation.observed_specialist_types
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:specialist_comparison_inconsistent"
                )
            if not observation.outcome_status:
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:outcome_status_required"
                )
            if not observation.memory_causality_status:
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:memory_causality_status_required"
                )
            if not observation.evidence_refs:
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:evidence_required"
                )
            if (
                not observation.read_only
                or not observation.human_review_required
                or observation.routing_write_allowed
                or observation.runtime_activation_allowed
                or observation.automatic_promotion_allowed
                or observation.core_mutation_allowed
            ):
                resolved_blockers.append(
                    f"observation:{observation.observation_id}:routing_authority_claim_not_allowed"
                )
            if observation.route_match or observation.observed_route is None:
                continue
            scope = (
                observation.expected_route,
                observation.expected_workflow_profile,
            )
            observed_routes_by_scope.setdefault(scope, set()).add(
                observation.observed_route
            )
            key = (*scope, observation.observed_route)
            mismatches.setdefault(key, []).append(observation)

        conflict_flags: list[str] = []
        for scope, observed_routes in sorted(observed_routes_by_scope.items()):
            if len(observed_routes) > 1:
                conflict_flags.append(
                    f"scope:{scope[0]}:{scope[1]}:conflicting_observed_routes"
                )

        candidates: list[RoutingAdaptationCandidateContract] = []
        successful_outcomes = {"completed", "success", "succeeded"}
        conflicted_scopes = {
            flag.removeprefix("scope:").removesuffix(
                ":conflicting_observed_routes"
            )
            for flag in conflict_flags
        }
        if not resolved_blockers:
            for key, group in sorted(mismatches.items()):
                expected_route, workflow_profile, observed_route = key
                scope_ref = f"{expected_route}:{workflow_profile}"
                if scope_ref in conflicted_scopes or len(group) < minimum_occurrences:
                    continue
                outcomes = sorted({item.outcome_status for item in group})
                memory_statuses = sorted(
                    {item.memory_causality_status for item in group}
                )
                specialist_sets = {
                    tuple(sorted(set(item.observed_specialist_types)))
                    for item in group
                }
                group_conflicts: list[str] = []
                if len(outcomes) != 1:
                    group_conflicts.append(
                        f"scope:{scope_ref}:{observed_route}:conflicting_outcomes"
                    )
                elif outcomes[0] not in successful_outcomes:
                    group_conflicts.append(
                        f"scope:{scope_ref}:{observed_route}:non_successful_outcome"
                    )
                if len(memory_statuses) != 1:
                    group_conflicts.append(
                        f"scope:{scope_ref}:{observed_route}:conflicting_memory_causality"
                    )
                if len(specialist_sets) != 1:
                    group_conflicts.append(
                        f"scope:{scope_ref}:{observed_route}:conflicting_specialists"
                    )
                elif any(not specialists for specialists in specialist_sets):
                    group_conflicts.append(
                        f"scope:{scope_ref}:{observed_route}:observed_specialist_required"
                    )
                if group_conflicts:
                    conflict_flags.extend(group_conflicts)
                    continue

                observation_refs = [item.observation_id for item in group]
                evidence_refs = list(
                    dict.fromkeys(
                        reference
                        for item in group
                        for reference in item.evidence_refs
                    )
                )[:100]
                observed_specialists = sorted(
                    {
                        specialist
                        for item in group
                        for specialist in item.observed_specialist_types
                    }
                )
                candidates.append(
                    RoutingAdaptationCandidateContract(
                        candidate_id=(
                            "routing-adaptation-candidate://"
                            f"{expected_route}/from/{observed_route}/{workflow_profile}"
                        ),
                        candidate_status="needs_review",
                        current_route=observed_route,
                        proposed_route=expected_route,
                        workflow_profile=workflow_profile,
                        expected_specialist_type=group[0].expected_specialist_type,
                        observed_specialist_types=observed_specialists,
                        observation_count=len(group),
                        minimum_occurrences=minimum_occurrences,
                        outcome_statuses=outcomes,
                        memory_causality_statuses=memory_statuses,
                        observation_refs=observation_refs,
                        evidence_refs=evidence_refs,
                        rationale=(
                            f"{len(group)} coherent observations routed to "
                            f"{observed_route} instead of expected promoted route "
                            f"{expected_route}; outcome={outcomes[0]}; "
                            f"memory={memory_statuses[0]}; "
                            f"specialists={','.join(observed_specialists) or 'none'}"
                        ),
                        proposed_tests=[
                            f"eval://routing/{expected_route}/equivalent-cases",
                            "python tools/engineering_gate.py --mode standard",
                        ],
                        rollback_plan_ref=(
                            f"rollback://routing/{expected_route}/current-baseline"
                        ),
                        risk_level="moderate",
                        blockers=[],
                        generated_at=generated_at,
                    )
                )
                if len(candidates) >= max_candidates:
                    break

        conflict_flags = sorted(set(conflict_flags))
        resolved_blockers = sorted(set(resolved_blockers))
        status = (
            "blocked"
            if resolved_blockers
            else (
                "attention_required"
                if conflict_flags
                else (
                    "evidence_ready_for_human_review"
                    if candidates
                    else "no_adaptation_candidate"
                )
            )
        )
        return RoutingAdaptationReportContract(
            report_id=report_id,
            report_status=status,
            observation_count=len(bounded_observations),
            route_match_count=sum(item.route_match for item in bounded_observations),
            route_mismatch_count=sum(
                not item.route_match for item in bounded_observations
            ),
            candidate_count=len(candidates),
            candidates=candidates,
            conflict_flags=conflict_flags,
            evidence_refs=list(dict.fromkeys(all_evidence))[:100],
            blockers=resolved_blockers,
            generated_at=generated_at,
        )

    @staticmethod
    def build_skill_evolution_operator_view(
        *,
        view_id: str,
        pattern_report: RecurringPatternReportContract,
        candidates: list[SkillCandidateContract],
        proposals: list[EvolutionProposalContract],
        generated_at: str,
    ) -> SkillEvolutionOperatorViewContract:
        """Correlate persisted skill evidence without mutating evolution state."""

        patterns_by_ref = {
            pattern.pattern_id: pattern for pattern in pattern_report.patterns
        }
        proposals_by_candidate_ref: dict[str, EvolutionProposalContract] = {}
        for proposal in proposals:
            if proposal.proposal_type != "skill_candidate":
                continue
            for candidate_ref in proposal.candidate_refs:
                proposals_by_candidate_ref.setdefault(candidate_ref, proposal)

        registered_pattern_refs = {
            pattern_ref
            for candidate in candidates
            for pattern_ref in candidate.source_pattern_refs
        }
        items: list[SkillEvolutionOperatorItemContract] = []
        for candidate in candidates:
            patterns = [
                patterns_by_ref[pattern_ref]
                for pattern_ref in candidate.source_pattern_refs
                if pattern_ref in patterns_by_ref
            ]
            pattern = patterns[0] if patterns else None
            proposal = proposals_by_candidate_ref.get(candidate.skill_candidate_id)
            review_context = (
                dict(proposal.strategy_context.get("evolution_review", {}))
                if proposal is not None
                else {}
            )
            sandbox_context = (
                dict(proposal.strategy_context.get("skill_sandbox_eval", {}))
                if proposal is not None
                else {}
            )
            review_status = str(
                review_context.get("review_status") or candidate.review_status
            )
            sandbox_eval_status = (
                str(sandbox_context["eval_status"])
                if sandbox_context.get("eval_status") is not None
                else None
            )
            blockers = list(candidate.blockers)
            if candidate.source_pattern_refs and pattern is None:
                blockers.append("source_pattern_not_available_in_view")
            if pattern is not None:
                blockers.extend(pattern.blockers)
                blockers.extend(pattern.conflict_flags)
            if proposal is not None:
                blockers.extend(proposal.optimization_blockers)
                blockers.extend(
                    str(value) for value in review_context.get("blockers", [])
                )
                blockers.extend(
                    str(value) for value in sandbox_context.get("blockers", [])
                )
            blockers = sorted(set(blockers))

            if blockers:
                evolution_status = "blocked"
                next_operator_action = "resolve_evolution_blockers"
            elif proposal is None:
                evolution_status = "candidate_registered"
                next_operator_action = "create_skill_evolution_proposal"
            elif review_status in {"rejected", "rolled_back"}:
                evolution_status = f"human_review_{review_status}"
                next_operator_action = "close_or_revise_skill_candidate"
            elif sandbox_eval_status == "passed_pending_release_gate":
                evolution_status = "sandbox_passed_pending_release_review"
                next_operator_action = "prepare_human_release_review"
            elif sandbox_eval_status is not None:
                evolution_status = "sandbox_attention_required"
                next_operator_action = "resolve_skill_sandbox_evidence"
            elif review_status in {"approved", "sandboxed"}:
                evolution_status = "sandbox_eval_pending"
                next_operator_action = "run_skill_sandbox_eval"
            else:
                evolution_status = "human_review_pending"
                next_operator_action = "review_skill_candidate"

            proposal_status = (
                proposal.optimization_safety_status if proposal is not None else None
            )
            evidence_refs = list(candidate.evidence_refs)
            if pattern is not None:
                evidence_refs.extend(pattern.evidence_refs)
            if proposal is not None:
                evidence_refs.extend(proposal.baseline_refs)
            evidence_refs = list(dict.fromkeys(evidence_refs))
            items.append(
                SkillEvolutionOperatorItemContract(
                    skill_candidate_id=candidate.skill_candidate_id,
                    skill_id=candidate.skill_id,
                    skill_name=candidate.skill_name,
                    version=candidate.version,
                    workflow_profile=candidate.workflow_profile,
                    route=pattern.route if pattern is not None else None,
                    domain=candidate.domain,
                    specialist_type=candidate.specialist_type,
                    risk_level=str(candidate.risk_level),
                    registry_status=candidate.registry_status,
                    review_status=review_status,
                    activation_status=candidate.activation_status,
                    evolution_status=evolution_status,
                    source_pattern_refs=list(candidate.source_pattern_refs),
                    pattern_status=pattern.pattern_status if pattern is not None else None,
                    pattern_summary=pattern.pattern_summary if pattern is not None else None,
                    occurrence_count=(pattern.occurrence_count if pattern is not None else None),
                    minimum_occurrences=(
                        pattern.minimum_occurrences if pattern is not None else None
                    ),
                    confidence_status=(
                        pattern.confidence_status if pattern is not None else None
                    ),
                    proposal_id=(
                        str(proposal.evolution_proposal_id)
                        if proposal is not None
                        else None
                    ),
                    proposal_status=proposal_status,
                    sandbox_eval_ref=(
                        str(sandbox_context["eval_id"])
                        if sandbox_context.get("eval_id") is not None
                        else None
                    ),
                    sandbox_eval_status=sandbox_eval_status,
                    sandbox_pass_rate=(
                        float(sandbox_context["pass_rate"])
                        if sandbox_context.get("pass_rate") is not None
                        else None
                    ),
                    allowed_tools=list(candidate.allowed_tools),
                    evidence_refs=evidence_refs,
                    proposed_tests=list(candidate.proposed_tests),
                    rollback_plan_ref=candidate.rollback_plan_ref,
                    blockers=blockers,
                    next_operator_action=next_operator_action,
                )
            )

        unregistered_pattern_refs = sorted(
            pattern.pattern_id
            for pattern in pattern_report.patterns
            if pattern.pattern_id not in registered_pattern_refs
        )
        view_blockers = sorted(
            set(pattern_report.blockers).union(
                blocker for item in items for blocker in item.blockers
            )
        )
        if not candidates and not pattern_report.patterns:
            view_status = "empty"
        elif any(item.evolution_status == "blocked" for item in items):
            view_status = "attention_required"
        elif unregistered_pattern_refs and not items:
            view_status = "pattern_review_required"
        elif items and all(
            item.evolution_status == "sandbox_passed_pending_release_review"
            for item in items
        ):
            view_status = "release_review_required"
        else:
            view_status = "operator_action_required"
        return SkillEvolutionOperatorViewContract(
            view_id=view_id,
            view_status=view_status,
            pattern_report_id=pattern_report.report_id,
            pattern_report_status=pattern_report.report_status,
            pattern_count=len(pattern_report.patterns),
            candidate_count=len(candidates),
            items=items,
            unregistered_pattern_refs=unregistered_pattern_refs,
            blockers=view_blockers,
            generated_at=generated_at,
        )

    @staticmethod
    def build_longitudinal_learning_report(
        *,
        report_id: str,
        targets: list[LearningVersionTargetContract],
        observations: list[LearningOutcomeObservationContract],
        generated_at: str,
        minimum_observations: int = 2,
    ) -> LongitudinalLearningReportContract:
        """Measure versioned learning evidence without creating promotion authority."""

        if not 2 <= minimum_observations <= 100:
            raise ValueError("minimum_observations must be between 2 and 100")
        target_keys: set[tuple[str, str, str]] = set()
        observation_ids: set[str] = set()
        duplicate_target_refs: list[str] = []
        duplicate_observation_refs: list[str] = []
        for target in targets:
            key = (target.capability_kind, target.capability_id, target.version_ref)
            if key in target_keys:
                duplicate_target_refs.append(target.target_id)
            target_keys.add(key)
        for observation in observations:
            if observation.observation_id in observation_ids:
                duplicate_observation_refs.append(observation.observation_id)
            observation_ids.add(observation.observation_id)

        unknown_observation_refs = [
            observation.observation_id
            for observation in observations
            if (
                observation.capability_kind,
                observation.capability_id,
                observation.version_ref,
            )
            not in target_keys
        ]
        metrics: list[LongitudinalVersionMetricsContract] = []
        for target in targets:
            scoped = [
                observation
                for observation in observations
                if observation.capability_kind == target.capability_kind
                and observation.capability_id == target.capability_id
                and observation.version_ref == target.version_ref
            ]
            blockers: list[str] = []
            if (
                target.runtime_activation_allowed
                or target.promotion_authorized
                or target.automatic_promotion_allowed
                or target.core_mutation_allowed
            ):
                blockers.append("target_authority_claim_not_allowed")
            if not target.evidence_refs:
                blockers.append("target_evidence_required")
            if any(
                observation.promotion_authorized
                or observation.automatic_promotion_allowed
                or observation.core_mutation_allowed
                for observation in scoped
            ):
                blockers.append("observation_authority_claim_not_allowed")
            if any(
                not 0.0 <= observation.success_score <= 1.0
                or observation.rework_count < 0
                for observation in scoped
            ):
                blockers.append("invalid_observation_metric")
            runtime_count = sum(
                observation.source_kind == "runtime_mission" for observation in scoped
            )
            offline_count = sum(
                observation.source_kind == "offline_eval" for observation in scoped
            )
            if target.runtime_status.startswith("inactive") and runtime_count:
                blockers.append("inactive_target_has_runtime_observation")
            observation_count = len(scoped)
            success_rate = (
                round(sum(observation.success for observation in scoped) / observation_count, 4)
                if observation_count
                else 0.0
            )
            average_success_score = (
                round(
                    sum(observation.success_score for observation in scoped)
                    / observation_count,
                    4,
                )
                if observation_count
                else 0.0
            )
            rework_rate = (
                round(
                    sum(observation.rework_count for observation in scoped)
                    / observation_count,
                    4,
                )
                if observation_count
                else 0.0
            )
            feedback = [
                observation.feedback_assessment
                for observation in scoped
                if observation.feedback_assessment
                and observation.feedback_assessment != "not_applicable"
            ]
            helpful_feedback_rate = (
                round(sum(item == "helpful" for item in feedback) / len(feedback), 4)
                if feedback
                else 0.0
            )
            regression_flags = sorted(
                {
                    flag
                    for observation in scoped
                    for flag in observation.regression_flags
                }
            )
            rollback_count = sum(
                observation.rollback_observed for observation in scoped
            ) + int(target.rollback_status == "rolled_back")
            evidence_refs = list(
                dict.fromkeys(
                    [
                        target.target_id,
                        *target.evidence_refs,
                        *(ref for observation in scoped for ref in observation.evidence_refs),
                    ]
                )
            )[:250]
            metrics.append(
                LongitudinalVersionMetricsContract(
                    capability_kind=target.capability_kind,
                    capability_id=target.capability_id,
                    version_ref=target.version_ref,
                    lifecycle_status=target.lifecycle_status,
                    runtime_status=target.runtime_status,
                    observation_count=observation_count,
                    runtime_observation_count=runtime_count,
                    offline_observation_count=offline_count,
                    mission_count=len(
                        {observation.mission_id for observation in scoped if observation.mission_id}
                    ),
                    success_rate=success_rate,
                    average_success_score=average_success_score,
                    rework_rate=rework_rate,
                    feedback_count=len(feedback),
                    helpful_feedback_rate=helpful_feedback_rate,
                    regression_count=len(regression_flags),
                    rollback_count=rollback_count,
                    trend_status="pending_comparison",
                    evidence_refs=evidence_refs,
                    blockers=sorted(set(blockers)),
                    baseline_version_ref=target.baseline_version_ref,
                )
            )

        metric_by_key = {
            (metric.capability_kind, metric.capability_id, metric.version_ref): metric
            for metric in metrics
        }
        resolved_metrics: list[LongitudinalVersionMetricsContract] = []
        for metric in metrics:
            baseline = (
                metric_by_key.get(
                    (
                        metric.capability_kind,
                        metric.capability_id,
                        metric.baseline_version_ref,
                    )
                )
                if metric.baseline_version_ref
                else None
            )
            success_delta = (
                round(metric.success_rate - baseline.success_rate, 4)
                if baseline is not None
                else None
            )
            rework_delta = (
                round(metric.rework_rate - baseline.rework_rate, 4)
                if baseline is not None
                else None
            )
            blockers = list(metric.blockers)
            if metric.baseline_version_ref and baseline is None:
                blockers.append("baseline_version_evidence_missing")
            if blockers:
                trend_status = "blocked"
            elif metric.regression_count or metric.rollback_count:
                trend_status = "regression_or_rollback_observed"
            elif metric.version_ref.startswith("baseline://"):
                trend_status = (
                    "baseline_reference"
                    if metric.observation_count >= minimum_observations
                    else "insufficient_evidence"
                )
            elif metric.observation_count < minimum_observations:
                trend_status = "insufficient_evidence"
            elif baseline is None or baseline.observation_count < minimum_observations:
                trend_status = "insufficient_baseline_evidence"
            elif success_delta is not None and success_delta < 0:
                trend_status = "regression_detected"
            elif rework_delta is not None and rework_delta > 0:
                trend_status = "regression_detected"
            elif (
                success_delta is not None
                and success_delta > 0
                and rework_delta is not None
                and rework_delta <= 0
                and metric.feedback_count > 0
                and metric.helpful_feedback_rate >= 0.5
            ):
                trend_status = "sustained_gain"
            else:
                trend_status = "stable_or_mixed"
            resolved_metrics.append(
                replace(
                    metric,
                    trend_status=trend_status,
                    blockers=sorted(set(blockers)),
                    success_rate_delta=success_delta,
                    rework_rate_delta=rework_delta,
                )
            )

        regression_flags = [
            f"{metric.capability_kind}:{metric.version_ref}:{metric.trend_status}"
            for metric in resolved_metrics
            if metric.trend_status
            in {"regression_detected", "regression_or_rollback_observed", "blocked"}
        ]
        if duplicate_target_refs:
            regression_flags.append("duplicate_version_targets")
        if duplicate_observation_refs:
            regression_flags.append("duplicate_learning_observations")
        if unknown_observation_refs:
            regression_flags.append("observations_without_version_target")
        if regression_flags:
            report_status = "attention_required"
        elif any(metric.trend_status == "sustained_gain" for metric in resolved_metrics):
            report_status = "sustained_gain_observed"
        elif resolved_metrics and all(
            metric.trend_status
            in {"insufficient_evidence", "insufficient_baseline_evidence"}
            for metric in resolved_metrics
        ):
            report_status = "insufficient_evidence"
        elif resolved_metrics:
            report_status = "mixed_or_stable"
        else:
            report_status = "no_version_targets"

        missing_evidence_refs = [
            metric.version_ref
            for metric in resolved_metrics
            if metric.observation_count < minimum_observations
        ]
        rollback_refs = [
            target.rollback_plan_ref
            for target in targets
            if target.rollback_status == "rolled_back" and target.rollback_plan_ref
        ]
        observed_at_values = sorted(observation.observed_at for observation in observations)
        limitations = ["measurement_does_not_authorize_promotion"]
        if any(metric.offline_observation_count for metric in resolved_metrics):
            limitations.append("offline_eval_is_not_longitudinal_runtime_evidence")
        if any(metric.runtime_status.startswith("inactive") for metric in resolved_metrics):
            limitations.append("inactive_versions_have_no_valid_runtime_claim")
        return LongitudinalLearningReportContract(
            report_id=report_id,
            report_status=report_status,
            minimum_observations=minimum_observations,
            target_count=len(targets),
            observation_count=len(observations),
            observed_version_count=sum(
                metric.observation_count > 0 for metric in resolved_metrics
            ),
            version_metrics=resolved_metrics,
            missing_evidence_refs=sorted(set(missing_evidence_refs)),
            regression_flags=sorted(set(regression_flags)),
            rollback_refs=sorted(set(rollback_refs)),
            limitations=limitations,
            evidence_refs=list(
                dict.fromkeys(
                    [
                        *duplicate_target_refs,
                        *duplicate_observation_refs,
                        *unknown_observation_refs,
                        *(ref for metric in resolved_metrics for ref in metric.evidence_refs),
                    ]
                )
            )[:500],
            generated_at=generated_at,
            period_start=observed_at_values[0] if observed_at_values else None,
            period_end=observed_at_values[-1] if observed_at_values else None,
            read_only=True,
            human_review_required=True,
            promotion_authorized=False,
            automatic_promotion_allowed=False,
            core_mutation_allowed=False,
        )

    @staticmethod
    def build_regression_readiness_report(
        *,
        report_id: str,
        capability_results: list[CapabilityReadinessContract],
        gate_mode: str,
        gate_status: str,
        test_status: str,
        document_status: str,
        backlog_status: str,
        next_ready_item: str | None,
        status_drift: list[str],
        evidence_refs: list[str],
        generated_at: str,
    ) -> RegressionReadinessReportContract:
        """Aggregate repository readiness without authorizing release."""

        capability_counts = {
            status: sum(
                1 for item in capability_results if item.readiness_status == status
            )
            for status in ("ready", "partial", "attention_required", "missing", "deferred")
        }
        scored_capabilities = [
            item for item in capability_results if item.scope_status != "deferred"
        ]
        capability_score = (
            round(
                sum(item.score for item in scored_capabilities)
                / len(scored_capabilities)
            )
            if scored_capabilities
            else 0
        )
        gate_score = 100 if gate_status == "passed" else 0
        test_score = 100 if test_status == "passed" else 0
        document_score = 100 if document_status == "healthy" else 0
        backlog_score = (
            100
            if backlog_status in {"synchronized", "queue_exhausted"}
            else 0
        )
        overall_score = round(
            capability_score * 0.7
            + gate_score * 0.1
            + test_score * 0.1
            + document_score * 0.05
            + backlog_score * 0.05
        )

        blockers = list(status_drift)
        if gate_status == "failed":
            blockers.append("engineering_gate_failed")
        if document_status != "healthy":
            blockers.append("document_guardrails_failed")
        if backlog_status not in {"synchronized", "queue_exhausted"}:
            blockers.append("backlog_status_drift")
        blockers.extend(
            f"baseline_capability_missing:{item.capability_id}"
            for item in capability_results
            if item.scope_status == "baseline" and item.readiness_status == "missing"
        )
        blockers = list(dict.fromkeys(blockers))

        warnings: list[str] = []
        if gate_status == "not_run":
            warnings.append("engineering_gate_evidence_not_refreshed")
        if test_status == "not_run":
            warnings.append("test_evidence_not_refreshed")
        candidate_gaps = [
            item.capability_id
            for item in capability_results
            if item.scope_status == "candidate"
            and item.readiness_status in {"attention_required", "missing"}
        ]
        if candidate_gaps:
            warnings.append(f"candidate_gaps:{','.join(candidate_gaps)}")

        if blockers:
            status = "blocked"
        elif gate_status != "passed" or test_status != "passed":
            status = "evidence_required"
        elif candidate_gaps or capability_counts["partial"]:
            status = "ready_with_known_gaps"
        else:
            status = "ready"

        return RegressionReadinessReportContract(
            report_id=report_id,
            status=status,
            overall_score=overall_score,
            capability_counts=capability_counts,
            capability_results=list(capability_results),
            gate_mode=gate_mode,
            gate_status=gate_status,
            test_status=test_status,
            document_status=document_status,
            backlog_status=backlog_status,
            next_ready_item=next_ready_item,
            status_drift=list(dict.fromkeys(status_drift)),
            blockers=blockers,
            warnings=warnings,
            evidence_refs=list(dict.fromkeys(evidence_refs)),
            generated_at=generated_at,
            read_only=True,
            autonomous_release_allowed=False,
        )

    def audit_flow(
        self,
        query: ObservabilityQuery,
        *,
        required_events: tuple[str, ...] = DEFAULT_REQUIRED_FLOW_EVENTS,
    ) -> FlowAudit:
        """Audit a correlated flow for trace completeness and operational anomalies."""

        events = self.list_recent_events(query)
        metrics = self.summarize_flow(query)
        if not events:
            return FlowAudit(
                request_id=query.request_id,
                session_id=query.session_id,
                mission_id=query.mission_id,
                total_events=0,
                workflow_domain_route=None,
                workflow_profile=None,
                workflow_governance_mode=None,
                workflow_trace_status="incomplete",
                workflow_profile_status="incomplete",
                contract_validation_status="incomplete",
                contract_validation_errors=[],
                contract_validation_retry_applied=False,
                output_validation_status="incomplete",
                output_validation_errors=[],
                output_validation_retry_applied=False,
                workflow_output_status="incomplete",
                workflow_output_errors=[],
                memory_causality_status="incomplete",
                primary_mind=None,
                primary_route=None,
                dominant_tension=None,
                arbitration_source=None,
                primary_domain_driver=None,
                metacognitive_guidance_status="incomplete",
                metacognitive_guidance_summary=None,
                metacognitive_effects=[],
                metacognitive_containment_recommendation=None,
                mind_disagreement_status="incomplete",
                mind_validation_checkpoint_status="incomplete",
                capability_decision_status="incomplete",
                capability_decision_objective=None,
                capability_decision_reason=None,
                capability_decision_selected_mode=None,
                capability_authorization_status="incomplete",
                capability_decision_tool_class=None,
                capability_decision_handoff_mode=None,
                capability_decision_eligible_capabilities=[],
                capability_decision_selected_capabilities=[],
                effective_autonomy_level=None,
                autonomy_ladder_status=None,
                max_autonomy_capability_mode=None,
                autonomy_human_confirmation_required=True,
                autonomy_confirmation_mode=None,
                autonomy_blocked_runtime_actions=[],
                capability_effectiveness="incomplete",
                handoff_adapter_status="incomplete",
                request_identity_status="incomplete",
                mission_policy_status="incomplete",
                request_identity_mismatch_flags=[],
                expanded_eval_status="attention_required",
                surface_axis_status="attention_required",
                ecosystem_state_status="attention_required",
                operational_ecosystem_state_status="not_applicable",
                active_work_items=[],
                active_artifact_refs=[],
                open_checkpoint_refs=[],
                surface_presence=[],
                surface_continuity_status="not_applicable",
                linked_surface_count=0,
                surface_identity_conflict_flags=[],
                multi_surface_readiness="not_applicable",
                experiment_lane_status="attention_required",
                wave2_candidate_class="baseline_hardening",
                experiment_entry_status="blocked_by_drift",
                experiment_exit_status="freeze_and_review",
                promotion_readiness="blocked",
                event_names=[],
                missing_required_events=list(required_events),
                anomaly_flags=["no_events_found"],
                mind_domain_specialist_status="incomplete",
                mind_domain_specialist_chain_status="incomplete",
                mind_domain_specialist_chain=None,
                mind_domain_specialist_effectiveness="incomplete",
                mind_domain_specialist_mismatch_flags=[],
                cognitive_recomposition_applied=False,
                cognitive_recomposition_reason=None,
                cognitive_recomposition_trigger=None,
                adaptive_intervention_status="incomplete",
                adaptive_intervention_reason=None,
                adaptive_intervention_trigger=None,
                adaptive_intervention_selected_action=None,
                adaptive_intervention_expected_effect=None,
                adaptive_intervention_effects=[],
                adaptive_intervention_effectiveness="incomplete",
                adaptive_intervention_policy_status="incomplete",
                cognitive_strategy_shift_status="incomplete",
                cognitive_strategy_shift_applied=False,
                cognitive_strategy_shift_summary=None,
                cognitive_strategy_shift_trigger=None,
                cognitive_strategy_shift_effects=[],
                semantic_memory_source=None,
                procedural_memory_source=None,
                semantic_memory_focus=[],
                semantic_memory_anchor_refs=[],
                semantic_memory_evidence_refs=[],
                semantic_memory_use_reason=None,
                semantic_memory_non_use_reason=None,
                memory_influence_used_refs=[],
                memory_influence_ignored_refs=[],
                memory_influence_reasons=[],
                memory_influence_evidence_refs=[],
                procedural_memory_hint=None,
                semantic_memory_effects=[],
                procedural_memory_effects=[],
                semantic_memory_lifecycle=None,
                procedural_memory_lifecycle=None,
                memory_lifecycle_status="incomplete",
                memory_review_status="incomplete",
                memory_maintenance_status="incomplete",
                memory_maintenance_reason=None,
                memory_maintenance_fallback_mode=None,
                context_compaction_status=None,
                cross_session_recall_status=None,
                memory_consolidation_status="incomplete",
                memory_fixation_status="incomplete",
                memory_archive_status="incomplete",
                memory_corpus_status="incomplete",
                memory_retention_pressure=None,
                memory_maintenance_effectiveness="incomplete",
                semantic_memory_specialists=[],
                procedural_memory_specialists=[],
                continuity_action=None,
                continuity_source=None,
                continuity_target_mission_id=None,
                continuity_target_goal=None,
                continuity_runtime_mode=None,
                specialist_subflow_status="incomplete",
                specialist_subflow_runtime_mode=None,
                mission_runtime_state_status="incomplete",
                registry_domains=[],
                domain_specialists=[],
                shadow_specialists=[],
                domain_alignment_status="incomplete",
                mind_alignment_status="incomplete",
                identity_alignment_status="incomplete",
                memory_alignment_status="incomplete",
                user_scope_status="incomplete",
                organization_scope_status="incomplete",
                specialist_recurrence_status="incomplete",
                specialist_sovereignty_status="incomplete",
                missing_continuity_signals=[],
                continuity_anomaly_flags=[],
                continuity_trace_status="attention_required",
                governance_decision=None,
                operation_status=None,
                duration_seconds=0.0,
                source_services=[],
            )

        event_names = [event.event_name for event in events]
        governance_event = self._first_event(events, "governance_checked")
        operation_event = self._first_event(events, "operation_completed")
        operation_dispatched_event = self._first_event(events, "operation_dispatched")
        continuity_event = self._first_event(events, "continuity_decided")
        continuity_runtime_event = self._first_event(events, "continuity_subflow_completed")
        specialist_subflow_event = self._first_event(events, "specialist_subflow_completed")
        mission_runtime_event = self._first_event(events, "mission_runtime_state_declared")
        workflow_composed_event = self._first_event(events, "workflow_composed")
        workflow_governance_event = self._first_event(events, "workflow_governance_declared")
        workflow_completed_event = self._first_event(events, "workflow_completed")
        directive_event = self._first_event(events, "directive_composed")
        plan_event = self._first_event(events, "plan_built")
        plan_refined_event = self._first_event(events, "plan_refined")
        plan_governed_event = self._first_event(events, "plan_governed")
        context_event = self._first_event(events, "context_composed")
        response_event = self._first_event(events, "response_synthesized")
        memory_event = self._first_event(events, "memory_recorded")
        memory_recovered_event = self._first_event(events, "memory_recovered")
        domain_registry_event = self._first_event(events, "domain_registry_resolved")
        shared_memory_event = self._first_event(events, "specialist_shared_memory_linked")
        specialist_contract_event = self._first_event(events, "specialist_contracts_composed")
        specialist_selection_event = self._first_event(events, "specialist_selection_decided")
        specialist_domain_event = self._first_event(events, "domain_specialist_completed")
        specialist_shadow_event = self._first_event(events, "specialist_shadow_mode_completed")
        first_event = events[0]
        governance_decision = (
            str(governance_event.payload.get("decision")) if governance_event else None
        )
        operation_status = str(operation_event.payload.get("status")) if operation_event else None
        continuity_action = (
            str(continuity_event.payload.get("continuity_action"))
            if continuity_event and continuity_event.payload.get("continuity_action") is not None
            else None
        )
        continuity_source = (
            str(continuity_event.payload.get("continuity_source"))
            if continuity_event and continuity_event.payload.get("continuity_source") is not None
            else None
        )
        continuity_target_mission_id = (
            str(continuity_event.payload.get("continuity_target_mission_id"))
            if continuity_event
            and continuity_event.payload.get("continuity_target_mission_id") is not None
            else None
        )
        continuity_target_goal = (
            str(continuity_event.payload.get("continuity_target_goal"))
            if continuity_event
            and continuity_event.payload.get("continuity_target_goal") is not None
            else None
        )
        continuity_runtime_mode = (
            str(continuity_runtime_event.payload.get("runtime_mode"))
            if continuity_runtime_event
            and continuity_runtime_event.payload.get("runtime_mode") is not None
            else "baseline_linear"
        )
        specialist_subflow_runtime_mode = (
            str(specialist_subflow_event.payload.get("runtime_mode"))
            if specialist_subflow_event
            and specialist_subflow_event.payload.get("runtime_mode") is not None
            else None
        )
        workflow_domain_route = (
            str(workflow_composed_event.payload.get("workflow_domain_route"))
            if workflow_composed_event
            and workflow_composed_event.payload.get("workflow_domain_route") is not None
            else (
                str(workflow_completed_event.payload.get("workflow_domain_route"))
                if workflow_completed_event
                and workflow_completed_event.payload.get("workflow_domain_route") is not None
                else (
                    str(operation_event.payload.get("workflow_domain_route"))
                    if operation_event and operation_event.payload.get("workflow_domain_route") is not None
                    else None
                )
            )
        )
        workflow_profile = (
            str(workflow_composed_event.payload.get("workflow_profile"))
            if workflow_composed_event
            and workflow_composed_event.payload.get("workflow_profile") is not None
            else (
                str(workflow_completed_event.payload.get("workflow_profile"))
                if workflow_completed_event
                and workflow_completed_event.payload.get("workflow_profile") is not None
                else (
                    str(operation_event.payload.get("workflow_profile"))
                    if operation_event and operation_event.payload.get("workflow_profile") is not None
                    else None
                )
            )
        )
        workflow_governance_mode = (
            str(workflow_governance_event.payload.get("workflow_governance_mode"))
            if workflow_governance_event
            and workflow_governance_event.payload.get("workflow_governance_mode") is not None
            else (
                str(workflow_completed_event.payload.get("workflow_governance_mode"))
                if workflow_completed_event
                and workflow_completed_event.payload.get("workflow_governance_mode") is not None
                else None
            )
        )
        contract_validation_status = (
            str(response_event.payload.get("contract_validation_status"))
            if response_event
            and response_event.payload.get("contract_validation_status") is not None
            else (
                str(plan_event.payload.get("contract_validation_status"))
                if plan_event
                and plan_event.payload.get("contract_validation_status") is not None
                else "not_applicable"
            )
        )
        contract_validation_errors = [
            str(item)
            for item in (
                response_event.payload.get("contract_validation_errors", [])
                if response_event
                else (
                    plan_event.payload.get("contract_validation_errors", [])
                    if plan_event
                    else []
                )
            )
        ]
        contract_validation_retry_applied = bool(
            response_event.payload.get("contract_validation_retry_applied")
            if response_event
            and response_event.payload.get("contract_validation_retry_applied") is not None
            else (
                plan_event.payload.get("contract_validation_retry_applied")
                if plan_event
                and plan_event.payload.get("contract_validation_retry_applied") is not None
                else False
            )
        )
        output_validation_status = (
            str(response_event.payload.get("output_validation_status"))
            if response_event
            and response_event.payload.get("output_validation_status") is not None
            else ("incomplete" if response_event is None else "not_applicable")
        )
        output_validation_errors = [
            str(item)
            for item in (
                response_event.payload.get("output_validation_errors", [])
                if response_event
                else []
            )
        ]
        output_validation_retry_applied = bool(
            response_event.payload.get("output_validation_retry_applied")
            if response_event
            and response_event.payload.get("output_validation_retry_applied") is not None
            else False
        )
        workflow_output_status = (
            str(response_event.payload.get("workflow_output_status"))
            if response_event
            and response_event.payload.get("workflow_output_status") is not None
            else ("incomplete" if response_event is None else "not_applicable")
        )
        workflow_output_errors = [
            str(item)
            for item in (
                response_event.payload.get("workflow_output_errors", [])
                if response_event
                else []
            )
        ]
        primary_mind = (
            str(context_event.payload.get("primary_mind"))
            if context_event
            and context_event.payload.get("primary_mind") is not None
            else (
                str(plan_event.payload.get("primary_mind"))
                if plan_event and plan_event.payload.get("primary_mind") is not None
                else (
                    str(response_event.payload.get("primary_mind"))
                    if response_event
                    and response_event.payload.get("primary_mind") is not None
                    else None
                )
            )
        )
        primary_route = (
            str(plan_event.payload.get("primary_route"))
            if plan_event and plan_event.payload.get("primary_route") is not None
            else (
                str(response_event.payload.get("primary_route"))
                if response_event
                and response_event.payload.get("primary_route") is not None
                else (
                    str(mission_runtime_event.payload.get("primary_route"))
                    if mission_runtime_event
                    and mission_runtime_event.payload.get("primary_route") is not None
                    else None
                )
            )
        )
        dominant_tension = (
            str(context_event.payload.get("dominant_tension"))
            if context_event
            and context_event.payload.get("dominant_tension") is not None
            else (
                str(plan_event.payload.get("dominant_tension"))
                if plan_event and plan_event.payload.get("dominant_tension") is not None
                else None
            )
        )
        arbitration_source = (
            str(context_event.payload.get("arbitration_source"))
            if context_event
            and context_event.payload.get("arbitration_source") is not None
            else (
                str(plan_event.payload.get("arbitration_source"))
                if plan_event and plan_event.payload.get("arbitration_source") is not None
                else (
                    str(response_event.payload.get("arbitration_source"))
                    if response_event
                    and response_event.payload.get("arbitration_source") is not None
                    else None
                )
            )
        )
        primary_domain_driver = (
            str(context_event.payload.get("primary_domain_driver"))
            if context_event
            and context_event.payload.get("primary_domain_driver") is not None
            else (
                str(plan_event.payload.get("primary_domain_driver"))
                if plan_event and plan_event.payload.get("primary_domain_driver") is not None
                else (
                    str(response_event.payload.get("primary_domain_driver"))
                    if response_event
                    and response_event.payload.get("primary_domain_driver") is not None
                    else None
                )
            )
        )
        metacognitive_guidance_summary = (
            str(plan_event.payload.get("metacognitive_guidance_summary"))
            if plan_event
            and plan_event.payload.get("metacognitive_guidance_summary") is not None
            else (
                str(response_event.payload.get("metacognitive_guidance_summary"))
                if response_event
                and response_event.payload.get("metacognitive_guidance_summary") is not None
                else None
            )
        )
        metacognitive_effects = [
            str(item)
            for item in (
                plan_event.payload.get("metacognitive_effects", [])
                if plan_event
                else (
                    response_event.payload.get("metacognitive_effects", [])
                    if response_event
                    else []
                )
            )
        ]
        metacognitive_containment_recommendation = (
            str(plan_event.payload.get("metacognitive_containment_recommendation"))
            if plan_event
            and plan_event.payload.get("metacognitive_containment_recommendation")
            is not None
            else (
                str(response_event.payload.get("metacognitive_containment_recommendation"))
                if response_event
                and response_event.payload.get("metacognitive_containment_recommendation")
                is not None
                else None
            )
        )
        cognitive_recomposition_applied = bool(
            (
                context_event.payload.get("cognitive_recomposition_applied")
                if context_event
                else False
            )
            or (
                response_event.payload.get("cognitive_recomposition_applied")
                if response_event
                else False
            )
        )
        cognitive_recomposition_reason = (
            str(context_event.payload.get("cognitive_recomposition_reason"))
            if context_event
            and context_event.payload.get("cognitive_recomposition_reason") is not None
            else (
                str(response_event.payload.get("cognitive_recomposition_reason"))
                if response_event
                and response_event.payload.get("cognitive_recomposition_reason") is not None
                else None
            )
        )
        cognitive_recomposition_trigger = (
            str(context_event.payload.get("cognitive_recomposition_trigger"))
            if context_event
            and context_event.payload.get("cognitive_recomposition_trigger") is not None
            else (
                str(response_event.payload.get("cognitive_recomposition_trigger"))
                if response_event
                and response_event.payload.get("cognitive_recomposition_trigger") is not None
                else None
            )
        )
        adaptive_intervention_status = self._adaptive_intervention_status(
            plan_event=plan_event,
            plan_refined_event=plan_refined_event,
            workflow_composed_event=workflow_composed_event,
            operation_dispatched_event=operation_dispatched_event,
            response_event=response_event,
        )
        adaptive_intervention_source = (
            plan_refined_event
            if plan_refined_event
            and (
                plan_refined_event.payload.get("adaptive_intervention_status") is not None
                or plan_refined_event.payload.get("adaptive_intervention_selected_action")
                is not None
            )
            else (
                plan_event
                if plan_event
                and (
                    plan_event.payload.get("adaptive_intervention_status") is not None
                    or plan_event.payload.get("adaptive_intervention_selected_action")
                    is not None
                )
                else None
            )
        )
        adaptive_intervention_reason = (
            str(adaptive_intervention_source.payload.get("adaptive_intervention_reason"))
            if adaptive_intervention_source
            and adaptive_intervention_source.payload.get("adaptive_intervention_reason")
            is not None
            else (
                str(response_event.payload.get("adaptive_intervention_reason"))
                if response_event
                and response_event.payload.get("adaptive_intervention_reason") is not None
                else None
            )
        )
        adaptive_intervention_trigger = (
            str(adaptive_intervention_source.payload.get("adaptive_intervention_trigger"))
            if adaptive_intervention_source
            and adaptive_intervention_source.payload.get("adaptive_intervention_trigger")
            is not None
            else (
                str(response_event.payload.get("adaptive_intervention_trigger"))
                if response_event
                and response_event.payload.get("adaptive_intervention_trigger") is not None
                else None
            )
        )
        adaptive_intervention_selected_action = (
            str(
                adaptive_intervention_source.payload.get(
                    "adaptive_intervention_selected_action"
                )
            )
            if adaptive_intervention_source
            and adaptive_intervention_source.payload.get(
                "adaptive_intervention_selected_action"
            )
            is not None
            else (
                str(response_event.payload.get("adaptive_intervention_selected_action"))
                if response_event
                and response_event.payload.get("adaptive_intervention_selected_action")
                is not None
                else (
                    str(
                        operation_dispatched_event.payload.get(
                            "adaptive_intervention_selected_action"
                        )
                    )
                    if operation_dispatched_event
                    and operation_dispatched_event.payload.get(
                        "adaptive_intervention_selected_action"
                    )
                    is not None
                    else None
                )
            )
        )
        adaptive_intervention_expected_effect = (
            str(
                adaptive_intervention_source.payload.get(
                    "adaptive_intervention_expected_effect"
                )
            )
            if adaptive_intervention_source
            and adaptive_intervention_source.payload.get(
                "adaptive_intervention_expected_effect"
            )
            is not None
            else (
                str(response_event.payload.get("adaptive_intervention_expected_effect"))
                if response_event
                and response_event.payload.get("adaptive_intervention_expected_effect")
                is not None
                else None
            )
        )
        adaptive_intervention_effects = [
            str(item)
            for item in (
                adaptive_intervention_source.payload.get(
                    "adaptive_intervention_effects",
                    [],
                )
                if adaptive_intervention_source
                else (
                    response_event.payload.get("adaptive_intervention_effects", [])
                    if response_event
                    else []
                )
            )
        ]
        cognitive_strategy_shift_applied = bool(
            (
                plan_refined_event.payload.get("cognitive_strategy_shift_applied")
                if plan_refined_event
                else False
            )
            or (
                response_event.payload.get("cognitive_strategy_shift_applied")
                if response_event
                else False
            )
        )
        cognitive_strategy_shift_summary = (
            str(plan_refined_event.payload.get("cognitive_strategy_shift_summary"))
            if plan_refined_event
            and plan_refined_event.payload.get("cognitive_strategy_shift_summary") is not None
            else (
                str(response_event.payload.get("cognitive_strategy_shift_summary"))
                if response_event
                and response_event.payload.get("cognitive_strategy_shift_summary") is not None
                else None
            )
        )
        cognitive_strategy_shift_trigger = (
            str(plan_refined_event.payload.get("cognitive_strategy_shift_trigger"))
            if plan_refined_event
            and plan_refined_event.payload.get("cognitive_strategy_shift_trigger") is not None
            else (
                str(response_event.payload.get("cognitive_strategy_shift_trigger"))
                if response_event
                and response_event.payload.get("cognitive_strategy_shift_trigger") is not None
                else None
            )
        )
        cognitive_strategy_shift_effects = [
            str(item)
            for item in (
                plan_refined_event.payload.get("cognitive_strategy_shift_effects", [])
                if plan_refined_event
                else (
                    response_event.payload.get("cognitive_strategy_shift_effects", [])
                    if response_event
                    else []
                )
            )
        ]
        semantic_memory_focus = [
            str(item)
            for item in (
                response_event.payload.get("semantic_memory_focus", [])
                if response_event
                else []
            )
        ]
        procedural_memory_hint = (
            str(response_event.payload.get("procedural_memory_hint"))
            if response_event
            and response_event.payload.get("procedural_memory_hint") is not None
            else None
        )
        semantic_memory_source = (
            str(response_event.payload.get("semantic_memory_source"))
            if response_event
            and response_event.payload.get("semantic_memory_source") is not None
            else (
                str(plan_event.payload.get("semantic_memory_source"))
                if plan_event
                and plan_event.payload.get("semantic_memory_source") is not None
                else None
            )
        )
        semantic_memory_anchor_refs = self._dedupe_payload_list(
            events,
            "semantic_memory_anchor_refs",
        )
        semantic_memory_evidence_refs = self._dedupe_payload_list(
            events,
            "semantic_memory_evidence_refs",
        )
        semantic_memory_reason_event = self._first_payload_event(
            events,
            "semantic_memory_use_reason",
        ) or self._first_payload_event(
            events,
            "semantic_memory_non_use_reason",
        )
        semantic_memory_use_reason = self._payload_optional_str(
            semantic_memory_reason_event,
            "semantic_memory_use_reason",
        )
        semantic_memory_non_use_reason = self._payload_optional_str(
            semantic_memory_reason_event,
            "semantic_memory_non_use_reason",
        )
        procedural_memory_source = (
            str(response_event.payload.get("procedural_memory_source"))
            if response_event
            and response_event.payload.get("procedural_memory_source") is not None
            else (
                str(plan_event.payload.get("procedural_memory_source"))
                if plan_event
                and plan_event.payload.get("procedural_memory_source") is not None
                else None
            )
        )
        semantic_memory_effects = [
            str(item)
            for item in (
                response_event.payload.get("semantic_memory_effects", [])
                if response_event
                else (
                    plan_event.payload.get("semantic_memory_effects", [])
                    if plan_event
                    else []
                )
            )
        ]
        procedural_memory_effects = [
            str(item)
            for item in (
                response_event.payload.get("procedural_memory_effects", [])
                if response_event
                else (
                    plan_event.payload.get("procedural_memory_effects", [])
                    if plan_event
                    else []
                )
            )
        ]
        semantic_memory_lifecycle = (
            str(response_event.payload.get("semantic_memory_lifecycle"))
            if response_event
            and response_event.payload.get("semantic_memory_lifecycle") is not None
            else (
                str(plan_event.payload.get("semantic_memory_lifecycle"))
                if plan_event
                and plan_event.payload.get("semantic_memory_lifecycle") is not None
                else None
            )
        )
        procedural_memory_lifecycle = (
            str(response_event.payload.get("procedural_memory_lifecycle"))
            if response_event
            and response_event.payload.get("procedural_memory_lifecycle") is not None
            else (
                str(plan_event.payload.get("procedural_memory_lifecycle"))
                if plan_event
                and plan_event.payload.get("procedural_memory_lifecycle") is not None
                else None
            )
        )
        memory_lifecycle_status = (
            str(response_event.payload.get("memory_lifecycle_status"))
            if response_event
            and response_event.payload.get("memory_lifecycle_status") is not None
            else (
                str(plan_event.payload.get("memory_lifecycle_status"))
                if plan_event
                and plan_event.payload.get("memory_lifecycle_status") is not None
                else (
                    str(memory_event.payload.get("memory_lifecycle_status"))
                    if memory_event
                    and memory_event.payload.get("memory_lifecycle_status") is not None
                    else "not_applicable"
                )
            )
        )
        memory_review_status = (
            str(response_event.payload.get("memory_review_status"))
            if response_event
            and response_event.payload.get("memory_review_status") is not None
            else (
                str(plan_event.payload.get("memory_review_status"))
                if plan_event
                and plan_event.payload.get("memory_review_status") is not None
                else (
                    str(memory_event.payload.get("memory_review_status"))
                    if memory_event
                    and memory_event.payload.get("memory_review_status") is not None
                    else "not_applicable"
                )
            )
        )
        memory_maintenance_status = (
            str(response_event.payload.get("memory_maintenance_status"))
            if response_event
            and response_event.payload.get("memory_maintenance_status") is not None
            else (
                str(plan_event.payload.get("memory_maintenance_status"))
                if plan_event
                and plan_event.payload.get("memory_maintenance_status") is not None
                else (
                    str(memory_recovered_event.payload.get("memory_maintenance_status"))
                    if memory_recovered_event
                    and memory_recovered_event.payload.get("memory_maintenance_status") is not None
                    else "not_applicable"
                )
            )
        )
        memory_maintenance_reason = (
            str(response_event.payload.get("memory_maintenance_reason"))
            if response_event
            and response_event.payload.get("memory_maintenance_reason") is not None
            else (
                str(plan_event.payload.get("memory_maintenance_reason"))
                if plan_event
                and plan_event.payload.get("memory_maintenance_reason") is not None
                else (
                    str(memory_recovered_event.payload.get("memory_maintenance_reason"))
                    if memory_recovered_event
                    and memory_recovered_event.payload.get("memory_maintenance_reason") is not None
                    else None
                )
            )
        )
        memory_maintenance_fallback_mode = (
            str(response_event.payload.get("memory_maintenance_fallback_mode"))
            if response_event
            and response_event.payload.get("memory_maintenance_fallback_mode") is not None
            else (
                str(plan_event.payload.get("memory_maintenance_fallback_mode"))
                if plan_event
                and plan_event.payload.get("memory_maintenance_fallback_mode") is not None
                else (
                    str(memory_recovered_event.payload.get("memory_maintenance_fallback_mode"))
                    if memory_recovered_event
                    and memory_recovered_event.payload.get("memory_maintenance_fallback_mode")
                    is not None
                    else None
                )
            )
        )
        context_compaction_status = (
            str(response_event.payload.get("context_compaction_status"))
            if response_event
            and response_event.payload.get("context_compaction_status") is not None
            else (
                str(plan_event.payload.get("context_compaction_status"))
                if plan_event
                and plan_event.payload.get("context_compaction_status") is not None
                else (
                    str(memory_recovered_event.payload.get("context_compaction_status"))
                    if memory_recovered_event
                    and memory_recovered_event.payload.get("context_compaction_status") is not None
                    else None
                )
            )
        )
        cross_session_recall_status = (
            str(response_event.payload.get("cross_session_recall_status"))
            if response_event
            and response_event.payload.get("cross_session_recall_status") is not None
            else (
                str(plan_event.payload.get("cross_session_recall_status"))
                if plan_event
                and plan_event.payload.get("cross_session_recall_status") is not None
                else (
                    str(memory_recovered_event.payload.get("cross_session_recall_status"))
                    if memory_recovered_event
                    and memory_recovered_event.payload.get("cross_session_recall_status") is not None
                    else None
                )
            )
        )
        memory_consolidation_status = self._lifecycle_support_status(
            response_event=response_event,
            plan_event=plan_event,
            shared_memory_event=shared_memory_event,
            field_name="memory_consolidation_status",
            map_name="memory_consolidation_statuses",
            priority_order=("in_progress", "revisit_before_reuse", "consolidated"),
        )
        memory_fixation_status = self._lifecycle_support_status(
            response_event=response_event,
            plan_event=plan_event,
            shared_memory_event=shared_memory_event,
            field_name="memory_fixation_status",
            map_name="memory_fixation_statuses",
            priority_order=("not_fixed", "fixed"),
        )
        memory_archive_status = self._lifecycle_support_status(
            response_event=response_event,
            plan_event=plan_event,
            shared_memory_event=shared_memory_event,
            field_name="memory_archive_status",
            map_name="memory_archive_statuses",
            priority_order=("archive_candidate", "active_memory"),
        )
        semantic_memory_specialists = [
            str(item)
            for item in (
                shared_memory_event.payload.get("semantic_memory_specialists", [])
                if shared_memory_event
                else []
            )
        ]
        procedural_memory_specialists = [
            str(item)
            for item in (
                shared_memory_event.payload.get("procedural_memory_specialists", [])
                if shared_memory_event
                else []
            )
        ]
        registry_domains = (
            [str(item) for item in domain_registry_event.payload.get("registry_domains", [])]
            if domain_registry_event
            else []
        )
        domain_specialists = (
            [str(item) for item in specialist_domain_event.payload.get("specialist_types", [])]
            if specialist_domain_event
            else []
        )
        shadow_specialists = (
            [str(item) for item in specialist_shadow_event.payload.get("specialist_types", [])]
            if specialist_shadow_event
            else []
        )
        anomaly_flags: list[str] = []
        missing_required_events = [
            event_name for event_name in required_events if event_name not in event_names
        ]
        missing_continuity_signals: list[str] = []
        continuity_anomaly_flags: list[str] = []
        if "error_raised" in event_names:
            anomaly_flags.append("error_raised_present")
        if governance_event is None:
            anomaly_flags.append("governance_check_missing")
        if operation_event and "operation_dispatched" not in event_names:
            anomaly_flags.append("operation_completed_without_dispatch")
        if operation_event is not None and workflow_composed_event is None:
            anomaly_flags.append("workflow_missing_composition")
        if operation_event is not None and workflow_governance_event is None:
            anomaly_flags.append("workflow_missing_governance")
        if operation_event is not None and workflow_completed_event is None:
            anomaly_flags.append("workflow_missing_completion")
        if governance_decision in {"allow", "allow_with_conditions"}:
            if "response_synthesized" not in event_names:
                anomaly_flags.append("allowed_flow_missing_response")
            if "memory_recorded" not in event_names:
                anomaly_flags.append("allowed_flow_missing_memory_record")
            if "operation_dispatched" in event_names and "operation_completed" not in event_names:
                anomaly_flags.append("operation_missing_completion")
        if governance_decision in {"block", "defer_for_validation"} and (
            "governance_blocked" not in event_names
        ):
            anomaly_flags.append("blocked_flow_missing_block_event")
        if contract_validation_status == "invalid":
            anomaly_flags.append("contract_validation_failed")
        if output_validation_status == "invalid":
            anomaly_flags.append("output_validation_failed")
        if workflow_output_status == "misaligned":
            anomaly_flags.append("workflow_output_misaligned")

        if continuity_event is None:
            missing_continuity_signals.append("continuity_decided")
        else:
            if continuity_action is None:
                missing_continuity_signals.append("continuity_action")
            if continuity_source is None:
                missing_continuity_signals.append("continuity_source")
        if response_event is None or response_event.payload.get("continuity_action") is None:
            missing_continuity_signals.append("response_continuity_action")
        if memory_event is None or memory_event.payload.get("continuity_mode") is None:
            missing_continuity_signals.append("memory_continuity_mode")

        response_continuity_action = (
            str(response_event.payload.get("continuity_action"))
            if response_event and response_event.payload.get("continuity_action") is not None
            else None
        )
        memory_continuity_mode = (
            str(memory_event.payload.get("continuity_mode"))
            if memory_event and memory_event.payload.get("continuity_mode") is not None
            else None
        )
        if (
            continuity_action is not None
            and response_continuity_action is not None
            and response_continuity_action != continuity_action
        ):
            continuity_anomaly_flags.append("response_continuity_mismatch")
        if (
            continuity_action is not None
            and memory_continuity_mode is not None
            and memory_continuity_mode != continuity_action
        ):
            continuity_anomaly_flags.append("memory_continuity_mismatch")
        if continuity_action == "retomar" and continuity_target_mission_id is None:
            continuity_anomaly_flags.append("retomar_missing_target_mission")
        if continuity_source == "related_mission" and continuity_target_mission_id is None:
            continuity_anomaly_flags.append("related_source_missing_target_mission")

        continuity_trace_status = self._continuity_trace_status(
            missing_continuity_signals=missing_continuity_signals,
            continuity_anomaly_flags=continuity_anomaly_flags,
        )
        workflow_trace_status = self._workflow_trace_status(
            operation_dispatched_event=operation_dispatched_event,
            workflow_composed_event=workflow_composed_event,
            workflow_governance_event=workflow_governance_event,
            workflow_completed_event=workflow_completed_event,
        )
        workflow_checkpoint_status = self._workflow_checkpoint_status(
            workflow_composed_event=workflow_composed_event,
            workflow_completed_event=workflow_completed_event,
        )
        workflow_resume_status, workflow_resume_point = self._workflow_resume_signals(
            workflow_composed_event=workflow_composed_event,
            workflow_completed_event=workflow_completed_event,
        )
        workflow_pending_checkpoint_count = self._workflow_pending_checkpoint_count(
            workflow_completed_event=workflow_completed_event,
        )
        workflow_profile_status = self._workflow_profile_status(
            workflow_profile=workflow_profile,
            workflow_trace_status=workflow_trace_status,
            response_event=response_event,
            shared_memory_event=shared_memory_event,
            specialist_domain_event=specialist_domain_event,
            workflow_output_status=workflow_output_status,
        )
        memory_causality_status = self._memory_causality_status(
            response_event=response_event,
            shared_memory_event=shared_memory_event,
        )
        domain_alignment_status = self._domain_alignment_status(
            domain_registry_event=domain_registry_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
            specialist_shadow_event=specialist_shadow_event,
        )
        mind_alignment_status = self._mind_alignment_status(
            context_event=context_event,
            plan_event=plan_event,
            response_event=response_event,
        )
        metacognitive_guidance_status = self._metacognitive_guidance_status(
            context_event=context_event,
            plan_event=plan_event,
            response_event=response_event,
        )
        mind_disagreement_status = self._mind_disagreement_status(
            plan_event=plan_event,
            response_event=response_event,
        )
        mind_validation_checkpoint_status = self._mind_validation_checkpoint_status(
            plan_event=plan_event,
            response_event=response_event,
            mind_disagreement_status=mind_disagreement_status,
        )
        capability_source_event = (
            response_event
            if response_event
            and (
                response_event.payload.get("capability_decision_status") is not None
                or response_event.payload.get("capability_decision_selected_mode") is not None
            )
            else (
                operation_dispatched_event
                if operation_dispatched_event
                and (
                    operation_dispatched_event.payload.get("capability_decision_status")
                    is not None
                    or operation_dispatched_event.payload.get(
                        "capability_decision_selected_mode"
                    )
                    is not None
                )
                else (
                    plan_governed_event
                    if plan_governed_event
                    and (
                        plan_governed_event.payload.get("capability_decision_status")
                        is not None
                        or plan_governed_event.payload.get(
                            "capability_decision_selected_mode"
                        )
                        is not None
                    )
                    else (
                        plan_refined_event
                        if plan_refined_event
                        and (
                            plan_refined_event.payload.get("capability_decision_status")
                            is not None
                            or plan_refined_event.payload.get(
                                "capability_decision_selected_mode"
                            )
                            is not None
                        )
                        else plan_event
                    )
                )
            )
        )
        capability_decision_status = self._capability_decision_status(
            source_event=capability_source_event,
        )
        capability_decision_objective = (
            str(capability_source_event.payload.get("capability_decision_objective"))
            if capability_source_event
            and capability_source_event.payload.get("capability_decision_objective")
            is not None
            else None
        )
        capability_decision_reason = (
            str(capability_source_event.payload.get("capability_decision_reason"))
            if capability_source_event
            and capability_source_event.payload.get("capability_decision_reason") is not None
            else None
        )
        capability_decision_selected_mode = (
            str(capability_source_event.payload.get("capability_decision_selected_mode"))
            if capability_source_event
            and capability_source_event.payload.get("capability_decision_selected_mode")
            is not None
            else None
        )
        capability_authorization_status = (
            str(
                capability_source_event.payload.get(
                    "capability_decision_authorization_status"
                )
            )
            if capability_source_event
            and capability_source_event.payload.get(
                "capability_decision_authorization_status"
            )
            is not None
            else "not_applicable"
        )
        effective_autonomy_level = (
            str(capability_source_event.payload.get("effective_autonomy_level"))
            if capability_source_event
            and capability_source_event.payload.get("effective_autonomy_level")
            is not None
            else None
        )
        autonomy_ladder_status = (
            str(capability_source_event.payload.get("autonomy_ladder_status"))
            if capability_source_event
            and capability_source_event.payload.get("autonomy_ladder_status")
            is not None
            else None
        )
        max_autonomy_capability_mode = (
            str(capability_source_event.payload.get("max_autonomy_capability_mode"))
            if capability_source_event
            and capability_source_event.payload.get("max_autonomy_capability_mode")
            is not None
            else None
        )
        autonomy_human_confirmation_required = bool(
            capability_source_event.payload.get(
                "autonomy_human_confirmation_required",
                True,
            )
        ) if capability_source_event else True
        autonomy_confirmation_mode = (
            str(capability_source_event.payload.get("autonomy_confirmation_mode"))
            if capability_source_event
            and capability_source_event.payload.get("autonomy_confirmation_mode")
            is not None
            else None
        )
        autonomy_blocked_runtime_actions = (
            [
                str(item)
                for item in capability_source_event.payload.get(
                    "autonomy_blocked_runtime_actions",
                    [],
                )
                if item
            ]
            if capability_source_event
            else []
        )
        capability_decision_tool_class = (
            str(capability_source_event.payload.get("capability_decision_tool_class"))
            if capability_source_event
            and capability_source_event.payload.get("capability_decision_tool_class")
            is not None
            else None
        )
        capability_decision_handoff_mode = (
            str(capability_source_event.payload.get("capability_decision_handoff_mode"))
            if capability_source_event
            and capability_source_event.payload.get("capability_decision_handoff_mode")
            is not None
            else None
        )
        capability_decision_eligible_capabilities = [
            str(item)
            for item in (
                capability_source_event.payload.get(
                    "capability_decision_eligible_capabilities",
                    [],
                )
                if capability_source_event
                else []
            )
        ]
        capability_decision_selected_capabilities = [
            str(item)
            for item in (
                capability_source_event.payload.get(
                    "capability_decision_selected_capabilities",
                    [],
                )
                if capability_source_event
                else []
            )
        ]
        handoff_adapter_status = self._handoff_adapter_status(
            capability_decision_handoff_mode=capability_decision_handoff_mode,
            capability_authorization_status=capability_authorization_status,
            specialist_contract_event=specialist_contract_event,
            specialist_handoff_event=self._first_event(events, "specialist_handoff_governed"),
            specialist_handoff_blocked_event=self._first_event(
                events, "specialist_handoff_blocked"
            ),
        )
        request_identity_source_event = (
            response_event
            if response_event
            and response_event.payload.get("request_identity_status") is not None
            else (
                operation_dispatched_event
                if operation_dispatched_event
                and operation_dispatched_event.payload.get("request_identity_status")
                is not None
                else (
                    plan_governed_event
                    if plan_governed_event
                    and plan_governed_event.payload.get("request_identity_status")
                    is not None
                    else plan_event
                )
            )
        )
        request_identity_status = self._request_identity_status(
            source_event=request_identity_source_event,
        )
        request_identity_mismatch_flags = self._request_identity_mismatch_flags(
            request_identity_source_event=request_identity_source_event,
            governance_event=governance_event,
            operation_dispatched_event=operation_dispatched_event,
            response_event=response_event,
        )
        mind_domain_specialist_status = self._mind_domain_specialist_status(
            context_event=context_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
        )
        mind_domain_specialist_chain_status = self._mind_domain_specialist_chain_status(
            response_event=response_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
            mind_domain_specialist_status=mind_domain_specialist_status,
        )
        cognitive_strategy_shift_status = self._cognitive_strategy_shift_status(
            plan_refined_event=plan_refined_event,
            response_event=response_event,
        )
        mind_domain_specialist_chain = self._mind_domain_specialist_chain(
            response_event=response_event,
            operation_dispatched_event=operation_dispatched_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
            primary_mind=primary_mind,
            primary_domain_driver=primary_domain_driver,
            primary_route=primary_route,
        )
        mind_domain_specialist_mismatch_flags = (
            self._mind_domain_specialist_mismatch_flags(
                workflow_composed_event=workflow_composed_event,
                operation_dispatched_event=operation_dispatched_event,
                response_event=response_event,
                specialist_selection_event=specialist_selection_event,
                specialist_domain_event=specialist_domain_event,
            )
        )
        mind_domain_specialist_effectiveness = (
            self._mind_domain_specialist_effectiveness(
                mind_domain_specialist_status=mind_domain_specialist_status,
                mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
                mind_domain_specialist_mismatch_flags=(
                    mind_domain_specialist_mismatch_flags
                ),
                workflow_composed_event=workflow_composed_event,
                response_event=response_event,
                specialist_selection_event=specialist_selection_event,
                specialist_domain_event=specialist_domain_event,
            )
        )
        specialist_subflow_status = self._specialist_subflow_status(
            specialist_subflow_event=specialist_subflow_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
        )
        mission_runtime_state_status = self._mission_runtime_state_status(
            mission_runtime_event=mission_runtime_event,
            first_event=first_event,
        )
        identity_alignment_status = self._identity_alignment_status(
            directive_event=directive_event,
            plan_governed_event=plan_governed_event,
            response_event=response_event,
        )
        memory_alignment_status = self._memory_alignment_status(
            shared_memory_event=shared_memory_event,
        )
        user_scope_status = self._user_scope_status(
            memory_recovered_event=memory_recovered_event,
            memory_recorded_event=memory_event,
        )
        organization_scope_status = self._organization_scope_status(
            memory_recovered_event=memory_recovered_event,
            memory_recorded_event=memory_event,
        )
        specialist_recurrence_status = self._specialist_recurrence_status(
            shared_memory_event=shared_memory_event,
        )
        memory_corpus_status, memory_retention_pressure = self._memory_corpus_signals(
            shared_memory_event=shared_memory_event,
        )
        memory_maintenance_effectiveness = self._memory_maintenance_effectiveness(
            memory_maintenance_status=memory_maintenance_status,
            memory_review_status=memory_review_status,
            context_compaction_status=context_compaction_status,
            cross_session_recall_status=cross_session_recall_status,
            memory_retention_pressure=memory_retention_pressure,
            workflow_output_status=workflow_output_status,
        )
        specialist_sovereignty_status = self._specialist_sovereignty_status(
            specialist_contract_event=specialist_contract_event,
        )
        capability_effectiveness = self._capability_effectiveness(
            capability_decision_status=capability_decision_status,
            capability_decision_selected_mode=capability_decision_selected_mode,
            capability_authorization_status=capability_authorization_status,
            workflow_output_status=workflow_output_status,
            operation_status=operation_status,
            handoff_adapter_status=handoff_adapter_status,
        )
        adaptive_intervention_effectiveness = self._adaptive_intervention_effectiveness(
            adaptive_intervention_status=adaptive_intervention_status,
            adaptive_intervention_selected_action=adaptive_intervention_selected_action,
            workflow_output_status=workflow_output_status,
            mind_validation_checkpoint_status=mind_validation_checkpoint_status,
            memory_causality_status=memory_causality_status,
            memory_corpus_status=memory_corpus_status,
            workflow_resume_status=workflow_resume_status,
            governance_decision=governance_decision,
            specialist_subflow_status=specialist_subflow_status,
        )
        adaptive_intervention_policy_status = self._adaptive_intervention_policy_status(
            workflow_profile=workflow_profile,
            adaptive_intervention_status=adaptive_intervention_status,
            adaptive_intervention_trigger=adaptive_intervention_trigger,
            adaptive_intervention_selected_action=adaptive_intervention_selected_action,
            mind_disagreement_status=mind_disagreement_status,
            memory_review_status=memory_review_status,
            memory_corpus_status=memory_corpus_status,
            memory_retention_pressure=memory_retention_pressure,
            workflow_resume_status=workflow_resume_status,
            continuity_action=continuity_action,
        )
        mission_policy_status = self._mission_policy_status(
            request_identity_status=request_identity_status,
            request_identity_mismatch_flags=request_identity_mismatch_flags,
            request_identity_source_event=request_identity_source_event,
            governance_event=governance_event,
        )
        expanded_eval_state = derive_expanded_eval_state(
            capability_decision_status=capability_decision_status,
            capability_effectiveness=capability_effectiveness,
            handoff_adapter_status=handoff_adapter_status,
            request_identity_status=request_identity_status,
            mission_policy_status=mission_policy_status,
            continuity_trace_status=continuity_trace_status,
            workflow_checkpoint_status=workflow_checkpoint_status,
            workflow_resume_status=workflow_resume_status,
            specialist_subflow_status=specialist_subflow_status,
            mission_runtime_state_status=mission_runtime_state_status,
        )
        ecosystem_state_source_event = self._first_payload_event(
            events,
            "ecosystem_state_status",
        )
        operational_ecosystem_state_status = (
            str(ecosystem_state_source_event.payload.get("ecosystem_state_status"))
            if ecosystem_state_source_event is not None
            and ecosystem_state_source_event.payload.get("ecosystem_state_status") is not None
            else "not_applicable"
        )
        active_work_items = self._dedupe_payload_list(events, "active_work_items")
        active_artifact_refs = self._dedupe_payload_list(events, "active_artifact_refs")
        open_checkpoint_refs = self._dedupe_payload_list(events, "open_checkpoint_refs")
        surface_presence = self._dedupe_payload_list(events, "surface_presence")
        surface_continuity_event = self._first_payload_event(
            events,
            "surface_continuity_status",
        )
        surface_continuity_status = (
            str(surface_continuity_event.payload.get("surface_continuity_status"))
            if surface_continuity_event is not None
            and surface_continuity_event.payload.get("surface_continuity_status")
            is not None
            else "not_applicable"
        )
        linked_surface_ids = self._dedupe_payload_list(events, "linked_surface_ids")
        surface_identity_conflict_flags = self._dedupe_payload_list(
            events,
            "surface_identity_conflict_flags",
        )
        linked_surface_count = len(linked_surface_ids)
        multi_surface_readiness = self._multi_surface_readiness(
            surface_continuity_status=surface_continuity_status,
            linked_surface_count=linked_surface_count,
            surface_identity_conflict_flags=surface_identity_conflict_flags,
        )
        objective_status_event = self._first_payload_event(events, "objective_status")
        objective_continuity_status = (
            str(objective_status_event.payload.get("objective_status"))
            if objective_status_event is not None
            and objective_status_event.payload.get("objective_status") is not None
            else "not_applicable"
        )
        objective_work_items = self._dedupe_payload_list(events, "work_item_refs")
        objective_checkpoints = self._dedupe_payload_list(events, "checkpoint_refs")
        objective_artifacts = self._dedupe_payload_list(events, "artifact_refs")
        if not objective_work_items:
            objective_work_items = active_work_items
        if not objective_checkpoints:
            objective_checkpoints = open_checkpoint_refs
        if not objective_artifacts:
            objective_artifacts = active_artifact_refs
        next_action_event = self._first_payload_event(events, "next_action_ref")
        next_action_status = (
            "ready"
            if next_action_event is not None
            and next_action_event.payload.get("next_action_ref")
            else "not_applicable"
        )
        artifact_continuity_status = (
            "attached" if objective_artifacts else "not_applicable"
        )
        objective_consulted = any(
            event.event_name == "objective_state_inspected"
            or event.payload.get("objective_consulted") is True
            for event in events
        )
        objective_transition_counts = self._objective_transition_counts(events)
        objective_missing_next_action = (
            objective_continuity_status
            in {"active", "paused", "blocked", "requires_operator_decision"}
            and next_action_status != "ready"
        )
        objective_missing_artifact = (
            objective_continuity_status
            in {"active", "paused", "blocked", "requires_operator_decision", "completed"}
            and artifact_continuity_status != "attached"
        )
        objective_utility_signals = self._objective_utility_signals(
            objective_consulted=objective_consulted,
            transition_counts=objective_transition_counts,
            missing_next_action=objective_missing_next_action,
            missing_artifact=objective_missing_artifact,
        )
        early_experience_reflection_event = self._first_payload_event(
            events,
            "experience_reflection_status",
        )
        early_reviewed_learning_event = self._first_payload_event(
            events,
            "reviewed_learning_influence_status",
        )
        operator_usefulness_signals = self._operator_usefulness_signals(
            objective_consulted=objective_consulted,
            active_work_item_count=len(objective_work_items),
            artifact_attached=artifact_continuity_status == "attached",
            next_action_ready=next_action_status == "ready",
            memory_causality_status=memory_causality_status,
            experience_reflection_status=self._payload_str(
                early_experience_reflection_event,
                "experience_reflection_status",
                "not_applicable",
            ),
            reviewed_learning_assisted_eval_status=(
                self._reviewed_learning_assisted_eval_status(
                    status=self._payload_str(
                        early_reviewed_learning_event,
                        "reviewed_learning_influence_status",
                        "not_applicable",
                    ),
                    refs=self._dedupe_payload_list(
                        events,
                        "reviewed_learning_influence_refs",
                    ),
                )
            ),
            missing_next_action=objective_missing_next_action,
            missing_artifact=objective_missing_artifact,
        )
        operator_usefulness_score = self._operator_usefulness_score(
            operator_usefulness_signals
        )
        operator_usefulness_status = self._operator_usefulness_status(
            score=operator_usefulness_score,
            missing_next_action=objective_missing_next_action,
            missing_artifact=objective_missing_artifact,
        )
        technology_absorption_event = self._first_payload_event(
            events,
            "technology_absorption_readiness",
        )
        technology_absorption_readiness = self._payload_str(
            technology_absorption_event,
            "technology_absorption_readiness",
            "not_applicable",
        )
        technology_absorption_decision = self._payload_str(
            technology_absorption_event,
            "technology_absorption_decision",
            "not_applicable",
        )
        technology_absorption_lane_status = self._payload_str(
            technology_absorption_event,
            "technology_absorption_lane_status",
            "not_applicable",
        )
        technology_absorption_promotion_readiness = self._payload_str(
            technology_absorption_event,
            "technology_absorption_promotion_readiness",
            "not_applicable",
        )
        technology_absorption_blockers = self._dedupe_payload_list(
            events,
            "technology_absorption_blockers",
        )
        technology_absorption_candidate_refs = self._dedupe_payload_list(
            events,
            "technology_absorption_candidate_refs",
        )
        technology_absorption_signals = self._technology_absorption_signals(
            readiness=technology_absorption_readiness,
            decision=technology_absorption_decision,
            blockers=technology_absorption_blockers,
            candidate_refs=technology_absorption_candidate_refs,
        )
        experience_reflection_event = self._first_payload_event(
            events,
            "experience_reflection_status",
        )
        experience_reflection_status = self._payload_str(
            experience_reflection_event,
            "experience_reflection_status",
            "not_applicable",
        )
        experience_reflection_change_type = self._payload_str(
            experience_reflection_event,
            "experience_reflection_change_type",
            "not_applicable",
        )
        experience_reflection_blockers = self._dedupe_payload_list(
            events,
            "experience_reflection_blockers",
        )
        experience_reflection_refs = self._dedupe_payload_list(
            events,
            "experience_reflection_refs",
        )
        experience_reflection_signals = self._experience_reflection_signals(
            status=experience_reflection_status,
            change_type=experience_reflection_change_type,
            blockers=experience_reflection_blockers,
            refs=experience_reflection_refs,
        )
        operator_feedback_event = self._first_payload_event(
            events,
            "operator_feedback_status",
        )
        operator_feedback_status = self._payload_str(
            operator_feedback_event,
            "operator_feedback_status",
            "not_applicable",
        )
        operator_feedback_id = self._payload_optional_str(
            operator_feedback_event,
            "operator_feedback_id",
        )
        operator_feedback_experience_id = self._payload_optional_str(
            operator_feedback_event,
            "operator_feedback_experience_id",
        )
        operator_feedback_assessment = self._payload_str(
            operator_feedback_event,
            "operator_feedback_assessment",
            "not_applicable",
        )
        operator_feedback_rating = self._payload_optional_int(
            operator_feedback_event,
            "operator_feedback_rating",
        )
        operator_feedback_evidence_refs = self._dedupe_payload_list(
            events,
            "operator_feedback_evidence_refs",
        )
        operator_feedback_evolution_review_status = self._payload_str(
            operator_feedback_event,
            "operator_feedback_evolution_review_status",
            "not_applicable",
        )
        operator_feedback_human_review_required = self._payload_bool(
            operator_feedback_event,
            "operator_feedback_human_review_required",
            True,
        )
        operator_feedback_automatic_promotion_allowed = self._payload_bool(
            operator_feedback_event,
            "operator_feedback_automatic_promotion_allowed",
            False,
        )
        operator_feedback_core_mutation_allowed = self._payload_bool(
            operator_feedback_event,
            "operator_feedback_core_mutation_allowed",
            False,
        )
        reflection_influence_event = self._first_payload_event(
            events,
            "reflection_influence_status",
        )
        reflection_influence_status = self._payload_str(
            reflection_influence_event,
            "reflection_influence_status",
            "not_applicable",
        )
        reflection_influence_refs = self._dedupe_payload_list(
            events,
            "reflection_influence_refs",
        )
        reflection_influence_summary = self._payload_str(
            reflection_influence_event,
            "reflection_influence_summary",
            None,
        )
        reflection_assisted_eval_status = self._reflection_assisted_eval_status(
            status=reflection_influence_status,
            refs=reflection_influence_refs,
        )
        reviewed_learning_influence_event = self._first_payload_event(
            events,
            "reviewed_learning_influence_status",
        )
        reviewed_learning_influence_status = self._payload_str(
            reviewed_learning_influence_event,
            "reviewed_learning_influence_status",
            "not_applicable",
        )
        reviewed_learning_influence_refs = self._dedupe_payload_list(
            events,
            "reviewed_learning_influence_refs",
        )
        reviewed_learning_influence_summary = self._payload_str(
            reviewed_learning_influence_event,
            "reviewed_learning_influence_summary",
            None,
        )
        reviewed_learning_influence_reason = self._payload_str(
            reviewed_learning_influence_event,
            "reviewed_learning_influence_reason",
            None,
        )
        reviewed_learning_assisted_eval_status = (
            self._reviewed_learning_assisted_eval_status(
                status=reviewed_learning_influence_status,
                refs=reviewed_learning_influence_refs,
            )
        )
        evolution_review_event = self._first_payload_event(
            events,
            "evolution_review_decision_status",
        )
        evolution_review_decision_status = self._payload_str(
            evolution_review_event,
            "evolution_review_decision_status",
            "not_applicable",
        )
        evolution_review_decision = self._payload_str(
            evolution_review_event,
            "evolution_review_decision",
            "not_applicable",
        )
        evolution_review_proposal_id = self._payload_optional_str(
            evolution_review_event,
            "evolution_proposal_id",
        )
        evolution_review_operator_ref = self._payload_optional_str(
            evolution_review_event,
            "operator_ref",
        )
        evolution_review_evidence_refs = self._dedupe_payload_list(
            events,
            "evolution_review_evidence_refs",
        )
        evolution_review_rollback_plan_ref = self._payload_optional_str(
            evolution_review_event,
            "rollback_plan_ref",
        )
        evolution_review_limits = self._evolution_review_limits(
            event=evolution_review_event,
            existing_limits=self._dedupe_payload_list(
                events,
                "evolution_review_limits",
            ),
        )
        promotion_gate_event = self._first_payload_event(
            events,
            "promotion_gate_status",
        )
        promotion_gate_status = self._payload_str(
            promotion_gate_event,
            "promotion_gate_status",
            "not_applicable",
        )
        promotion_gate_decision = self._payload_str(
            promotion_gate_event,
            "promotion_gate_decision",
            "not_applicable",
        )
        promotion_gate_id = self._payload_optional_str(
            promotion_gate_event,
            "promotion_gate_id",
        )
        promotion_gate_checklist_id = self._payload_optional_str(
            promotion_gate_event,
            "promotion_gate_checklist_id",
        )
        promotion_gate_release_scope = self._payload_optional_str(
            promotion_gate_event,
            "promotion_gate_release_scope",
        )
        promotion_gate_release_conclusion = self._payload_str(
            promotion_gate_event,
            "promotion_gate_release_conclusion",
            "no_promotion_gate_evidence",
        )
        promotion_gate_required_gates = self._dedupe_payload_list(
            events,
            "promotion_gate_required_gates",
        )
        promotion_gate_completed_gates = self._dedupe_payload_list(
            events,
            "promotion_gate_completed_gates",
        )
        promotion_gate_missing_gates = self._dedupe_payload_list(
            events,
            "promotion_gate_missing_gates",
        )
        promotion_gate_evidence_refs = self._dedupe_payload_list(
            events,
            "promotion_gate_evidence_refs",
        )
        promotion_gate_blockers = self._dedupe_payload_list(
            events,
            "promotion_gate_blockers",
        )
        promotion_gate_human_review_status = self._payload_str(
            promotion_gate_event,
            "promotion_gate_human_review_status",
            "not_applicable",
        )
        promotion_gate_promotion_eligible = self._payload_bool(
            promotion_gate_event,
            "promotion_gate_promotion_eligible",
            False,
        )
        promotion_gate_human_decision_required = self._payload_bool(
            promotion_gate_event,
            "promotion_gate_human_decision_required",
            True,
        )
        promotion_gate_promotion_authorized = self._payload_bool(
            promotion_gate_event,
            "promotion_gate_promotion_authorized",
            False,
        )
        mission_progress_event = self._first_payload_event(
            events,
            "mission_progress_report_status",
        )
        mission_progress_report_status = self._payload_str(
            mission_progress_event,
            "mission_progress_report_status",
            "not_applicable",
        )
        mission_progress_report_id = self._payload_optional_str(
            mission_progress_event,
            "mission_progress_report_id",
        )
        mission_progress_summary = self._payload_optional_str(
            mission_progress_event,
            "mission_progress_summary",
        )
        mission_progress_next_action_ref = self._payload_optional_str(
            mission_progress_event,
            "mission_progress_next_action_ref",
        )
        mission_progress_pending_decisions = self._dedupe_payload_list(
            events,
            "mission_progress_pending_decisions",
        )
        mission_progress_evidence_refs = self._dedupe_payload_list(
            events,
            "mission_progress_evidence_refs",
        )
        mission_progress_memory_influence_refs = self._dedupe_payload_list(
            events,
            "mission_progress_memory_influence_refs",
        )
        mission_progress_learning_refs = self._dedupe_payload_list(
            events,
            "mission_progress_learning_refs",
        )
        mission_progress_risk_refs = self._dedupe_payload_list(
            events,
            "mission_progress_risk_refs",
        )
        procedural_artifact_status_for_audit = (
            str(response_event.payload.get("procedural_artifact_status"))
            if response_event
            and response_event.payload.get("procedural_artifact_status") is not None
            else (
                str(plan_event.payload.get("procedural_artifact_status"))
                if plan_event
                and plan_event.payload.get("procedural_artifact_status") is not None
                else (
                    str(memory_event.payload.get("procedural_artifact_status"))
                    if memory_event
                    and memory_event.payload.get("procedural_artifact_status") is not None
                    else "not_applicable"
                )
            )
        )
        procedural_artifact_refs_for_audit = (
            [
                str(item)
                for item in response_event.payload.get("procedural_artifact_refs", [])
                if item
            ]
            if response_event is not None
            and response_event.payload.get("procedural_artifact_refs")
            else (
                [
                    str(item)
                    for item in plan_event.payload.get("procedural_artifact_refs", [])
                    if item
                ]
                if plan_event is not None
                and plan_event.payload.get("procedural_artifact_refs")
                else (
                    [
                        str(item)
                        for item in memory_event.payload.get(
                            "procedural_artifact_refs",
                            [],
                        )
                        if item
                    ]
                    if memory_event is not None
                    and memory_event.payload.get("procedural_artifact_refs")
                    else []
                )
            )
        )
        procedural_artifact_version_for_audit = (
            int(response_event.payload.get("procedural_artifact_version"))
            if response_event is not None
            and response_event.payload.get("procedural_artifact_version") is not None
            else (
                int(plan_event.payload.get("procedural_artifact_version"))
                if plan_event is not None
                and plan_event.payload.get("procedural_artifact_version") is not None
                else (
                    int(memory_event.payload.get("procedural_artifact_version"))
                    if memory_event is not None
                    and memory_event.payload.get("procedural_artifact_version")
                    is not None
                    else None
                )
            )
        )
        memory_influence_used_refs = list(semantic_memory_anchor_refs)
        memory_influence_ignored_refs: list[str] = []
        memory_influence_reasons: list[str] = []
        memory_influence_evidence_refs = list(semantic_memory_evidence_refs)
        if semantic_memory_use_reason:
            if not memory_influence_used_refs and semantic_memory_source:
                memory_influence_used_refs.append(
                    f"memory://semantic-source/{semantic_memory_source}"
                )
            memory_influence_reasons.append(
                f"semantic_used:{semantic_memory_use_reason}"
            )
        elif semantic_memory_non_use_reason:
            memory_influence_ignored_refs.append("memory://semantic")
            memory_influence_reasons.append(
                f"semantic_ignored:{semantic_memory_non_use_reason}"
            )
        if procedural_artifact_refs_for_audit:
            memory_influence_used_refs.extend(procedural_artifact_refs_for_audit)
            memory_influence_evidence_refs.extend(procedural_artifact_refs_for_audit)
            memory_influence_reasons.append(
                "procedural_artifact_used:"
                f"{procedural_artifact_status_for_audit or 'unknown'}"
            )
        elif procedural_memory_source:
            memory_influence_used_refs.append(
                f"memory://procedural-source/{procedural_memory_source}"
            )
            memory_influence_reasons.append(
                "procedural_used:source_available_without_artifact_ref"
            )
        else:
            memory_influence_ignored_refs.append("memory://procedural")
            memory_influence_reasons.append(
                "procedural_ignored:no_procedural_artifact_or_source"
            )
        memory_influence_used_refs = list(dict.fromkeys(memory_influence_used_refs))
        memory_influence_ignored_refs = list(
            dict.fromkeys(memory_influence_ignored_refs)
        )
        memory_influence_reasons = list(dict.fromkeys(memory_influence_reasons))
        memory_influence_evidence_refs = list(
            dict.fromkeys(memory_influence_evidence_refs)
        )

        return FlowAudit(
            request_id=first_event.request_id,
            session_id=first_event.session_id,
            mission_id=first_event.mission_id,
            total_events=len(events),
            workflow_domain_route=workflow_domain_route,
            workflow_profile=workflow_profile,
            workflow_governance_mode=workflow_governance_mode,
            workflow_trace_status=workflow_trace_status,
            workflow_checkpoint_status=workflow_checkpoint_status,
            workflow_resume_status=workflow_resume_status,
            workflow_resume_point=workflow_resume_point,
            workflow_pending_checkpoint_count=workflow_pending_checkpoint_count,
            workflow_profile_status=workflow_profile_status,
            contract_validation_status=contract_validation_status,
            contract_validation_errors=contract_validation_errors,
            contract_validation_retry_applied=contract_validation_retry_applied,
            output_validation_status=output_validation_status,
            output_validation_errors=output_validation_errors,
            output_validation_retry_applied=output_validation_retry_applied,
            workflow_output_status=workflow_output_status,
            workflow_output_errors=workflow_output_errors,
            memory_causality_status=memory_causality_status,
            primary_mind=primary_mind,
            primary_route=primary_route,
            dominant_tension=dominant_tension,
            arbitration_source=arbitration_source,
            primary_domain_driver=primary_domain_driver,
            metacognitive_guidance_status=metacognitive_guidance_status,
            metacognitive_guidance_summary=metacognitive_guidance_summary,
            metacognitive_effects=metacognitive_effects,
            metacognitive_containment_recommendation=(
                metacognitive_containment_recommendation
            ),
            mind_disagreement_status=mind_disagreement_status,
            mind_validation_checkpoint_status=mind_validation_checkpoint_status,
            capability_decision_status=capability_decision_status,
            capability_decision_objective=capability_decision_objective,
            capability_decision_reason=capability_decision_reason,
            capability_decision_selected_mode=capability_decision_selected_mode,
            capability_authorization_status=capability_authorization_status,
            capability_decision_tool_class=capability_decision_tool_class,
            capability_decision_handoff_mode=capability_decision_handoff_mode,
            capability_decision_eligible_capabilities=(
                capability_decision_eligible_capabilities
            ),
            capability_decision_selected_capabilities=(
                capability_decision_selected_capabilities
            ),
            effective_autonomy_level=effective_autonomy_level,
            autonomy_ladder_status=autonomy_ladder_status,
            max_autonomy_capability_mode=max_autonomy_capability_mode,
            autonomy_human_confirmation_required=autonomy_human_confirmation_required,
            autonomy_confirmation_mode=autonomy_confirmation_mode,
            autonomy_blocked_runtime_actions=autonomy_blocked_runtime_actions,
            capability_effectiveness=capability_effectiveness,
            handoff_adapter_status=handoff_adapter_status,
            request_identity_status=request_identity_status,
            mission_policy_status=mission_policy_status,
            request_identity_mismatch_flags=request_identity_mismatch_flags,
            expanded_eval_status=expanded_eval_state["expanded_eval_status"],
            surface_axis_status=expanded_eval_state["surface_axis_status"],
            ecosystem_state_status=expanded_eval_state["ecosystem_state_status"],
            operational_ecosystem_state_status=operational_ecosystem_state_status,
            active_work_items=active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=surface_presence,
            surface_continuity_status=surface_continuity_status,
            linked_surface_count=linked_surface_count,
            surface_identity_conflict_flags=surface_identity_conflict_flags,
            multi_surface_readiness=multi_surface_readiness,
            objective_continuity_status=objective_continuity_status,
            active_work_item_count=len(objective_work_items),
            open_checkpoint_count=len(objective_checkpoints),
            artifact_continuity_status=artifact_continuity_status,
            next_action_status=next_action_status,
            objective_consulted=objective_consulted,
            objective_transition_counts=objective_transition_counts,
            objective_utility_signals=objective_utility_signals,
            objective_missing_next_action=objective_missing_next_action,
            objective_missing_artifact=objective_missing_artifact,
            operator_usefulness_status=operator_usefulness_status,
            operator_usefulness_score=operator_usefulness_score,
            operator_usefulness_signals=operator_usefulness_signals,
            technology_absorption_readiness=technology_absorption_readiness,
            technology_absorption_decision=technology_absorption_decision,
            technology_absorption_lane_status=technology_absorption_lane_status,
            technology_absorption_promotion_readiness=(
                technology_absorption_promotion_readiness
            ),
            technology_absorption_blockers=technology_absorption_blockers,
            technology_absorption_candidate_refs=technology_absorption_candidate_refs,
            technology_absorption_signals=technology_absorption_signals,
            experience_reflection_status=experience_reflection_status,
            experience_reflection_change_type=experience_reflection_change_type,
            experience_reflection_blockers=experience_reflection_blockers,
            experience_reflection_refs=experience_reflection_refs,
            experience_reflection_signals=experience_reflection_signals,
            operator_feedback_status=operator_feedback_status,
            operator_feedback_id=operator_feedback_id,
            operator_feedback_experience_id=operator_feedback_experience_id,
            operator_feedback_assessment=operator_feedback_assessment,
            operator_feedback_rating=operator_feedback_rating,
            operator_feedback_evidence_refs=operator_feedback_evidence_refs,
            operator_feedback_evolution_review_status=(
                operator_feedback_evolution_review_status
            ),
            operator_feedback_human_review_required=(
                operator_feedback_human_review_required
            ),
            operator_feedback_automatic_promotion_allowed=(
                operator_feedback_automatic_promotion_allowed
            ),
            operator_feedback_core_mutation_allowed=(
                operator_feedback_core_mutation_allowed
            ),
            reflection_influence_status=reflection_influence_status,
            reflection_influence_refs=reflection_influence_refs,
            reflection_influence_summary=reflection_influence_summary,
            reflection_assisted_eval_status=reflection_assisted_eval_status,
            reviewed_learning_influence_status=reviewed_learning_influence_status,
            reviewed_learning_influence_refs=reviewed_learning_influence_refs,
            reviewed_learning_influence_summary=reviewed_learning_influence_summary,
            reviewed_learning_influence_reason=reviewed_learning_influence_reason,
            reviewed_learning_assisted_eval_status=(
                reviewed_learning_assisted_eval_status
            ),
            reviewed_learning_release_conclusion=(
                "no_promotion_without_release_gate"
            ),
            evolution_review_decision_status=evolution_review_decision_status,
            evolution_review_decision=evolution_review_decision,
            evolution_review_proposal_id=evolution_review_proposal_id,
            evolution_review_operator_ref=evolution_review_operator_ref,
            evolution_review_evidence_refs=evolution_review_evidence_refs,
            evolution_review_rollback_plan_ref=evolution_review_rollback_plan_ref,
            evolution_review_limits=evolution_review_limits,
            promotion_gate_status=promotion_gate_status,
            promotion_gate_decision=promotion_gate_decision,
            promotion_gate_id=promotion_gate_id,
            promotion_gate_checklist_id=promotion_gate_checklist_id,
            promotion_gate_release_scope=promotion_gate_release_scope,
            promotion_gate_release_conclusion=promotion_gate_release_conclusion,
            promotion_gate_required_gates=promotion_gate_required_gates,
            promotion_gate_completed_gates=promotion_gate_completed_gates,
            promotion_gate_missing_gates=promotion_gate_missing_gates,
            promotion_gate_evidence_refs=promotion_gate_evidence_refs,
            promotion_gate_blockers=promotion_gate_blockers,
            promotion_gate_human_review_status=(
                promotion_gate_human_review_status
            ),
            promotion_gate_promotion_eligible=(
                promotion_gate_promotion_eligible
            ),
            promotion_gate_human_decision_required=(
                promotion_gate_human_decision_required
            ),
            promotion_gate_promotion_authorized=(
                promotion_gate_promotion_authorized
            ),
            mission_progress_report_status=mission_progress_report_status,
            mission_progress_report_id=mission_progress_report_id,
            mission_progress_summary=mission_progress_summary,
            mission_progress_next_action_ref=(
                mission_progress_next_action_ref
            ),
            mission_progress_pending_decisions=(
                mission_progress_pending_decisions
            ),
            mission_progress_evidence_refs=mission_progress_evidence_refs,
            mission_progress_memory_influence_refs=(
                mission_progress_memory_influence_refs
            ),
            mission_progress_learning_refs=mission_progress_learning_refs,
            mission_progress_risk_refs=mission_progress_risk_refs,
            experiment_lane_status=expanded_eval_state["experiment_lane_status"],
            wave2_candidate_class=expanded_eval_state["wave2_candidate_class"],
            experiment_entry_status=expanded_eval_state["experiment_entry_status"],
            experiment_exit_status=expanded_eval_state["experiment_exit_status"],
            promotion_readiness=expanded_eval_state["promotion_readiness"],
            mind_domain_specialist_status=mind_domain_specialist_status,
            mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
            mind_domain_specialist_chain=mind_domain_specialist_chain,
            mind_domain_specialist_effectiveness=(
                mind_domain_specialist_effectiveness
            ),
            mind_domain_specialist_mismatch_flags=(
                mind_domain_specialist_mismatch_flags
            ),
            cognitive_recomposition_applied=cognitive_recomposition_applied,
            cognitive_recomposition_reason=cognitive_recomposition_reason,
            cognitive_recomposition_trigger=cognitive_recomposition_trigger,
            adaptive_intervention_status=adaptive_intervention_status,
            adaptive_intervention_reason=adaptive_intervention_reason,
            adaptive_intervention_trigger=adaptive_intervention_trigger,
            adaptive_intervention_selected_action=adaptive_intervention_selected_action,
            adaptive_intervention_expected_effect=adaptive_intervention_expected_effect,
            adaptive_intervention_effects=adaptive_intervention_effects,
            adaptive_intervention_effectiveness=adaptive_intervention_effectiveness,
            adaptive_intervention_policy_status=adaptive_intervention_policy_status,
            cognitive_strategy_shift_status=cognitive_strategy_shift_status,
            cognitive_strategy_shift_applied=cognitive_strategy_shift_applied,
            cognitive_strategy_shift_summary=cognitive_strategy_shift_summary,
            cognitive_strategy_shift_trigger=cognitive_strategy_shift_trigger,
            cognitive_strategy_shift_effects=cognitive_strategy_shift_effects,
            semantic_memory_source=semantic_memory_source,
            procedural_memory_source=procedural_memory_source,
            semantic_memory_focus=semantic_memory_focus,
            semantic_memory_anchor_refs=semantic_memory_anchor_refs,
            semantic_memory_evidence_refs=semantic_memory_evidence_refs,
            semantic_memory_use_reason=semantic_memory_use_reason,
            semantic_memory_non_use_reason=semantic_memory_non_use_reason,
            memory_influence_used_refs=memory_influence_used_refs,
            memory_influence_ignored_refs=memory_influence_ignored_refs,
            memory_influence_reasons=memory_influence_reasons,
            memory_influence_evidence_refs=memory_influence_evidence_refs,
            procedural_memory_hint=procedural_memory_hint,
            semantic_memory_effects=semantic_memory_effects,
            procedural_memory_effects=procedural_memory_effects,
            semantic_memory_lifecycle=semantic_memory_lifecycle,
            procedural_memory_lifecycle=procedural_memory_lifecycle,
            memory_lifecycle_status=memory_lifecycle_status,
            memory_review_status=memory_review_status,
            memory_maintenance_status=memory_maintenance_status,
            memory_maintenance_reason=memory_maintenance_reason,
            memory_maintenance_fallback_mode=memory_maintenance_fallback_mode,
            context_compaction_status=context_compaction_status,
            cross_session_recall_status=cross_session_recall_status,
            memory_consolidation_status=memory_consolidation_status,
            memory_fixation_status=memory_fixation_status,
            memory_archive_status=memory_archive_status,
            procedural_artifact_status=procedural_artifact_status_for_audit,
            procedural_artifact_refs=procedural_artifact_refs_for_audit,
            procedural_artifact_version=procedural_artifact_version_for_audit,
            memory_corpus_status=memory_corpus_status,
            memory_retention_pressure=memory_retention_pressure,
            memory_maintenance_effectiveness=memory_maintenance_effectiveness,
            semantic_memory_specialists=semantic_memory_specialists,
            procedural_memory_specialists=procedural_memory_specialists,
            event_names=event_names,
            missing_required_events=missing_required_events,
            anomaly_flags=anomaly_flags,
            continuity_action=continuity_action,
            continuity_source=continuity_source,
            continuity_target_mission_id=continuity_target_mission_id,
            continuity_target_goal=continuity_target_goal,
            continuity_runtime_mode=continuity_runtime_mode,
            specialist_subflow_status=specialist_subflow_status,
            specialist_subflow_runtime_mode=specialist_subflow_runtime_mode,
            mission_runtime_state_status=mission_runtime_state_status,
            registry_domains=registry_domains,
            domain_specialists=domain_specialists,
            shadow_specialists=shadow_specialists,
            domain_alignment_status=domain_alignment_status,
            mind_alignment_status=mind_alignment_status,
            identity_alignment_status=identity_alignment_status,
            memory_alignment_status=memory_alignment_status,
            user_scope_status=user_scope_status,
            organization_scope_status=organization_scope_status,
            specialist_recurrence_status=specialist_recurrence_status,
            specialist_sovereignty_status=specialist_sovereignty_status,
            missing_continuity_signals=missing_continuity_signals,
            continuity_anomaly_flags=continuity_anomaly_flags,
            continuity_trace_status=continuity_trace_status,
            governance_decision=governance_decision,
            operation_status=operation_status,
            duration_seconds=metrics.duration_seconds,
            source_services=sorted({event.source_service for event in events}),
        )

    def build_incident_evidence(
        self,
        query: ObservabilityQuery,
        *,
        required_events: tuple[str, ...] = DEFAULT_REQUIRED_FLOW_EVENTS,
    ) -> IncidentEvidence:
        """Build compact operator-facing evidence for anomalous request flows."""

        audit = self.audit_flow(query, required_events=required_events)
        recommended_operator_action = self._recommended_operator_action(audit)
        flow_summary = (
            f"decision={audit.governance_decision or 'unknown'}; "
            f"events={audit.total_events}; duration_seconds={audit.duration_seconds}; "
            f"operation_status={audit.operation_status or 'none'}; "
            f"continuity_action={audit.continuity_action or 'none'}; "
            f"continuity_status={audit.continuity_trace_status}"
        )
        return IncidentEvidence(
            request_id=audit.request_id,
            session_id=audit.session_id,
            mission_id=audit.mission_id,
            governance_decision=audit.governance_decision,
            operation_status=audit.operation_status,
            flow_summary=flow_summary,
            anomaly_flags=list(audit.anomaly_flags),
            missing_required_events=list(audit.missing_required_events),
            recommended_operator_action=recommended_operator_action,
            source_services=list(audit.source_services),
        )

    def summarize_recent_requests(
        self,
        *,
        limit: int = 10,
        required_events: tuple[str, ...] = DEFAULT_REQUIRED_FLOW_EVENTS,
    ) -> list[FlowAudit]:
        """Return audited recent request traces for pilot and rollout review."""

        request_ids = self._recent_request_ids(limit)
        return [
            self.audit_flow(
                ObservabilityQuery(request_id=request_id, limit=100),
                required_events=required_events,
            )
            for request_id in request_ids
        ]

    def _recent_request_ids(self, limit: int) -> list[str]:
        events = self.list_recent_events(ObservabilityQuery(limit=max(limit * 20, 20)))
        request_ids: list[str] = []
        for event in reversed(events):
            if event.request_id and event.request_id not in request_ids:
                request_ids.append(event.request_id)
        return list(reversed(request_ids[-limit:]))

    @staticmethod
    def _recommended_operator_action(audit: FlowAudit) -> str:
        if "no_events_found" in audit.anomaly_flags:
            return "pause_controlled_usage_and_investigate_missing_trace"
        if audit.contract_validation_status == "invalid":
            return "rebuild_plan_contract_before_resuming_flow"
        if audit.output_validation_status == "invalid":
            return "contain_response_and_recompose_with_last_valid_plan"
        if audit.governance_decision in {"block", "defer_for_validation"}:
            return "keep_contained_and_require_manual_review"
        if audit.capability_decision_status == "attention_required":
            return "review_capability_decision_contract_before_promoting_the_flow"
        if audit.handoff_adapter_status == "attention_required":
            return "review_specialist_handoff_adapter_before_promoting_the_flow"
        if audit.capability_effectiveness == "insufficient":
            return "review_capability_mode_authorization_and_execution_before_promoting_the_flow"
        if audit.adaptive_intervention_policy_status == "attention_required":
            return "review_workflow_adaptive_intervention_policy_before_promoting_the_flow"
        if audit.adaptive_intervention_effectiveness == "insufficient":
            return "review_adaptive_intervention_before_promoting_the_flow"
        if audit.mind_validation_checkpoint_status == "attention_required":
            return "review_mind_validation_checkpoint_before_promoting_the_flow"
        if audit.memory_corpus_status == "review_recommended":
            return "review_memory_corpus_pressure_before_expanding_guided_memory_usage"
        if audit.anomaly_flags or audit.missing_required_events:
            return "contain_request_and_revert_to_last_validated_baseline"
        if audit.continuity_anomaly_flags or audit.missing_continuity_signals:
            return "review_continuity_trace_and_replay_with_last_consistent_context"
        return "no_immediate_incident_action_required"

    @staticmethod
    def _first_event(
        events: list[InternalEventEnvelope],
        event_name: str,
    ) -> InternalEventEnvelope | None:
        for event in events:
            if event.event_name == event_name:
                return event
        return None

    @staticmethod
    def _first_payload_event(
        events: list[InternalEventEnvelope],
        field_name: str,
    ) -> InternalEventEnvelope | None:
        for event in events:
            if event.payload.get(field_name) not in {None, ""}:
                return event
        return None

    @staticmethod
    def _payload_str(
        event: InternalEventEnvelope | None,
        field_name: str,
        default: str,
    ) -> str:
        if event is None or event.payload.get(field_name) in {None, ""}:
            return default
        return str(event.payload[field_name])

    @staticmethod
    def _payload_optional_str(
        event: InternalEventEnvelope | None,
        field_name: str,
    ) -> str | None:
        if event is None or event.payload.get(field_name) in {None, ""}:
            return None
        return str(event.payload[field_name])

    @staticmethod
    def _payload_optional_int(
        event: InternalEventEnvelope | None,
        field_name: str,
    ) -> int | None:
        if event is None:
            return None
        value = event.payload.get(field_name)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @staticmethod
    def _payload_bool(
        event: InternalEventEnvelope | None,
        field_name: str,
        default: bool,
    ) -> bool:
        if event is None:
            return default
        value = event.payload.get(field_name)
        return value if isinstance(value, bool) else default

    @staticmethod
    def _dedupe_payload_list(
        events: list[InternalEventEnvelope],
        field_name: str,
    ) -> list[str]:
        values: list[str] = []
        for event in events:
            payload_value = event.payload.get(field_name, [])
            if not isinstance(payload_value, list):
                continue
            for item in payload_value:
                text = str(item).strip()
                if text and text not in values:
                    values.append(text)
        return values

    @staticmethod
    def _evolution_review_limits(
        *,
        event: InternalEventEnvelope | None,
        existing_limits: list[str],
    ) -> list[str]:
        limits = list(existing_limits)
        if event is None:
            return limits
        if event.payload.get("automatic_promotion_allowed") is False:
            limits.append("automatic_promotion_blocked")
        if event.payload.get("core_mutation_allowed") is False:
            limits.append("core_mutation_blocked")
        return list(dict.fromkeys(limits))

    @staticmethod
    def _objective_transition_counts(
        events: list[InternalEventEnvelope],
    ) -> dict[str, int]:
        counts = {
            "resume": 0,
            "pause": 0,
            "block": 0,
            "complete": 0,
            "redefine-next-action": 0,
        }
        for event in events:
            if event.event_name not in {"mission_updated", "governance_blocked"}:
                continue
            transition = event.payload.get("transition")
            if isinstance(transition, str) and transition in counts:
                counts[transition] += 1
        return counts

    @staticmethod
    def _objective_utility_signals(
        *,
        objective_consulted: bool,
        transition_counts: dict[str, int],
        missing_next_action: bool,
        missing_artifact: bool,
    ) -> list[str]:
        signals: list[str] = []
        if objective_consulted:
            signals.append("objective_consulted")
        for transition, signal in (
            ("resume", "objective_resumed"),
            ("pause", "objective_paused"),
            ("block", "objective_blocked"),
            ("complete", "objective_completed"),
            ("redefine-next-action", "objective_next_action_redefined"),
        ):
            if transition_counts.get(transition, 0) > 0:
                signals.append(signal)
        if missing_next_action:
            signals.append("objective_missing_next_action")
        if missing_artifact:
            signals.append("objective_missing_artifact")
        return signals

    @staticmethod
    def _operator_usefulness_signals(
        *,
        objective_consulted: bool,
        active_work_item_count: int,
        artifact_attached: bool,
        next_action_ready: bool,
        memory_causality_status: str,
        experience_reflection_status: str,
        reviewed_learning_assisted_eval_status: str,
        missing_next_action: bool,
        missing_artifact: bool,
    ) -> list[str]:
        signals: list[str] = []
        if objective_consulted:
            signals.append("operator_checked_state")
        if active_work_item_count > 0:
            signals.append("operator_has_work_items")
        if artifact_attached:
            signals.append("operator_has_artifacts")
        if next_action_ready:
            signals.append("operator_has_next_action")
        if memory_causality_status == "causal_guidance":
            signals.append("operator_memory_reused")
        if experience_reflection_status not in {"not_applicable", ""}:
            signals.append("operator_learning_recorded")
        if reviewed_learning_assisted_eval_status == "reviewed_learning_assisted":
            signals.append("operator_reviewed_learning_used")
        if missing_next_action:
            signals.append("operator_missing_next_action")
        if missing_artifact:
            signals.append("operator_missing_artifact")
        return signals

    @staticmethod
    def _operator_usefulness_score(signals: list[str]) -> int:
        negative = {"operator_missing_next_action", "operator_missing_artifact"}
        return max(0, len([item for item in signals if item not in negative]))

    @staticmethod
    def _operator_usefulness_status(
        *,
        score: int,
        missing_next_action: bool,
        missing_artifact: bool,
    ) -> str:
        if score >= 4 and not missing_next_action and not missing_artifact:
            return "useful"
        if score >= 2:
            return "partial"
        return "insufficient_signal"

    @staticmethod
    def _technology_absorption_signals(
        *,
        readiness: str,
        decision: str,
        blockers: list[str],
        candidate_refs: list[str],
    ) -> list[str]:
        signals: list[str] = []
        if candidate_refs:
            signals.append("technology_candidate_observed")
        if readiness not in {"not_applicable", ""}:
            signals.append(f"technology_absorption_readiness:{readiness}")
        if decision not in {"not_applicable", ""}:
            signals.append(f"technology_absorption_decision:{decision}")
        if blockers:
            signals.append("technology_absorption_blocked")
        if decision == "manual_promotion_review":
            signals.append("technology_absorption_manual_review_required")
        return signals

    @staticmethod
    def _experience_reflection_signals(
        *,
        status: str,
        change_type: str,
        blockers: list[str],
        refs: list[str],
    ) -> list[str]:
        signals: list[str] = []
        if refs:
            signals.append("experience_reflection_observed")
        if status not in {"not_applicable", ""}:
            signals.append(f"experience_reflection_status:{status}")
        if change_type not in {"not_applicable", ""}:
            signals.append(f"experience_reflection_change_type:{change_type}")
        if blockers:
            signals.append("experience_reflection_blocked")
        if status in {"candidate", "manual_review"}:
            signals.append("experience_reflection_manual_review_required")
        return signals

    @staticmethod
    def _reflection_assisted_eval_status(
        *,
        status: str,
        refs: list[str],
    ) -> str:
        if status == "applied" and refs:
            return "reflection_assisted"
        if status == "applied":
            return "reflection_signal_incomplete"
        if status in {"not_applicable", "no_relevant_reflection", "no_workflow_profile", ""}:
            return "baseline_no_reflection"
        return "reflection_review_required"

    @staticmethod
    def _reviewed_learning_assisted_eval_status(
        *,
        status: str,
        refs: list[str],
    ) -> str:
        if status == "applied" and refs:
            return "reviewed_learning_assisted"
        if status == "applied":
            return "reviewed_learning_signal_incomplete"
        if status in {
            "not_applicable",
            "no_relevant_guidance",
            "no_workflow_profile",
            "",
        }:
            return "baseline_no_reviewed_learning"
        return "reviewed_learning_review_required"

    @staticmethod
    def _multi_surface_readiness(
        *,
        surface_continuity_status: str,
        linked_surface_count: int,
        surface_identity_conflict_flags: list[str],
    ) -> str:
        status = surface_continuity_status or "not_applicable"
        if surface_identity_conflict_flags or "conflict" in status:
            return "attention_required"
        if status == "not_applicable" and linked_surface_count == 0:
            return "not_applicable"
        if linked_surface_count <= 1 and status in {
            "single_surface",
            "not_applicable",
        }:
            return "single_surface_ready"
        if linked_surface_count > 1:
            return "observable_not_promoted"
        return "attention_required"

    @staticmethod
    def _continuity_trace_status(
        *,
        missing_continuity_signals: list[str],
        continuity_anomaly_flags: list[str],
    ) -> str:
        if continuity_anomaly_flags:
            return "attention_required"
        if missing_continuity_signals:
            return "incomplete"
        return "healthy"

    @staticmethod
    def _workflow_trace_status(
        *,
        operation_dispatched_event: InternalEventEnvelope | None,
        workflow_composed_event: InternalEventEnvelope | None,
        workflow_governance_event: InternalEventEnvelope | None,
        workflow_completed_event: InternalEventEnvelope | None,
    ) -> str:
        if (
            operation_dispatched_event is None
            and workflow_composed_event is None
            and workflow_governance_event is None
            and workflow_completed_event is None
        ):
            return "not_applicable"
        if (
            workflow_composed_event is None
            and workflow_governance_event is None
            and workflow_completed_event is None
        ):
            return "not_applicable"
        if workflow_composed_event is None:
            return "attention_required"
        if workflow_governance_event is None or workflow_completed_event is None:
            return "incomplete"
        decision_points = workflow_composed_event.payload.get("workflow_decision_points", [])
        workflow_checkpoints = workflow_composed_event.payload.get("workflow_checkpoints", [])
        checkpoint_state = workflow_completed_event.payload.get("workflow_checkpoint_state", {})
        pending_checkpoints = workflow_completed_event.payload.get(
            "workflow_pending_checkpoints",
            [],
        )
        completed_decisions = workflow_completed_event.payload.get("workflow_decisions", [])
        workflow_state = workflow_completed_event.payload.get("workflow_state")
        governance_mode = workflow_governance_event.payload.get("workflow_governance_mode")
        workflow_objective = workflow_composed_event.payload.get("workflow_objective")
        composed_checkpoint_state = workflow_composed_event.payload.get(
            "workflow_checkpoint_state",
            {},
        )
        resume_status = workflow_completed_event.payload.get("workflow_resume_status")
        workflow_expected_deliverables = workflow_composed_event.payload.get(
            "workflow_expected_deliverables",
            [],
        )
        workflow_telemetry_focus = workflow_composed_event.payload.get(
            "workflow_telemetry_focus",
            [],
        )
        workflow_success_focus = workflow_governance_event.payload.get("workflow_success_focus")
        workflow_response_focus = workflow_completed_event.payload.get("workflow_response_focus")
        if not decision_points or not completed_decisions:
            return "attention_required"
        if not workflow_checkpoints or not checkpoint_state or not composed_checkpoint_state:
            return "attention_required"
        if sorted(checkpoint_state) != sorted(workflow_checkpoints):
            return "attention_required"
        if sorted(composed_checkpoint_state) != sorted(workflow_checkpoints):
            return "attention_required"
        if any(status != "completed" for status in checkpoint_state.values()):
            return "attention_required"
        if pending_checkpoints:
            return "attention_required"
        if resume_status not in {
            "resumed_from_checkpoint",
            "checkpointed_for_followup",
            "checkpointed_for_manual_resume",
            "completed_without_resume",
            "resume_blocked",
        }:
            return "attention_required"
        if workflow_state not in {"completed", "failed"}:
            return "attention_required"
        if governance_mode != "core_mediated":
            return "attention_required"
        if not workflow_objective:
            return "attention_required"
        if not workflow_expected_deliverables or not workflow_telemetry_focus:
            return "attention_required"
        if not workflow_success_focus or not workflow_response_focus:
            return "attention_required"
        if operation_dispatched_event is not None:
            if (
                operation_dispatched_event.payload.get("workflow_expected_deliverables")
                != workflow_expected_deliverables
            ):
                return "attention_required"
            if (
                operation_dispatched_event.payload.get("workflow_telemetry_focus")
                != workflow_telemetry_focus
            ):
                return "attention_required"
            if (
                operation_dispatched_event.payload.get("workflow_objective")
                != workflow_objective
            ):
                return "attention_required"
            if (
                operation_dispatched_event.payload.get("workflow_checkpoint_state")
                != composed_checkpoint_state
            ):
                return "attention_required"
            if operation_dispatched_event.payload.get("workflow_resume_status") not in {
                "fresh_start",
                "resume_available",
                "manual_resume_required",
            }:
                return "attention_required"
        return "healthy"

    @staticmethod
    def _workflow_checkpoint_status(
        *,
        workflow_composed_event: InternalEventEnvelope | None,
        workflow_completed_event: InternalEventEnvelope | None,
    ) -> str:
        if workflow_composed_event is None and workflow_completed_event is None:
            return "not_applicable"
        if workflow_composed_event is None or workflow_completed_event is None:
            return "incomplete"
        workflow_checkpoints = workflow_composed_event.payload.get("workflow_checkpoints", [])
        composed_state = workflow_composed_event.payload.get("workflow_checkpoint_state", {})
        completed_state = workflow_completed_event.payload.get("workflow_checkpoint_state", {})
        pending_checkpoints = workflow_completed_event.payload.get(
            "workflow_pending_checkpoints",
            [],
        )
        if not workflow_checkpoints or not composed_state or not completed_state:
            return "attention_required"
        if any(status not in {"pending", "resume_ready"} for status in composed_state.values()):
            return "attention_required"
        if any(status != "completed" for status in completed_state.values()):
            return "attention_required"
        if pending_checkpoints:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _workflow_resume_signals(
        *,
        workflow_composed_event: InternalEventEnvelope | None,
        workflow_completed_event: InternalEventEnvelope | None,
    ) -> tuple[str, str | None]:
        if workflow_composed_event is None and workflow_completed_event is None:
            return ("not_applicable", None)
        completed_status = (
            str(workflow_completed_event.payload.get("workflow_resume_status"))
            if workflow_completed_event is not None
            and workflow_completed_event.payload.get("workflow_resume_status") is not None
            else None
        )
        completed_point = (
            str(workflow_completed_event.payload.get("workflow_resume_point"))
            if workflow_completed_event is not None
            and workflow_completed_event.payload.get("workflow_resume_point") is not None
            else None
        )
        if completed_status is not None:
            return (completed_status, completed_point)
        composed_status = (
            str(workflow_composed_event.payload.get("workflow_resume_status"))
            if workflow_composed_event is not None
            and workflow_composed_event.payload.get("workflow_resume_status") is not None
            else "incomplete"
        )
        composed_point = (
            str(workflow_composed_event.payload.get("workflow_resume_point"))
            if workflow_composed_event is not None
            and workflow_composed_event.payload.get("workflow_resume_point") is not None
            else None
        )
        return (composed_status, composed_point)

    @staticmethod
    def _workflow_pending_checkpoint_count(
        *,
        workflow_completed_event: InternalEventEnvelope | None,
    ) -> int:
        if workflow_completed_event is None:
            return 0
        return len(workflow_completed_event.payload.get("workflow_pending_checkpoints", []))

    @staticmethod
    def _workflow_profile_status(
        *,
        workflow_profile: str | None,
        workflow_trace_status: str,
        response_event: InternalEventEnvelope | None,
        shared_memory_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
        workflow_output_status: str,
    ) -> str:
        if workflow_profile is None:
            return "not_applicable"
        if workflow_trace_status != "healthy":
            return workflow_trace_status
        if response_event is None:
            return "maturation_recommended"
        if workflow_output_status == "misaligned":
            return "attention_required"
        if workflow_output_status in {"partial", "incomplete"}:
            return "maturation_recommended"
        response_payload = response_event.payload
        if not response_payload.get("primary_mind"):
            return "maturation_recommended"
        if not response_payload.get("primary_domain_driver"):
            return "maturation_recommended"

        guided_memory_specialists = [
            str(item)
            for item in response_payload.get("guided_memory_specialists", [])
            if item
        ]
        semantic_memory_focus = [
            str(item)
            for item in response_payload.get("semantic_memory_focus", [])
            if item
        ]
        procedural_memory_hint = response_payload.get("procedural_memory_hint")
        shared_guided_specialists = (
            [
                str(item)
                for item in shared_memory_event.payload.get("guided_specialists", [])
                if item
            ]
            if shared_memory_event is not None
            else []
        )
        domain_specialists = (
            [
                str(item)
                for item in specialist_domain_event.payload.get("specialist_types", [])
                if item
            ]
            if specialist_domain_event is not None
            else []
        )
        has_specialist_support = bool(
            guided_memory_specialists or shared_guided_specialists or domain_specialists
        )

        if workflow_profile in {
            "strategic_direction_workflow",
            "structured_analysis_workflow",
        }:
            if not has_specialist_support or not semantic_memory_focus:
                return "maturation_recommended"
        if workflow_profile in {
            "strategic_direction_workflow",
            "decision_risk_workflow",
            "software_change_workflow",
            "operational_readiness_workflow",
        }:
            if not procedural_memory_hint:
                return "maturation_recommended"
        return "healthy"

    @staticmethod
    def _domain_alignment_status(
        *,
        domain_registry_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
        specialist_shadow_event: InternalEventEnvelope | None,
    ) -> str:
        if domain_registry_event is None:
            return "incomplete"
        registry_domains = domain_registry_event.payload.get("registry_domains", [])
        if not registry_domains:
            return "partial"
        route_domains = domain_registry_event.payload.get("route_domains", [])
        canonical_refs_by_route = domain_registry_event.payload.get(
            "canonical_domain_refs_by_route",
            {},
        )
        route_modes = domain_registry_event.payload.get("route_modes", {})
        route_maturity = domain_registry_event.payload.get("route_maturity", {})
        linked_specialist_types = domain_registry_event.payload.get("linked_specialist_types", {})
        promoted_route_registry = domain_registry_event.payload.get("promoted_route_registry", {})
        consumer_profiles = domain_registry_event.payload.get("consumer_profiles", {})
        consumer_objectives = domain_registry_event.payload.get("consumer_objectives", {})
        expected_deliverables = domain_registry_event.payload.get("expected_deliverables", {})
        telemetry_focus = domain_registry_event.payload.get("telemetry_focus", {})
        workflow_profiles = domain_registry_event.payload.get("workflow_profiles", {})
        routing_sources = domain_registry_event.payload.get("routing_sources", {})
        if route_domains and canonical_refs_by_route:
            for route_domain in route_domains:
                if route_domain not in canonical_refs_by_route:
                    return "attention_required"
                if routing_sources and route_domain not in routing_sources and route_domain in linked_specialist_types:
                    return "attention_required"
                if route_domain not in route_maturity or route_maturity.get(route_domain) is None:
                    return "attention_required"
                if route_domain in route_modes and route_modes[route_domain] not in {
                    "shadow",
                    "guided",
                    "active",
                    None,
                }:
                    return "attention_required"
                if route_domain in linked_specialist_types and route_domain not in route_modes:
                    return "attention_required"
                if route_domain in workflow_profiles and not workflow_profiles.get(route_domain):
                    return "attention_required"
        if promoted_route_registry:
            for route_domain, route_payload in promoted_route_registry.items():
                if route_domain not in route_domains:
                    return "attention_required"
                if not route_payload.get("canonical_domain_refs"):
                    return "attention_required"
                if route_payload.get("linked_specialist_type") is None:
                    return "attention_required"
                if route_payload.get("specialist_mode") not in {"guided", "active"}:
                    return "attention_required"
                if route_payload.get("maturity") != "active_specialist":
                    return "attention_required"
                if route_payload.get("mode_is_governed") is not True:
                    return "attention_required"
                if route_payload.get("eligible") is not True:
                    return "attention_required"
                if not consumer_profiles.get(route_domain):
                    return "attention_required"
                if not consumer_objectives.get(route_domain):
                    return "attention_required"
                if not expected_deliverables.get(route_domain):
                    return "attention_required"
                if not telemetry_focus.get(route_domain):
                    return "attention_required"
        if specialist_selection_event is not None:
            selected_specialists = specialist_selection_event.payload.get(
                "selected_specialists",
                [],
            )
            linked_domains = specialist_selection_event.payload.get("domain_links", {})
            selection_modes = specialist_selection_event.payload.get("selection_modes", {})
            route_maturity_by_specialist = specialist_selection_event.payload.get(
                "route_maturity",
                {},
            )
            canonical_domain_refs = specialist_selection_event.payload.get(
                "canonical_domain_refs_resolved",
                {},
            )
            registry_route_payloads = specialist_selection_event.payload.get(
                "registry_route_payloads",
                {},
            )
            registry_link_matches = specialist_selection_event.payload.get(
                "registry_link_matches",
                {},
            )
            registry_mode_matches = specialist_selection_event.payload.get(
                "registry_mode_matches",
                {},
            )
            registry_specialist_eligibility = specialist_selection_event.payload.get(
                "registry_specialist_eligibility",
                {},
            )
            primary_route = specialist_selection_event.payload.get("primary_route")
            primary_canonical_domain = specialist_selection_event.payload.get(
                "primary_canonical_domain"
            )
            primary_domain_driver = specialist_selection_event.payload.get(
                "primary_domain_driver"
            )
            primary_route_matches = specialist_selection_event.payload.get(
                "primary_route_matches",
                {},
            )
            primary_canonical_matches = specialist_selection_event.payload.get(
                "primary_canonical_matches",
                {},
            )
            primary_domain_driver_matches = specialist_selection_event.payload.get(
                "primary_domain_driver_matches",
                {},
            )
            for specialist_type in selected_specialists:
                linked_domain = linked_domains.get(specialist_type)
                if not linked_domain:
                    return "attention_required"
                if route_domains and linked_domain not in route_domains:
                    return "attention_required"
                if canonical_domain_refs and not canonical_domain_refs.get(specialist_type):
                    return "attention_required"
                if route_maturity_by_specialist and not route_maturity_by_specialist.get(
                    specialist_type
                ):
                    return "attention_required"
                if registry_route_payloads:
                    route_payload = registry_route_payloads.get(specialist_type)
                    if not route_payload:
                        return "attention_required"
                    if route_payload.get("route_name") != linked_domain:
                        return "attention_required"
                    if route_payload.get("linked_specialist_type") != specialist_type:
                        return "attention_required"
                    if not route_payload.get("canonical_domain_refs"):
                        return "attention_required"
                if registry_link_matches and registry_link_matches.get(specialist_type) is not True:
                    return "attention_required"
                if (
                    registry_mode_matches
                    and registry_mode_matches.get(specialist_type) is not True
                ):
                    return "attention_required"
                if (
                    registry_specialist_eligibility
                    and registry_specialist_eligibility.get(specialist_type) is not True
                ):
                    return "attention_required"
                if promoted_route_registry and linked_domain not in promoted_route_registry:
                    return "attention_required"
                if route_modes and selection_modes:
                    if route_modes.get(linked_domain) != selection_modes.get(specialist_type):
                        return "attention_required"
                if linked_specialist_types and (
                    linked_specialist_types.get(linked_domain) != specialist_type
                ):
                    return "attention_required"
                if primary_route and linked_domain == primary_route:
                    if primary_route_matches and primary_route_matches.get(specialist_type) is not True:
                        return "attention_required"
                    if (
                        primary_canonical_domain
                        and primary_canonical_matches
                        and primary_canonical_matches.get(specialist_type) is not True
                    ):
                        return "attention_required"
                    if (
                        primary_domain_driver
                        and primary_domain_driver_matches
                        and primary_domain_driver_matches.get(specialist_type) is not True
                    ):
                        return "attention_required"
            if (
                primary_domain_driver
                and primary_domain_driver_matches
                and selected_specialists
                and not any(
                    primary_domain_driver_matches.get(specialist_type) is True
                    for specialist_type in selected_specialists
                )
            ):
                return "attention_required"
        if specialist_domain_event is not None:
            linked_domains = specialist_domain_event.payload.get("linked_domains", {})
            selection_modes = specialist_domain_event.payload.get("selection_modes", {})
            route_maturity = specialist_domain_event.payload.get("route_maturity", {})
            canonical_domain_refs = specialist_domain_event.payload.get("canonical_domain_refs_resolved", {})
            registry_route_payloads = specialist_domain_event.payload.get(
                "registry_route_payloads",
                {},
            )
            registry_link_matches = specialist_domain_event.payload.get("registry_link_matches", {})
            registry_mode_matches = specialist_domain_event.payload.get("registry_mode_matches", {})
            registry_specialist_eligibility = specialist_domain_event.payload.get(
                "registry_specialist_eligibility",
                {},
            )
            primary_route = specialist_domain_event.payload.get("primary_route")
            primary_canonical_domain = specialist_domain_event.payload.get(
                "primary_canonical_domain"
            )
            primary_domain_driver = specialist_domain_event.payload.get(
                "primary_domain_driver"
            )
            primary_route_matches = specialist_domain_event.payload.get(
                "primary_route_matches",
                {},
            )
            primary_canonical_matches = specialist_domain_event.payload.get(
                "primary_canonical_matches",
                {},
            )
            primary_domain_driver_matches = specialist_domain_event.payload.get(
                "primary_domain_driver_matches",
                {},
            )
            if not linked_domains or not selection_modes:
                return "attention_required"
            for specialist_type, linked_domain in linked_domains.items():
                if route_domains and linked_domain not in route_domains:
                    return "attention_required"
                if canonical_domain_refs and not canonical_domain_refs.get(specialist_type):
                    return "attention_required"
                if route_maturity and not route_maturity.get(specialist_type):
                    return "attention_required"
                if registry_route_payloads:
                    route_payload = registry_route_payloads.get(specialist_type)
                    if not route_payload:
                        return "attention_required"
                    if route_payload.get("route_name") != linked_domain:
                        return "attention_required"
                    if route_payload.get("linked_specialist_type") != specialist_type:
                        return "attention_required"
                    if not route_payload.get("canonical_domain_refs"):
                        return "attention_required"
                if registry_link_matches and registry_link_matches.get(specialist_type) is not True:
                    return "attention_required"
                if (
                    registry_mode_matches
                    and registry_mode_matches.get(specialist_type) is not True
                ):
                    return "attention_required"
                if (
                    registry_specialist_eligibility
                    and registry_specialist_eligibility.get(specialist_type) is not True
                ):
                    return "attention_required"
                if promoted_route_registry and linked_domain not in promoted_route_registry:
                    return "attention_required"
                if route_modes and route_modes.get(linked_domain) != selection_modes.get(specialist_type):
                    return "attention_required"
                if linked_specialist_types and linked_specialist_types.get(linked_domain) != specialist_type:
                    return "attention_required"
                if primary_route and linked_domain == primary_route:
                    if primary_route_matches and primary_route_matches.get(specialist_type) is not True:
                        return "attention_required"
                    if (
                        primary_canonical_domain
                        and primary_canonical_matches
                        and primary_canonical_matches.get(specialist_type) is not True
                    ):
                        return "attention_required"
                    if (
                        primary_domain_driver
                        and primary_domain_driver_matches
                        and primary_domain_driver_matches.get(specialist_type) is not True
                    ):
                        return "attention_required"
            if (
                primary_domain_driver
                and primary_domain_driver_matches
                and linked_domains
                and not any(
                    primary_domain_driver_matches.get(specialist_type) is True
                    for specialist_type in linked_domains
                )
            ):
                return "attention_required"
            return "healthy"
        if specialist_shadow_event is None:
            return "healthy"
        linked_domains = specialist_shadow_event.payload.get("linked_domains", {})
        return "healthy" if linked_domains else "attention_required"

    @staticmethod
    def _identity_alignment_status(
        *,
        directive_event: InternalEventEnvelope | None,
        plan_governed_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        if directive_event is None and plan_governed_event is None and response_event is None:
            return "incomplete"
        if directive_event is None or response_event is None:
            return "partial"
        directive_mode = directive_event.payload.get("identity_mode")
        response_mode = response_event.payload.get("identity_mode")
        directive_signature = directive_event.payload.get("identity_signature")
        response_signature = response_event.payload.get("identity_signature")
        plan_signature = (
            plan_governed_event.payload.get("identity_signature")
            if plan_governed_event is not None
            else directive_signature
        )
        plan_mode = (
            plan_governed_event.payload.get("identity_mode")
            if plan_governed_event is not None
            else directive_mode
        )
        response_style = response_event.payload.get("response_style")
        guardrail = (
            plan_governed_event.payload.get("identity_guardrail")
            if plan_governed_event is not None
            else None
        )
        if not directive_signature or not response_signature:
            return "partial"
        if directive_signature != response_signature or directive_signature != plan_signature:
            return "attention_required"
        if directive_mode != response_mode or directive_mode != plan_mode:
            return "attention_required"
        if not response_style or not guardrail:
            return "partial"
        return "healthy"

    @staticmethod
    def _mind_alignment_status(
        *,
        context_event: InternalEventEnvelope | None,
        plan_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        if context_event is None:
            return "incomplete"
        primary_mind = context_event.payload.get("primary_mind")
        primary_mind_family = context_event.payload.get("primary_mind_family")
        active_minds = context_event.payload.get("active_minds", [])
        supporting_minds = context_event.payload.get("supporting_minds", [])
        suppressed_minds = context_event.payload.get("suppressed_minds", [])
        dominant_tension = context_event.payload.get("dominant_tension")
        arbitration_summary = context_event.payload.get("arbitration_summary")
        arbitration_source = context_event.payload.get("arbitration_source")
        recomposition_applied = bool(
            context_event.payload.get("cognitive_recomposition_applied")
        )
        recomposition_reason = context_event.payload.get("cognitive_recomposition_reason")
        recomposition_trigger = context_event.payload.get("cognitive_recomposition_trigger")
        canonical_domains = context_event.payload.get("canonical_domains", [])
        primary_domain_driver = context_event.payload.get("primary_domain_driver")
        support_limit = context_event.payload.get("supporting_mind_limit")
        suppressed_limit = context_event.payload.get("suppressed_mind_limit")
        if not primary_mind or not active_minds or not dominant_tension:
            return "partial"
        allowed_source = (
            "mind_registry_recomposition" if recomposition_applied else "mind_registry"
        )
        if arbitration_source != allowed_source:
            return "attention_required"
        if not arbitration_summary:
            return "attention_required"
        if recomposition_applied and (not recomposition_reason or not recomposition_trigger):
            return "attention_required"
        if (
            not recomposition_applied
            and (recomposition_reason is not None or recomposition_trigger is not None)
        ):
            return "attention_required"
        if canonical_domains and primary_domain_driver and primary_domain_driver not in canonical_domains:
            return "attention_required"
        if not isinstance(supporting_minds, list) or not isinstance(suppressed_minds, list):
            return "attention_required"
        if active_minds[0] != primary_mind:
            return "attention_required"
        if active_minds[1:] != supporting_minds:
            return "attention_required"
        if primary_mind in supporting_minds or primary_mind in suppressed_minds:
            return "attention_required"
        if isinstance(support_limit, int) and len(supporting_minds) > support_limit:
            return "attention_required"
        if isinstance(suppressed_limit, int) and len(suppressed_minds) > suppressed_limit:
            return "attention_required"
        if plan_event is not None:
            plan_primary_mind = plan_event.payload.get("primary_mind")
            plan_primary_mind_family = plan_event.payload.get("primary_mind_family")
            plan_primary_domain_driver = plan_event.payload.get("primary_domain_driver")
            plan_arbitration_source = plan_event.payload.get("arbitration_source")
            plan_recomposition_applied = plan_event.payload.get(
                "cognitive_recomposition_applied"
            )
            plan_recomposition_reason = plan_event.payload.get(
                "cognitive_recomposition_reason"
            )
            plan_recomposition_trigger = plan_event.payload.get(
                "cognitive_recomposition_trigger"
            )
            if plan_primary_mind is not None and plan_primary_mind != primary_mind:
                return "attention_required"
            if (
                plan_primary_mind_family is not None
                and primary_mind_family is not None
                and plan_primary_mind_family != primary_mind_family
            ):
                return "attention_required"
            if (
                plan_primary_domain_driver is not None
                and primary_domain_driver is not None
                and plan_primary_domain_driver != primary_domain_driver
            ):
                return "attention_required"
            if (
                plan_arbitration_source is not None
                and plan_arbitration_source != arbitration_source
            ):
                return "attention_required"
            if (
                plan_recomposition_applied is not None
                and bool(plan_recomposition_applied) != recomposition_applied
            ):
                return "attention_required"
            if (
                plan_recomposition_reason is not None
                and plan_recomposition_reason != recomposition_reason
            ):
                return "attention_required"
            if (
                plan_recomposition_trigger is not None
                and plan_recomposition_trigger != recomposition_trigger
            ):
                return "attention_required"
        if response_event is not None:
            response_primary_mind = response_event.payload.get("primary_mind")
            response_primary_mind_family = response_event.payload.get("primary_mind_family")
            response_primary_domain_driver = response_event.payload.get("primary_domain_driver")
            response_arbitration_source = response_event.payload.get("arbitration_source")
            response_recomposition_applied = response_event.payload.get(
                "cognitive_recomposition_applied"
            )
            response_recomposition_reason = response_event.payload.get(
                "cognitive_recomposition_reason"
            )
            response_recomposition_trigger = response_event.payload.get(
                "cognitive_recomposition_trigger"
            )
            if response_primary_mind is not None and response_primary_mind != primary_mind:
                return "attention_required"
            if (
                response_primary_mind_family is not None
                and primary_mind_family is not None
                and response_primary_mind_family != primary_mind_family
            ):
                return "attention_required"
            if (
                response_primary_domain_driver is not None
                and primary_domain_driver is not None
                and response_primary_domain_driver != primary_domain_driver
            ):
                return "attention_required"
            if (
                response_arbitration_source is not None
                and response_arbitration_source != arbitration_source
            ):
                return "attention_required"
            if (
                response_recomposition_applied is not None
                and bool(response_recomposition_applied) != recomposition_applied
            ):
                return "attention_required"
            if (
                response_recomposition_reason is not None
                and response_recomposition_reason != recomposition_reason
            ):
                return "attention_required"
            if (
                response_recomposition_trigger is not None
                and response_recomposition_trigger != recomposition_trigger
            ):
                return "attention_required"
        return "healthy"

    @staticmethod
    def _cognitive_strategy_shift_status(
        *,
        plan_refined_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        if plan_refined_event is None:
            if response_event is None:
                return "not_applicable"
            response_applied = bool(
                response_event.payload.get("cognitive_strategy_shift_applied")
            )
            response_has_details = any(
                response_event.payload.get(field_name) is not None
                for field_name in (
                    "cognitive_strategy_shift_summary",
                    "cognitive_strategy_shift_trigger",
                )
            ) or bool(response_event.payload.get("cognitive_strategy_shift_effects", []))
            return "attention_required" if response_applied or response_has_details else "not_applicable"

        plan_applied = bool(plan_refined_event.payload.get("cognitive_strategy_shift_applied"))
        plan_summary = plan_refined_event.payload.get("cognitive_strategy_shift_summary")
        plan_trigger = plan_refined_event.payload.get("cognitive_strategy_shift_trigger")
        plan_effects = list(
            plan_refined_event.payload.get("cognitive_strategy_shift_effects", [])
        )
        if plan_applied:
            if not plan_summary or not plan_trigger or not plan_effects:
                return "attention_required"
        elif plan_summary is not None or plan_trigger is not None or plan_effects:
            return "attention_required"

        if response_event is None:
            return "healthy" if plan_applied else "not_applicable"

        response_applied = bool(
            response_event.payload.get("cognitive_strategy_shift_applied")
        )
        response_summary = response_event.payload.get("cognitive_strategy_shift_summary")
        response_trigger = response_event.payload.get("cognitive_strategy_shift_trigger")
        response_effects = list(
            response_event.payload.get("cognitive_strategy_shift_effects", [])
        )
        if response_applied != plan_applied:
            return "attention_required"
        if response_summary != plan_summary:
            return "attention_required"
        if response_trigger != plan_trigger:
            return "attention_required"
        if response_effects != plan_effects:
            return "attention_required"
        return "healthy" if plan_applied else "not_applicable"

    @staticmethod
    def _capability_decision_status(
        *,
        source_event: InternalEventEnvelope | None,
    ) -> str:
        if source_event is None:
            return "not_applicable"
        decision_status = source_event.payload.get("capability_decision_status")
        selected_mode = source_event.payload.get("capability_decision_selected_mode")
        authorization_status = source_event.payload.get(
            "capability_decision_authorization_status"
        )
        objective = source_event.payload.get("capability_decision_objective")
        reason = source_event.payload.get("capability_decision_reason")
        fallback_mode = source_event.payload.get("capability_decision_fallback_mode")
        tool_class = source_event.payload.get("capability_decision_tool_class")
        handoff_mode = source_event.payload.get("capability_decision_handoff_mode")
        eligible_capabilities = list(
            source_event.payload.get("capability_decision_eligible_capabilities", [])
        )
        selected_capabilities = list(
            source_event.payload.get("capability_decision_selected_capabilities", [])
        )

        if (
            decision_status is None
            and selected_mode is None
            and authorization_status is None
            and not eligible_capabilities
            and not selected_capabilities
        ):
            return "not_applicable"

        if decision_status not in {"resolved", "contained"}:
            return "attention_required"
        if not objective or reason is None:
            return "attention_required"
        if selected_mode not in {
            "clarification_only",
            "contained_guidance",
            "core_guidance_only",
            "core_with_specialist_handoff",
            "core_with_local_operation",
        }:
            return "attention_required"
        if authorization_status is None or fallback_mode is None:
            return "attention_required"
        if not eligible_capabilities or not selected_capabilities:
            return "attention_required"
        if "core_reasoning" not in selected_capabilities:
            return "attention_required"
        if any(item not in eligible_capabilities for item in selected_capabilities):
            return "attention_required"
        if selected_mode == "core_with_local_operation":
            if tool_class is None:
                return "attention_required"
            if "local_safe_operation" not in selected_capabilities:
                return "attention_required"
        elif tool_class is not None:
            return "attention_required"
        if handoff_mode == "through_core_only":
            if "specialist_handoff" not in selected_capabilities:
                return "attention_required"
        elif handoff_mode not in {None, "none"}:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _handoff_adapter_status(
        *,
        capability_decision_handoff_mode: str | None,
        capability_authorization_status: str,
        specialist_contract_event: InternalEventEnvelope | None,
        specialist_handoff_event: InternalEventEnvelope | None,
        specialist_handoff_blocked_event: InternalEventEnvelope | None,
    ) -> str:
        handoff_disabled = capability_decision_handoff_mode in {None, "none"}
        handoff_contained = capability_authorization_status in {
            "blocked",
            "deferred_for_validation",
            "clarification_required",
            "human_validation_required",
        }

        if handoff_disabled:
            if specialist_contract_event is not None or specialist_handoff_event is not None:
                return "attention_required"
            if specialist_handoff_blocked_event is not None:
                return "contained" if handoff_contained else "attention_required"
            return "not_applicable"

        if capability_decision_handoff_mode != "through_core_only":
            return "attention_required"

        if handoff_contained:
            if specialist_contract_event is not None:
                return "attention_required"
            if specialist_handoff_blocked_event is not None:
                return "contained"
            if specialist_handoff_event is not None:
                decision = specialist_handoff_event.payload.get("decision")
                if decision in {"block", "defer_for_validation"}:
                    return "contained"
                return "attention_required"
            return "contained"

        if specialist_contract_event is None or specialist_handoff_event is None:
            return "incomplete"
        if specialist_contract_event.payload.get("response_channel") != "through_core":
            return "attention_required"
        if specialist_contract_event.payload.get("tool_access_mode") != "none":
            return "attention_required"
        if not specialist_contract_event.payload.get("invocation_ids"):
            return "attention_required"
        if specialist_handoff_event.payload.get("decision") not in {
            "allow",
            "allow_with_conditions",
        }:
            return "attention_required"
        if specialist_handoff_blocked_event is not None:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _request_identity_status(
        *,
        source_event: InternalEventEnvelope | None,
    ) -> str:
        if source_event is None:
            return "not_applicable"
        status = source_event.payload.get("request_identity_status")
        active_mission = source_event.payload.get("request_active_mission")
        executive_posture = source_event.payload.get("request_executive_posture")
        authority_level = source_event.payload.get("request_authority_level")
        risk_profile = source_event.payload.get("request_risk_profile")
        reversibility_mode = source_event.payload.get("request_reversibility_mode")
        confirmation_mode = source_event.payload.get("request_confirmation_mode")
        summary = source_event.payload.get("request_identity_summary")
        policy_refs = list(source_event.payload.get("request_identity_policy_refs", []))
        if (
            status is None
            and active_mission is None
            and executive_posture is None
            and authority_level is None
            and risk_profile is None
            and reversibility_mode is None
            and confirmation_mode is None
            and summary is None
            and not policy_refs
        ):
            return "not_applicable"
        if status != "resolved":
            return "attention_required"
        if not active_mission or executive_posture is None or authority_level is None:
            return "attention_required"
        if risk_profile is None or reversibility_mode is None or confirmation_mode is None:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _request_identity_mismatch_flags(
        *,
        request_identity_source_event: InternalEventEnvelope | None,
        governance_event: InternalEventEnvelope | None,
        operation_dispatched_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> list[str]:
        if request_identity_source_event is None:
            return []
        payload = request_identity_source_event.payload
        authority_level = payload.get("request_authority_level")
        confirmation_mode = payload.get("request_confirmation_mode")
        reversibility_mode = payload.get("request_reversibility_mode")
        active_mission = payload.get("request_active_mission")
        flags: list[str] = []

        governance_decision = (
            str(governance_event.payload.get("decision"))
            if governance_event and governance_event.payload.get("decision") is not None
            else None
        )
        dispatched_mode = (
            str(operation_dispatched_event.payload.get("capability_decision_selected_mode"))
            if operation_dispatched_event
            and operation_dispatched_event.payload.get("capability_decision_selected_mode")
            is not None
            else None
        )
        response_mission = (
            str(response_event.payload.get("request_active_mission"))
            if response_event and response_event.payload.get("request_active_mission") is not None
            else None
        )

        if (
            authority_level == "analysis_only"
            and dispatched_mode == "core_with_local_operation"
        ):
            flags.append("authority_level_mismatch")
        if (
            confirmation_mode == "explicit_confirmation_required"
            and governance_decision == "allow"
        ):
            flags.append("confirmation_mode_mismatch")
        if (
            reversibility_mode == "prefer_reversible_change"
            and dispatched_mode == "core_with_local_operation"
            and governance_decision not in {"allow_with_conditions", "defer_for_validation"}
        ):
            flags.append("reversibility_mode_mismatch")
        if active_mission and response_mission not in {None, str(active_mission)}:
            flags.append("active_mission_mismatch")
        return flags

    @staticmethod
    def _mission_policy_status(
        *,
        request_identity_status: str,
        request_identity_mismatch_flags: list[str],
        request_identity_source_event: InternalEventEnvelope | None,
        governance_event: InternalEventEnvelope | None,
    ) -> str:
        if request_identity_status == "not_applicable":
            return "not_applicable"
        if request_identity_status != "healthy":
            return "attention_required"
        if request_identity_mismatch_flags:
            return "attention_required"
        if request_identity_source_event is None:
            return "attention_required"
        confirmation_mode = request_identity_source_event.payload.get(
            "request_confirmation_mode"
        )
        governance_decision = (
            str(governance_event.payload.get("decision"))
            if governance_event and governance_event.payload.get("decision") is not None
            else None
        )
        if confirmation_mode == "explicit_confirmation_required":
            return (
                "policy_aligned"
                if governance_decision in {
                    "allow_with_conditions",
                    "defer_for_validation",
                }
                else "attention_required"
            )
        return "policy_aligned"

    @staticmethod
    def _capability_effectiveness(
        *,
        capability_decision_status: str,
        capability_decision_selected_mode: str | None,
        capability_authorization_status: str,
        workflow_output_status: str,
        operation_status: str | None,
        handoff_adapter_status: str,
    ) -> str:
        if capability_decision_status == "not_applicable":
            return "not_applicable"
        if capability_decision_status != "healthy":
            return "incomplete"
        if workflow_output_status not in {"coherent", "not_applicable"}:
            return "insufficient"

        if capability_decision_selected_mode in {
            "clarification_only",
            "contained_guidance",
        }:
            return (
                "effective"
                if capability_authorization_status
                in {
                    "clarification_required",
                    "human_validation_required",
                    "blocked",
                    "deferred_for_validation",
                }
                and operation_status is None
                else "insufficient"
            )
        if capability_decision_selected_mode == "core_with_local_operation":
            if capability_authorization_status in {"authorized", "authorized_with_conditions"}:
                return "effective" if operation_status == "completed" else "insufficient"
            return "effective" if operation_status is None else "insufficient"
        if capability_decision_selected_mode == "core_with_specialist_handoff":
            if capability_authorization_status in {"authorized", "authorized_with_conditions"}:
                return (
                    "effective" if handoff_adapter_status == "healthy" else "insufficient"
                )
            if capability_authorization_status in {"blocked", "deferred_for_validation"}:
                return (
                    "effective" if handoff_adapter_status == "contained" else "insufficient"
                )
            return "insufficient"
        if capability_decision_selected_mode == "core_guidance_only":
            return "effective" if operation_status is None else "insufficient"
        return "insufficient"

    @staticmethod
    def _adaptive_intervention_status(
        *,
        plan_event: InternalEventEnvelope | None,
        plan_refined_event: InternalEventEnvelope | None,
        workflow_composed_event: InternalEventEnvelope | None,
        operation_dispatched_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        source_event = (
            plan_refined_event
            if plan_refined_event
            and (
                plan_refined_event.payload.get("adaptive_intervention_status") is not None
                or plan_refined_event.payload.get("adaptive_intervention_selected_action")
                is not None
            )
            else plan_event
        )
        if source_event is None:
            if response_event is None:
                return "not_applicable"
            response_has_details = any(
                response_event.payload.get(field_name) is not None
                for field_name in (
                    "adaptive_intervention_status",
                    "adaptive_intervention_reason",
                    "adaptive_intervention_trigger",
                    "adaptive_intervention_selected_action",
                    "adaptive_intervention_expected_effect",
                )
            ) or bool(response_event.payload.get("adaptive_intervention_effects", []))
            return "attention_required" if response_has_details else "not_applicable"

        plan_status = source_event.payload.get("adaptive_intervention_status")
        plan_reason = source_event.payload.get("adaptive_intervention_reason")
        plan_trigger = source_event.payload.get("adaptive_intervention_trigger")
        plan_action = source_event.payload.get("adaptive_intervention_selected_action")
        plan_expected_effect = source_event.payload.get(
            "adaptive_intervention_expected_effect"
        )
        plan_effects = list(source_event.payload.get("adaptive_intervention_effects", []))
        plan_applied = plan_status == "applied" or plan_action is not None

        if plan_applied:
            if (
                plan_status != "applied"
                or not plan_reason
                or not plan_trigger
                or not plan_action
                or not plan_expected_effect
                or not plan_effects
            ):
                return "attention_required"
        elif any(
            value is not None for value in (plan_reason, plan_trigger, plan_action, plan_expected_effect)
        ) or plan_effects:
            return "attention_required"

        for event in (workflow_composed_event, operation_dispatched_event, response_event):
            if event is None:
                continue
            event_status = event.payload.get("adaptive_intervention_status")
            event_action = event.payload.get("adaptive_intervention_selected_action")
            event_reason = event.payload.get("adaptive_intervention_reason")
            event_trigger = event.payload.get("adaptive_intervention_trigger")
            event_expected_effect = event.payload.get("adaptive_intervention_expected_effect")
            event_effects = list(event.payload.get("adaptive_intervention_effects", []))
            if event_status is None and event_action is None and not event_effects:
                continue
            if event_status != plan_status:
                return "attention_required"
            if event_action != plan_action:
                return "attention_required"
            if event_reason is not None and event_reason != plan_reason:
                return "attention_required"
            if event_trigger is not None and event_trigger != plan_trigger:
                return "attention_required"
            if event_expected_effect is not None and event_expected_effect != plan_expected_effect:
                return "attention_required"
            if event_effects and event_effects != plan_effects:
                return "attention_required"
        return "healthy" if plan_applied else "not_applicable"

    @staticmethod
    def _adaptive_intervention_effectiveness(
        *,
        adaptive_intervention_status: str,
        adaptive_intervention_selected_action: str | None,
        workflow_output_status: str,
        mind_validation_checkpoint_status: str,
        memory_causality_status: str,
        memory_corpus_status: str,
        workflow_resume_status: str,
        governance_decision: str | None,
        specialist_subflow_status: str,
    ) -> str:
        if adaptive_intervention_status == "not_applicable":
            return "not_applicable"
        if adaptive_intervention_status != "healthy":
            return "incomplete"
        if adaptive_intervention_selected_action == "safe_containment":
            if governance_decision in {"block", "defer_for_validation", "allow_with_conditions"}:
                return "effective"
            if workflow_resume_status == "manual_resume_required":
                return "effective"
            return "insufficient"
        if adaptive_intervention_selected_action == "clarification_checkpoint":
            return "effective" if workflow_output_status == "coherent" else "insufficient"
        if adaptive_intervention_selected_action == "memory_review_checkpoint":
            if workflow_output_status == "coherent" and memory_causality_status == "healthy":
                return "effective"
            if memory_corpus_status == "review_recommended":
                return "effective"
            return "insufficient"
        if adaptive_intervention_selected_action == "specialist_reevaluation":
            if (
                specialist_subflow_status in {"healthy", "contained"}
                and mind_validation_checkpoint_status in {"healthy", "not_applicable"}
                and workflow_output_status == "coherent"
            ):
                return "effective"
            return "insufficient"
        return "effective" if workflow_output_status == "coherent" else "insufficient"

    @staticmethod
    def _memory_maintenance_effectiveness(
        *,
        memory_maintenance_status: str,
        memory_review_status: str,
        context_compaction_status: str | None,
        cross_session_recall_status: str | None,
        memory_retention_pressure: str | None,
        workflow_output_status: str,
    ) -> str:
        if memory_maintenance_status == "not_applicable":
            return "not_applicable"
        if memory_maintenance_status == "incomplete":
            return "incomplete"
        if workflow_output_status not in {"coherent", "not_applicable"}:
            return "insufficient"
        if memory_maintenance_status == "contained_fallback":
            return (
                "effective"
                if memory_review_status in {"attention_required", "review_recommended"}
                and context_compaction_status in {"compressed_live_context", "seeded_live_context"}
                else "insufficient"
            )
        if memory_maintenance_status == "review_required":
            return (
                "effective"
                if memory_review_status in {"review_recommended", "attention_required"}
                and memory_retention_pressure in {"moderate", "high"}
                else "insufficient"
            )
        if memory_maintenance_status == "cross_session_recall_active":
            return (
                "effective"
                if cross_session_recall_status == "active"
                and context_compaction_status in {"compressed_live_context", "seeded_live_context"}
                else "insufficient"
            )
        if memory_maintenance_status == "compaction_active":
            return (
                "effective"
                if context_compaction_status in {"compressed_live_context", "seeded_live_context"}
                else "insufficient"
            )
        return "effective"

    @staticmethod
    def _adaptive_intervention_policy_status(
        *,
        workflow_profile: str | None,
        adaptive_intervention_status: str,
        adaptive_intervention_trigger: str | None,
        adaptive_intervention_selected_action: str | None,
        mind_disagreement_status: str,
        memory_review_status: str,
        memory_corpus_status: str,
        memory_retention_pressure: str | None,
        workflow_resume_status: str,
        continuity_action: str | None,
    ) -> str:
        if adaptive_intervention_status == "not_applicable":
            return "not_applicable"
        if adaptive_intervention_status != "healthy" or adaptive_intervention_selected_action is None:
            return "attention_required"
        if adaptive_intervention_selected_action == "clarification_checkpoint":
            return (
                "mandatory_override"
                if adaptive_intervention_trigger == "clarification_required"
                else "attention_required"
            )
        if adaptive_intervention_selected_action == "safe_containment":
            if adaptive_intervention_trigger in {
                "manual_resume_required",
                "mission_conflict_detected",
            }:
                return "mandatory_override"
            if (
                workflow_resume_status == "manual_resume_required"
                or continuity_action == "reformular"
            ):
                return "mandatory_override"
            return "attention_required"

        candidate_actions: list[str] = []
        if (
            memory_review_status == "review_recommended"
            or memory_corpus_status == "review_recommended"
            or memory_retention_pressure == "high"
        ):
            candidate_actions.append("memory_review_checkpoint")
        if mind_disagreement_status in {"validation_required", "deep_review_required"}:
            candidate_actions.append("specialist_reevaluation")
        if not candidate_actions:
            return "attention_required"

        for prioritized_action in workflow_runtime_guidance(
            workflow_profile
        ).adaptive_intervention_priority:
            if prioritized_action in candidate_actions:
                return (
                    "policy_aligned"
                    if adaptive_intervention_selected_action == prioritized_action
                    else "attention_required"
                )
        return (
            "policy_aligned"
            if adaptive_intervention_selected_action == candidate_actions[0]
            else "attention_required"
        )

    @staticmethod
    def _metacognitive_guidance_status(
        *,
        context_event: InternalEventEnvelope | None,
        plan_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        if context_event is None:
            return "incomplete"
        primary_mind = context_event.payload.get("primary_mind")
        primary_domain_driver = context_event.payload.get("primary_domain_driver")
        dominant_tension = context_event.payload.get("dominant_tension")
        if not dominant_tension or not (primary_mind or primary_domain_driver):
            return "not_applicable"
        if plan_event is None:
            return "incomplete"
        plan_applied = bool(plan_event.payload.get("metacognitive_guidance_applied"))
        plan_summary = plan_event.payload.get("metacognitive_guidance_summary")
        plan_effects = plan_event.payload.get("metacognitive_effects", [])
        plan_containment = plan_event.payload.get(
            "metacognitive_containment_recommendation"
        )
        if plan_applied:
            if not plan_summary or not isinstance(plan_effects, list) or not plan_effects:
                return "attention_required"
        elif plan_summary is not None or plan_effects or plan_containment is not None:
            return "attention_required"
        if response_event is None:
            return "healthy"
        response_applied = bool(response_event.payload.get("metacognitive_guidance_applied"))
        response_summary = response_event.payload.get("metacognitive_guidance_summary")
        response_effects = response_event.payload.get("metacognitive_effects", [])
        response_containment = response_event.payload.get(
            "metacognitive_containment_recommendation"
        )
        if response_applied != plan_applied:
            return "attention_required"
        if response_summary != plan_summary:
            return "attention_required"
        if response_containment != plan_containment:
            return "attention_required"
        if list(response_effects or []) != list(plan_effects or []):
            return "attention_required"
        return "healthy"

    @staticmethod
    def _mind_disagreement_status(
        *,
        plan_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
    ) -> str:
        for event in (response_event, plan_event):
            if event is None:
                continue
            status = event.payload.get("mind_disagreement_status")
            if status is not None:
                return str(status)
        return "not_applicable"

    @staticmethod
    def _mind_validation_checkpoint_status(
        *,
        plan_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
        mind_disagreement_status: str,
    ) -> str:
        if mind_disagreement_status == "not_applicable":
            return "not_applicable"
        checkpoints = []
        if plan_event is not None:
            checkpoints = list(plan_event.payload.get("mind_validation_checkpoints", []))
        response_checkpoints = []
        if response_event is not None:
            response_checkpoints = list(
                response_event.payload.get("mind_validation_checkpoints", [])
            )
        if not checkpoints:
            return "attention_required"
        if response_checkpoints and response_checkpoints != checkpoints:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _mind_domain_specialist_status(
        *,
        context_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
    ) -> str:
        if context_event is None:
            return "incomplete"
        primary_domain_driver = context_event.payload.get("primary_domain_driver")
        if primary_domain_driver is None:
            return "not_applicable"
        specialist_event = specialist_domain_event or specialist_selection_event
        if specialist_event is None:
            return "not_applicable"
        selected_specialists = specialist_event.payload.get(
            "domain_specialists",
            specialist_event.payload.get("specialist_types", []),
        )
        if not selected_specialists:
            return "not_applicable"
        matches = specialist_event.payload.get("primary_domain_driver_matches", {})
        if not isinstance(matches, dict) or not matches:
            return "attention_required"
        if any(matches.get(str(item)) is True for item in selected_specialists):
            return "aligned"
        if all(matches.get(str(item)) is False for item in selected_specialists):
            return "mismatch"
        return "attention_required"

    @staticmethod
    def _specialist_subflow_status(
        *,
        specialist_subflow_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
    ) -> str:
        if specialist_subflow_event is None:
            if specialist_selection_event is None and specialist_domain_event is None:
                return "not_applicable"
            return "incomplete"
        selected_count = int(specialist_subflow_event.payload.get("selection_count", 0) or 0)
        invocation_count = int(
            specialist_subflow_event.payload.get("invocation_count", 0) or 0
        )
        contribution_count = int(
            specialist_subflow_event.payload.get("contribution_count", 0) or 0
        )
        selection_status = specialist_subflow_event.payload.get("selection_status")
        governance_status = specialist_subflow_event.payload.get("governance_status")
        dispatch_status = specialist_subflow_event.payload.get("dispatch_status")
        completion_status = specialist_subflow_event.payload.get("completion_status")
        if selected_count == 0 and selection_status == "not_applicable":
            return "not_applicable"
        if governance_status == "contained":
            if contribution_count == 0 and completion_status == "contained":
                return "contained"
            return "attention_required"
        if selected_count > 0 and invocation_count == 0:
            return "attention_required"
        if selected_count != invocation_count:
            return "attention_required"
        if selected_count > 0 and dispatch_status != "dispatched":
            return "attention_required"
        if contribution_count == 0 and completion_status not in {"not_applicable", "contained"}:
            return "attention_required"
        if contribution_count > 0 and completion_status != "completed":
            return "attention_required"
        return "healthy"

    @staticmethod
    def _mission_runtime_state_status(
        *,
        mission_runtime_event: InternalEventEnvelope | None,
        first_event: InternalEventEnvelope,
    ) -> str:
        if first_event.mission_id is None:
            return "not_applicable"
        if mission_runtime_event is None:
            return "incomplete"
        required_fields = (
            "mission_id",
            "mission_goal",
            "mission_status",
            "continuity_action",
            "primary_route",
            "workflow_profile",
        )
        if any(mission_runtime_event.payload.get(field) in {None, ""} for field in required_fields):
            return "attention_required"
        continuity_source = mission_runtime_event.payload.get("continuity_source")
        continuity_target_mission_id = mission_runtime_event.payload.get(
            "continuity_target_mission_id"
        )
        if continuity_source == "related_mission" and continuity_target_mission_id is None:
            return "attention_required"
        if mission_runtime_event.payload.get("active_task_count") is None:
            return "attention_required"
        if mission_runtime_event.payload.get("open_loop_count") is None:
            return "attention_required"
        return "healthy"

    @staticmethod
    def _memory_causality_status(
        *,
        response_event: InternalEventEnvelope | None,
        shared_memory_event: InternalEventEnvelope | None,
    ) -> str:
        if response_event is None and shared_memory_event is None:
            return "not_applicable"
        response_payload = response_event.payload if response_event else {}
        shared_payload = shared_memory_event.payload if shared_memory_event else {}
        semantic_available = bool(response_payload.get("semantic_memory_available"))
        procedural_available = bool(response_payload.get("procedural_memory_available"))
        semantic_focus = [
            str(item) for item in response_payload.get("semantic_memory_focus", [])
        ]
        procedural_hint = response_payload.get("procedural_memory_hint")
        semantic_source = response_payload.get("semantic_memory_source")
        procedural_source = response_payload.get("procedural_memory_source")
        semantic_effects = list(response_payload.get("semantic_memory_effects", []))
        procedural_effects = list(response_payload.get("procedural_memory_effects", []))
        memory_lifecycle_status = response_payload.get("memory_lifecycle_status")
        semantic_specialists = shared_payload.get("semantic_memory_specialists", [])
        procedural_specialists = shared_payload.get("procedural_memory_specialists", [])
        if semantic_focus and not semantic_available:
            return "attention_required"
        if procedural_hint and not procedural_available:
            return "attention_required"
        if semantic_source is not None and "framing" not in semantic_effects:
            return "attention_required"
        if procedural_source is not None and "next_action" not in procedural_effects:
            return "attention_required"
        if memory_lifecycle_status == "review_recommended" and not (
            semantic_source or procedural_source
        ):
            return "attention_required"
        if semantic_focus or procedural_hint or semantic_source or procedural_source:
            return "causal_guidance"
        if (
            semantic_available
            or procedural_available
            or semantic_specialists
            or procedural_specialists
        ):
            return "attached_only"
        return "not_applicable"

    @staticmethod
    def _mind_domain_specialist_chain_status(
        *,
        response_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
        mind_domain_specialist_status: str,
    ) -> str:
        for event in (response_event, specialist_selection_event, specialist_domain_event):
            if event is None:
                continue
            status = event.payload.get("mind_domain_specialist_chain_status")
            if status is not None:
                return str(status)
        return mind_domain_specialist_status

    @staticmethod
    def _mind_domain_specialist_chain(
        *,
        response_event: InternalEventEnvelope | None,
        operation_dispatched_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
        primary_mind: str | None,
        primary_domain_driver: str | None,
        primary_route: str | None,
    ) -> str | None:
        for event in (
            response_event,
            operation_dispatched_event,
            specialist_selection_event,
            specialist_domain_event,
        ):
            if event is None:
                continue
            chain = event.payload.get("mind_domain_specialist_chain")
            if chain is not None:
                return str(chain)
        if primary_mind is None and primary_domain_driver is None and primary_route is None:
            return None
        selected_specialists = (
            specialist_selection_event.payload.get("domain_specialists", [])
            if specialist_selection_event
            else []
        )
        return (
            f"{primary_mind or 'none'} -> {primary_domain_driver or 'none'} -> "
            f"{primary_route or 'none'} -> specialists[{','.join(selected_specialists) or 'none'}]"
        )

    @staticmethod
    def _mind_domain_specialist_mismatch_flags(
        *,
        workflow_composed_event: InternalEventEnvelope | None,
        operation_dispatched_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
    ) -> list[str]:
        contract_source = (
            response_event
            or operation_dispatched_event
            or workflow_composed_event
            or specialist_domain_event
            or specialist_selection_event
        )
        if contract_source is None:
            return []
        contract_status = contract_source.payload.get(
            "mind_domain_specialist_contract_status"
        )
        if contract_status in {None, "not_applicable"}:
            return []

        authoritative_specialist = contract_source.payload.get(
            "mind_domain_specialist_active_specialist"
        )
        consumer_mode = (
            response_event.payload.get("mind_domain_specialist_consumer_mode")
            if response_event is not None
            else (
                operation_dispatched_event.payload.get(
                    "mind_domain_specialist_consumer_mode"
                )
                if operation_dispatched_event is not None
                else (
                    workflow_composed_event.payload.get(
                        "mind_domain_specialist_consumer_mode"
                    )
                    if workflow_composed_event is not None
                    else None
                )
            )
        )
        framing_mode = (
            response_event.payload.get("mind_domain_specialist_framing_mode")
            if response_event is not None
            else (
                operation_dispatched_event.payload.get(
                    "mind_domain_specialist_framing_mode"
                )
                if operation_dispatched_event is not None
                else None
            )
        )
        dispatch_specialists = [
            str(item)
            for item in (
                operation_dispatched_event.payload.get("specialist_hints", [])
                if operation_dispatched_event is not None
                else []
            )
            if item
        ]
        completed_specialists = [
            str(item)
            for item in (
                specialist_domain_event.payload.get("domain_specialists", [])
                if specialist_domain_event is not None
                else (
                    specialist_selection_event.payload.get("domain_specialists", [])
                    if specialist_selection_event is not None
                    else []
                )
            )
            if item
        ]

        flags: list[str] = []
        if contract_status == "governed_fallback":
            if consumer_mode not in {None, "core_only_fallback"}:
                flags.append("fallback_consumer_mode_mismatch")
            if framing_mode not in {None, "core_only_governed_fallback"}:
                flags.append("fallback_framing_mode_mismatch")
            if dispatch_specialists:
                flags.append("fallback_dispatched_specialist")
            return flags

        if authoritative_specialist is None:
            flags.append("authoritative_specialist_missing")
            return flags
        if dispatch_specialists and authoritative_specialist not in dispatch_specialists:
            flags.append("dispatch_specialist_mismatch")
        if completed_specialists and authoritative_specialist not in completed_specialists:
            flags.append("completed_specialist_mismatch")

        expected_consumer_mode = {
            "authoritative_chain": "authoritative_specialist",
            "bounded_override": "bounded_override_specialist",
            "bounded_degradation": "degraded_specialist",
        }.get(str(contract_status))
        if expected_consumer_mode is not None and consumer_mode not in {
            None,
            expected_consumer_mode,
        }:
            flags.append("consumer_mode_mismatch")

        expected_framing_mode = {
            "authoritative_chain": "route_and_specialist_locked",
            "bounded_override": "override_bounded_to_active_specialist",
            "bounded_degradation": "core_mediated_degraded_specialist",
        }.get(str(contract_status))
        if expected_framing_mode is not None and framing_mode not in {
            None,
            expected_framing_mode,
        }:
            flags.append("framing_mode_mismatch")
        return flags

    @staticmethod
    def _mind_domain_specialist_effectiveness(
        *,
        mind_domain_specialist_status: str,
        mind_domain_specialist_chain_status: str,
        mind_domain_specialist_mismatch_flags: list[str],
        workflow_composed_event: InternalEventEnvelope | None,
        response_event: InternalEventEnvelope | None,
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
    ) -> str:
        if (
            workflow_composed_event is None
            and response_event is None
            and specialist_selection_event is None
            and specialist_domain_event is None
        ):
            return "not_applicable"
        contract_evidence = any(
            event is not None
            and event.payload.get("mind_domain_specialist_contract_status") is not None
            for event in (
                workflow_composed_event,
                response_event,
                specialist_selection_event,
                specialist_domain_event,
            )
        )
        if not contract_evidence:
            return "not_applicable"
        if mind_domain_specialist_status == "not_applicable":
            return "not_applicable"
        if mind_domain_specialist_status == "incomplete" or mind_domain_specialist_chain_status in {
            "incomplete",
            "evidence_partial",
        }:
            return "incomplete"
        if mind_domain_specialist_mismatch_flags:
            return "insufficient"
        if mind_domain_specialist_status in {"mismatch", "attention_required"}:
            return "insufficient"
        if mind_domain_specialist_chain_status in {"mismatch", "attention_required"}:
            return "insufficient"
        if (
            mind_domain_specialist_status == "aligned"
            and mind_domain_specialist_chain_status == "aligned"
        ):
            return "effective"
        return "incomplete"

    @staticmethod
    def _memory_alignment_status(
        *,
        shared_memory_event: InternalEventEnvelope | None,
    ) -> str:
        if shared_memory_event is None:
            return "incomplete"
        sharing_modes = shared_memory_event.payload.get("sharing_modes", {})
        if not sharing_modes:
            return "partial"
        class_policies = shared_memory_event.payload.get("memory_class_policies", {})
        consumed_memory_classes = shared_memory_event.payload.get("consumed_memory_classes", {})
        memory_write_policies = shared_memory_event.payload.get("memory_write_policies", {})
        memory_refs_by_specialist = shared_memory_event.payload.get("memory_refs_by_specialist", {})
        semantic_focus_by_specialist = shared_memory_event.payload.get("semantic_focus_by_specialist", {})
        semantic_memory_states = shared_memory_event.payload.get("semantic_memory_states", {})
        procedural_memory_states = shared_memory_event.payload.get(
            "procedural_memory_states",
            {},
        )
        memory_consolidation_statuses = shared_memory_event.payload.get(
            "memory_consolidation_statuses",
            {},
        )
        memory_fixation_statuses = shared_memory_event.payload.get(
            "memory_fixation_statuses",
            {},
        )
        memory_archive_statuses = shared_memory_event.payload.get(
            "memory_archive_statuses",
            {},
        )
        domain_mission_link_reasons = shared_memory_event.payload.get(
            "domain_mission_link_reasons",
            {},
        )
        consumer_modes = shared_memory_event.payload.get("consumer_modes", {})
        consumer_profiles = shared_memory_event.payload.get("consumer_profiles", {})
        consumer_objectives = shared_memory_event.payload.get("consumer_objectives", {})
        expected_deliverables = shared_memory_event.payload.get("expected_deliverables", {})
        telemetry_focus = shared_memory_event.payload.get("telemetry_focus", {})
        if not class_policies:
            return "partial"
        for specialist_type, sharing_mode in sharing_modes.items():
            if sharing_mode != "core_mediated_read_only":
                return "attention_required"
            policies = class_policies.get(specialist_type, {})
            if not policies:
                return "attention_required"
            consumed = set(consumed_memory_classes.get(specialist_type, []))
            if not consumed:
                consumed = set(policies)
            if not consumed:
                return "attention_required"
            if domain_mission_link_reasons and not domain_mission_link_reasons.get(specialist_type):
                return "attention_required"
            write_policies = memory_write_policies.get(specialist_type, {})
            consumer_mode = consumer_modes.get(specialist_type)
            memory_refs = memory_refs_by_specialist.get(specialist_type, [])
            semantic_focus = semantic_focus_by_specialist.get(specialist_type, [])
            consolidation_status = memory_consolidation_statuses.get(
                specialist_type,
                "not_applicable",
            )
            fixation_status = memory_fixation_statuses.get(
                specialist_type,
                "not_applicable",
            )
            archive_status = memory_archive_statuses.get(
                specialist_type,
                "not_applicable",
            )
            if consumer_mode == "domain_guided_memory_packet":
                if not consumer_profiles.get(specialist_type):
                    return "attention_required"
                if not consumer_objectives.get(specialist_type):
                    return "attention_required"
                if not expected_deliverables.get(specialist_type):
                    return "attention_required"
                if not telemetry_focus.get(specialist_type):
                    return "attention_required"
            elif {"semantic", "procedural"}.intersection(consumed):
                return "attention_required"
            for policy in policies.values():
                if not isinstance(policy, dict):
                    return "attention_required"
                if policy.get("specialist_shared") is not True:
                    return "attention_required"
                if policy.get("sharing_mode") != "core_mediated_read_only":
                    return "attention_required"
                if policy.get("write_policy") != "through_core_only":
                    return "attention_required"
            if consumed_memory_classes and consumed != set(policies):
                return "attention_required"
            for memory_class_name in consumed:
                if write_policies and write_policies.get(memory_class_name) != "through_core_only":
                    return "attention_required"
            if "semantic" in consumed:
                if semantic_memory_states.get(specialist_type) not in {
                    "fixed",
                    "operational",
                    "archivable",
                }:
                    return "attention_required"
                if not any(str(ref).startswith("memory://semantic") for ref in memory_refs):
                    return "attention_required"
                if not semantic_focus:
                    return "attention_required"
            if "procedural" in consumed and procedural_memory_states.get(specialist_type) not in {
                "fixed",
                "operational",
                "archivable",
            }:
                return "attention_required"
            if "procedural" in consumed and not any(
                str(ref).startswith("memory://procedural") for ref in memory_refs
            ):
                return "attention_required"
            if archive_status == "archive_candidate" and {"semantic", "procedural"}.intersection(
                consumed
            ):
                return "attention_required"
            if (
                shared_memory_event.payload.get("memory_review_statuses", {}).get(
                    specialist_type
                )
                == "review_recommended"
                and "procedural" in consumed
                and procedural_memory_states.get(specialist_type) != "fixed"
            ):
                return "attention_required"
            if consolidation_status not in {
                "in_progress",
                "consolidated",
                "revisit_before_reuse",
                "not_applicable",
            }:
                return "attention_required"
            if fixation_status not in {"fixed", "not_fixed", "not_applicable"}:
                return "attention_required"
            if archive_status not in {
                "archive_candidate",
                "active_memory",
                "not_applicable",
            }:
                return "attention_required"
            if archive_status == "archive_candidate" and not any(
                item == "review_recommended"
                for item in (
                    shared_memory_event.payload.get("memory_review_statuses", {})
                    .values()
                )
            ):
                return "attention_required"
        return "healthy"

    @staticmethod
    def _lifecycle_support_status(
        *,
        response_event: InternalEventEnvelope | None,
        plan_event: InternalEventEnvelope | None,
        shared_memory_event: InternalEventEnvelope | None,
        field_name: str,
        map_name: str,
        priority_order: tuple[str, ...],
    ) -> str:
        for event in (response_event, plan_event):
            if event is None:
                continue
            value = event.payload.get(field_name)
            if value is not None:
                return str(value)
        if shared_memory_event is None:
            return "not_applicable"
        values = [
            str(item)
            for item in (
                shared_memory_event.payload.get(map_name, {}).values()
                if isinstance(shared_memory_event.payload.get(map_name, {}), dict)
                else []
            )
            if item is not None
        ]
        if not values:
            return "not_applicable"
        for candidate in priority_order:
            if candidate in values:
                return candidate
        return values[0]

    @staticmethod
    def _memory_corpus_signals(
        *,
        shared_memory_event: InternalEventEnvelope | None,
    ) -> tuple[str, str | None]:
        if shared_memory_event is None:
            return "not_applicable", None
        payload = shared_memory_event.payload
        corpus_statuses = payload.get("memory_corpus_statuses", {})
        retention_pressures = payload.get("memory_retention_pressures", {})
        statuses = [
            str(item)
            for item in (corpus_statuses.values() if isinstance(corpus_statuses, dict) else [])
            if item is not None
        ]
        pressures = [
            str(item)
            for item in (
                retention_pressures.values()
                if isinstance(retention_pressures, dict)
                else []
            )
            if item is not None
        ]
        if not statuses:
            return "not_applicable", None
        if "review_recommended" in statuses:
            status = "review_recommended"
        elif "monitor" in statuses:
            status = "monitor"
        else:
            status = "stable"
        if "high" in pressures:
            pressure = "high"
        elif "moderate" in pressures:
            pressure = "moderate"
        elif "low" in pressures:
            pressure = "low"
        else:
            pressure = None
        return status, pressure

    @staticmethod
    def _user_scope_status(
        *,
        memory_recovered_event: InternalEventEnvelope | None,
        memory_recorded_event: InternalEventEnvelope | None,
    ) -> str:
        statuses = [
            str(event.payload.get("user_scope_status"))
            for event in (memory_recovered_event, memory_recorded_event)
            if event is not None and event.payload.get("user_scope_status") is not None
        ]
        if not statuses:
            return "incomplete"
        if all(status == "not_applicable" for status in statuses):
            return "not_applicable"
        if "recoverable" in statuses:
            return "recoverable"
        if any(status in {"seeded", "tracked_only"} for status in statuses):
            return "emerging"
        return "partial"

    @staticmethod
    def _organization_scope_status(
        *,
        memory_recovered_event: InternalEventEnvelope | None,
        memory_recorded_event: InternalEventEnvelope | None,
    ) -> str:
        statuses = [
            str(event.payload.get("organization_scope_status"))
            for event in (memory_recovered_event, memory_recorded_event)
            if event is not None and event.payload.get("organization_scope_status") is not None
        ]
        if not statuses:
            return "incomplete"
        if any(status == "no_go_without_canonical_consumer" for status in statuses):
            return "no_go_without_canonical_consumer"
        if all(status == "not_applicable" for status in statuses):
            return "not_applicable"
        return "attention_required"

    @staticmethod
    def _specialist_recurrence_status(
        *,
        shared_memory_event: InternalEventEnvelope | None,
    ) -> str:
        if shared_memory_event is None:
            return "incomplete"
        guided_specialists = [
            str(item)
            for item in shared_memory_event.payload.get("guided_specialists", [])
            if item
        ]
        status_map = shared_memory_event.payload.get("recurrent_context_statuses", {})
        if not guided_specialists:
            return "not_applicable"
        statuses = [
            str(status_map.get(item))
            for item in guided_specialists
            if status_map.get(item) is not None
        ]
        if not statuses:
            return "incomplete"
        if any(status == "recoverable" for status in statuses):
            return "recoverable"
        if any(status == "seeded" for status in statuses):
            return "emerging"
        if all(status == "not_applicable" for status in statuses):
            return "not_applicable"
        return "partial"

    @staticmethod
    def _specialist_sovereignty_status(
        *,
        specialist_contract_event: InternalEventEnvelope | None,
    ) -> str:
        if specialist_contract_event is None:
            return "incomplete"
        response_channel = specialist_contract_event.payload.get("response_channel")
        tool_access_mode = specialist_contract_event.payload.get("tool_access_mode")
        if response_channel == "through_core" and tool_access_mode == "none":
            return "healthy"
        return "attention_required"

    @staticmethod
    def _build_agentic_adapter() -> AgenticObservabilityAdapter | None:
        tracing_enabled = getenv("LANGSMITH_TRACING", "false").lower() == "true"
        if not tracing_enabled:
            return None
        project_name = getenv("LANGSMITH_PROJECT", "jarvis-v1")
        endpoint = getenv("LANGSMITH_ENDPOINT")
        workspace_id = getenv("LANGSMITH_WORKSPACE_ID")
        if getenv("LANGSMITH_API_KEY"):
            try:
                return LangSmithObservabilityAdapter(
                    project_name=project_name,
                    endpoint=endpoint,
                    workspace_id=workspace_id,
                )
            except Exception:
                pass
        mirror_path = getenv("JARVIS_AGENTIC_MIRROR_PATH")
        resolved = (
            Path(mirror_path)
            if mirror_path
            else Path.cwd() / ".jarvis_runtime" / "agentic_observability.jsonl"
        )
        return JsonlAgenticMirrorAdapter(resolved)
