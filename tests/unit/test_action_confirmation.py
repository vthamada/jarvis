from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from shared.action_confirmation import (
    action_confirmation_challenge_fingerprint,
    action_confirmation_claim_fingerprint,
    action_intent_fingerprint,
    build_action_fingerprint,
    build_action_intent,
    canonical_action_fingerprint_payload,
    human_confirmation_receipt_fingerprint,
    require_valid_action_confirmation_challenge,
    require_valid_action_confirmation_claim,
    require_valid_action_intent,
    require_valid_human_confirmation_receipt,
    validate_action_intent,
    verify_action_confirmation_challenge_fingerprint,
    verify_action_confirmation_claim_fingerprint,
    verify_action_fingerprint,
    verify_action_intent_fingerprint,
    verify_human_confirmation_receipt_fingerprint,
)
from shared.contracts import (
    ActionConfirmationChallengeContract,
    ActionConfirmationClaimContract,
    ActionIntentContract,
    HumanConfirmationReceiptContract,
    InputContract,
    OperationDispatchContract,
)
from shared.events import INTERNAL_EVENT_NAMES
from shared.schemas import (
    ACTION_CONFIRMATION_CHALLENGE_SCHEMA,
    ACTION_CONFIRMATION_CLAIM_SCHEMA,
    ACTION_INTENT_SCHEMA,
    HUMAN_CONFIRMATION_RECEIPT_SCHEMA,
    INPUT_SCHEMA,
    OPERATION_DISPATCH_SCHEMA,
)
from shared.types import (
    ChannelType,
    InputType,
    MissionId,
    OperationId,
    RequestId,
    RiskLevel,
    SessionId,
)

ISSUED_AT = "2026-08-29T12:00:00Z"
CONFIRMED_AT = "2026-08-29T12:01:00Z"
CLAIMED_AT = "2026-08-29T12:02:00Z"
EXPIRES_AT = "2026-08-29T12:10:00Z"
ACTIVE_NOW = datetime(2026, 8, 29, 12, 3, tzinfo=UTC)
CONTENT_DIGEST = "a" * 64
PRECONDITION_DIGEST = "b" * 64


def _action_fields() -> dict[str, object]:
    return {
        "origin_request_id": RequestId("request-origin-1"),
        "session_id": SessionId("session-1"),
        "mission_id": MissionId("mission-1"),
        "operator_identity_ref": "operator://local/alice",
        "handler_id": "handler://operational-service/text-artifact",
        "handler_version": "1.0.0",
        "operation": "create_text",
        "target_ref": "artifact-root://drafts/plan.md",
        "content_digest": CONTENT_DIGEST,
        "precondition_digest": PRECONDITION_DIGEST,
        "risk_level": RiskLevel.LOW,
        "policy_version": "policy-v1",
    }


def _intent() -> ActionIntentContract:
    fields = _action_fields()
    return ActionIntentContract(
        intent_id="action-intent://request-origin-1/1",
        **fields,
        nonce="nonce_0123456789abcdef",
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
        action_fingerprint=build_action_fingerprint(**fields),
    )


def _challenge(intent: ActionIntentContract) -> ActionConfirmationChallengeContract:
    return ActionConfirmationChallengeContract(
        challenge_id="action-confirmation-challenge://request-origin-1/1",
        intent_id=intent.intent_id,
        intent_fingerprint=action_intent_fingerprint(intent),
        action_fingerprint=intent.action_fingerprint,
        origin_request_id=intent.origin_request_id,
        session_id=intent.session_id,
        mission_id=intent.mission_id,
        operator_identity_ref=intent.operator_identity_ref,
        operation=intent.operation,
        nonce=intent.nonce,
        issued_at=intent.issued_at,
        expires_at=intent.expires_at,
    )


def _receipt(
    intent: ActionIntentContract,
    challenge: ActionConfirmationChallengeContract,
) -> HumanConfirmationReceiptContract:
    return HumanConfirmationReceiptContract(
        receipt_id="human-confirmation-receipt://request-origin-1/1",
        challenge_id=challenge.challenge_id,
        challenge_fingerprint=action_confirmation_challenge_fingerprint(challenge),
        intent_id=intent.intent_id,
        intent_fingerprint=action_intent_fingerprint(intent),
        action_fingerprint=intent.action_fingerprint,
        origin_request_id=intent.origin_request_id,
        session_id=intent.session_id,
        mission_id=intent.mission_id,
        operator_identity_ref=intent.operator_identity_ref,
        operation=intent.operation,
        confirmed_at=CONFIRMED_AT,
        expires_at=EXPIRES_AT,
    )


