from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from sqlite3 import IntegrityError, connect
from tempfile import gettempdir
from uuid import uuid4

import pytest
from governance_service.service import GovernanceService

from shared.action_confirmation import (
    action_intent_fingerprint,
    build_action_fingerprint,
)
from shared.contracts import (
    ActionConfirmationClaimContract,
    ActionIntentContract,
    OperationDispatchContract,
    WorkflowLifecycleTransitionContract,
    WorkflowPolicyDecisionContract,
)
from shared.types import MissionId, OperationId, RequestId, RiskLevel, SessionId
from tests.unit.test_workflow_lifecycle import _activation

ISSUED_AT = "2026-08-29T12:00:00Z"
CONFIRMED_AT = "2026-08-29T12:01:00Z"
CLAIMED_AT = "2026-08-29T12:02:00Z"
VERIFIED_AT = "2026-08-29T12:03:00Z"
EXPIRES_AT = "2026-08-29T12:05:00Z"


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def action_intent(**overrides: object) -> ActionIntentContract:
    identity: dict[str, object] = {
        "origin_request_id": RequestId("request://mb212/origin-001"),
        "session_id": SessionId("session://mb212/operator-001"),
        "mission_id": MissionId("mission://mb212/safe-local-action"),
        "operator_identity_ref": "operator://local/vtham",
        "handler_id": "handler://operational/local-file",
        "handler_version": "1.0.0",
        "operation": "write_local_file",
        "target_ref": "workspace-file://reports/mb212.txt",
        "content_digest": "a" * 64,
        "precondition_digest": "b" * 64,
        "risk_level": RiskLevel.MODERATE,
        "policy_version": "1.0.0",
    }
    for field_name in tuple(identity):
        if field_name in overrides:
            identity[field_name] = overrides.pop(field_name)
    fingerprint = build_action_fingerprint(**identity)
    values = {
        "intent_id": "action-intent://mb212/intent-001",
        **identity,
        "nonce": "nonce_0123456789abcdef",
        "issued_at": ISSUED_AT,
        "expires_at": EXPIRES_AT,
        "action_fingerprint": fingerprint,
        **overrides,
    }
    return ActionIntentContract(**values)


def workflow_policy_decision() -> WorkflowPolicyDecisionContract:
    return WorkflowPolicyDecisionContract(
        policy_ref="workflow-policy://mb212/1.0.0/local-write",
        policy_version="1.0.0",
        source_registry_ref="domain-registry://runtime-routes/current",
        source_registry_fingerprint="c" * 64,
        workflow_profile="software_change_workflow",
        route="software",
        resolution_status="resolved",
        application_status="applied",
        application_reason="exact prepared dispatch snapshot",
        planning_focus="bounded local artifact",
        success_focus="one exact confirmed write",
        semantic_memory_role="read_only_context",
        procedural_memory_role="read_only_guidance",
        response_focus="confirmed artifact",
        adaptive_intervention_priority=[],
        effects=["prepared_dispatch_frozen"],
        evidence_refs=["policy://action-confirmation/v1"],
    )


def prepared_dispatch(
    intent: ActionIntentContract,
    **overrides: object,
) -> OperationDispatchContract:
    values: dict[str, object] = {
        "operation_id": OperationId("operation://mb212/prepared-001"),
        "request_id": intent.origin_request_id,
        "session_id": intent.session_id,
        "mission_id": intent.mission_id,
        "task_type": "draft_plan",
        "task_goal": "Write the exact confirmed local artifact",
        "task_plan": "Persist the frozen prepared dispatch output",
        "constraints": ["configured-root-only", "single-use-confirmation"],
        "expected_output": "text_brief",
        "plan_summary": "Prepared MB-212 artifact",
        "planned_steps": ["render exact content", "write once"],
        "plan_rationale": "the operator reviewed this exact dispatch",
        "success_criteria": ["receipt cannot authorize replanned content"],
        "operator_identity_ref": intent.operator_identity_ref,
        "canonical_user_ref": "user://local_operator",
        "risk_hint": intent.risk_level,
        "requires_human_validation": True,
        "request_confirmation_mode": "explicit_confirmation_required",
        "autonomy_human_confirmation_required": True,
        "autonomy_confirmation_mode": "explicit_confirmation_required",
        "workflow_policy_decision": workflow_policy_decision(),
        "workflow_lifecycle_transition": _activation(),
    }
    values.update(overrides)
    return OperationDispatchContract(**values)


