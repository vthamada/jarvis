from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict, fields, replace
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps

import pytest

from shared.contracts import (
    TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
    TechnologyExperimentCaseContract,
    TechnologyExperimentControlSnapshotContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentObservationContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
)
from shared.schemas import (
    TECHNOLOGY_EXPERIMENT_CASE_RESULT_SCHEMA,
    TECHNOLOGY_EXPERIMENT_CASE_SCHEMA,
    TECHNOLOGY_EXPERIMENT_CONTROL_SNAPSHOT_SCHEMA,
    TECHNOLOGY_EXPERIMENT_EVAL_RUN_CLAIM_SCHEMA,
    TECHNOLOGY_EXPERIMENT_EVAL_RUN_SCHEMA,
    TECHNOLOGY_EXPERIMENT_OBSERVATION_SCHEMA,
    TECHNOLOGY_EXPERIMENT_PACK_SCHEMA,
)
from shared.technology_experiment import (
    canonical_technology_experiment_payload,
    derive_technology_experiment_case_result,
    derive_technology_experiment_eval_run,
    technology_experiment_artifact_fingerprint,
    technology_experiment_control_fingerprint,
    technology_experiment_pack_control_fingerprint,
    technology_experiment_pack_fingerprint,
    technology_experiment_pack_input_fingerprint,
    technology_experiment_text_fingerprint,
    validate_technology_experiment_case,
    validate_technology_experiment_case_result,
    validate_technology_experiment_control_snapshot,
    validate_technology_experiment_eval_run,
    validate_technology_experiment_eval_run_claim,
    validate_technology_experiment_observation,
    validate_technology_experiment_pack,
    validate_technology_experiment_pack_shape,
)
from shared.technology_radar_intake import (
    technology_radar_intake_fingerprint,
    technology_radar_review_subject_fingerprint,
)


def _intake(**overrides: object) -> TechnologyRadarIntakeContract:
    values: dict[str, object] = {
        "intake_id": "technology-intake://typed-handoffs/1.0.0",
        "candidate_ref": "technology-candidate://typed-handoffs",
        "intake_version": "1.0.0",
        "technology_name": "Typed Handoffs",
        "source_kind": "repository",
        "source_locator": "https://example.com/typed-handoffs",
        "source_version_ref": "commit://typed-handoffs/0123456789abcdef",
        "source_content_sha256": "a" * 64,
        "license_id": "MIT",
        "license_status": "declared",
        "license_evidence_ref": "license-evidence://typed-handoffs/mit",
        "retrieved_at": "2026-08-12T00:00:00Z",
        "claims": ["Typed handoffs can make delegation boundaries explicit."],
        "risks": ["A full framework import could weaken Core sovereignty."],
        "absorption_class": "sandbox_experiment",
        "target_gap_refs": ["KNW-006"],
        "research_approval_ref": "approval://technology-radar/typed-handoffs",
        "reviewed_payload_fingerprint": "0" * 64,
        "reviewer_ref": "operator://technology-radar/reviewer-1",
        "review_status": "approved_for_radar_intake",
        "review_evidence_refs": ["evidence://technology/review/typed-handoffs"],
        "reviewed_at": "2026-08-12T00:01:00Z",
        "recorded_at": "2026-08-12T00:02:00Z",
    }
    values.update(overrides)
    draft = TechnologyRadarIntakeContract(**values)  # type: ignore[arg-type]
    if "reviewed_payload_fingerprint" not in overrides:
        draft = replace(
            draft,
            reviewed_payload_fingerprint=(
                technology_radar_review_subject_fingerprint(draft)
            ),
        )
    return draft