def _claim(
    intent: ActionIntentContract,
    receipt: HumanConfirmationReceiptContract,
) -> ActionConfirmationClaimContract:
    return ActionConfirmationClaimContract(
        claim_id="action-confirmation-claim://operation-1",
        receipt_id=receipt.receipt_id,
        receipt_fingerprint=human_confirmation_receipt_fingerprint(receipt),
        intent_id=intent.intent_id,
        intent_fingerprint=action_intent_fingerprint(intent),
        action_fingerprint=intent.action_fingerprint,
        operation_id=OperationId("operation-1"),
        origin_request_id=intent.origin_request_id,
        session_id=intent.session_id,
        mission_id=intent.mission_id,
        operator_identity_ref=intent.operator_identity_ref,
        operation=intent.operation,
        claimed_at=CLAIMED_AT,
        expires_at=EXPIRES_AT,
    )


def test_action_fingerprint_uses_exact_canonical_action_identity() -> None:
    fields = _action_fields()
    canonical = canonical_action_fingerprint_payload(**fields)
    expected = (
        '{"content_digest":"'
        + CONTENT_DIGEST
        + '","handler_id":"handler://operational-service/text-artifact",'
        '"handler_version":"1.0.0","mission_id":"mission-1",'
        '"operation":"create_text","operator_identity_ref":"operator://local/alice",'
        '"origin_request_id":"request-origin-1","policy_version":"policy-v1",'
        '"precondition_digest":"'
        + PRECONDITION_DIGEST
        + '","risk_level":"low","session_id":"session-1",'
        '"target_ref":"artifact-root://drafts/plan.md"}'
    )

    assert canonical == expected
    assert build_action_fingerprint(**fields) == sha256(expected.encode("utf-8")).hexdigest()
    assert build_action_fingerprint(**dict(reversed(list(fields.items())))) == (
        build_action_fingerprint(**fields)
    )


def test_action_intent_builder_calculates_and_validates_the_exact_identity() -> None:
    intent = build_action_intent(
        intent_id="action-intent://request-origin-1/1",
        **_action_fields(),
        nonce="nonce_0123456789abcdef",
        issued_at=ISSUED_AT,
        expires_at=EXPIRES_AT,
        now=ACTIVE_NOW,
    )

    assert intent == _intent()
    assert verify_action_fingerprint(intent) is True


def test_intent_nonce_and_window_are_bound_without_changing_action_identity() -> None:
    intent = _intent()
    changed_nonce = replace(intent, nonce="nonce_fedcba9876543210")

    assert action_intent_fingerprint(intent) != action_intent_fingerprint(changed_nonce)
    assert intent.action_fingerprint == changed_nonce.action_fingerprint
    assert verify_action_fingerprint(intent) is True
    assert verify_action_intent_fingerprint(
        intent,
        action_intent_fingerprint(intent),
    ) is True
    assert verify_action_intent_fingerprint(
        intent,
        action_intent_fingerprint(changed_nonce),
    ) is False


def test_exact_intent_challenge_receipt_claim_chain_is_valid_and_frozen() -> None:
    intent = _intent()
    challenge = _challenge(intent)
    receipt = _receipt(intent, challenge)
    claim = _claim(intent, receipt)

    require_valid_action_intent(intent, now=ACTIVE_NOW)
    require_valid_action_confirmation_challenge(
        challenge,
        intent=intent,
        now=ACTIVE_NOW,
    )
    require_valid_human_confirmation_receipt(
        receipt,
        challenge=challenge,
        intent=intent,
        now=ACTIVE_NOW,
    )
    require_valid_action_confirmation_claim(
        claim,
        receipt=receipt,
        challenge=challenge,
        intent=intent,
        now=ACTIVE_NOW,
        expected_operation_id=OperationId("operation-1"),
    )

    assert verify_action_confirmation_challenge_fingerprint(
        challenge,
        action_confirmation_challenge_fingerprint(challenge),
    )
    assert verify_human_confirmation_receipt_fingerprint(
        receipt,
        human_confirmation_receipt_fingerprint(receipt),
    )
    assert verify_action_confirmation_claim_fingerprint(
        claim,
        action_confirmation_claim_fingerprint(claim),
    )
    with pytest.raises(FrozenInstanceError):
        intent.operation = "replace_text"  # type: ignore[misc]


