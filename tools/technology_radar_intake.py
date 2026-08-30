"""Strict local-manifest intake for reviewed technology radar references."""

from __future__ import annotations

from dataclasses import dataclass, fields
from hashlib import sha256
from json import JSONDecodeError, loads
from pathlib import Path
from re import fullmatch
from typing import Any

from evolution_lab.service import EvolutionLabService
from knowledge_service.service import (
    KnowledgeService,
    TechnologyRadarIntakeAssessment,
)

from shared.contracts import TechnologyRadarIntakeContract
from shared.technology_radar_intake import (
    require_valid_technology_radar_intake,
    technology_radar_intake_fingerprint,
)

MAX_TECHNOLOGY_RADAR_MANIFEST_BYTES = 65_536


@dataclass(frozen=True)
class TechnologyRadarIntakeRegistrationResult:
    """Verified result of one manual, local and non-authoritative intake."""

    intake: TechnologyRadarIntakeContract
    assessment: TechnologyRadarIntakeAssessment
    intake_fingerprint: str
    persistence_status: str = "recorded_or_exact_retry"
    source_trusted: bool = False
    network_fetch_performed: bool = False
    knowledge_ingestion_performed: bool = False
    evolution_proposal_created: bool = False
    dependency_installation_performed: bool = False
    execution_performed: bool = False
    runtime_activation_performed: bool = False
    promotion_performed: bool = False
    core_mutation_performed: bool = False
    priority_mutation_performed: bool = False


def load_technology_radar_intake_manifest(
    manifest_path: str | Path,
    *,
    intake_root: str | Path,
    expected_manifest_sha256: str | None = None,
    max_bytes: int = MAX_TECHNOLOGY_RADAR_MANIFEST_BYTES,
) -> TechnologyRadarIntakeContract:
    """Load one bounded JSON manifest from an explicitly approved local root."""

    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("technology radar manifest max_bytes must be positive")
    _reject_remote_or_device_path(intake_root, field_name="intake root")
    _reject_remote_or_device_path(manifest_path, field_name="manifest")
    root = Path(intake_root).expanduser()
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ValueError("technology radar intake root must be a real local directory")
    resolved_root = root.resolve(strict=True)
    requested = Path(manifest_path).expanduser()
    candidate = requested if requested.is_absolute() else resolved_root / requested
    if candidate.is_symlink():
        raise ValueError("technology radar manifest symlinks are not allowed")
    try:
        resolved_manifest = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("technology radar manifest is unavailable") from exc
    if not resolved_manifest.is_relative_to(resolved_root):
        raise ValueError("technology radar manifest must remain inside intake root")
    _reject_symlinked_manifest_path(
        lexical_path=candidate.absolute(),
        resolved_root=resolved_root,
    )
    if not resolved_manifest.is_file():
        raise ValueError("technology radar manifest must be a regular file")
    try:
        size = resolved_manifest.stat().st_size
    except OSError as exc:
        raise ValueError("technology radar manifest metadata is unavailable") from exc
    if size < 1 or size > max_bytes:
        raise ValueError("technology radar manifest size is outside the allowed bound")
    try:
        raw = resolved_manifest.read_bytes()
    except OSError as exc:
        raise ValueError("technology radar manifest cannot be read") from exc
    if len(raw) != size or len(raw) > max_bytes:
        raise ValueError("technology radar manifest changed while being read")
    if expected_manifest_sha256 is not None:
        if (
            not isinstance(expected_manifest_sha256, str)
            or fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256) is None
        ):
            raise ValueError("technology radar manifest SHA-256 must be canonical")
        if sha256(raw).hexdigest() != expected_manifest_sha256:
            raise ValueError("technology radar manifest SHA-256 mismatch")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("technology radar manifest must be UTF-8") from exc
    payload = _load_strict_json_object(text)
    expected_fields = {field.name for field in fields(TechnologyRadarIntakeContract)}
    supplied_fields = set(payload)
    missing = sorted(expected_fields - supplied_fields)
    unknown = sorted(supplied_fields - expected_fields)
    if missing or unknown:
        raise ValueError(
            "technology radar manifest schema mismatch: "
            f"missing={missing},unknown_field_count={len(unknown)}"
        )
    try:
        intake = TechnologyRadarIntakeContract(**payload)
    except TypeError as exc:
        raise ValueError("technology radar manifest has invalid field types") from exc
    return require_valid_technology_radar_intake(intake)


