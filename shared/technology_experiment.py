"""Canonical, fail-closed semantics for inert technology experiment packs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps
from math import isfinite
from re import fullmatch
from typing import Any
from unicodedata import category
from urllib.parse import unquote

from shared.contracts import (
    TECHNOLOGY_EXPERIMENT_COMPARISON_MODE,
    TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
    TECHNOLOGY_EXPERIMENT_METRICS,
    TECHNOLOGY_EXPERIMENT_METRICS_SOURCE,
    TechnologyExperimentCaseContract,
    TechnologyExperimentCaseResultContract,
    TechnologyExperimentControlSnapshotContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentEvalRunContract,
    TechnologyExperimentObservationContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
)
from shared.technology_radar_intake import (
    technology_radar_intake_fingerprint,
    technology_radar_review_subject_fingerprint,
    technology_text_contains_sensitive_material,
    validate_technology_radar_intake,
)
from shared.versioning import parse_canonical_semver

TECHNOLOGY_EXPERIMENT_TRANSLATION_KIND = "absorbable_pattern"
TECHNOLOGY_EXPERIMENT_ALLOWED_ABSORPTION_CLASSES = frozenset(
    {"sandbox_experiment", "controlled_complement", "promotable_translation"}
)
TECHNOLOGY_EXPERIMENT_ALLOWED_CONSUMERS = frozenset(
    {
        "jarvis-component://domain-registry",
        "jarvis-component://evolution-lab",
        "jarvis-component://governance-service",
        "jarvis-component://knowledge-service",
        "jarvis-component://memory-service",
        "jarvis-component://observability-service",
        "jarvis-component://orchestrator-service",
        "jarvis-component://planning-engine",
        "jarvis-component://synthesis-engine",
    }
)
TECHNOLOGY_EXPERIMENT_REQUIRED_ISOLATION_CHECKS = frozenset(
    {
        "dependencies_unchanged",
        "external_code_not_executed",
        "host_filesystem_unchanged",
        "network_disabled",
    }
)
TECHNOLOGY_EXPERIMENT_REQUIRED_CONTRACT_CHECKS = frozenset(
    {"sovereign_consumer_preserved"}
)

_SHA256 = r"[0-9a-f]{64}"
_MAX_ITEMS = 32
_MAX_TEXT = 1000
_MAX_CASES = 32
_MAX_CLOCK_SKEW_SECONDS = 300
_PACK_AUTHORITY_FALSE_FIELDS = (
    "network_fetch_allowed",
    "subprocess_allowed",
    "dependency_installation_allowed",
    "external_code_execution_allowed",
    "tool_dispatch_allowed",
    "host_filesystem_write_allowed",
    "knowledge_ingestion_allowed",
    "memory_write_allowed",
    "runtime_activation_allowed",
    "registry_write_allowed",
    "evolution_proposal_allowed",
    "release_authorized",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
    "priority_mutation_allowed",
)
_CONTROL_AUTHORITY_FALSE_FIELDS = tuple(
    field for field in _PACK_AUTHORITY_FALSE_FIELDS if field != "evolution_proposal_allowed"
)
_CASE_AUTHORITY_FALSE_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "release_authorized",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
    "priority_mutation_allowed",
)


def canonical_technology_experiment_payload(value: object) -> str:
    """Serialize one experiment artifact deterministically."""

    payload: object
    if is_dataclass(value) and not isinstance(value, type):
        payload = asdict(value)
    else:
        payload = value
    return dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def technology_experiment_artifact_fingerprint(value: object) -> str:
    return sha256(canonical_technology_experiment_payload(value).encode("utf-8")).hexdigest()


technology_experiment_pack_fingerprint = technology_experiment_artifact_fingerprint
technology_experiment_control_fingerprint = technology_experiment_artifact_fingerprint
technology_experiment_eval_run_fingerprint = technology_experiment_artifact_fingerprint


def technology_experiment_text_fingerprint(value: str) -> str:
    return sha256(
        canonical_technology_experiment_payload(str(value)).encode("utf-8")
    ).hexdigest()


def technology_experiment_pack_input_fingerprint(
    pack: TechnologyExperimentPackContract,
) -> str:
    return technology_experiment_artifact_fingerprint(
        [
            {
                "case_id": case.case_id,
                "case_version": case.case_version,
                "input_fingerprint": case.input_fingerprint,
            }
            for case in pack.cases
        ]
    )


def technology_experiment_pack_control_fingerprint(
    pack: TechnologyExperimentPackContract,
) -> str:
    return technology_experiment_artifact_fingerprint(
        [
            {
                "case_id": case.case_id,
                "case_version": case.case_version,
                "control_fingerprint": technology_experiment_control_fingerprint(
                    case.control_snapshot
                ),
            }
            for case in pack.cases
        ]
    )


def validate_technology_experiment_control_snapshot(
    control: TechnologyExperimentControlSnapshotContract,
) -> list[str]:
    blockers: list[str] = []
    _require_ref(control.control_snapshot_id, "technology-experiment-control", blockers)
    _require_hash(control.input_fingerprint, "control input fingerprint", blockers)
    _require_ref(control.sandbox_policy_ref, "technology-sandbox-policy", blockers)
    if parse_canonical_semver(control.sandbox_policy_version) is None:
        blockers.append("control sandbox policy version must be canonical SemVer")
    if parse_canonical_semver(control.evaluator_version) is None:
        blockers.append("control evaluator version must be canonical SemVer")
    if isinstance(control.deterministic_seed, bool) or not isinstance(
        control.deterministic_seed, int
    ) or not (0 <= control.deterministic_seed <= 2_147_483_647):
        blockers.append("control deterministic seed is outside the allowed bound")
    if _parse_utc(control.fixed_clock) is None:
        blockers.append("control fixed clock must be canonical UTC")
    if control.isolation_profile_ref != TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE:
        blockers.append("control isolation profile must be the sovereign offline profile")
    _require_hash(control.isolation_fingerprint, "control isolation fingerprint", blockers)
    _require_hash(control.environment_fingerprint, "control environment fingerprint", blockers)
    _require_true(control, ("offline_only", "sandbox_only", "read_only"), blockers)
    _require_false(control, _CONTROL_AUTHORITY_FALSE_FIELDS, blockers)
    return _dedupe(blockers)


def validate_technology_experiment_observation(
    observation: TechnologyExperimentObservationContract,
) -> list[str]:
    blockers: list[str] = []
    _require_ref(observation.observation_id, "technology-experiment-observation", blockers)
    _require_ref(observation.experiment_pack_id, "technology-experiment-pack", blockers)
    if parse_canonical_semver(observation.pack_version) is None:
        blockers.append("observation pack version must be canonical SemVer")
    _require_ref(observation.case_id, "technology-experiment-case", blockers)
    if parse_canonical_semver(observation.case_version) is None:
        blockers.append("observation case version must be canonical SemVer")
    if observation.arm not in {"baseline", "candidate"}:
        blockers.append("observation arm must be baseline or candidate")
    expected_definition_scheme = (
        "jarvis-baseline"
        if observation.arm == "baseline"
        else "jarvis-experiment-definition"
    )
    _require_ref(observation.definition_ref, expected_definition_scheme, blockers)
    _require_hash(observation.definition_hash, "observation definition hash", blockers)
    _require_hash(observation.input_fingerprint, "observation input fingerprint", blockers)
    _require_ref(observation.control_snapshot_id, "technology-experiment-control", blockers)
    _require_hash(
        observation.control_snapshot_fingerprint,
        "observation control fingerprint",
        blockers,
    )
    _require_ref(observation.outcome_ref, "technology-experiment-outcome", blockers)
    if observation.outcome_status not in {"completed", "failed", "blocked"}:
        blockers.append("observation outcome status is not canonical")
    for field_name, values in (
        ("contract checks", observation.contract_checks),
        ("isolation checks", observation.isolation_checks),
        ("success criteria", observation.success_criteria_results),
    ):
        _validate_boolean_map(values, field_name, blockers)
    for field_name, value in (
        ("action count", observation.action_count),
        ("rework count", observation.rework_count),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 10_000):
            blockers.append(f"observation {field_name} is outside the allowed bound")
    if observation.rework_count > observation.action_count:
        blockers.append("observation rework count cannot exceed action count")
    _validate_ref_list(observation.evidence_refs, "observation evidence", blockers, required=True)
    _validate_text_list(observation.limitations, "observation limitations", blockers)
    if _parse_utc(observation.observed_at) is None:
        blockers.append("observation timestamp must be canonical UTC")
    if observation.source_mode != "preproduced_sandbox_attestation":
        blockers.append("observation source mode must remain a preproduced attestation")
    _require_true(observation, ("offline_only", "sandbox_only", "read_only"), blockers)
    _require_false(observation, _CONTROL_AUTHORITY_FALSE_FIELDS, blockers)
    return _dedupe(blockers)


def validate_technology_experiment_case(
    case: TechnologyExperimentCaseContract,
) -> list[str]:
    blockers: list[str] = []
    _require_ref(case.experiment_pack_id, "technology-experiment-pack", blockers)
    if parse_canonical_semver(case.pack_version) is None:
        blockers.append("case pack version must be canonical SemVer")
    _require_ref(case.case_id, "technology-experiment-case", blockers)
    if parse_canonical_semver(case.case_version) is None:
        blockers.append("case version must be canonical SemVer")
    _require_ref(case.scenario_ref, "technology-experiment-scenario", blockers)
    _require_hash(case.input_fingerprint, "case input fingerprint", blockers)
    _require_ref(case.baseline_definition_ref, "jarvis-baseline", blockers)
    _require_hash(case.baseline_definition_hash, "case baseline definition hash", blockers)
    _require_ref(case.candidate_definition_ref, "jarvis-experiment-definition", blockers)
    _require_hash(case.candidate_definition_hash, "case candidate definition hash", blockers)
    if case.baseline_definition_hash == case.candidate_definition_hash:
        blockers.append("case requires distinct baseline and candidate definitions")
    _validate_name_list(
        case.critical_contract_check_refs,
        "case critical contract checks",
        blockers,
        required=True,
    )
    _validate_name_list(
        case.critical_isolation_check_refs,
        "case critical isolation checks",
        blockers,
        required=True,
    )
    _validate_name_list(
        case.success_criteria_refs,
        "case success criteria",
        blockers,
        required=True,
    )
    if not TECHNOLOGY_EXPERIMENT_REQUIRED_CONTRACT_CHECKS.issubset(
        case.critical_contract_check_refs
    ):
        blockers.append("case must verify sovereign consumer preservation")
    if not TECHNOLOGY_EXPERIMENT_REQUIRED_ISOLATION_CHECKS.issubset(
        case.critical_isolation_check_refs
    ):
        blockers.append("case must include every mandatory isolation check")
    blockers.extend(validate_technology_experiment_control_snapshot(case.control_snapshot))
    for observation in (case.baseline_observation, case.candidate_observation):
        blockers.extend(validate_technology_experiment_observation(observation))
    control_fingerprint = technology_experiment_control_fingerprint(case.control_snapshot)
    for arm, observation, definition_ref, definition_hash in (
        (
            "baseline",
            case.baseline_observation,
            case.baseline_definition_ref,
            case.baseline_definition_hash,
        ),
        (
            "candidate",
            case.candidate_observation,
            case.candidate_definition_ref,
            case.candidate_definition_hash,
        ),
    ):
        if (
            observation.arm != arm
            or observation.experiment_pack_id != case.experiment_pack_id
            or observation.pack_version != case.pack_version
            or observation.case_id != case.case_id
            or observation.case_version != case.case_version
            or observation.definition_ref != definition_ref
            or observation.definition_hash != definition_hash
            or observation.input_fingerprint != case.input_fingerprint
            or observation.control_snapshot_id != case.control_snapshot.control_snapshot_id
            or observation.control_snapshot_fingerprint != control_fingerprint
        ):
            blockers.append(f"case {arm} observation binding mismatch")
        if _parse_utc(observation.observed_at) != _parse_utc(case.control_snapshot.fixed_clock):
            blockers.append(f"case {arm} observation must use the fixed control clock")
        if set(observation.contract_checks) != set(case.critical_contract_check_refs):
            blockers.append(f"case {arm} contract check universe mismatch")
        if set(observation.isolation_checks) != set(case.critical_isolation_check_refs):
            blockers.append(f"case {arm} isolation check universe mismatch")
        if set(observation.success_criteria_results) != set(case.success_criteria_refs):
            blockers.append(f"case {arm} success criteria universe mismatch")
    if case.baseline_observation.outcome_ref == case.candidate_observation.outcome_ref:
        blockers.append("case observations require distinct outcome refs")
    _validate_ref_list(case.evidence_refs, "case evidence", blockers, required=True)
    _validate_text_list(case.limitations, "case limitations", blockers)
    if case.comparison_mode != TECHNOLOGY_EXPERIMENT_COMPARISON_MODE:
        blockers.append("case comparison mode is not canonical")
    if case.metrics_source != TECHNOLOGY_EXPERIMENT_METRICS_SOURCE:
        blockers.append("case metrics source is not canonical")
    _require_true(
        case,
        ("offline_only", "sandbox_only", "read_only", "human_review_required"),
        blockers,
    )
    _require_false(case, _CASE_AUTHORITY_FALSE_FIELDS, blockers)
    return _dedupe(blockers)


def validate_technology_experiment_pack_shape(
    pack: TechnologyExperimentPackContract,
) -> list[str]:
    blockers: list[str] = []
    _require_ref(pack.experiment_pack_id, "technology-experiment-pack", blockers)
    if parse_canonical_semver(pack.pack_version) is None:
        blockers.append("experiment pack version must be canonical SemVer")
    if not any(
        _canonical_ref(pack.intake_id, scheme)
        for scheme in ("technology-intake", "technology-radar-intake")
    ):
        blockers.append("experiment intake ref is not canonical")
    if parse_canonical_semver(pack.intake_version) is None:
        blockers.append("experiment intake version must be canonical SemVer")
    for field_name, value in (
        ("intake fingerprint", pack.intake_fingerprint),
        ("review subject fingerprint", pack.reviewed_payload_fingerprint),
        ("source content hash", pack.source_content_sha256),
        ("baseline definition hash", pack.baseline_definition_hash),
        ("candidate definition hash", pack.candidate_definition_hash),
    ):
        _require_hash(value, field_name, blockers)
    _require_compatible_ref(pack.candidate_ref, "technology-candidate", blockers)
    _validate_text(pack.technology_name, "technology name", blockers)
    if pack.absorption_class not in TECHNOLOGY_EXPERIMENT_ALLOWED_ABSORPTION_CLASSES:
        blockers.append("experiment intake class is not sandbox eligible")
    if pack.translation_kind != TECHNOLOGY_EXPERIMENT_TRANSLATION_KIND:
        blockers.append("framework substitution is not an experiment pack")
    _require_ref(pack.pattern_id, "technology-pattern", blockers)
    for field_name, value in (
        ("pattern name", pack.pattern_name),
        ("pattern summary", pack.pattern_summary),
        ("hypothesis", pack.hypothesis),
        ("expected gain", pack.expected_gain),
    ):
        _validate_text(value, field_name, blockers)
    _validate_hash_list(
        pack.selected_claim_fingerprints,
        "selected claim fingerprints",
        blockers,
        required=True,
    )
    _validate_hash_list(
        pack.selected_risk_fingerprints,
        "selected risk fingerprints",
        blockers,
    )
    if pack.sovereign_consumer_kind != "jarvis_component":
        blockers.append("experiment sovereign consumer kind is not canonical")
    if pack.sovereign_consumer_ref not in TECHNOLOGY_EXPERIMENT_ALLOWED_CONSUMERS:
        blockers.append("experiment sovereign consumer is not allowlisted")
    _require_ref(pack.consumer_contract_ref, "jarvis-contract", blockers)
    _require_ref(pack.bounded_integration_seam, "jarvis-seam", blockers)
    _validate_gap_list(pack.target_gap_refs, "experiment target gaps", blockers)
    _require_ref(pack.baseline_definition_ref, "jarvis-baseline", blockers)
    _require_ref(pack.candidate_definition_ref, "jarvis-experiment-definition", blockers)
    if pack.baseline_definition_hash == pack.candidate_definition_hash:
        blockers.append("experiment requires distinct baseline and candidate definitions")
    if pack.isolation_profile_ref != TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE:
        blockers.append("experiment isolation profile is not canonical")
    for field_name, values in (
        ("risk controls", pack.risk_control_refs),
        ("mitigations", pack.mitigation_refs),
        ("stop conditions", pack.stop_condition_refs),
        ("rollback verification", pack.rollback_verification_refs),
        ("evidence", pack.evidence_refs),
    ):
        _validate_ref_list(values, f"experiment {field_name}", blockers, required=True)
    if not pack.license_id or pack.license_id.upper() == "NOASSERTION":
        blockers.append("experiment requires a declared license")
    if pack.license_status != "declared":
        blockers.append("experiment license must be resolved before sandboxing")
    _require_compatible_ref(pack.license_evidence_ref, "license-evidence", blockers)
    _require_ref(pack.rollback_plan_ref, "technology-experiment-rollback", blockers)
    _validate_text_list(pack.rollback_steps, "experiment rollback steps", blockers, required=True)
    _require_ref(pack.selection_review_ref, "technology-experiment-selection-review", blockers)
    _require_ref(pack.selected_by_ref, "operator", blockers)
    if not isinstance(pack.cases, list) or not (1 <= len(pack.cases) <= _MAX_CASES):
        blockers.append("experiment pack cases are outside the allowed bound")
    else:
        identities = [(case.case_id, case.case_version) for case in pack.cases]
        if len(set(identities)) != len(identities):
            blockers.append("experiment pack contains duplicate case identities")
        for case in pack.cases:
            blockers.extend(validate_technology_experiment_case(case))
            if (
                case.experiment_pack_id != pack.experiment_pack_id
                or case.pack_version != pack.pack_version
                or case.baseline_definition_ref != pack.baseline_definition_ref
                or case.baseline_definition_hash != pack.baseline_definition_hash
                or case.candidate_definition_ref != pack.candidate_definition_ref
                or case.candidate_definition_hash != pack.candidate_definition_hash
                or case.control_snapshot.isolation_profile_ref != pack.isolation_profile_ref
            ):
                blockers.append("experiment case does not bind the pack definition")
    if (
        isinstance(pack.required_pass_rate, bool)
        or not isinstance(pack.required_pass_rate, (int, float))
        or not isfinite(float(pack.required_pass_rate))
        or not (0.0 < float(pack.required_pass_rate) <= 1.0)
    ):
        blockers.append("experiment required pass rate is outside the allowed bound")
    if _parse_utc(pack.generated_at) is None:
        blockers.append("experiment generated timestamp must be canonical UTC")
    if pack.pack_status != "sandbox_ready":
        blockers.append("experiment pack status must remain sandbox ready")
    if pack.source_mode != "registered_intake_only":
        blockers.append("experiment source mode must resolve a registered intake")
    if pack.external_framework_role != "subordinate_reference":
        blockers.append("external framework role must remain subordinate")
    if pack.requested_core_role != "subordinate":
        blockers.append("experiment cannot request a sovereign Core role")
    _require_true(
        pack,
        ("sandbox_only", "read_only", "immutable", "human_review_required"),
        blockers,
    )
    _require_false(pack, _PACK_AUTHORITY_FALSE_FIELDS, blockers)
    return _dedupe(blockers)


def validate_technology_experiment_pack(
    pack: TechnologyExperimentPackContract,
    *,
    intake: TechnologyRadarIntakeContract,
    now: datetime | None = None,
) -> list[str]:
    """Validate the pack against the exact verified MB-208 source record."""

    blockers = validate_technology_experiment_pack_shape(pack)
    intake_failures = validate_technology_radar_intake(intake, now=now)
    if intake_failures:
        blockers.append("experiment source intake is not canonical")
    if (
        pack.intake_id != intake.intake_id
        or pack.intake_version != intake.intake_version
        or pack.intake_fingerprint != technology_radar_intake_fingerprint(intake)
        or pack.reviewed_payload_fingerprint
        != technology_radar_review_subject_fingerprint(intake)
        or pack.candidate_ref != intake.candidate_ref
        or pack.technology_name != intake.technology_name
        or pack.source_content_sha256 != intake.source_content_sha256
        or pack.absorption_class != intake.absorption_class
        or pack.license_id != intake.license_id
        or pack.license_status != intake.license_status
        or pack.license_evidence_ref != intake.license_evidence_ref
    ):
        blockers.append("experiment pack does not match the verified intake")
    if intake.review_status != "approved_for_radar_intake":
        blockers.append("experiment source intake lacks approved human review")
    if not set(pack.target_gap_refs).issubset(intake.target_gap_refs):
        blockers.append("experiment target gaps must come from the verified intake")
    claim_fingerprints = {technology_experiment_text_fingerprint(item) for item in intake.claims}
    if not set(pack.selected_claim_fingerprints).issubset(claim_fingerprints):
        blockers.append("experiment selected claims must come from the verified intake")
    risk_fingerprints = {technology_experiment_text_fingerprint(item) for item in intake.risks}
    if not set(pack.selected_risk_fingerprints).issubset(risk_fingerprints):
        blockers.append("experiment selected risks must come from the verified intake")
    if intake.risks and not pack.selected_risk_fingerprints:
        blockers.append("experiment must bind at least one declared source risk")
    intake_recorded_at = _parse_utc(intake.recorded_at)
    generated_at = _parse_utc(pack.generated_at)
    if intake_recorded_at and generated_at and generated_at < intake_recorded_at:
        blockers.append("experiment cannot predate the verified intake")
    if generated_at and _timestamp_is_future(generated_at, now=now):
        blockers.append("experiment generated timestamp cannot be in the future")
    for case in pack.cases if isinstance(pack.cases, list) else []:
        fixed_clock = _parse_utc(case.control_snapshot.fixed_clock)
        if intake_recorded_at and fixed_clock and fixed_clock < intake_recorded_at:
            blockers.append("experiment evidence cannot predate the verified intake")
        if generated_at and fixed_clock and fixed_clock > generated_at:
            blockers.append("experiment evidence cannot postdate the pack")
    return _dedupe(blockers)


def require_valid_technology_experiment_pack(
    pack: TechnologyExperimentPackContract,
    *,
    intake: TechnologyRadarIntakeContract,
    now: datetime | None = None,
) -> TechnologyExperimentPackContract:
    blockers = validate_technology_experiment_pack(pack, intake=intake, now=now)
    if blockers:
        raise ValueError("technology experiment pack is invalid: " + "; ".join(blockers))
    return pack


def derive_technology_experiment_metrics(
    observation: TechnologyExperimentObservationContract,
) -> dict[str, float]:
    blockers = validate_technology_experiment_observation(observation)
    if blockers:
        raise ValueError("technology experiment observation is invalid: " + "; ".join(blockers))
    action_count = max(observation.action_count, 1)
    values = {
        "success_score": (
            _ratio(observation.success_criteria_results.values())
            if observation.outcome_status == "completed"
            else 0.0
        ),
        "contract_adherence": _ratio(observation.contract_checks.values()),
        "isolation_compliance": _ratio(observation.isolation_checks.values()),
        "sovereign_consumer_preservation": float(
            observation.contract_checks.get("sovereign_consumer_preserved") is True
        ),
        "rework_rate": round(observation.rework_count / action_count, 6),
    }
    return {name: values[name] for name in TECHNOLOGY_EXPERIMENT_METRICS}


def derive_technology_experiment_metric_deltas(
    baseline_metrics: dict[str, float],
    candidate_metrics: dict[str, float],
) -> dict[str, float]:
    if set(baseline_metrics) != set(TECHNOLOGY_EXPERIMENT_METRICS) or set(
        candidate_metrics
    ) != set(TECHNOLOGY_EXPERIMENT_METRICS):
        raise ValueError("technology experiment metrics are incomplete")
    return {
        name: round(
            (baseline_metrics[name] - candidate_metrics[name])
            if name == "rework_rate"
            else (candidate_metrics[name] - baseline_metrics[name]),
            6,
        )
        for name in TECHNOLOGY_EXPERIMENT_METRICS
    }


def derive_technology_experiment_case_result(
    case: TechnologyExperimentCaseContract,
    *,
    pack: TechnologyExperimentPackContract,
) -> TechnologyExperimentCaseResultContract:
    failures = [
        *validate_technology_experiment_pack_shape(pack),
        *validate_technology_experiment_case(case),
    ]
    if case not in pack.cases:
        failures.append("case is not present in the experiment pack")
    if failures:
        raise ValueError("technology experiment case is invalid: " + "; ".join(_dedupe(failures)))
    baseline_metrics = derive_technology_experiment_metrics(case.baseline_observation)
    candidate_metrics = derive_technology_experiment_metrics(case.candidate_observation)
    deltas = derive_technology_experiment_metric_deltas(baseline_metrics, candidate_metrics)
    improvement_signals = sorted(name for name, value in deltas.items() if value > 0)
    regression_flags = sorted(name for name, value in deltas.items() if value < 0)
    limitations = _dedupe(
        [
            *case.limitations,
            *case.baseline_observation.limitations,
            *case.candidate_observation.limitations,
        ]
    )
    baseline = case.baseline_observation
    candidate = case.candidate_observation
    checks = {
        "baseline_outcome_completed": baseline.outcome_status == "completed",
        "candidate_outcome_completed": candidate.outcome_status == "completed",
        "baseline_contract_checks_passed": all(baseline.contract_checks.values()),
        "candidate_contract_checks_passed": all(candidate.contract_checks.values()),
        "baseline_isolation_checks_passed": all(baseline.isolation_checks.values()),
        "candidate_isolation_checks_passed": all(candidate.isolation_checks.values()),
        "candidate_success_criteria_passed": all(
            candidate.success_criteria_results.values()
        ),
        "candidate_improved": bool(improvement_signals),
        "distinct_outcomes": (
            baseline.outcome_ref != candidate.outcome_ref
        ),
        "evidence_present": bool(
            case.evidence_refs
            and baseline.evidence_refs
            and candidate.evidence_refs
        ),
        "no_limitations": not limitations,
        "no_regression": not regression_flags,
    }
    result_failures = sorted(name for name, passed in checks.items() if passed is not True)
    evidence_refs = _dedupe(
        [
            *case.evidence_refs,
            *baseline.evidence_refs,
            *candidate.evidence_refs,
        ]
    )
    return TechnologyExperimentCaseResultContract(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=technology_experiment_pack_fingerprint(pack),
        case_id=case.case_id,
        case_version=case.case_version,
        scenario_ref=case.scenario_ref,
        input_fingerprint=case.input_fingerprint,
        control_snapshot_id=case.control_snapshot.control_snapshot_id,
        control_snapshot_fingerprint=technology_experiment_control_fingerprint(
            case.control_snapshot
        ),
        baseline_outcome_ref=baseline.outcome_ref,
        baseline_outcome_status=baseline.outcome_status,
        candidate_outcome_ref=candidate.outcome_ref,
        candidate_outcome_status=candidate.outcome_status,
        passed=not result_failures,
        checks=checks,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        metric_deltas=deltas,
        improvement_signals=improvement_signals,
        regression_flags=regression_flags,
        failures=result_failures,
        limitations=limitations,
        evidence_refs=evidence_refs,
    )


def validate_technology_experiment_case_result(
    result: TechnologyExperimentCaseResultContract,
    *,
    case: TechnologyExperimentCaseContract,
    pack: TechnologyExperimentPackContract,
) -> list[str]:
    try:
        expected = derive_technology_experiment_case_result(case, pack=pack)
    except (TypeError, ValueError) as exc:
        return [f"technology experiment case source is invalid:{type(exc).__name__}"]
    return [] if result == expected else ["technology experiment case result must be derived"]


def validate_technology_experiment_eval_run_claim(
    claim: TechnologyExperimentEvalRunClaimContract,
    *,
    pack: TechnologyExperimentPackContract,
    now: datetime | None = None,
) -> list[str]:
    blockers: list[str] = validate_technology_experiment_pack_shape(pack)
    _require_ref(claim.run_id, "technology-experiment-run", blockers)
    if (
        claim.experiment_pack_id != pack.experiment_pack_id
        or claim.pack_version != pack.pack_version
        or claim.pack_fingerprint != technology_experiment_pack_fingerprint(pack)
        or claim.intake_id != pack.intake_id
        or claim.intake_fingerprint != pack.intake_fingerprint
        or claim.input_fingerprint != technology_experiment_pack_input_fingerprint(pack)
        or claim.control_fingerprint
        != technology_experiment_pack_control_fingerprint(pack)
    ):
        blockers.append("technology experiment claim binding mismatch")
    claimed_at = _parse_utc(claim.claimed_at)
    generated_at = _parse_utc(pack.generated_at)
    if claimed_at is None:
        blockers.append("technology experiment claim timestamp must be canonical UTC")
    elif generated_at and claimed_at < generated_at:
        blockers.append("technology experiment claim cannot predate the pack")
    if claimed_at and _timestamp_is_future(claimed_at, now=now):
        blockers.append("technology experiment claim cannot be in the future")
    return _dedupe(blockers)


def derive_technology_experiment_eval_run(
    *,
    run_id: str,
    pack: TechnologyExperimentPackContract,
    intake: TechnologyRadarIntakeContract,
    generated_at: str,
    now: datetime | None = None,
) -> TechnologyExperimentEvalRunContract:
    _require_ref_or_raise(run_id, "technology-experiment-run", "run id")
    pack_blockers = validate_technology_experiment_pack(pack, intake=intake, now=now)
    if pack_blockers:
        raise ValueError(
            "technology experiment run requires a verified pack: "
            + "; ".join(pack_blockers)
        )
    generated = _parse_utc(generated_at)
    if generated is None:
        raise ValueError("technology experiment run timestamp must be canonical UTC")
    latest_source_time = max(
        [
            _parse_utc(pack.generated_at),
            *(
                _parse_utc(observation.observed_at)
                for case in pack.cases
                for observation in (case.baseline_observation, case.candidate_observation)
            ),
        ]
    )
    if latest_source_time and generated < latest_source_time:
        raise ValueError("technology experiment run cannot predate its evidence")
    if _timestamp_is_future(generated, now=now):
        raise ValueError("technology experiment run cannot be in the future")
    results = [
        derive_technology_experiment_case_result(case, pack=pack) for case in pack.cases
    ]
    total_cases = len(results)
    passed_cases = sum(result.passed for result in results)
    failed_cases = total_cases - passed_cases
    pass_rate = round(passed_cases / total_cases, 6)
    aggregate_baseline = _average_metrics(
        [result.baseline_metrics for result in results]
    )
    aggregate_candidate = _average_metrics(
        [result.candidate_metrics for result in results]
    )
    aggregate_deltas = derive_technology_experiment_metric_deltas(
        aggregate_baseline,
        aggregate_candidate,
    )
    regression_flags = _dedupe(
        [item for result in results for item in result.regression_flags]
    )
    limitations = _dedupe([item for result in results for item in result.limitations])
    universal_evidence_checks = {
        "baseline_outcome_completed",
        "candidate_outcome_completed",
        "baseline_contract_checks_passed",
        "candidate_contract_checks_passed",
        "baseline_isolation_checks_passed",
        "candidate_isolation_checks_passed",
        "distinct_outcomes",
        "evidence_present",
    }
    invalid_evidence = any(
        result.checks.get(check_name) is not True
        for result in results
        for check_name in universal_evidence_checks
    )
    blockers: list[str] = []
    if invalid_evidence:
        blockers.append("invalid_or_unsafe_case_evidence")
    if pass_rate < float(pack.required_pass_rate):
        blockers.append("required_pass_rate_not_met")
    if regression_flags:
        blockers.append("regression_detected")
    if limitations:
        blockers.append("limitations_present")
    passed = not blockers
    if passed:
        conclusion = "candidate_pattern_improved_without_regression"
    elif regression_flags:
        conclusion = "candidate_pattern_regression_detected"
    else:
        conclusion = "insufficient_or_invalid_evidence"
    return TechnologyExperimentEvalRunContract(
        run_id=run_id,
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=technology_experiment_pack_fingerprint(pack),
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
        intake_fingerprint=pack.intake_fingerprint,
        candidate_ref=pack.candidate_ref,
        pattern_id=pack.pattern_id,
        sovereign_consumer_ref=pack.sovereign_consumer_ref,
        input_fingerprint=technology_experiment_pack_input_fingerprint(pack),
        control_fingerprint=technology_experiment_pack_control_fingerprint(pack),
        status="passed_sandbox_only" if passed else "blocked",
        readiness_status=(
            "eligible_for_human_experiment_review" if passed else "blocked"
        ),
        promotion_readiness="not_applicable",
        comparison_conclusion=conclusion,
        pass_rate=pass_rate,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        aggregate_baseline_metrics=aggregate_baseline,
        aggregate_candidate_metrics=aggregate_candidate,
        aggregate_metric_deltas=aggregate_deltas,
        case_results=results,
        regression_flags=regression_flags,
        limitations=limitations,
        evidence_refs=_dedupe(
            [*pack.evidence_refs, *(item for result in results for item in result.evidence_refs)]
        ),
        blockers=blockers,
        generated_at=generated_at,
    )


def validate_technology_experiment_eval_run(
    run: TechnologyExperimentEvalRunContract,
    *,
    pack: TechnologyExperimentPackContract,
    intake: TechnologyRadarIntakeContract,
    now: datetime | None = None,
) -> list[str]:
    try:
        expected = derive_technology_experiment_eval_run(
            run_id=run.run_id,
            pack=pack,
            intake=intake,
            generated_at=str(run.generated_at),
            now=now,
        )
    except (TypeError, ValueError) as exc:
        return [f"technology experiment run source is invalid:{type(exc).__name__}"]
    return [] if run == expected else ["technology experiment eval run must be derived"]


def require_valid_technology_experiment_eval_run(
    run: TechnologyExperimentEvalRunContract,
    *,
    pack: TechnologyExperimentPackContract,
    intake: TechnologyRadarIntakeContract,
    now: datetime | None = None,
) -> TechnologyExperimentEvalRunContract:
    blockers = validate_technology_experiment_eval_run(
        run,
        pack=pack,
        intake=intake,
        now=now,
    )
    if blockers:
        raise ValueError("technology experiment eval run is invalid: " + "; ".join(blockers))
    return run


def _average_metrics(values: list[dict[str, float]]) -> dict[str, float]:
    if not values:
        raise ValueError("technology experiment metrics require at least one case")
    return {
        name: round(sum(item[name] for item in values) / len(values), 6)
        for name in TECHNOLOGY_EXPERIMENT_METRICS
    }


def _ratio(values: Any) -> float:
    items = list(values)
    if not items:
        return 0.0
    return round(sum(value is True for value in items) / len(items), 6)


def _validate_boolean_map(
    values: object,
    field_name: str,
    blockers: list[str],
) -> None:
    if not isinstance(values, dict) or not (1 <= len(values) <= _MAX_ITEMS):
        blockers.append(f"{field_name} must be a bounded mapping")
        return
    for key, value in values.items():
        if fullmatch(r"[a-z][a-z0-9_]{0,99}", key) is None or value not in {
            True,
            False,
        } or not isinstance(value, bool):
            blockers.append(f"{field_name} contains a non-canonical entry")
            return


def _validate_name_list(
    values: object,
    field_name: str,
    blockers: list[str],
    *,
    required: bool = False,
) -> None:
    if not isinstance(values, list) or len(values) > _MAX_ITEMS or (required and not values):
        blockers.append(f"{field_name} must be a bounded list")
        return
    if len(set(values)) != len(values):
        blockers.append(f"{field_name} contains duplicates")
    if any(
        not isinstance(value, str)
        or fullmatch(r"[a-z][a-z0-9_]{0,99}", value) is None
        for value in values
    ):
        blockers.append(f"{field_name} contains a non-canonical name")


def _validate_ref_list(
    values: object,
    field_name: str,
    blockers: list[str],
    *,
    required: bool = False,
) -> None:
    if not isinstance(values, list) or len(values) > _MAX_ITEMS or (required and not values):
        blockers.append(f"{field_name} must be a bounded list")
        return
    if len(set(values)) != len(values):
        blockers.append(f"{field_name} contains duplicates")
    if any(not _canonical_ref(value) for value in values):
        blockers.append(f"{field_name} contains a non-canonical ref")


def _validate_gap_list(
    values: object,
    field_name: str,
    blockers: list[str],
) -> None:
    if not isinstance(values, list) or not values or len(values) > _MAX_ITEMS:
        blockers.append(f"{field_name} must be a bounded list")
        return
    if len(set(values)) != len(values):
        blockers.append(f"{field_name} contains duplicates")
    if any(
        not isinstance(value, str)
        or fullmatch(r"[A-Z][A-Z0-9]{1,15}-[0-9]{3,6}", value) is None
        for value in values
    ):
        blockers.append(f"{field_name} contains a non-canonical gap id")


def _validate_hash_list(
    values: object,
    field_name: str,
    blockers: list[str],
    *,
    required: bool = False,
) -> None:
    if not isinstance(values, list) or len(values) > _MAX_ITEMS or (required and not values):
        blockers.append(f"{field_name} must be a bounded list")
        return
    if len(set(values)) != len(values) or any(
        not isinstance(value, str) or fullmatch(_SHA256, value) is None
        for value in values
    ):
        blockers.append(f"{field_name} contains a non-canonical hash")


def _validate_text_list(
    values: object,
    field_name: str,
    blockers: list[str],
    *,
    required: bool = False,
) -> None:
    if not isinstance(values, list) or len(values) > _MAX_ITEMS or (required and not values):
        blockers.append(f"{field_name} must be a bounded list")
        return
    if len(set(values)) != len(values):
        blockers.append(f"{field_name} contains duplicates")
    for value in values:
        _validate_text(value, field_name, blockers)


def _validate_text(value: object, field_name: str, blockers: list[str]) -> None:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
        or len(value) > _MAX_TEXT
        or any(category(character) in {"Cc", "Cf"} for character in value)
        or technology_text_contains_sensitive_material(value)
    ):
        blockers.append(f"{field_name} is not canonical inert text")


def _canonical_ref(value: object, scheme: str | None = None) -> bool:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > 500
        or not value.isascii()
    ):
        return False
    if any(category(character) in {"Cc", "Cf"} for character in value):
        return False
    pattern = rf"{scheme}://[^\s]+" if scheme else r"[a-z][a-z0-9+.-]*://[^\s]+"
    decoded = unquote(value)
    return (
        fullmatch(pattern, value) is not None
        and not any(category(character) in {"Cc", "Cf"} for character in decoded)
        and not technology_text_contains_sensitive_material(value)
        and not technology_text_contains_sensitive_material(decoded)
    )


def _canonical_identity_ref(value: object, scheme: str) -> bool:
    if not _canonical_ref(value, scheme):
        return False
    canonical_suffix = (
        r"[A-Za-z0-9][A-Za-z0-9._~:+-]*"
        r"(?:/[A-Za-z0-9][A-Za-z0-9._~:+-]*)*"
    )
    return fullmatch(rf"{scheme}://{canonical_suffix}", value) is not None


def _require_ref(value: object, scheme: str, blockers: list[str]) -> None:
    if not _canonical_identity_ref(value, scheme):
        blockers.append(f"{scheme} ref is not canonical")


def _require_compatible_ref(
    value: object,
    scheme: str,
    blockers: list[str],
) -> None:
    if not _canonical_ref(value, scheme):
        blockers.append(f"{scheme} ref is not canonical")


def _require_ref_or_raise(value: object, scheme: str, field_name: str) -> None:
    if not _canonical_identity_ref(value, scheme):
        raise ValueError(f"technology experiment {field_name} is not canonical")


def _require_hash(value: object, field_name: str, blockers: list[str]) -> None:
    if not isinstance(value, str) or fullmatch(_SHA256, value) is None:
        blockers.append(f"{field_name} must be a lowercase SHA-256")


def _require_true(value: object, fields: tuple[str, ...], blockers: list[str]) -> None:
    for field in fields:
        if getattr(value, field) is not True:
            blockers.append(f"{field} must be true")


def _require_false(value: object, fields: tuple[str, ...], blockers: list[str]) -> None:
    for field in fields:
        if getattr(value, field) is not False:
            blockers.append(f"{field} must be false")


def _parse_utc(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        return None
    return parsed


def _timestamp_is_future(value: datetime, *, now: datetime | None) -> bool:
    comparison_now = now or datetime.now(UTC)
    if comparison_now.tzinfo is None:
        comparison_now = comparison_now.replace(tzinfo=UTC)
    else:
        comparison_now = comparison_now.astimezone(UTC)
    return value.timestamp() > (
        comparison_now.timestamp() + _MAX_CLOCK_SKEW_SECONDS
    )


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
