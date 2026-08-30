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


def attribution(
    *,
    request_id: str,
    mission_id: str,
    guidance_ref: str | None,
    attribution_status: str = "declared_causality",
) -> SimpleNamespace:
    return SimpleNamespace(
        attribution_record_id=f"decision-outcome-attribution://request/{request_id}",
        request_id=request_id,
        session_id=f"session:{request_id}",
        mission_id=mission_id,
        experience_id=f"experience://{mission_id}/{request_id}",
        workflow_profile="software_change_workflow",
        route="software_development",
        memory_selected_refs=[guidance_ref] if guidance_ref else [],
        attribution_status=attribution_status,
        gain_claim_status="not_established_without_comparator",
        causal_effect_proven=False,
        memory_write_allowed=False,
        execution_allowed=False,
        tool_dispatch_allowed=False,
        promotion_authorized=False,
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
        observed_at="2026-07-10T12:00:00Z",
    )


def feedback_event(
    *,
    request_id: str,
    mission_id: str,
    assessment: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        event_id=f"feedback-event:{request_id}",
        event_name="operator_feedback_recorded",
        mission_id=mission_id,
        payload={
            "operator_feedback_experience_id": (
                f"experience://{mission_id}/{request_id}"
            ),
            "operator_feedback_assessment": assessment,
            "operator_feedback_rating": 5 if assessment == "helpful" else 2,
        },
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
    attributions = [
        attribution(
            request_id=item.request_id,
            mission_id=item.mission_id,
            guidance_ref=(
                guidance_ref if item.request_id.startswith("guidance-") else None
            ),
        )
        for item in audits
    ]
    feedback_events = [
        feedback_event(
            request_id=item.request_id,
            mission_id=item.mission_id,
            assessment=item.operator_feedback_assessment,
        )
        for item in audits
    ]
    observability = SimpleNamespace(
        summarize_recent_requests=lambda limit: audits[:limit],
        list_recent_events=lambda query: feedback_events[: query.limit],
    )
    memory = SimpleNamespace(
        list_reviewed_learning_guidance=lambda limit: [SimpleNamespace(guidance=guidance)],
        list_decision_outcome_attributions=lambda limit: attributions[:limit],
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
    # Historical baseline regressions remain visible, but runtime attribution
    # without a controlled comparator cannot become a gain claim.
    assert report.report_status == "attention_required"
    assert candidate.runtime_observation_count == 2
    assert candidate.mission_count == 2
    assert candidate.trend_status == "stable_or_mixed"
    assert candidate.success_rate_delta == 0.5
    assert candidate.rework_rate_delta == -1.0
    assert report.promotion_authorized is False
    assert (
        "decision_attribution_does_not_establish_gain_without_comparator"
        in report.limitations
    )


def test_runtime_trace_without_canonical_attribution_is_not_backfilled() -> None:
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
    legacy_audit = audit(
        request_id="legacy-without-attribution",
        mission_id="legacy-without-attribution",
        guidance_ref=guidance_ref,
        success=True,
        feedback="helpful",
    )
    observability = SimpleNamespace(
        summarize_recent_requests=lambda limit: [legacy_audit],
        list_recent_events=lambda query: [],
    )
    memory = SimpleNamespace(
        list_reviewed_learning_guidance=lambda limit: [SimpleNamespace(guidance=guidance)],
        list_decision_outcome_attributions=lambda limit: [],
    )
    evolution = SimpleNamespace(
        list_recent_proposals=lambda limit: [],
        list_recent_decisions=lambda limit: [],
    )

    report = build_longitudinal_report(
        observability_service=observability,
        memory_service=memory,
        evolution_service=evolution,
        minimum_observations=2,
        generated_at="2026-07-16T12:00:00Z",
    )

    candidate = next(
        metric for metric in report.version_metrics if metric.version_ref == guidance_ref
    )
    assert candidate.runtime_observation_count == 0
    assert candidate.trend_status == "insufficient_evidence"


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
    memory = SimpleNamespace(
        list_reviewed_learning_guidance=lambda limit: [],
        list_decision_outcome_attributions=lambda limit: [],
    )
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
        list_decision_outcome_attributions=lambda limit: [],
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
