from pathlib import Path

from tools.readiness_dashboard import (
    GateRunResult,
    build_repository_readiness_report,
)

ROOT = Path(__file__).resolve().parents[2]


def _safe_longitudinal_payload() -> dict[str, object]:
    return {
        "report_id": "longitudinal-learning-report://mb200-closure-test",
        "report_status": "sustained_gain_observed",
        "regression_flags": [],
        "read_only": True,
        "promotion_authorized": False,
        "automatic_promotion_allowed": False,
        "core_mutation_allowed": False,
    }


def test_daily_operator_loop_runbook_covers_governed_end_to_end_path() -> None:
    runbook = (ROOT / "docs/operations/daily-operator-loop-runbook.md").read_text(
        encoding="utf-8"
    )

    required_commands = (
        "doctor",
        "daily-workspace",
        "operator-dashboard",
        "mission-workflow",
        "open-loops",
        "resume-loop",
        "work-item",
        "artifact",
        "progress-report",
        "mission-feedback",
        "experience-reflections",
        "evolution-review-queue",
        "operator-outcomes",
        "readiness_dashboard.py --run-gate standard",
    )
    assert all(command in runbook for command in required_commands)
    assert "Resume only revalidates" in runbook
    assert "autonomous promotion" in runbook
    assert "voice/realtime" in runbook


def test_mb200_repository_closure_is_synchronized_and_bounded() -> None:
    report = build_repository_readiness_report(
        root=ROOT,
        gate_result=GateRunResult(
            gate_mode="standard",
            gate_status="passed",
            test_status="passed",
            evidence_refs=["engineering-gate://standard/passed"],
        ),
        longitudinal_payload=_safe_longitudinal_payload(),
        generated_at="2026-07-18T12:00:00Z",
    )

    assert report.status == "ready_with_known_gaps"
    assert report.backlog_status == "queue_exhausted"
    assert report.next_ready_item is None
    assert report.status_drift == []
    assert report.blockers == []
    assert report.document_status == "healthy"
    assert report.gate_status == "passed"
    assert report.test_status == "passed"
    assert report.autonomous_release_allowed is False

    capabilities = {item.capability_id: item for item in report.capability_results}
    for capability_id in ("SFC-006", "SFC-007", "ACT-006", "ACT-007", "ACT-009"):
        assert capabilities[capability_id].scope_status == "deferred"
        assert capabilities[capability_id].readiness_status == "deferred"
