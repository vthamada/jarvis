from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from sqlite3 import connect

import pytest
from governance_service.service import GovernanceService
from operational_service.adapters.local_text_file import (
    LOCAL_TEXT_DIFF_ALGORITHM,
    LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
    LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
)
from operational_service.service import OperationalService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_execution_permissions import SEEDED_ADAPTER_EXECUTION_REGISTRY
from shared.adapter_permissions import SEEDED_ADAPTER_REGISTRY
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    AdapterActionRequestContract,
    LocalTextFilePreflightRequestContract,
)
from shared.types import RiskLevel

PREPARE_AT = "2026-08-30T12:00:00Z"
PREFLIGHT_AT = "2026-08-30T12:01:00Z"
ATTEST_AT = "2026-08-30T12:01:10Z"
PREFLIGHT_EXPIRES_AT = "2026-08-30T12:03:00Z"
PREPARE_EXPIRES_AT = "2026-08-30T12:05:00Z"
INTENT_EXPIRES_AT = "2026-08-30T12:10:00Z"


@dataclass
class _Clock:
    current: str = ATTEST_AT

    def __call__(self) -> str:
        return self.current


def _prepare_decision():  # type: ignore[no-untyped-def]
    policy = AUTONOMY_LEVEL_POLICIES["supervised_external_action"]
    return evaluate_autonomy_action(
        requested_autonomy_level="supervised_external_action",
        max_autonomy_level="supervised_external_action",
        effective_autonomy_level="supervised_external_action",
        autonomy_ladder_status="within_limit",
        action_kind="prepare_external_action",
        selected_capability_mode="core_with_supervised_external_operation",
        max_capability_mode="core_with_supervised_external_operation",
        allowed_runtime_actions=policy["allowed_runtime_actions"],
        blocked_runtime_actions=policy["blocked_runtime_actions"],
        human_confirmation_required=False,
        human_confirmation_mode="not_required",
        confirmation_evidence_state="absent",
    )


def _attestation_count(database_path: Path) -> int:
    with connect(database_path) as connection:
        return int(
            connection.execute(
                "SELECT COUNT(*) FROM local_text_file_preflight_attestations"
            ).fetchone()[0]
        )


def test_operational_materializes_and_attests_before_returning_execution_bundle(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    text_root = tmp_path / "configured-text-root"
    text_root.mkdir()
    clock = _Clock()
    governance = GovernanceService(
        database_path,
        trusted_execution_clock=clock,
    )
    governance.activate_adapter_registry(
        SEEDED_ADAPTER_REGISTRY,
        activated_at=PREPARE_AT,
    )
    governance.activate_adapter_execution_registry(
        SEEDED_ADAPTER_EXECUTION_REGISTRY,
        activated_at=PREPARE_AT,
    )
    operational = OperationalService(
        artifact_dir=str(tmp_path / "artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_preflight_attestor=(governance.attest_local_text_file_preflight),
        local_text_file_roots={"notes": text_root},
    )
    action_request = AdapterActionRequestContract(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        operation="create_text",
        resource_scope="configured_text_root",
        resource_ref="text:notes/mb216-provenance.txt",
    )
    desired_text = "trusted operational preflight\n"
    root_fingerprint = operational.local_text_file_root_config_fingerprint()
    intent = build_action_intent(
        intent_id="adapter-intent://mb216/provenance",
        origin_request_id="request://mb216/provenance",
        session_id="session://mb216/provenance",
        mission_id="mission://mb216/provenance",
        operator_identity_ref="operator://local/tester",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation=action_request.operation,
        target_ref=action_request.resource_ref,
        content_digest=sha256(desired_text.encode()).hexdigest(),
        precondition_digest=root_fingerprint,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce="adapterPrepareIntentNonceMb216Provenance123456",
        issued_at=PREPARE_AT,
        expires_at=INTENT_EXPIRES_AT,
        now=PREPARE_AT,
    )
    registry, descriptor = governance.resolve_active_adapter_descriptor(action_request)
    grant = governance.issue_adapter_grant(
        intent,
        action_request,
        _prepare_decision(),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=PREPARE_AT,
        expires_at=PREPARE_EXPIRES_AT,
    )
    request = LocalTextFilePreflightRequestContract(
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        descriptor_fingerprint=grant.descriptor_fingerprint,
        registry_fingerprint=grant.registry_fingerprint,
        subject_ref=intent.operator_identity_ref,
        adapter_request=action_request,
        desired_text=desired_text,
        expected_root_config_fingerprint=root_fingerprint,
        preflight_policy_version=LOCAL_TEXT_PREFLIGHT_POLICY_VERSION,
        diff_algorithm=LOCAL_TEXT_DIFF_ALGORITHM,
        diff_algorithm_version=LOCAL_TEXT_DIFF_ALGORITHM_VERSION,
        prepared_at=PREFLIGHT_AT,
        expires_at=PREFLIGHT_EXPIRES_AT,
        authorization_expires_at=grant.expires_at,
    )

    pure = operational.preflight_local_text_file(
        request,
        now=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
    )
    assert _attestation_count(database_path) == 0

    preflight, attestation, execution_request = operational.preflight_and_attest_local_text_file(
        request,
        now=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
    )

    assert preflight == pure
    assert attestation.preflight_fingerprint == preflight.preflight_fingerprint
    assert execution_request.preflight_attestation_id == attestation.attestation_id
    assert execution_request.preflight_fingerprint == preflight.preflight_fingerprint
    assert _attestation_count(database_path) == 1
    assert list(text_root.iterdir()) == []

    forged_request = replace(execution_request, preflight_fingerprint="0" * 64)
    forged_operational = OperationalService(
        artifact_dir=str(tmp_path / "forged-artifacts"),
        adapter_preflight_verifier=governance.verify_adapter_grant_for_preflight_exact,
        local_text_file_preflight_attestor=lambda _preflight: (
            attestation,
            forged_request,
        ),
        local_text_file_roots={"notes": text_root},
    )
    with pytest.raises(
        ValueError,
        match="local_text_file_preflight_attestation_binding_mismatch",
    ):
        forged_operational.preflight_and_attest_local_text_file(
            request,
            now=datetime(2026, 8, 30, 12, 1, tzinfo=UTC),
        )