def confirmed_receipt(
    service: GovernanceService,
    intent: ActionIntentContract,
):
    challenge = service.issue_action_confirmation_challenge(intent)
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    return challenge, receipt


def claim_receipt(
    service: GovernanceService,
    intent: ActionIntentContract,
    receipt_id: str,
    *,
    operation_id: str = "operation://mb212/runtime-001",
    claimed_at: str = CLAIMED_AT,
) -> ActionConfirmationClaimContract:
    return service.claim_action_confirmation(
        receipt_id,
        operation_id=operation_id,
        origin_request_id=intent.origin_request_id,
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        operator_identity_ref=intent.operator_identity_ref,
        claimed_at=claimed_at,
    )


def verify_claim(
    service: GovernanceService,
    intent: ActionIntentContract,
    claim: ActionConfirmationClaimContract,
    *,
    verified_at: str = VERIFIED_AT,
) -> bool:
    return service.verify_action_confirmation_claim(
        receipt_id=claim.receipt_id,
        claim_id=claim.claim_id,
        operation_id=claim.operation_id,
        origin_request_id=claim.origin_request_id,
        expected_action_fingerprint=intent.action_fingerprint,
        intent_fingerprint=action_intent_fingerprint(intent),
        claimed_at=claim.claimed_at,
        verified_at=verified_at,
        operator_identity_ref=claim.operator_identity_ref,
    )


def test_governance_confirmation_chain_is_exact_and_non_authorizing() -> None:
    service = GovernanceService()
    intent = action_intent()
    challenge, receipt = confirmed_receipt(service, intent)
    claim = claim_receipt(service, intent, receipt.receipt_id)

    context = service.load_action_confirmation_context(receipt.receipt_id)
    assert context.intent == intent
    assert context.challenge == challenge
    assert context.receipt == receipt
    assert context.prepared_dispatch is None
    assert context.claim == claim
    assert verify_claim(service, intent, claim) is True
    assert verify_claim(service, intent, claim) is False
    for evidence in (intent, challenge, receipt, claim):
        assert evidence.single_use is True
        assert evidence.read_only is True
        assert evidence.immutable is True
        assert evidence.execution_allowed is False
        assert evidence.tool_dispatch_allowed is False
        assert evidence.runtime_activation_allowed is False
        assert evidence.promotion_authorized is False
        assert evidence.automatic_promotion_allowed is False
        assert evidence.core_mutation_allowed is False


def test_challenge_receipt_lookup_is_read_only_exact_and_survives_restart(tmp_path) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    intent = action_intent()
    challenge = service.issue_action_confirmation_challenge(intent)
    assert service.load_action_confirmation_context_for_challenge(challenge.challenge_id) is None
    with pytest.raises(KeyError):
        service.load_action_confirmation_context_for_challenge("challenge://unknown")
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    restarted = GovernanceService(database_path)
    expected = restarted.load_action_confirmation_context(receipt.receipt_id)
    assert expected.claim is None
    for _ in range(2):
        assert restarted.load_action_confirmation_context_for_challenge(challenge.challenge_id) == (
            expected
        )
    # Historical lookup preserves expiration and existing claims, but cannot
    # renew a receipt or consume a claim. Fixtures are deliberately in the past.
    claim = claim_receipt(restarted, intent, receipt.receipt_id)
    context = GovernanceService(database_path).load_action_confirmation_context_for_challenge(
        challenge.challenge_id
    )
    assert context.claim == claim and context.receipt.expires_at == EXPIRES_AT
    with connect(database_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM human_confirmation_receipts").fetchone()[0]
            == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM action_confirmation_claims").fetchone()[0] == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM action_confirmation_presentations").fetchone()[
                0
            ]
            == 0
        )


