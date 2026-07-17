"""Build a compact repository regression and readiness report."""

from __future__ import annotations

import re
from argparse import ArgumentParser, Namespace
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from json import dumps, loads
from pathlib import Path
from subprocess import run
from sys import executable
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.contracts import (
    CapabilityReadinessContract,
    RegressionReadinessReportContract,
)
from tools.verify_document_guardrails import build_payload as build_document_payload

ROOT = Path(__file__).resolve().parent.parent
MASTER_MAP_PATH = Path("docs/implementation/implementation-master-map.md")
EXECUTION_BACKLOG_PATH = Path("docs/implementation/execution-backlog.md")
ACTIVE_STATUS_DOCS = (
    Path("HANDOFF.md"),
    Path("docs/implementation/v2-adherence-snapshot.md"),
    Path("docs/implementation/unified-gap-and-absorption-backlog.md"),
)
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "readiness"
LONGITUDINAL_REPORT_PATH = Path(
    ".jarvis_runtime/learning/longitudinal/latest.json"
)
CAPABILITY_ID_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3}$")
MB_HEADING_PATTERN = re.compile(
    r"^### (MB-\d+)(?: -- [^\n]+)?\s*$([\s\S]*?)(?=^### |\Z)",
    re.MULTILINE,
)
READY_ITEM_CLAIM_PATTERN = re.compile(
    r"`(MB-\d+)`\s+e o unico item tecnico `ready`",
)

READY_STATUSES = {"implemented_baseline", "resolved_in_baseline"}
PARTIAL_STATUSES = {
    "minimum_baseline",
    "partial_runtime",
    "partial_runtime_enforced",
    "resolved_minimum_baseline",
}
ATTENTION_STATUSES = {"documentation_only", "candidate", "planned"}
DEFERRED_STATUSES = {
    "deferred",
    "deferred_by_phase",
    "research_only",
    "research_horizon",
}


@dataclass(frozen=True)
class GateRunResult:
    gate_mode: str
    gate_status: str
    test_status: str
    evidence_refs: list[str]


@dataclass(frozen=True)
class LongitudinalReadinessSignal:
    report_status: str
    regression_flags: list[str]
    evidence_ref: str | None
    authority_safe: bool


def _clean_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _scope_status(*, source_status: str, next_slice: str) -> str:
    normalized_next = next_slice.strip().lower()
    if source_status in DEFERRED_STATUSES or normalized_next in {"later", "not now"}:
        return "deferred"
    if normalized_next == "none":
        return "baseline"
    return "candidate"


def _readiness_status(source_status: str) -> tuple[str, int]:
    if source_status in READY_STATUSES:
        return "ready", 100
    if source_status in PARTIAL_STATUSES:
        return "partial", 70
    if source_status in ATTENTION_STATUSES:
        return "attention_required", 40
    if source_status == "missing":
        return "missing", 0
    if source_status in DEFERRED_STATUSES:
        return "deferred", 0
    return "attention_required", 25


def parse_capability_map(text: str) -> list[CapabilityReadinessContract]:
    """Parse capability rows from the master map without duplicating their status."""

    capabilities: list[CapabilityReadinessContract] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not CAPABILITY_ID_PATTERN.fullmatch(cells[0]):
            continue
        capability_id, name, source_status, target, dependencies, next_slice = cells
        readiness_status, score = _readiness_status(source_status)
        scope_status = _scope_status(
            source_status=source_status,
            next_slice=next_slice,
        )
        if scope_status == "deferred":
            readiness_status = "deferred"
            score = 0
        blockers = []
        if readiness_status == "missing" and scope_status != "deferred":
            blockers.append("capability_not_implemented")
        elif source_status not in (
            READY_STATUSES
            | PARTIAL_STATUSES
            | ATTENTION_STATUSES
            | DEFERRED_STATUSES
            | {"missing"}
        ):
            blockers.append(f"unknown_master_map_status:{source_status}")
        capabilities.append(
            CapabilityReadinessContract(
                capability_id=capability_id,
                capability_name=name,
                source_status=source_status,
                scope_status=scope_status,
                readiness_status=readiness_status,
                score=score,
                target=target,
                dependencies=dependencies,
                next_slice=next_slice,
                evidence_refs=[
                    f"docs://implementation-master-map/capability/{capability_id}"
                ],
                blockers=blockers,
            )
        )
    return capabilities


def parse_micro_backlog_statuses(text: str) -> dict[str, str]:
    """Read MB statuses from the executable backlog."""

    statuses: dict[str, str] = {}
    for match in MB_HEADING_PATTERN.finditer(text):
        status_match = re.search(r"^- `status`: `([^`]+)`", match.group(2), re.MULTILINE)
        if status_match:
            statuses[match.group(1)] = status_match.group(1)
    return statuses


