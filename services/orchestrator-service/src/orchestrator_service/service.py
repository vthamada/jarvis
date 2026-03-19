"""Orchestrator flow integrating engines, persistence, and observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from cognitive_engine.engine import CognitiveEngine
from executive_engine.engine import ExecutiveEngine
from governance_service.service import GovernanceService
from identity_engine.engine import IdentityEngine
from knowledge_service.service import KnowledgeRetrievalResult, KnowledgeService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from planning_engine.engine import PlanningContext, PlanningEngine
from shared.contracts import (
    ArtifactResultContract,
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
from synthesis_engine.engine import SynthesisEngine, SynthesisInput


@dataclass
class OrchestratorResponse:
    """Structured result of the orchestrated v1 request flow."""

    request_id: str
    session_id: str
    intent: str
    response_text: str
    governance_check: GovernanceCheckContract
    governance_decision: GovernanceDecisionContract
    memory_recovery: MemoryRecoveryContract
    memory_record: MemoryRecordContract
    recovered_context: list[str]
    knowledge_result: KnowledgeRetrievalResult | None = None
    artifact_results: list[ArtifactResultContract] = field(default_factory=list)
    active_minds: list[str] = field(default_factory=list)
    active_domains: list[str] = field(default_factory=list)
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
                    "memory_query_id": str(memory_recovery_result.recovery_contract.memory_query_id),
                    "recovery_type": memory_recovery_result.recovery_contract.recovery_type.value,
                },
            )
        )

        directive = self.executive_engine.direct(contract)
        events.append(self.make_event("intent_classified", contract, {"intent": directive.intent}))

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
        )
        events.append(
            self.make_event(
                "context_composed",
                contract,
                {
                    "active_minds": cognitive_snapshot.active_minds,
                    "active_domains": cognitive_snapshot.active_domains,
                },
            )
        )

        assessment = self.governance_service.assess_request(
            contract,
            intent=directive.intent,
            requested_by_service=self.name,
        )
        governance_check = assessment.governance_check
        governance_decision = assessment.governance_decision
        events.append(
            self.make_event(
                "governance_checked",
                contract,
                {
                    "governance_check_id": str(governance_check.governance_check_id),
                    "risk_hint": governance_check.risk_hint.value if governance_check.risk_hint else None,
                    "decision": governance_decision.decision.value,
                },
            )
        )

        operation_dispatch = None
        operation_result = None
        artifact_results: list[ArtifactResultContract] = []
        if governance_decision.decision in {
            PermissionDecision.ALLOW,
            PermissionDecision.ALLOW_WITH_CONDITIONS,
        } and directive.should_execute_operation:
            plan = self.planning_engine.build_task_plan(
                PlanningContext(
                    intent=directive.intent,
                    query=contract.content,
                    recovered_context=memory_recovery_result.recovered_items,
                    active_domains=cognitive_snapshot.active_domains,
                    knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
                )
            )
            operation_dispatch = self.build_operation_dispatch(
                contract,
                intent=directive.intent,
                plan=plan,
                active_domains=cognitive_snapshot.active_domains,
            )
            events.append(
                self.make_event(
                    "operation_dispatched",
                    contract,
                    {
                        "operation_id": str(operation_dispatch.operation_id),
                        "task_type": operation_dispatch.task_type,
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

        identity_profile = self.identity_engine.get_profile()
        response_text = self.synthesis_engine.compose(
            SynthesisInput(
                intent=directive.intent,
                identity_profile=identity_profile,
                response_style=self.identity_engine.build_response_style(
                    intent=directive.intent,
                    blocked=governance_decision.decision in {
                        PermissionDecision.BLOCK,
                        PermissionDecision.DEFER_FOR_VALIDATION,
                    },
                ),
                governance_decision=governance_decision,
                recovered_context=memory_recovery_result.recovered_items,
                active_minds=cognitive_snapshot.active_minds,
                active_domains=cognitive_snapshot.active_domains,
                knowledge_snippets=knowledge_result.snippets if knowledge_result else [],
                operation_result=operation_result,
            )
        )
        events.append(self.make_event("response_synthesized", contract, {"intent": directive.intent}))

        memory_record_result = self.memory_service.record_turn(
            contract,
            intent=directive.intent,
            response_text=response_text,
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

        return OrchestratorResponse(
            request_id=str(contract.request_id),
            session_id=str(contract.session_id),
            intent=directive.intent,
            response_text=response_text,
            governance_check=governance_check,
            governance_decision=governance_decision,
            memory_recovery=memory_recovery_result.recovery_contract,
            memory_record=memory_record_result.record_contract,
            recovered_context=memory_recovery_result.recovered_items,
            knowledge_result=knowledge_result,
            artifact_results=artifact_results,
            active_minds=cognitive_snapshot.active_minds,
            active_domains=cognitive_snapshot.active_domains,
            operation_dispatch=operation_dispatch,
            operation_result=operation_result,
            events=events,
        )

    def build_operation_dispatch(
        self,
        contract: InputContract,
        intent: str,
        *,
        plan: str,
        active_domains: list[str],
    ) -> OperationDispatchContract:
        """Create the operational dispatch for an allowed request."""

        task_type = {
            "planning": "draft_plan",
            "analysis": "produce_analysis_brief",
            "general_assistance": "general_response",
        }.get(intent, "general_response")
        return OperationDispatchContract(
            operation_id=OperationId(f"op-{uuid4().hex[:8]}"),
            request_id=RequestId(str(contract.request_id)),
            task_type=task_type,
            task_goal=contract.content,
            task_plan=plan,
            constraints=["low-risk", "local-only", "no external side effects"],
            expected_output="text_brief",
            session_id=contract.session_id,
            mission_id=contract.mission_id,
            domain_hints=active_domains,
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
            correlation_id=str(contract.request_id),
        )

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()
