"""Canonical fingerprints and fail-closed validation for action confirmation."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from math import isfinite
from re import fullmatch
from typing import Any
from unicodedata import category, normalize

from shared.contracts import (
    ActionConfirmationChallengeContract,
    ActionConfirmationClaimContract,
    ActionIntentContract,
    HumanConfirmationReceiptContract,
)
from shared.types import MissionId, OperationId, RequestId, RiskLevel, SessionId, Timestamp

_SHA256_PATTERN = r"[0-9a-f]{64}"
_IDENTIFIER_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._~:/?#@!$&'()*+,;=%+\-]{0,511}"
_OPERATION_PATTERN = r"[a-z][a-z0-9_.-]{0,127}"
_NONCE_PATTERN = r"[A-Za-z0-9_-]{16,128}"
_TIMESTAMP_PATTERN = (
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?"
    r"(?:Z|[+-]\d{2}:\d{2})"
)
_AUTHORITY_FALSE_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
)


def canonical_action_confirmation_payload(value: object) -> str:
    """Serialize an action-confirmation artifact with stable JCS-like ordering."""

    return dumps(
        _json_value(value),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_action_fingerprint_payload(
    *,
    origin_request_id: RequestId | str,
    session_id: SessionId | str,
    mission_id: MissionId | str | None,
    operator_identity_ref: str,
    handler_id: str,
    handler_version: str,
    operation: str,
    target_ref: str,
    content_digest: str,
    precondition_digest: str,
    risk_level: RiskLevel | str,
    policy_version: str,
) -> str:
    """Return the canonical payload for one exact action identity."""

    payload = _validated_action_identity(
        origin_request_id=origin_request_id,
        session_id=session_id,
        mission_id=mission_id,
        operator_identity_ref=operator_identity_ref,
        handler_id=handler_id,
        handler_version=handler_version,
        operation=operation,
        target_ref=target_ref,
        content_digest=content_digest,
        precondition_digest=precondition_digest,
        risk_level=risk_level,
        policy_version=policy_version,
    )
    return canonical_action_confirmation_payload(payload)


def build_action_fingerprint(
    *,
    origin_request_id: RequestId | str,
    session_id: SessionId | str,
    mission_id: MissionId | str | None,
    operator_identity_ref: str,
    handler_id: str,
    handler_version: str,
    operation: str,
    target_ref: str,
    content_digest: str,
    precondition_digest: str,
    risk_level: RiskLevel | str,
    policy_version: str,
) -> str:
    """Build the SHA-256 fingerprint of an exact action identity."""

    payload = canonical_action_fingerprint_payload(
        origin_request_id=origin_request_id,
        session_id=session_id,
        mission_id=mission_id,
        operator_identity_ref=operator_identity_ref,
        handler_id=handler_id,
        handler_version=handler_version,
        operation=operation,
        target_ref=target_ref,
        content_digest=content_digest,
        precondition_digest=precondition_digest,
        risk_level=risk_level,
        policy_version=policy_version,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def build_action_intent(
    *,
    intent_id: str,
    origin_request_id: RequestId | str,
    session_id: SessionId | str,
    mission_id: MissionId | str | None,
    operator_identity_ref: str,
    handler_id: str,
    handler_version: str,
    operation: str,
    target_ref: str,
    content_digest: str,
    precondition_digest: str,
    risk_level: RiskLevel | str,
    policy_version: str,
    nonce: str,
    issued_at: Timestamp,
    expires_at: Timestamp,
    now: datetime | Timestamp | None = None,
) -> ActionIntentContract:
    """Build and validate one immutable action intent with its exact fingerprint."""

    normalized_risk = RiskLevel(_risk_value(risk_level))
    intent = ActionIntentContract(
        intent_id=intent_id,
        origin_request_id=RequestId(str(origin_request_id)),
        session_id=SessionId(str(session_id)),
        mission_id=MissionId(str(mission_id)) if mission_id is not None else None,
        operator_identity_ref=operator_identity_ref,
        handler_id=handler_id,
        handler_version=handler_version,
        operation=operation,
        target_ref=target_ref,
        content_digest=content_digest,
        precondition_digest=precondition_digest,
        risk_level=normalized_risk,
        policy_version=policy_version,
        nonce=nonce,
        issued_at=issued_at,
        expires_at=expires_at,
        action_fingerprint=build_action_fingerprint(
            origin_request_id=origin_request_id,
            session_id=session_id,
            mission_id=mission_id,
            operator_identity_ref=operator_identity_ref,
            handler_id=handler_id,
            handler_version=handler_version,
            operation=operation,
            target_ref=target_ref,
            content_digest=content_digest,
            precondition_digest=precondition_digest,
            risk_level=normalized_risk,
            policy_version=policy_version,
        ),
    )
    require_valid_action_intent(intent, now=now)
    return intent


def action_confirmation_artifact_fingerprint(value: object) -> str:
    """Return the SHA-256 fingerprint of one complete confirmation artifact."""

    payload = canonical_action_confirmation_payload(value)
    return sha256(payload.encode("utf-8")).hexdigest()


action_intent_fingerprint = action_confirmation_artifact_fingerprint
action_confirmation_challenge_fingerprint = action_confirmation_artifact_fingerprint
human_confirmation_receipt_fingerprint = action_confirmation_artifact_fingerprint
action_confirmation_receipt_fingerprint = human_confirmation_receipt_fingerprint
action_confirmation_claim_fingerprint = action_confirmation_artifact_fingerprint


def verify_action_fingerprint(intent: ActionIntentContract) -> bool:
    """Return whether an intent still matches its exact action identity."""

    try:
        expected = build_action_fingerprint(
            origin_request_id=intent.origin_request_id,
            session_id=intent.session_id,
            mission_id=intent.mission_id,
            operator_identity_ref=intent.operator_identity_ref,
            handler_id=intent.handler_id,
            handler_version=intent.handler_version,
            operation=intent.operation,
            target_ref=intent.target_ref,
            content_digest=intent.content_digest,
            precondition_digest=intent.precondition_digest,
            risk_level=intent.risk_level,
            policy_version=intent.policy_version,
        )
        _require_sha256(intent.action_fingerprint, field_name="action_fingerprint")
    except (AttributeError, TypeError, ValueError):
        return False
    return compare_digest(intent.action_fingerprint, expected)


def verify_action_intent_fingerprint(
    intent: ActionIntentContract,
    expected_fingerprint: str,
) -> bool:
    return _verify_artifact_fingerprint(intent, expected_fingerprint)


def verify_action_confirmation_challenge_fingerprint(
    challenge: ActionConfirmationChallengeContract,
    expected_fingerprint: str,
) -> bool:
    return _verify_artifact_fingerprint(challenge, expected_fingerprint)


def verify_human_confirmation_receipt_fingerprint(
    receipt: HumanConfirmationReceiptContract,
    expected_fingerprint: str,
) -> bool:
    return _verify_artifact_fingerprint(receipt, expected_fingerprint)


def verify_action_confirmation_claim_fingerprint(
    claim: ActionConfirmationClaimContract,
    expected_fingerprint: str,
) -> bool:
    return _verify_artifact_fingerprint(claim, expected_fingerprint)


def validate_action_intent(
    intent: ActionIntentContract,
    *,
    now: datetime | Timestamp | None = None,
) -> list[str]:
    return _validation_failures(lambda: _require_action_intent(intent, now=now))


def require_valid_action_intent(
    intent: ActionIntentContract,
    *,
    now: datetime | Timestamp | None = None,
) -> None:
    _require_action_intent(intent, now=now)


def validate_action_confirmation_challenge(
    challenge: ActionConfirmationChallengeContract,
    *,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
) -> list[str]:
    return _validation_failures(
        lambda: _require_action_confirmation_challenge(
            challenge,
            intent=intent,
            now=now,
        )
    )


def require_valid_action_confirmation_challenge(
    challenge: ActionConfirmationChallengeContract,
    *,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
) -> None:
    _require_action_confirmation_challenge(challenge, intent=intent, now=now)


def validate_human_confirmation_receipt(
    receipt: HumanConfirmationReceiptContract,
    *,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
) -> list[str]:
    return _validation_failures(
        lambda: _require_human_confirmation_receipt(
            receipt,
            challenge=challenge,
            intent=intent,
            now=now,
        )
    )


def require_valid_human_confirmation_receipt(
    receipt: HumanConfirmationReceiptContract,
    *,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
) -> None:
    _require_human_confirmation_receipt(
        receipt,
        challenge=challenge,
        intent=intent,
        now=now,
    )


def validate_action_confirmation_claim(
    claim: ActionConfirmationClaimContract,
    *,
    receipt: HumanConfirmationReceiptContract,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
    expected_operation_id: OperationId | str | None = None,
) -> list[str]:
    return _validation_failures(
        lambda: _require_action_confirmation_claim(
            claim,
            receipt=receipt,
            challenge=challenge,
            intent=intent,
            now=now,
            expected_operation_id=expected_operation_id,
        )
    )


def require_valid_action_confirmation_claim(
    claim: ActionConfirmationClaimContract,
    *,
    receipt: HumanConfirmationReceiptContract,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None = None,
    expected_operation_id: OperationId | str | None = None,
) -> None:
    _require_action_confirmation_claim(
        claim,
        receipt=receipt,
        challenge=challenge,
        intent=intent,
        now=now,
        expected_operation_id=expected_operation_id,
    )


def _require_action_intent(
    intent: ActionIntentContract,
    *,
    now: datetime | Timestamp | None,
) -> None:
    if not isinstance(intent, ActionIntentContract):
        raise TypeError("action_intent_contract_required")
    _require_identifier(intent.intent_id, field_name="intent_id")
    _validated_action_identity(
        origin_request_id=intent.origin_request_id,
        session_id=intent.session_id,
        mission_id=intent.mission_id,
        operator_identity_ref=intent.operator_identity_ref,
        handler_id=intent.handler_id,
        handler_version=intent.handler_version,
        operation=intent.operation,
        target_ref=intent.target_ref,
        content_digest=intent.content_digest,
        precondition_digest=intent.precondition_digest,
        risk_level=intent.risk_level,
        policy_version=intent.policy_version,
    )
    _require_nonce(intent.nonce, field_name="nonce")
    issued_at = _parse_timestamp(intent.issued_at, field_name="issued_at")
    expires_at = _parse_timestamp(intent.expires_at, field_name="expires_at")
    _require_window(
        issued_at,
        expires_at,
        start_field="issued_at",
        artifact="action_intent",
        now=now,
    )
    _require_sha256(intent.action_fingerprint, field_name="action_fingerprint")
    if not verify_action_fingerprint(intent):
        raise ValueError("action_fingerprint_mismatch")
    _require_confirmation_invariants(intent)


def _require_action_confirmation_challenge(
    challenge: ActionConfirmationChallengeContract,
    *,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None,
) -> None:
    _require_action_intent(intent, now=now)
    if not isinstance(challenge, ActionConfirmationChallengeContract):
        raise TypeError("action_confirmation_challenge_contract_required")
    _require_identifier(challenge.challenge_id, field_name="challenge_id")
    _require_identifier(challenge.intent_id, field_name="intent_id")
    _require_sha256(challenge.intent_fingerprint, field_name="intent_fingerprint")
    _require_sha256(challenge.action_fingerprint, field_name="action_fingerprint")
    _require_identity_context(
        origin_request_id=challenge.origin_request_id,
        session_id=challenge.session_id,
        mission_id=challenge.mission_id,
        operator_identity_ref=challenge.operator_identity_ref,
    )
    _require_operation(challenge.operation, field_name="operation")
    _require_nonce(challenge.nonce, field_name="nonce")
    issued_at = _parse_timestamp(challenge.issued_at, field_name="issued_at")
    expires_at = _parse_timestamp(challenge.expires_at, field_name="expires_at")
    _require_window(
        issued_at,
        expires_at,
        start_field="issued_at",
        artifact="action_confirmation_challenge",
        now=now,
    )
    _require_confirmation_invariants(challenge)
    _require_equal(challenge.intent_id, intent.intent_id, "challenge_intent_id_mismatch")
    _require_fingerprint_equal(
        challenge.intent_fingerprint,
        action_intent_fingerprint(intent),
        "challenge_intent_fingerprint_mismatch",
    )
    _require_fingerprint_equal(
        challenge.action_fingerprint,
        intent.action_fingerprint,
        "challenge_action_fingerprint_mismatch",
    )
    _require_intent_context_match(challenge, intent, prefix="challenge")
    _require_equal(challenge.nonce, intent.nonce, "challenge_nonce_mismatch")
    _require_equal(challenge.issued_at, intent.issued_at, "challenge_issued_at_mismatch")
    _require_equal(challenge.expires_at, intent.expires_at, "challenge_expires_at_mismatch")


def _require_human_confirmation_receipt(
    receipt: HumanConfirmationReceiptContract,
    *,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None,
) -> None:
    _require_action_confirmation_challenge(challenge, intent=intent, now=now)
    if not isinstance(receipt, HumanConfirmationReceiptContract):
        raise TypeError("human_confirmation_receipt_contract_required")
    for field_name in ("receipt_id", "challenge_id", "intent_id"):
        _require_identifier(getattr(receipt, field_name), field_name=field_name)
    for field_name in (
        "challenge_fingerprint",
        "intent_fingerprint",
        "action_fingerprint",
    ):
        _require_sha256(getattr(receipt, field_name), field_name=field_name)
    _require_identity_context(
        origin_request_id=receipt.origin_request_id,
        session_id=receipt.session_id,
        mission_id=receipt.mission_id,
        operator_identity_ref=receipt.operator_identity_ref,
    )
    _require_operation(receipt.operation, field_name="operation")
    confirmed_at = _parse_timestamp(receipt.confirmed_at, field_name="confirmed_at")
    expires_at = _parse_timestamp(receipt.expires_at, field_name="expires_at")
    _require_window(
        confirmed_at,
        expires_at,
        start_field="confirmed_at",
        artifact="human_confirmation_receipt",
        now=now,
    )
    challenge_issued_at = _parse_timestamp(challenge.issued_at, field_name="issued_at")
    if confirmed_at < challenge_issued_at:
        raise ValueError("receipt_confirmed_before_challenge")
    _require_confirmation_invariants(receipt)
    _require_equal(
        receipt.challenge_id,
        challenge.challenge_id,
        "receipt_challenge_id_mismatch",
    )
    _require_fingerprint_equal(
        receipt.challenge_fingerprint,
        action_confirmation_challenge_fingerprint(challenge),
        "receipt_challenge_fingerprint_mismatch",
    )
    _require_equal(receipt.intent_id, intent.intent_id, "receipt_intent_id_mismatch")
    _require_fingerprint_equal(
        receipt.intent_fingerprint,
        action_intent_fingerprint(intent),
        "receipt_intent_fingerprint_mismatch",
    )
    _require_fingerprint_equal(
        receipt.action_fingerprint,
        intent.action_fingerprint,
        "receipt_action_fingerprint_mismatch",
    )
    _require_intent_context_match(receipt, intent, prefix="receipt")
    _require_equal(receipt.expires_at, challenge.expires_at, "receipt_expires_at_mismatch")


def _require_action_confirmation_claim(
    claim: ActionConfirmationClaimContract,
    *,
    receipt: HumanConfirmationReceiptContract,
    challenge: ActionConfirmationChallengeContract,
    intent: ActionIntentContract,
    now: datetime | Timestamp | None,
    expected_operation_id: OperationId | str | None,
) -> None:
    _require_human_confirmation_receipt(
        receipt,
        challenge=challenge,
        intent=intent,
        now=now,
    )
    if not isinstance(claim, ActionConfirmationClaimContract):
        raise TypeError("action_confirmation_claim_contract_required")
    for field_name in ("claim_id", "receipt_id", "intent_id", "operation_id"):
        _require_identifier(getattr(claim, field_name), field_name=field_name)
    for field_name in (
        "receipt_fingerprint",
        "intent_fingerprint",
        "action_fingerprint",
    ):
        _require_sha256(getattr(claim, field_name), field_name=field_name)
    _require_identity_context(
        origin_request_id=claim.origin_request_id,
        session_id=claim.session_id,
        mission_id=claim.mission_id,
        operator_identity_ref=claim.operator_identity_ref,
    )
    _require_operation(claim.operation, field_name="operation")
    claimed_at = _parse_timestamp(claim.claimed_at, field_name="claimed_at")
    expires_at = _parse_timestamp(claim.expires_at, field_name="expires_at")
    _require_window(
        claimed_at,
        expires_at,
        start_field="claimed_at",
        artifact="action_confirmation_claim",
        now=now,
    )
    receipt_confirmed_at = _parse_timestamp(receipt.confirmed_at, field_name="confirmed_at")
    if claimed_at < receipt_confirmed_at:
        raise ValueError("claim_created_before_confirmation")
    _require_confirmation_invariants(claim)
    _require_equal(claim.receipt_id, receipt.receipt_id, "claim_receipt_id_mismatch")
    _require_fingerprint_equal(
        claim.receipt_fingerprint,
        human_confirmation_receipt_fingerprint(receipt),
        "claim_receipt_fingerprint_mismatch",
    )
    _require_equal(claim.intent_id, intent.intent_id, "claim_intent_id_mismatch")
    _require_fingerprint_equal(
        claim.intent_fingerprint,
        action_intent_fingerprint(intent),
        "claim_intent_fingerprint_mismatch",
    )
    _require_fingerprint_equal(
        claim.action_fingerprint,
        intent.action_fingerprint,
        "claim_action_fingerprint_mismatch",
    )
    _require_intent_context_match(claim, intent, prefix="claim")
    _require_equal(claim.expires_at, receipt.expires_at, "claim_expires_at_mismatch")
    if expected_operation_id is not None:
        _require_identifier(expected_operation_id, field_name="expected_operation_id")
        _require_equal(
            str(claim.operation_id),
            str(expected_operation_id),
            "claim_operation_id_mismatch",
        )


def _validated_action_identity(
    *,
    origin_request_id: RequestId | str,
    session_id: SessionId | str,
    mission_id: MissionId | str | None,
    operator_identity_ref: str,
    handler_id: str,
    handler_version: str,
    operation: str,
    target_ref: str,
    content_digest: str,
    precondition_digest: str,
    risk_level: RiskLevel | str,
    policy_version: str,
) -> dict[str, object]:
    _require_identity_context(
        origin_request_id=origin_request_id,
        session_id=session_id,
        mission_id=mission_id,
        operator_identity_ref=operator_identity_ref,
    )
    _require_identifier(handler_id, field_name="handler_id")
    _require_identifier(handler_version, field_name="handler_version")
    _require_operation(operation, field_name="operation")
    _require_identifier(target_ref, field_name="target_ref")
    _require_sha256(content_digest, field_name="content_digest")
    _require_sha256(precondition_digest, field_name="precondition_digest")
    risk_value = _risk_value(risk_level)
    _require_identifier(policy_version, field_name="policy_version")
    return {
        "origin_request_id": str(origin_request_id),
        "session_id": str(session_id),
        "mission_id": str(mission_id) if mission_id is not None else None,
        "operator_identity_ref": operator_identity_ref,
        "handler_id": handler_id,
        "handler_version": handler_version,
        "operation": operation,
        "target_ref": target_ref,
        "content_digest": content_digest,
        "precondition_digest": precondition_digest,
        "risk_level": risk_value,
        "policy_version": policy_version,
    }


def _require_identity_context(
    *,
    origin_request_id: RequestId | str,
    session_id: SessionId | str,
    mission_id: MissionId | str | None,
    operator_identity_ref: str,
) -> None:
    _require_identifier(origin_request_id, field_name="origin_request_id")
    _require_identifier(session_id, field_name="session_id")
    if mission_id is not None:
        _require_identifier(mission_id, field_name="mission_id")
    _require_identifier(operator_identity_ref, field_name="operator_identity_ref")


def _require_intent_context_match(
    artifact: object,
    intent: ActionIntentContract,
    *,
    prefix: str,
) -> None:
    for field_name in (
        "origin_request_id",
        "session_id",
        "mission_id",
        "operator_identity_ref",
        "operation",
    ):
        _require_equal(
            getattr(artifact, field_name),
            getattr(intent, field_name),
            f"{prefix}_{field_name}_mismatch",
        )


def _require_confirmation_invariants(value: object) -> None:
    if getattr(value, "single_use", None) is not True:
        raise ValueError("single_use_must_be_true")
    if getattr(value, "read_only", None) is not True:
        raise ValueError("read_only_must_be_true")
    if getattr(value, "immutable", None) is not True:
        raise ValueError("immutable_must_be_true")
    for field_name in _AUTHORITY_FALSE_FIELDS:
        if getattr(value, field_name, None) is not False:
            raise ValueError(f"{field_name}_must_be_false")


def _require_identifier(value: object, *, field_name: str) -> None:
    if (
        not isinstance(value, str)
        or not fullmatch(_IDENTIFIER_PATTERN, value)
        or value != normalize("NFC", value)
        or any(category(char).startswith("C") for char in value)
    ):
        raise ValueError(f"{field_name}_must_be_canonical_identifier")


def _require_operation(value: object, *, field_name: str) -> None:
    if not isinstance(value, str) or not fullmatch(_OPERATION_PATTERN, value):
        raise ValueError(f"{field_name}_must_be_canonical_operation")


def _require_nonce(value: object, *, field_name: str) -> None:
    if not isinstance(value, str) or not fullmatch(_NONCE_PATTERN, value):
        raise ValueError(f"{field_name}_must_be_canonical_nonce")


def _require_sha256(value: object, *, field_name: str) -> None:
    if not isinstance(value, str) or not fullmatch(_SHA256_PATTERN, value):
        raise ValueError(f"{field_name}_must_be_lowercase_sha256")


def _risk_value(value: RiskLevel | str) -> str:
    normalized = value.value if isinstance(value, RiskLevel) else value
    if normalized not in {item.value for item in RiskLevel}:
        raise ValueError("risk_level_must_be_canonical")
    return normalized


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name}_must_be_iso8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name}_must_be_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field_name}_must_include_timezone")
    if not fullmatch(_TIMESTAMP_PATTERN, value):
        raise ValueError(f"{field_name}_must_be_canonical_iso8601")
    return parsed


def _parse_now(value: datetime | Timestamp) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("now_must_include_timezone")
        return value
    return _parse_timestamp(value, field_name="now")


def _require_window(
    start: datetime,
    expires_at: datetime,
    *,
    start_field: str,
    artifact: str,
    now: datetime | Timestamp | None,
) -> None:
    if expires_at <= start:
        raise ValueError(f"expires_at_must_be_after_{start_field}")
    if now is None:
        return
    comparison_now = _parse_now(now)
    if comparison_now < start:
        raise ValueError(f"{artifact}_not_yet_valid")
    if comparison_now >= expires_at:
        raise ValueError(f"{artifact}_expired")


def _require_equal(actual: object, expected: object, error: str) -> None:
    if actual != expected:
        raise ValueError(error)


def _require_fingerprint_equal(actual: str, expected: str, error: str) -> None:
    if not compare_digest(actual, expected):
        raise ValueError(error)


def _verify_artifact_fingerprint(value: object, expected_fingerprint: str) -> bool:
    try:
        _require_sha256(expected_fingerprint, field_name="expected_fingerprint")
        actual = action_confirmation_artifact_fingerprint(value)
    except (TypeError, ValueError):
        return False
    return compare_digest(actual, expected_fingerprint)


def _json_value(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical_json_object_keys_must_be_strings")
            result[key] = _json_value(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("canonical_json_numbers_must_be_finite")
        return value
    raise TypeError(f"unsupported_canonical_json_type:{type(value).__name__}")


def _validation_failures(validation: Any) -> list[str]:
    try:
        validation()
    except (AttributeError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []
