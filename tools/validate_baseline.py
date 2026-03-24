"""Single entrypoint for validating the JARVIS baseline."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from datetime import UTC, datetime
from importlib.util import find_spec
from os import getenv
from pathlib import Path
from shutil import which
from subprocess import run
from sys import executable
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

from evolution_lab.service import ComparisonInput, EvolutionLabService
from governance_service.service import GovernanceService
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from apps.jarvis_console.cli import JarvisConsole, render_response
from shared.contracts import InputContract
from shared.events import InternalEventEnvelope
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    PermissionDecision,
    RequestId,
    SessionId,
)
from tools.operational_artifacts import (
    create_baseline_snapshot,
    resolve_backend_label,
    write_baseline_snapshot,
)


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Validate the JARVIS baseline.")
    parser.add_argument(
        "--profile",
        choices=["development", "controlled"],
        default="development",
        help="Validation profile. 'controlled' requires DATABASE_URL.",
    )
    return parser.parse_args()


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tools"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def ensure_command_available(command: str) -> None:
    if which(command) is None:
        raise RuntimeError(f"Required command is not available: {command}")


def resolve_ruff_command() -> list[str]:
    if which("ruff") is not None:
        return ["ruff"]
    if find_spec("ruff") is not None:
        return [executable, "-m", "ruff"]
    raise RuntimeError(
        "Required linter is not available: ruff. "
        'Install the dev environment with `python -m pip install -e ".[dev,postgres]"`.'
    )


def run_command(args: list[str], *, label: str) -> None:
    result = run(args, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}.")


def resolve_database_url(profile: str, target_dir: Path) -> str | None:
    if profile == "controlled":
        database_url = getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required for the controlled profile.")
        return database_url
    return f"sqlite:///{(target_dir / 'memory.db').as_posix()}"


def ensure_database_ready(database_url: str) -> None:
    if not database_url.startswith("postgresql://"):
        return
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "psycopg is required for the controlled profile. "
            'Install the dev environment with `python -m pip install -e ".[dev,postgres]"`.'
        ) from exc
    try:
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "Controlled profile cannot use PostgreSQL at DATABASE_URL. "
            "Verify that the database is running and the credentials are correct. "
            f"Original error: {exc}"
        ) from exc


def check_profile_prerequisites(profile: str, target_dir: Path) -> str:
    database_url = resolve_database_url(profile, target_dir)
    if database_url is None:
        raise RuntimeError(f"Profile {profile} did not resolve a database URL.")
    ensure_database_ready(database_url)
    return database_url


def collect_preflight(profile: str) -> tuple[list[str], list[str] | None, str | None]:
    issues: list[str] = []
    ruff_command: list[str] | None = None
    database_url: str | None = None
    try:
        ruff_command = resolve_ruff_command()
    except RuntimeError as exc:
        issues.append(str(exc))
    try:
        database_url = check_profile_prerequisites(
            profile,
            runtime_dir(f"profile-{profile}"),
        )
    except RuntimeError as exc:
        issues.append(str(exc))
    return issues, ruff_command, database_url


def build_validation_orchestrator(
    *,
    profile: str,
    workdir: Path,
    database_url: str,
) -> OrchestratorService:
    resolved_database_url = database_url
    if profile != "controlled":
        sqlite_path = (workdir / "memory.db").as_posix()
        resolved_database_url = f"sqlite:///{sqlite_path}"
    observability = ObservabilityService(database_path=str(workdir / "observability.db"))
    memory = MemoryService(database_url=resolved_database_url)
    operational = OperationalService(artifact_dir=str(workdir / "artifacts"))
    return OrchestratorService(
        governance_service=GovernanceService(),
        memory_service=memory,
        operational_service=operational,
        observability_service=observability,
    )


def run_memory_smoke(profile: str, database_url: str | None = None) -> None:
    smoke_dir = runtime_dir(f"memory-{profile}")
    resolved_database_url = database_url or resolve_database_url(profile, smoke_dir)
    if resolved_database_url is None:
        raise RuntimeError(f"Memory smoke could not resolve a database URL for profile={profile}.")
    suffix = uuid4().hex[:6]
    service = MemoryService(database_url=resolved_database_url)
    contract = InputContract(
        request_id=RequestId(f"req-memory-{suffix}"),
        session_id=SessionId(f"sess-memory-{suffix}"),
        mission_id=MissionId(f"mission-memory-{suffix}"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Validate persistent mission continuity.",
        timestamp=now(),
    )
    service.record_turn(contract, intent="planning", response_text="Mission continuity validated.")
    recovered = service.recover_for_input(contract)
    mission_state = service.get_mission_state(str(contract.mission_id))
    if not recovered.recovered_items:
        raise RuntimeError("Memory smoke failed: recovered_items is empty.")
    if mission_state is None or "planning" not in mission_state.active_tasks:
        raise RuntimeError("Memory smoke failed: mission state was not persisted.")


def run_observability_smoke() -> None:
    smoke_dir = runtime_dir("observability")
    service = ObservabilityService(database_path=str(smoke_dir / "observability.db"))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-validate-1",
                event_name="input_received",
                timestamp=now(),
                source_service="validate-baseline",
                payload={"content": "observability smoke"},
                request_id="req-observe",
                session_id="sess-observe",
                correlation_id="req-observe",
                operation_id="op-observe",
            ),
            InternalEventEnvelope(
                event_id="evt-validate-2",
                event_name="operation_completed",
                timestamp=now(),
                source_service="validate-baseline",
                payload={"status": "completed"},
                request_id="req-observe",
                session_id="sess-observe",
                correlation_id="req-observe",
                operation_id="op-observe",
            ),
        ]
    )
    metrics = service.summarize_flow(
        ObservabilityQuery(request_id="req-observe", operation_id="op-observe")
    )
    if metrics.total_events != 2 or metrics.completed_operations != 1:
        raise RuntimeError("Observability smoke failed: correlated metrics are inconsistent.")
    evidence = service.build_incident_evidence(
        ObservabilityQuery(request_id="req-observe")
    )
    expected_action = "contain_request_and_revert_to_last_validated_baseline"
    if evidence.recommended_operator_action != expected_action:
        raise RuntimeError(
            "Observability smoke failed: incident evidence did not reflect anomaly handling."
        )


def run_evolution_smoke() -> None:
    smoke_dir = runtime_dir("evolution")
    observability = ObservabilityService(database_path=str(smoke_dir / "observability.db"))
    observability.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-evolution-1",
                event_name="input_received",
                timestamp="2026-03-19T00:00:00+00:00",
                source_service="validate-baseline",
                payload={"content": "baseline"},
                request_id="req-baseline",
                session_id="sess-baseline",
                correlation_id="req-baseline",
            ),
            InternalEventEnvelope(
                event_id="evt-evolution-2",
                event_name="operation_completed",
                timestamp="2026-03-19T00:00:02+00:00",
                source_service="validate-baseline",
                payload={"status": "completed"},
                request_id="req-baseline",
                session_id="sess-baseline",
                correlation_id="req-baseline",
                operation_id="op-baseline",
            ),
            InternalEventEnvelope(
                event_id="evt-evolution-3",
                event_name="input_received",
                timestamp="2026-03-19T00:00:03+00:00",
                source_service="validate-baseline",
                payload={"content": "candidate"},
                request_id="req-candidate",
                session_id="sess-candidate",
                correlation_id="req-candidate",
            ),
            InternalEventEnvelope(
                event_id="evt-evolution-4",
                event_name="operation_completed",
                timestamp="2026-03-19T00:00:04+00:00",
                source_service="validate-baseline",
                payload={"status": "completed"},
                request_id="req-candidate",
                session_id="sess-candidate",
                correlation_id="req-candidate",
                operation_id="op-candidate",
            ),
        ]
    )
    service = EvolutionLabService(database_path=str(smoke_dir / "evolution.db"))
    baseline_metrics = observability.summarize_flow(ObservabilityQuery(request_id="req-baseline"))
    candidate_metrics = observability.summarize_flow(ObservabilityQuery(request_id="req-candidate"))
    proposal = service.create_proposal(
        proposal_type="observability-driven-comparison",
        target_scope="validate-baseline",
        hypothesis="Candidate should remain sandbox-only until manual review.",
        expected_gain="Faster validated flow.",
        baseline_refs=["trace://req-baseline"],
        source_signals=["trace://req-baseline", "trace://req-candidate"],
        proposed_tests=["python tools/validate_baseline.py --profile development"],
    )
    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="baseline",
            candidate_label="candidate",
            baseline_metrics={
                "success": 1.0 if baseline_metrics.completed_operations else 0.0,
                "stability": 1.0 if baseline_metrics.error_events == 0 else 0.0,
                "throughput": float(baseline_metrics.total_events),
                "risk": float(baseline_metrics.blocked_events + baseline_metrics.error_events),
            },
            candidate_metrics={
                "success": 1.0 if candidate_metrics.completed_operations else 0.0,
                "stability": 1.0 if candidate_metrics.error_events == 0 else 0.0,
                "throughput": float(candidate_metrics.total_events),
                "risk": float(candidate_metrics.blocked_events + candidate_metrics.error_events),
            },
            governance_refs=["policy://sandbox/manual-review"],
            notes=["validate_baseline smoke"],
        ),
    )
    if comparison.decision.promoted_to is not None:
        raise RuntimeError(
            "Evolution smoke failed: candidate should not be promoted automatically."
        )


def run_governed_mission_smoke(profile: str, database_url: str) -> None:
    workdir = runtime_dir(f"governed-mission-{profile}")
    first = build_validation_orchestrator(
        profile=profile,
        workdir=workdir,
        database_url=database_url,
    )
    second = build_validation_orchestrator(
        profile=profile,
        workdir=workdir,
        database_url=database_url,
    )
    suffix = uuid4().hex[:6]
    mission_id = f"mission-validate-{suffix}"
    session_id = f"sess-validate-{suffix}"
    accepted_contract = InputContract(
        request_id=RequestId(f"req-validate-accepted-{suffix}"),
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Plan the controlled rollout.",
        timestamp=now(),
    )
    deferred_contract = InputContract(
        request_id=RequestId(f"req-validate-defer-{suffix}"),
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Start a new marketing campaign instead.",
        timestamp=now(),
    )
    blocked_contract = InputContract(
        request_id=RequestId(f"req-validate-block-{suffix}"),
        session_id=SessionId(session_id),
        mission_id=MissionId(mission_id),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Delete all mission records now.",
        timestamp=now(),
    )

    accepted = first.handle_input(accepted_contract)
    deferred = second.handle_input(deferred_contract)
    mission_after_defer = second.memory_service.get_mission_state(mission_id)
    blocked = second.handle_input(blocked_contract)
    mission_after_block = second.memory_service.get_mission_state(mission_id)

    if accepted.governance_decision.decision != PermissionDecision.ALLOW_WITH_CONDITIONS:
        raise RuntimeError("Governed mission smoke failed: accepted flow did not stay controlled.")
    if deferred.governance_decision.decision != PermissionDecision.DEFER_FOR_VALIDATION:
        raise RuntimeError("Governed mission smoke failed: conflicting mission was not deferred.")
    if blocked.governance_decision.decision != PermissionDecision.BLOCK:
        raise RuntimeError(
            "Governed mission smoke failed: destructive mission request was not blocked."
        )
    if mission_after_defer is None or mission_after_block is None:
        raise RuntimeError("Governed mission smoke failed: mission continuity was lost.")
    if mission_after_defer.mission_goal != accepted_contract.content:
        raise RuntimeError("Governed mission smoke failed: deferred flow rewrote the mission goal.")
    if mission_after_block.last_recommendation != accepted.deliberative_plan.plan_summary:
        raise RuntimeError(
            "Governed mission smoke failed: blocked flow contaminated the accepted recommendation."
        )
    if mission_after_block.open_loops != accepted.deliberative_plan.open_loops:
        raise RuntimeError(
            "Governed mission smoke failed: blocked flow changed open loops unexpectedly."
        )


def run_console_smoke(profile: str, database_url: str) -> None:
    workdir = runtime_dir(f"console-{profile}")
    suffix = uuid4().hex[:6]
    console = JarvisConsole.build(runtime_dir=workdir, database_url=database_url)
    first = console.ask(
        "Plan the final validation window.",
        session_id=f"console-session-{suffix}",
        mission_id=f"console-mission-{suffix}",
    )
    second = console.ask(
        "Analyze the previous plan.",
        session_id=f"console-session-{suffix}",
        mission_id=f"console-mission-{suffix}",
    )
    rendered = render_response(second, debug=True)
    if not first.response_text or not second.response_text:
        raise RuntimeError("Console smoke failed: empty response returned.")
    if "request_id=" not in rendered or "decision=" not in rendered:
        raise RuntimeError("Console smoke failed: debug render is incomplete.")
    recovered_continuity = any(
        item.startswith("prior_plan=") or item.startswith("context_summary=")
        for item in second.recovered_context
    )
    if not recovered_continuity:
        raise RuntimeError("Console smoke failed: mission continuity was not recovered.")


def write_snapshot(profile: str, database_url: str, checks_passed: list[str]) -> None:
    snapshot = create_baseline_snapshot(
        profile=profile,
        backend=resolve_backend_label(database_url),
        checks_passed=checks_passed,
        operational_decision="go_conditional_for_controlled_production",
    )
    write_baseline_snapshot(snapshot)


def now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> None:
    args = parse_args()
    ensure_command_available("python")
    issues, ruff_command, database_url = collect_preflight(args.profile)
    if issues:
        raise RuntimeError("Validation preflight failed:\n- " + "\n- ".join(issues))
    assert ruff_command is not None
    assert database_url is not None
    run_command(
        [executable, str(ROOT / "tools" / "check_mojibake.py"), str(ROOT)],
        label="encoding-check",
    )
    run_command([executable, "-m", "pytest", "-q"], label="pytest")
    run_command([*ruff_command, "check", "."], label="ruff")
    run_memory_smoke(args.profile, database_url)
    run_observability_smoke()
    run_evolution_smoke()
    run_governed_mission_smoke(args.profile, database_url)
    run_console_smoke(args.profile, database_url)
    write_snapshot(
        args.profile,
        database_url,
        checks_passed=[
            "encoding-check",
            "pytest",
            "ruff",
            "memory_smoke",
            "observability_smoke",
            "evolution_smoke",
            "governed_mission_smoke",
            "console_smoke",
        ],
    )
    print(f"JARVIS v1 validation passed for profile={args.profile}.")


if __name__ == "__main__":
    main()