def test_challenge_receipt_lookup_rejects_tampered_persisted_receipt(tmp_path) -> None:
    database_path = tmp_path / "governance.db"
    service = GovernanceService(database_path)
    challenge, receipt = confirmed_receipt(service, action_intent())
    with connect(database_path) as connection:
        connection.execute("DROP TRIGGER human_confirmation_receipts_no_update")
        connection.execute(
            "UPDATE human_confirmation_receipts SET payload_sha256 = ? WHERE receipt_id = ?",
            ("0" * 64, receipt.receipt_id),
        )
    with pytest.raises(ValueError, match="payload hash mismatch"):
        GovernanceService(database_path).load_action_confirmation_context_for_challenge(
            challenge.challenge_id
        )


def test_confirmation_rejects_spoof_drift_expiry_and_replay() -> None:
    service = GovernanceService()
    intent = action_intent()
    challenge = service.issue_action_confirmation_challenge(intent)

    with pytest.raises(ValueError, match="operator mismatch"):
        service.confirm_action_challenge(
            challenge.challenge_id,
            operator_identity_ref="operator://local/spoof",
            expected_action_fingerprint=intent.action_fingerprint,
            confirmed_at=CONFIRMED_AT,
        )
    with pytest.raises(ValueError, match="action fingerprint mismatch"):
        service.confirm_action_challenge(
            challenge.challenge_id,
            operator_identity_ref=intent.operator_identity_ref,
            expected_action_fingerprint="0" * 64,
            confirmed_at=CONFIRMED_AT,
        )
    with pytest.raises(ValueError, match="expired"):
        service.confirm_action_challenge(
            challenge.challenge_id,
            operator_identity_ref=intent.operator_identity_ref,
            expected_action_fingerprint=intent.action_fingerprint,
            confirmed_at=EXPIRES_AT,
        )

    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    with pytest.raises(ValueError, match="challenge already has a receipt"):
        service.confirm_action_challenge(
            challenge.challenge_id,
            operator_identity_ref=intent.operator_identity_ref,
            expected_action_fingerprint=intent.action_fingerprint,
            confirmed_at=CONFIRMED_AT,
        )
    with pytest.raises(ValueError, match="origin_request_id mismatch"):
        service.claim_action_confirmation(
            receipt.receipt_id,
            operation_id="operation://mb212/wrong-origin",
            origin_request_id="request://mb212/spoof",
            expected_action_fingerprint=intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(intent),
            operator_identity_ref=intent.operator_identity_ref,
            claimed_at=CLAIMED_AT,
        )
    with pytest.raises(ValueError, match="expired"):
        claim_receipt(
            service,
            intent,
            receipt.receipt_id,
            operation_id="operation://mb212/expired",
            claimed_at=EXPIRES_AT,
        )

    claim = claim_receipt(service, intent, receipt.receipt_id)
    with pytest.raises(ValueError, match="already claimed"):
        claim_receipt(
            service,
            intent,
            receipt.receipt_id,
            operation_id="operation://mb212/replay",
        )
    assert verify_claim(service, intent, claim, verified_at=EXPIRES_AT) is False
    assert (
        service.verify_action_confirmation_claim(
            receipt_id=claim.receipt_id,
            claim_id=claim.claim_id,
            operation_id="operation://mb212/substituted",
            origin_request_id=claim.origin_request_id,
            expected_action_fingerprint=intent.action_fingerprint,
            intent_fingerprint=action_intent_fingerprint(intent),
            claimed_at=claim.claimed_at,
            verified_at=VERIFIED_AT,
            operator_identity_ref=claim.operator_identity_ref,
        )
        is False
    )


def test_confirmation_reverifies_action_payload_before_persistence() -> None:
    service = GovernanceService()
    intent = action_intent()
    tampered = replace(intent, target_ref="workspace-file://reports/substituted.txt")

    with pytest.raises(ValueError, match="action_fingerprint_mismatch"):
        service.issue_action_confirmation_challenge(tampered)
    with pytest.raises(ValueError, match="preserve intent issuance"):
        service.issue_action_confirmation_challenge(
            intent,
            challenged_at="2026-08-29T12:00:00.000001Z",
        )


