"""Orchestrator flow integrating engines, persistence, and observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from cognitive_engine.engine import CognitiveEngine
from executive_engine.engine import ExecutiveDirective, ExecutiveEngine
from governance_service.service import GovernanceService
from identity_engine.engine import IdentityEngine
from knowledge_service.service import KnowledgeRetrievalResult, KnowledgeService
from memory_service.service import MemoryRecoveryResult, MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from planning_engine.engine import PlanningContext, PlanningEngine
from specialist_engine.engine import SpecialistEngine, SpecialistHandoffPlan, SpecialistReview
from synthesis_engine.engine import SynthesisEngine, SynthesisInput, SynthesisResult

from shared.contracts import (
    ArtifactResultContract,
    ContinuityPauseContract,
    ContinuityReplayContract,
    DeliberativePlanContract,
    EcosystemOperationalStateContract,
    GovernanceCheckContract,
    GovernanceDecisionContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    MissionRuntimeStateContract,
    OperationDispatchContract,
    OperationResultContract,
    SpecialistInvocationContract,
)
from shared.domain_registry import (
    primary_canonical_domain_for_name,
    primary_route_payload,
    promoted_specialist_route_payloads,
    resolve_primary_route,
    resolve_workflow_route,
    route_linked_specialist_type,
    route_metadata_payload,
    specialist_route_payload,
    workflow_runtime_guidance,
)
from shared.events import InternalEventEnvelope
from shared.mind_domain_specialist_contract import (
    build_mind_domain_specialist_runtime_policy,
)
from shared.types import MissionStatus, OperationId, PermissionDecision, RequestId


@dataclass
class OrchestratorResponse:
    """Structured result of the orchestrated v1 request flow."""

    request_id: str
    session_id: str
    intent: str
    response_text: str
    directive: ExecutiveDirective
    deliberative_plan: DeliberativePlanContract
    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract
    memory_recovery: MemoryRecoveryContract
    memory_record: MemoryRecordContract
    recovered_context: list[str]
    knowledge_result: KnowledgeRetrievalResult | None = None
    artifact_results: list[ArtifactResultContract] = field(default_factory=list)
    active_minds: list[str] = field(default_factory=list)
    active_domains: list[str] = field(default_factory=list)
    cognitive_tensions: list[str] = field(default_factory=list)
    specialist_hints: list[str] = field(default_factory=list)
    specialist_invocations: list[SpecialistInvocationContract] = field(default_factory=list)
    specialist_boundary_summary: str | None = None
    mission_runtime_state: MissionRuntimeStateContract | None = None
    specialist_handoff_check: GovernanceCheckContract | None = None
    specialist_handoff_decision: GovernanceDecisionContract | None = None
    specialist_review: SpecialistReview | None = None
    operation_dispatch: OperationDispatchContract | None = None
    operation_result: OperationResultContract | None = None
    events: list[InternalEventEnvelope] = field(default_factory=list)


@dataclass
class ContinuitySubflowResult:
    """Structured result of the native continuity/runtime prelude."""

    memory_recovery_result: MemoryRecoveryResult
    continuity_replay: ContinuityReplayContract | None
    resolved_pause: ContinuityPauseContract | None
    events: list[InternalEventEnvelope]


class OrchestratorService:
    """Coordinate the current v1 flow across services and engines."""

    name = "orchestrator-service"

    def __init__(
        self,
        governance_service: GovernanceService | None = None,
        memory_service: MemoryService | None = None,
        operational_service: OperationalService | None = None,
        knowledge_service: KnowledgeService | None = None,
        observability_service: ObservabilityService | None = None,
        identity_engine: IdentityEngine | None = None,
        executive_engine: ExecutiveEngine | None = None,
        planning_engine: PlanningEngine | None = None,
        cognitive_engine: CognitiveEngine | None = None,
        specialist_engine: SpecialistEngine | None = None,
        synthesis_engine: SynthesisEngine | None = None,
    ) -> None:
        self.governance_service = governance_service or GovernanceService()
        self.memory_service = memory_service or MemoryService()
        self.operational_service = operational_service or OperationalService()
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.observability_service = observability_service or ObservabilityService()
        self.identity_engine = identity_engine or IdentityEngine()
        self.executive_engine = executive_engine or ExecutiveEngine()
        self.planning_engine = planning_engine or PlanningEngine()
        self.cognitive_engine = cognitive_engine or CognitiveEngine()
        self.specialist_engine = specialist_engine or SpecialistEngine()
        self.synthesis_engine = synthesis_engine or SynthesisEngine()

    def handle_input(self, contract: InputContract) -> OrchestratorResponse:
        """Execute the orchestrated flow for a normalized input contract."""

        events = [
            self.make_event(
                "input_received",
                contract,
                {"content": contract.content, "channel": contract.channel.value},
            )
        ]
        continuity_result = self._run_native_continuity_subflow(contract, events)
        events = continuity_result.events
        memory_recovery_result = continuity_result.memory_recovery_result

        directive = self.executive_engine.direct(contract)
        identity_profile = self.identity_engine.get_profile()
        identity_style_preview = self.identity_engine.build_response_style(
            intent=directive.intent,
            blocked=False,
        )
        events.append(self.make_event("intent_classified", contract, {"intent": directive.intent}))
        events.append(
            self.make_event(
                "directive_composed",
                contract,
                {
                    "intent": directive.intent,
                    "intent_confidence": directive.intent_confidence,
                    "requires_clarification": directive.requires_clarification,
                    "preferred_response_mode": directive.preferred_response_mode,
                    "dominant_goal": directive.dominant_goal,
                    "identity_mode": directive.identity_mode,
                    "identity_signature": identity_profile.identity_signature,
                    "identity_posture": identity_profile.posture,
                    "principle_focus": identity_profile.principle_focus,
                    "response_style_preview": identity_style_preview,
                },
            )
        )
        if directive.requires_clarification:
            events.append(
                self.make_event(
                    "clarification_required",
                    contract,
                    {
                        "intent": directive.intent,
                        "reason": directive.ambiguity_reason or "insufficient_goal_clarity",
                    },
                )
            )

        knowledge_result = None
        if directive.should_query_knowledge:
            knowledge_result = self.knowledge_service.retrieve_for_intent(
                intent=directive.intent,
                query=contract.content,
            )
            events.append(
                self.make_event(
                    "knowledge_retrieved",
                    contract,
                    {
                        "domains": knowledge_result.active_domains,
                        "registry_domains": knowledge_result.registry_domains,
                        "routed_specialists": [
                            {
                                "domain_name": route.domain_name,
                                "specialist_type": route.specialist_type,
                                "specialist_mode": route.specialist_mode,
                                "canonical_domain_refs": route.canonical_domain_refs,
                                "routing_source": route.routing_source,
                            }
                            for route in knowledge_result.specialist_routes
                        ],
                        "sources": knowledge_result.sources,
                    },
                )
            )
            events.append(
                self.make_event(
                    "domain_registry_resolved",
                    contract,
                    self._domain_registry_event_payload(knowledge_result),
                )
            )

        memory_route_guidance = self._memory_route_guidance(
            active_domains=knowledge_result.active_domains if knowledge_result else [],
            recovered_context=memory_recovery_result.recovered_items,
        )
        cognitive_snapshot = self.cognitive_engine.build_snapshot(
            intent=directive.intent,
            risk_markers=directive.risk_markers,
            retrieved_domains=knowledge_result.active_domains if knowledge_result else [],
            domain_specialist_routes=(
                knowledge_result.specialist_routes if knowledge_result else []
            ),
            mind_hints=directive.mind_hints,
            memory_priority_domains=memory_route_guidance["prioritized_domains"],
            memory_specialist_hints=memory_route_guidance["prioritized_specialists"],
            memory_priority_sources=memory_route_guidance["sources"],
            memory_priority_summary=memory_route_guidance["summary"],
        )
        events.append(
            self.make_event(
                "context_composed",
                contract,
                {
                    "active_minds": cognitive_snapshot.active_minds,
                    "active_domains": cognitive_snapshot.active_domains,
                    "canonical_domains": cognitive_snapshot.canonical_domains,
                    "primary_mind": cognitive_snapshot.primary_mind,
                    "primary_mind_family": cognitive_snapshot.primary_mind_family,
                    "primary_domain_driver": cognitive_snapshot.primary_domain_driver,
                    "supporting_minds": cognitive_snapshot.supporting_minds,
                    "suppressed_minds": cognitive_snapshot.suppressed_minds,
                    "supporting_mind_limit": cognitive_snapshot.supporting_mind_limit,
                    "suppressed_mind_limit": cognitive_snapshot.suppressed_mind_limit,
                    "dominant_tension": cognitive_snapshot.dominant_tension,
                    "arbitration_summary": cognitive_snapshot.arbitration_summary,
                    "arbitration_source": cognitive_snapshot.arbitration_source,
                    "cognitive_recomposition_applied": (
                        cognitive_snapshot.recomposition_applied
                    ),
                    "cognitive_recomposition_reason": (
                        cognitive_snapshot.recomposition_reason
                    ),
                    "cognitive_recomposition_trigger": (
                        cognitive_snapshot.recomposition_trigger
                    ),
                    "specialist_hints": cognitive_snapshot.specialist_hints,
                    "mind_domain_specialist_contract_status": (
                        cognitive_snapshot.mind_domain_specialist_contract_status
                    ),
                    "mind_domain_specialist_contract_summary": (
                        cognitive_snapshot.mind_domain_specialist_contract_summary
                    ),
                    "mind_domain_specialist_contract_chain": (
                        cognitive_snapshot.mind_domain_specialist_contract_chain
                    ),
                    "mind_domain_specialist_active_specialist": (
                        cognitive_snapshot.mind_domain_specialist_active_specialist
                    ),
                    "mind_domain_specialist_override_mode": (
                        cognitive_snapshot.mind_domain_specialist_override_mode
                    ),
                    "mind_domain_specialist_fallback_mode": (
                        cognitive_snapshot.mind_domain_specialist_fallback_mode
                    ),
                    "memory_priority_applied": cognitive_snapshot.memory_priority_applied,
                    "memory_priority_domains": cognitive_snapshot.memory_priority_domains,
                    "memory_priority_specialist_hints": (
                        cognitive_snapshot.memory_priority_specialist_hints
                    ),
                    "memory_priority_sources": cognitive_snapshot.memory_priority_sources,
                    "memory_priority_summary": cognitive_snapshot.memory_priority_summary,
                },
            )
        )
        if cognitive_snapshot.recomposition_applied:
            events.append(
                self.make_event(
                    "cognitive_recomposition_applied",
                    contract,
                    {
                        "primary_mind": cognitive_snapshot.primary_mind,
                        "supporting_minds": cognitive_snapshot.supporting_minds,
                        "primary_domain_driver": cognitive_snapshot.primary_domain_driver,
                        "arbitration_source": cognitive_snapshot.arbitration_source,
                        "cognitive_recomposition_reason": (
                            cognitive_snapshot.recomposition_reason
                        ),
                        "cognitive_recomposition_trigger": (
                            cognitive_snapshot.recomposition_trigger
                        ),
                    },
                )
            )

        deliberative_plan = self.planning_engine.build_task_plan(
            self._build_planning_context(
                contract,
                directive=directive,
                memory_recovery_result=memory_recovery_result,
                cognitive_snapshot=cognitive_snapshot,
                knowledge_result=knowledge_result,
                memory_route_guidance=memory_route_guidance,
            )
        )
        events.append(
            self.make_event(
                "plan_built",
                contract,
                {
                    "contract_validation_status": (
                        deliberative_plan.contract_validation_status
                    ),
                    "contract_validation_errors": (
                        deliberative_plan.contract_validation_errors
                    ),
                    "contract_validation_retry_applied": (
                        deliberative_plan.contract_validation_retry_applied
                    ),
                    "recommended_task_type": deliberative_plan.recommended_task_type,
                    "requires_human_validation": deliberative_plan.requires_human_validation,
                    "steps": deliberative_plan.steps,
                    "dominant_tension": deliberative_plan.dominant_tension,
                    "smallest_safe_next_action": deliberative_plan.smallest_safe_next_action,
                    "metacognitive_guidance_applied": (
                        deliberative_plan.metacognitive_guidance_applied
                    ),
                    "metacognitive_guidance_summary": (
                        deliberative_plan.metacognitive_guidance_summary
                    ),
                    "metacognitive_effects": deliberative_plan.metacognitive_effects,
                    "metacognitive_containment_recommendation": (
                        deliberative_plan.metacognitive_containment_recommendation
                    ),
                    "mind_disagreement_status": deliberative_plan.mind_disagreement_status,
                    "mind_validation_checkpoints": (
                        deliberative_plan.mind_validation_checkpoints
                    ),
                    **self._memory_maintenance_event_payload(
                        deliberative_plan=deliberative_plan
                    ),
                    **self._capability_decision_event_payload(deliberative_plan),
                    **self._request_identity_policy_payload(deliberative_plan),
                    "adaptive_intervention_status": (
                        deliberative_plan.adaptive_intervention_status
                    ),
                    "adaptive_intervention_reason": (
                        deliberative_plan.adaptive_intervention_reason
                    ),
                    "adaptive_intervention_trigger": (
                        deliberative_plan.adaptive_intervention_trigger
                    ),
                    "adaptive_intervention_selected_action": (
                        deliberative_plan.adaptive_intervention_selected_action
                    ),
                    "adaptive_intervention_expected_effect": (
                        deliberative_plan.adaptive_intervention_expected_effect
                    ),
                    "adaptive_intervention_effects": (
                        deliberative_plan.adaptive_intervention_effects
                    ),
                    "cognitive_strategy_shift_applied": (
                        deliberative_plan.cognitive_strategy_shift_applied
                    ),
                    "cognitive_strategy_shift_summary": (
                        deliberative_plan.cognitive_strategy_shift_summary
                    ),
                    "cognitive_strategy_shift_trigger": (
                        deliberative_plan.cognitive_strategy_shift_trigger
                    ),
                    "cognitive_strategy_shift_effects": (
                        deliberative_plan.cognitive_strategy_shift_effects
                    ),
                    "primary_mind": deliberative_plan.primary_mind,
                    "primary_mind_family": deliberative_plan.primary_mind_family,
                    "primary_domain_driver": deliberative_plan.primary_domain_driver,
                    "arbitration_source": deliberative_plan.arbitration_source,
                    "cognitive_recomposition_applied": (
                        cognitive_snapshot.recomposition_applied
                    ),
                    "cognitive_recomposition_reason": (
                        cognitive_snapshot.recomposition_reason
                    ),
                    "cognitive_recomposition_trigger": (
                        cognitive_snapshot.recomposition_trigger
                    ),
                    "primary_route": deliberative_plan.primary_route,
                    "primary_canonical_domain": deliberative_plan.primary_canonical_domain,
                    "semantic_memory_source": deliberative_plan.semantic_memory_source,
                    "procedural_memory_source": deliberative_plan.procedural_memory_source,
                    "semantic_memory_effects": deliberative_plan.semantic_memory_effects,
                    "procedural_memory_effects": deliberative_plan.procedural_memory_effects,
                    "semantic_memory_lifecycle": (
                        deliberative_plan.semantic_memory_lifecycle
                    ),
                    "procedural_memory_lifecycle": (
                        deliberative_plan.procedural_memory_lifecycle
                    ),
                    "semantic_memory_state": deliberative_plan.semantic_memory_state,
                    "procedural_memory_state": deliberative_plan.procedural_memory_state,
                    "memory_lifecycle_status": deliberative_plan.memory_lifecycle_status,
                    "memory_review_status": deliberative_plan.memory_review_status,
                    "memory_consolidation_status": (
                        deliberative_plan.memory_consolidation_status
                    ),
                    "memory_fixation_status": deliberative_plan.memory_fixation_status,
                    "memory_archive_status": deliberative_plan.memory_archive_status,
                    "procedural_artifact_status": (
                        deliberative_plan.procedural_artifact_status
                    ),
                    "procedural_artifact_ref": deliberative_plan.procedural_artifact_ref,
                    "procedural_artifact_version": (
                        deliberative_plan.procedural_artifact_version
                    ),
                    "procedural_artifact_summary": (
                        deliberative_plan.procedural_artifact_summary
                    ),
                    "mind_domain_specialist_chain": (
                        f"{deliberative_plan.primary_mind or 'none'} -> "
                        f"{deliberative_plan.primary_domain_driver or 'none'} -> "
                        f"{deliberative_plan.primary_route or 'none'}"
                    ),
                    **self._mind_domain_specialist_contract_payload(
                        deliberative_plan
                    ),
                    "specialist_hints": deliberative_plan.specialist_hints,
                    "continuity_action": deliberative_plan.continuity_action,
                    "continuity_source": deliberative_plan.continuity_source,
                    "continuity_reason": deliberative_plan.continuity_reason,
                },
            )
        )
        events.append(
            self.make_event(
                "continuity_decided",
                contract,
                {
                    "continuity_action": deliberative_plan.continuity_action,
                    "continuity_source": deliberative_plan.continuity_source,
                    "continuity_target_mission_id": (
                        str(deliberative_plan.continuity_target_mission_id)
                        if deliberative_plan.continuity_target_mission_id
                        else None
                    ),
                    "continuity_target_goal": deliberative_plan.continuity_target_goal,
                    "continuity_reason": deliberative_plan.continuity_reason,
                },
            )
        )

        specialist_handoff_plan, events = self._plan_specialist_handoffs(
            contract,
            directive=directive,
            deliberative_plan=deliberative_plan,
            memory_recovery_result=memory_recovery_result,
            knowledge_result=knowledge_result,
            events=events,
        )
        specialist_handoff_assessment, events = self._govern_specialist_handoffs(
            contract,
            deliberative_plan=deliberative_plan,
            handoff_plan=specialist_handoff_plan,
            events=events,
        )
        specialist_review, deliberative_plan, events = self._execute_specialist_handoffs(
            contract,
            directive=directive,
            deliberative_plan=deliberative_plan,
            knowledge_result=knowledge_result,
            handoff_plan=specialist_handoff_plan,
            handoff_governance=(specialist_handoff_assessment.governance_decision),
            events=events,
        )
        mission_runtime_state, events = self._declare_mission_runtime_state(
            contract,
            deliberative_plan=deliberative_plan,
            memory_recovery_result=memory_recovery_result,
            specialist_review=specialist_review,
            events=events,
            runtime_mode="native_pipeline",
        )

        assessment = self.governance_service.assess_request(
            contract,
            intent=directive.intent,
            requested_by_service=self.name,
            plan=deliberative_plan,
            identity_mode=directive.identity_mode,
            identity_signature=identity_profile.identity_signature,
            response_style=identity_style_preview,
        )
        governance_check = assessment.governance_check
        governance_decision = assessment.governance_decision
        final_response_style = self.identity_engine.build_response_style(
            intent=directive.intent,
            blocked=governance_decision.decision
            in {
                PermissionDecision.BLOCK,
                PermissionDecision.DEFER_FOR_VALIDATION,
            },
        )
        events.append(
            self.make_event(
                "governance_checked",
                contract,
                {
                    "governance_check_id": str(governance_check.governance_check_id),
                    "risk_hint": governance_check.risk_hint.value
                    if governance_check.risk_hint
                    else None,
                    "decision": governance_decision.decision.value,
                    **self._request_identity_policy_payload(deliberative_plan),
                },
            )
        )
        events.append(
            self.make_event(
                "plan_governed",
                contract,
                {
                    "governance_check_id": str(governance_check.governance_check_id),
                    "proposed_effect": governance_check.proposed_effect,
                    "decision": governance_decision.decision.value,
                    "decision_frame": governance_check.decision_frame,
                    "identity_mode": directive.identity_mode,
                    "identity_signature": identity_profile.identity_signature,
                    "response_style": final_response_style,
                    "identity_guardrail": governance_check.context.get("identity_guardrail"),
                    **self._capability_decision_event_payload(
                        deliberative_plan,
                        authorization_status=self._resolve_capability_authorization_status(
                            plan=deliberative_plan,
                            governance_decision=governance_decision,
                            specialist_handoff_decision=(
                                specialist_handoff_assessment.governance_decision
                            ),
                        ),
                    ),
                    **self._request_identity_policy_payload(deliberative_plan),
                },
            )
        )

        operation_dispatch = None
        operation_result = None
        artifact_results: list[ArtifactResultContract] = []
        if (
            governance_decision.decision
            in {
                PermissionDecision.ALLOW,
                PermissionDecision.ALLOW_WITH_CONDITIONS,
            }
            and directive.should_execute_operation
            and self._capability_allows_operation(deliberative_plan)
        ):
            capability_authorization_status = self._resolve_capability_authorization_status(
                plan=deliberative_plan,
                governance_decision=governance_decision,
                specialist_handoff_decision=specialist_handoff_assessment.governance_decision,
            )
            operation_dispatch = self.build_operation_dispatch(
                contract,
                plan=deliberative_plan,
                specialist_review=specialist_review,
                mission_runtime_state=mission_runtime_state,
                authorization_status=capability_authorization_status,
            )
            events.append(
                self.make_event(
                    "workflow_composed",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
                        "workflow_expected_deliverables": (
                            operation_dispatch.workflow_expected_deliverables
                        ),
                        "workflow_telemetry_focus": (
                            operation_dispatch.workflow_telemetry_focus
                        ),
                        "workflow_success_focus": operation_dispatch.workflow_success_focus,
                        "workflow_response_focus": operation_dispatch.workflow_response_focus,
                        "workflow_state": operation_dispatch.workflow_state,
                        "workflow_governance_mode": operation_dispatch.workflow_governance_mode,
                        "workflow_steps": operation_dispatch.workflow_steps,
                        "workflow_checkpoints": operation_dispatch.workflow_checkpoints,
                        "workflow_checkpoint_state": (
                            operation_dispatch.workflow_checkpoint_state
                        ),
                        "workflow_decision_points": operation_dispatch.workflow_decision_points,
                        "workflow_resume_point": operation_dispatch.workflow_resume_point,
                        "workflow_resume_status": operation_dispatch.workflow_resume_status,
                        "workflow_resume_eligible": (
                            operation_dispatch.workflow_resume_eligible
                        ),
                        **self._ecosystem_operational_state_payload(
                            operation_dispatch
                        ),
                        **self._capability_decision_event_payload(operation_dispatch),
                        **self._request_identity_policy_payload(operation_dispatch),
                        "adaptive_intervention_status": (
                            operation_dispatch.adaptive_intervention_status
                        ),
                        "adaptive_intervention_reason": (
                            operation_dispatch.adaptive_intervention_reason
                        ),
                        "adaptive_intervention_trigger": (
                            operation_dispatch.adaptive_intervention_trigger
                        ),
                        "adaptive_intervention_selected_action": (
                            operation_dispatch.adaptive_intervention_selected_action
                        ),
                        "adaptive_intervention_expected_effect": (
                            operation_dispatch.adaptive_intervention_expected_effect
                        ),
                        "adaptive_intervention_effects": (
                            operation_dispatch.adaptive_intervention_effects
                        ),
                        "task_type": operation_dispatch.task_type,
                        "domain_hints": operation_dispatch.domain_hints,
                        **self._mind_domain_specialist_contract_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
            events.append(
                self.make_event(
                    "ecosystem_state_declared",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        **self._ecosystem_operational_state_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
            events.append(
                self.make_event(
                    "workflow_governance_declared",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
                        "workflow_expected_deliverables": (
                            operation_dispatch.workflow_expected_deliverables
                        ),
                        "workflow_telemetry_focus": (
                            operation_dispatch.workflow_telemetry_focus
                        ),
                        "workflow_success_focus": operation_dispatch.workflow_success_focus,
                        "workflow_state": operation_dispatch.workflow_state,
                        "workflow_governance_mode": operation_dispatch.workflow_governance_mode,
                        "workflow_decision_points": operation_dispatch.workflow_decision_points,
                        "workflow_resume_status": operation_dispatch.workflow_resume_status,
                        "workflow_resume_point": operation_dispatch.workflow_resume_point,
                        **self._ecosystem_operational_state_payload(
                            operation_dispatch
                        ),
                        **self._capability_decision_event_payload(operation_dispatch),
                        **self._request_identity_policy_payload(operation_dispatch),
                        "adaptive_intervention_status": (
                            operation_dispatch.adaptive_intervention_status
                        ),
                        "adaptive_intervention_selected_action": (
                            operation_dispatch.adaptive_intervention_selected_action
                        ),
                        **self._mind_domain_specialist_contract_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
            events.append(
                self.make_event(
                    "operation_dispatched",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "task_type": operation_dispatch.task_type,
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
                        "workflow_expected_deliverables": (
                            operation_dispatch.workflow_expected_deliverables
                        ),
                        "workflow_telemetry_focus": (
                            operation_dispatch.workflow_telemetry_focus
                        ),
                        "workflow_success_focus": operation_dispatch.workflow_success_focus,
                        "workflow_response_focus": operation_dispatch.workflow_response_focus,
                        "workflow_state": "dispatched",
                        "workflow_steps": operation_dispatch.workflow_steps,
                        "workflow_checkpoint_state": (
                            operation_dispatch.workflow_checkpoint_state
                        ),
                        "workflow_decision_points": operation_dispatch.workflow_decision_points,
                        "workflow_resume_status": operation_dispatch.workflow_resume_status,
                        "workflow_resume_point": operation_dispatch.workflow_resume_point,
                        "workflow_resume_eligible": (
                            operation_dispatch.workflow_resume_eligible
                        ),
                        **self._ecosystem_operational_state_payload(
                            operation_dispatch
                        ),
                        **self._capability_decision_event_payload(operation_dispatch),
                        **self._request_identity_policy_payload(operation_dispatch),
                        "adaptive_intervention_status": (
                            operation_dispatch.adaptive_intervention_status
                        ),
                        "adaptive_intervention_reason": (
                            operation_dispatch.adaptive_intervention_reason
                        ),
                        "adaptive_intervention_trigger": (
                            operation_dispatch.adaptive_intervention_trigger
                        ),
                        "adaptive_intervention_selected_action": (
                            operation_dispatch.adaptive_intervention_selected_action
                        ),
                        "adaptive_intervention_expected_effect": (
                            operation_dispatch.adaptive_intervention_expected_effect
                        ),
                        "adaptive_intervention_effects": (
                            operation_dispatch.adaptive_intervention_effects
                        ),
                        "specialist_hints": operation_dispatch.specialist_hints,
                        **self._mind_domain_specialist_contract_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
            execution = self.operational_service.execute(operation_dispatch)
            operation_result = execution.operation_result
            artifact_results = execution.artifact_results
            events.append(
                self.make_event(
                    "operation_completed",
                    contract,
                    {
                        "operation_id": str(operation_result.operation_id),
                        "status": operation_result.status.value,
                        "artifacts": operation_result.artifacts,
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
                        "workflow_expected_deliverables": (
                            operation_dispatch.workflow_expected_deliverables
                        ),
                        "workflow_telemetry_focus": (
                            operation_dispatch.workflow_telemetry_focus
                        ),
                        "workflow_response_focus": operation_dispatch.workflow_response_focus,
                        "workflow_state": operation_result.workflow_state,
                        "workflow_checkpoints": operation_dispatch.workflow_checkpoints,
                        "workflow_checkpoint_state": (
                            operation_result.workflow_checkpoint_state
                        ),
                        "workflow_completed_steps": operation_result.workflow_completed_steps,
                        "workflow_pending_checkpoints": (
                            operation_result.workflow_pending_checkpoints
                        ),
                        "workflow_decisions": operation_result.workflow_decisions,
                        "workflow_resume_status": operation_result.workflow_resume_status,
                        "workflow_resume_point": operation_result.workflow_resume_point,
                        **self._ecosystem_operational_state_payload(
                            operation_result
                        ),
                        **self._mind_domain_specialist_contract_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
            events.append(
                self.make_event(
                    "workflow_completed",
                    contract,
                    {
                        "operation_id": str(operation_result.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
                        "workflow_expected_deliverables": (
                            operation_dispatch.workflow_expected_deliverables
                        ),
                        "workflow_telemetry_focus": (
                            operation_dispatch.workflow_telemetry_focus
                        ),
                        "workflow_success_focus": operation_dispatch.workflow_success_focus,
                        "workflow_response_focus": operation_dispatch.workflow_response_focus,
                        "workflow_state": operation_result.workflow_state,
                        "workflow_governance_mode": operation_dispatch.workflow_governance_mode,
                        "workflow_decision_points": operation_dispatch.workflow_decision_points,
                        "workflow_decisions": operation_result.workflow_decisions,
                        "status": operation_result.status.value,
                        "checkpoints": operation_result.checkpoints,
                        "workflow_checkpoint_state": (
                            operation_result.workflow_checkpoint_state
                        ),
                        "workflow_pending_checkpoints": (
                            operation_result.workflow_pending_checkpoints
                        ),
                        "workflow_resume_status": operation_result.workflow_resume_status,
                        "workflow_resume_point": operation_result.workflow_resume_point,
                        **self._ecosystem_operational_state_payload(
                            operation_result
                        ),
                        **self._mind_domain_specialist_contract_payload(
                            operation_dispatch
                        ),
                    },
                )
            )
        elif governance_decision.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            events.append(
                self.make_event(
                    "governance_blocked",
                    contract,
                    {
                        "decision_id": str(governance_decision.decision_id),
                        "justification": governance_decision.justification,
                    },
                )
            )

        guided_memory_runtime_hints = self._guided_memory_runtime_hints(
            specialist_review,
            deliberative_plan,
            memory_recovery_result.recovered_items,
        )
        chain_payload = self._mind_domain_specialist_chain_payload(
            deliberative_plan,
            planned_specialists=list(deliberative_plan.specialist_hints),
            selected_specialists=[
                contribution.specialist_type
                for contribution in specialist_review.contributions
            ],
            selected_domains=[
                invocation.linked_domain
                for invocation in specialist_review.invocations
                if invocation.linked_domain
            ],
        )
        synthesis_result = self._compose_response(
            directive=directive,
            governance_decision=governance_decision,
            memory_recovery_result=memory_recovery_result,
            cognitive_snapshot=cognitive_snapshot,
            knowledge_result=knowledge_result,
            deliberative_plan=deliberative_plan,
            specialist_review=specialist_review,
            operation_result=operation_result,
        )
        response_text = synthesis_result.response_text
        events.append(
            self.make_event(
                "response_synthesized",
                contract,
                {
                    "intent": directive.intent,
                    "continuity_action": deliberative_plan.continuity_action,
                    "continuity_source": deliberative_plan.continuity_source,
                    "continuity_target_mission_id": (
                        str(deliberative_plan.continuity_target_mission_id)
                        if deliberative_plan.continuity_target_mission_id
                        else None
                    ),
                    "identity_mode": directive.identity_mode,
                    "identity_signature": identity_profile.identity_signature,
                    "response_style": final_response_style,
                    "identity_guardrail": governance_check.context.get("identity_guardrail"),
                    "primary_mind": deliberative_plan.primary_mind,
                    "primary_mind_family": deliberative_plan.primary_mind_family,
                    "primary_domain_driver": deliberative_plan.primary_domain_driver,
                    "dominant_tension": deliberative_plan.dominant_tension,
                    "arbitration_source": deliberative_plan.arbitration_source,
                    **self._mind_domain_specialist_contract_payload(
                        operation_dispatch or deliberative_plan
                    ),
                    "metacognitive_guidance_applied": (
                        deliberative_plan.metacognitive_guidance_applied
                    ),
                    "metacognitive_guidance_summary": (
                        deliberative_plan.metacognitive_guidance_summary
                    ),
                    "metacognitive_effects": deliberative_plan.metacognitive_effects,
                    "metacognitive_containment_recommendation": (
                        deliberative_plan.metacognitive_containment_recommendation
                    ),
                    "mind_disagreement_status": deliberative_plan.mind_disagreement_status,
                    "mind_validation_checkpoints": (
                        deliberative_plan.mind_validation_checkpoints
                    ),
                    **self._memory_maintenance_event_payload(
                        deliberative_plan=deliberative_plan
                    ),
                    **self._capability_decision_event_payload(
                        deliberative_plan,
                        authorization_status=self._resolve_capability_authorization_status(
                            plan=deliberative_plan,
                            governance_decision=governance_decision,
                            specialist_handoff_decision=(
                                specialist_handoff_assessment.governance_decision
                            ),
                        ),
                    ),
                    **self._request_identity_policy_payload(deliberative_plan),
                    "adaptive_intervention_status": (
                        deliberative_plan.adaptive_intervention_status
                    ),
                    "adaptive_intervention_reason": (
                        deliberative_plan.adaptive_intervention_reason
                    ),
                    "adaptive_intervention_trigger": (
                        deliberative_plan.adaptive_intervention_trigger
                    ),
                    "adaptive_intervention_selected_action": (
                        deliberative_plan.adaptive_intervention_selected_action
                    ),
                    "adaptive_intervention_expected_effect": (
                        deliberative_plan.adaptive_intervention_expected_effect
                    ),
                    "adaptive_intervention_effects": (
                        deliberative_plan.adaptive_intervention_effects
                    ),
                    **self._adaptive_intervention_response_payload(
                        synthesis_result=synthesis_result
                    ),
                    "cognitive_strategy_shift_applied": (
                        deliberative_plan.cognitive_strategy_shift_applied
                    ),
                    "cognitive_strategy_shift_summary": (
                        deliberative_plan.cognitive_strategy_shift_summary
                    ),
                    "cognitive_strategy_shift_trigger": (
                        deliberative_plan.cognitive_strategy_shift_trigger
                    ),
                    "cognitive_strategy_shift_effects": (
                        deliberative_plan.cognitive_strategy_shift_effects
                    ),
                    "cognitive_recomposition_applied": (
                        cognitive_snapshot.recomposition_applied
                    ),
                    "cognitive_recomposition_reason": (
                        cognitive_snapshot.recomposition_reason
                    ),
                    "cognitive_recomposition_trigger": (
                        cognitive_snapshot.recomposition_trigger
                    ),
                    "primary_route": deliberative_plan.primary_route,
                    "primary_canonical_domain": deliberative_plan.primary_canonical_domain,
                    "workflow_profile": deliberative_plan.route_workflow_profile,
                    "workflow_response_focus": workflow_runtime_guidance(
                        deliberative_plan.route_workflow_profile
                    ).response_focus,
                    "specialist_hints": deliberative_plan.specialist_hints,
                    "guided_memory_specialists": guided_memory_runtime_hints[
                        "guided_memory_specialists"
                    ],
                    "semantic_memory_available": guided_memory_runtime_hints[
                        "semantic_memory_available"
                    ],
                    "procedural_memory_available": guided_memory_runtime_hints[
                        "procedural_memory_available"
                    ],
                    "semantic_memory_source": deliberative_plan.semantic_memory_source,
                    "procedural_memory_source": deliberative_plan.procedural_memory_source,
                    "semantic_memory_effects": deliberative_plan.semantic_memory_effects,
                    "procedural_memory_effects": deliberative_plan.procedural_memory_effects,
                    "semantic_memory_lifecycle": (
                        deliberative_plan.semantic_memory_lifecycle
                    ),
                    "procedural_memory_lifecycle": (
                        deliberative_plan.procedural_memory_lifecycle
                    ),
                    "semantic_memory_state": deliberative_plan.semantic_memory_state,
                    "procedural_memory_state": deliberative_plan.procedural_memory_state,
                    "memory_lifecycle_status": deliberative_plan.memory_lifecycle_status,
                    "memory_review_status": deliberative_plan.memory_review_status,
                    "memory_consolidation_status": (
                        deliberative_plan.memory_consolidation_status
                    ),
                    "memory_fixation_status": deliberative_plan.memory_fixation_status,
                    "memory_archive_status": deliberative_plan.memory_archive_status,
                    "procedural_artifact_status": (
                        deliberative_plan.procedural_artifact_status
                    ),
                    "procedural_artifact_refs": (
                        [deliberative_plan.procedural_artifact_ref]
                        if deliberative_plan.procedural_artifact_ref
                        else []
                    ),
                    "procedural_artifact_version": (
                        deliberative_plan.procedural_artifact_version
                    ),
                    "procedural_artifact_summary": (
                        deliberative_plan.procedural_artifact_summary
                    ),
                    "contract_validation_status": (
                        deliberative_plan.contract_validation_status
                    ),
                    "contract_validation_errors": (
                        deliberative_plan.contract_validation_errors
                    ),
                    "contract_validation_retry_applied": (
                        deliberative_plan.contract_validation_retry_applied
                    ),
                    "output_validation_status": (
                        synthesis_result.output_validation_status
                    ),
                    "output_validation_errors": (
                        synthesis_result.output_validation_errors
                    ),
                    "output_validation_retry_applied": (
                        synthesis_result.output_validation_retry_applied
                    ),
                    "workflow_output_status": synthesis_result.workflow_output_status,
                    "workflow_output_errors": synthesis_result.workflow_output_errors,
                    "semantic_memory_focus": guided_memory_runtime_hints[
                        "semantic_memory_focus"
                    ],
                    "procedural_memory_hint": guided_memory_runtime_hints[
                        "procedural_memory_hint"
                    ],
                    "context_compaction_status": deliberative_plan.context_compaction_status,
                    "cross_session_recall_status": deliberative_plan.cross_session_recall_status,
                    "cross_session_recall_summary": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "cross_session_recall_summary=",
                    ),
                    "mind_domain_specialist_chain_status": chain_payload["status"],
                    "mind_domain_specialist_chain": chain_payload["chain"],
                },
            )
        )

        memory_record_result = self.memory_service.record_turn(
            contract,
            intent=directive.intent,
            response_text=response_text,
            deliberative_plan=deliberative_plan,
            specialist_contributions=specialist_review.contributions,
            governance_decision=governance_decision.decision,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
        )
        events.append(
            self.make_event(
                "memory_recorded",
                contract,
                {
                    "memory_record_id": str(memory_record_result.record_contract.memory_record_id),
                    "record_type": memory_record_result.record_contract.record_type,
                    "continuity_mode": deliberative_plan.continuity_action,
                    "continuity_source": deliberative_plan.continuity_source,
                    "continuity_target_mission_id": (
                        str(deliberative_plan.continuity_target_mission_id)
                        if deliberative_plan.continuity_target_mission_id
                        else None
                    ),
                    "user_scope_status": (
                        memory_record_result.user_scope_context.context_status
                        if memory_record_result.user_scope_context
                        else "not_applicable"
                    ),
                    "user_scope_interaction_count": (
                        memory_record_result.user_scope_context.interaction_count
                        if memory_record_result.user_scope_context
                        else 0
                    ),
                    "user_context_brief": (
                        memory_record_result.user_scope_context.user_context_brief
                        if memory_record_result.user_scope_context
                        else None
                    ),
                    "organization_scope_status": memory_record_result.organization_scope_status,
                    "organization_scope_reason": memory_record_result.organization_scope_reason,
                    "organization_scope_reopen_signal": (
                        memory_record_result.organization_scope_reopen_signal
                    ),
                    "semantic_memory_source": deliberative_plan.semantic_memory_source,
                    "procedural_memory_source": deliberative_plan.procedural_memory_source,
                    "semantic_memory_lifecycle": (
                        deliberative_plan.semantic_memory_lifecycle
                    ),
                    "procedural_memory_lifecycle": (
                        deliberative_plan.procedural_memory_lifecycle
                    ),
                    "semantic_memory_state": deliberative_plan.semantic_memory_state,
                    "procedural_memory_state": deliberative_plan.procedural_memory_state,
                    "memory_lifecycle_status": deliberative_plan.memory_lifecycle_status,
                    "memory_review_status": deliberative_plan.memory_review_status,
                    **self._memory_maintenance_event_payload(
                        deliberative_plan=deliberative_plan
                    ),
                    "memory_consolidation_status": (
                        deliberative_plan.memory_consolidation_status
                    ),
                    "memory_fixation_status": deliberative_plan.memory_fixation_status,
                    "memory_archive_status": deliberative_plan.memory_archive_status,
                    "procedural_artifact_status": (
                        memory_record_result.procedural_artifact_status
                    ),
                    "procedural_artifact_refs": (
                        memory_record_result.procedural_artifact_refs
                    ),
                    "procedural_artifact_version": (
                        memory_record_result.procedural_artifact_version
                    ),
                    "procedural_artifact_summary": (
                        memory_record_result.procedural_artifact_summary
                    ),
                    "ecosystem_state_status": (
                        operation_result.ecosystem_state_status if operation_result else None
                    ),
                    "active_work_items": (
                        operation_result.active_work_items if operation_result else []
                    ),
                    "active_artifact_refs": (
                        operation_result.active_artifact_refs if operation_result else []
                    ),
                    "open_checkpoint_refs": (
                        operation_result.open_checkpoint_refs if operation_result else []
                    ),
                    "surface_presence": (
                        operation_result.surface_presence if operation_result else []
                    ),
                    "ecosystem_state_summary": (
                        operation_result.ecosystem_state_summary if operation_result else None
                    ),
                },
            )
        )
        self.observability_service.ingest_events(events)

        return self._build_response_from_state(
            {
                "contract": contract,
                "directive": directive,
                "deliberative_plan": deliberative_plan,
                "governance_check": governance_check,
                "governance_decision": governance_decision,
                "memory_recovery_result": memory_recovery_result,
                "memory_record_result": memory_record_result,
                "knowledge_result": knowledge_result,
                "artifact_results": artifact_results,
                "cognitive_snapshot": cognitive_snapshot,
                "mission_runtime_state": mission_runtime_state,
                "specialist_review": specialist_review,
                "specialist_handoff_check": (specialist_handoff_assessment.governance_check),
                "specialist_handoff_decision": (specialist_handoff_assessment.governance_decision),
                "operation_dispatch": operation_dispatch,
                "operation_result": operation_result,
                "events": events,
                "response_text": response_text,
            }
        )

    def handle_input_langgraph_flow(self, contract: InputContract) -> OrchestratorResponse:
        """Run the optional LangGraph flow without changing the default v1 path."""

        from orchestrator_service.langgraph_flow import LangGraphFlowRunner

        return LangGraphFlowRunner(self).run(contract)

    def _plan_specialist_handoffs(
        self,
        contract: InputContract,
        *,
        directive: ExecutiveDirective,
        deliberative_plan: DeliberativePlanContract,
        memory_recovery_result: MemoryRecoveryResult,
        knowledge_result: KnowledgeRetrievalResult | None,
        events: list[InternalEventEnvelope],
    ) -> tuple[SpecialistHandoffPlan, list[InternalEventEnvelope]]:
        if not self._capability_allows_specialist_handoff(deliberative_plan):
            return (
                SpecialistHandoffPlan(
                    specialist_hints=[],
                    selections=[],
                    invocations=[],
                    boundary_summary="capability decision disabled specialist handoffs",
                ),
                list(events),
            )
        shared_memory_contexts = self.memory_service.prepare_specialist_shared_memory(
            session_id=str(contract.session_id),
            specialist_hints=list(deliberative_plan.specialist_hints),
            active_domains=list(deliberative_plan.active_domains),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            continuity_context=memory_recovery_result.continuity_context,
            user_id=contract.user_id,
        )
        handoff_plan = self.specialist_engine.plan_handoffs(
            intent=directive.intent,
            plan=deliberative_plan,
            knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
            domain_specialist_routes=(
                knowledge_result.specialist_routes if knowledge_result else []
            ),
            shared_memory_contexts=shared_memory_contexts,
            session_id=str(contract.session_id),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            requested_by_service=self.name,
        )
        updated_events = list(events)
        selection_registry_payloads = self._specialist_registry_payloads(handoff_plan.selections)
        selected_specialists = [
            item.specialist_type
            for item in handoff_plan.selections
            if item.selection_status == "selected"
        ]
        selected_domains = [
            item.linked_domain
            for item in handoff_plan.selections
            if item.selection_status == "selected" and item.linked_domain
        ]
        chain_payload = self._mind_domain_specialist_chain_payload(
            deliberative_plan,
            planned_specialists=list(deliberative_plan.specialist_hints),
            selected_specialists=selected_specialists,
            selected_domains=selected_domains,
        )
        updated_events.append(
            self.make_event(
                "specialist_selection_decided",
                contract,
                {
                    "selected_specialists": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.selection_status == "selected"
                    ],
                    "selection_statuses": {
                        item.specialist_type: item.selection_status
                        for item in handoff_plan.selections
                    },
                    "domain_links": {
                        item.specialist_type: item.linked_domain
                        for item in handoff_plan.selections
                        if item.linked_domain
                    },
                    "selection_modes": {
                        item.specialist_type: item.selection_mode
                        for item in handoff_plan.selections
                    },
                    "primary_mind": deliberative_plan.primary_mind,
                    "primary_mind_family": deliberative_plan.primary_mind_family,
                    "primary_domain_driver": deliberative_plan.primary_domain_driver,
                    "arbitration_source": deliberative_plan.arbitration_source,
                    "primary_route": deliberative_plan.primary_route,
                    "primary_canonical_domain": deliberative_plan.primary_canonical_domain,
                    "route_maturity": {
                        specialist_type: payload.get("maturity")
                        for specialist_type, payload in selection_registry_payloads.items()
                    },
                    "canonical_domain_refs_resolved": {
                        specialist_type: list(payload.get("canonical_domain_refs", []))
                        for specialist_type, payload in selection_registry_payloads.items()
                    },
                    "registry_route_payloads": selection_registry_payloads,
                    "registry_link_matches": {
                        specialist_type: payload.get("link_matches") is True
                        for specialist_type, payload in selection_registry_payloads.items()
                    },
                    "registry_mode_matches": {
                        item.specialist_type: (
                            selection_registry_payloads.get(item.specialist_type, {}).get(
                                "specialist_mode"
                            ) == item.selection_mode
                            if item.linked_domain
                            else item.selection_mode == "standard"
                        )
                        for item in handoff_plan.selections
                    },
                    "registry_specialist_eligibility": {
                        item.specialist_type: (
                            selection_registry_payloads.get(
                                item.specialist_type, {}
                            ).get("eligible")
                            is True
                            if item.linked_domain
                            else False
                        )
                        for item in handoff_plan.selections
                    },
                    "primary_route_matches": {
                        item.specialist_type: (
                            item.linked_domain == deliberative_plan.primary_route
                        )
                        for item in handoff_plan.selections
                        if item.linked_domain
                    },
                    "primary_canonical_matches": {
                        specialist_type: (
                            deliberative_plan.primary_canonical_domain
                            in payload.get("canonical_domain_refs", [])
                            if deliberative_plan.primary_canonical_domain is not None
                            else False
                        )
                        for specialist_type, payload in selection_registry_payloads.items()
                    },
                    "primary_domain_driver_matches": {
                        specialist_type: (
                            deliberative_plan.primary_domain_driver
                            in payload.get("canonical_domain_refs", [])
                            if deliberative_plan.primary_domain_driver is not None
                            else False
                        )
                        for specialist_type, payload in selection_registry_payloads.items()
                    },
                    "domain_specialists": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.linked_domain and item.selection_status == "selected"
                    ],
                    "shadow_specialists": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.selection_mode == "shadow" and item.selection_status == "selected"
                    ],
                    "guided_specialists": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.selection_mode in {"guided", "active"}
                        and item.selection_status == "selected"
                    ],
                    "requires_governance_review": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.requires_governance_review
                    ],
                    "selection_rationales": {
                        item.specialist_type: item.rationale for item in handoff_plan.selections
                    },
                    **self._mind_domain_specialist_contract_payload(handoff_plan),
                    "mind_domain_specialist_chain_status": chain_payload["status"],
                    "mind_domain_specialist_chain": chain_payload["chain"],
                },
            )
        )
        if handoff_plan.invocations:
            updated_events.append(
                self.make_event(
                    "specialist_shared_memory_linked",
                    contract,
                    {
                        "specialist_hints": handoff_plan.specialist_hints,
                        "sharing_modes": {
                            item.specialist_type: (
                                item.shared_memory_context.sharing_mode
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "related_mission_counts": {
                            item.specialist_type: len(
                                item.shared_memory_context.related_mission_ids
                            )
                            if item.shared_memory_context
                            else 0
                            for item in handoff_plan.invocations
                        },
                        "memory_class_policies": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_class_policies
                                if item.shared_memory_context
                                else {}
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_ref_counts": {
                            item.specialist_type: len(item.shared_memory_context.memory_refs)
                            if item.shared_memory_context
                            else 0
                            for item in handoff_plan.invocations
                        },
                        "memory_refs_by_specialist": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_refs
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "semantic_focus_by_specialist": {
                            item.specialist_type: (
                                item.shared_memory_context.semantic_focus
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "consumer_modes": {
                            item.specialist_type: (
                                item.shared_memory_context.consumer_mode
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "consumed_memory_classes": {
                            item.specialist_type: (
                                item.shared_memory_context.consumed_memory_classes
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_write_policies": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_write_policies
                                if item.shared_memory_context
                                else {}
                            )
                            for item in handoff_plan.invocations
                        },
                        "recurrent_context_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.recurrent_context_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "recurrent_interaction_counts": {
                            item.specialist_type: (
                                item.shared_memory_context.recurrent_interaction_count
                                if item.shared_memory_context
                                else 0
                            )
                            for item in handoff_plan.invocations
                        },
                        "recurrent_context_briefs": {
                            item.specialist_type: (
                                item.shared_memory_context.recurrent_context_brief
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "context_briefs": {
                            item.specialist_type: {
                                "mission": (
                                    item.shared_memory_context.mission_context_brief
                                    if item.shared_memory_context
                                    else None
                                ),
                                "domain": (
                                    item.shared_memory_context.domain_context_brief
                                    if item.shared_memory_context
                                    else None
                                ),
                                "continuity": (
                                    item.shared_memory_context.continuity_context_brief
                                    if item.shared_memory_context
                                    else None
                                ),
                            }
                            for item in handoff_plan.invocations
                        },
                        "consumer_profiles": {
                            item.specialist_type: (
                                item.shared_memory_context.consumer_profile
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "consumer_objectives": {
                            item.specialist_type: (
                                item.shared_memory_context.consumer_objective
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "expected_deliverables": {
                            item.specialist_type: (
                                item.shared_memory_context.expected_deliverables
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "telemetry_focus": {
                            item.specialist_type: (
                                item.shared_memory_context.telemetry_focus
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "linked_domains": {
                            item.specialist_type: item.linked_domain
                            for item in handoff_plan.invocations
                            if item.linked_domain
                        },
                        "domain_mission_link_reasons": {
                            item.specialist_type: (
                                item.shared_memory_context.domain_mission_link_reason
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                            if item.shared_memory_context
                        },
                        "domain_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.linked_domain
                        ],
                        "shadow_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.selection_mode == "shadow"
                        ],
                        "guided_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.selection_mode in {"guided", "active"}
                        ],
                        "semantic_memory_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.shared_memory_context
                            and "semantic" in item.shared_memory_context.consumed_memory_classes
                        ],
                        "procedural_memory_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.shared_memory_context
                            and "procedural" in item.shared_memory_context.consumed_memory_classes
                        ],
                        "semantic_memory_sources": {
                            item.specialist_type: (
                                item.shared_memory_context.semantic_memory_source
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_memory_sources": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_memory_source
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "semantic_memory_effects": {
                            item.specialist_type: (
                                item.shared_memory_context.semantic_memory_effects
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_memory_effects": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_memory_effects
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "semantic_memory_lifecycles": {
                            item.specialist_type: (
                                item.shared_memory_context.semantic_memory_lifecycle
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_memory_lifecycles": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_memory_lifecycle
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "semantic_memory_states": {
                            item.specialist_type: (
                                item.shared_memory_context.semantic_memory_state
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_memory_states": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_memory_state
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_lifecycle_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_lifecycle_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_review_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_review_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_consolidation_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_consolidation_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_fixation_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_fixation_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_archive_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_archive_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_artifact_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_artifact_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_artifact_refs_by_specialist": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_artifact_refs
                                if item.shared_memory_context
                                else []
                            )
                            for item in handoff_plan.invocations
                        },
                        "procedural_artifact_versions": {
                            item.specialist_type: (
                                item.shared_memory_context.procedural_artifact_version
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_corpus_statuses": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_corpus_status
                                if item.shared_memory_context
                                else "not_applicable"
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_retention_pressures": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_retention_pressure
                                if item.shared_memory_context
                                else None
                            )
                            for item in handoff_plan.invocations
                        },
                        "memory_corpus_summaries": {
                            item.specialist_type: (
                                item.shared_memory_context.memory_corpus_summary
                                if item.shared_memory_context
                                else {}
                            )
                            for item in handoff_plan.invocations
                        },
                        "mind_domain_specialist_chain_status": chain_payload["status"],
                        "mind_domain_specialist_chain": chain_payload["chain"],
                    },
                )
            )
            updated_events.append(
                self.make_event(
                    "specialist_contracts_composed",
                    contract,
                    {
                        "invocation_ids": [item.invocation_id for item in handoff_plan.invocations],
                        "specialist_hints": handoff_plan.specialist_hints,
                        "boundary_summary": handoff_plan.boundary_summary,
                        "response_channel": handoff_plan.invocations[0].boundary.response_channel,
                        "tool_access_mode": handoff_plan.invocations[0].boundary.tool_access_mode,
                        "shadow_specialists": [
                            item.specialist_type
                            for item in handoff_plan.invocations
                            if item.selection_mode == "shadow"
                        ],
                        "shared_memory_attached": all(
                            item.shared_memory_context is not None
                            for item in handoff_plan.invocations
                        ),
                    },
                )
            )
        return handoff_plan, updated_events

    def _govern_specialist_handoffs(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract,
        handoff_plan: SpecialistHandoffPlan,
        events: list[InternalEventEnvelope],
    ):
        assessment = self.governance_service.assess_specialist_handoff(
            contract=contract,
            plan=deliberative_plan,
            selections=handoff_plan.selections,
            invocations=handoff_plan.invocations,
            requested_by_service=self.name,
        )
        updated_events = list(events)
        updated_events.append(
            self.make_event(
                "specialist_handoff_governed",
                contract,
                {
                    "governance_check_id": str(assessment.governance_check.governance_check_id),
                    "decision": assessment.governance_decision.decision.value,
                    "selected_specialists": [
                        item.specialist_type
                        for item in handoff_plan.selections
                        if item.selection_status == "selected"
                    ],
                    "invocation_ids": [item.invocation_id for item in handoff_plan.invocations],
                    "requires_audit": assessment.governance_decision.requires_audit,
                    "conditions": list(assessment.governance_decision.conditions),
                },
            )
        )
        return assessment, updated_events

    def _execute_specialist_handoffs(
        self,
        contract: InputContract,
        *,
        directive: ExecutiveDirective,
        deliberative_plan: DeliberativePlanContract,
        knowledge_result: KnowledgeRetrievalResult | None,
        handoff_plan: SpecialistHandoffPlan,
        handoff_governance: GovernanceDecisionContract,
        events: list[InternalEventEnvelope],
        runtime_mode: str = "native_pipeline",
    ) -> tuple[SpecialistReview, DeliberativePlanContract, list[InternalEventEnvelope]]:
        executable_plan = handoff_plan
        updated_events = list(events)
        if handoff_governance.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            executable_plan = SpecialistHandoffPlan(
                specialist_hints=[],
                selections=handoff_plan.selections,
                invocations=handoff_plan.invocations,
                boundary_summary=handoff_plan.boundary_summary,
                mind_domain_specialist_contract_status=(
                    handoff_plan.mind_domain_specialist_contract_status
                ),
                mind_domain_specialist_contract_summary=(
                    handoff_plan.mind_domain_specialist_contract_summary
                ),
                mind_domain_specialist_contract_chain=(
                    handoff_plan.mind_domain_specialist_contract_chain
                ),
                mind_domain_specialist_active_specialist=(
                    handoff_plan.mind_domain_specialist_active_specialist
                ),
                mind_domain_specialist_override_mode=(
                    handoff_plan.mind_domain_specialist_override_mode
                ),
                mind_domain_specialist_fallback_mode=(
                    handoff_plan.mind_domain_specialist_fallback_mode
                ),
            )
            if handoff_plan.invocations:
                updated_events.append(
                    self.make_event(
                        "specialist_handoff_blocked",
                        contract,
                        {
                            "decision_id": str(handoff_governance.decision_id),
                            "invocation_ids": [
                                item.invocation_id for item in handoff_plan.invocations
                            ],
                            "justification": handoff_governance.justification,
                        },
                    )
                )
        specialist_review = self.specialist_engine.review_handoffs(
            intent=directive.intent,
            plan=deliberative_plan,
            knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
            handoff_plan=executable_plan,
        )
        refined_plan = deliberative_plan
        if specialist_review.specialist_hints:
            updated_events.append(
                self.make_event(
                    "specialists_dispatched",
                    contract,
                    {
                        "specialist_hints": specialist_review.specialist_hints,
                        "invocation_ids": [
                            item.invocation_id for item in specialist_review.invocations
                        ],
                        "domain_specialists": [
                            item.specialist_type
                            for item in specialist_review.invocations
                            if item.linked_domain
                        ],
                        "shadow_specialists": [
                            item.specialist_type
                            for item in specialist_review.invocations
                            if item.selection_mode == "shadow"
                        ],
                        "guided_specialists": [
                            item.specialist_type
                            for item in specialist_review.invocations
                            if item.selection_mode in {"guided", "active"}
                        ],
                        "boundary_summary": specialist_review.boundary_summary,
                        **self._mind_domain_specialist_contract_payload(
                            specialist_review
                        ),
                    },
                )
            )
        if specialist_review.contributions:
            domain_invocation_index = {
                item.invocation_id: item
                for item in specialist_review.invocations
                if item.linked_domain and item.invocation_id is not None
            }
            shadow_invocation_ids = {
                item.invocation_id
                for item in specialist_review.invocations
                if item.selection_mode == "shadow"
            }
            shadow_contributions = [
                item
                for item in specialist_review.contributions
                if item.invocation_id in shadow_invocation_ids
            ]
            domain_contributions = [
                item
                for item in specialist_review.contributions
                if item.invocation_id in domain_invocation_index
            ]
            live_contributions = [
                item
                for item in specialist_review.contributions
                if item.invocation_id not in shadow_invocation_ids
            ]
            updated_events.append(
                self.make_event(
                    "specialists_completed",
                    contract,
                    {
                        "specialist_types": [
                            item.specialist_type for item in specialist_review.contributions
                        ],
                        "invocation_ids": [
                            item.invocation_id for item in specialist_review.contributions
                        ],
                        "output_hints": [
                            output_hint
                            for item in specialist_review.contributions
                            for output_hint in item.output_hints
                        ],
                        "summary": specialist_review.summary,
                        **self._mind_domain_specialist_contract_payload(
                            specialist_review
                        ),
                    },
                )
            )
            if domain_contributions:
                completed_registry_payloads = self._specialist_registry_payloads(
                    list(domain_invocation_index.values())
                )
                updated_events.append(
                    self.make_event(
                        "domain_specialist_completed",
                        contract,
                        {
                            "specialist_types": [
                                item.specialist_type for item in domain_contributions
                            ],
                            "invocation_ids": [item.invocation_id for item in domain_contributions],
                            "primary_mind": deliberative_plan.primary_mind,
                            "primary_mind_family": deliberative_plan.primary_mind_family,
                            "primary_domain_driver": deliberative_plan.primary_domain_driver,
                            "arbitration_source": deliberative_plan.arbitration_source,
                            "linked_domains": {
                                invocation.specialist_type: invocation.linked_domain
                                for invocation in domain_invocation_index.values()
                            },
                            "selection_modes": {
                                invocation.specialist_type: invocation.selection_mode
                                for invocation in domain_invocation_index.values()
                            },
                            "primary_route": deliberative_plan.primary_route,
                            "primary_canonical_domain": deliberative_plan.primary_canonical_domain,
                            "route_maturity": {
                                specialist_type: payload.get("maturity")
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "registry_route_payloads": completed_registry_payloads,
                            "registry_link_matches": {
                                specialist_type: payload.get("link_matches") is True
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "registry_mode_matches": {
                                invocation.specialist_type: (
                                    completed_registry_payloads.get(
                                        invocation.specialist_type, {}
                                    ).get(
                                        "specialist_mode"
                                    ) == invocation.selection_mode
                                )
                                for invocation in domain_invocation_index.values()
                                if invocation.linked_domain
                            },
                            "registry_specialist_eligibility": {
                                specialist_type: payload.get("eligible") is True
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "primary_route_matches": {
                                invocation.specialist_type: (
                                    invocation.linked_domain == deliberative_plan.primary_route
                                )
                                for invocation in domain_invocation_index.values()
                                if invocation.linked_domain
                            },
                            "primary_canonical_matches": {
                                specialist_type: (
                                    deliberative_plan.primary_canonical_domain
                                    in payload.get("canonical_domain_refs", [])
                                    if deliberative_plan.primary_canonical_domain is not None
                                    else False
                                )
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "primary_domain_driver_matches": {
                                specialist_type: (
                                    deliberative_plan.primary_domain_driver
                                    in payload.get("canonical_domain_refs", [])
                                    if deliberative_plan.primary_domain_driver is not None
                                    else False
                                )
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "canonical_domain_refs": {
                                specialist_type: list(payload.get("canonical_domain_refs", []))
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "canonical_domain_refs_resolved": {
                                specialist_type: list(payload.get("canonical_domain_refs", []))
                                for specialist_type, payload in completed_registry_payloads.items()
                            },
                            "consumer_profiles": {
                                invocation.specialist_type: (
                                    invocation.shared_memory_context.consumer_profile
                                    if invocation.shared_memory_context
                                    else None
                                )
                                for invocation in domain_invocation_index.values()
                            },
                            "expected_deliverables": {
                                invocation.specialist_type: (
                                    invocation.shared_memory_context.expected_deliverables
                                    if invocation.shared_memory_context
                                    else []
                                )
                                for invocation in domain_invocation_index.values()
                            },
                            "telemetry_focus": {
                                invocation.specialist_type: (
                                    invocation.shared_memory_context.telemetry_focus
                                    if invocation.shared_memory_context
                                    else []
                                )
                                for invocation in domain_invocation_index.values()
                            },
                            **self._mind_domain_specialist_contract_payload(
                                specialist_review
                            ),
                        },
                    )
                )
            if shadow_contributions:
                updated_events.append(
                    self.make_event(
                        "specialist_shadow_mode_completed",
                        contract,
                        {
                            "specialist_types": [
                                item.specialist_type for item in shadow_contributions
                            ],
                            "invocation_ids": [item.invocation_id for item in shadow_contributions],
                            "linked_domains": {
                                invocation.specialist_type: invocation.linked_domain
                                for invocation in specialist_review.invocations
                                if invocation.invocation_id in shadow_invocation_ids
                            },
                        },
                    )
                )
            if live_contributions:
                refined_plan = self.planning_engine.refine_task_plan(
                    deliberative_plan,
                    specialist_summary=specialist_review.summary,
                    specialist_contributions=live_contributions,
                )
                updated_events.append(
                    self.make_event(
                        "plan_refined",
                        contract,
                        {
                            "recommended_task_type": refined_plan.recommended_task_type,
                            "requires_human_validation": refined_plan.requires_human_validation,
                            "steps": refined_plan.steps,
                            "specialist_resolution_summary": (
                                refined_plan.specialist_resolution_summary
                            ),
                            "adaptive_intervention_status": (
                                refined_plan.adaptive_intervention_status
                            ),
                            "adaptive_intervention_reason": (
                                refined_plan.adaptive_intervention_reason
                            ),
                            "adaptive_intervention_trigger": (
                                refined_plan.adaptive_intervention_trigger
                            ),
                            "adaptive_intervention_selected_action": (
                                refined_plan.adaptive_intervention_selected_action
                            ),
                            "adaptive_intervention_expected_effect": (
                                refined_plan.adaptive_intervention_expected_effect
                            ),
                            "adaptive_intervention_effects": (
                                refined_plan.adaptive_intervention_effects
                            ),
                            "cognitive_strategy_shift_applied": (
                                refined_plan.cognitive_strategy_shift_applied
                            ),
                            "cognitive_strategy_shift_summary": (
                                refined_plan.cognitive_strategy_shift_summary
                            ),
                            "cognitive_strategy_shift_trigger": (
                                refined_plan.cognitive_strategy_shift_trigger
                            ),
                            "cognitive_strategy_shift_effects": (
                                refined_plan.cognitive_strategy_shift_effects
                            ),
                            "smallest_safe_next_action": (
                                refined_plan.smallest_safe_next_action
                            ),
                            **self._mind_domain_specialist_contract_payload(
                                refined_plan
                            ),
                        },
                    )
                )
        updated_events.append(
            self.make_event(
                "specialist_subflow_completed",
                contract,
                self._build_specialist_subflow_payload(
                    runtime_mode=runtime_mode,
                    handoff_plan=handoff_plan,
                    handoff_governance=handoff_governance,
                    specialist_review=specialist_review,
                    refined_plan=refined_plan,
                    original_plan=deliberative_plan,
                ),
            )
        )
        return specialist_review, refined_plan, updated_events

    def _declare_mission_runtime_state(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract,
        memory_recovery_result: MemoryRecoveryResult,
        specialist_review: SpecialistReview,
        events: list[InternalEventEnvelope],
        runtime_mode: str,
    ) -> tuple[MissionRuntimeStateContract | None, list[InternalEventEnvelope]]:
        if contract.mission_id is None:
            return None, list(events)
        mission_runtime_state = self._build_mission_runtime_state(
            contract,
            deliberative_plan=deliberative_plan,
            memory_recovery_result=memory_recovery_result,
            specialist_review=specialist_review,
            runtime_mode=runtime_mode,
        )
        updated_events = list(events)
        updated_events.append(
            self.make_event(
                "mission_runtime_state_declared",
                contract,
                {
                    "runtime_mode": mission_runtime_state.runtime_mode,
                    "mission_id": str(mission_runtime_state.mission_id),
                    "mission_goal": mission_runtime_state.mission_goal,
                    "mission_status": mission_runtime_state.mission_status.value,
                    "continuity_action": mission_runtime_state.continuity_action,
                    "continuity_source": mission_runtime_state.continuity_source,
                    "continuity_target_mission_id": (
                        str(mission_runtime_state.continuity_target_mission_id)
                        if mission_runtime_state.continuity_target_mission_id
                        else None
                    ),
                    "continuity_target_goal": mission_runtime_state.continuity_target_goal,
                    "continuity_recommendation": (
                        mission_runtime_state.continuity_recommendation
                    ),
                    "continuity_replay_status": (
                        mission_runtime_state.continuity_replay_status
                    ),
                    "continuity_recovery_mode": (
                        mission_runtime_state.continuity_recovery_mode
                    ),
                    "continuity_resume_point": (
                        mission_runtime_state.continuity_resume_point
                    ),
                    "requires_manual_resume": (
                        mission_runtime_state.requires_manual_resume
                    ),
                    "primary_route": mission_runtime_state.primary_route,
                    "workflow_profile": mission_runtime_state.workflow_profile,
                    "primary_mind": deliberative_plan.primary_mind,
                    "primary_domain_driver": deliberative_plan.primary_domain_driver,
                    "semantic_memory_source": deliberative_plan.semantic_memory_source,
                    "procedural_memory_source": deliberative_plan.procedural_memory_source,
                    "memory_lifecycle_status": deliberative_plan.memory_lifecycle_status,
                    "memory_review_status": deliberative_plan.memory_review_status,
                    "active_task_count": len(mission_runtime_state.active_tasks),
                    "open_loop_count": len(mission_runtime_state.open_loops),
                    "last_recommendation": mission_runtime_state.last_recommendation,
                    "ecosystem_state_status": mission_runtime_state.ecosystem_state_status,
                    "active_work_items": mission_runtime_state.active_work_items,
                    "active_artifact_refs": mission_runtime_state.active_artifact_refs,
                    "open_checkpoint_refs": mission_runtime_state.open_checkpoint_refs,
                    "surface_presence": mission_runtime_state.surface_presence,
                    "ecosystem_state_summary": mission_runtime_state.ecosystem_state_summary,
                    "related_mission_id": (
                        str(mission_runtime_state.related_mission_id)
                        if mission_runtime_state.related_mission_id
                        else None
                    ),
                    "related_mission_goal": mission_runtime_state.related_mission_goal,
                },
            )
        )
        return mission_runtime_state, updated_events

    def build_operation_dispatch(
        self,
        contract: InputContract,
        *,
        plan: DeliberativePlanContract,
        specialist_review: SpecialistReview,
        mission_runtime_state: MissionRuntimeStateContract | None = None,
        authorization_status: str | None = None,
    ) -> OperationDispatchContract:
        """Create the operational dispatch for an allowed request."""

        (
            workflow_domain_route,
            workflow_profile,
            workflow_steps,
            workflow_checkpoints,
            workflow_decision_points,
        ) = self._build_workflow_profile(plan)
        workflow_guidance = workflow_runtime_guidance(workflow_profile)
        workflow_resume_point = (
            mission_runtime_state.continuity_resume_point
            if mission_runtime_state is not None and mission_runtime_state.continuity_resume_point
            else plan.continuity_resume_point
        )
        workflow_resume_eligible = bool(workflow_resume_point) and not (
            mission_runtime_state.requires_manual_resume
            if mission_runtime_state is not None
            else plan.continuity_requires_manual_resume
        )
        workflow_resume_status = (
            "resume_available"
            if workflow_resume_eligible
            else (
                "manual_resume_required"
                if workflow_resume_point
                else "fresh_start"
            )
        )
        workflow_checkpoint_state = self._initial_workflow_checkpoint_state(
            workflow_checkpoints,
            resume_status=workflow_resume_status,
        )
        mind_domain_specialist_policy = build_mind_domain_specialist_runtime_policy(
            contract_status=plan.mind_domain_specialist_contract_status,
            active_specialist=plan.mind_domain_specialist_active_specialist,
            planned_specialists=list(plan.specialist_hints),
            authoritative_specialist_hint=(
                route_linked_specialist_type(plan.primary_route)
                if plan.primary_route
                else None
            ),
            override_mode=plan.mind_domain_specialist_override_mode,
            fallback_mode=plan.mind_domain_specialist_fallback_mode,
        )
        expected_output = (
            plan.route_expected_deliverables[0]
            if plan.route_expected_deliverables
            else "text_brief"
        )
        ecosystem_state = self._build_ecosystem_operational_state(
            contract=contract,
            plan=plan,
            mission_runtime_state=mission_runtime_state,
            workflow_profile=workflow_profile,
            workflow_checkpoint_state=workflow_checkpoint_state,
        )
        return OperationDispatchContract(
            operation_id=OperationId(f"op-{uuid4().hex[:8]}"),
            request_id=RequestId(str(contract.request_id)),
            task_type=plan.recommended_task_type,
            task_goal=plan.goal,
            task_plan=plan.plan_summary,
            constraints=list(plan.constraints),
            expected_output=expected_output,
            plan_summary=plan.plan_summary,
            planned_steps=list(plan.steps),
            plan_risks=list(plan.risks),
            plan_rationale=plan.rationale,
            specialist_summary=self._mind_domain_specialist_dispatch_summary(
                plan=plan,
                specialist_review=specialist_review,
                consumer_mode=mind_domain_specialist_policy.consumer_mode,
            ),
            specialist_findings=list(specialist_review.findings),
            mind_domain_specialist_contract_status=(
                plan.mind_domain_specialist_contract_status
            ),
            mind_domain_specialist_contract_summary=(
                plan.mind_domain_specialist_contract_summary
            ),
            mind_domain_specialist_contract_chain=(
                plan.mind_domain_specialist_contract_chain
            ),
            mind_domain_specialist_active_specialist=(
                plan.mind_domain_specialist_active_specialist
            ),
            mind_domain_specialist_override_mode=(
                plan.mind_domain_specialist_override_mode
            ),
            mind_domain_specialist_fallback_mode=(
                plan.mind_domain_specialist_fallback_mode
            ),
            mind_domain_specialist_consumer_mode=(
                mind_domain_specialist_policy.consumer_mode
            ),
            mind_domain_specialist_framing_mode=(
                mind_domain_specialist_policy.framing_mode
            ),
            mind_domain_specialist_continuity_mode=(
                mind_domain_specialist_policy.continuity_mode
            ),
            success_criteria=list(plan.success_criteria),
            smallest_safe_next_action=plan.smallest_safe_next_action,
            requires_human_validation=plan.requires_human_validation,
            capability_decision_status=plan.capability_decision_status,
            capability_decision_objective=plan.capability_decision_objective,
            capability_decision_reason=plan.capability_decision_reason,
            capability_decision_selected_mode=plan.capability_decision_selected_mode,
            capability_decision_authorization_status=(
                authorization_status or plan.capability_decision_authorization_status
            ),
            capability_decision_fallback_mode=plan.capability_decision_fallback_mode,
            capability_decision_tool_class=plan.capability_decision_tool_class,
            capability_decision_handoff_mode=plan.capability_decision_handoff_mode,
            capability_decision_eligible_capabilities=list(
                plan.capability_decision_eligible_capabilities
            ),
            capability_decision_selected_capabilities=list(
                plan.capability_decision_selected_capabilities
            ),
            request_identity_status=plan.request_identity_status,
            request_active_mission=plan.request_active_mission,
            request_executive_posture=plan.request_executive_posture,
            request_authority_level=plan.request_authority_level,
            request_risk_profile=plan.request_risk_profile,
            request_reversibility_mode=plan.request_reversibility_mode,
            request_confirmation_mode=plan.request_confirmation_mode,
            request_identity_summary=plan.request_identity_summary,
            request_identity_policy_refs=list(plan.request_identity_policy_refs),
            adaptive_intervention_status=plan.adaptive_intervention_status,
            adaptive_intervention_reason=plan.adaptive_intervention_reason,
            adaptive_intervention_trigger=plan.adaptive_intervention_trigger,
            adaptive_intervention_selected_action=(
                plan.adaptive_intervention_selected_action
            ),
            adaptive_intervention_expected_effect=(
                plan.adaptive_intervention_expected_effect
            ),
            adaptive_intervention_effects=list(plan.adaptive_intervention_effects),
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            domain_hints=list(plan.active_domains),
            canonical_domain_hints=list(plan.canonical_domains),
            primary_canonical_domain=plan.primary_canonical_domain,
            specialist_hints=list(mind_domain_specialist_policy.effective_specialists),
            workflow_profile=workflow_profile,
            workflow_domain_route=workflow_domain_route,
            workflow_objective=plan.route_consumer_objective or plan.goal,
            workflow_expected_deliverables=list(plan.route_expected_deliverables),
            workflow_telemetry_focus=list(plan.route_telemetry_focus),
            workflow_success_focus=workflow_guidance.success_focus,
            workflow_response_focus=workflow_guidance.response_focus,
            workflow_state="composed",
            workflow_governance_mode="core_mediated",
            workflow_steps=workflow_steps,
            workflow_checkpoints=workflow_checkpoints,
            workflow_decision_points=workflow_decision_points,
            workflow_checkpoint_state=workflow_checkpoint_state,
            workflow_resume_point=workflow_resume_point,
            workflow_resume_status=workflow_resume_status,
            workflow_resume_eligible=workflow_resume_eligible,
            ecosystem_state_status=ecosystem_state.ecosystem_state_status,
            active_work_items=list(ecosystem_state.active_work_items),
            active_artifact_refs=list(ecosystem_state.active_artifact_refs),
            open_checkpoint_refs=list(ecosystem_state.open_checkpoint_refs),
            surface_presence=list(ecosystem_state.surface_presence),
            ecosystem_state_summary=ecosystem_state.state_summary,
            priority_hint=contract.priority_hint,
        )

    @staticmethod
    def _build_ecosystem_operational_state(
        *,
        contract: InputContract,
        plan: DeliberativePlanContract,
        mission_runtime_state: MissionRuntimeStateContract | None,
        workflow_profile: str | None,
        workflow_checkpoint_state: dict[str, str],
    ) -> EcosystemOperationalStateContract:
        active_work_items = OrchestratorService._dedupe_texts(
            [
                *(mission_runtime_state.active_tasks if mission_runtime_state else []),
                *(mission_runtime_state.open_loops if mission_runtime_state else []),
                *plan.open_loops,
                *(f"workflow_step:{item}" for item in plan.steps[:3]),
            ]
        )
        active_artifact_refs = OrchestratorService._dedupe_texts(
            [plan.procedural_artifact_ref] if plan.procedural_artifact_ref else []
        )
        open_checkpoint_refs = [
            f"workflow_checkpoint:{checkpoint}:{status}"
            for checkpoint, status in workflow_checkpoint_state.items()
            if status != "completed"
        ]
        surface_presence = OrchestratorService._dedupe_texts(
            [
                f"surface:{contract.channel}",
                f"session:{contract.session_id}",
                f"mission:{contract.mission_id}" if contract.mission_id else None,
                f"workflow:{workflow_profile}" if workflow_profile else None,
            ]
        )
        status = OrchestratorService._ecosystem_state_status(
            active_work_items=active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=surface_presence,
        )
        summary = (
            f"work_items={len(active_work_items)}; "
            f"artifacts={len(active_artifact_refs)}; "
            f"open_checkpoints={len(open_checkpoint_refs)}; "
            f"surfaces={len(surface_presence)}"
        )
        return EcosystemOperationalStateContract(
            ecosystem_state_status=status,
            active_work_items=active_work_items,
            active_artifact_refs=active_artifact_refs,
            open_checkpoint_refs=open_checkpoint_refs,
            surface_presence=surface_presence,
            state_summary=summary,
        )

    @staticmethod
    def _ecosystem_state_status(
        *,
        active_work_items: list[str],
        active_artifact_refs: list[str],
        open_checkpoint_refs: list[str],
        surface_presence: list[str],
    ) -> str:
        if not (
            active_work_items
            or active_artifact_refs
            or open_checkpoint_refs
            or surface_presence
        ):
            return "not_applicable"
        if surface_presence and active_work_items and (
            open_checkpoint_refs or active_artifact_refs
        ):
            return "operational_state_attached"
        return "partial_operational_state"

    @staticmethod
    def _dedupe_texts(items: list[str | None]) -> list[str]:
        deduped: list[str] = []
        for item in items:
            if item is None:
                continue
            value = str(item)
            if not value or value in deduped:
                continue
            deduped.append(value)
        return deduped

    @staticmethod
    def _initial_workflow_checkpoint_state(
        workflow_checkpoints: list[str],
        *,
        resume_status: str,
    ) -> dict[str, str]:
        if not workflow_checkpoints:
            return {}
        initial_state = "resume_ready" if resume_status == "resume_available" else "pending"
        return {checkpoint: initial_state for checkpoint in workflow_checkpoints}

    @staticmethod
    def _capability_decision_event_payload(
        source: DeliberativePlanContract | OperationDispatchContract,
        *,
        authorization_status: str | None = None,
    ) -> dict[str, object]:
        return {
            "capability_decision_status": source.capability_decision_status,
            "capability_decision_objective": source.capability_decision_objective,
            "capability_decision_reason": source.capability_decision_reason,
            "capability_decision_selected_mode": source.capability_decision_selected_mode,
            "capability_decision_authorization_status": (
                authorization_status or source.capability_decision_authorization_status
            ),
            "capability_decision_fallback_mode": source.capability_decision_fallback_mode,
            "capability_decision_tool_class": source.capability_decision_tool_class,
            "capability_decision_handoff_mode": source.capability_decision_handoff_mode,
            "capability_decision_eligible_capabilities": list(
                source.capability_decision_eligible_capabilities
            ),
            "capability_decision_selected_capabilities": list(
                source.capability_decision_selected_capabilities
            ),
        }

    @staticmethod
    def _request_identity_policy_payload(
        source: DeliberativePlanContract | OperationDispatchContract,
    ) -> dict[str, object]:
        return {
            "request_identity_status": source.request_identity_status,
            "request_active_mission": source.request_active_mission,
            "request_executive_posture": source.request_executive_posture,
            "request_authority_level": source.request_authority_level,
            "request_risk_profile": source.request_risk_profile,
            "request_reversibility_mode": source.request_reversibility_mode,
            "request_confirmation_mode": source.request_confirmation_mode,
            "request_identity_summary": source.request_identity_summary,
            "request_identity_policy_refs": list(source.request_identity_policy_refs),
        }

    @staticmethod
    def _ecosystem_operational_state_payload(source: object) -> dict[str, object]:
        return {
            "ecosystem_state_status": getattr(
                source,
                "ecosystem_state_status",
                None,
            ),
            "active_work_items": list(getattr(source, "active_work_items", []) or []),
            "active_artifact_refs": list(
                getattr(source, "active_artifact_refs", []) or []
            ),
            "open_checkpoint_refs": list(
                getattr(source, "open_checkpoint_refs", []) or []
            ),
            "surface_presence": list(getattr(source, "surface_presence", []) or []),
            "ecosystem_state_summary": getattr(
                source,
                "ecosystem_state_summary",
                None,
            ),
        }

    @staticmethod
    def _mind_domain_specialist_contract_payload(source: object) -> dict[str, object]:
        return {
            "mind_domain_specialist_contract_status": getattr(
                source,
                "mind_domain_specialist_contract_status",
                None,
            ),
            "mind_domain_specialist_contract_summary": getattr(
                source,
                "mind_domain_specialist_contract_summary",
                None,
            ),
            "mind_domain_specialist_contract_chain": getattr(
                source,
                "mind_domain_specialist_contract_chain",
                None,
            ),
            "mind_domain_specialist_active_specialist": getattr(
                source,
                "mind_domain_specialist_active_specialist",
                None,
            ),
            "mind_domain_specialist_override_mode": getattr(
                source,
                "mind_domain_specialist_override_mode",
                None,
            ),
            "mind_domain_specialist_fallback_mode": getattr(
                source,
                "mind_domain_specialist_fallback_mode",
                None,
            ),
            "mind_domain_specialist_consumer_mode": getattr(
                source,
                "mind_domain_specialist_consumer_mode",
                None,
            ),
            "mind_domain_specialist_framing_mode": getattr(
                source,
                "mind_domain_specialist_framing_mode",
                None,
            ),
            "mind_domain_specialist_continuity_mode": getattr(
                source,
                "mind_domain_specialist_continuity_mode",
                None,
            ),
        }

    @staticmethod
    def _mind_domain_specialist_dispatch_summary(
        *,
        plan: DeliberativePlanContract,
        specialist_review: SpecialistReview,
        consumer_mode: str,
    ) -> str | None:
        base_summary = plan.specialist_resolution_summary or specialist_review.summary
        contract_summary = plan.mind_domain_specialist_contract_summary
        if consumer_mode == "core_only_fallback":
            return (
                contract_summary
                or "fallback governado preservou o fechamento final no nucleo"
            )
        if contract_summary and base_summary:
            return f"{contract_summary}; {base_summary}"
        return contract_summary or base_summary

    @staticmethod
    def _capability_allows_specialist_handoff(plan: DeliberativePlanContract) -> bool:
        return plan.capability_decision_handoff_mode == "through_core_only"

    @staticmethod
    def _capability_allows_operation(plan: DeliberativePlanContract) -> bool:
        return (
            plan.capability_decision_selected_mode == "core_with_local_operation"
            and "local_safe_operation"
            in plan.capability_decision_selected_capabilities
        )

    @staticmethod
    def _resolve_capability_authorization_status(
        *,
        plan: DeliberativePlanContract,
        governance_decision: GovernanceDecisionContract,
        specialist_handoff_decision: GovernanceDecisionContract | None = None,
    ) -> str | None:
        if governance_decision.decision == PermissionDecision.BLOCK:
            return "blocked"
        if governance_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION:
            return "deferred_for_validation"
        if plan.capability_decision_selected_mode in {
            "clarification_only",
            "contained_guidance",
        }:
            return plan.capability_decision_authorization_status
        if plan.capability_decision_selected_mode == "core_with_local_operation":
            return (
                "authorized_with_conditions"
                if governance_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS
                else "authorized"
            )
        if (
            plan.capability_decision_handoff_mode == "through_core_only"
            and specialist_handoff_decision is not None
        ):
            if specialist_handoff_decision.decision == PermissionDecision.BLOCK:
                return "blocked"
            if specialist_handoff_decision.decision == PermissionDecision.DEFER_FOR_VALIDATION:
                return "deferred_for_validation"
            if specialist_handoff_decision.decision == PermissionDecision.ALLOW_WITH_CONDITIONS:
                return "authorized_with_conditions"
            return "authorized"
        return plan.capability_decision_authorization_status

    @staticmethod
    def _build_workflow_profile(
        plan: DeliberativePlanContract,
    ) -> tuple[str | None, str, list[str], list[str], list[str]]:
        if plan.primary_route is not None:
            primary_payload = route_metadata_payload(plan.primary_route)
            if primary_payload.get("workflow_profile"):
                return (
                    plan.primary_route,
                    str(primary_payload.get("workflow_profile") or "assisted_execution_workflow"),
                    list(primary_payload.get("workflow_steps", [])),
                    list(primary_payload.get("workflow_checkpoints", [])),
                    list(primary_payload.get("workflow_decision_points", [])),
                )
        route_workflow = resolve_workflow_route(plan.active_domains)
        if route_workflow is not None:
            route_name, route_entry = route_workflow
            return (
                route_name,
                route_entry.workflow_profile or "assisted_execution_workflow",
                list(route_entry.workflow_steps),
                list(route_entry.workflow_checkpoints),
                list(route_entry.workflow_decision_points),
            )
        if plan.recommended_task_type == "draft_plan":
            return (
                None,
                "deliberative_planning_workflow",
                [
                    "structure the goal and success criteria",
                    "sequence the smallest safe steps",
                    "emit checkpoints and the next safe action",
                ],
                ["goal_structured", "steps_sequenced", "next_action_defined"],
                [
                    "goal_scope_confirmed",
                    "step_sequence_validated",
                    "next_action_governed",
                ],
            )
        if plan.recommended_task_type == "produce_analysis_brief":
            return (
                None,
                "structured_analysis_workflow",
                [
                    "frame the question and decision context",
                    "compare evidence, risks and tradeoffs",
                    "emit a recommended interpretation",
                ],
                ["question_framed", "evidence_compared", "recommendation_emitted"],
                [
                    "question_frame_confirmed",
                    "tradeoff_review_governed",
                    "recommendation_governed",
                ],
            )
        return (
            None,
            "assisted_execution_workflow",
            [
                "preserve safe local scope",
                "apply the best bounded next action",
                "return a reversible result",
            ],
            ["scope_preserved", "action_applied", "result_returned"],
            [
                "local_scope_confirmed",
                "bounded_action_selected",
                "result_reversibility_confirmed",
            ],
        )

    def make_event(
        self,
        event_name: str,
        contract: InputContract,
        payload: dict[str, object],
    ) -> InternalEventEnvelope:
        """Build a canonical internal event envelope."""

        return InternalEventEnvelope(
            event_id=f"evt-{uuid4().hex[:8]}",
            event_name=event_name,
            timestamp=self.now(),
            source_service=self.name,
            payload=payload,
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            operation_id=str(payload.get("operation_id")) if payload.get("operation_id") else None,
            correlation_id=str(contract.request_id),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()

    def _build_planning_context(
        self,
        contract: InputContract,
        *,
        directive: ExecutiveDirective,
        memory_recovery_result: MemoryRecoveryResult,
        cognitive_snapshot,
        knowledge_result: KnowledgeRetrievalResult | None,
        memory_route_guidance: dict[str, object] | None = None,
    ) -> PlanningContext:
        recovered = memory_recovery_result.recovered_items
        canonical_domains = (
            list(knowledge_result.registry_domains)
            if knowledge_result
            else list(cognitive_snapshot.canonical_domains)
        )
        primary_route_contract = primary_route_payload(cognitive_snapshot.active_domains)
        primary_route_name = (
            primary_route_contract[0] if primary_route_contract is not None else None
        )
        primary_route_data = (
            primary_route_contract[1] if primary_route_contract is not None else {}
        )
        primary_canonical_domain = (
            self._resolve_primary_canonical_domain(
                active_domains=cognitive_snapshot.active_domains,
                canonical_domains=canonical_domains,
            )
        )
        route_guidance = memory_route_guidance or {}
        return PlanningContext(
            intent=directive.intent,
            query=contract.content,
            recovered_context=recovered,
            active_domains=cognitive_snapshot.active_domains,
            canonical_domains=canonical_domains,
            primary_canonical_domain=primary_canonical_domain,
            primary_route=primary_route_name,
            route_consumer_profile=(
                str(primary_route_data.get("consumer_profile"))
                if primary_route_data.get("consumer_profile") is not None
                else None
            ),
            route_consumer_objective=(
                str(primary_route_data.get("consumer_objective"))
                if primary_route_data.get("consumer_objective") is not None
                else None
            ),
            route_expected_deliverables=list(
                primary_route_data.get("expected_deliverables", [])
            ),
            route_telemetry_focus=list(primary_route_data.get("telemetry_focus", [])),
            route_workflow_profile=(
                str(primary_route_data.get("workflow_profile"))
                if primary_route_data.get("workflow_profile") is not None
                else None
            ),
            route_workflow_steps=list(primary_route_data.get("workflow_steps", [])),
            route_workflow_checkpoints=list(
                primary_route_data.get("workflow_checkpoints", [])
            ),
            route_workflow_decision_points=list(
                primary_route_data.get("workflow_decision_points", [])
            ),
            active_minds=cognitive_snapshot.active_minds,
            knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
            risk_markers=directive.risk_markers,
            requires_clarification=directive.requires_clarification,
            preferred_response_mode=directive.preferred_response_mode,
            cognitive_rationale=cognitive_snapshot.rationale,
            tensions=cognitive_snapshot.tensions,
            specialist_hints=cognitive_snapshot.specialist_hints,
            dominant_goal=directive.dominant_goal,
            secondary_goals=directive.secondary_goals,
            ambiguity_reason=directive.ambiguity_reason,
            identity_mode=directive.identity_mode,
            primary_mind=cognitive_snapshot.primary_mind,
            primary_mind_family=cognitive_snapshot.primary_mind_family,
            primary_domain_driver=cognitive_snapshot.primary_domain_driver,
            arbitration_source=cognitive_snapshot.arbitration_source,
            supporting_minds=cognitive_snapshot.supporting_minds,
            suppressed_minds=cognitive_snapshot.suppressed_minds,
            dominant_tension=cognitive_snapshot.dominant_tension,
            arbitration_summary=cognitive_snapshot.arbitration_summary,
            identity_continuity_brief=self._extract_context_hint(
                recovered, "identity_continuity_brief="
            ),
            open_loops=self._extract_list_hint(recovered, "open_loops="),
            mission_semantic_brief=self._extract_context_hint(recovered, "mission_semantic_brief="),
            mission_focus=self._extract_list_hint(recovered, "mission_focus=", separator=","),
            last_decision_frame=self._extract_context_hint(recovered, "last_decision_frame="),
            mission_goal=self._extract_context_hint(recovered, "mission_goal="),
            mission_recommendation=self._extract_context_hint(recovered, "mission_recommendation="),
            related_mission_id=(
                str(memory_recovery_result.continuity_context.related_candidates[0].mission_id)
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else None
            ),
            related_mission_goal=(
                memory_recovery_result.continuity_context.related_candidates[0].mission_goal
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else None
            ),
            related_continuity_reason=(
                memory_recovery_result.continuity_context.related_candidates[0].continuity_reason
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else None
            ),
            related_continuity_priority=(
                memory_recovery_result.continuity_context.related_candidates[0].priority_score
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else None
            ),
            related_continuity_confidence=(
                memory_recovery_result.continuity_context.related_candidates[0].confidence_score
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else None
            ),
            related_open_loops=(
                list(memory_recovery_result.continuity_context.related_candidates[0].open_loops)
                if (
                    memory_recovery_result.continuity_context
                    and memory_recovery_result.continuity_context.related_candidates
                )
                else []
            ),
            continuity_recommendation=(
                memory_recovery_result.continuity_context.recommended_action
                if memory_recovery_result.continuity_context
                else None
            ),
            continuity_ranking_summary=(
                memory_recovery_result.continuity_context.recommended_reason
                if memory_recovery_result.continuity_context
                else None
            ),
            continuity_replay_status=self._extract_context_hint(
                recovered, "continuity_replay_status="
            ),
            continuity_recovery_mode=self._extract_context_hint(
                recovered, "continuity_recovery_mode="
            ),
            continuity_resume_point=self._extract_context_hint(
                recovered, "continuity_resume_point="
            ),
            continuity_requires_manual_resume=(
                self._extract_context_hint(recovered, "continuity_replay_status=")
                in {"awaiting_validation", "contained"}
            ),
            memory_corpus_status=self._extract_context_hint(
                recovered, "memory_corpus_status="
            ),
            memory_retention_pressure=self._extract_context_hint(
                recovered, "memory_retention_pressure="
            ),
            user_scope_status=self._extract_context_hint(recovered, "user_scope_status="),
            user_domain_focus=self._extract_list_hint(
                recovered,
                "user_domain_focus=",
                separator=",",
            ),
            user_last_recommended_task_type=self._extract_context_hint(
                recovered,
                "user_last_recommended_task_type=",
            ),
            user_continuity_preference=self._extract_context_hint(
                recovered,
                "user_continuity_preference=",
            ),
            context_compaction_status=self._extract_context_hint(
                recovered, "context_compaction_status="
            ),
            context_compaction_summary=self._extract_context_hint(
                recovered, "context_compaction_summary="
            ),
            context_live_summary=self._extract_context_hint(
                recovered, "context_live_summary="
            ),
            cross_session_recall_status=self._extract_context_hint(
                recovered, "cross_session_recall_status="
            ),
            cross_session_recall_summary=self._extract_context_hint(
                recovered, "cross_session_recall_summary="
            ),
            memory_maintenance_status=self._extract_context_hint(
                recovered, "memory_maintenance_status="
            ),
            memory_maintenance_reason=self._extract_context_hint(
                recovered, "memory_maintenance_reason="
            ),
            memory_maintenance_fallback_mode=self._extract_context_hint(
                recovered, "memory_maintenance_fallback_mode="
            ),
            memory_priority_status=(
                str(route_guidance.get("status"))
                if route_guidance.get("status") is not None
                else "registry_only"
            ),
            memory_priority_domains=list(route_guidance.get("prioritized_domains", [])),
            memory_priority_specialists=list(
                route_guidance.get("prioritized_specialists", [])
            ),
            memory_priority_sources=list(route_guidance.get("sources", [])),
            memory_priority_summary=(
                str(route_guidance.get("summary"))
                if route_guidance.get("summary") is not None
                else None
            ),
            procedural_artifact_status=self._extract_context_hint(
                recovered, "procedural_artifact_status="
            ),
            procedural_artifact_ref=self._extract_context_hint(
                recovered, "procedural_artifact_ref="
            ),
            procedural_artifact_version=(
                int(version_hint)
                if (
                    version_hint := self._extract_context_hint(
                        recovered, "procedural_artifact_version="
                    )
                )
                else None
            ),
            procedural_artifact_summary=self._extract_context_hint(
                recovered, "procedural_artifact_summary="
            ),
        )

    def _domain_registry_event_payload(
        self,
        knowledge_result: KnowledgeRetrievalResult,
    ) -> dict[str, object]:
        route_metadata = {
            route_name: route_metadata_payload(route_name)
            for route_name in knowledge_result.active_domains
        }
        promoted_route_registry = promoted_specialist_route_payloads(
            knowledge_result.active_domains
        )
        primary_route = resolve_primary_route(knowledge_result.active_domains)
        primary_route_name = primary_route[0] if primary_route is not None else None
        primary_canonical_domain = (
            primary_canonical_domain_for_name(primary_route_name)
            if primary_route_name is not None
            else (
                knowledge_result.registry_domains[0]
                if knowledge_result.registry_domains
                else None
            )
        )
        return {
            "active_domains": knowledge_result.active_domains,
            "registry_domains": knowledge_result.registry_domains,
            "route_domains": knowledge_result.active_domains,
            "primary_route": primary_route_name,
            "primary_canonical_domain": primary_canonical_domain,
            "canonical_domain_refs_by_route": {
                route_name: metadata["canonical_domain_refs"]
                for route_name, metadata in route_metadata.items()
            },
            "route_modes": {
                route_name: metadata["specialist_mode"]
                for route_name, metadata in route_metadata.items()
                if metadata["specialist_mode"] is not None
            },
            "specialist_mode": {
                route_name: metadata["specialist_mode"]
                for route_name, metadata in route_metadata.items()
                if metadata["specialist_mode"] is not None
            },
            "route_maturity": {
                route_name: metadata["maturity"]
                for route_name, metadata in route_metadata.items()
            },
            "promoted_route_registry": promoted_route_registry,
            "linked_specialist_types": {
                route_name: metadata["linked_specialist_type"]
                for route_name, metadata in route_metadata.items()
                if metadata["linked_specialist_type"] is not None
            },
            "linked_specialist_type": {
                route_name: metadata["linked_specialist_type"]
                for route_name, metadata in route_metadata.items()
                if metadata["linked_specialist_type"] is not None
            },
            "consumer_profiles": {
                route_name: metadata["consumer_profile"]
                for route_name, metadata in route_metadata.items()
                if metadata["consumer_profile"] is not None
            },
            "consumer_objectives": {
                route_name: metadata["consumer_objective"]
                for route_name, metadata in route_metadata.items()
                if metadata["consumer_objective"] is not None
            },
            "expected_deliverables": {
                route_name: metadata["expected_deliverables"]
                for route_name, metadata in route_metadata.items()
                if metadata["expected_deliverables"]
            },
            "telemetry_focus": {
                route_name: metadata["telemetry_focus"]
                for route_name, metadata in route_metadata.items()
                if metadata["telemetry_focus"]
            },
            "workflow_profiles": {
                route_name: metadata["workflow_profile"]
                for route_name, metadata in route_metadata.items()
                if metadata["workflow_profile"] is not None
            },
            "workflow_profile": {
                route_name: metadata["workflow_profile"]
                for route_name, metadata in route_metadata.items()
                if metadata["workflow_profile"] is not None
            },
            "routing_sources": {
                route.domain_name: route.routing_source
                for route in knowledge_result.specialist_routes
            },
            "guided_domains": [
                route.domain_name
                for route in knowledge_result.specialist_routes
                if route.specialist_mode in {"guided", "active"}
            ],
            "shadow_domains": [
                route.domain_name
                for route in knowledge_result.specialist_routes
                if route.specialist_mode == "shadow"
            ],
        }

    @staticmethod
    def _specialist_registry_payloads(
        selections: list[object],
    ) -> dict[str, dict[str, object]]:
        payloads: dict[str, dict[str, object]] = {}
        for item in selections:
            specialist_type = getattr(item, "specialist_type", None)
            linked_domain = getattr(item, "linked_domain", None)
            if not specialist_type or not linked_domain:
                continue
            payloads[specialist_type] = specialist_route_payload(
                linked_domain,
                specialist_type,
            )
        return payloads

    @staticmethod
    def _resolve_primary_canonical_domain(
        *,
        active_domains: list[str],
        canonical_domains: list[str],
    ) -> str | None:
        primary_route = resolve_primary_route(active_domains)
        if primary_route is not None:
            return primary_canonical_domain_for_name(primary_route[0])
        return canonical_domains[0] if canonical_domains else None

    def _compose_response(
        self,
        *,
        directive: ExecutiveDirective,
        governance_decision: GovernanceDecisionContract,
        memory_recovery_result: MemoryRecoveryResult,
        cognitive_snapshot,
        knowledge_result: KnowledgeRetrievalResult | None,
        deliberative_plan: DeliberativePlanContract,
        specialist_review: SpecialistReview,
        operation_result: OperationResultContract | None,
    ) -> SynthesisResult:
        identity_profile = self.identity_engine.get_profile()
        guided_memory_runtime_hints = self._guided_memory_runtime_hints(
            specialist_review,
            deliberative_plan,
            memory_recovery_result.recovered_items,
        )
        return self.synthesis_engine.compose_result(
            SynthesisInput(
                intent=directive.intent,
                identity_profile=identity_profile,
                response_style=self.identity_engine.build_response_style(
                    intent=directive.intent,
                    blocked=governance_decision.decision
                    in {
                        PermissionDecision.BLOCK,
                        PermissionDecision.DEFER_FOR_VALIDATION,
                    },
                ),
                governance_decision=governance_decision,
                recovered_context=memory_recovery_result.recovered_items,
                active_minds=cognitive_snapshot.active_minds,
                active_domains=cognitive_snapshot.active_domains,
                knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
                deliberative_plan=deliberative_plan,
                specialist_contributions=specialist_review.contributions,
                operation_result=operation_result,
                identity_mode=directive.identity_mode,
                arbitration_summary=cognitive_snapshot.arbitration_summary,
                session_continuity_brief=self._extract_context_hint(
                    memory_recovery_result.recovered_items, "session_continuity_brief="
                ),
                session_continuity_mode=self._extract_context_hint(
                    memory_recovery_result.recovered_items, "session_continuity_mode="
                ),
                session_anchor_goal=self._extract_context_hint(
                    memory_recovery_result.recovered_items, "session_anchor_goal="
                ),
                context_compaction_status=self._extract_context_hint(
                    memory_recovery_result.recovered_items, "context_compaction_status="
                ),
                context_live_summary=self._extract_context_hint(
                    memory_recovery_result.recovered_items, "context_live_summary="
                ),
                cross_session_recall_status=self._extract_context_hint(
                    memory_recovery_result.recovered_items,
                    "cross_session_recall_status=",
                ),
                cross_session_recall_summary=self._extract_context_hint(
                    memory_recovery_result.recovered_items,
                    "cross_session_recall_summary=",
                ),
                guided_memory_specialists=guided_memory_runtime_hints[
                    "guided_memory_specialists"
                ],
                semantic_memory_focus=guided_memory_runtime_hints[
                    "semantic_memory_focus"
                ],
                procedural_memory_hint=guided_memory_runtime_hints[
                    "procedural_memory_hint"
                ],
                procedural_artifact_status=deliberative_plan.procedural_artifact_status,
                procedural_artifact_ref=deliberative_plan.procedural_artifact_ref,
                procedural_artifact_summary=deliberative_plan.procedural_artifact_summary,
            )
        )

    @staticmethod
    def _adaptive_intervention_response_payload(
        *,
        synthesis_result: SynthesisResult,
    ) -> dict[str, object]:
        return {
            "adaptive_intervention_workflow_priority_summary": (
                synthesis_result.adaptive_intervention_workflow_priority_summary
            ),
            "adaptive_intervention_preserved_checkpoint": (
                synthesis_result.adaptive_intervention_preserved_checkpoint
            ),
            "adaptive_intervention_preserved_gate": (
                synthesis_result.adaptive_intervention_preserved_gate
            ),
        }

    @staticmethod
    def _memory_maintenance_event_payload(
        *, deliberative_plan: DeliberativePlanContract
    ) -> dict[str, object]:
        return {
            "memory_maintenance_status": deliberative_plan.memory_maintenance_status,
            "memory_maintenance_reason": deliberative_plan.memory_maintenance_reason,
            "memory_maintenance_fallback_mode": (
                deliberative_plan.memory_maintenance_fallback_mode
            ),
            "context_compaction_status": deliberative_plan.context_compaction_status,
            "cross_session_recall_status": deliberative_plan.cross_session_recall_status,
        }

    @staticmethod
    def _guided_memory_runtime_hints(
        specialist_review: SpecialistReview,
        deliberative_plan: DeliberativePlanContract,
        recovered_context: list[str],
    ) -> dict[str, object]:
        guided_memory_specialists: list[str] = []
        semantic_memory_focus: list[str] = []
        procedural_memory_hint: str | None = None
        semantic_memory_available = False
        procedural_memory_available = False

        def extract_context_hint(prefix: str) -> str | None:
            for item in reversed(recovered_context):
                if item.startswith(prefix):
                    return item.removeprefix(prefix)
            return None

        def extract_list_hint(prefix: str, separator: str = ";") -> list[str]:
            value = extract_context_hint(prefix)
            if not value:
                return []
            return [part.strip() for part in value.split(separator) if part.strip()]

        def append_unique(values: list[str]) -> None:
            for value in values:
                if value and value not in semantic_memory_focus:
                    semantic_memory_focus.append(value)
                if len(semantic_memory_focus) >= 4:
                    break

        for invocation in specialist_review.invocations:
            context = invocation.shared_memory_context
            if context is None or invocation.selection_mode not in {"guided", "active"}:
                continue
            if context.consumer_mode != "domain_guided_memory_packet":
                continue
            if invocation.specialist_type not in guided_memory_specialists:
                guided_memory_specialists.append(invocation.specialist_type)
            consumed_classes = set(context.consumed_memory_classes)
            if "semantic" in consumed_classes:
                semantic_memory_available = True
                append_unique(context.semantic_focus)
            if "procedural" in consumed_classes:
                procedural_memory_available = True
                if procedural_memory_hint is None:
                    procedural_memory_hint = (
                        context.last_recommendation
                        or (context.open_loops[0] if context.open_loops else None)
                        or context.continuity_context_brief
                    )

        mission_focus = extract_list_hint("mission_focus=", separator=",")
        mission_semantic_brief = extract_context_hint("mission_semantic_brief=")
        mission_recommendation = extract_context_hint("mission_recommendation=")
        last_decision_frame = extract_context_hint("last_decision_frame=")
        user_continuity_preference = extract_context_hint("user_continuity_preference=")
        user_last_recommended_task_type = extract_context_hint(
            "user_last_recommended_task_type="
        )
        if (
            deliberative_plan.semantic_memory_source is not None
            or mission_focus
            or mission_semantic_brief is not None
        ):
            semantic_memory_available = True
            append_unique(
                [
                    *mission_focus,
                    mission_semantic_brief or "",
                    deliberative_plan.primary_canonical_domain or "",
                    deliberative_plan.primary_route or "",
                ]
            )
        if (
            deliberative_plan.procedural_memory_source is not None
            or mission_recommendation is not None
            or last_decision_frame is not None
            or user_continuity_preference is not None
            or user_last_recommended_task_type is not None
        ):
            procedural_memory_available = True
            if procedural_memory_hint is None:
                procedural_memory_hint = (
                    mission_recommendation
                    or last_decision_frame
                    or user_continuity_preference
                    or user_last_recommended_task_type
                    or deliberative_plan.smallest_safe_next_action
                )
        return {
            "guided_memory_specialists": guided_memory_specialists,
            "semantic_memory_available": semantic_memory_available,
            "procedural_memory_available": procedural_memory_available,
            "semantic_memory_focus": semantic_memory_focus,
            "procedural_memory_hint": procedural_memory_hint,
        }

    @staticmethod
    def _mind_domain_specialist_chain_payload(
        deliberative_plan: DeliberativePlanContract,
        *,
        planned_specialists: list[str],
        selected_specialists: list[str],
        selected_domains: list[str],
    ) -> dict[str, object]:
        primary_mind = deliberative_plan.primary_mind or "none"
        primary_domain_driver = deliberative_plan.primary_domain_driver or "none"
        primary_route = deliberative_plan.primary_route or "none"
        specialists = ",".join(selected_specialists[:3]) if selected_specialists else "none"
        domains = ",".join(selected_domains[:3]) if selected_domains else "none"
        planned = ",".join(planned_specialists[:3]) if planned_specialists else "none"
        planned_hint_match = bool(
            not planned_specialists
            or any(item in planned_specialists for item in selected_specialists)
        )
        route_match = bool(
            deliberative_plan.primary_route and deliberative_plan.primary_route in selected_domains
        )
        domain_match = bool(
            deliberative_plan.primary_domain_driver
            and deliberative_plan.primary_domain_driver
            in (deliberative_plan.canonical_domains or [])
        )
        if deliberative_plan.primary_domain_driver is None and not selected_specialists:
            status = "not_applicable"
        elif selected_specialists and route_match and domain_match and planned_hint_match:
            status = "aligned"
        elif selected_specialists and not planned_hint_match:
            status = "mismatch"
        elif selected_specialists and (route_match or domain_match):
            status = "evidence_partial"
        elif planned_specialists and not selected_specialists:
            status = "incomplete"
        elif selected_specialists:
            status = "attention_required"
        else:
            status = "incomplete"
        return {
            "status": status,
            "chain": (
                f"{primary_mind} -> {primary_domain_driver} -> {primary_route} -> "
                f"planned[{planned}] -> domains[{domains}] -> specialists[{specialists}]"
            ),
        }

    def _maybe_resolve_continuity_pause(self, contract: InputContract):
        resume_request = contract.metadata.get("continuity_resume")
        if not isinstance(resume_request, dict):
            return None
        approved = bool(resume_request.get("approved"))
        resolved_by = str(resume_request.get("resolved_by") or contract.user_id or "operator")
        resolution_note = str(
            resume_request.get("resolution_note") or "manual continuity resolution"
        )
        checkpoint_id = (
            str(resume_request["checkpoint_id"])
            if resume_request.get("checkpoint_id") is not None
            else None
        )
        return self.memory_service.resolve_session_continuity_pause(
            str(contract.session_id),
            approved=approved,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
            checkpoint_id=checkpoint_id,
        )

    def _run_native_continuity_subflow(
        self,
        contract: InputContract,
        events: list[InternalEventEnvelope],
    ) -> ContinuitySubflowResult:
        events = list(events)
        resolved_pause = self._maybe_resolve_continuity_pause(contract)
        if resolved_pause is not None:
            events.append(
                self.make_event(
                    "continuity_pause_resolved",
                    contract,
                    {
                        "checkpoint_id": resolved_pause.checkpoint_id,
                        "pause_status": resolved_pause.pause_status,
                        "resolution_status": resolved_pause.resolution_status,
                        "resolved_by": resolved_pause.resolved_by,
                    },
                )
            )

        memory_recovery_result = self.memory_service.recover_for_input(contract)
        continuity_replay = self.memory_service.get_session_continuity_replay(
            str(contract.session_id)
        )
        events.append(
            self.make_event(
                "memory_recovered",
                contract,
                {
                    "memory_query_id": str(
                        memory_recovery_result.recovery_contract.memory_query_id
                    ),
                    "recovery_type": memory_recovery_result.recovery_contract.recovery_type.value,
                    "continuity_recommendation": (
                        memory_recovery_result.continuity_context.recommended_action
                        if memory_recovery_result.continuity_context
                        else None
                    ),
                    "related_candidate_count": (
                        len(memory_recovery_result.continuity_context.related_candidates)
                        if memory_recovery_result.continuity_context
                        else 0
                    ),
                    "continuity_replay_status": (
                        continuity_replay.replay_status if continuity_replay else None
                    ),
                    "user_scope_status": (
                        memory_recovery_result.user_scope_context.context_status
                        if memory_recovery_result.user_scope_context
                        else "not_applicable"
                    ),
                    "user_scope_interaction_count": (
                        memory_recovery_result.user_scope_context.interaction_count
                        if memory_recovery_result.user_scope_context
                        else 0
                    ),
                    "user_context_brief": (
                        memory_recovery_result.user_scope_context.user_context_brief
                        if memory_recovery_result.user_scope_context
                        else None
                    ),
                    "context_compaction_status": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "context_compaction_status=",
                    ),
                    "context_compaction_summary": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "context_compaction_summary=",
                    ),
                    "context_live_summary": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "context_live_summary=",
                    ),
                    "cross_session_recall_status": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "cross_session_recall_status=",
                    ),
                    "cross_session_recall_summary": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "cross_session_recall_summary=",
                    ),
                    "memory_maintenance_status": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "memory_maintenance_status=",
                    ),
                    "memory_maintenance_reason": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "memory_maintenance_reason=",
                    ),
                    "memory_maintenance_fallback_mode": self._extract_context_hint(
                        memory_recovery_result.recovered_items,
                        "memory_maintenance_fallback_mode=",
                    ),
                    "user_scope_memory_refs": (
                        memory_recovery_result.user_scope_context.memory_refs
                        if memory_recovery_result.user_scope_context
                        else []
                    ),
                    "organization_scope_status": memory_recovery_result.organization_scope_status,
                    "organization_scope_reason": memory_recovery_result.organization_scope_reason,
                    "organization_scope_reopen_signal": (
                        memory_recovery_result.organization_scope_reopen_signal
                    ),
                },
            )
        )
        if continuity_replay is not None:
            events.append(
                self.make_event(
                    "continuity_replay_loaded",
                    contract,
                    {
                        "checkpoint_id": continuity_replay.checkpoint_id,
                        "replay_status": continuity_replay.replay_status,
                        "recovery_mode": continuity_replay.recovery_mode,
                        "resume_point": continuity_replay.resume_point,
                        "checkpoint_status": continuity_replay.checkpoint_status,
                        "requires_manual_resume": continuity_replay.requires_manual_resume,
                        "ecosystem_state_status": continuity_replay.ecosystem_state_status,
                        "active_work_items": continuity_replay.active_work_items,
                        "active_artifact_refs": continuity_replay.active_artifact_refs,
                        "open_checkpoint_refs": continuity_replay.open_checkpoint_refs,
                        "surface_presence": continuity_replay.surface_presence,
                        "ecosystem_state_summary": continuity_replay.ecosystem_state_summary,
                    },
                )
            )
            if continuity_replay.requires_manual_resume:
                events.append(
                    self.make_event(
                        "continuity_recovery_governed",
                        contract,
                        {
                            "checkpoint_id": continuity_replay.checkpoint_id,
                            "replay_status": continuity_replay.replay_status,
                            "recovery_mode": continuity_replay.recovery_mode,
                            "resume_point": continuity_replay.resume_point,
                        },
                    )
                )
        events.append(
            self.make_event(
                "continuity_subflow_completed",
                contract,
                self._build_continuity_subflow_payload(
                    runtime_mode="native_pipeline",
                    resolved_pause=resolved_pause,
                    memory_recovery_result=memory_recovery_result,
                    continuity_replay=continuity_replay,
                ),
            )
        )
        return ContinuitySubflowResult(
            memory_recovery_result=memory_recovery_result,
            continuity_replay=continuity_replay,
            resolved_pause=resolved_pause,
            events=events,
        )

    @staticmethod
    def _build_continuity_subflow_payload(
        *,
        runtime_mode: str,
        resolved_pause: ContinuityPauseContract | None,
        memory_recovery_result: MemoryRecoveryResult,
        continuity_replay: ContinuityReplayContract | None,
    ) -> dict[str, object]:
        continuity_context = memory_recovery_result.continuity_context
        return {
            "runtime_mode": runtime_mode,
            "subflow_name": "continuity_stateful",
            "checkpoint_id": continuity_replay.checkpoint_id if continuity_replay else None,
            "replay_status": continuity_replay.replay_status if continuity_replay else None,
            "recovery_mode": continuity_replay.recovery_mode if continuity_replay else None,
            "resume_point": continuity_replay.resume_point if continuity_replay else None,
            "requires_manual_resume": (
                continuity_replay.requires_manual_resume if continuity_replay else False
            ),
            "ecosystem_state_status": (
                continuity_replay.ecosystem_state_status if continuity_replay else None
            ),
            "ecosystem_state_summary": (
                continuity_replay.ecosystem_state_summary if continuity_replay else None
            ),
            "continuity_recommendation": (
                continuity_context.recommended_action if continuity_context else None
            ),
            "related_candidate_count": (
                len(continuity_context.related_candidates) if continuity_context else 0
            ),
            "pause_status": resolved_pause.pause_status if resolved_pause else None,
            "pause_resolution_status": (
                resolved_pause.resolution_status if resolved_pause else None
            ),
            "pause_resolved_by": resolved_pause.resolved_by if resolved_pause else None,
        }

    @staticmethod
    def _build_specialist_subflow_payload(
        *,
        runtime_mode: str,
        handoff_plan: SpecialistHandoffPlan,
        handoff_governance: GovernanceDecisionContract,
        specialist_review: SpecialistReview,
        refined_plan: DeliberativePlanContract,
        original_plan: DeliberativePlanContract,
    ) -> dict[str, object]:
        selected_specialists = [
            item.specialist_type
            for item in handoff_plan.selections
            if item.selection_status == "selected"
        ]
        domain_specialists = [
            item.specialist_type
            for item in specialist_review.invocations
            if item.linked_domain
        ]
        shadow_invocation_ids = {
            item.invocation_id
            for item in specialist_review.invocations
            if item.selection_mode == "shadow"
        }
        live_contributions = [
            item
            for item in specialist_review.contributions
            if item.invocation_id not in shadow_invocation_ids
        ]
        if not selected_specialists:
            selection_status = "not_applicable"
        else:
            selection_status = "selected"
        if handoff_governance.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            governance_status = "contained"
        elif handoff_governance.decision == PermissionDecision.ALLOW_WITH_CONDITIONS:
            governance_status = "approved_with_conditions"
        else:
            governance_status = "approved"
        if specialist_review.invocations:
            dispatch_status = "dispatched"
        elif selected_specialists:
            dispatch_status = "suppressed"
        else:
            dispatch_status = "not_applicable"
        if specialist_review.contributions:
            completion_status = "completed"
        elif handoff_governance.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            completion_status = "contained"
        elif selected_specialists:
            completion_status = "no_contribution"
        else:
            completion_status = "not_applicable"
        if live_contributions and refined_plan != original_plan:
            refinement_status = "refined"
        elif live_contributions:
            refinement_status = "unchanged"
        else:
            refinement_status = "not_applicable"
        return {
            "runtime_mode": runtime_mode,
            "subflow_name": "specialist_handoffs",
            "selection_status": selection_status,
            "governance_status": governance_status,
            "dispatch_status": dispatch_status,
            "completion_status": completion_status,
            "refinement_status": refinement_status,
            "selection_count": len(selected_specialists),
            "invocation_count": len(specialist_review.invocations),
            "contribution_count": len(specialist_review.contributions),
            "live_contribution_count": len(live_contributions),
            "selected_specialists": selected_specialists,
            "domain_specialists": domain_specialists,
            "shadow_specialists": [
                item.specialist_type
                for item in specialist_review.invocations
                if item.selection_mode == "shadow"
            ],
            "guided_specialists": [
                item.specialist_type
                for item in specialist_review.invocations
                if item.selection_mode in {"guided", "active"}
            ],
            "governance_decision": handoff_governance.decision.value,
            "specialist_hints": list(specialist_review.specialist_hints),
            "boundary_summary": specialist_review.boundary_summary,
            "specialist_summary": specialist_review.summary,
            "mind_domain_specialist_contract_status": (
                specialist_review.mind_domain_specialist_contract_status
            ),
            "mind_domain_specialist_contract_summary": (
                specialist_review.mind_domain_specialist_contract_summary
            ),
            "mind_domain_specialist_contract_chain": (
                specialist_review.mind_domain_specialist_contract_chain
            ),
            "mind_domain_specialist_active_specialist": (
                specialist_review.mind_domain_specialist_active_specialist
            ),
            "mind_domain_specialist_override_mode": (
                specialist_review.mind_domain_specialist_override_mode
            ),
            "mind_domain_specialist_fallback_mode": (
                specialist_review.mind_domain_specialist_fallback_mode
            ),
        }

    def _build_mission_runtime_state(
        self,
        contract: InputContract,
        *,
        deliberative_plan: DeliberativePlanContract,
        memory_recovery_result: MemoryRecoveryResult,
        specialist_review: SpecialistReview,
        runtime_mode: str,
    ) -> MissionRuntimeStateContract:
        mission_id = contract.mission_id
        assert mission_id is not None
        mission_state = self.memory_service.get_mission_state(str(mission_id))
        continuity_context = memory_recovery_result.continuity_context
        return MissionRuntimeStateContract(
            mission_id=mission_id,
            mission_goal=(
                mission_state.mission_goal
                if mission_state is not None
                else contract.content
            ),
            mission_status=(
                mission_state.mission_status
                if mission_state is not None
                else (
                    MissionStatus.PAUSED
                    if deliberative_plan.continuity_replay_status == "awaiting_validation"
                    else MissionStatus.ACTIVE
                )
            ),
            continuity_action=deliberative_plan.continuity_action,
            continuity_source=deliberative_plan.continuity_source,
            updated_at=datetime.now(UTC).isoformat(),
            continuity_target_mission_id=deliberative_plan.continuity_target_mission_id,
            continuity_target_goal=deliberative_plan.continuity_target_goal,
            continuity_recommendation=(
                continuity_context.recommended_action if continuity_context else None
            ),
            continuity_replay_status=deliberative_plan.continuity_replay_status,
            continuity_recovery_mode=deliberative_plan.continuity_recovery_mode,
            continuity_resume_point=deliberative_plan.continuity_resume_point,
            requires_manual_resume=(
                deliberative_plan.continuity_replay_status in {"awaiting_validation", "contained"}
            ),
            primary_route=deliberative_plan.primary_route,
            workflow_profile=deliberative_plan.route_workflow_profile,
            active_tasks=(
                list(mission_state.active_tasks)
                if mission_state is not None and mission_state.active_tasks
                else list(deliberative_plan.steps[:3])
            ),
            open_loops=(
                list(mission_state.open_loops)
                if mission_state is not None and mission_state.open_loops
                else list(deliberative_plan.open_loops)
            ),
            last_recommendation=(
                mission_state.last_recommendation
                if mission_state is not None and mission_state.last_recommendation
                else (
                    specialist_review.summary
                    if specialist_review.summary != "core_only"
                    else deliberative_plan.plan_summary
                )
            ),
            related_mission_id=(
                continuity_context.related_candidates[0].mission_id
                if continuity_context and continuity_context.related_candidates
                else None
            ),
            related_mission_goal=(
                continuity_context.related_candidates[0].mission_goal
                if continuity_context and continuity_context.related_candidates
                else None
            ),
            ecosystem_state_status=(
                mission_state.ecosystem_state_status if mission_state is not None else None
            ),
            active_work_items=(
                list(mission_state.active_work_items)
                if mission_state is not None
                else []
            ),
            active_artifact_refs=(
                list(mission_state.active_artifact_refs)
                if mission_state is not None
                else []
            ),
            open_checkpoint_refs=(
                list(mission_state.open_checkpoint_refs)
                if mission_state is not None
                else []
            ),
            surface_presence=(
                list(mission_state.surface_presence)
                if mission_state is not None
                else []
            ),
            ecosystem_state_summary=(
                mission_state.ecosystem_state_summary if mission_state is not None else None
            ),
            runtime_mode=runtime_mode,
        )

    @staticmethod
    def _extract_context_hint(recovered_context: list[str], prefix: str) -> str | None:
        for item in reversed(recovered_context):
            if item.startswith(prefix):
                return item.removeprefix(prefix)
        return None

    @staticmethod
    def _extract_list_hint(
        recovered_context: list[str],
        prefix: str,
        *,
        separator: str = ";",
    ) -> list[str]:
        for item in reversed(recovered_context):
            if item.startswith(prefix):
                raw = item.removeprefix(prefix)
                return [part.strip() for part in raw.split(separator) if part.strip()]
        return []

    @staticmethod
    def _memory_route_guidance(
        *,
        active_domains: list[str],
        recovered_context: list[str],
    ) -> dict[str, object]:
        if not active_domains:
            return {
                "status": "registry_only",
                "prioritized_domains": [],
                "prioritized_specialists": [],
                "sources": [],
                "summary": None,
            }

        mission_focus = OrchestratorService._extract_list_hint(
            recovered_context,
            "mission_focus=",
            separator=",",
        )
        user_domain_focus = OrchestratorService._extract_list_hint(
            recovered_context,
            "user_domain_focus=",
            separator=",",
        )
        continuity_recommendation = OrchestratorService._extract_context_hint(
            recovered_context,
            "continuity_recommendation=",
        )
        procedural_artifact_status = OrchestratorService._extract_context_hint(
            recovered_context,
            "procedural_artifact_status=",
        )
        related_priority_raw = OrchestratorService._extract_context_hint(
            recovered_context,
            "related_continuity_priority=",
        )
        try:
            related_priority = float(related_priority_raw) if related_priority_raw else None
        except ValueError:
            related_priority = None

        focus_sources = {
            "mission_focus": set(mission_focus),
            "user_scope": set(user_domain_focus),
        }
        scores: dict[str, int] = {}
        reasons_by_domain: dict[str, list[str]] = {}
        prioritized_specialists: list[str] = []
        sources: list[str] = []

        for route_name in active_domains:
            metadata = route_metadata_payload(route_name)
            match_tokens = {route_name, *metadata["canonical_domain_refs"]}
            score = 0
            reasons: list[str] = []

            for source_name, focus_values in focus_sources.items():
                if focus_values.intersection(match_tokens):
                    weight = 4 if source_name == "mission_focus" else 3
                    score += weight
                    reasons.append(source_name)
                    if source_name not in sources:
                        sources.append(source_name)

            if (
                continuity_recommendation == "retomar_missao_relacionada"
                and related_priority is not None
                and related_priority >= 0.6
                and reasons
            ):
                score += 2
                reasons.append("continuity_ranking")
                if "continuity_ranking" not in sources:
                    sources.append("continuity_ranking")

            if (
                procedural_artifact_status in {"candidate", "reusable", "fixed"}
                and metadata["linked_specialist_type"] is not None
            ):
                score += 1
                reasons.append("procedural_artifact")
                if "procedural_artifact" not in sources:
                    sources.append("procedural_artifact")

            if score <= 0:
                continue
            scores[route_name] = score
            reasons_by_domain[route_name] = reasons
            specialist_type = metadata["linked_specialist_type"]
            if specialist_type is not None and specialist_type not in prioritized_specialists:
                prioritized_specialists.append(str(specialist_type))

        if not scores:
            return {
                "status": "registry_only",
                "prioritized_domains": [],
                "prioritized_specialists": [],
                "sources": [],
                "summary": None,
            }

        prioritized_domains = sorted(
            scores,
            key=lambda route_name: (-scores[route_name], active_domains.index(route_name)),
        )
        sources = [
            source_name
            for source_name in (
                "mission_focus",
                "user_scope",
                "continuity_ranking",
                "procedural_artifact",
            )
            if source_name in sources
        ]
        summary = " > ".join(
            f"{route_name}:{scores[route_name]}[{','.join(reasons_by_domain[route_name])}]"
            for route_name in prioritized_domains
        )
        return {
            "status": "memory_guided",
            "prioritized_domains": prioritized_domains,
            "prioritized_specialists": prioritized_specialists,
            "sources": sources,
            "summary": summary,
        }

    @staticmethod
    def _build_response_from_state(state: dict[str, object]) -> OrchestratorResponse:
        contract = state["contract"]
        directive = state["directive"]
        deliberative_plan = state["deliberative_plan"]
        governance_check = state["governance_check"]
        governance_decision = state["governance_decision"]
        memory_recovery_result = state["memory_recovery_result"]
        memory_record_result = state["memory_record_result"]
        cognitive_snapshot = state["cognitive_snapshot"]
        specialist_review = state["specialist_review"]
        return OrchestratorResponse(
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            intent=directive.intent,
            response_text=state["response_text"],
            directive=directive,
            deliberative_plan=deliberative_plan,
            governance_check=governance_check,
            governance_decision=governance_decision,
            memory_recovery=memory_recovery_result.recovery_contract,
            memory_record=memory_record_result.record_contract,
            recovered_context=memory_recovery_result.recovered_items,
            knowledge_result=state["knowledge_result"],
            artifact_results=state["artifact_results"],
            active_minds=cognitive_snapshot.active_minds,
            active_domains=cognitive_snapshot.active_domains,
            cognitive_tensions=deliberative_plan.tensions_considered,
            specialist_hints=deliberative_plan.specialist_hints,
            specialist_invocations=specialist_review.invocations,
            specialist_boundary_summary=specialist_review.boundary_summary,
            mission_runtime_state=state.get("mission_runtime_state"),
            specialist_handoff_check=state.get("specialist_handoff_check"),
            specialist_handoff_decision=state.get("specialist_handoff_decision"),
            specialist_review=specialist_review,
            operation_dispatch=state["operation_dispatch"],
            operation_result=state["operation_result"],
            events=state["events"],
        )
