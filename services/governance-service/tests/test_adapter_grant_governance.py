from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from sqlite3 import IntegrityError, connect

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
CONFIRMED_AT = "2026-08-29T12:01:00Z"
CLAIMED_AT = "2026-08-29T12:02:00Z"
VERIFIED_AT = "2026-08-29T12:03:00Z"
GRANT_EXPIRES_AT = "2026-08-29T12:10:00Z"
INTENT_EXPIRES_AT = "2026-08-29T12:20:00Z"


def _request(**changes: str) -> AdapterActionRequestContract:
    values = {
        "adapter_id": "local_text_file",
        "adapter_version": "1.0.0",
        "action_kind": "prepare_external_action",
        "operation": "create_text",
        "resource_scope": "configured_text_root",
        "resource_ref": "text:notes/mb214.txt",
    }
    values.update(changes)
    return AdapterActionRequestContract(**values)


def _intent(suffix: str = "one", **changes: object) -> ActionIntentContract:
    values: dict[str, object] = {
        "intent_id": f"adapter-intent://mb214/{suffix}",
        "origin_request_id": f"request://mb214/{suffix}",
        "session_id": "session://mb214/operator",
        "mission_id": f"mission://mb214/{suffix}",
        "operator_identity_ref": "operator://local/vtham",
        "handler_id": "adapter://local_text_file",
        "handler_version": "1.0.0",
        "operation": "create_text",
        "target_ref": "text:notes/mb214.txt",
        "content_digest": "a" * 64,
        "precondition_digest": "b" * 64,
        "risk_level": RiskLevel.MODERATE,
        "policy_version": AUTONOMY_ACTION_POLICY_VERSION,
        "nonce": f"adapterIntentNonce{suffix}123456",
        "issued_at": ISSUED_AT,
        "expires_at": INTENT_EXPIRES_AT,
        "now": ISSUED_AT,
    }
    values.update(changes)
    return build_action_intent(**values)  # type: ignore[arg-type]


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
            "explicit_confirmation_required"
            if confirmation_required
            else "not_required"
        ),
        confirmation_evidence_state="absent",
    )


def _activate(service: GovernanceService, snapshot=SEEDED_ADAPTER_REGISTRY):  # type: ignore[no-untyped-def]
    return service.activate_adapter_registry(snapshot, activated_at=ISSUED_AT)


def _issue(
    service: GovernanceService,
    intent: ActionIntentContract,
    *,
    decision: AutonomyActionPolicyDecisionContract | None = None,
    request: AdapterActionRequestContract | None = None,
) -> AdapterGrantContract:
    exact_request = request or _request()
    registry, descriptor = service.resolve_active_adapter_descriptor(exact_request)
    return service.issue_adapter_grant(
        intent,
        exact_request,
        decision or _decision(),
        expected_registry_fingerprint=registry.registry_fingerprint,
        expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
        issued_at=ISSUED_AT,
        expires_at=GRANT_EXPIRES_AT,
    )


def _claim(
    service: GovernanceService,
    intent: ActionIntentContract,
    grant: AdapterGrantContract,
    *,
    operation_id: str = "operation://mb214/one",
    confirmation_receipt_id: str | None = None,
    claimed_at: str = CLAIMED_AT,
):  # type: ignore[no-untyped-def]
    return service.claim_adapter_grant_exact(
        grant.grant_id,
        operation_id=operation_id,
        subject_ref=intent.operator_identity_ref,
        expected_grant_fingerprint=grant.grant_fingerprint,
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        confirmation_receipt_id=confirmation_receipt_id,
        claimed_at=claimed_at,
    )


def _verify(
    service: GovernanceService,
    intent: ActionIntentContract,
    grant: AdapterGrantContract,
    claim,  # type: ignore[no-untyped-def]
    *,
    verified_at: str = VERIFIED_AT,
) -> bool:
    return service.verify_adapter_grant_claim_exact(
        grant_id=grant.grant_id,
        claim_id=claim.claim_id,
        operation_id=claim.operation_id,
        subject_ref=intent.operator_identity_ref,
        expected_grant_fingerprint=grant.grant_fingerprint,
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        claimed_at=claim.claimed_at,
        verified_at=verified_at,
        confirmation_receipt_id=claim.confirmation_receipt_id,
        confirmation_claim_id=claim.confirmation_claim_id,
        confirmation_claim_fingerprint=claim.confirmation_claim_fingerprint,
    )


def _expanded_registry(*, version: str = "1.1.0"):
    extra = build_adapter_descriptor(
        adapter_id="audit_sink",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        allowed_operations=("append_record",),
        allowed_resource_scopes=("configured_audit_root",),
    )
    return build_adapter_registry_snapshot(
        registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
        registry_version=version,
        descriptors=(LOCAL_TEXT_FILE_DESCRIPTOR, extra),
    )


def test_registry_and_grant_roundtrip_restart_with_exact_idempotence(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    assert _activate(service) == SEEDED_ADAPTER_REGISTRY
    assert _activate(service) == SEEDED_ADAPTER_REGISTRY
    intent = _intent()
    grant = _issue(service, intent)
    assert _issue(service, intent) == grant

    assert (
        service.action_confirmation_repository.record_adapter_grant(
            intent,
            grant,
            _decision(),
            verified_at=ISSUED_AT,
        )
        == grant
    )
    restarted = GovernanceService(database_path)
    context = restarted.load_adapter_grant_context(grant.grant_id)
    assert context.intent == intent
    assert context.grant == grant
    assert context.registry == SEEDED_ADAPTER_REGISTRY
    assert context.descriptor == LOCAL_TEXT_FILE_DESCRIPTOR
    assert context.claim is None
    with connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM adapter_registry_epochs").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM adapter_grants").fetchone() == (1,)
        assert connection.execute("SELECT COUNT(*) FROM action_intents").fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM action_confirmation_challenges"
        ).fetchone() == (0,)


def test_expected_registry_and_descriptor_cas_blocks_stale_planning_context(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    _activate(service)
    registry, descriptor = service.resolve_active_adapter_descriptor(_request())
    service.activate_adapter_registry(
        _expanded_registry(),
        activated_at="2026-08-29T12:00:01Z",
    )

    with pytest.raises(ValueError, match="registry fingerprint changed"):
        service.issue_adapter_grant(
            _intent(),
            _request(),
            _decision(),
            expected_registry_fingerprint=registry.registry_fingerprint,
            expected_descriptor_fingerprint=descriptor.descriptor_fingerprint,
            issued_at=ISSUED_AT,
            expires_at=GRANT_EXPIRES_AT,
        )
    with connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM adapter_grants").fetchone() == (0,)
        assert connection.execute("SELECT COUNT(*) FROM action_intents").fetchone() == (0,)


def test_old_grant_survives_additive_epoch_but_removal_or_drift_blocks_claim(
    tmp_path: Path,
) -> None:
    additive_service = GovernanceService(tmp_path / "additive.db")
    _activate(additive_service)
    additive_intent = _intent("additive")
    additive_grant = _issue(additive_service, additive_intent)
    additive_service.activate_adapter_registry(
        _expanded_registry(),
        activated_at="2026-08-29T12:00:01Z",
    )
    additive_claim = _claim(additive_service, additive_intent, additive_grant)
    assert additive_claim.grant_fingerprint == additive_grant.grant_fingerprint
    assert (
        additive_service.load_adapter_grant_context(additive_grant.grant_id).registry
        == SEEDED_ADAPTER_REGISTRY
    )

    removed_service = GovernanceService(tmp_path / "removed.db")
    _activate(removed_service)
    removed_intent = _intent("removed")
    removed_grant = _issue(removed_service, removed_intent)
    removed_service.activate_adapter_registry(
        build_adapter_registry_snapshot(
            registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
            registry_version="1.1.0",
            descriptors=(),
        ),
        activated_at="2026-08-29T12:00:01Z",
    )
    with pytest.raises(ValueError, match="not allowlisted"):
        _claim(removed_service, removed_intent, removed_grant)
    assert removed_service.load_adapter_grant_context(removed_grant.grant_id).claim is None

    drift_service = GovernanceService(tmp_path / "drift.db")
    _activate(drift_service)
    drift_intent = _intent("drift")
    drift_grant = _issue(drift_service, drift_intent)
    drifted_descriptor = build_adapter_descriptor(
        adapter_id="local_text_file",
        adapter_version="1.0.0",
        action_kind="prepare_external_action",
        allowed_operations=("create_text",),
        allowed_resource_scopes=("configured_text_root",),
    )
    drift_service.activate_adapter_registry(
        build_adapter_registry_snapshot(
            registry_id=SEEDED_ADAPTER_REGISTRY.registry_id,
            registry_version="1.1.0",
            descriptors=(drifted_descriptor,),
        ),
        activated_at="2026-08-29T12:00:01Z",
    )
    with pytest.raises(ValueError, match="no longer active"):
        _claim(drift_service, drift_intent, drift_grant)
    assert drift_service.load_adapter_grant_context(drift_grant.grant_id).claim is None


def test_claim_is_exact_single_use_restart_safe_and_expiry_is_exclusive(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    _activate(service)
    intent = _intent()
    grant = _issue(service, intent)
    claim = _claim(service, intent, grant)

    assert claim.execution_allowed is False
    assert claim.tool_dispatch_allowed is False
    assert _verify(GovernanceService(database_path), intent, grant, claim) is True
    with pytest.raises(ValueError, match="already claimed"):
        _claim(
            GovernanceService(database_path),
            intent,
            grant,
            operation_id="operation://mb214/replay",
        )
    assert _verify(service, intent, grant, claim, verified_at=GRANT_EXPIRES_AT) is False

    expiry_service = GovernanceService(tmp_path / "expiry.db")
    _activate(expiry_service)
    expiry_intent = _intent("expiry")
    expiry_grant = _issue(expiry_service, expiry_intent)
    with pytest.raises(ValueError, match="expired"):
        _claim(
            expiry_service,
            expiry_intent,
            expiry_grant,
            claimed_at=GRANT_EXPIRES_AT,
        )
    assert expiry_service.load_adapter_grant_context(expiry_grant.grant_id).claim is None


def test_eight_concurrent_claims_have_exactly_one_winner(tmp_path: Path) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    _activate(service)
    intent = _intent()
    grant = _issue(service, intent)

    def contend(index: int) -> bool:
        try:
            _claim(
                GovernanceService(database_path),
                intent,
                grant,
                operation_id=f"operation://mb214/contender-{index}",
            )
        except (KeyError, ValueError):
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        outcomes = list(executor.map(contend, range(8)))
    assert outcomes.count(True) == 1
    with connect(database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM adapter_grant_claims").fetchone() == (1,)


def test_ledgers_are_append_only_and_payload_hash_columns_are_reverified(
    tmp_path: Path,
) -> None:
    append_only_path = tmp_path / "append-only.db"
    service = GovernanceService(append_only_path)
    _activate(service)
    intent = _intent("append-only")
    grant = _issue(service, intent)
    _claim(service, intent, grant)
    tables = (
        "adapter_registry_epochs",
        "adapter_registry_descriptors",
        "adapter_grants",
        "adapter_grant_claims",
    )
    with connect(append_only_path) as connection:
        for table in tables:
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(f"UPDATE {table} SET payload = payload")
            connection.rollback()
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(f"DELETE FROM {table}")
            connection.rollback()

    tamper_cases = (
        ("payload", "payload = payload || ' '", "payload hash mismatch"),
        ("hash", "payload_sha256 = '0000'", "payload hash mismatch"),
        ("column", "subject_ref = 'operator://local/spoof'", "stored subject_ref mismatch"),
    )
    for suffix, mutation, error in tamper_cases:
        database_path = tmp_path / f"tamper-{suffix}.db"
        tamper_service = GovernanceService(database_path)
        _activate(tamper_service)
        tamper_intent = _intent(f"tamper-{suffix}")
        tamper_grant = _issue(tamper_service, tamper_intent)
        with connect(database_path) as connection:
            connection.execute("DROP TRIGGER adapter_grants_no_update")
            connection.execute(
                f"UPDATE adapter_grants SET {mutation} WHERE grant_id = ?",
                (tamper_grant.grant_id,),
            )
            connection.commit()
        with pytest.raises(ValueError, match=error):
            GovernanceService(database_path).load_adapter_grant_context(
                tamper_grant.grant_id
            )


def test_confirmation_and_grant_claim_are_atomic_and_confirmation_never_authorizes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    _activate(service)
    intent = _intent("confirmed")
    grant = _issue(service, intent, decision=_decision(confirmation_required=True))
    challenge = service.issue_action_confirmation_challenge(intent)
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )

    with pytest.raises(KeyError, match="unknown adapter grant"):
        service.claim_adapter_grant_exact(
            "adapter-grant://mb214/missing",
            operation_id="operation://mb214/missing-grant",
            subject_ref=intent.operator_identity_ref,
            expected_grant_fingerprint=grant.grant_fingerprint,
            expected_action_fingerprint=intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(intent),
            confirmation_receipt_id=receipt.receipt_id,
            claimed_at=CLAIMED_AT,
        )
    assert service.load_action_confirmation_context(receipt.receipt_id).claim is None
    with pytest.raises(ValueError, match="requires exact confirmation"):
        _claim(service, intent, grant)
    assert service.load_action_confirmation_context(receipt.receipt_id).claim is None
    with pytest.raises(ValueError, match="expected_grant_fingerprint mismatch"):
        service.claim_adapter_grant_exact(
            grant.grant_id,
            operation_id="operation://mb214/bad-grant",
            subject_ref=intent.operator_identity_ref,
            expected_grant_fingerprint="0" * 64,
            expected_action_fingerprint=intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(intent),
            confirmation_receipt_id=receipt.receipt_id,
            claimed_at=CLAIMED_AT,
        )
    assert service.load_action_confirmation_context(receipt.receipt_id).claim is None

    claim = _claim(
        service,
        intent,
        grant,
        confirmation_receipt_id=receipt.receipt_id,
    )
    context = service.load_adapter_grant_context(grant.grant_id)
    assert context.claim == claim
    assert context.confirmation_claim is not None
    assert context.confirmation_claim.claim_id == claim.confirmation_claim_id
    assert context.confirmation_claim.receipt_id == receipt.receipt_id
    assert _verify(service, intent, grant, claim) is True
    assert claim.execution_allowed is False
    assert claim.tool_dispatch_allowed is False


def test_adapter_claim_failure_rolls_back_new_confirmation_claim(tmp_path: Path) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    _activate(service)
    operation_id = "operation://mb214/atomic-collision"

    allow_intent = _intent("allow-first")
    allow_grant = _issue(service, allow_intent)
    _claim(service, allow_intent, allow_grant, operation_id=operation_id)

    confirmed_intent = _intent("confirmed-second")
    confirmed_grant = _issue(
        service,
        confirmed_intent,
        decision=_decision(confirmation_required=True),
    )
    challenge = service.issue_action_confirmation_challenge(confirmed_intent)
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=confirmed_intent.operator_identity_ref,
        expected_action_fingerprint=confirmed_intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    with pytest.raises(ValueError, match="already claimed"):
        _claim(
            service,
            confirmed_intent,
            confirmed_grant,
            operation_id=operation_id,
            confirmation_receipt_id=receipt.receipt_id,
        )
    assert service.load_action_confirmation_context(receipt.receipt_id).claim is None
    assert service.load_adapter_grant_context(confirmed_grant.grant_id).claim is None
    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM action_confirmation_claims WHERE receipt_id = ?",
            (receipt.receipt_id,),
        ).fetchone() == (0,)


def test_governance_stops_at_metadata_and_never_creates_target_artifact(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "notes" / "mb214.txt"
    service = GovernanceService(tmp_path / "governance.db")
    _activate(service)
    intent = _intent("metadata-only")
    grant = _issue(service, intent)
    claim = _claim(service, intent, grant)

    assert grant.execution_allowed is False
    assert grant.tool_dispatch_allowed is False
    assert claim.execution_allowed is False
    assert claim.tool_dispatch_allowed is False
    assert not artifact.exists()