def register_technology_radar_intake_manifest(
    manifest_path: str | Path,
    *,
    intake_root: str | Path,
    expected_manifest_sha256: str,
    evolution_service: EvolutionLabService,
    knowledge_service: KnowledgeService,
) -> TechnologyRadarIntakeRegistrationResult:
    """Assess and append one reviewed reference without fetching or activating it."""

    intake, assessment = assess_technology_radar_intake_manifest(
        manifest_path,
        intake_root=intake_root,
        expected_manifest_sha256=expected_manifest_sha256,
        knowledge_service=knowledge_service,
    )
    return register_technology_radar_intake(
        intake,
        assessment=assessment,
        evolution_service=evolution_service,
    )


def assess_technology_radar_intake_manifest(
    manifest_path: str | Path,
    *,
    intake_root: str | Path,
    expected_manifest_sha256: str,
    knowledge_service: KnowledgeService,
) -> tuple[TechnologyRadarIntakeContract, TechnologyRadarIntakeAssessment]:
    """Validate and assess a manifest before any writer is constructed."""

    intake = load_technology_radar_intake_manifest(
        manifest_path,
        intake_root=intake_root,
        expected_manifest_sha256=expected_manifest_sha256,
    )
    assessment = knowledge_service.assess_technology_radar_intake(intake)
    if (
        assessment.status != "eligible_for_reviewed_registry"
        or assessment.eligible_for_reviewed_registry is not True
        or assessment.registry_write_authorized is not False
        or assessment.blockers
    ):
        raise ValueError(
            "technology radar intake assessment blocked: "
            + ",".join(assessment.blockers or [assessment.status])
        )
    return intake, assessment


def register_technology_radar_intake(
    intake: TechnologyRadarIntakeContract,
    *,
    assessment: TechnologyRadarIntakeAssessment,
    evolution_service: EvolutionLabService,
) -> TechnologyRadarIntakeRegistrationResult:
    """Append a prevalidated intake after exact assessment parity checks."""

    expected_fingerprint = technology_radar_intake_fingerprint(intake)
    if (
        assessment.intake_id != intake.intake_id
        or assessment.intake_version != intake.intake_version
        or assessment.intake_fingerprint != expected_fingerprint
        or assessment.status != "eligible_for_reviewed_registry"
        or assessment.eligible_for_reviewed_registry is not True
        or assessment.registry_write_authorized is not False
        or assessment.blockers
    ):
        raise ValueError("technology radar intake assessment parity failed")
    recorded = evolution_service.register_technology_radar_intake(intake)
    if (
        recorded != intake
        or technology_radar_intake_fingerprint(recorded) != expected_fingerprint
    ):
        raise RuntimeError("technology radar intake persistence parity failed")
    return TechnologyRadarIntakeRegistrationResult(
        intake=recorded,
        assessment=assessment,
        intake_fingerprint=expected_fingerprint,
    )


def _load_strict_json_object(text: str) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("technology radar manifest has a duplicate key")
            result[key] = value
        return result

    def reject_non_finite(value: str) -> None:
        del value
        raise ValueError("technology radar manifest has a non-finite value")

    try:
        payload = loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except JSONDecodeError as exc:
        raise ValueError("technology radar manifest is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("technology radar manifest root must be an object")
    return payload


def _reject_symlinked_manifest_path(
    *,
    lexical_path: Path,
    resolved_root: Path,
) -> None:
    try:
        relative = lexical_path.relative_to(resolved_root)
    except ValueError:
        return
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("technology radar manifest path cannot traverse symlinks")


def _reject_remote_or_device_path(
    value: str | Path,
    *,
    field_name: str,
) -> None:
    lexical = str(value).replace("/", "\\")
    lowered = lexical.lower()
    if lexical.startswith("\\\\") or lowered.startswith(
        ("\\\\?\\", "\\\\.\\", "\\??\\", "\\globalroot\\")
    ):
        raise ValueError(
            f"technology radar {field_name} must be a local non-device path"
        )
