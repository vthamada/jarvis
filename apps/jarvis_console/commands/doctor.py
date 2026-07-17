"""Read-only local preflight checks for the JARVIS operator console."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from os import R_OK, W_OK, access
from pathlib import Path
from sqlite3 import connect
from sys import version_info

from tools.readiness_dashboard import assess_status_sync


@dataclass(frozen=True)
class DoctorCheck:
    check_id: str
    status: str
    summary: str
    required: bool
    evidence_refs: list[str]


@dataclass(frozen=True)
class DoctorReport:
    status: str
    checks: list[DoctorCheck]
    passed_count: int
    warning_count: int
    failed_count: int
    recommended_exit_code: int
    read_only: bool = True
    repair_allowed: bool = False
    write_attempted: bool = False
    secrets_redacted: bool = True


CORE_IMPORTS = (
    "identity_engine.engine",
    "cognitive_engine.engine",
    "executive_engine.engine",
    "planning_engine.engine",
    "specialist_engine.engine",
    "synthesis_engine.engine",
    "orchestrator_service.service",
    "governance_service.service",
    "memory_service.service",
    "knowledge_service.service",
    "observability_service.service",
    "operational_service.service",
    "evolution_lab.service",
)


def build_doctor_report(
    *,
    root: Path,
    runtime_dir: Path,
    memory_db: Path,
    evolution_db: Path,
    observability_db: Path,
) -> DoctorReport:
    """Inspect local readiness without creating directories or opening writable DBs."""

    checks = [
        _python_check(),
        _import_check(),
        _runtime_directory_check(runtime_dir),
        _sqlite_store_check("memory_store", memory_db),
        _sqlite_store_check("evolution_store", evolution_db),
        _sqlite_store_check("observability_store", observability_db),
        _backlog_check(root),
        _governance_check(),
        _gate_check(root),
    ]
    passed_count = sum(check.status == "passed" for check in checks)
    warning_count = sum(check.status == "warning" for check in checks)
    failed_count = sum(check.status == "failed" for check in checks)
    status = "failed" if failed_count else "degraded" if warning_count else "healthy"
    return DoctorReport(
        status=status,
        checks=checks,
        passed_count=passed_count,
        warning_count=warning_count,
        failed_count=failed_count,
        recommended_exit_code=1 if failed_count else 0,
    )


def render_doctor_report(report: DoctorReport) -> str:
    lines = [
        "doctor=read_only",
        f"status={report.status}",
        f"passed={report.passed_count}",
        f"warnings={report.warning_count}",
        f"failed={report.failed_count}",
        f"recommended_exit_code={report.recommended_exit_code}",
        "repair_allowed=False",
        "write_attempted=False",
        "secrets_redacted=True",
    ]
    for check in report.checks:
        lines.extend(
            [
                "---",
                f"check_id={check.check_id}",
                f"check_status={check.status}",
                f"required={check.required}",
                f"summary={check.summary}",
                f"evidence_refs={','.join(check.evidence_refs) or 'none'}",
            ]
        )
    return "\n".join(lines)


def _python_check() -> DoctorCheck:
    supported = version_info >= (3, 11)
    return DoctorCheck(
        check_id="python_runtime",
        status="passed" if supported else "failed",
        summary=(
            "python_runtime_supported"
            if supported
            else "python_3_11_or_newer_required"
        ),
        required=True,
        evidence_refs=[f"python://{version_info.major}.{version_info.minor}"],
    )


def _import_check() -> DoctorCheck:
    unavailable: list[str] = []
    for module_name in CORE_IMPORTS:
        try:
            import_module(module_name)
        except Exception:
            unavailable.append(module_name)
    return DoctorCheck(
        check_id="core_imports",
        status="failed" if unavailable else "passed",
        summary=(
            "core_imports_available"
            if not unavailable
            else f"unavailable_modules:{','.join(unavailable)}"
        ),
        required=True,
        evidence_refs=["runtime://core-imports"],
    )


def _runtime_directory_check(runtime_dir: Path) -> DoctorCheck:
    if runtime_dir.exists():
        usable = runtime_dir.is_dir() and access(runtime_dir, R_OK | W_OK)
        return DoctorCheck(
            check_id="runtime_directory",
            status="passed" if usable else "failed",
            summary=(
                "runtime_directory_available"
                if usable
                else "runtime_directory_unavailable"
            ),
            required=True,
            evidence_refs=["runtime://directory"],
        )
    parent = _nearest_existing_parent(runtime_dir)
    initializable = parent.is_dir() and access(parent, R_OK | W_OK)
    return DoctorCheck(
        check_id="runtime_directory",
        status="warning" if initializable else "failed",
        summary=(
            "runtime_directory_not_initialized"
            if initializable
            else "runtime_directory_parent_unavailable"
        ),
        required=True,
        evidence_refs=["runtime://directory"],
    )


def _sqlite_store_check(check_id: str, database_path: Path) -> DoctorCheck:
    if not database_path.exists():
        return DoctorCheck(
            check_id=check_id,
            status="warning",
            summary="store_not_initialized",
            required=False,
            evidence_refs=[f"store://{check_id}"],
        )
    if not database_path.is_file():
        return DoctorCheck(
            check_id=check_id,
            status="failed",
            summary="store_path_is_not_file",
            required=False,
            evidence_refs=[f"store://{check_id}"],
        )
    try:
        connection = connect(
            f"{database_path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=1.0,
        )
        try:
            connection.execute("PRAGMA query_only = ON")
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        finally:
            connection.close()
    except Exception as exc:
        return DoctorCheck(
            check_id=check_id,
            status="failed",
            summary=f"store_unreachable:{type(exc).__name__}",
            required=False,
            evidence_refs=[f"store://{check_id}"],
        )
    return DoctorCheck(
        check_id=check_id,
        status="passed",
        summary="store_read_only_reachable",
        required=False,
        evidence_refs=[f"store://{check_id}"],
    )


def _backlog_check(root: Path) -> DoctorCheck:
    backlog_path = root / "docs" / "implementation" / "execution-backlog.md"
    map_path = root / "docs" / "implementation" / "implementation-master-map.md"
    try:
        backlog_text = backlog_path.read_text(encoding="utf-8-sig")
        master_map_text = map_path.read_text(encoding="utf-8-sig")
        status, ready_item, drift = assess_status_sync(
            root=root,
            backlog_text=backlog_text,
            master_map_text=master_map_text,
        )
    except Exception as exc:
        return DoctorCheck(
            check_id="backlog_state",
            status="failed",
            summary=f"backlog_unreadable:{type(exc).__name__}",
            required=True,
            evidence_refs=["docs://execution-backlog"],
        )
    synchronized = status in {"synchronized", "queue_exhausted"} and not drift
    return DoctorCheck(
        check_id="backlog_state",
        status="passed" if synchronized else "failed",
        summary=(
            f"{status}:{ready_item or 'none'}"
            if synchronized
            else f"status_drift:{','.join(drift) or 'unknown'}"
        ),
        required=True,
        evidence_refs=["docs://execution-backlog", "docs://implementation-master-map"],
    )


def _governance_check() -> DoctorCheck:
    try:
        module = import_module("governance_service.service")
        service = module.GovernanceService()
        available = service.name == "governance-service"
    except Exception:
        available = False
    return DoctorCheck(
        check_id="governance_boundary",
        status="passed" if available else "failed",
        summary=(
            "governance_service_available"
            if available
            else "governance_service_unavailable"
        ),
        required=True,
        evidence_refs=["governance://service-boundary"],
    )


def _gate_check(root: Path) -> DoctorCheck:
    gate_path = root / "tools" / "engineering_gate.py"
    available = gate_path.is_file()
    return DoctorCheck(
        check_id="engineering_gate",
        status="passed" if available else "failed",
        summary=(
            "engineering_gate_discoverable"
            if available
            else "engineering_gate_missing"
        ),
        required=True,
        evidence_refs=["engineering-gate://discoverability"],
    )


def _nearest_existing_parent(path: Path) -> Path:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate
