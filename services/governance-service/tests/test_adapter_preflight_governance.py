from __future__ import annotations

from pathlib import Path
from sqlite3 import DatabaseError, connect

import pytest
from governance_service.service import GovernanceService

from shared.action_confirmation import action_intent_fingerprint, build_action_intent
from shared.adapter_permissions import (
    LOCAL_TEXT_FILE_DESCRIPTOR,
    SEEDED_ADAPTER_REGISTRY,
    build_adapter_descriptor,
    build_adapter_registry_snapshot,
)
from shared.autonomy_ladder import (
    AUTONOMY_ACTION_POLICY_VERSION,
    AUTONOMY_LEVEL_POLICIES,
    evaluate_autonomy_action,
)
from shared.contracts import (
    ActionIntentContract,
    AdapterActionRequestContract,
    AdapterGrantContract,
    AutonomyActionPolicyDecisionContract,
)
from shared.types import RiskLevel

ISSUED_AT = "2026-08-29T12:00:00Z"
PREFLIGHT_AT = "2026-08-29T12:02:00Z"
GRANT_EXPIRES_AT = "2026-08-29T12:10:00Z"
PREFLIGHT_EXPIRES_AT = "2026-08-29T12:05:00Z"
INTENT_EXPIRES_AT = "2026-08-29T12:20:00Z"


def _request(**changes: str) -> AdapterActionRequestContract:
    values = {
        "adapter_id": "local_text_file",
        "adapter_version": "1.0.0",
        "action_kind": "prepare_external_action",
        "operation": "create_text",
        "resource_scope": "configured_text_root",
        "resource_ref": "text:notes/mb215.txt",
    }
    values.update(changes)
    return AdapterActionRequestContract(**values)


def _intent(suffix: str = "one") -> ActionIntentContract:
    return build_action_intent(
        intent_id=f"adapter-intent://mb215/{suffix}",
        origin_request_id=f"request://mb215/{suffix}",
        session_id="session://mb215/operator",
        mission_id=f"mission://mb215/{suffix}",
        operator_identity_ref="operator://local/vtham",
        handler_id="adapter://local_text_file",
        handler_version="1.0.0",
        operation="create_text",
        target_ref="text:notes/mb215.txt",
        content_digest="a" * 64,
        precondition_digest="b" * 64,
        risk_level=RiskLevel.MODERATE,
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=f"adapterIntentNonceMb215{suffix}123456",
        issued_at=ISSUED_AT,
        expires_at=INTENT_EXPIRES_AT,
        now=ISSUED_AT,
    )


def _decision(
    *,
    confirmation_required: bool = False,
) -> AutonomyActionPolicyDecisionContract:
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
        human_confirmation_required=confirmation_required,
        human_confirmation_mode=(
            "explicit_confirmation_required" if confirmation_required else "not_required"
        ),
        confirmation_evidence_state="absent",
    )


def _issue(
    service: GovernanceService,
    intent: ActionIntentContract,
    *,
    confirmation_required: bool = False,
) -> AdapterGrantContract:
    request = _request()
    registry, descriptor = service.resolve_active_adapter_descriptor(request)
    return service.issue_adapter_grant(
        intent,
        request,
        _decision(confirmation_required=confirmation_required),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=ISSUED_AT,
        expires_at=GRANT_EXPIRES_AT,
    )


def _verify(
    service: GovernanceService,
    intent: ActionIntentContract,
    grant: AdapterGrantContract,
    *,
    request: AdapterActionRequestContract | None = None,
    subject_ref: str | None = None,
    expected_grant_fingerprint: str | None = None,
    expected_action_fingerprint: str | None = None,
    expected_content_digest: str | None = None,
    expected_precondition_digest: str | None = None,
    expected_descriptor_fingerprint: str | None = None,
    expected_registry_fingerprint: str | None = None,
    expected_authorization_expires_at: str | None = None,
    preflight_expires_at: str = PREFLIGHT_EXPIRES_AT,
    expected_intent_fingerprint: str | None = None,
    verified_at: str = PREFLIGHT_AT,
) -> bool:
    return service.verify_adapter_grant_for_preflight_exact(
        grant.grant_id,
        subject_ref=subject_ref or intent.operator_identity_ref,
        action_request=request or _request(),
        expected_grant_fingerprint=(expected_grant_fingerprint or grant.grant_fingerprint),
        expected_action_fingerprint=(expected_action_fingerprint or intent.action_fingerprint),
        expected_content_digest=(expected_content_digest or intent.content_digest),
        expected_precondition_digest=(expected_precondition_digest or intent.precondition_digest),
        expected_descriptor_fingerprint=(
            expected_descriptor_fingerprint or grant.descriptor_fingerprint
        ),
        expected_registry_fingerprint=(expected_registry_fingerprint or grant.registry_fingerprint),
        expected_authorization_expires_at=(expected_authorization_expires_at or grant.expires_at),
        preflight_expires_at=preflight_expires_at,
        intent_fingerprint=(expected_intent_fingerprint or action_intent_fingerprint(intent)),
        verified_at=verified_at,
    )


