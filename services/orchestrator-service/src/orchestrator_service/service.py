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
from specialist_engine.engine import SpecialistEngine, SpecialistReview
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
)
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

        memory_recovery_result = self.memory_service.recover_for_input(contract)
        events.append(
            self.make_event(
                "memory_recovered",
                contract,
                {
                    "memory_query_id": str(
                        memory_recovery_result.recovery_contract.memory_query_id
                    ),
                    "recovery_type": memory_recovery_result.recovery_contract.recovery_type.value,
                },
            )
        )

        directive = self.executive_engine.direct(contract)
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
                        "sources": knowledge_result.sources,
                    },
                )
            )

        cognitive_snapshot = self.cognitive_engine.build_snapshot(
            intent=directive.intent,
            risk_markers=directive.risk_markers,
            retrieved_domains=knowledge_result.active_domains if knowledge_result else [],
            mind_hints=directive.mind_hints,
        )
        events.append(
            self.make_event(
                "context_composed",
                contract,
                {
                    "active_minds": cognitive_snapshot.active_minds,
                    "active_domains": cognitive_snapshot.active_domains,
                    "primary_mind": cognitive_snapshot.primary_mind,
                    "supporting_minds": cognitive_snapshot.supporting_minds,
                    "dominant_tension": cognitive_snapshot.dominant_tension,
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
                },
            )
        )

        specialist_review = self.specialist_engine.review(
            intent=directive.intent,
            plan=deliberative_plan,
            knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
        )
        if specialist_review.specialist_hints:
            events.append(
                self.make_event(
                    "specialists_dispatched",
                    contract,
                    {"specialist_hints": specialist_review.specialist_hints},
                )
            )
        if specialist_review.contributions:
            events.append(
                self.make_event(
                    "specialists_completed",
                    contract,
                    {
                        "specialist_types": [
                            item.specialist_type for item in specialist_review.contributions
                        ],
                        "summary": specialist_review.summary,
                    },
                )
            )

        deliberative_plan = self.planning_engine.refine_task_plan(
            deliberative_plan,
            specialist_summary=specialist_review.summary,
            specialist_contributions=specialist_review.contributions,
        )
        if specialist_review.contributions:
            events.append(
                self.make_event(
                    "plan_refined",
                    contract,
                    {
                        "recommended_task_type": deliberative_plan.recommended_task_type,
                        "requires_human_validation": deliberative_plan.requires_human_validation,
                        "steps": deliberative_plan.steps,
                        "specialist_resolution_summary": (
                            deliberative_plan.specialist_resolution_summary
                        ),
                    },
                )
            )

        assessment = self.governance_service.assess_request(
            contract,
            intent=directive.intent,
            requested_by_service=self.name,
            plan=deliberative_plan,
        )
        governance_check = assessment.governance_check
        governance_decision = assessment.governance_decision
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
            self.make_event("response_synthesized", contract, {"intent": directive.intent})
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
                "operation_dispatch": operation_dispatch,
                "operation_result": operation_result,
                "events": events,
                "response_text": response_text,
            }
        )

    def handle_input_langgraph_poc(self, contract: InputContract) -> OrchestratorResponse:
        """Run the optional LangGraph POC without changing the default v1 flow."""

        from orchestrator_service.langgraph_poc import LangGraphPOCRunner

        return LangGraphPOCRunner(self).run(contract)

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
            )
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
            specialist_review=specialist_review,
            operation_dispatch=state["operation_dispatch"],
            operation_result=state["operation_result"],
            events=state["events"],
        )
