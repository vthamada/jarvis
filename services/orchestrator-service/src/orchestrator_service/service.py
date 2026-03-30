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
from synthesis_engine.engine import SynthesisEngine, SynthesisInput

from shared.contracts import (
    ArtifactResultContract,
    DeliberativePlanContract,
    GovernanceCheckContract,
    GovernanceDecisionContract,
    InputContract,
    MemoryRecordContract,
    MemoryRecoveryContract,
    OperationDispatchContract,
    OperationResultContract,
    SpecialistInvocationContract,
)
from shared.domain_registry import canonical_domain_refs_for_name
from shared.events import InternalEventEnvelope
from shared.types import OperationId, PermissionDecision, RequestId


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
    specialist_handoff_check: GovernanceCheckContract | None = None
    specialist_handoff_decision: GovernanceDecisionContract | None = None
    specialist_review: SpecialistReview | None = None
    operation_dispatch: OperationDispatchContract | None = None
    operation_result: OperationResultContract | None = None
    events: list[InternalEventEnvelope] = field(default_factory=list)


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
                    {
                        "active_domains": knowledge_result.active_domains,
                        "registry_domains": knowledge_result.registry_domains,
                        "route_domains": knowledge_result.active_domains,
                        "canonical_domain_refs_by_route": {
                            route.domain_name: route.canonical_domain_refs
                            for route in knowledge_result.specialist_routes
                        },
                        "route_modes": {
                            route.domain_name: route.specialist_mode
                            for route in knowledge_result.specialist_routes
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
                    },
                )
            )

        cognitive_snapshot = self.cognitive_engine.build_snapshot(
            intent=directive.intent,
            risk_markers=directive.risk_markers,
            retrieved_domains=knowledge_result.active_domains if knowledge_result else [],
            domain_specialist_routes=(
                knowledge_result.specialist_routes if knowledge_result else []
            ),
            mind_hints=directive.mind_hints,
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
                    "specialist_hints": cognitive_snapshot.specialist_hints,
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
            )
        )
        events.append(
            self.make_event(
                "plan_built",
                contract,
                {
                    "recommended_task_type": deliberative_plan.recommended_task_type,
                    "requires_human_validation": deliberative_plan.requires_human_validation,
                    "steps": deliberative_plan.steps,
                    "dominant_tension": deliberative_plan.dominant_tension,
                    "smallest_safe_next_action": deliberative_plan.smallest_safe_next_action,
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
        ):
            operation_dispatch = self.build_operation_dispatch(
                contract,
                plan=deliberative_plan,
                specialist_review=specialist_review,
            )
            events.append(
                self.make_event(
                    "operation_dispatched",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "task_type": operation_dispatch.task_type,
                        "specialist_hints": operation_dispatch.specialist_hints,
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

        response_text = self._compose_response_text(
            directive=directive,
            governance_decision=governance_decision,
            memory_recovery_result=memory_recovery_result,
            cognitive_snapshot=cognitive_snapshot,
            knowledge_result=knowledge_result,
            deliberative_plan=deliberative_plan,
            specialist_review=specialist_review,
            operation_result=operation_result,
        )
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
        shared_memory_contexts = self.memory_service.prepare_specialist_shared_memory(
            session_id=str(contract.session_id),
            specialist_hints=list(deliberative_plan.specialist_hints),
            active_domains=list(deliberative_plan.active_domains),
            mission_id=str(contract.mission_id) if contract.mission_id else None,
            continuity_context=memory_recovery_result.continuity_context,
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
                    },
                )
            )
            if domain_contributions:
                updated_events.append(
                    self.make_event(
                        "domain_specialist_completed",
                        contract,
                        {
                            "specialist_types": [
                                item.specialist_type for item in domain_contributions
                            ],
                            "invocation_ids": [item.invocation_id for item in domain_contributions],
                            "linked_domains": {
                                invocation.specialist_type: invocation.linked_domain
                                for invocation in domain_invocation_index.values()
                            },
                            "selection_modes": {
                                invocation.specialist_type: invocation.selection_mode
                                for invocation in domain_invocation_index.values()
                            },
                            "canonical_domain_refs": {
                                invocation.specialist_type: (
                                    list(canonical_domain_refs_for_name(invocation.linked_domain))
                                    if invocation.linked_domain
                                    else []
                                )
                                for invocation in domain_invocation_index.values()
                            },
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
                        },
                    )
                )
                return specialist_review, refined_plan, updated_events
        return specialist_review, deliberative_plan, updated_events

    def build_operation_dispatch(
        self,
        contract: InputContract,
        *,
        plan: DeliberativePlanContract,
        specialist_review: SpecialistReview,
    ) -> OperationDispatchContract:
        """Create the operational dispatch for an allowed request."""

        return OperationDispatchContract(
            operation_id=OperationId(f"op-{uuid4().hex[:8]}"),
            request_id=RequestId(str(contract.request_id)),
            task_type=plan.recommended_task_type,
            task_goal=plan.goal,
            task_plan=plan.plan_summary,
            constraints=list(plan.constraints),
            expected_output="text_brief",
            plan_summary=plan.plan_summary,
            planned_steps=list(plan.steps),
            plan_risks=list(plan.risks),
            plan_rationale=plan.rationale,
            specialist_summary=plan.specialist_resolution_summary or specialist_review.summary,
            specialist_findings=list(specialist_review.findings),
            success_criteria=list(plan.success_criteria),
            smallest_safe_next_action=plan.smallest_safe_next_action,
            requires_human_validation=plan.requires_human_validation,
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            domain_hints=list(plan.active_domains),
            specialist_hints=list(plan.specialist_hints),
            priority_hint=contract.priority_hint,
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
    ) -> PlanningContext:
        recovered = memory_recovery_result.recovered_items
        return PlanningContext(
            intent=directive.intent,
            query=contract.content,
            recovered_context=recovered,
            active_domains=cognitive_snapshot.active_domains,
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
            supporting_minds=cognitive_snapshot.supporting_minds,
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
        )

    def _compose_response_text(
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
    ) -> str:
        identity_profile = self.identity_engine.get_profile()
        return self.synthesis_engine.compose(
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
            )
        )

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
            specialist_handoff_check=state.get("specialist_handoff_check"),
            specialist_handoff_decision=state.get("specialist_handoff_decision"),
            specialist_review=specialist_review,
            operation_dispatch=state["operation_dispatch"],
            operation_result=state["operation_result"],
            events=state["events"],
        )