def _row_counts(database_path: Path) -> dict[str, int]:
    tables = (
        "action_intents",
        "action_confirmation_challenges",
        "human_confirmation_receipts",
        "action_confirmation_claims",
        "adapter_registry_epochs",
        "adapter_registry_descriptors",
        "adapter_grants",
        "adapter_grant_claims",
    )
    with connect(database_path) as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }


def _expanded_registry(*, drift: bool = False):  # type: ignore[no-untyped-def]
    local_descriptor = (
        build_adapter_descriptor(
            adapter_id="local_text_file",
            adapter_version="1.0.0",
            action_kind="prepare_external_action",
            allowed_operations=("create_text",),
            allowed_resource_scopes=("configured_text_root",),
        )
        if drift
        else LOCAL_TEXT_FILE_DESCRIPTOR
    )
    extra = build_adapter_descriptor(
        adapter_id="audit_sink",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        allowed_operations=("append_record",),
        allowed_resource_scopes=("configured_audit_root",),
    )
    return build_adapter_registry_snapshot(
        registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
        registry_version="1.1.0",
        descriptors=(local_descriptor, extra),
    )


def test_preflight_is_restart_safe_exact_and_does_not_mutate_rows(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    service.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    intent = _intent()
    grant = _issue(service, intent)
    before = _row_counts(database_path)

    assert _verify(GovernanceService(database_path), intent, grant) is True
    assert _verify(GovernanceService(database_path), intent, grant) is True
    assert _row_counts(database_path) == before
    assert before["adapter_grant_claims"] == 0


def test_confirmation_required_grant_allows_inspection_without_receipt_or_claim(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    service.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    intent = _intent("confirmation")
    grant = _issue(service, intent, confirmation_required=True)
    before = _row_counts(database_path)

    assert grant.confirmation_required is True
    assert _verify(service, intent, grant) is True
    assert _row_counts(database_path) == before
    assert before["human_confirmation_receipts"] == 0
    assert before["action_confirmation_claims"] == 0


def test_claimed_or_expired_grant_cannot_authorize_preflight(tmp_path: Path) -> None:
    database_path = tmp_path / "claimed.db"
    service = GovernanceService(database_path)
    service.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    intent = _intent("claimed")
    grant = _issue(service, intent)
    service.claim_adapter_grant_exact(
        grant.grant_id,
        operation_id="operation://mb215/claimed",
        subject_ref=intent.operator_identity_ref,
        expected_grant_fingerprint=grant.grant_fingerprint,
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        claimed_at=PREFLIGHT_AT,
    )

    assert _verify(service, intent, grant) is False

    expiry_path = tmp_path / "expiry.db"
    expiry_service = GovernanceService(expiry_path)
    expiry_service.activate_adapter_registry(
        SEEDED_ADAPTER_REGISTRY,
        activated_at=ISSUED_AT,
    )
    expiry_intent = _intent("expiry")
    expiry_grant = _issue(expiry_service, expiry_intent)
    before = _row_counts(expiry_path)
    assert (
        _verify(
            expiry_service,
            expiry_intent,
            expiry_grant,
            verified_at=GRANT_EXPIRES_AT,
        )
        is False
    )
    assert _row_counts(expiry_path) == before


def test_additive_registry_preserves_preflight_but_removal_and_drift_block(
    tmp_path: Path,
) -> None:
    additive = GovernanceService(tmp_path / "additive.db")
    additive.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    additive_intent = _intent("additive")
    additive_grant = _issue(additive, additive_intent)
    additive.activate_adapter_registry(
        _expanded_registry(),
        activated_at="2026-08-29T12:00:01Z",
    )
    assert _verify(additive, additive_intent, additive_grant) is True

    removed = GovernanceService(tmp_path / "removed.db")
    removed.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    removed_intent = _intent("removed")
    removed_grant = _issue(removed, removed_intent)
    removed.activate_adapter_registry(
        build_adapter_registry_snapshot(
            registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
            registry_version="1.1.0",
            descriptors=(),
        ),
        activated_at="2026-08-29T12:00:01Z",
    )
    assert _verify(removed, removed_intent, removed_grant) is False

    drifted = GovernanceService(tmp_path / "drifted.db")
    drifted.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    drifted_intent = _intent("drifted")
    drifted_grant = _issue(drifted, drifted_intent)
    drifted.activate_adapter_registry(
        _expanded_registry(drift=True),
        activated_at="2026-08-29T12:00:01Z",
    )
    assert _verify(drifted, drifted_intent, drifted_grant) is False


@pytest.mark.parametrize(
    ("changes"),
    (
        {"subject_ref": "operator://local/spoof"},
        {"request": _request(resource_ref="text:notes/other.txt")},
        {"request": _request(adapter_version="1.0.*")},
        {"request": _request(action_kind="execute_external_action")},
        {"expected_grant_fingerprint": "0" * 64},
        {"expected_action_fingerprint": "1" * 64},
        {"expected_content_digest": "5" * 64},
        {"expected_precondition_digest": "6" * 64},
        {"expected_descriptor_fingerprint": "3" * 64},
        {"expected_registry_fingerprint": "4" * 64},
        {"expected_authorization_expires_at": "2026-08-29T12:09:59Z"},
        {"preflight_expires_at": "2026-08-29T12:10:01Z"},
        {"preflight_expires_at": "2026-08-29T12:01:59Z"},
        {"expected_intent_fingerprint": "2" * 64},
    ),
)
def test_preflight_fails_closed_on_exact_binding_mismatch(
    tmp_path: Path,
    changes: dict[str, object],
) -> None:
    service = GovernanceService(tmp_path / "governance.db")
    service.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    intent = _intent("mismatch")
    grant = _issue(service, intent)

    assert _verify(service, intent, grant, **changes) is False  # type: ignore[arg-type]
    assert (
        service.verify_adapter_grant_for_preflight_exact(
            "adapter-grant://mb215/missing",
            subject_ref=intent.operator_identity_ref,
            action_request=_request(),
            expected_grant_fingerprint=grant.grant_fingerprint,
            expected_action_fingerprint=intent.action_fingerprint,
            expected_content_digest=intent.content_digest,
            expected_precondition_digest=intent.precondition_digest,
            expected_descriptor_fingerprint=grant.descriptor_fingerprint,
            expected_registry_fingerprint=grant.registry_fingerprint,
            expected_authorization_expires_at=grant.expires_at,
            preflight_expires_at=PREFLIGHT_EXPIRES_AT,
            intent_fingerprint=action_intent_fingerprint(intent),
            verified_at=PREFLIGHT_AT,
        )
        is False
    )
    assert (
        service.verify_adapter_grant_for_preflight_exact(
            grant.grant_id,
            subject_ref=intent.operator_identity_ref,
            action_request=None,  # type: ignore[arg-type]
            expected_grant_fingerprint=grant.grant_fingerprint,
            expected_action_fingerprint=intent.action_fingerprint,
            expected_content_digest=intent.content_digest,
            expected_precondition_digest=intent.precondition_digest,
            expected_descriptor_fingerprint=grant.descriptor_fingerprint,
            expected_registry_fingerprint=grant.registry_fingerprint,
            expected_authorization_expires_at=grant.expires_at,
            preflight_expires_at=PREFLIGHT_EXPIRES_AT,
            intent_fingerprint=action_intent_fingerprint(intent),
            verified_at=PREFLIGHT_AT,
        )
        is False
    )


def test_preflight_fails_closed_on_tamper_and_database_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "tamper.db"
    service = GovernanceService(database_path)
    service.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    intent = _intent("tamper")
    grant = _issue(service, intent)
    with connect(database_path) as connection:
        connection.execute("DROP TRIGGER adapter_grants_no_update")
        connection.execute(
            "UPDATE adapter_grants SET payload_sha256 = ? WHERE grant_id = ?",
            ("0" * 64, grant.grant_id),
        )
        connection.commit()
    assert _verify(GovernanceService(database_path), intent, grant) is False

    healthy = GovernanceService(tmp_path / "database-error.db")
    healthy.activate_adapter_registry(SEEDED_ADAPTER_REGISTRY, activated_at=ISSUED_AT)
    healthy_intent = _intent("database-error")
    healthy_grant = _issue(healthy, healthy_intent)

    def fail_connection():  # type: ignore[no-untyped-def]
        raise DatabaseError("simulated unavailable ledger")

    monkeypatch.setattr(
        healthy.action_confirmation_repository,
        "_new_connection",
        fail_connection,
    )
    assert _verify(healthy, healthy_intent, healthy_grant) is False
