from dataclasses import replace
from inspect import signature

import pytest
from evolution_lab.service import EvolutionLabService

from shared.contracts import (
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalControlSnapshotContract,
    WorkflowVariantEvalObservationContract,
)
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    build_active_workflow_version_registry,
    register_workflow_candidate_version,
    route_metadata_payload,
    workflow_definition_hash,
)
from shared.workflow_variant_eval import (
    validate_workflow_variant_eval_case_pack,
    validate_workflow_variant_eval_case_result,
    validate_workflow_variant_eval_run,
    workflow_variant_eval_control_fingerprint,
)
from tools.workflow_release_gate import evaluate_workflow_release_gate
from tools.workflow_variant_eval import run_workflow_variant_eval


def _registry_with_candidate():  # type: ignore[no-untyped-def]
    registry = build_active_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T20:00:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    steps = [*baseline.workflow_steps, "record verified release evidence"]
    checkpoints = [*baseline.workflow_checkpoints, "release_evidence_recorded"]
    decision_points = [*baseline.workflow_decision_points, "release_evidence_gate"]
    success_criteria = [
        *baseline.success_criteria,
        "release evidence remains auditable",
    ]
    candidate = replace(
        baseline,
        workflow_version_id="workflow-version://software_change_workflow/1.1.0",
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=steps,
            workflow_checkpoints=checkpoints,
            workflow_decision_points=decision_points,
            success_criteria=success_criteria,
        ),
        workflow_steps=steps,
        workflow_checkpoints=checkpoints,
        workflow_decision_points=decision_points,
        success_criteria=success_criteria,
        evidence_refs=[
            *baseline.evidence_refs,
            "recurring-pattern://software-release",
            "review-decision://software-release/001",
            "evidence://workflow/software-release",
        ],
        proposed_tests=["test://workflow/software-release-variant"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="record release evidence before recommendation",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )
    return (
        baseline,
        candidate,
        register_workflow_candidate_version(
            registry,
            candidate,
        ),
    )


def _pack(
    baseline,
    candidate,
    *,
    candidate_status: str = "completed",
    candidate_rework: int = 0,
    candidate_checkpoints: list[str] | None = None,
):  # type: ignore[no-untyped-def]
    control = WorkflowVariantEvalControlSnapshotContract(
        control_snapshot_id="workflow-eval-control://software-release/1",
        workflow_policy_ref="workflow-policy://software-change/1",
        workflow_policy_version="1.0.0",
        workflow_policy_source_registry_ref=baseline.source_registry_ref,
        workflow_policy_source_registry_fingerprint=(baseline.source_registry_fingerprint),
        governance_policy_ref="governance-policy://core/1",
        governance_policy_version="1.0.0",
        input_fingerprint="a" * 64,
        memory_policy_refs=["memory-policy://influence/1"],
        memory_policy_version_refs={"memory-policy://influence/1": "1.0.0"},
        memory_input_fingerprint="b" * 64,
        evaluator_version="1.0.0",
        deterministic_seed=206,
        fixed_clock="2026-07-16T20:10:00Z",
    )
    control_fingerprint = workflow_variant_eval_control_fingerprint(control)

    def observation(
        arm: str,
        version,
        *,
        outcome_status: str,
        rework_count: int,
        checkpoints: list[str],
        participating: list[str],
        declared: list[str],
    ) -> WorkflowVariantEvalObservationContract:
        return WorkflowVariantEvalObservationContract(
            observation_id=f"workflow-eval-observation://software-release/{arm}",
            case_id="software_release_evidence",
            case_version="1.0.0",
            arm=arm,
            workflow_version_ref=version.workflow_version_id,
            definition_hash=version.definition_hash,
            input_snapshot_fingerprint="a" * 64,
            control_snapshot_id=control.control_snapshot_id,
            control_snapshot_fingerprint=control_fingerprint,
            outcome_ref=f"outcome://workflow-eval/software-release/{arm}",
            outcome_status=outcome_status,
            contract_checks={
                "route": True,
                "governance": True,
                "response_contract": True,
                "evidence": arm == "candidate",
            },
            action_count=2,
            rework_count=rework_count,
            expected_workflow_steps=list(version.workflow_steps),
            expected_checkpoint_refs=list(version.workflow_checkpoints),
            expected_decision_points=list(version.workflow_decision_points),
            expected_success_criteria=list(version.success_criteria),
            observed_checkpoint_refs=checkpoints,
            memory_participating_refs=participating,
            memory_declared_causal_refs=declared,
            evidence_refs=[
                f"evidence://workflow-eval/software-release/{arm}",
                f"outcome-evidence://workflow-eval/software-release/{arm}",
            ],
            limitations=[],
            observed_at="2026-07-16T20:10:00Z",
        )

    baseline_observation = observation(
        "baseline",
        baseline,
        outcome_status="completed",
        rework_count=1,
        checkpoints=list(baseline.workflow_checkpoints[:-1]),
        participating=["memory://release-guidance", "memory://release-risk"],
        declared=["memory://release-guidance"],
    )
    candidate_observation = observation(
        "candidate",
        candidate,
        outcome_status=candidate_status,
        rework_count=candidate_rework,
        checkpoints=(
            list(candidate.workflow_checkpoints)
            if candidate_checkpoints is None
            else candidate_checkpoints
        ),
        participating=["memory://release-guidance", "memory://release-risk"],
        declared=["memory://release-guidance", "memory://release-risk"],
    )
    case = WorkflowVariantEvalCaseContract(
        case_pack_id="workflow-eval-pack://software-release",
        case_pack_version="1.0.0",
        case_id="software_release_evidence",
        case_version="1.0.0",
        scenario_ref="scenario://workflow/software-release/equivalent-1",
        input_snapshot_fingerprint="a" * 64,
        workflow_profile=candidate.workflow_profile,
        route=candidate.route,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        required_candidate_steps=["record verified release evidence"],
        required_candidate_checkpoints=["release_evidence_recorded"],
        required_candidate_decision_points=["release_evidence_gate"],
        required_candidate_success_criteria=["release evidence remains auditable"],
        contract_check_refs=["route", "governance", "response_contract", "evidence"],
        control_snapshot=control,
        baseline_observation=baseline_observation,
        candidate_observation=candidate_observation,
        evidence_refs=[
            baseline_observation.evidence_refs[0],
            candidate_observation.evidence_refs[0],
        ],
    )
    return WorkflowVariantEvalCasePackContract(
        case_pack_id=case.case_pack_id,
        case_pack_version=case.case_pack_version,
        workflow_profile=case.workflow_profile,
        route=case.route,
        baseline_version_ref=case.baseline_version_ref,
        candidate_version_ref=case.candidate_version_ref,
        scope_refs=["scope://workflow/software-release"],
        cases=[case],
        evidence_refs=[
            "evidence://workflow-eval/software-release/pack",
            "evidence://workflow-eval/software-release/control",
        ],
        generated_at="2026-07-16T20:10:00Z",
    )


def _with_second_case_version(
    pack: WorkflowVariantEvalCasePackContract,
) -> WorkflowVariantEvalCasePackContract:
    first = pack.cases[0]
    second = replace(
        first,
        case_version="1.1.0",
        scenario_ref="scenario://workflow/software-release/equivalent-2",
        baseline_observation=replace(
            first.baseline_observation,
            observation_id=(
                "workflow-eval-observation://software-release/baseline/1.1.0"
            ),
            case_version="1.1.0",
            outcome_ref="outcome://workflow-eval/software-release/baseline/1.1.0",
            evidence_refs=[
                "evidence://workflow-eval/software-release/baseline/1.1.0",
                "outcome-evidence://workflow-eval/software-release/baseline/1.1.0",
            ],
        ),
        candidate_observation=replace(
            first.candidate_observation,
            observation_id=(
                "workflow-eval-observation://software-release/candidate/1.1.0"
            ),
            case_version="1.1.0",
            outcome_ref="outcome://workflow-eval/software-release/candidate/1.1.0",
            evidence_refs=[
                "evidence://workflow-eval/software-release/candidate/1.1.0",
                "outcome-evidence://workflow-eval/software-release/candidate/1.1.0",
            ],
        ),
        evidence_refs=[
            "evidence://workflow-eval/software-release/case/1.1.0",
            "evidence://workflow-eval/software-release/control/1.1.0",
        ],
    )
    return replace(pack, cases=[first, second])


def _run(tmp_path, *, pack=None, run_id="workflow-variant-eval://run/1"):  # type: ignore[no-untyped-def]
    baseline, candidate, registry = _registry_with_candidate()
    resolved_pack = pack or _pack(baseline, candidate)
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    run = run_workflow_variant_eval(
        service=service,
        registry=registry,
        case_pack=resolved_pack,
        run_id=run_id,
        generated_at="2026-07-16T20:20:00Z",
    )
    return baseline, candidate, registry, service, resolved_pack, run


def test_metric_only_legacy_case_contract_no_longer_exists() -> None:
    parameters = signature(WorkflowVariantEvalCaseContract).parameters

    assert "baseline_metrics" not in parameters
    assert "candidate_metrics" not in parameters
    assert "control_snapshot" in parameters
    assert "baseline_observation" in parameters
    assert "candidate_observation" in parameters


def test_controlled_eval_derives_metrics_persists_and_retries(tmp_path) -> None:
    active_before = {route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY}
    baseline, candidate, registry, service, pack, run = _run(tmp_path)
    replay = run_workflow_variant_eval(
        service=service,
        registry=registry,
        case_pack=pack,
        run_id=run.run_id,
        generated_at=run.generated_at,
    )

    assert run.status == "passed"
    assert run.comparison_conclusion == "candidate_improved_without_regression"
    assert run.case_pack_version == "1.0.0"
    assert run.aggregate_candidate_metrics["success_score"] == 1.0
    assert run.aggregate_candidate_metrics["contract_adherence"] == 1.0
    assert run.aggregate_candidate_metrics["rework_rate"] == 0.0
    assert run.aggregate_candidate_metrics["checkpoint_coverage"] == 1.0
    assert run.aggregate_candidate_metrics["memory_causality"] == 1.0
    assert run.aggregate_metric_deltas["rework_rate"] == -0.5
    assert replay == run == service.get_workflow_variant_eval_run(run.run_id)
    assert len(service.list_workflow_variant_eval_runs()) == 1
    assert run.execution_allowed is False
    assert run.tool_dispatch_allowed is False
    assert run.runtime_activation_allowed is False
    assert run.release_authorized is False
    assert run.promotion_authorized is False
    assert run.automatic_promotion_allowed is False
    assert run.core_mutation_allowed is False
    assert candidate.runtime_activation_allowed is False
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before


def test_runner_accepts_two_versions_of_the_same_case_id(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    pack = _with_second_case_version(_pack(baseline, candidate))
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    run = run_workflow_variant_eval(
        service=service,
        registry=registry,
        case_pack=pack,
        run_id="workflow-variant-eval://versioned-case-identities",
        generated_at="2026-07-16T20:20:00Z",
    )

    assert run.status == "passed"
    assert run.total_cases == 2
    assert [(result.case_id, result.case_version) for result in run.case_results] == [
        (case.case_id, case.case_version) for case in pack.cases
    ]


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        (
            lambda pack: replace(
                pack,
                cases=[
                    replace(
                        pack.cases[0],
                        candidate_observation=replace(
                            pack.cases[0].candidate_observation,
                            input_snapshot_fingerprint="c" * 64,
                        ),
                    )
                ],
            ),
            "input",
        ),
        (
            lambda pack: replace(
                pack,
                cases=[
                    replace(
                        pack.cases[0],
                        candidate_observation=replace(
                            pack.cases[0].candidate_observation,
                            control_snapshot_fingerprint="d" * 64,
                        ),
                    )
                ],
            ),
            "control",
        ),
    ],
)
def test_control_mismatch_fails_closed(
    tmp_path,
    mutation,
    expected_fragment,
) -> None:  # type: ignore[no-untyped-def]
    baseline, candidate, registry = _registry_with_candidate()
    pack = mutation(_pack(baseline, candidate))
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    with pytest.raises(ValueError, match=expected_fragment):
        run_workflow_variant_eval(
            service=service,
            registry=registry,
            case_pack=pack,
            run_id="workflow-variant-eval://invalid/control",
            generated_at="2026-07-16T20:20:00Z",
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("workflow_policy_ref", "workflow-policy://different/1"),
        ("governance_policy_ref", "governance-policy://different/1"),
        ("memory_input_fingerprint", "c" * 64),
    ],
)
def test_policy_governance_or_memory_control_drift_fails_closed(
    tmp_path,
    field_name,
    value,
) -> None:  # type: ignore[no-untyped-def]
    baseline, candidate, registry = _registry_with_candidate()
    pack = _pack(baseline, candidate)
    case = pack.cases[0]
    alternative_control = replace(
        case.control_snapshot,
        **{field_name: value},
    )
    candidate_observation = replace(
        case.candidate_observation,
        control_snapshot_fingerprint=workflow_variant_eval_control_fingerprint(alternative_control),
    )
    drifted = replace(
        pack,
        cases=[replace(case, candidate_observation=candidate_observation)],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    with pytest.raises(ValueError, match="control"):
        run_workflow_variant_eval(
            service=service,
            registry=registry,
            case_pack=drifted,
            run_id=f"workflow-variant-eval://invalid/{field_name}",
            generated_at="2026-07-16T20:20:00Z",
        )


def test_limitations_are_recorded_and_fail_the_run(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    pack = _pack(baseline, candidate)
    pack = replace(
        pack,
        cases=[replace(pack.cases[0], limitations=["unverified outcome"])],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    run = run_workflow_variant_eval(
        service=service,
        registry=registry,
        case_pack=pack,
        run_id="workflow-variant-eval://limitation/1",
        generated_at="2026-07-16T20:20:00Z",
    )

    assert run.status == "failed"
    assert run.case_results[0].limitations == ["unverified outcome"]
    assert run.limitations == ["case:software_release_evidence:unverified outcome"]
    assert service.get_workflow_variant_eval_run(run.run_id) == run


def test_definition_hash_is_recomputed_before_comparison(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    stale = replace(candidate, workflow_steps=[*candidate.workflow_steps, "tampered"])
    stale_registry = replace(
        registry,
        versions=[
            stale if item.workflow_version_id == candidate.workflow_version_id else item
            for item in registry.versions
        ],
    )
    pack = _pack(baseline, stale)
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    with pytest.raises(
        ValueError,
        match="observation definition snapshot fingerprint mismatch",
    ):
        run_workflow_variant_eval(
            service=service,
            registry=stale_registry,
            case_pack=pack,
            run_id="workflow-variant-eval://stale/hash",
            generated_at="2026-07-16T20:20:00Z",
        )


@pytest.mark.parametrize("arm", ["baseline", "candidate"])
def test_definition_snapshot_must_match_registered_version(
    tmp_path,
    arm: str,
) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    pack = _pack(baseline, candidate)
    case = pack.cases[0]
    observation = getattr(case, f"{arm}_observation")
    forged_success_criteria = [
        *observation.expected_success_criteria,
        f"forged {arm} criterion",
    ]
    forged_observation = replace(
        observation,
        definition_hash=workflow_definition_hash(
            workflow_steps=observation.expected_workflow_steps,
            workflow_checkpoints=observation.expected_checkpoint_refs,
            workflow_decision_points=observation.expected_decision_points,
            success_criteria=forged_success_criteria,
        ),
        expected_success_criteria=forged_success_criteria,
    )
    forged_pack = replace(
        pack,
        cases=[replace(case, **{f"{arm}_observation": forged_observation})],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    assert validate_workflow_variant_eval_case_pack(forged_pack) == []
    with pytest.raises(ValueError, match="definition"):
        run_workflow_variant_eval(
            service=service,
            registry=registry,
            case_pack=forged_pack,
            run_id=f"workflow-variant-eval://forged/{arm}-definition",
            generated_at="2026-07-16T20:20:00Z",
        )


def test_case_pack_scope_must_match_registered_pair(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    pack = _pack(baseline, candidate)
    forged_scope = replace(
        pack,
        workflow_profile="forged_workflow",
        route="forged_route",
        cases=[
            replace(
                pack.cases[0],
                workflow_profile="forged_workflow",
                route="forged_route",
            )
        ],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    assert validate_workflow_variant_eval_case_pack(forged_scope) == []
    with pytest.raises(ValueError, match="scope"):
        run_workflow_variant_eval(
            service=service,
            registry=registry,
            case_pack=forged_scope,
            run_id="workflow-variant-eval://forged/scope",
            generated_at="2026-07-16T20:20:00Z",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"lifecycle_status": "active"},
        {"runtime_binding_status": "active_candidate"},
        {"review_status": "approved"},
        {"human_review_required": False},
        {"sandbox_required": False},
        {"blockers": ["unsafe candidate"]},
        {"evidence_refs": []},
        {"proposed_tests": []},
        {"rollback_plan_ref": ""},
        {"source_registry_ref": "domain-registry://forged"},
        {"source_registry_fingerprint": "f" * 64},
        {"active_registry_write_allowed": True},
    ],
)
def test_registered_candidate_must_remain_safe(
    tmp_path,
    changes: dict[str, object],
) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    unsafe_candidate = replace(candidate, **changes)
    unsafe_registry = replace(
        registry,
        versions=[
            unsafe_candidate
            if version.workflow_version_id == candidate.workflow_version_id
            else version
            for version in registry.versions
        ],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    with pytest.raises(ValueError):
        run_workflow_variant_eval(
            service=service,
            registry=unsafe_registry,
            case_pack=_pack(baseline, candidate),
            run_id="workflow-variant-eval://unsafe/candidate",
            generated_at="2026-07-16T20:20:00Z",
        )


@pytest.mark.parametrize(
    "evidence_prefix",
    ["recurring-pattern://", "review-decision://"],
)
def test_registered_candidate_requires_reviewed_pattern_evidence(
    tmp_path,
    evidence_prefix: str,
) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    unsafe_candidate = replace(
        candidate,
        evidence_refs=[
            reference
            for reference in candidate.evidence_refs
            if not reference.startswith(evidence_prefix)
        ],
    )
    unsafe_registry = replace(
        registry,
        versions=[
            unsafe_candidate
            if version.workflow_version_id == candidate.workflow_version_id
            else version
            for version in registry.versions
        ],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))

    with pytest.raises(ValueError, match="evidence"):
        run_workflow_variant_eval(
            service=service,
            registry=unsafe_registry,
            case_pack=_pack(baseline, candidate),
            run_id=f"workflow-variant-eval://unsafe/{evidence_prefix.split(':')[0]}",
            generated_at="2026-07-16T20:20:00Z",
        )


def test_regression_is_derived_from_observations(tmp_path) -> None:
    baseline, candidate, registry = _registry_with_candidate()
    pack = _pack(
        baseline,
        candidate,
        candidate_status="failed",
        candidate_rework=2,
        candidate_checkpoints=[],
    )
    service = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    run = run_workflow_variant_eval(
        service=service,
        registry=registry,
        case_pack=pack,
        run_id="workflow-variant-eval://regression/1",
        generated_at="2026-07-16T20:20:00Z",
    )

    assert run.status == "failed"
    assert run.comparison_conclusion == "candidate_regression_detected"
    assert any("success_score_regressed" in item for item in run.regression_flags)
    assert any("checkpoint_coverage_regressed" in item for item in run.regression_flags)
    assert any("rework_rate_regressed" in item for item in run.regression_flags)


def test_run_id_collision_is_rejected(tmp_path) -> None:
    baseline, candidate, registry, service, pack, run = _run(tmp_path)
    changed = replace(
        pack,
        evidence_refs=[*pack.evidence_refs, "evidence://different-pack-payload"],
    )
    with pytest.raises(ValueError, match="collision"):
        run_workflow_variant_eval(
            service=service,
            registry=registry,
            case_pack=changed,
            run_id=run.run_id,
            generated_at=run.generated_at,
        )


def test_workflow_release_gate_consumes_only_controlled_eval(tmp_path) -> None:
    baseline, candidate, _registry, service, _pack_value, workflow_eval = _run(tmp_path)
    proposal = service.create_proposal_from_workflow_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-release-reviewer",
        evidence_refs=["evidence://workflow/software-release/release-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    rollback_plan = service.build_workflow_rollback_plan(
        baseline=baseline,
        candidate=candidate,
        trigger_conditions=["controlled evaluation regression"],
        verification_tests=["test://workflow/software-release-rollback"],
        evidence_refs=["evidence://workflow/software-release/rollback"],
        operator_ref="operator://workflow-release-reviewer",
        generated_at="2026-07-16T20:21:00Z",
    )
    release = evaluate_workflow_release_gate(
        service=service,
        proposal=proposal,
        review_decision=review,
        candidate=candidate,
        workflow_eval=workflow_eval,
        rollback_plan=rollback_plan,
        completed_external_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )

    assert release.gate_decision.gate_status == "passed"
    assert release.gate_decision.promotion_eligible is True
    assert release.gate_decision.promotion_authorized is False


def test_result_checks_require_source_and_cannot_be_spoofed(tmp_path) -> None:
    baseline, candidate, _registry, service, pack, run = _run(tmp_path)
    canonical_result = run.case_results[0]
    forged_result = replace(
        canonical_result,
        checks={"spoofed": True},
        failures=[],
    )
    forged_run = replace(
        run,
        run_id="workflow-variant-eval://spoofed/checks",
        case_results=[forged_result],
    )

    assert validate_workflow_variant_eval_case_result(canonical_result) == [
        "workflow_eval_source_case_required"
    ]
    assert validate_workflow_variant_eval_run(run) == [
        "workflow_eval_source_case_pack_required"
    ]
    assert "case_result_checks_not_derived" in (
        validate_workflow_variant_eval_case_result(
            forged_result,
            case=pack.cases[0],
        )
    )
    assert validate_workflow_variant_eval_run(
        forged_run,
        case_pack=pack,
    )
    assert service.claim_workflow_variant_eval_run(
        run_id=forged_run.run_id,
        input_fingerprint=service.workflow_variant_eval_input_fingerprint(pack),
        baseline_version_ref=baseline.workflow_version_id,
        baseline_definition_hash=baseline.definition_hash,
        candidate_version_ref=candidate.workflow_version_id,
        candidate_definition_hash=candidate.definition_hash,
        case_pack_id=pack.case_pack_id,
        case_pack_version=pack.case_pack_version,
        case_pack_fingerprint=run.case_pack_fingerprint,
        control_fingerprint=service.workflow_variant_eval_control_fingerprint(pack),
        claimed_at=run.generated_at,
    ) is True
    with pytest.raises(ValueError, match="invalid workflow variant evaluation run"):
        service.record_workflow_variant_eval_run(forged_run)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda pack: _replace_case_control(pack, input_fingerprint="c" * 64),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    required_candidate_checkpoints=["checkpoint-not-in-definition"],
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    required_candidate_steps=["step-not-in-definition"],
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    required_candidate_steps=[
                        pack.cases[0].baseline_observation.expected_workflow_steps[0]
                    ],
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    required_candidate_decision_points=[
                        "decision-not-in-definition"
                    ],
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    required_candidate_success_criteria=[
                        "criterion-not-in-definition"
                    ],
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    candidate_observation=replace(
                        pack.cases[0].candidate_observation,
                        contract_checks={"different-check": True},
                    ),
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    candidate_observation=replace(
                        pack.cases[0].candidate_observation,
                        outcome_ref=pack.cases[0].baseline_observation.outcome_ref,
                    ),
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    candidate_observation=replace(
                        pack.cases[0].candidate_observation,
                        expected_workflow_steps=["tampered-definition"],
                    ),
                )
            ],
        ),
        lambda pack: replace(
            pack,
            cases=[
                replace(
                    pack.cases[0],
                    candidate_observation=replace(
                        pack.cases[0].candidate_observation,
                        observed_at="2026-07-16T20:10:01Z",
                    ),
                )
            ],
        ),
    ],
)
def test_case_pack_binds_control_definition_outcomes_and_fixed_clock(
    mutation,
) -> None:  # type: ignore[no-untyped-def]
    baseline, candidate, _registry = _registry_with_candidate()
    pack = mutation(_pack(baseline, candidate))

    assert validate_workflow_variant_eval_case_pack(pack)


def test_every_eval_layer_rejects_authority_claims(tmp_path) -> None:
    _baseline, _candidate, _registry, _service, pack, run = _run(tmp_path)
    case = pack.cases[0]
    control_unsafe = _replace_case_control(pack, execution_allowed=True)
    observation_unsafe = replace(
        pack,
        cases=[
            replace(
                case,
                candidate_observation=replace(
                    case.candidate_observation,
                    tool_dispatch_allowed=True,
                ),
            )
        ],
    )
    case_unsafe = replace(
        pack,
        cases=[replace(case, runtime_activation_allowed=True)],
    )
    pack_unsafe = replace(pack, release_authorized=True)

    for unsafe in (control_unsafe, observation_unsafe, case_unsafe, pack_unsafe):
        assert validate_workflow_variant_eval_case_pack(unsafe)
    assert validate_workflow_variant_eval_case_result(
        replace(run.case_results[0], promotion_authorized=True),
        case=case,
    )
    assert validate_workflow_variant_eval_run(
        replace(run, core_mutation_allowed=True),
        case_pack=pack,
    )


def _replace_case_control(
    pack: WorkflowVariantEvalCasePackContract,
    **changes: object,
) -> WorkflowVariantEvalCasePackContract:
    case = pack.cases[0]
    control = replace(case.control_snapshot, **changes)
    fingerprint = workflow_variant_eval_control_fingerprint(control)
    return replace(
        pack,
        cases=[
            replace(
                case,
                control_snapshot=control,
                baseline_observation=replace(
                    case.baseline_observation,
                    control_snapshot_fingerprint=fingerprint,
                ),
                candidate_observation=replace(
                    case.candidate_observation,
                    control_snapshot_fingerprint=fingerprint,
                ),
            )
        ],
    )
