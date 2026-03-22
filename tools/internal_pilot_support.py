"""Shared support utilities for internal pilot execution and comparison."""
# ruff: noqa: E402

from __future__ import annotations

from dataclasses import asdict, dataclass
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
from tools.validate_v1 import check_profile_prerequisites


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
    operation_status: str | None
    continuity_action: str | None
    continuity_source: str | None
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


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-internal-pilot"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


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
        ),
        PilotScenario(
            scenario_id="controlled_summary",
            content="Plan a concise rollout summary for the pilot.",
            expectation="Produce a concise textual artifact for the pilot operator.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=True,
            session_key="pilot-summary",
        ),
        PilotScenario(
            scenario_id="analysis_followup",
            content="Analyze the previous plan.",
            expectation="Reuse mission continuity and keep the response analytical.",
            expected_decision=PermissionDecision.ALLOW_WITH_CONDITIONS.value,
            expected_operation=False,
            session_key="pilot-main",
            mission_key="mission-pilot-v1",
        ),
        PilotScenario(
            scenario_id="guardrail_block",
            content="Delete all pilot records now.",
            expectation="Block the destructive request and preserve traceability.",
            expected_decision=PermissionDecision.BLOCK.value,
            expected_operation=False,
            session_key="pilot-guardrail",
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
        results.append(
            PilotExecutionResult(
                scenario_id=scenario.scenario_id,
                path_name=path_name,
                request_id=request_id,
                session_id=session_id,
                mission_id=scenario.mission_key,
                intent=response.intent,
                governance_decision=response.governance_decision.decision.value,
                operation_status=(
                    response.operation_result.status.value
                    if response.operation_result is not None
                    else None
                ),
                continuity_action=audit.continuity_action,
                continuity_source=audit.continuity_source,
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
            )
        )
    return results


def result_to_dict(result: PilotExecutionResult) -> dict[str, object]:
    return asdict(result)
