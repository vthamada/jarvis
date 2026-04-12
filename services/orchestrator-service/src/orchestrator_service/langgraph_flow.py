"""Optional LangGraph flow for the orchestrator service."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from shared.types import PermissionDecision

if TYPE_CHECKING:
    from orchestrator_service.service import OrchestratorResponse, OrchestratorService
    from shared.contracts import InputContract


class OrchestratorFlowState(TypedDict, total=False):
    # Keep the LangGraph flow state runtime-safe even when optional type-only
    # imports are unavailable during TypedDict introspection.
    contract: object
    directive: object
    memory_recovery_result: object
    knowledge_result: object | None
    cognitive_snapshot: object
    deliberative_plan: object
    specialist_review: object
    specialist_handoff_check: object | None
    specialist_handoff_decision: object | None
    mission_runtime_state: object | None
    governance_check: object
    governance_decision: object
    operation_dispatch: object | None
    operation_result: object | None
    artifact_results: list[object]
    memory_record_result: object
    response_text: str
    events: list[object]
    continuity_replay: object | None


class ContinuityFlowState(TypedDict, total=False):
    contract: object
    events: list[object]
    resolved_pause: object | None
    memory_recovery_result: object
    continuity_replay: object | None


class LangGraphFlowRunner:
    """Compose the current orchestrator flow as an optional LangGraph path."""

    def __init__(self, orchestrator: OrchestratorService) -> None:
        self.orchestrator = orchestrator

    def run(self, contract: InputContract) -> OrchestratorResponse:
        state_graph, start_token, end_token = _load_langgraph()
        graph = state_graph(OrchestratorFlowState)
        graph.add_node("run_continuity_subflow", self._run_continuity_subflow)
        graph.add_node("classify_directive", self._classify_directive)
        graph.add_node("retrieve_knowledge", self._retrieve_knowledge)
        graph.add_node("compose_context", self._compose_context)
        graph.add_node("build_plan", self._build_plan)
        graph.add_node("review_specialists", self._review_specialists)
        graph.add_node("govern_plan", self._govern_plan)
        graph.add_node("execute_operation", self._execute_operation)
        graph.add_node("synthesize_response", self._synthesize_response)
        graph.add_node("record_memory", self._record_memory)
        graph.add_edge(start_token, "run_continuity_subflow")
        graph.add_edge("run_continuity_subflow", "classify_directive")
        graph.add_edge("classify_directive", "retrieve_knowledge")
        graph.add_edge("retrieve_knowledge", "compose_context")
        graph.add_edge("compose_context", "build_plan")
        graph.add_edge("build_plan", "review_specialists")
        graph.add_edge("review_specialists", "govern_plan")
        graph.add_edge("govern_plan", "execute_operation")
        graph.add_edge("execute_operation", "synthesize_response")
        graph.add_edge("synthesize_response", "record_memory")
        graph.add_edge("record_memory", end_token)
        runner = graph.compile()
        final_state = runner.invoke(
            {
                "contract": contract,
                "events": [
                    self.orchestrator.make_event(
                        "input_received",
                        contract,
                        {"content": contract.content, "channel": contract.channel.value},
                    )
                ],
            }
        )
        self.orchestrator.observability_service.ingest_events(final_state["events"])
        return self.orchestrator._build_response_from_state(final_state)

    def _run_continuity_subflow(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        subflow = LangGraphContinuityFlowRunner(self.orchestrator)
        continuity_state = subflow.run(
            contract=state["contract"],
            events=list(state["events"]),
        )
        return {
            "memory_recovery_result": continuity_state["memory_recovery_result"],
            "continuity_replay": continuity_state.get("continuity_replay"),
            "events": continuity_state["events"],
        }

    def _classify_directive(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = self.orchestrator.executive_engine.direct(contract)
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
                "intent_classified",
                contract,
                {"intent": directive.intent},
            )
        )
        events.append(
            self.orchestrator.make_event(
                "directive_composed",
                contract,
                {
                    "intent": directive.intent,
                    "intent_confidence": directive.intent_confidence,
                    "requires_clarification": directive.requires_clarification,
                    "preferred_response_mode": directive.preferred_response_mode,
                },
            )
        )
        if directive.requires_clarification:
            events.append(
                self.orchestrator.make_event(
                    "clarification_required",
                    contract,
                    {"intent": directive.intent, "reason": "insufficient_goal_clarity"},
                )
            )
        return {"directive": directive, "events": events}

    def _retrieve_knowledge(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        events = list(state["events"])
        knowledge_result = None
        if directive.should_query_knowledge:
            knowledge_result = self.orchestrator.knowledge_service.retrieve_for_intent(
                intent=directive.intent,
                query=contract.content,
            )
            events.append(
                self.orchestrator.make_event(
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
                self.orchestrator.make_event(
                    "domain_registry_resolved",
                    contract,
                    self.orchestrator._domain_registry_event_payload(knowledge_result),
                )
            )
        return {"knowledge_result": knowledge_result, "events": events}

    def _compose_context(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        knowledge_result = state.get("knowledge_result")
        cognitive_snapshot = self.orchestrator.cognitive_engine.build_snapshot(
            intent=directive.intent,
            risk_markers=directive.risk_markers,
            retrieved_domains=knowledge_result.active_domains if knowledge_result else [],
            domain_specialist_routes=(
                knowledge_result.specialist_routes if knowledge_result else []
            ),
            mind_hints=directive.mind_hints,
        )
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
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
                    "tensions": cognitive_snapshot.tensions,
                    "dominant_tension": cognitive_snapshot.dominant_tension,
                    "arbitration_summary": cognitive_snapshot.arbitration_summary,
                    "arbitration_source": cognitive_snapshot.arbitration_source,
                    "specialist_hints": cognitive_snapshot.specialist_hints,
                },
            )
        )
        return {"cognitive_snapshot": cognitive_snapshot, "events": events}

    def _build_plan(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        memory_recovery_result = state["memory_recovery_result"]
        cognitive_snapshot = state["cognitive_snapshot"]
        knowledge_result = state.get("knowledge_result")
        deliberative_plan = self.orchestrator.planning_engine.build_task_plan(
            self.orchestrator._build_planning_context(
                contract,
                directive=directive,
                memory_recovery_result=memory_recovery_result,
                cognitive_snapshot=cognitive_snapshot,
                knowledge_result=knowledge_result,
            )
        )
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
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
                    "tensions": deliberative_plan.tensions_considered,
                    "specialist_hints": deliberative_plan.specialist_hints,
                    "continuity_action": deliberative_plan.continuity_action,
                    "continuity_source": deliberative_plan.continuity_source,
                    "continuity_reason": deliberative_plan.continuity_reason,
                },
            )
        )
        events.append(
            self.orchestrator.make_event(
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
        return {"deliberative_plan": deliberative_plan, "events": events}

    def _review_specialists(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        deliberative_plan = state["deliberative_plan"]
        knowledge_result = state.get("knowledge_result")
        handoff_plan, events = self.orchestrator._plan_specialist_handoffs(
            contract,
            directive=directive,
            deliberative_plan=deliberative_plan,
            memory_recovery_result=state["memory_recovery_result"],
            knowledge_result=knowledge_result,
            events=list(state["events"]),
        )
        handoff_assessment, events = self.orchestrator._govern_specialist_handoffs(
            contract,
            deliberative_plan=deliberative_plan,
            handoff_plan=handoff_plan,
            events=events,
        )
        specialist_review, refined_plan, events = (
            self.orchestrator._execute_specialist_handoffs(
                contract,
                directive=directive,
                deliberative_plan=deliberative_plan,
                knowledge_result=knowledge_result,
                handoff_plan=handoff_plan,
                handoff_governance=handoff_assessment.governance_decision,
                events=events,
                runtime_mode="langgraph_subflow",
            )
        )
        mission_runtime_state, events = self.orchestrator._declare_mission_runtime_state(
            contract,
            deliberative_plan=refined_plan,
            memory_recovery_result=state["memory_recovery_result"],
            specialist_review=specialist_review,
            events=events,
            runtime_mode="langgraph_subflow",
        )
        return {
            "specialist_review": specialist_review,
            "specialist_handoff_check": handoff_assessment.governance_check,
            "specialist_handoff_decision": handoff_assessment.governance_decision,
            "mission_runtime_state": mission_runtime_state,
            "deliberative_plan": refined_plan,
            "events": events,
        }

    def _govern_plan(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        deliberative_plan = state["deliberative_plan"]
        assessment = self.orchestrator.governance_service.assess_request(
            contract,
            intent=directive.intent,
            requested_by_service=self.orchestrator.name,
            plan=deliberative_plan,
        )
        governance_check = assessment.governance_check
        governance_decision = assessment.governance_decision
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
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
            self.orchestrator.make_event(
                "plan_governed",
                contract,
                {
                    "governance_check_id": str(governance_check.governance_check_id),
                    "proposed_effect": governance_check.proposed_effect,
                    "decision": governance_decision.decision.value,
                    **self.orchestrator._capability_decision_event_payload(
                        deliberative_plan,
                        authorization_status=(
                            self.orchestrator._resolve_capability_authorization_status(
                                plan=deliberative_plan,
                                governance_decision=governance_decision,
                                specialist_handoff_decision=state.get(
                                    "specialist_handoff_decision"
                                ),
                            )
                        ),
                    ),
                },
            )
        )
        if governance_decision.decision in {
            PermissionDecision.BLOCK,
            PermissionDecision.DEFER_FOR_VALIDATION,
        }:
            events.append(
                self.orchestrator.make_event(
                    "governance_blocked",
                    contract,
                    {
                        "decision_id": str(governance_decision.decision_id),
                        "justification": governance_decision.justification,
                    },
                )
            )
        return {
            "governance_check": governance_check,
            "governance_decision": governance_decision,
            "events": events,
        }

    def _execute_operation(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        governance_decision = state["governance_decision"]
        deliberative_plan = state["deliberative_plan"]
        specialist_review = state["specialist_review"]
        events = list(state["events"])
        operation_dispatch = None
        operation_result = None
        artifact_results: list[object] = []
        mission_runtime_state = state.get("mission_runtime_state")
        if (
            governance_decision.decision
            in {
                PermissionDecision.ALLOW,
                PermissionDecision.ALLOW_WITH_CONDITIONS,
            }
            and directive.should_execute_operation
            and self.orchestrator._capability_allows_operation(deliberative_plan)
        ):
            capability_authorization_status = (
                self.orchestrator._resolve_capability_authorization_status(
                    plan=deliberative_plan,
                    governance_decision=governance_decision,
                    specialist_handoff_decision=state.get("specialist_handoff_decision"),
                )
            )
            operation_dispatch = self.orchestrator.build_operation_dispatch(
                contract,
                plan=deliberative_plan,
                specialist_review=specialist_review,
                mission_runtime_state=mission_runtime_state,
                authorization_status=capability_authorization_status,
            )
            events.append(
                self.orchestrator.make_event(
                    "workflow_composed",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_objective": operation_dispatch.workflow_objective,
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
                        **self.orchestrator._capability_decision_event_payload(
                            operation_dispatch
                        ),
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
                    },
                )
            )
            events.append(
                self.orchestrator.make_event(
                    "workflow_governance_declared",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
                        "workflow_state": operation_dispatch.workflow_state,
                        "workflow_governance_mode": operation_dispatch.workflow_governance_mode,
                        "workflow_decision_points": operation_dispatch.workflow_decision_points,
                        "workflow_resume_status": operation_dispatch.workflow_resume_status,
                        "workflow_resume_point": operation_dispatch.workflow_resume_point,
                        **self.orchestrator._capability_decision_event_payload(
                            operation_dispatch
                        ),
                        "adaptive_intervention_status": (
                            operation_dispatch.adaptive_intervention_status
                        ),
                        "adaptive_intervention_selected_action": (
                            operation_dispatch.adaptive_intervention_selected_action
                        ),
                    },
                )
            )
            events.append(
                self.orchestrator.make_event(
                    "operation_dispatched",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "task_type": operation_dispatch.task_type,
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
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
                        **self.orchestrator._capability_decision_event_payload(
                            operation_dispatch
                        ),
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
                    },
                )
            )
            execution = self.orchestrator.operational_service.execute(operation_dispatch)
            operation_result = execution.operation_result
            artifact_results = execution.artifact_results
            events.append(
                self.orchestrator.make_event(
                    "operation_completed",
                    contract,
                    {
                        "operation_id": str(operation_result.operation_id),
                        "status": operation_result.status.value,
                        "artifacts": operation_result.artifacts,
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
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
                    },
                )
            )
            events.append(
                self.orchestrator.make_event(
                    "workflow_completed",
                    contract,
                    {
                        "operation_id": str(operation_result.operation_id),
                        "workflow_profile": operation_dispatch.workflow_profile,
                        "workflow_domain_route": operation_dispatch.workflow_domain_route,
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
                    },
                )
            )
        return {
            "operation_dispatch": operation_dispatch,
            "operation_result": operation_result,
            "artifact_results": artifact_results,
            "events": events,
        }

    def _synthesize_response(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        synthesis_result = self.orchestrator._compose_response(
            directive=directive,
            governance_decision=state["governance_decision"],
            memory_recovery_result=state["memory_recovery_result"],
            cognitive_snapshot=state["cognitive_snapshot"],
            knowledge_result=state.get("knowledge_result"),
            deliberative_plan=state["deliberative_plan"],
            specialist_review=state["specialist_review"],
            operation_result=state.get("operation_result"),
        )
        response_text = synthesis_result.response_text
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
                "response_synthesized",
                contract,
                {
                    "intent": directive.intent,
                    "contract_validation_status": (
                        state["deliberative_plan"].contract_validation_status
                    ),
                    "contract_validation_errors": (
                        state["deliberative_plan"].contract_validation_errors
                    ),
                    "contract_validation_retry_applied": (
                        state["deliberative_plan"].contract_validation_retry_applied
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
                    "primary_mind": state["deliberative_plan"].primary_mind,
                    "primary_mind_family": state["deliberative_plan"].primary_mind_family,
                    "primary_domain_driver": (
                        state["deliberative_plan"].primary_domain_driver
                    ),
                    "arbitration_source": state["deliberative_plan"].arbitration_source,
                    "mind_disagreement_status": (
                        state["deliberative_plan"].mind_disagreement_status
                    ),
                    "mind_validation_checkpoints": (
                        state["deliberative_plan"].mind_validation_checkpoints
                    ),
                    **self.orchestrator._capability_decision_event_payload(
                        state["deliberative_plan"],
                        authorization_status=(
                            self.orchestrator._resolve_capability_authorization_status(
                                plan=state["deliberative_plan"],
                                governance_decision=state["governance_decision"],
                                specialist_handoff_decision=state.get(
                                    "specialist_handoff_decision"
                                ),
                            )
                        ),
                    ),
                    "adaptive_intervention_status": (
                        state["deliberative_plan"].adaptive_intervention_status
                    ),
                    "adaptive_intervention_reason": (
                        state["deliberative_plan"].adaptive_intervention_reason
                    ),
                    "adaptive_intervention_trigger": (
                        state["deliberative_plan"].adaptive_intervention_trigger
                    ),
                    "adaptive_intervention_selected_action": (
                        state["deliberative_plan"].adaptive_intervention_selected_action
                    ),
                    "adaptive_intervention_expected_effect": (
                        state["deliberative_plan"].adaptive_intervention_expected_effect
                    ),
                    "adaptive_intervention_effects": (
                        state["deliberative_plan"].adaptive_intervention_effects
                    ),
                    "cognitive_strategy_shift_applied": (
                        state["deliberative_plan"].cognitive_strategy_shift_applied
                    ),
                    "cognitive_strategy_shift_summary": (
                        state["deliberative_plan"].cognitive_strategy_shift_summary
                    ),
                    "cognitive_strategy_shift_trigger": (
                        state["deliberative_plan"].cognitive_strategy_shift_trigger
                    ),
                    "cognitive_strategy_shift_effects": (
                        state["deliberative_plan"].cognitive_strategy_shift_effects
                    ),
                    "continuity_action": state["deliberative_plan"].continuity_action,
                    "continuity_source": state["deliberative_plan"].continuity_source,
                    "continuity_target_mission_id": (
                        str(state["deliberative_plan"].continuity_target_mission_id)
                        if state["deliberative_plan"].continuity_target_mission_id
                        else None
                    ),
                },
            )
        )
        return {"response_text": response_text, "events": events}

    def _record_memory(self, state: OrchestratorFlowState) -> OrchestratorFlowState:
        contract = state["contract"]
        directive = state["directive"]
        memory_record_result = self.orchestrator.memory_service.record_turn(
            contract,
            intent=directive.intent,
            response_text=state["response_text"],
            deliberative_plan=state["deliberative_plan"],
            specialist_contributions=state["specialist_review"].contributions,
            governance_decision=state["governance_decision"].decision,
        )
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
                "memory_recorded",
                contract,
                {
                    "memory_record_id": str(memory_record_result.record_contract.memory_record_id),
                    "record_type": memory_record_result.record_contract.record_type,
                    "continuity_mode": state["deliberative_plan"].continuity_action,
                    "continuity_source": state["deliberative_plan"].continuity_source,
                    "continuity_target_mission_id": (
                        str(state["deliberative_plan"].continuity_target_mission_id)
                        if state["deliberative_plan"].continuity_target_mission_id
                        else None
                    ),
                },
            )
        )
        return {"memory_record_result": memory_record_result, "events": events}


class LangGraphContinuityFlowRunner:
    """Run only the continuity recovery path as a dedicated LangGraph subflow."""

    def __init__(self, orchestrator: OrchestratorService) -> None:
        self.orchestrator = orchestrator

    def run(
        self,
        *,
        contract: InputContract,
        events: list[object],
    ) -> ContinuityFlowState:
        state_graph, start_token, end_token = _load_langgraph()
        graph = state_graph(ContinuityFlowState)
        graph.add_node("resolve_pause", self._resolve_pause)
        graph.add_node("recover_memory", self._recover_memory)
        graph.add_node("load_replay", self._load_replay)
        graph.add_node("seal_subflow", self._seal_subflow)
        graph.add_edge(start_token, "resolve_pause")
        graph.add_edge("resolve_pause", "recover_memory")
        graph.add_edge("recover_memory", "load_replay")
        graph.add_edge("load_replay", "seal_subflow")
        graph.add_edge("seal_subflow", end_token)
        runner = graph.compile()
        return runner.invoke({"contract": contract, "events": events})

    def _resolve_pause(self, state: ContinuityFlowState) -> ContinuityFlowState:
        contract = state["contract"]
        resolved_pause = self.orchestrator._maybe_resolve_continuity_pause(contract)
        events = list(state["events"])
        if resolved_pause is not None:
            events.append(
                self.orchestrator.make_event(
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
        return {"resolved_pause": resolved_pause, "events": events}

    def _recover_memory(self, state: ContinuityFlowState) -> ContinuityFlowState:
        contract = state["contract"]
        memory_recovery_result = self.orchestrator.memory_service.recover_for_input(contract)
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
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
                },
            )
        )
        return {
            "memory_recovery_result": memory_recovery_result,
            "events": events,
        }

    def _load_replay(self, state: ContinuityFlowState) -> ContinuityFlowState:
        contract = state["contract"]
        continuity_replay = self.orchestrator.memory_service.get_session_continuity_replay(
            str(contract.session_id)
        )
        events = list(state["events"])
        if continuity_replay is None:
            return {"continuity_replay": None, "events": events}
        memory_event = next(
            (
                event
                for event in reversed(events)
                if event.event_name == "memory_recovered"
            ),
            None,
        )
        if memory_event is not None:
            memory_event.payload["continuity_replay_status"] = continuity_replay.replay_status
        events.append(
            self.orchestrator.make_event(
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
                self.orchestrator.make_event(
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
        return {"continuity_replay": continuity_replay, "events": events}

    def _seal_subflow(self, state: ContinuityFlowState) -> ContinuityFlowState:
        contract = state["contract"]
        memory_recovery_result = state["memory_recovery_result"]
        continuity_replay = state.get("continuity_replay")
        resolved_pause = state.get("resolved_pause")
        events = list(state["events"])
        events.append(
            self.orchestrator.make_event(
                "continuity_subflow_completed",
                contract,
                self.orchestrator._build_continuity_subflow_payload(
                    runtime_mode="langgraph_subflow",
                    resolved_pause=resolved_pause,
                    memory_recovery_result=memory_recovery_result,
                    continuity_replay=continuity_replay,
                ),
            )
        )
        return {"events": events}


def _load_langgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - exercised by explicit unit test.
        raise RuntimeError(
            'LangGraph is not installed. Use `python -m pip install -e ".[langgraph]"` '
            "to run the experimental orchestrator flow."
        ) from exc
    return StateGraph, START, END
