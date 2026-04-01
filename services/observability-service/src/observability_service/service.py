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
    event_names: list[str]
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None
    continuity_source: str | None
    continuity_target_mission_id: str | None
    continuity_target_goal: str | None
    continuity_runtime_mode: str | None
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
                event_names=[],
                missing_required_events=list(required_events),
                anomaly_flags=["no_events_found"],
                continuity_action=None,
                continuity_source=None,
                continuity_target_mission_id=None,
                continuity_target_goal=None,
                continuity_runtime_mode=None,
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
        continuity_event = self._first_event(events, "continuity_decided")
        continuity_runtime_event = self._first_event(events, "continuity_subflow_completed")
        workflow_composed_event = self._first_event(events, "workflow_composed")
        workflow_governance_event = self._first_event(events, "workflow_governance_declared")
        workflow_completed_event = self._first_event(events, "workflow_completed")
        directive_event = self._first_event(events, "directive_composed")
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
            operation_event=operation_event,
            workflow_composed_event=workflow_composed_event,
            workflow_governance_event=workflow_governance_event,
            workflow_completed_event=workflow_completed_event,
        )
        domain_alignment_status = self._domain_alignment_status(
            domain_registry_event=domain_registry_event,
            specialist_selection_event=specialist_selection_event,
            specialist_domain_event=specialist_domain_event,
            specialist_shadow_event=specialist_shadow_event,
        )
        mind_alignment_status = self._mind_alignment_status(
            context_event=context_event,
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
            event_names=event_names,
            missing_required_events=missing_required_events,
            anomaly_flags=anomaly_flags,
            continuity_action=continuity_action,
            continuity_source=continuity_source,
            continuity_target_mission_id=continuity_target_mission_id,
            continuity_target_goal=continuity_target_goal,
            continuity_runtime_mode=continuity_runtime_mode,
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
        if audit.governance_decision in {"block", "defer_for_validation"}:
            return "keep_contained_and_require_manual_review"
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
        operation_event: InternalEventEnvelope | None,
        workflow_composed_event: InternalEventEnvelope | None,
        workflow_governance_event: InternalEventEnvelope | None,
        workflow_completed_event: InternalEventEnvelope | None,
    ) -> str:
        if (
            operation_event is None
            and workflow_composed_event is None
            and workflow_governance_event is None
            and workflow_completed_event is None
        ):
            return "not_applicable"
        if workflow_composed_event is None:
            return "attention_required"
        if workflow_governance_event is None or workflow_completed_event is None:
            return "incomplete"
        decision_points = workflow_composed_event.payload.get("workflow_decision_points", [])
        completed_decisions = workflow_completed_event.payload.get("workflow_decisions", [])
        workflow_state = workflow_completed_event.payload.get("workflow_state")
        governance_mode = workflow_governance_event.payload.get("workflow_governance_mode")
        if not decision_points or not completed_decisions:
            return "attention_required"
        if workflow_state not in {"completed", "failed"}:
            return "attention_required"
        if governance_mode != "core_mediated":
            return "attention_required"
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
            primary_route_matches = specialist_selection_event.payload.get(
                "primary_route_matches",
                {},
            )
            primary_canonical_matches = specialist_selection_event.payload.get(
                "primary_canonical_matches",
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
            primary_route_matches = specialist_domain_event.payload.get(
                "primary_route_matches",
                {},
            )
            primary_canonical_matches = specialist_domain_event.payload.get(
                "primary_canonical_matches",
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
    ) -> str:
        if context_event is None:
            return "incomplete"
        primary_mind = context_event.payload.get("primary_mind")
        active_minds = context_event.payload.get("active_minds", [])
        supporting_minds = context_event.payload.get("supporting_minds", [])
        suppressed_minds = context_event.payload.get("suppressed_minds", [])
        dominant_tension = context_event.payload.get("dominant_tension")
        arbitration_summary = context_event.payload.get("arbitration_summary")
        arbitration_source = context_event.payload.get("arbitration_source")
        canonical_domains = context_event.payload.get("canonical_domains", [])
        primary_domain_driver = context_event.payload.get("primary_domain_driver")
        support_limit = context_event.payload.get("supporting_mind_limit")
        suppressed_limit = context_event.payload.get("suppressed_mind_limit")
        if not primary_mind or not active_minds or not dominant_tension:
            return "partial"
        if arbitration_source != "mind_registry":
            return "attention_required"
        if not arbitration_summary:
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
        return "healthy"

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
                if not any(str(ref).startswith("memory://semantic") for ref in memory_refs):
                    return "attention_required"
                if not semantic_focus:
                    return "attention_required"
            if "procedural" in consumed and not any(
                str(ref).startswith("memory://procedural") for ref in memory_refs
            ):
                return "attention_required"
        return "healthy"

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
