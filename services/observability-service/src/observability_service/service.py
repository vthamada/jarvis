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
    event_names: list[str]
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None
    continuity_source: str | None
    continuity_target_mission_id: str | None
    continuity_target_goal: str | None
    continuity_runtime_mode: str | None
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
                event_names=[],
                missing_required_events=list(required_events),
                anomaly_flags=["no_events_found"],
                continuity_action=None,
                continuity_source=None,
                continuity_target_mission_id=None,
                continuity_target_goal=None,
                continuity_runtime_mode=None,
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
        response_event = self._first_event(events, "response_synthesized")
        memory_event = self._first_event(events, "memory_recorded")
        first_event = events[0]
        governance_decision = (
            str(governance_event.payload.get("decision")) if governance_event else None
        )
        operation_status = (
            str(operation_event.payload.get("status")) if operation_event else None
        )
        continuity_action = (
            str(continuity_event.payload.get("continuity_action"))
            if continuity_event
            and continuity_event.payload.get("continuity_action") is not None
            else None
        )
        continuity_source = (
            str(continuity_event.payload.get("continuity_source"))
            if continuity_event
            and continuity_event.payload.get("continuity_source") is not None
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
        if governance_decision in {"allow", "allow_with_conditions"}:
            if "response_synthesized" not in event_names:
                anomaly_flags.append("allowed_flow_missing_response")
            if "memory_recorded" not in event_names:
                anomaly_flags.append("allowed_flow_missing_memory_record")
            if (
                "operation_dispatched" in event_names
                and "operation_completed" not in event_names
            ):
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

        return FlowAudit(
            request_id=first_event.request_id,
            session_id=first_event.session_id,
            mission_id=first_event.mission_id,
            total_events=len(events),
            event_names=event_names,
            missing_required_events=missing_required_events,
            anomaly_flags=anomaly_flags,
            continuity_action=continuity_action,
            continuity_source=continuity_source,
            continuity_target_mission_id=continuity_target_mission_id,
            continuity_target_goal=continuity_target_goal,
            continuity_runtime_mode=continuity_runtime_mode,
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
