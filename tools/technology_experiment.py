"""Build and evaluate inert technology experiment packs from reviewed intakes.

This module is deliberately an attestation evaluator, not a technology runner.  It
never fetches, installs, imports or executes candidate code.  Both public write
paths validate a bounded local manifest before they are given an Evolution writer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from json import JSONDecodeError, loads
from os import fstat
from pathlib import Path
from re import IGNORECASE, fullmatch
from re import compile as compile_pattern
from stat import S_ISREG
from typing import Any, BinaryIO, TypeVar
from unicodedata import category, normalize

from shared.contracts import (
    TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
    TechnologyExperimentCaseContract,
    TechnologyExperimentControlSnapshotContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentEvalRunContract,
    TechnologyExperimentObservationContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
)
from shared.technology_experiment import (
    derive_technology_experiment_eval_run,
    require_valid_technology_experiment_eval_run,
    require_valid_technology_experiment_pack,
    technology_experiment_pack_fingerprint,
    technology_experiment_text_fingerprint,
    validate_technology_experiment_eval_run_claim,
)
from shared.technology_radar_intake import technology_radar_intake_fingerprint
from shared.versioning import parse_canonical_semver

MAX_TECHNOLOGY_EXPERIMENT_PACK_MANIFEST_BYTES = 131_072
MAX_TECHNOLOGY_EXPERIMENT_EVAL_MANIFEST_BYTES = 262_144

_SHA256_PATTERN = r"[0-9a-f]{64}"
_FORBIDDEN_MANIFEST_KEYS = frozenset(
    {
        "args",
        "argv",
        "command",
        "command_line",
        "dependency",
        "dependencies",
        "executable",
        "install",
        "module",
        "package",
        "packages",
        "path",
        "script",
        "source_code",
        "source_locator",
        "url",
    }
)
_FORBIDDEN_CALLER_DERIVED_KEYS = frozenset(
    {
        "baseline_metrics",
        "blockers",
        "candidate_metrics",
        "comparison_conclusion",
        "failures",
        "improvement_signals",
        "metric_deltas",
        "metrics",
        "passed",
        "readiness_status",
        "regression_flags",
        "status",
    }
)
_CANONICAL_BOOLEAN_CHECK_KEYS_WITH_FORBIDDEN_TOKENS = frozenset(
    {"dependencies_unchanged"}
)
_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "auth_token",
        "authorization",
        "client_secret",
        "credential",
        "credentials",
        "password",
        "passwd",
        "private_key",
        "secret",
        "token",
    }
)
_SENSITIVE_ASSIGNMENT = compile_pattern(
    r"\b(api[-_]?key|access[-_]?token|auth[-_]?token|client[-_]?secret|"
    r"aws[-_]?secret[-_]?access[-_]?key|private[-_]?key|token|password|passwd|secret)"
    r"\s*[:=]\s*[^\s,;]+",
    IGNORECASE,
)
_BEARER_TOKEN = compile_pattern(r"\bBearer\s+[^\s,;]+", IGNORECASE)
_AUTHENTICATED_URL = compile_pattern(r"://[^\s/:@]+:[^@\s]+@", IGNORECASE)
_PRIVATE_PATH = compile_pattern(
    r"(?:\b[A-Za-z]:[\\/]|(?<![:\w])/(?:Users|home|root|tmp|var|etc|run|opt)/)",
    IGNORECASE,
)
_PRIVATE_KEY_BLOCK = compile_pattern(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----",
    IGNORECASE,
)
_STANDALONE_CREDENTIAL = compile_pattern(
    r"(?:\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{16,255}\b"
    r"|\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{16,255}\b"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|\bglpat-[A-Za-z0-9_-]{16,255}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{16,255}\b"
    r"|\b(?:sk|rk)_live_[A-Za-z0-9]{16,255}\b"
    r"|\bAIza[0-9A-Za-z_-]{31,255}\b"
    r"|\bnpm_[A-Za-z0-9]{16,255}\b)",
)

_PACK_SELECTION_REQUIRED_FIELDS = frozenset(
    {
        "experiment_pack_id",
        "pack_version",
        "intake_id",
        "intake_version",
        "intake_fingerprint",
        "translation_kind",
        "pattern_id",
        "pattern_name",
        "pattern_summary",
        "selected_claim_fingerprints",
        "selected_risk_fingerprints",
        "hypothesis",
        "expected_gain",
        "sovereign_consumer_kind",
        "sovereign_consumer_ref",
        "consumer_contract_ref",
        "bounded_integration_seam",
        "target_gap_refs",
        "baseline_definition_ref",
        "baseline_definition_hash",
        "candidate_definition_ref",
        "candidate_definition_hash",
        "isolation_profile_ref",
        "risk_control_refs",
        "mitigation_refs",
        "stop_condition_refs",
        "rollback_plan_ref",
        "rollback_steps",
        "rollback_verification_refs",
        "selection_review_ref",
        "selected_by_ref",
        "cases",
        "required_pass_rate",
        "evidence_refs",
        "generated_at",
    }
)
_CASE_REQUIRED_FIELDS = frozenset(
    {
        "case_id",
        "case_version",
        "scenario_ref",
        "input_fingerprint",
        "baseline_definition_ref",
        "baseline_definition_hash",
        "candidate_definition_ref",
        "candidate_definition_hash",
        "critical_contract_check_refs",
        "critical_isolation_check_refs",
        "success_criteria_refs",
        "control_snapshot",
        "baseline_observation",
        "candidate_observation",
        "evidence_refs",
    }
)
_CONTROL_REQUIRED_FIELDS = frozenset(
    {
        "control_snapshot_id",
        "input_fingerprint",
        "sandbox_policy_ref",
        "sandbox_policy_version",
        "evaluator_version",
        "deterministic_seed",
        "fixed_clock",
        "isolation_profile_ref",
        "isolation_fingerprint",
        "environment_fingerprint",
    }
)
_OBSERVATION_REQUIRED_FIELDS = frozenset(
    {
        "observation_id",
        "case_id",
        "case_version",
        "arm",
        "definition_ref",
        "definition_hash",
        "input_fingerprint",
        "control_snapshot_id",
        "control_snapshot_fingerprint",
        "outcome_ref",
        "outcome_status",
        "contract_checks",
        "isolation_checks",
        "success_criteria_results",
        "action_count",
        "rework_count",
        "evidence_refs",
        "limitations",
        "observed_at",
    }
)
_EVAL_MANIFEST_FIELDS = frozenset(
    {
        "run_id",
        "experiment_pack_id",
        "pack_version",
        "pack_fingerprint",
        "generated_at",
    }
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class TechnologyExperimentRegistrationResult:
    """Result of translating one reviewed intake into an inert experiment pack."""

    pack: TechnologyExperimentPackContract
    pack_fingerprint: str
    persistence_status: str = "recorded_or_exact_retry"
    source_fetched: bool = False
    dependency_installed: bool = False
    candidate_imported: bool = False
    candidate_executed: bool = False
    core_called: bool = False
    tool_dispatched: bool = False
    runtime_activated: bool = False
    promotion_performed: bool = False
    core_mutated: bool = False
    priority_mutated: bool = False


def load_technology_experiment_pack_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    max_bytes: int = MAX_TECHNOLOGY_EXPERIMENT_PACK_MANIFEST_BYTES,
) -> dict[str, Any]:
    """Load one strict declarative pack selection without opening any store."""

    payload = _load_local_manifest_payload(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
        max_bytes=max_bytes,
        manifest_label="technology experiment pack manifest",
    )
    _reject_dangerous_manifest_content(
        payload,
        manifest_label="technology experiment pack manifest",
        reject_derived_keys=True,
    )
    _validate_pack_selection_payload(payload)
    return payload


def assess_technology_experiment_pack_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    intake_reader: object,
) -> TechnologyExperimentPackContract:
    """Resolve a safe selection against an exact persisted MB-208 intake."""

    payload = load_technology_experiment_pack_manifest(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    intake = _get_exact_intake(
        intake_reader,
        intake_id=payload["intake_id"],
        intake_version=payload["intake_version"],
    )
    return build_technology_experiment_pack(payload, intake=intake)


def build_technology_experiment_pack(
    selection: Mapping[str, Any],
    *,
    intake: TechnologyRadarIntakeContract,
) -> TechnologyExperimentPackContract:
    """Translate selected inert data while copying all source facts from intake."""

    _validate_pack_selection_payload(selection)
    expected_intake_fingerprint = technology_radar_intake_fingerprint(intake)
    if (
        selection["intake_id"] != intake.intake_id
        or selection["intake_version"] != intake.intake_version
        or selection["intake_fingerprint"] != expected_intake_fingerprint
    ):
        raise ValueError("technology experiment intake binding mismatch")
    if intake.intake_status != "reviewed_reference" or not intake.immutable:
        raise ValueError("technology experiment requires an immutable reviewed intake")
    if intake.license_status != "declared" or intake.license_id == "NOASSERTION":
        raise ValueError("technology experiment requires a resolved declared license")
    if intake.absorption_class not in {
        "sandbox_experiment",
        "controlled_complement",
        "promotable_translation",
    }:
        raise ValueError("technology experiment intake is not eligible for a sandbox pack")
    if not set(selection["target_gap_refs"]).issubset(intake.target_gap_refs):
        raise ValueError("technology experiment target gaps exceed the reviewed intake")
    _require_selected_text_fingerprints(
        selection["selected_claim_fingerprints"],
        source_values=intake.claims,
        field_name="selected_claim_fingerprints",
    )
    _require_selected_text_fingerprints(
        selection["selected_risk_fingerprints"],
        source_values=intake.risks,
        field_name="selected_risk_fingerprints",
    )

    pack_id = selection["experiment_pack_id"]
    pack_version = selection["pack_version"]
    cases = [
        _build_experiment_case(
            case_payload,
            experiment_pack_id=pack_id,
            pack_version=pack_version,
            baseline_definition_ref=selection["baseline_definition_ref"],
            baseline_definition_hash=selection["baseline_definition_hash"],
            candidate_definition_ref=selection["candidate_definition_ref"],
            candidate_definition_hash=selection["candidate_definition_hash"],
            isolation_profile_ref=selection["isolation_profile_ref"],
        )
        for case_payload in selection["cases"]
    ]
    pack = TechnologyExperimentPackContract(
        experiment_pack_id=pack_id,
        pack_version=pack_version,
        intake_id=intake.intake_id,
        intake_version=intake.intake_version,
        intake_fingerprint=expected_intake_fingerprint,
        reviewed_payload_fingerprint=intake.reviewed_payload_fingerprint,
        candidate_ref=intake.candidate_ref,
        technology_name=intake.technology_name,
        source_content_sha256=intake.source_content_sha256,
        absorption_class=intake.absorption_class,
        translation_kind=selection["translation_kind"],
        pattern_id=selection["pattern_id"],
        pattern_name=selection["pattern_name"],
        pattern_summary=selection["pattern_summary"],
        selected_claim_fingerprints=list(selection["selected_claim_fingerprints"]),
        selected_risk_fingerprints=list(selection["selected_risk_fingerprints"]),
        hypothesis=selection["hypothesis"],
        expected_gain=selection["expected_gain"],
        sovereign_consumer_kind=selection["sovereign_consumer_kind"],
        sovereign_consumer_ref=selection["sovereign_consumer_ref"],
        consumer_contract_ref=selection["consumer_contract_ref"],
        bounded_integration_seam=selection["bounded_integration_seam"],
        target_gap_refs=list(selection["target_gap_refs"]),
        baseline_definition_ref=selection["baseline_definition_ref"],
        baseline_definition_hash=selection["baseline_definition_hash"],
        candidate_definition_ref=selection["candidate_definition_ref"],
        candidate_definition_hash=selection["candidate_definition_hash"],
        isolation_profile_ref=selection["isolation_profile_ref"],
        risk_control_refs=list(selection["risk_control_refs"]),
        mitigation_refs=list(selection["mitigation_refs"]),
        stop_condition_refs=list(selection["stop_condition_refs"]),
        license_id=intake.license_id,
        license_status=intake.license_status,
        license_evidence_ref=intake.license_evidence_ref,
        rollback_plan_ref=selection["rollback_plan_ref"],
        rollback_steps=list(selection["rollback_steps"]),
        rollback_verification_refs=list(selection["rollback_verification_refs"]),
        selection_review_ref=selection["selection_review_ref"],
        selected_by_ref=selection["selected_by_ref"],
        cases=cases,
        required_pass_rate=float(selection["required_pass_rate"]),
        evidence_refs=list(selection["evidence_refs"]),
        generated_at=selection["generated_at"],
    )
    return require_valid_technology_experiment_pack(pack, intake=intake)


def register_technology_experiment_pack(
    pack: TechnologyExperimentPackContract,
    *,
    intake: TechnologyRadarIntakeContract,
    evolution_service: object,
) -> TechnologyExperimentRegistrationResult:
    """Persist one fully verified pack without creating a generic proposal."""

    verified = require_valid_technology_experiment_pack(pack, intake=intake)
    recorded = _call_service_method(
        evolution_service,
        "register_technology_experiment_pack",
        verified,
    )
    expected_fingerprint = technology_experiment_pack_fingerprint(verified)
    if (
        recorded != verified
        or technology_experiment_pack_fingerprint(recorded) != expected_fingerprint
    ):
        raise RuntimeError("technology experiment pack persistence parity failed")
    return TechnologyExperimentRegistrationResult(
        pack=recorded,
        pack_fingerprint=expected_fingerprint,
    )


def register_technology_experiment_pack_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    intake_reader: object,
    evolution_service: object,
) -> TechnologyExperimentRegistrationResult:
    """Convenience seam for callers that construct the writer after validation."""

    pack = assess_technology_experiment_pack_manifest(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
        intake_reader=intake_reader,
    )
    intake = _get_exact_intake(
        intake_reader,
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
    )
    return register_technology_experiment_pack(
        pack,
        intake=intake,
        evolution_service=evolution_service,
    )


def load_technology_experiment_eval_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    max_bytes: int = MAX_TECHNOLOGY_EXPERIMENT_EVAL_MANIFEST_BYTES,
) -> dict[str, Any]:
    """Load run identity only; observations and all metrics come from the pack."""

    payload = _load_local_manifest_payload(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
        max_bytes=max_bytes,
        manifest_label="technology experiment eval manifest",
    )
    _reject_dangerous_manifest_content(
        payload,
        manifest_label="technology experiment eval manifest",
        reject_derived_keys=True,
    )
    _require_exact_fields(
        payload,
        expected_fields=set(_EVAL_MANIFEST_FIELDS),
        manifest_label="technology experiment eval manifest",
    )
    for field_name in ("run_id", "experiment_pack_id", "generated_at"):
        _require_nonempty_text(payload[field_name], field_name=field_name)
    if parse_canonical_semver(
        _require_nonempty_text(payload["pack_version"], field_name="pack_version")
    ) is None:
        raise ValueError("technology experiment eval pack_version is invalid")
    _require_sha256(payload["pack_fingerprint"], field_name="pack_fingerprint")
    return payload


def prepare_technology_experiment_eval_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    pack_reader: object,
) -> tuple[
    TechnologyExperimentPackContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentEvalRunContract,
]:
    """Derive a claim and run from verified pre-produced paired observations."""

    payload = load_technology_experiment_eval_manifest(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    pack = _get_exact_pack(
        pack_reader,
        experiment_pack_id=payload["experiment_pack_id"],
        pack_version=payload["pack_version"],
    )
    intake = _get_exact_intake(
        pack_reader,
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
    )
    require_valid_technology_experiment_pack(pack, intake=intake)
    expected_pack_fingerprint = technology_experiment_pack_fingerprint(pack)
    if payload["pack_fingerprint"] != expected_pack_fingerprint:
        raise ValueError("technology experiment eval pack fingerprint mismatch")
    run = derive_technology_experiment_eval_run(
        run_id=payload["run_id"],
        pack=pack,
        intake=intake,
        generated_at=payload["generated_at"],
    )
    require_valid_technology_experiment_eval_run(run, pack=pack, intake=intake)
    claim = TechnologyExperimentEvalRunClaimContract(
        run_id=run.run_id,
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=expected_pack_fingerprint,
        intake_id=pack.intake_id,
        intake_fingerprint=pack.intake_fingerprint,
        input_fingerprint=run.input_fingerprint,
        control_fingerprint=run.control_fingerprint,
        claimed_at=payload["generated_at"],
    )
    claim_blockers = validate_technology_experiment_eval_run_claim(claim, pack=pack)
    if claim_blockers:
        raise ValueError(
            "technology experiment eval claim is invalid: " + "; ".join(claim_blockers)
        )
    return pack, claim, run


def record_technology_experiment_eval(
    *,
    pack: TechnologyExperimentPackContract,
    claim: TechnologyExperimentEvalRunClaimContract,
    run: TechnologyExperimentEvalRunContract,
    evolution_service: object,
) -> TechnologyExperimentEvalRunContract:
    """Atomically reserve then append one independently derived evaluation."""

    intake = _get_exact_intake(
        evolution_service,
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
    )
    require_valid_technology_experiment_pack(pack, intake=intake)
    require_valid_technology_experiment_eval_run(
        run,
        pack=pack,
        intake=intake,
    )
    claim_created = _call_service_method(
        evolution_service,
        "claim_technology_experiment_eval_run",
        claim,
    )
    if not claim_created:
        existing = _get_exact_eval_run(evolution_service, run_id=run.run_id)
        if existing is not None:
            if existing != run:
                raise ValueError("technology experiment eval run collision")
            return existing
    recorded = _call_service_method(
        evolution_service,
        "record_technology_experiment_eval_run",
        run,
    )
    if recorded != run:
        raise RuntimeError("technology experiment eval persistence parity failed")
    return recorded


def run_technology_experiment_eval_manifest(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    pack_reader: object,
    evolution_service: object,
) -> TechnologyExperimentEvalRunContract:
    """Evaluate inert observations only; never invoke the candidate or Core."""

    pack, claim, run = prepare_technology_experiment_eval_manifest(
        manifest_path,
        manifest_root=manifest_root,
        expected_manifest_sha256=expected_manifest_sha256,
        pack_reader=pack_reader,
    )
    return record_technology_experiment_eval(
        pack=pack,
        claim=claim,
        run=run,
        evolution_service=evolution_service,
    )


def _load_local_manifest_payload(
    manifest_path: str | Path,
    *,
    manifest_root: str | Path,
    expected_manifest_sha256: str,
    max_bytes: int,
    manifest_label: str,
) -> dict[str, Any]:
    """Read one bounded regular file without following a caller-controlled link."""

    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError(f"{manifest_label} max_bytes must be positive")
    if not isinstance(expected_manifest_sha256, str) or fullmatch(
        _SHA256_PATTERN, expected_manifest_sha256
    ) is None:
        raise ValueError(f"{manifest_label} SHA-256 must be canonical")

    _reject_remote_or_device_path(manifest_root, field_name="manifest root")
    _reject_remote_or_device_path(manifest_path, field_name="manifest")
    root = Path(manifest_root).expanduser()
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ValueError(f"{manifest_label} root must be a real local directory")
    _reject_symlinked_root(root.absolute())
    resolved_root = root.resolve(strict=True)
    try:
        root_before = resolved_root.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"{manifest_label} root metadata is unavailable") from exc

    requested = Path(manifest_path).expanduser()
    _reject_lexical_traversal_or_stream(manifest_path, field_name="manifest")
    candidate = requested if requested.is_absolute() else resolved_root / requested
    if candidate.is_symlink():
        raise ValueError(f"{manifest_label} symlinks are not allowed")
    try:
        resolved_manifest = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"{manifest_label} is unavailable") from exc
    if not resolved_manifest.is_relative_to(resolved_root):
        raise ValueError(f"{manifest_label} must remain inside manifest root")
    _reject_symlinked_path(lexical_path=candidate.absolute(), resolved_root=resolved_root)

    try:
        before = resolved_manifest.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"{manifest_label} metadata is unavailable") from exc
    if not S_ISREG(before.st_mode):
        raise ValueError(f"{manifest_label} must be a regular file")
    if before.st_size < 1 or before.st_size > max_bytes:
        raise ValueError(f"{manifest_label} size is outside the allowed bound")
    if getattr(before, "st_nlink", 1) != 1:
        raise ValueError(f"{manifest_label} hard links are not allowed")

    try:
        with resolved_manifest.open("rb") as stream:
            opened = fstat(stream.fileno())
            _require_same_file(before, opened, manifest_label=manifest_label)
            raw = _read_bounded(stream, max_bytes=max_bytes)
            after_read = fstat(stream.fileno())
            _require_same_file(opened, after_read, manifest_label=manifest_label)
            # Metadata alone can miss same-size writes on coarse clocks.
            stream.seek(0)
            verified_raw = _read_bounded(stream, max_bytes=max_bytes)
            _require_same_file(opened, fstat(stream.fileno()), manifest_label=manifest_label)
            if raw != verified_raw:
                raise ValueError(f"{manifest_label} changed while being read")
    except OSError as exc:
        raise ValueError(f"{manifest_label} cannot be read") from exc

    try:
        after = resolved_manifest.stat(follow_symlinks=False)
        root_after = resolved_root.stat(follow_symlinks=False)
    except OSError as exc:
        raise ValueError(f"{manifest_label} changed while being read") from exc
    _require_same_file(before, after, manifest_label=manifest_label)
    _require_same_file(root_before, root_after, manifest_label=f"{manifest_label} root")
    if len(raw) != before.st_size:
        raise ValueError(f"{manifest_label} changed while being read")
    if sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError(f"{manifest_label} SHA-256 mismatch")

    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{manifest_label} must be UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError(f"{manifest_label} must not contain a UTF-8 BOM")
    payload = _load_strict_json_object(text, manifest_label=manifest_label)
    _reject_dangerous_manifest_content(payload, manifest_label=manifest_label)
    return payload


def _validate_pack_selection_payload(payload: Mapping[str, Any]) -> None:
    label = "technology experiment pack manifest"
    _require_exact_fields(
        payload,
        expected_fields=set(_PACK_SELECTION_REQUIRED_FIELDS),
        manifest_label=label,
    )
    text_fields = (
        "experiment_pack_id",
        "intake_id",
        "translation_kind",
        "pattern_id",
        "pattern_name",
        "pattern_summary",
        "hypothesis",
        "expected_gain",
        "sovereign_consumer_kind",
        "sovereign_consumer_ref",
        "consumer_contract_ref",
        "bounded_integration_seam",
        "baseline_definition_ref",
        "candidate_definition_ref",
        "isolation_profile_ref",
        "rollback_plan_ref",
        "selection_review_ref",
        "selected_by_ref",
        "generated_at",
    )
    for field_name in text_fields:
        _require_nonempty_text(payload[field_name], field_name=field_name)
    for field_name in ("pack_version", "intake_version"):
        value = _require_nonempty_text(payload[field_name], field_name=field_name)
        if parse_canonical_semver(value) is None:
            raise ValueError(f"technology experiment {field_name} must be canonical semver")
    for field_name in (
        "intake_fingerprint",
        "baseline_definition_hash",
        "candidate_definition_hash",
    ):
        _require_sha256(payload[field_name], field_name=field_name)
    if payload["translation_kind"] != "absorbable_pattern":
        raise ValueError("technology experiment translation_kind must remain absorbable")
    if payload["isolation_profile_ref"] != TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE:
        raise ValueError("technology experiment requires the canonical isolation profile")
    list_fields = (
        "selected_claim_fingerprints",
        "selected_risk_fingerprints",
        "target_gap_refs",
        "risk_control_refs",
        "mitigation_refs",
        "stop_condition_refs",
        "rollback_steps",
        "rollback_verification_refs",
        "evidence_refs",
    )
    for field_name in list_fields:
        values = _require_string_list(payload[field_name], field_name=field_name)
        if field_name in {
            "selected_claim_fingerprints",
            "selected_risk_fingerprints",
        }:
            for value in values:
                _require_sha256(value, field_name=field_name)
    _require_rate(payload["required_pass_rate"], field_name="required_pass_rate")
    cases = payload["cases"]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 32:
        raise ValueError("technology experiment cases must be a bounded list")
    case_identities: list[tuple[str, str]] = []
    for raw_case in cases:
        if not isinstance(raw_case, Mapping):
            raise ValueError("technology experiment cases must be objects")
        _validate_case_payload(raw_case)
        case_identities.append((raw_case["case_id"], raw_case["case_version"]))
    if len(case_identities) != len(set(case_identities)):
        raise ValueError("technology experiment cases contain duplicate identities")


def _validate_case_payload(payload: Mapping[str, Any]) -> None:
    _require_exact_fields_with_optional(
        payload,
        required_fields=set(_CASE_REQUIRED_FIELDS),
        optional_fields={"limitations"},
        manifest_label="technology experiment case",
    )
    for field_name in (
        "case_id",
        "scenario_ref",
        "baseline_definition_ref",
        "candidate_definition_ref",
    ):
        _require_nonempty_text(payload[field_name], field_name=field_name)
    if parse_canonical_semver(
        _require_nonempty_text(payload["case_version"], field_name="case_version")
    ) is None:
        raise ValueError("technology experiment case_version must be canonical semver")
    for field_name in (
        "input_fingerprint",
        "baseline_definition_hash",
        "candidate_definition_hash",
    ):
        _require_sha256(payload[field_name], field_name=field_name)
    for field_name in (
        "critical_contract_check_refs",
        "critical_isolation_check_refs",
        "success_criteria_refs",
        "evidence_refs",
    ):
        _require_string_list(payload[field_name], field_name=field_name)
    if "limitations" in payload:
        _require_string_list(
            payload["limitations"],
            field_name="limitations",
            minimum=0,
        )
    control = payload["control_snapshot"]
    if not isinstance(control, Mapping):
        raise ValueError("technology experiment control snapshot must be an object")
    _validate_control_payload(control)
    for arm in ("baseline", "candidate"):
        observation = payload[f"{arm}_observation"]
        if not isinstance(observation, Mapping):
            raise ValueError("technology experiment observation must be an object")
        _validate_observation_payload(observation, expected_arm=arm)


def _validate_control_payload(payload: Mapping[str, Any]) -> None:
    _require_exact_fields(
        payload,
        expected_fields=set(_CONTROL_REQUIRED_FIELDS),
        manifest_label="technology experiment control snapshot",
    )
    for field_name in (
        "control_snapshot_id",
        "sandbox_policy_ref",
        "sandbox_policy_version",
        "evaluator_version",
        "fixed_clock",
        "isolation_profile_ref",
    ):
        _require_nonempty_text(payload[field_name], field_name=field_name)
    for field_name in (
        "input_fingerprint",
        "isolation_fingerprint",
        "environment_fingerprint",
    ):
        _require_sha256(payload[field_name], field_name=field_name)
    if payload["isolation_profile_ref"] != TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE:
        raise ValueError("technology experiment control isolation profile mismatch")
    seed = payload["deterministic_seed"]
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("technology experiment deterministic_seed is invalid")


def _validate_observation_payload(
    payload: Mapping[str, Any],
    *,
    expected_arm: str,
) -> None:
    _require_exact_fields(
        payload,
        expected_fields=set(_OBSERVATION_REQUIRED_FIELDS),
        manifest_label="technology experiment observation",
    )
    for field_name in (
        "observation_id",
        "case_id",
        "definition_ref",
        "control_snapshot_id",
        "outcome_ref",
        "outcome_status",
        "observed_at",
    ):
        _require_nonempty_text(payload[field_name], field_name=field_name)
    if parse_canonical_semver(
        _require_nonempty_text(payload["case_version"], field_name="case_version")
    ) is None:
        raise ValueError("technology experiment observation case_version is invalid")
    if payload["arm"] != expected_arm:
        raise ValueError("technology experiment observation arm mismatch")
    for field_name in (
        "definition_hash",
        "input_fingerprint",
        "control_snapshot_fingerprint",
    ):
        _require_sha256(payload[field_name], field_name=field_name)
    for field_name in (
        "contract_checks",
        "isolation_checks",
        "success_criteria_results",
    ):
        _require_bool_mapping(payload[field_name], field_name=field_name)
    action_count = payload["action_count"]
    rework_count = payload["rework_count"]
    if type(action_count) is not int or not 1 <= action_count <= 1_000_000:
        raise ValueError("technology experiment action_count is invalid")
    if type(rework_count) is not int or not 0 <= rework_count <= action_count:
        raise ValueError("technology experiment rework_count is invalid")
    _require_string_list(payload["evidence_refs"], field_name="evidence_refs", minimum=2)
    _require_string_list(payload["limitations"], field_name="limitations", minimum=0)


def _build_experiment_case(
    payload: Mapping[str, Any],
    *,
    experiment_pack_id: str,
    pack_version: str,
    baseline_definition_ref: str,
    baseline_definition_hash: str,
    candidate_definition_ref: str,
    candidate_definition_hash: str,
    isolation_profile_ref: str,
) -> TechnologyExperimentCaseContract:
    control = TechnologyExperimentControlSnapshotContract(**payload["control_snapshot"])
    if control.isolation_profile_ref != isolation_profile_ref:
        raise ValueError("technology experiment pack/control isolation mismatch")
    observations: dict[str, TechnologyExperimentObservationContract] = {}
    for arm, definition_ref, definition_hash in (
        ("baseline", baseline_definition_ref, baseline_definition_hash),
        ("candidate", candidate_definition_ref, candidate_definition_hash),
    ):
        raw = payload[f"{arm}_observation"]
        observation = TechnologyExperimentObservationContract(
            experiment_pack_id=experiment_pack_id,
            pack_version=pack_version,
            **raw,
        )
        if (
            observation.case_id != payload["case_id"]
            or observation.case_version != payload["case_version"]
            or observation.definition_ref != definition_ref
            or observation.definition_hash != definition_hash
            or observation.input_fingerprint != payload["input_fingerprint"]
            or observation.control_snapshot_id != control.control_snapshot_id
        ):
            raise ValueError("technology experiment observation scope mismatch")
        observations[arm] = observation
    if (
        payload["baseline_definition_ref"] != baseline_definition_ref
        or payload["baseline_definition_hash"] != baseline_definition_hash
        or payload["candidate_definition_ref"] != candidate_definition_ref
        or payload["candidate_definition_hash"] != candidate_definition_hash
        or payload["input_fingerprint"] != control.input_fingerprint
    ):
        raise ValueError("technology experiment case definition/control mismatch")
    return TechnologyExperimentCaseContract(
        experiment_pack_id=experiment_pack_id,
        pack_version=pack_version,
        case_id=payload["case_id"],
        case_version=payload["case_version"],
        scenario_ref=payload["scenario_ref"],
        input_fingerprint=payload["input_fingerprint"],
        baseline_definition_ref=baseline_definition_ref,
        baseline_definition_hash=baseline_definition_hash,
        candidate_definition_ref=candidate_definition_ref,
        candidate_definition_hash=candidate_definition_hash,
        critical_contract_check_refs=list(payload["critical_contract_check_refs"]),
        critical_isolation_check_refs=list(payload["critical_isolation_check_refs"]),
        success_criteria_refs=list(payload["success_criteria_refs"]),
        control_snapshot=control,
        baseline_observation=observations["baseline"],
        candidate_observation=observations["candidate"],
        evidence_refs=list(payload["evidence_refs"]),
        limitations=list(payload.get("limitations", [])),
    )


def _read_bounded(stream: BinaryIO, *, max_bytes: int) -> bytes:
    raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("technology experiment manifest exceeds the bounded size limit")
    return raw


def _require_same_file(before: Any, after: Any, *, manifest_label: str) -> None:
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_size,
        getattr(before, "st_mtime_ns", None),
        getattr(before, "st_nlink", None),
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_size,
        getattr(after, "st_mtime_ns", None),
        getattr(after, "st_nlink", None),
    )
    if identity_before != identity_after:
        raise ValueError(f"{manifest_label} changed while being read")


def _load_strict_json_object(text: str, *, manifest_label: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{manifest_label} has a duplicate key")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        del value
        raise ValueError(f"{manifest_label} has a non-finite value")

    try:
        payload = loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except JSONDecodeError as exc:
        raise ValueError(f"{manifest_label} is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{manifest_label} root must be an object")
    return payload


def _reject_dangerous_manifest_content(
    payload: Mapping[str, Any],
    *,
    manifest_label: str,
    reject_derived_keys: bool = False,
) -> None:
    for key, value in _walk_mapping(payload):
        normalized_key = key.strip().casefold().replace("-", "_")
        key_tokens = set(normalized_key.split("_"))
        is_canonical_boolean_check = (
            normalized_key in _CANONICAL_BOOLEAN_CHECK_KEYS_WITH_FORBIDDEN_TOKENS
            and isinstance(value, bool)
        )
        if not is_canonical_boolean_check and (
            normalized_key in _FORBIDDEN_MANIFEST_KEYS
            or key_tokens.intersection(_FORBIDDEN_MANIFEST_KEYS)
        ):
            raise ValueError(f"{manifest_label} contains a forbidden field")
        if reject_derived_keys and normalized_key in _FORBIDDEN_CALLER_DERIVED_KEYS:
            raise ValueError(f"{manifest_label} contains a caller-derived field")
        if normalized_key in _SENSITIVE_FIELD_NAMES:
            raise ValueError(f"{manifest_label} contains a sensitive field")
        if isinstance(value, str) and _contains_sensitive_material(value):
            raise ValueError(f"{manifest_label} contains sensitive material")
        if isinstance(value, str) and _has_control_character(value):
            raise ValueError(f"{manifest_label} contains a control character")


def _walk_mapping(payload: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    for key, value in payload.items():
        if not isinstance(key, str) or not key or key != key.strip():
            raise ValueError("technology experiment manifest keys must be canonical text")
        yield key, value
        if isinstance(value, Mapping):
            yield from _walk_mapping(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    yield from _walk_mapping(item)
                elif isinstance(item, list):
                    yield from _walk_list(key, item)
                else:
                    yield key, item


def _walk_list(parent_key: str, values: list[Any]) -> Iterable[tuple[str, Any]]:
    for value in values:
        if isinstance(value, Mapping):
            yield from _walk_mapping(value)
        elif isinstance(value, list):
            yield from _walk_list(parent_key, value)
        else:
            yield parent_key, value


def _contains_sensitive_material(value: str) -> bool:
    return bool(
        _SENSITIVE_ASSIGNMENT.search(value)
        or _BEARER_TOKEN.search(value)
        or _AUTHENTICATED_URL.search(value)
        or _PRIVATE_PATH.search(value)
        or _PRIVATE_KEY_BLOCK.search(value)
        or _STANDALONE_CREDENTIAL.search(value)
    )


def _reject_symlinked_path(*, lexical_path: Path, resolved_root: Path) -> None:
    try:
        relative = lexical_path.relative_to(resolved_root)
    except ValueError:
        return
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("technology experiment manifest path cannot traverse symlinks")


def _reject_symlinked_root(root: Path) -> None:
    current = Path(root.anchor)
    for part in root.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise ValueError("technology experiment manifest root cannot traverse symlinks")


def _reject_lexical_traversal_or_stream(
    value: str | Path,
    *,
    field_name: str,
) -> None:
    lexical = str(value).replace("\\", "/")
    without_drive = lexical[2:] if fullmatch(r"[A-Za-z]:.*", lexical) else lexical
    segments = without_drive.split("/")
    if any(segment in {".", ".."} for segment in segments) or any(
        ":" in segment or segment.endswith((" ", ".")) for segment in segments
    ):
        raise ValueError(
            f"technology experiment {field_name} must not use traversal or streams"
        )


def _reject_remote_or_device_path(value: str | Path, *, field_name: str) -> None:
    lexical = str(value).replace("/", "\\")
    lowered = lexical.casefold()
    if lexical.startswith("\\\\") or lowered.startswith(
        ("\\\\?\\", "\\\\.\\", "\\??\\", "\\globalroot\\")
    ):
        raise ValueError(
            f"technology experiment {field_name} must be a local non-device path"
        )


def _require_exact_fields(
    payload: Mapping[str, Any],
    *,
    expected_fields: set[str],
    manifest_label: str,
) -> None:
    supplied = set(payload)
    missing = sorted(expected_fields - supplied)
    unknown = sorted(supplied - expected_fields)
    if missing or unknown:
        raise ValueError(
            f"{manifest_label} schema mismatch: missing={missing},"
            f"unknown_field_count={len(unknown)}"
        )


def _require_exact_fields_with_optional(
    payload: Mapping[str, Any],
    *,
    required_fields: set[str],
    optional_fields: set[str],
    manifest_label: str,
) -> None:
    supplied = set(payload)
    missing = sorted(required_fields - supplied)
    unknown = sorted(supplied - required_fields - optional_fields)
    if missing or unknown:
        raise ValueError(
            f"{manifest_label} schema mismatch: missing={missing},"
            f"unknown_field_count={len(unknown)}"
        )


def _require_exact_bool(value: object, *, field_name: str, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        raise ValueError(f"technology experiment {field_name} must be {expected}")


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or fullmatch(_SHA256_PATTERN, value) is None:
        raise ValueError(f"technology experiment {field_name} must be canonical SHA-256")
    return value


def _require_rate(value: object, *, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"technology experiment {field_name} must be a number")
    resolved = float(value)
    if not 0.0 < resolved <= 1.0:
        raise ValueError(f"technology experiment {field_name} is outside its bound")
    return resolved


def _require_bool_mapping(value: object, *, field_name: str) -> dict[str, bool]:
    if not isinstance(value, dict) or not 1 <= len(value) <= 100:
        raise ValueError(f"technology experiment {field_name} must be a bounded object")
    result: dict[str, bool] = {}
    for key, item in value.items():
        canonical_key = _require_nonempty_text(key, field_name=field_name, max_length=500)
        if type(item) is not bool:
            raise ValueError(f"technology experiment {field_name} values must be booleans")
        result[canonical_key] = item
    return result


def _require_nonempty_text(value: object, *, field_name: str, max_length: int = 1000) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
        or _has_control_character(value)
    ):
        raise ValueError(f"technology experiment {field_name} must be bounded text")
    return value


def _require_string_list(
    value: object,
    *,
    field_name: str,
    minimum: int = 1,
    maximum: int = 32,
) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"technology experiment {field_name} must be a bounded list")
    result = [_require_nonempty_text(item, field_name=field_name) for item in value]
    if len({normalize("NFKC", item).casefold() for item in result}) != len(result):
        raise ValueError(f"technology experiment {field_name} contains duplicates")
    return result


def _has_control_character(value: str) -> bool:
    return any(category(character) in {"Cc", "Cf"} for character in value)


def _attested_text_fingerprint(value: str) -> str:
    return technology_experiment_text_fingerprint(value)


def _require_selected_text_fingerprints(
    selected: object,
    *,
    source_values: list[str],
    field_name: str,
) -> None:
    selected_values = _require_string_list(selected, field_name=field_name)
    expected = {_attested_text_fingerprint(value) for value in source_values}
    if not set(selected_values).issubset(expected):
        raise ValueError(f"technology experiment {field_name} exceeds reviewed intake")


def _get_exact_intake(
    reader: object,
    *,
    intake_id: str,
    intake_version: str,
) -> TechnologyRadarIntakeContract:
    method = getattr(reader, "get_technology_radar_intake", None)
    if not isinstance(method, Callable):
        raise TypeError("intake reader does not implement get_technology_radar_intake")
    intake = method(intake_id=intake_id, intake_version=intake_version)
    if not isinstance(intake, TechnologyRadarIntakeContract):
        raise ValueError("technology experiment requires an exact persisted intake")
    return intake


def _get_exact_pack(
    reader: object,
    *,
    experiment_pack_id: str,
    pack_version: str,
) -> TechnologyExperimentPackContract:
    method = getattr(reader, "get_technology_experiment_pack", None)
    if not isinstance(method, Callable):
        raise TypeError("pack reader does not implement get_technology_experiment_pack")
    pack = method(
        experiment_pack_id=experiment_pack_id,
        pack_version=pack_version,
    )
    if not isinstance(pack, TechnologyExperimentPackContract):
        raise ValueError("technology experiment requires an exact persisted pack")
    intake = _get_exact_intake(
        reader,
        intake_id=pack.intake_id,
        intake_version=pack.intake_version,
    )
    return require_valid_technology_experiment_pack(pack, intake=intake)


def _get_exact_eval_run(
    reader: object,
    *,
    run_id: str,
) -> TechnologyExperimentEvalRunContract | None:
    method = getattr(reader, "get_technology_experiment_eval_run", None)
    if not isinstance(method, Callable):
        raise TypeError(
            "eval reader does not implement get_technology_experiment_eval_run"
        )
    run = method(run_id=run_id)
    if run is not None and not isinstance(run, TechnologyExperimentEvalRunContract):
        raise RuntimeError("technology experiment eval store returned an invalid run")
    return run


def _call_service_method(
    service: object,
    method_name: str,
    argument: _T,
) -> Any:
    """Keep service integration explicit while allowing narrow test doubles."""

    method = getattr(service, method_name, None)
    if not isinstance(method, Callable):
        raise TypeError(f"Evolution service does not implement {method_name}")
    return method(argument)
