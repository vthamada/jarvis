"""Canonical validation and fingerprints for controlled workflow variant evals."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from hashlib import sha256
from json import dumps
from math import isclose
from typing import Any

from shared.contracts import (
    WORKFLOW_VARIANT_EVAL_COMPARISON_MODE,
    WORKFLOW_VARIANT_EVAL_METRICS_SOURCE,
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalCaseResultContract,
    WorkflowVariantEvalControlSnapshotContract,
    WorkflowVariantEvalObservationContract,
    WorkflowVariantEvalRunContract,
)
from shared.domain_registry import workflow_definition_hash
from shared.versioning import parse_canonical_semver

WORKFLOW_VARIANT_EVAL_METRICS = (
    "success_score",
    "contract_adherence",
    "rework_rate",
    "checkpoint_coverage",
    "memory_causality",
)
WORKFLOW_VARIANT_HIGHER_IS_BETTER = frozenset(
    {
        "success_score",
        "contract_adherence",
        "checkpoint_coverage",
        "memory_causality",
    }
)
_SAFE_OUTCOME_STATUSES = frozenset({"blocked", "completed", "failed", "governed"})
_AUTHORITY_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "release_authorized",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
)


def canonical_workflow_variant_eval_payload(value: object) -> str:
    """Serialize one eval artifact deterministically for append-only storage."""

    payload: Any = asdict(value) if is_dataclass(value) else value
    return dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def workflow_variant_eval_fingerprint(value: object) -> str:
    """Return a stable SHA-256 fingerprint of a complete eval artifact."""

    payload = canonical_workflow_variant_eval_payload(value)
    return sha256(payload.encode("utf-8")).hexdigest()


workflow_variant_control_snapshot_fingerprint = workflow_variant_eval_fingerprint
workflow_variant_eval_control_fingerprint = workflow_variant_eval_fingerprint
workflow_variant_case_fingerprint = workflow_variant_eval_fingerprint
workflow_variant_case_pack_fingerprint = workflow_variant_eval_fingerprint
workflow_variant_eval_case_pack_fingerprint = workflow_variant_eval_fingerprint
workflow_variant_eval_run_fingerprint = workflow_variant_eval_fingerprint


def derive_workflow_variant_eval_metrics(
    observation: WorkflowVariantEvalObservationContract,
    *,
    checkpoint_refs: list[str] | None = None,
) -> dict[str, float]:
    """Derive fixed metrics from one raw sandbox observation."""

    _validate_workflow_variant_eval_observation_or_raise(observation)
    checkpoints = _canonical_text_list(
        checkpoint_refs
        if checkpoint_refs is not None
        else observation.expected_checkpoint_refs,
        field_name="workflow_checkpoints",
        minimum=1,
        maximum=100,
    )
    if checkpoints != observation.expected_checkpoint_refs:
        raise ValueError(
            "observation expected checkpoints must match the workflow definition"
        )
    contract_total = len(observation.contract_checks)
    contract_passed = sum(value is True for value in observation.contract_checks.values())
    observed_checkpoints = set(observation.observed_checkpoint_refs)
    participating = set(observation.memory_participating_refs)
    declared = set(observation.memory_declared_causal_refs)
    return {
        "success_score": 1.0 if observation.outcome_status == "completed" else 0.0,
        "contract_adherence": round(contract_passed / contract_total, 4),
        "rework_rate": round(observation.rework_count / observation.action_count, 4),
        "checkpoint_coverage": round(
            len(observed_checkpoints.intersection(checkpoints)) / len(checkpoints),
            4,
        ),
        "memory_causality": round(
            len(declared.intersection(participating)) / len(participating),
            4,
        )
        if participating
        else 0.0,
    }


def derive_workflow_variant_eval_metric_deltas(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
) -> dict[str, float]:
    """Derive candidate-minus-baseline deltas for the fixed metric set."""

    _validate_metrics(baseline_metrics, field_name="baseline_metrics")
    _validate_metrics(candidate_metrics, field_name="candidate_metrics")
    return {
        metric: round(candidate_metrics[metric] - baseline_metrics[metric], 4)
        for metric in WORKFLOW_VARIANT_EVAL_METRICS
    }


def workflow_variant_eval_metric_signals(
    metric_deltas: dict[str, float],
) -> tuple[list[str], list[str]]:
    """Return canonical improvement and regression signals."""

    _validate_deltas(metric_deltas)
    improvements: list[str] = []
    regressions: list[str] = []
    for metric in WORKFLOW_VARIANT_EVAL_METRICS:
        delta = metric_deltas[metric]
        higher_is_better = metric in WORKFLOW_VARIANT_HIGHER_IS_BETTER
        if (delta > 0 and higher_is_better) or (delta < 0 and not higher_is_better):
            improvements.append(f"{metric}_improved")
        if (delta < 0 and higher_is_better) or (delta > 0 and not higher_is_better):
            regressions.append(f"{metric}_regressed")
    return improvements, regressions


def derive_workflow_variant_eval_case_checks(
    case: WorkflowVariantEvalCaseContract,
    *,
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
    limitations: list[str] | None = None,
) -> dict[str, bool]:
    """Derive the one canonical check set accepted in stored case results."""

    _validate_metrics(baseline_metrics, field_name="baseline_metrics")
    _validate_metrics(candidate_metrics, field_name="candidate_metrics")
    deltas = derive_workflow_variant_eval_metric_deltas(
        baseline_metrics,
        candidate_metrics,
    )
    improvements, regressions = workflow_variant_eval_metric_signals(deltas)
    control_fingerprint = workflow_variant_eval_control_fingerprint(
        case.control_snapshot
    )
    resolved_limitations = [
        *case.limitations,
        *case.baseline_observation.limitations,
        *case.candidate_observation.limitations,
        *(limitations or []),
    ]
    return {
        "paired_input_matches": (
            case.control_snapshot.input_fingerprint
            == case.input_snapshot_fingerprint
            == case.baseline_observation.input_snapshot_fingerprint
            == case.candidate_observation.input_snapshot_fingerprint
        ),
        "paired_control_matches": (
            case.baseline_observation.control_snapshot_id
            == case.control_snapshot.control_snapshot_id
            == case.candidate_observation.control_snapshot_id
            and case.baseline_observation.control_snapshot_fingerprint
            == control_fingerprint
            == case.candidate_observation.control_snapshot_fingerprint
        ),
        "exactly_two_arms": (
            case.baseline_observation.arm == "baseline"
            and case.candidate_observation.arm == "candidate"
            and case.baseline_observation.observation_id
            != case.candidate_observation.observation_id
        ),
        "outcome_evidence_bound": (
            bool(case.baseline_observation.outcome_ref)
            and bool(case.candidate_observation.outcome_ref)
            and len(case.baseline_observation.evidence_refs) >= 2
            and len(case.candidate_observation.evidence_refs) >= 2
        ),
        "limitations_absent": not resolved_limitations,
        "no_metric_regression": not regressions,
        "measurable_improvement": bool(improvements),
    }


def _validate_workflow_variant_eval_control_snapshot_or_raise(
    snapshot: WorkflowVariantEvalControlSnapshotContract,
) -> None:
    """Fail closed when a shared policy/governance/memory control is incomplete."""

    for field_name in (
        "control_snapshot_id",
        "workflow_policy_ref",
        "workflow_policy_version",
        "workflow_policy_source_registry_ref",
        "workflow_policy_source_registry_fingerprint",
        "governance_policy_ref",
        "governance_policy_version",
        "input_fingerprint",
        "memory_input_fingerprint",
        "evaluator_version",
        "fixed_clock",
    ):
        _require_text(getattr(snapshot, field_name), field_name=field_name)
    for version_field in (
        "workflow_policy_version",
        "governance_policy_version",
        "evaluator_version",
    ):
        if parse_canonical_semver(getattr(snapshot, version_field)) is None:
            raise ValueError(f"{version_field} must be canonical semver")
    _require_sha256_like(
        snapshot.workflow_policy_source_registry_fingerprint,
        field_name="workflow_policy_source_registry_fingerprint",
    )
    _require_sha256_like(snapshot.input_fingerprint, field_name="input_fingerprint")
    _require_sha256_like(
        snapshot.memory_input_fingerprint,
        field_name="memory_input_fingerprint",
    )
    memory_policy_refs = _canonical_text_list(
        snapshot.memory_policy_refs,
        field_name="memory_policy_refs",
        minimum=1,
        maximum=20,
    )
    if not isinstance(snapshot.memory_policy_version_refs, dict):
        raise ValueError("memory_policy_version_refs must be a canonical mapping")
    if set(snapshot.memory_policy_version_refs) != set(memory_policy_refs):
        raise ValueError("memory policy refs and version refs must match exactly")
    for ref, version in snapshot.memory_policy_version_refs.items():
        _require_text(ref, field_name="memory_policy_version_ref key")
        if parse_canonical_semver(version) is None:
            raise ValueError("memory policy versions must be canonical semver")
    if isinstance(snapshot.deterministic_seed, bool) or not isinstance(
        snapshot.deterministic_seed, int
    ):
        raise ValueError("deterministic_seed must be an integer")
    if snapshot.deterministic_seed < 0 or snapshot.deterministic_seed > 2**31 - 1:
        raise ValueError("deterministic_seed must remain bounded")
    _require_timestamp(snapshot.fixed_clock, field_name="fixed_clock")
    _validate_safe_authority(snapshot)


def _validate_workflow_variant_eval_observation_or_raise(
    observation: WorkflowVariantEvalObservationContract,
) -> None:
    """Validate a raw baseline/candidate observation before deriving metrics."""

    for field_name in (
        "observation_id",
        "case_id",
        "case_version",
        "arm",
        "workflow_version_ref",
        "definition_hash",
        "input_snapshot_fingerprint",
        "control_snapshot_id",
        "control_snapshot_fingerprint",
        "outcome_ref",
        "outcome_status",
        "observed_at",
    ):
        _require_text(getattr(observation, field_name), field_name=field_name)
    if parse_canonical_semver(observation.case_version) is None:
        raise ValueError("case_version must be canonical semver")
    if observation.arm not in {"baseline", "candidate"}:
        raise ValueError("workflow eval arm must be baseline or candidate")
    for field_name in (
        "definition_hash",
        "input_snapshot_fingerprint",
        "control_snapshot_fingerprint",
    ):
        _require_sha256_like(getattr(observation, field_name), field_name=field_name)
    if observation.outcome_status not in _SAFE_OUTCOME_STATUSES:
        raise ValueError("workflow eval outcome_status is not canonical")
    if (
        not isinstance(observation.contract_checks, dict)
        or not observation.contract_checks
        or len(observation.contract_checks) > 50
    ):
        raise ValueError("contract_checks must be a bounded non-empty mapping")
    for name, passed in observation.contract_checks.items():
        _require_text(name, field_name="contract check name")
        if passed is not True and passed is not False:
            raise ValueError("contract check values must be strict booleans")
    for field_name in ("action_count", "rework_count"):
        value = getattr(observation, field_name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{field_name} must be a non-negative integer")
    if observation.action_count < 1 or observation.action_count > 10_000:
        raise ValueError("action_count must remain bounded and non-zero")
    if observation.rework_count > observation.action_count:
        raise ValueError("rework_count cannot exceed action_count")
    expected_steps = _canonical_text_list(
        observation.expected_workflow_steps,
        field_name="expected_workflow_steps",
        minimum=1,
        maximum=100,
    )
    expected_checkpoints = _canonical_text_list(
        observation.expected_checkpoint_refs,
        field_name="expected_checkpoint_refs",
        minimum=1,
        maximum=100,
    )
    expected_decision_points = _canonical_text_list(
        observation.expected_decision_points,
        field_name="expected_decision_points",
        minimum=0,
        maximum=100,
    )
    expected_success_criteria = _canonical_text_list(
        observation.expected_success_criteria,
        field_name="expected_success_criteria",
        minimum=1,
        maximum=100,
    )
    if observation.definition_hash != workflow_definition_hash(
        workflow_steps=expected_steps,
        workflow_checkpoints=expected_checkpoints,
        workflow_decision_points=expected_decision_points,
        success_criteria=expected_success_criteria,
    ):
        raise ValueError("observation definition snapshot fingerprint mismatch")
    observed_checkpoints = _canonical_text_list(
        observation.observed_checkpoint_refs,
        field_name="observed_checkpoint_refs",
        minimum=0,
        maximum=100,
    )
    if not set(observed_checkpoints).issubset(expected_checkpoints):
        raise ValueError("observed checkpoints must belong to the expected definition")
    participating = _canonical_text_list(
        observation.memory_participating_refs,
        field_name="memory_participating_refs",
        minimum=0,
        maximum=50,
    )
    declared = _canonical_text_list(
        observation.memory_declared_causal_refs,
        field_name="memory_declared_causal_refs",
        minimum=0,
        maximum=50,
    )
    if not set(declared).issubset(participating):
        raise ValueError("declared causal memory refs must participate")
    _canonical_text_list(
        observation.evidence_refs,
        field_name="observation evidence_refs",
        minimum=2,
        maximum=50,
    )
    _canonical_text_list(
        observation.limitations,
        field_name="observation limitations",
        minimum=0,
        maximum=20,
    )
    _require_timestamp(observation.observed_at, field_name="observed_at")
    _validate_safe_authority(observation)


def _validate_workflow_variant_eval_case_or_raise(
    case: WorkflowVariantEvalCaseContract,
) -> None:
    """Validate one controlled pair and its common control snapshot."""

    for field_name in (
        "case_pack_id",
        "case_pack_version",
        "case_id",
        "case_version",
        "scenario_ref",
        "input_snapshot_fingerprint",
        "workflow_profile",
        "route",
        "baseline_version_ref",
        "candidate_version_ref",
    ):
        _require_text(getattr(case, field_name), field_name=field_name)
    for version_field in ("case_pack_version", "case_version"):
        if parse_canonical_semver(getattr(case, version_field)) is None:
            raise ValueError(f"{version_field} must be canonical semver")
    _require_sha256_like(
        case.input_snapshot_fingerprint,
        field_name="input_snapshot_fingerprint",
    )
    if case.control_snapshot.input_fingerprint != case.input_snapshot_fingerprint:
        raise ValueError("control snapshot and case input fingerprints must match")
    if case.baseline_version_ref == case.candidate_version_ref:
        raise ValueError("baseline and candidate workflow versions must differ")
    required_values = (
        *case.required_candidate_steps,
        *case.required_candidate_checkpoints,
        *case.required_candidate_decision_points,
        *case.required_candidate_success_criteria,
    )
    if not required_values:
        raise ValueError("candidate expectations must declare at least one delta")
    for field_name in (
        "required_candidate_steps",
        "required_candidate_checkpoints",
        "required_candidate_decision_points",
        "required_candidate_success_criteria",
    ):
        _canonical_text_list(
            getattr(case, field_name),
            field_name=field_name,
            minimum=0,
            maximum=50,
        )
    contract_check_refs = _canonical_text_list(
        case.contract_check_refs,
        field_name="contract_check_refs",
        minimum=1,
        maximum=50,
    )
    _canonical_text_list(
        case.evidence_refs,
        field_name="case evidence_refs",
        minimum=2,
        maximum=50,
    )
    _canonical_text_list(
        case.limitations,
        field_name="case limitations",
        minimum=0,
        maximum=20,
    )
    _validate_eval_modes(case)
    _validate_workflow_variant_eval_control_snapshot_or_raise(case.control_snapshot)
    control_fingerprint = workflow_variant_control_snapshot_fingerprint(
        case.control_snapshot
    )
    for expected_arm, observation, expected_version_ref in (
        ("baseline", case.baseline_observation, case.baseline_version_ref),
        ("candidate", case.candidate_observation, case.candidate_version_ref),
    ):
        _validate_workflow_variant_eval_observation_or_raise(observation)
        if observation.arm != expected_arm:
            raise ValueError("workflow eval observation arm mismatch")
        if observation.case_id != case.case_id or observation.case_version != case.case_version:
            raise ValueError("workflow eval observation case identity mismatch")
        if observation.workflow_version_ref != expected_version_ref:
            raise ValueError("workflow eval observation version mismatch")
        if observation.input_snapshot_fingerprint != case.input_snapshot_fingerprint:
            raise ValueError("workflow eval observations must use the same input snapshot")
        if (
            observation.control_snapshot_id != case.control_snapshot.control_snapshot_id
            or observation.control_snapshot_fingerprint != control_fingerprint
        ):
            raise ValueError("workflow eval observations must use the same control snapshot")
        if observation.observed_at != case.control_snapshot.fixed_clock:
            raise ValueError("workflow eval observations must use the fixed control clock")
        if set(observation.contract_checks) != set(contract_check_refs):
            raise ValueError(
                "workflow eval observations must use the case contract checks"
            )
    if case.baseline_observation.observation_id == case.candidate_observation.observation_id:
        raise ValueError("workflow eval observations require distinct identities")
    if case.baseline_observation.outcome_ref == case.candidate_observation.outcome_ref:
        raise ValueError("workflow eval observations require distinct outcome refs")
    if (
        case.baseline_observation.definition_hash
        == case.candidate_observation.definition_hash
    ):
        raise ValueError("workflow eval observations require distinct definitions")
    for required_values, baseline_values, candidate_values, label in (
        (
            case.required_candidate_steps,
            case.baseline_observation.expected_workflow_steps,
            case.candidate_observation.expected_workflow_steps,
            "steps",
        ),
        (
            case.required_candidate_checkpoints,
            case.baseline_observation.expected_checkpoint_refs,
            case.candidate_observation.expected_checkpoint_refs,
            "checkpoints",
        ),
        (
            case.required_candidate_decision_points,
            case.baseline_observation.expected_decision_points,
            case.candidate_observation.expected_decision_points,
            "decision points",
        ),
        (
            case.required_candidate_success_criteria,
            case.baseline_observation.expected_success_criteria,
            case.candidate_observation.expected_success_criteria,
            "success criteria",
        ),
    ):
        required_set = set(required_values)
        if not required_set.issubset(candidate_values):
            raise ValueError(
                f"required candidate {label} must belong to the expected definition"
            )
        if required_set.intersection(baseline_values):
            raise ValueError(f"required candidate {label} must be definition deltas")
    _validate_safe_authority(case)


def _validate_workflow_variant_eval_case_pack_or_raise(
    pack: WorkflowVariantEvalCasePackContract,
) -> None:
    """Validate a bounded immutable versioned case pack."""

    for field_name in (
        "case_pack_id",
        "case_pack_version",
        "workflow_profile",
        "route",
        "baseline_version_ref",
        "candidate_version_ref",
        "generated_at",
    ):
        _require_text(getattr(pack, field_name), field_name=field_name)
    if parse_canonical_semver(pack.case_pack_version) is None:
        raise ValueError("case_pack_version must be canonical semver")
    if pack.baseline_version_ref == pack.candidate_version_ref:
        raise ValueError("case pack baseline and candidate must differ")
    _canonical_text_list(
        pack.scope_refs,
        field_name="case pack scope_refs",
        minimum=1,
        maximum=20,
    )
    _canonical_text_list(
        pack.evidence_refs,
        field_name="case pack evidence_refs",
        minimum=2,
        maximum=100,
    )
    if not isinstance(pack.cases, list) or not 1 <= len(pack.cases) <= 32:
        raise ValueError("case pack must contain between one and 32 cases")
    identities: list[tuple[str, str]] = []
    scenarios: list[str] = []
    for case in pack.cases:
        _validate_workflow_variant_eval_case_or_raise(case)
        if (
            case.case_pack_id != pack.case_pack_id
            or case.case_pack_version != pack.case_pack_version
            or case.workflow_profile != pack.workflow_profile
            or case.route != pack.route
            or case.baseline_version_ref != pack.baseline_version_ref
            or case.candidate_version_ref != pack.candidate_version_ref
        ):
            raise ValueError("case pack scope and case scope must match exactly")
        identities.append((case.case_id, case.case_version))
        scenarios.append(case.scenario_ref)
    if len(identities) != len(set(identities)):
        raise ValueError("case pack contains duplicate case identities")
    if len(scenarios) != len(set(scenarios)):
        raise ValueError("case pack contains duplicate scenario refs")
    _require_timestamp(pack.generated_at, field_name="generated_at")
    _validate_eval_modes(pack)
    _validate_safe_authority(pack)


def _validate_workflow_variant_eval_case_result_or_raise(
    result: WorkflowVariantEvalCaseResultContract,
) -> None:
    """Recompute result truth so downstream aggregation cannot trust spoofed fields."""

    for field_name in (
        "case_pack_id",
        "case_pack_version",
        "case_pack_fingerprint",
        "case_id",
        "case_version",
        "scenario_ref",
        "input_snapshot_fingerprint",
        "workflow_profile",
        "route",
        "baseline_version_ref",
        "candidate_version_ref",
        "baseline_definition_hash",
        "candidate_definition_hash",
        "control_snapshot_id",
        "control_snapshot_fingerprint",
        "baseline_outcome_ref",
        "candidate_outcome_ref",
        "baseline_outcome_status",
        "candidate_outcome_status",
    ):
        _require_text(getattr(result, field_name), field_name=field_name)
    for version_field in ("case_pack_version", "case_version"):
        if parse_canonical_semver(getattr(result, version_field)) is None:
            raise ValueError(f"{version_field} must be canonical semver")
    for field_name in (
        "case_pack_fingerprint",
        "input_snapshot_fingerprint",
        "baseline_definition_hash",
        "candidate_definition_hash",
        "control_snapshot_fingerprint",
    ):
        _require_sha256_like(getattr(result, field_name), field_name=field_name)
    if result.baseline_version_ref == result.candidate_version_ref:
        raise ValueError("case result baseline and candidate must differ")
    if result.baseline_outcome_status not in _SAFE_OUTCOME_STATUSES or (
        result.candidate_outcome_status not in _SAFE_OUTCOME_STATUSES
    ):
        raise ValueError("case result outcome status is not canonical")
    if (
        not isinstance(result.checks, dict)
        or not result.checks
        or any(value is not True and value is not False for value in result.checks.values())
    ):
        raise ValueError("case result checks must be strict booleans")
    for name in result.checks:
        _require_text(name, field_name="case result check name")
    _validate_metrics(result.baseline_metrics, field_name="baseline_metrics")
    _validate_metrics(result.candidate_metrics, field_name="candidate_metrics")
    expected_deltas = derive_workflow_variant_eval_metric_deltas(
        result.baseline_metrics,
        result.candidate_metrics,
    )
    if not _float_mappings_equal(result.metric_deltas, expected_deltas):
        raise ValueError("case result metric_deltas do not match derived metrics")
    improvements, regressions = workflow_variant_eval_metric_signals(expected_deltas)
    if result.improvement_signals != improvements:
        raise ValueError("case result improvement signals are not canonical")
    if result.regression_flags != regressions:
        raise ValueError("case result regression flags are not canonical")
    expected_failures = [name for name, passed in result.checks.items() if not passed]
    if result.failures != expected_failures:
        raise ValueError("case result failures do not match checks")
    _canonical_text_list(
        result.limitations,
        field_name="case result limitations",
        minimum=0,
        maximum=50,
    )
    expected_passed = bool(improvements) and not (
        expected_failures or regressions or result.limitations
    )
    if result.passed is not expected_passed:
        raise ValueError("case result passed status is inconsistent")
    _canonical_text_list(
        result.evidence_refs,
        field_name="case result evidence_refs",
        minimum=2,
        maximum=100,
    )
    _validate_eval_modes(result)
    _validate_safe_authority(result)


def _validate_workflow_variant_eval_run_or_raise(
    run: WorkflowVariantEvalRunContract,
) -> None:
    """Recompute aggregate truth and reject any unsafe or inconsistent run."""

    for field_name in (
        "run_id",
        "case_pack_id",
        "case_pack_version",
        "case_pack_fingerprint",
        "workflow_profile",
        "route",
        "baseline_version_ref",
        "candidate_version_ref",
        "status",
        "readiness_status",
        "promotion_readiness",
        "comparison_conclusion",
        "generated_at",
    ):
        _require_text(getattr(run, field_name), field_name=field_name)
    if parse_canonical_semver(run.case_pack_version) is None:
        raise ValueError("run case_pack_version must be canonical semver")
    _require_sha256_like(run.case_pack_fingerprint, field_name="case_pack_fingerprint")
    if not isinstance(run.case_results, list) or not 1 <= len(run.case_results) <= 32:
        raise ValueError("workflow eval run requires bounded case results")
    identities: list[tuple[str, str]] = []
    for result in run.case_results:
        _validate_workflow_variant_eval_case_result_or_raise(result)
        if (
            result.case_pack_id != run.case_pack_id
            or result.case_pack_version != run.case_pack_version
            or result.case_pack_fingerprint != run.case_pack_fingerprint
            or result.workflow_profile != run.workflow_profile
            or result.route != run.route
            or result.baseline_version_ref != run.baseline_version_ref
            or result.candidate_version_ref != run.candidate_version_ref
        ):
            raise ValueError("workflow eval run and case result scope mismatch")
        identities.append((result.case_id, result.case_version))
    if len(identities) != len(set(identities)):
        raise ValueError("workflow eval run contains duplicate case results")
    total = len(run.case_results)
    passed = sum(result.passed for result in run.case_results)
    failed = total - passed
    if (run.total_cases, run.passed_cases, run.failed_cases) != (total, passed, failed):
        raise ValueError("workflow eval run case counts are inconsistent")
    expected_pass_rate = round(passed / total, 4)
    if not _float_equal(run.pass_rate, expected_pass_rate):
        raise ValueError("workflow eval run pass_rate is inconsistent")
    expected_baseline = _aggregate_metrics(run.case_results, "baseline_metrics")
    expected_candidate = _aggregate_metrics(run.case_results, "candidate_metrics")
    expected_deltas = derive_workflow_variant_eval_metric_deltas(
        expected_baseline,
        expected_candidate,
    )
    for field_name, actual, expected in (
        ("aggregate_baseline_metrics", run.aggregate_baseline_metrics, expected_baseline),
        ("aggregate_candidate_metrics", run.aggregate_candidate_metrics, expected_candidate),
        ("aggregate_metric_deltas", run.aggregate_metric_deltas, expected_deltas),
    ):
        if not _float_mappings_equal(actual, expected):
            raise ValueError(f"workflow eval run {field_name} is inconsistent")
    expected_regressions = list(
        dict.fromkeys(
            [
            f"case:{result.case_id}:{flag}"
            for result in run.case_results
            for flag in result.regression_flags
            ]
        )
    )
    if run.regression_flags != expected_regressions:
        raise ValueError("workflow eval run regression flags are inconsistent")
    _canonical_text_list(
        run.limitations,
        field_name="workflow eval run limitations",
        minimum=0,
        maximum=100,
    )
    _canonical_text_list(
        run.blockers,
        field_name="workflow eval run blockers",
        minimum=0,
        maximum=100,
    )
    expected_passed = passed == total and not (
        run.regression_flags or run.limitations or run.blockers
    )
    expected_values = (
        (
            "passed",
            "candidate_ready_for_human_gate_review",
            "manual_gate_only",
            "candidate_improved_without_regression",
        )
        if expected_passed
        else (
            "failed",
            "attention_required",
            "blocked",
            "candidate_regression_detected"
            if run.regression_flags
            else "insufficient_or_invalid_evidence",
        )
    )
    if (
        run.status,
        run.readiness_status,
        run.promotion_readiness,
        run.comparison_conclusion,
    ) != expected_values:
        raise ValueError("workflow eval run status projection is inconsistent")
    expected_lists = {
        "baseline_definition_hashes": [
            result.baseline_definition_hash for result in run.case_results
        ],
        "candidate_definition_hashes": [
            result.candidate_definition_hash for result in run.case_results
        ],
        "control_snapshot_ids": [
            result.control_snapshot_id for result in run.case_results
        ],
        "control_snapshot_fingerprints": [
            result.control_snapshot_fingerprint for result in run.case_results
        ],
        "baseline_outcome_refs": [
            result.baseline_outcome_ref for result in run.case_results
        ],
        "candidate_outcome_refs": [
            result.candidate_outcome_ref for result in run.case_results
        ],
    }
    for field_name, expected in expected_lists.items():
        if getattr(run, field_name) != expected:
            raise ValueError(f"workflow eval run {field_name} is inconsistent")
    _canonical_text_list(
        run.evidence_refs,
        field_name="workflow eval run evidence_refs",
        minimum=2,
        maximum=200,
    )
    _require_timestamp(run.generated_at, field_name="generated_at")
    _validate_eval_modes(run)
    _validate_safe_authority(run)


def validate_workflow_variant_eval_control_snapshot(
    snapshot: WorkflowVariantEvalControlSnapshotContract,
) -> list[str]:
    """Return bounded fail-closed validation blockers for one control snapshot."""

    return _validation_failures(
        lambda: _validate_workflow_variant_eval_control_snapshot_or_raise(snapshot)
    )


def validate_workflow_variant_eval_observation(
    observation: WorkflowVariantEvalObservationContract,
) -> list[str]:
    """Return bounded fail-closed validation blockers for one arm observation."""

    return _validation_failures(
        lambda: _validate_workflow_variant_eval_observation_or_raise(observation)
    )


def validate_workflow_variant_eval_case(
    case: WorkflowVariantEvalCaseContract,
) -> list[str]:
    """Return bounded fail-closed validation blockers for one paired case."""

    return _validation_failures(
        lambda: _validate_workflow_variant_eval_case_or_raise(case)
    )


def validate_workflow_variant_eval_case_pack(
    pack: WorkflowVariantEvalCasePackContract,
) -> list[str]:
    """Return bounded fail-closed validation blockers for one versioned pack."""

    return _validation_failures(
        lambda: _validate_workflow_variant_eval_case_pack_or_raise(pack)
    )


def validate_workflow_variant_eval_case_result(
    result: WorkflowVariantEvalCaseResultContract,
    *,
    case: WorkflowVariantEvalCaseContract | None = None,
) -> list[str]:
    """Revalidate a result, optionally against its immutable source case."""

    if case is None:
        return ["workflow_eval_source_case_required"]
    failures = _validation_failures(
        lambda: _validate_workflow_variant_eval_case_result_or_raise(result)
    )
    if failures:
        return failures
    case_failures = validate_workflow_variant_eval_case(case)
    if case_failures:
        return [f"source_case:{failure}" for failure in case_failures]
    expected_identity = (
        case.case_pack_id,
        case.case_pack_version,
        case.case_id,
        case.case_version,
        case.scenario_ref,
        case.input_snapshot_fingerprint,
        case.workflow_profile,
        case.route,
        case.baseline_version_ref,
        case.candidate_version_ref,
        case.baseline_observation.definition_hash,
        case.candidate_observation.definition_hash,
        case.control_snapshot.control_snapshot_id,
        workflow_variant_eval_control_fingerprint(case.control_snapshot),
        case.baseline_observation.outcome_ref,
        case.candidate_observation.outcome_ref,
        case.baseline_observation.outcome_status,
        case.candidate_observation.outcome_status,
    )
    actual_identity = (
        result.case_pack_id,
        result.case_pack_version,
        result.case_id,
        result.case_version,
        result.scenario_ref,
        result.input_snapshot_fingerprint,
        result.workflow_profile,
        result.route,
        result.baseline_version_ref,
        result.candidate_version_ref,
        result.baseline_definition_hash,
        result.candidate_definition_hash,
        result.control_snapshot_id,
        result.control_snapshot_fingerprint,
        result.baseline_outcome_ref,
        result.candidate_outcome_ref,
        result.baseline_outcome_status,
        result.candidate_outcome_status,
    )
    if actual_identity != expected_identity:
        failures.append("case_result_source_identity_mismatch")
    try:
        expected_baseline = derive_workflow_variant_eval_metrics(
            case.baseline_observation,
            checkpoint_refs=case.baseline_observation.expected_checkpoint_refs,
        )
        expected_candidate = derive_workflow_variant_eval_metrics(
            case.candidate_observation,
            checkpoint_refs=case.candidate_observation.expected_checkpoint_refs,
        )
    except ValueError as exc:
        failures.append(f"case_result_metric_derivation_failed:{exc}")
        return failures
    if not _float_mappings_equal(result.baseline_metrics, expected_baseline):
        failures.append("case_result_baseline_metrics_not_derived")
    if not _float_mappings_equal(result.candidate_metrics, expected_candidate):
        failures.append("case_result_candidate_metrics_not_derived")
    expected_checks = derive_workflow_variant_eval_case_checks(
        case,
        baseline_metrics=expected_baseline,
        candidate_metrics=expected_candidate,
        limitations=result.limitations,
    )
    if result.checks != expected_checks:
        failures.append("case_result_checks_not_derived")
    expected_failures = [
        name for name, passed in expected_checks.items() if not passed
    ]
    if result.failures != expected_failures:
        failures.append("case_result_failures_not_derived")
    return failures


def validate_workflow_variant_eval_run(
    run: WorkflowVariantEvalRunContract,
    *,
    case_pack: WorkflowVariantEvalCasePackContract | None = None,
) -> list[str]:
    """Revalidate one aggregate run against its pack when available."""

    if case_pack is None:
        return ["workflow_eval_source_case_pack_required"]
    failures = _validation_failures(
        lambda: _validate_workflow_variant_eval_run_or_raise(run)
    )
    if failures:
        return failures
    pack_failures = validate_workflow_variant_eval_case_pack(case_pack)
    if pack_failures:
        return [f"source_case_pack:{failure}" for failure in pack_failures]
    if (
        run.case_pack_id != case_pack.case_pack_id
        or run.case_pack_version != case_pack.case_pack_version
        or run.case_pack_fingerprint
        != workflow_variant_eval_case_pack_fingerprint(case_pack)
        or run.workflow_profile != case_pack.workflow_profile
        or run.route != case_pack.route
        or run.baseline_version_ref != case_pack.baseline_version_ref
        or run.candidate_version_ref != case_pack.candidate_version_ref
    ):
        failures.append("workflow_eval_run_case_pack_identity_mismatch")
    cases_by_identity = {
        (case.case_id, case.case_version): case for case in case_pack.cases
    }
    if len(run.case_results) != len(cases_by_identity):
        failures.append("workflow_eval_run_case_pack_cardinality_mismatch")
    for result in run.case_results:
        case = cases_by_identity.get((result.case_id, result.case_version))
        if case is None:
            failures.append(f"case:{result.case_id}:not_in_case_pack")
            continue
        failures.extend(
            f"case:{result.case_id}:{failure}"
            for failure in validate_workflow_variant_eval_case_result(
                result,
                case=case,
            )
        )
    return list(dict.fromkeys(failures))


def _validation_failures(validation: Any) -> list[str]:
    try:
        validation()
    except (TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def _aggregate_metrics(
    results: list[WorkflowVariantEvalCaseResultContract],
    attribute: str,
) -> dict[str, float]:
    return {
        metric: round(
            sum(getattr(result, attribute)[metric] for result in results) / len(results),
            4,
        )
        for metric in WORKFLOW_VARIANT_EVAL_METRICS
    }


def _validate_eval_modes(value: object) -> None:
    if getattr(value, "comparison_mode", None) != WORKFLOW_VARIANT_EVAL_COMPARISON_MODE:
        raise ValueError("workflow eval comparison_mode is not controlled")
    if getattr(value, "metrics_source", None) != WORKFLOW_VARIANT_EVAL_METRICS_SOURCE:
        raise ValueError("workflow eval metrics_source is not derived")


def _validate_safe_authority(value: object) -> None:
    for field_name in ("offline_only", "read_only", "sandbox_only"):
        if getattr(value, field_name, None) is not True:
            raise ValueError(f"workflow eval {field_name} must be true")
    for field_name in _AUTHORITY_FIELDS:
        if getattr(value, field_name, None) is not False:
            raise ValueError(f"workflow eval {field_name} must be false")
    if hasattr(value, "human_review_required") and (
        getattr(value, "human_review_required") is not True
    ):
        raise ValueError("workflow eval human_review_required must be true")


def _validate_metrics(metrics: dict[str, float], *, field_name: str) -> None:
    if not isinstance(metrics, dict) or set(metrics) != set(WORKFLOW_VARIANT_EVAL_METRICS):
        raise ValueError(f"{field_name} must contain the fixed metric set")
    for value in metrics.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{field_name} values must be numeric")
        if not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{field_name} values must be normalized")


def _validate_deltas(deltas: dict[str, float]) -> None:
    if not isinstance(deltas, dict) or set(deltas) != set(WORKFLOW_VARIANT_EVAL_METRICS):
        raise ValueError("metric_deltas must contain the fixed metric set")
    for value in deltas.values():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("metric_deltas values must be numeric")
        if not -1.0 <= float(value) <= 1.0:
            raise ValueError("metric_deltas values must remain normalized")


def _canonical_text_list(
    values: object,
    *,
    field_name: str,
    minimum: int,
    maximum: int,
) -> list[str]:
    if not isinstance(values, list) or not minimum <= len(values) <= maximum:
        raise ValueError(f"{field_name} must be a bounded list")
    canonical: list[str] = []
    for value in values:
        _require_text(value, field_name=field_name)
        if len(value) > 500:
            raise ValueError(f"{field_name} values must remain bounded")
        canonical.append(value)
    if len(canonical) != len(set(canonical)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return canonical


def _require_text(value: object, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 500
    ):
        raise ValueError(f"{field_name} must be canonical bounded text")


def _require_sha256_like(value: object, *, field_name: str) -> None:
    _require_text(value, field_name=field_name)
    assert isinstance(value, str)
    normalized = value.removeprefix("sha256:")
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise ValueError(f"{field_name} must be a lowercase SHA-256 fingerprint")


def _require_timestamp(value: object, *, field_name: str) -> None:
    _require_text(value, field_name=field_name)
    assert isinstance(value, str)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name} must include a timezone")


def _float_equal(left: object, right: object) -> bool:
    if isinstance(left, bool) or not isinstance(left, (int, float)):
        return False
    if isinstance(right, bool) or not isinstance(right, (int, float)):
        return False
    return isclose(float(left), float(right), abs_tol=0.00005)


def _float_mappings_equal(
    left: object,
    right: dict[str, float],
) -> bool:
    return isinstance(left, dict) and set(left) == set(right) and all(
        _float_equal(left[key], right[key]) for key in right
    )
