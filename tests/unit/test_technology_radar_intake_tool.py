from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
from json import dumps
from pathlib import Path

import pytest
from evolution_lab.service import EvolutionLabService
from knowledge_service.service import KnowledgeService

from shared.contracts import TechnologyRadarIntakeContract
from shared.technology_radar_intake import (
    technology_radar_review_subject_fingerprint,
)
from tools.technology_radar_intake import (
    assess_technology_radar_intake_manifest,
    load_technology_radar_intake_manifest,
    register_technology_radar_intake_manifest,
)


def _intake() -> TechnologyRadarIntakeContract:
    provisional = TechnologyRadarIntakeContract(
        intake_id="technology-intake://openai-agents-sdk/1.0.0",
        candidate_ref="technology-candidate://openai-agents-sdk",
        intake_version="1.0.0",
        technology_name="OpenAI Agents SDK",
        source_kind="repository",
        source_locator="https://github.com/openai/openai-agents-python",
        source_version_ref="git-commit://openai-agents-python/0123456789abcdef",
        source_content_sha256="1" * 64,
        license_id="MIT",
        license_status="declared",
        license_evidence_ref="license-evidence://openai-agents-sdk/mit",
        retrieved_at="2026-08-12T10:00:00Z",
        claims=["Typed handoffs can improve bounded edge orchestration."],
        risks=["A foreign runtime must not replace the sovereign Core."],
        absorption_class="reference",
        target_gap_refs=["KNW-006"],
        research_approval_ref="research-approval://technology-radar/2026-08-12",
        reviewed_payload_fingerprint="0" * 64,
        reviewer_ref="operator://technology-radar-reviewer",
        review_status="approved_for_radar_intake",
        review_evidence_refs=["review-evidence://technology-radar/openai-agents-sdk"],
        reviewed_at="2026-08-12T10:05:00Z",
        recorded_at="2026-08-12T10:06:00Z",
    )
    return replace(
        provisional,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            provisional
        ),
    )


def _write_manifest(root: Path, intake: TechnologyRadarIntakeContract) -> Path:
    path = root / "openai-agents-sdk.json"
    path.write_text(
        dumps(asdict(intake), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _manifest_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def test_manifest_digest_binds_the_exact_reviewed_bytes(tmp_path: Path) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = _write_manifest(intake_root, _intake())
    reviewed_digest = _manifest_sha256(manifest)
    replacement = replace(_intake(), technology_name="Unreviewed replacement")
    replacement = replace(
        replacement,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            replacement
        ),
    )
    manifest.write_text(
        dumps(asdict(replacement), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        assess_technology_radar_intake_manifest(
            manifest,
            intake_root=intake_root,
            expected_manifest_sha256=reviewed_digest,
            knowledge_service=KnowledgeService(),
        )

    assert not (tmp_path / "evolution.db").exists()


def test_register_manifest_uses_read_only_assessment_and_append_only_store(
    tmp_path: Path,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = _write_manifest(intake_root, _intake())
    evolution = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    knowledge = KnowledgeService()
    proposals_before = evolution.list_recent_proposals(limit=100)

    first = register_technology_radar_intake_manifest(
        manifest,
        intake_root=intake_root,
        expected_manifest_sha256=_manifest_sha256(manifest),
        evolution_service=evolution,
        knowledge_service=knowledge,
    )
    second = register_technology_radar_intake_manifest(
        manifest,
        intake_root=intake_root,
        expected_manifest_sha256=_manifest_sha256(manifest),
        evolution_service=evolution,
        knowledge_service=knowledge,
    )

    assert first.intake == second.intake == _intake()
    assert first.assessment.status == "eligible_for_reviewed_registry"
    assert first.assessment.registry_write_authorized is False
    assert first.network_fetch_performed is False
    assert first.knowledge_ingestion_performed is False
    assert first.evolution_proposal_created is False
    assert first.execution_performed is False
    assert first.runtime_activation_performed is False
    assert first.promotion_performed is False
    assert first.core_mutation_performed is False
    assert first.priority_mutation_performed is False
    assert evolution.list_technology_radar_intakes() == [_intake()]
    assert evolution.list_recent_proposals(limit=100) == proposals_before

    restarted = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    assert restarted.get_technology_radar_intake(
        intake_id=_intake().intake_id,
        intake_version="1.0.0",
    ) == _intake()


@pytest.mark.parametrize(
    "raw",
    [
        '{"intake_id":"a","intake_id":"b"}',
        '{"value":NaN}',
        "[]",
    ],
)
def test_manifest_rejects_noncanonical_json_before_persistence(
    tmp_path: Path,
    raw: str,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = intake_root / "invalid.json"
    manifest.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError, match="technology radar manifest"):
        load_technology_radar_intake_manifest(
            manifest,
            intake_root=intake_root,
        )


def test_manifest_rejects_traversal_unknown_fields_and_secret_without_writing(
    tmp_path: Path,
) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    outside = _write_manifest(tmp_path, _intake())
    with pytest.raises(ValueError, match="inside intake root"):
        load_technology_radar_intake_manifest(outside, intake_root=intake_root)

    payload = asdict(_intake())
    payload["unknown_authority"] = True
    unknown = intake_root / "unknown.json"
    unknown.write_text(dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="schema mismatch"):
        load_technology_radar_intake_manifest(unknown, intake_root=intake_root)

    secret_intake = replace(
        _intake(),
        claims=["api_key=do-not-persist-this-value"],
    )
    secret_intake = replace(
        secret_intake,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            secret_intake
        ),
    )
    secret = _write_manifest(intake_root, secret_intake)
    evolution = EvolutionLabService(database_path=str(tmp_path / "evolution.db"))
    with pytest.raises(ValueError, match="sensitive"):
        register_technology_radar_intake_manifest(
            secret,
            intake_root=intake_root,
            expected_manifest_sha256=_manifest_sha256(secret),
            evolution_service=evolution,
            knowledge_service=KnowledgeService(),
        )
    assert evolution.list_technology_radar_intakes() == []


def test_registration_requires_detached_manifest_digest(tmp_path: Path) -> None:
    intake_root = tmp_path / "intake"
    intake_root.mkdir()
    manifest = _write_manifest(intake_root, _intake())

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        assess_technology_radar_intake_manifest(
            manifest,
            intake_root=intake_root,
            expected_manifest_sha256="f" * 64,
            knowledge_service=KnowledgeService(),
        )
    assert not (tmp_path / "evolution.db").exists()


@pytest.mark.parametrize(
    "unsafe_root",
    [
        r"\\host\share\technology-intake",
        r"\\?\C:\technology-intake",
        r"\\.\GLOBALROOT\Device\HarddiskVolumeShadowCopy1",
    ],
)
def test_remote_or_device_root_is_rejected_before_filesystem_access(
    unsafe_root: str,
) -> None:
    with pytest.raises(ValueError, match="local non-device path"):
        load_technology_radar_intake_manifest(
            "manifest.json",
            intake_root=unsafe_root,
        )