def test_prepared_dispatch_roundtrips_with_nested_contracts_after_restart() -> None:
    database_path = runtime_dir("governance-prepared-dispatch") / "governance.db"
    service = GovernanceService(database_path)
    intent = action_intent()
    dispatch = prepared_dispatch(intent)
    challenge = service.issue_action_confirmation_challenge(
        intent,
        prepared_dispatch=dispatch,
    )
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )

    context = GovernanceService(database_path).load_action_confirmation_context(receipt.receipt_id)
    assert context.prepared_dispatch == dispatch
    assert isinstance(
        context.prepared_dispatch.workflow_policy_decision,
        WorkflowPolicyDecisionContract,
    )
    assert isinstance(
        context.prepared_dispatch.workflow_lifecycle_transition,
        WorkflowLifecycleTransitionContract,
    )
    assert context.prepared_dispatch.request_id == intent.origin_request_id
    assert context.prepared_dispatch.session_id == intent.session_id
    assert context.prepared_dispatch.mission_id == intent.mission_id
    assert context.prepared_dispatch.operator_identity_ref == intent.operator_identity_ref
    assert context.prepared_dispatch.canonical_user_ref == "user://local_operator"


def test_prepared_dispatch_is_append_only_tamper_evident_and_non_authorizing() -> None:
    database_path = runtime_dir("governance-prepared-tamper") / "governance.db"
    service = GovernanceService(database_path)
    intent = action_intent()
    dispatch = prepared_dispatch(intent)

    with pytest.raises(ValueError, match="request_id mismatch"):
        service.issue_action_confirmation_challenge(
            intent,
            prepared_dispatch=replace(
                dispatch,
                request_id=RequestId("request://mb212/substituted"),
            ),
        )
    with pytest.raises(ValueError, match="workflow policy has authority"):
        service.issue_action_confirmation_challenge(
            intent,
            prepared_dispatch=replace(
                dispatch,
                workflow_policy_decision=replace(
                    dispatch.workflow_policy_decision,
                    autonomous_execution_allowed=True,
                ),
            ),
        )
    with pytest.raises(ValueError, match="must require human confirmation"):
        service.issue_action_confirmation_challenge(
            intent,
            prepared_dispatch=replace(
                dispatch,
                autonomy_human_confirmation_required=False,
            ),
        )

    challenge = service.issue_action_confirmation_challenge(
        intent,
        prepared_dispatch=dispatch,
    )
    receipt = service.confirm_action_challenge(
        challenge.challenge_id,
        operator_identity_ref=intent.operator_identity_ref,
        expected_action_fingerprint=intent.action_fingerprint,
        confirmed_at=CONFIRMED_AT,
    )
    with connect(database_path) as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                """
                UPDATE action_confirmation_prepared_dispatches
                SET payload = payload
                WHERE intent_id = ?
                """,
                (intent.intent_id,),
            )
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                """
                DELETE FROM action_confirmation_prepared_dispatches
                WHERE intent_id = ?
                """,
                (intent.intent_id,),
            )
        connection.execute("DROP TRIGGER action_confirmation_prepared_no_update")
        connection.execute(
            """
            UPDATE action_confirmation_prepared_dispatches
            SET dispatch_fingerprint = ?
            WHERE intent_id = ?
            """,
            ("0" * 64, intent.intent_id),
        )
        connection.commit()

    with pytest.raises(ValueError, match="stored dispatch_fingerprint mismatch"):
        GovernanceService(database_path).load_action_confirmation_context(receipt.receipt_id)
    with connect(database_path) as connection:
        connection.execute("DROP TRIGGER action_confirmation_prepared_no_update")
        connection.execute(
            """
            UPDATE action_confirmation_prepared_dispatches
            SET dispatch_fingerprint = payload_sha256,
                payload_sha256 = ?
            WHERE intent_id = ?
            """,
            ("0" * 64, intent.intent_id),
        )
        connection.commit()

    with pytest.raises(ValueError, match="prepared dispatch payload hash mismatch"):
        GovernanceService(database_path).load_action_confirmation_context(receipt.receipt_id)


