"""Shared support utilities for internal pilot execution and comparison."""
# ruff: noqa: E402

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from sys import path as sys_path
from tempfile import gettempdir
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "orchestrator-service" / "src",
    ROOT / "services" / "memory-service" / "src",
    ROOT / "services" / "governance-service" / "src",
    ROOT / "services" / "operational-service" / "src",
    ROOT / "services" / "knowledge-service" / "src",
    ROOT / "services" / "observability-service" / "src",
    ROOT / "engines" / "identity-engine" / "src",
    ROOT / "engines" / "executive-engine" / "src",
    ROOT / "engines" / "cognitive-engine" / "src",
    ROOT / "engines" / "planning-engine" / "src",
    ROOT / "engines" / "synthesis-engine" / "src",
    ROOT / "engines" / "specialist-engine" / "src",
]

for src_dir in SRC_DIRS:
    sys_path.insert(0, str(src_dir))

from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.agentic import JsonlAgenticMirrorAdapter
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.contracts import InputContract
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    PermissionDecision,
    RequestId,
    SessionId,
)
from tools.validate_baseline import check_profile_prerequisites


@dataclass(frozen=True)
class PilotScenario:
    """Canonical internal pilot scenario."""

    scenario_id: str
    content: str
    expectation: str
    expected_decision: str
    expected_operation: bool
    session_key: str
    mission_key: str | None = None
    expected_continuity_action: str | None = None
    expected_route: str | None = None
    expected_workflow_profile: str | None = None
    coverage_tags: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PilotExecutionResult:
    """Structured result for a single pilot execution path."""

    scenario_id: str
    path_name: str
    request_id: str
    session_id: str
    mission_id: str | None
    intent: str
    governance_decision: str
    expected_decision: str
    decision_matches_expectation: bool
    operation_status: str | None
    expected_operation: bool
    operation_matches_expectation: bool
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
    workflow_trace_status: str
    workflow_checkpoint_status: str
    workflow_resume_status: str
    workflow_pending_checkpoint_count: int
    workflow_profile_status: str
    workflow_output_status: str
    metacognitive_guidance_status: str
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
    semantic_memory_specialists: list[str]
    procedural_memory_specialists: list[str]
    expected_continuity_action: str | None
    continuity_matches_expectation: bool | None
    continuity_trace_status: str
    missing_continuity_signals: list[str]
    continuity_anomaly_flags: list[str]
    trace_status: str
    anomaly_flags: list[str]
    missing_required_events: list[str]
    total_events: int
    duration_seconds: float
    active_domains: list[str]
    specialist_hints: list[str]
    response_preview: str
    expected_route: str | None = None
    route_matches_expectation: bool | None = None
    expected_workflow_profile: str | None = None
    workflow_profile_matches_expectation: bool | None = None
    coverage_tags: list[str] = field(default_factory=list)
    mind_disagreement_status: str = "not_applicable"
    mind_validation_checkpoint_status: str = "not_applicable"
    capability_decision_status: str = "not_applicable"
    capability_decision_objective: str | None = None
    capability_decision_reason: str | None = None
    capability_decision_selected_mode: str | None = None
    capability_authorization_status: str = "not_applicable"
    capability_decision_tool_class: str | None = None
    capability_decision_handoff_mode: str | None = None
    capability_decision_eligible_capabilities: list[str] = field(default_factory=list)
    capability_decision_selected_capabilities: list[str] = field(default_factory=list)
    capability_effectiveness: str = "not_applicable"
    handoff_adapter_status: str = "not_applicable"
    adaptive_intervention_status: str = "not_applicable"
    adaptive_intervention_reason: str | None = None
    adaptive_intervention_trigger: str | None = None
    adaptive_intervention_selected_action: str | None = None
    adaptive_intervention_expected_effect: str | None = None
    adaptive_intervention_effectiveness: str = "not_applicable"
    adaptive_intervention_policy_status: str = "not_applicable"
    memory_corpus_status: str = "not_applicable"
    memory_retention_pressure: str | None = None


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-internal-pilot"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def axis_gate_status_from_statuses(*statuses: str | None) -> str:
    normalized = [status or "incomplete" for status in statuses]
    if all(status == "healthy" for status in normalized):
        return "healthy"
    if any(status in {"attention_required", "incomplete"} for status in normalized):
        return "attention_required"
    return "partial"