def parse_master_map_mb_statuses(text: str) -> dict[str, str]:
    """Read narrative MB statuses from the master map queue."""

    statuses: dict[str, str] = {}
    for match in MB_HEADING_PATTERN.finditer(text):
        status_match = re.search(r"^Status: ([^\n]+)", match.group(2), re.MULTILINE)
        if status_match:
            statuses[match.group(1)] = status_match.group(1).strip().lower()
    return statuses


def assess_status_sync(
    *,
    root: Path,
    backlog_text: str,
    master_map_text: str,
) -> tuple[str, str | None, list[str]]:
    """Compare the executable queue with its active documentary projections."""

    backlog_statuses = parse_micro_backlog_statuses(backlog_text)
    master_statuses = parse_master_map_mb_statuses(master_map_text)
    ready_items = [item for item, status in backlog_statuses.items() if status == "ready"]
    drift: list[str] = []
    next_ready_item = ready_items[0] if len(ready_items) == 1 else None

    if len(ready_items) > 1:
        drift.append(f"multiple_ready_items:{','.join(sorted(ready_items))}")
    elif next_ready_item:
        master_status = master_statuses.get(next_ready_item, "")
        if not master_status.startswith("ready"):
            drift.append(f"master_map_ready_mismatch:{next_ready_item}")

    latest_item = max(
        backlog_statuses,
        key=lambda item: int(item.split("-")[1]),
        default=None,
    )
    expected_marker = next_ready_item or latest_item
    if expected_marker:
        for relative_path in ACTIVE_STATUS_DOCS:
            path = root / relative_path
            document_text = _read_text(path) if path.exists() else ""
            if expected_marker not in document_text:
                drift.append(f"active_doc_missing_status:{relative_path.as_posix()}")
            current_claims = READY_ITEM_CLAIM_PATTERN.findall(document_text)
            expected_claims = {next_ready_item} if next_ready_item else set()
            for claim in current_claims:
                if claim not in expected_claims:
                    drift.append(
                        "active_doc_ready_claim_mismatch:"
                        f"{relative_path.as_posix()}:{claim}"
                    )

    if drift:
        return "status_drift", next_ready_item, drift
    if next_ready_item:
        return "synchronized", next_ready_item, []
    return "queue_exhausted", None, []