def test_tampered_action_or_chain_mismatch_fails_closed() -> None:
    intent = _intent()
    challenge = _challenge(intent)
    receipt = _receipt(intent, challenge)
    claim = _claim(intent, receipt)

    tampered_intent = replace(intent, target_ref="artifact-root://drafts/other.md")
    assert verify_action_fingerprint(tampered_intent) is False
    with pytest.raises(ValueError, match="action_fingerprint_mismatch"):
        require_valid_action_intent(tampered_intent, now=ACTIVE_NOW)

    mismatched_challenge = replace(
        challenge,
        operator_identity_ref="operator://local/mallory",
    )
    with pytest.raises(ValueError, match="challenge_operator_identity_ref_mismatch"):
        require_valid_action_confirmation_challenge(
            mismatched_challenge,
            intent=intent,
            now=ACTIVE_NOW,
        )

    tampered_receipt = replace(receipt, confirmed_at="2026-08-29T12:01:30Z")
    with pytest.raises(ValueError, match="claim_receipt_fingerprint_mismatch"):
        require_valid_action_confirmation_claim(
            claim,
            receipt=tampered_receipt,
            challenge=challenge,
            intent=intent,
            now=ACTIVE_NOW,
        )


def test_timestamps_expiry_digests_and_authorities_are_strict() -> None:
    intent = _intent()

    assert validate_action_intent(intent, now=datetime(2026, 8, 29, 12, 11, tzinfo=UTC)) == [
        "action_intent_expired"
    ]
    assert "issued_at_must_include_timezone" in validate_action_intent(
        replace(intent, issued_at="2026-08-29T12:00:00"),
    )
    assert "content_digest_must_be_lowercase_sha256" in validate_action_intent(
        replace(intent, content_digest="A" * 64),
    )
    assert "execution_allowed_must_be_false" in validate_action_intent(
        replace(intent, execution_allowed=True),
    )
    assert "single_use_must_be_true" in validate_action_intent(
        replace(intent, single_use=False),
    )


def test_confirmation_contracts_have_canonical_schemas_and_zero_authority() -> None:
    intent = _intent()
    challenge = _challenge(intent)
    receipt = _receipt(intent, challenge)
    claim = _claim(intent, receipt)

    contracts_and_schemas = (
        (intent, ACTION_INTENT_SCHEMA),
        (challenge, ACTION_CONFIRMATION_CHALLENGE_SCHEMA),
        (receipt, HUMAN_CONFIRMATION_RECEIPT_SCHEMA),
        (claim, ACTION_CONFIRMATION_CLAIM_SCHEMA),
    )
    for contract, schema in contracts_and_schemas:
        assert schema.contract_name == type(contract).__name__
        assert contract.single_use is True
        assert contract.read_only is True
        assert contract.immutable is True
        assert contract.execution_allowed is False
        assert contract.tool_dispatch_allowed is False
        assert contract.runtime_activation_allowed is False
        assert contract.promotion_authorized is False
        assert contract.automatic_promotion_allowed is False
        assert contract.core_mutation_allowed is False

    assert {
        "origin_request_id",
        "handler_id",
        "operation",
        "action_fingerprint",
        "nonce",
        "issued_at",
        "expires_at",
    }.issubset(ACTION_INTENT_SCHEMA.required_fields)
    assert "receipt_fingerprint" in ACTION_CONFIRMATION_CLAIM_SCHEMA.required_fields
    assert "operation_id" in ACTION_CONFIRMATION_CLAIM_SCHEMA.required_fields


def test_input_and_dispatch_additions_are_backward_compatible_and_declared() -> None:
    input_contract = InputContract(
        request_id=RequestId("request-new-envelope"),
        session_id=SessionId("session-1"),
        channel=ChannelType.CONSOLE,
        input_type=InputType.TEXT,
        content="execute confirmed action",
        timestamp=ISSUED_AT,
    )
    dispatch = OperationDispatchContract(
        operation_id=OperationId("operation-1"),
        request_id=RequestId("request-new-envelope"),
        task_type="draft_plan",
        task_goal="draft",
        task_plan="draft safely",
        constraints=[],
        expected_output="text/markdown",
    )

    assert input_contract.action_confirmation_receipt_id is None
    assert input_contract.action_confirmation_origin_request_id is None
    assert dispatch.receipt_id is None
    assert dispatch.claim_id is None
    assert dispatch.origin_request_id is None
    assert dispatch.action_fingerprint is None
    assert dispatch.intent_fingerprint is None
    assert dispatch.claimed_at is None
    assert {
        "action_confirmation_receipt_id",
        "action_confirmation_origin_request_id",
    }.issubset(INPUT_SCHEMA.optional_fields)
    assert {
        "receipt_id",
        "claim_id",
        "origin_request_id",
        "action_fingerprint",
        "intent_fingerprint",
        "claimed_at",
    }.issubset(OPERATION_DISPATCH_SCHEMA.optional_fields)


def test_action_confirmation_event_names_are_canonical() -> None:
    assert {
        "action_confirmation_challenged",
        "action_confirmation_recorded",
        "action_confirmation_claimed",
        "action_confirmation_blocked",
    }.issubset(INTERNAL_EVENT_NAMES)
