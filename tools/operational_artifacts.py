"""Operational artifacts for the v1 controlled baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from json import dumps, loads
from pathlib import Path
from subprocess import run

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = ROOT / ".jarvis_runtime" / "operational"
PILOT_ROOT = ROOT / ".jarvis_runtime" / "pilot"


@dataclass(frozen=True)
class BaselineSnapshot:
    baseline_id: str
    git_sha: str
    profile: str
    backend: str
    checks_passed: list[str]
    pilot_status: str
    operational_decision: str
    timestamp: str


@dataclass(frozen=True)
class ContainmentDrill:
    baseline_id: str
    git_sha: str
    profile: str
    trigger_reason: str
    rollback_target: str
    containment_status: str
    operator_action: str
    timestamp: str


def now() -> str:
    return datetime.now(UTC).isoformat()


def artifact_root() -> Path:
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_ROOT


def read_latest_pilot_status() -> str:
    latest = PILOT_ROOT / "latest_pilot.json"
    if not latest.exists():
        return "not_available"
    try:
        payload = loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return "unreadable"
    return str(payload.get("overall_status", "unknown"))


def resolve_backend_label(database_url: str | None) -> str:
    if not database_url:
        return "sqlite"
    if database_url.startswith("postgresql://"):
        return "postgresql"
    if database_url.startswith("sqlite:///"):
        return "sqlite"
    return "custom"


def git_sha() -> str:
    result = run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def create_baseline_snapshot(
    *,
    profile: str,
    backend: str,
    checks_passed: list[str],
    operational_decision: str,
    pilot_status: str | None = None,
) -> BaselineSnapshot:
    return BaselineSnapshot(
        baseline_id=f"baseline-{profile}",
        git_sha=git_sha(),
        profile=profile,
        backend=backend,
        checks_passed=checks_passed,
        pilot_status=pilot_status or read_latest_pilot_status(),
        operational_decision=operational_decision,
        timestamp=now(),
    )


def write_baseline_snapshot(snapshot: BaselineSnapshot) -> tuple[Path, Path]:
    root = artifact_root()
    json_path = root / f"{snapshot.profile}-baseline-snapshot.json"
    md_path = root / f"{snapshot.profile}-baseline-snapshot.md"
    json_path.write_text(dumps(asdict(snapshot), ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(render_baseline_snapshot(snapshot), encoding="utf-8")
    return json_path, md_path


def read_baseline_snapshot(profile: str) -> BaselineSnapshot | None:
    path = artifact_root() / f"{profile}-baseline-snapshot.json"
    if not path.exists():
        return None
    payload = loads(path.read_text(encoding="utf-8"))
    return BaselineSnapshot(**payload)


def create_containment_drill(
    *,
    snapshot: BaselineSnapshot,
    trigger_reason: str,
    operator_action: str = "mark_contained_and_return_to_validated_baseline",
) -> ContainmentDrill:
    return ContainmentDrill(
        baseline_id=snapshot.baseline_id,
        git_sha=snapshot.git_sha,
        profile=snapshot.profile,
        trigger_reason=trigger_reason,
        rollback_target=snapshot.git_sha,
        containment_status="contained",
        operator_action=operator_action,
        timestamp=now(),
    )


def write_containment_drill(drill: ContainmentDrill) -> tuple[Path, Path]:
    root = artifact_root()
    json_path = root / f"{drill.profile}-containment-drill.json"
    md_path = root / f"{drill.profile}-containment-drill.md"
    json_path.write_text(dumps(asdict(drill), ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(render_containment_drill(drill), encoding="utf-8")
    return json_path, md_path


def write_incident_evidence(profile: str, evidence: object) -> tuple[Path, Path]:
    root = artifact_root()
    request_id = getattr(evidence, "request_id", None) or "unknown-request"
    normalized = str(request_id).replace("/", "-")
    json_path = root / f"{profile}-incident-{normalized}.json"
    md_path = root / f"{profile}-incident-{normalized}.md"
    payload = asdict(evidence) if is_dataclass(evidence) else evidence
    json_path.write_text(dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    md_path.write_text(render_incident_evidence(payload), encoding="utf-8")
    return json_path, md_path


def render_baseline_snapshot(snapshot: BaselineSnapshot) -> str:
    checks = ", ".join(snapshot.checks_passed)
    return "\n".join(
        [
            "# Baseline Snapshot",
            "",
            f"- baseline_id: `{snapshot.baseline_id}`",
            f"- git_sha: `{snapshot.git_sha}`",
            f"- profile: `{snapshot.profile}`",
            f"- backend: `{snapshot.backend}`",
            f"- checks_passed: `{checks}`",
            f"- pilot_status: `{snapshot.pilot_status}`",
            f"- operational_decision: `{snapshot.operational_decision}`",
            f"- timestamp: `{snapshot.timestamp}`",
        ]
    )


def render_containment_drill(drill: ContainmentDrill) -> str:
    return "\n".join(
        [
            "# Containment Drill",
            "",
            f"- baseline_id: `{drill.baseline_id}`",
            f"- git_sha: `{drill.git_sha}`",
            f"- profile: `{drill.profile}`",
            f"- trigger_reason: `{drill.trigger_reason}`",
            f"- rollback_target: `{drill.rollback_target}`",
            f"- containment_status: `{drill.containment_status}`",
            f"- operator_action: `{drill.operator_action}`",
            f"- timestamp: `{drill.timestamp}`",
        ]
    )


def render_incident_evidence(payload: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Incident Evidence",
            "",
            f"- request_id: `{payload.get('request_id')}`",
            f"- session_id: `{payload.get('session_id')}`",
            f"- mission_id: `{payload.get('mission_id')}`",
            f"- governance_decision: `{payload.get('governance_decision')}`",
            f"- operation_status: `{payload.get('operation_status')}`",
            f"- flow_summary: `{payload.get('flow_summary')}`",
            f"- anomaly_flags: `{', '.join(payload.get('anomaly_flags', []))}`",
            f"- missing_required_events: `{', '.join(payload.get('missing_required_events', []))}`",
            f"- recommended_operator_action: `{payload.get('recommended_operator_action')}`",
        ]
    )