def run_engineering_gate(*, root: Path, mode: str) -> GateRunResult:
    """Run an explicitly requested gate using a fixed local command."""

    project_python = root / ".venv" / "Scripts" / "python.exe"
    runner = str(project_python) if project_python.exists() else executable
    result = run(
        [runner, "tools/engineering_gate.py", "--mode", mode],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    gate_status = "passed" if result.returncode == 0 else "failed"
    test_status = (
        gate_status if mode in {"standard", "release"} else "not_run"
    )
    return GateRunResult(
        gate_mode=mode,
        gate_status=gate_status,
        test_status=test_status,
        evidence_refs=[f"engineering-gate://{mode}/{gate_status}"],
    )


def _default_gate_result() -> GateRunResult:
    return GateRunResult(
        gate_mode="not_run",
        gate_status="not_run",
        test_status="not_run",
        evidence_refs=[],
    )


def load_longitudinal_readiness_signal(
    *,
    report_path: Path,
    payload: dict[str, object] | None = None,
) -> LongitudinalReadinessSignal:
    """Read MB-188 evidence without treating it as release authority."""

    raw_payload: object = payload
    if raw_payload is None:
        if not report_path.exists():
            return LongitudinalReadinessSignal(
                report_status="not_evaluated",
                regression_flags=[],
                evidence_ref=None,
                authority_safe=True,
            )
        try:
            raw_payload = loads(report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raw_payload = None
    if not isinstance(raw_payload, dict):
        return LongitudinalReadinessSignal(
            report_status="invalid_evidence",
            regression_flags=[],
            evidence_ref=None,
            authority_safe=False,
        )

    report_status = raw_payload.get("report_status")
    report_id = raw_payload.get("report_id")
    regression_flags = raw_payload.get("regression_flags")
    valid_flags = (
        isinstance(regression_flags, list)
        and all(isinstance(item, str) and item for item in regression_flags)
    )
    authority_safe = (
        raw_payload.get("read_only") is True
        and raw_payload.get("promotion_authorized") is False
        and raw_payload.get("automatic_promotion_allowed") is False
        and raw_payload.get("core_mutation_allowed") is False
    )
    if (
        not isinstance(report_status, str)
        or not isinstance(report_id, str)
        or not report_id
        or not valid_flags
    ):
        return LongitudinalReadinessSignal(
            report_status="invalid_evidence",
            regression_flags=[],
            evidence_ref=None,
            authority_safe=False,
        )
    return LongitudinalReadinessSignal(
        report_status=report_status,
        regression_flags=list(dict.fromkeys(regression_flags)),
        evidence_ref=report_id,
        authority_safe=authority_safe,
    )


def build_repository_readiness_report(
    *,
    root: Path = ROOT,
    gate_mode: str | None = None,
    gate_result: GateRunResult | None = None,
    document_payload: dict[str, object] | None = None,
    longitudinal_report_path: Path | None = None,
    longitudinal_payload: dict[str, object] | None = None,
    generated_at: str | None = None,
) -> RegressionReadinessReportContract:
    """Collect canonical repository signals and build one bounded report."""

    master_map_text = _read_text(root / MASTER_MAP_PATH)
    backlog_text = _read_text(root / EXECUTION_BACKLOG_PATH)
    capabilities = parse_capability_map(master_map_text)
    backlog_status, next_ready_item, status_drift = assess_status_sync(
        root=root,
        backlog_text=backlog_text,
        master_map_text=master_map_text,
    )
    documents = document_payload or build_document_payload(root=root)
    document_status = (
        "healthy"
        if documents.get("decision") == "document_guardrails_ok"
        else "attention_required"
    )
    resolved_gate = gate_result or (
        run_engineering_gate(root=root, mode=gate_mode)
        if gate_mode
        else _default_gate_result()
    )
    longitudinal_signal = load_longitudinal_readiness_signal(
        report_path=(
            longitudinal_report_path
            if longitudinal_report_path is not None
            else root / LONGITUDINAL_REPORT_PATH
        ),
        payload=longitudinal_payload,
    )
    timestamp = generated_at or datetime.now(UTC).isoformat()
    evidence_refs = [
        "docs://implementation-master-map",
        "docs://execution-backlog",
        f"document-guardrails://{document_status}",
        *resolved_gate.evidence_refs,
    ]
    return ObservabilityService.build_regression_readiness_report(
        report_id=f"regression-readiness://{uuid4().hex[:12]}",
        capability_results=capabilities,
        gate_mode=resolved_gate.gate_mode,
        gate_status=resolved_gate.gate_status,
        test_status=resolved_gate.test_status,
        document_status=document_status,
        backlog_status=backlog_status,
        next_ready_item=next_ready_item,
        status_drift=status_drift,
        evidence_refs=evidence_refs,
        generated_at=timestamp,
        longitudinal_learning_status=longitudinal_signal.report_status,
        longitudinal_regression_flags=longitudinal_signal.regression_flags,
        longitudinal_learning_evidence_ref=longitudinal_signal.evidence_ref,
        longitudinal_learning_authority_safe=longitudinal_signal.authority_safe,
    )


def render_text(report: RegressionReadinessReportContract) -> str:
    counts = report.capability_counts
    lines = [
        "regression_readiness=read_only",
        f"status={report.status}",
        f"overall_score={report.overall_score}",
        f"gate_mode={report.gate_mode}",
        f"gate_status={report.gate_status}",
        f"test_status={report.test_status}",
        f"document_status={report.document_status}",
        f"backlog_status={report.backlog_status}",
        f"next_ready_item={report.next_ready_item or 'none'}",
        f"longitudinal_learning_status={report.longitudinal_learning_status}",
        "longitudinal_regression_flags="
        f"{','.join(report.longitudinal_regression_flags) or 'none'}",
        "longitudinal_learning_evidence_ref="
        f"{report.longitudinal_learning_evidence_ref or 'none'}",
        "longitudinal_learning_authority_safe="
        f"{str(report.longitudinal_learning_authority_safe).lower()}",
        (
            "capabilities="
            f"ready:{counts.get('ready', 0)},"
            f"partial:{counts.get('partial', 0)},"
            f"attention:{counts.get('attention_required', 0)},"
            f"missing:{counts.get('missing', 0)},"
            f"deferred:{counts.get('deferred', 0)}"
        ),
        f"status_drift={','.join(report.status_drift) or 'none'}",
        f"blockers={','.join(report.blockers) or 'none'}",
        f"warnings={','.join(report.warnings) or 'none'}",
        "autonomous_release_allowed=false",
    ]
    return "\n".join(lines)


def save_report(
    report: RegressionReadinessReportContract,
    *,
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    payload = dumps(asdict(report), ensure_ascii=False, indent=2)
    latest_path = output_dir / "latest.json"
    safe_timestamp = re.sub(r"[^0-9A-Za-z]+", "-", str(report.generated_at)).strip("-")
    history_path = history_dir / f"readiness-{safe_timestamp}.json"
    latest_path.write_text(payload + "\n", encoding="utf-8")
    history_path.write_text(payload + "\n", encoding="utf-8")
    return latest_path, history_path


def parse_args() -> Namespace:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--run-gate", choices=["quick", "standard"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--longitudinal-report")
    parser.add_argument("--no-save", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_repository_readiness_report(
        gate_mode=args.run_gate,
        longitudinal_report_path=(
            Path(args.longitudinal_report) if args.longitudinal_report else None
        ),
    )
    if not args.no_save:
        save_report(report, output_dir=Path(args.output_dir))
    print(
        dumps(asdict(report), ensure_ascii=False, indent=2)
        if args.format == "json"
        else render_text(report)
    )
    if report.status == "blocked":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
