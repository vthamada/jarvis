from json import loads
from pathlib import Path

from tools.readiness_dashboard import (
    ACTIVE_STATUS_DOCS,
    GateRunResult,
    assess_status_sync,
    build_repository_readiness_report,
    load_longitudinal_readiness_signal,
    parse_capability_map,
    render_text,
    save_report,
)

MASTER_MAP = """# Implementation Master Map

| ID | Capability | Current status | Target | Dependencies | Next slice |
| --- | --- | --- | --- | --- | --- |
| `OP-001` | Governed mission | `implemented_baseline` | Keep stable | Core | none |
| `MEM-001` | Semantic memory | `partial_runtime` | Improve causality | Memory | candidate |
| `OBS-001` | Regression signal | `missing` | Add report | Tools | candidate |
| `SO-001` | Voice | `deferred_by_phase` | Future surface | Realtime | later |

### MB-174 -- Regression And Readiness Dashboard

Status: ready after `MB-173`.
"""

BACKLOG_READY = """# Execution Backlog

### MB-173

- `status`: `done`

### MB-174

- `status`: `ready`
"""


def longitudinal_payload(
    *,
    status: str = "sustained_gain_observed",
    regression_flags: list[str] | None = None,
    promotion_authorized: bool = False,
) -> dict[str, object]:
    return {
        "report_id": "longitudinal-learning-report://readiness-test",
        "report_status": status,
        "regression_flags": regression_flags or [],
        "read_only": True,
        "promotion_authorized": promotion_authorized,
        "automatic_promotion_allowed": False,
        "core_mutation_allowed": False,
    }


def _write_repository_fixture(root: Path, *, backlog: str = BACKLOG_READY) -> None:
    map_path = root / "docs" / "implementation" / "implementation-master-map.md"
    backlog_path = root / "docs" / "implementation" / "execution-backlog.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(MASTER_MAP, encoding="utf-8")
    backlog_path.write_text(backlog, encoding="utf-8")
    for relative_path in ACTIVE_STATUS_DOCS:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("MB-174 is the current queue status.\n", encoding="utf-8")


def test_parse_capability_map_separates_active_candidate_and_deferred() -> None:
    capabilities = parse_capability_map(MASTER_MAP)

    assert [item.capability_id for item in capabilities] == [
        "OP-001",
        "MEM-001",
        "OBS-001",
        "SO-001",
    ]
    assert capabilities[0].scope_status == "baseline"
    assert capabilities[0].readiness_status == "ready"
    assert capabilities[1].scope_status == "candidate"
    assert capabilities[1].readiness_status == "partial"
    assert capabilities[2].readiness_status == "missing"
    assert capabilities[2].blockers == ["capability_not_implemented"]
    assert capabilities[3].scope_status == "deferred"
    assert capabilities[3].readiness_status == "deferred"


def test_status_sync_detects_ready_item_and_master_map_drift(tmp_path: Path) -> None:
    _write_repository_fixture(tmp_path)

    status, ready_item, drift = assess_status_sync(
        root=tmp_path,
        backlog_text=BACKLOG_READY,
        master_map_text=MASTER_MAP,
    )

    assert status == "synchronized"
    assert ready_item == "MB-174"
    assert drift == []

    stale_map = MASTER_MAP.replace("Status: ready", "Status: blocked")
    status, ready_item, drift = assess_status_sync(
        root=tmp_path,
        backlog_text=BACKLOG_READY,
        master_map_text=stale_map,
    )

    assert status == "status_drift"
    assert ready_item == "MB-174"
    assert drift == ["master_map_ready_mismatch:MB-174"]


def test_status_sync_detects_obsolete_ready_claim_in_active_doc(tmp_path: Path) -> None:
    _write_repository_fixture(tmp_path)
    handoff_path = tmp_path / "HANDOFF.md"
    handoff_path.write_text(
        handoff_path.read_text(encoding="utf-8")
        + "`MB-173` e o unico item tecnico `ready`.\n",
        encoding="utf-8",
    )

    status, ready_item, drift = assess_status_sync(
        root=tmp_path,
        backlog_text=BACKLOG_READY,
        master_map_text=MASTER_MAP,
    )

    assert status == "status_drift"
    assert ready_item == "MB-174"
    assert drift == ["active_doc_ready_claim_mismatch:HANDOFF.md:MB-173"]


