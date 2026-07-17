from json import loads
from pathlib import Path
from tempfile import gettempdir
from types import SimpleNamespace
from uuid import uuid4

from tools.longitudinal_learning_report import build_longitudinal_report, save_report


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def audit(
    *,
    request_id: str,
    mission_id: str,
    guidance_ref: str | None,
    success: bool,
    feedback: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        request_id=request_id,
        mission_id=mission_id,
        workflow_profile="software_change_workflow",
        reviewed_learning_influence_refs=[guidance_ref] if guidance_ref else [],
        operator_feedback_assessment=feedback,
        operator_feedback_evidence_refs=[f"feedback://{mission_id}"],
        operator_feedback_rating=5 if feedback == "helpful" else 2,
        anomaly_flags=[] if success else ["runtime_regression"],
        missing_required_events=[],
        trace_complete=success,
        governance_decision="allow",
        operation_status="completed" if success else "failed",
        primary_route="software_development",
    )


def test_report_collector_compares_reviewed_memory_against_runtime_baseline() -> None:
    guidance_ref = "reviewed-learning-guidance://software-change/1.0.0"
    guidance = SimpleNamespace(
        guidance_id=guidance_ref,
        workflow_profile="software_change_workflow",
        review_status="approved",
        source_review_decision_id="review-decision://guidance/1",
        evolution_proposal_id="evolution-proposal://guidance/1",
        evidence_refs=["reflection://guidance/1"],
        rollback_plan_ref="rollback://guidance/1",
        timestamp="2026-07-01T12:00:00Z",
    )
    audits = [
        audit(
            request_id="baseline-1",
            mission_id="baseline-1",
            guidance_ref=None,
            success=True,
            feedback="correction",
        ),
        audit(
            request_id="baseline-2",
            mission_id="baseline-2",
            guidance_ref=None,
            success=False,
            feedback="not_helpful",
        ),
        audit(
            request_id="guidance-1",
            mission_id="guidance-1",
            guidance_ref=guidance_ref,
            success=True,
            feedback="helpful",
        ),
        audit(
            request_id="guidance-2",
            mission_id="guidance-2",
            guidance_ref=guidance_ref,
            success=True,
            feedback="helpful",
        ),
    ]
    observability = SimpleNamespace(
        summarize_recent_requests=lambda limit: audits[:limit],
        list_recent_events=lambda query: [
            SimpleNamespace(timestamp="2026-07-10T12:00:00Z")
        ],
    )
    memory = SimpleNamespace(
        list_reviewed_learning_guidance=lambda limit: [SimpleNamespace(guidance=guidance)]
    )
    evolution = SimpleNamespace(
        list_recent_proposals=lambda limit: [],
        list_recent_decisions=lambda limit: [],
    )

    report = build_longitudinal_report(
        observability_service=observability,
        memory_service=memory,
        evolution_service=evolution,
        generated_at="2026-07-16T12:00:00Z",
    )

    candidate = next(
        metric for metric in report.version_metrics if metric.version_ref == guidance_ref
    )
    # Historical baseline regressions remain visible even when the reviewed
    # version shows a sustained comparative gain.
    assert report.report_status == "attention_required"
    assert candidate.runtime_observation_count == 2
    assert candidate.mission_count == 2
    assert candidate.trend_status == "sustained_gain"
    assert candidate.success_rate_delta == 0.5
    assert candidate.rework_rate_delta == -1.0
    assert report.promotion_authorized is False


def test_report_collector_keeps_inactive_skill_eval_out_of_runtime_claims() -> None:
    proposal = SimpleNamespace(
        evolution_proposal_id="evolution-proposal://skill/1",
        proposal_type="skill_candidate",
        timestamp="2026-07-10T12:00:00Z",
        baseline_refs=["pattern://skill/1"],
        source_signals=["experience://skill/1"],
        strategy_context={
            "evolution_review": {"review_status": "approved"},
            "skill_candidate": {
                "skill_id": "skill://software-change/review",
                "skill_candidate_id": "skill-candidate://software-change/1.0.0",
                "rollback_plan_ref": "rollback://skill/1.0.0",
            },
            "skill_sandbox_eval": {
                "eval_id": "skill-sandbox-eval://software-change/1.0.0",
                "skill_id": "skill://software-change/review",
                "skill_candidate_id": "skill-candidate://software-change/1.0.0",
                "eval_status": "passed_pending_release_gate",
                "pass_rate": 1.0,
                "blockers": [],
            },
        },
    )
    observability = SimpleNamespace(summarize_recent_requests=lambda limit: [])
    memory = SimpleNamespace(list_reviewed_learning_guidance=lambda limit: [])
    evolution = SimpleNamespace(
        list_recent_proposals=lambda limit: [proposal],
        list_recent_decisions=lambda limit: [],
    )

    report = build_longitudinal_report(
        observability_service=observability,
        memory_service=memory,
        evolution_service=evolution,
        generated_at="2026-07-16T12:00:00Z",
    )

    assert report.report_status == "insufficient_evidence"
    assert report.version_metrics[0].offline_observation_count == 1
    assert report.version_metrics[0].runtime_observation_count == 0
    assert report.version_metrics[0].trend_status == "insufficient_evidence"
    assert "offline_eval_is_not_longitudinal_runtime_evidence" in report.limitations
    assert "inactive_versions_have_no_valid_runtime_claim" in report.limitations


def test_save_report_writes_latest_and_immutable_history_evidence() -> None:
    empty = SimpleNamespace(
        summarize_recent_requests=lambda limit: [],
        list_reviewed_learning_guidance=lambda limit: [],
        list_recent_proposals=lambda limit: [],
        list_recent_decisions=lambda limit: [],
    )
    report = build_longitudinal_report(
        observability_service=empty,
        memory_service=empty,
        evolution_service=empty,
        generated_at="2026-07-16T12:00:00Z",
    )

    latest, history = save_report(report, output_dir=runtime_dir("longitudinal-report"))

    assert latest.name == "latest.json"
    assert history != latest
    assert loads(latest.read_text(encoding="utf-8"))["report_status"] == (
        "no_version_targets"
    )
    assert history.read_text(encoding="utf-8") == latest.read_text(encoding="utf-8")
