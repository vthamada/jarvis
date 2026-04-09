# ruff: noqa: E501
"""Structured local observability service."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from observability_service.agentic import (
    AgenticObservabilityAdapter,
    JsonlAgenticMirrorAdapter,
    LangSmithObservabilityAdapter,
)
from observability_service.repository import ObservabilityRepository
from shared.events import InternalEventEnvelope


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
    mind_domain_specialist_status: str
    mind_domain_specialist_chain_status: str
    mind_domain_specialist_chain: str | None
    cognitive_recomposition_applied: bool
    cognitive_recomposition_reason: str | None
    cognitive_recomposition_trigger: str | None
    cognitive_strategy_shift_status: str
    cognitive_strategy_shift_applied: bool
    cognitive_strategy_shift_summary: str | None
    cognitive_strategy_shift_trigger: str | None
    cognitive_strategy_shift_effects: list[str]
    semantic_memory_source: str | None
    procedural_memory_source: str | None
    semantic_memory_focus: list[str]
    procedural_memory_hint: str | None
    semantic_memory_effects: list[str]
    procedural_memory_effects: list[str]
    semantic_memory_lifecycle: str | None
    procedural_memory_lifecycle: str | None
    memory_lifecycle_status: str
    memory_review_status: str
    memory_consolidation_status: str
    memory_fixation_status: str
    memory_archive_status: str
    procedural_artifact_status: str
    procedural_artifact_refs: list[str]
    procedural_artifact_version: int | None
    memory_corpus_status: str
    memory_retention_pressure: str | None
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
            and self.cognitive_strategy_shift_status in {"healthy", "not_applicable"}
            and self.specialist_subflow_status
            in {"healthy", "not_applicable", "contained"}
            and self.mission_runtime_state_status in {"healthy", "not_applicable"}
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
                event_names=[],
                missing_required_events=list(required_events),
                anomaly_flags=["no_events_found"],
                mind_domain_specialist_status="incomplete",
                mind_domain_specialist_chain_status="incomplete",
                mind_domain_specialist_chain=None,
                cognitive_recomposition_applied=False,
                cognitive_recomposition_reason=None,
                cognitive_recomposition_trigger=None,
                cognitive_strategy_shift_status="incomplete",
                cognitive_strategy_shift_applied=False,
                cognitive_strategy_shift_summary=None,
                cognitive_strategy_shift_trigger=None,
                cognitive_strategy_shift_effects=[],
                semantic_memory_source=None,
                procedural_memory_source=None,
                semantic_memory_focus=[],
                procedural_memory_hint=None,
                semantic_memory_effects=[],
                procedural_memory_effects=[],
                semantic_memory_lifecycle=None,
                procedural_memory_lifecycle=None,
                memory_lifecycle_status="incomplete",
                memory_review_status="incomplete",
                memory_consolidation_status="incomplete",
                memory_fixation_status="incomplete",
                memory_archive_status="incomplete",
                memory_corpus_status="incomplete",
                memory_retention_pressure=None,
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
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
            primary_mind=primary_mind,
            primary_domain_driver=primary_domain_driver,
            primary_route=primary_route,
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
        specialist_sovereignty_status = self._specialist_sovereignty_status(
            specialist_contract_event=specialist_contract_event,
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
            mind_domain_specialist_status=mind_domain_specialist_status,
            mind_domain_specialist_chain_status=mind_domain_specialist_chain_status,
            mind_domain_specialist_chain=mind_domain_specialist_chain,
            cognitive_recomposition_applied=cognitive_recomposition_applied,
            cognitive_recomposition_reason=cognitive_recomposition_reason,
            cognitive_recomposition_trigger=cognitive_recomposition_trigger,
            cognitive_strategy_shift_status=cognitive_strategy_shift_status,
            cognitive_strategy_shift_applied=cognitive_strategy_shift_applied,
            cognitive_strategy_shift_summary=cognitive_strategy_shift_summary,
            cognitive_strategy_shift_trigger=cognitive_strategy_shift_trigger,
            cognitive_strategy_shift_effects=cognitive_strategy_shift_effects,
            semantic_memory_source=semantic_memory_source,
            procedural_memory_source=procedural_memory_source,
            semantic_memory_focus=semantic_memory_focus,
            procedural_memory_hint=procedural_memory_hint,
            semantic_memory_effects=semantic_memory_effects,
            procedural_memory_effects=procedural_memory_effects,
            semantic_memory_lifecycle=semantic_memory_lifecycle,
            procedural_memory_lifecycle=procedural_memory_lifecycle,
            memory_lifecycle_status=memory_lifecycle_status,
            memory_review_status=memory_review_status,
            memory_consolidation_status=memory_consolidation_status,
            memory_fixation_status=memory_fixation_status,
            memory_archive_status=memory_archive_status,
            procedural_artifact_status=(
                str(response_event.payload.get("procedural_artifact_status"))
                if response_event and response_event.payload.get("procedural_artifact_status") is not None
                else (
                    str(plan_event.payload.get("procedural_artifact_status"))
                    if plan_event and plan_event.payload.get("procedural_artifact_status") is not None
                    else (
                        str(memory_event.payload.get("procedural_artifact_status"))
                        if memory_event and memory_event.payload.get("procedural_artifact_status") is not None
                        else "not_applicable"
                    )
                )
            ),
            procedural_artifact_refs=(
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
                            for item in memory_event.payload.get("procedural_artifact_refs", [])
                            if item
                        ]
                        if memory_event is not None
                        and memory_event.payload.get("procedural_artifact_refs")
                        else []
                    )
                )
            ),
            procedural_artifact_version=(
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
                        and memory_event.payload.get("procedural_artifact_version") is not None
                        else None
                    )
                )
            ),
            memory_corpus_status=memory_corpus_status,
            memory_retention_pressure=memory_retention_pressure,
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
        specialist_selection_event: InternalEventEnvelope | None,
        specialist_domain_event: InternalEventEnvelope | None,
        primary_mind: str | None,
        primary_domain_driver: str | None,
        primary_route: str | None,
    ) -> str | None:
        for event in (response_event, specialist_selection_event, specialist_domain_event):
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