def test_status_sync_accepts_explicitly_exhausted_queue(tmp_path: Path) -> None:
    exhausted_backlog = BACKLOG_READY.replace("`ready`", "`completed`")
    _write_repository_fixture(tmp_path, backlog=exhausted_backlog)

    status, ready_item, drift = assess_status_sync(
        root=tmp_path,
        backlog_text=exhausted_backlog,
        master_map_text=MASTER_MAP.replace(
            "Status: ready after `MB-173`.",
            "Status: closed in `MB-174`.",
        ),
    )

    assert status == "queue_exhausted"
    assert ready_item is None
    assert drift == []


def test_build_repository_readiness_report_uses_explicit_gate_evidence(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path)
    report = build_repository_readiness_report(
        root=tmp_path,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=["engineering-gate://standard/passed"],
        ),
        document_payload={"decision": "document_guardrails_ok"},
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.status == "ready_with_known_gaps"
    assert report.overall_score == 70
    assert report.backlog_status == "synchronized"
    assert report.next_ready_item == "MB-174"
    assert report.gate_status == "passed"
    assert report.test_status == "passed"
    assert report.blockers == []
    assert report.autonomous_release_allowed is False
    assert "candidate_gaps:OBS-001" in report.warnings

    latest_path, history_path = save_report(
        report,
        output_dir=tmp_path / "reports",
    )
    assert latest_path.exists()
    assert history_path.exists()
    assert loads(latest_path.read_text(encoding="utf-8"))["status"] == (
        "ready_with_known_gaps"
    )


def test_build_repository_readiness_report_blocks_document_drift(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path)
    report = build_repository_readiness_report(
        root=tmp_path,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=[],
        ),
        document_payload={"decision": "document_guardrails_failed"},
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.status == "blocked"
    assert report.document_status == "attention_required"
    assert "document_guardrails_failed" in report.blockers


def test_readiness_dashboard_includes_safe_longitudinal_learning_evidence(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path)
    report = build_repository_readiness_report(
        root=tmp_path,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=["engineering-gate://standard/passed"],
        ),
        document_payload={"decision": "document_guardrails_ok"},
        longitudinal_payload=longitudinal_payload(),
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.longitudinal_learning_status == "sustained_gain_observed"
    assert report.longitudinal_regression_flags == []
    assert report.longitudinal_learning_authority_safe is True
    assert report.longitudinal_learning_evidence_ref in report.evidence_refs
    assert "longitudinal_learning_evidence:not_evaluated" not in report.warnings
    assert "longitudinal_learning_status=sustained_gain_observed" in render_text(report)
    assert "longitudinal_learning_authority_safe=true" in render_text(report)


def test_readiness_dashboard_surfaces_longitudinal_regression_without_promotion(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path)
    report = build_repository_readiness_report(
        root=tmp_path,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=[],
        ),
        document_payload={"decision": "document_guardrails_ok"},
        longitudinal_payload=longitudinal_payload(
            status="attention_required",
            regression_flags=["workflow:version-2:regression_detected"],
        ),
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.status == "ready_with_known_gaps"
    assert report.blockers == []
    assert report.autonomous_release_allowed is False
    assert report.warnings[0] == (
        "longitudinal_learning_attention_required:"
        "workflow:version-2:regression_detected"
    )


def test_readiness_dashboard_blocks_longitudinal_authority_claim(
    tmp_path: Path,
) -> None:
    _write_repository_fixture(tmp_path)
    report = build_repository_readiness_report(
        root=tmp_path,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=[],
        ),
        document_payload={"decision": "document_guardrails_ok"},
        longitudinal_payload=longitudinal_payload(promotion_authorized=True),
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.status == "blocked"
    assert report.longitudinal_learning_authority_safe is False
    assert "longitudinal_learning_authority_violation" in report.blockers


def test_longitudinal_readiness_signal_fails_closed_on_invalid_json(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "latest.json"
    report_path.write_text("{not-json", encoding="utf-8")

    signal = load_longitudinal_readiness_signal(report_path=report_path)

    assert signal.report_status == "invalid_evidence"
    assert signal.authority_safe is False
