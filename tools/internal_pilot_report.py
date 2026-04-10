"""Summarize recent internal pilot traces from local observability storage."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from json import dumps
from pathlib import Path
from sys import path as sys_path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "services" / "observability-service" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from observability_service.service import DEFAULT_REQUIRED_FLOW_EVENTS, ObservabilityService

from tools.internal_pilot_support import axis_gate_status_from_statuses


@dataclass(frozen=True)
class PilotTraceSummary:
    request_id: str
    session_id: str | None
    mission_id: str | None
    total_events: int
    event_names: list[str]
    missing_required_events: list[str]
    anomaly_flags: list[str]
    continuity_action: str | None
    continuity_source: str | None
    continuity_runtime_mode: str | None
    specialist_subflow_status: str
    specialist_subflow_runtime_mode: str | None
    mission_runtime_state_status: str
    workflow_domain_route: str | None
    registry_domains: list[str]
    shadow_specialists: list[str]
    domain_alignment_status: str
    mind_alignment_status: str
    identity_alignment_status: str
    memory_alignment_status: str
    specialist_sovereignty_status: str
    axis_gate_status: str
    expectation_status: str
    workflow_trace_status: str
    workflow_checkpoint_status: str
    workflow_resume_status: str
    workflow_pending_checkpoint_count: int
    workflow_profile_status: str
    workflow_profile_assessment: str
    workflow_output_status: str
    workflow_output_assessment: str
    metacognitive_guidance_status: str
    mind_disagreement_status: str
    mind_validation_checkpoint_status: str
    adaptive_intervention_status: str
    adaptive_intervention_reason: str | None
    adaptive_intervention_trigger: str | None
    adaptive_intervention_selected_action: str | None
    adaptive_intervention_effectiveness: str
    memory_causality_status: str
    primary_mind: str | None
    primary_route: str | None
    dominant_tension: str | None
    arbitration_source: str | None
    primary_domain_driver: str | None
    mind_domain_specialist_status: str
    mind_domain_specialist_chain_status: str
    mind_domain_specialist_chain: str | None
    cognitive_recomposition_applied: bool
    cognitive_recomposition_assessment: str
    cognitive_recomposition_reason: str | None
    cognitive_recomposition_trigger: str | None
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
    procedural_artifact_status: str
    procedural_artifact_refs: list[str]
    procedural_artifact_version: int | None
    memory_corpus_status: str
    memory_retention_pressure: str | None
    semantic_memory_specialists: list[str]
    procedural_memory_specialists: list[str]
    continuity_trace_status: str
    missing_continuity_signals: list[str]
    continuity_anomaly_flags: list[str]
    trace_status: str
    governance_decision: str | None
    operation_status: str | None
    duration_seconds: float
    source_services: list[str]


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Summarize JARVIS internal pilot traces.")
    parser.add_argument(
        "--database-path",
        default=str(ROOT / ".jarvis_runtime" / "observability.db"),
        help="Path to the local observability SQLite database.",
    )
    parser.add_argument("--request-id", help="Single request_id to summarize.")
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of recent request traces to summarize.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format for the report.",
    )
    return parser.parse_args()


def summarize_traces(
    database_path: str,
    *,
    request_id: str | None = None,
    limit: int = 10,
) -> list[PilotTraceSummary]:
    service = ObservabilityService(database_path=database_path)
    audits = (
        [service.audit_flow(query=service_query(request_id))]
        if request_id
        else service.summarize_recent_requests(limit=limit)
    )
    return [
        PilotTraceSummary(
            request_id=audit.request_id or "unknown",
            session_id=audit.session_id,
            mission_id=audit.mission_id,
            total_events=audit.total_events,
            event_names=audit.event_names,
            missing_required_events=audit.missing_required_events,
            anomaly_flags=audit.anomaly_flags,
            continuity_action=audit.continuity_action,
            continuity_source=audit.continuity_source,
            continuity_runtime_mode=audit.continuity_runtime_mode,
            specialist_subflow_status=audit.specialist_subflow_status,
            specialist_subflow_runtime_mode=audit.specialist_subflow_runtime_mode,
            mission_runtime_state_status=audit.mission_runtime_state_status,
            workflow_domain_route=audit.workflow_domain_route,
            registry_domains=list(audit.registry_domains),
            shadow_specialists=list(audit.shadow_specialists),
            domain_alignment_status=audit.domain_alignment_status,
            mind_alignment_status=audit.mind_alignment_status,
            identity_alignment_status=audit.identity_alignment_status,
            memory_alignment_status=audit.memory_alignment_status,
            specialist_sovereignty_status=audit.specialist_sovereignty_status,
            axis_gate_status=axis_gate_status_from_statuses(
                audit.domain_alignment_status,
                audit.mind_alignment_status,
                audit.identity_alignment_status,
                audit.memory_alignment_status,
                audit.specialist_sovereignty_status,
            ),
            expectation_status=_expectation_status(
                governance_decision=audit.governance_decision,
                operation_status=audit.operation_status,
                continuity_action=audit.continuity_action,
            ),
            workflow_trace_status=audit.workflow_trace_status,
            workflow_checkpoint_status=audit.workflow_checkpoint_status,
            workflow_resume_status=audit.workflow_resume_status,
            workflow_pending_checkpoint_count=audit.workflow_pending_checkpoint_count,
            workflow_profile_status=audit.workflow_profile_status,
            workflow_profile_assessment=_workflow_profile_assessment(
                audit.workflow_profile_status
            ),
            workflow_output_status=audit.workflow_output_status,
            workflow_output_assessment=_workflow_output_assessment(
                audit.workflow_output_status
            ),
            metacognitive_guidance_status=audit.metacognitive_guidance_status,
            mind_disagreement_status=audit.mind_disagreement_status,
            mind_validation_checkpoint_status=audit.mind_validation_checkpoint_status,
            adaptive_intervention_status=audit.adaptive_intervention_status,
            adaptive_intervention_reason=audit.adaptive_intervention_reason,
            adaptive_intervention_trigger=audit.adaptive_intervention_trigger,
            adaptive_intervention_selected_action=(
                audit.adaptive_intervention_selected_action
            ),
            adaptive_intervention_effectiveness=(
                audit.adaptive_intervention_effectiveness
            ),
            memory_causality_status=audit.memory_causality_status,
            primary_mind=audit.primary_mind,
            primary_route=audit.primary_route,
            dominant_tension=audit.dominant_tension,
            arbitration_source=audit.arbitration_source,
            primary_domain_driver=audit.primary_domain_driver,
            mind_domain_specialist_status=audit.mind_domain_specialist_status,
            mind_domain_specialist_chain_status=(
                audit.mind_domain_specialist_chain_status
            ),
            mind_domain_specialist_chain=audit.mind_domain_specialist_chain,
            cognitive_recomposition_applied=audit.cognitive_recomposition_applied,
            cognitive_recomposition_assessment=_cognitive_recomposition_assessment(
                applied=audit.cognitive_recomposition_applied,
                reason=audit.cognitive_recomposition_reason,
                trigger=audit.cognitive_recomposition_trigger,
            ),
            cognitive_recomposition_reason=audit.cognitive_recomposition_reason,
            cognitive_recomposition_trigger=audit.cognitive_recomposition_trigger,
            semantic_memory_source=audit.semantic_memory_source,
            procedural_memory_source=audit.procedural_memory_source,
            semantic_memory_focus=list(audit.semantic_memory_focus),
            procedural_memory_hint=audit.procedural_memory_hint,
            semantic_memory_effects=list(audit.semantic_memory_effects),
            procedural_memory_effects=list(audit.procedural_memory_effects),
            semantic_memory_lifecycle=audit.semantic_memory_lifecycle,
            procedural_memory_lifecycle=audit.procedural_memory_lifecycle,
            memory_lifecycle_status=audit.memory_lifecycle_status,
            memory_review_status=audit.memory_review_status,
            procedural_artifact_status=audit.procedural_artifact_status,
            procedural_artifact_refs=list(audit.procedural_artifact_refs),
            procedural_artifact_version=audit.procedural_artifact_version,
            memory_corpus_status=audit.memory_corpus_status,
            memory_retention_pressure=audit.memory_retention_pressure,
            semantic_memory_specialists=list(audit.semantic_memory_specialists),
            procedural_memory_specialists=list(audit.procedural_memory_specialists),
            continuity_trace_status=audit.continuity_trace_status,
            missing_continuity_signals=audit.missing_continuity_signals,
            continuity_anomaly_flags=audit.continuity_anomaly_flags,
            trace_status=_trace_status(audit),
            governance_decision=audit.governance_decision,
            operation_status=audit.operation_status,
            duration_seconds=audit.duration_seconds,
            source_services=audit.source_services,
        )
        for audit in audits
        if audit.total_events > 0
    ]


def service_query(request_id: str):
    from observability_service.service import ObservabilityQuery

    return ObservabilityQuery(
        request_id=request_id,
        limit=max(len(DEFAULT_REQUIRED_FLOW_EVENTS) * 4, 100),
    )


def _trace_status(audit) -> str:
    if audit.anomaly_flags or audit.continuity_anomaly_flags:
        return "attention_required"
    if audit.adaptive_intervention_effectiveness in {"insufficient", "incomplete"}:
        return "attention_required"
    if audit.missing_required_events or audit.missing_continuity_signals:
        return "incomplete"
    return "healthy"


def _expectation_status(
    *,
    governance_decision: str | None,
    operation_status: str | None,
    continuity_action: str | None,
) -> str:
    if governance_decision == "block":
        return "guardrail_expected"
    if governance_decision == "defer_for_validation":
        return "manual_validation_expected"
    if continuity_action in {"continuar", "retomar"} and operation_status in {None, "completed"}:
        return "continuity_progressing"
    if operation_status == "completed":
        return "operation_completed"
    return "review_required"


def _workflow_profile_assessment(workflow_profile_status: str | None) -> str:
    if workflow_profile_status in {None, "not_applicable"}:
        return "not_applicable"
    if workflow_profile_status == "healthy":
        return "baseline_saudavel"
    if workflow_profile_status == "maturation_recommended":
        return "maturation_recommended"
    return "attention_required"


def _workflow_output_assessment(workflow_output_status: str | None) -> str:
    if workflow_output_status in {None, "not_applicable"}:
        return "not_applicable"
    if workflow_output_status == "coherent":
        return "baseline_saudavel"
    if workflow_output_status == "partial":
        return "maturation_recommended"
    return "attention_required"


def _cognitive_recomposition_assessment(
    *,
    applied: bool,
    reason: str | None,
    trigger: str | None,
) -> str:
    if not applied:
        if reason is None and trigger is None:
            return "not_applicable"
        return "attention_required"
    if reason is not None and trigger is not None:
        return "coherent"
    return "attention_required"


def _specialist_subflow_assessment(status: str | None) -> str:
    if status in {None, "not_applicable"}:
        return "not_applicable"
    if status in {"healthy", "contained"}:
        return status
    return "attention_required"


def _mission_runtime_state_assessment(status: str | None) -> str:
    if status in {None, "not_applicable"}:
        return "not_applicable"
    if status == "healthy":
        return "healthy"
    return "attention_required"


def _render_summary(summary: PilotTraceSummary) -> str:
    subflow_status = getattr(summary, "specialist_subflow_status", None)
    subflow_assessment = _specialist_subflow_assessment(subflow_status)
    mission_status = getattr(summary, "mission_runtime_state_status", None)
    mission_assessment = _mission_runtime_state_assessment(mission_status)
    return (
        f"request_id={summary.request_id} "
        f"session_id={summary.session_id} "
        f"mission_id={summary.mission_id} "
        f"total_events={summary.total_events} "
        f"governance_decision={summary.governance_decision} "
        f"operation_status={summary.operation_status} "
        f"missing_required_events={','.join(summary.missing_required_events) or 'none'} "
        f"anomaly_flags={','.join(summary.anomaly_flags) or 'none'} "
        f"continuity_action={summary.continuity_action or 'none'} "
        f"continuity_source={summary.continuity_source or 'none'} "
        f"continuity_runtime_mode={summary.continuity_runtime_mode or 'none'} "
        "specialist_subflow_status="
        f"{getattr(summary, 'specialist_subflow_status', 'not_applicable')} "
        "specialist_subflow_runtime_mode="
        f"{getattr(summary, 'specialist_subflow_runtime_mode', None) or 'none'} "
        f"specialist_subflow_assessment={subflow_assessment} "
        "mission_runtime_state_status="
        f"{mission_status or 'not_applicable'} "
        f"mission_runtime_state_assessment={mission_assessment} "
        f"workflow_domain_route={getattr(summary, 'workflow_domain_route', None) or 'none'} "
        "registry_domains="
        f"{','.join(getattr(summary, 'registry_domains', [])) or 'none'} "
        "shadow_specialists="
        f"{','.join(getattr(summary, 'shadow_specialists', [])) or 'none'} "
        "domain_alignment_status="
        f"{getattr(summary, 'domain_alignment_status', 'incomplete')} "
        "mind_alignment_status="
        f"{getattr(summary, 'mind_alignment_status', 'incomplete')} "
        "identity_alignment_status="
        f"{getattr(summary, 'identity_alignment_status', 'incomplete')} "
        "memory_alignment_status="
        f"{getattr(summary, 'memory_alignment_status', 'incomplete')} "
        "specialist_sovereignty_status="
        f"{getattr(summary, 'specialist_sovereignty_status', 'incomplete')} "
        "axis_gate_status="
        f"{getattr(summary, 'axis_gate_status', 'attention_required')} "
        f"expectation_status={summary.expectation_status} "
        f"workflow_trace_status={getattr(summary, 'workflow_trace_status', 'not_applicable')} "
        "workflow_checkpoint_status="
        f"{getattr(summary, 'workflow_checkpoint_status', 'not_applicable')} "
        "workflow_resume_status="
        f"{getattr(summary, 'workflow_resume_status', 'not_applicable')} "
        "workflow_pending_checkpoint_count="
        f"{getattr(summary, 'workflow_pending_checkpoint_count', 0)} "
        "workflow_profile_status="
        f"{getattr(summary, 'workflow_profile_status', 'not_applicable')} "
        "workflow_profile_assessment="
        f"{getattr(summary, 'workflow_profile_assessment', 'not_applicable')} "
        "workflow_output_status="
        f"{getattr(summary, 'workflow_output_status', 'not_applicable')} "
        "workflow_output_assessment="
        f"{getattr(summary, 'workflow_output_assessment', 'not_applicable')} "
        "metacognitive_guidance_status="
        f"{getattr(summary, 'metacognitive_guidance_status', 'not_applicable')} "
        "mind_disagreement_status="
        f"{getattr(summary, 'mind_disagreement_status', 'not_applicable')} "
        "mind_validation_checkpoint_status="
        f"{getattr(summary, 'mind_validation_checkpoint_status', 'not_applicable')} "
        "adaptive_intervention_status="
        f"{getattr(summary, 'adaptive_intervention_status', 'not_applicable')} "
        "adaptive_intervention_selected_action="
        f"{getattr(summary, 'adaptive_intervention_selected_action', None) or 'none'} "
        "adaptive_intervention_effectiveness="
        f"{getattr(summary, 'adaptive_intervention_effectiveness', 'not_applicable')} "
        "adaptive_intervention_trigger="
        f"{getattr(summary, 'adaptive_intervention_trigger', None) or 'none'} "
        "memory_causality_status="
        f"{getattr(summary, 'memory_causality_status', 'not_applicable')} "
        "primary_mind="
        f"{getattr(summary, 'primary_mind', None) or 'none'} "
        "primary_route="
        f"{getattr(summary, 'primary_route', None) or 'none'} "
        "dominant_tension="
        f"{getattr(summary, 'dominant_tension', None) or 'none'} "
        "arbitration_source="
        f"{getattr(summary, 'arbitration_source', None) or 'none'} "
        "primary_domain_driver="
        f"{getattr(summary, 'primary_domain_driver', None) or 'none'} "
        "mind_domain_specialist_status="
        f"{getattr(summary, 'mind_domain_specialist_status', 'not_applicable')} "
        "mind_domain_specialist_chain_status="
        f"{getattr(summary, 'mind_domain_specialist_chain_status', 'not_applicable')} "
        "mind_domain_specialist_chain="
        f"{getattr(summary, 'mind_domain_specialist_chain', None) or 'none'} "
        "cognitive_recomposition_applied="
        f"{getattr(summary, 'cognitive_recomposition_applied', False)} "
        "cognitive_recomposition_assessment="
        f"{getattr(summary, 'cognitive_recomposition_assessment', 'not_applicable')} "
        "cognitive_recomposition_reason="
        f"{getattr(summary, 'cognitive_recomposition_reason', None) or 'none'} "
        "cognitive_recomposition_trigger="
        f"{getattr(summary, 'cognitive_recomposition_trigger', None) or 'none'} "
        "semantic_memory_source="
        f"{getattr(summary, 'semantic_memory_source', None) or 'none'} "
        "procedural_memory_source="
        f"{getattr(summary, 'procedural_memory_source', None) or 'none'} "
        "semantic_memory_focus="
        f"{','.join(getattr(summary, 'semantic_memory_focus', [])) or 'none'} "
        "procedural_memory_hint="
        f"{getattr(summary, 'procedural_memory_hint', None) or 'none'} "
        "semantic_memory_effects="
        f"{','.join(getattr(summary, 'semantic_memory_effects', [])) or 'none'} "
        "procedural_memory_effects="
        f"{','.join(getattr(summary, 'procedural_memory_effects', [])) or 'none'} "
        "semantic_memory_lifecycle="
        f"{getattr(summary, 'semantic_memory_lifecycle', None) or 'none'} "
        "procedural_memory_lifecycle="
        f"{getattr(summary, 'procedural_memory_lifecycle', None) or 'none'} "
        "memory_lifecycle_status="
        f"{getattr(summary, 'memory_lifecycle_status', 'not_applicable')} "
        "memory_review_status="
        f"{getattr(summary, 'memory_review_status', 'not_applicable')} "
        "procedural_artifact_status="
        f"{getattr(summary, 'procedural_artifact_status', 'not_applicable')} "
        "procedural_artifact_refs="
        f"{','.join(getattr(summary, 'procedural_artifact_refs', [])) or 'none'} "
        "procedural_artifact_version="
        f"{getattr(summary, 'procedural_artifact_version', None) or 'none'} "
        "memory_corpus_status="
        f"{getattr(summary, 'memory_corpus_status', 'not_applicable')} "
        "memory_retention_pressure="
        f"{getattr(summary, 'memory_retention_pressure', None) or 'none'} "
        "semantic_memory_specialists="
        f"{','.join(getattr(summary, 'semantic_memory_specialists', [])) or 'none'} "
        "procedural_memory_specialists="
        f"{','.join(getattr(summary, 'procedural_memory_specialists', [])) or 'none'} "
        "missing_continuity_signals="
        f"{','.join(summary.missing_continuity_signals) or 'none'} "
        "continuity_anomaly_flags="
        f"{','.join(summary.continuity_anomaly_flags) or 'none'} "
        f"continuity_trace_status={summary.continuity_trace_status} "
        f"trace_status={summary.trace_status} "
        f"source_services={','.join(summary.source_services) or 'none'} "
        f"duration_seconds={summary.duration_seconds}"
    )


def render_text(summaries: list[PilotTraceSummary]) -> str:
    if not summaries:
        return "No internal pilot traces found."
    return "\n".join(_render_summary(s) for s in summaries)


def main() -> None:
    args = parse_args()
    summaries = summarize_traces(
        args.database_path,
        request_id=args.request_id,
        limit=args.limit,
    )
    if args.format == "json":
        print(dumps([asdict(summary) for summary in summaries], ensure_ascii=True, indent=2))
        return
    print(render_text(summaries))


if __name__ == "__main__":
    main()