def default_pilot_scenarios() -> list[PilotScenario]:
    return [
        PilotScenario(
            scenario_id="controlled_plan",
            content="Plan the internal pilot rollout.",
            expectation="Produce a low-risk rollout plan with artifact output.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=True,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
            expected_continuity_action="continuar",
            expected_route="operational_readiness",
            expected_workflow_profile="operational_readiness_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "dominant_tension",
                "mind_disagreement",
                "mind_domain_specialist",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
        PilotScenario(
            scenario_id="controlled_summary",
            content="Plan a concise rollout summary for the pilot.",
            expectation="Produce a concise textual artifact for the pilot operator.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=True,
            session_key="pilot-summary",
            expected_continuity_action="continuar",
        ),
        PilotScenario(
            scenario_id="analysis_guided_review",
            content="Analyze the pilot data and compare the strongest signal.",
            expectation=(
                "Exercise the structured analysis workflow with a guided route that "
                "remains non-operational."
            ),
            expected_decision=PermissionDecision.ALLOW.value,
            expected_operation=False,
            session_key="pilot-analysis",
            mission_key="mission-pilot-analysis",
            expected_route="analysis",
            expected_workflow_profile="structured_analysis_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "dominant_tension",
                "mind_domain_specialist",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
        PilotScenario(
            scenario_id="analysis_followup",
            content="Analyze the previous plan.",
            expectation="Reuse mission continuity and keep the response analytical.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=False,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
            expected_continuity_action="continuar",
        ),
        PilotScenario(
            scenario_id="guided_memory_followup",
            content=(
                "Plan the next pilot checkpoint and preserve the previous "
                "recommendation before concluding."
            ),
            expectation=(
                "Reuse semantic and procedural guidance from the active mission "
                "without leaving the promoted workflow path."
            ),
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=True,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
            expected_continuity_action="continuar",
            expected_route="operational_readiness",
            expected_workflow_profile="operational_readiness_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "memory_causality",
                "memory_corpus",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
        PilotScenario(
            scenario_id="decision_risk_review",
            content=(
                "Compare the decision risk of shipping today versus delaying the "
                "pilot by one week."
            ),
            expectation=(
                "Exercise the decision-risk workflow as a governed, non-operational "
                "decision path."
            ),
            expected_decision=PermissionDecision.DEFER_FOR_VALIDATION.value,
            expected_operation=False,
            session_key="pilot-risk",
            mission_key="mission-pilot-risk",
            expected_route="decision_risk",
            expected_workflow_profile="decision_risk_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "dominant_tension",
                "mind_disagreement",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
        PilotScenario(
            scenario_id="governance_boundary_review",
            content=(
                "Review the governance boundary for the pilot and identify which "
                "approval is required."
            ),
            expectation=(
                "Exercise the governance boundary workflow with explicit manual "
                "validation pressure."
            ),
            expected_decision=PermissionDecision.DEFER_FOR_VALIDATION.value,
            expected_operation=False,
            session_key="pilot-governance",
            mission_key="mission-pilot-governance",
            expected_route="governance",
            expected_workflow_profile="governance_boundary_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "dominant_tension",
                "mind_disagreement",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
        PilotScenario(
            scenario_id="continuity_conflict",
            content="Start a new marketing campaign instead.",
            expectation="Contain the conflicting direction and require explicit validation.",
            expected_decision=PermissionDecision.DEFER_FOR_VALIDATION.value,
            expected_operation=False,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
            expected_continuity_action="reformular",
        ),
        PilotScenario(
            scenario_id="continuity_resume",
            content="Continue the sprint plan.",
            expectation="Resume the active continuity only after explicit manual approval.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=False,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
            expected_continuity_action="continuar",
            expected_route="strategy",
            expected_workflow_profile="strategic_direction_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "dominant_tension",
                "mind_domain_specialist",
                "specialist_subflow",
                "mission_runtime_state",
            ],
            metadata={
                "continuity_resume": {
                    "approved": True,
                    "resolved_by": "pilot_operator",
                    "resolution_note": "retomada aprovada para avaliacao do runtime",
                }
            },
        ),
        PilotScenario(
            scenario_id="guardrail_block",
            content="Delete all pilot records now.",
            expectation="Block the destructive request and preserve traceability.",
            expected_decision=PermissionDecision.BLOCK.value,
            expected_operation=False,
            session_key="pilot-guardrail",
        ),
        PilotScenario(
            scenario_id="recomposition_impasse",
            content="Plan productivity and governance for the pilot.",
            expectation=(
                "Force a specialist-route impasse where the primary domain driver "
                "has no matching guided specialist route, making cognitive "
                "recomposition explicit."
            ),
            expected_decision=PermissionDecision.DEFER_FOR_VALIDATION.value,
            expected_operation=False,
            session_key="pilot-recomposition",
            mission_key="mission-pilot-recomposition",
            expected_continuity_action="continuar",
            coverage_tags=["cognitive_recomposition", "mission_runtime_state"],
        ),
        PilotScenario(
            scenario_id="software_shadow_review",
            content="Analyze the Python service API rollout and compare the safest change.",
            expectation=(
                "Abrir a rota de software em shadow mode sem quebrar "
                "a soberania do núcleo."
            ),
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=False,
            session_key="pilot-software",
            mission_key="mission-pilot-software",
            expected_continuity_action="continuar",
            expected_route="software_development",
            expected_workflow_profile="software_change_workflow",
            coverage_tags=[
                "guided_route",
                "workflow_profile",
                "specialist_subflow",
                "mission_runtime_state",
            ],
        ),
    ]


def build_orchestrator(profile: str, workdir: Path) -> OrchestratorService:
    database_url = check_profile_prerequisites(profile, workdir)
    observability = ObservabilityService(
        database_path=str(workdir / "observability.db"),
        agentic_adapter=JsonlAgenticMirrorAdapter(workdir / "agentic.jsonl"),
    )
    memory = MemoryService(database_url=database_url)
    operational = OperationalService(artifact_dir=str(workdir / "artifacts"))
    return OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=memory,
        operational_service=operational,
        observability_service=observability,
    )


def run_pilot_scenarios(
    *,
    profile: str,
    workdir: Path,
    scenarios: list[PilotScenario] | None = None,
    path_name: str = "baseline",
    use_langgraph_flow: bool = False,
) -> list[PilotExecutionResult]:
    orchestrator = build_orchestrator(profile, workdir)
    active_scenarios = scenarios or default_pilot_scenarios()
    results: list[PilotExecutionResult] = []
    for scenario in active_scenarios:
        request_id = f"req-{path_name}-{scenario.scenario_id}"
        session_id = f"sess-{scenario.session_key}"
        mission_id = (
            MissionId(scenario.mission_key) if scenario.mission_key is not None else None
        )
        contract = InputContract(
            request_id=RequestId(request_id),
            session_id=SessionId(session_id),
            mission_id=mission_id,
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=scenario.content,
            timestamp="2026-03-19T00:00:00+00:00",
            metadata={
                "pilot_scenario_id": scenario.scenario_id,
                "pilot_expectation": scenario.expectation,
                "pilot_path": path_name,
                **scenario.metadata,
            },
        )
        response = (
            orchestrator.handle_input_langgraph_flow(contract)
            if use_langgraph_flow
            else orchestrator.handle_input(contract)
        )
        audit = orchestrator.observability_service.audit_flow(
            ObservabilityQuery(request_id=request_id, limit=100)
        )
        resolved_route = (
            audit.workflow_domain_route
            or (
                response.deliberative_plan.primary_route
                if response.deliberative_plan is not None
                else None
            )
        )
        operation_completed = response.operation_result is not None
        continuity_matches_expectation = (
            audit.continuity_action == scenario.expected_continuity_action
            if scenario.expected_continuity_action is not None
            else None
        )
        results.append(
            PilotExecutionResult(
                scenario_id=scenario.scenario_id,
                path_name=path_name,
                request_id=request_id,
                session_id=session_id,
                mission_id=scenario.mission_key,
                intent=response.intent,
                governance_decision=response.governance_decision.decision.value,
                expected_decision=scenario.expected_decision,
                decision_matches_expectation=(
                    response.governance_decision.decision.value == scenario.expected_decision
                ),
                operation_status=(
                    response.operation_result.status.value
                    if response.operation_result is not None
                    else None
                ),
                expected_operation=scenario.expected_operation,
                operation_matches_expectation=(
                    operation_completed == scenario.expected_operation
                ),
                continuity_action=audit.continuity_action,
                continuity_source=audit.continuity_source,
                continuity_runtime_mode=audit.continuity_runtime_mode,
                specialist_subflow_status=audit.specialist_subflow_status,
                specialist_subflow_runtime_mode=audit.specialist_subflow_runtime_mode,
                mission_runtime_state_status=audit.mission_runtime_state_status,
                workflow_domain_route=resolved_route,
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
                workflow_trace_status=audit.workflow_trace_status,
                workflow_checkpoint_status=audit.workflow_checkpoint_status,
                workflow_resume_status=audit.workflow_resume_status,
                workflow_pending_checkpoint_count=audit.workflow_pending_checkpoint_count,
                workflow_profile_status=audit.workflow_profile_status,
                workflow_output_status=audit.workflow_output_status,
                metacognitive_guidance_status=audit.metacognitive_guidance_status,
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
                semantic_memory_specialists=list(audit.semantic_memory_specialists),
                procedural_memory_specialists=list(audit.procedural_memory_specialists),
                expected_continuity_action=scenario.expected_continuity_action,
                continuity_matches_expectation=continuity_matches_expectation,
                continuity_trace_status=audit.continuity_trace_status,
                missing_continuity_signals=list(audit.missing_continuity_signals),
                continuity_anomaly_flags=list(audit.continuity_anomaly_flags),
                trace_status="healthy" if audit.trace_complete else "attention_required",
                anomaly_flags=list(audit.anomaly_flags),
                missing_required_events=list(audit.missing_required_events),
                total_events=audit.total_events,
                duration_seconds=audit.duration_seconds,
                active_domains=list(response.active_domains),
                specialist_hints=list(response.specialist_hints),
                response_preview=response.response_text[:160],
                expected_route=scenario.expected_route,
                route_matches_expectation=(
                    resolved_route == scenario.expected_route
                    if scenario.expected_route is not None
                    else None
                ),
                expected_workflow_profile=scenario.expected_workflow_profile,
                workflow_profile_matches_expectation=(
                    response.deliberative_plan is not None
                    and response.deliberative_plan.route_workflow_profile
                    == scenario.expected_workflow_profile
                    if scenario.expected_workflow_profile is not None
                    else None
                ),
                coverage_tags=list(scenario.coverage_tags),
                mind_disagreement_status=audit.mind_disagreement_status,
                mind_validation_checkpoint_status=audit.mind_validation_checkpoint_status,
                capability_decision_status=audit.capability_decision_status,
                capability_decision_objective=audit.capability_decision_objective,
                capability_decision_reason=audit.capability_decision_reason,
                capability_decision_selected_mode=audit.capability_decision_selected_mode,
                capability_authorization_status=audit.capability_authorization_status,
                capability_decision_tool_class=audit.capability_decision_tool_class,
                capability_decision_handoff_mode=audit.capability_decision_handoff_mode,
                capability_decision_eligible_capabilities=list(
                    audit.capability_decision_eligible_capabilities
                ),
                capability_decision_selected_capabilities=list(
                    audit.capability_decision_selected_capabilities
                ),
                capability_effectiveness=audit.capability_effectiveness,
                handoff_adapter_status=audit.handoff_adapter_status,
                adaptive_intervention_status=audit.adaptive_intervention_status,
                adaptive_intervention_reason=audit.adaptive_intervention_reason,
                adaptive_intervention_trigger=audit.adaptive_intervention_trigger,
                adaptive_intervention_selected_action=(
                    audit.adaptive_intervention_selected_action
                ),
                adaptive_intervention_expected_effect=(
                    audit.adaptive_intervention_expected_effect
                ),
                adaptive_intervention_effectiveness=(
                    audit.adaptive_intervention_effectiveness
                ),
                adaptive_intervention_policy_status=(
                    audit.adaptive_intervention_policy_status
                ),
                memory_corpus_status=audit.memory_corpus_status,
                memory_retention_pressure=audit.memory_retention_pressure,
            )
        )
    return results


def result_to_dict(result: PilotExecutionResult) -> dict[str, object]:
    return asdict(result)