def test_confirmation_ledger_survives_restart_and_detects_tamper() -> None:
    database_path = runtime_dir("governance-confirmation-restart") / "governance.db"
    service = GovernanceService(database_path)
    intent = action_intent()
    _challenge, receipt = confirmed_receipt(service, intent)
    claim = claim_receipt(service, intent, receipt.receipt_id)

    restarted = GovernanceService(database_path)
    assert verify_claim(restarted, intent, claim) is True
    assert verify_claim(GovernanceService(database_path), intent, claim) is False

    identifiers = {
        "action_intents": ("intent_id", intent.intent_id),
        "action_confirmation_challenges": (
            "challenge_id",
            restarted.load_action_confirmation_context(receipt.receipt_id).challenge.challenge_id,
        ),
        "human_confirmation_receipts": ("receipt_id", receipt.receipt_id),
        "action_confirmation_claims": ("claim_id", claim.claim_id),
        "action_confirmation_presentations": ("claim_id", claim.claim_id),
    }
    with connect(database_path) as connection:
        for table_name, (id_column, identifier) in identifiers.items():
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(
                    f"UPDATE {table_name} SET payload = payload WHERE {id_column} = ?",
                    (identifier,),
                )
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(
                    f"DELETE FROM {table_name} WHERE {id_column} = ?",
                    (identifier,),
                )
        connection.execute("DROP TRIGGER action_confirmation_claims_no_update")
        connection.execute(
            """
            UPDATE action_confirmation_claims
            SET payload_sha256 = ?
            WHERE claim_id = ?
            """,
            ("0" * 64, claim.claim_id),
        )
        connection.commit()

    assert verify_claim(restarted, intent, claim) is False
    with pytest.raises(ValueError, match="payload hash mismatch"):
        restarted.load_action_confirmation_context(receipt.receipt_id)


def test_confirmation_receipt_claim_is_atomic_under_concurrency() -> None:
    database_path = runtime_dir("governance-confirmation-race") / "governance.db"
    issuer = GovernanceService(database_path)
    intent = action_intent()
    _challenge, receipt = confirmed_receipt(issuer, intent)
    contenders = [GovernanceService(database_path), GovernanceService(database_path)]

    def consume(index: int) -> ActionConfirmationClaimContract | ValueError:
        try:
            return claim_receipt(
                contenders[index],
                intent,
                receipt.receipt_id,
                operation_id=f"operation://mb212/race-{index}",
            )
        except ValueError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(consume, range(2)))

    claims = [result for result in results if isinstance(result, ActionConfirmationClaimContract)]
    failures = [result for result in results if isinstance(result, ValueError)]
    assert len(claims) == 1
    assert len(failures) == 1
    assert "already claimed" in str(failures[0])
    assert verify_claim(issuer, intent, claims[0]) is True


def test_confirmation_claim_presentation_is_atomic_under_concurrency_and_restart() -> None:
    database_path = runtime_dir("governance-presentation-race") / "governance.db"
    issuer = GovernanceService(database_path)
    intent = action_intent()
    _challenge, receipt = confirmed_receipt(issuer, intent)
    claim = claim_receipt(issuer, intent, receipt.receipt_id)
    contenders = [GovernanceService(database_path) for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(
            executor.map(
                lambda service: verify_claim(service, intent, claim),
                contenders,
            )
        )

    assert results.count(True) == 1
    assert results.count(False) == 7
    assert verify_claim(GovernanceService(database_path), intent, claim) is False
    with connect(database_path) as connection:
        presentation_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM action_confirmation_presentations
            WHERE claim_id = ? AND operation_id = ?
            """,
            (claim.claim_id, claim.operation_id),
        ).fetchone()[0]
    assert presentation_count == 1
