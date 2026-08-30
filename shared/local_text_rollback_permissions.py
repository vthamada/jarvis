"""Dedicated local-text rollback evidence, allowlist, grants, and claims."""

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from hmac import compare_digest
from json import dumps
from re import fullmatch
from unicodedata import is_normalized

from shared.action_confirmation import action_intent_fingerprint, validate_action_intent
from shared.adapter_execution_permissions import (
    validate_adapter_execution_grant_claim_fingerprint,
    validate_adapter_execution_grant_fingerprint,
)
from shared.adapter_permissions import autonomy_policy_decision_fingerprint
from shared.autonomy_ladder import AUTONOMY_ACTION_POLICY_VERSION
from shared.contracts import (
    ActionIntentContract,
    AdapterExecutionGrantClaimContract,
    AdapterExecutionGrantContract,
    AutonomyActionPolicyDecisionContract,
    LocalTextFileRollbackDescriptorContract,
    LocalTextFileRollbackGrantClaimContract,
    LocalTextFileRollbackGrantContract,
    LocalTextFileRollbackRegistrySnapshotContract,
    LocalTextFileRollbackRequestContract,
    LocalTextMutationReceipt,
    LocalTextRollbackReceipt,
)
from shared.types import OperationId, Timestamp

_ID = r"[a-z][a-z0-9_.-]{0,127}"
_REF = r"[^\x00-\x1f\x7f*?]{1,512}"
_RESOURCE_REF = r"[a-z][a-z0-9+.-]{1,31}:[^\x00-\x20\x7f\\*?]{1,479}"
_SHA256 = r"[0-9a-f]{64}"
_NONCE = r"[A-Za-z0-9_-]{16,128}"
_SEMVER = (
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
_AUTHORITY_FIELDS = (
    "execution_allowed",
    "tool_dispatch_allowed",
    "runtime_activation_allowed",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
)
_EMPTY_SHA256 = sha256(b"").hexdigest()

LOCAL_TEXT_FILE_ROLLBACK_ADAPTER_VERSION = "3.0.0"
LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION = "local-text-file-rollback-policy/v1"
LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION = "local-text-transactional-writer/v1"
LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS = 120
LOCAL_TEXT_TRANSACTION_POLICY_VERSION = "1.0.0"
LOCAL_TEXT_TRANSACTION_BACKEND_VERSION = "posix-openat-1.0.0"


def _canonical(value: object) -> str:
    return dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _digest(value: object) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _without(value: object, field: str) -> dict[str, object]:
    payload = asdict(value)  # type: ignore[arg-type]
    payload.pop(field, None)
    return payload


def _parse_time(value: Timestamp | datetime) -> datetime:
    parsed = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    )
    if parsed.tzinfo is None:
        raise ValueError("timestamp_not_timezone_aware")
    return parsed.astimezone(timezone.utc)


def _canonical_time(value: Timestamp | datetime) -> str:
    return _parse_time(value).isoformat().replace("+00:00", "Z")