def _control(**overrides: object) -> TechnologyExperimentControlSnapshotContract:
    values: dict[str, object] = {
        "control_snapshot_id": "technology-experiment-control://typed-handoffs/case-1",
        "input_fingerprint": "1" * 64,
        "sandbox_policy_ref": "technology-sandbox-policy://offline-attestation/v1",
        "sandbox_policy_version": "1.0.0",
        "evaluator_version": "1.0.0",
        "deterministic_seed": 208209,
        "fixed_clock": "2026-08-12T00:03:00Z",
        "isolation_profile_ref": TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        "isolation_fingerprint": "2" * 64,
        "environment_fingerprint": "3" * 64,
    }
    values.update(overrides)
    return TechnologyExperimentControlSnapshotContract(**values)  # type: ignore[arg-type]


def _observation(
    arm: str,
    *,
    control: TechnologyExperimentControlSnapshotContract,
    success: bool,
    action_count: int,
    rework_count: int,
    **overrides: object,
) -> TechnologyExperimentObservationContract:
    baseline = arm == "baseline"
    values: dict[str, object] = {
        "observation_id": f"technology-experiment-observation://typed-handoffs/{arm}",
        "experiment_pack_id": "technology-experiment-pack://typed-handoffs/1.0.0",
        "pack_version": "1.0.0",
        "case_id": "technology-experiment-case://typed-handoffs/case-1",
        "case_version": "1.0.0",
        "arm": arm,
        "definition_ref": (
            "jarvis-baseline://typed-handoffs/v1"
            if baseline
            else "jarvis-experiment-definition://typed-handoffs/pattern-v1"
        ),
        "definition_hash": "4" * 64 if baseline else "5" * 64,
        "input_fingerprint": control.input_fingerprint,
        "control_snapshot_id": control.control_snapshot_id,
        "control_snapshot_fingerprint": technology_experiment_control_fingerprint(
            control
        ),
        "outcome_ref": f"technology-experiment-outcome://typed-handoffs/{arm}",
        "outcome_status": "completed",
        "contract_checks": {"sovereign_consumer_preserved": True},
        "isolation_checks": {
            "dependencies_unchanged": True,
            "external_code_not_executed": True,
            "host_filesystem_unchanged": True,
            "network_disabled": True,
        },
        "success_criteria_results": {"boundary_is_explicit": success},
        "action_count": action_count,
        "rework_count": rework_count,
        "evidence_refs": [f"evidence://technology-experiment/{arm}"],
        "limitations": [],
        "observed_at": control.fixed_clock,
    }
    values.update(overrides)
    return TechnologyExperimentObservationContract(**values)  # type: ignore[arg-type]


def _case(
    *,
    control: TechnologyExperimentControlSnapshotContract | None = None,
    baseline_success: bool = False,
    candidate_success: bool = True,
    baseline_rework: int = 2,
    candidate_rework: int = 0,
    **overrides: object,
) -> TechnologyExperimentCaseContract:
    resolved_control = control or _control()
    baseline = _observation(
        "baseline",
        control=resolved_control,
        success=baseline_success,
        action_count=4,
        rework_count=baseline_rework,
    )
    candidate = _observation(
        "candidate",
        control=resolved_control,
        success=candidate_success,
        action_count=4,
        rework_count=candidate_rework,
    )
    values: dict[str, object] = {
        "experiment_pack_id": "technology-experiment-pack://typed-handoffs/1.0.0",
        "pack_version": "1.0.0",
        "case_id": "technology-experiment-case://typed-handoffs/case-1",
        "case_version": "1.0.0",
        "scenario_ref": "technology-experiment-scenario://typed-handoffs/bounded-delegation",
        "input_fingerprint": resolved_control.input_fingerprint,
        "baseline_definition_ref": baseline.definition_ref,
        "baseline_definition_hash": baseline.definition_hash,
        "candidate_definition_ref": candidate.definition_ref,
        "candidate_definition_hash": candidate.definition_hash,
        "critical_contract_check_refs": ["sovereign_consumer_preserved"],
        "critical_isolation_check_refs": [
            "dependencies_unchanged",
            "external_code_not_executed",
            "host_filesystem_unchanged",
            "network_disabled",
        ],
        "success_criteria_refs": ["boundary_is_explicit"],
        "control_snapshot": resolved_control,
        "baseline_observation": baseline,
        "candidate_observation": candidate,
        "evidence_refs": ["evidence://technology-experiment/paired-case"],
    }
    values.update(overrides)
    return TechnologyExperimentCaseContract(**values)  # type: ignore[arg-type]


