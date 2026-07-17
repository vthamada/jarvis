"""Build a governed longitudinal report from existing runtime and eval evidence."""

from __future__ import annotations

from argparse import ArgumentParser
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from pathlib import Path

from evolution_lab.service import EvolutionLabService
from memory_service.service import MemoryService
from observability_service.service import (
    FlowAudit,
    ObservabilityQuery,
    ObservabilityService,
)

from shared.contracts import (
    EvolutionDecisionContract,
    EvolutionProposalContract,
    LearningOutcomeObservationContract,
    LearningVersionTargetContract,
    LongitudinalLearningReportContract,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / ".jarvis_runtime" / "learning" / "longitudinal"


def collect_longitudinal_inputs(
    *,
    observability_service: ObservabilityService,
    memory_service: MemoryService,
    evolution_service: EvolutionLabService,
    limit: int,
    generated_at: str,
) -> tuple[list[LearningVersionTargetContract], list[LearningOutcomeObservationContract]]:
    """Collect bounded targets and observations without writing operational state."""

    safe_limit = max(1, min(limit, 500))
    proposals = evolution_service.list_recent_proposals(limit=safe_limit)
    decisions = evolution_service.list_recent_decisions(limit=safe_limit)
    guidance_records = memory_service.list_reviewed_learning_guidance(limit=safe_limit)
    targets = _proposal_targets(proposals, decisions)
    guidance_targets = _guidance_targets(guidance_records, decisions, generated_at)
    targets.extend(guidance_targets)
    targets = _dedupe_targets(targets)
    observations = _proposal_eval_observations(proposals)
    observations.extend(
        _runtime_observations(
            observability_service=observability_service,
            targets=targets,
            limit=safe_limit,
        )
    )
    return targets, observations


def build_longitudinal_report(
    *,
    observability_service: ObservabilityService,
    memory_service: MemoryService,
    evolution_service: EvolutionLabService,
    limit: int = 100,
    minimum_observations: int = 2,
    generated_at: str | None = None,
) -> LongitudinalLearningReportContract:
    """Build one read-only report from canonical services."""

    safe_generated_at = generated_at or datetime.now(UTC).isoformat()
    targets, observations = collect_longitudinal_inputs(
        observability_service=observability_service,
        memory_service=memory_service,
        evolution_service=evolution_service,
        limit=limit,
        generated_at=safe_generated_at,
    )
    report_seed = "|".join(
        [
            safe_generated_at,
            *(target.target_id for target in targets),
            *(observation.observation_id for observation in observations),
        ]
    )
    return ObservabilityService.build_longitudinal_learning_report(
        report_id=(
            "longitudinal-learning-report://"
            f"{sha256(report_seed.encode()).hexdigest()[:16]}"
        ),
        targets=targets,
        observations=observations,
        generated_at=safe_generated_at,
        minimum_observations=minimum_observations,
    )


def save_report(
    report: LongitudinalLearningReportContract,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Persist report evidence outside canonical runtime stores."""

    output_dir.mkdir(parents=True, exist_ok=True)
    payload = dumps(asdict(report), indent=2, sort_keys=True)
    latest_path = output_dir / "latest.json"
    history_path = output_dir / f"{_safe_timestamp(report.generated_at)}.json"
    latest_path.write_text(payload + "\n", encoding="utf-8")
    history_path.write_text(payload + "\n", encoding="utf-8")
    return latest_path, history_path


def _proposal_targets(
    proposals: list[EvolutionProposalContract],
    decisions: list[EvolutionDecisionContract],
) -> list[LearningVersionTargetContract]:
    rollback_status = _rollback_status_by_proposal(decisions)
    targets: list[LearningVersionTargetContract] = []
    for proposal in proposals:
        context = dict(proposal.strategy_context)
        review = dict(context.get("evolution_review", {}))
        if proposal.proposal_type == "skill_candidate":
            skill = dict(context.get("skill_candidate", {}))
            skill_id = str(skill.get("skill_id") or "")
            version_ref = str(skill.get("skill_candidate_id") or "")
            if not skill_id or not version_ref:
                continue
            targets.append(
                _target(
                    capability_kind="skill",
                    capability_id=skill_id,
                    version_ref=version_ref,
                    lifecycle_status="candidate_inactive",
                    review_status=str(review.get("review_status") or "needs_review"),
                    runtime_status="inactive_candidate",
                    evidence_refs=[
                        str(proposal.evolution_proposal_id),
                        *proposal.baseline_refs,
                        *proposal.source_signals,
                    ],
                    rollback_plan_ref=_optional_text(
                        skill.get("rollback_plan_ref")
                        or review.get("rollback_plan_ref")
                    ),
                    rollback_status=rollback_status.get(
                        str(proposal.evolution_proposal_id),
                        "not_observed",
                    ),
                    observed_at=proposal.timestamp,
                )
            )
        elif proposal.proposal_type == "workflow_candidate":
            workflow = dict(context.get("workflow_candidate", {}))
            workflow_profile = str(workflow.get("workflow_profile") or "")
            version_ref = str(workflow.get("workflow_version_id") or "")
            baseline_ref = _optional_text(workflow.get("baseline_version_ref"))
            if not workflow_profile or not version_ref:
                continue
            if baseline_ref:
                targets.append(
                    _target(
                        capability_kind="workflow",
                        capability_id=workflow_profile,
                        version_ref=baseline_ref,
                        lifecycle_status="baseline_snapshot",
                        review_status="promoted_baseline",
                        runtime_status="active_baseline",
                        evidence_refs=[baseline_ref, *proposal.baseline_refs],
                        rollback_plan_ref=None,
                        rollback_status="not_observed",
                        observed_at=proposal.timestamp,
                    )
                )
            targets.append(
                _target(
                    capability_kind="workflow",
                    capability_id=workflow_profile,
                    version_ref=version_ref,
                    lifecycle_status="candidate_inactive",
                    review_status=str(review.get("review_status") or "needs_review"),
                    runtime_status="inactive_candidate",
                    evidence_refs=[
                        str(proposal.evolution_proposal_id),
                        *proposal.baseline_refs,
                        *proposal.source_signals,
                    ],
                    rollback_plan_ref=_optional_text(
                        workflow.get("rollback_plan_ref")
                        or review.get("rollback_plan_ref")
                    ),
                    rollback_status=rollback_status.get(
                        str(proposal.evolution_proposal_id),
                        "not_observed",
                    ),
                    observed_at=proposal.timestamp,
                    baseline_version_ref=baseline_ref,
                )
            )
    return targets


def _guidance_targets(
    guidance_records: list[object],
    decisions: list[EvolutionDecisionContract],
    generated_at: str,
) -> list[LearningVersionTargetContract]:
    rollback_status = _rollback_status_by_proposal(decisions)
    targets: list[LearningVersionTargetContract] = []
    baseline_workflows: set[str] = set()
    for record in guidance_records:
        guidance = record.guidance
        baseline_ref = _reviewed_memory_baseline_ref(guidance.workflow_profile)
        if guidance.workflow_profile not in baseline_workflows:
            baseline_workflows.add(guidance.workflow_profile)
            targets.append(
                _target(
                    capability_kind="reviewed_memory",
                    capability_id=guidance.workflow_profile,
                    version_ref=baseline_ref,
                    lifecycle_status="baseline_without_reviewed_guidance",
                    review_status="baseline",
                    runtime_status="active_baseline",
                    evidence_refs=[
                        f"workflow://profile/{guidance.workflow_profile}",
                        "memory-policy://baseline/no-reviewed-learning",
                    ],
                    rollback_plan_ref=None,
                    rollback_status="not_observed",
                    observed_at=generated_at,
                )
            )
        targets.append(
            _target(
                capability_kind="reviewed_memory",
                capability_id=guidance.workflow_profile,
                version_ref=guidance.guidance_id,
                lifecycle_status="reviewed_guidance",
                review_status=guidance.review_status,
                runtime_status="active_reviewed_guidance",
                evidence_refs=[
                    guidance.source_review_decision_id,
                    str(guidance.evolution_proposal_id),
                    *guidance.evidence_refs,
                ],
                rollback_plan_ref=guidance.rollback_plan_ref,
                rollback_status=rollback_status.get(
                    str(guidance.evolution_proposal_id),
                    "not_observed",
                ),
                observed_at=guidance.timestamp,
                baseline_version_ref=baseline_ref,
            )
        )
    return targets


def _proposal_eval_observations(
    proposals: list[EvolutionProposalContract],
) -> list[LearningOutcomeObservationContract]:
    observations: list[LearningOutcomeObservationContract] = []
    for proposal in proposals:
        if proposal.proposal_type != "skill_candidate":
            continue
        context = dict(proposal.strategy_context)
        skill = dict(context.get("skill_candidate", {}))
        sandbox = dict(context.get("skill_sandbox_eval", {}))
        if not sandbox:
            continue
        skill_id = str(skill.get("skill_id") or sandbox.get("skill_id") or "")
        version_ref = str(
            skill.get("skill_candidate_id")
            or sandbox.get("skill_candidate_id")
            or ""
        )
        if not skill_id or not version_ref:
            continue
        blockers = [str(item) for item in sandbox.get("blockers", [])]
        pass_rate = float(sandbox.get("pass_rate") or 0.0)
        eval_id = str(sandbox.get("eval_id") or proposal.evolution_proposal_id)
        observations.append(
            LearningOutcomeObservationContract(
                observation_id=f"learning-observation://offline/{_digest(eval_id)}",
                capability_kind="skill",
                capability_id=skill_id,
                version_ref=version_ref,
                source_kind="offline_eval",
                observed_at=proposal.timestamp,
                success=str(sandbox.get("eval_status")) == "passed_pending_release_gate",
                success_score=pass_rate,
                rework_count=0,
                evidence_refs=[eval_id, str(proposal.evolution_proposal_id)],
                regression_flags=blockers,
                human_review_required=True,
                promotion_authorized=False,
                automatic_promotion_allowed=False,
                core_mutation_allowed=False,
            )
        )
    return observations


def _runtime_observations(
    *,
    observability_service: ObservabilityService,
    targets: list[LearningVersionTargetContract],
    limit: int,
) -> list[LearningOutcomeObservationContract]:
    guidance_targets = {
        target.version_ref: target
        for target in targets
        if target.capability_kind == "reviewed_memory"
        and not target.version_ref.startswith("baseline://")
    }
    baseline_by_workflow = {
        target.capability_id: target
        for target in targets
        if target.capability_kind == "reviewed_memory"
        and target.version_ref.startswith("baseline://")
    }
    if not guidance_targets:
        return []
    audits = observability_service.summarize_recent_requests(limit=limit)
    feedback_by_mission = {
        audit.mission_id: audit
        for audit in audits
        if audit.mission_id
        and audit.operator_feedback_assessment != "not_applicable"
    }
    observations: list[LearningOutcomeObservationContract] = []
    for audit in audits:
        version_targets = [
            guidance_targets[ref]
            for ref in audit.reviewed_learning_influence_refs
            if ref in guidance_targets
        ]
        if not version_targets and audit.workflow_profile in baseline_by_workflow:
            version_targets = [baseline_by_workflow[str(audit.workflow_profile)]]
        for target in version_targets:
            feedback = feedback_by_mission.get(audit.mission_id)
            assessment = (
                feedback.operator_feedback_assessment if feedback else None
            )
            regression_flags = [
                *audit.anomaly_flags,
                *(f"missing_event:{item}" for item in audit.missing_required_events),
            ]
            if assessment in {"not_helpful", "correction"}:
                regression_flags.append(f"operator_feedback:{assessment}")
            success = (
                audit.trace_complete
                and audit.governance_decision in {"allow", "allow_with_conditions"}
                and audit.operation_status not in {"failed", "blocked"}
            )
            observations.append(
                LearningOutcomeObservationContract(
                    observation_id=(
                        "learning-observation://runtime/"
                        f"{_digest(f'{target.version_ref}|{audit.request_id}')}"
                    ),
                    capability_kind=target.capability_kind,
                    capability_id=target.capability_id,
                    version_ref=target.version_ref,
                    source_kind="runtime_mission",
                    observed_at=_audit_timestamp(observability_service, audit),
                    success=success,
                    success_score=1.0 if success else 0.0,
                    rework_count=int(assessment in {"not_helpful", "correction"}),
                    evidence_refs=[
                        target.version_ref,
                        f"trace://{audit.request_id}",
                        *(feedback.operator_feedback_evidence_refs if feedback else []),
                    ],
                    mission_id=audit.mission_id,
                    request_id=audit.request_id,
                    workflow_profile=audit.workflow_profile,
                    route=audit.primary_route,
                    feedback_assessment=assessment,
                    feedback_rating=feedback.operator_feedback_rating if feedback else None,
                    regression_flags=sorted(set(regression_flags)),
                    # The target lifecycle records the rollback once. Runtime
                    # observations must not multiply that event per mission.
                    rollback_observed=False,
                    human_review_required=True,
                    promotion_authorized=False,
                    automatic_promotion_allowed=False,
                    core_mutation_allowed=False,
                )
            )
    return observations


def _audit_timestamp(service: ObservabilityService, audit: FlowAudit) -> str:
    events = service.list_recent_events(
        ObservabilityQuery(request_id=audit.request_id, limit=100)
    )
    return events[-1].timestamp if events else datetime.now(UTC).isoformat()


def _target(
    *,
    capability_kind: str,
    capability_id: str,
    version_ref: str,
    lifecycle_status: str,
    review_status: str,
    runtime_status: str,
    evidence_refs: list[str],
    rollback_plan_ref: str | None,
    rollback_status: str,
    observed_at: str,
    baseline_version_ref: str | None = None,
) -> LearningVersionTargetContract:
    identity = f"{capability_kind}|{capability_id}|{version_ref}"
    return LearningVersionTargetContract(
        target_id=f"learning-target://{capability_kind}/{_digest(identity)}",
        capability_kind=capability_kind,
        capability_id=capability_id,
        version_ref=version_ref,
        lifecycle_status=lifecycle_status,
        review_status=review_status,
        runtime_status=runtime_status,
        evidence_refs=list(dict.fromkeys(ref for ref in evidence_refs if ref))[:200],
        rollback_plan_ref=rollback_plan_ref,
        rollback_status=rollback_status,
        observed_at=observed_at,
        baseline_version_ref=baseline_version_ref,
        human_review_required=True,
        runtime_activation_allowed=False,
        promotion_authorized=False,
        automatic_promotion_allowed=False,
        core_mutation_allowed=False,
    )


def _dedupe_targets(
    targets: list[LearningVersionTargetContract],
) -> list[LearningVersionTargetContract]:
    deduped: dict[tuple[str, str, str], LearningVersionTargetContract] = {}
    for target in targets:
        key = (target.capability_kind, target.capability_id, target.version_ref)
        deduped.setdefault(key, target)
    return list(deduped.values())


def _rollback_status_by_proposal(
    decisions: list[EvolutionDecisionContract],
) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for decision in decisions:
        proposal_id = str(decision.evolution_proposal_id)
        if "rollback" in decision.decision:
            statuses[proposal_id] = "rolled_back"
        elif decision.rollback_plan_ref and proposal_id not in statuses:
            statuses[proposal_id] = "available"
    return statuses


def _reviewed_memory_baseline_ref(workflow_profile: str) -> str:
    return f"baseline://reviewed-memory/{_digest(workflow_profile)}"


def _optional_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()[:16]


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "-").replace("+", "_").replace("/", "-")


def main() -> int:
    parser = ArgumentParser(description="Build longitudinal learning evidence.")
    parser.add_argument("--observability-db")
    parser.add_argument("--memory-db")
    parser.add_argument("--evolution-db")
    parser.add_argument("--output-dir")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--minimum-observations", type=int, default=2)
    args = parser.parse_args()
    observability_db = Path(
        args.observability_db or ROOT / ".jarvis_runtime" / "observability.db"
    )
    memory_db = Path(args.memory_db or ROOT / ".jarvis_runtime" / "memory.db")
    evolution_db = Path(args.evolution_db or ROOT / ".jarvis_runtime" / "evolution.db")
    report = build_longitudinal_report(
        observability_service=ObservabilityService(database_path=str(observability_db)),
        memory_service=MemoryService(
            database_url=f"sqlite:///{memory_db.resolve().as_posix()}"
        ),
        evolution_service=EvolutionLabService(database_path=str(evolution_db.resolve())),
        limit=args.limit,
        minimum_observations=args.minimum_observations,
    )
    latest_path, _ = save_report(
        report,
        output_dir=Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_DIR,
    )
    print(latest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