def _errors(check) -> list[str]:  # type: ignore[no-untyped-def]
    try:
        check()
    except (AttributeError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []


def _require_match(value: str, pattern: str, error: str) -> None:
    if not isinstance(value, str) or fullmatch(pattern, value) is None:
        raise ValueError(error)


def _require_sha256(value: str, error: str) -> None:
    _require_match(value, _SHA256, error)


def _require_ref(value: str, *, resource: bool, error: str) -> None:
    _require_match(value, _RESOURCE_REF if resource else _REF, error)
    if value != value.strip() or not is_normalized("NFC", value) or "\\" in value:
        raise ValueError(error)
    payload = value.split(":", 1)[1] if resource else value
    if any(segment in {".", ".."} for segment in payload.split("/")):
        raise ValueError(error)


def _require_metadata_only(value: object) -> None:
    if not getattr(value, "read_only", False) or not getattr(value, "immutable", False):
        raise ValueError("local_text_rollback_artifact_not_immutable_metadata")
    if any(getattr(value, field, False) for field in _AUTHORITY_FIELDS):
        raise ValueError("local_text_rollback_artifact_authority_flag_true")


def build_mutation_receipt_fingerprint(receipt: LocalTextMutationReceipt) -> str:
    return _digest(_without(receipt, "receipt_fingerprint"))


def validate_mutation_receipt_fingerprint(receipt: LocalTextMutationReceipt) -> bool:
    return bool(fullmatch(_SHA256, receipt.receipt_fingerprint)) and compare_digest(
        receipt.receipt_fingerprint,
        build_mutation_receipt_fingerprint(receipt),
    )


def validate_local_text_mutation_receipt(receipt: LocalTextMutationReceipt) -> list[str]:
    return _errors(lambda: require_valid_local_text_mutation_receipt(receipt))


def require_valid_local_text_mutation_receipt(receipt: LocalTextMutationReceipt) -> None:
    if not isinstance(receipt, LocalTextMutationReceipt):
        raise TypeError("local_text_mutation_receipt_required")
    for value, error in (
        (receipt.operation_id, "local_text_mutation_operation_id_invalid"),
        (receipt.execution_grant_id, "local_text_mutation_grant_id_invalid"),
        (receipt.execution_claim_id, "local_text_mutation_claim_id_invalid"),
        (receipt.subject_ref, "local_text_mutation_subject_ref_invalid"),
    ):
        _require_ref(value, resource=False, error=error)
    _require_ref(
        receipt.resource_ref,
        resource=True,
        error="local_text_mutation_resource_ref_invalid",
    )
    for value in (
        receipt.preflight_fingerprint,
        receipt.before_content_sha256,
        receipt.desired_content_sha256,
        receipt.root_config_fingerprint,
        receipt.applied_event_fingerprint,
    ):
        _require_sha256(value, "local_text_mutation_sha256_invalid")
    if receipt.operation not in {"create_text", "replace_text"}:
        raise ValueError("local_text_mutation_operation_invalid")
    if receipt.operation == "create_text" and receipt.before_content_sha256 != _EMPTY_SHA256:
        raise ValueError("local_text_mutation_create_before_digest_invalid")
    if receipt.before_content_sha256 == receipt.desired_content_sha256:
        raise ValueError("local_text_mutation_no_change_invalid")
    _parse_time(receipt.committed_at)
    if receipt.mutation_status != "applied" or not receipt.rollback_available:
        raise ValueError("local_text_mutation_status_invalid")
    _require_metadata_only(receipt)
    if not validate_mutation_receipt_fingerprint(receipt):
        raise ValueError("local_text_mutation_receipt_fingerprint_invalid")


def build_rollback_receipt_fingerprint(receipt: LocalTextRollbackReceipt) -> str:
    return _digest(_without(receipt, "rollback_receipt_fingerprint"))


def validate_rollback_receipt_fingerprint(receipt: LocalTextRollbackReceipt) -> bool:
    return bool(fullmatch(_SHA256, receipt.rollback_receipt_fingerprint)) and compare_digest(
        receipt.rollback_receipt_fingerprint,
        build_rollback_receipt_fingerprint(receipt),
    )


def validate_local_text_rollback_receipt(receipt: LocalTextRollbackReceipt) -> list[str]:
    return _errors(lambda: require_valid_local_text_rollback_receipt(receipt))


def require_valid_local_text_rollback_receipt(receipt: LocalTextRollbackReceipt) -> None:
    if not isinstance(receipt, LocalTextRollbackReceipt):
        raise TypeError("local_text_rollback_receipt_required")
    for value, error in (
        (receipt.operation_id, "local_text_rollback_receipt_operation_id_invalid"),
        (
            receipt.mutation_operation_id,
            "local_text_rollback_receipt_mutation_operation_id_invalid",
        ),
        (receipt.rollback_grant_id, "local_text_rollback_receipt_grant_id_invalid"),
        (receipt.rollback_claim_id, "local_text_rollback_receipt_claim_id_invalid"),
    ):
        _require_ref(value, resource=False, error=error)
    _require_ref(
        receipt.resource_ref,
        resource=True,
        error="local_text_rollback_receipt_resource_invalid",
    )
    for value in (
        receipt.mutation_receipt_fingerprint,
        receipt.restored_content_sha256,
        receipt.rolled_back_event_fingerprint,
    ):
        _require_sha256(value, "local_text_rollback_receipt_sha256_invalid")
    _parse_time(receipt.rolled_back_at)
    _require_metadata_only(receipt)
    if not validate_rollback_receipt_fingerprint(receipt):
        raise ValueError("local_text_rollback_receipt_fingerprint_invalid")


def build_local_text_file_rollback_descriptor_fingerprint(
    descriptor: LocalTextFileRollbackDescriptorContract,
) -> str:
    return _digest(_without(descriptor, "descriptor_fingerprint"))


def require_valid_local_text_file_rollback_descriptor(
    descriptor: LocalTextFileRollbackDescriptorContract,
) -> None:
    if not isinstance(descriptor, LocalTextFileRollbackDescriptorContract):
        raise TypeError("local_text_rollback_descriptor_required")
    _require_match(descriptor.adapter_id, _ID, "local_text_rollback_adapter_id_invalid")
    _require_match(
        descriptor.adapter_version,
        _SEMVER,
        "local_text_rollback_adapter_version_invalid",
    )
    if (
        descriptor.adapter_id != "local_text_file"
        or descriptor.adapter_version != LOCAL_TEXT_FILE_ROLLBACK_ADAPTER_VERSION
        or descriptor.action_kind != "execute_external_action"
        or descriptor.purpose != "rollback"
        or descriptor.allowed_operations != ("rollback_text",)
        or descriptor.allowed_resource_scopes != ("configured_text_root",)
        or descriptor.rollback_policy_version != LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION
        or descriptor.rollback_backend_version != LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION
        or not descriptor.rollback_only
    ):
        raise ValueError("local_text_rollback_descriptor_binding_invalid")
    _require_ref(
        descriptor.executor_ref,
        resource=False,
        error="local_text_rollback_executor_ref_invalid",
    )
    _require_metadata_only(descriptor)
    expected = build_local_text_file_rollback_descriptor_fingerprint(descriptor)
    if not compare_digest(descriptor.descriptor_fingerprint, expected):
        raise ValueError("local_text_rollback_descriptor_fingerprint_invalid")


def build_local_text_file_rollback_descriptor() -> LocalTextFileRollbackDescriptorContract:
    descriptor = LocalTextFileRollbackDescriptorContract(
        adapter_id="local_text_file",
        adapter_version=LOCAL_TEXT_FILE_ROLLBACK_ADAPTER_VERSION,
        action_kind="execute_external_action",
        purpose="rollback",
        allowed_operations=("rollback_text",),
        allowed_resource_scopes=("configured_text_root",),
        executor_ref="adapter-rollback-executor://local_text_file",
        rollback_policy_version=LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION,
        rollback_backend_version=LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION,
        descriptor_fingerprint="0" * 64,
    )
    descriptor = replace(
        descriptor,
        descriptor_fingerprint=build_local_text_file_rollback_descriptor_fingerprint(descriptor),
    )
    require_valid_local_text_file_rollback_descriptor(descriptor)
    return descriptor


def build_local_text_file_rollback_registry_fingerprint(
    registry: LocalTextFileRollbackRegistrySnapshotContract,
) -> str:
    return _digest(_without(registry, "registry_fingerprint"))


def require_valid_local_text_file_rollback_registry(
    registry: LocalTextFileRollbackRegistrySnapshotContract,
) -> None:
    if not isinstance(registry, LocalTextFileRollbackRegistrySnapshotContract):
        raise TypeError("local_text_rollback_registry_required")
    _require_match(registry.registry_id, _ID, "local_text_rollback_registry_id_invalid")
    _require_match(
        registry.registry_version,
        _SEMVER,
        "local_text_rollback_registry_version_invalid",
    )
    keys = [(item.adapter_id, item.adapter_version) for item in registry.descriptors]
    if len(keys) != len(set(keys)) or keys != sorted(keys):
        raise ValueError("local_text_rollback_registry_order_or_duplicate_invalid")
    for descriptor in registry.descriptors:
        require_valid_local_text_file_rollback_descriptor(descriptor)
    _require_metadata_only(registry)
    expected = build_local_text_file_rollback_registry_fingerprint(registry)
    if not compare_digest(registry.registry_fingerprint, expected):
        raise ValueError("local_text_rollback_registry_fingerprint_invalid")


def build_local_text_file_rollback_registry_snapshot(
    *,
    registry_id: str,
    registry_version: str,
    descriptors: tuple[LocalTextFileRollbackDescriptorContract, ...],
) -> LocalTextFileRollbackRegistrySnapshotContract:
    registry = LocalTextFileRollbackRegistrySnapshotContract(
        registry_id=registry_id,
        registry_version=registry_version,
        descriptors=tuple(
            sorted(
                descriptors,
                key=lambda item: (item.adapter_id, item.adapter_version),
            )
        ),
        registry_fingerprint="0" * 64,
    )
    registry = replace(
        registry,
        registry_fingerprint=build_local_text_file_rollback_registry_fingerprint(registry),
    )
    require_valid_local_text_file_rollback_registry(registry)
    return registry


def resolve_local_text_file_rollback_descriptor(
    registry: LocalTextFileRollbackRegistrySnapshotContract,
    *,
    adapter_id: str,
    adapter_version: str,
) -> LocalTextFileRollbackDescriptorContract | None:
    try:
        require_valid_local_text_file_rollback_registry(registry)
    except (TypeError, ValueError):
        return None
    return next(
        (
            item
            for item in registry.descriptors
            if item.adapter_id == adapter_id and item.adapter_version == adapter_version
        ),
        None,
    )


def build_local_text_file_rollback_request_fingerprint(
    request: LocalTextFileRollbackRequestContract,
) -> str:
    return _digest(_without(request, "rollback_request_fingerprint"))


def build_local_text_file_rollback_request(
    receipt: LocalTextMutationReceipt,
    *,
    source_execution_grant: AdapterExecutionGrantContract,
    source_execution_claim: AdapterExecutionGrantClaimContract,
    rollback_operation_id: OperationId | str,
    requested_at: Timestamp | datetime,
    expires_at: Timestamp | datetime | None = None,
) -> LocalTextFileRollbackRequestContract:
    require_valid_local_text_mutation_receipt(receipt)
    if not validate_adapter_execution_grant_fingerprint(source_execution_grant):
        raise ValueError("local_text_rollback_source_grant_fingerprint_invalid")
    if not validate_adapter_execution_grant_claim_fingerprint(source_execution_claim):
        raise ValueError("local_text_rollback_source_claim_fingerprint_invalid")
    request_time = _parse_time(requested_at)
    request_expires = (
        _parse_time(expires_at)
        if expires_at is not None
        else request_time + timedelta(seconds=LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS)
    )
    execution_request = source_execution_grant.execution_request
    expected_receipt = (
        source_execution_grant.grant_id,
        source_execution_claim.claim_id,
        str(source_execution_claim.operation_id),
        execution_request.operation,
        execution_request.resource_ref,
        execution_request.subject_ref,
        execution_request.preflight_fingerprint,
        execution_request.before_content_sha256,
        execution_request.desired_content_sha256,
        execution_request.root_config_fingerprint,
    )
    observed_receipt = (
        receipt.execution_grant_id,
        receipt.execution_claim_id,
        receipt.operation_id,
        receipt.operation,
        receipt.resource_ref,
        receipt.subject_ref,
        receipt.preflight_fingerprint,
        receipt.before_content_sha256,
        receipt.desired_content_sha256,
        receipt.root_config_fingerprint,
    )
    if observed_receipt != expected_receipt:
        raise ValueError("local_text_rollback_mutation_receipt_source_mismatch")
    if source_execution_claim.grant_id != source_execution_grant.grant_id:
        raise ValueError("local_text_rollback_source_claim_grant_mismatch")
    rollback_id = OperationId(str(rollback_operation_id))
    if str(rollback_id) == receipt.operation_id:
        raise ValueError("local_text_rollback_operation_id_not_distinct")
    restored = (
        _EMPTY_SHA256
        if execution_request.operation == "create_text"
        else execution_request.before_content_sha256
    )
    request = LocalTextFileRollbackRequestContract(
        purpose="rollback",
        adapter_id=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_id,
        adapter_version=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.adapter_version,
        action_kind=LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR.action_kind,
        operation="rollback_text",
        resource_scope=execution_request.resource_scope,
        resource_ref=execution_request.resource_ref,
        subject_ref=execution_request.subject_ref,
        rollback_operation_id=rollback_id,
        mutation_operation_id=OperationId(receipt.operation_id),
        mutation_receipt_fingerprint=receipt.receipt_fingerprint,
        mutation_applied_event_fingerprint=receipt.applied_event_fingerprint,
        mutation_committed_at=receipt.committed_at,
        source_execution_grant_id=source_execution_grant.grant_id,
        source_execution_grant_fingerprint=source_execution_grant.grant_fingerprint,
        source_execution_claim_id=source_execution_claim.claim_id,
        source_execution_claim_fingerprint=source_execution_claim.claim_fingerprint,
        source_execution_request_fingerprint=(execution_request.execution_request_fingerprint),
        source_preflight_attestation_id=execution_request.preflight_attestation_id,
        source_preflight_attestation_fingerprint=(
            execution_request.preflight_attestation_fingerprint
        ),
        source_preflight_fingerprint=execution_request.preflight_fingerprint,
        source_action_fingerprint=source_execution_grant.action_fingerprint,
        source_intent_fingerprint=source_execution_grant.intent_fingerprint,
        original_operation=execution_request.operation,
        root_config_fingerprint=execution_request.root_config_fingerprint,
        expected_current_sha256=execution_request.desired_content_sha256,
        restored_content_sha256=restored,
        original_before_content_sha256=execution_request.before_content_sha256,
        original_desired_content_sha256=execution_request.desired_content_sha256,
        rollback_plan_fingerprint=execution_request.rollback_fingerprint,
        source_preflight_policy_version=execution_request.preflight_policy_version,
        source_preflight_backend_version=execution_request.preflight_backend_version,
        source_execution_policy_version=execution_request.execution_policy_version,
        source_execution_backend_version=execution_request.execution_backend_version,
        transaction_policy_version=LOCAL_TEXT_TRANSACTION_POLICY_VERSION,
        transaction_backend_version=LOCAL_TEXT_TRANSACTION_BACKEND_VERSION,
        rollback_policy_version=LOCAL_TEXT_FILE_ROLLBACK_POLICY_VERSION,
        rollback_backend_version=LOCAL_TEXT_FILE_ROLLBACK_BACKEND_VERSION,
        requested_at=_canonical_time(request_time),
        expires_at=_canonical_time(request_expires),
        rollback_request_fingerprint="0" * 64,
    )
    request = replace(
        request,
        rollback_request_fingerprint=build_local_text_file_rollback_request_fingerprint(request),
    )
    require_valid_local_text_file_rollback_request(request, now=request_time)
    return request


def validate_local_text_file_rollback_request(
    request: LocalTextFileRollbackRequestContract,
    *,
    now: Timestamp | datetime | None = None,
) -> list[str]:
    return _errors(lambda: require_valid_local_text_file_rollback_request(request, now=now))


def require_valid_local_text_file_rollback_request(
    request: LocalTextFileRollbackRequestContract,
    *,
    now: Timestamp | datetime | None = None,
) -> None:
    if not isinstance(request, LocalTextFileRollbackRequestContract):
        raise TypeError("local_text_rollback_request_required")
    descriptor = LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR
    if (
        request.purpose != "rollback"
        or (request.adapter_id, request.adapter_version, request.action_kind)
        != (descriptor.adapter_id, descriptor.adapter_version, descriptor.action_kind)
        or request.operation != "rollback_text"
        or request.resource_scope != "configured_text_root"
        or request.original_operation not in {"create_text", "replace_text"}
        or str(request.rollback_operation_id) == str(request.mutation_operation_id)
    ):
        raise ValueError("local_text_rollback_request_scope_invalid")
    for value, error in (
        (request.subject_ref, "local_text_rollback_subject_ref_invalid"),
        (request.source_execution_grant_id, "local_text_rollback_source_grant_id_invalid"),
        (request.source_execution_claim_id, "local_text_rollback_source_claim_id_invalid"),
        (str(request.rollback_operation_id), "local_text_rollback_operation_id_invalid"),
        (str(request.mutation_operation_id), "local_text_mutation_operation_id_invalid"),
    ):
        _require_ref(value, resource=False, error=error)
    _require_ref(
        request.resource_ref,
        resource=True,
        error="local_text_rollback_resource_ref_invalid",
    )
    for value in (
        request.mutation_receipt_fingerprint,
        request.mutation_applied_event_fingerprint,
        request.source_execution_grant_fingerprint,
        request.source_execution_claim_fingerprint,
        request.source_execution_request_fingerprint,
        request.source_preflight_attestation_fingerprint,
        request.source_preflight_fingerprint,
        request.source_action_fingerprint,
        request.source_intent_fingerprint,
        request.root_config_fingerprint,
        request.expected_current_sha256,
        request.restored_content_sha256,
        request.original_before_content_sha256,
        request.original_desired_content_sha256,
        request.rollback_plan_fingerprint,
    ):
        _require_sha256(value, "local_text_rollback_request_sha256_invalid")
    _require_ref(
        request.source_preflight_attestation_id,
        resource=False,
        error="local_text_rollback_attestation_id_invalid",
    )
    if (
        request.expected_current_sha256 != request.original_desired_content_sha256
        or (
            request.original_operation == "create_text"
            and (
                request.original_before_content_sha256 != _EMPTY_SHA256
                or request.restored_content_sha256 != _EMPTY_SHA256
            )
        )
        or (
            request.original_operation == "replace_text"
            and request.restored_content_sha256 != request.original_before_content_sha256
        )
    ):
        raise ValueError("local_text_rollback_content_binding_invalid")
    if (
        request.transaction_policy_version != LOCAL_TEXT_TRANSACTION_POLICY_VERSION
        or request.transaction_backend_version != LOCAL_TEXT_TRANSACTION_BACKEND_VERSION
        or request.rollback_policy_version != descriptor.rollback_policy_version
        or request.rollback_backend_version != descriptor.rollback_backend_version
    ):
        raise ValueError("local_text_rollback_policy_or_backend_invalid")
    committed = _parse_time(request.mutation_committed_at)
    requested = _parse_time(request.requested_at)
    expires = _parse_time(request.expires_at)
    if committed > requested or requested >= expires:
        raise ValueError("local_text_rollback_request_window_invalid")
    if (expires - requested).total_seconds() > LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS:
        raise ValueError("local_text_rollback_request_ttl_invalid")
    if now is not None:
        current = _parse_time(now)
        if current < requested or current >= expires:
            raise ValueError("local_text_rollback_request_inactive")
    _require_metadata_only(request)
    expected = build_local_text_file_rollback_request_fingerprint(request)
    if not compare_digest(request.rollback_request_fingerprint, expected):
        raise ValueError("local_text_rollback_request_fingerprint_invalid")


def build_local_text_file_rollback_grant_fingerprint(
    grant: LocalTextFileRollbackGrantContract,
) -> str:
    return _digest(_without(grant, "grant_fingerprint"))


def build_local_text_file_rollback_grant(
    *,
    grant_id: str,
    request: LocalTextFileRollbackRequestContract,
    descriptor: LocalTextFileRollbackDescriptorContract,
    registry: LocalTextFileRollbackRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    nonce: str,
    issued_at: Timestamp,
    expires_at: Timestamp,
    now: Timestamp | datetime,
) -> LocalTextFileRollbackGrantContract:
    grant = LocalTextFileRollbackGrantContract(
        grant_id=grant_id,
        subject_ref=request.subject_ref,
        rollback_request=request,
        descriptor_fingerprint=descriptor.descriptor_fingerprint,
        registry_fingerprint=registry.registry_fingerprint,
        intent_id=intent.intent_id,
        intent_fingerprint=intent_fingerprint,
        action_fingerprint=intent.action_fingerprint,
        autonomy_policy_decision_fingerprint=autonomy_policy_decision_fingerprint(
            autonomy_decision
        ),
        policy_version=AUTONOMY_ACTION_POLICY_VERSION,
        nonce=nonce,
        confirmation_required=True,
        issued_at=issued_at,
        expires_at=expires_at,
        grant_fingerprint="0" * 64,
    )
    grant = replace(
        grant,
        grant_fingerprint=build_local_text_file_rollback_grant_fingerprint(grant),
    )
    require_valid_local_text_file_rollback_grant(
        grant,
        descriptor=descriptor,
        registry=registry,
        intent=intent,
        intent_fingerprint=intent_fingerprint,
        autonomy_decision=autonomy_decision,
        now=now,
    )
    return grant


def require_valid_local_text_file_rollback_grant(
    grant: LocalTextFileRollbackGrantContract,
    *,
    descriptor: LocalTextFileRollbackDescriptorContract,
    registry: LocalTextFileRollbackRegistrySnapshotContract,
    intent: ActionIntentContract,
    intent_fingerprint: str,
    autonomy_decision: AutonomyActionPolicyDecisionContract,
    now: Timestamp | datetime,
) -> None:
    if not isinstance(grant, LocalTextFileRollbackGrantContract):
        raise TypeError("local_text_rollback_grant_required")
    _require_ref(grant.grant_id, resource=False, error="local_text_rollback_grant_id_invalid")
    _require_ref(grant.subject_ref, resource=False, error="local_text_rollback_subject_invalid")
    _require_match(grant.nonce, _NONCE, "local_text_rollback_grant_nonce_invalid")
    require_valid_local_text_file_rollback_registry(registry)
    require_valid_local_text_file_rollback_descriptor(descriptor)
    require_valid_local_text_file_rollback_request(grant.rollback_request)
    resolved = resolve_local_text_file_rollback_descriptor(
        registry,
        adapter_id=grant.rollback_request.adapter_id,
        adapter_version=grant.rollback_request.adapter_version,
    )
    if (
        resolved != descriptor
        or grant.descriptor_fingerprint != descriptor.descriptor_fingerprint
        or grant.registry_fingerprint != registry.registry_fingerprint
        or grant.subject_ref != grant.rollback_request.subject_ref
    ):
        raise ValueError("local_text_rollback_grant_registry_binding_invalid")
    if validate_action_intent(intent, now=grant.issued_at):
        raise ValueError("local_text_rollback_intent_invalid")
    if not compare_digest(action_intent_fingerprint(intent), intent_fingerprint):
        raise ValueError("local_text_rollback_intent_fingerprint_invalid")
    request = grant.rollback_request
    if (
        (grant.intent_id, grant.intent_fingerprint, grant.action_fingerprint)
        != (intent.intent_id, intent_fingerprint, intent.action_fingerprint)
        or intent.operator_identity_ref != request.subject_ref
        or intent.operation != "rollback_text"
        or intent.target_ref != request.resource_ref
        or intent.handler_id != descriptor.executor_ref
        or intent.handler_version != descriptor.adapter_version
        or intent.content_digest != request.restored_content_sha256
        or intent.precondition_digest != request.rollback_request_fingerprint
    ):
        raise ValueError("local_text_rollback_intent_exact_binding_mismatch")
    if grant.autonomy_policy_decision_fingerprint != autonomy_policy_decision_fingerprint(
        autonomy_decision
    ):
        raise ValueError("local_text_rollback_autonomy_decision_drift")
    if (
        grant.policy_version != AUTONOMY_ACTION_POLICY_VERSION
        or intent.policy_version != AUTONOMY_ACTION_POLICY_VERSION
        or autonomy_decision.policy_version != AUTONOMY_ACTION_POLICY_VERSION
        or autonomy_decision.action_kind != "execute_external_action"
        or autonomy_decision.decision != "require_confirmation"
        or not autonomy_decision.confirmation_required
        or autonomy_decision.confirmation_requirement != "explicit_confirmation_required"
        or autonomy_decision.confirmation_evidence_state != "absent"
        or autonomy_decision.side_effect_allowed
        or autonomy_decision.reason_codes != ("exact_confirmation_required",)
    ):
        raise ValueError("local_text_rollback_autonomy_decision_invalid")
    issued = _parse_time(grant.issued_at)
    expires = _parse_time(grant.expires_at)
    if (
        issued < _parse_time(request.requested_at)
        or issued < _parse_time(intent.issued_at)
        or _parse_time(intent.issued_at) < _parse_time(request.requested_at)
        or issued >= expires
        or (expires - issued).total_seconds() > LOCAL_TEXT_FILE_ROLLBACK_MAX_TTL_SECONDS
        or expires > _parse_time(intent.expires_at)
        or expires > _parse_time(request.expires_at)
        or _parse_time(now) < issued
        or _parse_time(now) >= expires
    ):
        raise ValueError("local_text_rollback_grant_window_invalid")
    if not grant.confirmation_required or not grant.single_use:
        raise ValueError("local_text_rollback_grant_single_use_confirmation_required")
    _require_metadata_only(grant)
    expected = build_local_text_file_rollback_grant_fingerprint(grant)
    if not compare_digest(grant.grant_fingerprint, expected):
        raise ValueError("local_text_rollback_grant_fingerprint_invalid")


def build_local_text_file_rollback_claim_fingerprint(
    claim: LocalTextFileRollbackGrantClaimContract,
) -> str:
    return _digest(_without(claim, "claim_fingerprint"))


def build_local_text_file_rollback_grant_claim(
    *,
    claim_id: str,
    grant: LocalTextFileRollbackGrantContract,
    rollback_journal_reservation_fingerprint: str,
    claimed_at: Timestamp,
    confirmation_receipt_id: str,
    confirmation_claim_id: str,
    confirmation_claim_fingerprint: str,
) -> LocalTextFileRollbackGrantClaimContract:
    claim = LocalTextFileRollbackGrantClaimContract(
        claim_id=claim_id,
        grant_id=grant.grant_id,
        grant_fingerprint=grant.grant_fingerprint,
        rollback_operation_id=grant.rollback_request.rollback_operation_id,
        rollback_journal_reservation_fingerprint=(rollback_journal_reservation_fingerprint),
        subject_ref=grant.subject_ref,
        rollback_request=grant.rollback_request,
        intent_id=grant.intent_id,
        intent_fingerprint=grant.intent_fingerprint,
        action_fingerprint=grant.action_fingerprint,
        claimed_at=claimed_at,
        expires_at=grant.expires_at,
        claim_fingerprint="0" * 64,
        confirmation_receipt_id=confirmation_receipt_id,
        confirmation_claim_id=confirmation_claim_id,
        confirmation_claim_fingerprint=confirmation_claim_fingerprint,
    )
    claim = replace(
        claim,
        claim_fingerprint=build_local_text_file_rollback_claim_fingerprint(claim),
    )
    require_valid_local_text_file_rollback_grant_claim(claim, grant=grant)
    return claim


def require_valid_local_text_file_rollback_grant_claim(
    claim: LocalTextFileRollbackGrantClaimContract,
    *,
    grant: LocalTextFileRollbackGrantContract,
    now: Timestamp | datetime | None = None,
    require_active: bool = False,
) -> None:
    if not isinstance(claim, LocalTextFileRollbackGrantClaimContract):
        raise TypeError("local_text_rollback_claim_required")
    for value, error in (
        (claim.claim_id, "local_text_rollback_claim_id_invalid"),
        (str(claim.rollback_operation_id), "local_text_rollback_operation_id_invalid"),
        (claim.confirmation_receipt_id, "local_text_rollback_confirmation_receipt_invalid"),
        (claim.confirmation_claim_id, "local_text_rollback_confirmation_claim_invalid"),
    ):
        _require_ref(value, resource=False, error=error)
    _require_sha256(
        claim.rollback_journal_reservation_fingerprint,
        "local_text_rollback_journal_reservation_invalid",
    )
    _require_sha256(
        claim.confirmation_claim_fingerprint,
        "local_text_rollback_confirmation_claim_fingerprint_invalid",
    )
    expected = (
        grant.grant_id,
        grant.grant_fingerprint,
        grant.rollback_request.rollback_operation_id,
        grant.subject_ref,
        grant.rollback_request,
        grant.intent_id,
        grant.intent_fingerprint,
        grant.action_fingerprint,
        grant.expires_at,
    )
    observed = (
        claim.grant_id,
        claim.grant_fingerprint,
        claim.rollback_operation_id,
        claim.subject_ref,
        claim.rollback_request,
        claim.intent_id,
        claim.intent_fingerprint,
        claim.action_fingerprint,
        claim.expires_at,
    )
    if observed != expected:
        raise ValueError("local_text_rollback_claim_binding_drift")
    claimed = _parse_time(claim.claimed_at)
    expires = _parse_time(claim.expires_at)
    if claimed < _parse_time(grant.issued_at) or claimed >= expires:
        raise ValueError("local_text_rollback_claim_time_invalid")
    if require_active:
        if now is None:
            raise ValueError("local_text_rollback_claim_active_time_required")
        current = _parse_time(now)
        if current < claimed or current >= expires:
            raise ValueError("local_text_rollback_claim_inactive")
    if not claim.single_use:
        raise ValueError("local_text_rollback_claim_not_single_use")
    _require_metadata_only(claim)
    expected_fingerprint = build_local_text_file_rollback_claim_fingerprint(claim)
    if not compare_digest(claim.claim_fingerprint, expected_fingerprint):
        raise ValueError("local_text_rollback_claim_fingerprint_invalid")


def require_local_text_rollback_receipt_matches_claim(
    receipt: LocalTextRollbackReceipt,
    *,
    mutation_receipt: LocalTextMutationReceipt,
    claim: LocalTextFileRollbackGrantClaimContract,
) -> None:
    require_valid_local_text_rollback_receipt(receipt)
    require_valid_local_text_mutation_receipt(mutation_receipt)
    expected = (
        str(claim.rollback_operation_id),
        mutation_receipt.operation_id,
        claim.grant_id,
        claim.claim_id,
        mutation_receipt.receipt_fingerprint,
        mutation_receipt.resource_ref,
        claim.rollback_request.restored_content_sha256,
    )
    observed = (
        receipt.operation_id,
        receipt.mutation_operation_id,
        receipt.rollback_grant_id,
        receipt.rollback_claim_id,
        receipt.mutation_receipt_fingerprint,
        receipt.resource_ref,
        receipt.restored_content_sha256,
    )
    if observed != expected:
        raise ValueError("local_text_rollback_receipt_claim_binding_mismatch")
    if _parse_time(receipt.rolled_back_at) < _parse_time(claim.claimed_at):
        raise ValueError("local_text_rollback_receipt_predates_claim")


LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR = build_local_text_file_rollback_descriptor()

SEEDED_LOCAL_TEXT_FILE_ROLLBACK_REGISTRY = build_local_text_file_rollback_registry_snapshot(
    registry_id="jarvis.local_text_file_rollback_registry",
    registry_version="1.0.0",
    descriptors=(LOCAL_TEXT_FILE_ROLLBACK_DESCRIPTOR,),
)