def _pack(
    *,
    intake: TechnologyRadarIntakeContract | None = None,
    case: TechnologyExperimentCaseContract | None = None,
    **overrides: object,
) -> TechnologyExperimentPackContract:
    source = intake or _intake()
    resolved_case = case or _case()
    values: dict[str, object] = {
        "experiment_pack_id": resolved_case.experiment_pack_id,
        "pack_version": resolved_case.pack_version,
        "intake_id": source.intake_id,
        "intake_version": source.intake_version,
        "intake_fingerprint": technology_radar_intake_fingerprint(source),
        "reviewed_payload_fingerprint": technology_radar_review_subject_fingerprint(
            source
        ),
        "candidate_ref": source.candidate_ref,
        "technology_name": source.technology_name,
        "source_content_sha256": source.source_content_sha256,
        "absorption_class": source.absorption_class,
        "translation_kind": "absorbable_pattern",
        "pattern_id": "technology-pattern://typed-handoffs/explicit-boundary",
        "pattern_name": "Explicit handoff boundary",
        "pattern_summary": "Translate explicit handoff typing into a bounded seam.",
        "selected_claim_fingerprints": [
            technology_experiment_text_fingerprint(source.claims[0])
        ],
        "selected_risk_fingerprints": [
            technology_experiment_text_fingerprint(source.risks[0])
        ],
        "hypothesis": "A typed boundary reduces rework without moving authority.",
        "expected_gain": "Fewer ambiguous delegation repairs in the same workflow.",
        "sovereign_consumer_kind": "jarvis_component",
        "sovereign_consumer_ref": "jarvis-component://planning-engine",
        "consumer_contract_ref": "jarvis-contract://deliberative-plan/v1",
        "bounded_integration_seam": "jarvis-seam://planning/handoff-description",
        "target_gap_refs": list(source.target_gap_refs),
        "baseline_definition_ref": resolved_case.baseline_definition_ref,
        "baseline_definition_hash": resolved_case.baseline_definition_hash,
        "candidate_definition_ref": resolved_case.candidate_definition_ref,
        "candidate_definition_hash": resolved_case.candidate_definition_hash,
        "isolation_profile_ref": TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        "risk_control_refs": ["technology-risk-control://core-sovereignty"],
        "mitigation_refs": ["technology-mitigation://discard-inert-pack"],
        "stop_condition_refs": ["technology-stop-condition://any-regression"],
        "license_id": source.license_id,
        "license_status": source.license_status,
        "license_evidence_ref": source.license_evidence_ref,
        "rollback_plan_ref": "technology-experiment-rollback://typed-handoffs/v1",
        "rollback_steps": [
            "Discard the inert sandbox evidence and retain the baseline definition."
        ],
        "rollback_verification_refs": [
            "technology-rollback-verification://baseline-unchanged"
        ],
        "selection_review_ref": (
            "technology-experiment-selection-review://typed-handoffs/approved"
        ),
        "selected_by_ref": "operator://technology-experiment/reviewer-1",
        "cases": [resolved_case],
        "required_pass_rate": 1.0,
        "evidence_refs": ["evidence://technology-experiment/pack-source"],
        "generated_at": "2026-08-12T00:04:00Z",
    }
    values.update(overrides)
    return TechnologyExperimentPackContract(**values)  # type: ignore[arg-type]


