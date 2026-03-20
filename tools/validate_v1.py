"""Single entrypoint for validating the JARVIS v1 baseline."""
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
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService

from shared.contracts import InputContract
from shared.events import InternalEventEnvelope
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Validate the JARVIS v1 baseline.")
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
    """Return the preferred ruff invocation for the current environment."""

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
    """Validate connectivity for the configured persistence backend."""

    if not database_url.startswith("postgresql://"):
        return
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on environment packages.
        raise RuntimeError(
            "psycopg is required for the controlled profile. "
            'Install the dev environment with `python -m pip install -e ".[dev,postgres]"`.'
        ) from exc
    try:
        with psycopg.connect(
            database_url,
            connect_timeout=5,
        ) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - depends on runtime infrastructure.
        raise RuntimeError(
            "Controlled profile cannot use PostgreSQL at DATABASE_URL. "
            "Verify that the database is running, the credentials are correct, and, for local "
            "validation, that `docker compose -f infra/local-postgres.compose.yml up -d` "
            "completed. "
            f"Original error: {exc}"
        ) from exc


def check_profile_prerequisites(profile: str, target_dir: Path) -> str:
    """Resolve the runtime database and validate profile-specific prerequisites."""

    database_url = resolve_database_url(profile, target_dir)
    if database_url is None:
        raise RuntimeError(f"Profile {profile} did not resolve a database URL.")
    ensure_database_ready(database_url)
    return database_url


def collect_preflight(profile: str) -> tuple[list[str], str | None, list[str]]:
    """Collect preflight issues before the full validation run starts."""

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


def run_memory_smoke(profile: str, database_url: str | None = None) -> None:
    smoke_dir = runtime_dir(f"memory-{profile}")
    resolved_database_url = database_url or resolve_database_url(profile, smoke_dir)
    if resolved_database_url is None:
        raise RuntimeError(f"Memory smoke could not resolve a database URL for profile={profile}.")
    service = MemoryService(database_url=resolved_database_url)
    contract = InputContract(
        request_id=RequestId("req-memory"),
        session_id=SessionId("sess-memory"),
        mission_id=MissionId("mission-memory"),
        channel=ChannelType.CHAT,
        input_type=InputType.TEXT,
        content="Validate persistent mission continuity.",
        timestamp=now(),
    )
    service.record_turn(contract, intent="planning", response_text="Mission continuity validated.")
    recovered = service.recover_for_input(contract)
    mission_state = service.get_mission_state("mission-memory")
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
                source_service="validate-v1",
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
                source_service="validate-v1",
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


def run_evolution_smoke() -> None:
    smoke_dir = runtime_dir("evolution")
    observability = ObservabilityService(database_path=str(smoke_dir / "observability.db"))
    observability.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-evolution-1",
                event_name="input_received",
                timestamp="2026-03-19T00:00:00+00:00",
                source_service="validate-v1",
                payload={"content": "baseline"},
                request_id="req-baseline",
                session_id="sess-baseline",
                correlation_id="req-baseline",
            ),
            InternalEventEnvelope(
                event_id="evt-evolution-2",
                event_name="operation_completed",
                timestamp="2026-03-19T00:00:02+00:00",
                source_service="validate-v1",
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
                source_service="validate-v1",
                payload={"content": "candidate"},
                request_id="req-candidate",
                session_id="sess-candidate",
                correlation_id="req-candidate",
            ),
            InternalEventEnvelope(
                event_id="evt-evolution-4",
                event_name="operation_completed",
                timestamp="2026-03-19T00:00:04+00:00",
                source_service="validate-v1",
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
        target_scope="validate-v1",
        hypothesis="Candidate should remain sandbox-only until manual review.",
        expected_gain="Faster validated flow.",
        baseline_refs=["trace://req-baseline"],
        source_signals=["trace://req-baseline", "trace://req-candidate"],
        proposed_tests=["python tools/validate_v1.py --profile development"],
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
            notes=["validate_v1 smoke"],
        ),
    )
    if comparison.decision.promoted_to is not None:
        raise RuntimeError(
            "Evolution smoke failed: candidate should not be promoted automatically."
        )


def now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> None:
    args = parse_args()
    ensure_command_available("python")
    issues, ruff_command, database_url = collect_preflight(args.profile)
    if issues:
        raise RuntimeError(
            "Validation preflight failed:\n- " + "\n- ".join(issues)
        )
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
    print(f"JARVIS v1 validation passed for profile={args.profile}.")


if __name__ == "__main__":
    main()