def test_valid_pack_binds_verified_intake_and_is_frozen_zero_authority() -> None:
    intake = _intake()
    pack = _pack(intake=intake)

    assert validate_technology_experiment_pack(pack, intake=intake) == []
    assert pack.sandbox_only is True
    assert pack.read_only is True
    assert pack.immutable is True
    assert pack.human_review_required is True
    assert pack.network_fetch_allowed is False
    assert pack.subprocess_allowed is False
    assert pack.dependency_installation_allowed is False
    assert pack.external_code_execution_allowed is False
    assert pack.tool_dispatch_allowed is False
    assert pack.evolution_proposal_allowed is False
    assert pack.runtime_activation_allowed is False
    assert pack.promotion_authorized is False
    assert pack.automatic_promotion_allowed is False
    assert pack.core_mutation_allowed is False
    assert pack.priority_mutation_allowed is False
    assert not {
        "command",
        "code",
        "dependencies",
        "allowed_tools",
        "tool_name",
    }.intersection(field.name for field in fields(pack))
    with pytest.raises(FrozenInstanceError):
        pack.pack_status = "active"  # type: ignore[misc]


def test_payload_and_fingerprint_are_canonical_and_cover_nested_evidence() -> None:
    pack = _pack()
    expected = dumps(
        asdict(pack),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    assert canonical_technology_experiment_payload(pack) == expected
    assert technology_experiment_pack_fingerprint(pack) == sha256(
        expected.encode("utf-8")
    ).hexdigest()
    changed = replace(pack, hypothesis="A materially different hypothesis.")
    assert technology_experiment_artifact_fingerprint(changed) != (
        technology_experiment_artifact_fingerprint(pack)
    )


@pytest.mark.parametrize(
    ("pack_change", "expected"),
    [
        ({"translation_kind": "framework_substitution"}, "framework substitution"),
        ({"sovereign_consumer_ref": "jarvis-component://core"}, "not allowlisted"),
        ({"requested_core_role": "orchestrator"}, "cannot request a sovereign Core role"),
        ({"external_framework_role": "primary_brain"}, "must remain subordinate"),
        ({"dependency_installation_allowed": True}, "must be false"),
        ({"evolution_proposal_allowed": True}, "must be false"),
    ],
)
def test_pack_shape_blocks_substitution_unsafe_consumers_and_authority(
    pack_change: dict[str, object],
    expected: str,
) -> None:
    blockers = validate_technology_experiment_pack_shape(
        replace(_pack(), **pack_change)
    )

    assert any(expected in blocker for blocker in blockers)


def test_reference_class_and_unknown_license_cannot_be_sandboxed() -> None:
    reference = _intake(absorption_class="reference")
    reference_pack = _pack(intake=reference)
    unresolved = _intake(
        license_id="NOASSERTION",
        license_status="unknown_requires_review",
    )
    unresolved_pack = _pack(intake=unresolved)

    assert "experiment intake class is not sandbox eligible" in (
        validate_technology_experiment_pack(reference_pack, intake=reference)
    )
    unresolved_blockers = validate_technology_experiment_pack(
        unresolved_pack,
        intake=unresolved,
    )
    assert "experiment requires a declared license" in unresolved_blockers
    assert "experiment license must be resolved before sandboxing" in (
        unresolved_blockers
    )


def test_pack_fails_closed_on_source_binding_or_selected_evidence_drift() -> None:
    intake = _intake()
    pack = _pack(intake=intake)

    assert "experiment pack does not match the verified intake" in (
        validate_technology_experiment_pack(
            replace(pack, source_content_sha256="f" * 64),
            intake=intake,
        )
    )
    assert "experiment selected claims must come from the verified intake" in (
        validate_technology_experiment_pack(
            replace(pack, selected_claim_fingerprints=["e" * 64]),
            intake=intake,
        )
    )
    assert "experiment selected risks must come from the verified intake" in (
        validate_technology_experiment_pack(
            replace(pack, selected_risk_fingerprints=["d" * 64]),
            intake=intake,
        )
    )


def test_control_observation_and_case_require_identical_inert_boundaries() -> None:
    control = _control()
    case = _case(control=control)

    assert validate_technology_experiment_control_snapshot(control) == []
    assert validate_technology_experiment_observation(case.baseline_observation) == []
    assert validate_technology_experiment_observation(case.candidate_observation) == []
    assert validate_technology_experiment_case(case) == []

    unsafe_control = replace(control, network_fetch_allowed=True)
    assert "network_fetch_allowed must be false" in (
        validate_technology_experiment_control_snapshot(unsafe_control)
    )
    mismatched_candidate = replace(
        case.candidate_observation,
        input_fingerprint="9" * 64,
    )
    paired_blockers = validate_technology_experiment_case(
        replace(case, candidate_observation=mismatched_candidate)
    )
    assert "case candidate observation binding mismatch" in paired_blockers


def test_case_result_and_passing_run_are_derived_without_promotion_authority() -> None:
    intake = _intake()
    pack = _pack(intake=intake)
    case = pack.cases[0]

    result = derive_technology_experiment_case_result(case, pack=pack)
    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/run-1",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    assert result.passed is True
    assert result.metric_deltas["success_score"] == 1.0
    assert result.metric_deltas["rework_rate"] == 0.5
    assert result.regression_flags == []
    assert validate_technology_experiment_case_result(
        result,
        case=case,
        pack=pack,
    ) == []
    assert run.status == "passed_sandbox_only"
    assert run.readiness_status == "eligible_for_human_experiment_review"
    assert run.promotion_readiness == "not_applicable"
    assert run.pass_rate == 1.0
    assert run.promotion_authorized is False
    assert run.automatic_promotion_allowed is False
    assert run.core_mutation_allowed is False
    assert validate_technology_experiment_eval_run(
        run,
        pack=pack,
        intake=intake,
    ) == []

    forged_result = replace(result, passed=False)
    assert validate_technology_experiment_case_result(
        forged_result,
        case=case,
        pack=pack,
    ) == ["technology experiment case result must be derived"]
    forged_run = replace(run, status="passed")
    assert validate_technology_experiment_eval_run(
        forged_run,
        pack=pack,
        intake=intake,
    ) == [
        "technology experiment eval run must be derived"
    ]


def test_regression_and_limitations_block_the_derived_run() -> None:
    intake = _intake()
    regressed_candidate = _observation(
        "candidate",
        control=_control(),
        success=False,
        action_count=4,
        rework_count=4,
        limitations=["The candidate attestation is incomplete."],
    )
    case = _case(
        baseline_success=True,
        baseline_rework=0,
        candidate_observation=regressed_candidate,
    )
    pack = _pack(intake=intake, case=case)

    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/regression",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    assert run.status == "blocked"
    assert run.readiness_status == "blocked"
    assert run.promotion_readiness == "not_applicable"
    assert "regression_detected" in run.blockers
    assert "limitations_present" in run.blockers
    assert run.case_results[0].passed is False


def test_failed_candidate_outcome_is_preserved_and_blocks_readiness() -> None:
    intake = _intake()
    case = _case()
    failed_candidate = replace(case.candidate_observation, outcome_status="failed")
    case = replace(case, candidate_observation=failed_candidate)
    pack = _pack(intake=intake, case=case)

    assert validate_technology_experiment_pack(pack, intake=intake) == []
    result = derive_technology_experiment_case_result(case, pack=pack)
    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/failed-candidate",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    assert result.baseline_outcome_status == "completed"
    assert result.candidate_outcome_status == "failed"
    assert result.candidate_metrics["success_score"] == 0.0
    assert result.passed is False
    assert "candidate_outcome_completed" in result.failures
    assert run.status == "blocked"
    assert run.readiness_status == "blocked"


def test_baseline_must_preserve_sovereignty_and_isolation() -> None:
    intake = _intake()
    case = _case()
    invalid_baseline = replace(
        case.baseline_observation,
        contract_checks={"sovereign_consumer_preserved": False},
        isolation_checks={
            name: False for name in case.critical_isolation_check_refs
        },
    )
    case = replace(case, baseline_observation=invalid_baseline)
    pack = _pack(intake=intake, case=case)

    result = derive_technology_experiment_case_result(case, pack=pack)
    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/invalid-baseline",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    assert result.passed is False
    assert "baseline_contract_checks_passed" in result.failures
    assert "baseline_isolation_checks_passed" in result.failures
    assert run.status == "blocked"


def test_required_pass_rate_cannot_absorb_unsafe_case_evidence() -> None:
    intake = _intake()
    safe_case = _case()
    second_control = _control(
        control_snapshot_id="technology-experiment-control://typed-handoffs/case-2",
        input_fingerprint="7" * 64,
    )
    second = _case(control=second_control)
    case_id = "technology-experiment-case://typed-handoffs/case-2"
    unsafe_baseline = replace(
        second.baseline_observation,
        observation_id=(
            "technology-experiment-observation://typed-handoffs/case-2/baseline"
        ),
        case_id=case_id,
        outcome_ref=(
            "technology-experiment-outcome://typed-handoffs/case-2/baseline"
        ),
        contract_checks={"sovereign_consumer_preserved": False},
        isolation_checks={name: False for name in second.critical_isolation_check_refs},
    )
    second_candidate = replace(
        second.candidate_observation,
        observation_id=(
            "technology-experiment-observation://typed-handoffs/case-2/candidate"
        ),
        case_id=case_id,
        outcome_ref=(
            "technology-experiment-outcome://typed-handoffs/case-2/candidate"
        ),
    )
    unsafe_case = replace(
        second,
        case_id=case_id,
        baseline_observation=unsafe_baseline,
        candidate_observation=second_candidate,
    )
    pack = _pack(
        intake=intake,
        case=safe_case,
        cases=[safe_case, unsafe_case],
        required_pass_rate=0.5,
    )

    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/mixed-safety",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    assert run.pass_rate == 0.5
    assert run.status == "blocked"
    assert run.readiness_status == "blocked"
    assert "invalid_or_unsafe_case_evidence" in run.blockers


def test_pack_preserves_mb208_compatible_percent_encoded_evidence_refs() -> None:
    intake = _intake(
        license_evidence_ref="license-evidence://typed-handoffs/mit%2Freview"
    )
    pack = _pack(intake=intake)

    assert validate_technology_experiment_pack(pack, intake=intake) == []


def test_run_derivation_requires_the_exact_fully_valid_intake_bound_pack() -> None:
    intake = _intake()
    pack = _pack(intake=intake)

    with pytest.raises(ValueError, match="requires a verified pack"):
        derive_technology_experiment_eval_run(
            run_id="technology-experiment-run://typed-handoffs/unsafe-pack",
            pack=replace(
                pack,
                translation_kind="framework_substitution",
                dependency_installation_allowed=True,
                promotion_authorized=True,
            ),
            intake=intake,
            generated_at="2026-08-12T00:05:00Z",
        )

    spoofed_intake = _intake(
        intake_id="technology-intake://spoofed-source/1.0.0",
        candidate_ref="technology-candidate://spoofed-source",
        technology_name="Spoofed source",
        source_content_sha256="9" * 64,
        research_approval_ref="approval://technology-radar/spoofed-source",
        reviewer_ref="operator://technology-radar/reviewer-2",
        review_evidence_refs=["evidence://technology/review/spoofed-source"],
    )
    spoofed_pack = _pack(intake=spoofed_intake)
    with pytest.raises(ValueError, match="requires a verified pack"):
        derive_technology_experiment_eval_run(
            run_id="technology-experiment-run://typed-handoffs/spoofed-intake",
            pack=spoofed_pack,
            intake=intake,
            generated_at="2026-08-12T00:05:00Z",
        )


def test_experiment_chronology_and_reference_identity_are_fail_closed() -> None:
    intake = _intake()
    stale_case = _case(control=_control(fixed_clock="2020-01-01T00:00:00Z"))
    stale_pack = _pack(intake=intake, case=stale_case)
    assert "experiment evidence cannot predate the verified intake" in (
        validate_technology_experiment_pack(stale_pack, intake=intake)
    )

    future_case = _case(control=_control(fixed_clock="2099-01-01T00:00:00Z"))
    future_pack = _pack(
        intake=intake,
        case=future_case,
        generated_at="2099-01-01T00:01:00Z",
    )
    future_blockers = validate_technology_experiment_pack(
        future_pack,
        intake=intake,
        now=datetime(2026, 8, 12, tzinfo=UTC),
    )
    assert "experiment generated timestamp cannot be in the future" in future_blockers

    alias = replace(
        _pack(intake=intake),
        experiment_pack_id="technology-experiment-pack://typed-%68andoffs/1.0.0",
    )
    assert "technology-experiment-pack ref is not canonical" in (
        validate_technology_experiment_pack_shape(alias)
    )


def test_run_claim_binds_pack_source_input_and_control_fingerprints() -> None:
    pack = _pack()
    claim = TechnologyExperimentEvalRunClaimContract(
        run_id="technology-experiment-run://typed-handoffs/run-1",
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=technology_experiment_pack_fingerprint(pack),
        intake_id=pack.intake_id,
        intake_fingerprint=pack.intake_fingerprint,
        input_fingerprint=technology_experiment_pack_input_fingerprint(pack),
        control_fingerprint=technology_experiment_pack_control_fingerprint(pack),
        claimed_at="2026-08-12T00:05:00Z",
    )

    assert validate_technology_experiment_eval_run_claim(claim, pack=pack) == []
    assert "technology experiment claim binding mismatch" in (
        validate_technology_experiment_eval_run_claim(
            replace(claim, pack_fingerprint="f" * 64),
            pack=pack,
        )
    )


def test_all_seven_schema_definitions_match_their_frozen_contracts() -> None:
    instances = (
        (TECHNOLOGY_EXPERIMENT_CONTROL_SNAPSHOT_SCHEMA, _control()),
        (
            TECHNOLOGY_EXPERIMENT_OBSERVATION_SCHEMA,
            _case().baseline_observation,
        ),
        (TECHNOLOGY_EXPERIMENT_CASE_SCHEMA, _case()),
        (TECHNOLOGY_EXPERIMENT_PACK_SCHEMA, _pack()),
    )
    intake = _intake()
    pack = _pack(intake=intake)
    result = derive_technology_experiment_case_result(pack.cases[0], pack=pack)
    claim = TechnologyExperimentEvalRunClaimContract(
        run_id="technology-experiment-run://typed-handoffs/schema",
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=technology_experiment_pack_fingerprint(pack),
        intake_id=pack.intake_id,
        intake_fingerprint=pack.intake_fingerprint,
        input_fingerprint=technology_experiment_pack_input_fingerprint(pack),
        control_fingerprint=technology_experiment_pack_control_fingerprint(pack),
        claimed_at="2026-08-12T00:05:00Z",
    )
    run = derive_technology_experiment_eval_run(
        run_id="technology-experiment-run://typed-handoffs/schema",
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T00:05:00Z",
    )

    for schema, instance in (
        *instances,
        (TECHNOLOGY_EXPERIMENT_CASE_RESULT_SCHEMA, result),
        (TECHNOLOGY_EXPERIMENT_EVAL_RUN_CLAIM_SCHEMA, claim),
        (TECHNOLOGY_EXPERIMENT_EVAL_RUN_SCHEMA, run),
    ):
        assert schema.contract_name == type(instance).__name__
        assert set(schema.required_fields + schema.optional_fields) == {
            field.name for field in fields(instance)
        }
